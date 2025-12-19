# 💳 Billing & Credits - Como Funciona

## Sistema de Cobrança

O Dumont Cloud opera em **modelo pré-pago** (créditos).

---

## 💰 Adicionar Créditos

### Valores Disponíveis

| Pacote | Valor | Bônus |
|--------|-------|-------|
| Starter | $10 | - |
| Popular | $50 | +$5 (10%) |
| Power | $100 | +$15 (15%) |
| Enterprise | $500+ | +$100 (20%) |

### Métodos de Pagamento

#### 1. Cartão de Crédito (Stripe)
- **Processamento**: Instantâneo
- **Aceita**: Visa, Mastercard, Amex
- **Cobrança adicional**: 3.5% (taxa Stripe)

#### 2. PIX (Brasil)
- **Processamento**: Até 2 horas
- **Sem taxa adicional**
- **QR Code**: Válido por 1 hora

#### 3. Boleto (Brasil)
- **Processamento**: 1-2 dias úteis
- **Sem taxa adicional**
- **Vencimento**: 3 dias corridos

### Como Adicionar

```bash
# Web
1. Login → Billing → Adicionar Créditos
2. Escolha valor
3. Selecione método de pagamento
4. Confirme

# API
curl -X POST https://dumontcloud.com/api/billing/credits \
  -H "Authorization: Bearer TOKEN" \
  -d '{"amount_usd": 50, "method": "card"}'
```

---

## 📊 Ciclo de Faturamento

### Como é Cobrado

- **Cobrança por hora** (não por segundo)
- **Arredondamento**: Hora completa (ex: 1h 10min = 2h)
- **Auto-hibernação**: Para cobrança quando GPU ociosa

### Exemplo de Fatura

```
Período: 01/12/2025 - 31/12/2025

Instância: ml-training-rig (RTX 4090)
├─ Horas ativas:  120h × $0.40/h = $48.00
├─ Horas standby:  50h × $0.05/h = $2.50
└─ Snapshots:      3 × $0.10    = $0.30
                              ─────────
Total:                         $50.80

Créditos anteriores:           $100.00
Consumo do mês:                -$50.80
                              ─────────
Saldo restante:                $49.20
```

---

## 🔔 Alertas de Budget

### Notificações Automáticas

Você recebe email/Slack quando:

| Gatilho | Exemplo |
|---------|---------|
| **80% do budget diário** | Gastou $40 de $50/dia |
| **Créditos < $10** | Saldo: $8.50 |
| **Cobrança incomum** | Spike de $100 em 1h |

### Configurar Limites

```bash
# Dashboard
Settings → Billing → Daily Budget

# API
curl -X PATCH https://dumontcloud.com/api/settings \
  -d '{"daily_budget_usd": 50}'
```

---

## 🛑 O Que Acontece Quando Créditos Acabam?

### Ações Automáticas

1. **Saldo = $5**: Email de aviso
2. **Saldo = $1**: Instâncias são **hibernadas** automaticamente
3. **Saldo = $0**: 
   - Não pode criar novas instâncias
   - Instâncias hibernadas **preservadas por 7 dias**
   - Após 7 dias: Snapshots criados automaticamente, instâncias deletadas

### Recuperação

```bash
# Adicionar créditos
1. Dashboard → Billing → Adicionar

# Reativar instâncias
2. Dashboard → Machines → "Wake Up"
```

---

## 💸 Reembolsos

### Política de Reembolso

- ✅ **Aceito**: Dentro de 7 dias da compra
- ✅ **Condição**: <10% dos créditos usados
- ❌ **Não aceito**: Após 7 dias ou >10% usado

### Solicitar Reembolso

```bash
# Email
Para: billing@dumontcloud.com
Assunto: Reembolso - [SEU_EMAIL]
Corpo: Motivo do reembolso + Comprovante

# Prazo
48h úteis para análise
```

---

## 📄 Nota Fiscal (Brasil)

### Emissão

- Gerada **automaticamente** após pagamento
- Enviada por email (PDF)
- Disponível em: Dashboard → Billing → Invoices

### Informações

- CNPJ: 12.345.678/0001-90
- Razão Social: Dumont Cloud Ltda
- Serviço: "Hospedagem de Aplicações na Nuvem"

---

## 🔄 Assinaturas (Annual Plans)

### Benefícios

- **16% de desconto** (2 meses grátis)
- **Budget garantido** (não precisa recarregar)
- **Suporte prioritário**

### Planos Anuais

| Tier | Mensal | Anual | Economia |
|------|--------|-------|----------|
| Pro | $79/mês | $799/ano | **$149** |
| Enterprise | $299/mês | $2,999/ano | **$589** |

### Ativar

```bash
Dashboard → Billing → Switch to Annual
```

---

## 📈 Histórico de Transações

### Exportar Relatório

```bash
# Dashboard
Billing → Transactions → Export CSV

# API
curl https://dumontcloud.com/api/billing/transactions?from=2025-01-01&to=2025-12-31 \
  -H "Authorization: Bearer TOKEN"
```

### Filtros Disponíveis

- **Período**: Data inicial e final
- **Tipo**: Créditos, Consumo, Reembolso
- **Status**: Pendente, Aprovado, Recusado

---

## ❓ FAQ de Billing

### 1. Posso pagar com criptomoeda?
🚧 **Em desenvolvimento** para Q2 2025 (Bitcoin, USDT)

### 2. Tenho desconto para eduação?
✅ Sim! 50% off para estudantes (.edu email)

### 3. Posso transferir créditos entre contas?
❌ Não permitido (política anti-fraude)

### 4. Como funciona o trial gratuito?
✅ 7 dias grátis no plano Pro ($79 de crédito)

---

**Última atualização**: 2025-12-19  
**Dúvidas**: billing@dumontcloud.com
