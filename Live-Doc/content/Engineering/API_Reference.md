# 🔌 API Reference - Dumont Cloud

## Base URL
- **Produção**: `https://dumontcloud.com`
- **Local**: `http://localhost:8766`
- **Demo**: `http://localhost:8766/demo-app` (sem credenciais)

## 🎭 Demo Mode

Para testar a API **sem credenciais reais**, use o parâmetro `?demo=true` ou acesse `/demo-app`:

```bash
# Listar máquinas demo
curl http://localhost:8766/api/machines?demo=true

# Criar instância demo
curl -X POST http://localhost:8766/api/instances?demo=true \
  -H "Content-Type: application/json" \
  -d '{"gpu_type": "RTX 4090", "region": "US-East"}'
```

**Dados Demo**: RTX 4090, A100, RTX 3090 com status `running`/`hibernating`

---

## Autenticação

Todas as rotas (exceto `/demo-*`) requerem JWT token no header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📦 Endpoints Principais

### 1. Máquinas (GPUs)

#### **GET** `/api/machines`
Lista todas as instâncias do usuário.

**Response 200**:
```json
{
  "machines": [
    {
      "id": "28864630",
      "name": "ML Training Rig",
      "gpu_name": "RTX 4090",
      "status": "running",
      "cost_per_hour": 0.40,
      "region": "US-East"
    }
  ]
}
```

#### **POST** `/api/instances`
Cria uma nova instância GPU.

**Request Body**:
```json
{
  "gpu_type": "RTX 4090",
  "region": "US-East",
  "auto_hibernate": true
}
```

**Response 201**:
```json
{
  "instance_id": "28864630",
  "status": "creating",
  "estimated_ready": "2025-12-19T02:25:00Z"
}
```

#### **DELETE** `/api/instances/{instance_id}`
Encerra uma instância.

**Response 200**:
```json
{
  "message": "Instance 28864630 terminated",
  "final_cost": 12.50
}
```

---

### 2. Snapshots

#### **POST** `/api/snapshots`
Cria um snapshot da instância.

**Request Body**:
```json
{
  "instance_id": "28864630",
  "name": "Before Upgrade",
  "compression": "lz4"
}
```

**Response 202**:
```json
{
  "snapshot_id": "snap-abc123",
  "status": "compressing",
  "estimated_size": "45GB"
}
```

#### **GET** `/api/snapshots/{snapshot_id}`
Verifica o status de um snapshot.

**Response 200**:
```json
{
  "snapshot_id": "snap-abc123",
  "status": "completed",
  "size": "12GB",
  "compression_ratio": 3.75,
  "upload_speed": "1.2GB/s"
}
```

---

### 3. Hibernação

#### **POST** `/api/instances/{instance_id}/hibernate`
Força hibernação imediata.

**Response 200**:
```json
{
  "message": "Instance hibernated",
  "savings_per_hour": 0.38
}
```

#### **POST** `/api/instances/{instance_id}/wake`
Acorda instância hibernada.

**Response 200**:
```json
{
  "message": "Instance waking up",
  "estimated_ready": "2025-12-19T02:30:00Z"
}
```

---

### 4. Métricas & Economia

#### **GET** `/api/savings/dashboard`
Dashboard de economia em tempo real.

**Response 200**:
```json
{
  "total_saved_usd": 1247.50,
  "monthly_burn": 799.00,
  "aws_equivalent": 4590.00,
  "savings_percent": 82.6,
  "roi_percent": 1650
}
```

---

### 5. IA (GPU Advisor)

#### **POST** `/api/ai/recommend-gpu`
Recomenda GPU baseado no workload.

**Request Body**:
```json
{
  "task": "fine-tune llama2-7b",
  "dataset_size": "50GB",
  "budget_per_hour": 1.00
}
```

**Response 200**:
```json
{
  "recommended_gpu": "RTX 4090",
  "reasoning": "Best cost/performance for 7B models. 24GB VRAM sufficient.",
  "estimated_time": "12 hours",
  "total_cost": "$4.80"
}
```

---

### 5. Economia (Savings API)

#### **GET** `/api/savings/summary`
Dashboard overview de economia.

**Query Params**:
- `period`: day, week, month, year (default: month)

**Response 200**:
```json
{
  "period": "2025-12",
  "total_hours": 156.5,
  "total_cost_dumont": 68.86,
  "total_cost_aws": 641.65,
  "savings_vs_aws": 572.79,
  "savings_percentage": 89.3,
  "roi_percent": 1650,
  "auto_hibernate_savings": 32.50
}
```

#### **GET** `/api/savings/history`
Histórico de economia dos últimos meses.

**Query Params**:
- `months`: Número de meses (default: 6)

**Response 200**:
```json
{
  "history": [
    {"month": "2025-12", "savings_vs_aws": 572.79},
    {"month": "2025-11", "savings_vs_aws": 445.20}
  ]
}
```

#### **GET** `/api/savings/breakdown`
Breakdown detalhado por GPU.

**Response 200**:
```json
{
  "breakdown_by_gpu": [
    {
      "gpu_type": "RTX 4090",
      "hours": 120,
      "cost_dumont": 52.80,
      "cost_aws": 367.20,
      "savings": 314.40
    }
  ]
}
```

#### **GET** `/api/savings/comparison/{gpu_type}`
Comparação em tempo real para uma GPU específica.

**Response 200**:
```json
{
  "gpu_type": "RTX 4090",
  "dumont_hourly": 0.44,
  "aws_hourly": 3.06,
  "gcp_hourly": 2.74,
  "azure_hourly": 2.95,
  "savings_per_hour": 2.62,
  "savings_percent": 85.6
}
```

---

### 6. Métricas de Mercado

#### **GET** `/api/metrics/market`
Estado atual do mercado Spot.

**Response 200**:
```json
{
  "timestamp": "2025-12-19T03:30:00Z",
  "total_gpus_available": 450,
  "avg_price_change_24h": -2.3,
  "trending_gpus": ["RTX 4090", "A100"]
}
```

#### **GET** `/api/metrics/providers`
Ranking de provedores (reliability, preço).

**Response 200**:
```json
{
  "providers": [
    {
      "name": "Vast.ai",
      "reliability_score": 0.92,
      "avg_price": 0.40,
      "uptime_percent": 94.5
    }
  ]
}
```

#### **GET** `/api/metrics/predictions/{gpu_name}`
Predição de preços usando ML.

**Response 200**:
```json
{
  "gpu_name": "RTX 4090",
  "current_price": 0.40,
  "predictions": {
    "next_1h": {"price": 0.39, "confidence": 0.92},
    "next_6h": {"price": 0.38, "confidence": 0.78},
    "next_24h": {"price": 0.42, "confidence": 0.65}
  },
  "recommendation": "Wait 2-4 hours for best price",
  "model_accuracy": 0.87
}
```

#### **GET** `/api/metrics/hibernation/events`
Histórico de eventos de auto-hibernação.

**Query Params**:
- `days`: Últimos N dias (default: 7)

**Response 200**:
```json
{
  "events": [
    {
      "instance_id": "28864630",
      "timestamp": "2025-12-19T02:15:30Z",
      "reason": "Low GPU utilization (<5%)",
      "savings_per_hour": 0.38
    }
  ],
  "total_savings": 12.50
}
```

---

### 7. Agent Heartbeat

#### **POST** `/api/agent/status`
Instância envia heartbeat com métricas.

**Request Body**:
```json
{
  "instance_id": "28864630",
  "gpu_utilization": 87,
  "vram_used_gb": 18.4,
  "cost_accumulated": 2.40,
  "status": "running"
}
```

**Response 200**:
```json
{
  "success": true,
  "next_heartbeat_in_seconds": 60,
  "actions": []
}
```

#### **GET** `/api/agent/instances`
Lista todas as instâncias com status de heartbeat.

**Response 200**:
```json
{
  "instances": [
    {
      "instance_id": "28864630",
      "last_heartbeat": "2025-12-19T03:25:30Z",
      "health": "healthy",
      "gpu_utilization": 87
    }
  ]
}
```

---

### 8. WebSocket (Tempo Real)

### `/ws/instance/{instance_id}/metrics`

Conecte via WebSocket para receber métricas em tempo real:

```javascript
const ws = new WebSocket('wss://dumontcloud.com/ws/instance/28864630/metrics');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('GPU Usage:', data.gpu_utilization);
  console.log('Current Cost:', data.cost_accumulated);
};
```

**Payload de Exemplo**:
```json
{
  "timestamp": "2025-12-19T02:28:30Z",
  "gpu_utilization": 87,
  "vram_used_gb": 18.4,
  "cost_accumulated": 2.40
}
```

---

## 📊 Status Codes

| Code | Descrição |
|------|-----------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async operation) |
| 400 | Bad Request (validação falhou) |
| 401 | Unauthorized (token inválido) |
| 404 | Not Found |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

---

## 🧪 Testando com cURL

```bash
# Login
curl -X POST https://dumontcloud.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "senha123"}'

# Criar instância (use o token retornado)
curl -X POST https://dumontcloud.com/api/instances \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"gpu_type": "RTX 4090", "region": "US-East"}'
```

---

**Swagger UI Completo**: https://dumontcloud.com/docs  
**Última atualização**: 2025-12-19
