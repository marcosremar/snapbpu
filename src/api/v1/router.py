"""
Main API v1 router
"""
from fastapi import APIRouter

from .endpoints import auth, instances, snapshots, settings, metrics, ai_wizard, standby, agent, savings, advisor, hibernation
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

# Spot Reports - Relatórios de instâncias spot
api_router.include_router(spot_router, prefix="/metrics", tags=["Spot Reports"])

