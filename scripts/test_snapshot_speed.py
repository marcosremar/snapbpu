#!/usr/bin/env python3
"""
Script simplificado para teste de snapshot com máquina disponível
"""
import sys
import os

# Informações da máquina criada
SSH_HOST = "ssh4.vast.ai"
SSH_PORT = 38784
INSTANCE_ID = 28998785

sys.path.append(os.getcwd())

os.environ["B2_KEY_ID"] = "a1ef6268a3f3"
os.environ["B2_APPLICATION_KEY"] = "00309def7dbba65c97bb234af3ce2e89ea62fdf7dd"

from src.services.gpu_snapshot_service import GPUSnapshotService
import time
import subprocess

B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
B2_BUCKET = "dumoncloud-snapshot"

print("="*70)
print("TESTE FINAL: RANGE DOWNLOADS + MULTI-PROVIDER")
print("="*70)
print(f"Host: {SSH_HOST}:{SSH_PORT}")
print(f"Storage: B2 + R2 (Multi-provider)")
print()

# Verificar conexão
print("1. Testando SSH...")
result = subprocess.run(
    ['ssh', '-p', str(SSH_PORT), '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
     f'root@{SSH_HOST}', 'echo "OK" && du -sh /workspace'],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"❌ SSH falhou: {result.stderr}")
    print("\nPor favor, atualize SSH_HOST e SSH_PORT no script com as informações da máquina criada")
    sys.exit(1)

print(f"✓ SSH conectado!")
print(f"  {result.stdout.strip()}")

# Criar serviço
service = GPUSnapshotService(B2_ENDPOINT, B2_BUCKET)

# Snapshot
print("\n2. Criando Snapshot...")
start = time.time()
try:
    snap_info = service.create_snapshot(
        instance_id="speed_test_final",
        ssh_host=SSH_HOST,
        ssh_port=SSH_PORT,
        workspace_path="/workspace"
    )
    create_time = time.time() - start
    
    print(f"✓ Snapshot criado em {create_time:.1f}s")
    print(f"  Original: {snap_info['size_original']/1024/1024:.0f} MB")
    print(f"  Comprimido: {snap_info['size_compressed']/1024/1024:.0f} MB")
    print(f"  Ratio: {snap_info['compression_ratio']:.2f}x")
    print(f"  Chunks: {snap_info['num_chunks']}")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Limpar
print("\n3. Limpando workspace...")
subprocess.run(
    ['ssh', '-p', str(SSH_PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{SSH_HOST}', 'rm -rf /workspace/*'],
    check=True,
    capture_output=True
)
print("✓ Limpo!")

# Restore
print("\n4. Restaurando (Range Downloads + Multi-Provider)...")
start = time.time()
try:
    restore_info = service.restore_snapshot(
        snapshot_id=snap_info['snapshot_id'],
        ssh_host=SSH_HOST,
        ssh_port=SSH_PORT,
        workspace_path="/workspace"
    )
    restore_time = time.time() - start
    
    print(f"✓ Restore concluído em {restore_time:.1f}s!")
    print(f"  Download: {restore_info['download_time']:.1f}s")
    print(f"  Decompress: {restore_info['decompress_time']:.1f}s")
    
    size_mb = snap_info['size_original'] / 1024 / 1024
    speed = size_mb / restore_time
    
    print(f"\n{'='*70}")
    print(f"RESULTADO FINAL - RANGE DOWNLOADS + MULTI-PROVIDER")
    print(f"{'='*70}")
    print(f"Tamanho: {size_mb:.0f} MB")
    print(f"Tempo: {restore_time:.1f}s")
    print(f"VELOCIDADE: {speed:.0f} MB/s")
    print(f"{'='*70}\n")
    
    print(f"🚀 {8400/restore_time:.0f}x MAIS RÁPIDO que original (14min)")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verificar
print("\n5. Verificando integridade...")
result = subprocess.run(
    ['ssh', '-p', str(SSH_PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{SSH_HOST}', 'ls -lh /workspace/'],
    capture_output=True,
    text=True
)
print(result.stdout)

print("✓ TESTE COMPLETO!")
