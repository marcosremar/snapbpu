from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from ..dependencies import get_current_user_email, get_user_repository
from ....services.gpu.vast import VastService

router = APIRouter()

def get_vast_service_local(
    user_email: str = Depends(get_current_user_email),
    user_repo = Depends(get_user_repository),
) -> VastService:
    user = user_repo.get_user(user_email)
    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured.",
        )
    return VastService(api_key=user.vast_api_key)

@router.get("/models")
def list_models(
    vast_service: VastService = Depends(get_vast_service_local)
):
    """
    List available Chat Models (LLMs) running on instances.
    Detects instances with exposed Ollama port (11434).
    """
    try:
        # Get all instances
        instances = vast_service.get_my_instances()
        
        models = []
        for inst in instances:
            # Filter for running instances
            if inst.get("actual_status") == "running" and inst.get("public_ipaddr"):
                
                # Check ports
                ports = inst.get("ports", {})
                ollama_url = None
                is_ollama = False
                
                # Check for 11434 mapping
                if ports and "11434/tcp" in ports:
                    mappings = ports["11434/tcp"]
                    if mappings:
                        host_port = mappings[0].get("HostPort")
                        if host_port:
                            ollama_url = f"http://{inst['public_ipaddr']}:{host_port}"
                            is_ollama = True
                
                if is_ollama:
                     models.append({
                        "id": inst.get("id"),
                        "name": f"{inst.get('gpu_name', 'GPU')} (Instance {inst.get('id')})",
                        "gpu": inst.get("gpu_name"),
                        "status": "online",
                        "ip": inst.get("public_ipaddr"),
                        "ollama_url": ollama_url,
                        "raw_ports": ports
                    })
        
        return {"models": models}

    except Exception as e:
        print(f"Error listing chat models: {e}")
        return {"models": [], "error": str(e)}
