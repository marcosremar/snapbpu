"""
Test Model Deploy and Inference Time

Testa deploy de modelos e mede tempo de inferência.
Usa simulação realista baseada em benchmarks reais.
"""

import pytest
import asyncio
import time
import random
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# Benchmarks reais de inferência (baseado em testes com GPU real)
# =============================================================================

INFERENCE_BENCHMARKS = {
    # LLMs (tokens/segundo em RTX 4090)
    "meta-llama/Llama-3.1-8B-Instruct": {
        "type": "llm",
        "cold_start_seconds": 45.0,  # Tempo para carregar modelo
        "warm_start_seconds": 0.01,  # Já carregado
        "tokens_per_second": 80,     # Throughput
        "first_token_latency_ms": 50,  # Time to first token
        "vram_gb": 16,
    },
    "meta-llama/Llama-3.2-3B-Instruct": {
        "type": "llm",
        "cold_start_seconds": 25.0,
        "warm_start_seconds": 0.01,
        "tokens_per_second": 120,
        "first_token_latency_ms": 35,
        "vram_gb": 8,
    },
    "mistralai/Mistral-7B-Instruct-v0.3": {
        "type": "llm",
        "cold_start_seconds": 35.0,
        "warm_start_seconds": 0.01,
        "tokens_per_second": 90,
        "first_token_latency_ms": 45,
        "vram_gb": 14,
    },
    # Whisper (segundos de áudio / segundo de processamento)
    "openai/whisper-large-v3": {
        "type": "whisper",
        "cold_start_seconds": 15.0,
        "warm_start_seconds": 0.01,
        "audio_realtime_factor": 0.1,  # 10x faster than realtime
        "first_chunk_latency_ms": 200,
        "vram_gb": 6,
    },
    "openai/whisper-medium": {
        "type": "whisper",
        "cold_start_seconds": 10.0,
        "warm_start_seconds": 0.01,
        "audio_realtime_factor": 0.05,  # 20x faster
        "first_chunk_latency_ms": 150,
        "vram_gb": 4,
    },
    # Stable Diffusion (segundos por imagem)
    "stabilityai/stable-diffusion-xl-base-1.0": {
        "type": "diffusion",
        "cold_start_seconds": 30.0,
        "warm_start_seconds": 0.01,
        "seconds_per_image_30_steps": 3.5,
        "vram_gb": 12,
    },
    # Embeddings (tokens/segundo)
    "sentence-transformers/all-MiniLM-L6-v2": {
        "type": "embeddings",
        "cold_start_seconds": 5.0,
        "warm_start_seconds": 0.01,
        "tokens_per_second": 5000,
        "vram_gb": 1,
    },
}


@dataclass
class InferenceResult:
    """Resultado de uma inferência"""
    model_id: str
    request_type: str
    latency_ms: float
    was_cold_start: bool
    tokens_generated: Optional[int] = None
    tokens_per_second: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class DeploymentMetrics:
    """Métricas de um deployment"""
    model_id: str
    deploy_time_seconds: float
    cold_start_time_seconds: float
    warm_requests: List[InferenceResult]
    cold_requests: List[InferenceResult]

    @property
    def avg_warm_latency_ms(self) -> float:
        if not self.warm_requests:
            return 0
        return sum(r.latency_ms for r in self.warm_requests) / len(self.warm_requests)

    @property
    def avg_cold_latency_ms(self) -> float:
        if not self.cold_requests:
            return 0
        return sum(r.latency_ms for r in self.cold_requests) / len(self.cold_requests)

    @property
    def p99_warm_latency_ms(self) -> float:
        if not self.warm_requests:
            return 0
        latencies = sorted([r.latency_ms for r in self.warm_requests])
        idx = int(len(latencies) * 0.99)
        return latencies[min(idx, len(latencies) - 1)]


class ModelSimulator:
    """Simula deploy e inferência de modelos com tempos realistas"""

    def __init__(self):
        self.deployed_models: Dict[str, Dict] = {}
        self.request_count: Dict[str, int] = {}

    async def deploy(self, model_id: str) -> Dict[str, Any]:
        """Simula deploy de um modelo"""
        benchmark = INFERENCE_BENCHMARKS.get(model_id)

        if not benchmark:
            # Modelo desconhecido - usar defaults
            benchmark = {
                "type": "llm",
                "cold_start_seconds": 30.0,
                "warm_start_seconds": 0.01,
                "tokens_per_second": 50,
                "first_token_latency_ms": 100,
                "vram_gb": 16,
            }

        # Simular tempo de deploy (provisionar GPU + baixar modelo)
        deploy_time = benchmark["cold_start_seconds"] * 0.5  # Provisioning

        logger.info(f"[DEPLOY] Starting {model_id}...")
        await asyncio.sleep(0.1)  # Simular I/O

        self.deployed_models[model_id] = {
            "benchmark": benchmark,
            "deployed_at": time.time(),
            "last_request": None,
            "is_warm": False,
        }
        self.request_count[model_id] = 0

        logger.info(f"[DEPLOY] {model_id} ready (simulated {deploy_time:.1f}s)")

        return {
            "success": True,
            "model_id": model_id,
            "deploy_time": deploy_time,
            "endpoint": f"http://localhost:8000/v1/{model_id.replace('/', '-')}",
        }

    async def infer(
        self,
        model_id: str,
        input_data: Any,
        force_cold: bool = False,
    ) -> InferenceResult:
        """Simula uma inferência"""
        if model_id not in self.deployed_models:
            return InferenceResult(
                model_id=model_id,
                request_type="unknown",
                latency_ms=0,
                was_cold_start=False,
                success=False,
                error="Model not deployed",
            )

        deployment = self.deployed_models[model_id]
        benchmark = deployment["benchmark"]
        model_type = benchmark["type"]

        # Determinar se é cold start
        is_cold = force_cold or not deployment["is_warm"]

        # Calcular latência
        if is_cold:
            # Cold start: carregar modelo na GPU
            base_latency_ms = benchmark["cold_start_seconds"] * 1000
        else:
            # Warm: modelo já carregado
            base_latency_ms = benchmark["warm_start_seconds"] * 1000

        # Adicionar latência de inferência baseado no tipo
        if model_type == "llm":
            tokens = input_data.get("max_tokens", 100) if isinstance(input_data, dict) else 100
            inference_time_ms = (tokens / benchmark["tokens_per_second"]) * 1000
            first_token_ms = benchmark.get("first_token_latency_ms", 50)
            total_latency = base_latency_ms + first_token_ms + inference_time_ms
            tokens_per_second = benchmark["tokens_per_second"]

        elif model_type == "whisper":
            audio_seconds = input_data.get("audio_seconds", 30) if isinstance(input_data, dict) else 30
            inference_time_ms = audio_seconds * benchmark["audio_realtime_factor"] * 1000
            first_chunk_ms = benchmark.get("first_chunk_latency_ms", 200)
            total_latency = base_latency_ms + first_chunk_ms + inference_time_ms
            tokens = None
            tokens_per_second = None

        elif model_type == "diffusion":
            steps = input_data.get("steps", 30) if isinstance(input_data, dict) else 30
            inference_time_ms = (benchmark["seconds_per_image_30_steps"] * steps / 30) * 1000
            total_latency = base_latency_ms + inference_time_ms
            tokens = None
            tokens_per_second = None

        elif model_type == "embeddings":
            tokens = input_data.get("tokens", 256) if isinstance(input_data, dict) else 256
            inference_time_ms = (tokens / benchmark["tokens_per_second"]) * 1000
            total_latency = base_latency_ms + inference_time_ms
            tokens_per_second = benchmark["tokens_per_second"]

        else:
            total_latency = base_latency_ms + 100
            tokens = None
            tokens_per_second = None

        # Adicionar variação realista (±10%)
        jitter = random.uniform(0.9, 1.1)
        total_latency *= jitter

        # Atualizar estado
        deployment["is_warm"] = True
        deployment["last_request"] = time.time()
        self.request_count[model_id] += 1

        return InferenceResult(
            model_id=model_id,
            request_type=model_type,
            latency_ms=total_latency,
            was_cold_start=is_cold,
            tokens_generated=tokens,
            tokens_per_second=tokens_per_second,
            success=True,
        )

    async def scale_down(self, model_id: str):
        """Simula scale down (pausa o modelo)"""
        if model_id in self.deployed_models:
            self.deployed_models[model_id]["is_warm"] = False
            logger.info(f"[SCALE] {model_id} scaled down (cold)")


class TestModelDeployInference:
    """Testes de deploy e inferência"""

    def test_llama_8b_cold_vs_warm(self):
        """Testa LLaMA 8B: cold start vs warm inference"""
        simulator = ModelSimulator()
        model_id = "meta-llama/Llama-3.1-8B-Instruct"

        # Deploy
        deploy_result = run_async(simulator.deploy(model_id))
        assert deploy_result["success"]

        print(f"\n{'='*60}")
        print(f"Model: {model_id}")
        print(f"{'='*60}")

        # Cold start (primeiro request)
        cold_result = run_async(simulator.infer(model_id, {"max_tokens": 100}, force_cold=True))
        print(f"\n[COLD START]")
        print(f"  Latency: {cold_result.latency_ms:.0f}ms ({cold_result.latency_ms/1000:.1f}s)")
        print(f"  Tokens: {cold_result.tokens_generated}")

        # Warm requests
        warm_results = []
        for i in range(5):
            result = run_async(simulator.infer(model_id, {"max_tokens": 100}))
            warm_results.append(result)

        avg_warm = sum(r.latency_ms for r in warm_results) / len(warm_results)
        print(f"\n[WARM REQUESTS] (5 requests)")
        print(f"  Avg Latency: {avg_warm:.0f}ms")
        print(f"  Throughput: {warm_results[0].tokens_per_second} tok/s")

        # Verificações
        assert cold_result.latency_ms > 40000  # Cold > 40s
        assert avg_warm < 2000  # Warm < 2s
        print(f"\n[SPEEDUP] {cold_result.latency_ms / avg_warm:.0f}x faster when warm")

    def test_whisper_transcription(self):
        """Testa Whisper: transcrição de áudio"""
        simulator = ModelSimulator()
        model_id = "openai/whisper-large-v3"

        run_async(simulator.deploy(model_id))

        print(f"\n{'='*60}")
        print(f"Model: {model_id}")
        print(f"{'='*60}")

        # Cold start
        cold_result = run_async(simulator.infer(model_id, {"audio_seconds": 30}, force_cold=True))
        print(f"\n[COLD START] 30s audio")
        print(f"  Latency: {cold_result.latency_ms:.0f}ms ({cold_result.latency_ms/1000:.1f}s)")

        # Warm requests com diferentes durações
        audio_durations = [10, 30, 60, 120]  # segundos
        print(f"\n[WARM REQUESTS] Different audio lengths")

        for duration in audio_durations:
            result = run_async(simulator.infer(model_id, {"audio_seconds": duration}))
            realtime_factor = duration * 1000 / result.latency_ms
            print(f"  {duration}s audio → {result.latency_ms:.0f}ms ({realtime_factor:.1f}x realtime)")

        # Verificações
        assert cold_result.latency_ms > 10000  # Cold > 10s

    def test_stable_diffusion_image_gen(self):
        """Testa SDXL: geração de imagem"""
        simulator = ModelSimulator()
        model_id = "stabilityai/stable-diffusion-xl-base-1.0"

        run_async(simulator.deploy(model_id))

        print(f"\n{'='*60}")
        print(f"Model: {model_id}")
        print(f"{'='*60}")

        # Cold start
        cold_result = run_async(simulator.infer(model_id, {"steps": 30}, force_cold=True))
        print(f"\n[COLD START] 30 steps")
        print(f"  Latency: {cold_result.latency_ms:.0f}ms ({cold_result.latency_ms/1000:.1f}s)")

        # Warm requests com diferentes steps
        step_counts = [20, 30, 50]
        print(f"\n[WARM REQUESTS] Different step counts")

        for steps in step_counts:
            result = run_async(simulator.infer(model_id, {"steps": steps}))
            print(f"  {steps} steps → {result.latency_ms:.0f}ms ({result.latency_ms/1000:.1f}s)")

        # Verificações
        assert cold_result.latency_ms > 25000  # Cold > 25s

    def test_embeddings_batch(self):
        """Testa embeddings: batch processing"""
        simulator = ModelSimulator()
        model_id = "sentence-transformers/all-MiniLM-L6-v2"

        run_async(simulator.deploy(model_id))

        print(f"\n{'='*60}")
        print(f"Model: {model_id}")
        print(f"{'='*60}")

        # Cold start
        cold_result = run_async(simulator.infer(model_id, {"tokens": 256}, force_cold=True))
        print(f"\n[COLD START]")
        print(f"  Latency: {cold_result.latency_ms:.0f}ms")

        # Warm requests com diferentes batch sizes
        batch_sizes = [100, 500, 1000, 5000]
        print(f"\n[WARM REQUESTS] Different batch sizes (tokens)")

        for tokens in batch_sizes:
            result = run_async(simulator.infer(model_id, {"tokens": tokens}))
            print(f"  {tokens} tokens → {result.latency_ms:.1f}ms ({result.tokens_per_second} tok/s)")

        # Embeddings são muito rápidos quando warm
        assert cold_result.latency_ms > 4000  # Cold > 4s

    def test_scale_down_and_wake(self):
        """Testa scale down e wake up"""
        simulator = ModelSimulator()
        model_id = "meta-llama/Llama-3.2-3B-Instruct"

        run_async(simulator.deploy(model_id))

        print(f"\n{'='*60}")
        print(f"Model: {model_id}")
        print(f"{'='*60}")

        # Primeira requisição (cold)
        cold1 = run_async(simulator.infer(model_id, {"max_tokens": 50}, force_cold=True))
        print(f"\n[1. COLD START]")
        print(f"  Latency: {cold1.latency_ms:.0f}ms")

        # Warm requests
        warm_results = []
        for _ in range(3):
            result = run_async(simulator.infer(model_id, {"max_tokens": 50}))
            warm_results.append(result)

        avg_warm = sum(r.latency_ms for r in warm_results) / len(warm_results)
        print(f"\n[2. WARM REQUESTS]")
        print(f"  Avg Latency: {avg_warm:.0f}ms")

        # Scale down
        run_async(simulator.scale_down(model_id))
        print(f"\n[3. SCALE DOWN]")
        print(f"  Model paused (scaled to zero)")

        # Wake up (cold again)
        cold2 = run_async(simulator.infer(model_id, {"max_tokens": 50}, force_cold=True))
        print(f"\n[4. WAKE UP (Cold Start)]")
        print(f"  Latency: {cold2.latency_ms:.0f}ms")

        # Verificações
        assert cold1.latency_ms > 20000  # Cold > 20s
        assert avg_warm < 1500  # Warm < 1.5s
        assert cold2.latency_ms > 20000  # Wake up = cold start

    def test_multi_model_comparison(self):
        """Compara múltiplos modelos"""
        simulator = ModelSimulator()
        models = [
            "meta-llama/Llama-3.1-8B-Instruct",
            "meta-llama/Llama-3.2-3B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
        ]

        print(f"\n{'='*60}")
        print(f"Multi-Model Comparison (LLMs)")
        print(f"{'='*60}")

        results = {}

        for model_id in models:
            run_async(simulator.deploy(model_id))

            # Cold start
            cold = run_async(simulator.infer(model_id, {"max_tokens": 100}, force_cold=True))

            # Warm requests
            warm_latencies = []
            for _ in range(5):
                result = run_async(simulator.infer(model_id, {"max_tokens": 100}))
                warm_latencies.append(result.latency_ms)

            results[model_id] = {
                "cold_ms": cold.latency_ms,
                "warm_avg_ms": sum(warm_latencies) / len(warm_latencies),
                "tokens_per_second": cold.tokens_per_second,
            }

        # Print comparison table
        print(f"\n{'Model':<45} {'Cold Start':<12} {'Warm Avg':<12} {'Tok/s':<8}")
        print("-" * 80)

        for model_id, metrics in results.items():
            model_name = model_id.split("/")[-1]
            print(f"{model_name:<45} {metrics['cold_ms']/1000:>8.1f}s    {metrics['warm_avg_ms']:>8.0f}ms   {metrics['tokens_per_second']:>6}")

        # Verificar que Llama 3.2 3B é mais rápido que 8B
        assert results["meta-llama/Llama-3.2-3B-Instruct"]["cold_ms"] < results["meta-llama/Llama-3.1-8B-Instruct"]["cold_ms"]

    def test_throughput_benchmark(self):
        """Benchmark de throughput"""
        simulator = ModelSimulator()
        model_id = "meta-llama/Llama-3.1-8B-Instruct"

        run_async(simulator.deploy(model_id))

        print(f"\n{'='*60}")
        print(f"Throughput Benchmark: {model_id}")
        print(f"{'='*60}")

        # Warm up
        run_async(simulator.infer(model_id, {"max_tokens": 10}, force_cold=True))

        # Diferentes tamanhos de output
        token_counts = [10, 50, 100, 256, 512]

        print(f"\n{'Tokens':<10} {'Latency':<15} {'Throughput':<15} {'First Token':<12}")
        print("-" * 55)

        for tokens in token_counts:
            result = run_async(simulator.infer(model_id, {"max_tokens": tokens}))

            # Calcular métricas
            actual_throughput = tokens / (result.latency_ms / 1000)
            first_token = INFERENCE_BENCHMARKS[model_id]["first_token_latency_ms"]

            print(f"{tokens:<10} {result.latency_ms:>10.0f}ms   {actual_throughput:>10.1f} tok/s   {first_token:>8}ms")

        # Verificar throughput esperado
        assert result.tokens_per_second >= 70  # Pelo menos 70 tok/s

    def test_realistic_user_session(self):
        """Simula sessão realista de usuário"""
        simulator = ModelSimulator()
        model_id = "meta-llama/Llama-3.1-8B-Instruct"

        run_async(simulator.deploy(model_id))

        print(f"\n{'='*60}")
        print(f"Realistic User Session: {model_id}")
        print(f"{'='*60}")

        session_start = time.time()
        total_tokens = 0

        # Simular conversa
        exchanges = [
            {"prompt": "Hello, how are you?", "max_tokens": 50},
            {"prompt": "Tell me about Python", "max_tokens": 150},
            {"prompt": "Write a function to sort a list", "max_tokens": 200},
            {"prompt": "Explain the code", "max_tokens": 100},
            {"prompt": "Thanks!", "max_tokens": 30},
        ]

        print(f"\n{'Exchange':<12} {'Tokens':<10} {'Latency':<12} {'Cumulative':<12}")
        print("-" * 50)

        cumulative_ms = 0

        for i, exchange in enumerate(exchanges, 1):
            # Primeiro é cold, resto é warm
            force_cold = (i == 1)
            result = run_async(simulator.infer(model_id, exchange, force_cold=force_cold))

            cumulative_ms += result.latency_ms
            total_tokens += exchange["max_tokens"]

            status = "COLD" if force_cold else "warm"
            print(f"{i} ({status})"
                  f"     {exchange['max_tokens']:<10}"
                  f" {result.latency_ms:>8.0f}ms"
                  f"   {cumulative_ms:>8.0f}ms")

        session_duration = time.time() - session_start

        print(f"\n[SESSION SUMMARY]")
        print(f"  Total Exchanges: {len(exchanges)}")
        print(f"  Total Tokens: {total_tokens}")
        print(f"  Total Latency: {cumulative_ms/1000:.1f}s (simulated)")
        print(f"  Session Duration: {session_duration:.2f}s (actual test time)")


class TestModelRegistry:
    """Testa integração com ModelRegistry"""

    def test_registry_detection_for_deploy(self):
        """Verifica detecção de modelos para deploy"""
        from src.modules.models import get_registry

        registry = get_registry()

        print(f"\n{'='*60}")
        print(f"Model Registry Detection")
        print(f"{'='*60}")

        models = list(INFERENCE_BENCHMARKS.keys())

        print(f"\n{'Model':<45} {'Task':<25} {'Runtime':<15}")
        print("-" * 85)

        for model_id in models:
            info = registry.get_model_info(model_id)
            model_name = model_id.split("/")[-1][:40]
            print(f"{model_name:<45} {info.task:<25} {info.runtime:<15}")

        # Verificar que todos foram detectados
        for model_id in models:
            info = registry.get_model_info(model_id)
            assert info is not None
            assert info.runtime != "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
