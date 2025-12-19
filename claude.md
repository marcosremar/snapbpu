# Dumont Cloud - Sistema de Gerenciamento de GPU Cloud (v3)

## Objetivo Principal

Sistema de gerenciamento e backup/restore ultra-rápido para ambientes de GPU cloud (vast.ai, runpod, etc).
**O tempo de inicialização e a economia de custos são críticos** - o sistema deve restaurar o ambiente o mais rápido possível e hibernar máquinas ociosas automaticamente.

## Princípios de Design

### 1. Velocidade é Prioridade #1
- Cada segundo conta na inicialização.
- Uso de compactação ANS e restic otimizado (32+ conexões).
- Restore em menos de 15 segundos para 7GB.

### 2. Auto-Hibernação Inteligente (Custo Zero)
- **REGRA CRÍTICA**: Monitoramento constante via `DumontAgent`.
- Se GPU ociosa (< 5%) por **3 minutos**: Instantânea criação de snapshot e destruição da máquina.
- Se hibernada por **30 minutos**: Limpeza da reserva, mantendo apenas o snapshot no R2 ($0.01/mês).

### 3. Estratégia de Multi-Start Dinâmico (Batches)
- **Implementado**: Supera a variabilidade de boot das clouds iniciando máquinas em paralelo.
- **Batches**: Inicia batches de 5 máquinas (até 3 rounds/15 máquinas total).
- **Vencedor**: Monitora todas via API; a primeira que reportar status "Running" e liberar dados de SSH vence.
- **Cleanup Imediato**: Todas as outras máquinas são destruídas no instante em que o vencedor é confirmado.
- **Timeouts**: Timeout agressivo de 90s por batch para garantir rapidez.

### 4. Arquitetura SOLID & FastAPI
- Backend moderno com **FastAPI**, **Pydantic v2** e **Dependency Injection**.
- Autenticação via **JWT** (stateless).
- Camadas bem definidas: Domain, Infrastructure, API, Core.

## Arquitetura

```
VPS (Control Plane)             GPU Cloud (Data Plane)
┌─────────────────┐           ┌──────────────────┐
│ FastAPI Backend │           │ DumontAgent      │
│ - Domain Logic  │◄─────────►│ - GPU Monitor    │
│ - Auto-Hiber.   │   (SSH)   │ - Sync Service   │
└────────┬────────┘           └──────────────────┘
         │
         ▼
┌─────────────────┐
│ Cloudflare R2   │
│ - Snapshots ANS │
│ - Restic Repos  │
└─────────────────┘
```

## APIs Principais (v1)

- `/api/v1/auth/login` - Autenticação JWT
- `/api/v1/instances` - Gerenciamento de instâncias (list, create, destroy, pause, resume)
- `/api/v1/instances/{id}/wake` - Reativação ultra-rápida de máquina hibernada
- `/api/v1/snapshots` - Lista e gerencia backups
- `/api/v1/metrics` - Métricas de performance e uso
- `/api/v1/metrics/savings/real` - Economia real acumulada via hibernação
- `/api/v1/agent/status` - Recebe heartbeats do DumontAgent
- `/api/v1/standby` - Configura CPU Standby/Failover (GCP)

## Credenciais e Acesso (Dev)

- VPS: ubuntu@54.37.225.188
- Dashboard: http://vps-a84d392b.vps.ovh.net:8765/
- Restic repo: s3:https://....r2.cloudflarestorage.com/musetalk/restic

## Boas Práticas de Desenvolvimento

### 1. Camada de Domínio Primeiro
Sempre defina os modelos em `src/domain/models/` e interfaces em `src/domain/repositories/` antes de implementar infraestrutura.

### 2. Dependency Injection
Use o decorator `Depends()` do FastAPI para injetar serviços e repositórios. Nunca instancie classes de infraestrutura diretamente nos endpoints.

### 3. SSH Otimizado
Evite comandos inline complexos. Use `src/infrastructure/providers/vast_provider.py` para abstrair operações SSH.

## Status Atual (Atualizado 2024-12-17)

- [x] Migração Flask → FastAPI (100%)
- [x] Autenticação JWT (100%)
- [x] Sistema de Auto-Hibernação (100%) - Inclui endpoint `/wake` e agents inicializados
- [x] Refatoração SOLID (100%)
- [x] Multi-Start Dinâmico (Batches 5x3) (100%)
- [x] Dashboard de Economia Real (100%) - Endpoints e componentes React prontos
- [x] Endpoint de Heartbeats `/api/agent/status` (100%)
- [x] CPU Standby/Failover Backend (100%)
- [/] CPU Standby UI (70%) - Componente Config pronto, falta badge detalhado
- [ ] Testes E2E (0%)
