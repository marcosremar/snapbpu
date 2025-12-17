"""
Configuration management for Dumont Cloud
Loads from environment variables with sensible defaults
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class R2Settings(BaseSettings):
    """Cloudflare R2 Configuration"""
    access_key: str = Field(default="", env="R2_ACCESS_KEY")
    secret_key: str = Field(default="", env="R2_SECRET_KEY")
    endpoint: str = Field(default="", env="R2_ENDPOINT")
    bucket: str = Field(default="musetalk", env="R2_BUCKET")

    @property
    def restic_repo(self) -> str:
        """Constructs restic repository URL"""
        return f"s3:{self.endpoint}/{self.bucket}/restic"

    class Config:
        env_prefix = ""


class ResticSettings(BaseSettings):
    """Restic backup configuration"""
    password: str = Field(default="", env="RESTIC_PASSWORD")
    connections: int = Field(default=32, env="RESTIC_CONNECTIONS")

    class Config:
        env_prefix = ""


class VastSettings(BaseSettings):
    """Vast.ai API configuration"""
    api_url: str = Field(default="https://console.vast.ai/api/v0", env="VAST_API_URL")
    stage_timeout: int = Field(default=30, env="VAST_STAGE_TIMEOUT")
    ssh_ready_timeout: int = Field(default=60, env="VAST_SSH_TIMEOUT")
    default_region: str = Field(default="EU", env="VAST_DEFAULT_REGION")
    min_reliability: float = Field(default=0.95, env="VAST_MIN_RELIABILITY")
    min_cuda: str = Field(default="12.0", env="VAST_MIN_CUDA")

    class Config:
        env_prefix = ""


class AppSettings(BaseSettings):
    """Application configuration"""
    # Server
    host: str = Field(default="0.0.0.0", env="APP_HOST")
    port: int = Field(default=8766, env="APP_PORT")
    debug: bool = Field(default=False, env="DEBUG")

    # Security
    secret_key: str = Field(default="snapgpu-secret-key-2024", env="SECRET_KEY")
    demo_mode: bool = Field(default=False, env="DEMO_MODE")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="CORS_ORIGINS"
    )

    # Session
    session_cookie_domain: Optional[str] = Field(default=None, env="SESSION_COOKIE_DOMAIN")
    session_cookie_secure: bool = Field(default=True, env="SESSION_COOKIE_SECURE")

    # Storage
    config_file: str = Field(default="config.json", env="CONFIG_FILE")

    class Config:
        env_prefix = ""
        case_sensitive = False


class DumontAgentSettings(BaseSettings):
    """DumontAgent configuration (agent running on GPU instances)"""
    server_url: str = Field(default="https://dumontcloud.com", env="DUMONT_SERVER")
    sync_interval: int = Field(default=30, env="DUMONT_SYNC_INTERVAL")
    sync_dirs: str = Field(default="/workspace", env="DUMONT_SYNC_DIRS")
    keep_last: int = Field(default=10, env="DUMONT_KEEP_LAST")

    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Main settings container"""
    app: AppSettings = Field(default_factory=AppSettings)
    r2: R2Settings = Field(default_factory=R2Settings)
    restic: ResticSettings = Field(default_factory=ResticSettings)
    vast: VastSettings = Field(default_factory=VastSettings)
    agent: DumontAgentSettings = Field(default_factory=DumontAgentSettings)

    class Config:
        env_prefix = ""


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience export
settings = get_settings()
