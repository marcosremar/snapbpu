"""
Abstract interface for snapshot/backup providers (Dependency Inversion Principle)
Allows swapping between restic, borg, duplicity, etc.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ISnapshotProvider(ABC):
    """Abstract interface for snapshot/backup providers"""

    @abstractmethod
    def create_snapshot(
        self,
        ssh_host: str,
        ssh_port: int,
        source_path: str,
        tags: Optional[List[str]] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Create a snapshot of a directory"""
        pass

    @abstractmethod
    def list_snapshots(
        self,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> List[Dict[str, Any]]:
        """List all snapshots"""
        pass

    @abstractmethod
    def restore_snapshot(
        self,
        snapshot_id: str,
        ssh_host: str,
        ssh_port: int,
        target_path: str,
        verify: bool = False,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Restore a snapshot to a target path"""
        pass

    @abstractmethod
    def delete_snapshot(
        self,
        snapshot_id: str,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> bool:
        """Delete a snapshot"""
        pass

    @abstractmethod
    def get_snapshot_info(
        self,
        snapshot_id: str,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Get detailed information about a snapshot"""
        pass

    @abstractmethod
    def prune_snapshots(
        self,
        keep_last: int = 10,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Prune old snapshots according to retention policy"""
        pass
