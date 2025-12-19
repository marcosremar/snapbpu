# 🔌 Integration Guide - SDK, CLI, Webhooks

## Visão Geral

O Dumont Cloud oferece **3 formas de integração**:

1. **REST API** - HTTP direto
2. **Python SDK** - Biblioteca oficial
3. **CLI** - Linha de comando
4. **Webhooks** - Eventos em tempo real

---

## 🔑 Autenticação

### Obter API Key

```bash
# Dashboard
1. Login → Settings → API Keys
2. Clique em "Generate New Key"
3. Copie (só aparece uma vez!)
```

**Formato**: `dumont_sk_1234567890abcdef`

### Usar API Key

```bash
# Header HTTP
Authorization: Bearer dumont_sk_1234567890abcdef
```

---

## 🐍 Python SDK

### Instalação

```bash
pip install dumont-cloud
```

### Quick Start

```python
from dumont import Client

# Inicializar cliente
client = Client(api_key="dumont_sk_...")

# Criar instância
instance = client.instances.create(
    gpu_type="RTX 4090",
    region="US-East",
    auto_hibernate=True
)

print(f"Instance ID: {instance.id}")
print(f"Status: {instance.status}")
print(f"IP: {instance.ip}")
```

### Listar Instâncias

```python
# Todas as instâncias
instances = client.instances.list()

for inst in instances:
    print(f"{inst.name}: {inst.status}")

# Filtrar por status
running = client.instances.list(status="running")
```

### Criar Snapshot

```python
snapshot = client.snapshots.create(
    instance_id="28864630",
    name="Pre-upgrade backup",
    compression="lz4"
)

# Aguardar conclusão
snapshot.wait_until_complete(timeout=300)  # 5 min
print(f"Snapshot completo: {snapshot.size_gb}GB")
```

### Hibernar/Acordar

```python
# Hibernar
instance.hibernate()

# Acordar
instance.wake()

# Aguardar ready
instance.wait_until_ready(timeout=60)
```

### Verificar Economia

```python
# Dashboard de economia
savings = client.savings.get_dashboard()

print(f"Total economizado: ${savings.total_saved_usd}")
print(f"ROI: {savings.roi_percent}%")
print(f"AWS equivalente: ${savings.aws_equivalent}")
```

### Error Handling

```python
from dumont import DumontError, RateLimitError

try:
    instance = client.instances.create(gpu_type="RTX 4090")
except RateLimitError as e:
    print(f"Rate limit: tente em {e.retry_after}s")
except DumontError as e:
    print(f"Erro: {e.message}")
```

---

## 💻 CLI (Command Line Interface)

### Instalação

```bash
pip install dumont-cli
```

### Configuração

```bash
# Adicionar API key
dumont config set-key dumont_sk_...

# Verificar config
dumont config show
```

### Comandos Básicos

```bash
# Listar instâncias
dumont list

# Criar instância
dumont create --gpu RTX4090 --region US-East

# Ver detalhes
dumont show INSTANCE_ID

# Hibernar
dumont hibernate INSTANCE_ID

# Acordar
dumont wake INSTANCE_ID

# Deletar
dumont delete INSTANCE_ID
```

### Snapshots via CLI

```bash
# Criar snapshot
dumont snapshot create INSTANCE_ID --name "Backup"

# Listar snapshots
dumont snapshot list

# Restaurar
dumont snapshot restore SNAPSHOT_ID
```

### Output JSON

```bash
# Para parsing em scripts
dumont list --output json | jq '.instances[] | .name'
```

---

## 🌐 REST API

### Base URL

```
https://dumontcloud.com/api
```

### Endpoints Principais

#### 1. Criar Instância

```bash
POST /api/instances

curl -X POST https://dumontcloud.com/api/instances \
  -H "Authorization: Bearer dumont_sk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "gpu_type": "RTX 4090",
    "region": "US-East",
    "auto_hibernate": true
  }'
```

**Response**:
```json
{
  "id": "28864630",
  "status": "creating",
  "gpu_name": "RTX 4090",
  "ip": null,
  "estimated_ready": "2025-12-19T02:45:00Z"
}
```

#### 2. Listar Instâncias

```bash
GET /api/machines

curl https://dumontcloud.com/api/machines \
  -H "Authorization: Bearer dumont_sk_..."
```

#### 3. Hibernar

```bash
POST /api/instances/{id}/hibernate

curl -X POST https://dumontcloud.com/api/instances/28864630/hibernate \
  -H "Authorization: Bearer dumont_sk_..."
```

#### 4. Criar Snapshot

```bash
POST /api/snapshots

curl -X POST https://dumontcloud.com/api/snapshots \
  -H "Authorization: Bearer dumont_sk_..." \
  -d '{
    "instance_id": "28864630",
    "name": "Backup",
    "compression": "lz4"
  }'
```

---

## 🔔 Webhooks

### Eventos Disponíveis

| Evento | Quando Dispara |
|--------|----------------|
| `instance.created` | Nova instância criada |
| `instance.deleted` | Instância deletada |
| `instance.hibernated` | Auto-hibernação ativada |
| `instance.ready` | Instância pronta para uso |
| `failover.triggered` | Failover GPU → CPU |
| `snapshot.completed` | Snapshot finalizado |
| `billing.low_balance` | Créditos <$10 |

### Configurar Webhook

```bash
# Dashboard
Settings → Webhooks → Add New

# API
curl -X POST https://dumontcloud.com/api/webhooks \
  -H "Authorization: Bearer dumont_sk_..." \
  -d '{
    "url": "https://your-app.com/webhooks/dumont",
    "events": ["instance.created", "failover.triggered"],
    "secret": "your_webhook_secret"
  }'
```

### Payload de Exemplo

```json
{
  "event": "instance.created",
  "timestamp": "2025-12-19T02:45:30Z",
  "data": {
    "instance_id": "28864630",
    "gpu_type": "RTX 4090",
    "region": "US-East",
    "ip": "79.112.1.66"
  }
}
```

### Validar Signature

```python
import hmac
import hashlib

def validate_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

# Flask example
@app.route('/webhooks/dumont', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Dumont-Signature')
    payload = request.data.decode()
    
    if not validate_webhook(payload, signature, WEBHOOK_SECRET):
        return 'Invalid signature', 401
    
    event = request.json
    if event['event'] == 'failover.triggered':
        notify_ops_team(event['data'])
    
    return 'OK', 200
```

---

## 🚦 Rate Limiting

### Limites

| Tier | Requisições/min | Burst |
|------|-----------------|-------|
| **Starter** | 10 | 20 |
| **Pro** | 60 | 120 |
| **Enterprise** | 300 | 600 |

### Headers de Rate Limit

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1734567890
```

### Tratamento de 429 (Too Many Requests)

```python
import time

def create_instance_with_retry(client, **kwargs):
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            return client.instances.create(**kwargs)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(e.retry_after)
```

---

## 📚 SDKs em Outras Linguagens

### JavaScript/TypeScript

```bash
npm install @dumont/cloud
```

```typescript
import { DumontClient } from '@dumont/cloud';

const client = new DumontClient({ apiKey: 'dumont_sk_...' });

const instance = await client.instances.create({
  gpuType: 'RTX 4090',
  region: 'US-East',
});
```

### Go

```bash
go get github.com/dumont-cloud/go-sdk
```

```go
import "github.com/dumont-cloud/go-sdk"

client := dumont.NewClient("dumont_sk_...")

instance, err := client.Instances.Create(&dumont.CreateInstanceInput{
    GPUType: "RTX 4090",
    Region:  "US-East",
})
```

---

## 🧪 Ambiente de Testes

### Sandbox (Demo Mode)

Use `demo=true` para testar sem criar instâncias reais:

```bash
curl https://dumontcloud.com/api/machines?demo=true
```

Retorna dados fictícios (RTX 4090, A100, etc.)

---

## 📂 Exemplos de Integração

### CI/CD (GitHub Actions)

```yaml
name: Deploy ML Model

on: push

jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - name: Create GPU Instance
        run: |
          INSTANCE_ID=$(dumont create --gpu A100 --output json | jq -r '.id')
          echo "INSTANCE_ID=$INSTANCE_ID" >> $GITHUB_ENV
      
      - name: Train Model
        run: |
          ssh $INSTANCE_ID python train.py
      
      - name: Delete Instance
        run: dumont delete $INSTANCE_ID
```

### Slack Bot

```python
from slack_sdk import WebClient
from dumont import Client

# Comando: /create-gpu RTX4090
@slack.command("/create-gpu")
def create_gpu(ack, command):
    ack()
    
    gpu_type = command['text']
    instance = dumont_client.instances.create(gpu_type=gpu_type)
    
    slack_client.chat_postMessage(
        channel=command['channel_id'],
        text=f"GPU {gpu_type} criada! IP: {instance.ip}"
    )
```

---

**Última atualização**: 2025-12-19  
**Dúvidas**: dev@dumontcloud.com
