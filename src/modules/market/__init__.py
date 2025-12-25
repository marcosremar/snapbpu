"""
Market Module - Intelligence de mercado GPU

Este módulo consolida toda a lógica de análise de mercado:
- Coleta de dados VAST.ai (MarketCollector)
- Previsão de preços (PricePredictor)
- Monitoramento em tempo real (MarketMonitor)
- Cálculo de economia (SavingsCalculator)
- Estatísticas (StatisticsCalculator)
- Agente de background (MarketAgent)

Uso:
    from src.modules.market import MarketService, PricePredictor

    # Monitorar preços
    service = MarketService()
    prices = await service.get_current_prices(gpu_model="RTX 4090")

    # Prever preços
    predictor = PricePredictor()
    forecast = predictor.predict(gpu_model="RTX 4090", hours_ahead=24)

    # Agente de background
    agent = get_market_agent()
    agent.start()
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

from .statistics import (
    StatisticsCalculator,
    PriceStats,
    MarketStats,
    get_statistics_calculator,
)

from .collector import (
    MarketCollector,
    get_collector,
    DEFAULT_GPUS,
    MACHINE_TYPES,
)

from .agent import (
    MarketAgent,
    MarketMonitorAgent,  # Alias para compatibilidade
    get_market_agent,
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
    # Statistics (NEW)
    "StatisticsCalculator",
    "PriceStats",
    "MarketStats",
    "get_statistics_calculator",
    # Collector (NEW)
    "MarketCollector",
    "get_collector",
    "DEFAULT_GPUS",
    "MACHINE_TYPES",
    # Agent (NEW)
    "MarketAgent",
    "MarketMonitorAgent",
    "get_market_agent",
]
