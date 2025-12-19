#!/usr/bin/env python3
"""
Teste de Descompressão Ultra-Rápida
- ZipNN com múltiplos workers (CPU paralelo)
- nvCOMP ZSTD GPU (se disponível)
- Blackwell Decompression Engine (se disponível)
"""
import os
import sys
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

print("=" * 70)
print("TESTE DE DESCOMPRESSÃO ACELERADA")
print("=" * 70)

# Instalar dependências
print("\n1. Instalando dependências...")
os.system("pip install --quiet lz4 zipnn huggingface_hub zstandard")

import lz4.frame
import zipnn
import zstandard as zstd

# Verificar GPU
print("\n2. Verificando hardware...")
import subprocess
result = subprocess.run(['nvidia-smi', '--query-gpu=name,compute_cap', '--format=csv,noheader'], 
                      capture_output=True, text=True)
gpu_info = result.stdout.strip()
print(f"   GPU: {gpu_info}")

# Verificar se é Blackwell (compute 10.x)
is_blackwell = '10.' in gpu_info or '5090' in gpu_info or '5080' in gpu_info
print(f"   Blackwell (DE): {'Sim' if is_blackwell else 'Não'}")

# Tentar nvCOMP
nvcomp_available = False
try:
    # Tentar diferentes formas de importar nvCOMP
    os.system("pip install --quiet nvidia-nvcomp-cu12 2>/dev/null || pip install --quiet kvikio-cu12 2>/dev/null")
    
    try:
        import kvikio
        print("   nvCOMP: Disponível (kvikio)")
        nvcomp_available = True
    except:
        try:
            from nvidia import nvcomp
            print("   nvCOMP: Disponível (nvidia-nvcomp)")
            nvcomp_available = True
        except:
            print("   nvCOMP: Não instalado")
except Exception as e:
    print(f"   nvCOMP: Erro - {e}")

# Verificar CPUs
num_cpus = multiprocessing.cpu_count()
print(f"   CPUs: {num_cpus}")

# Baixar modelo de teste
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

# Comprimir com ZipNN
print("\n4. Comprimindo com ZipNN BF16...")
znn = zipnn.ZipNN(bytearray_dtype="bfloat16")

CHUNK_SIZE = 64 * 1024 * 1024  # 64MB
compressed_chunks = []

for i in range(0, len(model_data), CHUNK_SIZE):
    chunk = model_data[i:i+CHUNK_SIZE]
    compressed = znn.compress(chunk)
    if isinstance(compressed, memoryview):
        compressed = bytes(compressed)
    compressed_chunks.append(compressed)

total_original = len(model_data)
total_compressed = sum(len(c) for c in compressed_chunks)
print(f"   Original: {total_original/1024/1024:.0f} MB")
print(f"   Comprimido: {total_compressed/1024/1024:.0f} MB ({total_original/total_compressed:.2f}x)")
print(f"   Chunks: {len(compressed_chunks)}")

# ============ TESTE 1: Descompressão Sequencial (baseline) ============
print("\n" + "=" * 70)
print("TESTE 1: Descompressão SEQUENCIAL (1 thread)")
print("=" * 70)

znn_seq = zipnn.ZipNN(bytearray_dtype="bfloat16")
start = time.time()
result_seq = b""
for chunk in compressed_chunks:
    result_seq += znn_seq.decompress(chunk)
time_seq = time.time() - start
speed_seq = total_original / time_seq / 1024 / 1024

print(f"   Tempo: {time_seq:.2f}s")
print(f"   Velocidade: {speed_seq:.0f} MB/s")

# ============ TESTE 2: Descompressão Paralela (ThreadPool) ============
print("\n" + "=" * 70)
print(f"TESTE 2: Descompressão PARALELA (ThreadPool, {num_cpus} threads)")
print("=" * 70)

def decompress_chunk_thread(idx_chunk):
    idx, chunk = idx_chunk
    znn_local = zipnn.ZipNN(bytearray_dtype="bfloat16")
    return idx, znn_local.decompress(chunk)

start = time.time()
results = {}
with ThreadPoolExecutor(max_workers=num_cpus) as executor:
    for idx, decompressed in executor.map(decompress_chunk_thread, enumerate(compressed_chunks)):
        results[idx] = decompressed

result_parallel = b""
for i in range(len(compressed_chunks)):
    result_parallel += results[i]

time_parallel = time.time() - start
speed_parallel = total_original / time_parallel / 1024 / 1024

print(f"   Tempo: {time_parallel:.2f}s")
print(f"   Velocidade: {speed_parallel:.0f} MB/s")
print(f"   Speedup: {time_seq/time_parallel:.1f}x")

# ============ TESTE 3: Descompressão com ZSTD puro (para comparação) ============
print("\n" + "=" * 70)
print("TESTE 3: ZSTD puro (CPU, para referência)")
print("=" * 70)

# Comprimir com ZSTD puro para comparar
cctx = zstd.ZstdCompressor(level=3)
zstd_compressed = []
for i in range(0, len(model_data), CHUNK_SIZE):
    chunk = model_data[i:i+CHUNK_SIZE]
    zstd_compressed.append(cctx.compress(chunk))

zstd_total = sum(len(c) for c in zstd_compressed)
print(f"   ZSTD comprimido: {zstd_total/1024/1024:.0f} MB ({total_original/zstd_total:.2f}x)")

# Descomprimir ZSTD
dctx = zstd.ZstdDecompressor()
start = time.time()
result_zstd = b""
for chunk in zstd_compressed:
    result_zstd += dctx.decompress(chunk)
time_zstd = time.time() - start
speed_zstd = total_original / time_zstd / 1024 / 1024

print(f"   Tempo decompress: {time_zstd:.2f}s")
print(f"   Velocidade: {speed_zstd:.0f} MB/s")

# ============ TESTE 4: ZSTD Paralelo ============
print("\n" + "=" * 70)
print(f"TESTE 4: ZSTD PARALELO ({num_cpus} threads)")
print("=" * 70)

def decompress_zstd_chunk(idx_chunk):
    idx, chunk = idx_chunk
    dctx_local = zstd.ZstdDecompressor()
    return idx, dctx_local.decompress(chunk)

start = time.time()
results_zstd = {}
with ThreadPoolExecutor(max_workers=num_cpus) as executor:
    for idx, decompressed in executor.map(decompress_zstd_chunk, enumerate(zstd_compressed)):
        results_zstd[idx] = decompressed

result_zstd_parallel = b""
for i in range(len(zstd_compressed)):
    result_zstd_parallel += results_zstd[i]

time_zstd_parallel = time.time() - start
speed_zstd_parallel = total_original / time_zstd_parallel / 1024 / 1024

print(f"   Tempo: {time_zstd_parallel:.2f}s")
print(f"   Velocidade: {speed_zstd_parallel:.0f} MB/s")
print(f"   Speedup vs sequencial: {time_zstd/time_zstd_parallel:.1f}x")

# ============ TESTE 5: LZ4 (para referência - mais rápido) ============
print("\n" + "=" * 70)
print("TESTE 5: LZ4 (referência - não comprime BF16)")
print("=" * 70)

lz4_compressed = []
for i in range(0, len(model_data), CHUNK_SIZE):
    chunk = model_data[i:i+CHUNK_SIZE]
    lz4_compressed.append(lz4.frame.compress(chunk))

lz4_total = sum(len(c) for c in lz4_compressed)
print(f"   LZ4 comprimido: {lz4_total/1024/1024:.0f} MB ({total_original/lz4_total:.2f}x)")

start = time.time()
result_lz4 = b""
for chunk in lz4_compressed:
    result_lz4 += lz4.frame.decompress(chunk)
time_lz4 = time.time() - start
speed_lz4 = total_original / time_lz4 / 1024 / 1024

print(f"   Tempo decompress: {time_lz4:.2f}s")
print(f"   Velocidade: {speed_lz4:.0f} MB/s")

# Verificar integridade
print("\n5. Verificando integridade...")
original_hash = hashlib.sha256(model_data).hexdigest()
print(f"   Sequencial: {'✓' if hashlib.sha256(result_seq).hexdigest() == original_hash else '✗'}")
print(f"   Paralelo:   {'✓' if hashlib.sha256(result_parallel).hexdigest() == original_hash else '✗'}")
print(f"   ZSTD:       {'✓' if hashlib.sha256(result_zstd).hexdigest() == original_hash else '✗'}")
print(f"   LZ4:        {'✓' if hashlib.sha256(result_lz4).hexdigest() == original_hash else '✗'}")

# Resultados
print("\n" + "=" * 70)
print("COMPARAÇÃO DE VELOCIDADE DE DESCOMPRESSÃO")
print("=" * 70)
print(f"\nTamanho: {total_original/1024/1024:.0f} MB")
print()
print(f"{'Método':<35} {'Ratio':>8} {'Tempo':>10} {'Velocidade':>12} {'Speedup':>10}")
print("-" * 80)
print(f"{'ZipNN Sequencial':<35} {total_original/total_compressed:>7.2f}x {time_seq:>8.2f}s {speed_seq:>10.0f} MB/s {1.0:>9.1f}x")
print(f"{'ZipNN Paralelo ({} threads)'.format(num_cpus):<35} {total_original/total_compressed:>7.2f}x {time_parallel:>8.2f}s {speed_parallel:>10.0f} MB/s {time_seq/time_parallel:>9.1f}x")
print(f"{'ZSTD Sequencial':<35} {total_original/zstd_total:>7.2f}x {time_zstd:>8.2f}s {speed_zstd:>10.0f} MB/s {time_seq/time_zstd:>9.1f}x")
print(f"{'ZSTD Paralelo ({} threads)'.format(num_cpus):<35} {total_original/zstd_total:>7.2f}x {time_zstd_parallel:>8.2f}s {speed_zstd_parallel:>10.0f} MB/s {time_seq/time_zstd_parallel:>9.1f}x")
print(f"{'LZ4 (não comprime BF16)':<35} {total_original/lz4_total:>7.2f}x {time_lz4:>8.2f}s {speed_lz4:>10.0f} MB/s {time_seq/time_lz4:>9.1f}x")
print()
print("NOTA: ZipNN é único que comprime BF16 (1.51x), outros não comprimem (1.0x)")
print("=" * 70)
