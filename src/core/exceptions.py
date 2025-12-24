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


class InsufficientBalanceException(VastAPIException):
    """Raised when user doesn't have enough balance"""
    def __init__(self, required: float = 0, available: float = 0):
        self.required = required
        self.available = available
        message = f"Saldo insuficiente. Disponível: ${available:.2f}, Necessário: ${required:.2f}"
        super().__init__(message, {"required": required, "available": available})


class OfferUnavailableException(VastAPIException):
    """Raised when a GPU offer is no longer available"""
    def __init__(self, offer_id: int, reason: str = ""):
        self.offer_id = offer_id
        reasons = {
            "rented": "A máquina já foi alugada por outro usuário",
            "offline": "O host saiu do ar temporariamente",
            "maintenance": "O host está em manutenção",
            "price_changed": "O preço da oferta mudou",
            "": "A oferta não está mais disponível"
        }
        human_reason = reasons.get(reason, reason or reasons[""])
        message = f"Oferta {offer_id} indisponível: {human_reason}"
        super().__init__(message, {"offer_id": offer_id, "reason": reason})


class RateLimitException(VastAPIException):
    """Raised when API rate limit is exceeded"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        message = f"Limite de requisições excedido. Tente novamente em {retry_after} segundos"
        super().__init__(message, {"retry_after": retry_after})


class InvalidOfferException(VastAPIException):
    """Raised when offer parameters are invalid"""
    def __init__(self, reason: str):
        message = f"Parâmetros da oferta inválidos: {reason}"
        super().__init__(message, {"reason": reason})


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


class MigrationException(DumontCloudException):
    """Raised when instance migration fails"""
    pass
