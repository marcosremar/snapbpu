"""
Endpoints para métricas de auto-hibernação.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List

from src.config.database import get_db
from src.api.v1.dependencies import get_current_user_email
from src.models.instance_status import InstanceStatus, HibernationEvent

router = APIRouter()

@router.get("/stats")
async def get_hibernation_stats(
    user_id: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    Retorna estatísticas de economia por auto-hibernação.
    """
    # Total economizado por este usuário
    stats = db.query(
        func.count(HibernationEvent.id).label("total_hibernations"),
        func.sum(HibernationEvent.idle_hours).label("total_hours"),
        func.sum(HibernationEvent.savings_usd).label("total_savings")
    ).join(InstanceStatus, InstanceStatus.instance_id == HibernationEvent.instance_id)\
     .filter(InstanceStatus.user_id == user_id)\
     .filter(HibernationEvent.event_type == "hibernated")\
     .first()

    # Breakdown por máquina
    machines = db.query(
        InstanceStatus.instance_id,
        func.count(HibernationEvent.id).label("hibernations"),
        func.sum(HibernationEvent.savings_usd).label("savings")
    ).join(HibernationEvent, InstanceStatus.instance_id == HibernationEvent.instance_id)\
     .filter(InstanceStatus.user_id == user_id)\
     .group_by(InstanceStatus.instance_id).all()

    return {
        "total_hibernations": stats.total_hibernations or 0,
        "total_hours_saved": round(stats.total_hours or 0, 1),
        "total_savings": round(stats.total_savings or 0, 2),
        "machines": [
            {
                "instance_id": m.instance_id,
                "hibernations": m.hibernations,
                "savings": round(m.savings, 2)
            } for m in machines
        ]
    }

