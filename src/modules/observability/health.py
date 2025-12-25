"""
Health Checker - Verificação de saúde do sistema
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from .models import HealthStatus, HealthReport, ComponentHealth

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Verificador de saúde do sistema.

    Verifica saúde de componentes:
    - Database
    - Redis/Cache
    - GPU providers (Vast, TensorDock)
    - External APIs

    Uso:
        checker = get_health_checker()

        # Registrar checks customizados
        checker.register("my_service", my_health_check_func)

        # Verificar tudo
        report = await checker.check_all()
        if report.overall_status == HealthStatus.HEALTHY:
            print("All systems operational")
    """

    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._last_report: Optional[HealthReport] = None
        self._start_time = time.time()
        self._version = "1.0.0"

        # Registrar checks padrão
        self._register_default_checks()

    def _register_default_checks(self):
        """Registra health checks padrão"""
        self.register("database", self._check_database)
        self.register("vast_api", self._check_vast_api)
        self.register("storage", self._check_storage)

    def register(
        self,
        name: str,
        check_func: Callable[[], ComponentHealth],
    ):
        """
        Registra um health check.

        Args:
            name: Nome do componente
            check_func: Função que retorna ComponentHealth
        """
        self._checks[name] = check_func
        logger.debug(f"[HEALTH] Registered check: {name}")

    def unregister(self, name: str):
        """Remove um health check"""
        if name in self._checks:
            del self._checks[name]

    async def check_all(self) -> HealthReport:
        """
        Executa todos os health checks.

        Returns:
            HealthReport com status de todos os componentes
        """
        components = []
        start = time.time()

        for name, check_func in self._checks.items():
            try:
                check_start = time.time()

                # Executar check (sync ou async)
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                result.response_time_ms = (time.time() - check_start) * 1000
                components.append(result)

            except Exception as e:
                logger.error(f"[HEALTH] Check failed for {name}: {e}")
                components.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                ))

        # Determinar status geral
        overall = self._calculate_overall_status(components)

        report = HealthReport(
            overall_status=overall,
            components=components,
            uptime_seconds=time.time() - self._start_time,
            version=self._version,
        )

        self._last_report = report
        return report

    async def check_component(self, name: str) -> Optional[ComponentHealth]:
        """Verifica um componente específico"""
        if name not in self._checks:
            return None

        check_func = self._checks[name]
        try:
            if asyncio.iscoroutinefunction(check_func):
                return await check_func()
            return check_func()
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )

    def _calculate_overall_status(
        self,
        components: List[ComponentHealth]
    ) -> HealthStatus:
        """Calcula status geral baseado nos componentes"""
        if not components:
            return HealthStatus.UNKNOWN

        statuses = [c.status for c in components]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    def get_last_report(self) -> Optional[HealthReport]:
        """Retorna último relatório de saúde"""
        return self._last_report

    # === CHECKS PADRÃO ===

    def _check_database(self) -> ComponentHealth:
        """Verifica conexão com banco de dados"""
        try:
            from src.config.database import get_session_factory

            session = get_session_factory()()
            session.execute("SELECT 1")
            session.close()

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection OK",
            )
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)[:100]}",
            )

    def _check_vast_api(self) -> ComponentHealth:
        """Verifica API da Vast.ai"""
        try:
            import os
            import requests

            api_key = os.getenv("VAST_API_KEY")
            if not api_key:
                return ComponentHealth(
                    name="vast_api",
                    status=HealthStatus.DEGRADED,
                    message="VAST_API_KEY not configured",
                )

            # Quick check - não faz request real para economizar
            return ComponentHealth(
                name="vast_api",
                status=HealthStatus.HEALTHY,
                message="Vast API configured",
                details={"api_key_present": True},
            )
        except Exception as e:
            return ComponentHealth(
                name="vast_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Vast API error: {str(e)[:100]}",
            )

    def _check_storage(self) -> ComponentHealth:
        """Verifica storage backends"""
        try:
            import os

            # Verificar configuração de storage
            b2_key = os.getenv("B2_APPLICATION_KEY_ID")
            r2_key = os.getenv("R2_ACCESS_KEY_ID")

            if b2_key or r2_key:
                return ComponentHealth(
                    name="storage",
                    status=HealthStatus.HEALTHY,
                    message="Storage configured",
                    details={
                        "b2_configured": bool(b2_key),
                        "r2_configured": bool(r2_key),
                    },
                )
            else:
                return ComponentHealth(
                    name="storage",
                    status=HealthStatus.DEGRADED,
                    message="No storage backend configured",
                )
        except Exception as e:
            return ComponentHealth(
                name="storage",
                status=HealthStatus.UNHEALTHY,
                message=f"Storage error: {str(e)[:100]}",
            )


# Singleton
_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Obtém instância do HealthChecker"""
    global _checker
    if _checker is None:
        _checker = HealthChecker()
    return _checker
