# 🚀 Plano de Implementação - Prioridades Dumont Cloud

> **Objetivo**: Implementar as features de maior impacto para criar "aha moments" e aumentar conversão/retenção.
> 
> **Data**: Dezembro 2024
> **Estimativa Total**: 4-6 semanas

---

## 📊 Visão Geral das Sprints

| Sprint | Feature | Duração | Impacto |
|--------|---------|---------|---------|
| Sprint 1 | Dashboard de Economia em Tempo Real | 1-2 semanas | 🔥🔥🔥 |
| Sprint 2 | AI GPU Advisor | 1-2 semanas | 🔥🔥🔥 |
| Sprint 3 | Onboarding Guiado | 1 semana | 🔥🔥 |
| Sprint 4 | Métricas de Auto-Hibernação | 1 semana | 🔥🔥 |

---

# 📈 SPRINT 1: Dashboard de Economia em Tempo Real

## 1.1 Objetivo
Mostrar ao usuário, em tempo real e de forma visual, quanto ele está economizando comparado aos grandes cloud providers (AWS, GCP, Azure).

## 1.2 Por que é Prioridade #1?
- ✅ É a **proposta de valor central** do produto
- ✅ Reforça a decisão do usuário a cada login
- ✅ Cria conteúdo compartilhável (screenshots)
- ✅ Os dados já existem no sistema
- ✅ Baixa complexidade técnica, alto impacto visual

---

## 1.3 Checklist de Implementação

### 📦 Backend - Coleta de Dados

#### 1.3.1 Modelo de Dados para Tracking de Uso
- [ ] Criar tabela/collection `usage_records`
  ```python
  # Estrutura do registro de uso
  {
    "id": "uuid",
    "user_id": "string",
    "machine_id": "string",
    "gpu_type": "RTX 4090",
    "started_at": "datetime",
    "ended_at": "datetime | null",
    "duration_minutes": "int",
    "cost_dumont": "decimal",
    "cost_aws_equivalent": "decimal",
    "cost_gcp_equivalent": "decimal",
    "cost_azure_equivalent": "decimal",
    "status": "running | stopped | hibernated"
  }
  ```

- [ ] Criar tabela/collection `gpu_pricing_reference`
  ```python
  # Preços de referência por GPU
  {
    "gpu_type": "RTX 4090",
    "vram_gb": 24,
    "dumont_hourly": 0.44,
    "aws_equivalent_hourly": 4.10,
    "gcp_equivalent_hourly": 3.67,
    "azure_equivalent_hourly": 3.95,
    "last_updated": "datetime"
  }
  ```

#### 1.3.2 Serviço de Cálculo de Economia
- [ ] Criar arquivo `src/services/savings_calculator.py`
  ```python
  class SavingsCalculator:
      def calculate_user_savings(self, user_id: str, period: str = "month") -> dict:
          """
          Calcula economia do usuário para o período especificado.
          
          Returns:
              {
                  "period": "2024-12",
                  "total_hours": 156.5,
                  "total_cost_dumont": 68.86,
                  "total_cost_aws": 641.65,
                  "total_cost_gcp": 574.26,
                  "total_cost_azure": 618.18,
                  "savings_vs_aws": 572.79,
                  "savings_vs_gcp": 505.40,
                  "savings_vs_azure": 549.32,
                  "savings_percentage_avg": 88.7,
                  "breakdown_by_gpu": [...],
                  "auto_hibernate_savings": 32.50
              }
          """
          pass
      
      def get_realtime_comparison(self, gpu_type: str) -> dict:
          """Retorna comparação em tempo real para uma GPU específica."""
          pass
      
      def get_savings_history(self, user_id: str, months: int = 6) -> list:
          """Retorna histórico de economia dos últimos N meses."""
          pass
  ```

- [ ] Implementar método `calculate_user_savings()`
- [ ] Implementar método `get_realtime_comparison()`
- [ ] Implementar método `get_savings_history()`
- [ ] Adicionar cache para otimização (Redis ou in-memory)

#### 1.3.3 Endpoints da API
- [ ] Criar arquivo `src/api/v1/endpoints/savings.py`
  ```python
  @router.get("/savings/summary")
  async def get_savings_summary(
      user: User = Depends(get_current_user),
      period: str = Query("month", regex="^(day|week|month|year|all)$")
  ) -> SavingsSummaryResponse:
      """Retorna resumo de economia do usuário."""
      pass
  
  @router.get("/savings/history")
  async def get_savings_history(
      user: User = Depends(get_current_user),
      months: int = Query(6, ge=1, le=24)
  ) -> SavingsHistoryResponse:
      """Retorna histórico mensal de economia."""
      pass
  
  @router.get("/savings/breakdown")
  async def get_savings_breakdown(
      user: User = Depends(get_current_user),
      period: str = Query("month")
  ) -> SavingsBreakdownResponse:
      """Retorna breakdown por GPU/máquina."""
      pass
  
  @router.get("/pricing/comparison/{gpu_type}")
  async def get_gpu_price_comparison(
      gpu_type: str
  ) -> GPUPriceComparisonResponse:
      """Retorna comparação de preços para uma GPU."""
      pass
  ```

- [ ] Implementar endpoint `/savings/summary`
- [ ] Implementar endpoint `/savings/history`
- [ ] Implementar endpoint `/savings/breakdown`
- [ ] Implementar endpoint `/pricing/comparison/{gpu_type}`
- [ ] Adicionar testes unitários para cada endpoint
- [ ] Documentar endpoints no Swagger/OpenAPI

---

### 🎨 Frontend - Componentes Visuais

#### 1.3.4 Componente Principal: SavingsDashboard
- [ ] Criar arquivo `web/src/components/SavingsDashboard.jsx`

**Estrutura do componente:**
```jsx
// Componentes filhos necessários:
// - SavingsSummaryCard
// - SavingsComparisonChart
// - SavingsBreakdownTable
// - SavingsHistoryGraph
// - AutoHibernateSavingsCard
```

#### 1.3.5 SavingsSummaryCard (Card Principal)
- [ ] Criar componente `web/src/components/savings/SavingsSummaryCard.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  💰 Sua Economia Este Mês                    [?] [⚙️]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   $47.60    │  │   $312.00   │  │   $264.40   │     │
│  │  Você pagou │  │ AWS pagaria │  │  Economia   │     │
│  │             │  │             │  │    (85%)    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ═══════════════════════════════════════════════════   │
│  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │
│  15% do custo                                    AWS   │
│  ═══════════════════════════════════════════════════   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Checklist do componente:**
- [ ] Exibir valor pago pelo usuário (grande, destaque)
- [ ] Exibir valor equivalente AWS (comparação)
- [ ] Exibir economia total em $ e %
- [ ] Barra de progresso visual (% do custo)
- [ ] Animação de contagem ao carregar
- [ ] Loading skeleton enquanto carrega dados
- [ ] Tooltip explicando cálculo
- [ ] Seletor de período (dia/semana/mês/ano)

#### 1.3.6 SavingsComparisonChart (Gráfico de Comparação)
- [ ] Criar componente `web/src/components/savings/SavingsComparisonChart.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  📊 Comparação com Cloud Providers                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Dumont    ████████░░░░░░░░░░░░░░░░░░░░░  $47.60       │
│  AWS       ████████████████████████████░░  $312.00     │
│  GCP       ███████████████████████████░░░  $287.40     │
│  Azure     ████████████████████████████░░  $308.00     │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  Economia média: 85% | Economia total: $264.40          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Checklist do componente:**
- [ ] Gráfico de barras horizontais
- [ ] Cores distintas para cada provider
- [ ] Valores em $ ao lado de cada barra
- [ ] Animação de entrada das barras
- [ ] Logos dos providers (AWS, GCP, Azure)
- [ ] Hover com detalhes
- [ ] Responsivo para mobile

#### 1.3.7 SavingsBreakdownTable (Detalhamento por GPU)
- [ ] Criar componente `web/src/components/savings/SavingsBreakdownTable.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  📋 Detalhamento por GPU                    [Exportar]  │
├─────────────────────────────────────────────────────────┤
│  GPU         │ Horas │ Você Pagou │ AWS     │ Economia  │
│  ─────────────────────────────────────────────────────  │
│  RTX 4090    │ 40h   │ $17.60     │ $164.00 │ $146.40   │
│  RTX 3090    │ 20h   │ $5.00      │ $42.00  │ $37.00    │
│  A100 80GB   │ 5h    │ $9.45      │ $163.85 │ $154.40   │
│  ─────────────────────────────────────────────────────  │
│  TOTAL       │ 65h   │ $32.05     │ $369.85 │ $337.80   │
└─────────────────────────────────────────────────────────┘
```

**Checklist do componente:**
- [ ] Tabela ordenável por coluna
- [ ] Cálculo automático de totais
- [ ] Highlight na linha com maior economia
- [ ] Exportar para CSV
- [ ] Paginação se muitos itens
- [ ] Filtro por GPU

#### 1.3.8 SavingsHistoryGraph (Histórico Mensal)
- [ ] Criar componente `web/src/components/savings/SavingsHistoryGraph.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  📈 Histórico de Economia (últimos 6 meses)             │
├─────────────────────────────────────────────────────────┤
│                                           ●             │
│                               ●       ●                 │
│                   ●       ●                             │
│       ●       ●                                         │
│   ●                                                     │
│  ─────────────────────────────────────────────────────  │
│  Jul    Ago    Set    Out    Nov    Dez                │
│                                                         │
│  Total economizado em 2024: $1,847.50                   │
└─────────────────────────────────────────────────────────┘
```

**Checklist do componente:**
- [ ] Gráfico de linha com área preenchida
- [ ] Hover mostra valor do mês
- [ ] Cores gradiente (verde)
- [ ] Seletor de período (3m, 6m, 12m, all)
- [ ] Total acumulado abaixo
- [ ] Usando Recharts ou Chart.js

#### 1.3.9 AutoHibernateSavingsCard (Economia por Auto-Hibernação)
- [ ] Criar componente `web/src/components/savings/AutoHibernateSavingsCard.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  😴 Economia com Auto-Hibernação                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Máquinas hibernadas automaticamente: 12 vezes         │
│  Horas economizadas: 47h                                │
│  💰 Você economizou: $32.50                             │
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │ "Se não hibernasse, você pagaria $32.50 a mais │    │
│  │  este mês por máquinas paradas"                │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Checklist do componente:**
- [ ] Contador de hibernações automáticas
- [ ] Horas economizadas
- [ ] Valor economizado
- [ ] Mensagem explicativa
- [ ] Ícone animado de "sleeping"

---

### 🔧 Integração e Testes

#### 1.3.10 Hooks e Estado
- [ ] Criar hook `web/src/hooks/useSavings.js`
  ```javascript
  export function useSavings(period = 'month') {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    
    // Fetch savings data
    // Auto-refresh a cada 5 minutos
    // Cache local
    
    return { data, loading, error, refetch }
  }
  ```

- [ ] Criar hook `useSavingsHistory()`
- [ ] Criar hook `useSavingsBreakdown()`
- [ ] Implementar refresh automático
- [ ] Implementar cache local (React Query ou SWR)

#### 1.3.11 Integração no Dashboard Principal
- [ ] Adicionar SavingsDashboard à página principal
- [ ] Posicionar como primeiro elemento visível
- [ ] Garantir que seja responsivo
- [ ] Testar em diferentes resoluções

#### 1.3.12 Testes
- [ ] Testes unitários dos componentes React
- [ ] Testes de integração da API
- [ ] Testes E2E do fluxo completo
- [ ] Testes de performance (carregamento)
- [ ] Testes de acessibilidade (a11y)

---

### 📱 Responsividade

#### 1.3.13 Mobile Layout
- [ ] Cards empilhados verticalmente
- [ ] Gráficos simplificados
- [ ] Swipe entre cards
- [ ] Touch-friendly interactions

#### 1.3.14 Tablet Layout
- [ ] Grid 2x2 para cards
- [ ] Gráficos adaptados
- [ ] Sidebar colapsável

---

### 🎨 Design System

#### 1.3.15 Cores e Estilos
```css
/* Cores para economia */
--savings-positive: #22c55e;  /* Verde - economia */
--savings-neutral: #f59e0b;   /* Amarelo - neutro */
--savings-negative: #ef4444;  /* Vermelho - prejuízo */

/* Cores dos providers */
--color-aws: #FF9900;
--color-gcp: #4285F4;
--color-azure: #0078D4;
--color-dumont: #22c55e;
```

- [ ] Definir variáveis CSS
- [ ] Criar componentes de ícones para providers
- [ ] Animações padronizadas
- [ ] Skeleton loading styles

---

## 1.4 Critérios de Conclusão (Definition of Done)

- [ ] Todos os endpoints da API funcionando
- [ ] Todos os componentes implementados
- [ ] Responsivo em mobile, tablet e desktop
- [ ] Testes passando (>80% coverage)
- [ ] Performance < 2s para carregar
- [ ] Documentação atualizada
- [ ] Code review aprovado
- [ ] Deploy em staging testado
- [ ] Deploy em produção

---

# 🤖 SPRINT 2: AI GPU Advisor

## 2.1 Objetivo
Criar um assistente de IA que recomenda a GPU ideal baseado na descrição do projeto do usuário.

## 2.2 Por que é Prioridade #2?
- ✅ **Diferenciador único** no mercado
- ✅ Remove **fricção** da escolha de GPU
- ✅ Demonstra **expertise técnica**
- ✅ Cria momento **WOW** imediato
- ✅ Aumenta **confiança** do usuário

---

## 2.3 Checklist de Implementação

### 🧠 Backend - Motor de IA

#### 2.3.1 Serviço de Recomendação
- [ ] Criar arquivo `src/services/gpu_advisor.py`

```python
class GPUAdvisor:
    """
    Serviço de recomendação de GPU baseado em IA.
    Analisa descrição do projeto e recomenda configuração ideal.
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.gpu_specs = self._load_gpu_specs()
        self.pricing = self._load_pricing()
    
    async def get_recommendation(
        self, 
        project_description: str,
        budget_limit: float = None,
        preferred_gpus: list = None
    ) -> GPURecommendation:
        """
        Analisa projeto e retorna recomendação de GPU.
        
        Args:
            project_description: Descrição em linguagem natural
            budget_limit: Limite de orçamento por hora (opcional)
            preferred_gpus: Lista de GPUs preferidas (opcional)
        
        Returns:
            GPURecommendation com GPU recomendada e justificativa
        """
        pass
    
    def _analyze_workload(self, description: str) -> WorkloadAnalysis:
        """Extrai características do workload da descrição."""
        pass
    
    def _match_gpu(self, workload: WorkloadAnalysis) -> list[GPUMatch]:
        """Encontra GPUs adequadas para o workload."""
        pass
    
    def _calculate_estimates(self, gpu: str, workload: WorkloadAnalysis) -> Estimates:
        """Calcula estimativas de tempo e custo."""
        pass
```

#### 2.3.2 Estruturas de Dados
- [ ] Criar arquivo `src/models/gpu_advisor.py`

```python
from pydantic import BaseModel
from typing import Optional, List

class WorkloadAnalysis(BaseModel):
    """Análise do workload do usuário."""
    workload_type: str  # training, inference, rendering, etc.
    model_type: Optional[str]  # LLM, CNN, diffusion, etc.
    model_size: Optional[str]  # 7B, 13B, 70B params
    dataset_size: Optional[str]  # small, medium, large
    precision: str  # fp32, fp16, int8
    vram_required_gb: int
    compute_intensity: str  # low, medium, high
    estimated_duration_hours: float

class GPUMatch(BaseModel):
    """Match de GPU para o workload."""
    gpu_type: str
    vram_gb: int
    score: float  # 0-100
    fits_workload: bool
    fits_budget: bool
    reasons: List[str]

class GPURecommendation(BaseModel):
    """Recomendação final de GPU."""
    recommended_gpu: str
    vram_gb: int
    hourly_price: float
    estimated_hours: float
    estimated_total_cost: float
    aws_equivalent_cost: float
    savings_percentage: float
    
    # Alternativas
    alternatives: List[GPUMatch]
    
    # Justificativa
    reasoning: str
    technical_notes: List[str]
    
    # Warnings
    warnings: Optional[List[str]]
```

#### 2.3.3 Prompt Engineering
- [ ] Criar arquivo `src/services/prompts/gpu_advisor_prompt.py`

```python
GPU_ADVISOR_SYSTEM_PROMPT = """
Você é um especialista em GPU Cloud e Machine Learning. 
Sua função é analisar descrições de projetos e recomendar a GPU ideal.

CONHECIMENTO DE GPUs DISPONÍVEIS:
{gpu_specs}

REGRAS DE RECOMENDAÇÃO:
1. VRAM é crítico - modelo deve caber na memória
2. Para training: considere batch size e gradient checkpointing
3. Para inference: considere latência e throughput
4. Custo-benefício é importante
5. Sempre considere alternativas mais baratas se adequadas

FORMATO DE RESPOSTA:
Responda em JSON com a estrutura especificada.
"""

GPU_ADVISOR_USER_PROMPT = """
PROJETO DO USUÁRIO:
{project_description}

RESTRIÇÕES:
- Orçamento máximo por hora: {budget_limit}
- GPUs preferidas: {preferred_gpus}

Analise o projeto e recomende a GPU ideal.
"""
```

#### 2.3.4 Knowledge Base de GPUs
- [ ] Criar arquivo `src/data/gpu_knowledge_base.json`

```json
{
  "gpus": [
    {
      "name": "RTX 3060",
      "vram_gb": 12,
      "cuda_cores": 3584,
      "tensor_cores": 112,
      "memory_bandwidth_gbps": 360,
      "fp32_tflops": 12.7,
      "fp16_tflops": 25.4,
      "best_for": ["small models", "inference", "development"],
      "not_recommended_for": ["large LLMs", "70B+ training"],
      "typical_workloads": [
        "Stable Diffusion inference",
        "Small model fine-tuning",
        "Development and testing"
      ]
    },
    {
      "name": "RTX 4090",
      "vram_gb": 24,
      "cuda_cores": 16384,
      "tensor_cores": 512,
      "memory_bandwidth_gbps": 1008,
      "fp32_tflops": 82.6,
      "fp16_tflops": 165.2,
      "best_for": ["LLM fine-tuning", "Stable Diffusion", "medium models"],
      "not_recommended_for": ["70B+ full training"],
      "typical_workloads": [
        "LLaMA 7B/13B fine-tuning with LoRA",
        "Stable Diffusion XL training",
        "Medium-scale ML training"
      ]
    },
    {
      "name": "A100 80GB",
      "vram_gb": 80,
      "cuda_cores": 6912,
      "tensor_cores": 432,
      "memory_bandwidth_gbps": 2039,
      "fp32_tflops": 19.5,
      "fp16_tflops": 312,
      "best_for": ["large LLMs", "multi-GPU", "research"],
      "not_recommended_for": ["simple inference", "small projects"],
      "typical_workloads": [
        "LLaMA 65B/70B training",
        "Large batch training",
        "Research workloads"
      ]
    },
    {
      "name": "H100",
      "vram_gb": 80,
      "cuda_cores": 16896,
      "tensor_cores": 528,
      "memory_bandwidth_gbps": 3350,
      "fp32_tflops": 67,
      "fp16_tflops": 1979,
      "best_for": ["cutting-edge LLMs", "production inference", "massive scale"],
      "not_recommended_for": ["budget projects", "small workloads"],
      "typical_workloads": [
        "LLaMA 2 70B training",
        "GPT-scale models",
        "High-throughput inference"
      ]
    }
  ],
  "workload_patterns": {
    "llm_finetuning_lora": {
      "vram_multiplier": 1.2,
      "description": "LoRA fine-tuning requires ~1.2x model size in VRAM"
    },
    "llm_finetuning_full": {
      "vram_multiplier": 4.0,
      "description": "Full fine-tuning requires ~4x model size (model + optimizer + gradients)"
    },
    "inference": {
      "vram_multiplier": 1.1,
      "description": "Inference requires ~1.1x model size"
    },
    "stable_diffusion": {
      "vram_base_gb": 8,
      "description": "SD 1.5 needs 8GB, SDXL needs 12GB+"
    }
  }
}
```

#### 2.3.5 Integração com LLM
- [ ] Criar arquivo `src/services/llm_client.py`

```python
class LLMClient:
    """Cliente para comunicação com LLM (OpenAI, Anthropic, local)."""
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self._setup_client()
    
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict = None
    ) -> dict:
        """Envia prompt e retorna resposta estruturada."""
        pass
```

- [ ] Suporte para OpenAI GPT-4
- [ ] Suporte para Anthropic Claude
- [ ] Suporte para modelo local (Ollama)
- [ ] Fallback entre providers
- [ ] Rate limiting e retry logic

#### 2.3.6 Endpoints da API
- [ ] Criar arquivo `src/api/v1/endpoints/gpu_advisor.py`

```python
@router.post("/advisor/recommend")
async def get_gpu_recommendation(
    request: GPURecommendationRequest,
    user: User = Depends(get_current_user)
) -> GPURecommendation:
    """
    Recebe descrição do projeto e retorna recomendação de GPU.
    
    Request:
        {
            "project_description": "Preciso treinar LLaMA 7B...",
            "budget_limit": 1.00,  # opcional
            "preferred_gpus": ["RTX 4090", "A100"]  # opcional
        }
    """
    pass

@router.get("/advisor/quick/{workload_type}")
async def get_quick_recommendation(
    workload_type: str,
    model_size: Optional[str] = None
) -> GPURecommendation:
    """
    Recomendação rápida baseada em tipo de workload.
    
    workload_type: llm_training, llm_inference, stable_diffusion, etc.
    """
    pass

@router.get("/advisor/compare")
async def compare_gpus(
    gpus: List[str] = Query(...),
    workload: Optional[str] = None
) -> GPUComparisonResponse:
    """Compara múltiplas GPUs para um workload."""
    pass
```

- [ ] Implementar endpoint `/advisor/recommend`
- [ ] Implementar endpoint `/advisor/quick/{workload_type}`
- [ ] Implementar endpoint `/advisor/compare`
- [ ] Cache de respostas similares
- [ ] Rate limiting por usuário
- [ ] Logging para analytics

---

### 🎨 Frontend - Interface do Advisor

#### 2.3.7 Componente Principal: GPUAdvisor
- [ ] Criar arquivo `web/src/components/GPUAdvisor.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ✨ AI GPU Advisor                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Descreva seu projeto:                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Preciso treinar um modelo LLaMA 7B com LoRA fine-tuning │   │
│  │ em um dataset de 50k exemplos de código Python.         │   │
│  │ Quero bom custo-benefício.                              │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Orçamento máximo: [$0.50/h ▼]  [Analisar Projeto 🔍]          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Checklist:**
- [ ] Textarea para descrição
- [ ] Placeholder com exemplos
- [ ] Seletor de orçamento (opcional)
- [ ] Botão de análise
- [ ] Loading state com animação
- [ ] Sugestões de prompts rápidos

#### 2.3.8 Componente: RecommendationCard
- [ ] Criar arquivo `web/src/components/gpu-advisor/RecommendationCard.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  🎯 Recomendação                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ⚡ GPU Recomendada: RTX 4090                           │   │
│  │                                                          │   │
│  │  VRAM: 24GB    │    Preço: $0.44/hora                   │   │
│  │                                                          │   │
│  │  📊 Estimativas:                                        │   │
│  │  • Tempo estimado: ~8 horas                             │   │
│  │  • Custo estimado: $3.52                                │   │
│  │  • AWS equivalente: $32.80                              │   │
│  │  • Economia: 89% ($29.28)                               │   │
│  │                                                          │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │                                                          │   │
│  │  💡 Por quê RTX 4090?                                   │   │
│  │  • LLaMA 7B com LoRA cabe confortavelmente em 24GB     │   │
│  │  • Dataset de 50k pode rodar em batch size 4-8         │   │
│  │  • Melhor custo-benefício para este workload           │   │
│  │  • A100 seria overkill (custaria $15.12)               │   │
│  │                                                          │   │
│  │  ⚠️ Dicas:                                              │   │
│  │  • Use gradient checkpointing se precisar de mais VRAM │   │
│  │  • Considere fp16 mixed precision                       │   │
│  │                                                          │   │
│  │  [Criar Máquina com RTX 4090]  [Ver Alternativas]       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Checklist:**
- [ ] Destaque visual da GPU recomendada
- [ ] Specs da GPU (VRAM, preço)
- [ ] Estimativas de tempo e custo
- [ ] Comparação com AWS
- [ ] Reasoning expandível
- [ ] Dicas técnicas
- [ ] CTA para criar máquina
- [ ] Link para alternativas

#### 2.3.9 Componente: AlternativesPanel
- [ ] Criar arquivo `web/src/components/gpu-advisor/AlternativesPanel.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  🔄 Alternativas                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GPU        │ VRAM │ Preço/h │ Est. Tempo │ Custo  │ Match     │
│  ─────────────────────────────────────────────────────────────  │
│  RTX 4090   │ 24GB │ $0.44   │ 8h         │ $3.52  │ ██████ 95%│
│  A100 80GB  │ 80GB │ $1.89   │ 4h         │ $7.56  │ █████░ 80%│
│  RTX 3090   │ 24GB │ $0.25   │ 12h        │ $3.00  │ ████░░ 70%│
│  H100       │ 80GB │ $2.49   │ 3h         │ $7.47  │ ████░░ 65%│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Checklist:**
- [ ] Tabela comparativa
- [ ] Ordenação por custo/tempo/match
- [ ] Barra de match score visual
- [ ] Seleção de alternativa
- [ ] Tooltip com detalhes

#### 2.3.10 Quick Suggestions
- [ ] Criar arquivo `web/src/components/gpu-advisor/QuickSuggestions.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ Sugestões Rápidas                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [LLaMA 7B LoRA]  [Stable Diffusion XL]  [BERT Fine-tuning]    │
│  [GPT-2 Training]  [Whisper Inference]  [Midjourney Clone]      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Checklist:**
- [ ] Chips clicáveis
- [ ] Preenche o textarea ao clicar
- [ ] Baseado em workloads populares
- [ ] Analytics de clicks

---

### 🔧 Integração

#### 2.3.11 Hook e Estado
- [ ] Criar hook `web/src/hooks/useGPUAdvisor.js`

```javascript
export function useGPUAdvisor() {
  const [recommendation, setRecommendation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const analyze = async (description, options = {}) => {
    setLoading(true)
    try {
      const result = await api.post('/advisor/recommend', {
        project_description: description,
        ...options
      })
      setRecommendation(result.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  return { recommendation, loading, error, analyze }
}
```

#### 2.3.12 Integração no Fluxo de Criação de Máquina
- [ ] Adicionar GPUAdvisor no modal de nova máquina
- [ ] Opção "Não sei qual GPU escolher"
- [ ] Pre-fill specs baseado na recomendação
- [ ] CTA direto para criar com config recomendada

#### 2.3.13 Analytics e Feedback
- [ ] Tracking de recomendações aceitas/rejeitadas
- [ ] Botão de feedback ("Foi útil?")
- [ ] Log para melhorar prompts
- [ ] A/B testing de diferentes prompts

---

## 2.4 Critérios de Conclusão

- [ ] Motor de IA funcionando com precisão > 80%
- [ ] Latência < 3s para recomendação
- [ ] Interface implementada e responsiva
- [ ] Integrado no fluxo de criação
- [ ] Feedback loop implementado
- [ ] Testes passando
- [ ] Documentação atualizada

---

# 🎓 SPRINT 3: Onboarding Guiado

## 3.1 Objetivo
Criar uma experiência de primeiro uso que leva o usuário ao primeiro "aha moment" em menos de 5 minutos.

## 3.2 Por que é Prioridade #3?
- ✅ First impression é crucial
- ✅ Reduz churn nos primeiros 7 dias
- ✅ Ensina as features principais
- ✅ Leva ao primeiro sucesso rápido

---

## 3.3 Checklist de Implementação

### 🎯 Fluxo do Onboarding

#### 3.3.1 Detectar Primeiro Acesso
- [ ] Flag `has_completed_onboarding` no user profile
- [ ] Verificar no login/app load
- [ ] Trigger do onboarding wizard

#### 3.3.2 Passos do Onboarding
```
Passo 1: Boas-vindas
├── Mostrar nome do usuário
├── Explicar proposta de valor (economia)
└── CTA: "Vamos começar!"

Passo 2: AI GPU Advisor
├── "Me conta sobre seu projeto"
├── Input de descrição
├── Mostrar recomendação
└── CTA: "Usar esta GPU" ou "Escolher manualmente"

Passo 3: Criar Primeira Máquina
├── Pre-fill com recomendação da IA
├── Explicar cada campo
├── Mostrar estimativa de custo
└── CTA: "Criar Máquina"

Passo 4: Aguardar Provisionamento
├── Animação de progresso
├── Dicas enquanto espera
├── Estimativa de tempo
└── Notificação quando pronto

Passo 5: Primeiro Acesso
├── Mostrar VS Code no browser
├── Ou comando SSH
├── Tutorial rápido do ambiente
└── CTA: "Começar a desenvolver!"

Passo 6: Parabéns!
├── Celebração visual
├── Mostrar economia em tempo real
├── Dicas de próximos passos
├── Links para docs
└── CTA: "Ir para Dashboard"
```

#### 3.3.3 Componentes do Wizard
- [ ] Criar arquivo `web/src/components/onboarding/OnboardingWizard.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/WizardStep.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/ProgressBar.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/WelcomeStep.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/AdvisorStep.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/CreateMachineStep.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/ProvisioningStep.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/AccessStep.jsx`
- [ ] Criar arquivo `web/src/components/onboarding/CompletionStep.jsx`

#### 3.3.4 Estilos e Animações
- [ ] Transições suaves entre passos
- [ ] Progress bar animada
- [ ] Confetti na conclusão
- [ ] Ícones animados
- [ ] Skeleton loading nos passos

#### 3.3.5 Backend
- [ ] Endpoint para marcar onboarding completo
- [ ] Endpoint para tracking de passos
- [ ] Analytics de drop-off por passo

#### 3.3.6 Skip e Retomar
- [ ] Opção de pular onboarding
- [ ] Salvar progresso se sair
- [ ] Opção de refazer depois
- [ ] Acesso via menu de ajuda

---

## 3.4 Checklist Detalhado por Passo

### Passo 1: Boas-vindas
- [ ] Layout full-screen
- [ ] Animação de entrada
- [ ] Nome do usuário
- [ ] Texto de boas-vindas
- [ ] Proposta de valor
- [ ] Botão "Começar"
- [ ] Link "Pular tutorial"

### Passo 2: AI GPU Advisor
- [ ] Explicação do advisor
- [ ] Textarea para descrição
- [ ] Sugestões rápidas
- [ ] Botão de análise
- [ ] Exibir recomendação
- [ ] Explicar o resultado
- [ ] Botões: "Usar" / "Escolher manual"

### Passo 3: Criar Máquina
- [ ] Form simplificado
- [ ] Campos pre-filled
- [ ] Tooltips explicativos
- [ ] Estimativa de custo
- [ ] Botão "Criar"
- [ ] Validação em tempo real

### Passo 4: Provisionamento
- [ ] Animação de progresso
- [ ] Status em tempo real
- [ ] Estimativa de tempo
- [ ] Dicas (3-4 slides)
- [ ] Notificação quando pronto
- [ ] Auto-avançar ao completar

### Passo 5: Primeiro Acesso
- [ ] Tabs: VS Code / SSH / JupyterLab
- [ ] Botão de acesso
- [ ] Tutorial interativo básico
- [ ] Verificar que acessou

### Passo 6: Conclusão
- [ ] Animação de celebração
- [ ] Mostrar economia
- [ ] Próximos passos
- [ ] Links úteis
- [ ] Ir para dashboard

---

## 3.5 Critérios de Conclusão

- [ ] Fluxo completo funcionando
- [ ] < 5 min para completar
- [ ] Taxa de conclusão > 70%
- [ ] Responsivo
- [ ] Testes E2E passando

---

# 😴 SPRINT 4: Métricas de Auto-Hibernação

## 4.1 Objetivo
Mostrar ao usuário quanto ele economiza automaticamente com a feature de auto-hibernação.

## 4.2 Por que é Prioridade #4?
- ✅ Prova de valor contínua
- ✅ Justifica o produto
- ✅ Diferencial competitivo
- ✅ Relativamente simples de implementar

---

## 4.3 Checklist de Implementação

### Backend

#### 4.3.1 Tracking de Hibernações
- [ ] Registrar cada hibernação automática
  ```python
  {
    "machine_id": "string",
    "hibernated_at": "datetime",
    "resumed_at": "datetime | null",
    "idle_duration_before_hibernate": "int",  # minutos
    "would_have_cost": "decimal",  # se tivesse ficado ligada
    "savings": "decimal"
  }
  ```

- [ ] Calcular tempo que teria ficado ligada
- [ ] Calcular custo evitado

#### 4.3.2 Endpoint de Métricas
- [ ] `GET /hibernation/stats`
  ```json
  {
    "period": "month",
    "total_hibernations": 23,
    "total_hours_saved": 156,
    "total_savings": 68.64,
    "average_idle_before_hibernate": 15,
    "machines_breakdown": [...]
  }
  ```

### Frontend

#### 4.3.3 Card de Hibernação no Dashboard
- [ ] Criar `web/src/components/HibernationStatsCard.jsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  😴 Auto-Hibernação                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Este mês suas máquinas hibernaram                      │
│  automaticamente 23 vezes                               │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  💰 Economia: $68.64                            │   │
│  │  ⏱️ 156 horas economizadas                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  💡 Máquinas ociosas por mais de 15 min são            │
│     hibernadas automaticamente.                         │
│                                                         │
│  [Configurar] [Ver Histórico]                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 4.3.4 Notificação de Hibernação
- [ ] Toast quando máquina hiberna
  ```
  😴 Sua máquina "dev-server" foi hibernada automaticamente.
     Economia: $0.44/hora enquanto você não usa.
     [Acordar] [OK]
  ```

#### 4.3.5 Configurações
- [ ] Modal de configuração de hibernação
- [ ] Tempo de idle configurável (5, 10, 15, 30 min)
- [ ] Desativar para máquinas específicas
- [ ] Schedule (não hibernar em horário X)

---

## 4.4 Critérios de Conclusão

- [ ] Tracking funcionando
- [ ] Card no dashboard
- [ ] Notificações implementadas
- [ ] Configurações funcionando
- [ ] Testes passando

---

# 📋 RESUMO E TIMELINE

## Ordem de Implementação

```
Semana 1-2:  [████████████████████] Sprint 1 - Dashboard de Economia
Semana 3-4:  [████████████████████] Sprint 2 - AI GPU Advisor
Semana 5:    [██████████░░░░░░░░░░] Sprint 3 - Onboarding
Semana 6:    [██████████░░░░░░░░░░] Sprint 4 - Auto-Hibernação
```

## Métricas de Sucesso

| Sprint | Métrica | Target |
|--------|---------|--------|
| Sprint 1 | Usuários vendo dashboard | 100% |
| Sprint 1 | Tempo de load < 2s | ✓ |
| Sprint 2 | Precisão de recomendações | > 80% |
| Sprint 2 | Uso do advisor | > 50% dos novos usuários |
| Sprint 3 | Taxa de conclusão onboarding | > 70% |
| Sprint 3 | Tempo para primeiro "aha moment" | < 5 min |
| Sprint 4 | Economia média por hibernação | > $10/usuário/mês |

---

## Próximos Passos Após Sprints 1-4

1. **Sistema de Billing/Stripe** - Trial → Pagamento
2. **Notificações de Spending** - Alertas de gastos
3. **Programa de Referral** - Viralização
4. **API/Webhooks** - Integrações
5. **Multi-usuário/Times** - B2B

---

*Documento criado em Dezembro 2024*
*Última atualização: Dezembro 2024*

