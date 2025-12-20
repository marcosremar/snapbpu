# GPU Cloud Providers - Comparativo

Análise de provedores de GPU cloud para o DumontCloud, focando em suporte a containers privilegiados para cuda-checkpoint.

## Resumo Executivo

| Provider | Preço H100/hr | Checkpoint? | Recomendação |
|----------|---------------|-------------|--------------|
| TensorDock | $2.25 | ✅ Sim | **Melhor custo-benefício** |
| HOSTKEY | ~$3.00 | ✅ Sim | Boa opção enterprise |
| CoreWeave | $4.76 | ⚠️ Negociável | Para grandes volumes |
| Lambda Labs | $2.99 | ❌ Não | Bom para dev sem checkpoint |
| RunPod | $4.69 | ❌ Não | Fácil de usar |
| Vast.ai | $2.50 | ❌ Não | Mais barato, menos features |
| AWS/GCP | $30+ | ⚠️ Caro | Enterprise com compliance |

## Detalhamento

### TensorDock (Recomendado)

**Website**: https://tensordock.com

**Tipo**: Marketplace + Bare Metal

**Preços**:
| GPU | VRAM | Preço/hr |
|-----|------|----------|
| RTX 3080 | 10GB | $0.12 |
| RTX 3090 | 24GB | $0.20 |
| RTX 4090 | 24GB | $0.35 |
| A100 | 40/80GB | $1.80 |
| H100 | 80GB | $2.25 |
| V100 | 16GB | $0.45 |

**Suporte a Checkpoint**: ✅ Sim (Bare Metal)
- Acesso root completo
- CAP_SYS_PTRACE disponível
- Driver 570+ instalável
- **Testado e validado** em 20/12/2024

**Prós**:
- Preço muito competitivo
- Bare metal com acesso total
- Pagamento por hora
- Sem commitment

**Contras**:
- Interface básica
- Inventário limitado
- Suporte menos responsivo
- Menor comunidade

**Cobrança ao pausar**: ~10-20% do preço (disco mantido)

---

### RunPod

**Website**: https://runpod.io

**Tipo**: Managed Cloud + Serverless

**Preços**:
| GPU | VRAM | Preço/hr |
|-----|------|----------|
| RTX 4090 | 24GB | $0.44 |
| A100 | 80GB | $1.99 |
| H100 | 80GB | $4.69 |

**Suporte a Checkpoint**: ❌ Não
- Confirmado via Discord (Out/2024)
- Staff: "This is not possible as it requires privileged docker container"
- CAP_SYS_ADMIN não disponível
- Seccomp ativo

**Prós**:
- Interface polida
- Bom suporte
- Serverless disponível
- Grande comunidade

**Contras**:
- Sem containers privilegiados
- Preço mais alto que TensorDock

---

### Vast.ai

**Website**: https://vast.ai

**Tipo**: Marketplace P2P

**Preços** (variam por host):
| GPU | VRAM | Preço/hr (aprox) |
|-----|------|------------------|
| RTX 3090 | 24GB | $0.15-0.25 |
| RTX 4090 | 24GB | $0.25-0.40 |
| A100 | 80GB | $1.50-2.00 |
| H100 | 80GB | $2.50-3.50 |

**Suporte a Checkpoint**: ❌ Não
- **Testado em 20/12/2024**
- Capabilities ausentes:
  - CAP_SYS_PTRACE: ❌
  - CAP_SYS_ADMIN: ❌
  - CAP_CHECKPOINT_RESTORE: ❌
- Seccomp: Ativo (Seccomp: 2)

**Prós**:
- Preços mais baixos
- Grande variedade de GPUs
- Modelo P2P

**Contras**:
- Sem containers privilegiados
- Qualidade inconsistente
- Uptime não garantido

---

### Lambda Labs

**Website**: https://lambdalabs.com

**Tipo**: Managed Cloud

**Preços**:
| GPU | VRAM | Preço/hr |
|-----|------|----------|
| A100 | 40GB | $1.29 |
| A100 | 80GB | $1.79 |
| H100 | 80GB | $2.99-3.29 |

**Suporte a Checkpoint**: ❌ Não (não confirmado oficialmente, mas provável)

**Cobrança**: Por **minuto** (não hora) - útil para cold starts curtos

**Prós**:
- Cobrança por minuto
- Boa reputação
- Focado em ML

**Contras**:
- Provavelmente sem privileged containers
- Inventário limitado

---

### CoreWeave

**Website**: https://coreweave.com

**Tipo**: Kubernetes Cloud

**Preços**:
| GPU | VRAM | Preço/hr |
|-----|------|----------|
| A100 | 80GB | $2.21 |
| H100 | 80GB | $4.76 |

**Suporte a Checkpoint**: ⚠️ Negociável
- Kubernetes bare metal disponível (CKS)
- Requer contrato enterprise
- Pode configurar pods privilegiados

**Prós**:
- Alta performance
- Kubernetes nativo
- Enterprise-grade

**Contras**:
- Requer contrato
- Mínimo de commitment
- Setup mais complexo

---

### HOSTKEY

**Website**: https://hostkey.com

**Tipo**: Bare Metal Dedicated

**Preços**: Sob consulta (geralmente ~$3-4/hr para H100)

**Suporte a Checkpoint**: ✅ Sim
- Acesso root completo
- Sem restrições de container
- Full control

**Prós**:
- Controle total
- Sem limitações
- Suporte enterprise

**Contras**:
- Preço não transparente
- Geralmente requer commitment
- Setup manual

---

### AWS/GCP/Azure

**Tipo**: Enterprise Cloud

**Preços** (AWS p5.48xlarge - 8x H100):
- On-demand: ~$98/hr (~$12/hr por GPU)
- Bare metal: $32+/hr por GPU

**Suporte a Checkpoint**: ⚠️ Possível mas caro
- Bare metal instances disponíveis
- Acesso root possível
- Mas preço 10x maior

**Prós**:
- Compliance
- Integração com outros serviços
- SLA garantido

**Contras**:
- **Muito caro** para experimentos
- Complexidade de setup

---

## Matriz de Decisão

### Para Desenvolvimento/Testes
→ **TensorDock** (V100 a $0.45/hr ou RTX 4090 a $0.35/hr)

### Para Produção com Checkpoint
→ **TensorDock Bare Metal** ou **HOSTKEY**

### Para Produção sem Checkpoint
→ **RunPod** (melhor UX) ou **Lambda** (cobrança por minuto)

### Para Enterprise com Compliance
→ **CoreWeave** (negociar) ou **AWS/GCP**

### Para Orçamento Mínimo
→ **Vast.ai** (aceitar limitações)

## Configuração TensorDock para DumontCloud

### 1. Criar Conta
https://dashboard.tensordock.com/register

### 2. Adicionar SSH Key
Account Settings → SSH Keys → Add sua `~/.ssh/id_rsa.pub`

### 3. Deploy VM
- Location: Qualquer
- GPU: V100 ou RTX 4090 (para testes)
- OS: Ubuntu 22.04
- SSH Key: Selecionar a adicionada

### 4. Setup Inicial
```bash
# Conectar
ssh user@<IP>

# Instalar driver 570
sudo apt-get update
sudo apt-get install -y nvidia-driver-570
sudo reboot

# Clonar cuda-checkpoint
git clone https://github.com/NVIDIA/cuda-checkpoint.git

# Testar
~/cuda-checkpoint/bin/x86_64_Linux/cuda-checkpoint --help
```

### 5. Destroy Quando Terminar
**IMPORTANTE**: Destroy a VM no dashboard para parar cobrança!
Stop apenas reduz (não para) a cobrança.
