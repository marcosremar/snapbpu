"""
Teste REAL de Fine-Tuning usando o módulo Jobs.

Este teste:
1. Cria um job de fine-tuning com DistilGPT-2 (82M params)
2. Submete para execução em GPU VAST.ai
3. Aguarda conclusão
4. Verifica se o modelo foi treinado

AVISO: Este teste usa créditos REAIS da VAST.ai!

Uso:
    python -m tests.modules.jobs.test_finetune_real
"""

import os
import sys
import time
import json
import logging

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.services.gpu.vast import VastService
from src.modules.jobs.executor import JobExecutor, ExecutionResult


def get_vast_api_key() -> str:
    """Obtém API key do VAST.ai."""
    # 1. Tentar variável de ambiente
    key = os.environ.get("VAST_API_KEY")
    if key:
        return key

    # 2. Tentar arquivo .env
    env_file = os.path.join(os.path.dirname(__file__), "../../../.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("VAST_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"\'')

    # 3. Tentar arquivo de credenciais
    cred_file = os.path.expanduser("~/.credentials/vast_api_key")
    if os.path.exists(cred_file):
        with open(cred_file) as f:
            return f.read().strip()

    raise ValueError("VAST_API_KEY não encontrada")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Dataset simples para fine-tuning (conversas sobre Dumont Cloud)
TRAINING_DATA = [
    {"text": "### Human: O que é o Dumont Cloud?\n### Assistant: O Dumont Cloud é uma plataforma de GPU sob demanda que permite alugar GPUs poderosas para machine learning e IA por preços acessíveis."},
    {"text": "### Human: Como funciona o sistema de jobs?\n### Assistant: O sistema de jobs do Dumont Cloud permite submeter tarefas de ML como fine-tuning, treinamento e inferência. A plataforma provisiona uma GPU, executa o job e destrói a instância automaticamente."},
    {"text": "### Human: Qual GPU é melhor para fine-tuning?\n### Assistant: Para fine-tuning de modelos pequenos, uma RTX 3090 ou RTX 4090 são excelentes escolhas. Elas oferecem boa relação custo-benefício com 24GB de VRAM."},
    {"text": "### Human: Quanto custa usar o Dumont Cloud?\n### Assistant: Os preços variam de acordo com a GPU escolhida. GPUs como RTX 3090 custam cerca de $0.20-0.40/hora, enquanto A100s podem custar $1-2/hora."},
    {"text": "### Human: O que é serverless GPU?\n### Assistant: Serverless GPU é um modo onde a GPU é pausada quando não está em uso, reduzindo custos. Quando você precisa, ela acorda em segundos, pronta para processar."},
    {"text": "### Human: Posso fazer fine-tuning de LLMs?\n### Assistant: Sim! O Dumont Cloud suporta fine-tuning de modelos como LLaMA, Mistral, GPT-2 e outros. Usamos técnicas como LoRA para treinar eficientemente mesmo em GPUs com menos VRAM."},
    {"text": "### Human: Como faço deploy de um modelo?\n### Assistant: Você pode fazer deploy usando nosso sistema de jobs. Basta criar um job com a imagem Docker, comando e configurações. A plataforma cuida do resto."},
    {"text": "### Human: O que acontece se o job falhar?\n### Assistant: O sistema tem retry automático. Se um job falhar, ele é reexecutado automaticamente até o limite configurado. Você também recebe logs detalhados para debugging."},
]


def create_finetune_script() -> str:
    """Cria o script de fine-tuning que será executado na GPU."""
    return '''#!/bin/bash
set -e

echo "=== Iniciando Fine-Tuning de DistilGPT-2 ==="
echo "Data: $(date)"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
echo ""

# Instalar dependências (reinstalar fresh para evitar conflitos)
echo ">>> Instalando dependências..."
pip install -q --upgrade pip huggingface_hub
pip install -q transformers==4.35.0 datasets accelerate==0.25.0

# Criar script Python de fine-tuning (simples, sem LoRA)
cat > /workspace/finetune.py << 'PYTHON_SCRIPT'
import json
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from datasets import Dataset
import os

print("=== Fine-Tuning DistilGPT-2 ===")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# Modelo pequeno: DistilGPT-2 (82M params)
MODEL_NAME = "distilgpt2"

print(f"\\n>>> Carregando modelo {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
if torch.cuda.is_available():
    model = model.cuda()

print(f"Parâmetros do modelo: {model.num_parameters():,}")

# Carregar dataset
print("\\n>>> Carregando dataset...")
with open("/workspace/input/train.json", "r") as f:
    data = json.load(f)

dataset = Dataset.from_list(data)
print(f"Exemplos de treino: {len(dataset)}")

# Tokenizar
def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=128,
        padding="max_length",
    )

print("\\n>>> Tokenizando dataset...")
tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

# Configurar treinamento (rápido para teste)
print("\\n>>> Configurando treinamento...")
training_args = TrainingArguments(
    output_dir="/workspace/output",
    num_train_epochs=2,
    per_device_train_batch_size=4,
    learning_rate=5e-5,
    warmup_steps=5,
    logging_steps=2,
    save_steps=100,
    save_total_limit=1,
    report_to="none",
    no_cuda=not torch.cuda.is_available(),
)

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
)

# Treinar
print("\\n>>> Iniciando treinamento...")
trainer.train()

# Salvar modelo
print("\\n>>> Salvando modelo treinado...")
trainer.save_model("/workspace/output/final")
tokenizer.save_pretrained("/workspace/output/final")

# Teste rápido de geração
print("\\n>>> Testando modelo treinado...")
model.eval()
test_prompt = "### Human: O que é o Dumont Cloud?\\n### Assistant:"
inputs = tokenizer(test_prompt, return_tensors="pt")
if torch.cuda.is_available():
    inputs = {k: v.cuda() for k, v in inputs.items()}

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=50,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(f"\\nPrompt: {test_prompt}")
print(f"Resposta gerada: {generated[len(test_prompt):]}")

print("\\n=== Fine-Tuning Concluído! ===")
PYTHON_SCRIPT

# Executar fine-tuning
echo ""
echo ">>> Executando fine-tuning..."
python /workspace/finetune.py

echo ""
echo "=== Job Finalizado ==="
echo "Modelo salvo em /workspace/output/final"
ls -la /workspace/output/final/
'''


def run_finetune_test():
    """Executa o teste de fine-tuning."""
    logger.info("=" * 60)
    logger.info("  TESTE REAL: Fine-Tuning com Jobs Module")
    logger.info("=" * 60)

    # 1. Criar dataset temporário
    logger.info("\n>>> Criando dataset de treino...")
    dataset_path = "/tmp/dumont_train.json"
    with open(dataset_path, "w") as f:
        json.dump(TRAINING_DATA, f, ensure_ascii=False, indent=2)
    logger.info(f"Dataset criado: {dataset_path} ({len(TRAINING_DATA)} exemplos)")

    # 2. Criar serviço VAST
    logger.info("\n>>> Conectando ao VAST.ai...")
    api_key = get_vast_api_key()
    vast_service = VastService(api_key)

    # 3. Criar executor (usa MachineProvisionerService internamente)
    executor = JobExecutor(
        vast_service,
        execution_timeout=1800,  # 30 min max
    )

    # 4. Configurar job
    finetune_script = create_finetune_script()

    job_config = {
        "job_id": "finetune_test_001",
        "docker_image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        "command": finetune_script,
        "gpu_name": "RTX 4090",  # GPU confiável com 24GB VRAM
        "max_price": 0.60,  # Max $0.60/hr
        "disk_gb": 30,
        "timeout_seconds": 1800,
        "env_vars": {},
    }

    # Callback para logs
    def on_log(level: str, message: str):
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[JOB] {message}")

    # 5. Precisamos copiar o dataset para a instância
    # Vamos incluir o dataset no script
    dataset_json = json.dumps(TRAINING_DATA, ensure_ascii=False)

    # Modificar o script para criar o dataset
    setup_script = f'''#!/bin/bash
set -e

# Criar diretório de input
mkdir -p /workspace/input /workspace/output

# Criar dataset
cat > /workspace/input/train.json << 'DATASET_EOF'
{dataset_json}
DATASET_EOF

echo "Dataset criado com $(cat /workspace/input/train.json | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))') exemplos"

{finetune_script}
'''

    job_config["command"] = setup_script

    # 6. Executar
    logger.info("\n>>> Buscando GPU disponível e executando fine-tuning...")
    logger.info("(Isso pode levar alguns minutos...)")

    start_time = time.time()
    result = executor.execute(job_config, on_log=on_log)
    elapsed = time.time() - start_time

    # 7. Resultado
    logger.info("\n" + "=" * 60)
    logger.info("  RESULTADO DO FINE-TUNING")
    logger.info("=" * 60)
    logger.info(f"Sucesso: {result.success}")
    logger.info(f"Exit code: {result.exit_code}")
    logger.info(f"Duração: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    logger.info(f"GPU usada: {result.gpu_name}")
    logger.info(f"Custo: ${result.cost_usd:.4f}")

    if result.error:
        logger.error(f"Erro: {result.error}")

    if result.output:
        logger.info("\n--- OUTPUT (últimas 50 linhas) ---")
        output_lines = result.output.strip().split('\n')
        for line in output_lines[-50:]:
            print(line)

    return result


if __name__ == "__main__":
    try:
        result = run_finetune_test()
        sys.exit(0 if result.success else 1)
    except KeyboardInterrupt:
        logger.warning("\nInterrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Erro: {e}")
        sys.exit(1)
