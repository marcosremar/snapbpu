"""
Instance Service - Domain Service (Business Logic)
Orchestrates GPU instance operations using IGpuProvider
"""
import logging
from typing import List, Optional, Dict, Any

from ..repositories import IGpuProvider
from ..models import Instance, GpuOffer
from ...core.exceptions import NotFoundException, VastAPIException

logger = logging.getLogger(__name__)


class InstanceService:
    """
    Domain service for GPU instance management.
    Orchestrates operations between providers (Single Responsibility Principle).
    """

    def __init__(self, gpu_provider: IGpuProvider):
        """
        Initialize instance service

        Args:
            gpu_provider: GPU provider implementation (vast.ai, lambda labs, etc)
        """
        self.gpu_provider = gpu_provider

    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        max_price: float = 1.0,
        region: Optional[str] = None,
        min_disk: float = 50,
        **kwargs
    ) -> List[GpuOffer]:
        """
        Search for available GPU offers

        Args:
            gpu_name: GPU model (e.g., "RTX 4090")
            max_price: Maximum price per hour
            region: Region filter (e.g., "EU", "US")
            min_disk: Minimum disk space in GB
            **kwargs: Additional filters

        Returns:
            List of GPU offers
        """
        return self.gpu_provider.search_offers(
            gpu_name=gpu_name,
            max_price=max_price,
            region=region,
            min_disk=min_disk,
            **kwargs
        )

    def create_instance(
        self,
        offer_id: int,
        image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        disk_size: float = 100,
        label: Optional[str] = None,
        ports: Optional[List[int]] = None,
    ) -> Instance:
        """
        Create a new GPU instance

        Args:
            offer_id: ID of the GPU offer
            image: Docker image to use
            disk_size: Disk size in GB
            label: Optional label for the instance
            ports: List of ports to expose

        Returns:
            Created instance
        """
        logger.info(f"Creating instance from offer {offer_id}")

        # Prepare env vars for ports
        env_vars = {}
        if ports:
            for port in ports:
                env_vars[f"PORT_{port}"] = str(port)

        instance = self.gpu_provider.create_instance(
            offer_id=offer_id,
            image=image,
            disk_size=disk_size,
            label=label,
            env_vars=env_vars,
        )

        logger.info(f"Instance {instance.id} created successfully")
        return instance

    def get_instance(self, instance_id: int) -> Instance:
        """
        Get instance by ID

        Args:
            instance_id: Instance ID

        Returns:
            Instance details

        Raises:
            NotFoundException: If instance not found
        """
        try:
            return self.gpu_provider.get_instance(instance_id)
        except Exception as e:
            logger.error(f"Failed to get instance {instance_id}: {e}")
            raise NotFoundException(f"Instance {instance_id} not found")

    def list_instances(self) -> List[Instance]:
        """
        List all user instances

        Returns:
            List of instances
        """
        return self.gpu_provider.list_instances()

    def destroy_instance(self, instance_id: int) -> bool:
        """
        Destroy an instance

        Args:
            instance_id: Instance ID

        Returns:
            True if successful
        """
        logger.info(f"Destroying instance {instance_id}")
        success = self.gpu_provider.destroy_instance(instance_id)

        if success:
            logger.info(f"Instance {instance_id} destroyed")
        else:
            logger.error(f"Failed to destroy instance {instance_id}")

        return success

    def pause_instance(self, instance_id: int) -> bool:
        """
        Pause an instance

        Args:
            instance_id: Instance ID

        Returns:
            True if successful
        """
        logger.info(f"Pausing instance {instance_id}")
        return self.gpu_provider.pause_instance(instance_id)

    def resume_instance(self, instance_id: int) -> bool:
        """
        Resume a paused instance

        Args:
            instance_id: Instance ID

        Returns:
            True if successful
        """
        logger.info(f"Resuming instance {instance_id}")
        return self.gpu_provider.resume_instance(instance_id)

    def get_instance_metrics(self, instance_id: int) -> Dict[str, Any]:
        """
        Get real-time metrics for an instance

        Args:
            instance_id: Instance ID

        Returns:
            Dictionary of metrics
        """
        return self.gpu_provider.get_instance_metrics(instance_id)

    def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance

        Returns:
            Dictionary with credit, balance, etc
        """
        return self.gpu_provider.get_balance()
