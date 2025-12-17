"""
Main API v1 router
"""
from fastapi import APIRouter

from .endpoints import auth, instances, snapshots, settings
from .endpoints.settings import balance_router

# Create API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(instances.router)
api_router.include_router(snapshots.router)
api_router.include_router(settings.router)
api_router.include_router(balance_router)
