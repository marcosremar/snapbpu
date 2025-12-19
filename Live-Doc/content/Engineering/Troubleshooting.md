# 🔧 Troubleshooting - Top 5 Problemas

## 1. ❌ Instância não inicia ("Status: creating" travado)

### Sintomas
- Status fica em `creating` por mais de 5 minutos
- Logs mostram: `Error: No available GPU in region`

### Causa Provável
- Vast.ai não tem GPUs disponíveis na região selecionada
- Orçamento insuficiente na conta Vast

### Solução
```bash
# 1. Verifique disponibilidade em outras regiões
curl https://dumontcloud.com/api/regions/availability

# 2. Tente outra região ou GPU
curl -X POST /api/instances \
  -d '{"gpu_type": "RTX 3090", "region": "EU-West"}'

# 3. Verifique saldo Vast.ai
python scripts/check_vast_balance.py
```

### Prevenção
- Configure **auto-retry** com fallback de região
- Ative alertas de saldo baixo

---

## 2. 💾 Snapshot falha com "Disk full"

### Sintomas
- Snapshot inicia mas falha em 50-80%
- Erro: `OSError: [Errno 28] No space left on device`

### Causa Provável
- Disco da instância ou do servidor S3 está cheio
- Muitos snapshots temporários não deletados

### Solução
```bash
# 1. Verifique espaço em disco
df -h /mnt/snapshots

# 2. Limpe snapshots antigos (>30 dias)
python scripts/cleanup_old_snapshots.py --days 30

# 3. Force garbage collection do Restic
restic -r s3:your-bucket forget --prune --keep-last 10
```

### Prevenção
- Ative **auto-cleanup** de snapshots antigos (Settings → Snapshots → Retention)
- Configure alerta quando disco >80%

---

## 3. 🔌 "Connection refused" ao acessar instância

### Sintomas
- SSH não conecta: `ssh: connect to host X.X.X.X port 22: Connection refused`
- VS Code não abre

### Causa Provável
- Instância ainda está iniciando (aguarde 2-3min)
- Firewall bloqueando porta 22 ou 8080
- Vast.ai atribuiu IP diferente do esperado

### Solução
```bash
# 1. Verifique se instância está UP
curl https://dumontcloud.com/api/instances/28864630

# 2. Tente o IP correto (atualizado)
ssh -i ~/.ssh/dumont.key ubuntu@<NOVO_IP>

# 3. Verifique firewall (dentro da instância)
sudo ufw status
sudo ufw allow 22
sudo ufw allow 8080
```

### Prevenção
- Use o **Dynamic DNS** do Dumont (always updated)
- Configure SSH KeepAlive para reconectar automaticamente

---

## 4. 🐌 Snapshot muito lento (< 50 MB/s)

### Sintomas
- Upload de 100GB leva > 30 minutos
- Dashboard mostra velocidade oscilando muito

### Causa Provável
- Compressão LZ4 desabilitada (usando gzip)
- s5cmd não configurado (usando boto3)
- Rede da instância congestionada

### Solução
```bash
# 1. Force usar s5cmd (não boto3)
export USE_S5CMD=true

# 2. Verifique se LZ4 está ativo
grep "compression" config.json  # deve ser "lz4", não "gzip"

# 3. Teste velocidade de rede
iperf3 -c speedtest.vast.ai
```

### Prevenção
- Sempre use `compression: lz4` em `config.json`
- Escolha instâncias com rede ≥ 1 Gbps

---

## 5. 💸 Custo inesperado alto (> $10/dia)

### Sintomas
- Fatura mensal 3x maior que esperado
- Dashboard mostra burn rate alto

### Causa Provável
- Auto-hibernação desativada (GPU rodando 24/7)
- Múltiplas GPUs esquecidas "running"
- Snapshots excessivos (>10 por dia)

### Solução
```bash
# 1. Veja todas as instâncias ativas
curl https://dumontcloud.com/api/machines

# 2. Hiberne ou delete as não usadas
curl -X POST /api/instances/28864630/hibernate

# 3. Ative auto-hibernação
curl -X PATCH /api/settings \
  -d '{"auto_hibernate_enabled": true, "idle_threshold_minutes": 5}'
```

### Prevenção
- **SEMPRE** ative auto-hibernação
- Configure alerta de custo diário (Settings → Billing → Daily Budget)
- Revise "Active Instances" toda semana

---

## 🆘 Ainda com problemas?

1. **Logs Completos**: Acesse `/api/logs/{instance_id}` e copie os últimos 100 linhas
2. **Status de Saúde**: Rode `curl https://dumontcloud.com/health`
3. **Suporte**: Abra ticket em [support@dumontcloud.com](mailto:support@dumontcloud.com) com logs anexados

---

**Última atualização**: 2025-12-19  
**Contribua**: Encontrou um bug novo? [Adicione aqui](https://github.com/dumont-cloud/docs/blob/main/troubleshooting.md)
