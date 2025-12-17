"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..schemas.request import LoginRequest, RegisterRequest
from ..schemas.response import LoginResponse, AuthMeResponse, SuccessResponse
from ....domain.services import AuthService
from ....core.exceptions import AuthenticationException, ValidationException
from ..dependencies import get_auth_service, get_current_user_email, get_session_manager, SessionManager

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Login endpoint

    Authenticates user and creates session.
    """
    try:
        user = auth_service.login(request.username, request.password)

        # Create session
        session_token = session_manager.create_session(user.email)

        return LoginResponse(
            success=True,
            user=user.email,
            token=session_token,
        )
    except (AuthenticationException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    session_manager: SessionManager = Depends(get_session_manager),
    user_email: str = Depends(get_current_user_email),
):
    """
    Logout endpoint

    Destroys user session.
    """
    session_manager.destroy_session(user_email)
    return SuccessResponse(success=True, message="Logged out successfully")


@router.get("/me", response_model=AuthMeResponse)
async def get_current_user(
    user_email: str = Depends(get_current_user_email),
):
    """
    Get current authenticated user

    Returns user information if authenticated.
    """
    if user_email:
        return AuthMeResponse(authenticated=True, user=user_email)
    return AuthMeResponse(authenticated=False)


@router.post("/register", response_model=LoginResponse)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Register new user

    Creates a new user account.
    """
    try:
        user = auth_service.register(request.email, request.password)

        # Auto-login after registration
        session_token = session_manager.create_session(user.email)

        return LoginResponse(
            success=True,
            user=user.email,
            token=session_token,
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
