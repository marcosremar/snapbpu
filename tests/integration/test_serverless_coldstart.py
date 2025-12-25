"""
Test: Serverless Cold Start / Warm Start

Simula um usuário fazendo requisições periódicas para medir:
- Cold start time (máquina parada → running)
- Warm start time (máquina já running)
- Checkpoint restore time (cuda-checkpoint)

Fluxo:
1. Deploy instância TensorDock
2. Fazer 1ª requisição (warm - máquina já running)
3. Aguardar scale down (idle timeout)
4. Fazer 2ª requisição (cold start - máquina parada)
5. Repetir ciclos
"""

import os
import sys
import time
import statistics
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.gpu.tensordock import TensorDockService, get_tensordock_service
from src.modules.serverless.service import ServerlessService, ProviderType
from src.modules.serverless.checkpoint import get_checkpoint_service
from src.config.database import get_session_factory


@dataclass
class RequestResult:
    """Resultado de uma requisição"""
    timestamp: datetime
    response_time_ms: float
    is_cold_start: bool
    instance_status_before: str
    checkpoint_restored: bool = False


@dataclass
class TestResults:
    """Resultados do teste"""
    requests: List[RequestResult] = field(default_factory=list)
    cold_starts: List[float] = field(default_factory=list)
    warm_starts: List[float] = field(default_factory=list)

    @property
    def avg_cold_start_ms(self) -> float:
        return statistics.mean(self.cold_starts) if self.cold_starts else 0

    @property
    def avg_warm_start_ms(self) -> float:
        return statistics.mean(self.warm_starts) if self.warm_starts else 0

    @property
    def p95_cold_start_ms(self) -> float:
        if not self.cold_starts:
            return 0
        sorted_times = sorted(self.cold_starts)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]


def simulate_inference_request(
    tensordock: TensorDockService,
    instance_id: str,
    ssh_host: str,
    ssh_port: int,
) -> dict:
    """
    Simula uma requisição de inferência.
    Na prática, isso seria uma chamada HTTP para um modelo.
    """
    import subprocess

    start = time.time()

    # Simular inferência (echo simples para medir latência SSH)
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=10",
                "-p", str(ssh_port),
                f"root@{ssh_host}",
                "echo 'inference_ok'; nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        latency_ms = (time.time() - start) * 1000

        if "inference_ok" in result.stdout:
            return {
                "success": True,
                "latency_ms": latency_ms,
                "gpu_util": result.stdout.strip().split('\n')[-1],
            }
        else:
            return {
                "success": False,
                "latency_ms": latency_ms,
                "error": result.stderr,
            }

    except Exception as e:
        return {
            "success": False,
            "latency_ms": (time.time() - start) * 1000,
            "error": str(e),
        }


def run_serverless_test(
    num_cycles: int = 3,
    scale_down_timeout: int = 30,  # Segundos de idle para scale down
    wait_between_requests: int = 60,  # Segundos entre requisições
):
    """
    Executa teste de serverless com múltiplos ciclos cold/warm start.

    Args:
        num_cycles: Número de ciclos cold start/warm start
        scale_down_timeout: Segundos de idle antes do scale down
        wait_between_requests: Segundos entre requisições
    """
    print("=" * 70)
    print("TESTE: Serverless Cold Start / Warm Start (TensorDock)")
    print("=" * 70)
    print()

    # Inicializar serviços
    tensordock = get_tensordock_service()
    session_factory = get_session_factory()
    results = TestResults()

    # 1. Deploy instância
    print("[1/5] Deployando instância TensorDock...")
    deploy_start = time.time()

    deploy_result = tensordock.deploy_and_wait(
        name=f"serverless-test-{int(time.time())}",
        gpu_model="geforcertx4090-pcie-24gb",  # RTX 4090 disponível no TensorDock
        gpu_count=1,
        vcpu=4,
        ram_gb=16,
        storage_gb=100,
        timeout=300,
    )

    if not deploy_result.get("success"):
        print(f"ERRO: Deploy falhou - {deploy_result.get('error')}")
        return None

    instance_id = deploy_result["instance_id"]
    ssh_host = deploy_result["ssh_host"]
    ssh_port = deploy_result["ssh_port"]
    deploy_time = time.time() - deploy_start

    print(f"    Instância: {instance_id}")
    print(f"    SSH: {ssh_host}:{ssh_port}")
    print(f"    Deploy time: {deploy_time:.1f}s")
    print()

    # 2. Setup cuda-checkpoint
    print("[2/5] Configurando cuda-checkpoint...")
    checkpoint_service = get_checkpoint_service()
    setup_result = checkpoint_service.setup_instance(instance_id, ssh_host, ssh_port)
    if setup_result.get("success"):
        print(f"    cuda-checkpoint instalado (driver: {setup_result.get('driver')})")
    else:
        print(f"    AVISO: cuda-checkpoint não disponível - {setup_result.get('error')}")
    print()

    # 3. Executar ciclos de teste
    print(f"[3/5] Executando {num_cycles} ciclos de teste...")
    print(f"    Scale down timeout: {scale_down_timeout}s")
    print(f"    Wait entre requisições: {wait_between_requests}s")
    print()

    try:
        for cycle in range(num_cycles):
            print(f"--- Ciclo {cycle + 1}/{num_cycles} ---")

            # Verificar status atual
            instance = tensordock.get_instance(instance_id)
            status_before = instance.status if instance else "unknown"

            is_cold = status_before.lower() in ("stopped", "paused", "inactive")

            # Fazer requisição
            print(f"    Status antes: {status_before}")
            req_start = time.time()

            if is_cold:
                # Precisa acordar a máquina primeiro
                print("    Acordando máquina (cold start)...")
                tensordock.start_instance(instance_id)

                # Aguardar SSH
                ssh_info = tensordock.wait_for_ssh(instance_id, timeout=120)
                if not ssh_info:
                    print("    ERRO: SSH não ficou disponível")
                    continue

                ssh_host = ssh_info["ssh_host"]
                ssh_port = ssh_info["ssh_port"]

            # Executar "inferência"
            req_result = simulate_inference_request(tensordock, instance_id, ssh_host, ssh_port)
            req_time_ms = (time.time() - req_start) * 1000

            result = RequestResult(
                timestamp=datetime.now(),
                response_time_ms=req_time_ms,
                is_cold_start=is_cold,
                instance_status_before=status_before,
            )
            results.requests.append(result)

            if is_cold:
                results.cold_starts.append(req_time_ms)
                print(f"    COLD START: {req_time_ms:.0f}ms")
            else:
                results.warm_starts.append(req_time_ms)
                print(f"    WARM START: {req_time_ms:.0f}ms")

            # Aguardar scale down (se não for último ciclo)
            if cycle < num_cycles - 1:
                wait_time = scale_down_timeout + 10  # +10s margem
                print(f"    Aguardando scale down ({wait_time}s)...")

                # Parar a máquina para simular scale down
                time.sleep(5)  # Pequena pausa
                print("    Parando instância...")
                tensordock.stop_instance(instance_id)

                # Aguardar ficar parada
                for _ in range(60):
                    instance = tensordock.get_instance(instance_id)
                    if instance and instance.status.lower() in ("stopped", "inactive"):
                        break
                    time.sleep(1)

                print(f"    Instância parada, aguardando {wait_between_requests}s...")
                time.sleep(wait_between_requests)

            print()

    except KeyboardInterrupt:
        print("\nTeste interrompido pelo usuário")

    finally:
        # 4. Cleanup
        print("[4/5] Limpando recursos...")
        tensordock.destroy_instance(instance_id)
        print(f"    Instância {instance_id} destruída")
        print()

    # 5. Resultados
    print("[5/5] Resultados")
    print("=" * 70)
    print()
    print(f"Total de requisições: {len(results.requests)}")
    print(f"Cold starts: {len(results.cold_starts)}")
    print(f"Warm starts: {len(results.warm_starts)}")
    print()

    if results.cold_starts:
        print("COLD START (máquina parada → running):")
        print(f"  Média: {results.avg_cold_start_ms:.0f}ms ({results.avg_cold_start_ms/1000:.1f}s)")
        print(f"  Min: {min(results.cold_starts):.0f}ms")
        print(f"  Max: {max(results.cold_starts):.0f}ms")
        print(f"  P95: {results.p95_cold_start_ms:.0f}ms")
        print()

    if results.warm_starts:
        print("WARM START (máquina já running):")
        print(f"  Média: {results.avg_warm_start_ms:.0f}ms")
        print(f"  Min: {min(results.warm_starts):.0f}ms")
        print(f"  Max: {max(results.warm_starts):.0f}ms")
        print()

    # Timeline
    print("TIMELINE:")
    for i, req in enumerate(results.requests):
        start_type = "COLD" if req.is_cold_start else "WARM"
        print(f"  [{i+1}] {req.timestamp.strftime('%H:%M:%S')} - {start_type}: {req.response_time_ms:.0f}ms")

    print()
    print("=" * 70)
    print("TESTE CONCLUÍDO")
    print("=" * 70)

    return results


if __name__ == "__main__":
    # Carregar .env
    from dotenv import load_dotenv
    load_dotenv()

    # Executar teste
    results = run_serverless_test(
        num_cycles=3,
        scale_down_timeout=30,
        wait_between_requests=30,
    )
