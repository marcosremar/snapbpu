"""
Tests for Serverless Module - Service

Testes do serviço com mocks do VAST.ai provider.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import threading
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.config.database import SessionLocal
from src.modules.serverless.service import ServerlessService, ScaleDownResult, ScaleUpResult
from src.modules.serverless.repository import ServerlessRepository
from src.modules.serverless.models import InstanceStateEnum


@pytest.fixture
def mock_vast_provider():
    """Mock do VAST.ai provider"""
    provider = Mock()
    provider.pause_instance.return_value = True
    provider.resume_instance.return_value = True
    provider.destroy_instance.return_value = True
    provider.get_instance_status.return_value = {
        "actual_status": "running",
        "gpu_name": "RTX 4090",
        "dph_total": 0.31,
        "ssh_host": "ssh.vast.ai",
        "ssh_port": 22,
    }
    provider.search_offers.return_value = [
        Mock(id=1, gpu_name="RTX 4090", dph_total=0.31)
    ]
    return provider


@pytest.fixture
def session_factory():
    """Factory de sessões do banco"""
    def factory():
        return SessionLocal()
    return factory


@pytest.fixture
def service(session_factory, mock_vast_provider):
    """Cria serviço para testes"""
    svc = ServerlessService(
        session_factory=session_factory,
        vast_provider=mock_vast_provider,
        check_interval=0.1,  # Check rápido para testes
    )
    yield svc
    svc.stop()


@pytest.fixture
def test_user_id():
    """ID de usuário único para testes"""
    import uuid
    return f"test_user_{uuid.uuid4().hex[:8]}"


class TestServiceConfiguration:
    """Testes de configuração do serviço"""

    def test_configure_user(self, service, test_user_id):
        """Deve configurar usuário corretamente"""
        result = service.configure_user(
            user_id=test_user_id,
            scale_down_timeout=2,
            destroy_after_hours=48,
        )

        assert result["user_id"] == test_user_id
        assert result["scale_down_timeout_seconds"] == 2
        assert result["destroy_after_hours_paused"] == 48

    def test_get_user_stats(self, service, test_user_id):
        """Deve retornar estatísticas do usuário"""
        # Configurar usuário primeiro
        service.configure_user(user_id=test_user_id)

        stats = service.get_user_stats(test_user_id)

        assert "total_instances" in stats
        assert "total_savings_usd" in stats
        assert "efficiency_percent" in stats


class TestEnableForInstance:
    """Testes de habilitação de serverless para instância"""

    def test_enable_for_instance(self, service, test_user_id, mock_vast_provider):
        """Deve habilitar serverless para instância"""
        import random
        instance_id = random.randint(10000000, 99999999)

        result = service.enable_for_instance(
            user_id=test_user_id,
            instance_id=instance_id,
            scale_down_timeout=5,
        )

        assert result["instance_id"] == instance_id
        assert result["scale_down_timeout_seconds"] == 5
        assert result["state"] == "running"


class TestScaleDown:
    """Testes de scale down (pause)"""

    def test_scale_down_after_timeout(self, service, test_user_id, mock_vast_provider):
        """Deve pausar após timeout sem requisição"""
        import random
        instance_id = random.randint(10000000, 99999999)

        # Habilitar com timeout curto
        service.enable_for_instance(
            user_id=test_user_id,
            instance_id=instance_id,
            scale_down_timeout=1,  # 1 segundo
        )

        # Iniciar serviço
        service.start()

        # Simular requisição e depois parar
        service.on_request_end(instance_id)

        # Aguardar scale down (timeout 1s + check interval 0.1s + margem)
        time.sleep(1.5)

        # Verificar se pause foi chamado
        mock_vast_provider.pause_instance.assert_called_with(instance_id)

    def test_no_scale_down_with_activity(self, service, test_user_id, mock_vast_provider):
        """Não deve pausar se há atividade contínua"""
        import random
        instance_id = random.randint(10000000, 99999999)

        # Habilitar com timeout curto
        service.enable_for_instance(
            user_id=test_user_id,
            instance_id=instance_id,
            scale_down_timeout=1,
        )

        # Iniciar serviço
        service.start()

        # Simular atividade contínua
        for _ in range(5):
            service.on_request_end(instance_id)
            time.sleep(0.3)

        # Verificar que pause não foi chamado
        mock_vast_provider.pause_instance.assert_not_called()


class TestScaleUp:
    """Testes de scale up (resume)"""

    def test_scale_up_on_request_when_paused(self, service, test_user_id, mock_vast_provider):
        """Deve acordar quando requisição chega em instância pausada"""
        import random
        instance_id = random.randint(10000000, 99999999)

        # Habilitar
        service.enable_for_instance(
            user_id=test_user_id,
            instance_id=instance_id,
            scale_down_timeout=1,
        )

        # Simular pausa manual no banco
        with service.session_factory() as session:
            repo = ServerlessRepository(session)
            repo.update_instance_state(instance_id, InstanceStateEnum.PAUSED)

        # Simular requisição
        result = service.on_request_start(instance_id)

        # Verificar que resume foi chamado
        mock_vast_provider.resume_instance.assert_called_with(instance_id)


class TestAutoDestroy:
    """Testes de auto-destroy"""

    def test_auto_destroy_after_hours_paused(self, service, test_user_id, mock_vast_provider):
        """Deve destruir instância após X horas pausada"""
        import random
        instance_id = random.randint(10000000, 99999999)

        # Habilitar com destroy após 1 hora
        service.configure_user(
            user_id=test_user_id,
            destroy_after_hours=1,
        )

        service.enable_for_instance(
            user_id=test_user_id,
            instance_id=instance_id,
        )

        # Simular pausa por mais de 1 hora
        with service.session_factory() as session:
            repo = ServerlessRepository(session)
            repo.update_instance_state(instance_id, InstanceStateEnum.PAUSED)
            instance = repo.get_instance(instance_id)
            instance.paused_at = datetime.utcnow() - timedelta(hours=2)
            session.commit()

        # Executar check de destroy manualmente
        service._check_auto_destroy()

        # Verificar que destroy foi chamado
        mock_vast_provider.destroy_instance.assert_called_with(instance_id)


class TestFallback:
    """Testes de fallback quando resume falha"""

    def test_fallback_to_snapshot_when_resume_fails(self, service, test_user_id, mock_vast_provider):
        """Deve tentar snapshot quando resume falha"""
        import random
        instance_id = random.randint(10000000, 99999999)

        # Configurar resume para falhar
        mock_vast_provider.resume_instance.return_value = False

        # Habilitar
        service.enable_for_instance(
            user_id=test_user_id,
            instance_id=instance_id,
        )

        # Criar snapshot para fallback
        with service.session_factory() as session:
            repo = ServerlessRepository(session)
            repo.update_instance_state(instance_id, InstanceStateEnum.PAUSED)
            instance = repo.get_instance(instance_id)
            repo.create_snapshot(
                instance_id=instance.id,
                snapshot_type="full",
                vast_snapshot_id="snap_123",
            )

        # Tentar scale up (deve tentar resume, falhar, e tentar snapshot)
        result = service.on_request_start(instance_id)

        # Verificar que tentou resume
        mock_vast_provider.resume_instance.assert_called()


class TestServiceLifecycle:
    """Testes do ciclo de vida do serviço"""

    def test_start_and_stop(self, session_factory, mock_vast_provider):
        """Deve iniciar e parar corretamente"""
        service = ServerlessService(
            session_factory=session_factory,
            vast_provider=mock_vast_provider,
            check_interval=0.1,
        )

        service.start()
        assert service._running == True
        assert service._monitor_thread.is_alive()

        service.stop()
        assert service._running == False

    def test_multiple_start_calls(self, service):
        """Múltiplas chamadas a start devem ser idempotentes"""
        service.start()
        service.start()
        service.start()

        # Deve ter apenas uma thread
        assert service._running == True
