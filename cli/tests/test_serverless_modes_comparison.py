#!/usr/bin/env python3
"""
Testes de Jornada - Comparação de TODOS os Modos Serverless

Compara os 3 modos disponíveis:
1. FAST - CPU Standby (GCP) - recovery <1s teórico
2. ECONOMIC - VAST.ai pause/resume - recovery 7-40s
3. SPOT - Instâncias spot + failover - recovery ~30s

Para rodar:
    cd /home/marcos/dumontcloud/cli
    pytest tests/test_serverless_modes_comparison.py -v -s
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# CONFIGURATION
# =============================================================================

API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
CONFIG_FILE = Path("/home/marcos/dumontcloud/config.json")


@dataclass
class ModeResult:
    """Resultado de teste de um modo"""
    mode: str
    instance_id: int
    gpu_name: str
    enable_time: float = 0.0
    pause_time: float = 0.0
    resume_time: float = 0.0  # Cold start
    total_cycle: float = 0.0
    success: bool = True
    error: Optional[str] = None


class DumontAPI:
    """Cliente para API Dumont"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def get(self, path: str) -> Dict:
        resp = self.session.get(f"{self.base_url}{path}", timeout=30)
        return resp.json() if resp.ok else {"error": resp.text}

    def post(self, path: str, data: Dict = None) -> Dict:
        resp = self.session.post(f"{self.base_url}{path}", json=data or {}, timeout=60)
        return resp.json() if resp.ok else {"error": resp.text}

    def get_instances(self) -> List[Dict]:
        """Get all instances"""
        result = self.get("/api/v1/instances")
        return result.get("instances", [])

    def get_running_instances(self) -> List[Dict]:
        """Get running instances"""
        instances = self.get_instances()
        return [i for i in instances if i.get("status") == "running"]

    def enable_serverless(
        self,
        instance_id: int,
        mode: str,
        idle_timeout: int = 20,
        gpu_threshold: float = 5.0
    ) -> Dict:
        """Enable serverless for an instance"""
        return self.post(f"/api/v1/serverless/enable/{instance_id}", {
            "mode": mode,
            "idle_timeout_seconds": idle_timeout,
            "gpu_threshold": gpu_threshold,
        })

    def disable_serverless(self, instance_id: int) -> Dict:
        """Disable serverless for an instance"""
        return self.post(f"/api/v1/serverless/disable/{instance_id}")

    def get_serverless_status(self, instance_id: int) -> Dict:
        """Get serverless status for an instance"""
        return self.get(f"/api/v1/serverless/status/{instance_id}")

    def wake_instance(self, instance_id: int) -> Dict:
        """Wake up a paused instance"""
        return self.post(f"/api/v1/serverless/wake/{instance_id}")

    def pause_instance(self, instance_id: int) -> Dict:
        """Pause an instance"""
        return self.post(f"/api/v1/instances/{instance_id}/pause")

    def resume_instance(self, instance_id: int) -> Dict:
        """Resume an instance"""
        return self.post(f"/api/v1/instances/{instance_id}/resume")

    def send_idle_heartbeat(self, instance_id: int) -> Dict:
        """Send heartbeat with 0% GPU to trigger idle"""
        return self.post("/api/v1/agent/status", {
            "agent": "DumontAgent",
            "version": "1.0.0",
            "instance_id": str(instance_id),
            "status": "idle",
            "timestamp": datetime.now().isoformat(),
            "gpu_metrics": {
                "utilization": 0.0,
                "gpu_count": 1,
                "gpu_names": ["Test GPU"],
                "gpu_utilizations": [0.0],
                "gpu_memory_used": [0],
                "gpu_memory_total": [16000],
                "gpu_temperatures": [40.0]
            }
        })


class VastDirectAPI:
    """API direta para VAST.ai (bypass Dumont)"""

    def __init__(self):
        self.api_key = self._get_api_key()
        self.api_url = "https://console.vast.ai/api/v0"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def _get_api_key(self) -> str:
        if CONFIG_FILE.exists():
            config = json.loads(CONFIG_FILE.read_text())
            for user in config.get("users", {}).values():
                if user.get("vast_api_key"):
                    return user["vast_api_key"]
        return os.environ.get("VAST_API_KEY", "")

    def get_instance_status(self, instance_id: int) -> Optional[str]:
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

    def wait_for_status(
        self,
        instance_id: int,
        target_statuses: List[str],
        max_wait: int = 120
    ) -> Tuple[bool, float]:
        start = time.time()
        while time.time() - start < max_wait:
            status = self.get_instance_status(instance_id)
            if status in target_statuses:
                return True, time.time() - start
            time.sleep(2)
        return False, time.time() - start


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def dumont_api():
    """Dumont API client"""
    api = DumontAPI()
    # Verify backend is running
    try:
        result = api.get("/api/v1/health")
        if "error" in result:
            pytest.skip("Backend not available")
    except:
        pytest.skip("Backend not running")
    return api


@pytest.fixture(scope="module")
def vast_api():
    """VAST.ai direct API client"""
    api = VastDirectAPI()
    if not api.api_key:
        pytest.skip("VAST.ai API key not configured")
    return api


@pytest.fixture(scope="module")
def test_instance(dumont_api, vast_api):
    """Get a running instance for testing"""
    instances = dumont_api.get_running_instances()
    if not instances:
        pytest.skip("No running instances available")

    # Prefer cheaper/faster GPUs for testing
    preferred = ["RTX A2000", "RTX A4000", "RTX 3060"]
    for pref in preferred:
        for inst in instances:
            if pref in inst.get("gpu_name", ""):
                return inst

    # Fall back to first instance
    return instances[0]


# =============================================================================
# TESTS
# =============================================================================

class TestServerlessModesOverview:
    """Overview dos modos disponíveis"""

    def test_list_available_modes(self, dumont_api):
        """Lista os modos serverless disponíveis"""
        print("\n" + "="*60)
        print("📋 MODOS SERVERLESS DISPONÍVEIS")
        print("="*60)

        modes = [
            {
                "mode": "FAST",
                "description": "CPU Standby (GCP)",
                "recovery": "<1s (teórico)",
                "idle_cost": "$0.01/hr",
                "requirements": "GCP credentials",
            },
            {
                "mode": "ECONOMIC",
                "description": "VAST.ai pause/resume",
                "recovery": "7-40s (varia por GPU)",
                "idle_cost": "~$0.005/hr",
                "requirements": "Nenhum",
            },
            {
                "mode": "SPOT",
                "description": "Instâncias spot + failover",
                "recovery": "~30s",
                "idle_cost": "$0 (destroy)",
                "requirements": "Template/snapshot",
            },
        ]

        print(f"\n{'Mode':<12} {'Recovery':<20} {'Idle Cost':<12} {'Requirements':<20}")
        print("-"*60)
        for m in modes:
            print(f"{m['mode']:<12} {m['recovery']:<20} {m['idle_cost']:<12} {m['requirements']:<20}")

        print("="*60)

    def test_list_running_instances(self, dumont_api):
        """Lista instâncias running disponíveis para teste"""
        instances = dumont_api.get_running_instances()

        print(f"\n📊 Instâncias Running: {len(instances)}")
        for inst in instances:
            print(f"   - {inst.get('id')}: {inst.get('gpu_name')} @ ${inst.get('dph_total', 0):.4f}/hr")


class TestEconomicMode:
    """Testes do modo ECONOMIC (VAST.ai pause/resume)"""

    @pytest.mark.benchmark
    def test_economic_full_cycle(self, dumont_api, vast_api, test_instance):
        """
        Teste completo do modo ECONOMIC:
        1. Habilita serverless mode=economic
        2. Força pause via idle
        3. Mede tempo de pause
        4. Faz wake/resume
        5. Mede cold start
        """
        instance_id = test_instance["id"]
        gpu_name = test_instance.get("gpu_name", "Unknown")

        print(f"\n🔬 ECONOMIC MODE TEST")
        print(f"   Instance: {instance_id} ({gpu_name})")
        print("="*60)

        result = ModeResult(
            mode="economic",
            instance_id=instance_id,
            gpu_name=gpu_name,
        )

        try:
            # Step 1: Enable serverless
            print("\n[1] Enabling serverless mode=economic...")
            start = time.time()
            resp = dumont_api.enable_serverless(instance_id, "economic", idle_timeout=15)
            result.enable_time = time.time() - start

            if "error" in resp:
                result.success = False
                result.error = resp["error"]
                print(f"   ❌ Error: {resp['error']}")
                return result

            print(f"   ✅ Enabled in {result.enable_time:.2f}s")

            # Step 2: Send idle heartbeats to trigger pause
            print("\n[2] Sending idle heartbeats...")
            for i in range(20):
                dumont_api.send_idle_heartbeat(instance_id)
                time.sleep(1)
                print(f"   Heartbeat {i+1}/20", end="\r")
            print()

            # Step 3: Force pause and measure
            print("\n[3] Forcing pause...")
            start = time.time()
            dumont_api.pause_instance(instance_id)
            success, elapsed = vast_api.wait_for_status(
                instance_id, ["stopped", "exited"], max_wait=60
            )
            result.pause_time = time.time() - start

            if success:
                print(f"   ✅ Paused in {result.pause_time:.2f}s")
            else:
                print(f"   ⚠️ Timeout after {result.pause_time:.2f}s")

            time.sleep(3)

            # Step 4: Resume and measure cold start
            print("\n[4] Resuming (cold start)...")
            start = time.time()
            dumont_api.resume_instance(instance_id)
            success, elapsed = vast_api.wait_for_status(
                instance_id, ["running"], max_wait=120
            )
            result.resume_time = time.time() - start

            if success:
                print(f"   ✅ Resumed in {result.resume_time:.2f}s (COLD START)")
            else:
                print(f"   ⚠️ Timeout after {result.resume_time:.2f}s")
                result.success = False

            result.total_cycle = result.pause_time + result.resume_time

        finally:
            # Cleanup
            print("\n[5] Disabling serverless...")
            dumont_api.disable_serverless(instance_id)

        # Summary
        print("\n" + "="*60)
        print(f"📊 ECONOMIC MODE RESULTS - {gpu_name}")
        print("="*60)
        print(f"   Enable time:    {result.enable_time:.2f}s")
        print(f"   Pause time:     {result.pause_time:.2f}s")
        print(f"   Resume time:    {result.resume_time:.2f}s ← COLD START")
        print(f"   Total cycle:    {result.total_cycle:.2f}s")
        print("="*60)

        return result


class TestFastMode:
    """Testes do modo FAST (CPU Standby)"""

    @pytest.mark.benchmark
    def test_fast_mode_enable(self, dumont_api, test_instance):
        """
        Teste do modo FAST:
        - Requer GCP configurado
        - Cria VM CPU standby
        - Recovery <1s teórico
        """
        instance_id = test_instance["id"]
        gpu_name = test_instance.get("gpu_name", "Unknown")

        print(f"\n🔬 FAST MODE TEST")
        print(f"   Instance: {instance_id} ({gpu_name})")
        print("="*60)

        result = ModeResult(
            mode="fast",
            instance_id=instance_id,
            gpu_name=gpu_name,
        )

        try:
            # Step 1: Try to enable fast mode
            print("\n[1] Enabling serverless mode=fast...")
            start = time.time()
            resp = dumont_api.enable_serverless(instance_id, "fast", idle_timeout=30)
            result.enable_time = time.time() - start

            if "error" in resp:
                if "GCP" in str(resp.get("error", "")) or "standby" in str(resp.get("error", "")):
                    print(f"   ⚠️ FAST mode requires GCP CPU Standby configured")
                    print(f"      Error: {resp.get('error', '')[:100]}")
                    pytest.skip("FAST mode requires GCP CPU Standby")
                result.success = False
                result.error = resp.get("error")
                print(f"   ❌ Error: {resp.get('error')}")
                return result

            print(f"   ✅ Enabled in {result.enable_time:.2f}s")

            # Check status
            status = dumont_api.get_serverless_status(instance_id)
            print(f"\n   Status: {json.dumps(status, indent=2)[:200]}")

            # FAST mode has near-instant recovery
            # We would need to actually have CPU standby configured to test
            print("\n   ℹ️ FAST mode uses CPU Standby for <1s recovery")
            print("   ℹ️ Full test requires GCP CPU Standby running")

        finally:
            dumont_api.disable_serverless(instance_id)

        return result


class TestSpotMode:
    """Testes do modo SPOT (instâncias interruptíveis)"""

    @pytest.mark.benchmark
    def test_spot_mode_enable(self, dumont_api, test_instance):
        """
        Teste do modo SPOT:
        - Usa instâncias spot/bid
        - Requer template (snapshot)
        - Failover automático quando interrompido
        """
        instance_id = test_instance["id"]
        gpu_name = test_instance.get("gpu_name", "Unknown")

        print(f"\n🔬 SPOT MODE TEST")
        print(f"   Instance: {instance_id} ({gpu_name})")
        print("="*60)

        result = ModeResult(
            mode="spot",
            instance_id=instance_id,
            gpu_name=gpu_name,
        )

        try:
            # Step 1: Try to enable spot mode
            print("\n[1] Enabling serverless mode=spot...")
            start = time.time()
            resp = dumont_api.enable_serverless(instance_id, "spot", idle_timeout=60)
            result.enable_time = time.time() - start

            if "error" in resp:
                if "template" in str(resp.get("error", "")).lower():
                    print(f"   ⚠️ SPOT mode requires a template (snapshot)")
                    pytest.skip("SPOT mode requires template")
                result.success = False
                result.error = resp.get("error")
                print(f"   ❌ Error: {resp.get('error')}")
                return result

            print(f"   ✅ Enabled in {result.enable_time:.2f}s")

            # Check status
            status = dumont_api.get_serverless_status(instance_id)
            print(f"\n   Status: {json.dumps(status, indent=2)[:200]}")

            print("\n   ℹ️ SPOT mode destroys instance when idle")
            print("   ℹ️ Recovery ~30s (find new GPU + restore snapshot)")
            print("   ℹ️ 60-70% cheaper than on-demand")

        finally:
            dumont_api.disable_serverless(instance_id)

        return result


class TestModeComparison:
    """Comparação direta entre modos"""

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_compare_all_modes(self, dumont_api, vast_api, test_instance):
        """
        Compara ECONOMIC vs FAST vs SPOT
        (onde disponível)
        """
        instance_id = test_instance["id"]
        gpu_name = test_instance.get("gpu_name", "Unknown")

        print("\n" + "="*70)
        print("🔬 SERVERLESS MODES COMPARISON")
        print(f"   Instance: {instance_id} ({gpu_name})")
        print("="*70)

        results = {}

        # Test ECONOMIC (sempre disponível)
        print("\n📍 Testing ECONOMIC mode...")
        try:
            dumont_api.enable_serverless(instance_id, "economic", idle_timeout=15)

            # Pause
            start = time.time()
            dumont_api.pause_instance(instance_id)
            success, _ = vast_api.wait_for_status(instance_id, ["stopped", "exited"], 60)
            pause_time = time.time() - start

            time.sleep(2)

            # Resume
            start = time.time()
            dumont_api.resume_instance(instance_id)
            success, _ = vast_api.wait_for_status(instance_id, ["running"], 120)
            resume_time = time.time() - start

            results["economic"] = {
                "pause": pause_time,
                "resume": resume_time,
                "total": pause_time + resume_time,
            }
            print(f"   ✅ Pause: {pause_time:.1f}s, Resume: {resume_time:.1f}s")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["economic"] = {"error": str(e)}
        finally:
            dumont_api.disable_serverless(instance_id)

        time.sleep(3)

        # Test FAST (requer GCP)
        print("\n📍 Testing FAST mode...")
        try:
            resp = dumont_api.enable_serverless(instance_id, "fast", idle_timeout=30)
            if "error" in resp:
                print(f"   ⚠️ Not available: {str(resp.get('error', ''))[:50]}")
                results["fast"] = {"error": "Requires GCP CPU Standby"}
            else:
                # FAST mode - recovery would be <1s if properly configured
                results["fast"] = {
                    "pause": "N/A (suspend)",
                    "resume": "<1s (teórico)",
                    "total": "<1s (teórico)",
                }
                print(f"   ✅ Enabled (recovery <1s when properly configured)")
        except Exception as e:
            results["fast"] = {"error": str(e)}
        finally:
            dumont_api.disable_serverless(instance_id)

        # Test SPOT (requer template)
        print("\n📍 Testing SPOT mode...")
        try:
            resp = dumont_api.enable_serverless(instance_id, "spot", idle_timeout=60)
            if "error" in resp:
                print(f"   ⚠️ Not available: {str(resp.get('error', ''))[:50]}")
                results["spot"] = {"error": "Requires template/snapshot"}
            else:
                results["spot"] = {
                    "pause": "N/A (destroy)",
                    "resume": "~30s (teórico)",
                    "total": "~30s (teórico)",
                }
                print(f"   ✅ Enabled (recovery ~30s, 60-70% cheaper)")
        except Exception as e:
            results["spot"] = {"error": str(e)}
        finally:
            dumont_api.disable_serverless(instance_id)

        # Summary
        print("\n" + "="*70)
        print("📊 COMPARISON RESULTS")
        print("="*70)
        print(f"GPU: {gpu_name}")
        print(f"\n{'Mode':<12} {'Pause':<12} {'Resume':<12} {'Total':<12} {'Status':<15}")
        print("-"*70)

        for mode, data in results.items():
            if "error" in data:
                print(f"{mode.upper():<12} {'N/A':<12} {'N/A':<12} {'N/A':<12} {data['error'][:15]:<15}")
            else:
                pause = f"{data['pause']:.1f}s" if isinstance(data['pause'], float) else data['pause']
                resume = f"{data['resume']:.1f}s" if isinstance(data['resume'], float) else data['resume']
                total = f"{data['total']:.1f}s" if isinstance(data['total'], float) else data['total']
                print(f"{mode.upper():<12} {pause:<12} {resume:<12} {total:<12} {'✅ Available':<15}")

        print("="*70)

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if "economic" in results and "error" not in results["economic"]:
            eco = results["economic"]
            if eco["resume"] < 15:
                print(f"   ✅ ECONOMIC works well for this GPU ({eco['resume']:.1f}s cold start)")
            else:
                print(f"   ⚠️ ECONOMIC is slow for this GPU ({eco['resume']:.1f}s)")
                print("      Consider FAST mode for faster recovery")

        print("\n")

        return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
