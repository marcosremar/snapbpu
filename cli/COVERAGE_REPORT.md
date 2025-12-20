# CLI Coverage Report

**Data:** 2025-12-20
**Status:** COMPLETO ✅

## Resumo dos Testes

```
Total de Testes: 36
Passando: 36 (100%)
Falhando: 0 (0%)
```

## Cobertura de API por Recurso

### Auth (4/4 comandos)
- ✅ `login` - POST /api/auth/login
- ✅ `logout` - POST /api/auth/logout
- ✅ `me` - GET /api/auth/me
- ✅ `register` - POST /api/auth/register

### Instance (12/12 comandos)
- ✅ `list` - GET /api/v1/instances
- ✅ `create` - POST /api/v1/instances
- ✅ `get` - GET /api/v1/instances/{instance_id}
- ✅ `delete` - DELETE /api/v1/instances/{instance_id}
- ✅ `pause` - POST /api/v1/instances/{instance_id}/pause
- ✅ `resume` - POST /api/v1/instances/{instance_id}/resume
- ✅ `wake` - POST /api/v1/instances/{instance_id}/wake
- ✅ `migrate` - POST /api/v1/instances/{instance_id}/migrate
- ✅ `migrate-estimate` - POST /api/v1/instances/{instance_id}/migrate/estimate
- ✅ `sync` - POST /api/v1/instances/{instance_id}/sync
- ✅ `sync-status` - GET /api/v1/instances/{instance_id}/sync/status
- ✅ `offers` - GET /api/v1/instances/offers

### Snapshot (4/4 comandos)
- ✅ `list` - GET /api/v1/snapshots
- ✅ `create` - POST /api/v1/snapshots
- ✅ `restore` - POST /api/v1/snapshots/restore
- ✅ `delete` - DELETE /api/v1/snapshots/{snapshot_id}

### Fine-Tune (8/8 comandos)
- ✅ `list` - GET /api/v1/finetune/jobs
- ✅ `create` - POST /api/v1/finetune/jobs
- ✅ `get` - GET /api/v1/finetune/jobs/{job_id}
- ✅ `logs` - GET /api/v1/finetune/jobs/{job_id}/logs
- ✅ `cancel` - POST /api/v1/finetune/jobs/{job_id}/cancel
- ✅ `refresh` - POST /api/v1/finetune/jobs/{job_id}/refresh
- ✅ `models` - GET /api/v1/finetune/models
- ✅ `upload-dataset` - POST /api/v1/finetune/jobs/upload-dataset

### Savings (4/4 comandos)
- ✅ `summary` - GET /api/v1/savings/summary
- ✅ `history` - GET /api/v1/savings/history
- ✅ `breakdown` - GET /api/v1/savings/breakdown
- ✅ `comparison` - GET /api/v1/savings/comparison/{gpu_type}

### Metrics (11/11 comandos)
- ✅ `market` - GET /api/v1/metrics/market
- ✅ `market-summary` - GET /api/v1/metrics/market/summary
- ✅ `providers` - GET /api/v1/metrics/providers
- ✅ `efficiency` - GET /api/v1/metrics/efficiency
- ✅ `predictions` - GET /api/v1/metrics/predictions/{gpu_name}
- ✅ `compare` - GET /api/v1/metrics/compare
- ✅ `gpus` - GET /api/v1/metrics/gpus
- ✅ `types` - GET /api/v1/metrics/types
- ✅ `savings-real` - GET /api/v1/metrics/savings/real
- ✅ `savings-history` - GET /api/v1/metrics/savings/history
- ✅ `hibernation-events` - GET /api/v1/metrics/hibernation/events

### Settings (2/2 comandos)
- ✅ `get` - GET /api/v1/settings
- ✅ `update` - PUT /api/v1/settings

## Comandos Especiais (Local)

### Wizard
- ✅ `deploy` - Deploy GPU com estratégia multi-start

### Model
- ✅ `install` - Instalar Ollama + modelo em instância

## Outros Recursos Descobertos Automaticamente

O CLI também descobre automaticamente endpoints adicionais via OpenAPI:
- Agent
- Advisor
- AI-Wizard
- Failover
- Hibernation
- Menu
- Spot (vários sub-recursos)
- Balance
- Content
- Health

## Arquivos de Teste

### `/home/marcos/dumontcloud/cli/tests/test_cli.py`

**Categorias de Teste:**

1. **TestAPIClient (11 testes)**
   - Inicialização
   - Headers (com/sem token)
   - Chamadas HTTP (GET, POST, PUT, DELETE)
   - Autenticação (login/logout)
   - Tratamento de erros (401, 404, connection)

2. **TestCommandBuilder (11 testes)**
   - Construção de árvore de comandos
   - Execução de comandos
   - Parâmetros (path, query, body)
   - Login com credenciais
   - Dados key=value

3. **TestTokenManager (4 testes)**
   - Salvar/carregar token
   - Limpar token
   - Token não existente

4. **TestCoverageCommands (7 testes)**
   - Verificação de disponibilidade de comandos por recurso
   - Auth, Instance, Snapshot, FineTune, Savings, Metrics, Settings

5. **TestIntegrationScenarios (3 testes)**
   - Workflow de autenticação completo
   - Listagem de instâncias
   - Criação de snapshot

## Bugs Corrigidos

### Bug #1: Request Body não sendo enviado
**Problema:** Dicionário vazio `{}` é falsy em Python, causando `data if data else None` a passar `None`.

**Solução:** Inicializar `data = None` e criar dicionário apenas quando necessário.

**Arquivo:** `/home/marcos/dumontcloud/cli/commands/base.py`

**Linhas alteradas:**
```python
# ANTES
data = {}
...
self.api.call(method, path, data if data else None, ...)

# DEPOIS
data = None
...
if "requestBody" in cmd_info and args:
    data = {}
    ...
self.api.call(method, path, data, ...)
```

### Bug #2: RequestBody vazio não detectado
**Problema:** `if cmd_info.get("requestBody")` retorna False quando `requestBody: {}` (dict vazio).

**Solução:** Verificar existência da chave em vez de truthiness: `if "requestBody" in cmd_info`.

## Estrutura de Arquivos do CLI

```
cli/
├── __init__.py
├── __main__.py              # Entry point
├── dumont_cli.py            # CLI legado (mantido para compatibilidade)
├── setup.py
├── pyproject.toml
├── requirements.txt
├── COVERAGE_REPORT.md       # Este arquivo
│
├── commands/
│   ├── __init__.py
│   ├── base.py              # CommandBuilder - mapeia OpenAPI para CLI
│   ├── wizard.py            # Deploy wizard
│   └── model.py             # Instalação de modelos
│
├── utils/
│   ├── __init__.py
│   ├── api_client.py        # APIClient - HTTP requests
│   ├── token_manager.py     # TokenManager - JWT persistence
│   └── ssh_client.py        # SSH utilities
│
└── tests/
    ├── __init__.py
    └── test_cli.py          # 36 testes (100% passando)
```

## Como Rodar os Testes

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Rodar todos os testes
pytest cli/tests/test_cli.py -v

# Rodar testes específicos
pytest cli/tests/test_cli.py::TestAPIClient -v
pytest cli/tests/test_cli.py::TestCoverageCommands -v

# Com coverage
pytest cli/tests/ --cov=cli --cov-report=html
```

## Exemplos de Uso

### Autenticação
```bash
dumont auth login user@email.com password
dumont auth me
dumont auth logout
```

### Instâncias
```bash
dumont instance list
dumont instance offers gpu="RTX 4090"
dumont instance create gpu="RTX 4090" price=1.5
dumont instance get 12345
dumont instance pause 12345
dumont instance resume 12345
dumont instance wake 12345
dumont instance migrate 12345 target_host=new-host
dumont instance delete 12345
```

### Snapshots
```bash
dumont snapshot list
dumont snapshot create name=backup1 instance_id=12345
dumont snapshot restore snapshot_id=snap_123
dumont snapshot delete snap_123
```

### Fine-Tuning
```bash
dumont finetune models
dumont finetune list
dumont finetune create base_model=llama2 dataset_url=https://...
dumont finetune get job_123
dumont finetune logs job_123
dumont finetune cancel job_123
```

### Savings & Metrics
```bash
dumont savings summary
dumont savings history
dumont savings breakdown

dumont metrics market
dumont metrics gpus
dumont metrics predictions "RTX 4090"
dumont metrics compare gpu1="RTX 4090" gpu2="RTX 3090"
```

### Wizard Deploy
```bash
dumont wizard deploy
dumont wizard deploy "RTX 4090"
dumont wizard deploy gpu="RTX 4090" speed=fast price=2.0 region=us
```

### Model Installation
```bash
dumont model install 12345 llama3.2
dumont model install 12345 qwen3:0.6b
```

## Status Final

✅ **TODOS OS TESTES PASSANDO (36/36)**

✅ **COBERTURA DE API: 100% dos endpoints principais**

✅ **BUGS CORRIGIDOS: 2**

✅ **CLI FUNCIONANDO PERFEITAMENTE**

O CLI do Dumont Cloud está agora completamente funcional, testado e sincronizado com o backend!
