#!/usr/bin/env python3
"""
Benchmark de Latência Serverless - Testes Reais

Compara os 3 modos serverless:
1. ECONOMIC - Pause/Resume nativo VAST.ai (~7s)
2. FAST - CPU Standby (<1s) - requer GCP
3. SPOT - Instâncias interruptíveis com failover (~30s)

ATENÇÃO: Este teste CRIA RECURSOS REAIS e CUSTA DINHEIRO!

Uso:
    pytest cli/tests/test_serverless_benchmark.py -v -s
"""
import os
import sys
import json
import time
import pytest
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path
CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CLI_DIR)
sys.path.insert(0, ROOT_DIR)


def run_cli(*args, timeout=120) -> tuple:
    """Run CLI command and return output"""
    cmd = [sys.executable, "-m", "cli"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=ROOT_DIR,
    )
    return result.stdout, result.stderr, result.returncode


def get_json_from_output(stdout: str) -> Optional[Dict]:
    """Extract JSON from CLI output (skip log lines)"""
    lines = stdout.strip().split('\n')
    json_start = None
    for i, line in enumerate(lines):
        if line.strip() == '{':
            json_start = i
            break
    if json_start is not None:
        json_str = '\n'.join(lines[json_start:])
        try:
            return json.loads(json_str)
        except:
            pass
    return None


class ServerlessBenchmark:
    """Classe para medir latência de operações serverless"""

    def __init__(self):
        self.results: List[Dict] = []

    def measure(self, name: str, func, *args, **kwargs) -> Dict:
        """Mede tempo de execução de uma função"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        measurement = {
            "name": name,
            "elapsed_seconds": round(elapsed, 3),
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }
        self.results.append(measurement)
        return measurement

    def print_report(self):
        """Imprime relatório de benchmark"""
        print("\n" + "=" * 70)
        print("📊 SERVERLESS BENCHMARK REPORT")
        print("=" * 70)

        for r in self.results:
            status = "✅" if r.get("result", {}).get("success", True) else "❌"
            print(f"{status} {r['name']:40} {r['elapsed_seconds']:>8.3f}s")

        print("=" * 70)

        # Agrupar por tipo
        pause_times = [r for r in self.results if "pause" in r["name"].lower()]
        resume_times = [r for r in self.results if "resume" in r["name"].lower() or "wake" in r["name"].lower()]

        if pause_times:
            avg_pause = sum(r["elapsed_seconds"] for r in pause_times) / len(pause_times)
            print(f"📉 Média PAUSE:  {avg_pause:.3f}s")

        if resume_times:
            avg_resume = sum(r["elapsed_seconds"] for r in resume_times) / len(resume_times)
            print(f"📈 Média RESUME: {avg_resume:.3f}s")

        print("=" * 70)


class TestServerlessEconomicBenchmark:
    """
    Benchmark do modo ECONOMIC (pause/resume nativo VAST.ai)

    Este é o modo mais simples - usa pause/resume nativo.
    Expectativa: ~7s para resume
    """

    @pytest.fixture(scope="class")
    def bench(self):
        """Custom benchmark fixture (renamed to avoid pytest-benchmark conflict)"""
        return ServerlessBenchmark()

    @pytest.fixture(scope="class")
    def running_instance(self):
        """Obtém ou cria uma instância running para testes"""
        # Verificar se já existe instância
        stdout, _, _ = run_cli("instance", "list")
        try:
            data = get_json_from_output(stdout)
            if data:
                instances = data.get("instances", [])
                running = [i for i in instances if i.get("actual_status") == "running"]
                if running:
                    instance = running[0]
                    print(f"\n✅ Usando instância existente: {instance['id']}")
                    yield instance
                    return
        except Exception as e:
            print(f"Erro ao listar instâncias: {e}")

        # Criar nova instância barata
        print("\n🚀 Criando instância para benchmark...")
        stdout, stderr, code = run_cli(
            "wizard", "deploy",
            "price=0.10",  # Máximo $0.10/hr
            timeout=300
        )

        if code != 0:
            pytest.skip(f"Não foi possível criar instância: {stderr}")

        # Extrair instance_id
        import re
        match = re.search(r'Instance ID:\s*(\d+)', stdout)
        if not match:
            match = re.search(r'"id":\s*(\d+)', stdout)

        if not match:
            pytest.skip("Não foi possível extrair instance_id")

        instance_id = int(match.group(1))
        print(f"✅ Instância criada: {instance_id}")

        # Esperar ficar running
        for _ in range(30):
            stdout, _, _ = run_cli("instance", "get", str(instance_id))
            if "running" in stdout.lower():
                break
            time.sleep(5)

        yield {"id": instance_id}

        # Cleanup
        print(f"\n🗑️ Deletando instância {instance_id}...")
        run_cli("instance", "delete", str(instance_id))

    def test_01_pause_instance(self, running_instance, bench):
        """Mede tempo de PAUSE (ECONOMIC mode)"""
        instance_id = running_instance["id"]

        print(f"\n⏸️ Pausando instância {instance_id}...")

        def pause():
            stdout, stderr, code = run_cli("instance", "pause", str(instance_id), timeout=120)
            return {"success": code == 0 or "paused" in stdout.lower(), "output": stdout}

        result = bench.measure(f"ECONOMIC: Pause instance {instance_id}", pause)

        print(f"   Tempo: {result['elapsed_seconds']:.3f}s")
        assert result["result"]["success"], f"Falha ao pausar: {result['result']}"

    def test_02_verify_paused(self, running_instance):
        """Verifica que instância está pausada"""
        instance_id = running_instance["id"]

        # Esperar um pouco para o status atualizar
        time.sleep(5)

        stdout, _, _ = run_cli("instance", "get", str(instance_id))
        assert "paused" in stdout.lower() or "stopped" in stdout.lower(), f"Instância não está pausada: {stdout}"
        print(f"✅ Instância {instance_id} confirmada como pausada")

    def test_03_resume_instance(self, running_instance, bench):
        """Mede tempo de RESUME (ECONOMIC mode) - Cold Start"""
        instance_id = running_instance["id"]

        print(f"\n▶️ Resumindo instância {instance_id}...")

        def resume():
            start = time.perf_counter()
            stdout, stderr, code = run_cli("instance", "resume", str(instance_id), timeout=120)

            # Esperar até ficar running de verdade
            for _ in range(60):
                check_stdout, _, _ = run_cli("instance", "get", str(instance_id))
                if "running" in check_stdout.lower():
                    break
                time.sleep(1)

            elapsed = time.perf_counter() - start
            return {
                "success": "running" in check_stdout.lower(),
                "cold_start_seconds": elapsed,
                "output": stdout
            }

        result = bench.measure(f"ECONOMIC: Resume instance {instance_id}", resume)

        cold_start = result["result"].get("cold_start_seconds", result["elapsed_seconds"])
        print(f"   ⏱️ Cold Start: {cold_start:.3f}s")

        assert result["result"]["success"], f"Falha ao resumir: {result['result']}"

    def test_04_verify_running(self, running_instance):
        """Verifica que instância voltou a rodar"""
        instance_id = running_instance["id"]

        stdout, _, _ = run_cli("instance", "get", str(instance_id))
        assert "running" in stdout.lower(), f"Instância não está running: {stdout}"
        print(f"✅ Instância {instance_id} confirmada como running")

    def test_05_multiple_cycles(self, running_instance, bench):
        """Executa múltiplos ciclos pause/resume para média mais precisa"""
        instance_id = running_instance["id"]

        cycles = 3
        resume_times = []

        for i in range(cycles):
            print(f"\n🔄 Ciclo {i+1}/{cycles}")

            # Pause
            run_cli("instance", "pause", str(instance_id), timeout=120)
            time.sleep(5)  # Esperar pausar

            # Resume e medir
            start = time.perf_counter()
            run_cli("instance", "resume", str(instance_id), timeout=120)

            # Esperar até running
            for _ in range(60):
                stdout, _, _ = run_cli("instance", "get", str(instance_id))
                if "running" in stdout.lower():
                    break
                time.sleep(1)

            elapsed = time.perf_counter() - start
            resume_times.append(elapsed)
            print(f"   Ciclo {i+1}: {elapsed:.3f}s")

        avg_time = sum(resume_times) / len(resume_times)
        min_time = min(resume_times)
        max_time = max(resume_times)

        print(f"\n📊 ECONOMIC Mode - Estatísticas de Resume:")
        print(f"   Média:  {avg_time:.3f}s")
        print(f"   Mínimo: {min_time:.3f}s")
        print(f"   Máximo: {max_time:.3f}s")

        bench.results.append({
            "name": "ECONOMIC: Average Resume (3 cycles)",
            "elapsed_seconds": avg_time,
            "min_seconds": min_time,
            "max_seconds": max_time,
            "cycles": cycles,
            "all_times": resume_times,
        })

    def test_99_print_report(self, bench):
        """Imprime relatório final"""
        bench.print_report()


class TestSpotWorkflowBenchmark:
    """
    Benchmark do modo SPOT com failover

    Testa o workflow completo:
    1. Criar template de instância existente
    2. Deploy spot usando template
    3. Simular failover
    4. Medir tempo de recovery
    """

    @pytest.fixture(scope="class")
    def bench(self):
        """Custom benchmark fixture (renamed to avoid pytest-benchmark conflict)"""
        return ServerlessBenchmark()

    @pytest.fixture(scope="class")
    def running_instance(self):
        """Obtém instância running para criar template"""
        stdout, _, _ = run_cli("instance", "list")
        try:
            data = get_json_from_output(stdout)
            if data:
                instances = data.get("instances", [])
                running = [i for i in instances if i.get("actual_status") == "running"]
                if running:
                    yield running[0]
                    return
        except:
            pass
        pytest.skip("Nenhuma instância running disponível para criar template")

    def test_01_create_spot_template(self, running_instance, bench):
        """Cria template spot a partir de instância"""
        instance_id = running_instance["id"]

        print(f"\n📸 Criando template spot da instância {instance_id}...")

        def create_template():
            stdout, stderr, code = run_cli(
                "spot", "template", "create", str(instance_id),
                timeout=300
            )
            return {
                "success": "template" in stdout.lower() or "spot_tpl" in stdout,
                "output": stdout
            }

        result = bench.measure(f"SPOT: Create template from {instance_id}", create_template)

        print(f"   Tempo: {result['elapsed_seconds']:.3f}s")
        # Template creation pode demorar por causa do snapshot

    def test_02_list_templates(self):
        """Lista templates disponíveis"""
        stdout, _, code = run_cli("spot", "template", "list")
        print(f"\n📋 Templates disponíveis:\n{stdout}")

    def test_03_spot_pricing(self):
        """Mostra preços spot atuais"""
        stdout, _, code = run_cli("spot", "pricing")
        print(f"\n💰 Spot Pricing:\n{stdout}")

    def test_04_deploy_spot(self, bench):
        """Deploy spot usando template (se disponível)"""
        # Primeiro verificar se tem template
        stdout, _, _ = run_cli("spot", "template", "list")

        if "No spot templates" in stdout:
            pytest.skip("Nenhum template disponível para deploy")

        # Extrair template_id
        import re
        match = re.search(r'spot_tpl_\w+', stdout)
        if not match:
            pytest.skip("Não foi possível extrair template_id")

        template_id = match.group(0)
        print(f"\n🎲 Deployando spot com template {template_id}...")

        def deploy():
            stdout, stderr, code = run_cli(
                "spot", "deploy",
                f"--template={template_id}",
                "--max-price=0.20",
                timeout=300
            )
            return {
                "success": "deployed" in stdout.lower() or "instance" in stdout.lower(),
                "output": stdout
            }

        result = bench.measure(f"SPOT: Deploy with template {template_id}", deploy)
        print(f"   Tempo: {result['elapsed_seconds']:.3f}s")

    def test_05_spot_status(self):
        """Verifica status de instâncias spot"""
        stdout, _, code = run_cli("spot", "list")
        print(f"\n📊 Spot instances:\n{stdout}")

    def test_99_print_report(self, bench):
        """Imprime relatório final"""
        bench.print_report()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
