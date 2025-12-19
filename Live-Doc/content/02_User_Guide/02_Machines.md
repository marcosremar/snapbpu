# Gerenciando Maquinas

## Visao Geral

Maquinas sao instancias de GPU que voce aluga para rodar seus workloads. Cada maquina vem pre-configurada com CUDA, drivers e bibliotecas ML.

---

## Criar Nova Maquina

### Via Dashboard

1. Va em **Machines** no menu
2. Clique em **"Nova Maquina"**
3. Configure:
   - **GPU**: Escolha o modelo (RTX 4090, A100, etc)
   - **Imagem**: PyTorch, TensorFlow, ou custom
   - **Disco**: Tamanho do storage (50GB-2TB)
   - **Regiao**: us-east, us-west, eu-west
4. Clique em **"Lancar"**

### Via AI Wizard

O AI Wizard analisa seu projeto e recomenda a melhor configuracao:

1. Clique em **"AI Wizard"**
2. Descreva seu workload:
   > "Treinar LLaMA 7B com batch size 32"
3. Revise a recomendacao
4. Clique em **"Aceitar e Lancar"**

---

## Status das Maquinas

| Status | Descricao | Cobranca |
|--------|-----------|----------|
| **Running** | Ativa e pronta | Sim |
| **Starting** | Inicializando | Nao |
| **Stopping** | Desligando | Nao |
| **Stopped** | Desligada | Nao |
| **Standby** | Em CPU fallback | Reducido |
| **Error** | Com problema | Nao |

---

## Acoes Disponiveis

### Conectar
- **SSH**: `ssh root@<IP> -p <PORTA>`
- **Jupyter**: Clique em "Open Jupyter"
- **VS Code**: Clique em "Open VS Code"
- **Terminal Web**: Clique em "Terminal"

### Pausar / Retomar
- Pausar salva o estado e para cobranca
- Retomar restaura em ~30 segundos
- Dados permanecem intactos

### Reiniciar
- Reinicia a maquina mantendo dados
- Util para resolver problemas

### Desligar
- Para completamente a maquina
- Dados sao preservados no backup
- Nao cobra enquanto desligada

### Deletar
- Remove a maquina permanentemente
- **ATENCAO**: Dados locais serao perdidos
- Backups permanecem por 7 dias

---

## Monitoring

### Metricas em Tempo Real
- **GPU Usage**: Utilizacao da GPU (%)
- **GPU Memory**: VRAM utilizada
- **CPU**: Uso do processador
- **RAM**: Memoria do sistema
- **Disk**: Espaco em disco
- **Network**: Trafego de rede

### Graficos Historicos
- Ultimas 24 horas
- Ultima semana
- Ultimo mes

### Alertas
Configure alertas para:
- GPU > 90% por 5 minutos
- Disco > 85%
- Memoria > 90%
- Maquina offline

---

## SSH Keys

### Adicionar Chave SSH
1. Va em **Settings** > **SSH Keys**
2. Clique em **"Adicionar Chave"**
3. Cole sua chave publica
4. Clique em **"Salvar"**

### Gerar Nova Chave
```bash
ssh-keygen -t ed25519 -C "seu@email.com"
cat ~/.ssh/id_ed25519.pub
```

---

## Snapshots

### Criar Snapshot
1. Selecione a maquina
2. Clique em **"Criar Snapshot"**
3. De um nome descritivo
4. Aguarde (~2-5 minutos)

### Restaurar Snapshot
1. Va em **Snapshots**
2. Selecione o snapshot
3. Clique em **"Restaurar"**
4. Escolha nova maquina ou existente

---

## Troubleshooting

### Maquina nao inicia
1. Verifique seu saldo
2. Tente outra regiao
3. Tente outro modelo de GPU

### Conexao SSH falha
1. Aguarde 60s apos "Running"
2. Verifique IP e porta no dashboard
3. Confirme sua SSH key

### GPU nao detectada
```bash
nvidia-smi
# Se erro, reinicie a maquina
```

### Disco cheio
```bash
df -h
# Limpe arquivos desnecessarios
rm -rf /tmp/*
```
