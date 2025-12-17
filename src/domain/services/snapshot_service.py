"""
Snapshot Service - Domain Service (Business Logic)
Orchestrates snapshot operations using ISnapshotProvider
"""
import logging
from typing import List, Dict, Any, Optional

from ..repositories import ISnapshotProvider
from ...core.exceptions import SnapshotException

logger = logging.getLogger(__name__)


class SnapshotService:
    """
    Domain service for snapshot management.
    Orchestrates backup/restore operations (Single Responsibility Principle).
    """

    def __init__(self, snapshot_provider: ISnapshotProvider):
        """
        Initialize snapshot service

        Args:
            snapshot_provider: Snapshot provider implementation (restic, borg, etc)
        """
        self.snapshot_provider = snapshot_provider

    def create_snapshot(
        self,
        ssh_host: str,
        ssh_port: int,
        source_path: str = "/workspace",
        tags: Optional[List[str]] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """
        Create a snapshot of a directory

        Args:
            ssh_host: SSH host
            ssh_port: SSH port
            source_path: Path to backup
            tags: Optional tags for the snapshot
            ssh_user: SSH user

        Returns:
            Snapshot creation result
        """
        logger.info(f"Creating snapshot of {source_path} on {ssh_host}:{ssh_port}")

        result = self.snapshot_provider.create_snapshot(
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            source_path=source_path,
            tags=tags,
            ssh_user=ssh_user,
        )

        logger.info(f"Snapshot {result.get('snapshot_id')} created")
        return result

    def list_snapshots(
        self,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> List[Dict[str, Any]]:
        """
        List all snapshots

        Args:
            ssh_host: Optional SSH host (for remote listing)
            ssh_port: Optional SSH port
            ssh_user: SSH user

        Returns:
            List of snapshots
        """
        return self.snapshot_provider.list_snapshots(
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
        )

    def restore_snapshot(
        self,
        snapshot_id: str,
        ssh_host: str,
        ssh_port: int,
        target_path: str = "/workspace",
        verify: bool = False,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """
        Restore a snapshot

        Args:
            snapshot_id: Snapshot ID to restore
            ssh_host: SSH host
            ssh_port: SSH port
            target_path: Path to restore to
            verify: Whether to verify restoration
            ssh_user: SSH user

        Returns:
            Restore result
        """
        logger.info(f"Restoring snapshot {snapshot_id} to {target_path}")

        result = self.snapshot_provider.restore_snapshot(
            snapshot_id=snapshot_id,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            target_path=target_path,
            verify=verify,
            ssh_user=ssh_user,
        )

        logger.info(f"Snapshot {snapshot_id} restored")
        return result

    def delete_snapshot(
        self,
        snapshot_id: str,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> bool:
        """
        Delete a snapshot

        Args:
            snapshot_id: Snapshot ID to delete
            ssh_host: Optional SSH host
            ssh_port: Optional SSH port
            ssh_user: SSH user

        Returns:
            True if successful
        """
        logger.info(f"Deleting snapshot {snapshot_id}")
        return self.snapshot_provider.delete_snapshot(
            snapshot_id=snapshot_id,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
        )

    def get_snapshot_info(
        self,
        snapshot_id: str,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """
        Get detailed snapshot information

        Args:
            snapshot_id: Snapshot ID
            ssh_host: Optional SSH host
            ssh_port: Optional SSH port
            ssh_user: SSH user

        Returns:
            Snapshot information
        """
        return self.snapshot_provider.get_snapshot_info(
            snapshot_id=snapshot_id,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
        )

    def prune_snapshots(
        self,
        keep_last: int = 10,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """
        Prune old snapshots

        Args:
            keep_last: Number of snapshots to keep
            ssh_host: Optional SSH host
            ssh_port: Optional SSH port
            ssh_user: SSH user

        Returns:
            Prune result
        """
        logger.info(f"Pruning snapshots (keep last {keep_last})")
        return self.snapshot_provider.prune_snapshots(
            keep_last=keep_last,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
        )
