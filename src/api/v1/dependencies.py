"""
FastAPI Dependencies (Dependency Injection)
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...core.config import get_settings
from ...core.jwt import create_access_token, verify_token
from ...domain.services import InstanceService, SnapshotService, AuthService, MigrationService, SyncService
from ...domain.repositories import IGpuProvider, ISnapshotProvider, IUserRepository
from ...infrastructure.providers import VastProvider, ResticProvider, FileUserRepository

# Security
security = HTTPBearer(auto_error=False)


# JWT-based Session Management
class SessionManager:
    """JWT-based session manager (stateless)"""

    def create_session(self, user_email: str) -> str:
        """Create a new JWT token for user"""
        return create_access_token(user_email)

    def get_user_email(self, token: str) -> Optional[str]:
        """Verify JWT and get user email"""
        return verify_token(token)

    def destroy_session(self, user_email: str):
        """JWT tokens are stateless - logout is handled client-side"""
        pass


# Global session manager instance
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get session manager instance"""
    return _session_manager


# Repository Dependencies

def get_user_repository() -> Generator[IUserRepository, None, None]:
    """Get user repository instance"""
    settings = get_settings()
    repo = FileUserRepository(config_file=settings.app.config_file)
    yield repo


# Authentication Dependencies (must be defined before service dependencies)

def get_current_user_email_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_manager: SessionManager = Depends(get_session_manager),
) -> Optional[str]:
    """Get current user email (returns None if not authenticated)"""
    # Check for demo mode (from env or query param)
    settings = get_settings()
    demo_param = request.query_params.get("demo", "").lower() == "true"

    if settings.app.demo_mode or demo_param:
        return "marcosremar@gmail.com"

    # Check Authorization header
    if credentials:
        token = credentials.credentials
        user_email = session_manager.get_user_email(token)
        if user_email:
            return user_email

    # Check session cookie (for compatibility with Flask)
    if hasattr(request.state, "user_email"):
        return request.state.user_email

    return None


def get_current_user_email(
    user_email: Optional[str] = Depends(get_current_user_email_optional),
) -> str:
    """Get current user email (raises exception if not authenticated)"""
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_email


def get_current_user(
    user_email: str = Depends(get_current_user_email),
    user_repo: IUserRepository = Depends(get_user_repository),
) -> any:
    """Get current user object (raises exception if not found)"""
    user = user_repo.get_user(user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def require_auth(
    user_email: str = Depends(get_current_user_email),
) -> str:
    """Require authentication (dependency for router)"""
    return user_email


# Service Dependencies

def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repository),
) -> AuthService:
    """Get authentication service"""
    return AuthService(user_repository=user_repo)


def get_instance_service(
    user_email: str = Depends(get_current_user_email),
) -> InstanceService:
    """Get instance service"""
    settings = get_settings()

    # In demo mode, use demo provider that returns mock data
    if settings.app.demo_mode:
        from ...infrastructure.providers.demo_provider import DemoProvider
        gpu_provider = DemoProvider()
        return InstanceService(gpu_provider=gpu_provider)

    # Get user's vast API key, fallback to env var
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    gpu_provider = VastProvider(api_key=api_key)
    return InstanceService(gpu_provider=gpu_provider)


def get_snapshot_service(
    user_email: str = Depends(get_current_user_email),
) -> SnapshotService:
    """Get snapshot service"""
    # Get user's settings
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get R2 credentials from user settings or use defaults
    settings = get_settings()
    repo = user.settings.get("restic_repo") or settings.r2.restic_repo
    password = user.settings.get("restic_password") or settings.restic.password
    access_key = user.settings.get("r2_access_key") or settings.r2.access_key
    secret_key = user.settings.get("r2_secret_key") or settings.r2.secret_key

    if not repo or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restic repository not configured. Please update settings.",
        )

    snapshot_provider = ResticProvider(
        repo=repo,
        password=password,
        access_key=access_key,
        secret_key=secret_key,
    )
    return SnapshotService(snapshot_provider=snapshot_provider)


def get_migration_service(
    user_email: str = Depends(get_current_user_email),
) -> MigrationService:
    """Get migration service"""
    from ...services.gpu.vast import VastService

    # Get user's settings
    settings = get_settings()
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    # Get settings for snapshot provider
    repo = (user.settings.get("restic_repo") if user else None) or settings.r2.restic_repo
    password = (user.settings.get("restic_password") if user else None) or settings.restic.password
    access_key = (user.settings.get("r2_access_key") if user else None) or settings.r2.access_key
    secret_key = (user.settings.get("r2_secret_key") if user else None) or settings.r2.secret_key

    # Create services
    gpu_provider = VastProvider(api_key=api_key)
    instance_service = InstanceService(gpu_provider=gpu_provider)

    snapshot_provider = ResticProvider(
        repo=repo,
        password=password,
        access_key=access_key,
        secret_key=secret_key,
    )
    snapshot_service = SnapshotService(snapshot_provider=snapshot_provider)

    # Direct vast service for CPU operations
    vast_service = VastService(api_key=api_key)

    return MigrationService(
        instance_service=instance_service,
        snapshot_service=snapshot_service,
        vast_service=vast_service,
    )


# Global sync service instance (to maintain state across requests)
_sync_service_instance: Optional[SyncService] = None


def get_sync_service(
    user_email: str = Depends(get_current_user_email),
) -> SyncService:
    """Get sync service (singleton to maintain sync state)"""
    global _sync_service_instance

    # Get user's settings
    settings = get_settings()
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    # Get settings for providers
    repo = (user.settings.get("restic_repo") if user else None) or settings.r2.restic_repo
    password = (user.settings.get("restic_password") if user else None) or settings.restic.password
    access_key = (user.settings.get("r2_access_key") if user else None) or settings.r2.access_key
    secret_key = (user.settings.get("r2_secret_key") if user else None) or settings.r2.secret_key

    # Create services
    gpu_provider = VastProvider(api_key=api_key)
    instance_service = InstanceService(gpu_provider=gpu_provider)

    snapshot_provider = ResticProvider(
        repo=repo,
        password=password,
        access_key=access_key,
        secret_key=secret_key,
    )
    snapshot_service = SnapshotService(snapshot_provider=snapshot_provider)

    # Create or reuse sync service
    if _sync_service_instance is None:
        _sync_service_instance = SyncService(
            snapshot_service=snapshot_service,
            instance_service=instance_service,
        )

    return _sync_service_instance


def get_job_manager(
    request: Request,
    user_email: str = Depends(get_current_user_email),
):
    """Get job manager service"""
    from ...services.job import JobManager
    import logging
    logger = logging.getLogger(__name__)

    settings = get_settings()

    # Check for demo mode (from env or query param)
    demo_param = request.query_params.get("demo", "").lower() == "true"
    is_demo = settings.app.demo_mode or demo_param
    logger.info(f"get_job_manager: demo_param={demo_param}, is_demo={is_demo}")

    # In demo mode, use demo provider
    if is_demo:
        logger.info("Using demo mode for JobManager")
        return JobManager(vast_api_key="demo", demo_mode=True)

    # Get user's vast API key, fallback to env var
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    # Try user's key first, then fall back to system key from .env
    api_key = (user.vast_api_key if user else None) or settings.vast.api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    return JobManager(vast_api_key=api_key)
