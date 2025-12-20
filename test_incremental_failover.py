"""
Teste de Failover com Snapshot Incremental

Fluxo:
1. Provisionar GPU de teste
2. Criar arquivos de teste no workspace
3. Criar snapshot BASE
4. Modificar alguns arquivos
5. Executar failover (deve usar snapshot incremental)
6. Comparar tempos: full vs incremental
"""

import asyncio
import sys
import time
import subprocess

sys.path.insert(0, '/home/marcos/dumontcloud')

from src.services.gpu.provisioner import GPUProvisioner
from src.services.gpu.snapshot import GPUSnapshotService
from src.services.standby.failover import FailoverService


async def main():
    print("="*70)
    print(" TESTE: Failover com Snapshot Incremental")
    print("="*70)

    vast_key = 'a9df8f732d9b1b8a6bb54fd43c477824254552b0d964c58bd92b16c6f25ca3dd'

    # Services
    provisioner = GPUProvisioner(vast_key)
    snapshot_service = GPUSnapshotService(
        r2_endpoint="https://s3.us-west-004.backblazeb2.com",
        r2_bucket="dumoncloud-snapshot"
    )
    failover_service = FailoverService(vast_api_key=vast_key)

    print("\n[1/6] Provisionando GPU de teste...")
    gpu_result = await provisioner.provision_fast(
        min_gpu_ram=10000,
        max_price=1.0,
        gpus_per_round=5,
        timeout_per_round=90,
        max_rounds=1,
    )

    if not gpu_result.success:
        print(f"✗ Falha ao provisionar GPU: {gpu_result.error}")
        return

    gpu_id = gpu_result.instance_id
    ssh_host = gpu_result.ssh_host
    ssh_port = gpu_result.ssh_port

    print(f"✓ GPU provisionada: {gpu_result.gpu_name} (ID: {gpu_id})")
    print(f"  SSH: {ssh_host}:{ssh_port}")

    try:
        # Criar arquivos de teste
        print("\n[2/6] Criando arquivos de teste no workspace...")
        test_files_cmd = """
mkdir -p /workspace/test
echo "File 1 content" > /workspace/test/file1.txt
echo "File 2 content" > /workspace/test/file2.txt
echo "File 3 content" > /workspace/test/file3.txt
dd if=/dev/zero of=/workspace/test/largefile.dat bs=1M count=10 2>/dev/null
ls -lh /workspace/test/
"""
        result = subprocess.run(
            [
                "ssh", "-p", str(ssh_port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"root@{ssh_host}",
                test_files_cmd
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"✓ Arquivos criados:\n{result.stdout}")

        # Criar snapshot BASE
        print("\n[3/6] Criando snapshot BASE...")
        base_start = time.time()
        base_snapshot = snapshot_service.create_snapshot(
            instance_id=str(gpu_id),
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            workspace_path="/workspace",
            snapshot_name=f"base-{gpu_id}-{int(time.time())}",
        )
        base_time = time.time() - base_start
        print(f"✓ Snapshot BASE criado: {base_snapshot.get('snapshot_id')}")
        print(f"  Tamanho: {base_snapshot.get('size_compressed', 0) / (1024*1024):.2f} MB")
        print(f"  Tempo: {base_time:.1f}s")

        # Modificar alguns arquivos
        print("\n[4/6] Modificando arquivos (simular mudanças)...")
        modify_cmd = """
echo "Modified file 1" >> /workspace/test/file1.txt
echo "New file 4" > /workspace/test/file4.txt
rm /workspace/test/largefile.dat
ls -lh /workspace/test/
"""
        result = subprocess.run(
            [
                "ssh", "-p", str(ssh_port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"root@{ssh_host}",
                modify_cmd
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"✓ Arquivos modificados:\n{result.stdout}")

        # Executar failover (deve usar incremental)
        print("\n[5/6] Executando FAILOVER (deve usar incremental)...")
        failover_start = time.time()

        failover_result = await failover_service.execute_failover(
            gpu_instance_id=gpu_id,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            failover_id=f"incr-test-{int(time.time())}",
            workspace_path="/workspace",
            model="qwen2.5:0.5b",
            min_gpu_ram=10000,
            max_gpu_price=1.0,
        )

        failover_time = time.time() - failover_start

        print("\n" + "="*70)
        print(" RESULTADOS DO TESTE")
        print("="*70)

        if failover_result.success:
            print(f"\n✓ FAILOVER BEM-SUCEDIDO!")
            print(f"\n📊 Tempos:")
            print(f"  Snapshot BASE (full):    {base_time:6.1f}s")
            print(f"  Snapshot INCREMENTAL:    {failover_result.snapshot_creation_ms/1000:6.1f}s")

            improvement = ((base_time * 1000 - failover_result.snapshot_creation_ms) / (base_time * 1000)) * 100
            print(f"  Melhoria:                {improvement:6.1f}%")

            print(f"\n  Provisionamento GPU:     {failover_result.gpu_provisioning_ms/1000:6.1f}s")
            print(f"  Restore:                 {failover_result.restore_ms/1000:6.1f}s")
            print(f"  Inferência:              {failover_result.inference_test_ms/1000:6.1f}s")
            print(f"  {'─'*50}")
            print(f"  MTTR TOTAL:              {failover_result.total_ms/1000:6.1f}s")

            print(f"\n🎯 Nova GPU: {failover_result.new_gpu_name}")
            print(f"   SSH: {failover_result.new_ssh_host}:{failover_result.new_ssh_port}")

        else:
            print(f"\n✗ FAILOVER FALHOU: {failover_result.error}")
            print(f"   Fase que falhou: {failover_result.failed_phase}")

        print("\n" + "="*70)

    finally:
        # Cleanup - deletar GPU de teste
        print("\n[6/6] Limpando GPU de teste...")
        try:
            import requests
            requests.delete(
                f"https://console.vast.ai/api/v0/instances/{gpu_id}/",
                headers={'Authorization': f'Bearer {vast_key}'},
                timeout=10
            )
            print(f"✓ GPU {gpu_id} deletada")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
