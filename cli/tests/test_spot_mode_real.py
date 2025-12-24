"""
Teste REAL do modo SPOT com VAST.ai

Este teste mede tempos REAIS de:
1. Busca de ofertas interruptíveis (spot)
2. Comparação com modo ECONOMIC (pause/resume)
3. Simulação de failover

USA CRÉDITOS REAIS da VAST.ai!
"""
import pytest
import time
import json
import requests
from datetime import datetime
from pathlib import Path

# Resultados do teste
RESULTS_FILE = Path(__file__).parent / "mode_spot_results.json"


class TestSpotModeReal:
    """Testes REAIS do modo SPOT"""

    VAST_API_KEY = "a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd"
    VAST_API_URL = "https://console.vast.ai/api/v0"

    @pytest.fixture
    def vast_headers(self):
        return {"Authorization": f"Bearer {self.VAST_API_KEY}"}

    @pytest.fixture
    def running_instance(self, vast_headers) -> dict:
        """Busca uma instância running para usar nos testes"""
        resp = requests.get(
            f"{self.VAST_API_URL}/instances/",
            headers=vast_headers,
            timeout=30
        )
        assert resp.status_code == 200

        instances = resp.json().get("instances", [])
        running = [i for i in instances if i.get("actual_status") == "running"]

        if not running:
            pytest.skip("No running instances for spot testing")

        # Pegar uma instância barata para testar
        return min(running, key=lambda x: x.get("dph_total", 999))

    def _get_spot_offers(self, vast_headers, max_price=1.0):
        """Busca ofertas spot usando API direta"""
        # Query para ofertas interruptíveis
        query = {
            "type": "bid",  # Apenas ofertas que aceitam bid
            "min_bid": {"lte": max_price},
            "inet_down": {"gte": 50},
            "disk_space": {"gte": 10},
        }

        resp = requests.get(
            f"{self.VAST_API_URL}/bundles/",
            params={
                "q": json.dumps(query),
                "order": "min_bid",
                "type": "bid",
            },
            headers=vast_headers,
            timeout=30
        )

        if resp.status_code == 200:
            return resp.json().get("offers", [])
        return []

    def test_list_interruptible_offers(self, vast_headers):
        """
        Testa busca de ofertas spot (interruptíveis).
        """
        start = time.time()

        offers = self._get_spot_offers(vast_headers)

        elapsed = time.time() - start

        print(f"\n=== SPOT OFFERS ===")
        print(f"Found {len(offers)} interruptible offers in {elapsed:.2f}s")

        for o in offers[:5]:
            gpu = o.get("gpu_name", "Unknown")
            min_bid = o.get("min_bid", 0)
            dph = o.get("dph_total", 0)
            geo = o.get("geolocation", "??")
            print(f"  {gpu}: ${min_bid:.4f}/hr (on-demand: ${dph:.4f}) - {geo}")

        assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s"

        if offers:
            for o in offers[:3]:
                min_bid = o.get("min_bid", 0)
                dph = o.get("dph_total", 0)
                if min_bid and dph:
                    savings = (1 - min_bid/dph) * 100
                    print(f"    Savings: {savings:.1f}%")

    def test_calculate_spot_savings(self, vast_headers):
        """
        Calcula economia REAL do modo spot vs on-demand.
        """
        offers = self._get_spot_offers(vast_headers, max_price=2.0)

        if not offers:
            pytest.skip("No spot offers to calculate savings")

        # Calcular economia média
        savings_list = []
        for o in offers:
            min_bid = o.get("min_bid", 0)
            dph = o.get("dph_total", 0)
            if min_bid > 0 and dph > 0:
                savings = (1 - min_bid/dph) * 100
                savings_list.append(savings)

        if savings_list:
            avg_savings = sum(savings_list) / len(savings_list)
            max_savings = max(savings_list)
            min_savings = min(savings_list)

            print(f"\n=== SPOT SAVINGS ===")
            print(f"Offers analyzed: {len(savings_list)}")
            print(f"Average: {avg_savings:.1f}%")
            print(f"Maximum: {max_savings:.1f}%")
            print(f"Minimum: {min_savings:.1f}%")

            assert avg_savings >= 0, "Expected some savings from spot"

    def test_spot_interruption_detection(self, vast_headers, running_instance):
        """
        Testa detecção de interrupção em instância spot.
        """
        instance_id = running_instance.get("id")
        actual_status = running_instance.get("actual_status")
        intended_status = running_instance.get("intended_status", running_instance.get("status"))

        print(f"\n=== INTERRUPTION DETECTION ===")
        print(f"Instance: {instance_id}")
        print(f"Actual: {actual_status}")
        print(f"Intended: {intended_status}")

        # Lógica de detecção de interrupção
        is_interrupted = (
            actual_status in ["exited", "offline", "stopped", "error"] and
            intended_status == "running"
        )

        print(f"Would detect as interrupted: {is_interrupted}")
        assert instance_id is not None

    def test_spot_failover_simulation(self, vast_headers, running_instance):
        """
        Simula fluxo de failover:

        1. Detecta "interrupção" (simula)
        2. Busca nova GPU na mesma região
        3. Mede tempo de busca
        """
        instance_id = running_instance.get("id")
        gpu_name = running_instance.get("gpu_name", "Unknown")
        geolocation = running_instance.get("geolocation", "global")

        print(f"\n=== FAILOVER SIMULATION ===")
        print(f"Original instance: {instance_id}")
        print(f"GPU: {gpu_name}")
        print(f"Region: {geolocation}")

        # Buscar nova GPU (simula failover search)
        search_start = time.time()

        offers = self._get_spot_offers(vast_headers, max_price=1.0)

        search_elapsed = time.time() - search_start

        print(f"Search took: {search_elapsed:.2f}s")
        print(f"Found {len(offers)} replacement offers")

        if offers:
            best = offers[0]
            print(f"Best replacement: {best.get('gpu_name')} at ${best.get('min_bid', 0):.4f}/hr")

            # Tempo estimado de failover completo
            estimated_failover = 10 + search_elapsed + 30 + 30  # detect + search + deploy + restore
            print(f"Estimated total failover time: {estimated_failover:.0f}s")

    def test_measure_spot_vs_economic_recovery(self, vast_headers, running_instance):
        """
        Compara tempo de recovery SPOT vs ECONOMIC.

        - ECONOMIC: pause/resume na mesma instância (REAL)
        - SPOT: busca + deploy + restore (búsqueda real + estimativas)
        """
        instance_id = running_instance.get("id")
        gpu_name = running_instance.get("gpu_name")

        print(f"\n=== SPOT vs ECONOMIC RECOVERY ===")
        print(f"Testing on: {instance_id} ({gpu_name})")

        # 1. Medir ECONOMIC (pause/resume)
        print("\n--- ECONOMIC MODE (pause/resume) ---")

        # Pause
        pause_start = time.time()
        resp = requests.put(
            f"{self.VAST_API_URL}/instances/{instance_id}/",
            json={"state": "stopped"},
            headers=vast_headers,
            timeout=60
        )

        if resp.status_code != 200:
            print(f"Pause failed: {resp.text}")
            economic_pause = None
        else:
            # Aguardar pausa completar
            for _ in range(60):
                time.sleep(1)
                check = requests.get(
                    f"{self.VAST_API_URL}/instances/",
                    headers=vast_headers,
                    timeout=30
                )
                if check.status_code == 200:
                    instances = check.json().get("instances", [])
                    inst = next((i for i in instances if i.get("id") == instance_id), None)
                    if inst:
                        status = inst.get("actual_status")
                        if status in ["stopped", "exited", "offline"]:
                            break

            economic_pause = time.time() - pause_start
            print(f"Pause time: {economic_pause:.2f}s")

        # Resume
        resume_start = time.time()
        resp = requests.put(
            f"{self.VAST_API_URL}/instances/{instance_id}/",
            json={"state": "running"},
            headers=vast_headers,
            timeout=60
        )

        if resp.status_code != 200:
            print(f"Resume failed: {resp.text}")
            economic_resume = None
        else:
            # Aguardar resume completar
            for _ in range(90):
                time.sleep(1)
                check = requests.get(
                    f"{self.VAST_API_URL}/instances/",
                    headers=vast_headers,
                    timeout=30
                )
                if check.status_code == 200:
                    instances = check.json().get("instances", [])
                    inst = next((i for i in instances if i.get("id") == instance_id), None)
                    if inst:
                        status = inst.get("actual_status")
                        if status == "running":
                            break

            economic_resume = time.time() - resume_start
            print(f"Resume time: {economic_resume:.2f}s")

        # 2. Medir SPOT search (parte real) + estimar resto
        print("\n--- SPOT MODE (search real, rest estimated) ---")

        search_start = time.time()
        offers = self._get_spot_offers(vast_headers, max_price=1.0)
        spot_search = time.time() - search_start

        # Componentes do tempo de SPOT failover
        spot_detection = 10   # Polling interval
        spot_deploy = 30      # Tempo estimado para deploy
        spot_restore = 30     # Tempo estimado para restore snapshot

        spot_total_estimated = spot_detection + spot_search + spot_deploy + spot_restore

        print(f"Search time (real): {spot_search:.2f}s")
        print(f"Detection interval: {spot_detection}s")
        print(f"Deploy (estimated): {spot_deploy}s")
        print(f"Restore (estimated): {spot_restore}s")
        print(f"Total estimated: {spot_total_estimated:.0f}s")

        # Salvar resultados
        results = {
            "mode": "spot_vs_economic",
            "instance_id": instance_id,
            "gpu_name": gpu_name,
            "economic": {
                "pause_seconds": economic_pause,
                "resume_seconds": economic_resume,
                "total_seconds": (economic_pause or 0) + (economic_resume or 0),
            },
            "spot": {
                "search_seconds": spot_search,
                "detection_seconds": spot_detection,
                "deploy_estimated_seconds": spot_deploy,
                "restore_estimated_seconds": spot_restore,
                "total_estimated_seconds": spot_total_estimated,
            },
            "offers_available": len(offers),
            "timestamp": datetime.now().isoformat(),
        }

        with open(RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {RESULTS_FILE}")

        print(f"\n=== SUMMARY ===")
        economic_total = results['economic']['total_seconds']
        print(f"ECONOMIC recovery: {economic_total:.0f}s (REAL)")
        print(f"SPOT recovery: {spot_total_estimated:.0f}s (estimated)")

        if economic_total < spot_total_estimated:
            print(f"Advantage: ECONOMIC is ~{spot_total_estimated - economic_total:.0f}s faster")
        else:
            print(f"Advantage: SPOT is ~{economic_total - spot_total_estimated:.0f}s faster")


class TestSpotPricing:
    """Testes de preços spot"""

    VAST_API_KEY = "a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd"
    VAST_API_URL = "https://console.vast.ai/api/v0"

    @pytest.fixture
    def vast_headers(self):
        return {"Authorization": f"Bearer {self.VAST_API_KEY}"}

    def _get_spot_offers(self, vast_headers, max_price=5.0):
        """Busca ofertas spot usando API direta"""
        query = {
            "type": "bid",
            "min_bid": {"lte": max_price},
            "inet_down": {"gte": 50},
        }

        resp = requests.get(
            f"{self.VAST_API_URL}/bundles/",
            params={
                "q": json.dumps(query),
                "order": "min_bid",
                "type": "bid",
            },
            headers=vast_headers,
            timeout=30
        )

        if resp.status_code == 200:
            return resp.json().get("offers", [])
        return []

    def test_spot_pricing_by_gpu(self, vast_headers):
        """
        Analisa preços spot por tipo de GPU.
        """
        offers = self._get_spot_offers(vast_headers)

        if not offers:
            pytest.skip("No spot offers available")

        # Agrupar por GPU
        gpu_prices = {}
        for o in offers:
            gpu = o.get("gpu_name")
            if not gpu:
                continue
            if gpu not in gpu_prices:
                gpu_prices[gpu] = []
            min_bid = o.get("min_bid")
            if min_bid:
                gpu_prices[gpu].append(min_bid)

        print(f"\n=== SPOT PRICING BY GPU ===")
        for gpu, prices in sorted(gpu_prices.items(), key=lambda x: min(x[1]) if x[1] else 999):
            if prices:
                avg = sum(prices) / len(prices)
                mn = min(prices)
                print(f"{gpu}: ${mn:.4f}/hr (avg: ${avg:.4f}, {len(prices)} offers)")

    def test_spot_vs_ondemand_comparison(self, vast_headers):
        """
        Compara preços spot vs on-demand.
        """
        offers = self._get_spot_offers(vast_headers)

        if not offers:
            pytest.skip("No spot offers available")

        print(f"\n=== SPOT vs ON-DEMAND ===")
        print(f"{'GPU':<20} {'Spot':<12} {'On-demand':<12} {'Savings':<10}")
        print("-" * 55)

        seen = set()
        for o in offers[:20]:
            gpu_name = o.get("gpu_name")
            if not gpu_name or gpu_name in seen:
                continue
            seen.add(gpu_name)

            min_bid = o.get("min_bid", 0)
            dph = o.get("dph_total", 0)

            if min_bid and dph:
                savings = (1 - min_bid/dph) * 100
                print(f"{gpu_name:<20} ${min_bid:<10.4f} ${dph:<10.4f} {savings:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
