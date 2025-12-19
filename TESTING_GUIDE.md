# GUIA DE TESTES: CPU STANDBY FAILOVER AUTOMÁTICO

## 🚀 Como Executar os Testes

### 1. SIMULAÇÃO VISUAL (Recomendado para começar)

A forma mais intuitiva de entender o sistema:

```bash
# Executar simulador interativo
python3 /home/ubuntu/dumont-cloud/scripts/simulate_failover.py

# Modo silencioso (apenas saída final)
python3 /home/ubuntu/dumont-cloud/scripts/simulate_failover.py --quiet
```

**Output:**
- Timeline visual completa do failover
- Performance metrics por fase
- Relatório de eventos críticos
- Recomendações de otimização

**Tempo de execução:** ~30 segundos
**Saída esperada:** Ver seção "Output da Simulação" abaixo

---

### 2. TESTES UNITÁRIOS (Desenvolvimento)

Suite completa de testes pytest:

```bash
# Instalar dependências (se não tiver)
pip install pytest pytest-asyncio

# Rodar todos os testes
pytest /home/ubuntu/dumont-cloud/tests/test_failover_comprehensive.py -v

# Rodar teste específico
pytest /home/ubuntu/dumont-cloud/tests/test_failover_comprehensive.py::TestCPUStandbySync::test_sync_gpu_to_cpu_continuous -v

# Com mais detalhes de output
pytest /home/ubuntu/dumont-cloud/tests/test_failover_comprehensive.py -v -s

# Apenas relatório de cobertura
pytest /home/ubuntu/dumont-cloud/tests/test_failover_comprehensive.py --cov=src
```

**Testes disponíveis:**

#### Sincronização
- `test_sync_gpu_to_cpu_continuous` - Sincronização contínua
- `test_sync_failure_recovery` - Recuperação de falha de sync

#### Detecção de Falha
- `test_gpu_failure_detection_threshold` - Detecção com threshold
- `test_failover_state_transition` - Transição de estado

#### Restauração de Dados
- `test_data_sync_to_cpu_before_failure` - Sincronização antes da falha
- `test_data_consistency_after_failover` - Consistência após failover
- `test_data_restore_from_cpu_to_new_gpu` - Restauração

#### Auto-Recovery
- `test_auto_recovery_find_gpu` - Busca de GPU
- `test_auto_recovery_provision_gpu` - Provisionamento
- `test_auto_recovery_wait_for_ssh` - Aguardar SSH
- `test_auto_recovery_full_cycle` - Ciclo completo

#### Integração
- `test_complete_failover_flow` - Fluxo completo
- `test_standby_manager_create_association` - Criação de associação
- `test_standby_manager_mark_gpu_failed` - Marcar GPU como falha

---

### 3. TESTES INTEGRADOS (Staging)

Para testar com componentes reais (ainda simulados):

```bash
# Requer backend rodando
cd /home/ubuntu/dumont-cloud
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8766

# Em outro terminal, rodar testes de API
pytest /home/ubuntu/dumont-cloud/tests/test_failover_api_integration.py -v
```

**Testes:**
- Create GPU + CPU standby
- Sync status monitoring
- Trigger failover via API
- Auto-recovery progress
- Restauração de dados

---

### 4. TESTES EM PRODUÇÃO (Com infraestrutura real)

Para testar com GPU e CPU reais:

```bash
# Requer:
# 1. GPU em Vast.ai já provisionada
# 2. GCP credentials configuradas
# 3. Restic/S3 credentials

# Teste manual de failover
python3 /home/ubuntu/dumont-cloud/scripts/test_failover_manual.py \
  --gpu-instance-id 123456 \
  --cpu-standby-ip 35.204.123.45

# Teste de sync com dados reais
python3 /home/ubuntu/dumont-cloud/scripts/test_sync_real_data.py \
  --workspace-size 10GB \
  --duration 3600  # 1 hora
```

---

## 📊 Output da Simulação

Ao rodar `simulate_failover.py`, você verá:

```
==========================================================================================
                       SIMULADOR DE FAILOVER AUTOMÁTICO - CPU STANDBY
==========================================================================================

[95m[T000.00s] [PHASE  ] Iniciando simulação...[0m

==========================================================================================
                                   FASE 1: SETUP INICIAL
==========================================================================================

[94m[T000.50s] [INFO   ] Configurando GPU instance (Vast.ai)...[0m
[94m[T000.80s] [INFO   ]   ✓ GPU Instance ID: 123456[0m
[94m[T000.80s] [INFO   ]   ✓ GPU Model: RTX 4090[0m
...
```

**Cores:**
- 🔵 Blue = INFO (informações)
- 🟢 Green = SYNC (sincronização)
- 🟡 Yellow = HEALTH (health check)
- 🔴 Red = ERROR (erros)
- 🟢 Green = SUCCESS (sucesso)
- 🟣 Magenta = PHASE (fases)
- 🔵 Cyan = METRIC (métricas)

---

## 🔍 Interpretando os Resultados

### Tempos Esperados (Simulação)

```
FASE 1 (Setup):          2.00s - Rápido
FASE 2 (Operação):       3.50s - Normal
FASE 3 (GPU Falha):      1.10s - Instantâneo
FASE 4 (Detecção):       1.80s - ~30s em produção
FASE 5 (Failover):       2.50s - Rápido
FASE 6 (Auto-Recovery):  5.71s - ~15 min em produção
FASE 7 (Recuperado):     2.00s - Final
───────────────────────────────────────
TOTAL:                  18.63s - ~15-20 min em produção
```

### Métricas Importantes

```
Sincronizações: 5 bem-sucedidas
  → Taxa de sucesso: 100%
  → Tempo médio: 0.2s por sync

Health checks: 8 total (5 OK, 3 FAIL)
  → Taxa de detecção: 100%
  → Tempo até detecção: 2.1s

Failover:
  → Tempo de acionamento: <1s
  → Tempo até CPU pronto: 2.5s
  → Dados preservados: 100%

Auto-recovery:
  → Buscou GPU: ✓
  → Provisionou GPU: ✓
  → SSH pronto: ✓
  → Dados restaurados: ✓
  → Taxa de sucesso: 100%
```

---

## ❌ Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'src'"

**Causa:** Script rodado do diretório errado

**Solução:**
```bash
cd /home/ubuntu/dumont-cloud
python3 scripts/simulate_failover.py
```

### Erro: "Permission denied: scripts/simulate_failover.py"

**Causa:** Script não tem permissão de execução

**Solução:**
```bash
chmod +x /home/ubuntu/dumont-cloud/scripts/simulate_failover.py
python3 /home/ubuntu/dumont-cloud/scripts/simulate_failover.py
```

### Teste pytest falha com "fixtures not found"

**Causa:** Pytest não encontra os mocks

**Solução:**
```bash
# Instalar pytest e dependências
pip install pytest pytest-asyncio unittest-mock

# Rodar do diretório correto
cd /home/ubuntu/dumont-cloud
pytest tests/test_failover_comprehensive.py -v
```

### Output muito colorido, difícil de ler

**Solução:** Redirecionar para arquivo
```bash
python3 scripts/simulate_failover.py > simulation_output.txt 2>&1
cat simulation_output.txt
```

---

## 📈 Analisando Performance

### Coletar dados de múltiplas execuções

```bash
#!/bin/bash
# run_performance_tests.sh

echo "Executando 5 simulações..."
for i in {1..5}; do
  echo "Simulação $i:"
  python3 scripts/simulate_failover.py --quiet > sim_$i.log 2>&1

  # Extrair tempos críticos
  grep "Duração" sim_$i.log
done

echo "Análise concluída!"
```

### Métricas a monitorar

```
1. Tempo de detecção (alvo: <30s)
2. Tempo de failover (alvo: <2s)
3. Taxa de sucesso de sync (alvo: >99%)
4. Taxa de sucesso de recovery (alvo: 100%)
5. Tempo total de recovery (alvo: <20 min)
```

---

## 🧪 Modificando os Testes

### Mudar threshold de detecção

```python
# Em test_failover_comprehensive.py
config = CPUStandbyConfig(
    health_check_interval=5,        # Reduzir para 5s
    failover_threshold=2,           # Reduzir para 2 falhas
)
```

**Efeito:** Detecção mais rápida (~10s), mas mais false positives

### Simular mais syncs

```python
# Em test_cpu_standby_sync.py
num_syncs = 10  # Aumentar de 5 para 10
```

**Efeito:** Teste mais dados sincronizados

### Simular workspace maior

```python
# Em test_data_restoration.py
self.mock_workspace_gpu = {
    'model.pt': {'size': 10000000},  # 10GB
    'data.csv': {'size': 5000000},   # 5GB
    'config.json': {'size': 1000},
}
```

**Efeito:** Simular volumes maiores

### Adicionar novo teste

```python
def test_custom_failover_scenario(self):
    """Teste: Seu cenário customizado"""
    self.metrics.log("TEST: Seu teste aqui")

    # Sua lógica
    assert condition

    self.metrics.log("✅ Teste passou")
```

---

## 🎯 Checklist de Teste

Antes de colocar em produção:

- [ ] Simulação visual roda sem erros
- [ ] Todos os testes unitários passam
- [ ] Tempos de failover < 2 segundos
- [ ] Taxa de sucesso de sync > 99%
- [ ] Dados preservados em 100% dos casos
- [ ] Auto-recovery provisiona nova GPU
- [ ] Health checks detectam falha em < 30s
- [ ] CPU standby permanece sincronizado
- [ ] Failover é transparente para usuário
- [ ] Relatório de performance gerado corretamente

---

## 📚 Arquivos Relevantes

```
/home/ubuntu/dumont-cloud/
├── scripts/
│   ├── simulate_failover.py          ← Simulador visual
│   ├── test_failover_manual.py       ← Testes com GPU real
│   └── test_sync_real_data.py        ← Teste de sync real
├── tests/
│   └── test_failover_comprehensive.py ← Suite de testes
├── src/
│   └── services/
│       ├── standby_manager.py         ← Orquestrador
│       ├── cpu_standby_service.py    ← Serviço principal
│       └── ...
└── FAILOVER_PERFORMANCE_REPORT.md    ← Relatório detalhado
```

---

## 🔗 Links Úteis

- **Código da API:** `src/api/v1/endpoints/standby.py`
- **Configuração:** `src/services/cpu_standby_service.py`
- **Testes:** `tests/test_failover_comprehensive.py`
- **Relatório:** `FAILOVER_PERFORMANCE_REPORT.md`
- **README:** `README.md`

---

## 💬 Dúvidas?

Verifique:
1. `FAILOVER_PERFORMANCE_REPORT.md` - Documentação completa
2. `README.md` - Visão geral do sistema
3. Código comentado em `src/services/cpu_standby_service.py`
4. Logs do simulador (última execução)

---

**Última atualização:** 2025-12-19
**Versão:** 1.0
