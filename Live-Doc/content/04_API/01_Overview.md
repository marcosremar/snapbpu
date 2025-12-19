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
- `failover.started`
- `failover.completed`
- `balance.low`

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
