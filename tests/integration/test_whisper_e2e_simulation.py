"""
Test: Whisper E2E Simulation

Simulação end-to-end de um serviço Whisper serverless.
Mede latências realistas e valida comportamento do sistema.

Cenários testados:
1. Cold Start inicial
2. Requisições em burst (warm)
3. Idle timeout e scale down
4. Cold start após idle
5. Stress test com padrões aleatórios
"""

import os
import sys
import time
import random
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# =============================================================================
# CONFIGURAÇÃO DE LATÊNCIAS SIMULADAS (baseadas em medições reais)
# =============================================================================

class LatencyConfig:
    """Latências simuladas baseadas em medições reais"""

    # TensorDock RTX 4090 - tempos observados
    COLD_START_MIN_MS = 15000   # 15s mínimo
    COLD_START_MAX_MS = 45000   # 45s máximo (caso ruim)
    COLD_START_P50_MS = 20000   # 20s típico

    # Warm start (máquina já running)
    WARM_START_MIN_MS = 50      # 50ms mínimo
    WARM_START_MAX_MS = 500     # 500ms máximo
    WARM_START_P50_MS = 100     # 100ms típico

    # Whisper processing (por segundo de áudio)
    WHISPER_PROCESSING_RATIO = 0.05  # 5% do tempo real de áudio

    # Scale down
    SCALE_DOWN_TIME_MS = 5000   # 5s para parar

    # SSH connection
    SSH_CONNECT_TIME_MS = 200   # 200ms para conectar

    # Com cuda-checkpoint
    CHECKPOINT_CREATE_MS = 3000  # 3s para criar checkpoint
    CHECKPOINT_RESTORE_MS = 2000 # 2s para restaurar

    @classmethod
    def simulate_cold_start(cls) -> float:
        """Retorna latência simulada de cold start em segundos"""
        # Distribuição log-normal para simular realidade
        import random
        base = cls.COLD_START_P50_MS
        variance = random.gauss(0, 0.3)
        result_ms = base * (1 + variance)
        return max(cls.COLD_START_MIN_MS, min(cls.COLD_START_MAX_MS, result_ms)) / 1000

    @classmethod
    def simulate_warm_start(cls) -> float:
        """Retorna latência simulada de warm start em segundos"""
        result_ms = random.uniform(cls.WARM_START_MIN_MS, cls.WARM_START_MAX_MS)
        return result_ms / 1000

    @classmethod
    def simulate_whisper_processing(cls, audio_duration_seconds: float) -> float:
        """Retorna tempo de processamento Whisper em segundos"""
        base_time = audio_duration_seconds * cls.WHISPER_PROCESSING_RATIO
        variance = random.uniform(0.8, 1.2)
        return base_time * variance


# =============================================================================
# SISTEMA SERVERLESS SIMULADO
# =============================================================================

@dataclass
class GPUInstance:
    """Representa uma instância GPU"""
    id: str
    status: str = "stopped"  # stopped, starting, running, stopping
    gpu_model: str = "RTX 4090"
    hourly_cost: float = 0.35
    last_activity: Optional[float] = None
    start_count: int = 0
    stop_count: int = 0
    total_runtime_seconds: float = 0
    last_start_time: Optional[float] = None
    has_checkpoint: bool = False
    checkpoint_id: Optional[str] = None


@dataclass
class RequestResult:
    """Resultado de uma requisição"""
    request_id: int
    audio_duration: float
    total_latency_ms: float
    start_type: str  # "cold", "warm", "checkpoint"
    start_latency_ms: float
    processing_latency_ms: float
    timestamp: datetime
    success: bool = True
    error: Optional[str] = None


@dataclass
class SessionMetrics:
    """Métricas da sessão de testes"""
    requests: List[RequestResult] = field(default_factory=list)
    scale_ups: int = 0
    scale_downs: int = 0
    checkpoints_created: int = 0
    checkpoints_restored: int = 0
    total_cost: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_request(self, result: RequestResult):
        self.requests.append(result)

    @property
    def cold_starts(self) -> List[RequestResult]:
        return [r for r in self.requests if r.start_type == "cold"]

    @property
    def warm_starts(self) -> List[RequestResult]:
        return [r for r in self.requests if r.start_type == "warm"]

    @property
    def checkpoint_starts(self) -> List[RequestResult]:
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
    def p95_cold_start_ms(self) -> float:
        cold = sorted(r.start_latency_ms for r in self.cold_starts)
        if not cold:
            return 0
        idx = int(len(cold) * 0.95)
        return cold[min(idx, len(cold) - 1)]

    def print_report(self):
        """Imprime relatório completo"""
        print("\n" + "=" * 70)
        print("RELATÓRIO DE MÉTRICAS")
        print("=" * 70)

        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            print(f"\nDuração total: {duration:.1f}s")

        print(f"\nTotal de requisições: {len(self.requests)}")
        print(f"  - Cold Starts: {len(self.cold_starts)}")
        print(f"  - Warm Starts: {len(self.warm_starts)}")
        print(f"  - Checkpoint Starts: {len(self.checkpoint_starts)}")

        print(f"\nScale Up/Down:")
        print(f"  - Scale Ups: {self.scale_ups}")
        print(f"  - Scale Downs: {self.scale_downs}")

        print(f"\nCheckpoints:")
        print(f"  - Criados: {self.checkpoints_created}")
        print(f"  - Restaurados: {self.checkpoints_restored}")

        if self.cold_starts:
            print(f"\nLatências Cold Start:")
            print(f"  - Média: {self.avg_cold_start_ms:.0f}ms ({self.avg_cold_start_ms/1000:.2f}s)")
            print(f"  - P95: {self.p95_cold_start_ms:.0f}ms")
            print(f"  - Min: {min(r.start_latency_ms for r in self.cold_starts):.0f}ms")
            print(f"  - Max: {max(r.start_latency_ms for r in self.cold_starts):.0f}ms")

        if self.warm_starts:
            print(f"\nLatências Warm Start:")
            print(f"  - Média: {self.avg_warm_start_ms:.0f}ms")
            print(f"  - Min: {min(r.start_latency_ms for r in self.warm_starts):.0f}ms")
            print(f"  - Max: {max(r.start_latency_ms for r in self.warm_starts):.0f}ms")

        print(f"\nCusto estimado: ${self.total_cost:.4f}")


class ServerlessWhisperSimulator:
    """Simulador do serviço Whisper serverless"""

    def __init__(
        self,
        idle_timeout_seconds: float = 30.0,
        use_checkpoint: bool = True,
        accelerated: bool = True,  # Acelera tempos para teste
    ):
        self.idle_timeout = idle_timeout_seconds
        self.use_checkpoint = use_checkpoint
        self.accelerated = accelerated

        # Fator de aceleração (para testes rápidos)
        self.accel_factor = 0.01 if accelerated else 1.0

        self.instance = GPUInstance(id="whisper-gpu-1")
        self.metrics = SessionMetrics()
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._request_counter = 0

    def _accelerate(self, seconds: float) -> float:
        """Aplica fator de aceleração"""
        return seconds * self.accel_factor

    def start(self):
        """Inicia o simulador"""
        self.metrics.start_time = datetime.now()
        self._running = True
        self._monitor_thread = threading.Thread(target=self._idle_monitor, daemon=True)
        self._monitor_thread.start()
        print(f"[SIM] Simulador iniciado (acelerado: {self.accelerated})")
        print(f"[SIM] Idle timeout: {self.idle_timeout}s")
        print(f"[SIM] Checkpoint: {'enabled' if self.use_checkpoint else 'disabled'}")

    def stop(self):
        """Para o simulador"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        self.metrics.end_time = datetime.now()

        # Calcular custo
        if self.instance.total_runtime_seconds > 0:
            hours = self.instance.total_runtime_seconds / 3600
            self.metrics.total_cost = hours * self.instance.hourly_cost

    def process_audio(self, audio_duration_seconds: float) -> RequestResult:
        """
        Processa uma requisição de transcrição.

        Returns:
            RequestResult com métricas da requisição
        """
        with self._lock:
            self._request_counter += 1
            request_id = self._request_counter

        start_time = time.time()
        start_type = "warm"
        start_latency = 0

        # 1. Scale up se necessário
        if self.instance.status != "running":
            with self._lock:
                if self.instance.status != "running":
                    start_type = self._scale_up()
                    start_latency = (time.time() - start_time) * 1000

        # 2. Processar áudio
        processing_start = time.time()
        processing_time = LatencyConfig.simulate_whisper_processing(audio_duration_seconds)
        time.sleep(self._accelerate(processing_time))
        processing_latency = (time.time() - processing_start) * 1000

        # 3. Atualizar atividade
        with self._lock:
            self.instance.last_activity = time.time()

        # 4. Calcular latência total
        total_latency = (time.time() - start_time) * 1000

        if start_type == "warm":
            start_latency = LatencyConfig.simulate_warm_start() * 1000 * self.accel_factor

        result = RequestResult(
            request_id=request_id,
            audio_duration=audio_duration_seconds,
            total_latency_ms=total_latency,
            start_type=start_type,
            start_latency_ms=start_latency,
            processing_latency_ms=processing_latency,
            timestamp=datetime.now(),
        )

        self.metrics.add_request(result)
        return result

    def _scale_up(self) -> str:
        """Faz scale up da instância. Retorna tipo de start."""
        self.instance.status = "starting"
        self.metrics.scale_ups += 1

        if self.use_checkpoint and self.instance.has_checkpoint:
            # Restore de checkpoint (mais rápido)
            restore_time = LatencyConfig.CHECKPOINT_RESTORE_MS / 1000
            time.sleep(self._accelerate(restore_time))
            self.metrics.checkpoints_restored += 1
            start_type = "checkpoint"
        else:
            # Cold start normal
            cold_start_time = LatencyConfig.simulate_cold_start()
            time.sleep(self._accelerate(cold_start_time))
            start_type = "cold"

        self.instance.status = "running"
        self.instance.start_count += 1
        self.instance.last_start_time = time.time()
        self.instance.last_activity = time.time()

        return start_type

    def _scale_down(self):
        """Faz scale down da instância"""
        with self._lock:
            if self.instance.status != "running":
                return

            self.instance.status = "stopping"

            # Criar checkpoint se habilitado
            if self.use_checkpoint:
                checkpoint_time = LatencyConfig.CHECKPOINT_CREATE_MS / 1000
                time.sleep(self._accelerate(checkpoint_time))
                self.instance.has_checkpoint = True
                self.instance.checkpoint_id = f"ckpt-{int(time.time())}"
                self.metrics.checkpoints_created += 1

            # Calcular runtime
            if self.instance.last_start_time:
                runtime = time.time() - self.instance.last_start_time
                self.instance.total_runtime_seconds += runtime

            # Parar
            stop_time = LatencyConfig.SCALE_DOWN_TIME_MS / 1000
            time.sleep(self._accelerate(stop_time))

            self.instance.status = "stopped"
            self.instance.stop_count += 1
            self.metrics.scale_downs += 1

    def _idle_monitor(self):
        """Monitor de idle que faz scale down automático"""
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
# TESTES
# =============================================================================

def test_basic_flow():
    """Teste básico: cold start, warm, idle, cold"""
    print("\n" + "=" * 70)
    print("TESTE: Fluxo Básico")
    print("=" * 70)

    sim = ServerlessWhisperSimulator(
        idle_timeout_seconds=2.0,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        # 1. Primeira requisição (cold)
        print("\n[1] Primeira requisição (Cold Start)...")
        r1 = sim.process_audio(10.0)
        print(f"    {r1.start_type.upper()}: {r1.total_latency_ms:.0f}ms")
        assert r1.start_type == "cold"

        # 2. Segunda requisição (warm)
        print("[2] Segunda requisição (Warm)...")
        r2 = sim.process_audio(5.0)
        print(f"    {r2.start_type.upper()}: {r2.total_latency_ms:.0f}ms")
        assert r2.start_type == "warm"

        # 3. Aguardar idle (tempo suficiente para scale down)
        print("[3] Aguardando idle timeout...")
        # Aguardar mais tempo para garantir que o monitor detecte e faça scale down
        max_wait = 50  # Máximo de iterações
        for i in range(max_wait):
            time.sleep(sim._accelerate(0.5))
            if sim.instance.status == "stopped":
                break
        assert sim.instance.status == "stopped", f"Status: {sim.instance.status}"
        print("    Scale down OK")

        # 4. Terceira requisição (com checkpoint)
        print("[4] Terceira requisição (Checkpoint restore)...")
        r3 = sim.process_audio(8.0)
        print(f"    {r3.start_type.upper()}: {r3.total_latency_ms:.0f}ms")
        assert r3.start_type == "checkpoint"

        sim.stop()
        sim.metrics.print_report()

        # Validações
        assert sim.metrics.scale_ups == 2
        assert sim.metrics.scale_downs == 1
        assert sim.metrics.checkpoints_created == 1
        assert sim.metrics.checkpoints_restored == 1

        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_burst_requests():
    """Teste de burst: múltiplas requisições rápidas"""
    print("\n" + "=" * 70)
    print("TESTE: Burst de Requisições")
    print("=" * 70)

    sim = ServerlessWhisperSimulator(
        idle_timeout_seconds=5.0,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        # Burst de 10 requisições
        print("\n[1] Enviando burst de 10 requisições...")
        for i in range(10):
            audio_len = random.uniform(2.0, 15.0)
            result = sim.process_audio(audio_len)
            start_type = "C" if result.start_type == "cold" else "W"
            print(f"    [{i+1}] {start_type} - {result.total_latency_ms:.0f}ms")
            time.sleep(sim._accelerate(0.1))  # Pequena pausa entre requisições

        sim.stop()

        # Validações
        assert len(sim.metrics.cold_starts) == 1  # Apenas a primeira é cold
        assert len(sim.metrics.warm_starts) == 9  # Resto é warm
        assert sim.metrics.scale_ups == 1

        print(f"\n    Cold starts: {len(sim.metrics.cold_starts)}")
        print(f"    Warm starts: {len(sim.metrics.warm_starts)}")
        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_intermittent_usage():
    """Teste de uso intermitente com múltiplos cold starts"""
    print("\n" + "=" * 70)
    print("TESTE: Uso Intermitente")
    print("=" * 70)

    sim = ServerlessWhisperSimulator(
        idle_timeout_seconds=1.5,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        for cycle in range(3):
            print(f"\n--- Ciclo {cycle + 1} ---")

            # Algumas requisições
            for i in range(3):
                result = sim.process_audio(random.uniform(3.0, 10.0))
                start_type = result.start_type[0].upper()
                print(f"    [{i+1}] {start_type} - {result.total_latency_ms:.0f}ms")

            # Aguardar idle (se não for último ciclo)
            if cycle < 2:
                print("    Aguardando idle...")
                time.sleep(sim._accelerate(3.0))

        sim.stop()
        sim.metrics.print_report()

        # Validações
        # Devemos ter 1 cold + 2 checkpoint (ou mais dependendo do timing)
        assert sim.metrics.scale_downs >= 2
        assert len(sim.metrics.requests) == 9

        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_no_checkpoint_mode():
    """Teste sem checkpoint (modo econômico)"""
    print("\n" + "=" * 70)
    print("TESTE: Modo Econômico (sem checkpoint)")
    print("=" * 70)

    sim = ServerlessWhisperSimulator(
        idle_timeout_seconds=1.5,
        use_checkpoint=False,  # Sem checkpoint
        accelerated=True,
    )

    try:
        sim.start()

        # Primeira requisição
        print("\n[1] Primeira requisição...")
        r1 = sim.process_audio(5.0)
        assert r1.start_type == "cold"

        # Aguardar idle
        print("[2] Aguardando idle...")
        time.sleep(sim._accelerate(3.0))

        # Segunda requisição (cold novamente, sem checkpoint)
        print("[3] Segunda requisição após idle...")
        r2 = sim.process_audio(5.0)
        assert r2.start_type == "cold"  # Cold, não checkpoint

        sim.stop()

        # Validações
        assert sim.metrics.checkpoints_created == 0
        assert sim.metrics.checkpoints_restored == 0
        assert len(sim.metrics.cold_starts) == 2

        print(f"\n    Cold starts: {len(sim.metrics.cold_starts)}")
        print(f"    Checkpoints: {sim.metrics.checkpoints_created}")
        print("\n✅ TESTE PASSOU!")
        return True

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    finally:
        sim.stop()


def test_cost_estimation():
    """Teste de estimativa de custo"""
    print("\n" + "=" * 70)
    print("TESTE: Estimativa de Custo")
    print("=" * 70)

    sim = ServerlessWhisperSimulator(
        idle_timeout_seconds=30.0,
        use_checkpoint=True,
        accelerated=True,
    )

    try:
        sim.start()

        # Simular uso
        print("\n[1] Processando 20 requisições...")
        for i in range(20):
            sim.process_audio(random.uniform(5.0, 30.0))

        sim.stop()

        # Calcular custo
        runtime_hours = sim.instance.total_runtime_seconds / 3600
        cost = runtime_hours * sim.instance.hourly_cost

        print(f"\n    Runtime: {sim.instance.total_runtime_seconds:.1f}s")
        print(f"    Runtime (horas): {runtime_hours:.4f}h")
        print(f"    Custo estimado: ${cost:.6f}")
        print(f"    Taxa horária: ${sim.instance.hourly_cost}/hr")

        # Validação básica
        assert sim.metrics.total_cost >= 0

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
    print("WHISPER E2E SIMULATION TESTS")
    print("=" * 70)

    tests = [
        ("Fluxo Básico", test_basic_flow),
        ("Burst de Requisições", test_burst_requests),
        ("Uso Intermitente", test_intermittent_usage),
        ("Modo Econômico", test_no_checkpoint_mode),
        ("Estimativa de Custo", test_cost_estimation),
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
