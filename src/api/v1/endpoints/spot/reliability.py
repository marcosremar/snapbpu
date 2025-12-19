"""
Endpoint: Provider Reliability Score.

Score detalhado de confiabilidade de provedores.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

from ...schemas.spot.reliability import ReliabilityScoreItem, ReliabilityScoreResponse
from .....config.database import SessionLocal
from .....models.metrics import ProviderReliability

router = APIRouter(tags=["Spot Reliability"])


@router.get("/reliability", response_model=ReliabilityScoreResponse)
async def get_reliability_scores(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    min_score: float = Query(0, ge=0, le=100, description="Score mínimo"),
    limit: int = Query(50, le=200, description="Limite de resultados"),
):
    """
    Score de confiabilidade de provedores.

    Ranking detalhado de provedores por múltiplos fatores:
    - Uptime Score (40%)
    - Price Stability (30%)
    - Performance Score (30%)
    """
    db = SessionLocal()
    try:
        query = db.query(ProviderReliability)

        if gpu_name:
            query = query.filter(ProviderReliability.gpu_name == gpu_name)

        # Pegar todos para calcular estatísticas, depois limitar
        providers = query.all()

        items = []
        excellent_count = 0
        total_score = 0

        for p in providers:
            # Calcular scores (0-100) usando os valores já calculados no banco
            availability = p.availability_score or 0.5
            uptime_score = availability * 100

            price_stability = p.price_stability_score or 0.7
            price_score = price_stability * 100

            # Performance score do banco (já calculado baseado em GPU type)
            perf_score = (p.performance_score or 0.7) * 100

            # Overall score ponderado (mesmo cálculo do reliability_score * 100)
            overall = p.reliability_score * 100 if p.reliability_score else (
                uptime_score * 0.35 + price_score * 0.25 + perf_score * 0.20 + 10  # base bonus
            )

            if overall < min_score:
                continue

            # Recomendação
            if overall >= 85:
                rec = "excellent"
                excellent_count += 1
            elif overall >= 70:
                rec = "good"
            elif overall >= 50:
                rec = "fair"
            else:
                rec = "poor"

            # Dias de histórico
            if p.first_seen:
                history_days = (datetime.utcnow() - p.first_seen).days
            else:
                history_days = 1

            item = ReliabilityScoreItem(
                machine_id=p.machine_id,
                hostname=p.hostname,
                geolocation=p.geolocation,
                gpu_name=p.gpu_name,
                overall_score=round(overall, 1),
                uptime_score=round(uptime_score, 1),
                price_stability_score=round(price_score, 1),
                performance_score=round(perf_score, 1),
                history_days=history_days,
                total_rentals=p.total_observations or 1,
                recommendation=rec,
            )
            items.append(item)
            total_score += overall

            if len(items) >= limit:
                break

        avg_score = total_score / len(items) if items else 0

        return ReliabilityScoreResponse(
            items=items,
            excellent_providers=excellent_count,
            avg_score=round(avg_score, 1),
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
