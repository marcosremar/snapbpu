"""Standby services - failover, hibernation, CPU standby"""

from .cpu import CPUStandbyService
from .manager import StandbyManager
from .hibernation import AutoHibernationManager
from .failover import FailoverService, FailoverResult, execute_failover

__all__ = [
    "CPUStandbyService",
    "StandbyManager",
    "AutoHibernationManager",
    "FailoverService",
    "FailoverResult",
    "execute_failover",
]
