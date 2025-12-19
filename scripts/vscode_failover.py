#!/usr/bin/env python3
"""
Failover Proxy para VS Code Server
Redireciona automaticamente de GPU para CPU se GPU cair
"""
import time
import requests
from flask import Flask, request, Response
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class VSCodeFailover:
    def __init__(self):
        self.gpu_url = None
        self.cpu_url = None
        self.current_target = "gpu"
        self.previous_target = "gpu"
        self.last_check = 0
        self.check_interval = 5  # segundos
        self.show_transition = False  # Flag para mostrar página de transição
        
    def set_targets(self, gpu_host, gpu_port, cpu_host, cpu_port):
        """Configura URLs de GPU e CPU"""
        self.gpu_url = f"http://{gpu_host}:{gpu_port}"
        self.cpu_url = f"http://{cpu_host}:{cpu_port}"
        
    def check_health(self, url):
        """Verifica se VS Code Server está respondendo"""
        try:
            response = requests.get(f"{url}/healthz", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def get_active_target(self):
        """Retorna URL ativo (GPU ou CPU)"""
        now = time.time()
        
        # Só checa a cada X segundos para não sobrecarregar
        if now - self.last_check < self.check_interval:
            return self.gpu_url if self.current_target == "gpu" else self.cpu_url
        
        self.last_check = now
        
        # Verifica GPU primeiro
        if self.check_health(self.gpu_url):
            if self.current_target != "gpu":
                logging.info("✅ GPU voltou! Redirecting para GPU")
                self.previous_target = self.current_target
                self.current_target = "gpu"
                self.show_transition = True
            return self.gpu_url
        
        # GPU down, tenta CPU
        if self.check_health(self.cpu_url):
            if self.current_target != "cpu":
                logging.warning("⚠️  GPU down! Failover para CPU")
                self.previous_target = self.current_target
                self.current_target = "cpu"
                self.show_transition = True
            return self.cpu_url
        
        # Ambos down
        logging.error("❌ GPU e CPU down!")
        return None
    
    def get_transition_page(self, from_target, to_target):
        """Página HTML de notificação de failover"""
        gpu_name = "GPU (Vast.ai)"
        cpu_name = "CPU Backup (GCP)"
        
        from_name = gpu_name if from_target == "gpu" else cpu_name
        to_name = cpu_name if to_target == "cpu" else gpu_name
        
        icon = "⚠️" if to_target == "cpu" else "✅"
        color = "#ff6b6b" if to_target == "cpu" else "#51cf66"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="3;url=/">
    <title>Trocando de Máquina...</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            color: white;
        }}
        
        .container {{
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 60px 80px;
            text-align: center;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
            max-width: 600px;
            animation: slideIn 0.5s ease-out;
        }}
        
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(-30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .icon {{
            font-size: 80px;
            margin-bottom: 30px;
            animation: pulse 1.5s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.1); }}
        }}
        
        h1 {{
            font-size: 36px;
            margin-bottom: 20px;
            font-weight: 700;
        }}
        
        .subtitle {{
            font-size: 20px;
            margin-bottom: 40px;
            opacity: 0.9;
        }}
        
        .transition-info {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        
        .machine {{
            display: inline-block;
            padding: 12px 24px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            margin: 10px;
            font-size: 18px;
            font-weight: 600;
        }}
        
        .arrow {{
            font-size: 32px;
            margin: 0 20px;
        }}
        
        .status {{
            font-size: 16px;
            opacity: 0.8;
            margin-top: 20px;
        }}
        
        .loader {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        /* Publicidade Sutil */
        .ad-section {{
            margin-top: 40px;
            padding: 20px;
            background: rgba(76, 209, 55, 0.1);
            border-left: 3px solid #4cd137;
            border-radius: 10px;
            text-align: left;
            backdrop-filter: blur(5px);
            transition: all 0.3s ease;
        }}
        
        .ad-section:hover {{
            background: rgba(76, 209, 55, 0.15);
            transform: translateY(-2px);
        }}
        
        .ad-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        
        .ad-content {{
            margin-top: 10px;
        }}
        
        .ad-content strong {{
            font-size: 18px;
            display: block;
            margin-bottom: 8px;
        }}
        
        .ad-content p {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 12px;
        }}
        
        .ad-link {{
            color: #4cd137;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
        }}
        
        .ad-link:hover {{
            color: #44bd32;
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{icon}</div>
        <h1>Trocando de Máquina</h1>
        <p class="subtitle">Redirecionando automaticamente...</p>
        
        <div class="transition-info">
            <div class="machine">{from_name}</div>
            <span class="arrow">→</span>
            <div class="machine" style="background: {color};">{to_name}</div>
        </div>
        
        <div class="status">
            Conectando no novo servidor<span class="loader"></span>
        </div>
        
        <!-- Publicidade Sutil -->
        <div class="ad-section">
            <div class="ad-badge">💡 Dica Profissional</div>
            <div class="ad-content">
                <strong>Deploy de LLM em 2 minutos</strong>
                <p>Ollama + GPU pronto para usar. Zero config.</p>
                <a href="#" class="ad-link">Saiba mais →</a>
            </div>
        </div>
        
        <p style="margin-top: 30px; font-size: 14px; opacity: 0.7;">
            Você será redirecionado em <strong>3 segundos</strong>
        </p>
    </div>
    
    <script>
        // Auto-redirect após 3s
        setTimeout(function() {{
            window.location.href = '/';
        }}, 3000);
    </script>
</body>
</html>
"""
        return html

failover = VSCodeFailover()

@app.route('/__transition__')
def transition():
    """Página de transição de failover"""
    html = failover.get_transition_page(failover.previous_target, failover.current_target)
    failover.show_transition = False  # Reset flag
    return html

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    """Proxy todas requisições para target ativo"""
    
    # Se houver transição pendente e for requisição GET, mostrar página
    if failover.show_transition and request.method == 'GET' and not path.startswith('_'):
        return f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="0;url=/__transition__">
        </head>
        <body>Redirecionando...</body>
        </html>
        """
    
    target = failover.get_active_target()
    
    if not target:
        return "VS Code Server temporariamente indisponível", 503
    
    # Constrói URL completa
    url = f"{target}/{path}"
    
    # Copia headers da requisição original
    headers = {key: value for key, value in request.headers if key != 'Host'}
    
    # Proxy da requisição
    try:
        if request.method == 'GET':
            resp = requests.get(url, headers=headers, params=request.args, stream=True)
        elif request.method == 'POST':
            resp = requests.post(url, headers=headers, data=request.get_data(), params=request.args)
        elif request.method == 'PUT':
            resp = requests.put(url, headers=headers, data=request.get_data(), params=request.args)
        elif request.method == 'DELETE':
            resp = requests.delete(url, headers=headers, params=request.args)
        elif request.method == 'PATCH':
            resp = requests.patch(url, headers=headers, data=request.get_data(), params=request.args)
        else:
            return "Method not allowed", 405
        
        # Retorna resposta
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, headers)
        
    except Exception as e:
        logging.error(f"Erro no proxy: {e}")
        return "Erro ao conectar com VS Code Server", 502

@app.route('/health')
def health():
    """Endpoint de health check do proxy"""
    target = failover.get_active_target()
    if target:
        return {
            "status": "ok",
            "active_target": failover.current_target,
            "gpu_url": failover.gpu_url,
            "cpu_url": failover.cpu_url
        }
    return {"status": "error", "message": "No targets available"}, 503

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 5:
        print("Uso: python3 vscode_failover.py GPU_HOST GPU_PORT CPU_HOST CPU_PORT")
        print("Exemplo: python3 vscode_failover.py ssh4.vast.ai 38784 35.240.1.1 22")
        sys.exit(1)
    
    gpu_host = sys.argv[1]
    gpu_port = sys.argv[2]
    cpu_host = sys.argv[3]
    cpu_port = sys.argv[4]
    
    failover.set_targets(gpu_host, gpu_port, cpu_host, cpu_port)
    
    print("="*70)
    print("VS Code Server - Failover Proxy")
    print("="*70)
    print(f"GPU Target: {failover.gpu_url}")
    print(f"CPU Target: {failover.cpu_url}")
    print(f"Proxy rodando em: http://0.0.0.0:8888")
    print("="*70)
    
    app.run(host='0.0.0.0', port=8888, debug=False)
