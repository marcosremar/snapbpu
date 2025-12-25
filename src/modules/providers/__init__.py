"""
Providers Module - Interface unificada de providers GPU

Este módulo abstrai diferentes provedores GPU:
- Vast.ai
- TensorDock
- GCP
- RunPod

Uso:
    from src.modules.providers import (
        GPUProvider,
        get_provider,
        ProviderFactory,
    )

    # Obter provider específico
    vast = get_provider("vast")
    instance = await vast.create_instance(gpu_type="RTX 4090", max_price=0.50)

    # Factory pattern
    factory = ProviderFactory()
    provider = factory.get("tensordock")
"""

from .base import (
    GPUProvider,
    ProviderType,
    GPUInstance,
    GPUOffer,
)

from .factory import (
    ProviderFactory,
    get_provider,
)

__all__ = [
    "GPUProvider",
    "ProviderType",
    "GPUInstance",
    "GPUOffer",
    "ProviderFactory",
    "get_provider",
]
