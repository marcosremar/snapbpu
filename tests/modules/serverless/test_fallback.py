"""
Tests for Serverless Module - Fallback Strategies

Testes das estratégias de fallback quando resume falha.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.modules.serverless.fallback import (
    FallbackResult,
    SnapshotFallbackStrategy,
    DiskMigrationStrategy,
    FallbackOrchestrator,
)


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
        "disk_id": "disk_123",
    }
    provider.search_offers.return_value = [
        Mock(id=1, gpu_name="RTX 4090", dph_total=0.31)
    ]
    provider.create_instance.return_value = 99999
    return provider




class TestFallbackResult:
    """Testes do dataclass FallbackResult"""

    def test_success_result(self):
        """Resultado de sucesso"""
        result = FallbackResult(
            success=True,
            method="snapshot",
            new_instance_id=99999,
            original_instance_id=12345,
            duration_seconds=5.5,
        )

        assert result.success == True
        assert result.method == "snapshot"
        assert result.new_instance_id == 99999
        assert result.error is None

    def test_failure_result(self):
        """Resultado de falha"""
        result = FallbackResult(
            success=False,
            method="disk_migration",
            original_instance_id=12345,
            duration_seconds=2.0,
            error="No disk found"
        )

        assert result.success == False
        assert result.error == "No disk found"


class TestSnapshotFallbackStrategy:
    """Testes da estratégia de snapshot fallback"""

    def test_execute_no_instance(self, mock_vast_provider):
        """Deve falhar se instância não existe"""
        from contextlib import contextmanager

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        with patch('src.modules.serverless.repository.ServerlessRepository') as MockRepo:
            MockRepo.return_value.get_instance.return_value = None

            strategy = SnapshotFallbackStrategy(mock_vast_provider, session_factory)
            result = strategy.execute(
                original_instance_id=99999,
                user_id="test_user",
            )

            assert result.success == False
            assert "not found" in result.error.lower()

    def test_execute_no_snapshot(self, mock_vast_provider):
        """Deve falhar se não há snapshot válido"""
        from contextlib import contextmanager

        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.gpu_name = "RTX 4090"

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        with patch('src.modules.serverless.repository.ServerlessRepository') as MockRepo:
            MockRepo.return_value.get_instance.return_value = mock_instance
            MockRepo.return_value.get_latest_snapshot.return_value = None

            strategy = SnapshotFallbackStrategy(mock_vast_provider, session_factory)
            result = strategy.execute(
                original_instance_id=12345,
                user_id="test_user",
            )

            assert result.success == False
            assert "snapshot" in result.error.lower()


class TestDiskMigrationStrategy:
    """Testes da estratégia de disk migration"""

    def test_execute_no_instance(self, mock_vast_provider):
        """Deve falhar se instância não existe"""
        from contextlib import contextmanager

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        with patch('src.modules.serverless.repository.ServerlessRepository') as MockRepo:
            MockRepo.return_value.get_instance.return_value = None

            strategy = DiskMigrationStrategy(mock_vast_provider, session_factory)
            result = strategy.execute(
                original_instance_id=99999,
                user_id="test_user",
            )

            assert result.success == False
            assert "not found" in result.error.lower()

    def test_execute_no_disk(self, mock_vast_provider):
        """Deve falhar se não há disk_id"""
        from contextlib import contextmanager

        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.disk_id = None
        mock_instance.gpu_name = "RTX 4090"

        mock_vast_provider.get_instance_status.return_value = {
            "disk_id": None,
            "storage_id": None,
        }

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        with patch('src.modules.serverless.repository.ServerlessRepository') as MockRepo:
            MockRepo.return_value.get_instance.return_value = mock_instance

            strategy = DiskMigrationStrategy(mock_vast_provider, session_factory)
            result = strategy.execute(
                original_instance_id=12345,
                user_id="test_user",
            )

            assert result.success == False


class TestFallbackOrchestrator:
    """Testes do orquestrador de fallback"""

    def test_init(self, mock_vast_provider):
        """Deve inicializar com estratégias"""
        from contextlib import contextmanager

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        orchestrator = FallbackOrchestrator(mock_vast_provider, session_factory)

        assert orchestrator.snapshot_strategy is not None
        assert orchestrator.disk_strategy is not None

    def test_execute_fallback_all_failed(self, mock_vast_provider):
        """Deve retornar all_failed se todas estratégias falharem"""
        from contextlib import contextmanager

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        with patch('src.modules.serverless.repository.ServerlessRepository') as MockRepo:
            MockRepo.return_value.get_instance.return_value = None

            orchestrator = FallbackOrchestrator(mock_vast_provider, session_factory)
            result = orchestrator.execute_fallback(
                instance_id=99999,
                user_id="test_user",
            )

            assert result.success == False
            assert result.method == "all_failed"

    def test_prefer_snapshot_order(self, mock_vast_provider):
        """Deve tentar snapshot antes de disk migration quando prefer_snapshot=True"""
        from contextlib import contextmanager

        call_order = []

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        with patch('src.modules.serverless.repository.ServerlessRepository') as MockRepo:
            MockRepo.return_value.get_instance.return_value = None

            orchestrator = FallbackOrchestrator(mock_vast_provider, session_factory)

            # Patch execute methods to track call order
            original_snap = orchestrator.snapshot_strategy.execute
            original_disk = orchestrator.disk_strategy.execute

            def snap_execute(*args, **kwargs):
                call_order.append("snapshot")
                return original_snap(*args, **kwargs)

            def disk_execute(*args, **kwargs):
                call_order.append("disk")
                return original_disk(*args, **kwargs)

            orchestrator.snapshot_strategy.execute = snap_execute
            orchestrator.disk_strategy.execute = disk_execute

            orchestrator.execute_fallback(
                instance_id=12345,
                user_id="test_user",
                prefer_snapshot=True,
            )

        # Snapshot deve ser tentado primeiro
        assert call_order[0] == "snapshot"

    def test_prefer_disk_order(self, mock_vast_provider):
        """Deve tentar disk antes de snapshot quando prefer_snapshot=False"""
        from contextlib import contextmanager

        call_order = []

        @contextmanager
        def session_factory():
            session = Mock()
            yield session

        with patch('src.modules.serverless.repository.ServerlessRepository') as MockRepo:
            MockRepo.return_value.get_instance.return_value = None

            orchestrator = FallbackOrchestrator(mock_vast_provider, session_factory)

            # Patch execute methods to track call order
            original_snap = orchestrator.snapshot_strategy.execute
            original_disk = orchestrator.disk_strategy.execute

            def snap_execute(*args, **kwargs):
                call_order.append("snapshot")
                return original_snap(*args, **kwargs)

            def disk_execute(*args, **kwargs):
                call_order.append("disk")
                return original_disk(*args, **kwargs)

            orchestrator.snapshot_strategy.execute = snap_execute
            orchestrator.disk_strategy.execute = disk_execute

            orchestrator.execute_fallback(
                instance_id=12345,
                user_id="test_user",
                prefer_snapshot=False,
            )

        # Disk deve ser tentado primeiro
        assert call_order[0] == "disk"
