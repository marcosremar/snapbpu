"""
Alert Manager - Sistema de alertas
"""

import uuid
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict

from .models import Alert, AlertSeverity, AlertRule

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Gerenciador de alertas do sistema.

    Funcionalidades:
    - Criar e resolver alertas
    - Cooldown para evitar spam
    - Callbacks para notificações
    - Histórico de alertas

    Uso:
        manager = get_alert_manager()

        # Registrar callback
        manager.on_alert(lambda alert: send_slack_notification(alert))

        # Disparar alerta
        manager.trigger(
            name="high_latency",
            severity=AlertSeverity.WARNING,
            message="Sync latency is 5s",
            source="sync_service",
        )

        # Resolver alerta
        manager.resolve(alert_id)
    """

    def __init__(self):
        self._alerts: Dict[str, Alert] = {}  # alert_id -> Alert
        self._rules: Dict[str, AlertRule] = {}
        self._callbacks: List[Callable[[Alert], None]] = []
        self._last_triggered: Dict[str, datetime] = defaultdict(lambda: datetime.min)
        self._history: List[Alert] = []
        self._max_history = 1000

    def on_alert(self, callback: Callable[[Alert], None]):
        """Registra callback para alertas"""
        self._callbacks.append(callback)

    def add_rule(self, rule: AlertRule):
        """Adiciona regra de alerta"""
        self._rules[rule.name] = rule

    def trigger(
        self,
        name: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        message: str = "",
        source: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """
        Dispara um alerta.

        Args:
            name: Nome do alerta
            severity: Severidade
            message: Mensagem descritiva
            source: Origem do alerta
            details: Detalhes adicionais

        Returns:
            Alert criado ou None se em cooldown
        """
        # Verificar cooldown
        rule = self._rules.get(name)
        cooldown = rule.cooldown_seconds if rule else 300

        last = self._last_triggered[name]
        if datetime.now() - last < timedelta(seconds=cooldown):
            logger.debug(f"[ALERTING] Alert {name} in cooldown")
            return None

        # Verificar se regra está desabilitada
        if rule and not rule.enabled:
            return None

        # Criar alerta
        alert = Alert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            name=name,
            severity=severity,
            message=message,
            source=source,
            details=details or {},
        )

        self._alerts[alert.alert_id] = alert
        self._last_triggered[name] = datetime.now()

        logger.warning(f"[ALERTING] Alert triggered: {name} ({severity.value}): {message}")

        # Notificar callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"[ALERTING] Callback error: {e}")

        return alert

    def resolve(
        self,
        alert_id: str,
        message: str = "",
    ) -> Optional[Alert]:
        """
        Resolve um alerta.

        Args:
            alert_id: ID do alerta
            message: Mensagem de resolução

        Returns:
            Alert resolvido ou None se não encontrado
        """
        if alert_id not in self._alerts:
            return None

        alert = self._alerts[alert_id]
        alert.resolved_at = datetime.now()

        if message:
            alert.details["resolution"] = message

        # Mover para histórico
        self._history.append(alert)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        del self._alerts[alert_id]

        logger.info(f"[ALERTING] Alert resolved: {alert.name}")
        return alert

    def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> Optional[Alert]:
        """
        Reconhece um alerta.

        Args:
            alert_id: ID do alerta
            acknowledged_by: Quem reconheceu

        Returns:
            Alert atualizado
        """
        if alert_id not in self._alerts:
            return None

        alert = self._alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by

        logger.info(f"[ALERTING] Alert acknowledged: {alert.name} by {acknowledged_by}")
        return alert

    def get_active(
        self,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
    ) -> List[Alert]:
        """
        Obtém alertas ativos.

        Args:
            severity: Filtrar por severidade
            source: Filtrar por origem

        Returns:
            Lista de alertas ativos
        """
        alerts = list(self._alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if source:
            alerts = [a for a in alerts if a.source == source]

        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def get_history(
        self,
        hours: int = 24,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        """
        Obtém histórico de alertas.

        Args:
            hours: Horas de histórico
            severity: Filtrar por severidade

        Returns:
            Lista de alertas
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        alerts = [a for a in self._history if a.triggered_at >= cutoff]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def get_summary(self) -> Dict[str, Any]:
        """Obtém resumo de alertas"""
        active = list(self._alerts.values())

        by_severity = defaultdict(int)
        for alert in active:
            by_severity[alert.severity.value] += 1

        return {
            "total_active": len(active),
            "by_severity": dict(by_severity),
            "critical_count": by_severity.get("critical", 0),
            "unacknowledged": len([a for a in active if not a.acknowledged]),
            "oldest_alert": min(
                [a.triggered_at for a in active],
                default=None
            ),
        }

    def clear_all(self, move_to_history: bool = True):
        """Limpa todos os alertas ativos"""
        if move_to_history:
            for alert in self._alerts.values():
                alert.resolved_at = datetime.now()
                alert.details["resolution"] = "Cleared by admin"
                self._history.append(alert)

        self._alerts.clear()
        logger.info("[ALERTING] All alerts cleared")


# Singleton
_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Obtém instância do AlertManager"""
    global _manager
    if _manager is None:
        _manager = AlertManager()
    return _manager
