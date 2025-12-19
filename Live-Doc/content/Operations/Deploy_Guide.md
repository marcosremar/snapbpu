# 🚀 Deploy Guide - Dumont Cloud

## Pré-requisitos

- [ ] Servidor Ubuntu 22.04 LTS (mínimo: 4 CPU, 8GB RAM)
- [ ] Domínio configurado (ex: `dumontcloud.com`)
- [ ] Credenciais: Vast.ai, GCP, Backblaze B2
- [ ] PostgreSQL 15+ instalado
- [ ] Nginx instalado

---

## 1. Configurar Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install python3.10 python3-pip postgresql nginx redis-server -y

# Instalar s5cmd (upload ultra-rápido)
wget https://github.com/peak/s5cmd/releases/latest/download/s5cmd_Linux-64bit.tar.gz
tar -xzf s5cmd_Linux-64bit.tar.gz
sudo mv s5cmd /usr/local/bin/
```

---

## 2. Clonar & Setup

```bash
# Clone do repo
git clone https://github.com/dumont-cloud/platform.git /opt/dumont-cloud
cd /opt/dumont-cloud

# Criar venv
python3 -m venv venv
source venv/bin/activate

# Instalar deps
pip install -r requirements.txt
pip install gunicorn  # Production ASGI server
```

---

## 3. Configurar Database

```bash
# Criar usuário e database
sudo -u postgres psql

postgres=# CREATE USER dumontcloud WITH PASSWORD 'senha_segura';
postgres=# CREATE DATABASE dumontcloud OWNER dumontcloud;
postgres=# \q

# Migrar schema
cd /opt/dumont-cloud
python init_db.py
```

---

## 4. Configurar Env Vars

Crie `/opt/dumont-cloud/.env`:

```bash
# Database
DATABASE_URL=postgresql://dumontcloud:senha_segura@localhost/dumontcloud

# Vast.ai
VAST_API_KEY=YOUR_VAST_API_KEY

# Google Cloud
GCP_CREDENTIALS={"type": "service_account", "project_id": "..."}

# Storage
R2_ENDPOINT=https://your-endpoint.r2.cloudflarestorage.com
R2_ACCESS_KEY=YOUR_R2_ACCESS
R2_SECRET_KEY=YOUR_R2_SECRET
RESTIC_PASSWORD=ultra_secure_password_123

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=generate_with_openssl_rand_hex_32

# Monitoring
PROMETHEUS_PORT=9090
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Gere JWT secret:
```bash
openssl rand -hex 32
```

---

## 5. Configurar Systemd (Auto-start)

Crie `/etc/systemd/system/dumont-cloud.service`:

```ini
[Unit]
Description=Dumont Cloud API
After=network.target postgresql.service

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/opt/dumont-cloud
Environment="PATH=/opt/dumont-cloud/venv/bin"
ExecStart=/opt/dumont-cloud/venv/bin/gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8766
Restart=always

[Install]
WantedBy=multi-user.target
```

Ativar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dumont-cloud
sudo systemctl start dumont-cloud
sudo systemctl status dumont-cloud  # Verificar se está rodando
```

---

## 6. Configurar Nginx (Reverse Proxy)

Crie `/etc/nginx/sites-available/dumontcloud`:

```nginx
server {
    listen 80;
    server_name dumontcloud.com www.dumontcloud.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dumontcloud.com www.dumontcloud.com;

    ssl_certificate /etc/letsencrypt/live/dumontcloud.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dumontcloud.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8766;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Ativar:
```bash
sudo ln -s /etc/nginx/sites-available/dumontcloud /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 7. SSL/TLS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d dumontcloud.com -d www.dumontcloud.com
sudo systemctl reload nginx
```

Auto-renovação (cronjob já configurado automaticamente).

---

## 8. Deploy Frontend (React)

```bash
cd /opt/dumont-cloud/web

# Build estático
npm install
npm run build

# Servir via Nginx
sudo cp -r dist/* /var/www/html/

# Atualizar Nginx config para servir SPA
# (adicionar try_files $uri /index.html; na location /)
```

---

## 9. Configurar Prometheus (Metrics)

Crie `/etc/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dumont-cloud'
    static_configs:
      - targets: ['localhost:9090']
```

Restart:
```bash
sudo systemctl restart prometheus
```

---

## 10. Health Check

```bash
# API
curl https://dumontcloud.com/health
# Expected: {"status": "ok"}

# Prometheus
curl http://localhost:9090/metrics
# Expected: métricas exportadas

# Database
psql postgresql://dumontcloud:senha@localhost/dumontcloud -c "SELECT 1;"
# Expected: 1
```

---

## 🔒 Hardening de Segurança (Recomendado)

```bash
# Firewall
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Fail2ban (proteção contra brute force)
sudo apt install fail2ban -y
sudo systemctl enable fail2ban

# Desabilitar root SSH
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

---

## 📊 Monitoring Post-Deploy

- **Logs**: `sudo journalctl -u dumont-cloud -f`
- **Metrics**: `http://your-server:9090/metrics`
- **Grafana Dashboard**: Importe template `dashboards/dumont-cloud.json`

---

**Resultado Final**:
- ✅ API rodando em `https://dumontcloud.com`
- ✅ Auto-restart em caso de crash
- ✅ SSL/TLS configurado
- ✅ Métricas em tempo real
- ✅ Backups automáticos

**Tempo Total**: ~45 minutos
