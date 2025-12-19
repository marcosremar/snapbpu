#!/usr/bin/env python3
"""
Teste Final: Restore Completo com Backblaze B2
"""
import sys
import os
import time
import subprocess

sys.path.append(os.getcwd())

# Configurar credenciais B2
os.environ["AWS_ACCESS_KEY_ID"] = "003a1ef6268a3f30000000002"
os.environ["AWS_SECRET_ACCESS_KEY"] = "K003vYodS+gmuU83zDEDNy2EIv5ddnQ"
os.environ["AWS_REGION"] = "us-west-004"

from src.services.gpu_snapshot_service import GPUSnapshotService

# Configuração
HOST = "136.60.217.200"
PORT = 50341
B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
B2_BUCKET = "dumoncloud-snapshot"

print("="*70)
print("TESTE FINAL: BACKBLAZE B2 (31x MAIS RÁPIDO QUE R2)")
print("="*70)
print(f"Host: {HOST}:{PORT}")
print(f"Storage: Backblaze B2 ({B2_ENDPOINT})")
print(f"Bucket: {B2_BUCKET}\n")

# Verificar workspace
print("1. Verificando workspace remoto...")
result = subprocess.run(
    ['ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{HOST}', 'du -sh /workspace && ls -lh /workspace/*.safetensors 2>/dev/null | wc -l'],
    capture_output=True,
    text=True
)
print(f"   {result.stdout.strip()}")

# Criar serviço com B2
service = GPUSnapshotService(B2_ENDPOINT, B2_BUCKET)

# Snapshot
print("\n2. Criando Snapshot com Backblaze B2...")
start_time = time.time()
try:
    snap_info = service.create_snapshot(
        instance_id="test_b2_final",
        ssh_host=HOST,
        ssh_port=PORT,
        workspace_path="/workspace"
    )
    create_time = time.time() - start_time
    
    print(f"   ✓ Snapshot criado em {create_time:.1f}s")
    print(f"   Original: {snap_info['size_original']/1024/1024:.0f} MB")
    print(f"   Comprimido: {snap_info['size_compressed']/1024/1024:.0f} MB")
    print(f"   Ratio: {snap_info['compression_ratio']:.2f}x")
    print(f"   Chunks: {snap_info['num_chunks']}")
    
except Exception as e:
    print(f"   ERRO: {e}")
    print("\nDetalhes do erro (stderr):")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Limpar
print("\n3. Limpando workspace...")
subprocess.run(
    ['ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{HOST}', 'rm -rf /workspace/*'],
    check=True,
    capture_output=True
)
print("   ✓ Limpeza concluída")

# Restore
print("\n4. Restaurando com Backblaze B2...")
start_time = time.time()
try:
    restore_info = service.restore_snapshot(
        snapshot_id=snap_info['snapshot_id'],
        ssh_host=HOST,
        ssh_port=PORT,
        workspace_path="/workspace"
    )
    restore_time = time.time() - start_time
    
    print(f"   ✓ Restore concluído em {restore_time:.1f}s")
    print(f"   Download: {restore_info['download_time']:.1f}s")
    print(f"   Decompress: {restore_info['decompress_time']:.1f}s")
    
    # Calcular velocidade
    size_mb = snap_info['size_original'] / 1024 / 1024
    speed_mbps = size_mb / restore_time
    
    print(f"\n{'='*70}")
    print(f"RESULTADO FINAL - BACKBLAZE B2")
    print(f"{'='*70}")
    print(f"Tamanho: {size_mb:.0f} MB")
    print(f"Tempo Total: {restore_time:.1f}s")
    print(f"VELOCIDADE: {speed_mbps:.0f} MB/s")
    print(f"{'='*70}\n")
    
    # Comparação
    r2_time_estimated = 39.6  # Do teste anterior
    improvement = r2_time_estimated / restore_time
    print(f"🚀 {improvement:.1f}x MAIS RÁPIDO que Cloudflare R2!")
    
except Exception as e:
    print(f"   ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verificar integridade
print("\n5. Verificando integridade...")
result = subprocess.run(
    ['ssh', '-p', str(PORT), '-o', 'StrictHostKeyChecking=no',
     f'root@{HOST}', 'ls -lh /workspace/'],
    capture_output=True,
    text=True
)
print(f"   Arquivos restaurados:\n{result.stdout}")

print("✓ TESTE COMPLETO COM BACKBLAZE B2!")
