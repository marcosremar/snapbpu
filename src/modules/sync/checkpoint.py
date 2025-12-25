"""
Checkpoint Manager - Gerenciamento de checkpoints
"""

import os
import time
import logging
import subprocess
from typing import Optional, Dict, Any, List
from datetime import datetime

from .models import (
    Checkpoint,
    CheckpointType,
    RestoreResult,
    SyncConfig,
)

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Gerenciador de checkpoints para backup/restore de workspace.

    Suporta:
    - Checkpoint full (todos os arquivos)
    - Checkpoint incremental (apenas mudanças)
    - Múltiplos storage providers (B2, R2, S3)

    Uso:
        manager = get_checkpoint_manager()

        # Criar checkpoint full
        checkpoint = await manager.create(
            machine_id=123,
            ssh_host="gpu.vast.ai",
            ssh_port=12345,
        )

        # Criar checkpoint incremental
        incr_checkpoint = await manager.create_incremental(
            machine_id=123,
            ssh_host="gpu.vast.ai",
            ssh_port=12345,
            base_checkpoint_id=checkpoint.checkpoint_id,
        )

        # Restaurar
        result = await manager.restore(
            checkpoint_id=checkpoint.checkpoint_id,
            target_host="new-gpu.vast.ai",
            target_port=12346,
        )
    """

    def __init__(
        self,
        storage_endpoint: str = "",
        storage_bucket: str = "dumoncloud-snapshot",
        storage_provider: str = "b2",
    ):
        self.storage_endpoint = storage_endpoint or os.getenv(
            "B2_ENDPOINT", "https://s3.us-west-004.backblazeb2.com"
        )
        self.storage_bucket = storage_bucket
        self.storage_provider = storage_provider

        # Lazy import do snapshot service
        self._snapshot_service = None

    @property
    def snapshot_service(self):
        """Obtém GPUSnapshotService lazily"""
        if self._snapshot_service is None:
            from src.services.gpu.snapshot import GPUSnapshotService
            self._snapshot_service = GPUSnapshotService(
                r2_endpoint=self.storage_endpoint,
                r2_bucket=self.storage_bucket,
                provider=self.storage_provider,
            )
        return self._snapshot_service

    async def create(
        self,
        machine_id: int,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str = "/workspace",
        checkpoint_name: Optional[str] = None,
    ) -> Checkpoint:
        """
        Cria checkpoint full do workspace.

        Args:
            machine_id: ID da máquina
            ssh_host: Host SSH
            ssh_port: Porta SSH
            workspace_path: Path do workspace
            checkpoint_name: Nome customizado

        Returns:
            Checkpoint com metadados
        """
        start_time = time.time()

        if not checkpoint_name:
            checkpoint_name = f"checkpoint-{machine_id}-{int(time.time())}"

        logger.info(f"[CHECKPOINT] Creating full checkpoint: {checkpoint_name}")

        try:
            # Usar GPUSnapshotService para criar snapshot
            result = self.snapshot_service.create_snapshot(
                instance_id=str(machine_id),
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                workspace_path=workspace_path,
                snapshot_name=checkpoint_name,
            )

            creation_time = int((time.time() - start_time) * 1000)

            checkpoint = Checkpoint(
                checkpoint_id=checkpoint_name,
                machine_id=machine_id,
                checkpoint_type=CheckpointType.FULL,
                storage_path=f"snapshots/{checkpoint_name}/",
                storage_provider=self.storage_provider,
                size_original=result.get("size_original", 0),
                size_compressed=result.get("size_compressed", 0),
                compression_ratio=result.get("compression_ratio", 1.0),
                num_files=result.get("num_files", 0),
                num_chunks=result.get("num_chunks", 0),
                workspace_path=workspace_path,
                creation_time_ms=creation_time,
                upload_time_ms=int(result.get("upload_time", 0) * 1000),
            )

            logger.info(
                f"[CHECKPOINT] Full checkpoint created: {checkpoint_name} "
                f"({checkpoint.size_compressed / 1024 / 1024:.1f} MB) "
                f"in {creation_time}ms"
            )

            return checkpoint

        except Exception as e:
            logger.error(f"[CHECKPOINT] Failed to create checkpoint: {e}")
            raise

    async def create_incremental(
        self,
        machine_id: int,
        ssh_host: str,
        ssh_port: int,
        base_checkpoint_id: str,
        workspace_path: str = "/workspace",
        checkpoint_name: Optional[str] = None,
    ) -> Checkpoint:
        """
        Cria checkpoint incremental (apenas arquivos modificados).

        Args:
            machine_id: ID da máquina
            ssh_host: Host SSH
            ssh_port: Porta SSH
            base_checkpoint_id: ID do checkpoint base
            workspace_path: Path do workspace

        Returns:
            Checkpoint incremental
        """
        start_time = time.time()

        if not checkpoint_name:
            checkpoint_name = f"incr-{machine_id}-{int(time.time())}"

        logger.info(
            f"[CHECKPOINT] Creating incremental checkpoint: {checkpoint_name} "
            f"(base: {base_checkpoint_id})"
        )

        try:
            result = self.snapshot_service.create_incremental_snapshot(
                instance_id=str(machine_id),
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                base_snapshot_id=base_checkpoint_id,
                workspace_path=workspace_path,
                snapshot_name=checkpoint_name,
            )

            creation_time = int((time.time() - start_time) * 1000)

            checkpoint = Checkpoint(
                checkpoint_id=checkpoint_name,
                machine_id=machine_id,
                checkpoint_type=CheckpointType.INCREMENTAL,
                storage_path=f"snapshots/{checkpoint_name}/",
                storage_provider=self.storage_provider,
                size_compressed=result.get("size_compressed", 0),
                workspace_path=workspace_path,
                creation_time_ms=creation_time,
                base_checkpoint_id=base_checkpoint_id,
                files_changed=result.get("files_changed", 0),
            )

            logger.info(
                f"[CHECKPOINT] Incremental checkpoint created: {checkpoint_name} "
                f"({checkpoint.files_changed} files changed) "
                f"in {creation_time}ms"
            )

            return checkpoint

        except Exception as e:
            logger.error(f"[CHECKPOINT] Incremental checkpoint failed: {e}")
            raise

    async def restore(
        self,
        checkpoint_id: str,
        target_host: str,
        target_port: int,
        workspace_path: str = "/workspace",
    ) -> RestoreResult:
        """
        Restaura checkpoint para uma máquina.

        Args:
            checkpoint_id: ID do checkpoint
            target_host: Host de destino
            target_port: Porta SSH de destino
            workspace_path: Path do workspace

        Returns:
            RestoreResult com detalhes
        """
        start_time = time.time()

        logger.info(f"[CHECKPOINT] Restoring {checkpoint_id} to {target_host}:{target_port}")

        try:
            result = self.snapshot_service.restore_snapshot(
                snapshot_id=checkpoint_id,
                ssh_host=target_host,
                ssh_port=target_port,
                workspace_path=workspace_path,
            )

            total_time = int((time.time() - start_time) * 1000)

            restore_result = RestoreResult(
                success=True,
                checkpoint_id=checkpoint_id,
                target_host=target_host,
                target_port=target_port,
                download_time_ms=int(result.get("download_time", 0) * 1000),
                decompress_time_ms=int(result.get("decompress_time", 0) * 1000),
                total_time_ms=total_time,
                files_restored=result.get("files_restored", 0),
            )

            logger.info(
                f"[CHECKPOINT] Restore complete: {checkpoint_id} "
                f"in {total_time}ms"
            )

            return restore_result

        except Exception as e:
            logger.error(f"[CHECKPOINT] Restore failed: {e}")
            return RestoreResult(
                success=False,
                checkpoint_id=checkpoint_id,
                target_host=target_host,
                target_port=target_port,
                error=str(e),
            )

    def list_checkpoints(
        self,
        machine_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Lista checkpoints disponíveis"""
        try:
            snapshots = self.snapshot_service.list_snapshots(
                instance_id=str(machine_id) if machine_id else None
            )
            return snapshots
        except Exception as e:
            logger.error(f"[CHECKPOINT] Failed to list checkpoints: {e}")
            return []

    def delete(self, checkpoint_id: str) -> bool:
        """Deleta um checkpoint"""
        try:
            self.snapshot_service.delete_snapshot(checkpoint_id)
            logger.info(f"[CHECKPOINT] Deleted: {checkpoint_id}")
            return True
        except Exception as e:
            logger.error(f"[CHECKPOINT] Delete failed: {e}")
            return False

    def get_latest(self, machine_id: int) -> Optional[Checkpoint]:
        """Obtém checkpoint mais recente de uma máquina"""
        checkpoints = self.list_checkpoints(machine_id)
        if not checkpoints:
            return None

        # Ordenar por timestamp
        sorted_checkpoints = sorted(
            checkpoints,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )

        if sorted_checkpoints:
            cp = sorted_checkpoints[0]
            return Checkpoint(
                checkpoint_id=cp.get("snapshot_id", ""),
                machine_id=machine_id,
                checkpoint_type=CheckpointType.FULL,
                created_at=datetime.fromisoformat(cp.get("created_at", "")),
                size_compressed=cp.get("size_compressed", 0),
            )

        return None


# Singleton
_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager(
    storage_endpoint: Optional[str] = None,
    storage_bucket: Optional[str] = None,
) -> CheckpointManager:
    """Obtém instância do CheckpointManager"""
    global _manager
    if _manager is None:
        _manager = CheckpointManager(
            storage_endpoint=storage_endpoint or os.getenv("B2_ENDPOINT", ""),
            storage_bucket=storage_bucket or os.getenv("B2_BUCKET", "dumoncloud-snapshot"),
        )
    return _manager
