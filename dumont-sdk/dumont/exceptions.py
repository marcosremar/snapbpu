"""Dumont SDK Exceptions"""


class DumontError(Exception):
    """Base exception for all Dumont SDK errors"""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(DumontError):
    """Raised when authentication fails or token is invalid"""
    pass


class NotFoundError(DumontError):
    """Raised when a resource is not found (404)"""
    pass


class ValidationError(DumontError):
    """Raised when request validation fails (400/422)"""
    pass


class RateLimitError(DumontError):
    """Raised when rate limit is exceeded (429)"""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class APIError(DumontError):
    """Raised for general API errors (500, etc)"""
    pass


class ConnectionError(DumontError):
    """Raised when connection to API fails"""
    pass
