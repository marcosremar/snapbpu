"""
AI Wizard Service - Uses OpenRouter to analyze projects and suggest GPUs
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# AI Wizard System Prompt - Fluxo Completo de Reserva
SYSTEM_PROMPT = """
Você é um assistente especialista em GPUs e cloud computing chamado "AI GPU Advisor". 
Sua função é guiar o usuário através de um fluxo completo: análise → pesquisa → opções → seleção → reserva.

FLUXO COMPLETO DO SISTEMA:

ETAPA 1 - ANÁLISE INICIAL:
- Analise o projeto do usuário e o modelo desejado
- Se faltar informações, pergunte sobre:
  * Qual projeto específico? (ex: fine-tuning, inferência, treinamento)
  * Qual modelo de IA? (ex: LLaMA 7B, Stable Diffusion, YOLOv8)
  * Qual framework? (PyTorch, TensorFlow, etc.)
  * Quantos usuários/concorrência?
  * Orçamento aproximado?

ETAPA 2 - PESQUISA NA INTERNET:
- Use gpt-4o-search-preview para buscar informações atualizadas
- Pesquise benchmarks, preços atuais, disponibilidade
- Compare diferentes GPUs no mercado
- Considere preços de cloud providers (AWS, GCP, Azure)

ETAPA 3 - OPÇÕES DE PREÇO:
- Apresente 3-4 opções claramente definidas:
  * "Econômico" - Mais barato, performance básica
  * "Intermediário" - Bom custo-benefício
  * "Rápido" - Alta performance
  * "Premium" - Máxima performance
- Para cada opção, mostre:
  * GPUs recomendadas
  * Preço estimado por hora
  * Performance esperada
  * Casos de uso ideais

ETAPA 4 - SELEÇÃO DE MÁQUINAS:
- Pergunte: "Você quer escolher as máquinas manualmente ou deseja que eu escolha a melhor opção para você?"
- Se MANUAL: Mostre lista detalhada de máquinas disponíveis
- Se AUTOMÁTICO: Selecione a melhor configuração automaticamente

ETAPA 5 - LISTA DE MÁQUINAS (se manual):
- Apresente lista com:
  * Nome da máquina
  * GPU específica
  * VRAM disponível
  * Preço por hora
  * Localização
  * Disponibilidade
- Permita seleção individual de máquinas

ETAPA 6 - RESERVA:
- Após seleção, inicie processo de reserva
- Confirme detalhes da reserva
- Forneça próximos passos

IMPORTANTE:
- Use busca na web para informações atualizadas
- Sempre apresente opções de preço claras
- Guie o usuário passo a passo
- Seja claro e objetivo nas recomendações

FORMATO DE RESPOSTA (JSON obrigatório):
{
  "stage": "analysis|research|options|selection|reservation",
  "needs_more_info": true/false,
  "questions": ["pergunta1", "pergunta2"] (se necessário),
  "research_results": {
    "findings": "resultados da pesquisa",
    "benchmarks": "benchmarks encontrados",
    "prices": "preços atuais"
  } (se na etapa de pesquisa),
  "price_options": [
    {
      "tier": "Econômico|Intermediário|Rápido|Premium",
      "gpus": ["GPU1", "GPU2"],
      "price_per_hour": "$X.XX",
      "performance": "descrição",
      "use_cases": ["caso1", "caso2"]
    }
  ] (se na etapa de opções),
  "machines": [
    {
      "id": "machine_id",
      "name": "Nome da Máquina",
      "gpu": "GPU específica",
      "vram": "XXGB",
      "price_per_hour": "$X.XX",
      "location": "região",
      "available": true
    }
  ] (se na etapa de seleção),
  "selection_mode": "manual|automatic" (se na etapa de seleção),
  "reservation": {
    "status": "ready|pending",
    "details": "detalhes da reserva"
  } (se na etapa de reserva),
  "explanation": "explicação detalhada da etapa atual"
}
"""

# GPU knowledge base - agora será complementado com busca na web
GPU_KNOWLEDGE = """
## GPU Recommendations by Use Case:

### Inferência (Deploy de modelos / APIs):
- RTX 4060/4070, RTX 3060/3070: Modelos pequenos, Stable Diffusion, LLMs até 7B
- Tesla T4: Inferência em produção, custo-eficiente
- A4000, L40: Modelos médios, batch inference

### Treinamento (Fine-tuning / ML Training):
- RTX 4080/4090: Fine-tuning de modelos até 13B, Stable Diffusion training
- RTX 3080/3090: Treinamento de modelos médios
- A5000, A6000: Workloads profissionais, modelos até 30B
- L40S: Alto desempenho para training

### HPC / LLMs (Modelos grandes / Multi-GPU):
- A100 40GB/80GB: LLMs grandes (30B-70B), treinamento distribuído
- H100: Estado da arte, modelos 70B+, máxima performance
- V100: Legacy mas ainda eficiente para muitos workloads

### Requisitos de VRAM por modelo:
- Stable Diffusion XL: 8-12GB
- LLaMA 7B (fp16): 14GB, (int8): 8GB, (int4): 4GB
- LLaMA 13B (fp16): 26GB, (int8): 14GB, (int4): 8GB
- LLaMA 30B (fp16): 60GB, (int8): 32GB, (int4): 16GB
- LLaMA 70B (fp16): 140GB (multi-GPU), (int8): 70GB, (int4): 35GB
- Mixtral 8x7B: 90GB (fp16), 45GB (int8), 24GB (int4)
- FLUX: 24GB+ recomendado
- Whisper Large: 10GB
- GPT-J 6B: 12GB (fp16), 6GB (int8)
"""

SYSTEM_PROMPT = f"""Você é um especialista em GPU Cloud para Machine Learning e IA.
Sua função é analisar o projeto do usuário e recomendar a GPU ideal.

IMPORTANTE: Sempre busque na internet informações atualizadas sobre:
- Requisitos de VRAM do modelo específico mencionado
- Benchmarks de tokens/segundo para o modelo em diferentes GPUs e frameworks
- Performance com diferentes técnicas (quantização INT4/INT8, Flash Attention, etc.)
- Possibilidade de RAM offloading quando VRAM é insuficiente

Use estas informações de referência como base:
{GPU_KNOWLEDGE}

Ao responder, inclua:
1. Informações do modelo (VRAM, quantização recomendada)
2. 3 opções de GPU (mínima, recomendada, máxima)
3. Performance por framework (PyTorch, vLLM, llama.cpp, TGI)
4. RAM offload: quando a VRAM não é suficiente, indicar quanto de RAM do sistema é necessário
5. Técnicas de otimização aplicáveis

GPUs disponíveis e preços médios:
- RTX_3060 (12GB): ~$0.10/hr | RTX_4060 (8GB): ~$0.12/hr
- RTX_4070 (12GB): ~$0.18/hr | RTX_4080 (16GB): ~$0.35/hr
- RTX_3090 (24GB): ~$0.40/hr | RTX_4090 (24GB): ~$0.70/hr
- A6000 (48GB): ~$1.00/hr | L40S (48GB): ~$1.50/hr
- A100 (80GB): ~$2.50/hr | H100 (80GB): ~$4.00/hr

Responda SEMPRE em JSON com este formato:
{{
  "needs_more_info": false,
  "questions": [],
  "recommendation": {{
    "workload_type": "inference|training|hpc",
    "model_info": {{
      "name": "Nome do modelo",
      "parameters": "7B",
      "vram_fp16": "14GB",
      "vram_int8": "8GB",
      "vram_int4": "4GB",
      "recommended_quantization": "INT8 para melhor balanço qualidade/velocidade"
    }},
    "gpu_options": [
      {{
        "tier": "minima",
        "gpu": "RTX_4060",
        "vram": "8GB",
        "price_per_hour": "$0.12",
        "frameworks": {{
          "vllm": "60-80 tok/s (INT4)",
          "pytorch": "30-40 tok/s (INT8)",
          "llama_cpp": "40-60 tok/s (Q4_K_M)"
        }},
        "ram_offload": "Não necessário com INT4/INT8",
        "observation": "Requer quantização, bom para testes"
      }},
      {{
        "tier": "recomendada",
        "gpu": "RTX_4070",
        "vram": "12GB",
        "price_per_hour": "$0.18",
        "frameworks": {{
          "vllm": "100-130 tok/s (INT8)",
          "pytorch": "50-70 tok/s (FP16)",
          "llama_cpp": "70-90 tok/s (Q5_K_M)"
        }},
        "ram_offload": "Não necessário",
        "observation": "Melhor custo-benefício"
      }},
      {{
        "tier": "maxima",
        "gpu": "RTX_4090",
        "vram": "24GB",
        "price_per_hour": "$0.70",
        "frameworks": {{
          "vllm": "180-220 tok/s (FP16)",
          "pytorch": "100-130 tok/s (FP16)",
          "tgi": "150-180 tok/s (FP16)"
        }},
        "ram_offload": "Não necessário",
        "observation": "Máxima performance, FP16 sem quantização"
      }}
    ],
    "optimization_tips": [
      "Use Flash Attention 2 para reduzir uso de VRAM",
      "vLLM oferece melhor throughput para serving",
      "INT8 oferece ~95% da qualidade com metade da VRAM"
    ],
    "explanation": "Explicação detalhada baseada nos benchmarks...",
    "search_sources": "Fontes: HuggingFace, vLLM benchmarks, etc."
  }}
}}

Se precisar de mais informações:
{{
  "needs_more_info": true,
  "questions": ["Qual modelo específico?", "Qual framework pretende usar?"],
  "recommendation": null
}}
"""


class AIWizardService:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Modelos para iteração - otimizados para conversa e busca
        self.models = [
            "openai/gpt-4o-mini",              # Principal para conversa (rápido e eficiente)
            "openai/gpt-4o-search-preview",    # Para busca de informações atualizadas
            "openai/gpt-4o",                    # Capacidade completa quando necessário
            "anthropic/claude-3.5-sonnet",     # Alternativa robusta
            "google/gemini-pro-1.5",           # Google alternative
            "openai/gpt-3.5-turbo"             # Fallback final
        ]
        
        self.max_retries = len(self.models)

    async def analyze_project(
        self,
        project_description: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a project description and return GPU recommendations
        Iterates through multiple models until finding a valid response
        """
        if not self.api_key:
            logger.error("OpenRouter API key not configured - AI Wizard requires LLM access")
            raise ValueError("AI Wizard requires OpenRouter API key to function. Please configure OPENROUTER_API_KEY environment variable.")

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history if exists
        if conversation_history:
            messages.extend(conversation_history)

        # Add current message
        messages.append({"role": "user", "content": project_description})

        # Iterar através dos modelos até encontrar resposta válida
        last_error = None
        
        for attempt, model in enumerate(self.models):
            logger.info(f"Tentativa {attempt + 1}/{self.max_retries} com modelo: {model}")
            
            try:
                result = await self._try_model(model, messages)
                if result:
                    logger.info(f"Sucesso com modelo: {model}")
                    return {
                        "success": True,
                        "data": result,
                        "model_used": model,
                        "attempts": attempt + 1
                    }
            
            except PermissionError as e:
                logger.error(f"Erro de permissão fatal: {e}")
                last_error = e
                break # Interromper loop imediatamente e ir para fallback
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Falha com modelo {model}: {str(e)}")
                continue
        
        # Se todos os modelos falharam, tentar abordagem simplificada
        logger.error("Todos os modelos falharam (ou erro de auth), tentando abordagem simplificada...")
        try:
            simplified_result = await self._try_simplified_approach(messages)
            return {
                "success": True,
                "data": simplified_result,
                "model_used": "simplified_fallback",
                "attempts": attempt + 1,
                "warning": "Usando abordagem simplificada após falha dos modelos"
            }
        except Exception as e:
            logger.error(f"Falha completa: {str(e)}")
            raise Exception(f"AI Wizard failed after trying {self.max_retries} models. Last error: {str(last_error)}")

    async def _try_model(self, model: str, messages: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Tenta obter resposta de um modelo específico
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://dumontcloud.com",
                    "X-Title": "Dumont Cloud GPU Wizard"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"}
                }
            )

            if response.status_code != 200:
                # Se for erro de autenticação (401), não adianta tentar outros modelos
                if response.status_code == 401:
                    logger.error("Erro de autenticação (401) no OpenRouter. Abortando tentativas com LLM.")
                    raise PermissionError(f"API error 401: {response.text}")
                
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Validar e parsear JSON
            import json
            try:
                result = json.loads(content)
                
                # Validar estrutura da resposta
                if self._validate_response(result):
                    return result
                else:
                    logger.warning(f"Resposta inválida do modelo {model}: {result}")
                    return None
                    
            except json.JSONDecodeError:
                logger.error(f"JSON inválido do modelo {model}: {content}")
                return None

    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Valida se a resposta tem a estrutura esperada do novo fluxo
        """
        try:
            # Verificar campos obrigatórios do novo formato
            if "stage" not in response:
                return False
                
            # Validar stage
            valid_stages = ["analysis", "research", "options", "selection", "reservation"]
            if response["stage"] not in valid_stages:
                return False
                
            if "needs_more_info" not in response:
                return False
                
            if response["needs_more_info"]:
                # Se precisa de mais info, deve ter questions
                if "questions" not in response or not isinstance(response["questions"], list):
                    return False
            else:
                # Validar campos específicos de cada etapa
                stage = response["stage"]
                
                if stage == "research":
                    if "research_results" not in response:
                        return False
                        
                elif stage == "options":
                    if "price_options" not in response or not isinstance(response["price_options"], list):
                        return False
                        
                    # Validar estrutura das opções de preço
                    for option in response["price_options"]:
                        if not all(key in option for key in ["tier", "gpus", "price_per_hour", "performance"]):
                            return False
                            
                elif stage == "selection":
                    if "selection_mode" not in response or response["selection_mode"] not in ["manual", "automatic"]:
                        return False
                        
                    if response["selection_mode"] == "manual":
                        if "machines" not in response or not isinstance(response["machines"], list):
                            return False
                            
                        # Validar estrutura das máquinas
                        for machine in response["machines"]:
                            required_fields = ["id", "name", "gpu", "vram", "price_per_hour", "location", "available"]
                            if not all(field in machine for field in required_fields):
                                return False
                                
                elif stage == "reservation":
                    if "reservation" not in response:
                        return False
                        
                    reservation = response["reservation"]
                    if not isinstance(reservation, dict) or "status" not in reservation:
                        return False
                        
            # Verificar campo explanation
            if "explanation" not in response:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação: {str(e)}")
            return False

    async def _try_simplified_approach(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Abordagem simplificada se todos os modelos falharem - segue novo fluxo com progressão completa
        """
        user_input = messages[-1]["content"].lower()
        
        # Verificar se tem informações suficientes para progredir
        has_project_type = any(word in user_input for word in [
            "fine-tuning", "finetune", "training", "treinamento", "inferencia", "inference",
            "deploy", "deploy", "api", "serving", "stable diffusion", "llama", "yolo",
            "rodar", "executar", "instalar", "uso", "usar", "run", "install"
        ])
        
        has_model = any(word in user_input for word in [
            "llama", "lama", "stable diffusion", "yolo", "gpt", "bert", "resnet", "vgg",
            "mistral", "mixtral", "falcon"
        ])
        
        has_budget = any(word in user_input for word in [
            "$", "dollar", "real", "r$", "orçamento", "budget", "preço", "custo"
        ])
        
        # Verificar solicitações específicas para progredir
        wants_options = any(word in user_input for word in [
            "opções", "opcoes", "preço", "preco", "custo", "valor", "disponível", "disponivel"
        ])
        
        wants_selection = any(word in user_input for word in [
            "escolher", "selecionar", "máquina", "gpu", "automático", "automatico", "manual",
            "escolho", "seleciono", "opção", "opcao", "intermediário", "economico", "rapido", "premium"
        ]) and not any(word in user_input for word in [
            "projeto", "fazer", "quero", "preciso"
        ])
        
        wants_reservation = any(word in user_input for word in [
            "reservar", "reserva", "finalizar", "confirmar", "contratar", "alugar"
        ])
        
        # Se tiver informações completas e não estiver pedindo nada específico, progredir para research
        if (has_project_type and has_model and has_budget and 
            not wants_options and not wants_selection and not wants_reservation):
            
            # Implementar pesquisa real com gpt-4o-search-preview
            try:
                research_result = await self._perform_real_research(messages[-1]["content"])
                return {
                    "stage": "research",
                    "needs_more_info": False,
                    "research_results": research_result,
                    "explanation": "Pesquisei informações atualizadas sobre GPUs e benchmarks para seu projeto."
                }
            except Exception as e:
                logger.error(f"Erro na pesquisa real: {e}")
                # Fallback para pesquisa simulada
                return {
                    "stage": "research",
                    "needs_more_info": False,
                    "research_results": {
                        "findings": "Projeto identificado com informações completas. Iniciando pesquisa de GPUs e benchmarks.",
                        "benchmarks": "Analisando performance para o modelo especificado.",
                        "prices": "Pesquisando preços atuais no mercado."
                    },
                    "explanation": "Com as informações fornecidas, vou pesquisar as melhores opções de GPU para seu projeto."
                }
        
        # Se pedir opções, progredir para options
        elif wants_options or "opções de preço" in user_input:
            return {
                "stage": "options",
                "needs_more_info": False,
                "price_options": [
                    {
                        "tier": "Econômico",
                        "gpus": ["RTX 4060", "RTX 3060"],
                        "price_per_hour": "$0.20-0.30",
                        "performance": "Adequado para projetos pequenos e testes",
                        "use_cases": ["Fine-tuning leve", "Inferência básica", "Desenvolvimento"]
                    },
                    {
                        "tier": "Intermediário",
                        "gpus": ["RTX 4080", "RTX 3090"],
                        "price_per_hour": "$0.40-0.60",
                        "performance": "Bom equilíbrio entre custo e performance",
                        "use_cases": ["Fine-tuning médio", "Inferência avançada", "Produção leve"]
                    },
                    {
                        "tier": "Rápido",
                        "gpus": ["RTX 4090", "A5000"],
                        "price_per_hour": "$0.70-1.00",
                        "performance": "Alta performance para projetos exigentes",
                        "use_cases": ["Fine-tuning avançado", "Inferência em larga escala", "Produção pesada"]
                    },
                    {
                        "tier": "Premium",
                        "gpus": ["A6000", "H100"],
                        "price_per_hour": "$1.50-3.00",
                        "performance": "Máxima performance para projetos críticos",
                        "use_cases": ["Treinamento do zero", "LLMs grandes", "Produção empresarial"]
                    }
                ],
                "explanation": "Encontrei 4 opções de preço para seu projeto. Cada uma com diferentes níveis de performance e custo."
            }
        
        # Se pedir seleção ou escolher opção, progredir para selection
        elif wants_selection or "escolher" in user_input:
            # Verificar se está escolhendo opção específica ou pedindo seleção automática
            if "automaticamente" in user_input or "melhor máquina" in user_input:
                return {
                    "stage": "reservation",
                    "needs_more_info": False,
                    "reservation": {
                        "status": "ready",
                        "details": "Máquina selecionada automaticamente: RTX 4090 (24GB VRAM) - $0.85/hora. Pronta para reserva."
                    },
                    "explanation": "Selecionei automaticamente a melhor máquina para seu projeto. Está pronta para ser reservada."
                }
            else:
                return {
                    "stage": "selection",
                    "needs_more_info": False,
                    "selection_mode": "automatic",
                    "machines": [
                        {
                            "id": "machine_001",
                            "name": "GPU Cloud Basic",
                            "gpu": "RTX 4080",
                            "vram": "16GB",
                            "price_per_hour": "$0.45",
                            "location": "US East",
                            "available": True
                        },
                        {
                            "id": "machine_002",
                            "name": "GPU Cloud Pro",
                            "gpu": "RTX 4090",
                            "vram": "24GB",
                            "price_per_hour": "$0.85",
                            "location": "US West",
                            "available": True
                        },
                        {
                            "id": "machine_003",
                            "name": "GPU Cloud Enterprise",
                            "gpu": "A6000",
                            "vram": "48GB",
                            "price_per_hour": "$1.80",
                            "location": "EU Central",
                            "available": True
                        }
                    ],
                    "explanation": "Selecionei as melhores máquinas disponíveis para seu projeto. Você pode escolher manualmente ou usar a seleção automática."
                }
        
        # Se pedir reserva, progredir para reservation
        elif wants_reservation or "reservar" in user_input:
            return {
                "stage": "reservation",
                "needs_more_info": False,
                "reservation": {
                    "status": "ready",
                    "details": "Máquina selecionada e pronta para reserva. Prossiga com o pagamento para ativar."
                },
                "explanation": "Sua máquina está pronta para ser reservada. Complete o processo para começar a usar."
            }
        
        # Se tiver projeto e modelo mas sem orçamento, perguntar sobre orçamento
        elif has_project_type and has_model:
            return {
                "stage": "analysis",
                "needs_more_info": True,
                "questions": [
                    "Qual seu orçamento aproximado por hora? (ex: $20, $50, $100+)"
                ],
                "explanation": "Já entendo seu projeto e modelo. Preciso saber seu orçamento para recomendar as melhores opções."
            }
        
        # Se tiver apenas informações básicas, perguntar mais detalhes
        else:
            return {
                "stage": "analysis",
                "needs_more_info": True,
                "questions": [
                    "Por favor, descreva melhor seu projeto (ex: fine-tuning, inferência, treinamento).",
                    "Qual modelo de IA você pretende usar? (ex: LLaMA, Stable Diffusion, YOLO)",
                    "Qual seu orçamento aproximado por hora?"
                ],
                "explanation": "Preciso entender melhor seu projeto para recomendar as melhores opções de GPU."
            }

    async def _perform_real_research(self, user_query: str) -> Dict[str, Any]:
        """
        Realiza pesquisa real usando gpt-4o-search-preview
        """
        research_prompt = f"""
        Pesquise informações atualizadas sobre GPUs e benchmarks para: {user_query}
        
        Retorne um JSON com:
        {{
          "findings": "descobertas principais sobre o projeto",
          "benchmarks": "benchmarks de performance atualizados",
          "prices": "preços atuais de mercado",
          "recommendations": "recomendações específicas"
        }}
        
        Use informações reais de 2024 sobre GPUs, preços e performance.
        """
        
        research_messages = [
            {"role": "system", "content": research_prompt},
            {"role": "user", "content": user_query}
        ]
        
        # Usar gpt-4o-search-preview para pesquisa
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-search-preview",
                    "messages": research_messages,
                    "temperature": 0.1,
                    "max_tokens": 500
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Tentar extrair JSON
                import json
                import re
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
                        
            # Fallback se pesquisa falhar
            return {
                "findings": "Projeto identificado. Pesquisando melhores opções de GPU.",
                "benchmarks": "Analisando performance para modelos específicos.",
                "prices": "Verificando preços atuais no mercado.",
                "recommendations": "Baseado no projeto, recomendo GPUs com VRAM adequada."
            }

        # Singleton instance
ai_wizard_service = AIWizardService()
