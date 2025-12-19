# Dumont Snapshot Module

Sistema de snapshot otimizado para workspaces de ML com:
- **Compressão híbrida** (melhor compressor por tipo de arquivo)
- **Chunks de 64 MB** (download paralelo + processamento pipeline)
- **ZipNN (IBM)** para modelos BF16/FP16 (~33% economia)
- **LZ4** para código/texto (~200x ratio)

---

## Benchmarks Reais (Testados em RTX 3060 - Polônia, 17/12/2024)

### Resultados por Tipo de Arquivo

| Tipo de Arquivo      | Compressor   | Ratio   | Compressão    | Descompressão | Integridade |
|----------------------|--------------|---------|---------------|---------------|-------------|
| **Código Python**    | LZ4          | 127x    | 9,265 MB/s    | 1,290 MB/s    | ✓ SHA256    |
| **JSON/YAML**        | LZ4          | 175x    | 10,191 MB/s   | 1,281 MB/s    | ✓ SHA256    |
| **Logs (.log,.txt)** | LZ4          | 218x    | 10,458 MB/s   | 1,303 MB/s    | ✓ SHA256    |
| **CSV/Dados**        | LZ4          | 3.6x    | 627 MB/s      | 2,867 MB/s    | ✓ SHA256    |
| **Modelos BF16**     | ZipNN (IBM)  | **1.5x**| 1,518 MB/s    | 4,642 MB/s    | ✓ SHA256    |
| **Checkpoints .pt**  | ZipNN        | 1.2x    | 1,095 MB/s    | 4,942 MB/s    | ✓ SHA256    |
| **GGUF (quantizado)**| Nenhum       | 1.0x    | -             | -             | -           |
| **Imagens/Vídeos**   | Nenhum       | 1.0x    | -             | -             | -           |

### Teste com Modelo Real: TinyLlama-1.1B (BF16)

```
Arquivo: 2098 MB (2.1 GB)
Chunks de 64MB: 33

Resultados por chunk:
- LZ4:        1.00x (não comprime pesos BF16)
- ZipNN-BF16: 1.51x (consistente em todos os 33 chunks)

RESULTADO FINAL:
  Original:  2098 MB
  LZ4:       2098 MB (ratio: 1.00x)
  ZipNN:     1394 MB (ratio: 1.51x)
  Economia:  33.6%
```

### Projeção para Modelos Maiores

| Modelo      | Original | Com ZipNN  | Economia |
|-------------|----------|------------|----------|
| LLaMA-7B    | 14 GB    | **9.3 GB** | 4.7 GB   |
| LLaMA-13B   | 26 GB    | **17.3 GB**| 8.7 GB   |
| LLaMA-70B   | 140 GB   | **93 GB**  | 47 GB    |
| Mixtral-8x7B| 90 GB    | **60 GB**  | 30 GB    |

---

## Estratégia de Compressão Híbrida

### Método: `hybrid_v2` (Atualizado)

**Princípio**: Cada tipo de arquivo usa o compressor que oferece o melhor ratio.

#### Por que cada decisão?

**Modelos FP16/BF16 → ZipNN (IBM)**
- ZipNN separa expoente e mantissa dos floats
- Aplica Huffman encoding no expoente (altamente compressível)
- Ratio de **1.5x** para BF16 (33% economia)
- Velocidade: 1.5 GB/s compressão, 4.6 GB/s descompressão
- **Lossless** - integridade verificada via SHA256

**Código/Texto/Logs → LZ4**
- Ratio extremo para texto repetitivo (100-200x)
- Velocidade absurda: 10+ GB/s compressão
- Perfeito para download paralelo
- Suporte futuro a nvCOMP GPU (300+ GB/s)

**Modelos Quantizados (GGUF/GGML) → Nenhum**
- GGUF já usa quantização interna (4-8 bits)
- Comprimir novamente = 0% ganho, apenas CPU wasted
- Apenas divide em chunks de 64 MB

**Mídia (JPG, PNG, MP4) → Nenhum**
- Formatos já comprimidos (DCT, H.264, etc)
- Apenas chunking para download paralelo

---

## Arquitetura de Chunks (64 MB)

### Por que 64 MB?

1. **Download paralelo**: Múltiplos chunks podem ser baixados simultaneamente
2. **Pipeline**: Enquanto chunk N baixa, chunk N-1 descomprime
3. **Resume**: Falha em um chunk não perde progresso total
4. **Memória**: Cabe em RAM de GPUs menores
5. **Latência**: Tamanho otimizado para HDDs/SSDs

### Formato do Arquivo (.dumont)

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER (512 bytes)                                          │
│ - magic: "DUMONT02"                                         │
│ - version: 2                                                │
│ - num_chunks, num_files                                     │
│ - total_size_compressed, total_size_original                │
│ - chunk_size: 67108864 (64 MB)                              │
│ - manifest_offset, manifest_size                            │
├─────────────────────────────────────────────────────────────┤
│ CHUNK INDEX (25 bytes × num_chunks)                         │
│ Per chunk:                                                  │
│ - offset (8 bytes)                                          │
│ - size_compressed (4 bytes)                                 │
│ - size_original (4 bytes)                                   │
│ - compressor_id (1 byte): 0=none, 1=lz4, 2=lz4_hc, 3=zipnn │
│ - checksum SHA256 (8 bytes - primeiros 64 bits)            │
├─────────────────────────────────────────────────────────────┤
│ CHUNK DATA                                                  │
│ [Chunk 0] [Chunk 1] [Chunk 2] ... [Chunk N]                │
│ Cada chunk é independente e pode ser descomprimido sozinho │
├─────────────────────────────────────────────────────────────┤
│ MANIFEST (LZ4 compressed JSON)                              │
│ - Lista de arquivos com paths, sizes, permissions          │
│ - Mapeamento arquivo → chunks                               │
│ - Checksums por arquivo                                     │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline de Restauração

```
Internet (lenta)     CPU/RAM              Armazenamento
     │                  │                      │
     │  Download        │                      │
     │  Chunk N    ────►│ Buffer 512MB        │
     │                  │   │                  │
     │  Download        │   │  Decompress      │
     │  Chunk N+1  ────►│   └────────────────►│ Write
     │                  │      LZ4: 1.3 GB/s   │
     │                  │      ZipNN: 4.6 GB/s │
     │                  │                      │
     ▼                  ▼                      ▼
   ~12 MB/s          Ring Buffer           3-7 GB/s
   (100 Mbps)        (paralelo)            (NVMe)
```

**Gargalo principal**: Internet (não CPU nem disco)

---

## Compressores Suportados

### 1. LZ4 (ID: 1)
- **Uso**: Código, texto, logs, JSON, YAML, CSV
- **Ratio**: 3-200x (depende do conteúdo)
- **Velocidade**: 10+ GB/s compressão, 1-3 GB/s descompressão
- **Vantagem**: Ultra-rápido, suporte nvCOMP GPU

### 2. LZ4-HC (ID: 2)
- **Uso**: Arquivos onde ratio importa mais que velocidade
- **Ratio**: 10-20% melhor que LZ4
- **Velocidade**: ~100 MB/s compressão (lento), mesma descompressão
- **Vantagem**: Melhor ratio quando tempo de compressão não importa

### 3. ZipNN (ID: 3) - IBM Research
- **Uso**: Modelos FP16, BF16, FP32, safetensors, .pt, .pth
- **Ratio**: 1.2-1.5x para modelos BF16 (33% economia)
- **Velocidade**: 1.5 GB/s comp, 4.6 GB/s decomp
- **Vantagem**: Único que comprime pesos de NN efetivamente
- **Técnica**: Separa expoente/mantissa + Huffman encoding

### 4. Nenhum (ID: 0)
- **Uso**: GGUF, GGML, imagens, vídeos, arquivos já comprimidos
- **Ratio**: 1.0x
- **Vantagem**: Evita CPU desnecessário, apenas chunking

---

## Mapeamento Extensão → Compressor

```python
COMPRESSION_MAP = {
    # Modelos de NN (ZipNN)
    ".safetensors": "zipnn",
    ".pt": "zipnn",
    ".pth": "zipnn", 
    ".bin": "zipnn",       # Hugging Face format
    ".ckpt": "zipnn",
    
    # Modelos quantizados (nenhum)
    ".gguf": "none",
    ".ggml": "none",
    ".Q4_K_M": "none",
    ".Q5_K_M": "none",
    
    # Código (LZ4)
    ".py": "lz4",
    ".js": "lz4",
    ".ts": "lz4",
    ".jsx": "lz4",
    ".tsx": "lz4",
    ".go": "lz4",
    ".rs": "lz4",
    ".c": "lz4",
    ".cpp": "lz4",
    ".h": "lz4",
    ".hpp": "lz4",
    ".java": "lz4",
    ".sh": "lz4",
    
    # Dados estruturados (LZ4)
    ".json": "lz4",
    ".yaml": "lz4",
    ".yml": "lz4",
    ".xml": "lz4",
    ".csv": "lz4",
    ".parquet": "lz4",
    ".arrow": "lz4",
    
    # Texto/Logs (LZ4)
    ".txt": "lz4",
    ".log": "lz4",
    ".md": "lz4",
    ".rst": "lz4",
    
    # Mídia (nenhum - já comprimido)
    ".jpg": "none",
    ".jpeg": "none",
    ".png": "none",
    ".gif": "none",
    ".mp4": "none",
    ".mp3": "none",
    ".wav": "none",
    ".webp": "none",
    
    # Arquivos comprimidos (nenhum)
    ".zip": "none",
    ".gz": "none",
    ".tar.gz": "none",
    ".7z": "none",
    ".rar": "none",
    
    # Default
    "*": "lz4",
}
```

---

## Uso

### CLI

```bash
# Empacotar workspace
dumont-pack /workspace -o workspace.dumont

# Ver informações do snapshot
dumont-restore workspace.dumont --info

# Restaurar
dumont-restore workspace.dumont /target

# Restaurar com verificação de integridade
dumont-restore workspace.dumont /target --verify
```

### Python API

```python
from dumont_snapshot import SnapshotService

# Criar snapshot
service = SnapshotService()
result = service.create_snapshot(
    source_path="/workspace",
    output_path="workspace.dumont",
    chunk_size=64 * 1024 * 1024  # 64 MB
)
print(f"Comprimido: {result.original_size} -> {result.compressed_size}")
print(f"Ratio: {result.ratio:.2f}x")

# Restaurar
service.restore_snapshot(
    snapshot_path="workspace.dumont",
    target_path="/workspace",
    verify=True  # Verificar SHA256
)
```

---

## Dependências

```
lz4>=4.3.0          # LZ4 compression
zipnn>=1.0.0        # ZipNN for neural weights (IBM)
numpy>=1.20.0       # Array operations
```

---

## Estrutura do Módulo

```
src/snapshot/
├── __init__.py              # Exports principais
├── snapshot_service.py      # API de alto nível
├── README.md                # Esta documentação
├── compression/
│   ├── __init__.py
│   ├── hybrid_compressor.py # Seleção de compressor por tipo
│   ├── dumont_format.py     # Formato binário .dumont
│   ├── chunk_manager.py     # Divisão em chunks 64 MB
│   └── methods.py           # Registry de métodos
└── strategies/
    ├── lz4_strategy.py      # LZ4/LZ4-HC
    └── zipnn_strategy.py    # ZipNN (IBM)

scripts/
├── dumont-pack.py           # CLI empacotamento
├── dumont-restore.py        # CLI restauração
└── benchmark_compression.py # Benchmark de compressores
```

---

## Changelog

### v2.0.0 (2024-12-17)
- ✅ Atualizado benchmarks com testes reais (RTX 3060)
- ✅ Documentado ZipNN (IBM) para modelos BF16/FP16
- ✅ Confirmado 33% economia em modelo real (TinyLlama-1.1B)
- ✅ Mapeamento completo extensão → compressor
- ✅ Chunks de 64 MB com verificação SHA256

### v1.0.0 (2024-12-01)
- Versão inicial com LZ4 e suporte básico

---

## Roadmap

- [ ] Integrar nvCOMP para descompressão GPU (300+ GB/s)
- [ ] Download paralelo com aria2c/curl multi
- [ ] Resume de downloads parciais
- [ ] Suporte a ZipNN GPU (quando IBM lançar)
- [ ] Streaming compression para arquivos muito grandes
