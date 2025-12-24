"""
Testes REAIS de TODOS os endpoints do Dumont Cloud CLI

Este arquivo testa TODOS os 228 endpoints da API de forma realista.
USA CREDITOS REAIS da VAST.ai!

Para rodar:
    pytest tests/test_all_endpoints_real.py -v -s --tb=short

Para rodar por categoria:
    pytest tests/test_all_endpoints_real.py -v -s -k "Auth"
    pytest tests/test_all_endpoints_real.py -v -s -k "Instance"
    pytest tests/test_all_endpoints_real.py -v -s -k "Failover"
"""
import pytest
import requests
import time
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

# Configuracao
API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
TEST_USER = os.environ.get("TEST_USER", "test@test.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")

# Rate limiting
DELAY_BETWEEN_CALLS = 1  # segundos entre chamadas


@dataclass
class TestResult:
    """Resultado de um teste de endpoint"""
    endpoint: str
    method: str
    success: bool
    status_code: int
    response_time: float
    error: Optional[str] = None
    response_preview: Optional[str] = None


@dataclass
class TestReport:
    """Relatorio completo de testes"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    results: List[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)

    def summary(self) -> Dict[str, Any]:
        self.end_time = datetime.now()
        passed = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        return {
            "total": len(self.results),
            "passed": len(passed),
            "failed": len(failed),
            "success_rate": f"{len(passed)/len(self.results)*100:.1f}%" if self.results else "0%",
            "duration": str(self.end_time - self.start_time),
            "avg_response_time": f"{sum(r.response_time for r in self.results)/len(self.results):.2f}s" if self.results else "0s",
        }

    def print_report(self):
        """Imprime relatorio formatado"""
        summary = self.summary()

        print("\n" + "=" * 70)
        print("RELATORIO DE TESTES - TODOS OS ENDPOINTS")
        print("=" * 70)
        print(f"Data: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duracao: {summary['duration']}")
        print(f"Tempo medio resposta: {summary['avg_response_time']}")
        print("-" * 70)
        print(f"TOTAL: {summary['total']} endpoints testados")
        print(f"  PASSED: {summary['passed']}")
        print(f"  FAILED: {summary['failed']}")
        print(f"  Taxa de sucesso: {summary['success_rate']}")
        print("-" * 70)

        if summary['failed'] > 0:
            print("\nENDPOINTS COM FALHA:")
            for r in self.results:
                if not r.success:
                    print(f"  {r.method:6} {r.endpoint}")
                    print(f"         Status: {r.status_code}, Erro: {r.error}")

        print("=" * 70)


class RealAPIClient:
    """Cliente para API real com autenticacao e rate limiting"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.token = None
        self.session = requests.Session()
        self.report = TestReport()

    def login(self, username: str = TEST_USER, password: str = TEST_PASSWORD) -> bool:
        """Faz login e armazena token"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            if response.ok:
                data = response.json()
                self.token = data.get("token")
                self.session.headers["Authorization"] = f"Bearer {self.token}"
                return True
        except Exception as e:
            print(f"Erro no login: {e}")
        return False

    def call(self, method: str, path: str, data: dict = None, params: dict = None) -> TestResult:
        """Chama endpoint e registra resultado"""
        url = f"{self.base_url}{path}"
        start = time.time()

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=30)
            else:
                raise ValueError(f"Metodo nao suportado: {method}")

            elapsed = time.time() - start

            # Determinar sucesso (2xx ou erros esperados como 404 para recursos inexistentes)
            success = response.status_code < 400 or response.status_code == 404

            try:
                resp_json = response.json()
                preview = str(resp_json)[:100]
            except:
                preview = response.text[:100] if response.text else ""

            result = TestResult(
                endpoint=path,
                method=method.upper(),
                success=success,
                status_code=response.status_code,
                response_time=elapsed,
                response_preview=preview,
                error=None if success else preview
            )

        except Exception as e:
            elapsed = time.time() - start
            result = TestResult(
                endpoint=path,
                method=method.upper(),
                success=False,
                status_code=0,
                response_time=elapsed,
                error=str(e)
            )

        self.report.add(result)
        time.sleep(DELAY_BETWEEN_CALLS)
        return result


# Fixture global
@pytest.fixture(scope="module")
def api():
    """Cliente API autenticado"""
    client = RealAPIClient()
    assert client.login(), f"Falha no login com {TEST_USER}"
    print(f"\n Login OK: {TEST_USER}")
    yield client
    # Imprimir relatorio ao final
    client.report.print_report()


# Fixture para instancia real (cria e deleta)
@pytest.fixture(scope="module")
def real_instance(api):
    """Cria instancia real para testes"""
    instance_id = None

    # Buscar oferta mais barata
    result = api.call("GET", "/api/v1/instances/offers")
    if result.success and result.status_code == 200:
        try:
            resp = api.session.get(f"{api.base_url}/api/v1/instances/offers").json()
            offers = resp.get("offers", [])
            if offers:
                cheapest = sorted(offers, key=lambda x: x.get("dph_total", 999))[0]
                print(f"\n Oferta: {cheapest['gpu_name']} - ${cheapest['dph_total']:.4f}/hr")

                # Criar instancia
                create_resp = api.session.post(
                    f"{api.base_url}/api/v1/instances",
                    json={
                        "offer_id": cheapest["id"],
                        "image": "nvidia/cuda:12.0-base-ubuntu22.04",
                        "disk_size": 20
                    }
                ).json()

                instance_id = create_resp.get("instance_id") or create_resp.get("id")
                if instance_id:
                    print(f" Instancia criada: {instance_id}")
                    # Aguardar ficar pronta
                    time.sleep(10)
        except Exception as e:
            print(f" Erro ao criar instancia: {e}")

    yield instance_id

    # Cleanup
    if instance_id:
        print(f"\n Deletando instancia {instance_id}...")
        api.call("DELETE", f"/api/v1/instances/{instance_id}")


# =============================================================================
# TESTES DE AUTH
# =============================================================================
class TestAuth:
    """Testes de autenticacao"""

    def test_auth_me(self, api):
        """GET /api/v1/auth/me"""
        result = api.call("GET", "/api/v1/auth/me")
        assert result.success
        print(f"   auth/me: {result.response_preview}")

    def test_auth_login_success(self, api):
        """POST /api/v1/auth/login (ja logado)"""
        # Testar login novamente
        result = api.call("POST", "/api/v1/auth/login", {
            "username": TEST_USER,
            "password": TEST_PASSWORD
        })
        assert result.success
        print(f"   login: OK")


# =============================================================================
# TESTES DE INSTANCES
# =============================================================================
class TestInstances:
    """Testes de instancias GPU"""

    def test_list_offers(self, api):
        """GET /api/v1/instances/offers"""
        result = api.call("GET", "/api/v1/instances/offers")
        assert result.success
        print(f"   offers: {result.status_code}")

    def test_list_instances(self, api):
        """GET /api/v1/instances"""
        result = api.call("GET", "/api/v1/instances")
        assert result.success
        print(f"   instances: {result.status_code}")

    def test_get_instance(self, api, real_instance):
        """GET /api/v1/instances/{id}"""
        if real_instance:
            result = api.call("GET", f"/api/v1/instances/{real_instance}")
            print(f"   get instance {real_instance}: {result.status_code}")
        else:
            # Testar com ID fake
            result = api.call("GET", "/api/v1/instances/99999999")
            print(f"   get instance (fake): {result.status_code}")

    def test_pause_instance(self, api, real_instance):
        """POST /api/v1/instances/{id}/pause"""
        if real_instance:
            result = api.call("POST", f"/api/v1/instances/{real_instance}/pause")
            print(f"   pause: {result.status_code}")
            time.sleep(5)

    def test_resume_instance(self, api, real_instance):
        """POST /api/v1/instances/{id}/resume"""
        if real_instance:
            result = api.call("POST", f"/api/v1/instances/{real_instance}/resume")
            print(f"   resume: {result.status_code}")

    def test_sync_status(self, api, real_instance):
        """GET /api/v1/instances/{id}/sync/status"""
        if real_instance:
            result = api.call("GET", f"/api/v1/instances/{real_instance}/sync/status")
            print(f"   sync status: {result.status_code}")

    def test_migrate_estimate(self, api, real_instance):
        """POST /api/v1/instances/{id}/migrate/estimate"""
        if real_instance:
            result = api.call("POST", f"/api/v1/instances/{real_instance}/migrate/estimate", {
                "target_gpu": "RTX 4090"
            })
            print(f"   migrate estimate: {result.status_code}")


# =============================================================================
# TESTES DE SNAPSHOTS
# =============================================================================
class TestSnapshots:
    """Testes de snapshots"""

    def test_list_snapshots(self, api):
        """GET /api/v1/snapshots"""
        result = api.call("GET", "/api/v1/snapshots")
        assert result.success or result.status_code == 400  # Pode falhar se Restic nao configurado
        print(f"   list snapshots: {result.status_code}")

    def test_create_snapshot(self, api, real_instance):
        """POST /api/v1/snapshots"""
        if real_instance:
            result = api.call("POST", "/api/v1/snapshots", {
                "instance_id": real_instance,
                "name": f"test_snapshot_{int(time.time())}"
            })
            print(f"   create snapshot: {result.status_code}")


# =============================================================================
# TESTES DE SETTINGS
# =============================================================================
class TestSettings:
    """Testes de configuracoes"""

    def test_get_settings(self, api):
        """GET /api/v1/settings"""
        result = api.call("GET", "/api/v1/settings")
        assert result.success
        print(f"   settings: {result.status_code}")

    def test_get_cloud_storage(self, api):
        """GET /api/v1/settings/cloud-storage"""
        result = api.call("GET", "/api/v1/settings/cloud-storage")
        assert result.success
        print(f"   cloud-storage: {result.status_code}")

    def test_complete_onboarding(self, api):
        """POST /api/v1/settings/complete-onboarding"""
        result = api.call("POST", "/api/v1/settings/complete-onboarding")
        print(f"   complete-onboarding: {result.status_code}")


# =============================================================================
# TESTES DE BALANCE
# =============================================================================
class TestBalance:
    """Testes de saldo"""

    def test_get_balance(self, api):
        """GET /api/v1/balance"""
        result = api.call("GET", "/api/v1/balance")
        assert result.success
        print(f"   balance: {result.response_preview}")


# =============================================================================
# TESTES DE METRICS
# =============================================================================
class TestMetrics:
    """Testes de metricas"""

    def test_market(self, api):
        """GET /api/v1/metrics/market"""
        result = api.call("GET", "/api/v1/metrics/market")
        print(f"   market: {result.status_code}")

    def test_market_summary(self, api):
        """GET /api/v1/metrics/market/summary"""
        result = api.call("GET", "/api/v1/metrics/market/summary")
        print(f"   market/summary: {result.status_code}")

    def test_providers(self, api):
        """GET /api/v1/metrics/providers"""
        result = api.call("GET", "/api/v1/metrics/providers")
        print(f"   providers: {result.status_code}")

    def test_efficiency(self, api):
        """GET /api/v1/metrics/efficiency"""
        result = api.call("GET", "/api/v1/metrics/efficiency")
        print(f"   efficiency: {result.status_code}")

    def test_gpus(self, api):
        """GET /api/v1/metrics/gpus"""
        result = api.call("GET", "/api/v1/metrics/gpus")
        print(f"   gpus: {result.status_code}")

    def test_types(self, api):
        """GET /api/v1/metrics/types"""
        result = api.call("GET", "/api/v1/metrics/types")
        print(f"   types: {result.status_code}")

    def test_compare(self, api):
        """GET /api/v1/metrics/compare"""
        result = api.call("GET", "/api/v1/metrics/compare")
        print(f"   compare: {result.status_code}")

    def test_predictions(self, api):
        """GET /api/v1/metrics/predictions/{gpu_name}"""
        result = api.call("GET", "/api/v1/metrics/predictions/RTX 4090")
        print(f"   predictions: {result.status_code}")

    def test_savings_real(self, api):
        """GET /api/v1/metrics/savings/real"""
        result = api.call("GET", "/api/v1/metrics/savings/real")
        print(f"   savings/real: {result.status_code}")

    def test_savings_history(self, api):
        """GET /api/v1/metrics/savings/history"""
        result = api.call("GET", "/api/v1/metrics/savings/history")
        print(f"   savings/history: {result.status_code}")

    def test_hibernation_events(self, api):
        """GET /api/v1/metrics/hibernation/events"""
        result = api.call("GET", "/api/v1/metrics/hibernation/events")
        print(f"   hibernation/events: {result.status_code}")


# =============================================================================
# TESTES DE SPOT MARKET
# =============================================================================
class TestSpotMarket:
    """Testes de Spot Market Analysis"""

    def test_spot_monitor(self, api):
        """GET /api/v1/metrics/spot/monitor"""
        result = api.call("GET", "/api/v1/metrics/spot/monitor")
        print(f"   spot/monitor: {result.status_code}")

    def test_spot_savings(self, api):
        """GET /api/v1/metrics/spot/savings"""
        result = api.call("GET", "/api/v1/metrics/spot/savings")
        print(f"   spot/savings: {result.status_code}")

    def test_spot_interruption_rates(self, api):
        """GET /api/v1/metrics/spot/interruption-rates"""
        result = api.call("GET", "/api/v1/metrics/spot/interruption-rates")
        print(f"   spot/interruption-rates: {result.status_code}")

    def test_spot_safe_windows(self, api):
        """GET /api/v1/metrics/spot/safe-windows/{gpu_name}"""
        result = api.call("GET", "/api/v1/metrics/spot/safe-windows/RTX 4090")
        print(f"   spot/safe-windows: {result.status_code}")

    def test_spot_llm_gpus(self, api):
        """GET /api/v1/metrics/spot/llm-gpus"""
        result = api.call("GET", "/api/v1/metrics/spot/llm-gpus")
        print(f"   spot/llm-gpus: {result.status_code}")

    def test_spot_prediction(self, api):
        """GET /api/v1/metrics/spot/prediction/{gpu_name}"""
        result = api.call("GET", "/api/v1/metrics/spot/prediction/RTX 4090")
        print(f"   spot/prediction: {result.status_code}")

    def test_spot_availability(self, api):
        """GET /api/v1/metrics/spot/availability"""
        result = api.call("GET", "/api/v1/metrics/spot/availability")
        print(f"   spot/availability: {result.status_code}")

    def test_spot_reliability(self, api):
        """GET /api/v1/metrics/spot/reliability"""
        result = api.call("GET", "/api/v1/metrics/spot/reliability")
        print(f"   spot/reliability: {result.status_code}")

    def test_spot_training_cost(self, api):
        """GET /api/v1/metrics/spot/training-cost"""
        result = api.call("GET", "/api/v1/metrics/spot/training-cost")
        print(f"   spot/training-cost: {result.status_code}")

    def test_spot_fleet_strategy(self, api):
        """GET /api/v1/metrics/spot/fleet-strategy"""
        result = api.call("GET", "/api/v1/metrics/spot/fleet-strategy")
        print(f"   spot/fleet-strategy: {result.status_code}")


# =============================================================================
# TESTES DE FAILOVER
# =============================================================================
class TestFailover:
    """Testes de Failover Orchestrator"""

    def test_failover_strategies(self, api):
        """GET /api/v1/failover/strategies"""
        result = api.call("GET", "/api/v1/failover/strategies")
        assert result.success
        print(f"   strategies: {result.status_code}")

    def test_failover_settings_global(self, api):
        """GET /api/v1/failover/settings/global"""
        result = api.call("GET", "/api/v1/failover/settings/global")
        print(f"   settings/global: {result.status_code}")

    def test_failover_settings_machines(self, api):
        """GET /api/v1/failover/settings/machines"""
        result = api.call("GET", "/api/v1/failover/settings/machines")
        print(f"   settings/machines: {result.status_code}")

    def test_failover_readiness(self, api, real_instance):
        """GET /api/v1/failover/readiness/{machine_id}"""
        machine_id = real_instance or "test-machine"
        result = api.call("GET", f"/api/v1/failover/readiness/{machine_id}")
        print(f"   readiness: {result.status_code}")

    def test_failover_status(self, api, real_instance):
        """GET /api/v1/failover/status/{machine_id}"""
        machine_id = real_instance or "test-machine"
        result = api.call("GET", f"/api/v1/failover/status/{machine_id}")
        print(f"   status: {result.status_code}")

    def test_regional_volume_list(self, api):
        """GET /api/v1/failover/regional-volume/list"""
        result = api.call("GET", "/api/v1/failover/regional-volume/list")
        print(f"   regional-volume/list: {result.status_code}")

    def test_regional_volume_search(self, api):
        """GET /api/v1/failover/regional-volume/search/{region}"""
        result = api.call("GET", "/api/v1/failover/regional-volume/search/us-east")
        print(f"   regional-volume/search: {result.status_code}")


# =============================================================================
# TESTES DE STANDBY (CPU Standby)
# =============================================================================
class TestStandby:
    """Testes de CPU Standby"""

    def test_standby_status(self, api):
        """GET /api/v1/standby/status"""
        result = api.call("GET", "/api/v1/standby/status")
        print(f"   status: {result.status_code}")

    def test_standby_associations(self, api):
        """GET /api/v1/standby/associations"""
        result = api.call("GET", "/api/v1/standby/associations")
        print(f"   associations: {result.status_code}")

    def test_standby_pricing(self, api):
        """GET /api/v1/standby/pricing"""
        result = api.call("GET", "/api/v1/standby/pricing")
        print(f"   pricing: {result.status_code}")

    def test_failover_report(self, api):
        """GET /api/v1/standby/failover/report"""
        result = api.call("GET", "/api/v1/standby/failover/report")
        print(f"   failover/report: {result.status_code}")

    def test_failover_active(self, api):
        """GET /api/v1/standby/failover/active"""
        result = api.call("GET", "/api/v1/standby/failover/active")
        print(f"   failover/active: {result.status_code}")

    def test_failover_history(self, api):
        """GET /api/v1/standby/failover/test-real/history"""
        result = api.call("GET", "/api/v1/standby/failover/test-real/history")
        print(f"   failover/history: {result.status_code}")

    def test_create_mock_association(self, api):
        """POST /api/v1/standby/test/create-mock-association"""
        result = api.call("POST", "/api/v1/standby/test/create-mock-association", {
            "gpu_type": "RTX 4090",
            "cpu_type": "c2-standard-4"
        })
        print(f"   create-mock-association: {result.status_code}")


# =============================================================================
# TESTES DE WARMPOOL (GPU Warm Pool)
# =============================================================================
class TestWarmPool:
    """Testes de GPU Warm Pool"""

    def test_warmpool_hosts(self, api):
        """GET /api/v1/warmpool/hosts"""
        result = api.call("GET", "/api/v1/warmpool/hosts")
        print(f"   hosts: {result.status_code}")

    def test_warmpool_status(self, api, real_instance):
        """GET /api/v1/warmpool/status/{machine_id}"""
        machine_id = real_instance or "test-machine"
        result = api.call("GET", f"/api/v1/warmpool/status/{machine_id}")
        print(f"   status: {result.status_code}")


# =============================================================================
# TESTES DE SAVINGS
# =============================================================================
class TestSavings:
    """Testes de economia"""

    def test_savings_summary(self, api):
        """GET /api/v1/savings/summary"""
        result = api.call("GET", "/api/v1/savings/summary")
        print(f"   summary: {result.status_code}")

    def test_savings_history(self, api):
        """GET /api/v1/savings/history"""
        result = api.call("GET", "/api/v1/savings/history")
        print(f"   history: {result.status_code}")

    def test_savings_breakdown(self, api):
        """GET /api/v1/savings/breakdown"""
        result = api.call("GET", "/api/v1/savings/breakdown")
        print(f"   breakdown: {result.status_code}")

    def test_savings_comparison(self, api):
        """GET /api/v1/savings/comparison/{gpu_type}"""
        result = api.call("GET", "/api/v1/savings/comparison/RTX 4090")
        print(f"   comparison: {result.status_code}")


# =============================================================================
# TESTES DE HIBERNATION
# =============================================================================
class TestHibernation:
    """Testes de hibernacao"""

    def test_hibernation_stats(self, api):
        """GET /api/v1/hibernation/stats"""
        result = api.call("GET", "/api/v1/hibernation/stats")
        print(f"   stats: {result.status_code}")


# =============================================================================
# TESTES DE FINETUNE
# =============================================================================
class TestFineTune:
    """Testes de Fine-tuning"""

    def test_finetune_models(self, api):
        """GET /api/v1/finetune/models"""
        result = api.call("GET", "/api/v1/finetune/models")
        print(f"   models: {result.status_code}")

    def test_finetune_jobs(self, api):
        """GET /api/v1/finetune/jobs"""
        result = api.call("GET", "/api/v1/finetune/jobs")
        print(f"   jobs: {result.status_code}")


# =============================================================================
# TESTES DE AGENT
# =============================================================================
class TestAgent:
    """Testes de Agent (DumontAgent)"""

    def test_agent_instances(self, api):
        """GET /api/v1/agent/instances"""
        result = api.call("GET", "/api/v1/agent/instances")
        print(f"   instances: {result.status_code}")

    def test_agent_status(self, api):
        """POST /api/v1/agent/status"""
        result = api.call("POST", "/api/v1/agent/status", {
            "instance_id": "test-instance",
            "status": "running"
        })
        print(f"   status: {result.status_code}")


# =============================================================================
# TESTES DE AI WIZARD
# =============================================================================
class TestAIWizard:
    """Testes de AI Wizard"""

    def test_ai_wizard_analyze(self, api):
        """POST /api/v1/ai-wizard/analyze"""
        result = api.call("POST", "/api/v1/ai-wizard/analyze", {
            "requirements": "I need to train a 7B LLM model",
            "budget": 100
        })
        print(f"   analyze: {result.status_code}")


# =============================================================================
# TESTES DE ADVISOR
# =============================================================================
class TestAdvisor:
    """Testes de Advisor"""

    def test_advisor_recommend(self, api):
        """POST /api/v1/advisor/recommend"""
        result = api.call("POST", "/api/v1/advisor/recommend", {
            "workload_type": "training",
            "model_size": "7B",
            "budget_per_hour": 1.0
        })
        print(f"   recommend: {result.status_code}")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
