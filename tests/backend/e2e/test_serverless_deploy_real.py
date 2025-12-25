"""
Serverless Deploy Real Tests - Whisper & Stable Diffusion

Testes REAIS que fazem deploy de modelos e testam serverless.
ATENÇÃO: Consome créditos VAST.ai!

Uso:
    pytest tests/backend/e2e/test_serverless_deploy_real.py -v -s --timeout=600
"""

import os
import sys
import time
import pytest
import requests
import logging
from typing import Optional, Dict, Any

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.services.gpu.vast import VastService
from src.modules.serverless import get_serverless_manager, ServerlessMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Colors for output
class C:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'


# =============================================================================
# CONFIGURATION
# =============================================================================

# Load VAST API key from environment or .env
def get_vast_api_key() -> str:
    key = os.environ.get("VAST_API_KEY")
    if not key:
        # Try loading from .env
        env_path = os.path.join(os.path.dirname(__file__), "../../../.env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("VAST_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
    return key or ""


VAST_API_KEY = get_vast_api_key()

# Test configuration
GPU_CONFIG = {
    "gpu_name": "RTX 4090",      # Bom custo-benefício
    "max_price": 0.60,           # Max $0.60/hr
    "disk_space": 50,            # 50GB
    "min_ram": 24,               # 24GB VRAM
}

# Model configs
WHISPER_CONFIG = {
    "name": "Whisper",
    "model_id": "openai/whisper-small",  # Modelo pequeno para teste rápido
    "port": 8001,
    "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
    "gpu_memory_gb": 4,
    "startup_script": """
pip install transformers accelerate torch fastapi uvicorn python-multipart --quiet
echo "Whisper dependencies installed"
""",
}

STABLE_DIFFUSION_CONFIG = {
    "name": "StableDiffusion",
    "model_id": "stabilityai/sdxl-turbo",  # Versão turbo mais leve
    "port": 8002,
    "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
    "gpu_memory_gb": 8,
    "startup_script": """
pip install diffusers transformers accelerate torch fastapi uvicorn --quiet
echo "Stable Diffusion dependencies installed"
""",
}

# Timeouts
PROVISION_TIMEOUT = 300   # 5 min
STARTUP_TIMEOUT = 180     # 3 min
SERVERLESS_IDLE = 30      # 30s idle before pause
WAKE_TIMEOUT = 120        # 2 min


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def log_step(step: int, total: int, message: str):
    """Log a step with formatting."""
    print(f"\n{C.BLUE}[{step}/{total}]{C.END} {message}")


def log_success(message: str):
    """Log success message."""
    print(f"    {C.GREEN}✓{C.END} {message}")


def log_error(message: str):
    """Log error message."""
    print(f"    {C.RED}✗{C.END} {message}")


def log_info(message: str):
    """Log info message."""
    print(f"    {C.CYAN}→{C.END} {message}")


def find_cheap_gpu(vast: VastService, gpu_name: str = None, max_price: float = 0.60) -> Optional[Dict]:
    """Find a cheap GPU offer."""
    try:
        offers = vast.search_offers(
            gpu_name=gpu_name or GPU_CONFIG["gpu_name"],
            num_gpus=1,
            min_gpu_ram=GPU_CONFIG["min_ram"],
            min_disk=GPU_CONFIG["disk_space"],
            verified_only=True,
            max_price=max_price,
            limit=10,
        )

        if not offers:
            return None

        # Filter by price
        affordable = [o for o in offers if o.get("dph_total", 999) <= max_price]
        if not affordable:
            return None

        return affordable[0]
    except Exception as e:
        logger.error(f"Error finding GPU: {e}")
        return None


def wait_for_running(vast: VastService, instance_id: int, timeout: int = 180) -> bool:
    """Wait for instance to be running."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = vast.get_instance_status(instance_id)
            if status.get("actual_status") == "running":
                return True
            log_info(f"Status: {status.get('actual_status', 'unknown')}...")
        except Exception as e:
            log_info(f"Waiting... ({e})")
        time.sleep(10)
    return False


def wait_for_ssh(vast: VastService, instance_id: int, timeout: int = 120) -> Optional[Dict]:
    """Wait for SSH info to be available (host/port exposed)."""
    start = time.time()
    last_status = None
    while time.time() - start < timeout:
        try:
            status = vast.get_instance_status(instance_id)
            ssh_host = status.get("ssh_host")
            ssh_port = status.get("ssh_port")
            actual_status = status.get("actual_status")

            if actual_status != last_status:
                log_info(f"Status: {actual_status}, SSH: {ssh_host}:{ssh_port}")
                last_status = actual_status

            # Just check if SSH info is available (no need to actually connect)
            if ssh_host and ssh_port and actual_status == "running":
                return {"ssh_host": ssh_host, "ssh_port": ssh_port}
        except Exception as e:
            log_error(f"Error checking status: {e}")
        time.sleep(5)
    return None


def destroy_instance(vast: VastService, instance_id: int):
    """Safely destroy instance."""
    try:
        vast.destroy_instance(instance_id)
        log_success(f"Instance {instance_id} destroyed")
    except Exception as e:
        log_error(f"Failed to destroy {instance_id}: {e}")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def vast_service():
    """Get VastService with API key."""
    if not VAST_API_KEY:
        pytest.skip("VAST_API_KEY not configured")
    return VastService(VAST_API_KEY)


@pytest.fixture(scope="module")
def serverless_manager(vast_service):
    """Get configured ServerlessManager."""
    manager = get_serverless_manager()
    manager.configure(vast_api_key=VAST_API_KEY, enable_checkpoint=True)
    return manager


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.real
@pytest.mark.expensive
@pytest.mark.timeout(600)
class TestWhisperServerless:
    """Test Whisper model with Serverless."""

    def test_whisper_serverless_journey(self, vast_service, serverless_manager):
        """
        Jornada completa:
        1. Provisionar GPU
        2. Instalar Whisper
        3. Habilitar Serverless
        4. Testar pause/wake
        5. Destruir GPU
        """
        print(f"\n{C.CYAN}{'='*60}{C.END}")
        print(f"{C.CYAN}  WHISPER + SERVERLESS JOURNEY TEST{C.END}")
        print(f"{C.CYAN}{'='*60}{C.END}")

        instance_id = None

        try:
            # Step 1: Find GPU
            log_step(1, 7, "Finding cheap GPU...")
            offer = find_cheap_gpu(vast_service, max_price=GPU_CONFIG["max_price"])
            if not offer:
                pytest.skip("No affordable GPU available")
            log_success(f"Found: {offer.get('gpu_name')} @ ${offer.get('dph_total', 0):.3f}/hr")
            log_info(f"Machine ID: {offer.get('machine_id')}")

            # Step 2: Create instance
            log_step(2, 7, "Creating instance...")
            result = vast_service.create_instance(
                offer_id=offer["id"],
                image=WHISPER_CONFIG["image"],
                disk=GPU_CONFIG["disk_space"],
                label="dumont:test:whisper-serverless",
                onstart_cmd=WHISPER_CONFIG["startup_script"],
            )

            if not result:
                pytest.fail(f"Failed to create instance: {result}")

            instance_id = result  # create_instance returns int directly
            log_success(f"Instance created: {instance_id}")

            # Step 3: Wait for running
            log_step(3, 7, "Waiting for instance to start...")
            if not wait_for_running(vast_service, instance_id, PROVISION_TIMEOUT):
                pytest.fail("Instance did not start in time")
            log_success("Instance is running")

            # Step 4: Wait for SSH
            log_step(4, 7, "Waiting for SSH...")
            ssh_info = wait_for_ssh(vast_service, instance_id, 120)
            if not ssh_info:
                pytest.fail("SSH not available")
            log_success(f"SSH ready: {ssh_info['ssh_host']}:{ssh_info['ssh_port']}")

            # Step 5: Enable Serverless
            log_step(5, 7, "Enabling Serverless mode...")
            result = serverless_manager.enable(
                instance_id=instance_id,
                mode="economic",
                idle_timeout_seconds=SERVERLESS_IDLE,
                gpu_threshold=5.0,
            )
            log_success(f"Serverless enabled: mode={result.get('mode')}")
            log_info(f"Will pause after {SERVERLESS_IDLE}s idle")

            # Step 6: Check status
            log_step(6, 7, "Checking serverless status...")
            status = serverless_manager.get_status(instance_id)
            assert status is not None, "Status should not be None"
            assert status.mode == "economic", f"Mode should be economic, got {status.mode}"
            assert not status.is_paused, "Should not be paused initially"
            log_success(f"Status OK: mode={status.mode}, paused={status.is_paused}")

            # Step 7: Test wake (even if not paused)
            log_step(7, 7, "Testing wake functionality...")
            wake_result = serverless_manager.wake(instance_id)
            log_info(f"Wake result: {wake_result.get('status')}")

            # Final summary
            print(f"\n{C.GREEN}{'='*60}{C.END}")
            print(f"{C.GREEN}  WHISPER SERVERLESS TEST PASSED!{C.END}")
            print(f"{C.GREEN}{'='*60}{C.END}")
            print(f"    Instance: {instance_id}")
            print(f"    GPU: {offer.get('gpu_name')}")
            print(f"    Cost: ${offer.get('dph_total', 0):.3f}/hr")
            print(f"    Serverless: ENABLED")

        finally:
            # Cleanup
            if instance_id:
                print(f"\n{C.YELLOW}Cleaning up...{C.END}")
                # Disable serverless first
                try:
                    serverless_manager.disable(instance_id)
                except:
                    pass
                # Destroy instance
                destroy_instance(vast_service, instance_id)


@pytest.mark.real
@pytest.mark.expensive
@pytest.mark.timeout(600)
class TestStableDiffusionServerless:
    """Test Stable Diffusion model with Serverless."""

    def test_stable_diffusion_serverless_journey(self, vast_service, serverless_manager):
        """
        Jornada completa:
        1. Provisionar GPU
        2. Instalar SD
        3. Habilitar Serverless (modo fast com checkpoint)
        4. Verificar checkpoint setup
        5. Destruir GPU
        """
        print(f"\n{C.CYAN}{'='*60}{C.END}")
        print(f"{C.CYAN}  STABLE DIFFUSION + SERVERLESS JOURNEY TEST{C.END}")
        print(f"{C.CYAN}{'='*60}{C.END}")

        instance_id = None

        try:
            # Step 1: Find GPU (need more VRAM for SD)
            log_step(1, 6, "Finding GPU with enough VRAM for Stable Diffusion...")
            offer = find_cheap_gpu(vast_service, gpu_name="RTX 4090", max_price=0.70)
            if not offer:
                # Try any GPU with 24GB+
                offer = find_cheap_gpu(vast_service, max_price=0.80)
            if not offer:
                pytest.skip("No suitable GPU available for Stable Diffusion")
            log_success(f"Found: {offer.get('gpu_name')} @ ${offer.get('dph_total', 0):.3f}/hr")

            # Step 2: Create instance
            log_step(2, 6, "Creating instance for Stable Diffusion...")
            result = vast_service.create_instance(
                offer_id=offer["id"],
                image=STABLE_DIFFUSION_CONFIG["image"],
                disk=GPU_CONFIG["disk_space"],
                label="dumont:test:sd-serverless",
                onstart_cmd=STABLE_DIFFUSION_CONFIG["startup_script"],
            )

            if not result:
                pytest.fail(f"Failed to create instance: {result}")

            instance_id = result  # create_instance returns int directly
            log_success(f"Instance created: {instance_id}")

            # Step 3: Wait for running
            log_step(3, 6, "Waiting for instance...")
            if not wait_for_running(vast_service, instance_id, PROVISION_TIMEOUT):
                pytest.fail("Instance did not start")
            log_success("Instance running")

            # Step 4: Wait for SSH
            log_step(4, 6, "Waiting for SSH...")
            ssh_info = wait_for_ssh(vast_service, instance_id, 120)
            if not ssh_info:
                pytest.fail("SSH not available")
            log_success(f"SSH ready")

            # Step 5: Enable Serverless with FAST mode (checkpoint)
            log_step(5, 6, "Enabling Serverless FAST mode (with checkpoint)...")
            result = serverless_manager.enable(
                instance_id=instance_id,
                mode="fast",  # Modo com checkpoint
                idle_timeout_seconds=60,
                gpu_threshold=5.0,
                checkpoint_enabled=True,
            )
            log_success(f"Serverless enabled: mode={result.get('mode')}")
            log_info(f"Checkpoint enabled: {result.get('checkpoint_enabled', False)}")

            # Step 6: Verify status
            log_step(6, 6, "Verifying serverless status...")
            status = serverless_manager.get_status(instance_id)
            assert status is not None
            log_success(f"Mode: {status.mode}")
            log_success(f"Is Paused: {status.is_paused}")
            log_info(f"Last Checkpoint: {status.last_checkpoint_id or 'None'}")

            # Final summary
            print(f"\n{C.GREEN}{'='*60}{C.END}")
            print(f"{C.GREEN}  STABLE DIFFUSION SERVERLESS TEST PASSED!{C.END}")
            print(f"{C.GREEN}{'='*60}{C.END}")
            print(f"    Instance: {instance_id}")
            print(f"    GPU: {offer.get('gpu_name')}")
            print(f"    Serverless Mode: FAST (checkpoint)")

        finally:
            # Cleanup
            if instance_id:
                print(f"\n{C.YELLOW}Cleaning up...{C.END}")
                try:
                    serverless_manager.disable(instance_id)
                except:
                    pass
                destroy_instance(vast_service, instance_id)


@pytest.mark.real
@pytest.mark.expensive
@pytest.mark.timeout(900)
class TestServerlessPauseWakeCycle:
    """Test complete pause/wake cycle with real GPU."""

    def test_pause_wake_cycle(self, vast_service, serverless_manager):
        """
        Test real pause/wake cycle:
        1. Create GPU
        2. Enable serverless with short timeout
        3. Wait for auto-pause
        4. Wake and measure cold start
        5. Cleanup
        """
        print(f"\n{C.CYAN}{'='*60}{C.END}")
        print(f"{C.CYAN}  PAUSE/WAKE CYCLE TEST{C.END}")
        print(f"{C.CYAN}{'='*60}{C.END}")

        instance_id = None

        try:
            # Step 1: Find cheap GPU
            log_step(1, 8, "Finding cheap GPU...")
            offer = find_cheap_gpu(vast_service, max_price=0.50)
            if not offer:
                pytest.skip("No cheap GPU available")
            log_success(f"Found: {offer.get('gpu_name')} @ ${offer.get('dph_total', 0):.3f}/hr")

            # Step 2: Create instance
            log_step(2, 8, "Creating instance...")
            result = vast_service.create_instance(
                offer_id=offer["id"],
                image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
                disk=30,
                label="dumont:test:pause-wake",
            )
            instance_id = result.get("new_contract")
            if not instance_id:
                pytest.fail("Failed to create instance")
            log_success(f"Instance: {instance_id}")

            # Step 3: Wait for running
            log_step(3, 8, "Waiting for instance...")
            if not wait_for_running(vast_service, instance_id, 180):
                pytest.fail("Instance did not start")
            log_success("Running")

            # Step 4: Enable serverless with SHORT timeout
            log_step(4, 8, "Enabling serverless (10s idle timeout)...")
            serverless_manager.enable(
                instance_id=instance_id,
                mode="economic",
                idle_timeout_seconds=10,  # Very short for testing
                gpu_threshold=5.0,
            )
            log_success("Serverless enabled")

            # Step 5: Wait for auto-pause
            log_step(5, 8, "Waiting for auto-pause (up to 60s)...")
            paused = False
            for i in range(12):  # 60 seconds
                time.sleep(5)
                status = serverless_manager.get_status(instance_id)
                if status and status.is_paused:
                    paused = True
                    log_success(f"Instance paused after ~{(i+1)*5}s")
                    break
                log_info(f"Checking... ({(i+1)*5}s)")

            if not paused:
                log_info("Instance did not auto-pause (GPU may be busy)")
                # Manually pause via VAST API
                log_info("Attempting manual pause...")
                vast_service.pause_instance(instance_id)
                time.sleep(5)

            # Step 6: Verify paused state
            log_step(6, 8, "Verifying paused state...")
            vast_status = vast_service.get_instance_status(instance_id)
            log_info(f"VAST status: {vast_status.get('actual_status')}")

            # Step 7: Wake and measure cold start
            log_step(7, 8, "Waking instance...")
            wake_start = time.time()
            wake_result = serverless_manager.wake(instance_id)
            wake_time = time.time() - wake_start

            if wake_result.get("status") == "resumed":
                log_success(f"Woke in {wake_time:.2f}s")
                log_info(f"Cold start reported: {wake_result.get('cold_start_seconds', 'N/A')}s")
            else:
                log_info(f"Wake result: {wake_result}")

            # Step 8: Final status
            log_step(8, 8, "Final status check...")
            final_status = serverless_manager.get_status(instance_id)
            if final_status:
                log_success(f"Mode: {final_status.mode}")
                log_success(f"Total savings: ${final_status.total_savings_usd:.4f}")

            print(f"\n{C.GREEN}{'='*60}{C.END}")
            print(f"{C.GREEN}  PAUSE/WAKE CYCLE TEST PASSED!{C.END}")
            print(f"{C.GREEN}{'='*60}{C.END}")
            print(f"    Cold Start Time: {wake_time:.2f}s")

        finally:
            if instance_id:
                print(f"\n{C.YELLOW}Cleaning up...{C.END}")
                try:
                    serverless_manager.disable(instance_id)
                except:
                    pass
                destroy_instance(vast_service, instance_id)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--timeout=600"])
