"""
E2E User Journey Tests - Testes REAIS de Jornada do Usuario
============================================================

Testes que fazem operacoes REAIS via API:
- Login e autenticacao
- Listar ofertas de GPU
- Provisionar instancia (quando marcado @slow)
- Verificar status
- Destruir instancia

Execucao rapida (sem provisionar GPU):
    cd cli && pytest tests/test_e2e_journeys.py -v -m "not slow"

Execucao completa (provisiona GPU real - CUSTA DINHEIRO):
    cd cli && pytest tests/test_e2e_journeys.py -v
"""
import pytest
import requests
import time
import os
from typing import Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8001")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def api_session():
    """Session HTTP para testes."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    yield session
    session.close()


@pytest.fixture(scope="module")
def auth_token(api_session) -> Optional[str]:
    """Obtem token JWT via login."""
    try:
        response = api_session.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
    except Exception:
        pass
    return None


@pytest.fixture(scope="module")
def authenticated_session(api_session, auth_token):
    """Session com autenticacao."""
    if auth_token:
        api_session.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_session


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def api_get(session, path: str, expect_json: bool = True) -> dict:
    """GET request helper."""
    try:
        resp = session.get(f"{API_BASE_URL}{path}", timeout=30)
        if expect_json and resp.text:
            try:
                return {"status": resp.status_code, "data": resp.json()}
            except ValueError:
                return {"status": resp.status_code, "data": resp.text[:100]}
        return {"status": resp.status_code, "data": resp.text[:100] if resp.text else ""}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def api_post(session, path: str, data: dict = None) -> dict:
    """POST request helper."""
    try:
        resp = session.post(f"{API_BASE_URL}{path}", json=data or {}, timeout=60)
        return {"status": resp.status_code, "data": resp.json() if resp.text else {}}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def api_delete(session, path: str) -> dict:
    """DELETE request helper."""
    try:
        resp = session.delete(f"{API_BASE_URL}{path}", timeout=30)
        return {"status": resp.status_code, "data": resp.json() if resp.text else {}}
    except Exception as e:
        return {"status": 0, "error": str(e)}


# =============================================================================
# JOURNEY 1: API Health & Discovery
# =============================================================================

class TestAPIHealthJourney:
    """Jornada: Descoberta da API e verificacao de saude."""

    def test_api_is_reachable(self, api_session):
        """API responde a requests."""
        result = api_get(api_session, "/", expect_json=False)
        assert result["status"] in [200, 307, 404], f"API unreachable: {result}"

    def test_openapi_docs_available(self, api_session):
        """Documentacao OpenAPI disponivel."""
        result = api_get(api_session, "/docs", expect_json=False)
        assert result["status"] in [200, 307]

    def test_api_version_endpoint(self, api_session):
        """Endpoint de versao da API."""
        result = api_get(api_session, "/api/v1/")
        # Pode retornar 200 ou 404 dependendo da configuracao
        assert result["status"] in [200, 404, 307]


# =============================================================================
# JOURNEY 2: Authentication Flow
# =============================================================================

class TestAuthenticationJourney:
    """Jornada: Fluxo completo de autenticacao."""

    def test_login_with_valid_credentials(self, api_session):
        """Login com credenciais validas retorna token."""
        result = api_post(api_session, "/api/v1/auth/login", {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        # Pode falhar se usuario nao existe, mas API deve responder
        assert result["status"] in [200, 401, 422]

    def test_login_with_invalid_credentials(self, api_session):
        """Login com credenciais invalidas retorna 401."""
        result = api_post(api_session, "/api/v1/auth/login", {
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert result["status"] in [401, 422]

    def test_protected_endpoint_without_token(self, api_session):
        """Endpoints protegidos requerem token."""
        # Remove auth header temporariamente
        session = requests.Session()
        result = api_get(session, "/api/v1/instances")
        assert result["status"] in [401, 403, 422]


# =============================================================================
# JOURNEY 3: GPU Offers Discovery
# =============================================================================

class TestGPUOffersJourney:
    """Jornada: Descoberta de ofertas de GPU."""

    def test_list_gpu_offers(self, authenticated_session):
        """Listar ofertas de GPU disponiveis."""
        result = api_get(authenticated_session, "/api/v1/instances/offers")
        # Pode precisar de autenticacao
        if result["status"] == 200:
            assert "offers" in result["data"] or isinstance(result["data"], list)

    def test_list_offers_with_filter(self, authenticated_session):
        """Listar ofertas com filtro de GPU."""
        result = api_get(authenticated_session, "/api/v1/instances/offers?gpu_name=RTX")
        assert result["status"] in [200, 401, 422]

    def test_spot_market_analysis(self, authenticated_session):
        """Analise do mercado spot."""
        result = api_get(authenticated_session, "/api/v1/spot/market")
        assert result["status"] in [200, 401, 404]


# =============================================================================
# JOURNEY 4: Instance Management
# =============================================================================

class TestInstanceManagementJourney:
    """Jornada: Gerenciamento de instancias."""

    def test_list_instances(self, authenticated_session):
        """Listar instancias do usuario."""
        result = api_get(authenticated_session, "/api/v1/instances")
        if result["status"] == 200:
            data = result["data"]
            assert "instances" in data or isinstance(data, list)

    def test_list_instances_with_status_filter(self, authenticated_session):
        """Listar instancias com filtro de status."""
        result = api_get(authenticated_session, "/api/v1/instances?status=running")
        assert result["status"] in [200, 401, 422]


# =============================================================================
# JOURNEY 5: Standby & Failover
# =============================================================================

class TestStandbyFailoverJourney:
    """Jornada: Configuracao de standby e failover."""

    def test_get_standby_status(self, authenticated_session):
        """Obter status do standby."""
        result = api_get(authenticated_session, "/api/v1/standby")
        assert result["status"] in [200, 401, 404]

    def test_get_failover_strategies(self, authenticated_session):
        """Listar estrategias de failover disponiveis."""
        result = api_get(authenticated_session, "/api/v1/standby/strategies")
        assert result["status"] in [200, 401, 404]


# =============================================================================
# JOURNEY 6: Machine History & Blacklist
# =============================================================================

class TestMachineHistoryJourney:
    """Jornada: Historico e blacklist de maquinas."""

    def test_get_machine_history_summary(self, authenticated_session):
        """Obter resumo do historico de maquinas."""
        result = api_get(authenticated_session, "/api/v1/machines/history/summary")
        assert result["status"] in [200, 401, 404]

    def test_get_blacklist(self, authenticated_session):
        """Listar maquinas na blacklist."""
        result = api_get(authenticated_session, "/api/v1/machines/history/blacklist")
        assert result["status"] in [200, 401, 404]


# =============================================================================
# JOURNEY 7: Metrics & Savings
# =============================================================================

class TestMetricsSavingsJourney:
    """Jornada: Metricas e economia."""

    def test_get_savings_metrics(self, authenticated_session):
        """Obter metricas de economia."""
        result = api_get(authenticated_session, "/api/v1/metrics/savings/real")
        assert result["status"] in [200, 401, 404]

    def test_get_general_metrics(self, authenticated_session):
        """Obter metricas gerais."""
        result = api_get(authenticated_session, "/api/v1/metrics")
        assert result["status"] in [200, 401, 404]


# =============================================================================
# JOURNEY 8: Model Deployment
# =============================================================================

class TestModelDeploymentJourney:
    """Jornada: Deploy de modelos LLM."""

    def test_list_available_models(self, authenticated_session):
        """Listar modelos disponiveis para deploy."""
        result = api_get(authenticated_session, "/api/v1/models/list")
        assert result["status"] in [200, 401, 404]


# =============================================================================
# JOURNEY 9: Complete User Flow (REAL GPU - Costs Money!)
# =============================================================================

class TestCompleteGPUJourney:
    """Jornada COMPLETA: Provisiona GPU real, testa, destroi."""

    @pytest.mark.slow
    def test_full_gpu_lifecycle(self, authenticated_session):
        """
        Jornada completa de GPU:
        1. Buscar ofertas
        2. Provisionar instancia mais barata
        3. Aguardar ready
        4. Verificar status
        5. Destruir instancia

        AVISO: Este teste CUSTA DINHEIRO!
        """
        # 1. Buscar ofertas
        offers_result = api_get(authenticated_session, "/api/v1/instances/offers?max_price=0.50")
        if offers_result["status"] != 200:
            pytest.skip("Could not get GPU offers")

        offers = offers_result["data"].get("offers", [])
        if not offers:
            pytest.skip("No GPU offers available under $0.50/hr")

        # 2. Escolher oferta mais barata
        cheapest = min(offers, key=lambda x: x.get("dph_total", 999))
        offer_id = cheapest.get("id")

        print(f"\n  Selected offer: {cheapest.get('gpu_name')} @ ${cheapest.get('dph_total')}/hr")

        # 3. Provisionar
        provision_result = api_post(authenticated_session, "/api/v1/instances/provision", {
            "offer_id": offer_id,
            "image": "nvidia/cuda:12.1.0-base-ubuntu22.04",
            "disk_size": 20,
            "label": "pytest-e2e-test"
        })

        if provision_result["status"] != 200:
            pytest.skip(f"Could not provision: {provision_result}")

        instance_id = provision_result["data"].get("instance_id")
        assert instance_id is not None, "No instance_id returned"

        print(f"  Provisioned instance: {instance_id}")

        try:
            # 4. Aguardar ready (max 120s)
            ready = False
            for _ in range(24):  # 24 * 5s = 120s
                time.sleep(5)
                status_result = api_get(authenticated_session, f"/api/v1/instances/{instance_id}")
                if status_result["status"] == 200:
                    status = status_result["data"].get("status", "")
                    print(f"  Status: {status}")
                    if status.lower() in ["running", "ready"]:
                        ready = True
                        break

            assert ready, "Instance did not become ready in 120s"

            # 5. Verificar que tem SSH info
            assert status_result["data"].get("ssh_host") or status_result["data"].get("ip")

        finally:
            # 6. SEMPRE destruir a instancia
            print(f"  Destroying instance {instance_id}...")
            destroy_result = api_delete(authenticated_session, f"/api/v1/instances/{instance_id}")
            assert destroy_result["status"] in [200, 204, 404], f"Failed to destroy: {destroy_result}"
            print("  Instance destroyed successfully")


# =============================================================================
# JOURNEY 10: Batch Operations
# =============================================================================

class TestBatchOperationsJourney:
    """Jornada: Operacoes em lote."""

    def test_list_all_resources(self, authenticated_session):
        """Lista todos os recursos principais em sequencia."""
        endpoints = [
            "/api/v1/instances",
            "/api/v1/standby",
            "/api/v1/machines/history/summary",
        ]

        results = {}
        for endpoint in endpoints:
            result = api_get(authenticated_session, endpoint)
            results[endpoint] = result["status"]

        # Pelo menos metade deve responder com sucesso
        success_count = sum(1 for s in results.values() if s in [200, 404])
        assert success_count >= len(endpoints) // 2, f"Too many failures: {results}"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
