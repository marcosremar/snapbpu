"""
Model Downloader - Download automático de modelos do HuggingFace

Faz download de modelos para cache local ou remoto (na GPU instance).
Suporta:
- Download local (para desenvolvimento)
- Download remoto via SSH (para GPU instances)
- Cache persistente para evitar re-downloads
- Progress tracking
"""

import os
import json
import time
import logging
import subprocess
import hashlib
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from .registry import ModelInfo, ModelRegistry, get_registry, ModelRuntime

logger = logging.getLogger(__name__)


class DownloadStatus(str, Enum):
    """Status do download"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class DownloadResult:
    """Resultado de um download"""
    model_id: str
    status: DownloadStatus
    cache_path: Optional[str] = None
    size_bytes: Optional[int] = None
    download_time_seconds: Optional[float] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status in (DownloadStatus.COMPLETED, DownloadStatus.CACHED)


class ModelDownloader:
    """
    Gerencia download de modelos do HuggingFace.

    Uso:
        downloader = ModelDownloader()

        # Download local
        result = downloader.download("meta-llama/Llama-3.1-8B-Instruct")

        # Download em máquina remota via SSH
        result = downloader.download_remote(
            model_id="meta-llama/Llama-3.1-8B-Instruct",
            ssh_host="192.168.1.100",
            ssh_port=22,
        )
    """

    # Diretório padrão de cache do HuggingFace
    DEFAULT_CACHE_DIR = "~/.cache/huggingface/hub"

    # Scripts para download em máquina remota
    DOWNLOAD_SCRIPT = '''#!/bin/bash
set -e

MODEL_ID="$1"
CACHE_DIR="${2:-/root/.cache/huggingface/hub}"

echo "[DOWNLOAD] Model: $MODEL_ID"
echo "[DOWNLOAD] Cache: $CACHE_DIR"

# Instalar huggingface_hub se não existir
if ! python3 -c "import huggingface_hub" 2>/dev/null; then
    echo "[DOWNLOAD] Installing huggingface_hub..."
    pip install huggingface_hub -q
fi

# Download usando huggingface-cli
echo "[DOWNLOAD] Starting download..."
export HF_HUB_CACHE="$CACHE_DIR"

python3 << 'PYEOF'
import os
import sys
from huggingface_hub import snapshot_download

model_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MODEL_ID", "")
cache_dir = os.environ.get("HF_HUB_CACHE", "/root/.cache/huggingface/hub")

if not model_id:
    print('{"error": "MODEL_ID not provided"}')
    sys.exit(1)

try:
    path = snapshot_download(
        repo_id=model_id,
        cache_dir=cache_dir,
        resume_download=True,
    )
    # Calcular tamanho
    total_size = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            total_size += os.path.getsize(os.path.join(root, f))

    print(f'{{"success": true, "path": "{path}", "size_bytes": {total_size}}}')
except Exception as e:
    print(f'{{"error": "{str(e)}"}}')
    sys.exit(1)
PYEOF
'''

    CHECK_CACHE_SCRIPT = '''#!/bin/bash
MODEL_ID="$1"
CACHE_DIR="${2:-/root/.cache/huggingface/hub}"

python3 << 'PYEOF'
import os
import sys
from pathlib import Path

model_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MODEL_ID", "")
cache_dir = os.environ.get("HF_HUB_CACHE", "/root/.cache/huggingface/hub")

# Converter model_id para formato de cache
# meta-llama/Llama-3.1-8B -> models--meta-llama--Llama-3.1-8B
cache_name = "models--" + model_id.replace("/", "--")
cache_path = Path(cache_dir) / cache_name

if cache_path.exists():
    # Verificar se tem snapshots
    snapshots = cache_path / "snapshots"
    if snapshots.exists() and any(snapshots.iterdir()):
        # Calcular tamanho
        total_size = 0
        for root, dirs, files in os.walk(cache_path):
            for f in files:
                total_size += os.path.getsize(os.path.join(root, f))
        print(f'{{"cached": true, "path": "{cache_path}", "size_bytes": {total_size}}}')
    else:
        print('{"cached": false, "reason": "no snapshots"}')
else:
    print('{"cached": false, "reason": "not found"}')
PYEOF
'''

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        registry: Optional[ModelRegistry] = None,
    ):
        """
        Args:
            cache_dir: Diretório de cache local
            registry: Registry para obter info do modelo
        """
        self.cache_dir = Path(cache_dir or os.path.expanduser(self.DEFAULT_CACHE_DIR))
        self.registry = registry or get_registry()

    def is_cached_locally(self, model_id: str) -> bool:
        """Verifica se modelo está em cache local"""
        cache_name = "models--" + model_id.replace("/", "--")
        cache_path = self.cache_dir / cache_name / "snapshots"
        return cache_path.exists() and any(cache_path.iterdir())

    def get_local_cache_path(self, model_id: str) -> Optional[Path]:
        """Retorna path do cache local se existir"""
        cache_name = "models--" + model_id.replace("/", "--")
        cache_path = self.cache_dir / cache_name

        if not cache_path.exists():
            return None

        # Encontrar snapshot mais recente
        snapshots_dir = cache_path / "snapshots"
        if not snapshots_dir.exists():
            return None

        snapshots = list(snapshots_dir.iterdir())
        if not snapshots:
            return None

        # Retornar o mais recente
        return max(snapshots, key=lambda p: p.stat().st_mtime)

    def download_local(
        self,
        model_id: str,
        force: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> DownloadResult:
        """
        Faz download de um modelo para cache local.

        Args:
            model_id: ID do modelo no HuggingFace
            force: Se True, baixa mesmo se já estiver em cache
            progress_callback: Callback para progresso (mensagem, percentual)

        Returns:
            DownloadResult com status e path
        """
        # Verificar cache
        if not force and self.is_cached_locally(model_id):
            cache_path = self.get_local_cache_path(model_id)
            logger.info(f"[DOWNLOAD] Model already cached: {model_id}")
            return DownloadResult(
                model_id=model_id,
                status=DownloadStatus.CACHED,
                cache_path=str(cache_path) if cache_path else None,
            )

        start_time = time.time()

        try:
            if progress_callback:
                progress_callback(f"Downloading {model_id}...", 0.0)

            # Usar huggingface_hub se disponível
            try:
                from huggingface_hub import snapshot_download

                path = snapshot_download(
                    repo_id=model_id,
                    cache_dir=str(self.cache_dir),
                    resume_download=True,
                )

                download_time = time.time() - start_time

                # Calcular tamanho
                total_size = 0
                for root, dirs, files in os.walk(path):
                    for f in files:
                        total_size += os.path.getsize(os.path.join(root, f))

                if progress_callback:
                    progress_callback(f"Downloaded {model_id}", 100.0)

                logger.info(f"[DOWNLOAD] Completed: {model_id} ({total_size / 1e9:.2f} GB)")

                return DownloadResult(
                    model_id=model_id,
                    status=DownloadStatus.COMPLETED,
                    cache_path=path,
                    size_bytes=total_size,
                    download_time_seconds=download_time,
                )

            except ImportError:
                # Fallback: usar huggingface-cli
                logger.warning("[DOWNLOAD] huggingface_hub not installed, using CLI")

                result = subprocess.run(
                    ["huggingface-cli", "download", model_id],
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hora
                )

                if result.returncode != 0:
                    raise Exception(result.stderr)

                cache_path = self.get_local_cache_path(model_id)

                return DownloadResult(
                    model_id=model_id,
                    status=DownloadStatus.COMPLETED,
                    cache_path=str(cache_path) if cache_path else None,
                    download_time_seconds=time.time() - start_time,
                )

        except Exception as e:
            logger.error(f"[DOWNLOAD] Failed: {model_id} - {e}")
            return DownloadResult(
                model_id=model_id,
                status=DownloadStatus.FAILED,
                error=str(e),
            )

    def download_remote(
        self,
        model_id: str,
        ssh_host: str,
        ssh_port: int = 22,
        ssh_user: str = "root",
        cache_dir: str = "/root/.cache/huggingface/hub",
        timeout: int = 3600,
        check_cache_first: bool = True,
    ) -> DownloadResult:
        """
        Faz download de um modelo em uma máquina remota via SSH.

        Args:
            model_id: ID do modelo
            ssh_host: Host SSH
            ssh_port: Porta SSH
            ssh_user: Usuário SSH
            cache_dir: Diretório de cache na máquina remota
            timeout: Timeout em segundos
            check_cache_first: Se True, verifica cache antes de baixar

        Returns:
            DownloadResult com status
        """
        start_time = time.time()

        # Verificar cache remoto primeiro
        if check_cache_first:
            cache_result = self._check_remote_cache(
                model_id, ssh_host, ssh_port, ssh_user, cache_dir
            )
            if cache_result.get("cached"):
                logger.info(f"[DOWNLOAD] Remote cache hit: {model_id}")
                return DownloadResult(
                    model_id=model_id,
                    status=DownloadStatus.CACHED,
                    cache_path=cache_result.get("path"),
                    size_bytes=cache_result.get("size_bytes"),
                )

        # Fazer download
        try:
            logger.info(f"[DOWNLOAD] Starting remote download: {model_id}")

            # Executar script de download
            result = self._ssh_exec(
                ssh_host, ssh_port, ssh_user,
                f'MODEL_ID="{model_id}" HF_HUB_CACHE="{cache_dir}" ' + self.DOWNLOAD_SCRIPT.replace("$1", model_id).replace("$2", cache_dir),
                timeout=timeout,
            )

            if result.returncode != 0:
                raise Exception(f"Download failed: {result.stderr}")

            # Parsear resultado JSON
            output = result.stdout.strip()
            for line in output.split('\n'):
                if line.startswith('{'):
                    data = json.loads(line)
                    if data.get("error"):
                        raise Exception(data["error"])

                    download_time = time.time() - start_time
                    logger.info(f"[DOWNLOAD] Remote completed: {model_id} in {download_time:.1f}s")

                    return DownloadResult(
                        model_id=model_id,
                        status=DownloadStatus.COMPLETED,
                        cache_path=data.get("path"),
                        size_bytes=data.get("size_bytes"),
                        download_time_seconds=download_time,
                    )

            raise Exception("No JSON output from download script")

        except Exception as e:
            logger.error(f"[DOWNLOAD] Remote failed: {model_id} - {e}")
            return DownloadResult(
                model_id=model_id,
                status=DownloadStatus.FAILED,
                error=str(e),
            )

    def _check_remote_cache(
        self,
        model_id: str,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        cache_dir: str,
    ) -> Dict[str, Any]:
        """Verifica se modelo está em cache remoto"""
        try:
            result = self._ssh_exec(
                ssh_host, ssh_port, ssh_user,
                f'MODEL_ID="{model_id}" HF_HUB_CACHE="{cache_dir}" ' + self.CHECK_CACHE_SCRIPT.replace("$1", model_id).replace("$2", cache_dir),
                timeout=30,
            )

            for line in result.stdout.strip().split('\n'):
                if line.startswith('{'):
                    return json.loads(line)

            return {"cached": False}

        except Exception as e:
            logger.warning(f"[DOWNLOAD] Cache check failed: {e}")
            return {"cached": False, "error": str(e)}

    def _ssh_exec(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        command: str,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        """Executa comando via SSH"""
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", str(ssh_port),
            f"{ssh_user}@{ssh_host}",
            command,
        ]

        return subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def get_download_command(self, model_id: str, runtime: str = "auto") -> str:
        """
        Retorna comando para download do modelo no runtime correto.

        Args:
            model_id: ID do modelo
            runtime: Runtime (vllm, transformers, diffusers, auto)

        Returns:
            Comando bash para download
        """
        if runtime == "auto":
            info = self.registry.get_model_info(model_id)
            runtime = info.runtime

        if runtime == ModelRuntime.VLLM or runtime == "vllm":
            # vLLM baixa automaticamente quando inicia
            return f'''python -c "
from vllm import LLM
print('Downloading model: {model_id}')
# Isso força o download sem iniciar inference
import huggingface_hub
huggingface_hub.snapshot_download('{model_id}')
print('Download complete')
"'''

        elif runtime == ModelRuntime.DIFFUSERS or runtime == "diffusers":
            return f'''python -c "
from diffusers import DiffusionPipeline
import torch
print('Downloading model: {model_id}')
pipe = DiffusionPipeline.from_pretrained('{model_id}', torch_dtype=torch.float16)
print('Download complete')
"'''

        else:
            # Genérico - usar huggingface_hub
            return f'''python -c "
from huggingface_hub import snapshot_download
print('Downloading model: {model_id}')
snapshot_download('{model_id}')
print('Download complete')
"'''


# Singleton
_downloader: Optional[ModelDownloader] = None


def get_downloader() -> ModelDownloader:
    """Retorna instância singleton do downloader"""
    global _downloader
    if _downloader is None:
        _downloader = ModelDownloader()
    return _downloader
