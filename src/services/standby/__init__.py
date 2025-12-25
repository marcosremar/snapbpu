"""Standby services - failover, hibernation, CPU standby"""

from .cpu import CPUStandbyService
from .manager import StandbyManager
from .hibernation import AutoHibernationManager
from .failover import FailoverService, FailoverResult, execute_failover

# Re-export from modules.serverless for backwards compatibility
from src.modules.serverless import (
    ServerlessManager,
    ServerlessMode,
    get_serverless_manager,
)

__all__ = [
    "CPUStandbyService",
    "StandbyManager",
    "AutoHibernationManager",
    "FailoverService",
    "FailoverResult",
    "execute_failover",
    # Serverless (from modules)
    "ServerlessManager",
    "ServerlessMode",
    "get_serverless_manager",
]
