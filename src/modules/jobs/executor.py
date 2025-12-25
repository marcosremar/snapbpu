"""
Jobs Module - Executor

Executor responsável por:
1. Provisionar GPU via MachineProvisionerService (com failover automático)
2. Executar o job
3. Coletar resultados (upload automático para Storage com expiração de 24h)
4. Destruir a instância
"""

import logging
import time
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StorageInfo:
    """Informações de storage do output"""
    file_key: str
    download_url: str
    size_bytes: int
    file_count: int = 1
    expires_at: Optional[datetime] = None


@dataclass
class CheckpointSyncConfig:
    """Configuração de sync periódico de checkpoints"""
    enabled: bool = True
    interval_minutes: int = 5  # Sync a cada 5 minutos
    sync_path: str = "/workspace/output"  # Path para sincronizar
    provider: str = "gcs"  # gcs ou b2


@dataclass
class ExecutionResult:
    """Resultado da execução de um job"""
    success: bool
    exit_code: int
    duration_seconds: float
    output: Optional[str] = None
    error: Optional[str] = None
    output_url: Optional[str] = None
    cost_usd: float = 0
    gpu_name: Optional[str] = None
    instance_id: Optional[int] = None
    # Storage info para outputs
    storage_info: Optional[StorageInfo] = None
    # Checkpoint syncs realizados
    checkpoint_syncs: int = 0
    last_checkpoint_at: Optional[datetime] = None


class JobExecutor:
    """
    Executor de jobs em GPUs VAST.ai.

    Usa MachineProvisionerService para provisionar com failover automático.

    Fluxo:
    1. Provisionar GPU (via MachineProvisionerService.provision_with_failover)
    2. Executar comando do job
    3. Coletar output
    4. Destruir instância
    """

    def __init__(
        self,
        vast_service,
        execution_timeout: int = 3600,
        ssh_key_path: Optional[str] = None,
        storage_service=None,
        auto_upload_output: bool = True,
        output_expires_hours: int = 24,
    ):
        """
        Args:
            vast_service: Serviço VAST.ai
            execution_timeout: Timeout padrão de execução (segundos)
            ssh_key_path: Caminho da chave SSH
            storage_service: StorageService para upload automático de outputs
            auto_upload_output: Se True, faz upload automático de /workspace/output
            output_expires_hours: Horas até expiração do output (padrão: 24)
        """
        self.vast_service = vast_service
        self.execution_timeout = execution_timeout
        self.ssh_key_path = ssh_key_path or "~/.ssh/id_ed25519"
        self.storage_service = storage_service
        self.auto_upload_output = auto_upload_output
        self.output_expires_hours = output_expires_hours

    def execute(
        self,
        job_config: Dict[str, Any],
        on_log: Optional[Callable[[str, str], None]] = None,
    ) -> ExecutionResult:
        """
        Executa um job completo.

        Args:
            job_config: Configuração do job com:
                - job_id: ID único do job
                - user_id: ID do usuário
                - docker_image: Imagem Docker
                - command: Comando a executar
                - gpu_name: Nome da GPU (opcional)
                - max_price: Preço máximo por hora
                - disk_gb: Espaço em disco
                - env_vars: Variáveis de ambiente
                - timeout_seconds: Timeout de execução
                - input_path: Caminho de entrada (opcional)
                - output_path: Caminho de saída (opcional, legado)
                - storage_provider: "gcs" ou "b2" (opcional, default: gcs)
                - output_expires_hours: Horas até expirar output (default: 24)
            on_log: Callback para logs (level, message)

        Returns:
            ExecutionResult com detalhes da execução

        Fluxo:
            1. Provisiona GPU via VAST.ai
            2. Executa comando
            3. Copia /workspace/output para Storage (GCS ou B2)
            4. Destrói GPU
            5. Retorna URL de download (válida por 24h)
        """
        start_time = time.time()
        instance_id = None
        hourly_rate = 0.0

        def log(level: str, msg: str):
            logger.log(getattr(logging, level), msg)
            if on_log:
                on_log(level, msg)

        try:
            # 1. Provisionar GPU usando MachineProvisionerService
            log("INFO", "Provisionando GPU...")

            from src.services.gpu.strategies import MachineProvisionerService, ProvisionConfig

            provisioner = MachineProvisionerService(self.vast_service.api_key)

            config = ProvisionConfig(
                gpu_name=job_config.get("gpu_name"),
                max_price=job_config.get("max_price", 1.0),
                disk_space=job_config.get("disk_gb", 50),
                image=job_config.get("docker_image", "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"),
                onstart_cmd=self._build_onstart_script(job_config),
                label=f"job:{job_config.get('job_id', 'unknown')}",
                ports=[22],
                max_ssh_retries=3,
                ssh_command_timeout=20,
            )

            def progress_callback(status: str, message: str, progress: int):
                log("INFO", f"[{status}] {message}")

            result = provisioner.provision_with_failover(
                config=config,
                progress_callback=progress_callback,
            )

            if not result.success:
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    duration_seconds=time.time() - start_time,
                    error=result.error or "Falha ao provisionar GPU",
                )

            instance_id = result.instance_id
            ssh_host = result.ssh_host
            ssh_port = result.ssh_port
            gpu_name = result.gpu_name
            hourly_rate = result.dph_total

            log("INFO", f"GPU pronta: {gpu_name} ({ssh_host}:{ssh_port}) @ ${hourly_rate:.2f}/hr")

            # 2. Aguardar setup (se houver onstart)
            if job_config.get("setup_wait_seconds", 0) > 0:
                log("INFO", f"Aguardando setup ({job_config['setup_wait_seconds']}s)...")
                time.sleep(job_config["setup_wait_seconds"])

            # 2.5 Iniciar checkpoint sync (se habilitado)
            checkpoint_sync_enabled = False
            if job_config.get("checkpoint_sync", {}).get("enabled", False):
                sync_cfg = CheckpointSyncConfig(
                    enabled=True,
                    interval_minutes=job_config["checkpoint_sync"].get("interval_minutes", 5),
                    sync_path=job_config["checkpoint_sync"].get("sync_path", "/workspace/output"),
                    provider=job_config.get("storage_provider", "gcs"),
                )
                checkpoint_sync_enabled = self._start_checkpoint_sync(
                    ssh_host, ssh_port,
                    job_config.get("job_id", "unknown"),
                    job_config.get("user_id", "unknown"),
                    sync_cfg,
                    log,
                )

            # 3. Executar comando
            command = job_config.get("command")
            if command:
                log("INFO", f"Executando comando...")
                exec_start = time.time()

                exec_result = self._execute_ssh_command(
                    ssh_host,
                    ssh_port,
                    command,
                    timeout=job_config.get("timeout_seconds", self.execution_timeout),
                    env_vars=job_config.get("env_vars"),
                )

                exec_duration = time.time() - exec_start
                log("INFO", f"Execução concluída em {exec_duration:.1f}s")

                exit_code = exec_result.get("exit_code", -1)
                output = exec_result.get("stdout", "")
                error = exec_result.get("stderr", "")

                if exit_code != 0:
                    log("ERROR", f"Job falhou com exit code {exit_code}")
                else:
                    log("INFO", "Job concluído com sucesso")
            else:
                exit_code = 0
                output = ""
                error = ""

            # 4. Coletar output
            output_url = None
            storage_info = None

            # 4a. Upload automático de /workspace/output (se habilitado e StorageService disponível)
            if self.auto_upload_output and self.storage_service and exit_code == 0:
                log("INFO", "Verificando output em /workspace/output...")

                # Pegar configurações do job (ou usar defaults)
                expires_hours = job_config.get("output_expires_hours", self.output_expires_hours)
                storage_provider = job_config.get("storage_provider")  # None = usa default do service

                storage_info = self._auto_upload_output(
                    ssh_host, ssh_port,
                    job_config.get("user_id", "unknown"),
                    job_config.get("job_id", "unknown"),
                    log,
                    expires_hours=expires_hours,
                    storage_provider_override=storage_provider,
                )
                if storage_info:
                    output_url = storage_info.download_url
                    log("INFO", f"Output disponível por {expires_hours}h: {output_url}")

            # 4b. Coletar output para path customizado (legado)
            if job_config.get("output_path") and not storage_info:
                log("INFO", "Coletando output para path customizado...")
                output_url = self._collect_output(
                    ssh_host, ssh_port,
                    job_config["output_path"],
                )

            # 4c. Pegar status de checkpoint sync
            checkpoint_syncs = 0
            last_checkpoint_at = None
            if checkpoint_sync_enabled:
                sync_status = self._get_checkpoint_sync_status(ssh_host, ssh_port)
                checkpoint_syncs = sync_status.get("sync_count", 0)
                if checkpoint_syncs > 0:
                    last_checkpoint_at = datetime.now()
                    log("INFO", f"Checkpoint syncs realizados: {checkpoint_syncs}")

            # 5. Destruir instância
            log("INFO", "Destruindo instância...")
            self._destroy_instance(instance_id)

            # Calcular custo
            total_duration = time.time() - start_time
            cost = (total_duration / 3600) * hourly_rate

            return ExecutionResult(
                success=exit_code == 0,
                exit_code=exit_code,
                duration_seconds=total_duration,
                output=output,
                error=error if exit_code != 0 else None,
                output_url=output_url,
                cost_usd=cost,
                checkpoint_syncs=checkpoint_syncs,
                last_checkpoint_at=last_checkpoint_at,
                gpu_name=gpu_name,
                instance_id=instance_id,
                storage_info=storage_info,
            )

        except Exception as e:
            logger.exception(f"Erro executando job: {e}")

            # Garantir que a instância seja destruída
            if instance_id:
                try:
                    self._destroy_instance(instance_id)
                except:
                    pass

            return ExecutionResult(
                success=False,
                exit_code=-1,
                duration_seconds=time.time() - start_time,
                error=str(e),
                instance_id=instance_id,
            )

    def _build_onstart_script(self, job_config: Dict[str, Any]) -> Optional[str]:
        """Constrói script de inicialização"""
        parts = ["#!/bin/bash", "set -e"]

        # Variáveis de ambiente
        env_vars = job_config.get("env_vars", {})
        for key, value in env_vars.items():
            parts.append(f'export {key}="{value}"')

        # Setup commands
        if job_config.get("setup_commands"):
            parts.extend(job_config["setup_commands"])

        # Download de dados de entrada
        if job_config.get("input_path"):
            input_path = job_config["input_path"]
            if input_path.startswith("s3://"):
                parts.append(f"aws s3 sync {input_path} /workspace/input")
            elif input_path.startswith("gs://"):
                parts.append(f"gsutil -m cp -r {input_path} /workspace/input")
            elif input_path.startswith("http"):
                parts.append(f"wget -P /workspace/input {input_path}")

        if len(parts) > 2:
            return "\n".join(parts)
        return None

    def _execute_ssh_command(
        self,
        host: str,
        port: int,
        command: str,
        timeout: int = 3600,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Executa comando via SSH"""
        import os

        # Construir comando com variáveis de ambiente
        full_command = command
        if env_vars:
            env_exports = " ".join([f'{k}="{v}"' for k, v in env_vars.items()])
            full_command = f"{env_exports} {command}"

        ssh_key = os.path.expanduser(self.ssh_key_path)

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-i", ssh_key,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=30",
                    "-p", str(port),
                    f"root@{host}",
                    full_command,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Timeout expired",
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }

    def _auto_upload_output(
        self,
        host: str,
        port: int,
        user_id: str,
        job_id: str,
        log: Callable[[str, str], None],
        expires_hours: int = 24,
        storage_provider_override: Optional[str] = None,
    ) -> Optional[StorageInfo]:
        """
        Faz upload automático do /workspace/output para o Storage.

        Verifica se existe conteúdo em /workspace/output e faz upload
        usando o StorageService (GCS por padrão, ou B2 se especificado).

        Args:
            host: SSH host da GPU
            port: SSH port
            user_id: ID do usuário
            job_id: ID do job
            log: Callback de log
            expires_hours: Horas até expirar (default: 24)
            storage_provider_override: "gcs" ou "b2" para override
        """
        try:
            # Verificar se /workspace/output existe e tem conteúdo
            check_cmd = "test -d /workspace/output && ls -A /workspace/output | head -1"
            result = self._execute_ssh_command(host, port, check_cmd, timeout=30)

            if result["exit_code"] != 0 or not result["stdout"].strip():
                log("INFO", "Nenhum output encontrado em /workspace/output")
                return None

            # Determinar provider
            provider = storage_provider_override or self.storage_service.config.provider.value
            log("INFO", f"Output encontrado, fazendo upload para {provider.upper()}...")

            # Se tiver override, criar service temporário com outro provider
            service = self.storage_service
            if storage_provider_override and storage_provider_override != self.storage_service.config.provider.value:
                from src.modules.storage import StorageService, StorageConfig, StorageProviderType
                import os

                if storage_provider_override == "b2":
                    config = StorageConfig(
                        provider=StorageProviderType.BACKBLAZE_B2,
                        bucket=os.environ.get("B2_BUCKET", "dumontcloud-snapshots"),
                        endpoint=os.environ.get("B2_ENDPOINT", "https://s3.eu-central-003.backblazeb2.com"),
                        access_key=os.environ.get("B2_KEY_ID", ""),
                        secret_key=os.environ.get("B2_APPLICATION_KEY", ""),
                    )
                    service = StorageService(self.storage_service.session_factory, config)
                    log("INFO", "Usando B2 (override)")

            # Upload remoto
            upload_result = service.upload_from_remote(
                user_id=user_id,
                ssh_host=host,
                ssh_port=port,
                remote_path="/workspace/output",
                name=f"job_{job_id}_output",
                source_type="job",
                source_id=job_id,
                expires_hours=expires_hours,
                ssh_key_path=self.ssh_key_path,
            )

            if not upload_result.success:
                log("WARNING", f"Falha no upload do output: {upload_result.error}")
                return None

            log("INFO", f"Upload concluído: {upload_result.size_bytes} bytes para {provider.upper()}")

            return StorageInfo(
                file_key=upload_result.file_key,
                download_url=upload_result.download_url,
                size_bytes=upload_result.size_bytes,
                file_count=upload_result.file_count or 1,
                expires_at=upload_result.expires_at,
            )

        except Exception as e:
            log("WARNING", f"Erro no upload automático: {e}")
            logger.exception(f"Erro no upload automático de output: {e}")
            return None

    def _collect_output(
        self,
        host: str,
        port: int,
        output_path: str,
    ) -> Optional[str]:
        """Coleta output do job (upload para S3/GCS se necessário) - LEGADO"""
        try:
            if output_path.startswith("s3://"):
                # Fazer upload para S3
                self._execute_ssh_command(
                    host, port,
                    f"aws s3 sync /workspace/output {output_path}",
                    timeout=600,
                )
                return output_path
            elif output_path.startswith("gs://"):
                # Fazer upload para GCS
                self._execute_ssh_command(
                    host, port,
                    f"gsutil -m cp -r /workspace/output/* {output_path}",
                    timeout=600,
                )
                return output_path
            else:
                # Caminho local - não faz nada
                return output_path
        except Exception as e:
            logger.error(f"Erro coletando output: {e}")
            return None

    def _destroy_instance(self, instance_id: int):
        """Destrói instância VAST.ai"""
        try:
            self.vast_service.destroy_instance(instance_id)
            logger.info(f"Instância {instance_id} destruída")
        except Exception as e:
            logger.error(f"Erro destruindo instância {instance_id}: {e}")

    # ==================== Checkpoint Sync ====================

    def _generate_checkpoint_sync_script(
        self,
        job_id: str,
        user_id: str,
        sync_config: CheckpointSyncConfig,
    ) -> str:
        """
        Gera script que roda em background na GPU fazendo sync periódico.

        O script:
        1. Configura credenciais (GCS ou B2)
        2. Instala gsutil ou s5cmd
        3. Loop infinito: sync → sleep → repeat
        4. Salva log de cada sync
        """
        import os

        if sync_config.provider == "gcs":
            bucket = os.environ.get("GCS_BUCKET", "dumont-jobs-output")
            sync_cmd = f"gsutil -m rsync -r {sync_config.sync_path}/ gs://{bucket}/checkpoints/{user_id}/{job_id}/"

            # Ler credenciais GCS
            gcs_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
            creds_content = ""
            if gcs_credentials and os.path.exists(gcs_credentials):
                try:
                    with open(gcs_credentials, "r") as f:
                        creds_content = f.read().replace("'", "'\\''")
                except Exception as e:
                    logger.warning(f"Não foi possível ler credenciais GCS: {e}")

            if creds_content:
                # Com credenciais
                install_cmd = f'''
# Criar arquivo de credenciais GCS
cat > /tmp/gcs-credentials.json << 'GCSEOF'
{creds_content}
GCSEOF

# Criar arquivo de configuração boto para gsutil
cat > /root/.boto << 'BOTOEOF'
[Credentials]
gs_service_key_file = /tmp/gcs-credentials.json

[GSUtil]
parallel_composite_upload_threshold = 150M
BOTOEOF

# Instalar gsutil se não existir
if ! command -v gsutil &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq python3-pip > /dev/null 2>&1 || true
    pip3 install -q gsutil 2>/dev/null || true
fi
'''
            else:
                # Sem credenciais (tenta default)
                install_cmd = '''
if ! command -v gsutil &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq python3-pip > /dev/null 2>&1 || true
    pip3 install -q gsutil 2>/dev/null || true
fi
'''
        else:  # b2
            bucket = os.environ.get("B2_BUCKET", "dumontcloud-snapshots")
            endpoint = os.environ.get("B2_ENDPOINT", "https://s3.eu-central-003.backblazeb2.com")
            key_id = os.environ.get("B2_KEY_ID", "")
            app_key = os.environ.get("B2_APPLICATION_KEY", "")
            sync_cmd = f"s5cmd sync {sync_config.sync_path}/ s3://{bucket}/checkpoints/{user_id}/{job_id}/"
            install_cmd = f'''
which s5cmd || curl -sL https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz | tar -xz -C /usr/local/bin/
export AWS_ACCESS_KEY_ID="{key_id}"
export AWS_SECRET_ACCESS_KEY="{app_key}"
export S3_ENDPOINT_URL="{endpoint}"
'''

        script = f'''#!/bin/bash
# Dumont Cloud - Checkpoint Sync Service
# Job: {job_id} | User: {user_id}
# Sync every {sync_config.interval_minutes} minutes to {sync_config.provider.upper()}

LOG_FILE="/var/log/dumont_checkpoint_sync.log"
SYNC_PATH="{sync_config.sync_path}"
INTERVAL={sync_config.interval_minutes * 60}

echo "[$(date)] Checkpoint sync iniciado" | tee -a $LOG_FILE

# Configurar e instalar ferramenta de sync
{install_cmd}

# Loop de sync
sync_count=0
while true; do
    # Verificar se há arquivos para sync
    if [ -d "$SYNC_PATH" ] && [ "$(ls -A $SYNC_PATH 2>/dev/null)" ]; then
        echo "[$(date)] Iniciando sync #$((sync_count+1))..." | tee -a $LOG_FILE

        {sync_cmd} 2>&1 | tee -a $LOG_FILE

        if [ $? -eq 0 ]; then
            sync_count=$((sync_count+1))
            echo "[$(date)] Sync #$sync_count concluído com sucesso" | tee -a $LOG_FILE
        else
            echo "[$(date)] Erro no sync" | tee -a $LOG_FILE
        fi
    else
        echo "[$(date)] Aguardando arquivos em $SYNC_PATH..." | tee -a $LOG_FILE
    fi

    sleep $INTERVAL
done
'''
        return script

    def _start_checkpoint_sync(
        self,
        host: str,
        port: int,
        job_id: str,
        user_id: str,
        sync_config: CheckpointSyncConfig,
        log: Callable[[str, str], None],
    ) -> bool:
        """Inicia o serviço de checkpoint sync na GPU"""
        try:
            script = self._generate_checkpoint_sync_script(job_id, user_id, sync_config)

            # Criar script na GPU
            create_script = f'''
cat > /tmp/checkpoint_sync.sh << 'SYNC_SCRIPT'
{script}
SYNC_SCRIPT
chmod +x /tmp/checkpoint_sync.sh
'''
            result = self._execute_ssh_command(host, port, create_script, timeout=30)
            if result["exit_code"] != 0:
                log("WARNING", f"Erro criando script de sync: {result['stderr']}")
                return False

            # Iniciar em background
            start_cmd = "nohup /tmp/checkpoint_sync.sh > /dev/null 2>&1 &"
            result = self._execute_ssh_command(host, port, start_cmd, timeout=10)

            if result["exit_code"] == 0:
                log("INFO", f"Checkpoint sync iniciado (a cada {sync_config.interval_minutes} min)")
                return True
            else:
                log("WARNING", f"Erro iniciando checkpoint sync: {result['stderr']}")
                return False

        except Exception as e:
            log("WARNING", f"Erro no checkpoint sync: {e}")
            return False

    def _get_checkpoint_sync_status(
        self,
        host: str,
        port: int,
    ) -> Dict[str, Any]:
        """Retorna status do checkpoint sync"""
        try:
            cmd = "tail -5 /var/log/dumont_checkpoint_sync.log 2>/dev/null || echo 'No sync log'"
            result = self._execute_ssh_command(host, port, cmd, timeout=10)

            # Contar syncs
            count_cmd = "grep -c 'concluído com sucesso' /var/log/dumont_checkpoint_sync.log 2>/dev/null || echo 0"
            count_result = self._execute_ssh_command(host, port, count_cmd, timeout=10)

            return {
                "log": result["stdout"],
                "sync_count": int(count_result["stdout"].strip()) if count_result["exit_code"] == 0 else 0,
            }
        except:
            return {"log": "", "sync_count": 0}


class FineTuneExecutor(JobExecutor):
    """
    Executor especializado para jobs de fine-tuning.

    Adiciona:
    - Download automático de modelo base
    - Upload de modelo treinado
    - Métricas de treinamento
    """

    def build_finetune_config(
        self,
        base_model: str,
        dataset_path: str,
        output_path: str,
        num_epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 2e-5,
        lora_r: int = 8,
        lora_alpha: int = 16,
        extra_args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Constrói configuração para fine-tuning"""

        # Script de fine-tuning
        finetune_script = f'''
pip install -q transformers peft datasets accelerate bitsandbytes

python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
from datasets import load_dataset

# Carregar modelo
model = AutoModelForCausalLM.from_pretrained('{base_model}', load_in_8bit=True)
tokenizer = AutoTokenizer.from_pretrained('{base_model}')

# LoRA config
lora_config = LoraConfig(
    r={lora_r},
    lora_alpha={lora_alpha},
    target_modules=['q_proj', 'v_proj'],
    lora_dropout=0.05,
    bias='none',
)
model = get_peft_model(model, lora_config)

# Dataset
dataset = load_dataset('json', data_files='/workspace/input/train.json')

# Training
training_args = TrainingArguments(
    output_dir='/workspace/output',
    num_train_epochs={num_epochs},
    per_device_train_batch_size={batch_size},
    learning_rate={learning_rate},
    save_strategy='epoch',
    logging_steps=10,
)

from transformers import Trainer
trainer = Trainer(model=model, args=training_args, train_dataset=dataset['train'])
trainer.train()
trainer.save_model('/workspace/output/final')
"
'''

        return {
            "docker_image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
            "command": finetune_script,
            "input_path": dataset_path,
            "output_path": output_path,
            "gpu_name": "RTX 4090",  # Bom para fine-tuning
            "max_price": 0.50,
            "disk_gb": 100,
            "timeout_seconds": 14400,  # 4 horas
            "setup_wait_seconds": 30,
            **(extra_args or {}),
        }
