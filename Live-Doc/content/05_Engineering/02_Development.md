# Guia de Desenvolvimento

## Requisitos

### Sistema
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Ferramentas
- Git
- Docker (opcional)
- VS Code (recomendado)

---

## Setup Local

### 1. Clone o Repositorio
```bash
git clone https://github.com/dumont-cloud/platform.git
cd platform
```

### 2. Backend (Python)
```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variaveis
cp .env.example .env
# Edite .env com suas credenciais

# Rodar migrations
alembic upgrade head

# Iniciar servidor
uvicorn src.main:app --reload --port 8766
```

### 3. Frontend (React)
```bash
cd web

# Instalar dependencias
npm install

# Iniciar dev server
npm run dev
```

### 4. Docker (Alternativo)
```bash
docker-compose up -d
```

---

## Estrutura do Projeto

```
dumont-cloud/
├── src/                    # Backend Python
│   ├── api/               # Endpoints REST
│   │   └── v1/           # API v1
│   ├── core/             # Config, constants
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic
│   └── main.py           # Entry point
├── web/                   # Frontend React
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/        # Page components
│   │   └── App.jsx       # Root component
│   └── vite.config.js
├── tests/                 # Testes
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── Live-Doc/              # Documentacao
└── docker-compose.yml
```

---

## Padroes de Codigo

### Python
- Black para formatacao
- isort para imports
- flake8 para linting
- mypy para type checking

```bash
# Formatar
black src/
isort src/

# Lint
flake8 src/
mypy src/
```

### JavaScript
- ESLint + Prettier
- Import sorting

```bash
# Formatar e lint
npm run lint
npm run format
```

---

## Git Workflow

### Branches
- `main` - Producao
- `develop` - Desenvolvimento
- `feature/*` - Novas features
- `fix/*` - Bug fixes
- `hotfix/*` - Fixes urgentes

### Commits
Seguimos Conventional Commits:
```
feat: adiciona nova feature
fix: corrige bug
docs: atualiza documentacao
refactor: refatora codigo
test: adiciona testes
chore: tarefas de manutencao
```

### Pull Requests
1. Crie branch a partir de `develop`
2. Faca suas alteracoes
3. Escreva testes
4. Abra PR para `develop`
5. Aguarde code review
6. Merge apos aprovacao

---

## Testes

### Rodar Testes
```bash
# Todos os testes
pytest

# Com coverage
pytest --cov=src

# Apenas unit tests
pytest tests/unit

# Apenas e2e
pytest tests/e2e
```

### Escrever Testes
```python
# tests/unit/test_billing.py
import pytest
from src.services.billing import calculate_cost

def test_calculate_cost_basic():
    # GPU rodando por 1 hora a $0.40/h
    result = calculate_cost(
        gpu="RTX 4090",
        hours=1.0
    )
    assert result == 0.40

def test_calculate_cost_partial_hour():
    # 30 minutos = 0.5 horas
    result = calculate_cost(
        gpu="RTX 4090",
        hours=0.5
    )
    assert result == 0.20
```

---

## Debug

### Logs
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Operacao concluida")
logger.warning("Alerta: saldo baixo")
logger.error("Erro ao conectar", exc_info=True)
```

### Breakpoints
```python
# Adicione em qualquer lugar
import pdb; pdb.set_trace()
```

### VS Code Debug
Use a configuracao `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.main:app", "--reload"]
    }
  ]
}
```

---

## Database Migrations

### Criar Migration
```bash
alembic revision --autogenerate -m "add user preferences"
```

### Aplicar Migration
```bash
alembic upgrade head
```

### Rollback
```bash
alembic downgrade -1
```

---

## Deploy

### Staging
```bash
git push origin develop
# CI/CD faz deploy automatico para staging
```

### Producao
```bash
# Criar tag de release
git tag v1.2.3
git push origin v1.2.3
# CI/CD faz deploy para producao
```

---

## Recursos Uteis

### Documentacao
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [React Docs](https://react.dev)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org)

### Ferramentas
- Postman/Insomnia para testar API
- pgAdmin para PostgreSQL
- RedisInsight para Redis
