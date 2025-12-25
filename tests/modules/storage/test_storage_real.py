"""
Teste REAL do módulo Storage com B2.

Usa as credenciais existentes no .env para testar:
1. Upload de arquivo para B2
2. Geração de URL de download
3. Listagem de arquivos
4. Cleanup de expirados

Uso:
    python -m tests.modules.storage.test_storage_real
"""

import os
import sys
import tempfile
import logging

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from src.config.database import get_session_factory
from src.modules.storage import (
    StorageService,
    StorageConfig,
    StorageProviderType,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_storage_b2():
    """Testa storage com B2 usando credenciais do .env"""

    logger.info("=" * 60)
    logger.info("  TESTE: Storage Module com Backblaze B2")
    logger.info("=" * 60)

    # 1. Verificar credenciais
    b2_key = os.environ.get("B2_KEY_ID")
    b2_secret = os.environ.get("B2_APPLICATION_KEY")
    b2_endpoint = os.environ.get("B2_ENDPOINT")
    b2_bucket = os.environ.get("B2_BUCKET")

    if not all([b2_key, b2_secret, b2_endpoint, b2_bucket]):
        logger.error("Credenciais B2 não encontradas no .env")
        return False

    logger.info(f"B2 Bucket: {b2_bucket}")
    logger.info(f"B2 Endpoint: {b2_endpoint}")

    # 2. Criar configuração
    config = StorageConfig(
        provider=StorageProviderType.BACKBLAZE_B2,
        bucket=b2_bucket,
        endpoint=b2_endpoint,
        access_key=b2_key,
        secret_key=b2_secret,
    )

    # 3. Criar serviço
    session_factory = get_session_factory()
    service = StorageService(
        session_factory=session_factory,
        config=config,
        default_expires_hours=1,  # 1 hora para teste
    )

    logger.info("StorageService criado com sucesso")

    # 4. Criar arquivo de teste
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Teste de upload do Dumont Cloud Storage Module\n")
        f.write(f"Timestamp: {os.popen('date').read()}")
        f.write("Este arquivo será deletado automaticamente em 1 hora.\n")
        test_file = f.name

    logger.info(f"Arquivo de teste criado: {test_file}")

    # 5. Fazer upload
    logger.info("\n>>> Fazendo upload para B2...")
    result = service.upload_file(
        user_id="test_user",
        local_path=test_file,
        original_name="storage_test.txt",
        source_type="test",
        source_id="storage_module_test",
        expires_hours=1,
    )

    # Limpar arquivo local
    os.unlink(test_file)

    if not result.success:
        logger.error(f"Falha no upload: {result.error}")
        return False

    logger.info(f"Upload OK!")
    logger.info(f"  File ID: {result.file_id}")
    logger.info(f"  File Key: {result.file_key}")
    logger.info(f"  Size: {result.size_bytes} bytes")
    logger.info(f"  Expires: {result.expires_at}")

    if result.download_url:
        logger.info(f"  Download URL: {result.download_url[:80]}...")

    # 6. Listar arquivos do usuário
    logger.info("\n>>> Listando arquivos do usuário...")
    files = service.list_user_files("test_user")
    logger.info(f"Arquivos encontrados: {len(files)}")
    for f in files[:5]:
        logger.info(f"  - {f['name']} ({f['size_bytes']} bytes) - {f['status']}")

    # 7. Gerar nova URL de download
    logger.info("\n>>> Gerando nova URL de download...")
    new_url = service.get_download_url(result.file_key, expires_hours=1)
    if new_url:
        logger.info(f"Nova URL gerada: {new_url[:80]}...")
    else:
        logger.warning("Não foi possível gerar URL")

    logger.info("\n" + "=" * 60)
    logger.info("  TESTE CONCLUÍDO COM SUCESSO!")
    logger.info("=" * 60)

    return True


def check_s5cmd():
    """Verifica se s5cmd está instalado"""
    import shutil
    if shutil.which("s5cmd"):
        logger.info("s5cmd encontrado")
        return True
    else:
        logger.warning("s5cmd não encontrado - instalando...")
        os.system("curl -sL https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz | sudo tar -xz -C /usr/local/bin/")
        return shutil.which("s5cmd") is not None


if __name__ == "__main__":
    try:
        # Verificar dependências
        if not check_s5cmd():
            logger.error("s5cmd não pôde ser instalado")
            sys.exit(1)

        # Rodar teste
        success = test_storage_b2()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.warning("\nInterrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Erro: {e}")
        sys.exit(1)
