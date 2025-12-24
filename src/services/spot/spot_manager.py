"""
Spot GPU Manager - Deploy e failover de instâncias spot

Instâncias spot são 60-70% mais baratas que on-demand,
mas podem ser interrompidas se outro usuário fizer bid maior.

Estratégia:
1. Cria template (snapshot) numa região
2. Deploy via bidding no preço mais barato
3. Monitor detecta interrupções
4. Failover automático restaura do template

Economia esperada: ~70% vs on-demand
Recovery time: ~30s (snapshot restore)
"""
import os
import json
import logging
import threading
import time
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Arquivo de configuração persistente
CONFIG_FILE = os.path.expanduser("~/.dumont_spot.json")


class SpotState(str, Enum):
    """Estados de uma instância spot"""
    ACTIVE = "active"           # Rodando normalmente
    INTERRUPTED = "interrupted"  # Detectou interrupção
    FAILOVER = "failover"       # Executando failover
    FAILED = "failed"           # Failover falhou
    STOPPED = "stopped"         # Parada pelo usuário


@dataclass
class SpotTemplate:
    """Template (snapshot) para restore rápido"""
    template_id: str
    instance_id: int
    region: str
    gpu_name: str
    created_at: str
    workspace_path: str
    size_bytes: int = 0
    snapshot_path: str = ""  # Path no B2/R2


@dataclass
class SpotConfig:
    """Configuração de uma instância spot"""
    instance_id: int
    template_id: str              # Template para restore
    region: str                   # Região do template
    max_price: float = 1.0        # Preço máximo para bid
    gpu_preference: Optional[str] = None  # GPU preferida
    auto_failover: bool = True    # Failover automático

    # Estado atual
    state: SpotState = SpotState.ACTIVE
    current_bid_price: float = 0.0
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None

    # Histórico
    failover_count: int = 0
    last_failover_at: Optional[str] = None
    total_savings_usd: float = 0.0
    created_at: Optional[str] = None


class InterruptionMonitor:
    """
    Monitora instâncias spot para detectar interrupções.

    VAST.ai não tem webhooks, então usamos polling.
    Quando detecta interrupção, dispara failover.
    """

    POLL_INTERVAL = 10  # segundos

    def __init__(self, spot_manager: 'SpotManager'):
        self.spot_manager = spot_manager
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia monitoramento em background"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="SpotInterruptionMonitor"
        )
        self._thread.start()
        logger.info("InterruptionMonitor started")

    def stop(self):
        """Para monitoramento"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("InterruptionMonitor stopped")

    def _monitor_loop(self):
        """Loop principal de monitoramento"""
        while self._running:
            try:
                self._check_all_instances()
            except Exception as e:
                logger.error(f"Monitor error: {e}")

            time.sleep(self.POLL_INTERVAL)

    def _check_all_instances(self):
        """Verifica todas as instâncias spot ativas"""
        for instance_id, config in list(self.spot_manager._configs.items()):
            if config.state == SpotState.ACTIVE:
                self._check_instance(instance_id, config)

    def _check_instance(self, instance_id: int, config: SpotConfig):
        """Verifica status de uma instância específica"""
        try:
            provider = self.spot_manager._get_provider()
            if not provider:
                return

            instance = provider.get_instance(instance_id)

            # Detecta interrupção
            actual_status = getattr(instance, 'actual_status', 'unknown')
            intended_status = getattr(instance, 'status', 'unknown')

            if actual_status in ["exited", "offline", "stopped", "error"]:
                if intended_status == "running":
                    # Estava rodando, parou inesperadamente = interrupção
                    logger.warning(f"Spot instance {instance_id} interrupted! "
                                  f"actual={actual_status}, intended={intended_status}")
                    self.spot_manager._on_interruption(instance_id)

        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg:
                # Instância não existe mais - foi interrompida
                logger.warning(f"Spot instance {instance_id} no longer exists!")
                self.spot_manager._on_interruption(instance_id)
            else:
                logger.debug(f"Error checking instance {instance_id}: {e}")


class SpotManager:
    """
    Gerenciador de GPU Spot.

    Gerencia deploy, monitoramento e failover de instâncias spot.
    Singleton thread-safe.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._configs: Dict[int, SpotConfig] = {}
        self._templates: Dict[str, SpotTemplate] = {}
        self._vast_api_key: Optional[str] = None
        self._monitor: Optional[InterruptionMonitor] = None
        self._failover_in_progress: set = set()

        # Carrega configurações salvas
        self._load_configs()

        logger.info("SpotManager initialized")

    def configure(self, vast_api_key: str):
        """Configura API key do VAST.ai"""
        self._vast_api_key = vast_api_key

    def _get_provider(self):
        """Retorna VastProvider configurado"""
        if not self._vast_api_key:
            return None

        from ...infrastructure.providers import VastProvider
        return VastProvider(api_key=self._vast_api_key)

    # ==========================================
    # Template Management
    # ==========================================

    def create_template(
        self,
        instance_id: int,
        region: Optional[str] = None,
        workspace_path: str = "/workspace",
    ) -> Dict[str, Any]:
        """
        Cria template (snapshot) de uma instância para uso em spot.

        Args:
            instance_id: ID da instância fonte
            region: Região para o template (auto-detecta se None)
            workspace_path: Path do workspace a salvar

        Returns:
            Informações do template criado
        """
        logger.info(f"Creating spot template from instance {instance_id}")

        provider = self._get_provider()
        if not provider:
            return {"error": "VAST API key not configured"}

        # Obter detalhes da instância
        try:
            instance = provider.get_instance(instance_id)
        except Exception as e:
            return {"error": f"Instance not found: {e}"}

        # Auto-detectar região
        if not region:
            region = getattr(instance, 'geolocation', 'global') or 'global'

        # Criar snapshot
        template_id = f"spot_tpl_{instance_id}_{int(time.time())}"

        try:
            # Usar serviço de snapshot existente
            from ..gpu.snapshot import GPUSnapshotService
            from ...core.config import get_settings

            settings = get_settings()
            snapshot_svc = GPUSnapshotService(
                r2_endpoint=settings.storage.r2_endpoint or "",
                r2_bucket=settings.storage.r2_bucket or "dumont-snapshots",
            )

            snapshot_result = snapshot_svc.create_snapshot(
                instance_id=str(instance_id),
                ssh_host=instance.ssh_host or instance.public_ipaddr,
                ssh_port=instance.ssh_port or 22,
                workspace_path=workspace_path,
                snapshot_name=template_id,
            )

            # Criar template
            template = SpotTemplate(
                template_id=template_id,
                instance_id=instance_id,
                region=region,
                gpu_name=getattr(instance, 'gpu_name', 'Unknown'),
                created_at=datetime.utcnow().isoformat(),
                workspace_path=workspace_path,
                size_bytes=snapshot_result.get('size_original', 0),
                snapshot_path=snapshot_result.get('r2_path', ''),
            )

            self._templates[template_id] = template
            self._save_configs()

            logger.info(f"Created spot template {template_id} in region {region}")

            return {
                "template_id": template_id,
                "region": region,
                "gpu_name": template.gpu_name,
                "size_bytes": template.size_bytes,
                "snapshot_path": template.snapshot_path,
            }

        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            return {"error": f"Failed to create snapshot: {e}"}

    def list_templates(self) -> List[Dict[str, Any]]:
        """Lista todos os templates disponíveis"""
        return [asdict(t) for t in self._templates.values()]

    def delete_template(self, template_id: str) -> Dict[str, Any]:
        """Deleta um template"""
        if template_id not in self._templates:
            return {"error": "Template not found"}

        # TODO: Deletar do B2/R2 também
        del self._templates[template_id]
        self._save_configs()

        return {"status": "deleted", "template_id": template_id}

    # ==========================================
    # Spot Deploy
    # ==========================================

    def deploy(
        self,
        template_id: str,
        max_price: float = 1.0,
        gpu_preference: Optional[str] = None,
        auto_failover: bool = True,
    ) -> Dict[str, Any]:
        """
        Deploy de instância spot usando template.

        1. Busca GPUs disponíveis na região do template
        2. Filtra por preço (min_bid <= max_price)
        3. Faz bid na GPU mais barata
        4. Restaura snapshot do template
        5. Inicia monitoramento de interrupção

        Args:
            template_id: ID do template a usar
            max_price: Preço máximo por hora
            gpu_preference: GPU preferida (opcional)
            auto_failover: Se True, failover automático quando interrompido

        Returns:
            Detalhes da instância criada
        """
        logger.info(f"Deploying spot instance from template {template_id}")

        # Validar template
        if template_id not in self._templates:
            return {"error": f"Template {template_id} not found"}

        template = self._templates[template_id]

        provider = self._get_provider()
        if not provider:
            return {"error": "VAST API key not configured"}

        # Buscar ofertas spot na região
        offers = provider.get_interruptible_offers(
            region=template.region,
            gpu_name=gpu_preference,
            max_price=max_price,
        )

        if not offers:
            return {
                "error": f"No spot offers available in {template.region} for max ${max_price}/hr"
            }

        # Pegar a oferta mais barata
        best_offer = offers[0]
        bid_price = best_offer.min_bid or max_price * 0.9

        logger.info(f"Best offer: {best_offer.gpu_name} at ${bid_price:.4f}/hr")

        # Criar instância via bid
        try:
            instance = provider.create_instance_bid(
                offer_id=best_offer.offer_id,
                image="ollama/ollama",  # Imagem leve
                disk_size=50,
                bid_price=bid_price,
                label=f"spot_{template_id}",
            )

            # Aguardar SSH disponível
            ssh_host = None
            ssh_port = None

            for _ in range(60):  # 60 tentativas = ~2 min
                time.sleep(2)
                try:
                    inst = provider.get_instance(instance.id)
                    if getattr(inst, 'ssh_host', None) and getattr(inst, 'ssh_port', None):
                        ssh_host = inst.ssh_host
                        ssh_port = inst.ssh_port
                        break
                except:
                    pass

            if not ssh_host:
                return {"error": "Instance created but SSH not available"}

            # Restaurar snapshot
            restore_result = self._restore_snapshot(
                template=template,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
            )

            if "error" in restore_result:
                logger.warning(f"Snapshot restore failed: {restore_result['error']}")
                # Continua mesmo sem restore (instância ainda é útil)

            # Criar config e iniciar monitoramento
            config = SpotConfig(
                instance_id=instance.id,
                template_id=template_id,
                region=template.region,
                max_price=max_price,
                gpu_preference=gpu_preference,
                auto_failover=auto_failover,
                state=SpotState.ACTIVE,
                current_bid_price=bid_price,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                created_at=datetime.utcnow().isoformat(),
            )

            self._configs[instance.id] = config
            self._save_configs()

            # Iniciar monitor se não estiver rodando
            self._ensure_monitor_running()

            logger.info(f"Spot instance {instance.id} deployed successfully")

            return {
                "instance_id": instance.id,
                "gpu_name": best_offer.gpu_name,
                "bid_price": bid_price,
                "ssh_host": ssh_host,
                "ssh_port": ssh_port,
                "region": template.region,
                "template_id": template_id,
                "snapshot_restored": "error" not in restore_result,
            }

        except Exception as e:
            logger.error(f"Failed to deploy spot instance: {e}")
            return {"error": f"Deployment failed: {e}"}

    def _restore_snapshot(
        self,
        template: SpotTemplate,
        ssh_host: str,
        ssh_port: int,
    ) -> Dict[str, Any]:
        """Restaura snapshot do template na instância"""
        try:
            from ..gpu.snapshot import GPUSnapshotService
            from ...core.config import get_settings

            settings = get_settings()
            snapshot_svc = GPUSnapshotService(
                r2_endpoint=settings.storage.r2_endpoint or "",
                r2_bucket=settings.storage.r2_bucket or "dumont-snapshots",
            )

            result = snapshot_svc.restore_snapshot(
                snapshot_id=template.template_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                workspace_path=template.workspace_path,
            )

            return result

        except Exception as e:
            return {"error": str(e)}

    # ==========================================
    # Interruption Handling
    # ==========================================

    def _on_interruption(self, instance_id: int):
        """Chamado quando instância spot é interrompida"""
        if instance_id not in self._configs:
            return

        if instance_id in self._failover_in_progress:
            return  # Já está em failover

        config = self._configs[instance_id]
        config.state = SpotState.INTERRUPTED

        logger.warning(f"Spot instance {instance_id} interrupted!")

        if config.auto_failover:
            self._execute_failover(instance_id)

    def _execute_failover(self, instance_id: int):
        """Executa failover para nova GPU"""
        if instance_id not in self._configs:
            return

        self._failover_in_progress.add(instance_id)
        config = self._configs[instance_id]
        config.state = SpotState.FAILOVER

        logger.info(f"Executing failover for instance {instance_id}")

        try:
            # Buscar novo spot
            result = self.deploy(
                template_id=config.template_id,
                max_price=config.max_price,
                gpu_preference=config.gpu_preference,
                auto_failover=True,
            )

            if "error" in result:
                logger.error(f"Failover failed: {result['error']}")
                config.state = SpotState.FAILED
                return

            # Sucesso - atualizar config
            new_instance_id = result["instance_id"]
            config.failover_count += 1
            config.last_failover_at = datetime.utcnow().isoformat()

            # Remover config antiga, nova já foi criada pelo deploy
            del self._configs[instance_id]

            self._save_configs()

            logger.info(f"Failover complete: {instance_id} -> {new_instance_id}")

        except Exception as e:
            logger.error(f"Failover error: {e}")
            config.state = SpotState.FAILED
        finally:
            self._failover_in_progress.discard(instance_id)

    def trigger_failover(self, instance_id: int) -> Dict[str, Any]:
        """Trigger manual de failover (para testes)"""
        if instance_id not in self._configs:
            return {"error": "Instance not configured for spot"}

        self._on_interruption(instance_id)
        return {"status": "failover_triggered", "instance_id": instance_id}

    # ==========================================
    # Status & Management
    # ==========================================

    def get_status(self, instance_id: int) -> Optional[Dict[str, Any]]:
        """Retorna status de uma instância spot"""
        if instance_id not in self._configs:
            return None

        config = self._configs[instance_id]
        return {
            "instance_id": config.instance_id,
            "state": config.state.value,
            "template_id": config.template_id,
            "region": config.region,
            "bid_price": config.current_bid_price,
            "max_price": config.max_price,
            "auto_failover": config.auto_failover,
            "failover_count": config.failover_count,
            "last_failover_at": config.last_failover_at,
            "ssh_host": config.ssh_host,
            "ssh_port": config.ssh_port,
        }

    def list_instances(self) -> List[Dict[str, Any]]:
        """Lista todas as instâncias spot"""
        return [self.get_status(id) for id in self._configs.keys()]

    def stop(self, instance_id: int) -> Dict[str, Any]:
        """Para monitoramento de uma instância spot"""
        if instance_id not in self._configs:
            return {"error": "Instance not configured for spot"}

        config = self._configs[instance_id]
        config.state = SpotState.STOPPED
        config.auto_failover = False
        self._save_configs()

        return {"status": "stopped", "instance_id": instance_id}

    def remove(self, instance_id: int) -> Dict[str, Any]:
        """Remove instância do gerenciamento spot"""
        if instance_id not in self._configs:
            return {"error": "Instance not configured for spot"}

        del self._configs[instance_id]
        self._save_configs()

        return {"status": "removed", "instance_id": instance_id}

    # ==========================================
    # Monitor Management
    # ==========================================

    def _ensure_monitor_running(self):
        """Garante que o monitor está rodando"""
        if not self._monitor:
            self._monitor = InterruptionMonitor(self)

        if not self._monitor._running:
            self._monitor.start()

    def start_monitoring(self):
        """Inicia monitoramento de todas as instâncias spot"""
        self._ensure_monitor_running()

    def stop_monitoring(self):
        """Para monitoramento"""
        if self._monitor:
            self._monitor.stop()

    # ==========================================
    # Persistence
    # ==========================================

    def _load_configs(self):
        """Carrega configurações do arquivo"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)

                # Carregar templates
                for tpl_data in data.get("templates", []):
                    tpl = SpotTemplate(**tpl_data)
                    self._templates[tpl.template_id] = tpl

                # Carregar configs
                for cfg_data in data.get("configs", []):
                    cfg_data["state"] = SpotState(cfg_data.get("state", "active"))
                    cfg = SpotConfig(**cfg_data)
                    self._configs[cfg.instance_id] = cfg

                logger.info(f"Loaded {len(self._templates)} templates, {len(self._configs)} configs")

        except Exception as e:
            logger.warning(f"Failed to load spot configs: {e}")

    def _save_configs(self):
        """Salva configurações no arquivo"""
        try:
            data = {
                "templates": [asdict(t) for t in self._templates.values()],
                "configs": [],
            }

            for cfg in self._configs.values():
                cfg_dict = asdict(cfg)
                cfg_dict["state"] = cfg.state.value
                data["configs"].append(cfg_dict)

            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save spot configs: {e}")


# Singleton getter
def get_spot_manager() -> SpotManager:
    """Retorna instância única do SpotManager"""
    return SpotManager()
