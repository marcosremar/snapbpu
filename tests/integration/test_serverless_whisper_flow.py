"""
Test: Serverless Whisper Flow Simulation

Simula um usuário fazendo transcrições com Whisper para testar:
1. Cold Start - Primeira requisição (máquina parada)
2. Warm Start - Requisições seguidas (máquina já running)
3. Scale Down - Idle timeout (máquina para automaticamente)
4. Scale Up - Nova requisição após scale down

Este teste usa mocks para simular o provider, validando toda a lógica
do módulo serverless sem gastar créditos reais.
"""

import os
import sys
import time
import asyncio
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class MockInstanceStatus(str, Enum):
    """Status possíveis de uma instância mock"""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class MockInstance:
    """Instância GPU mockada"""
    id: str
    name: str
    status: MockInstanceStatus = MockInstanceStatus.STOPPED
    gpu_model: str = "geforcertx4090-pcie-24gb"
    gpu_count: int = 1
    ip_address: str = "192.168.1.100"
    ssh_port: int = 22
    hourly_cost: float = 0.35

    # Métricas simuladas
    gpu_utilization: float = 0.0
    last_request_at: Optional[float] = None
    start_time: Optional[float] = None

    # Contadores
    start_count: int = 0
    stop_count: int = 0


@dataclass
class RequestMetrics:
    """Métricas de uma requisição"""
    request_id: int
    timestamp: datetime
    duration_ms: float
    was_cold_start: bool
    instance_status_before: str
    instance_status_after: str
    gpu_utilization: float


@dataclass
class TestResults:
    """Resultados do teste"""
    requests: List[RequestMetrics] = field(default_factory=list)
    cold_starts: int = 0
    warm_starts: int = 0
    scale_downs: int = 0
    scale_ups: int = 0
    total_cold_start_time_ms: float = 0
    total_warm_start_time_ms: float = 0

    def add_request(self, metrics: RequestMetrics):
        self.requests.append(metrics)
        if metrics.was_cold_start:
            self.cold_starts += 1
            self.total_cold_start_time_ms += metrics.duration_ms
        else:
            self.warm_starts += 1
            self.total_warm_start_time_ms += metrics.duration_ms

    @property
    def avg_cold_start_ms(self) -> float:
        return self.total_cold_start_time_ms / self.cold_starts if self.cold_starts else 0

    @property
    def avg_warm_start_ms(self) -> float:
        return self.total_warm_start_time_ms / self.warm_starts if self.warm_starts else 0

    def print_summary(self):
        print("\n" + "=" * 70)
        print("RESULTADOS DO TESTE")
        print("=" * 70)
        print(f"\nTotal de requisições: {len(self.requests)}")
        print(f"Cold Starts: {self.cold_starts}")
        print(f"Warm Starts: {self.warm_starts}")
        print(f"Scale Downs: {self.scale_downs}")
        print(f"Scale Ups: {self.scale_ups}")
        print()

        if self.cold_starts:
            print(f"Média Cold Start: {self.avg_cold_start_ms:.0f}ms ({self.avg_cold_start_ms/1000:.2f}s)")
        if self.warm_starts:
            print(f"Média Warm Start: {self.avg_warm_start_ms:.0f}ms")

        print("\nTIMELINE:")
        for i, req in enumerate(self.requests):
            start_type = "COLD" if req.was_cold_start else "WARM"
            print(f"  [{i+1}] {req.timestamp.strftime('%H:%M:%S.%f')[:-3]} - "
                  f"{start_type}: {req.duration_ms:.0f}ms "
                  f"(GPU: {req.gpu_utilization:.0f}%)")


class MockGPUProvider:
    """
    Provider mockado que simula TensorDock/VAST.ai.

    Simula tempos realistas de:
    - Cold start: ~15-30 segundos
    - Warm start: ~50-200ms
    - Scale down: ~5 segundos
    """

    # Tempos simulados (em segundos)
    COLD_START_TIME = 0.5  # Acelerado para teste (real: 15-30s)
    WARM_START_TIME = 0.05  # 50ms
    SCALE_DOWN_TIME = 0.2  # Acelerado para teste (real: 5s)

    def __init__(self):
        self.instances: Dict[str, MockInstance] = {}
        self._lock = threading.Lock()
        self._events: List[Dict] = []

    def create_instance(self, name: str, gpu_model: str = "geforcertx4090-pcie-24gb") -> MockInstance:
        """Cria uma nova instância mock"""
        instance_id = f"mock-{len(self.instances) + 1}-{int(time.time())}"
        instance = MockInstance(
            id=instance_id,
            name=name,
            gpu_model=gpu_model,
            status=MockInstanceStatus.STOPPED,
        )
        self.instances[instance_id] = instance
        self._log_event("CREATE", instance_id, f"Instance {name} created")
        return instance

    def get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """Retorna status da instância"""
        instance = self.instances.get(instance_id)
        if not instance:
            return {"status": "not_found"}

        return {
            "instance_id": instance.id,
            "actual_status": instance.status.value,
            "gpu_name": instance.gpu_model,
            "gpu_count": instance.gpu_count,
            "ssh_host": instance.ip_address,
            "ssh_port": instance.ssh_port,
            "dph_total": instance.hourly_cost,
            "gpu_utilization": instance.gpu_utilization,
        }

    def start_instance(self, instance_id: str) -> bool:
        """Inicia uma instância (simula cold start)"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False

        with self._lock:
            if instance.status == MockInstanceStatus.RUNNING:
                return True

            instance.status = MockInstanceStatus.STARTING
            self._log_event("START", instance_id, "Starting instance...")

        # Simular tempo de boot
        time.sleep(self.COLD_START_TIME)

        with self._lock:
            instance.status = MockInstanceStatus.RUNNING
            instance.start_time = time.time()
            instance.start_count += 1
            self._log_event("STARTED", instance_id,
                          f"Instance running (start #{instance.start_count})")

        return True

    def stop_instance(self, instance_id: str) -> bool:
        """Para uma instância (simula scale down)"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False

        with self._lock:
            if instance.status == MockInstanceStatus.STOPPED:
                return True

            instance.status = MockInstanceStatus.STOPPING
            self._log_event("STOP", instance_id, "Stopping instance...")

        # Simular tempo de parada
        time.sleep(self.SCALE_DOWN_TIME)

        with self._lock:
            instance.status = MockInstanceStatus.STOPPED
            instance.gpu_utilization = 0
            instance.stop_count += 1
            self._log_event("STOPPED", instance_id,
                          f"Instance stopped (stop #{instance.stop_count})")

        return True

    def pause_instance(self, instance_id: str) -> bool:
        """Alias para stop_instance"""
        return self.stop_instance(instance_id)

    def resume_instance(self, instance_id: str) -> bool:
        """Alias para start_instance"""
        return self.start_instance(instance_id)

    def destroy_instance(self, instance_id: str) -> bool:
        """Destrói uma instância"""
        if instance_id in self.instances:
            del self.instances[instance_id]
            self._log_event("DESTROY", instance_id, "Instance destroyed")
            return True
        return False

    def simulate_gpu_usage(self, instance_id: str, utilization: float):
        """Simula uso de GPU"""
        instance = self.instances.get(instance_id)
        if instance:
            instance.gpu_utilization = utilization
            instance.last_request_at = time.time()

    def _log_event(self, event_type: str, instance_id: str, message: str):
        """Registra evento para debugging"""
        self._events.append({
            "timestamp": datetime.now(),
            "type": event_type,
            "instance_id": instance_id,
            "message": message,
        })


class ServerlessSimulator:
    """
    Simula o comportamento do módulo serverless.

    Gerencia:
    - Auto scale up quando há requisição
    - Auto scale down quando idle
    - Monitoramento de GPU utilization
    """

    def __init__(
        self,
        provider: MockGPUProvider,
        idle_timeout_seconds: float = 2.0,  # Acelerado para teste
        gpu_threshold: float = 5.0,
    ):
        self.provider = provider
        self.idle_timeout = idle_timeout_seconds
        self.gpu_threshold = gpu_threshold

        self._instance: Optional[MockInstance] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        self.results = TestResults()

    def setup(self):
        """Inicializa o simulador"""
        # Criar instância inicial (parada)
        self._instance = self.provider.create_instance(
            name="whisper-serverless",
            gpu_model="geforcertx4090-pcie-24gb"
        )

        # Iniciar monitor de idle
        self._running = True
        self._monitor_thread = threading.Thread(target=self._idle_monitor, daemon=True)
        self._monitor_thread.start()

        print(f"[SETUP] Instance created: {self._instance.id}")
        print(f"[SETUP] Idle timeout: {self.idle_timeout}s")
        print(f"[SETUP] GPU threshold: {self.gpu_threshold}%")

    def teardown(self):
        """Finaliza o simulador"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

        if self._instance:
            self.provider.destroy_instance(self._instance.id)

    def process_request(self, audio_duration_seconds: float = 5.0) -> RequestMetrics:
        """
        Processa uma requisição de transcrição Whisper.

        Simula:
        - Cold start se máquina parada
        - Warm start se máquina running
        - Uso de GPU durante processamento
        """
        request_id = len(self.results.requests) + 1
        start_time = time.time()

        with self._lock:
            status_before = self._instance.status.value
            was_cold_start = self._instance.status != MockInstanceStatus.RUNNING

        print(f"\n[REQ {request_id}] Processing {audio_duration_seconds}s audio...")
        print(f"[REQ {request_id}] Instance status: {status_before}")

        # Scale up se necessário
        if was_cold_start:
            print(f"[REQ {request_id}] COLD START - Starting instance...")
            self.results.scale_ups += 1
            self.provider.start_instance(self._instance.id)

        # Simular processamento
        processing_time = audio_duration_seconds * 0.1  # ~10% do tempo real
        self.provider.simulate_gpu_usage(self._instance.id, 85.0)  # 85% GPU
        time.sleep(processing_time)
        self.provider.simulate_gpu_usage(self._instance.id, 0.0)  # Idle

        # Calcular métricas
        duration_ms = (time.time() - start_time) * 1000

        with self._lock:
            status_after = self._instance.status.value

        metrics = RequestMetrics(
            request_id=request_id,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            was_cold_start=was_cold_start,
            instance_status_before=status_before,
            instance_status_after=status_after,
            gpu_utilization=85.0,
        )

        self.results.add_request(metrics)

        print(f"[REQ {request_id}] {'COLD' if was_cold_start else 'WARM'} START: {duration_ms:.0f}ms")

        return metrics

    def _idle_monitor(self):
        """Thread que monitora idle e faz scale down automático"""
        while self._running:
            time.sleep(0.5)  # Check interval

            with self._lock:
                if not self._instance:
                    continue

                if self._instance.status != MockInstanceStatus.RUNNING:
                    continue

                # Verificar se está idle
                if self._instance.gpu_utilization > self.gpu_threshold:
                    continue

                if not self._instance.last_request_at:
                    continue

                idle_time = time.time() - self._instance.last_request_at

                if idle_time >= self.idle_timeout:
                    print(f"\n[MONITOR] Instance idle for {idle_time:.1f}s - Scaling down...")
                    self.results.scale_downs += 1

            # Scale down fora do lock
            if idle_time >= self.idle_timeout:
                self.provider.stop_instance(self._instance.id)
                print(f"[MONITOR] Scale down complete")


def run_whisper_simulation():
    """
    Executa simulação completa de um usuário usando Whisper.

    Cenário:
    1. Primeira requisição (Cold Start)
    2. Segunda requisição imediata (Warm Start)
    3. Terceira requisição imediata (Warm Start)
    4. Pausa - usuário para de usar
    5. Scale down automático após idle timeout
    6. Quarta requisição (Cold Start novamente)
    7. Quinta requisição (Warm Start)
    """
    print("=" * 70)
    print("TESTE: Simulação Whisper Serverless")
    print("=" * 70)
    print()
    print("Cenário:")
    print("  1. Usuário faz 3 requisições seguidas")
    print("  2. Usuário para de usar (idle)")
    print("  3. Sistema faz scale down automático")
    print("  4. Usuário volta e faz mais 2 requisições")
    print()

    # Criar provider e simulador
    provider = MockGPUProvider()
    simulator = ServerlessSimulator(
        provider=provider,
        idle_timeout_seconds=2.0,  # 2 segundos para teste rápido
    )

    try:
        # Setup
        print("-" * 70)
        print("FASE 1: Setup")
        print("-" * 70)
        simulator.setup()
        print()

        # Fase 2: Primeiras requisições (Cold + Warm + Warm)
        print("-" * 70)
        print("FASE 2: Primeiras 3 requisições")
        print("-" * 70)

        # Requisição 1: Cold Start
        simulator.process_request(audio_duration_seconds=10.0)

        # Requisição 2: Warm Start (imediata)
        time.sleep(0.1)
        simulator.process_request(audio_duration_seconds=5.0)

        # Requisição 3: Warm Start (imediata)
        time.sleep(0.1)
        simulator.process_request(audio_duration_seconds=8.0)

        print()

        # Fase 3: Idle e Scale Down
        print("-" * 70)
        print("FASE 3: Idle - aguardando scale down automático")
        print("-" * 70)

        print("[USER] Usuário parou de fazer requisições...")

        # Aguardar scale down (idle timeout + margem)
        wait_time = simulator.idle_timeout + 1.0
        print(f"[WAIT] Aguardando {wait_time:.1f}s para scale down...")
        time.sleep(wait_time)

        # Verificar se fez scale down
        status = provider.get_instance_status(simulator._instance.id)
        print(f"[CHECK] Status após idle: {status['actual_status']}")
        print()

        # Fase 4: Novas requisições (Cold + Warm)
        print("-" * 70)
        print("FASE 4: Usuário retorna - mais 2 requisições")
        print("-" * 70)

        # Requisição 4: Cold Start (após scale down)
        simulator.process_request(audio_duration_seconds=15.0)

        # Requisição 5: Warm Start
        time.sleep(0.1)
        simulator.process_request(audio_duration_seconds=7.0)

        print()

        # Resultados
        simulator.results.print_summary()

        # Validações
        print("\n" + "=" * 70)
        print("VALIDAÇÕES")
        print("=" * 70)

        passed = True

        # Deve ter 2 cold starts (req 1 e req 4)
        if simulator.results.cold_starts == 2:
            print("✅ Cold Starts: 2 (correto)")
        else:
            print(f"❌ Cold Starts: {simulator.results.cold_starts} (esperado: 2)")
            passed = False

        # Deve ter 3 warm starts (req 2, 3, 5)
        if simulator.results.warm_starts == 3:
            print("✅ Warm Starts: 3 (correto)")
        else:
            print(f"❌ Warm Starts: {simulator.results.warm_starts} (esperado: 3)")
            passed = False

        # Deve ter 1 scale down
        if simulator.results.scale_downs >= 1:
            print(f"✅ Scale Downs: {simulator.results.scale_downs} (correto)")
        else:
            print(f"❌ Scale Downs: {simulator.results.scale_downs} (esperado: >= 1)")
            passed = False

        # Deve ter 2 scale ups
        if simulator.results.scale_ups == 2:
            print(f"✅ Scale Ups: {simulator.results.scale_ups} (correto)")
        else:
            print(f"❌ Scale Ups: {simulator.results.scale_ups} (esperado: 2)")
            passed = False

        # Cold start deve ser mais lento que warm start
        if simulator.results.avg_cold_start_ms > simulator.results.avg_warm_start_ms:
            print(f"✅ Cold Start ({simulator.results.avg_cold_start_ms:.0f}ms) > "
                  f"Warm Start ({simulator.results.avg_warm_start_ms:.0f}ms)")
        else:
            print(f"❌ Cold Start deveria ser mais lento que Warm Start")
            passed = False

        print()
        if passed:
            print("🎉 TODOS OS TESTES PASSARAM!")
        else:
            print("❌ ALGUNS TESTES FALHARAM")

        return passed

    finally:
        simulator.teardown()


def run_stress_test(num_requests: int = 20):
    """
    Teste de stress com múltiplas requisições.

    Simula uso intenso seguido de períodos de idle.
    """
    print("=" * 70)
    print(f"TESTE DE STRESS: {num_requests} requisições")
    print("=" * 70)
    print()

    provider = MockGPUProvider()
    simulator = ServerlessSimulator(
        provider=provider,
        idle_timeout_seconds=1.5,
    )

    try:
        simulator.setup()

        # Padrão: burst de requisições, idle, burst, idle...
        import random

        burst_sizes = [5, 3, 7, 5]  # Tamanhos dos bursts
        idle_times = [3.0, 2.5, 4.0]  # Tempos de idle entre bursts

        request_count = 0
        for i, burst_size in enumerate(burst_sizes):
            if request_count >= num_requests:
                break

            print(f"\n--- Burst {i+1}: {burst_size} requisições ---")

            for j in range(burst_size):
                if request_count >= num_requests:
                    break

                # Áudio de 2-15 segundos
                audio_duration = random.uniform(2.0, 15.0)
                simulator.process_request(audio_duration_seconds=audio_duration)
                request_count += 1

                # Pequena pausa entre requisições do mesmo burst
                time.sleep(random.uniform(0.05, 0.2))

            # Idle entre bursts
            if i < len(idle_times) and request_count < num_requests:
                print(f"\n[IDLE] Pausa de {idle_times[i]:.1f}s...")
                time.sleep(idle_times[i])

        simulator.results.print_summary()

        print(f"\n[STATS] Instância iniciada {simulator._instance.start_count}x")
        print(f"[STATS] Instância parada {simulator._instance.stop_count}x")

        return True

    finally:
        simulator.teardown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Teste Serverless Whisper")
    parser.add_argument("--stress", action="store_true", help="Executar teste de stress")
    parser.add_argument("--requests", type=int, default=20, help="Número de requisições para stress test")
    args = parser.parse_args()

    if args.stress:
        success = run_stress_test(num_requests=args.requests)
    else:
        success = run_whisper_simulation()

    sys.exit(0 if success else 1)
