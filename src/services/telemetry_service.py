"""
Telemetry Service - Coleta e expõe métricas do sistema Dumont Cloud
Usa Prometheus para métricas e fornece endpoints para monitoramento
"""

from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Serviço de telemetria centralizado para Dumont Cloud.
    
    Coleta e expõe métricas de:
    - Sincronização (latência, bytes, arquivos)
    - Recursos (CPU, memória, disco)
    - Custos (hourly, savings)
    - Disponibilidade (uptime, failovers)
    """
    
    _instance: Optional['TelemetryService'] = None
    
    def __init__(self):
        if TelemetryService._instance is not None:
            raise RuntimeError("TelemetryService is a singleton. Use get_instance()")
        
        # === MÉTRICAS DE SYNC ===
        self.sync_latency = Histogram(
            'dumont_sync_latency_seconds',
            'Latência de sincronização entre GPU e CPU',
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
            'Timestamp da última sincronização bem-sucedida',
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
        
        self.memory_total = Gauge(
            'dumont_memory_total_bytes',
            'Memória total em bytes',
            ['machine_type', 'machine_id']
        )
        
        self.disk_usage = Gauge(
            'dumont_disk_usage_bytes',
            'Uso de disco em bytes',
            ['machine_type', 'machine_id', 'mount']
        )
        
        self.disk_total = Gauge(
            'dumont_disk_total_bytes',
            'Disco total em bytes',
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
        
        self.transfer_bytes = Counter(
            'dumont_transfer_bytes_total',
            'Total de bytes transferidos (para cálculo de economia)',
            ['from_region', 'to_region']
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
        
        self.downtime_avoided = Counter(
            'dumont_downtime_avoided_seconds',
            'Downtime evitado graças ao failover',
            ['machine_id']
        )
        
        # === MÉTRICAS DE HEALTH ===
        self.health_status = Gauge(
            'dumont_health_status',
            'Status de saúde do sistema (1=healthy, 0.5=degraded, 0=unhealthy)',
            ['component']
        )
        
        self.alerts_active = Gauge(
            'dumont_alerts_active',
            'Número de alertas ativos',
            ['severity']
        )
        
        TelemetryService._instance = self
        logger.info("📊 TelemetryService initialized")
    
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
        files_count: int,
        direction: str = 'upload'
    ):
        """
        Registra métrica de sincronização
        
        Args:
            machine_id: ID da máquina
            latency_seconds: Latência em segundos
            bytes_transferred: Bytes transferidos
            files_count: Número de arquivos
            direction: 'upload' ou 'download'
        """
        self.sync_latency.labels(
            machine_id=machine_id,
            direction=direction
        ).observe(latency_seconds)
        
        self.sync_bytes.labels(
            machine_id=machine_id,
            direction=direction
        ).inc(bytes_transferred)
        
        self.sync_files.labels(machine_id=machine_id).inc(files_count)
        
        self.sync_last_success.labels(machine_id=machine_id).set(time.time())
        
        logger.debug(f"📊 Sync recorded: {machine_id}, {latency_seconds}s, {bytes_transferred} bytes")
    
    def update_resource_usage(
        self,
        machine_type: str,
        machine_id: str,
        cpu_percent: float,
        memory_used: int,
        memory_total: int,
        disk_used: int,
        disk_total: int,
        mount: str = '/workspace'
    ):
        """
        Atualiza métricas de uso de recursos
        
        Args:
            machine_type: 'gpu' ou 'cpu'
            machine_id: ID da máquina
            cpu_percent: Uso de CPU (0-100)
            memory_used: Memória usada em bytes
            memory_total: Memória total em bytes
            disk_used: Disco usado em bytes
            disk_total: Disco total em bytes
            mount: Ponto de montagem
        """
        self.cpu_usage.labels(
            machine_type=machine_type,
            machine_id=machine_id
        ).set(cpu_percent)
        
        self.memory_usage.labels(
            machine_type=machine_type,
            machine_id=machine_id
        ).set(memory_used)
        
        self.memory_total.labels(
            machine_type=machine_type,
            machine_id=machine_id
        ).set(memory_total)
        
        self.disk_usage.labels(
            machine_type=machine_type,
            machine_id=machine_id,
            mount=mount
        ).set(disk_used)
        
        self.disk_total.labels(
            machine_type=machine_type,
            machine_id=machine_id,
            mount=mount
        ).set(disk_total)
    
    def record_cost(
        self,
        machine_type: str,
        machine_id: str,
        provider: str,
        cost_per_hour: float
    ):
        """
        Registra custo da máquina
        
        Args:
            machine_type: 'gpu' ou 'cpu'
            machine_id: ID da máquina
            provider: 'vastai', 'gcp', etc
            cost_per_hour: Custo por hora em USD
        """
        self.cost_hourly.labels(
            machine_type=machine_type,
            machine_id=machine_id,
            provider=provider
        ).set(cost_per_hour)
    
    def record_savings(self, category: str, amount_usd: float):
        """
        Registra economia
        
        Args:
            category: 'transfer', 'spot_vs_ondemand', 'downtime_avoided', etc
            amount_usd: Valor economizado em USD
        """
        self.savings_total.labels(category=category).inc(amount_usd)
        logger.info(f"💰 Savings recorded: {category} = ${amount_usd:.2f}")
    
    def record_transfer(self, from_region: str, to_region: str, bytes_transferred: int):
        """
        Registra transferência entre regiões (para cálculo de economia)
        
        Args:
            from_region: Região de origem
            to_region: Região de destino
            bytes_transferred: Bytes transferidos
        """
        self.transfer_bytes.labels(
            from_region=from_region,
            to_region=to_region
        ).inc(bytes_transferred)
    
    def update_machine_uptime(self, machine_type: str, machine_id: str, uptime_seconds: float):
        """Atualiza uptime da máquina"""
        self.machine_uptime.labels(
            machine_type=machine_type,
            machine_id=machine_id
        ).set(uptime_seconds)
    
    def record_failover(
        self,
        from_type: str,
        to_type: str,
        reason: str,
        downtime_avoided_seconds: float,
        machine_id: str
    ):
        """
        Registra evento de failover
        
        Args:
            from_type: Tipo da máquina que caiu ('gpu')
            to_type: Tipo que assumiu ('cpu')
            reason: Motivo ('spot_interruption', 'manual', etc)
            downtime_avoided_seconds: Downtime evitado
            machine_id: ID da máquina
        """
        self.failovers_total.labels(
            from_type=from_type,
            to_type=to_type,
            reason=reason
        ).inc()
        
        self.downtime_avoided.labels(machine_id=machine_id).inc(downtime_avoided_seconds)
        
        logger.warning(f"🔄 Failover recorded: {from_type} → {to_type} ({reason})")
    
    def update_health(self, component: str, status: str):
        """
        Atualiza status de saúde de um componente
        
        Args:
            component: 'sync', 'api', 'database', etc
            status: 'healthy', 'degraded', 'unhealthy'
        """
        status_map = {
            'healthy': 1.0,
            'degraded': 0.5,
            'unhealthy': 0.0
        }
        
        self.health_status.labels(component=component).set(status_map.get(status, 0))
    
    def update_alerts(self, severity: str, count: int):
        """
        Atualiza contagem de alertas ativos
        
        Args:
            severity: 'critical', 'warning', 'info'
            count: Número de alertas ativos
        """
        self.alerts_active.labels(severity=severity).set(count)
    
    def start_server(self, port: int = 9090):
        """
        Inicia servidor HTTP para expor métricas Prometheus
        
        Args:
            port: Porta do servidor (default: 9090)
        """
        try:
            start_http_server(port)
            logger.info(f"📊 Prometheus metrics server started on port {port}")
            logger.info(f"   Metrics available at http://localhost:{port}/metrics")
            return True
        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"⚠️  Port {port} already in use, metrics server already running")
                return False
            else:
                raise


# Singleton instance
def get_telemetry() -> TelemetryService:
    """Helper function to get telemetry instance"""
    return TelemetryService.get_instance()


if __name__ == "__main__":
    # Exemplo de uso
    logging.basicConfig(level=logging.INFO)
    
    telemetry = TelemetryService()
    telemetry.start_server(port=9090)
    
    # Simular algumas métricas
    print("\n📊 Simulando métricas...\n")
    
    # Sync
    telemetry.record_sync(
        machine_id='gpu-12345',
        latency_seconds=2.5,
        bytes_transferred=1024 * 1024 * 100,  # 100MB
        files_count=50
    )
    
    # Resources
    telemetry.update_resource_usage(
        machine_type='gpu',
        machine_id='gpu-12345',
        cpu_percent=45.2,
        memory_used=8 * 1024**3,  # 8GB
        memory_total=16 * 1024**3,  # 16GB
        disk_used=50 * 1024**3,  # 50GB
        disk_total=100 * 1024**3  # 100GB
    )
    
    # Cost
    telemetry.record_cost(
        machine_type='gpu',
        machine_id='gpu-12345',
        provider='vastai',
        cost_per_hour=0.50
    )
    
    # Savings
    telemetry.record_savings('transfer', 30.00)
    
    # Failover
    telemetry.record_failover(
        from_type='gpu',
        to_type='cpu',
        reason='spot_interruption',
        downtime_avoided_seconds=900,  # 15 min
        machine_id='gpu-12345'
    )
    
    print("\n✅ Métricas registradas!")
    print(f"📊 Acesse: http://localhost:9090/metrics")
    print("\n⏸️  Pressione Ctrl+C para parar...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")
