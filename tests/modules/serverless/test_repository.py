"""
Tests for Serverless Module - Repository

Testes do repository com banco de dados real (PostgreSQL).
"""

import pytest
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from sqlalchemy.orm import Session
from src.config.database import engine, SessionLocal
from src.modules.serverless.repository import ServerlessRepository
from src.modules.serverless.models import (
    ServerlessUserSettings,
    ServerlessInstance,
    ServerlessSnapshot,
    ServerlessEvent,
    ServerlessModeEnum,
    InstanceStateEnum,
    EventTypeEnum,
    create_serverless_schema,
)


@pytest.fixture(scope="module")
def db_session():
    """Cria sessão de banco para testes"""
    # Garantir que schema existe
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS serverless"))
        conn.commit()

    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repo(db_session):
    """Cria repository para testes"""
    return ServerlessRepository(db_session)


@pytest.fixture
def test_user_id():
    """ID de usuário único para testes"""
    import uuid
    return f"test_user_{uuid.uuid4().hex[:8]}"


class TestUserSettings:
    """Testes de configuração de usuário"""

    def test_get_or_create_user_settings(self, repo, test_user_id):
        """Deve criar settings se não existir"""
        settings = repo.get_or_create_user_settings(test_user_id)

        assert settings is not None
        assert settings.user_id == test_user_id
        assert settings.scale_down_timeout_seconds == 30  # default

    def test_get_existing_settings(self, repo, test_user_id):
        """Deve retornar settings existente"""
        # Criar
        settings1 = repo.get_or_create_user_settings(test_user_id)

        # Buscar novamente
        settings2 = repo.get_or_create_user_settings(test_user_id)

        assert settings1.id == settings2.id

    def test_update_user_settings(self, repo, test_user_id):
        """Deve atualizar settings corretamente"""
        settings = repo.update_user_settings(
            user_id=test_user_id,
            scale_down_timeout=2,
            destroy_after_hours=48,
        )

        assert settings.scale_down_timeout_seconds == 2
        assert settings.destroy_after_hours_paused == 48


class TestInstances:
    """Testes de instâncias serverless"""

    def test_create_instance(self, repo, test_user_id):
        """Deve criar instância corretamente"""
        import random
        vast_id = random.randint(10000000, 99999999)

        instance = repo.create_instance(
            user_id=test_user_id,
            vast_instance_id=vast_id,
            mode="economic",
            scale_down_timeout=5,
            gpu_name="RTX 4090",
            hourly_cost=0.31,
        )

        assert instance is not None
        assert instance.vast_instance_id == vast_id
        assert instance.state == InstanceStateEnum.RUNNING
        assert instance.scale_down_timeout_seconds == 5

    def test_update_instance_state_to_paused(self, repo, test_user_id):
        """Deve atualizar estado para pausado"""
        import random
        vast_id = random.randint(10000000, 99999999)

        instance = repo.create_instance(
            user_id=test_user_id,
            vast_instance_id=vast_id,
            mode="economic",
            scale_down_timeout=5,
        )

        updated = repo.update_instance_state(vast_id, InstanceStateEnum.PAUSED)

        assert updated.state == InstanceStateEnum.PAUSED
        assert updated.paused_at is not None
        assert updated.scale_down_count == 1

    def test_update_instance_state_to_running(self, repo, test_user_id):
        """Deve calcular savings ao voltar para running"""
        import random
        vast_id = random.randint(10000000, 99999999)

        instance = repo.create_instance(
            user_id=test_user_id,
            vast_instance_id=vast_id,
            mode="economic",
            scale_down_timeout=5,
            hourly_cost=1.0,  # $1/hr para facilitar cálculo
        )

        # Pausar
        repo.update_instance_state(vast_id, InstanceStateEnum.PAUSED)

        # Simular 1 hora pausado
        instance = repo.get_instance(vast_id)
        instance.paused_at = datetime.utcnow() - timedelta(hours=1)
        repo.session.commit()

        # Voltar para running
        updated = repo.update_instance_state(vast_id, InstanceStateEnum.RUNNING)

        assert updated.state == InstanceStateEnum.RUNNING
        assert updated.paused_at is None
        assert updated.scale_up_count == 1
        assert updated.total_paused_seconds > 3500  # ~1 hora
        assert updated.total_savings_usd > 0.9  # ~$1

    def test_get_instances_to_destroy(self, repo, test_user_id):
        """Deve retornar instâncias que devem ser destruídas"""
        import random
        vast_id = random.randint(10000000, 99999999)

        instance = repo.create_instance(
            user_id=test_user_id,
            vast_instance_id=vast_id,
            mode="economic",
            scale_down_timeout=5,
        )

        # Configurar para destruir após 1 hora
        instance.destroy_after_hours_paused = 1
        repo.session.commit()

        # Pausar
        repo.update_instance_state(vast_id, InstanceStateEnum.PAUSED)

        # Simular 2 horas pausado
        instance = repo.get_instance(vast_id)
        instance.paused_at = datetime.utcnow() - timedelta(hours=2)
        repo.session.commit()

        # Buscar instâncias para destruir
        to_destroy = repo.get_instances_to_destroy()

        assert any(i.vast_instance_id == vast_id for i in to_destroy)


class TestSnapshots:
    """Testes de snapshots"""

    def test_create_snapshot(self, repo, test_user_id):
        """Deve criar snapshot corretamente"""
        import random
        vast_id = random.randint(10000000, 99999999)

        instance = repo.create_instance(
            user_id=test_user_id,
            vast_instance_id=vast_id,
            mode="economic",
            scale_down_timeout=5,
        )

        snapshot = repo.create_snapshot(
            instance_id=instance.id,
            snapshot_type="full",
            vast_snapshot_id="snap_123",
            size_gb=50.0,
        )

        assert snapshot is not None
        assert snapshot.vast_snapshot_id == "snap_123"
        assert snapshot.is_valid == True

    def test_get_latest_snapshot(self, repo, test_user_id):
        """Deve retornar snapshot mais recente"""
        import random
        vast_id = random.randint(10000000, 99999999)

        instance = repo.create_instance(
            user_id=test_user_id,
            vast_instance_id=vast_id,
            mode="economic",
            scale_down_timeout=5,
        )

        # Criar 2 snapshots
        snap1 = repo.create_snapshot(instance.id, "full", vast_snapshot_id="snap_1")
        snap2 = repo.create_snapshot(instance.id, "full", vast_snapshot_id="snap_2")

        latest = repo.get_latest_snapshot(instance.id)

        assert latest.vast_snapshot_id == "snap_2"


class TestEvents:
    """Testes de eventos"""

    def test_log_event(self, repo, test_user_id):
        """Deve registrar evento corretamente"""
        import random
        vast_id = random.randint(10000000, 99999999)

        instance = repo.create_instance(
            user_id=test_user_id,
            vast_instance_id=vast_id,
            mode="economic",
            scale_down_timeout=5,
        )

        event = repo.log_event(
            instance_id=instance.id,
            user_id=test_user_id,
            event_type=EventTypeEnum.SCALE_DOWN,
            duration_seconds=0.7,
            cost_saved=0.05,
            details={"reason": "idle_timeout"},
        )

        assert event is not None
        assert event.event_type == EventTypeEnum.SCALE_DOWN
        assert event.details["reason"] == "idle_timeout"

    def test_get_user_stats(self, repo, test_user_id):
        """Deve calcular estatísticas corretamente"""
        import random

        # Criar algumas instâncias com savings
        for _ in range(3):
            vast_id = random.randint(10000000, 99999999)
            instance = repo.create_instance(
                user_id=test_user_id,
                vast_instance_id=vast_id,
                mode="economic",
                scale_down_timeout=5,
            )
            instance.total_savings_usd = 10.0
            instance.total_runtime_seconds = 3600
            instance.total_paused_seconds = 7200
            repo.session.commit()

        stats = repo.get_user_stats(test_user_id)

        assert stats["total_instances"] >= 3
        assert stats["total_savings_usd"] >= 30.0
