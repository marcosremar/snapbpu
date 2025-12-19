# Precos e Planos

## Tabela de Precos GPU

| GPU | VRAM | Preco/hora | vs AWS |
|-----|------|------------|--------|
| RTX 3090 | 24GB | $0.30 | -90% |
| RTX 4090 | 24GB | $0.40 | -87% |
| A100 40GB | 40GB | $1.20 | -85% |
| A100 80GB | 80GB | $1.80 | -83% |
| H100 | 80GB | $2.50 | -80% |

---

## Planos

### Free
**$0/mes**
- Ate $10 em creditos
- 1 maquina simultanea
- Suporte por email (24h)
- Backup basico (7 dias)

### Pro
**$29/mes**
- $79 em creditos inclusos
- 5 maquinas simultaneas
- Suporte prioritario (4h)
- Backup estendido (30 dias)
- CPU Standby incluido
- API access

### Enterprise
**Customizado**
- Creditos ilimitados
- Maquinas ilimitadas
- Suporte 24/7 (1h SLA)
- Backup ilimitado (90 dias)
- Account Manager dedicado
- SLA garantido (99.9%)
- Faturamento mensal

---

## Comparativo com Concorrentes

### vs AWS EC2 p3.2xlarge (V100)
| | AWS | Dumont | Economia |
|-|-----|--------|----------|
| Preco/hora | $3.06 | $0.40 | 87% |
| 100 horas/mes | $306 | $40 | $266 |
| 500 horas/mes | $1,530 | $200 | $1,330 |

### vs Google Cloud A100
| | GCP | Dumont | Economia |
|-|-----|--------|----------|
| Preco/hora | $4.00 | $1.20 | 70% |
| 100 horas/mes | $400 | $120 | $280 |
| 500 horas/mes | $2,000 | $600 | $1,400 |

### vs Lambda Labs
| | Lambda | Dumont | Economia |
|-|--------|--------|----------|
| RTX 4090/hora | $0.75 | $0.40 | 47% |
| A100/hora | $1.99 | $1.20 | 40% |

---

## Custos Adicionais

### Storage (Backup)
| Uso | Preco |
|-----|-------|
| 0-50GB | Gratis |
| 50-500GB | $0.01/GB/mes |
| 500GB-5TB | $0.008/GB/mes |
| Acima 5TB | $0.005/GB/mes |

### CPU Standby
| Tipo | Preco/hora |
|------|------------|
| e2-medium | $0.03 |
| e2-standard-4 | $0.15 |
| n2-standard-8 | $0.40 |

### Trafego de Rede
- **Inbound**: Gratis
- **Outbound**: Gratis ate 1TB/mes
- **Acima**: $0.05/GB

---

## Calculadora de Custos

### Exemplo 1: Pesquisador ML
```
Uso: RTX 4090, 8h/dia, 20 dias/mes

GPU: 160h × $0.40 = $64
Storage: 100GB = $0.50
CPU Standby: ~10h × $0.15 = $1.50
----------------------------------------
Total: ~$66/mes

vs AWS: $490/mes (economia de $424)
```

### Exemplo 2: Startup AI
```
Uso: 3x A100, 24/7

GPU: 3 × 720h × $1.20 = $2,592
Storage: 500GB = $4.50
CPU Standby: ~50h × $0.40 = $20
----------------------------------------
Total: ~$2,617/mes

vs GCP: $8,640/mes (economia de $6,023)
```

### Exemplo 3: Hobby
```
Uso: RTX 3090, 4h/semana

GPU: 16h × $0.30 = $4.80
Storage: 20GB = Gratis
----------------------------------------
Total: ~$5/mes
```

---

## Formas de Pagamento

### Aceitos
- Cartao de Credito (Visa, Mastercard, Amex)
- PIX (instantaneo)
- Boleto Bancario
- Cripto (BTC, ETH, USDT)
- Wire Transfer (Enterprise)

### Bonus por Volume
| Valor | Bonus |
|-------|-------|
| $50+ | +10% |
| $100+ | +15% |
| $500+ | +20% |

---

## Faturamento Corporativo

Para empresas com faturamento mensal:

1. Entre em contato: enterprise@dumontcloud.com
2. Envie documentacao (CNPJ, contrato social)
3. Definimos limite de credito
4. Fatura mensal com vencimento em 30 dias
5. Nota fiscal emitida automaticamente

### Beneficios
- Sem necessidade de pre-pago
- Fatura consolidada
- Suporte prioritario
- Precos negociaveis por volume
