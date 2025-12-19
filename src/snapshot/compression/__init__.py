"""
Compression submodule for Dumont Snapshot

Provides:
- HybridCompressor: Selects best compressor per file type
- DumontArchive: Read/write .dumont format with chunks
- ChunkManager: Splits data into 64MB chunks
- CompressionMethod: Named compression methods

Methods:
- hybrid_v1: Hybrid compression (LZ4 + ZipNN by file type)
- lz4_fast: Fast LZ4 for GPU decompression
- none: Passthrough (just chunking, no compression)
"""

from .hybrid_compressor import HybridCompressor, CompressionStrategy, FileCategory, Compressor
from .dumont_format import DumontArchive, DumontHeader, ChunkInfo
from .chunk_manager import ChunkManager
from .methods import (
    CompressionMethod,
    CompressionMethodID,
    get_method,
    get_method_by_name,
    get_default_method,
    list_methods,
    describe_methods,
)

__all__ = [
    'HybridCompressor',
    'CompressionStrategy',
    'FileCategory',
    'Compressor',
    'DumontArchive',
    'DumontHeader',
    'ChunkInfo',
    'ChunkManager',
    'CompressionMethod',
    'CompressionMethodID',
    'get_method',
    'get_method_by_name',
    'get_default_method',
    'list_methods',
    'describe_methods',
]
