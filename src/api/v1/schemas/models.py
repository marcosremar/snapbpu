"""
Model Deploy API Schemas (Pydantic models)
Schemas for deploying and managing ML models (LLM, Whisper, Diffusion, Embeddings)
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# Enums

class ModelType(str, Enum):
    """Type of model to deploy"""
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


# Request Schemas

class DeployModelRequest(BaseModel):
    """Deploy a new model request"""
    # Model type - optional, auto-detected from model name if not provided
    model_type: Optional[ModelType] = Field(None, description="Type of model (llm, speech, image, embeddings, vision, video) - auto-detected if not provided")
    type: Optional[str] = Field(None, description="Alias for model_type (for speech-to-text, image-generation, etc.)")

    # Model ID - can be model_id or model
    model_id: Optional[str] = Field(None, description="Model ID (HuggingFace ID or Ollama model name)")
    model: Optional[str] = Field(None, description="Alias for model_id")

    # Instance selection
    instance_id: Optional[int] = Field(None, description="Existing instance ID to use (null = create new)")
    offer_id: Optional[int] = Field(None, description="VAST.ai offer ID to use for new instance")

    # GPU config (only if creating new instance)
    gpu_type: Optional[str] = Field(None, description="GPU type (e.g., 'RTX 4090', 'A100')")
    num_gpus: int = Field(1, ge=1, le=8, description="Number of GPUs")
    max_price: float = Field(2.0, ge=0, description="Max price per hour ($)")

    # Runtime/Backend config
    backend: Optional[str] = Field(None, description="Runtime backend: vllm, ollama, pytorch, diffusers")
    quantization: Optional[str] = Field(None, description="Quantization: q4, q8, fp16, fp32")
    source: Optional[str] = Field(None, description="Model source: huggingface, ollama, local")

    # Access config
    access_type: AccessType = Field(AccessType.PRIVATE, description="Endpoint access type")
    port: int = Field(8000, ge=1024, le=65535, description="Port to expose")

    # Optional config
    name: Optional[str] = Field(None, max_length=100, description="Friendly name for the deployment")
    env_vars: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    label: Optional[str] = Field(None, max_length=100, description="Instance label (for testing use dumont:test:*)")

    class Config:
        use_enum_values = True

    def get_model_id(self) -> str:
        """Get model ID from model_id or model alias"""
        return self.model_id or self.model or ""

    def get_model_type(self) -> str:
        """Auto-detect model type from model name if not provided"""
        if self.model_type:
            return self.model_type.value if hasattr(self.model_type, 'value') else self.model_type

        # Check type alias
        if self.type:
            type_mapping = {
                "speech-to-text": "speech",
                "stt": "speech",
                "transcription": "speech",
                "image-generation": "image",
                "text-to-image": "image",
                "embedding": "embeddings",
            }
            return type_mapping.get(self.type.lower(), self.type.lower())

        # Auto-detect from model name
        model = self.get_model_id().lower()

        # Speech models
        if any(x in model for x in ["whisper", "wav2vec", "speech"]):
            return "speech"

        # Image models
        if any(x in model for x in ["stable-diffusion", "sdxl", "flux", "dall-e", "imagen", "diffusion"]):
            return "image"

        # Embedding models
        if any(x in model for x in ["embed", "sentence-transformer", "bge", "e5-", "minilm"]):
            return "embeddings"

        # Vision models
        if any(x in model for x in ["vision", "llava", "qwen-vl", "cogvlm"]):
            return "vision"

        # Default to LLM
        return "llm"


class StopModelRequest(BaseModel):
    """Stop a running model"""
    force: bool = Field(False, description="Force stop without graceful shutdown")


class UpdateModelRequest(BaseModel):
    """Update model configuration"""
    name: Optional[str] = Field(None, max_length=100, description="Update friendly name")
    access_type: Optional[AccessType] = Field(None, description="Update access type")

    class Config:
        use_enum_values = True


# Response Schemas

class ModelTemplateResponse(BaseModel):
    """Model template info"""
    type: str = Field(..., description="Model type")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    runtime: str = Field(..., description="Runtime (vllm, pytorch, diffusers)")
    default_port: int = Field(..., description="Default port")
    gpu_memory_required: float = Field(..., description="Minimum GPU memory (GB)")
    popular_models: List[Dict[str, str]] = Field(..., description="Popular models for this type")


class ListTemplatesResponse(BaseModel):
    """List available templates"""
    templates: List[ModelTemplateResponse] = Field(..., description="Available templates")


class DeployedModelResponse(BaseModel):
    """Deployed model info"""
    id: str = Field(..., description="Deployment ID")
    user_id: str = Field(..., description="User ID")
    name: Optional[str] = Field(None, description="Friendly name")

    # Model info
    model_type: str = Field(..., description="Model type")
    model_id: str = Field(..., description="Model ID")
    runtime: str = Field(..., description="Runtime used")

    # Instance info
    instance_id: int = Field(..., description="GPU instance ID")
    gpu_name: Optional[str] = Field(None, description="GPU name")
    num_gpus: int = Field(1, description="Number of GPUs")

    # Status
    status: str = Field(..., description="Deployment status")
    status_message: Optional[str] = Field(None, description="Status details")
    progress: float = Field(0, ge=0, le=100, description="Deploy progress (0-100)")

    # Endpoint
    endpoint_url: Optional[str] = Field(None, description="API endpoint URL")
    access_type: str = Field("private", description="Access type")
    api_key: Optional[str] = Field(None, description="API key (if private)")
    port: int = Field(8000, description="Port")

    # Cost
    dph_total: float = Field(0, description="Cost per hour ($)")

    # Timestamps
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")

    # Metrics (when running)
    requests_total: int = Field(0, description="Total requests served")
    requests_per_minute: float = Field(0, description="Current RPM")
    avg_latency_ms: float = Field(0, description="Average latency (ms)")


class ListModelsResponse(BaseModel):
    """List deployed models response"""
    models: List[DeployedModelResponse] = Field(..., description="Deployed models")
    count: int = Field(..., description="Total count")


class DeployModelResponse(BaseModel):
    """Deploy model response"""
    success: bool = Field(True, description="Deployment started")
    deployment_id: str = Field(..., description="Deployment ID")
    message: str = Field(..., description="Status message")
    estimated_time_seconds: int = Field(..., description="Estimated time to complete")


class ModelLogsResponse(BaseModel):
    """Model logs response"""
    deployment_id: str = Field(..., description="Deployment ID")
    logs: str = Field(..., description="Log output")
    timestamp: str = Field(..., description="Log timestamp")


class ModelHealthResponse(BaseModel):
    """Model health check response"""
    deployment_id: str = Field(..., description="Deployment ID")
    healthy: bool = Field(..., description="Is healthy")
    status: str = Field(..., description="Current status")
    uptime_seconds: int = Field(0, description="Uptime in seconds")
    last_request: Optional[str] = Field(None, description="Last request timestamp")
    error: Optional[str] = Field(None, description="Error if unhealthy")
