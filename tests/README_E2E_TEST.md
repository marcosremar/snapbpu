# 🧪 Teste End-to-End: Sistema Completo de Failover

## 📋 O Que Este Teste Faz

Testa **TUDO** automaticamente:

1. ✅ Cria 2 máquinas (GPU + CPU backup)
2. ✅ Instala VS Code Server em ambas  
3. ✅ Configura sincronização em tempo real
4. ✅ Edita arquivo via SSH
5. ✅ Verifica se sincronizou
6. ✅ Desliga GPU
7. ✅ Verifica failover automático para CPU
8. ✅ **Mostra mensagens de redirecionamento**
9. ✅ Cleanup (reativa GPU)

## 🚀 Executar Teste

### Automático (Completo)

```bash
cd /home/ubuntu/dumont-cloud
python3 tests/test_end_to_end_failover.py
```

### Manual (Passo a Passo para Debug)

```bash
# 1. Criar GPU (ou usar existente)
export GPU_HOST="ssh4.vast.ai"
export GPU_PORT="38784"

# 2. Criar CPU backup
python3 << EOF
from src.infrastructure.providers.gcp_provider import GCPProvider, GCPInstanceConfig
gcp = GCPProvider(credentials_path=".credentials/gcp-service-account.json")
config = GCPInstanceConfig(
    name="test-failover-cpu",
    machine_type="e2-medium",
    zone="us-central1-a"
)
result = gcp.create_instance(config)
print(f"CPU IP: {result['external_ip']}")
EOF

# Salvar IP da CPU
export CPU_HOST="35.240.x.x"  # IP retornado acima

# 3. Instalar VS Code Server na GPU
ssh -p $GPU_PORT root@$GPU_HOST << 'SCRIPT'
curl -fsSL https://code-server.dev/install.sh | sh
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml << EOF
bind-addr: 0.0.0.0:8080
auth: password
password: dumont-test-2024
cert: false
EOF
systemctl enable --now code-server
SCRIPT

# 4. Instalar VS Code Server na CPU
ssh root@$CPU_HOST << 'SCRIPT'
# ... mesmo script acima ...
SCRIPT

# 5. Configurar sync em tempo real
ssh -p $GPU_PORT root@$GPU_HOST << 'SCRIPT'
apt-get update && apt-get install -y lsyncd
cat > /etc/lsyncd/lsyncd.conf.lua << EOF
settings { logfile = "/var/log/lsyncd.log", maxDelays = 1 }
sync { default.rssh, source = "/workspace", 
       host = "root@$CPU_HOST", targetdir = "/workspace", delay = 1 }
EOF
systemctl enable --now lsyncd
SCRIPT

# 6. Iniciar proxy failover
python3 scripts/vscode_failover.py $GPU_HOST 8080 $CPU_HOST 8080 &
PROXY_PID=$!

# 7. Criar arquivo de teste
ssh -p $GPU_PORT root@$GPU_HOST \
    "echo 'Test at $(date)' > /workspace/test_failover.txt"

# 8. Aguardar sync (2s)
sleep 2

# 9. Verificar sync na CPU
ssh root@$CPU_HOST "cat /workspace/test_failover.txt"

# 10. Desligar GPU
ssh -p $GPU_PORT root@$GPU_HOST "systemctl stop code-server"

# 11. Testar proxy (deve redirecionar para CPU)
curl -I http://localhost:8888

# 12. Verificar logs do proxy
# Deve mostrar: "⚠️  GPU down! Failover para CPU"

# 13. Cleanup
kill $PROXY_PID
ssh -p $GPU_PORT root@$GPU_HOST "systemctl start code-server"
```

## 📊 Output Esperado

```
======================================================================
🧪 TESTE END-TO-END: Sistema de Failover Completo
======================================================================

[STEP 1] Criando máquina GPU no Vast.ai...
ℹ️  GPU: ssh4.vast.ai:38784
✅ GPU disponível!

[STEP 2] Criando CPU backup no GCP...
ℹ️  Criando CPU backup (pode demorar 1-2 min)...
✅ CPU criada: 35.240.1.2

[STEP 3] Instalando VS Code Server...
ℹ️  Instalando na GPU...
✅ VS Code Server instalado na GPU
ℹ️  Instalando na CPU...
✅ VS Code Server instalado na CPU

[STEP 4] Configurando sincronização em tempo real...
✅ Sincronização em tempo real configurada!

[STEP 5] Iniciando proxy de failover...
✅ Proxy de failover ativo!

[STEP 6] Criando e editando arquivo de teste...
✅ Arquivo criado: /workspace/test/test_failover.txt

[STEP 7] Verificando sincronização...
Aguardando sincronização..... OK!
✅ Arquivo sincronizado com sucesso!

[STEP 8] Simulando falha da GPU...
GPU parando... OK!
✅ GPU 'desligada' (code-server parado)

[STEP 9] Verificando failover automático...
ℹ️  Verificando redirecionamento...

======================================================================
FAILOVER DETECTADO!
======================================================================
❌ GPU está DOWN: ssh4.vast.ai:38784
✅ Redirecionando para CPU: 35.240.1.2:8080
🔄 Proxy URL: http://localhost:8888

Usuário continua acessando a mesma URL:
   http://localhost:8888

Mas agora está conectado na CPU backup! ✅
======================================================================

✅ Failover automático funcionando!

[STEP 10] Cleanup (opcional)...
✅ GPU reativada

======================================================================
📊 RESUMO DO TESTE
======================================================================

✅ TODOS OS TESTES PASSARAM!

⏱️  Tempo total: 145.3s

📋 URLs de Acesso:
  Proxy (único): http://localhost:8888
  GPU direto: http://ssh4.vast.ai:8080
  CPU direto: http://35.240.1.2:8080
```

## 🎯 Mensagens de Redirecionamento

O teste mostra **claramente** quando o failover acontece:

```
======================================================================
FAILOVER DETECTADO!
======================================================================
❌ GPU está DOWN: ssh4.vast.ai:38784
✅ Redirecionando para CPU: 35.240.1.2:8080
🔄 Proxy URL: http://localhost:8888

Usuário continua acessando a mesma URL:
   http://localhost:8888

Mas agora está conectado na CPU backup! ✅
======================================================================
```

## 🔍 Verificar Manualmente

### Acessar via Browser

1. **Abrir VS Code Server:**
   ```
   http://localhost:8888
   Senha: dumont-test-2024
   ```

2. **Editar arquivo:**
   - Criar novo arquivo
   - Salvar

3. **Verificar sync:**
   ```bash
   ssh root@$CPU_HOST "ls -la /workspace"
   ```

4. **Desligar GPU:**
   ```bash
   ssh -p $GPU_PORT root@$GPU_HOST "systemctl stop code-server"
   ```

5. **Reload browser:**
   - Deve reconectar automaticamente
   - Agora conectado na CPU!

## 📂 Arquivos do Teste

- **`tests/test_end_to_end_failover.py`** - Teste automatizado completo
- **`scripts/vscode_failover.py`** - Proxy de failover
- **`scripts/setup_realtime_sync.sh`** - Setup de sync
- Este README

## ✅ Checklist de Validação

Após rodar o teste, verificar:

- [ ] GPU criada e acessível
- [ ] CPU backup criada e acessível
- [ ] VS Code Server rodando em ambas
- [ ] Sync em tempo real configurado
- [ ] Arquivo criado na GPU aparece na CPU em ~2s
- [ ] Proxy detecta GPU down
- [ ] **Mensagem de redirecionamento aparece**
- [ ] Proxy redireciona para CPU
- [ ] GPU pode ser reativada

## 🐛 Troubleshooting

### Teste falha ao criar CPU

```bash
# Verificar credenciais GCP
ls -la /home/ubuntu/dumont-cloud/.credentials/gcp-service-account.json

# Testar manualmente
python3 -c "from src.infrastructure.providers.gcp_provider import GCPProvider; \
    gcp = GCPProvider(credentials_path='.credentials/gcp-service-account.json'); \
    print('OK' if gcp.credentials else 'FAIL')"
```

### Sync não funciona

```bash
# Verificar lsyncd
ssh -p $GPU_PORT root@$GPU_HOST "systemctl status lsyncd"
ssh -p $GPU_PORT root@$GPU_HOST "tail /var/log/lsyncd.log"
```

### Proxy não redireciona

```bash
# Verificar health check
curl http://localhost:8888/health

# Deve retornar:
# {"status": "ok", "active_target": "cpu", ...}
```

## 🚀 Executar Agora

```bash
# Teste completo automático
python3 tests/test_end_to_end_failover.py

# Ou com mais verbosidade
python3 -u tests/test_end_to_end_failover.py 2>&1 | tee test_output.log
```

**Todo o sistema validado em um único comando!** ✅
