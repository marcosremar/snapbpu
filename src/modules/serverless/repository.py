"""
Serverless Module - Repository Layer

Acesso ao banco de dados PostgreSQL para o módulo serverless.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import (
    ServerlessUserSettings,
    ServerlessInstance,
    ServerlessSnapshot,
    ServerlessEvent,
    ServerlessModeEnum,
    InstanceStateEnum,
    EventTypeEnum,
)

logger = logging.getLogger(__name__)


class ServerlessRepository:
    """Repository para operações de banco de dados do módulo serverless"""

    def __init__(self, session: Session):
        self.session = session

    # =========================================================================
    # USER SETTINGS
    # =========================================================================

    def get_user_settings(self, user_id: str) -> Optional[ServerlessUserSettings]:
        """Retorna configurações do usuário"""
        return self.session.query(ServerlessUserSettings).filter(
            ServerlessUserSettings.user_id == user_id
        ).first()

    def get_or_create_user_settings(self, user_id: str) -> ServerlessUserSettings:
        """Retorna ou cria configurações do usuário"""
        settings = self.get_user_settings(user_id)
        if not settings:
            settings = ServerlessUserSettings(user_id=user_id)
            self.session.add(settings)
            self.session.commit()
            logger.info(f"Created serverless settings for user {user_id}")
        return settings

    def update_user_settings(
        self,
        user_id: str,
        scale_down_timeout: Optional[int] = None,
        destroy_after_hours: Optional[int] = None,
        default_mode: Optional[str] = None,
        fallback_enabled: Optional[bool] = None,
        **kwargs
    ) -> ServerlessUserSettings:
        """Atualiza configurações do usuário"""
        settings = self.get_or_create_user_settings(user_id)

        if scale_down_timeout is not None:
            settings.scale_down_timeout_seconds = scale_down_timeout

        if destroy_after_hours is not None:
            settings.destroy_after_hours_paused = destroy_after_hours
            settings.auto_destroy_enabled = destroy_after_hours > 0

        if default_mode is not None:
            settings.default_mode = ServerlessModeEnum(default_mode)

        if fallback_enabled is not None:
            settings.fallback_enabled = fallback_enabled

        # Outros campos
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        settings.updated_at = datetime.utcnow()
        self.session.commit()
        return settings

    # =========================================================================
    # INSTANCES
    # =========================================================================

    def get_instance(self, vast_instance_id: int) -> Optional[ServerlessInstance]:
        """Retorna instância por ID do VAST.ai"""
        return self.session.query(ServerlessInstance).filter(
            ServerlessInstance.vast_instance_id == vast_instance_id
        ).first()

    def get_user_instances(
        self,
        user_id: str,
        state: Optional[InstanceStateEnum] = None
    ) -> List[ServerlessInstance]:
        """Retorna instâncias do usuário"""
        query = self.session.query(ServerlessInstance).filter(
            ServerlessInstance.user_id == user_id
        )
        if state:
            query = query.filter(ServerlessInstance.state == state)
        return query.all()

    def create_instance(
        self,
        user_id: str,
        vast_instance_id: int,
        mode: str = "economic",
        scale_down_timeout: int = 30,
        gpu_name: Optional[str] = None,
        hourly_cost: float = 0.0,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        **kwargs
    ) -> ServerlessInstance:
        """Cria registro de instância serverless"""
        # Obter settings do usuário para defaults
        user_settings = self.get_or_create_user_settings(user_id)

        instance = ServerlessInstance(
            user_id=user_id,
            vast_instance_id=vast_instance_id,
            mode=ServerlessModeEnum(mode),
            scale_down_timeout_seconds=scale_down_timeout,
            destroy_after_hours_paused=user_settings.destroy_after_hours_paused,
            gpu_name=gpu_name,
            hourly_cost=hourly_cost,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            user_settings_id=user_settings.id,
            state=InstanceStateEnum.RUNNING,
        )

        self.session.add(instance)
        self.session.commit()
        logger.info(f"Created serverless instance record for {vast_instance_id}")
        return instance

    def update_instance_state(
        self,
        vast_instance_id: int,
        state: InstanceStateEnum,
        **kwargs
    ) -> Optional[ServerlessInstance]:
        """Atualiza estado da instância"""
        instance = self.get_instance(vast_instance_id)
        if not instance:
            return None

        old_state = instance.state
        instance.state = state

        # Atualizar timestamps baseado no novo estado
        now = datetime.utcnow()

        if state == InstanceStateEnum.PAUSED:
            instance.paused_at = now
            instance.scale_down_count += 1
            # Calcular tempo running
            if instance.last_request_at:
                runtime = (now - instance.last_request_at).total_seconds()
                instance.total_runtime_seconds += runtime

        elif state == InstanceStateEnum.RUNNING:
            if old_state == InstanceStateEnum.PAUSED and instance.paused_at:
                # Calcular tempo pausado
                paused_time = (now - instance.paused_at).total_seconds()
                instance.total_paused_seconds += paused_time
                # Calcular economia
                savings = (paused_time / 3600) * instance.hourly_cost
                instance.total_savings_usd += savings
                instance.scale_up_count += 1

            instance.paused_at = None
            instance.idle_since = None
            instance.last_request_at = now

        elif state == InstanceStateEnum.DESTROYED:
            pass  # Manter timestamps para histórico

        # Campos adicionais
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        self.session.commit()
        return instance

    def update_last_request(self, vast_instance_id: int) -> Optional[ServerlessInstance]:
        """Atualiza timestamp da última requisição"""
        instance = self.get_instance(vast_instance_id)
        if instance:
            instance.last_request_at = datetime.utcnow()
            instance.idle_since = None
            self.session.commit()
        return instance

    def mark_idle(self, vast_instance_id: int) -> Optional[ServerlessInstance]:
        """Marca instância como idle"""
        instance = self.get_instance(vast_instance_id)
        if instance and not instance.idle_since:
            instance.idle_since = datetime.utcnow()
            self.session.commit()
        return instance

    def get_instances_to_destroy(self) -> List[ServerlessInstance]:
        """
        Retorna instâncias pausadas que devem ser destruídas.

        Critérios:
        - Estado = PAUSED
        - Tempo pausado > destroy_after_hours_paused
        """
        now = datetime.utcnow()

        instances = self.session.query(ServerlessInstance).filter(
            ServerlessInstance.state == InstanceStateEnum.PAUSED,
            ServerlessInstance.paused_at.isnot(None),
            ServerlessInstance.destroy_after_hours_paused.isnot(None)
        ).all()

        return [
            inst for inst in instances
            if inst.should_destroy
        ]

    def get_instances_to_scale_down(self) -> List[ServerlessInstance]:
        """
        Retorna instâncias que devem fazer scale down.

        Critérios:
        - Estado = RUNNING
        - idle_since + scale_down_timeout < now
        """
        now = datetime.utcnow()

        instances = self.session.query(ServerlessInstance).filter(
            ServerlessInstance.state == InstanceStateEnum.RUNNING,
            ServerlessInstance.idle_since.isnot(None)
        ).all()

        result = []
        for inst in instances:
            idle_duration = (now - inst.idle_since).total_seconds()
            if idle_duration >= inst.scale_down_timeout_seconds:
                result.append(inst)

        return result

    # =========================================================================
    # SNAPSHOTS
    # =========================================================================

    def create_snapshot(
        self,
        instance_id: int,
        snapshot_type: str = "full",
        vast_snapshot_id: Optional[str] = None,
        r2_snapshot_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        size_gb: float = 0,
        gpu_state_included: bool = False,
    ) -> ServerlessSnapshot:
        """Cria registro de snapshot"""
        snapshot = ServerlessSnapshot(
            instance_id=instance_id,
            snapshot_type=snapshot_type,
            vast_snapshot_id=vast_snapshot_id,
            r2_snapshot_id=r2_snapshot_id,
            checkpoint_id=checkpoint_id,
            size_gb=size_gb,
            gpu_state_included=gpu_state_included,
        )
        self.session.add(snapshot)
        self.session.commit()
        return snapshot

    def get_latest_snapshot(self, instance_id: int) -> Optional[ServerlessSnapshot]:
        """Retorna snapshot mais recente válido"""
        return self.session.query(ServerlessSnapshot).filter(
            ServerlessSnapshot.instance_id == instance_id,
            ServerlessSnapshot.is_valid == True
        ).order_by(ServerlessSnapshot.created_at.desc()).first()

    def get_valid_snapshots(self, instance_id: int) -> List[ServerlessSnapshot]:
        """Retorna todos os snapshots válidos"""
        return self.session.query(ServerlessSnapshot).filter(
            ServerlessSnapshot.instance_id == instance_id,
            ServerlessSnapshot.is_valid == True
        ).order_by(ServerlessSnapshot.created_at.desc()).all()

    def invalidate_snapshot(self, snapshot_id: int):
        """Marca snapshot como inválido"""
        snapshot = self.session.query(ServerlessSnapshot).get(snapshot_id)
        if snapshot:
            snapshot.is_valid = False
            self.session.commit()

    # =========================================================================
    # EVENTS
    # =========================================================================

    def log_event(
        self,
        instance_id: int,
        user_id: str,
        event_type: EventTypeEnum,
        duration_seconds: Optional[float] = None,
        cost_saved: float = 0,
        details: Optional[Dict[str, Any]] = None,
    ) -> ServerlessEvent:
        """Registra evento serverless"""
        event = ServerlessEvent(
            instance_id=instance_id,
            user_id=user_id,
            event_type=event_type,
            duration_seconds=duration_seconds,
            cost_saved_usd=cost_saved,
            details=details or {},
        )
        self.session.add(event)
        self.session.commit()
        return event

    def get_user_events(
        self,
        user_id: str,
        since: Optional[datetime] = None,
        event_types: Optional[List[EventTypeEnum]] = None,
        limit: int = 100
    ) -> List[ServerlessEvent]:
        """Retorna eventos do usuário"""
        query = self.session.query(ServerlessEvent).filter(
            ServerlessEvent.user_id == user_id
        )

        if since:
            query = query.filter(ServerlessEvent.created_at >= since)

        if event_types:
            query = query.filter(ServerlessEvent.event_type.in_(event_types))

        return query.order_by(
            ServerlessEvent.created_at.desc()
        ).limit(limit).all()

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Retorna estatísticas agregadas do usuário"""
        instances = self.get_user_instances(user_id)

        total_savings = sum(i.total_savings_usd for i in instances)
        total_runtime = sum(i.total_runtime_seconds for i in instances)
        total_paused = sum(i.total_paused_seconds for i in instances)
        total_scale_downs = sum(i.scale_down_count for i in instances)
        total_scale_ups = sum(i.scale_up_count for i in instances)

        return {
            "total_instances": len(instances),
            "active_instances": len([i for i in instances if i.state == InstanceStateEnum.RUNNING]),
            "paused_instances": len([i for i in instances if i.state == InstanceStateEnum.PAUSED]),
            "total_savings_usd": round(total_savings, 2),
            "total_runtime_hours": round(total_runtime / 3600, 2),
            "total_paused_hours": round(total_paused / 3600, 2),
            "efficiency_percent": round(
                (total_paused / (total_runtime + total_paused) * 100) if (total_runtime + total_paused) > 0 else 0,
                1
            ),
            "total_scale_downs": total_scale_downs,
            "total_scale_ups": total_scale_ups,
        }
