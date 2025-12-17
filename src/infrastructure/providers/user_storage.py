"""
File-based User Storage Implementation
Implements IUserRepository interface (Dependency Inversion Principle)
"""
import json
import os
import hashlib
import logging
from typing import Optional, Dict, Any

from ...core.exceptions import NotFoundException, ValidationException
from ...domain.repositories import IUserRepository
from ...domain.models import User

logger = logging.getLogger(__name__)


class FileUserRepository(IUserRepository):
    """
    File-based implementation of IUserRepository.
    Stores users in a JSON file (config.json).
    """

    def __init__(self, config_file: str = "config.json"):
        """
        Initialize file-based user storage

        Args:
            config_file: Path to config file (relative to project root)
        """
        self.config_file = config_file
        self._ensure_config_exists()

    def get_user(self, email: str) -> Optional[User]:
        """Get user by email"""
        config = self._load_config()
        user_data = config.get("users", {}).get(email)

        if not user_data:
            return None

        return User(
            email=email,
            password_hash=user_data.get("password", ""),
            vast_api_key=user_data.get("vast_api_key"),
            settings=user_data.get("settings", {}),
        )

    def create_user(self, email: str, password: str) -> User:
        """Create a new user"""
        if not email or not password:
            raise ValidationException("Email and password are required")

        config = self._load_config()

        if "users" not in config:
            config["users"] = {}

        if email in config["users"]:
            raise ValidationException(f"User {email} already exists")

        password_hash = self._hash_password(password)

        config["users"][email] = {
            "password": password_hash,
            "vast_api_key": None,
            "settings": {},
        }

        self._save_config(config)
        logger.info(f"User {email} created")

        return User(
            email=email,
            password_hash=password_hash,
            vast_api_key=None,
            settings={},
        )

    def update_user(self, email: str, updates: Dict[str, Any]) -> User:
        """Update user information"""
        config = self._load_config()

        if "users" not in config or email not in config["users"]:
            raise NotFoundException(f"User {email} not found")

        user_data = config["users"][email]

        # Update allowed fields
        if "vast_api_key" in updates:
            user_data["vast_api_key"] = updates["vast_api_key"]

        if "settings" in updates:
            user_data["settings"] = updates["settings"]

        if "password" in updates:
            user_data["password"] = self._hash_password(updates["password"])

        config["users"][email] = user_data
        self._save_config(config)
        logger.info(f"User {email} updated")

        return self.get_user(email)

    def delete_user(self, email: str) -> bool:
        """Delete a user"""
        config = self._load_config()

        if "users" not in config or email not in config["users"]:
            return False

        del config["users"][email]
        self._save_config(config)
        logger.info(f"User {email} deleted")

        return True

    def verify_password(self, email: str, password: str) -> bool:
        """Verify user password"""
        user = self.get_user(email)
        if not user:
            return False

        password_hash = self._hash_password(password)
        return user.password_hash == password_hash

    def update_settings(self, email: str, settings: Dict[str, Any]) -> User:
        """Update user settings"""
        return self.update_user(email, {"settings": settings})

    def get_settings(self, email: str) -> Dict[str, Any]:
        """Get user settings"""
        user = self.get_user(email)
        if not user:
            raise NotFoundException(f"User {email} not found")
        return user.settings

    # Helper methods

    def _ensure_config_exists(self):
        """Ensure config file exists"""
        if not os.path.exists(self.config_file):
            self._save_config({"users": {}})

    def _load_config(self) -> Dict[str, Any]:
        """Load config from file"""
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"users": {}}
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {self.config_file}, starting fresh")
            return {"users": {}}

    def _save_config(self, config: Dict[str, Any]):
        """Save config to file"""
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)

    def _hash_password(self, password: str) -> str:
        """Hash a password (simple SHA-256 for now)"""
        # NOTE: In production, use bcrypt or argon2
        return hashlib.sha256(password.encode()).hexdigest()
