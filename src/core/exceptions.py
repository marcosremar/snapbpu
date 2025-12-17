"""
Custom exceptions for Dumont Cloud
Follows hierarchy for proper error handling
"""


class DumontCloudException(Exception):
    """Base exception for all Dumont Cloud errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(DumontCloudException):
    """Raised when validation fails"""
    pass


class AuthenticationException(DumontCloudException):
    """Raised when authentication fails"""
    pass


class AuthorizationException(DumontCloudException):
    """Raised when user is not authorized"""
    pass


class NotFoundException(DumontCloudException):
    """Raised when resource is not found"""
    pass


class VastAPIException(DumontCloudException):
    """Raised when Vast.ai API calls fail"""
    pass


class SnapshotException(DumontCloudException):
    """Raised when snapshot operations fail"""
    pass


class SSHException(DumontCloudException):
    """Raised when SSH operations fail"""
    pass


class ConfigurationException(DumontCloudException):
    """Raised when configuration is invalid"""
    pass


class ServiceUnavailableException(DumontCloudException):
    """Raised when external service is unavailable"""
    pass
