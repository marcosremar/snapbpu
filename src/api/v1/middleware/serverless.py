"""
Serverless Middleware

Middleware para tracking de requests em instâncias serverless.
Integra com ServerlessService para auto-pause/resume baseado em atividade.

Uso:
    from src.api.v1.middleware.serverless import ServerlessMiddleware

    app = FastAPI()
    app.add_middleware(ServerlessMiddleware)
"""

import logging
import time
from typing import Optional, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Global reference to ServerlessService (initialized by setup_serverless_middleware)
_serverless_service = None


def setup_serverless_middleware(app: FastAPI, service) -> None:
    """
    Configura middleware de serverless na aplicação.

    Args:
        app: Aplicação FastAPI
        service: Instância de ServerlessService
    """
    global _serverless_service
    _serverless_service = service

    app.add_middleware(ServerlessMiddleware)
    logger.info("Serverless middleware configured")


def get_serverless_service():
    """Retorna serviço serverless configurado"""
    return _serverless_service


class ServerlessMiddleware(BaseHTTPMiddleware):
    """
    Middleware para tracking de requests em instâncias serverless.

    Funcionalidades:
    - Detecta instance_id da requisição (header ou path)
    - Chama on_request_start() para acordar instância se pausada
    - Chama on_request_end() para resetar idle timer
    - Mede latência e cold start

    Headers suportados:
    - X-Instance-Id: ID da instância VAST.ai
    - X-Serverless-Enabled: Se "true", força tracking mesmo sem instance_id
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extrair instance_id
        instance_id = self._get_instance_id(request)

        if not instance_id or not _serverless_service:
            return await call_next(request)

        start_time = time.time()
        cold_start_seconds = 0
        was_paused = False

        try:
            # Notificar início da requisição (pode acordar instância)
            result = _serverless_service.on_request_start(instance_id)

            if result and result.success:
                was_paused = True
                cold_start_seconds = result.cold_start_seconds
                logger.info(
                    f"Instance {instance_id} woken up in {cold_start_seconds:.2f}s "
                    f"(method: {result.method})"
                )

        except Exception as e:
            logger.error(f"Error in serverless request_start for {instance_id}: {e}")

        # Processar requisição
        response = await call_next(request)

        try:
            # Notificar fim da requisição (reseta idle timer)
            _serverless_service.on_request_end(instance_id)

        except Exception as e:
            logger.error(f"Error in serverless request_end for {instance_id}: {e}")

        # Adicionar headers de debug
        total_time = time.time() - start_time
        response.headers["X-Serverless-Instance"] = str(instance_id)
        response.headers["X-Serverless-Cold-Start"] = str(was_paused)

        if was_paused:
            response.headers["X-Serverless-Cold-Start-Seconds"] = f"{cold_start_seconds:.3f}"

        response.headers["X-Serverless-Total-Time"] = f"{total_time:.3f}"

        return response

    def _get_instance_id(self, request: Request) -> Optional[int]:
        """
        Extrai instance_id da requisição.

        Ordem de precedência:
        1. Header X-Instance-Id
        2. Path parameter /api/v1/.../instances/{id}
        3. Query parameter ?instance_id=...
        """
        # 1. Header
        header_id = request.headers.get("X-Instance-Id")
        if header_id and header_id.isdigit():
            return int(header_id)

        # 2. Path parameter
        path = request.url.path
        if "/instances/" in path:
            parts = path.split("/instances/")
            if len(parts) > 1:
                id_part = parts[1].split("/")[0]
                if id_part.isdigit():
                    return int(id_part)

        # 3. Query parameter
        query_id = request.query_params.get("instance_id")
        if query_id and query_id.isdigit():
            return int(query_id)

        return None


# Dependency para injetar serviço em endpoints
async def get_serverless_service_dependency():
    """
    FastAPI Dependency para injetar ServerlessService.

    Uso:
        @router.get("/status")
        async def get_status(
            service: ServerlessService = Depends(get_serverless_service_dependency)
        ):
            return service.get_user_stats(...)
    """
    if not _serverless_service:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serverless service not configured"
        )
    return _serverless_service
