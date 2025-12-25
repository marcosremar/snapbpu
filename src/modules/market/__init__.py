"""
Market Module - Intelligence de mercado GPU

Este módulo consolida toda a lógica de análise de mercado:
- Previsão de preços (ML-based)
- Monitoramento em tempo real
- Cálculo de economia
- Recomendações de GPU

Uso:
    from src.modules.market import MarketService, PricePredictor

    # Monitorar preços
    service = MarketService()
    prices = await service.get_current_prices(gpu_model="RTX 4090")

    # Prever preços
    predictor = PricePredictor()
    forecast = predictor.predict(gpu_model="RTX 4090", hours_ahead=24)
"""

from .models import (
    PricePoint,
    PriceForecast,
    MarketSnapshot,
    GPURecommendation,
    SavingsReport,
)

from .service import (
    MarketService,
    get_market_service,
)

from .predictor import (
    PricePredictor,
    get_price_predictor,
)

from .monitor import (
    MarketMonitor,
    get_market_monitor,
)

from .savings import (
    SavingsCalculator,
    calculate_savings,
)

__all__ = [
    # Models
    "PricePoint",
    "PriceForecast",
    "MarketSnapshot",
    "GPURecommendation",
    "SavingsReport",
    # Service
    "MarketService",
    "get_market_service",
    # Predictor
    "PricePredictor",
    "get_price_predictor",
    # Monitor
    "MarketMonitor",
    "get_market_monitor",
    # Savings
    "SavingsCalculator",
    "calculate_savings",
]
