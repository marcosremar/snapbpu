"""
GPU Checkpoint Service

Checkpoint/Restore de estado GPU (VRAM + processos) usando cuda-checkpoint + CRIU.

Permite restaurar o estado completo da VRAM em segundos ao invés de minutos
(download de modelos).

Requisitos:
- NVIDIA Driver 550+ (suporta cuda-checkpoint)
- CRIU instalado
- Bare metal ou VM com acesso privilegiado

Provedores testados:
- TensorDock Bare Metal: ✅ Funciona
- VAST.ai: ✅ Funciona (maioria das máquinas)
- RunPod: ⚠️ Parcial

Arquitetura:
- GPU Machine sincroniza em tempo real com Sync Machine
- Sync Machine cria snapshots a cada 30 segundos
- Se GPU cair, restaura do snapshot local (mais rápido)
- R2 serve como backup de longo prazo
"""

import os
import subprocess
import time
import json
import threading
from typing import Optional, Dict, List
from dataclasses import dataclass

from .config import get_settings


@dataclass
class GPUCheckpoint:
    """Representa um checkpoint de estado GPU"""
    checkpoint_id: str
    instance_id: str
    timestamp: float
    size_bytes: int
    process_name: str
    vram_used_gb: float
    status: str  # 'creating', 'ready', 'uploading', 'failed'
    sync_machine_id: Optional[str] = None
    r2_path: Optional[str] = None


class GPUCheckpointService:
    """Serviço para checkpoint/restore de estado GPU"""

    # Scripts que serão instalados nas máquinas GPU
    CHECKPOINT_SCRIPT = '''#!/bin/bash
set -e
CHECKPOINT_ID=${1:-"gpu-$(date +%s)"}
CHECKPOINT_DIR="/workspace/.gpu-checkpoints/$CHECKPOINT_ID"

# Encontrar processo Python usando GPU
PID=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | head -1)

if [ -z "$PID" ]; then
    echo '{"error": "Nenhum processo GPU encontrado"}'
    exit 1
fi

PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "unknown")
VRAM_USED=$(nvidia-smi --query-compute-apps=used_memory --format=csv,noheader,nounits | head -1)

echo "Fazendo checkpoint do PID $PID ($PROCESS_NAME, ${VRAM_USED}MB VRAM)..."
mkdir -p "$CHECKPOINT_DIR"

# 1. Suspender estado CUDA
if ! cuda-checkpoint --toggle --pid $PID 2>/dev/null; then
    echo '{"error": "cuda-checkpoint falhou - verifique se esta instalado"}'
    exit 1
fi

# 2. CRIU dump
if ! criu dump -t $PID -D "$CHECKPOINT_DIR" --shell-job --tcp-established --ext-unix-sk --file-locks 2>/dev/null; then
    # Tentar resumir CUDA se dump falhou
    cuda-checkpoint --toggle --pid $PID 2>/dev/null || true
    echo '{"error": "CRIU dump falhou"}'
    exit 1
fi

# 3. Calcular tamanho
SIZE=$(du -sb "$CHECKPOINT_DIR" | cut -f1)

# 4. Output JSON
echo "{\"checkpoint_id\": \"$CHECKPOINT_ID\", \"pid\": $PID, \"process_name\": \"$PROCESS_NAME\", \"vram_mb\": $VRAM_USED, \"size_bytes\": $SIZE, \"path\": \"$CHECKPOINT_DIR\"}"
'''

    RESTORE_SCRIPT = '''#!/bin/bash
set -e
CHECKPOINT_ID=$1

if [ -z "$CHECKPOINT_ID" ]; then
    echo '{"error": "checkpoint_id obrigatorio"}'
    exit 1
fi

CHECKPOINT_DIR="/workspace/.gpu-checkpoints/$CHECKPOINT_ID"

if [ ! -d "$CHECKPOINT_DIR" ]; then
    echo '{"error": "Checkpoint nao encontrado"}'
    exit 1
fi

# Restaurar processo
criu restore -D "$CHECKPOINT_DIR" --shell-job --tcp-established --ext-unix-sk --file-locks &
RESTORED_PID=$!

sleep 2

# Verificar se processo está vivo
if ! kill -0 $RESTORED_PID 2>/dev/null; then
    echo '{"error": "Processo nao iniciou"}'
    exit 1
fi

# Resumir CUDA
if ! cuda-checkpoint --toggle --pid $RESTORED_PID 2>/dev/null; then
    echo '{"error": "cuda-checkpoint resume falhou"}'
    exit 1
fi

echo "{\"restored_pid\": $RESTORED_PID, \"checkpoint_id\": \"$CHECKPOINT_ID\"}"
'''

    SETUP_SCRIPT = '''#!/bin/bash
set -e

echo "=== Instalando dependencias para GPU Checkpoint ==="

# Verificar driver NVIDIA
DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
echo "Driver NVIDIA: $DRIVER_VERSION"

MAJOR_VERSION="${DRIVER_VERSION%%.*}"
if [ "$MAJOR_VERSION" -lt 550 ]; then
    echo '{"error": "Driver 550+ necessario (atual: '$DRIVER_VERSION')"}'
    exit 1
fi

# Instalar CRIU
apt-get update -qq
apt-get install -y -qq criu protobuf-compiler libprotobuf-dev libnl-3-dev libcap-dev python3-protobuf

CRIU_VERSION=$(criu --version 2>/dev/null | grep -oP '\\d+\\.\\d+' | head -1)
echo "CRIU instalado: $CRIU_VERSION"

# Compilar cuda-checkpoint se não existe
if ! command -v cuda-checkpoint &>/dev/null; then
    echo "Compilando cuda-checkpoint..."
    cd /tmp
    rm -rf cuda-checkpoint
    git clone --quiet https://github.com/NVIDIA/cuda-checkpoint.git
    cd cuda-checkpoint
    make -j$(nproc) 2>/dev/null
    cp cuda-checkpoint /usr/local/bin/
    chmod +x /usr/local/bin/cuda-checkpoint
    echo "cuda-checkpoint instalado"
fi

# Criar diretórios
mkdir -p /workspace/.gpu-checkpoints
mkdir -p /opt/dumont/scripts

echo '{"success": true, "driver": "'$DRIVER_VERSION'", "criu": "'$CRIU_VERSION'"}'
'''

    def __init__(self):
        self._checkpoints: Dict[str, GPUCheckpoint] = {}
        self._lock = threading.Lock()
        self._settings = get_settings()

    def setup_instance(self, instance_id: str, ssh_host: str, ssh_port: int) -> Dict:
        """
        Instala dependências de checkpoint em uma instância GPU.

        Args:
            instance_id: ID da instância
            ssh_host: Host SSH
            ssh_port: Porta SSH

        Returns:
            Dict com resultado da instalação
        """
        try:
            # Criar script completo com checkpoint e restore
            full_setup = self.SETUP_SCRIPT + f'''
# Instalar scripts
cat > /opt/dumont/scripts/gpu-checkpoint.sh << 'CHECKPOINT_EOF'
{self.CHECKPOINT_SCRIPT}
CHECKPOINT_EOF

cat > /opt/dumont/scripts/gpu-restore.sh << 'RESTORE_EOF'
{self.RESTORE_SCRIPT}
RESTORE_EOF

chmod +x /opt/dumont/scripts/*.sh
'''

            result = self._ssh_exec(
                ssh_host, ssh_port,
                f'bash -c "{full_setup}"',
                timeout=300
            )

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            output = result.stdout.strip()
            for line in output.split('\n'):
                if line.startswith('{'):
                    return json.loads(line)

            return {'success': True, 'output': output}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_checkpoint(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int,
        checkpoint_id: Optional[str] = None
    ) -> Dict:
        """
        Cria um checkpoint do estado GPU atual.

        Args:
            instance_id: ID da instância
            ssh_host: Host SSH
            ssh_port: Porta SSH
            checkpoint_id: ID opcional (auto-gerado se não fornecido)

        Returns:
            Dict com informações do checkpoint
        """
        checkpoint_id = checkpoint_id or f"gpu-{instance_id}-{int(time.time())}"

        try:
            result = self._ssh_exec(
                ssh_host, ssh_port,
                f'/opt/dumont/scripts/gpu-checkpoint.sh {checkpoint_id}',
                timeout=60
            )

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            output = result.stdout.strip()
            for line in output.split('\n'):
                if line.startswith('{'):
                    data = json.loads(line)

                    if 'error' in data:
                        return {'success': False, 'error': data['error']}

                    checkpoint = GPUCheckpoint(
                        checkpoint_id=data['checkpoint_id'],
                        instance_id=instance_id,
                        timestamp=time.time(),
                        size_bytes=data.get('size_bytes', 0),
                        process_name=data.get('process_name', 'unknown'),
                        vram_used_gb=data.get('vram_mb', 0) / 1024,
                        status='ready'
                    )

                    with self._lock:
                        self._checkpoints[checkpoint_id] = checkpoint

                    return {
                        'success': True,
                        'checkpoint_id': checkpoint_id,
                        'size_bytes': checkpoint.size_bytes,
                        'vram_gb': checkpoint.vram_used_gb,
                        'process': checkpoint.process_name
                    }

            return {'success': False, 'error': 'Output inválido'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def restore_checkpoint(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int,
        checkpoint_id: str
    ) -> Dict:
        """
        Restaura um checkpoint em uma instância.

        Args:
            instance_id: ID da instância destino
            ssh_host: Host SSH
            ssh_port: Porta SSH
            checkpoint_id: ID do checkpoint a restaurar

        Returns:
            Dict com resultado do restore
        """
        try:
            result = self._ssh_exec(
                ssh_host, ssh_port,
                f'/opt/dumont/scripts/gpu-restore.sh {checkpoint_id}',
                timeout=60
            )

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            output = result.stdout.strip()
            for line in output.split('\n'):
                if line.startswith('{'):
                    data = json.loads(line)

                    if 'error' in data:
                        return {'success': False, 'error': data['error']}

                    return {
                        'success': True,
                        'restored_pid': data.get('restored_pid'),
                        'checkpoint_id': checkpoint_id
                    }

            return {'success': False, 'error': 'Output inválido'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def list_checkpoints(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int
    ) -> List[Dict]:
        """Lista checkpoints disponíveis em uma instância"""
        try:
            result = self._ssh_exec(
                ssh_host, ssh_port,
                'ls -la /workspace/.gpu-checkpoints/ 2>/dev/null || echo "[]"',
                timeout=10
            )

            if result.returncode != 0:
                return []

            checkpoints = []
            for line in result.stdout.strip().split('\n'):
                if line.startswith('d') and 'gpu-' in line:
                    parts = line.split()
                    if len(parts) >= 9:
                        name = parts[-1]
                        checkpoints.append({
                            'checkpoint_id': name,
                            'instance_id': instance_id
                        })

            return checkpoints

        except Exception:
            return []

    def delete_checkpoint(
        self,
        ssh_host: str,
        ssh_port: int,
        checkpoint_id: str
    ) -> Dict:
        """Deleta um checkpoint"""
        try:
            result = self._ssh_exec(
                ssh_host, ssh_port,
                f'rm -rf /workspace/.gpu-checkpoints/{checkpoint_id}',
                timeout=30
            )

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            with self._lock:
                if checkpoint_id in self._checkpoints:
                    del self._checkpoints[checkpoint_id]

            return {'success': True, 'checkpoint_id': checkpoint_id}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cleanup_old_checkpoints(
        self,
        ssh_host: str,
        ssh_port: int,
        keep_count: int = 5
    ) -> Dict:
        """Remove checkpoints antigos, mantendo apenas os N mais recentes"""
        try:
            # Listar e ordenar por data
            cmd = '''
cd /workspace/.gpu-checkpoints 2>/dev/null || exit 0
ls -t | tail -n +{} | xargs -r rm -rf
echo '{{"success": true, "kept": {}}}'
'''.format(keep_count + 1, keep_count)

            result = self._ssh_exec(ssh_host, ssh_port, cmd, timeout=30)

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            return {'success': True, 'kept': keep_count}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def sync_to_machine(
        self,
        src_ssh_host: str,
        src_ssh_port: int,
        dst_ssh_host: str,
        dst_ssh_port: int,
        checkpoint_id: str
    ) -> Dict:
        """
        Sincroniza checkpoint entre máquinas (GPU -> Sync Machine).

        Args:
            src_*: Máquina origem (GPU)
            dst_*: Máquina destino (Sync)
            checkpoint_id: ID do checkpoint

        Returns:
            Dict com resultado da sincronização
        """
        try:
            # Comprimir na origem
            compress_cmd = f'''
cd /workspace/.gpu-checkpoints &&
tar -czf {checkpoint_id}.tar.gz {checkpoint_id}/ &&
echo "size=$(stat -c%s {checkpoint_id}.tar.gz)"
'''
            result = self._ssh_exec(src_ssh_host, src_ssh_port, compress_cmd, timeout=120)

            if result.returncode != 0:
                return {'success': False, 'error': f'Compress failed: {result.stderr}'}

            # Transferir via rsync
            rsync_cmd = f'''
rsync -avz -e "ssh -o StrictHostKeyChecking=no -p {dst_ssh_port}" \
    /workspace/.gpu-checkpoints/{checkpoint_id}.tar.gz \
    root@{dst_ssh_host}:/workspace/.gpu-checkpoints/
'''
            result = self._ssh_exec(src_ssh_host, src_ssh_port, rsync_cmd, timeout=300)

            if result.returncode != 0:
                return {'success': False, 'error': f'Rsync failed: {result.stderr}'}

            # Descomprimir no destino
            extract_cmd = f'''
cd /workspace/.gpu-checkpoints &&
tar -xzf {checkpoint_id}.tar.gz &&
rm {checkpoint_id}.tar.gz
'''
            result = self._ssh_exec(dst_ssh_host, dst_ssh_port, extract_cmd, timeout=120)

            if result.returncode != 0:
                return {'success': False, 'error': f'Extract failed: {result.stderr}'}

            # Limpar arquivo comprimido na origem
            self._ssh_exec(
                src_ssh_host, src_ssh_port,
                f'rm -f /workspace/.gpu-checkpoints/{checkpoint_id}.tar.gz',
                timeout=10
            )

            return {'success': True, 'checkpoint_id': checkpoint_id}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def upload_to_r2(
        self,
        ssh_host: str,
        ssh_port: int,
        checkpoint_id: str,
        r2_bucket: Optional[str] = None
    ) -> Dict:
        """Upload checkpoint para Cloudflare R2 (backup de longo prazo)"""
        bucket = r2_bucket or self._settings.r2_bucket

        try:
            cmd = f'''
cd /workspace/.gpu-checkpoints &&
tar -czf {checkpoint_id}.tar.gz {checkpoint_id}/ &&
rclone copy {checkpoint_id}.tar.gz r2:{bucket}/ &&
rm {checkpoint_id}.tar.gz &&
echo '{{"success": true, "path": "r2:{bucket}/{checkpoint_id}.tar.gz"}}'
'''
            result = self._ssh_exec(ssh_host, ssh_port, cmd, timeout=300)

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            for line in result.stdout.strip().split('\n'):
                if line.startswith('{'):
                    return json.loads(line)

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def download_from_r2(
        self,
        ssh_host: str,
        ssh_port: int,
        checkpoint_id: str,
        r2_bucket: Optional[str] = None
    ) -> Dict:
        """Download checkpoint do Cloudflare R2"""
        bucket = r2_bucket or self._settings.r2_bucket

        try:
            cmd = f'''
mkdir -p /workspace/.gpu-checkpoints &&
cd /workspace/.gpu-checkpoints &&
rclone copy r2:{bucket}/{checkpoint_id}.tar.gz . &&
tar -xzf {checkpoint_id}.tar.gz &&
rm {checkpoint_id}.tar.gz &&
echo '{{"success": true, "checkpoint_id": "{checkpoint_id}"}}'
'''
            result = self._ssh_exec(ssh_host, ssh_port, cmd, timeout=300)

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            for line in result.stdout.strip().split('\n'):
                if line.startswith('{'):
                    return json.loads(line)

            return {'success': True, 'checkpoint_id': checkpoint_id}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _ssh_exec(
        self,
        ssh_host: str,
        ssh_port: int,
        command: str,
        timeout: int = 30,
        user: str = 'root'
    ) -> subprocess.CompletedProcess:
        """Executa comando via SSH"""
        ssh_cmd = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', f'ConnectTimeout={self._settings.ssh_connect_timeout}',
            '-p', str(ssh_port),
            f'{user}@{ssh_host}',
            command
        ]

        return subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )


# Singleton instance
_checkpoint_service: Optional[GPUCheckpointService] = None


def get_checkpoint_service() -> GPUCheckpointService:
    """Retorna instância singleton do serviço"""
    global _checkpoint_service
    if _checkpoint_service is None:
        _checkpoint_service = GPUCheckpointService()
    return _checkpoint_service
