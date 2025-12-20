# Planejamento de Otimizações - Sistema de Failover

**Objetivo:** Reduzir MTTR de ~108s para ~73-88s (melhoria de 19-32%)

**Status Atual:**
- ✅ Failover básico funcionando (107.9s MTTR)
- ✅ Snapshot incremental implementado (não testado)
- ✅ Race strategy para GPU provisioning (funcionando)
- ✅ Clock sync implementado (não aplicado em todos scripts)

---

## 📋 FASE 1: Fixes Críticos (P0) - Bloqueadores

### ✅ 1.1 Clock Sync na Restauração
**Impacto:** Fix blocker - Restore falhando em 100% dos casos
**Tempo estimado:** 15 minutos

- [ ] Verificar qual script de restore está sendo usado (B2 vs Hybrid)
- [ ] Adicionar NTP sync no início do script B2 restore
- [ ] Testar com GPU nova para confirmar que clock sync funciona
- [ ] Adicionar logging: "Clock synced: before={X} after={Y}"

**Arquivos:**
- `src/services/gpu/snapshot.py` - Método `_generate_b2_restore_script()`

**Código:**
```python
# Logo no início do script, antes de importar b2sdk
subprocess.run(["apt-get", "update", "-qq"], capture_output=True)
subprocess.run(["apt-get", "install", "-qq", "-y", "ntpdate"], capture_output=True)
subprocess.run(["ntpdate", "-s", "pool.ntp.org"], capture_output=True)
```

---

### ✅ 1.2 Credenciais B2 do .env
**Impacto:** Segurança - Credenciais hardcoded
**Tempo estimado:** 20 minutos

- [ ] Adicionar B2_KEY_ID e B2_APPLICATION_KEY ao script via env vars
- [ ] Modificar `_generate_b2_restore_script()` para usar variáveis
- [ ] Modificar `_generate_hybrid_snapshot_script()` para usar variáveis
- [ ] Testar criação e restore de snapshot com credenciais do .env
- [ ] Remover credenciais hardcoded dos scripts

**Arquivos:**
- `src/services/gpu/snapshot.py` - Todos os métodos `_generate_*_script()`
- `.env` - Verificar se tem B2_KEY_ID e B2_APPLICATION_KEY

**Código:**
```python
def _generate_b2_restore_script(self, ...):
    # Ler do .env
    b2_key_id = os.getenv("B2_KEY_ID")
    b2_app_key = os.getenv("B2_APPLICATION_KEY")

    return f"""
import os
os.environ["AWS_ACCESS_KEY_ID"] = "{b2_key_id}"
os.environ["AWS_SECRET_ACCESS_KEY"] = "{b2_app_key}"
...
"""
```

---

### ✅ 1.3 s5cmd instalado localmente
**Impacto:** Fix incremental snapshot
**Tempo estimado:** 10 minutos

- [ ] Instalar s5cmd no servidor de controle
- [ ] Verificar que `which s5cmd` retorna path válido
- [ ] Testar `_find_latest_base_snapshot()` consegue listar B2
- [ ] Adicionar s5cmd ao Dockerfile/requirements se necessário

**Comandos:**
```bash
# Instalar s5cmd
curl -sL https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz | tar xz
sudo mv s5cmd /usr/local/bin/
sudo chmod +x /usr/local/bin/s5cmd

# Testar
s5cmd --version
```

---

## 📋 FASE 2: Performance (P1) - Impacto Alto

### ✅ 2.1 Snapshot Metadata Persistence
**Impacto:** -5s no MTTR (incremental funciona de verdade)
**Tempo estimado:** 30 minutos

- [ ] Modificar `create_snapshot()` para salvar metadata.json no B2
- [ ] Metadata deve conter: `{"files": {"path/file.txt": mtime, ...}, "timestamp": ...}`
- [ ] Modificar `create_incremental_snapshot()` para baixar e comparar metadata
- [ ] Testar: criar base, modificar 1 arquivo, incremental deve pegar só 1 arquivo
- [ ] Adicionar logging: "Incremental: X files changed out of Y total"

**Arquivos:**
- `src/services/gpu/snapshot.py` - `create_snapshot()`, `_generate_hybrid_snapshot_script()`

**Estrutura do metadata.json:**
```json
{
  "snapshot_id": "base-29049571-1766230181",
  "timestamp": 1766230181.5,
  "files": {
    "test/file1.txt": 1766230150.123,
    "test/file2.txt": 1766230150.456,
    "models/model.safetensors": 1766229000.789
  },
  "total_size": 10485760,
  "compression": "lz4"
}
```

---

### ✅ 2.2 Rate Limiting Vast.ai
**Impacto:** -10s no MTTR (menos falhas 429)
**Tempo estimado:** 25 minutos

- [ ] Adicionar rate limiter na classe GPUProvisioner
- [ ] Delay de 200ms entre cada requisição de provisioning
- [ ] Reduzir paralelismo: `gpus_per_round * 3` → `gpus_per_round * 2`
- [ ] Adicionar retry com exponential backoff em erros 429
- [ ] Testar que não recebe mais de 1-2 erros 429 por rodada

**Arquivos:**
- `src/services/gpu/provisioner.py` - `_provision_batch()`

**Código:**
```python
import asyncio

async def provision_one(offer: Dict[str, Any]) -> Optional[GPUCandidate]:
    # Rate limiting
    await asyncio.sleep(0.2)  # 200ms delay

    for attempt in range(3):  # Retry até 3x
        try:
            response = requests.put(...)

            if response.status_code == 429:
                wait = (2 ** attempt)  # 1s, 2s, 4s
                await asyncio.sleep(wait)
                continue

            # ... resto do código
        except:
            ...
```

---

### ✅ 2.3 Timeout Otimizado
**Impacto:** -15s no MTTR (menos rodadas desperdiçadas)
**Tempo estimado:** 15 minutos

- [ ] Analisar logs: qual % de GPUs conecta em <60s vs 60-90s vs >90s
- [ ] Ajustar timeout baseado em dados reais
- [ ] Se 80% conecta em 60s: usar timeout=75s com max_rounds=2
- [ ] Adicionar métrica: "SSH ready time distribution"
- [ ] Testar com 5 provisionamentos e validar melhoria

**Arquivos:**
- `src/services/standby/failover.py` - `execute_failover()`

**Análise necessária:**
```python
# Adicionar ao GPUProvisioner
ssh_ready_times = []

# No _race_for_connection quando SSH conecta:
ssh_ready_time = time.time() - start_time
ssh_ready_times.append(ssh_ready_time)
logger.info(f"SSH ready in {ssh_ready_time:.1f}s")

# No final, calcular distribuição
p50 = percentile(ssh_ready_times, 50)
p90 = percentile(ssh_ready_times, 90)
# Ajustar timeout = p90 + 10s de margem
```

---

## 📋 FASE 3: Qualidade (P2) - Melhorias

### ✅ 3.1 Periodic Snapshots Integrado
**Impacto:** -5s no MTTR (sempre tem snapshot recente)
**Tempo estimado:** 40 minutos

- [ ] Criar endpoint para listar GPUs ativas do usuário
- [ ] Modificar `PeriodicSnapshotService` para consultar GPUs ativas
- [ ] Iniciar serviço no `src/main.py` startup event
- [ ] Configurar intervalo: 1 hora (configurável via .env)
- [ ] Adicionar dashboard: "Last snapshot: X minutes ago"
- [ ] Testar: após 1h, verificar que snapshot foi criado automaticamente

**Arquivos:**
- `src/main.py` - Startup event
- `src/services/standby/periodic_snapshots.py`
- `.env` - Adicionar `PERIODIC_SNAPSHOT_INTERVAL_MINUTES=60`

**Código no main.py:**
```python
from src.services.standby.periodic_snapshots import get_periodic_snapshot_service

@app.on_event("startup")
async def startup_event():
    # Iniciar snapshots periódicos
    snapshot_service = get_periodic_snapshot_service(
        interval_minutes=int(os.getenv("PERIODIC_SNAPSHOT_INTERVAL_MINUTES", "60"))
    )
    await snapshot_service.start()
    logger.info("Periodic snapshot service started")
```

---

### ✅ 3.2 Restore menos verboso
**Impacto:** 0s (UX melhor)
**Tempo estimado:** 10 minutos

- [ ] Modificar scripts de restore para só mostrar progresso a cada 10%
- [ ] Capturar stdout detalhado mas só logar sumário
- [ ] Formato: "Downloading: 45% (450MB/1GB) - 12MB/s"
- [ ] No final: "✓ Restored X files (Y MB) in Z seconds"

**Arquivos:**
- `src/services/gpu/snapshot.py` - Scripts de restore

---

### ✅ 3.3 Validação Pós-Restore
**Impacto:** 0s (confiabilidade +100%)
**Tempo estimado:** 30 minutos

- [ ] Após restore, listar arquivos restaurados
- [ ] Comparar com metadata do snapshot (total de arquivos)
- [ ] Se model files: calcular MD5 e comparar com esperado
- [ ] Retornar `{"validation": "ok", "files_restored": X, "files_expected": Y}`
- [ ] Se validação falhar: marcar failover como failed mesmo que restore complete

**Arquivos:**
- `src/services/gpu/snapshot.py` - `restore_snapshot()`
- `src/services/standby/failover.py` - Adicionar validação após Phase 3

**Código:**
```python
# Após restore
validation = self._validate_restore(
    ssh_host=new_ssh_host,
    ssh_port=new_ssh_port,
    workspace_path=workspace_path,
    expected_metadata=snapshot_metadata
)

if not validation["success"]:
    raise Exception(f"Restore validation failed: {validation['error']}")
```

---

### ✅ 3.4 Métricas Completas no PostgreSQL
**Impacto:** 0s (observabilidade)
**Tempo estimado:** 25 minutos

- [ ] Adicionar campos ao modelo `FailoverTestEvent`:
  - `gpu_provisioning_time_ms` (INT)
  - `original_ssh_host` (VARCHAR(100))
  - `original_ssh_port` (INT)
  - `snapshot_type` (VARCHAR(20)) - "full" ou "incremental"
  - `base_snapshot_id` (VARCHAR(200))
  - `files_changed` (INT) - para snapshots incrementais
- [ ] Criar migration do Alembic
- [ ] Modificar endpoint `/failover/fast` para salvar esses campos
- [ ] Testar query: métricas por tipo de snapshot

**Arquivos:**
- `src/models/instance_status.py` - Classe `FailoverTestEvent`
- `alembic/versions/` - Nova migration
- `src/api/v1/endpoints/standby.py` - Salvar campos extras

**Migration:**
```python
def upgrade():
    op.add_column('failover_test_events',
        sa.Column('gpu_provisioning_time_ms', sa.Integer(), nullable=True))
    op.add_column('failover_test_events',
        sa.Column('original_ssh_host', sa.String(100), nullable=True))
    op.add_column('failover_test_events',
        sa.Column('original_ssh_port', sa.Integer(), nullable=True))
    op.add_column('failover_test_events',
        sa.Column('snapshot_type', sa.String(20), nullable=True))
    op.add_column('failover_test_events',
        sa.Column('base_snapshot_id', sa.String(200), nullable=True))
    op.add_column('failover_test_events',
        sa.Column('files_changed', sa.Integer(), nullable=True))
```

---

## 📊 Checklist Geral de Progresso

### Fase 1: Fixes Críticos (P0) ✅ COMPLETA
- [x] 1.1 Clock Sync na Restauração ⏱️ 15min ✅
- [x] 1.2 Credenciais B2 do .env ⏱️ 20min ✅
- [x] 1.3 s5cmd instalado localmente ⏱️ 10min ✅

**Total Fase 1:** ~45 minutos ✅

---

### Fase 2: Performance (P1)
- [x] 2.1 Snapshot Metadata Persistence ⏱️ 30min ✅
- [x] 2.2 Rate Limiting Vast.ai ⏱️ 25min ✅
- [x] 2.3 Timeout Otimizado ⏱️ 15min ✅

**Total Fase 2:** ~70 minutos ✅

---

### Fase 3: Qualidade (P2)
- [x] 3.1 Periodic Snapshots Integrado ⏱️ 40min ✅
- [x] 3.2 Restore menos verboso ⏱️ 10min ✅
- [x] 3.3 Validação Pós-Restore ⏱️ 30min ✅
- [x] 3.4 Métricas Completas no PostgreSQL ⏱️ 25min ✅

**Total Fase 3:** ~105 minutos ✅

---

## 🎯 Tempo Total Estimado: ~3h 40min

## 📈 MTTR Esperado Após Implementação

| Fase | MTTR Estimado | Melhoria |
|------|---------------|----------|
| Antes | 107.9s | - |
| Após P0 | 107.9s | 0% (fix blockers) |
| Após P1 | 73-88s | **19-32%** ⚡ |
| Após P2 | 68-83s | **23-37%** ⚡⚡ |

---

## 🧪 Plano de Testes

### Após cada fase, executar:

1. **Teste de Snapshot**
   - Criar base snapshot
   - Modificar 2-3 arquivos
   - Criar snapshot incremental
   - Verificar: só arquivos modificados no incremental

2. **Teste de Failover Completo**
   - Provisionar GPU
   - Criar arquivos de teste
   - Executar failover
   - Verificar: MTTR, inferência OK, dados restaurados

3. **Teste de Rate Limiting**
   - Executar 3 failovers consecutivos
   - Verificar: máximo 1-2 erros 429 por teste

4. **Teste de Métricas**
   - Query PostgreSQL após failover
   - Verificar: todos campos populados corretamente

---

## 📝 Notas de Implementação

- Commitar após cada item completado
- Testar individualmente antes de ir para o próximo
- Se bloqueado em algum item, documentar e pular para próximo
- Manter log de tempos reais vs estimados

---

## ✅ Correções Pós-Implementação

### Fix: Timeout do s5cmd (2025-12-20)
**Problema:** `_find_latest_base_snapshot()` tinha timeout de 10s, insuficiente para listar buckets B2 grandes
**Solução:** Aumentado de 10s → 60s em `src/services/standby/failover.py:516`
**Status:** ✅ Corrigido

**Arquivo:** `src/services/standby/failover.py` linha 516
**Commit:** Próximo commit

---

**Última atualização:** 2025-12-20
**Responsável:** Claude + Marcos
**Status:** ✅ Implementação completa - 10/10 otimizações funcionais
