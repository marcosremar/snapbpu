#!/usr/bin/env python3
"""
Teste de Snapshot OTIMIZADO
- Downloads paralelos (8-16 threads)
- Pipeline: Download + Decompress simultâneo
- nvCOMP GPU para LZ4 (quando disponível)
"""
import os
import sys
import time
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import tempfile

# Configurações R2
R2_ENDPOINT = "https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com"
R2_BUCKET = "musetalk"
R2_ACCESS_KEY = "f0a6f424064e46c903c76a447f5e73d2"
R2_SECRET_KEY = "1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5"

CHUNK_SIZE = 64 * 1024 * 1024  # 64MB
NUM_DOWNLOAD_THREADS = 16  # Downloads paralelos

print("=" * 70)
print("TESTE DE SNAPSHOT OTIMIZADO")
print("Downloads Paralelos + Pipeline")
print("=" * 70)

# Instalar dependências
print("\n1. Instalando dependências...")
os.system("pip install --quiet lz4 zipnn boto3 huggingface_hub aiohttp")

import lz4.frame
import zipnn
import boto3
from botocore.config import Config

# Configurar cliente S3/R2 com pool de conexões maior
s3_config = Config(
    signature_version='s3v4',
    max_pool_connections=50,
    retries={'max_attempts': 3}
)

s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=s3_config
)

# Verificar GPU e nvCOMP
print("\n2. Verificando GPU...")
try:
    import subprocess
    result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                          capture_output=True, text=True)
    gpu_name = result.stdout.strip()
    print(f"   GPU: {gpu_name}")
except:
    gpu_name = "Unknown"

# Tentar carregar nvCOMP para descompressão GPU
HAS_NVCOMP = False
try:
    # nvCOMP pode estar disponível via diferentes pacotes
    import kvikio
    HAS_NVCOMP = True
    print("   nvCOMP: Disponível via kvikio")
except ImportError:
    try:
        from nvidia import nvcomp
        HAS_NVCOMP = True
        print("   nvCOMP: Disponível via nvidia-nvcomp")
    except ImportError:
        print("   nvCOMP: Não disponível (usando CPU)")

# Baixar modelo para teste
print("\n3. Preparando dados de teste...")
from huggingface_hub import hf_hub_download

model_path = hf_hub_download(
    repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    filename="model.safetensors",
    cache_dir="/tmp/hf_cache"
)

with open(model_path, "rb") as f:
    model_data = f.read()

print(f"   Modelo: {len(model_data)/1024/1024:.0f} MB")

# Compactar e fazer upload
print("\n4. Compactando e fazendo upload para R2...")
znn = zipnn.ZipNN(bytearray_dtype="bfloat16")

chunks = []
for i in range(0, len(model_data), CHUNK_SIZE):
    chunk = model_data[i:i+CHUNK_SIZE]
    compressed = znn.compress(chunk)
    if isinstance(compressed, memoryview):
        compressed = bytes(compressed)
    chunks.append(compressed)

total_original = len(model_data)
total_compressed = sum(len(c) for c in chunks)
print(f"   Original: {total_original/1024/1024:.0f} MB")
print(f"   Comprimido: {total_compressed/1024/1024:.0f} MB ({total_original/total_compressed:.2f}x)")

snapshot_id = f"snapshot_parallel_{int(time.time())}"

# Upload paralelo
def upload_chunk(args):
    idx, chunk = args
    key = f"snapshots/{snapshot_id}/chunk_{idx:03d}.znn"
    s3.put_object(Bucket=R2_BUCKET, Key=key, Body=chunk)
    return idx, len(chunk)

print(f"\n   Fazendo upload ({NUM_DOWNLOAD_THREADS} threads)...")
start_upload = time.time()

with ThreadPoolExecutor(max_workers=NUM_DOWNLOAD_THREADS) as executor:
    futures = [executor.submit(upload_chunk, (i, c)) for i, c in enumerate(chunks)]
    for f in as_completed(futures):
        idx, size = f.result()

# Upload manifest
manifest = {
    "snapshot_id": snapshot_id,
    "original_size": total_original,
    "compressed_size": total_compressed,
    "num_chunks": len(chunks),
    "compression": "zipnn_bf16"
}
s3.put_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/manifest.json",
              Body=json.dumps(manifest))

upload_time = time.time() - start_upload
print(f"   Upload: {upload_time:.1f}s ({total_compressed/upload_time/1024/1024:.0f} MB/s)")

# Limpar dados locais
del chunks
del model_data
import gc
gc.collect()

# ============ TESTE 1: Download Sequencial (baseline) ============
print("\n" + "=" * 70)
print("TESTE 1: Download SEQUENCIAL (baseline)")
print("=" * 70)

manifest_obj = s3.get_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/manifest.json")
manifest = json.loads(manifest_obj['Body'].read())

znn = zipnn.ZipNN(bytearray_dtype="bfloat16")

start_seq = time.time()
restored_seq = b""

for i in range(manifest['num_chunks']):
    obj = s3.get_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/chunk_{i:03d}.znn")
    compressed = obj['Body'].read()
    decompressed = znn.decompress(compressed)
    restored_seq += decompressed

time_seq = time.time() - start_seq
print(f"   Tempo: {time_seq:.1f}s ({total_original/time_seq/1024/1024:.0f} MB/s)")

# ============ TESTE 2: Download Paralelo ============
print("\n" + "=" * 70)
print(f"TESTE 2: Download PARALELO ({NUM_DOWNLOAD_THREADS} threads)")
print("=" * 70)

# Download todos os chunks em paralelo
def download_chunk(idx):
    key = f"snapshots/{snapshot_id}/chunk_{idx:03d}.znn"
    obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
    return idx, obj['Body'].read()

start_parallel = time.time()

# Download paralelo
downloaded_chunks = {}
with ThreadPoolExecutor(max_workers=NUM_DOWNLOAD_THREADS) as executor:
    futures = {executor.submit(download_chunk, i): i for i in range(manifest['num_chunks'])}
    for future in as_completed(futures):
        idx, data = future.result()
        downloaded_chunks[idx] = data

download_time = time.time() - start_parallel

# Descompressão (sequencial para garantir ordem)
start_decompress = time.time()
znn = zipnn.ZipNN(bytearray_dtype="bfloat16")
restored_parallel = b""
for i in range(manifest['num_chunks']):
    decompressed = znn.decompress(downloaded_chunks[i])
    restored_parallel += decompressed

decompress_time = time.time() - start_decompress
total_parallel = time.time() - start_parallel

print(f"   Download: {download_time:.1f}s ({total_compressed/download_time/1024/1024:.0f} MB/s)")
print(f"   Decompress: {decompress_time:.1f}s ({total_original/decompress_time/1024/1024:.0f} MB/s)")
print(f"   Total: {total_parallel:.1f}s ({total_original/total_parallel/1024/1024:.0f} MB/s)")

# ============ TESTE 3: Download Paralelo + Pipeline ============
print("\n" + "=" * 70)
print(f"TESTE 3: Download PARALELO + PIPELINE (download + decompress simultâneo)")
print("=" * 70)

# Pipeline: Descomprime enquanto baixa
start_pipeline = time.time()

# Fila para chunks baixados
chunk_queue = Queue()
decompressed_chunks = {}
decompress_done = threading.Event()

def download_worker():
    """Worker de download"""
    with ThreadPoolExecutor(max_workers=NUM_DOWNLOAD_THREADS) as executor:
        futures = {executor.submit(download_chunk, i): i for i in range(manifest['num_chunks'])}
        for future in as_completed(futures):
            idx, data = future.result()
            chunk_queue.put((idx, data))
    chunk_queue.put(None)  # Sinaliza fim

def decompress_worker():
    """Worker de descompressão"""
    znn_worker = zipnn.ZipNN(bytearray_dtype="bfloat16")
    while True:
        item = chunk_queue.get()
        if item is None:
            break
        idx, compressed = item
        decompressed_chunks[idx] = znn_worker.decompress(compressed)
    decompress_done.set()

# Executar em paralelo
download_thread = threading.Thread(target=download_worker)
decompress_thread = threading.Thread(target=decompress_worker)

download_thread.start()
decompress_thread.start()

download_thread.join()
decompress_thread.join()

# Reconstruir
restored_pipeline = b""
for i in range(manifest['num_chunks']):
    restored_pipeline += decompressed_chunks[i]

time_pipeline = time.time() - start_pipeline
print(f"   Tempo total: {time_pipeline:.1f}s ({total_original/time_pipeline/1024/1024:.0f} MB/s)")

# Verificar integridade
print("\n5. Verificando integridade...")
original_path = hf_hub_download(
    repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    filename="model.safetensors",
    cache_dir="/tmp/hf_cache"
)
with open(original_path, "rb") as f:
    original_hash = hashlib.sha256(f.read()).hexdigest()

hash_seq = hashlib.sha256(restored_seq).hexdigest()
hash_parallel = hashlib.sha256(restored_parallel).hexdigest()
hash_pipeline = hashlib.sha256(restored_pipeline).hexdigest()

print(f"   Sequencial: {'✓' if hash_seq == original_hash else '✗'}")
print(f"   Paralelo:   {'✓' if hash_parallel == original_hash else '✗'}")
print(f"   Pipeline:   {'✓' if hash_pipeline == original_hash else '✗'}")

# Limpar
print("\n6. Limpando...")
for i in range(manifest['num_chunks']):
    s3.delete_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/chunk_{i:03d}.znn")
s3.delete_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/manifest.json")

# Resultados
print("\n" + "=" * 70)
print("COMPARAÇÃO DE PERFORMANCE")
print("=" * 70)
print(f"\nTamanho: {total_original/1024/1024:.0f} MB (comprimido: {total_compressed/1024/1024:.0f} MB)")
print()
print(f"{'Método':<30} {'Tempo':>10} {'Velocidade':>15} {'Speedup':>10}")
print("-" * 70)
print(f"{'Sequencial (baseline)':<30} {time_seq:>8.1f}s {total_original/time_seq/1024/1024:>12.0f} MB/s {1.0:>9.1f}x")
print(f"{'Paralelo (16 threads)':<30} {total_parallel:>8.1f}s {total_original/total_parallel/1024/1024:>12.0f} MB/s {time_seq/total_parallel:>9.1f}x")
print(f"{'Pipeline (download+decomp)':<30} {time_pipeline:>8.1f}s {total_original/time_pipeline/1024/1024:>12.0f} MB/s {time_seq/time_pipeline:>9.1f}x")
print()
print("=" * 70)
