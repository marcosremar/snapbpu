"""
GPU Warm Pool Service - Estrategia principal de failover.

Utiliza multiplas GPUs do mesmo host fisico no VAST.ai,
compartilhando um Volume persistente para failover em 30-60 segundos.
"""
from .manager import WarmPoolManager, WarmPoolState, WarmPoolStatus, get_warm_pool_manager
from .host_finder import HostFinder, MultiGPUHost
from .volume_service import VolumeService

__all__ = [
    'WarmPoolManager',
    'WarmPoolState',
    'WarmPoolStatus',
    'get_warm_pool_manager',
    'HostFinder',
    'MultiGPUHost',
    'VolumeService',
]
