# 📊 Spot Market Intelligence - Guia Completo

## Visão Geral

O Dumont Cloud possui um **sistema de inteligência de mercado Spot** que analisa em tempo real preços, disponibilidade e confiabilidade de GPUs no mercado Vast.ai.

Esta é uma **feature diferenciadora** - AWS, GCP e Azure não oferecem análise preditiva do mercado Spot.

---

## 🎯 Por Que Usar?

### Problemas que Resolve
1. **Escolha de GPU**: Qual GPU tem melhor custo/benefício hoje?
2. **Timing**: Quando é o melhor momento para treinar meu modelo?
3. **Confiabilidade**: Qual GPU tem menor taxa de interrupção?
4. **Economia**: Quanto vou economizar vs AWS?

### Casos de Uso
- **Startups**: Maximizar economia sem sacrificar performance
- **Pesquisadores**: Encontrar janelas seguras para treinamento longo
- **Empresas**: Análise de ROI antes de scaling

---

## 📡 API Endpoints (10 total)

### 1. Monitor de Preços em Tempo Real

**`GET /api/spot/monitor`**

Monitora preços de todas as GPUs no mercado Spot.

**Request**:
```bash
curl https://dumontcloud.com/api/spot/monitor \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "timestamp": "2025-12-19T03:25:00Z",
  "total_gpus_tracked": 50,
  "price_trends": [
    {
      "gpu_name": "RTX 4090",
      "current_price": 0.40,
      "avg_price_24h": 0.42,
      "min_price_24h": 0.38,
      "max_price_24h": 0.46,
      "trend": "decreasing",
      "change_percent": -4.8
    }
  ]
}
```

**Quando usar**: Dashboards em tempo real, alertas de preço

---

### 2. Melhores GPUs para LLM

**`GET /api/spot/llm-gpus`**

Recomenda GPUs ideais baseado no tamanho do modelo LLM.

**Request**:
```bash
curl "https://dumontcloud.com/api/spot/llm-gpus?model_size=7B" \
  -H "Authorization: Bearer TOKEN"
```

**Query Params**:
- `model_size`: 7B, 13B, 30B, 70B, 180B
- `min_vram`: Mínimo de VRAM (GB)
- `max_price`: Orçamento máximo ($/hora)

**Response**:
```json
{
  "model_size": "7B",
  "recommendations": [
    {
      "gpu_name": "RTX 4090",
      "vram_gb": 24,
      "price_per_hour": 0.40,
      "fit_score": 0.95,
      "reasoning": "VRAM suficiente + melhor custo/benefício",
      "estimated_training_time_hours": 12
    },
    {
      "gpu_name": "RTX 3090",
      "vram_gb": 24,
      "price_per_hour": 0.30,
      "fit_score": 0.85,
      "reasoning": "Mais barato, mas 20% mais lento"
    }
  ]
}
```

**Quando usar**: Fine-tuning wizard, onboarding

---

### 3. Estratégia de Fleet

**`GET /api/spot/fleet-strategy`**

Sugere composição ideal de fleet para máxima economia.

**Request**:
```bash
curl "https://dumontcloud.com/api/spot/fleet-strategy?workload=training&budget=100" \
  -H "Authorization: Bearer TOKEN"
```

**Query Params**:
- `workload`: training, inference, rendering
- `budget`: Orçamento mensal ($)
- `reliability`: low, medium, high

**Response**:
```json
{
  "strategy": "hybrid",
  "total_gpus": 8,
  "monthly_cost": 96.00,
  "composition": [
    {
      "gpu_type": "RTX 4090",
      "quantity": 5,
      "role": "primary",
      "cost_per_month": 72.00
    },
    {
      "gpu_type": "A100",
      "quantity": 1,
      "role": "high_priority",
      "cost_per_month": 36.00
    }
  ],
  "savings_vs_aws": 804.00,
  "roi_percent": 837
}
```

**Quando usar**: Planejamento de infra, scaling

---

### 4. Predição de Preços

**`GET /api/spot/prediction/{gpu_name}`**

Prevê preços futuros baseado em ML.

**Request**:
```bash
curl https://dumontcloud.com/api/spot/prediction/RTX%204090 \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "gpu_name": "RTX 4090",
  "current_price": 0.40,
  "predictions": {
    "next_1h": {
      "price": 0.39,
      "confidence": 0.92
    },
    "next_6h": {
      "price": 0.38,
      "confidence": 0.78
    },
    "next_24h": {
      "price": 0.42,
      "confidence": 0.65
    }
  },
  "recommendation": "Wait 2-4 hours for best price",
  "model_accuracy": 0.87
}
```

**Quando usar**: Scheduling de treinamento, otimização de custo

---

### 5. Disponibilidade Instantânea

**`GET /api/spot/availability`**

Verifica disponibilidade em tempo real de todas as regiões.

**Request**:
```bash
curl "https://dumontcloud.com/api/spot/availability?gpu=RTX%204090" \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "gpu_name": "RTX 4090",
  "total_available": 127,
  "regions": [
    {
      "region": "US-East",
      "available_count": 45,
      "avg_price": 0.40,
      "latency_ms": 12
    },
    {
      "region": "EU-West",
      "available_count": 38,
      "avg_price": 0.42,
      "latency_ms": 8
    }
  ],
  "best_region": "EU-West"
}
```

**Quando usar**: Criar instância (escolher região ideal)

---

### 6. Custo de Treinamento

**`GET /api/spot/training-cost`**

Calcula custo estimado de treinar um modelo.

**Request**:
```bash
curl "https://dumontcloud.com/api/spot/training-cost?model=llama2-7b&dataset_size=50GB" \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "model": "llama2-7b",
  "dataset_size_gb": 50,
  "gpu_recommendations": [
    {
      "gpu_name": "RTX 4090",
      "estimated_hours": 12,
      "cost_dumont": 4.80,
      "cost_aws": 36.72,
      "savings": 31.92,
      "savings_percent": 86.9
    }
  ]
}
```

**Quando usar**: Orçamento de projetos, comparação de providers

---

### 7. Calculadora de Economia

**`GET /api/spot/savings`**

Calcula economia detalhada vs AWS/GCP/Azure.

**Request**:
```bash
curl "https://dumontcloud.com/api/spot/savings?gpu=RTX%204090&hours=100" \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "gpu_name": "RTX 4090",
  "hours": 100,
  "cost_dumont": 40.00,
  "cost_aws": 306.00,
  "cost_gcp": 274.00,
  "cost_azure": 295.00,
  "savings_vs_aws": 266.00,
  "savings_percent": 86.9,
  "roi_annual": 31920.00
}
```

**Quando usar**: Apresentações de vendas, justificativa de budget

---

### 8. Score de Confiabilidade

**`GET /api/spot/reliability`**

Analisa histórico de confiabilidade de cada GPU.

**Request**:
```bash
curl "https://dumontcloud.com/api/spot/reliability?gpu=RTX%204090" \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "gpu_name": "RTX 4090",
  "reliability_score": 0.92,
  "uptime_percent_30d": 94.5,
  "mean_time_between_interruptions_hours": 72,
  "avg_interruption_duration_minutes": 3,
  "risk_level": "low"
}
```

**Quando usar**: SLA planning, escolha de GPU crítica

---

### 9. Taxa de Interrupção

**`GET /api/spot/interruption-rates`**

Histórico de interrupções por GPU e região.

**Request**:
```bash
curl "https://dumontcloud.com/api/spot/interruption-rates?period=7d" \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "period": "7d",
  "gpus": [
    {
      "gpu_name": "RTX 4090",
      "total_interruptions": 3,
      "interruption_rate_per_day": 0.43,
      "avg_duration_minutes": 2.5,
      "worst_region": "US-West"
    }
  ]
}
```

**Quando usar**: Reports de reliability, debugging de failovers

---

### 10. Janelas Seguras (Safe Windows)

**`GET /api/spot/safe-windows/{gpu_name}`**

Identifica horários com menor risco de interrupção.

**Request**:
```bash
curl https://dumontcloud.com/api/spot/safe-windows/RTX%204090 \
  -H "Authorization: Bearer TOKEN"
```

**Response**:
```json
{
  "gpu_name": "RTX 4090",
  "timezone": "UTC",
  "safe_windows": [
    {
      "day_of_week": "Monday",
      "start_hour": 2,
      "end_hour": 8,
      "safety_score": 0.95,
      "avg_price": 0.38,
      "reasoning": "Baixa demanda, menor interrupção histórica"
    },
    {
      "day_of_week": "Saturday",
      "start_hour": 0,
      "end_hour": 12,
      "safety_score": 0.92,
      "avg_price": 0.39
    }
  ],
  "worst_windows": [
    {
      "day_of_week": "Friday",
      "start_hour": 14,
      "end_hour": 18,
      "safety_score": 0.65,
      "reasoning": "Pico de demanda"
    }
  ]
}
```

**Quando usar**: Scheduling de treinamentos longos, batch jobs

---

## 🧪 Exemplos de Uso

### Caso 1: Encontrar Melhor Momento para Treinar

```python
import requests
from datetime import datetime

# 1. Verificar predição de preços
pred = requests.get(
    "https://dumontcloud.com/api/spot/prediction/RTX%204090",
    headers={"Authorization": "Bearer TOKEN"}
).json()

# 2. Verificar janelas seguras
windows = requests.get(
    "https://dumontcloud.com/api/spot/safe-windows/RTX%204090",
    headers={"Authorization": "Bearer TOKEN"}
).json()

# 3. Decidir quando criar instância
if pred['predictions']['next_6h']['price'] < 0.40:
    print("Criar instância agora (preço vai subir)")
else:
    safe_window = windows['safe_windows'][0]
    print(f"Esperar até {safe_window['day_of_week']} {safe_window['start_hour']}h")
```

### Caso 2: Comparar GPUs para Projeto

```python
# Calcular custo de treinamento para diferentes GPUs
gpus = ["RTX 4090", "A100", "RTX 3090"]

for gpu in gpus:
    cost = requests.get(
        f"https://dumontcloud.com/api/spot/training-cost",
        params={"model": "llama2-13b", "gpu": gpu},
        headers={"Authorization": "Bearer TOKEN"}
    ).json()
    
    print(f"{gpu}: ${cost['cost_dumont']} (Economia: {cost['savings_percent']}%)")
```

---

## 📊 Dashboards Recomendados

### Dashboard 1: Market Overview
- **Widgets**: Monitor de preços, Disponibilidade por região
- **Refresh**: A cada 5 minutos
- **Público**: Ops team, Finance

### Dashboard 2: Reliability Tracking
- **Widgets**: Taxa de interrupção, Score de confiabilidade
- **Refresh**: Diário
- **Público**: SRE, DevOps

### Dashboard 3: Cost Optimization
- **Widgets**: Predição de preços, Safe windows, Calculadora
- **Refresh**: Hourly
- **Público**: Developers, Researchers

---

## 🚀 Roadmap

### Q1 2025
- [ ] Alertas customizáveis (ex: "Avise quando RTX 4090 < $0.35")
- [ ] Webhook para mudanças de preço

### Q2 2025
- [ ] API pública para partners
- [ ] Dados históricos de 12 meses (atualmente 30 dias)

---

**Última atualização**: 2025-12-19  
**Mantido por**: ML & Analytics Team  
**Dúvidas**: analytics@dumontcloud.com
