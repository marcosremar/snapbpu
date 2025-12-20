# GPU Checkpoint/Restore - Fast Cold Start

Esta documentação descreve como implementar cold start rápido de modelos de ML usando NVIDIA cuda-checkpoint, similar ao Modal.ai GPU Memory Snapshots.

## Visão Geral

O cuda-checkpoint permite salvar e restaurar o estado da GPU (VRAM) de um processo, possibilitando:
- **Cold start rápido**: Restaurar modelo em ~0.5s ao invés de 15-30s
- **Preemption**: Pausar workloads de baixa prioridade
- **Migration**: Mover workloads entre GPUs/nodes

## Benchmark Resultados (Testado em 20/12/2024)

### Ambiente de Teste
- **Provider**: TensorDock Bare Metal
- **GPU**: Tesla V100-SXM2-16GB
- **Driver**: NVIDIA 570.195.03
- **CUDA**: 12.8
- **Modelo**: Qwen3-0.6B (600M params)

### Resultados

| Método | Tempo | Speedup |
|--------|-------|---------|
| Cold Start tradicional (load + 1ª inferência) | 3.07s | - |
| CUDA Restore | 0.48s | 6.4x |
| Restore + 1ª inferência | 1.26s | 2.4x |

### Projeção para Modelos Maiores

| Modelo | Cold Start | Com Checkpoint | Speedup Estimado |
|--------|------------|----------------|------------------|
| Qwen3-0.6B | 3s | 1.3s | 2.4x |
| Llama 7B | ~20s | ~2s | ~10x |
| Llama 70B | ~120s | ~5s | ~24x |

## Requisitos

### Hardware/Infra
- NVIDIA GPU (qualquer arquitetura moderna)
- **NVIDIA Driver 570+** (obrigatório)
- Linux com kernel compatível
- **Bare metal ou container privilegiado** com:
  - `CAP_SYS_PTRACE`
  - `CAP_SYS_ADMIN` (para CRIU)
  - Seccomp desabilitado

### Provedores Compatíveis

| Provider | Tipo | Suporta? | Notas |
|----------|------|----------|-------|
| TensorDock | Bare Metal | ✅ Sim | Testado, funciona |
| HOSTKEY | Bare Metal | ✅ Sim | Acesso root completo |
| CoreWeave | Kubernetes | ⚠️ Negociável | Requer contrato enterprise |
| RunPod | Managed | ❌ Não | Sem containers privilegiados |
| Vast.ai | Marketplace | ❌ Não | Sem CAP_SYS_PTRACE |
| Lambda Labs | Managed | ❌ Não | Sem containers privilegiados |
| AWS/GCP | Cloud | ⚠️ Caro | Bare metal disponível mas $30+/hr |

## Setup

### 1. Instalar Driver NVIDIA 570+

```bash
# Ubuntu 22.04
sudo apt-get update
sudo apt-get install -y nvidia-driver-570
sudo reboot
```

### 2. Clonar cuda-checkpoint

```bash
git clone https://github.com/NVIDIA/cuda-checkpoint.git
cd cuda-checkpoint

# Binário já vem pré-compilado
ls bin/x86_64_Linux/cuda-checkpoint
```

### 3. (Opcional) Instalar CRIU para checkpoint completo

```bash
sudo apt-get install -y criu
```

## Uso Básico

### Verificar Estado

```bash
cuda-checkpoint --get-state --pid <PID>
# Retorna: "running" ou "checkpointed"
```

### Fazer Checkpoint (Pausar GPU)

```bash
sudo cuda-checkpoint --toggle --pid <PID>
# GPU memory é liberada, processo continua rodando mas sem GPU
```

### Fazer Restore (Resumir GPU)

```bash
sudo cuda-checkpoint --toggle --pid <PID>
# GPU memory é restaurada, processo continua de onde parou
```

## Integração com DumontCloud

### Estratégia de Cold Start

```
┌─────────────────────────────────────────────────────────────┐
│                    DUMONT CLOUD                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Request chegou                                              │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ Checkpoint  │ YES │   Restore   │     │  Processar  │   │
│  │  Existe?    │────▶│   (0.5s)    │────▶│   Request   │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│       │ NO                                                   │
│       ▼                                                      │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ Cold Start  │     │   Criar     │     │  Processar  │   │
│  │  (15-30s)   │────▶│ Checkpoint  │────▶│   Request   │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Opções de Start Mode para Usuário

```typescript
interface DeploymentConfig {
  model: string;

  // Opções de cold start
  startMode:
    | 'cold'           // Sempre carregar do disco (mais lento, mais barato)
    | 'warm'           // Manter modelo quente (mais rápido, mais caro)
    | 'checkpoint';    // Usar cuda-checkpoint (rápido, custo médio)

  // Configurações de checkpoint
  checkpoint?: {
    enabled: boolean;
    ttl: number;              // Tempo para manter checkpoint (segundos)
    storage: 'local' | 's3';  // Onde salvar checkpoint
  };
}
```

### Exemplo de API

```python
# Usuário define o modelo
deployment = dumont.deploy(
    model="Qwen/Qwen3-0.6B",
    start_mode="checkpoint",
    checkpoint={
        "enabled": True,
        "ttl": 3600,  # Manter checkpoint por 1 hora
    }
)

# Primeira request (cold start + cria checkpoint)
response = deployment.generate("Hello")  # ~3s

# Requests subsequentes (restore do checkpoint)
response = deployment.generate("World")  # ~1.3s
```

## Workflow Completo com CRIU

Para checkpoint completo (RAM + VRAM + filesystem):

```bash
# 1. Pausar CUDA
cuda-checkpoint --toggle --pid $PID

# 2. Checkpoint do processo com CRIU
mkdir -p /checkpoints/model-v1
criu dump --shell-job --images-dir /checkpoints/model-v1 --tree $PID

# 3. (Processo morreu, pode desligar a máquina)

# --- Depois, para restaurar ---

# 4. Restaurar processo com CRIU
criu restore --shell-job --restore-detached --images-dir /checkpoints/model-v1

# 5. Resumir CUDA
cuda-checkpoint --toggle --pid $NEW_PID
```

## Limitações Conhecidas

1. **Driver 570+ obrigatório**: Versões anteriores não suportam
2. **Bare metal necessário**: Containers managed não têm as capabilities necessárias
3. **Mesmo hardware**: Restore deve ser na mesma arquitetura de GPU
4. **Processo único**: cuda-checkpoint opera em um PID por vez

## Scripts de Referência

### Benchmark Script

```python
#!/usr/bin/env python3
"""benchmark_checkpoint.py - Benchmark cold start vs checkpoint restore"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import subprocess
import time
import os

CKPT = os.path.expanduser("~/cuda-checkpoint/bin/x86_64_Linux/cuda-checkpoint")

def benchmark():
    print("=" * 60)
    print("BENCHMARK: Cold Start vs Checkpoint/Restore")
    print("=" * 60)

    # Cold start
    torch.cuda.empty_cache()
    start = time.time()

    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen3-0.6B",
        torch_dtype=torch.float16,
        device_map="cuda"
    )

    inputs = tokenizer("Test", return_tensors="pt").to("cuda")
    model.generate(**inputs, max_new_tokens=10)

    cold_start = time.time() - start
    print(f"Cold start: {cold_start:.2f}s")

    # Checkpoint
    pid = os.getpid()
    subprocess.run(["sudo", CKPT, "--toggle", "--pid", str(pid)])
    time.sleep(1)

    # Restore + inference
    start = time.time()
    subprocess.run(["sudo", CKPT, "--toggle", "--pid", str(pid)])

    inputs = tokenizer("Test", return_tensors="pt").to("cuda")
    model.generate(**inputs, max_new_tokens=10)

    restore_time = time.time() - start

    print(f"Restore + inference: {restore_time:.2f}s")
    print(f"Speedup: {cold_start/restore_time:.1f}x")

if __name__ == "__main__":
    benchmark()
```

## Referências

- [NVIDIA cuda-checkpoint GitHub](https://github.com/NVIDIA/cuda-checkpoint)
- [CRIU - Checkpoint Restore in Userspace](https://criu.org/)
- [Modal GPU Memory Snapshots](https://modal.com/docs/guide/cuda-memory-snapshot)
- [NVIDIA Driver 570 Release Notes](https://docs.nvidia.com/datacenter/tesla/tesla-release-notes-570-xx/index.html)
