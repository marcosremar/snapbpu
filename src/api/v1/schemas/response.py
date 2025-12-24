"""
API Response Schemas (Pydantic models)
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# Generic Responses

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Success message")


class ErrorResponse(BaseModel):
    """Generic error response"""
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


# Auth Responses

class LoginResponse(BaseModel):
    """Login response"""
    success: bool = Field(True, description="Login success")
    user: str = Field(..., description="User email")
    token: Optional[str] = Field(None, description="Session token")


class AuthMeResponse(BaseModel):
    """Auth me response"""
    authenticated: bool = Field(..., description="Authentication status")
    user: Optional[Dict[str, Any]] = Field(None, description="User data if authenticated")


# GPU Offer Responses

class GpuOfferResponse(BaseModel):
    """GPU offer response"""
    id: int
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    inet_down: float
    inet_up: float
    dph_total: float
    geolocation: Optional[str] = None
    reliability: float
    cuda_version: Optional[str] = None
    verified: bool
    static_ip: bool

    # Machine History fields (from blacklist/history system)
    machine_id: Optional[str] = None
    is_blacklisted: bool = False
    blacklist_reason: Optional[str] = None
    success_rate: Optional[float] = None  # 0.0 to 1.0
    total_attempts: int = 0
    reliability_status: Optional[str] = None  # excellent, good, fair, poor, unknown

    @field_validator('cuda_version', mode='before')
    @classmethod
    def convert_cuda_version(cls, v):
        """Convert cuda_version to string if it's a float"""
        if v is None:
            return "0.0"
        return str(v)


class SearchOffersResponse(BaseModel):
    """Search offers response"""
    offers: List[GpuOfferResponse]
    count: int = Field(..., description="Number of offers found")


# CPU Standby Info

class CPUStandbyInfo(BaseModel):
    """CPU Standby information"""
    enabled: bool = False
    provider: str = "gcp"  # gcp, aws, etc
    name: Optional[str] = None
    zone: Optional[str] = None
    ip: Optional[str] = None
    machine_type: Optional[str] = None
    status: Optional[str] = None  # running, stopped, etc
    dph_total: float = 0.0  # Cost per hour
    sync_enabled: bool = False
    sync_count: int = 0
    state: Optional[str] = None  # syncing, ready, failover_active


# Instance Responses

class InstanceResponse(BaseModel):
    """Instance response"""
    id: int
    status: str
    actual_status: str
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    dph_total: float
    public_ipaddr: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    start_date: Optional[str] = None
    label: Optional[str] = None
    ports: Optional[Dict[str, Any]] = None

    # Real-time metrics
    gpu_util: Optional[float] = None
    gpu_temp: Optional[float] = None
    cpu_util: Optional[float] = None
    ram_used: Optional[float] = None
    ram_total: Optional[float] = None

    # Provider info
    provider: str = "vast.ai"

    # CPU Standby info (for failover)
    cpu_standby: Optional[CPUStandbyInfo] = None

    # Combined cost (GPU + CPU standby)
    total_dph: Optional[float] = None


class ListInstancesResponse(BaseModel):
    """List instances response"""
    instances: List[InstanceResponse]
    count: int = Field(..., description="Number of instances")


# Snapshot Responses

class SnapshotResponse(BaseModel):
    """Snapshot response"""
    id: str
    short_id: str
    time: str
    hostname: str
    tags: List[str]
    paths: List[str]


class ListSnapshotsResponse(BaseModel):
    """List snapshots response"""
    snapshots: List[SnapshotResponse]
    count: int = Field(..., description="Number of snapshots")


class CreateSnapshotResponse(BaseModel):
    """Create snapshot response"""
    success: bool = True
    snapshot_id: str
    files_new: int
    files_changed: int
    files_unmodified: int
    total_files_processed: int
    data_added: int
    total_bytes_processed: int


class RestoreSnapshotResponse(BaseModel):
    """Restore snapshot response"""
    success: bool
    snapshot_id: str
    target_path: str
    files_restored: int
    errors: List[str]


# Settings Responses

class SettingsResponse(BaseModel):
    """User settings response"""
    vast_api_key: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


# Balance Response

class BalanceResponse(BaseModel):
    """Account balance response"""
    credit: float = Field(..., description="Account credit")
    balance: float = Field(..., description="Account balance")
    balance_threshold: float = Field(..., description="Balance threshold")
    email: str = Field(..., description="User email")


# Migration Responses

class MigrationResponse(BaseModel):
    """Migration result response"""
    success: bool = Field(..., description="Migration success status")
    new_instance_id: Optional[int] = Field(None, description="New instance ID")
    old_instance_id: Optional[int] = Field(None, description="Old instance ID")
    snapshot_id: Optional[str] = Field(None, description="Snapshot ID used")
    error: Optional[str] = Field(None, description="Error message if failed")
    steps_completed: List[str] = Field(default_factory=list, description="Steps completed")


class MigrationEstimateResponse(BaseModel):
    """Migration estimate response"""
    available: bool = Field(..., description="Migration available")
    error: Optional[str] = Field(None, description="Error if not available")
    source: Optional[Dict[str, Any]] = Field(None, description="Source instance info")
    target: Optional[Dict[str, Any]] = Field(None, description="Target type info")
    estimated_time_minutes: Optional[int] = Field(None, description="Estimated time")
    offers_available: Optional[int] = Field(None, description="Number of offers")


# Sync Responses

class SyncResponse(BaseModel):
    """Sync operation response"""
    success: bool = Field(..., description="Sync success status")
    instance_id: int = Field(..., description="Instance ID")
    snapshot_id: Optional[str] = Field(None, description="Snapshot ID created")
    files_new: int = Field(0, description="New files")
    files_changed: int = Field(0, description="Changed files")
    files_unmodified: int = Field(0, description="Unchanged files")
    data_added: str = Field("0 B", description="Data added (human readable)")
    data_added_bytes: int = Field(0, description="Data added in bytes")
    duration_seconds: float = Field(0, description="Duration in seconds")
    is_incremental: bool = Field(True, description="Was incremental sync")
    error: Optional[str] = Field(None, description="Error message if failed")


class SyncStatusResponse(BaseModel):
    """Sync status response"""
    instance_id: int = Field(..., description="Instance ID")
    synced: bool = Field(False, description="Has been synced")
    is_syncing: bool = Field(False, description="Currently syncing")
    last_sync: Optional[str] = Field(None, description="Last sync timestamp")
    last_sync_ago: str = Field("Never", description="Time since last sync")
    last_snapshot_id: Optional[str] = Field(None, description="Last snapshot ID")
    sync_count: int = Field(0, description="Total sync count")
    last_stats: Optional[Dict[str, Any]] = Field(None, description="Last sync statistics")
    error: Optional[str] = Field(None, description="Last error if any")


# Fine-Tuning Responses

class FineTuneJobResponse(BaseModel):
    """Fine-tuning job response"""
    id: str = Field(..., description="Job ID")
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="Job name")
    status: str = Field(..., description="Job status")
    base_model: str = Field(..., description="Base model ID")
    dataset_source: str = Field(..., description="Dataset source")
    dataset_path: str = Field(..., description="Dataset path")
    dataset_format: str = Field(..., description="Dataset format")
    gpu_type: str = Field(..., description="GPU type")
    num_gpus: int = Field(..., description="Number of GPUs")
    config: Dict[str, Any] = Field(..., description="Fine-tuning config")

    # Progress
    current_epoch: int = Field(0, description="Current epoch")
    current_step: int = Field(0, description="Current step")
    total_steps: int = Field(0, description="Total steps")
    loss: Optional[float] = Field(None, description="Current loss")
    progress_percent: float = Field(0.0, description="Progress percentage")

    # Timestamps
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")

    # Output
    output_model_path: Optional[str] = Field(None, description="Output model path")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @classmethod
    def from_domain(cls, job) -> "FineTuneJobResponse":
        """Create from domain model"""
        return cls(
            id=job.id,
            user_id=job.user_id,
            name=job.name,
            status=job.status.value,
            base_model=job.config.base_model,
            dataset_source=job.dataset_source.value,
            dataset_path=job.dataset_path,
            dataset_format=job.dataset_format,
            gpu_type=job.gpu_type,
            num_gpus=job.num_gpus,
            config=job.config.to_dict(),
            current_epoch=job.current_epoch,
            current_step=job.current_step,
            total_steps=job.total_steps,
            loss=job.loss,
            progress_percent=job.progress_percent,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            output_model_path=job.output_model_path,
            error_message=job.error_message,
        )


class ListFineTuneJobsResponse(BaseModel):
    """List fine-tuning jobs response"""
    jobs: List[FineTuneJobResponse] = Field(..., description="List of jobs")
    count: int = Field(..., description="Number of jobs")


class FineTuneJobLogsResponse(BaseModel):
    """Fine-tuning job logs response"""
    job_id: str = Field(..., description="Job ID")
    logs: str = Field(..., description="Log output")


class FineTuneModelsResponse(BaseModel):
    """Supported models response"""
    models: List[Dict[str, Any]] = Field(..., description="List of supported models")
