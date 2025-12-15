#!/bin/bash
# SnapGPU Sync Daemon - Sincroniza workspace com R2 a cada 30 segundos

export AWS_ACCESS_KEY_ID="f0a6f424064e46c903c76a447f5e73d2"
export AWS_SECRET_ACCESS_KEY="1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5"
export RESTIC_PASSWORD="musetalk123"
export RESTIC_REPOSITORY="s3:https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com/musetalk/restic"

SYNC_DIRS="/workspace"
LOG_FILE="/var/log/snapgpu-sync.log"
LOCK_FILE="/tmp/snapgpu-sync.lock"
INTERVAL=30

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Sync daemon ja esta rodando (PID $PID)"
        exit 1
    fi
fi

echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "=== SnapGPU Sync Daemon Iniciado ==="
log "PID: $$"
log "Intervalo: ${INTERVAL}s"
log "Diretorio: $SYNC_DIRS"

LAST_BACKUP=""
while true; do
    if [ -d "$SYNC_DIRS" ]; then
        CURRENT_HASH=$(find "$SYNC_DIRS" -type f -mmin -1 2>/dev/null | sort | md5sum | cut -d" " -f1)

        if [ "$CURRENT_HASH" != "$LAST_BACKUP" ]; then
            log "Detectada mudanca, iniciando backup incremental..."
            START_TIME=$(date +%s)

            if restic backup "$SYNC_DIRS" --tag auto --quiet -o s3.connections=16 2>&1 | tee -a "$LOG_FILE"; then
                END_TIME=$(date +%s)
                DURATION=$((END_TIME - START_TIME))
                log "Backup concluido em ${DURATION}s"
                LAST_BACKUP="$CURRENT_HASH"
                restic forget --keep-last 10 --tag auto --quiet 2>/dev/null
            else
                log "ERRO: Backup falhou"
            fi
        else
            log "Nenhuma mudanca detectada"
        fi
    else
        log "AVISO: Diretorio $SYNC_DIRS nao existe"
    fi

    sleep "$INTERVAL"
done
