"""
Migration 001: Create Storage Schema

Cria as tabelas do módulo de storage:
- stored_files: Arquivos armazenados com expiração
- stored_directories: Diretórios (conjuntos de arquivos)

Uso:
    python -m src.modules.storage.migrations.001_create_schema
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from sqlalchemy import text
from src.config.database import engine, Base
from src.modules.storage.models import StoredFile, StoredDirectory


def create_tables():
    """Cria todas as tabelas do módulo storage"""
    tables = [
        StoredFile.__table__,
        StoredDirectory.__table__,
    ]

    for table in tables:
        table.create(engine, checkfirst=True)
        print(f"✓ Tabela '{table.name}' criada/verificada")


def create_indexes():
    """Cria índices adicionais"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_stored_files_user_status ON stored_files(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_stored_files_expires ON stored_files(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_stored_files_source ON stored_files(source_type, source_id)",
        "CREATE INDEX IF NOT EXISTS idx_stored_dirs_user ON stored_directories(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_stored_dirs_source ON stored_directories(source_type, source_id)",
    ]

    with engine.connect() as conn:
        for idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                idx_name = idx_sql.split("idx_")[1].split(" ")[0]
                print(f"✓ Índice criado: idx_{idx_name}")
            except Exception as e:
                # Índice pode já existir
                if "already exists" not in str(e).lower():
                    print(f"⚠ Aviso ao criar índice: {e}")
        conn.commit()


def run_migration():
    """Executa migração completa"""
    print("\n" + "=" * 60)
    print("  MIGRATION: Create Storage Schema")
    print("=" * 60 + "\n")

    create_tables()
    create_indexes()

    print("\n" + "=" * 60)
    print("  MIGRATION COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_migration()
