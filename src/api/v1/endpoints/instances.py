"""
Instance management API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from typing import Optional
from pydantic import BaseModel

from ..schemas.request import SearchOffersRequest, CreateInstanceRequest, MigrateInstanceRequest, MigrationEstimateRequest

logger = logging.getLogger(__name__)
from ..schemas.response import (
    SearchOffersResponse,
    GpuOfferResponse,
    ListInstancesResponse,
    InstanceResponse,
    SuccessResponse,
    MigrationResponse,
    MigrationEstimateResponse,
    SyncResponse,
    SyncStatusResponse,
)
from ....domain.services import InstanceService, MigrationService, SyncService
from ....core.exceptions import (
    NotFoundException,
    VastAPIException,
    MigrationException,
    InsufficientBalanceException,
    OfferUnavailableException,
    ServiceUnavailableException,
)
from ..dependencies import get_instance_service, get_migration_service, get_sync_service, require_auth, get_current_user_email
from ..dependencies_usage import get_usage_service
from ....services.usage_service import UsageService
from ....services.standby.manager import get_standby_manager
from ....services.machine_history_service import get_machine_history_service

router = APIRouter(prefix="/instances", tags=["Instances"], dependencies=[Depends(require_auth)])


@router.get("/offers", response_model=SearchOffersResponse)
async def search_offers(
    gpu_name: Optional[str] = Query(None, description="Filter by GPU model (e.g., RTX_4090, A100)"),
    num_gpus: int = Query(1, ge=1, le=8, description="Number of GPUs"),
    min_gpu_ram: float = Query(0, description="Minimum GPU RAM in GB"),
    min_cpu_cores: int = Query(1, description="Minimum CPU cores"),
    min_cpu_ram: float = Query(1, description="Minimum CPU RAM in GB"),
    min_disk: float = Query(50, description="Minimum disk space in GB"),
    min_inet_down: float = Query(100, description="Minimum download speed in Mbps"),
    min_inet_up: float = Query(100, description="Minimum upload speed in Mbps"),
    max_price: float = Query(10.0, description="Maximum price per hour in USD"),
    min_reliability: float = Query(0.0, ge=0, le=1, description="Minimum reliability score (0-1)"),
    region: Optional[str] = Query(None, description="Region filter: US, EU, ASIA"),
    verified_only: bool = Query(False, description="Only verified hosts"),
    static_ip: bool = Query(False, description="Require static IP"),
    cuda_version: Optional[str] = Query(None, description="Minimum CUDA version"),
    machine_type: Optional[str] = Query(None, description="Machine type: on-demand, interruptible, or None for all"),
    order_by: str = Query("dph_total", description="Order by field: dph_total, gpu_ram, reliability"),
    limit: int = Query(50, le=100, description="Maximum results"),
    include_blacklisted: bool = Query(False, description="Include blacklisted machines (marked but not filtered)"),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Search available GPU offers with advanced filters

    Returns list of available GPU instances matching filters.
    Supports filtering by GPU specs, network, price, reliability and more.

    Machine history information is included for each offer:
    - is_blacklisted: If machine has been blocked due to failures
    - success_rate: Historical success rate (0-1)
    - reliability_status: excellent, good, fair, poor, unknown
    """
    # Use search_offers_by_type if machine_type is specified
    if machine_type:
        offers = instance_service.search_offers_by_type(
            machine_type=machine_type,
            gpu_name=gpu_name,
            num_gpus=num_gpus,
            min_gpu_ram=min_gpu_ram,
            max_price=max_price,
            region=region,
            min_reliability=min_reliability,
            verified_only=verified_only,
            limit=limit,
        )
    else:
        offers = instance_service.search_offers(
            gpu_name=gpu_name,
            num_gpus=num_gpus,
            min_gpu_ram=min_gpu_ram,
            min_cpu_cores=min_cpu_cores,
            min_cpu_ram=min_cpu_ram,
            max_price=max_price,
            region=region,
            min_disk=min_disk,
            min_inet_down=min_inet_down,
            min_reliability=min_reliability,
            verified_only=verified_only,
            static_ip=static_ip,
            limit=limit,
        )

    # Annotate offers with machine history data
    history_service = get_machine_history_service()
    offer_dicts = [
        {
            "id": offer.id,
            "machine_id": str(offer.machine_id) if hasattr(offer, 'machine_id') else str(offer.id),
            "gpu_name": offer.gpu_name,
            "num_gpus": offer.num_gpus,
            "gpu_ram": offer.gpu_ram,
            "cpu_cores": offer.cpu_cores,
            "cpu_ram": offer.cpu_ram,
            "disk_space": offer.disk_space,
            "inet_down": offer.inet_down,
            "inet_up": offer.inet_up,
            "dph_total": offer.dph_total,
            "geolocation": offer.geolocation,
            "reliability": offer.reliability,
            "cuda_version": offer.cuda_version,
            "verified": offer.verified,
            "static_ip": offer.static_ip,
        }
        for offer in offers
    ]

    # Annotate with machine history (blacklist, success rate, etc)
    annotated_offers = history_service.annotate_offers(offer_dicts, provider="vast")

    # Filter out blacklisted if not including them
    if not include_blacklisted:
        annotated_offers = [o for o in annotated_offers if not o.get("_is_blacklisted", False)]

    offer_responses = [
        GpuOfferResponse(
            id=offer["id"],
            gpu_name=offer["gpu_name"],
            num_gpus=offer["num_gpus"],
            gpu_ram=offer["gpu_ram"],
            cpu_cores=offer["cpu_cores"],
            cpu_ram=offer["cpu_ram"],
            disk_space=offer["disk_space"],
            inet_down=offer["inet_down"],
            inet_up=offer["inet_up"],
            dph_total=offer["dph_total"],
            geolocation=offer.get("geolocation"),
            reliability=offer["reliability"],
            cuda_version=offer.get("cuda_version"),
            verified=offer["verified"],
            static_ip=offer["static_ip"],
            # Machine history fields
            machine_id=offer.get("machine_id"),
            is_blacklisted=offer.get("_is_blacklisted", False),
            blacklist_reason=offer.get("_blacklist_reason"),
            success_rate=offer.get("_success_rate"),
            total_attempts=offer.get("_total_attempts", 0),
            reliability_status=offer.get("_reliability_status"),
        )
        for offer in annotated_offers
    ]

    return SearchOffersResponse(offers=offer_responses, count=len(offer_responses))


@router.get("", response_model=ListInstancesResponse)
async def list_instances(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status: running, stopped, paused"),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    List all user instances

    Returns all GPU instances owned by the user, including CPU standby info if enabled.
    In demo mode, returns sample machines for demonstration.

    Optional filters:
    - status: Filter by instance status (running, stopped, paused)
    """
    from ..schemas.response import CPUStandbyInfo
    from datetime import datetime, timedelta
    from ....core.config import get_settings

    # Check if demo mode
    settings = get_settings()
    demo_param = request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param

    # Demo machines for demonstration
    if is_demo:
        demo_instances = [
            InstanceResponse(
                id=12345678,
                status="running",
                actual_status="running",
                gpu_name="RTX 4090",
                num_gpus=1,
                gpu_ram=24.0,
                cpu_cores=16,
                cpu_ram=64.0,
                disk_space=500.0,
                dph_total=0.45,
                public_ipaddr="203.0.113.45",
                ssh_host="ssh4.vast.ai",
                ssh_port=22345,
                start_date=(datetime.now() - timedelta(hours=3)).isoformat(),
                label="dev-workspace-01",
                ports={"22": 22345, "8080": 8080, "3000": 3000},
                gpu_util=45.2,
                gpu_temp=62.0,
                cpu_util=28.5,
                ram_used=24.3,
                ram_total=64.0,
                provider="vast.ai",
                cpu_standby=None,
                total_dph=0.45,
            ),
            InstanceResponse(
                id=87654321,
                status="stopped",
                actual_status="stopped",
                gpu_name="A100 80GB",
                num_gpus=1,
                gpu_ram=80.0,
                cpu_cores=32,
                cpu_ram=128.0,
                disk_space=1000.0,
                dph_total=1.25,
                public_ipaddr=None,
                ssh_host="ssh7.vast.ai",
                ssh_port=22789,
                start_date=(datetime.now() - timedelta(days=2)).isoformat(),
                label="ml-training-large",
                ports={"22": 22789},
                gpu_util=0.0,
                gpu_temp=0.0,
                cpu_util=0.0,
                ram_used=0.0,
                ram_total=128.0,
                provider="vast.ai",
                cpu_standby=None,
                total_dph=1.25,
            ),
            InstanceResponse(
                id=55555555,
                status="running",
                actual_status="running",
                gpu_name="RTX 3090",
                num_gpus=2,
                gpu_ram=48.0,
                cpu_cores=24,
                cpu_ram=96.0,
                disk_space=250.0,
                dph_total=0.68,
                public_ipaddr="198.51.100.78",
                ssh_host="ssh2.vast.ai",
                ssh_port=22123,
                start_date=(datetime.now() - timedelta(hours=12)).isoformat(),
                label="inference-server",
                ports={"22": 22123, "8000": 8000, "5000": 5000},
                gpu_util=78.3,
                gpu_temp=71.0,
                cpu_util=42.1,
                ram_used=58.7,
                ram_total=96.0,
                provider="vast.ai",
                cpu_standby=CPUStandbyInfo(
                    enabled=True,
                    provider="gcp",
                    name="standby-inference-eu",
                    zone="europe-west1-b",
                    ip="35.204.123.45",
                    machine_type="e2-medium",
                    status="running",
                    dph_total=0.01,
                    sync_enabled=True,
                    sync_count=847,
                    state="syncing",
                ),
                total_dph=0.69,
            ),
        ]
        # Apply status filter to demo instances too
        if status:
            status_lower = status.lower()
            demo_instances = [
                inst for inst in demo_instances
                if inst.status.lower() == status_lower
            ]
        return ListInstancesResponse(instances=demo_instances, count=len(demo_instances))

    instances = instance_service.list_instances()
    standby_manager = get_standby_manager()

    # GCP Spot VM pricing (e2-medium)
    GCP_SPOT_DPH = 0.010  # $0.01/hour for e2-medium spot

    instance_responses = []
    for inst in instances:
        # Check if this GPU has a CPU standby
        cpu_standby_info = None
        total_dph = inst.dph_total

        association = standby_manager.get_association(inst.id)
        if association:
            cpu_standby = association.get('cpu_standby', {})
            cpu_standby_info = CPUStandbyInfo(
                enabled=True,
                provider="gcp",
                name=cpu_standby.get('name'),
                zone=cpu_standby.get('zone'),
                ip=cpu_standby.get('ip'),
                machine_type="e2-medium",
                status="running",
                dph_total=GCP_SPOT_DPH,
                sync_enabled=association.get('sync_enabled', False),
                sync_count=association.get('sync_count', 0),
                state=association.get('state'),
            )
            total_dph = inst.dph_total + GCP_SPOT_DPH

        instance_responses.append(InstanceResponse(
            id=inst.id,
            status=inst.status or "stopped",
            actual_status=inst.actual_status or inst.status or "stopped",
            gpu_name=inst.gpu_name,
            num_gpus=inst.num_gpus,
            gpu_ram=inst.gpu_ram,
            cpu_cores=inst.cpu_cores,
            cpu_ram=inst.cpu_ram,
            disk_space=inst.disk_space,
            dph_total=inst.dph_total,
            public_ipaddr=inst.public_ipaddr,
            ssh_host=inst.ssh_host,
            ssh_port=inst.ssh_port,
            start_date=inst.start_date.isoformat() if inst.start_date else None,
            label=inst.label,
            ports=inst.ports,
            gpu_util=inst.gpu_util,
            gpu_temp=inst.gpu_temp,
            cpu_util=inst.cpu_util,
            ram_used=inst.ram_used,
            ram_total=inst.ram_total,
            provider="vast.ai",
            cpu_standby=cpu_standby_info,
            total_dph=total_dph,
        ))

    # Apply status filter if provided
    if status:
        status_lower = status.lower()
        instance_responses = [
            inst for inst in instance_responses
            if inst.status.lower() == status_lower or inst.actual_status.lower() == status_lower
        ]

    return ListInstancesResponse(instances=instance_responses, count=len(instance_responses))


@router.post("", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    request: CreateInstanceRequest,
    background_tasks: BackgroundTasks,
    instance_service: InstanceService = Depends(get_instance_service),
    usage_service: UsageService = Depends(get_usage_service),
    user_id: str = Depends(get_current_user_email),
):
    """
    Create a new GPU instance

    Creates instance from a GPU offer.
    If auto-standby is enabled, also creates a CPU standby for failover.

    Pré-validações executadas:
    - Verificar conectividade com VAST.ai
    - Verificar saldo suficiente
    - Verificar se oferta ainda está disponível
    """
    # =========================================================================
    # PRÉ-VALIDAÇÕES - Verificar antes de executar (pode ser pulada para testes)
    # =========================================================================
    if not request.skip_validation:
        try:
            validation = instance_service.validate_before_create(request.offer_id)
            if not validation["valid"]:
                errors = "; ".join(validation["errors"])
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Pré-validação falhou: {errors}"
                )

            # Log warnings
            for warning in validation.get("warnings", []):
                logger.warning(f"Create instance warning: {warning}")

        except InsufficientBalanceException as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e)
            )
        except OfferUnavailableException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except ServiceUnavailableException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e)
            )
    else:
        logger.info(f"Skipping pre-validation for offer {request.offer_id} (skip_validation=True)")

    # =========================================================================
    # CRIAR INSTÂNCIA
    # =========================================================================
    try:
        instance = instance_service.create_instance(
            offer_id=request.offer_id,
            image=request.image,
            disk_size=request.disk_size,
            label=request.label,
            ports=request.ports,
            onstart_cmd=request.onstart_cmd,
        )
        logger.info(f"Instance {instance.id} created successfully")

        # Track usage (non-critical, don't fail if this errors)
        try:
            usage_service.start_usage(
                user_id=user_id,
                instance_id=str(instance.id),
                gpu_type=instance.gpu_name
            )
        except Exception as e:
            logger.warning(f"Failed to start usage tracking for {instance.id}: {e}")

        # Auto-create CPU standby in background
        if not request.skip_standby:
            standby_manager = get_standby_manager()
            if standby_manager.is_configured():
                logger.info(f"Scheduling CPU standby creation for GPU {instance.id}")
                background_tasks.add_task(
                    standby_manager.on_gpu_created,
                    gpu_instance_id=instance.id,
                    label=request.label
                )

        return InstanceResponse(
            id=instance.id,
            status=instance.status or "loading",
            actual_status=instance.actual_status or instance.status or "loading",
            gpu_name=instance.gpu_name,
            num_gpus=instance.num_gpus,
            gpu_ram=instance.gpu_ram,
            cpu_cores=instance.cpu_cores,
            cpu_ram=instance.cpu_ram,
            disk_space=instance.disk_space,
            dph_total=instance.dph_total,
            public_ipaddr=instance.public_ipaddr,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            label=instance.label,
            ports=instance.ports or {},
        )
    except VastAPIException as e:
        logger.error(f"VastAPI error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error creating instance: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create instance: {e}")


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    request: Request,
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Get instance details

    Returns detailed information about a specific instance.
    """
    from ..schemas.response import CPUStandbyInfo
    from datetime import datetime, timedelta
    from ....core.config import get_settings

    # Check if demo mode
    settings = get_settings()
    demo_param = request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param

    # Demo instances data
    demo_instances = {
        12345678: InstanceResponse(
            id=12345678,
            status="running",
            actual_status="running",
            gpu_name="RTX 4090",
            num_gpus=1,
            gpu_ram=24.0,
            cpu_cores=16,
            cpu_ram=64.0,
            disk_space=500.0,
            dph_total=0.45,
            public_ipaddr="203.0.113.45",
            ssh_host="ssh4.vast.ai",
            ssh_port=22345,
            start_date=(datetime.now() - timedelta(hours=3)).isoformat(),
            label="dev-workspace-01",
            ports={"22": 22345, "8080": 8080, "3000": 3000},
            gpu_util=45.2,
            gpu_temp=62.0,
            cpu_util=28.5,
            ram_used=24.3,
            ram_total=64.0,
            provider="vast.ai",
            cpu_standby=None,
            total_dph=0.45,
        ),
        87654321: InstanceResponse(
            id=87654321,
            status="stopped",
            actual_status="stopped",
            gpu_name="A100 80GB",
            num_gpus=1,
            gpu_ram=80.0,
            cpu_cores=32,
            cpu_ram=128.0,
            disk_space=1000.0,
            dph_total=1.25,
            public_ipaddr=None,
            ssh_host="ssh7.vast.ai",
            ssh_port=22789,
            start_date=(datetime.now() - timedelta(days=2)).isoformat(),
            label="ml-training-large",
            ports={"22": 22789},
            gpu_util=0.0,
            gpu_temp=0.0,
            cpu_util=0.0,
            ram_used=0.0,
            ram_total=128.0,
            provider="vast.ai",
            cpu_standby=None,
            total_dph=1.25,
        ),
        55555555: InstanceResponse(
            id=55555555,
            status="running",
            actual_status="running",
            gpu_name="RTX 3090",
            num_gpus=2,
            gpu_ram=48.0,
            cpu_cores=24,
            cpu_ram=96.0,
            disk_space=250.0,
            dph_total=0.68,
            public_ipaddr="198.51.100.78",
            ssh_host="ssh2.vast.ai",
            ssh_port=22123,
            start_date=(datetime.now() - timedelta(hours=12)).isoformat(),
            label="inference-server",
            ports={"22": 22123, "8000": 8000, "5000": 5000},
            gpu_util=78.3,
            gpu_temp=71.0,
            cpu_util=42.1,
            ram_used=58.7,
            ram_total=96.0,
            provider="vast.ai",
            cpu_standby=CPUStandbyInfo(
                enabled=True,
                provider="gcp",
                name="standby-inference-eu",
                zone="europe-west1-b",
                ip="35.204.123.45",
                machine_type="e2-medium",
                status="running",
                dph_total=0.01,
                sync_enabled=True,
                sync_count=847,
                state="syncing",
            ),
            total_dph=0.69,
        ),
    }

    if is_demo:
        if instance_id in demo_instances:
            return demo_instances[instance_id]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    try:
        instance = instance_service.get_instance(instance_id)

        return InstanceResponse(
            id=instance.id,
            status=instance.status,
            actual_status=instance.actual_status,
            gpu_name=instance.gpu_name,
            num_gpus=instance.num_gpus,
            gpu_ram=instance.gpu_ram,
            cpu_cores=instance.cpu_cores,
            cpu_ram=instance.cpu_ram,
            disk_space=instance.disk_space,
            dph_total=instance.dph_total,
            public_ipaddr=instance.public_ipaddr,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            start_date=instance.start_date.isoformat() if instance.start_date else None,
            label=instance.label,
            ports=instance.ports,
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{instance_id}", response_model=SuccessResponse)
async def destroy_instance(
    instance_id: int,
    background_tasks: BackgroundTasks,
    destroy_standby: bool = Query(True, description="Also destroy associated CPU standby"),
    reason: str = Query("user_request", description="Reason for destruction: user_request, gpu_failure, spot_interruption"),
    instance_service: InstanceService = Depends(get_instance_service),
    usage_service: UsageService = Depends(get_usage_service),
):
    """
    Destroy an instance
    ...
    If destroy_standby=false, CPU standby is always kept.
    """
    # Finalizar tracking de uso
    usage_service.stop_usage(str(instance_id))

    success = instance_service.destroy_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy instance {instance_id}",
        )

    standby_manager = get_standby_manager()
    association = standby_manager.get_association(instance_id)

    # Lógica de destruição do CPU standby:
    # - Se destroy_standby=false, nunca destrói
    # - Se reason é falha (gpu_failure, spot_interruption), mantém CPU para backup
    # - Se reason=user_request, destrói CPU junto

    should_destroy_cpu = destroy_standby and reason == "user_request"

    if association:
        if should_destroy_cpu:
            logger.info(f"Scheduling CPU standby destruction for GPU {instance_id} (reason={reason})")
            background_tasks.add_task(
                standby_manager.on_gpu_destroyed,
                gpu_instance_id=instance_id
            )
            return SuccessResponse(
                success=True,
                message=f"Instance {instance_id} destroyed. CPU standby also destroyed.",
            )
        else:
            # Mantém CPU standby para backup/restore
            logger.info(f"Keeping CPU standby for GPU {instance_id} (reason={reason}) - useful for backup/restore")
            # Marcar associação como "orphan" (GPU morreu, CPU viva)
            standby_manager.mark_gpu_failed(instance_id, reason=reason)
            return SuccessResponse(
                success=True,
                message=f"Instance {instance_id} destroyed. CPU standby kept for backup/restore (reason: {reason}).",
            )

    return SuccessResponse(
        success=True,
        message=f"Instance {instance_id} destroyed successfully",
    )


@router.post("/{instance_id}/pause", response_model=SuccessResponse)
async def pause_instance(
    request: Request,
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Pause an instance

    Pauses a running instance without destroying it.
    """
    from ....core.config import get_settings

    # Check if demo mode
    settings = get_settings()
    demo_param = request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param

    # Demo mode: simulate pause
    demo_instance_ids = [12345678, 87654321, 55555555]
    if is_demo:
        if instance_id in demo_instance_ids:
            return SuccessResponse(
                success=True,
                message=f"Instance {instance_id} paused successfully (demo mode)",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    # Check if instance exists first
    try:
        instance_service.get_instance(instance_id)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    success = instance_service.pause_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause instance {instance_id}",
        )

    return SuccessResponse(
        success=True,
        message=f"Instance {instance_id} paused successfully",
    )


@router.post("/{instance_id}/resume", response_model=SuccessResponse)
async def resume_instance(
    request: Request,
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Resume a paused instance

    Resumes a previously paused instance.
    """
    from ....core.config import get_settings

    # Check if demo mode
    settings = get_settings()
    demo_param = request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param

    # Demo mode: simulate resume
    demo_instance_ids = [12345678, 87654321, 55555555]
    if is_demo:
        if instance_id in demo_instance_ids:
            return SuccessResponse(
                success=True,
                message=f"Instance {instance_id} resumed successfully (demo mode)",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    # Check if instance exists first
    try:
        instance_service.get_instance(instance_id)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    success = instance_service.resume_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume instance {instance_id}",
        )

    return SuccessResponse(
        success=True,
        message=f"Instance {instance_id} resumed successfully",
    )


class WakeInstanceRequest(BaseModel):
    """Request to wake a hibernated instance"""
    gpu_type: Optional[str] = None
    region: Optional[str] = None
    max_price: float = 1.0
    restore_snapshot: bool = True


class WakeInstanceResponse(BaseModel):
    """Response from wake operation"""
    success: bool
    new_instance_id: Optional[int] = None
    old_instance_id: str
    snapshot_id: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    time_taken: float
    message: str


@router.post("/{instance_id}/wake", response_model=WakeInstanceResponse)
async def wake_instance(
    instance_id: str,
    request: WakeInstanceRequest = None,
    background_tasks: BackgroundTasks = None,
):
    """
    Wake a hibernated instance.
    
    This will:
    1. Find the last snapshot for this instance
    2. Provision a new GPU matching criteria (or similar to original)
    3. Restore the snapshot to the new instance
    4. Return the new instance details
    
    The old instance_id is used to find the snapshot, but a NEW instance ID
    will be returned since we're provisioning a new machine.
    """
    from ....services.standby.hibernation import get_auto_hibernation_manager
    
    if request is None:
        request = WakeInstanceRequest()
    
    manager = get_auto_hibernation_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-hibernation manager not initialized. Configure it in settings first."
        )
    
    try:
        result = manager.wake_instance(
            instance_id=instance_id,
            gpu_type=request.gpu_type,
            region=request.region,
            max_price=request.max_price
        )
        
        return WakeInstanceResponse(
            success=result.get("success", False),
            new_instance_id=result.get("new_instance_id"),
            old_instance_id=instance_id,
            snapshot_id=result.get("snapshot_id"),
            ssh_host=result.get("ssh_host"),
            ssh_port=result.get("ssh_port"),
            time_taken=result.get("time_taken", 0),
            message=result.get("message", "Instance woken successfully")
        )
        
    except Exception as e:
        logger.error(f"Failed to wake instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{instance_id}/migrate", response_model=MigrationResponse)
async def migrate_instance(
    instance_id: int,
    request: MigrateInstanceRequest,
    migration_service: MigrationService = Depends(get_migration_service),
):
    """
    Migrate instance between GPU and CPU

    Migrates an instance from GPU to CPU or vice-versa.
    Creates a snapshot, provisions new instance, restores snapshot,
    and optionally destroys the source instance.
    """
    # Validate target_type
    if request.target_type not in ["gpu", "cpu"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type must be 'gpu' or 'cpu'",
        )

    # Validate gpu_name for GPU migration
    if request.target_type == "gpu" and not request.gpu_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gpu_name is required for GPU migration",
        )

    try:
        result = migration_service.migrate_instance(
            source_instance_id=instance_id,
            target_type=request.target_type,
            gpu_name=request.gpu_name,
            max_price=request.max_price,
            region=request.region,
            disk_size=request.disk_size,
            auto_destroy_source=request.auto_destroy_source,
        )

        return MigrationResponse(
            success=result.success,
            new_instance_id=result.new_instance_id,
            old_instance_id=result.old_instance_id,
            snapshot_id=result.snapshot_id,
            error=result.error,
            steps_completed=result.steps_completed,
        )

    except MigrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{instance_id}/migrate/estimate", response_model=MigrationEstimateResponse)
async def estimate_migration(
    instance_id: int,
    request: MigrationEstimateRequest,
    migration_service: MigrationService = Depends(get_migration_service),
):
    """
    Get migration estimate

    Returns estimated cost and availability for migrating an instance.
    """
    # Validate target_type
    if request.target_type not in ["gpu", "cpu"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type must be 'gpu' or 'cpu'",
        )

    estimate = migration_service.get_migration_estimate(
        source_instance_id=instance_id,
        target_type=request.target_type,
        gpu_name=request.gpu_name,
        max_price=request.max_price,
        region=request.region,
    )

    return MigrationEstimateResponse(**estimate)


@router.post("/{instance_id}/sync", response_model=SyncResponse)
async def sync_instance(
    instance_id: int,
    force: bool = Query(False, description="Force sync even if recently synced"),
    source_path: str = Query("/workspace", description="Path to sync"),
    sync_service: SyncService = Depends(get_sync_service),
):
    """
    Perform incremental sync for an instance

    Uses Restic's deduplication to only upload changed data.
    After first sync, subsequent syncs are typically 10-100x faster.

    Returns detailed statistics about what was synced.
    """
    result = sync_service.sync_instance(
        instance_id=instance_id,
        source_path=source_path,
        force=force,
    )

    # Format data_added for human readability
    data_added = sync_service._format_bytes(result.data_added_bytes)

    return SyncResponse(
        success=result.success,
        instance_id=result.instance_id,
        snapshot_id=result.snapshot_id,
        files_new=result.files_new,
        files_changed=result.files_changed,
        files_unmodified=result.files_unmodified,
        data_added=data_added,
        data_added_bytes=result.data_added_bytes,
        duration_seconds=result.duration_seconds,
        is_incremental=result.is_incremental,
        error=result.error,
    )


@router.get("/{instance_id}/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    instance_id: int,
    sync_service: SyncService = Depends(get_sync_service),
):
    """
    Get sync status for an instance

    Returns information about last sync, current sync state,
    and statistics from the most recent sync operation.
    """
    stats = sync_service.get_sync_stats(instance_id)

    return SyncStatusResponse(
        instance_id=stats["instance_id"],
        synced=stats["synced"],
        is_syncing=stats.get("is_syncing", False),
        last_sync=stats.get("last_sync"),
        last_sync_ago=stats.get("last_sync_ago", "Never"),
        last_snapshot_id=stats.get("last_snapshot_id"),
        sync_count=stats.get("sync_count", 0),
        last_stats=stats.get("last_stats"),
        error=stats.get("error"),
    )


# =============================================================================
# ALIAS ENDPOINTS - Serverless (alternate path)
# =============================================================================

class ServerlessEnableRequest(BaseModel):
    """Request to enable serverless mode"""
    mode: str = "economic"
    idle_timeout_seconds: int = 10
    idle_threshold: int = 60  # Alias for gpu_threshold
    gpu_threshold: float = 5.0
    keep_warm: bool = False
    cpu_standby: bool = False  # Alias for mode=fast


@router.post("/{instance_id}/serverless/enable")
async def enable_serverless_alias(
    instance_id: int,
    request: ServerlessEnableRequest = ServerlessEnableRequest(),
    user_email: str = Depends(get_current_user_email),
):
    """
    Enable serverless mode for an instance (alias for /serverless/enable/{id})
    """
    from ....modules.serverless import get_serverless_manager
    from ....infrastructure.providers import FileUserRepository
    from ....core.config import get_settings

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

    # Handle mode aliases
    mode = request.mode
    if request.cpu_standby:
        mode = "fast"

    result = manager.enable(
        instance_id=instance_id,
        mode=mode,
        idle_timeout_seconds=request.idle_timeout_seconds or request.idle_threshold,
        gpu_threshold=request.gpu_threshold,
        keep_warm=request.keep_warm,
    )

    return {
        **result,
        "message": f"Serverless mode '{mode}' enabled for instance {instance_id}",
    }


@router.post("/{instance_id}/serverless/disable")
async def disable_serverless_alias(
    instance_id: int,
    user_email: str = Depends(get_current_user_email),
):
    """
    Disable serverless mode for an instance (alias for /serverless/disable/{id})
    """
    from ....modules.serverless import get_serverless_manager
    from ....infrastructure.providers import FileUserRepository
    from ....core.config import get_settings

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

    return {
        **result,
        "message": f"Serverless disabled for instance {instance_id}"
    }


# =============================================================================
# ALIAS ENDPOINTS - Snapshots (alternate path)
# =============================================================================

class CreateInstanceSnapshotRequest(BaseModel):
    """Request to create snapshot from instance"""
    name: Optional[str] = None
    type: str = "full"  # full or incremental
    source_path: str = "/workspace"
    tags: Optional[list] = None


@router.post("/{instance_id}/snapshots", status_code=status.HTTP_201_CREATED)
async def create_instance_snapshot(
    instance_id: int,
    request: CreateInstanceSnapshotRequest = CreateInstanceSnapshotRequest(),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Create a snapshot from an instance (alias for /snapshots)
    """
    from ....domain.services import SnapshotService
    from ..dependencies import get_snapshot_service

    try:
        instance = instance_service.get_instance(instance_id)

        if not instance.ssh_host or not instance.ssh_port:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {instance_id} SSH details not available",
            )

        snapshot_service = get_snapshot_service()

        tags = request.tags or []
        if request.name:
            tags.append(f"name:{request.name}")
        tags.append(f"instance:{instance_id}")
        tags.append(f"type:{request.type}")

        result = snapshot_service.create_snapshot(
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            source_path=request.source_path,
            tags=tags,
        )

        return {
            "success": True,
            "snapshot_id": result["snapshot_id"],
            "instance_id": instance_id,
            "type": request.type,
            "files_new": result.get("files_new", 0),
            "files_changed": result.get("files_changed", 0),
            "data_added": result.get("data_added", "0 B"),
        }

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create snapshot for instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{instance_id}/metrics")
async def get_instance_metrics(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Get metrics for an instance (GPU utilization, memory, etc.)
    """
    try:
        instance = instance_service.get_instance(instance_id)

        return {
            "instance_id": instance_id,
            "gpu_util": instance.gpu_util or 0.0,
            "gpu_temp": instance.gpu_temp or 0.0,
            "cpu_util": instance.cpu_util or 0.0,
            "ram_used": instance.ram_used or 0.0,
            "ram_total": instance.ram_total or 0.0,
            "status": instance.status,
        }
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{instance_id}/health")
async def get_instance_health(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Get health status for an instance
    """
    try:
        instance = instance_service.get_instance(instance_id)

        is_healthy = instance.status == "running"

        return {
            "instance_id": instance_id,
            "healthy": is_healthy,
            "status": instance.status,
            "gpu_name": instance.gpu_name,
            "ssh_available": bool(instance.ssh_host and instance.ssh_port),
        }
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
