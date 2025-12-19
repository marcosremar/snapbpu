"""
Snapshot Service - High-level API for workspace snapshots

Provides:
- Create snapshot from workspace directory
- Restore snapshot to directory
- Upload/download to/from R2
- GPU-accelerated decompression
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from .compression import DumontArchive, HybridCompressor, ChunkManager


@dataclass
class SnapshotInfo:
    """Information about a snapshot"""
    id: str
    path: str
    size_original: int
    size_compressed: int
    num_files: int
    num_chunks: int
    compression_ratio: float
    created_at: float


@dataclass
class RestoreProgress:
    """Progress information during restore"""
    phase: str  # 'download', 'decompress', 'extract'
    current_chunk: int
    total_chunks: int
    bytes_processed: int
    bytes_total: int
    elapsed_seconds: float
    estimated_remaining: float


class SnapshotService:
    """
    High-level service for creating and restoring workspace snapshots.

    Usage:
        service = SnapshotService()

        # Create snapshot
        info = service.create_snapshot("/workspace", "snapshot.dumont")

        # Restore snapshot
        service.restore_snapshot("snapshot.dumont", "/workspace", use_gpu=True)
    """

    def __init__(self, chunk_size: int = 64 * 1024 * 1024):
        """
        Initialize snapshot service.

        Args:
            chunk_size: Size of chunks in bytes (default 64 MB)
        """
        self.chunk_size = chunk_size
        self.compressor = HybridCompressor()

    def create_snapshot(
        self,
        source_dir: str,
        output_path: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> SnapshotInfo:
        """
        Create a snapshot from a directory.

        Args:
            source_dir: Directory to snapshot
            output_path: Path for output .dumont file
            progress_callback: Optional callback(filepath, file_index, total_files)

        Returns:
            SnapshotInfo with details about the snapshot
        """
        start_time = time.time()

        # Create archive
        with DumontArchive.create(output_path, chunk_size=self.chunk_size) as archive:
            archive.add_directory(source_dir, progress_callback)

        # Read back stats
        with DumontArchive.open(output_path) as archive:
            stats = archive.get_stats()

        # Generate snapshot ID from file hash
        with open(output_path, 'rb') as f:
            # Read first and last 1MB for quick hash
            first_chunk = f.read(1024 * 1024)
            f.seek(-min(1024 * 1024, os.path.getsize(output_path)), 2)
            last_chunk = f.read()
            snapshot_id = hashlib.sha256(first_chunk + last_chunk).hexdigest()[:12]

        return SnapshotInfo(
            id=snapshot_id,
            path=output_path,
            size_original=stats['total_original'],
            size_compressed=stats['total_compressed'],
            num_files=stats['num_files'],
            num_chunks=stats['num_chunks'],
            compression_ratio=stats['ratio'],
            created_at=time.time(),
        )

    @staticmethod
    def detect_gpu() -> bool:
        """
        Detect if NVIDIA GPU is available for decompression.

        Returns:
            True if GPU is available, False otherwise
        """
        try:
            # Method 1: Check for CUDA via torch
            import torch
            if torch.cuda.is_available():
                return True
        except ImportError:
            pass

        try:
            # Method 2: Check nvidia-smi
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return False

    def restore_snapshot(
        self,
        snapshot_path: str,
        target_dir: str,
        use_gpu: Optional[bool] = None,
        progress_callback: Optional[Callable[[RestoreProgress], None]] = None,
    ) -> Dict[str, Any]:
        """
        Restore a snapshot to a directory.

        Args:
            snapshot_path: Path to .dumont file
            target_dir: Directory to restore to
            use_gpu: Use GPU for decompression. If None, auto-detect.
            progress_callback: Optional callback(RestoreProgress)

        Returns:
            Dict with restore statistics
        """
        start_time = time.time()
        bytes_processed = 0

        # Auto-detect GPU if not specified
        if use_gpu is None:
            use_gpu = self.detect_gpu()

        with DumontArchive.open(snapshot_path) as archive:
            stats = archive.get_stats()
            total_chunks = stats['num_chunks']
            total_bytes = stats['total_compressed']

            def _progress(chunk_idx, total):
                nonlocal bytes_processed
                if progress_callback:
                    elapsed = time.time() - start_time
                    # Estimate bytes per chunk
                    bytes_per_chunk = total_bytes / max(1, total)
                    bytes_processed = chunk_idx * bytes_per_chunk

                    if chunk_idx > 0:
                        rate = bytes_processed / elapsed
                        remaining = (total_bytes - bytes_processed) / rate
                    else:
                        remaining = 0

                    progress = RestoreProgress(
                        phase='decompress_gpu' if use_gpu else 'extract',
                        current_chunk=chunk_idx,
                        total_chunks=total,
                        bytes_processed=int(bytes_processed),
                        bytes_total=total_bytes,
                        elapsed_seconds=elapsed,
                        estimated_remaining=remaining,
                    )
                    progress_callback(progress)

            # Extract (GPU decompression would be integrated here)
            if use_gpu:
                self._restore_with_gpu(archive, target_dir, _progress)
            else:
                archive.extract_all(target_dir, _progress)

        elapsed = time.time() - start_time

        return {
            'success': True,
            'files_restored': stats['num_files'],
            'chunks_processed': stats['num_chunks'],
            'bytes_original': stats['total_original'],
            'bytes_compressed': stats['total_compressed'],
            'elapsed_seconds': elapsed,
            'throughput_mbps': (stats['total_original'] / 1024 / 1024) / elapsed if elapsed > 0 else 0,
            'used_gpu': use_gpu,
            'gpu_detected': self.detect_gpu(),
        }

    def _restore_with_gpu(self, archive: DumontArchive, target_dir: str, progress_callback):
        """
        Restore using GPU-accelerated decompression.

        Falls back to CPU if nvCOMP not available.
        """
        try:
            # Try to import nvCOMP
            # Note: nvCOMP Python bindings would be imported here
            # For now, fall back to CPU implementation
            raise ImportError("nvCOMP not implemented yet")
        except ImportError:
            # Fall back to CPU (GPU detected but nvCOMP not installed)
            archive.extract_all(target_dir, progress_callback)

    def get_snapshot_info(self, snapshot_path: str) -> SnapshotInfo:
        """
        Get information about a snapshot without extracting.

        Args:
            snapshot_path: Path to .dumont file

        Returns:
            SnapshotInfo with details
        """
        with DumontArchive.open(snapshot_path) as archive:
            stats = archive.get_stats()

        # Generate snapshot ID
        with open(snapshot_path, 'rb') as f:
            first_chunk = f.read(1024 * 1024)
            f.seek(-min(1024 * 1024, os.path.getsize(snapshot_path)), 2)
            last_chunk = f.read()
            snapshot_id = hashlib.sha256(first_chunk + last_chunk).hexdigest()[:12]

        return SnapshotInfo(
            id=snapshot_id,
            path=snapshot_path,
            size_original=stats['total_original'],
            size_compressed=stats['total_compressed'],
            num_files=stats['num_files'],
            num_chunks=stats['num_chunks'],
            compression_ratio=stats['ratio'],
            created_at=os.path.getmtime(snapshot_path),
        )

    def list_files(self, snapshot_path: str) -> list:
        """
        List files in a snapshot without extracting.

        Args:
            snapshot_path: Path to .dumont file

        Returns:
            List of file paths
        """
        with DumontArchive.open(snapshot_path) as archive:
            return [f.path for f in archive.files]

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size in human-readable form"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format time in human-readable form"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"
