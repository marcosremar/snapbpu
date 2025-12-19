# 🔐 Security & Credentials - Dumont Cloud

## Gestão de API Keys

### 🔑 Credenciais Necessárias

Para operar o Dumont Cloud, você precisa de:

| Provider | Tipo | Onde Conseguir |
|----------|------|----------------|
| **Vast.ai** | API Key | https://vast.ai/console/account/ |
| **Google Cloud** | Service Account JSON | https://console.cloud.google.com/iam-admin/serviceaccounts |
| **Backblaze B2 / R2** | Access Key + Secret | https://secure.backblaze.com/app_keys.htm |
| **Restic** | Password | Gerado localmente |

---

## 📂 Armazenamento Seguro (Produção)

### ❌ NUNCA fazer:
```bash
# NÃO comitar no Git
git add .env  # ❌ PERIGOSO

# NÃO hardcoded no código
VAST_API_KEY = "abc123"  # ❌ PERIGOSO
```

### ✅ Método Recomendado: Variáveis de Ambiente

```bash
# .env (adicione ao .gitignore!)
VAST_API_KEY=your_vast_api_key_here
GCP_CREDENTIALS={"type": "service_account", "project_id": "..."}
R2_ACCESS_KEY=your_r2_access_key
R2_SECRET_KEY=your_r2_secret_key
RESTIC_PASSWORD=ultra_secure_password_123
JWT_SECRET=generated_with_openssl_rand_hex_32
```

**Gerar JWT Secret:**
```bash
openssl rand -hex 32
```

---

## 🛡️ Políticas de Senha

### Requisitos Mínimos
- **Tamanho**: ≥ 8 caracteres
- **Complexidade**: Letra maiúscula + minúscula + número
- **Proibido**: Senhas comuns (`password123`, `admin`, etc.)

### Exemplo de Validação (Backend)

```python
# src/core/security.py
import re
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

---

## 🔒 2FA (Two-Factor Authentication)

### Status Atual
⚠️ **Não implementado** no MVP.

### Roadmap (Q2 2025)
- [ ] TOTP (Google Authenticator, Authy)
- [ ] SMS Backup
- [ ] Recovery Codes

---

## 🔄 Rotação de Secrets

### Frequência Recomendada

| Secret | Rotação |
|--------|---------|
| **JWT Secret** | A cada 6 meses |
| **Vast.ai API Key** | Anual ou se comprometido |
| **GCP Service Account** | Anual |
| **Restic Password** | Nunca (perde acesso aos snapshots!) |

### Como Rotacionar JWT Secret

```bash
# 1. Gerar novo secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. Atualizar .env
echo "JWT_SECRET=$NEW_SECRET" >> .env

# 3. Restart da API
sudo systemctl restart dumont-cloud

# ⚠️ TODOS os usuários precisarão fazer login novamente
```

---

## 🚨 Em Caso de Vazamento

### 1. **API Key Vazou**

```bash
# 1. Revogar imediatamente no provider
# Vast.ai: https://vast.ai/console/account/
# GCP: https://console.cloud.google.com/iam-admin/serviceaccounts

# 2. Gerar nova key

# 3. Atualizar .env

# 4. Restart
sudo systemctl restart dumont-cloud
```

### 2. **Database Comprometida**

```bash
# 1. Forçar logout de todos os usuários
redis-cli FLUSHDB

# 2. Rotacionar JWT secret
NEW_SECRET=$(openssl rand -hex 32)
sed -i "s/JWT_SECRET=.*/JWT_SECRET=$NEW_SECRET/" .env

# 3. Notificar usuários
python scripts/send_security_alert.py

# 4. Restart
sudo systemctl restart dumont-cloud
```

---

## 📋 Checklist de Segurança (Produção)

### Servidor
- [ ] Firewall ativado (ufw)
- [ ] SSH com chave pública (não senha)
- [ ] Fail2ban instalado
- [ ] Updates automáticos (`unattended-upgrades`)
- [ ] Backups diários do PostgreSQL

### Aplicação
- [ ] `.env` no `.gitignore`
- [ ] HTTPS obrigatório (redirecionamento)
- [ ] CORS configurado corretamente
- [ ] Rate limiting ativo (10 req/min)
- [ ] SQL Injection prevenido (ORMs)

### Monitoring
- [ ] Alertas de login suspeito (P99 de localização)
- [ ] Alertas de custo anormal (>$100/dia)
- [ ] Logs centralizados

---

## 🔍 Auditoria de Acessos

### Logs de Autenticação

```python
# src/api/auth.py
import logging

logger = logging.getLogger("security")

@app.post("/api/auth/login")
async def login(credentials: LoginRequest):
    logger.info(
        f"Login attempt: {credentials.email} from IP {request.client.host}"
    )
    # ...
```

### Verificar Logs

```bash
# Ver últimos logins
grep "Login attempt" /var/log/dumont-cloud/security.log | tail -n 20

# Detectar força bruta (>5 tentativas mesma IP)
grep "Login failed" /var/log/dumont-cloud/security.log | \
  awk '{print $NF}' | sort | uniq -c | sort -rn | head
```

---

## 📚 Compliance

### LGPD / GDPR
- ✅ Senhas hasheadas (bcrypt, cost 12)
- ✅ Dados em trânsito criptografados (TLS 1.3)
- ✅ Snapshots criptografados (Restic AES-256)
- ⚠️ Direito ao esquecimento (em desenvolvimento)

### SOC 2 Type II
🚧 **Planejado para Q3 2025**

---

**Última atualização**: 2025-12-19  
**Owner**: Security Team
