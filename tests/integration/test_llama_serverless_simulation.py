"""
Test: LLaMA 3 8B Serverless Simulation

Simulação de um serviço LLaMA 3 8B serverless.
Diferente do Whisper, LLMs têm características específicas:
- Model loading: ~15-30s para carregar 8B params na VRAM (~16GB)
- First token latency (TTFT): tempo para gerar primeiro token
- Token generation: ~30-100 tokens/segundo no RTX 4090
- Context window: afeta latência de processamento

Cenários testados:
1. Cold Start com model loading
2. Warm Start (modelo já carregado)
3. Checkpoint do estado do modelo
4. Diferentes tamanhos de prompt/response
5. Streaming vs non-streaming
"""

import os
import sys
import time
import random
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Generator
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# =============================================================================
# CONFIGURAÇÃO DE LATÊNCIAS LLaMA 3 8B (baseadas em benchmarks reais)
# =============================================================================

class LLaMAConfig:
    """Configurações e latências do LLaMA 3 8B"""

    # Modelo
    MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"
    MODEL_SIZE_GB = 16.0  # ~16GB em FP16
    CONTEXT_WINDOW = 8192  # tokens

    # Cold Start - RTX 4090
    # Boot da máquina + carregar modelo na VRAM
    COLD_START_BOOT_MS = 20000      # 20s boot da VM
    COLD_START_MODEL_LOAD_MS = 25000  # 25s para carregar modelo (SSD → VRAM)
    COLD_START_TOTAL_MIN_MS = 35000   # 35s mínimo total
    COLD_START_TOTAL_MAX_MS = 60000   # 60s máximo (caso ruim)

    # Warm Start (modelo já na VRAM)
    WARM_START_MIN_MS = 10       # 10ms mínimo
    WARM_START_MAX_MS = 50       # 50ms máximo

    # Inference - RTX 4090 com LLaMA 3 8B
    # Time to First Token (TTFT) - depende do tamanho do prompt
    TTFT_BASE_MS = 50            # Base 50ms
    TTFT_PER_1K_TOKENS_MS = 30   # +30ms por 1000 tokens de prompt

    # Token Generation
    TOKENS_PER_SECOND = 80       # ~80 tok/s no RTX 4090
    TOKENS_PER_SECOND_VARIANCE = 0.15  # ±15% variação

    # Checkpoint
    CHECKPOINT_CREATE_MS = 5000   # 5s para checkpoint (estado + KV cache)
    CHECKPOINT_RESTORE_MS = 3000  # 3s para restore

    # Scale down
    SCALE_DOWN_TIME_MS = 5000

    @classmethod
    def estimate_cold_start(cls) -> float:
        """Estima cold start em segundos"""
        base = cls.COLD_START_TOTAL_MIN_MS
        variance = random.gauss(0, 0.2)
        result_ms = base * (1 + abs(variance))
        return min(cls.COLD_START_TOTAL_MAX_MS, result_ms) / 1000

    @classmethod
    def estimate_warm_start(cls) -> float:
        """Estima warm start em segundos"""
        return random.uniform(cls.WARM_START_MIN_MS, cls.WARM_START_MAX_MS) / 1000

    @classmethod
    def estimate_ttft(cls, prompt_tokens: int) -> float:
        """Estima Time to First Token em segundos"""
        base_ms = cls.TTFT_BASE_MS
        prompt_overhead_ms = (prompt_tokens / 1000) * cls.TTFT_PER_1K_TOKENS_MS
        total_ms = base_ms + prompt_overhead_ms
        # Adicionar variância
        variance = random.uniform(0.8, 1.2)
        return (total_ms * variance) / 1000

    @classmethod
    def estimate_generation_time(cls, output_tokens: int) -> float:
        """Estima tempo de geração em segundos"""
        variance = 1 + random.uniform(-cls.TOKENS_PER_SECOND_VARIANCE,
                                       cls.TOKENS_PER_SECOND_VARIANCE)
        effective_tps = cls.TOKENS_PER_SECOND * variance
        return output_tokens / effective_tps


# =============================================================================
# SIMULADOR DE REQUISIÇÕES LLM
# =============================================================================

@dataclass
class LLMRequest:
    """Representa uma requisição de chat/completion"""
    prompt: str
    prompt_tokens: int
    max_tokens: int = 512
    temperature: float = 0.7
    stream: bool = False


@dataclass
class LLMResponse:
    """Resposta do modelo"""
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    ttft_ms: float  # Time to First Token
    generation_time_ms: float
    total_latency_ms: float


@dataclass
class RequestMetrics:
    """Métricas de uma requisição"""
    request_id: int
    timestamp: datetime
    start_type: str  # "cold", "warm", "checkpoint"
    start_latency_ms: float
    ttft_ms: float
    generation_time_ms: float
    total_latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    tokens_per_second: float
    streaming: bool


@dataclass
class SessionMetrics:
    """Métricas da sessão"""
    requests: List[RequestMetrics] = field(default_factory=list)
    scale_ups: int = 0
    scale_downs: int = 0
    checkpoints_created: int = 0
    checkpoints_restored: int = 0
    total_tokens_processed: int = 0
    total_cost: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_request(self, metrics: RequestMetrics):
        self.requests.append(metrics)
        self.total_tokens_processed += metrics.prompt_tokens + metrics.completion_tokens

    @property
    def cold_starts(self) -> List[RequestMetrics]:
        return [r for r in self.requests if r.start_type == "cold"]

    @property
    def warm_starts(self) -> List[RequestMetrics]:
        return [r for r in self.requests if r.start_type == "warm"]

    @property
    def checkpoint_starts(self) -> List[RequestMetrics]:
        return [r for r in self.requests if r.start_type == "checkpoint"]

    @property
    def avg_cold_start_ms(self) -> float:
        cold = self.cold_starts
        return sum(r.start_latency_ms for r in cold) / len(cold) if cold else 0

    @property
    def avg_warm_start_ms(self) -> float:
        warm = self.warm_starts
        return sum(r.start_latency_ms for r in warm) / len(warm) if warm else 0

    @property
    def avg_ttft_ms(self) -> float:
        return sum(r.ttft_ms for r in self.requests) / len(self.requests) if self.requests else 0

    @property
    def avg_tokens_per_second(self) -> float:
        warm = [r for r in self.requests if r.start_type != "cold"]
        return sum(r.tokens_per_second for r in warm) / len(warm) if warm else 0

    def print_report(self):
        """Imprime relatório detalhado"""
        print("\n" + "=" * 70)
        print("RELATÓRIO DE MÉTRICAS - LLaMA 3 8B")
        print("=" * 70)

        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            print(f"\nDuração total: {duration:.1f}s")

        print(f"\nRequisições:")
        print(f"  Total: {len(self.requests)}")
        print(f"  - Cold Starts: {len(self.cold_starts)}")
        print(f"  - Warm Starts: {len(self.warm_starts)}")
        print(f"  - Checkpoint Starts: {len(self.checkpoint_starts)}")

        print(f"\nTokens:")
        print(f"  Total processados: {self.total_tokens_processed:,}")
        print(f"  Média por requisição: {self.total_tokens_processed // len(self.requests) if self.requests else 0}")

        print(f"\nScale Up/Down:")
        print(f"  Scale Ups: {self.scale_ups}")
        print(f"  Scale Downs: {self.scale_downs}")

        print(f"\nCheckpoints:")
        print(f"  Criados: {self.checkpoints_created}")
        print(f"  Restaurados: {self.checkpoints_restored}")

        if self.cold_starts:
            print(f"\nLatências Cold Start:")
            print(f"  Média: {self.avg_cold_start_ms:.0f}ms ({self.avg_cold_start_ms/1000:.1f}s)")
            print(f"  Min: {min(r.start_latency_ms for r in self.cold_starts):.0f}ms")
            print(f"  Max: {max(r.start_latency_ms for r in self.cold_starts):.0f}ms")

        if self.warm_starts:
            print(f"\nLatências Warm Start:")
            print(f"  Média: {self.avg_warm_start_ms:.1f}ms")

        print(f"\nPerformance de Inference:")
        print(f"  TTFT médio: {self.avg_ttft_ms:.1f}ms")
        print(f"  Tokens/segundo médio: {self.avg_tokens_per_second:.1f}")

        print(f"\nCusto estimado: ${self.total_cost:.4f}")


@dataclass
class GPUInstance:
    """Instância GPU para LLaMA"""
    id: str
    status: str = "stopped"
    model_loaded: bool = False
    gpu_model: str = "RTX 4090"
    vram_gb: int = 24
    hourly_cost: float = 0.35
    last_activity: Optional[float] = None
    start_count: int = 0
    stop_count: int = 0
    total_runtime_seconds: float = 0
    last_start_time: Optional[float] = None
    has_checkpoint: bool = False


class LLaMAServerlessSimulator:
    """Simulador do serviço LLaMA serverless"""

    def __init__(
        self,
        idle_timeout_seconds: float = 60.0,
        use_checkpoint: bool = True,
        accelerated: bool = True,
    ):
        self.idle_timeout = idle_timeout_seconds
        self.use_checkpoint = use_checkpoint
        self.accelerated = accelerated
        self.accel_factor = 0.01 if accelerated else 1.0

        self.instance = GPUInstance(id="llama-gpu-1")
        self.metrics = SessionMetrics()
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._request_counter = 0

    def _accelerate(self, seconds: float) -> float:
        return seconds * self.accel_factor

    def start(self):
        """Inicia o simulador"""
        self.metrics.start_time = datetime.now()
        self._running = True
        self._monitor_thread = threading.Thread(target=self._idle_monitor, daemon=True)
        self._monitor_thread.start()
        print(f"[LLaMA] Simulador iniciado")
        print(f"[LLaMA] Modelo: {LLaMAConfig.MODEL_NAME}")
        print(f"[LLaMA] Idle timeout: {self.idle_timeout}s")
        print(f"[LLaMA] Checkpoint: {'enabled' if self.use_checkpoint else 'disabled'}")

    def stop(self):
        """Para o simulador"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        self.metrics.end_time = datetime.now()

        if self.instance.total_runtime_seconds > 0:
            hours = self.instance.total_runtime_seconds / 3600
            self.metrics.total_cost = hours * self.instance.hourly_cost

    def chat(
        self,
        prompt: str,
        max_tokens: int = 256,
        stream: bool = False,
    ) -> RequestMetrics:
        """
        Processa uma requisição de chat.

        Args:
            prompt: Texto do prompt
            max_tokens: Máximo de tokens a gerar
            stream: Se deve fazer streaming

        Returns:
            RequestMetrics com métricas detalhadas
        """
        with self._lock:
            self._request_counter += 1
            request_id = self._request_counter

        # Estimar tokens do prompt (~4 chars por token)
        prompt_tokens = len(prompt) // 4

        start_time = time.time()
        start_type = "warm"
        start_latency = 0

        # 1. Scale up se necessário
        if self.instance.status != "running" or not self.instance.model_loaded:
            with self._lock:
                if self.instance.status != "running":
                    start_type = self._scale_up()
                    start_latency = (time.time() - start_time) * 1000

        # 2. Time to First Token
        ttft = LLaMAConfig.estimate_ttft(prompt_tokens)
        time.sleep(self._accelerate(ttft))
        ttft_ms = ttft * 1000

        # 3. Gerar tokens
        # Simular quantidade de tokens gerados (entre 50% e 100% do max)
        completion_tokens = random.randint(max_tokens // 2, max_tokens)
        generation_time = LLaMAConfig.estimate_generation_time(completion_tokens)
        time.sleep(self._accelerate(generation_time))
        generation_time_ms = generation_time * 1000

        # 4. Atualizar atividade
        with self._lock:
            self.instance.last_activity = time.time()

        # Calcular métricas
        total_latency = (time.time() - start_time) * 1000
        tokens_per_second = completion_tokens / (generation_time if generation_time > 0 else 0.001)

        if start_type == "warm":
            start_latency = LLaMAConfig.estimate_warm_start() * 1000 * self.accel_factor

        metrics = RequestMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            start_type=start_type,
            start_latency_ms=start_latency,
            ttft_ms=ttft_ms * self.accel_factor,
            generation_time_ms=generation_time_ms * self.accel_factor,
            total_latency_ms=total_latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tokens_per_second=tokens_per_second,
            streaming=stream,
        )

        self.metrics.add_request(metrics)
        return metrics

    def _scale_up(self) -> str:
        """Faz scale up e carrega modelo"""
        self.instance.status = "starting"
        self.metrics.scale_ups += 1

        if self.use_checkpoint and self.instance.has_checkpoint:
            # Restore de checkpoint (mais rápido)
            restore_time = LLaMAConfig.CHECKPOINT_RESTORE_MS / 1000
            time.sleep(self._accelerate(restore_time))
            self.metrics.checkpoints_restored += 1
            start_type = "checkpoint"
        else:
            # Cold start: boot + load model
            cold_start_time = LLaMAConfig.estimate_cold_start()
            time.sleep(self._accelerate(cold_start_time))
            start_type = "cold"

        self.instance.status = "running"
        self.instance.model_loaded = True
        self.instance.start_count += 1
        self.instance.last_start_time = time.time()
        self.instance.last_activity = time.time()

        return start_type

    def _scale_down(self):
        """Faz scale down"""
        with self._lock:
            if self.instance.status != "running":
                return

            self.instance.status = "stopping"

            if self.use_checkpoint:
                checkpoint_time = LLaMAConfig.CHECKPOINT_CREATE_MS / 1000
                time.sleep(self._accelerate(checkpoint_time))
                self.instance.has_checkpoint = True
                self.metrics.checkpoints_created += 1

            if self.instance.last_start_time:
                runtime = time.time() - self.instance.last_start_time
                self.instance.total_runtime_seconds += runtime

            stop_time = LLaMAConfig.SCALE_DOWN_TIME_MS / 1000
            time.sleep(self._accelerate(stop_time))

            self.instance.status = "stopped"
            self.instance.model_loaded = False
            self.instance.stop_count += 1
            self.metrics.scale_downs += 1

    def _idle_monitor(self):
        """Monitor de idle"""
        check_interval = self._accelerate(0.5)

        while self._running:
            time.sleep(check_interval)

            with self._lock:
                if self.instance.status != "running":
                    continue
                if not self.instance.last_activity:
                    continue

                idle_time = time.time() - self.instance.last_activity
                scaled_timeout = self._accelerate(self.idle_timeout)

            if idle_time >= scaled_timeout:
                self._scale_down()


# =============================================================================
# PROMPTS DE TESTE
# =============================================================================

SAMPLE_PROMPTS = [
    # Curtos (~50 tokens)
    "Explique o que é machine learning em uma frase.",
    "Qual a capital do Brasil?",
    "O que é Python?",

    # Médios (~200 tokens)
    """Você é um assistente de programação. Explique o conceito de
    recursão em Python com um exemplo simples de código.""",

    """Como funciona o sistema de serverless computing? Quais são
    as principais vantagens e desvantagens comparado a servidores tradicionais?""",

    # Longos (~500+ tokens)
    """Você é um especialista em arquitetura de software. Preciso implementar
    um sistema de processamento de pagamentos que seja escalável, seguro e
    resiliente. O sistema deve suportar múltiplos métodos de pagamento
    (cartão de crédito, PIX, boleto), integrar com gateways de pagamento
    externos, manter um log de auditoria completo, e ser capaz de processar
    milhares de transações por segundo. Por favor, descreva a arquitetura
    recomendada, incluindo os principais componentes, padrões de design
    a serem utilizados, e considerações de segurança.""",
]


# =============================================================================
# TESTES
# =============================================================================

def test_basic_chat_flow():
    """Teste básico: cold start, chat, idle, cold"""
    print("\n" + "=" * 70)
    print("TESTE: Fluxo Básico de Chat")
    print("=" * 70)

    sim = LLaMAServerlessSimulator(
        idle_timeout_seconds=2.0,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        # 1. Primeira requisição (cold)
        print("\n[1] Primeira requisição (Cold Start + Model Load)...")
        r1 = sim.chat("Olá, como você está?", max_tokens=100)
        print(f"    {r1.start_type.upper()}: {r1.total_latency_ms:.0f}ms")
        print(f"    TTFT: {r1.ttft_ms:.1f}ms, Tokens: {r1.completion_tokens}")
        assert r1.start_type == "cold"

        # 2. Segunda requisição (warm)
        print("\n[2] Segunda requisição (Warm - modelo na VRAM)...")
        r2 = sim.chat("Explique o que é serverless.", max_tokens=200)
        print(f"    {r2.start_type.upper()}: {r2.total_latency_ms:.0f}ms")
        print(f"    TTFT: {r2.ttft_ms:.1f}ms, Tokens: {r2.completion_tokens}")
        print(f"    Tokens/s: {r2.tokens_per_second:.0f}")
        assert r2.start_type == "warm"

        # 3. Terceira requisição (warm)
        print("\n[3] Terceira requisição (Warm)...")
        r3 = sim.chat("Quais as vantagens do Python?", max_tokens=150)
        print(f"    {r3.start_type.upper()}: {r3.total_latency_ms:.0f}ms")
        assert r3.start_type == "warm"

        # 4. Aguardar idle
        print("\n[4] Aguardando idle timeout...")
        max_wait = 50
        for i in range(max_wait):
            time.sleep(sim._accelerate(0.5))
            if sim.instance.status == "stopped":
                break
        assert sim.instance.status == "stopped"
        print("    Scale down OK (modelo descarregado)")

        # 5. Nova requisição (com checkpoint)
        print("\n[5] Nova requisição (Checkpoint restore)...")
        r4 = sim.chat("O que é CUDA?", max_tokens=100)
        print(f"    {r4.start_type.upper()}: {r4.total_latency_ms:.0f}ms")
        assert r4.start_type == "checkpoint"

        sim.stop()
        sim.metrics.print_report()

        # Validações
        assert sim.metrics.scale_ups == 2
        assert sim.metrics.scale_downs == 1
        assert sim.metrics.checkpoints_created == 1
        assert sim.metrics.checkpoints_restored == 1
        assert len(sim.metrics.warm_starts) == 2

        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_conversation_session():
    """Teste de sessão de conversa contínua"""
    print("\n" + "=" * 70)
    print("TESTE: Sessão de Conversa")
    print("=" * 70)

    sim = LLaMAServerlessSimulator(
        idle_timeout_seconds=10.0,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        conversation = [
            ("Olá! Vamos conversar sobre Python.", 50),
            ("O que são decorators?", 200),
            ("Pode dar um exemplo prático?", 300),
            ("E o que são generators?", 200),
            ("Qual a diferença entre list e generator?", 250),
        ]

        print("\n[CONVERSA] Iniciando sessão de chat...")

        for i, (prompt, max_tokens) in enumerate(conversation, 1):
            result = sim.chat(prompt, max_tokens=max_tokens)
            start_type = result.start_type[0].upper()
            print(f"  [{i}] {start_type} - {result.total_latency_ms:.0f}ms "
                  f"(TTFT: {result.ttft_ms:.1f}ms, {result.completion_tokens} tokens)")
            time.sleep(sim._accelerate(0.5))  # Pausa entre mensagens

        sim.stop()

        # Validações
        assert len(sim.metrics.cold_starts) == 1  # Apenas primeira é cold
        assert len(sim.metrics.warm_starts) == 4   # Resto é warm
        assert sim.metrics.total_tokens_processed > 0

        print(f"\n    Total de tokens: {sim.metrics.total_tokens_processed}")
        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_varying_prompt_sizes():
    """Teste com diferentes tamanhos de prompt"""
    print("\n" + "=" * 70)
    print("TESTE: Diferentes Tamanhos de Prompt")
    print("=" * 70)

    sim = LLaMAServerlessSimulator(
        idle_timeout_seconds=30.0,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        print("\n[PROMPTS] Testando diferentes tamanhos...")

        for i, prompt in enumerate(SAMPLE_PROMPTS, 1):
            prompt_tokens = len(prompt) // 4
            result = sim.chat(prompt, max_tokens=256)
            start_type = result.start_type[0].upper()
            print(f"  [{i}] {start_type} - Prompt: ~{prompt_tokens} tokens, "
                  f"TTFT: {result.ttft_ms:.1f}ms, Output: {result.completion_tokens} tokens")

        sim.stop()
        sim.metrics.print_report()

        print("\n✅ TESTE PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_intermittent_usage():
    """Teste de uso intermitente com múltiplos cold starts"""
    print("\n" + "=" * 70)
    print("TESTE: Uso Intermitente (múltiplos ciclos)")
    print("=" * 70)

    sim = LLaMAServerlessSimulator(
        idle_timeout_seconds=1.5,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        for cycle in range(3):
            print(f"\n--- Sessão {cycle + 1} ---")

            # Algumas requisições
            for i in range(3):
                prompt = random.choice(SAMPLE_PROMPTS[:3])
                result = sim.chat(prompt, max_tokens=150)
                start_type = result.start_type[0].upper()
                print(f"    [{i+1}] {start_type} - {result.total_latency_ms:.0f}ms")

            # Idle entre sessões
            if cycle < 2:
                print("    [IDLE] Usuário pausou...")
                max_wait = 50
                for _ in range(max_wait):
                    time.sleep(sim._accelerate(0.5))
                    if sim.instance.status == "stopped":
                        break

        sim.stop()
        sim.metrics.print_report()

        # Validações
        assert sim.metrics.scale_downs >= 2
        assert len(sim.metrics.requests) == 9

        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_high_throughput():
    """Teste de alto throughput"""
    print("\n" + "=" * 70)
    print("TESTE: Alto Throughput (20 requisições)")
    print("=" * 70)

    sim = LLaMAServerlessSimulator(
        idle_timeout_seconds=60.0,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        print("\n[THROUGHPUT] Processando 20 requisições...")

        total_tokens = 0
        start = time.time()

        for i in range(20):
            prompt = random.choice(SAMPLE_PROMPTS)
            max_tokens = random.randint(100, 400)
            result = sim.chat(prompt, max_tokens=max_tokens)
            total_tokens += result.completion_tokens

            if i % 5 == 4:
                print(f"    Processadas: {i+1}/20")

        duration = time.time() - start

        sim.stop()

        # Métricas de throughput
        tokens_per_minute = (total_tokens / duration) * 60
        print(f"\n    Duração: {duration:.2f}s")
        print(f"    Tokens gerados: {total_tokens}")
        print(f"    Throughput: {tokens_per_minute:.0f} tokens/min")

        sim.metrics.print_report()

        print("\n✅ TESTE PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_cold_vs_warm_comparison():
    """Compara métricas de cold start vs warm start"""
    print("\n" + "=" * 70)
    print("TESTE: Comparação Cold Start vs Warm Start")
    print("=" * 70)

    sim = LLaMAServerlessSimulator(
        idle_timeout_seconds=1.0,
        use_checkpoint=False,  # Sem checkpoint para forçar cold starts
        accelerated=True,
    )

    try:
        sim.start()

        results = []

        # Fase 1: Cold start
        print("\n[FASE 1] Cold Start...")
        r1 = sim.chat("Teste de cold start", max_tokens=100)
        results.append(("Cold", r1))
        print(f"    Latência total: {r1.total_latency_ms:.0f}ms")

        # Fase 2: Warm starts
        print("\n[FASE 2] Warm Starts (3x)...")
        for i in range(3):
            r = sim.chat(f"Teste warm start {i}", max_tokens=100)
            results.append(("Warm", r))
            print(f"    [{i+1}] Latência: {r.total_latency_ms:.0f}ms")

        # Fase 3: Forçar idle e outro cold start
        print("\n[FASE 3] Forçando idle + novo Cold Start...")
        max_wait = 50
        for _ in range(max_wait):
            time.sleep(sim._accelerate(0.5))
            if sim.instance.status == "stopped":
                break

        r5 = sim.chat("Segundo cold start", max_tokens=100)
        results.append(("Cold", r5))
        print(f"    Latência total: {r5.total_latency_ms:.0f}ms")

        sim.stop()

        # Análise
        cold_latencies = [r.total_latency_ms for t, r in results if t == "Cold"]
        warm_latencies = [r.total_latency_ms for t, r in results if t == "Warm"]

        print("\n" + "-" * 50)
        print("ANÁLISE COMPARATIVA")
        print("-" * 50)
        print(f"\nCold Start ({len(cold_latencies)} amostras):")
        print(f"  Média: {sum(cold_latencies)/len(cold_latencies):.0f}ms")
        print(f"  Min: {min(cold_latencies):.0f}ms")
        print(f"  Max: {max(cold_latencies):.0f}ms")

        print(f"\nWarm Start ({len(warm_latencies)} amostras):")
        print(f"  Média: {sum(warm_latencies)/len(warm_latencies):.0f}ms")
        print(f"  Min: {min(warm_latencies):.0f}ms")
        print(f"  Max: {max(warm_latencies):.0f}ms")

        ratio = (sum(cold_latencies)/len(cold_latencies)) / (sum(warm_latencies)/len(warm_latencies))
        print(f"\nCold/Warm ratio: {ratio:.1f}x mais lento")

        # Validação
        assert sum(cold_latencies)/len(cold_latencies) > sum(warm_latencies)/len(warm_latencies)

        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def run_all_tests():
    """Executa todos os testes"""
    print("=" * 70)
    print("LLaMA 3 8B SERVERLESS SIMULATION TESTS")
    print("=" * 70)
    print(f"\nModelo: {LLaMAConfig.MODEL_NAME}")
    print(f"VRAM necessária: ~{LLaMAConfig.MODEL_SIZE_GB}GB")
    print(f"Cold Start estimado: {LLaMAConfig.COLD_START_TOTAL_MIN_MS/1000:.0f}-{LLaMAConfig.COLD_START_TOTAL_MAX_MS/1000:.0f}s")
    print(f"Tokens/segundo: ~{LLaMAConfig.TOKENS_PER_SECOND}")

    tests = [
        ("Fluxo Básico de Chat", test_basic_chat_flow),
        ("Sessão de Conversa", test_conversation_session),
        ("Diferentes Tamanhos de Prompt", test_varying_prompt_sizes),
        ("Uso Intermitente", test_intermittent_usage),
        ("Alto Throughput", test_high_throughput),
        ("Cold vs Warm Comparison", test_cold_vs_warm_comparison),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ ERRO em {name}: {e}")
            results.append((name, False))

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)

    passed = sum(1 for _, p in results if p)
    failed = len(results) - passed

    for name, p in results:
        status = "✅" if p else "❌"
        print(f"  {status} {name}")

    print(f"\nTotal: {len(results)} testes")
    print(f"Passou: {passed}")
    print(f"Falhou: {failed}")

    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
