"""
Hibernation Module - Auto-pause e hibernação inteligente

Este módulo gerencia hibernação automática:
- Detecção de idle
- Auto-pause
- Wake-up triggers
- Agendamento

Uso:
    from src.modules.hibernation import (
        HibernationManager,
        get_hibernation_manager,
    )

    manager = get_hibernation_manager()
    await manager.start_monitoring(machine_id=123)
    await manager.pause(machine_id=123)
    await manager.resume(machine_id=123)
"""

from .models import (
    HibernationState,
    HibernationEvent,
    IdleConfig,
)

from .manager import (
    HibernationManager,
    get_hibernation_manager,
)

from .detector import (
    IdleDetector,
    get_idle_detector,
)

__all__ = [
    "HibernationState",
    "HibernationEvent",
    "IdleConfig",
    "HibernationManager",
    "get_hibernation_manager",
    "IdleDetector",
    "get_idle_detector",
]
