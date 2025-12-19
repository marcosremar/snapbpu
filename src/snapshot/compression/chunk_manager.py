"""
Chunk Manager - Handles splitting and reassembling data into chunks

Features:
- Configurable chunk size (default 64 MB)
- Streaming processing for large files
- Progress tracking
"""

import os
from typing import Iterator, Tuple, Optional, BinaryIO
from pathlib import Path
from dataclasses import dataclass

DEFAULT_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB


@dataclass
class ChunkMetadata:
    """Metadata for a chunk"""
    index: int
    size: int
    offset: int  # Offset in original stream


class ChunkManager:
    """
    Manages splitting data into fixed-size chunks.

    Usage:
        manager = ChunkManager(chunk_size=64 * 1024 * 1024)

        # Split a file into chunks
        for chunk_data, metadata in manager.split_file("/path/to/file"):
            process(chunk_data)

        # Split bytes into chunks
        for chunk_data, metadata in manager.split_bytes(large_bytes):
            process(chunk_data)
    """

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize chunk manager.

        Args:
            chunk_size: Size of each chunk in bytes (default 64 MB)
        """
        self.chunk_size = chunk_size

    def split_bytes(self, data: bytes) -> Iterator[Tuple[bytes, ChunkMetadata]]:
        """
        Split bytes into chunks.

        Args:
            data: Bytes to split

        Yields:
            Tuple of (chunk_data, metadata)
        """
        offset = 0
        index = 0

        while offset < len(data):
            chunk = data[offset:offset + self.chunk_size]
            metadata = ChunkMetadata(
                index=index,
                size=len(chunk),
                offset=offset,
            )
            yield chunk, metadata

            offset += len(chunk)
            index += 1

    def split_file(self, filepath: str) -> Iterator[Tuple[bytes, ChunkMetadata]]:
        """
        Split a file into chunks.

        Args:
            filepath: Path to file

        Yields:
            Tuple of (chunk_data, metadata)
        """
        with open(filepath, 'rb') as f:
            offset = 0
            index = 0

            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break

                metadata = ChunkMetadata(
                    index=index,
                    size=len(chunk),
                    offset=offset,
                )
                yield chunk, metadata

                offset += len(chunk)
                index += 1

    def split_stream(self, stream: BinaryIO, total_size: Optional[int] = None) -> Iterator[Tuple[bytes, ChunkMetadata]]:
        """
        Split a stream into chunks.

        Args:
            stream: Binary stream to read from
            total_size: Optional total size (for progress tracking)

        Yields:
            Tuple of (chunk_data, metadata)
        """
        offset = 0
        index = 0

        while True:
            chunk = stream.read(self.chunk_size)
            if not chunk:
                break

            metadata = ChunkMetadata(
                index=index,
                size=len(chunk),
                offset=offset,
            )
            yield chunk, metadata

            offset += len(chunk)
            index += 1

    def reassemble_bytes(self, chunks: Iterator[bytes]) -> bytes:
        """
        Reassemble chunks into original bytes.

        Args:
            chunks: Iterator of chunk data

        Returns:
            Reassembled bytes
        """
        return b''.join(chunks)

    def reassemble_to_file(self, chunks: Iterator[bytes], filepath: str):
        """
        Reassemble chunks directly to a file.

        Args:
            chunks: Iterator of chunk data
            filepath: Path to write to
        """
        with open(filepath, 'wb') as f:
            for chunk in chunks:
                f.write(chunk)

    @staticmethod
    def calculate_num_chunks(total_size: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> int:
        """
        Calculate number of chunks needed for a given size.

        Args:
            total_size: Total bytes
            chunk_size: Chunk size

        Returns:
            Number of chunks
        """
        return (total_size + chunk_size - 1) // chunk_size

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size in human-readable form"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
