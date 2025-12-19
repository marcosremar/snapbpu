"""
Compression Methods Registry

Defines named compression methods that can be used in snapshots.
Each method has a unique ID, name, and configuration.

Methods:
- hybrid_v1: Hybrid compression by file type (LZ4 + ZipNN)
- lz4_fast: Fast LZ4 compression (GPU-friendly)
- zipnn_models: ZipNN for neural network weights
- none: No compression (passthrough)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .hybrid_compressor import (
    HybridCompressor,
    Compressor,
    FileCategory,
    CompressionStrategy,
    DEFAULT_STRATEGIES,
)


class CompressionMethodID(Enum):
    """Numeric IDs for compression methods (stored in file format)"""
    NONE = 0
    LZ4_FAST = 1
    LZ4_HC = 2
    ZIPNN = 3
    HYBRID_V1 = 10  # Our hybrid method


@dataclass
class CompressionMethod:
    """Definition of a compression method"""
    id: CompressionMethodID
    name: str
    description: str
    version: str
    gpu_decompress: bool  # Supports nvCOMP GPU decompression
    strategies: Dict[FileCategory, CompressionStrategy] = field(default_factory=dict)

    def get_compressor(self) -> HybridCompressor:
        """Get configured HybridCompressor for this method"""
        return HybridCompressor(strategies=self.strategies if self.strategies else None)


# Registry of all available methods
COMPRESSION_METHODS: Dict[CompressionMethodID, CompressionMethod] = {}


def register_method(method: CompressionMethod):
    """Register a compression method"""
    COMPRESSION_METHODS[method.id] = method


def get_method(method_id: CompressionMethodID) -> CompressionMethod:
    """Get a compression method by ID"""
    if method_id not in COMPRESSION_METHODS:
        raise ValueError(f"Unknown compression method: {method_id}")
    return COMPRESSION_METHODS[method_id]


def get_method_by_name(name: str) -> CompressionMethod:
    """Get a compression method by name"""
    for method in COMPRESSION_METHODS.values():
        if method.name == name:
            return method
    raise ValueError(f"Unknown compression method name: {name}")


# =============================================================================
# Method Definitions
# =============================================================================

# Method 0: None (passthrough)
register_method(CompressionMethod(
    id=CompressionMethodID.NONE,
    name="none",
    description="No compression (passthrough)",
    version="1.0",
    gpu_decompress=False,
    strategies={
        cat: CompressionStrategy(
            category=cat,
            compressor=Compressor.NONE,
            level=0,
            gpu_decompress=False,
            expected_ratio=1.0,
        )
        for cat in FileCategory
    },
))


# Method 1: LZ4 Fast (GPU-friendly)
register_method(CompressionMethod(
    id=CompressionMethodID.LZ4_FAST,
    name="lz4_fast",
    description="Fast LZ4 compression, optimized for GPU decompression",
    version="1.0",
    gpu_decompress=True,
    strategies={
        cat: CompressionStrategy(
            category=cat,
            compressor=Compressor.LZ4,
            level=0,
            gpu_decompress=True,
            expected_ratio=2.5,
        )
        for cat in FileCategory
    },
))


# Method 2: LZ4 High Compression
register_method(CompressionMethod(
    id=CompressionMethodID.LZ4_HC,
    name="lz4_hc",
    description="LZ4 High Compression mode",
    version="1.0",
    gpu_decompress=True,
    strategies={
        cat: CompressionStrategy(
            category=cat,
            compressor=Compressor.LZ4_HC,
            level=9,
            gpu_decompress=True,
            expected_ratio=4.0,
        )
        for cat in FileCategory
    },
))


# Method 3: ZipNN (neural network weights)
register_method(CompressionMethod(
    id=CompressionMethodID.ZIPNN,
    name="zipnn",
    description="ZipNN for neural network weights (FP16/BF16)",
    version="1.0",
    gpu_decompress=False,  # ZipNN doesn't have GPU decompression yet
    strategies={
        cat: CompressionStrategy(
            category=cat,
            compressor=Compressor.ZIPNN,
            level=0,
            gpu_decompress=False,
            expected_ratio=1.3,
        )
        for cat in FileCategory
    },
))


# Method 10: Hybrid v1 (our main method)
# Uses different algorithms per file type for optimal compression
register_method(CompressionMethod(
    id=CompressionMethodID.HYBRID_V1,
    name="hybrid_v1",
    description="Hybrid compression: LZ4 for code/text, ZipNN for models, skip for media/quantized",
    version="1.0",
    gpu_decompress=True,  # LZ4 parts can use GPU
    strategies=DEFAULT_STRATEGIES,  # From hybrid_compressor.py
))


# =============================================================================
# Utility Functions
# =============================================================================

def list_methods() -> List[CompressionMethod]:
    """List all available compression methods"""
    return list(COMPRESSION_METHODS.values())


def get_default_method() -> CompressionMethod:
    """Get the default compression method (hybrid_v1)"""
    return COMPRESSION_METHODS[CompressionMethodID.HYBRID_V1]


def describe_methods() -> str:
    """Get human-readable description of all methods"""
    lines = ["Available compression methods:", ""]
    for method in list_methods():
        gpu = "Yes" if method.gpu_decompress else "No"
        lines.append(f"  [{method.id.value:2d}] {method.name}")
        lines.append(f"       {method.description}")
        lines.append(f"       GPU decompression: {gpu}")
        lines.append("")
    return "\n".join(lines)
