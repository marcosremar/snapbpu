# ❓ FAQ - Perguntas Frequentes

## 🚀 Geral

### O que é Dumont Cloud?
Uma plataforma de **GPU Cloud** que combina o custo baixo do Spot Market com a resiliência da Google Cloud. Economize até **89% vs AWS** sem perder dados.

### Como vocês conseguem ser tão baratos?
Usamos **GPUs Spot** (Vast.ai) que são até 10x mais baratas que AWS. Quando uma GPU Spot cai, fazemos **failover automático** para uma CPU standby (GCP), preservando 100% dos dados.

### Qual é o catch?
Nenhum. A única diferença é que você pode ter **interrupções ocasionais** (failover de ~5s), mas sem data loss.

---

## 💰 Preços & Billing

### Quanto custa?
**RTX 4090**: $0.40/hora  
**A100**: $1.20/hora  
**RTX 3090**: $0.30/hora

Comparado com AWS EC2 (p3.2xlarge): **$3.06/hora**

### Tem trial gratuito?
✅ Sim! **7 dias grátis** no plano Pro ($79 de crédito). Não precisa cartão.

### Como adiciono créditos?
Dashboard → Billing → Adicionar Créditos  
Aceita: Cartão, PIX, Boleto

### Posso pagar mensalmente?
✅ Sim. Planos **Pro** ($79/mês) e **Enterprise** (custom). Veja [Pricing](../Strategy/Pricing_Strategy.md).

---

## 🎮 Instâncias & GPU

### Quanto tempo leva para criar uma GPU?
**2-3 minutos** em média. Máximo: 5 minutos.

### Posso escolher a região?
✅ Sim. Oferecemos: US-East, US-West, EU-West, Asia-Pacific.

### Qual GPU devo escolher?
Use o **AI GPU Advisor** (dashboard → Nova Instância → Wizard). Ele recomenda baseado no seu workload.

### Posso mudar de GPU depois?
✅ Sim. Crie um **snapshot**, delete a instância antiga, e crie uma nova com outra GPU. Seus dados são preservados.

---

## 💤 Auto-Hibernação

### O que é auto-hibernação?
Se sua GPU fica **ociosa >5min** (uso <5%), ela hiberna automaticamente. Você **para de pagar** enquanto hibernada.

### Quanto eu economizo?
**70-90%** do custo, dependendo do padrão de uso.

### Como desativar?
Settings → Standby Config → Desmarcar "Enable Auto-Hibernate" (não recomendado).

### Quanto tempo leva para acordar?
**~30 segundos**. Seus dados estão intactos.

---

## 🔄 Failover & Resiliência

### O que acontece se a GPU Spot cair?
**Failover automático** em <5s para CPU standby (GCP). Você pode continuar trabalhando, sem data loss.

### Vou perder meus dados?
❌ **Nunca**. Fazemos sync contínuo (lsyncd) entre GPU Spot e CPU standby.

### Quanto tempo fico na CPU?
O sistema **automaticamente provisiona** uma nova GPU. Tempo médio: 3-5 minutos.

### E se a CPU standby também cair?
Temos **multi-região backup** (Q2 2025). Se GCP US-East cair, failover para EU-West.

---

## 📸 Snapshots

### O que é um snapshot?
Um **backup completo** da sua instância (código + dados + ambiente).

### Quanto tempo leva?
**100GB em ~2 minutos** (compressão LZ4 + s5cmd).

### Quanto custa?
**$0.005/GB/mês**. Exemplo: 100GB = $0.50/mês.

### Posso restaurar em outra região?
✅ Sim. Snapshots são globais (Backblaze B2).

---

## 🔐 Segurança

### Meus dados estão seguros?
✅ Sim. 
- **Em trânsito**: TLS 1.3
- **Em repouso**: Snapshots criptografados (Restic AES-256)
- **Senhas**: Bcrypt (cost 12)

### Vocês têm 2FA?
🚧 **Planejado para Q2 2025**.

### Posso usar minha própria chave SSH?
✅ Sim. Dashboard → Settings → SSH Keys → Adicionar.

---

## 🛠️ Desenvolvimento

### Tem CLI?
✅ Sim. Instale: `pip install dumont-cli`

```bash
dumont create --gpu RTX4090 --region US-East
dumont list
dumont hibernate INSTANCE_ID
```

### Tem SDK Python?
✅ Sim.

```python
from dumont import Client

client = Client(api_key="your_api_key")
instance = client.instances.create(gpu="RTX 4090")
print(instance.status)
```

### Consigo integrar com CI/CD?
✅ Sim. Temos **webhooks** para eventos:
- Instance created
- Instance deleted
- Failover triggered
- Snapshot completed

Veja [Integration Guide](../Engineering/Integration_Guide.md).

---

## 🤖 AI & Machine Learning

### Consigo treinar modelos LLM?
✅ Sim. Recomendamos **A100** (80GB VRAM) para modelos >7B parâmetros.

### Tem Jupyter pré-instalado?
✅ Sim. Clique em "Jupyter" no card da instância.

### Posso usar TensorFlow/PyTorch?
✅ Sim. Ambos pré-instalados. Drivers CUDA 12.2.

### Consigo rodar Stable Diffusion?
✅ Sim. RTX 4090 é ideal (512x512 em ~2s).

---

## 🌐 Rede & Acesso

### Consigo acessar via SSH?
✅ Sim. Comando SSH disponível no dashboard.

### Tem IP fixo?
⚠️ **Não** no Spot (IP muda a cada restart). Use **Dynamic DNS** (fornecido).

### Consigo expor porta 8080?
✅ Sim. Use **subdomínio**: `INSTANCE_ID-8080.dumontcloud.com`

### Tem VPN?
🚧 **Planejado para Q3 2025**.

---

## 📊 Suporte & SLA

### Qual é o SLA?
**99.9% uptime** (planos Pro+). Downtime máximo: 43min/mês.

### Tem suporte 24/7?
✅ **Enterprise only**. Pro tem suporte em horário comercial (9h-18h BRT).

### Como abro um ticket?
Email: suporte@dumontcloud.com  
Chat: Ícone 💬 no dashboard  
Discord: [link]

### Tempo de resposta?
- **Starter**: <24h
- **Pro**: <4h
- **Enterprise**: <1h (24/7)

---

## 📈 Comparação com Concorrentes

### Dumont vs AWS
| Feature | AWS | Dumont |
|---------|-----|--------|
| **Custo/hora (RTX 4090)** | $3.06 | **$0.40** ✅ |
| **Failover automático** | ❌ | **✅** |
| **Auto-hibernação** | ❌ | **✅** |
| **Setup** | Complexo | **5 min** ✅ |

### Dumont vs Vast.ai
| Feature | Vast.ai | Dumont |
|---------|---------|--------|
| **Custo/hora** | $0.40 | $0.40 (igual) |
| **Resiliência** | ❌ Baixa | **✅ Alta** |
| **Data Loss** | ⚠️ Comum | **❌ Zero** |
| **Interface** | Básica | **✨ Moderna** ✅ |

---

## 🆘 Problemas Comuns

### "Não consigo criar instância"
**Soluções**:
1. Verifique créditos (Billing)
2. Tente outra região
3. Tente outra GPU

### "SSH não conecta"
**Soluções**:
1. Aguarde 3min (instância iniciando)
2. Verifique se IP mudou (Dynamic DNS)
3. Use VS Code Web (sempre funciona)

### "Custo muito alto"
**Soluções**:
1. Ative auto-hibernação
2. Delete instâncias não usadas
3. Configure budget alerts

---

## 📞 Ainda Tem Dúvidas?

- **Email**: suporte@dumontcloud.com
- **Chat**: Clique no ícone 💬
- **Discord**: [Comunidade](https://discord.gg/dumontcloud)
- **Twitter**: [@dumontcloud](https://twitter.com/dumontcloud)

**Tempo médio de resposta**: 2-4h (horário comercial)

---

**Última atualização**: 2025-12-19  
**Contribua**: Tem uma pergunta? [Adicione aqui](https://github.com/dumont-cloud/docs/blob/main/FAQ.md)
