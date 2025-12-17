"""
Instance management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from ..schemas.request import SearchOffersRequest, CreateInstanceRequest
from ..schemas.response import (
    SearchOffersResponse,
    GpuOfferResponse,
    ListInstancesResponse,
    InstanceResponse,
    SuccessResponse,
)
from ....domain.services import InstanceService
from ....core.exceptions import NotFoundException, VastAPIException
from ..dependencies import get_instance_service, require_auth

router = APIRouter(prefix="/instances", tags=["Instances"], dependencies=[Depends(require_auth)])


@router.get("/offers", response_model=SearchOffersResponse)
async def search_offers(
    gpu_name: Optional[str] = Query(None),
    max_price: float = Query(1.0),
    region: Optional[str] = Query(None),
    min_disk: float = Query(50),
    limit: int = Query(50, le=100),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Search available GPU offers

    Returns list of available GPU instances matching filters.
    """
    offers = instance_service.search_offers(
        gpu_name=gpu_name,
        max_price=max_price,
        region=region,
        min_disk=min_disk,
        limit=limit,
    )

    offer_responses = [
        GpuOfferResponse(
            id=offer.id,
            gpu_name=offer.gpu_name,
            num_gpus=offer.num_gpus,
            gpu_ram=offer.gpu_ram,
            cpu_cores=offer.cpu_cores,
            cpu_ram=offer.cpu_ram,
            disk_space=offer.disk_space,
            inet_down=offer.inet_down,
            inet_up=offer.inet_up,
            dph_total=offer.dph_total,
            geolocation=offer.geolocation,
            reliability=offer.reliability,
            cuda_version=offer.cuda_version,
            verified=offer.verified,
            static_ip=offer.static_ip,
        )
        for offer in offers
    ]

    return SearchOffersResponse(offers=offer_responses, count=len(offer_responses))


@router.get("", response_model=ListInstancesResponse)
async def list_instances(
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    List all user instances

    Returns all GPU instances owned by the user.
    """
    instances = instance_service.list_instances()

    instance_responses = [
        InstanceResponse(
            id=inst.id,
            status=inst.status,
            actual_status=inst.actual_status,
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
        )
        for inst in instances
    ]

    return ListInstancesResponse(instances=instance_responses, count=len(instance_responses))


@router.post("", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    request: CreateInstanceRequest,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Create a new GPU instance

    Creates instance from a GPU offer.
    """
    try:
        instance = instance_service.create_instance(
            offer_id=request.offer_id,
            image=request.image,
            disk_size=request.disk_size,
            label=request.label,
            ports=request.ports,
        )

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
            label=instance.label,
            ports=instance.ports,
        )
    except VastAPIException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Get instance details

    Returns detailed information about a specific instance.
    """
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
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Destroy an instance

    Permanently deletes a GPU instance.
    """
    success = instance_service.destroy_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to destroy instance {instance_id}",
        )

    return SuccessResponse(
        success=True,
        message=f"Instance {instance_id} destroyed successfully",
    )


@router.post("/{instance_id}/pause", response_model=SuccessResponse)
async def pause_instance(
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Pause an instance

    Pauses a running instance without destroying it.
    """
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
    instance_id: int,
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Resume a paused instance

    Resumes a previously paused instance.
    """
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
