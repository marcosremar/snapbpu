"""
Serverless GPU Module

Funcionalidades de GPU Serverless com auto-pause/resume e checkpoint de estado.

Principais componentes:
- ServerlessManager: Gerencia auto-pause/resume baseado em idle
- ServerlessService: Serviço com banco de dados, auto-destroy, fallback
- GPUCheckpointService: Checkpoint/restore de estado GPU (CUDA + CRIU)

Database Schema (PostgreSQL):
- serverless.serverless_user_settings: Configuração por usuário
- serverless.serverless_instances: Instâncias com serverless ativo
- serverless.serverless_snapshots: Snapshots para recovery
- serverless.serverless_events: Log de eventos

Modos disponíveis:
- FAST: CPU Standby com checkpoint, recovery <1s
- ECONOMIC: Pause/resume VAST.ai, recovery ~7s
- SPOT: Instâncias spot com failover, recovery ~30s

Exemplo de uso:
    from src.modules.serverless import ServerlessService, get_serverless_manager

    # Usar o novo serviço com banco de dados
    service = ServerlessService(session_factory, vast_provider)
    service.configure_user(
        user_id="user123",
        scale_down_timeout=2,      # Pausa após 2s sem requisição
        destroy_after_hours=24,    # Destrói após 24h pausado
    )

    # Ou usar o manager legado (in-memory)
    manager = get_serverless_manager()
    manager.configure(vast_api_key="...")
    manager.enable(instance_id=12345, mode="fast", idle_timeout_seconds=30)
"""

from .manager import (
    ServerlessManager,
    ServerlessMode,
    ServerlessConfig,
    ServerlessStats,
    get_serverless_manager,
)

from .checkpoint import (
    GPUCheckpointService,
    GPUCheckpoint,
    get_checkpoint_service,
)

from .config import ServerlessSettings

# Database models
from .models import (
    ServerlessUserSettings,
    ServerlessInstance,
    ServerlessSnapshot,
    ServerlessEvent,
    ServerlessModeEnum,
    InstanceStateEnum,
    EventTypeEnum,
    create_serverless_schema,
)

# Repository & Service
from .repository import ServerlessRepository
from .service import ServerlessService, ScaleDownResult, ScaleUpResult

# Fallback strategies
from .fallback import (
    FallbackResult,
    SnapshotFallbackStrategy,
    DiskMigrationStrategy,
    FallbackOrchestrator,
    get_fallback_orchestrator,
)

__all__ = [
    # Manager (legado, in-memory)
    "ServerlessManager",
    "ServerlessMode",
    "ServerlessConfig",
    "ServerlessStats",
    "get_serverless_manager",
    # Checkpoint
    "GPUCheckpointService",
    "GPUCheckpoint",
    "get_checkpoint_service",
    # Config
    "ServerlessSettings",
    # Database Models
    "ServerlessUserSettings",
    "ServerlessInstance",
    "ServerlessSnapshot",
    "ServerlessEvent",
    "ServerlessModeEnum",
    "InstanceStateEnum",
    "EventTypeEnum",
    "create_serverless_schema",
    # Repository & Service
    "ServerlessRepository",
    "ServerlessService",
    "ScaleDownResult",
    "ScaleUpResult",
    # Fallback strategies
    "FallbackResult",
    "SnapshotFallbackStrategy",
    "DiskMigrationStrategy",
    "FallbackOrchestrator",
    "get_fallback_orchestrator",
]
