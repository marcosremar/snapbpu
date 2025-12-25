"""
Observability Models - Dataclasses para monitoramento
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Status de saúde"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    """Severidade de alerta"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Ponto de métrica"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit,
        }


@dataclass
class ComponentHealth:
    """Saúde de um componente"""
    name: str
    status: HealthStatus
    message: str = ""
    last_check: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "last_check": self.last_check.isoformat(),
            "response_time_ms": self.response_time_ms,
            "details": self.details,
        }


@dataclass
class HealthReport:
    """Relatório de saúde do sistema"""
    overall_status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.now)
    components: List[ComponentHealth] = field(default_factory=list)
    uptime_seconds: float = 0.0
    version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp.isoformat(),
            "components": [c.to_dict() for c in self.components],
            "uptime_seconds": self.uptime_seconds,
            "version": self.version,
        }


@dataclass
class Alert:
    """Alerta do sistema"""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    source: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None

    @property
    def duration_seconds(self) -> float:
        end = self.resolved_at or datetime.now()
        return (end - self.triggered_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "source": self.source,
            "details": self.details,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "is_resolved": self.is_resolved,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class AlertRule:
    """Regra de alerta"""
    name: str
    condition: str  # Ex: "latency > 5s"
    severity: AlertSeverity
    message_template: str
    cooldown_seconds: int = 300  # Tempo mínimo entre alertas
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "condition": self.condition,
            "severity": self.severity.value,
            "message_template": self.message_template,
            "cooldown_seconds": self.cooldown_seconds,
            "enabled": self.enabled,
            "labels": self.labels,
        }


@dataclass
class DashboardData:
    """Dados para dashboard"""
    timestamp: datetime = field(default_factory=datetime.now)

    # Métricas de sistema
    active_machines: int = 0
    active_gpus: int = 0
    total_cost_hourly: float = 0.0

    # Health
    healthy_components: int = 0
    degraded_components: int = 0
    unhealthy_components: int = 0

    # Alertas
    active_alerts: int = 0
    critical_alerts: int = 0

    # Performance
    avg_sync_latency_ms: float = 0.0
    failover_success_rate: float = 1.0

    # Economia
    savings_today_usd: float = 0.0
    savings_month_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "machines": {
                "active": self.active_machines,
                "gpus": self.active_gpus,
                "cost_hourly": self.total_cost_hourly,
            },
            "health": {
                "healthy": self.healthy_components,
                "degraded": self.degraded_components,
                "unhealthy": self.unhealthy_components,
            },
            "alerts": {
                "active": self.active_alerts,
                "critical": self.critical_alerts,
            },
            "performance": {
                "avg_sync_latency_ms": self.avg_sync_latency_ms,
                "failover_success_rate": self.failover_success_rate,
            },
            "savings": {
                "today_usd": self.savings_today_usd,
                "month_usd": self.savings_month_usd,
            },
        }
