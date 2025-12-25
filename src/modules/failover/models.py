"""
Failover Models - Dataclasses e Enums para o módulo de failover
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


class FailoverStrategy(str, Enum):
    """Estratégias de failover disponíveis"""
    WARM_POOL = "warm_pool"       # GPU standby no mesmo host (~30-60s)
    CPU_STANDBY = "cpu_standby"   # Snapshot + nova GPU (~5-10min)
    BOTH = "both"                 # Tenta warm pool, depois CPU standby
    DISABLED = "disabled"         # Failover desabilitado


class FailoverPhase(str, Enum):
    """Fases do processo de failover"""
    IDLE = "idle"
    DETECTING = "detecting"                  # Detectando falha
    WARM_POOL_CHECK = "warm_pool_check"      # Verificando warm pool
    WARM_POOL_FAILOVER = "warm_pool_failover"
    CPU_STANDBY_CHECK = "cpu_standby_check"  # Verificando CPU standby
    SNAPSHOT_CREATION = "snapshot_creation"   # Criando snapshot
    GPU_PROVISIONING = "gpu_provisioning"     # Provisionando nova GPU
    SNAPSHOT_RESTORE = "snapshot_restore"     # Restaurando snapshot
    VALIDATION = "validation"                 # Validando restore
    INFERENCE_TEST = "inference_test"         # Testando inferência
    COMPLETED = "completed"
    FAILED = "failed"


class FailoverStatus(str, Enum):
    """Status geral do failover"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FailoverConfig:
    """Configuração de failover para uma máquina"""
    machine_id: int
    strategy: FailoverStrategy = FailoverStrategy.BOTH

    # Warm Pool config
    warm_pool_enabled: bool = True
    warm_pool_timeout_seconds: int = 120

    # CPU Standby config
    cpu_standby_enabled: bool = True
    snapshot_timeout_seconds: int = 300
    gpu_provisioning_timeout_seconds: int = 180
    restore_timeout_seconds: int = 300

    # GPU requirements
    min_gpu_ram_mb: int = 10000
    max_gpu_price: float = 1.0
    preferred_gpu_models: List[str] = field(default_factory=list)

    # Retry config
    max_retries: int = 2
    retry_delay_seconds: int = 30

    # Notifications
    notify_on_start: bool = True
    notify_on_success: bool = True
    notify_on_failure: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "strategy": self.strategy.value,
            "warm_pool_enabled": self.warm_pool_enabled,
            "warm_pool_timeout_seconds": self.warm_pool_timeout_seconds,
            "cpu_standby_enabled": self.cpu_standby_enabled,
            "snapshot_timeout_seconds": self.snapshot_timeout_seconds,
            "gpu_provisioning_timeout_seconds": self.gpu_provisioning_timeout_seconds,
            "restore_timeout_seconds": self.restore_timeout_seconds,
            "min_gpu_ram_mb": self.min_gpu_ram_mb,
            "max_gpu_price": self.max_gpu_price,
            "preferred_gpu_models": self.preferred_gpu_models,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
        }


@dataclass
class FailoverResult:
    """Resultado completo de um failover"""
    success: bool
    failover_id: str
    machine_id: int

    # Estratégia
    strategy_attempted: str  # "warm_pool", "cpu_standby", "both"
    strategy_succeeded: Optional[str] = None

    # GPU original
    original_gpu_id: Optional[int] = None
    original_ssh_host: Optional[str] = None
    original_ssh_port: Optional[int] = None

    # Nova GPU
    new_gpu_id: Optional[int] = None
    new_ssh_host: Optional[str] = None
    new_ssh_port: Optional[int] = None
    new_gpu_name: Optional[str] = None

    # Snapshot info
    snapshot_id: Optional[str] = None
    snapshot_size_bytes: int = 0
    snapshot_type: Optional[str] = None  # "full" ou "incremental"
    base_snapshot_id: Optional[str] = None
    files_changed: Optional[int] = None

    # Timing (milliseconds)
    warm_pool_attempt_ms: int = 0
    snapshot_creation_ms: int = 0
    gpu_provisioning_ms: int = 0
    restore_ms: int = 0
    validation_ms: int = 0
    inference_test_ms: int = 0
    total_ms: int = 0

    # Inference test
    inference_success: Optional[bool] = None
    inference_response: Optional[str] = None

    # Errors
    error: Optional[str] = None
    failed_phase: Optional[str] = None
    warm_pool_error: Optional[str] = None
    cpu_standby_error: Optional[str] = None

    # Metrics
    gpus_tried: int = 0
    rounds_attempted: int = 0
    retries: int = 0

    # History
    phase_history: List[tuple] = field(default_factory=list)
    phase_timings: Dict[str, int] = field(default_factory=dict)

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "failover_id": self.failover_id,
            "machine_id": self.machine_id,
            "strategy_attempted": self.strategy_attempted,
            "strategy_succeeded": self.strategy_succeeded,
            "original_gpu_id": self.original_gpu_id,
            "new_gpu_id": self.new_gpu_id,
            "new_ssh_host": self.new_ssh_host,
            "new_ssh_port": self.new_ssh_port,
            "new_gpu_name": self.new_gpu_name,
            "snapshot_id": self.snapshot_id,
            "snapshot_type": self.snapshot_type,
            "total_ms": self.total_ms,
            "phase_timings": self.phase_timings,
            "error": self.error,
            "failed_phase": self.failed_phase,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class FailoverEvent:
    """Evento de failover para logging/auditoria"""
    event_id: str
    failover_id: str
    machine_id: int

    event_type: str  # "started", "phase_changed", "completed", "failed"
    phase: FailoverPhase
    status: FailoverStatus

    timestamp: datetime = field(default_factory=datetime.now)

    # Detalhes
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    # Métricas
    duration_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "failover_id": self.failover_id,
            "machine_id": self.machine_id,
            "event_type": self.event_type,
            "phase": self.phase.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "details": self.details,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }
