"""
AI Wizard API Endpoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.services.ai_wizard_service import ai_wizard_service

router = APIRouter(prefix="/ai-wizard", tags=["AI Wizard"])


class Message(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")


class AnalyzeRequest(BaseModel):
    project_description: str = Field(..., description="User's project description")
    conversation_history: Optional[List[Message]] = Field(
        default=None,
        description="Previous conversation messages for context"
    )


class GPUOption(BaseModel):
    tier: str = Field(..., description="minima, recomendada, or maxima")
    gpu: str = Field(..., description="GPU model name")
    vram: str = Field(..., description="VRAM amount")
    price_per_hour: str = Field(..., description="Price per hour")
    frameworks: Optional[Dict[str, str]] = Field(default=None, description="Performance by framework")
    ram_offload: Optional[str] = Field(default=None, description="RAM offload requirements")
    tokens_per_second: Optional[str] = Field(default=None, description="Estimated tokens/second (legacy)")
    observation: str = Field(..., description="Additional notes")


class ModelInfo(BaseModel):
    name: str = Field(..., description="Model name")
    parameters: str = Field(..., description="Model size in parameters")
    vram_fp16: Optional[str] = Field(default=None, description="VRAM for FP16")
    vram_int8: Optional[str] = Field(default=None, description="VRAM for INT8")
    vram_int4: Optional[str] = Field(default=None, description="VRAM for INT4")
    vram_required: Optional[str] = Field(default=None, description="VRAM required (legacy)")
    recommended_quantization: Optional[str] = Field(default=None, description="Recommended quantization")
    quantization: Optional[str] = Field(default=None, description="Quantization (legacy)")


class GPURecommendation(BaseModel):
    workload_type: str
    model_info: Optional[ModelInfo] = None
    gpu_options: Optional[List[GPUOption]] = None
    optimization_tips: Optional[List[str]] = Field(default=None, description="Optimization tips")
    # Legacy fields for backward compatibility
    min_vram_gb: Optional[int] = None
    recommended_gpus: Optional[List[str]] = None
    tier_suggestion: Optional[str] = None
    explanation: str
    search_sources: Optional[str] = None


class AnalyzeResponse(BaseModel):
    success: bool
    needs_more_info: bool
    questions: List[str] = []
    recommendation: Optional[GPURecommendation] = None
    model_used: str


@router.post("/analyze")
async def analyze_project(request: AnalyzeRequest):
    """
    Analyze a project description and return GPU recommendations.

    The AI will either:
    1. Return GPU recommendations if it has enough information
    2. Ask clarifying questions if more details are needed
    """
    # Convert conversation history to dict format
    history = None
    if request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    result = await ai_wizard_service.analyze_project(
        project_description=request.project_description,
        conversation_history=history
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail="Failed to analyze project")

    data = result.get("data", {})

    # Retornar no novo formato com campo data completo
    return {
        "success": True,
        "data": data,  # Incluir campo data completo com stage, questions, etc.
        "model_used": result.get("model_used", "unknown"),
        "attempts": result.get("attempts", 1)
    }
