"""
Machines Models - Dataclasses para gestão de máquinas
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class MachineStatus(str, Enum):
    """Status da máquina"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"
    PROVISIONING = "provisioning"


@dataclass
class MachineInfo:
    """Informações de uma máquina"""
    machine_id: int
    user_id: str
    status: MachineStatus

    # GPU info
    gpu_type: str = ""
    gpu_count: int = 1
    gpu_ram_mb: int = 0

    # Provider info
    provider: str = "vast"
    instance_id: Optional[int] = None
    ssh_host: str = ""
    ssh_port: int = 22

    # Pricing
    price_per_hour: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_seen_at: Optional[datetime] = None

    # Stats
    total_uptime_hours: float = 0.0
    total_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "gpu_type": self.gpu_type,
            "gpu_count": self.gpu_count,
            "provider": self.provider,
            "price_per_hour": self.price_per_hour,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class MachineStats:
    """Estatísticas de uma máquina"""
    machine_id: int

    # Uptime
    total_uptime_hours: float = 0.0
    uptime_percentage: float = 0.0

    # Cost
    total_cost: float = 0.0
    avg_hourly_cost: float = 0.0

    # Performance
    avg_gpu_utilization: float = 0.0
    avg_memory_utilization: float = 0.0

    # Reliability
    failover_count: int = 0
    error_count: int = 0

    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "total_uptime_hours": self.total_uptime_hours,
            "uptime_percentage": self.uptime_percentage,
            "total_cost": self.total_cost,
            "failover_count": self.failover_count,
        }


@dataclass
class HostBlacklist:
    """Host na blacklist"""
    host_id: str
    provider: str
    reason: str
    blacklisted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Stats
    failure_count: int = 0
    last_failure_reason: str = ""

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "host_id": self.host_id,
            "provider": self.provider,
            "reason": self.reason,
            "blacklisted_at": self.blacklisted_at.isoformat(),
            "failure_count": self.failure_count,
        }
