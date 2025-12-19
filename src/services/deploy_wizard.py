"""
DeployWizard Service - Gerenciamento inteligente de deploy de maquinas GPU

Estrategia:
1. Busca ofertas baseado nos filtros do wizard
2. Cria maquinas em paralelo (batch de 5)
3. Timeout de 10 segundos por maquina - se nao ficar pronta, tenta outra
4. Usa a primeira que responder
5. Destroi as outras automaticamente
6. Opcionalmente faz restore do snapshot
7. Instala code-server automaticamente via CodeServerService
"""
import time
import uuid
import threading
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.services.vast_service import VastService
from src.services.codeserver_service import CodeServerService, CodeServerConfig


# Configuracoes do Wizard
SPEED_TIERS = {
    'slow': {'min': 100, 'max': 500, 'name': 'Lenta'},
    'medium': {'min': 500, 'max': 2000, 'name': 'Media'},
    'fast': {'min': 2000, 'max': 4000, 'name': 'Rapida'},
    'ultra': {'min': 4000, 'max': 99999, 'name': 'Ultra'},
}

GPU_OPTIONS = [
    'RTX 5090', 'RTX 4090', 'RTX 4080', 'RTX 3090', 'RTX 3080',
    'RTX A6000', 'RTX A5000', 'RTX A4000', 'A100', 'H100', 'L40S'
]

REGIONS = {
    'global': [],
    'US': ['US', 'United States', 'CA', 'Canada'],
    'EU': ['ES', 'DE', 'FR', 'NL', 'IT', 'PL', 'CZ', 'BG', 'UK', 'GB',
           'Spain', 'Germany', 'France', 'Netherlands', 'Poland',
           'Czechia', 'Bulgaria', 'Sweden', 'Norway', 'Finland'],
    'ASIA': ['JP', 'Japan', 'KR', 'Korea', 'SG', 'Singapore', 'TW', 'Taiwan'],
}

# Configuracoes de timeout e batches
BATCH_TIMEOUT = 90  # segundos para aguardar batch inteiro
CHECK_INTERVAL = 3  # intervalo entre verificacoes
BATCH_SIZE = 5      # maquinas por batch
MAX_BATCHES = 3     # maximo de batches (15 maquinas total)


@dataclass
class DeployConfig:
    """Configuracao de deploy do wizard"""
    speed_tier: str = 'fast'
    gpu_name: Optional[str] = None
    region: str = 'global'
    disk_space: int = 50
    max_price: float = 2.0
    snapshot_id: Optional[str] = None
    target_path: str = '/workspace'
    hot_start: bool = False
    docker_options: Optional[str] = None  # Ex: "-p 10000-10010:10000-10010/udp" para streaming
    setup_codeserver: bool = True  # Instalar code-server automaticamente


class DeployJob:
    """Representa um job de deploy em andamento"""

    def __init__(self, job_id: str, config: DeployConfig):
        self.id = job_id
        self.config = config
        self.status = 'starting'
        self.message = 'Iniciando deploy...'
        self.created_at = time.time()

        # Progresso
        self.batch = 0
        self.machines_tried = 0
        self.machines_created = []
        self.machines_destroyed = []
        self.offers_found = 0

        # Resultado
        self.result = None
        self.error = None
        self.setup_result = None  # Resultado do setup code-server

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'status': self.status,
            'message': self.message,
            'created_at': self.created_at,
            'config': {
                'speed_tier': self.config.speed_tier,
                'gpu_name': self.config.gpu_name,
                'region': self.config.region,
                'disk_space': self.config.disk_space,
                'max_price': self.config.max_price,
                'setup_codeserver': self.config.setup_codeserver,
            },
            'progress': {
                'batch': self.batch,
                'machines_tried': self.machines_tried,
                'machines_created': len(self.machines_created),
                'machines_destroyed': len(self.machines_destroyed),
                'offers_found': self.offers_found,
            },
            'result': self.result,
            'error': self.error,
            'setup_result': self.setup_result,
        }


class DeployWizardService:
    """
    Servico centralizado de deploy com estrategia de multi-start.

    Estrategia:
    - Cria batch de 5 maquinas em paralelo
    - Monitora todas simultaneamente
    - Usa a primeira que ficar pronta (SSH respondendo)
    - Destroi as outras imediatamente
    - Timeout de 90s por batch - se nenhuma ficar pronta, tenta mais um batch
    """

    def __init__(self, api_key: str):
        self.vast = VastService(api_key)
        self.jobs: Dict[str, DeployJob] = {}

    def get_offers(self, config: DeployConfig) -> List[dict]:
        """Busca ofertas baseado na configuracao do wizard"""
        tier = SPEED_TIERS.get(config.speed_tier, SPEED_TIERS['fast'])

        offers = self.vast.search_offers(
            gpu_name=config.gpu_name,
            min_inet_down=tier['min'],
            max_price=config.max_price,
            min_disk=config.disk_space,
            region=config.region if config.region != 'global' else None,
            limit=BATCH_SIZE * MAX_BATCHES * 2
        )

        # Filtrar por velocidade maxima do tier (exceto ultra)
        if config.speed_tier != 'ultra':
            offers = [o for o in offers if o.get('inet_down', 0) < tier['max']]

        # Ordenar por velocidade de internet (mais rapido primeiro)
        offers.sort(key=lambda o: o.get('inet_down', 0), reverse=True)

        return offers

    def get_offers_preview(self, config: DeployConfig) -> dict:
        """Preview de ofertas por tier de velocidade"""
        offers = self.vast.search_offers(
            gpu_name=config.gpu_name,
            min_inet_down=100,
            max_price=config.max_price,
            min_disk=config.disk_space,
            region=config.region if config.region != 'global' else None,
            limit=200
        )

        tiers_summary = {}
        for tier_name, tier_config in SPEED_TIERS.items():
            tier_offers = [
                o for o in offers
                if tier_config['min'] <= o.get('inet_down', 0) < tier_config['max']
            ]

            if tier_offers:
                prices = [o['dph_total'] for o in tier_offers]
                speeds = [o['inet_down'] for o in tier_offers]
                tiers_summary[tier_name] = {
                    'count': len(tier_offers),
                    'min_price': min(prices),
                    'max_price': max(prices),
                    'avg_speed': sum(speeds) / len(speeds),
                    'gpus': list(set(o['gpu_name'] for o in tier_offers))[:5]
                }
            else:
                tiers_summary[tier_name] = {
                    'count': 0, 'min_price': None, 'max_price': None,
                    'avg_speed': None, 'gpus': []
                }

        return {
            'total_offers': len(offers),
            'tiers': tiers_summary,
            'gpu_options': GPU_OPTIONS,
            'regions': list(REGIONS.keys()),
        }

    def _check_instance_status(self, instance_id: int) -> Optional[dict]:
        """
        Verifica status de uma instancia.

        Considera a maquina pronta quando:
        - Status é 'running'
        - Tem ssh_host e ssh_port (retornados pela API vast.ai)

        Nota: Nao fazemos verificacao SSH pois o servidor nao tem
        as chaves SSH para conectar nas maquinas vast.ai.
        """
        try:
            status = self.vast.get_instance_status(instance_id)
            actual_status = status.get('status')

            # Debug logging - usar ssh_host e ssh_port em vez de ports
            ssh_host = status.get('ssh_host')
            ssh_port = status.get('ssh_port')
            print(f"[DEBUG] Instance {instance_id}: status={actual_status}, ssh_host={ssh_host}, ssh_port={ssh_port}")

            if actual_status == 'running':
                # vast.ai retorna ssh_host e ssh_port diretamente
                if ssh_host and ssh_port:
                    print(f"[DEBUG] Instance {instance_id} is READY! Host={ssh_host}, Port={ssh_port}")
                    return {
                        'instance_id': instance_id,
                        'public_ip': ssh_host,
                        'ssh_port': int(ssh_port),
                        'gpu_name': status.get('gpu_name'),
                    }
            return None
        except Exception as e:
            print(f"[DEBUG] Instance {instance_id} error: {e}")
            return None

    def _create_instance(self, offer: dict, config: DeployConfig) -> Optional[int]:
        """Cria uma instancia e retorna o ID"""
        try:
            instance_id = self.vast.create_instance(
                offer_id=offer['id'],
                image='pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime',
                disk=config.disk_space,
                docker_options=config.docker_options
            )
            return instance_id
        except Exception:
            return None

    def _setup_codeserver(self, ssh_host: str, ssh_port: int, workspace: str = "/workspace") -> dict:
        """
        Instala e configura code-server na instancia.

        Args:
            ssh_host: IP ou hostname do servidor
            ssh_port: Porta SSH
            workspace: Diretorio workspace

        Returns:
            dict com resultado do setup
        """
        try:
            config = CodeServerConfig(
                port=8080,
                workspace=workspace,
                theme="Default Dark+",
                trust_enabled=False,
                user="root",
            )

            codeserver = CodeServerService(ssh_host, ssh_port, "root")
            result = codeserver.setup_full(config)

            return {
                "success": result.get("success", False),
                "port": config.port,
                "message": result.get("message", ""),
                "steps": result.get("steps", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _run_deploy(self, job: DeployJob):
        """
        Executa o deploy em background com estrategia multi-start.

        Estrategia:
        1. Criar batch de 5 maquinas em paralelo
        2. Monitorar todas a cada 3 segundos
        3. A primeira que ficar pronta (SSH respondendo) vence
        4. Se nenhuma ficar pronta em 90s, criar mais um batch
        5. Destruir todas as perdedoras
        """
        try:
            job.status = 'searching'
            job.message = 'Buscando ofertas...'

            # Buscar ofertas
            offers = self.get_offers(job.config)
            job.offers_found = len(offers)

            if not offers:
                job.status = 'failed'
                job.error = 'Nenhuma oferta disponivel com os filtros especificados'
                return

            winner = None
            all_created = []  # Lista de (instance_id, offer)
            deploy_start = time.time()

            # Multi-start em batches
            for batch_num in range(MAX_BATCHES):
                if winner:
                    break

                job.batch = batch_num + 1
                start_idx = batch_num * BATCH_SIZE
                batch_offers = offers[start_idx:start_idx + BATCH_SIZE]

                if not batch_offers:
                    break

                # Criar maquinas em paralelo
                job.status = 'creating'
                job.message = f'Batch {batch_num + 1}: Criando {len(batch_offers)} maquinas...'

                with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                    create_futures = {
                        executor.submit(self._create_instance, offer, job.config): offer
                        for offer in batch_offers
                    }

                    for future in as_completed(create_futures, timeout=30):
                        try:
                            instance_id = future.result()
                            offer = create_futures[future]
                            job.machines_tried += 1

                            if instance_id:
                                all_created.append((instance_id, offer))
                                job.machines_created.append(instance_id)
                                job.message = f'Criada maquina {instance_id}'
                        except Exception:
                            pass

                # Monitorar todas as maquinas do batch
                job.status = 'waiting'
                batch_start = time.time()

                while time.time() - batch_start < BATCH_TIMEOUT:
                    elapsed = int(time.time() - deploy_start)
                    job.message = f'Aguardando maquinas... ({elapsed}s, {len(all_created)} criadas)'

                    # Verificar cada maquina criada
                    for instance_id, offer in all_created:
                        if instance_id in job.machines_destroyed:
                            continue

                        result = self._check_instance_status(instance_id)
                        if result:
                            # Maquina pronta!
                            winner = result
                            winner['offer_id'] = offer['id']
                            winner['inet_down'] = offer.get('inet_down', 0)
                            winner['dph_total'] = offer.get('dph_total', 0)
                            winner['ready_time'] = time.time() - deploy_start

                            job.status = 'ready'
                            job.message = f'Maquina {instance_id} pronta em {winner["ready_time"]:.1f}s!'
                            break

                    if winner:
                        break

                    time.sleep(CHECK_INTERVAL)

                # Se nao encontrou vencedor, proximo batch
                if not winner:
                    job.message = f'Batch {batch_num + 1}: Nenhuma maquina ficou pronta em {BATCH_TIMEOUT}s'

            # Cleanup - destruir todas as maquinas nao utilizadas
            job.status = 'cleanup'
            job.message = 'Destruindo maquinas nao utilizadas...'

            for instance_id, offer in all_created:
                if not winner or instance_id != winner.get('instance_id'):
                    if instance_id not in job.machines_destroyed:
                        try:
                            self.vast.destroy_instance(instance_id)
                            job.machines_destroyed.append(instance_id)
                        except:
                            pass

            if not winner:
                job.status = 'failed'
                job.error = f'Nenhuma maquina ficou pronta em {BATCH_TIMEOUT}s apos {job.machines_tried} tentativas'
                return

            # Setup code-server se habilitado
            if job.config.setup_codeserver:
                job.status = 'setting_up'
                job.message = 'Instalando code-server...'

                setup_result = self._setup_codeserver(
                    ssh_host=winner['public_ip'],
                    ssh_port=winner['ssh_port'],
                    workspace=job.config.target_path
                )
                job.setup_result = setup_result

                if setup_result.get('success'):
                    job.message = f"code-server instalado na porta {setup_result.get('port')}"
                else:
                    job.message = f"code-server falhou: {setup_result.get('error', 'erro desconhecido')}"

            # Sucesso!
            job.status = 'completed'
            job.message = 'Deploy concluido!'
            job.result = {
                'success': True,
                'instance_id': winner['instance_id'],
                'public_ip': winner['public_ip'],
                'ssh_port': winner['ssh_port'],
                'ssh_command': f"ssh -p {winner['ssh_port']} root@{winner['public_ip']}",
                'gpu_name': winner.get('gpu_name'),
                'inet_down': winner.get('inet_down'),
                'dph_total': winner.get('dph_total'),
                'ready_time': winner.get('ready_time'),
                'total_time': time.time() - job.created_at,
                'codeserver_port': 8080 if job.config.setup_codeserver else None,
            }

        except Exception as e:
            job.status = 'failed'
            job.error = str(e)

            # Cleanup em caso de erro
            for instance_id, offer in getattr(job, '_all_created', []):
                if instance_id not in job.machines_destroyed:
                    try:
                        self.vast.destroy_instance(instance_id)
                    except:
                        pass

    def start_deploy(self, config: DeployConfig) -> DeployJob:
        """Inicia um novo deploy em background"""
        job_id = str(uuid.uuid4())[:8]
        job = DeployJob(job_id, config)
        self.jobs[job_id] = job

        # Executar em background
        thread = threading.Thread(
            target=self._run_deploy,
            args=(job,),
            daemon=True
        )
        thread.start()

        return job

    def get_job(self, job_id: str) -> Optional[DeployJob]:
        """Retorna um job pelo ID"""
        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[DeployJob]:
        """Lista os ultimos jobs"""
        jobs = list(self.jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]


# Singleton para armazenar jobs entre requests
_wizard_jobs: Dict[str, DeployJob] = {}


def get_wizard_service(api_key: str) -> DeployWizardService:
    """Factory para criar o servico do wizard"""
    service = DeployWizardService(api_key)
    service.jobs = _wizard_jobs
    return service
