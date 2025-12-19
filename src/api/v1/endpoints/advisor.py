"""
Endpoints para o AI GPU Advisor.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from src.config.database import get_db
from src.services.gpu_advisor import GPUAdvisor
from src.api.v1.dependencies import get_current_user_email

router = APIRouter()

class AdvisorRequest(BaseModel):
    project_description: str
    budget_limit: Optional[float] = None

@router.post("/recommend")
async def get_recommendation(
    request: AdvisorRequest,
    user_id: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    """
    Analisa projeto e retorna recomendação de GPU.
    """
    advisor = GPUAdvisor(db)
    result = await advisor.get_recommendation(
        project_description=request.project_description,
        budget_limit=request.budget_limit
    )
    return result

