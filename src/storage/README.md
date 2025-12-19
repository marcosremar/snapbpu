# Storage Module - Dumont Cloud

Sistema centralizado de storage que suporta múltiplos providers (Backblaze B2, Cloudflare R2, AWS S3, Wasabi).

## 🚀 Uso Rápido

### Opção 1: Usar o provider padrão (Backblaze B2 - Recomendado)

```python
from src.storage import get_storage_config

# Pega automaticamente a configuração (Backblaze B2 por padrão)
config = get_storage_config()

print(f"Usando: {config.display_name}")
print(f"Endpoint: {config.endpoint}")
print(f"Bucket: {config.bucket}")
```

### Opção 2: Trocar provider via variável de ambiente

```bash
# No terminal
export STORAGE_PROVIDER=r2  # ou b2, s3, wasabi

# No código Python (não precisa mudar nada!)
from src.storage import get_storage_config
config = get_storage_config()  # Usa automaticamente o R2
```

### Opção 3: Trocar provider no código

```python
from src.storage import StorageConfig

# Mudar o padrão
StorageConfig.set_default_provider('b2')  # ou 'r2', 's3', 'wasabi'

# Agora todas as chamadas usam o novo padrão
config = StorageConfig.get_default()
```

### Opção 4: Usar provider específico diretamente

```python
from src.storage import StorageConfig

# Pegar config de um provider específico
b2_config = StorageConfig.get_provider('b2')
r2_config = StorageConfig.get_provider('r2')
s3_config = StorageConfig.get_provider('s3')
```

## 📋 Providers Disponíveis

| Provider | Nome Código | Velocidade | Custo | Recomendado |
|----------|-------------|------------|-------|-------------|
| **Backblaze B2** | `b2` | **1.5 GB/s** | $6/TB | ✅ **Sim** |
| Cloudflare R2 | `r2` | 100 MB/s | Grátis | ❌ Muito lento |
| AWS S3 | `s3` | 2+ GB/s | $23/TB | 💰 Caro |
| Wasabi | `wasabi` | 500 MB/s | $7/TB flat | ⭐ Boa opção |

## 🔧 Configuração Avançada

### Variáveis de Ambiente

#### Backblaze B2 (Padrão)
```bash
export STORAGE_PROVIDER=b2
export B2_KEY_ID="003a1ef6268a3f30000000002"
export B2_APPLICATION_KEY="K003vYodS+gmuU83zDEDNy2EIv5ddnQ"
export B2_BUCKET="dumoncloud-snapshot"
export B2_REGION="us-west-004"
```

#### Cloudflare R2
```bash
export STORAGE_PROVIDER=r2
export R2_ACCOUNT_ID="142ed673a5cc1a9e91519c099af3d791"
export R2_ACCESS_KEY="f0a6f424064e46c903c76a447f5e73d2"
export R2_SECRET_KEY="1dcf325fe8556fca221cf8b383e277e7af6660a246148d5e11e4fc67e822c9b5"
export R2_BUCKET="musetalk"
```

#### AWS S3
```bash
export STORAGE_PROVIDER=s3
export AWS_ACCESS_KEY_ID="seu_access_key"
export AWS_SECRET_ACCESS_KEY="seu_secret_key"
export S3_BUCKET="dumont-snapshots"
export AWS_REGION="us-east-1"
```

#### Wasabi
```bash
export STORAGE_PROVIDER=wasabi
export WASABI_ACCESS_KEY="seu_access_key"
export WASABI_SECRET_KEY="seu_secret_key"
export WASABI_BUCKET="dumont-snapshots"
export WASABI_REGION="us-east-1"
```

## 💡 Exemplos Práticos

### Integração com GPUSnapshotService

```python
from src.storage import get_storage_config
from src.services.gpu_snapshot_service import GPUSnapshotService

# Pega config automaticamente (B2 por padrão)
config = get_storage_config()

# Cria o serviço de snapshot
service = GPUSnapshotService(config.endpoint, config.bucket)

# Criar snapshot
snapshot_info = service.create_snapshot(
    instance_id="my-instance",
    ssh_host="1.2.3.4",
    ssh_port=22,
    workspace_path="/workspace"
)

print(f"Snapshot criado com {config.display_name}!")
```

### Listar Providers Disponíveis

```python
from src.storage import StorageConfig

providers = StorageConfig.list_providers()
for p in providers:
    status = "✅ Recomendado" if p['recommended'] else "📦 Disponível"
    print(f"{status} - {p['display_name']} ({p['name']})")
```

Saída:
```
✅ Recomendado - Backblaze B2 (b2)
📦 Disponível - Cloudflare R2 (r2)
📦 Disponível - AWS S3 (s3)
📦 Disponível - Wasabi (wasabi)
```

## 🎯 Decisão: Qual Provider Usar?

### Use Backblaze B2 se:
- ✅ Você quer máxima velocidade (31x mais rápido que R2)
- ✅ Custo é ok ($6/TB)
- ✅ Quer a melhor experiência (padrão recomendado)

### Use Cloudflare R2 se:
- ✅ Custo zero é crítico
- ❌ Mas aceita velocidade 31x menor

### Use AWS S3 se:
- ✅ Já usa AWS e precisa integração
- ❌ Mas aceita pagar 4x mais

### Use Wasabi se:
- ✅ Quer custo fixo previsível
- ✅ Volume muito alto de restores
- ⭐ Boa opção intermediária

## 🔄 Como Trocar de Provider

É só mudar uma variável de ambiente - **ZERO MUDANÇAS NO CÓDIGO**:

```bash
# Estava usando R2
export STORAGE_PROVIDER=r2
python app.py  # Usa R2

# Agora quer B2 (31x mais rápido)
export STORAGE_PROVIDER=b2
python app.py  # Usa B2 - MESMO CÓDIGO!
```

## 📊 Benchmarks

Testado em RTX 3060 (5.4 Gbps) com arquivo de 500MB:

| Provider | Upload | Download | Total | vs R2 |
|----------|--------|----------|-------|-------|
| Backblaze B2 | 1783 MB/s | 1590 MB/s | 3373 MB/s | **31x** ✅ |
| Cloudflare R2 | 44 MB/s | 64 MB/s | 108 MB/s | 1x |

**Veredito**: Use Backblaze B2! 🚀
