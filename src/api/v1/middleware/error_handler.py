"""
Global error handling middleware
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ....core.exceptions import (
    DumontCloudException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    VastAPIException,
    SnapshotException,
    SSHException,
    ServiceUnavailableException,
)

logger = logging.getLogger(__name__)


async def dumont_exception_handler(request: Request, exc: DumontCloudException) -> JSONResponse:
    """Handle custom Dumont Cloud exceptions"""
    logger.error(f"DumontCloudException: {exc.message}", extra={"details": exc.details})

    # Map exception types to HTTP status codes
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, (ValidationException, RequestValidationError)):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, AuthenticationException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AuthorizationException):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ServiceUnavailableException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.message,
            "details": exc.details,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    logger.warning(f"HTTPException: {exc.detail} (status={exc.status_code})")

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors from Pydantic"""
    logger.warning(f"ValidationError: {exc.errors()}")

    # Ensure all error details are JSON serializable (convert bytes to str)
    def make_serializable(obj):
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        elif isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(item) for item in obj]
        return obj

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": make_serializable(exc.errors()),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.exception(f"Unexpected error: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "details": str(exc),
        },
    )
