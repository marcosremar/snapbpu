"""
Dumont Snapshot Module

Sistema de snapshot otimizado para workspaces de ML com:
- Compressão híbrida por tipo de arquivo
- Chunks de 64 MB para download/descompressão paralela
- Descompressão GPU ultra-rápida via nvCOMP
- Formato .dumont com resume e verificação
"""

from .snapshot_service import SnapshotService
from .compression import HybridCompressor, DumontArchive

__all__ = [
    'SnapshotService',
    'HybridCompressor',
    'DumontArchive',
]

__version__ = '1.0.0'
