"""
Sync Models - Dataclasses para sincronização
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SyncStatus(str, Enum):
    """Status de sincronização"""
    IDLE = "idle"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class CheckpointType(str, Enum):
    """Tipo de checkpoint"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


@dataclass
class Checkpoint:
    """Checkpoint de workspace"""
    checkpoint_id: str
    machine_id: int
    checkpoint_type: CheckpointType
    created_at: datetime = field(default_factory=datetime.now)

    # Storage info
    storage_path: str = ""
    storage_provider: str = "b2"  # b2, r2, s3, wasabi

    # Size info
    size_original: int = 0
    size_compressed: int = 0
    compression_ratio: float = 1.0

    # Content info
    num_files: int = 0
    num_chunks: int = 0
    workspace_path: str = "/workspace"

    # Timing
    creation_time_ms: int = 0
    upload_time_ms: int = 0

    # Incremental info
    base_checkpoint_id: Optional[str] = None
    files_changed: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "machine_id": self.machine_id,
            "checkpoint_type": self.checkpoint_type.value,
            "created_at": self.created_at.isoformat(),
            "storage_path": self.storage_path,
            "storage_provider": self.storage_provider,
            "size_original": self.size_original,
            "size_compressed": self.size_compressed,
            "compression_ratio": self.compression_ratio,
            "num_files": self.num_files,
            "creation_time_ms": self.creation_time_ms,
            "base_checkpoint_id": self.base_checkpoint_id,
            "files_changed": self.files_changed,
        }


@dataclass
class SyncProgress:
    """Progresso de sincronização"""
    status: SyncStatus
    progress_pct: float = 0.0
    bytes_transferred: int = 0
    bytes_total: int = 0
    files_transferred: int = 0
    files_total: int = 0
    current_file: str = ""
    started_at: Optional[datetime] = None
    eta_seconds: float = 0.0
    speed_bytes_per_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "progress_pct": self.progress_pct,
            "bytes_transferred": self.bytes_transferred,
            "bytes_total": self.bytes_total,
            "files_transferred": self.files_transferred,
            "files_total": self.files_total,
            "current_file": self.current_file,
            "eta_seconds": self.eta_seconds,
            "speed_mbps": round(self.speed_bytes_per_sec / 1024 / 1024, 2),
        }


@dataclass
class RestoreResult:
    """Resultado de restore"""
    success: bool
    checkpoint_id: str
    target_host: str
    target_port: int

    # Timing
    download_time_ms: int = 0
    decompress_time_ms: int = 0
    total_time_ms: int = 0

    # Stats
    files_restored: int = 0
    bytes_restored: int = 0

    # Error
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "checkpoint_id": self.checkpoint_id,
            "target_host": self.target_host,
            "target_port": self.target_port,
            "download_time_ms": self.download_time_ms,
            "decompress_time_ms": self.decompress_time_ms,
            "total_time_ms": self.total_time_ms,
            "files_restored": self.files_restored,
            "bytes_restored": self.bytes_restored,
            "error": self.error,
        }


@dataclass
class SyncConfig:
    """Configuração de sync"""
    machine_id: int

    # Storage
    storage_provider: str = "b2"
    storage_bucket: str = "dumoncloud-snapshot"
    storage_endpoint: str = ""

    # Compression
    compression_algorithm: str = "lz4"
    chunk_size_mb: int = 64

    # Paths
    workspace_path: str = "/workspace"
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.tmp", "*.log", "__pycache__", ".git"
    ])

    # Realtime sync
    realtime_enabled: bool = True
    realtime_interval_seconds: int = 5

    # Incremental
    incremental_enabled: bool = True
    full_backup_interval_hours: int = 24

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "storage_provider": self.storage_provider,
            "storage_bucket": self.storage_bucket,
            "compression_algorithm": self.compression_algorithm,
            "workspace_path": self.workspace_path,
            "realtime_enabled": self.realtime_enabled,
            "incremental_enabled": self.incremental_enabled,
        }
