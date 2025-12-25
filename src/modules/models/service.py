"""
Serverless Model Service - Deploy automático de modelos

Integra:
- ModelRegistry: detecta tipo do modelo
- ModelDownloader: baixa do HuggingFace
- RuntimeTemplates: scripts de instalação/execução
- ServerlessService: scale up/down automático

Uso simples:
    service = ServerlessModelService()
    result = await service.deploy("meta-llama/Llama-3.1-8B-Instruct")
    # Pronto! Modelo detectado, baixado, e rodando
"""

import os
import time
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .registry import ModelRegistry, ModelInfo, get_registry, ModelRuntime
from .downloader import ModelDownloader, DownloadResult, DownloadStatus, get_downloader

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """Status do deployment"""
    PENDING = "pending"
    DETECTING = "detecting"           # Detectando tipo do modelo
    PROVISIONING = "provisioning"     # Criando instância GPU
    DOWNLOADING = "downloading"       # Baixando modelo
    INSTALLING = "installing"         # Instalando dependências
    STARTING = "starting"             # Iniciando servidor
    RUNNING = "running"               # Pronto para requests
    SCALING_DOWN = "scaling_down"     # Pausando
    PAUSED = "paused"                 # Pausado (scale to zero)
    FAILED = "failed"


@dataclass
class DeploymentConfig:
    """Configuração de deployment"""
    model_id: str

    # GPU Config
    gpu_type: str = "RTX 4090"
    gpu_count: int = 1
    min_vram_gb: Optional[float] = None  # Auto-detect

    # Serverless Config
    idle_timeout_seconds: int = 300     # 5 minutos
    scale_to_zero: bool = True
    use_checkpoint: bool = True

    # Runtime Config
    runtime: str = "auto"               # auto, vllm, transformers, diffusers
    port: int = 0                       # 0 = auto-detect

    # Model Config
    quantization: Optional[str] = None  # None, "int8", "int4", "awq", "gptq"
    max_model_len: Optional[int] = None
    gpu_memory_utilization: float = 0.9

    # Download Config
    force_download: bool = False
    hf_token: Optional[str] = None


@dataclass
class DeploymentResult:
    """Resultado de um deployment"""
    deployment_id: str
    model_id: str
    status: DeploymentStatus
    endpoint_url: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    ready_at: Optional[datetime] = None

    # Details
    model_info: Optional[ModelInfo] = None
    instance_id: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    port: int = 8000

    # Errors
    error: Optional[str] = None
    error_stage: Optional[str] = None

    # Metrics
    download_time_seconds: Optional[float] = None
    startup_time_seconds: Optional[float] = None
    total_time_seconds: Optional[float] = None

    @property
    def success(self) -> bool:
        return self.status == DeploymentStatus.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "model_id": self.model_id,
            "status": self.status.value,
            "endpoint_url": self.endpoint_url,
            "created_at": self.created_at.isoformat(),
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
            "instance_id": self.instance_id,
            "port": self.port,
            "error": self.error,
            "download_time_seconds": self.download_time_seconds,
            "startup_time_seconds": self.startup_time_seconds,
            "total_time_seconds": self.total_time_seconds,
        }


class ServerlessModelService:
    """
    Serviço principal para deploy serverless de modelos.

    Fluxo:
    1. detect_model() - Identifica tipo e runtime
    2. provision_gpu() - Cria instância (se necessário)
    3. download_model() - Baixa para cache
    4. start_server() - Inicia servidor do modelo
    5. monitor_idle() - Scale down quando idle

    Uso:
        service = ServerlessModelService(gpu_provider=tensordock)

        # Deploy simples
        result = await service.deploy("meta-llama/Llama-3.1-8B-Instruct")
        print(result.endpoint_url)

        # Deploy com config
        result = await service.deploy(
            "openai/whisper-large-v3",
            config=DeploymentConfig(
                idle_timeout_seconds=60,
                gpu_type="RTX 4090",
            )
        )
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        downloader: Optional[ModelDownloader] = None,
        gpu_provider: Optional[Any] = None,  # TensorDockService ou VastService
    ):
        self.registry = registry or get_registry()
        self.downloader = downloader or get_downloader()
        self.gpu_provider = gpu_provider

        # Deployments ativos
        self._deployments: Dict[str, DeploymentResult] = {}

        # Templates de runtime (do runtime_templates.py existente)
        self._runtime_templates = self._load_runtime_templates()

    def _load_runtime_templates(self) -> Dict[str, Any]:
        """Carrega templates de runtime existentes"""
        try:
            from src.services.runtime_templates import TEMPLATES
            return TEMPLATES
        except ImportError:
            logger.warning("[SERVICE] Could not load runtime_templates, using defaults")
            return {}

    async def deploy(
        self,
        model_id: str,
        config: Optional[DeploymentConfig] = None,
        wait: bool = True,
        progress_callback: Optional[Callable[[str, DeploymentStatus], None]] = None,
    ) -> DeploymentResult:
        """
        Faz deploy de um modelo.

        Args:
            model_id: ID do modelo no HuggingFace
            config: Configuração opcional
            wait: Se True, aguarda até estar running
            progress_callback: Callback de progresso

        Returns:
            DeploymentResult com status e endpoint
        """
        config = config or DeploymentConfig(model_id=model_id)
        config.model_id = model_id

        deployment_id = f"deploy-{int(time.time())}-{model_id.replace('/', '-')}"

        result = DeploymentResult(
            deployment_id=deployment_id,
            model_id=model_id,
            status=DeploymentStatus.PENDING,
        )

        self._deployments[deployment_id] = result

        try:
            # 1. Detectar tipo do modelo
            result.status = DeploymentStatus.DETECTING
            self._notify(progress_callback, "Detecting model type...", result.status)

            model_info = self.registry.get_model_info(model_id)
            result.model_info = model_info

            logger.info(f"[DEPLOY] Model: {model_id}")
            logger.info(f"[DEPLOY] Task: {model_info.task}")
            logger.info(f"[DEPLOY] Runtime: {model_info.runtime}")

            # Auto-detect runtime e port
            if config.runtime == "auto":
                config.runtime = model_info.runtime
            if config.port == 0:
                config.port = model_info.default_port

            result.port = config.port

            # 2. Verificar/Provisionar GPU
            result.status = DeploymentStatus.PROVISIONING
            self._notify(progress_callback, "Provisioning GPU...", result.status)

            instance = await self._ensure_gpu_instance(config, model_info)
            if instance:
                result.instance_id = instance.get("id")
                result.ssh_host = instance.get("ssh_host")
                result.ssh_port = instance.get("ssh_port")

            # 3. Baixar modelo
            result.status = DeploymentStatus.DOWNLOADING
            self._notify(progress_callback, f"Downloading {model_id}...", result.status)

            download_start = time.time()
            download_result = await self._download_model(config, result)

            if not download_result.success:
                raise Exception(f"Download failed: {download_result.error}")

            result.download_time_seconds = time.time() - download_start
            logger.info(f"[DEPLOY] Download complete in {result.download_time_seconds:.1f}s")

            # 4. Instalar dependências
            result.status = DeploymentStatus.INSTALLING
            self._notify(progress_callback, "Installing dependencies...", result.status)

            await self._install_dependencies(config, result)

            # 5. Iniciar servidor
            result.status = DeploymentStatus.STARTING
            self._notify(progress_callback, "Starting model server...", result.status)

            startup_start = time.time()
            await self._start_model_server(config, result)

            result.startup_time_seconds = time.time() - startup_start

            # 6. Aguardar health check
            if wait:
                healthy = await self._wait_for_health(result, timeout=300)
                if not healthy:
                    raise Exception("Health check timeout")

            # Sucesso!
            result.status = DeploymentStatus.RUNNING
            result.ready_at = datetime.now()
            result.total_time_seconds = (result.ready_at - result.created_at).total_seconds()

            if result.ssh_host:
                result.endpoint_url = f"http://{result.ssh_host}:{result.port}"

            self._notify(progress_callback, "Deployment ready!", result.status)
            logger.info(f"[DEPLOY] Ready: {result.endpoint_url}")

            return result

        except Exception as e:
            result.status = DeploymentStatus.FAILED
            result.error = str(e)
            logger.error(f"[DEPLOY] Failed: {e}")
            self._notify(progress_callback, f"Failed: {e}", result.status)
            return result

    async def _ensure_gpu_instance(
        self,
        config: DeploymentConfig,
        model_info: ModelInfo,
    ) -> Optional[Dict[str, Any]]:
        """Garante que há uma instância GPU disponível"""
        if not self.gpu_provider:
            logger.warning("[DEPLOY] No GPU provider configured, running locally")
            return None

        # TODO: Implementar lógica de reutilização de instâncias
        # Por enquanto, cria uma nova

        min_vram = config.min_vram_gb or model_info.size_gb or 16.0

        logger.info(f"[DEPLOY] Requesting GPU with {min_vram}GB VRAM")

        # Usar o provider
        if hasattr(self.gpu_provider, 'deploy'):
            result = self.gpu_provider.deploy(
                name=f"model-{config.model_id.replace('/', '-')}",
                gpu_model=config.gpu_type,
                gpu_count=config.gpu_count,
            )
            if result.get("success"):
                return {
                    "id": result.get("instance_id"),
                    "ssh_host": result.get("ip_address"),
                    "ssh_port": result.get("ssh_port", 22),
                }

        return None

    async def _download_model(
        self,
        config: DeploymentConfig,
        result: DeploymentResult,
    ) -> DownloadResult:
        """Baixa o modelo para cache"""
        if result.ssh_host:
            # Download remoto
            return self.downloader.download_remote(
                model_id=config.model_id,
                ssh_host=result.ssh_host,
                ssh_port=result.ssh_port or 22,
                check_cache_first=not config.force_download,
            )
        else:
            # Download local
            return self.downloader.download_local(
                model_id=config.model_id,
                force=config.force_download,
            )

    async def _install_dependencies(
        self,
        config: DeploymentConfig,
        result: DeploymentResult,
    ) -> None:
        """Instala dependências do runtime"""
        runtime = config.runtime

        # Pegar script de instalação do template
        if runtime in self._runtime_templates:
            template = self._runtime_templates[runtime]
            install_script = template.install_script if hasattr(template, 'install_script') else ""
        else:
            # Scripts padrão por runtime
            install_scripts = {
                "vllm": "pip install vllm -q",
                "transformers": "pip install transformers accelerate torch -q",
                "diffusers": "pip install diffusers transformers accelerate torch -q",
                "sentence-transformers": "pip install sentence-transformers torch -q",
            }
            install_script = install_scripts.get(runtime, "")

        if not install_script:
            return

        if result.ssh_host:
            # Executar remotamente
            import subprocess
            cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-p", str(result.ssh_port or 22),
                f"root@{result.ssh_host}",
                install_script,
            ]
            subprocess.run(cmd, capture_output=True, timeout=600)
        else:
            # Executar localmente
            import subprocess
            subprocess.run(install_script, shell=True, capture_output=True)

    async def _start_model_server(
        self,
        config: DeploymentConfig,
        result: DeploymentResult,
    ) -> None:
        """Inicia o servidor do modelo"""
        runtime = config.runtime
        model_id = config.model_id
        port = config.port

        # Comandos de start por runtime
        if runtime == "vllm" or runtime == ModelRuntime.VLLM:
            cmd = f'''nohup python -m vllm.entrypoints.openai.api_server \
                --model "{model_id}" \
                --port {port} \
                --gpu-memory-utilization {config.gpu_memory_utilization} \
                --trust-remote-code \
                > /tmp/vllm.log 2>&1 &'''

        elif runtime == "transformers" or runtime == ModelRuntime.TRANSFORMERS:
            # Verificar task para escolher servidor
            task = result.model_info.task if result.model_info else "unknown"

            if task == "automatic-speech-recognition":
                # Whisper server
                cmd = self._get_whisper_start_command(model_id, port)
            else:
                # Generic transformers server
                cmd = self._get_transformers_start_command(model_id, port)

        elif runtime == "diffusers" or runtime == ModelRuntime.DIFFUSERS:
            cmd = self._get_diffusers_start_command(model_id, port)

        elif runtime == "sentence-transformers" or runtime == ModelRuntime.SENTENCE_TRANSFORMERS:
            cmd = self._get_embeddings_start_command(model_id, port)

        else:
            raise ValueError(f"Unknown runtime: {runtime}")

        logger.info(f"[DEPLOY] Starting server: {runtime} on port {port}")

        if result.ssh_host:
            # Executar remotamente
            import subprocess
            ssh_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-p", str(result.ssh_port or 22),
                f"root@{result.ssh_host}",
                cmd,
            ]
            subprocess.run(ssh_cmd, capture_output=True, timeout=60)
        else:
            # Executar localmente
            import subprocess
            subprocess.Popen(cmd, shell=True)

    def _get_whisper_start_command(self, model_id: str, port: int) -> str:
        """Comando para iniciar servidor Whisper"""
        return f'''cat > /tmp/whisper_server.py << 'EOF'
import os, torch
from fastapi import FastAPI, UploadFile, File
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import uvicorn, tempfile, librosa

app = FastAPI()
model = WhisperForConditionalGeneration.from_pretrained("{model_id}", torch_dtype=torch.float16).to("cuda")
processor = WhisperProcessor.from_pretrained("{model_id}")

@app.get("/health")
def health(): return {{"status": "healthy"}}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    audio, sr = librosa.load(tmp_path, sr=16000)
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
    inputs = {{k: v.to("cuda") for k, v in inputs.items()}}
    with torch.no_grad():
        ids = model.generate(**inputs)
    text = processor.batch_decode(ids, skip_special_tokens=True)[0]
    os.unlink(tmp_path)
    return {{"text": text}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port})
EOF
pip install librosa -q
nohup python /tmp/whisper_server.py > /tmp/whisper.log 2>&1 &'''

    def _get_transformers_start_command(self, model_id: str, port: int) -> str:
        """Comando para iniciar servidor Transformers genérico"""
        return f'''cat > /tmp/llm_server.py << 'EOF'
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import uvicorn

app = FastAPI()
tokenizer = AutoTokenizer.from_pretrained("{model_id}")
model = AutoModelForCausalLM.from_pretrained("{model_id}", torch_dtype=torch.float16, device_map="auto")

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 256

@app.get("/health")
def health(): return {{"status": "healthy"}}

@app.post("/generate")
def generate(req: GenerateRequest):
    inputs = tokenizer(req.prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=req.max_tokens)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return {{"text": text}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port})
EOF
nohup python /tmp/llm_server.py > /tmp/llm.log 2>&1 &'''

    def _get_diffusers_start_command(self, model_id: str, port: int) -> str:
        """Comando para iniciar servidor Diffusers"""
        return f'''cat > /tmp/diffusion_server.py << 'EOF'
import io, base64, torch
from fastapi import FastAPI
from pydantic import BaseModel
from diffusers import DiffusionPipeline
import uvicorn

app = FastAPI()
pipe = DiffusionPipeline.from_pretrained("{model_id}", torch_dtype=torch.float16).to("cuda")

class GenerateRequest(BaseModel):
    prompt: str
    num_inference_steps: int = 30

@app.get("/health")
def health(): return {{"status": "healthy"}}

@app.post("/generate")
def generate(req: GenerateRequest):
    image = pipe(req.prompt, num_inference_steps=req.num_inference_steps).images[0]
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return {{"image": base64.b64encode(buffer.getvalue()).decode()}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port})
EOF
nohup python /tmp/diffusion_server.py > /tmp/diffusion.log 2>&1 &'''

    def _get_embeddings_start_command(self, model_id: str, port: int) -> str:
        """Comando para iniciar servidor de Embeddings"""
        return f'''cat > /tmp/embeddings_server.py << 'EOF'
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
from sentence_transformers import SentenceTransformer
import uvicorn

app = FastAPI()
model = SentenceTransformer("{model_id}")
model.to("cuda")

class EmbedRequest(BaseModel):
    input: Union[str, List[str]]

@app.get("/health")
def health(): return {{"status": "healthy"}}

@app.post("/v1/embeddings")
def embed(req: EmbedRequest):
    texts = [req.input] if isinstance(req.input, str) else req.input
    embeddings = model.encode(texts).tolist()
    return {{"data": [{{"embedding": e, "index": i}} for i, e in enumerate(embeddings)]}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port})
EOF
nohup python /tmp/embeddings_server.py > /tmp/embeddings.log 2>&1 &'''

    async def _wait_for_health(
        self,
        result: DeploymentResult,
        timeout: int = 300,
        interval: int = 5,
    ) -> bool:
        """Aguarda servidor ficar healthy"""
        import aiohttp

        if not result.ssh_host:
            # Local - assume que está ok
            await asyncio.sleep(5)
            return True

        url = f"http://{result.ssh_host}:{result.port}/health"
        start = time.time()

        while time.time() - start < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            return True
            except:
                pass

            await asyncio.sleep(interval)

        return False

    def _notify(
        self,
        callback: Optional[Callable],
        message: str,
        status: DeploymentStatus,
    ):
        """Notifica callback de progresso"""
        logger.debug(f"[DEPLOY] {status.value}: {message}")
        if callback:
            try:
                callback(message, status)
            except:
                pass

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentResult]:
        """Retorna status de um deployment"""
        return self._deployments.get(deployment_id)

    def list_deployments(self) -> List[DeploymentResult]:
        """Lista todos os deployments"""
        return list(self._deployments.values())

    async def stop_deployment(self, deployment_id: str) -> bool:
        """Para um deployment"""
        result = self._deployments.get(deployment_id)
        if not result:
            return False

        # TODO: Implementar stop via SSH
        result.status = DeploymentStatus.PAUSED
        return True

    async def destroy_deployment(self, deployment_id: str) -> bool:
        """Destrói um deployment e a instância"""
        result = self._deployments.get(deployment_id)
        if not result:
            return False

        if self.gpu_provider and result.instance_id:
            self.gpu_provider.destroy_instance(result.instance_id)

        del self._deployments[deployment_id]
        return True


# Singleton
_service: Optional[ServerlessModelService] = None


def get_model_service(gpu_provider: Optional[Any] = None) -> ServerlessModelService:
    """Retorna instância singleton do service"""
    global _service
    if _service is None:
        _service = ServerlessModelService(gpu_provider=gpu_provider)
    return _service
