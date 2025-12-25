"""
Realtime Sync Manager - Sincronização em tempo real via lsyncd/rsync
"""

import asyncio
import logging
import subprocess
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RealtimeSyncStatus(str, Enum):
    """Status do sync em tempo real"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class RealtimeSyncInfo:
    """Informações do sync em tempo real"""
    machine_id: int
    status: RealtimeSyncStatus
    source_path: str
    target_host: str
    target_port: int
    target_path: str
    started_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    files_synced: int = 0
    bytes_synced: int = 0
    error: Optional[str] = None


class RealtimeSyncManager:
    """
    Gerenciador de sincronização em tempo real.

    Usa lsyncd para monitorar mudanças e rsync para transferir.
    Ideal para manter workspace GPU/CPU sincronizado.

    Uso:
        manager = get_realtime_sync()

        # Iniciar sync bidirecional
        await manager.start(
            machine_id=123,
            gpu_host="gpu.vast.ai",
            gpu_port=12345,
            cpu_host="cpu.gcp.com",
            cpu_port=22,
        )

        # Verificar status
        info = manager.get_status(machine_id=123)

        # Parar sync
        await manager.stop(machine_id=123)
    """

    def __init__(self):
        self._syncs: Dict[int, RealtimeSyncInfo] = {}
        self._processes: Dict[int, subprocess.Popen] = {}

    async def start(
        self,
        machine_id: int,
        source_host: str,
        source_port: int,
        target_host: str,
        target_port: int,
        source_path: str = "/workspace",
        target_path: str = "/workspace",
        exclude_patterns: Optional[List[str]] = None,
    ) -> RealtimeSyncInfo:
        """
        Inicia sincronização em tempo real.

        Args:
            machine_id: ID da máquina
            source_host: Host de origem
            source_port: Porta SSH origem
            target_host: Host de destino
            target_port: Porta SSH destino
            source_path: Path de origem
            target_path: Path de destino
            exclude_patterns: Padrões a excluir

        Returns:
            RealtimeSyncInfo com status
        """
        if machine_id in self._syncs:
            if self._syncs[machine_id].status == RealtimeSyncStatus.RUNNING:
                logger.warning(f"[REALTIME] Sync already running for {machine_id}")
                return self._syncs[machine_id]

        exclude_patterns = exclude_patterns or ["*.tmp", "*.log", "__pycache__", ".git"]

        info = RealtimeSyncInfo(
            machine_id=machine_id,
            status=RealtimeSyncStatus.STARTING,
            source_path=source_path,
            target_host=target_host,
            target_port=target_port,
            target_path=target_path,
        )
        self._syncs[machine_id] = info

        try:
            # Gerar configuração lsyncd
            config = self._generate_lsyncd_config(
                source_host=source_host,
                source_port=source_port,
                source_path=source_path,
                target_host=target_host,
                target_port=target_port,
                target_path=target_path,
                exclude_patterns=exclude_patterns,
            )

            # Escrever config no host de origem
            config_path = f"/tmp/lsyncd_{machine_id}.conf"
            await self._write_remote_file(
                source_host, source_port, config_path, config
            )

            # Instalar e iniciar lsyncd
            await self._start_lsyncd(source_host, source_port, config_path)

            info.status = RealtimeSyncStatus.RUNNING
            info.started_at = datetime.now()

            logger.info(
                f"[REALTIME] Started sync for machine {machine_id}: "
                f"{source_host}:{source_path} -> {target_host}:{target_path}"
            )

            return info

        except Exception as e:
            info.status = RealtimeSyncStatus.ERROR
            info.error = str(e)
            logger.error(f"[REALTIME] Failed to start sync: {e}")
            return info

    async def stop(self, machine_id: int) -> bool:
        """Para sincronização em tempo real"""
        if machine_id not in self._syncs:
            return False

        info = self._syncs[machine_id]

        try:
            # Matar processo lsyncd remoto
            # (simplificado - em produção precisaria do SSH real)
            logger.info(f"[REALTIME] Stopping sync for machine {machine_id}")
            info.status = RealtimeSyncStatus.STOPPED

            return True

        except Exception as e:
            logger.error(f"[REALTIME] Failed to stop sync: {e}")
            return False

    def get_status(self, machine_id: int) -> Optional[RealtimeSyncInfo]:
        """Obtém status do sync"""
        return self._syncs.get(machine_id)

    def list_active(self) -> List[RealtimeSyncInfo]:
        """Lista todos os syncs ativos"""
        return [
            info for info in self._syncs.values()
            if info.status == RealtimeSyncStatus.RUNNING
        ]

    def _generate_lsyncd_config(
        self,
        source_host: str,
        source_port: int,
        source_path: str,
        target_host: str,
        target_port: int,
        target_path: str,
        exclude_patterns: List[str],
    ) -> str:
        """Gera configuração lsyncd"""
        excludes = ",\n        ".join([f'"{p}"' for p in exclude_patterns])

        return f"""
settings {{
    logfile = "/var/log/lsyncd.log",
    statusFile = "/var/log/lsyncd.status",
    nodaemon = false,
    insist = true,
    maxProcesses = 4,
}}

sync {{
    default.rsync,
    source = "{source_path}",
    target = "root@{target_host}:{target_path}",
    delay = 2,
    rsync = {{
        archive = true,
        compress = true,
        rsh = "ssh -p {target_port} -o StrictHostKeyChecking=no",
        exclude = {{
            {excludes}
        }},
    }},
}}
"""

    async def _write_remote_file(
        self,
        host: str,
        port: int,
        path: str,
        content: str,
    ):
        """Escreve arquivo em host remoto"""
        # Em produção, usaria SSH real
        logger.debug(f"[REALTIME] Would write {path} to {host}:{port}")

    async def _start_lsyncd(
        self,
        host: str,
        port: int,
        config_path: str,
    ):
        """Inicia lsyncd no host remoto"""
        # Em produção, executaria via SSH
        logger.debug(f"[REALTIME] Would start lsyncd on {host}:{port}")


# Singleton
_manager: Optional[RealtimeSyncManager] = None


def get_realtime_sync() -> RealtimeSyncManager:
    """Obtém instância do RealtimeSyncManager"""
    global _manager
    if _manager is None:
        _manager = RealtimeSyncManager()
    return _manager
