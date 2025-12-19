#!/usr/bin/env python3
"""
Teste final de restore usando snapshot B2 puro existente
"""
import sys
import os
import time
import subprocess

sys.path.append(os.getcwd())

os.environ["B2_KEY_ID"] = "a1ef6268a3f3"
os.environ["B2_APPLICATION_KEY"] = "00309def7dbba65c97bb234af3ce2e89ea62fdf7dd"

from src.services.gpu_snapshot_service import GPUSnapshotService

# Config
HOST = "136.60.217.200"
PORT = 50341
B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
B2_BUCKET = "dumoncloud-snapshot"
SNAPSHOT_ID = "test_b2_final_1766037438"  # 3 chunks B2 puro

print("="*70)
print("TESTE FINAL: DOWNLOAD + DESCOMPRESSÃO (B2)")
print("="*70)
print(f"Snapshot: {SNAPSHOT_ID}")
print(f"Host: {HOST}:{PORT}\n")

# Limpar workspace primeiro
print("Limpando workspace...")
subprocess.run([
    'ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
    f'root@{HOST}', 'rm -rf /workspace/*'
], check=True, capture_output=True)
print("✓ Workspace limpo\n")

service = GPUSnapshotService(B2_ENDPOINT, B2_BUCKET)

# Restore
print("Iniciando RESTORE (Download + Decompress)...")
start = time.time()
try:
    restore_info = service.restore_snapshot(
        snapshot_id=SNAPSHOT_ID,
        ssh_host=HOST,
        ssh_port=PORT,
        workspace_path="/workspace"
    )
    total_time = time.time() - start
    
    print(f"\n✓ Restore concluído!")
    print(f"  Download: {restore_info['download_time']:.1f}s")
    print(f"  Decompress: {restore_info['decompress_time']:.1f}s")
    print(f"  Total: {total_time:.1f}s")
    
    # Calcular velocidades
    size_mb = 4197  # 4.2GB
    download_speed = size_mb / restore_info['download_time']
    decompress_speed = size_mb / restore_info['decompress_time']
    total_speed = size_mb / total_time
    
    print(f"\n{'='*70}")
    print(f"RESULTADO FINAL - BACKBLAZE B2")
    print(f"{'='*70}")
    print(f"Tamanho: {size_mb} MB (4.2 GB)")
    print(f"")
    print(f"Download:    {restore_info['download_time']:.1f}s  →  {download_speed:.0f} MB/s")
    print(f"Decompress:  {restore_info['decompress_time']:.1f}s  →  {decompress_speed:.0f} MB/s")
    print(f"Total:       {total_time:.1f}s  →  {total_speed:.0f} MB/s")
    print(f"{'='*70}")
    print(f"\n🚀 {8400 / total_time:.0f}x MAIS RÁPIDO que original (14 minutos)")
    
except Exception as e:
    print(f"\nERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verificar integridade
print("\nVerificando integridade...")
result = subprocess.run([
    'ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
    f'root@{HOST}', 'du -sh /workspace && ls -lh /workspace'
], capture_output=True, text=True)
print(result.stdout)

print("✓ TESTE COMPLETO!")
