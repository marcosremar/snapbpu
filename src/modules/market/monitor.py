"""
Market Monitor - Monitoramento em tempo real de preços
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .models import PricePoint, PriceTrend, MarketSnapshot

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    """Tipos de alerta"""
    PRICE_DROP = "price_drop"
    PRICE_SPIKE = "price_spike"
    LOW_AVAILABILITY = "low_availability"
    HIGH_AVAILABILITY = "high_availability"
    TREND_CHANGE = "trend_change"


@dataclass
class PriceAlert:
    """Alerta de preço"""
    alert_type: AlertType
    gpu_model: str
    current_price: float
    threshold_price: float
    triggered_at: datetime = field(default_factory=datetime.now)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_type": self.alert_type.value,
            "gpu_model": self.gpu_model,
            "current_price": self.current_price,
            "threshold_price": self.threshold_price,
            "triggered_at": self.triggered_at.isoformat(),
            "message": self.message,
        }


@dataclass
class WatchConfig:
    """Configuração de monitoramento"""
    gpu_model: str
    max_price: Optional[float] = None
    min_availability: Optional[int] = None
    check_interval_seconds: int = 60


class MarketMonitor:
    """
    Monitor de mercado GPU em tempo real.

    Uso:
        monitor = MarketMonitor()

        # Adicionar callback de alerta
        monitor.on_alert(lambda alert: print(f"Alert: {alert}"))

        # Monitorar GPU
        await monitor.watch("RTX 4090", max_price=0.40)

        # Iniciar monitoramento
        await monitor.start()
    """

    def __init__(self, vast_api_key: Optional[str] = None):
        self.vast_api_key = vast_api_key
        self._watches: Dict[str, WatchConfig] = {}
        self._alerts: List[PriceAlert] = []
        self._callbacks: List[Callable[[PriceAlert], None]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._price_history: Dict[str, List[PricePoint]] = {}

    def on_alert(self, callback: Callable[[PriceAlert], None]) -> None:
        """Registra callback para alertas"""
        self._callbacks.append(callback)

    async def watch(
        self,
        gpu_model: str,
        max_price: Optional[float] = None,
        min_availability: Optional[int] = None,
        check_interval: int = 60,
    ) -> None:
        """
        Adiciona GPU ao monitoramento.

        Args:
            gpu_model: Modelo da GPU
            max_price: Preço máximo para alerta
            min_availability: Disponibilidade mínima para alerta
            check_interval: Intervalo de verificação em segundos
        """
        self._watches[gpu_model] = WatchConfig(
            gpu_model=gpu_model,
            max_price=max_price,
            min_availability=min_availability,
            check_interval_seconds=check_interval,
        )
        logger.info(f"[MONITOR] Watching {gpu_model} (max_price={max_price})")

    async def unwatch(self, gpu_model: str) -> None:
        """Remove GPU do monitoramento"""
        if gpu_model in self._watches:
            del self._watches[gpu_model]
            logger.info(f"[MONITOR] Stopped watching {gpu_model}")

    async def start(self) -> None:
        """Inicia monitoramento"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("[MONITOR] Started monitoring")

    async def stop(self) -> None:
        """Para monitoramento"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[MONITOR] Stopped monitoring")

    async def _monitor_loop(self) -> None:
        """Loop principal de monitoramento"""
        while self._running:
            try:
                for gpu_model, config in self._watches.items():
                    await self._check_gpu(gpu_model, config)
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[MONITOR] Error in monitor loop: {e}")
                await asyncio.sleep(10)

    async def _check_gpu(self, gpu_model: str, config: WatchConfig) -> None:
        """Verifica preço de uma GPU"""
        try:
            # Obter preço atual
            price = await self._get_current_price(gpu_model)
            availability = await self._get_availability(gpu_model)

            # Registrar histórico
            if gpu_model not in self._price_history:
                self._price_history[gpu_model] = []

            self._price_history[gpu_model].append(PricePoint(
                gpu_model=gpu_model,
                price_per_hour=price,
                timestamp=datetime.now(),
                availability=availability,
            ))

            # Manter apenas últimas 24h
            cutoff = datetime.now() - timedelta(hours=24)
            self._price_history[gpu_model] = [
                p for p in self._price_history[gpu_model]
                if p.timestamp > cutoff
            ]

            # Verificar alertas
            if config.max_price and price <= config.max_price:
                await self._trigger_alert(PriceAlert(
                    alert_type=AlertType.PRICE_DROP,
                    gpu_model=gpu_model,
                    current_price=price,
                    threshold_price=config.max_price,
                    message=f"{gpu_model} price dropped to ${price:.2f}/hr (target: ${config.max_price:.2f})",
                ))

            if config.min_availability and availability <= config.min_availability:
                await self._trigger_alert(PriceAlert(
                    alert_type=AlertType.LOW_AVAILABILITY,
                    gpu_model=gpu_model,
                    current_price=price,
                    threshold_price=config.max_price or 0,
                    message=f"{gpu_model} availability low: {availability} units",
                ))

        except Exception as e:
            logger.warning(f"[MONITOR] Error checking {gpu_model}: {e}")

    async def _get_current_price(self, gpu_model: str) -> float:
        """Obtém preço atual da GPU"""
        # Em produção, buscaria da API
        base_prices = {
            "RTX 4090": 0.45,
            "RTX 4080": 0.35,
            "RTX 3090": 0.30,
            "A100": 1.50,
            "H100": 3.00,
        }
        import random
        base = base_prices.get(gpu_model, 0.50)
        return base * (1 + random.uniform(-0.1, 0.1))

    async def _get_availability(self, gpu_model: str) -> int:
        """Obtém disponibilidade da GPU"""
        # Em produção, buscaria da API
        import random
        return random.randint(5, 50)

    async def _trigger_alert(self, alert: PriceAlert) -> None:
        """Dispara alerta"""
        # Evitar alertas duplicados em 5 minutos
        recent = [
            a for a in self._alerts
            if a.gpu_model == alert.gpu_model
            and a.alert_type == alert.alert_type
            and datetime.now() - a.triggered_at < timedelta(minutes=5)
        ]
        if recent:
            return

        self._alerts.append(alert)
        logger.info(f"[MONITOR] Alert: {alert.message}")

        # Notificar callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"[MONITOR] Callback error: {e}")

    def get_alerts(self, hours: int = 24) -> List[PriceAlert]:
        """Obtém alertas recentes"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self._alerts if a.triggered_at > cutoff]

    def get_price_history(self, gpu_model: str) -> List[PricePoint]:
        """Obtém histórico de preços"""
        return self._price_history.get(gpu_model, [])

    def get_trend(self, gpu_model: str) -> PriceTrend:
        """Calcula tendência de preço"""
        history = self._price_history.get(gpu_model, [])
        if len(history) < 2:
            return PriceTrend.STABLE

        recent = history[-10:]  # Últimos 10 pontos
        prices = [p.price_per_hour for p in recent]

        avg_first = sum(prices[:len(prices)//2]) / (len(prices)//2)
        avg_last = sum(prices[len(prices)//2:]) / (len(prices) - len(prices)//2)

        change = (avg_last - avg_first) / avg_first

        if change > 0.05:
            return PriceTrend.RISING
        elif change < -0.05:
            return PriceTrend.FALLING
        elif abs(change) > 0.02:
            return PriceTrend.VOLATILE
        else:
            return PriceTrend.STABLE


# Singleton
_monitor: Optional[MarketMonitor] = None


def get_market_monitor(vast_api_key: Optional[str] = None) -> MarketMonitor:
    """Obtém instância do MarketMonitor"""
    global _monitor
    if _monitor is None:
        import os
        _monitor = MarketMonitor(
            vast_api_key=vast_api_key or os.getenv("VAST_API_KEY")
        )
    return _monitor
