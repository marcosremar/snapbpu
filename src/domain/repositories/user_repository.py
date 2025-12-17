"""
Abstract interface for user storage (Dependency Inversion Principle)
Allows swapping between file-based, database, or external auth providers
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..models import User


class IUserRepository(ABC):
    """Abstract interface for user storage"""

    @abstractmethod
    def get_user(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    def create_user(self, email: str, password: str) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    def update_user(self, email: str, updates: Dict[str, Any]) -> User:
        """Update user information"""
        pass

    @abstractmethod
    def delete_user(self, email: str) -> bool:
        """Delete a user"""
        pass

    @abstractmethod
    def verify_password(self, email: str, password: str) -> bool:
        """Verify user password"""
        pass

    @abstractmethod
    def update_settings(self, email: str, settings: Dict[str, Any]) -> User:
        """Update user settings"""
        pass

    @abstractmethod
    def get_settings(self, email: str) -> Dict[str, Any]:
        """Get user settings"""
        pass
