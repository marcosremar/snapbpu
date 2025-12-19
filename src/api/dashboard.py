"""
Dashboard API - Endpoints para expor métricas, economia e status do sistema
Usa FastAPI para servir dados em tempo real para o frontend
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# === MODELS ===

class SavingsSummary(BaseModel):
    """Resumo de economia"""
    today: float
    month: float
    year: float
    roi_percentage: float


class SavingsBreakdown(BaseModel):
    """Detalhamento da economia"""
    transfer_costs_avoided: Dict[str, float]
    spot_vs_ondemand: Dict[str, float]
    downtime_avoided: Dict[str, float]


class SavingsResponse(BaseModel):
    """Resposta completa de economia"""
    summary: SavingsSummary
    breakdown: SavingsBreakdown
    timestamp: str


class SyncInfo(BaseModel):
    """Informações de sincronização"""
    last_sync: Optional[str]
    latency_ms: float
    bytes_synced: int
    status: str  # 'active', 'paused', 'error'


class ResourceInfo(BaseModel):
    """Informações de recursos"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float


class CostInfo(BaseModel):
    """Informações de custo"""
    hourly_usd: float
    monthly_usd: float


class MachineMetrics(BaseModel):
    """Métricas de uma máquina"""
    machine_id: str
    type: str  # 'gpu' or 'cpu'
    status: str  # 'running', 'stopped', etc
    sync: SyncInfo
    resources: ResourceInfo
    cost: CostInfo


class MetricsSummary(BaseModel):
    """Resumo geral das métricas"""
    total_machines: int
    gpus_active: int
    cpus_active: int
    total_cost_hourly: float
    sync_status: str  # 'healthy', 'degraded'


class RealtimeMetricsResponse(BaseModel):
    """Resposta de métricas em tempo real"""
    machines: List[MachineMetrics]
    summary: MetricsSummary
    timestamp: str


class AlertInfo(BaseModel):
    """Informação de alerta"""
    severity: str
    title: str
    message: str
    timestamp: str


class HealthResponse(BaseModel):
    """Resposta de health check"""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    alerts_count: int
    alerts: List[AlertInfo]
    uptime_seconds: float
    version: str
    timestamp: str


# === HELPER FUNCTIONS ===

def get_machines_from_db() -> List[Dict]:
    """
    Busca máquinas do banco de dados / estado do sistema
    
    TODO: Integrar com database real
    Por enquanto, retorna dados mock
    """
    # Mock data para demonstração
    return [
        {
            'id': 'gpu-12345',
            'type': 'gpu',
            'status': 'running',
            'provider': 'vastai',
            'cost_per_hour': 0.50,
            'created_at': datetime.now() - timedelta(hours=5)
        },
        {
            'id': 'cpu-67890',
            'type': 'cpu',
            'status': 'running',
            'provider': 'gcp',
            'cost_per_hour': 0.02,
            'created_at': datetime.now() - timedelta(hours=4)
        }
    ]


def get_machine_status(machine_id: str) -> Dict:
    """
    Busca status atual de uma máquina
    
    TODO: Integrar com sistema de monitoramento real
    """
    # Mock data
    return {
        'cpu_percent': 45.2,
        'memory_percent': 62.5,
        'disk_percent': 38.1,
        'status': 'running'
    }


def get_sync_info(machine_id: str) -> Dict:
    """
    Busca informações de sincronização
    
    TODO: Integrar com lsyncd/telemetry
    """
    # Mock data
    return {
        'last_sync': datetime.now().isoformat(),
        'latency_ms': 2500,
        'bytes_synced': 1024 * 1024 * 100,  # 100MB
        'status': 'active'
    }


def get_bytes_synced(period: timedelta) -> int:
    """
    Calcula bytes sincronizados no período
    
    TODO: Integrar com Prometheus/Telemetry
    """
    # Mock: 100GB no mês
    return 100 * 1024**3


def get_failovers_count(period: timedelta) -> int:
    """
    Conta failovers no período
    
    TODO: Buscar do Prometheus
    """
    # Mock: 5 failovers no mês
    return 5


def get_active_alerts() -> List[Dict]:
    """
    Busca alertas ativos
    
    TODO: Integrar com AlertManager
    """
    try:
        # Try importing when running as part of application
        from src.services.alert_manager import get_alert_manager
        
        alert_mgr = get_alert_manager()
        alerts = alert_mgr.get_active_alerts()
        
        return [
            {
                'severity': a.severity,
                'title': a.title,
                'message': a.message,
                'timestamp': datetime.fromtimestamp(a.timestamp).isoformat()
            }
            for a in alerts
        ]
    except (ImportError, RuntimeError) as e:
        logger.debug(f"AlertManager not available: {e}")
        # Return mock data for testing
        return []


def get_system_uptime() -> float:
    """
    Retorna uptime do sistema em segundos
    
    TODO: Integrar com sistema real
    """
    # Mock: 5 dias
    return 5 * 24 * 3600


# === ENDPOINTS ===

@router.get("/savings", response_model=SavingsResponse)
async def get_savings():
    """
    Retorna economia em tempo real
    
    Calcula economia de:
    - Transfer costs (mesma região vs diferentes)
    - Spot vs on-demand
    - Downtime evitado
    """
    
    # Calcular economia de transfer
    bytes_synced_month = get_bytes_synced(timedelta(days=30))
    gb_synced = bytes_synced_month / (1024**3)
    
    # Se estivessem em regiões diferentes: $0.01/GB
    # Na mesma região: $0
    transfer_savings_month = gb_synced * 0.01
    transfer_savings_today = transfer_savings_month / 30
    
    # Calcular economia de spot vs on-demand
    # Assumindo: 10 GPUs, $0.30/h economia por GPU
    num_gpus = 10
    savings_per_gpu_hour = 0.30
    hours_month = 720
    spot_savings_month = num_gpus * savings_per_gpu_hour * hours_month
    spot_savings_today = spot_savings_month / 30
    
    # Calcular economia de downtime evitado
    failovers = get_failovers_count(timedelta(days=30))
    minutes_saved_per_failover = 15  # Sem sistema: 15min downtime
    cost_per_minute = 50 / 60  # $50/h de produtividade
    downtime_savings_month = failovers * minutes_saved_per_failover * cost_per_minute
    downtime_savings_today = downtime_savings_month / 30
    
    # Total
    total_today = transfer_savings_today + spot_savings_today + downtime_savings_today
    total_month = transfer_savings_month + spot_savings_month + downtime_savings_month
    total_year = total_month * 12
    
    # ROI
    # Custo do sistema: CPU backups = 10 * $0.02 * 720 = $144/mês
    system_cost_month = 10 * 0.02 * 720
    roi_percentage = ((total_month - system_cost_month) / system_cost_month) * 100
    
    return SavingsResponse(
        summary=SavingsSummary(
            today=round(total_today, 2),
            month=round(total_month, 2),
            year=round(total_year, 2),
            roi_percentage=round(roi_percentage, 1)
        ),
        breakdown=SavingsBreakdown(
            transfer_costs_avoided={
                'today': round(transfer_savings_today, 2),
                'month': round(transfer_savings_month, 2),
                'bytes_synced_month': bytes_synced_month,
                'gb_synced': round(gb_synced, 2)
            },
            spot_vs_ondemand={
                'today': round(spot_savings_today, 2),
                'month': round(spot_savings_month, 2),
                'num_gpus': num_gpus,
                'savings_per_gpu_hour': savings_per_gpu_hour
            },
            downtime_avoided={
                'today': round(downtime_savings_today, 2),
                'month': round(downtime_savings_month, 2),
                'failovers_count': failovers,
                'minutes_saved': failovers * minutes_saved_per_failover
            }
        ),
        timestamp=datetime.now().isoformat()
    )


@router.get("/metrics/realtime", response_model=RealtimeMetricsResponse)
async def get_realtime_metrics():
    """
    Retorna métricas em tempo real de todas as máquinas
    
    Inclui:
    - Status de cada máquina
    - Uso de recursos
    - Status de sync
    - Custos
    """
    
    machines = get_machines_from_db()
    
    metrics = []
    for machine in machines:
        status = get_machine_status(machine['id'])
        sync_info = get_sync_info(machine['id'])
        
        metrics.append(MachineMetrics(
            machine_id=machine['id'],
            type=machine['type'],
            status=status['status'],
            sync=SyncInfo(
                last_sync=sync_info['last_sync'],
                latency_ms=sync_info['latency_ms'],
                bytes_synced=sync_info['bytes_synced'],
                status=sync_info['status']
            ),
            resources=ResourceInfo(
                cpu_percent=status['cpu_percent'],
                memory_percent=status['memory_percent'],
                disk_percent=status['disk_percent']
            ),
            cost=CostInfo(
                hourly_usd=machine['cost_per_hour'],
                monthly_usd=machine['cost_per_hour'] * 720
            )
        ))
    
    # Summary
    total_machines = len(machines)
    gpus_active = sum(1 for m in metrics if m.type == 'gpu' and m.status == 'running')
    cpus_active = sum(1 for m in metrics if m.type == 'cpu' and m.status == 'running')
    total_cost_hourly = sum(m.cost.hourly_usd for m in metrics)
    
    # Sync status
    all_syncs_active = all(m.sync.status == 'active' for m in metrics)
    sync_status = 'healthy' if all_syncs_active else 'degraded'
    
    return RealtimeMetricsResponse(
        machines=metrics,
        summary=MetricsSummary(
            total_machines=total_machines,
            gpus_active=gpus_active,
            cpus_active=cpus_active,
            total_cost_hourly=round(total_cost_hourly, 2),
            sync_status=sync_status
        ),
        timestamp=datetime.now().isoformat()
    )


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Retorna status geral do sistema
    
    Inclui:
    - Health status
    - Alertas ativos
    - Uptime
    """
    
    alerts = get_active_alerts()
    alerts_count = len(alerts)
    
    # Determinar status geral
    if alerts_count == 0:
        status = 'healthy'
    else:
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        if critical_alerts:
            status = 'unhealthy'
        else:
            status = 'degraded'
    
    return HealthResponse(
        status=status,
        alerts_count=alerts_count,
        alerts=[
            AlertInfo(
                severity=a['severity'],
                title=a['title'],
                message=a['message'],
                timestamp=a['timestamp']
            )
            for a in alerts
        ],
        uptime_seconds=get_system_uptime(),
        version='1.0.0',
        timestamp=datetime.now().isoformat()
    )


@router.get("/stats/summary")
async def get_stats_summary():
    """
    Retorna resumo estatístico rápido (para widgets)
    """
    
    savings = await get_savings()
    metrics = await get_realtime_metrics()
    health = await get_health()
    
    return {
        'savings_month': savings.summary.month,
        'savings_year': savings.summary.year,
        'roi_percentage': savings.summary.roi_percentage,
        'machines_active': metrics.summary.total_machines,
        'cost_hourly': metrics.summary.total_cost_hourly,
        'health_status': health.status,
        'alerts_count': health.alerts_count,
        'timestamp': datetime.now().isoformat()
    }


# === TESTE ===

if __name__ == "__main__":
    import asyncio
    import json
    
    async def test_api():
        print("="*60)
        print("🧪 TESTE: Dashboard API")
        print("="*60)
        print()
        
        # Test savings
        print("1. Testing /api/dashboard/savings...")
        savings = await get_savings()
        print(f"   ✅ Savings today: ${savings.summary.today:.2f}")
        print(f"   ✅ Savings month: ${savings.summary.month:.2f}")
        print(f"   ✅ Savings year: ${savings.summary.year:.2f}")
        print(f"   ✅ ROI: {savings.summary.roi_percentage:.1f}%")
        
        # Test metrics
        print()
        print("2. Testing /api/dashboard/metrics/realtime...")
        metrics = await get_realtime_metrics()
        print(f"   ✅ Total machines: {metrics.summary.total_machines}")
        print(f"   ✅ GPUs active: {metrics.summary.gpus_active}")
        print(f"   ✅ CPUs active: {metrics.summary.cpus_active}")
        print(f"   ✅ Cost/hour: ${metrics.summary.total_cost_hourly:.2f}")
        
        # Test health
        print()
        print("3. Testing /api/dashboard/health...")
        health = await get_health()
        print(f"   ✅ Status: {health.status}")
        print(f"   ✅ Alerts: {health.alerts_count}")
        print(f"   ✅ Uptime: {health.uptime_seconds/3600:.1f}h")
        
        # Test summary
        print()
        print("4. Testing /api/dashboard/stats/summary...")
        summary = await get_stats_summary()
        print(f"   ✅ Quick stats retrieved")
        print(json.dumps(summary, indent=2))
        
        print()
        print("="*60)
        print("✅ TODOS OS ENDPOINTS TESTADOS!")
        print("="*60)
    
    asyncio.run(test_api())
