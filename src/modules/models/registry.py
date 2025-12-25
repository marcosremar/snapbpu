"""
Model Registry - Detecção automática de tipo de modelo

Detecta automaticamente o tipo de modelo (LLM, Whisper, Diffusion, etc.)
e o runtime necessário (vLLM, transformers, diffusers).

Estratégia:
1. Primeiro tenta mapeamento estático (zero API calls)
2. Se não encontrar, busca na API do HuggingFace
3. Cacheia resultado localmente para não repetir

Fonte dos dados: https://huggingface.co/docs/hub/en/models-tasks
"""

import os
import json
import time
import logging
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ModelTask(str, Enum):
    """Tipos de tarefas suportadas"""
    TEXT_GENERATION = "text-generation"
    CHAT = "text-generation"  # Alias
    SPEECH_RECOGNITION = "automatic-speech-recognition"
    TEXT_TO_IMAGE = "text-to-image"
    IMAGE_TO_TEXT = "image-to-text"
    IMAGE_TEXT_TO_TEXT = "image-text-to-text"  # VLMs
    FEATURE_EXTRACTION = "feature-extraction"  # Embeddings
    TEXT_TO_VIDEO = "text-to-video"
    TEXT_TO_SPEECH = "text-to-speech"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question-answering"
    OBJECT_DETECTION = "object-detection"
    IMAGE_CLASSIFICATION = "image-classification"
    UNKNOWN = "unknown"


class ModelRuntime(str, Enum):
    """Runtimes disponíveis para servir modelos"""
    VLLM = "vllm"                      # LLMs - melhor performance
    TRANSFORMERS = "transformers"       # Genérico
    DIFFUSERS = "diffusers"            # Stable Diffusion, FLUX
    SENTENCE_TRANSFORMERS = "sentence-transformers"  # Embeddings
    WHISPER = "whisper"                # Speech (usa transformers internamente)
    ONNX = "onnx"                      # Modelos otimizados
    UNKNOWN = "unknown"


@dataclass
class ModelInfo:
    """Informações detectadas sobre um modelo"""
    model_id: str
    task: str
    runtime: str
    library: str

    # Metadados opcionais
    size_gb: Optional[float] = None
    requires_gpu: bool = True
    min_vram_gb: Optional[float] = None
    default_port: int = 8000

    # Cache metadata
    cached_at: Optional[float] = None
    source: str = "unknown"  # "static", "api", "cache"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ModelInfo":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# MAPEAMENTO ESTÁTICO - Zero API calls para modelos conhecidos
# =============================================================================

# Prefixos conhecidos -> configuração
KNOWN_MODEL_PREFIXES: Dict[str, Dict[str, Any]] = {
    # LLMs - usar vLLM
    "meta-llama/": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },
    "mistralai/": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },
    "microsoft/Phi": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },
    "Qwen/Qwen2": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },
    "google/gemma": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },
    "deepseek-ai/": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },
    "NousResearch/": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },
    "teknium/": {
        "task": ModelTask.TEXT_GENERATION,
        "runtime": ModelRuntime.VLLM,
        "library": "transformers",
        "default_port": 8000,
    },

    # Speech Recognition - Whisper
    "openai/whisper": {
        "task": ModelTask.SPEECH_RECOGNITION,
        "runtime": ModelRuntime.TRANSFORMERS,
        "library": "transformers",
        "default_port": 8001,
    },
    "distil-whisper/": {
        "task": ModelTask.SPEECH_RECOGNITION,
        "runtime": ModelRuntime.TRANSFORMERS,
        "library": "transformers",
        "default_port": 8001,
    },

    # Image Generation - Diffusers
    "stabilityai/": {
        "task": ModelTask.TEXT_TO_IMAGE,
        "runtime": ModelRuntime.DIFFUSERS,
        "library": "diffusers",
        "default_port": 8002,
    },
    "black-forest-labs/": {
        "task": ModelTask.TEXT_TO_IMAGE,
        "runtime": ModelRuntime.DIFFUSERS,
        "library": "diffusers",
        "default_port": 8002,
    },
    "runwayml/": {
        "task": ModelTask.TEXT_TO_IMAGE,
        "runtime": ModelRuntime.DIFFUSERS,
        "library": "diffusers",
        "default_port": 8002,
    },
    "CompVis/": {
        "task": ModelTask.TEXT_TO_IMAGE,
        "runtime": ModelRuntime.DIFFUSERS,
        "library": "diffusers",
        "default_port": 8002,
    },

    # Embeddings - Sentence Transformers
    "BAAI/bge": {
        "task": ModelTask.FEATURE_EXTRACTION,
        "runtime": ModelRuntime.SENTENCE_TRANSFORMERS,
        "library": "sentence-transformers",
        "default_port": 8003,
        "requires_gpu": False,  # Pode rodar em CPU
    },
    "sentence-transformers/": {
        "task": ModelTask.FEATURE_EXTRACTION,
        "runtime": ModelRuntime.SENTENCE_TRANSFORMERS,
        "library": "sentence-transformers",
        "default_port": 8003,
        "requires_gpu": False,
    },
    "intfloat/": {
        "task": ModelTask.FEATURE_EXTRACTION,
        "runtime": ModelRuntime.SENTENCE_TRANSFORMERS,
        "library": "sentence-transformers",
        "default_port": 8003,
        "requires_gpu": False,
    },
    "thenlper/": {
        "task": ModelTask.FEATURE_EXTRACTION,
        "runtime": ModelRuntime.SENTENCE_TRANSFORMERS,
        "library": "sentence-transformers",
        "default_port": 8003,
        "requires_gpu": False,
    },

    # Vision-Language Models (VLMs)
    "llava-hf/": {
        "task": ModelTask.IMAGE_TEXT_TO_TEXT,
        "runtime": ModelRuntime.TRANSFORMERS,
        "library": "transformers",
        "default_port": 8004,
    },
    "Qwen/Qwen2-VL": {
        "task": ModelTask.IMAGE_TEXT_TO_TEXT,
        "runtime": ModelRuntime.TRANSFORMERS,
        "library": "transformers",
        "default_port": 8004,
    },
    "HuggingFaceTB/SmolVLM": {
        "task": ModelTask.IMAGE_TEXT_TO_TEXT,
        "runtime": ModelRuntime.TRANSFORMERS,
        "library": "transformers",
        "default_port": 8004,
    },

    # Video Generation
    "damo-vilab/": {
        "task": ModelTask.TEXT_TO_VIDEO,
        "runtime": ModelRuntime.DIFFUSERS,
        "library": "diffusers",
        "default_port": 8005,
    },
    "cerspense/": {
        "task": ModelTask.TEXT_TO_VIDEO,
        "runtime": ModelRuntime.DIFFUSERS,
        "library": "diffusers",
        "default_port": 8005,
    },
}

# Estimativas de tamanho por modelo (aproximado)
MODEL_SIZE_ESTIMATES: Dict[str, float] = {
    # LLMs
    "7b": 14.0,
    "8b": 16.0,
    "13b": 26.0,
    "70b": 140.0,
    "72b": 144.0,

    # Whisper
    "whisper-tiny": 0.15,
    "whisper-base": 0.3,
    "whisper-small": 1.0,
    "whisper-medium": 3.0,
    "whisper-large": 6.0,

    # Diffusion
    "sd-1.5": 8.0,
    "sdxl": 14.0,
    "flux": 24.0,
}


# =============================================================================
# MAPEAMENTO DE TASK -> RUNTIME
# =============================================================================

TASK_TO_RUNTIME: Dict[str, ModelRuntime] = {
    "text-generation": ModelRuntime.VLLM,
    "text2text-generation": ModelRuntime.VLLM,
    "conversational": ModelRuntime.VLLM,
    "automatic-speech-recognition": ModelRuntime.TRANSFORMERS,
    "text-to-image": ModelRuntime.DIFFUSERS,
    "image-to-image": ModelRuntime.DIFFUSERS,
    "text-to-video": ModelRuntime.DIFFUSERS,
    "feature-extraction": ModelRuntime.SENTENCE_TRANSFORMERS,
    "sentence-similarity": ModelRuntime.SENTENCE_TRANSFORMERS,
    "image-text-to-text": ModelRuntime.TRANSFORMERS,
    "visual-question-answering": ModelRuntime.TRANSFORMERS,
    "image-to-text": ModelRuntime.TRANSFORMERS,
    "text-to-speech": ModelRuntime.TRANSFORMERS,
    "translation": ModelRuntime.TRANSFORMERS,
    "summarization": ModelRuntime.TRANSFORMERS,
    "question-answering": ModelRuntime.TRANSFORMERS,
    "fill-mask": ModelRuntime.TRANSFORMERS,
    "token-classification": ModelRuntime.TRANSFORMERS,
    "text-classification": ModelRuntime.TRANSFORMERS,
    "object-detection": ModelRuntime.TRANSFORMERS,
    "image-classification": ModelRuntime.TRANSFORMERS,
    "image-segmentation": ModelRuntime.TRANSFORMERS,
    "depth-estimation": ModelRuntime.TRANSFORMERS,
}

TASK_TO_PORT: Dict[str, int] = {
    "text-generation": 8000,
    "automatic-speech-recognition": 8001,
    "text-to-image": 8002,
    "feature-extraction": 8003,
    "image-text-to-text": 8004,
    "text-to-video": 8005,
}


class ModelRegistry:
    """
    Registry de modelos com detecção automática de tipo.

    Uso:
        registry = ModelRegistry()
        info = registry.get_model_info("meta-llama/Llama-3.1-8B-Instruct")
        print(info.task)     # "text-generation"
        print(info.runtime)  # "vllm"
    """

    # Cache em memória
    _cache: Dict[str, ModelInfo] = {}

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Args:
            cache_dir: Diretório para cache persistente.
                       Default: ~/.cache/dumont/models
        """
        self.cache_dir = Path(cache_dir or os.path.expanduser("~/.cache/dumont/models"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "registry_cache.json"

        # Carregar cache do disco
        self._load_cache()

    def get_model_info(self, model_id: str, force_refresh: bool = False) -> ModelInfo:
        """
        Obtém informações sobre um modelo.

        Args:
            model_id: ID do modelo no HuggingFace (ex: "meta-llama/Llama-3.1-8B")
            force_refresh: Se True, ignora cache e busca na API

        Returns:
            ModelInfo com task, runtime, library, etc.
        """
        # 1. Tentar cache em memória
        if not force_refresh and model_id in self._cache:
            logger.debug(f"[REGISTRY] Cache hit (memory): {model_id}")
            return self._cache[model_id]

        # 2. Tentar mapeamento estático (zero API)
        static_info = self._try_static_mapping(model_id)
        if static_info:
            logger.info(f"[REGISTRY] Static match: {model_id} -> {static_info.runtime}")
            self._cache[model_id] = static_info
            return static_info

        # 3. Tentar cache em disco
        if not force_refresh:
            disk_info = self._try_disk_cache(model_id)
            if disk_info:
                logger.debug(f"[REGISTRY] Cache hit (disk): {model_id}")
                self._cache[model_id] = disk_info
                return disk_info

        # 4. Buscar na API do HuggingFace
        api_info = self._fetch_from_api(model_id)
        if api_info:
            logger.info(f"[REGISTRY] API fetch: {model_id} -> {api_info.runtime}")
            self._cache[model_id] = api_info
            self._save_cache()
            return api_info

        # 5. Fallback: assumir genérico
        logger.warning(f"[REGISTRY] Unknown model, using defaults: {model_id}")
        fallback = ModelInfo(
            model_id=model_id,
            task=ModelTask.UNKNOWN,
            runtime=ModelRuntime.TRANSFORMERS,
            library="transformers",
            source="fallback",
        )
        self._cache[model_id] = fallback
        return fallback

    def _try_static_mapping(self, model_id: str) -> Optional[ModelInfo]:
        """Tenta encontrar no mapeamento estático (zero API calls)"""
        for prefix, config in KNOWN_MODEL_PREFIXES.items():
            if model_id.startswith(prefix) or prefix in model_id:
                return ModelInfo(
                    model_id=model_id,
                    task=config["task"].value if isinstance(config["task"], Enum) else config["task"],
                    runtime=config["runtime"].value if isinstance(config["runtime"], Enum) else config["runtime"],
                    library=config.get("library", "transformers"),
                    default_port=config.get("default_port", 8000),
                    requires_gpu=config.get("requires_gpu", True),
                    size_gb=self._estimate_size(model_id),
                    source="static",
                    cached_at=time.time(),
                )
        return None

    def _estimate_size(self, model_id: str) -> Optional[float]:
        """Estima tamanho do modelo baseado no nome"""
        model_lower = model_id.lower()

        for pattern, size in MODEL_SIZE_ESTIMATES.items():
            if pattern in model_lower:
                return size

        return None

    def _try_disk_cache(self, model_id: str) -> Optional[ModelInfo]:
        """Tenta carregar do cache em disco"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    if model_id in cache_data:
                        info = ModelInfo.from_dict(cache_data[model_id])
                        info.source = "cache"
                        return info
        except Exception as e:
            logger.warning(f"[REGISTRY] Failed to read cache: {e}")
        return None

    def _fetch_from_api(self, model_id: str) -> Optional[ModelInfo]:
        """Busca informações na API do HuggingFace"""
        try:
            url = f"https://huggingface.co/api/models/{model_id}"

            headers = {}
            hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 429:
                logger.warning(f"[REGISTRY] Rate limited by HuggingFace API")
                return None

            if response.status_code != 200:
                logger.warning(f"[REGISTRY] API returned {response.status_code} for {model_id}")
                return None

            data = response.json()

            task = data.get("pipeline_tag", "unknown")
            library = data.get("library_name", "transformers")

            # Determinar runtime baseado na task
            runtime = TASK_TO_RUNTIME.get(task, ModelRuntime.TRANSFORMERS)

            # Se library é vllm, usar vllm
            if library == "vllm":
                runtime = ModelRuntime.VLLM

            return ModelInfo(
                model_id=model_id,
                task=task,
                runtime=runtime.value if isinstance(runtime, Enum) else runtime,
                library=library,
                default_port=TASK_TO_PORT.get(task, 8000),
                size_gb=self._estimate_size(model_id),
                source="api",
                cached_at=time.time(),
            )

        except requests.exceptions.Timeout:
            logger.warning(f"[REGISTRY] API timeout for {model_id}")
            return None
        except Exception as e:
            logger.warning(f"[REGISTRY] API error for {model_id}: {e}")
            return None

    def _load_cache(self):
        """Carrega cache do disco"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    for model_id, info_dict in cache_data.items():
                        self._cache[model_id] = ModelInfo.from_dict(info_dict)
                logger.debug(f"[REGISTRY] Loaded {len(self._cache)} models from cache")
        except Exception as e:
            logger.warning(f"[REGISTRY] Failed to load cache: {e}")

    def _save_cache(self):
        """Salva cache no disco"""
        try:
            cache_data = {
                model_id: info.to_dict()
                for model_id, info in self._cache.items()
                if info.source in ("api", "cache")  # Só salva API results
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"[REGISTRY] Failed to save cache: {e}")

    def clear_cache(self):
        """Limpa cache em memória e disco"""
        self._cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("[REGISTRY] Cache cleared")

    def list_known_prefixes(self) -> List[str]:
        """Lista prefixos conhecidos (mapeamento estático)"""
        return list(KNOWN_MODEL_PREFIXES.keys())

    def get_runtime_for_task(self, task: str) -> str:
        """Retorna runtime recomendado para uma task"""
        runtime = TASK_TO_RUNTIME.get(task, ModelRuntime.TRANSFORMERS)
        return runtime.value if isinstance(runtime, Enum) else runtime


# Singleton
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Retorna instância singleton do registry"""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def detect_model(model_id: str) -> ModelInfo:
    """Atalho para get_registry().get_model_info()"""
    return get_registry().get_model_info(model_id)
