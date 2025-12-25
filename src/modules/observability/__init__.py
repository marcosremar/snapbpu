"""
Observability Module - Monitoramento e Alertas

Este módulo consolida toda a observabilidade do sistema:
- Telemetria (métricas Prometheus)
- Health checks
- Alertas
- Dashboard data

Uso:
    from src.modules.observability import (
        TelemetryService,
        HealthChecker,
        AlertManager,
        get_telemetry,
    )

    # Registrar métricas
    telemetry = get_telemetry()
    telemetry.record_sync(machine_id="123", latency_seconds=2.5, bytes_transferred=1024*1024)

    # Verificar saúde
    checker = HealthChecker()
    health = await checker.check_all()

    # Gerenciar alertas
    alerts = AlertManager()
    alerts.trigger("high_latency", severity="warning", details={"latency": 5.0})
"""

from .models import (
    HealthStatus,
    AlertSeverity,
    Alert,
    HealthReport,
    ComponentHealth,
    MetricPoint,
)

from .telemetry import (
    TelemetryService,
    get_telemetry,
)

from .health import (
    HealthChecker,
    get_health_checker,
)

from .alerting import (
    AlertManager,
    get_alert_manager,
)

__all__ = [
    # Models
    "HealthStatus",
    "AlertSeverity",
    "Alert",
    "HealthReport",
    "ComponentHealth",
    "MetricPoint",
    # Telemetry
    "TelemetryService",
    "get_telemetry",
    # Health
    "HealthChecker",
    "get_health_checker",
    # Alerting
    "AlertManager",
    "get_alert_manager",
]
