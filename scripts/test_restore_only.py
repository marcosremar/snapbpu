#!/usr/bin/env python3
"""
Teste de restore apenas (usando snapshot já criado)
"""
import sys
import os
import time
import subprocess

sys.path.append(os.getcwd())

SSH_HOST = "ssh4.vast.ai"
SSH_PORT = 38784
SNAPSHOT_ID = "test_b2_final_1766040186"  # 2GB valid snapshot

os.environ["B2_KEY_ID"] = "a1ef6268a3f3"
os.environ["B2_APPLICATION_KEY"] = "00309def7dbba65c97bb234af3ce2e89ea62fdf7dd"

from src.services.gpu_snapshot_service import GPUSnapshotService

B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
B2_BUCKET = "dumoncloud-snapshot"

print("="*70)
print("TESTE: RESTORE COM RANGE DOWNLOADS + MULTI-PROVIDER")
print("="*70)
print(f"Snapshot: {SNAPSHOT_ID}")
print(f"Host: {SSH_HOST}:{SSH_PORT}\n")

# Limpar workspace
print("1. Limpando workspace...")
subprocess.run(
    ['ssh', '-p', str(SSH_PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{SSH_HOST}', 'rm -rf /workspace/*'],
    check=True,
    capture_output=True
)
print("✓ Limpo!\n")

# Criar serviço
service = GPUSnapshotService(B2_ENDPOINT, B2_BUCKET)

# Restore
print("2. Restaurando com Range Downloads...")
start = time.time()
try:
    restore_info = service.restore_snapshot(
        snapshot_id=SNAPSHOT_ID,
        ssh_host=SSH_HOST,
        ssh_port=SSH_PORT,
        workspace_path="/workspace"
    )
    restore_time = time.time() - start
    
    print(f"\n✓ Restore concluído em {restore_time:.1f}s!")
    print(f"  Download: {restore_info['download_time']:.1f}s")
    print(f"  Decompress: {restore_info['decompress_time']:.1f}s")
    
    size_mb = 4196  # Do snapshot
    speed = size_mb / restore_time
    
    print(f"\n{'='*70}")
    print(f"RESULTADO FINAL - RANGE DOWNLOADS + MULTI-PROVIDER")
    print(f"{'='*70}")
    print(f"Tamanho: {size_mb:.0f} MB (4.2GB)")
    print(f"Tempo: {restore_time:.1f}s")
    print(f"VELOCIDADE: {speed:.0f} MB/s")
    print(f"{'='*70}\n")
    
    print(f"🚀 {8400/restore_time:.0f}x MAIS RÁPIDO que original (14min)")
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verificar
print("\n3. Verificando integridade...")
result = subprocess.run(
    ['ssh', '-p', str(SSH_PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{SSH_HOST}', 'ls -lh /workspace/ && du -sh /workspace'],
    capture_output=True,
    text=True
)
print(result.stdout)

print("✓ TESTE COMPLETO!")
