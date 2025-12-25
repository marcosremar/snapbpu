"""
Provider Factory - Factory pattern para providers
"""

import os
import logging
from typing import Optional, Dict, Type

from .base import GPUProvider, ProviderType

logger = logging.getLogger(__name__)


class VastProvider(GPUProvider):
    """Provider Vast.ai"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.VAST

    @property
    def supports_pause(self) -> bool:
        return True

    @property
    def supports_spot(self) -> bool:
        return True

    async def list_offers(self, gpu_type=None, min_gpu_ram=0, max_price=10.0, region=None):
        from .base import GPUOffer
        # Em produção, usaria API real
        return [
            GPUOffer(
                offer_id="vast-12345",
                provider=ProviderType.VAST,
                gpu_type="RTX 4090",
                gpu_ram_mb=24576,
                price_per_hour=0.45,
            )
        ]

    async def create_instance(self, offer_id, image="pytorch/pytorch:latest", disk_gb=50, **kwargs):
        from .base import GPUInstance
        return GPUInstance(
            instance_id=f"vast-{offer_id}",
            provider=ProviderType.VAST,
            status="running",
            gpu_type="RTX 4090",
        )

    async def destroy_instance(self, instance_id):
        return True

    async def get_instance(self, instance_id):
        return None

    async def pause_instance(self, instance_id):
        logger.info(f"[VAST] Pausing {instance_id}")
        return True

    async def resume_instance(self, instance_id):
        logger.info(f"[VAST] Resuming {instance_id}")
        return True


class TensorDockProvider(GPUProvider):
    """Provider TensorDock"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.TENSORDOCK

    async def list_offers(self, gpu_type=None, min_gpu_ram=0, max_price=10.0, region=None):
        from .base import GPUOffer
        return [
            GPUOffer(
                offer_id="td-67890",
                provider=ProviderType.TENSORDOCK,
                gpu_type="RTX 3090",
                gpu_ram_mb=24576,
                price_per_hour=0.35,
            )
        ]

    async def create_instance(self, offer_id, image="pytorch/pytorch:latest", disk_gb=50, **kwargs):
        from .base import GPUInstance
        return GPUInstance(
            instance_id=f"td-{offer_id}",
            provider=ProviderType.TENSORDOCK,
            status="running",
            gpu_type="RTX 3090",
        )

    async def destroy_instance(self, instance_id):
        return True

    async def get_instance(self, instance_id):
        return None


class GCPProvider(GPUProvider):
    """Provider Google Cloud"""

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GCP

    @property
    def supports_spot(self) -> bool:
        return True

    async def list_offers(self, gpu_type=None, min_gpu_ram=0, max_price=10.0, region=None):
        from .base import GPUOffer
        return [
            GPUOffer(
                offer_id="gcp-a100",
                provider=ProviderType.GCP,
                gpu_type="A100",
                gpu_ram_mb=40960,
                price_per_hour=2.50,
            )
        ]

    async def create_instance(self, offer_id, image="pytorch/pytorch:latest", disk_gb=50, **kwargs):
        from .base import GPUInstance
        return GPUInstance(
            instance_id=f"gcp-{offer_id}",
            provider=ProviderType.GCP,
            status="running",
            gpu_type="A100",
        )

    async def destroy_instance(self, instance_id):
        return True

    async def get_instance(self, instance_id):
        return None


class ProviderFactory:
    """
    Factory para criar providers GPU.

    Uso:
        factory = ProviderFactory()
        vast = factory.get("vast")
        offers = await vast.list_offers()
    """

    _providers: Dict[ProviderType, Type[GPUProvider]] = {
        ProviderType.VAST: VastProvider,
        ProviderType.TENSORDOCK: TensorDockProvider,
        ProviderType.GCP: GCPProvider,
    }

    _instances: Dict[ProviderType, GPUProvider] = {}

    @classmethod
    def register(cls, provider_type: ProviderType, provider_class: Type[GPUProvider]):
        """Registra novo provider"""
        cls._providers[provider_type] = provider_class

    @classmethod
    def get(cls, provider: str, api_key: Optional[str] = None) -> GPUProvider:
        """
        Obtém instância de provider.

        Args:
            provider: Nome do provider (vast, tensordock, gcp)
            api_key: API key (usa env var se não fornecida)

        Returns:
            GPUProvider instance
        """
        provider_type = ProviderType(provider.lower())

        if provider_type not in cls._instances:
            provider_class = cls._providers.get(provider_type)
            if not provider_class:
                raise ValueError(f"Unknown provider: {provider}")

            # Obter API key do ambiente se não fornecida
            if not api_key:
                env_key = f"{provider.upper()}_API_KEY"
                api_key = os.getenv(env_key, "")

            cls._instances[provider_type] = provider_class(api_key=api_key)

        return cls._instances[provider_type]

    @classmethod
    def list_available(cls) -> list:
        """Lista providers disponíveis"""
        return [p.value for p in cls._providers.keys()]


def get_provider(provider: str, api_key: Optional[str] = None) -> GPUProvider:
    """Shortcut para ProviderFactory.get()"""
    return ProviderFactory.get(provider, api_key)
