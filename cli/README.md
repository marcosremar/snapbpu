# Dumont Cloud CLI

> Professional command-line interface for Dumont Cloud GPU management

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 🚀 Features

- ✅ **Auto-Discovery** - Automatically discovers API endpoints via OpenAPI
- ✅ **Natural Commands** - Intuitive command structure (e.g., `dumont instance list`)
- ✅ **Wizard Deploy** - Multi-start parallel deployment for fast GPU provisioning
- ✅ **Model Installation** - One-command Ollama + LLM model setup
- ✅ **Smart Auth** - Automatic JWT token management
- ✅ **Modular Design** - Clean separation of concerns
- ✅ **Easy to Extend** - Add new commands without touching core code

## 📦 Installation

### Option 1: System-wide (Recommended)

```bash
cd /home/marcos/dumontcloud/cli
./scripts/install.sh
```

This creates a global `dumont` command accessible from anywhere.

### Option 2: Python Package (Development)

```bash
cd /home/marcos/dumontcloud/cli
pip install -e .
```

This installs as an editable Python package.

### Option 3: Direct Execution

```bash
cd /home/marcos/dumontcloud
python -m cli instance list
```

## 🎯 Quick Start

### Authentication

```bash
# Login
dumont auth login user@email.com password

# Check auth status
dumont auth me
```

### Instance Management

```bash
# List instances
dumont instance list

# Deploy GPU with wizard (fast parallel deployment)
dumont wizard deploy "RTX 4090"
dumont wizard deploy gpu="A100" speed=fast price=2.5

# Get instance details
dumont instance get 12345

# Pause/Resume
dumont instance pause 12345
dumont instance resume 12345

# Delete
dumont instance delete 12345
```

### Model Installation

```bash
# Install Ollama + model on instance
dumont model install 12345 llama3.2
dumont model install 12345 qwen3:0.6b
dumont model install 12345 codellama:7b
```

### Snapshots

```bash
# List snapshots
dumont snapshot list

# Create backup
dumont snapshot create name=backup instance_id=12345

# Restore
dumont snapshot restore snapshot_id=snap_abc instance_id=12345
```

## 📋 All Available Commands (100+)

### Failover Orchestrator
```bash
dumont failover strategies              # Ver estrategias
dumont failover settings-global         # Config global
dumont failover settings-machines       # Config por maquina
dumont failover readiness <id>          # Verificar prontidao
dumont failover status <id>             # Status do failover
dumont failover execute                 # Executar failover
dumont failover test <id>               # Testar failover
dumont failover regional-volume-list    # Listar volumes
dumont failover regional-volume-create  # Criar volume
```

### CPU Standby
```bash
dumont standby status                   # Status geral
dumont standby configure                # Configurar standby
dumont standby associations             # Listar associacoes
dumont standby pricing                  # Ver precos
dumont standby failover-simulate <id>   # Simular failover
dumont standby failover-report          # Relatorio
dumont standby failover-fast <id>       # Failover rapido
```

### GPU Warm Pool
```bash
dumont warmpool hosts                   # Listar hosts
dumont warmpool status <id>             # Status da maquina
dumont warmpool provision               # Provisionar
dumont warmpool enable <id>             # Habilitar
dumont warmpool disable <id>            # Desabilitar
```

### Metrics & Spot Market
```bash
dumont metric market                    # Metricas de mercado
dumont metric providers                 # Comparar provedores
dumont metric gpus                      # Lista de GPUs
dumont metric spot-monitor              # Monitorar spot
dumont metric spot-llm-gpus             # GPUs para LLM
dumont metric spot-availability         # Disponibilidade
```

### Savings & Economy
```bash
dumont saving summary                   # Resumo de economia
dumont saving history                   # Historico
dumont saving breakdown                 # Detalhamento
dumont hibernation stats                # Stats hibernacao
```

### Fine-tuning
```bash
dumont finetune models                  # Modelos disponiveis
dumont finetune jobs                    # Listar jobs
dumont finetune create                  # Criar job
dumont finetune logs <job_id>           # Ver logs
```

### Settings
```bash
dumont setting list                     # Ver configuracoes
dumont setting cloud-storage            # Config cloud storage
dumont balance list                     # Ver saldo
```

### AI Wizard & Advisor
```bash
dumont ai-wizard analyze                # Analisar requisitos
dumont advisor recommend                # Recomendacoes
```

## 🧪 Testing

### Run all CLI tests
```bash
cd /home/marcos/dumontcloud/cli
pytest tests/ -v -s
```

### Run by group
```bash
pytest tests/test_cli_real.py -v -s -k "Auth"
pytest tests/test_cli_real.py -v -s -k "Instance"
pytest tests/test_cli_real.py -v -s -k "Failover"
pytest tests/test_cli_real.py -v -s -k "Metrics"
```

### Real integration tests (USES CREDITS!)
```bash
pytest tests/test_real_integration.py -v -s
pytest tests/test_all_endpoints_real.py -v -s
```

## 🏗️ Architecture

```
cli/
├── __init__.py
├── __main__.py                 # Main entry point
│
├── commands/                   # Command modules
│   ├── __init__.py
│   ├── base.py                # Command builder from OpenAPI
│   ├── wizard.py              # Wizard deploy
│   └── model.py               # Model installation
│
├── utils/                      # Utilities
│   ├── __init__.py
│   ├── api_client.py          # HTTP API client
│   ├── ssh_client.py          # SSH execution
│   └── token_manager.py       # JWT token management
│
├── bin/
│   └── dumont                 # Entry point script
│
├── scripts/                    # Installation scripts
│   └── install.sh
│
├── docs/                       # Documentation
│   ├── README.md
│   ├── NATURAL.md
│   └── SYSTEM.md
│
├── tests/                      # Tests
│   └── __init__.py
│
├── setup.py                    # Package setup
├── pyproject.toml             # Modern packaging config
└── README.md                   # This file
```

## 📚 Documentation

- [Natural Commands Guide](docs/NATURAL.md) - User-friendly command reference
- [System Integration](docs/SYSTEM.md) - System-wide installation guide
- [API Documentation](../docs/) - Backend API docs

## 🛠️ Development

### Adding New Commands

The CLI automatically discovers new API endpoints! Just add them to the FastAPI backend:

```python
@router.post("/api/v1/deployments/create")
async def create_deployment(data: DeploymentCreate):
    return {"deployment_id": "123"}
```

The CLI will automatically make it available:

```bash
dumont deployment create
```

### Custom Commands

For complex operations (like wizard deploy), create a new module in `commands/`:

```python
# cli/commands/my_feature.py
class MyFeatureCommands:
    def __init__(self, api_client):
        self.api = api_client

    def do_something(self, arg1, arg2):
        # Your logic here
        pass
```

Then register it in `__main__.py`.

### Running Tests

```bash
cd cli
pytest tests/
```

## 🎨 Design Principles

1. **Auto-Discovery First** - Let OpenAPI do the heavy lifting
2. **Modular** - Each feature in its own module
3. **Clean Separation** - Utils handle infrastructure, commands handle business logic
4. **User-Friendly** - Clear error messages, helpful output
5. **Extensible** - Easy to add new commands without refactoring

## 🤝 Contributing

1. Add new command modules in `commands/`
2. Add utilities in `utils/`
3. Update documentation
4. Add tests in `tests/`
5. Follow existing code style

## 📄 License

MIT License - see [LICENSE](../LICENSE) for details

## 🙏 Credits

Built with ❤️ by the Dumont Cloud team.

Inspired by:
- AWS CLI
- Google Cloud CLI
- Claude Code CLI
