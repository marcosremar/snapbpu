"""
Serverless GPU Manager

Gerencia auto-pause/resume de GPUs baseado em idle, com suporte a checkpoint
de estado para recovery ultra-rápido.

Modos:
1. FAST (CPU Standby + Checkpoint): Estado salvo via CRIU, recovery <1s
2. ECONOMIC (Pause/Resume): Usa pause nativo VAST.ai, recovery ~7s
3. SPOT (Instâncias spot): 60-70% mais barato, failover ~30s

Integração com GPU Checkpoint:
- No modo FAST, cria checkpoint antes de pausar
- No wake, restaura processo direto do checkpoint
- Elimina necessidade de reiniciar aplicação/modelo
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .config import ServerlessMode, InstanceServerlessConfig, get_settings

logger = logging.getLogger(__name__)


# Re-export para manter compatibilidade
ServerlessConfig = InstanceServerlessConfig


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
    last_checkpoint_id: Optional[str] = None


class ServerlessManager:
    """
    Gerenciador de GPU Serverless.

    Monitora GPU utilization e auto-pausa/resume baseado em configuração.
    Integra com GPUCheckpointService para preservar estado de memória.

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
        self._configs: Dict[int, InstanceServerlessConfig] = {}
        self._gpu_utils: Dict[int, float] = {}
        self._vast_provider = None
        self._checkpoint_service = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False

        # Histórico para cold start timing
        self._resume_times: Dict[int, List[float]] = {}
        self._pause_counts: Dict[int, int] = {}
        self._resume_counts: Dict[int, int] = {}

        # Carregar configurações salvas
        self._load_configs()

        logger.info("ServerlessManager initialized")

    def configure(self, vast_api_key: str, enable_checkpoint: bool = True):
        """
        Configura o manager com acesso ao VAST.ai e checkpoint.

        Args:
            vast_api_key: Chave API do VAST.ai
            enable_checkpoint: Se True, habilita checkpoint de estado GPU
        """
        from src.infrastructure.providers.vast_provider import VastProvider

        self._vast_provider = VastProvider(api_key=vast_api_key)

        if enable_checkpoint:
            from .checkpoint import get_checkpoint_service
            self._checkpoint_service = get_checkpoint_service()
            logger.info("ServerlessManager configured with checkpoint support")
        else:
            logger.info("ServerlessManager configured without checkpoint")

    def enable(
        self,
        instance_id: int,
        mode: str = "economic",
        idle_timeout_seconds: int = 30,
        gpu_threshold: float = 5.0,
        keep_warm: bool = False,
        checkpoint_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Habilita modo serverless para uma instância.

        Args:
            instance_id: ID da instância VAST.ai
            mode: "fast" (checkpoint), "economic" (pause), ou "spot"
            idle_timeout_seconds: Segundos idle antes de pausar
            gpu_threshold: % GPU abaixo do qual considera idle
            keep_warm: Se True, nunca pausa automaticamente
            checkpoint_enabled: Se True, cria checkpoint antes de pausar (modo fast)

        Returns:
            Dict com configuração aplicada
        """
        try:
            serverless_mode = ServerlessMode(mode)
        except ValueError:
            serverless_mode = ServerlessMode.ECONOMIC

        config = InstanceServerlessConfig(
            instance_id=instance_id,
            mode=serverless_mode,
            idle_timeout_seconds=idle_timeout_seconds,
            gpu_threshold=gpu_threshold,
            keep_warm=keep_warm,
            checkpoint_enabled=checkpoint_enabled and serverless_mode == ServerlessMode.FAST,
            last_activity=datetime.utcnow().isoformat(),
        )

        self._configs[instance_id] = config
        self._save_configs()

        # Iniciar monitor se não estiver rodando
        self._start_monitor()

        # Setup checkpoint se modo fast
        if serverless_mode == ServerlessMode.FAST and checkpoint_enabled:
            self._setup_checkpoint_if_needed(instance_id)

        logger.info(f"Serverless enabled for {instance_id}: mode={mode}, timeout={idle_timeout_seconds}s")

        return {
            "instance_id": instance_id,
            "mode": mode,
            "idle_timeout_seconds": idle_timeout_seconds,
            "gpu_threshold": gpu_threshold,
            "keep_warm": keep_warm,
            "checkpoint_enabled": config.checkpoint_enabled,
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

            if gpu_util >= config.gpu_threshold:
                config.idle_since = None
                config.last_activity = datetime.utcnow().isoformat()

                if config.is_paused:
                    config.is_paused = False
                    config.paused_at = None

    def on_inference_start(self, instance_id: int):
        """Chamado quando inferência começa - reseta idle timer"""
        if instance_id in self._configs:
            config = self._configs[instance_id]
            config.idle_since = None
            config.last_activity = datetime.utcnow().isoformat()
            logger.debug(f"Inference started on {instance_id}, idle timer reset")

    def on_inference_complete(self, instance_id: int):
        """Chamado quando inferência termina - inicia idle timer"""
        if instance_id in self._configs:
            config = self._configs[instance_id]
            if config.idle_since is None:
                config.idle_since = datetime.utcnow().isoformat()
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
            idle_since_dt = datetime.fromisoformat(config.idle_since)
            pause_time = idle_since_dt + timedelta(seconds=config.idle_timeout_seconds)
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
            idle_since=config.idle_since,
            will_pause_at=will_pause_at,
            pause_count=self._pause_counts.get(instance_id, 0),
            resume_count=self._resume_counts.get(instance_id, 0),
            total_idle_hours=config.total_idle_time / 3600,
            total_savings_usd=config.total_savings,
            avg_cold_start_seconds=avg_cold_start,
            last_checkpoint_id=config.last_checkpoint_id,
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
                    "total_savings_usd": status.total_savings_usd,
                    "last_checkpoint_id": status.last_checkpoint_id,
                })
        return result

    def wake(self, instance_id: int, use_checkpoint: bool = True) -> Dict[str, Any]:
        """
        Acorda uma instância pausada.

        No modo FAST com checkpoint, restaura o processo do checkpoint.
        Nos outros modos, usa resume normal.

        Args:
            instance_id: ID da instância para acordar
            use_checkpoint: Se True, tenta restaurar do checkpoint (modo fast)

        Returns:
            Dict com status, tempo de wake, e método usado
        """
        if instance_id not in self._configs:
            return {"error": "Instance not configured for serverless"}

        config = self._configs[instance_id]

        if not config.is_paused:
            return {"instance_id": instance_id, "status": "already_running"}

        start_time = time.time()

        # Escolher método baseado no modo
        if config.mode == ServerlessMode.FAST and use_checkpoint and config.last_checkpoint_id:
            result = self._wake_with_checkpoint(instance_id, config)
        else:
            result = self._wake_simple(instance_id, config)

        duration = time.time() - start_time

        if result.get("success"):
            # Registrar tempo de resume
            if instance_id not in self._resume_times:
                self._resume_times[instance_id] = []
            self._resume_times[instance_id].append(duration)
            self._resume_times[instance_id] = self._resume_times[instance_id][-10:]

            # Incrementar contador
            self._resume_counts[instance_id] = self._resume_counts.get(instance_id, 0) + 1

            return {
                "instance_id": result.get("instance_id", instance_id),
                "status": "resumed",
                "cold_start_seconds": round(duration, 2),
                "mode": config.mode.value,
                "method": result.get("method", "resume"),
                "ssh_host": result.get("ssh_host"),
                "ssh_port": result.get("ssh_port"),
                "checkpoint_restored": result.get("checkpoint_restored", False),
            }

        return {
            "instance_id": instance_id,
            "status": "failed",
            "error": result.get("error", "Wake failed"),
            "cold_start_seconds": round(duration, 2),
        }

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _setup_checkpoint_if_needed(self, instance_id: int):
        """Setup checkpoint na instância se ainda não configurado"""
        if not self._checkpoint_service or not self._vast_provider:
            return

        try:
            status = self._vast_provider.get_instance_status(instance_id)
            if status.get("actual_status") != "running":
                return

            ssh_host = status.get("ssh_host")
            ssh_port = status.get("ssh_port")

            if ssh_host and ssh_port:
                result = self._checkpoint_service.setup_instance(
                    str(instance_id), ssh_host, ssh_port
                )
                if result.get("success"):
                    logger.info(f"Checkpoint setup completed for {instance_id}")
                else:
                    logger.warning(f"Checkpoint setup failed for {instance_id}: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error setting up checkpoint for {instance_id}: {e}")

    def _start_monitor(self):
        """Inicia thread de monitoramento"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        settings = get_settings()
        if not settings.monitor_enabled:
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
        settings = get_settings()
        while self._running:
            try:
                self._check_all_instances()
            except Exception as e:
                logger.error(f"Error in serverless monitor: {e}")

            time.sleep(settings.monitor_check_interval)

    def _check_all_instances(self):
        """Verifica todas as instâncias configuradas"""
        now = datetime.utcnow()

        for instance_id, config in list(self._configs.items()):
            if config.keep_warm or config.is_paused:
                continue

            if config.mode == ServerlessMode.DISABLED:
                continue

            gpu_util = self._gpu_utils.get(instance_id, 100)

            if gpu_util < config.gpu_threshold:
                if config.idle_since is None:
                    config.idle_since = now.isoformat()
                    logger.debug(f"Instance {instance_id} became idle (GPU: {gpu_util}%)")

                idle_since_dt = datetime.fromisoformat(config.idle_since)
                idle_duration = (now - idle_since_dt).total_seconds()

                if idle_duration >= config.idle_timeout_seconds:
                    if config.last_activity:
                        last_activity_dt = datetime.fromisoformat(config.last_activity)
                        runtime = (now - last_activity_dt).total_seconds()
                        if runtime < config.min_runtime_seconds:
                            continue

                    logger.info(f"Instance {instance_id} idle for {idle_duration}s, pausing...")
                    self._pause_instance(instance_id, config)
            else:
                config.idle_since = None
                config.last_activity = now.isoformat()

    def _pause_instance(self, instance_id: int, config: InstanceServerlessConfig) -> bool:
        """Pausa uma instância, criando checkpoint se modo FAST"""
        if not self._vast_provider:
            logger.error("VastProvider not configured")
            return False

        try:
            # Criar checkpoint antes de pausar (modo FAST)
            if config.mode == ServerlessMode.FAST and config.checkpoint_enabled:
                checkpoint_result = self._create_checkpoint_before_pause(instance_id)
                if checkpoint_result.get("success"):
                    config.last_checkpoint_id = checkpoint_result.get("checkpoint_id")
                    logger.info(f"Checkpoint created before pause: {config.last_checkpoint_id}")

            # Pausar instância
            success = self._vast_provider.pause_instance(instance_id)

            if success:
                config.is_paused = True
                config.paused_at = datetime.utcnow().isoformat()
                self._pause_counts[instance_id] = self._pause_counts.get(instance_id, 0) + 1
                self._save_configs()
                logger.info(f"Instance {instance_id} paused (mode={config.mode.value})")

            return success

        except Exception as e:
            logger.error(f"Failed to pause instance {instance_id}: {e}")
            return False

    def _create_checkpoint_before_pause(self, instance_id: int) -> Dict[str, Any]:
        """Cria checkpoint antes de pausar"""
        if not self._checkpoint_service or not self._vast_provider:
            return {"success": False, "error": "Services not configured"}

        try:
            status = self._vast_provider.get_instance_status(instance_id)
            ssh_host = status.get("ssh_host")
            ssh_port = status.get("ssh_port")

            if not ssh_host or not ssh_port:
                return {"success": False, "error": "SSH not available"}

            return self._checkpoint_service.create_checkpoint(
                str(instance_id), ssh_host, ssh_port
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _wake_with_checkpoint(self, instance_id: int, config: InstanceServerlessConfig) -> Dict[str, Any]:
        """Acorda instância restaurando do checkpoint"""
        if not self._checkpoint_service or not self._vast_provider:
            return self._wake_simple(instance_id, config)

        try:
            # Primeiro, resume a instância
            if not self._vast_provider.resume_instance(instance_id):
                return {"success": False, "error": "Resume failed"}

            # Aguardar SSH ficar disponível
            if not self._wait_for_ssh(instance_id, config.ssh_verify_timeout):
                return {"success": False, "error": "SSH not ready after resume"}

            # Obter info de conexão
            status = self._vast_provider.get_instance_status(instance_id)
            ssh_host = status.get("ssh_host")
            ssh_port = status.get("ssh_port")

            # Restaurar checkpoint
            restore_result = self._checkpoint_service.restore_checkpoint(
                str(instance_id), ssh_host, ssh_port, config.last_checkpoint_id
            )

            # Atualizar estado
            self._update_resume_state(config)

            return {
                "success": True,
                "method": "checkpoint",
                "instance_id": instance_id,
                "ssh_host": ssh_host,
                "ssh_port": ssh_port,
                "checkpoint_restored": restore_result.get("success", False),
                "restored_pid": restore_result.get("restored_pid"),
            }

        except Exception as e:
            logger.error(f"Wake with checkpoint failed: {e}")
            # Fallback para wake simples
            return self._wake_simple(instance_id, config)

    def _wake_simple(self, instance_id: int, config: InstanceServerlessConfig) -> Dict[str, Any]:
        """Wake simples sem checkpoint"""
        if not self._vast_provider:
            return {"success": False, "error": "VastProvider not configured"}

        try:
            if not self._vast_provider.resume_instance(instance_id):
                return {"success": False, "error": "Resume failed"}

            if not self._wait_for_ssh(instance_id, config.ssh_verify_timeout):
                return {"success": False, "error": "SSH not ready"}

            self._update_resume_state(config)

            status = self._vast_provider.get_instance_status(instance_id)

            return {
                "success": True,
                "method": "resume",
                "instance_id": instance_id,
                "ssh_host": status.get("ssh_host"),
                "ssh_port": status.get("ssh_port"),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resume_instance(self, instance_id: int, config: InstanceServerlessConfig) -> bool:
        """Resume uma instância (wrapper legacy)"""
        result = self._wake_simple(instance_id, config)
        return result.get("success", False)

    def _update_resume_state(self, config: InstanceServerlessConfig):
        """Atualiza estado após resume"""
        settings = get_settings()

        if config.paused_at:
            paused_at_dt = datetime.fromisoformat(config.paused_at)
            idle_seconds = (datetime.utcnow() - paused_at_dt).total_seconds()
            config.total_idle_time += idle_seconds

            # Calcular economia
            if config.mode == ServerlessMode.FAST:
                idle_cost = settings.cpu_standby_hourly_rate
            else:
                idle_cost = settings.storage_idle_hourly_rate

            savings = (settings.gpu_hourly_rate - idle_cost) * (idle_seconds / 3600)
            config.total_savings += savings

        config.is_paused = False
        config.paused_at = None
        config.idle_since = None
        config.last_activity = datetime.utcnow().isoformat()
        self._save_configs()

    def _wait_for_ssh(self, instance_id: int, timeout: int = 30) -> bool:
        """Aguarda SSH ficar disponível"""
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

    def _save_configs(self):
        """Salva configurações em arquivo"""
        settings = get_settings()
        config_file = os.path.expanduser(settings.config_file)

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
                    "total_savings": config.total_savings,
                    "checkpoint_enabled": config.checkpoint_enabled,
                    "last_checkpoint_id": config.last_checkpoint_id,
                }

            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save serverless configs: {e}")

    def _load_configs(self):
        """Carrega configurações de arquivo"""
        settings = get_settings()
        config_file = os.path.expanduser(settings.config_file)

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    data = json.load(f)

                for instance_id_str, cfg in data.items():
                    instance_id = int(instance_id_str)
                    self._configs[instance_id] = InstanceServerlessConfig(
                        instance_id=instance_id,
                        mode=ServerlessMode(cfg.get("mode", "disabled")),
                        idle_timeout_seconds=cfg.get("idle_timeout_seconds", 30),
                        gpu_threshold=cfg.get("gpu_threshold", 5.0),
                        keep_warm=cfg.get("keep_warm", False),
                        min_runtime_seconds=cfg.get("min_runtime_seconds", 60),
                        is_paused=cfg.get("is_paused", False),
                        total_idle_time=cfg.get("total_idle_time", 0),
                        total_savings=cfg.get("total_savings", 0),
                        checkpoint_enabled=cfg.get("checkpoint_enabled", True),
                        last_checkpoint_id=cfg.get("last_checkpoint_id"),
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
