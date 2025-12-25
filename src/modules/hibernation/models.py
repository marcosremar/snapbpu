"""
Hibernation Models - Dataclasses para hibernação
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class HibernationState(str, Enum):
    """Estado de hibernação"""
    ACTIVE = "active"
    IDLE = "idle"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    ERROR = "error"


class HibernationEventType(str, Enum):
    """Tipo de evento de hibernação"""
    IDLE_DETECTED = "idle_detected"
    AUTO_PAUSED = "auto_paused"
    MANUAL_PAUSED = "manual_paused"
    RESUMED = "resumed"
    ERROR = "error"


@dataclass
class HibernationEvent:
    """Evento de hibernação"""
    machine_id: int
    event_type: HibernationEventType
    timestamp: datetime = field(default_factory=datetime.now)

    # Stats
    idle_hours: float = 0.0
    savings_usd: float = 0.0

    # Details
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "idle_hours": self.idle_hours,
            "savings_usd": self.savings_usd,
            "details": self.details,
        }


@dataclass
class IdleConfig:
    """Configuração de detecção de idle"""
    machine_id: int

    # Thresholds
    idle_threshold_minutes: int = 15
    gpu_utilization_threshold: float = 5.0  # %
    cpu_utilization_threshold: float = 10.0  # %

    # Behavior
    auto_pause_enabled: bool = True
    pause_delay_minutes: int = 5

    # Schedule
    schedule_enabled: bool = False
    schedule_pause_time: str = "22:00"
    schedule_resume_time: str = "08:00"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "idle_threshold_minutes": self.idle_threshold_minutes,
            "auto_pause_enabled": self.auto_pause_enabled,
            "schedule_enabled": self.schedule_enabled,
        }


@dataclass
class MachineIdleStatus:
    """Status de idle de uma máquina"""
    machine_id: int
    state: HibernationState

    # Current metrics
    gpu_utilization: float = 0.0
    cpu_utilization: float = 0.0

    # Idle tracking
    idle_since: Optional[datetime] = None
    idle_minutes: float = 0.0

    # Pause info
    paused_at: Optional[datetime] = None
    total_paused_hours: float = 0.0
    total_savings_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "state": self.state.value,
            "gpu_utilization": self.gpu_utilization,
            "cpu_utilization": self.cpu_utilization,
            "idle_minutes": self.idle_minutes,
            "total_savings_usd": self.total_savings_usd,
        }
