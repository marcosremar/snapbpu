# ⚡ Quick Start - Dumont Cloud

## Setup em 5 Minutos

### 1️⃣ Clone & Install

```bash
# Clone do repositório
git clone https://github.com/dumont-cloud/platform.git
cd platform

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2️⃣ Configurar Credenciais

Crie o arquivo `.env` na raiz:

```bash
# Vast.ai (GPU Provider)
VAST_API_KEY=sua_chave_vast_ai

# Google Cloud (Backup)
GCP_CREDENTIALS={"type": "service_account", "project_id": "..."}

# Backblaze B2 / Cloudflare R2 (Storage)
R2_ENDPOINT=https://your-endpoint.r2.cloudflarestorage.com
R2_ACCESS_KEY=sua_access_key
R2_SECRET_KEY=sua_secret_key

# Restic (Snapshots)
RESTIC_PASSWORD=senha_segura_para_criptografia

# Database
DATABASE_URL=postgresql://user:password@localhost/dumontcloud
```

### 3️⃣ Inicializar Database

```bash
# Criar tabelas
python init_db.py

# (Opcional) Popular com dados demo
python scripts/seed_demo_data.py
```

### 4️⃣ Rodar Backend

```bash
# Modo desenvolvimento
python -m uvicorn src.main:app --reload --port 8766

# Modo produção
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8766
```

### 5️⃣ Rodar Frontend

```bash
cd web
npm install
npm run dev  # Desenvolvimento (http://localhost:5173)
# ou
npm run build && npm run preview  # Produção
```

---

## ✅ Verificação

Acesse:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8766/docs (Swagger UI)
- **Metrics**: http://localhost:9090 (Prometheus)

---

## 🔥 Modo Demo (Sem Credenciais)

Para testar sem configurar APIs externas:

```bash
# Backend em modo demo
DEMO_MODE=true python -m uvicorn src.main:app --port 8766

# Acesse
http://localhost:8766/demo-app
```

O modo demo simula GPUs fictícias (RTX 4090, A100, RTX 3090) e permite testar toda a interface.

---

## 🚨 Troubleshooting Comum

### Erro: "ModuleNotFoundError: No module named 'fastapi'"
**Solução**: `pip install -r requirements.txt`

### Erro: "Connection refused on port 8766"
**Solução**: Verifique se outro processo está usando a porta: `lsof -i :8766`

### Frontend não conecta ao backend
**Solução**: Atualize `web/.env` com `VITE_API_URL=http://localhost:8766`

---

## 📚 Próximos Passos

- Leia a [Arquitetura](Architecture.md) para entender o sistema
- Veja a [API Reference](API_Reference.md) para integrar com o backend
- Configure [Monitoramento](../Operations/Monitoring.md) para produção
