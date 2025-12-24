"""
Spot GPU Services - Deploy e failover de instâncias spot

Instâncias spot são mais baratas mas podem ser interrompidas.
Este módulo gerencia:
- Templates (snapshots) para restore rápido
- Deploy via bidding
- Monitoramento de interrupções
- Failover automático
"""

from .spot_manager import SpotManager, SpotConfig, get_spot_manager

__all__ = ['SpotManager', 'SpotConfig', 'get_spot_manager']
