# Cost Optimizer - Otimização Automática de Custos GPU

Daemon que monitora continuamente todas as instâncias GPU e realiza otimizações automáticas para reduzir custos.

## Visão Geral

O Cost Optimizer é um serviço que roda 24/7 monitorando:
- **Vast.ai** - Marketplace de GPUs
- **TensorDock** - Bare metal GPUs
- **Google Cloud Platform** - Enterprise GPUs

### Ações Automáticas

| Condição | Ação | Threshold Padrão |
|----------|------|------------------|
| GPU < 10% por 30min | **Pause** | Configurável |
| Instância idle > 24h | **Delete** | Configurável |

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    COST OPTIMIZER DAEMON                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Vast.ai  │    │TensorDock│    │   GCP    │              │
│  │ Provider │    │ Provider │    │ Provider │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                      │
│       └───────────────┼───────────────┘                      │
│                       │                                      │
│              ┌────────▼────────┐                            │
│              │  GPU Metrics    │                            │
│              │  Collector      │                            │
│              └────────┬────────┘                            │
│                       │                                      │
│              ┌────────▼────────┐                            │
│              │  Decision       │                            │
│              │  Engine         │                            │
│              └────────┬────────┘                            │
│                       │                                      │
│       ┌───────────────┼───────────────┐                      │
│       ▼               ▼               ▼                      │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐              │
│  │  PAUSE  │    │  DELETE  │    │  NOTIFY  │              │
│  └─────────┘    └──────────┘    └──────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Configuração

### Variáveis de Ambiente

```bash
# Thresholds
PAUSE_THRESHOLD_GPU=10        # Pausar se GPU < 10%
DELETE_THRESHOLD_HOURS=24     # Deletar se idle > 24h
CHECK_INTERVAL=60             # Checar a cada 60 segundos

# Providers
VAST_API_KEY=your_vast_key
TENSORDOCK_API_KEY=your_td_key
TENSORDOCK_API_TOKEN=your_td_token
GCP_PROJECT_ID=your_project_id
GCP_ZONE=us-central1-a

# Notificações (opcional)
WEBHOOK_URL=https://hooks.slack.com/...
```

### Adicionar ao .env

```bash
# Cost Optimizer
PAUSE_THRESHOLD_GPU=10
DELETE_THRESHOLD_HOURS=24
CHECK_INTERVAL=60
```

## Uso

### Rodar Manualmente

```bash
cd ~/dumontcloud
./bin/start-cost-optimizer.sh
```

### Instalar como Serviço (systemd)

```bash
# Copiar arquivo de serviço
sudo cp docker/cost-optimizer.service /etc/systemd/system/

# Habilitar e iniciar
sudo systemctl enable cost-optimizer
sudo systemctl start cost-optimizer

# Verificar status
sudo systemctl status cost-optimizer

# Ver logs
journalctl -u cost-optimizer -f
```

### Uso Programático

```python
from services.cost_optimizer import (
    CostOptimizer, 
    OptimizerConfig,
    VastAiProvider,
    TensorDockProvider,
    GcpProvider,
    ProviderType
)
import asyncio

# Configurar
config = OptimizerConfig(
    pause_threshold_gpu=10.0,      # Pausar se GPU < 10%
    delete_threshold_hours=24,      # Deletar se idle > 24h
    check_interval_seconds=60,
    protected_instances=["important-vm-1"]  # Nunca deletar
)

optimizer = CostOptimizer(config)

# Adicionar providers
optimizer.add_provider(
    ProviderType.VAST_AI,
    VastAiProvider("your-api-key")
)

optimizer.add_provider(
    ProviderType.TENSOR_DOCK,
    TensorDockProvider("api-key", "api-token")
)

# Rodar uma vez (para testes)
asyncio.run(optimizer.run_once())

# Ou rodar continuamente
asyncio.run(optimizer.run())
```

## Lógica de Decisão

### Quando Pausar

Uma instância é pausada quando:
1. Está **RUNNING**
2. **NÃO** está na lista de proteção
3. GPU utilization < threshold por **todos** os samples na janela de tempo
4. Tem pelo menos 5 amostras de métricas

### Quando Deletar

Uma instância é deletada quando:
1. **NÃO** está na lista de proteção
2. Idade > 1 hora (proteção contra deletar acidentalmente)
3. Idle por mais de N horas (configurável)

### Proteções

```python
config = OptimizerConfig(
    min_instance_age_hours=1.0,        # Não deletar instâncias novas
    protected_instances=[               # IDs que nunca serão tocados
        "prod-server-1",
        "critical-training-job"
    ]
)
```

## Métricas Coletadas

Via SSH + `nvidia-smi`:

| Métrica | Descrição |
|---------|-----------|
| `gpu_utilization` | % de uso da GPU (0-100) |
| `memory_used` | VRAM usada (GB) |
| `memory_total` | VRAM total (GB) |
| `temperature` | Temperatura (°C) |

## Logs

```
2024-12-20 15:30:00 - cost_optimizer - INFO - Cost Optimizer started
2024-12-20 15:30:00 - cost_optimizer - INFO - Config: pause_threshold=10.0%, delete_after=24h
2024-12-20 15:30:01 - cost_optimizer - INFO - Added provider: vast.ai
2024-12-20 15:30:02 - cost_optimizer - INFO - Running optimization cycle...
2024-12-20 15:30:05 - cost_optimizer - INFO - Found 3 total instances
2024-12-20 15:30:10 - cost_optimizer - DEBUG - vast.ai/123456: GPU=2.1%, Mem=45.2%
2024-12-20 15:30:11 - cost_optimizer - INFO - [CostOptimizer] PAUSE: vast.ai/123456 (RTX 4090) - GPU avg=3.2% (threshold=10.0%)
2024-12-20 15:30:12 - cost_optimizer - INFO - Successfully paused 123456
2024-12-20 15:30:15 - cost_optimizer - INFO - Cycle complete: 2 running, 1 paused/stopped
```

## Economia Estimada

| Cenário | Sem Optimizer | Com Optimizer | Economia |
|---------|---------------|---------------|----------|
| 1 GPU idle 12h/dia | $720/mês | $360/mês | 50% |
| 5 GPUs esquecidas | $3,600/mês | $0 | 100% |
| Workloads batch | $500/mês | $200/mês | 60% |

## Integração com DumontCloud

O Cost Optimizer integra-se automaticamente com:

1. **Deploy Wizard** - Registra novas instâncias automaticamente
2. **GPU Checkpoint** - Usa checkpoint antes de pausar (se disponível)
3. **Billing Dashboard** - Mostra economia realizada

## Troubleshooting

### Instância não está sendo monitorada

1. Verificar se o provider está configurado:
```bash
grep -E "(VAST|TENSOR|GCP)" .env
```

2. Verificar conectividade SSH:
```bash
ssh -o ConnectTimeout=5 user@<IP> nvidia-smi
```

### Falha ao pausar/deletar

1. Verificar logs:
```bash
journalctl -u cost-optimizer --since "1 hour ago"
```

2. Verificar API keys:
```bash
curl -H "Authorization: Bearer $VAST_API_KEY" \
  https://console.vast.ai/api/v0/instances
```

## Referências

- [Vast.ai API Docs](https://vast.ai/docs)
- [TensorDock API](https://marketplace.tensordock.com/api)
- [GCloud Compute](https://cloud.google.com/compute/docs)
