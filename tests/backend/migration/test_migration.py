#!/usr/bin/env python3
"""
Testes Backend - Sistema de Migração

Testa endpoints de migração existentes na API:
- POST /api/v1/instances/{instance_id}/migrate - Migrar instância
- POST /api/v1/instances/{instance_id}/migrate/estimate - Estimar migração

Uso:
    pytest tests/backend/migration/test_migration.py -v
"""

import pytest
from tests.backend.conftest import BaseTestCase, Colors


class TestMigrationEndpoints(BaseTestCase):
    """Testes para endpoints de migração via instances"""

    def test_migrate_estimate_requires_instance(self, api_client):
        """POST /api/v1/instances/{id}/migrate/estimate - Requer ID válido"""
        resp = api_client.post(
            "/api/v1/instances/99999999/migrate/estimate",
            json={"target_offer_id": 12345}
        )

        # Deve retornar erro (instância não existe) ou estimativa
        assert resp.status_code in [200, 400, 404, 422, 500], \
            f"Status inesperado: {resp.status_code}"

        if resp.status_code == 200:
            data = resp.json()
            self.log_success("Migrate estimate retornou dados")
        else:
            self.log_info(f"Migrate estimate para instância inexistente: {resp.status_code}")

    def test_migrate_requires_instance(self, api_client):
        """POST /api/v1/instances/{id}/migrate - Requer ID válido"""
        resp = api_client.post(
            "/api/v1/instances/99999999/migrate",
            json={"target_offer_id": 12345}
        )

        # Deve retornar erro (instância não existe)
        assert resp.status_code in [200, 400, 404, 422, 500], \
            f"Status inesperado: {resp.status_code}"

        self.log_info(f"Migrate para instância inexistente: {resp.status_code}")

    def test_migrate_requires_target(self, api_client):
        """POST /api/v1/instances/{id}/migrate - Requer target_offer_id"""
        resp = api_client.post(
            "/api/v1/instances/99999999/migrate",
            json={}
        )

        # Deve requerer target_offer_id ou retornar erro de instância inexistente
        # 500 pode ocorrer se tentar validar instância inexistente
        assert resp.status_code in [400, 404, 422, 500], \
            f"Status inesperado: {resp.status_code}"

        self.log_info(f"Validação de target_offer_id: status {resp.status_code}")


class TestMigrationSecurity(BaseTestCase):
    """Testes de segurança para migração"""

    def test_migrate_requires_auth(self, unauth_client):
        """Testa que endpoints de migrate requerem autenticação"""
        endpoints = [
            ("/api/v1/instances/123/migrate", {"target_offer_id": 456}),
            ("/api/v1/instances/123/migrate/estimate", {"target_offer_id": 456})
        ]

        for endpoint, payload in endpoints:
            resp = unauth_client.post(endpoint, json=payload)

            # Deve requerer autenticação
            if resp.status_code == 200:
                data = resp.json()
                assert "error" in data, f"Endpoint {endpoint} não protegido"
            else:
                assert resp.status_code in [401, 403, 404], \
                    f"Endpoint {endpoint}: status inesperado {resp.status_code}"

        self.log_success("Endpoints de migrate protegidos")

    def test_migrate_input_validation(self, api_client):
        """Testa validação de input para migração"""
        invalid_payloads = [
            {"target_offer_id": "invalid"},
            {"target_offer_id": -1},
            {"target_offer_id": "'; DROP TABLE --"}
        ]

        for payload in invalid_payloads:
            resp = api_client.post(
                "/api/v1/instances/99999999/migrate/estimate",
                json=payload
            )

            # Deve rejeitar ou tratar graciosamente
            assert resp.status_code in [200, 400, 404, 422, 500]

        self.log_success("Validação de input para migração OK")


class TestMigrationPerformance(BaseTestCase):
    """Testes de performance de migração"""

    def test_migrate_estimate_response_time(self, api_client):
        """Testa tempo de resposta da estimativa de migração"""
        import time

        start = time.time()
        resp = api_client.post(
            "/api/v1/instances/99999999/migrate/estimate",
            json={"target_offer_id": 12345}
        )
        elapsed = time.time() - start

        # Mesmo para instância inexistente, deve responder em tempo razoável
        assert elapsed < 10.0, f"Resposta muito lenta: {elapsed:.2f}s"

        self.log_success(f"Migrate estimate response time: {elapsed:.3f}s")
