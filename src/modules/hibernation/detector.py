"""
Idle Detector - Detecção de ociosidade
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IdleMetrics:
    """Métricas para detecção de idle"""
    gpu_utilization: float = 0.0
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    disk_io_bytes: int = 0
    last_api_call: Optional[datetime] = None
    active_connections: int = 0


class IdleDetector:
    """
    Detector de ociosidade para máquinas GPU.

    Analisa múltiplas métricas para determinar se máquina está ociosa:
    - GPU utilization
    - CPU utilization
    - Network activity
    - API calls

    Uso:
        detector = get_idle_detector()

        is_idle = detector.check(
            machine_id=123,
            gpu_util=2.0,
            cpu_util=5.0,
        )
    """

    def __init__(
        self,
        gpu_threshold: float = 5.0,
        cpu_threshold: float = 10.0,
        network_threshold_kbps: float = 10.0,
    ):
        self.gpu_threshold = gpu_threshold
        self.cpu_threshold = cpu_threshold
        self.network_threshold = network_threshold_kbps * 1024

        self._metrics: Dict[int, IdleMetrics] = {}
        self._history: Dict[int, list] = {}

    def update_metrics(
        self,
        machine_id: int,
        gpu_util: float = 0,
        cpu_util: float = 0,
        memory_util: float = 0,
        network_rx: int = 0,
        network_tx: int = 0,
    ):
        """Atualiza métricas de uma máquina"""
        metrics = IdleMetrics(
            gpu_utilization=gpu_util,
            cpu_utilization=cpu_util,
            memory_utilization=memory_util,
            network_rx_bytes=network_rx,
            network_tx_bytes=network_tx,
        )
        self._metrics[machine_id] = metrics

        # Histórico para análise
        if machine_id not in self._history:
            self._history[machine_id] = []
        self._history[machine_id].append({
            "timestamp": datetime.now(),
            **metrics.__dict__
        })
        # Manter últimos 60 pontos
        self._history[machine_id] = self._history[machine_id][-60:]

    def check(
        self,
        machine_id: int,
        gpu_util: Optional[float] = None,
        cpu_util: Optional[float] = None,
    ) -> bool:
        """
        Verifica se máquina está ociosa.

        Args:
            machine_id: ID da máquina
            gpu_util: GPU utilization (%)
            cpu_util: CPU utilization (%)

        Returns:
            True se máquina está ociosa
        """
        # Usar métricas passadas ou cached
        if gpu_util is None or cpu_util is None:
            metrics = self._metrics.get(machine_id)
            if not metrics:
                return False
            gpu_util = gpu_util or metrics.gpu_utilization
            cpu_util = cpu_util or metrics.cpu_utilization

        # Verificar thresholds
        gpu_idle = gpu_util < self.gpu_threshold
        cpu_idle = cpu_util < self.cpu_threshold

        return gpu_idle and cpu_idle

    def get_idle_duration(self, machine_id: int) -> float:
        """
        Calcula há quanto tempo máquina está ociosa.

        Returns:
            Minutos de idle (0 se não está ociosa)
        """
        history = self._history.get(machine_id, [])
        if not history:
            return 0

        # Encontrar primeiro ponto onde começou a ficar idle
        idle_start = None
        for point in reversed(history):
            is_idle = (
                point.get("gpu_utilization", 100) < self.gpu_threshold and
                point.get("cpu_utilization", 100) < self.cpu_threshold
            )
            if is_idle:
                idle_start = point.get("timestamp")
            else:
                break

        if idle_start:
            return (datetime.now() - idle_start).total_seconds() / 60

        return 0

    def get_metrics(self, machine_id: int) -> Optional[IdleMetrics]:
        """Obtém métricas atuais"""
        return self._metrics.get(machine_id)

    def get_history(
        self,
        machine_id: int,
        minutes: int = 60,
    ) -> list:
        """Obtém histórico de métricas"""
        history = self._history.get(machine_id, [])
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [
            h for h in history
            if h.get("timestamp", datetime.min) >= cutoff
        ]


# Singleton
_detector: Optional[IdleDetector] = None


def get_idle_detector() -> IdleDetector:
    """Obtém instância do IdleDetector"""
    global _detector
    if _detector is None:
        _detector = IdleDetector()
    return _detector
