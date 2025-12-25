"""
Failover Module - Orquestração unificada de failover GPU

Este módulo consolida toda a lógica de failover:
- Warm Pool: Failover rápido via GPU standby (~30-60s)
- CPU Standby: Failover via snapshot + nova GPU (~5-10min)
- Recovery: Auto-recovery e retry strategies

Uso:
    from src.modules.failover import FailoverOrchestrator, execute_failover

    # Método 1: Via orquestrador
    orchestrator = FailoverOrchestrator(vast_api_key="...")
    result = await orchestrator.execute(machine_id=123, gpu_id=456, ...)

    # Método 2: Função direta
    result = await execute_failover(machine_id=123, gpu_id=456, ...)

Estratégias disponíveis:
- FailoverStrategy.WARM_POOL: Usa GPU standby no mesmo host
- FailoverStrategy.CPU_STANDBY: Usa snapshot + provisiona nova GPU
- FailoverStrategy.BOTH: Tenta warm pool primeiro, depois CPU standby
- FailoverStrategy.DISABLED: Desabilita failover
"""

from .models import (
    FailoverStrategy,
    FailoverPhase,
    FailoverStatus,
    FailoverResult,
    FailoverEvent,
    FailoverConfig,
)

from .orchestrator import (
    FailoverOrchestrator,
    get_failover_orchestrator,
)

from .service import (
    FailoverService,
    execute_failover,
)

__all__ = [
    # Models
    "FailoverStrategy",
    "FailoverPhase",
    "FailoverStatus",
    "FailoverResult",
    "FailoverEvent",
    "FailoverConfig",
    # Orchestrator
    "FailoverOrchestrator",
    "get_failover_orchestrator",
    # Service
    "FailoverService",
    "execute_failover",
]
