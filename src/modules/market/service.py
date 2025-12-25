"""
Market Service - Serviço principal de mercado
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .models import MarketSnapshot, GPURecommendation, PricePoint, PriceTrend

logger = logging.getLogger(__name__)


class MarketService:
    """
    Serviço central de análise de mercado.

    Uso:
        service = MarketService()
        snapshot = await service.get_market_snapshot()
        recommendation = service.recommend_gpu(min_vram=24, max_price=0.50)
    """

    # Preços de referência (atualizados periodicamente)
    GPU_REFERENCE_PRICES = {
        "RTX 4090": {"min": 0.30, "avg": 0.45, "max": 0.80, "vram": 24},
        "RTX 4080": {"min": 0.25, "avg": 0.35, "max": 0.60, "vram": 16},
        "RTX 3090": {"min": 0.20, "avg": 0.30, "max": 0.50, "vram": 24},
        "RTX 3080": {"min": 0.15, "avg": 0.25, "max": 0.40, "vram": 10},
        "A100": {"min": 1.00, "avg": 1.50, "max": 2.50, "vram": 80},
        "H100": {"min": 2.00, "avg": 3.00, "max": 5.00, "vram": 80},
    }

    def __init__(self, vast_api_key: Optional[str] = None):
        self.vast_api_key = vast_api_key
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutos

    async def get_market_snapshot(self, provider: str = "vast") -> MarketSnapshot:
        """Obtém snapshot atual do mercado"""
        # Verificar cache
        cache_key = f"snapshot_{provider}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now() - cached["timestamp"] < timedelta(seconds=self._cache_ttl):
                return cached["data"]

        # Buscar dados atuais
        try:
            gpu_prices = {}
            gpu_availability = {}
            total_gpus = 0

            # Tentar API real
            if self.vast_api_key:
                offers = await self._fetch_vast_offers()
                for offer in offers:
                    gpu = offer.get("gpu_name", "Unknown")
                    price = offer.get("dph_total", 0)
                    if gpu not in gpu_prices or price < gpu_prices[gpu]:
                        gpu_prices[gpu] = price
                    gpu_availability[gpu] = gpu_availability.get(gpu, 0) + 1
                    total_gpus += 1
            else:
                # Usar preços de referência
                for gpu, info in self.GPU_REFERENCE_PRICES.items():
                    gpu_prices[gpu] = info["avg"]
                    gpu_availability[gpu] = 10  # Simulado
                    total_gpus += 10

            prices = list(gpu_prices.values())
            snapshot = MarketSnapshot(
                timestamp=datetime.now(),
                provider=provider,
                gpu_prices=gpu_prices,
                gpu_availability=gpu_availability,
                avg_price=sum(prices) / len(prices) if prices else 0,
                min_price=min(prices) if prices else 0,
                max_price=max(prices) if prices else 0,
                total_gpus=total_gpus,
            )

            # Atualizar cache
            self._cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": snapshot,
            }

            return snapshot

        except Exception as e:
            logger.error(f"[MARKET] Error getting snapshot: {e}")
            return MarketSnapshot(timestamp=datetime.now(), provider=provider)

    async def _fetch_vast_offers(self) -> List[Dict]:
        """Busca ofertas da Vast.ai"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://console.vast.ai/api/v0/bundles",
                    headers={"Authorization": f"Bearer {self.vast_api_key}"},
                    timeout=30
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("offers", [])
        except Exception as e:
            logger.warning(f"[MARKET] Vast API error: {e}")
        return []

    def recommend_gpu(
        self,
        min_vram: int = 0,
        max_price: float = 10.0,
        task: str = "inference",
    ) -> List[GPURecommendation]:
        """
        Recomenda GPUs baseado em requisitos.

        Args:
            min_vram: VRAM mínima em GB
            max_price: Preço máximo por hora
            task: Tipo de tarefa (inference, training, fine-tuning)
        """
        recommendations = []

        for gpu, info in self.GPU_REFERENCE_PRICES.items():
            if info["vram"] < min_vram:
                continue
            if info["avg"] > max_price:
                continue

            # Calcular score
            value_score = 100 - (info["avg"] / max_price * 50)
            vram_score = min(100, info["vram"] / min_vram * 50) if min_vram > 0 else 50
            score = (value_score + vram_score) / 2

            reasons = []
            if info["avg"] < info["min"] * 1.2:
                reasons.append("Good price currently")
            if info["vram"] >= min_vram * 1.5:
                reasons.append("Exceeds VRAM requirement")

            recommendations.append(GPURecommendation(
                gpu_model=gpu,
                price_per_hour=info["avg"],
                score=score,
                reasons=reasons,
                vram_gb=info["vram"],
                value_score=int(value_score),
            ))

        # Ordenar por score
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:5]

    def get_price_history(
        self,
        gpu_model: str,
        hours: int = 24,
    ) -> List[PricePoint]:
        """Obtém histórico de preços"""
        # Em produção, buscaria do banco de dados
        # Por enquanto, retorna dados simulados
        history = []
        base_price = self.GPU_REFERENCE_PRICES.get(gpu_model, {}).get("avg", 0.50)

        import random
        for i in range(hours):
            variation = random.uniform(-0.1, 0.1)
            history.append(PricePoint(
                gpu_model=gpu_model,
                price_per_hour=base_price * (1 + variation),
                timestamp=datetime.now() - timedelta(hours=hours - i),
            ))

        return history


# Singleton
_service: Optional[MarketService] = None


def get_market_service(vast_api_key: Optional[str] = None) -> MarketService:
    """Obtém instância do MarketService"""
    global _service
    if _service is None:
        import os
        _service = MarketService(
            vast_api_key=vast_api_key or os.getenv("VAST_API_KEY")
        )
    return _service
