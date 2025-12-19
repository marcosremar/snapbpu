"""
Contract Tests - Fixtures
=========================

Fixtures compartilhadas para testes de contrato.
"""

import pytest
import requests
import os

# Configuração
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8766")
DEMO_USER = os.getenv("TEST_USER", "test@test.com")
DEMO_PASS = os.getenv("TEST_PASS", "test123")
TIMEOUT = 10


@pytest.fixture(scope="module")
def api_session():
    """Sessão HTTP com autenticação para testes de contrato"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })

    # Fazer login e obter token
    try:
        login_response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": DEMO_USER, "password": DEMO_PASS},
            timeout=TIMEOUT
        )

        if login_response.status_code == 200:
            data = login_response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                session.headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        print(f"Warning: Could not authenticate: {e}")

    yield session
    session.close()


@pytest.fixture(scope="module")
def base_url():
    """URL base da API"""
    return BASE_URL


@pytest.fixture
def unauthenticated_session():
    """Sessão HTTP sem autenticação"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    yield session
    session.close()
