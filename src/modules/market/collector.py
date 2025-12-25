"""
Market Collector - Coleta de dados de mercado GPU

Responsável por:
- Coletar ofertas de GPUs da VAST.ai
- Salvar snapshots de mercado
- Atualizar dados de provedores
- Calcular rankings de eficiência
- Tracking de estabilidade de ofertas
"""

import logging
import statistics as stats
from datetime import datetime
from typing import List, Dict, Optional, Any
from collections import defaultdict
from contextlib import contextmanager

from .statistics import StatisticsCalculator, get_statistics_calculator

logger = logging.getLogger(__name__)


# GPUs padrão para monitoramento
DEFAULT_GPUS = [
    # RTX 40 Series
    "RTX 4090", "RTX 4080", "RTX 4080 SUPER", "RTX 4070", "RTX 4070 Ti", "RTX 4070 Ti SUPER",
    # RTX 30 Series
    "RTX 3090", "RTX 3090 Ti", "RTX 3080", "RTX 3080 Ti", "RTX 3070", "RTX 3070 Ti",
    # Data Center
    "A100", "A100 SXM4 80GB", "A100 PCIe", "A100-SXM4-80GB",
    "H100", "H100 PCIe", "H100 SXM5", "H100 NVL",
    "A6000", "A5000", "A4000", "A40",
    "L40S", "L40", "L4",
    # RTX 50 Series
    "RTX 5090", "RTX 5080",
]

MACHINE_TYPES = ["on-demand", "interruptible", "bid"]


@contextmanager
def get_db_session():
    """Context manager para sessão de banco de dados."""
    from src.config.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


class MarketCollector:
    """
    Coletor de dados de mercado GPU.

    Coleta ofertas da VAST.ai e salva:
    - Snapshots agregados de mercado
    - Dados de confiabilidade de provedores
    - Rankings de custo-benefício
    - Estabilidade de ofertas

    Uso:
        collector = get_collector()
        await collector.collect_all()
    """

    def __init__(
        self,
        vast_api_key: str = "",
        gpus_to_monitor: Optional[List[str]] = None,
        machine_types: Optional[List[str]] = None,
    ):
        """
        Inicializa o coletor.

        Args:
            vast_api_key: API key da VAST.ai
            gpus_to_monitor: Lista de GPUs (padrão: DEFAULT_GPUS)
            machine_types: Tipos de máquina (padrão: MACHINE_TYPES)
        """
        import os
        self.vast_api_key = vast_api_key or os.getenv("VAST_API_KEY", "")
        self.gpus_to_monitor = gpus_to_monitor or DEFAULT_GPUS
        self.machine_types = machine_types or MACHINE_TYPES
        self.stats_calc = get_statistics_calculator()

        # Provider lazy-loaded
        self._vast_provider = None

    @property
    def vast_provider(self):
        """Lazy load do VastProvider."""
        if self._vast_provider is None:
            from src.infrastructure.providers.vast_provider import VastProvider
            self._vast_provider = VastProvider(api_key=self.vast_api_key)
        return self._vast_provider

    def collect_all(self) -> Dict[str, List[Any]]:
        """
        Executa ciclo completo de coleta.

        Returns:
            Dict com ofertas por GPU:tipo
        """
        logger.info("=" * 60)
        logger.info(f"Ciclo de monitoramento - {datetime.utcnow()}")
        logger.info("=" * 60)

        # 1. Coletar dados
        all_offers = self._collect_market_data()

        if not all_offers:
            logger.warning("Nenhuma oferta coletada neste ciclo")
            return {}

        # 2. Salvar snapshots
        self._save_market_snapshots(all_offers)

        # 3. Atualizar provedores
        self._update_provider_data(all_offers)

        # 4. Calcular rankings
        self._calculate_efficiency_rankings(all_offers)

        # 5. Atualizar estabilidade
        self._update_offer_stability(all_offers)

        logger.info("Ciclo de monitoramento concluído")
        return all_offers

    def collect_gpu(self, gpu_name: str, machine_type: str = "on-demand") -> List[Any]:
        """
        Coleta ofertas de uma GPU específica.

        Args:
            gpu_name: Nome da GPU (ex: "RTX 4090")
            machine_type: Tipo de máquina

        Returns:
            Lista de ofertas
        """
        try:
            offers = self.vast_provider.search_offers_by_type(
                machine_type=machine_type,
                gpu_name=gpu_name,
                max_price=100.0,
                limit=200,
            )
            logger.debug(f"{gpu_name}:{machine_type}: {len(offers)} ofertas")
            return offers
        except Exception as e:
            logger.warning(f"Falha ao coletar {gpu_name}:{machine_type}: {e}")
            return []

    def _collect_market_data(self) -> Dict[str, List[Any]]:
        """Coleta dados de todas GPUs e tipos."""
        all_offers = {}
        total_collected = 0

        for gpu_name in self.gpus_to_monitor:
            for machine_type in self.machine_types:
                key = f"{gpu_name}:{machine_type}"
                offers = self.collect_gpu(gpu_name, machine_type)
                all_offers[key] = offers
                total_collected += len(offers)

                if offers:
                    min_price = min(o.dph_total for o in offers if o.dph_total)
                    logger.debug(f"{key}: {len(offers)} ofertas, min=${min_price:.4f}/h")

        logger.info(f"Total coletado: {total_collected} ofertas em "
                   f"{len([k for k, v in all_offers.items() if v])} combinações")
        return all_offers

    def _save_market_snapshots(self, all_offers: Dict[str, List[Any]]):
        """Salva snapshots agregados no banco de dados."""
        from src.models.metrics import MarketSnapshot

        try:
            with get_db_session() as db:
                timestamp = datetime.utcnow()
                snapshots_saved = 0

                for key, offers in all_offers.items():
                    if not offers:
                        continue

                    gpu_name, machine_type = key.split(":")
                    market_stats = self.stats_calc.calculate_market_stats(offers)

                    snapshot = MarketSnapshot(
                        timestamp=timestamp,
                        gpu_name=gpu_name,
                        machine_type=machine_type,
                        min_price=market_stats.min_price,
                        max_price=market_stats.max_price,
                        avg_price=market_stats.avg_price,
                        median_price=market_stats.median_price,
                        percentile_25=market_stats.p25,
                        percentile_75=market_stats.p75,
                        total_offers=market_stats.total_offers,
                        available_gpus=market_stats.available_gpus,
                        verified_offers=market_stats.verified_offers,
                        avg_reliability=market_stats.avg_reliability,
                        avg_total_flops=market_stats.avg_total_flops,
                        avg_dlperf=market_stats.avg_dlperf,
                        avg_gpu_mem_bw=market_stats.avg_gpu_mem_bw,
                        min_cost_per_tflops=market_stats.min_cost_per_tflops,
                        avg_cost_per_tflops=market_stats.avg_cost_per_tflops,
                        min_cost_per_gb_vram=market_stats.min_cost_per_gb_vram,
                        region_distribution=market_stats.region_distribution,
                    )
                    db.add(snapshot)
                    snapshots_saved += 1

                logger.info(f"Salvos {snapshots_saved} snapshots de mercado")

        except Exception as e:
            logger.error(f"Erro ao salvar snapshots: {e}")

    def _update_provider_data(self, all_offers: Dict[str, List[Any]]):
        """Atualiza dados de confiabilidade de provedores."""
        from src.models.metrics import ProviderReliability

        try:
            with get_db_session() as db:
                # Agrupar por machine_id
                providers = defaultdict(list)
                for offers in all_offers.values():
                    for offer in offers:
                        if offer.machine_id:
                            providers[offer.machine_id].append(offer)

                providers_updated = 0
                for machine_id, machine_offers in providers.items():
                    provider = db.query(ProviderReliability).filter(
                        ProviderReliability.machine_id == machine_id
                    ).first()

                    if not provider:
                        provider = ProviderReliability(
                            machine_id=machine_id,
                            first_seen=datetime.utcnow()
                        )
                        db.add(provider)

                    # Atualizar com dados mais recentes
                    latest = machine_offers[0]
                    provider.hostname = latest.hostname
                    provider.geolocation = latest.geolocation
                    provider.verified = latest.verified
                    provider.gpu_name = latest.gpu_name
                    provider.last_seen = datetime.utcnow()
                    provider.last_updated = datetime.utcnow()

                    # Contadores
                    provider.total_observations = (provider.total_observations or 0) + 1
                    provider.times_available = (provider.times_available or 0) + 1

                    # Preços
                    prices = [o.dph_total for o in machine_offers if o.dph_total > 0]
                    if prices:
                        min_price = min(prices)
                        max_price = max(prices)
                        avg_price = stats.mean(prices)

                        if provider.min_price_seen is None or min_price < provider.min_price_seen:
                            provider.min_price_seen = min_price
                        if provider.max_price_seen is None or max_price > provider.max_price_seen:
                            provider.max_price_seen = max_price

                        if provider.avg_price:
                            provider.avg_price = provider.avg_price * 0.9 + avg_price * 0.1
                        else:
                            provider.avg_price = avg_price

                    # Performance
                    flops = [o.total_flops for o in machine_offers if o.total_flops]
                    if flops:
                        provider.avg_total_flops = stats.mean(flops)

                    dlperfs = [o.dlperf for o in machine_offers if o.dlperf]
                    if dlperfs:
                        provider.avg_dlperf = stats.mean(dlperfs)

                    # Calcular scores
                    self._update_provider_scores(provider, latest)
                    providers_updated += 1

                logger.info(f"Atualizados {providers_updated} provedores")

        except Exception as e:
            logger.error(f"Erro ao atualizar provedores: {e}")

    def _update_provider_scores(self, provider: Any, offer: Any):
        """Atualiza scores do provedor usando StatisticsCalculator."""
        availability_ratio = 0
        if provider.total_observations and provider.total_observations > 0:
            availability_ratio = (provider.times_available or 0) / provider.total_observations

        price_range = 0
        if provider.min_price_seen and provider.max_price_seen:
            price_range = provider.max_price_seen - provider.min_price_seen

        scores = self.stats_calc.calculate_provider_scores(
            availability_ratio=availability_ratio,
            price_range=price_range,
            avg_price=provider.avg_price or 0,
            dlperf=getattr(offer, 'dlperf', None) if offer else None,
            total_flops=getattr(offer, 'total_flops', None) if offer else None,
            verified=provider.verified or False,
            total_observations=provider.total_observations or 1,
            gpu_name=provider.gpu_name or "",
            geolocation=provider.geolocation or "",
        )

        provider.availability_score = scores['availability_score']
        provider.price_stability_score = scores['price_stability_score']
        provider.performance_score = scores['performance_score']
        provider.reliability_score = scores['reliability_score']

    def _calculate_efficiency_rankings(self, all_offers: Dict[str, List[Any]]):
        """Calcula e salva rankings de custo-benefício."""
        from src.models.metrics import CostEfficiencyRanking

        try:
            with get_db_session() as db:
                timestamp = datetime.utcnow()
                all_ranked = []

                for key, offers in all_offers.items():
                    gpu_name, machine_type = key.split(":")

                    for offer in offers:
                        if not offer.total_flops or offer.total_flops <= 0:
                            continue
                        if not offer.dph_total or offer.dph_total <= 0:
                            continue

                        score = self.stats_calc.calculate_efficiency_score(offer)

                        ranking = CostEfficiencyRanking(
                            timestamp=timestamp,
                            offer_id=offer.id,
                            gpu_name=gpu_name,
                            machine_type=machine_type,
                            dph_total=offer.dph_total,
                            total_flops=offer.total_flops,
                            gpu_ram=offer.gpu_ram,
                            dlperf=offer.dlperf,
                            gpu_mem_bw=offer.gpu_mem_bw,
                            cost_per_tflops=offer.cost_per_tflops,
                            cost_per_gb_vram=offer.cost_per_gb_vram,
                            cost_per_dlperf=(offer.dph_total / offer.dlperf
                                            if offer.dlperf and offer.dlperf > 0 else None),
                            efficiency_score=score,
                            reliability=offer.reliability,
                            verified=offer.verified,
                            geolocation=offer.geolocation,
                            machine_id=offer.machine_id,
                        )
                        all_ranked.append(ranking)

                # Ordenar e atribuir ranks
                all_ranked.sort(key=lambda x: x.efficiency_score, reverse=True)
                for i, ranking in enumerate(all_ranked):
                    ranking.rank_overall = i + 1

                # Rank por GPU
                gpu_ranks = defaultdict(list)
                for r in all_ranked:
                    gpu_ranks[r.gpu_name].append(r)

                for rankings in gpu_ranks.values():
                    for i, r in enumerate(rankings):
                        r.rank_in_gpu_class = i + 1

                # Salvar top 1000
                for ranking in all_ranked[:1000]:
                    db.add(ranking)

                logger.info(f"Salvos {min(len(all_ranked), 1000)} rankings de eficiência")

        except Exception as e:
            logger.error(f"Erro ao calcular rankings: {e}")

    def _update_offer_stability(self, all_offers: Dict[str, List[Any]]):
        """Atualiza estabilidade de ofertas."""
        from src.models.machine_history import OfferStability

        try:
            with get_db_session() as db:
                # Coletar machine_ids atuais
                current_ids = set()
                machine_data = {}

                for offers in all_offers.values():
                    for offer in offers:
                        mid = str(offer.machine_id) if offer.machine_id else None
                        if mid:
                            current_ids.add(mid)
                            machine_data[mid] = (
                                offer.gpu_name,
                                offer.dph_total or offer.min_bid,
                                offer.geolocation
                            )

                # Buscar anteriores
                previously_available = db.query(OfferStability).filter(
                    OfferStability.provider == "vast",
                    OfferStability.is_available == True,
                ).all()
                previous_ids = {str(m.machine_id) for m in previously_available}

                # Desapareceram
                disappeared = previous_ids - current_ids
                for mid in disappeared:
                    stability = db.query(OfferStability).filter(
                        OfferStability.provider == "vast",
                        OfferStability.machine_id == mid,
                    ).first()
                    if stability:
                        stability.record_disappeared()

                # Apareceram
                appeared = current_ids - previous_ids
                for mid in appeared:
                    stability = db.query(OfferStability).filter(
                        OfferStability.provider == "vast",
                        OfferStability.machine_id == mid,
                    ).first()

                    gpu_name, price, geo = machine_data.get(mid, (None, None, None))

                    if not stability:
                        stability = OfferStability(
                            provider="vast",
                            machine_id=mid,
                            gpu_name=gpu_name,
                            geolocation=geo,
                        )
                        db.add(stability)

                    stability.record_appeared(price=price, gpu_name=gpu_name, geolocation=geo)

                # Ainda disponíveis
                still_available = current_ids & previous_ids
                for mid in still_available:
                    stability = db.query(OfferStability).filter(
                        OfferStability.provider == "vast",
                        OfferStability.machine_id == mid,
                    ).first()
                    if stability:
                        stability.last_seen_at = datetime.utcnow()
                        gpu_name, price, geo = machine_data.get(mid, (None, None, None))
                        if price:
                            stability.price_per_hour = price

                # Log
                unstable_count = db.query(OfferStability).filter(
                    OfferStability.provider == "vast",
                    OfferStability.is_unstable == True,
                ).count()

                logger.info(f"Stability update: {len(appeared)} appeared, {len(disappeared)} disappeared, "
                           f"{len(still_available)} stable, {unstable_count} marked unstable")

        except Exception as e:
            logger.error(f"Error updating offer stability: {e}")


# Singleton
_collector: Optional[MarketCollector] = None


def get_collector(vast_api_key: str = "") -> MarketCollector:
    """Obtém instância do MarketCollector."""
    global _collector
    if _collector is None:
        _collector = MarketCollector(vast_api_key=vast_api_key)
    return _collector
