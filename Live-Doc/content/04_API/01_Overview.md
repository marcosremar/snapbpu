# API Reference

## Visao Geral

A API do Dumont Cloud permite integrar nossas funcionalidades em suas aplicacoes. Todas as chamadas usam REST com JSON.

---

## Base URL

```
Producao: https://dumontcloud.com/api/v1
Sandbox:  https://sandbox.dumontcloud.com/api/v1
```

---

## Autenticacao

### API Key
Todas as requisicoes precisam de uma API Key no header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://dumontcloud.com/api/v1/instances
```

### Obter API Key
1. Va em **Settings** > **API Keys**
2. Clique em **"Gerar Nova Chave"**
3. Copie e guarde em local seguro
4. A chave so e mostrada uma vez!

---

## Rate Limits

| Plano | Requisicoes/min | Requisicoes/dia |
|-------|-----------------|-----------------|
| Free | 60 | 1.000 |
| Pro | 300 | 10.000 |
| Enterprise | 1.000 | Ilimitado |

### Headers de Rate Limit
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200
```

---

## Formato de Resposta

### Sucesso
```json
{
  "success": true,
  "data": { ... }
}
```

### Erro
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Saldo insuficiente para esta operacao"
  }
}
```

---

## Endpoints Principais

### Instances (Maquinas)

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/instances` | Listar maquinas |
| POST | `/instances` | Criar maquina |
| GET | `/instances/{id}` | Detalhes da maquina |
| DELETE | `/instances/{id}` | Deletar maquina |
| POST | `/instances/{id}/start` | Iniciar maquina |
| POST | `/instances/{id}/stop` | Parar maquina |

### Billing

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/balance` | Saldo atual |
| GET | `/billing/history` | Historico |
| POST | `/billing/add-credits` | Adicionar creditos |

### Spot Market

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/offers` | Listar ofertas |
| GET | `/offers/{gpu}` | Ofertas por GPU |

### Failover Orchestrator

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/failover/execute` | Executar failover |
| GET | `/failover/readiness/{machine_id}` | Verificar prontidao |
| GET | `/failover/status/{machine_id}` | Status detalhado |
| POST | `/failover/test/{machine_id}` | Testar failover (dry-run) |
| GET | `/failover/strategies` | Listar estrategias |

### Failover Settings

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/failover/settings/global` | Config global |
| PUT | `/failover/settings/global` | Atualizar config global |
| GET | `/failover/settings/machines` | Listar configs por maquina |
| GET | `/failover/settings/machines/{id}` | Config de uma maquina |
| PUT | `/failover/settings/machines/{id}` | Atualizar config de maquina |

### GPU Warm Pool

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/warmpool/status/{machine_id}` | Status do warm pool |
| GET | `/warmpool/hosts` | Listar hosts multi-GPU |
| POST | `/warmpool/provision` | Provisionar warm pool |
| POST | `/warmpool/enable/{machine_id}` | Habilitar warm pool |
| POST | `/warmpool/disable/{machine_id}` | Desabilitar warm pool |

### Standby (CPU)

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/standby/status` | Status do CPU standby |
| POST | `/standby/configure` | Configurar standby |
| GET | `/standby/associations` | Listar associacoes GPU-CPU |
| GET | `/standby/pricing` | Estimar custos |

### Agent Status

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/agent/status` | Heartbeat do agente |
| GET | `/agent/instances` | Listar instancias com agente |
| POST | `/agent/instances/{id}/keep-alive` | Adiar hibernacao |

### Hibernation

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/hibernation/stats` | Estatisticas de economia |

### Machine History (Novo)

Sistema de rastreamento de confiabilidade de maquinas GPU.

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/machines/history/blacklist` | Listar maquinas bloqueadas |
| POST | `/machines/history/blacklist` | Adicionar ao blacklist |
| GET | `/machines/history/blacklist/check/{provider}/{machine_id}` | Verificar se bloqueada |
| DELETE | `/machines/history/blacklist/{provider}/{machine_id}` | Remover do blacklist |
| GET | `/machines/history/summary` | Resumo do historico |

#### Ofertas com Machine History

O endpoint `/instances/offers` agora retorna campos de confiabilidade:

```json
{
  "id": 29102584,
  "gpu_name": "RTX 4090",
  "dph_total": 0.25,
  "machine_id": "12345",
  "is_blacklisted": false,
  "success_rate": 0.85,
  "total_attempts": 20,
  "reliability_status": "good"
}
```

| Parametro | Descricao |
|-----------|-----------|
| `include_blacklisted=true` | Mostra maquinas blacklisted (ocultas por padrao) |

---

## Exemplos

### Listar Maquinas
```bash
curl -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  https://dumontcloud.com/api/v1/instances
```

Resposta:
```json
{
  "success": true,
  "data": [
    {
      "id": "inst_abc123",
      "gpu": "RTX 4090",
      "status": "running",
      "ip": "192.168.1.100",
      "ssh_port": 22,
      "cost_per_hour": 0.40,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Criar Maquina
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "gpu": "RTX 4090",
    "image": "pytorch:2.0-cuda12",
    "disk_size": 100
  }' \
  https://dumontcloud.com/api/v1/instances
```

### Parar Maquina
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  https://dumontcloud.com/api/v1/instances/inst_abc123/stop
```

---

## SDKs

### Python
```bash
pip install dumont-cloud
```

```python
from dumont import DumontClient

client = DumontClient(api_key="YOUR_API_KEY")

# Listar maquinas
machines = client.instances.list()

# Criar maquina
new_machine = client.instances.create(
    gpu="RTX 4090",
    image="pytorch:2.0-cuda12"
)

# Parar maquina
client.instances.stop(new_machine.id)
```

### JavaScript/Node.js
```bash
npm install dumont-cloud
```

```javascript
const Dumont = require('dumont-cloud');

const client = new Dumont({ apiKey: 'YOUR_API_KEY' });

// Listar maquinas
const machines = await client.instances.list();

// Criar maquina
const newMachine = await client.instances.create({
  gpu: 'RTX 4090',
  image: 'pytorch:2.0-cuda12'
});
```

---

## Webhooks

Receba notificacoes em tempo real sobre eventos:

### Configurar Webhook
1. Va em **Settings** > **Webhooks**
2. Adicione URL do seu endpoint
3. Selecione eventos de interesse
4. Salve

### Eventos Disponiveis
- `instance.created`
- `instance.started`
- `instance.stopped`
- `instance.deleted`
- `instance.interrupted`
- `instance.hibernated`
- `failover.started`
- `failover.warm_pool_success`
- `failover.cpu_standby_success`
- `failover.completed`
- `failover.failed`
- `warmpool.provisioned`
- `warmpool.degraded`
- `standby.sync_started`
- `standby.sync_completed`
- `balance.low`
- `agent.heartbeat_lost`

### Payload Exemplo
```json
{
  "event": "instance.interrupted",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "instance_id": "inst_abc123",
    "gpu": "RTX 4090",
    "reason": "spot_preemption"
  }
}
```
