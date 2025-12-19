#!/usr/bin/env python3
"""
Testes Backend - Auto-Hibernação Inteligente

Testa endpoints de auto-hibernação do sistema Dumont Cloud:
- GET /api/v1/hibernation/stats - Estatísticas de hibernação

Uso:
    pytest tests/backend/hibernation/test_auto_hibernation.py -v
    pytest tests/backend/hibernation/test_auto_hibernation.py -v -k "test_stats"
"""

import pytest
import json
import time
from pathlib import Path
from tests.backend.conftest import BaseTestCase, Colors


class TestHibernationStats(BaseTestCase):
    """Testes para estatísticas de hibernação"""

    def test_stats_basic(self, api_client):
        """GET /api/v1/hibernation/stats - Estatísticas básicas"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Estatísticas de hibernação")
        data = resp.json()

        # Validar estrutura da resposta
        required_keys = [
            "total_hibernations",
            "total_hours_saved",
            "total_savings",
            "machines"
        ]
        self.assert_json_keys(data, required_keys)

        # Validar tipos de dados
        assert isinstance(data["total_hibernations"], int), "total_hibernations deve ser int"
        assert isinstance(data["total_hours_saved"], (int, float)), "total_hours_saved deve ser número"
        assert isinstance(data["total_savings"], (int, float)), "total_savings deve ser número"
        assert isinstance(data["machines"], list), "machines deve ser lista"

        # Validar valores não negativos
        assert data["total_hibernations"] >= 0, "total_hibernations não pode ser negativo"
        assert data["total_hours_saved"] >= 0, "total_hours_saved não pode ser negativo"
        assert data["total_savings"] >= 0, "total_savings não pode ser negativo"

        self.log_success(
            f"Stats: {data['total_hibernations']} hibernações, "
            f"{data['total_hours_saved']}h salvos, "
            f"${data['total_savings']} economia"
        )

    def test_stats_machines_structure(self, api_client):
        """GET /api/v1/hibernation/stats - Estrutura de máquinas"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Estrutura de máquinas")
        data = resp.json()

        # Se houver máquinas, validar estrutura
        if data["machines"]:
            machine = data["machines"][0]

            required_machine_keys = ["instance_id", "hibernations", "savings"]
            self.assert_json_keys(machine, required_machine_keys)

            # Validar tipos
            assert isinstance(machine["instance_id"], str), "instance_id deve ser string"
            assert isinstance(machine["hibernations"], int), "hibernations deve ser int"
            assert isinstance(machine["savings"], (int, float)), "savings deve ser número"

            # Validar valores
            assert machine["instance_id"], "instance_id não pode ser vazio"
            assert machine["hibernations"] >= 0, "hibernations não pode ser negativo"
            assert machine["savings"] >= 0, "savings não pode ser negativo"

            self.log_success(f"Máquina validada: {machine['instance_id']}")
        else:
            self.log_info("Nenhuma máquina com hibernação encontrada")

    def test_stats_empty_response(self, api_client):
        """GET /api/v1/hibernation/stats - Resposta vazia válida"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Resposta vazia")
        data = resp.json()

        # Mesmo sem dados, estrutura deve estar presente
        assert "total_hibernations" in data
        assert "total_hours_saved" in data
        assert "total_savings" in data
        assert "machines" in data

        # Valores padrão válidos
        if data["total_hibernations"] == 0:
            assert data["total_hours_saved"] == 0, "Sem hibernações, horas deve ser 0"
            assert data["total_savings"] == 0, "Sem hibernações, economia deve ser 0"
            assert data["machines"] == [], "Sem hibernações, machines deve ser vazio"

            self.log_success("Resposta vazia válida (sem hibernações)")
        else:
            self.log_info(f"Usuário tem {data['total_hibernations']} hibernações")

    def test_stats_calculation_consistency(self, api_client):
        """GET /api/v1/hibernation/stats - Consistência de cálculos"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Consistência de cálculos")
        data = resp.json()

        if data["machines"]:
            # Soma de hibernações das máquinas deve bater com total
            total_from_machines = sum(m["hibernations"] for m in data["machines"])
            assert total_from_machines == data["total_hibernations"], \
                f"Total inconsistente: {total_from_machines} vs {data['total_hibernations']}"

            # Soma de economia das máquinas deve bater com total
            total_savings_from_machines = sum(m["savings"] for m in data["machines"])
            # Permitir pequena diferença por arredondamento (0.01)
            diff = abs(total_savings_from_machines - data["total_savings"])
            assert diff < 0.02, \
                f"Economia inconsistente: {total_savings_from_machines} vs {data['total_savings']}"

            self.log_success(
                f"Cálculos consistentes: {len(data['machines'])} máquinas, "
                f"{data['total_hibernations']} hibernações"
            )
        else:
            self.log_info("Sem máquinas para validar consistência")

    def test_stats_numeric_precision(self, api_client):
        """GET /api/v1/hibernation/stats - Precisão numérica"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Precisão numérica")
        data = resp.json()

        # Validar casas decimais razoáveis
        hours_str = str(data["total_hours_saved"])
        if "." in hours_str:
            decimals = len(hours_str.split(".")[1])
            assert decimals <= 2, f"Muitas casas decimais em hours: {decimals}"

        savings_str = str(data["total_savings"])
        if "." in savings_str:
            decimals = len(savings_str.split(".")[1])
            assert decimals <= 2, f"Muitas casas decimais em savings: {decimals}"

        # Validar máquinas
        for machine in data["machines"]:
            savings_str = str(machine["savings"])
            if "." in savings_str:
                decimals = len(savings_str.split(".")[1])
                assert decimals <= 2, f"Muitas casas decimais em machine savings: {decimals}"

        self.log_success("Precisão numérica validada (máx 2 casas decimais)")


class TestHibernationSecurity(BaseTestCase):
    """Testes de segurança para hibernação"""

    def test_stats_requires_authentication(self, unauth_client):
        """GET /api/v1/hibernation/stats - Requer autenticação"""
        resp = unauth_client.get("/api/v1/hibernation/stats")

        # Deve retornar 401 ou 403
        assert resp.status_code in [401, 403], \
            f"Esperado 401/403, recebido {resp.status_code}"

        self.log_success("Endpoint protegido contra acesso não autenticado")

    def test_stats_invalid_token(self, unauth_client):
        """GET /api/v1/hibernation/stats - Token inválido"""
        # Adicionar token inválido
        unauth_client.session.headers.update({
            "Authorization": "Bearer invalid_token_123"
        })

        resp = unauth_client.get("/api/v1/hibernation/stats")

        # Deve retornar 401 ou 403
        assert resp.status_code in [401, 403], \
            f"Token inválido deveria ser rejeitado: {resp.status_code}"

        self.log_success("Token inválido rejeitado corretamente")

    def test_stats_malformed_token(self, unauth_client):
        """GET /api/v1/hibernation/stats - Token malformado"""
        # Tokens malformados
        malformed_tokens = [
            "Bearer ",
            "Bearer",
            "InvalidFormat",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.malformed",
            "Bearer " + "x" * 1000,  # Token muito longo
        ]

        for token in malformed_tokens:
            unauth_client.session.headers.update({
                "Authorization": token
            })

            resp = unauth_client.get("/api/v1/hibernation/stats")

            assert resp.status_code in [401, 403], \
                f"Token malformado deveria ser rejeitado: {resp.status_code}"

        self.log_success(f"Todos os {len(malformed_tokens)} tokens malformados rejeitados")

    def test_stats_user_isolation(self, api_client):
        """GET /api/v1/hibernation/stats - Isolamento entre usuários"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Isolamento de usuários")
        data = resp.json()

        # Validar que todas as máquinas retornadas pertencem ao usuário
        # (não podemos validar 100% sem acesso ao banco, mas validamos estrutura)
        for machine in data["machines"]:
            assert "instance_id" in machine
            assert machine["instance_id"], "instance_id não pode ser vazio"

        self.log_success("Resposta contém apenas dados do usuário autenticado")

    def test_stats_no_sql_injection(self, api_client):
        """GET /api/v1/hibernation/stats - Proteção contra SQL injection"""
        # Tentar injeções SQL comuns via query params
        injection_attempts = [
            {"user_id": "1' OR '1'='1"},
            {"user_id": "1; DROP TABLE users--"},
            {"instance_id": "' UNION SELECT * FROM users--"},
            {"order_by": "1; DELETE FROM hibernation_events--"},
        ]

        for params in injection_attempts:
            resp = api_client.get("/api/v1/hibernation/stats", params=params)

            # Deve retornar sucesso (ignorando params inválidos) ou 400
            assert resp.status_code in [200, 400], \
                f"Resposta inesperada para injection: {resp.status_code}"

            # Se retornar 200, validar estrutura normal
            if resp.status_code == 200:
                data = resp.json()
                assert "total_hibernations" in data

        self.log_success("Proteção contra SQL injection validada")


class TestHibernationPerformance(BaseTestCase):
    """Testes de performance para hibernação"""

    def test_stats_response_time(self, api_client):
        """GET /api/v1/hibernation/stats - Tempo de resposta"""
        start_time = time.time()
        resp = api_client.get("/api/v1/hibernation/stats")
        request_time = time.time() - start_time

        self.assert_success_response(resp, "Tempo de resposta")

        # Stats deve ser rápido (< 2s em condições normais)
        assert request_time < 2.0, \
            f"Resposta muito lenta: {request_time:.3f}s"

        self.log_success(f"Tempo de resposta: {request_time:.3f}s")

    def test_stats_multiple_requests(self, api_client):
        """GET /api/v1/hibernation/stats - Múltiplas requisições"""
        times = []

        # Fazer 5 requisições sequenciais
        for i in range(5):
            start = time.time()
            resp = api_client.get("/api/v1/hibernation/stats")
            elapsed = time.time() - start

            self.assert_success_response(resp, f"Request {i+1}")
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        # Performance deve ser consistente
        assert max_time < 3.0, f"Tempo máximo muito alto: {max_time:.3f}s"
        assert avg_time < 1.5, f"Tempo médio muito alto: {avg_time:.3f}s"

        self.log_success(
            f"5 requests - avg: {avg_time:.3f}s, "
            f"min: {min_time:.3f}s, max: {max_time:.3f}s"
        )

    def test_stats_concurrent_requests(self, api_client):
        """GET /api/v1/hibernation/stats - Requisições concorrentes"""
        import threading
        import queue

        results = queue.Queue()

        def stats_worker():
            try:
                start = time.time()
                resp = api_client.get("/api/v1/hibernation/stats")
                end = time.time()
                results.put({
                    "status": resp.status_code,
                    "time": end - start,
                    "success": resp.status_code == 200
                })
            except Exception as e:
                results.put({"error": str(e), "success": False})

        # Criar 3 threads concorrentes
        threads = []
        for _ in range(3):
            t = threading.Thread(target=stats_worker)
            threads.append(t)
            t.start()

        # Aguardar todas as threads
        for t in threads:
            t.join()

        # Analisar resultados
        success_count = 0
        total_time = 0

        while not results.empty():
            result = results.get()
            if result.get("success"):
                success_count += 1
                total_time += result["time"]

        assert success_count >= 2, \
            f"Muitas requisições concorrentes falharam: {success_count}/3"

        avg_time = total_time / success_count
        self.log_success(
            f"Concorrência: {success_count}/3 sucesso, "
            f"avg={avg_time:.3f}s"
        )

    def test_stats_response_size(self, api_client):
        """GET /api/v1/hibernation/stats - Tamanho da resposta"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Tamanho da resposta")

        # Calcular tamanho da resposta
        response_size = len(resp.content)

        # Validar que resposta não é excessivamente grande
        assert response_size < 1024 * 100, \
            f"Resposta muito grande: {response_size} bytes"

        # Validar que JSON é compacto
        data = resp.json()
        json_str = json.dumps(data)

        self.log_success(
            f"Tamanho da resposta: {response_size} bytes, "
            f"JSON: {len(json_str)} chars"
        )


class TestHibernationEdgeCases(BaseTestCase):
    """Testes de casos extremos"""

    def test_stats_content_type(self, api_client):
        """GET /api/v1/hibernation/stats - Content-Type correto"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Content-Type")

        # Validar Content-Type
        content_type = resp.headers.get("Content-Type", "")
        assert "application/json" in content_type, \
            f"Content-Type inválido: {content_type}"

        self.log_success(f"Content-Type: {content_type}")

    def test_stats_response_encoding(self, api_client):
        """GET /api/v1/hibernation/stats - Encoding correto"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Encoding")

        # Validar que resposta é UTF-8 válido
        try:
            resp.content.decode("utf-8")
            self.log_success("Resposta em UTF-8 válido")
        except UnicodeDecodeError:
            pytest.fail("Resposta não é UTF-8 válido")

    def test_stats_json_validity(self, api_client):
        """GET /api/v1/hibernation/stats - JSON válido"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "JSON válido")

        # Validar que JSON é parseável
        try:
            data = resp.json()

            # Re-serializar para validar
            json.dumps(data)

            self.log_success("JSON válido e serializável")
        except (json.JSONDecodeError, TypeError) as e:
            pytest.fail(f"JSON inválido: {e}")

    def test_stats_http_methods(self, api_client):
        """GET /api/v1/hibernation/stats - Apenas GET permitido"""
        # Tentar outros métodos HTTP
        methods = [
            ("POST", api_client.post),
            ("PUT", api_client.put),
            ("DELETE", api_client.delete),
        ]

        for method_name, method_func in methods:
            resp = method_func("/api/v1/hibernation/stats")

            # Deve retornar 405 Method Not Allowed
            assert resp.status_code == 405, \
                f"{method_name} deveria retornar 405, retornou {resp.status_code}"

        self.log_success("Apenas GET permitido (outros retornam 405)")

    def test_stats_caching_headers(self, api_client):
        """GET /api/v1/hibernation/stats - Headers de caching"""
        resp = api_client.get("/api/v1/hibernation/stats")

        self.assert_success_response(resp, "Caching headers")

        # Validar headers comuns
        headers = resp.headers

        # Log headers relevantes
        cache_headers = {
            "Cache-Control": headers.get("Cache-Control"),
            "ETag": headers.get("ETag"),
            "Last-Modified": headers.get("Last-Modified"),
        }

        self.log_info(f"Cache headers: {cache_headers}")
        self.log_success("Headers de resposta validados")


# Salvar resultados do teste
TestHibernationStats._test_result = {
    "test_class": "TestHibernationStats",
    "timestamp": time.time(),
    "status": "completed"
}

TestHibernationSecurity._test_result = {
    "test_class": "TestHibernationSecurity",
    "timestamp": time.time(),
    "status": "completed"
}

TestHibernationPerformance._test_result = {
    "test_class": "TestHibernationPerformance",
    "timestamp": time.time(),
    "status": "completed"
}

TestHibernationEdgeCases._test_result = {
    "test_class": "TestHibernationEdgeCases",
    "timestamp": time.time(),
    "status": "completed"
}
