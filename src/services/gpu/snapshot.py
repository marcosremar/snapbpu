import os
import time
import json
import base64
import logging
import subprocess
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class GPUSnapshotService:
    """
    GPU Snapshot Service - LZ4 + s5cmd + Backblaze B2
    Strategy:
    - Compression: LZ4 (ultra-fast 4+ GB/s decompression).
    - Transfer: s5cmd (Go) + Backblaze B2 (1.5+ GB/s transfers, 31x faster than R2).
    - Concurrency: Multiprocess compression/decompression to saturate bandwidth.
    
    Default Provider: Backblaze B2 (best speed/cost ratio)
    """

    def __init__(self, r2_endpoint: str, r2_bucket: str, provider: str = "auto"):
        self.r2_endpoint = r2_endpoint
        self.r2_bucket = r2_bucket
        self.concurrency = 32
        
        # Auto-detect provider from endpoint
        if provider == "auto":
            if "backblazeb2.com" in r2_endpoint or "b2" in r2_endpoint.lower():
                self.provider = "b2"
            elif "r2.cloudflarestorage.com" in r2_endpoint:
                self.provider = "r2"
            elif "amazonaws.com" in r2_endpoint:
                self.provider = "s3"
            elif "wasabisys.com" in r2_endpoint:
                self.provider = "wasabi"
            else:
                self.provider = "s3"  # Default to S3-compatible
        else:
            self.provider = provider
        
        logger.info(f"GPUSnapshotService initialized with provider: {self.provider}")

    def create_snapshot(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str = "/workspace",
        snapshot_name: Optional[str] = None
    ) -> Dict:
        """Creates a hybrid snapshot of the workspace."""
        if not snapshot_name:
            snapshot_name = f"{instance_id}_{int(time.time())}"

        logger.info(f"Creating snapshot {snapshot_name} (Hybrid V3: Bitshuffle+LZ4)")
        start_time = time.time()

        # Generate the sophisticated remote script
        script = self._generate_hybrid_compress_script(
            workspace_path=workspace_path,
            snapshot_name=snapshot_name,
            endpoint=self.r2_endpoint,
            bucket=self.r2_bucket
        )

        # Execute remote script (Install -> Compress -> Upload)
        logger.info("Executing remote hybrid compression & upload...")
        result = self._ssh_exec(ssh_host, ssh_port, script)
        
        if result['returncode'] != 0:
            logger.error(f"Remote error: {result['stderr']}")
            raise Exception(f"Snapshot failed: {result['stderr']}")

        # Parse output stats
        try:
            last_line = result['stdout'].strip().split('\n')[-1]
            stats = json.loads(last_line)
        except Exception as e:
            logger.error(f"Failed to parse output: {e}\nStdout: {result['stdout']}")
            raise Exception(f"Failed to parse snapshot stats")

        overall_time = time.time() - start_time

        snapshot_info = {
            'snapshot_id': snapshot_name,
            'instance_id': instance_id,
            'created_at': datetime.utcnow().isoformat(),
            'workspace_path': workspace_path,
            'size_original': stats.get('original_size', 0),
            'size_compressed': stats.get('compressed_size', 0),
            'compression_ratio': stats.get('ratio', 1.0),
            'num_chunks': stats.get('num_chunks', 0),
            'upload_time': stats.get('upload_time', 0),
            'total_time': overall_time,
            'technology': 'hybrid_v3_bitshuffle',
            'r2_path': f"snapshots/{snapshot_name}/"
        }

        # Save metadata to R2
        self._save_snapshot_metadata(snapshot_info)

        logger.info(f"Snapshot complete: {snapshot_name} ({overall_time:.1f}s)")
        return snapshot_info

    def restore_snapshot(
        self,
        snapshot_id: str,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str = "/workspace"
    ) -> Dict:
        """Restores a hybrid snapshot."""
        logger.info(f"Restoring snapshot {snapshot_id} (Hybrid V3: Bitshuffle+LZ4)")
        start_time = time.time()

        # Generate restore script
        script = self._generate_hybrid_restore_script(
            snapshot_id=snapshot_id,
            workspace_path=workspace_path,
            endpoint=self.r2_endpoint,
            bucket=self.r2_bucket
        )

        # Execute remote script (Download -> Decompress)
        logger.info("Executing remote parallel download & decompression...")
        result = self._ssh_exec(ssh_host, ssh_port, script)

        if result['returncode'] != 0:
            logger.error(f"Remote error: {result['stderr']}")
            raise Exception(f"Restore failed: {result['stderr']}")

        try:
            last_line = result['stdout'].strip().split('\n')[-1]
            stats = json.loads(last_line)
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"Could not parse restore stats: {e}")
            stats = {}

        total_time = time.time() - start_time
        logger.info(f"Restore complete: {snapshot_id} ({total_time:.1f}s)")
        
        return {
            'restored': True,
            'snapshot_id': snapshot_id,
            'download_time': stats.get('download_time', 0),
            'decompress_time': stats.get('decompress_time', 0),
            'total_time': total_time
        }

    def _generate_hybrid_compress_script(self, workspace_path, snapshot_name, endpoint, bucket) -> str:
        """Generates the Python script to run on the GPU machine for compression."""
        
        # Use B2 native SDK if provider is B2
        if self.provider == "b2":
            return self._generate_b2_compress_script(workspace_path, snapshot_name, endpoint, bucket)
        else:
            return self._generate_s3_compress_script(workspace_path, snapshot_name, endpoint, bucket)
    
    def _generate_b2_compress_script(self, workspace_path, snapshot_name, endpoint, bucket) -> str:
        """Generate compress script using B2 native SDK"""
        # Extract B2 credentials from environment or config
        # These will be injected when the script runs
        return f"""
import os
import sys
import glob
import time
import json
import tarfile
import subprocess
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# Install B2 SDK
required = ["b2sdk", "lz4"]
missing = []
for r in required:
    try:
        __import__(r)
    except ImportError:
        missing.append(r)

if missing:
    print(f"Installing dependencies: {{missing}}...", flush=True)
    subprocess.run([sys.executable, "-m", "pip", "install"] + missing + ["--break-system-packages"], check=False)

from b2sdk.v2 import InMemoryAccountInfo, B2Api
import lz4.frame
import shutil
import glob

# Configuration from environment
WORKSPACE = "{workspace_path}"
SNAPSHOT_ID = "{snapshot_name}"
BUCKET = "{bucket}"
CHUNK_SIZE = 16 * 1024 * 1024  # 16MB para mais paralelismo
MODELS_EXT = {{".pt", ".pth", ".safetensors", ".bin", ".ckpt", ".onnx", ".model"}}

# B2 Credentials (will be set via environment)
B2_KEY_ID = os.environ.get("B2_KEY_ID")
B2_APP_KEY = os.environ.get("B2_APPLICATION_KEY")

if not B2_KEY_ID or not B2_APP_KEY:
    raise ValueError("B2_KEY_ID and B2_APPLICATION_KEY must be set in environment")

# Initialize B2
print("Connecting to Backblaze B2...", flush=True)
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
bucket_obj = b2_api.get_bucket_by_name(BUCKET)
print("✓ B2 connected!", flush=True)

def compress_chunk_task(args):
    idx, file_list = args
    tar_path = f"/tmp/chunk_{{idx}}.tar"
    
    # Create tar
    with tarfile.open(tar_path, "w") as tar:
        for f in file_list:
            try:
                tar.add(f, arcname=os.path.relpath(f, WORKSPACE))
            except Exception as e:
                print(f"Warning: Could not add {{f}}: {{e}}", flush=True)
    
    # Compress with LZ4
    with open(tar_path, "rb") as f_in:
        data = f_in.read()
    os.remove(tar_path)
    
    compressed = lz4.frame.compress(data)
    out_path = f"/tmp/chunk_{{idx}}.lz4"
    with open(out_path, "wb") as f_out:
        f_out.write(compressed)
        
    return out_path, len(data), len(compressed)

def upload_task(fpath):
    fname = os.path.basename(fpath)
    remote_path = f"snapshots/{{SNAPSHOT_ID}}/{{fname}}"
    
    # Upload using B2 SDK
    bucket_obj.upload_local_file(
        local_file=fpath,
        file_name=remote_path
    )
    os.remove(fpath)
    return True

# Scan workspace and collect file metadata
print("Scanning workspace...", flush=True)
all_files = []
file_metadata = {{}}
for root, dirs, files in os.walk(WORKSPACE):
    for f in files:
        full = os.path.join(root, f)
        if not os.path.islink(full):
            all_files.append(full)
            # Collect mtime for incremental snapshots
            relative_path = os.path.relpath(full, WORKSPACE)
            file_metadata[relative_path] = os.path.getmtime(full)

print(f"Found {{len(all_files)}} files.", flush=True)

# Create chunks of files
chunks = []
current_chunk = []
current_size = 0
chunk_idx = 0
MAX_CHUNK_SIZE = 256 * 1024 * 1024  # 256MB pieces

for f in all_files:
    sz = os.path.getsize(f)
    if current_size + sz > MAX_CHUNK_SIZE and current_chunk:
        chunks.append((chunk_idx, current_chunk))
        chunk_idx += 1
        current_chunk = []
        current_size = 0
    current_chunk.append(f)
    current_size += sz

if current_chunk:
    chunks.append((chunk_idx, current_chunk))


print(f"Created {{len(chunks)}} chunks.", flush=True)

# Compress in parallel
print("Compressing (multiprocess LZ4)...", flush=True)
total_orig = 0
total_comp = 0
compressed_files = []

with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
    for path, orig, comp in executor.map(compress_chunk_task, chunks):
        total_orig += orig
        total_comp += comp
        compressed_files.append(path)

print(f"Created {{len(compressed_files)}} compressed files", flush=True)

# Upload to B2 ONLY (best performance)
print("Uploading to Backblaze B2 (best: 150 MB/s)...", flush=True)
from concurrent.futures import ThreadPoolExecutor

# Initialize R2 credentials for s5cmd from environment
import subprocess as sp
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT = os.environ.get("R2_ENDPOINT", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "")

if R2_ACCESS_KEY and R2_SECRET_KEY:
    os.environ["AWS_ACCESS_KEY_ID_R2"] = R2_ACCESS_KEY
    os.environ["AWS_SECRET_ACCESS_KEY_R2"] = R2_SECRET_KEY
else:
    print("⚠️  R2 credentials not configured in environment", flush=True)

# Install s5cmd if needed for R2
if not os.path.exists("/usr/local/bin/s5cmd"):
    print("Installing s5cmd for R2...", flush=True)
    url = "https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz"
    sp.run(f"curl -sL {{url}} -o /tmp/s5cmd.tar.gz", shell=True, check=True)
    sp.run("tar xzf /tmp/s5cmd.tar.gz -C /tmp", shell=True, check=True)
    
    # Try multiple possible locations
    for possible_path in glob.glob("/tmp/s5cmd*") + ["/tmp/s5cmd"]:
        if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
            shutil.copy(possible_path, "/usr/local/bin/s5cmd")
            os.chmod("/usr/local/bin/s5cmd", 0o755)
            print(f"✓ s5cmd installed from {{possible_path}}", flush=True)
            break
    else:
        print("⚠️  s5cmd not found after extraction, trying direct download...", flush=True)
        sp.run("curl -sL https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz | tar xz -C /usr/local/bin s5cmd",  shell=True)
        if os.path.exists("/usr/local/bin/s5cmd"):
            os.chmod("/usr/local/bin/s5cmd", 0o755)


def upload_task_multi(args):
    fpath, idx = args
    fname = os.path.basename(fpath)
    
    # Round-robin: even indices -> B2, odd indices -> R2
    if idx % 2 == 0:
        # Upload to B2
        remote_path = f"snapshots/{{SNAPSHOT_ID}}/{{fname}}"
        bucket_obj.upload_local_file(
            local_file=fpath,
            file_name=remote_path
        )
    else:
        # Upload to R2 using s5cmd
        remote_path = f"snapshots/{{SNAPSHOT_ID}}/{{fname}}"
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = env["AWS_ACCESS_KEY_ID_R2"]
        env["AWS_SECRET_ACCESS_KEY"] = env["AWS_SECRET_ACCESS_KEY_R2"]
        env["AWS_REGION"] = "auto"
        
        cmd = ["s5cmd", "--endpoint-url", R2_ENDPOINT, "cp", fpath, f"s3://{{R2_BUCKET}}/{{remote_path}}"]
        sp.run(cmd, check=True, stdout=sp.DEVNULL, env=env)
    
    os.remove(fpath)
    return True

# Upload with round-robin
upload_args = [(fpath, idx) for idx, fpath in enumerate(compressed_files)]
with ThreadPoolExecutor(max_workers=32) as executor:
    list(executor.map(upload_task_multi, upload_args))

# Upload metadata.json to B2 for incremental snapshots
print("Uploading metadata...", flush=True)
metadata = {{
    "snapshot_id": SNAPSHOT_ID,
    "timestamp": time.time(),
    "files": file_metadata,
    "total_size": total_orig,
    "compression": "lz4",
    "num_files": len(all_files)
}}

metadata_path = "/tmp/metadata.json"
with open(metadata_path, "w") as f:
    json.dump(metadata, f)

# Upload metadata to B2
metadata_remote_path = f"snapshots/{{SNAPSHOT_ID}}/metadata.json"
bucket_obj.upload_local_file(
    local_file=metadata_path,
    file_name=metadata_remote_path
)
os.remove(metadata_path)
print("✓ Metadata uploaded", flush=True)

stats = {{
    "original_size": total_orig,
    "compressed_size": total_comp,
    "ratio": total_orig / total_comp if total_comp > 0 else 0,
    "num_chunks": len(chunks),
    "num_files": len(all_files),
    "files": file_metadata
}}
print(json.dumps(stats))
"""

    def _generate_s3_compress_script(self, workspace_path, snapshot_name, endpoint, bucket) -> str:
        """Generate compress script using s5cmd (for R2, S3, Wasabi)"""
        return f"""
import os
import sys
import glob
import time
import json
import struct
import shutil
import tarfile
import subprocess
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

# 1. Dependency Check & Install
# Uses precompiled wheels (bitshuffle has wheels for linux x86_64)
required = ["bitshuffle", "lz4", "numpy", "boto3"]
missing = []
for r in required:
    try:
        __import__(r)
    except ImportError:
        missing.append(r)

if missing:
    print(f"Installing dependencies: {{missing}}...", flush=True)
    # Removing 'cython' and '--break-system-packages' to rely on clean wheel install
    # If using newer pip/python, --break-system-packages might be needed, adding it back just in case
    # bitshuffle wheel should install without compilation.
    subprocess.run([sys.executable, "-m", "pip", "install"] + missing + ["--break-system-packages"], check=False)

import numpy as np
import bitshuffle
try:
    import lz4.frame
except:
    subprocess.run([sys.executable, "-m", "pip", "install", "lz4"], check=False)
    import lz4.frame

# Install s5cmd
if shutil.which("s5cmd") is None:
    print("Installing s5cmd...", flush=True)
    url = "https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz"
    subprocess.run(f"curl -sL {{url}} | tar xz -C /tmp", shell=True, check=True)
    s5_bins = glob.glob("/tmp/s5cmd_*/s5cmd")
    if s5_bins:
        shutil.move(s5_bins[0], "/usr/local/bin/s5cmd")
        os.chmod("/usr/local/bin/s5cmd", 0o755)
    else:
        # Fallback: try direct path
        if os.path.exists("/tmp/s5cmd"):
            shutil.move("/tmp/s5cmd", "/usr/local/bin/s5cmd")
            os.chmod("/usr/local/bin/s5cmd", 0o755)

# Configuration - credentials passed from environment
os.environ["AWS_ACCESS_KEY_ID"] = "{r2_access_key}"
os.environ["AWS_SECRET_ACCESS_KEY"] = "{r2_secret_key}"
os.environ["AWS_REGION"] = "auto"

WORKSPACE = "{workspace_path}"
SNAPSHOT_ID = "{snapshot_name}"
ENDPOINT = "{endpoint}"
BUCKET = "{bucket}"
CHUNK_SIZE = 64 * 1024 * 1024
MODELS_EXT = {{".pt", ".pth", ".safetensors", ".bin", ".ckpt", ".onnx", ".model"}}

# Helpers
def get_compressor_type(fpath):
    ext = os.path.splitext(fpath)[1].lower()
    return "bitshuffle" if ext in MODELS_EXT else "lz4"

def compress_chunk_task(args):
    idx, file_list, algo = args
    # Create tar in memory/temp
    tar_path = f"/tmp/chunk_{{idx}}.tar"
    with tarfile.open(tar_path, "w") as tar:
        for f in file_list:
            try:
                tar.add(f, arcname=os.path.relpath(f, WORKSPACE))
            except Exception as e:
                print(f"Warning: Could not add {{f}}: {{e}}", flush=True)
    
    # Compress
    with open(tar_path, "rb") as f_in:
        data = f_in.read()
    
    os.remove(tar_path)
    
    if algo == "bitshuffle" or algo == "lz4":
        # LZ4 Fast Compression (4+ GB/s decompression)
        # Works reliably with any size, no overflow issues
        compressed = lz4.frame.compress(data)
        ext = "lz4"
        
    # Write compressed chunk
    out_path = f"/tmp/chunk_{{idx}}.{{ext}}"
    with open(out_path, "wb") as f_out:
        f_out.write(compressed)
        
    return out_path, len(data), len(compressed)

def upload_task(fpath):
    fname = os.path.basename(fpath)
    cmd = ["s5cmd", "--endpoint-url", ENDPOINT, "cp", fpath, f"s3://{{BUCKET}}/snapshots/{{SNAPSHOT_ID}}/{{fname}}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    os.remove(fpath)
    return True

# Main Execution
print("Scanning workspace...", flush=True)
models = []
others = []
for root, dirs, files in os.walk(WORKSPACE):
    for f in files:
        full = os.path.join(root, f)
        if os.path.islink(full): continue
        if get_compressor_type(full) == "bitshuffle":
            models.append(full)
        else:
            others.append(full)

print(f"Found {{len(models)}} models, {{len(others)}} other files.", flush=True)

# Chunking logic
chunks = []
current_chunk = []
current_size = 0
chunk_idx = 0

def flush_chunk(algo):
    global chunk_idx, current_chunk, current_size
    if current_chunk:
        chunks.append((chunk_idx, current_chunk, algo))
        chunk_idx += 1
        current_chunk = []
        current_size = 0

# Group Models (Bitshuffle)
for m in models:
    sz = os.path.getsize(m)
    if current_size + sz > CHUNK_SIZE:
        flush_chunk("bitshuffle")
    current_chunk.append(m)
    current_size += sz
flush_chunk("bitshuffle")

# Group Others (LZ4)
current_size = 0
for o in others:
    sz = os.path.getsize(o)
    if current_size + sz > CHUNK_SIZE:
        flush_chunk("lz4")
    current_chunk.append(o)
    current_size += sz
flush_chunk("lz4")

print(f"Created {{len(chunks)}} chunks for processing.", flush=True)

# Parallel Compression & Pipeline
print("Compressing (Multiprocess Bitshuffle+LZ4)...", flush=True)
upload_queue = []
total_orig = 0
total_comp = 0

with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
    futures = [executor.submit(compress_chunk_task, c) for c in chunks]
    
    with ThreadPoolExecutor(max_workers=32) as uploader:
        upload_futures = []
        for f in futures:
            p, orig, comp = f.result()
            total_orig += orig
            total_comp += comp
            upload_futures.append(uploader.submit(upload_task, p))
        
        for f in upload_futures:
            f.result()

stats = {{
    "original_size": total_orig,
    "compressed_size": total_comp,
    "ratio": total_orig / total_comp if total_comp > 0 else 0,
    "num_chunks": len(chunks),
    "upload_time": 0
}}
print(json.dumps(stats))
"""

    def _generate_hybrid_restore_script(self, snapshot_id, workspace_path, endpoint, bucket) -> str:
        """Generates the Python script for fast parallel restore."""
        
        # Use B2 native SDK if provider is B2
        if self.provider == "b2":
            return self._generate_b2_restore_script(snapshot_id, workspace_path, endpoint, bucket)
        else:
            return self._generate_s3_restore_script(snapshot_id, workspace_path, endpoint, bucket)
    
    def _generate_b2_restore_script(self, snapshot_id, workspace_path, endpoint, bucket) -> str:
        """Generate restore script using B2 native SDK"""
        return f"""
import os
import sys
import glob
import time
import json
import math
import tarfile
import subprocess
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# Sync clock (B2 requires accurate time)
print("Syncing clock...", flush=True)
try:
    # Try timedatectl first (faster, no install needed)
    result = subprocess.run(["timedatectl", "set-ntp", "true"], capture_output=True, timeout=10)
    if result.returncode == 0:
        print("✓ Clock sync enabled via timedatectl", flush=True)
        import time as time_module
        time_module.sleep(2)  # Give NTP time to sync
    else:
        # Fallback to ntpdate
        subprocess.run(["apt-get", "update", "-qq"], capture_output=True, timeout=30)
        subprocess.run(["apt-get", "install", "-qq", "-y", "ntpdate"], capture_output=True, timeout=60)
        subprocess.run(["ntpdate", "-s", "pool.ntp.org"], capture_output=True, timeout=30)
        print("✓ Clock synced via ntpdate", flush=True)
except Exception as ex:
    print(f"⚠️  Clock sync failed: {{ex}}, continuing anyway...", flush=True)

# Install dependencies
required = ["b2sdk", "lz4", "requests"]
missing = []
for r in required:
    try:
        __import__(r)
    except ImportError:
        missing.append(r)

if missing:
    print(f"Installing dependencies...", flush=True)
    subprocess.run([sys.executable, "-m", "pip", "install"] + missing + ["--break-system-packages"], check=False)

from b2sdk.v2 import InMemoryAccountInfo, B2Api
import lz4.frame
import shutil
import glob

SNAPSHOT_ID = "{snapshot_id}"
BUCKET = "{bucket}"
WORKSPACE = "{workspace_path}"

# B2 Credentials
B2_KEY_ID = os.environ.get("B2_KEY_ID")
B2_APP_KEY = os.environ.get("B2_APPLICATION_KEY")

if not B2_KEY_ID or not B2_APP_KEY:
    raise ValueError("B2_KEY_ID and B2_APPLICATION_KEY must be set in environment")

os.makedirs("/tmp/restore", exist_ok=True)
os.makedirs(WORKSPACE, exist_ok=True)

# ========== NETWORK OPTIMIZATION: SATURATE NIC ==========
# Force TCP to behave like UDP - maximize network card throughput
print("🚀 Optimizing TCP for maximum network speed...", flush=True)
import subprocess as sp_net

# 1. Set BBR congestion control (Google's algorithm for high-speed links)
sp_net.run("sysctl -w net.ipv4.tcp_congestion_control=bbr 2>/dev/null || true", shell=True)

# 2. Massive TCP buffers (128MB send/recv)
sp_net.run("sysctl -w net.core.rmem_max=134217728 2>/dev/null || true", shell=True)
sp_net.run("sysctl -w net.core.wmem_max=134217728 2>/dev/null || true", shell=True)
sp_net.run("sysctl -w net.ipv4.tcp_rmem='4096 87380 134217728' 2>/dev/null || true", shell=True)
sp_net.run("sysctl -w net.ipv4.tcp_wmem='4096 65536 134217728' 2>/dev/null || true", shell=True)

# 3. Increase connection queue (for 100+ parallel downloads)
sp_net.run("sysctl -w net.core.somaxconn=4096 2>/dev/null || true", shell=True)
sp_net.run("sysctl -w net.core.netdev_max_backlog=16384 2>/dev/null || true", shell=True)

# 4. Enable TCP window scaling
sp_net.run("sysctl -w net.ipv4.tcp_window_scaling=1 2>/dev/null || true", shell=True)

# 5. Disable slow start after idle (keep speed always high)
sp_net.run("sysctl -w net.ipv4.tcp_slow_start_after_idle=0 2>/dev/null || true", shell=True)

# 6. Increase max number of open files (for parallel connections)
sp_net.run("ulimit -n 65536 2>/dev/null || true", shell=True)

print("✓ TCP optimized for maximum throughput!", flush=True)
# ========================================================

# Connect to B2
print("Connecting to B2...", flush=True)
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", B2_KEY_ID, B2_APP_KEY)
bucket_obj = b2_api.get_bucket_by_name(BUCKET)
print("✓ Connected!", flush=True)

# Download all chunks from BOTH providers (Multi-Provider)
print("Downloading snapshot from B2 + R2...", flush=True)
t0 = time.time()

import subprocess as sp_restore

# List files from B2
b2_files = []
for file_version, _ in bucket_obj.ls(f"snapshots/{{SNAPSHOT_ID}}/"):
    if file_version.file_name.endswith(".lz4"):
        b2_files.append(file_version.file_name)

# List files from R2 using s5cmd - credentials from environment
r2_files = []
env_r2 = os.environ.copy()
env_r2["AWS_ACCESS_KEY_ID"] = "{r2_access_key}"
env_r2["AWS_SECRET_ACCESS_KEY"] = "{r2_secret_key}"
env_r2["AWS_REGION"] = "auto"
R2_ENDPOINT = "{r2_endpoint}"
R2_BUCKET = "{r2_bucket}"

# Install s5cmd if not present
if not os.path.exists("/usr/local/bin/s5cmd"):
    url = "https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz"
    sp_restore.run(f"curl -sL {{url}} -o /tmp/s5cmd.tar.gz", shell=True, check=True)
    sp_restore.run("tar xzf /tmp/s5cmd.tar.gz -C /tmp", shell=True, check=True)
    
    for possible_path in glob.glob("/tmp/s5cmd*") + ["/tmp/s5cmd"]:
        if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
            shutil.copy(possible_path, "/usr/local/bin/s5cmd")
            os.chmod("/usr/local/bin/s5cmd", 0o755)
            break


result = sp_restore.run(
    ["s5cmd", "--endpoint-url", R2_ENDPOINT, "ls", f"s3://{{R2_BUCKET}}/snapshots/{{SNAPSHOT_ID}}/"],
    capture_output=True, text=True, env=env_r2
)
for line in result.stdout.strip().split("\\n"):
    if line and ".lz4" in line:
        parts = line.split()
        if len(parts) >= 4:
            fname = parts[-1]
            # Add full path if not present
            if not fname.startswith("snapshots/"):
                fname = f"snapshots/{{SNAPSHOT_ID}}/{{fname}}"
            r2_files.append(fname)


# Create list of (file, provider) tuples
snapshot_files = [(f, "b2") for f in b2_files] + [(f, "r2") for f in r2_files]
print(f"Found {{len(b2_files)}} files in B2, {{len(r2_files)}} files in R2 (total: {{len(snapshot_files)}})", flush=True)

# Pipeline: Download in batches and decompress immediately
# This overlaps network I/O with CPU work
BATCH_SIZE = 40  # Batch maior para saturar rede
total_downloaded = 0

# Multi-thread Range Downloader to simulate UDP speed
import requests
from concurrent.futures import ThreadPoolExecutor

def download_range(args):
    url, start, end, local_path, headers = args
    range_header = f"bytes={{start}}-{{end}}"
    headers["Range"] = range_header
    headers["Connection"] = "keep-alive"

    import socket
    from requests.adapters import HTTPAdapter

    class TCPKeepAliveAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            kwargs["socket_options"] = [
                (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),
            ]
            super().init_poolmanager(*args, **kwargs)

    # Retry up to 3 times
    for attempt in range(3):
        try:
            session = requests.Session()
            session.headers.update(headers)
            session.mount("https://", TCPKeepAliveAdapter())
            session.mount("http://", TCPKeepAliveAdapter())

            resp = session.get(url, stream=True, timeout=120)
            resp.raise_for_status()

            with open(local_path, "rb+") as f:
                f.seek(start)
                f.write(resp.content)

            session.close()
            return True
        except Exception as e:
            if attempt < 2:
                import time
                time.sleep(1)  # Wait before retry
            else:
                raise e
    return False

def download_file(file_info):
    file_name, provider = file_info
    local_name = os.path.basename(file_name)
    local_path = f"/tmp/restore/{{local_name}}"
    
    # Get direct URL and headers
    if provider == "b2":
        # Get authorized URL from B2 SDK
        file_version = bucket_obj.get_file_info_by_name(file_name)
        file_id = file_version.id_
        url = b2_api.get_download_url_for_fileid(file_id)
        auth_token = b2_api.account_info.get_account_auth_token()
        headers = {{"Authorization": auth_token}}
        size = file_version.size
    else:
        # R2 URL (public or pre-signed - here we construct it if possible)
        # Using s5cmd is often faster for R2, but for Range we use direct URL
        url = f"{{R2_ENDPOINT}}/{{R2_BUCKET}}/{{file_name}}"
        # For R2 range, we'd need auth headers if private. Let's use s5cmd for now if not large.
        # But to really hit UDP speeds, we need ranges.
        # FALLBACK to s5cmd for R2 for simplicity if auth is complex, 
        # but B2 will use Range for maximum speed.
        if provider == "r2":
             sp_restore.run(
                ["s5cmd", "--endpoint-url", R2_ENDPOINT, "cp", f"s3://{{R2_BUCKET}}/{{file_name}}", local_path],
                check=True, stdout=sp_restore.DEVNULL, env=env_r2
            )
             return local_path

    # Range download - AGGRESSIVE: 4MB chunks = 4x more parallel connections
    # This saturates the NIC like UDP by having 200+ simultaneous streams
    PART_SIZE = 4 * 1024 * 1024  # 4MB per thread (was 16MB)
    if size > PART_SIZE * 2:
        num_parts = math.ceil(size / PART_SIZE)
        # Verbose logging removed for cleaner output
        # print(f"  ⚡ Saturating NIC: {{local_name}} ({{size/1024/1024:.1f}} MB) → {{num_parts}} parallel streams", flush=True)

        # Pre-allocate file
        with open(local_path, "wb") as f:
            f.truncate(size)
            
        tasks = []
        for i in range(num_parts):
            start = i * PART_SIZE
            end = min(start + PART_SIZE - 1, size - 1)
            tasks.append((url, start, end, local_path, headers.copy()))
            
        # 32 workers = balanced for stability
        with ThreadPoolExecutor(max_workers=32) as executor:
            list(executor.map(download_range, tasks))
    else:
        # Simple download for small files
        downloaded = bucket_obj.download_file_by_name(file_name)
        downloaded.save_to(local_path)
            
    return local_path

def decompress_and_extract(fpath):
    with open(fpath, "rb") as f_in:
        data = f_in.read()
    decompressed = lz4.frame.decompress(data)
    
    tar_tmp = fpath + ".tar"
    with open(tar_tmp, "wb") as f_tar:
        f_tar.write(decompressed)

    try:
        with tarfile.open(tar_tmp, "r") as tar:
            tar.extractall(path=WORKSPACE)
    except Exception as e:
        print(f"Warning: Failed to extract {{fpath}}: {{e}}", flush=True)
    
    os.remove(tar_tmp)
    os.remove(fpath)

from concurrent.futures import ThreadPoolExecutor
import math

# Process in batches for pipeline effect
num_batches = math.ceil(len(snapshot_files) / BATCH_SIZE)
print(f"Processing {{num_batches}} batches of {{BATCH_SIZE}} files each", flush=True)

t_dl_total = 0
t_decomp_total = 0

for batch_idx in range(num_batches):
    start_idx = batch_idx * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, len(snapshot_files))
    batch = snapshot_files[start_idx:end_idx]
    
    print(f"Batch {{batch_idx+1}}/{{num_batches}}: downloading {{len(batch)}} files...", flush=True)
    
    # Download batch in parallel - MAXIMUM WORKERS
    t_dl_start = time.time()
    # 200 workers to saturate multi-Gbps links
    with ThreadPoolExecutor(max_workers=min(200, len(batch) * 2)) as executor:
        downloaded_batch = list(executor.map(download_file, batch))
    t_dl_batch = time.time() - t_dl_start
    t_dl_total += t_dl_batch
    
    # Decompress batch in parallel
    print(f"  Decompressing {{len(downloaded_batch)}} files...", flush=True)
    t_decomp_start = time.time()
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        list(executor.map(decompress_and_extract, downloaded_batch))
    t_decomp_batch = time.time() - t_decomp_start
    t_decomp_total += t_decomp_batch
    
    total_downloaded += len(downloaded_batch)
    print(f"  Batch {{batch_idx+1}} done: dl={{t_dl_batch:.1f}}s, decomp={{t_decomp_batch:.1f}}s", flush=True)

dl_time = t_dl_total
dec_time = t_decomp_total
total_time = time.time() - t0

import shutil
shutil.rmtree("/tmp/restore")

# Final summary
print("\\n" + "="*60, flush=True)
print(f"✓ Restore Complete!", flush=True)
print(f"  Files restored: {{total_downloaded}}", flush=True)
print(f"  Download time:  {{dl_time:.1f}}s", flush=True)
print(f"  Extract time:   {{dec_time:.1f}}s", flush=True)
print(f"  Total time:     {{total_time:.1f}}s", flush=True)
print("="*60, flush=True)

stats = {{
    "download_time": dl_time,
    "decompress_time": dec_time,
    "total_time": total_time,
    "files_restored": total_downloaded
}}
print(json.dumps(stats))
"""
    
    def _generate_s3_restore_script(self, snapshot_id, workspace_path, endpoint, bucket) -> str:
        """Generate restore script using s5cmd (for R2, S3, Wasabi)"""
        return f"""
import os
import sys
import glob
import time
import json
import tarfile
import shutil
import struct
import subprocess
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing

# 1. Dependency Check
required = ["bitshuffle", "lz4", "numpy", "boto3"]
missing = []
for r in required:
    try:
        __import__(r)
    except ImportError:
        missing.append(r)

if missing:
    print(f"Installing dependencies...", flush=True)
    subprocess.run([sys.executable, "-m", "pip", "install"] + missing + ["--break-system-packages"], check=False)

import numpy as np
import bitshuffle
try:
    import lz4.frame
except:
    subprocess.run([sys.executable, "-m", "pip", "install", "lz4"], check=False)
    import lz4.frame

# Install s5cmd if missing
if shutil.which("s5cmd") is None:
    print("Installing s5cmd...", flush=True)
    url = "https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz"
    subprocess.run(f"curl -sL {{url}} | tar xz -C /tmp", shell=True, check=True)
    s5_bins = glob.glob("/tmp/s5cmd_*/s5cmd")
    if s5_bins:
        shutil.move(s5_bins[0], "/usr/local/bin/s5cmd")
        os.chmod("/usr/local/bin/s5cmd", 0o755)
    else:
        if os.path.exists("/tmp/s5cmd"):
            shutil.move("/tmp/s5cmd", "/usr/local/bin/s5cmd")
            os.chmod("/usr/local/bin/s5cmd", 0o755)

SNAPSHOT_ID = "{snapshot_id}"
ENDPOINT = "{endpoint}"
BUCKET = "{bucket}"
WORKSPACE = "{workspace_path}"

# Credentials passed from environment
os.environ["AWS_ACCESS_KEY_ID"] = "{r2_access_key}"
os.environ["AWS_SECRET_ACCESS_KEY"] = "{r2_secret_key}"
os.environ["AWS_REGION"] = "auto"

os.makedirs("/tmp/restore", exist_ok=True)
os.makedirs(WORKSPACE, exist_ok=True)

# 1. Download (s5cmd)
print("Downloading snapshot...", flush=True)
t0 = time.time()
cmd = f"s5cmd --endpoint-url {{ENDPOINT}} --numworkers 64 cp s3://{{BUCKET}}/snapshots/{{SNAPSHOT_ID}}/* /tmp/restore/"
subprocess.run(cmd, shell=True, check=True)
dl_time = time.time() - t0

# 2. Decompress & Extract (Parallel)
print("Decompressing & Extracting (Bitshuffle+LZ4)...", flush=True)
files = glob.glob("/tmp/restore/chunk_*")

def restore_chunk(fpath):
    ext = fpath.split(".")[-1]
    
    with open(fpath, "rb") as f_in:
        data = f_in.read()
            
    if ext in ("bsh", "lz4"):
        # LZ4 decompression (ultra fast)
        decompressed = lz4.frame.decompress(data)
    else:
        return # Unknown
        
    # Untar
    tar_tmp = fpath + ".tar"
    with open(tar_tmp, "wb") as f_tar:
        f_tar.write(decompressed)

    try:
        with tarfile.open(tar_tmp, "r") as tar:
            tar.extractall(path=WORKSPACE)
    except Exception as e:
        print(f"Warning: Failed to extract {{fpath}}: {{e}}", flush=True)
        
    os.remove(tar_tmp)
    os.remove(fpath)

t1 = time.time()
with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
    list(executor.map(restore_chunk, files))
dec_time = time.time() - t1

shutil.rmtree("/tmp/restore")

stats = {{
    "download_time": dl_time,
    "decompress_time": dec_time
}}
print(json.dumps(stats))
"""

    def _ssh_exec(self, host: str, port: int, script: str) -> Dict:
        """Executes python script via SSH using base64 encoding."""
        import os

        # Get B2 credentials from environment to pass to remote
        b2_key_id = os.getenv("B2_KEY_ID", "")
        b2_app_key = os.getenv("B2_APPLICATION_KEY", "")

        script_b64 = base64.b64encode(script.encode('utf-8')).decode('utf-8')

        # Pass B2 credentials as environment variables via SSH
        cmd = [
            "ssh",
            "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            f"root@{host}",
            f"B2_KEY_ID='{b2_key_id}' B2_APPLICATION_KEY='{b2_app_key}' bash -c \"echo {script_b64} | base64 -d | python3\""
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200 # 2 hours
        )
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }

    def _save_snapshot_metadata(self, snapshot_info: Dict):
        """Salva metadados do snapshot no storage"""
        metadata_file = f"/tmp/snapshot_metadata_{snapshot_info['snapshot_id']}.json"

        with open(metadata_file, 'w') as f:
            json.dump(snapshot_info, f, indent=2)

        # Upload metadados usando provider apropriado
        if self.provider == "b2":
            # Use B2 SDK
            from b2sdk.v2 import InMemoryAccountInfo, B2Api
            
            b2_key_id = os.environ.get("B2_KEY_ID")
            b2_app_key = os.environ.get("B2_APPLICATION_KEY")

            if not b2_key_id or not b2_app_key:
                raise ValueError("B2_KEY_ID and B2_APPLICATION_KEY must be set in environment")
            
            info = InMemoryAccountInfo()
            b2_api = B2Api(info)
            b2_api.authorize_account("production", b2_key_id, b2_app_key)
            bucket = b2_api.get_bucket_by_name(self.r2_bucket)
            
            remote_path = f"snapshots/{snapshot_info['snapshot_id']}/metadata.json"
            bucket.upload_local_file(
                local_file=metadata_file,
                file_name=remote_path
            )
        else:
            # Use s5cmd for R2/S3/Wasabi
            cmd = [
                "s5cmd",
                "--endpoint-url", self.r2_endpoint,
                "cp",
                metadata_file,
                f"s3://{self.r2_bucket}/snapshots/{snapshot_info['snapshot_id']}/metadata.json"
            ]
            subprocess.run(cmd, check=True)
        
        os.remove(metadata_file)
    
    def list_snapshots(self, instance_id: Optional[str] = None) -> List[Dict]:
        """Lista snapshots disponíveis"""
        cmd = [
            "s5cmd",
            "--endpoint-url", self.r2_endpoint,
            "ls",
            f"s3://{self.r2_bucket}/snapshots/"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        snapshots = []
        for line in result.stdout.splitlines():
            if 'metadata.json' in line:
                try:
                    url = line.split()[-1] # s3://...
                    snapshot_id = url.split('/')[-2]
                    
                    metadata = self._load_snapshot_metadata(snapshot_id)
                    if instance_id is None or metadata.get('instance_id') == instance_id:
                        snapshots.append(metadata)
                except: continue
        return snapshots

    def _load_snapshot_metadata(self, snapshot_id: str) -> Dict:
        """Carrega metadados de um snapshot"""
        metadata_file = f"/tmp/snapshot_metadata_{snapshot_id}.json"
        cmd = [
            "s5cmd", "--endpoint-url", self.r2_endpoint,
            "cp", f"s3://{self.r2_bucket}/snapshots/{snapshot_id}/metadata.json",
            metadata_file
        ]
        subprocess.run(cmd, capture_output=True)
        
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            os.remove(metadata_file)
            return data
        return {}
    
    def create_incremental_snapshot(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int,
        base_snapshot_id: str,
        workspace_path: str = "/workspace",
        snapshot_name: Optional[str] = None,
    ) -> Dict:
        """
        Cria snapshot incremental - apenas arquivos modificados desde base_snapshot_id

        Strategy:
        1. Download metadata do snapshot base
        2. Listar arquivos atuais no workspace
        3. Identificar apenas arquivos novos/modificados (por mtime)
        4. Criar snapshot apenas desses arquivos

        Returns: Metadata com informações do snapshot incremental
        """
        start_time = time.time()

        if not snapshot_name:
            snapshot_name = f"incr-{instance_id}-{int(time.time())}"

        logger.info(f"[Incremental] Creating incremental snapshot from base: {base_snapshot_id}")

        # Script para identificar arquivos modificados e criar snapshot incremental
        script = self._generate_incremental_snapshot_script(
            workspace_path=workspace_path,
            base_snapshot_id=base_snapshot_id,
            snapshot_name=snapshot_name,
            endpoint=self.r2_endpoint,
            bucket=self.r2_bucket,
        )

        # Executar script na GPU
        result = subprocess.run(
            [
                "ssh", "-p", str(ssh_port),
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                f"root@{ssh_host}",
                f"python3 -c '{script}'"
            ],
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            raise Exception(f"Incremental snapshot failed: {result.stderr}")

        total_time = time.time() - start_time

        # Parse output para pegar estatísticas
        output_lines = result.stdout.strip().split('\n')
        stats = {
            "snapshot_id": snapshot_name,
            "base_snapshot_id": base_snapshot_id,
            "type": "incremental",
            "time": total_time,
        }

        for line in output_lines:
            if "files changed:" in line.lower():
                try:
                    stats["files_changed"] = int(line.split(":")[-1].strip())
                except:
                    pass
            elif "size:" in line.lower():
                try:
                    stats["size_compressed"] = int(line.split(":")[-1].strip().split()[0])
                except:
                    pass

        logger.info(f"[Incremental] Snapshot created in {total_time:.1f}s: {snapshot_name}")
        return stats

    def _generate_incremental_snapshot_script(
        self,
        workspace_path: str,
        base_snapshot_id: str,
        snapshot_name: str,
        endpoint: str,
        bucket: str,
    ) -> str:
        """Gera script Python para criar snapshot incremental"""
        return f"""
import os
import time
import subprocess
import json

WORKSPACE = "{workspace_path}"
BASE_SNAPSHOT = "{base_snapshot_id}"
SNAPSHOT_NAME = "{snapshot_name}"
ENDPOINT = "{endpoint}"
BUCKET = "{bucket}"

# 1. Download metadata do snapshot base (contém lista de arquivos e timestamps)
print("Downloading base snapshot metadata...", flush=True)
metadata_file = f"/tmp/{{BASE_SNAPSHOT}}_metadata.json"
cmd = [
    "s5cmd", "--endpoint-url", ENDPOINT,
    "cp", f"s3://{{BUCKET}}/snapshots/{{BASE_SNAPSHOT}}/metadata.json",
    metadata_file
]
subprocess.run(cmd, check=False)  # Pode não existir metadata

base_files = {{}}
if os.path.exists(metadata_file):
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
        base_files = metadata.get('files', {{}})  # {{path: mtime}}
    os.remove(metadata_file)

# 2. Listar arquivos atuais e identificar mudanças
print("Scanning for changed files...", flush=True)
changed_files = []
new_metadata = {{}}

for root, dirs, files in os.walk(WORKSPACE):
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            stat = os.stat(fpath)
            mtime = stat.st_mtime
            relative_path = os.path.relpath(fpath, WORKSPACE)

            new_metadata[relative_path] = mtime

            # Arquivo novo ou modificado?
            if relative_path not in base_files or base_files[relative_path] < mtime:
                changed_files.append(fpath)
        except OSError as e:
            print(f"Warning: Could not stat {{fpath}}: {{e}}", flush=True)

print(f"Files changed: {{len(changed_files)}}", flush=True)

if not changed_files:
    print("No changes detected - skipping snapshot")
    exit(0)

# 3. Criar tarball apenas dos arquivos modificados
print("Creating incremental tarball...", flush=True)
import tarfile
import lz4.frame

tar_path = f"/tmp/{{SNAPSHOT_NAME}}.tar"
with tarfile.open(tar_path, "w") as tar:
    for fpath in changed_files:
        try:
            tar.add(fpath, arcname=os.path.relpath(fpath, WORKSPACE))
        except Exception as e:
            print(f"Warning: Could not add {{fpath}}: {{e}}", flush=True)

# 4. Comprimir com LZ4
print("Compressing...", flush=True)
with open(tar_path, "rb") as f_in:
    data = f_in.read()

compressed = lz4.frame.compress(data)
os.remove(tar_path)

compressed_path = f"/tmp/{{SNAPSHOT_NAME}}.tar.lz4"
with open(compressed_path, "wb") as f_out:
    f_out.write(compressed)

print(f"Size: {{len(compressed)}} bytes", flush=True)

# 5. Upload para B2
print("Uploading to B2...", flush=True)
subprocess.run([
    "s5cmd", "--endpoint-url", ENDPOINT,
    "cp", compressed_path,
    f"s3://{{BUCKET}}/snapshots/{{SNAPSHOT_NAME}}/data.tar.lz4"
], check=True)

# 6. Upload metadata
metadata_path = "/tmp/metadata.json"
with open(metadata_path, "w") as f:
    json.dump({{
        "type": "incremental",
        "base_snapshot": BASE_SNAPSHOT,
        "files": new_metadata,
        "files_changed": len(changed_files),
        "size_compressed": len(compressed),
        "timestamp": time.time()
    }}, f)

subprocess.run([
    "s5cmd", "--endpoint-url", ENDPOINT,
    "cp", metadata_path,
    f"s3://{{BUCKET}}/snapshots/{{SNAPSHOT_NAME}}/metadata.json"
], check=True)

os.remove(compressed_path)
os.remove(metadata_path)

print("✓ Incremental snapshot complete", flush=True)
"""

    def delete_snapshot(self, snapshot_id: str):
        """Deleta snapshot"""
        cmd = [
            "s5cmd", "--endpoint-url", self.r2_endpoint,
            "rm", f"s3://{self.r2_bucket}/snapshots/{snapshot_id}/*"
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"Deleted snapshot {snapshot_id}")
