#!/usr/bin/env python3
"""
Video Background Remover usando RMBG 2.0 (BRIA AI)
===================================================
Modelo state-of-the-art para remoção de fundo em vídeos.
Funciona em Mac (CPU ou MPS) e Linux/Windows (CPU ou CUDA).

Uso:
    python video_background_remover.py input.mp4 output.mp4

Instalação (Mac):
    pip install torch torchvision transformers pillow opencv-python tqdm

Autor: Claude (Anthropic)
"""

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from tqdm import tqdm


def get_device():
    """Detecta o melhor dispositivo disponível."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        # Mac com Apple Silicon
        return torch.device("mps")
    else:
        return torch.device("cpu")


def load_model(device):
    """Carrega o modelo RMBG 2.0."""
    print("📥 Carregando modelo RMBG 2.0...")
    from transformers import AutoModelForImageSegmentation
    
    model = AutoModelForImageSegmentation.from_pretrained(
        "briaai/RMBG-2.0",
        trust_remote_code=True
    )
    model = model.to(device)
    model.eval()
    print(f"✅ Modelo carregado em: {device}")
    return model


def create_transform():
    """Cria as transformações para o modelo."""
    return transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])


def process_frame(frame, model, transform, device):
    """Processa um único frame e retorna com fundo transparente."""
    # Converte BGR (OpenCV) para RGB (PIL)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    original_size = image.size
    
    # Prepara input
    input_tensor = transform(image).unsqueeze(0).to(device)
    
    # Inferência
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    
    # Processa máscara
    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(original_size, Image.LANCZOS)
    
    # Aplica transparência
    image = image.convert("RGBA")
    mask_array = np.array(mask)
    
    # Cria imagem com alpha
    result = np.array(image)
    result[:, :, 3] = mask_array
    
    return result


def process_frame_with_color_bg(frame, model, transform, device, bg_color=(0, 255, 0)):
    """Processa frame e substitui fundo por uma cor (padrão: verde)."""
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    original_size = image.size
    
    input_tensor = transform(image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    
    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(original_size, Image.LANCZOS)
    mask_array = np.array(mask).astype(np.float32) / 255.0
    
    # Aplica a cor de fundo
    frame_array = np.array(image).astype(np.float32)
    bg = np.full_like(frame_array, bg_color, dtype=np.float32)
    
    # Blend: foreground * mask + background * (1 - mask)
    mask_3ch = np.stack([mask_array] * 3, axis=-1)
    result = frame_array * mask_3ch + bg * (1 - mask_3ch)
    result = result.astype(np.uint8)
    
    return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)


def process_frame_with_image_bg(frame, model, transform, device, bg_image_path):
    """Processa frame e substitui fundo por uma imagem."""
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    original_size = image.size
    
    input_tensor = transform(image).unsqueeze(0).to(device)
    
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()
    
    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(original_size, Image.LANCZOS)
    mask_array = np.array(mask).astype(np.float32) / 255.0
    
    # Carrega imagem de fundo
    bg_image = Image.open(bg_image_path).convert("RGB")
    bg_image = bg_image.resize(original_size, Image.LANCZOS)
    bg_array = np.array(bg_image).astype(np.float32)
    
    # Aplica a imagem de fundo
    frame_array = np.array(image).astype(np.float32)
    
    # Blend: foreground * mask + background * (1 - mask)
    mask_3ch = np.stack([mask_array] * 3, axis=-1)
    result = frame_array * mask_3ch + bg_array * (1 - mask_3ch)
    result = result.astype(np.uint8)
    
    return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)


def process_video(input_path, output_path, transparent=False, bg_color=(0, 255, 0), bg_image_path=None):
    """Processa o vídeo completo."""
    device = get_device()
    model = load_model(device)
    transform = create_transform()
    
    # Abre vídeo
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"❌ Erro ao abrir vídeo: {input_path}")
        sys.exit(1)
    
    # Propriedades do vídeo
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"📹 Vídeo: {width}x{height} @ {fps}fps, {total_frames} frames")
    
    # Configura output
    if transparent:
        # Para vídeo com transparência, usa WebM com VP9
        fourcc = cv2.VideoWriter_fourcc(*'VP90')
        output_path = str(Path(output_path).with_suffix('.webm'))
    else:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print(f"🎬 Processando...")
    
    # Processa frames
    with tqdm(total=total_frames, desc="Frames", unit="frame") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if transparent:
                result = process_frame(frame, model, transform, device)
                # Converte RGBA para BGR para salvar
                result_bgr = cv2.cvtColor(result, cv2.COLOR_RGBA2BGR)
                out.write(result_bgr)
            elif bg_image_path:
                result = process_frame_with_image_bg(frame, model, transform, device, bg_image_path)
                out.write(result)
            else:
                result = process_frame_with_color_bg(frame, model, transform, device, bg_color)
                out.write(result)
            
            pbar.update(1)
    
    cap.release()
    out.release()
    
    print(f"✅ Vídeo salvo em: {output_path}")


def hex_to_rgb(hex_color):
    """Converte cor hex para RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def main():
    parser = argparse.ArgumentParser(
        description="Remove fundo de vídeos usando RMBG 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python video_background_remover.py video.mp4 output.mp4
  python video_background_remover.py video.mp4 output.mp4 --bg-color "#00FF00"
  python video_background_remover.py video.mp4 output.webm --transparent
  python video_background_remover.py video.mp4 output.mp4 --bg-image background.png
        """
    )
    parser.add_argument("input", help="Caminho do vídeo de entrada")
    parser.add_argument("output", help="Caminho do vídeo de saída")
    parser.add_argument(
        "--transparent", "-t",
        action="store_true",
        help="Gera vídeo com fundo transparente (WebM)"
    )
    parser.add_argument(
        "--bg-color", "-c",
        default="#00FF00",
        help="Cor de fundo em hex (padrão: #00FF00 verde)"
    )
    parser.add_argument(
        "--bg-image", "-i",
        help="Caminho para imagem de fundo"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ Arquivo não encontrado: {args.input}")
        sys.exit(1)
    
    if args.bg_image and not os.path.exists(args.bg_image):
        print(f"❌ Imagem de fundo não encontrada: {args.bg_image}")
        sys.exit(1)
    
    bg_color = hex_to_rgb(args.bg_color)
    
    print("=" * 50)
    print("🎥 Video Background Remover - RMBG 2.0")
    print("=" * 50)
    
    process_video(
        args.input,
        args.output,
        transparent=args.transparent,
        bg_color=bg_color,
        bg_image_path=args.bg_image
    )


if __name__ == "__main__":
    main()
