#!/usr/bin/env python3
"""
Teste de compressão com LLaMA-7B
Benchmarks: ZipNN (BF16) vs LZ4 com chunks de 64MB
"""
import os
import time
import hashlib
import lz4.frame
import zipnn
from huggingface_hub import hf_hub_download

CHUNK_SIZE = 64 * 1024 * 1024  # 64MB

print("=" * 70)
print("BENCHMARK LLaMA-7B - Compressão ZipNN (IBM) vs LZ4")
print("RTX A4000 (16GB) - Czechia - Chunks de 64MB")
print("=" * 70)

# Baixar modelo LLaMA-7B (ou usar Mistral-7B que é mais rápido de baixar)
print("\nBaixando modelo Mistral-7B-v0.1 (similar ao LLaMA-7B em tamanho)...")
print("Este é um modelo BF16 real de ~14GB")

try:
    model_path = hf_hub_download(
        repo_id="mistralai/Mistral-7B-v0.1",
        filename="model-00001-of-00002.safetensors",
        cache_dir="/tmp/hf_cache"
    )
    print(f"Arquivo 1/2: {os.path.getsize(model_path)/1024/1024/1024:.2f} GB")
except Exception as e:
    print(f"Erro ao baixar Mistral: {e}")
    print("Tentando TinyLlama (menor)...")
    model_path = hf_hub_download(
        repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        filename="model.safetensors",
        cache_dir="/tmp/hf_cache"
    )
    print(f"TinyLlama: {os.path.getsize(model_path)/1024/1024:.0f} MB")

# Ler arquivo
print("\nLendo arquivo do modelo...")
with open(model_path, "rb") as f:
    model_data = f.read()

file_size = len(model_data)
print(f"Tamanho total: {file_size/1024/1024/1024:.2f} GB")

# Calcular hash original
original_hash = hashlib.sha256(model_data).hexdigest()
print(f"SHA256 original: {original_hash[:16]}...")

# Dividir em chunks de 64MB
num_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
print(f"Chunks de 64MB: {num_chunks}")
print("-" * 70)

# Testar compressores
znn_bf16 = zipnn.ZipNN(bytearray_dtype="bfloat16")

results = {
    "lz4": {"compressed": 0, "compress_time": 0, "decompress_time": 0},
    "zipnn": {"compressed": 0, "compress_time": 0, "decompress_time": 0},
}

print("\nProcessando chunks:")
for i in range(0, file_size, CHUNK_SIZE):
    chunk = model_data[i:i+CHUNK_SIZE]
    chunk_num = i // CHUNK_SIZE
    
    # LZ4
    start = time.time()
    compressed_lz4 = lz4.frame.compress(chunk)
    results["lz4"]["compress_time"] += time.time() - start
    results["lz4"]["compressed"] += len(compressed_lz4)
    
    start = time.time()
    _ = lz4.frame.decompress(compressed_lz4)
    results["lz4"]["decompress_time"] += time.time() - start
    
    # ZipNN BF16
    start = time.time()
    compressed_zipnn = znn_bf16.compress(chunk)
    results["zipnn"]["compress_time"] += time.time() - start
    results["zipnn"]["compressed"] += len(compressed_zipnn)
    
    start = time.time()
    _ = znn_bf16.decompress(compressed_zipnn)
    results["zipnn"]["decompress_time"] += time.time() - start
    
    # Progress
    ratio_lz4 = len(chunk) / len(compressed_lz4)
    ratio_zipnn = len(chunk) / len(compressed_zipnn)
    print(f"  Chunk {chunk_num:2d}/{num_chunks}: LZ4={ratio_lz4:.2f}x, ZipNN={ratio_zipnn:.2f}x ({len(chunk)/1024/1024:.0f}MB)")

# Verificar integridade
print("\n" + "-" * 70)
print("Verificando integridade (descomprimir e verificar SHA256)...")

# Reconstruir com ZipNN
reconstructed = b""
for i in range(0, file_size, CHUNK_SIZE):
    chunk = model_data[i:i+CHUNK_SIZE]
    compressed = znn_bf16.compress(chunk)
    decompressed = znn_bf16.decompress(compressed)
    reconstructed += decompressed

reconstructed_hash = hashlib.sha256(reconstructed).hexdigest()
integrity_ok = original_hash == reconstructed_hash

print(f"SHA256 reconstruído: {reconstructed_hash[:16]}...")
print(f"Integridade: {'✓ OK' if integrity_ok else '✗ FALHA'}")

# Resultados finais
print("\n" + "=" * 70)
print("RESULTADOS FINAIS")
print("=" * 70)

for name, r in results.items():
    ratio = file_size / r["compressed"]
    savings = (1 - r["compressed"] / file_size) * 100
    compress_speed = (file_size / 1024 / 1024) / r["compress_time"]
    decompress_speed = (file_size / 1024 / 1024) / r["decompress_time"]
    
    print(f"\n{name.upper()}:")
    print(f"  Original:    {file_size/1024/1024/1024:.2f} GB")
    print(f"  Comprimido:  {r['compressed']/1024/1024/1024:.2f} GB")
    print(f"  Ratio:       {ratio:.2f}x")
    print(f"  Economia:    {savings:.1f}%")
    print(f"  Compress:    {compress_speed:.0f} MB/s ({r['compress_time']:.1f}s)")
    print(f"  Decompress:  {decompress_speed:.0f} MB/s ({r['decompress_time']:.1f}s)")

print("\n" + "=" * 70)
print("CONCLUSÃO:")
print(f"  ZipNN (IBM) é {results['zipnn']['compressed']/results['lz4']['compressed']*100:.0f}% do tamanho do LZ4")
print(f"  Economia adicional: {(1-results['zipnn']['compressed']/file_size)*100:.1f}%")
print("=" * 70)
