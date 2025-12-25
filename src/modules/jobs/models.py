"""
Jobs Module - Database Models

Modelos para gerenciamento de jobs GPU:
- Job: Definição de um job (template)
- JobRun: Execução de um job
- JobLog: Logs de execução
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from src.config.database import Base


class JobType(enum.Enum):
    """Tipos de job suportados"""
    FINE_TUNE = "fine_tune"           # Fine-tuning de modelo
    INFERENCE = "inference"           # Inferência batch
    TRAINING = "training"             # Treinamento completo
    EMBEDDING = "embedding"           # Geração de embeddings
    CUSTOM = "custom"                 # Script customizado


class JobStatus(enum.Enum):
    """Status de execução do job"""
    PENDING = "pending"               # Aguardando GPU
    PROVISIONING = "provisioning"     # Provisionando GPU
    RUNNING = "running"               # Executando
    COMPLETED = "completed"           # Concluído com sucesso
    FAILED = "failed"                 # Falhou
    CANCELLED = "cancelled"           # Cancelado pelo usuário
    TIMEOUT = "timeout"               # Timeout excedido


class JobPriority(enum.Enum):
    """Prioridade do job"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Job(Base):
    """
    Definição de um Job (template).

    Um Job define O QUE executar, um JobRun é UMA execução desse job.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificação
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Tipo e configuração
    job_type = Column(Enum(JobType), nullable=False, default=JobType.CUSTOM)

    # Requisitos de GPU
    gpu_name = Column(String(100), nullable=True)  # Ex: "RTX 4090", None = qualquer
    min_vram_gb = Column(Integer, nullable=True)   # VRAM mínima
    max_price_per_hour = Column(Float, default=1.0)

    # Configuração de execução
    docker_image = Column(String(500), nullable=False)
    command = Column(Text, nullable=True)          # Comando a executar
    env_vars = Column(JSON, nullable=True)         # Variáveis de ambiente

    # Arquivos/dados
    input_path = Column(String(500), nullable=True)   # Caminho de entrada (S3, etc)
    output_path = Column(String(500), nullable=True)  # Caminho de saída

    # Limites
    timeout_seconds = Column(Integer, default=3600)   # 1 hora default
    max_retries = Column(Integer, default=2)
    disk_gb = Column(Integer, default=50)

    # Metadados
    config = Column(JSON, nullable=True)           # Configuração extra (hiperparâmetros, etc)
    tags = Column(JSON, nullable=True)             # Tags para organização

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    runs = relationship("JobRun", back_populates="job", lazy="dynamic")

    def __repr__(self):
        return f"<Job {self.id}: {self.name} ({self.job_type.value})>"


class JobRun(Base):
    """
    Uma execução de um Job.

    Cada vez que um Job é executado, cria-se um JobRun.
    """
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Referência ao job
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    # Identificação
    user_id = Column(String(255), nullable=False, index=True)
    run_number = Column(Integer, default=1)        # Número da execução

    # Status
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    priority = Column(Enum(JobPriority), default=JobPriority.NORMAL)

    # Instância VAST.ai
    vast_instance_id = Column(Integer, nullable=True, index=True)
    vast_offer_id = Column(Integer, nullable=True)
    gpu_name = Column(String(100), nullable=True)

    # Conexão
    ssh_host = Column(String(255), nullable=True)
    ssh_port = Column(Integer, nullable=True)

    # Tempos
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Resultados
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    output_url = Column(String(500), nullable=True)  # URL do resultado

    # Métricas
    gpu_seconds = Column(Float, default=0)         # Tempo de GPU usado
    cost_usd = Column(Float, default=0)            # Custo total
    hourly_rate = Column(Float, nullable=True)     # Taxa horária da GPU

    # Retries
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    # Metadados
    run_metadata = Column(JSON, nullable=True)     # Dados extras do run

    # Relacionamentos
    job = relationship("Job", back_populates="runs")
    logs = relationship("JobLog", back_populates="run", lazy="dynamic")

    def __repr__(self):
        return f"<JobRun {self.id}: job={self.job_id} status={self.status.value}>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duração do job em segundos"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None

    @property
    def queue_time_seconds(self) -> Optional[float]:
        """Tempo na fila em segundos"""
        if self.queued_at and self.started_at:
            return (self.started_at - self.queued_at).total_seconds()
        elif self.queued_at:
            return (datetime.utcnow() - self.queued_at).total_seconds()
        return None


class JobLog(Base):
    """
    Logs de execução de um JobRun.
    """
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Referência ao run
    run_id = Column(Integer, ForeignKey("job_runs.id"), nullable=False, index=True)

    # Log
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20), default="INFO")     # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)

    # Contexto
    stage = Column(String(50), nullable=True)      # provisioning, running, cleanup, etc

    # Relacionamento
    run = relationship("JobRun", back_populates="logs")

    def __repr__(self):
        return f"<JobLog {self.id}: [{self.level}] {self.message[:50]}...>"


# Índices adicionais para queries comuns
from sqlalchemy import Index

Index('idx_job_runs_status_queued', JobRun.status, JobRun.queued_at)
Index('idx_job_runs_user_status', JobRun.user_id, JobRun.status)
Index('idx_jobs_user_type', Job.user_id, Job.job_type)
