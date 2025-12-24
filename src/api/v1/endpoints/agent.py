"""
Agent API Endpoints - Recebe heartbeats do DumontAgent

O DumontAgent roda DENTRO das máquinas GPU e envia status periodicamente.
Este endpoint processa esses heartbeats e atualiza o AutoHibernationManager.
"""
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from ....services.standby.hibernation import get_auto_hibernation_manager
from ....services.standby.serverless import get_serverless_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


class GPUMetrics(BaseModel):
    """Métricas de GPU enviadas pelo agente"""
    utilization: float = Field(..., ge=0, le=100, description="GPU utilization %")
    gpu_count: int = Field(1, ge=1, description="Number of GPUs")
    gpu_names: List[str] = Field(default_factory=list, description="GPU model names")
    gpu_utilizations: List[float] = Field(default_factory=list, description="Per-GPU utilization")
    gpu_memory_used: List[int] = Field(default_factory=list, description="Memory used per GPU (MB)")
    gpu_memory_total: List[int] = Field(default_factory=list, description="Total memory per GPU (MB)")
    gpu_temperatures: List[float] = Field(default_factory=list, description="Temperature per GPU (C)")


class AgentStatusRequest(BaseModel):
    """Request do heartbeat do agente"""
    agent: str = Field("DumontAgent", description="Agent name")
    version: str = Field(..., description="Agent version")
    instance_id: str = Field(..., description="Instance ID (vast_12345 or just 12345)")
    status: str = Field(..., description="Agent status: idle, syncing, error, starting")
    message: Optional[str] = Field(None, description="Status message")
    last_backup: Optional[str] = Field(None, description="Last backup timestamp")
    timestamp: str = Field(..., description="Heartbeat timestamp")
    uptime: Optional[str] = Field(None, description="Instance uptime")
    gpu_metrics: Optional[GPUMetrics] = Field(None, description="GPU metrics")
    # Campos legacy do shell agent
    gpu_utilization: Optional[float] = Field(None, description="Legacy: GPU utilization %")


class AgentStatusResponse(BaseModel):
    """Resposta para o agente"""
    received: bool = True
    instance_id: str
    action: Optional[str] = Field(None, description="Action for agent: none, prepare_hibernate, shutdown")
    message: str = "Status received"


class AgentHeartbeatSummary(BaseModel):
    """Resumo de heartbeat para listagem"""
    instance_id: str
    status: str
    gpu_utilization: float
    last_seen: str
    idle_since: Optional[str] = None
    will_hibernate_at: Optional[str] = None


@router.post("/status", response_model=AgentStatusResponse)
async def receive_agent_status(request: AgentStatusRequest):
    """
    Recebe status/heartbeat do DumontAgent.
    
    O agente envia isso a cada 30 segundos com:
    - Status atual (idle, syncing, error)
    - Métricas de GPU (utilização, memória, temperatura)
    - Informações de backup
    
    O servidor processa e decide se deve hibernar a máquina.
    """
    try:
        # Extrair instance_id numérico
        instance_id = request.instance_id
        if instance_id.startswith("vast_"):
            instance_id = instance_id.replace("vast_", "")
        
        # Obter utilização de GPU
        gpu_utilization = 0.0
        if request.gpu_metrics:
            gpu_utilization = request.gpu_metrics.utilization
        elif request.gpu_utilization is not None:
            gpu_utilization = request.gpu_utilization
        
        logger.info(
            f"Agent heartbeat: instance={instance_id}, status={request.status}, "
            f"gpu_util={gpu_utilization:.1f}%"
        )
        
        # Atualizar o AutoHibernationManager
        manager = get_auto_hibernation_manager()
        if manager:
            result = manager.update_instance_status(
                instance_id=instance_id,
                gpu_utilization=gpu_utilization,
                gpu_threshold=5.0  # < 5% é considerado ocioso
            )

            # Verificar se deve hibernar
            if result and result.get("should_hibernate"):
                return AgentStatusResponse(
                    instance_id=instance_id,
                    action="prepare_hibernate",
                    message=f"Instance will hibernate in {result.get('seconds_until_hibernate', 0)}s"
                )

        # Atualizar o ServerlessManager com GPU utilization
        try:
            serverless_manager = get_serverless_manager()
            serverless_manager.update_gpu_utilization(
                instance_id=int(instance_id),
                gpu_util=gpu_utilization
            )
        except (ValueError, Exception) as e:
            # Instance ID pode não ser numérico, ou serverless não configurado
            logger.debug(f"Could not update serverless manager: {e}")
        
        return AgentStatusResponse(
            instance_id=instance_id,
            action="none",
            message="Status received"
        )
        
    except Exception as e:
        logger.error(f"Error processing agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/instances", response_model=List[AgentHeartbeatSummary])
async def list_agent_instances():
    """
    Lista todas as instâncias com agentes ativos.
    
    Retorna informações sobre:
    - Status do agente
    - Utilização de GPU
    - Tempo ocioso
    - Previsão de hibernação
    """
    manager = get_auto_hibernation_manager()
    if not manager:
        return []
    
    # Obter status de todas as instâncias rastreadas
    instances = manager.get_all_instance_status()
    
    summaries = []
    for inst in instances:
        summaries.append(AgentHeartbeatSummary(
            instance_id=str(inst.get("instance_id", "")),
            status=inst.get("status", "unknown"),
            gpu_utilization=inst.get("gpu_utilization", 0),
            last_seen=inst.get("last_heartbeat", ""),
            idle_since=inst.get("idle_since"),
            will_hibernate_at=inst.get("will_hibernate_at"),
        ))
    
    return summaries


@router.get("/instances/{instance_id}")
async def get_agent_instance_status(instance_id: str):
    """
    Obtém status detalhado de uma instância específica.
    """
    manager = get_auto_hibernation_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-hibernation manager not initialized"
        )
    
    status_data = manager.get_instance_status(instance_id)
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found or no recent heartbeat"
        )
    
    return status_data


@router.post("/instances/{instance_id}/keep-alive")
async def keep_instance_alive(instance_id: str, minutes: int = 30):
    """
    Mantém uma instância ativa por mais tempo, adiando hibernação.
    
    Útil quando o usuário sabe que vai precisar da máquina em breve.
    """
    manager = get_auto_hibernation_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auto-hibernation manager not initialized"
        )
    
    success = manager.extend_keep_alive(instance_id, minutes)
    
    if success:
        return {
            "success": True,
            "message": f"Instance {instance_id} will stay alive for {minutes} more minutes",
            "new_hibernate_at": manager.get_instance_status(instance_id).get("will_hibernate_at")
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found"
        )
