# 🚀 Dumont Cloud CLI - Natural Commands

CLI integrado ao sistema com **comandos naturais em inglês** - funciona de qualquer lugar como o `claude` do Claude Code!

## ⚡ Instalação Rápida

```bash
cd /home/marcos/dumontcloud
./install-cli.sh
./setup-cli-shortcuts.sh
source ~/.bashrc
```

## 🎯 Filosofia

**Comandos naturais** ao invés de `call POST /api/...`:

```bash
# ❌ Antigo (genérico)
dumont call POST /api/instances/create --data '{"gpu_name":"rtx4090"}'

# ✅ Novo (natural)
dumont instance create wizard rtx4090
```

## 📖 Comandos Disponíveis

### 🔐 Authentication

```bash
# Login
dumont auth login user@email.com password
dmlogin user@email.com password  # alias

# Check authentication
dumont auth me
dmme  # alias

# Logout
dumont auth logout
```

### 💻 Instances (GPU Management)

```bash
# List all instances
dumont instance list
dmls  # alias

# Create with AI Wizard
dumont instance create wizard rtx4090
dmcreate wizard rtx4090  # alias

# Create manually
dumont instance create rtx4090
dumont instance create rtx4090 num_gpus=2
dumont instance create 'a100 80gb' num_gpus=4 disk_space=500

# Get instance details
dumont instance get 12345
dmget 12345  # alias

# Control instances
dumont instance pause 12345
dumont instance resume 12345
dumont instance wake 12345

# Delete instance
dumont instance delete 12345
dmrm 12345  # alias

# Migration
dumont instance migrate 12345
```

### 💾 Snapshots

```bash
# List snapshots
dumont snapshot list
dmsnap  # alias

# Create snapshot
dumont snapshot create backup-name instance_id=12345
dmsnap-create backup-name  # alias

# Restore snapshot
dumont snapshot restore snapshot_id=abc123 instance_id=12345
```

### ⚙️ Settings

```bash
# View settings
dumont setting list
dmconfig  # alias

# Update settings
dumont setting update vast_api_key=YOUR_KEY
dumont setting update r2_bucket=mybucket
```

### 📊 Metrics & Monitoring

```bash
# Dashboard metrics
dumont metric dashboard

# Cost metrics
dumont metric cost
```

### 🤖 AI Features

```bash
# AI Wizard analysis
dumont ai-wizard analyze

# Get GPU recommendations
dumont advisor recommend
```

### 💰 Savings Calculator

```bash
# Calculate savings
dumont saving calculate
```

## 🔥 Quick Shortcuts

Depois de `source ~/.bashrc`:

| Comando | Descrição |
|---------|-----------|
| `dm` | Alias para `dumont` |
| `dmlogin user pass` | Login rápido |
| `dmme` | Verificar autenticação |
| `dmls` | Listar instâncias |
| `dmcreate wizard rtx4090` | Criar com wizard |
| `dmget 12345` | Ver detalhes |
| `dmrm 12345` | Deletar instância |
| `dmsnap` | Listar snapshots |

## 💡 Exemplos Práticos

### Workflow Completo

```bash
# 1. Login
dmlogin marcosremar@gmail.com senha123

# 2. Verificar autenticação
dmme

# 3. Listar instâncias
dmls

# 4. Criar nova instância com wizard
dmcreate wizard rtx4090

# 5. Ver detalhes
dmget 12345

# 6. Criar snapshot
dumont snapshot create backup-antes-deploy instance_id=12345

# 7. Listar snapshots
dmsnap

# 8. Pausar instância
dumont instance pause 12345

# 9. Resumir instância
dumont instance resume 12345
```

### Criar Instância com Parâmetros

```bash
# Simples
dumont instance create rtx4090

# Com múltiplas GPUs
dumont instance create rtx4090 num_gpus=4

# Com configuração completa
dumont instance create 'a100 80gb' num_gpus=2 disk_space=1000 cpu_ram=128

# Com wizard (IA ajuda a configurar)
dumont instance create wizard rtx4090
```

### Gerenciar Snapshots

```bash
# Criar backup
dumont snapshot create pre-deployment instance_id=12345

# Listar todos
dumont snapshot list

# Restaurar
dumont snapshot restore snapshot_id=snap_abc123 instance_id=12345
```

## ✨ Características

✅ **Comandos Naturais** - Sintaxe intuitiva em inglês  
✅ **Global** - Funciona de qualquer diretório  
✅ **100% Automático** - Descobre APIs via OpenAPI  
✅ **Smart Auth** - Token salvo automaticamente  
✅ **Wizard Support** - Use `wizard` para assistência IA  
✅ **Key=Value** - Parâmetros flexíveis  
✅ **Aliases** - Atalhos curtos para comandos comuns  

## 🔄 Como Funciona

1. **Auto-descoberta**: CLI lê OpenAPI schema do FastAPI
2. **Mapeamento Inteligente**: Converte endpoints em comandos naturais
   - `/api/instances` → `instance list`
   - `/api/instances/{id}` → `instance get <id>`
   - `/api/auth/login` → `auth login`
3. **Execução**: Chama a API correspondente automaticamente
4. **Response**: Mostra JSON formatado e bonito

## 🆕 Adicionar Nova API

**ZERO trabalho!** Apenas adicione no FastAPI:

```python
@router.post("/api/deployments/create")
async def create_deployment(data: DeploymentCreate):
    return {"deployment_id": "123"}
```

O CLI descobre automaticamente:
```bash
dumont deployment create  # Funciona automaticamente!
```

## 📚 Comparação: Antes vs Depois

### ❌ Antes (genérico)
```bash
dumont call POST /api/auth/login --data '{"username":"user","password":"pass"}'
dumont call GET /api/instances
dumont call POST /api/instances/create --data '{"gpu_name":"rtx4090","num_gpus":2}'
dumont call GET /api/instances/12345
dumont call DELETE /api/instances/12345
```

### ✅ Depois (natural)
```bash
dumont auth login user pass
dumont instance list
dumont instance create rtx4090 num_gpus=2
dumont instance get 12345
dumont instance delete 12345
```

## 🎓 Tips & Tricks

### 1. Use Wizard para Criação Inteligente
```bash
dumont instance create wizard rtx4090
# IA vai sugerir configurações otimizadas
```

### 2. Sintaxe Key=Value Flexível
```bash
dumont instance create rtx4090 num_gpus=2 disk_space=500 cpu_ram=64
```

### 3. Aliases para Velocidade
```bash
# Ao invés de digitar tudo:
dumont instance list

# Use o alias:
dmls
```

### 4. Funciona de Qualquer Lugar
```bash
cd /tmp
cd ~/Projects/outro-projeto
cd /

# Todos funcionam:
dumont instance list
dmls
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
cd /home/marcos/dumontcloud
./setup-cli-shortcuts.sh
source ~/.bashrc
```

### Ver quais comandos estão disponíveis
```bash
# Os comandos são descobertos automaticamente do OpenAPI
# Para testar:
dumont -h
dumont instance -h
```

## 📖 Documentação Adicional

- **Guia Rápido**: `./cli-help.sh`
- **Demo**: `./demo-natural-cli.sh`
- **Instalação**: `./install-cli.sh --help`

## 🌟 Comparação com Outras CLIs

| Feature | AWS CLI | gcloud CLI | Dumont CLI |
|---------|---------|------------|------------|
| Comandos naturais | ✅ | ✅ | ✅ |
| Auto-descoberta | ❌ | ❌ | ✅ (via OpenAPI) |
| Funciona globalmente | ✅ | ✅ | ✅ |
| Wizard integrado | ❌ | ❌ | ✅ |
| Zero configuração | ❌ | ❌ | ✅ |

---

**Desenvolvido com ❤️ para Dumont Cloud**  
Comandos naturais + Auto-descoberta = CLI perfeito! 🚀
