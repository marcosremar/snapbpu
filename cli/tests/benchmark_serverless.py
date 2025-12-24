#!/usr/bin/env python3
"""
Benchmark Direto de Latência Serverless

Mede o tempo de pause/resume no modo ECONOMIC.
Roda manualmente, sem pytest.

Uso:
    source .venv/bin/activate
    python3 cli/tests/benchmark_serverless.py
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime

CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CLI_DIR)
sys.path.insert(0, ROOT_DIR)


def run_cli(*args, timeout=300):
    """Run CLI command"""
    cmd = [sys.executable, "-m", "cli"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=ROOT_DIR,
    )
    return result.stdout, result.stderr, result.returncode


def get_json_from_output(stdout):
    """Extract JSON from output"""
    lines = stdout.strip().split('\n')
    for i, line in enumerate(lines):
        if line.strip() == '{':
            json_str = '\n'.join(lines[i:])
            try:
                return json.loads(json_str)
            except:
                pass
    return None


def wait_for_status(instance_id, target_status, max_wait=120):
    """Wait for instance to reach target status"""
    start = time.time()
    while time.time() - start < max_wait:
        stdout, _, _ = run_cli("instance", "get", str(instance_id))
        if target_status in stdout.lower():
            return True, time.time() - start
        time.sleep(2)
    return False, time.time() - start


def measure_pause(instance_id):
    """Measure pause time"""
    print(f"\n⏸️  PAUSANDO instância {instance_id}...")
    start = time.time()

    stdout, stderr, code = run_cli("instance", "pause", str(instance_id))

    # Wait until paused
    success, elapsed = wait_for_status(instance_id, "paused", max_wait=60)

    total_time = time.time() - start
    print(f"    Tempo total: {total_time:.2f}s")
    return total_time, success


def measure_resume(instance_id):
    """Measure resume time (cold start)"""
    print(f"\n▶️  RESUMINDO instância {instance_id}...")
    start = time.time()

    stdout, stderr, code = run_cli("instance", "resume", str(instance_id))

    # Wait until running
    success, elapsed = wait_for_status(instance_id, "running", max_wait=120)

    total_time = time.time() - start
    print(f"    Tempo total: {total_time:.2f}s")
    return total_time, success


def get_running_instance():
    """Get a running instance or create one"""
    print("\n🔍 Buscando instância running...")
    stdout, _, _ = run_cli("instance", "list")
    data = get_json_from_output(stdout)

    if data:
        instances = data.get("instances", [])
        running = [i for i in instances if i.get("actual_status") == "running"]
        if running:
            inst = running[0]
            print(f"   ✅ Encontrada: {inst['id']} ({inst.get('gpu_name', 'Unknown GPU')})")
            return inst

    # Create new instance
    print("\n🚀 Criando instância para benchmark...")
    stdout, stderr, code = run_cli("wizard", "deploy", "price=0.15", timeout=300)

    if code != 0:
        print(f"❌ Erro ao criar instância: {stderr}")
        return None

    # Extract instance_id
    import re
    match = re.search(r'Instance ID:\s*(\d+)', stdout)
    if match:
        instance_id = int(match.group(1))
        print(f"   ✅ Criada: {instance_id}")
        return {"id": instance_id}

    return None


def main():
    print("=" * 70)
    print("📊 BENCHMARK SERVERLESS - MODO ECONOMIC (Pause/Resume)")
    print("=" * 70)
    print(f"   Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Get or create instance
    instance = get_running_instance()
    if not instance:
        print("❌ Não foi possível obter instância para benchmark")
        sys.exit(1)

    instance_id = instance["id"]
    gpu_name = instance.get("gpu_name", "Unknown")

    print(f"\n📋 Instância: {instance_id}")
    print(f"   GPU: {gpu_name}")

    # Run benchmark cycles
    cycles = 3
    pause_times = []
    resume_times = []

    for i in range(cycles):
        print(f"\n{'='*70}")
        print(f"🔄 CICLO {i+1}/{cycles}")
        print("=" * 70)

        # Pause
        pause_time, pause_ok = measure_pause(instance_id)
        if pause_ok:
            pause_times.append(pause_time)
        else:
            print("   ⚠️  Pause pode não ter completado")

        time.sleep(3)  # Small delay

        # Resume
        resume_time, resume_ok = measure_resume(instance_id)
        if resume_ok:
            resume_times.append(resume_time)
        else:
            print("   ⚠️  Resume pode não ter completado")

        time.sleep(5)  # Wait for stability

    # Print results
    print("\n" + "=" * 70)
    print("📊 RESULTADOS DO BENCHMARK")
    print("=" * 70)
    print(f"   GPU: {gpu_name}")
    print(f"   Modo: ECONOMIC (VAST.ai pause/resume)")
    print(f"   Ciclos: {cycles}")
    print("-" * 70)

    if pause_times:
        avg_pause = sum(pause_times) / len(pause_times)
        print(f"\n⏸️  PAUSE Times:")
        for i, t in enumerate(pause_times):
            print(f"      Ciclo {i+1}: {t:.2f}s")
        print(f"      Média:   {avg_pause:.2f}s")
        print(f"      Min:     {min(pause_times):.2f}s")
        print(f"      Max:     {max(pause_times):.2f}s")

    if resume_times:
        avg_resume = sum(resume_times) / len(resume_times)
        print(f"\n▶️  RESUME Times (Cold Start):")
        for i, t in enumerate(resume_times):
            print(f"      Ciclo {i+1}: {t:.2f}s")
        print(f"      Média:   {avg_resume:.2f}s")
        print(f"      Min:     {min(resume_times):.2f}s")
        print(f"      Max:     {max(resume_times):.2f}s")

    print("\n" + "=" * 70)

    # Summary
    if resume_times:
        avg_resume = sum(resume_times) / len(resume_times)
        print(f"\n🎯 LATÊNCIA MÉDIA COLD START: {avg_resume:.2f}s")

        if avg_resume < 10:
            print("   ✅ Excelente! Abaixo de 10s")
        elif avg_resume < 20:
            print("   ⚠️  Bom, mas pode melhorar")
        else:
            print("   ❌ Acima do esperado (~7s)")

    print("\n" + "=" * 70)

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "instance_id": instance_id,
        "gpu_name": gpu_name,
        "mode": "economic",
        "cycles": cycles,
        "pause_times": pause_times,
        "resume_times": resume_times,
        "avg_pause": sum(pause_times) / len(pause_times) if pause_times else 0,
        "avg_resume": sum(resume_times) / len(resume_times) if resume_times else 0,
    }

    results_file = os.path.join(CLI_DIR, "benchmark_results.json")

    # Append to existing results
    all_results = []
    if os.path.exists(results_file):
        try:
            with open(results_file) as f:
                all_results = json.load(f)
        except:
            pass

    all_results.append(results)

    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"💾 Resultados salvos em: {results_file}")

    return results


if __name__ == "__main__":
    main()
