"""
Storage Configuration - Centralized provider management
Simple usage: Just set STORAGE_PROVIDER env var and it works!
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import os


class Provider(Enum):
    """Available storage providers"""
    BACKBLAZE_B2 = "b2"
    CLOUDFLARE_R2 = "r2"
    AWS_S3 = "s3"
    WASABI = "wasabi"


@dataclass
class ProviderConfig:
    """Storage provider configuration"""
    name: str
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str = "auto"
    
    @property
    def display_name(self) -> str:
        """Human-readable provider name"""
        names = {
            "b2": "Backblaze B2",
            "r2": "Cloudflare R2",
            "s3": "AWS S3",
            "wasabi": "Wasabi"
        }
        return names.get(self.name, self.name.upper())


class StorageConfig:
    """
    Centralized storage configuration
    
    Usage:
        # Option 1: Use environment variables (recommended)
        export STORAGE_PROVIDER=b2
        config = StorageConfig.from_env()
        
        # Option 2: Use directly
        config = StorageConfig.get_provider('b2')
        
        # Option 3: Override default
        StorageConfig.set_default_provider('b2')
        config = StorageConfig.get_default()
    """
    
    # Default provider (can be changed)
    _default_provider = Provider.BACKBLAZE_B2
    
    # Provider configurations
    _configs = {
        Provider.BACKBLAZE_B2: lambda: ProviderConfig(
            name="b2",
            endpoint=f"https://s3.{os.getenv('B2_REGION', 'us-west-004')}.backblazeb2.com",
            bucket=os.getenv("B2_BUCKET", "dumoncloud-snapshot"),
            access_key=os.getenv("B2_KEY_ID", "a1ef6268a3f3"),  # Master Application Key
            secret_key=os.getenv("B2_APPLICATION_KEY", "00309def7dbba65c97bb234af3ce2e89ea62fdf7dd"),
            region=os.getenv("B2_REGION", "us-west-004")
        ),
        
        Provider.CLOUDFLARE_R2: lambda: ProviderConfig(
            name="r2",
            endpoint=f"https://{os.getenv('R2_ACCOUNT_ID', '142ed673a5cc1a9e91519c099af3d791')}.r2.cloudflarestorage.com",
            bucket=os.getenv("R2_BUCKET", "musetalk"),
            access_key=os.getenv("R2_ACCESS_KEY", "f0a6f424064e46c903c76a447f5e73d2"),
            secret_key=os.getenv("R2_SECRET_KEY", "1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5"),
            region="auto"
        ),
        
        Provider.AWS_S3: lambda: ProviderConfig(
            name="s3",
            endpoint=f"https://s3.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com",
            bucket=os.getenv("S3_BUCKET", "dumont-snapshots"),
            access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            region=os.getenv("AWS_REGION", "us-east-1")
        ),
        
        Provider.WASABI: lambda: ProviderConfig(
            name="wasabi",
            endpoint=f"https://s3.{os.getenv('WASABI_REGION', 'us-east-1')}.wasabisys.com",
            bucket=os.getenv("WASABI_BUCKET", "dumont-snapshots"),
            access_key=os.getenv("WASABI_ACCESS_KEY", ""),
            secret_key=os.getenv("WASABI_SECRET_KEY", ""),
            region=os.getenv("WASABI_REGION", "us-east-1")
        ),
    }
    
    @classmethod
    def set_default_provider(cls, provider: str):
        """Set default storage provider"""
        if provider == "b2":
            cls._default_provider = Provider.BACKBLAZE_B2
        elif provider == "r2":
            cls._default_provider = Provider.CLOUDFLARE_R2
        elif provider == "s3":
            cls._default_provider = Provider.AWS_S3
        elif provider == "wasabi":
            cls._default_provider = Provider.WASABI
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @classmethod
    def get_provider(cls, provider_name: str) -> ProviderConfig:
        """Get configuration for specific provider"""
        provider_map = {
            "b2": Provider.BACKBLAZE_B2,
            "r2": Provider.CLOUDFLARE_R2,
            "s3": Provider.AWS_S3,
            "wasabi": Provider.WASABI,
        }
        
        provider = provider_map.get(provider_name.lower())
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        config_func = cls._configs[provider]
        return config_func()
    
    @classmethod
    def get_default(cls) -> ProviderConfig:
        """Get default provider configuration"""
        config_func = cls._configs[cls._default_provider]
        return config_func()
    
    @classmethod
    def from_env(cls) -> ProviderConfig:
        """
        Get configuration from environment variable STORAGE_PROVIDER
        Falls back to default if not set
        """
        provider_name = os.getenv("STORAGE_PROVIDER", cls._default_provider.value)
        return cls.get_provider(provider_name)
    
    @classmethod
    def list_providers(cls) -> list:
        """List all available providers"""
        return [
            {
                "name": p.value,
                "display_name": cls.get_provider(p.value).display_name,
                "recommended": p == cls._default_provider
            }
            for p in Provider
        ]


# Convenience function
def get_storage_config() -> ProviderConfig:
    """
    Get storage configuration (reads from env automatically)
    
    This is the simplest way to get storage config:
    >>> config = get_storage_config()
    >>> print(f"Using {config.display_name}")
    """
    return StorageConfig.from_env()


# Example usage in comments:
"""
# Example 1: Use default (Backblaze B2)
from src.storage import get_storage_config
config = get_storage_config()

# Example 2: Use Cloudflare R2
export STORAGE_PROVIDER=r2
config = get_storage_config()

# Example 3: Change default in code
from src.storage.storage_config import StorageConfig
StorageConfig.set_default_provider('b2')
config = StorageConfig.get_default()

# Example 4: List all available providers
providers = StorageConfig.list_providers()
for p in providers:
    print(f"- {p['display_name']} ({'recommended' if p['recommended'] else 'available'})")
"""
