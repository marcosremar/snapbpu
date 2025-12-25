"""
Market Models - Dataclasses para análise de mercado
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class GPUTier(str, Enum):
    """Tiers de GPU"""
    BUDGET = "budget"       # RTX 3060, 3070
    MID = "mid"             # RTX 3080, 3090
    HIGH = "high"           # RTX 4080, 4090
    DATACENTER = "datacenter"  # A100, H100


class PriceTrend(str, Enum):
    """Tendência de preço"""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class PricePoint:
    """Ponto de preço histórico"""
    gpu_model: str
    price_per_hour: float
    timestamp: datetime
    provider: str = "vast"
    availability: int = 0  # Número de GPUs disponíveis

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gpu_model": self.gpu_model,
            "price_per_hour": self.price_per_hour,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "availability": self.availability,
        }


@dataclass
class PriceForecast:
    """Previsão de preço"""
    gpu_model: str
    current_price: float
    predicted_price: float
    prediction_time: datetime
    confidence: float  # 0.0 - 1.0
    trend: PriceTrend

    # Detalhes
    hours_ahead: int = 24
    price_change_pct: float = 0.0
    model_used: str = "linear"

    # Recomendação
    recommendation: str = ""  # "buy_now", "wait", "hold"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gpu_model": self.gpu_model,
            "current_price": self.current_price,
            "predicted_price": self.predicted_price,
            "prediction_time": self.prediction_time.isoformat(),
            "confidence": self.confidence,
            "trend": self.trend.value,
            "hours_ahead": self.hours_ahead,
            "price_change_pct": self.price_change_pct,
            "recommendation": self.recommendation,
        }


@dataclass
class MarketSnapshot:
    """Snapshot do mercado em um momento"""
    timestamp: datetime
    provider: str = "vast"

    # Preços por GPU
    gpu_prices: Dict[str, float] = field(default_factory=dict)

    # Disponibilidade
    gpu_availability: Dict[str, int] = field(default_factory=dict)

    # Estatísticas
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    total_gpus: int = 0

    # Tendências
    price_trend: PriceTrend = PriceTrend.STABLE
    demand_level: str = "normal"  # "low", "normal", "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "gpu_prices": self.gpu_prices,
            "gpu_availability": self.gpu_availability,
            "avg_price": self.avg_price,
            "total_gpus": self.total_gpus,
            "price_trend": self.price_trend.value,
            "demand_level": self.demand_level,
        }


@dataclass
class GPURecommendation:
    """Recomendação de GPU"""
    gpu_model: str
    price_per_hour: float
    score: float  # 0-100

    # Razões
    reasons: List[str] = field(default_factory=list)

    # Detalhes
    vram_gb: int = 0
    performance_score: int = 0
    value_score: int = 0
    availability_score: int = 0

    # Alternativas
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gpu_model": self.gpu_model,
            "price_per_hour": self.price_per_hour,
            "score": self.score,
            "reasons": self.reasons,
            "vram_gb": self.vram_gb,
            "alternatives": self.alternatives,
        }


@dataclass
class SavingsReport:
    """Relatório de economia"""
    period_start: datetime
    period_end: datetime

    # Custos
    on_demand_cost: float = 0.0
    spot_cost: float = 0.0
    actual_cost: float = 0.0

    # Economia
    savings_amount: float = 0.0
    savings_percentage: float = 0.0

    # Detalhes por GPU
    gpu_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Recomendações
    optimization_tips: List[str] = field(default_factory=list)
    potential_savings: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "on_demand_cost": self.on_demand_cost,
            "spot_cost": self.spot_cost,
            "actual_cost": self.actual_cost,
            "savings_amount": self.savings_amount,
            "savings_percentage": self.savings_percentage,
            "optimization_tips": self.optimization_tips,
            "potential_savings": self.potential_savings,
        }
