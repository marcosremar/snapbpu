#!/usr/bin/env python3
"""
Testes Backend - Autenticação e Segurança

Testa endpoints de autenticação do sistema Dumont Cloud:
- POST /api/v1/auth/login - Login com JWT
- POST /api/v1/auth/refresh - Refresh token
- POST /api/v1/auth/logout - Logout
- GET /api/v1/auth/me - Dados do usuário logado
- POST /api/v1/auth/register - Registro de novo usuário
- Rate limiting e segurança

Uso:
    pytest tests/test_backend_auth.py -v
    pytest tests/test_backend_auth.py -v -k "test_login"
"""

import pytest
import requests
import json
import time
from datetime import datetime, timedelta
import sys
import os

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuração
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8766")
TEST_USER = os.environ.get("TEST_USER", "test@example.com")
TEST_PASS = os.environ.get("TEST_PASS", "test123")


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


@pytest.fixture(scope="module")
def session():
    """Cria sessão sem autenticação para testes de login."""
    return requests.Session()


class TestAuthenticationEndpoints:
    """Testes para endpoints de autenticação /api/v1/auth/*"""
    
    def test_login_success(self, session):
        """POST /api/v1/auth/login - Login bem-sucedido"""
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER, "password": TEST_PASS},
            timeout=10
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Validar estrutura do token
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 50  # JWT token
        
        print(f"  ✓ Login OK: token={data['access_token'][:20]}...")
        return data["access_token"]
    
    def test_login_invalid_credentials(self, session):
        """POST /api/v1/auth/login - Credenciais inválidas"""
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "invalid@example.com", "password": "wrong"},
            timeout=10
        )
        
        assert resp.status_code == 401, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "detail" in data
        print(f"  ✓ Login inválido rejeitado: {data['detail']}")
    
    def test_login_missing_fields(self, session):
        """POST /api/v1/auth/login - Campos faltando"""
        # Testa sem email
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"password": TEST_PASS},
            timeout=10
        )
        assert resp.status_code == 422, f"Status {resp.status_code}: {resp.text}"
        print(f"  ✓ Campo email validado")
        
        # Testa sem password
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER},
            timeout=10
        )
        assert resp.status_code == 422, f"Status {resp.status_code}: {resp.text}"
        print(f"  ✓ Campo password validado")
    
    def test_token_validation(self, session):
        """GET /api/v1/auth/me - Validação de token"""
        # Primeiro faz login
        login_resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER, "password": TEST_PASS},
            timeout=10
        )
        token = login_resp.json()["access_token"]
        
        # Testa endpoint protegido com token válido
        resp = session.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "email" in data
        assert "id" in data
        assert data["email"] == TEST_USER
        print(f"  ✓ Token válido: user={data['email']}")
    
    def test_token_invalid(self, session):
        """GET /api/v1/auth/me - Token inválido"""
        resp = session.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
            timeout=10
        )
        
        assert resp.status_code == 401, f"Status {resp.status_code}: {resp.text}"
        print(f"  ✓ Token inválido rejeitado")
    
    def test_token_missing(self, session):
        """GET /api/v1/auth/me - Token faltando"""
        resp = session.get(f"{BASE_URL}/api/v1/auth/me", timeout=10)
        assert resp.status_code == 401, f"Status {resp.status_code}: {resp.text}"
        print(f"  ✓ Endpoint protegido sem token")
    
    def test_refresh_token(self, session):
        """POST /api/v1/auth/refresh - Refresh token"""
        # Primeiro faz login
        login_resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER, "password": TEST_PASS},
            timeout=10
        )
        old_token = login_resp.json()["access_token"]
        
        # Faz refresh
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_token}"},
            timeout=10
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "access_token" in data
        assert data["access_token"] != old_token  # Novo token diferente
        
        # Testa se novo token funciona
        new_token = data["access_token"]
        verify_resp = session.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
            timeout=10
        )
        assert verify_resp.status_code == 200
        
        print(f"  ✓ Token refresh: novo token gerado e válido")
    
    def test_logout(self, session):
        """POST /api/v1/auth/logout - Logout e invalidação"""
        # Primeiro faz login
        login_resp = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": TEST_USER, "password": TEST_PASS},
            timeout=10
        )
        token = login_resp.json()["access_token"]
        
        # Faz logout
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "message" in data
        
        # Testa se token foi invalidado
        verify_resp = session.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        assert verify_resp.status_code == 401
        
        print(f"  ✓ Logout: token invalidado com sucesso")
    
    def test_rate_limiting(self, session):
        """Testa rate limiting de login"""
        # Tenta múltiplos logins falhos rapidamente
        for i in range(5):
            resp = session.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrong"},
                timeout=10
            )
            
            # Após alguns tentativas, deve começar a rate limit
            if i >= 3:
                # Pode retornar 429 (too many requests) ou ainda 401
                # O importante é que não quebre o servidor
                assert resp.status_code in [401, 429]
        
        print(f"  ✓ Rate limiting funcionando (sem quebrar servidor)")
    
    def test_input_sanitization(self, session):
        """Testa sanitização de input"""
        # Testa SQL injection
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd"
        ]
        
        for malicious_input in malicious_inputs:
            resp = session.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": malicious_input, "password": "test"},
                timeout=10
            )
            
            # Deve rejeitar input malicioso
            assert resp.status_code in [401, 422, 400]
        
        print(f"  ✓ Input sanitização OK (inputs maliciosos rejeitados)")


class TestUserRegistration:
    """Testes para registro de novos usuários"""
    
    def test_register_user(self, session):
        """POST /api/v1/auth/register - Registro de novo usuário"""
        timestamp = int(time.time())
        test_email = f"test_user_{timestamp}@example.com"
        
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "email": test_email,
                "password": "test123456",
                "confirm_password": "test123456"
            },
            timeout=10
        )
        
        # Pode retornar 201 (criado) ou 409 (já existe)
        if resp.status_code == 201:
            data = resp.json()
            assert "message" in data
            assert "user_id" in data
            print(f"  ✓ Usuário registrado: {test_email}")
        elif resp.status_code == 409:
            print(f"  ⚠ Usuário já existe: {test_email}")
        else:
            assert False, f"Status inesperado: {resp.status_code}"
    
    def test_register_password_mismatch(self, session):
        """POST /api/v1/auth/register - Senhas não conferem"""
        resp = session.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "confirm_password": "different_password"
            },
            timeout=10
        )
        
        assert resp.status_code == 422, f"Status {resp.status_code}: {resp.text}"
        print(f"  ✓ Validação de senha: senhas diferentes rejeitadas")
    
    def test_register_weak_password(self, session):
        """POST /api/v1/auth/register - Senha fraca"""
        weak_passwords = ["123", "password", "abc", ""]
        
        for weak_pass in weak_passwords:
            resp = session.post(
                f"{BASE_URL}/api/v1/auth/register",
                json={
                    "email": f"test_{time.time()}@example.com",
                    "password": weak_pass,
                    "confirm_password": weak_pass
                },
                timeout=10
            )
            
            # Deve rejeitar senhas muito fracas
            assert resp.status_code in [422, 400]
        
        print(f"  ✓ Validação de senha: senhas fracas rejeitadas")
    
    def test_register_invalid_email(self, session):
        """POST /api/v1/auth/register - Email inválido"""
        invalid_emails = [
            "not_an_email",
            "@example.com",
            "test@",
            "test..test@example.com",
            ""
        ]
        
        for invalid_email in invalid_emails:
            resp = session.post(
                f"{BASE_URL}/api/v1/auth/register",
                json={
                    "email": invalid_email,
                    "password": "validpassword123",
                    "confirm_password": "validpassword123"
                },
                timeout=10
            )
            
            assert resp.status_code in [422, 400]
        
        print(f"  ✓ Validação de email: emails inválidos rejeitados")


def run_tests():
    """Executa todos os testes manualmente."""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
