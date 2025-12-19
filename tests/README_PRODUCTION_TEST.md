# 🧪 Teste de Produção: Failover com Modelo Real (Llama 7B)

## 🎯 O Que Este Teste Faz

Testa o **cenário REAL** de interrupção de GPU Spot com dados de produção:

### Fluxo Completo:

1. ✅ Cria CPU backup no GCP
2. ✅ **Baixa Llama 7B (~4GB)** via Ollama na GPU
3. ✅ Configura **sync em tempo real** (lsyncd)
4. ✅ Cria arquivos de trabalho (código Python, configs)
5. ✅ **FORÇA shutdown abrupto** da GPU (simula spot interruption)
6. ✅ Verifica se dados sincronizaram para CPU
7. ✅ Verifica failover do VS Code Server
8. ✅ **Mede TUDO**: tempos, perdas, economia

## 📊 Métricas Medidas

- ⏱️ **Tempo de download** do modelo
- ⏱️ **Tempo de sync** inicial
- ⏱️ **Tempo de failover**
- 📦 **Tamanho de dados** sincronizados
- 💥 **Dados perdidos** na interrupção
- 📁 **Arquivos perdidos**
- ✅ **Taxa de sucesso** da sincronização
- 💰 **Economia estimada** com failover

## 🚀 Executar

### Pré-requisitos:

```bash
# 1. Credenciais GCP configuradas
ls -la /home/ubuntu/dumont-cloud/.credentials/gcp-service-account.json

# 2. GPU ativa
ssh -p 38784 root@ssh4.vast.ai "echo OK"
```

### Executar Teste:

```bash
cd /home/ubuntu/dumont-cloud
python3 tests/test_production_failover_llama.py
```

## 📊 Output Esperado

```
======================================================================
🧪 TESTE DE PRODUÇÃO: Failover com Modelo Real
======================================================================

[19:00:00] ======================================================================
[19:00:00] STEP 1: Criando CPU Backup no GCP
[19:00:00] ======================================================================
[19:00:01] ⏳ Criando CPU backup (e2-standard-2)...
[19:01:30] ✅ CPU criada: 35.240.1.2
[19:01:30]    Zone: us-central1-a
[19:01:30]    Type: e2-standard-2

[19:01:45] ======================================================================
[19:01:45] STEP 2: Baixando Modelo Llama 7B (~4GB)
[19:01:45] ======================================================================
[19:01:46] ⏳ Baixando modelo via Ollama...
[19:05:20] 📦 Modelo baixado: 4.0G
[19:05:20] ✅ Download concluído em 214.3s

[19:05:21] ======================================================================
[19:05:21] STEP 3: Configurando Sync em Tempo Real (lsyncd)
[19:05:21] ======================================================================
[19:05:22] ⏳ Instalando e configurando lsyncd...
[19:05:35] ✅ Lsyncd configurado em 13.2s
[19:05:35] ⏳ Sincronização inicial em andamento...
[19:06:05] ✅ Sync inicial verificado na CPU
[19:06:05]    4.0G    /root/.ollama
[19:06:05]    12K     /workspace

[19:06:06] ======================================================================
[19:06:06] STEP 4: Criando Arquivos de Trabalho
[19:06:06] ======================================================================
[19:06:07] ✅ Arquivos criados:
[19:06:07] -rw-r--r-- 1 root root  245 Dec 18 19:06 config.json
[19:06:07] -rw-r--r-- 1 root root  320 Dec 18 19:06 test_llm.py
[19:06:07] -rw-r--r-- 1 root root   89 Dec 18 19:06 work.log
[19:06:07] ⏳ Aguardando sync em tempo real (2s)...

[19:06:09] ======================================================================
[19:06:09] STEP 5: FORÇANDO SHUTDOWN DA GPU (Spot Interruption)
[19:06:09] ======================================================================
[19:06:10] ⚠️  Simulando interrupção súbita...
[19:06:11] 💥 GPU 'interrompida' (code-server killed)

[19:06:16] ======================================================================
[19:06:16] STEP 6: Verificando Sincronização e Failover
[19:06:16] ======================================================================
[19:06:16] 📂 Verificando arquivos na CPU...
[19:06:17] 📊 Estado da CPU:
[19:06:17] === Arquivos de Trabalho ===
[19:06:17] -rw-r--r-- 1 root root  245 Dec 18 19:06 config.json
[19:06:17] -rw-r--r-- 1 root root  320 Dec 18 19:06 test_llm.py
[19:06:17] -rw-r--r-- 1 root root   89 Dec 18 19:06 work.log
[19:06:17] 
[19:06:17] === Conteúdo config.json ===
[19:06:17] {
[19:06:17]     "model": "llama2:7b",
[19:06:17]     "created_at": "2024-12-18T19:06:06",
[19:06:17]     "temperature": 0.7
[19:06:17] }
[19:06:17] 
[19:06:17] === Modelo Ollama ===
[19:06:17] 4.0G    /root/.ollama
[19:06:17] 
[19:06:17] ✅ Projeto sincronizado!
[19:06:17] ✅ Config sincronizado!
[19:06:17] ✅ Modelo sincronizado!

[19:06:18] 🔄 Testando failover...
[19:06:19] ✅ VS Code Server ativo na CPU!

[19:06:19] ⏱️  Verificação concluída em 3.2s

======================================================================
📊 RELATÓRIO FINAL - TESTE DE PRODUÇÃO
======================================================================

⏱️  TEMPOS:
  Download modelo:      214.3s
  Setup sync:           13.2s
  Verificação failover: 3.2s
  TOTAL:               317.8s

📦 DADOS:
  Tamanho modelo:      4000 MB
  Perda de dados:      0 MB
  Arquivos perdidos:   0

✅ VALIDAÇÕES:
  ✅ Sincronização: FUNCIONANDO
  ✅ Failover: FUNCIONANDO
  ✅ Integridade: 100%

💰 ECONOMIA ESTIMADA:
  Sem failover: $0.08 perdidos por interrupção
  Com failover: $0.00 (continua trabalhando)
  💵 Economia: $0.08 por interrupção
  💵 Economia mensal: $2.50/mês

======================================================================
📄 Resultados salvos em: /tmp/failover_test_results.json
```

## 📊 Análise de Resultados

### Cenário Ideal (100% Sucesso):

```json
{
  "download_time": 214.3,
  "sync_time": 13.2,
  "failover_time": 3.2,
  "data_loss_mb": 0,
  "files_lost": 0,
  "total_time": 317.8,
  "model_size_mb": 4000,
  "sync_verified": true,
  "failover_verified": true
}
```

### Interpretação:

| Métrica | Valor Ideal | Problema Se |
|---------|-------------|-------------|
| `data_loss_mb` | 0 | > 0 (dados perdidos) |
| `files_lost` | 0 | > 0 (arquivos não sincronizados) |
| `sync_verified` | true | false (sync não funciona) |
| `failover_verified` | true | false (VS Code não disponível) |
| `download_time` | < 300s | > 600s (conexão lenta) |
| `failover_time` | < 10s | > 30s (delay grande) |

## 💰 Economia Real

### Cálculo:

**Sem failover:**
- GPU cai → Perde 10-30 minutos reprovisioning
- trabalho parado = $ perdido
- Frustração do usuário

**Com failover:**
- GPU cai → Automaticamente vai para CPU em 3-5s
- Trabalho continua sem interrupção
- Zero perda de produtividade

### Números:

```
GPU: $0.50/hora
CPU: $0.02/hora (spot)

1 interrupção spot/dia = 30/mês

Downtime médio sem failover: 15 min
Custo por interrupção: $0.125

Com failover:
- Continua na CPU
- Custo: $0.005 (15min de CPU)
- Economia: $0.12 por evento

Mensal: $0.12 × 30 = $3.60/mês por GPU
Anual: $43.20/ano por GPU

Com 10 GPUs: $432/ano economizados! 💰
```

## 🐛 Troubleshooting

### Teste falha no download do modelo

```bash
# Verificar conexão GPU
ssh -p 38784 root@ssh4.vast.ai "curl -I https://ollama.ai"

# Verificar espaço em disco
ssh -p 38784 root@ssh4.vast.ai "df -h /workspace"

# Tentar download manual
ssh -p 38784 root@ssh4.vast.ai "ollama pull llama2:7b"
```

### Sync não funciona

```bash
# Verificar lsyncd rodando
ssh -p 38784 root@ssh4.vast.ai "systemctl status lsyncd"

# Ver logs
ssh -p 38784 root@ssh4.vast.ai "tail -50 /var/log/lsyncd.log"

# Verificar conectividade SSH GPU → CPU
ssh -p 38784 root@ssh4.vast.ai "ssh -o StrictHostKeyChecking=no root@CPU_IP echo OK"
```

### CPU não criada

```bash
# Verificar credenciais GCP
python3 -c "
from src.infrastructure.providers.gcp_provider import GCPProvider
gcp = GCPProvider(credentials_path='.credentials/gcp-service-account.json')
print('OK' if gcp.credentials else 'FAIL')
"

# Criar manualmente
gcloud compute instances create test-failover \
  --zone=us-central1-a \
  --machine-type=e2-standard-2 \
  --provisioning-model=SPOT
```

## 🎯 O Que Validar

Após o teste, confirmar:

- [ ] Modelo Llama 7B baixado na GPU
- [ ] Lsyncd configurado e rodando
- [ ] Arquivos de trabalho criados
- [ ] **TODOS os arquivos sincronizados para CPU**
- [ ] **Modelo (4GB) sincronizado para CPU**
- [ ] Zero perda de dados
- [ ] Failover funcional (VS Code na CPU)
- [ ] Tempo total < 400s
- [ ] Economia > $0.10/interrupção

## ✅ Sucesso Se

```
✅ Sincronização: FUNCIONANDO
✅ Failover: FUNCIONANDO
✅ Integridade: 100%
💰 Economia confirmada
```

**Este é o teste que importa para economia real!** 💰🚀
