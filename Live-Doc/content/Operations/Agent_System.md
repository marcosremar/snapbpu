# 🤖 Agent System - Heartbeat & Lifecycle

## Visão Geral

O **Agent System** é responsável por monitorar o status de todas as instâncias GPU/CPU e detectar automaticamente instâncias "órfãs" (esquecidas rodando sem uso).

---

## 🎯 Problema que Resolve

### Cenário Sem Agent System
```
Usuário cria GPU → Esquece de deletar → Paga $0.40/h indefinidamente
```

**Custo**: $292.80/mês por GPU esquecida

### Cenário Com Agent System
```
Usuário cria GPU → Não usa por 24h → Sistema alerta + auto-hiberna → $0.01/h
```

**Economia**: 97.5% ($285/mês economizado)

---

## 🔄 Como Funciona

### 1. Heartbeat Mechanism

Cada instância envia um **heartbeat a cada 60 segundos**:

```python
# Dentro da instância (agente local)
import requests
import time

while True:
    try:
        requests.post(
            "https://dumontcloud.com/api/agent/status",
            json={
                "instance_id": "28864630",
                "gpu_utilization": 87,
                "vram_used_gb": 18.4,
                "cost_accumulated": 2.40,
                "status": "running"
            },
            headers={"Authorization": "Bearer INSTANCE_TOKEN"}
        )
    except:
        pass
    
    time.sleep(60)
```

### 2. Detecção de Órfãs

Se uma instância **não envia heartbeat por >5 minutos**:

```python
# Backend (automatic check)
if last_heartbeat > 5min_ago:
    instance.status = "orphaned"
    send_alert(user, f"Instance {instance_id} may be stuck")
    
if last_heartbeat > 30min_ago:
    instance.hibernate()  # Auto-hibernate para economizar
```

---

## 📡 API Endpoints

### 1. Enviar Heartbeat

**`POST /api/agent/status`**

Instância reporta seu status.

**Request**:
```bash
curl -X POST https://dumontcloud.com/api/agent/status \
  -H "Authorization: Bearer INSTANCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instance_id": "28864630",
    "gpu_utilization": 87,
    "vram_used_gb": 18.4,
    "cpu_utilization": 45,
    "ram_used_gb": 12.0,
    "disk_used_gb": 45.2,
    "cost_accumulated": 2.40,
    "status": "running",
    "uptime_seconds": 7200
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Heartbeat received",
  "next_heartbeat_in_seconds": 60,
  "actions": []
}
```

**Se auto-hibernação detectada**:
```json
{
  "success": true,
  "message": "Low utilization detected",
  "actions": [
    {
      "type": "hibernate_warning",
      "message": "GPU <5% utilization for 3min. Hibernating in 2min.",
      "countdown_seconds": 120
    }
  ]
}
```

---

### 2. Listar Instâncias com Heartbeat

**`GET /api/agent/instances`**

Lista todas as instâncias e seu status de heartbeat.

**Request**:
```bash
curl https://dumontcloud.com/api/agent/instances \
  -H "Authorization: Bearer USER_TOKEN"
```

**Response**:
```json
{
  "instances": [
    {
      "instance_id": "28864630",
      "name": "ML Training Rig",
      "status": "running",
      "last_heartbeat": "2025-12-19T03:25:30Z",
      "seconds_since_heartbeat": 15,
      "health": "healthy",
      "gpu_utilization": 87,
      "cost_today": 2.40
    },
    {
      "instance_id": "98765432",
      "name": "Render Farm",
      "status": "orphaned",
      "last_heartbeat": "2025-12-19T02:15:00Z",
      "seconds_since_heartbeat": 4230,
      "health": "unhealthy",
      "gpu_utilization": null,
      "cost_today": 8.50,
      "alert": "No heartbeat for 70 minutes. May be stuck."
    }
  ]
}
```

---

### 3. Ver Detalhes de Heartbeat

**`GET /api/agent/instances/{instance_id}`**

Histórico detalhado de heartbeats.

**Request**:
```bash
curl https://dumontcloud.com/api/agent/instances/28864630 \
  -H "Authorization: Bearer USER_TOKEN"
```

**Response**:
```json
{
  "instance_id": "28864630",
  "total_heartbeats": 542,
  "first_heartbeat": "2025-12-18T12:00:00Z",
  "last_heartbeat": "2025-12-19T03:25:30Z",
  "uptime_percent": 99.8,
  "missed_heartbeats": 1,
  "avg_gpu_utilization": 82.5,
  "recent_heartbeats": [
    {
      "timestamp": "2025-12-19T03:25:30Z",
      "gpu_utilization": 87,
      "vram_used_gb": 18.4,
      "status": "running"
    },
    {
      "timestamp": "2025-12-19T03:24:30Z",
      "gpu_utilization": 85,
      "vram_used_gb": 18.2,
      "status": "running"
    }
  ]
}
```

---

### 4. Keep-Alive Manual

**`POST /api/agent/instances/{instance_id}/keep-alive`**

Força keep-alive mesmo sem heartbeat automático.

**Request**:
```bash
curl -X POST https://dumontcloud.com/api/agent/instances/28864630/keep-alive \
  -H "Authorization: Bearer USER_TOKEN"
```

**Response**:
```json
{
  "success": true,
  "message": "Manual keep-alive registered",
  "valid_for_minutes": 60
}
```

**Quando usar**: Debugging, instâncias batch que não rodam agente

---

## 🛡️ Políticas de Lifecycle

### Auto-Hibernação por Ociocidade

```python
# Lógica do backend
if gpu_utilization < 5% for 3min:
    send_warning(instance, "Hibernating in 2min")
    
if gpu_utilization < 5% for 5min:
    instance.hibernate()
    notify_user("Instance hibernated due to low usage")
```

### Detecção de Instâncias Órfãs

```python
# Executa a cada 5 minutos
for instance in all_instances:
    if instance.last_heartbeat > 30min_ago:
        instance.mark_as_orphaned()
        send_alert(user, "Instance may be stuck")
        
    if instance.last_heartbeat > 2h_ago:
        instance.force_hibernate()
        send_critical_alert(user, "Instance force-hibernated")
```

### Auto-Delete de Instâncias Esquecidas

```python
# Executa diariamente
for instance in orphaned_instances:
    if instance.orphaned_for > 7_days:
        snapshot = create_snapshot(instance)
        instance.delete()
        notify_user(
            "Instance auto-deleted after 7 days orphaned. "
            f"Snapshot saved: {snapshot.id}"
        )
```

---

## 🔧 Instalação do Agente

### Método 1: Automático (Recomendado)

O agente é **pré-instalado** em todas as imagens Dumont Cloud.

Verificar se está rodando:
```bash
systemctl status dumont-agent
```

### Método 2: Manual

```bash
# Baixar agente
wget https://dumontcloud.com/downloads/agent/latest/dumont-agent

# Dar permissão
chmod +x dumont-agent

# Configurar
export DUMONT_INSTANCE_ID="28864630"
export DUMONT_API_TOKEN="your_instance_token"

# Rodar como serviço
sudo ./dumont-agent install
sudo systemctl start dumont-agent
```

---

## 📊 Métricas Exportadas

O Agent System exporta métricas Prometheus:

```promql
# Total de instâncias ativas
dumont_agents_active

# Instâncias órfãs detectadas
dumont_agents_orphaned

# Taxa de heartbeat perdidos
rate(dumont_agents_heartbeat_missed_total[5m])

# Utilização média de GPU
avg(dumont_agents_gpu_utilization_percent)
```

---

## 🚨 Alertas Recomendados

### 1. Instância Órfã Detectada

```yaml
alert: OrphanedInstance
expr: dumont_agents_orphaned > 0
for: 5m
labels:
  severity: warning
annotations:
  summary: "Instance {{ $labels.instance_id }} is orphaned"
  description: "No heartbeat for 30+ minutes"
```

### 2. Alto Custo por Instância Ociosa

```yaml
alert: HighCostIdleInstance
expr: dumont_agents_cost_accumulated > 10 AND dumont_agents_gpu_utilization < 10
for: 1h
labels:
  severity: critical
annotations:
  summary: "Instance wasting money"
  description: "Cost >$10 but GPU <10% utilization"
```

---

## 🧪 Testes

### Simular Heartbeat Perdido

```bash
# Parar agente propositalmente
sudo systemctl stop dumont-agent

# Aguardar 6 minutos

# Verificar se foi detectado como órfã
curl https://dumontcloud.com/api/agent/instances \
  -H "Authorization: Bearer TOKEN"
```

### Simular Auto-Hibernação

```python
# Enviar heartbeat com GPU ociosa
for i in range(6):  # 6 minutos
    requests.post(
        "https://dumontcloud.com/api/agent/status",
        json={
            "instance_id": "test-instance",
            "gpu_utilization": 2,  # <5%
            "status": "running"
        }
    )
    time.sleep(60)

# Deve hibernar automaticamente após 5 min
```

---

## 🔍 Troubleshooting

### Problema: Heartbeat não está sendo recebido

**Soluções**:
```bash
# 1. Verificar se agente está rodando
systemctl status dumont-agent

# 2. Verificar logs
journalctl -u dumont-agent -f

# 3. Testar conectividade
curl https://dumontcloud.com/api/agent/status

# 4. Verificar token
echo $DUMONT_API_TOKEN
```

### Problema: Instância marcada como órfã incorretamente

**Soluções**:
```bash
# 1. Enviar keep-alive manual
curl -X POST https://dumontcloud.com/api/agent/instances/ID/keep-alive

# 2. Reiniciar agente
sudo systemctl restart dumont-agent

# 3. Verificar clock sync (NTP)
timedatectl status
```

---

## 📚 Boas Práticas

### 1. Sempre Rodar Agente
❌ **Não fazer**: Desabilitar agente para "economizar recursos"  
✅ **Fazer**: Manter agente rodando (usa <1% CPU, <10MB RAM)

### 2. Monitorar Órfãs Semanalmente
```bash
# Criar script semanal
curl https://dumontcloud.com/api/agent/instances | \
  jq '.instances[] | select(.health == "unhealthy")'
```

### 3. Configurar Alertas
Slack ou email quando instância órfã >30min

---

**Última atualização**: 2025-12-19  
**Mantido por**: Infrastructure Team  
**Dúvidas**: infra@dumontcloud.com
