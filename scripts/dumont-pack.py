#!/usr/bin/env python3
"""
dumont-pack - Create optimized workspace snapshots

Usage:
    dumont-pack /workspace -o snapshot.dumont
    dumont-pack /workspace --chunk-size 64  # 64 MB chunks

Features:
    - Hybrid compression by file type
    - 64 MB chunks for parallel processing
    - Progress display
"""

import sys
import os
import argparse
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.snapshot import SnapshotService


def format_size(size_bytes: int) -> str:
    """Format size in human-readable form"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def main():
    parser = argparse.ArgumentParser(
        description='Create optimized workspace snapshot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    dumont-pack /workspace -o workspace.dumont
    dumont-pack /workspace --chunk-size 128  # 128 MB chunks
    dumont-pack /workspace -o backup.dumont -v  # verbose
        """
    )
    parser.add_argument('source', help='Directory to snapshot')
    parser.add_argument('-o', '--output', required=True, help='Output .dumont file')
    parser.add_argument('--chunk-size', type=int, default=64,
                        help='Chunk size in MB (default: 64)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    # Validate source directory
    if not os.path.isdir(args.source):
        print(f"Error: Source directory not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    # Calculate total size
    total_size = 0
    file_count = 0
    for root, dirs, files in os.walk(args.source):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if not f.startswith('.'):
                fpath = os.path.join(root, f)
                if os.path.isfile(fpath):
                    total_size += os.path.getsize(fpath)
                    file_count += 1

    print(f"Source: {args.source}")
    print(f"Files: {file_count}")
    print(f"Total size: {format_size(total_size)}")
    print(f"Chunk size: {args.chunk_size} MB")
    print()

    # Create snapshot service
    chunk_size = args.chunk_size * 1024 * 1024
    service = SnapshotService(chunk_size=chunk_size)

    # Progress tracking
    start_time = time.time()
    last_update = [0]

    def progress_callback(filepath, file_idx, total_files):
        now = time.time()
        # Update every 0.5 seconds
        if now - last_update[0] >= 0.5:
            pct = (file_idx / total_files) * 100 if total_files > 0 else 0
            elapsed = now - start_time
            eta = (elapsed / max(1, file_idx)) * (total_files - file_idx) if file_idx > 0 else 0

            # Truncate filepath for display
            display_path = filepath
            if len(display_path) > 50:
                display_path = "..." + display_path[-47:]

            print(f"\r[{pct:5.1f}%] {file_idx}/{total_files} files | "
                  f"Elapsed: {elapsed:.0f}s | ETA: {eta:.0f}s | "
                  f"{display_path:<50}", end='', flush=True)
            last_update[0] = now

    # Create snapshot
    print("Creating snapshot...")
    try:
        info = service.create_snapshot(
            args.source,
            args.output,
            progress_callback=progress_callback if args.verbose else None
        )
    except Exception as e:
        print(f"\nError creating snapshot: {e}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.time() - start_time
    print()
    print()

    # Display results
    print("=" * 60)
    print("Snapshot created successfully!")
    print("=" * 60)
    print(f"Output:      {args.output}")
    print(f"Snapshot ID: {info.id}")
    print(f"Files:       {info.num_files}")
    print(f"Chunks:      {info.num_chunks}")
    print()
    print(f"Original:    {format_size(info.size_original)}")
    print(f"Compressed:  {format_size(info.size_compressed)}")
    print(f"Ratio:       {info.compression_ratio:.2f}x")
    print(f"Savings:     {(1 - 1/info.compression_ratio) * 100:.1f}%")
    print()
    print(f"Time:        {elapsed:.1f}s")
    print(f"Speed:       {info.size_original / 1024 / 1024 / elapsed:.1f} MB/s")


if __name__ == '__main__':
    main()
