"""
Restic Snapshot Provider Implementation
Implements ISnapshotProvider interface (Dependency Inversion Principle)
"""
import subprocess
import json
import os
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from ...core.exceptions import SnapshotException, SSHException
from ...core.constants import RESTIC_DEFAULT_CONNECTIONS
from ...domain.repositories import ISnapshotProvider

logger = logging.getLogger(__name__)


class ResticProvider(ISnapshotProvider):
    """
    Restic implementation of ISnapshotProvider.
    Handles all backup/restore operations using restic.
    """

    def __init__(
        self,
        repo: str,
        password: str,
        access_key: str,
        secret_key: str,
        connections: int = RESTIC_DEFAULT_CONNECTIONS,
    ):
        """
        Initialize Restic provider

        Args:
            repo: Restic repository URL (e.g., s3:https://endpoint.com/bucket/restic)
            password: Restic repository password
            access_key: S3/R2 access key
            secret_key: S3/R2 secret key
            connections: Number of parallel connections
        """
        if not repo or not password:
            raise ValueError("Restic repository and password are required")

        self.repo = repo
        self.password = password
        self.access_key = access_key
        self.secret_key = secret_key
        self.connections = connections

    def create_snapshot(
        self,
        ssh_host: str,
        ssh_port: int,
        source_path: str,
        tags: Optional[List[str]] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Create a snapshot of a directory via SSH"""
        logger.info(f"Creating snapshot of {source_path} on {ssh_host}:{ssh_port}")

        tag_args = []
        if tags:
            for tag in tags:
                tag_args.extend(["--tag", tag])

        # Build restic command
        restic_cmd = (
            f"export AWS_ACCESS_KEY_ID='{self.access_key}' && "
            f"export AWS_SECRET_ACCESS_KEY='{self.secret_key}' && "
            f"export RESTIC_PASSWORD='{self.password}' && "
            f"export RESTIC_REPOSITORY='{self.repo}' && "
            f"restic backup {source_path} {' '.join(tag_args)} "
            f"-o s3.connections={self.connections} --json"
        )

        try:
            # Execute via SSH
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=30",
                    "-p", str(ssh_port),
                    f"{ssh_user}@{ssh_host}",
                    restic_cmd,
                ],
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour max
            )

            if result.returncode != 0:
                logger.error(f"Snapshot creation failed: {result.stderr}")
                raise SnapshotException(f"Failed to create snapshot: {result.stderr}")

            # Parse last JSON line (summary)
            lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
            if not lines:
                raise SnapshotException("No output from restic backup")

            # Get last JSON line
            for line in reversed(lines):
                try:
                    summary = json.loads(line)
                    if summary.get("message_type") == "summary":
                        return {
                            "snapshot_id": summary.get("snapshot_id", "")[:8],
                            "files_new": summary.get("files_new", 0),
                            "files_changed": summary.get("files_changed", 0),
                            "files_unmodified": summary.get("files_unmodified", 0),
                            "total_files_processed": summary.get("total_files_processed", 0),
                            "data_added": summary.get("data_added", 0),
                            "total_bytes_processed": summary.get("total_bytes_processed", 0),
                        }
                except json.JSONDecodeError:
                    continue

            raise SnapshotException("Could not parse restic output")

        except subprocess.TimeoutExpired:
            logger.error("Snapshot creation timed out")
            raise SnapshotException("Snapshot creation timed out after 1 hour")
        except Exception as e:
            logger.error(f"Unexpected error creating snapshot: {e}")
            raise SnapshotException(f"Failed to create snapshot: {e}")

    def list_snapshots(
        self,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> List[Dict[str, Any]]:
        """List all snapshots"""
        logger.debug("Listing snapshots")

        restic_cmd = (
            f"export AWS_ACCESS_KEY_ID='{self.access_key}' && "
            f"export AWS_SECRET_ACCESS_KEY='{self.secret_key}' && "
            f"export RESTIC_PASSWORD='{self.password}' && "
            f"export RESTIC_REPOSITORY='{self.repo}' && "
            f"restic snapshots --json"
        )

        try:
            # Execute locally or via SSH
            if ssh_host and ssh_port:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=30",
                        "-p", str(ssh_port),
                        f"{ssh_user}@{ssh_host}",
                        restic_cmd,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            else:
                result = subprocess.run(
                    ["bash", "-c", restic_cmd],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=self._get_env(),
                )

            if result.returncode != 0:
                logger.error(f"Failed to list snapshots: {result.stderr}")
                return []

            snapshots = json.loads(result.stdout) if result.stdout else []
            formatted = []

            for s in snapshots:
                formatted.append({
                    "id": s.get("id", ""),
                    "short_id": s.get("id", "")[:8],
                    "time": s.get("time", "")[:19].replace("T", " "),
                    "hostname": s.get("hostname", ""),
                    "tags": s.get("tags", []),
                    "paths": s.get("paths", []),
                })

            # Sort by time (newest first)
            formatted.sort(key=lambda x: x["time"], reverse=True)
            return formatted

        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            return []

    def restore_snapshot(
        self,
        snapshot_id: str,
        ssh_host: str,
        ssh_port: int,
        target_path: str,
        verify: bool = False,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Restore a snapshot to a target path via SSH"""
        logger.info(f"Restoring snapshot {snapshot_id} to {target_path} on {ssh_host}:{ssh_port}")

        # Build restic restore command
        verify_flag = "--verify" if verify else ""
        restic_cmd = (
            f"export AWS_ACCESS_KEY_ID='{self.access_key}' && "
            f"export AWS_SECRET_ACCESS_KEY='{self.secret_key}' && "
            f"export RESTIC_PASSWORD='{self.password}' && "
            f"export RESTIC_REPOSITORY='{self.repo}' && "
            f"restic restore {snapshot_id} --target / --no-owner "
            f"-o s3.connections={self.connections} {verify_flag} 2>&1"
        )

        try:
            # Execute via SSH
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=30",
                    "-p", str(ssh_port),
                    f"{ssh_user}@{ssh_host}",
                    restic_cmd,
                ],
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes max
            )

            output = result.stdout + result.stderr

            # Parse output for statistics
            files_restored = 0
            errors = []

            for line in output.split("\n"):
                if "restoring" in line.lower():
                    files_restored += 1
                if "error" in line.lower() and "lchown" not in line.lower():
                    errors.append(line.strip())

            if result.returncode != 0 and errors:
                logger.warning(f"Restore completed with errors: {errors[:5]}")

            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "target_path": target_path,
                "files_restored": files_restored,
                "errors": errors[:10],  # Limit to 10 errors
                "output": output,
            }

        except subprocess.TimeoutExpired:
            logger.error("Restore timed out")
            raise SnapshotException("Restore timed out after 30 minutes")
        except Exception as e:
            logger.error(f"Unexpected error restoring snapshot: {e}")
            raise SnapshotException(f"Failed to restore snapshot: {e}")

    def delete_snapshot(
        self,
        snapshot_id: str,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> bool:
        """Delete a snapshot"""
        logger.info(f"Deleting snapshot {snapshot_id}")

        restic_cmd = (
            f"export AWS_ACCESS_KEY_ID='{self.access_key}' && "
            f"export AWS_SECRET_ACCESS_KEY='{self.secret_key}' && "
            f"export RESTIC_PASSWORD='{self.password}' && "
            f"export RESTIC_REPOSITORY='{self.repo}' && "
            f"restic forget {snapshot_id} --prune"
        )

        try:
            # Execute locally or via SSH
            if ssh_host and ssh_port:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=30",
                        "-p", str(ssh_port),
                        f"{ssh_user}@{ssh_host}",
                        restic_cmd,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            else:
                result = subprocess.run(
                    ["bash", "-c", restic_cmd],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=self._get_env(),
                )

            success = result.returncode == 0
            if success:
                logger.info(f"Snapshot {snapshot_id} deleted")
            else:
                logger.error(f"Failed to delete snapshot: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete snapshot: {e}")
            return False

    def get_snapshot_info(
        self,
        snapshot_id: str,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Get detailed information about a snapshot"""
        # List all snapshots and find the one
        snapshots = self.list_snapshots(ssh_host, ssh_port, ssh_user)
        for snapshot in snapshots:
            if snapshot["id"].startswith(snapshot_id) or snapshot["short_id"] == snapshot_id:
                return snapshot
        return {}

    def prune_snapshots(
        self,
        keep_last: int = 10,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: str = "root",
    ) -> Dict[str, Any]:
        """Prune old snapshots according to retention policy"""
        logger.info(f"Pruning snapshots (keep last {keep_last})")

        restic_cmd = (
            f"export AWS_ACCESS_KEY_ID='{self.access_key}' && "
            f"export AWS_SECRET_ACCESS_KEY='{self.secret_key}' && "
            f"export RESTIC_PASSWORD='{self.password}' && "
            f"export RESTIC_REPOSITORY='{self.repo}' && "
            f"restic forget --keep-last {keep_last} --prune"
        )

        try:
            # Execute locally or via SSH
            if ssh_host and ssh_port:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ConnectTimeout=30",
                        "-p", str(ssh_port),
                        f"{ssh_user}@{ssh_host}",
                        restic_cmd,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            else:
                result = subprocess.run(
                    ["bash", "-c", restic_cmd],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=self._get_env(),
                )

            if result.returncode != 0:
                logger.error(f"Prune failed: {result.stderr}")
                return {"success": False, "error": result.stderr}

            return {"success": True, "output": result.stdout}

        except Exception as e:
            logger.error(f"Failed to prune snapshots: {e}")
            return {"success": False, "error": str(e)}

    # Helper methods

    def _get_env(self) -> Dict[str, str]:
        """Get environment variables for restic"""
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = self.access_key
        env["AWS_SECRET_ACCESS_KEY"] = self.secret_key
        env["RESTIC_PASSWORD"] = self.password
        env["RESTIC_REPOSITORY"] = self.repo
        return env
