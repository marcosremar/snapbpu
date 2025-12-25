"""
Serverless Module Configuration

Configurações centralizadas para o módulo serverless.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ServerlessMode(str, Enum):
    """Modos de serverless disponíveis"""
    FAST = "fast"           # CPU Standby + Checkpoint - recovery <1s
    ECONOMIC = "economic"   # Pause/Resume VAST.ai - recovery ~7s
    SPOT = "spot"           # Spot instances - recovery ~30s
    DISABLED = "disabled"   # Sem auto-pause


@dataclass
class ServerlessSettings:
    """Configurações globais do módulo serverless"""

    # Defaults para novas instâncias
    default_mode: ServerlessMode = ServerlessMode.ECONOMIC
    default_idle_timeout_seconds: int = 30
    default_gpu_threshold: float = 5.0
    default_min_runtime_seconds: int = 60

    # Checkpoint settings
    checkpoint_enabled: bool = True
    checkpoint_auto_create: bool = True  # Criar checkpoint antes de pausar
    checkpoint_dir: str = "/workspace/.gpu-checkpoints"
    checkpoint_max_count: int = 5  # Máximo de checkpoints por instância

    # Fallback settings
    fallback_enabled: bool = True
    fallback_parallel: bool = True  # Lançar backup em paralelo ao resume
    fallback_max_price: float = 1.0
    fallback_timeout_seconds: int = 60

    # SSH settings
    ssh_verify_timeout: int = 30
    ssh_connect_timeout: int = 10

    # Monitor settings
    monitor_check_interval: int = 5  # Segundos entre checks
    monitor_enabled: bool = True

    # Storage settings
    config_file: str = "~/.dumont_serverless.json"
    r2_bucket: str = "dumont-checkpoints"

    # Custo estimado por hora (para cálculo de savings)
    gpu_hourly_rate: float = 0.30
    cpu_standby_hourly_rate: float = 0.01
    storage_idle_hourly_rate: float = 0.005


@dataclass
class InstanceServerlessConfig:
    """Configuração serverless para uma instância específica"""
    instance_id: int
    mode: ServerlessMode = ServerlessMode.DISABLED
    idle_timeout_seconds: int = 30
    gpu_threshold: float = 5.0
    keep_warm: bool = False
    min_runtime_seconds: int = 60

    # Estado runtime
    is_paused: bool = False
    paused_at: Optional[str] = None
    last_activity: Optional[str] = None
    idle_since: Optional[str] = None
    total_idle_time: float = 0
    total_savings: float = 0

    # Checkpoint
    checkpoint_enabled: bool = True
    last_checkpoint_id: Optional[str] = None

    # Fallback
    enable_fallback: bool = True
    fallback_max_price: float = 1.0
    fallback_gpu_name: Optional[str] = None
    fallback_parallel: bool = True
    resume_timeout: int = 60
    ssh_verify_timeout: int = 30
    last_snapshot_id: Optional[str] = None


# Singleton settings
_settings: Optional[ServerlessSettings] = None


def get_settings() -> ServerlessSettings:
    """Retorna configurações singleton do módulo"""
    global _settings
    if _settings is None:
        _settings = ServerlessSettings()
    return _settings


def configure(**kwargs) -> ServerlessSettings:
    """Configura o módulo com novos valores"""
    global _settings
    _settings = ServerlessSettings(**kwargs)
    return _settings
