#!/usr/bin/env python3
"""
Benchmark DIRETO via VAST.ai API

Mede latência de pause/resume sem passar pelo backend Dumont.
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

def get_api_key():
    config_file = Path('/home/marcos/dumontcloud/config.json')
    config = json.loads(config_file.read_text())
    users = config.get('users', {})
    for email, user_data in users.items():
        api_key = user_data.get('vast_api_key')
        if api_key:
            return api_key
    return os.environ.get('VAST_API_KEY')


def vast_api(method, endpoint, api_key, data=None):
    """Call VAST.ai API"""
    headers = {'Authorization': f'Bearer {api_key}'}
    url = f'https://console.vast.ai/api/v0{endpoint}'

    if method == 'GET':
        resp = requests.get(url, headers=headers)
    elif method == 'PUT':
        resp = requests.put(url, headers=headers, json=data or {})
    elif method == 'POST':
        resp = requests.post(url, headers=headers, json=data or {})

    return resp


def get_instance_status(instance_id, api_key):
    """Get instance status"""
    resp = vast_api('GET', '/instances/', api_key)
    if resp.status_code == 200:
        for inst in resp.json().get('instances', []):
            if inst.get('id') == instance_id:
                return inst.get('actual_status')
    return None


def pause_instance(instance_id, api_key):
    """Pause instance via VAST API"""
    # VAST uses PUT /instances/{id}/ with {"state": "stopped"}
    resp = vast_api('PUT', f'/instances/{instance_id}/', api_key, {"state": "stopped"})
    return resp.status_code == 200


def resume_instance(instance_id, api_key):
    """Resume instance via VAST API"""
    resp = vast_api('PUT', f'/instances/{instance_id}/', api_key, {"state": "running"})
    return resp.status_code == 200


def wait_for_status(instance_id, api_key, target_statuses, max_wait=120):
    """Wait for instance to reach one of target statuses"""
    start = time.time()
    while time.time() - start < max_wait:
        status = get_instance_status(instance_id, api_key)
        print(f"      Status: {status}")
        if status in target_statuses:
            return True, time.time() - start
        time.sleep(2)
    return False, time.time() - start


def get_running_instances(api_key):
    """Get all running instances"""
    resp = vast_api('GET', '/instances/', api_key)
    if resp.status_code == 200:
        instances = resp.json().get('instances', [])
        return [i for i in instances if i.get('actual_status') == 'running']
    return []


def main():
    print("=" * 70)
    print("📊 BENCHMARK SERVERLESS DIRETO - VAST.ai API")
    print("=" * 70)
    print(f"   Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    api_key = get_api_key()
    if not api_key:
        print("❌ No API key found!")
        sys.exit(1)

    print(f"\n🔑 API Key: {api_key[:10]}...")

    # Get running instances
    running = get_running_instances(api_key)
    print(f"\n📋 Running instances: {len(running)}")

    if not running:
        print("❌ No running instances available for benchmark")
        sys.exit(1)

    for inst in running:
        print(f"   - {inst['id']}: {inst.get('gpu_name')} @ {inst.get('ssh_host')}:{inst.get('ssh_port')}")

    # Use the first running instance
    instance = running[0]
    instance_id = instance['id']
    gpu_name = instance.get('gpu_name', 'Unknown')

    print(f"\n🎯 Usando instância: {instance_id} ({gpu_name})")

    # Run benchmark
    cycles = 3
    pause_times = []
    resume_times = []

    for i in range(cycles):
        print(f"\n{'='*70}")
        print(f"🔄 CICLO {i+1}/{cycles}")
        print("=" * 70)

        # === PAUSE ===
        print(f"\n⏸️  PAUSANDO instância {instance_id}...")
        start = time.time()

        if pause_instance(instance_id, api_key):
            print("   Comando enviado, aguardando status...")
            success, elapsed = wait_for_status(instance_id, api_key, ['stopped', 'exited'], max_wait=60)
            total_time = time.time() - start

            if success:
                pause_times.append(total_time)
                print(f"   ✅ Pausado em: {total_time:.2f}s")
            else:
                print(f"   ⚠️  Timeout após {total_time:.2f}s")
        else:
            print("   ❌ Falha ao enviar comando pause")

        time.sleep(3)

        # === RESUME ===
        print(f"\n▶️  RESUMINDO instância {instance_id}...")
        start = time.time()

        if resume_instance(instance_id, api_key):
            print("   Comando enviado, aguardando status...")
            success, elapsed = wait_for_status(instance_id, api_key, ['running'], max_wait=120)
            total_time = time.time() - start

            if success:
                resume_times.append(total_time)
                print(f"   ✅ Resumido em: {total_time:.2f}s (Cold Start)")
            else:
                print(f"   ⚠️  Timeout após {total_time:.2f}s")
        else:
            print("   ❌ Falha ao enviar comando resume")

        time.sleep(5)

    # Print results
    print("\n" + "=" * 70)
    print("📊 RESULTADOS DO BENCHMARK")
    print("=" * 70)
    print(f"   GPU: {gpu_name}")
    print(f"   Modo: ECONOMIC (VAST.ai pause/resume nativo)")
    print(f"   Ciclos completados: {len(resume_times)}/{cycles}")
    print("-" * 70)

    if pause_times:
        avg_pause = sum(pause_times) / len(pause_times)
        print(f"\n⏸️  PAUSE Times:")
        for i, t in enumerate(pause_times):
            print(f"      Ciclo {i+1}: {t:.2f}s")
        print(f"      ────────────────")
        print(f"      Média:   {avg_pause:.2f}s")
        print(f"      Min:     {min(pause_times):.2f}s")
        print(f"      Max:     {max(pause_times):.2f}s")

    if resume_times:
        avg_resume = sum(resume_times) / len(resume_times)
        print(f"\n▶️  RESUME Times (Cold Start):")
        for i, t in enumerate(resume_times):
            print(f"      Ciclo {i+1}: {t:.2f}s")
        print(f"      ────────────────")
        print(f"      Média:   {avg_resume:.2f}s")
        print(f"      Min:     {min(resume_times):.2f}s")
        print(f"      Max:     {max(resume_times):.2f}s")

    print("\n" + "=" * 70)

    if resume_times:
        avg_resume = sum(resume_times) / len(resume_times)
        print(f"\n🎯 LATÊNCIA MÉDIA COLD START: {avg_resume:.2f}s")

        if avg_resume < 10:
            print("   ✅ Excelente! Abaixo de 10s")
        elif avg_resume < 20:
            print("   ⚠️  Bom, mas acima do esperado (~7s)")
        else:
            print("   ❌ Muito lento")

    print("\n" + "=" * 70)

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "instance_id": instance_id,
        "gpu_name": gpu_name,
        "mode": "economic_direct",
        "cycles": cycles,
        "pause_times": pause_times,
        "resume_times": resume_times,
        "avg_pause": sum(pause_times) / len(pause_times) if pause_times else 0,
        "avg_resume": sum(resume_times) / len(resume_times) if resume_times else 0,
    }

    results_file = Path('/home/marcos/dumontcloud/cli/benchmark_results.json')

    all_results = []
    if results_file.exists():
        try:
            all_results = json.loads(results_file.read_text())
        except:
            pass

    all_results.append(results)
    results_file.write_text(json.dumps(all_results, indent=2))

    print(f"💾 Resultados salvos em: {results_file}")

    return results


if __name__ == "__main__":
    main()
