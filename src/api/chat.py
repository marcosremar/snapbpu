from flask import Blueprint, jsonify, request, g
from src.services.gpu.vast import VastService

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

from src.config import settings
import json
import os

def get_vast_service() -> VastService:
    """Factory para criar VastService com API key do usuario"""
    api_key = getattr(g, 'vast_api_key', '')
    
    # Fallback: se nao tiver API key na sessao, tentar carregar do config.json (primeiro usuario)
    if not api_key:
        try:
            # Caminho para config.json (raiz do projeto)
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(root_dir, 'config.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    users = config.get('users', {})
                    # Tentar marcosremar ou o primeiro disponivel
                    if 'marcosremar@gmail.com' in users:
                        api_key = users['marcosremar@gmail.com'].get('vast_api_key')
                    elif users:
                        first_user = next(iter(users.values()))
                        api_key = first_user.get('vast_api_key')
        except Exception as e:
            print(f"Erro ao carregar fallback API key: {e}")

    return VastService(api_key)

@chat_bp.route('/models', methods=['GET'])
def list_models():
    """
    Lista modelos disponiveis para chat.
    Retorna todas as instancias rodando que podem ter um LLM.
    """
    vast = get_vast_service()
    if not vast.api_key:
        return jsonify({'error': 'API key nao configurada'}), 400

    try:
        instances = vast.get_my_instances()
        
        models = []
        for inst in instances:
            # Filtrar apenas instancias rodando e com IP publico
            status = inst.get('actual_status') or inst.get('status')
            if status != 'running':
                continue
                
            public_ip = inst.get('public_ipaddr')
            ports = inst.get('ports', {})
            
            if not public_ip:
                continue

            # Verificar se tem portas relevantes mapeadas
            # 11434 = Ollama, 8000 = vLLM/FastAPI, 5000 = Flask/Oobabooga, 7860 = Gradio
            mapped_ports = []
            ollama_url = None
            
            # Checar porta 11434 (Ollama)
            ollama_port_map = ports.get('11434/tcp')
            if ollama_port_map:
                host_port = ollama_port_map[0].get('HostPort')
                if host_port:
                    ollama_url = f"http://{public_ip}:{host_port}"
                    mapped_ports.append({'port': 11434, 'url': ollama_url, 'type': 'ollama'})

            # Checar outras portas comuns se Ollama nao for encontrado ou para dar opcoes
            # (Simplificacao: vamos assumir que se tem 11434, e Ollama. Se nao, listamos a maquina como generica)
            
            models.append({
                'id': inst.get('id'),
                'name': f"Instance {inst.get('id')} ({inst.get('gpu_name')})",
                'gpu': inst.get('gpu_name'),
                'status': status,
                'ip': public_ip,
                'ports': ports, # Raw ports info
                'ollama_url': ollama_url, # URL especifica do Ollama se disponivel
                'ssh_host': inst.get('ssh_host'),
                'ssh_port': inst.get('ssh_port'),
            })

        return jsonify({'models': models})

    except Exception as e:
        print(f"Erro ao listar models: {e}")
        return jsonify({'error': str(e)}), 500
