#!/usr/bin/env python3
"""
Teste de Snapshot End-to-End
1. Cria snapshot compactado (simula workspace)
2. Upload para Cloudflare R2
3. Restaura e mede tempo total
"""
import os
import sys
import time
import hashlib
import json
import tempfile
import subprocess
from pathlib import Path

# Configurações R2
R2_ENDPOINT = "https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com"
R2_BUCKET = "musetalk"
R2_ACCESS_KEY = "f0a6f424064e46c903c76a447f5e73d2"
R2_SECRET_KEY = "1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5"

CHUNK_SIZE = 64 * 1024 * 1024  # 64MB

print("=" * 70)
print("TESTE DE SNAPSHOT END-TO-END")
print("RTX 4090 - Texas - 32 Gbps")
print("=" * 70)

# Instalar dependências
print("\n1. Instalando dependências...")
os.system("pip install --quiet lz4 zipnn boto3 huggingface_hub")

import lz4.frame
import zipnn
import boto3
from botocore.config import Config

# Configurar cliente S3/R2
s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

# Criar snapshot de teste (simular workspace com modelo)
print("\n2. Criando snapshot de teste (~2GB)...")
print("   Baixando modelo TinyLlama para simular workspace...")

from huggingface_hub import hf_hub_download

model_path = hf_hub_download(
    repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    filename="model.safetensors",
    cache_dir="/tmp/hf_cache"
)

with open(model_path, "rb") as f:
    model_data = f.read()

print(f"   Modelo: {len(model_data)/1024/1024:.0f} MB")

# Compactar com ZipNN (BF16)
print("\n3. Compactando com ZipNN (BF16)...")
znn = zipnn.ZipNN(bytearray_dtype="bfloat16")

start_compress = time.time()
chunks = []
chunk_info = []

for i in range(0, len(model_data), CHUNK_SIZE):
    chunk = model_data[i:i+CHUNK_SIZE]
    compressed = znn.compress(chunk)
    # Converter memoryview para bytes para compatibilidade com boto3
    if isinstance(compressed, memoryview):
        compressed = bytes(compressed)
    chunks.append(compressed)
    
    chunk_info.append({
        "index": len(chunks) - 1,
        "original_size": len(chunk),
        "compressed_size": len(compressed),
        "sha256": hashlib.sha256(chunk).hexdigest()[:16]
    })

compress_time = time.time() - start_compress
total_compressed = sum(len(c) for c in chunks)
total_original = len(model_data)

print(f"   Original: {total_original/1024/1024:.0f} MB")
print(f"   Comprimido: {total_compressed/1024/1024:.0f} MB")
print(f"   Ratio: {total_original/total_compressed:.2f}x")
print(f"   Chunks: {len(chunks)} x 64MB")
print(f"   Tempo: {compress_time:.1f}s")

# Upload para R2
print("\n4. Fazendo upload para Cloudflare R2...")
snapshot_id = f"snapshot_test_{int(time.time())}"

start_upload = time.time()

for i, chunk in enumerate(chunks):
    key = f"snapshots/{snapshot_id}/chunk_{i:03d}.znn"
    s3.put_object(Bucket=R2_BUCKET, Key=key, Body=chunk)
    print(f"   Chunk {i}/{len(chunks)} uploaded ({len(chunk)/1024/1024:.1f} MB)")

# Upload manifest
manifest = {
    "snapshot_id": snapshot_id,
    "original_size": total_original,
    "compressed_size": total_compressed,
    "num_chunks": len(chunks),
    "chunk_size": CHUNK_SIZE,
    "compression": "zipnn_bf16",
    "chunks": chunk_info
}
s3.put_object(
    Bucket=R2_BUCKET, 
    Key=f"snapshots/{snapshot_id}/manifest.json",
    Body=json.dumps(manifest, indent=2)
)

upload_time = time.time() - start_upload
upload_speed = total_compressed / upload_time / 1024 / 1024

print(f"   Upload completo: {upload_time:.1f}s ({upload_speed:.0f} MB/s)")

# Limpar dados locais
del chunks
del model_data
import gc
gc.collect()

print("\n5. Simulando restore do snapshot...")
print("   (Baixando chunks do R2 e descomprimindo)")

# Baixar manifest
manifest_obj = s3.get_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/manifest.json")
manifest = json.loads(manifest_obj['Body'].read())

print(f"   Snapshot: {manifest['snapshot_id']}")
print(f"   Tamanho original: {manifest['original_size']/1024/1024:.0f} MB")
print(f"   Tamanho comprimido: {manifest['compressed_size']/1024/1024:.0f} MB")
print(f"   Chunks: {manifest['num_chunks']}")

# Restore
start_restore = time.time()
restored_data = b""
total_downloaded = 0

znn = zipnn.ZipNN(bytearray_dtype="bfloat16")

for i in range(manifest['num_chunks']):
    key = f"snapshots/{snapshot_id}/chunk_{i:03d}.znn"
    
    # Download
    t0 = time.time()
    obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
    compressed = obj['Body'].read()
    download_time = time.time() - t0
    total_downloaded += len(compressed)
    
    # Decompress
    t1 = time.time()
    decompressed = znn.decompress(compressed)
    decompress_time = time.time() - t1
    
    restored_data += decompressed
    
    download_speed = len(compressed) / download_time / 1024 / 1024
    decompress_speed = len(decompressed) / decompress_time / 1024 / 1024
    
    print(f"   Chunk {i}: Download {download_speed:.0f} MB/s, Decompress {decompress_speed:.0f} MB/s")

restore_time = time.time() - start_restore

# Verificar integridade
print("\n6. Verificando integridade...")
original_path = hf_hub_download(
    repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    filename="model.safetensors",
    cache_dir="/tmp/hf_cache"
)
with open(original_path, "rb") as f:
    original_hash = hashlib.sha256(f.read()).hexdigest()

restored_hash = hashlib.sha256(restored_data).hexdigest()
integrity_ok = original_hash == restored_hash

print(f"   Original SHA256:  {original_hash[:32]}...")
print(f"   Restaurado SHA256: {restored_hash[:32]}...")
print(f"   Integridade: {'✓ OK' if integrity_ok else '✗ FALHA'}")

# Limpar snapshots do R2
print("\n7. Limpando snapshot do R2...")
for i in range(manifest['num_chunks']):
    s3.delete_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/chunk_{i:03d}.znn")
s3.delete_object(Bucket=R2_BUCKET, Key=f"snapshots/{snapshot_id}/manifest.json")
print("   Snapshot removido")

# Resultados finais
print("\n" + "=" * 70)
print("RESULTADOS FINAIS")
print("=" * 70)
print(f"\nTamanho do workspace: {total_original/1024/1024:.0f} MB")
print(f"Tamanho comprimido:   {total_compressed/1024/1024:.0f} MB ({total_original/total_compressed:.2f}x)")
print()
print("Tempos:")
print(f"  Compressão:         {compress_time:.1f}s ({total_original/compress_time/1024/1024:.0f} MB/s)")
print(f"  Upload (R2):        {upload_time:.1f}s ({total_compressed/upload_time/1024/1024:.0f} MB/s)")
print(f"  Download + Restore: {restore_time:.1f}s ({total_original/restore_time/1024/1024:.0f} MB/s)")
print()
print(f"TEMPO TOTAL RESTORE:  {restore_time:.1f} segundos")
print()
print("=" * 70)
