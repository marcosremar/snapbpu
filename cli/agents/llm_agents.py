#!/usr/bin/env python3
"""
LLM Agents para Dumont Cloud CLI

Sistema de agentes que usam o CLI como usuários reais:
- Executor: Realiza tarefas
- Corretor: Identifica e corrige erros
- Verificador: Valida resultados

Uso:
    python agents/llm_agents.py

Requer:
    - OPENROUTER_API_KEY no ambiente (ou hardcoded)
    - Backend rodando em localhost:8000

Modelos suportados:
    - x-ai/grok-code-fast-1 (default via OpenRouter)
    - groq/llama-3.3-70b-versatile
    - anthropic/claude-sonnet-4
"""

import os
import sys
import json
import subprocess
import time
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime


# =============================================================================
# LOGGER EM TEMPO REAL
# =============================================================================

class LiveLogger:
    """Logger que mostra status em tempo real e salva em arquivo."""

    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "logs"
        )
        os.makedirs(self.log_dir, exist_ok=True)

        # Arquivo de log da sessão
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"session_{self.session_id}.log")
        self.json_file = os.path.join(self.log_dir, f"session_{self.session_id}.json")

        # Estado
        self.events: List[Dict] = []
        self.current_task = None
        self.current_agent = None
        self.spinner_active = False
        self._spinner_thread = None

        # Inicia arquivo de log
        self._write_log(f"=== SESSÃO INICIADA: {self.session_id} ===\n")

    def _write_log(self, message: str):
        """Escreve no arquivo de log."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

    def _save_json(self):
        """Salva eventos em JSON."""
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(self.events, f, indent=2, default=str, ensure_ascii=False)

    def status(self, message: str, emoji: str = "🔄"):
        """Mostra status em tempo real."""
        line = f"{emoji} {message}"
        print(f"\r{line:<80}", end="", flush=True)
        self._write_log(message)

    def info(self, message: str, emoji: str = "ℹ️"):
        """Mostra informação."""
        print(f"\n{emoji} {message}")
        self._write_log(message)

    def success(self, message: str):
        """Mostra sucesso."""
        print(f"\n✅ {message}")
        self._write_log(f"SUCCESS: {message}")

    def error(self, message: str):
        """Mostra erro."""
        print(f"\n❌ {message}")
        self._write_log(f"ERROR: {message}")

    def warning(self, message: str):
        """Mostra aviso."""
        print(f"\n⚠️ {message}")
        self._write_log(f"WARNING: {message}")

    def task_start(self, task: str, task_num: int, total: int):
        """Inicia uma nova tarefa."""
        self.current_task = task
        header = f"\n{'='*70}\n📋 TAREFA [{task_num}/{total}]: {task}\n{'='*70}"
        print(header)
        self._write_log(f"\n=== TAREFA {task_num}/{total}: {task} ===")

        self.events.append({
            "type": "task_start",
            "task": task,
            "task_num": task_num,
            "total": total,
            "timestamp": datetime.now().isoformat()
        })

    def agent_start(self, agent_name: str, action: str):
        """Inicia ação de um agente."""
        self.current_agent = agent_name
        emoji = {"executor": "🤖", "corrector": "🔧", "verifier": "✔️"}.get(agent_name, "🔹")
        print(f"\n{emoji} [{agent_name.upper()}] {action}")
        self._write_log(f"[{agent_name.upper()}] {action}")

        self.events.append({
            "type": "agent_action",
            "agent": agent_name,
            "action": action,
            "timestamp": datetime.now().isoformat()
        })

    def llm_call(self, provider: str, model: str):
        """Registra chamada ao LLM."""
        self.status(f"Consultando {provider} ({model})...", "🧠")

    def llm_response(self, response: str):
        """Registra resposta do LLM."""
        # Trunca para exibição
        display = response[:200] + "..." if len(response) > 200 else response
        print(f"\n   💬 Resposta: {display}")
        self._write_log(f"LLM Response: {response}")

        self.events.append({
            "type": "llm_response",
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

    def cli_execute(self, command: List[str]):
        """Registra execução de comando CLI."""
        cmd_str = "dumont " + " ".join(command)
        self.status(f"Executando: {cmd_str}", "⚡")
        self._write_log(f"CLI Execute: {cmd_str}")

    def cli_result(self, success: bool, output: str, duration: float):
        """Registra resultado do CLI."""
        status_emoji = "✅" if success else "❌"
        print(f"\n   {status_emoji} Resultado: {'OK' if success else 'ERRO'} ({duration:.2f}s)")

        # Mostra output truncado
        if output:
            lines = output.strip().split('\n')[:5]
            for line in lines:
                print(f"   │ {line[:80]}")
            if len(output.strip().split('\n')) > 5:
                print(f"   │ ... (+{len(output.strip().split(chr(10))) - 5} linhas)")

        self._write_log(f"CLI Result: success={success}, duration={duration:.2f}s")
        self._write_log(f"Output: {output[:500]}")

        self.events.append({
            "type": "cli_result",
            "success": success,
            "output": output[:2000],
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })

    def task_complete(self, status: str, summary: str):
        """Finaliza uma tarefa."""
        emoji = {"success": "✅", "partial": "⚠️", "failure": "❌"}.get(status, "❓")
        print(f"\n{emoji} Status: {status.upper()}")
        print(f"   📝 {summary}")
        self._write_log(f"Task Complete: {status} - {summary}")

        self.events.append({
            "type": "task_complete",
            "status": status,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        })

        # Salva JSON após cada tarefa
        self._save_json()

    def session_summary(self, results: List[Dict]):
        """Mostra resumo da sessão."""
        success = sum(1 for r in results if r.get("final_status") == "success")
        partial = sum(1 for r in results if r.get("final_status") == "partial")
        failure = sum(1 for r in results if r.get("final_status") == "failure")

        print(f"\n{'='*70}")
        print("📊 RESUMO DA SESSÃO")
        print(f"{'='*70}")
        print(f"   Total: {len(results)} tarefas")
        print(f"   ✅ Sucesso: {success}")
        print(f"   ⚠️ Parcial: {partial}")
        print(f"   ❌ Falha: {failure}")
        print(f"\n   📁 Logs salvos em:")
        print(f"      • {self.log_file}")
        print(f"      • {self.json_file}")
        print(f"{'='*70}\n")

        self._write_log(f"\n=== RESUMO: {success} success, {partial} partial, {failure} failure ===")
        self._save_json()


# Instância global do logger
logger = LiveLogger()

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# CONFIGURACAO
# =============================================================================

CLI_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = "/home/marcos/dumontcloud/.venv/bin/python"
CLI_SCRIPT = f"{CLI_PATH}/dumont_cli.py"

# Provedor de LLM (openrouter, xai, groq ou anthropic)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openrouter")  # Default: OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Modelos
OPENROUTER_MODEL = "x-ai/grok-code-fast-1"  # Grok Code via OpenRouter
XAI_MODEL = "grok-code-fast-1"  # Modelo X.AI direto
GROQ_MODEL = "llama-3.3-70b-versatile"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


# =============================================================================
# CLI RUNNER
# =============================================================================

@dataclass
class CLIResult:
    """Resultado de um comando CLI"""
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration: float

    @property
    def success(self) -> bool:
        return self.returncode == 0

    @property
    def output(self) -> str:
        return self.stdout + self.stderr

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "success": self.success,
            "output": self.output[:2000],  # Trunca para não sobrecarregar LLM
            "duration": f"{self.duration:.2f}s"
        }


def run_cli(*args, timeout: int = 60) -> CLIResult:
    """Executa comando no CLI"""
    cmd = [VENV_PYTHON, CLI_SCRIPT] + list(args)
    cmd_str = "dumont " + " ".join(args)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=CLI_PATH,
            env={**os.environ, "PYTHONPATH": "/home/marcos/dumontcloud"}
        )
        elapsed = time.time() - start

        return CLIResult(
            command=cmd_str,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=elapsed
        )
    except subprocess.TimeoutExpired:
        return CLIResult(
            command=cmd_str,
            returncode=-1,
            stdout="",
            stderr=f"Timeout after {timeout}s",
            duration=timeout
        )
    except Exception as e:
        return CLIResult(
            command=cmd_str,
            returncode=-1,
            stdout="",
            stderr=str(e),
            duration=time.time() - start
        )


# =============================================================================
# LLM CLIENT
# =============================================================================

def call_llm(messages: List[Dict], system: str = None) -> str:
    """Chama o LLM (OpenRouter, X.AI Grok, Groq ou Anthropic)"""

    if LLM_PROVIDER == "openrouter" and OPENROUTER_API_KEY:
        logger.llm_call("OpenRouter", OPENROUTER_MODEL)
        response = call_openrouter(messages, system)
        logger.llm_response(response)
        return response
    elif LLM_PROVIDER == "xai" and XAI_API_KEY:
        logger.llm_call("X.AI", XAI_MODEL)
        response = call_xai(messages, system)
        logger.llm_response(response)
        return response
    elif LLM_PROVIDER == "groq" and GROQ_API_KEY:
        logger.llm_call("Groq", GROQ_MODEL)
        response = call_groq(messages, system)
        logger.llm_response(response)
        return response
    elif ANTHROPIC_API_KEY:
        logger.llm_call("Anthropic", ANTHROPIC_MODEL)
        response = call_anthropic(messages, system)
        logger.llm_response(response)
        return response
    else:
        # Fallback: simula resposta
        logger.llm_call("Simulador", "local")
        response = simulate_llm_response(messages)
        logger.llm_response(response)
        return response


def call_openrouter(messages: List[Dict], system: str = None) -> str:
    """Chama OpenRouter API (x-ai/grok-code-fast-1)"""
    import requests

    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://dumont.cloud",
                "X-Title": "Dumont Cloud CLI Agents"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": all_messages,
                "temperature": 0.3,
                "max_tokens": 2000
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        # Fallback para simulação
        return simulate_llm_response(messages)


def call_xai(messages: List[Dict], system: str = None) -> str:
    """Chama X.AI Grok API (compatível com OpenAI)"""
    import requests

    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": XAI_MODEL,
            "messages": all_messages,
            "temperature": 0.3,
            "max_tokens": 2000
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_groq(messages: List[Dict], system: str = None) -> str:
    """Chama Groq API"""
    import requests

    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": all_messages,
            "temperature": 0.3,
            "max_tokens": 2000
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_anthropic(messages: List[Dict], system: str = None) -> str:
    """Chama Anthropic API"""
    import requests

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 2000,
            "system": system or "",
            "messages": messages
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["content"][0]["text"]


def simulate_llm_response(messages: List[Dict]) -> str:
    """Simula resposta LLM quando API não disponível - modo inteligente"""
    last_msg = messages[-1]["content"] if messages else ""
    msg_lower = last_msg.lower()

    # PRIMEIRO: Verificar se é contexto do VERIFICADOR (tem prioridade)
    if "tarefa original" in msg_lower and "foi cumprida" in msg_lower:
        # Detecta padrões de sucesso no output
        if "sucesso: true" in msg_lower or "✅ success" in msg_lower or "200)" in msg_lower:
            return json.dumps({
                "status": "success",
                "verified": True,
                "summary": "Comando executado com sucesso, dados retornados corretamente",
                "issues": []
            })
        elif any(ind in msg_lower for ind in ["erro", "error", "401", "403", "404", "500", "timeout", "failed"]):
            return json.dumps({
                "status": "failure",
                "verified": False,
                "summary": "Comando falhou",
                "issues": ["Verificar logs e tentar novamente"]
            })
        else:
            return json.dumps({
                "status": "partial",
                "verified": True,
                "summary": "Comando executado, resultado pode estar incompleto",
                "issues": []
            })

    # SEGUNDO: Verificar se é contexto do CORRETOR
    if "resultado: erro" in msg_lower or "analise o erro" in msg_lower:
        if "401" in msg_lower or "unauthorized" in msg_lower:
            return json.dumps({"diagnosis": "Nao autenticado", "action": "retry", "command": ["auth", "login", "test@test.com", "test123"]})
        elif "not found" in msg_lower or "404" in msg_lower:
            return json.dumps({"diagnosis": "Recurso nao encontrado", "action": "alternative", "command": ["instance", "list"]})
        elif "rate limit" in msg_lower or "429" in msg_lower:
            return json.dumps({"diagnosis": "Rate limit atingido", "action": "retry", "reason": "Esperar e tentar novamente"})
        else:
            return json.dumps({"diagnosis": "Erro generico", "action": "abort", "reason": "Verificar logs"})

    # TERCEIRO: Mapping de intenções para comandos CLI (EXECUTOR)
    intent_map = [
        # Instâncias
        (["listar", "list", "maquinas", "instancias", "rodando"],
         {"action": "execute", "command": ["instance", "list"], "reason": "Listando instancias"}),
        (["ofertas", "offers", "gpu", "rtx", "disponiv"],
         {"action": "execute", "command": ["instance", "offers"], "reason": "Buscando ofertas GPU"}),
        (["criar", "create", "provisionar", "deploy"],
         {"action": "execute", "command": ["instance", "offers"], "reason": "Primeiro buscar ofertas"}),
        (["pausar", "pause", "parar"],
         {"action": "clarify", "reason": "Preciso do ID da instancia para pausar"}),
        (["deletar", "delete", "remover", "destruir"],
         {"action": "clarify", "reason": "Preciso do ID da instancia para deletar"}),

        # Saldo e conta
        (["saldo", "balance", "credito", "dinheiro", "conta"],
         {"action": "execute", "command": ["balance", "list"], "reason": "Verificando saldo"}),
        (["usuario", "me", "quem sou", "minha conta"],
         {"action": "execute", "command": ["auth", "me"], "reason": "Info do usuario"}),

        # Failover e Standby
        (["standby", "cpu standby", "failover status"],
         {"action": "execute", "command": ["standby", "status"], "reason": "Status CPU Standby"}),
        (["warmpool", "warm pool", "hosts"],
         {"action": "execute", "command": ["warmpool", "hosts"], "reason": "Hosts warm pool"}),

        # Métricas
        (["metrica", "metric", "mercado", "market"],
         {"action": "execute", "command": ["metrics", "market"], "reason": "Metricas de mercado"}),
        (["spot", "preco", "disponibilidade"],
         {"action": "execute", "command": ["spot", "availability"], "reason": "Disponibilidade spot"}),

        # Settings
        (["config", "settings", "configurac"],
         {"action": "execute", "command": ["settings", "get"], "reason": "Configuracoes"}),

        # Snapshots
        (["snapshot", "backup"],
         {"action": "execute", "command": ["snapshot", "list"], "reason": "Listando snapshots"}),
    ]

    # Busca a melhor correspondência
    for keywords, response in intent_map:
        if any(kw in msg_lower for kw in keywords):
            return json.dumps(response)

    # Default: mostra help
    return json.dumps({"action": "execute", "command": ["help"], "reason": "Mostrando ajuda disponivel"})


# =============================================================================
# AGENTES
# =============================================================================

@dataclass
class AgentAction:
    """Acao de um agente"""
    agent: str
    action: str
    command: Optional[List[str]] = None
    result: Optional[CLIResult] = None
    analysis: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class ExecutorAgent:
    """
    Agente EXECUTOR

    Responsavel por executar tarefas usando o CLI.
    Recebe instrucoes em linguagem natural e traduz para comandos.
    """

    SYSTEM_PROMPT = """Voce e o EXECUTOR, um agente que usa o Dumont Cloud CLI.

Seu trabalho:
1. Receber tarefas em linguagem natural
2. Traduzir para comandos CLI com os parametros corretos
3. Executar e reportar resultados

Comandos disponiveis:

INSTANCIAS:
- dumont instance list                              # Lista todas instancias
- dumont instance list status=running               # Lista apenas maquinas rodando
- dumont instance list status=stopped               # Lista apenas maquinas paradas
- dumont instance offers                            # Lista ofertas GPU (sem filtro)
- dumont instance offers gpu_name="RTX 3060"        # Filtra por GPU especifica
- dumont instance offers max_price=0.10             # Filtra por preco maximo $/hora
- dumont instance offers gpu_name="RTX 3060" max_price=0.10  # Combina filtros
- dumont instance create <offer_id>                 # Cria instancia
- dumont instance delete <instance_id>              # Deleta instancia
- dumont instance pause <instance_id>               # Pausa instancia
- dumont instance resume <instance_id>              # Resume instancia

DEPLOY AUTOMATICO:
- dumont wizard deploy "RTX 4090"                   # Deploy GPU especifica
- dumont wizard deploy gpu="RTX 4090" price=1.5     # Com preco maximo

AUTENTICACAO:
- dumont auth me                                    # Info do usuario
- dumont balance list                               # Saldo da conta

FAILOVER (CPU Standby e Warm Pool):
- dumont standby status                             # Status do sistema de failover/standby
- dumont standby associate <gpu_id>                 # Associa CPU standby a GPU
- dumont standby pricing                            # Precos/custo do servico de CPU standby
- dumont warmpool hosts                             # Lista hosts para warm pool
- dumont warmpool status <machine_id>               # Status de um host

METRICAS E ANALYTICS:
- dumont metrics market                             # Metricas de mercado
- dumont metrics providers                          # Ranking de provedores
- dumont metrics efficiency                         # GPUs mais eficientes (performance/preco)
- dumont spot availability                          # Disponibilidade spot
- dumont spot llm-gpus                              # GPUs recomendadas para LLMs

ECONOMIA (Saving):
- dumont saving summary                             # Resumo de economia total
- dumont saving estimate                            # Estimativa de economia

Responda SEMPRE em JSON:
{
    "action": "execute|skip|clarify",
    "command": ["arg1", "arg2", ...],  // Argumentos para o CLI
    "reason": "Explicacao curta"
}

Exemplos:
- Tarefa: "Listar minhas maquinas"
  {"action": "execute", "command": ["instance", "list"], "reason": "Listando instancias"}

- Tarefa: "Ofertas de RTX 3060 ate $0.10"
  {"action": "execute", "command": ["instance", "offers", "gpu_name=RTX 3060", "max_price=0.10"], "reason": "Buscando RTX 3060 baratas"}

- Tarefa: "Status do failover"
  {"action": "execute", "command": ["standby", "status"], "reason": "Verificando sistema de failover"}

- Tarefa: "Quanto custa o standby?"
  {"action": "execute", "command": ["standby", "pricing"], "reason": "Verificando precos do CPU standby"}

- Tarefa: "Quanto economizei?"
  {"action": "execute", "command": ["saving", "summary"], "reason": "Resumo de economia"}

- Tarefa: "GPUs boas para LLM"
  {"action": "execute", "command": ["spot", "llm-gpus"], "reason": "Ranking de GPUs para LLMs"}

- Tarefa: "GPUs mais eficientes"
  {"action": "execute", "command": ["metrics", "efficiency"], "reason": "Ranking de GPUs por eficiencia"}

- Tarefa: "Ranking dos provedores"
  {"action": "execute", "command": ["metrics", "providers"], "reason": "Ranking de provedores"}

- Tarefa: "Deletar tudo"
  {"action": "clarify", "reason": "Preciso saber quais instancias deletar"}
"""

    def __init__(self):
        self.history: List[AgentAction] = []

    def execute(self, task: str) -> AgentAction:
        """Executa uma tarefa"""
        logger.agent_start("executor", f"Analisando tarefa: {task}")

        # Pede ao LLM para decidir
        response = call_llm(
            messages=[{"role": "user", "content": f"Tarefa: {task}"}],
            system=self.SYSTEM_PROMPT
        )

        # Parse da resposta
        try:
            decision = json.loads(response)
        except:
            # Tenta extrair JSON da resposta
            import re
            match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if match:
                decision = json.loads(match.group())
            else:
                decision = {"action": "skip", "reason": "Nao entendi a resposta"}

        action = AgentAction(
            agent="executor",
            action=decision.get("action", "skip"),
            command=decision.get("command"),
            analysis=decision.get("reason", "")
        )

        # Executa comando se necessario
        if action.action == "execute" and action.command:
            logger.cli_execute(action.command)
            action.result = run_cli(*action.command)
            logger.cli_result(action.result.success, action.result.output, action.result.duration)
        elif action.action == "clarify":
            logger.warning(f"Precisa esclarecimento: {action.analysis}")
        elif action.action == "skip":
            logger.info(f"Pulando: {action.analysis}")

        self.history.append(action)
        return action


class CorrectorAgent:
    """
    Agente CORRETOR

    Analisa erros e sugere correcoes.
    """

    SYSTEM_PROMPT = """Voce e o CORRETOR, um agente que analisa erros do Dumont Cloud CLI.

Seu trabalho:
1. Analisar resultados de comandos que falharam
2. Identificar a causa do erro
3. Sugerir comando corrigido ou acao alternativa

Responda SEMPRE em JSON:
{
    "diagnosis": "O que causou o erro",
    "action": "retry|alternative|abort",
    "command": ["arg1", "arg2", ...],  // Comando corrigido
    "reason": "Explicacao da correcao"
}

Exemplos de erros comuns:
- "Instance not found" -> Verificar ID correto com instance list
- "401 Unauthorized" -> Fazer login novamente com auth login
- "Rate limit" -> Esperar e tentar novamente
- "No offers found" -> Relaxar filtros (aumentar max_price)
"""

    def __init__(self):
        self.history: List[AgentAction] = []

    def analyze(self, failed_action: AgentAction) -> AgentAction:
        """Analisa uma acao que falhou"""
        logger.agent_start("corrector", "Analisando erro e buscando correção...")

        context = f"""
Comando executado: {failed_action.command}
Resultado: ERRO
Output: {failed_action.result.output if failed_action.result else 'N/A'}

Analise o erro e sugira correcao.
"""

        response = call_llm(
            messages=[{"role": "user", "content": context}],
            system=self.SYSTEM_PROMPT
        )

        try:
            decision = json.loads(response)
        except:
            import re
            match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if match:
                decision = json.loads(match.group())
            else:
                decision = {"action": "abort", "diagnosis": "Nao consegui analisar"}

        action = AgentAction(
            agent="corrector",
            action=decision.get("action", "abort"),
            command=decision.get("command"),
            analysis=f"{decision.get('diagnosis', '')} - {decision.get('reason', '')}"
        )

        # Executa correcao se for retry
        if action.action == "retry" and action.command:
            logger.info(f"Tentando correção: {' '.join(action.command)}")
            logger.cli_execute(action.command)
            action.result = run_cli(*action.command)
            logger.cli_result(action.result.success, action.result.output, action.result.duration)
        elif action.action == "abort":
            logger.warning(f"Abortando: {action.analysis}")

        self.history.append(action)
        return action


class VerifierAgent:
    """
    Agente VERIFICADOR

    Valida resultados e confirma sucesso.
    """

    SYSTEM_PROMPT = """Voce e o VERIFICADOR, um agente que valida resultados do Dumont Cloud CLI.

Seu trabalho:
1. Analisar resultado de comandos executados
2. Verificar se a tarefa original foi cumprida
3. Confirmar sucesso ou indicar problemas

Responda SEMPRE em JSON:
{
    "status": "success|partial|failure",
    "verified": true/false,
    "summary": "Resumo do que foi feito",
    "issues": ["problema1", "problema2"],  // Lista vazia se tudo OK
    "next_steps": ["sugestao1"]  // Opcional
}
"""

    def __init__(self):
        self.history: List[AgentAction] = []

    def _summarize_output(self, output: str) -> str:
        """Cria um resumo estruturado do output para o Verifier"""
        if not output:
            return "N/A"

        # Tenta parsear como JSON para extrair informações úteis
        try:
            # Remove linhas de status do CLI (🔄, ✅, etc)
            lines = output.strip().split('\n')
            json_start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('{') or line.strip().startswith('['):
                    json_start = i
                    break

            json_text = '\n'.join(lines[json_start:])
            data = json.loads(json_text)

            # Gera resumo baseado no tipo de dados
            if isinstance(data, dict):
                if "instances" in data:
                    instances = data["instances"]
                    running = len([i for i in instances if i.get("status") == "running"])
                    stopped = len([i for i in instances if i.get("status") == "stopped"])
                    return f"Retornou {len(instances)} instancias (running: {running}, stopped: {stopped}). Dados completos recebidos."
                elif "hosts" in data:
                    hosts = data["hosts"]
                    return f"Retornou {len(hosts)} hosts para warm pool. Dados completos recebidos."
                elif "offers" in data:
                    offers = data["offers"]
                    return f"Retornou {len(offers)} ofertas de GPU. Dados completos recebidos."
                elif "credit" in data or "balance" in data:
                    return f"Retornou dados de saldo: credit={data.get('credit', 'N/A')}, balance={data.get('balance', 'N/A')}. Dados completos."
                elif "associations" in data:
                    assocs = data.get("associations", [])
                    return f"Retornou {len(assocs)} associações de standby. configured={data.get('configured', False)}. Dados completos."
                else:
                    # Resumo genérico
                    keys = list(data.keys())[:5]
                    return f"Retornou objeto com campos: {', '.join(keys)}. Dados completos recebidos."
            elif isinstance(data, list):
                return f"Retornou lista com {len(data)} items. Dados completos recebidos."
            else:
                return output[:500]
        except:
            # Se não for JSON, retorna preview com nota
            preview = output[:800]
            if len(output) > 800:
                return f"{preview}\n... (output continua, {len(output)} caracteres total)"
            return preview

    def verify(self, original_task: str, action: AgentAction) -> AgentAction:
        """Verifica se a tarefa foi cumprida"""
        logger.agent_start("verifier", "Validando resultado...")

        # Gera resumo estruturado do output
        output_summary = self._summarize_output(action.result.output if action.result else None)

        context = f"""
Tarefa original: {original_task}
Comando executado: {action.command}
Sucesso: {action.result.success if action.result else 'N/A'}
Output: {output_summary}

A tarefa foi cumprida corretamente?
"""

        response = call_llm(
            messages=[{"role": "user", "content": context}],
            system=self.SYSTEM_PROMPT
        )

        try:
            decision = json.loads(response)
        except:
            import re
            match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if match:
                decision = json.loads(match.group())
            else:
                decision = {"status": "failure", "verified": False}

        verification = AgentAction(
            agent="verifier",
            action=decision.get("status", "failure"),
            analysis=decision.get("summary", "")
        )

        # Registra resultado da verificação
        logger.task_complete(verification.action, verification.analysis)

        self.history.append(verification)
        return verification


# =============================================================================
# ORQUESTRADOR
# =============================================================================

class AgentOrchestrator:
    """
    Orquestra os agentes para executar tarefas completas.

    Fluxo:
    1. Executor recebe tarefa
    2. Se erro -> Corretor analisa e tenta corrigir
    3. Verificador valida resultado final
    """

    def __init__(self):
        self.executor = ExecutorAgent()
        self.corrector = CorrectorAgent()
        self.verifier = VerifierAgent()
        self.session_log: List[Dict] = []

    def run_task(self, task: str, task_num: int = 1, total: int = 1, max_retries: int = 2) -> Dict:
        """Executa uma tarefa com os 3 agentes"""
        logger.task_start(task, task_num, total)

        log_entry = {
            "task": task,
            "start_time": datetime.now().isoformat(),
            "actions": [],
            "final_status": None
        }

        # Passo 1: Executor tenta a tarefa
        action = self.executor.execute(task)
        log_entry["actions"].append({
            "agent": "executor",
            "command": action.command,
            "success": action.result.success if action.result else None,
            "analysis": action.analysis
        })

        # Passo 2: Se falhou OU pediu esclarecimento, Corretor tenta corrigir
        retries = 0
        needs_correction = (
            (action.result and not action.result.success) or  # Comando falhou
            (action.action == "clarify") or  # Pediu esclarecimento
            (action.command is None)  # Não executou nada
        )

        while needs_correction and retries < max_retries:
            retries += 1
            logger.info(f"Tentativa de correção {retries}/{max_retries}", "🔧")

            correction = self.corrector.analyze(action)
            log_entry["actions"].append({
                "agent": "corrector",
                "command": correction.command,
                "success": correction.result.success if correction.result else None,
                "analysis": correction.analysis
            })

            if correction.result and correction.result.success:
                action = correction  # Usa resultado corrigido
                break
            elif correction.action == "abort":
                break

            needs_correction = correction.result and not correction.result.success

        # Passo 3: Verificador valida
        verification = self.verifier.verify(task, action)
        log_entry["actions"].append({
            "agent": "verifier",
            "status": verification.action,
            "analysis": verification.analysis
        })

        log_entry["final_status"] = verification.action
        log_entry["end_time"] = datetime.now().isoformat()

        self.session_log.append(log_entry)
        return log_entry

    def run_session(self, tasks: List[str]) -> List[Dict]:
        """Executa uma sessao com multiplas tarefas"""
        # Determina modelo em uso
        model_info = {
            "openrouter": f"OpenRouter ({OPENROUTER_MODEL})",
            "xai": f"X.AI Grok ({XAI_MODEL})",
            "groq": f"Groq ({GROQ_MODEL})",
            "anthropic": f"Anthropic ({ANTHROPIC_MODEL})"
        }.get(LLM_PROVIDER, "Simulado (sem API key)")

        print("\n" + "="*70)
        print("🚀 DUMONT CLOUD - AGENTES LLM")
        print("="*70)
        print(f"   📊 Tarefas: {len(tasks)}")
        print(f"   🧠 Modelo: {model_info}")
        print(f"   📁 Logs: {logger.log_dir}")
        print("="*70)

        results = []
        for i, task in enumerate(tasks, 1):
            result = self.run_task(task, task_num=i, total=len(tasks))
            results.append(result)
            time.sleep(0.5)  # Rate limiting

        # Mostra resumo final
        logger.session_summary(results)
        return results


# =============================================================================
# MAIN
# =============================================================================

def demo_session():
    """Sessao de demonstracao"""

    # Primeiro faz login
    logger.info("Fazendo login no Dumont Cloud...", "🔐")
    login_result = run_cli("auth", "login", "test@test.com", "test123")
    if not login_result.success:
        logger.error(f"Erro no login: {login_result.output}")
        return
    logger.success("Login realizado com sucesso!")

    # Suite completa de tarefas para testar robustez
    # Organizadas por categoria para cobertura máxima
    tasks = [
        # === CONSULTAS BÁSICAS ===
        "Quero ver meu saldo na conta",
        "Mostra minhas credenciais de usuario",

        # === LISTAGEM DE INSTÂNCIAS ===
        "Lista todas as minhas maquinas rodando",
        "Quais instancias estao paradas?",

        # === BUSCA DE OFERTAS COM FILTROS ===
        "Mostra as ofertas de GPU RTX 3060 ate $0.10/hora",
        "Quero ver GPUs baratas, menos de 5 centavos por hora",
        "Tem alguma RTX 4090 disponivel?",

        # === FAILOVER E STANDBY ===
        "Qual o status do sistema de failover?",
        "Mostra as associacoes de standby ativas",
        "Quanto custa o servico de CPU standby?",

        # === WARM POOL ===
        "Quais hosts estao disponiveis para warm pool?",

        # === MÉTRICAS E ANALYTICS ===
        "Como esta o mercado de GPUs agora?",
        "Quais sao as GPUs mais eficientes?",
        "Mostra o ranking dos provedores",

        # === SAVINGS ===
        "Quanto eu economizei usando Dumont?",
        "Mostra meu historico de economia",

        # === CONFIGURAÇÕES ===
        "Quais sao minhas configuracoes atuais?",
    ]

    # Executa sessao
    orchestrator = AgentOrchestrator()
    orchestrator.run_session(tasks)


def test_all_commands():
    """
    Testa TODOS os comandos do CLI automaticamente.

    1. Lê o help do CLI
    2. Extrai todos os comandos disponíveis
    3. Testa cada um (exceto os perigosos)
    4. Gera relatório completo
    """
    import re

    print("\n" + "="*70)
    print("🔬 TESTE AUTOMÁTICO DE TODOS OS COMANDOS DO CLI")
    print("="*70)

    # Login primeiro
    logger.info("Fazendo login...", "🔐")
    login_result = run_cli("auth", "login", "test@test.com", "test123")
    if not login_result.success:
        logger.error(f"Erro no login: {login_result.output}")
        return
    logger.success("Login OK!")

    # Lê o help
    logger.info("Lendo comandos disponíveis (dumont help)...", "📖")
    help_result = run_cli("help")
    if not help_result.success:
        logger.error("Não consegui ler o help")
        return

    # Extrai comandos do help
    # Formato: "📦 RESOURCE" seguido de "  - action    Description"
    commands = []
    current_resource = None

    for line in help_result.output.split('\n'):
        # Detecta recurso: "📦 INSTANCE" ou "📦 AI-WIZARD"
        resource_match = re.match(r'📦\s+([\w-]+)', line)
        if resource_match:
            current_resource = resource_match.group(1).lower()
            continue

        # Detecta ação: "  - list            List Instances"
        action_match = re.match(r'\s+-\s+(\w+)\s+(.+)', line)
        if action_match and current_resource:
            action = action_match.group(1)
            description = action_match.group(2).strip()
            commands.append({
                "resource": current_resource,
                "action": action,
                "description": description,
                "command": f"{current_resource} {action}"
            })

    print(f"\n📋 Encontrados {len(commands)} comandos")

    # Comandos perigosos que NÃO devem ser executados
    dangerous = [
        "delete", "destroy", "remove", "cleanup",
        "create", "provision", "execute", "failover",
        "update", "configure", "enable", "disable",
        "login", "logout", "register"  # Auth já foi feito
    ]

    # Filtra comandos seguros (somente leitura)
    safe_commands = [
        cmd for cmd in commands
        if cmd["action"] not in dangerous
    ]

    print(f"🔒 {len(safe_commands)} comandos seguros para testar")
    print(f"⚠️  {len(commands) - len(safe_commands)} comandos perigosos ignorados")

    # Testa cada comando
    results = []

    for i, cmd in enumerate(safe_commands, 1):
        print(f"\n{'─'*60}")
        print(f"[{i}/{len(safe_commands)}] 🧪 Testando: dumont {cmd['command']}")
        print(f"    📝 {cmd['description']}")

        result = run_cli(cmd["resource"], cmd["action"])

        status = "✅ OK" if result.success else "❌ ERRO"
        print(f"    {status} ({result.duration:.2f}s)")

        # Mostra preview do output
        if result.output:
            lines = result.output.strip().split('\n')[:3]
            for line in lines:
                print(f"    │ {line[:70]}")

        results.append({
            "command": cmd["command"],
            "description": cmd["description"],
            "success": result.success,
            "duration": result.duration,
            "output_preview": result.output[:500] if result.output else ""
        })

        time.sleep(0.5)  # Rate limiting

    # Resumo
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count

    print(f"\n{'='*70}")
    print("📊 RESUMO DO TESTE DE COMANDOS")
    print(f"{'='*70}")
    print(f"   Total testados: {len(results)}")
    print(f"   ✅ Sucesso: {success_count}")
    print(f"   ❌ Falha: {fail_count}")

    if fail_count > 0:
        print(f"\n   Comandos com falha:")
        for r in results:
            if not r["success"]:
                print(f"   • {r['command']}: {r['description']}")

    # Salva relatório
    report_file = os.path.join(logger.log_dir, f"command_test_{logger.session_id}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_commands": len(commands),
            "tested": len(results),
            "success": success_count,
            "failed": fail_count,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n   📁 Relatório: {report_file}")
    print(f"{'='*70}\n")

    return results


def reliability_report():
    """
    Gera relatório de confiabilidade baseado nos logs históricos.
    Mostra tendências e identifica regressões.
    """
    import glob

    print("\n" + "="*70)
    print("📊 RELATÓRIO DE CONFIABILIDADE")
    print("="*70)

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

    # Lê todos os relatórios de sessão
    session_files = sorted(glob.glob(os.path.join(log_dir, "session_*.json")))
    command_files = sorted(glob.glob(os.path.join(log_dir, "command_test_*.json")))

    if not session_files and not command_files:
        print("   Nenhum log encontrado. Execute demo_session() ou test_all_commands() primeiro.")
        return

    # Analisa sessões LLM
    print("\n📋 SESSÕES LLM (últimas 10):")
    print("-"*50)

    session_stats = []
    for f in session_files[-10:]:
        try:
            with open(f) as file:
                data = json.load(file)
                # Conta status
                success = sum(1 for item in data if item.get('type') == 'task_complete' and item.get('status') == 'success')
                partial = sum(1 for item in data if item.get('type') == 'task_complete' and item.get('status') == 'partial')
                failure = sum(1 for item in data if item.get('type') == 'task_complete' and item.get('status') == 'failure')
                total = success + partial + failure

                if total > 0:
                    rate = (success / total) * 100
                    session_stats.append(rate)
                    status_icon = "✅" if rate >= 80 else "⚠️" if rate >= 60 else "❌"
                    print(f"   {os.path.basename(f)}: {status_icon} {rate:.0f}% ({success}/{total})")
        except:
            pass

    if session_stats:
        avg_rate = sum(session_stats) / len(session_stats)
        trend = "📈" if len(session_stats) > 1 and session_stats[-1] >= session_stats[0] else "📉"
        print(f"\n   Média: {avg_rate:.1f}% {trend}")

    # Analisa testes de comando
    print("\n📋 TESTES DE COMANDOS (últimos 10):")
    print("-"*50)

    cmd_stats = []
    for f in command_files[-10:]:
        try:
            with open(f) as file:
                data = json.load(file)
                success = data.get('success', 0)
                total = data.get('tested', 0)
                if total > 0:
                    rate = (success / total) * 100
                    cmd_stats.append(rate)
                    status_icon = "✅" if rate >= 80 else "⚠️" if rate >= 60 else "❌"
                    print(f"   {os.path.basename(f)}: {status_icon} {rate:.0f}% ({success}/{total})")
        except:
            pass

    if cmd_stats:
        avg_rate = sum(cmd_stats) / len(cmd_stats)
        trend = "📈" if len(cmd_stats) > 1 and cmd_stats[-1] >= cmd_stats[0] else "📉"
        print(f"\n   Média: {avg_rate:.1f}% {trend}")

    # Resumo geral
    print("\n" + "="*70)
    print("📈 RESUMO DE CONFIABILIDADE")
    print("="*70)

    overall_rate = 0
    if session_stats and cmd_stats:
        overall_rate = (sum(session_stats) + sum(cmd_stats)) / (len(session_stats) + len(cmd_stats))
    elif session_stats:
        overall_rate = sum(session_stats) / len(session_stats)
    elif cmd_stats:
        overall_rate = sum(cmd_stats) / len(cmd_stats)

    if overall_rate >= 90:
        status = "🟢 EXCELENTE"
    elif overall_rate >= 75:
        status = "🟡 BOM"
    elif overall_rate >= 50:
        status = "🟠 ATENÇÃO"
    else:
        status = "🔴 CRÍTICO"

    print(f"   Taxa geral: {overall_rate:.1f}% {status}")
    print(f"   Sessões analisadas: {len(session_stats)}")
    print(f"   Testes analisados: {len(cmd_stats)}")
    print("="*70 + "\n")


def test_error_scenarios():
    """
    Testa cenários de erro para validar tratamento correto.
    """
    print("\n" + "="*70)
    print("🔥 TESTE DE CENÁRIOS DE ERRO")
    print("="*70)

    # Login primeiro
    logger.info("Fazendo login...", "🔐")
    login_result = run_cli("auth", "login", "test@test.com", "test123")
    if not login_result.success:
        logger.error(f"Erro no login: {login_result.output}")
        return

    # Cenários de erro para testar
    error_scenarios = [
        {
            "name": "ID de instância inválido",
            "task": "Pausa a instância 999999999999",
            "expected": "failure",
        },
        {
            "name": "Comando ambíguo",
            "task": "Faz alguma coisa com as maquinas",
            "expected": "failure",
        },
        {
            "name": "Filtro impossível",
            "task": "Mostra GPUs RTX 5090 por menos de 1 centavo",
            "expected": "success",  # Deve retornar lista vazia
        },
        {
            "name": "Recurso inexistente",
            "task": "Lista todos os clusters kubernetes",
            "expected": "failure",
        },
    ]

    orchestrator = AgentOrchestrator()
    results = []

    for i, scenario in enumerate(error_scenarios, 1):
        print(f"\n{'─'*60}")
        print(f"[{i}/{len(error_scenarios)}] 🧪 {scenario['name']}")
        print(f"    Tarefa: {scenario['task']}")
        print(f"    Esperado: {scenario['expected']}")

        result = orchestrator.run_task(scenario['task'], i, len(error_scenarios))

        actual = result['final_status']
        passed = (actual == scenario['expected']) or (scenario['expected'] == 'failure' and actual in ['failure', 'partial'])

        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"    Resultado: {actual} {status}")

        results.append({
            "scenario": scenario['name'],
            "task": scenario['task'],
            "expected": scenario['expected'],
            "actual": actual,
            "passed": passed
        })

    # Resumo
    passed_count = sum(1 for r in results if r['passed'])
    print(f"\n{'='*70}")
    print("📊 RESUMO DOS CENÁRIOS DE ERRO")
    print(f"{'='*70}")
    print(f"   Total: {len(results)}")
    print(f"   ✅ Passaram: {passed_count}")
    print(f"   ❌ Falharam: {len(results) - passed_count}")
    print(f"{'='*70}\n")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "test-all":
            # Testa todos os comandos do CLI
            test_all_commands()
        elif cmd == "test-errors":
            # Testa cenários de erro
            test_error_scenarios()
        elif cmd == "report":
            # Gera relatório de confiabilidade
            reliability_report()
        elif cmd == "full":
            # Suite completa
            print("🚀 EXECUTANDO SUITE COMPLETA DE TESTES\n")
            demo_session()
            print("\n" + "─"*70 + "\n")
            test_all_commands()
            print("\n" + "─"*70 + "\n")
            test_error_scenarios()
            print("\n" + "─"*70 + "\n")
            reliability_report()
        else:
            print(f"Comando desconhecido: {cmd}")
            print("\nUso: python llm_agents.py [comando]")
            print("  (sem args)   - Sessão demo com 17 tarefas")
            print("  test-all     - Testa todos os comandos do CLI")
            print("  test-errors  - Testa cenários de erro")
            print("  report       - Relatório de confiabilidade")
            print("  full         - Suite completa de testes")
    else:
        # Sessão demo com agentes LLM
        demo_session()
