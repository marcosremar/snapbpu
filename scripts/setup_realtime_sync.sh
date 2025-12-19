#!/bin/bash
"""
Configuração de Lsyncd - Sincronização Profissional em Tempo Real
Mais eficiente que inotify manual
"""

BACKUP_HOST="$1"
WORKSPACE="/workspace"

if [ -z "$BACKUP_HOST" ]; then
    echo "Uso: $0 BACKUP_HOST"
    echo "Exemplo: $0 root@35.240.1.1"
    exit 1
fi

echo "📦 Instalando lsyncd..."
apt-get update -qq
apt-get install -y lsyncd

echo "⚙️  Configurando lsyncd..."

# Criar arquivo de configuração
cat > /etc/lsyncd/lsyncd.conf.lua << EOF
----
-- Lsyncd Configuration - Real-time Sync
-- GPU → CPU Backup
----

settings {
    logfile = "/var/log/lsyncd/lsyncd.log",
    statusFile = "/var/log/lsyncd/lsyncd.status",
    statusInterval = 5,
    
    -- Agressivo: Sync IMEDIATO
    maxDelays = 1,      -- Max 1 segundo de espera
    maxProcesses = 10,  -- 10 processos rsync paralelos
}

-- Sincronização para CPU backup
sync {
    default.rssh,
    source = "$WORKSPACE",
    host = "$BACKUP_HOST",
    targetdir = "$WORKSPACE",
    
    -- Configurações rsync
    rsync = {
        archive = true,
        compress = true,
        verbose = true,
        _extra = {
            "--delete",                    -- Remove arquivos deletados
            "--exclude=.git",              -- Ignora .git
            "--exclude=.vscode-server",    -- Ignora VS Code cache
            "--exclude=*.tmp",             -- Ignora temporários
            "--exclude=*.swp",             -- Ignora vim swap
            "--exclude=__pycache__",       -- Ignora Python cache
            "--exclude=*.pyc",
            "--bwlimit=10000",             -- Limite: 10MB/s (não saturar rede)
        }
    },
    
    -- SSH config
    ssh = {
        _extra = {
            "-o", "StrictHostKeyChecking=no",
            "-o", "Compression=yes",
        }
    },
    
    -- Delay mínimo (praticamente instantâneo)
    delay = 1,  -- 1 segundo após mudança
}

-- Log de eventos
log(Normal, "🔄 Lsyncd iniciado - Sincronização em tempo real ativa")
EOF

# Criar diretório de logs
mkdir -p /var/log/lsyncd

# Criar serviço systemd
cat > /etc/systemd/system/lsyncd.service << EOF
[Unit]
Description=Live Syncing Daemon - Realtime Backup
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/lsyncd /etc/lsyncd/lsyncd.conf.lua
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Iniciar serviço
systemctl daemon-reload
systemctl enable lsyncd
systemctl start lsyncd

echo ""
echo "✅ Lsyncd configurado e rodando!"
echo ""
echo "📊 Status:"
systemctl status lsyncd --no-pager
echo ""
echo "📝 Logs:"
echo "   tail -f /var/log/lsyncd/lsyncd.log"
echo ""
echo "📊 Status detalhado:"
echo "   cat /var/log/lsyncd/lsyncd.status"
echo ""
echo "🔄 Sincronização em tempo real ATIVA!"
echo "   Qualquer mudança em $WORKSPACE é sincronizada IMEDIATAMENTE"
