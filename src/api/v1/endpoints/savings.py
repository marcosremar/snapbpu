"""
Endpoints para o Dashboard de Economia.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from src.config.database import get_db
from src.api.v1.dependencies import get_current_user_email
from src.services.savings_calculator import SavingsCalculator
from src.api.v1.schemas.savings import (
    SavingsSummaryResponse,
    SavingsHistoryResponse,
    SavingsBreakdownResponse,
    GPUPriceComparisonResponse
)

router = APIRouter()


@router.get("/summary", response_model=SavingsSummaryResponse)
async def get_savings_summary(
    period: str = Query("month", regex="^(day|week|month|year|all)$"),
    user_id: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Retorna resumo de economia do usuário."""
    calculator = SavingsCalculator(db)
    return calculator.calculate_user_savings(user_id, period)


@router.get("/history", response_model=SavingsHistoryResponse)
async def get_savings_history(
    months: int = Query(6, ge=1, le=24),
    user_id: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Retorna histórico mensal de economia."""
    calculator = SavingsCalculator(db)
    history = calculator.get_savings_history(user_id, months)
    return {"history": history}


@router.get("/breakdown", response_model=SavingsBreakdownResponse)
async def get_savings_breakdown(
    period: str = Query("month", regex="^(day|week|month|year|all)$"),
    user_id: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """Retorna breakdown por GPU/máquina."""
    calculator = SavingsCalculator(db)
    breakdown = calculator.get_savings_breakdown(user_id, period)
    return {"breakdown": breakdown}


@router.get("/comparison/{gpu_type}", response_model=GPUPriceComparisonResponse)
async def get_gpu_price_comparison(
    gpu_type: str,
    db: Session = Depends(get_db)
):
    """Retorna comparação de preços para uma GPU."""
    calculator = SavingsCalculator(db)
    return calculator.get_realtime_comparison(gpu_type)

