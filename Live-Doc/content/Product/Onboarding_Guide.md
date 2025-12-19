# 🚀 Onboarding Guide - Primeiros Passos

## Bem-vindo ao Dumont Cloud! 

Este guia vai te ajudar a **criar sua primeira GPU em menos de 5 minutos**.

---

## ✅ Passo 1: Criar Conta

1. Acesse: https://dumontcloud.com
2. Clique em **"Criar Conta"**
3. Preencha:
   - Email
   - Senha (mínimo 8 caracteres)
   - Aceite os Termos de Uso
4. Clique em **"Registrar"**

Você receberá um email de confirmação. Clique no link para ativar sua conta.

---

## 💳 Passo 2: Adicionar Créditos

1. Faça login: https://dumontcloud.com/login
2. Vá em **"Billing"** → **"Adicionar Créditos"**
3. Escolha o valor:
   - $10 (teste)
   - $50 (recomendado)
   - $100 (heavy use)
4. Pague via:
   - Cartão de crédito (Stripe)
   - PIX (Brasil)
   - Boleto (Brasil)

**Tempo de processamento**: Instantâneo (cartão), até 2h (PIX/Boleto)

---

## 🎮 Passo 3: Criar Primeira Instância GPU

### Método 1: Wizard Guiado (Recomendado)

1. No dashboard, clique em **"Nova Instância"**
2. **Escolha seu caso de uso**:
   - 🤖 Fine-tuning de LLM
   - 🎨 Renderização 3D
   - 🧪 Pesquisa/Treinamento
   - 🎮 Gaming na nuvem
3. O **AI GPU Advisor** vai recomendar a melhor GPU
4. Confirme a escolha
5. Clique em **"Criar"**

**Tempo de criação**: 2-3 minutos

### Método 2: Manual (Avançado)

```bash
# Via API
curl -X POST https://dumontcloud.com/api/instances \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "gpu_type": "RTX 4090",
    "region": "US-East",
    "auto_hibernate": true
  }'
```

---

## 🖥️ Passo 4: Acessar Sua GPU

### Opção A: VS Code no Navegador

1. Clique em **"Abrir VS Code"** no card da instância
2. Uma nova aba abre com VS Code Web
3. Código já está pronto para usar!

### Opção B: SSH

1. Copie o comando SSH do dashboard:
   ```bash
   ssh -i ~/.ssh/dumont.key ubuntu@X.X.X.X
   ```
2. Cole no terminal
3. Pronto! Você está na GPU

### Opção C: Jupyter Notebook

1. Clique em **"Jupyter"** no card da instância
2. Navegador abre com Jupyter
3. Crie um novo notebook Python 3

---

## 📊 Passo 5: Monitorar Custo

### Dashboard de Economia

No menu lateral, clique em **"Savings Dashboard"** para ver:

- 💵 Custo acumulado (hoje)
- 💰 Economia vs AWS (em tempo real)
- 📉 ROI %
- ⏱️ Tempo de uso

**Alerta**: Você recebe notificação quando atingir 80% do budget diário.

---

## 💤 Passo 6: Auto-Hibernação (Economize 70%!)

Por padrão, a auto-hibernação **já está ativada**. Isso significa:

- GPU ociosa >5min → Hiberna automaticamente
- Você para de pagar enquanto hibernada
- Ao voltar a usar → Acorda em 30s

**Como desativar** (não recomendado):
1. Vá em **Settings** → **Standby Config**
2. Desmarque "Enable Auto-Hibernate"

---

## 🔄 Passo 7: Criar Snapshot (Backup)

**Por que fazer snapshot?**
- Backup antes de atualizar sistema
- Duplicar ambiente para outro projeto
- Proteção contra perda de dados

**Como fazer**:
1. Clique em **"Snapshot"** no card da instância
2. Dê um nome: "Backup pré-upgrade"
3. Clique em **"Criar"**

**Tempo**: 100GB em ~2 minutos (compressão LZ4)

**Restaurar**:
1. Vá em **"Snapshots"**
2. Clique em **"Restore"** no snapshot desejado
3. Nova instância é criada com os dados

---

## 🆘 Primeiros Problemas (e Soluções)

### 1. "Instância não inicia"
**Causa**: Região sem GPUs disponíveis  
**Solução**: Tente outra região (EU-West, Asia-Pacific)

### 2. "SSH não conecta"
**Causa**: Instância ainda iniciando  
**Solução**: Aguarde 2-3min, tente novamente

### 3. "Custo maior que esperado"
**Causa**: Auto-hibernação desativada  
**Solução**: Settings → Ativar "Auto Hibernate"

### 4. "Snapshot muito lento"
**Causa**: Compressão gzip (padrão)  
**Solução**: Use LZ4 (4x mais rápido)

---

## 🎓 Próximos Passos

Agora que você já sabe o básico:

1. 📚 Leia o [Quick Start](../Engineering/Quick_Start.md) para configurar ambiente local
2. 🔌 Veja [API Reference](../Engineering/API_Reference.md) para automações
3. 💰 Confira [Pricing Strategy](../Strategy/Pricing_Strategy.md) para entender tiers
4. 🤖 Ative [AI GPU Advisor](AI_GPU_Advisor.md) para recomendações personalizadas

---

## 📞 Precisa de Ajuda?

- **FAQ**: [Perguntas Frequentes](FAQ.md)
- **Suporte**: suporte@dumontcloud.com
- **Chat**: Clique no ícone 💬 no canto inferior direito
- **Comunidade**: Discord (link no rodapé)

---

**Tempo médio de onboarding**: 5-10 minutos  
**Taxa de sucesso**: 95% criam primeira instância  
**Última atualização**: 2025-12-19
