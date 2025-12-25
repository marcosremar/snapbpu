"""
Storage Module

Gerenciamento de arquivos em cloud storage com:
- Upload para B2/R2/S3/Wasabi
- URLs temporárias para download
- Expiração automática (24h padrão)
- Integração com Jobs
"""

from .models import StoredFile, StoredDirectory, FileStatus, StorageProviderType
from .repository import StorageRepository
from .service import (
    StorageService,
    StorageConfig,
    UploadResult,
    get_storage_service,
)

__all__ = [
    # Models
    "StoredFile",
    "StoredDirectory",
    "FileStatus",
    "StorageProviderType",
    # Repository
    "StorageRepository",
    # Service
    "StorageService",
    "StorageConfig",
    "UploadResult",
    "get_storage_service",
]
