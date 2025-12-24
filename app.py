#!/usr/bin/env python3
"""
Dumont Cloud - GPU Cloud Manager
Aplicacao principal Flask
"""
import os
import sys
import json
from flask import Flask, g, session, redirect, url_for, request, Response, jsonify
from flask_cors import CORS
from functools import wraps
import requests

# Adiciona src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from src.api import snapshots_bp, instances_bp
from src.api.deploy import deploy_bp
from src.api.gpu_checkpoints import gpu_bp
from src.api.price_reports import price_reports_bp
from src.api.snapshots_ans import snapshots_ans_bp
from src.api.hibernation import hibernation_bp
from src.api.cpu_standby import cpu_standby_bp, init_standby_service
from src.api.chat import chat_bp


def create_app():
    """Factory function para criar a aplicacao Flask"""
    # Disable automatic static route - we'll handle everything in catchall
    app = Flask(__name__, static_folder=None)
    app.secret_key = settings.app.secret_key

    # Cookie de sessao valido para todos os subdominios
    app.config['SESSION_COOKIE_DOMAIN'] = '.dumontcloud.com'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = True

    # CORS para desenvolvimento
    CORS(app, supports_credentials=True)

    # Registrar blueprints da API
    app.register_blueprint(snapshots_bp)
    app.register_blueprint(snapshots_ans_bp)
    app.register_blueprint(hibernation_bp)
    app.register_blueprint(instances_bp)
    app.register_blueprint(deploy_bp)
    app.register_blueprint(gpu_bp)
    app.register_blueprint(price_reports_bp)
    app.register_blueprint(cpu_standby_bp)
    app.register_blueprint(chat_bp)

    # Inicializar sistema de agentes
    def init_agents():
        """Inicializa agentes automaticos (monitoramento de precos, auto-hibernacao, etc)."""
        import logging
        import os
        from src.services.agent_manager import agent_manager
        from src.services.price_monitor_agent import PriceMonitorAgent
        from src.services.standby import AutoHibernationManager

        logger = logging.getLogger(__name__)
        logger.info("Inicializando agentes automaticos...")

        # Carregar config do primeiro usuario para obter API key
        config = load_user_config()
        vast_api_key = None
        for user_data in config.get('users', {}).values():
            vast_api_key = user_data.get('vast_api_key')
            if vast_api_key:
                break

        if vast_api_key:
            # Registrar agente de monitoramento de precos
            try:
                agent_manager.register_agent(
                    PriceMonitorAgent,
                    vast_api_key=vast_api_key,
                    interval_minutes=30,
                    gpus_to_monitor=['RTX 4090', 'RTX 4080']
                )
                logger.info("✓ Agente de monitoramento de precos iniciado (RTX 4090, RTX 4080)")
            except Exception as e:
                logger.error(f"Erro ao iniciar agente de monitoramento: {e}")

            # Registrar agente de auto-hibernacao
            try:
                r2_endpoint = os.getenv('R2_ENDPOINT', 'https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com')
                r2_bucket = os.getenv('R2_BUCKET', 'musetalk')
                
                # Carregar credenciais TensorDock do primeiro usuário
                tensordock_auth_id = None
                tensordock_api_token = None
                gcp_credentials = None
                
                for user_data in config.get('users', {}).values():
                    if not tensordock_auth_id and user_data.get('tensordock_auth_id'):
                        tensordock_auth_id = user_data.get('tensordock_auth_id')
                        tensordock_api_token = user_data.get('tensordock_api_token')
                    if not gcp_credentials and user_data.get('settings', {}).get('gcp_credentials'):
                        gcp_credentials = user_data.get('settings', {}).get('gcp_credentials')

                hibernation_manager = agent_manager.register_agent(
                    AutoHibernationManager,
                    vast_api_key=vast_api_key,
                    r2_endpoint=r2_endpoint,
                    r2_bucket=r2_bucket,
                    check_interval=30,
                    tensordock_auth_id=tensordock_auth_id,
                    tensordock_api_token=tensordock_api_token,
                    gcp_credentials=gcp_credentials,
                )

                # Salvar referência no app para uso nos endpoints
                app.hibernation_manager = hibernation_manager

                logger.info("✓ Agente de auto-hibernacao iniciado (check_interval=30s)")
            except Exception as e:
                logger.error(f"Erro ao iniciar agente de auto-hibernacao: {e}")

            # Inicializar CPU Standby Service (GCP)
            try:
                gcp_creds_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'credentials', 'gcp-service-account.json'
                )
                if os.path.exists(gcp_creds_path):
                    with open(gcp_creds_path, 'r') as f:
                        gcp_credentials = json.load(f)

                    standby_service = init_standby_service(
                        vast_api_key=vast_api_key,
                        gcp_credentials=gcp_credentials,
                        config={
                            'gcp_zone': 'europe-west1-b',
                            'gcp_machine_type': 'e2-medium',
                            'gcp_disk_size': 100,
                            'sync_interval': 30,
                        }
                    )

                    # Salvar referência no app
                    app.cpu_standby_service = standby_service
                    logger.info("✓ CPU Standby service inicializado (GCP europe-west1-b)")
                else:
                    logger.warning("GCP credentials not found - CPU Standby disabled")
            except Exception as e:
                logger.error(f"Erro ao iniciar CPU Standby service: {e}")
        else:
            logger.warning("Nenhuma API key configurada - agentes nao iniciados")

    # Shutdown handler para parar agentes
    import atexit
    def shutdown_agents():
        """Para todos os agentes ao desligar o servidor."""
        import logging
        from src.services.agent_manager import agent_manager
        logger = logging.getLogger(__name__)
        logger.info("Parando agentes...")
        agent_manager.stop_all()
        logger.info("Agentes parados")

    atexit.register(shutdown_agents)

    # Inicializar agentes apos criar app (mas antes de retornar)
    # Vamos fazer isso no final, antes do return
    app._init_agents = init_agents

    # Carregar config de usuarios
    def load_user_config():
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            settings.app.config_file
        )
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"users": {}}

    def save_user_config(config):
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            settings.app.config_file
        )
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

    # Usuarios carregados do config.json
    def get_users():
        config = load_user_config()
        return config.get('users', {})

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Modo demo - bypass authentication using marcosremar@gmail.com
            if os.getenv('DEMO_MODE', 'false').lower() == 'true' or request.args.get('demo') == 'true':
                if 'user' not in session:
                    session['user'] = 'marcosremar@gmail.com'
                return f(*args, **kwargs)

            if 'user' not in session:
                if request.path.startswith('/api/'):
                    return {"error": "Nao autenticado"}, 401
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated

    @app.before_request
    def before_request():
        """Carrega dados do usuario antes de cada request"""
        if 'user' in session:
            config = load_user_config()
            user_data = config.get('users', {}).get(session['user'], {})
            g.vast_api_key = user_data.get('vast_api_key', '')
            g.user_settings = user_data.get('settings', {})

    # ========== AUTH ROUTES ==========

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        import hashlib
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        users = get_users()
        if username in users:
            stored_hash = users[username].get('password', '')
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if stored_hash == password_hash:
                session['user'] = username
                return {"success": True, "user": username}
        return {"error": "Usuario ou senha incorretos"}, 401

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        session.pop('user', None)
        return {"success": True}

    @app.route('/api/auth/me')
    def api_me():
        if 'user' in session:
            return {"user": session['user'], "authenticated": True}
        return {"authenticated": False}

    @app.route('/api/auth/validate')
    def api_auth_validate():
        """Endpoint para nginx auth_request - valida sessao do usuario"""
        if 'user' in session:
            return '', 200  # Autenticado - nginx permite acesso
        return '', 401  # Nao autenticado - nginx bloqueia

    # ========== LATENCY ROUTES ==========

    @app.route('/api/latency')
    def measure_latency():
        """Mede latencia para endpoints representativos de cada regiao"""
        import subprocess
        import time

        # Endpoints representativos para cada regiao (servidores de CDN/cloud)
        region_endpoints = {
            'US': ['1.1.1.1', '8.8.8.8'],  # Cloudflare US, Google US
            'EU': ['1.0.0.1', '9.9.9.9'],  # Cloudflare EU, Quad9 EU
            'ASIA': ['168.63.129.16', '223.5.5.5'],  # Azure Asia, Alibaba DNS
        }

        results = {}
        for region, endpoints in region_endpoints.items():
            latencies = []
            for endpoint in endpoints:
                try:
                    # Fazer 2 pings rapidos
                    start = time.time()
                    result = subprocess.run(
                        ['ping', '-c', '2', '-W', '2', endpoint],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    elapsed = (time.time() - start) * 1000 / 2  # Media em ms

                    # Extrair tempo do output do ping
                    output = result.stdout
                    if 'time=' in output:
                        # Extrair ultimo tempo (mais preciso)
                        import re
                        times = re.findall(r'time=(\d+\.?\d*)', output)
                        if times:
                            latencies.append(float(times[-1]))
                        else:
                            latencies.append(elapsed)
                    elif result.returncode == 0:
                        latencies.append(elapsed)
                except Exception as e:
                    continue

            if latencies:
                results[region] = {
                    'latency': round(min(latencies), 1),
                    'unit': 'ms'
                }
            else:
                results[region] = {
                    'latency': None,
                    'error': 'timeout'
                }

        return jsonify(results)

    # ========== SETTINGS ROUTES ==========

    @app.route('/api/settings', methods=['GET'])
    @login_required
    def get_settings():
        config = load_user_config()
        user_data = config.get('users', {}).get(session['user'], {})
        return {
            "vast_api_key": user_data.get('vast_api_key', ''),
            "settings": user_data.get('settings', {})
        }

    @app.route('/api/settings', methods=['PUT'])
    @login_required
    def update_settings():
        data = request.get_json()
        config = load_user_config()

        if 'users' not in config:
            config['users'] = {}
        if session['user'] not in config['users']:
            config['users'][session['user']] = {}

        if 'vast_api_key' in data:
            config['users'][session['user']]['vast_api_key'] = data['vast_api_key']

        if 'settings' in data:
            config['users'][session['user']]['settings'] = data['settings']

        save_user_config(config)
        return {"success": True}

    # ========== AGENT SETTINGS ROUTES ==========

    @app.route('/api/settings/agent', methods=['GET'])
    @login_required
    def get_agent_settings():
        """Retorna configuracoes do DumontAgent"""
        config = load_user_config()
        user_data = config.get('users', {}).get(session['user'], {})
        agent_settings = user_data.get('agent_settings', {
            'sync_interval': 30,
            'keep_last': 10,
        })
        return jsonify(agent_settings)

    @app.route('/api/settings/agent', methods=['PUT'])
    @login_required
    def update_agent_settings():
        """Atualiza configuracoes do DumontAgent"""
        data = request.get_json()

        # Validacoes
        sync_interval = int(data.get('sync_interval', 30))
        keep_last = int(data.get('keep_last', 10))

        if sync_interval < 10:
            return jsonify({'error': 'Intervalo minimo e 10 segundos'}), 400
        if sync_interval > 3600:
            return jsonify({'error': 'Intervalo maximo e 1 hora (3600 segundos)'}), 400
        if keep_last < 1:
            return jsonify({'error': 'Deve manter ao menos 1 snapshot'}), 400
        if keep_last > 100:
            return jsonify({'error': 'Maximo de 100 snapshots'}), 400

        # Salvar
        config = load_user_config()
        if 'users' not in config:
            config['users'] = {}
        if session['user'] not in config['users']:
            config['users'][session['user']] = {}

        config['users'][session['user']]['agent_settings'] = {
            'sync_interval': sync_interval,
            'keep_last': keep_last,
        }
        save_user_config(config)

        return jsonify({
            'success': True,
            'sync_interval': sync_interval,
            'keep_last': keep_last,
        })

    @app.route('/api/agent/status', methods=['POST'])
    def receive_agent_status():
        """Recebe status do DumontAgent (enviado pelas maquinas GPU)"""
        data = request.get_json()
        instance_id = data.get('instance_id')

        if not instance_id:
            return jsonify({'error': 'instance_id obrigatorio'}), 400

        # Armazenar status em memoria (pode ser movido para Redis/DB depois)
        if not hasattr(app, 'agent_statuses'):
            app.agent_statuses = {}

        app.agent_statuses[str(instance_id)] = {
            **data,
            'received_at': __import__('datetime').datetime.now().isoformat(),
        }

        # Integrar com AutoHibernationManager se disponível
        if hasattr(app, 'hibernation_manager'):
            try:
                gpu_utilization = data.get('gpu_utilization', 0)
                app.hibernation_manager.update_instance_status(
                    instance_id=instance_id,
                    gpu_utilization=gpu_utilization
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Erro ao atualizar status no hibernation manager: {e}")

        return jsonify({'success': True})

    @app.route('/api/agent/status/<instance_id>', methods=['GET'])
    @login_required
    def get_agent_status(instance_id):
        """Retorna status de um agente especifico"""
        if not hasattr(app, 'agent_statuses'):
            return jsonify({'error': 'Nenhum status disponivel'}), 404

        status = app.agent_statuses.get(str(instance_id))
        if not status:
            return jsonify({'error': f'Agente {instance_id} nao encontrado'}), 404

        return jsonify(status)

    @app.route('/api/agent/statuses', methods=['GET'])
    @login_required
    def get_all_agent_statuses():
        """Retorna status de todos os agentes"""
        if not hasattr(app, 'agent_statuses'):
            return jsonify({'agents': {}})

        return jsonify({'agents': app.agent_statuses})

    # ========== CPU STANDBY ROUTES ==========

    @app.route('/api/standby/status', methods=['GET'])
    @login_required
    def get_standby_status():
        """Retorna status do sistema de CPU Standby"""
        if not hasattr(app, 'cpu_standby_service'):
            return jsonify({
                'enabled': False,
                'message': 'CPU Standby service nao inicializado'
            })

        return jsonify(app.cpu_standby_service.get_status())

    @app.route('/api/standby/enable', methods=['POST'])
    @login_required
    def enable_standby():
        """Ativa o sistema de CPU Standby para o usuario"""
        from src.services.cpu_standby_service import CPUStandbyService, CPUStandbyConfig

        api_key = getattr(g, 'vast_api_key', '')
        if not api_key:
            return jsonify({'error': 'API key nao configurada'}), 400

        # Criar/obter instancia do servico
        if not hasattr(app, 'cpu_standby_service'):
            config = CPUStandbyConfig()
            app.cpu_standby_service = CPUStandbyService(api_key, config)

        # Provisionar CPU standby
        instance_id = app.cpu_standby_service.provision_cpu_standby(session['user'])

        if instance_id:
            # Iniciar monitoramento
            app.cpu_standby_service.start_monitoring()
            return jsonify({
                'success': True,
                'cpu_standby_instance': instance_id,
                'message': 'CPU Standby provisionada. Aguardando ficar pronta...'
            })
        else:
            return jsonify({
                'error': 'Falha ao provisionar CPU Standby',
                'hint': 'Verifique se ha ofertas disponiveis na regiao'
            }), 500

    @app.route('/api/standby/disable', methods=['POST'])
    @login_required
    def disable_standby():
        """Desativa o sistema de CPU Standby"""
        if not hasattr(app, 'cpu_standby_service'):
            return jsonify({'error': 'CPU Standby nao esta ativo'}), 400

        app.cpu_standby_service.stop_monitoring()
        return jsonify({'success': True, 'message': 'CPU Standby desativado'})

    @app.route('/api/standby/register-gpu', methods=['POST'])
    @login_required
    def register_gpu_for_standby():
        """Registra uma GPU no sistema de monitoramento para failover"""
        from src.services.cpu_standby_service import CPUStandbyService, CPUStandbyConfig

        data = request.get_json()
        instance_id = data.get('instance_id')
        is_interruptible = data.get('is_interruptible', True)

        if not instance_id:
            return jsonify({'error': 'instance_id obrigatorio'}), 400

        api_key = getattr(g, 'vast_api_key', '')
        if not api_key:
            return jsonify({'error': 'API key nao configurada'}), 400

        # Criar servico se nao existir
        if not hasattr(app, 'cpu_standby_service'):
            config = CPUStandbyConfig()
            app.cpu_standby_service = CPUStandbyService(api_key, config)

        # Registrar GPU
        success = app.cpu_standby_service.register_gpu_instance(instance_id, is_interruptible)

        if success:
            # Iniciar monitoramento se ainda nao estiver rodando
            app.cpu_standby_service.start_monitoring()
            return jsonify({
                'success': True,
                'instance_id': instance_id,
                'is_interruptible': is_interruptible,
                'message': 'GPU registrada para monitoramento de failover'
            })
        else:
            return jsonify({'error': 'Falha ao registrar GPU'}), 500

    @app.route('/api/standby/active-endpoint', methods=['GET'])
    @login_required
    def get_active_endpoint():
        """Retorna o endpoint ativo atual (GPU ou CPU fallback)"""
        if not hasattr(app, 'cpu_standby_service'):
            return jsonify({
                'error': 'CPU Standby nao configurado',
                'hint': 'Use /api/standby/enable para ativar'
            }), 400

        endpoint = app.cpu_standby_service.get_active_endpoint()
        if endpoint:
            return jsonify(endpoint)
        else:
            return jsonify({
                'error': 'Nenhuma maquina ativa',
                'hint': 'Registre uma GPU com /api/standby/register-gpu'
            }), 404

    # ========== DOCUMENTATION API ROUTES ==========

    @app.route('/api/docs/menu')
    def docs_menu():
        """Returns the documentation directory structure as JSON for the sidebar"""
        import os
        import json

        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Live-Doc', 'content')

        def get_menu_structure(path):
            """
            Recursively scans the documentation directory to build the menu structure.
            Returns a list of dicts: {name: str, type: 'file'|'dir', path: str, children: []}
            """
            items = []
            if not os.path.exists(path):
                return items

            for entry in sorted(os.listdir(path)):
                if entry.startswith('.'):
                    continue

                full_path = os.path.join(path, entry)
                relative_path = os.path.relpath(full_path, docs_dir)

                if os.path.isdir(full_path):
                    items.append({
                        "name": entry,
                        "type": "dir",
                        "path": relative_path,
                        "children": get_menu_structure(full_path)
                    })
                elif entry.endswith(".md"):
                    # Remove extension for display, keep relative path for ID
                    display_name = os.path.splitext(entry)[0].replace('_', ' ')
                    items.append({
                        "name": display_name,
                        "type": "file",
                        "path": relative_path,  # e.g., "Strategy/Marketing_Plan.md"
                        "id": relative_path     # used for fetching content
                    })

            return items

        return jsonify({"menu": get_menu_structure(docs_dir)})

    @app.route('/api/docs/content/<path:doc_path>')
    def docs_content(doc_path: str):
        """Fetches documentation content by relative path"""
        import os

        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Live-Doc', 'content')

        # Security: Prevent directory traversal
        safe_path = os.path.normpath(os.path.join(docs_dir, doc_path))
        if not safe_path.startswith(docs_dir):
            return jsonify({"error": "Access denied"}), 403

        if os.path.exists(safe_path) and os.path.isfile(safe_path):
            with open(safe_path, "r", encoding="utf-8") as f:
                return jsonify({"content": f.read()})

        return jsonify({"error": "Document not found"}), 404

    # ========== FRONTEND ROUTES ==========

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        import hashlib
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            users = get_users()
            if username in users:
                stored_hash = users[username].get('password', '')
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if stored_hash == password_hash:
                    session['user'] = username
                    return redirect('/')
        # Retorna pagina de login simples (sera substituida pelo React)
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Dumont Cloud Login</title>
        <style>
            body { font-family: system-ui; background: #0d1117; color: #c9d1d9; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
            .login { background: #161b22; padding: 40px; border-radius: 12px; border: 1px solid #30363d; width: 320px; }
            .logo { text-align: center; font-size: 1.8em; font-weight: 700; color: #58a6ff; margin-bottom: 24px; }
            input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #30363d; border-radius: 6px; background: #0d1117; color: #c9d1d9; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #238636; border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer; margin-top: 16px; }
            button:hover { background: #2ea043; }
        </style>
        </head>
        <body>
            <form class="login" method="POST">
                <div class="logo">Dumont Cloud</div>
                <input name="username" placeholder="Usuario" required>
                <input name="password" type="password" placeholder="Senha" required>
                <button type="submit">Entrar</button>
            </form>
        </body>
        </html>
        '''

    @app.route('/logout')
    def logout():
        session.pop('user', None)
        return redirect('/login')

    # ========== PORT PROXY ROUTES ==========

    @app.route('/api/instances/<int:instance_id>/ports')
    @login_required
    def get_instance_ports(instance_id: int):
        """Lista portas disponiveis e configuradas para uma instancia (Docker + nginx custom)"""
        from src.services import VastService
        import glob as glob_module

        api_key = getattr(g, 'vast_api_key', '')
        vast = VastService(api_key)

        status = vast.get_instance_status(instance_id)
        if status.get('status') == 'error':
            return jsonify({'error': 'Instancia nao encontrada'}), 404

        ports = status.get('ports', {})
        public_ip = status.get('public_ipaddr')

        # Portas comuns com descricao
        common_ports = {
            '22/tcp': 'SSH',
            '8080/tcp': 'VS Code / Code Server',
            '8888/tcp': 'Jupyter Notebook',
            '6006/tcp': 'TensorBoard',
            '3000/tcp': 'Dev Server',
            '5000/tcp': 'Flask/API',
            '7860/tcp': 'Gradio',
            '8501/tcp': 'Streamlit',
        }

        available_ports = []
        docker_ports_set = set()  # Track which ports came from Docker

        # 1. Primeiro, adicionar portas do Docker (Vast API)
        for port_key, mappings in ports.items():
            if mappings and len(mappings) > 0:
                host_port = mappings[0].get('HostPort')
                container_port = port_key.split('/')[0]
                description = common_ports.get(port_key, f'Port {port_key}')
                docker_ports_set.add(container_port)
                available_ports.append({
                    'container_port': port_key,
                    'host_port': host_port,
                    'public_ip': public_ip,
                    'description': description,
                    'direct_url': f'http://{public_ip}:{host_port}' if public_ip and host_port else None,
                    'proxy_url': f'https://dumontcloud.com/p/{instance_id}/{container_port}/' if host_port else None,
                    'subdomain_url': f'https://{instance_id}-{container_port}.dumontcloud.com' if host_port else None,
                })

        # 2. Depois, adicionar portas customizadas do nginx (que nao estao no Docker)
        nginx_pattern = f"{NGINX_CONF_DIR}/auto_{instance_id}-*.conf"
        nginx_configs = glob_module.glob(nginx_pattern)

        for config in nginx_configs:
            filename = os.path.basename(config)
            # auto_28864630-3434.conf -> 3434
            parts = filename.replace('auto_', '').replace('.conf', '').split('-')
            if len(parts) == 2:
                custom_port = parts[1]
                # So adicionar se NAO veio do Docker (evitar duplicatas)
                if custom_port not in docker_ports_set:
                    available_ports.append({
                        'container_port': f'{custom_port}/tcp',
                        'host_port': custom_port,  # Para portas custom, host_port = container_port
                        'public_ip': public_ip,
                        'description': f'Custom Port {custom_port}',
                        'direct_url': f'http://{public_ip}:{custom_port}' if public_ip else None,
                        'proxy_url': f'https://dumontcloud.com/p/{instance_id}/{custom_port}/' if public_ip else None,
                        'subdomain_url': f'https://{instance_id}-{custom_port}.dumontcloud.com',
                        'is_custom': True,  # Marcar como porta customizada
                    })

        return jsonify({
            'instance_id': instance_id,
            'status': status.get('status'),
            'public_ip': public_ip,
            'ports': available_ports,
        })

    # ========== VM PROXY ROUTE ==========
    # Cache de info de instancias para proxy por subdominio
    instance_cache = {}

    # ========== DYNAMIC NGINX CONFIG FOR PORT EXPOSURE ==========
    NGINX_CONF_DIR = '/etc/nginx/conf.d'
    NGINX_TEMPLATE = '''# Auto-generated config for {subdomain}
server {{
    server_name {subdomain}.dumontcloud.com;

    location / {{
        proxy_pass http://{backend_ip}:{backend_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_buffering off;
        proxy_cache off;
    }}

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/dumontcloud.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dumontcloud.com/privkey.pem;
}}
'''

    def register_nginx_subdomain(subdomain: str, backend_ip: str, backend_port: int) -> dict:
        """
        Registra um novo subdomain no nginx com WebSocket support.
        Cria arquivo de config e recarrega nginx.
        """
        import subprocess

        config_file = f"{NGINX_CONF_DIR}/auto_{subdomain}.conf"
        config_content = NGINX_TEMPLATE.format(
            subdomain=subdomain,
            backend_ip=backend_ip,
            backend_port=backend_port
        )

        try:
            # Escrever config via sudo tee
            process = subprocess.run(
                ['sudo', 'tee', config_file],
                input=config_content.encode(),
                capture_output=True,
                timeout=10
            )
            if process.returncode != 0:
                return {'error': f'Falha ao criar config: {process.stderr.decode()}'}

            # Testar config do nginx
            test = subprocess.run(['sudo', 'nginx', '-t'], capture_output=True, timeout=10)
            if test.returncode != 0:
                # Remover config invalido
                subprocess.run(['sudo', 'rm', '-f', config_file], timeout=5)
                return {'error': f'Config nginx invalido: {test.stderr.decode()}'}

            # Recarregar nginx
            reload = subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], capture_output=True, timeout=10)
            if reload.returncode != 0:
                return {'error': f'Falha ao recarregar nginx: {reload.stderr.decode()}'}

            return {
                'success': True,
                'subdomain': f'{subdomain}.dumontcloud.com',
                'url': f'https://{subdomain}.dumontcloud.com',
                'backend': f'{backend_ip}:{backend_port}'
            }

        except subprocess.TimeoutExpired:
            return {'error': 'Timeout ao configurar nginx'}
        except Exception as e:
            return {'error': str(e)}

    def check_nginx_subdomain_exists(subdomain: str) -> bool:
        """Verifica se um subdomain ja esta configurado no nginx"""
        import subprocess
        config_file = f"{NGINX_CONF_DIR}/auto_{subdomain}.conf"
        result = subprocess.run(['test', '-f', config_file], capture_output=True)
        return result.returncode == 0

    @app.route('/api/port-proxy/register', methods=['POST'])
    @login_required
    def register_port_proxy():
        """
        Registra dinamicamente uma nova porta para exposicao via subdomain.
        POST /api/port-proxy/register
        Body: {"instance_id": 28864630, "port": 5050}

        Retorna URL do subdomain configurado com WebSocket support.
        """
        from src.services import VastService

        data = request.get_json()
        instance_id = data.get('instance_id')
        target_port = data.get('port')

        if not instance_id or not target_port:
            return jsonify({'error': 'instance_id e port sao obrigatorios'}), 400

        # Obter info da instancia
        api_key = getattr(g, 'vast_api_key', '')
        if not api_key:
            return jsonify({'error': 'API key nao configurada'}), 400

        vast = VastService(api_key)
        status = vast.get_instance_status(instance_id)

        if status.get('status') != 'running':
            return jsonify({
                'error': 'Instancia nao esta rodando',
                'status': status.get('status')
            }), 400

        public_ip = status.get('public_ipaddr')
        ports = status.get('ports', {})

        # Encontrar porta mapeada
        port_key = f"{target_port}/tcp"
        port_mapping = ports.get(port_key, [])

        if port_mapping and port_mapping[0].get('HostPort'):
            # Porta esta no mapeamento Docker - usar HostPort
            host_port = port_mapping[0].get('HostPort')
        else:
            # Porta NAO esta no mapeamento - usar diretamente (assume que esta exposta)
            # Isso permite expor qualquer porta que esteja rodando na maquina
            host_port = target_port

        # Gerar subdomain
        subdomain = f"{instance_id}-{target_port}"

        # Verificar se ja existe
        if check_nginx_subdomain_exists(subdomain):
            return jsonify({
                'success': True,
                'message': 'Subdomain ja registrado',
                'url': f'https://{subdomain}.dumontcloud.com',
                'backend': f'{public_ip}:{host_port}'
            })

        # Registrar no nginx
        result = register_nginx_subdomain(subdomain, public_ip, int(host_port))

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500

    @app.route('/api/port-proxy/remove', methods=['POST'])
    @login_required
    def remove_port_proxy():
        """
        Remove uma porta customizada exposta via nginx.
        POST /api/port-proxy/remove
        Body: {"instance_id": 28864630, "port": 5050}

        Remove o arquivo de config nginx e recarrega o nginx.
        """
        import subprocess

        data = request.get_json()
        instance_id = data.get('instance_id')
        target_port = data.get('port')

        if not instance_id or not target_port:
            return jsonify({'error': 'instance_id e port sao obrigatorios'}), 400

        # Verificar se e uma porta customizada (arquivo nginx existe)
        subdomain = f"{instance_id}-{target_port}"
        config_file = f"{NGINX_CONF_DIR}/auto_{subdomain}.conf"

        # Verificar se o arquivo existe
        check = subprocess.run(['test', '-f', config_file], capture_output=True)
        if check.returncode != 0:
            return jsonify({
                'error': 'Porta nao encontrada ou nao e uma porta customizada',
                'port': target_port,
                'instance_id': instance_id
            }), 404

        try:
            # Remover arquivo de config
            remove = subprocess.run(
                ['sudo', 'rm', '-f', config_file],
                capture_output=True,
                timeout=10
            )
            if remove.returncode != 0:
                return jsonify({'error': f'Falha ao remover config: {remove.stderr.decode()}'}), 500

            # Testar config do nginx
            test = subprocess.run(['sudo', 'nginx', '-t'], capture_output=True, timeout=10)
            if test.returncode != 0:
                return jsonify({'error': f'Config nginx invalido apos remocao: {test.stderr.decode()}'}), 500

            # Recarregar nginx
            reload = subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], capture_output=True, timeout=10)
            if reload.returncode != 0:
                return jsonify({'error': f'Falha ao recarregar nginx: {reload.stderr.decode()}'}), 500

            return jsonify({
                'success': True,
                'message': f'Porta {target_port} removida com sucesso',
                'port': target_port,
                'instance_id': instance_id
            })

        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Timeout ao remover configuracao nginx'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/port-proxy/list/<int:instance_id>')
    @login_required
    def list_port_proxies(instance_id: int):
        """Lista todas as portas expostas para uma instancia"""
        import subprocess
        import glob

        pattern = f"{NGINX_CONF_DIR}/auto_{instance_id}-*.conf"
        configs = glob.glob(pattern)

        ports = []
        for config in configs:
            filename = os.path.basename(config)
            # auto_28864630-8080.conf -> 8080
            parts = filename.replace('auto_', '').replace('.conf', '').split('-')
            if len(parts) == 2:
                ports.append({
                    'port': parts[1],
                    'subdomain': f"{parts[0]}-{parts[1]}.dumontcloud.com",
                    'url': f"https://{parts[0]}-{parts[1]}.dumontcloud.com"
                })

        return jsonify({'instance_id': instance_id, 'exposed_ports': ports})

    def handle_instance_proxy(instance_id: int, target_port: str):
        """
        Faz PROXY REVERSO REAL para uma porta especifica de uma instancia GPU.
        Todo o trafego passa pelo VPS, mantendo SSL e escondendo IP real.
        """
        import time
        import requests as req
        from src.services import VastService

        cache_key = f"{instance_id}_{target_port}"
        cache_entry = instance_cache.get(cache_key)

        # Cache de 60 segundos
        if not cache_entry or (time.time() - cache_entry.get('cached_at', 0)) > 60:
            config = load_user_config()
            for user_data in config.get('users', {}).values():
                api_key = user_data.get('vast_api_key', '')
                if api_key:
                    vast = VastService(api_key)
                    status = vast.get_instance_status(instance_id)
                    if status.get('status') == 'running':
                        public_ip = status.get('public_ipaddr')
                        ports = status.get('ports', {})

                        # Buscar a porta especificada
                        port_key = f"{target_port}/tcp"
                        port_mapping = ports.get(port_key, [])
                        host_port = None
                        if port_mapping and len(port_mapping) > 0:
                            host_port = port_mapping[0].get('HostPort')

                        instance_cache[cache_key] = {
                            'public_ip': public_ip,
                            'host_port': host_port,
                            'all_ports': ports,
                            'status': status.get('status'),
                            'cached_at': time.time(),
                        }
                    else:
                        instance_cache[cache_key] = {
                            'status': status.get('status', 'unknown'),
                            'error': status.get('error'),
                            'cached_at': time.time(),
                        }
                    break

        cache_entry = instance_cache.get(cache_key)
        if not cache_entry:
            return jsonify({
                'error': 'Instancia nao encontrada',
                'instance_id': instance_id,
                'hint': 'Verifique se a instancia existe e se voce tem uma API key configurada'
            }), 404

        if cache_entry.get('status') != 'running':
            return jsonify({
                'error': f'Instancia nao esta rodando',
                'status': cache_entry.get('status'),
                'instance_id': instance_id,
            }), 503

        public_ip = cache_entry.get('public_ip')
        host_port = cache_entry.get('host_port')

        if not host_port:
            # A porta nao esta mapeada - mostrar portas disponiveis
            available = []
            for port_key, mappings in cache_entry.get('all_ports', {}).items():
                if mappings and len(mappings) > 0:
                    available.append({
                        'port': port_key,
                        'host_port': mappings[0].get('HostPort')
                    })
            return jsonify({
                'error': f'Porta {target_port} nao esta mapeada nesta instancia',
                'instance_id': instance_id,
                'requested_port': target_port,
                'available_ports': available,
                'hint': 'Use uma das portas disponiveis ou configure a instancia com essa porta'
            }), 404

        # ========== PROXY REVERSO REAL ==========
        # Construir URL de destino
        target_path = request.path or '/'
        target_url = f"http://{public_ip}:{host_port}{target_path}"
        if request.query_string:
            target_url += f"?{request.query_string.decode()}"

        # Headers para passar ao servidor de destino
        excluded_headers = ['host', 'content-length', 'transfer-encoding', 'connection']
        headers = {
            key: value for key, value in request.headers
            if key.lower() not in excluded_headers
        }
        headers['X-Forwarded-For'] = request.remote_addr
        headers['X-Forwarded-Proto'] = request.scheme
        headers['X-Real-IP'] = request.remote_addr

        try:
            # Fazer request para o servidor de destino
            resp = req.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=120,
            )

            # Construir resposta para o cliente
            excluded_response_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            response_headers = [
                (name, value) for name, value in resp.raw.headers.items()
                if name.lower() not in excluded_response_headers
            ]

            # Retornar resposta com streaming
            from flask import Response
            return Response(
                resp.iter_content(chunk_size=8192),
                status=resp.status_code,
                headers=response_headers,
            )

        except req.exceptions.Timeout:
            return jsonify({
                'error': 'Timeout ao conectar com a instancia',
                'instance_id': instance_id,
                'target': f"{public_ip}:{host_port}",
            }), 504

        except req.exceptions.ConnectionError as e:
            return jsonify({
                'error': 'Erro de conexao com a instancia',
                'instance_id': instance_id,
                'target': f"{public_ip}:{host_port}",
                'details': str(e),
            }), 502

        except Exception as e:
            return jsonify({
                'error': 'Erro interno no proxy',
                'details': str(e),
            }), 500

    @app.before_request
    def check_subdomain_proxy():
        """Verifica se o request vem de um subdominio de VM e faz proxy"""
        host = request.host.split(':')[0]  # Remove porta se houver

        # Formato do subdominio: INSTANCE_ID-PORT.dumontcloud.com
        # Exemplo: 28864630-8080.dumontcloud.com
        parts = host.split('.')

        # Verifica se e um subdominio valido (nao e o dominio principal)
        if len(parts) >= 3 and parts[-2] == 'dumontcloud' and parts[-1] == 'com':
            subdomain = parts[0]

            # Parse do subdomain: pode ser "instanceid-port" ou apenas "instanceid"
            if '-' in subdomain:
                subdomain_parts = subdomain.split('-')
                if len(subdomain_parts) == 2 and subdomain_parts[0].isdigit() and subdomain_parts[1].isdigit():
                    instance_id = int(subdomain_parts[0])
                    target_port = subdomain_parts[1]
                else:
                    return  # Formato invalido
            elif subdomain.isdigit():
                instance_id = int(subdomain)
                target_port = '8080'  # Porta padrao (code-server)
            else:
                return  # Nao e um subdominio de instancia

            # Buscar info da instancia e fazer proxy
            return handle_instance_proxy(instance_id, target_port)

        # Formato legado: 12345.54.37.225.188.nip.io
        if len(parts) > 1 and parts[0].isdigit():
            # Valida que nao e apenas um IP (primeiro octeto)
            # Deve ter 6+ partes (nip.io) ou nao ser apenas numeros (dominio)
            if len(parts) < 6 and all(p.isdigit() for p in parts[:4]):
                return  # E apenas um IP, ignorar

            instance_id = int(parts[0])

            # Buscar info da instancia (com cache de 60 segundos)
            import time
            cache_entry = instance_cache.get(instance_id)
            if not cache_entry or (time.time() - cache_entry.get('cached_at', 0)) > 60:
                from src.services import VastService
                # Usar API key do config padrao para proxy
                config = load_user_config()
                for user_data in config.get('users', {}).values():
                    api_key = user_data.get('vast_api_key', '')
                    if api_key:
                        vast = VastService(api_key)
                        status = vast.get_instance_status(instance_id)
                        if status.get('status') == 'running':
                            public_ip = status.get('public_ipaddr')
                            ports = status.get('ports', {})

                            # Buscar porta 8080 (code-server)
                            port_8080 = None
                            port_8080_list = ports.get('8080/tcp', [])
                            if port_8080_list and len(port_8080_list) > 0:
                                port_8080 = port_8080_list[0].get('HostPort')

                            instance_cache[instance_id] = {
                                'ssh_host': status.get('ssh_host'),
                                'ssh_port': status.get('ssh_port'),
                                'public_ip': public_ip,
                                'port_8080': port_8080,
                                'cached_at': time.time(),
                            }
                        break

            # Se temos info da instancia, fazer redirect APENAS para /code/
            # A raiz / e outras rotas mostram o dashboard Dumont Cloud normalmente
            cache_entry = instance_cache.get(instance_id)
            if cache_entry and request.path.startswith('/code'):
                public_ip = cache_entry.get('public_ip')
                port_8080 = cache_entry.get('port_8080')

                if port_8080 and public_ip:
                    # Remove /code do path para o code-server
                    code_path = request.path[5:] if request.path.startswith('/code') else request.path
                    if not code_path:
                        code_path = '/'
                    target = f"http://{public_ip}:{port_8080}{code_path}"
                    if request.query_string:
                        target += f"?{request.query_string.decode()}"
                    return redirect(target)

            # Armazenar instance_id no g para uso nas rotas
            g.subdomain_instance_id = instance_id
            g.subdomain_instance_cache = cache_entry

    @app.route('/vm/<int:instance_id>')
    @app.route('/vm/<int:instance_id>/<path:subpath>')
    @login_required
    def vm_proxy(instance_id: int, subpath=''):
        """Proxy para VS Code web rodando na maquina remota"""
        from src.services import VastService

        api_key = getattr(g, 'vast_api_key', '')
        vast = VastService(api_key)

        # Obter info da instancia
        status = vast.get_instance_status(instance_id)
        if status.get('status') != 'running':
            return {'error': 'Instancia nao esta rodando', 'status': status.get('status', 'unknown')}, 400

        public_ip = status.get('public_ipaddr')

        # Preferir subdominio ao inves de IP direto
        base_host = f"{instance_id}.dumontcloud.com"

        # Redirecionar para subdominio (sem porta) - Nginx faz o proxy
        target_url = f"https://{base_host}"
        if subpath:
            target_url += f"/{subpath}"
        return redirect(target_url)

        # Se nao tiver porta direta, retorna erro informativo
        return {
            'error': 'VS Code web nao disponivel diretamente',
            'hint': 'Porta 8080 nao esta mapeada ou code-server nao esta rodando',
            'ssh': f"ssh -L 8080:localhost:8080 root@{status.get('ssh_host')} -p {status.get('ssh_port')}",
            'instance_id': instance_id,
            'ports': ports,
            'public_ip': public_ip
        }, 400

    # ========== PATH-BASED PORT PROXY ==========
    # Alternativa ao subdominio - funciona sem configuracao de DNS wildcard
    # Formato: /p/<instance_id>/<port>/
    # Exemplo: /p/28864630/8080/ -> redireciona para http://IP:PORTA_MAPEADA/

    @app.route('/p/<int:instance_id>/<int:port>')
    @app.route('/p/<int:instance_id>/<int:port>/')
    @app.route('/p/<int:instance_id>/<int:port>/<path:subpath>')
    def port_proxy(instance_id: int, port: int, subpath=''):
        """
        Proxy path-based para acessar portas de instancias.
        Funciona sem configuracao de DNS wildcard.

        Uso: https://dumontcloud.com/p/28864630/8080/
        """
        import time
        from src.services import VastService

        target_port = str(port)
        cache_key = f"{instance_id}_{target_port}"
        cache_entry = instance_cache.get(cache_key)

        # Cache de 60 segundos
        if not cache_entry or (time.time() - cache_entry.get('cached_at', 0)) > 60:
            config = load_user_config()
            for user_data in config.get('users', {}).values():
                api_key = user_data.get('vast_api_key', '')
                if api_key:
                    vast = VastService(api_key)
                    status = vast.get_instance_status(instance_id)
                    if status.get('status') == 'running':
                        public_ip = status.get('public_ipaddr')
                        ports = status.get('ports', {})

                        # Buscar a porta especificada
                        port_key = f"{target_port}/tcp"
                        port_mapping = ports.get(port_key, [])
                        host_port = None
                        if port_mapping and len(port_mapping) > 0:
                            host_port = port_mapping[0].get('HostPort')

                        instance_cache[cache_key] = {
                            'public_ip': public_ip,
                            'host_port': host_port,
                            'all_ports': ports,
                            'status': status.get('status'),
                            'cached_at': time.time(),
                        }
                    else:
                        instance_cache[cache_key] = {
                            'status': status.get('status', 'unknown'),
                            'error': status.get('error'),
                            'cached_at': time.time(),
                        }
                    break

        cache_entry = instance_cache.get(cache_key)
        if not cache_entry:
            return jsonify({
                'error': 'Instancia nao encontrada',
                'instance_id': instance_id,
                'hint': 'Verifique se a instancia existe e se voce tem uma API key configurada'
            }), 404

        if cache_entry.get('status') != 'running':
            return jsonify({
                'error': f'Instancia nao esta rodando',
                'status': cache_entry.get('status'),
                'instance_id': instance_id,
            }), 503

        public_ip = cache_entry.get('public_ip')
        host_port = cache_entry.get('host_port')

        if not host_port:
            # A porta nao esta mapeada - mostrar portas disponiveis
            available = []
            for port_key, mappings in cache_entry.get('all_ports', {}).items():
                if mappings and len(mappings) > 0:
                    container_port = port_key.split('/')[0]
                    available.append({
                        'port': port_key,
                        'host_port': mappings[0].get('HostPort'),
                        'url': f'/p/{instance_id}/{container_port}/'
                    })
            return jsonify({
                'error': f'Porta {target_port} nao esta mapeada nesta instancia',
                'instance_id': instance_id,
                'requested_port': target_port,
                'available_ports': available,
                'hint': 'Use uma das portas disponiveis'
            }), 404

        # Construir URL de destino
        target_path = f"/{subpath}" if subpath else '/'
        target_url = f"http://{public_ip}:{host_port}{target_path}"
        if request.query_string:
            target_url += f"?{request.query_string.decode()}"

        # Proxy reverso - suporta WebSocket
        # Detectar se é um upgrade de WebSocket
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            # Para WebSocket, precisamos fazer um proxy bidirecional
            # Infelizmente Flask não suporta isso nativamente
            # Retornar erro informativo
            return jsonify({
                'error': 'WebSocket proxy não implementado via Flask',
                'hint': 'Use Nginx diretamente ou configure um proxy WebSocket adequado',
                'target_url': target_url
            }), 501

        # Para requisições HTTP normais, fazer proxy
        headers = dict(request.headers)
        headers.pop('Host', None)  # Remover Host header original

        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False,
                stream=True,
                timeout=30
            )

            # Construir response
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            response_headers = [(name, value) for (name, value) in resp.raw.headers.items()
                                if name.lower() not in excluded_headers]

            return Response(resp.content, resp.status_code, response_headers)
        except Exception as e:
            return jsonify({
                'error': 'Erro ao fazer proxy da requisicao',
                'details': str(e),
                'target_url': target_url
            }), 502

    @app.route('/')
    @login_required
    def index():
        from flask import send_from_directory
        # Servir o React app quando estiver buildado
        build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'build')
        index_path = os.path.join(build_dir, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(build_dir, 'index.html')
        # Fallback para pagina simples
        return redirect('/dashboard-legacy')

    @app.route('/dashboard-legacy')
    @login_required
    def dashboard_legacy():
        # Manter o dashboard antigo como fallback
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Dumont Cloud</title>
        <style>
            body { font-family: system-ui; background: #0d1117; color: #c9d1d9; margin: 0; padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .logo { font-size: 1.5em; font-weight: 700; color: #58a6ff; }
            .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
            .btn { padding: 8px 16px; background: #238636; border: none; border-radius: 6px; color: white; cursor: pointer; text-decoration: none; }
            a { color: #58a6ff; }
        </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">Dumont Cloud</div>
                <a href="/logout" class="btn" style="background: #21262d;">Sair</a>
            </div>
            <div class="card">
                <h3>Frontend em desenvolvimento</h3>
                <p>O novo frontend React esta sendo construido em <code>web/</code></p>
                <p>API disponivel em <code>/api/*</code></p>
            </div>
            <div class="card">
                <h3>Endpoints disponiveis:</h3>
                <ul>
                    <li><a href="/api/snapshots">/api/snapshots</a> - Lista snapshots</li>
                    <li><a href="/api/offers">/api/offers</a> - Lista ofertas de GPU</li>
                    <li><a href="/api/machines">/api/machines</a> - Suas instancias</li>
                    <li><a href="/api/settings">/api/settings</a> - Configuracoes</li>
                </ul>
            </div>
        </body>
        </html>
        '''

    # Catchall route for SPA - manually handle all static files and routes
    @app.route('/<path:path>')
    def spa_catchall(path):
        from flask import send_from_directory

        # Build directory path
        build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'build')

        # Try to serve static file if it exists
        file_path = os.path.join(build_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(build_dir, path)

        # For SPA routes (no file extension or file doesn't exist), serve index.html
        index_path = os.path.join(build_dir, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(build_dir, 'index.html')

        return redirect('/')

    # Inicializar agentes antes de retornar
    app._init_agents()

    return app


# Criar app
app = create_app()

if __name__ == '__main__':
    app.run(
        host=settings.app.host,
        port=settings.app.port,
        debug=settings.app.debug,
    )
