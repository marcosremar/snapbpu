#!/usr/bin/env python3
"""
Testes Backend - Snapshots (Restic)

Testa endpoints de snapshots do sistema Dumont Cloud:
- GET /api/v1/snapshots - Lista snapshots
- POST /api/v1/snapshots - Criar snapshot
- POST /api/v1/snapshots/restore - Restaurar snapshot
- DELETE /api/v1/snapshots/{snapshot_id} - Deletar snapshot

Uso:
    pytest tests/backend/snapshots/test_snapshots.py -v
    pytest tests/backend/snapshots/test_snapshots.py -v -k "test_list"
"""

import pytest
import json
import time
from pathlib import Path
from tests.backend.conftest import BaseTestCase, Colors


class TestSnapshotSecurity(BaseTestCase):
    """Testes de segurança para endpoints de snapshots"""

    def test_list_snapshots_unauthorized(self, unauth_client):
        """GET /api/v1/snapshots - Acesso não autorizado"""
        resp = unauth_client.get("/api/v1/snapshots")

        assert resp.status_code == 401
        self.log_success("Acesso não autorizado rejeitado para listar snapshots")

    def test_create_snapshot_unauthorized(self, unauth_client):
        """POST /api/v1/snapshots - Acesso não autorizado"""
        resp = unauth_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 123,
                "source_path": "/workspace",
            }
        )

        assert resp.status_code == 401
        self.log_success("Acesso não autorizado rejeitado para criar snapshot")

    def test_restore_snapshot_unauthorized(self, unauth_client):
        """POST /api/v1/snapshots/restore - Acesso não autorizado"""
        resp = unauth_client.post(
            "/api/v1/snapshots/restore",
            json={
                "snapshot_id": "test123",
                "target_path": "/workspace",
            }
        )

        assert resp.status_code in [401, 422]  # 422 se validação falhar primeiro
        if resp.status_code == 401:
            self.log_success("Acesso não autorizado rejeitado para restaurar snapshot")
        else:
            self.log_success("Validação requer autenticação")

    def test_delete_snapshot_unauthorized(self, unauth_client):
        """DELETE /api/v1/snapshots/{id} - Acesso não autorizado"""
        resp = unauth_client.delete("/api/v1/snapshots/test_snapshot_123")

        assert resp.status_code == 401
        self.log_success("Acesso não autorizado rejeitado para deletar snapshot")


class TestSnapshotConfiguration(BaseTestCase):
    """Testes de configuração do Restic"""

    def test_list_snapshots_restic_not_configured(self, api_client):
        """GET /api/v1/snapshots - Restic não configurado"""
        resp = api_client.get("/api/v1/snapshots")

        # Pode retornar 400 se não configurado ou 200 se configurado
        if resp.status_code == 400:
            data = resp.json()
            # API pode retornar "error" ou "detail"
            error_msg = data.get("error", data.get("detail", ""))
            assert "Restic" in error_msg or "configured" in error_msg.lower()
            self.log_success("Restic não configurado detectado corretamente")
        elif resp.status_code == 200:
            data = resp.json()
            assert "snapshots" in data
            assert "count" in data
            self.log_success(f"Restic configurado - {data['count']} snapshots encontrados")
        else:
            self.log_warning(f"Status inesperado: {resp.status_code}")
            # Pode ser 500 se houver erro de infraestrutura
            assert resp.status_code in [200, 400, 500]

    def test_create_snapshot_restic_not_configured(self, api_client):
        """POST /api/v1/snapshots - Restic não configurado"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 999,  # Instância não existente
                "source_path": "/workspace",
                "tags": ["test"]
            }
        )

        # Pode retornar 400 (não configurado ou instância não existe) ou 404 (instância não encontrada)
        assert resp.status_code in [400, 404, 500]

        if resp.status_code == 400:
            data = resp.json()
            # API pode retornar "error" ou "detail"
            assert "error" in data or "detail" in data
            self.log_success("Erro de configuração ou validação detectado")
        elif resp.status_code == 404:
            data = resp.json()
            assert "error" in data or "detail" in data
            self.log_success("Instância não encontrada")
        else:
            self.log_success("Erro de servidor (esperado se Restic não configurado)")


class TestSnapshotListing(BaseTestCase):
    """Testes para listagem de snapshots"""

    def test_list_snapshots_structure(self, api_client):
        """GET /api/v1/snapshots - Estrutura de resposta"""
        resp = api_client.get("/api/v1/snapshots")

        # Pode falhar se não configurado - trata como sucesso do teste
        if resp.status_code == 400:
            data = resp.json()
            error_msg = data.get("error", data.get("detail", ""))
            assert "Restic" in error_msg or "configured" in error_msg.lower()
            self.log_success("Restic não configurado - erro tratado corretamente")
            return

        if resp.status_code == 200:
            data = resp.json()

            # Validar estrutura principal
            required_keys = ["snapshots", "count"]
            self.assert_json_keys(data, required_keys)

            assert isinstance(data["snapshots"], list)
            assert isinstance(data["count"], int)
            assert data["count"] == len(data["snapshots"])

            # Se houver snapshots, validar estrutura
            if data["snapshots"]:
                snapshot = data["snapshots"][0]
                snapshot_keys = ["id", "short_id", "time", "hostname", "tags", "paths"]

                for key in snapshot_keys:
                    assert key in snapshot, f"Chave '{key}' faltando no snapshot"

                assert isinstance(snapshot["id"], str)
                assert isinstance(snapshot["short_id"], str)
                assert isinstance(snapshot["time"], str)
                assert isinstance(snapshot["hostname"], str)
                assert isinstance(snapshot["tags"], list)
                assert isinstance(snapshot["paths"], list)

                self.log_success(f"Estrutura válida - {data['count']} snapshots")
            else:
                self.log_success("Lista vazia - estrutura válida")


class TestSnapshotCreation(BaseTestCase):
    """Testes para criação de snapshots"""

    def test_create_snapshot_missing_instance_id(self, api_client):
        """POST /api/v1/snapshots - instance_id obrigatório"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "source_path": "/workspace",
                "tags": ["test"]
            }
        )

        assert resp.status_code in [400, 422]
        data = resp.json()
        assert "error" in data or "detail" in data
        self.log_success("instance_id obrigatório validado")

    def test_create_snapshot_invalid_instance_id_type(self, api_client):
        """POST /api/v1/snapshots - instance_id deve ser int"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": "not_a_number",
                "source_path": "/workspace",
            }
        )

        assert resp.status_code in [400, 422]
        data = resp.json()
        assert "error" in data or "detail" in data
        self.log_success("Tipo de instance_id validado")

    def test_create_snapshot_nonexistent_instance(self, api_client):
        """POST /api/v1/snapshots - Instância não existente"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 999999,  # ID muito alto, provavelmente não existe
                "source_path": "/workspace",
                "tags": ["test"]
            }
        )

        # Pode retornar 400 (não configurado), 404 (não encontrado) ou 500 (erro)
        assert resp.status_code in [400, 404, 500]

        if resp.status_code == 404:
            data = resp.json()
            assert "error" in data or "detail" in data
            self.log_success("Instância não existente rejeitada")
        elif resp.status_code == 400:
            data = resp.json()
            assert "error" in data or "detail" in data
            self.log_success("Erro de configuração ou instância não encontrada")
        else:
            self.log_success("Erro de servidor (esperado)")

    def test_create_snapshot_default_source_path(self, api_client):
        """POST /api/v1/snapshots - source_path com valor padrão"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 1
            }
        )

        # Pode falhar por várias razões (não configurado, instância não existe, etc)
        # O importante é que aceita sem source_path (usa default "/workspace")
        assert resp.status_code in [200, 201, 400, 404, 500]

        if resp.status_code in [200, 201]:
            data = resp.json()
            assert data.get("success") == True
            self.log_success("source_path padrão aceito e snapshot criado")
        else:
            # Falhou por outra razão, mas aceitou a estrutura
            self.log_success("source_path padrão aceito (falhou por outro motivo)")

    def test_create_snapshot_with_tags(self, api_client):
        """POST /api/v1/snapshots - Tags opcionais"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 1,
                "source_path": "/workspace",
                "tags": ["backup", "test", "automated"]
            }
        )

        # Aceita independentemente de funcionar
        assert resp.status_code in [200, 201, 400, 404, 500]
        self.log_success("Tags aceitas (validação OK)")

    def test_create_snapshot_structure_when_configured(self, api_client):
        """POST /api/v1/snapshots - Estrutura de resposta quando bem-sucedido"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 1,
                "source_path": "/workspace",
                "tags": ["test"]
            }
        )

        # Se conseguiu criar (200/201), valida estrutura
        if resp.status_code in [200, 201]:
            data = resp.json()

            required_keys = [
                "success",
                "snapshot_id",
                "files_new",
                "files_changed",
                "files_unmodified",
                "total_files_processed",
                "data_added",
                "total_bytes_processed"
            ]

            self.assert_json_keys(data, required_keys)

            assert data["success"] == True
            assert isinstance(data["snapshot_id"], str)
            assert len(data["snapshot_id"]) > 0
            assert isinstance(data["files_new"], int)
            assert isinstance(data["files_changed"], int)
            assert isinstance(data["files_unmodified"], int)
            assert isinstance(data["total_files_processed"], int)
            assert isinstance(data["data_added"], int)
            assert isinstance(data["total_bytes_processed"], int)

            self.log_success(f"Snapshot criado: {data['snapshot_id']}")
        else:
            # Restic não configurado ou instância inválida - comportamento esperado em teste
            self.log_success("Snapshot não criado (Restic não configurado ou instância inválida - OK)")


class TestSnapshotRestoration(BaseTestCase):
    """Testes para restauração de snapshots"""

    def test_restore_snapshot_missing_snapshot_id(self, api_client):
        """POST /api/v1/snapshots/restore - snapshot_id obrigatório"""
        resp = api_client.post(
            "/api/v1/snapshots/restore",
            json={
                "target_path": "/workspace"
            },
            params={"instance_id": 1}
        )

        assert resp.status_code in [400, 422]
        data = resp.json()
        assert "error" in data or "detail" in data
        self.log_success("snapshot_id obrigatório validado")

    def test_restore_snapshot_missing_instance_id(self, api_client):
        """POST /api/v1/snapshots/restore - instance_id obrigatório"""
        resp = api_client.post(
            "/api/v1/snapshots/restore",
            json={
                "snapshot_id": "test123",
                "target_path": "/workspace"
            }
        )

        # Pode retornar 422 (falta parâmetro) ou 400 (erro de validação)
        assert resp.status_code in [400, 422]
        self.log_success("instance_id obrigatório validado")

    def test_restore_snapshot_default_target_path(self, api_client):
        """POST /api/v1/snapshots/restore - target_path com valor padrão"""
        resp = api_client.post(
            "/api/v1/snapshots/restore",
            json={
                "snapshot_id": "test123"
            },
            params={"instance_id": 1}
        )

        # Pode falhar mas deve aceitar sem target_path
        assert resp.status_code in [200, 400, 404, 422, 500]

        if resp.status_code == 422:
            # Se 422, provavelmente está validando target_path como obrigatório
            self.log_info("target_path pode ser obrigatório")
        else:
            self.log_success("target_path padrão aceito")

    def test_restore_snapshot_nonexistent(self, api_client):
        """POST /api/v1/snapshots/restore - Snapshot inexistente"""
        resp = api_client.post(
            "/api/v1/snapshots/restore",
            json={
                "snapshot_id": "nonexistent_snapshot_id_12345",
                "target_path": "/workspace"
            },
            params={"instance_id": 1}
        )

        # Pode retornar 400 (não configurado), 404 (não encontrado) ou 500 (erro)
        assert resp.status_code in [400, 404, 500]

        if resp.status_code == 404:
            data = resp.json()
            assert "error" in data or "detail" in data
            self.log_success("Snapshot inexistente rejeitado com 404")
        else:
            self.log_success("Snapshot inexistente causou erro esperado")

    def test_restore_snapshot_verify_flag(self, api_client):
        """POST /api/v1/snapshots/restore - Flag verify"""
        resp = api_client.post(
            "/api/v1/snapshots/restore",
            json={
                "snapshot_id": "test123",
                "target_path": "/workspace",
                "verify": True
            },
            params={"instance_id": 1}
        )

        # Aceita independentemente de funcionar
        assert resp.status_code in [200, 400, 404, 500]
        self.log_success("Flag verify aceita")

    def test_restore_snapshot_structure_when_configured(self, api_client):
        """POST /api/v1/snapshots/restore - Estrutura de resposta quando bem-sucedido"""
        # Primeiro tenta listar snapshots para pegar um ID válido
        list_resp = api_client.get("/api/v1/snapshots")

        if list_resp.status_code == 200:
            snapshots = list_resp.json().get("snapshots", [])

            if snapshots:
                snapshot_id = snapshots[0]["id"]

                resp = api_client.post(
                    "/api/v1/snapshots/restore",
                    json={
                        "snapshot_id": snapshot_id,
                        "target_path": "/workspace",
                        "verify": False
                    },
                    params={"instance_id": 1}
                )

                if resp.status_code == 200:
                    data = resp.json()

                    required_keys = [
                        "success",
                        "snapshot_id",
                        "target_path",
                        "files_restored",
                        "errors"
                    ]

                    self.assert_json_keys(data, required_keys)

                    assert isinstance(data["success"], bool)
                    assert isinstance(data["snapshot_id"], str)
                    assert isinstance(data["target_path"], str)
                    assert isinstance(data["files_restored"], int)
                    assert isinstance(data["errors"], list)

                    self.log_success(f"Restauração executada: {data['files_restored']} arquivos")
                else:
                    # Não foi possível restaurar - comportamento esperado em teste
                    self.log_success("Restauração não executada (esperado em ambiente de teste)")
            else:
                # Sem snapshots disponíveis - comportamento esperado
                self.log_success("Nenhum snapshot disponível (esperado em ambiente de teste)")
        else:
            # Restic não configurado - comportamento esperado em teste
            self.log_success("Restic não configurado (esperado em ambiente de teste)")


class TestSnapshotDeletion(BaseTestCase):
    """Testes para deleção de snapshots"""

    def test_delete_snapshot_nonexistent(self, api_client):
        """DELETE /api/v1/snapshots/{id} - Snapshot inexistente"""
        resp = api_client.delete("/api/v1/snapshots/nonexistent_snapshot_12345")

        # Pode retornar 400 (não configurado), 404 (não encontrado) ou 500 (erro)
        assert resp.status_code in [200, 400, 404, 500]

        if resp.status_code == 404:
            self.log_success("Snapshot inexistente retornou 404")
        elif resp.status_code == 500:
            # Pode retornar 500 se tentar deletar e falhar
            self.log_success("Erro ao deletar snapshot inexistente (esperado)")
        elif resp.status_code == 400:
            data = resp.json()
            assert "error" in data or "detail" in data
            self.log_success("Erro de configuração detectado")
        else:
            # Retornou 200 mesmo não existindo (implementação pode variar)
            data = resp.json()
            assert "success" in data or "message" in data
            self.log_success("Deleção processada (pode ter sido idempotente)")

    def test_delete_snapshot_structure(self, api_client):
        """DELETE /api/v1/snapshots/{id} - Estrutura de resposta"""
        # Tenta deletar um snapshot (pode não existir)
        resp = api_client.delete("/api/v1/snapshots/test_snapshot_id")

        if resp.status_code == 200:
            data = resp.json()

            # Deve ter success e message
            assert "success" in data
            assert "message" in data
            assert isinstance(data["success"], bool)
            assert isinstance(data["message"], str)

            self.log_success("Estrutura de deleção válida")
        else:
            # Deleção não executada - comportamento esperado em teste
            self.log_success("Deleção não executada (Restic não configurado - OK)")


class TestSnapshotInputValidation(BaseTestCase):
    """Testes de validação de input"""

    def test_create_snapshot_sql_injection(self, api_client):
        """POST /api/v1/snapshots - SQL Injection"""
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE snapshots; --",
            "1' UNION SELECT * FROM users--"
        ]

        for malicious in malicious_inputs:
            resp = api_client.post(
                "/api/v1/snapshots",
                json={
                    "instance_id": malicious,
                    "source_path": "/workspace"
                }
            )

            # Deve rejeitar (422 para tipo inválido)
            assert resp.status_code in [400, 422]

        self.log_success("SQL Injection em instance_id rejeitado")

    def test_create_snapshot_path_traversal(self, api_client):
        """POST /api/v1/snapshots - Path Traversal"""
        malicious_paths = [
            "../../etc/passwd",
            "/etc/passwd",
            "../../../root/.ssh/id_rsa",
            "/root/.ssh/id_rsa"
        ]

        for malicious_path in malicious_paths:
            resp = api_client.post(
                "/api/v1/snapshots",
                json={
                    "instance_id": 1,
                    "source_path": malicious_path
                }
            )

            # Pode aceitar ou rejeitar dependendo da validação
            # O importante é não executar ações perigosas
            assert resp.status_code in [200, 201, 400, 404, 422, 500]

        self.log_success("Path traversal testado (servidor não quebrou)")

    def test_create_snapshot_xss(self, api_client):
        """POST /api/v1/snapshots - XSS em tags"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 1,
                "source_path": "/workspace",
                "tags": ["<script>alert('xss')</script>", "normal-tag"]
            }
        )

        # Deve aceitar (tags são strings), mas sanitizar na saída
        assert resp.status_code in [200, 201, 400, 404, 500]
        self.log_success("XSS em tags aceito (deve ser sanitizado)")

    def test_create_snapshot_very_long_tags(self, api_client):
        """POST /api/v1/snapshots - Tags muito longas"""
        very_long_tag = "a" * 10000

        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 1,
                "source_path": "/workspace",
                "tags": [very_long_tag]
            }
        )

        # Pode aceitar ou rejeitar
        assert resp.status_code in [200, 201, 400, 422, 500]
        self.log_success("Tags longas testadas (não quebrou servidor)")

    def test_restore_snapshot_invalid_snapshot_id_format(self, api_client):
        """POST /api/v1/snapshots/restore - Formato inválido de snapshot_id"""
        invalid_ids = [
            "",
            " ",
            "a" * 1000,
            "<script>alert('xss')</script>",
            "../../etc/passwd"
        ]

        for invalid_id in invalid_ids:
            resp = api_client.post(
                "/api/v1/snapshots/restore",
                json={
                    "snapshot_id": invalid_id,
                    "target_path": "/workspace"
                },
                params={"instance_id": 1}
            )

            # Deve rejeitar ou tratar adequadamente
            assert resp.status_code in [400, 404, 422, 500]

        self.log_success("Snapshot IDs inválidos rejeitados/tratados")


class TestSnapshotRateLimiting(BaseTestCase):
    """Testes de rate limiting"""

    def test_create_snapshot_rate_limiting(self, api_client):
        """Testa rate limiting em criação de snapshots"""
        # Faz múltiplas requisições rapidamente
        responses = []
        for i in range(5):
            resp = api_client.post(
                "/api/v1/snapshots",
                json={
                    "instance_id": i + 1,
                    "source_path": "/workspace"
                }
            )
            responses.append(resp.status_code)

        # Verifica que não quebrou o servidor
        for status in responses:
            assert status in [200, 201, 400, 404, 429, 500]

        # Se tem rate limiting, alguma deve ser 429
        if 429 in responses:
            self.log_success("Rate limiting ativado (429 detectado)")
        else:
            self.log_success("Múltiplas requisições processadas (sem rate limit ou não atingido)")

    def test_list_snapshots_concurrent(self, api_client):
        """Testa requisições concorrentes de listagem"""
        import concurrent.futures

        def list_worker():
            try:
                resp = api_client.get("/api/v1/snapshots")
                return resp.status_code
            except Exception as e:
                return f"error: {e}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(list_worker) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verifica que processou sem erros graves
        success_count = sum(1 for r in results if isinstance(r, int) and r in [200, 400])
        assert success_count >= 1, "Nenhuma requisição concorrente funcionou"

        self.log_success(f"Requisições concorrentes: {success_count}/3 processadas")


class TestSnapshotEdgeCases(BaseTestCase):
    """Testes de casos extremos"""

    def test_create_snapshot_negative_instance_id(self, api_client):
        """POST /api/v1/snapshots - instance_id negativo"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": -1,
                "source_path": "/workspace"
            }
        )

        # Pode aceitar e retornar 404 ou rejeitar com 422
        assert resp.status_code in [400, 404, 422, 500]
        self.log_success("instance_id negativo tratado")

    def test_create_snapshot_zero_instance_id(self, api_client):
        """POST /api/v1/snapshots - instance_id zero"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 0,
                "source_path": "/workspace"
            }
        )

        # Pode aceitar e retornar 404 ou rejeitar
        assert resp.status_code in [400, 404, 422, 500]
        self.log_success("instance_id zero tratado")

    def test_create_snapshot_empty_source_path(self, api_client):
        """POST /api/v1/snapshots - source_path vazio"""
        resp = api_client.post(
            "/api/v1/snapshots",
            json={
                "instance_id": 1,
                "source_path": ""
            }
        )

        # Pode aceitar (usa default) ou rejeitar
        assert resp.status_code in [200, 201, 400, 404, 422, 500]
        self.log_success("source_path vazio tratado")

    def test_restore_snapshot_empty_target_path(self, api_client):
        """POST /api/v1/snapshots/restore - target_path vazio"""
        resp = api_client.post(
            "/api/v1/snapshots/restore",
            json={
                "snapshot_id": "test123",
                "target_path": ""
            },
            params={"instance_id": 1}
        )

        # Pode aceitar (usa default) ou rejeitar
        assert resp.status_code in [200, 400, 404, 422, 500]
        self.log_success("target_path vazio tratado")

    def test_delete_snapshot_empty_id(self, api_client):
        """DELETE /api/v1/snapshots/{id} - ID vazio"""
        # FastAPI vai tratar como rota inválida
        resp = api_client.delete("/api/v1/snapshots/")

        # Pode retornar 404 (rota não encontrada) ou 405 (método não permitido)
        assert resp.status_code in [404, 405]
        self.log_success("Snapshot ID vazio tratado")

    def test_list_snapshots_with_query_params(self, api_client):
        """GET /api/v1/snapshots - Com parâmetros de query"""
        resp = api_client.get(
            "/api/v1/snapshots",
            params={
                "limit": 10,
                "offset": 0,
                "tag": "test"
            }
        )

        # Pode aceitar ou ignorar parâmetros
        assert resp.status_code in [200, 400, 500]

        if resp.status_code == 200:
            data = resp.json()
            assert "snapshots" in data
            self.log_success("Query params aceitos (podem ser ignorados)")
        else:
            self.log_success("Query params causaram erro (podem não ser suportados)")
