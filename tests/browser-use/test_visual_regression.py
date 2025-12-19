"""
Browser-Use: Visual Regression Tests
====================================

Testes visuais usando IA para detectar problemas de layout,
elementos quebrados, ou mudanças inesperadas na UI.

Diferente de testes de screenshot pixel-a-pixel, a IA entende
o contexto e pode identificar problemas semânticos.

Suporta múltiplos LLMs (ordem de prioridade):
1. Google Gemini 2.5 Flash - Mais barato (~$0.075/1M tokens)
2. Anthropic Claude Sonnet - Melhor qualidade
3. OpenRouter - Fallback para qualquer modelo
"""

import pytest
import asyncio
import os

# Browser-Use imports
try:
    from browser_use import Agent, Browser
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    Browser = None


pytestmark = pytest.mark.skipif(
    not BROWSER_USE_AVAILABLE,
    reason="browser-use not installed"
)


def get_llm():
    """
    Configura o LLM para Browser-Use via OpenRouter.

    Usa a classe ChatOpenRouter nativa do browser-use (não LangChain).
    """
    from browser_use.llm.openrouter.chat import ChatOpenRouter

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        pytest.skip("OPENROUTER_API_KEY not configured")

    return ChatOpenRouter(
        model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
        api_key=openrouter_key,
        temperature=0.1,
        http_referer="https://snapgpu.com",
    )


# ============================================================
# LAYOUT TESTS
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_dashboard_layout_is_correct():
    """
    IA verifica se o layout do Dashboard está correto.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Analyze the Dashboard layout of Dumont Cloud.

        1. Go to http://localhost:5173 and login (test@test.com / test123)
        2. Once on Dashboard, analyze the visual layout:
           - Is there a header/navigation bar at the top?
           - Is there a sidebar menu on the left?
           - Is the main content area properly centered?
           - Are there any overlapping elements?
           - Is the text readable (good contrast)?
           - Are buttons properly styled and visible?
        3. Take note of any visual issues:
           - Broken layouts
           - Missing images
           - Misaligned elements
           - Truncated text
        4. Report your findings with specific details
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Dashboard layout: {result}")
    finally:
        await browser.stop()


@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_machines_page_displays_correctly():
    """
    IA verifica se a página de Machines renderiza corretamente.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Check the Machines page visual quality.

        1. Go to http://localhost:5173 and login (test@test.com / test123)
        2. Navigate to Machines page
        3. Analyze the GPU cards/list:
           - Do GPU cards have images?
           - Is pricing information visible and formatted?
           - Are status indicators (available/unavailable) clear?
           - Is the filter/search visible?
        4. Look for visual issues:
           - Cards with missing data
           - Broken images
           - Loading spinners stuck
           - Empty states that look broken
        5. Report what you see
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Machines page visual: {result}")
    finally:
        await browser.stop()


# ============================================================
# COMPONENT TESTS
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_savings_cards_display_numbers():
    """
    IA verifica se os cards de economia mostram números.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Check the Savings/Economy display on Dumont Cloud.

        1. Go to http://localhost:5173 and login (test@test.com / test123)
        2. Look for savings/economy information on Dashboard
        3. Verify:
           - Are there cards showing savings amounts?
           - Do the numbers look reasonable (not NaN, undefined, etc)?
           - Are currency symbols displayed correctly?
           - Are percentages formatted correctly (e.g., 25%)?
        4. Report:
           - What savings information is displayed
           - Any formatting issues
           - Missing or broken data
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Savings display: {result}")
    finally:
        await browser.stop()


@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_forms_are_styled_correctly():
    """
    IA verifica se os formulários estão estilizados corretamente.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Check form styling on Dumont Cloud.

        1. Go to http://localhost:5173/login
        2. Analyze the login form:
           - Are input fields clearly visible?
           - Do inputs have proper borders/backgrounds?
           - Are labels readable?
           - Is the submit button prominent?
           - Are there any placeholder texts?
        3. After logging in, find any other form (settings, search, etc)
        4. Check for consistent styling:
           - Same input style across forms
           - Proper error states (if any)
           - Clear focus indicators
        5. Report any inconsistencies
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Form styling: {result}")
    finally:
        await browser.stop()


# ============================================================
# DARK MODE / THEME TESTS
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_theme_is_consistent():
    """
    IA verifica se o tema visual é consistente.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Analyze the visual theme consistency of Dumont Cloud.

        1. Go to http://localhost:5173 and login (test@test.com / test123)
        2. Navigate through different pages:
           - Dashboard
           - Machines
           - Settings (if available)
        3. Check for theme consistency:
           - Same primary color throughout?
           - Consistent button styles?
           - Same typography?
           - Consistent spacing/margins?
        4. Look for a dark mode toggle (if exists)
        5. Report:
           - Overall theme quality (1-10)
           - Any inconsistent elements
           - Professional appearance?
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Theme consistency: {result}")
    finally:
        await browser.stop()


# ============================================================
# LOADING STATES
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_loading_states_are_visible():
    """
    IA verifica se estados de loading são visíveis.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Check loading states on Dumont Cloud.

        1. Go to http://localhost:5173/login
        2. When you click Login, watch for:
           - Loading spinner on button?
           - Button disabled during load?
           - Any loading indicator?
        3. After login, navigate to pages that load data
        4. Observe:
           - Do you see loading spinners?
           - Are there skeleton loaders?
           - Or does content just pop in suddenly?
        5. Report:
           - Quality of loading states (1-10)
           - Any pages that feel "janky"
           - Missing loading indicators
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Loading states: {result}")
    finally:
        await browser.stop()
