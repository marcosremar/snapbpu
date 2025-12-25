"""
Warm Pool Manager - Gerenciamento de pool de GPUs
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .models import WarmPoolState, WarmPoolStatus, WarmPoolConfig

logger = logging.getLogger(__name__)


class WarmPoolManager:
    """
    Gerenciador de warm pool para failover rápido.

    Mantém GPU standby pronta para assumir em caso de falha.
    Reduz tempo de failover de ~5min para ~30-60s.

    Uso:
        manager = get_warmpool_manager(machine_id=123)

        # Iniciar warm pool
        await manager.start()

        # Verificar status
        status = manager.get_status()

        # Trigger failover
        if need_failover:
            await manager.trigger_failover()
    """

    def __init__(
        self,
        machine_id: int,
        vast_api_key: str = "",
        config: Optional[WarmPoolConfig] = None,
    ):
        self.machine_id = machine_id
        self.vast_api_key = vast_api_key
        self.config = config or WarmPoolConfig(machine_id=machine_id)

        self.status = WarmPoolStatus(
            machine_id=machine_id,
            state=WarmPoolState.INACTIVE,
        )

        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Inicia warm pool"""
        if self.status.state == WarmPoolState.ACTIVE:
            logger.warning(f"[WARMPOOL] Already active for machine {self.machine_id}")
            return True

        self.status.state = WarmPoolState.STARTING
        logger.info(f"[WARMPOOL] Starting warm pool for machine {self.machine_id}")

        try:
            # Provisionar GPU standby
            standby_result = await self._provision_standby()

            if standby_result:
                self.status.standby_gpu_id = standby_result.get("instance_id")
                self.status.standby_ssh_host = standby_result.get("ssh_host")
                self.status.standby_ssh_port = standby_result.get("ssh_port")
                self.status.standby_gpu_name = standby_result.get("gpu_name", "")

                self.status.state = WarmPoolState.ACTIVE
                logger.info(f"[WARMPOOL] Active with standby GPU {self.status.standby_gpu_id}")

                # Iniciar monitoramento
                self._monitor_task = asyncio.create_task(self._monitor_loop())

                return True
            else:
                self.status.state = WarmPoolState.ERROR
                self.status.error_message = "Failed to provision standby GPU"
                return False

        except Exception as e:
            self.status.state = WarmPoolState.ERROR
            self.status.error_message = str(e)
            logger.error(f"[WARMPOOL] Start failed: {e}")
            return False

    async def stop(self):
        """Para warm pool"""
        logger.info(f"[WARMPOOL] Stopping warm pool for machine {self.machine_id}")

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Destruir standby GPU
        if self.status.standby_gpu_id:
            await self._destroy_gpu(self.status.standby_gpu_id)

        self.status.state = WarmPoolState.INACTIVE
        self.status.standby_gpu_id = None

    async def trigger_failover(self) -> bool:
        """Executa failover para GPU standby"""
        if self.status.state != WarmPoolState.ACTIVE:
            logger.error(f"[WARMPOOL] Cannot failover - state: {self.status.state}")
            return False

        if not self.status.standby_gpu_id:
            logger.error("[WARMPOOL] No standby GPU available")
            return False

        self.status.state = WarmPoolState.FAILOVER
        logger.info(f"[WARMPOOL] Triggering failover to {self.status.standby_gpu_id}")

        try:
            # Promover standby para primary
            self.status.primary_gpu_id = self.status.standby_gpu_id
            self.status.primary_ssh_host = self.status.standby_ssh_host
            self.status.primary_ssh_port = self.status.standby_ssh_port
            self.status.primary_gpu_name = self.status.standby_gpu_name

            # Limpar standby
            self.status.standby_gpu_id = None
            self.status.standby_ssh_host = None
            self.status.standby_ssh_port = None

            # Atualizar stats
            self.status.failover_count += 1
            self.status.last_failover_at = datetime.now()

            self.status.state = WarmPoolState.ACTIVE

            # Provisionar novo standby em background
            asyncio.create_task(self._replenish_standby())

            logger.info("[WARMPOOL] Failover complete")
            return True

        except Exception as e:
            self.status.state = WarmPoolState.ERROR
            self.status.error_message = str(e)
            logger.error(f"[WARMPOOL] Failover failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual"""
        return self.status.to_dict()

    async def _provision_standby(self) -> Optional[Dict[str, Any]]:
        """Provisiona GPU standby"""
        # Em produção, usaria GPUProvisioner
        logger.debug("[WARMPOOL] Provisioning standby GPU...")
        # Simulado
        return {
            "instance_id": 12345,
            "ssh_host": "standby.vast.ai",
            "ssh_port": 22,
            "gpu_name": "RTX 4090",
        }

    async def _destroy_gpu(self, gpu_id: int):
        """Destroi GPU"""
        logger.debug(f"[WARMPOOL] Destroying GPU {gpu_id}")

    async def _replenish_standby(self):
        """Repõe GPU standby após failover"""
        logger.info("[WARMPOOL] Replenishing standby GPU...")
        result = await self._provision_standby()
        if result:
            self.status.standby_gpu_id = result.get("instance_id")
            self.status.standby_ssh_host = result.get("ssh_host")
            self.status.standby_ssh_port = result.get("ssh_port")
            logger.info(f"[WARMPOOL] New standby GPU: {self.status.standby_gpu_id}")

    async def _monitor_loop(self):
        """Loop de monitoramento"""
        while True:
            try:
                # Verificar saúde do primary e standby
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WARMPOOL] Monitor error: {e}")


# Cache de managers por machine_id
_managers: Dict[int, WarmPoolManager] = {}


def get_warmpool_manager(
    machine_id: int,
    vast_api_key: str = "",
) -> WarmPoolManager:
    """Obtém WarmPoolManager para uma máquina"""
    import os

    if machine_id not in _managers:
        _managers[machine_id] = WarmPoolManager(
            machine_id=machine_id,
            vast_api_key=vast_api_key or os.getenv("VAST_API_KEY", ""),
        )
    return _managers[machine_id]
