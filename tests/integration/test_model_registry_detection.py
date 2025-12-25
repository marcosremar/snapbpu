"""
Test Model Registry Detection

Testa a detecção automática de tipos de modelos usando o ModelRegistry.
"""

import pytest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


class TestModelRegistryDetection:
    """Testa detecção de modelos via static mapping e API"""

    def test_detect_llama_from_static_mapping(self):
        """Detecta LLaMA 3 8B sem API call (static mapping)"""
        from src.modules.models import get_registry, ModelRuntime, ModelTask

        registry = get_registry()

        # LLaMA deve ser detectado via static mapping (zero API)
        info = registry.get_model_info("meta-llama/Llama-3.1-8B-Instruct")

        assert info is not None
        assert info.task == ModelTask.TEXT_GENERATION
        assert info.runtime == ModelRuntime.VLLM
        assert "meta-llama" in info.model_id

        print(f"\n[LLAMA] Model: {info.model_id}")
        print(f"[LLAMA] Task: {info.task}")
        print(f"[LLAMA] Runtime: {info.runtime}")
        print(f"[LLAMA] Port: {info.default_port}")

    def test_detect_whisper_from_static_mapping(self):
        """Detecta Whisper sem API call (static mapping)"""
        from src.modules.models import get_registry, ModelRuntime, ModelTask

        registry = get_registry()

        info = registry.get_model_info("openai/whisper-large-v3")

        assert info is not None
        assert info.task == ModelTask.SPEECH_RECOGNITION
        assert info.runtime == ModelRuntime.TRANSFORMERS

        print(f"\n[WHISPER] Model: {info.model_id}")
        print(f"[WHISPER] Task: {info.task}")
        print(f"[WHISPER] Runtime: {info.runtime}")
        print(f"[WHISPER] Port: {info.default_port}")

    def test_detect_stable_diffusion_from_static_mapping(self):
        """Detecta Stable Diffusion sem API call"""
        from src.modules.models import get_registry, ModelRuntime, ModelTask

        registry = get_registry()

        info = registry.get_model_info("stabilityai/stable-diffusion-xl-base-1.0")

        assert info is not None
        assert info.task == ModelTask.TEXT_TO_IMAGE
        assert info.runtime == ModelRuntime.DIFFUSERS

        print(f"\n[SDXL] Model: {info.model_id}")
        print(f"[SDXL] Task: {info.task}")
        print(f"[SDXL] Runtime: {info.runtime}")

    def test_detect_embedding_model(self):
        """Detecta modelo de embeddings"""
        from src.modules.models import get_registry, ModelRuntime, ModelTask

        registry = get_registry()

        info = registry.get_model_info("sentence-transformers/all-MiniLM-L6-v2")

        assert info is not None
        assert info.task == ModelTask.FEATURE_EXTRACTION
        assert info.runtime == ModelRuntime.SENTENCE_TRANSFORMERS

        print(f"\n[EMBEDDINGS] Model: {info.model_id}")
        print(f"[EMBEDDINGS] Task: {info.task}")
        print(f"[EMBEDDINGS] Runtime: {info.runtime}")

    def test_detect_mistral_model(self):
        """Detecta Mistral como LLM com vLLM"""
        from src.modules.models import get_registry, ModelRuntime, ModelTask

        registry = get_registry()

        info = registry.get_model_info("mistralai/Mistral-7B-Instruct-v0.3")

        assert info is not None
        assert info.task == ModelTask.TEXT_GENERATION
        assert info.runtime == ModelRuntime.VLLM

        print(f"\n[MISTRAL] Model: {info.model_id}")
        print(f"[MISTRAL] Task: {info.task}")
        print(f"[MISTRAL] Runtime: {info.runtime}")

    def test_static_mapping_has_no_api_calls(self):
        """Verifica que static mapping não faz API calls"""
        from src.modules.models import get_registry

        registry = get_registry()

        # Patch API para falhar se for chamada
        with patch.object(registry, '_fetch_from_api', side_effect=Exception("Should not call API")):
            # Esses modelos devem usar static mapping
            models = [
                "meta-llama/Llama-3.1-8B-Instruct",
                "openai/whisper-large-v3",
                "stabilityai/stable-diffusion-xl-base-1.0",
                "mistralai/Mistral-7B-v0.1",
                "sentence-transformers/all-MiniLM-L6-v2",
            ]

            for model_id in models:
                info = registry.get_model_info(model_id)
                assert info is not None, f"Failed for {model_id}"
                print(f"[STATIC] {model_id} -> {info.runtime}")


class TestModelRegistryAPIFallback:
    """Testa fallback para API do HuggingFace"""

    def test_unknown_model_uses_fallback(self):
        """Modelo desconhecido retorna info default"""
        from src.modules.models import get_registry, ModelInfo

        registry = get_registry()

        # Modelo fictício não está no static mapping
        # Deve retornar info mesmo sem API (fallback)
        info = registry.get_model_info("unknown-org/unknown-model-xyz-123")

        # Deve retornar algo (mesmo que seja default/unknown)
        assert info is not None
        assert isinstance(info, ModelInfo)
        print(f"\n[FALLBACK] Unknown model handled: {info.runtime}")

    def test_caching_works_for_known_models(self):
        """Cache deve funcionar para modelos conhecidos"""
        from src.modules.models import get_registry

        registry = get_registry()

        # Primeira chamada
        info1 = registry.get_model_info("meta-llama/Llama-3.1-8B-Instruct")

        # Segunda chamada - deve usar cache (memory)
        info2 = registry.get_model_info("meta-llama/Llama-3.1-8B-Instruct")

        # Ambos devem ser iguais
        assert info1.model_id == info2.model_id
        assert info1.runtime == info2.runtime
        print(f"\n[CACHE] Memory cache working for known models")


class TestModelRegistryPorts:
    """Testa portas padrão por tipo de modelo"""

    def test_vllm_default_port(self):
        """vLLM usa porta 8000"""
        from src.modules.models import get_registry

        registry = get_registry()
        info = registry.get_model_info("meta-llama/Llama-3.1-8B-Instruct")

        assert info.default_port == 8000
        print(f"\n[PORT] vLLM: {info.default_port}")

    def test_transformers_default_port(self):
        """Transformers (Whisper) usa porta 8001"""
        from src.modules.models import get_registry

        registry = get_registry()
        info = registry.get_model_info("openai/whisper-large-v3")

        assert info.default_port == 8001
        print(f"\n[PORT] Transformers: {info.default_port}")

    def test_diffusers_default_port(self):
        """Diffusers usa porta 8002"""
        from src.modules.models import get_registry

        registry = get_registry()
        info = registry.get_model_info("stabilityai/stable-diffusion-xl-base-1.0")

        assert info.default_port == 8002
        print(f"\n[PORT] Diffusers: {info.default_port}")


class TestDownloader:
    """Testa o ModelDownloader"""

    def test_cache_check(self):
        """Verifica se modelo está em cache local"""
        from src.modules.models import get_downloader

        downloader = get_downloader()

        # Modelo provavelmente não está em cache
        cached = downloader.is_cached_locally("meta-llama/Llama-3.1-8B-Instruct")
        print(f"\n[CACHE] LLaMA cached locally: {cached}")

    def test_download_command_vllm(self):
        """Gera comando de download para vLLM"""
        from src.modules.models import get_downloader

        downloader = get_downloader()
        cmd = downloader.get_download_command("meta-llama/Llama-3.1-8B-Instruct", "vllm")

        assert "huggingface" in cmd.lower() or "snapshot_download" in cmd
        print(f"\n[DOWNLOAD] vLLM command generated")

    def test_download_command_diffusers(self):
        """Gera comando de download para Diffusers"""
        from src.modules.models import get_downloader

        downloader = get_downloader()
        cmd = downloader.get_download_command("stabilityai/stable-diffusion-xl-base-1.0", "diffusers")

        assert "diffusers" in cmd.lower() or "DiffusionPipeline" in cmd
        print(f"\n[DOWNLOAD] Diffusers command generated")


class TestServiceConfig:
    """Testa configuração do ServerlessModelService"""

    def test_deployment_config_defaults(self):
        """Verifica defaults do DeploymentConfig"""
        from src.modules.models import DeploymentConfig

        config = DeploymentConfig(model_id="test/model")

        assert config.gpu_type == "RTX 4090"
        assert config.gpu_count == 1
        assert config.idle_timeout_seconds == 300
        assert config.scale_to_zero == True
        assert config.runtime == "auto"
        print(f"\n[CONFIG] Defaults: GPU={config.gpu_type}, timeout={config.idle_timeout_seconds}s")

    def test_service_initialization(self):
        """Inicializa service sem provider"""
        from src.modules.models import ServerlessModelService

        service = ServerlessModelService()

        assert service.registry is not None
        assert service.downloader is not None
        print(f"\n[SERVICE] Initialized without GPU provider")


class TestEndToEndDetection:
    """Testa fluxo completo de detecção"""

    def test_llama_full_detection(self):
        """Detecta LLaMA e retorna config completa"""
        from src.modules.models import get_registry, get_downloader

        registry = get_registry()
        downloader = get_downloader()

        # Detectar
        info = registry.get_model_info("meta-llama/Llama-3.2-3B-Instruct")

        # Verificar info
        assert info is not None
        print(f"\n[E2E LLAMA]")
        print(f"  Model: {info.model_id}")
        print(f"  Task: {info.task}")
        print(f"  Runtime: {info.runtime}")
        print(f"  Size: {info.size_gb}GB")
        print(f"  Port: {info.default_port}")

        # Gerar comando de download
        cmd = downloader.get_download_command(info.model_id, info.runtime)
        print(f"  Download: {'huggingface' in cmd.lower()}")

    def test_whisper_full_detection(self):
        """Detecta Whisper e retorna config completa"""
        from src.modules.models import get_registry, get_downloader

        registry = get_registry()
        downloader = get_downloader()

        info = registry.get_model_info("openai/whisper-large-v3")

        assert info is not None
        print(f"\n[E2E WHISPER]")
        print(f"  Model: {info.model_id}")
        print(f"  Task: {info.task}")
        print(f"  Runtime: {info.runtime}")
        print(f"  Port: {info.default_port}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
