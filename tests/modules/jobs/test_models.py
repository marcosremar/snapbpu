"""
Tests for Jobs Module - Database Models

Testes das models SQLAlchemy do módulo jobs.
"""

import pytest
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.modules.jobs.models import (
    Job,
    JobRun,
    JobLog,
    JobType,
    JobStatus,
    JobPriority,
)


class TestJobTypeEnum:
    """Testes do enum de tipos de job"""

    def test_all_types_exist(self):
        """Verifica que todos os tipos existem"""
        assert JobType.FINE_TUNE.value == "fine_tune"
        assert JobType.INFERENCE.value == "inference"
        assert JobType.TRAINING.value == "training"
        assert JobType.EMBEDDING.value == "embedding"
        assert JobType.CUSTOM.value == "custom"

    def test_type_from_string(self):
        """Verifica conversão de string para enum"""
        assert JobType("fine_tune") == JobType.FINE_TUNE
        assert JobType("custom") == JobType.CUSTOM


class TestJobStatusEnum:
    """Testes do enum de status"""

    def test_all_statuses_exist(self):
        """Verifica que todos os status existem"""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROVISIONING.value == "provisioning"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"
        assert JobStatus.TIMEOUT.value == "timeout"


class TestJobPriorityEnum:
    """Testes do enum de prioridade"""

    def test_all_priorities_exist(self):
        """Verifica que todas as prioridades existem"""
        assert JobPriority.LOW.value == "low"
        assert JobPriority.NORMAL.value == "normal"
        assert JobPriority.HIGH.value == "high"
        assert JobPriority.URGENT.value == "urgent"


class TestJob:
    """Testes do modelo Job"""

    def test_default_values(self):
        """Verifica valores padrão - usando Column defaults"""
        # Verificar que os defaults estão definidos nas colunas
        assert Job.max_price_per_hour.default.arg == 1.0
        assert Job.timeout_seconds.default.arg == 3600
        assert Job.max_retries.default.arg == 2
        assert Job.disk_gb.default.arg == 50

    def test_custom_values(self):
        """Verifica valores customizados"""
        job = Job(
            user_id="test_user",
            name="Fine-tune LLaMA",
            docker_image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
            job_type=JobType.FINE_TUNE,
            gpu_name="RTX 4090",
            max_price_per_hour=0.50,
            timeout_seconds=7200,
        )

        assert job.user_id == "test_user"
        assert job.name == "Fine-tune LLaMA"
        assert job.job_type == JobType.FINE_TUNE
        assert job.gpu_name == "RTX 4090"
        assert job.max_price_per_hour == 0.50
        assert job.timeout_seconds == 7200


class TestJobRun:
    """Testes do modelo JobRun"""

    def test_duration_seconds_not_started(self):
        """duration_seconds deve retornar None se não iniciou"""
        run = JobRun(
            job_id=1,
            user_id="test",
            status=JobStatus.PENDING,
            started_at=None,
            completed_at=None,
        )

        assert run.duration_seconds is None

    def test_duration_seconds_running(self):
        """duration_seconds deve calcular tempo em execução"""
        run = JobRun(
            job_id=1,
            user_id="test",
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=None,
        )

        # Deve ser aproximadamente 5 minutos = 300 segundos
        assert 290 < run.duration_seconds < 310

    def test_duration_seconds_completed(self):
        """duration_seconds deve calcular duração total"""
        start = datetime.utcnow() - timedelta(minutes=10)
        end = start + timedelta(minutes=5)

        run = JobRun(
            job_id=1,
            user_id="test",
            status=JobStatus.COMPLETED,
            started_at=start,
            completed_at=end,
        )

        # Deve ser exatamente 5 minutos = 300 segundos
        assert run.duration_seconds == 300

    def test_queue_time_seconds_not_started(self):
        """queue_time_seconds deve calcular tempo na fila antes de iniciar"""
        run = JobRun(
            job_id=1,
            user_id="test",
            status=JobStatus.PENDING,
            queued_at=datetime.utcnow() - timedelta(minutes=2),
            started_at=None,
        )

        # Deve ser aproximadamente 2 minutos = 120 segundos
        assert 110 < run.queue_time_seconds < 130

    def test_queue_time_seconds_started(self):
        """queue_time_seconds deve calcular tempo na fila até início"""
        queued = datetime.utcnow() - timedelta(minutes=5)
        started = queued + timedelta(minutes=3)

        run = JobRun(
            job_id=1,
            user_id="test",
            status=JobStatus.RUNNING,
            queued_at=queued,
            started_at=started,
        )

        # Deve ser exatamente 3 minutos = 180 segundos
        assert run.queue_time_seconds == 180


class TestJobLog:
    """Testes do modelo JobLog"""

    def test_log_creation(self):
        """Verifica criação de log"""
        log = JobLog(
            run_id=1,
            message="Job iniciado",
            level="INFO",
            stage="execution",
        )

        assert log.run_id == 1
        assert log.message == "Job iniciado"
        assert log.level == "INFO"
        assert log.stage == "execution"

    def test_log_levels(self):
        """Verifica diferentes níveis de log"""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

        for level in levels:
            log = JobLog(run_id=1, message="Test", level=level)
            assert log.level == level
