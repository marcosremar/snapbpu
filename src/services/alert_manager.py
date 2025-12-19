"""
Alert Manager - Sistema de alertas proativos para Dumont Cloud
Monitora métricas e envia notificações quando thresholds são ultrapassados
"""

import requests
import logging
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time
import threading

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Representa um alerta"""
    severity: str  # 'critical', 'warning', 'info'
    title: str
    message: str
    machine_id: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """Converte para dict"""
        return {
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'machine_id': self.machine_id,
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'threshold': self.threshold,
            'timestamp': self.timestamp,
           'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat()
        }


@dataclass
class AlertRule:
    """Define uma regra de alerta"""
    name: str
    metric_name: str
    condition: Callable[[float], bool]
    severity: str
    message_template: str
    threshold: Optional[float] = None
    cooldown_seconds: int = 300  # Não alertar novamente por 5min
    
    def check(self, value: float, machine_id: str = 'unknown') -> Optional[Alert]:
        """Verifica se condição é atendida e cria alerta"""
        if self.condition(value):
            return Alert(
                severity=self.severity,
                title=self.name,
                message=self.message_template.format(
                    value=value,
                    threshold=self.threshold or 'N/A'
                ),
                machine_id=machine_id,
                metric_name=self.metric_name,
                current_value=value,
                threshold=self.threshold or 0
            )
        return None


class AlertManager:
    """
    Gerenciador de alertas proativos.
    
    Monitora métricas e envia notificações via:
    - Slack
    - Email (futuro)
    - Webhook genérico
    """
    
    def __init__(
        self,
        slack_webhook: Optional[str] = None,
        email_config: Optional[Dict] = None,
        webhook_url: Optional[str] = None
    ):
        self.slack_webhook = slack_webhook
        self.email_config = email_config
        self.webhook_url = webhook_url
        
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.last_alert_time: Dict[str, float] = {}
        
        self._define_default_rules()
        
        logger.info("🚨 AlertManager initialized")
    
    def _define_default_rules(self):
        """Define regras de alerta padrão"""
        
        # Sync latency
        self.add_rule(AlertRule(
            name='high_sync_latency',
            metric_name='dumont_sync_latency_seconds',
            condition=lambda v: v > 20,
            severity='warning',
            message_template='Latência de sync alta: {value:.1f}s (threshold: {threshold}s)',
            threshold=20
        ))
        
        # Sync stopped
        self.add_rule(AlertRule(
            name='sync_stopped',
            metric_name='dumont_sync_last_success_seconds_ago',
            condition=lambda v: v > 300,
            severity='critical',
            message_template='Sync parado há {value:.0f}s (threshold: {threshold}s)',
            threshold=300
        ))
        
        # Disk almost full
        self.add_rule(AlertRule(
            name='disk_almost_full',
            metric_name='dumont_disk_usage_percent',
            condition=lambda v: v > 80,
            severity='critical',
            message_template='Disco quase cheio: {value:.1f}% (threshold: {threshold}%)',
            threshold=80
        ))
        
        # High memory usage
        self.add_rule(AlertRule(
            name='high_memory_usage',
            metric_name='dumont_memory_usage_percent',
            condition=lambda v: v > 90,
            severity='warning',
            message_template='Uso de memória alto: {value:.1f}% (threshold: {threshold}%)',
            threshold=90
        ))
        
        # Cost anomaly
        self.add_rule(AlertRule(
            name='high_cost_anomaly',
            metric_name='dumont_cost_hourly_usd',
            condition=lambda v: v > 1.0,
            severity='warning',
            message_template='Custo alto detectado: ${value:.2f}/hora (esperado: <${threshold}/hora)',
            threshold=1.0
        ))
        
        # Machine down
        self.add_rule(AlertRule(
            name='machine_down',
            metric_name='dumont_machine_uptime_seconds',
            condition=lambda v: v == 0,
            severity='critical',
            message_template='Máquina offline detectada',
            threshold=0
        ))
        
        # Health degraded
        self.add_rule(AlertRule(
            name='health_degraded',
            metric_name='dumont_health_status',
            condition=lambda v: v < 1.0,
            severity='warning',
            message_template='Sistema degradado: status={value:.1f}',
            threshold=1.0
        ))
    
    def add_rule(self, rule: AlertRule):
        """Adiciona regra de alerta"""
        self.alert_rules.append(rule)
        logger.debug(f"Added alert rule: {rule.name}")
    
    def check_metric(
        self,
        metric_name: str,
        value: float,
        machine_id: str = 'unknown'
    ) -> List[Alert]:
        """
        Verifica métrica contra todas as regras aplicáveis
        
        Args:
            metric_name: Nome da métrica
            value: Valor atual
            machine_id: ID da máquina
            
        Returns:
            Lista de alertas ativados
        """
        alerts = []
        
        for rule in self.alert_rules:
            if rule.metric_name == metric_name:
                alert = rule.check(value, machine_id)
                
                if alert:
                    # Verificar cooldown
                    alert_key = f"{rule.name}_{machine_id}"
                    last_time = self.last_alert_time.get(alert_key, 0)
                    
                    if time.time() - last_time > rule.cooldown_seconds:
                        alerts.append(alert)
                        self._handle_alert(alert)
                        self.last_alert_time[alert_key] = time.time()
                    else:
                        logger.debug(f"Alert {alert_key} in cooldown period")
        
        return alerts
    
    def check_all_metrics(self, metrics: Dict[str, Dict]) -> List[Alert]:
        """
        Verifica múltiplas métricas de uma vez
        
        Args:
            metrics: Dict de {metric_name: {machine_id: value}}
            
        Returns:
            Lista de todos os alertas ativados
        """
        all_alerts = []
        
        for metric_name, machine_values in metrics.items():
            for machine_id, value in machine_values.items():
                alerts = self.check_metric(metric_name, value, machine_id)
                all_alerts.extend(alerts)
        
        return all_alerts
    
    def _handle_alert(self, alert: Alert):
        """
        Processa alerta: salva, envia notificações
        
        Args:
            alert: Alerta a processar
        """
        # Salvar no histórico
        self.alert_history.append(alert)
        
        # Adicionar aos ativos
        alert_key = f"{alert.title}_{alert.machine_id}"
        self.active_alerts[alert_key] = alert
        
        # Enviar notificações
        self._send_alert(alert)
        
        # Log
        severity_emoji = {
            'critical': '🔴',
            'warning': '🟡',
            'info': '🔵'
        }
        
        emoji = severity_emoji.get(alert.severity, '⚪')
        logger.warning(f"{emoji} ALERT [{alert.severity.upper()}] {alert.title}: {alert.message}")
    
    def _send_alert(self, alert: Alert):
        """Envia alerta via canais configurados"""
        
        # Slack
        if self.slack_webhook:
            try:
                self._send_slack(alert)
            except Exception as e:
                logger.error(f"Failed to send Slack alert: {e}")
        
        # Webhook genérico
        if self.webhook_url:
            try:
                self._send_webhook(alert)
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
        
        # Email (futuro)
        # if self.email_config:
        #     self._send_email(alert)
    
    def _send_slack(self, alert: Alert):
        """Envia alerta para Slack"""
        
        color_map = {
            'critical': '#ff0000',  # Vermelho
            'warning': '#ffaa00',   # Laranja
            'info': '#0099ff'       # Azul
        }
        
        color = color_map.get(alert.severity, '#999999')
        
        payload = {
            'attachments': [{
                'color': color,
                'title': f"🚨 {alert.severity.upper()}: {alert.title}",
                'text': alert.message,
                'fields': [
                    {
                        'title': 'Machine',
                        'value': alert.machine_id,
                        'short': True
                    },
                    {
                        'title': 'Metric',
                        'value': alert.metric_name,
                        'short': True
                    },
                    {
                        'title': 'Current Value',
                        'value': f"{alert.current_value:.2f}",
                        'short': True
                    },
                    {
                        'title': 'Threshold',
                        'value': f"{alert.threshold:.2f}",
                        'short': True
                    }
                ],
                'footer': 'Dumont Cloud Alert Manager',
                'ts': int(alert.timestamp)
            }]
        }
        
        response = requests.post(
            self.slack_webhook,
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Slack alert sent: {alert.title}")
        else:
            logger.error(f"❌ Slack alert failed: {response.status_code}")
    
    def _send_webhook(self, alert: Alert):
        """Envia alerta para webhook genérico"""
        
        payload = alert.to_dict()
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=5
        )
        
        if response.status_code in [200, 201, 204]:
            logger.info(f"✅ Webhook alert sent: {alert.title}")
        else:
            logger.error(f"❌ Webhook alert failed: {response.status_code}")
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """
        Retorna alertas ativos
        
        Args:
            severity: Filtrar por severidade ('critical', 'warning', 'info')
            
        Returns:
            Lista de alertas ativos
        """
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    def clear_alert(self, alert_key: str):
        """Remove alerta dos ativos"""
        if alert_key in self.active_alerts:
            del self.active_alerts[alert_key]
            logger.info(f"✅ Alert cleared: {alert_key}")
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Retorna histórico de alertas"""
        return self.alert_history[-limit:]
    
    def start_monitoring(self, check_interval: int = 60):
        """
        Inicia monitoramento contínuo (se métricas vierem de fonte externa)
        
        Args:
            check_interval: Intervalo entre verificações em segundos
        """
        def monitor_loop():
            while True:
                try:
                    # Aqui você poderia consultar Prometheus para pegar métricas
                    # e verificar contra as regras
                    # Por enquanto, esse método é placeholder
                    pass
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                
                time.sleep(check_interval)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logger.info(f"🚨 Alert monitoring started (interval: {check_interval}s)")


# Singleton instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(
    slack_webhook: Optional[str] = None,
    email_config: Optional[Dict] = None,
    webhook_url: Optional[str] = None
) -> AlertManager:
    """
    Retorna instância singleton do AlertManager
    
    Args:
        slack_webhook: URL do webhook Slack
        email_config: Configuração de email
        webhook_url: URL de webhook genérico
    """
    global _alert_manager
    
    if _alert_manager is None:
        _alert_manager = AlertManager(
            slack_webhook=slack_webhook,
            email_config=email_config,
            webhook_url=webhook_url
        )
    
    return _alert_manager


if __name__ == "__main__":
    # Exemplo de uso
    logging.basicConfig(level=logging.INFO)
    
    # Criar AlertManager (sem Slack para teste)
    alert_mgr = AlertManager()
    
    print("\n🚨 Testando AlertManager...\n")
    
    # Simular métricas problemáticas
    print("1. Testando latência alta...")
    alerts = alert_mgr.check_metric('dumont_sync_latency_seconds', 25.0, 'gpu-12345')
    print(f"   Alertas: {len(alerts)}")
    
    print("\n2. Testando disco cheio...")
    alerts = alert_mgr.check_metric('dumont_disk_usage_percent', 85.0, 'gpu-12345')
    print(f"   Alertas: {len(alerts)}")
    
    print("\n3. Testando custo alto...")
    alerts = alert_mgr.check_metric('dumont_cost_hourly_usd', 2.5, 'gpu-67890')
    print(f"   Alertas: {len(alerts)}")
    
    # Verificar alertas ativos
    print(f"\n📊 Alertas ativos: {len(alert_mgr.get_active_alerts())}")
    for alert in alert_mgr.get_active_alerts():
        print(f"   - [{alert.severity}] {alert.title}: {alert.message}")
    
    print("\n✅ Teste concluído!")
