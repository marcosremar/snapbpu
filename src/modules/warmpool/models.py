"""
Warmpool Models - Dataclasses para pool de GPUs
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class WarmPoolState(str, Enum):
    """Estado do warm pool"""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    FAILOVER = "failover"
    ERROR = "error"


@dataclass
class WarmPoolStatus:
    """Status do warm pool"""
    machine_id: int
    state: WarmPoolState

    # Primary GPU
    primary_gpu_id: Optional[int] = None
    primary_ssh_host: Optional[str] = None
    primary_ssh_port: Optional[int] = None
    primary_gpu_name: str = ""

    # Standby GPU
    standby_gpu_id: Optional[int] = None
    standby_ssh_host: Optional[str] = None
    standby_ssh_port: Optional[int] = None
    standby_gpu_name: str = ""

    # Stats
    failover_count: int = 0
    last_failover_at: Optional[datetime] = None
    uptime_hours: float = 0.0

    # Error
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "state": self.state.value,
            "primary_gpu_id": self.primary_gpu_id,
            "standby_gpu_id": self.standby_gpu_id,
            "failover_count": self.failover_count,
            "uptime_hours": self.uptime_hours,
            "error_message": self.error_message,
        }


@dataclass
class WarmPoolConfig:
    """Configuração do warm pool"""
    machine_id: int

    # GPU requirements
    min_gpu_ram_mb: int = 10000
    max_gpu_price: float = 1.0
    preferred_gpu_types: List[str] = field(default_factory=lambda: ["RTX 4090", "RTX 3090"])

    # Pool settings
    standby_count: int = 1
    preemption_buffer_hours: float = 0.5

    # Failover settings
    auto_failover: bool = True
    failover_timeout_seconds: int = 120

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "min_gpu_ram_mb": self.min_gpu_ram_mb,
            "max_gpu_price": self.max_gpu_price,
            "standby_count": self.standby_count,
            "auto_failover": self.auto_failover,
        }
