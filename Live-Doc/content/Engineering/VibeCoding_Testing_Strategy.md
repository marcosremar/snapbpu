# 🚀 VibeCoding Testing Strategy - Dumont Cloud

## Filosofia: Máximo Impacto, Mínimo Tempo

Em VibeCoding, o objetivo é **validar rapidamente** que o sistema funciona para o usuário final.
Não precisamos de 100% de cobertura - precisamos de **100% de confiança nos fluxos críticos**.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIRÂMIDE VIBECODING                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    🤖 AI Visual Tests                           │
│                   (UI-TARS + Browser-Use)                       │
│                      "Está bonito?"                             │
│                         10%                                     │
│                                                                 │
│              ┌─────────────────────────────┐                    │
│              │    🔄 E2E User Journeys     │                    │
│              │  (Playwright + API Mocks)   │                    │
│              │   "Fluxo completo funciona?"│                    │
│              │           20%               │                    │
│              └─────────────────────────────┘                    │
│                                                                 │
│         ┌───────────────────────────────────────┐               │
│         │      🎯 Critical Path API Tests       │               │
│         │        (Pytest + Demo Provider)       │               │
│         │      "Endpoints críticos OK?"         │               │
│         │               30%                     │               │
│         └───────────────────────────────────────┘               │
│                                                                 │
│    ┌─────────────────────────────────────────────────┐          │
│    │           ⚡ Smoke Tests (Always Run)           │          │
│    │         Health + Auth + Demo Mode               │          │
│    │              "Sistema vivo?"                    │          │
│    │                   40%                           │          │
│    └─────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Estado Atual vs Proposto

| Aspecto | Atual | Proposto | Benefício |
|---------|-------|----------|-----------|
| **Smoke Tests** | 0 | 10 testes | Validação em <10s |
| **E2E UI↔API** | 0 | 5 jornadas | Confiança total |
| **Demo Provider** | 40% | 100% | Demo funcional |
| **Browser-Use** | 0 | 3 cenários | IA testa como humano |
| **UI-TARS** | 88 | 88 (mantém) | Já excelente |
| **Backend API** | 218 | 218 (mantém) | Já completo |

---

## 🎯 Estratégia em 4 Camadas

### Camada 1: Smoke Tests (Sempre Rodam - 10s)

```bash
# Roda antes de QUALQUER commit
pytest tests/smoke/ -v --timeout=10
```

**Testes Essenciais:**
1. ✅ Backend está vivo (`/health`)
2. ✅ Login funciona (demo user)
3. ✅ Demo mode ativo
4. ✅ Frontend carrega (200 OK)
5. ✅ API retorna ofertas

### Camada 2: Critical Path (Pré-Deploy - 2min)

```bash
# Roda antes de deploy
pytest tests/backend/ -v -m critical --timeout=120
```

**Fluxos Críticos:**
1. 🔐 Auth completo (login → token → refresh → logout)
2. 🖥️ Busca GPU → Filtros → Resultados
3. 💰 Dashboard → Savings → Métricas
4. 🔄 Standby → Configure → Status
5. 📸 Snapshots → List (erro tratado se não configurado)

### Camada 3: E2E com Playwright Agents (Nightly - 10min)

```bash
# Inicializar Playwright Agents
npx playwright init-agents --loop=claude

# Roda toda noite ou antes de release
npx playwright test tests/e2e-journeys/ --workers=1
```

**🎭 Playwright Test Agents (RECOMENDADO):**

| Agente | Função | Benefício |
|--------|--------|-----------|
| 🎭 **Planner** | Explora app e cria test plan em Markdown | Geração automática |
| 🎭 **Generator** | Converte plan em código Playwright | Zero esforço manual |
| 🎭 **Healer** | Auto-corrige testes que falharam | Self-healing nativo |

**Por que Playwright Agents > Midscene.js:**
- ⚡ **Velocidade**: Código nativo (~2s) vs API calls (~45s/teste)
- 🔧 **Self-Healing**: Healer Agent corrige locators automaticamente
- 📝 **Geração**: Planner + Generator criam testes a partir de exploração
- 🏢 **Oficial Microsoft**: Suporte garantido

**Jornadas Completas:**
1. **Novo Usuário**: Landing → Demo → Dashboard → Explorar
2. **ML Researcher**: Login → Buscar GPU → Ver Preços → Deploy
3. **Operador**: Login → Máquinas → Pausar → Resumir → Migrar
4. **Admin**: Login → Settings → Configurar Standby → Verificar

### Camada 4: AI Visual (Weekly - 5min)

```bash
# Roda semanalmente ou após mudanças de UI
python tests/ui-tars-test/ui_tars_comprehensive_test.py
python tests/browser-use/visual_regression.py
```

**Validações Visuais:**
1. 🎨 Layout não quebrou
2. 📱 Mobile responsivo
3. ♿ Acessibilidade básica
4. ⚡ Performance aceitável

---

## 🔧 Implementações Necessárias

### 1. Completar Demo Provider (CRÍTICO)

```python
# src/infrastructure/providers/demo_provider.py
# Adicionar métodos faltantes para demo funcionar 100%

class DemoProvider(IGpuProvider):
    # ✅ Já implementado
    def search_offers(...) -> List[GpuOffer]
    def list_instances() -> List[Instance]
    def get_balance() -> Dict

    # ❌ FALTA IMPLEMENTAR
    def create_instance(self, offer_id: int, **kwargs) -> Instance:
        """Simula criação - retorna instância fake"""
        return Instance(
            id=f"demo-{random.randint(1000,9999)}",
            status="running",
            gpu_name=self._get_offer_gpu(offer_id),
            created_at=datetime.now(),
            # ... outros campos
        )

    def destroy_instance(self, instance_id: str) -> bool:
        """Simula destroy - sempre sucesso"""
        return True

    def pause_instance(self, instance_id: str) -> bool:
        """Simula pause - sempre sucesso"""
        return True

    def resume_instance(self, instance_id: str) -> bool:
        """Simula resume - sempre sucesso"""
        return True
```

### 2. Criar Smoke Tests

```python
# tests/smoke/test_smoke.py
"""
Smoke Tests - Validação rápida do sistema
Tempo máximo: 10 segundos
"""
import pytest
import requests

BASE_URL = "http://localhost:8766"

class TestSmoke:
    """Testes que SEMPRE devem passar"""

    @pytest.mark.smoke
    def test_backend_alive(self):
        """Backend responde"""
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        assert resp.status_code == 200

    @pytest.mark.smoke
    def test_demo_login(self):
        """Login demo funciona"""
        resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "test@test.com", "password": "test123"},
            timeout=5
        )
        assert resp.status_code == 200
        assert "token" in resp.json()

    @pytest.mark.smoke
    def test_demo_mode_active(self):
        """Demo mode retorna ofertas"""
        resp = requests.get(
            f"{BASE_URL}/api/v1/instances/offers?demo=true",
            timeout=5
        )
        # 200 = ofertas, 500/503 = API externa (OK em demo)
        assert resp.status_code in [200, 500, 503]

    @pytest.mark.smoke
    def test_frontend_loads(self):
        """Frontend carrega"""
        resp = requests.get("http://localhost:5173", timeout=5)
        assert resp.status_code == 200
```

### 3. Criar E2E User Journeys

```javascript
// tests/e2e-journeys/new-user-journey.spec.js
const { test, expect } = require('@playwright/test');

test.describe('Jornada: Novo Usuário', () => {

  test('Landing → Demo → Dashboard → Explorar', async ({ page }) => {
    // 1. Chega na landing
    await page.goto('/');
    await expect(page.locator('text=Dumont Cloud')).toBeVisible();

    // 2. Clica em "Try Demo"
    await page.click('button:has-text("Demo")');

    // 3. Verifica redirecionamento para dashboard
    await expect(page).toHaveURL(/.*dashboard/);

    // 4. Vê cards de economia
    await expect(page.locator('[data-testid="savings-card"]')).toBeVisible();

    // 5. Navega para Machines
    await page.click('text=Machines');
    await expect(page).toHaveURL(/.*machines/);

    // 6. Vê lista de GPUs
    await expect(page.locator('[data-testid="gpu-list"]')).toBeVisible();

    // 7. Usa filtro
    await page.fill('[data-testid="gpu-search"]', 'RTX 4090');
    await page.waitForTimeout(500); // Debounce

    // 8. Verifica resultados filtrados
    const gpuCards = page.locator('[data-testid="gpu-card"]');
    await expect(gpuCards.first()).toContainText('4090');
  });

});
```

### 4. Integrar Browser-Use

```python
# tests/browser-use/user_simulation.py
"""
Browser-Use: IA simula usuário real
"""
from browser_use import Agent, Browser

async def test_deploy_wizard_flow():
    """IA navega pelo Deploy Wizard como usuário"""

    browser = Browser()
    agent = Agent(
        task="""
        1. Vá para http://localhost:5173
        2. Clique no botão de Demo
        3. No Dashboard, encontre o Deploy Wizard
        4. Selecione o tier "Rápido"
        5. Escolha região "US East"
        6. Clique em "Ver Ofertas"
        7. Verifique se apareceram GPUs disponíveis
        8. Tire screenshot do resultado
        """,
        llm=your_llm,  # Claude, GPT-4, etc
        browser=browser
    )

    result = await agent.run()

    # Validações
    assert "GPUs disponíveis" in result.final_state
    assert result.screenshots[-1].contains("ofertas")
```

---

## 📁 Estrutura Proposta

```
tests/
├── smoke/                          # ⚡ Smoke tests (10s)
│   ├── conftest.py
│   └── test_smoke.py              # 5 testes essenciais
│
├── backend/                        # 🎯 API tests (existente)
│   ├── conftest.py                # Framework base
│   ├── auth/                      # 16 testes
│   ├── instances/                 # 22 testes
│   ├── standby/                   # 27 testes
│   └── ...                        # Total: 218 testes
│
├── e2e-journeys/                   # 🔄 User journeys (NOVO)
│   ├── new-user-journey.spec.js
│   ├── ml-researcher-journey.spec.js
│   ├── operator-journey.spec.js
│   └── admin-journey.spec.js
│
├── browser-use/                    # 🤖 AI automation (NOVO)
│   ├── user_simulation.py
│   ├── visual_regression.py
│   └── accessibility_check.py
│
├── ui-tars-test/                   # 👁️ Visual AI (existente)
│   ├── ui_tars_comprehensive_test.py
│   └── ...
│
└── playwright/                     # 🎭 UI tests (existente)
    ├── dashboard.spec.js
    ├── machines.spec.js
    └── ...                        # 50 specs
```

---

## ⏱️ Pipeline de Execução

```
┌─────────────────────────────────────────────────────────────────┐
│                     QUANDO RODAR O QUÊ                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📝 A cada SAVE (hot reload):                                   │
│     └── Nada (deixa o dev em paz)                               │
│                                                                 │
│  💾 A cada COMMIT:                                              │
│     └── Smoke Tests (10s)                                       │
│         pytest tests/smoke/ -v --timeout=10                     │
│                                                                 │
│  🚀 A cada PUSH/PR:                                             │
│     └── Smoke + Critical Path (2min)                            │
│         pytest tests/smoke/ tests/backend/ -v -m "smoke or critical" │
│                                                                 │
│  🌙 NIGHTLY (3am):                                              │
│     └── Tudo (15min)                                            │
│         pytest tests/ -v                                        │
│         npx playwright test                                     │
│                                                                 │
│  📦 Antes de RELEASE:                                           │
│     └── Tudo + AI Visual (20min)                                │
│         pytest tests/ -v                                        │
│         npx playwright test                                     │
│         python tests/ui-tars-test/ui_tars_comprehensive_test.py │
│         python tests/browser-use/visual_regression.py           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Markers para Pytest

```python
# pytest.ini ou pyproject.toml
[tool.pytest.ini_options]
markers = [
    "smoke: Testes rápidos que sempre devem passar",
    "critical: Fluxos críticos do negócio",
    "slow: Testes lentos (>5s)",
    "e2e: Testes end-to-end",
    "visual: Testes visuais com IA",
    "demo: Testes específicos do modo demo",
]
```

**Uso:**
```bash
# Só smoke
pytest -m smoke

# Smoke + Critical
pytest -m "smoke or critical"

# Tudo menos slow
pytest -m "not slow"

# Só E2E
pytest -m e2e
```

---

## 🤖 LLMs Recomendados para Playwright Agents

### Via OpenRouter (Recomendado)

Pesquisa de mercado 2025 identificou os melhores modelos:

| Modelo | Performance | Custo | Recomendação |
|--------|-------------|-------|--------------|
| **Claude Sonnet 4** | ⭐⭐⭐⭐⭐ (77.2% SWE-bench) | $3/$15 per 1M tokens | 🏆 **MELHOR para Agentic Coding** |
| **Claude Sonnet 4.5** | ⭐⭐⭐⭐⭐ | $3/$15 per 1M tokens | 🥇 Mais recente, melhor reasoning |
| **Qwen 2.5 VL 72B** | ⭐⭐⭐⭐ | ~$0.20/$0.20 per 1M tokens | 💰 **MELHOR CUSTO-BENEFÍCIO** |
| **GPT-4o** | ⭐⭐⭐⭐ | $5/$15 per 1M tokens | ✅ Estável e confiável |
| **DeepSeek V3** | ⭐⭐⭐⭐ | ~$0.14/$0.28 per 1M tokens | 💸 Mais barato, bom para volume |

### Configuração com OpenRouter

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=anthropic/claude-sonnet-4

# Ou para economia:
# OPENROUTER_MODEL=qwen/qwen-2.5-vl-72b-instruct
```

### Inicializar Playwright Agents

```bash
# Com Claude (recomendado)
npx playwright init-agents --loop=claude

# Com VS Code + Copilot
npx playwright init-agents --loop=vscode

# Com OpenCode (OpenRouter)
npx playwright init-agents --loop=opencode
```

### Por que Claude Sonnet 4?

> "Sonnet 4 is considered the best model in agentic coding. Note that it doesn't mean it is the greatest at generating code, it also excels at choosing the right tools for the task."
> — Awesome Testing, 2025

**Vantagens:**
1. **Visually grounded** - Entende UI screenshots
2. **Instruction following** - Segue specs precisamente
3. **Planning** - Excelente em criar test plans
4. **Tool use** - Sabe quando usar cada ferramenta

### Alternativa Econômica: Qwen 2.5 VL 72B

Para projetos com orçamento limitado:
- **15x mais barato** que Claude
- **Performance comparável** para tarefas simples
- **Self-hostable** para privacidade
- **Visually grounded** (entende screenshots)

```bash
# Via OpenRouter
OPENROUTER_MODEL=qwen/qwen-2.5-vl-72b-instruct
```

---

## 🔮 Coisas "Mágicas" para Adicionar

### 1. Auto-Healing Tests
```python
# Se um seletor quebrar, IA encontra o novo
@auto_heal
def test_click_deploy_button(page):
    page.click('[data-testid="deploy-btn"]')  # Se falhar, IA busca alternativa
```

### 2. Screenshot Diff Automático
```python
# Compara screenshots e alerta se mudou muito
@visual_regression(threshold=0.05)  # 5% de diferença tolerada
def test_dashboard_visual(page):
    page.goto('/dashboard')
    page.screenshot(path='dashboard.png')
```

### 3. Performance Budget
```python
# Falha se performance degradar
@performance_budget(
    first_contentful_paint=1500,  # ms
    largest_contentful_paint=2500,
    time_to_interactive=3000
)
def test_dashboard_performance(page):
    page.goto('/dashboard')
```

### 4. Chaos Testing (Opcional)
```python
# Simula falhas para testar resiliência
@chaos_test(
    kill_backend_probability=0.1,
    slow_network_probability=0.2
)
def test_system_resilience(page):
    # Sistema deve se recuperar graciosamente
    pass
```

---

## 📈 Métricas de Sucesso

| Métrica | Meta | Como Medir |
|---------|------|------------|
| **Smoke Pass Rate** | 100% | CI/CD |
| **Critical Path Pass Rate** | >98% | CI/CD |
| **E2E Journey Pass Rate** | >95% | Nightly |
| **Tempo de Smoke** | <10s | CI/CD |
| **Tempo Total de Testes** | <15min | Nightly |
| **Cobertura Fluxos Críticos** | 100% | Manual review |

---

## 🚀 Implementação Rápida (VibeCoding Style)

### Fase 1: Hoje (2h)
1. ✅ Criar `tests/smoke/test_smoke.py` com 5 testes
2. ✅ Adicionar markers no `pytest.ini`
3. ✅ Testar: `pytest -m smoke`

### Fase 2: Esta Semana (4h)
1. 🔄 Completar Demo Provider (métodos faltantes)
2. 🔄 Criar 2 E2E journeys em Playwright
3. 🔄 Configurar CI para rodar smoke em PRs

### Fase 3: Próxima Semana (4h)
1. 📋 Adicionar Browser-Use para 1 cenário
2. 📋 Configurar nightly run completo
3. 📋 Dashboard de métricas de testes

---

## 💡 Dicas VibeCoding para Testes

1. **Não teste tudo** - Teste o que quebra o usuário
2. **Smoke primeiro** - Se smoke falha, nada mais importa
3. **Demo é rei** - Se demo não funciona, cliente não compra
4. **IA para visual** - Humano não deveria verificar pixels
5. **Falhe rápido** - Timeout agressivo nos testes
6. **Paralelize** - Testes devem ser independentes
7. **Mock externo** - Não dependa de Vast.ai/GCP nos testes

---

**Última atualização**: 2025-12-19
**Autor**: Engineering Team
**Filosofia**: "Se o usuário consegue fazer, o teste consegue verificar"
