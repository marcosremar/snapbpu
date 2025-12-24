"""
Testes Concorrentes de GPU - Dumont Cloud

IMPORTANTE: Este arquivo é projetado para rodar em PARALELO!
Use: pytest tests/test_concurrent_gpu.py -n 10 --dist=loadscope

Testa:
- Criação simultânea de múltiplas instâncias
- Operações paralelas em instâncias diferentes
- Race conditions
- Stress test de API

Uses api_client fixture from conftest.py
"""
import pytest
import time
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional


# ============================================================
# Configuration
# ============================================================

MAX_CONCURRENT_INSTANCES = 5
API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
TEST_USER = os.environ.get("TEST_USER", "test@test.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")


# ============================================================
# Helpers
# ============================================================

@dataclass
class InstanceResult:
    """Resultado de criação de instância"""
    offer_id: int
    instance_id: Optional[int] = None
    success: bool = False
    error: Optional[str] = None
    time_seconds: float = 0


# ============================================================
# Testes de Operações Paralelas (Sem GPU Real)
# ============================================================

class TestParallelOperations:
    """Testes de operações paralelas em instâncias"""

    
    def test_parallel_offer_searches(self, api_client):
        """Busca ofertas em paralelo com diferentes filtros"""
        searches = [
            {"max_price": 0.5, "limit": 10},
            {"max_price": 1.0, "limit": 20},
            {"max_price": 2.0, "gpu_name": "RTX_4090"},
            {"max_price": 5.0, "num_gpus": 2},
            {"machine_type": "on-demand", "limit": 30},
        ]

        print(f"\n🔍 Executando {len(searches)} buscas em paralelo...")

        def search_offers(params):
            query = "&".join(f"{k}={v}" for k, v in params.items())
            return api_client.call("GET", f"/api/v1/instances/offers?{query}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(search_offers, s): s for s in searches}
            results = []
            for future in as_completed(futures):
                params = futures[future]
                result = future.result()
                count = len(result.get("offers", [])) if result else 0
                results.append(count)
                print(f"   • {params}: {count} ofertas")

        assert len(results) == len(searches)

    
    def test_parallel_status_checks(self, api_client):
        """Verifica status de múltiplos endpoints em paralelo"""
        endpoints = [
            "/api/v1/instances",
            "/api/v1/warmpool/hosts",
            "/api/v1/failover/strategies",
            "/api/v1/standby/status",
            "/api/v1/balance",
        ]

        print(f"\n🔍 Verificando {len(endpoints)} endpoints em paralelo...")

        def check_endpoint(endpoint):
            start = time.time()
            result = api_client.call("GET", endpoint)
            elapsed = time.time() - start
            return endpoint, result is not None, elapsed

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_endpoint, ep) for ep in endpoints]
            for future in as_completed(futures):
                endpoint, success, elapsed = future.result()
                status = "✅" if success else "❌"
                print(f"   {status} {endpoint}: {elapsed:.2f}s")


# ============================================================
# Testes de Race Conditions
# ============================================================

class TestRaceConditions:
    """Testes de race conditions"""

    
    def test_simultaneous_login_same_user(self, api_client):
        """Testa login simultâneo do mesmo usuário"""
        print("\n🔐 Testando login simultâneo...")

        def do_login():
            try:
                response = requests.post(f"{API_BASE_URL}/api/v1/auth/login", json={
                    "email": TEST_USER,
                    "password": TEST_PASSWORD
                }, timeout=30)
                return response.status_code == 200
            except:
                return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(do_login) for _ in range(5)]
            results = [f.result() for f in as_completed(futures)]

        success_count = sum(1 for r in results if r)
        print(f"   Logins bem-sucedidos: {success_count}/5")
        assert success_count >= 3


# ============================================================
# Testes de Stress
# ============================================================

class TestAPIStress:
    """Testes de stress da API"""

    
    def test_burst_requests(self, api_client):
        """Testa burst de requisições"""
        num_requests = 20

        print(f"\n⚡ Enviando burst de {num_requests} requisições...")

        def quick_request(i):
            start = time.time()
            result = api_client.call("GET", "/api/v1/instances/offers?limit=1")
            return time.time() - start, result is not None

        start_total = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(quick_request, i) for i in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_total
        success_count = sum(1 for _, success in results if success)
        avg_time = sum(t for t, _ in results) / len(results)

        print(f"   Tempo total: {total_time:.2f}s")
        print(f"   Tempo médio/req: {avg_time:.3f}s")
        print(f"   Sucessos: {success_count}/{num_requests}")
        print(f"   Throughput: {num_requests/total_time:.1f} req/s")

        assert success_count >= num_requests * 0.8

    
    
    def test_sustained_load(self, api_client):
        """Testa carga sustentada por 30 segundos"""
        duration = 30
        requests_made = 0
        errors = 0

        print(f"\n📈 Testando carga sustentada por {duration}s...")

        start = time.time()
        while time.time() - start < duration:
            result = api_client.call("GET", "/api/v1/instances?limit=5")
            requests_made += 1
            if not result or "error" in str(result):
                errors += 1
            time.sleep(0.5)

        elapsed = time.time() - start
        success_rate = (requests_made - errors) / requests_made

        print(f"   Requisições: {requests_made}")
        print(f"   Erros: {errors}")
        print(f"   Taxa de sucesso: {success_rate:.1%}")
        print(f"   Throughput: {requests_made/elapsed:.1f} req/s")

        assert success_rate >= 0.9


# ============================================================
# Testes de Cleanup
# ============================================================

class TestParallelCleanup:
    """Testes de cleanup paralelo"""

    
    def test_list_and_identify_orphan_instances(self, api_client):
        """Lista instâncias e identifica órfãs de testes anteriores"""
        result = api_client.call("GET", "/api/v1/instances")

        if not result or not result.get("instances"):
            print("\n📋 Nenhuma instância ativa")
            return

        instances = result["instances"]
        print(f"\n📋 {len(instances)} instâncias ativas:")

        test_instances = []
        for inst in instances:
            label = inst.get("label", "")
            status = inst.get("status", "unknown")
            gpu = inst.get("gpu_name", "N/A")
            iid = inst.get("id")

            is_test = (label and "test" in label.lower()) or not label
            marker = "🧪" if is_test else "📦"
            print(f"   {marker} {iid}: {gpu} ({status}) - {label or 'sem label'}")

            if is_test:
                test_instances.append(iid)

        if test_instances:
            print(f"\n⚠️ {len(test_instances)} instâncias parecem ser de testes")
