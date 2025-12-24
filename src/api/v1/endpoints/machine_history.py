"""
Machine History & Blacklist API endpoints

Endpoints para gerenciar histórico de máquinas e blacklist.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from ..dependencies import require_auth
from ....services.machine_history_service import get_machine_history_service, MachineHistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/machines/history", tags=["Machine History"], dependencies=[Depends(require_auth)])


# ==================== SCHEMAS ====================

class MachineAttemptResponse(BaseModel):
    """Resposta de uma tentativa de criação de instância."""
    id: int
    provider: str
    machine_id: str
    offer_id: Optional[str]
    gpu_name: Optional[str]
    price_per_hour: Optional[float]
    attempted_at: Optional[str]
    success: bool
    instance_id: Optional[str]
    failure_stage: Optional[str]
    failure_reason: Optional[str]
    time_to_ready_seconds: Optional[float]


class MachineBlacklistResponse(BaseModel):
    """Resposta de um item da blacklist."""
    id: int
    provider: str
    machine_id: str
    blacklist_type: str
    total_attempts: int
    failed_attempts: int
    failure_rate: float
    last_failure_reason: Optional[str]
    blacklisted_at: Optional[str]
    expires_at: Optional[str]
    is_active: bool
    reason: Optional[str]
    gpu_name: Optional[str]


class MachineStatsResponse(BaseModel):
    """Resposta de estatísticas de uma máquina."""
    provider: str
    machine_id: str
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    success_rate: float
    avg_time_to_ready: Optional[float]
    reliability_status: str
    is_blacklisted: bool
    last_seen: Optional[str]
    gpu_name: Optional[str]


class SummaryResponse(BaseModel):
    """Resposta do resumo de estatísticas."""
    period_hours: int
    provider: str
    total_attempts: int
    successful: int
    failed: int
    success_rate: float
    failure_stages: dict
    blacklisted_machines: int


class AddBlacklistRequest(BaseModel):
    """Request para adicionar à blacklist."""
    provider: str = Field(..., description="Nome do provider (vast, tensordock)")
    machine_id: str = Field(..., description="ID da máquina no provider")
    reason: str = Field(..., description="Razão do bloqueio")
    duration_hours: Optional[int] = Field(None, description="Duração em horas (None = permanente)")
    gpu_name: Optional[str] = Field(None, description="Nome da GPU (opcional)")


class RemoveBlacklistRequest(BaseModel):
    """Request para remover da blacklist."""
    provider: str
    machine_id: str


# ==================== ENDPOINTS ====================

def get_history_service() -> MachineHistoryService:
    """Dependency para obter o serviço de histórico."""
    return get_machine_history_service()


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    provider: Optional[str] = Query(None, description="Filtrar por provider"),
    hours: int = Query(24, ge=1, le=168, description="Período em horas"),
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Obtém resumo de estatísticas de máquinas.

    Retorna total de tentativas, taxa de sucesso e falhas por estágio.
    """
    summary = service.get_summary(provider=provider, hours=hours)
    return SummaryResponse(**summary)


@router.get("/attempts", response_model=List[MachineAttemptResponse])
async def list_attempts(
    provider: Optional[str] = Query(None, description="Filtrar por provider"),
    machine_id: Optional[str] = Query(None, description="Filtrar por máquina"),
    success_only: Optional[bool] = Query(None, description="Apenas sucessos ou apenas falhas"),
    hours: int = Query(72, ge=1, le=168, description="Período em horas"),
    limit: int = Query(100, ge=1, le=500, description="Limite de resultados"),
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Lista histórico de tentativas de criação de instância.
    """
    attempts = service.get_history(
        provider=provider,
        machine_id=machine_id,
        success_only=success_only,
        hours=hours,
        limit=limit,
    )
    return [MachineAttemptResponse(**a) for a in attempts]


@router.get("/stats/{provider}/{machine_id}", response_model=MachineStatsResponse)
async def get_machine_stats(
    provider: str,
    machine_id: str,
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Obtém estatísticas de uma máquina específica.
    """
    stats = service.get_machine_stats(provider, machine_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Machine stats not found")
    return MachineStatsResponse(**stats)


@router.get("/problematic", response_model=List[MachineStatsResponse])
async def list_problematic_machines(
    provider: Optional[str] = Query(None, description="Filtrar por provider"),
    min_attempts: int = Query(3, ge=1, description="Mínimo de tentativas"),
    max_success_rate: float = Query(0.5, ge=0, le=1, description="Taxa máxima de sucesso"),
    limit: int = Query(50, ge=1, le=200, description="Limite de resultados"),
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Lista máquinas problemáticas (baixa taxa de sucesso).
    """
    machines = service.get_problematic_machines(
        provider=provider,
        min_attempts=min_attempts,
        max_success_rate=max_success_rate,
        limit=limit,
    )
    return [MachineStatsResponse(**m) for m in machines]


@router.get("/reliable", response_model=List[MachineStatsResponse])
async def list_reliable_machines(
    provider: Optional[str] = Query(None, description="Filtrar por provider"),
    min_attempts: int = Query(5, ge=1, description="Mínimo de tentativas"),
    min_success_rate: float = Query(0.8, ge=0, le=1, description="Taxa mínima de sucesso"),
    limit: int = Query(50, ge=1, le=200, description="Limite de resultados"),
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Lista máquinas confiáveis (alta taxa de sucesso).
    """
    machines = service.get_reliable_machines(
        provider=provider,
        min_attempts=min_attempts,
        min_success_rate=min_success_rate,
        limit=limit,
    )
    return [MachineStatsResponse(**m) for m in machines]


# ==================== BLACKLIST ENDPOINTS ====================

@router.get("/blacklist", response_model=List[MachineBlacklistResponse])
async def list_blacklist(
    provider: Optional[str] = Query(None, description="Filtrar por provider"),
    blacklist_type: Optional[str] = Query(None, description="Filtrar por tipo (auto, manual, temporary)"),
    include_expired: bool = Query(False, description="Incluir blacklists expirados"),
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Lista máquinas na blacklist.
    """
    entries = service.list_blacklist(
        provider=provider,
        blacklist_type=blacklist_type,
        include_expired=include_expired,
    )
    return [MachineBlacklistResponse(**e.to_dict()) for e in entries]


@router.get("/blacklist/check/{provider}/{machine_id}")
async def check_blacklist(
    provider: str,
    machine_id: str,
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Verifica se uma máquina está na blacklist.
    """
    is_blacklisted = service.is_blacklisted(provider, machine_id)
    info = service.get_blacklist_info(provider, machine_id) if is_blacklisted else None

    return {
        "is_blacklisted": is_blacklisted,
        "info": info,
    }


@router.post("/blacklist", response_model=MachineBlacklistResponse)
async def add_to_blacklist(
    request: AddBlacklistRequest,
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Adiciona uma máquina à blacklist manualmente.
    """
    entry = service.add_to_blacklist(
        provider=request.provider,
        machine_id=request.machine_id,
        reason=request.reason,
        blacklist_type="manual",
        blocked_by="user",
        duration_hours=request.duration_hours,
        gpu_name=request.gpu_name,
    )
    return MachineBlacklistResponse(**entry.to_dict())


@router.delete("/blacklist/{provider}/{machine_id}")
async def remove_from_blacklist(
    provider: str,
    machine_id: str,
    service: MachineHistoryService = Depends(get_history_service),
):
    """
    Remove uma máquina da blacklist.
    """
    removed = service.remove_from_blacklist(provider, machine_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Machine not in blacklist")
    return {"success": True, "message": f"Removed {provider}:{machine_id} from blacklist"}
