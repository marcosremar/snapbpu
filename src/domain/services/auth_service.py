"""
Authentication Service - Domain Service (Business Logic)
Handles user authentication and session management
"""
import logging
from typing import Optional

from ..repositories import IUserRepository
from ..models import User
from ...core.exceptions import AuthenticationException, ValidationException

logger = logging.getLogger(__name__)


class AuthService:
    """
    Domain service for authentication.
    Handles login, logout, and user verification (Single Responsibility Principle).
    """

    def __init__(self, user_repository: IUserRepository):
        """
        Initialize auth service

        Args:
            user_repository: User repository implementation
        """
        self.user_repository = user_repository

    def login(self, email: str, password: str) -> User:
        """
        Authenticate a user

        Args:
            email: User email
            password: User password

        Returns:
            User object if authentication successful

        Raises:
            AuthenticationException: If credentials are invalid
        """
        if not email or not password:
            raise ValidationException("Email and password are required")

        user = self.user_repository.get_user(email)
        if not user:
            logger.warning(f"Login failed: user {email} not found")
            raise AuthenticationException("Invalid email or password")

        if not self.user_repository.verify_password(email, password):
            logger.warning(f"Login failed: invalid password for {email}")
            raise AuthenticationException("Invalid email or password")

        logger.info(f"User {email} logged in successfully")
        return user

    def register(self, email: str, password: str) -> User:
        """
        Register a new user

        Args:
            email: User email
            password: User password

        Returns:
            Created user

        Raises:
            ValidationException: If user already exists or input invalid
        """
        if not email or not password:
            raise ValidationException("Email and password are required")

        if len(password) < 6:
            raise ValidationException("Password must be at least 6 characters")

        user = self.user_repository.create_user(email, password)
        logger.info(f"User {email} registered successfully")
        return user

    def get_user(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.user_repository.get_user(email)

    def update_settings(self, email: str, settings: dict) -> User:
        """Update user settings"""
        return self.user_repository.update_settings(email, settings)

    def get_settings(self, email: str) -> dict:
        """Get user settings"""
        return self.user_repository.get_settings(email)
