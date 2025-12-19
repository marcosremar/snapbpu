# Perguntas Frequentes (FAQ)

## Geral

### O que e Dumont Cloud?
Uma plataforma de **GPU Cloud** que combina GPUs Spot de baixo custo com failover automatico para CPU, garantindo que voce nunca perca dados mesmo quando a GPU cai.

### Como voces conseguem ser tao baratos?
Usamos **GPUs Spot** de provedores como Vast.ai, que sao ate 10x mais baratas que AWS. A diferenca e que GPUs Spot podem ser interrompidas, mas nos resolvemos isso com failover automatico.

### E seguro?
Sim! Todos os dados sao criptografados e sincronizados em tempo real. Mesmo que a GPU seja interrompida, seus dados estao seguros no backup.

---

## Precos e Billing

### Quanto custa?
| GPU | Preco/hora |
|-----|------------|
| RTX 4090 | $0.40 |
| RTX 3090 | $0.30 |
| A100 40GB | $1.20 |
| H100 | $2.50 |

### Tem trial gratuito?
**Sim!** 7 dias gratis com $79 em creditos. Nao precisa cartao de credito.

### Quais formas de pagamento?
- Cartao de Credito (Visa, Mastercard, Amex)
- PIX (instantaneo)
- Boleto Bancario
- Cripto (BTC, ETH, USDT)

### Como funciona a cobranca?
- Cobranca **por minuto** de uso
- Minimo de 1 minuto
- Maquinas pausadas **nao cobram**

---

## Tecnico

### Quais GPUs estao disponiveis?
- NVIDIA RTX 3090, 4090
- NVIDIA A100 (40GB e 80GB)
- NVIDIA H100
- AMD MI250X (em breve)

### Quais imagens Docker vem pre-instaladas?
- PyTorch 2.x + CUDA 12
- TensorFlow 2.x + CUDA 12
- JAX + TPU
- Hugging Face Transformers
- ComfyUI (Stable Diffusion)

### Posso usar minha propria imagem Docker?
Sim! Basta especificar a URL da imagem ao criar a maquina.

### Como faco backup dos meus dados?
Os dados sao sincronizados automaticamente a cada 30 segundos para o Cloudflare R2. Voce tambem pode fazer backup manual via dashboard.

---

## Problemas Comuns

### Minha maquina nao conecta
1. Verifique se a maquina esta "Running"
2. Aguarde 30-60 segundos apos iniciar
3. Tente reconectar via SSH ou dashboard

### GPU esta lenta
1. Verifique utilizacao com `nvidia-smi`
2. Reinicie a maquina se necessario
3. Considere uma GPU mais potente

### Perdi meus dados!
Entre em contato imediatamente: suporte@dumontcloud.com
Temos backups de ate 7 dias.

---

## Suporte

### Como entro em contato?
- **Email**: suporte@dumontcloud.com
- **Discord**: discord.gg/dumontcloud
- **Chat**: Widget no canto inferior direito

### Qual o tempo de resposta?
- Plano Free: 24h
- Plano Pro: 4h
- Plano Enterprise: 1h (24/7)
