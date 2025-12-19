#!/bin/bash
"""
Sincronização em Tempo Real - GPU → CPU Backup
Usando inotify para detectar mudanças instantaneamente
"""

# Configuração
WATCH_DIR="/workspace"
BACKUP_HOST="$1"  # Ex: root@35.240.1.1
BACKUP_PATH="/workspace"
LOG_FILE="/var/log/realtime-sync.log"

if [ -z "$BACKUP_HOST" ]; then
    echo "Uso: $0 BACKUP_HOST"
    echo "Exemplo: $0 root@35.240.1.1"
    exit 1
fi

echo "🔄 Iniciando sincronização em tempo real..."
echo "   Monitorando: $WATCH_DIR"
echo "   Backup para: $BACKUP_HOST:$BACKUP_PATH"
echo "   Log: $LOG_FILE"
echo ""

# Instalar inotify-tools se não existir
if ! command -v inotifywait &> /dev/null; then
    echo "📦 Instalando inotify-tools..."
    apt-get update -qq
    apt-get install -y inotify-tools
fi

# Função para sincronizar um arquivo específico
sync_file() {
    local file="$1"
    local relative_path="${file#$WATCH_DIR/}"
    
    # Log
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] Sincronizando: $relative_path" | tee -a "$LOG_FILE"
    
    # Rsync apenas este arquivo
    rsync -avz --compress-level=3 \
        -e "ssh -o StrictHostKeyChecking=no" \
        "$file" \
        "$BACKUP_HOST:$BACKUP_PATH/$relative_path" \
        2>> "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        echo "[$timestamp] ✅ Sincronizado: $relative_path" | tee -a "$LOG_FILE"
    else
        echo "[$timestamp] ❌ Erro ao sincronizar: $relative_path" | tee -a "$LOG_FILE"
    fi
}

# Função para sincronizar diretório completo (inicial)
sync_all() {
    echo "📂 Sincronização inicial completa..."
    rsync -avz --delete --compress-level=3 \
        -e "ssh -o StrictHostKeyChecking=no" \
        "$WATCH_DIR/" \
        "$BACKUP_HOST:$BACKUP_PATH/" \
        2>> "$LOG_FILE"
    echo "✅ Sincronização inicial concluída!"
}

# Sincronização inicial
sync_all

echo ""
echo "👁️  Monitorando mudanças em tempo real..."
echo "   (Ctrl+C para parar)"
echo ""

# Monitorar mudanças em tempo real
inotifywait -m -r \
    --exclude '\.(git|vscode-server|cache|tmp)' \
    -e modify,create,delete,moved_to,moved_from \
    --format '%w%f,%e' \
    "$WATCH_DIR" | while IFS=',' read -r file event; do
    
    # Ignorar eventos temporários
    if [[ "$file" == *".swp"* ]] || [[ "$file" == *".tmp"* ]]; then
        continue
    fi
    
    # Sync baseado no evento
    case "$event" in
        CREATE|MODIFY|MOVED_TO)
            # Aguarda 1 segundo para arquivo terminar de ser escrito
            sleep 1
            if [ -f "$file" ]; then
                sync_file "$file"
            elif [ -d "$file" ]; then
                # Se for diretório, sync completo recursivo
                rsync -avz --compress-level=3 \
                    -e "ssh -o StrictHostKeyChecking=no" \
                    "$file/" \
                    "$BACKUP_HOST:$BACKUP_PATH/${file#$WATCH_DIR/}/" \
                    2>> "$LOG_FILE"
            fi
            ;;
        DELETE|MOVED_FROM)
            # Deletar no backup também
            relative="${file#$WATCH_DIR/}"
            timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            echo "[$timestamp] 🗑️  Deletando: $relative" | tee -a "$LOG_FILE"
            ssh -o StrictHostKeyChecking=no "$BACKUP_HOST" "rm -rf $BACKUP_PATH/$relative" 2>> "$LOG_FILE"
            ;;
    esac
done
