"""
Modelos para tracking de uso e economia.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from datetime import datetime
from src.config.database import Base


class UsageRecord(Base):
    """
    Registro de uso de GPU para cálculo de economia.
    """
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    instance_id = Column(String(100), nullable=False, index=True)
    gpu_type = Column(String(100), nullable=False, index=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True, index=True)
    
    # Duração e Custo
    duration_minutes = Column(Integer, default=0)
    cost_dumont = Column(Float, default=0.0)
    
    # Custos equivalentes em outros providers (para comparação)
    cost_aws_equivalent = Column(Float, default=0.0)
    cost_gcp_equivalent = Column(Float, default=0.0)
    cost_azure_equivalent = Column(Float, default=0.0)
    
    # Status atual do registro
    status = Column(String(50), default="running")  # "running", "completed", "hibernated"

    __table_args__ = (
        Index('idx_user_usage_period', 'user_id', 'started_at'),
        Index('idx_instance_usage', 'instance_id', 'started_at'),
    )

    def __repr__(self):
        return f"<UsageRecord(user={self.user_id}, gpu={self.gpu_type}, cost={self.cost_dumont})>"


class GPUPricingReference(Base):
    """
    Tabela de referência de preços por GPU em diferentes providers.
    """
    __tablename__ = "gpu_pricing_references"

    id = Column(Integer, primary_key=True, index=True)
    gpu_type = Column(String(100), unique=True, nullable=False, index=True)
    vram_gb = Column(Integer, nullable=False)
    
    # Preços horários
    dumont_hourly = Column(Float, nullable=False)
    aws_equivalent_hourly = Column(Float, nullable=False)
    gcp_equivalent_hourly = Column(Float, nullable=False)
    azure_equivalent_hourly = Column(Float, nullable=False)
    
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GPUPricingReference(gpu={self.gpu_type}, dumont=${self.dumont_hourly}/h)>"

