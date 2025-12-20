# 🚀 Dumont Cloud CLI - Sistema Integrado

CLI automático **integrado ao sistema** para o Dumont Cloud - funciona de qualquer lugar como o `claude` do Claude Code!

## ⚡ Instalação

```bash
# 1. Instalar o CLI globalmente
cd /home/marcos/dumontcloud
./install-cli.sh

# 2. Configurar atalhos (opcional mas recomendado)
./setup-cli-shortcuts.sh

# 3. Ativar no terminal atual
source ~/.bashrc

# Pronto! Use de qualquer lugar
dumont list
```

## 🎯 Uso Básico

### Comando Principal: `dumont`

Funciona de **qualquer diretório** do sistema:

```bash
# De qualquer lugar
dumont list                    # Lista todos os endpoints
dumont call GET /health        # Chama uma API
dumont interactive             # Modo interativo
```

### Atalhos Rápidos

Depois de configurar os shortcuts:

```bash
dm                  # = dumont (atalho curto)
dml                 # = dumont list
dmc GET /health     # = dumont call GET /health
dmi                 # = dumont interactive

# Atalhos específicos
dmh                 # Health check
dmauth              # Verificar autenticação
dminstances         # Listar instâncias
dmsnapshots         # Listar snapshots
dmsettings          # Ver configurações

# Função de login rápido
dmlogin user@email.com senha123
```

## 📖 Comandos Disponíveis

### 1. Listar Endpoints
```bash
dumont list
# ou
dml
```

Mostra **todos** os endpoints do sistema automaticamente.

### 2. Chamar APIs
```bash
dumont call <METHOD> <PATH> [--data JSON] [--token TOKEN]
# ou
dmc <METHOD> <PATH> [--data JSON]
```

**Exemplos:**

```bash
# Health check
dumont call GET /health
dmh  # atalho

# Login
dumont call POST /api/auth/login --data '{"username":"user@email.com","password":"senha"}'
dmlogin user@email.com senha  # atalho

# Verificar autenticação
dumont call GET /api/auth/me
dmauth  # atalho

# Listar instâncias
dumont call GET /api/instances
dminstances  # atalho

# Criar instância
dumont call POST /api/instances --data '{
  "gpu_name": "RTX 4090",
  "num_gpus": 2,
  "docker_image": "pytorch/pytorch"
}'

# Buscar ofertas
dumont call GET /api/instances/offers --param gpu_name='RTX 4090'

# Listar snapshots
dumont call GET /api/snapshots
dmsnapshots  # atalho

# Ver configurações
dumont call GET /api/settings
dmsettings  # atalho
```

### 3. Modo Interativo
```bash
dumont interactive
# ou
dmi
```

Modo REPL para testes rápidos:
```
> list
> GET /health
> POST /api/auth/login {"username":"user@email.com","password":"senha"}
> GET /api/instances
> exit
```

## 🔐 Autenticação Automática

O CLI gerencia JWT tokens automaticamente:

```bash
# 1. Login (salva token automaticamente)
dmlogin user@email.com senha123

# 2. Todas as chamadas usam o token salvo
dminstances
dmsnapshots
dmsettings
```

## ✨ Características

✅ **Global** - Funciona de qualquer diretório  
✅ **100% Automático** - Descobre APIs via OpenAPI  
✅ **Zero Configuração** - Novas APIs aparecem automaticamente  
✅ **Smart Auth** - Gerencia tokens JWT automaticamente  
✅ **Atalhos Inteligentes** - Comandos curtos para operações comuns  
✅ **Pretty Output** - JSON formatado, cores, ícones  

## 🔄 Workflow Completo

```bash
# De qualquer lugar no sistema
cd ~/Projects/meu-projeto

# Ver endpoints disponíveis
dml

# Login
dmlogin marcosremar@gmail.com 123456

# Verificar autenticação
dmauth

# Listar instâncias
dminstances

# Ver detalhes
dumont call GET /api/instances/12345

# Criar nova instância
dumont call POST /api/instances --data '{
  "gpu_name": "RTX 4090",
  "num_gpus": 1
}'

# Listar snapshots
dmsnapshots

# Health check
dmh
```

## 🆕 Adicionar Nova API

**Você não precisa fazer NADA no CLI!**

1. Adicione rota no FastAPI:
```python
@router.get("/api/minha-api")
async def minha_api():
    return {"data": "hello"}
```

2. A API aparece automaticamente:
```bash
dml  # Sua nova API aparece aqui!
dumont call GET /api/minha-api
```

## 🛠️ Comandos de Desenvolvimento

```bash
# Reinstalar CLI (se atualizar o código)
cd /home/marcos/dumontcloud
./install-cli.sh

# Adicionar novos atalhos
./setup-cli-shortcuts.sh
```

## 📚 Estrutura

```
/home/marcos/dumontcloud/
├── cli.py                      # CLI principal
├── install-cli.sh              # Instalador global
├── setup-cli-shortcuts.sh      # Configurar atalhos
└── CLI_SYSTEM.md              # Esta documentação

/home/marcos/.local/bin/
└── dumont                      # Comando global

~/.bashrc
└── [aliases do dumont]        # dm, dml, dmc, etc
```

## 🎓 Tips Avançados

### Mudar Base URL
```bash
dumont --base-url http://production.com:8000 list
```

### Usar Token Específico
```bash
dumont call GET /api/instances --token YOUR_JWT_TOKEN
```

### Modo Debug
O CLI já mostra automaticamente:
- Request body formatado
- Response time
- Status code
- Response body formatado

### Integração com Scripts

```bash
#!/bin/bash
# Seu script pode usar o CLI

# Fazer login
dmlogin user@email.com senha

# Criar instância e capturar resposta
RESPONSE=$(dumont call POST /api/instances --data '{"gpu_name":"RTX 4090"}')

# Processar resposta
echo "$RESPONSE" | jq .
```

## 🐛 Troubleshooting

### Comando não encontrado
```bash
# Adicionar ao PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Aliases não funcionam
```bash
# Reconfigurar
cd /home/marcos/dumontcloud
./setup-cli-shortcuts.sh
source ~/.bashrc
```

### API não aparece no list
```bash
# Verificar se backend está rodando
dmh

# Verificar OpenAPI schema
curl http://localhost:8767/api/v1/openapi.json
```

## 🌟 Comparação com Claude Code

| Recurso | Claude Code | Dumont CLI |
|---------|-------------|------------|
| Comando global | ✅ `claude` | ✅ `dumont` ou `dm` |
| Funciona de qualquer lugar | ✅ | ✅ |
| Auto-descoberta | ❌ | ✅ (via OpenAPI) |
| Atalhos personalizados | ❌ | ✅ |
| Autenticação automática | ✅ | ✅ |
| Modo interativo | ✅ | ✅ |

## 🚀 Próximos Passos

Agora você tem um CLI completo e integrado ao sistema:

1. Use `dumont` ou `dm` de qualquer lugar
2. Explore endpoints: `dml`
3. Faça login: `dmlogin user@email.com senha`
4. Teste suas APIs!

---

**Desenvolvido com ❤️ para Dumont Cloud**  
CLI inspirado no Claude Code, mas com super-poderes de auto-descoberta via OpenAPI!
