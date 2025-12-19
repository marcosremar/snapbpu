# Estratégia de Snapshot #1: hybrid_v1

**Nome**: Hybrid Compression v1
**ID**: 10
**Versão**: 1.0
**Status**: Implementado

---

## Objetivo

Otimizar transferência de workspaces ML para conexões de internet lentas usando:
- **Compressão em CPU** (prioriza ratio de compressão)
- **Descompressão em GPU** (prioriza velocidade via nvCOMP)
- **Chunks de 64 MB** (permite download paralelo e pipeline)

---

## Critérios de Design

### 1. Compressão por Tipo de Arquivo

Cada tipo de arquivo usa o algoritmo mais adequado:

| Categoria | Extensões | Algoritmo | Justificativa |
|-----------|-----------|-----------|---------------|
| **models_fp16** | .pt, .pth, .safetensors, .bin, .ckpt | **ZipNN** | Otimizado para tensores FP16/BF16. Ratio ~1.3x vs ~1.0x do LZ4. |
| **models_quantized** | .gguf, .ggml | **Nenhum** | Já compactado internamente. Apenas divide em chunks. |
| **code** | .py, .js, .ts, .jsx, .tsx, .go, .rs, .c, .cpp, .h | **LZ4** | Descompressão GPU via nvCOMP. Ratio ~5x para código. |
| **data** | .json, .csv, .parquet, .yaml, .yml, .toml, .xml | **LZ4 HC** | Alto ratio (~10x) para dados estruturados. GPU decompress. |
| **logs** | .log, .txt, .md, .rst | **LZ4** | Bom ratio (~8x) para texto. GPU decompress. |
| **media** | .jpg, .jpeg, .png, .gif, .mp4, .mp3, .zip, .gz, .tar.gz | **Nenhum** | Já compactado. Apenas divide em chunks. |
| **generic** | * | **LZ4** | Fallback seguro com GPU decompress. |

### 2. Tamanho dos Chunks: 64 MB

**Por que 64 MB?**
- Permite começar a extrair rapidamente (não espera download completo)
- Bom para download paralelo (4-8 conexões)
- Cada chunk é independente (pode descomprimir em qualquer ordem)
- Cabe na memória da GPU para descompressão em batch

### 3. Compressão em CPU, Descompressão em GPU

**Compressão (CPU/VPS)**:
- Pode ser mais lenta (roda em background)
- Prioriza máximo ratio de compressão
- Não interfere com GPU que está processando

**Descompressão (GPU)**:
- nvCOMP LZ4: ~312 GB/s (A100) / ~400+ GB/s (RTX 5090 com DE)
- Gargalo é sempre a rede, nunca a GPU
- Pipeline: baixa chunk N+1 enquanto descomprime chunk N

### 4. Arquivos Já Compactados = Apenas Chunking

Para arquivos que já estão compactados (GGUF, JPEG, ZIP, etc):
- **NÃO comprimir novamente** (desperdício de CPU)
- Apenas dividir em chunks de 64 MB
- Checksum CRC32 por chunk para verificação

---

## Formato do Arquivo (.dumont)

```
Offset    Tamanho     Descrição
──────────────────────────────────────────────────────
0         512         HEADER
                      - magic: "DUMONT01" (8 bytes)
                      - version: uint16
                      - flags: uint16
                      - num_chunks: uint32
                      - num_files: uint32
                      - total_compressed: uint64
                      - total_original: uint64
                      - checksum_type: uint8 (1=CRC32)
                      - chunk_size: uint32 (default 64MB)
                      - manifest_offset: uint64
                      - manifest_size: uint32
                      - reserved: pad to 512 bytes

512       21×N        CHUNK INDEX (N = num_chunks)
                      Per chunk:
                      - offset: uint64 (posição no arquivo)
                      - size_compressed: uint32
                      - size_original: uint32
                      - compressor_id: uint8
                        (0=none, 1=lz4, 2=lz4_hc, 3=zipnn)
                      - checksum: uint32 (CRC32)

512+21N   variável    CHUNK DATA
                      [Chunk 0][Chunk 1]...[Chunk N-1]
                      Cada chunk é independente

fim-M     M           MANIFEST (LZ4 compressed JSON)
                      Lista de arquivos com:
                      - path, size, mode, mtime
                      - chunk_start, chunk_end
                      - compressor_id
```

---

## Algoritmos Suportados

### LZ4 (ID: 1)
- **Compressão**: Rápida (~400 MB/s)
- **Descompressão CPU**: ~4-6 GB/s
- **Descompressão GPU (nvCOMP)**: ~312 GB/s
- **Ratio típico**: 2-5x para texto

### LZ4 HC (ID: 2)
- **Compressão**: Lenta (~50 MB/s)
- **Descompressão**: Igual ao LZ4
- **Ratio típico**: 3-10x (melhor que LZ4)

### ZipNN (ID: 3)
- **Compressão**: Média (~100 MB/s)
- **Descompressão**: CPU only por enquanto
- **Ratio típico**: 1.2-1.5x para pesos neurais FP16/BF16
- **Vantagem**: Específico para tensores de ML

### None (ID: 0)
- **Passthrough**: Sem compressão
- **Uso**: Arquivos já compactados (GGUF, media)

---

## Performance Esperada

### Cenário: Workspace 68 GB, Internet 100 Mbps

**Sem otimização:**
- Download: 68 GB ÷ 12.5 MB/s = **90 minutos**
- Descompressão: N/A

**Com hybrid_v1:**
- Compressão híbrida: 68 GB → ~40 GB (ratio ~1.7x)
- Download: 40 GB ÷ 12.5 MB/s = **53 minutos**
- Descompressão GPU: 68 GB ÷ 312 GB/s = **<1 segundo**
- **Economia: 37 minutos (41%)**

### Throughput de Descompressão

| GPU | LZ4 nvCOMP | Bottleneck |
|-----|------------|------------|
| RTX 4090 | ~300 GB/s | Nunca |
| RTX 5090 | ~400+ GB/s | Nunca |
| A100 | ~312 GB/s | Nunca |

**Bottleneck real**: Sempre a rede (internet lenta)

---

## Implementação

### Arquivos

```
src/snapshot/
├── compression/
│   ├── hybrid_compressor.py   # Seleção de algoritmo por tipo
│   ├── dumont_format.py       # Leitura/escrita do formato
│   ├── chunk_manager.py       # Divisão em chunks 64 MB
│   └── methods.py             # Registry de métodos
├── snapshot_service.py        # API de alto nível
└── strategies/
    └── hybrid_v1/
        └── README.md          # Esta documentação
```

### Uso

```python
from src.snapshot import SnapshotService

service = SnapshotService(chunk_size=64*1024*1024)

# Criar snapshot (CPU)
info = service.create_snapshot("/workspace", "snapshot.dumont")

# Restaurar (GPU auto-detectada)
result = service.restore_snapshot("snapshot.dumont", "/target")
```

### CLI

```bash
# Pack (compressão em CPU)
dumont-pack /workspace -o workspace.dumont --chunk-size 64

# Restore (descompressão GPU se disponível)
dumont-restore workspace.dumont /target
```

---

## Decisões Técnicas

### Por que LZ4 e não Zstd?

- LZ4 tem suporte nativo no nvCOMP com 312+ GB/s
- Zstd no nvCOMP é mais lento (~15-25 GB/s)
- Para código/texto, LZ4 já tem bom ratio

### Por que ZipNN para modelos?

- Específico para pesos neurais FP16/BF16
- Explora padrões estatísticos em tensores
- Desenvolvido pela IBM Research
- Ratio 23-51% melhor que compressores genéricos

### Por que não comprimir GGUF?

- GGUF já usa quantização (compressão com perda)
- Comprimir novamente = ratio ~1.01x
- Desperdício de CPU sem benefício

### Por que 64 MB e não 256 MB?

- Começa a extrair mais rápido
- Melhor para conexões instáveis (resume parcial)
- 64 MB ainda é eficiente para nvCOMP batch

---

## TODO / Roadmap

- [ ] Integrar nvCOMP real (não apenas fallback CPU)
- [ ] Benchmark real em RTX 5090 com DE (Decompression Engine)
- [ ] Download paralelo com aria2c
- [ ] Resume de downloads parciais (estado por chunk)
- [ ] Suporte a ZipNN GPU (quando IBM lançar)
- [ ] Compressão incremental (delta entre snapshots)

---

## Referências

- [NVIDIA nvCOMP](https://developer.nvidia.com/nvcomp) - GPU compression
- [nvCOMP Benchmarks](https://github.com/NVIDIA/nvcomp/blob/main/doc/Benchmarks.md)
- [ZipNN IBM](https://github.com/ibm/zipnn) - Neural network compression
- [LZ4](https://github.com/lz4/lz4) - Fast compression
- [Blackwell DE](https://developer.nvidia.com/blog/speeding-up-data-decompression-with-nvcomp-and-the-nvidia-blackwell-decompression-engine/) - Hardware decompression
