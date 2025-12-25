"""
API endpoints para GPU Checkpoint e Sync Machines
"""

from flask import Blueprint, request, jsonify, g
from src.modules.serverless import get_checkpoint_service
from ..services.sync_machine_service import get_sync_machine_service
from ..services.gpu.vast import VastService

# Alias para compatibilidade
get_gpu_checkpoint_service = get_checkpoint_service


gpu_bp = Blueprint('gpu', __name__)


def get_vast_service() -> VastService:
    """Retorna VastService com API key do usuario"""
    api_key = getattr(g, 'vast_api_key', '')
    return VastService(api_key)


# =============================================================================
# GPU CHECKPOINT ENDPOINTS
# =============================================================================

@gpu_bp.route('/gpu/setup/<instance_id>', methods=['POST'])
def setup_gpu_checkpoint(instance_id):
    """
    Instala dependencias de GPU checkpoint em uma instancia.

    POST /api/gpu/setup/<instance_id>

    Instala:
    - CRIU 4.0+
    - cuda-checkpoint
    - Scripts de checkpoint/restore
    """
    vast = get_vast_service()
    instance = vast.get_instance_status(instance_id)

    if not instance:
        return jsonify({'error': 'Instancia nao encontrada'}), 404

    ssh_host = instance.get('ssh_host')
    ssh_port = instance.get('ssh_port')

    if not ssh_host or not ssh_port:
        return jsonify({'error': 'SSH nao disponivel'}), 400

    service = get_gpu_checkpoint_service()
    result = service.setup_instance(instance_id, ssh_host, ssh_port)

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@gpu_bp.route('/gpu/checkpoint/<instance_id>', methods=['POST'])
def create_checkpoint(instance_id):
    """
    Cria um checkpoint do estado GPU atual.

    POST /api/gpu/checkpoint/<instance_id>
    Body (opcional): {"checkpoint_id": "meu-checkpoint"}

    Retorna:
    - checkpoint_id: ID do checkpoint criado
    - size_bytes: Tamanho do checkpoint
    - vram_gb: VRAM usada pelo processo
    """
    vast = get_vast_service()
    instance = vast.get_instance_status(instance_id)

    if not instance:
        return jsonify({'error': 'Instancia nao encontrada'}), 404

    ssh_host = instance.get('ssh_host')
    ssh_port = instance.get('ssh_port')

    if not ssh_host or not ssh_port:
        return jsonify({'error': 'SSH nao disponivel'}), 400

    data = request.get_json() or {}
    checkpoint_id = data.get('checkpoint_id')

    service = get_gpu_checkpoint_service()
    result = service.create_checkpoint(instance_id, ssh_host, ssh_port, checkpoint_id)

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@gpu_bp.route('/gpu/restore/<instance_id>', methods=['POST'])
def restore_checkpoint(instance_id):
    """
    Restaura um checkpoint em uma instancia.

    POST /api/gpu/restore/<instance_id>
    Body: {"checkpoint_id": "gpu-xxx-timestamp"}
    """
    vast = get_vast_service()
    instance = vast.get_instance_status(instance_id)

    if not instance:
        return jsonify({'error': 'Instancia nao encontrada'}), 404

    ssh_host = instance.get('ssh_host')
    ssh_port = instance.get('ssh_port')

    if not ssh_host or not ssh_port:
        return jsonify({'error': 'SSH nao disponivel'}), 400

    data = request.get_json() or {}
    checkpoint_id = data.get('checkpoint_id')

    if not checkpoint_id:
        return jsonify({'error': 'checkpoint_id obrigatorio'}), 400

    service = get_gpu_checkpoint_service()
    result = service.restore_checkpoint(instance_id, ssh_host, ssh_port, checkpoint_id)

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@gpu_bp.route('/gpu/checkpoints/<instance_id>', methods=['GET'])
def list_checkpoints(instance_id):
    """
    Lista checkpoints disponiveis em uma instancia.

    GET /api/gpu/checkpoints/<instance_id>
    """
    vast = get_vast_service()
    instance = vast.get_instance_status(instance_id)

    if not instance:
        return jsonify({'error': 'Instancia nao encontrada'}), 404

    ssh_host = instance.get('ssh_host')
    ssh_port = instance.get('ssh_port')

    if not ssh_host or not ssh_port:
        return jsonify({'error': 'SSH nao disponivel'}), 400

    service = get_gpu_checkpoint_service()
    checkpoints = service.list_checkpoints(instance_id, ssh_host, ssh_port)

    return jsonify({'checkpoints': checkpoints})


@gpu_bp.route('/gpu/upload-r2/<instance_id>', methods=['POST'])
def upload_checkpoint_r2(instance_id):
    """
    Faz upload de um checkpoint para Cloudflare R2.

    POST /api/gpu/upload-r2/<instance_id>
    Body: {"checkpoint_id": "gpu-xxx-timestamp"}
    """
    vast = get_vast_service()
    instance = vast.get_instance_status(instance_id)

    if not instance:
        return jsonify({'error': 'Instancia nao encontrada'}), 404

    ssh_host = instance.get('ssh_host')
    ssh_port = instance.get('ssh_port')

    if not ssh_host or not ssh_port:
        return jsonify({'error': 'SSH nao disponivel'}), 400

    data = request.get_json() or {}
    checkpoint_id = data.get('checkpoint_id')

    if not checkpoint_id:
        return jsonify({'error': 'checkpoint_id obrigatorio'}), 400

    service = get_gpu_checkpoint_service()
    result = service.upload_to_r2(ssh_host, ssh_port, checkpoint_id)

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


# =============================================================================
# SYNC MACHINE ENDPOINTS
# =============================================================================

@gpu_bp.route('/sync-machines', methods=['GET'])
def list_sync_machines():
    """
    Lista todas as sync machines.

    GET /api/sync-machines
    """
    service = get_sync_machine_service()
    machines = service.list_machines()
    return jsonify({'machines': machines})


@gpu_bp.route('/sync-machines', methods=['POST'])
def create_sync_machine():
    """
    Cria uma sync machine para uma instancia GPU.

    POST /api/sync-machines
    Body: {
        "gpu_instance_id": "12345",
        "provider": "gcp" | "vastai",
        "gpu_region": "Utah, US"
    }
    """
    data = request.get_json() or {}

    gpu_instance_id = data.get('gpu_instance_id')
    provider = data.get('provider', 'gcp')
    gpu_region = data.get('gpu_region', 'US')

    if not gpu_instance_id:
        return jsonify({'error': 'gpu_instance_id obrigatorio'}), 400

    service = get_sync_machine_service()

    if provider == 'gcp':
        result = service.create_gcp_machine(
            gpu_instance_id=gpu_instance_id,
            gpu_region=gpu_region
        )
    elif provider == 'vastai':
        vast_api_key = getattr(g, 'vast_api_key', '')
        if not vast_api_key:
            return jsonify({'error': 'vast_api_key nao configurada'}), 400

        result = service.create_vastai_cpu_machine(
            gpu_instance_id=gpu_instance_id,
            gpu_region=gpu_region,
            vast_api_key=vast_api_key
        )
    else:
        return jsonify({'error': f'Provider invalido: {provider}'}), 400

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@gpu_bp.route('/sync-machines/<sync_id>', methods=['GET'])
def get_sync_machine(sync_id):
    """
    Retorna informacoes de uma sync machine.

    GET /api/sync-machines/<sync_id>
    """
    service = get_sync_machine_service()
    machine = service.get_machine(sync_id)

    if not machine:
        return jsonify({'error': 'Sync machine nao encontrada'}), 404

    return jsonify({
        'sync_id': machine.sync_id,
        'provider': machine.provider,
        'region': machine.region,
        'zone': machine.zone,
        'ip_address': machine.ip_address,
        'status': machine.status,
        'gpu_instance_id': machine.gpu_instance_id,
        'last_sync': machine.last_sync,
        'snapshots': machine.snapshots
    })


@gpu_bp.route('/sync-machines/<sync_id>', methods=['DELETE'])
def delete_sync_machine(sync_id):
    """
    Destroi uma sync machine.

    DELETE /api/sync-machines/<sync_id>
    """
    service = get_sync_machine_service()
    result = service.destroy_machine(sync_id)

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@gpu_bp.route('/sync-machines/<sync_id>/start-sync', methods=['POST'])
def start_sync(sync_id):
    """
    Inicia sincronizacao continua entre GPU e Sync Machine.

    POST /api/sync-machines/<sync_id>/start-sync
    Body: {
        "gpu_instance_id": "12345",
        "source_path": "/workspace",
        "interval_seconds": 30
    }
    """
    data = request.get_json() or {}

    gpu_instance_id = data.get('gpu_instance_id')
    source_path = data.get('source_path', '/workspace')
    interval = data.get('interval_seconds', 30)

    if not gpu_instance_id:
        return jsonify({'error': 'gpu_instance_id obrigatorio'}), 400

    # Obter SSH da GPU
    vast = get_vast_service()
    instance = vast.get_instance_status(gpu_instance_id)

    if not instance:
        return jsonify({'error': 'GPU nao encontrada'}), 404

    ssh_host = instance.get('ssh_host')
    ssh_port = instance.get('ssh_port')

    if not ssh_host or not ssh_port:
        return jsonify({'error': 'SSH da GPU nao disponivel'}), 400

    service = get_sync_machine_service()
    result = service.start_continuous_sync(
        sync_id=sync_id,
        gpu_ssh_host=ssh_host,
        gpu_ssh_port=ssh_port,
        source_path=source_path,
        interval_seconds=interval
    )

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@gpu_bp.route('/sync-machines/<sync_id>/stop-sync', methods=['POST'])
def stop_sync(sync_id):
    """
    Para sincronizacao continua.

    POST /api/sync-machines/<sync_id>/stop-sync
    """
    service = get_sync_machine_service()
    result = service.stop_continuous_sync(sync_id)

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500
