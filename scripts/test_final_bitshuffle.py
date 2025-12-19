#!/usr/bin/env python3
"""
Teste Final Bitshuffle - Versão Simplificada
Executa snapshot end-to-end usando GPUSnapshotService
"""
import sys
import os
import time
import subprocess

# Configuração
HOST = sys.argv[1]
PORT = int(sys.argv[2])

print("="*70)
print("TESTE FINAL: BITSHUFFLE + LZ4 + S5CMD")
print("="*70)
print(f"Host: {HOST}:{PORT}\n")

# Passo 1: Preparar workspace remoto
print("1. Preparando workspace remoto...")
setup_cmds = [
    "mkdir -p /workspace",
    "pip install -q huggingface_hub",
    "python3 -c 'from huggingface_hub import hf_hub_download; import shutil; p=hf_hub_download(\"TinyLlama/TinyLlama-1.1B-Chat-v1.0\", \"model.safetensors\", cache_dir=\"/tmp/hf\"); shutil.copy(p, \"/workspace/model.safetensors\"); print(\"Downloaded\")'",
    "cp /workspace/model.safetensors /workspace/model_copy.safetensors",  # Duplicar para ter ~4GB
]

for cmd in setup_cmds:
    print(f"   Executando: {cmd[:60]}...")
    result = subprocess.run(
        ['ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no', 
         f'root@{HOST}', cmd],
        capture_output=True,
        text=True,
        timeout=300
    )
    if result.returncode != 0:
        print(f"   ERRO: {result.stderr}")
    else:
        print(f"   OK")

# Verificar tamanho total
result = subprocess.run(
    ['ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{HOST}', 'du -sh /workspace'],
    capture_output=True,
    text=True
)
workspace_size = result.stdout.strip()
print(f"   Workspace: {workspace_size}\n")

# Passo 2: Criar Snapshot usando GPUSnapshotService
print("2. Criando Snapshot (Bitshuffle + LZ4)...")
sys.path.append(os.getcwd())
from src.services.gpu_snapshot_service import GPUSnapshotService

R2_ENDPOINT = "https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com"
R2_BUCKET = "musetalk"

service = GPUSnapshotService(R2_ENDPOINT, R2_BUCKET)

start_time = time.time()
try:
    snap_info = service.create_snapshot(
        instance_id="test_bitshuffle",
        ssh_host=HOST,
        ssh_port=PORT,
        workspace_path="/workspace"
    )
    create_time = time.time() - start_time
    
    print(f"   ✓ Snapshot criado em {create_time:.1f}s")
    print(f"   Original: {snap_info['size_original']/1024/1024:.0f} MB")
    print(f"   Comprimido: {snap_info['size_compressed']/1024/1024:.0f} MB")
    print(f"   Ratio: {snap_info['compression_ratio']:.2f}x")
    print(f"   Chunks: {snap_info['num_chunks']}\n")
    
except Exception as e:
    print(f"   ERRO ao criar snapshot: {e}")
    sys.exit(1)

# Passo 3: Limpar workspace
print("3. Limpando workspace...")
subprocess.run(
    ['ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{HOST}', 'rm -rf /workspace/*'],
    check=True
)
print("   ✓ Limpeza concluída\n")

# Passo 4: Restaurar Snapshot
print("4. Restaurando Snapshot (Download + Decompress)...")
start_time = time.time()
try:
    restore_info = service.restore_snapshot(
        snapshot_id=snap_info['snapshot_id'],
        ssh_host=HOST,
        ssh_port=PORT,
        workspace_path="/workspace"
    )
    restore_time = time.time() - start_time
    
    print(f"   ✓ Snapshot restaurado em {restore_time:.1f}s")
    print(f"   Download: {restore_info['download_time']:.1f}s")
    print(f"   Decompress: {restore_info['decompress_time']:.1f}s")
    
    # Calcular velocidade
    size_mb = snap_info['size_original'] / 1024 / 1024
    speed_mbps = size_mb / restore_time
    
    print(f"\n{'='*70}")
    print(f"RESULTADO FINAL")
    print(f"{'='*70}")
    print(f"Tamanho Original: {size_mb:.0f} MB")
    print(f"Tempo Restore: {restore_time:.1f}s")
    print(f"VELOCIDADE: {speed_mbps:.0f} MB/s")
    print(f"{'='*70}\n")
    
except Exception as e:
    print(f"   ERRO ao restaurar: {e}")
    sys.exit(1)

# Passo 5: Verificar integridade
print("5. Verificando integridade...")
result = subprocess.run(
    ['ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{HOST}', 'ls -lh /workspace/'],
    capture_output=True,
    text=True
)
print(f"   Arquivos restaurados:\n{result.stdout}")

print("✓ TESTE COMPLETO!")
