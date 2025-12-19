# Deploy e Operacoes

## Ambientes

| Ambiente | URL | Uso |
|----------|-----|-----|
| **Development** | localhost:8766 | Dev local |
| **Staging** | staging.dumontcloud.com | Testes |
| **Production** | dumontcloud.com | Usuarios |

---

## CI/CD Pipeline

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest --cov

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: ./deploy.sh staging

  deploy-prod:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: ./deploy.sh production
```

---

## Deploy Manual

### Staging
```bash
ssh ubuntu@staging.dumontcloud.com

cd /home/ubuntu/dumont-cloud
git pull origin develop
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

sudo systemctl restart dumont-api
```

### Production
```bash
ssh ubuntu@dumontcloud.com

cd /home/ubuntu/dumont-cloud
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Deploy com zero downtime
sudo systemctl reload dumont-api
```

---

## Servicos Systemd

### API Service
```ini
# /etc/systemd/system/dumont-api.service
[Unit]
Description=Dumont Cloud API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/dumont-cloud
Environment="PATH=/home/ubuntu/dumont-cloud/venv/bin"
ExecStart=/home/ubuntu/dumont-cloud/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8766
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Comandos
```bash
sudo systemctl start dumont-api
sudo systemctl stop dumont-api
sudo systemctl restart dumont-api
sudo systemctl status dumont-api
sudo journalctl -u dumont-api -f
```

---

## Nginx

### Configuracao
```nginx
# /etc/nginx/sites-available/dumontcloud
server {
    server_name dumontcloud.com www.dumontcloud.com;

    location / {
        proxy_pass http://127.0.0.1:8766;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/dumontcloud.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dumontcloud.com/privkey.pem;
}
```

### Comandos
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Monitoramento

### Health Checks
```bash
# API health
curl https://dumontcloud.com/health

# Response esperado
{"status":"healthy","version":"3.0.0"}
```

### Logs
```bash
# API logs
sudo journalctl -u dumont-api -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Metricas
Acesse Grafana em: https://grafana.dumontcloud.com

Dashboards disponiveis:
- API Performance
- GPU Usage
- Billing
- Errors

---

## Troubleshooting

### API nao responde
```bash
# Verificar status
sudo systemctl status dumont-api

# Verificar logs
sudo journalctl -u dumont-api -n 100

# Reiniciar
sudo systemctl restart dumont-api
```

### Erro 502 Bad Gateway
```bash
# Verificar se API esta rodando
curl http://127.0.0.1:8766/health

# Se nao, reiniciar
sudo systemctl restart dumont-api
```

### Disco cheio
```bash
# Verificar uso
df -h

# Limpar logs antigos
sudo journalctl --vacuum-time=7d

# Limpar cache pip
pip cache purge
```

### Memoria alta
```bash
# Verificar uso
free -h

# Identificar processos
top -o %MEM

# Reiniciar se necessario
sudo systemctl restart dumont-api
```

---

## Backup

### Database
```bash
# Backup manual
pg_dump -U dumont dumont_db > backup_$(date +%Y%m%d).sql

# Restore
psql -U dumont dumont_db < backup_20240115.sql
```

### Automatico (Cron)
```cron
# /etc/cron.d/dumont-backup
0 3 * * * ubuntu pg_dump -U dumont dumont_db | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

---

## Rollback

### Codigo
```bash
# Ver commits recentes
git log --oneline -10

# Reverter para commit anterior
git revert HEAD

# Ou checkout de versao especifica
git checkout v1.2.2
```

### Database
```bash
# Rollback ultima migration
alembic downgrade -1

# Rollback para versao especifica
alembic downgrade abc123
```
