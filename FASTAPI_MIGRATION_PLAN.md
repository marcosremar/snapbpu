# FastAPI Migration Plan - SOLID Principles

## Current State
- **Framework**: Flask with Blueprints
- **Structure**:
  - `app.py` (main entry point with mixed concerns)
  - `src/api/*.py` (API blueprints - business logic mixed with routing)
  - `src/services/*.py` (Service layer - some SOLID violations)
  - `src/config/settings.py` (Configuration)

## Architecture Goals (SOLID Principles)

### 1. **Single Responsibility Principle (SRP)**
- Separate concerns into dedicated modules
- Each class/module has ONE reason to change

### 2. **Open/Closed Principle (OCP)**
- Open for extension, closed for modification
- Use dependency injection
- Use abstract base classes for extensibility

### 3. **Liskov Substitution Principle (LSP)**
- Interchangeable implementations
- Common interfaces for different services

### 4. **Interface Segregation Principle (ISP)**
- Clients should not depend on unnecessary interfaces
- Smaller, focused interfaces

### 5. **Dependency Inversion Principle (DIP)**
- Depend on abstractions, not concretions
- Use dependency injection

## New Directory Structure

```
src/
├── core/
│   ├── __init__.py
│   ├── config.py                 # Configuration loader (from settings.py)
│   ├── exceptions.py             # Custom exceptions
│   ├── constants.py              # Application constants
│   └── dependencies.py           # Dependency injection container
├── domain/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── gpu_offer.py          # GpuOffer model (currently in vast_service.py)
│   │   ├── instance.py           # Instance model
│   │   └── user.py               # User model
│   ├── repositories/             # Abstract interfaces
│   │   ├── __init__.py
│   │   ├── gpu_provider.py       # IGpuProvider (abstract)
│   │   ├── snapshot_provider.py  # ISnapshotProvider (abstract)
│   │   └── user_provider.py      # IUserProvider (abstract)
│   └── services/                 # Domain services (no HTTP concerns)
│       ├── __init__.py
│       ├── instance_service.py   # Instance orchestration
│       ├── snapshot_service.py   # Snapshot orchestration
│       └── gpu_service.py        # GPU service
├── infrastructure/
│   ├── __init__.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── vast_provider.py      # VastService -> VastProvider (IGpuProvider)
│   │   ├── restic_provider.py    # ResticService -> ResticProvider (ISnapshotProvider)
│   │   ├── codeserver_provider.py
│   │   └── user_storage.py       # File-based user storage
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py         # Abstract agent
│   │   ├── price_monitor_agent.py
│   │   └── hibernation_agent.py
│   └── external/
│       ├── __init__.py
│       ├── ssh_client.py         # SSH communication
│       └── http_client.py        # HTTP requests wrapper
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── router.py             # Main router
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # Auth routes
│   │   │   ├── instances.py      # Instance routes
│   │   │   ├── snapshots.py      # Snapshot routes
│   │   │   ├── offers.py         # GPU offers routes
│   │   │   ├── hibernation.py    # Hibernation routes
│   │   │   └── settings.py       # Settings routes
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── request.py        # Request models (Pydantic)
│   │   │   ├── response.py       # Response models (Pydantic)
│   │   │   └── errors.py         # Error schemas
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py           # Authentication middleware
│   │       ├── logging.py        # Request logging
│   │       └── error_handler.py  # Global error handling
│   └── static/
│       └── (static files)
├── main.py                       # FastAPI app factory & startup

```

## Migration Strategy (Phased Approach)

### Phase 1: Setup & Core Infrastructure (2-3 steps)
- [ ] Setup FastAPI project structure
- [ ] Create core config and DI container
- [ ] Define domain models and abstract interfaces
- [ ] Setup Pydantic schemas for API

### Phase 2: Infrastructure Providers (2-3 steps)
- [ ] Migrate VastService → VastProvider (IGpuProvider impl)
- [ ] Migrate ResticService → ResticProvider (ISnapshotProvider impl)
- [ ] Setup SSH client wrapper
- [ ] Create user storage provider

### Phase 3: Domain Services (1-2 steps)
- [ ] Create instance management service (orchestrates VastProvider)
- [ ] Create snapshot service (orchestrates ResticProvider)
- [ ] Setup exception handling

### Phase 4: API Layer (3-4 steps)
- [ ] Create API endpoints for instances (/api/v1/instances)
- [ ] Create API endpoints for snapshots (/api/v1/snapshots)
- [ ] Create API endpoints for offers (/api/v1/offers)
- [ ] Create API endpoints for auth (/api/v1/auth)
- [ ] Create API endpoints for settings (/api/v1/settings)

### Phase 5: Middleware & Features (1-2 steps)
- [ ] Authentication middleware
- [ ] Global error handling
- [ ] Request/response logging
- [ ] CORS configuration

### Phase 6: Agents & Background Tasks (1-2 steps)
- [ ] Migrate PriceMonitorAgent
- [ ] Migrate AutoHibernationManager
- [ ] Setup lifespan events

### Phase 7: Testing & Deployment (1-2 steps)
- [ ] Update requirements.txt
- [ ] Test API compatibility
- [ ] Update deployment scripts

## SOLID Principles Implementation Details

### Dependency Inversion Example:
```python
# Before (Flask): Direct dependency on concrete class
class InstanceAPI:
    def __init__(self):
        self.vast_service = VastService(api_key)

# After (FastAPI): Dependency on abstraction
from abc import ABC, abstractmethod

class IGpuProvider(ABC):
    @abstractmethod
    def search_offers(self, ...): pass

class InstanceService:
    def __init__(self, gpu_provider: IGpuProvider):
        self.gpu_provider = gpu_provider  # Depends on abstraction
```

### Service Locator (Dependency Container):
```python
# src/core/dependencies.py
class DIContainer:
    _instance = None
    _services = {}

    @classmethod
    def register(cls, name: str, factory: callable):
        cls._services[name] = factory

    @classmethod
    def resolve(cls, name: str):
        if name not in cls._services:
            raise Exception(f"Service {name} not registered")
        return cls._services[name]()
```

### Exception Hierarchy:
```python
# src/core/exceptions.py
class DumontCloudException(Exception): pass
class VastAPIException(DumontCloudException): pass
class SnapshotException(DumontCloudException): pass
class AuthenticationException(DumontCloudException): pass
```

## Files to Keep (No Changes Needed)
- `web/` (Frontend - independent)
- `tests/` (Existing tests - will adapt)
- `.env` config

## Estimated Impact
- **API Compatibility**: 100% (same endpoints, same responses)
- **Performance**: Slight improvement (FastAPI async support)
- **Maintainability**: Significantly improved (SOLID compliance)
- **Testability**: Much easier (dependency injection)
- **Migration Time**: 6-8 focused work sessions

## Benefits After Migration
1. **Type Safety**: Full async support, better type hints
2. **Performance**: Async middleware, better concurrency
3. **Maintainability**: Clear separation of concerns
4. **Testability**: Mockable dependencies, easier unit tests
5. **Extensibility**: Easy to add new providers, services, endpoints
6. **Documentation**: Auto-generated OpenAPI docs

