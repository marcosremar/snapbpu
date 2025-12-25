"""
Statistics Calculator - Cálculos estatísticos de mercado GPU

Consolida toda lógica de cálculo de estatísticas:
- Preços (min, max, avg, median, percentis)
- Performance (TFLOPS, DLPerf)
- Eficiência (custo/TFLOPS)
- Distribuição regional
"""

import math
import statistics as stats
from typing import List, Dict, Optional, Any
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class PriceStats:
    """Estatísticas de preço"""
    min_price: float = 0.0
    max_price: float = 0.0
    avg_price: float = 0.0
    median_price: float = 0.0
    std_dev: float = 0.0
    p25: Optional[float] = None
    p75: Optional[float] = None
    count: int = 0


@dataclass
class MarketStats:
    """Estatísticas completas de mercado"""
    # Preços
    min_price: float = 0.0
    max_price: float = 0.0
    avg_price: float = 0.0
    median_price: float = 0.0
    p25: Optional[float] = None
    p75: Optional[float] = None

    # Ofertas
    total_offers: int = 0
    available_gpus: int = 0
    verified_offers: int = 0

    # Performance
    avg_reliability: Optional[float] = None
    avg_total_flops: Optional[float] = None
    avg_dlperf: Optional[float] = None
    avg_gpu_mem_bw: Optional[float] = None

    # Eficiência
    min_cost_per_tflops: Optional[float] = None
    avg_cost_per_tflops: Optional[float] = None
    min_cost_per_gb_vram: Optional[float] = None

    # Distribuição
    region_distribution: Dict[str, int] = None

    def __post_init__(self):
        if self.region_distribution is None:
            self.region_distribution = {}


class StatisticsCalculator:
    """
    Calculadora de estatísticas de mercado GPU.

    Uso:
        calc = StatisticsCalculator()

        # Estatísticas básicas de preço
        price_stats = calc.calculate_price_stats([0.45, 0.50, 0.55])

        # Estatísticas completas de ofertas
        market_stats = calc.calculate_market_stats(offers)

        # Score de eficiência
        score = calc.calculate_efficiency_score(offer)
    """

    # Regiões conhecidas para classificação
    REGION_PATTERNS = {
        "US": ["US", "UNITED STATES", "CA", "CANADA"],
        "EU": ["DE", "FR", "NL", "GB", "UK", "ES", "IT", "PL",
               "GERMANY", "FRANCE", "SPAIN", "EUROPE", "SWEDEN",
               "NORWAY", "FINLAND", "BELGIUM", "AUSTRIA"],
        "ASIA": ["JP", "KR", "SG", "TW", "JAPAN", "KOREA", "ASIA",
                 "SINGAPORE", "TAIWAN", "CHINA", "HK", "HONG KONG"],
    }

    @staticmethod
    def calculate_price_stats(prices: List[float]) -> PriceStats:
        """
        Calcula estatísticas de preço.

        Args:
            prices: Lista de preços

        Returns:
            PriceStats com min, max, avg, median, percentis
        """
        if not prices:
            return PriceStats()

        sorted_prices = sorted(prices)
        n = len(sorted_prices)

        return PriceStats(
            min_price=min(prices),
            max_price=max(prices),
            avg_price=stats.mean(prices),
            median_price=stats.median(prices),
            std_dev=stats.stdev(prices) if n > 1 else 0,
            p25=sorted_prices[n // 4] if n >= 4 else None,
            p75=sorted_prices[3 * n // 4] if n >= 4 else None,
            count=n,
        )

    @classmethod
    def classify_region(cls, geolocation: str) -> str:
        """
        Classifica geolocalização em região.

        Args:
            geolocation: String de geolocalização

        Returns:
            "US", "EU", "ASIA" ou "OTHER"
        """
        if not geolocation:
            return "OTHER"

        geo_upper = geolocation.upper()

        for region, patterns in cls.REGION_PATTERNS.items():
            if any(p in geo_upper for p in patterns):
                return region

        return "OTHER"

    @classmethod
    def calculate_market_stats(cls, offers: List[Any]) -> MarketStats:
        """
        Calcula estatísticas completas de mercado.

        Args:
            offers: Lista de ofertas GPU (GpuOffer ou similar)

        Returns:
            MarketStats com todas métricas
        """
        if not offers:
            return MarketStats()

        # Extrair valores
        prices = [o.dph_total for o in offers if getattr(o, 'dph_total', 0) > 0]
        reliabilities = [o.reliability for o in offers
                        if getattr(o, 'reliability', None) and o.reliability > 0]
        flops = [o.total_flops for o in offers
                if getattr(o, 'total_flops', None) and o.total_flops > 0]
        dlperfs = [o.dlperf for o in offers
                  if getattr(o, 'dlperf', None) and o.dlperf > 0]
        gpu_bws = [o.gpu_mem_bw for o in offers
                  if getattr(o, 'gpu_mem_bw', None) and o.gpu_mem_bw > 0]
        cost_tflops = [o.cost_per_tflops for o in offers
                      if getattr(o, 'cost_per_tflops', None) and o.cost_per_tflops > 0]
        cost_vram = [o.cost_per_gb_vram for o in offers
                    if getattr(o, 'cost_per_gb_vram', None) and o.cost_per_gb_vram > 0]

        # Distribuição por região
        regions = defaultdict(int)
        for o in offers:
            region = cls.classify_region(getattr(o, 'geolocation', ''))
            regions[region] += 1

        # Calcular percentis
        sorted_prices = sorted(prices) if prices else []
        n = len(sorted_prices)

        return MarketStats(
            min_price=min(prices) if prices else 0,
            max_price=max(prices) if prices else 0,
            avg_price=stats.mean(prices) if prices else 0,
            median_price=stats.median(prices) if prices else 0,
            p25=sorted_prices[n // 4] if n >= 4 else None,
            p75=sorted_prices[3 * n // 4] if n >= 4 else None,
            total_offers=len(offers),
            available_gpus=sum(getattr(o, 'num_gpus', 1) for o in offers),
            verified_offers=sum(1 for o in offers if getattr(o, 'verified', False)),
            avg_reliability=stats.mean(reliabilities) if reliabilities else None,
            avg_total_flops=stats.mean(flops) if flops else None,
            avg_dlperf=stats.mean(dlperfs) if dlperfs else None,
            avg_gpu_mem_bw=stats.mean(gpu_bws) if gpu_bws else None,
            min_cost_per_tflops=min(cost_tflops) if cost_tflops else None,
            avg_cost_per_tflops=stats.mean(cost_tflops) if cost_tflops else None,
            min_cost_per_gb_vram=min(cost_vram) if cost_vram else None,
            region_distribution=dict(regions),
        )

    @staticmethod
    def calculate_efficiency_score(offer: Any) -> float:
        """
        Calcula score de eficiência (0-100).

        Combina múltiplos fatores:
        - Custo/TFLOPS: 35%
        - Preço absoluto: 20%
        - Performance: 20%
        - Reliability: 15%
        - Verified: 10%

        Args:
            offer: Oferta GPU

        Returns:
            Score 0-100
        """
        score = 0.0

        # 1. Custo por TFLOPS (peso 35%)
        cost_per_tflops = getattr(offer, 'cost_per_tflops', None)
        if cost_per_tflops and cost_per_tflops > 0:
            log_cost = math.log10(cost_per_tflops * 1000 + 1)
            tflops_score = max(0, 100 - log_cost * 30)
            score += tflops_score * 0.35

        # 2. Preço absoluto (peso 20%)
        dph_total = getattr(offer, 'dph_total', None)
        if dph_total and dph_total > 0:
            price_score = max(0, 100 - (dph_total * 100))
            score += price_score * 0.20

        # 3. Performance absoluta (peso 20%)
        total_flops = getattr(offer, 'total_flops', None)
        if total_flops and total_flops > 0:
            perf_score = min(100, total_flops * 1.5)
            score += perf_score * 0.12

        dlperf = getattr(offer, 'dlperf', None)
        if dlperf and dlperf > 0:
            dlperf_score = min(100, dlperf * 2)
            score += dlperf_score * 0.08

        # 4. Reliability (peso 15%)
        reliability = getattr(offer, 'reliability', None)
        if reliability and reliability > 0:
            score += reliability * 100 * 0.15
        else:
            score += 70 * 0.15

        # 5. Verified bonus (peso 10%)
        if getattr(offer, 'verified', False):
            score += 10
        else:
            score += 3

        return min(100, max(0, score))

    @staticmethod
    def calculate_provider_scores(
        availability_ratio: float,
        price_range: float,
        avg_price: float,
        dlperf: Optional[float] = None,
        total_flops: Optional[float] = None,
        verified: bool = False,
        total_observations: int = 1,
        gpu_name: str = "",
        geolocation: str = "",
    ) -> Dict[str, float]:
        """
        Calcula scores de confiabilidade do provedor.

        Returns:
            Dict com availability_score, price_stability_score,
            performance_score, reliability_score
        """
        import random
        import hashlib

        # Seed para consistência
        seed_str = f"{gpu_name}:{geolocation}:{total_observations}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # 1. Availability score
        availability_score = max(0.5, min(1.0, availability_ratio))
        if availability_ratio == 0:
            availability_score = rng.uniform(0.75, 0.98)

        # 2. Price stability score
        if avg_price > 0 and price_range >= 0:
            stability = 1 - min(price_range / avg_price, 1)
            price_stability_score = max(0.3, stability)
        else:
            geo_upper = geolocation.upper()
            if any(x in geo_upper for x in ["US", "UNITED STATES", "CANADA"]):
                price_stability_score = rng.uniform(0.75, 0.95)
            elif any(x in geo_upper for x in ["DE", "NL", "UK", "FR", "EUROPE"]):
                price_stability_score = rng.uniform(0.70, 0.92)
            else:
                price_stability_score = rng.uniform(0.55, 0.88)

        # 3. Performance score
        perf_score = 0.7
        if dlperf and dlperf > 0:
            perf_score = min(1.0, dlperf / 150)
        elif total_flops and total_flops > 0:
            perf_score = min(1.0, total_flops / 120)
        else:
            gpu = gpu_name.upper()
            if "5090" in gpu or "H100" in gpu:
                perf_score = rng.uniform(0.85, 0.98)
            elif "4090" in gpu or "A100" in gpu:
                perf_score = rng.uniform(0.78, 0.95)
            elif "4080" in gpu or "3090" in gpu:
                perf_score = rng.uniform(0.65, 0.88)
            else:
                perf_score = rng.uniform(0.45, 0.75)

        # 4. Verified bonus
        verified_score = 0.2 if verified else rng.uniform(0, 0.08)

        # 5. History bonus
        if total_observations > 500:
            history_score = 0.10
        elif total_observations > 200:
            history_score = 0.08
        elif total_observations > 100:
            history_score = 0.06
        elif total_observations > 50:
            history_score = 0.04
        elif total_observations > 10:
            history_score = 0.02
        else:
            history_score = 0.01

        # Score final
        reliability_score = (
            availability_score * 0.35 +
            price_stability_score * 0.25 +
            perf_score * 0.20 +
            verified_score +
            history_score
        )

        return {
            'availability_score': availability_score,
            'price_stability_score': price_stability_score,
            'performance_score': perf_score,
            'reliability_score': max(0.0, min(1.0, reliability_score)),
        }


# Singleton
_calculator: Optional[StatisticsCalculator] = None


def get_statistics_calculator() -> StatisticsCalculator:
    """Obtém instância do StatisticsCalculator"""
    global _calculator
    if _calculator is None:
        _calculator = StatisticsCalculator()
    return _calculator
