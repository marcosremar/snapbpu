"""
Models API Endpoints - Deploy and manage ML models (LLM, Whisper, Diffusion, Embeddings)

Supports deploying models to GPU instances with different runtimes:
- LLM: vLLM for chat/completion
- Speech: PyTorch + Transformers for Whisper
- Image: Diffusers for Stable Diffusion/FLUX
- Embeddings: Sentence-Transformers
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from datetime import datetime

from ..dependencies import get_current_user_email
from ..schemas.models import (
    ModelType, ModelStatus, AccessType,
    DeployModelRequest, StopModelRequest, UpdateModelRequest,
    DeployedModelResponse, ListModelsResponse, DeployModelResponse,
    ModelTemplateResponse, ListTemplatesResponse,
    ModelLogsResponse, ModelHealthResponse,
)
from src.domain.services.model_deploy_service import get_model_deploy_service, ModelDeployService
from src.domain.models.model_deploy import ModelDeployment

router = APIRouter(prefix="/models", tags=["Models"])


# ============================================================================
# Helper Functions
# ============================================================================

def deployment_to_response(deployment: ModelDeployment) -> DeployedModelResponse:
    """Convert ModelDeployment to API response"""
    return DeployedModelResponse(
        id=deployment.id,
        user_id=deployment.user_id,
        name=deployment.name,
        model_type=deployment.model_type.value,
        model_id=deployment.model_id,
        runtime=deployment.runtime,
        instance_id=deployment.instance_id,
        gpu_name=deployment.gpu_name,
        num_gpus=deployment.num_gpus,
        status=deployment.status.value,
        status_message=deployment.status_message,
        progress=deployment.progress,
        endpoint_url=deployment.endpoint_url,
        access_type=deployment.access_type.value,
        api_key=deployment.api_key,
        port=deployment.port,
        dph_total=deployment.dph_total,
        created_at=deployment.created_at.isoformat() if deployment.created_at else datetime.utcnow().isoformat(),
        started_at=deployment.started_at.isoformat() if deployment.started_at else None,
        requests_total=deployment.requests_total,
        requests_per_minute=deployment.requests_per_minute,
        avg_latency_ms=deployment.avg_latency_ms,
    )


def get_service(request: Request) -> ModelDeployService:
    """Get model deploy service, with demo mode support"""
    from src.core.config import get_settings
    settings = get_settings()

    demo_param = request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param

    # For now, the service works the same in demo mode
    # In production, we'd pass vast_client and ssh_client
    return get_model_deploy_service()


# ============================================================================
# Template Endpoints
# ============================================================================

@router.get("/templates", response_model=ListTemplatesResponse)
async def list_templates(
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """
    List available model templates.

    Returns templates for:
    - LLM (vLLM): Chat and completion models
    - Speech (Whisper): Audio transcription
    - Image (Diffusers): Image generation
    - Embeddings: Vector embeddings for search/RAG
    """
    service = get_service(request)
    templates = service.get_templates()

    return ListTemplatesResponse(
        templates=[
            ModelTemplateResponse(**t) for t in templates
        ]
    )


# ============================================================================
# Deploy Endpoints
# ============================================================================

@router.post("/deploy", response_model=DeployModelResponse, status_code=status.HTTP_201_CREATED)
async def deploy_model(
    request_body: DeployModelRequest,
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """
    Deploy a new model to a GPU instance.

    The deployment process:
    1. Get or create GPU instance
    2. Install runtime dependencies
    3. Download model from HuggingFace
    4. Start model server
    5. Wait for health check

    Returns immediately with deployment ID - poll /models/{id} for status.
    """
    try:
        service = get_service(request)

        deployment = await service.create_deployment(
            user_id=user_email,
            model_type=request_body.model_type.value if hasattr(request_body.model_type, 'value') else request_body.model_type,
            model_id=request_body.model_id,
            instance_id=request_body.instance_id,
            gpu_type=request_body.gpu_type,
            num_gpus=request_body.num_gpus,
            max_price=request_body.max_price,
            access_type=request_body.access_type.value if hasattr(request_body.access_type, 'value') else request_body.access_type,
            port=request_body.port,
            name=request_body.name,
            env_vars=request_body.env_vars,
            label=request_body.label,  # Custom label for testing
        )

        # Estimate time based on model type
        estimated_time = {
            "llm": 300,  # 5 min
            "speech": 180,  # 3 min
            "image": 240,  # 4 min
            "embeddings": 120,  # 2 min
        }.get(deployment.model_type.value, 180)

        return DeployModelResponse(
            success=True,
            deployment_id=deployment.id,
            message=f"Deployment started for {deployment.model_id}",
            estimated_time_seconds=estimated_time,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deployment: {str(e)}"
        )


@router.get("/", response_model=ListModelsResponse)
async def list_models(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    model_type: Optional[str] = Query(None, description="Filter by model type"),
    user_email: str = Depends(get_current_user_email),
):
    """
    List all deployed models for current user.

    Optional filters:
    - status: pending, deploying, downloading, starting, running, stopped, error
    - model_type: llm, speech, image, embeddings
    """
    service = get_service(request)
    deployments = await service.get_user_deployments(user_email)

    # Apply filters
    if status_filter:
        try:
            from src.domain.models.model_deploy import ModelStatus as DomainModelStatus
            filter_status = DomainModelStatus(status_filter)
            deployments = [d for d in deployments if d.status == filter_status]
        except ValueError:
            pass

    if model_type:
        try:
            from src.domain.models.model_deploy import ModelType as DomainModelType
            filter_type = DomainModelType(model_type)
            deployments = [d for d in deployments if d.model_type == filter_type]
        except ValueError:
            pass

    return ListModelsResponse(
        models=[deployment_to_response(d) for d in deployments],
        count=len(deployments)
    )


@router.get("/{deployment_id}", response_model=DeployedModelResponse)
async def get_deployment(
    deployment_id: str,
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """Get deployment details by ID"""
    service = get_service(request)
    deployment = await service.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )

    # Check ownership
    if deployment.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return deployment_to_response(deployment)


@router.post("/{deployment_id}/stop", response_model=DeployedModelResponse)
async def stop_deployment(
    deployment_id: str,
    request_body: StopModelRequest,
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """
    Stop a running deployment.

    The model server will be stopped but the instance may remain
    for quick restart.
    """
    service = get_service(request)
    deployment = await service.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )

    if deployment.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    success = await service.stop_deployment(deployment_id, force=request_body.force)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop deployment"
        )

    # Refresh deployment status
    deployment = await service.get_deployment(deployment_id)
    return deployment_to_response(deployment)


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deployment(
    deployment_id: str,
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """
    Delete a deployment.

    This will stop the model and remove all associated resources.
    """
    service = get_service(request)
    deployment = await service.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )

    if deployment.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    success = await service.delete_deployment(deployment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete deployment"
        )

    return None


@router.get("/{deployment_id}/logs", response_model=ModelLogsResponse)
async def get_deployment_logs(
    deployment_id: str,
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """Get logs for a deployment"""
    service = get_service(request)
    deployment = await service.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )

    if deployment.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    logs = await service.get_logs(deployment_id)

    return ModelLogsResponse(
        deployment_id=deployment_id,
        logs=logs,
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/{deployment_id}/health", response_model=ModelHealthResponse)
async def check_deployment_health(
    deployment_id: str,
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """Check health of a deployment"""
    service = get_service(request)
    deployment = await service.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )

    if deployment.user_id != user_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    health = await service.health_check(deployment_id)

    return ModelHealthResponse(
        deployment_id=deployment_id,
        healthy=health.get("healthy", False),
        status=health.get("status", "unknown"),
        uptime_seconds=health.get("uptime_seconds", 0),
        error=health.get("error"),
    )
