"""
Tests for Serverless Module - Database Models

Testes das models SQLAlchemy do módulo serverless.
"""

import pytest
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.modules.serverless.models import (
    ServerlessUserSettings,
    ServerlessInstance,
    ServerlessSnapshot,
    ServerlessEvent,
    ServerlessModeEnum,
    InstanceStateEnum,
    EventTypeEnum,
)


class TestServerlessModeEnum:
    """Testes do enum de modos serverless"""

    def test_all_modes_exist(self):
        """Verifica que todos os modos existem"""
        assert ServerlessModeEnum.DISABLED.value == "disabled"
        assert ServerlessModeEnum.FAST.value == "fast"
        assert ServerlessModeEnum.ECONOMIC.value == "economic"
        assert ServerlessModeEnum.SPOT.value == "spot"

    def test_mode_from_string(self):
        """Verifica conversão de string para enum"""
        assert ServerlessModeEnum("fast") == ServerlessModeEnum.FAST
        assert ServerlessModeEnum("economic") == ServerlessModeEnum.ECONOMIC


class TestInstanceStateEnum:
    """Testes do enum de estados"""

    def test_all_states_exist(self):
        """Verifica que todos os estados existem"""
        assert InstanceStateEnum.RUNNING.value == "running"
        assert InstanceStateEnum.PAUSED.value == "paused"
        assert InstanceStateEnum.WAKING.value == "waking"
        assert InstanceStateEnum.DESTROYED.value == "destroyed"
        assert InstanceStateEnum.FAILED.value == "failed"


class TestEventTypeEnum:
    """Testes do enum de tipos de evento"""

    def test_all_event_types_exist(self):
        """Verifica que todos os tipos de evento existem"""
        assert EventTypeEnum.SCALE_DOWN.value == "scale_down"
        assert EventTypeEnum.SCALE_UP.value == "scale_up"
        assert EventTypeEnum.AUTO_DESTROY.value == "auto_destroy"
        assert EventTypeEnum.RESUME_FAILED.value == "resume_failed"
        assert EventTypeEnum.FALLBACK_SNAPSHOT.value == "fallback_snapshot"
        assert EventTypeEnum.FALLBACK_DISK.value == "fallback_disk"


class TestServerlessUserSettings:
    """Testes do modelo de configuração de usuário"""

    def test_default_values(self):
        """Verifica valores padrão - usando Column defaults"""
        # Nota: defaults são aplicados pelo SQLAlchemy no commit, não no __init__
        # Então testamos os valores do Column.default
        from src.modules.serverless.models import ServerlessUserSettings

        # Verificar que os defaults estão definidos nas colunas
        assert ServerlessUserSettings.scale_down_timeout_seconds.default.arg == 30
        assert ServerlessUserSettings.destroy_after_hours_paused.default.arg == 24
        assert ServerlessUserSettings.auto_destroy_enabled.default.arg == True
        assert ServerlessUserSettings.fallback_enabled.default.arg == True

    def test_custom_values(self):
        """Verifica valores customizados"""
        settings = ServerlessUserSettings(
            user_id="custom_user",
            default_mode=ServerlessModeEnum.FAST,
            scale_down_timeout_seconds=2,
            destroy_after_hours_paused=48,
        )

        assert settings.scale_down_timeout_seconds == 2
        assert settings.destroy_after_hours_paused == 48
        assert settings.default_mode == ServerlessModeEnum.FAST


class TestServerlessInstance:
    """Testes do modelo de instância serverless"""

    def test_hours_paused_when_not_paused(self):
        """hours_paused deve retornar 0 se não está pausado"""
        instance = ServerlessInstance(
            user_id="test",
            vast_instance_id=12345,
            mode=ServerlessModeEnum.ECONOMIC,
            scale_down_timeout_seconds=30,
            state=InstanceStateEnum.RUNNING,
            paused_at=None,
        )

        assert instance.hours_paused == 0

    def test_hours_paused_when_paused(self):
        """hours_paused deve calcular tempo corretamente"""
        instance = ServerlessInstance(
            user_id="test",
            vast_instance_id=12345,
            mode=ServerlessModeEnum.ECONOMIC,
            scale_down_timeout_seconds=30,
            state=InstanceStateEnum.PAUSED,
            paused_at=datetime.utcnow() - timedelta(hours=2),
        )

        assert 1.9 < instance.hours_paused < 2.1  # ~2 horas

    def test_should_destroy_when_not_paused(self):
        """should_destroy deve retornar False se não está pausado"""
        instance = ServerlessInstance(
            user_id="test",
            vast_instance_id=12345,
            mode=ServerlessModeEnum.ECONOMIC,
            scale_down_timeout_seconds=30,
            state=InstanceStateEnum.RUNNING,
            destroy_after_hours_paused=24,
        )

        assert instance.should_destroy == False

    def test_should_destroy_when_under_limit(self):
        """should_destroy deve retornar False se ainda não atingiu limite"""
        instance = ServerlessInstance(
            user_id="test",
            vast_instance_id=12345,
            mode=ServerlessModeEnum.ECONOMIC,
            scale_down_timeout_seconds=30,
            state=InstanceStateEnum.PAUSED,
            paused_at=datetime.utcnow() - timedelta(hours=12),
            destroy_after_hours_paused=24,
        )

        assert instance.should_destroy == False

    def test_should_destroy_when_over_limit(self):
        """should_destroy deve retornar True se passou do limite"""
        instance = ServerlessInstance(
            user_id="test",
            vast_instance_id=12345,
            mode=ServerlessModeEnum.ECONOMIC,
            scale_down_timeout_seconds=30,
            state=InstanceStateEnum.PAUSED,
            paused_at=datetime.utcnow() - timedelta(hours=25),
            destroy_after_hours_paused=24,
        )

        assert instance.should_destroy == True


class TestServerlessSnapshot:
    """Testes do modelo de snapshot"""

    def test_default_values(self):
        """Verifica valores padrão - usando Column defaults"""
        from src.modules.serverless.models import ServerlessSnapshot

        # Verificar defaults nas colunas
        assert ServerlessSnapshot.is_valid.default.arg == True
        assert ServerlessSnapshot.gpu_state_included.default.arg == False


class TestServerlessEvent:
    """Testes do modelo de evento"""

    def test_event_creation(self):
        """Verifica criação de evento"""
        event = ServerlessEvent(
            instance_id=1,
            user_id="test",
            event_type=EventTypeEnum.SCALE_DOWN,
            duration_seconds=0.7,
            cost_saved_usd=0.05,
        )

        assert event.event_type == EventTypeEnum.SCALE_DOWN
        assert event.duration_seconds == 0.7
        assert event.cost_saved_usd == 0.05
