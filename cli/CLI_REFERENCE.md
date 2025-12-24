# Dumont Cloud CLI - Referência Completa

> **Atualizado em:** 2024-12-23
> **Versão:** 3.0.0

Este documento lista TODAS as funcionalidades do CLI. Atualize-o sempre que adicionar novos comandos.

---

## Índice

1. [Autenticação](#autenticação)
2. [Instâncias GPU](#instâncias-gpu)
3. [Jobs (Execute and Destroy)](#jobs-execute-and-destroy)
4. [Fine-tuning](#fine-tuning)
5. [Serverless (3 modos)](#serverless-3-modos)
6. [Wizard Deploy](#wizard-deploy)
7. [Spot Instances](#spot-instances)
8. [Standby/Failover](#standbyfailover)
9. [Warm Pool](#warm-pool)
10. [Snapshots](#snapshots)
11. [Métricas e Savings](#métricas-e-savings)
12. [History e Blacklist](#history-e-blacklist)
13. [Modelos LLM](#modelos-llm)
14. [Configurações](#configurações)

---

## Autenticação

```bash
# Login
dumont auth login <email> <password>

# Ver usuário atual
dumont auth me

# Logout
dumont auth logout

# Registrar novo usuário
dumont auth register
```

---

## Instâncias GPU

### Listar instâncias
```bash
dumont instance list
dumont instance list status=running
dumont instance list status=paused
```

### Gerenciar instância
```bash
dumont instance get <instance_id>
dumont instance pause <instance_id>
dumont instance resume <instance_id>
dumont instance delete <instance_id>
```

### Buscar ofertas
```bash
dumont instance offers
```

---

## Jobs (Execute and Destroy)

Jobs provisionam GPU, executam a tarefa e DESTROEM a GPU automaticamente.

### Criar job
```bash
# On-demand (estável, mais caro)
dumont job create <name> --command="..." --use-spot=false

# Spot (60-70% mais barato, pode ser interrompido)
dumont job create <name> --command="..." --use-spot=true

# Com opções completas
dumont job create train \
  --command="python train.py" \
  --gpu="RTX 4090" \
  --use-spot=false \
  --timeout=480 \
  --disk=100
```

### Opções do job create
| Opção | Descrição | Default |
|-------|-----------|---------|
| `--command="..."` | Comando a executar | (obrigatório) |
| `--gpu="RTX 4090"` | Tipo de GPU | RTX 4090 |
| `--use-spot=true/false` | Usar spot instance | true |
| `--num-gpus=1` | Número de GPUs | 1 |
| `--disk=50` | Disco em GB | 50 |
| `--timeout=480` | Timeout em minutos | 480 (8h) |
| `--image="..."` | Imagem Docker | - |
| `--setup="..."` | Script de setup | - |
| `--pip="pkg1,pkg2"` | Pacotes pip | - |
| `--hf-repo="user/repo"` | Repo HuggingFace | - |
| `--git-url="..."` | Repo Git | - |

### Gerenciar jobs
```bash
dumont job list
dumont job list --status=running
dumont job status <job_id>
dumont job logs <job_id>
dumont job cancel <job_id>
dumont job wait <job_id>
```

---

## Fine-tuning

Fine-tune LLMs usando LoRA/QLoRA com Unsloth.

### Listar modelos suportados
```bash
dumont finetune models
```

**Modelos disponíveis:**
- `unsloth/llama-3-8b-bnb-4bit` - Llama 3 8B
- `unsloth/llama-3-70b-bnb-4bit` - Llama 3 70B
- `unsloth/mistral-7b-bnb-4bit` - Mistral 7B
- `unsloth/gemma-7b-bnb-4bit` - Gemma 7B
- `unsloth/Qwen2-7B-bnb-4bit` - Qwen 2 7B
- `unsloth/Phi-3-mini-4k-instruct-bnb-4bit` - Phi-3 Mini

### Upload dataset
```bash
dumont finetune upload data/train.jsonl
```

### Criar job de fine-tuning
```bash
dumont finetune create my-model \
  --model="unsloth/llama-3-8b-bnb-4bit" \
  --dataset="/path/to/dataset" \
  --format=alpaca \
  --epochs=3 \
  --lr=2e-4 \
  --batch-size=4
```

### Gerenciar fine-tuning
```bash
dumont finetune list
dumont finetune status <job_id>
dumont finetune logs <job_id>
dumont finetune cancel <job_id>
dumont finetune refresh <job_id>
```

---

## Serverless (3 modos)

Auto pause/resume de GPUs baseado em idle detection.

### 3 Modos Disponíveis

| Modo | Recovery | Economia | Descrição |
|------|----------|----------|-----------|
| `fast` | <1s | ~80% | CPU Standby com sync contínuo |
| `economic` | ~7s | ~82% | VAST.ai pause/resume nativo |
| `spot` | ~30s | ~90% | Spot instances 60-70% mais baratas |

### Habilitar serverless
```bash
# Modo fast (recovery <1s)
dumont serverless enable <instance_id> mode=fast idle_timeout_seconds=30

# Modo economic (recovery ~7s)
dumont serverless enable <instance_id> mode=economic idle_timeout_seconds=30

# Modo spot (60-70% mais barato, recovery ~30s)
dumont serverless enable <instance_id> mode=spot idle_timeout_seconds=60
```

### Gerenciar serverless
```bash
dumont serverless list
dumont serverless status <instance_id>
dumont serverless disable <instance_id>
dumont serverless wake <instance_id>
dumont serverless pricing
```

---

## Wizard Deploy

Deploy inteligente com multi-start (cria várias máquinas, primeira que funcionar vence).

### Deploy básico
```bash
dumont wizard deploy
dumont wizard deploy "RTX 4090"
```

### Deploy com opções
```bash
# On-demand (estável)
dumont wizard deploy gpu="RTX 4090" type=on-demand price=1.5

# Spot (60-70% mais barato)
dumont wizard deploy gpu="RTX 4090" type=spot price=0.5

# Com região e velocidade
dumont wizard deploy gpu="RTX 4090" region=EU speed=fast
```

### Opções
| Opção | Valores | Default |
|-------|---------|---------|
| `gpu=` | RTX 4090, RTX 3090, A100, etc | Any |
| `type=` | on-demand, spot | on-demand |
| `price=` | Max $/hr | 2.0 |
| `speed=` | slow, medium, fast, ultra | fast |
| `region=` | global, US, EU, ASIA | global |

---

## Spot Instances

GPUs 60-70% mais baratas com automatic failover.

### Ver preços spot
```bash
dumont spot pricing
dumont spot pricing --region=US --gpu=RTX4090
```

### Templates (salvar configuração para reuso)
```bash
dumont spot template list
dumont spot template create <instance_id>
dumont spot template create <instance_id> --region=US
```

### Deploy spot
```bash
dumont spot deploy --template=<template_id>
dumont spot deploy --template=<id> --max-price=0.5
```

### Gerenciar spot
```bash
dumont spot status <instance_id>
dumont spot failover <instance_id>
dumont spot stop <instance_id>
dumont spot instances
```

### Análises spot
```bash
dumont spot prediction <gpu_name>
dumont spot safe-windows <gpu_name>
dumont spot comparison
```

---

## Standby/Failover

CPU Standby para failover instantâneo.

```bash
# Provisionar CPU standby
dumont standby provision <gpu_instance_id>
dumont standby provision <gpu_instance_id> label="my-standby"

# Ver status
dumont standby status
dumont standby associations

# Testar failover
dumont standby failover <gpu_instance_id>

# Configurar
dumont standby configure
dumont standby pricing
```

---

## Warm Pool

Pool de GPUs pré-aquecidas para failover rápido.

```bash
# Habilitar warm pool
dumont warmpool enable <machine_id>
dumont warmpool disable <machine_id>

# Status e hosts
dumont warmpool status <machine_id>
dumont warmpool hosts

# Testar failover
dumont warmpool failover <machine_id>

# Provisionar e limpar
dumont warmpool provision
dumont warmpool cleanup <machine_id>
```

---

## Snapshots

Backup e restore de instâncias.

```bash
dumont snapshot list
dumont snapshot create
dumont snapshot restore <instance_id>
dumont snapshot delete <snapshot_id>
```

---

## Métricas e Savings

### Savings (economia)
```bash
dumont saving summary
dumont saving summary period=month
dumont saving history months=6
dumont saving breakdown period=week
dumont saving comparison <gpu_type>
```

### Métricas de mercado
```bash
dumont metrics gpus
dumont metrics efficiency
dumont metrics providers
dumont metrics market
dumont metrics spot
dumont metrics spot gpu_name="RTX 4090"
dumont metrics hibernation
dumont metrics types
```

### Comparações e previsões
```bash
dumont metrics compare "RTX 4090,RTX 3090"
dumont metrics predictions "RTX 4090"
```

---

## History e Blacklist

Histórico de tentativas e blacklist de máquinas problemáticas.

### History
```bash
dumont history summary
dumont history summary --provider=vast --hours=24
dumont history list --provider=vast --hours=72
dumont history stats <provider> <machine_id>
dumont history problematic --provider=vast
dumont history reliable --provider=vast
```

### Blacklist
```bash
dumont blacklist list
dumont blacklist list --include-expired
dumont blacklist add <provider> <machine_id> "<reason>" --hours=48
dumont blacklist remove <provider> <machine_id>
dumont blacklist check <provider> <machine_id>
```

---

## Modelos LLM

Instalar Ollama e modelos em instâncias.

```bash
dumont model install <instance_id> <model_id>
dumont model install 12345 llama3.2
dumont model install 12345 qwen2.5:0.5b
dumont model install 12345 mistral
```

### Modelos populares
- `llama3.2` - Llama 3.2
- `qwen2.5:0.5b` - Qwen 2.5 (leve)
- `mistral` - Mistral 7B
- `codellama` - CodeLlama
- `phi3` - Phi-3

---

## Configurações

```bash
# Ver configurações
dumont settings list

# Atualizar
dumont settings update

# Cloud storage
dumont settings cloud-storage

# Completar onboarding
dumont settings complete-onboarding
```

---

## Balance

```bash
dumont balance list
```

---

## Outros Comandos

### Health
```bash
dumont health list
```

### Menu (navegação)
```bash
dumont menu list
```

### Content
```bash
dumont content get <path>
```

### Chat/AI
```bash
dumont chat models
dumont ai-wizard analyze
dumont advisor recommend
```

### Hibernação
```bash
dumont hibernation stats
```

---

## Workflow Típico

### 1. Deploy simples
```bash
dumont wizard deploy "RTX 4090"
```

### 2. Deploy + Serverless
```bash
# Deploy
dumont wizard deploy "RTX 4090"

# Habilitar auto-pause após 60s idle
dumont serverless enable <instance_id> mode=economic idle_timeout_seconds=60
```

### 3. Job de treinamento
```bash
# Criar job on-demand (estável)
dumont job create training \
  --command="python train.py" \
  --gpu="RTX 4090" \
  --use-spot=false \
  --timeout=480

# Monitorar
dumont job wait <job_id>
```

### 4. Fine-tuning
```bash
# Upload dataset
dumont finetune upload data/train.jsonl

# Criar job
dumont finetune create my-llama \
  --model="unsloth/llama-3-8b-bnb-4bit" \
  --dataset="/path/to/dataset"

# Monitorar
dumont finetune logs <job_id> --tail=50
```

### 5. Spot com failover
```bash
# Criar template de instância existente
dumont spot template create 12345

# Deploy spot
dumont spot deploy --template=spot_tpl_xxx

# Ver status
dumont spot status <instance_id>
```

---

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `DUMONT_API_URL` | URL da API (default: http://localhost:8000) |
| `VAST_API_KEY` | API key do VAST.ai |
| `GCP_CREDENTIALS` | Credenciais GCP para CPU Standby |

---

## Arquivos de Configuração

| Arquivo | Descrição |
|---------|-----------|
| `~/.dumont_token` | Token de autenticação |
| `config.json` | Configurações do usuário |

---

## Como Atualizar Este Documento

1. Adicione novos comandos na seção apropriada
2. Atualize a data no topo
3. Atualize o arquivo de testes `tests/test_cli_reference.py`
4. Execute os testes para validar

```bash
cd cli && pytest tests/test_cli_reference.py -v
```
