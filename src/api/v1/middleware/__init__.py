"""
FastAPI middleware
"""
from . import error_handler
from .serverless import (
    ServerlessMiddleware,
    setup_serverless_middleware,
    get_serverless_service,
    get_serverless_service_dependency,
)

__all__ = [
    'error_handler',
    'ServerlessMiddleware',
    'setup_serverless_middleware',
    'get_serverless_service',
    'get_serverless_service_dependency',
]
