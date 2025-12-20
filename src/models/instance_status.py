"""
Modelos de banco de dados para status de instâncias e auto-hibernação.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, ForeignKey, BigInteger, Text
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


class FailoverTestEvent(Base):
    """Tabela para armazenar resultados de testes de failover realistas."""

    __tablename__ = "failover_test_events"

    id = Column(Integer, primary_key=True, index=True)
    failover_id = Column(String(50), unique=True, nullable=False, index=True)
    gpu_instance_id = Column(Integer, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Snapshot - criação
    snapshot_id = Column(String(200), nullable=True)
    snapshot_size_bytes = Column(BigInteger, nullable=True)
    snapshot_creation_time_ms = Column(Integer, nullable=True)
    snapshot_files_count = Column(Integer, nullable=True)
    snapshot_compression = Column(String(20), default="lz4")
    snapshot_storage = Column(String(50), default="backblaze_b2")
    snapshot_type = Column(String(20), nullable=True)  # "full" or "incremental"
    base_snapshot_id = Column(String(200), nullable=True)  # For incremental snapshots
    files_changed = Column(Integer, nullable=True)  # For incremental snapshots

    # Restauração
    restore_time_ms = Column(Integer, nullable=True)
    restore_download_time_ms = Column(Integer, nullable=True)
    restore_decompress_time_ms = Column(Integer, nullable=True)
    data_restored_bytes = Column(BigInteger, nullable=True)

    # Inferência (Ollama)
    inference_model = Column(String(100), nullable=True)
    inference_test_prompt = Column(String(500), nullable=True)
    inference_response = Column(Text, nullable=True)
    inference_ready_time_ms = Column(Integer, nullable=True)
    inference_success = Column(Boolean, nullable=True)

    # GPU info
    original_gpu_type = Column(String(100), nullable=True)
    original_ssh_host = Column(String(100), nullable=True)  # Original GPU SSH host
    original_ssh_port = Column(Integer, nullable=True)  # Original GPU SSH port
    new_gpu_type = Column(String(100), nullable=True)
    new_gpu_instance_id = Column(Integer, nullable=True)
    gpu_search_time_ms = Column(Integer, nullable=True)
    gpu_provision_time_ms = Column(Integer, nullable=True)

    # Totais
    total_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=False)
    failure_reason = Column(String(500), nullable=True)
    failure_phase = Column(String(50), nullable=True)

    # Breakdown detalhado (JSON)
    phase_timings_json = Column(Text, nullable=True)

    # Índices
    __table_args__ = (
        Index('idx_failover_user', 'user_id', 'started_at'),
        Index('idx_failover_success', 'success', 'started_at'),
    )

    def __repr__(self):
        return f"<FailoverTestEvent(id={self.failover_id}, gpu={self.gpu_instance_id}, success={self.success})>"

    def to_dict(self):
        """Converte para dicionário para API responses."""
        import json

        phase_timings = {}
        if self.phase_timings_json:
            try:
                phase_timings = json.loads(self.phase_timings_json)
            except:
                pass

        return {
            'failover_id': self.failover_id,
            'gpu_instance_id': self.gpu_instance_id,
            'user_id': self.user_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'snapshot': {
                'id': self.snapshot_id,
                'size_bytes': self.snapshot_size_bytes,
                'size_mb': round(self.snapshot_size_bytes / (1024*1024), 2) if self.snapshot_size_bytes else None,
                'creation_time_ms': self.snapshot_creation_time_ms,
                'files_count': self.snapshot_files_count,
                'compression': self.snapshot_compression,
                'storage': self.snapshot_storage,
            },
            'restore': {
                'time_ms': self.restore_time_ms,
                'download_time_ms': self.restore_download_time_ms,
                'decompress_time_ms': self.restore_decompress_time_ms,
                'data_bytes': self.data_restored_bytes,
                'data_mb': round(self.data_restored_bytes / (1024*1024), 2) if self.data_restored_bytes else None,
            },
            'inference': {
                'model': self.inference_model,
                'prompt': self.inference_test_prompt,
                'response': self.inference_response,
                'ready_time_ms': self.inference_ready_time_ms,
                'success': self.inference_success,
            },
            'gpu': {
                'original_type': self.original_gpu_type,
                'new_type': self.new_gpu_type,
                'new_instance_id': self.new_gpu_instance_id,
                'search_time_ms': self.gpu_search_time_ms,
                'provision_time_ms': self.gpu_provision_time_ms,
            },
            'totals': {
                'total_time_ms': self.total_time_ms,
                'total_time_seconds': round(self.total_time_ms / 1000, 2) if self.total_time_ms else None,
                'success': self.success,
                'failure_reason': self.failure_reason,
                'failure_phase': self.failure_phase,
            },
            'phase_timings': phase_timings,
        }

