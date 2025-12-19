#!/bin/bash
"""
Instala VS Code Server (code-server) com failover automático
"""

# Função para instalar code-server
install_code_server() {
    echo "📦 Instalando code-server..."
    
    # Download e install
    curl -fsSL https://code-server.dev/install.sh | sh
    
    # Configurar
    mkdir -p ~/.config/code-server
    cat > ~/.config/code-server/config.yaml << EOF
bind-addr: 0.0.0.0:8080
auth: password
password: dumont-secure-password-2024  # Trocar por senha segura
cert: false
EOF
    
    # Criar serviço systemd
    cat > /etc/systemd/system/code-server.service << EOF
[Unit]
Description=Code Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace
ExecStart=/usr/bin/code-server /workspace
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Iniciar serviço
    systemctl daemon-reload
    systemctl enable code-server
    systemctl start code-server
    
    echo "✅ code-server instalado e rodando em :8080"
}

# Instalar extensões úteis
install_extensions() {
    echo "🔧 Instalando extensões..."
    
    # Python
    code-server --install-extension ms-python.python
    code-server --install-extension ms-python.vscode-pylance
    
    # Git
    code-server --install-extension eamodio.gitlens
    
    # Remote Development
    code-server --install-extension ms-vscode-remote.remote-ssh
    
    # Jupyter
    code-server --install-extension ms-toolsai.jupyter
    
    # Docker
    code-server --install-extension ms-azuretools.vscode-docker
    
    echo "✅ Extensões instaladas"
}

# Configurar health check endpoint
setup_health_check() {
    echo "🏥 Configurando health check..."
    
    cat > /workspace/.vscode-health << 'EOF'
#!/bin/bash
# Health check para code-server
if systemctl is-active --quiet code-server; then
    echo "OK"
    exit 0
else
    echo "FAIL"
    exit 1
fi
EOF
    
    chmod +x /workspace/.vscode-health
}

# Main
main() {
    install_code_server
    sleep 5
    install_extensions
    setup_health_check
    
    echo ""
    echo "="*70
    echo "✅ VS Code Server instalado com sucesso!"
    echo "="*70
    echo ""
    echo "Acesse: http://$(curl -s ifconfig.me):8080"
    echo "Senha: dumont-secure-password-2024"
    echo ""
    echo "Para trocar senha:"
    echo "  nano ~/.config/code-server/config.yaml"
    echo "  systemctl restart code-server"
    echo ""
}

main
