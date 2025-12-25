"""
Test: Checkpoint Sync durante Fine-Tuning

Simula um treinamento com múltiplos checkpoints para validar:
1. Sync periódico funciona
2. Checkpoints são salvos no GCS
3. Checkpoints sobrevivem à destruição da GPU
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.gpu.vast import VastService
from src.modules.jobs.executor import JobExecutor
from src.modules.storage import StorageService, StorageConfig, StorageProviderType
from src.config.database import get_session_factory


# Script que simula treinamento com checkpoints
SIMULATED_TRAINING_SCRIPT = '''
#!/bin/bash
set -e

echo "=== Dumont Cloud - Simulated Fine-Tuning ==="
echo "Iniciando treinamento simulado com checkpoints..."

# Criar diretório de output
mkdir -p /workspace/output/checkpoints

# Simular 6 epochs, cada uma salva um checkpoint
for epoch in 1 2 3 4 5 6; do
    echo ""
    echo "=== Epoch $epoch/6 ==="
    echo "[$(date)] Treinando epoch $epoch..."

    # Simular tempo de treino (30 segundos por epoch)
    sleep 30

    # Criar checkpoint
    CHECKPOINT_DIR="/workspace/output/checkpoints/epoch_$epoch"
    mkdir -p $CHECKPOINT_DIR

    # Simular arquivos de checkpoint (modelo, optimizer, scheduler)
    echo "epoch: $epoch" > $CHECKPOINT_DIR/training_state.json
    echo "loss: 0.$((10 - epoch))" >> $CHECKPOINT_DIR/training_state.json
    echo "timestamp: $(date -Iseconds)" >> $CHECKPOINT_DIR/training_state.json

    # Criar arquivo binário fake (simula pesos do modelo)
    dd if=/dev/urandom of=$CHECKPOINT_DIR/model_weights.bin bs=1M count=5 2>/dev/null

    # Criar optimizer state
    dd if=/dev/urandom of=$CHECKPOINT_DIR/optimizer.bin bs=512K count=1 2>/dev/null

    echo "[$(date)] Checkpoint epoch $epoch salvo ($(du -sh $CHECKPOINT_DIR | cut -f1))"

    # Listar o que foi salvo
    ls -la $CHECKPOINT_DIR/
done

echo ""
echo "=== Treinamento Concluído ==="
echo "Total de checkpoints: $(ls /workspace/output/checkpoints/ | wc -l)"
echo "Tamanho total: $(du -sh /workspace/output/ | cut -f1)"

# Criar arquivo final do modelo
echo "Salvando modelo final..."
cp -r /workspace/output/checkpoints/epoch_6 /workspace/output/final_model
echo "training_completed: true" >> /workspace/output/final_model/training_state.json

echo ""
echo "=== Arquivos de Output ==="
find /workspace/output -type f -exec ls -lh {} \\;

echo ""
echo "[$(date)] Fine-tuning simulado concluído com sucesso!"
'''


def run_checkpoint_sync_test():
    """Executa teste de checkpoint sync"""

    print("=" * 60)
    print("TESTE: Checkpoint Sync durante Fine-Tuning")
    print("=" * 60)
    print()

    # Configurar serviços
    vast_api_key = os.environ.get("VAST_API_KEY")
    if not vast_api_key:
        print("ERRO: VAST_API_KEY não configurada")
        return False

    vast_service = VastService(api_key=vast_api_key)
    session_factory = get_session_factory()

    # Configurar storage (GCS)
    storage_config = StorageConfig(
        provider=StorageProviderType.gcs,
        bucket=os.environ.get("GCS_BUCKET", "dumont-jobs-output"),
    )
    storage_service = StorageService(session_factory, storage_config)

    # Criar executor com storage
    executor = JobExecutor(
        vast_service=vast_service,
        execution_timeout=600,  # 10 minutos max
        storage_service=storage_service,
        auto_upload_output=True,
        output_expires_hours=24,
    )

    # Configurar job
    job_id = f"checkpoint_test_{int(time.time())}"
    user_id = "test_user"

    job_config = {
        "job_id": job_id,
        "user_id": user_id,
        "docker_image": "ubuntu:22.04",  # Imagem leve para teste
        "command": SIMULATED_TRAINING_SCRIPT,
        "gpu_name": None,  # Qualquer GPU barata
        "max_price": 0.15,  # Máximo $0.15/hr
        "disk_gb": 20,
        "timeout_seconds": 600,

        # CHECKPOINT SYNC CONFIG
        "checkpoint_sync": {
            "enabled": True,
            "interval_minutes": 1,  # Sync a cada 1 minuto para teste
            "sync_path": "/workspace/output",
        },

        "storage_provider": "gcs",
        "output_expires_hours": 24,
    }

    print(f"Job ID: {job_id}")
    print(f"Checkpoint sync: a cada 1 minuto")
    print(f"Duração estimada: ~3 minutos (6 epochs x 30s)")
    print()

    # Callback de log
    def on_log(level: str, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")

    # Executar
    print("Iniciando job...")
    print("-" * 60)

    start = time.time()
    result = executor.execute(job_config, on_log=on_log)
    duration = time.time() - start

    print("-" * 60)
    print()

    # Resultados
    print("=" * 60)
    print("RESULTADOS")
    print("=" * 60)
    print(f"Sucesso: {result.success}")
    print(f"Exit code: {result.exit_code}")
    print(f"Duração: {duration:.1f}s")
    print(f"Custo: ${result.cost_usd:.4f}")
    print(f"GPU: {result.gpu_name}")
    print()
    print(f"Checkpoint syncs realizados: {result.checkpoint_syncs}")
    print(f"Último checkpoint: {result.last_checkpoint_at}")
    print()

    if result.storage_info:
        print("Storage Info:")
        print(f"  File key: {result.storage_info.file_key}")
        print(f"  Size: {result.storage_info.size_bytes / 1024 / 1024:.2f} MB")
        print(f"  Files: {result.storage_info.file_count}")
        print(f"  Download URL: {result.storage_info.download_url[:100]}...")
        print(f"  Expires: {result.storage_info.expires_at}")

    # Verificar checkpoints no GCS
    print()
    print("=" * 60)
    print("VERIFICANDO CHECKPOINTS NO GCS")
    print("=" * 60)

    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(os.environ.get("GCS_BUCKET", "dumont-jobs-output"))

        checkpoint_prefix = f"checkpoints/{user_id}/{job_id}/"
        blobs = list(bucket.list_blobs(prefix=checkpoint_prefix))

        if blobs:
            print(f"Checkpoints encontrados: {len(blobs)} arquivos")
            total_size = sum(b.size for b in blobs)
            print(f"Tamanho total: {total_size / 1024 / 1024:.2f} MB")
            print()
            print("Arquivos:")
            for blob in blobs[:20]:  # Mostrar primeiros 20
                print(f"  - {blob.name} ({blob.size / 1024:.1f} KB)")
            if len(blobs) > 20:
                print(f"  ... e mais {len(blobs) - 20} arquivos")
        else:
            print("Nenhum checkpoint encontrado no GCS")
            print(f"Prefix buscado: {checkpoint_prefix}")
    except Exception as e:
        print(f"Erro verificando GCS: {e}")

    print()
    print("=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)

    return result.success and result.checkpoint_syncs > 0


if __name__ == "__main__":
    # Carregar .env
    from dotenv import load_dotenv
    load_dotenv()

    success = run_checkpoint_sync_test()
    sys.exit(0 if success else 1)
