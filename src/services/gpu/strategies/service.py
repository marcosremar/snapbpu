"""
Machine Provisioner Service

Unified entry point for GPU machine provisioning.
Uses Strategy Pattern for different provisioning approaches.
"""
import logging
from typing import Optional, Dict, Any, Type

from .base import ProvisioningStrategy, ProvisionConfig, ProvisionResult
from .race import RaceStrategy
from .single import SingleStrategy

logger = logging.getLogger(__name__)


# Registry of available strategies
STRATEGIES: Dict[str, Type[ProvisioningStrategy]] = {
    "race": RaceStrategy,
    "single": SingleStrategy,
}

# Default strategy
DEFAULT_STRATEGY = "race"


class MachineProvisionerService:
    """
    Unified service for GPU machine provisioning.

    This service is the single entry point for provisioning machines.
    It uses pluggable strategies for different provisioning approaches.

    Usage:
        from src.services.gpu.strategies import MachineProvisionerService, ProvisionConfig

        # Using default race strategy
        provisioner = MachineProvisionerService(api_key)
        result = provisioner.provision(config)

        # Using specific strategy
        result = provisioner.provision(config, strategy="single")

        # Using strategy instance
        provisioner = MachineProvisionerService(api_key, strategy=RaceStrategy())
        result = provisioner.provision(config)
    """

    def __init__(
        self,
        api_key: str,
        strategy: Optional[ProvisioningStrategy] = None,
    ):
        """
        Initialize provisioner.

        Args:
            api_key: Vast.ai API key
            strategy: Optional strategy instance. If None, uses RaceStrategy.
        """
        # Lazy import to avoid circular dependency
        from src.services.gpu.vast import VastService

        self.api_key = api_key
        self.vast_service = VastService(api_key)
        self._default_strategy = strategy or RaceStrategy()

    def provision(
        self,
        config: ProvisionConfig,
        strategy: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Provision a GPU machine.

        Args:
            config: Provisioning configuration
            strategy: Strategy name ("race", "single") or None for default
            progress_callback: Optional callback for progress updates
                               Signature: callback(status: str, message: str, progress: int)

        Returns:
            ProvisionResult with success/failure and machine info
        """
        # Get strategy
        if strategy:
            strategy_class = STRATEGIES.get(strategy)
            if not strategy_class:
                logger.warning(f"Unknown strategy '{strategy}', using default")
                strategy_instance = self._default_strategy
            else:
                strategy_instance = strategy_class()
        else:
            strategy_instance = self._default_strategy

        logger.info(f"[MachineProvisioner] Using strategy: {strategy_instance.name}")

        # Execute provisioning
        result = strategy_instance.provision(
            config=config,
            vast_service=self.vast_service,
            progress_callback=progress_callback,
        )

        # Log result
        if result.success:
            logger.info(
                f"[MachineProvisioner] Success: {result.gpu_name} "
                f"({result.ssh_host}:{result.ssh_port}) in {result.total_time_seconds:.1f}s"
            )
        else:
            logger.warning(f"[MachineProvisioner] Failed: {result.error}")

        return result

    def provision_fast(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 1.0,
        disk_space: int = 50,
        image: Optional[str] = None,
        onstart_cmd: Optional[str] = None,
        ports: Optional[list] = None,
        label: str = "dumont:provisioned",
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Quick provisioning with common defaults.

        Uses RaceStrategy for fastest results.

        Args:
            gpu_name: Optional GPU filter (e.g., "RTX 4090")
            max_price: Maximum price per hour
            disk_space: Disk space in GB
            image: Docker image (default: pytorch)
            onstart_cmd: Command to run on start
            ports: Ports to expose (default: [22])
            label: Instance label
            progress_callback: Progress callback

        Returns:
            ProvisionResult
        """
        config = ProvisionConfig(
            gpu_name=gpu_name,
            max_price=max_price,
            disk_space=disk_space,
            image=image,
            onstart_cmd=onstart_cmd,
            ports=ports or [22],
            label=label,
        )

        return self.provision(config, strategy="race", progress_callback=progress_callback)

    def provision_cheap(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 0.5,
        disk_space: int = 50,
        image: Optional[str] = None,
        onstart_cmd: Optional[str] = None,
        ports: Optional[list] = None,
        label: str = "dumont:provisioned",
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Cost-optimized provisioning.

        Uses SingleStrategy and lower price limit.

        Args:
            gpu_name: Optional GPU filter
            max_price: Maximum price per hour (lower default)
            disk_space: Disk space in GB
            image: Docker image
            onstart_cmd: Command to run on start
            ports: Ports to expose
            label: Instance label
            progress_callback: Progress callback

        Returns:
            ProvisionResult
        """
        config = ProvisionConfig(
            gpu_name=gpu_name,
            max_price=max_price,
            disk_space=disk_space,
            image=image,
            onstart_cmd=onstart_cmd,
            ports=ports or [22],
            label=label,
        )

        return self.provision(config, strategy="single", progress_callback=progress_callback)

    def get_available_strategies(self) -> Dict[str, str]:
        """List available strategies and their descriptions"""
        return {
            "race": "Create multiple machines in parallel, first ready wins (fastest)",
            "single": "Create single machine and wait (cheapest)",
        }

    def provision_with_failover(
        self,
        config: ProvisionConfig,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Provision with automatic SSH failover.

        This is the recommended method for production use:
        1. Run race strategy to get a machine
        2. Verify SSH actually works with a real command
        3. If SSH fails, destroy machine and try another
        4. Repeat up to config.max_ssh_retries times

        Use this when you need guaranteed working SSH, especially for:
        - Model deployment
        - Long-running jobs
        - Cold start from pause/hibernation

        Args:
            config: Provisioning configuration (with max_ssh_retries, ssh_command_timeout)
            progress_callback: Optional callback for progress updates

        Returns:
            ProvisionResult with verified working SSH
        """
        strategy = RaceStrategy()
        result = strategy.provision_with_failover(
            config=config,
            vast_service=self.vast_service,
            progress_callback=progress_callback,
        )

        if result.success:
            logger.info(
                f"[MachineProvisioner] Failover success: {result.gpu_name} "
                f"({result.ssh_host}:{result.ssh_port}) in {result.total_time_seconds:.1f}s"
            )
        else:
            logger.warning(f"[MachineProvisioner] Failover failed: {result.error}")

        return result

    def resume_with_failover(
        self,
        instance_id: int,
        backup_config: Optional[ProvisionConfig] = None,
        parallel_backup: bool = True,
        resume_timeout: int = 60,
        total_timeout: int = 180,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Resume a paused instance with automatic failover.

        If the resumed instance doesn't have working SSH, automatically
        launch a backup machine and race between them.

        Use this for:
        - Resuming from serverless/economic mode
        - Cold start from hibernation
        - Any pause/resume operation that needs reliability

        Args:
            instance_id: Instance to resume
            backup_config: Config for backup machine (optional, creates similar GPU)
            parallel_backup: If True, launch backup immediately in parallel
            resume_timeout: Seconds to wait before launching backup (if not parallel)
            total_timeout: Max time to wait for either machine
            progress_callback: Optional callback for progress updates

        Returns:
            ProvisionResult with the winning machine (resume or backup)

        Example:
            result = provisioner.resume_with_failover(
                instance_id=12345,
                backup_config=ProvisionConfig(max_price=1.0),
                parallel_backup=True,
            )

            if result.success:
                print(f"Ready at {result.ssh_host}:{result.ssh_port}")
        """
        from .coldstart import ColdStartStrategy, ColdStartConfig

        coldstart_config = ColdStartConfig(
            instance_id=instance_id,
            backup_config=backup_config,
            parallel_backup=parallel_backup,
            resume_timeout=resume_timeout,
            total_timeout=total_timeout,
        )

        strategy = ColdStartStrategy()
        result = strategy.resume_with_failover(
            coldstart_config=coldstart_config,
            vast_service=self.vast_service,
            progress_callback=progress_callback,
        )

        if result.success:
            logger.info(
                f"[MachineProvisioner] Resume success: {result.gpu_name} "
                f"({result.ssh_host}:{result.ssh_port}) in {result.total_time_seconds:.1f}s"
            )
        else:
            logger.warning(f"[MachineProvisioner] Resume failed: {result.error}")

        return result


# Convenience function for quick usage
def provision_machine(
    api_key: str,
    config: Optional[ProvisionConfig] = None,
    strategy: str = "race",
    **kwargs,
) -> ProvisionResult:
    """
    Quick function to provision a GPU machine.

    Args:
        api_key: Vast.ai API key
        config: ProvisionConfig or None to use kwargs
        strategy: Strategy name ("race" or "single")
        **kwargs: Config options if config is None

    Returns:
        ProvisionResult

    Example:
        result = provision_machine(
            "your-api-key",
            gpu_name="RTX 4090",
            max_price=1.0,
        )
    """
    provisioner = MachineProvisionerService(api_key)

    if config is None:
        config = ProvisionConfig(**kwargs)

    return provisioner.provision(config, strategy=strategy)
