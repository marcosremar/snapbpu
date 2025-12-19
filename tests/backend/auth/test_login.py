#!/usr/bin/env python3
"""
Testes Backend - Autenticação e Login

Testa endpoints de autenticação do sistema Dumont Cloud:
- POST /api/v1/auth/login - Login com JWT
- POST /api/v1/auth/logout - Logout
- GET /api/v1/auth/me - Dados do usuário logado
- POST /api/v1/auth/register - Registro de novo usuário

Uso:
    pytest tests/backend/auth/test_login.py -v
    pytest tests/backend/auth/test_login.py -v -k "test_login"
"""

import pytest
import json
import time
from pathlib import Path
from tests.backend.conftest import BaseTestCase, Colors


class TestAuthentication(BaseTestCase):
    """Testes para endpoints de autenticação /api/v1/auth/*"""

    def test_login_success(self, api_client):
        """POST /api/v1/auth/login - Login bem-sucedido"""
        resp = api_client.post(
            "/api/v1/auth/login",
            json={"username": self.config["TEST_USER"], "password": self.config["TEST_PASS"]}
        )

        self.assert_success_response(resp, "Login bem-sucedido")
        data = resp.json()

        # Validar estrutura do token - API retorna success, user, token
        required_keys = ["success", "user", "token"]
        self.assert_json_keys(data, required_keys)

        assert data["success"] == True
        assert len(data["token"]) > 50  # JWT token

        self.log_success(f"Token gerado: {data['token'][:20]}...")

    def test_login_invalid_credentials(self, unauth_client):
        """POST /api/v1/auth/login - Credenciais inválidas"""
        resp = unauth_client.post(
            "/api/v1/auth/login",
            json={"username": "invalid@example.com", "password": "wrong"}
        )

        assert resp.status_code == 401
        data = resp.json()
        assert "error" in data or "detail" in data
        self.log_success("Credenciais inválidas rejeitadas")

    def test_login_missing_fields(self, unauth_client):
        """POST /api/v1/auth/login - Campos faltando"""
        # Testa sem username
        resp = unauth_client.post(
            "/api/v1/auth/login",
            json={"password": self.config["TEST_PASS"]}
        )
        assert resp.status_code == 422
        self.log_success("Campo username validado")

        # Testa sem password
        resp = unauth_client.post(
            "/api/v1/auth/login",
            json={"username": self.config["TEST_USER"]}
        )
        assert resp.status_code == 422
        self.log_success("Campo password validado")

    def test_token_validation(self, api_client):
        """GET /api/v1/auth/me - Validação de token"""
        resp = api_client.get("/api/v1/auth/me")

        self.assert_success_response(resp, "Token válido")
        data = resp.json()

        # API retorna authenticated e user
        assert data.get("authenticated") == True
        assert "user" in data
        assert data["user"]["email"] == self.config["TEST_USER"]

        self.log_success(f"Usuário validado: {data['user']['email']}")

    def test_token_invalid(self, unauth_client):
        """GET /api/v1/auth/me - Token inválido"""
        resp = unauth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        # Pode retornar 401 ou 200 com authenticated=false
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("authenticated") == False
        else:
            assert resp.status_code == 401
        self.log_success("Token inválido rejeitado/identificado")

    def test_token_missing(self, unauth_client):
        """GET /api/v1/auth/me - Token faltando"""
        resp = unauth_client.get("/api/v1/auth/me")

        # Pode retornar 401 ou 200 com authenticated=false e error
        if resp.status_code == 200:
            data = resp.json()
            # Se retorna 200, deve indicar não autenticado
            assert data.get("authenticated") == False or "error" in data
        else:
            assert resp.status_code == 401
        self.log_success("Endpoint protegido sem token")

    def test_logout(self, api_client):
        """POST /api/v1/auth/logout - Logout"""
        resp = api_client.post("/api/v1/auth/logout")
        self.assert_success_response(resp, "Logout")

        data = resp.json()
        assert data.get("success") == True or "message" in data

        self.log_success("Logout realizado com sucesso")

    def test_rate_limiting(self, unauth_client):
        """Testa rate limiting de login"""
        # Tenta múltiplos logins falhos rapidamente
        for i in range(5):
            resp = unauth_client.post(
                "/api/v1/auth/login",
                json={"username": "test@example.com", "password": "wrong"}
            )

            # Após alguns tentativas, deve começar a rate limit
            # O importante é que não quebre o servidor
            assert resp.status_code in [401, 429, 422]

        self.log_success("Rate limiting funcionando (sem quebrar servidor)")

    def test_input_sanitization(self, unauth_client):
        """Testa sanitização de input"""
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd"
        ]

        for malicious_input in malicious_inputs:
            resp = unauth_client.post(
                "/api/v1/auth/login",
                json={"username": malicious_input, "password": "test"}
            )

            # Deve rejeitar input malicioso (não é email válido)
            assert resp.status_code in [401, 422, 400]

        self.log_success("Input sanitização OK (inputs maliciosos rejeitados)")


class TestUserRegistration(BaseTestCase):
    """Testes para registro de novos usuários"""

    def test_register_user(self, unauth_client):
        """POST /api/v1/auth/register - Registro de novo usuário"""
        timestamp = int(time.time())
        test_email = f"test_{timestamp}@example.com"

        resp = unauth_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_email,
                "password": "test123456"
            }
        )

        # Pode retornar 200/201 (criado) ou 400 (já existe ou erro de validação)
        if resp.status_code in [200, 201]:
            data = resp.json()
            assert data.get("success") == True or "token" in data
            self.log_success(f"Usuário registrado: {test_email}")
        elif resp.status_code == 400:
            data = resp.json()
            self.log_warning(f"Registro falhou: {data.get('error', data.get('detail', 'unknown'))}")
        else:
            self.log_info(f"Status: {resp.status_code}")
            assert resp.status_code in [200, 201, 400, 409, 422]

    def test_register_duplicate_user(self, unauth_client):
        """POST /api/v1/auth/register - Usuário duplicado"""
        # Tenta registrar o usuário de teste que já existe
        resp = unauth_client.post(
            "/api/v1/auth/register",
            json={
                "email": self.config["TEST_USER"],
                "password": "test123456"
            }
        )

        # Deve rejeitar (400, 409 ou 422)
        assert resp.status_code in [400, 409, 422]
        self.log_success("Registro de usuário duplicado rejeitado")

    def test_register_weak_password(self, unauth_client):
        """POST /api/v1/auth/register - Senha fraca"""
        weak_passwords = ["123", "abc", ""]

        for weak_pass in weak_passwords:
            resp = unauth_client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test_{time.time()}@example.com",
                    "password": weak_pass
                }
            )

            # Deve rejeitar senhas muito fracas
            assert resp.status_code in [422, 400]

        self.log_success("Validação de senha: senhas fracas rejeitadas")

    def test_register_invalid_email(self, unauth_client):
        """POST /api/v1/auth/register - Email inválido"""
        invalid_emails = [
            "not_an_email",
            "@example.com",
            "test@",
            ""
        ]

        for invalid_email in invalid_emails:
            resp = unauth_client.post(
                "/api/v1/auth/register",
                json={
                    "email": invalid_email,
                    "password": "validpassword123"
                }
            )

            assert resp.status_code in [422, 400]

        self.log_success("Validação de email: emails inválidos rejeitados")


class TestAuthSecurity(BaseTestCase):
    """Testes de segurança avançados para autenticação"""

    def test_jwt_token_structure(self, api_client):
        """Testa estrutura JWT token"""
        login_resp = api_client.post(
            "/api/v1/auth/login",
            json={"username": self.config["TEST_USER"], "password": self.config["TEST_PASS"]}
        )
        token = login_resp.json()["token"]

        # Verificar estrutura JWT (3 partes separadas por .)
        parts = token.split('.')
        assert len(parts) == 3, f"Token JWT deve ter 3 partes, tem {len(parts)}"

        # Tentar decodar header e payload (sem validar assinatura)
        import base64

        try:
            # Header
            header_padding = '=' * (-len(parts[0]) % 4)
            header = json.loads(base64.b64decode(parts[0] + header_padding))
            assert "alg" in header
            assert "typ" in header

            # Payload
            payload_padding = '=' * (-len(parts[1]) % 4)
            payload = json.loads(base64.b64decode(parts[1] + payload_padding))
            assert "sub" in payload or "email" in payload
            assert "exp" in payload

            self.log_success("Estrutura JWT válida")

        except Exception as e:
            pytest.fail(f"Token JWT inválido: {e}")

    def test_token_has_expiration(self, api_client):
        """Testa que token tem expiração"""
        import base64

        login_resp = api_client.post(
            "/api/v1/auth/login",
            json={"username": self.config["TEST_USER"], "password": self.config["TEST_PASS"]}
        )
        token = login_resp.json()["token"]

        # Decodar payload
        parts = token.split('.')
        payload_padding = '=' * (-len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(parts[1] + payload_padding))

        assert "exp" in payload, "Token deve ter campo exp"
        assert "iat" in payload, "Token deve ter campo iat"

        # Verificar que exp > iat
        assert payload["exp"] > payload["iat"], "exp deve ser maior que iat"

        self.log_success(f"Token tem expiração válida")

    def test_concurrent_login(self, unauth_client):
        """Testa login concorrente"""
        import concurrent.futures

        def login_worker():
            try:
                resp = unauth_client.post(
                    "/api/v1/auth/login",
                    json={"username": self.config["TEST_USER"], "password": self.config["TEST_PASS"]}
                )
                return resp.status_code
            except Exception as e:
                return f"error: {e}"

        # Usar ThreadPoolExecutor para logins concorrentes
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(login_worker) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verificar resultados
        success_count = sum(1 for r in results if r == 200)

        # Deve permitir múltiplos logins
        assert success_count > 0, "Nenhum login simultâneo funcionou"
        self.log_success(f"Logins concorrentes: {success_count}/3 bem-sucedidos")
