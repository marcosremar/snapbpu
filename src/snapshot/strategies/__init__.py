"""
Snapshot Strategies

Cada estratégia define um método de compressão/descompressão com critérios específicos.

Estratégias disponíveis:
- hybrid_v1 (ID: 10): Compressão híbrida por tipo de arquivo
  - Compressão em CPU (prioriza ratio)
  - Descompressão em GPU (nvCOMP LZ4)
  - Chunks de 64 MB

Futuras estratégias:
- hybrid_v2: Com suporte a novos algoritmos
- streaming: Para arquivos muito grandes (>100GB)
"""

STRATEGIES = {
    "hybrid_v1": {
        "id": 10,
        "name": "Hybrid Compression v1",
        "description": "Compressão híbrida por tipo de arquivo. CPU compress, GPU decompress.",
        "version": "1.0",
        "chunk_size": 64 * 1024 * 1024,  # 64 MB
        "gpu_decompress": True,
    },
}


def get_strategy_info(name: str) -> dict:
    """Get information about a strategy"""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}")
    return STRATEGIES[name]


def list_strategies() -> list:
    """List all available strategies"""
    return list(STRATEGIES.keys())
