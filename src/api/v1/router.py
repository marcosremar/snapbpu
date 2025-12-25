"""
Main API v1 router
"""
from fastapi import APIRouter

from .endpoints import auth, instances, snapshots, settings, metrics, ai_wizard, standby, agent, savings, advisor, hibernation, finetune, chat
from .endpoints import warmpool, failover_settings, failover, serverless, spot_deploy, machine_history, jobs, models
from .endpoints.settings import balance_router
from .endpoints.spot import router as spot_router

# Create API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(instances.router)
api_router.include_router(snapshots.router)
api_router.include_router(settings.router)
api_router.include_router(balance_router)
api_router.include_router(metrics.router)
api_router.include_router(ai_wizard.router)
api_router.include_router(advisor.router, prefix="/advisor", tags=["AI GPU Advisor"])
api_router.include_router(hibernation.router, prefix="/hibernation", tags=["Auto-Hibernation"])
api_router.include_router(standby.router)
api_router.include_router(agent.router)
api_router.include_router(savings.router, prefix="/savings", tags=["Savings Dashboard"])
api_router.include_router(finetune.router)

# Spot Reports - Relatórios de instâncias spot
api_router.include_router(spot_router, prefix="/metrics", tags=["Spot Reports"])

# GPU Warm Pool - Estratégia principal de failover
api_router.include_router(warmpool.router, tags=["GPU Warm Pool"])

# Failover Settings - Configurações de failover
api_router.include_router(failover_settings.router, tags=["Failover Settings"])

# Failover Orchestrator - Execução de failover
api_router.include_router(failover.router, tags=["Failover Orchestrator"])

# Serverless GPU - Auto-pause/resume
api_router.include_router(serverless.router, tags=["Serverless GPU"])
api_router.include_router(serverless.public_router, tags=["Serverless GPU"])  # Public endpoints (no auth)

# Spot GPU Deploy - Deploy e failover de instâncias spot
api_router.include_router(spot_deploy.router, tags=["Spot GPU Deploy"])

# Chat - LLM Chat Integration
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])

# Machine History & Blacklist - Histórico de máquinas e blacklist
api_router.include_router(machine_history.router, tags=["Machine History"])

# Jobs - GPU Jobs (Execute and Destroy)
api_router.include_router(jobs.router, tags=["Jobs"])

# Models - Deploy and manage ML models (LLM, Whisper, Diffusion, Embeddings)
api_router.include_router(models.router, tags=["Models"])

