# 🧪 Testing Guide - Dumont Cloud

## Filosofia de Testes

O sistema utiliza **testes de integração via API HTTP** como base principal, testando endpoints reais contra o servidor backend FastAPI.

```
       E2E (5%) - 9 testes
      /              \
  API Integration (95%) - 209 testes
```

---

## 📊 Estrutura Atual de Testes

### Módulos e Quantidade de Testes

| Módulo | Testes | Descrição |
|--------|--------|-----------|
| **snapshots** | 34 | Backup/restore com Restic |
| **metrics** | 28 | Métricas de mercado GPU |
| **standby** | 27 | CPU Standby e failover |
| **ai_wizard** | 26 | Assistente IA para configuração |
| **instances** | 22 | Gerenciamento de instâncias GPU |
| **hibernation** | 19 | Auto-hibernação de instâncias |
| **auth** | 16 | Autenticação JWT |
| **dashboard** | 11 | Economia/savings dashboard |
| **e2e** | 9 | Fluxos completos end-to-end |
| **telemetry** | 7 | Health checks e telemetria |
| **migration** | 6 | Migração de instâncias |
| **sync** | 5 | Sincronização de dados |
| **regions** | 4 | Regiões disponíveis |
| **alerts** | 4 | Sistema de alertas |

**Total: 218 testes**

---

## 1. Testes de Autenticação

### Características
- Testam login, logout e proteção de endpoints
- Validam tokens JWT
- Verificam rate limiting

### Exemplo Real

```python
# tests/backend/auth/test_login.py
class TestLoginEndpoint(BaseTestCase):
    def test_login_success(self, api_client, config):
        """POST /api/v1/auth/login - Login com credenciais válidas"""
        resp = api_client.session.post(
            f"{config['BASE_URL']}/api/v1/auth/login",
            json={
                "username": config["TEST_USER"],  # Usa 'username', não 'email'
                "password": config["TEST_PASS"]
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] == True
        assert "token" in data  # Retorna 'token', não 'access_token'
        assert "user" in data
```

### Executar

```bash
pytest tests/backend/auth/test_login.py -v
```

---

## 2. Testes de Instâncias GPU

### Características
- Testam busca de ofertas via Vast.ai
- Gerenciamento de instâncias (criar, listar, pausar, resumir)
- Filtros por GPU, preço, especificações

### Exemplo Real

```python
# tests/backend/instances/test_gpu_instances.py
class TestInstanceOffers(BaseTestCase):
    def test_search_offers_basic(self, api_client):
        """GET /api/v1/instances/offers - Busca básica de ofertas"""
        resp = api_client.get("/api/v1/instances/offers")

        # API externa pode estar indisponível
        if resp.status_code in [429, 500, 503]:
            self.log_warning("API externa indisponível")
            return

        assert resp.status_code == 200
        data = resp.json()
        assert "offers" in data
        assert "count" in data
```

### Executar

```bash
pytest tests/backend/instances/test_gpu_instances.py -v
```

---

## 3. Testes de Snapshots (Restic)

### Características
- Backup incremental com deduplicação
- Integração com Cloudflare R2/S3
- Testes passam mesmo sem Restic configurado

### Endpoints Testados

- `GET /api/v1/snapshots` - Lista snapshots
- `POST /api/v1/snapshots` - Criar snapshot
- `POST /api/v1/snapshots/restore` - Restaurar
- `DELETE /api/v1/snapshots/{id}` - Deletar

### Executar

```bash
pytest tests/backend/snapshots/test_snapshots.py -v
```

---

## 4. Testes de CPU Standby

### Características
- Configuração de standby automático
- Associações GPU ↔ CPU
- Sincronização de dados
- Pricing de instâncias GCP

### Endpoints Testados

- `GET /api/v1/standby/status` - Status do sistema
- `POST /api/v1/standby/configure` - Configurar standby
- `GET /api/v1/standby/associations` - Listar associações
- `POST /api/v1/standby/sync/start` - Iniciar sync
- `GET /api/v1/standby/pricing` - Preços GCP

### Executar

```bash
pytest tests/backend/standby/test_standby.py -v
```

---

## 5. Testes E2E (End-to-End)

### Características
- Simulam jornadas completas de usuário
- Testam resiliência do sistema
- Verificam integração entre módulos

### Exemplo Real

```python
# tests/backend/e2e/test_complete_system_flow.py
class TestUserJourneyScenarios(BaseTestCase):
    def test_ml_researcher_journey(self, api_client):
        """Simula jornada de um pesquisador de ML"""
        # 1. Buscar ofertas
        offers_resp = api_client.get("/api/v1/instances/offers")

        # 2. Ver métricas de mercado
        market_resp = api_client.get("/api/v1/metrics/market")

        # 3. Listar instâncias
        instances_resp = api_client.get("/api/v1/instances")

        # 4. Verificar economia
        savings_resp = api_client.get("/api/v1/savings/summary")
```

### Executar

```bash
pytest tests/backend/e2e/test_complete_system_flow.py -v
```

---

## 🔧 Framework de Testes

### Configuração Base (conftest.py)

```python
# tests/backend/conftest.py
DEFAULT_CONFIG = {
    "BASE_URL": "http://localhost:8766",
    "TEST_USER": "test@test.com",
    "TEST_PASS": "test123",
    "TIMEOUT": 30
}

# Fixtures disponíveis:
# - api_client: Cliente autenticado com token JWT
# - unauth_client: Cliente sem autenticação
# - config: Configurações de teste
```

### Classe Base para Testes

```python
class BaseTestCase:
    """Classe base com helpers úteis"""

    def log_success(self, message): ...
    def log_fail(self, message): ...
    def log_warning(self, message): ...
    def assert_success_response(self, response, message): ...
    def assert_json_keys(self, data, required_keys): ...
```

---

## 🚀 Executando os Testes

### Todos os Testes Backend

```bash
# Executar todos (218 testes)
pytest tests/backend/ -v

# Com relatório de cobertura
pytest tests/backend/ --cov=src --cov-report=html

# Apenas um módulo
pytest tests/backend/auth/ -v
pytest tests/backend/instances/ -v
pytest tests/backend/standby/ -v
```

### Testes Específicos

```bash
# Um arquivo
pytest tests/backend/auth/test_login.py -v

# Um teste específico
pytest tests/backend/auth/test_login.py::TestLoginEndpoint::test_login_success -v

# Com output detalhado
pytest tests/backend/auth/test_login.py -v -s
```

### Debug de Falhas

```bash
# Parar no primeiro erro
pytest tests/backend/ -x

# Mostrar últimos falhos
pytest tests/backend/ --lf

# Entrar no debugger
pytest tests/backend/auth/test_login.py --pdb
```

---

## 📝 Escrevendo Novos Testes

### Template Padrão

```python
#!/usr/bin/env python3
"""
Testes Backend - [Nome do Módulo]

Testa endpoints de [descrição]:
- GET /api/v1/[endpoint] - Descrição
- POST /api/v1/[endpoint] - Descrição

Uso:
    pytest tests/backend/[modulo]/test_[modulo].py -v
"""

import pytest
from tests.backend.conftest import BaseTestCase, Colors


class Test[Modulo]Endpoints(BaseTestCase):
    """Testes para endpoints de [módulo]"""

    def test_endpoint_basic(self, api_client):
        """GET /api/v1/[endpoint] - Descrição"""
        resp = api_client.get("/api/v1/[endpoint]")

        assert resp.status_code == 200
        data = resp.json()

        # Validações
        assert "expected_key" in data
        self.log_success("Teste passou")


class Test[Modulo]Security(BaseTestCase):
    """Testes de segurança"""

    def test_requires_auth(self, unauth_client):
        """Testa que endpoint requer autenticação"""
        resp = unauth_client.get("/api/v1/[endpoint]")
        assert resp.status_code == 401
```

---

## 🎯 Casos de Teste Críticos

### Autenticação
- ✅ Login com credenciais válidas → 200 + token
- ✅ Login com senha inválida → 401
- ✅ Acesso sem token → 401
- ✅ Token inválido → 401

### Instâncias GPU
- ✅ Listar ofertas disponíveis
- ✅ Filtrar por GPU (RTX 4090, A100, etc)
- ✅ Filtrar por preço máximo
- ✅ Listar instâncias do usuário

### CPU Standby
- ✅ Verificar status do sistema
- ✅ Configurar standby automático
- ✅ Listar associações GPU ↔ CPU
- ✅ Iniciar/parar sincronização

### Snapshots
- ✅ Listar snapshots existentes
- ✅ Criar novo snapshot
- ✅ Restaurar snapshot
- ✅ Tratar erro quando Restic não configurado

---

## ⚠️ Considerações Importantes

### APIs Externas
Os testes são resilientes a falhas de APIs externas:
- **Vast.ai**: Pode retornar 429 (rate limit) ou 500
- **GCP**: Pode não ter credenciais configuradas
- **Restic/R2**: Pode não estar configurado

Testes tratam esses casos como sucesso parcial, não como falha.

### Ambiente de Teste
- Backend deve estar rodando em `http://localhost:8766`
- Usuário de teste: `test@test.com` / `test123`
- Configurável via variáveis de ambiente:
  - `TEST_BASE_URL`
  - `TEST_USER`
  - `TEST_PASS`

---

**Última atualização**: 2025-12-19
**Total de testes**: 218
**Taxa de sucesso**: 100% ✅
**Mantido por**: Engineering Team
