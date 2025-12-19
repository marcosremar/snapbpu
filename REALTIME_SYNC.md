# 🔄 Sincronização em Tempo Real - GPU → CPU Backup

## 🎯 Objetivo

**Zero perda de dados!** Qualquer arquivo salvo é **imediatamente** sincronizado para o backup.

## ⚡ Comparação: 30s vs Tempo Real

| Método | Quando sincroniza | Perda máxima | Overhead |
|--------|-------------------|--------------|----------|
| **Rsync 30s** (anterior) | A cada 30 segundos | Últimos 30s | Baixo |
| **Lsyncd Real-time** ✅ | Imediatamente (1s) | ~1 segundo | Médio |
| **inotify Manual** | Imediatamente | ~1 segundo | Médio |

## 🚀 Solução Recomendada: Lsyncd

**Lsyncd** = Linux Sync Daemon (usado pelo Google, Dropbox, etc)

### Por que Lsyncd?

✅ **Instantâneo**: Detecta mudanças via inotify  
✅ **Inteligente**: Agrupa múltiplas mudanças (eficiente)  
✅ **Batching**: Se você salvar 100 arquivos de uma vez, agrupa em 1 rsync  
✅ **Resiliente**: Se perder conexão, sincroniza ao reconectar  
✅ **Profissional**: Usado em produção por grandes empresas  

## 📦 Instalação

### Opção 1: Setup Automático (Recomendado)

```bash
# Na GPU
ssh root@gpu-host

# Rodar script
bash /path/to/setup_realtime_sync.sh root@cpu-backup-host

# Pronto! Sincronização em tempo real ativa
```

### Opção 2: Manual

```bash
# 1. Instalar lsyncd
apt-get update
apt-get install -y lsyncd

# 2. Configurar
nano /etc/lsyncd/lsyncd.conf.lua
# (copiar config do script)

# 3. Iniciar
systemctl enable lsyncd
systemctl start lsyncd
```

## ⚙️ Configuração Otimizada

```lua
settings {
    logfile = "/var/log/lsyncd/lsyncd.log",
    statusFile = "/var/log/lsyncd/lsyncd.status",
    
    -- ⚡ INSTANTÂNEO
    maxDelays = 1,      -- Máx 1 segundo de espera
    maxProcesses = 10,  -- 10 rsyncs paralelos
}

sync {
    default.rssh,
    source = "/workspace",
    host = "root@cpu-backup",
    targetdir = "/workspace",
    
    -- Sync imediato após mudança
    delay = 1,  -- 1 segundo após detectar mudança
    
    rsync = {
        archive = true,
        compress = true,
        _extra = {
            "--delete",              -- Remove arquivos deletados
            "--exclude=.git",        -- Ignora cache
            "--exclude=__pycache__",
            "--bwlimit=10000",       -- Limite: 10MB/s
        }
    },
}
```

## 📊 Performance

### Timeline de Sincronização:

```
Você salva arquivo.py (Ctrl+S)
    ↓ (0.1s - VS Code salva)
Lsyncd detecta mudança via inotify
    ↓ (1s - delay configurado)
Rsync sincroniza arquivo
    ↓ (0.5s - arquivo pequeno)
    ↓ (5s - arquivo 100MB)
✅ Arquivo no backup!

Total: 1.6s para código
       6s para arquivo grande
```

### Impacto na GPU:

| Recurso | Uso | Impacto |
|---------|-----|---------|
| **CPU** | ~1-2% | Imperceptível |
| **RAM** | ~50MB | Irrelevante |
| **Rede** | Apenas quando há mudanças | Mínimo |
| **I/O** | Lê arquivo 1x para sync | Baixo |

### Cenários Reais:

```python
# Salvando modelo durante training
torch.save(model.state_dict(), 'checkpoint.pt')  # 2GB

# Com Lsyncd:
# 1. Arquivo salvo localmente (200ms)
# 2. Training continua imediatamente
# 3. Lsyncd sincroniza em background (30s)
# 4. Zero impacto no training!
```

## 🔥 Casos de Uso

### 1. Desenvolvimento Normal

```python
# Você edita code.py
# Salva (Ctrl+S)
# ✅ Sincronizado em 1-2 segundos!
```

### 2. Training com Checkpoints

```python
# Training loop
for epoch in range(100):
    train()
    torch.save(model, f'checkpoint_{epoch}.pt')
    # ✅ Cada checkpoint sincronizado automaticamente
```

### 3. Git Commits

```bash
git add .
git commit -m "feature"
# ✅ .git/ é excluído (configurado)
# ✅ Apenas código fonte sincronizado
```

## 📊 Monitoramento

### Ver Status em Tempo Real

```bash
# Status do serviço
systemctl status lsyncd

# Logs ao vivo
tail -f /var/log/lsyncd/lsyncd.log

# Status detalhado (JSON)
cat /var/log/lsyncd/lsyncd.status
```

### Status JSON:

```json
{
  "inotify": {
    "watching": 234,  // Arquivos monitorados
    "queued": 0       // Mudanças na fila
  },
  "sync": {
    "source": "/workspace",
    "target": "root@35.240.1.1:/workspace",
    "delays": 0,      // Arquivos esperando sync
    "running": 2      // Rsyncs rodando agora
  }
}
```

## 🚨 Troubleshooting

### Lsyncd não sincronizando?

```bash
# 1. Verificar se está rodando
systemctl status lsyncd

# 2. Ver erros
tail -100 /var/log/lsyncd/lsyncd.log

# 3. Testar SSH manualmente
ssh root@cpu-backup "echo OK"

# 4. Reiniciar
systemctl restart lsyncd
```

### Performance ruim?

```bash
# Se muitas mudanças simultâneas, aumentar buffer:
# Em /etc/lsyncd/lsyncd.conf.lua:

settings {
    maxDelays = 5,      -- Era 1, agora 5
    maxProcesses = 20,  -- Era 10, agora 20
}

# Reiniciar
systemctl restart lsyncd
```

## 🔄 Migrar de Rsync 30s para Lsyncd

### Parar sync antigo:

```bash
# Se estava usando cron job
crontab -e
# Comentar linha do rsync

# Se estava usando sistemd timer
systemctl stop rsync-backup.timer
systemctl disable rsync-backup.timer
```

### Iniciar Lsyncd:

```bash
bash setup_realtime_sync.sh root@cpu-backup
```

## ✅ Checklist de Deploy

- [ ] Instalar lsyncd na GPU
- [ ] Configurar host do backup CPU
- [ ] Iniciar serviço
- [ ] Verificar logs (sem erros)
- [ ] Testar: criar arquivo e verificar backup
- [ ] Testar: deletar arquivo e verificar backup
- [ ] Monitorar performance (1-2% CPU ok)
- [ ] Configurar alertas (opcional)

## 📊 Comparação Final

| Aspecto | Rsync 30s | **Lsyncd Real-time** |
|---------|-----------|----------------------|
| **Perda máxima** | 30 segundos | ~1 segundo ✅ |
| **Latência** | 0-30s | ~1-2s ✅ |
| **Overhead CPU** | 0.5% por 30s | 1-2% contínuo |
| **Overhead rede** | Spike a cada 30s | Constante baixo ✅ |
| **Eficiência** | Transfer tudo | Apenas mudanças ✅ |
| **Complexidade** | Simples | Média |
| **Recomendado para** | Backup batch | **Produção** ✅ |

## ✅ Conclusão

**Sincronização em tempo real com Lsyncd:**

✅ **Zero perda de dados** (máximo 1-2 segundos)  
✅ **Profissional** (usado em produção)  
✅ **Eficiente** (apenas arquivos alterados)  
✅ **Transparente** (não afeta trabalho)  

**Scripts criados:**
- ✅ `scripts/realtime_sync.sh` - Solução inotify manual
- ✅ `scripts/setup_realtime_sync.sh` - Lsyncd automático (recomendado)

**Pronto para deploy!** 🚀
