"""
Serverless GPU API endpoints

Permite configurar GPUs para auto-pause/resume baseado em idle timeout.
Dois modos:
- FAST: Usa CPU Standby (recovery <1s)
- ECONOMIC: Usa VAST.ai pause/resume nativo (recovery ~7s, testado dez/2024)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

from ..dependencies import require_auth, get_current_user_email
from ....services.standby.serverless import get_serverless_manager, ServerlessMode
from ....infrastructure.providers import FileUserRepository
from ....core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/serverless", tags=["Serverless GPU"], dependencies=[Depends(require_auth)])


class ServerlessModeEnum(str, Enum):
    """Modos serverless disponíveis via API"""
    fast = "fast"           # CPU Standby - recovery <1s
    economic = "economic"   # VAST.ai pause/resume - recovery ~7s
    spot = "spot"           # Spot instances - 60-70% cheaper, recovery ~30s


class EnableServerlessRequest(BaseModel):
    """Request para habilitar modo serverless"""
    mode: ServerlessModeEnum = Field(
        ServerlessModeEnum.spot,  # Spot é o default agora (mais econômico)
        description="Modo: 'spot' (60-70% mais barato, ~30s recovery), 'economic' (~7s), ou 'fast' (<1s)"
    )
    idle_timeout_seconds: int = Field(
        10,
        ge=2,
        le=3600,
        description="Segundos de idle antes de pausar (2-3600)"
    )
    gpu_threshold: float = Field(
        5.0,
        ge=0,
        le=100,
        description="% GPU utilization abaixo do qual considera idle"
    )
    keep_warm: bool = Field(
        False,
        description="Se True, nunca pausa automaticamente (override)"
    )


class ServerlessStatusResponse(BaseModel):
    """Response com status serverless de uma instância"""
    instance_id: int
    mode: str
    is_paused: bool
    idle_timeout_seconds: int
    current_gpu_util: float
    idle_since: Optional[str]
    will_pause_at: Optional[str]
    total_savings_usd: float
    avg_cold_start_seconds: float


class ServerlessListResponse(BaseModel):
    """Response com lista de instâncias serverless"""
    count: int
    instances: List[Dict[str, Any]]


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/enable/{instance_id}")
async def enable_serverless(
    instance_id: int,
    request: EnableServerlessRequest = EnableServerlessRequest(),
    user_email: str = Depends(get_current_user_email),
):
    """
    Habilita modo serverless para uma instância GPU.

    Quando habilitado, a GPU será automaticamente pausada após ficar
    idle (GPU utilization < threshold) pelo tempo configurado.

    **Modos disponíveis:**

    - **fast**: Usa CPU Standby com sincronização contínua.
      Recovery ultra-rápido (<1s). Custo idle: ~$0.01/hr.
      Requer CPU Standby configurado previamente.

    - **economic**: Usa pause/resume nativo do VAST.ai.
      Recovery rápido (~7s). Custo idle: ~$0.005/hr.
      Não requer configuração adicional.

    **Idle detection:**
    A GPU é considerada idle quando utilization < gpu_threshold.
    O DumontAgent envia heartbeats com GPU utilization a cada 30s.

    **Exemplo de uso:**
    ```
    # Pausar após 10s idle, modo econômico
    dumont serverless enable 12345 --mode economic --timeout 10

    # Pausar após 60s idle, modo rápido
    dumont serverless enable 12345 --mode fast --timeout 60
    ```
    """
    # Get user's VAST API key
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    # Configure manager with VAST provider
    manager = get_serverless_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    # Enable serverless
    result = manager.enable(
        instance_id=instance_id,
        mode=request.mode.value,
        idle_timeout_seconds=request.idle_timeout_seconds,
        gpu_threshold=request.gpu_threshold,
        keep_warm=request.keep_warm,
    )

    logger.info(f"Serverless enabled for {instance_id} by {user_email}: mode={request.mode.value}")

    return {
        **result,
        "message": f"Serverless mode '{request.mode.value}' enabled for instance {instance_id}",
        "behavior": {
            "will_pause_after": f"{request.idle_timeout_seconds}s of idle",
            "idle_threshold": f"GPU < {request.gpu_threshold}%",
            "recovery_time": "<1s" if request.mode == ServerlessModeEnum.fast else "~30s",
        }
    }


@router.post("/disable/{instance_id}")
async def disable_serverless(
    instance_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Desabilita modo serverless para uma instância.

    Se a instância estiver pausada, ela será resumida automaticamente.
    """
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    manager = get_serverless_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    result = manager.disable(instance_id)

    if result.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not configured for serverless"
        )

    logger.info(f"Serverless disabled for {instance_id} by {user_email}")

    return {
        **result,
        "message": f"Serverless disabled for instance {instance_id}"
    }


@router.get("/status/{instance_id}", response_model=ServerlessStatusResponse)
async def get_serverless_status(
    instance_id: int,
):
    """
    Obtém status serverless de uma instância específica.

    Retorna:
    - Modo atual (fast/economic/disabled)
    - Se está pausada
    - GPU utilization atual
    - Quando vai pausar (se aplicável)
    - Economia acumulada
    """
    manager = get_serverless_manager()
    instance_status = manager.get_status(instance_id)

    if not instance_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not configured for serverless"
        )

    return ServerlessStatusResponse(
        instance_id=instance_status.instance_id,
        mode=instance_status.mode,
        is_paused=instance_status.is_paused,
        idle_timeout_seconds=instance_status.idle_timeout_seconds,
        current_gpu_util=instance_status.current_gpu_util,
        idle_since=instance_status.idle_since,
        will_pause_at=instance_status.will_pause_at,
        total_savings_usd=instance_status.total_savings_usd,
        avg_cold_start_seconds=instance_status.avg_cold_start_seconds,
    )


@router.get("/list", response_model=ServerlessListResponse)
async def list_serverless_instances():
    """
    Lista todas as instâncias com serverless configurado.

    Retorna status resumido de cada instância.
    """
    manager = get_serverless_manager()
    instances = manager.list_all()

    return ServerlessListResponse(
        count=len(instances),
        instances=instances,
    )


@router.post("/wake/{instance_id}")
async def wake_instance(
    instance_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Acorda uma instância pausada (on-demand).

    Use este endpoint para acordar uma GPU antes de enviar inferências.
    Retorna o tempo de cold start.

    **Exemplo de uso em código:**
    ```python
    # Antes de enviar inferência
    response = requests.post(f"/api/v1/serverless/wake/{instance_id}")
    cold_start = response.json()["cold_start_seconds"]

    # Agora pode enviar inferência
    result = send_inference(instance_id, prompt)
    ```
    """
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    manager = get_serverless_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    result = manager.wake(instance_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    logger.info(f"Instance {instance_id} woken by {user_email}: {result.get('cold_start_seconds', 0)}s")

    return result


@router.post("/inference-start/{instance_id}")
async def notify_inference_start(instance_id: int):
    """
    Notifica que uma inferência começou.

    Reseta o idle timer para evitar que a GPU seja pausada
    durante processamento ativo.

    Chamado automaticamente pelo DumontAgent.
    """
    manager = get_serverless_manager()
    manager.on_inference_start(instance_id)

    return {"status": "ok", "idle_timer": "reset"}


@router.post("/inference-complete/{instance_id}")
async def notify_inference_complete(instance_id: int):
    """
    Notifica que uma inferência terminou.

    Inicia o idle timer. Se GPU ficar idle por mais que
    idle_timeout_seconds, será pausada automaticamente.

    Chamado automaticamente pelo DumontAgent.
    """
    manager = get_serverless_manager()
    manager.on_inference_complete(instance_id)

    return {"status": "ok", "idle_timer": "started"}


@router.get("/pricing")
async def get_serverless_pricing():
    """
    Retorna estimativas de custo para cada modo serverless.

    Compara custo de:
    - GPU ligada 24/7
    - Modo fast (CPU standby)
    - Modo economic (pause/resume)

    Baseado em uso estimado de 4h/dia de GPU ativa.
    """
    # Estimativas baseadas em GPU média $0.30/hr
    gpu_hourly = 0.30
    hours_per_day_active = 4
    hours_per_day_idle = 20
    days_per_month = 30

    # Custo 24/7
    cost_24_7 = gpu_hourly * 24 * days_per_month

    # Modo fast: GPU ativa + CPU standby durante idle
    cpu_standby_hourly = 0.01  # e2-medium spot
    cost_fast = (gpu_hourly * hours_per_day_active + cpu_standby_hourly * hours_per_day_idle) * days_per_month

    # Modo economic: GPU ativa + storage durante idle (praticamente zero)
    storage_hourly = 0.005  # Custo de storage para estado pausado
    cost_economic = (gpu_hourly * hours_per_day_active + storage_hourly * hours_per_day_idle) * days_per_month

    return {
        "assumptions": {
            "gpu_hourly_rate_usd": gpu_hourly,
            "active_hours_per_day": hours_per_day_active,
            "idle_hours_per_day": hours_per_day_idle,
            "days_per_month": days_per_month,
        },
        "monthly_costs": {
            "always_on": {
                "cost_usd": round(cost_24_7, 2),
                "description": "GPU ligada 24/7",
            },
            "serverless_fast": {
                "cost_usd": round(cost_fast, 2),
                "savings_usd": round(cost_24_7 - cost_fast, 2),
                "savings_percent": round((1 - cost_fast/cost_24_7) * 100, 1),
                "description": "Modo fast com CPU standby",
                "recovery_time": "<1 segundo",
            },
            "serverless_economic": {
                "cost_usd": round(cost_economic, 2),
                "savings_usd": round(cost_24_7 - cost_economic, 2),
                "savings_percent": round((1 - cost_economic/cost_24_7) * 100, 1),
                "description": "Modo economic com pause/resume",
                "recovery_time": "~7 segundos",
            },
        },
        "recommendation": "economic" if hours_per_day_active <= 4 else "fast",
        "note": "Preços são estimativas. Custo real depende do tipo de GPU e provedor.",
    }
