#!/usr/bin/env python3
"""
Benchmark MULTI-GPU - Compara latência entre diferentes GPUs
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
    headers = {'Authorization': f'Bearer {api_key}'}
    url = f'https://console.vast.ai/api/v0{endpoint}'
    if method == 'GET':
        resp = requests.get(url, headers=headers)
    elif method == 'PUT':
        resp = requests.put(url, headers=headers, json=data or {})
    return resp


def get_instance_status(instance_id, api_key):
    resp = vast_api('GET', '/instances/', api_key)
    if resp.status_code == 200:
        for inst in resp.json().get('instances', []):
            if inst.get('id') == instance_id:
                return inst.get('actual_status')
    return None


def wait_for_status(instance_id, api_key, target_statuses, max_wait=120):
    start = time.time()
    while time.time() - start < max_wait:
        status = get_instance_status(instance_id, api_key)
        if status in target_statuses:
            return True, time.time() - start
        time.sleep(2)
    return False, time.time() - start


def benchmark_single_cycle(instance_id, api_key):
    """Run single pause/resume cycle and return times"""
    # PAUSE
    print(f"   ⏸️  Pausando...", end='', flush=True)
    start = time.time()
    vast_api('PUT', f'/instances/{instance_id}/', api_key, {"state": "stopped"})
    success, _ = wait_for_status(instance_id, api_key, ['stopped', 'exited'], max_wait=60)
    pause_time = time.time() - start
    print(f" {pause_time:.1f}s")

    time.sleep(2)

    # RESUME
    print(f"   ▶️  Resumindo...", end='', flush=True)
    start = time.time()
    vast_api('PUT', f'/instances/{instance_id}/', api_key, {"state": "running"})
    success, _ = wait_for_status(instance_id, api_key, ['running'], max_wait=120)
    resume_time = time.time() - start
    print(f" {resume_time:.1f}s")

    return pause_time, resume_time


def main():
    print("=" * 70)
    print("📊 BENCHMARK MULTI-GPU - Comparação de Latência")
    print("=" * 70)
    print(f"   Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    api_key = get_api_key()

    # Get all running instances
    resp = vast_api('GET', '/instances/', api_key)
    instances = resp.json().get('instances', [])
    running = [i for i in instances if i.get('actual_status') == 'running']

    print(f"\n📋 GPUs disponíveis para benchmark: {len(running)}")
    for inst in running:
        print(f"   - {inst['id']}: {inst.get('gpu_name')}")

    # Benchmark each GPU (1 cycle each for quick comparison)
    results = []

    for inst in running[:5]:  # Limit to 5 GPUs
        instance_id = inst['id']
        gpu_name = inst.get('gpu_name', 'Unknown')

        print(f"\n{'='*70}")
        print(f"🎯 Testando: {gpu_name} (ID: {instance_id})")
        print("=" * 70)

        pause_time, resume_time = benchmark_single_cycle(instance_id, api_key)

        results.append({
            "instance_id": instance_id,
            "gpu_name": gpu_name,
            "pause_time": pause_time,
            "resume_time": resume_time,
        })

        time.sleep(3)

    # Print comparison
    print("\n" + "=" * 70)
    print("📊 COMPARAÇÃO DE LATÊNCIA")
    print("=" * 70)
    print(f"{'GPU':<20} {'Pause':>10} {'Resume':>10} {'Total':>10}")
    print("-" * 70)

    for r in sorted(results, key=lambda x: x['resume_time']):
        total = r['pause_time'] + r['resume_time']
        print(f"{r['gpu_name']:<20} {r['pause_time']:>9.1f}s {r['resume_time']:>9.1f}s {total:>9.1f}s")

    print("=" * 70)

    # Best GPU
    if results:
        best = min(results, key=lambda x: x['resume_time'])
        print(f"\n🏆 GPU mais rápida: {best['gpu_name']} ({best['resume_time']:.1f}s cold start)")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "mode": "multi_gpu_comparison",
        "results": results,
    }

    results_file = Path('/home/marcos/dumontcloud/cli/benchmark_multi_gpu.json')
    results_file.write_text(json.dumps(output, indent=2))
    print(f"\n💾 Resultados: {results_file}")


if __name__ == "__main__":
    main()
