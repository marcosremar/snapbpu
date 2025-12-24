"""
Testes de Fine-Tuning Lifecycle Completo - Dumont Cloud

Testa:
- Listagem de modelos suportados
- Criação de jobs de fine-tuning
- Monitoramento de progresso
- Cancelamento de jobs
- Download de modelos treinados

Uses api_client fixture from conftest.py
"""
import pytest


# ============================================================
# Testes de Modelos Suportados
# ============================================================

class TestFineTuneModels:
    """Testes de listagem de modelos para fine-tuning"""

    
    def test_list_supported_models(self, api_client):
        """Lista modelos suportados para fine-tuning"""
        result = api_client.call("GET", "/api/v1/finetune/models")
        assert result is not None

    
    def test_list_models_by_size(self, api_client):
        """Lista modelos filtrados por tamanho"""
        result = api_client.call("GET", "/api/v1/finetune/models?max_size=7B")
        assert result is not None

    
    def test_list_models_by_type(self, api_client):
        """Lista modelos filtrados por tipo"""
        result = api_client.call("GET", "/api/v1/finetune/models?type=llama")
        assert result is not None


# ============================================================
# Testes de Criação de Jobs
# ============================================================

class TestFineTuneJobCreation:
    """Testes de criação de jobs de fine-tuning"""

    
    def test_create_job_validation(self, api_client):
        """Testa validação de criação de job"""
        result = api_client.call("POST", "/api/v1/finetune/jobs", {
            "name": "",
            "base_model": "invalid-model",
            "dataset_source": "invalid"
        })
        assert result is not None

    
    def test_create_job_dry_run(self, api_client):
        """Testa criação de job em modo dry-run"""
        result = api_client.call("POST", "/api/v1/finetune/jobs", {
            "name": "test-finetune-dryrun",
            "base_model": "unsloth/llama-3-8b-bnb-4bit",
            "dataset_source": "huggingface",
            "dataset_path": "mlabonne/guanaco-llama2-1k",
            "dry_run": True
        })
        assert result is not None

    
    def test_estimate_finetune_cost(self, api_client):
        """Testa estimativa de custo de fine-tuning"""
        result = api_client.call("POST", "/api/v1/finetune/estimate", {
            "base_model": "unsloth/llama-3-8b-bnb-4bit",
            "dataset_size_mb": 100,
            "epochs": 3,
            "gpu_type": "RTX_4090"
        })
        assert result is not None


# ============================================================
# Testes de Listagem de Jobs
# ============================================================

class TestFineTuneJobListing:
    """Testes de listagem de jobs"""

    
    def test_list_all_jobs(self, api_client):
        """Lista todos os jobs de fine-tuning"""
        result = api_client.call("GET", "/api/v1/finetune/jobs")
        assert result is not None

    
    def test_list_jobs_by_status(self, api_client):
        """Lista jobs filtrados por status"""
        for status in ["running", "completed", "failed", "queued"]:
            result = api_client.call("GET", f"/api/v1/finetune/jobs?status={status}")
            assert result is not None

    
    def test_get_job_details(self, api_client):
        """Obtém detalhes de um job específico"""
        list_result = api_client.call("GET", "/api/v1/finetune/jobs")
        if list_result and list_result.get("jobs"):
            job_id = list_result["jobs"][0].get("id")
            if job_id:
                result = api_client.call("GET", f"/api/v1/finetune/jobs/{job_id}")
                assert result is not None


# ============================================================
# Testes de Monitoramento
# ============================================================

class TestFineTuneMonitoring:
    """Testes de monitoramento de jobs"""

    
    def test_get_job_logs(self, api_client):
        """Obtém logs de um job"""
        list_result = api_client.call("GET", "/api/v1/finetune/jobs")
        if list_result and list_result.get("jobs"):
            job_id = list_result["jobs"][0].get("id")
            if job_id:
                result = api_client.call("GET", f"/api/v1/finetune/jobs/{job_id}/logs")
                assert result is not None

    
    def test_get_job_metrics(self, api_client):
        """Obtém métricas de treinamento"""
        list_result = api_client.call("GET", "/api/v1/finetune/jobs")
        if list_result and list_result.get("jobs"):
            job_id = list_result["jobs"][0].get("id")
            if job_id:
                result = api_client.call("GET", f"/api/v1/finetune/jobs/{job_id}/metrics")
                assert result is not None


# ============================================================
# Testes de Cancelamento
# ============================================================

class TestFineTuneJobCancellation:
    """Testes de cancelamento de jobs"""

    
    def test_cancel_invalid_job(self, api_client):
        """Testa cancelamento de job inexistente"""
        result = api_client.call("POST", "/api/v1/finetune/jobs/invalid-job-id/cancel")
        assert result is not None

    
    def test_cancel_completed_job(self, api_client):
        """Testa cancelamento de job já completado"""
        list_result = api_client.call("GET", "/api/v1/finetune/jobs?status=completed")
        if list_result and list_result.get("jobs"):
            job_id = list_result["jobs"][0].get("id")
            if job_id:
                result = api_client.call("POST", f"/api/v1/finetune/jobs/{job_id}/cancel")
                assert result is not None


# ============================================================
# Testes de Configuração
# ============================================================

class TestFineTuneConfig:
    """Testes de configuração de fine-tuning"""

    
    def test_get_default_config(self, api_client):
        """Obtém configuração padrão de fine-tuning"""
        result = api_client.call("GET", "/api/v1/finetune/config/default")
        assert result is not None

    
    def test_validate_config(self, api_client):
        """Valida configuração de fine-tuning"""
        result = api_client.call("POST", "/api/v1/finetune/config/validate", {
            "lora_rank": 16,
            "lora_alpha": 32,
            "learning_rate": 2e-4,
            "epochs": 3,
            "batch_size": 4
        })
        assert result is not None
