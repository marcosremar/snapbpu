"""
Modelos de banco de dados para status de instâncias e auto-hibernação.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, ForeignKey
from datetime import datetime
from src.config.database import Base


class InstanceStatus(Base):
    """Tabela para armazenar status e configuração de auto-hibernação de instâncias."""

    __tablename__ = "instance_status"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Status atual
    status = Column(String(50), nullable=False, default="unknown")  # "running", "idle", "hibernated", "deleted", "waking"
    gpu_utilization = Column(Float, default=0.0)  # % de uso da GPU
    last_activity = Column(DateTime, default=datetime.utcnow)  # Última atividade detectada
    last_heartbeat = Column(DateTime, nullable=True)  # Último heartbeat do DumontAgent

    # Hibernação
    idle_since = Column(DateTime, nullable=True)  # Quando ficou ociosa
    hibernated_at = Column(DateTime, nullable=True)  # Quando foi hibernada
    snapshot_id = Column(String(200), nullable=True)  # ID do snapshot no R2
    woke_at = Column(DateTime, nullable=True)  # Última vez que acordou

    # Configuração de auto-hibernação
    auto_hibernation_enabled = Column(Boolean, default=True)
    pause_after_minutes = Column(Integer, default=3)  # Pausar após X minutos ociosa
    delete_after_minutes = Column(Integer, default=30)  # Deletar após X minutos pausada
    gpu_usage_threshold = Column(Float, default=5.0)  # Threshold de uso (%)
    idle_timeout_seconds = Column(Integer, default=180)  # Timeout em segundos (3 min)
    last_snapshot_id = Column(String(200), nullable=True)  # ID do último snapshot

    # Vast.ai info
    vast_instance_id = Column(Integer, nullable=True, index=True)
    gpu_type = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    ssh_host = Column(String(100), nullable=True)
    ssh_port = Column(Integer, nullable=True)

    # Agendamento (wake/sleep automático)
    scheduled_wake_enabled = Column(Boolean, default=False)
    scheduled_wake_time = Column(String(10), nullable=True)  # "09:00"
    scheduled_sleep_time = Column(String(10), nullable=True)  # "18:00"
    timezone = Column(String(50), default="America/Sao_Paulo")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Índices compostos
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_vast_instance', 'vast_instance_id'),
    )

    def __repr__(self):
        return f"<InstanceStatus(id={self.instance_id}, status={self.status}, gpu_util={self.gpu_utilization}%)>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'instance_id': self.instance_id,
            'user_id': self.user_id,
            'status': self.status,
            'gpu_utilization': self.gpu_utilization,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'idle_since': self.idle_since.isoformat() if self.idle_since else None,
            'hibernated_at': self.hibernated_at.isoformat() if self.hibernated_at else None,
            'snapshot_id': self.snapshot_id,
            'auto_hibernation': {
                'enabled': self.auto_hibernation_enabled,
                'pause_after_minutes': self.pause_after_minutes,
                'delete_after_minutes': self.delete_after_minutes,
                'gpu_usage_threshold': self.gpu_usage_threshold,
            },
            'vast_info': {
                'instance_id': self.vast_instance_id,
                'gpu_type': self.gpu_type,
                'region': self.region,
                'ssh_host': self.ssh_host,
                'ssh_port': self.ssh_port,
            },
            'schedule': {
                'enabled': self.scheduled_wake_enabled,
                'wake_time': self.scheduled_wake_time,
                'sleep_time': self.scheduled_sleep_time,
                'timezone': self.timezone,
            } if self.scheduled_wake_enabled else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class HibernationEvent(Base):
    """Tabela para log de eventos de hibernação."""

    __tablename__ = "hibernation_events"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String(100), ForeignKey('instance_status.instance_id'), nullable=False, index=True)

    # Tipo de evento
    event_type = Column(String(50), nullable=False, index=True)
    # Tipos: "idle_detected", "hibernated", "woke_up", "deleted", "restored", "auto_wake", "manual_wake"

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Metadata do evento
    gpu_utilization = Column(Float, nullable=True)
    snapshot_id = Column(String(200), nullable=True)
    reason = Column(String(500), nullable=True)  # Motivo (ex: "GPU ociosa por 3 minutos")
    
    # Economia (para calcular savings)
    dph_total = Column(Float, nullable=True)  # Preço por hora da instância
    idle_hours = Column(Float, nullable=True)  # Horas economizadas
    savings_usd = Column(Float, nullable=True)  # Valor economizado em USD

    # Info adicional (JSON-like)
    event_metadata = Column(String(2000), nullable=True)  # JSON string com dados extras

    # Índice composto para buscas por instância e data
    __table_args__ = (
        Index('idx_instance_timestamp', 'instance_id', 'timestamp'),
        Index('idx_event_type', 'event_type', 'timestamp'),
    )

    def __repr__(self):
        return f"<HibernationEvent(instance={self.instance_id}, type={self.event_type}, time={self.timestamp})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'gpu_utilization': self.gpu_utilization,
            'snapshot_id': self.snapshot_id,
            'reason': self.reason,
            'dph_total': self.dph_total,
            'idle_hours': self.idle_hours,
            'savings_usd': self.savings_usd,
            'metadata': self.event_metadata,
        }

