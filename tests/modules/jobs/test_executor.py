"""
Tests for Jobs Module - Executor

Testes do executor de jobs GPU.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.modules.jobs.executor import JobExecutor, FineTuneExecutor, ExecutionResult


class TestExecutionResult:
    """Testes do dataclass ExecutionResult"""

    def test_success_result(self):
        """Verifica resultado de sucesso"""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            duration_seconds=120.5,
            output="Training complete",
            cost_usd=0.15,
            gpu_name="RTX 4090",
            instance_id=12345,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.duration_seconds == 120.5
        assert result.cost_usd == 0.15

    def test_failure_result(self):
        """Verifica resultado de falha"""
        result = ExecutionResult(
            success=False,
            exit_code=1,
            duration_seconds=30.0,
            error="Out of memory",
            instance_id=12345,
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.error == "Out of memory"


class TestJobExecutor:
    """Testes do JobExecutor"""

    def test_build_onstart_script_empty(self):
        """Script vazio quando não há configuração"""
        mock_vast = Mock()
        executor = JobExecutor(mock_vast)

        script = executor._build_onstart_script({})

        assert script is None

    def test_build_onstart_script_with_env_vars(self):
        """Script com variáveis de ambiente"""
        mock_vast = Mock()
        executor = JobExecutor(mock_vast)

        config = {
            "env_vars": {
                "HF_TOKEN": "secret123",
                "MODEL_NAME": "llama-7b",
            }
        }

        script = executor._build_onstart_script(config)

        assert script is not None
        assert 'export HF_TOKEN="secret123"' in script
        assert 'export MODEL_NAME="llama-7b"' in script

    def test_build_onstart_script_with_s3_input(self):
        """Script com download de S3"""
        mock_vast = Mock()
        executor = JobExecutor(mock_vast)

        config = {
            "input_path": "s3://my-bucket/data/",
        }

        script = executor._build_onstart_script(config)

        assert script is not None
        assert "aws s3 sync s3://my-bucket/data/ /workspace/input" in script

    def test_build_onstart_script_with_gcs_input(self):
        """Script com download de GCS"""
        mock_vast = Mock()
        executor = JobExecutor(mock_vast)

        config = {
            "input_path": "gs://my-bucket/data/",
        }

        script = executor._build_onstart_script(config)

        assert script is not None
        assert "gsutil -m cp -r gs://my-bucket/data/ /workspace/input" in script

    def test_build_onstart_script_with_http_input(self):
        """Script com download via HTTP"""
        mock_vast = Mock()
        executor = JobExecutor(mock_vast)

        config = {
            "input_path": "https://example.com/data.tar.gz",
        }

        script = executor._build_onstart_script(config)

        assert script is not None
        assert "wget -P /workspace/input https://example.com/data.tar.gz" in script

    def test_execute_no_offers(self):
        """Execute deve falhar quando não há GPUs disponíveis"""
        mock_vast = Mock()
        mock_vast.search_offers.return_value = []

        executor = JobExecutor(mock_vast)

        result = executor.execute({
            "docker_image": "pytorch/pytorch:latest",
            "gpu_name": "RTX 4090",
            "max_price": 0.50,
        })

        assert result.success is False
        assert "Nenhuma GPU disponível" in result.error

    def test_execute_create_instance_fails(self):
        """Execute deve falhar quando criar instância falha"""
        mock_vast = Mock()
        mock_vast.search_offers.return_value = [
            {"id": 123, "gpu_name": "RTX 4090", "dph_total": 0.45}
        ]
        mock_vast.create_instance.return_value = None

        executor = JobExecutor(mock_vast)

        result = executor.execute({
            "docker_image": "pytorch/pytorch:latest",
            "gpu_name": "RTX 4090",
            "max_price": 0.50,
        })

        assert result.success is False
        assert "Falha ao criar instância" in result.error


class TestFineTuneExecutor:
    """Testes do FineTuneExecutor"""

    def test_build_finetune_config(self):
        """Verifica configuração de fine-tuning"""
        mock_vast = Mock()
        executor = FineTuneExecutor(mock_vast)

        config = executor.build_finetune_config(
            base_model="meta-llama/Llama-2-7b",
            dataset_path="s3://my-bucket/train.json",
            output_path="s3://my-bucket/output/",
            num_epochs=5,
            batch_size=8,
            learning_rate=1e-5,
        )

        assert config["docker_image"] == "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"
        assert config["input_path"] == "s3://my-bucket/train.json"
        assert config["output_path"] == "s3://my-bucket/output/"
        assert config["gpu_name"] == "RTX 4090"
        assert config["max_price"] == 0.50
        assert config["timeout_seconds"] == 14400  # 4 horas
        assert "meta-llama/Llama-2-7b" in config["command"]
        assert "num_train_epochs=5" in config["command"]
        assert "per_device_train_batch_size=8" in config["command"]

    def test_build_finetune_config_with_extra_args(self):
        """Verifica configuração com argumentos extras"""
        mock_vast = Mock()
        executor = FineTuneExecutor(mock_vast)

        config = executor.build_finetune_config(
            base_model="gpt2",
            dataset_path="s3://bucket/data.json",
            output_path="s3://bucket/output/",
            extra_args={
                "disk_gb": 200,
                "max_price": 1.0,
            }
        )

        assert config["disk_gb"] == 200
        assert config["max_price"] == 1.0
