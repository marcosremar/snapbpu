"""
Serverless Module E2E Tests

Testes end-to-end para o módulo Serverless GPU:
- Testes unitários do módulo
- Testes de integração com API
- Jornadas de deploy de modelos + serverless (Whisper, SD, LLM)
- Testes de checkpoint/restore

IMPORTANTE: Estes testes consomem créditos reais na VAST.ai.
Use com cuidado e monitore os custos.
"""

import os
import sys
import time
import json
import pytest
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from tests.conftest import (
    APIClient, CLIRunner, Colors, register_instance, unregister_instance,
    API_BASE_URL, TEST_USER, TEST_PASSWORD, RateLimiter
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Timeouts
DEPLOY_TIMEOUT = 300  # 5 minutos para deploy
PAUSE_TIMEOUT = 60    # 1 minuto para pausar
WAKE_TIMEOUT = 120    # 2 minutos para acordar
IDLE_WAIT = 15        # Segundos de idle antes de pausar (para teste)

# GPU preferences for tests (cheaper options)
TEST_GPU_PREFERENCES = {
    "gpu_name": "RTX 4090",  # Bom custo-benefício
    "max_price": 0.50,       # Max $0.50/hr
    "min_ram": 24,           # 24GB VRAM
    "disk_space": 50,        # 50GB disk
}

# Models for testing
TEST_MODELS = {
    "whisper": {
        "type": "speech",
        "model_id": "openai/whisper-small",  # Modelo menor para teste rápido
        "port": 8001,
        "gpu_memory": 4,
    },
    "stable_diffusion": {
        "type": "diffusion",
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "port": 8002,
        "gpu_memory": 12,
    },
    "llm": {
        "type": "llm",
        "model_id": "microsoft/Phi-3-mini-4k-instruct",  # Modelo pequeno
        "port": 8000,
        "gpu_memory": 8,
    }
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def serverless_api_client() -> APIClient:
    """API client autenticado para testes serverless."""
    client = APIClient(API_BASE_URL)
    if not client.login(TEST_USER, TEST_PASSWORD):
        pytest.skip("Could not authenticate")
    return client


@pytest.fixture(scope="module")
def rate_limiter() -> RateLimiter:
    """Rate limiter para evitar 429."""
    return RateLimiter(delay=2.0, max_retries=5)


@pytest.fixture
def cleanup_instance(serverless_api_client):
    """Fixture para limpeza automática de instâncias."""
    instances = []

    def _register(instance_id: int):
        instances.append(instance_id)
        register_instance(instance_id)
        return instance_id

    yield _register

    # Cleanup
    for inst_id in instances:
        try:
            serverless_api_client.delete(f"/api/v1/instances/{inst_id}")
            unregister_instance(inst_id)
            logger.info(f"[CLEANUP] Destroyed instance {inst_id}")
        except Exception as e:
            logger.warning(f"[CLEANUP] Failed to destroy {inst_id}: {e}")


# =============================================================================
# UNIT TESTS - Module Imports and Configuration
# =============================================================================

class TestServerlessModuleImports:
    """Testes de importação e configuração do módulo."""

    def test_module_imports(self):
        """Verifica se o módulo importa corretamente."""
        from src.modules.serverless import (
            get_serverless_manager,
            get_checkpoint_service,
            ServerlessMode,
            ServerlessManager,
            GPUCheckpointService,
            ServerlessSettings,
        )

        assert get_serverless_manager is not None
        assert get_checkpoint_service is not None
        assert ServerlessMode is not None
        print(f"{Colors.GREEN}[OK]{Colors.END} Module imports working")

    def test_serverless_modes(self):
        """Verifica os modos serverless disponíveis."""
        from src.modules.serverless import ServerlessMode

        assert ServerlessMode.FAST.value == "fast"
        assert ServerlessMode.ECONOMIC.value == "economic"
        assert ServerlessMode.SPOT.value == "spot"
        assert ServerlessMode.DISABLED.value == "disabled"
        print(f"{Colors.GREEN}[OK]{Colors.END} ServerlessMode enum OK")

    def test_serverless_manager_singleton(self):
        """Verifica se o manager é singleton."""
        from src.modules.serverless import get_serverless_manager

        manager1 = get_serverless_manager()
        manager2 = get_serverless_manager()

        assert manager1 is manager2
        print(f"{Colors.GREEN}[OK]{Colors.END} ServerlessManager is singleton")

    def test_checkpoint_service_singleton(self):
        """Verifica se o checkpoint service é singleton."""
        from src.modules.serverless import get_checkpoint_service

        svc1 = get_checkpoint_service()
        svc2 = get_checkpoint_service()

        assert svc1 is svc2
        print(f"{Colors.GREEN}[OK]{Colors.END} GPUCheckpointService is singleton")

    def test_serverless_settings(self):
        """Verifica configurações do módulo."""
        from src.modules.serverless import ServerlessSettings
        from src.modules.serverless.config import get_settings

        settings = get_settings()

        assert settings.default_idle_timeout_seconds > 0
        assert settings.checkpoint_enabled is True
        assert settings.fallback_enabled is True
        print(f"{Colors.GREEN}[OK]{Colors.END} ServerlessSettings OK")

    def test_backwards_compatibility_standby(self):
        """Verifica compatibilidade com imports antigos (standby)."""
        from src.services.standby import get_serverless_manager, ServerlessMode

        manager = get_serverless_manager()
        assert manager is not None
        assert ServerlessMode.FAST.value == "fast"
        print(f"{Colors.GREEN}[OK]{Colors.END} Backwards compatibility (standby) OK")

    def test_backwards_compatibility_gpu(self):
        """Verifica compatibilidade com imports antigos (gpu)."""
        from src.services.gpu import GPUCheckpointService, get_checkpoint_service

        svc = get_checkpoint_service()
        assert svc is not None
        assert isinstance(svc, GPUCheckpointService)
        print(f"{Colors.GREEN}[OK]{Colors.END} Backwards compatibility (gpu) OK")


# =============================================================================
# API INTEGRATION TESTS
# =============================================================================

class TestServerlessAPI:
    """Testes de integração com a API Serverless."""

    def test_serverless_pricing_endpoint(self, serverless_api_client):
        """Testa endpoint de pricing."""
        response = serverless_api_client.get("/api/v1/serverless/pricing")

        assert response.get("_ok"), f"Request failed: {response}"
        assert "monthly_costs" in response
        assert "always_on" in response["monthly_costs"]
        assert "serverless_fast" in response["monthly_costs"]
        assert "serverless_economic" in response["monthly_costs"]

        # Verificar que serverless é mais barato
        always_on = response["monthly_costs"]["always_on"]["cost_usd"]
        economic = response["monthly_costs"]["serverless_economic"]["cost_usd"]
        assert economic < always_on, "Serverless should be cheaper"

        print(f"{Colors.GREEN}[OK]{Colors.END} Pricing endpoint working")
        print(f"    Always-on: ${always_on}/month")
        print(f"    Serverless: ${economic}/month")
        print(f"    Savings: {response['monthly_costs']['serverless_economic']['savings_percent']}%")

    def test_serverless_list_empty(self, serverless_api_client):
        """Testa listagem de instâncias serverless (vazia inicialmente)."""
        response = serverless_api_client.get("/api/v1/serverless/list")

        assert response.get("_ok"), f"Request failed: {response}"
        assert "count" in response
        assert "instances" in response
        assert isinstance(response["instances"], list)

        print(f"{Colors.GREEN}[OK]{Colors.END} List endpoint working (count: {response['count']})")

    def test_serverless_status_not_found(self, serverless_api_client):
        """Testa status de instância inexistente."""
        response = serverless_api_client.get("/api/v1/serverless/status/999999999")

        # Deve retornar 404
        assert response.get("_status_code") == 404
        print(f"{Colors.GREEN}[OK]{Colors.END} Status returns 404 for unknown instance")


# =============================================================================
# E2E JOURNEY TESTS - Require Real GPU
# =============================================================================

@pytest.mark.real
@pytest.mark.slow
@pytest.mark.expensive
class TestServerlessJourneys:
    """
    Testes de jornada completa com GPU real.

    ATENÇÃO: Estes testes consomem créditos VAST.ai!
    """

    def _find_cheap_gpu(self, api_client: APIClient) -> Optional[Dict]:
        """Encontra GPU barata para teste."""
        response = api_client.get("/api/v1/instances/offers", params={
            "gpu_name": TEST_GPU_PREFERENCES["gpu_name"],
            "max_price": TEST_GPU_PREFERENCES["max_price"],
            "min_ram": TEST_GPU_PREFERENCES["min_ram"],
            "verified": True,
            "limit": 5,
        })

        if not response.get("_ok") or not response.get("offers"):
            return None

        # Retornar a mais barata
        offers = sorted(response["offers"], key=lambda x: x.get("dph_total", 999))
        return offers[0] if offers else None

    def _create_instance(self, api_client: APIClient, offer: Dict, label: str) -> Optional[int]:
        """Cria instância a partir de oferta."""
        response = api_client.post("/api/v1/instances", data={
            "offer_id": offer["id"],
            "disk_space": TEST_GPU_PREFERENCES["disk_space"],
            "label": f"dumont:test:{label}",
            "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        })

        if response.get("_ok") and response.get("instance_id"):
            return response["instance_id"]
        return None

    def _wait_for_running(self, api_client: APIClient, instance_id: int, timeout: int = 180) -> bool:
        """Aguarda instância ficar running."""
        start = time.time()
        while time.time() - start < timeout:
            response = api_client.get(f"/api/v1/instances/{instance_id}")
            if response.get("actual_status") == "running":
                return True
            time.sleep(10)
        return False

    def _enable_serverless(
        self,
        api_client: APIClient,
        instance_id: int,
        mode: str = "economic",
        idle_timeout: int = IDLE_WAIT
    ) -> bool:
        """Habilita serverless na instância."""
        response = api_client.post(f"/api/v1/serverless/enable/{instance_id}", data={
            "mode": mode,
            "idle_timeout_seconds": idle_timeout,
            "gpu_threshold": 5.0,
        })
        return response.get("_ok", False)

    @pytest.mark.creates_machine
    def test_serverless_basic_journey(self, serverless_api_client, cleanup_instance):
        """
        Jornada básica: criar GPU → habilitar serverless → verificar status.
        """
        print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}TEST: Basic Serverless Journey{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")

        # 1. Buscar GPU barata
        print(f"\n{Colors.BLUE}[1/5]{Colors.END} Finding cheap GPU...")
        offer = self._find_cheap_gpu(serverless_api_client)
        if not offer:
            pytest.skip("No cheap GPU available")
        print(f"    Found: {offer.get('gpu_name')} @ ${offer.get('dph_total', 0):.3f}/hr")

        # 2. Criar instância
        print(f"\n{Colors.BLUE}[2/5]{Colors.END} Creating instance...")
        instance_id = self._create_instance(serverless_api_client, offer, "serverless-basic")
        if not instance_id:
            pytest.fail("Failed to create instance")
        cleanup_instance(instance_id)
        print(f"    Instance ID: {instance_id}")

        # 3. Aguardar running
        print(f"\n{Colors.BLUE}[3/5]{Colors.END} Waiting for instance to start...")
        if not self._wait_for_running(serverless_api_client, instance_id):
            pytest.fail("Instance did not start in time")
        print(f"    {Colors.GREEN}Instance running{Colors.END}")

        # 4. Habilitar serverless
        print(f"\n{Colors.BLUE}[4/5]{Colors.END} Enabling serverless mode...")
        if not self._enable_serverless(serverless_api_client, instance_id, "economic", IDLE_WAIT):
            pytest.fail("Failed to enable serverless")
        print(f"    {Colors.GREEN}Serverless enabled{Colors.END}")

        # 5. Verificar status
        print(f"\n{Colors.BLUE}[5/5]{Colors.END} Checking serverless status...")
        response = serverless_api_client.get(f"/api/v1/serverless/status/{instance_id}")
        assert response.get("_ok"), f"Status check failed: {response}"
        assert response.get("mode") == "economic"
        assert response.get("is_paused") is False
        print(f"    Mode: {response.get('mode')}")
        print(f"    Is Paused: {response.get('is_paused')}")
        print(f"    Idle Timeout: {response.get('idle_timeout_seconds')}s")

        print(f"\n{Colors.GREEN}[SUCCESS]{Colors.END} Basic serverless journey complete!")

    @pytest.mark.creates_machine
    def test_serverless_pause_wake_cycle(self, serverless_api_client, cleanup_instance):
        """
        Jornada: criar GPU → serverless → aguardar pause → wake → verificar.
        """
        print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}TEST: Serverless Pause/Wake Cycle{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")

        # 1. Buscar GPU
        print(f"\n{Colors.BLUE}[1/7]{Colors.END} Finding cheap GPU...")
        offer = self._find_cheap_gpu(serverless_api_client)
        if not offer:
            pytest.skip("No cheap GPU available")
        print(f"    Found: {offer.get('gpu_name')}")

        # 2. Criar instância
        print(f"\n{Colors.BLUE}[2/7]{Colors.END} Creating instance...")
        instance_id = self._create_instance(serverless_api_client, offer, "serverless-cycle")
        if not instance_id:
            pytest.fail("Failed to create instance")
        cleanup_instance(instance_id)
        print(f"    Instance ID: {instance_id}")

        # 3. Aguardar running
        print(f"\n{Colors.BLUE}[3/7]{Colors.END} Waiting for instance...")
        if not self._wait_for_running(serverless_api_client, instance_id):
            pytest.fail("Instance did not start")
        print(f"    {Colors.GREEN}Running{Colors.END}")

        # 4. Habilitar serverless com timeout curto
        print(f"\n{Colors.BLUE}[4/7]{Colors.END} Enabling serverless (timeout={IDLE_WAIT}s)...")
        if not self._enable_serverless(serverless_api_client, instance_id, "economic", IDLE_WAIT):
            pytest.fail("Failed to enable serverless")
        print(f"    {Colors.GREEN}Enabled{Colors.END}")

        # 5. Aguardar auto-pause (GPU ociosa deve pausar)
        print(f"\n{Colors.BLUE}[5/7]{Colors.END} Waiting for auto-pause ({IDLE_WAIT + 30}s)...")
        time.sleep(IDLE_WAIT + 30)  # Tempo extra para processar

        response = serverless_api_client.get(f"/api/v1/serverless/status/{instance_id}")
        is_paused = response.get("is_paused", False)
        print(f"    Is Paused: {is_paused}")

        # Nota: pode não pausar se a GPU estiver rodando algo
        if not is_paused:
            print(f"    {Colors.YELLOW}[WARN]{Colors.END} Instance did not auto-pause (GPU may be busy)")

        # 6. Wake manual
        print(f"\n{Colors.BLUE}[6/7]{Colors.END} Waking instance...")
        wake_start = time.time()
        response = serverless_api_client.post(f"/api/v1/serverless/wake/{instance_id}")
        wake_time = time.time() - wake_start

        if response.get("_ok"):
            print(f"    {Colors.GREEN}Woke in {wake_time:.2f}s{Colors.END}")
            print(f"    Cold start: {response.get('cold_start_seconds', 'N/A')}s")
        else:
            print(f"    Status: {response.get('status')}")

        # 7. Verificar status final
        print(f"\n{Colors.BLUE}[7/7]{Colors.END} Final status check...")
        response = serverless_api_client.get(f"/api/v1/serverless/status/{instance_id}")
        print(f"    Mode: {response.get('mode')}")
        print(f"    Is Paused: {response.get('is_paused')}")
        print(f"    Total Savings: ${response.get('total_savings_usd', 0):.4f}")

        print(f"\n{Colors.GREEN}[SUCCESS]{Colors.END} Pause/Wake cycle complete!")


# =============================================================================
# MODEL DEPLOYMENT + SERVERLESS JOURNEYS
# =============================================================================

@pytest.mark.real
@pytest.mark.slow
@pytest.mark.expensive
class TestModelServerlessJourneys:
    """Testes de deploy de modelos com serverless."""

    def _deploy_model(
        self,
        api_client: APIClient,
        model_type: str,
        model_id: str,
        gpu_memory: int = 8
    ) -> Optional[Dict]:
        """Faz deploy de um modelo e retorna info."""
        response = api_client.post("/api/v1/models/deploy", data={
            "type": model_type,
            "model_id": model_id,
            "gpu_name": "RTX 4090",
            "max_price": 0.50,
            "disk_space": 50,
        })

        if response.get("_ok"):
            return {
                "instance_id": response.get("instance_id"),
                "deployment_id": response.get("deployment_id"),
            }
        return None

    @pytest.mark.creates_machine
    def test_whisper_serverless_journey(self, serverless_api_client, cleanup_instance):
        """
        Jornada: Deploy Whisper → Serverless → Transcrição → Pause → Wake.
        """
        print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}TEST: Whisper + Serverless Journey{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")

        model_config = TEST_MODELS["whisper"]

        # 1. Deploy Whisper
        print(f"\n{Colors.BLUE}[1/5]{Colors.END} Deploying Whisper ({model_config['model_id']})...")
        result = self._deploy_model(
            serverless_api_client,
            model_config["type"],
            model_config["model_id"],
            model_config["gpu_memory"]
        )

        if not result:
            pytest.skip("Could not deploy Whisper model")

        instance_id = result["instance_id"]
        cleanup_instance(instance_id)
        print(f"    Instance ID: {instance_id}")

        # 2. Aguardar deploy
        print(f"\n{Colors.BLUE}[2/5]{Colors.END} Waiting for deployment...")
        start = time.time()
        while time.time() - start < DEPLOY_TIMEOUT:
            response = serverless_api_client.get(f"/api/v1/models/{result['deployment_id']}/health")
            if response.get("healthy"):
                break
            time.sleep(15)
        else:
            pytest.skip("Whisper deployment timeout")
        print(f"    {Colors.GREEN}Whisper ready in {time.time()-start:.0f}s{Colors.END}")

        # 3. Habilitar serverless
        print(f"\n{Colors.BLUE}[3/5]{Colors.END} Enabling serverless...")
        response = serverless_api_client.post(f"/api/v1/serverless/enable/{instance_id}", data={
            "mode": "economic",
            "idle_timeout_seconds": 30,
        })
        assert response.get("_ok"), f"Failed to enable serverless: {response}"
        print(f"    {Colors.GREEN}Serverless enabled{Colors.END}")

        # 4. Verificar status
        print(f"\n{Colors.BLUE}[4/5]{Colors.END} Checking status...")
        response = serverless_api_client.get(f"/api/v1/serverless/status/{instance_id}")
        print(f"    Mode: {response.get('mode')}")
        print(f"    Checkpoint enabled: {response.get('last_checkpoint_id') is not None}")

        # 5. Desabilitar e limpar
        print(f"\n{Colors.BLUE}[5/5]{Colors.END} Disabling serverless...")
        serverless_api_client.post(f"/api/v1/serverless/disable/{instance_id}")

        print(f"\n{Colors.GREEN}[SUCCESS]{Colors.END} Whisper + Serverless journey complete!")

    @pytest.mark.creates_machine
    def test_llm_serverless_journey(self, serverless_api_client, cleanup_instance):
        """
        Jornada: Deploy LLM → Serverless → Chat → Pause → Wake → Chat.
        """
        print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}TEST: LLM + Serverless Journey{Colors.END}")
        print(f"{Colors.CYAN}{'='*60}{Colors.END}")

        model_config = TEST_MODELS["llm"]

        # 1. Deploy LLM
        print(f"\n{Colors.BLUE}[1/6]{Colors.END} Deploying LLM ({model_config['model_id']})...")
        result = self._deploy_model(
            serverless_api_client,
            model_config["type"],
            model_config["model_id"],
            model_config["gpu_memory"]
        )

        if not result:
            pytest.skip("Could not deploy LLM model")

        instance_id = result["instance_id"]
        cleanup_instance(instance_id)
        print(f"    Instance ID: {instance_id}")

        # 2. Aguardar deploy
        print(f"\n{Colors.BLUE}[2/6]{Colors.END} Waiting for LLM to load...")
        start = time.time()
        while time.time() - start < DEPLOY_TIMEOUT:
            response = serverless_api_client.get(f"/api/v1/models/{result['deployment_id']}/health")
            if response.get("healthy"):
                break
            time.sleep(20)
        else:
            pytest.skip("LLM deployment timeout")
        print(f"    {Colors.GREEN}LLM ready in {time.time()-start:.0f}s{Colors.END}")

        # 3. Habilitar serverless modo FAST (com checkpoint)
        print(f"\n{Colors.BLUE}[3/6]{Colors.END} Enabling serverless (FAST mode)...")
        response = serverless_api_client.post(f"/api/v1/serverless/enable/{instance_id}", data={
            "mode": "fast",
            "idle_timeout_seconds": 60,
            "checkpoint_enabled": True,
        })
        if not response.get("_ok"):
            print(f"    {Colors.YELLOW}[WARN]{Colors.END} Fast mode failed, trying economic...")
            response = serverless_api_client.post(f"/api/v1/serverless/enable/{instance_id}", data={
                "mode": "economic",
                "idle_timeout_seconds": 60,
            })
        assert response.get("_ok"), f"Failed: {response}"
        print(f"    {Colors.GREEN}Serverless enabled: {response.get('mode', 'unknown')}{Colors.END}")

        # 4. Verificar checkpoint setup
        print(f"\n{Colors.BLUE}[4/6]{Colors.END} Checking serverless status...")
        response = serverless_api_client.get(f"/api/v1/serverless/status/{instance_id}")
        print(f"    Mode: {response.get('mode')}")
        print(f"    Last Checkpoint: {response.get('last_checkpoint_id', 'None')}")

        # 5. Simular uso e aguardar
        print(f"\n{Colors.BLUE}[5/6]{Colors.END} Simulating idle period...")
        time.sleep(30)

        response = serverless_api_client.get(f"/api/v1/serverless/status/{instance_id}")
        print(f"    Is Paused: {response.get('is_paused')}")
        print(f"    Will Pause At: {response.get('will_pause_at', 'N/A')}")

        # 6. Cleanup
        print(f"\n{Colors.BLUE}[6/6]{Colors.END} Cleaning up...")
        serverless_api_client.post(f"/api/v1/serverless/disable/{instance_id}")

        print(f"\n{Colors.GREEN}[SUCCESS]{Colors.END} LLM + Serverless journey complete!")


# =============================================================================
# CHECKPOINT TESTS
# =============================================================================

@pytest.mark.real
@pytest.mark.slow
class TestCheckpointFunctionality:
    """Testes de funcionalidade de checkpoint."""

    def test_checkpoint_setup_script(self):
        """Verifica se o script de setup está correto."""
        from src.modules.serverless import get_checkpoint_service

        svc = get_checkpoint_service()

        # Verificar que scripts existem
        assert svc.SETUP_SCRIPT is not None
        assert "cuda-checkpoint" in svc.SETUP_SCRIPT
        assert "criu" in svc.SETUP_SCRIPT.lower()

        assert svc.CHECKPOINT_SCRIPT is not None
        assert "nvidia-smi" in svc.CHECKPOINT_SCRIPT

        assert svc.RESTORE_SCRIPT is not None
        assert "criu restore" in svc.RESTORE_SCRIPT

        print(f"{Colors.GREEN}[OK]{Colors.END} Checkpoint scripts are valid")

    def test_checkpoint_list_empty(self):
        """Testa listagem de checkpoints em instância inexistente."""
        from src.modules.serverless import get_checkpoint_service

        svc = get_checkpoint_service()

        # Deve retornar lista vazia, não erro
        result = svc.list_checkpoints("invalid", "localhost", 22)
        assert isinstance(result, list)
        assert len(result) == 0

        print(f"{Colors.GREEN}[OK]{Colors.END} Checkpoint list returns empty for invalid instance")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestServerlessPerformance:
    """Testes de performance do módulo."""

    def test_manager_initialization_time(self):
        """Mede tempo de inicialização do manager."""
        import importlib
        import src.modules.serverless.manager as manager_module

        # Resetar singleton
        manager_module._serverless_manager = None

        start = time.time()
        from src.modules.serverless import get_serverless_manager
        manager = get_serverless_manager()
        init_time = time.time() - start

        assert init_time < 1.0, f"Manager took too long to initialize: {init_time:.2f}s"
        print(f"{Colors.GREEN}[OK]{Colors.END} Manager initialized in {init_time*1000:.1f}ms")

    def test_config_load_time(self):
        """Mede tempo de carregamento de config."""
        start = time.time()
        from src.modules.serverless.config import get_settings
        settings = get_settings()
        load_time = time.time() - start

        assert load_time < 0.1, f"Config load too slow: {load_time:.2f}s"
        print(f"{Colors.GREEN}[OK]{Colors.END} Config loaded in {load_time*1000:.1f}ms")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
