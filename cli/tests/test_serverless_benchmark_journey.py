#!/usr/bin/env python3
"""
Testes de Jornada BENCHMARK - Medição de latência serverless

Usa instâncias EXISTENTES (não cria novas) para medir:
- Latência de PAUSE (tempo para parar)
- Latência de RESUME (cold start)
- Comparação entre GPUs diferentes
- Comparação entre providers (VAST.ai, TensorDock, GCP)

Para rodar:
    cd /home/marcos/dumontcloud/cli
    pytest tests/test_serverless_benchmark_journey.py -v -s
"""
import pytest
import time
import json
import os
import sys
import requests
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# CONFIGURATION
# =============================================================================

API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
CONFIG_FILE = Path("/home/marcos/dumontcloud/config.json")
ENV_FILE = Path("/home/marcos/dumontcloud/.env")

# SLA Targets (em segundos) - ajustados baseado em benchmarks reais
SLA_TARGETS = {
    "vast_pause": 60.0,      # VAST.ai pause (varia muito por host)
    "vast_resume": 60.0,     # VAST.ai resume - 4060 Ti pode ser 40s+
    "tensordock_start": 15.0,
    "tensordock_stop": 10.0,
    "gcp_start": 15.0,
    "gcp_stop": 180.0,       # GCP stop pode demorar muito
}


@dataclass
class BenchmarkResult:
    """Resultado de um benchmark"""
    provider: str
    instance_id: str
    gpu_name: str
    operation: str  # "pause", "resume", "start", "stop"
    duration_seconds: float
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


@dataclass
class BenchmarkSummary:
    """Resumo de todos os benchmarks"""
    results: List[BenchmarkResult] = field(default_factory=list)

    def add(self, result: BenchmarkResult):
        self.results.append(result)

    def get_average(self, provider: str, operation: str) -> float:
        filtered = [r for r in self.results
                   if r.provider == provider and r.operation == operation and r.success]
        if not filtered:
            return 0.0
        return sum(r.duration_seconds for r in filtered) / len(filtered)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "results": [
                {
                    "provider": r.provider,
                    "instance_id": r.instance_id,
                    "gpu_name": r.gpu_name,
                    "operation": r.operation,
                    "duration_seconds": r.duration_seconds,
                    "success": r.success,
                    "error": r.error,
                }
                for r in self.results
            ],
            "summary": {
                "vast_pause_avg": self.get_average("vast", "pause"),
                "vast_resume_avg": self.get_average("vast", "resume"),
                "tensordock_start_avg": self.get_average("tensordock", "start"),
                "tensordock_stop_avg": self.get_average("tensordock", "stop"),
                "gcp_start_avg": self.get_average("gcp", "start"),
                "gcp_stop_avg": self.get_average("gcp", "stop"),
            }
        }


# =============================================================================
# VAST.AI PROVIDER
# =============================================================================

class VastProvider:
    """Provider para VAST.ai"""

    def __init__(self):
        self.api_key = self._get_api_key()
        self.api_url = "https://console.vast.ai/api/v0"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def _get_api_key(self) -> str:
        """Get VAST.ai API key from config"""
        if CONFIG_FILE.exists():
            config = json.loads(CONFIG_FILE.read_text())
            for user in config.get("users", {}).values():
                if user.get("vast_api_key"):
                    return user["vast_api_key"]
        return os.environ.get("VAST_API_KEY", "")

    def get_running_instances(self) -> List[Dict]:
        """Get all running instances"""
        resp = requests.get(
            f"{self.api_url}/instances/",
            headers=self.headers,
            timeout=30
        )
        if resp.status_code == 200:
            instances = resp.json().get("instances", [])
            return [i for i in instances if i.get("actual_status") == "running"]
        return []

    def get_instance_status(self, instance_id: int) -> Optional[str]:
        """Get instance status"""
        resp = requests.get(
            f"{self.api_url}/instances/",
            headers=self.headers,
            timeout=30
        )
        if resp.status_code == 200:
            for inst in resp.json().get("instances", []):
                if inst.get("id") == instance_id:
                    return inst.get("actual_status")
        return None

    def pause(self, instance_id: int) -> bool:
        """Pause instance"""
        resp = requests.put(
            f"{self.api_url}/instances/{instance_id}/",
            headers=self.headers,
            json={"state": "stopped"},
            timeout=30
        )
        return resp.status_code == 200

    def resume(self, instance_id: int) -> bool:
        """Resume instance"""
        resp = requests.put(
            f"{self.api_url}/instances/{instance_id}/",
            headers=self.headers,
            json={"state": "running"},
            timeout=30
        )
        return resp.status_code == 200

    def wait_for_status(
        self,
        instance_id: int,
        target_statuses: List[str],
        max_wait: int = 120
    ) -> Tuple[bool, float]:
        """Wait for instance to reach target status"""
        start = time.time()
        while time.time() - start < max_wait:
            status = self.get_instance_status(instance_id)
            if status in target_statuses:
                return True, time.time() - start
            time.sleep(2)
        return False, time.time() - start


# =============================================================================
# TENSORDOCK PROVIDER
# =============================================================================

class TensorDockProvider:
    """Provider para TensorDock"""

    def __init__(self):
        self.auth_id = os.environ.get("TENSORDOCK_AUTH_ID", "")
        self.api_token = os.environ.get("TENSORDOCK_API_TOKEN", "")
        self.api_url = "https://marketplace.tensordock.com/api/v0"

        # Load from .env if not in environ
        if not self.auth_id and ENV_FILE.exists():
            for line in ENV_FILE.read_text().split("\n"):
                if line.startswith("TENSORDOCK_AUTH_ID="):
                    self.auth_id = line.split("=", 1)[1].strip()
                elif line.startswith("TENSORDOCK_API_TOKEN="):
                    self.api_token = line.split("=", 1)[1].strip()

    @property
    def configured(self) -> bool:
        return bool(self.auth_id and self.api_token)

    def get_vms(self) -> List[Dict]:
        """Get all VMs"""
        if not self.configured:
            return []

        resp = requests.post(
            f"{self.api_url}/client/list",
            data={
                "api_key": self.auth_id,
                "api_token": self.api_token
            },
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return list(data.get("virtualmachines", {}).values())
        return []

    def get_vm_status(self, vm_id: str) -> Optional[str]:
        """Get VM status"""
        vms = self.get_vms()
        for vm in vms:
            if str(vm.get("id")) == str(vm_id):
                return vm.get("status")
        return None

    def start(self, vm_id: str) -> bool:
        """Start VM"""
        resp = requests.post(
            f"{self.api_url}/client/start/single",
            data={
                "api_key": self.auth_id,
                "api_token": self.api_token,
                "server": vm_id
            },
            timeout=30
        )
        return resp.status_code == 200 and resp.json().get("success", False)

    def stop(self, vm_id: str) -> bool:
        """Stop VM"""
        resp = requests.post(
            f"{self.api_url}/client/stop/single",
            data={
                "api_key": self.auth_id,
                "api_token": self.api_token,
                "server": vm_id
            },
            timeout=30
        )
        return resp.status_code == 200 and resp.json().get("success", False)

    def wait_for_status(
        self,
        vm_id: str,
        target_status: str,
        max_wait: int = 120
    ) -> Tuple[bool, float]:
        """Wait for VM to reach target status"""
        start = time.time()
        while time.time() - start < max_wait:
            status = self.get_vm_status(vm_id)
            if status and status.lower() == target_status.lower():
                return True, time.time() - start
            time.sleep(2)
        return False, time.time() - start


# =============================================================================
# GCP PROVIDER
# =============================================================================

class GCPProvider:
    """Provider para Google Cloud Platform"""

    def __init__(self):
        self.project_id = os.environ.get("GCP_PROJECT_ID", "")
        self.credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        self._client = None

        # Load from .env if not in environ
        if not self.project_id and ENV_FILE.exists():
            for line in ENV_FILE.read_text().split("\n"):
                if line.startswith("GCP_PROJECT_ID="):
                    self.project_id = line.split("=", 1)[1].strip()
                elif line.startswith("GOOGLE_APPLICATION_CREDENTIALS="):
                    self.credentials_path = line.split("=", 1)[1].strip()

    @property
    def configured(self) -> bool:
        return bool(self.project_id and self.credentials_path)

    @property
    def client(self):
        if self._client is None and self.configured:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            from google.cloud import compute_v1
            self._client = compute_v1.InstancesClient()
        return self._client

    def get_instances(self) -> List[Dict]:
        """Get all instances"""
        if not self.configured:
            return []

        try:
            from google.cloud import compute_v1
            instances = []
            agg_list = self.client.aggregated_list(project=self.project_id)

            for zone, response in agg_list:
                if response.instances:
                    for inst in response.instances:
                        instances.append({
                            "name": inst.name,
                            "zone": zone.split("/")[-1],
                            "status": inst.status,
                            "machine_type": inst.machine_type.split("/")[-1],
                        })
            return instances
        except Exception as e:
            print(f"GCP error: {e}")
            return []

    def get_instance_status(self, name: str, zone: str) -> Optional[str]:
        """Get instance status"""
        try:
            inst = self.client.get(project=self.project_id, zone=zone, instance=name)
            return inst.status
        except:
            return None

    def start(self, name: str, zone: str) -> bool:
        """Start instance"""
        try:
            self.client.start(project=self.project_id, zone=zone, instance=name)
            return True
        except Exception as e:
            print(f"GCP start error: {e}")
            return False

    def stop(self, name: str, zone: str) -> bool:
        """Stop instance"""
        try:
            self.client.stop(project=self.project_id, zone=zone, instance=name)
            return True
        except Exception as e:
            print(f"GCP stop error: {e}")
            return False

    def wait_for_status(
        self,
        name: str,
        zone: str,
        target_status: str,
        max_wait: int = 120
    ) -> Tuple[bool, float]:
        """Wait for instance to reach target status"""
        start = time.time()
        while time.time() - start < max_wait:
            status = self.get_instance_status(name, zone)
            if status == target_status:
                return True, time.time() - start
            time.sleep(2)
        return False, time.time() - start


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def vast_provider():
    """VAST.ai provider fixture"""
    provider = VastProvider()
    if not provider.api_key:
        pytest.skip("VAST.ai API key not configured")
    return provider


@pytest.fixture(scope="module")
def tensordock_provider():
    """TensorDock provider fixture"""
    provider = TensorDockProvider()
    if not provider.configured:
        pytest.skip("TensorDock credentials not configured")
    return provider


@pytest.fixture(scope="module")
def gcp_provider():
    """GCP provider fixture"""
    provider = GCPProvider()
    if not provider.configured:
        pytest.skip("GCP credentials not configured")
    return provider


@pytest.fixture(scope="module")
def benchmark_summary():
    """Shared benchmark summary"""
    return BenchmarkSummary()


# =============================================================================
# TESTS - VAST.AI
# =============================================================================

class TestVastBenchmark:
    """Testes de benchmark VAST.ai"""

    def test_vast_list_running(self, vast_provider):
        """Lista instâncias running no VAST.ai"""
        instances = vast_provider.get_running_instances()

        print(f"\n📊 VAST.ai - Instâncias running: {len(instances)}")
        for inst in instances:
            print(f"   - {inst['id']}: {inst.get('gpu_name')} @ ${inst.get('dph_total', 0):.4f}/hr")

        assert len(instances) >= 0  # OK mesmo sem instâncias

    @pytest.mark.benchmark
    def test_vast_pause_resume_cycle(self, vast_provider, benchmark_summary):
        """
        Testa ciclo completo pause/resume no VAST.ai

        Mede:
        - Tempo de PAUSE (até status=stopped)
        - Tempo de RESUME (cold start até status=running)
        """
        instances = vast_provider.get_running_instances()

        if not instances:
            pytest.skip("No running VAST.ai instances available")

        # Usar primeira instância running
        instance = instances[0]
        instance_id = instance["id"]
        gpu_name = instance.get("gpu_name", "Unknown")

        print(f"\n🎯 Testing VAST.ai instance {instance_id} ({gpu_name})")

        # === PAUSE ===
        print(f"\n⏸️  PAUSE test...")
        start = time.time()

        assert vast_provider.pause(instance_id), "Failed to send pause command"
        success, elapsed = vast_provider.wait_for_status(
            instance_id,
            ["stopped", "exited"],
            max_wait=60
        )
        pause_time = time.time() - start

        benchmark_summary.add(BenchmarkResult(
            provider="vast",
            instance_id=str(instance_id),
            gpu_name=gpu_name,
            operation="pause",
            duration_seconds=pause_time,
            success=success,
        ))

        print(f"   {'✅' if success else '❌'} PAUSE: {pause_time:.2f}s")

        time.sleep(3)  # Brief pause between operations

        # === RESUME ===
        print(f"\n▶️  RESUME test (cold start)...")
        start = time.time()

        assert vast_provider.resume(instance_id), "Failed to send resume command"
        success, elapsed = vast_provider.wait_for_status(
            instance_id,
            ["running"],
            max_wait=120
        )
        resume_time = time.time() - start

        benchmark_summary.add(BenchmarkResult(
            provider="vast",
            instance_id=str(instance_id),
            gpu_name=gpu_name,
            operation="resume",
            duration_seconds=resume_time,
            success=success,
        ))

        print(f"   {'✅' if success else '❌'} RESUME (cold start): {resume_time:.2f}s")

        # Assertions
        assert success, f"Resume failed after {resume_time:.2f}s"
        assert resume_time < SLA_TARGETS["vast_resume"], \
            f"Resume too slow: {resume_time:.2f}s > {SLA_TARGETS['vast_resume']}s"


# =============================================================================
# TESTS - TENSORDOCK
# =============================================================================

class TestTensorDockBenchmark:
    """Testes de benchmark TensorDock"""

    def test_tensordock_list_vms(self, tensordock_provider):
        """Lista VMs no TensorDock"""
        vms = tensordock_provider.get_vms()

        print(f"\n📊 TensorDock - VMs: {len(vms)}")
        for vm in vms:
            print(f"   - {vm.get('id')}: {vm.get('gpu_model')} ({vm.get('status')})")

        assert len(vms) >= 0

    @pytest.mark.benchmark
    def test_tensordock_stop_start_cycle(self, tensordock_provider, benchmark_summary):
        """
        Testa ciclo completo stop/start no TensorDock

        Mede:
        - Tempo de STOP
        - Tempo de START (cold start)
        """
        vms = tensordock_provider.get_vms()
        running = [vm for vm in vms if vm.get("status", "").lower() == "running"]

        if not running:
            pytest.skip("No running TensorDock VMs available")

        vm = running[0]
        vm_id = str(vm.get("id"))
        gpu_name = vm.get("gpu_model", "Unknown")

        print(f"\n🎯 Testing TensorDock VM {vm_id} ({gpu_name})")

        # === STOP ===
        print(f"\n⏹️  STOP test...")
        start = time.time()

        assert tensordock_provider.stop(vm_id), "Failed to send stop command"
        success, elapsed = tensordock_provider.wait_for_status(
            vm_id,
            "stopped",
            max_wait=60
        )
        stop_time = time.time() - start

        benchmark_summary.add(BenchmarkResult(
            provider="tensordock",
            instance_id=vm_id,
            gpu_name=gpu_name,
            operation="stop",
            duration_seconds=stop_time,
            success=success,
        ))

        print(f"   {'✅' if success else '❌'} STOP: {stop_time:.2f}s")

        time.sleep(3)

        # === START ===
        print(f"\n▶️  START test (cold start)...")
        start = time.time()

        assert tensordock_provider.start(vm_id), "Failed to send start command"
        success, elapsed = tensordock_provider.wait_for_status(
            vm_id,
            "running",
            max_wait=120
        )
        start_time = time.time() - start

        benchmark_summary.add(BenchmarkResult(
            provider="tensordock",
            instance_id=vm_id,
            gpu_name=gpu_name,
            operation="start",
            duration_seconds=start_time,
            success=success,
        ))

        print(f"   {'✅' if success else '❌'} START (cold start): {start_time:.2f}s")

        assert success, f"Start failed after {start_time:.2f}s"


# =============================================================================
# TESTS - GCP
# =============================================================================

class TestGCPBenchmark:
    """Testes de benchmark GCP"""

    def test_gcp_list_instances(self, gcp_provider):
        """Lista instâncias no GCP"""
        instances = gcp_provider.get_instances()

        print(f"\n📊 GCP - Instâncias: {len(instances)}")
        for inst in instances:
            print(f"   - {inst['name']}: {inst['machine_type']} ({inst['status']})")

        assert len(instances) >= 0

    @pytest.mark.benchmark
    def test_gcp_stop_start_cycle(self, gcp_provider, benchmark_summary):
        """
        Testa ciclo completo stop/start no GCP

        Mede:
        - Tempo de START
        - Tempo de STOP
        """
        instances = gcp_provider.get_instances()
        terminated = [i for i in instances if i["status"] == "TERMINATED"]

        if not terminated:
            pytest.skip("No TERMINATED GCP instances available")

        inst = terminated[0]
        name = inst["name"]
        zone = inst["zone"]

        print(f"\n🎯 Testing GCP instance {name} ({zone})")

        # === START ===
        print(f"\n▶️  START test...")
        start = time.time()

        assert gcp_provider.start(name, zone), "Failed to send start command"
        success, elapsed = gcp_provider.wait_for_status(
            name, zone, "RUNNING", max_wait=120
        )
        start_time = time.time() - start

        benchmark_summary.add(BenchmarkResult(
            provider="gcp",
            instance_id=name,
            gpu_name=inst["machine_type"],
            operation="start",
            duration_seconds=start_time,
            success=success,
        ))

        print(f"   {'✅' if success else '❌'} START: {start_time:.2f}s")

        time.sleep(5)

        # === STOP ===
        print(f"\n⏹️  STOP test...")
        start = time.time()

        assert gcp_provider.stop(name, zone), "Failed to send stop command"
        success, elapsed = gcp_provider.wait_for_status(
            name, zone, "TERMINATED", max_wait=120
        )
        stop_time = time.time() - start

        benchmark_summary.add(BenchmarkResult(
            provider="gcp",
            instance_id=name,
            gpu_name=inst["machine_type"],
            operation="stop",
            duration_seconds=stop_time,
            success=success,
        ))

        print(f"   {'✅' if success else '❌'} STOP: {stop_time:.2f}s")


# =============================================================================
# SUMMARY TEST
# =============================================================================

class TestVastMultiGPUBenchmark:
    """Testes de benchmark comparando múltiplas GPUs no VAST.ai"""

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_vast_multi_gpu_comparison(self, vast_provider, benchmark_summary):
        """
        Compara cold start de múltiplas GPUs no VAST.ai

        Importante: Este teste pausa/resume TODAS as GPUs disponíveis
        para encontrar quais têm melhor latência.
        """
        instances = vast_provider.get_running_instances()

        if len(instances) < 2:
            pytest.skip("Need at least 2 running instances for comparison")

        print(f"\n🔬 Multi-GPU Comparison Test ({len(instances)} GPUs)")
        print("="*60)

        results = []

        for inst in instances[:5]:  # Limitar a 5 GPUs
            instance_id = inst["id"]
            gpu_name = inst.get("gpu_name", "Unknown")

            print(f"\n🎯 Testing {gpu_name} (ID: {instance_id})")

            # PAUSE
            print(f"   ⏸️  Pausing...", end="", flush=True)
            start = time.time()
            vast_provider.pause(instance_id)
            success, _ = vast_provider.wait_for_status(
                instance_id, ["stopped", "exited"], max_wait=60
            )
            pause_time = time.time() - start
            print(f" {pause_time:.1f}s")

            benchmark_summary.add(BenchmarkResult(
                provider="vast",
                instance_id=str(instance_id),
                gpu_name=gpu_name,
                operation="pause",
                duration_seconds=pause_time,
                success=success,
            ))

            time.sleep(2)

            # RESUME
            print(f"   ▶️  Resuming...", end="", flush=True)
            start = time.time()
            vast_provider.resume(instance_id)
            success, _ = vast_provider.wait_for_status(
                instance_id, ["running"], max_wait=120
            )
            resume_time = time.time() - start
            print(f" {resume_time:.1f}s")

            benchmark_summary.add(BenchmarkResult(
                provider="vast",
                instance_id=str(instance_id),
                gpu_name=gpu_name,
                operation="resume",
                duration_seconds=resume_time,
                success=success,
            ))

            results.append({
                "gpu": gpu_name,
                "instance_id": instance_id,
                "pause": pause_time,
                "resume": resume_time,
                "total": pause_time + resume_time,
            })

            time.sleep(3)

        # Ranking
        print("\n" + "="*60)
        print("📊 GPU RANKING (by cold start time)")
        print("="*60)
        print(f"{'GPU':<20} {'Pause':>10} {'Resume':>10} {'Total':>10}")
        print("-"*60)

        for r in sorted(results, key=lambda x: x['resume']):
            print(f"{r['gpu']:<20} {r['pause']:>9.1f}s {r['resume']:>9.1f}s {r['total']:>9.1f}s")

        print("="*60)

        # Best GPU
        if results:
            best = min(results, key=lambda x: x['resume'])
            worst = max(results, key=lambda x: x['resume'])
            print(f"\n🏆 FASTEST: {best['gpu']} ({best['resume']:.1f}s cold start)")
            print(f"🐌 SLOWEST: {worst['gpu']} ({worst['resume']:.1f}s cold start)")
            print(f"📈 Variance: {worst['resume'] - best['resume']:.1f}s ({worst['resume']/best['resume']:.1f}x)")


class TestBenchmarkSummary:
    """Teste que imprime resumo final"""

    def test_print_summary(self, benchmark_summary):
        """Imprime resumo de todos os benchmarks"""

        print("\n" + "="*70)
        print("📊 BENCHMARK SUMMARY - ALL PROVIDERS")
        print("="*70)

        summary = benchmark_summary.to_dict()

        print(f"\nTotal results: {len(summary['results'])}")

        if summary['results']:
            print("\n┌────────────────┬─────────────────┬───────────┬──────────┬─────────┐")
            print("│ Provider       │ Instance        │ Operation │ Time (s) │ Status  │")
            print("├────────────────┼─────────────────┼───────────┼──────────┼─────────┤")

            for r in summary['results']:
                status = "✅" if r['success'] else "❌"
                print(f"│ {r['provider']:<14} │ {r['instance_id'][:15]:<15} │ {r['operation']:<9} │ {r['duration_seconds']:>8.2f} │ {status:<7} │")

            print("└────────────────┴─────────────────┴───────────┴──────────┴─────────┘")

            print("\n📈 Averages:")
            for key, value in summary['summary'].items():
                if value > 0:
                    print(f"   {key}: {value:.2f}s")

        # Save results
        results_file = Path("/home/marcos/dumontcloud/cli/tests/benchmark_journey_results.json")
        results_file.write_text(json.dumps(summary, indent=2))
        print(f"\n💾 Results saved to: {results_file}")

        print("="*70)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
