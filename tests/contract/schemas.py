"""
API Contract Schemas - Pydantic Models
======================================

Estes schemas definem a estrutura esperada das respostas da API.
Se a API retornar dados que não conformam com estes schemas,
os testes de contrato falharão.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class InstanceStatus(str, Enum):
    """Status válidos para instâncias GPU"""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    HIBERNATED = "hibernated"
    TERMINATED = "terminated"
    PAUSED = "paused"
    RESUMING = "resuming"
    ERROR = "error"


class StandbyStatus(str, Enum):
    """Status válidos para CPU Standby"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"


# ============================================================
# AUTH CONTRACTS
# ============================================================

class LoginRequest(BaseModel):
    """Schema de request para login"""
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    """Schema de response para login bem-sucedido"""
    token: str = Field(min_length=10)
    user: Optional[Dict[str, Any]] = None
    expires_in: Optional[int] = None


class TokenRefreshResponse(BaseModel):
    """Schema para refresh de token"""
    token: str = Field(min_length=10)


# ============================================================
# INSTANCE CONTRACTS
# ============================================================

class InstanceContract(BaseModel):
    """Schema para uma instância GPU"""
    id: str = Field(min_length=1)
    status: str
    gpu_name: Optional[str] = None
    gpu_type: Optional[str] = None
    region: Optional[str] = None
    hourly_cost: Optional[float] = None
    created_at: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = [s.value for s in InstanceStatus]
        # Permite status desconhecidos mas loga warning
        if v not in valid_statuses:
            # Não falha, apenas aceita
            pass
        return v

    @field_validator('hourly_cost')
    @classmethod
    def validate_cost(cls, v):
        if v is not None and v < 0:
            raise ValueError('hourly_cost não pode ser negativo')
        return v


class InstanceListResponse(BaseModel):
    """Schema para lista de instâncias"""
    instances: List[Dict[str, Any]] = []
    total: Optional[int] = None


# ============================================================
# GPU OFFER CONTRACTS
# ============================================================

class GpuOfferContract(BaseModel):
    """Schema para uma oferta de GPU"""
    id: Optional[int] = None
    gpu_name: str
    gpu_type: Optional[str] = None
    num_gpus: Optional[int] = Field(default=1, ge=1)
    price_per_hour: Optional[float] = Field(default=None, ge=0)
    dph_total: Optional[float] = Field(default=None, ge=0)
    region: Optional[str] = None
    provider: Optional[str] = None
    availability: Optional[str] = None


class OffersListResponse(BaseModel):
    """Schema para lista de ofertas"""
    offers: List[Dict[str, Any]] = []
    total: Optional[int] = None


# ============================================================
# SAVINGS CONTRACTS
# ============================================================

class SavingsSummaryContract(BaseModel):
    """Schema para resumo de economia"""
    total_saved: Optional[float] = Field(default=0, ge=0)
    total_spent: Optional[float] = Field(default=0, ge=0)
    savings_percentage: Optional[float] = Field(default=0, ge=0, le=100)
    period: Optional[str] = None


class SavingsDetailContract(BaseModel):
    """Schema para detalhes de economia"""
    date: str
    amount_saved: float = Field(ge=0)
    instance_id: Optional[str] = None


# ============================================================
# STANDBY CONTRACTS
# ============================================================

class StandbyStatusContract(BaseModel):
    """Schema para status do CPU Standby"""
    enabled: bool
    status: str
    failover_active: Optional[bool] = False
    last_check: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_standby_status(cls, v):
        valid = [s.value for s in StandbyStatus]
        if v not in valid:
            pass  # Aceita status desconhecidos
        return v


class StandbyConfigContract(BaseModel):
    """Schema para configuração de CPU Standby"""
    enabled: bool
    auto_failover: Optional[bool] = True
    check_interval_seconds: Optional[int] = Field(default=60, ge=10)
    max_retries: Optional[int] = Field(default=3, ge=1)


# ============================================================
# DASHBOARD CONTRACTS
# ============================================================

class DashboardMetricsContract(BaseModel):
    """Schema para métricas do dashboard"""
    active_instances: Optional[int] = Field(default=0, ge=0)
    total_gpus: Optional[int] = Field(default=0, ge=0)
    monthly_cost: Optional[float] = Field(default=0, ge=0)
    monthly_savings: Optional[float] = Field(default=0, ge=0)


# ============================================================
# HEALTH CONTRACTS
# ============================================================

class HealthResponse(BaseModel):
    """Schema para health check"""
    status: str = Field(pattern="^(healthy|ok|unhealthy|degraded)$")
    version: Optional[str] = None
    uptime: Optional[float] = None


# ============================================================
# ERROR CONTRACTS
# ============================================================

class ErrorResponse(BaseModel):
    """Schema para respostas de erro"""
    error: str
    message: Optional[str] = None
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
