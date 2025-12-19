# Quick Start - 5 Minutos

## Passo 1: Criar Conta

1. Acesse [dumontcloud.com](https://dumontcloud.com)
2. Clique em **"Criar Conta"**
3. Preencha email e senha
4. Confirme seu email

---

## Passo 2: Adicionar Creditos

1. Va em **Dashboard** > **Billing**
2. Clique em **"Adicionar Creditos"**
3. Escolha o valor (minimo $10)
4. Pague via **Cartao**, **PIX** ou **Boleto**

> **Dica**: Novos usuarios ganham **$79 em creditos gratis** por 7 dias!

---

## Passo 3: Lancar sua GPU

### Via Dashboard (Recomendado)

1. Va em **Machines** > **"Nova Maquina"**
2. Escolha a GPU desejada (ex: RTX 4090)
3. Selecione a imagem (PyTorch, TensorFlow, etc)
4. Clique em **"Lancar"**

### Via AI Wizard

1. Clique em **"AI Wizard"** no menu
2. Descreva seu projeto:
   > "Quero treinar um modelo LLM com 7B parametros"
3. O wizard recomenda a melhor GPU automaticamente

---

## Passo 4: Conectar

Apos a maquina iniciar (~30s), voce pode conectar via:

### SSH
```bash
ssh -p 22 root@<IP_DA_MAQUINA>
```

### Jupyter Notebook
Acesse: `https://<ID>.dumontcloud.com:8888`

### VS Code (Browser)
Clique em **"Open VS Code"** no dashboard

---

## Passo 5: Comecar a Trabalhar

Sua maquina ja vem com:
- CUDA 12.x instalado
- PyTorch / TensorFlow
- Jupyter Lab
- Git, vim, tmux

**Pronto!** Comece a rodar seus modelos.

---

## Proximos Passos

- [Entender o sistema de Billing](/admin/doc/live#02_User_Guide/01_Billing.md)
- [Configurar backups automaticos](/admin/doc/live#03_Features/02_Auto_Backup.md)
- [Usar o Spot Market](/admin/doc/live#03_Features/03_Spot_Market.md)
