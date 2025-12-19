"""
CPU Standby Service - Sistema de failover GPU → CPU
Mantém uma máquina CPU sincronizada com a GPU para failover transparente.

Arquitetura:
┌─────────────────┐         ┌─────────────────┐
│  GPU Vast.ai    │  rsync  │  GCP CPU        │
│  (principal)    │ ──────► │  (standby)      │
└─────────────────┘         └─────────────────┘
        │                          │
        │                          │ backup
        ▼                          ▼
   [Usuário]                 [Cloudflare R2]
"""
import os
import time
import json
import subprocess
import threading
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from requests.exceptions import RequestException

from src.infrastructure.providers.gcp_provider import GCPProvider, GCPInstanceConfig
from src.services.vast_service import VastService
from src.services.gpu_snapshot_service import GPUSnapshotService

logger = logging.getLogger(__name__)


class StandbyState(Enum):
    """Estados do sistema de standby"""
    DISABLED = "disabled"
    PROVISIONING = "provisioning"
    SYNCING = "syncing"
    READY = "ready"
    FAILOVER_ACTIVE = "failover_active"
    RECOVERING = "recovering"  # Provisionando nova GPU
    ERROR = "error"


@dataclass
class CPUStandbyConfig:
    """Configuração do sistema de CPU Standby"""
    # GCP Config
    gcp_zone: str = "europe-west1-b"  # Próximo das GPUs EU
    gcp_machine_type: str = "e2-medium"  # 1 vCPU, 4GB - suficiente para standby
    gcp_disk_size: int = 100  # GB
    gcp_spot: bool = True  # Usar Spot VM (mais barato)

    # Sync Config
    sync_interval_seconds: int = 30  # Intervalo de sync GPU → CPU
    sync_path: str = "/workspace"  # Path a sincronizar
    sync_exclude: List[str] = field(default_factory=lambda: [
        ".git",
        "__pycache__",
        "*.pyc",
        ".cache",
        "node_modules",
        ".venv",
        "venv",
        "*.log",
        "*.tmp"
    ])

    # Failover Config
    health_check_interval: int = 10  # Segundos entre health checks
    failover_threshold: int = 3  # Número de falhas antes de failover
    auto_failover: bool = True  # Failover automático ou manual
    auto_recovery: bool = True  # Provisionar nova GPU automaticamente após failover

    # GPU Recovery Config
    gpu_min_ram: int = 8  # GB mínimo de VRAM
    gpu_max_price: float = 0.50  # Preço máximo por hora
    gpu_preferred_regions: List[str] = field(default_factory=lambda: [
        "TH", "VN", "JP", "EU", "US"  # Regiões preferidas (ordem de prioridade)
    ])

    # R2 Backup Config
    r2_backup_interval: int = 300  # Backup para R2 a cada 5 min
    r2_endpoint: str = ""
    r2_bucket: str = ""


class CPUStandbyService:
    """
    Serviço de CPU Standby para failover de GPU.

    Funcionalidades:
    1. Provisiona VM CPU no GCP (Spot para economia)
    2. Sincroniza continuamente GPU → CPU via rsync
    3. Monitora saúde da GPU
    4. Failover automático/manual quando GPU cai
    5. Backup periódico CPU → R2
    """

    def __init__(
        self,
        vast_api_key: str,
        gcp_credentials: Dict[str, Any],
        config: Optional[CPUStandbyConfig] = None
    ):
        """
        Inicializa o serviço de CPU Standby.

        Args:
            vast_api_key: API key da Vast.ai
            gcp_credentials: Credenciais GCP (dict do JSON)
            config: Configuração do serviço
        """
        self.vast_service = VastService(api_key=vast_api_key)
        self.gcp_provider = GCPProvider(credentials_json=json.dumps(gcp_credentials))
        self.config = config or CPUStandbyConfig()

        # Estado
        self.state = StandbyState.DISABLED
        self.cpu_instance: Optional[Dict] = None
        self.gpu_instance_id: Optional[int] = None
        self.gpu_ssh_host: Optional[str] = None
        self.gpu_ssh_port: Optional[int] = None

        # Threads de background
        self._sync_thread: Optional[threading.Thread] = None
        self._health_thread: Optional[threading.Thread] = None
        self._backup_thread: Optional[threading.Thread] = None
        self._running = False

        # Métricas
        self.last_sync_time: Optional[datetime] = None
        self.last_backup_time: Optional[datetime] = None
        self.sync_count = 0
        self.failed_health_checks = 0

        # R2 para backup
        if self.config.r2_endpoint and self.config.r2_bucket:
            self.snapshot_service = GPUSnapshotService(
                self.config.r2_endpoint,
                self.config.r2_bucket
            )
        else:
            self.snapshot_service = None

        logger.info("CPUStandbyService initialized")

    def provision_cpu_standby(self, name_suffix: str = "standby") -> Optional[str]:
        """
        Provisiona uma nova VM CPU no GCP para standby.

        Args:
            name_suffix: Sufixo para o nome da VM

        Returns:
            ID da instância criada ou None
        """
        self.state = StandbyState.PROVISIONING
        logger.info("Provisioning CPU standby VM in GCP")

        try:
            # Configurar VM
            vm_config = GCPInstanceConfig(
                name=f"dumont-{name_suffix}-{int(time.time())}",
                machine_type=self.config.gcp_machine_type,
                zone=self.config.gcp_zone,
                disk_size_gb=self.config.gcp_disk_size,
                spot=self.config.gcp_spot
            )

            # Criar VM
            result = self.gcp_provider.create_instance(vm_config)

            if result.get("error"):
                logger.error(f"Failed to create CPU standby: {result['error']}")
                self.state = StandbyState.ERROR
                return None

            self.cpu_instance = result
            logger.info(f"CPU standby provisioned: {result['name']} ({result['external_ip']})")

            # Aguardar VM estar pronta para SSH
            self._wait_for_ssh_ready(result['external_ip'])

            self.state = StandbyState.READY
            return result['instance_id']

        except Exception as e:
            logger.error(f"Error provisioning CPU standby: {e}")
            self.state = StandbyState.ERROR
            return None

    def _wait_for_ssh_ready(self, ip: str, timeout: int = 300, port: int = 22):
        """Aguarda a VM estar pronta para conexão SSH"""
        import socket

        logger.info(f"Waiting for SSH to be ready on {ip}:{port}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((ip, port))
                sock.close()

                if result == 0:
                    logger.info(f"SSH ready on {ip}:{port}")
                    # Aguardar mais um pouco para startup script completar
                    time.sleep(30)
                    return True
            except (OSError, subprocess.TimeoutExpired) as e:
                logger.debug(f"SSH not yet ready on {ip}:{port}: {e}")

            time.sleep(5)

        logger.warning(f"SSH timeout waiting for {ip}:{port}")
        return False

    def register_gpu_instance(
        self,
        instance_id: int,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None
    ) -> bool:
        """
        Registra uma instância GPU para monitoramento e sync.

        Args:
            instance_id: ID da instância Vast.ai
            ssh_host: Host SSH (obtido automaticamente se não fornecido)
            ssh_port: Porta SSH (obtido automaticamente se não fornecido)

        Returns:
            True se registrado com sucesso
        """
        self.gpu_instance_id = instance_id

        # Obter detalhes da instância se não fornecidos
        if not ssh_host or not ssh_port:
            status = self.vast_service.get_instance_status(instance_id)
            if status.get('status') != 'running':
                logger.error(f"GPU instance {instance_id} is not running")
                return False

            self.gpu_ssh_host = status.get('ssh_host')
            self.gpu_ssh_port = status.get('ssh_port')
        else:
            self.gpu_ssh_host = ssh_host
            self.gpu_ssh_port = ssh_port

        logger.info(f"Registered GPU instance {instance_id} ({self.gpu_ssh_host}:{self.gpu_ssh_port})")
        return True

    def start_sync(self) -> bool:
        """
        Inicia sincronização contínua GPU → CPU.

        Returns:
            True se iniciado com sucesso
        """
        if not self.cpu_instance or not self.gpu_ssh_host:
            logger.error("CPU standby or GPU not configured")
            return False

        if self._running:
            logger.warning("Sync already running")
            return True

        self._running = True
        self.state = StandbyState.SYNCING

        # Thread de sync
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()

        # Thread de health check
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()

        # Thread de backup para R2 (se configurado)
        if self.snapshot_service:
            self._backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
            self._backup_thread.start()

        logger.info("Sync started")
        return True

    def stop_sync(self):
        """Para a sincronização"""
        self._running = False
        self.state = StandbyState.READY

        if self._sync_thread:
            self._sync_thread.join(timeout=10)
        if self._health_thread:
            self._health_thread.join(timeout=10)
        if self._backup_thread:
            self._backup_thread.join(timeout=10)

        logger.info("Sync stopped")

    def _sync_loop(self):
        """Loop de sincronização GPU → CPU"""
        while self._running:
            try:
                self._do_sync()
                self.last_sync_time = datetime.now()
            except Exception as e:
                logger.error(f"Sync error: {e}")

            time.sleep(self.config.sync_interval_seconds)

    def _do_sync(self):
        """
        Executa sincronização GPU → CPU via rsync.

        Como rsync não suporta cópia direta entre dois hosts remotos,
        usamos um diretório local temporário como relay:
        GPU → /tmp/dumont-sync/ → CPU
        """
        if not self.cpu_instance or not self.gpu_ssh_host:
            return

        cpu_ip = self.cpu_instance.get('external_ip')
        if not cpu_ip:
            return

        # Diretório temporário para relay
        local_sync_dir = "/tmp/dumont-sync-relay"
        os.makedirs(local_sync_dir, exist_ok=True)

        # Construir exclude args
        exclude_args = []
        for pattern in self.config.sync_exclude:
            exclude_args.extend(["--exclude", pattern])

        ssh_key = os.path.expanduser("~/.ssh/id_rsa")
        ssh_opts = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {ssh_key}"

        try:
            # Step 1: GPU → Local
            rsync_gpu_local = [
                "rsync", "-avz", "--delete",
                "-e", f"{ssh_opts} -p {self.gpu_ssh_port}",
                *exclude_args,
                f"root@{self.gpu_ssh_host}:{self.config.sync_path}/",
                f"{local_sync_dir}/"
            ]

            logger.debug(f"Sync step 1: GPU → Local")
            result1 = subprocess.run(
                rsync_gpu_local,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result1.returncode != 0:
                logger.warning(f"GPU→Local sync failed: {result1.stderr[:200]}")
                return

            # Step 2: Local → CPU
            rsync_local_cpu = [
                "rsync", "-avz", "--delete",
                "-e", f"{ssh_opts}",
                *exclude_args,
                f"{local_sync_dir}/",
                f"root@{cpu_ip}:{self.config.sync_path}/"
            ]

            logger.debug(f"Sync step 2: Local → CPU")
            result2 = subprocess.run(
                rsync_local_cpu,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result2.returncode == 0:
                self.sync_count += 1
                logger.debug("Sync completed successfully")
            else:
                logger.warning(f"Local→CPU sync failed: {result2.stderr[:200]}")

        except subprocess.TimeoutExpired:
            logger.error("Sync timeout")
        except Exception as e:
            logger.error(f"Sync error: {e}")

    def _health_check_loop(self):
        """Loop de verificação de saúde da GPU"""
        while self._running:
            try:
                is_healthy = self._check_gpu_health()

                if is_healthy:
                    self.failed_health_checks = 0
                else:
                    self.failed_health_checks += 1
                    logger.warning(f"GPU health check failed ({self.failed_health_checks}/{self.config.failover_threshold})")

                    if self.failed_health_checks >= self.config.failover_threshold:
                        if self.config.auto_failover:
                            logger.warning("Initiating automatic failover!")
                            self.trigger_failover()
                        else:
                            logger.warning("Failover threshold reached. Manual failover required.")

            except Exception as e:
                logger.error(f"Health check error: {e}")

            time.sleep(self.config.health_check_interval)

    def _check_gpu_health(self) -> bool:
        """Verifica se a GPU está saudável"""
        if not self.gpu_instance_id:
            return False

        try:
            status = self.vast_service.get_instance_status(self.gpu_instance_id)
            is_healthy = status.get('status') == 'running'
            if not is_healthy:
                logger.debug(f"GPU {self.gpu_instance_id} unhealthy: status={status.get('status')}")
            return is_healthy
        except (RequestException, ValueError, KeyError) as e:
            logger.error(f"Error checking GPU health: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking GPU health: {e}")
            return False

    def _backup_loop(self):
        """Loop de backup CPU → R2"""
        while self._running:
            try:
                if self.cpu_instance and self.state == StandbyState.SYNCING:
                    self._do_backup_to_r2()
                    self.last_backup_time = datetime.now()
            except Exception as e:
                logger.error(f"Backup error: {e}")

            time.sleep(self.config.r2_backup_interval)

    def _do_backup_to_r2(self):
        """Executa backup da CPU para R2"""
        if not self.snapshot_service or not self.cpu_instance:
            return

        cpu_ip = self.cpu_instance.get('external_ip')
        if not cpu_ip:
            return

        logger.info("Backing up CPU standby to R2")

        # Usar s5cmd na CPU para fazer upload direto para R2
        backup_cmd = f"""
cd {self.config.sync_path} && \
tar -czf /tmp/standby_backup.tar.gz . && \
s5cmd --endpoint-url={self.config.r2_endpoint} cp /tmp/standby_backup.tar.gz s3://{self.config.r2_bucket}/standby/latest.tar.gz && \
rm /tmp/standby_backup.tar.gz && \
echo "Backup completed"
"""

        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            f"root@{cpu_ip}",
            backup_cmd
        ]

        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            logger.info("Backup to R2 completed")
        else:
            logger.warning(f"Backup failed: {result.stderr[:200]}")

    def trigger_failover(self) -> Dict[str, Any]:
        """
        Executa failover para a CPU standby.
        A CPU assume como principal até uma nova GPU ser provisionada.

        Returns:
            Dict com informações do failover
        """
        logger.warning("FAILOVER: Switching to CPU standby")

        self.state = StandbyState.FAILOVER_ACTIVE

        if not self.cpu_instance:
            return {"error": "No CPU standby available"}

        cpu_ip = self.cpu_instance.get('external_ip')

        # Iniciar auto-recovery em background se configurado
        if self.config.auto_recovery:
            recovery_thread = threading.Thread(
                target=self._auto_recovery_loop,
                daemon=True
            )
            recovery_thread.start()
            logger.info("Auto-recovery thread started")

        return {
            "success": True,
            "message": "Failover to CPU standby activated",
            "active_endpoint": {
                "type": "cpu_standby",
                "ip": cpu_ip,
                "ssh_host": cpu_ip,
                "ssh_port": 22,
                "workspace": self.config.sync_path
            },
            "gpu_status": "offline",
            "auto_recovery": self.config.auto_recovery,
            "timestamp": datetime.now().isoformat()
        }

    def _auto_recovery_loop(self):
        """
        Loop de auto-recovery: provisiona nova GPU automaticamente após failover.
        Roda em background até conseguir uma nova GPU.
        """
        logger.info("Starting auto-recovery process...")
        self.state = StandbyState.RECOVERING

        max_attempts = 10
        attempt = 0

        while attempt < max_attempts and self.state == StandbyState.RECOVERING:
            attempt += 1
            logger.info(f"Auto-recovery attempt {attempt}/{max_attempts}")

            try:
                # 1. Buscar GPU disponível
                new_gpu = self._find_available_gpu()
                if not new_gpu:
                    logger.warning("No suitable GPU found, waiting 30s...")
                    time.sleep(30)
                    continue

                logger.info(f"Found GPU: {new_gpu.get('gpu_name')} at ${new_gpu.get('dph_total'):.2f}/hr")

                # 2. Criar instância
                offer_id = new_gpu.get('id')
                result = self.vast_service.create_instance(
                    offer_id=offer_id,
                    image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
                    disk_size=50,
                    ssh=True
                )

                if not result.get('success'):
                    logger.error(f"Failed to create instance: {result}")
                    time.sleep(30)
                    continue

                new_instance_id = result.get('new_contract')
                logger.info(f"Created new GPU instance: {new_instance_id}")

                # 3. Aguardar instância ficar pronta
                if not self._wait_for_instance_ready(new_instance_id, timeout=300):
                    logger.error(f"Instance {new_instance_id} did not become ready")
                    self.vast_service.destroy_instance(new_instance_id)
                    time.sleep(30)
                    continue

                # 4. Restaurar dados da CPU para nova GPU
                restore_result = self.restore_to_gpu(new_instance_id)
                if restore_result.get('error'):
                    logger.error(f"Failed to restore: {restore_result}")
                    continue

                logger.info(f"✅ Auto-recovery complete! New GPU: {new_instance_id}")
                self.state = StandbyState.SYNCING
                return

            except Exception as e:
                logger.error(f"Auto-recovery error: {e}")
                time.sleep(30)

        logger.error("Auto-recovery failed after max attempts")
        self.state = StandbyState.FAILOVER_ACTIVE

    def _find_available_gpu(self) -> Optional[Dict[str, Any]]:
        """
        Busca GPU disponível no Vast.ai com os critérios configurados.
        Prioriza regiões preferidas.
        """
        try:
            # Buscar ofertas
            offers = self.vast_service.search_offers(
                gpu_ram_min=self.config.gpu_min_ram,
                max_price=self.config.gpu_max_price,
                rentable=True
            )

            if not offers:
                return None

            # Ordenar por região preferida e preço
            def score_offer(offer):
                geo = offer.get('geolocation', '')
                price = offer.get('dph_total', 999)

                # Pontuação por região (menor = melhor)
                region_score = 100
                for i, region in enumerate(self.config.gpu_preferred_regions):
                    if region in geo:
                        region_score = i
                        break

                return (region_score, price)

            offers.sort(key=score_offer)
            return offers[0] if offers else None

        except Exception as e:
            logger.error(f"Error finding GPU: {e}")
            return None

    def _wait_for_instance_ready(self, instance_id: int, timeout: int = 300) -> bool:
        """Aguarda instância ficar pronta com SSH disponível"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                status = self.vast_service.get_instance_status(instance_id)
                if status and status.get('actual_status') == 'running':
                    ssh_host = status.get('ssh_host')
                    ssh_port = status.get('ssh_port')
                    if ssh_host and ssh_port:
                        # Testar conexão SSH
                        logger.info(f"Instance {instance_id} ready at {ssh_host}:{ssh_port}")
                        time.sleep(10)  # Dar tempo para SSH iniciar
                        return True
            except (RequestException, ValueError, KeyError, TypeError) as e:
                logger.debug(f"Instance {instance_id} not yet ready: {e}")
            except Exception as e:
                logger.error(f"Unexpected error waiting for instance {instance_id}: {e}")

            time.sleep(5)

        logger.error(f"Timeout waiting for instance {instance_id} to be ready")
        return False

    def restore_to_gpu(self, new_gpu_instance_id: int) -> Dict[str, Any]:
        """
        Restaura dados da CPU standby para uma nova GPU.

        Args:
            new_gpu_instance_id: ID da nova instância GPU

        Returns:
            Dict com resultado da restauração
        """
        if not self.cpu_instance:
            return {"error": "No CPU standby available"}

        # Registrar nova GPU
        if not self.register_gpu_instance(new_gpu_instance_id):
            return {"error": "Failed to register new GPU instance"}

        # Sync reverso: CPU → GPU
        cpu_ip = self.cpu_instance.get('external_ip')
        ssh_key = os.path.expanduser("~/.ssh/id_rsa")

        # Build SSH command for rsync (CPU → GPU)
        # Note: rsync can only use one -e SSH command, so we use a relay approach
        # We need to first pull from CPU to local /tmp, then push to GPU

        # Step 1: Pull from CPU
        rsync_cmd_cpu = [
            "rsync", "-avz", "--delete",
            "-e", f"ssh -o StrictHostKeyChecking=no -i {ssh_key}",
            f"root@{cpu_ip}:{self.config.sync_path}/",
            "/tmp/dumont-restore-relay/",
        ]

        logger.info(f"Pulling data from CPU standby...")
        result = subprocess.run(rsync_cmd_cpu, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            logger.error(f"Failed to pull from CPU: {result.stderr}")
            return {
                "success": False,
                "message": f"Failed to pull data from CPU: {result.stderr}",
                "timestamp": datetime.now().isoformat()
            }

        # Step 2: Push to new GPU
        ssh_opts = f"ssh -o StrictHostKeyChecking=no -i {ssh_key} -p {self.gpu_ssh_port}"
        rsync_cmd_gpu = [
            "rsync", "-avz", "--delete",
            "-e", ssh_opts,
            "/tmp/dumont-restore-relay/",
            f"root@{self.gpu_ssh_host}:{self.config.sync_path}/"
        ]

        logger.info(f"Pushing data to new GPU {new_gpu_instance_id}...")

        result = subprocess.run(rsync_cmd_gpu, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            self.state = StandbyState.SYNCING
            self.failed_health_checks = 0

            logger.info(f"✓ Data restored successfully to GPU {new_gpu_instance_id}")

            # Limparcache local de restore
            try:
                import shutil
                shutil.rmtree("/tmp/dumont-restore-relay/", ignore_errors=True)
                logger.debug("Cleaned up restore cache directory")
            except (OSError, TypeError) as e:
                logger.warning(f"Failed to cleanup restore cache: {e}")

            return {
                "success": True,
                "message": "Restored to new GPU",
                "gpu_instance_id": new_gpu_instance_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"✗ Restore failed: {result.stderr}")
            return {
                "success": False,
                "error": f"Restore failed: {result.stderr[:200]}",
                "timestamp": datetime.now().isoformat()
            }

    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema de standby"""
        return {
            "state": self.state.value,
            "cpu_standby": {
                "provisioned": self.cpu_instance is not None,
                "name": self.cpu_instance.get('name') if self.cpu_instance else None,
                "ip": self.cpu_instance.get('external_ip') if self.cpu_instance else None,
                "zone": self.cpu_instance.get('zone') if self.cpu_instance else None,
            },
            "gpu_instance": {
                "id": self.gpu_instance_id,
                "ssh_host": self.gpu_ssh_host,
                "ssh_port": self.gpu_ssh_port,
                "healthy": self.failed_health_checks == 0
            },
            "sync": {
                "running": self._running,
                "count": self.sync_count,
                "last_sync": self.last_sync_time.isoformat() if self.last_sync_time else None,
                "interval_seconds": self.config.sync_interval_seconds
            },
            "backup": {
                "enabled": self.snapshot_service is not None,
                "last_backup": self.last_backup_time.isoformat() if self.last_backup_time else None,
                "interval_seconds": self.config.r2_backup_interval
            },
            "failover": {
                "auto_enabled": self.config.auto_failover,
                "threshold": self.config.failover_threshold,
                "failed_checks": self.failed_health_checks
            }
        }

    def get_active_endpoint(self) -> Optional[Dict[str, Any]]:
        """
        Retorna o endpoint ativo atual (GPU ou CPU).
        Use isso para redirecionar tráfego de forma transparente.
        """
        if self.state == StandbyState.FAILOVER_ACTIVE:
            # CPU está ativa
            if self.cpu_instance:
                return {
                    "type": "cpu_standby",
                    "host": self.cpu_instance.get('external_ip'),
                    "port": 22,
                    "status": "active"
                }
        elif self.gpu_instance_id and self.failed_health_checks == 0:
            # GPU está ativa
            return {
                "type": "gpu",
                "host": self.gpu_ssh_host,
                "port": self.gpu_ssh_port,
                "instance_id": self.gpu_instance_id,
                "status": "active"
            }

        return None

    def cleanup(self):
        """Limpa recursos (para VM, para threads)"""
        logger.info("Cleaning up CPU standby service")

        self.stop_sync()

        if self.cpu_instance:
            name = self.cpu_instance.get('name')
            zone = self.cpu_instance.get('zone')
            if name and zone:
                self.gcp_provider.delete_instance(name, zone)
                self.cpu_instance = None

        self.state = StandbyState.DISABLED
