"""
Models Module - Auto-deploy de modelos com detecção automática

Este módulo permite fazer deploy de qualquer modelo do HuggingFace
com detecção automática de tipo e runtime.

Uso:
    from src.modules.models import ServerlessModelService, DeploymentConfig

    # Deploy simples
    service = ServerlessModelService()
    result = await service.deploy("meta-llama/Llama-3.1-8B-Instruct")

    # Deploy com config
    result = await service.deploy(
        "openai/whisper-large-v3",
        config=DeploymentConfig(
            idle_timeout_seconds=60,
            gpu_type="RTX 4090",
        )
    )

    # Apenas detectar tipo do modelo
    from src.modules.models import get_registry
    registry = get_registry()
    info = registry.get_model_info("stabilityai/stable-diffusion-xl-base-1.0")
    print(info.runtime)  # diffusers
"""

from .registry import (
    ModelRegistry,
    ModelInfo,
    ModelTask,
    ModelRuntime,
    get_registry,
)

from .downloader import (
    ModelDownloader,
    DownloadResult,
    DownloadStatus,
    get_downloader,
)

from .service import (
    ServerlessModelService,
    DeploymentConfig,
    DeploymentResult,
    DeploymentStatus,
    get_model_service,
)

__all__ = [
    # Registry
    "ModelRegistry",
    "ModelInfo",
    "ModelTask",
    "ModelRuntime",
    "get_registry",
    # Downloader
    "ModelDownloader",
    "DownloadResult",
    "DownloadStatus",
    "get_downloader",
    # Service
    "ServerlessModelService",
    "DeploymentConfig",
    "DeploymentResult",
    "DeploymentStatus",
    "get_model_service",
]
