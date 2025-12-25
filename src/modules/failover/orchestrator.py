"""
Failover Orchestrator - Orquestração unificada de failover

Coordena estratégias de failover:
1. Warm Pool (primário, ~30-60s)
2. CPU Standby + Snapshot (fallback, ~5-10min)
"""

import asyncio
import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from .models import (
    FailoverStrategy,
    FailoverPhase,
    FailoverStatus,
    FailoverResult,
    FailoverConfig,
)

logger = logging.getLogger(__name__)


class FailoverOrchestrator:
    """
    Orquestrador unificado de failover.

    Gerencia failover usando estratégias configuradas:
    - WARM_POOL: GPU standby no mesmo host
    - CPU_STANDBY: Snapshot + nova GPU
    - BOTH: Tenta warm pool primeiro, depois CPU standby

    Uso:
        orchestrator = FailoverOrchestrator(vast_api_key="...")

        result = await orchestrator.execute(
            machine_id=123,
            gpu_instance_id=456,
            ssh_host="ssh.vast.ai",
            ssh_port=12345
        )

        if result.success:
            print(f"Failover via {result.strategy_succeeded}")
            print(f"Nova GPU: {result.new_ssh_host}:{result.new_ssh_port}")
    """

    def __init__(
        self,
        vast_api_key: str,
        gcp_credentials: Optional[dict] = None,
        b2_endpoint: str = "https://s3.us-west-004.backblazeb2.com",
        b2_bucket: str = "dumoncloud-snapshot",
    ):
        self.vast_api_key = vast_api_key
        self.gcp_credentials = gcp_credentials
        self.b2_endpoint = b2_endpoint
        self.b2_bucket = b2_bucket

        # Lazy imports para evitar dependências circulares
        self._settings_manager = None
        self._warm_pool_manager = None

    @property
    def settings_manager(self):
        if self._settings_manager is None:
            try:
                from src.config.failover_settings import get_failover_settings_manager
                self._settings_manager = get_failover_settings_manager()
            except ImportError:
                logger.warning("[FAILOVER] FailoverSettingsManager not available")
                self._settings_manager = None
        return self._settings_manager

    def get_config(self, machine_id: int) -> FailoverConfig:
        """Obtém configuração efetiva para uma máquina"""
        config = FailoverConfig(machine_id=machine_id)

        if self.settings_manager:
            try:
                effective = self.settings_manager.get_effective_config(machine_id)
                strategy_str = effective.get('effective_strategy', 'both')
                config.strategy = FailoverStrategy(strategy_str)
            except Exception as e:
                logger.warning(f"[FAILOVER] Error getting config: {e}")

        return config

    async def execute(
        self,
        machine_id: int,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        failover_id: Optional[str] = None,
        workspace_path: str = "/workspace",
        force_strategy: Optional[FailoverStrategy] = None,
        config: Optional[FailoverConfig] = None,
    ) -> FailoverResult:
        """
        Executa failover usando estratégias configuradas.

        Args:
            machine_id: ID interno da máquina
            gpu_instance_id: ID da instância GPU atual
            ssh_host: Host SSH atual
            ssh_port: Porta SSH atual
            failover_id: ID único (gerado automaticamente se não fornecido)
            workspace_path: Path para backup/restore
            force_strategy: Override de estratégia
            config: Configuração customizada

        Returns:
            FailoverResult com detalhes completos
        """
        start_time = time.time()
        failover_id = failover_id or f"fo-{uuid.uuid4().hex[:8]}"

        # Obter configuração
        config = config or self.get_config(machine_id)
        strategy = force_strategy or config.strategy

        logger.info(f"[{failover_id}] Starting failover for machine {machine_id}")
        logger.info(f"[{failover_id}] Strategy: {strategy.value}")

        result = FailoverResult(
            success=False,
            failover_id=failover_id,
            machine_id=machine_id,
            strategy_attempted=strategy.value,
            original_gpu_id=gpu_instance_id,
            original_ssh_host=ssh_host,
            original_ssh_port=ssh_port,
            started_at=datetime.now(),
        )

        # Verificar se desabilitado
        if strategy == FailoverStrategy.DISABLED:
            result.error = "Failover disabled for this machine"
            result.total_ms = int((time.time() - start_time) * 1000)
            result.completed_at = datetime.now()
            logger.warning(f"[{failover_id}] Failover disabled")
            return result

        result.phase_history.append((FailoverPhase.DETECTING.value, time.time()))

        # Determinar quais estratégias tentar
        try_warm_pool = strategy in [FailoverStrategy.WARM_POOL, FailoverStrategy.BOTH]
        try_cpu_standby = strategy in [FailoverStrategy.CPU_STANDBY, FailoverStrategy.BOTH]

        # ============================================================
        # FASE 1: Tentar Warm Pool
        # ============================================================
        if try_warm_pool:
            result.phase_history.append((FailoverPhase.WARM_POOL_CHECK.value, time.time()))
            logger.info(f"[{failover_id}] Attempting Warm Pool failover...")

            warm_start = time.time()
            warm_result = await self._try_warm_pool(
                machine_id=machine_id,
                failover_id=failover_id,
                timeout=config.warm_pool_timeout_seconds,
            )
            result.warm_pool_attempt_ms = int((time.time() - warm_start) * 1000)

            if warm_result["success"]:
                logger.info(f"[{failover_id}] Warm Pool succeeded in {result.warm_pool_attempt_ms}ms")
                result.success = True
                result.strategy_succeeded = "warm_pool"
                result.new_gpu_id = warm_result.get("new_gpu_id")
                result.new_ssh_host = warm_result.get("new_ssh_host")
                result.new_ssh_port = warm_result.get("new_ssh_port")
                result.new_gpu_name = warm_result.get("new_gpu_name")
                result.phase_history.append((FailoverPhase.COMPLETED.value, time.time()))
                result.total_ms = int((time.time() - start_time) * 1000)
                result.completed_at = datetime.now()
                return result
            else:
                result.warm_pool_error = warm_result.get("error", "Unknown error")
                logger.warning(f"[{failover_id}] Warm Pool failed: {result.warm_pool_error}")

        # ============================================================
        # FASE 2: Tentar CPU Standby
        # ============================================================
        if try_cpu_standby:
            result.phase_history.append((FailoverPhase.CPU_STANDBY_CHECK.value, time.time()))
            logger.info(f"[{failover_id}] Attempting CPU Standby failover...")

            cpu_start = time.time()
            cpu_result = await self._try_cpu_standby(
                machine_id=machine_id,
                gpu_instance_id=gpu_instance_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                failover_id=failover_id,
                workspace_path=workspace_path,
                config=config,
            )

            # Copiar métricas
            result.snapshot_creation_ms = cpu_result.get("snapshot_creation_ms", 0)
            result.gpu_provisioning_ms = cpu_result.get("gpu_provisioning_ms", 0)
            result.restore_ms = cpu_result.get("restore_ms", 0)
            result.validation_ms = cpu_result.get("validation_ms", 0)
            result.phase_timings = cpu_result.get("phase_timings", {})

            if cpu_result["success"]:
                total_cpu_ms = int((time.time() - cpu_start) * 1000)
                logger.info(f"[{failover_id}] CPU Standby succeeded in {total_cpu_ms}ms")

                result.success = True
                result.strategy_succeeded = "cpu_standby"
                result.new_gpu_id = cpu_result.get("new_gpu_id")
                result.new_ssh_host = cpu_result.get("new_ssh_host")
                result.new_ssh_port = cpu_result.get("new_ssh_port")
                result.new_gpu_name = cpu_result.get("new_gpu_name")
                result.snapshot_id = cpu_result.get("snapshot_id")
                result.snapshot_type = cpu_result.get("snapshot_type")
                result.snapshot_size_bytes = cpu_result.get("snapshot_size_bytes", 0)
                result.gpus_tried = cpu_result.get("gpus_tried", 0)
                result.rounds_attempted = cpu_result.get("rounds_attempted", 0)
                result.phase_history.append((FailoverPhase.COMPLETED.value, time.time()))
                result.total_ms = int((time.time() - start_time) * 1000)
                result.completed_at = datetime.now()
                return result
            else:
                result.cpu_standby_error = cpu_result.get("error", "Unknown error")
                result.failed_phase = cpu_result.get("failed_phase")
                logger.warning(f"[{failover_id}] CPU Standby failed: {result.cpu_standby_error}")

        # ============================================================
        # FALHA: Nenhuma estratégia funcionou
        # ============================================================
        result.phase_history.append((FailoverPhase.FAILED.value, time.time()))
        result.total_ms = int((time.time() - start_time) * 1000)
        result.completed_at = datetime.now()

        if result.warm_pool_error and result.cpu_standby_error:
            result.error = f"All strategies failed. Warm Pool: {result.warm_pool_error}. CPU Standby: {result.cpu_standby_error}"
        elif result.warm_pool_error:
            result.error = f"Warm Pool failed: {result.warm_pool_error}"
        elif result.cpu_standby_error:
            result.error = f"CPU Standby failed: {result.cpu_standby_error}"
        else:
            result.error = "No failover strategy was attempted"

        logger.error(f"[{failover_id}] Failover failed: {result.error}")
        return result

    async def _try_warm_pool(
        self,
        machine_id: int,
        failover_id: str,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """Tenta failover via Warm Pool"""
        try:
            from src.services.warmpool import get_warm_pool_manager, WarmPoolState

            manager = get_warm_pool_manager(machine_id, self.vast_api_key)

            # Verificar se warm pool está ativo
            if manager.status.state != WarmPoolState.ACTIVE:
                return {
                    "success": False,
                    "error": f"Warm pool not active (state={manager.status.state.value})"
                }

            # Verificar se há GPU standby
            if not manager.status.standby_gpu_id:
                return {
                    "success": False,
                    "error": "No standby GPU available in warm pool"
                }

            # Executar failover
            logger.info(f"[{failover_id}] Triggering warm pool failover...")
            success = await asyncio.wait_for(
                manager.trigger_failover(),
                timeout=timeout
            )

            if success:
                return {
                    "success": True,
                    "new_gpu_id": manager.status.primary_gpu_id,
                    "new_ssh_host": manager.status.primary_ssh_host,
                    "new_ssh_port": manager.status.primary_ssh_port,
                    "new_gpu_name": "GPU",
                }
            else:
                return {
                    "success": False,
                    "error": manager.status.error_message or "Failover trigger failed"
                }

        except asyncio.TimeoutError:
            return {"success": False, "error": f"Warm pool timeout ({timeout}s)"}
        except ImportError:
            return {"success": False, "error": "WarmPoolManager not available"}
        except Exception as e:
            logger.error(f"[{failover_id}] Warm pool error: {e}")
            return {"success": False, "error": str(e)}

    async def _try_cpu_standby(
        self,
        machine_id: int,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        failover_id: str,
        workspace_path: str,
        config: FailoverConfig,
    ) -> Dict[str, Any]:
        """Tenta failover via CPU Standby + Snapshot"""
        try:
            from .service import FailoverService

            service = FailoverService(
                vast_api_key=self.vast_api_key,
                b2_endpoint=self.b2_endpoint,
                b2_bucket=self.b2_bucket,
            )

            logger.info(f"[{failover_id}] Starting CPU Standby failover...")

            result = await service.execute(
                gpu_instance_id=gpu_instance_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                failover_id=failover_id,
                workspace_path=workspace_path,
                min_gpu_ram=config.min_gpu_ram_mb,
                max_gpu_price=config.max_gpu_price,
            )

            if result.success:
                return {
                    "success": True,
                    "new_gpu_id": result.new_gpu_id,
                    "new_ssh_host": result.new_ssh_host,
                    "new_ssh_port": result.new_ssh_port,
                    "new_gpu_name": result.new_gpu_name,
                    "snapshot_id": result.snapshot_id,
                    "snapshot_type": result.snapshot_type,
                    "snapshot_size_bytes": result.snapshot_size_bytes,
                    "snapshot_creation_ms": result.snapshot_creation_ms,
                    "gpu_provisioning_ms": result.gpu_provisioning_ms,
                    "restore_ms": result.restore_ms,
                    "validation_ms": result.validation_ms,
                    "phase_timings": result.phase_timings,
                    "gpus_tried": result.gpus_tried,
                    "rounds_attempted": result.rounds_attempted,
                }
            else:
                return {
                    "success": False,
                    "error": result.error or f"Failed at phase: {result.failed_phase}",
                    "failed_phase": result.failed_phase,
                    "phase_timings": result.phase_timings,
                }

        except Exception as e:
            logger.error(f"[{failover_id}] CPU Standby error: {e}")
            return {"success": False, "error": str(e)}

    async def check_readiness(self, machine_id: int) -> Dict[str, Any]:
        """
        Verifica se failover está pronto para uma máquina.

        Returns:
            Dict com status de cada estratégia
        """
        config = self.get_config(machine_id)

        result = {
            "machine_id": machine_id,
            "strategy": config.strategy.value,
            "warm_pool_ready": False,
            "warm_pool_status": None,
            "cpu_standby_ready": False,
            "cpu_standby_status": None,
            "overall_ready": False,
        }

        # Verificar Warm Pool
        if config.strategy in [FailoverStrategy.WARM_POOL, FailoverStrategy.BOTH]:
            try:
                from src.services.warmpool import get_warm_pool_manager

                manager = get_warm_pool_manager(machine_id, self.vast_api_key)
                status = manager.get_status()
                result["warm_pool_status"] = status
                result["warm_pool_ready"] = (
                    status.get("state") == "active" and
                    status.get("standby_gpu_id") is not None
                )
            except Exception as e:
                result["warm_pool_status"] = {"error": str(e)}

        # Verificar CPU Standby
        if config.strategy in [FailoverStrategy.CPU_STANDBY, FailoverStrategy.BOTH]:
            try:
                from src.services.standby import StandbyManager

                standby_manager = StandbyManager()
                association = standby_manager.get_association(machine_id)
                result["cpu_standby_status"] = association
                result["cpu_standby_ready"] = association is not None
            except Exception as e:
                result["cpu_standby_status"] = {"error": str(e)}

        # Overall readiness
        if config.strategy == FailoverStrategy.WARM_POOL:
            result["overall_ready"] = result["warm_pool_ready"]
        elif config.strategy == FailoverStrategy.CPU_STANDBY:
            result["overall_ready"] = result["cpu_standby_ready"]
        elif config.strategy == FailoverStrategy.BOTH:
            result["overall_ready"] = result["warm_pool_ready"] or result["cpu_standby_ready"]

        return result


# Singleton
_orchestrator: Optional[FailoverOrchestrator] = None


def get_failover_orchestrator(
    vast_api_key: Optional[str] = None,
    gcp_credentials: Optional[dict] = None,
) -> FailoverOrchestrator:
    """Obtém ou cria instância global do FailoverOrchestrator"""
    global _orchestrator

    if _orchestrator is None:
        import os
        if not vast_api_key:
            vast_api_key = os.getenv("VAST_API_KEY", "")
        _orchestrator = FailoverOrchestrator(
            vast_api_key=vast_api_key,
            gcp_credentials=gcp_credentials,
        )

    return _orchestrator
