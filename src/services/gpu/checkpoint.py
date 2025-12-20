"""
GPU Checkpoint Service - Checkpoint/Restore de estado GPU (VRAM + processos)

Este servico usa cuda-checkpoint + CRIU para fazer checkpoint de processos
que estao usando a GPU, permitindo restaurar o estado completo da VRAM
em segundos ao inves de minutos (download de modelos).

Arquitetura:
- GPU Machine (RTX 5090) sincroniza em tempo real com Sync Machine
- Sync Machine cria snapshots a cada 30 segundos
- Se GPU cair, restaura do snapshot da Sync Machine (mais rapido)
- R2 serve como backup de longo prazo
"""

import os
import subprocess
import time
import json
import threading
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime


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
    """Servico para checkpoint/restore de estado GPU"""

    # Scripts que serao instalados nas maquinas GPU
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

# Verificar se processo esta vivo
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

# Compilar cuda-checkpoint se nao existe
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

# Criar diretorios
mkdir -p /workspace/.gpu-checkpoints
mkdir -p /opt/dumont/scripts

# Instalar scripts
cat > /opt/dumont/scripts/gpu-checkpoint.sh << 'CHECKPOINT_EOF'
''' + CHECKPOINT_SCRIPT + '''
CHECKPOINT_EOF

cat > /opt/dumont/scripts/gpu-restore.sh << 'RESTORE_EOF'
''' + RESTORE_SCRIPT + '''
RESTORE_EOF

chmod +x /opt/dumont/scripts/*.sh

echo '{"success": true, "driver": "'$DRIVER_VERSION'", "criu": "'$CRIU_VERSION'"}'
'''

    def __init__(self, vast_service=None, restic_service=None):
        self.vast_service = vast_service
        self.restic_service = restic_service
        self._checkpoints: Dict[str, GPUCheckpoint] = {}
        self._lock = threading.Lock()

    def setup_instance(self, instance_id: str, ssh_host: str, ssh_port: int) -> Dict:
        """
        Instala dependencias de checkpoint em uma instancia GPU.

        Args:
            instance_id: ID da instancia vast.ai
            ssh_host: Host SSH
            ssh_port: Porta SSH

        Returns:
            Dict com resultado da instalacao
        """
        try:
            # Executar script de setup via SSH
            result = self._ssh_exec(
                ssh_host, ssh_port,
                f'bash -c "{self.SETUP_SCRIPT}"',
                timeout=300  # 5 minutos para compilar cuda-checkpoint
            )

            if result.returncode != 0:
                return {'success': False, 'error': result.stderr}

            # Tentar parsear JSON do output
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
            instance_id: ID da instancia vast.ai
            ssh_host: Host SSH
            ssh_port: Porta SSH
            checkpoint_id: ID opcional (auto-gerado se nao fornecido)

        Returns:
            Dict com informacoes do checkpoint
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

            # Parsear resultado
            output = result.stdout.strip()
            for line in output.split('\n'):
                if line.startswith('{'):
                    data = json.loads(line)

                    # Criar objeto checkpoint
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

            return {'success': False, 'error': 'Output invalido'}

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
        Restaura um checkpoint em uma instancia.

        Args:
            instance_id: ID da instancia destino
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
                    return {
                        'success': True,
                        'restored_pid': data.get('restored_pid'),
                        'checkpoint_id': checkpoint_id
                    }

            return {'success': False, 'error': 'Output invalido'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def list_checkpoints(
        self,
        instance_id: str,
        ssh_host: str,
        ssh_port: int
    ) -> List[Dict]:
        """Lista checkpoints disponiveis em uma instancia"""
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

    def sync_checkpoint_to_machine(
        self,
        src_ssh_host: str,
        src_ssh_port: int,
        dst_ssh_host: str,
        dst_ssh_port: int,
        checkpoint_id: str
    ) -> Dict:
        """
        Sincroniza checkpoint entre maquinas (GPU -> Sync Machine).

        Args:
            src_*: Maquina origem (GPU)
            dst_*: Maquina destino (Sync)
            checkpoint_id: ID do checkpoint

        Returns:
            Dict com resultado da sincronizacao
        """
        try:
            # Comprimir checkpoint na origem
            compress_cmd = f'''
cd /workspace/.gpu-checkpoints &&
tar -czf {checkpoint_id}.tar.gz {checkpoint_id}/ &&
echo "size=$(stat -c%s {checkpoint_id}.tar.gz)"
'''
            result = self._ssh_exec(src_ssh_host, src_ssh_port, compress_cmd, timeout=120)

            if result.returncode != 0:
                return {'success': False, 'error': f'Compress failed: {result.stderr}'}

            # TODO: Implementar transferencia via rsync ou scp entre maquinas
            # Por enquanto, retornar que precisa de sync machine configurada

            return {
                'success': False,
                'error': 'Sync machine nao configurada - implemente SyncMachineService'
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def upload_to_r2(
        self,
        ssh_host: str,
        ssh_port: int,
        checkpoint_id: str,
        r2_bucket: str = 'dumont-checkpoints'
    ) -> Dict:
        """Upload checkpoint para Cloudflare R2 (backup de longo prazo)"""
        try:
            cmd = f'''
cd /workspace/.gpu-checkpoints &&
tar -czf {checkpoint_id}.tar.gz {checkpoint_id}/ &&
rclone copy {checkpoint_id}.tar.gz r2:{r2_bucket}/ &&
rm {checkpoint_id}.tar.gz &&
echo '{{"success": true, "path": "r2:{r2_bucket}/{checkpoint_id}.tar.gz"}}'
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
            '-o', 'ConnectTimeout=10',
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
_gpu_checkpoint_service: Optional[GPUCheckpointService] = None


def get_gpu_checkpoint_service() -> GPUCheckpointService:
    """Retorna instancia singleton do servico"""
    global _gpu_checkpoint_service
    if _gpu_checkpoint_service is None:
        _gpu_checkpoint_service = GPUCheckpointService()
    return _gpu_checkpoint_service
