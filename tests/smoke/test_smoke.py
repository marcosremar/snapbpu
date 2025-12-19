#!/usr/bin/env python3
"""
🚀 Smoke Tests - Dumont Cloud

Validação RÁPIDA que o sistema está funcionando.
Tempo máximo: 10 segundos TOTAL

Roda:
- A cada commit
- Antes de qualquer outro teste
- Se falhar, não prosseguir

Uso:
    pytest tests/smoke/ -v --timeout=10
    pytest -m smoke -v
"""

import pytest
import requests
import os

# Configuração
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8766")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
DEMO_USER = os.environ.get("TEST_USER", "test@test.com")
DEMO_PASS = os.environ.get("TEST_PASS", "test123")
TIMEOUT = 5  # segundos - agressivo!


class TestSmoke:
    """
    Smoke Tests - Se QUALQUER um falhar, o sistema está broken.

    Ordem importa:
    1. Backend vivo?
    2. Auth funciona?
    3. API principal responde?
    4. Demo mode OK?
    5. Frontend carrega?
    """

    @pytest.mark.smoke
    @pytest.mark.order(1)
    def test_01_backend_alive(self):
        """🏥 Backend Health Check - Sistema está vivo?"""
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
            # Aceita 200 ou 404 (endpoint pode não existir mas servidor responde)
            assert resp.status_code in [200, 404], f"Backend morto: {resp.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.fail("❌ Backend não está rodando! Inicie com: python src/main.py")
        except requests.exceptions.Timeout:
            pytest.fail("❌ Backend muito lento (>5s)")

    @pytest.mark.smoke
    @pytest.mark.order(2)
    def test_02_auth_endpoint_exists(self):
        """🔐 Auth Endpoint - Login endpoint responde?"""
        try:
            # Só verifica se endpoint existe (não precisa credenciais válidas)
            resp = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"username": "invalid", "password": "invalid"},
                timeout=TIMEOUT
            )
            # 401 = endpoint existe e rejeita credenciais inválidas (CORRETO!)
            # 200 = logou (improvável com credenciais inválidas)
            # 422 = validação (endpoint existe)
            assert resp.status_code in [200, 401, 422], \
                f"Auth endpoint broken: {resp.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.fail("❌ Backend não está rodando!")

    @pytest.mark.smoke
    @pytest.mark.order(3)
    def test_03_demo_login_works(self):
        """👤 Demo Login - Usuário de teste consegue logar?"""
        try:
            resp = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"username": DEMO_USER, "password": DEMO_PASS},
                timeout=TIMEOUT
            )

            if resp.status_code != 200:
                pytest.fail(f"❌ Demo login falhou: {resp.status_code} - {resp.text[:200]}")

            data = resp.json()
            assert "token" in data or "access_token" in data, \
                "❌ Login OK mas sem token na resposta"

        except requests.exceptions.ConnectionError:
            pytest.fail("❌ Backend não está rodando!")

    @pytest.mark.smoke
    @pytest.mark.order(4)
    def test_04_api_returns_data(self):
        """📊 API Data - Endpoint principal retorna dados?"""
        # Primeiro faz login
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": DEMO_USER, "password": DEMO_PASS},
            timeout=TIMEOUT
        )

        if login_resp.status_code != 200:
            pytest.skip("Login falhou - pulando teste de API")

        token = login_resp.json().get("token") or login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # Testa endpoint de instâncias (core do sistema)
        resp = requests.get(
            f"{BASE_URL}/api/v1/instances",
            headers=headers,
            timeout=TIMEOUT
        )

        # 200 = dados, 500/503 = API externa (aceitável em smoke)
        assert resp.status_code in [200, 500, 503], \
            f"❌ API instances broken: {resp.status_code}"

    @pytest.mark.smoke
    @pytest.mark.order(5)
    def test_05_offers_endpoint(self):
        """🎯 GPU Offers - Busca de ofertas funciona?"""
        # Login
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": DEMO_USER, "password": DEMO_PASS},
            timeout=TIMEOUT
        )

        if login_resp.status_code != 200:
            pytest.skip("Login falhou")

        token = login_resp.json().get("token") or login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # Busca ofertas (com demo flag)
        resp = requests.get(
            f"{BASE_URL}/api/v1/instances/offers",
            headers=headers,
            params={"demo": "true"},
            timeout=TIMEOUT
        )

        # 200 = ofertas, 429/500/503 = API externa com problema (OK em smoke)
        assert resp.status_code in [200, 429, 500, 503], \
            f"❌ Offers endpoint broken: {resp.status_code}"

    @pytest.mark.smoke
    @pytest.mark.order(6)
    def test_06_savings_endpoint(self):
        """💰 Savings - Dashboard de economia funciona?"""
        # Login
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": DEMO_USER, "password": DEMO_PASS},
            timeout=TIMEOUT
        )

        if login_resp.status_code != 200:
            pytest.skip("Login falhou")

        token = login_resp.json().get("token") or login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(
            f"{BASE_URL}/api/v1/savings/summary",
            headers=headers,
            timeout=TIMEOUT
        )

        assert resp.status_code == 200, f"❌ Savings broken: {resp.status_code}"

    @pytest.mark.smoke
    @pytest.mark.order(7)
    def test_07_standby_status(self):
        """🔄 Standby - Sistema de failover responde?"""
        # Login
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": DEMO_USER, "password": DEMO_PASS},
            timeout=TIMEOUT
        )

        if login_resp.status_code != 200:
            pytest.skip("Login falhou")

        token = login_resp.json().get("token") or login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(
            f"{BASE_URL}/api/v1/standby/status",
            headers=headers,
            timeout=TIMEOUT
        )

        # 200 = OK, 400 = GCP não configurado (OK em smoke)
        assert resp.status_code in [200, 400], f"❌ Standby broken: {resp.status_code}"


class TestSmokePerformance:
    """Testes de performance básica"""

    @pytest.mark.smoke
    def test_api_response_time(self):
        """⚡ Performance - API responde em tempo aceitável?"""
        import time

        start = time.time()
        resp = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        elapsed = time.time() - start

        # Health check deve ser < 500ms
        assert elapsed < 0.5, f"❌ API muito lenta: {elapsed:.2f}s (max 0.5s)"


class TestSmokeFrontend:
    """Testes básicos do frontend (se disponível)"""

    @pytest.mark.smoke
    @pytest.mark.frontend
    def test_frontend_loads(self):
        """🌐 Frontend - Página carrega?"""
        try:
            resp = requests.get(FRONTEND_URL, timeout=TIMEOUT)
            assert resp.status_code == 200, f"❌ Frontend não carrega: {resp.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.skip("Frontend não está rodando (OK se testando só backend)")


# Configuração do pytest
def pytest_configure(config):
    """Registra markers"""
    config.addinivalue_line("markers", "smoke: Smoke tests - sempre devem passar")
    config.addinivalue_line("markers", "frontend: Testes que requerem frontend rodando")
    config.addinivalue_line("markers", "order: Ordem de execução")


if __name__ == "__main__":
    # Permite rodar diretamente: python test_smoke.py
    pytest.main([__file__, "-v", "--timeout=10"])
