"""
CPU Standby management API endpoints
"""
import logging
import time
import uuid
import json
import asyncio
import subprocess
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum

from ..dependencies import require_auth, get_current_user_email
from ....services.standby.manager import get_standby_manager
from ....services.standby.failover import FailoverService
from ....infrastructure.providers import FileUserRepository
from ....core.config import get_settings
from ....models.instance_status import FailoverTestEvent
from ....config.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FailoverPhase(str, Enum):
    """Phases of failover process"""
    DETECTING = "detecting"
    GPU_LOST = "gpu_lost"
    FAILOVER_TO_CPU = "failover_to_cpu"
    SEARCHING_GPU = "searching_gpu"
    PROVISIONING = "provisioning"
    RESTORING = "restoring"
    COMPLETE = "complete"
    FAILED = "failed"


class FailoverSimulationRequest(BaseModel):
    """Request to simulate failover"""
    reason: str = "spot_interruption"
    simulate_restore: bool = True
    simulate_new_gpu: bool = True


class RealFailoverTestRequest(BaseModel):
    """Request for real failover test with actual B2 snapshots"""
    model: str = "qwen2.5:0.5b"
    test_prompt: str = "Olá, qual é o seu nome?"
    workspace_path: str = "/workspace"
    skip_inference: bool = False
    destroy_original_gpu: bool = False  # Safety: don't destroy unless explicitly requested


class FailoverEvent:
    """Tracks a single failover event"""
    def __init__(self, failover_id: str, gpu_instance_id: int, reason: str):
        self.failover_id = failover_id
        self.gpu_instance_id = gpu_instance_id
        self.reason = reason
        self.phase = FailoverPhase.DETECTING
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.success = False
        self.new_gpu_id: Optional[int] = None
        self.data_restored: bool = False
        self.phase_timings: Dict[str, float] = {}
        self._phase_start: float = time.time()

    def advance_phase(self, new_phase: FailoverPhase):
        """Advance to next phase and record timing"""
        elapsed = time.time() - self._phase_start
        self.phase_timings[self.phase.value] = round(elapsed * 1000)  # ms
        self.phase = new_phase
        self._phase_start = time.time()

        if new_phase == FailoverPhase.COMPLETE:
            self.completed_at = datetime.now()
            self.success = True
        elif new_phase == FailoverPhase.FAILED:
            self.completed_at = datetime.now()
            self.success = False

    def to_dict(self) -> Dict[str, Any]:
        total_time = None
        if self.completed_at:
            total_time = int((self.completed_at - self.started_at).total_seconds() * 1000)

        return {
            "failover_id": self.failover_id,
            "gpu_instance_id": self.gpu_instance_id,
            "reason": self.reason,
            "phase": self.phase.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "new_gpu_id": self.new_gpu_id,
            "data_restored": self.data_restored,
            "phase_timings_ms": self.phase_timings,
            "total_time_ms": total_time,
        }


# In-memory storage for failover events (in production, use persistent storage)
_failover_events: Dict[str, FailoverEvent] = {}
_failover_history: List[Dict[str, Any]] = []

router = APIRouter(prefix="/standby", tags=["Standby"], dependencies=[Depends(require_auth)])


class StandbyConfigRequest(BaseModel):
    """Request to configure auto-standby"""
    enabled: bool = True
    gcp_zone: str = "europe-west1-b"
    gcp_machine_type: str = "e2-medium"
    gcp_disk_size: int = 100
    gcp_spot: bool = True
    sync_interval: int = 30
    auto_failover: bool = True
    auto_recovery: bool = True


class StandbyStatusResponse(BaseModel):
    """Status response for standby system"""
    configured: bool
    auto_standby_enabled: bool
    active_associations: int
    associations: Dict[str, Any]
    config: Dict[str, Any]


class StandbyAssociationResponse(BaseModel):
    """Response for a single standby association"""
    gpu_instance_id: int
    cpu_standby: Dict[str, Any]
    sync_enabled: bool
    state: Optional[str] = None
    sync_count: Optional[int] = None


@router.get("/status", response_model=StandbyStatusResponse)
async def get_standby_status():
    """
    Get status of the CPU standby system.

    Returns information about:
    - Whether auto-standby is configured and enabled
    - Active GPU ↔ CPU associations
    - Current configuration
    """
    manager = get_standby_manager()
    return manager.get_status()


@router.post("/configure")
async def configure_standby(
    request: StandbyConfigRequest,
    user_email: str = Depends(get_current_user_email),
):
    """
    Configure the auto-standby system.

    When enabled, creating a GPU instance will automatically:
    1. Provision a CPU standby VM in GCP
    2. Start syncing data GPU → CPU
    3. Enable automatic failover on GPU failure

    When a GPU is destroyed, its associated CPU standby is also destroyed.

    Requires GCP credentials to be configured in user settings.
    """
    # Get user's settings
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check for GCP credentials
    gcp_creds = user.settings.get("gcp_credentials")
    if not gcp_creds and request.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GCP credentials not configured. Please add gcp_credentials to your settings."
        )

    if not user.vast_api_key and request.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured."
        )

    # Configure the manager
    manager = get_standby_manager()

    if request.enabled:
        manager.configure(
            gcp_credentials=gcp_creds,
            vast_api_key=user.vast_api_key,
            auto_standby_enabled=True,
            config={
                'gcp_zone': request.gcp_zone,
                'gcp_machine_type': request.gcp_machine_type,
                'gcp_disk_size': request.gcp_disk_size,
                'gcp_spot': request.gcp_spot,
                'sync_interval': request.sync_interval,
                'auto_failover': request.auto_failover,
                'auto_recovery': request.auto_recovery,
            }
        )

        logger.info(f"Auto-standby enabled for user {user_email}")

        return {
            "success": True,
            "message": "Auto-standby enabled. New GPU instances will automatically have CPU backup.",
            "config": {
                "gcp_zone": request.gcp_zone,
                "gcp_machine_type": request.gcp_machine_type,
                "estimated_cost_monthly_usd": 7.20 if request.gcp_spot else 25.0,
            }
        }
    else:
        # Disable auto-standby
        manager._auto_standby_enabled = False
        logger.info(f"Auto-standby disabled for user {user_email}")

        return {
            "success": True,
            "message": "Auto-standby disabled. Existing associations will remain active.",
        }


@router.get("/associations")
async def list_associations():
    """
    List all active GPU ↔ CPU standby associations.

    Returns mapping of GPU instance IDs to their CPU standby info.
    """
    manager = get_standby_manager()
    return {
        "associations": manager.list_associations(),
        "count": len(manager._associations),
    }


@router.get("/associations/{gpu_instance_id}")
async def get_association(gpu_instance_id: int):
    """
    Get CPU standby association for a specific GPU.

    Returns details about the associated CPU standby, sync status, etc.
    """
    manager = get_standby_manager()
    association = manager.get_association(gpu_instance_id)

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    return association


@router.post("/associations/{gpu_instance_id}/start-sync")
async def start_sync(gpu_instance_id: int):
    """
    Start synchronization for a GPU ↔ CPU standby pair.

    Begins continuous sync of /workspace from GPU to CPU.
    """
    manager = get_standby_manager()

    if gpu_instance_id not in manager._associations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    success = manager.start_sync(gpu_instance_id)

    if success:
        return {
            "success": True,
            "message": f"Sync started for GPU {gpu_instance_id}",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start sync"
        )


@router.post("/associations/{gpu_instance_id}/stop-sync")
async def stop_sync(gpu_instance_id: int):
    """
    Stop synchronization for a GPU ↔ CPU standby pair.
    """
    manager = get_standby_manager()

    if gpu_instance_id not in manager._associations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    success = manager.stop_sync(gpu_instance_id)

    return {
        "success": True,
        "message": f"Sync stopped for GPU {gpu_instance_id}",
    }


@router.delete("/associations/{gpu_instance_id}")
async def destroy_standby(
    gpu_instance_id: int,
    keep_gpu: bool = Query(True, description="Keep the GPU instance running"),
):
    """
    Destroy the CPU standby for a GPU instance.

    This removes the CPU standby VM and stops sync/failover.
    The GPU instance is kept running by default.
    """
    manager = get_standby_manager()

    if gpu_instance_id not in manager._associations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}"
        )

    success = manager.on_gpu_destroyed(gpu_instance_id)

    if success:
        return {
            "success": True,
            "message": f"CPU standby for GPU {gpu_instance_id} destroyed",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to destroy CPU standby"
        )


@router.get("/pricing")
async def get_pricing(
    machine_type: str = Query("e2-medium", description="GCP machine type"),
    disk_gb: int = Query(100, description="Disk size in GB"),
    spot: bool = Query(True, description="Use Spot VM"),
):
    """
    Get estimated pricing for CPU standby.

    Returns estimated monthly cost for a CPU standby VM.
    """
    # Spot VM prices (approximate)
    spot_prices = {
        "e2-micro": 0.002,
        "e2-small": 0.005,
        "e2-medium": 0.010,
        "e2-standard-2": 0.020,
        "e2-standard-4": 0.040,
    }

    # On-demand prices (approximate)
    ondemand_prices = {
        "e2-micro": 0.008,
        "e2-small": 0.017,
        "e2-medium": 0.034,
        "e2-standard-2": 0.067,
        "e2-standard-4": 0.134,
    }

    prices = spot_prices if spot else ondemand_prices
    hourly = prices.get(machine_type, 0.010)
    monthly_vm = hourly * 720  # ~720 hours/month
    monthly_disk = disk_gb * 0.04  # $0.04/GB for standard disk

    return {
        "machine_type": machine_type,
        "disk_gb": disk_gb,
        "spot": spot,
        "estimated_hourly_usd": round(hourly, 4),
        "estimated_monthly_usd": round(monthly_vm + monthly_disk, 2),
        "breakdown": {
            "vm_monthly": round(monthly_vm, 2),
            "disk_monthly": round(monthly_disk, 2),
        },
        "note": "Prices are estimates and may vary by region."
    }


# ============================================================
# MANUAL PROVISIONING ENDPOINT
# ============================================================

@router.post("/provision/{gpu_instance_id}")
async def provision_cpu_standby(
    gpu_instance_id: int,
    label: Optional[str] = Query(None, description="Label for the CPU standby VM"),
    user_email: str = Depends(get_current_user_email),
):
    """
    Manually provision CPU Standby for an existing GPU instance.

    This endpoint triggers the creation of a CPU Standby VM in GCP
    for a GPU instance that was created before auto-standby was enabled.

    Requires:
    - GCP credentials configured in user settings
    - Auto-standby to be configured via /standby/configure

    Returns the association info if successful.
    """
    manager = get_standby_manager()

    # Check if already has association
    if gpu_instance_id in manager._associations:
        association = manager.get_association(gpu_instance_id)
        return {
            "success": True,
            "message": "CPU Standby already exists for this GPU",
            "association": association,
        }

    # Check if manager is configured
    if not manager.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Standby manager not configured. Call POST /standby/configure first."
        )

    # Trigger provisioning
    try:
        result = manager.on_gpu_created(
            gpu_instance_id=gpu_instance_id,
            label=label or f"gpu-{gpu_instance_id}",
            machine_id=gpu_instance_id,
        )

        if result:
            return {
                "success": True,
                "message": "CPU Standby provisioned successfully",
                "association": result,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to provision CPU Standby. Check GCP credentials and quota."
            )

    except Exception as e:
        logger.error(f"Failed to provision CPU standby for GPU {gpu_instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provisioning failed: {str(e)}"
        )


# ============================================================
# FAILOVER SIMULATION & TESTING ENDPOINTS
# ============================================================

@router.post("/failover/simulate/{gpu_instance_id}")
async def simulate_failover(
    gpu_instance_id: int,
    request: FailoverSimulationRequest = FailoverSimulationRequest(),
):
    """
    Simulate a GPU failover for testing purposes.

    This endpoint simulates a complete failover journey:
    1. GPU Interrompida (GPU Lost) - Detects GPU failure
    2. Failover para CPU Standby - Switches to CPU backup
    3. Buscando Nova GPU - Searches for replacement GPU
    4. Provisionando - Provisions new GPU
    5. Restaurando Dados - Restores data from CPU backup
    6. Recuperação Completa - Failover complete

    Returns a failover_id to track progress.

    Use GET /standby/failover/status/{failover_id} to monitor progress.
    """
    import asyncio

    manager = get_standby_manager()

    # Check if GPU has standby association
    if gpu_instance_id not in manager._associations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standby association for GPU {gpu_instance_id}. Create one first."
        )

    # Create failover event
    failover_id = str(uuid.uuid4())[:8]
    event = FailoverEvent(failover_id, gpu_instance_id, request.reason)
    _failover_events[failover_id] = event

    logger.info(f"Starting failover simulation {failover_id} for GPU {gpu_instance_id}")

    # Run failover simulation in background
    async def run_simulation():
        try:
            # Phase 1: Detecting → GPU Lost
            await asyncio.sleep(0.5)  # Detection delay
            event.advance_phase(FailoverPhase.GPU_LOST)
            logger.info(f"[{failover_id}] Phase 1: GPU Lost detected")

            # Mark GPU as failed in manager
            manager.mark_gpu_failed(gpu_instance_id, request.reason)

            # Phase 2: GPU Lost → Failover to CPU
            await asyncio.sleep(2.0)  # Failover time
            event.advance_phase(FailoverPhase.FAILOVER_TO_CPU)
            logger.info(f"[{failover_id}] Phase 2: Failover to CPU Standby")

            # Phase 3: Failover to CPU → Searching GPU
            await asyncio.sleep(3.0)  # CPU takeover time
            event.advance_phase(FailoverPhase.SEARCHING_GPU)
            logger.info(f"[{failover_id}] Phase 3: Searching for new GPU")

            if request.simulate_new_gpu:
                # Phase 4: Searching → Provisioning
                await asyncio.sleep(3.5)  # Search time
                event.advance_phase(FailoverPhase.PROVISIONING)
                logger.info(f"[{failover_id}] Phase 4: Provisioning new GPU")

                # Simulate new GPU ID
                event.new_gpu_id = gpu_instance_id + 1000

                if request.simulate_restore:
                    # Phase 5: Provisioning → Restoring
                    await asyncio.sleep(3.0)  # Provisioning time
                    event.advance_phase(FailoverPhase.RESTORING)
                    logger.info(f"[{failover_id}] Phase 5: Restoring data to new GPU")

                    # Simulate data restoration
                    await asyncio.sleep(4.0)  # Restore time
                    event.data_restored = True

            # Phase 6: Complete
            event.advance_phase(FailoverPhase.COMPLETE)
            logger.info(f"[{failover_id}] Phase 6: Failover COMPLETE")

            # Record in history
            _failover_history.append(event.to_dict())

        except Exception as e:
            logger.error(f"[{failover_id}] Failover simulation failed: {e}")
            event.advance_phase(FailoverPhase.FAILED)
            _failover_history.append(event.to_dict())

    # Start simulation in background
    asyncio.create_task(run_simulation())

    return {
        "failover_id": failover_id,
        "gpu_instance_id": gpu_instance_id,
        "message": "Failover simulation started. Use GET /standby/failover/status/{failover_id} to monitor.",
        "phase": event.phase.value,
    }


@router.get("/failover/status/{failover_id}")
async def get_failover_status(failover_id: str):
    """
    Get status of an ongoing or completed failover.

    Returns current phase, timings, and result.
    """
    if failover_id not in _failover_events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failover {failover_id} not found"
        )

    event = _failover_events[failover_id]
    return event.to_dict()


@router.get("/failover/report")
async def get_failover_report(
    days: int = Query(30, description="Number of days to include in report"),
):
    """
    Get failover report with metrics.

    Returns:
    - Total failovers
    - Success rate
    - MTTR (Mean Time To Recovery)
    - Latency breakdown by phase
    - Recent failover history
    """
    cutoff = datetime.now() - timedelta(days=days)

    # Filter history by date
    recent = [
        e for e in _failover_history
        if datetime.fromisoformat(e["started_at"]) > cutoff
    ]

    if not recent:
        return {
            "period_days": days,
            "total_failovers": 0,
            "success_rate": 0.0,
            "mttr_ms": 0,
            "mttr_seconds": 0,
            "latency_by_phase_ms": {},
            "history": [],
            "message": "No failover events in the specified period."
        }

    # Calculate metrics
    total = len(recent)
    successful = sum(1 for e in recent if e["success"])
    success_rate = (successful / total) * 100 if total > 0 else 0

    # Calculate MTTR (Mean Time To Recovery)
    completed_times = [e["total_time_ms"] for e in recent if e["total_time_ms"]]
    mttr = sum(completed_times) / len(completed_times) if completed_times else 0

    # Average latency by phase
    phase_totals: Dict[str, List[int]] = {}
    for event in recent:
        for phase, timing in event.get("phase_timings_ms", {}).items():
            if phase not in phase_totals:
                phase_totals[phase] = []
            phase_totals[phase].append(timing)

    avg_by_phase = {
        phase: round(sum(times) / len(times))
        for phase, times in phase_totals.items()
    }

    return {
        "period_days": days,
        "total_failovers": total,
        "successful_failovers": successful,
        "failed_failovers": total - successful,
        "success_rate": round(success_rate, 1),
        "mttr_ms": round(mttr),
        "mttr_seconds": round(mttr / 1000, 2),
        "latency_by_phase_ms": avg_by_phase,
        "data_restored_count": sum(1 for e in recent if e.get("data_restored")),
        "gpus_provisioned_count": sum(1 for e in recent if e.get("new_gpu_id")),
        "primary_cause": max(
            set(e["reason"] for e in recent),
            key=lambda r: sum(1 for e in recent if e["reason"] == r)
        ) if recent else None,
        "history": recent[-10:],  # Last 10 events
    }


@router.get("/failover/active")
async def get_active_failovers():
    """
    Get list of currently active (in-progress) failovers.
    """
    active = [
        event.to_dict()
        for event in _failover_events.values()
        if event.phase not in [FailoverPhase.COMPLETE, FailoverPhase.FAILED]
    ]

    return {
        "active_count": len(active),
        "failovers": active,
    }


@router.post("/test/create-mock-association")
async def create_mock_association(
    gpu_instance_id: int = Query(12345, description="Mock GPU instance ID"),
):
    """
    Create a mock standby association for testing failover.

    This endpoint creates a fake GPU ↔ CPU standby association
    without actually provisioning any resources. Use it to test
    the failover simulation flow.
    """
    from ....services.standby.manager import get_standby_manager, StandbyAssociation

    manager = get_standby_manager()

    # Create mock association
    association = StandbyAssociation(
        gpu_instance_id=gpu_instance_id,
        cpu_instance_name=f"mock-cpu-standby-{gpu_instance_id}",
        cpu_instance_zone="europe-west1-b",
        cpu_instance_ip="10.0.0.100",
        sync_enabled=True,
        created_at=datetime.now().isoformat(),
    )

    manager._associations[gpu_instance_id] = association
    manager._save_associations()

    logger.info(f"Created mock association for GPU {gpu_instance_id}")

    return {
        "success": True,
        "message": f"Mock association created for GPU {gpu_instance_id}",
        "association": {
            "gpu_instance_id": gpu_instance_id,
            "cpu_standby": {
                "name": association.cpu_instance_name,
                "zone": association.cpu_instance_zone,
                "ip": association.cpu_instance_ip,
            },
            "sync_enabled": True,
        },
        "next_step": f"Run: dumont failover simulate {gpu_instance_id}",
    }


# ============================================================
# REAL FAILOVER TEST - With B2 Snapshots
# ============================================================

def _get_vast_instance_info(instance_id: int, vast_api_key: str) -> Dict[str, Any]:
    """Get instance info from Vast.ai API"""
    import requests

    headers = {"Authorization": f"Bearer {vast_api_key}"}
    response = requests.get("https://console.vast.ai/api/v0/instances/", headers=headers)
    response.raise_for_status()

    for instance in response.json().get("instances", []):
        if instance["id"] == instance_id:
            return {
                "id": instance["id"],
                "ssh_host": instance.get("ssh_host"),
                "ssh_port": instance.get("ssh_port"),
                "status": instance.get("actual_status"),
                "gpu_name": instance.get("gpu_name"),
                "dph_total": instance.get("dph_total"),
            }

    raise ValueError(f"Instance {instance_id} not found")


def _run_ssh_command(ssh_host: str, ssh_port: int, command: str, timeout: int = 300) -> Dict[str, Any]:
    """Execute command via SSH"""
    cmd = [
        "ssh",
        "-p", str(ssh_port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=30",
        f"root@{ssh_host}",
        command
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _test_ollama_inference(ssh_host: str, ssh_port: int, model: str, prompt: str) -> Dict[str, Any]:
    """Test Ollama inference on remote GPU"""
    start_time = time.time()

    command = f"""
export OLLAMA_MODELS=/workspace/ollama_models
pgrep ollama || (ollama serve &)
sleep 2
echo '{prompt}' | timeout 60 ollama run {model} 2>/dev/null | head -5
"""

    result = _run_ssh_command(ssh_host, ssh_port, command, timeout=120)
    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "success": result["returncode"] == 0 and len(result["stdout"].strip()) > 0,
        "response": result["stdout"].strip()[:500],
        "error": result["stderr"][:200] if result["returncode"] != 0 else None,
        "time_ms": elapsed_ms,
    }


@router.post("/failover/test-real/{gpu_instance_id}")
async def test_real_failover(
    gpu_instance_id: int,
    request: RealFailoverTestRequest = RealFailoverTestRequest(),
    background_tasks: BackgroundTasks = None,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Execute a REAL failover test with actual B2 snapshots.

    This endpoint performs a complete, realistic failover test:

    1. **Snapshot Creation**: Creates a real snapshot in Backblaze B2
       - Uses LZ4 compression for speed
       - Measures exact creation time
       - Records snapshot size

    2. **GPU Simulation**: Simulates GPU failure (optional destroy)

    3. **GPU Provisioning**: Finds and provisions a new GPU

    4. **Restore**: Restores snapshot from B2 to new GPU
       - Measures download time
       - Measures decompression time

    5. **Inference Test**: Verifies Ollama model works after restore
       - Measures time to first inference

    All metrics are persisted to PostgreSQL for historical analysis.

    **WARNING**: This test will:
    - Create real data in Backblaze B2 (costs apply)
    - Provision a new GPU instance (costs apply)
    - Take several minutes to complete

    Returns failover_id for status tracking via GET /failover/test-real/status/{failover_id}
    """
    import requests

    # Get user settings for API keys
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured in user settings"
        )

    # Verify GPU instance exists and is running
    try:
        instance_info = _get_vast_instance_info(gpu_instance_id, user.vast_api_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GPU instance {gpu_instance_id} not found: {str(e)}"
        )

    if instance_info.get("status") != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GPU instance is not running. Status: {instance_info.get('status')}"
        )

    if not instance_info.get("ssh_host") or not instance_info.get("ssh_port"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPU instance SSH info not available. Wait for instance to be ready."
        )

    # Create failover test record
    failover_id = f"real-{str(uuid.uuid4())[:8]}"

    failover_event = FailoverTestEvent(
        failover_id=failover_id,
        gpu_instance_id=gpu_instance_id,
        user_id=user_email,
        started_at=datetime.utcnow(),
        inference_model=request.model,
        inference_test_prompt=request.test_prompt,
        original_gpu_type=instance_info.get("gpu_name"),
    )
    db.add(failover_event)
    db.commit()

    logger.info(f"Starting REAL failover test {failover_id} for GPU {gpu_instance_id}")

    # Run the test synchronously (it's a long-running operation)
    # In production, this could be moved to a background task

    phase_timings = {}
    total_start = time.time()

    try:
        ssh_host = instance_info["ssh_host"]
        ssh_port = instance_info["ssh_port"]

        # ============================================================
        # PHASE 1: Create Snapshot in Backblaze B2
        # ============================================================
        logger.info(f"[{failover_id}] Phase 1: Creating snapshot in B2...")
        phase_start = time.time()

        from ....services.gpu.snapshot import GPUSnapshotService

        # Get B2 credentials from environment or config
        import os
        b2_endpoint = os.environ.get("B2_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
        b2_bucket = os.environ.get("B2_BUCKET", "dumoncloud-snapshot")

        snapshot_service = GPUSnapshotService(
            r2_endpoint=b2_endpoint,
            r2_bucket=b2_bucket,
            provider="b2"
        )

        snapshot_name = f"failover-test-{failover_id}"

        snapshot_info = snapshot_service.create_snapshot(
            instance_id=str(gpu_instance_id),
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            workspace_path=request.workspace_path,
            snapshot_name=snapshot_name
        )

        phase_timings["snapshot_creation"] = int((time.time() - phase_start) * 1000)

        # Update DB with snapshot info
        failover_event.snapshot_id = snapshot_info.get("snapshot_id")
        failover_event.snapshot_size_bytes = snapshot_info.get("size_compressed", 0)
        failover_event.snapshot_creation_time_ms = phase_timings["snapshot_creation"]
        failover_event.snapshot_files_count = snapshot_info.get("num_chunks", 0)
        db.commit()

        logger.info(f"[{failover_id}] Snapshot created: {snapshot_info.get('snapshot_id')} ({snapshot_info.get('size_compressed', 0)} bytes)")

        # ============================================================
        # PHASE 2: Test inference BEFORE failover (baseline)
        # ============================================================
        if not request.skip_inference:
            logger.info(f"[{failover_id}] Phase 2: Testing inference before failover...")
            phase_start = time.time()

            inference_before = _test_ollama_inference(
                ssh_host, ssh_port, request.model, request.test_prompt
            )

            phase_timings["inference_before"] = inference_before["time_ms"]
            logger.info(f"[{failover_id}] Pre-failover inference: {'SUCCESS' if inference_before['success'] else 'FAILED'}")

        # ============================================================
        # PHASE 3: Simulate GPU failure (optional destroy)
        # ============================================================
        logger.info(f"[{failover_id}] Phase 3: Simulating GPU failure...")
        phase_start = time.time()

        if request.destroy_original_gpu:
            # Actually destroy the GPU instance
            headers = {"Authorization": f"Bearer {user.vast_api_key}"}
            response = requests.delete(
                f"https://console.vast.ai/api/v0/instances/{gpu_instance_id}/",
                headers=headers
            )
            logger.info(f"[{failover_id}] GPU {gpu_instance_id} destroyed")
        else:
            logger.info(f"[{failover_id}] GPU failure simulated (instance kept running for safety)")

        phase_timings["gpu_failure_simulation"] = int((time.time() - phase_start) * 1000)

        # ============================================================
        # PHASE 4: Search and provision new GPU
        # ============================================================
        logger.info(f"[{failover_id}] Phase 4: Searching for new GPU...")
        phase_start = time.time()

        # Search for similar GPU
        headers = {"Authorization": f"Bearer {user.vast_api_key}"}
        search_params = {
            "verified": "true",
            "external": "false",
            "rentable": "true",
            "gpu_ram": "10000",  # At least 10GB VRAM
            "num_gpus": "1",
            "order": "dph_total",  # Cheapest first
            "type": "on-demand",
        }

        response = requests.get(
            "https://console.vast.ai/api/v0/bundles",
            headers=headers,
            params=search_params
        )

        offers = response.json().get("offers", [])[:5]  # Top 5 cheapest

        if not offers:
            raise Exception("No GPU offers available matching criteria")

        phase_timings["gpu_search"] = int((time.time() - phase_start) * 1000)
        failover_event.gpu_search_time_ms = phase_timings["gpu_search"]

        # Provision new GPU - try multiple offers
        logger.info(f"[{failover_id}] Phase 4b: Provisioning new GPU...")
        phase_start = time.time()

        new_instance = None
        last_error = None
        successful_offer = None

        for offer in offers:
            try:
                logger.info(f"[{failover_id}] Trying offer {offer['id']} ({offer.get('gpu_name', 'unknown')})...")
                create_response = requests.put(
                    f"https://console.vast.ai/api/v0/asks/{offer['id']}/",
                    headers=headers,
                    json={
                        "client_id": "me",
                        "image": "nvidia/cuda:12.1.0-runtime-ubuntu22.04",
                        "disk": 50,
                        "onstart": "apt-get update && apt-get install -y python3-pip curl && pip3 install b2sdk lz4",
                    }
                )

                if create_response.status_code in [200, 201]:
                    new_instance = create_response.json()
                    successful_offer = offer
                    break
                else:
                    last_error = create_response.text
                    logger.warning(f"[{failover_id}] Offer {offer['id']} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{failover_id}] Offer {offer['id']} exception: {e}")

        if not new_instance:
            raise Exception(f"Failed to provision GPU after trying {len(offers)} offers. Last error: {last_error}")

        new_gpu_id = new_instance.get("new_contract")

        phase_timings["gpu_provision"] = int((time.time() - phase_start) * 1000)
        failover_event.gpu_provision_time_ms = phase_timings["gpu_provision"]
        failover_event.new_gpu_instance_id = new_gpu_id
        failover_event.new_gpu_type = successful_offer.get("gpu_name") if successful_offer else "unknown"
        db.commit()

        logger.info(f"[{failover_id}] New GPU provisioned: {new_gpu_id}")

        # Wait for new GPU to be ready
        logger.info(f"[{failover_id}] Waiting for new GPU to be ready...")
        phase_start = time.time()

        max_wait = 300  # 5 minutes
        new_ssh_host = None
        new_ssh_port = None

        while time.time() - phase_start < max_wait:
            try:
                new_info = _get_vast_instance_info(new_gpu_id, user.vast_api_key)
                if new_info.get("status") == "running" and new_info.get("ssh_host") and new_info.get("ssh_port"):
                    new_ssh_host = new_info["ssh_host"]
                    new_ssh_port = new_info["ssh_port"]

                    # Test SSH connectivity
                    logger.info(f"[{failover_id}] Testing SSH connectivity to {new_ssh_host}:{new_ssh_port}...")
                    ssh_test = subprocess.run(
                        ["ssh", "-p", str(new_ssh_port), "-o", "StrictHostKeyChecking=no",
                         "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
                         f"root@{new_ssh_host}", "echo ready"],
                        capture_output=True, text=True, timeout=30
                    )
                    if ssh_test.returncode == 0:
                        logger.info(f"[{failover_id}] SSH connectivity confirmed")
                        break
                    else:
                        logger.warning(f"[{failover_id}] SSH not ready yet: {ssh_test.stderr}")
                        new_ssh_host = None
                        new_ssh_port = None
            except Exception as e:
                logger.warning(f"[{failover_id}] Waiting for GPU: {e}")
            await asyncio.sleep(10)

        if not new_ssh_host:
            raise Exception(f"New GPU {new_gpu_id} did not become ready in time")

        phase_timings["gpu_ready_wait"] = int((time.time() - phase_start) * 1000)
        logger.info(f"[{failover_id}] New GPU ready: {new_ssh_host}:{new_ssh_port}")

        # ============================================================
        # PHASE 5: Restore snapshot to new GPU
        # ============================================================
        logger.info(f"[{failover_id}] Phase 5: Restoring snapshot to new GPU...")
        phase_start = time.time()

        restore_info = snapshot_service.restore_snapshot(
            snapshot_id=snapshot_name,
            ssh_host=new_ssh_host,
            ssh_port=new_ssh_port,
            workspace_path=request.workspace_path
        )

        phase_timings["restore"] = int((time.time() - phase_start) * 1000)
        failover_event.restore_time_ms = phase_timings["restore"]
        failover_event.restore_download_time_ms = int(restore_info.get("download_time", 0) * 1000)
        failover_event.restore_decompress_time_ms = int(restore_info.get("decompress_time", 0) * 1000)
        failover_event.data_restored_bytes = snapshot_info.get("size_compressed", 0)
        db.commit()

        logger.info(f"[{failover_id}] Snapshot restored in {phase_timings['restore']}ms")

        # ============================================================
        # PHASE 6: Test inference AFTER restore
        # ============================================================
        if not request.skip_inference:
            logger.info(f"[{failover_id}] Phase 6: Testing inference after restore...")
            phase_start = time.time()

            # First, need to install/start Ollama on new GPU
            install_cmd = """
export OLLAMA_MODELS=/workspace/ollama_models
if ! which ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
ollama serve &
sleep 5
ollama list
"""
            _run_ssh_command(new_ssh_host, new_ssh_port, install_cmd, timeout=180)

            inference_after = _test_ollama_inference(
                new_ssh_host, new_ssh_port, request.model, request.test_prompt
            )

            phase_timings["inference_after"] = inference_after["time_ms"]
            failover_event.inference_ready_time_ms = inference_after["time_ms"]
            failover_event.inference_success = inference_after["success"]
            failover_event.inference_response = inference_after.get("response", "")[:500]

            logger.info(f"[{failover_id}] Post-failover inference: {'SUCCESS' if inference_after['success'] else 'FAILED'}")

        # ============================================================
        # COMPLETE
        # ============================================================
        total_time_ms = int((time.time() - total_start) * 1000)

        failover_event.completed_at = datetime.utcnow()
        failover_event.total_time_ms = total_time_ms
        failover_event.success = True
        failover_event.phase_timings_json = json.dumps(phase_timings)
        db.commit()

        logger.info(f"[{failover_id}] REAL FAILOVER TEST COMPLETE - Total: {total_time_ms}ms")

        return {
            "failover_id": failover_id,
            "success": True,
            "message": "Real failover test completed successfully",
            "total_time_ms": total_time_ms,
            "total_time_seconds": round(total_time_ms / 1000, 2),
            "phase_breakdown": {
                "snapshot_creation_ms": phase_timings.get("snapshot_creation", 0),
                "gpu_search_ms": phase_timings.get("gpu_search", 0),
                "gpu_provision_ms": phase_timings.get("gpu_provision", 0),
                "gpu_ready_wait_ms": phase_timings.get("gpu_ready_wait", 0),
                "restore_ms": phase_timings.get("restore", 0),
                "inference_after_ms": phase_timings.get("inference_after", 0),
            },
            "snapshot": {
                "id": snapshot_info.get("snapshot_id"),
                "size_bytes": snapshot_info.get("size_compressed", 0),
                "size_mb": round(snapshot_info.get("size_compressed", 0) / (1024*1024), 2),
            },
            "gpu": {
                "original_id": gpu_instance_id,
                "original_type": instance_info.get("gpu_name"),
                "new_id": new_gpu_id,
                "new_type": successful_offer.get("gpu_name") if successful_offer else "unknown",
            },
            "inference": {
                "model": request.model,
                "success": failover_event.inference_success if not request.skip_inference else None,
                "response_preview": failover_event.inference_response[:100] if failover_event.inference_response else None,
            },
            "view_report": f"/api/standby/failover/test-real/report/{failover_id}",
        }

    except Exception as e:
        logger.error(f"[{failover_id}] REAL FAILOVER TEST FAILED: {str(e)}")

        total_time_ms = int((time.time() - total_start) * 1000)

        failover_event.completed_at = datetime.utcnow()
        failover_event.total_time_ms = total_time_ms
        failover_event.success = False
        failover_event.failure_reason = str(e)[:500]
        failover_event.phase_timings_json = json.dumps(phase_timings)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "failover_id": failover_id,
                "error": str(e),
                "phase_timings": phase_timings,
                "total_time_ms": total_time_ms,
            }
        )


@router.get("/failover/test-real/report/{failover_id}")
async def get_real_failover_report(
    failover_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed report for a specific real failover test.

    Returns all metrics, timings, and results from the test.
    """
    event = db.query(FailoverTestEvent).filter(
        FailoverTestEvent.failover_id == failover_id
    ).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failover test {failover_id} not found"
        )

    return event.to_dict()


@router.get("/failover/test-real/history")
async def get_real_failover_history(
    days: int = Query(30, description="Number of days to include"),
    limit: int = Query(50, description="Maximum number of results"),
    db: Session = Depends(get_db),
):
    """
    Get history of all real failover tests.

    Returns summary metrics and list of all tests.
    """
    from sqlalchemy import func, desc

    cutoff = datetime.utcnow() - timedelta(days=days)

    events = db.query(FailoverTestEvent).filter(
        FailoverTestEvent.started_at > cutoff
    ).order_by(desc(FailoverTestEvent.started_at)).limit(limit).all()

    if not events:
        return {
            "period_days": days,
            "total_tests": 0,
            "success_rate": 0,
            "mttr_ms": 0,
            "mttr_seconds": 0,
            "tests": [],
        }

    # Calculate metrics
    total = len(events)
    successful = sum(1 for e in events if e.success)
    success_rate = (successful / total) * 100 if total > 0 else 0

    # MTTR
    completed_times = [e.total_time_ms for e in events if e.total_time_ms and e.success]
    mttr = sum(completed_times) / len(completed_times) if completed_times else 0

    # Average by phase
    snapshot_times = [e.snapshot_creation_time_ms for e in events if e.snapshot_creation_time_ms]
    restore_times = [e.restore_time_ms for e in events if e.restore_time_ms]
    inference_times = [e.inference_ready_time_ms for e in events if e.inference_ready_time_ms]

    return {
        "period_days": days,
        "total_tests": total,
        "successful_tests": successful,
        "failed_tests": total - successful,
        "success_rate": round(success_rate, 1),
        "mttr_ms": round(mttr),
        "mttr_seconds": round(mttr / 1000, 2) if mttr else 0,
        "averages": {
            "snapshot_creation_ms": round(sum(snapshot_times) / len(snapshot_times)) if snapshot_times else 0,
            "restore_ms": round(sum(restore_times) / len(restore_times)) if restore_times else 0,
            "inference_ready_ms": round(sum(inference_times) / len(inference_times)) if inference_times else 0,
        },
        "tests": [e.to_dict() for e in events[:10]],  # Last 10
    }


# ============================================================
# NEW: Fast Failover with Race Strategy
# ============================================================

@router.post("/failover/fast/{gpu_instance_id}")
async def fast_failover(
    gpu_instance_id: int,
    request: RealFailoverTestRequest = RealFailoverTestRequest(),
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    """
    Execute fast failover using race strategy.

    This endpoint uses GPUProvisioner with race strategy:
    - Provisions 5 GPUs in parallel per round
    - First GPU to have SSH ready wins
    - Deletes the other 4
    - Up to 4 rounds (20 GPUs total)

    Much faster and more reliable than the standard test-real endpoint.
    """
    import os

    # Get user settings
    settings = get_settings()
    user_repo = FileUserRepository(config_file=settings.app.config_file)
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured"
        )

    # Verify GPU exists
    try:
        instance_info = _get_vast_instance_info(gpu_instance_id, user.vast_api_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GPU {gpu_instance_id} not found: {e}"
        )

    if not instance_info.get("ssh_host") or not instance_info.get("ssh_port"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPU SSH not ready"
        )

    # Create record
    failover_id = f"fast-{str(uuid.uuid4())[:8]}"

    failover_event = FailoverTestEvent(
        failover_id=failover_id,
        gpu_instance_id=gpu_instance_id,
        user_id=user_email,
        started_at=datetime.utcnow(),
        inference_model=request.model,
        inference_test_prompt=request.test_prompt,
        original_gpu_type=instance_info.get("gpu_name"),
    )
    db.add(failover_event)
    db.commit()

    # Execute failover using FailoverService
    try:
        b2_endpoint = os.environ.get("B2_ENDPOINT", "https://s3.us-west-004.backblazeb2.com")
        b2_bucket = os.environ.get("B2_BUCKET", "dumoncloud-snapshot")

        service = FailoverService(
            vast_api_key=user.vast_api_key,
            b2_endpoint=b2_endpoint,
            b2_bucket=b2_bucket,
        )

        result = await service.execute_failover(
            gpu_instance_id=gpu_instance_id,
            ssh_host=instance_info["ssh_host"],
            ssh_port=instance_info["ssh_port"],
            failover_id=failover_id,
            workspace_path=request.workspace_path,
            model=request.model if not request.skip_inference else None,
            test_prompt=request.test_prompt,
        )

        # Update DB with comprehensive metrics
        failover_event.completed_at = datetime.utcnow()
        failover_event.success = result.success
        failover_event.total_time_ms = result.total_ms

        # Snapshot metrics
        failover_event.snapshot_id = result.snapshot_id
        failover_event.snapshot_size_bytes = result.snapshot_size_bytes
        failover_event.snapshot_creation_time_ms = result.snapshot_creation_ms
        failover_event.snapshot_type = result.snapshot_type
        failover_event.base_snapshot_id = result.base_snapshot_id
        failover_event.files_changed = result.files_changed

        # Restore metrics
        failover_event.restore_time_ms = result.restore_ms

        # GPU metrics
        failover_event.original_ssh_host = instance_info["ssh_host"]
        failover_event.original_ssh_port = instance_info["ssh_port"]
        failover_event.new_gpu_instance_id = result.new_gpu_id
        failover_event.new_gpu_type = result.new_gpu_name
        failover_event.gpu_provision_time_ms = result.gpu_provisioning_ms

        # Inference metrics
        failover_event.inference_success = result.inference_success
        failover_event.inference_ready_time_ms = result.inference_test_ms

        # Phase timings and errors
        failover_event.phase_timings_json = json.dumps(result.phase_timings)
        failover_event.failure_reason = result.error

        db.commit()

        if result.success:
            return {
                "failover_id": failover_id,
                "success": True,
                "message": "Fast failover completed!",
                "total_time_ms": result.total_ms,
                "total_time_seconds": round(result.total_ms / 1000, 2),
                "phases": {
                    "snapshot_ms": result.snapshot_creation_ms,
                    "gpu_provisioning_ms": result.gpu_provisioning_ms,
                    "restore_ms": result.restore_ms,
                    "inference_ms": result.inference_test_ms,
                },
                "gpu": {
                    "original": {
                        "id": gpu_instance_id,
                        "type": instance_info.get("gpu_name"),
                    },
                    "new": {
                        "id": result.new_gpu_id,
                        "type": result.new_gpu_name,
                        "ssh": f"{result.new_ssh_host}:{result.new_ssh_port}",
                    },
                },
                "snapshot": {
                    "id": result.snapshot_id,
                    "size_mb": round(result.snapshot_size_bytes / (1024*1024), 2),
                },
                "inference": {
                    "success": result.inference_success,
                    "response": result.inference_response[:100] if result.inference_response else None,
                },
                "stats": {
                    "gpus_tried": result.gpus_tried,
                    "rounds_attempted": result.rounds_attempted,
                },
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "failover_id": failover_id,
                    "error": result.error,
                    "failed_phase": result.failed_phase,
                    "phase_timings": result.phase_timings,
                    "total_time_ms": result.total_ms,
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{failover_id}] Fast failover failed: {e}")

        failover_event.completed_at = datetime.utcnow()
        failover_event.success = False
        failover_event.failure_reason = str(e)[:500]
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"failover_id": failover_id, "error": str(e)}
        )
