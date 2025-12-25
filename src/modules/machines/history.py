"""
Machine History - Histórico de eventos de máquinas
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Tipo de evento"""
    CREATED = "created"
    STARTED = "started"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESUMED = "resumed"
    FAILOVER = "failover"
    ERROR = "error"
    COST_UPDATE = "cost_update"


@dataclass
class MachineEvent:
    """Evento de máquina"""
    machine_id: int
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class MachineHistory:
    """
    Gerenciador de histórico de máquinas.

    Rastreia todos os eventos importantes:
    - Criação/destruição
    - Start/stop/pause
    - Failovers
    - Erros

    Uso:
        history = get_machine_history()

        # Registrar evento
        history.record(machine_id=123, event_type=EventType.STARTED)

        # Obter histórico
        events = history.get_events(machine_id=123, hours=24)
    """

    def __init__(self):
        self._events: List[MachineEvent] = []
        self._max_events = 10000

    def record(
        self,
        machine_id: int,
        event_type: EventType,
        details: Optional[Dict[str, Any]] = None,
    ) -> MachineEvent:
        """Registra evento"""
        event = MachineEvent(
            machine_id=machine_id,
            event_type=event_type,
            details=details or {},
        )

        self._events.append(event)

        # Limitar tamanho
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        logger.debug(f"[HISTORY] Machine {machine_id}: {event_type.value}")
        return event

    def get_events(
        self,
        machine_id: int,
        hours: int = 24,
        event_type: Optional[EventType] = None,
    ) -> List[MachineEvent]:
        """Obtém eventos de uma máquina"""
        cutoff = datetime.now() - timedelta(hours=hours)

        events = [
            e for e in self._events
            if e.machine_id == machine_id and e.timestamp >= cutoff
        ]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return sorted(events, key=lambda e: e.timestamp, reverse=True)

    def get_recent(
        self,
        limit: int = 100,
        event_type: Optional[EventType] = None,
    ) -> List[MachineEvent]:
        """Obtém eventos mais recentes"""
        events = self._events.copy()

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def count_by_type(
        self,
        machine_id: int,
        hours: int = 24,
    ) -> Dict[str, int]:
        """Conta eventos por tipo"""
        events = self.get_events(machine_id, hours)

        counts: Dict[str, int] = {}
        for e in events:
            key = e.event_type.value
            counts[key] = counts.get(key, 0) + 1

        return counts

    def get_failover_count(self, machine_id: int, hours: int = 24) -> int:
        """Conta failovers de uma máquina"""
        events = self.get_events(machine_id, hours, EventType.FAILOVER)
        return len(events)


# Singleton
_history: Optional[MachineHistory] = None


def get_machine_history() -> MachineHistory:
    """Obtém instância do MachineHistory"""
    global _history
    if _history is None:
        _history = MachineHistory()
    return _history
