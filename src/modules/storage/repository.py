"""
Storage Module - Repository

Repositório para persistência de arquivos armazenados.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from .models import StoredFile, StoredDirectory, FileStatus, StorageProviderType

logger = logging.getLogger(__name__)


class StorageRepository:
    """Repositório para operações com arquivos armazenados"""

    def __init__(self, session: Session):
        self.session = session

    # ==================== StoredFile CRUD ====================

    def create_file(
        self,
        user_id: str,
        file_key: str,
        provider: StorageProviderType,
        bucket: str,
        path: str,
        original_name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        size_bytes: int = 0,
        content_type: Optional[str] = None,
        expires_hours: int = 24,
    ) -> StoredFile:
        """Cria registro de arquivo"""
        file = StoredFile(
            user_id=user_id,
            file_key=file_key,
            original_name=original_name,
            source_type=source_type,
            source_id=source_id,
            provider=provider,
            bucket=bucket,
            path=path,
            size_bytes=size_bytes,
            content_type=content_type,
            status=FileStatus.UPLOADING,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        )
        self.session.add(file)
        self.session.commit()
        logger.info(f"Created file record: {file_key}")
        return file

    def get_file(self, file_id: int) -> Optional[StoredFile]:
        """Busca arquivo por ID"""
        return self.session.query(StoredFile).filter(StoredFile.id == file_id).first()

    def get_file_by_key(self, file_key: str) -> Optional[StoredFile]:
        """Busca arquivo por chave"""
        return self.session.query(StoredFile).filter(StoredFile.file_key == file_key).first()

    def get_files_by_user(
        self,
        user_id: str,
        status: Optional[FileStatus] = None,
        limit: int = 50,
    ) -> List[StoredFile]:
        """Lista arquivos de um usuário"""
        query = self.session.query(StoredFile).filter(StoredFile.user_id == user_id)

        if status:
            query = query.filter(StoredFile.status == status)

        return query.order_by(desc(StoredFile.created_at)).limit(limit).all()

    def get_files_by_source(
        self,
        source_type: str,
        source_id: str,
    ) -> List[StoredFile]:
        """Busca arquivos por fonte (ex: job)"""
        return self.session.query(StoredFile).filter(
            StoredFile.source_type == source_type,
            StoredFile.source_id == source_id,
        ).all()

    def update_file_status(
        self,
        file_id: int,
        status: FileStatus,
        download_url: Optional[str] = None,
        url_expires_at: Optional[datetime] = None,
    ) -> Optional[StoredFile]:
        """Atualiza status do arquivo"""
        file = self.get_file(file_id)
        if not file:
            return None

        file.status = status

        if status == FileStatus.AVAILABLE:
            file.uploaded_at = datetime.utcnow()

        if status == FileStatus.DELETED:
            file.deleted_at = datetime.utcnow()

        if download_url:
            file.download_url = download_url
            file.url_expires_at = url_expires_at

        self.session.commit()
        return file

    def update_file_size(self, file_id: int, size_bytes: int) -> Optional[StoredFile]:
        """Atualiza tamanho do arquivo"""
        file = self.get_file(file_id)
        if not file:
            return None

        file.size_bytes = size_bytes
        self.session.commit()
        return file

    def get_expired_files(self, limit: int = 100) -> List[StoredFile]:
        """Busca arquivos expirados que precisam ser deletados"""
        return self.session.query(StoredFile).filter(
            StoredFile.status == FileStatus.AVAILABLE,
            StoredFile.expires_at < datetime.utcnow(),
        ).limit(limit).all()

    def delete_file(self, file_id: int) -> bool:
        """Marca arquivo como deletado"""
        file = self.get_file(file_id)
        if not file:
            return False

        file.status = FileStatus.DELETED
        file.deleted_at = datetime.utcnow()
        self.session.commit()
        return True

    # ==================== StoredDirectory CRUD ====================

    def create_directory(
        self,
        user_id: str,
        dir_key: str,
        provider: StorageProviderType,
        bucket: str,
        prefix: str,
        name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        expires_hours: int = 24,
    ) -> StoredDirectory:
        """Cria registro de diretório"""
        directory = StoredDirectory(
            user_id=user_id,
            dir_key=dir_key,
            name=name,
            source_type=source_type,
            source_id=source_id,
            provider=provider,
            bucket=bucket,
            prefix=prefix,
            status=FileStatus.UPLOADING,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        )
        self.session.add(directory)
        self.session.commit()
        logger.info(f"Created directory record: {dir_key}")
        return directory

    def get_directory(self, dir_id: int) -> Optional[StoredDirectory]:
        """Busca diretório por ID"""
        return self.session.query(StoredDirectory).filter(StoredDirectory.id == dir_id).first()

    def get_directory_by_key(self, dir_key: str) -> Optional[StoredDirectory]:
        """Busca diretório por chave"""
        return self.session.query(StoredDirectory).filter(StoredDirectory.dir_key == dir_key).first()

    def get_directory_by_source(
        self,
        source_type: str,
        source_id: str,
    ) -> Optional[StoredDirectory]:
        """Busca diretório por fonte"""
        return self.session.query(StoredDirectory).filter(
            StoredDirectory.source_type == source_type,
            StoredDirectory.source_id == source_id,
        ).first()

    def get_directories_by_user(
        self,
        user_id: str,
        status: Optional[FileStatus] = None,
        limit: int = 50,
    ) -> List[StoredDirectory]:
        """Lista diretórios de um usuário"""
        query = self.session.query(StoredDirectory).filter(StoredDirectory.user_id == user_id)

        if status:
            query = query.filter(StoredDirectory.status == status)

        return query.order_by(desc(StoredDirectory.created_at)).limit(limit).all()

    def update_directory_status(
        self,
        dir_id: int,
        status: FileStatus,
        total_size_bytes: Optional[int] = None,
        file_count: Optional[int] = None,
    ) -> Optional[StoredDirectory]:
        """Atualiza status do diretório"""
        directory = self.get_directory(dir_id)
        if not directory:
            return None

        directory.status = status

        if status == FileStatus.AVAILABLE:
            directory.uploaded_at = datetime.utcnow()

        if status == FileStatus.DELETED:
            directory.deleted_at = datetime.utcnow()

        if total_size_bytes is not None:
            directory.total_size_bytes = total_size_bytes

        if file_count is not None:
            directory.file_count = file_count

        self.session.commit()
        return directory

    def get_expired_directories(self, limit: int = 100) -> List[StoredDirectory]:
        """Busca diretórios expirados"""
        return self.session.query(StoredDirectory).filter(
            StoredDirectory.status == FileStatus.AVAILABLE,
            StoredDirectory.expires_at < datetime.utcnow(),
        ).limit(limit).all()

    # ==================== Estatísticas ====================

    def get_user_storage_stats(self, user_id: str) -> dict:
        """Retorna estatísticas de storage de um usuário"""
        files = self.session.query(StoredFile).filter(
            StoredFile.user_id == user_id,
            StoredFile.status == FileStatus.AVAILABLE,
        ).all()

        directories = self.session.query(StoredDirectory).filter(
            StoredDirectory.user_id == user_id,
            StoredDirectory.status == FileStatus.AVAILABLE,
        ).all()

        total_file_size = sum(f.size_bytes for f in files)
        total_dir_size = sum(d.total_size_bytes for d in directories)

        return {
            "files_count": len(files),
            "directories_count": len(directories),
            "total_size_bytes": total_file_size + total_dir_size,
            "total_size_mb": (total_file_size + total_dir_size) / (1024 * 1024),
        }
