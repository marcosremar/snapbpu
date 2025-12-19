# Credenciais - Dumont Cloud

Este diretório contém credenciais sensíveis. **NÃO COMMITAR!**

## Arquivo: gcp-service-account.json

**Uso:** Credenciais do Google Cloud Platform (GCP) para:
- Criar VMs de backup (CPU Standby)
- Sincronizar dados GPU → CPU
- Gerenciar infrastructure on GCP

**Projeto GCP:** `avian-computer-477918-j9`
**Service Account:** `skypilot-v1@avian-computer-477918-j9.iam.gserviceaccount.com`

## Configuração

### Opção 1: Variável de Ambiente (Recomendado)

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/home/ubuntu/dumont-cloud/.credentials/gcp-service-account.json"
```

Adicione ao `~/.bashrc` ou `~/.profile` para permanência:
```bash
echo 'export GOOGLE_APPLICATION_CREDENTIALS="/home/ubuntu/dumont-cloud/.credentials/gcp-service-account.json"' >> ~/.bashrc
source ~/.bashrc
```

### Opção 2: Diretamente no Código

```python
from src.infrastructure.providers.gcp_provider import GCPProvider

gcp = GCPProvider(credentials_path="/home/ubuntu/dumont-cloud/.credentials/gcp-service-account.json")
```

## Verificar

```bash
# Testar se credenciais estão configuradas
python3 scripts/check_gcloud_backup.py

# Ou:
echo $GOOGLE_APPLICATION_CREDENTIALS
```

## Segurança

- ✅ Permissões: `600` (apenas owner pode ler)
- ✅ Diretório: `700` (apenas owner pode acessar)
- ✅ Gitignore: `.credentials/` está no .gitignore

**NUNCA commitar este arquivo no git!**
