"""Modelos de banco de dados."""

from .price_history import PriceHistory, PriceAlert
from .instance_status import InstanceStatus, HibernationEvent
from .metrics import MarketSnapshot, ProviderReliability, PricePrediction, CostEfficiencyRanking
from .machine_history import MachineAttempt, MachineBlacklist, MachineStats

__all__ = [
    'PriceHistory',
    'PriceAlert',
    'InstanceStatus',
    'HibernationEvent',
    # Novos modelos de métricas expandidas
    'MarketSnapshot',
    'ProviderReliability',
    'PricePrediction',
    'CostEfficiencyRanking',
    # Machine history e blacklist
    'MachineAttempt',
    'MachineBlacklist',
    'MachineStats',
]
