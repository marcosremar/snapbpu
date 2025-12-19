"""
Browser-Use Tests - Fixtures
============================

Fixtures compartilhadas para testes com Browser-Use (IA navegando como usuário).

Usa GCP Vertex AI com Gemini 2.5 Flash por padrão.
Fallback para OpenRouter se GCP não estiver configurado.
"""

import pytest
import os

# Configuração de URLs
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5173")
API_URL = os.getenv("TEST_API_URL", "http://localhost:8766")

# GCP Vertex AI
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# OpenRouter (fallback)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")


@pytest.fixture(scope="session")
def base_url():
    """URL base do frontend"""
    return BASE_URL


@pytest.fixture(scope="session")
def api_url():
    """URL base da API"""
    return API_URL


@pytest.fixture(scope="session")
def llm_config():
    """Configuração do LLM"""
    if GOOGLE_APPLICATION_CREDENTIALS and GCP_PROJECT_ID:
        return {
            "provider": "vertex_ai",
            "model": VERTEX_MODEL,
            "project_id": GCP_PROJECT_ID,
            "location": GCP_LOCATION
        }
    elif OPENROUTER_API_KEY:
        return {
            "provider": "openrouter",
            "model": OPENROUTER_MODEL,
            "api_key": OPENROUTER_API_KEY
        }
    else:
        pytest.skip("No LLM configured (GCP or OPENROUTER_API_KEY)")


@pytest.fixture
def skip_if_no_llm():
    """Skip test se não houver LLM configurado"""
    if not GOOGLE_APPLICATION_CREDENTIALS and not OPENROUTER_API_KEY:
        pytest.skip("No LLM configured")


def get_browser_use_llm():
    """
    Retorna o LLM configurado para Browser-Use.

    Usa a integração NATIVA do browser-use (não LangChain).

    Prioridade:
    1. OpenRouter (via browser_use.llm.openrouter.chat.ChatOpenRouter)
    2. Google Gemini (via browser_use.llm.google se API key disponível)

    Uso:
        from browser_use import Agent, Browser
        from conftest import get_browser_use_llm

        llm = get_browser_use_llm()
        agent = Agent(task="...", llm=llm)
    """
    # 1. OpenRouter (recomendado - funciona com qualquer modelo)
    if OPENROUTER_API_KEY:
        from browser_use.llm.openrouter.chat import ChatOpenRouter
        return ChatOpenRouter(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            temperature=0.1,
            http_referer="https://snapgpu.com",
        )

    # 2. Google Gemini direto (requer GOOGLE_API_KEY)
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        from browser_use.llm.google.chat import ChatGoogle
        return ChatGoogle(
            model=VERTEX_MODEL,
            api_key=google_api_key,
            temperature=0.1,
        )

    return None
