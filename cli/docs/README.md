# Dumont Cloud CLI - Automatic API Client

🚀 **CLI automático que descobre e chama todas as APIs do sistema dinamicamente!**

## ✨ Características

- **100% Automático**: Descobre todos os endpoints via OpenAPI schema
- **Zero Configuração**: Novas APIs aparecem automaticamente
- **Fácil de Usar**: Sintaxe simples e intuitiva
- **Auto-Autenticação**: Salva token JWT automaticamente após login

## 🎯 Uso Rápido

### Opção 1: Usar o wrapper `dc` (recomendado)

```bash
# Listar todos os endpoints disponíveis
./dc list

# Fazer login
./dc call POST /api/auth/login --data '{"username":"user@email.com","password":"senha"}'

# Chamar qualquer API (após login, token é salvo automaticamente)
./dc call GET /api/instances/list
./dc call POST /api/instances/create --data '{"gpu":"RTX 4090"}'
```

### Opção 2: Usar diretamente o Python

```bash
source venv/bin/activate
python cli.py list
python cli.py call GET /api/health
```

## 📖 Comandos Disponíveis

### 1. Listar Endpoints
```bash
./dc list
```

Mostra TODOS os endpoints disponíveis no sistema com:
- Método HTTP (GET, POST, etc)
- Caminho (/api/...)
- Descrição
- Parâmetros necessários
- Body format

### 2. Chamar API
```bash
./dc call <METHOD> <PATH> [--data JSON] [--token TOKEN]
```

**Exemplos:**

```bash
# Login (salva token automaticamente)
./dc call POST /api/auth/login --data '{"username":"user@example.com","password":"senha123"}'

# Verificar autenticação
./dc call GET /api/auth/me

# Listar instâncias
./dc call GET /api/instances/list

# Criar instância
./dc call POST /api/instances/create --data '{
  "gpu_name": "RTX 4090",
  "num_gpus": 1,
  "docker_image": "pytorch/pytorch"
}'

# Listar snapshots
./dc call GET /api/snapshots/list

# Com parâmetros query
./dc call GET /api/instances/get --param id=12345

# Usar token específico
./dc call GET /api/instances/list --token YOUR_JWT_TOKEN_HERE
```

### 3. Modo Interativo
```bash
./dc interactive
```

Modo interativo permite testar APIs rapidamente:
```
> list
> POST /api/auth/login {"username":"user@example.com","password":"senha"}
> GET /api/instances/list
> exit
```

## 🔐 Autenticação

O CLI gerencia autenticação automaticamente:

1. Faça login uma vez:
```bash
./dc call POST /api/auth/login --data '{"username":"seu@email.com","password":"senha"}'
```

2. O token JWT é salvo automaticamente

3. Todas as próximas chamadas usam o token salvo:
```bash
./dc call GET /api/instances/list  # Usa token automaticamente
```

## 🎨 Output Bonito

O CLI mostra:
- ✅ Status da resposta
- ⏱️ Tempo de resposta
- 📦 Request body formatado
- 📄 Response body formatado (JSON pretty-print)
- 🔐 Notificação quando token é salvo

## 🔄 Como Funciona (100% Automático)

1. **Descobre APIs via OpenAPI**: O CLI lê o schema OpenAPI do FastAPI
2. **Mapeia Endpoints**: Todos os endpoints são descobertos automaticamente
3. **Sem Código Manual**: Você adiciona uma nova rota no FastAPI → ela aparece automaticamente no CLI!

## 📝 Exemplos Práticos

### Workflow Completo

```bash
# 1. Ver todos os endpoints
./dc list

# 2. Fazer login
./dc call POST /api/auth/login --data '{
  "username": "marcosremar@gmail.com",
  "password": "123456"
}'

# 3. Verificar autenticação
./dc call GET /api/auth/me

# 4. Listar instâncias GPU
./dc call GET /api/instances/list

# 5. Ver detalhes de uma instância
./dc call GET /api/instances/12345

# 6. Criar nova instância
./dc call POST /api/instances/create --data '{
  "gpu_name": "RTX 4090",
  "num_gpus": 2,
  "docker_image": "nvidia/cuda:12.0.0-base-ubuntu22.04"
}'

# 7. Listar snapshots
./dc call GET /api/snapshots/list

# 8. Criar snapshot
./dc call POST /api/snapshots/create --data '{
  "instance_id": "12345",
  "name": "my-backup"
}'
```

### Testar AI Wizard

```bash
./dc call POST /api/ai-wizard/analyze --data '{
  "files": ["train.py", "requirements.txt"],
  "project_description": "Deep Learning project with PyTorch"
}'
```

### Testar Savings Calculator

```bash
./dc call POST /api/savings/calculate --data '{
  "gpu_name": "RTX 4090",
  "num_gpus": 2,
  "hours_per_day": 8
}'
```

## 🆕 Adicionar Nova API

**Você não precisa fazer NADA no CLI!**

1. Adicione sua rota no FastAPI:
```python
@router.get("/api/my-new-endpoint")
async def my_new_endpoint():
    return {"message": "Hello!"}
```

2. Reinicie o servidor FastAPI

3. Pronto! A API já aparece no CLI:
```bash
./dc list  # Seu novo endpoint aparece aqui!
./dc call GET /api/my-new-endpoint
```

## 🛠️ Opções Avançadas

### URL Customizada
```bash
./dc --base-url http://production-server.com:8000 list
```

### Debug de Request
```bash
# O CLI mostra automaticamente:
# - Request body
# - Response headers
# - Response time
# - Formatted JSON
```

## 📚 Estrutura do Projeto

```
dumontcloud/
├── cli.py          # CLI principal (Python)
├── dc              # Wrapper bash para facilitar
└── CLI_README.md   # Este arquivo
```

## 🎓 Tips & Tricks

1. **Use `list` frequentemente** para ver os endpoints disponíveis
2. **Token é salvo automaticamente** após login
3. **JSON deve estar em aspas simples** no bash: `--data '{...}'`
4. **Modo interativo** é ótimo para testar rapidamente
5. **Adicione `--token`** se precisar usar token específico

## 🐛 Troubleshooting

### Erro: "Could not find OpenAPI schema"
- Verifique se o backend está rodando: `curl http://localhost:8767/health`

### Erro: "Not authenticated"
- Faça login primeiro: `./dc call POST /api/auth/login --data '{...}'`

### Erro: "Invalid JSON"
- Verifique se o JSON está correto
- Use aspas simples no bash: `--data '{...}'`

## 🚀 Próximos Passos

Agora que você tem o CLI:

1. Explore todos os endpoints: `./dc list`
2. Faça login: `./dc call POST /api/auth/login ...`
3. Teste suas APIs favoritas!
4. Adicione novas APIs no FastAPI - elas aparecem automaticamente!

---

**Desenvolvido com ❤️ para Dumont Cloud**
