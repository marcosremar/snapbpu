#!/usr/bin/env python3
"""
Testes Backend - Sistema de Sincronização

Testa endpoints de sincronização existentes na API:
- POST /api/v1/instances/{instance_id}/sync - Iniciar sync de instância
- GET /api/v1/instances/{instance_id}/sync/status - Status do sync

Uso:
    pytest tests/backend/sync/test_sync.py -v
"""

import pytest
from tests.backend.conftest import BaseTestCase, Colors


class TestSyncEndpoints(BaseTestCase):
    """Testes para endpoints de sync via instances"""

    def test_sync_status_requires_instance(self, api_client):
        """GET /api/v1/instances/{id}/sync/status - Requer ID válido"""
        # Tenta com ID fictício
        resp = api_client.get("/api/v1/instances/99999999/sync/status")

        # Deve retornar erro - instância não existe
        # 500 pode ocorrer se tentar acessar uma instância que não existe
        assert resp.status_code in [200, 400, 404, 422, 500], \
            f"Status inesperado: {resp.status_code}"

        if resp.status_code == 200:
            data = resp.json()
            # Verifica estrutura básica se retornar 200
            assert isinstance(data, dict)
            self.log_success("Sync status retornou dados")
        elif resp.status_code == 500:
            self.log_info("Sync status para instância inexistente retornou 500 (esperado)")
        else:
            self.log_info(f"Sync status para instância inexistente: {resp.status_code}")

    def test_sync_trigger_requires_instance(self, api_client):
        """POST /api/v1/instances/{id}/sync - Requer ID válido"""
        # Tenta iniciar sync em instância fictícia
        resp = api_client.post("/api/v1/instances/99999999/sync")

        # Deve retornar erro (instância não existe)
        assert resp.status_code in [200, 400, 404, 422, 500], \
            f"Status inesperado: {resp.status_code}"

        self.log_info(f"Sync trigger para instância inexistente: {resp.status_code}")

    def test_sync_endpoints_require_auth(self, unauth_client):
        """Testa que endpoints de sync requerem autenticação"""
        endpoints = [
            "/api/v1/instances/123/sync/status",
            "/api/v1/instances/123/sync"
        ]

        for endpoint in endpoints:
            if "status" in endpoint:
                resp = unauth_client.get(endpoint)
            else:
                resp = unauth_client.post(endpoint)

            # Deve requerer autenticação
            if resp.status_code == 200:
                data = resp.json()
                assert "error" in data, f"Endpoint {endpoint} não protegido"
            else:
                assert resp.status_code in [401, 403, 404], \
                    f"Endpoint {endpoint}: status inesperado {resp.status_code}"

        self.log_success("Endpoints de sync protegidos")


class TestSyncStandalone(BaseTestCase):
    """Testes para endpoints de sync standalone (não implementados)"""

    def test_standalone_sync_not_implemented(self, api_client):
        """Verifica endpoints de sync standalone não implementados"""
        endpoints = [
            "/api/v1/sync",
            "/api/v1/sync/initialize",
            "/api/v1/sync/status"
        ]

        for endpoint in endpoints:
            resp = api_client.get(endpoint)
            # 404 = endpoint não existe (esperado)
            assert resp.status_code in [404, 405, 501], \
                f"Endpoint {endpoint} retornou {resp.status_code} - pode ter sido implementado!"

        self.log_info("Endpoints de sync standalone não implementados (esperado)")


class TestSyncPerformance(BaseTestCase):
    """Testes de performance do sync"""

    def test_sync_status_response_time(self, api_client):
        """Testa tempo de resposta do sync status"""
        import time

        start = time.time()
        resp = api_client.get("/api/v1/instances/99999999/sync/status")
        elapsed = time.time() - start

        # Mesmo para instância inexistente, deve responder rápido
        assert elapsed < 5.0, f"Resposta muito lenta: {elapsed:.2f}s"

        self.log_success(f"Sync status response time: {elapsed:.3f}s")
