# Dumont Cloud - GPU Cloud Orchestration Platform (v3.2)

## Project Overview

High-performance GPU cloud orchestration platform that combines:
- **Vast.ai/TensorDock** for low-cost GPU instances
- **GCP** for CPU standby failover
- **B2/R2/S3** for high-speed snapshots
- **Auto-hibernation** for cost savings

**Critical priorities**: Fast boot time (< 30s) and automatic cost reduction via hibernation.

## Architecture

### Tech Stack
- **Backend**: FastAPI + Pydantic v2 + JWT auth
- **Frontend**: React 18 + Redux + Tailwind CSS + shadcn/ui
- **CLI**: Python + Click
- **Storage**: Multi-provider (B2, R2, S3, Wasabi)
- **GPU Providers**: Vast.ai, TensorDock, GCP

### Key Design Patterns
1. **Strategy Pattern** for GPU provisioning (Race, RoundRobin, Coldstart, Serverless)
2. **Repository Pattern** for provider abstraction
3. **Dependency Injection** via FastAPI's `Depends()`
4. **Domain-Driven Design** with clear layer separation

### Directory Structure
```
src/
├── api/v1/          # REST endpoints
│   ├── endpoints/   # Route handlers
│   ├── schemas/     # Request/Response models
│   └── dependencies.py
├── domain/          # Business logic
│   ├── models/      # Domain entities
│   ├── repositories/# Provider interfaces
│   └── services/    # Core services
├── services/        # Application services
│   ├── gpu/         # GPU strategies
│   ├── standby/     # Failover logic
│   └── storage/     # Storage providers
├── infrastructure/  # External integrations
└── core/            # Config, JWT, exceptions

cli/                 # Python CLI
├── commands/        # CLI command groups
└── utils/           # API client

web/                 # React frontend
├── src/components/  # UI components
└── src/pages/       # Route pages
```

## Main API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | JWT authentication |
| `/api/v1/instances` | GET | List running instances |
| `/api/v1/instances/provision` | POST | Deploy new GPU |
| `/api/v1/instances/{id}/wake` | POST | Wake hibernated machine |
| `/api/v1/instances/{id}/destroy` | DELETE | Destroy instance |
| `/api/v1/standby` | GET/POST | Failover configuration |
| `/api/v1/standby/failover` | POST | Trigger manual failover |
| `/api/v1/models/deploy` | POST | Deploy LLM model |
| `/api/v1/spot/market` | GET | Spot market analysis |
| `/api/v1/machines/history` | GET | Machine reliability stats |

## Development Guidelines

### 1. Domain-First Development
Always define models in `src/domain/models/` and interfaces in `src/domain/repositories/` before implementing infrastructure.

### 2. Dependency Injection
Use FastAPI's `Depends()` decorator. Never instantiate infrastructure classes directly in endpoints.

---

## Code Standards

### Exception Handling
- Never use bare `except:` or `except: pass`
- Always specify exception types (e.g., `json.JSONDecodeError`, `IOError`, `KeyError`)
- Log errors before re-raising when appropriate

### Logging
- Use `logger` from `src.core.logging` instead of `print()`
- Never use `print("[DEBUG]...")` - use `logger.debug()`
- Log levels: `debug` → `info` → `warning` → `error`

### Credentials & Security
- Never hardcode credentials in source code
- Always use `os.environ.get("VAR", "")` for secrets
- Never commit API keys, passwords, or tokens to git

### Code Cleanliness
- Remove commented-out code blocks
- Remove unreachable code (code after `return`)
- Define variables before using them

### Imports
- Order: standard library → third-party → local
- Group imports by category with blank lines between

### Error Messages
- Always include context in error messages
- Avoid vague messages like "Error" or "Failed"

### API Responses
- Use consistent format: `{"success": bool, "data": ...}`
- Include meaningful error details in HTTPException

### Config Files
- Never store sensitive data in config.json
- Use empty templates, load values from environment

## Testing

### Running Tests
```bash
# All tests (parallel, 10 workers)
cd cli && pytest

# Specific test file
pytest tests/test_real_integration.py -v

# With timeout
pytest -v --timeout=600
```

### Test Configuration (pyproject.toml)
```toml
addopts = ["-n", "10", "-v", "--tb=short", "--dist=loadscope"]
```

### Important Notes
- Tests provision **real GPU instances** on Vast.ai (costs money)
- Each test is self-contained: provisions its own instance and destroys it
- Tests run in parallel across separate instances
- No shared state between tests

### Test Fixture Pattern
```python
@pytest.fixture
def gpu_instance(api_client):
    """Provisions instance for test and destroys after."""
    instance = api_client.provision_instance(gpu_type="RTX_4090")
    wait_for_ready(instance)
    yield instance
    api_client.destroy_instance(instance.id)

def test_gpu_operation(gpu_instance):
    result = gpu_instance.run_command("nvidia-smi")
    assert "CUDA" in result
```

## Key Features

### GPU Provisioning Strategies
| Strategy | Description |
|----------|-------------|
| Race | 5 machines in parallel, first ready wins |
| RoundRobin | Sequential attempts across providers |
| Coldstart | Single machine, wait for boot |
| Serverless | Pre-warmed pool + auto-hibernate |

### Machine History & Blacklist
- Tracks success/failure rate per machine
- Auto-blacklists machines with <30% success rate
- Deploy wizard filters unreliable hosts

### Auto-Hibernation
- GPU idle (<5%) for 3 min → snapshot + destroy
- Hibernated 30 min → cleanup reservation
- Only snapshot kept in R2 ($0.01/month)
