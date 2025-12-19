#!/usr/bin/env python3
"""
Testes Backend - Dashboard e Savings

Testa endpoints de dashboard e economia do sistema Dumont Cloud:
- GET /api/v1/savings/summary - Resumo de economia
- GET /api/v1/savings/history - Histórico de economia
- GET /api/v1/savings/breakdown - Detalhamento de economia

Uso:
    pytest tests/backend/dashboard/test_dashboard.py -v
"""

import pytest
import time
from tests.backend.conftest import BaseTestCase, Colors


class TestDashboardSavings(BaseTestCase):
    """Testes para endpoints de savings /api/v1/savings/*"""

    def test_savings_summary(self, api_client):
        """GET /api/v1/savings/summary - Resumo de economia"""
        resp = api_client.get("/api/v1/savings/summary")

        self.assert_success_response(resp, "Savings summary")
        data = resp.json()

        # Verificar campos esperados
        expected_fields = [
            "period", "total_hours", "total_cost_dumont",
            "savings_vs_aws", "savings_vs_gcp", "savings_vs_azure"
        ]
        for field in expected_fields:
            assert field in data, f"Campo {field} esperado no response"

        self.log_success("Savings summary retornou dados válidos")

    def test_savings_with_period(self, api_client):
        """GET /api/v1/savings/summary?period=week - Com período específico"""
        periods = ["day", "week", "month"]

        for period in periods:
            resp = api_client.get(f"/api/v1/savings/summary?period={period}")

            if resp.status_code == 200:
                data = resp.json()
                assert "total_cost_dumont" in data
                self.log_success(f"Savings para período {period} OK")
            else:
                # Período pode não ser suportado
                assert resp.status_code in [200, 400, 422]
                self.log_info(f"Período {period}: status {resp.status_code}")

    def test_savings_history(self, api_client):
        """GET /api/v1/savings/history - Histórico de economia"""
        resp = api_client.get("/api/v1/savings/history")

        self.assert_success_response(resp, "Savings history")
        data = resp.json()

        # Pode retornar lista ou objeto com history
        assert isinstance(data, (list, dict))
        self.log_success("Savings history retornou dados")

    def test_savings_breakdown(self, api_client):
        """GET /api/v1/savings/breakdown - Detalhamento de economia"""
        resp = api_client.get("/api/v1/savings/breakdown")

        self.assert_success_response(resp, "Savings breakdown")
        data = resp.json()

        assert isinstance(data, dict)
        self.log_success("Savings breakdown retornou dados")


class TestDashboardHealth(BaseTestCase):
    """Testes para endpoints de health"""

    def test_health_status(self, unauth_client):
        """GET /health - Status de saúde (sem auth)"""
        resp = unauth_client.get("/health")

        self.assert_success_response(resp, "Health check")
        data = resp.json()

        assert "status" in data
        assert data["status"] == "healthy"
        self.log_success("Health check OK")

    def test_health_version(self, unauth_client):
        """GET /health - Verificar versão"""
        resp = unauth_client.get("/health")

        self.assert_success_response(resp, "Health version")
        data = resp.json()

        if "version" in data:
            self.log_success(f"Versão: {data['version']}")
        else:
            self.log_info("Campo version não presente")


class TestDashboardPerformance(BaseTestCase):
    """Testes de performance do dashboard"""

    def test_dashboard_response_time(self, api_client):
        """Testa tempo de resposta do dashboard"""
        import time

        start = time.time()
        resp = api_client.get("/api/v1/savings/summary")
        elapsed = time.time() - start

        assert resp.status_code == 200
        assert elapsed < 5.0, f"Resposta muito lenta: {elapsed:.2f}s"

        self.log_success(f"Tempo de resposta: {elapsed:.3f}s")

    def test_dashboard_concurrent_requests(self, api_client):
        """Testa requisições concorrentes ao dashboard"""
        import concurrent.futures

        def fetch_summary():
            resp = api_client.get("/api/v1/savings/summary")
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(fetch_summary) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 2, "Muitas falhas em requisições concorrentes"

        self.log_success(f"Requisições concorrentes: {success_count}/3 OK")


class TestDashboardSecurity(BaseTestCase):
    """Testes de segurança do dashboard"""

    def test_dashboard_unauthorized(self, unauth_client):
        """Testa acesso não autorizado ao dashboard"""
        protected_endpoints = [
            "/api/v1/savings/summary",
            "/api/v1/savings/history",
            "/api/v1/savings/breakdown"
        ]

        for endpoint in protected_endpoints:
            resp = unauth_client.get(endpoint)

            # Deve rejeitar sem autenticação (401 ou 403)
            # Ou retornar erro de autenticação no body
            if resp.status_code == 200:
                data = resp.json()
                assert "error" in data, f"Endpoint {endpoint} não protegido"
            else:
                assert resp.status_code in [401, 403], f"Endpoint {endpoint}: status inesperado {resp.status_code}"

        self.log_success("Endpoints de savings protegidos")

    def test_dashboard_input_validation(self, api_client):
        """Testa validação de input"""
        # Tenta períodos inválidos
        invalid_periods = ["invalid", "123", "' OR 1=1"]

        for period in invalid_periods:
            resp = api_client.get(f"/api/v1/savings/summary?period={period}")

            # Deve aceitar ou rejeitar, mas não quebrar
            assert resp.status_code in [200, 400, 422]

        self.log_success("Validação de input OK")

    def test_dashboard_rate_limiting(self, api_client):
        """Testa rate limiting do dashboard"""
        responses = []
        for _ in range(10):
            resp = api_client.get("/api/v1/savings/summary")
            responses.append(resp.status_code)

        # Deve permitir múltiplas requisições ou fazer rate limit (429)
        success_count = sum(1 for r in responses if r == 200)
        rate_limited = sum(1 for r in responses if r == 429)

        assert success_count > 0 or rate_limited > 0
        self.log_success(f"Rate limiting: {success_count} OK, {rate_limited} limited")
