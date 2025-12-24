"""
Model Deploy Domain Model
Represents a deployed ML model (LLM, Whisper, Diffusion, Embeddings)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import uuid
import secrets


class ModelType(str, Enum):
    """Type of model"""
    LLM = "llm"
    SPEECH = "speech"
    IMAGE = "image"
    EMBEDDINGS = "embeddings"
    VISION = "vision"  # Image → Text (VLM, OCR, image understanding)
    VIDEO = "video"    # Text → Video (video generation)


class ModelStatus(str, Enum):
    """Status of deployed model"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    DOWNLOADING = "downloading"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class AccessType(str, Enum):
    """Access type for endpoint"""
    PUBLIC = "public"
    PRIVATE = "private"


@dataclass
class ModelDeployment:
    """Represents a deployed model"""

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: Optional[str] = None

    # Model info
    model_type: ModelType = ModelType.LLM
    model_id: str = ""  # HuggingFace ID or Ollama model name
    runtime: str = "vllm"  # vllm, pytorch, diffusers, sentence-transformers

    # Instance info
    instance_id: int = 0
    gpu_name: Optional[str] = None
    num_gpus: int = 1

    # Status
    status: ModelStatus = ModelStatus.PENDING
    status_message: Optional[str] = None
    progress: float = 0.0  # 0-100

    # Endpoint
    endpoint_url: Optional[str] = None
    access_type: AccessType = AccessType.PRIVATE
    api_key: Optional[str] = None
    port: int = 8000

    # Cost
    dph_total: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None

    # Metrics
    requests_total: int = 0
    requests_per_minute: float = 0.0
    avg_latency_ms: float = 0.0

    # Internal
    pid: Optional[int] = None  # Process ID on the instance
    env_vars: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Generate API key if private access"""
        if self.access_type == AccessType.PRIVATE and not self.api_key:
            self.api_key = f"sk-{secrets.token_urlsafe(32)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "model_type": self.model_type.value,
            "model_id": self.model_id,
            "runtime": self.runtime,
            "instance_id": self.instance_id,
            "gpu_name": self.gpu_name,
            "num_gpus": self.num_gpus,
            "status": self.status.value,
            "status_message": self.status_message,
            "progress": self.progress,
            "endpoint_url": self.endpoint_url,
            "access_type": self.access_type.value,
            "api_key": self.api_key,
            "port": self.port,
            "dph_total": self.dph_total,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "requests_total": self.requests_total,
            "requests_per_minute": self.requests_per_minute,
            "avg_latency_ms": self.avg_latency_ms,
            "pid": self.pid,
            "env_vars": self.env_vars,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelDeployment":
        """Create from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            name=data.get("name"),
            model_type=ModelType(data.get("model_type", "llm")),
            model_id=data.get("model_id", ""),
            runtime=data.get("runtime", "vllm"),
            instance_id=data.get("instance_id", 0),
            gpu_name=data.get("gpu_name"),
            num_gpus=data.get("num_gpus", 1),
            status=ModelStatus(data.get("status", "pending")),
            status_message=data.get("status_message"),
            progress=data.get("progress", 0.0),
            endpoint_url=data.get("endpoint_url"),
            access_type=AccessType(data.get("access_type", "private")),
            api_key=data.get("api_key"),
            port=data.get("port", 8000),
            dph_total=data.get("dph_total", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            stopped_at=datetime.fromisoformat(data["stopped_at"]) if data.get("stopped_at") else None,
            requests_total=data.get("requests_total", 0),
            requests_per_minute=data.get("requests_per_minute", 0.0),
            avg_latency_ms=data.get("avg_latency_ms", 0.0),
            pid=data.get("pid"),
            env_vars=data.get("env_vars", {}),
        )

    def update_status(self, status: ModelStatus, message: Optional[str] = None, progress: Optional[float] = None):
        """Update deployment status"""
        self.status = status
        if message:
            self.status_message = message
        if progress is not None:
            self.progress = progress

        if status == ModelStatus.RUNNING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif status == ModelStatus.STOPPED:
            self.stopped_at = datetime.utcnow()

    def is_running(self) -> bool:
        """Check if model is running"""
        return self.status == ModelStatus.RUNNING

    def is_deploying(self) -> bool:
        """Check if model is being deployed"""
        return self.status in [ModelStatus.PENDING, ModelStatus.DEPLOYING, ModelStatus.DOWNLOADING, ModelStatus.STARTING]

    def get_runtime_for_type(self) -> str:
        """Get appropriate runtime for model type"""
        runtime_map = {
            ModelType.LLM: "vllm",
            ModelType.SPEECH: "pytorch",
            ModelType.IMAGE: "diffusers",
            ModelType.EMBEDDINGS: "sentence-transformers",
            ModelType.VISION: "transformers",  # VLMs use transformers (SmolVLM, LLaVA, etc)
            ModelType.VIDEO: "diffusers",      # Video gen uses diffusers (CogVideoX, etc)
        }
        return runtime_map.get(self.model_type, "pytorch")
