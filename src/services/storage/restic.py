"""
Service para operacoes com Restic (backup/restore)
"""
import subprocess
import json
import os
from typing import List, Dict, Any, Optional
from collections import defaultdict

from ..codeserver_service import CodeServerService, CodeServerConfig


class ResticService:
    """Service para gerenciar backups/restores com Restic"""

    def __init__(
        self,
        repo: str,
        password: str,
        access_key: str,
        secret_key: str,
        connections: int = 32,
    ):
        self.repo = repo
        self.password = password
        self.access_key = access_key
        self.secret_key = secret_key
        self.connections = connections

    def _get_env(self) -> Dict[str, str]:
        """Retorna variaveis de ambiente para o restic"""
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = self.access_key
        env["AWS_SECRET_ACCESS_KEY"] = self.secret_key
        env["RESTIC_PASSWORD"] = self.password
        env["RESTIC_REPOSITORY"] = self.repo
        return env

    def list_snapshots(self, deduplicate: bool = True) -> Dict[str, Any]:
        """Lista snapshots do repositorio"""
        try:
            result = subprocess.run(
                ["restic", "snapshots", "--json"],
                capture_output=True,
                text=True,
                env=self._get_env(),
                timeout=30,
            )

            if result.returncode != 0:
                return {"error": result.stderr, "snapshots": [], "deduplicated": []}

            snapshots = json.loads(result.stdout) if result.stdout else []
            formatted = []

            for s in snapshots:
                formatted.append({
                    "id": s.get("id", ""),
                    "short_id": s.get("id", "")[:8],
                    "time": s.get("time", "")[:19].replace("T", " "),
                    "hostname": s.get("hostname", ""),
                    "tags": s.get("tags", []),
                    "paths": s.get("paths", []),
                    "tree": s.get("tree", ""),
                    "parent": s.get("parent", ""),
                })

            # Ordenar por data (mais recente primeiro)
            formatted.sort(key=lambda x: x["time"], reverse=True)

            if not deduplicate:
                return {"snapshots": formatted, "deduplicated": formatted}

            # Deduplicar por tree hash - manter apenas o mais recente de cada
            tree_groups = defaultdict(list)
            for s in formatted:
                tree_groups[s["tree"]].append(s)

            deduplicated = []
            for tree_hash, group in tree_groups.items():
                most_recent = group[0]
                most_recent["version_count"] = len(group) - 1
                deduplicated.append(most_recent)

            deduplicated.sort(key=lambda x: x["time"], reverse=True)

            return {"snapshots": formatted, "deduplicated": deduplicated}

        except Exception as e:
            return {"error": str(e), "snapshots": [], "deduplicated": []}

    def get_snapshot_folders(self, snapshot_id: str) -> List[Dict[str, Any]]:
        """Lista pastas principais de um snapshot"""
        try:
            result = subprocess.run(
                ["restic", "ls", snapshot_id, "--json"],
                capture_output=True,
                text=True,
                env=self._get_env(),
                timeout=60,
            )

            if result.returncode != 0:
                return []

            folders = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if item.get("type") == "dir":
                        path = item.get("path", "")
                        # Apenas pastas do primeiro nivel
                        parts = path.strip("/").split("/")
                        if len(parts) <= 2:
                            folders.append({
                                "name": parts[-1] if parts else "",
                                "path": path,
                                "size": item.get("size", 0),
                            })
                except json.JSONDecodeError:
                    continue

            return folders

        except Exception as e:
            return []

    def _get_dumont_agent_script(
        self,
        instance_id: str,
        sync_dirs: str = "/workspace",
        dumont_server: str = "https://dumontcloud.com",
        sync_interval: int = 30,
        keep_last: int = 10,
    ) -> str:
        """Gera o script de instalacao do DumontAgent com suporte a systemd"""
        return f'''
# ========================================
# DumontAgent Installation v2.0
# ========================================
echo "DUMONT_AGENT_INSTALL_START"

INSTALL_DIR="/opt/dumont"
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log

# Instalar restic se necessario
if ! command -v restic &> /dev/null; then
    echo "Instalando restic..."
    wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2
    bunzip2 -f /tmp/restic.bz2
    chmod +x /tmp/restic
    mv /tmp/restic /usr/local/bin/restic
fi

# Criar arquivo de configuracao
cat > "$INSTALL_DIR/config.env" << 'AGENTCFG'
export DUMONT_SERVER="{dumont_server}"
export INSTANCE_ID="{instance_id}"
export SYNC_DIRS="{sync_dirs}"
export SYNC_INTERVAL={sync_interval}
export KEEP_LAST={keep_last}
export AWS_ACCESS_KEY_ID="{self.access_key}"
export AWS_SECRET_ACCESS_KEY="{self.secret_key}"
export RESTIC_PASSWORD="{self.password}"
export RESTIC_REPOSITORY="{self.repo}"
AGENTCFG
chmod 600 "$INSTALL_DIR/config.env"

# Criar script do agente
cat > "$INSTALL_DIR/dumont-agent.sh" << 'AGENTSCRIPT'
#!/bin/bash
VERSION="2.1.0"
AGENT_NAME="DumontAgent"
INSTALL_DIR="/opt/dumont"
LOG_FILE="/var/log/dumont-agent.log"
LOCK_FILE="/tmp/dumont-agent.lock"
STATUS_FILE="/tmp/dumont-agent-status.json"

# Limites de disco (%)
DISK_WARNING_THRESHOLD=85
DISK_CRITICAL_THRESHOLD=95

source "$INSTALL_DIR/config.env"

# Usar valores do config ou defaults
INTERVAL=${{SYNC_INTERVAL:-30}}
RETENTION=${{KEEP_LAST:-10}}

log() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2" | tee -a "$LOG_FILE"
}}

# Obter uso de disco em %
get_disk_usage() {{
    local dir="${{1:-$SYNC_DIRS}}"
    df "$dir" 2>/dev/null | awk 'NR==2 {{gsub(/%/,""); print $5}}'
}}

# Obter espaco livre em GB
get_disk_free_gb() {{
    local dir="${{1:-$SYNC_DIRS}}"
    df -BG "$dir" 2>/dev/null | awk 'NR==2 {{gsub(/G/,""); print $4}}'
}}

send_status() {{
    local disk_usage=$(get_disk_usage)
    local disk_free=$(get_disk_free_gb)
    cat > "$STATUS_FILE" << EOF
{{"agent":"$AGENT_NAME","version":"$VERSION","instance_id":"$INSTANCE_ID","status":"$1","message":"$2","last_backup":"$3","timestamp":"$(date -Iseconds)","interval":$INTERVAL,"keep_last":$RETENTION,"disk_usage":${{disk_usage:-0}},"disk_free_gb":${{disk_free:-0}}}}
EOF
    [ -n "$DUMONT_SERVER" ] && curl -s -X POST "$DUMONT_SERVER/api/agent/status" -H "Content-Type: application/json" -d @"$STATUS_FILE" > /dev/null 2>&1 || true
}}

# Verificar disco antes de operacoes
check_disk() {{
    local usage=$(get_disk_usage)
    local free=$(get_disk_free_gb)

    if [ -z "$usage" ]; then
        return 0  # Se nao conseguiu ler, continua
    fi

    if [ "$usage" -ge "$DISK_CRITICAL_THRESHOLD" ]; then
        log "CRITICAL" "DISCO CHEIO! Uso: ${{usage}}% (livre: ${{free}}GB)"
        send_status "disk_full" "DISCO CHEIO! ${{usage}}% usado. Libere espaco AGORA!" ""
        return 2  # Critico - para tudo
    elif [ "$usage" -ge "$DISK_WARNING_THRESHOLD" ]; then
        log "WARNING" "Disco quase cheio! Uso: ${{usage}}% (livre: ${{free}}GB)"
        send_status "disk_warning" "Atencao: Disco ${{usage}}% cheio (${{free}}GB livre)" ""
        return 1  # Warning - continua mas avisa
    fi
    return 0
}}

do_backup() {{
    # Verificar disco antes do backup
    check_disk
    local disk_status=$?

    if [ $disk_status -eq 2 ]; then
        log "ERROR" "Backup cancelado - disco cheio!"
        return 1
    fi

    local start_time=$(date +%s)
    log "INFO" "Iniciando backup de $SYNC_DIRS..."
    send_status "syncing" "Backup em progresso" ""

    if restic backup "$SYNC_DIRS" --tag auto --tag "instance:$INSTANCE_ID" --quiet -o s3.connections=32 2>&1 | tee -a "$LOG_FILE"; then
        local duration=$(($(date +%s) - start_time))
        log "INFO" "Backup concluido em ${{duration}}s"

        # Verificar disco novamente apos backup e ajustar mensagem
        check_disk
        local post_status=$?
        if [ $post_status -eq 1 ]; then
            send_status "disk_warning" "Backup OK (${{duration}}s) - ATENCAO: disco quase cheio!" "$(date -Iseconds)"
        else
            send_status "idle" "Ultimo backup: ${{duration}}s" "$(date -Iseconds)"
        fi

        restic forget --keep-last $RETENTION --tag auto --quiet 2>/dev/null
        return 0
    else
        log "ERROR" "Backup falhou"
        send_status "error" "Backup falhou" ""
        return 1
    fi
}}

[ -f "$LOCK_FILE" ] && kill -0 $(cat "$LOCK_FILE") 2>/dev/null && echo "Ja rodando" && exit 1
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "INFO" "=== $AGENT_NAME v$VERSION Iniciado (PID $$) ==="
log "INFO" "Intervalo: ${{INTERVAL}}s | Retencao: $RETENTION snapshots"
log "INFO" "Limites de disco: Warning=${{DISK_WARNING_THRESHOLD}}% Critical=${{DISK_CRITICAL_THRESHOLD}}%"
send_status "starting" "Agente iniciado" ""

last_hash=""
disk_full_notified=false
while true; do
    # Verificar disco a cada ciclo
    check_disk
    disk_status=$?

    if [ $disk_status -eq 2 ]; then
        # Disco critico - nao fazer backup, apenas alertar
        if [ "$disk_full_notified" = false ]; then
            log "CRITICAL" "Sync pausado - disco cheio!"
            disk_full_notified=true
        fi
        sleep "$INTERVAL"
        continue
    else
        disk_full_notified=false
    fi

    if [ -d "$SYNC_DIRS" ]; then
        current_hash=$(find "$SYNC_DIRS" -type f -mmin -1 2>/dev/null | sort | md5sum | cut -d" " -f1)
        if [ "$current_hash" != "$last_hash" ] && [ -n "$current_hash" ]; then
            do_backup && last_hash="$current_hash"
        else
            # Manter status de warning se disco estiver quase cheio
            if [ $disk_status -eq 1 ]; then
                send_status "disk_warning" "Aguardando - disco quase cheio!" ""
            else
                send_status "idle" "Aguardando mudancas" ""
            fi
        fi
    fi
    sleep "$INTERVAL"
done
AGENTSCRIPT
chmod +x "$INSTALL_DIR/dumont-agent.sh"

# Criar script de controle (com suporte a systemd)
cat > "/usr/local/bin/dumontctl" << 'CTLSCRIPT'
#!/bin/bash
INSTALL_DIR="/opt/dumont"
SERVICE_NAME="dumont-agent"

# Detectar se systemd esta disponivel
has_systemd() {{
    command -v systemctl &> /dev/null && systemctl --version &> /dev/null 2>&1
}}

case "$1" in
    start)
        if has_systemd; then
            systemctl start $SERVICE_NAME && echo "Iniciado via systemd"
        else
            pkill -f dumont-agent.sh 2>/dev/null
            nohup "$INSTALL_DIR/dumont-agent.sh" > /dev/null 2>&1 &
            echo "Iniciado (PID $!)"
        fi
        ;;
    stop)
        if has_systemd; then
            systemctl stop $SERVICE_NAME && echo "Parado via systemd"
        else
            pkill -f dumont-agent.sh && echo "Parado" || echo "Nao estava rodando"
        fi
        ;;
    restart)
        if has_systemd; then
            systemctl restart $SERVICE_NAME && echo "Reiniciado via systemd"
        else
            $0 stop
            sleep 1
            $0 start
        fi
        ;;
    status)
        echo "=== Status do Agente ==="
        cat /tmp/dumont-agent-status.json 2>/dev/null | python3 -m json.tool || echo "Sem status"
        echo ""
        if has_systemd; then
            echo "=== Systemd ==="
            systemctl status $SERVICE_NAME --no-pager 2>/dev/null | head -10
        else
            echo "=== Processo ==="
            pgrep -f dumont-agent.sh > /dev/null && echo "Rodando (PID $(pgrep -f dumont-agent.sh))" || echo "Parado"
        fi
        ;;
    logs)
        tail -${{2:-50}} /var/log/dumont-agent.log 2>/dev/null
        ;;
    logs-follow)
        tail -f /var/log/dumont-agent.log 2>/dev/null
        ;;
    backup)
        echo "Forcando backup manual..."
        source "$INSTALL_DIR/config.env"
        restic backup "$SYNC_DIRS" --tag manual -o s3.connections=32
        ;;
    config)
        echo "=== Configuracao Atual ==="
        cat "$INSTALL_DIR/config.env" 2>/dev/null | grep -v "KEY\|PASSWORD" || echo "Sem config"
        ;;
    *)
        echo "DumontAgent Control v2.0"
        echo ""
        echo "Uso: dumontctl [comando]"
        echo ""
        echo "Comandos:"
        echo "  start       Inicia o agente"
        echo "  stop        Para o agente"
        echo "  restart     Reinicia o agente"
        echo "  status      Mostra status atual"
        echo "  logs [N]    Mostra ultimas N linhas do log"
        echo "  logs-follow Segue o log em tempo real"
        echo "  backup      Forca backup manual"
        echo "  config      Mostra configuracao atual"
        ;;
esac
CTLSCRIPT
chmod +x /usr/local/bin/dumontctl

# Criar servico systemd (se disponivel)
if command -v systemctl &> /dev/null && systemctl --version &> /dev/null 2>&1; then
    echo "Configurando systemd..."
    cat > /etc/systemd/system/dumont-agent.service << 'SYSTEMDUNIT'
[Unit]
Description=Dumont Cloud Sync Agent
After=network.target

[Service]
Type=simple
ExecStart=/opt/dumont/dumont-agent.sh
WorkingDirectory=/opt/dumont
EnvironmentFile=/opt/dumont/config.env
Restart=always
RestartSec=10
StandardOutput=append:/var/log/dumont-agent.log
StandardError=append:/var/log/dumont-agent.log

[Install]
WantedBy=multi-user.target
SYSTEMDUNIT

    # Parar processo antigo se existir
    pkill -f "dumont-agent.sh" 2>/dev/null || true
    sleep 1

    # Ativar e iniciar via systemd
    systemctl daemon-reload
    systemctl enable dumont-agent
    systemctl start dumont-agent
    sleep 2

    if systemctl is-active --quiet dumont-agent; then
        echo "DUMONT_AGENT_INSTALLED"
        echo "DumontAgent rodando via systemd (restart automatico habilitado)"
    else
        echo "DUMONT_AGENT_FAILED"
        systemctl status dumont-agent --no-pager
    fi
else
    # Fallback: usar nohup
    echo "Systemd nao disponivel, usando nohup..."
    pkill -f "dumont-agent.sh" 2>/dev/null || true
    sleep 1
    nohup "$INSTALL_DIR/dumont-agent.sh" > /dev/null 2>&1 &
    sleep 2

    if pgrep -f "dumont-agent.sh" > /dev/null; then
        echo "DUMONT_AGENT_INSTALLED"
        echo "DumontAgent rodando (PID $(pgrep -f dumont-agent.sh)) - sem restart automatico"
    else
        echo "DUMONT_AGENT_FAILED"
    fi
fi
'''

    def restore(
        self,
        snapshot_id: str,
        target_path: str,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str = "root",
        install_codeserver: bool = True,
        install_agent: bool = True,
        instance_id: str = "",
        dumont_server: str = "https://dumontcloud.com",
        sync_interval: int = 30,
        keep_last: int = 10,
    ) -> Dict[str, Any]:
        """
        Executa restore em uma maquina remota via SSH.

        Args:
            snapshot_id: ID do snapshot a restaurar
            target_path: Caminho de destino (ex: /workspace)
            ssh_host: IP do servidor
            ssh_port: Porta SSH
            ssh_user: Usuario SSH (padrao: root, recomendado: ubuntu)
            install_codeserver: Instalar code-server?
            install_agent: Instalar DumontAgent?
            instance_id: ID da instancia (para tags)
            dumont_server: URL do servidor Dumont
            sync_interval: Intervalo de sync em segundos
            keep_last: Quantos backups manter

        Returns:
            Dict com resultado do restore
        """
        # Script para instalar DumontAgent
        agent_install = ""
        if install_agent:
            agent_install = self._get_dumont_agent_script(
                instance_id=instance_id or f"vast-{ssh_host}",
                sync_dirs=target_path,
                dumont_server=dumont_server,
                sync_interval=sync_interval,
                keep_last=keep_last,
            )

        cmd = f"""
export AWS_ACCESS_KEY_ID="{self.access_key}"
export AWS_SECRET_ACCESS_KEY="{self.secret_key}"
export RESTIC_REPOSITORY="{self.repo}"
export RESTIC_PASSWORD="{self.password}"
mkdir -p {target_path}
restic restore {snapshot_id} --target {target_path} -o s3.connections={self.connections} 2>&1
echo "RESTORE_COMPLETED"
du -sh {target_path}/* 2>/dev/null | head -5
{agent_install}
"""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=30",
                    "-p", str(ssh_port),
                    f"{ssh_user}@{ssh_host}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutos max
            )

            restore_success = "RESTORE_COMPLETED" in result.stdout
            output = result.stdout
            error = result.stderr if not restore_success else None

            # Instalar e configurar code-server usando o servico dedicado
            codeserver_result = None
            if install_codeserver and restore_success:
                try:
                    config = CodeServerConfig(
                        port=8080,
                        workspace=target_path,
                        theme="Default Dark+",
                        trust_enabled=False,
                        user=ssh_user,
                    )
                    codeserver_svc = CodeServerService(ssh_host, ssh_port, ssh_user)
                    codeserver_result = codeserver_svc.setup_full(config)
                    output += f"\n\n=== Code-Server Setup ===\n{codeserver_result}"
                except Exception as e:
                    codeserver_result = {"success": False, "error": str(e)}
                    output += f"\n\nCode-server setup failed: {e}"

            return {
                "success": restore_success,
                "output": output,
                "error": error,
                "codeserver": codeserver_result,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Restore timeout (5 minutos)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_snapshot_tree(self, snapshot_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Lista arvore de arquivos de um snapshot"""
        try:
            result = subprocess.run(
                ["restic", "ls", snapshot_id, "--json"],
                capture_output=True,
                text=True,
                env=self._get_env(),
                timeout=120,
            )

            if result.returncode != 0:
                return []

            # Build tree structure
            all_items = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    path = item.get("path", "")
                    parts = path.strip("/").split("/")
                    depth = len(parts)

                    # Limitar profundidade
                    if depth > max_depth + 1:  # +1 porque o primeiro nivel e o root
                        continue

                    all_items.append({
                        "name": parts[-1] if parts else "",
                        "path": path,
                        "type": item.get("type", "file"),
                        "size": item.get("size", 0),
                        "mtime": item.get("mtime", "")[:19].replace("T", " ") if item.get("mtime") else "",
                        "depth": depth,
                        "parts": parts,
                    })
                except json.JSONDecodeError:
                    continue

            # Build hierarchical tree
            def build_tree(items, parent_path="", current_depth=1):
                tree = []
                # Group items by their immediate parent
                children = {}
                for item in items:
                    if item["depth"] == current_depth:
                        item_path = item["path"]
                        if parent_path == "" or item_path.startswith(parent_path + "/"):
                            children[item_path] = {
                                "name": item["name"],
                                "path": item["path"],
                                "type": item["type"],
                                "size": item["size"],
                                "mtime": item["mtime"],
                                "children": []
                            }

                # For each direct child, find its children recursively
                for path, node in children.items():
                    if node["type"] == "dir":
                        node["children"] = build_tree(items, path, current_depth + 1)
                    tree.append(node)

                # Sort: folders first, then by name
                tree.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"].lower()))
                return tree

            return build_tree(all_items)

        except Exception as e:
            print(f"Error getting snapshot tree: {e}")
            return []

    def install_on_remote(self, ssh_host: str, ssh_port: int, timeout: int = 30) -> bool:
        """Instala restic moderno em uma maquina remota"""
        cmd = """
wget -q https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 -O /tmp/restic.bz2 &&
bunzip2 -f /tmp/restic.bz2 &&
chmod +x /tmp/restic &&
mv /tmp/restic /usr/local/bin/restic &&
/usr/local/bin/restic version
"""
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    cmd,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return "restic" in result.stdout.lower()
        except Exception:
            return False
