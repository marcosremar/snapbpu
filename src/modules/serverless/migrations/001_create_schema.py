"""
Migration 001: Create Serverless Schema

Cria o schema 'serverless' e todas as tabelas do módulo.

Uso:
    python -m src.modules.serverless.migrations.001_create_schema
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from sqlalchemy import text
from src.config.database import engine, Base
from src.modules.serverless.models import (
    ServerlessUserSettings,
    ServerlessInstance,
    ServerlessSnapshot,
    ServerlessEvent,
)


def create_schema():
    """Cria schema 'serverless' se não existir"""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS serverless"))
        conn.commit()
    print("✓ Schema 'serverless' criado/verificado")


def create_tables():
    """Cria todas as tabelas do módulo serverless"""
    # Criar apenas as tabelas do módulo serverless
    tables = [
        ServerlessUserSettings.__table__,
        ServerlessInstance.__table__,
        ServerlessSnapshot.__table__,
        ServerlessEvent.__table__,
    ]

    for table in tables:
        table.create(engine, checkfirst=True)
        print(f"✓ Tabela '{table.name}' criada/verificada")


def run_migration():
    """Executa migração completa"""
    print("\n" + "="*60)
    print("  MIGRATION: Create Serverless Schema")
    print("="*60 + "\n")

    create_schema()
    create_tables()

    print("\n" + "="*60)
    print("  MIGRATION COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_migration()
