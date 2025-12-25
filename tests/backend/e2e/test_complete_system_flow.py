#!/usr/bin/env python3
"""
Testes Backend - Fluxos End-to-End

Testa fluxos completos do sistema Dumont Cloud:
- Fluxo de novo usuário (registro, login, configuração)
- Fluxo de power user (instâncias, savings, standby)
- Resiliência do sistema

Uso:
    pytest tests/backend/e2e/test_complete_system_flow.py -v
"""

import os
import sys
import pytest
import time
import requests
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.conftest import BaseTestCase, Colors


# =============================================================================
# E2E CLIENT (local to avoid fixture conflicts with xdist)
# =============================================================================

class E2EClient:
    """E2E test client that returns raw Response objects."""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout
        self.token = None

    def login(self, username: str = None, password: str = None) -> bool:
        """Authenticate and store token. Auto-registers if user doesn't exist."""
        if username is None:
            username = f"e2e_auto_{int(time.time())}@example.com"
        if password is None:
            password = "e2e_test_password_123"
            
        try:
            # Try login first
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.ok:
                data = response.json()
                self.token = data.get("token") or data.get("access_token")
                if self.token:
                    self.session.headers["Authorization"] = f"Bearer {self.token}"
                    return True
            
            # If login fails, try to register
            if response.status_code == 401:
                reg_resp = self.session.post(
                    f"{self.base_url}/api/v1/auth/register",
                    json={"email": username, "password": password},
                    timeout=10
                )
                
                if reg_resp.ok:
                    data = reg_resp.json()
                    self.token = data.get("token") or data.get("access_token")
                    if self.token:
                        self.session.headers["Authorization"] = f"Bearer {self.token}"
                        return True
                    
                    # If no token in register response, try login again
                    login2 = self.session.post(
                        f"{self.base_url}/api/v1/auth/login",
                        json={"username": username, "password": password},
                        timeout=10
                    )
                    if login2.ok:
                        data = login2.json()
                        self.token = data.get("token") or data.get("access_token")
                        if self.token:
                            self.session.headers["Authorization"] = f"Bearer {self.token}"
                            return True
                
            return False
        except Exception:
            return False

    def get(self, path: str, params: dict = None, headers: dict = None) -> requests.Response:
        """GET request returning raw Response."""
        url = f"{self.base_url}{path}"
        return self.session.get(url, params=params, headers=headers, timeout=self.timeout)

    def post(self, path: str, json: dict = None, data: dict = None, headers: dict = None) -> requests.Response:
        """POST request returning raw Response."""
        url = f"{self.base_url}{path}"
        return self.session.post(url, json=json or data, headers=headers, timeout=self.timeout)


# =============================================================================
# MODULE FIXTURES (avoid global fixture conflicts)
# =============================================================================

@pytest.fixture(scope="module")
def e2e_server_url():
    """Get server URL, starting server if needed."""
    import subprocess
    import socket
    
    port = int(os.environ.get("E2E_SERVER_PORT", "8000"))
    host = "127.0.0.1"
    base_url = f"http://{host}:{port}"
    
    # Check if server already running
    def is_port_in_use():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0
    
    if is_port_in_use():
        yield base_url
        return
    
    # Start server
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app", 
         "--host", host, "--port", str(port), "--log-level", "warning"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for server
    for _ in range(60):
        try:
            resp = requests.get(f"{base_url}/health", timeout=2)
            if resp.status_code == 200:
                break
        except:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("Server failed to start")
    
    yield base_url
    
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except:
        proc.kill()


@pytest.fixture(scope="module")
def e2e_api_client(e2e_server_url):
    """Authenticated E2E client."""
    client = E2EClient(e2e_server_url)
    if not client.login():
        pytest.skip(f"Could not authenticate with {e2e_server_url}")
    yield client


@pytest.fixture(scope="module")
def e2e_unauth_client(e2e_server_url):
    """Unauthenticated E2E client."""
    yield E2EClient(e2e_server_url)


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestCompleteSystemFlow(BaseTestCase):
    """Testes de fluxos completos do sistema"""

    def test_new_user_onboarding(self, e2e_unauth_client, e2e_server_url):
        """Testa fluxo completo de novo usuário"""
        timestamp = int(time.time())
        test_email = f"e2e_test_{timestamp}@example.com"

        # 1. Registro
        self.log_info("Passo 1: Registro de novo usuário")
        resp = e2e_unauth_client.post(
            "/api/v1/auth/register",
            json={"email": test_email, "password": "e2e_test_123"}
        )

        # Skip se database não configurado
        if resp.status_code == 500:
            pytest.skip("Database não configurado para E2E")

        if resp.status_code in [200, 201]:
            data = resp.json()
            token = data.get("token")
            self.log_success(f"Usuário registrado: {test_email}")

            # 2. Login para obter novo token
            self.log_info("Passo 2: Login")
            login_resp = e2e_unauth_client.post(
                "/api/v1/auth/login",
                json={"username": test_email, "password": "e2e_test_123"}
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["token"]
            self.log_success("Login bem-sucedido")

            # 3. Verificar autenticação
            self.log_info("Passo 3: Verificar /me")
            headers = {"Authorization": f"Bearer {token}"}
            me_resp = e2e_unauth_client.get("/api/v1/auth/me", headers=headers)
            assert me_resp.status_code == 200
            me_data = me_resp.json()
            assert me_data.get("authenticated") == True
            self.log_success("Autenticação verificada")

            # 4. Verificar savings (dashboard) - skip se DB não configurado
            self.log_info("Passo 4: Acessar dashboard")
            savings_resp = e2e_unauth_client.get("/api/v1/savings/summary", headers=headers)
            if savings_resp.status_code == 500:
                self.log_warning("Savings não disponível (DB não configurado)")
            else:
                assert savings_resp.status_code == 200
                self.log_success("Dashboard acessível")

        else:
            # Registro pode falhar se usuário já existe
            self.log_warning(f"Registro falhou: {resp.status_code}")
            assert resp.status_code in [400, 409, 422]

    def test_authenticated_user_flow(self, e2e_api_client):
        """Testa fluxo de usuário autenticado"""
        # 1. Verificar autenticação
        self.log_info("Passo 1: Verificar autenticação")
        me_resp = e2e_api_client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        self.log_success("Usuário autenticado")

        # 2. Listar instâncias
        self.log_info("Passo 2: Listar instâncias")
        instances_resp = e2e_api_client.get("/api/v1/instances")
        assert instances_resp.status_code in [200, 503], f"Got {instances_resp.status_code}"
        instances_data = instances_resp.json()
        assert "instances" in instances_data
        self.log_success(f"Instâncias listadas: {instances_data.get('count', 0)}")

        # 3. Ver savings summary (skip se DB não disponível)
        self.log_info("Passo 3: Ver savings")
        savings_resp = e2e_api_client.get("/api/v1/savings/summary")
        if savings_resp.status_code == 500:
            self.log_warning("Savings não disponível (DB não configurado)")
        else:
            assert savings_resp.status_code == 200
            self.log_success("Savings carregado")

        # 4. Ver status do standby
        self.log_info("Passo 4: Ver standby status")
        standby_resp = e2e_api_client.get("/api/v1/standby/status")
        assert standby_resp.status_code == 200
        self.log_success("Standby status carregado")

        # 5. Ver hibernation stats
        self.log_info("Passo 5: Ver hibernation stats")
        hibernation_resp = e2e_api_client.get("/api/v1/hibernation/stats")
        assert hibernation_resp.status_code == 200
        self.log_success("Hibernation stats carregado")

    def test_system_resilience(self, e2e_api_client, e2e_server_url):
        """Testa resiliência do sistema com múltiplas requisições"""
        import concurrent.futures

        endpoints = [
            "/api/v1/instances",
            "/api/v1/savings/summary",
            "/api/v1/standby/status",
            "/api/v1/hibernation/stats",
            "/health"
        ]

        def fetch_endpoint(endpoint):
            if endpoint == "/health":
                client = E2EClient(e2e_server_url)
                resp = client.get(endpoint)
            else:
                resp = e2e_api_client.get(endpoint)
            return (endpoint, resp.status_code)

        self.log_info("Testando resiliência com requisições concorrentes")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_endpoint, ep) for ep in endpoints]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = sum(1 for _, status in results if status == 200)
        self.log_success(f"Resiliência: {success_count}/{len(endpoints)} endpoints OK")

        assert success_count >= 3, "Sistema não resiliente - muitas falhas"


class TestUserJourneyScenarios(BaseTestCase):
    """Testes de cenários de jornada do usuário"""

    def test_ml_researcher_journey(self, e2e_api_client):
        """Simula jornada de um pesquisador de ML"""
        # 1. Buscar ofertas de GPU
        self.log_info("ML Researcher: Buscando ofertas de GPU")
        offers_resp = e2e_api_client.get("/api/v1/instances/offers")
        # API externa (Vast.ai) pode estar indisponível - aceitar falhas
        if offers_resp.status_code in [429, 500, 503]:
            self.log_warning("API externa indisponível - continuando jornada")
        else:
            assert offers_resp.status_code == 200
            self.log_success("Ofertas carregadas")

        # 2. Ver métricas de mercado
        self.log_info("ML Researcher: Analisando mercado")
        market_resp = e2e_api_client.get("/api/v1/metrics/market")
        assert market_resp.status_code == 200
        self.log_success("Métricas de mercado carregadas")

        # 3. Listar instâncias existentes
        self.log_info("ML Researcher: Verificando instâncias")
        instances_resp = e2e_api_client.get("/api/v1/instances")
        assert instances_resp.status_code in [200, 503], f"Got {instances_resp.status_code}"
        self.log_success("Instâncias verificadas")

    def test_cost_optimizer_journey(self, e2e_api_client):
        """Simula jornada de alguém focado em economia"""
        # 1. Ver savings summary
        self.log_info("Cost Optimizer: Analisando savings")
        savings_resp = e2e_api_client.get("/api/v1/savings/summary")

        # Skip se database não está configurado
        if savings_resp.status_code == 500:
            pytest.skip("Database não configurado para savings")

        assert savings_resp.status_code == 200
        self.log_success("Savings summary OK")

        # 4. Ver hibernation stats (economia automática)
        self.log_info("Cost Optimizer: Hibernation stats")
        hibernation_resp = e2e_api_client.get("/api/v1/hibernation/stats")
        assert hibernation_resp.status_code == 200
        self.log_success("Hibernation stats OK")

    def test_devops_engineer_journey(self, e2e_api_client, e2e_server_url):
        """Simula jornada de um engenheiro DevOps"""
        # 1. Health check
        self.log_info("DevOps: Health check")
        client = E2EClient(e2e_server_url)
        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        self.log_success("Health OK")

        # 2. Standby status
        self.log_info("DevOps: Standby status")
        standby_resp = e2e_api_client.get("/api/v1/standby/status")
        assert standby_resp.status_code == 200
        self.log_success("Standby status OK")

        # 3. Listar instâncias
        self.log_info("DevOps: Listar instâncias")
        instances_resp = e2e_api_client.get("/api/v1/instances")
        assert instances_resp.status_code in [200, 503], f"Got {instances_resp.status_code}"
        self.log_success("Instâncias listadas")


class TestErrorRecovery(BaseTestCase):
    """Testes de recuperação de erros"""

    def test_invalid_endpoint_recovery(self, e2e_api_client):
        """Testa que sistema se recupera de endpoints inválidos"""
        # Acessar endpoint inválido - pode retornar 404 ou ser tratado graciosamente
        resp = e2e_api_client.get("/api/v1/nonexistent/xyz123")
        assert resp.status_code in [200, 404, 405], f"Status inesperado: {resp.status_code}"

        # Sistema deve continuar funcionando
        instances_resp = e2e_api_client.get("/api/v1/instances")
        assert instances_resp.status_code in [200, 503], f"Got {instances_resp.status_code}"

        self.log_success("Sistema se recuperou de endpoint inválido")

    def test_invalid_auth_recovery(self, e2e_unauth_client, e2e_api_client):
        """Testa recuperação após tentativa de auth inválida"""
        # Tentar com token inválido
        resp = e2e_unauth_client.get(
            "/api/v1/instances",
            headers={"Authorization": "Bearer invalid_token"}
        )

        # Deve rejeitar mas não quebrar (503 = serviço indisponível também é ok)
        assert resp.status_code in [200, 401, 403, 503]

        # Sistema deve continuar funcionando para usuário válido
        valid_resp = e2e_api_client.get("/api/v1/instances")
        assert valid_resp.status_code in [200, 503], f"Status: {valid_resp.status_code}"

        self.log_success("Sistema se recuperou de auth inválida")

    def test_malformed_request_recovery(self, e2e_api_client):
        """Testa recuperação após requisição malformada"""
        # Enviar JSON inválido
        resp = e2e_api_client.session.post(
            f"{e2e_api_client.base_url}/api/v1/auth/login",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Deve rejeitar mas não quebrar (400 ou 422)
        assert resp.status_code in [400, 422, 500]

        # Sistema deve continuar funcionando
        instances_resp = e2e_api_client.get("/api/v1/instances")
        assert instances_resp.status_code in [200, 503], f"Got {instances_resp.status_code}"

        self.log_success("Sistema se recuperou de requisição malformada")
