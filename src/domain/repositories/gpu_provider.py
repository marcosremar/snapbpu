"""
Abstract interface for GPU providers (Dependency Inversion Principle)
Allows swapping between different GPU providers (vast.ai, lambda labs, etc)
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models import GpuOffer, Instance


class IGpuProvider(ABC):
    """Abstract interface for GPU instance providers"""

    @abstractmethod
    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        min_gpu_ram: float = 0,
        min_cpu_cores: int = 1,
        min_cpu_ram: float = 1,
        min_disk: float = 50,
        min_inet_down: float = 500,
        max_price: float = 1.0,
        min_cuda: str = "11.0",
        min_reliability: float = 0.0,
        region: Optional[str] = None,
        verified_only: bool = False,
        static_ip: bool = False,
        limit: int = 50,
    ) -> List[GpuOffer]:
        """Search for available GPU offers"""
        pass

    @abstractmethod
    def create_instance(
        self,
        offer_id: int,
        image: str,
        disk_size: float,
        label: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        onstart_cmd: Optional[str] = None,
    ) -> Instance:
        """Create a new GPU instance"""
        pass

    @abstractmethod
    def get_instance(self, instance_id: int) -> Instance:
        """Get instance details by ID"""
        pass

    @abstractmethod
    def list_instances(self) -> List[Instance]:
        """List all user instances"""
        pass

    @abstractmethod
    def destroy_instance(self, instance_id: int) -> bool:
        """Destroy an instance"""
        pass

    @abstractmethod
    def pause_instance(self, instance_id: int) -> bool:
        """Pause an instance"""
        pass

    @abstractmethod
    def resume_instance(self, instance_id: int) -> bool:
        """Resume a paused instance"""
        pass

    @abstractmethod
    def get_instance_metrics(self, instance_id: int) -> Dict[str, Any]:
        """Get real-time metrics for an instance"""
        pass
