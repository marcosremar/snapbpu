"""
GPU Provisioning Strategies

Strategy Pattern for machine provisioning:
- RaceStrategy: Create multiple machines in parallel, first ready wins
- SingleStrategy: Create single machine and wait
- ColdStartStrategy: Resume paused instances with automatic failover

New Features:
- provision_with_failover: Verify SSH works, retry on different machine if fails
- resume_with_failover: Resume paused instance, launch backup if SSH fails

Usage:
    from src.services.gpu.strategies import RaceStrategy, MachineProvisionerService, ProvisionConfig

    config = ProvisionConfig(
        max_price=1.0,
        min_gpu_ram=10000,
        disk_space=50,
    )

    # Standard provisioning
    provisioner = MachineProvisionerService(api_key, strategy=RaceStrategy())
    result = provisioner.provision(config)

    # Provisioning with SSH failover (recommended for production)
    result = provisioner.provision_with_failover(config)

    # Cold start with failover (for resuming paused instances)
    from src.services.gpu.strategies import resume_with_failover
    result = resume_with_failover(
        vast_service=vast_client,
        instance_id=12345,
        backup_config=config,
        parallel_backup=True,
    )
"""
from .base import (
    ProvisioningStrategy,
    ProvisionConfig,
    ProvisionResult,
    MachineCandidate,
)
from .race import RaceStrategy
from .single import SingleStrategy
from .coldstart import ColdStartStrategy, ColdStartConfig, resume_with_failover
from .service import MachineProvisionerService

__all__ = [
    "ProvisioningStrategy",
    "ProvisionConfig",
    "ProvisionResult",
    "MachineCandidate",
    "RaceStrategy",
    "SingleStrategy",
    "ColdStartStrategy",
    "ColdStartConfig",
    "MachineProvisionerService",
    "resume_with_failover",
]
