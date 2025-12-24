"""
CLI Tests - Specific Fixtures

Este arquivo importa tudo do conftest global e adiciona
apenas fixtures específicas para testes do CLI.

O conftest global (tests/conftest.py) fornece:
- APIClient, CLIRunner, RateLimiter
- settings, api_client, cli_runner fixtures
- GPU cleanup e signal handlers
- Markers e hooks do pytest
"""
import os
import sys
import warnings
import pytest
from pathlib import Path
from typing import Generator

# =============================================================================
# IMPORT FROM GLOBAL CONFTEST
# =============================================================================

# Add tests directory to path so we can import from global conftest
TESTS_DIR = Path(__file__).parent.parent.parent / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# Import everything from global conftest
from conftest import (
    # Settings
    _settings,
    get_settings,
    API_BASE_URL,
    TEST_USER,
    TEST_PASSWORD,
    PROJECT_ROOT,

    # Classes
    APIClient,
    CLIRunner,
    CLIResult,
    RateLimiter,
    RateLimitError,

    # Fixtures (re-export for pytest to find)
    settings,
    api_base_url,
    vast_api_key,
    rate_limiter,
    api_client,
    cli_runner,
    logged_in_cli,
    session_cleanup,
    auto_cleanup_instance,

    # Helpers
    parse_json_output,
    assert_valid_response,
    assert_sla,
    SLA_TARGETS,
    SLA_MARGIN,

    # GPU cleanup
    register_instance,
    unregister_instance,
)


# =============================================================================
# CLI-SPECIFIC FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def real_instance(api_client) -> Generator[str, None, None]:
    """
    Create a real GPU instance for testing using MachineProvisionerService (Race Strategy).

    WARNING: This uses real VAST.ai credits!

    Uses the new MachineProvisionerService with RaceStrategy:
    - Creates 5 machines in parallel
    - Uses the first one that becomes ready
    - Destroys the others automatically

    If REAL_INSTANCE_ID is set, uses that existing instance.
    """
    # Check if using existing instance
    existing_instance = os.environ.get("REAL_INSTANCE_ID")
    if existing_instance:
        print(f"\n  Using existing instance: {existing_instance}")
        yield existing_instance
        return

    instance_id = None
    vast_service = None

    try:
        print("\n🚀 Provisioning GPU via MachineProvisionerService (RaceStrategy)...")

        # Get VAST API key
        vast_api_key = os.environ.get("VAST_API_KEY") or _settings.vast.api_key

        if not vast_api_key:
            # Try getting from API settings
            try:
                settings_resp = api_client.call("GET", "/api/v1/settings")
                if settings_resp:
                    vast_api_key = settings_resp.get("vast_api_key")
            except Exception:
                pass

        if not vast_api_key:
            pytest.fail("VAST_API_KEY not configured")

        # Import the provisioner
        from src.services.gpu.strategies import MachineProvisionerService, ProvisionConfig

        provisioner = MachineProvisionerService(vast_api_key)

        # Create config - try cheaper GPUs first
        config = ProvisionConfig(
            gpu_name=None,  # Any GPU (fastest to find)
            max_price=0.50,
            disk_space=20,
            image="nvidia/cuda:12.1.0-base-ubuntu22.04",
            label="pytest-test-instance",
        )

        def progress_callback(status: str, message: str, progress: int):
            print(f"  [{progress}%] {status}: {message}")

        print("  🔄 Starting RaceStrategy (5 machines in parallel)...")
        result = provisioner.provision(config, strategy="race", progress_callback=progress_callback)

        if not result.success:
            # Fallback: try with higher price
            print("  ⚠️ First attempt failed, trying with higher price limit...")
            config.max_price = 1.0
            result = provisioner.provision(config, strategy="race", progress_callback=progress_callback)

        if not result.success:
            pytest.fail(f"GPU provisioning failed: {result.error}")

        instance_id = str(result.instance_id)
        print(f"  ✅ GPU ready! Instance: {instance_id}")
        print(f"     GPU: {result.gpu_name}")
        print(f"     SSH: {result.ssh_host}:{result.ssh_port}")
        print(f"     Time: {result.total_time_seconds:.1f}s")

        # Store vast_service for cleanup
        vast_service = provisioner.vast_service

        # Register for crash-safe cleanup
        register_instance(int(instance_id))

    except pytest.fail.Exception:
        raise
    except ImportError as e:
        pytest.fail(f"Could not import MachineProvisionerService: {e}")
    except Exception as e:
        pytest.fail(f"CRITICAL: Failed to create test instance: {e}")

    yield instance_id

    # Cleanup - destroy instance directly
    if instance_id and vast_service:
        print(f"\n  🧹 Destroying instance {instance_id}...")
        try:
            vast_service.destroy_instance(int(instance_id))
            unregister_instance(int(instance_id))
            print(f"  ✓ Instance {instance_id} destroyed")
        except Exception as e:
            warnings.warn(f"CRITICAL: Instance {instance_id} NOT destroyed: {e}", UserWarning)
            try:
                with open("/tmp/dumont_orphan_instances.txt", "a") as f:
                    f.write(f"{instance_id}\n")
            except:
                pass


@pytest.fixture
def benchmark_api_call(api_client):
    """Benchmark fixture for API calls (simple timing)."""
    import time

    def _benchmark_call(method, path, data=None):
        start = time.perf_counter()
        result = api_client.call(method, path, data)
        elapsed = time.perf_counter() - start
        return {"result": result, "elapsed": elapsed}
    return _benchmark_call


@pytest.fixture
def benchmark_cli_command(cli_runner):
    """Benchmark fixture for CLI commands (simple timing)."""
    import time

    def _benchmark_cmd(*args):
        start = time.perf_counter()
        result = cli_runner.run(*args)
        elapsed = time.perf_counter() - start
        return {"result": result, "elapsed": elapsed}
    return _benchmark_cmd
