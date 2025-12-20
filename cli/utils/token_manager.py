"""Token management for Dumont CLI"""
from pathlib import Path
from typing import Optional


TOKEN_FILE = Path.home() / ".dumont_token"
CONFIG_FILE = Path.home() / ".dumont_config"


class TokenManager:
    """Manage authentication tokens"""

    def __init__(self):
        self.token: Optional[str] = None

    def load(self) -> Optional[str]:
        """Load saved token from file"""
        if TOKEN_FILE.exists():
            self.token = TOKEN_FILE.read_text().strip()
            return self.token
        return None

    def save(self, token: str):
        """Save token to file"""
        TOKEN_FILE.write_text(token)
        TOKEN_FILE.chmod(0o600)  # Secure permissions
        self.token = token

    def clear(self):
        """Remove saved token"""
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        self.token = None

    def get(self) -> Optional[str]:
        """Get current token (load if not in memory)"""
        if not self.token:
            return self.load()
        return self.token
