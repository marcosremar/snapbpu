"""
Telemetry Service - Coleta de métricas Prometheus
"""

import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Verificar se prometheus_client está disponível
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("[TELEMETRY] prometheus_client not installed, metrics disabled")


class TelemetryService:
    """
    Serviço de telemetria centralizado.

    Coleta e expõe métricas de:
    - Sincronização (latência, bytes, arquivos)
    - Recursos (CPU, memória, disco)
    - Custos (hourly, savings)
    - Disponibilidade (uptime, failovers)

    Uso:
        telemetry = get_telemetry()
        telemetry.record_sync(machine_id="123", latency_seconds=2.5, bytes_transferred=1024*1024)
        telemetry.record_failover(from_type="gpu", to_type="cpu", reason="spot_interruption")
    """

    _instance: Optional['TelemetryService'] = None

    def __init__(self):
        if TelemetryService._instance is not None:
            raise RuntimeError("TelemetryService is a singleton. Use get_telemetry()")

        self._metrics_enabled = PROMETHEUS_AVAILABLE
        self._server_started = False

        if self._metrics_enabled:
            self._init_metrics()

        TelemetryService._instance = self
        logger.info("[TELEMETRY] TelemetryService initialized")

    def _init_metrics(self):
        """Inicializa métricas Prometheus"""
        # === MÉTRICAS DE SYNC ===
        self.sync_latency = Histogram(
            'dumont_sync_latency_seconds',
            'Latência de sincronização',
            ['machine_id', 'direction'],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120]
        )

        self.sync_bytes = Counter(
            'dumont_sync_bytes_total',
            'Total de bytes sincronizados',
            ['machine_id', 'direction']
        )

        self.sync_files = Counter(
            'dumont_sync_files_total',
            'Total de arquivos sincronizados',
            ['machine_id']
        )

        self.sync_last_success = Gauge(
            'dumont_sync_last_success_timestamp',
            'Timestamp da última sync bem-sucedida',
            ['machine_id']
        )

        # === MÉTRICAS DE RECURSOS ===
        self.cpu_usage = Gauge(
            'dumont_cpu_usage_percent',
            'Uso de CPU em percentual',
            ['machine_type', 'machine_id']
        )

        self.memory_usage = Gauge(
            'dumont_memory_usage_bytes',
            'Uso de memória em bytes',
            ['machine_type', 'machine_id']
        )

        self.disk_usage = Gauge(
            'dumont_disk_usage_bytes',
            'Uso de disco em bytes',
            ['machine_type', 'machine_id', 'mount']
        )

        # === MÉTRICAS DE CUSTOS ===
        self.cost_hourly = Gauge(
            'dumont_cost_hourly_usd',
            'Custo por hora em USD',
            ['machine_type', 'machine_id', 'provider']
        )

        self.savings_total = Counter(
            'dumont_savings_total_usd',
            'Economia total acumulada em USD',
            ['category']
        )

        # === MÉTRICAS DE DISPONIBILIDADE ===
        self.machine_uptime = Gauge(
            'dumont_machine_uptime_seconds',
            'Uptime da máquina em segundos',
            ['machine_type', 'machine_id']
        )

        self.failovers_total = Counter(
            'dumont_failovers_total',
            'Total de failovers executados',
            ['from_type', 'to_type', 'reason']
        )

        self.failover_duration = Histogram(
            'dumont_failover_duration_seconds',
            'Duração do failover',
            ['strategy'],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600]
        )

        # === MÉTRICAS DE HEALTH ===
        self.health_status = Gauge(
            'dumont_health_status',
            'Status de saúde (1=healthy, 0.5=degraded, 0=unhealthy)',
            ['component']
        )

        self.alerts_active = Gauge(
            'dumont_alerts_active',
            'Número de alertas ativos',
            ['severity']
        )

        # === MÉTRICAS DE INFERÊNCIA ===
        self.inference_latency = Histogram(
            'dumont_inference_latency_seconds',
            'Latência de inferência',
            ['model', 'gpu_type'],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
        )

        self.inference_tokens = Counter(
            'dumont_inference_tokens_total',
            'Total de tokens processados',
            ['model', 'direction']  # direction: input/output
        )

    @classmethod
    def get_instance(cls) -> 'TelemetryService':
        """Retorna instância singleton"""
        if cls._instance is None:
            cls._instance = TelemetryService()
        return cls._instance

    # === MÉTODOS DE REGISTRO ===

    def record_sync(
        self,
        machine_id: str,
        latency_seconds: float,
        bytes_transferred: int,
        files_count: int = 0,
        direction: str = 'upload'
    ):
        """Registra métrica de sincronização"""
        if not self._metrics_enabled:
            return

        self.sync_latency.labels(
            machine_id=machine_id,
            direction=direction
        ).observe(latency_seconds)

        self.sync_bytes.labels(
            machine_id=machine_id,
            direction=direction
        ).inc(bytes_transferred)

        if files_count > 0:
            self.sync_files.labels(machine_id=machine_id).inc(files_count)

        self.sync_last_success.labels(machine_id=machine_id).set(time.time())

    def update_resources(
        self,
        machine_type: str,
        machine_id: str,
        cpu_percent: float = 0,
        memory_bytes: int = 0,
        disk_bytes: int = 0,
        mount: str = '/workspace'
    ):
        """Atualiza métricas de recursos"""
        if not self._metrics_enabled:
            return

        if cpu_percent > 0:
            self.cpu_usage.labels(
                machine_type=machine_type,
                machine_id=machine_id
            ).set(cpu_percent)

        if memory_bytes > 0:
            self.memory_usage.labels(
                machine_type=machine_type,
                machine_id=machine_id
            ).set(memory_bytes)

        if disk_bytes > 0:
            self.disk_usage.labels(
                machine_type=machine_type,
                machine_id=machine_id,
                mount=mount
            ).set(disk_bytes)

    def record_cost(
        self,
        machine_type: str,
        machine_id: str,
        provider: str,
        cost_per_hour: float
    ):
        """Registra custo da máquina"""
        if not self._metrics_enabled:
            return

        self.cost_hourly.labels(
            machine_type=machine_type,
            machine_id=machine_id,
            provider=provider
        ).set(cost_per_hour)

    def record_savings(self, category: str, amount_usd: float):
        """Registra economia"""
        if not self._metrics_enabled:
            return

        self.savings_total.labels(category=category).inc(amount_usd)
        logger.info(f"[TELEMETRY] Savings recorded: {category} = ${amount_usd:.2f}")

    def record_failover(
        self,
        from_type: str,
        to_type: str,
        reason: str,
        duration_seconds: float = 0,
        strategy: str = "unknown"
    ):
        """Registra evento de failover"""
        if not self._metrics_enabled:
            return

        self.failovers_total.labels(
            from_type=from_type,
            to_type=to_type,
            reason=reason
        ).inc()

        if duration_seconds > 0:
            self.failover_duration.labels(strategy=strategy).observe(duration_seconds)

        logger.info(f"[TELEMETRY] Failover: {from_type} -> {to_type} ({reason})")

    def update_health(self, component: str, status: str):
        """Atualiza status de saúde"""
        if not self._metrics_enabled:
            return

        status_map = {'healthy': 1.0, 'degraded': 0.5, 'unhealthy': 0.0}
        self.health_status.labels(component=component).set(status_map.get(status, 0))

    def update_alerts(self, severity: str, count: int):
        """Atualiza contagem de alertas"""
        if not self._metrics_enabled:
            return

        self.alerts_active.labels(severity=severity).set(count)

    def record_inference(
        self,
        model: str,
        gpu_type: str,
        latency_seconds: float,
        input_tokens: int = 0,
        output_tokens: int = 0
    ):
        """Registra métrica de inferência"""
        if not self._metrics_enabled:
            return

        self.inference_latency.labels(
            model=model,
            gpu_type=gpu_type
        ).observe(latency_seconds)

        if input_tokens > 0:
            self.inference_tokens.labels(model=model, direction='input').inc(input_tokens)
        if output_tokens > 0:
            self.inference_tokens.labels(model=model, direction='output').inc(output_tokens)

    def start_server(self, port: int = 9090) -> bool:
        """Inicia servidor HTTP para métricas"""
        if not self._metrics_enabled:
            logger.warning("[TELEMETRY] Metrics disabled, cannot start server")
            return False

        if self._server_started:
            return True

        try:
            start_http_server(port)
            self._server_started = True
            logger.info(f"[TELEMETRY] Prometheus server started on port {port}")
            return True
        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"[TELEMETRY] Port {port} in use, server already running")
                return True
            raise


# Singleton
_telemetry: Optional[TelemetryService] = None


def get_telemetry() -> TelemetryService:
    """Obtém instância do TelemetryService"""
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryService.get_instance()
    return _telemetry
