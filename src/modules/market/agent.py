"""
Market Agent - Agente de background para coleta de mercado

Wrapper fino que conecta o MarketCollector ao sistema de agentes.
Roda em background com auto-restart.
"""

import os
import logging
from typing import Optional, Dict, List

from src.services.agent_manager import Agent
from .collector import MarketCollector, get_collector

logger = logging.getLogger(__name__)


class MarketAgent(Agent):
    """
    Agente de background para monitoramento de mercado GPU.

    Executa ciclos de coleta em intervalos regulares,
    salvando snapshots e rankings no banco de dados.

    Uso:
        agent = get_market_agent()
        agent.start()

        # ou via AgentManager
        from src.services.agent_manager import AgentManager
        manager = AgentManager()
        manager.register(MarketAgent)
        manager.start_all()
    """

    def __init__(
        self,
        interval_minutes: int = 5,
        vast_api_key: str = "",
        gpus_to_monitor: Optional[List[str]] = None,
        machine_types: Optional[List[str]] = None,
    ):
        """
        Inicializa o agente de mercado.

        Args:
            interval_minutes: Intervalo entre ciclos (padrão: 5)
            vast_api_key: API key VAST.ai (usa env se não fornecida)
            gpus_to_monitor: Lista de GPUs para monitorar
            machine_types: Tipos de máquina
        """
        super().__init__(name="MarketMonitor")
        self.interval_seconds = interval_minutes * 60

        # Configurar collector
        api_key = vast_api_key or os.getenv("VAST_API_KEY", "")
        self.collector = MarketCollector(
            vast_api_key=api_key,
            gpus_to_monitor=gpus_to_monitor,
            machine_types=machine_types,
        )

        # Cache de último ciclo
        self.last_cycle_offers: Dict[str, list] = {}

    def run(self):
        """Loop principal do agente."""
        logger.info(
            f"MarketMonitor iniciando: {len(self.collector.gpus_to_monitor)} GPUs, "
            f"{len(self.collector.machine_types)} tipos, "
            f"intervalo={self.interval_seconds/60}min"
        )

        while self.running:
            try:
                self._monitor_cycle()
            except Exception as e:
                logger.error(f"Erro no ciclo de monitoramento: {e}", exc_info=True)

            if self.running:
                logger.info(f"Próximo ciclo em {self.interval_seconds/60} minutos...")
                self.sleep(self.interval_seconds)

    def _monitor_cycle(self):
        """Executa um ciclo de coleta."""
        self.last_cycle_offers = self.collector.collect_all()

    def get_stats(self) -> Dict:
        """Retorna estatísticas do agente."""
        return {
            'name': self.name,
            'running': self.is_running(),
            'interval_minutes': self.interval_seconds / 60,
            'gpus_monitored': self.collector.gpus_to_monitor,
            'machine_types': self.collector.machine_types,
            'last_cycle_keys': list(self.last_cycle_offers.keys()) if self.last_cycle_offers else [],
        }


# Singleton
_agent: Optional[MarketAgent] = None


def get_market_agent(
    interval_minutes: int = 5,
    vast_api_key: str = "",
) -> MarketAgent:
    """
    Obtém instância do MarketAgent.

    Args:
        interval_minutes: Intervalo entre ciclos
        vast_api_key: API key VAST.ai

    Returns:
        MarketAgent singleton
    """
    global _agent
    if _agent is None:
        _agent = MarketAgent(
            interval_minutes=interval_minutes,
            vast_api_key=vast_api_key,
        )
    return _agent


# Alias para compatibilidade
MarketMonitorAgent = MarketAgent
