"""
Sync Module - Sincronização de dados GPU/CPU

Este módulo consolida toda a lógica de sincronização:
- Checkpoint management (create, restore)
- Real-time sync (lsyncd/rsync)
- Incremental backup

Uso:
    from src.modules.sync import (
        CheckpointManager,
        SyncService,
        get_checkpoint_manager,
    )

    # Criar checkpoint
    manager = get_checkpoint_manager()
    checkpoint = await manager.create(
        machine_id=123,
        ssh_host="gpu.vast.ai",
        ssh_port=12345,
    )

    # Restaurar
    await manager.restore(
        checkpoint_id=checkpoint.checkpoint_id,
        target_host="new-gpu.vast.ai",
        target_port=12346,
    )
"""

from .models import (
    SyncStatus,
    CheckpointType,
    Checkpoint,
    SyncProgress,
    RestoreResult,
)

from .checkpoint import (
    CheckpointManager,
    get_checkpoint_manager,
)

from .service import (
    SyncService,
    get_sync_service,
)

from .realtime import (
    RealtimeSyncManager,
    get_realtime_sync,
)

__all__ = [
    # Models
    "SyncStatus",
    "CheckpointType",
    "Checkpoint",
    "SyncProgress",
    "RestoreResult",
    # Checkpoint
    "CheckpointManager",
    "get_checkpoint_manager",
    # Service
    "SyncService",
    "get_sync_service",
    # Realtime
    "RealtimeSyncManager",
    "get_realtime_sync",
]
