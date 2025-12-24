# Machine History e Blacklist

> **STATUS**: Operacional | Melhora qualidade das reservas de GPU

## O que e Machine History?

Machine History e o sistema de **rastreamento de confiabilidade** do Dumont Cloud. Ele monitora o historico de cada maquina GPU utilizada, registrando:

- Tentativas de deploy (sucesso/falha)
- Taxa de sucesso por maquina
- Motivos de falha
- Blacklist automatico de maquinas problematicas

### Por que isso importa?

Nem todas as maquinas GPU sao iguais. Algumas tem problemas recorrentes:
- Drivers desatualizados
- Hardware instavel
- Conectividade ruim
- Boot lento ou falho

O Machine History **aprende** quais maquinas sao confiaveis e **evita** as problematicas automaticamente.

---

## Como Funciona

```
┌─────────────────────────────────────────────────────────────┐
│              SISTEMA DE MACHINE HISTORY                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. REGISTRO DE TENTATIVAS                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   Deploy    │ ──▶ │  Resultado  │ ──▶ │  Registro   │  │
│   │   GPU       │     │  Sucesso?   │     │  no DB      │  │
│   └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                             │
│   2. CALCULO DE CONFIABILIDADE                              │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │  Historico  │ ──▶ │  Taxa de    │ ──▶ │   Status    │  │
│   │  Tentativas │     │  Sucesso    │     │  Confiavel? │  │
│   └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                             │
│   3. FILTRAGEM AUTOMATICA                                   │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   Busca     │ ──▶ │  Exclui     │ ──▶ │  Ofertas    │  │
│   │   Ofertas   │     │  Blacklist  │     │  Limpas     │  │
│   └─────────────┘     └─────────────┘     └─────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Fluxo de Registro

1. **Deploy**: Usuario solicita uma GPU
2. **Tentativa**: Sistema tenta reservar a maquina
3. **Resultado**: Sucesso ou falha e registrado
4. **Estatisticas**: Taxa de sucesso e atualizada
5. **Blacklist**: Se taxa < 30%, maquina e bloqueada automaticamente

---

## Niveis de Confiabilidade

| Status | Taxa de Sucesso | Cor | Acao |
|--------|-----------------|-----|------|
| **Excellent** | >= 90% | Verde | Prioridade alta |
| **Good** | >= 70% | Verde claro | Normal |
| **Fair** | >= 50% | Amarelo | Aviso na UI |
| **Poor** | >= 30% | Laranja | Alerta |
| **Blacklisted** | < 30% | Vermelho | Bloqueado |

---

## Blacklist Automatico

### Quando uma maquina e bloqueada?

1. **Taxa de sucesso < 30%** com minimo de 3 tentativas
2. **3 falhas consecutivas** em deploys
3. **Falha critica** (erro de hardware, timeout)
4. **Bloqueio manual** pelo usuario

### Tipos de Blacklist

| Tipo | Descricao | Duracao |
|------|-----------|---------|
| **automatic** | Sistema detectou falhas | 7 dias |
| **manual** | Usuario bloqueou | Permanente |
| **temporary** | Falha temporaria | 24 horas |

### Motivos Comuns de Blacklist

- `driver_mismatch` - Drivers CUDA incompativeis
- `boot_timeout` - Maquina nao iniciou a tempo
- `ssh_failed` - Conexao SSH falhou
- `gpu_not_ready` - GPU nao inicializou
- `frequent_interrupts` - Muitas interrupcoes spot

---

## Impacto no Sistema

### Deploy Wizard

O assistente de deploy **automaticamente**:
- Filtra maquinas blacklisted
- Ordena por confiabilidade
- Mostra avisos para maquinas com historico ruim

### Listagem de Ofertas

Na busca avancada de GPUs:
- Maquinas blacklisted sao **ocultadas por padrao**
- Parametro `include_blacklisted=true` mostra todas
- Cada oferta mostra `reliability_status` e `success_rate`

### Serverless/Failover

Durante failover automatico:
- Sistema prioriza maquinas confiaveis
- Evita maquinas com historico de falhas
- Melhora tempo de recovery

---

## Como Usar

### Ver Historico de uma Maquina

No Dashboard:
1. Va em **Machines** > **Historico**
2. Clique em uma maquina
3. Veja tentativas, taxa de sucesso, e motivos de falha

### Gerenciar Blacklist

#### Adicionar ao Blacklist
```bash
# Via CLI
dumont history blacklist add vast:12345 --reason "Falhas frequentes"

# Via API
curl -X POST /api/v1/machines/history/blacklist \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"machine_id":"12345","provider":"vast","reason":"Falhas frequentes"}'
```

#### Remover do Blacklist
```bash
# Via CLI
dumont history blacklist remove vast:12345

# Via API
curl -X DELETE /api/v1/machines/history/blacklist/vast/12345 \
  -H "Authorization: Bearer $TOKEN"
```

#### Listar Blacklist
```bash
# Via CLI
dumont history blacklist list

# Via API
curl /api/v1/machines/history/blacklist \
  -H "Authorization: Bearer $TOKEN"
```

### Verificar se Maquina esta Bloqueada
```bash
# Via CLI
dumont history check vast:12345

# Via API
curl /api/v1/machines/history/blacklist/check/vast/12345 \
  -H "Authorization: Bearer $TOKEN"
```

---

## API Reference

### Endpoints de Machine History

```bash
# Listar blacklist
GET /api/v1/machines/history/blacklist

# Adicionar ao blacklist
POST /api/v1/machines/history/blacklist
{
  "machine_id": "12345",
  "provider": "vast",
  "reason": "Motivo do bloqueio",
  "blacklist_type": "manual"  # ou "automatic", "temporary"
}

# Verificar se maquina esta bloqueada
GET /api/v1/machines/history/blacklist/check/{provider}/{machine_id}

# Remover do blacklist
DELETE /api/v1/machines/history/blacklist/{provider}/{machine_id}

# Resumo do historico
GET /api/v1/machines/history/summary
```

### Ofertas com Machine History

As ofertas de GPU agora incluem campos de historico:

```json
{
  "id": 29102584,
  "gpu_name": "RTX 4090",
  "dph_total": 0.25,
  "machine_id": "12345",
  "is_blacklisted": false,
  "blacklist_reason": null,
  "success_rate": 0.85,
  "total_attempts": 20,
  "reliability_status": "good"
}
```

---

## Indicadores na UI

### Card de Oferta

| Indicador | Significado |
|-----------|-------------|
| Badge verde "Verificado" | Maquina com alta confiabilidade |
| Badge "Historico: 85%" | Taxa de sucesso da maquina |
| Aviso amarelo | Algumas falhas recentes |
| Aviso laranja | Baixa confiabilidade |
| Barra vermelha "Bloqueada" | Maquina no blacklist |

### Cores de Confiabilidade

- **Verde**: >= 90% sucesso
- **Amarelo**: 70-89% sucesso
- **Vermelho**: < 70% sucesso

---

## Banco de Dados

### Tabelas

```sql
-- Registro de tentativas
CREATE TABLE machine_attempts (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50),
    machine_id VARCHAR(100),
    attempt_type VARCHAR(50),
    success BOOLEAN,
    error_message TEXT,
    duration_seconds FLOAT,
    created_at TIMESTAMP
);

-- Blacklist
CREATE TABLE machine_blacklist (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50),
    machine_id VARCHAR(100),
    blacklist_type VARCHAR(50),
    reason TEXT,
    total_attempts INTEGER,
    failed_attempts INTEGER,
    failure_rate FLOAT,
    blacklisted_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN
);

-- Estatisticas agregadas
CREATE TABLE machine_stats (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50),
    machine_id VARCHAR(100),
    total_attempts INTEGER,
    successful_attempts INTEGER,
    failed_attempts INTEGER,
    success_rate FLOAT,
    avg_boot_time FLOAT,
    last_attempt_at TIMESTAMP,
    last_success_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    reliability_score FLOAT
);
```

---

## Configuracao

### Variaveis de Ambiente

```bash
# Banco de dados (obrigatorio)
DATABASE_URL=postgresql://user:pass@localhost:5432/dumont_cloud
DB_USER=dumont
DB_PASSWORD=dumont123
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dumont_cloud
```

### Parametros de Blacklist

No codigo (`src/services/machine_history_service.py`):

```python
# Minimo de tentativas para blacklist automatico
MIN_ATTEMPTS_FOR_BLACKLIST = 3

# Taxa de sucesso minima
MIN_SUCCESS_RATE = 0.3  # 30%

# Duracao do blacklist automatico
AUTOMATIC_BLACKLIST_DAYS = 7

# Duracao do blacklist temporario
TEMPORARY_BLACKLIST_HOURS = 24
```

---

## Best Practices

### Para Usuarios

1. **Reporte maquinas problematicas** - Ajuda a melhorar o sistema
2. **Use o modo automatico** - Deixe o sistema filtrar maquinas ruins
3. **Verifique historico** - Antes de reservar manualmente

### Para o Sistema

1. **Priorize maquinas confiaveis** no Deploy Wizard
2. **Exclua blacklisted** por padrao nas buscas
3. **Atualize estatisticas** apos cada deploy
4. **Limpe blacklist antigo** automaticamente

---

## Ver Tambem

- [GPU Warm Pool](05_GPU_Warm_Pool.md) - Failover rapido
- [CPU Standby](04_CPU_Standby.md) - Fallback para CPU
- [API Overview](/admin/doc/live#04_API/01_Overview.md) - Documentacao da API
