"""
Base Provider - Interface abstrata para provedores GPU
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ProviderType(str, Enum):
    """Tipos de provider"""
    VAST = "vast"
    TENSORDOCK = "tensordock"
    GCP = "gcp"
    RUNPOD = "runpod"
    LOCAL = "local"


@dataclass
class GPUOffer:
    """Oferta de GPU disponível"""
    offer_id: str
    provider: ProviderType

    # GPU info
    gpu_type: str
    gpu_count: int = 1
    gpu_ram_mb: int = 0

    # Pricing
    price_per_hour: float = 0.0
    spot_price: Optional[float] = None

    # Machine info
    cpu_cores: int = 0
    ram_mb: int = 0
    disk_gb: int = 0

    # Location
    region: str = ""
    datacenter: str = ""

    # Performance
    dlperf: float = 0.0
    total_flops: float = 0.0

    # Reliability
    reliability_score: float = 0.0
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "provider": self.provider.value,
            "gpu_type": self.gpu_type,
            "gpu_count": self.gpu_count,
            "gpu_ram_mb": self.gpu_ram_mb,
            "price_per_hour": self.price_per_hour,
            "region": self.region,
            "reliability_score": self.reliability_score,
        }


@dataclass
class GPUInstance:
    """Instância GPU provisionada"""
    instance_id: str
    provider: ProviderType
    status: str = "pending"

    # Connection
    ssh_host: str = ""
    ssh_port: int = 22
    ssh_user: str = "root"

    # GPU info
    gpu_type: str = ""
    gpu_count: int = 1
    gpu_ram_mb: int = 0

    # Pricing
    price_per_hour: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "provider": self.provider.value,
            "status": self.status,
            "ssh_host": self.ssh_host,
            "ssh_port": self.ssh_port,
            "gpu_type": self.gpu_type,
            "price_per_hour": self.price_per_hour,
            "created_at": self.created_at.isoformat(),
        }


class GPUProvider(ABC):
    """
    Interface abstrata para provedores GPU.

    Todos os providers devem implementar:
    - list_offers(): Lista GPUs disponíveis
    - create_instance(): Provisiona nova instância
    - destroy_instance(): Destroi instância
    - get_instance(): Obtém status de instância
    - pause_instance(): Pausa instância (se suportado)
    - resume_instance(): Resume instância (se suportado)
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Tipo do provider"""
        pass

    @property
    def supports_pause(self) -> bool:
        """Se provider suporta pause/resume"""
        return False

    @property
    def supports_spot(self) -> bool:
        """Se provider suporta instâncias spot"""
        return False

    @abstractmethod
    async def list_offers(
        self,
        gpu_type: Optional[str] = None,
        min_gpu_ram: int = 0,
        max_price: float = 10.0,
        region: Optional[str] = None,
    ) -> List[GPUOffer]:
        """Lista ofertas de GPU disponíveis"""
        pass

    @abstractmethod
    async def create_instance(
        self,
        offer_id: str,
        image: str = "pytorch/pytorch:latest",
        disk_gb: int = 50,
        **kwargs
    ) -> GPUInstance:
        """Provisiona nova instância"""
        pass

    @abstractmethod
    async def destroy_instance(self, instance_id: str) -> bool:
        """Destroi instância"""
        pass

    @abstractmethod
    async def get_instance(self, instance_id: str) -> Optional[GPUInstance]:
        """Obtém status de instância"""
        pass

    async def pause_instance(self, instance_id: str) -> bool:
        """Pausa instância (se suportado)"""
        raise NotImplementedError(f"{self.provider_type} does not support pause")

    async def resume_instance(self, instance_id: str) -> bool:
        """Resume instância (se suportado)"""
        raise NotImplementedError(f"{self.provider_type} does not support resume")

    async def health_check(self) -> bool:
        """Verifica se API está acessível"""
        try:
            await self.list_offers(max_price=0.01)  # Query mínima
            return True
        except Exception:
            return False
