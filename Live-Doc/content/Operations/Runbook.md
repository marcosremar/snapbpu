# 🚨 Runbook - Dumont Cloud

## Cenários de Incidente

### 1. Database Down

**Sintomas**: API retorna 500, `/health` mostra `database: error`

**Ações**:
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
sudo systemctl restart dumont-cloud
```

---

### 2. Vast.ai API Down

**Sintomas**: Não cria instâncias, HTTPError 503

**Ações**:
```bash
# Verificar status
curl https://vast.ai/api/v0/health

# Usar fallback GCP (editar config.json)
{"fallback_provider": "gcp"}

# Notificar usuários
python scripts/broadcast_alert.py --message "Usando GCP como fallback"
```

---

### 3. Instance Stuck "Creating"

**Sintomas**: Status em `creating` >10min

**Ações**:
```bash
# Verificar no Vast
python scripts/check_vast_instance.py --id INSTANCE_ID

# Recriar
curl -X DELETE /api/instances/INSTANCE_ID
curl -X POST /api/instances -d '{"gpu_type": "RTX 4090"}'
```

---

### 4. Custo Disparou

**Sintomas**: Burn rate >$4/hora

**Ações**:
```bash
# Listar instâncias ativas
curl /api/machines | jq '.machines[] | select(.status == "running")'

# Hibernar todas
python scripts/force_hibernate_all.py --idle-threshold 1
```

---

### 5. Acesso Não Autorizado

**Sintomas**: Múltiplas tentativas 401

**Ações**:
```bash
# Bloquear IP
sudo ufw deny from ATTACKER_IP

# Invalidar tokens
redis-cli FLUSHDB

# Rotacionar JWT secret
# Editar .env: JWT_SECRET=novo_secret
sudo systemctl restart dumont-cloud
```

---

## Scripts Úteis

```bash
# Restart completo
sudo systemctl restart dumont-cloud nginx postgresql

# Logs em tempo real
sudo journalctl -u dumont-cloud -f

# Health check
curl https://dumontcloud.com/health | jq .
```

---

**Owner**: DevOps Team  
**Última revisão**: 2025-12-19
