"""
Sync Service - Serviço principal de sincronização
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .models import (
    SyncStatus,
    SyncProgress,
    SyncConfig,
    Checkpoint,
    CheckpointType,
)
from .checkpoint import CheckpointManager, get_checkpoint_manager

logger = logging.getLogger(__name__)


class SyncService:
    """
    Serviço unificado de sincronização.

    Gerencia:
    - Checkpoints periódicos
    - Sync sob demanda
    - Monitoramento de status

    Uso:
        service = get_sync_service()

        # Configurar máquina
        service.configure(machine_id=123, config=SyncConfig(...))

        # Iniciar sync
        await service.start_sync(machine_id=123)

        # Verificar status
        progress = service.get_progress(machine_id=123)
    """

    def __init__(self):
        self._configs: Dict[int, SyncConfig] = {}
        self._progress: Dict[int, SyncProgress] = {}
        self._tasks: Dict[int, asyncio.Task] = {}
        self._checkpoint_manager = get_checkpoint_manager()

    def configure(self, machine_id: int, config: SyncConfig):
        """Configura sync para uma máquina"""
        self._configs[machine_id] = config
        logger.info(f"[SYNC] Configured machine {machine_id}")

    def get_config(self, machine_id: int) -> Optional[SyncConfig]:
        """Obtém configuração de uma máquina"""
        return self._configs.get(machine_id)

    def get_progress(self, machine_id: int) -> SyncProgress:
        """Obtém progresso atual de sync"""
        return self._progress.get(machine_id, SyncProgress(status=SyncStatus.IDLE))

    async def start_sync(
        self,
        machine_id: int,
        ssh_host: str,
        ssh_port: int,
        force_full: bool = False,
    ) -> Checkpoint:
        """
        Inicia sincronização para uma máquina.

        Args:
            machine_id: ID da máquina
            ssh_host: Host SSH
            ssh_port: Porta SSH
            force_full: Forçar checkpoint full

        Returns:
            Checkpoint criado
        """
        config = self._configs.get(machine_id)
        if not config:
            config = SyncConfig(machine_id=machine_id)
            self._configs[machine_id] = config

        # Atualizar status
        self._progress[machine_id] = SyncProgress(
            status=SyncStatus.SYNCING,
            started_at=datetime.now(),
        )

        try:
            # Verificar se deve ser incremental
            if config.incremental_enabled and not force_full:
                latest = self._checkpoint_manager.get_latest(machine_id)
                if latest:
                    # Verificar se checkpoint base é recente
                    age_hours = (datetime.now() - latest.created_at).total_seconds() / 3600
                    if age_hours < config.full_backup_interval_hours:
                        logger.info(f"[SYNC] Creating incremental checkpoint")
                        checkpoint = await self._checkpoint_manager.create_incremental(
                            machine_id=machine_id,
                            ssh_host=ssh_host,
                            ssh_port=ssh_port,
                            base_checkpoint_id=latest.checkpoint_id,
                            workspace_path=config.workspace_path,
                        )
                        self._progress[machine_id].status = SyncStatus.COMPLETED
                        return checkpoint

            # Checkpoint full
            logger.info(f"[SYNC] Creating full checkpoint")
            checkpoint = await self._checkpoint_manager.create(
                machine_id=machine_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                workspace_path=config.workspace_path,
            )

            self._progress[machine_id] = SyncProgress(
                status=SyncStatus.COMPLETED,
                progress_pct=100.0,
                bytes_transferred=checkpoint.size_compressed,
                files_transferred=checkpoint.num_files,
            )

            return checkpoint

        except Exception as e:
            logger.error(f"[SYNC] Sync failed for machine {machine_id}: {e}")
            self._progress[machine_id] = SyncProgress(
                status=SyncStatus.FAILED,
            )
            raise

    async def restore(
        self,
        machine_id: int,
        target_host: str,
        target_port: int,
        checkpoint_id: Optional[str] = None,
    ):
        """
        Restaura checkpoint para uma máquina.

        Args:
            machine_id: ID da máquina
            target_host: Host de destino
            target_port: Porta de destino
            checkpoint_id: ID do checkpoint (usa mais recente se None)
        """
        if not checkpoint_id:
            latest = self._checkpoint_manager.get_latest(machine_id)
            if not latest:
                raise ValueError(f"No checkpoint found for machine {machine_id}")
            checkpoint_id = latest.checkpoint_id

        config = self._configs.get(machine_id, SyncConfig(machine_id=machine_id))

        return await self._checkpoint_manager.restore(
            checkpoint_id=checkpoint_id,
            target_host=target_host,
            target_port=target_port,
            workspace_path=config.workspace_path,
        )

    def list_checkpoints(self, machine_id: int) -> List[Dict[str, Any]]:
        """Lista checkpoints de uma máquina"""
        return self._checkpoint_manager.list_checkpoints(machine_id)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Deleta um checkpoint"""
        return self._checkpoint_manager.delete(checkpoint_id)

    async def start_periodic_sync(
        self,
        machine_id: int,
        ssh_host: str,
        ssh_port: int,
        interval_seconds: int = 300,
    ):
        """
        Inicia sync periódico em background.

        Args:
            machine_id: ID da máquina
            interval_seconds: Intervalo entre syncs
        """
        if machine_id in self._tasks:
            logger.warning(f"[SYNC] Periodic sync already running for {machine_id}")
            return

        async def periodic_task():
            while True:
                try:
                    await self.start_sync(machine_id, ssh_host, ssh_port)
                except Exception as e:
                    logger.error(f"[SYNC] Periodic sync failed: {e}")

                await asyncio.sleep(interval_seconds)

        task = asyncio.create_task(periodic_task())
        self._tasks[machine_id] = task
        logger.info(f"[SYNC] Started periodic sync for machine {machine_id}")

    def stop_periodic_sync(self, machine_id: int):
        """Para sync periódico"""
        if machine_id in self._tasks:
            self._tasks[machine_id].cancel()
            del self._tasks[machine_id]
            logger.info(f"[SYNC] Stopped periodic sync for machine {machine_id}")


# Singleton
_service: Optional[SyncService] = None


def get_sync_service() -> SyncService:
    """Obtém instância do SyncService"""
    global _service
    if _service is None:
        _service = SyncService()
    return _service
