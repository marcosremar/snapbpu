"""
Runtime Templates for Model Deployment
Provides templates and scripts for deploying different model types
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class RuntimeTemplate:
    """Template for a model runtime"""
    type: str
    name: str
    description: str
    runtime: str
    default_port: int
    gpu_memory_required: float  # GB
    install_script: str
    start_script: str
    health_check_script: str
    popular_models: List[Dict[str, str]]


# LLM Template (vLLM)
LLM_TEMPLATE = RuntimeTemplate(
    type="llm",
    name="LLM (Chat/Completion)",
    description="Deploy large language models for chat and text generation using vLLM",
    runtime="vllm",
    default_port=8000,
    gpu_memory_required=8.0,
    install_script="""#!/bin/bash
set -e
echo "Installing vLLM..."
pip install vllm --quiet
echo "vLLM installed successfully"
""",
    start_script="""#!/bin/bash
set -e
MODEL_ID="${MODEL_ID:-meta-llama/Llama-3.1-8B-Instruct}"
PORT="${PORT:-8000}"
GPU_MEMORY="${GPU_MEMORY_UTILIZATION:-0.9}"

echo "Starting vLLM server..."
echo "Model: $MODEL_ID"
echo "Port: $PORT"

echo "Starting vLLM server on port $PORT..."
# Run in foreground to keep container alive
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_ID" \
    --port "$PORT" \
    --gpu-memory-utilization "$GPU_MEMORY" \
    --trust-remote-code \
    2>&1 | tee /tmp/vllm.log
""",
    health_check_script="""#!/bin/bash
PORT="${PORT:-8000}"
curl -s "http://localhost:$PORT/health" > /dev/null 2>&1
""",
    popular_models=[
        {"id": "meta-llama/Llama-3.1-8B-Instruct", "name": "Llama 3.1 8B", "size": "16GB"},
        {"id": "mistralai/Mistral-7B-Instruct-v0.3", "name": "Mistral 7B", "size": "14GB"},
        {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 7B", "size": "14GB"},
        {"id": "microsoft/Phi-3-mini-4k-instruct", "name": "Phi-3 Mini", "size": "8GB"},
        {"id": "google/gemma-2-9b-it", "name": "Gemma 2 9B", "size": "18GB"},
    ]
)

# Speech Template (Whisper)
SPEECH_TEMPLATE = RuntimeTemplate(
    type="speech",
    name="Speech-to-Text (Whisper)",
    description="Deploy Whisper models for audio transcription",
    runtime="pytorch",
    default_port=8001,
    gpu_memory_required=4.0,
    install_script="""#!/bin/bash
set -e
echo "Installing Whisper dependencies..."
pip install transformers accelerate torch --quiet
pip install fastapi uvicorn python-multipart --quiet
echo "Whisper dependencies installed"
""",
    start_script="""#!/bin/bash
set -e
MODEL_ID="${MODEL_ID:-openai/whisper-large-v3}"
PORT="${PORT:-8001}"

cat > /tmp/whisper_server.py << 'PYEOF'
import os
import torch
from fastapi import FastAPI, UploadFile, File
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import uvicorn
import tempfile

app = FastAPI()
model_id = os.environ.get("MODEL_ID", "openai/whisper-large-v3")

print(f"Loading model: {model_id}")
processor = WhisperProcessor.from_pretrained(model_id)
model = WhisperForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.float16)
model.to("cuda")
print("Model loaded!")

@app.get("/health")
def health():
    return {"status": "healthy", "model": model_id}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    import librosa
    audio, sr = librosa.load(tmp_path, sr=16000)
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}

    with torch.no_grad():
        generated_ids = model.generate(**inputs)
    transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    os.unlink(tmp_path)
    return {"text": transcription}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8001)))
PYEOF

pip install librosa --quiet
echo "Starting Whisper server on port $PORT..."
# Run in foreground to keep container alive
MODEL_ID="$MODEL_ID" PORT="$PORT" python /tmp/whisper_server.py 2>&1 | tee /tmp/whisper.log
""",
    health_check_script="""#!/bin/bash
PORT="${PORT:-8001}"
curl -s "http://localhost:$PORT/health" > /dev/null 2>&1
""",
    popular_models=[
        {"id": "openai/whisper-large-v3", "name": "Whisper Large V3", "size": "6GB"},
        {"id": "openai/whisper-medium", "name": "Whisper Medium", "size": "3GB"},
        {"id": "openai/whisper-small", "name": "Whisper Small", "size": "1GB"},
        {"id": "openai/whisper-base", "name": "Whisper Base", "size": "500MB"},
    ]
)

# Image Template (Diffusers)
IMAGE_TEMPLATE = RuntimeTemplate(
    type="image",
    name="Image Generation (Diffusion)",
    description="Deploy Stable Diffusion and FLUX models for image generation",
    runtime="diffusers",
    default_port=8002,
    gpu_memory_required=12.0,
    install_script="""#!/bin/bash
set -e
echo "Installing Diffusers dependencies..."
pip install diffusers transformers accelerate torch --quiet
pip install fastapi uvicorn --quiet
echo "Diffusers dependencies installed"
""",
    start_script="""#!/bin/bash
set -e
MODEL_ID="${MODEL_ID:-stabilityai/stable-diffusion-xl-base-1.0}"
PORT="${PORT:-8002}"

cat > /tmp/diffusion_server.py << 'PYEOF'
import os
import io
import base64
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from diffusers import DiffusionPipeline
import uvicorn

app = FastAPI()
model_id = os.environ.get("MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")

print(f"Loading model: {model_id}")
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
pipe.to("cuda")
print("Model loaded!")

class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    width: int = 1024
    height: int = 1024

@app.get("/health")
def health():
    return {"status": "healthy", "model": model_id}

@app.post("/generate")
def generate(req: GenerateRequest):
    image = pipe(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        num_inference_steps=req.num_inference_steps,
        guidance_scale=req.guidance_scale,
        width=req.width,
        height=req.height,
    ).images[0]

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return {"image": img_str}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8002)))
PYEOF

echo "Starting Diffusion server on port $PORT..."
# Run in foreground to keep container alive
MODEL_ID="$MODEL_ID" PORT="$PORT" python /tmp/diffusion_server.py 2>&1 | tee /tmp/diffusion.log
""",
    health_check_script="""#!/bin/bash
PORT="${PORT:-8002}"
curl -s "http://localhost:$PORT/health" > /dev/null 2>&1
""",
    popular_models=[
        {"id": "stabilityai/stable-diffusion-xl-base-1.0", "name": "SDXL Base", "size": "14GB"},
        {"id": "black-forest-labs/FLUX.1-schnell", "name": "FLUX.1 Schnell", "size": "24GB"},
        {"id": "runwayml/stable-diffusion-v1-5", "name": "SD 1.5", "size": "8GB"},
        {"id": "stabilityai/sdxl-turbo", "name": "SDXL Turbo", "size": "14GB"},
    ]
)

# Embeddings Template
EMBEDDINGS_TEMPLATE = RuntimeTemplate(
    type="embeddings",
    name="Text Embeddings",
    description="Deploy embedding models for vector search and RAG",
    runtime="sentence-transformers",
    default_port=8003,
    gpu_memory_required=2.0,
    install_script="""
echo "Installing embedding dependencies..."
pip install sentence-transformers torch --quiet
pip install fastapi uvicorn --quiet
echo "Embedding dependencies installed"
""",
    start_script="""
echo "[$(date)] Starting embeddings server setup" >> /var/log/dumont-deploy.log
echo "[$(date)] MODEL_ID=$MODEL_ID PORT=$PORT" >> /var/log/dumont-deploy.log

cat > /tmp/embeddings_server.py << 'PYEOF'
import os
import time
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
from sentence_transformers import SentenceTransformer
import uvicorn

app = FastAPI()
model_id = os.environ.get("MODEL_ID", "BAAI/bge-large-en-v1.5")

print(f"Loading model: {model_id}")
model = SentenceTransformer(model_id)
model.to("cuda")
print("Model loaded!")

# OpenAI-compatible request/response models
class EmbeddingRequest(BaseModel):
    model: str = ""
    input: Union[str, List[str]]

class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: dict

@app.get("/health")
def health():
    return {"status": "healthy", "model": model_id}

@app.post("/v1/embeddings")
def create_embeddings(req: EmbeddingRequest):
    # Handle both string and list inputs
    texts = [req.input] if isinstance(req.input, str) else req.input

    embeddings = model.encode(texts, convert_to_numpy=True)

    data = [
        EmbeddingData(embedding=emb.tolist(), index=i)
        for i, emb in enumerate(embeddings)
    ]

    return EmbeddingResponse(
        data=data,
        model=model_id,
        usage={"prompt_tokens": sum(len(t.split()) for t in texts), "total_tokens": sum(len(t.split()) for t in texts)}
    )

# Legacy endpoint for backwards compatibility
class LegacyEmbedRequest(BaseModel):
    texts: List[str]

@app.post("/embed")
def embed(req: LegacyEmbedRequest):
    embeddings = model.encode(req.texts, convert_to_numpy=True)
    return {"embeddings": embeddings.tolist()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8003)))
PYEOF

echo "[$(date)] Starting embeddings server on port $PORT..." >> /var/log/dumont-deploy.log
echo "Starting embeddings server on port $PORT..."
# Run in foreground to keep container alive
MODEL_ID="$MODEL_ID" PORT="$PORT" python /tmp/embeddings_server.py 2>&1 | tee -a /var/log/dumont-deploy.log
""",
    health_check_script="""#!/bin/bash
PORT="${PORT:-8003}"
curl -s "http://localhost:$PORT/health" > /dev/null 2>&1
""",
    popular_models=[
        {"id": "BAAI/bge-large-en-v1.5", "name": "BGE Large", "size": "2GB"},
        {"id": "sentence-transformers/all-MiniLM-L6-v2", "name": "MiniLM L6", "size": "100MB"},
        {"id": "intfloat/e5-large-v2", "name": "E5 Large", "size": "2GB"},
        {"id": "thenlper/gte-large", "name": "GTE Large", "size": "2GB"},
    ]
)


# Vision Template (VLM - Image to Text)
VISION_TEMPLATE = RuntimeTemplate(
    type="vision",
    name="Vision (Image Understanding)",
    description="Deploy Vision-Language Models for image analysis, OCR, and visual question answering",
    runtime="transformers",
    default_port=8004,
    gpu_memory_required=2.0,
    install_script="""#!/bin/bash
set -e
echo "Installing Vision dependencies..."
pip install transformers accelerate torch pillow --quiet
pip install fastapi uvicorn python-multipart --quiet
echo "Vision dependencies installed"
""",
    start_script="""#!/bin/bash
set -e
MODEL_ID="${MODEL_ID:-HuggingFaceTB/SmolVLM-256M-Instruct}"
PORT="${PORT:-8004}"

cat > /tmp/vision_server.py << 'PYEOF'
import os
import io
import base64
import torch
from fastapi import FastAPI, UploadFile, File, Form
from PIL import Image
from transformers import AutoProcessor, AutoModelForVision2Seq
import uvicorn

app = FastAPI()
model_id = os.environ.get("MODEL_ID", "HuggingFaceTB/SmolVLM-256M-Instruct")

print(f"Loading model: {model_id}")
processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForVision2Seq.from_pretrained(model_id, torch_dtype=torch.float16, trust_remote_code=True)
model.to("cuda")
print("Model loaded!")

@app.get("/health")
def health():
    return {"status": "healthy", "model": model_id}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), prompt: str = Form("Describe this image")):
    content = await file.read()
    image = Image.open(io.BytesIO(content)).convert("RGB")

    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}

    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=256)
    response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    return {"response": response}

@app.post("/analyze_base64")
async def analyze_base64(image_base64: str, prompt: str = "Describe this image"):
    image_data = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_data)).convert("RGB")

    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt_text, images=[image], return_tensors="pt")
    inputs = {k: v.to("cuda") for k, v in inputs.items()}

    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=256)
    response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8004)))
PYEOF

echo "Starting Vision server on port $PORT..."
# Run in foreground to keep container alive
MODEL_ID="$MODEL_ID" PORT="$PORT" python /tmp/vision_server.py 2>&1 | tee /tmp/vision.log
""",
    health_check_script="""#!/bin/bash
PORT="${PORT:-8004}"
curl -s "http://localhost:$PORT/health" > /dev/null 2>&1
""",
    popular_models=[
        {"id": "HuggingFaceTB/SmolVLM-256M-Instruct", "name": "SmolVLM 256M", "size": "500MB"},
        {"id": "HuggingFaceTB/SmolVLM-Instruct", "name": "SmolVLM 2B", "size": "4GB"},
        {"id": "llava-hf/llava-1.5-7b-hf", "name": "LLaVA 1.5 7B", "size": "14GB"},
        {"id": "Qwen/Qwen2-VL-2B-Instruct", "name": "Qwen2-VL 2B", "size": "4GB"},
    ]
)

# Video Template (Text to Video)
VIDEO_TEMPLATE = RuntimeTemplate(
    type="video",
    name="Video Generation",
    description="Deploy video generation models for creating videos from text prompts",
    runtime="diffusers",
    default_port=8005,
    gpu_memory_required=16.0,
    install_script="""#!/bin/bash
set -e
echo "Installing Video generation dependencies..."
pip install diffusers transformers accelerate torch --quiet
pip install imageio imageio-ffmpeg --quiet
pip install fastapi uvicorn --quiet
echo "Video dependencies installed"
""",
    start_script="""#!/bin/bash
set -e
MODEL_ID="${MODEL_ID:-damo-vilab/text-to-video-ms-1.7b}"
PORT="${PORT:-8005}"

cat > /tmp/video_server.py << 'PYEOF'
import os
import io
import base64
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from diffusers import DiffusionPipeline
import imageio
import uvicorn
import tempfile

app = FastAPI()
model_id = os.environ.get("MODEL_ID", "damo-vilab/text-to-video-ms-1.7b")

print(f"Loading model: {model_id}")
pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
pipe.to("cuda")
# Enable memory efficient attention if available
try:
    pipe.enable_model_cpu_offload()
except:
    pass
print("Model loaded!")

class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_inference_steps: int = 25
    num_frames: int = 16
    guidance_scale: float = 7.5

@app.get("/health")
def health():
    return {"status": "healthy", "model": model_id}

@app.post("/generate")
def generate(req: GenerateRequest):
    video_frames = pipe(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        num_inference_steps=req.num_inference_steps,
        num_frames=req.num_frames,
        guidance_scale=req.guidance_scale,
    ).frames[0]

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        imageio.mimsave(tmp.name, video_frames, fps=8)
        tmp.seek(0)
        with open(tmp.name, "rb") as f:
            video_bytes = f.read()
        os.unlink(tmp.name)

    video_base64 = base64.b64encode(video_bytes).decode()
    return {"video": video_base64, "format": "mp4"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8005)))
PYEOF

echo "Starting Video server on port $PORT..."
# Run in foreground to keep container alive
MODEL_ID="$MODEL_ID" PORT="$PORT" python /tmp/video_server.py 2>&1 | tee /tmp/video.log
""",
    health_check_script="""#!/bin/bash
PORT="${PORT:-8005}"
curl -s "http://localhost:$PORT/health" > /dev/null 2>&1
""",
    popular_models=[
        {"id": "damo-vilab/text-to-video-ms-1.7b", "name": "ModelScope 1.7B", "size": "8GB"},
        {"id": "cerspense/zeroscope_v2_576w", "name": "Zeroscope V2", "size": "8GB"},
        {"id": "THUDM/CogVideoX-2b", "name": "CogVideoX 2B", "size": "10GB"},
        {"id": "genmo/mochi-1-preview", "name": "Mochi 1", "size": "20GB"},
    ]
)


# Template registry
TEMPLATES: Dict[str, RuntimeTemplate] = {
    "llm": LLM_TEMPLATE,
    "speech": SPEECH_TEMPLATE,
    "image": IMAGE_TEMPLATE,
    "embeddings": EMBEDDINGS_TEMPLATE,
    "vision": VISION_TEMPLATE,
    "video": VIDEO_TEMPLATE,
}


def get_template(model_type: str) -> RuntimeTemplate:
    """Get template for model type"""
    if model_type not in TEMPLATES:
        raise ValueError(f"Unknown model type: {model_type}. Available: {list(TEMPLATES.keys())}")
    return TEMPLATES[model_type]


def get_all_templates() -> List[Dict[str, Any]]:
    """Get all templates as dictionaries"""
    return [
        {
            "type": t.type,
            "name": t.name,
            "description": t.description,
            "runtime": t.runtime,
            "default_port": t.default_port,
            "gpu_memory_required": t.gpu_memory_required,
            "popular_models": t.popular_models,
        }
        for t in TEMPLATES.values()
    ]


def get_install_script(model_type: str) -> str:
    """Get install script for model type"""
    return get_template(model_type).install_script


def get_start_script(model_type: str, model_id: str, port: int) -> str:
    """Get start script with environment variables set"""
    template = get_template(model_type)
    script = template.start_script
    # The script uses environment variables, so we prepend exports (no shebang, parent script has it)
    return f"""export MODEL_ID="{model_id}"
export PORT="{port}"
{script}
"""


def get_health_check_script(model_type: str, port: int) -> str:
    """Get health check script"""
    template = get_template(model_type)
    return f"""#!/bin/bash
export PORT="{port}"
{template.health_check_script}
"""
