"""
Repository interfaces (abstractions for Dependency Inversion Principle)
"""
from .gpu_provider import IGpuProvider
from .snapshot_provider import ISnapshotProvider
from .user_repository import IUserRepository

__all__ = ['IGpuProvider', 'ISnapshotProvider', 'IUserRepository']
