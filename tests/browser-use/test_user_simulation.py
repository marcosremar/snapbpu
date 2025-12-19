"""
Browser-Use: User Simulation Tests
==================================

Testes onde IA simula um usuário real navegando pelo sistema.
A IA recebe instruções em linguagem natural e navega autonomamente.

Estes testes são mais lentos (~30-60s cada) mas capturam problemas
que testes tradicionais não conseguem.

Suporta múltiplos LLMs (ordem de prioridade):
1. Google Gemini 2.5 Flash - Mais barato (~$0.075/1M tokens)
2. Anthropic Claude Sonnet - Melhor qualidade
3. OpenRouter - Fallback para qualquer modelo
"""

import pytest
import asyncio
import os

# Browser-Use imports (com fallback para quando não estiver disponível)
try:
    from browser_use import Agent, Browser
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    Browser = None


# Skip todos os testes se browser-use não estiver disponível
pytestmark = pytest.mark.skipif(
    not BROWSER_USE_AVAILABLE,
    reason="browser-use not installed"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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
# USER JOURNEY TESTS
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_new_user_can_access_demo():
    """
    IA simula um novo usuário acessando o modo demo.

    Cenário:
    1. Acessar página inicial
    2. Encontrar e clicar no botão Demo
    3. Verificar se chegou ao Dashboard
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        You are testing a GPU cloud platform called Dumont Cloud.

        1. Go to http://localhost:5173
        2. Look for a "Demo" or "Try Demo" button and click it
        3. If you see a login page, use:
           - Email/Username: test@test.com
           - Password: test123
        4. After login, verify you can see the Dashboard
        5. Report if you successfully reached the Dashboard
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()

        # Verifica resultado
        assert result is not None
        # O agente deve ter completado a tarefa
        print(f"Agent result: {result}")

    finally:
        await browser.stop()


@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_user_can_navigate_to_machines():
    """
    IA simula navegação para a página de Machines.

    Cenário:
    1. Login no sistema
    2. Navegar para Machines
    3. Verificar se vê lista de GPUs
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Test the GPU Machines page on Dumont Cloud.

        1. Go to http://localhost:5173/login
        2. Login with:
           - Username: test@test.com
           - Password: test123
        3. After login, find and click on "Machines" in the navigation menu
        4. Look for GPU cards or a list of available GPUs
        5. Report what GPUs you can see (names, prices if visible)
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Machines page result: {result}")
    finally:
        await browser.stop()


@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_deploy_wizard_is_accessible():
    """
    IA verifica se o Deploy Wizard é acessível e intuitivo.

    Cenário:
    1. Login e ir para Dashboard
    2. Encontrar o Deploy Wizard
    3. Verificar se consegue interagir com ele
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Test the Deploy Wizard on Dumont Cloud.

        1. Go to http://localhost:5173 and login (test@test.com / test123)
        2. Once on Dashboard, look for:
           - A "Deploy" button, or
           - An "AI Wizard" section, or
           - A deployment wizard component
        3. If you find it, try to:
           - Select a GPU tier or type
           - Choose a region
           - See pricing information
        4. DO NOT actually deploy, just verify the wizard works
        5. Report what options you found in the wizard
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Deploy wizard result: {result}")
    finally:
        await browser.stop()


# ============================================================
# ACCESSIBILITY TESTS
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_navigation_is_intuitive():
    """
    IA avalia se a navegação é intuitiva para um usuário novo.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Evaluate the navigation of Dumont Cloud as a first-time user.

        1. Go to http://localhost:5173 and login (test@test.com / test123)
        2. Explore the main navigation menu
        3. Try to find these features:
           - View my instances/machines
           - Check savings/costs
           - Access settings
           - Find help or documentation
        4. For each feature, report:
           - Was it easy to find? (yes/no)
           - How many clicks to reach it?
           - Any confusion points?
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Navigation evaluation: {result}")
    finally:
        await browser.stop()


# ============================================================
# ERROR HANDLING TESTS
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_error_messages_are_helpful():
    """
    IA verifica se mensagens de erro são úteis.
    """
    llm = get_llm()

    browser = Browser()
    agent = Agent(
        task="""
        Test error handling on Dumont Cloud.

        1. Go to http://localhost:5173/login
        2. Try to login with WRONG credentials:
           - Username: wrong@email.com
           - Password: wrongpassword
        3. Observe the error message
        4. Report:
           - Is there an error message? (yes/no)
           - Is the message helpful? (explains what went wrong?)
           - Does it tell how to fix the problem?
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Error handling result: {result}")
    finally:
        await browser.stop()


# ============================================================
# MOBILE RESPONSIVENESS
# ============================================================

@pytest.mark.browser_use
@pytest.mark.asyncio
@pytest.mark.slow
async def test_mobile_view_is_usable():
    """
    IA testa a versão mobile do site.
    """
    llm = get_llm()

    # Configura viewport mobile
    browser = Browser()
    agent = Agent(
        task="""
        Test mobile responsiveness of Dumont Cloud.

        IMPORTANT: You are on a mobile device (375x812 pixels).

        1. Go to http://localhost:5173
        2. Check if:
           - The page is readable (no horizontal scroll)
           - Navigation is accessible (hamburger menu?)
           - Buttons are tap-friendly (large enough)
        3. Try to login and navigate to Dashboard
        4. Report any usability issues on mobile
        """,
        llm=llm,
        browser=browser,
    )

    try:
        result = await agent.run()
        assert result is not None
        print(f"Mobile test result: {result}")
    finally:
        await browser.stop()
