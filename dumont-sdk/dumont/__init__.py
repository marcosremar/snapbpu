"""
Dumont Cloud SDK - Python client for Dumont Cloud API

Usage:
    from dumont import DumontClient

    client = DumontClient(api_url="http://localhost:8000")
    client.auth.login("user@email.com", "password")

    # List instances
    instances = client.instances.list()

    # Pause an instance
    client.instances.pause(12345)

    # Deploy with wizard
    result = client.wizard.deploy(gpu="RTX 4090", max_price=1.5)
"""

from .client import DumontClient
from .exceptions import (
    DumontError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    APIError,
)

__version__ = "0.1.0"
__all__ = [
    "DumontClient",
    "DumontError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "APIError",
]
