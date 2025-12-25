"""
Serverless Module - Database Models

Schema: serverless (PostgreSQL schema para isolamento)

Tabelas:
- serverless.user_settings: Configuração serverless por usuário
- serverless.instances: Instâncias com serverless ativo
- serverless.snapshots: Snapshots para recovery
- serverless.events: Eventos de pause/resume/destroy
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Enum, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from src.config.database import Base


# =============================================================================
# ENUMS
# =============================================================================

class ServerlessModeEnum(enum.Enum):
    """Modos de serverless disponíveis"""
    DISABLED = "disabled"
    FAST = "fast"           # Checkpoint CRIU, <1s recovery
    ECONOMIC = "economic"   # Pause/resume VAST.ai, ~7s
    SPOT = "spot"           # Instâncias spot, ~30s


class InstanceStateEnum(enum.Enum):
    """Estados possíveis da instância"""
    RUNNING = "running"
    PAUSED = "paused"
    WAKING = "waking"
    DESTROYED = "destroyed"
    FAILED = "failed"


class EventTypeEnum(enum.Enum):
    """Tipos de eventos serverless"""
    SCALE_DOWN = "scale_down"      # Pausou por idle
    SCALE_UP = "scale_up"          # Acordou por requisição
    AUTO_DESTROY = "auto_destroy"  # Destruído por tempo pausado
    RESUME_FAILED = "resume_failed"  # Falha ao acordar
    FALLBACK_SNAPSHOT = "fallback_snapshot"  # Usou snapshot em nova máquina
    FALLBACK_DISK = "fallback_disk"  # Migrou disco para nova máquina


# =============================================================================
# USER SETTINGS - Configuração por usuário
# =============================================================================

class ServerlessUserSettings(Base):
    """
    Configuração serverless por usuário.

    Cada usuário pode customizar:
    - Modo padrão (fast, economic, spot)
    - Timeout de scale down (segundos sem requisição)
    - Tempo máximo pausado antes de destruir
    - Preferências de fallback
    """
    __tablename__ = "serverless_user_settings"
    __table_args__ = {"schema": "serverless"}

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)

    # Modo padrão
    default_mode = Column(
        Enum(ServerlessModeEnum),
        default=ServerlessModeEnum.ECONOMIC,
        nullable=False
    )

    # Scale down config
    scale_down_timeout_seconds = Column(Integer, default=30)  # 30s padrão
    gpu_idle_threshold = Column(Float, default=5.0)  # GPU < 5% = idle

    # Auto-destroy config (quando pausado muito tempo)
    auto_destroy_enabled = Column(Boolean, default=True)
    destroy_after_hours_paused = Column(Integer, default=24)  # 1 dia padrão

    # Custo máximo de storage enquanto pausado ($/hr)
    max_paused_cost_per_hour = Column(Float, default=0.05)

    # Fallback config
    fallback_enabled = Column(Boolean, default=True)
    fallback_use_snapshot = Column(Boolean, default=True)
    fallback_use_disk_migration = Column(Boolean, default=True)
    fallback_max_price = Column(Float, default=1.0)  # Max $/hr para fallback

    # Notificações
    notify_on_scale_down = Column(Boolean, default=False)
    notify_on_destroy = Column(Boolean, default=True)
    notify_on_fallback = Column(Boolean, default=True)
    webhook_url = Column(String(500), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    instances = relationship("ServerlessInstance", back_populates="user_settings")

    def __repr__(self):
        return f"<ServerlessUserSettings user={self.user_id} mode={self.default_mode.value}>"


# =============================================================================
# INSTANCES - Instâncias com serverless ativo
# =============================================================================

class ServerlessInstance(Base):
    """
    Instância com serverless habilitado.

    Rastreia:
    - Estado atual (running, paused, etc.)
    - Tempo idle/pausado
    - Configuração específica da instância
    - Métricas de economia
    """
    __tablename__ = "serverless_instances"
    __table_args__ = (
        Index("ix_serverless_instances_user_state", "user_id", "state"),
        Index("ix_serverless_instances_vast_id", "vast_instance_id"),
        {"schema": "serverless"}
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    vast_instance_id = Column(Integer, unique=True, nullable=False)

    # Estado atual
    state = Column(
        Enum(InstanceStateEnum),
        default=InstanceStateEnum.RUNNING,
        nullable=False
    )

    # Configuração (pode sobrescrever user settings)
    mode = Column(Enum(ServerlessModeEnum), nullable=False)
    scale_down_timeout_seconds = Column(Integer, nullable=False)
    gpu_idle_threshold = Column(Float, default=5.0)
    destroy_after_hours_paused = Column(Integer, nullable=True)  # NULL = usar config do user

    # Info da máquina
    gpu_name = Column(String(100))
    gpu_count = Column(Integer, default=1)
    hourly_cost = Column(Float)  # $/hr quando rodando
    paused_cost = Column(Float, default=0.0)  # $/hr quando pausado (storage)

    # SSH info
    ssh_host = Column(String(200))
    ssh_port = Column(Integer)

    # Timestamps de estado
    created_at = Column(DateTime, default=datetime.utcnow)
    last_request_at = Column(DateTime, nullable=True)  # Última requisição recebida
    idle_since = Column(DateTime, nullable=True)  # Quando ficou idle
    paused_at = Column(DateTime, nullable=True)  # Quando foi pausado

    # Snapshot/Checkpoint
    last_snapshot_id = Column(String(200), nullable=True)
    last_checkpoint_id = Column(String(200), nullable=True)
    disk_id = Column(String(200), nullable=True)  # ID do disco para migração

    # Métricas acumuladas
    total_runtime_seconds = Column(Float, default=0)
    total_paused_seconds = Column(Float, default=0)
    total_savings_usd = Column(Float, default=0)
    scale_down_count = Column(Integer, default=0)
    scale_up_count = Column(Integer, default=0)
    fallback_count = Column(Integer, default=0)

    # Relacionamentos
    user_settings_id = Column(Integer, ForeignKey("serverless.serverless_user_settings.id"))
    user_settings = relationship("ServerlessUserSettings", back_populates="instances")
    snapshots = relationship("ServerlessSnapshot", back_populates="instance")
    events = relationship("ServerlessEvent", back_populates="instance")

    def __repr__(self):
        return f"<ServerlessInstance vast={self.vast_instance_id} state={self.state.value}>"

    @property
    def hours_paused(self) -> float:
        """Retorna horas que está pausado"""
        if not self.paused_at:
            return 0
        delta = datetime.utcnow() - self.paused_at
        return delta.total_seconds() / 3600

    @property
    def should_destroy(self) -> bool:
        """Verifica se deve ser destruído por tempo pausado"""
        if self.state != InstanceStateEnum.PAUSED:
            return False
        if not self.destroy_after_hours_paused:
            return False
        return self.hours_paused >= self.destroy_after_hours_paused


# =============================================================================
# SNAPSHOTS - Para recovery/fallback
# =============================================================================

class ServerlessSnapshot(Base):
    """
    Snapshots de instância para recovery.

    Quando resume falha, pode restaurar em nova máquina.
    """
    __tablename__ = "serverless_snapshots"
    __table_args__ = (
        Index("ix_serverless_snapshots_instance", "instance_id"),
        {"schema": "serverless"}
    )

    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, ForeignKey("serverless.serverless_instances.id"), nullable=False)

    # IDs externos
    vast_snapshot_id = Column(String(200), nullable=True)  # ID no VAST.ai
    r2_snapshot_id = Column(String(200), nullable=True)    # ID no Cloudflare R2
    checkpoint_id = Column(String(200), nullable=True)     # ID do checkpoint CRIU

    # Metadata
    snapshot_type = Column(String(50))  # "full", "checkpoint", "disk"
    size_gb = Column(Float)
    gpu_state_included = Column(Boolean, default=False)  # Se inclui estado GPU

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Para limpeza automática

    # Custo de storage
    storage_cost_per_hour = Column(Float, default=0.0)

    # Status
    is_valid = Column(Boolean, default=True)
    last_verified_at = Column(DateTime, nullable=True)

    # Relacionamentos
    instance = relationship("ServerlessInstance", back_populates="snapshots")

    def __repr__(self):
        return f"<ServerlessSnapshot id={self.id} type={self.snapshot_type}>"


# =============================================================================
# EVENTS - Log de eventos para auditoria
# =============================================================================

class ServerlessEvent(Base):
    """
    Log de eventos serverless.

    Registra todos os scale up/down, destroys, fallbacks.
    """
    __tablename__ = "serverless_events"
    __table_args__ = (
        Index("ix_serverless_events_instance_time", "instance_id", "created_at"),
        Index("ix_serverless_events_user_time", "user_id", "created_at"),
        {"schema": "serverless"}
    )

    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, ForeignKey("serverless.serverless_instances.id"), nullable=False)
    user_id = Column(String(100), nullable=False, index=True)

    # Tipo de evento
    event_type = Column(Enum(EventTypeEnum), nullable=False)

    # Detalhes
    details = Column(JSONB, default={})  # Detalhes específicos do evento

    # Métricas do evento
    duration_seconds = Column(Float, nullable=True)  # Tempo que levou (cold start, etc.)
    cost_saved_usd = Column(Float, default=0)  # Economia gerada

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relacionamentos
    instance = relationship("ServerlessInstance", back_populates="events")

    def __repr__(self):
        return f"<ServerlessEvent {self.event_type.value} at {self.created_at}>"


# =============================================================================
# HELPER: Criar schema se não existir
# =============================================================================

def create_serverless_schema(engine):
    """Cria o schema 'serverless' se não existir"""
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS serverless"))
        conn.commit()

    # Criar tabelas
    Base.metadata.create_all(engine)
