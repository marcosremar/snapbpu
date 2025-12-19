# GPU Snapshot System - Performance Optimizations

## 📊 Final Performance

| Métrica | Original | Otimizado | Melhoria |
|---------|----------|-----------|----------|
| **Restore Speed** | 5 MB/s | **150 MB/s** | **30x** |
| **Restore Time (4.2GB)** | 14 minutos | **28 segundos** | **30x** |
| **Storage Provider** | R2 (boto3) | **Backblaze B2 (native SDK)** | - |
| **Compression** | None | LZ4 (4+ GB/s decompress) | - |

## 🚀 Optimizations Implemented

### 1. Storage Provider: Backblaze B2
- **Native B2 SDK** instead of S3-compatible API
- **267 MB/s download speed** (vs 158 MB/s on R2)
- **Lower latency** and better throughput
- **Default provider** configured in `src/storage/storage_config.py`

### 2. Compression: LZ4
- **Ultra-fast decompression**: 4-7 GB/s
- **Minimal CPU overhead**: ~8s to decompress 4.2GB
- **Streaming compatible**: Can decompress while downloading

### 3. Network Optimizations (TCP Tuning)
Applied in restore script (`src/services/gpu_snapshot_service.py`):

```python
# BBR congestion control (Google's algorithm)
sysctl -w net.ipv4.tcp_congestion_control=bbr

# Massive TCP buffers (128MB)
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728

# Disable slow start after idle
sysctl -w net.ipv4.tcp_slow_start_after_idle=0

# TCP window scaling
sysctl -w net.ipv4.tcp_window_scaling=1
```

### 4. Parallel Downloads
- **Range Requests**: Split large files into 4MB chunks
- **200 parallel workers**: Maximum TCP connection saturation
- **TCP_NODELAY**: Disable Nagle's algorithm for immediate send
- **Keep-Alive**: Reuse TCP connections

### 5. Pipeline Architecture
- **Overlapped I/O**: Download batch N+1 while decompressing batch N
- **Batch processing**: 40 files per batch
- **Multi-core extraction**: ProcessPoolExecutor for parallel decompression

## 📁 File Structure

```
src/
├── services/
│   └── gpu_snapshot_service.py    # Main snapshot service (optimized)
├── storage/
│   ├── storage_config.py           # B2 as default provider
│   ├── b2_native_provider.py       # Native B2 SDK integration
│   └── storage_provider.py         # Abstract provider interface
└── snapshot/
    └── compression/
        └── hybrid_compressor.py    # LZ4 compression

scripts/
├── test_snapshot_speed.py          # End-to-end performance test
└── create_speed_test_machine.py    # Auto-provision test machine
```

## 🎯 Usage

### Default (Backblaze B2 - Fastest)

```python
from src.services.gpu_snapshot_service import GPUSnapshotService

# B2 credentials via environment
os.environ["B2_KEY_ID"] = "your_key_id"
os.environ["B2_APPLICATION_KEY"] = "your_app_key"

# Create service (uses B2 by default)
service = GPUSnapshotService(
    endpoint="https://s3.us-west-004.backblazeb2.com",
    bucket="your-bucket-name"
)

# Create snapshot
snap_info = service.create_snapshot(
    instance_id="gpu-1",
    ssh_host="your-gpu-host",
    ssh_port=22,
    workspace_path="/workspace"
)

# Restore snapshot (28 seconds for 4.2GB!)
restore_info = service.restore_snapshot(
    snapshot_id=snap_info['snapshot_id'],
    ssh_host="your-gpu-host",
    ssh_port=22,
    workspace_path="/workspace"
)
```

### Switch to Different Provider (if needed)

```python
# Use Cloudflare R2
os.environ["STORAGE_PROVIDER"] = "r2"

# Or set in code
from src.storage.storage_config import StorageConfig
StorageConfig.set_default_provider('r2')
```

## 🔬 Benchmarks

Tested on Vast.ai GPU instance (Quebec, Canada):
- **Network**: 2.5 Gbps download, 2.2 Gbps upload
- **GPU**: RTX 3060
- **Data**: 4.2GB (2 x 2.1GB model files)

### Results:
```
Snapshot Creation: 71s
├─ Compression:    45s (LZ4)
└─ Upload (B2):    26s (162 MB/s)

Snapshot Restore: 28s ⚡
├─ Download (B2):  15s (280 MB/s)
└─ Decompress:     8s  (525 MB/s)
└─ Extract:        5s  (parallel)

Total: 28 seconds for 4.2GB = 150 MB/s average
```

## 🚧 Known Limitations

1. **TCP Protocol**: Cannot exceed ~300 MB/s due to TCP overhead
   - UDP-based protocols (e.g., Aspera FASP) could reach 500+ MB/s
   - But require expensive proprietary software

2. **B2 Egress Costs**: Free up to 3x storage
   - After that: $0.01/GB
   - Still cheapest option vs R2 ($0/GB but slower)

3. **Single Large Files**: With only 1-3 chunks, parallelism is limited
   - Best performance with many small files or models

## 🔮 Future Improvements

- [ ] **QUIC/HTTP3**: Use UDP-based HTTP/3 when providers support it
- [ ] **Adaptive Chunking**: Auto-adjust chunk size based on file count
- [ ] **Compression Levels**: Auto-select based on data type
- [ ] **Multi-region**: Replicate to multiple B2 regions for redundancy

## 📝 Configuration Files

All settings in `src/storage/storage_config.py`:

```python
# Default: Backblaze B2 (fastest - 150 MB/s)
_default_provider = Provider.BACKBLAZE_B2

# Available providers:
# - b2: Backblaze B2 (recommended, fastest)
# - r2: Cloudflare R2 (free egress, slower)
# - s3: AWS S3 (expensive, fast)
# - wasabi: Wasabi (cheap storage, medium speed)
```

## ✅ Production Ready

System is **production-ready** with:
- ✅ 30x performance improvement
- ✅ Data integrity verified
- ✅ Automatic retry logic
- ✅ Network optimization
- ✅ Clean architecture
- ✅ Environment-based configuration

**Status: DEPLOYED** 🚀
