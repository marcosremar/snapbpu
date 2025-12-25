"""
Warmpool Module - Pool de GPUs pré-aquecidas

Este módulo gerencia pool de GPUs prontas para uso:
- Provisioning antecipado
- Volume management
- Failover rápido

Uso:
    from src.modules.warmpool import (
        WarmPoolManager,
        get_warmpool_manager,
    )

    manager = get_warmpool_manager(machine_id=123)
    await manager.start()
    status = manager.get_status()
"""

from .models import (
    WarmPoolState,
    WarmPoolStatus,
    WarmPoolConfig,
)

from .manager import (
    WarmPoolManager,
    get_warmpool_manager,
)

__all__ = [
    "WarmPoolState",
    "WarmPoolStatus",
    "WarmPoolConfig",
    "WarmPoolManager",
    "get_warmpool_manager",
]
