"""
Hibernation Manager - Gerenciamento de hibernação
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .models import (
    HibernationState,
    HibernationEvent,
    HibernationEventType,
    IdleConfig,
    MachineIdleStatus,
)

logger = logging.getLogger(__name__)


class HibernationManager:
    """
    Gerenciador de hibernação automática.

    Funcionalidades:
    - Detecção de idle
    - Auto-pause quando ocioso
    - Resume sob demanda
    - Tracking de economia

    Uso:
        manager = get_hibernation_manager()

        # Configurar
        manager.configure(machine_id=123, config=IdleConfig(...))

        # Iniciar monitoramento
        await manager.start_monitoring(machine_id=123)

        # Pausar manualmente
        await manager.pause(machine_id=123)

        # Resumir
        await manager.resume(machine_id=123)
    """

    def __init__(self):
        self._configs: Dict[int, IdleConfig] = {}
        self._status: Dict[int, MachineIdleStatus] = {}
        self._events: List[HibernationEvent] = []
        self._tasks: Dict[int, asyncio.Task] = {}

    def configure(self, machine_id: int, config: IdleConfig):
        """Configura hibernação para uma máquina"""
        self._configs[machine_id] = config
        if machine_id not in self._status:
            self._status[machine_id] = MachineIdleStatus(
                machine_id=machine_id,
                state=HibernationState.ACTIVE,
            )
        logger.info(f"[HIBERNATION] Configured machine {machine_id}")

    def get_status(self, machine_id: int) -> MachineIdleStatus:
        """Obtém status de hibernação"""
        return self._status.get(machine_id, MachineIdleStatus(
            machine_id=machine_id,
            state=HibernationState.ACTIVE,
        ))

    async def start_monitoring(self, machine_id: int):
        """Inicia monitoramento de idle"""
        if machine_id in self._tasks:
            logger.warning(f"[HIBERNATION] Already monitoring machine {machine_id}")
            return

        config = self._configs.get(machine_id, IdleConfig(machine_id=machine_id))
        self._configs[machine_id] = config

        task = asyncio.create_task(self._monitor_loop(machine_id))
        self._tasks[machine_id] = task
        logger.info(f"[HIBERNATION] Started monitoring machine {machine_id}")

    async def stop_monitoring(self, machine_id: int):
        """Para monitoramento"""
        if machine_id in self._tasks:
            self._tasks[machine_id].cancel()
            try:
                await self._tasks[machine_id]
            except asyncio.CancelledError:
                pass
            del self._tasks[machine_id]
            logger.info(f"[HIBERNATION] Stopped monitoring machine {machine_id}")

    async def pause(self, machine_id: int, reason: str = "manual") -> bool:
        """Pausa máquina"""
        status = self._status.get(machine_id)
        if not status:
            status = MachineIdleStatus(machine_id=machine_id, state=HibernationState.ACTIVE)
            self._status[machine_id] = status

        if status.state == HibernationState.PAUSED:
            logger.warning(f"[HIBERNATION] Machine {machine_id} already paused")
            return True

        status.state = HibernationState.PAUSING
        logger.info(f"[HIBERNATION] Pausing machine {machine_id}: {reason}")

        try:
            # Em produção, chamaria API do provider
            await self._pause_instance(machine_id)

            status.state = HibernationState.PAUSED
            status.paused_at = datetime.now()

            # Registrar evento
            event_type = HibernationEventType.AUTO_PAUSED if reason == "idle" else HibernationEventType.MANUAL_PAUSED
            self._events.append(HibernationEvent(
                machine_id=machine_id,
                event_type=event_type,
                idle_hours=status.idle_minutes / 60,
            ))

            logger.info(f"[HIBERNATION] Machine {machine_id} paused")
            return True

        except Exception as e:
            status.state = HibernationState.ERROR
            logger.error(f"[HIBERNATION] Pause failed: {e}")
            return False

    async def resume(self, machine_id: int) -> bool:
        """Resume máquina"""
        status = self._status.get(machine_id)
        if not status or status.state != HibernationState.PAUSED:
            logger.warning(f"[HIBERNATION] Machine {machine_id} not paused")
            return False

        status.state = HibernationState.RESUMING
        logger.info(f"[HIBERNATION] Resuming machine {machine_id}")

        try:
            # Em produção, chamaria API do provider
            await self._resume_instance(machine_id)

            # Calcular economia
            if status.paused_at:
                paused_hours = (datetime.now() - status.paused_at).total_seconds() / 3600
                status.total_paused_hours += paused_hours

                # Estimar savings ($0.50/hr médio)
                savings = paused_hours * 0.50
                status.total_savings_usd += savings

                self._events.append(HibernationEvent(
                    machine_id=machine_id,
                    event_type=HibernationEventType.RESUMED,
                    savings_usd=savings,
                ))

            status.state = HibernationState.ACTIVE
            status.paused_at = None
            status.idle_since = None
            status.idle_minutes = 0

            logger.info(f"[HIBERNATION] Machine {machine_id} resumed")
            return True

        except Exception as e:
            status.state = HibernationState.ERROR
            logger.error(f"[HIBERNATION] Resume failed: {e}")
            return False

    def get_savings(self, machine_id: int) -> Dict[str, Any]:
        """Obtém economia de uma máquina"""
        status = self._status.get(machine_id)
        if not status:
            return {"machine_id": machine_id, "savings_usd": 0, "hours_paused": 0}

        return {
            "machine_id": machine_id,
            "savings_usd": status.total_savings_usd,
            "hours_paused": status.total_paused_hours,
        }

    def get_events(self, machine_id: int, limit: int = 50) -> List[HibernationEvent]:
        """Obtém eventos de hibernação"""
        events = [e for e in self._events if e.machine_id == machine_id]
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    async def _monitor_loop(self, machine_id: int):
        """Loop de monitoramento de idle"""
        while True:
            try:
                config = self._configs.get(machine_id)
                if not config:
                    await asyncio.sleep(60)
                    continue

                status = self._status.get(machine_id)
                if not status or status.state in [HibernationState.PAUSED, HibernationState.PAUSING]:
                    await asyncio.sleep(60)
                    continue

                # Verificar utilização
                is_idle = await self._check_idle(machine_id, config)

                if is_idle:
                    if status.idle_since is None:
                        status.idle_since = datetime.now()
                        status.state = HibernationState.IDLE

                    status.idle_minutes = (datetime.now() - status.idle_since).total_seconds() / 60

                    # Auto-pause se configurado
                    if config.auto_pause_enabled:
                        total_idle = status.idle_minutes
                        threshold = config.idle_threshold_minutes + config.pause_delay_minutes

                        if total_idle >= threshold:
                            await self.pause(machine_id, reason="idle")
                else:
                    status.idle_since = None
                    status.idle_minutes = 0
                    status.state = HibernationState.ACTIVE

                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HIBERNATION] Monitor error: {e}")
                await asyncio.sleep(60)

    async def _check_idle(self, machine_id: int, config: IdleConfig) -> bool:
        """Verifica se máquina está ociosa"""
        # Em produção, verificaria métricas reais
        import random
        return random.random() < 0.1  # 10% chance de estar idle

    async def _pause_instance(self, machine_id: int):
        """Pausa instância no provider"""
        await asyncio.sleep(0.1)

    async def _resume_instance(self, machine_id: int):
        """Resume instância no provider"""
        await asyncio.sleep(0.1)


# Singleton
_manager: Optional[HibernationManager] = None


def get_hibernation_manager() -> HibernationManager:
    """Obtém instância do HibernationManager"""
    global _manager
    if _manager is None:
        _manager = HibernationManager()
    return _manager
