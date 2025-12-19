#!/usr/bin/env python3
"""
dumont-restore - Restore workspace from snapshot

Usage:
    dumont-restore snapshot.dumont /workspace
    dumont-restore snapshot.dumont /workspace --gpu  # Use GPU decompression
    dumont-restore snapshot.dumont --info  # Show snapshot info

Features:
    - GPU-accelerated decompression (with nvCOMP)
    - Progress display
    - Resume support
"""

import sys
import os
import argparse
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.snapshot import SnapshotService
from src.snapshot.snapshot_service import RestoreProgress


def format_size(size_bytes: int) -> str:
    """Format size in human-readable form"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def show_info(snapshot_path: str):
    """Show information about a snapshot"""
    service = SnapshotService()
    info = service.get_snapshot_info(snapshot_path)

    print("=" * 60)
    print("Snapshot Information")
    print("=" * 60)
    print(f"File:        {snapshot_path}")
    print(f"Snapshot ID: {info.id}")
    print(f"Files:       {info.num_files}")
    print(f"Chunks:      {info.num_chunks}")
    print()
    print(f"Original:    {format_size(info.size_original)}")
    print(f"Compressed:  {format_size(info.size_compressed)}")
    print(f"Ratio:       {info.compression_ratio:.2f}x")
    print(f"Savings:     {(1 - 1/info.compression_ratio) * 100:.1f}%")
    print()

    # List files (first 20)
    files = service.list_files(snapshot_path)
    print(f"Files ({len(files)} total):")
    for f in files[:20]:
        print(f"  {f}")
    if len(files) > 20:
        print(f"  ... and {len(files) - 20} more")


def main():
    parser = argparse.ArgumentParser(
        description='Restore workspace from snapshot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    dumont-restore snapshot.dumont /workspace
    dumont-restore snapshot.dumont /workspace --gpu
    dumont-restore snapshot.dumont --info
    dumont-restore snapshot.dumont --list
        """
    )
    parser.add_argument('snapshot', help='Path to .dumont snapshot file')
    parser.add_argument('target', nargs='?', help='Target directory to restore to')
    parser.add_argument('--gpu', action='store_true', default=None,
                        help='Force GPU decompression (auto-detected by default)')
    parser.add_argument('--no-gpu', action='store_true',
                        help='Disable GPU decompression')
    parser.add_argument('--info', action='store_true',
                        help='Show snapshot information')
    parser.add_argument('--list', action='store_true',
                        help='List files in snapshot')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    # Validate snapshot file
    if not os.path.isfile(args.snapshot):
        print(f"Error: Snapshot file not found: {args.snapshot}", file=sys.stderr)
        sys.exit(1)

    # Info mode
    if args.info:
        show_info(args.snapshot)
        return

    # List mode
    if args.list:
        service = SnapshotService()
        files = service.list_files(args.snapshot)
        for f in files:
            print(f)
        return

    # Restore mode
    if not args.target:
        print("Error: Target directory required for restore", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    service = SnapshotService()
    info = service.get_snapshot_info(args.snapshot)

    # Determine GPU usage
    if args.no_gpu:
        use_gpu = False
    elif args.gpu:
        use_gpu = True
    else:
        use_gpu = None  # Auto-detect

    # Detect GPU for display
    gpu_detected = service.detect_gpu()

    print("=" * 60)
    print("Restoring Snapshot")
    print("=" * 60)
    print(f"Source:      {args.snapshot}")
    print(f"Target:      {args.target}")
    print(f"Snapshot ID: {info.id}")
    print(f"Files:       {info.num_files}")
    print(f"Chunks:      {info.num_chunks}")
    print(f"Size:        {format_size(info.size_original)} "
          f"(compressed: {format_size(info.size_compressed)})")
    print(f"GPU detected: {'Yes' if gpu_detected else 'No'}")
    if use_gpu is None:
        print(f"GPU mode:    Auto ({'enabled' if gpu_detected else 'disabled'})")
    else:
        print(f"GPU mode:    {'Forced ON' if use_gpu else 'Forced OFF'}")
    print()

    # Progress tracking
    start_time = time.time()
    last_update = [0]

    def progress_callback(progress: RestoreProgress):
        now = time.time()
        # Update every 0.3 seconds
        if now - last_update[0] >= 0.3:
            pct = (progress.current_chunk / progress.total_chunks) * 100 if progress.total_chunks > 0 else 0

            # Speed calculation
            if progress.elapsed_seconds > 0:
                speed = progress.bytes_processed / progress.elapsed_seconds / 1024 / 1024
            else:
                speed = 0

            print(f"\r[{pct:5.1f}%] Chunk {progress.current_chunk}/{progress.total_chunks} | "
                  f"{format_size(progress.bytes_processed)}/{format_size(progress.bytes_total)} | "
                  f"{speed:.1f} MB/s | "
                  f"Elapsed: {progress.elapsed_seconds:.0f}s | "
                  f"ETA: {progress.estimated_remaining:.0f}s", end='', flush=True)
            last_update[0] = now

    # Restore
    print("Restoring...")
    try:
        result = service.restore_snapshot(
            args.snapshot,
            args.target,
            use_gpu=use_gpu,
            progress_callback=progress_callback if args.verbose else None
        )
    except Exception as e:
        print(f"\nError restoring snapshot: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print()

    # Display results
    print("=" * 60)
    print("Restore completed successfully!")
    print("=" * 60)
    print(f"Files restored:   {result['files_restored']}")
    print(f"Chunks processed: {result['chunks_processed']}")
    print(f"Data restored:    {format_size(result['bytes_original'])}")
    print(f"Time:             {result['elapsed_seconds']:.1f}s")
    print(f"Throughput:       {result['throughput_mbps']:.1f} MB/s")
    print(f"GPU detected:     {'Yes' if result.get('gpu_detected', False) else 'No'}")
    print(f"GPU used:         {'Yes' if result['used_gpu'] else 'No'}")


if __name__ == '__main__':
    main()
