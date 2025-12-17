"""
Domain model for users
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class User:
    """Represents a user in the system"""
    email: str
    password_hash: str
    vast_api_key: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary (excludes password_hash for security)"""
        return {
            'email': self.email,
            'vast_api_key': self.vast_api_key,
            'settings': self.settings,
        }

    @property
    def restic_repo(self) -> Optional[str]:
        """Get restic repository from settings"""
        return self.settings.get('restic_repo')

    @property
    def restic_password(self) -> Optional[str]:
        """Get restic password from settings"""
        return self.settings.get('restic_password')

    @property
    def r2_access_key(self) -> Optional[str]:
        """Get R2 access key from settings"""
        return self.settings.get('r2_access_key')

    @property
    def r2_secret_key(self) -> Optional[str]:
        """Get R2 secret key from settings"""
        return self.settings.get('r2_secret_key')
