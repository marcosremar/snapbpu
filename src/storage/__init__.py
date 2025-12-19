"""
Storage Module - Multi-provider cloud storage abstraction

Quick Start:
    from src.storage import get_storage_config
    
    # Use default provider (Backblaze B2)
    config = get_storage_config()
    
    # Or set via environment:
    # export STORAGE_PROVIDER=b2  (or r2, s3, wasabi)
"""
from .storage_provider import (
    StorageProvider,
    StorageConfig as StorageProviderConfig,
    S5cmdProvider,
    create_storage_provider,
    get_cloudflare_r2_config,
    get_backblaze_b2_config,
    get_wasabi_config,
    get_aws_s3_config,
)

from .storage_config import (
    StorageConfig,
    ProviderConfig,
    Provider,
    get_storage_config,
)

__all__ = [
    # Provider classes
    'StorageProvider',
    'StorageProviderConfig',
    'S5cmdProvider',
    'create_storage_provider',
    
    # Config helpers (old style)
    'get_cloudflare_r2_config',
    'get_backblaze_b2_config',
    'get_wasabi_config',
    'get_aws_s3_config',
    
    # Centralized config (new style - recommended)
    'StorageConfig',
    'ProviderConfig',
    'Provider',
    'get_storage_config',  # <- Use this!
]
