"""
Endpoint: Interruption Rate by Provider.

Taxa de interrupção por provedor para avaliar riscos.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

from ...schemas.spot.interruption import InterruptionRateItem, InterruptionRateResponse
from .....config.database import SessionLocal
from .....models.metrics import ProviderReliability

router = APIRouter(tags=["Spot Interruption"])


@router.get("/interruption-rates", response_model=InterruptionRateResponse)
async def get_interruption_rates(
    gpu_name: Optional[str] = Query(None, description="Filtrar por GPU"),
    geolocation: Optional[str] = Query(None, description="Filtrar por região"),
    max_rate: float = Query(1.0, ge=0, le=1, description="Taxa máxima de interrupção"),
    limit: int = Query(50, le=200, description="Limite de resultados"),
):
    """
    Taxa de interrupção por provedor.

    Mostra quais provedores têm menor risco de interrupção.
    Ordenado por taxa de interrupção (menor primeiro).
    """
    db = SessionLocal()
    try:
        query = db.query(ProviderReliability)

        if gpu_name:
            query = query.filter(ProviderReliability.gpu_name == gpu_name)
        if geolocation:
            query = query.filter(ProviderReliability.geolocation.ilike(f"%{geolocation}%"))

        # Ordenar por availability_score (menor = maior interrupção = mais relevante mostrar)
        providers = query.order_by(ProviderReliability.availability_score.asc()).limit(limit * 2).all()

        items = []
        total_rate = 0
        safe_count = 0

        for p in providers:
            # Usar availability_score para taxa de interrupção (mais preciso)
            availability = p.availability_score or 0.8
            interruption_rate = 1 - availability

            if interruption_rate > max_rate:
                continue

            # Uptime baseado na disponibilidade real
            avg_uptime = availability * 24  # horas estimadas por dia

            # Classificar risco baseado na taxa de interrupção
            if interruption_rate < 0.10:
                risk = "low"
                safe_count += 1
            elif interruption_rate < 0.25:
                risk = "medium"
            else:
                risk = "high"

            item = InterruptionRateItem(
                machine_id=p.machine_id,
                hostname=p.hostname,
                geolocation=p.geolocation,
                gpu_name=p.gpu_name,
                interruption_rate=round(interruption_rate, 3),
                avg_uptime_hours=round(avg_uptime, 1),
                total_rentals=p.total_observations or 1,
                successful_completions=int((p.total_observations or 1) * availability),
                reliability_score=round(p.reliability_score or 0.7, 3),
                risk_level=risk,
            )
            items.append(item)
            total_rate += interruption_rate

        items.sort(key=lambda x: x.interruption_rate)
        avg_rate = total_rate / len(items) if items else 0

        return InterruptionRateResponse(
            items=items,
            avg_interruption_rate=round(avg_rate, 3),
            safest_providers=safe_count,
            generated_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()
