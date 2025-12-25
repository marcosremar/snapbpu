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

    # Initialize background agents
    agents_started = []
    try:
        settings = get_settings()
        vast_api_key = os.environ.get("VAST_API_KEY", "")
        
        # Initialize CPU Standby Manager
        try:
            from .services.standby.manager import get_standby_manager
            gcp_credentials_json = os.environ.get("GCP_CREDENTIALS", "")

            if gcp_credentials_json and vast_api_key:
                import json
                gcp_creds = json.loads(gcp_credentials_json)

                standby_mgr = get_standby_manager()
                standby_mgr.configure(
                    gcp_credentials=gcp_creds,
                    vast_api_key=vast_api_key,
                    auto_standby_enabled=os.environ.get("AUTO_STANDBY_ENABLED", "true").lower() == "true",
                    config={
                        "gcp_zone": os.environ.get("GCP_ZONE", "europe-west1-b"),
                        "gcp_machine_type": os.environ.get("GCP_MACHINE_TYPE", "e2-medium"),
                        "gcp_disk_size": int(os.environ.get("GCP_DISK_SIZE", "100")),
                        "gcp_spot": os.environ.get("GCP_SPOT", "true").lower() == "true",
                        "sync_interval_seconds": int(os.environ.get("SYNC_INTERVAL", "30")),
                        "health_check_interval": int(os.environ.get("HEALTH_CHECK_INTERVAL", "10")),
                        "failover_threshold": int(os.environ.get("FAILOVER_THRESHOLD", "3")),
                        "auto_failover": os.environ.get("AUTO_FAILOVER", "true").lower() == "true",
                        "auto_recovery": os.environ.get("AUTO_RECOVERY", "true").lower() == "true",
                    }
                )
                agents_started.append("StandbyManager")
                logger.info("✓ CPU Standby Manager configured and ready")
            else:
                logger.warning("⚠ CPU Standby Manager not initialized (missing GCP_CREDENTIALS or VAST_API_KEY)")
        except Exception as e:
            logger.error(f"✗ Error initializing CPU Standby Manager: {e}")

        # Initialize Market Monitor Agent (se houver database)
        try:
            from .modules.market import get_market_agent
            from .config.database import SessionLocal

            # Test database connection
            db = SessionLocal()
            db.close()

            if vast_api_key:
                market_agent = get_market_agent(
                    interval_minutes=5,
                    vast_api_key=vast_api_key,
                )
                market_agent.start()
                agents_started.append("MarketMonitorAgent")
                logger.info("✓ MarketMonitorAgent started")
        except Exception as e:
            logger.warning(f"⚠ MarketMonitorAgent not started: {e}")

        # Initialize Periodic Snapshot Service
        try:
            from .services.standby.periodic_snapshots import get_periodic_snapshot_service
            from .services.gpu.snapshot import GPUSnapshotService

            b2_endpoint = os.environ.get("B2_ENDPOINT", "")
            b2_bucket = os.environ.get("B2_BUCKET", "")
            snapshot_interval = int(os.environ.get("PERIODIC_SNAPSHOT_INTERVAL_MINUTES", "60"))

            if b2_endpoint and b2_bucket:
                snapshot_service = GPUSnapshotService(
                    r2_endpoint=b2_endpoint,
                    r2_bucket=b2_bucket
                )
                periodic_snapshot = get_periodic_snapshot_service(
                    snapshot_service=snapshot_service,
                    interval_minutes=snapshot_interval,
                    keep_last_n=24  # Keep last 24 snapshots (1 day at 1/hour)
                )
                # Note: start() is async, will be called separately if needed
                # For now, the service is created and ready to use via API
                agents_started.append(f"PeriodicSnapshotService ({snapshot_interval}min)")
                logger.info(f"✓ PeriodicSnapshotService configured (interval: {snapshot_interval}min)")
            else:
                logger.warning("⚠ PeriodicSnapshotService not started (missing B2_ENDPOINT or B2_BUCKET)")
        except Exception as e:
            logger.warning(f"⚠ PeriodicSnapshotService not started: {e}")

        logger.info(f"   Started agents: {', '.join(agents_started) if agents_started else 'None'}")
        
    except Exception as e:
        logger.error(f"Error initializing agents: {e}")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Dumont Cloud FastAPI application...")
    
    # Stop background agents
    try:
        from .services.standby.hibernation import get_auto_hibernation_manager
        manager = get_auto_hibernation_manager()
        if manager:
            manager.stop()
            logger.info("✓ AutoHibernationManager stopped")
    except Exception as e:
        logger.error(f"Error stopping agents: {e}")



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

    # Live Docs API functions (defined before api_router to avoid conflicts)
    def get_menu_structure_docs(path):
        """
        Recursively scans the directory to build the menu structure.
        Returns a list of dicts: {name: str, type: 'file'|'dir', path: str, children: []}
        """
        items = []
        content_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Live-Doc", "content")

        if not os.path.exists(path):
            return items

        for entry in sorted(os.listdir(path)):
            if entry.startswith('.'):
                continue

            full_path = os.path.join(path, entry)
            relative_path = os.path.relpath(full_path, content_dir)

            if os.path.isdir(full_path):
                items.append({
                    "name": entry,
                    "type": "dir",
                    "path": relative_path,
                    "children": get_menu_structure_docs(full_path)
                })
            elif entry.endswith(".md"):
                # Remove extension for display, keep relative path for ID
                display_name = os.path.splitext(entry)[0].replace('_', ' ')
                items.append({
                    "name": display_name,
                    "type": "file",
                    "path": relative_path,
                    "id": relative_path
                })

        return items

    @app.get("/api/menu", tags=["docs"])
    async def get_menu():
        """Returns the directory structure as JSON for the sidebar"""
        content_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Live-Doc", "content")
        return {"menu": get_menu_structure_docs(content_dir)}

    @app.get("/api/content/{path:path}", tags=["docs"])
    async def get_content(path: str):
        """Fetches markdown content by relative path"""
        from fastapi.exceptions import HTTPException

        base_dir = os.path.dirname(os.path.dirname(__file__))
        content_dir = os.path.join(base_dir, "Live-Doc", "content")

        # Security: Prevent directory traversal
        safe_path = os.path.normpath(os.path.join(content_dir, path))
        if not safe_path.startswith(content_dir):
            raise HTTPException(status_code=403, detail="Access denied")

        if os.path.exists(safe_path) and os.path.isfile(safe_path):
            with open(safe_path, "r", encoding="utf-8") as f:
                return {"content": f.read()}

        raise HTTPException(status_code=404, detail="Document not found")

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

    # Marketing Live Docs (Standalone HTML)
    @app.get("/admin/doc/live", response_class=HTMLResponse)
    async def admin_doc_live():
        """Serve separate Marketing Live Docs"""
        template_path = os.path.join(os.path.dirname(__file__), "templates", "marketing_doc.html")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        from fastapi.responses import Response
        return Response("<h1>Template not found</h1>", status_code=404, media_type="text/html")

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
    async def serve_spa(full_path: str, request: Request):
        """Serve React SPA for all non-API routes"""
        # Skip API routes - they should be handled by the router
        # If we get here with an API route, it means the route doesn't exist
        if full_path.startswith("api/") or full_path.startswith("api"):
            # Don't serve SPA for API routes - return proper 404
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"API endpoint not found: /{full_path}")

        # Skip special routes
        if full_path in ["docs", "redoc", "openapi.json", "health"]:
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
