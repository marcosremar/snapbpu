"""
Dumont Archive Format (.dumont)

Binary format optimized for:
- Chunked storage (64 MB default)
- Independent chunk decompression
- Resume support
- GPU-friendly decompression

Structure:
    [Header 512 bytes]
    [Chunk Index]
    [File Manifest (LZ4 compressed)]
    [Chunk Data...]
"""

import struct
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, BinaryIO, Iterator, Tuple
from pathlib import Path
import zlib

try:
    import lz4.frame
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False

from .hybrid_compressor import Compressor


# Constants
MAGIC = b"DUMONT01"
VERSION = 1
HEADER_SIZE = 512
DEFAULT_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB


@dataclass
class ChunkInfo:
    """Information about a single chunk"""
    index: int
    offset: int              # Offset in file
    size_compressed: int     # Size after compression
    size_original: int       # Size before compression
    compressor_id: int       # 0=none, 1=lz4, 2=lz4_hc, 3=zipnn
    checksum: int            # CRC32 of compressed data

    def to_bytes(self) -> bytes:
        """Serialize to bytes (21 bytes total)"""
        return struct.pack(
            "<QIIBI",
            self.offset,
            self.size_compressed,
            self.size_original,
            self.compressor_id,
            self.checksum,
        )

    @classmethod
    def from_bytes(cls, data: bytes, index: int) -> 'ChunkInfo':
        """Deserialize from bytes"""
        offset, size_compressed, size_original, compressor_id, checksum = struct.unpack(
            "<QIIBI", data[:21]
        )
        return cls(
            index=index,
            offset=offset,
            size_compressed=size_compressed,
            size_original=size_original,
            compressor_id=compressor_id,
            checksum=checksum,
        )

    STRUCT_SIZE = 21


@dataclass
class FileEntry:
    """Information about a file in the archive"""
    path: str                # Relative path
    size: int               # Original size
    mode: int               # File permissions
    mtime: float            # Modification time
    chunk_start: int        # First chunk index
    chunk_end: int          # Last chunk index (exclusive)
    compressor_id: int      # Compressor used


@dataclass
class DumontHeader:
    """Archive header (512 bytes)"""
    magic: bytes = MAGIC
    version: int = VERSION
    flags: int = 0
    num_chunks: int = 0
    num_files: int = 0
    total_size_compressed: int = 0
    total_size_original: int = 0
    checksum_type: int = 1  # 1 = CRC32
    chunk_size: int = DEFAULT_CHUNK_SIZE
    manifest_offset: int = 0
    manifest_size: int = 0

    def to_bytes(self) -> bytes:
        """Serialize header to 512 bytes"""
        # Format: magic(8) version(2) flags(2) num_chunks(4) num_files(4)
        #         compressed(8) original(8) checksum_type(1) pad(3) chunk_size(4)
        #         manifest_offset(8) manifest_size(4)
        header = struct.pack(
            "<8sHHIIQQBxxxIQI",
            self.magic,
            self.version,
            self.flags,
            self.num_chunks,
            self.num_files,
            self.total_size_compressed,
            self.total_size_original,
            self.checksum_type,
            self.chunk_size,
            self.manifest_offset,
            self.manifest_size,
        )
        # Pad to 512 bytes
        return header.ljust(HEADER_SIZE, b'\x00')

    @classmethod
    def from_bytes(cls, data: bytes) -> 'DumontHeader':
        """Deserialize from bytes"""
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Header too short: {len(data)} < {HEADER_SIZE}")

        # Same format as to_bytes
        magic, version, flags, num_chunks, num_files, total_compressed, total_original, \
            checksum_type, chunk_size, manifest_offset, manifest_size = struct.unpack(
                "<8sHHIIQQBxxxIQI", data[:56]
            )

        if magic != MAGIC:
            raise ValueError(f"Invalid magic: {magic}")

        return cls(
            magic=magic,
            version=version,
            flags=flags,
            num_chunks=num_chunks,
            num_files=num_files,
            total_size_compressed=total_compressed,
            total_size_original=total_original,
            checksum_type=checksum_type,
            chunk_size=chunk_size,
            manifest_offset=manifest_offset,
            manifest_size=manifest_size,
        )


class DumontArchive:
    """
    Read/write Dumont archives (.dumont).

    For creating:
        with DumontArchive.create("archive.dumont") as archive:
            archive.add_directory("/workspace")

    For reading:
        with DumontArchive.open("archive.dumont") as archive:
            for chunk in archive.iter_chunks():
                # Process chunk
                pass
            archive.extract_all("/workspace")
    """

    def __init__(self, path: str, mode: str = 'r'):
        self.path = path
        self.mode = mode
        self.header: Optional[DumontHeader] = None
        self.chunks: List[ChunkInfo] = []
        self.files: List[FileEntry] = []
        self._file: Optional[BinaryIO] = None
        self._compressor = None

    def __enter__(self):
        if self.mode == 'r':
            self._file = open(self.path, 'rb')
            self._read_header()
        elif self.mode == 'w':
            self._file = open(self.path, 'wb')
            self.header = DumontHeader()
            # Initialize compressor for writing
            from .hybrid_compressor import HybridCompressor
            self._compressor = HybridCompressor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            self._file.close()

    @classmethod
    def create(cls, path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> 'DumontArchive':
        """Create a new archive for writing"""
        archive = cls(path, 'w')
        archive.header = DumontHeader(chunk_size=chunk_size)
        return archive

    @classmethod
    def open(cls, path: str) -> 'DumontArchive':
        """Open an existing archive for reading"""
        return cls(path, 'r')

    def _read_header(self):
        """Read and parse archive header"""
        self._file.seek(0)
        header_data = self._file.read(HEADER_SIZE)
        self.header = DumontHeader.from_bytes(header_data)

        # Read chunk index
        chunk_index_size = self.header.num_chunks * ChunkInfo.STRUCT_SIZE
        chunk_data = self._file.read(chunk_index_size)

        self.chunks = []
        for i in range(self.header.num_chunks):
            offset = i * ChunkInfo.STRUCT_SIZE
            chunk = ChunkInfo.from_bytes(chunk_data[offset:offset + ChunkInfo.STRUCT_SIZE], i)
            self.chunks.append(chunk)

        # Read manifest
        self._file.seek(self.header.manifest_offset)
        manifest_compressed = self._file.read(self.header.manifest_size)

        if HAS_LZ4:
            manifest_data = lz4.frame.decompress(manifest_compressed)
        else:
            # Fallback: assume uncompressed
            manifest_data = manifest_compressed

        manifest = json.loads(manifest_data.decode('utf-8'))
        self.files = [
            FileEntry(
                path=f['path'],
                size=f['size'],
                mode=f['mode'],
                mtime=f['mtime'],
                chunk_start=f['chunk_start'],
                chunk_end=f['chunk_end'],
                compressor_id=f['compressor_id'],
            )
            for f in manifest['files']
        ]

    def read_chunk(self, chunk_index: int) -> bytes:
        """Read and decompress a single chunk"""
        if chunk_index >= len(self.chunks):
            raise IndexError(f"Chunk {chunk_index} out of range")

        chunk = self.chunks[chunk_index]
        self._file.seek(chunk.offset)
        compressed_data = self._file.read(chunk.size_compressed)

        # Verify checksum
        actual_crc = zlib.crc32(compressed_data) & 0xFFFFFFFF
        if actual_crc != chunk.checksum:
            raise ValueError(f"Chunk {chunk_index} checksum mismatch: {actual_crc} != {chunk.checksum}")

        # Decompress
        from .hybrid_compressor import HybridCompressor, Compressor
        compressor = HybridCompressor()
        comp_enum = compressor.get_compressor_from_id(chunk.compressor_id)
        return compressor.decompress(compressed_data, comp_enum)

    def iter_chunks(self) -> Iterator[Tuple[int, bytes]]:
        """Iterate over all chunks, yielding (index, data)"""
        for i in range(len(self.chunks)):
            yield i, self.read_chunk(i)

    def extract_all(self, target_dir: str, progress_callback=None):
        """
        Extract all files to target directory.

        Args:
            target_dir: Directory to extract to
            progress_callback: Optional callback(chunk_index, total_chunks)
        """
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)

        # Build chunk -> file mapping
        chunk_data = {}
        for i, data in self.iter_chunks():
            chunk_data[i] = data
            if progress_callback:
                progress_callback(i, len(self.chunks))

        # Reconstruct files
        for file_entry in self.files:
            file_path = target / file_entry.path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Combine chunks for this file
            file_bytes = b''
            for chunk_idx in range(file_entry.chunk_start, file_entry.chunk_end):
                file_bytes += chunk_data[chunk_idx]

            # Truncate to actual file size
            file_bytes = file_bytes[:file_entry.size]

            # Write file
            with open(file_path, 'wb') as f:
                f.write(file_bytes)

            # Restore permissions and mtime
            os.chmod(file_path, file_entry.mode)
            os.utime(file_path, (file_entry.mtime, file_entry.mtime))

    def add_directory(self, source_dir: str, progress_callback=None):
        """
        Add all files from a directory to the archive.

        Args:
            source_dir: Directory to archive
            progress_callback: Optional callback(file_path, file_index, total_files)
        """
        if self.mode != 'w':
            raise RuntimeError("Archive not opened for writing")

        source = Path(source_dir)
        if not source.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        # Collect all files
        all_files = []
        for root, dirs, files in os.walk(source):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in files:
                if fname.startswith('.'):
                    continue
                fpath = Path(root) / fname
                if fpath.is_file():
                    all_files.append(fpath)

        total_files = len(all_files)
        total_original = 0
        total_compressed = 0

        # First pass: compress all files and collect chunk data in memory
        all_chunk_data = []  # List of (compressed_bytes, compressor_id, original_size)

        for file_idx, fpath in enumerate(all_files):
            if progress_callback:
                progress_callback(str(fpath), file_idx, total_files)

            # Read file
            with open(fpath, 'rb') as f:
                file_data = f.read()

            # Get file info
            stat = fpath.stat()
            rel_path = str(fpath.relative_to(source))

            # Determine compression strategy
            compressed_data, strategy = self._compressor.compress_file(file_data, str(fpath))
            compressor_id = self._compressor.get_compressor_id(strategy.compressor)

            # Track chunk indices for this file
            chunk_start = len(all_chunk_data)

            # Split into chunks
            offset = 0
            while offset < len(compressed_data):
                chunk_bytes = compressed_data[offset:offset + self.header.chunk_size]

                # Calculate original size for this chunk
                if strategy.compressor != Compressor.NONE and len(compressed_data) > 0:
                    ratio = len(file_data) / len(compressed_data)
                    orig_chunk_size = int(len(chunk_bytes) * ratio)
                else:
                    orig_chunk_size = len(chunk_bytes)

                all_chunk_data.append((chunk_bytes, compressor_id, orig_chunk_size))
                total_compressed += len(chunk_bytes)
                offset += len(chunk_bytes)

            chunk_end = len(all_chunk_data)
            total_original += len(file_data)

            # Create file entry
            file_entry = FileEntry(
                path=rel_path,
                size=len(file_data),
                mode=stat.st_mode,
                mtime=stat.st_mtime,
                chunk_start=chunk_start,
                chunk_end=chunk_end,
                compressor_id=compressor_id,
            )
            self.files.append(file_entry)

        # Now write everything in correct order:
        # [Header 512b] [Chunk Index] [Chunk Data...] [Manifest]

        num_chunks = len(all_chunk_data)
        chunk_index_size = num_chunks * ChunkInfo.STRUCT_SIZE

        # Calculate where chunk data starts
        chunk_data_start = HEADER_SIZE + chunk_index_size

        # Build chunk info with correct offsets
        current_offset = chunk_data_start
        for i, (chunk_bytes, compressor_id, orig_size) in enumerate(all_chunk_data):
            checksum = zlib.crc32(chunk_bytes) & 0xFFFFFFFF
            chunk_info = ChunkInfo(
                index=i,
                offset=current_offset,
                size_compressed=len(chunk_bytes),
                size_original=orig_size,
                compressor_id=compressor_id,
                checksum=checksum,
            )
            self.chunks.append(chunk_info)
            current_offset += len(chunk_bytes)

        # Write header (placeholder, will rewrite at end)
        self._file.write(b'\x00' * HEADER_SIZE)

        # Write chunk index
        for chunk in self.chunks:
            self._file.write(chunk.to_bytes())

        # Write chunk data
        for chunk_bytes, _, _ in all_chunk_data:
            self._file.write(chunk_bytes)

        # Write manifest
        manifest = {
            'files': [
                {
                    'path': f.path,
                    'size': f.size,
                    'mode': f.mode,
                    'mtime': f.mtime,
                    'chunk_start': f.chunk_start,
                    'chunk_end': f.chunk_end,
                    'compressor_id': f.compressor_id,
                }
                for f in self.files
            ]
        }
        manifest_json = json.dumps(manifest).encode('utf-8')
        if HAS_LZ4:
            manifest_compressed = lz4.frame.compress(manifest_json)
        else:
            manifest_compressed = manifest_json

        manifest_offset = self._file.tell()
        self._file.write(manifest_compressed)

        # Update and write header at beginning
        self.header.num_chunks = num_chunks
        self.header.num_files = len(self.files)
        self.header.total_size_compressed = total_compressed
        self.header.total_size_original = total_original
        self.header.manifest_offset = manifest_offset
        self.header.manifest_size = len(manifest_compressed)

        self._file.seek(0)
        self._file.write(self.header.to_bytes())

    def get_stats(self) -> dict:
        """Get archive statistics"""
        return {
            'num_files': self.header.num_files,
            'num_chunks': self.header.num_chunks,
            'total_original': self.header.total_size_original,
            'total_compressed': self.header.total_size_compressed,
            'ratio': round(self.header.total_size_original / max(1, self.header.total_size_compressed), 2),
            'chunk_size': self.header.chunk_size,
        }
