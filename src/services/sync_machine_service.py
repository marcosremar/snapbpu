"""
Sync Machine Service - Gerencia maquinas de sincronizacao para backup rapido

Cada GPU cria uma Sync Machine na mesma regiao (GCP ou vast.ai CPU-only).
A GPU sincroniza em tempo real com a Sync Machine que cria snapshots a cada 30s.
Se a GPU cair, restaura do snapshot local (muito mais rapido que R2).

Arquitetura:
┌─────────────┐     sync (rsync)     ┌─────────────┐     backup     ┌─────────────┐
│  GPU RTX    │ ─────────────────►   │ Sync Machine│ ────────────►  │ Cloudflare  │
│  5090       │     (tempo real)     │  (CPU-only) │   (cada 5min)  │     R2      │
└─────────────┘                      └─────────────┘                └─────────────┘
       │                                    │
       │     Se GPU cair, restaura daqui    │
       └────────────────────────────────────┘
              (snapshots cada 30s)
"""

import os
import json
import time
import subprocess
import threading
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SyncMachine:
    """Representa uma maquina de sincronizacao"""
    sync_id: str
    provider: str  # 'gcp' ou 'vastai'
    region: str
    zone: str
    ip_address: str
    ssh_port: int = 22
    status: str = 'creating'  # 'creating', 'running', 'stopped', 'error'
    gpu_instance_id: Optional[str] = None  # GPU associada
    created_at: float = field(default_factory=time.time)
    last_sync: Optional[float] = None
    snapshots: List[str] = field(default_factory=list)


class SyncMachineService:
    """Servico para gerenciar maquinas de sincronizacao"""

    # Custo estimado por hora
    GCP_COST_PER_HOUR = 0.13  # e2-standard-4
    VASTAI_CPU_COST_PER_HOUR = 0.02  # CPU-only

    # Mapeamento de regioes vast.ai -> GCP (EXPANDIDO para 90%+ cobertura)
    REGION_MAP = {
        # === AMERICAS ===
        # US - West Coast
        'California, US': 'us-west2-a',
        'Los Angeles': 'us-west2-a',
        'LA': 'us-west2-a',
        'Oregon, US': 'us-west1-a',
        'Washington, US': 'us-west1-a',
        'Seattle': 'us-west1-a',
        'Nevada, US': 'us-west4-a',
        'Las Vegas': 'us-west4-a',
        
        # US - Central
        'Utah, US': 'us-central1-a',
        'Iowa, US': 'us-central1-a',
        'Illinois, US': 'us-central1-a',
        'Chicago': 'us-central1-a',
        'Texas, US': 'us-south1-a',
        'Dallas': 'us-south1-a',
        'Kansas, US': 'us-central1-a',
        'Oklahoma, US': 'us-central1-a',
        'Missouri, US': 'us-central1-a',
        
        # US - East Coast
        'Virginia, US': 'us-east4-a',
        'New York, US': 'us-east4-a',
        'NYC': 'us-east4-a',
        'North Carolina, US': 'us-east1-a',
        'South Carolina, US': 'us-east1-a',
        'Georgia, US': 'us-east1-a',
        'Atlanta': 'us-east1-a',
        'Florida, US': 'us-east1-a',
        'Miami': 'us-east1-a',
        
        # CANADA 🇨🇦 (CRÍTICO - estava faltando!)
        'Quebec': 'northamerica-northeast1-a',
        'Montreal': 'northamerica-northeast1-a',
        'Montréal': 'northamerica-northeast1-a',
        'QC': 'northamerica-northeast1-a',
        'Ontario': 'northamerica-northeast1-a',
        'Toronto': 'northamerica-northeast1-a',
        'Canada': 'northamerica-northeast1-a',
        'CA': 'northamerica-northeast1-a',
        
        # LATAM
        'Brazil': 'southamerica-east1-a',
        'São Paulo': 'southamerica-east1-a',
        'Sao Paulo': 'southamerica-east1-a',
        'BR': 'southamerica-east1-a',
        'Chile': 'southamerica-west1-a',
        'Santiago': 'southamerica-west1-a',
        'Argentina': 'southamerica-east1-a',
        
        # === EUROPE ===
        # West Europe
        'Belgium, BE': 'europe-west1-a',
        'Belgium': 'europe-west1-a',
        'Brussels': 'europe-west1-a',
        'Netherlands, NL': 'europe-west4-a',
        'Netherlands': 'europe-west4-a',
        'Amsterdam': 'europe-west4-a',
        'UK': 'europe-west2-a',
        'United Kingdom': 'europe-west2-a',
        'London': 'europe-west2-a',
        'GB': 'europe-west2-a',
        'Ireland': 'europe-west1-a',
        'Dublin': 'europe-west1-a',
        'France': 'europe-west9-a',
        'Paris': 'europe-west9-a',
        'FR': 'europe-west9-a',
        
        # Central Europe
        'Germany, DE': 'europe-west3-a',
        'Germany': 'europe-west3-a',
        'Frankfurt': 'europe-west3-a',
        'Berlin': 'europe-west3-a',
        'DE': 'europe-west3-a',
        'Switzerland': 'europe-west6-a',
        'Zurich': 'europe-west6-a',
        'CH': 'europe-west6-a',
        'Austria': 'europe-west3-a',
        'Vienna': 'europe-west3-a',
        
        # North Europe
        'Finland, FI': 'europe-north1-a',
        'Finland': 'europe-north1-a',
        'Helsinki': 'europe-north1-a',
        'Sweden': 'europe-north1-a',
        'Stockholm': 'europe-north1-a',
        'Norway': 'europe-north1-a',
        'Oslo': 'europe-north1-a',
        'Denmark': 'europe-north1-a',
        'Copenhagen': 'europe-north1-a',
        
        # East Europe
        'Poland, PL': 'europe-central2-a',
        'Poland': 'europe-central2-a',
        'Warsaw': 'europe-central2-a',
        'PL': 'europe-central2-a',
        
        # South Europe
        'Spain': 'europe-southwest1-a',
        'Madrid': 'europe-southwest1-a',
        'Italy': 'europe-west8-a',
        'Milan': 'europe-west8-a',
        
        # === ASIA ===
        # East Asia
        'Taiwan, TW': 'asia-east1-a',
        'Taiwan': 'asia-east1-a',
        'TW': 'asia-east1-a',
        'Hong Kong': 'asia-east2-a',
        'HK': 'asia-east2-a',
        'Japan, JP': 'asia-northeast1-a',
        'Japan': 'asia-northeast1-a',
        'Tokyo': 'asia-northeast1-a',
        'JP': 'asia-northeast1-a',
        'South Korea': 'asia-northeast3-a',
        'Seoul': 'asia-northeast3-a',
        'Korea': 'asia-northeast3-a',
        'KR': 'asia-northeast3-a',
        
        # Southeast Asia
        'Singapore, SG': 'asia-southeast1-a',
        'Singapore': 'asia-southeast1-a',
        'SG': 'asia-southeast1-a',
        'Indonesia': 'asia-southeast2-a',
        'Jakarta': 'asia-southeast2-a',
        'Thailand': 'asia-southeast1-a',
        'Bangkok': 'asia-southeast1-a',
        'Vietnam': 'asia-southeast1-a',
        'Malaysia': 'asia-southeast1-a',
        
        # South Asia
        'India': 'asia-south1-a',
        'Mumbai': 'asia-south1-a',
        'IN': 'asia-south1-a',
        'Bangalore': 'asia-south1-a',
        'Delhi': 'asia-south1-a',
        
        # === OCEANIA ===
        'Australia, AU': 'australia-southeast1-a',
        'Australia': 'australia-southeast1-a',
        'Sydney': 'australia-southeast1-a',
        'Melbourne': 'australia-southeast1-a',
        'AU': 'australia-southeast1-a',
        'New Zealand': 'australia-southeast1-a',
        'NZ': 'australia-southeast1-a',
        
        # === MIDDLE EAST ===
        'Israel': 'me-west1-a',
        'Tel Aviv': 'me-west1-a',
        'UAE': 'me-central1-a',
        'Dubai': 'me-central1-a',
        
        # === FALLBACKS (ordem de preferência) ===
        'US': 'us-central1-a',
        'EU': 'europe-west1-a',
        'ASIA': 'asia-east1-a',
    }

    def __init__(self, gcp_credentials_path: Optional[str] = None):
        self.gcp_credentials_path = gcp_credentials_path or os.environ.get(
            'GOOGLE_APPLICATION_CREDENTIALS',
            '/Users/marcos/Documents/projects/teste/credentials/gcp-service-account.json'
        )
        self._machines: Dict[str, SyncMachine] = {}
        self._lock = threading.Lock()
        self._sync_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}

    def get_gcp_zone_for_region(self, vast_region: str) -> str:
        """Mapeia regiao vast.ai para zona GCP"""
        # Tentar match exato
        if vast_region in self.REGION_MAP:
            return self.REGION_MAP[vast_region]

        # Tentar match parcial
        for key, zone in self.REGION_MAP.items():
            if key.lower() in vast_region.lower():
                return zone

        # Default para US Central
        return 'us-central1-b'

    def create_gcp_machine(
        self,
        gpu_instance_id: str,
        gpu_region: str,
        project_id: str = 'avian-computer-477918-j9',
        machine_type: str = 'e2-standard-4',
        disk_size_gb: int = 500
    ) -> Dict:
        """
        Cria uma sync machine no GCP na mesma regiao da GPU.

        Args:
            gpu_instance_id: ID da instancia GPU associada
            gpu_region: Regiao da GPU (ex: 'Utah, US')
            project_id: ID do projeto GCP
            machine_type: Tipo da maquina GCP
            disk_size_gb: Tamanho do disco em GB

        Returns:
            Dict com resultado da criacao
        """
        zone = self.get_gcp_zone_for_region(gpu_region)
        sync_id = f"sync-{gpu_instance_id}-{int(time.time())}"

        try:
            # Construir comando gcloud
            cmd = [
                'gcloud', 'compute', 'instances', 'create', sync_id,
                f'--project={project_id}',
                f'--zone={zone}',
                f'--machine-type={machine_type}',
                f'--boot-disk-size={disk_size_gb}GB',
                '--boot-disk-type=pd-ssd',
                '--image-family=ubuntu-2204-lts',
                '--image-project=ubuntu-os-cloud',
                '--tags=dumont-sync',
                '--format=json',
            ]

            # Adicionar credenciais se disponivel
            if os.path.exists(self.gcp_credentials_path):
                env = os.environ.copy()
                env['GOOGLE_APPLICATION_CREDENTIALS'] = self.gcp_credentials_path
            else:
                env = None

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'error': result.stderr or 'Falha ao criar maquina GCP'
                }

            # Parsear resultado
            instances = json.loads(result.stdout)
            if instances:
                instance = instances[0]
                ip_address = None

                # Obter IP externo
                for interface in instance.get('networkInterfaces', []):
                    for access in interface.get('accessConfigs', []):
                        if access.get('natIP'):
                            ip_address = access['natIP']
                            break

                machine = SyncMachine(
                    sync_id=sync_id,
                    provider='gcp',
                    region=gpu_region,
                    zone=zone,
                    ip_address=ip_address or '',
                    status='running',
                    gpu_instance_id=gpu_instance_id
                )

                with self._lock:
                    self._machines[sync_id] = machine

                # Configurar maquina em background
                threading.Thread(
                    target=self._setup_sync_machine,
                    args=(machine,),
                    daemon=True
                ).start()

                return {
                    'success': True,
                    'sync_id': sync_id,
                    'ip_address': ip_address,
                    'zone': zone,
                    'cost_per_hour': self.GCP_COST_PER_HOUR
                }

            return {'success': False, 'error': 'Resposta vazia do GCP'}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout ao criar maquina GCP'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_vastai_cpu_machine(
        self,
        gpu_instance_id: str,
        gpu_region: str,
        vast_api_key: str,
        min_disk_gb: int = 200,
        max_price: float = 0.05
    ) -> Dict:
        """
        Cria uma sync machine no vast.ai (CPU-only, mais barato).

        Args:
            gpu_instance_id: ID da instancia GPU associada
            gpu_region: Regiao da GPU
            vast_api_key: API key do vast.ai
            min_disk_gb: Disco minimo
            max_price: Preco maximo por hora

        Returns:
            Dict com resultado
        """
        sync_id = f"sync-{gpu_instance_id}-{int(time.time())}"

        try:
            import requests

            headers = {'Authorization': f'Bearer {vast_api_key}'}

            # Buscar ofertas CPU-only na mesma regiao
            query = {
                'rentable': {'eq': True},
                'num_gpus': {'eq': 0},  # CPU-only
                'disk_space': {'gte': min_disk_gb},
                'dph_total': {'lte': max_price},
                'order': [['dph_total', 'asc']],
                'type': 'on-demand'
            }

            resp = requests.get(
                'https://console.vast.ai/api/v0/bundles/',
                headers=headers,
                params={'q': json.dumps(query)}
            )

            if resp.status_code != 200:
                return {'success': False, 'error': f'API error: {resp.status_code}'}

            offers = resp.json().get('offers', [])

            # Filtrar por regiao
            region_offers = [
                o for o in offers
                if gpu_region.split(',')[0].lower() in o.get('geolocation', '').lower()
            ]

            # Se nao encontrar na regiao, usar qualquer uma
            offer = (region_offers or offers)[0] if offers else None

            if not offer:
                return {'success': False, 'error': 'Nenhuma oferta CPU disponivel'}

            # Criar instancia
            create_resp = requests.put(
                f'https://console.vast.ai/api/v0/asks/{offer["id"]}/',
                headers=headers,
                json={
                    'client_id': 'me',
                    'image': 'ubuntu:22.04',
                    'disk': min_disk_gb,
                    'onstart': 'apt-get update && apt-get install -y rsync rclone restic'
                }
            )

            if create_resp.status_code != 200:
                return {'success': False, 'error': 'Falha ao criar instancia'}

            data = create_resp.json()
            instance_id = data.get('new_contract')

            if not instance_id:
                return {'success': False, 'error': 'ID da instancia nao retornado'}

            machine = SyncMachine(
                sync_id=sync_id,
                provider='vastai',
                region=gpu_region,
                zone=offer.get('geolocation', ''),
                ip_address='',  # Sera preenchido quando estiver pronta
                status='creating',
                gpu_instance_id=gpu_instance_id
            )

            with self._lock:
                self._machines[sync_id] = machine

            return {
                'success': True,
                'sync_id': sync_id,
                'vastai_instance_id': instance_id,
                'cost_per_hour': offer.get('dph_total', self.VASTAI_CPU_COST_PER_HOUR)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def start_continuous_sync(
        self,
        sync_id: str,
        gpu_ssh_host: str,
        gpu_ssh_port: int,
        source_path: str = '/workspace',
        interval_seconds: int = 30
    ) -> Dict:
        """
        Inicia sincronizacao continua entre GPU e Sync Machine.

        Args:
            sync_id: ID da sync machine
            gpu_ssh_host: Host SSH da GPU
            gpu_ssh_port: Porta SSH da GPU
            source_path: Caminho a sincronizar
            interval_seconds: Intervalo entre snapshots

        Returns:
            Dict com resultado
        """
        with self._lock:
            machine = self._machines.get(sync_id)
            if not machine:
                return {'success': False, 'error': 'Sync machine nao encontrada'}

            if sync_id in self._sync_threads and self._sync_threads[sync_id].is_alive():
                return {'success': False, 'error': 'Sincronizacao ja esta ativa'}

        # Criar evento de parada
        stop_event = threading.Event()
        self._stop_events[sync_id] = stop_event

        # Iniciar thread de sincronizacao
        thread = threading.Thread(
            target=self._sync_loop,
            args=(sync_id, gpu_ssh_host, gpu_ssh_port, source_path, interval_seconds, stop_event),
            daemon=True
        )
        thread.start()
        self._sync_threads[sync_id] = thread

        return {
            'success': True,
            'sync_id': sync_id,
            'interval': interval_seconds
        }

    def stop_continuous_sync(self, sync_id: str) -> Dict:
        """Para sincronizacao continua"""
        stop_event = self._stop_events.get(sync_id)
        if stop_event:
            stop_event.set()
            return {'success': True}
        return {'success': False, 'error': 'Sincronizacao nao encontrada'}

    def get_machine(self, sync_id: str) -> Optional[SyncMachine]:
        """Retorna informacoes de uma sync machine"""
        with self._lock:
            return self._machines.get(sync_id)

    def list_machines(self) -> List[Dict]:
        """Lista todas as sync machines"""
        with self._lock:
            return [
                {
                    'sync_id': m.sync_id,
                    'provider': m.provider,
                    'region': m.region,
                    'zone': m.zone,
                    'ip_address': m.ip_address,
                    'status': m.status,
                    'gpu_instance_id': m.gpu_instance_id,
                    'last_sync': m.last_sync,
                    'snapshots_count': len(m.snapshots)
                }
                for m in self._machines.values()
            ]

    def destroy_machine(self, sync_id: str) -> Dict:
        """Destroi uma sync machine"""
        with self._lock:
            machine = self._machines.get(sync_id)
            if not machine:
                return {'success': False, 'error': 'Maquina nao encontrada'}

        # Parar sincronizacao
        self.stop_continuous_sync(sync_id)

        try:
            if machine.provider == 'gcp':
                cmd = [
                    'gcloud', 'compute', 'instances', 'delete', sync_id,
                    f'--zone={machine.zone}',
                    '--quiet'
                ]
                subprocess.run(cmd, capture_output=True, timeout=60)

            with self._lock:
                del self._machines[sync_id]

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _setup_sync_machine(self, machine: SyncMachine):
        """Configura uma sync machine recem-criada"""
        try:
            # Aguardar maquina estar acessivel
            time.sleep(30)

            # Instalar dependencias
            setup_cmd = '''
apt-get update -qq &&
apt-get install -y -qq rsync rclone restic &&
mkdir -p /workspace/snapshots /workspace/sync &&
echo "Sync machine ready"
'''
            self._ssh_exec(machine.ip_address, machine.ssh_port, setup_cmd, timeout=300)

            with self._lock:
                machine.status = 'ready'

        except Exception as e:
            with self._lock:
                machine.status = 'error'

    def _sync_loop(
        self,
        sync_id: str,
        gpu_ssh_host: str,
        gpu_ssh_port: int,
        source_path: str,
        interval: int,
        stop_event: threading.Event
    ):
        """Loop de sincronizacao continua"""
        while not stop_event.is_set():
            try:
                machine = self.get_machine(sync_id)
                if not machine or machine.status != 'ready':
                    time.sleep(5)
                    continue

                # Sincronizar via rsync
                rsync_cmd = [
                    'rsync', '-avz', '--delete',
                    '-e', f'ssh -o StrictHostKeyChecking=no -p {gpu_ssh_port}',
                    f'root@{gpu_ssh_host}:{source_path}/',
                    f'root@{machine.ip_address}:/workspace/sync/'
                ]

                subprocess.run(rsync_cmd, capture_output=True, timeout=300)

                # Criar snapshot local
                snapshot_id = f"snap-{int(time.time())}"
                snapshot_cmd = f'''
cd /workspace &&
restic -r /workspace/snapshots backup /workspace/sync --tag {sync_id}
'''
                self._ssh_exec(machine.ip_address, machine.ssh_port, snapshot_cmd, timeout=120)

                with self._lock:
                    machine.last_sync = time.time()
                    machine.snapshots.append(snapshot_id)
                    # Manter apenas ultimos 10 snapshots
                    if len(machine.snapshots) > 10:
                        machine.snapshots = machine.snapshots[-10:]

            except Exception:
                pass

            stop_event.wait(interval)

    def _ssh_exec(
        self,
        ssh_host: str,
        ssh_port: int,
        command: str,
        timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """Executa comando via SSH"""
        return subprocess.run(
            [
                'ssh', '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-p', str(ssh_port),
                f'root@{ssh_host}',
                command
            ],
            capture_output=True,
            text=True,
            timeout=timeout
        )


# Singleton
_sync_machine_service: Optional[SyncMachineService] = None


def get_sync_machine_service() -> SyncMachineService:
    """Retorna instancia singleton do servico"""
    global _sync_machine_service
    if _sync_machine_service is None:
        _sync_machine_service = SyncMachineService()
    return _sync_machine_service
