#!/usr/bin/env python3
"""
Test restore multi-provider usando snapshot existente
"""
import sys
import os
import time

sys.path.append(os.getcwd())

os.environ["B2_KEY_ID"] = "a1ef6268a3f3"
os.environ["B2_APPLICATION_KEY"] = "00309def7dbba65c97bb234af3ce2e89ea62fdf7dd"

from src.services.gpu_snapshot_service import GPUSnapshotService

# Config
HOST = "136.60.217.200"
PORT = 50341
B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
B2_BUCKET = "dumoncloud-snapshot"
SNAPSHOT_ID = "test_b2_final_1766034438"  # 133 chunks multi-provider

print("="*70)
print("TESTE RESTORE MULTI-PROVIDER (B2 + R2)")
print("="*70)
print(f"Snapshot: {SNAPSHOT_ID}")
print(f"Host: {HOST}:{PORT}\n")

service = GPUSnapshotService(B2_ENDPOINT, B2_BUCKET)

# Restore
print("Restaurando com MULTI-PROVIDER (B2 + R2)...")
start = time.time()
try:
    restore_info = service.restore_snapshot(
        snapshot_id=SNAPSHOT_ID,
        ssh_host=HOST,
        ssh_port=PORT,
        workspace_path="/workspace"
    )
    total_time = time.time() - start
    
    print(f"\n✓ Restore concluído em {total_time:.1f}s")
    print(f"  Download time: {restore_info['download_time']:.1f}s")
    print(f"  Decompress time: {restore_info['decompress_time']:.1f}s")
    
    # Estimate size (4.2GB)
    size_mb = 4197
    speed = size_mb / total_time
    
    print(f"\n{'='*70}")
    print(f"RESULTADO - MULTI-PROVIDER (B2 + R2)")
    print(f"{'='*70}")
    print(f"Tamanho: {size_mb} MB")
    print(f"Tempo: {total_time:.1f}s")
    print(f"VELOCIDADE: {speed:.0f} MB/s")
    print(f"{'='*70}")
    
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ TESTE MULTI-PROVIDER COMPLETO!")
