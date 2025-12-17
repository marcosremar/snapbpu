"""
FastAPI Application - Dumont Cloud v3
GPU Instance Management Platform with SOLID Architecture
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import get_settings
from .core.constants import API_V1_PREFIX, API_TITLE, API_VERSION, API_DESCRIPTION
from .core.exceptions import DumontCloudException
from .api.v1 import api_router
from .api.v1.middleware.error_handler import (
    dumont_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown
    """
    # Startup
    logger.info("🚀 Starting Dumont Cloud FastAPI application...")
    logger.info(f"   Version: {API_VERSION}")
    logger.info(f"   Environment: {'Development' if get_settings().app.debug else 'Production'}")

    # TODO: Initialize background agents here
    # - PriceMonitorAgent
    # - AutoHibernationManager

    yield

    # Shutdown
    logger.info("🛑 Shutting down Dumont Cloud FastAPI application...")
    # TODO: Stop background agents


def create_app() -> FastAPI:
    """
    Application factory

    Creates and configures FastAPI application with:
    - CORS middleware
    - Exception handlers
    - API routers
    - Static file serving
    """
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins + ["*"],  # Allow all in dev
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(DumontCloudException, dumont_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include API v1 router
    app.include_router(api_router, prefix=API_V1_PREFIX)

    # Compatibility: also mount at /api (without v1) for frontend
    app.include_router(api_router, prefix="/api")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": API_VERSION,
            "service": "dumont-cloud",
        }

    # Static files path
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "build")
    index_path = os.path.join(static_path, "index.html")

    # Mount static files (React build) - for JS, CSS, images
    assets_path = os.path.join(static_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        logger.info(f"✓ Mounted static assets from {assets_path}")

    # Root endpoint - serve React app
    @app.get("/")
    async def root():
        """Serve React app"""
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {
            "message": "Dumont Cloud API",
            "version": API_VERSION,
            "docs": "/docs",
            "health": "/health",
        }

    # Catch-all route for React SPA - must be last
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA for all non-API routes"""
        # Skip API routes
        if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
            return JSONResponse({"error": "Not Found"}, status_code=404)

        # Check if it's a static file request
        file_path = os.path.join(static_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Serve index.html for SPA routing
        if os.path.exists(index_path):
            return FileResponse(index_path)

        return JSONResponse({"error": "Not Found"}, status_code=404)

    logger.info(f"✓ FastAPI application created")
    logger.info(f"   API Docs: http://localhost:{settings.app.port}/docs")
    logger.info(f"   API v1: http://localhost:{settings.app.port}{API_V1_PREFIX}")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "src.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level="info" if settings.app.debug else "warning",
    )
