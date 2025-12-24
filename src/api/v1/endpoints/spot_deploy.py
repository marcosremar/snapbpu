"""
Spot GPU API endpoints

Deploy e gerenciamento de instâncias spot (interruptíveis).
Instâncias spot são 60-70% mais baratas que on-demand,
mas podem ser interrompidas se outro usuário fizer bid maior.

Estratégia:
1. Criar template (snapshot) de uma instância
2. Deploy spot usando o template
3. Failover automático quando interrompido
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from ..dependencies import require_auth, get_current_user_email
from ....services.spot import get_spot_manager
from ....infrastructure.providers import FileUserRepository
from ....core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spot", tags=["Spot GPU"], dependencies=[Depends(require_auth)])


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class CreateTemplateRequest(BaseModel):
    """Request para criar template spot"""
    region: Optional[str] = Field(
        None,
        description="Região para o template. Auto-detecta se não especificado."
    )
    workspace_path: str = Field(
        "/workspace",
        description="Path do workspace a salvar"
    )


class DeploySpotRequest(BaseModel):
    """Request para deploy spot"""
    template_id: str = Field(
        ...,
        description="ID do template a usar"
    )
    max_price: float = Field(
        1.0,
        ge=0.01,
        le=10.0,
        description="Preço máximo por hora em USD"
    )
    gpu_preference: Optional[str] = Field(
        None,
        description="GPU preferida (RTX 4090, etc). None = mais barata disponível"
    )
    auto_failover: bool = Field(
        True,
        description="Se True, failover automático quando interrompido"
    )


class TemplateResponse(BaseModel):
    """Response com detalhes de um template"""
    template_id: str
    instance_id: int
    region: str
    gpu_name: str
    created_at: str
    size_bytes: int
    workspace_path: str


class SpotInstanceResponse(BaseModel):
    """Response com detalhes de uma instância spot"""
    instance_id: int
    state: str
    template_id: str
    region: str
    bid_price: float
    max_price: float
    auto_failover: bool
    failover_count: int
    last_failover_at: Optional[str]
    ssh_host: Optional[str]
    ssh_port: Optional[int]


class SpotDeployResponse(BaseModel):
    """Response de deploy spot"""
    instance_id: int
    gpu_name: str
    bid_price: float
    ssh_host: str
    ssh_port: int
    region: str
    template_id: str
    snapshot_restored: bool


class SpotPricingResponse(BaseModel):
    """Response com estimativas de preço spot"""
    region: str
    gpu_name: Optional[str]
    offers_count: int
    cheapest_price: float
    average_price: float
    savings_vs_ondemand: float


# ============================================================
# TEMPLATE ENDPOINTS
# ============================================================

@router.post("/template/{instance_id}", response_model=Dict[str, Any])
async def create_template(
    instance_id: int,
    request: CreateTemplateRequest = CreateTemplateRequest(),
    user_email: str = Depends(get_current_user_email),
):
    """
    Cria template (snapshot) para deploy spot.

    O template fica salvo na região especificada e pode ser
    usado para deployar rapidamente em qualquer GPU da região.

    **Exemplo de uso:**
    ```bash
    # Criar template de uma instância existente
    curl -X POST /api/v1/spot/template/12345

    # Especificar região
    curl -X POST /api/v1/spot/template/12345 -d '{"region": "US"}'
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

    manager = get_spot_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    result = manager.create_template(
        instance_id=instance_id,
        region=request.region,
        workspace_path=request.workspace_path,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    logger.info(f"Template created by {user_email}: {result.get('template_id')}")

    return result


@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_templates():
    """
    Lista todos os templates spot disponíveis.
    """
    manager = get_spot_manager()
    return manager.list_templates()


@router.delete("/template/{template_id}")
async def delete_template(template_id: str):
    """
    Deleta um template spot.
    """
    manager = get_spot_manager()
    result = manager.delete_template(template_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    return result


# ============================================================
# DEPLOY ENDPOINTS
# ============================================================

@router.post("/deploy", response_model=Dict[str, Any])
async def deploy_spot(
    request: DeploySpotRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Deploya instância spot usando template.

    Busca GPU mais barata na região do template,
    faz bid, e restaura o ambiente do snapshot.

    **Economia esperada:** 60-70% vs on-demand

    **Exemplo de uso:**
    ```bash
    curl -X POST /api/v1/spot/deploy -d '{
        "template_id": "spot_tpl_12345_1703245600",
        "max_price": 0.50
    }'
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

    manager = get_spot_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    result = manager.deploy(
        template_id=request.template_id,
        max_price=request.max_price,
        gpu_preference=request.gpu_preference,
        auto_failover=request.auto_failover,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    logger.info(f"Spot deploy by {user_email}: {result.get('instance_id')}")

    return result


# ============================================================
# STATUS ENDPOINTS
# ============================================================

@router.get("/status/{instance_id}", response_model=Dict[str, Any])
async def get_spot_status(instance_id: int):
    """
    Status de uma instância spot.

    Retorna:
    - Estado atual (active, interrupted, failover, etc)
    - Preço do bid atual
    - Contagem de failovers
    - SSH host/port
    """
    manager = get_spot_manager()
    result = manager.get_status(instance_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not configured for spot"
        )

    return result


@router.get("/instances", response_model=List[Dict[str, Any]])
async def list_spot_instances():
    """
    Lista todas as instâncias spot ativas.
    """
    manager = get_spot_manager()
    return manager.list_instances()


# ============================================================
# CONTROL ENDPOINTS
# ============================================================

@router.post("/failover/{instance_id}")
async def trigger_failover(
    instance_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Trigger manual de failover (para testes).

    Simula uma interrupção e executa failover para nova GPU.
    """
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    manager = get_spot_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    result = manager.trigger_failover(instance_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    logger.info(f"Failover triggered by {user_email} for instance {instance_id}")

    return result


@router.post("/stop/{instance_id}")
async def stop_spot_monitoring(instance_id: int):
    """
    Para monitoramento de uma instância spot.

    Desabilita failover automático.
    """
    manager = get_spot_manager()
    result = manager.stop(instance_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    return result


@router.delete("/instance/{instance_id}")
async def remove_spot_instance(instance_id: int):
    """
    Remove instância do gerenciamento spot.

    Não destrói a instância, apenas remove do monitoramento.
    """
    manager = get_spot_manager()
    result = manager.remove(instance_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )

    return result


# ============================================================
# PRICING ENDPOINTS
# ============================================================

@router.get("/pricing")
async def get_spot_pricing(
    region: str = Query("global", description="Região (US, EU, ASIA, global)"),
    gpu_name: Optional[str] = Query(None, description="GPU específica"),
    include_all: bool = Query(False, description="Incluir máquinas instáveis (que somem/aparecem frequentemente)"),
    user_email: str = Depends(get_current_user_email),
):
    """
    Retorna preços spot atuais.

    Mostra ofertas disponíveis e economia vs on-demand.
    """
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    manager = get_spot_manager()
    manager.configure(vast_api_key=user.vast_api_key)

    provider = manager._get_provider()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize provider"
        )

    # Buscar ofertas spot
    all_offers = provider.get_interruptible_offers(
        region=region if region != "global" else None,
        gpu_name=gpu_name,
        max_price=10.0,  # Alto para ver tudo
    )

    if not all_offers:
        return {
            "region": region,
            "gpu_name": gpu_name,
            "offers_count": 0,
            "cheapest_price": 0,
            "average_price": 0,
            "savings_vs_ondemand": 0,
            "include_all": include_all,
            "message": "No spot offers available"
        }

    # Filtrar máquinas instáveis (a menos que include_all=True)
    offers = all_offers
    filtered_count = 0

    if not include_all:
        try:
            from ....config.database import SessionLocal
            from ....models.machine_history import OfferStability

            db = SessionLocal()
            try:
                # Buscar máquinas instáveis
                unstable_machines = db.query(OfferStability.machine_id).filter(
                    OfferStability.provider == "vast",
                    OfferStability.is_unstable == True,
                ).all()
                unstable_ids = {str(m.machine_id) for m in unstable_machines}

                # Filtrar ofertas
                stable_offers = [
                    o for o in all_offers
                    if str(getattr(o, 'machine_id', '')) not in unstable_ids
                ]

                filtered_count = len(all_offers) - len(stable_offers)
                if stable_offers:
                    offers = stable_offers
                # Se todas foram filtradas, mostra as originais com aviso

            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not filter unstable machines: {e}")
            # Continua com todas as ofertas se houver erro

    prices = [o.min_bid or o.dph_total for o in offers if o.min_bid or o.dph_total]
    cheapest = min(prices) if prices else 0
    average = sum(prices) / len(prices) if prices else 0

    # Estimativa de economia (spot ~30-40% do on-demand)
    ondemand_estimate = average * 2.5
    savings = ((ondemand_estimate - average) / ondemand_estimate * 100) if ondemand_estimate > 0 else 0

    result = {
        "region": region,
        "gpu_name": gpu_name,
        "offers_count": len(offers),
        "total_offers": len(all_offers),
        "filtered_unstable": filtered_count,
        "include_all": include_all,
        "cheapest_price": round(cheapest, 4),
        "average_price": round(average, 4),
        "estimated_ondemand": round(ondemand_estimate, 4),
        "savings_vs_ondemand": round(savings, 1),
        "top_offers": [
            {
                "gpu_name": o.gpu_name,
                "min_bid": o.min_bid,
                "region": o.geolocation,
                "inet_down": o.inet_down,
                "machine_id": getattr(o, 'machine_id', None),
            }
            for o in offers[:10]
        ]
    }

    if filtered_count > 0 and not include_all:
        result["note"] = f"{filtered_count} máquinas instáveis filtradas. Use include_all=true para ver todas."

    return result


@router.get("/comparison")
async def compare_modes():
    """
    Compara custos entre modos: on-demand, economic, spot.

    Baseado em uso estimado de 4h/dia de GPU ativa.
    """
    # Estimativas baseadas em GPU média $0.30/hr
    gpu_hourly = 0.30
    spot_hourly = 0.10  # ~70% mais barato
    hours_per_day_active = 4
    hours_per_day_idle = 20
    days_per_month = 30

    # Custo 24/7 on-demand
    cost_ondemand = gpu_hourly * 24 * days_per_month

    # Modo economic (pause/resume)
    storage_hourly = 0.005
    cost_economic = (gpu_hourly * hours_per_day_active + storage_hourly * hours_per_day_idle) * days_per_month

    # Modo spot
    cost_spot = (spot_hourly * hours_per_day_active + storage_hourly * hours_per_day_idle) * days_per_month

    return {
        "assumptions": {
            "gpu_hourly_rate_usd": gpu_hourly,
            "spot_hourly_rate_usd": spot_hourly,
            "active_hours_per_day": hours_per_day_active,
            "idle_hours_per_day": hours_per_day_idle,
            "days_per_month": days_per_month,
        },
        "monthly_costs": {
            "on_demand": {
                "cost_usd": round(cost_ondemand, 2),
                "description": "GPU ligada 24/7",
            },
            "economic": {
                "cost_usd": round(cost_economic, 2),
                "savings_usd": round(cost_ondemand - cost_economic, 2),
                "savings_percent": round((1 - cost_economic/cost_ondemand) * 100, 1),
                "description": "Pause/resume quando idle",
                "recovery_time": "~7 segundos",
            },
            "spot": {
                "cost_usd": round(cost_spot, 2),
                "savings_usd": round(cost_ondemand - cost_spot, 2),
                "savings_percent": round((1 - cost_spot/cost_ondemand) * 100, 1),
                "description": "Spot com failover automático",
                "recovery_time": "~30 segundos",
                "risk": "Pode ser interrompido",
            },
        },
        "recommendation": "spot",
        "note": "Spot é ideal para workloads tolerantes a interrupções (batch, training, dev).",
    }
