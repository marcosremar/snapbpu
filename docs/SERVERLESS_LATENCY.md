# Serverless GPU - Latência de Cold Start

Testes realizados em dezembro de 2024 com VAST.ai.

## Resultados

### Cold Start por GPU

| GPU | Cold Start (média) | Min | Max |
|-----|-------------------|-----|-----|
| RTX A2000 | ~5s | 4.9s | 5.3s |
| RTX 5070 | ~5-7s | 4.8s | 7.3s |
| RTX 4090 | ~14s | 13.8s | 15.6s |

### Operações

| Operação | Tempo |
|----------|-------|
| API Pause | ~0.7s |
| API Resume | ~0.7s |
| SSH indisponível (após pause) | ~1s |
| SSH disponível (após resume) | varia por GPU |

## Como funciona

1. **PAUSE**: Container é parado completamente
   - SSH fica `Connection refused`
   - Processos NÃO sobrevivem
   - Storage é preservado

2. **RESUME**: Container reinicia
   - Todos os processos precisam ser reiniciados
   - Use rc.local ou supervisor para auto-start

## Comparação com concorrentes

| Provedor | Cold Start | Custo Idle |
|----------|------------|------------|
| **VAST.ai (Dumont)** | **5-15s** | ~$0.005/hr |
| RunPod Serverless | 15-30s | $0.00/hr |
| Modal | 5-10s | $0.00/hr |
| AWS SageMaker | 60-180s | $0.00/hr |

## Nota importante

Para uma API real funcionar após cold start, você precisa configurar
auto-start dos seus serviços (supervisor, rc.local, docker entrypoint).

O tempo de cold start medido é: **tempo até SSH + nvidia-smi responderem**.
