"""
Serverless GPU Manager - Auto-pause/resume baseado em idle

Três modos:
1. FAST (CPU Standby): Estado sincronizado, recovery <1s
2. ECONOMIC (Pause/Resume): Usa pause nativo VAST.ai, recovery 5-15s
3. SPOT (Instâncias spot): 60-70% mais barato, failover ~30s

Tempos reais medidos (dezembro 2024):
- RTX A2000/5070: cold start ~5-7s
- RTX 4090: cold start ~14s
- Container REALMENTE para (SSH connection refused quando pausado)
- Processos NÃO sobrevivem - precisam de auto-start
- Storage é preservado

Modo SPOT:
- Usa instâncias interruptíveis (spot/bid)
- Quando interrompido, faz failover automático
- Requer template (snapshot) pré-configurado
- Recovery ~30s (buscar nova GPU + restaurar snapshot)

Integra com:
- DumontAgent heartbeat para GPU utilization
- StandbyManager para modo fast
- VastProvider pause/resume para modo economic
- SpotManager para modo spot
"""
import os
import json
import logging
import threading
import time
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ServerlessMode(Enum):
    """Modos de serverless disponíveis"""
    FAST = "fast"           # CPU Standby - recovery <1s, custo $0.01/hr idle
    ECONOMIC = "economic"   # Pause/Resume VAST.ai - recovery ~7s, custo ~$0.005/hr idle
    SPOT = "spot"           # Spot instances - mais barato, failover ~30s
    DISABLED = "disabled"   # Sem auto-pause


@dataclass
class ServerlessConfig:
    """Configuração serverless para uma instância"""
    instance_id: int
    mode: ServerlessMode = ServerlessMode.DISABLED
    idle_timeout_seconds: int = 10  # Pausa após X segundos idle
    gpu_threshold: float = 5.0      # % GPU utilization para considerar idle
    keep_warm: bool = False         # Se True, nunca pausa (override)
    min_runtime_seconds: int = 60   # Tempo mínimo antes de poder pausar

    # Estado
    is_paused: bool = False
    paused_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    idle_since: Optional[datetime] = None
    total_idle_time: float = 0      # Segundos totais em idle
    total_savings: float = 0        # USD economizado

    # Fallback configuration
    enable_fallback: bool = True         # Se resume falhar, provisionar nova GPU
    fallback_max_price: float = 1.0      # Preço máximo para fallback
    fallback_gpu_name: Optional[str] = None  # GPU preferida para fallback
    fallback_parallel: bool = True       # Lançar backup em paralelo ao resume
    resume_timeout: int = 60             # Timeout antes de declarar resume como falho
    ssh_verify_timeout: int = 30         # Timeout para verificar SSH
    last_snapshot_id: Optional[str] = None  # Snapshot para restaurar no fallback


@dataclass
class ServerlessStats:
    """Estatísticas de uso serverless"""
    instance_id: int
    mode: str
    is_paused: bool
    idle_timeout_seconds: int
    current_gpu_util: float
    idle_since: Optional[str]
    will_pause_at: Optional[str]
    pause_count: int = 0
    resume_count: int = 0
    total_idle_hours: float = 0
    total_savings_usd: float = 0
    avg_cold_start_seconds: float = 0


class ServerlessManager:
    """
    Gerenciador de GPU Serverless.

    Monitora GPU utilization e auto-pausa/resume baseado em configuração.
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
        self._configs: Dict[int, ServerlessConfig] = {}
        self._gpu_utils: Dict[int, float] = {}  # instance_id → last GPU %
        self._vast_provider = None
        self._standby_manager = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._check_interval = 5  # Checar a cada 5 segundos

        # Histórico para cold start timing
        self._resume_times: Dict[int, List[float]] = {}  # instance_id → [durations]

        # Carregar configurações salvas
        self._load_configs()

        logger.info("ServerlessManager initialized")

    def configure(self, vast_api_key: str):
        """Configura o manager com acesso ao VAST.ai"""
        from src.infrastructure.providers.vast_provider import VastProvider
        from src.services.standby.manager import get_standby_manager

        self._vast_provider = VastProvider(api_key=vast_api_key)
        self._standby_manager = get_standby_manager()

        logger.info("ServerlessManager configured with VAST provider")

    def enable(
        self,
        instance_id: int,
        mode: str = "economic",
        idle_timeout_seconds: int = 10,
        gpu_threshold: float = 5.0,
        keep_warm: bool = False
    ) -> Dict[str, Any]:
        """
        Habilita modo serverless para uma instância.

        Args:
            instance_id: ID da instância VAST.ai
            mode: "fast" (CPU standby) ou "economic" (pause/resume)
            idle_timeout_seconds: Segundos idle antes de pausar
            gpu_threshold: % GPU abaixo do qual considera idle
            keep_warm: Se True, nunca pausa automaticamente

        Returns:
            Dict com configuração aplicada
        """
        try:
            serverless_mode = ServerlessMode(mode)
        except ValueError:
            serverless_mode = ServerlessMode.ECONOMIC

        config = ServerlessConfig(
            instance_id=instance_id,
            mode=serverless_mode,
            idle_timeout_seconds=idle_timeout_seconds,
            gpu_threshold=gpu_threshold,
            keep_warm=keep_warm,
            last_activity=datetime.utcnow()
        )

        self._configs[instance_id] = config
        self._save_configs()

        # Iniciar monitor se não estiver rodando
        self._start_monitor()

        logger.info(f"Serverless enabled for {instance_id}: mode={mode}, timeout={idle_timeout_seconds}s")

        return {
            "instance_id": instance_id,
            "mode": mode,
            "idle_timeout_seconds": idle_timeout_seconds,
            "gpu_threshold": gpu_threshold,
            "keep_warm": keep_warm,
            "status": "enabled"
        }

    def disable(self, instance_id: int) -> Dict[str, Any]:
        """Desabilita modo serverless para uma instância"""
        if instance_id in self._configs:
            config = self._configs[instance_id]

            # Se estava pausado, resume primeiro
            if config.is_paused:
                self._resume_instance(instance_id, config)

            del self._configs[instance_id]
            self._save_configs()

            logger.info(f"Serverless disabled for {instance_id}")

            return {"instance_id": instance_id, "status": "disabled"}

        return {"instance_id": instance_id, "status": "not_found"}

    def update_gpu_utilization(self, instance_id: int, gpu_util: float):
        """
        Atualiza GPU utilization de uma instância.
        Chamado pelo DumontAgent heartbeat.
        """
        self._gpu_utils[instance_id] = gpu_util

        if instance_id in self._configs:
            config = self._configs[instance_id]

            # Se GPU está sendo usada, resetar idle
            if gpu_util >= config.gpu_threshold:
                config.idle_since = None
                config.last_activity = datetime.utcnow()

                # Se estava pausado, não deveria estar recebendo heartbeat
                # mas se receber, significa que foi resumido
                if config.is_paused:
                    config.is_paused = False
                    config.paused_at = None

    def on_inference_start(self, instance_id: int):
        """Chamado quando inferência começa - reseta idle timer"""
        if instance_id in self._configs:
            config = self._configs[instance_id]
            config.idle_since = None
            config.last_activity = datetime.utcnow()
            logger.debug(f"Inference started on {instance_id}, idle timer reset")

    def on_inference_complete(self, instance_id: int):
        """Chamado quando inferência termina - inicia idle timer"""
        if instance_id in self._configs:
            config = self._configs[instance_id]
            if config.idle_since is None:
                config.idle_since = datetime.utcnow()
                logger.debug(f"Inference complete on {instance_id}, idle timer started")

    def get_status(self, instance_id: int) -> Optional[ServerlessStats]:
        """Retorna status serverless de uma instância"""
        if instance_id not in self._configs:
            return None

        config = self._configs[instance_id]
        gpu_util = self._gpu_utils.get(instance_id, 0)

        # Calcular quando vai pausar
        will_pause_at = None
        if config.idle_since and not config.is_paused and not config.keep_warm:
            pause_time = config.idle_since + timedelta(seconds=config.idle_timeout_seconds)
            if pause_time > datetime.utcnow():
                will_pause_at = pause_time.isoformat()

        # Calcular média de cold start
        avg_cold_start = 0
        if instance_id in self._resume_times and self._resume_times[instance_id]:
            avg_cold_start = sum(self._resume_times[instance_id]) / len(self._resume_times[instance_id])

        return ServerlessStats(
            instance_id=instance_id,
            mode=config.mode.value,
            is_paused=config.is_paused,
            idle_timeout_seconds=config.idle_timeout_seconds,
            current_gpu_util=gpu_util,
            idle_since=config.idle_since.isoformat() if config.idle_since else None,
            will_pause_at=will_pause_at,
            total_idle_hours=config.total_idle_time / 3600,
            total_savings_usd=config.total_savings,
            avg_cold_start_seconds=avg_cold_start
        )

    def list_all(self) -> List[Dict[str, Any]]:
        """Lista todas as instâncias com serverless configurado"""
        result = []
        for instance_id, config in self._configs.items():
            status = self.get_status(instance_id)
            if status:
                result.append({
                    "instance_id": status.instance_id,
                    "mode": status.mode,
                    "is_paused": status.is_paused,
                    "idle_timeout_seconds": status.idle_timeout_seconds,
                    "current_gpu_util": status.current_gpu_util,
                    "will_pause_at": status.will_pause_at,
                    "total_savings_usd": status.total_savings_usd
                })
        return result

    def wake(self, instance_id: int, use_fallback: bool = True) -> Dict[str, Any]:
        """
        Acorda uma instância pausada (on-demand) com fallback automático.

        Se o resume falhar ou SSH não funcionar, automaticamente provisiona
        uma nova GPU e restaura o snapshot.

        Args:
            instance_id: ID da instância para acordar
            use_fallback: Se True, usa fallback para nova GPU se resume falhar

        Returns:
            Dict com status, tempo de wake, e info sobre qual método foi usado
        """
        if instance_id not in self._configs:
            return {"error": "Instance not configured for serverless"}

        config = self._configs[instance_id]

        if not config.is_paused:
            return {"instance_id": instance_id, "status": "already_running"}

        start_time = time.time()

        # Se fallback está habilitado, usar cold start strategy
        if use_fallback and config.enable_fallback:
            result = self._resume_with_failover(instance_id, config)
        else:
            # Modo simples sem fallback
            result = self._resume_instance_simple(instance_id, config)

        duration = time.time() - start_time

        if result.get("success"):
            # Registrar tempo de resume
            if instance_id not in self._resume_times:
                self._resume_times[instance_id] = []
            self._resume_times[instance_id].append(duration)
            self._resume_times[instance_id] = self._resume_times[instance_id][-10:]

            return {
                "instance_id": result.get("instance_id", instance_id),
                "status": "resumed",
                "cold_start_seconds": round(duration, 2),
                "mode": config.mode.value,
                "method": result.get("method", "resume"),  # "resume" or "fallback"
                "ssh_host": result.get("ssh_host"),
                "ssh_port": result.get("ssh_port"),
            }

        return {
            "instance_id": instance_id,
            "status": "failed",
            "error": result.get("error", "Resume failed"),
            "cold_start_seconds": round(duration, 2),
        }

    def wake_with_failover(
        self,
        instance_id: int,
        backup_gpu_name: Optional[str] = None,
        backup_max_price: float = 1.0,
        parallel_backup: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Acorda uma instância com failover garantido.

        Este método é recomendado para produção onde você precisa
        de garantia de que uma GPU estará disponível.

        Fluxo:
        1. Tenta resume da instância pausada
        2. Em paralelo (ou após timeout), lança backup GPU
        3. Primeiro com SSH funcionando vence
        4. Perdedor é destruído

        Args:
            instance_id: Instância a acordar
            backup_gpu_name: GPU preferida para backup (ex: "RTX 4090")
            backup_max_price: Preço máximo para backup
            parallel_backup: Se True, lança backup imediatamente em paralelo
            progress_callback: Callback para updates de progresso

        Returns:
            Dict com resultado (instance_id pode ser diferente se fallback venceu)
        """
        if instance_id not in self._configs:
            return {"error": "Instance not configured for serverless"}

        config = self._configs[instance_id]

        if not config.is_paused:
            return {"instance_id": instance_id, "status": "already_running"}

        # Atualizar config com parâmetros
        config.fallback_gpu_name = backup_gpu_name or config.fallback_gpu_name
        config.fallback_max_price = backup_max_price
        config.fallback_parallel = parallel_backup

        start_time = time.time()
        result = self._resume_with_failover(instance_id, config, progress_callback)
        duration = time.time() - start_time

        if result.get("success"):
            return {
                "instance_id": result.get("instance_id", instance_id),
                "status": "resumed",
                "cold_start_seconds": round(duration, 2),
                "mode": config.mode.value,
                "method": result.get("method", "unknown"),
                "ssh_host": result.get("ssh_host"),
                "ssh_port": result.get("ssh_port"),
                "gpu_name": result.get("gpu_name"),
            }

        return {
            "instance_id": instance_id,
            "status": "failed",
            "error": result.get("error", "Resume with failover failed"),
            "cold_start_seconds": round(duration, 2),
        }

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _start_monitor(self):
        """Inicia thread de monitoramento"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Serverless monitor thread started")

    def _stop_monitor(self):
        """Para thread de monitoramento"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)

    def _monitor_loop(self):
        """Loop principal de monitoramento"""
        while self._running:
            try:
                self._check_all_instances()
            except Exception as e:
                logger.error(f"Error in serverless monitor: {e}")

            time.sleep(self._check_interval)

    def _check_all_instances(self):
        """Verifica todas as instâncias configuradas"""
        now = datetime.utcnow()

        for instance_id, config in list(self._configs.items()):
            # Pular se keep_warm ou já pausado
            if config.keep_warm or config.is_paused:
                continue

            # Pular se modo desabilitado
            if config.mode == ServerlessMode.DISABLED:
                continue

            # Verificar se está idle
            gpu_util = self._gpu_utils.get(instance_id, 100)  # Default alto para não pausar sem dados

            if gpu_util < config.gpu_threshold:
                # Está idle
                if config.idle_since is None:
                    config.idle_since = now
                    logger.debug(f"Instance {instance_id} became idle (GPU: {gpu_util}%)")

                # Verificar se passou timeout
                idle_duration = (now - config.idle_since).total_seconds()

                if idle_duration >= config.idle_timeout_seconds:
                    # Verificar min_runtime
                    if config.last_activity:
                        runtime = (now - config.last_activity).total_seconds()
                        if runtime < config.min_runtime_seconds:
                            continue

                    logger.info(f"Instance {instance_id} idle for {idle_duration}s, pausing...")
                    self._pause_instance(instance_id, config)
            else:
                # Não está idle - resetar
                config.idle_since = None
                config.last_activity = now

    def _pause_instance(self, instance_id: int, config: ServerlessConfig) -> bool:
        """Pausa uma instância baseado no modo"""
        if not self._vast_provider:
            logger.error("VastProvider not configured")
            return False

        try:
            if config.mode == ServerlessMode.FAST:
                # Modo fast: Usa failover para CPU standby
                # GPU é pausada, mas estado já está no CPU
                success = self._vast_provider.pause_instance(instance_id)
                if success:
                    logger.info(f"[FAST] Instance {instance_id} paused (state on CPU standby)")

            elif config.mode == ServerlessMode.ECONOMIC:
                # Modo economic: Usa pause nativo VAST.ai
                success = self._vast_provider.pause_instance(instance_id)
                if success:
                    logger.info(f"[ECONOMIC] Instance {instance_id} paused via VAST.ai")
            else:
                return False

            if success:
                config.is_paused = True
                config.paused_at = datetime.utcnow()
                self._save_configs()

            return success

        except Exception as e:
            logger.error(f"Failed to pause instance {instance_id}: {e}")
            return False

    def _resume_instance_simple(self, instance_id: int, config: ServerlessConfig) -> Dict[str, Any]:
        """Resume simples sem fallback - retorna dict com resultado"""
        if not self._vast_provider:
            return {"success": False, "error": "VastProvider not configured"}

        try:
            success = self._vast_provider.resume_instance(instance_id)
            if not success:
                return {"success": False, "error": "Resume API call failed"}

            # Aguardar SSH ficar disponível
            ssh_ready = self._wait_for_ssh(instance_id, config.ssh_verify_timeout)
            if not ssh_ready:
                return {"success": False, "error": "SSH not ready after resume"}

            # Atualizar estado
            self._update_resume_state(config)

            # Obter info de conexão
            status = self._vast_provider.get_instance_status(instance_id)

            return {
                "success": True,
                "method": "resume",
                "instance_id": instance_id,
                "ssh_host": status.get("ssh_host"),
                "ssh_port": status.get("ssh_port"),
            }

        except Exception as e:
            logger.error(f"Failed to resume instance {instance_id}: {e}")
            return {"success": False, "error": str(e)}

    def _resume_with_failover(
        self,
        instance_id: int,
        config: ServerlessConfig,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Resume com fallback automático usando ColdStartStrategy.

        Fluxo:
        1. Tenta resume da instância
        2. Em paralelo (se configurado), provisiona backup
        3. Primeiro com SSH funcionando vence
        4. Perdedor é destruído
        """
        try:
            # Import cold start strategy
            from src.services.gpu.strategies.coldstart import ColdStartStrategy, ColdStartConfig
            from src.services.gpu.strategies.base import ProvisionConfig

            def report_progress(status: str, message: str, progress: int = 0):
                if progress_callback:
                    progress_callback(status, message, progress)
                logger.info(f"[Serverless Wake] {status}: {message}")

            report_progress("starting", f"Waking instance {instance_id}...", 5)

            # Criar backup config se fallback está habilitado
            backup_config = None
            if config.enable_fallback:
                backup_config = ProvisionConfig(
                    gpu_name=config.fallback_gpu_name,
                    max_price=config.fallback_max_price,
                    disk_space=50,
                    label="dumont:serverless-fallback",
                )

            # Criar cold start config
            coldstart_config = ColdStartConfig(
                instance_id=instance_id,
                backup_config=backup_config,
                parallel_backup=config.fallback_parallel,
                resume_timeout=config.resume_timeout,
                total_timeout=180,  # 3 minutos máximo
                ssh_timeout=config.ssh_verify_timeout,
            )

            # Executar cold start com failover
            strategy = ColdStartStrategy()

            # Criar VastService wrapper
            vast_service = self._create_vast_service_wrapper()

            result = strategy.resume_with_failover(
                coldstart_config=coldstart_config,
                vast_service=vast_service,
                progress_callback=progress_callback,
            )

            if result.success:
                # Determinar qual método venceu
                method = "resume" if result.instance_id == instance_id else "fallback"

                # Se fallback venceu, atualizar config para nova instância
                if method == "fallback":
                    report_progress("fallback", f"Fallback won! New instance: {result.instance_id}", 95)
                    # Atualizar configuração para nova instância
                    new_config = ServerlessConfig(
                        instance_id=result.instance_id,
                        mode=config.mode,
                        idle_timeout_seconds=config.idle_timeout_seconds,
                        gpu_threshold=config.gpu_threshold,
                        keep_warm=config.keep_warm,
                        min_runtime_seconds=config.min_runtime_seconds,
                        enable_fallback=config.enable_fallback,
                        fallback_max_price=config.fallback_max_price,
                        fallback_gpu_name=config.fallback_gpu_name,
                        fallback_parallel=config.fallback_parallel,
                    )
                    # Remover config antiga
                    if instance_id in self._configs:
                        del self._configs[instance_id]
                    # Adicionar nova
                    self._configs[result.instance_id] = new_config
                    self._save_configs()
                else:
                    # Resume venceu, atualizar estado
                    self._update_resume_state(config)

                report_progress("ready", f"Instance ready via {method}!", 100)

                return {
                    "success": True,
                    "method": method,
                    "instance_id": result.instance_id,
                    "ssh_host": result.ssh_host,
                    "ssh_port": result.ssh_port,
                    "gpu_name": result.gpu_name,
                }

            return {
                "success": False,
                "error": result.error or "Cold start failed",
            }

        except ImportError as e:
            logger.warning(f"ColdStartStrategy not available, falling back to simple resume: {e}")
            return self._resume_instance_simple(instance_id, config)
        except Exception as e:
            logger.error(f"Resume with failover failed: {e}")
            return {"success": False, "error": str(e)}

    def _create_vast_service_wrapper(self):
        """Cria wrapper do VastProvider que implementa interface esperada pelo ColdStartStrategy"""
        provider = self._vast_provider

        class VastServiceWrapper:
            def __init__(self, provider):
                self._provider = provider

            def resume_instance(self, instance_id: int) -> bool:
                return self._provider.resume_instance(instance_id)

            def get_instance_status(self, instance_id: int) -> Dict[str, Any]:
                return self._provider.get_instance_status(instance_id)

            def destroy_instance(self, instance_id: int) -> bool:
                return self._provider.destroy_instance(instance_id)

            def search_offers(self, **kwargs):
                return self._provider.search_offers(**kwargs)

            def create_instance(self, offer_id: int, **kwargs):
                return self._provider.create_instance(offer_id, **kwargs)

        return VastServiceWrapper(provider)

    def _update_resume_state(self, config: ServerlessConfig):
        """Atualiza estado após resume bem-sucedido"""
        if config.paused_at:
            idle_seconds = (datetime.utcnow() - config.paused_at).total_seconds()
            config.total_idle_time += idle_seconds

            # Estimar economia (assumindo $0.30/hr GPU)
            hourly_rate = 0.30
            idle_cost = 0.01 if config.mode == ServerlessMode.FAST else 0.005
            savings = (hourly_rate - idle_cost) * (idle_seconds / 3600)
            config.total_savings += savings

        config.is_paused = False
        config.paused_at = None
        config.idle_since = None
        config.last_activity = datetime.utcnow()
        self._save_configs()

    def _wait_for_ssh(self, instance_id: int, timeout: int = 30) -> bool:
        """Aguarda SSH ficar disponível após resume"""
        import subprocess

        start = time.time()
        while time.time() - start < timeout:
            try:
                status = self._vast_provider.get_instance_status(instance_id)
                if status.get("actual_status") != "running":
                    time.sleep(2)
                    continue

                ssh_host = status.get("ssh_host")
                ssh_port = status.get("ssh_port")

                if not ssh_host or not ssh_port:
                    time.sleep(2)
                    continue

                # Testar SSH com comando real
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null",
                        "-o", "ConnectTimeout=5",
                        "-o", "BatchMode=yes",
                        "-p", str(ssh_port),
                        f"root@{ssh_host}",
                        "echo SSH_OK"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0 and "SSH_OK" in result.stdout:
                    return True

            except Exception as e:
                logger.debug(f"SSH check failed: {e}")

            time.sleep(2)

        return False

    def _resume_instance(self, instance_id: int, config: ServerlessConfig) -> bool:
        """Resume uma instância baseado no modo (legacy wrapper)"""
        result = self._resume_instance_simple(instance_id, config)
        return result.get("success", False)

    def _save_configs(self):
        """Salva configurações em arquivo"""
        config_file = os.path.expanduser("~/.dumont_serverless.json")
        try:
            data = {}
            for instance_id, config in self._configs.items():
                data[str(instance_id)] = {
                    "mode": config.mode.value,
                    "idle_timeout_seconds": config.idle_timeout_seconds,
                    "gpu_threshold": config.gpu_threshold,
                    "keep_warm": config.keep_warm,
                    "min_runtime_seconds": config.min_runtime_seconds,
                    "is_paused": config.is_paused,
                    "total_idle_time": config.total_idle_time,
                    "total_savings": config.total_savings
                }

            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save serverless configs: {e}")

    def _load_configs(self):
        """Carrega configurações de arquivo"""
        config_file = os.path.expanduser("~/.dumont_serverless.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    data = json.load(f)

                for instance_id_str, cfg in data.items():
                    instance_id = int(instance_id_str)
                    self._configs[instance_id] = ServerlessConfig(
                        instance_id=instance_id,
                        mode=ServerlessMode(cfg.get("mode", "disabled")),
                        idle_timeout_seconds=cfg.get("idle_timeout_seconds", 10),
                        gpu_threshold=cfg.get("gpu_threshold", 5.0),
                        keep_warm=cfg.get("keep_warm", False),
                        min_runtime_seconds=cfg.get("min_runtime_seconds", 60),
                        is_paused=cfg.get("is_paused", False),
                        total_idle_time=cfg.get("total_idle_time", 0),
                        total_savings=cfg.get("total_savings", 0)
                    )

                logger.info(f"Loaded {len(self._configs)} serverless configs")

        except Exception as e:
            logger.error(f"Failed to load serverless configs: {e}")


# Singleton accessor
_serverless_manager: Optional[ServerlessManager] = None

def get_serverless_manager() -> ServerlessManager:
    """Retorna instância singleton do ServerlessManager"""
    global _serverless_manager
    if _serverless_manager is None:
        _serverless_manager = ServerlessManager()
    return _serverless_manager
