"""
API Response Schemas (Pydantic models)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
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
    user: Optional[str] = Field(None, description="User email if authenticated")


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
    geolocation: str
    reliability: float
    cuda_version: str
    verified: bool
    static_ip: bool


class SearchOffersResponse(BaseModel):
    """Search offers response"""
    offers: List[GpuOfferResponse]
    count: int = Field(..., description="Number of offers found")


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
