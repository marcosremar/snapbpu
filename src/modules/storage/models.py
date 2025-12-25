"""
Storage Module - Database Models

Modelos para gerenciamento de arquivos armazenados:
- StoredFile: Arquivo armazenado com expiração
- StorageProvider: Provedores de storage configurados
"""

import enum
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Enum, ForeignKey, BigInteger
)
from sqlalchemy.orm import relationship

from src.config.database import Base


class StorageProviderType(enum.Enum):
    """Tipos de provedor de storage"""
    BACKBLAZE_B2 = "BACKBLAZE_B2"
    gcs = "gcs"  # Google Cloud Storage (minúsculo para match com DB)
    LOCAL = "LOCAL"


class FileStatus(enum.Enum):
    """Status do arquivo"""
    UPLOADING = "uploading"
    AVAILABLE = "available"
    EXPIRED = "expired"
    DELETED = "deleted"
    FAILED = "failed"


class StoredFile(Base):
    """
    Arquivo armazenado no cloud storage.

    Rastreia arquivos uploadados com:
    - Expiração automática
    - URLs temporárias para download
    - Metadados do arquivo
    """
    __tablename__ = "stored_files"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificação
    user_id = Column(String(255), nullable=False, index=True)
    file_key = Column(String(500), nullable=False, unique=True)  # Chave no storage
    original_name = Column(String(255), nullable=True)  # Nome original do arquivo

    # Fonte
    source_type = Column(String(50), nullable=True)  # "job", "upload", "snapshot"
    source_id = Column(String(100), nullable=True)   # ID do job, etc

    # Storage
    provider = Column(Enum(StorageProviderType), nullable=False)
    bucket = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)  # Caminho no bucket

    # Metadados
    size_bytes = Column(BigInteger, default=0)
    content_type = Column(String(100), nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA-256

    # Status e expiração
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADING)
    expires_at = Column(DateTime, nullable=False)
    is_public = Column(Boolean, default=False)

    # URLs
    download_url = Column(String(1000), nullable=True)  # URL pré-assinada
    url_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<StoredFile {self.id}: {self.original_name} ({self.status.value})>"

    @property
    def is_expired(self) -> bool:
        """Verifica se o arquivo expirou"""
        return datetime.utcnow() > self.expires_at

    @property
    def time_remaining(self) -> Optional[timedelta]:
        """Tempo restante até expirar"""
        if self.is_expired:
            return None
        return self.expires_at - datetime.utcnow()

    @property
    def size_mb(self) -> float:
        """Tamanho em MB"""
        return self.size_bytes / (1024 * 1024)

    def get_storage_path(self) -> str:
        """Retorna caminho completo no storage"""
        return f"{self.provider.value}://{self.bucket}/{self.path}"


class StoredDirectory(Base):
    """
    Diretório armazenado (conjunto de arquivos).

    Usado para outputs de jobs que podem ter múltiplos arquivos.
    """
    __tablename__ = "stored_directories"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identificação
    user_id = Column(String(255), nullable=False, index=True)
    dir_key = Column(String(500), nullable=False, unique=True)
    name = Column(String(255), nullable=True)

    # Fonte
    source_type = Column(String(50), nullable=True)
    source_id = Column(String(100), nullable=True, index=True)

    # Storage
    provider = Column(Enum(StorageProviderType), nullable=False)
    bucket = Column(String(255), nullable=False)
    prefix = Column(String(500), nullable=False)  # Prefixo no bucket

    # Metadados
    total_size_bytes = Column(BigInteger, default=0)
    file_count = Column(Integer, default=0)

    # Status e expiração
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADING)
    expires_at = Column(DateTime, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<StoredDirectory {self.id}: {self.name} ({self.file_count} files)>"

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


# Índices adicionais
from sqlalchemy import Index

Index('idx_stored_files_user_status', StoredFile.user_id, StoredFile.status)
Index('idx_stored_files_expires', StoredFile.expires_at)
Index('idx_stored_files_source', StoredFile.source_type, StoredFile.source_id)
Index('idx_stored_dirs_user', StoredDirectory.user_id)
Index('idx_stored_dirs_source', StoredDirectory.source_type, StoredDirectory.source_id)
