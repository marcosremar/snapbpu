"""
Periodic Snapshot Service - Cria snapshots periódicos em background

Estratégia:
- Cria snapshot de todas GPUs ativas a cada X minutos
- Mantém histórico dos últimos N snapshots
- Permite failover rápido usando último snapshot + sync incremental
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from ..gpu.snapshot import GPUSnapshotService

logger = logging.getLogger(__name__)


class PeriodicSnapshotService:
    """Cria snapshots periódicos de GPUs ativas"""

    def __init__(
        self,
        snapshot_service: GPUSnapshotService,
        interval_minutes: int = 60,
        keep_last_n: int = 24,  # Manter últimas 24 horas
    ):
        self.snapshot_service = snapshot_service
        self.interval_minutes = interval_minutes
        self.keep_last_n = keep_last_n
        self.running = False
        self._task = None

        # Histórico de snapshots: {instance_id: [(timestamp, snapshot_id), ...]}
        self.snapshot_history: Dict[int, List[tuple]] = {}

    async def start(self):
        """Inicia o serviço de snapshots periódicos"""
        if self.running:
            logger.warning("[PeriodicSnapshot] Service already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"[PeriodicSnapshot] Started (interval: {self.interval_minutes}min)")

    async def stop(self):
        """Para o serviço"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[PeriodicSnapshot] Stopped")

    async def _run_loop(self):
        """Loop principal - cria snapshots periodicamente"""
        while self.running:
            try:
                await self._create_snapshots()
            except Exception as e:
                logger.error(f"[PeriodicSnapshot] Error creating snapshots: {e}")

            # Aguardar próximo ciclo
            await asyncio.sleep(self.interval_minutes * 60)

    async def _create_snapshots(self):
        """Cria snapshots de todas GPUs ativas"""
        # TODO: Integrar com sistema de monitoramento para pegar GPUs ativas
        # Por enquanto, vamos fazer placeholder
        logger.info("[PeriodicSnapshot] Creating periodic snapshots...")

        # Em produção, isso viria do banco de dados ou API
        active_gpus = []  # Lista de {instance_id, ssh_host, ssh_port}

        for gpu in active_gpus:
            try:
                snapshot_id = f"periodic-{gpu['instance_id']}-{int(time.time())}"

                snapshot_info = self.snapshot_service.create_snapshot(
                    instance_id=str(gpu['instance_id']),
                    ssh_host=gpu['ssh_host'],
                    ssh_port=gpu['ssh_port'],
                    workspace_path="/workspace",
                    snapshot_name=snapshot_id,
                )

                # Adicionar ao histórico
                timestamp = datetime.utcnow()
                if gpu['instance_id'] not in self.snapshot_history:
                    self.snapshot_history[gpu['instance_id']] = []

                self.snapshot_history[gpu['instance_id']].append((timestamp, snapshot_id))

                # Limpar snapshots antigos
                self._cleanup_old_snapshots(gpu['instance_id'])

                logger.info(
                    f"[PeriodicSnapshot] Created snapshot for GPU {gpu['instance_id']}: "
                    f"{snapshot_id} ({snapshot_info.get('size_compressed', 0)} bytes)"
                )

            except Exception as e:
                logger.error(f"[PeriodicSnapshot] Failed to snapshot GPU {gpu['instance_id']}: {e}")

    def _cleanup_old_snapshots(self, instance_id: int):
        """Remove snapshots antigos, mantendo apenas os últimos N"""
        if instance_id not in self.snapshot_history:
            return

        snapshots = self.snapshot_history[instance_id]
        if len(snapshots) > self.keep_last_n:
            # Ordenar por timestamp e manter só os últimos N
            snapshots.sort(key=lambda x: x[0])
            old_snapshots = snapshots[:-self.keep_last_n]

            # TODO: Deletar snapshots antigos do B2
            for timestamp, snapshot_id in old_snapshots:
                logger.info(f"[PeriodicSnapshot] Cleaning up old snapshot: {snapshot_id}")

            self.snapshot_history[instance_id] = snapshots[-self.keep_last_n:]

    def get_latest_snapshot(self, instance_id: int) -> Optional[tuple]:
        """Retorna o último snapshot de uma GPU"""
        if instance_id not in self.snapshot_history:
            return None

        snapshots = self.snapshot_history[instance_id]
        if not snapshots:
            return None

        # Retorna (timestamp, snapshot_id) mais recente
        return max(snapshots, key=lambda x: x[0])

    def get_snapshot_age(self, instance_id: int) -> Optional[timedelta]:
        """Retorna a idade do último snapshot"""
        latest = self.get_latest_snapshot(instance_id)
        if not latest:
            return None

        timestamp, _ = latest
        return datetime.utcnow() - timestamp


# Singleton global
_periodic_snapshot_service: Optional[PeriodicSnapshotService] = None


def get_periodic_snapshot_service(
    snapshot_service: Optional[GPUSnapshotService] = None,
    **kwargs
) -> PeriodicSnapshotService:
    """Retorna instância singleton do serviço"""
    global _periodic_snapshot_service

    if _periodic_snapshot_service is None:
        if snapshot_service is None:
            # Criar com configuração padrão
            snapshot_service = GPUSnapshotService(
                b2_endpoint="https://s3.us-west-004.backblazeb2.com",
                b2_bucket="dumoncloud-snapshot"
            )

        _periodic_snapshot_service = PeriodicSnapshotService(
            snapshot_service=snapshot_service,
            **kwargs
        )

    return _periodic_snapshot_service
