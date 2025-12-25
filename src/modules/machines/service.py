"""
Machine Manager - Gerenciamento de máquinas GPU
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .models import MachineInfo, MachineStatus, MachineStats, HostBlacklist

logger = logging.getLogger(__name__)


class MachineManager:
    """
    Gerenciador central de máquinas GPU.

    Funcionalidades:
    - Registro e tracking de máquinas
    - Blacklist de hosts problemáticos
    - Estatísticas de uso
    - Seleção de melhor host

    Uso:
        manager = get_machine_manager()

        # Registrar máquina
        machine = manager.register(user_id="user123", gpu_type="RTX 4090")

        # Blacklist host
        manager.blacklist_host("host-456", reason="High failure rate")

        # Obter estatísticas
        stats = manager.get_stats(machine_id=123)
    """

    def __init__(self):
        self._machines: Dict[int, MachineInfo] = {}
        self._blacklist: Dict[str, HostBlacklist] = {}
        self._next_id = 1

    def register(
        self,
        user_id: str,
        gpu_type: str,
        provider: str = "vast",
        **kwargs
    ) -> MachineInfo:
        """Registra nova máquina"""
        machine = MachineInfo(
            machine_id=self._next_id,
            user_id=user_id,
            status=MachineStatus.PROVISIONING,
            gpu_type=gpu_type,
            provider=provider,
            **kwargs
        )
        self._machines[machine.machine_id] = machine
        self._next_id += 1

        logger.info(f"[MACHINES] Registered machine {machine.machine_id}")
        return machine

    def get(self, machine_id: int) -> Optional[MachineInfo]:
        """Obtém informações de uma máquina"""
        return self._machines.get(machine_id)

    def update_status(self, machine_id: int, status: MachineStatus):
        """Atualiza status de uma máquina"""
        if machine_id in self._machines:
            self._machines[machine_id].status = status
            self._machines[machine_id].last_seen_at = datetime.now()
            logger.debug(f"[MACHINES] Machine {machine_id} status: {status.value}")

    def list_active(self, user_id: Optional[str] = None) -> List[MachineInfo]:
        """Lista máquinas ativas"""
        machines = [
            m for m in self._machines.values()
            if m.status in [MachineStatus.ACTIVE, MachineStatus.PAUSED]
        ]
        if user_id:
            machines = [m for m in machines if m.user_id == user_id]
        return machines

    def blacklist_host(
        self,
        host_id: str,
        reason: str,
        provider: str = "vast",
        duration_hours: Optional[int] = None,
    ):
        """Adiciona host à blacklist"""
        expires = None
        if duration_hours:
            expires = datetime.now() + timedelta(hours=duration_hours)

        entry = HostBlacklist(
            host_id=host_id,
            provider=provider,
            reason=reason,
            expires_at=expires,
        )
        self._blacklist[host_id] = entry
        logger.warning(f"[MACHINES] Blacklisted host {host_id}: {reason}")

    def is_blacklisted(self, host_id: str) -> bool:
        """Verifica se host está na blacklist"""
        if host_id not in self._blacklist:
            return False

        entry = self._blacklist[host_id]
        if entry.is_expired():
            del self._blacklist[host_id]
            return False

        return True

    def get_blacklist(self) -> List[HostBlacklist]:
        """Retorna blacklist atual"""
        # Limpar expirados
        expired = [k for k, v in self._blacklist.items() if v.is_expired()]
        for k in expired:
            del self._blacklist[k]

        return list(self._blacklist.values())

    def remove_from_blacklist(self, host_id: str) -> bool:
        """Remove host da blacklist"""
        if host_id in self._blacklist:
            del self._blacklist[host_id]
            logger.info(f"[MACHINES] Removed {host_id} from blacklist")
            return True
        return False

    def get_stats(
        self,
        machine_id: int,
        days: int = 30,
    ) -> MachineStats:
        """Obtém estatísticas de uma máquina"""
        machine = self._machines.get(machine_id)
        if not machine:
            return MachineStats(machine_id=machine_id)

        # Em produção, buscaria do banco de dados
        return MachineStats(
            machine_id=machine_id,
            total_uptime_hours=machine.total_uptime_hours,
            total_cost=machine.total_cost,
            avg_hourly_cost=machine.price_per_hour,
            period_start=datetime.now() - timedelta(days=days),
            period_end=datetime.now(),
        )


# Singleton
_manager: Optional[MachineManager] = None


def get_machine_manager() -> MachineManager:
    """Obtém instância do MachineManager"""
    global _manager
    if _manager is None:
        _manager = MachineManager()
    return _manager
