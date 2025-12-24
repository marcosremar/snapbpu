"""
API Request Schemas (Pydantic models)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


# Auth Requests

class LoginRequest(BaseModel):
    """Login request"""
    username: EmailStr = Field(..., alias="email", description="User email")
    password: str = Field(..., min_length=1, description="User password")

    class Config:
        populate_by_name = True  # Accept both username and email


class RegisterRequest(BaseModel):
    """Registration request"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")


# Instance Requests

class SearchOffersRequest(BaseModel):
    """Search GPU offers request"""
    gpu_name: Optional[str] = Field(None, description="GPU model (e.g., 'RTX 4090')")
    num_gpus: int = Field(1, ge=1, le=8, description="Number of GPUs")
    min_gpu_ram: float = Field(0, ge=0, description="Minimum GPU RAM (GB)")
    min_cpu_cores: int = Field(1, ge=1, description="Minimum CPU cores")
    min_cpu_ram: float = Field(1, ge=0, description="Minimum CPU RAM (GB)")
    min_disk: float = Field(50, ge=10, description="Minimum disk space (GB)")
    min_inet_down: float = Field(500, ge=0, description="Minimum download speed (Mbps)")
    max_price: float = Field(1.0, ge=0, description="Maximum price per hour ($)")
    min_cuda: str = Field("11.0", description="Minimum CUDA version")
    min_reliability: float = Field(0.0, ge=0, le=1, description="Minimum reliability score")
    region: Optional[str] = Field(None, description="Region filter (US, EU, ASIA)")
    verified_only: bool = Field(False, description="Only verified hosts")
    static_ip: bool = Field(False, description="Require static IP")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results")


class CreateInstanceRequest(BaseModel):
    """Create instance request"""
    offer_id: int = Field(..., description="GPU offer ID")
    image: str = Field("pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime", description="Docker image")
    disk_size: float = Field(100, ge=10, description="Disk size (GB)")
    label: Optional[str] = Field(None, description="Instance label")
    ports: Optional[List[int]] = Field(None, description="Ports to expose")
    skip_standby: bool = Field(False, alias="skip-standby", description="Skip CPU standby creation (default: create standby)")
    skip_validation: bool = Field(False, description="Skip pre-validation (faster but may fail at creation time)")

    class Config:
        populate_by_name = True  # Accept both skip_standby and skip-standby


# Snapshot Requests

class CreateSnapshotRequest(BaseModel):
    """Create snapshot request"""
    instance_id: int = Field(..., description="Instance ID to snapshot")
    source_path: str = Field("/workspace", description="Path to backup")
    tags: Optional[List[str]] = Field(None, description="Optional tags")


class RestoreSnapshotRequest(BaseModel):
    """Restore snapshot request"""
    snapshot_id: str = Field(..., description="Snapshot ID to restore")
    target_path: str = Field("/workspace", description="Path to restore to")
    verify: bool = Field(False, description="Verify restoration")


class DeleteSnapshotRequest(BaseModel):
    """Delete snapshot request"""
    snapshot_id: str = Field(..., description="Snapshot ID to delete")


class PruneSnapshotsRequest(BaseModel):
    """Prune snapshots request"""
    keep_last: int = Field(10, ge=1, description="Number of snapshots to keep")


# Migration Requests

class MigrateInstanceRequest(BaseModel):
    """Migrate instance request (GPU <-> CPU)"""
    target_type: str = Field(..., description="Target type: 'gpu' or 'cpu'")
    gpu_name: Optional[str] = Field(None, description="GPU model (required if target_type='gpu')")
    max_price: float = Field(2.0, ge=0, description="Maximum price per hour ($)")
    region: Optional[str] = Field(None, description="Region filter (US, EU, ASIA)")
    disk_size: int = Field(100, ge=50, description="Disk size (GB)")
    auto_destroy_source: bool = Field(True, description="Destroy source instance after migration")


class MigrationEstimateRequest(BaseModel):
    """Migration estimate request"""
    target_type: str = Field(..., description="Target type: 'gpu' or 'cpu'")
    gpu_name: Optional[str] = Field(None, description="GPU model (required if target_type='gpu')")
    max_price: float = Field(2.0, ge=0, description="Maximum price per hour ($)")
    region: Optional[str] = Field(None, description="Region filter (US, EU, ASIA)")


# Settings Requests

class UpdateSettingsRequest(BaseModel):
    """Update user settings request"""
    vast_api_key: Optional[str] = Field(None, description="Vast.ai API key")
    settings: Optional[Dict[str, Any]] = Field(None, description="User settings")


# Fine-Tuning Requests

class FineTuneConfigRequest(BaseModel):
    """Fine-tuning configuration"""
    lora_rank: int = Field(16, ge=4, le=128, description="LoRA rank")
    lora_alpha: int = Field(16, ge=4, le=128, description="LoRA alpha")
    learning_rate: float = Field(2e-4, ge=1e-6, le=1e-2, description="Learning rate")
    epochs: int = Field(1, ge=1, le=10, description="Number of epochs")
    batch_size: int = Field(2, ge=1, le=32, description="Batch size per GPU")
    gradient_accumulation_steps: int = Field(4, ge=1, le=32, description="Gradient accumulation steps")
    max_seq_length: int = Field(2048, ge=256, le=8192, description="Maximum sequence length")
    warmup_steps: int = Field(5, ge=0, le=1000, description="Warmup steps")
    weight_decay: float = Field(0.01, ge=0, le=1, description="Weight decay")


class CreateFineTuneJobRequest(BaseModel):
    """Create fine-tuning job request"""
    name: str = Field(..., min_length=1, max_length=100, description="Job name")
    base_model: str = Field(..., description="Base model ID (e.g., unsloth/llama-3-8b-bnb-4bit)")
    dataset_source: str = Field(..., description="Dataset source: upload, url, huggingface")
    dataset_path: str = Field(..., description="Dataset path (local path or URL)")
    dataset_format: str = Field("alpaca", description="Dataset format: alpaca, sharegpt, raw")
    config: Optional[FineTuneConfigRequest] = Field(None, description="Fine-tuning configuration")
    gpu_type: str = Field("A100", description="GPU type")
    num_gpus: int = Field(1, ge=1, le=8, description="Number of GPUs")
