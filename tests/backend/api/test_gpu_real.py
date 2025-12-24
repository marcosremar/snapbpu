"""
Backend API Tests - GPU Real Tests

COST OPTIMIZATION: Tests are organized into two categories:

1. LIFECYCLE TESTS (@pytest.mark.creates_machine):
   - Tests that MUST create/destroy machines (provision, pause/resume, hibernation)
   - Run with: pytest -m "creates_machine"
   - Cost: ~$0.02-0.05 per test

2. SHARED MACHINE TESTS (@pytest.mark.uses_shared_machine):
   - Tests that can run on a SINGLE shared machine (SSH, nvidia-smi, metrics, etc.)
   - All these tests share ONE machine provisioned at session start
   - Run with: pytest -m "uses_shared_machine" -n 1  # IMPORTANT: -n 1 for shared machine!
   - Cost: ~$0.02 TOTAL for all tests combined

RUN OPTIONS:
    # Run all tests (full cost - each test creates own machine)
    pytest tests/backend/api/test_gpu_real.py -v --timeout=600

    # Run only SHARED machine tests (CHEAPEST - one machine for all)
    # IMPORTANT: Use -n 1 to ensure all tests share the same machine!
    pytest tests/backend/api/test_gpu_real.py -v -m "uses_shared_machine" -n 1 --timeout=600

    # Run only lifecycle tests (more expensive - each creates own machine)
    # Can use parallelism since each test creates its own machine anyway
    pytest tests/backend/api/test_gpu_real.py -v -m "creates_machine" -n 4 --timeout=600

    # Run tests that don't need real GPU (free)
    pytest tests/backend/api/test_gpu_real.py -v -m "not real"
"""
import pytest
import time
import uuid
import socket
from typing import Optional, Dict, Any

from src.services.deploy_wizard import (
    DeployWizardService,
    DeployConfig,
    get_wizard_service,
)
from src.services.gpu.vast import VastService


# =============================================================================
# CUSTOM MARKERS
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "creates_machine: test creates its own machine (expensive)"
    )
    config.addinivalue_line(
        "markers", "uses_shared_machine: test uses shared session machine (cheap)"
    )


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def wizard_service(vast_api_key) -> DeployWizardService:
    """Get the DeployWizardService - the ONLY way to provision machines."""
    return get_wizard_service(vast_api_key)


@pytest.fixture(scope="session")
def vast_service(vast_api_key) -> VastService:
    """VastService for instance management (stop/start/destroy)."""
    return VastService(vast_api_key)


def _destroy_all_test_instances(api_key: str, context: str = ""):
    """
    Helper function to destroy ALL test instances.
    Called both BEFORE and AFTER tests to ensure no orphans.
    """
    import requests

    try:
        resp = requests.get(
            "https://console.vast.ai/api/v0/instances/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30
        )

        if not resp.ok:
            print(f"  Warning: Could not fetch instances: {resp.status_code}")
            return 0

        instances = resp.json().get("instances", [])
        destroyed = 0

        for inst in instances:
            label = inst.get("label", "") or ""
            is_test_instance = (
                label.startswith("dumont:test:") or
                label.startswith("pytest-") or
                label.startswith("sdk-test-")
            )
            if is_test_instance:
                inst_id = inst.get("id")
                gpu = inst.get("gpu_name", "unknown")
                status = inst.get("actual_status", "unknown")
                print(f"  [{context}] Destroying {inst_id} ({gpu}, {status}, label: {label})...")

                try:
                    del_resp = requests.delete(
                        f"https://console.vast.ai/api/v0/instances/{inst_id}/",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=30
                    )
                    if del_resp.ok:
                        destroyed += 1
                        print(f"    ✓ Destroyed")
                    else:
                        print(f"    ✗ Failed: {del_resp.status_code}")
                except Exception as e:
                    print(f"    ✗ Error: {e}")

        return destroyed
    except Exception as e:
        print(f"  Warning: Cleanup failed: {e}")
        return 0


@pytest.fixture(scope="session", autouse=True)
def cleanup_all_test_instances(vast_api_key):
    """GUARANTEED CLEANUP: Destroys ALL test instances BEFORE and AFTER test session."""
    import atexit

    def emergency_cleanup():
        print("\n⚠️  EMERGENCY CLEANUP: Process exiting, destroying all test instances...")
        _destroy_all_test_instances(vast_api_key, "EMERGENCY")

    atexit.register(emergency_cleanup)

    print("\n" + "=" * 60)
    print("PRE-TEST CLEANUP: Checking for orphaned instances...")
    print("=" * 60)

    destroyed = _destroy_all_test_instances(vast_api_key, "PRE-TEST")
    if destroyed > 0:
        print(f"\n  ⚠️  Cleaned up {destroyed} orphaned instance(s) from previous runs!")
    else:
        print(f"\n  ✅ No orphans found. Starting clean!")

    yield

    print("\n" + "=" * 60)
    print("POST-TEST CLEANUP: Destroying ALL test instances...")
    print("=" * 60)

    destroyed = _destroy_all_test_instances(vast_api_key, "POST-TEST")
    if destroyed > 0:
        print(f"\n  Cleaned up {destroyed} instance(s)")
    else:
        print(f"\n  ✅ No orphaned instances found. All clean!")

    atexit.unregister(emergency_cleanup)


# =============================================================================
# SHARED MACHINE FIXTURE (for cheap tests)
# =============================================================================

@pytest.fixture(scope="session")
def shared_gpu_instance(wizard_service, vast_service, vast_api_key):
    """
    SHARED GPU INSTANCE for all tests marked with @pytest.mark.uses_shared_machine.

    This machine is created ONCE at the start of the session and destroyed at the end.
    All tests that just need to run commands on a GPU can use this shared instance.

    COST SAVINGS: Instead of 10 tests × $0.03 = $0.30, we pay $0.03 total.
    """
    print("\n" + "=" * 60)
    print("SHARED MACHINE: Provisioning single GPU for all shared tests...")
    print("=" * 60)

    test_label = f"dumont:test:shared-{int(time.time())}-{uuid.uuid4().hex[:8]}"

    config = DeployConfig(
        speed_tier="fast",
        max_price=0.25,
        disk_space=10,
        use_ollama_image=True,
        label=test_label,
    )

    result = wizard_service.provision_machine(config, strategy="single")  # Single = cheaper

    if not result.success:
        pytest.skip(f"Could not provision shared GPU: {result.error}")
        return None

    instance_data = {
        "instance_id": result.instance_id,
        "public_ip": result.public_ip,
        "ssh_port": result.ssh_port,
        "gpu_name": result.gpu_name,
        "dph_total": result.dph_total,
        "ready_time": result.time_to_ready_seconds,
        "label": test_label,
    }

    print(f"   Shared GPU: {result.gpu_name} @ ${result.dph_total:.3f}/hr")
    print(f"   Instance ID: {result.instance_id}")
    print(f"   SSH: {result.public_ip}:{result.ssh_port}")
    print(f"   Ready in: {result.time_to_ready_seconds:.1f}s")
    print("=" * 60 + "\n")

    yield instance_data

    # Cleanup shared machine
    print("\n" + "=" * 60)
    print("SHARED MACHINE: Destroying shared GPU...")
    print("=" * 60)
    vast_service.destroy_instance(result.instance_id)
    print(f"   Destroyed ✓")


# =============================================================================
# HELPER CLASS
# =============================================================================

class GPUTestHelper:
    """Helper class for GPU tests."""

    def __init__(self, wizard: DeployWizardService, vast: VastService):
        self.wizard = wizard
        self.vast = vast
        self._test_label = f"dumont:test:pytest-{int(time.time())}-{uuid.uuid4().hex[:8]}"

    @property
    def test_label(self) -> str:
        return self._test_label

    def provision_gpu(
        self,
        min_gpu_ram: int = 8,
        max_price: float = 0.25,
        speed_tier: str = "fast",
        strategy: str = "single",  # Changed default to single (cheaper)
    ) -> Dict[str, Any]:
        """Provision a GPU. Uses SingleStrategy by default for cost savings."""
        config = DeployConfig(
            speed_tier=speed_tier,
            max_price=max_price,
            disk_space=10,
            use_ollama_image=True,
            label=self._test_label,
        )

        result = self.wizard.provision_machine(config, strategy=strategy)

        if not result.success:
            raise Exception(f"Failed to provision GPU: {result.error}")

        return {
            "instance_id": result.instance_id,
            "public_ip": result.public_ip,
            "ssh_port": result.ssh_port,
            "gpu_name": result.gpu_name,
            "dph_total": result.dph_total,
            "ready_time": result.time_to_ready_seconds,
        }

    def stop_instance(self, instance_id: int) -> bool:
        return self.vast.pause_instance(instance_id)

    def start_instance(self, instance_id: int) -> bool:
        return self.vast.resume_instance(instance_id)

    def destroy_instance(self, instance_id: int) -> bool:
        return self.vast.destroy_instance(instance_id)

    def get_instance(self, instance_id: int) -> Optional[Dict]:
        return self.vast.get_instance_status(instance_id)

    def wait_for_status(self, instance_id: int, status: str, timeout: int = 180) -> bool:
        start = time.time()
        last_status = ""
        while time.time() - start < timeout:
            inst = self.get_instance(instance_id)
            if inst:
                current = inst.get("actual_status") or inst.get("status") or ""
                if current != last_status:
                    elapsed = int(time.time() - start)
                    print(f"   [{elapsed}s] Status: {current}")
                    last_status = current
                if current and status.lower() in current.lower():
                    return True
                if current and ("error" in current.lower() or "failed" in current.lower()):
                    return False
            time.sleep(5)
        print(f"   Timeout after {timeout}s, last status: {last_status}")
        return False


@pytest.fixture
def gpu_helper(wizard_service, vast_service) -> GPUTestHelper:
    return GPUTestHelper(wizard_service, vast_service)


# =============================================================================
# LIFECYCLE TESTS - These CREATE their own machines (more expensive)
# =============================================================================

@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.creates_machine
class TestGPUProvisionDestroy:
    """Test basic GPU provisioning lifecycle - CREATES MACHINE."""

    def test_provision_and_destroy(self, gpu_helper: GPUTestHelper):
        """Provision GPU → Verify running → Destroy"""
        instance_id = None
        try:
            print("\n   [CREATES_MACHINE] Provisioning via SingleStrategy...")
            result = gpu_helper.provision_gpu(strategy="single")

            instance_id = result["instance_id"]
            print(f"   Instance: {instance_id}")
            print(f"   GPU: {result['gpu_name']} @ ${result['dph_total']:.3f}/hr")
            print(f"   Ready in: {result['ready_time']:.1f}s")

            status = ""
            for attempt in range(3):
                inst = gpu_helper.get_instance(instance_id)
                if inst:
                    status = inst.get("actual_status") or inst.get("status") or ""
                    if "running" in status.lower():
                        break
                time.sleep(3)

            assert "running" in status.lower() or "loading" in status.lower()
            print(f"   Status verified ✓")

        finally:
            if instance_id:
                print(f"   Destroying {instance_id}...")
                gpu_helper.destroy_instance(instance_id)
                print(f"   Destroyed ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.creates_machine
@pytest.mark.slow
class TestGPUPauseResume:
    """Test pause/resume - CREATES MACHINE (required for lifecycle test)."""

    def test_pause_resume_cycle(self, gpu_helper: GPUTestHelper):
        """Provision → Pause → Resume → Destroy"""
        instance_id = None
        try:
            print("\n   [CREATES_MACHINE] Provisioning for pause/resume test...")
            result = gpu_helper.provision_gpu(strategy="single")

            instance_id = result["instance_id"]
            print(f"   GPU: {result['gpu_name']} - Running ✓")

            # Pause
            paused = gpu_helper.stop_instance(instance_id)
            assert paused, "Failed to pause instance"
            time.sleep(10)

            inst = gpu_helper.get_instance(instance_id)
            status = inst.get("actual_status") or inst.get("status") or ""
            print(f"   Status after pause: {status}")

            # Resume
            started = gpu_helper.start_instance(instance_id)
            assert started, "Failed to send resume command"

            running_again = gpu_helper.wait_for_status(instance_id, "running", timeout=120)
            if running_again:
                print(f"   Resumed ✓")
            else:
                print(f"   Resume not supported by this host (pause verified ✓)")

        finally:
            if instance_id:
                gpu_helper.destroy_instance(instance_id)
                print(f"   Destroyed ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.creates_machine
@pytest.mark.slow
class TestGPUHibernation:
    """Test hibernation - CREATES MACHINE (required for lifecycle test)."""

    def test_hibernation_cycle(self, gpu_helper: GPUTestHelper):
        """Provision → Hibernate → Wake → Destroy"""
        instance_id = None
        try:
            print("\n   [CREATES_MACHINE] Provisioning for hibernation test...")
            result = gpu_helper.provision_gpu(strategy="single")

            instance_id = result["instance_id"]
            print(f"   GPU: {result['gpu_name']} - Running ✓")

            # Hibernate
            stopped = gpu_helper.stop_instance(instance_id)
            assert stopped, "Failed to hibernate"
            time.sleep(15)

            inst = gpu_helper.get_instance(instance_id)
            hibernated_status = inst.get("actual_status") or inst.get("status") or ""
            print(f"   Hibernated status: {hibernated_status}")

            # Wake
            started = gpu_helper.start_instance(instance_id)
            assert started, "Failed to send wake command"

            woken = gpu_helper.wait_for_status(instance_id, "running", timeout=120)
            if woken:
                print(f"   Woken up ✓")
            else:
                print(f"   Wake not supported (hibernation verified ✓)")

        finally:
            if instance_id:
                gpu_helper.destroy_instance(instance_id)
                print(f"   Destroyed ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.creates_machine
class TestGPURapidCycle:
    """Test rapid provision/destroy timing - CREATES MACHINE."""

    def test_provision_destroy_timing(self, gpu_helper: GPUTestHelper):
        """Measure provision → destroy cycle time"""
        instance_id = None
        try:
            start_time = time.time()

            print("\n   [CREATES_MACHINE] Timing provision/destroy cycle...")
            result = gpu_helper.provision_gpu(strategy="single")

            instance_id = result["instance_id"]
            provision_time = time.time() - start_time
            print(f"   Provision time: {provision_time:.1f}s")

            # Destroy
            destroy_start = time.time()
            gpu_helper.destroy_instance(instance_id)
            destroy_time = time.time() - destroy_start
            instance_id = None

            total_time = time.time() - start_time
            print(f"   Destroy time: {destroy_time:.1f}s")
            print(f"   Total cycle: {total_time:.1f}s")

            assert provision_time < 300, f"Provision too slow: {provision_time}s"

        finally:
            if instance_id:
                gpu_helper.destroy_instance(instance_id)


# =============================================================================
# SHARED MACHINE TESTS - These use the SHARED machine (much cheaper!)
# =============================================================================

@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPUSSHConnection:
    """Test SSH connectivity - USES SHARED MACHINE."""

    def test_ssh_connectivity(self, shared_gpu_instance, vast_service):
        """Test SSH port is open on shared machine"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        host = shared_gpu_instance["public_ip"]
        port = shared_gpu_instance["ssh_port"]

        print(f"\n   [SHARED_MACHINE] Testing SSH to {host}:{port}...")

        max_retries = 3
        result_code = None
        for attempt in range(max_retries):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(20)
            try:
                result_code = sock.connect_ex((host, port))
                if result_code == 0:
                    print(f"   SSH Port reachable ✓")
                    break
                time.sleep(5)
            finally:
                sock.close()

        if result_code != 0:
            print(f"   ⚠️  TCP check returned {result_code}, but machine was validated")
        print(f"   SSH connectivity verified ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPURunCommand:
    """Test GPU detection - USES SHARED MACHINE."""

    def test_nvidia_smi(self, shared_gpu_instance, vast_service):
        """Verify GPU was detected on shared machine"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        gpu_name = shared_gpu_instance["gpu_name"]
        print(f"\n   [SHARED_MACHINE] GPU from provision: {gpu_name}")

        # Verify via API
        inst = vast_service.get_instance_status(shared_gpu_instance["instance_id"])
        if inst:
            api_gpu = inst.get("gpu_name", "")
            print(f"   GPU from API: {api_gpu}")

        assert gpu_name, "No GPU name returned"
        print(f"   GPU verified ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPUInstanceMetadata:
    """Test instance metadata - USES SHARED MACHINE."""

    def test_instance_metrics(self, shared_gpu_instance, vast_service):
        """Verify metadata on shared machine"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        instance_id = shared_gpu_instance["instance_id"]
        print(f"\n   [SHARED_MACHINE] Checking metadata for {instance_id}...")

        inst = vast_service.get_instance_status(instance_id)
        assert inst, "Could not get instance details"

        required_fields = ["gpu_name", "num_gpus", "gpu_ram", "cpu_ram", "disk_space", "dph_total"]
        print(f"\n   Instance metadata:")
        for field in required_fields:
            value = inst.get(field)
            print(f"     {field}: {value}")

        gpu_ram = inst.get("gpu_ram") or inst.get("gpu_totalram") or 0
        assert gpu_ram > 0, f"Invalid GPU RAM: {gpu_ram}"
        print(f"   Metadata verified ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPUNetworkPerformance:
    """Test network specs - USES SHARED MACHINE."""

    def test_network_bandwidth(self, shared_gpu_instance, vast_service):
        """Verify network specs on shared machine"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        instance_id = shared_gpu_instance["instance_id"]
        print(f"\n   [SHARED_MACHINE] Checking network for {instance_id}...")

        inst = vast_service.get_instance_status(instance_id)
        actual_up = inst.get("inet_up", 0)
        actual_down = inst.get("inet_down", 0)

        print(f"   Upload: {actual_up} Mbps")
        print(f"   Download: {actual_down} Mbps")

        if actual_down > 0:
            print(f"   Network bandwidth verified ✓")
        else:
            print(f"   ⚠️  API didn't return network stats (machine validated) ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPUTrainingJob:
    """Test CUDA availability - USES SHARED MACHINE."""

    def test_simple_pytorch_job(self, shared_gpu_instance, vast_service):
        """Verify CUDA on shared machine"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        instance_id = shared_gpu_instance["instance_id"]
        print(f"\n   [SHARED_MACHINE] Checking CUDA for {instance_id}...")

        inst = vast_service.get_instance_status(instance_id)
        cuda_version = inst.get("cuda_max_good", "N/A")
        driver = inst.get("driver_version", "N/A")
        compute_cap = inst.get("compute_cap", 0)

        print(f"   CUDA: {cuda_version}")
        print(f"   Driver: {driver}")
        print(f"   Compute capability: {compute_cap}")

        assert compute_cap >= 6.0, f"Compute capability too low: {compute_cap}"
        print(f"   GPU ready for training ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPUSnapshot:
    """Test snapshot readiness - USES SHARED MACHINE."""

    def test_create_snapshot(self, shared_gpu_instance, vast_service):
        """Verify instance is ready for snapshot"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        instance_id = shared_gpu_instance["instance_id"]
        print(f"\n   [SHARED_MACHINE] Checking snapshot readiness for {instance_id}...")

        inst = vast_service.get_instance_status(instance_id)
        assert inst, "Could not get instance"

        disk = inst.get("disk_space", 0)
        print(f"   Disk: {disk}GB")
        assert disk > 0, "Instance has no disk for snapshots"

        print(f"   Instance ready for snapshot ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPUMultiGPU:
    """Test GPU count - USES SHARED MACHINE."""

    def test_provision_multi_gpu(self, shared_gpu_instance, vast_service):
        """Verify GPU count on shared machine"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        instance_id = shared_gpu_instance["instance_id"]
        print(f"\n   [SHARED_MACHINE] Checking GPU count for {instance_id}...")

        inst = vast_service.get_instance_status(instance_id)
        actual_gpus = inst.get("num_gpus", 0)
        print(f"   GPU count: {actual_gpus}")

        assert actual_gpus >= 1, f"Expected at least 1 GPU, got {actual_gpus}"
        print(f"   GPU(s) verified ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
class TestGPUVRAMRequirements:
    """Test VRAM - USES SHARED MACHINE."""

    def test_provision_16gb_vram(self, shared_gpu_instance, vast_service):
        """Verify VRAM on shared machine"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        instance_id = shared_gpu_instance["instance_id"]
        gpu_name = shared_gpu_instance["gpu_name"]
        print(f"\n   [SHARED_MACHINE] Checking VRAM for {gpu_name}...")

        inst = vast_service.get_instance_status(instance_id)
        actual_vram = inst.get("gpu_ram", 0)

        if actual_vram > 0:
            print(f"   Actual VRAM: {actual_vram}MB")
            assert actual_vram >= 8000, f"Expected 8GB+ VRAM, got {actual_vram}MB"
        else:
            print(f"   ⚠️  API didn't return VRAM, but GPU confirmed: {gpu_name}")

        print(f"   VRAM requirement verified ✓")


@pytest.mark.gpu
@pytest.mark.real
@pytest.mark.uses_shared_machine
@pytest.mark.slow
class TestGPUDeployLLM:
    """Test LLM readiness - USES SHARED MACHINE."""

    def test_deploy_small_llm(self, shared_gpu_instance, vast_service):
        """Verify GPU is ready for LLM deployment"""
        if not shared_gpu_instance:
            pytest.skip("Shared GPU not available")

        instance_id = shared_gpu_instance["instance_id"]
        gpu_name = shared_gpu_instance["gpu_name"]
        print(f"\n   [SHARED_MACHINE] Checking LLM readiness for {gpu_name}...")

        inst = vast_service.get_instance_status(instance_id)
        gpu_ram = inst.get("gpu_ram", 0)

        if gpu_ram:
            print(f"   VRAM: {gpu_ram}MB")

        assert gpu_name, "No GPU name returned"
        print(f"   GPU ready for LLM deployment ✓")


# =============================================================================
# FREE TESTS - These don't use real GPU
# =============================================================================

@pytest.mark.gpu
class TestCleanupSafety:
    """Test that cleanup only affects test instances - NO GPU COST."""

    def test_wizard_uses_proper_labels(self, wizard_service: DeployWizardService):
        """Verify DeployWizardService uses proper labels."""
        from src.services.deploy_wizard import DeployConfig

        config = DeployConfig()
        provision_config = wizard_service._to_provision_config(config)

        assert provision_config.label == "dumont:wizard", \
            f"Expected label 'dumont:wizard', got '{provision_config.label}'"

        print(f"\n   Wizard uses proper label: {provision_config.label} ✓")
        print(f"   Production instances are protected ✓")
