"""
Configuration management for Dumont Cloud
Loads from environment variables with sensible defaults
"""
import os
from typing import Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class R2Settings(BaseSettings):
    """Cloudflare R2 Configuration"""
    model_config = SettingsConfigDict(env_prefix="R2_", extra="ignore")

    access_key: str = Field(default="", validation_alias=AliasChoices("access_key", "R2_ACCESS_KEY"))
    secret_key: str = Field(default="", validation_alias=AliasChoices("secret_key", "R2_SECRET_KEY"))
    endpoint: str = Field(default="", validation_alias=AliasChoices("endpoint", "R2_ENDPOINT"))
    bucket: str = Field(default="musetalk", validation_alias=AliasChoices("bucket", "R2_BUCKET"))

    @property
    def restic_repo(self) -> str:
        """Constructs restic repository URL"""
        return f"s3:{self.endpoint}/{self.bucket}/restic"


class ResticSettings(BaseSettings):
    """Restic backup configuration"""
    model_config = SettingsConfigDict(env_prefix="RESTIC_", extra="ignore")

    password: str = Field(default="", validation_alias=AliasChoices("password", "RESTIC_PASSWORD"))
    connections: int = Field(default=32, validation_alias=AliasChoices("connections", "RESTIC_CONNECTIONS"))


class VastSettings(BaseSettings):
    """Vast.ai API configuration"""
    model_config = SettingsConfigDict(env_prefix="VAST_", extra="ignore")

    api_key: str = Field(default="", validation_alias=AliasChoices("api_key", "VAST_API_KEY"))
    api_url: str = Field(default="https://console.vast.ai/api/v0", validation_alias=AliasChoices("api_url", "VAST_API_URL"))
    stage_timeout: int = Field(default=30, validation_alias=AliasChoices("stage_timeout", "VAST_STAGE_TIMEOUT"))
    ssh_ready_timeout: int = Field(default=60, validation_alias=AliasChoices("ssh_ready_timeout", "VAST_SSH_TIMEOUT"))
    default_region: str = Field(default="EU", validation_alias=AliasChoices("default_region", "VAST_DEFAULT_REGION"))
    min_reliability: float = Field(default=0.95, validation_alias=AliasChoices("min_reliability", "VAST_MIN_RELIABILITY"))
    min_cuda: str = Field(default="12.0", validation_alias=AliasChoices("min_cuda", "VAST_MIN_CUDA"))


class AppSettings(BaseSettings):
    """Application configuration"""
    model_config = SettingsConfigDict(extra="ignore")

    # Server
    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("host", "APP_HOST"))
    port: int = Field(default=8766, validation_alias=AliasChoices("port", "APP_PORT"))
    debug: bool = Field(default=False, validation_alias=AliasChoices("debug", "DEBUG"))

    # Security
    secret_key: str = Field(default="dumont-cloud-secret-key-2024", validation_alias=AliasChoices("secret_key", "SECRET_KEY"))
    demo_mode: bool = Field(default=False, validation_alias=AliasChoices("demo_mode", "DEMO_MODE"))

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        validation_alias=AliasChoices("cors_origins", "CORS_ORIGINS")
    )

    # Session
    session_cookie_domain: Optional[str] = Field(default=None, validation_alias=AliasChoices("session_cookie_domain", "SESSION_COOKIE_DOMAIN"))
    session_cookie_secure: bool = Field(default=True, validation_alias=AliasChoices("session_cookie_secure", "SESSION_COOKIE_SECURE"))

    # Storage
    config_file: str = Field(default="config.json", validation_alias=AliasChoices("config_file", "CONFIG_FILE"))


class DumontAgentSettings(BaseSettings):
    """DumontAgent configuration (agent running on GPU instances)"""
    model_config = SettingsConfigDict(env_prefix="DUMONT_", extra="ignore")

    server_url: str = Field(default="https://dumontcloud.com", validation_alias=AliasChoices("server_url", "DUMONT_SERVER"))
    sync_interval: int = Field(default=30, validation_alias=AliasChoices("sync_interval", "DUMONT_SYNC_INTERVAL"))
    sync_dirs: str = Field(default="/workspace", validation_alias=AliasChoices("sync_dirs", "DUMONT_SYNC_DIRS"))
    keep_last: int = Field(default=10, validation_alias=AliasChoices("keep_last", "DUMONT_KEEP_LAST"))


class LLMSettings(BaseSettings):
    """LLM configuration for AI Advisor"""
    model_config = SettingsConfigDict(extra="ignore")

    openai_api_key: str = Field(default="", validation_alias=AliasChoices("openai_api_key", "OPENAI_API_KEY"))
    anthropic_api_key: str = Field(default="", validation_alias=AliasChoices("anthropic_api_key", "ANTHROPIC_API_KEY"))
    default_provider: str = Field(default="openai", validation_alias=AliasChoices("default_provider", "LLM_DEFAULT_PROVIDER"))
    model_name: str = Field(default="gpt-4o", validation_alias=AliasChoices("model_name", "LLM_MODEL_NAME"))


class Settings(BaseSettings):
    """Main settings container"""
    model_config = SettingsConfigDict(extra="ignore")

    app: AppSettings = Field(default_factory=AppSettings)
    r2: R2Settings = Field(default_factory=R2Settings)
    restic: ResticSettings = Field(default_factory=ResticSettings)
    vast: VastSettings = Field(default_factory=VastSettings)
    agent: DumontAgentSettings = Field(default_factory=DumontAgentSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)


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
