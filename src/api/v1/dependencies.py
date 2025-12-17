"""
FastAPI Dependencies (Dependency Injection)
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...core.config import get_settings
from ...core.jwt import create_access_token, verify_token
from ...domain.services import InstanceService, SnapshotService, AuthService
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
    # Check for demo mode
    settings = get_settings()
    if settings.app.demo_mode:
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
    # Get user's vast API key
    user_repo = next(get_user_repository())
    user = user_repo.get_user(user_email)

    if not user or not user.vast_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vast.ai API key not configured. Please update settings.",
        )

    gpu_provider = VastProvider(api_key=user.vast_api_key)
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
