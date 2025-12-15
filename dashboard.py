#!/usr/bin/env python3
"""
SnapGPU Dashboard v5 - Interface com perfis de maquina (Economica/Equilibrada/Performance)
Features:
- 3 perfis de maquina com presets de velocidade/preco
- Filtro de disco visivel
- Badges de velocidade de internet (Lenta/Media/Rapida)
- Multi-start de maquinas para inicializacao rapida
"""

from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
import subprocess
import threading
import json
import os
import requests
from datetime import datetime
from functools import wraps
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'snapgpu-secret-key-2024'

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"users": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_user_api_key(username):
    config = load_config()
    return config.get("users", {}).get(username, {}).get("vast_api_key", "")

def set_user_api_key(username, api_key):
    config = load_config()
    if "users" not in config:
        config["users"] = {}
    if username not in config["users"]:
        config["users"][username] = {}
    config["users"][username]["vast_api_key"] = api_key
    save_config(config)

state = {
    "task_output": [],
    "task_status": "idle",
    "deploy_status": {}
}

USERS = {
    "marcoslogin": {
        "email": "marcos@email.com",
        "password": "marcos123"
    }
}

CONFIG = {
    "R2_ACCESS_KEY": "f0a6f424064e46c903c76a447f5e73d2",
    "R2_SECRET_KEY": "1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5",
    "R2_ENDPOINT": "https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com",
    "R2_BUCKET": "musetalk",
    "RESTIC_PASSWORD": "musetalk123",
    "RESTIC_REPO": "s3:https://142ed673a5cc1a9e91519c099af3d791.r2.cloudflarestorage.com/musetalk/restic",
    "S3_CONNECTIONS": 32
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>SnapGPU - Login</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: #161b22;
            border-radius: 12px;
            padding: 40px;
            width: 100%;
            max-width: 380px;
            border: 1px solid #30363d;
        }
        .logo {
            text-align: center;
            font-size: 2em;
            font-weight: 700;
            margin-bottom: 8px;
            color: #58a6ff;
        }
        .subtitle { text-align: center; color: #8b949e; margin-bottom: 32px; font-size: 0.9em; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; color: #c9d1d9; margin-bottom: 8px; font-size: 0.9em; }
        .form-group input {
            width: 100%; padding: 12px 14px; border: 1px solid #30363d;
            border-radius: 6px; background: #0d1117; color: #c9d1d9; font-size: 0.95em;
        }
        .form-group input:focus { outline: none; border-color: #58a6ff; }
        .btn-login {
            width: 100%; padding: 12px; border: none; border-radius: 6px;
            background: #238636; color: #fff; font-size: 1em; font-weight: 600; cursor: pointer;
        }
        .btn-login:hover { background: #2ea043; }
        .error { background: rgba(248, 81, 73, 0.1); border: 1px solid #f85149; color: #f85149; padding: 12px; border-radius: 6px; margin-bottom: 16px; text-align: center; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">SnapGPU</div>
        <div class="subtitle">GPU Snapshot Manager</div>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Usuario</label>
                <input type="text" name="username" placeholder="Seu usuario" required>
            </div>
            <div class="form-group">
                <label>Senha</label>
                <input type="password" name="password" placeholder="Sua senha" required>
            </div>
            <button type="submit" class="btn-login">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <title>SnapGPU Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-yellow: #d29922;
            --accent-purple: #a371f7;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; font-size: 14px; }

        /* Header */
        .header { background: var(--bg-secondary); padding: 12px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.3em; font-weight: 700; color: var(--accent-blue); }
        .user-info { display: flex; align-items: center; gap: 16px; }
        .user-name { color: var(--text-secondary); }
        .btn-logout { padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px; background: transparent; color: var(--text-primary); cursor: pointer; text-decoration: none; font-size: 0.85em; }
        .btn-logout:hover { border-color: var(--accent-red); color: var(--accent-red); }

        /* Container */
        .container { max-width: 1400px; margin: 0 auto; padding: 24px; }

        /* Grid */
        .main-grid { display: grid; grid-template-columns: 400px 1fr; gap: 24px; }
        @media (max-width: 1100px) { .main-grid { grid-template-columns: 1fr; } }

        /* Cards */
        .card { background: var(--bg-secondary); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; }
        .card-header { padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .card-title { font-size: 0.95em; font-weight: 600; color: var(--text-primary); }
        .card-body { padding: 16px; }

        /* Buttons */
        .btn { padding: 8px 16px; border: 1px solid var(--border); border-radius: 6px; font-size: 0.85em; font-weight: 500; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; background: var(--bg-tertiary); color: var(--text-primary); }
        .btn:hover { border-color: var(--text-secondary); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-primary { background: var(--accent-green); border-color: var(--accent-green); color: #fff; }
        .btn-primary:hover { background: #2ea043; }
        .btn-blue { background: var(--accent-blue); border-color: var(--accent-blue); color: #fff; }
        .btn-sm { padding: 4px 10px; font-size: 0.8em; }
        .btn-icon { padding: 6px 8px; }

        /* Snapshots */
        .snapshot-list { max-height: 500px; overflow-y: auto; }
        .snapshot-item { padding: 14px 16px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.2s; }
        .snapshot-item:hover { background: var(--bg-tertiary); }
        .snapshot-item.selected { background: rgba(56, 139, 253, 0.1); border-left: 3px solid var(--accent-blue); }
        .snapshot-item:last-child { border-bottom: none; }
        .snapshot-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
        .snapshot-name { font-weight: 600; color: var(--text-primary); font-size: 0.95em; }
        .snapshot-date { color: var(--text-muted); font-size: 0.8em; }
        .snapshot-meta { color: var(--text-secondary); font-size: 0.8em; display: flex; gap: 12px; flex-wrap: wrap; }
        .snapshot-meta span { display: flex; align-items: center; gap: 4px; }
        .snapshot-tag { background: var(--accent-purple); color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.7em; font-weight: 500; }
        .snapshot-versions { color: var(--accent-yellow); font-size: 0.75em; margin-top: 6px; cursor: pointer; }
        .snapshot-versions:hover { text-decoration: underline; }
        .snapshot-actions { display: flex; gap: 6px; margin-top: 8px; }

        /* Filters */
        .filters-panel { margin-bottom: 16px; }
        .filters-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
        .filter-group { }
        .filter-label { color: var(--text-secondary); font-size: 0.8em; margin-bottom: 6px; display: block; }
        .filter-input, .filter-select { width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 0.9em; }
        .filter-input:focus, .filter-select:focus { outline: none; border-color: var(--accent-blue); }
        .filter-range { display: flex; align-items: center; gap: 8px; }
        .filter-range input[type="range"] { flex: 1; accent-color: var(--accent-blue); }
        .filter-range .range-value { min-width: 60px; text-align: right; color: var(--text-secondary); font-size: 0.85em; }
        .filter-toggle { display: flex; align-items: center; gap: 8px; padding: 8px 0; }
        .filter-toggle input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent-blue); }
        .filter-toggle label { color: var(--text-primary); font-size: 0.9em; cursor: pointer; }
        .filters-actions { display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
        .filters-toggle { padding: 8px 0; cursor: pointer; color: var(--accent-blue); font-size: 0.85em; display: flex; align-items: center; gap: 6px; }

        /* Offers */
        .offers-list { max-height: 350px; overflow-y: auto; }
        .offer-item { padding: 12px 16px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.2s; display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center; }
        .offer-item:hover { background: var(--bg-tertiary); }
        .offer-item.selected { background: rgba(56, 139, 253, 0.1); border-left: 3px solid var(--accent-blue); }
        .offer-item:last-child { border-bottom: none; }
        .offer-gpu { font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
        .offer-specs { color: var(--text-secondary); font-size: 0.8em; display: flex; gap: 8px; flex-wrap: wrap; }
        .offer-specs span { background: var(--bg-primary); padding: 2px 6px; border-radius: 4px; }
        .offer-price { font-weight: 600; color: var(--accent-green); font-size: 1.1em; }
        .offer-location { color: var(--text-muted); font-size: 0.75em; margin-top: 2px; }

        /* Output */
        .output { background: var(--bg-primary); border-radius: 6px; padding: 12px; font-family: 'SF Mono', Consolas, monospace; font-size: 0.8em; max-height: 200px; overflow-y: auto; white-space: pre-wrap; border: 1px solid var(--border); color: var(--text-secondary); }

        /* Status badges */
        .status { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.75em; font-weight: 500; }
        .status-ready { background: rgba(63, 185, 80, 0.15); color: var(--accent-green); }
        .status-running { background: rgba(210, 153, 34, 0.15); color: var(--accent-yellow); }
        .status-error { background: rgba(248, 81, 73, 0.15); color: var(--accent-red); }

        /* Modal */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: var(--bg-secondary); border-radius: 12px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto; border: 1px solid var(--border); }
        .modal-header { padding: 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .modal-header h3 { font-size: 1em; font-weight: 600; }
        .modal-close { background: none; border: none; color: var(--text-secondary); font-size: 1.5em; cursor: pointer; line-height: 1; }
        .modal-body { padding: 16px; }

        /* Deploy steps */
        .deploy-steps { display: flex; flex-direction: column; gap: 8px; }
        .deploy-step { display: flex; align-items: center; gap: 12px; padding: 10px; background: var(--bg-primary); border-radius: 6px; }
        .step-number { width: 24px; height: 24px; border-radius: 50%; background: var(--border); display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.8em; }
        .step-number.active { background: var(--accent-yellow); color: #000; }
        .step-number.done { background: var(--accent-green); color: #fff; }
        .step-text { flex: 1; font-size: 0.9em; }
        .step-status { color: var(--text-muted); font-size: 0.8em; }

        /* Alert */
        .alert { padding: 10px 14px; border-radius: 6px; font-size: 0.85em; margin-bottom: 12px; }
        .alert-info { background: rgba(88, 166, 255, 0.1); border: 1px solid var(--accent-blue); color: var(--accent-blue); }
        .alert-success { background: rgba(63, 185, 80, 0.1); border: 1px solid var(--accent-green); color: var(--accent-green); }
        .alert-warning { background: rgba(210, 153, 34, 0.1); border: 1px solid var(--accent-yellow); color: var(--accent-yellow); }

        /* Form */
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; color: var(--text-secondary); margin-bottom: 6px; font-size: 0.85em; }
        .form-group input, .form-group select { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 0.9em; }
        .form-group input:focus { outline: none; border-color: var(--accent-blue); }
        .form-row { display: flex; gap: 10px; }
        .form-row > * { flex: 1; }

        /* Tabs */
        .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
        .tab-btn { padding: 10px 16px; border: none; background: none; color: var(--text-secondary); cursor: pointer; font-size: 0.9em; border-bottom: 2px solid transparent; margin-bottom: -1px; }
        .tab-btn:hover { color: var(--text-primary); }
        .tab-btn.active { color: var(--accent-blue); border-bottom-color: var(--accent-blue); }

        /* Empty state */
        .empty-state { text-align: center; padding: 40px 20px; color: var(--text-muted); }
        .empty-state svg { width: 48px; height: 48px; margin-bottom: 12px; opacity: 0.5; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        /* Settings section */
        .settings-section { margin-top: 24px; }
        .settings-row { display: flex; gap: 12px; align-items: flex-end; }
        .settings-row > div:first-child { flex: 1; }

        /* Snapshot detail modal */
        .detail-section { margin-bottom: 16px; }
        .detail-section h4 { font-size: 0.85em; color: var(--text-secondary); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .detail-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 0.9em; }
        .detail-row:last-child { border-bottom: none; }
        .detail-label { color: var(--text-secondary); }
        .detail-value { color: var(--text-primary); font-weight: 500; }
        .folder-list { background: var(--bg-primary); border-radius: 6px; padding: 8px; }
        .folder-item { display: flex; justify-content: space-between; padding: 6px 8px; font-size: 0.85em; }
        .folder-name { color: var(--accent-blue); }
        .folder-size { color: var(--text-muted); }
        .tag-input-group { display: flex; gap: 8px; margin-top: 12px; }
        .tag-input-group input { flex: 1; }

        /* Profile Cards */
        .profile-card {
            background: var(--bg-primary);
            border: 2px solid var(--border);
            border-radius: 10px;
            padding: 14px 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .profile-card:hover { border-color: var(--accent-blue); background: var(--bg-tertiary); }
        .profile-card.selected { border-color: var(--accent-blue); background: rgba(56, 139, 253, 0.1); }
        .profile-icon { font-size: 1.5em; font-weight: 700; color: var(--accent-green); margin-bottom: 6px; }
        .profile-name { font-weight: 600; font-size: 0.95em; color: var(--text-primary); margin-bottom: 4px; }
        .profile-desc { font-size: 0.75em; color: var(--text-muted); line-height: 1.4; margin-bottom: 6px; }
        .profile-price { font-size: 0.85em; font-weight: 600; color: var(--accent-yellow); }

        /* Region selector - AWS style */
        .region-selector { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
        .region-btn {
            padding: 8px 14px;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--bg-primary);
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .region-btn:hover { border-color: var(--accent-blue); color: var(--text-primary); }
        .region-btn.selected { border-color: var(--accent-blue); background: rgba(56, 139, 253, 0.15); color: var(--accent-blue); }
        .region-flag { font-size: 1.1em; }

        /* Offer item improved */
        .offer-speed { font-size: 0.7em; padding: 2px 6px; border-radius: 4px; margin-left: 6px; }
        .offer-speed.fast { background: rgba(63, 185, 80, 0.2); color: var(--accent-green); }
        .offer-speed.medium { background: rgba(210, 153, 34, 0.2); color: var(--accent-yellow); }
        .offer-speed.slow { background: rgba(248, 81, 73, 0.2); color: var(--accent-red); }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">SnapGPU <span style="font-size: 0.5em; font-weight: 400; color: var(--text-muted); margin-left: 8px;">Restore rapido para GPU Cloud</span></div>
        <div class="user-info">
            <span class="user-name">{{ user }}</span>
            <a href="/logout" class="btn-logout">Sair</a>
        </div>
    </div>

    <div class="container">
        <div class="main-grid">
            <!-- Left: Snapshots Panel -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Snapshots</span>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span id="snapshot-count" class="status status-ready">0</span>
                        <button class="btn btn-sm" onclick="loadSnapshots()">Atualizar</button>
                    </div>
                </div>
                <div id="snapshots-list" class="snapshot-list">
                    <div class="empty-state">Carregando...</div>
                </div>
                <div style="padding: 12px 16px; border-top: 1px solid var(--border);">
                    <label class="filter-toggle">
                        <input type="checkbox" id="show-all-snapshots" onchange="loadSnapshots()">
                        <span>Mostrar versoes anteriores</span>
                    </label>
                </div>
            </div>

            <!-- Right: Deploy Panel -->
            <div>
                <div id="selected-snapshot-banner" class="alert alert-info" style="display: none;">
                    Snapshot selecionado: <strong id="selected-snapshot-display">-</strong>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Deploy</span>
                    </div>

                    <div class="tabs">
                        <button class="tab-btn active" onclick="showTab('new')">Nova Maquina</button>
                        <button class="tab-btn" onclick="showTab('existing')">Maquina Existente</button>
                    </div>

                    <div id="tab-new" class="card-body">
                        <!-- Filters Toggle -->
                        <div class="filters-toggle" onclick="toggleFilters()">
                            <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 3.834A.5.5 0 0 1 1.5 3.5v-2z"/></svg>
                            <span id="filters-toggle-text">Mostrar filtros avancados</span>
                        </div>

                        <!-- Filters Panel -->
                        <div id="filters-panel" class="filters-panel" style="display: none;">
                            <div class="filters-grid">
                                <!-- GPU Selection -->
                                <div class="filter-group">
                                    <label class="filter-label">GPU</label>
                                    <select id="filter-gpu" class="filter-select" onchange="applyFilters()">
                                        <option value="">Todas as GPUs</option>
                                        <option value="RTX 5090">RTX 5090</option>
                                        <option value="RTX 4090">RTX 4090</option>
                                        <option value="RTX 4080">RTX 4080</option>
                                        <option value="RTX 3090">RTX 3090</option>
                                        <option value="RTX 3080">RTX 3080</option>
                                        <option value="A100">A100</option>
                                        <option value="A100 PCIE">A100 PCIE</option>
                                        <option value="H100">H100</option>
                                        <option value="L40">L40</option>
                                    </select>
                                </div>

                                <!-- Num GPUs -->
                                <div class="filter-group">
                                    <label class="filter-label">Quantidade GPUs</label>
                                    <select id="filter-num-gpus" class="filter-select" onchange="applyFilters()">
                                        <option value="1">1 GPU</option>
                                        <option value="2">2 GPUs</option>
                                        <option value="4">4 GPUs</option>
                                        <option value="8">8 GPUs</option>
                                    </select>
                                </div>

                                <!-- VRAM -->
                                <div class="filter-group">
                                    <label class="filter-label">VRAM Minima</label>
                                    <div class="filter-range">
                                        <input type="range" id="filter-vram" min="8" max="80" value="16" oninput="updateRangeDisplay('vram')" onchange="applyFilters()">
                                        <span id="filter-vram-value" class="range-value">16 GB</span>
                                    </div>
                                </div>

                                <!-- Max Price -->
                                <div class="filter-group">
                                    <label class="filter-label">Preco Maximo</label>
                                    <div class="filter-range">
                                        <input type="range" id="filter-price" min="10" max="300" value="100" step="5" oninput="updateRangeDisplay('price')" onchange="applyFilters()">
                                        <span id="filter-price-value" class="range-value">$1.00/h</span>
                                    </div>
                                </div>

                                <!-- CPU Cores -->
                                <div class="filter-group">
                                    <label class="filter-label">CPU Cores Min</label>
                                    <div class="filter-range">
                                        <input type="range" id="filter-cpu" min="4" max="128" value="8" step="4" oninput="updateRangeDisplay('cpu')" onchange="applyFilters()">
                                        <span id="filter-cpu-value" class="range-value">8</span>
                                    </div>
                                </div>

                                <!-- RAM -->
                                <div class="filter-group">
                                    <label class="filter-label">RAM Minima</label>
                                    <div class="filter-range">
                                        <input type="range" id="filter-ram" min="8" max="512" value="16" step="8" oninput="updateRangeDisplay('ram')" onchange="applyFilters()">
                                        <span id="filter-ram-value" class="range-value">16 GB</span>
                                    </div>
                                </div>

                                <!-- Disk -->
                                <div class="filter-group">
                                    <label class="filter-label">Disco Minimo</label>
                                    <div class="filter-range">
                                        <input type="range" id="filter-disk" min="20" max="500" value="50" step="10" oninput="updateRangeDisplay('disk')" onchange="applyFilters()">
                                        <span id="filter-disk-value" class="range-value">50 GB</span>
                                    </div>
                                </div>

                                <!-- Download Speed -->
                                <div class="filter-group">
                                    <label class="filter-label">Download Min (Mbps)</label>
                                    <div class="filter-range">
                                        <input type="range" id="filter-download" min="100" max="10000" value="500" step="100" oninput="updateRangeDisplay('download')" onchange="applyFilters()">
                                        <span id="filter-download-value" class="range-value">500</span>
                                    </div>
                                </div>

                                <!-- CUDA Version -->
                                <div class="filter-group">
                                    <label class="filter-label">CUDA Minimo</label>
                                    <select id="filter-cuda" class="filter-select" onchange="applyFilters()">
                                        <option value="">Qualquer</option>
                                        <option value="11.0">11.0+</option>
                                        <option value="11.8">11.8+</option>
                                        <option value="12.0" selected>12.0+</option>
                                        <option value="12.4">12.4+</option>
                                    </select>
                                </div>

                                <!-- Reliability -->
                                <div class="filter-group">
                                    <label class="filter-label">Reliability Min</label>
                                    <select id="filter-reliability" class="filter-select" onchange="applyFilters()">
                                        <option value="">Qualquer</option>
                                        <option value="0.90">90%+</option>
                                        <option value="0.95" selected>95%+</option>
                                        <option value="0.99">99%+</option>
                                    </select>
                                </div>

                                <!-- Location -->
                                <div class="filter-group">
                                    <label class="filter-label">Localizacao</label>
                                    <select id="filter-location" class="filter-select" onchange="applyFilters()">
                                        <option value="">Qualquer</option>
                                        <option value="US">Estados Unidos</option>
                                        <option value="EU">Europa</option>
                                        <option value="ASIA">Asia</option>
                                    </select>
                                </div>
                            </div>

                            <!-- Toggle filters -->
                            <div style="display: flex; gap: 20px; margin-top: 12px; flex-wrap: wrap;">
                                <label class="filter-toggle">
                                    <input type="checkbox" id="filter-verified" checked onchange="applyFilters()">
                                    <span>Verificados</span>
                                </label>
                                <label class="filter-toggle">
                                    <input type="checkbox" id="filter-static-ip" onchange="applyFilters()">
                                    <span>IP Estatico</span>
                                </label>
                                <label class="filter-toggle">
                                    <input type="checkbox" id="filter-datacenter" onchange="applyFilters()">
                                    <span>Datacenter</span>
                                </label>
                            </div>

                            <div class="filters-actions">
                                <button class="btn btn-sm" onclick="resetFilters()">Resetar Filtros</button>
                                <button class="btn btn-sm btn-blue" onclick="applyFilters()">Aplicar</button>
                            </div>
                        </div>

                        <!-- Region Selector - AWS Style -->
                        <div class="form-group">
                            <label style="font-size: 0.95em; font-weight: 600; margin-bottom: 10px; display: block;">Regiao</label>
                            <div class="region-selector">
                                <button class="region-btn selected" id="region-all" onclick="selectRegion('')">
                                    <span class="region-flag">🌍</span> Global
                                </button>
                                <button class="region-btn" id="region-US" onclick="selectRegion('US')">
                                    <span class="region-flag">🇺🇸</span> US
                                </button>
                                <button class="region-btn" id="region-EU" onclick="selectRegion('EU')">
                                    <span class="region-flag">🇪🇺</span> Europa
                                </button>
                                <button class="region-btn" id="region-ASIA" onclick="selectRegion('ASIA')">
                                    <span class="region-flag">🌏</span> Asia
                                </button>
                            </div>
                        </div>

                        <!-- Machine Profile Selection -->
                        <div class="form-group" id="profile-select-group">
                            <label style="font-size: 0.95em; font-weight: 600; margin-bottom: 12px; display: block;">Velocidade (mais rapido = mais caro)</label>
                            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px;">
                                <div class="profile-card" id="profile-slow" onclick="selectProfile('slow')">
                                    <div class="profile-icon">🐢</div>
                                    <div class="profile-name">Lenta</div>
                                    <div class="profile-desc">100-500 Mbps<br>Restore ~5 min</div>
                                    <div class="profile-price" id="price-slow">Carregando...</div>
                                    <div class="profile-count" id="count-slow" style="font-size: 0.7em; color: var(--text-muted);"></div>
                                </div>
                                <div class="profile-card" id="profile-economy" onclick="selectProfile('economy')">
                                    <div class="profile-icon">⚡</div>
                                    <div class="profile-name">Media</div>
                                    <div class="profile-desc">500-2000 Mbps<br>Restore ~1-2 min</div>
                                    <div class="profile-price" id="price-economy">Carregando...</div>
                                    <div class="profile-count" id="count-economy" style="font-size: 0.7em; color: var(--text-muted);"></div>
                                </div>
                                <div class="profile-card selected" id="profile-balanced" onclick="selectProfile('balanced')">
                                    <div class="profile-icon">🚀</div>
                                    <div class="profile-name">Rapida</div>
                                    <div class="profile-desc">2000-4000 Mbps<br>Restore ~30s</div>
                                    <div class="profile-price" id="price-balanced">Carregando...</div>
                                    <div class="profile-count" id="count-balanced" style="font-size: 0.7em; color: var(--text-muted);"></div>
                                </div>
                                <div class="profile-card" id="profile-performance" onclick="selectProfile('performance')">
                                    <div class="profile-icon">🔥</div>
                                    <div class="profile-name">Ultra</div>
                                    <div class="profile-desc">4000+ Mbps<br>Restore ~15s</div>
                                    <div class="profile-price" id="price-performance">Carregando...</div>
                                    <div class="profile-count" id="count-performance" style="font-size: 0.7em; color: var(--text-muted);"></div>
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label>GPU</label>
                                    <select id="gpu-select" class="filter-select" onchange="onGpuChange()">
                                        <option value="">-- Selecione GPU --</option>
                                        <option value="RTX 4090" selected>RTX 4090</option>
                                        <option value="RTX 3090">RTX 3090</option>
                                        <option value="RTX 5090">RTX 5090</option>
                                        <option value="A100">A100</option>
                                        <option value="H100">H100</option>
                                    </select>
                                </div>
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label>Disco Minimo</label>
                                    <select id="disk-select" class="filter-select" onchange="loadOffers()">
                                        <option value="20">20 GB</option>
                                        <option value="50" selected>50 GB</option>
                                        <option value="100">100 GB</option>
                                        <option value="200">200 GB</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <!-- Offers List -->
                        <div id="offers-list" class="offers-list">
                            <div class="empty-state">Selecione uma GPU para ver ofertas</div>
                        </div>

                        <!-- Hot Start Option -->
                        <div style="margin-top: 12px; padding: 12px; background: var(--bg-primary); border-radius: 8px; border: 1px solid var(--border);">
                            <label class="filter-toggle" style="margin-bottom: 0;">
                                <input type="checkbox" id="hot-start-toggle" onchange="toggleHotStart()">
                                <span style="font-weight: 600;">Hot Start + Migrate</span>
                            </label>
                            <div id="hot-start-info" style="display: none; font-size: 0.8em; color: var(--text-secondary); margin-top: 10px;">
                                <div style="margin-bottom: 8px; padding: 8px; background: rgba(210, 153, 34, 0.1); border-radius: 6px; border-left: 3px solid var(--accent-yellow);">
                                    <strong style="color: var(--accent-yellow);">Estrategia:</strong> Inicia em maquina ULTRA rapida (~15s restore), depois migra para economica
                                </div>
                                <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px;">
                                    <span>Migrar para:</span>
                                    <select id="migrate-target" class="filter-select" style="width: auto; padding: 4px 8px;">
                                        <option value="slow">Lenta (100-500 Mbps)</option>
                                        <option value="economy" selected>Media (500-2000 Mbps)</option>
                                    </select>
                                </div>
                                <div style="color: var(--accent-green); font-size: 0.95em;">
                                    Economia estimada: <strong id="savings-estimate">~50-70%</strong> no custo/hora apos migracao
                                </div>
                            </div>
                        </div>

                        <button class="btn btn-primary" onclick="deployNew()" style="width: 100%; margin-top: 16px; padding: 12px;" id="btn-deploy">
                            Criar Maquina + Restore
                        </button>
                    </div>

                    <div id="tab-existing" class="card-body" style="display: none;">
                        <div id="my-machines" class="offers-list">
                            <div class="empty-state">Carregando maquinas...</div>
                        </div>

                        <button class="btn btn-primary" onclick="restoreExisting()" style="width: 100%; margin-top: 16px; padding: 12px;">
                            Restore na Maquina Selecionada
                        </button>
                    </div>
                </div>

                <!-- Output -->
                <div class="card" style="margin-top: 16px;">
                    <div class="card-header">
                        <span class="card-title">Output</span>
                        <span id="task-status" class="status status-ready">Pronto</span>
                    </div>
                    <div class="card-body">
                        <div id="output" class="output">Aguardando comando...</div>
                    </div>
                </div>

                <!-- Settings -->
                <div class="settings-section">
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Configuracoes</span>
                        </div>
                        <div class="card-body">
                            <div class="form-group">
                                <label>vast.ai API Key</label>
                                <div class="settings-row">
                                    <div>
                                        <input type="password" id="api-key" placeholder="Sua API Key" value="{{ vast_api_key }}">
                                    </div>
                                    <button class="btn" onclick="saveApiKey()">Salvar</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Deploy Modal -->
    <div id="deploy-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Criando Maquina + Restore</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="deploy-steps">
                    <div class="deploy-step">
                        <div class="step-number" id="step1">1</div>
                        <div class="step-text">Criando instancia vast.ai</div>
                        <div class="step-status" id="step1-status">Aguardando...</div>
                    </div>
                    <div class="deploy-step">
                        <div class="step-number" id="step2">2</div>
                        <div class="step-text">Aguardando maquina ficar pronta</div>
                        <div class="step-status" id="step2-status">Aguardando...</div>
                    </div>
                    <div class="deploy-step">
                        <div class="step-number" id="step3">3</div>
                        <div class="step-text">Instalando restic</div>
                        <div class="step-status" id="step3-status">Aguardando...</div>
                    </div>
                    <div class="deploy-step">
                        <div class="step-number" id="step4">4</div>
                        <div class="step-text">Restaurando snapshot</div>
                        <div class="step-status" id="step4-status">Aguardando...</div>
                    </div>
                    <!-- Hot Start Migration Steps (hidden by default) -->
                    <div class="deploy-step hot-start-step" id="step5-row" style="display: none;">
                        <div class="step-number" id="step5">5</div>
                        <div class="step-text">Criando maquina economica</div>
                        <div class="step-status" id="step5-status">Aguardando...</div>
                    </div>
                    <div class="deploy-step hot-start-step" id="step6-row" style="display: none;">
                        <div class="step-number" id="step6">6</div>
                        <div class="step-text">Migrando dados (rsync)</div>
                        <div class="step-status" id="step6-status">Aguardando...</div>
                    </div>
                    <div class="deploy-step hot-start-step" id="step7-row" style="display: none;">
                        <div class="step-number" id="step7">7</div>
                        <div class="step-text">Destruindo maq Ultra</div>
                        <div class="step-status" id="step7-status">Aguardando...</div>
                    </div>
                </div>
                <div id="deploy-result" style="margin-top: 16px; display: none;"></div>
            </div>
        </div>
    </div>

    <!-- Snapshot Detail Modal -->
    <div id="snapshot-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Detalhes do Snapshot</h3>
                <button class="modal-close" onclick="closeSnapshotModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="detail-section">
                    <h4>Informacoes</h4>
                    <div class="detail-row">
                        <span class="detail-label">ID</span>
                        <span class="detail-value" id="detail-id">-</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Data</span>
                        <span class="detail-value" id="detail-time">-</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Hostname</span>
                        <span class="detail-value" id="detail-hostname">-</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Path</span>
                        <span class="detail-value" id="detail-path">-</span>
                    </div>
                </div>

                <div class="detail-section">
                    <h4>Pastas Principais</h4>
                    <div id="detail-folders" class="folder-list">
                        <div class="empty-state">Carregando...</div>
                    </div>
                </div>

                <div class="detail-section">
                    <h4>Nome/Tag</h4>
                    <div class="tag-input-group">
                        <input type="text" id="detail-tag" placeholder="Digite um nome para este snapshot">
                        <button class="btn btn-primary" onclick="saveSnapshotTag()">Salvar</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedSnapshot = null;
        let selectedOffer = null;
        let selectedMachine = null;
        let allSnapshots = [];
        let filtersVisible = false;
        let currentFilters = {};
        let currentProfile = 'balanced';
        let currentRegion = '';
        let hotStartEnabled = false;

        // Profile presets: min_download (Mbps), max_download (Mbps), min_disk (GB)
        const PROFILES = {
            slow: { min_download: 100, max_download: 500, min_disk: 20, label: 'Lenta' },
            economy: { min_download: 500, max_download: 2000, min_disk: 30, label: 'Media' },
            balanced: { min_download: 2000, max_download: 4000, min_disk: 50, label: 'Rapida' },
            performance: { min_download: 4000, max_download: 99999, min_disk: 100, label: 'Ultra' }
        };

        // Select region - AWS style
        function selectRegion(region) {
            currentRegion = region;
            document.querySelectorAll('.region-btn').forEach(b => b.classList.remove('selected'));
            const btnId = region ? 'region-' + region : 'region-all';
            document.getElementById(btnId).classList.add('selected');
            updateProfilePrices();
            loadOffers();
        }

        // Toggle Hot Start mode
        function toggleHotStart() {
            hotStartEnabled = document.getElementById('hot-start-toggle').checked;
            document.getElementById('hot-start-info').style.display = hotStartEnabled ? 'block' : 'none';

            if (hotStartEnabled) {
                // Force performance profile for initial deploy
                selectProfile('performance');
                document.getElementById('btn-deploy').textContent = 'Hot Start (Ultra) + Migrate';
            } else {
                document.getElementById('btn-deploy').textContent = 'Criar Maquina + Restore';
            }
        }

        // GPU change handler - updates prices and loads offers
        function onGpuChange() {
            updateProfilePrices();
            loadOffers();
        }

        // Select profile
        function selectProfile(profile) {
            currentProfile = profile;
            document.querySelectorAll('.profile-card').forEach(c => c.classList.remove('selected'));
            document.getElementById('profile-' + profile).classList.add('selected');
            // Update disk select based on profile
            const diskSelect = document.getElementById('disk-select');
            if (profile === 'slow') diskSelect.value = '20';
            else if (profile === 'economy') diskSelect.value = '30';
            else if (profile === 'balanced') diskSelect.value = '50';
            else diskSelect.value = '100';
            loadOffers();
        }

        // Tab switching
        function showTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`.tab-btn[onclick="showTab('${tab}')"]`).classList.add('active');
            document.getElementById('tab-new').style.display = tab === 'new' ? 'block' : 'none';
            document.getElementById('tab-existing').style.display = tab === 'existing' ? 'block' : 'none';
            if (tab === 'existing') loadMyMachines();
        }

        // Toggle filters
        function toggleFilters() {
            filtersVisible = !filtersVisible;
            document.getElementById('filters-panel').style.display = filtersVisible ? 'block' : 'none';
            document.getElementById('profile-select-group').style.display = filtersVisible ? 'none' : 'block';
            document.getElementById('filters-toggle-text').textContent = filtersVisible ? 'Ocultar filtros avancados' : 'Mostrar filtros avancados';
        }

        // Update range displays
        function updateRangeDisplay(type) {
            const value = document.getElementById('filter-' + type).value;
            const display = document.getElementById('filter-' + type + '-value');
            switch(type) {
                case 'vram': display.textContent = value + ' GB'; break;
                case 'price': display.textContent = '$' + (value/100).toFixed(2) + '/h'; break;
                case 'cpu': display.textContent = value; break;
                case 'ram': display.textContent = value + ' GB'; break;
                case 'disk': display.textContent = value + ' GB'; break;
                case 'download': display.textContent = value; break;
            }
        }

        // Reset filters
        function resetFilters() {
            document.getElementById('filter-gpu').value = '';
            document.getElementById('filter-num-gpus').value = '1';
            document.getElementById('filter-vram').value = '16';
            document.getElementById('filter-price').value = '100';
            document.getElementById('filter-cpu').value = '8';
            document.getElementById('filter-ram').value = '16';
            document.getElementById('filter-disk').value = '50';
            document.getElementById('filter-download').value = '500';
            document.getElementById('filter-cuda').value = '12.0';
            document.getElementById('filter-reliability').value = '0.95';
            document.getElementById('filter-location').value = '';
            document.getElementById('filter-verified').checked = true;
            document.getElementById('filter-static-ip').checked = false;
            document.getElementById('filter-datacenter').checked = false;
            ['vram', 'price', 'cpu', 'ram', 'disk', 'download'].forEach(updateRangeDisplay);
        }

        // Apply filters and load offers
        async function applyFilters() {
            const params = new URLSearchParams();

            const gpu = document.getElementById('filter-gpu').value;
            if (gpu) params.append('gpu', gpu);

            params.append('num_gpus', document.getElementById('filter-num-gpus').value);
            params.append('gpu_ram', document.getElementById('filter-vram').value * 1024); // Convert to MB
            params.append('dph_total', document.getElementById('filter-price').value / 100);
            params.append('cpu_cores', document.getElementById('filter-cpu').value);
            params.append('cpu_ram', document.getElementById('filter-ram').value * 1024);
            params.append('disk_space', document.getElementById('filter-disk').value);
            params.append('inet_down', document.getElementById('filter-download').value);

            const cuda = document.getElementById('filter-cuda').value;
            if (cuda) params.append('cuda_max_good', cuda);

            const reliability = document.getElementById('filter-reliability').value;
            if (reliability) params.append('reliability2', reliability);

            const location = document.getElementById('filter-location').value;
            if (location) params.append('geolocation', location);

            if (document.getElementById('filter-verified').checked) params.append('verified', 'true');
            if (document.getElementById('filter-static-ip').checked) params.append('static_ip', 'true');
            if (document.getElementById('filter-datacenter').checked) params.append('datacenter', 'true');

            const list = document.getElementById('offers-list');
            list.innerHTML = '<div class="empty-state">Buscando ofertas...</div>';

            const res = await fetch('/api/offers?' + params.toString());
            const data = await res.json();
            renderOffers(data.offers);
        }

        // Load snapshots with deduplication
        async function loadSnapshots() {
            const res = await fetch('/api/snapshots');
            const data = await res.json();
            const list = document.getElementById('snapshots-list');

            if (data.error) {
                list.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
                return;
            }

            allSnapshots = data.snapshots;
            const showAll = document.getElementById('show-all-snapshots').checked;

            let snapshotsToShow = showAll ? allSnapshots : data.deduplicated || allSnapshots;

            document.getElementById('snapshot-count').textContent = allSnapshots.length;

            if (snapshotsToShow.length === 0) {
                list.innerHTML = '<div class="empty-state">Nenhum snapshot encontrado</div>';
                return;
            }

            list.innerHTML = snapshotsToShow.map(s => {
                const name = s.tags ? s.tags.split(',')[0].trim() : s.paths.split('/').pop() || s.id.substring(0,8);
                const versionCount = s.version_count || 0;

                return `
                <div class="snapshot-item ${selectedSnapshot === s.id ? 'selected' : ''}" onclick="selectSnapshot('${s.id}', '${s.time}', '${name}')">
                    <div class="snapshot-header">
                        <span class="snapshot-name">${name}</span>
                        <span class="snapshot-date">${s.time}</span>
                    </div>
                    <div class="snapshot-meta">
                        <span>ID: ${s.id.substring(0,8)}</span>
                        <span>Host: ${s.hostname}</span>
                        <span>${s.paths}</span>
                    </div>
                    ${s.tags ? `<div style="margin-top: 4px;"><span class="snapshot-tag">${s.tags}</span></div>` : ''}
                    ${versionCount > 0 ? `<div class="snapshot-versions">${versionCount} versoes anteriores</div>` : ''}
                    <div class="snapshot-actions">
                        <button class="btn btn-sm btn-icon" onclick="event.stopPropagation(); showSnapshotDetails('${s.id}')" title="Ver detalhes">
                            <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 7a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1h-5zM5 9.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h2a.5.5 0 0 1 0 1h-2a.5.5 0 0 1-.5-.5z"/><path d="M9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.5L9.5 0zm0 1v2A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5z"/></svg>
                        </button>
                    </div>
                </div>
            `}).join('');
        }

        function selectSnapshot(id, time, name) {
            selectedSnapshot = id;
            document.querySelectorAll('.snapshot-item').forEach(el => el.classList.remove('selected'));
            event.currentTarget.classList.add('selected');
            document.getElementById('selected-snapshot-banner').style.display = 'block';
            document.getElementById('selected-snapshot-display').textContent = name + ' (' + time + ')';
        }

        // Show snapshot details modal
        async function showSnapshotDetails(id) {
            document.getElementById('snapshot-modal').classList.add('active');

            const snapshot = allSnapshots.find(s => s.id === id);
            if (snapshot) {
                document.getElementById('detail-id').textContent = snapshot.id;
                document.getElementById('detail-time').textContent = snapshot.time;
                document.getElementById('detail-hostname').textContent = snapshot.hostname;
                document.getElementById('detail-path').textContent = snapshot.paths;
                document.getElementById('detail-tag').value = snapshot.tags || '';
                document.getElementById('detail-tag').dataset.snapshotId = id;
            }

            // Load folders
            document.getElementById('detail-folders').innerHTML = '<div class="empty-state">Carregando pastas...</div>';
            const res = await fetch(`/api/snapshot/${id}/folders`);
            const data = await res.json();

            if (data.folders && data.folders.length > 0) {
                document.getElementById('detail-folders').innerHTML = data.folders.map(f => `
                    <div class="folder-item">
                        <span class="folder-name">${f.name}</span>
                        <span class="folder-size">${f.size}</span>
                    </div>
                `).join('');
            } else {
                document.getElementById('detail-folders').innerHTML = '<div class="empty-state">Nenhuma pasta encontrada</div>';
            }
        }

        function closeSnapshotModal() {
            document.getElementById('snapshot-modal').classList.remove('active');
        }

        async function saveSnapshotTag() {
            const id = document.getElementById('detail-tag').dataset.snapshotId;
            const tag = document.getElementById('detail-tag').value.trim();

            if (!tag) {
                alert('Digite um nome para o snapshot');
                return;
            }

            const res = await fetch(`/api/snapshot/${id}/tag`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tag: tag})
            });
            const data = await res.json();

            if (data.success) {
                alert('Tag salva com sucesso!');
                closeSnapshotModal();
                loadSnapshots();
            } else {
                alert('Erro ao salvar tag: ' + (data.error || 'Erro desconhecido'));
            }
        }

        // Load offers (simple mode) - sorted by speed (fastest first)
        async function loadOffers() {
            const gpu = document.getElementById('gpu-select').value;
            if (!gpu) return;

            const list = document.getElementById('offers-list');
            list.innerHTML = '<div class="empty-state">Buscando ofertas...</div>';

            const profile = PROFILES[currentProfile];
            const disk = document.getElementById('disk-select').value;

            // Build query with profile settings
            const params = new URLSearchParams({
                gpu: gpu,
                inet_down: profile.min_download,
                dph_total: profile.max_price,
                disk_space: disk,
                sort_by: 'speed'  // Sort by speed instead of price
            });

            // Add region filter
            if (currentRegion) {
                params.append('geolocation', currentRegion);
            }

            currentFilters = {gpu: gpu, profile: currentProfile, disk: disk, region: currentRegion};
            const res = await fetch(`/api/offers?${params.toString()}`);
            const data = await res.json();
            renderOffers(data.offers);
        }

        function getSpeedClass(mbps) {
            if (mbps >= 4000) return 'fast';
            if (mbps >= 2000) return 'medium';
            if (mbps >= 500) return 'medium';
            return 'slow';
        }

        function getSpeedLabel(mbps) {
            if (mbps >= 4000) return 'Ultra';
            if (mbps >= 2000) return 'Rapida';
            if (mbps >= 500) return 'Media';
            return 'Lenta';
        }

        function renderOffers(offers) {
            const list = document.getElementById('offers-list');

            if (!offers || offers.length === 0) {
                list.innerHTML = '<div class="empty-state">Nenhuma oferta encontrada com esses filtros.<br><small>Tente outro perfil ou GPU.</small></div>';
                return;
            }

            list.innerHTML = offers.slice(0, 15).map(o => `
                <div class="offer-item ${selectedOffer === o.id ? 'selected' : ''}" onclick="selectOffer(${o.id})" data-offer-id="${o.ask_contract_id}">
                    <div>
                        <div class="offer-gpu">
                            ${o.gpu_name} ${o.num_gpus > 1 ? 'x' + o.num_gpus : ''}
                            <span class="offer-speed ${getSpeedClass(o.inet_down)}">${getSpeedLabel(o.inet_down)}</span>
                        </div>
                        <div class="offer-specs">
                            <span>${o.cpu_cores} CPU</span>
                            <span>${Math.round(o.gpu_ram/1024)}GB VRAM</span>
                            <span>${Math.round(o.disk_space || 0)}GB Disco</span>
                            <span>${Math.round(o.inet_down)} Mbps</span>
                        </div>
                        <div class="offer-location">${o.geolocation || 'N/A'} | ${Math.round((o.reliability2 || 0) * 100)}% confiavel</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="offer-price">$${o.dph_total.toFixed(3)}/h</div>
                        <div style="font-size: 0.7em; color: var(--text-muted);">~$${(o.dph_total * 24).toFixed(2)}/dia</div>
                    </div>
                </div>
            `).join('');
        }

        function selectOffer(id) {
            selectedOffer = id;
            document.querySelectorAll('#offers-list .offer-item').forEach(el => el.classList.remove('selected'));
            event.currentTarget.classList.add('selected');
        }

        // Load my machines
        async function loadMyMachines() {
            const res = await fetch('/api/machines');
            const data = await res.json();
            const list = document.getElementById('my-machines');

            if (data.error) {
                list.innerHTML = `<div class="alert alert-warning">${data.error}</div>`;
                return;
            }

            if (data.machines.length === 0) {
                list.innerHTML = '<div class="empty-state">Nenhuma maquina ativa</div>';
                return;
            }

            list.innerHTML = data.machines.map(m => `
                <div class="offer-item ${selectedMachine?.id === m.id ? 'selected' : ''}" onclick="selectMachine(${m.id}, '${m.ssh_host}', ${m.ssh_port}, '${m.public_ipaddr}')">
                    <div>
                        <div class="offer-gpu">${m.gpu_name} #${m.id}</div>
                        <div class="offer-specs">
                            <span>${m.ssh_host}:${m.ssh_port}</span>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span class="status status-running">${m.actual_status}</span>
                        <div class="offer-price">$${(m.dph_total || 0).toFixed(3)}/h</div>
                    </div>
                </div>
            `).join('');
        }

        function selectMachine(id, host, port, ip) {
            selectedMachine = {id, host, port, ip};
            document.querySelectorAll('#my-machines .offer-item').forEach(el => el.classList.remove('selected'));
            event.currentTarget.classList.add('selected');
        }

        // Deploy new machine
        async function deployNew() {
            if (!selectedSnapshot) {
                alert('Selecione um snapshot primeiro');
                return;
            }
            if (!selectedOffer) {
                alert('Selecione uma maquina/oferta');
                return;
            }

            document.getElementById('deploy-modal').classList.add('active');
            resetSteps();

            try {
                // MULTI-START: Create up to 5 machines per round, use first ready
                const BATCH_SIZE = 5;
                const WAIT_PER_ROUND = 10; // seconds
                const MAX_ROUNDS = 3;

                // Get available offers
                updateStep(1, 'active', 'Buscando maquinas...');
                const offersRes = await fetch('/api/offers?' + new URLSearchParams(currentFilters || {}));
                const offersData = await offersRes.json();
                let availableOffers = offersData.offers || [];

                if (availableOffers.length === 0) {
                    updateStep(1, '', 'Nenhuma maquina disponivel');
                    return;
                }

                let allCreatedInstances = [];
                let winner = null;
                let sshInfo = null;

                for (let round = 0; round < MAX_ROUNDS && !winner; round++) {
                    const batchOffers = availableOffers.slice(round * BATCH_SIZE, (round + 1) * BATCH_SIZE);
                    if (batchOffers.length === 0) break;

                    updateStep(1, 'active', `Round ${round + 1}: Criando ${batchOffers.length} maquinas...`);

                    // Create instances in parallel
                    const createPromises = batchOffers.map(offer =>
                        fetch('/api/create-instance', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({offer_id: offer.ask_contract_id})
                        }).then(r => r.json()).catch(() => ({success: false}))
                    );

                    const createResults = await Promise.all(createPromises);
                    const newInstances = createResults.filter(r => r.success).map(r => r.instance_id);
                    allCreatedInstances = allCreatedInstances.concat(newInstances);

                    updateStep(2, 'active', `Aguardando ${allCreatedInstances.length} maquinas...`);

                    // Poll for first ready instance
                    for (let sec = 0; sec < WAIT_PER_ROUND && !winner; sec++) {
                        await sleep(1000);
                        updateStep(2, 'active', `Round ${round + 1}: ${sec + 1}s (${allCreatedInstances.length} maq)`);

                        const statusRes = await fetch('/api/multi-status', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({instance_ids: allCreatedInstances})
                        });
                        const statusData = await statusRes.json();

                        for (const inst of (statusData.instances || [])) {
                            if (inst.status === 'running' && inst.ssh_host) {
                                winner = inst.instance_id;
                                sshInfo = inst;
                                break;
                            }
                        }
                    }
                }

                if (!winner) {
                    updateStep(1, '', 'Timeout - nenhuma maquina iniciou');
                    for (const id of allCreatedInstances) {
                        fetch(`/api/destroy-instance/${id}`, {method: 'DELETE'}).catch(() => {});
                    }
                    return;
                }

                updateStep(1, 'done', `ID: ${winner} (${allCreatedInstances.length} tentativas)`);
                updateStep(2, 'done', sshInfo.ssh_host + ':' + sshInfo.ssh_port);

                // Destroy unused instances
                for (const id of allCreatedInstances.filter(i => i !== winner)) {
                    fetch(`/api/destroy-instance/${id}`, {method: 'DELETE'}).catch(() => {});
                }

                // Step 3: Install restic
                updateStep(3, 'active', 'Instalando...');
                const installRes = await fetch('/api/install-restic', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ssh_host: sshInfo.ssh_host, ssh_port: sshInfo.ssh_port, public_ip: sshInfo.public_ipaddr, ports: sshInfo.ports})
                });
                const installData = await installRes.json();
                if (!installData.success) {
                    updateStep(3, '', 'Erro');
                    return;
                }
                updateStep(3, 'done', 'OK');

                // Step 4: Restore
                updateStep(4, 'active', 'Restaurando...');
                const restoreRes = await fetch('/api/restore-snapshot', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        snapshot_id: selectedSnapshot,
                        ssh_host: sshInfo.ssh_host,
                        ssh_port: sshInfo.ssh_port,
                        public_ip: sshInfo.public_ipaddr,
                        ports: sshInfo.ports
                    })
                });
                const restoreData = await restoreRes.json();
                updateStep(4, 'done', restoreData.duration + 's');

                // HOT START + MIGRATE: If enabled, create cheap machine and migrate
                if (hotStartEnabled) {
                    const migrateTarget = document.getElementById('migrate-target').value;
                    const targetProfile = PROFILES[migrateTarget];

                    // Step 5: Create target machine (cheap)
                    updateStep(5, 'active', 'Criando maquina economica...');

                    // Get offers for target profile
                    const targetFilters = {
                        ...currentFilters,
                        min_download: targetProfile.min_download,
                        max_download: targetProfile.max_download
                    };
                    const targetOffersRes = await fetch('/api/offers?' + new URLSearchParams(targetFilters));
                    const targetOffersData = await targetOffersRes.json();
                    const targetOffers = (targetOffersData.offers || []).slice(0, 5);

                    if (targetOffers.length === 0) {
                        updateStep(5, '', 'Sem maquinas economicas disponiveis');
                        document.getElementById('deploy-result').style.display = 'block';
                        document.getElementById('deploy-result').innerHTML = `
                            <div class="alert alert-warning">
                                <strong>Hot Start OK, migracao falhou</strong><br>
                                Nenhuma maquina economica disponivel. Use a maquina Ultra:<br>
                                SSH: ssh -p ${sshInfo.ssh_port} root@${sshInfo.ssh_host}
                            </div>
                        `;
                        loadMyMachines();
                        return;
                    }

                    // Create target instances
                    const targetCreatePromises = targetOffers.map(offer =>
                        fetch('/api/create-instance', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({offer_id: offer.ask_contract_id})
                        }).then(r => r.json()).catch(() => ({success: false}))
                    );
                    const targetResults = await Promise.all(targetCreatePromises);
                    const targetInstances = targetResults.filter(r => r.success).map(r => r.instance_id);

                    // Wait for target to be ready
                    let targetWinner = null;
                    let targetSsh = null;
                    for (let sec = 0; sec < 60 && !targetWinner; sec++) {
                        await sleep(1000);
                        updateStep(5, 'active', `Aguardando maq economica... ${sec}s`);

                        const statusRes = await fetch('/api/multi-status', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({instance_ids: targetInstances})
                        });
                        const statusData = await statusRes.json();

                        for (const inst of (statusData.instances || [])) {
                            if (inst.status === 'running' && inst.ssh_host) {
                                targetWinner = inst.instance_id;
                                targetSsh = inst;
                                break;
                            }
                        }
                    }

                    if (!targetWinner) {
                        updateStep(5, '', 'Timeout maq economica');
                        for (const id of targetInstances) {
                            fetch(`/api/destroy-instance/${id}`, {method: 'DELETE'}).catch(() => {});
                        }
                        document.getElementById('deploy-result').style.display = 'block';
                        document.getElementById('deploy-result').innerHTML = `
                            <div class="alert alert-warning">
                                <strong>Migracao falhou</strong><br>
                                Timeout ao criar maquina economica. Use a Ultra:<br>
                                SSH: ssh -p ${sshInfo.ssh_port} root@${sshInfo.ssh_host}
                            </div>
                        `;
                        loadMyMachines();
                        return;
                    }

                    updateStep(5, 'done', targetSsh.ssh_host);

                    // Destroy unused target instances
                    for (const id of targetInstances.filter(i => i !== targetWinner)) {
                        fetch(`/api/destroy-instance/${id}`, {method: 'DELETE'}).catch(() => {});
                    }

                    // Step 6: Migrate data via rsync
                    updateStep(6, 'active', 'Migrando dados...');
                    const migrateRes = await fetch('/api/migrate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            source_host: sshInfo.ssh_host,
                            source_port: sshInfo.ssh_port,
                            target_host: targetSsh.ssh_host,
                            target_port: targetSsh.ssh_port,
                            target_public_ip: targetSsh.public_ipaddr,
                            target_ports: targetSsh.ports
                        })
                    });
                    const migrateData = await migrateRes.json();

                    if (!migrateData.success) {
                        updateStep(6, '', 'Erro na migracao');
                        document.getElementById('deploy-result').style.display = 'block';
                        document.getElementById('deploy-result').innerHTML = `
                            <div class="alert alert-warning">
                                <strong>Migracao falhou</strong><br>
                                ${migrateData.error || 'Erro desconhecido'}.<br>
                                Maquina Ultra: ssh -p ${sshInfo.ssh_port} root@${sshInfo.ssh_host}<br>
                                Maquina Econ: ssh -p ${targetSsh.ssh_port} root@${targetSsh.ssh_host}
                            </div>
                        `;
                        loadMyMachines();
                        return;
                    }

                    updateStep(6, 'done', migrateData.duration + 's');

                    // Step 7: Destroy expensive machine
                    updateStep(7, 'active', 'Destruindo maq Ultra...');
                    await fetch(`/api/destroy-instance/${winner}`, {method: 'DELETE'});
                    updateStep(7, 'done', 'OK');

                    document.getElementById('deploy-result').style.display = 'block';
                    document.getElementById('deploy-result').innerHTML = `
                        <div class="alert alert-success">
                            <strong>Hot Start + Migracao concluida!</strong><br>
                            SSH: ssh -p ${targetSsh.ssh_port} root@${targetSsh.ssh_host}<br>
                            Restore Ultra: ${restoreData.duration}s | Migracao: ${migrateData.duration}s<br>
                            <span style="color: var(--accent-green);">Economizando com maquina ${targetProfile.label}!</span>
                        </div>
                    `;
                } else {
                    document.getElementById('deploy-result').style.display = 'block';
                    document.getElementById('deploy-result').innerHTML = `
                        <div class="alert alert-success">
                            <strong>Deploy concluido!</strong><br>
                            SSH: ssh -p ${sshInfo.ssh_port} root@${sshInfo.ssh_host}<br>
                            Tempo restore: ${restoreData.duration}s
                        </div>
                    `;
                }

                loadMyMachines();

            } catch (e) {
                console.error(e);
                document.getElementById('deploy-result').style.display = 'block';
                document.getElementById('deploy-result').innerHTML = `<div class="alert alert-warning">Erro: ${e.message}</div>`;
            }
        }

        // Restore to existing machine
        async function restoreExisting() {
            if (!selectedSnapshot) {
                alert('Selecione um snapshot primeiro');
                return;
            }
            if (!selectedMachine) {
                alert('Selecione uma maquina');
                return;
            }

            const output = document.getElementById('output');
            output.textContent = 'Iniciando restore...\\n';
            document.getElementById('task-status').textContent = 'Executando';
            document.getElementById('task-status').className = 'status status-running';

            const res = await fetch('/api/restore-snapshot', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    snapshot_id: selectedSnapshot,
                    ssh_host: selectedMachine.host,
                    ssh_port: selectedMachine.port,
                    public_ip: selectedMachine.ip
                })
            });
            const data = await res.json();

            output.textContent = data.output || 'Concluido';
            document.getElementById('task-status').textContent = data.success ? 'Concluido' : 'Erro';
            document.getElementById('task-status').className = 'status ' + (data.success ? 'status-ready' : 'status-error');
        }

        // Helpers
        function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

        function resetSteps() {
            for (let i = 1; i <= 7; i++) {
                const stepEl = document.getElementById('step' + i);
                const statusEl = document.getElementById('step' + i + '-status');
                if (stepEl) {
                    stepEl.className = 'step-number';
                }
                if (statusEl) {
                    statusEl.textContent = 'Aguardando...';
                }
            }
            // Show/hide Hot Start steps based on toggle
            const showHotSteps = hotStartEnabled;
            for (let i = 5; i <= 7; i++) {
                const row = document.getElementById('step' + i + '-row');
                if (row) {
                    row.style.display = showHotSteps ? 'flex' : 'none';
                }
            }
            document.getElementById('deploy-result').style.display = 'none';
        }

        function updateStep(num, status, text) {
            const stepEl = document.getElementById('step' + num);
            const statusEl = document.getElementById('step' + num + '-status');
            if (stepEl) {
                stepEl.className = 'step-number ' + status;
            }
            if (statusEl) {
                statusEl.textContent = text;
            }
        }

        function closeModal() {
            document.getElementById('deploy-modal').classList.remove('active');
        }

        // API Key
        async function saveApiKey() {
            const key = document.getElementById('api-key').value;
            const res = await fetch('/api/save-api-key', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({api_key: key})
            });
            const data = await res.json();
            if (data.success) {
                alert('API Key salva!');
                loadSnapshots();
                loadMyMachines();
            }
        }

        // Update profile prices in real-time based on available offers
        async function updateProfilePrices() {
            const gpu = document.getElementById('gpu-select').value;
            if (!gpu) {
                document.getElementById('price-slow').textContent = 'Selecione GPU';
                document.getElementById('price-economy').textContent = 'Selecione GPU';
                document.getElementById('price-balanced').textContent = 'Selecione GPU';
                document.getElementById('price-performance').textContent = 'Selecione GPU';
                return;
            }

            // Set loading state
            document.getElementById('price-slow').textContent = '...';
            document.getElementById('price-economy').textContent = '...';
            document.getElementById('price-balanced').textContent = '...';
            document.getElementById('price-performance').textContent = '...';

            try {
                const res = await fetch(`/api/price-ranges?gpu=${gpu}&region=${currentRegion}`);
                const data = await res.json();

                if (data.slow) {
                    const s = data.slow;
                    document.getElementById('price-slow').innerHTML = `<span style="color: var(--accent-green);">$${s.min.toFixed(2)}</span> - <span>$${s.max.toFixed(2)}</span>/h`;
                    document.getElementById('count-slow').textContent = `${s.count} maquinas`;
                } else {
                    document.getElementById('price-slow').textContent = 'Sem oferta';
                    document.getElementById('count-slow').textContent = '';
                }

                if (data.economy) {
                    const e = data.economy;
                    document.getElementById('price-economy').innerHTML = `<span style="color: var(--accent-green);">$${e.min.toFixed(2)}</span> - <span>$${e.max.toFixed(2)}</span>/h`;
                    document.getElementById('count-economy').textContent = `${e.count} maquinas`;
                } else {
                    document.getElementById('price-economy').textContent = 'Sem oferta';
                    document.getElementById('count-economy').textContent = '';
                }

                if (data.balanced) {
                    const b = data.balanced;
                    document.getElementById('price-balanced').innerHTML = `<span style="color: var(--accent-green);">$${b.min.toFixed(2)}</span> - <span>$${b.max.toFixed(2)}</span>/h`;
                    document.getElementById('count-balanced').textContent = `${b.count} maquinas`;
                } else {
                    document.getElementById('price-balanced').textContent = 'Sem oferta';
                    document.getElementById('count-balanced').textContent = '';
                }

                if (data.performance) {
                    const p = data.performance;
                    document.getElementById('price-performance').innerHTML = `<span style="color: var(--accent-green);">$${p.min.toFixed(2)}</span> - <span>$${p.max.toFixed(2)}</span>/h`;
                    document.getElementById('count-performance').textContent = `${p.count} maquinas`;
                } else {
                    document.getElementById('price-performance').textContent = 'Sem oferta';
                    document.getElementById('count-performance').textContent = '';
                }
            } catch (e) {
                console.error('Error fetching prices:', e);
            }
        }

        // Init
        loadSnapshots();
        loadMyMachines();
        updateProfilePrices();
        ['vram', 'price', 'cpu', 'ram', 'disk', 'download'].forEach(updateRangeDisplay);
    </script>
</body>
</html>
"""

# ==================== ROUTES ====================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username]["password"] == password:
            session["user"] = username
            return redirect(url_for("index"))
        else:
            error = "Usuario ou senha incorretos"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    user = session.get("user")
    vast_api_key = get_user_api_key(user)
    return render_template_string(DASHBOARD_TEMPLATE, user=user, vast_api_key=vast_api_key)

@app.route("/api/snapshots")
@login_required
def get_snapshots():
    try:
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = CONFIG["R2_ACCESS_KEY"]
        env["AWS_SECRET_ACCESS_KEY"] = CONFIG["R2_SECRET_KEY"]
        env["RESTIC_PASSWORD"] = CONFIG["RESTIC_PASSWORD"]
        env["RESTIC_REPOSITORY"] = CONFIG["RESTIC_REPO"]

        result = subprocess.run(
            ["restic", "snapshots", "--json"],
            capture_output=True, text=True, env=env, timeout=30
        )

        if result.returncode != 0:
            return jsonify({"error": result.stderr, "snapshots": [], "deduplicated": []})

        snapshots = json.loads(result.stdout) if result.stdout else []
        formatted = []

        for s in snapshots:
            formatted.append({
                "id": s.get("id", ""),
                "time": s.get("time", "")[:19].replace("T", " "),
                "hostname": s.get("hostname", ""),
                "tags": ", ".join(s.get("tags", [])),
                "paths": ", ".join(s.get("paths", [])),
                "tree": s.get("tree", ""),  # Hash for deduplication
                "parent": s.get("parent", "")
            })

        # Sort by time (newest first)
        formatted.sort(key=lambda x: x["time"], reverse=True)

        # Deduplicate by tree hash - keep only the most recent of each
        tree_groups = defaultdict(list)
        for s in formatted:
            tree_groups[s["tree"]].append(s)

        deduplicated = []
        for tree_hash, group in tree_groups.items():
            # Get the most recent one
            most_recent = group[0]  # Already sorted by time
            most_recent["version_count"] = len(group) - 1
            deduplicated.append(most_recent)

        # Sort deduplicated by time
        deduplicated.sort(key=lambda x: x["time"], reverse=True)

        return jsonify({
            "snapshots": formatted,
            "deduplicated": deduplicated
        })
    except Exception as e:
        return jsonify({"error": str(e), "snapshots": [], "deduplicated": []})

@app.route("/api/snapshot/<snapshot_id>/folders")
@login_required
def get_snapshot_folders(snapshot_id):
    try:
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = CONFIG["R2_ACCESS_KEY"]
        env["AWS_SECRET_ACCESS_KEY"] = CONFIG["R2_SECRET_KEY"]
        env["RESTIC_PASSWORD"] = CONFIG["RESTIC_PASSWORD"]
        env["RESTIC_REPOSITORY"] = CONFIG["RESTIC_REPO"]

        # List only top-level directories
        result = subprocess.run(
            ["restic", "ls", "--json", snapshot_id],
            capture_output=True, text=True, env=env, timeout=120
        )

        if result.returncode != 0:
            return jsonify({"error": result.stderr, "folders": []})

        # Parse JSON lines output - find the backup root and list subdirectories
        folders = []
        backup_root = None
        folder_sizes = {}

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                item = json.loads(line)

                # Skip snapshot metadata line
                if item.get("struct_type") == "snapshot":
                    continue

                item_type = item.get("type", "")
                path = item.get("path", "")
                size = item.get("size", 0)

                if not path:
                    continue

                parts = path.strip("/").split("/")

                # First directory is the backup root (e.g., "workspace" or "root/workspace/MuseTalk1.5")
                if backup_root is None and item_type == "dir" and len(parts) >= 1:
                    backup_root = len(parts)  # Depth of the backup root
                    continue

                # Get folders at depth backup_root + 1 (direct children of backup root)
                if backup_root and len(parts) == backup_root + 1:
                    if item_type == "dir":
                        folder_name = parts[-1]
                        if folder_name not in folder_sizes:
                            folder_sizes[folder_name] = 0
                            folders.append({"name": folder_name, "size": 0, "type": "dir"})

                # Accumulate sizes for folders
                if backup_root and len(parts) >= backup_root + 1:
                    parent_folder = parts[backup_root] if len(parts) > backup_root else None
                    if parent_folder and parent_folder in folder_sizes and size:
                        folder_sizes[parent_folder] += size

            except:
                continue

        # Format sizes
        def format_size(bytes_size):
            if bytes_size >= 1024**3:
                return f"{bytes_size / 1024**3:.1f} GB"
            elif bytes_size >= 1024**2:
                return f"{bytes_size / 1024**2:.1f} MB"
            elif bytes_size >= 1024:
                return f"{bytes_size / 1024:.1f} KB"
            return f"{bytes_size} B"

        # Update folder sizes
        for folder in folders:
            size = folder_sizes.get(folder["name"], 0)
            folder["size"] = format_size(size) if size > 0 else "-"

        return jsonify({"folders": folders[:30]})  # Limit to 30
    except Exception as e:
        return jsonify({"error": str(e), "folders": []})

@app.route("/api/snapshot/<snapshot_id>/tag", methods=["POST"])
@login_required
def set_snapshot_tag(snapshot_id):
    try:
        data = request.json or {}
        tag = data.get("tag", "").strip()

        if not tag:
            return jsonify({"success": False, "error": "Tag vazia"})

        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = CONFIG["R2_ACCESS_KEY"]
        env["AWS_SECRET_ACCESS_KEY"] = CONFIG["R2_SECRET_KEY"]
        env["RESTIC_PASSWORD"] = CONFIG["RESTIC_PASSWORD"]
        env["RESTIC_REPOSITORY"] = CONFIG["RESTIC_REPO"]

        result = subprocess.run(
            ["restic", "tag", "--set", tag, snapshot_id],
            capture_output=True, text=True, env=env, timeout=30
        )

        if result.returncode != 0:
            return jsonify({"success": False, "error": result.stderr})

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/machines")
@login_required
def get_machines():
    user = session.get("user")
    api_key = get_user_api_key(user)

    if not api_key:
        return jsonify({"error": "Configure sua API Key", "machines": []})

    try:
        api_key = api_key.strip().split()[0]
        url = f"https://cloud.vast.ai/api/v0/instances/?owner=me&api_key={api_key}"
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            return jsonify({"error": f"Erro API: {response.status_code}", "machines": []})

        data = response.json()
        return jsonify({"machines": data.get("instances", [])})
    except Exception as e:
        return jsonify({"error": str(e), "machines": []})

@app.route("/api/offers")
@login_required
def get_offers():
    user = session.get("user")
    api_key = get_user_api_key(user)

    if not api_key:
        return jsonify({"offers": []})

    try:
        api_key = api_key.strip().split()[0]

        # Build query from parameters
        query = {"rentable": {"eq": True}}

        # GPU name
        gpu = request.args.get("gpu", "")
        if gpu:
            query["gpu_name"] = {"eq": gpu}

        # Num GPUs
        num_gpus = request.args.get("num_gpus", "1")
        query["num_gpus"] = {"eq": int(num_gpus)}

        # GPU RAM (in MB)
        gpu_ram = request.args.get("gpu_ram")
        if gpu_ram:
            query["gpu_ram"] = {"gte": int(gpu_ram)}

        # Max price
        dph_total = request.args.get("dph_total", "1.0")
        query["dph_total"] = {"lte": float(dph_total)}

        # CPU cores
        cpu_cores = request.args.get("cpu_cores")
        if cpu_cores:
            query["cpu_cores"] = {"gte": int(cpu_cores)}

        # CPU RAM (in MB)
        cpu_ram = request.args.get("cpu_ram")
        if cpu_ram:
            query["cpu_ram"] = {"gte": int(cpu_ram)}

        # Disk space
        disk_space = request.args.get("disk_space")
        if disk_space:
            query["disk_space"] = {"gte": int(disk_space)}

        # Download speed
        inet_down = request.args.get("inet_down")
        if inet_down:
            query["inet_down"] = {"gte": int(inet_down)}

        # CUDA version
        cuda = request.args.get("cuda_max_good")
        if cuda:
            query["cuda_max_good"] = {"gte": float(cuda)}

        # Reliability
        reliability = request.args.get("reliability2")
        if reliability:
            query["reliability2"] = {"gte": float(reliability)}

        # Verified
        verified = request.args.get("verified")
        if verified == "true":
            query["verified"] = {"eq": True}

        # Static IP
        static_ip = request.args.get("static_ip")
        if static_ip == "true":
            query["static_ip"] = {"eq": True}

        # Datacenter
        datacenter = request.args.get("datacenter")
        if datacenter == "true":
            query["datacenter"] = {"eq": True}

        # Location (simplified mapping)
        location = request.args.get("geolocation")
        if location == "US":
            query["geolocation"] = {"in": ["US", "United States", "California", "Texas", "New York"]}
        elif location == "EU":
            query["geolocation"] = {"in": ["Germany", "France", "Netherlands", "UK", "Poland", "Sweden", "Norway"]}
        elif location == "ASIA":
            query["geolocation"] = {"in": ["Japan", "Singapore", "Hong Kong", "Taiwan", "Korea"]}

        import urllib.parse
        q = urllib.parse.quote(json.dumps(query))
        url = f"https://console.vast.ai/api/v0/bundles/?q={q}&api_key={api_key}"

        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return jsonify({"offers": []})

        data = response.json()
        offers = data.get("offers", [])

        # Sort by speed (fastest first) or by price
        sort_by = request.args.get("sort_by", "price")
        if sort_by == "speed":
            # Sort by download speed descending (fastest first)
            offers = sorted(offers, key=lambda x: x.get("inet_down", 0), reverse=True)
        else:
            # Sort by price ascending (cheapest first)
            offers = sorted(offers, key=lambda x: x.get("dph_total", 999))

        return jsonify({"offers": offers[:30]})
    except Exception as e:
        return jsonify({"offers": [], "error": str(e)})

@app.route("/api/price-ranges")
@login_required
def get_price_ranges():
    """Get price ranges for each speed profile based on current GPU and region"""
    user = session.get("user")
    api_key = get_user_api_key(user)

    if not api_key:
        return jsonify({})

    try:
        api_key = api_key.strip().split()[0]
        gpu = request.args.get("gpu", "RTX 4090")
        region = request.args.get("region", "")

        # Base query
        query = {
            "rentable": {"eq": True},
            "num_gpus": {"eq": 1}
        }

        if gpu:
            query["gpu_name"] = {"eq": gpu}

        # Region filter
        if region == "US":
            query["geolocation"] = {"in": ["US", "United States", "California", "Texas", "New York"]}
        elif region == "EU":
            query["geolocation"] = {"in": ["Germany", "France", "Netherlands", "UK", "Poland", "Sweden", "Norway"]}
        elif region == "ASIA":
            query["geolocation"] = {"in": ["Japan", "Singapore", "Hong Kong", "Taiwan", "Korea"]}

        import urllib.parse
        q = urllib.parse.quote(json.dumps(query))
        url = f"https://console.vast.ai/api/v0/bundles/?q={q}&api_key={api_key}"

        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return jsonify({})

        data = response.json()
        offers = data.get("offers", [])

        # Classify offers by speed profile (4 profiles)
        # Lenta: 100-500 Mbps, Media: 500-2000 Mbps, Rapida: 2000-4000 Mbps, Ultra: 4000+ Mbps
        slow_offers = [o for o in offers if o.get("inet_down", 0) >= 100 and o.get("inet_down", 0) < 500]
        economy_offers = [o for o in offers if o.get("inet_down", 0) >= 500 and o.get("inet_down", 0) < 2000]
        balanced_offers = [o for o in offers if o.get("inet_down", 0) >= 2000 and o.get("inet_down", 0) < 4000]
        performance_offers = [o for o in offers if o.get("inet_down", 0) >= 4000]

        result = {}

        if slow_offers:
            prices = [o.get("dph_total", 0) for o in slow_offers]
            result["slow"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "count": len(slow_offers)
            }

        if economy_offers:
            prices = [o.get("dph_total", 0) for o in economy_offers]
            result["economy"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "count": len(economy_offers)
            }

        if balanced_offers:
            prices = [o.get("dph_total", 0) for o in balanced_offers]
            result["balanced"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "count": len(balanced_offers)
            }

        if performance_offers:
            prices = [o.get("dph_total", 0) for o in performance_offers]
            result["performance"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "count": len(performance_offers)
            }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/create-instance", methods=["POST"])
@login_required
def create_instance():
    user = session.get("user")
    api_key = get_user_api_key(user)
    data = request.json or {}
    offer_id = data.get("offer_id")

    if not api_key or not offer_id:
        return jsonify({"success": False, "error": "Missing data"})

    try:
        api_key = api_key.strip().split()[0]
        url = f"https://console.vast.ai/api/v0/asks/{offer_id}/?api_key={api_key}"

        response = requests.put(url, json={
            "client_id": "me",
            "image": "nvidia/cuda:12.1.0-devel-ubuntu22.04",
            "disk": 50
        }, timeout=30)

        result = response.json()
        if result.get("success"):
            return jsonify({"success": True, "instance_id": result.get("new_contract")})
        else:
            return jsonify({"success": False, "error": result.get("msg", "Unknown error")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/instance-status/<int:instance_id>")
@login_required
def instance_status(instance_id):
    user = session.get("user")
    api_key = get_user_api_key(user)

    try:
        api_key = api_key.strip().split()[0]
        url = f"https://console.vast.ai/api/v0/instances/{instance_id}/?api_key={api_key}"
        response = requests.get(url, timeout=15)
        data = response.json()

        # vast.ai returns instance data inside "instances" key as an object
        inst = data.get("instances", data)
        if isinstance(inst, list) and len(inst) > 0:
            inst = inst[0]

        return jsonify({
            "status": inst.get("actual_status"),
            "ssh_host": inst.get("ssh_host"),
            "ssh_port": inst.get("ssh_port"),
            "public_ipaddr": inst.get("public_ipaddr"),
            "ports": inst.get("ports")
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/api/destroy-instance/<int:instance_id>", methods=["DELETE"])
@login_required
def destroy_instance(instance_id):
    """Destroy/cancel a vast.ai instance"""
    user = session.get("user")
    api_key = get_user_api_key(user)

    try:
        api_key = api_key.strip().split()[0]
        url = f"https://console.vast.ai/api/v0/instances/{instance_id}/?api_key={api_key}"
        response = requests.delete(url, timeout=15)
        return jsonify({"success": True, "instance_id": instance_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/multi-status", methods=["POST"])
@login_required
def multi_instance_status():
    """Check status of multiple instances at once"""
    user = session.get("user")
    api_key = get_user_api_key(user)
    data = request.json or {}
    instance_ids = data.get("instance_ids", [])

    if not instance_ids:
        return jsonify({"instances": []})

    try:
        api_key = api_key.strip().split()[0]
        results = []

        for instance_id in instance_ids:
            try:
                url = f"https://console.vast.ai/api/v0/instances/{instance_id}/?api_key={api_key}"
                response = requests.get(url, timeout=10)
                data = response.json()

                inst = data.get("instances", data)
                if isinstance(inst, list) and len(inst) > 0:
                    inst = inst[0]

                results.append({
                    "instance_id": instance_id,
                    "status": inst.get("actual_status"),
                    "ssh_host": inst.get("ssh_host"),
                    "ssh_port": inst.get("ssh_port"),
                    "public_ipaddr": inst.get("public_ipaddr"),
                    "ports": inst.get("ports")
                })
            except:
                results.append({"instance_id": instance_id, "status": "error"})

        return jsonify({"instances": results})
    except Exception as e:
        return jsonify({"error": str(e), "instances": []})

@app.route("/api/install-restic", methods=["POST"])
@login_required
def install_restic():
    data = request.json or {}
    ssh_host = data.get("ssh_host")
    ssh_port = data.get("ssh_port")
    public_ip = data.get("public_ip")

    # vast.ai: use ssh_host (like ssh9.vast.ai) and ssh_port directly
    connect_host = ssh_host or public_ip

    try:
        cmd = f"""ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p {ssh_port} root@{connect_host} '
apt-get update -qq && apt-get install -y restic curl bzip2 &&
cd /tmp &&
curl -LO https://github.com/restic/restic/releases/download/v0.17.3/restic_0.17.3_linux_amd64.bz2 &&
bunzip2 -f restic_0.17.3_linux_amd64.bz2 &&
mv restic_0.17.3_linux_amd64 /usr/local/bin/restic &&
chmod +x /usr/local/bin/restic &&
/usr/local/bin/restic version
'"""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        return jsonify({"success": result.returncode == 0, "output": result.stdout + result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/restore-snapshot", methods=["POST"])
@login_required
def restore_snapshot():
    data = request.json or {}
    snapshot_id = data.get("snapshot_id", "latest")
    ssh_host = data.get("ssh_host")
    ssh_port = data.get("ssh_port")
    public_ip = data.get("public_ip")
    ports = data.get("ports", {})

    # vast.ai: use ssh_host (like ssh9.vast.ai) and ssh_port directly
    connect_host = ssh_host or public_ip

    try:
        cmd = f"""ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=30 -p {ssh_port} root@{connect_host} '
export AWS_ACCESS_KEY_ID="{CONFIG["R2_ACCESS_KEY"]}"
export AWS_SECRET_ACCESS_KEY="{CONFIG["R2_SECRET_KEY"]}"
export RESTIC_PASSWORD="{CONFIG["RESTIC_PASSWORD"]}"
export RESTIC_REPOSITORY="{CONFIG["RESTIC_REPO"]}"

mkdir -p /workspace
START=$(date +%s)
/usr/local/bin/restic restore {snapshot_id} --target / -o s3.connections=32
END=$(date +%s)
echo "DURATION=$((END-START))"
ls -la /workspace/
'"""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)

        # Extract duration
        duration = "?"
        for line in result.stdout.split("\n"):
            if line.startswith("DURATION="):
                duration = line.split("=")[1]

        return jsonify({
            "success": result.returncode == 0,
            "duration": duration,
            "output": result.stdout + result.stderr
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "duration": "?"})

@app.route("/api/migrate", methods=["POST"])
@login_required
def migrate_data():
    """
    Migrate data from source machine to target machine.
    Strategy: Use restic to restore directly on target (faster than rsync between vast.ai machines).

    This is used in Hot Start + Migrate strategy.
    """
    data = request.json or {}
    source_host = data.get("source_host")
    source_port = data.get("source_port")
    target_host = data.get("target_host")
    target_port = data.get("target_port")
    target_public_ip = data.get("target_public_ip")
    target_ports = data.get("target_ports", {})

    if not all([source_host, source_port, target_host, target_port]):
        return jsonify({"success": False, "error": "Missing required parameters"})

    try:
        # Strategy: Instead of rsync between vast.ai machines (which is complex due to SSH proxies),
        # we'll restore the same snapshot on the target machine using restic.
        # This is faster and simpler since both machines are behind SSH proxies.

        # Step 1: Install restic on target (if needed)
        # Step 2: Restore the latest snapshot on target

        target_connect = f"root@{target_host}"

        migrate_script = f'''
# Install restic and restore on target machine
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=60 -o ServerAliveInterval=30 -p {target_port} {target_connect} '
START=$(date +%s)

export AWS_ACCESS_KEY_ID="{CONFIG["R2_ACCESS_KEY"]}"
export AWS_SECRET_ACCESS_KEY="{CONFIG["R2_SECRET_KEY"]}"
export RESTIC_PASSWORD="{CONFIG["RESTIC_PASSWORD"]}"
export RESTIC_REPOSITORY="{CONFIG["RESTIC_REPO"]}"

# Install restic if needed
if ! command -v restic &> /dev/null; then
    echo "Installing restic..."
    apt-get update -qq && apt-get install -y -qq wget bzip2
    wget -q https://github.com/restic/restic/releases/download/v0.16.2/restic_0.16.2_linux_amd64.bz2
    bunzip2 restic_0.16.2_linux_amd64.bz2
    chmod +x restic_0.16.2_linux_amd64
    mv restic_0.16.2_linux_amd64 /usr/local/bin/restic
fi

# Create workspace directory
mkdir -p /workspace

# Restore latest snapshot
echo "Restoring snapshot on target machine..."
/usr/local/bin/restic restore latest --target / -o s3.connections=32

END=$(date +%s)
echo "DURATION=$((END-START))"
echo "Migration completed"
ls -la /workspace/
'
'''

        result = subprocess.run(migrate_script, shell=True, capture_output=True, text=True, timeout=1800)  # 30 min timeout

        # Extract duration
        duration = "?"
        for line in result.stdout.split("\n"):
            if line.startswith("DURATION="):
                duration = line.split("=")[1]

        success = "Migration completed" in result.stdout or result.returncode == 0

        return jsonify({
            "success": success,
            "duration": duration,
            "output": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
            "stderr": result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
        })

    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Migration timeout (30 min)", "duration": "?"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "duration": "?"})

@app.route("/api/save-api-key", methods=["POST"])
@login_required
def save_api_key():
    user = session.get("user")
    data = request.json or {}
    api_key = data.get("api_key", "")

    try:
        set_user_api_key(user, api_key)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)
