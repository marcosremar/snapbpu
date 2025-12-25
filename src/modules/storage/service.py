"""
Storage Module - Service

Serviço principal para gerenciamento de storage:
- Upload de arquivos/diretórios para GCS (padrão) ou B2
- Download via URLs temporárias (signed URLs)
- Cleanup automático de arquivos expirados (24h)
- Integração com Jobs - upload automático de /workspace/output

Fluxo do Job:
1. Job executa na GPU
2. Job termina (sucesso)
3. StorageService copia /workspace/output para GCS/B2
4. GPU é destruída
5. URL de download fica disponível por 24h
"""

import os
import logging
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Tuple
from contextlib import contextmanager
from dataclasses import dataclass

from .models import StoredFile, StoredDirectory, FileStatus, StorageProviderType
from .repository import StorageRepository

logger = logging.getLogger(__name__)

# GCS client (lazy loading)
_gcs_client = None


def _get_gcs_client():
    """Retorna cliente GCS (lazy loading)"""
    global _gcs_client
    if _gcs_client is None:
        try:
            from google.cloud import storage
            _gcs_client = storage.Client()
            logger.info("GCS client inicializado")
        except ImportError:
            raise ImportError("google-cloud-storage não instalado. Rode: pip install google-cloud-storage")
    return _gcs_client


@dataclass
class UploadResult:
    """Resultado de um upload"""
    success: bool
    file_id: Optional[int] = None
    dir_id: Optional[int] = None
    file_key: Optional[str] = None
    download_url: Optional[str] = None
    size_bytes: int = 0
    file_count: int = 0
    error: Optional[str] = None
    expires_at: Optional[datetime] = None


@dataclass
class StorageConfig:
    """Configuração do storage"""
    provider: StorageProviderType
    bucket: str
    endpoint: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: str = "auto"


class StorageService:
    """
    Serviço de gerenciamento de storage.

    Responsabilidades:
    - Upload de arquivos para cloud storage
    - Geração de URLs temporárias para download
    - Cleanup automático de arquivos expirados
    - Rastreamento de arquivos no banco de dados
    """

    def __init__(
        self,
        session_factory: Callable,
        config: Optional[StorageConfig] = None,
        default_expires_hours: int = 24,
        cleanup_interval_minutes: int = 60,
        auto_start_cleanup: bool = False,
    ):
        """
        Args:
            session_factory: Factory para criar sessões do banco
            config: Configuração do storage (ou usa variáveis de ambiente)
            default_expires_hours: Horas até expiração padrão
            cleanup_interval_minutes: Intervalo de cleanup em minutos
            auto_start_cleanup: Se True, inicia worker de cleanup
        """
        self.session_factory = session_factory
        self.config = config or self._load_config_from_env()
        self.default_expires_hours = default_expires_hours
        self.cleanup_interval = cleanup_interval_minutes * 60

        # Cleanup worker
        self._running = False
        self._cleanup_thread: Optional[threading.Thread] = None

        if auto_start_cleanup:
            self.start_cleanup_worker()

    def _load_config_from_env(self) -> StorageConfig:
        """Carrega configuração do ambiente (B2 ou GCS)"""
        provider_name = os.environ.get("STORAGE_PROVIDER", "b2").lower()

        provider_map = {
            "b2": StorageProviderType.BACKBLAZE_B2,
            "gcs": StorageProviderType.gcs,
        }

        provider = provider_map.get(provider_name, StorageProviderType.BACKBLAZE_B2)

        # Carregar credenciais baseado no provider
        if provider == StorageProviderType.BACKBLAZE_B2:
            return StorageConfig(
                provider=provider,
                bucket=os.environ.get("B2_BUCKET", "dumontcloud-snapshots"),
                endpoint=os.environ.get("B2_ENDPOINT", "https://s3.eu-central-003.backblazeb2.com"),
                access_key=os.environ.get("B2_KEY_ID", ""),
                secret_key=os.environ.get("B2_APPLICATION_KEY", ""),
            )
        elif provider == StorageProviderType.gcs:
            # GCS usa credenciais de service account
            return StorageConfig(
                provider=provider,
                bucket=os.environ.get("GCS_BUCKET", "dumont-storage"),
                endpoint="https://storage.googleapis.com",
                # GCS usa GOOGLE_APPLICATION_CREDENTIALS para autenticação
            )
        else:
            # Fallback para B2
            return StorageConfig(
                provider=StorageProviderType.BACKBLAZE_B2,
                bucket=os.environ.get("B2_BUCKET", "dumontcloud-snapshots"),
                endpoint=os.environ.get("B2_ENDPOINT", "https://s3.eu-central-003.backblazeb2.com"),
                access_key=os.environ.get("B2_KEY_ID", ""),
                secret_key=os.environ.get("B2_APPLICATION_KEY", ""),
            )

    @contextmanager
    def _get_session(self):
        """Context manager para sessão do banco"""
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def _generate_file_key(self, user_id: str, filename: str) -> str:
        """Gera chave única para arquivo"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in filename)
        return f"{user_id}/{timestamp}_{unique_id}_{safe_name}"

    def _generate_dir_key(self, user_id: str, name: str) -> str:
        """Gera chave única para diretório"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"{user_id}/dirs/{timestamp}_{unique_id}_{name}"

    def _get_s3_url(self) -> str:
        """Retorna URL S3 do bucket (para B2)"""
        return f"s3://{self.config.bucket}"

    def _get_env_for_s5cmd(self) -> Dict[str, str]:
        """Retorna variáveis de ambiente para s5cmd (B2)"""
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = self.config.access_key or ""
        env["AWS_SECRET_ACCESS_KEY"] = self.config.secret_key or ""
        if self.config.endpoint:
            env["S3_ENDPOINT_URL"] = self.config.endpoint
        return env

    # ==================== Upload Helpers ====================

    def _upload_file_gcs(self, local_path: str, remote_key: str) -> bool:
        """Upload arquivo para GCS usando SDK nativo"""
        try:
            client = _get_gcs_client()
            bucket = client.bucket(self.config.bucket)
            blob = bucket.blob(remote_key)
            blob.upload_from_filename(local_path)
            logger.info(f"GCS upload: {remote_key}")
            return True
        except Exception as e:
            logger.error(f"Erro upload GCS: {e}")
            return False

    def _upload_dir_gcs(self, local_dir: str, remote_prefix: str) -> bool:
        """Upload diretório para GCS"""
        try:
            client = _get_gcs_client()
            bucket = client.bucket(self.config.bucket)

            for root, _, files in os.walk(local_dir):
                for filename in files:
                    local_file = os.path.join(root, filename)
                    relative_path = os.path.relpath(local_file, local_dir)
                    remote_key = f"{remote_prefix}/{relative_path}"

                    blob = bucket.blob(remote_key)
                    blob.upload_from_filename(local_file)

            logger.info(f"GCS upload dir: {remote_prefix}")
            return True
        except Exception as e:
            logger.error(f"Erro upload dir GCS: {e}")
            return False

    def _upload_file_b2(self, local_path: str, remote_key: str) -> bool:
        """Upload arquivo para B2 usando s5cmd"""
        try:
            s3_path = f"{self._get_s3_url()}/{remote_key}"
            result = subprocess.run(
                ["s5cmd", "cp", local_path, s3_path],
                capture_output=True,
                text=True,
                env=self._get_env_for_s5cmd(),
                timeout=300,
            )
            if result.returncode != 0:
                logger.error(f"B2 upload error: {result.stderr}")
                return False
            logger.info(f"B2 upload: {remote_key}")
            return True
        except Exception as e:
            logger.error(f"Erro upload B2: {e}")
            return False

    def _upload_dir_b2(self, local_dir: str, remote_prefix: str) -> bool:
        """Upload diretório para B2 usando s5cmd sync"""
        try:
            s3_path = f"{self._get_s3_url()}/{remote_prefix}/"
            result = subprocess.run(
                ["s5cmd", "sync", f"{local_dir}/", s3_path],
                capture_output=True,
                text=True,
                env=self._get_env_for_s5cmd(),
                timeout=600,
            )
            if result.returncode != 0:
                logger.error(f"B2 sync error: {result.stderr}")
                return False
            logger.info(f"B2 sync dir: {remote_prefix}")
            return True
        except Exception as e:
            logger.error(f"Erro sync B2: {e}")
            return False

    def _do_upload_file(self, local_path: str, remote_key: str) -> bool:
        """Upload arquivo para o provider configurado"""
        if self.config.provider == StorageProviderType.gcs:
            return self._upload_file_gcs(local_path, remote_key)
        else:  # B2 ou fallback
            return self._upload_file_b2(local_path, remote_key)

    def _do_upload_dir(self, local_dir: str, remote_prefix: str) -> bool:
        """Upload diretório para o provider configurado"""
        if self.config.provider == StorageProviderType.gcs:
            return self._upload_dir_gcs(local_dir, remote_prefix)
        else:  # B2 ou fallback
            return self._upload_dir_b2(local_dir, remote_prefix)

    # ==================== Upload ====================

    def upload_file(
        self,
        user_id: str,
        local_path: str,
        original_name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        expires_hours: Optional[int] = None,
    ) -> UploadResult:
        """
        Faz upload de um arquivo para o storage.

        Args:
            user_id: ID do usuário
            local_path: Caminho local do arquivo
            original_name: Nome original (usa basename se não fornecido)
            source_type: Tipo de fonte ("job", "upload", etc)
            source_id: ID da fonte
            expires_hours: Horas até expirar (padrão: 24)

        Returns:
            UploadResult com informações do upload
        """
        if not os.path.exists(local_path):
            return UploadResult(success=False, error=f"Arquivo não encontrado: {local_path}")

        if not original_name:
            original_name = os.path.basename(local_path)

        file_key = self._generate_file_key(user_id, original_name)
        expires = expires_hours or self.default_expires_hours

        try:
            # Criar registro no banco
            with self._get_session() as session:
                repo = StorageRepository(session)
                file_record = repo.create_file(
                    user_id=user_id,
                    file_key=file_key,
                    provider=self.config.provider,
                    bucket=self.config.bucket,
                    path=file_key,
                    original_name=original_name,
                    source_type=source_type,
                    source_id=source_id,
                    size_bytes=os.path.getsize(local_path),
                    expires_hours=expires,
                )
                file_id = file_record.id
                expires_at = file_record.expires_at

            # Fazer upload (GCS ou B2)
            if not self._do_upload_file(local_path, file_key):
                with self._get_session() as session:
                    repo = StorageRepository(session)
                    repo.update_file_status(file_id, FileStatus.FAILED)
                return UploadResult(
                    success=False,
                    error=f"Falha no upload para {self.config.provider.value}",
                )

            # Gerar URL de download
            download_url = self._generate_presigned_url(file_key, expires)

            # Atualizar status
            with self._get_session() as session:
                repo = StorageRepository(session)
                repo.update_file_status(
                    file_id,
                    FileStatus.AVAILABLE,
                    download_url=download_url,
                    url_expires_at=expires_at,
                )

            logger.info(f"Arquivo uploadado: {file_key} ({os.path.getsize(local_path)} bytes)")

            return UploadResult(
                success=True,
                file_id=file_id,
                file_key=file_key,
                download_url=download_url,
                size_bytes=os.path.getsize(local_path),
                expires_at=expires_at,
            )

        except Exception as e:
            logger.exception(f"Erro no upload: {e}")
            return UploadResult(success=False, error=str(e))

    def upload_directory(
        self,
        user_id: str,
        local_dir: str,
        name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        expires_hours: Optional[int] = None,
    ) -> UploadResult:
        """
        Faz upload de um diretório inteiro para o storage.

        Args:
            user_id: ID do usuário
            local_dir: Caminho do diretório local
            name: Nome do diretório (usa basename se não fornecido)
            source_type: Tipo de fonte
            source_id: ID da fonte
            expires_hours: Horas até expirar

        Returns:
            UploadResult com informações do upload
        """
        if not os.path.isdir(local_dir):
            return UploadResult(success=False, error=f"Diretório não encontrado: {local_dir}")

        if not name:
            name = os.path.basename(local_dir.rstrip("/"))

        dir_key = self._generate_dir_key(user_id, name)
        expires = expires_hours or self.default_expires_hours

        try:
            # Calcular tamanho total e contagem de arquivos
            total_size = 0
            file_count = 0
            for root, _, files in os.walk(local_dir):
                for f in files:
                    filepath = os.path.join(root, f)
                    total_size += os.path.getsize(filepath)
                    file_count += 1

            if file_count == 0:
                return UploadResult(success=False, error="Diretório vazio")

            # Criar registro no banco
            with self._get_session() as session:
                repo = StorageRepository(session)
                dir_record = repo.create_directory(
                    user_id=user_id,
                    dir_key=dir_key,
                    provider=self.config.provider,
                    bucket=self.config.bucket,
                    prefix=dir_key,
                    name=name,
                    source_type=source_type,
                    source_id=source_id,
                    expires_hours=expires,
                )
                dir_id = dir_record.id
                expires_at = dir_record.expires_at

            # Fazer upload (GCS ou B2)
            if not self._do_upload_dir(local_dir, dir_key):
                with self._get_session() as session:
                    repo = StorageRepository(session)
                    repo.update_directory_status(dir_id, FileStatus.FAILED)
                return UploadResult(
                    success=False,
                    error=f"Falha no upload para {self.config.provider.value}",
                )

            # Gerar URL base
            download_url = self._generate_presigned_url(dir_key, expires, is_prefix=True)

            # Atualizar status
            with self._get_session() as session:
                repo = StorageRepository(session)
                repo.update_directory_status(
                    dir_id,
                    FileStatus.AVAILABLE,
                    total_size_bytes=total_size,
                    file_count=file_count,
                )

            logger.info(f"Diretório uploadado: {dir_key} ({file_count} arquivos, {total_size} bytes)")

            return UploadResult(
                success=True,
                dir_id=dir_id,
                file_key=dir_key,
                download_url=download_url,
                size_bytes=total_size,
                file_count=file_count,
                expires_at=expires_at,
            )

        except Exception as e:
            logger.exception(f"Erro no upload de diretório: {e}")
            return UploadResult(success=False, error=str(e))

    def upload_from_remote(
        self,
        user_id: str,
        ssh_host: str,
        ssh_port: int,
        remote_path: str,
        name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        expires_hours: Optional[int] = None,
        ssh_key_path: str = "~/.ssh/id_ed25519",
    ) -> UploadResult:
        """
        Faz upload de arquivos diretamente de uma máquina remota via SSH.

        Ideal para coletar outputs de jobs sem baixar localmente primeiro.
        """
        if not name:
            name = os.path.basename(remote_path.rstrip("/"))

        dir_key = self._generate_dir_key(user_id, name)
        expires = expires_hours or self.default_expires_hours
        ssh_key = os.path.expanduser(ssh_key_path)

        try:
            # Verificar se é arquivo ou diretório
            check_cmd = f"test -d {remote_path} && echo 'dir' || echo 'file'"
            check_result = subprocess.run(
                [
                    "ssh", "-i", ssh_key,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    check_cmd,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            is_directory = "dir" in check_result.stdout

            # Criar registro no banco
            with self._get_session() as session:
                repo = StorageRepository(session)
                if is_directory:
                    record = repo.create_directory(
                        user_id=user_id,
                        dir_key=dir_key,
                        provider=self.config.provider,
                        bucket=self.config.bucket,
                        prefix=dir_key,
                        name=name,
                        source_type=source_type,
                        source_id=source_id,
                        expires_hours=expires,
                    )
                    record_id = record.id
                    expires_at = record.expires_at
                else:
                    record = repo.create_file(
                        user_id=user_id,
                        file_key=dir_key,
                        provider=self.config.provider,
                        bucket=self.config.bucket,
                        path=dir_key,
                        original_name=name,
                        source_type=source_type,
                        source_id=source_id,
                        expires_hours=expires,
                    )
                    record_id = record.id
                    expires_at = record.expires_at

            # Gerar script de upload baseado no provider
            if self.config.provider == StorageProviderType.gcs:
                upload_script = self._generate_gcs_upload_script(
                    remote_path, dir_key, ssh_host, ssh_port, ssh_key
                )
            else:
                # S3/B2 - usar s5cmd
                s3_path = f"{self._get_s3_url()}/{dir_key}"
                upload_script = f'''
set -e

# Instalar s5cmd se não existir
if ! command -v s5cmd &> /dev/null; then
    curl -sL https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz | tar -xz -C /usr/local/bin/
fi

# Configurar credenciais
export AWS_ACCESS_KEY_ID="{self.config.access_key}"
export AWS_SECRET_ACCESS_KEY="{self.config.secret_key}"
export S3_ENDPOINT_URL="{self.config.endpoint or ''}"

# Upload
if [ -d "{remote_path}" ]; then
    s5cmd sync "{remote_path}/" "{s3_path}/"
    du -sb "{remote_path}" | cut -f1
else
    s5cmd cp "{remote_path}" "{s3_path}"
    stat -c%s "{remote_path}"
fi
'''

            result = subprocess.run(
                [
                    "ssh", "-i", ssh_key,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    upload_script,
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                with self._get_session() as session:
                    repo = StorageRepository(session)
                    if is_directory:
                        repo.update_directory_status(record_id, FileStatus.FAILED)
                    else:
                        repo.update_file_status(record_id, FileStatus.FAILED)
                return UploadResult(
                    success=False,
                    error=f"Falha no upload remoto: {result.stderr}",
                )

            # Parse tamanho do output
            try:
                total_size = int(result.stdout.strip().split('\n')[-1])
            except:
                total_size = 0

            # Gerar URL
            download_url = self._generate_presigned_url(dir_key, expires)

            # Atualizar status
            with self._get_session() as session:
                repo = StorageRepository(session)
                if is_directory:
                    repo.update_directory_status(
                        record_id,
                        FileStatus.AVAILABLE,
                        total_size_bytes=total_size,
                    )
                else:
                    repo.update_file_status(
                        record_id,
                        FileStatus.AVAILABLE,
                        download_url=download_url,
                    )
                    repo.update_file_size(record_id, total_size)

            logger.info(f"Upload remoto concluído: {dir_key} ({total_size} bytes)")

            return UploadResult(
                success=True,
                file_id=record_id if not is_directory else None,
                dir_id=record_id if is_directory else None,
                file_key=dir_key,
                download_url=download_url,
                size_bytes=total_size,
                expires_at=expires_at,
            )

        except Exception as e:
            logger.exception(f"Erro no upload remoto: {e}")
            return UploadResult(success=False, error=str(e))

    def _generate_gcs_upload_script(
        self,
        remote_path: str,
        dir_key: str,
        ssh_host: str,
        ssh_port: int,
        ssh_key: str,
    ) -> str:
        """
        Gera script para upload remoto para GCS.

        O fluxo é:
        1. Copiar credenciais GCS para a GPU via SCP
        2. Ativar service account
        3. Usar gsutil para fazer upload
        """
        gcs_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        bucket = self.config.bucket

        # Ler conteúdo das credenciais se existir
        creds_content = ""
        if gcs_credentials and os.path.exists(gcs_credentials):
            try:
                with open(gcs_credentials, "r") as f:
                    creds_content = f.read().replace("'", "'\\''")  # Escape quotes
            except Exception as e:
                logger.warning(f"Não foi possível ler credenciais GCS: {e}")

        if creds_content:
            # Script com credenciais embutidas
            script = f'''
set -e

# Criar arquivo de credenciais GCS
mkdir -p /root/.config/gcloud
cat > /tmp/gcs-credentials.json << 'GCSEOF'
{creds_content}
GCSEOF

# Instalar gsutil se não existir
if ! command -v gsutil &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq python3-pip > /dev/null 2>&1 || true
    pip3 install -q google-cloud-storage gsutil 2>/dev/null || true
fi

# Criar arquivo de configuração boto para gsutil
cat > /root/.boto << 'BOTOEOF'
[Credentials]
gs_service_key_file = /tmp/gcs-credentials.json

[GSUtil]
parallel_composite_upload_threshold = 150M
BOTOEOF

# Upload
if [ -d "{remote_path}" ]; then
    gsutil -m rsync -r "{remote_path}/" "gs://{bucket}/{dir_key}/"
    du -sb "{remote_path}" | cut -f1
else
    gsutil cp "{remote_path}" "gs://{bucket}/{dir_key}"
    stat -c%s "{remote_path}"
fi

# Limpar credenciais
rm -f /tmp/gcs-credentials.json /root/.boto
'''
        else:
            # Sem credenciais - tentar usar default credentials (funciona em GCE)
            logger.warning("Credenciais GCS não encontradas, tentando default credentials")
            script = f'''
set -e

# Instalar gsutil se não existir
if ! command -v gsutil &> /dev/null; then
    apt-get update -qq && apt-get install -y -qq python3-pip > /dev/null 2>&1 || true
    pip3 install -q google-cloud-storage gsutil 2>/dev/null || true
fi

# Upload usando default credentials
if [ -d "{remote_path}" ]; then
    gsutil -m rsync -r "{remote_path}/" "gs://{bucket}/{dir_key}/"
    du -sb "{remote_path}" | cut -f1
else
    gsutil cp "{remote_path}" "gs://{bucket}/{dir_key}"
    stat -c%s "{remote_path}"
fi
'''
        return script

    def _generate_presigned_url(
        self,
        file_key: str,
        expires_hours: int = 24,
        is_prefix: bool = False,
    ) -> str:
        """Gera URL pré-assinada para download (GCS ou B2)"""

        # GCS: usar SDK nativo
        if self.config.provider == StorageProviderType.gcs:
            return self._generate_gcs_signed_url(file_key, expires_hours)

        # B2: usar boto3 S3-compatible
        return self._generate_b2_signed_url(file_key, expires_hours)

    def _generate_gcs_signed_url(self, file_key: str, expires_hours: int) -> str:
        """Gera signed URL para GCS"""
        try:
            client = _get_gcs_client()
            bucket = client.bucket(self.config.bucket)
            blob = bucket.blob(file_key)

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=expires_hours),
                method="GET",
            )
            return url

        except Exception as e:
            logger.warning(f"Erro gerando GCS signed URL: {e}")
            # Fallback: URL pública (se bucket for público)
            return f"https://storage.googleapis.com/{self.config.bucket}/{file_key}"

    def _generate_b2_signed_url(self, file_key: str, expires_hours: int) -> str:
        """Gera signed URL para B2 usando boto3"""
        try:
            import boto3
            from botocore.config import Config

            s3_client = boto3.client(
                's3',
                endpoint_url=self.config.endpoint,
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                config=Config(signature_version='s3v4'),
                region_name=self.config.region or 'auto',
            )

            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.config.bucket,
                    'Key': file_key,
                },
                ExpiresIn=expires_hours * 3600,
            )
            return url

        except ImportError:
            logger.warning("boto3 não instalado")
        except Exception as e:
            logger.warning(f"Erro gerando B2 signed URL: {e}")

        # Fallback
        return f"{self.config.endpoint}/{self.config.bucket}/{file_key}"

    # ==================== Download ====================

    def get_download_url(
        self,
        file_key: str,
        expires_hours: int = 1,
    ) -> Optional[str]:
        """Gera nova URL de download para um arquivo"""
        with self._get_session() as session:
            repo = StorageRepository(session)
            file = repo.get_file_by_key(file_key)

            if not file or file.status != FileStatus.AVAILABLE:
                return None

            if file.is_expired:
                return None

            return self._generate_presigned_url(file_key, expires_hours)

    def list_user_files(
        self,
        user_id: str,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """Lista arquivos de um usuário"""
        with self._get_session() as session:
            repo = StorageRepository(session)

            status = None if include_expired else FileStatus.AVAILABLE
            files = repo.get_files_by_user(user_id, status)
            directories = repo.get_directories_by_user(user_id, status)

            result = []

            for f in files:
                result.append({
                    "type": "file",
                    "id": f.id,
                    "key": f.file_key,
                    "name": f.original_name,
                    "size_bytes": f.size_bytes,
                    "size_mb": f.size_mb,
                    "status": f.status.value,
                    "expires_at": f.expires_at.isoformat() if f.expires_at else None,
                    "is_expired": f.is_expired,
                    "download_url": f.download_url,
                    "source_type": f.source_type,
                    "source_id": f.source_id,
                    "created_at": f.created_at.isoformat(),
                })

            for d in directories:
                result.append({
                    "type": "directory",
                    "id": d.id,
                    "key": d.dir_key,
                    "name": d.name,
                    "size_bytes": d.total_size_bytes,
                    "size_mb": d.total_size_bytes / (1024 * 1024),
                    "file_count": d.file_count,
                    "status": d.status.value,
                    "expires_at": d.expires_at.isoformat() if d.expires_at else None,
                    "is_expired": d.is_expired,
                    "source_type": d.source_type,
                    "source_id": d.source_id,
                    "created_at": d.created_at.isoformat(),
                })

            return sorted(result, key=lambda x: x["created_at"], reverse=True)

    # ==================== Cleanup ====================

    def cleanup_expired(self) -> Tuple[int, int]:
        """
        Remove arquivos expirados do storage e banco.

        Returns:
            Tuple (arquivos_deletados, bytes_liberados)
        """
        deleted_count = 0
        freed_bytes = 0

        with self._get_session() as session:
            repo = StorageRepository(session)

            # Arquivos expirados
            expired_files = repo.get_expired_files()
            for file in expired_files:
                try:
                    # Deletar do storage
                    s3_path = f"{self._get_s3_url()}/{file.path}"
                    subprocess.run(
                        ["s5cmd", "rm", s3_path],
                        capture_output=True,
                        env=self._get_env_for_s5cmd(),
                        timeout=60,
                    )

                    # Marcar como deletado
                    repo.delete_file(file.id)

                    deleted_count += 1
                    freed_bytes += file.size_bytes or 0

                    logger.info(f"Arquivo expirado deletado: {file.file_key}")
                except Exception as e:
                    logger.error(f"Erro deletando arquivo {file.file_key}: {e}")

            # Diretórios expirados
            expired_dirs = repo.get_expired_directories()
            for directory in expired_dirs:
                try:
                    # Deletar do storage (recursivo)
                    s3_path = f"{self._get_s3_url()}/{directory.prefix}/*"
                    subprocess.run(
                        ["s5cmd", "rm", s3_path],
                        capture_output=True,
                        env=self._get_env_for_s5cmd(),
                        timeout=120,
                    )

                    # Marcar como deletado
                    repo.update_directory_status(directory.id, FileStatus.DELETED)

                    deleted_count += directory.file_count or 1
                    freed_bytes += directory.total_size_bytes or 0

                    logger.info(f"Diretório expirado deletado: {directory.dir_key}")
                except Exception as e:
                    logger.error(f"Erro deletando diretório {directory.dir_key}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleanup: {deleted_count} itens deletados, {freed_bytes / 1024 / 1024:.1f} MB liberados")

        return deleted_count, freed_bytes

    def start_cleanup_worker(self):
        """Inicia worker de cleanup automático"""
        if self._running:
            return

        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="StorageCleanup",
        )
        self._cleanup_thread.start()
        logger.info("Storage cleanup worker iniciado")

    def stop_cleanup_worker(self):
        """Para worker de cleanup"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=10)
        logger.info("Storage cleanup worker parado")

    def _cleanup_loop(self):
        """Loop de cleanup"""
        while self._running:
            try:
                self.cleanup_expired()
            except Exception as e:
                logger.error(f"Erro no cleanup: {e}")

            time.sleep(self.cleanup_interval)


# Singleton global
_storage_service: Optional[StorageService] = None


def get_storage_service(
    session_factory=None,
    config: Optional[StorageConfig] = None,
    **kwargs,
) -> StorageService:
    """Retorna instância singleton do StorageService"""
    global _storage_service

    if _storage_service is None:
        if session_factory is None:
            raise ValueError("session_factory é obrigatório na primeira chamada")
        _storage_service = StorageService(session_factory, config, **kwargs)

    return _storage_service
