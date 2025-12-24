# Sprint: Teste e Funcionalidades dos Modos GPU

## Análise dos 4 Modos de Criação de Instâncias

### Estado Atual do CLI vs API

| Modo | API Existe | CLI Existe | Status |
|------|------------|------------|--------|
| **Jobs** | ✅ `/api/v1/jobs/` | ❌ Não tem | **FALTANDO** |
| **Fine-Tune** | ✅ `/api/v1/finetune/` | ❌ Não tem | **FALTANDO** |
| **Serverless** | ✅ `/api/v1/serverless/` | ✅ `dumont serverless` | OK |
| **Normal/Wizard** | ✅ `/api/v1/instances/` | ✅ `dumont wizard/instance` | OK |

---

## 1. JOBS (Executa e Destrói)

### 1.1 Funcionalidades da API (existentes)
- [x] `POST /api/v1/jobs/` - Criar job
- [x] `GET /api/v1/jobs/` - Listar jobs
- [x] `GET /api/v1/jobs/{job_id}` - Status de um job
- [x] `POST /api/v1/jobs/{job_id}/cancel` - Cancelar job
- [x] `GET /api/v1/jobs/{job_id}/logs` - Logs do job

### 1.2 Parâmetros Suportados
- `name` - Nome do job
- `source` - command | huggingface | git
- `command` - Comando a executar
- `hf_repo` - Repo HuggingFace
- `hf_token` - Token para repos privados
- `git_url` / `git_branch` - Repo Git
- `setup_script` - Script de setup
- `pip_packages` - Pacotes pip
- `gpu_type` - Tipo de GPU
- `num_gpus` - Quantidade de GPUs
- `use_spot` - Spot (true) ou On-demand (false)
- `disk_size` - Tamanho do disco
- `timeout_minutes` - Timeout máximo
- `image` - Imagem Docker
- `output_paths` - Paths para salvar

### 1.3 Comandos CLI a Implementar
```bash
dumont job create <name> --command="python train.py" --gpu="RTX 4090"
dumont job create <name> --source=huggingface --hf-repo="user/repo" --command="python main.py"
dumont job create <name> --source=git --git-url="https://github.com/..." --command="./run.sh"
dumont job list [--status=running|completed|failed]
dumont job status <job_id>
dumont job logs <job_id> [--tail=100]
dumont job cancel <job_id>
dumont job wait <job_id>  # Espera job completar
```

### 1.4 Testes a Realizar
- [ ] Criar job simples com comando
- [ ] Criar job com source=huggingface
- [ ] Criar job com source=git
- [ ] Criar job com use_spot=false (on-demand)
- [ ] Criar job com use_spot=true (spot)
- [ ] Listar jobs
- [ ] Ver status de job running
- [ ] Ver logs de job
- [ ] Cancelar job running
- [ ] Verificar destruição automática após conclusão
- [ ] Testar timeout
- [ ] Testar pip_packages instalação
- [ ] Testar setup_script execução

---

## 2. FINE-TUNE (Via SkyPilot)

### 2.1 Funcionalidades da API (existentes)
- [x] `GET /api/v1/finetune/models` - Listar modelos suportados
- [x] `POST /api/v1/finetune/jobs/upload-dataset` - Upload dataset
- [x] `POST /api/v1/finetune/jobs` - Criar job de fine-tuning
- [x] `GET /api/v1/finetune/jobs` - Listar jobs
- [x] `GET /api/v1/finetune/jobs/{job_id}` - Status do job
- [x] `GET /api/v1/finetune/jobs/{job_id}/logs` - Logs
- [x] `POST /api/v1/finetune/jobs/{job_id}/cancel` - Cancelar
- [x] `POST /api/v1/finetune/jobs/{job_id}/refresh` - Atualizar status

### 2.2 Modelos Suportados (Unsloth)
- Llama 3 8B (`unsloth/llama-3-8b-bnb-4bit`)
- Llama 3 70B (`unsloth/llama-3-70b-bnb-4bit`)
- Mistral 7B (`unsloth/mistral-7b-bnb-4bit`)
- Gemma 7B (`unsloth/gemma-7b-bnb-4bit`)
- Qwen 2 7B (`unsloth/Qwen2-7B-bnb-4bit`)
- Phi-3 Mini 4K (`unsloth/Phi-3-mini-4k-instruct-bnb-4bit`)

### 2.3 Comandos CLI a Implementar
```bash
dumont finetune models                    # Listar modelos suportados
dumont finetune upload <file.jsonl>       # Upload dataset
dumont finetune create <name> \
  --model="unsloth/llama-3-8b-bnb-4bit" \
  --dataset=<path> \
  --format=alpaca \
  --gpu="A100" \
  --epochs=3 \
  --lr=2e-4
dumont finetune list [--status=running]
dumont finetune status <job_id>
dumont finetune logs <job_id> [--tail=100]
dumont finetune cancel <job_id>
dumont finetune refresh <job_id>
```

### 2.4 Testes a Realizar
- [ ] Listar modelos suportados
- [ ] Upload de dataset JSON/JSONL
- [ ] Criar fine-tuning com Llama 3 8B
- [ ] Criar fine-tuning com Qwen 2 7B
- [ ] Testar formato alpaca
- [ ] Testar formato sharegpt
- [ ] Ver status do job
- [ ] Ver logs em tempo real
- [ ] Cancelar job
- [ ] Verificar integração com SkyPilot
- [ ] Testar configurações LoRA (rank, alpha)
- [ ] Verificar output do modelo treinado

---

## 3. SERVERLESS (Pausa/Resume)

### 3.1 Funcionalidades da API (existentes)
- [x] `POST /api/v1/serverless/enable/{instance_id}` - Habilitar
- [x] `POST /api/v1/serverless/disable/{instance_id}` - Desabilitar
- [x] `GET /api/v1/serverless/status/{instance_id}` - Status
- [x] `GET /api/v1/serverless/list` - Listar
- [x] `POST /api/v1/serverless/wake/{instance_id}` - Acordar
- [x] `GET /api/v1/serverless/pricing` - Preços

### 3.2 Comandos CLI Existentes
```bash
dumont serverless enable <instance_id> [mode=spot|economic|fast]
dumont serverless disable <instance_id>
dumont serverless status <instance_id>
dumont serverless list
dumont serverless wake <instance_id>
dumont serverless pricing
```

### 3.3 Testes a Realizar
- [ ] Habilitar serverless modo economic em instância
- [ ] Habilitar serverless modo spot
- [ ] Habilitar serverless modo fast (com CPU Standby)
- [ ] Verificar detecção de idle
- [ ] Verificar pausa automática após idle
- [ ] Acordar instância pausada
- [ ] Desabilitar serverless
- [ ] Listar instâncias serverless
- [ ] Verificar pricing por modo
- [ ] Testar idle_timeout_seconds
- [ ] Testar gpu_threshold

---

## 4. MÁQUINAS NORMAIS (Deploy Wizard)

### 4.1 Funcionalidades da API (existentes)
- [x] `POST /api/v1/instances/` - Criar instância
- [x] `GET /api/v1/instances/` - Listar
- [x] `GET /api/v1/instances/{id}` - Detalhes
- [x] `POST /api/v1/instances/{id}/pause` - Pausar
- [x] `POST /api/v1/instances/{id}/resume` - Resumir
- [x] `DELETE /api/v1/instances/{id}` - Deletar
- [x] `GET /api/v1/instances/offers` - Ofertas disponíveis

### 4.2 Comandos CLI Existentes
```bash
dumont wizard deploy [gpu_name] [speed=fast] [price=2.0] [region=global]
dumont instance list [status=running|paused]
dumont instance get <id>
dumont instance pause <id>
dumont instance resume <id>
dumont instance delete <id>
dumont instance offers
dumont model install <instance_id> <model_name>
```

### 4.3 Testes a Realizar
- [ ] Deploy com wizard (multi-start)
- [ ] Deploy GPU específica (RTX 4090)
- [ ] Deploy com speed tier (slow, medium, fast, ultra)
- [ ] Deploy com região específica
- [ ] Listar instâncias
- [ ] Pausar instância
- [ ] Resumir instância pausada
- [ ] Deletar instância
- [ ] Instalar modelo Ollama
- [ ] Ver ofertas disponíveis
- [ ] Testar blacklist de máquinas
- [ ] Testar history de tentativas

---

## 5. SPOT (Failover Automático)

### 5.1 Comandos CLI Existentes
```bash
dumont spot template create <instance_id> [--region=US]
dumont spot template list
dumont spot deploy --template=<id> [--max-price=0.5] [--gpu=RTX4090]
dumont spot status <instance_id>
dumont spot list
dumont spot pricing [--region=US] [--gpu=RTX4090]
dumont spot failover <instance_id>
```

### 5.2 Testes a Realizar
- [ ] Criar template de instância existente
- [ ] Listar templates
- [ ] Deploy spot a partir de template
- [ ] Ver status de instância spot
- [ ] Listar instâncias spot
- [ ] Ver pricing por região/GPU
- [ ] Trigger failover manual
- [ ] Testar failover automático (simular interrupção)
- [ ] Verificar restauração de workspace

---

## 6. AUXILIARES

### 6.1 History/Blacklist
```bash
dumont history summary [--provider=vast] [--hours=24]
dumont history list [--provider=vast] [--hours=72]
dumont history stats <provider> <machine_id>
dumont history problematic [--provider=vast]
dumont history reliable [--provider=vast]
dumont blacklist list
dumont blacklist add <provider> <machine_id> <reason>
dumont blacklist remove <provider> <machine_id>
dumont blacklist check <provider> <machine_id>
```

### 6.2 Autenticação
```bash
dumont auth login <email> <password>
dumont auth logout
dumont auth me
dumont auth register <email> <password>
```

---

## Funcionalidades Faltantes (A Implementar)

### Alta Prioridade
1. **CLI para Jobs** - Comandos `dumont job` completos
2. **CLI para Fine-Tune** - Comandos `dumont finetune` completos
3. **Testes automatizados** para cada modo

### Média Prioridade
4. **Job com HF_TOKEN** - Suporte a repos privados HuggingFace
5. **Fine-tune output** - Download do modelo treinado
6. **Serverless notifications** - Webhook quando acorda/pausa
7. **Spot monitoring** - Dashboard de interrupções

### Baixa Prioridade
8. **Job scheduling** - Agendar jobs para horários específicos
9. **Fine-tune presets** - Configurações pré-definidas por caso de uso
10. **Multi-GPU jobs** - Jobs distribuídos em múltiplas GPUs

---

## Ordem de Execução do Sprint

### Fase 1: Implementar CLI Faltante
1. [ ] Adicionar comandos `dumont job` no CLI
2. [ ] Adicionar comandos `dumont finetune` no CLI
3. [ ] Testar todos os comandos manualmente

### Fase 2: Testar Cada Modo
4. [ ] Testar Jobs (criar, monitorar, cancelar)
5. [ ] Testar Fine-Tune (criar, monitorar)
6. [ ] Testar Serverless (enable, idle, wake)
7. [ ] Testar Wizard Deploy (multi-start)
8. [ ] Testar Spot (template, deploy, failover)

### Fase 3: Corrigir Bugs
9. [ ] Documentar bugs encontrados
10. [ ] Corrigir bugs críticos
11. [ ] Re-testar após correções

### Fase 4: Testes Automatizados
12. [ ] Criar suite de testes pytest
13. [ ] Testes de integração real (com VAST.ai)
14. [ ] CI/CD para rodar testes

---

## Arquivos Relevantes

### CLI
- `cli/dumont_cli.py` - CLI principal

### Jobs
- `src/api/v1/endpoints/jobs.py` - API endpoints
- `src/services/job/job_manager.py` - Lógica de negócio
- `src/domain/models/job.py` - Modelo de dados

### Fine-Tune
- `src/api/v1/endpoints/finetune.py` - API endpoints
- `src/domain/services/finetune_service.py` - Lógica de negócio
- `src/infrastructure/providers/skypilot_provider.py` - Integração SkyPilot

### Serverless
- `src/api/v1/endpoints/serverless.py` - API endpoints

### Wizard/Instances
- `src/api/v1/endpoints/instances.py` - API endpoints
- `src/services/deploy_wizard.py` - Wizard multi-start

### Spot
- `src/api/v1/endpoints/spot_deploy.py` - API endpoints
- `src/services/spot/` - Spot manager
