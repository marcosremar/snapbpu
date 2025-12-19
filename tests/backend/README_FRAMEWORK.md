# Framework de Testes Backend - Dumont Cloud

Este documento descreve o framework de testes backend criado para o sistema Dumont Cloud, com organização por módulos, cache inteligente e estrutura reutilizável.

## 🏗️ Estrutura de Diretórios

```
tests/backend/
├── conftest.py                    # Framework base e configurações
├── auth/
│   └── test_login.py            # Testes de autenticação
├── instances/
│   └── test_gpu_instances.py     # Testes de instâncias GPU
├── hibernation/
│   └── test_auto_hibernation.py # Testes de auto-hibernação
├── snapshots/
│   └── test_snapshots.py        # Testes de snapshots
├── migration/
│   └── test_migration.py        # Testes de migração
├── ai_wizard/
│   └── test_ai_wizard.py       # Testes de AI Wizard
├── metrics/
│   └── test_metrics.py          # Testes de métricas
├── sync/
│   └── test_sync.py             # Testes de sincronização
├── standby/
│   └── test_standby.py         # Testes de CPU Standby
├── regions/
│   └── test_regions.py          # Testes de mapeamento
├── dashboard/
│   └── test_dashboard.py       # Testes de dashboard
├── telemetry/
│   └── test_telemetry.py        # Testes de telemetria
├── alerts/
│   └── test_alerts.py          # Testes de alertas
└── e2e/
    └── test_e2e_complete.py    # Testes end-to-end
```

## 🔧 Framework Base (conftest.py)

### Características Principais

1. **Cache Inteligente**
   - Baseado em hash SHA256 do arquivo de teste
   - Evita re-execução se o arquivo não mudou
   - Cache expira em 24 horas
   - Configurável via variável de ambiente `TEST_CACHE`

2. **APIClient Reutilizável**
   - Autenticação automática JWT
   - Retry com exponential backoff
   - Timeout configurável
   - Headers padrão

3. **BaseTestCase**
   - Classe base com métodos utilitários
   - Logging estruturado com cores
   - Assertions personalizadas
   - Setup/teardown automático

4. **Fixtures Globais**
   - `api_client`: Client autenticado
   - `unauth_client`: Client sem autenticação
   - `sample_instance_data`: Dados de teste para instâncias
   - `sample_snapshot_data`: Dados de teste para snapshots

### Configurações

```bash
# Variáveis de ambiente
export TEST_BASE_URL="http://localhost:8766"
export TEST_USER="test@example.com"
export TEST_PASS="test123"
export TEST_TIMEOUT="30"
export TEST_RETRY="3"
export TEST_CACHE="true"  # Habilita cache inteligente
```

## 🚀 Como Usar

### Executar Todos os Testes
```bash
# Com cache habilitado (padrão)
pytest tests/backend/ -v

# Sem cache (sempre executa)
TEST_CACHE=false pytest tests/backend/ -v

# Apenas testes de um módulo
pytest tests/backend/auth/ -v

# Apenas testes específicos
pytest tests/backend/auth/test_login.py -v -k "test_login"
```

### Executar com Filtros
```bash
# Apenas testes de autenticação
pytest tests/backend/ -v -k "auth"

# Apenas testes de performance
pytest tests/backend/ -v -k "performance"

# Pular testes lentos
pytest tests/backend/ -v -k "not slow"
```

### Parallelização
```bash
# Executar em paralelo (4 processos)
pytest tests/backend/ -v -n 4

# Distribuir por diretório
pytest tests/backend/ -v --dist=loadscope
```

## 📊 Cache Inteligente

### Como Funciona

1. **Hash do Arquivo**: Calcula SHA256 do arquivo de teste
2. **Chave de Cache**: Combina hash do arquivo + parâmetros
3. **Verificação**: Verifica se resultado existe em cache
4. **Pulamento**: Se cache existe, pula o teste
5. **Armazenamento**: Salva resultado após execução

### Estrutura do Cache
```
tests/backend/.test_cache/
├── test_login_hash1_params1.json
├── test_instances_hash2_params2.json
└── ...
```

### Benefícios

- **Velocidade**: Testes não mudados pulam execução
- **Consistência**: Resultados reproducíveis
- **Economia**: Menos carga nos sistemas externos
- **Desenvolvimento**: Feedback mais rápido

## 🎯 Padrões de Teste

### Estrutura de uma Classe de Teste
```python
class TestModuleName(BaseTestCase):
    """Descrição dos testes deste módulo"""
    
    def test_functionality_positive(self, api_client):
        """Teste positivo da funcionalidade"""
        # Preparar dados
        test_data = {...}
        
        # Executar request
        resp = api_client.post("/api/v1/endpoint", json=test_data)
        
        # Validar resposta
        self.assert_success_response(resp, "Descrição do sucesso")
        data = resp.json()
        
        # Validar estrutura
        required_keys = ["key1", "key2"]
        self.assert_json_keys(data, required_keys)
        
        # Validar valores
        assert data["key1"] == expected_value
        
        self.log_success("Mensagem de sucesso específica")
    
    def test_functionality_negative(self, api_client):
        """Teste negativo da funcionalidade"""
        # Preparar dados inválidos
        invalid_data = {...}
        
        # Executar request
        resp = api_client.post("/api/v1/endpoint", json=invalid_data)
        
        # Validar erro
        assert resp.status_code in [400, 422]
        
        self.log_success("Validação funcionou")
```

### Padrões de Assert

```python
# Sucesso genérico
self.assert_success_response(resp, "Descrição")

# Validação de JSON
self.assert_json_keys(data, ["required", "keys"])

# Logs específicos
self.log_success("Mensagem de sucesso")
self.log_warning("Mensagem de aviso")
self.log_fail("Mensagem de falha")
self.log_info("Mensagem informativa")
```

## 🔍 Tipos de Teste Implementados

### 1. Testes Funcionais
- Validação de endpoints
- Fluxos completos de negócio
- Comportamento esperado

### 2. Testes de Validação
- Campos obrigatórios
- Tipos de dados inválidos
- Valores fora de range

### 3. Testes de Segurança
- Input malicioso
- SQL Injection
- XSS
- Rate limiting

### 4. Testes de Performance
- Tempo de resposta
- Requisições concorrentes
- Load testing básico

### 5. Testes de Integração
- Múltiplos endpoints juntos
- Fluxos complexos
- Dependencies entre sistemas

## 📈 Relatórios e Resultados

### Saída Padrão
```
✓ Login OK: token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
✓ Token válido: user=test@example.com
✓ Token refresh: novo token gerado e válido
⚠ Instância não encontrada para pausa
✓ Multi-status: 0/3 encontradas
```

### Cache Status
```
Dumont Cloud Backend Tests
Cache: ENABLED
Base URL: http://localhost:8766
============================================================

✓ Login OK: token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
✓ Teste em cache: test_login_success (pulado)
✓ Token válido: user=test@example.com
```

### Resultados Finais
```
============================================================
Testes Finalizados
Exit status: 0
============================================================
```

## 🛠️ Extensão do Framework

### Adicionar Novo Módulo

1. Criar diretório: `tests/backend/novo_modulo/`
2. Criar arquivo: `tests/backend/novo_modulo/test_novo.py`
3. Herdar de `BaseTestCase`
4. Seguir padrões estabelecidos

### Adicionar Novo Fixture
```python
@pytest.fixture(scope="function")
def novo_dado_teste():
    """Descrição do fixture"""
    return {
        "campo1": "valor1",
        "campo2": "valor2"
    }
```

### Adicionar Novo Teste de Performance
```python
def test_performance_endpoint(self, api_client):
    """Testa performance do endpoint"""
    start_time = time.time()
    resp = api_client.get("/api/v1/endpoint")
    request_time = time.time() - start_time
    
    self.assert_success_response(resp, "Performance test")
    assert request_time < 2.0, f"Request muito lento: {request_time:.2f}s"
    
    self.log_success(f"Performance: {request_time:.2f}s")
```

## 🚨 Boas Práticas

### 1. Nomenclatura
- Classes: `TestModuleName`
- Métodos: `test_functionality_scenario`
- Descrições claras e específicas

### 2. Estrutura
- Setup/teardown automáticos
- Dados de teste em fixtures
- Validações explícitas

### 3. Mensagens
- Sempre em português
- Descritivas e claras
- Incluir contexto quando relevante

### 4. Cache
- Testes idempotentes devem usar cache
- Testes com side effects devem desabilitar cache
- Documentar comportamento esperado

### 5. Performance
- Testes rápidos priorizados
- Testes lentos marcados com `@pytest.mark.slow`
- Timeout apropriado para cada tipo de teste

## 🔮 Próximos Passos

1. **Completar módulos restantes**: snapshots, migration, ai_wizard, etc.
2. **Integração CI/CD**: GitHub Actions com cache
3. **Coverage**: Relatório de cobertura de código
4. **Performance**: Benchmarking automatizado
5. **Mocking**: Isolar dependências externas

Este framework fornece uma base sólida para testes backend do Dumont Cloud, com foco em produtividade, confiabilidade e mantenabilidade.
