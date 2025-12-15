# SnapGPU - Sistema de Snapshot para GPU Cloud

## Objetivo Principal

Sistema de backup/restore ultra-rápido para ambientes de GPU cloud (vast.ai, runpod, etc).
**O tempo de inicialização é crítico** - o sistema deve restaurar o ambiente de trabalho o mais rápido possível.

## Princípios de Design

### 1. Velocidade é Prioridade #1
- Cada segundo conta na inicialização
- Preferir soluções que minimizem latência
- Paralelizar operações sempre que possível

### 2. Estratégia de Multi-Start para Máquinas
- Máquinas GPU cloud têm tempos de inicialização imprevisíveis (10s a 3+ min)
- **Solução**: Iniciar múltiplas máquinas em paralelo, usar a primeira que ficar pronta
- Algoritmo:
  1. Iniciar 5 máquinas simultaneamente
  2. Aguardar 10 segundos
  3. Se nenhuma estiver pronta, iniciar mais 5 diferentes
  4. Repetir até 3 vezes (máximo 15 máquinas)
  5. Usar a primeira que responder, cancelar as outras

### 3. Restore Otimizado
- Usar restic com máximo de conexões paralelas (32+)
- Considerar cache local para arquivos frequentes
- Priorizar restauração de arquivos críticos primeiro

## Arquitetura

```
VPS (54.37.225.188)           GPU Cloud (vast.ai)
┌─────────────────┐           ┌─────────────────┐
│ Dashboard       │           │ Workspace       │
│ - Flask API     │◄─────────►│ - MuseTalk1.5   │
│ - Restic client │           │ - Sync daemon   │
└────────┬────────┘           └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Cloudflare R2   │
│ - Restic repo   │
│ - ~7GB comprim. │
└─────────────────┘
```

## APIs Principais

- `/api/snapshots` - Lista snapshots com deduplicação por tree hash
- `/api/offers` - Lista máquinas disponíveis com filtros completos
- `/api/create-instance` - Cria instância vast.ai
- `/api/restore` - Restaura snapshot na máquina

## Credenciais (Desenvolvimento)

- VPS: ubuntu@54.37.225.188
- Dashboard: http://vps-a84d392b.vps.ovh.net:8765/
- R2 Bucket: musetalk
- Restic repo: s3:https://....r2.cloudflarestorage.com/musetalk/restic

## TODO

- [ ] Implementar multi-start de máquinas (5 paralelas, 10s timeout)
- [ ] Cancelamento automático de máquinas não utilizadas
- [ ] Métricas de tempo de inicialização por host
- [ ] Cache de hosts "rápidos" para priorização futura
