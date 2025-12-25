"""
Machines Module - Gestão de máquinas GPU

Este módulo consolida a gestão de máquinas:
- Histórico de máquinas
- Blacklist de hosts
- Estatísticas de performance
- Health monitoring

Uso:
    from src.modules.machines import (
        MachineManager,
        MachineHistory,
        get_machine_manager,
    )

    manager = get_machine_manager()
    history = manager.get_history(machine_id=123)
    manager.blacklist_host(host_id="host-456", reason="Poor performance")
"""

from .models import (
    MachineStatus,
    MachineInfo,
    MachineStats,
    HostBlacklist,
)

from .service import (
    MachineManager,
    get_machine_manager,
)

from .history import (
    MachineHistory,
    get_machine_history,
)

__all__ = [
    "MachineStatus",
    "MachineInfo",
    "MachineStats",
    "HostBlacklist",
    "MachineManager",
    "get_machine_manager",
    "MachineHistory",
    "get_machine_history",
]
