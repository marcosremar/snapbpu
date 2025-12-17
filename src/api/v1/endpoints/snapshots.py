"""
Snapshot management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas.request import CreateSnapshotRequest, RestoreSnapshotRequest, DeleteSnapshotRequest
from ..schemas.response import (
    ListSnapshotsResponse,
    SnapshotResponse,
    CreateSnapshotResponse,
    RestoreSnapshotResponse,
    SuccessResponse,
)
from ....domain.services import SnapshotService, InstanceService
from ....core.exceptions import SnapshotException, NotFoundException
from ..dependencies import get_snapshot_service, get_instance_service, require_auth

router = APIRouter(prefix="/snapshots", tags=["Snapshots"], dependencies=[Depends(require_auth)])


@router.get("", response_model=ListSnapshotsResponse)
async def list_snapshots(
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
):
    """
    List all snapshots

    Returns list of all backups in the repository.
    """
    snapshots = snapshot_service.list_snapshots()

    snapshot_responses = [
        SnapshotResponse(
            id=snap["id"],
            short_id=snap["short_id"],
            time=snap["time"],
            hostname=snap["hostname"],
            tags=snap["tags"],
            paths=snap["paths"],
        )
        for snap in snapshots
    ]

    return ListSnapshotsResponse(snapshots=snapshot_responses, count=len(snapshot_responses))


@router.post("", response_model=CreateSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    request: CreateSnapshotRequest,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Create a new snapshot

    Creates a backup of the specified instance.
    """
    try:
        # Get instance details
        instance = instance_service.get_instance(request.instance_id)

        if not instance.is_running:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {request.instance_id} is not running",
            )

        if not instance.ssh_host or not instance.ssh_port:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {request.instance_id} SSH details not available",
            )

        # Create snapshot
        result = snapshot_service.create_snapshot(
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            source_path=request.source_path,
            tags=request.tags,
        )

        return CreateSnapshotResponse(
            success=True,
            snapshot_id=result["snapshot_id"],
            files_new=result["files_new"],
            files_changed=result["files_changed"],
            files_unmodified=result["files_unmodified"],
            total_files_processed=result["total_files_processed"],
            data_added=result["data_added"],
            total_bytes_processed=result["total_bytes_processed"],
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SnapshotException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/restore", response_model=RestoreSnapshotResponse)
async def restore_snapshot(
    request: RestoreSnapshotRequest,
    instance_id: int,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    instance_service: InstanceService = Depends(get_instance_service),
):
    """
    Restore a snapshot

    Restores a backup to the specified instance.
    """
    try:
        # Get instance details
        instance = instance_service.get_instance(instance_id)

        if not instance.is_running:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {instance_id} is not running",
            )

        if not instance.ssh_host or not instance.ssh_port:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance {instance_id} SSH details not available",
            )

        # Restore snapshot
        result = snapshot_service.restore_snapshot(
            snapshot_id=request.snapshot_id,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            target_path=request.target_path,
            verify=request.verify,
        )

        return RestoreSnapshotResponse(
            success=result["success"],
            snapshot_id=result["snapshot_id"],
            target_path=result["target_path"],
            files_restored=result["files_restored"],
            errors=result["errors"],
        )

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except SnapshotException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{snapshot_id}", response_model=SuccessResponse)
async def delete_snapshot(
    snapshot_id: str,
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
):
    """
    Delete a snapshot

    Permanently deletes a backup.
    """
    success = snapshot_service.delete_snapshot(snapshot_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete snapshot {snapshot_id}",
        )

    return SuccessResponse(
        success=True,
        message=f"Snapshot {snapshot_id} deleted successfully",
    )
