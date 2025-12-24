"""
Jobs API Endpoints - GPU Jobs (Execute and Destroy)

Jobs are one-time GPU tasks that:
1. Provision a GPU
2. Download from HuggingFace (or run command)
3. Execute the task
4. DESTROY the GPU (no hibernation)
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..dependencies import get_current_user_email, get_job_manager
from src.domain.models.job import Job, JobConfig, JobStatus, JobSource
from src.services.job import JobManager

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CreateJobRequest(BaseModel):
    """Create a new GPU job"""
    name: str = Field(..., min_length=1, max_length=100, description="Job name")

    # Source type
    source: str = Field("command", description="Source type: command, huggingface, git")

    # Command to execute
    command: Optional[str] = Field(None, description="Command to execute")

    # Hugging Face options
    hf_repo: Optional[str] = Field(None, description="Hugging Face repo (e.g., 'unsloth/llama-3-8b-Instruct')")
    hf_revision: Optional[str] = Field(None, description="HF branch/tag/commit")
    hf_token: Optional[str] = Field(None, description="HF token for private repos")

    # Git options
    git_url: Optional[str] = Field(None, description="Git clone URL")
    git_branch: Optional[str] = Field(None, description="Git branch")

    # Setup
    setup_script: Optional[str] = Field(None, description="Setup script to run before command")
    pip_packages: Optional[List[str]] = Field(default_factory=list, description="Pip packages to install")

    # GPU requirements
    gpu_type: str = Field("RTX 4090", description="GPU type")
    num_gpus: int = Field(1, ge=1, le=8, description="Number of GPUs")
    use_spot: bool = Field(True, description="Use spot instance (cheaper but can be preempted). False = on-demand (stable)")

    # Execution
    disk_size: float = Field(50, ge=10, description="Disk size (GB)")
    timeout_minutes: int = Field(480, ge=10, le=1440, description="Max runtime (10 min to 24h)")
    image: str = Field("pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime", description="Docker image")

    # Output
    output_paths: Optional[List[str]] = Field(default_factory=lambda: ["/workspace/output"], description="Paths to save")
    save_logs: bool = Field(True, description="Save job logs")


class JobResponse(BaseModel):
    """Job response"""
    id: str
    name: str
    status: str
    source: str
    gpu_type: str
    instance_id: Optional[int] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration: Optional[str] = None
    total_cost: float = 0.0
    gpu_hours: float = 0.0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """List of jobs response"""
    jobs: List[JobResponse]
    total: int


class JobLogsResponse(BaseModel):
    """Job logs response"""
    job_id: str
    logs: str


# ============================================================================
# Helper Functions
# ============================================================================

def job_to_response(job: Job) -> JobResponse:
    """Convert Job model to response"""
    return JobResponse(
        id=job.id,
        name=job.config.name,
        status=job.status.value,
        source=job.config.source.value,
        gpu_type=job.config.gpu_type,
        instance_id=job.instance_id,
        ssh_host=job.ssh_host,
        ssh_port=job.ssh_port,
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        duration=job.duration_formatted,
        total_cost=job.total_cost,
        gpu_hours=job.gpu_hours,
        error_message=job.error_message,
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: CreateJobRequest,
    user_email: str = Depends(get_current_user_email),
    job_manager: JobManager = Depends(get_job_manager),
):
    """
    Create a new GPU job.

    The job will:
    1. Provision a GPU instance
    2. Setup environment (HF repo, git, packages)
    3. Execute the command
    4. Monitor completion
    5. **DESTROY** the GPU when done

    Different from serverless which hibernates for reuse.
    """
    try:
        # Build JobConfig
        config = JobConfig(
            name=request.name,
            source=JobSource(request.source),
            command=request.command or "",
            hf_repo=request.hf_repo,
            hf_revision=request.hf_revision,
            hf_token=request.hf_token,
            git_url=request.git_url,
            git_branch=request.git_branch,
            setup_script=request.setup_script,
            pip_packages=request.pip_packages or [],
            gpu_type=request.gpu_type,
            num_gpus=request.num_gpus,
            use_spot=request.use_spot,
            disk_size=request.disk_size,
            timeout_minutes=request.timeout_minutes,
            image=request.image,
            output_paths=request.output_paths or ["/workspace/output"],
            save_logs=request.save_logs,
        )

        # Create job
        job = job_manager.create_job(config, user_email)

        return job_to_response(job)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=100, description="Max jobs to return"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    user_email: str = Depends(get_current_user_email),
    job_manager: JobManager = Depends(get_job_manager),
):
    """
    List jobs for current user.

    Optionally filter by status: pending, provisioning, running, completed, failed, cancelled
    """
    jobs = job_manager.list_jobs(user_id=user_email, limit=limit)

    # Filter by status if provided
    if status_filter:
        try:
            filter_status = JobStatus(status_filter)
            jobs = [j for j in jobs if j.status == filter_status]
        except ValueError:
            pass

    return JobListResponse(
        jobs=[job_to_response(j) for j in jobs],
        total=len(jobs)
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    user_email: str = Depends(get_current_user_email),
    job_manager: JobManager = Depends(get_job_manager),
):
    """Get job details by ID"""
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Check ownership
    if job.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return job_to_response(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    user_email: str = Depends(get_current_user_email),
    job_manager: JobManager = Depends(get_job_manager),
):
    """
    Cancel a running job.

    This will immediately destroy the GPU instance.
    """
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if job.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if job.is_finished:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is already finished"
        )

    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )

    return job_to_response(job)


@router.get("/{job_id}/logs", response_model=JobLogsResponse)
async def get_job_logs(
    job_id: str,
    user_email: str = Depends(get_current_user_email),
    job_manager: JobManager = Depends(get_job_manager),
):
    """Get logs for a job"""
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if job.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    logs = job_manager.get_job_logs(job_id) or ""

    return JobLogsResponse(
        job_id=job_id,
        logs=logs
    )
