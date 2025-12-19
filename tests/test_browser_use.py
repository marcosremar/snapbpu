"""
Browser Use test for Dumont Cloud system navigation
Using OpenRouter with Gemini Flash
"""
import asyncio
import os
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

# Set up the LLM with Anthropic Claude
llm = ChatAnthropic(
    model="claude-opus-4-5-20251101",
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    temperature=0.1,
)

async def test_dumont_cloud():
    """Navigate through Dumont Cloud and test functionality"""

    task = """
    Navegue pelo sistema Dumont Cloud em https://dumontcloud.com e faça um teste completo:

    1. FAZER LOGIN:
       - Acesse https://dumontcloud.com
       - Faça login com email: marcosremar@gmail.com e senha: dumont123
       - Aguarde carregar o Dashboard

    2. TESTAR DASHBOARD:
       - Verifique se o Dashboard carregou corretamente
       - Observe os cards de velocidade (Lento, Medio, Rapido, Ultra)
       - Clique em um dos cards de velocidade (por exemplo "Rapido")
       - Verifique se aparece o botão "Buscar Máquinas Disponíveis"
       - Clique no botão de buscar e veja se carrega resultados ou mostra erro

    3. TESTAR PÁGINA MACHINES:
       - Clique no menu "Machines" no topo
       - Verifique se a página carrega
       - Observe se aparece a lista de máquinas ou algum erro
       - Anote quantas máquinas aparecem e seus status

    4. TESTAR PÁGINA SETTINGS:
       - Clique no menu "Settings" no topo
       - Verifique se a página carrega
       - Observe as configurações disponíveis

    5. TESTAR PÁGINA MÉTRICAS:
       - Clique no menu "Métricas" no topo
       - Verifique se a página carrega
       - Observe os dados de métricas

    6. FAZER LOGOUT:
       - Clique no botão "Logout"
       - Verifique se volta para a tela de login

    IMPORTANTE: A cada página, descreva o que você vê.
    Se encontrar algum erro ou problema, descreva detalhadamente.

    No final, faça um RELATÓRIO completo dizendo:
    - O que funcionou
    - O que não funcionou ou apresentou erros
    - Sugestões de melhorias na interface
    """

    agent = Agent(
        task=task,
        llm=llm,
        use_vision=True,
    )

    result = await agent.run()
    print("\n" + "="*60)
    print("RESULTADO DO TESTE")
    print("="*60)
    print(result)
    return result

if __name__ == "__main__":
    asyncio.run(test_dumont_cloud())
