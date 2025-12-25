"""
Migration 001: Create Jobs Schema

Cria as tabelas do módulo de jobs:
- jobs: Definições de jobs (templates)
- job_runs: Execuções de jobs
- job_logs: Logs de execução

Uso:
    python -m src.modules.jobs.migrations.001_create_schema
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from sqlalchemy import text
from src.config.database import engine, Base
from src.modules.jobs.models import Job, JobRun, JobLog


def create_tables():
    """Cria todas as tabelas do módulo jobs"""
    tables = [
        Job.__table__,
        JobRun.__table__,
        JobLog.__table__,
    ]

    for table in tables:
        table.create(engine, checkfirst=True)
        print(f"✓ Tabela '{table.name}' criada/verificada")


def create_indexes():
    """Cria índices adicionais"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_job_runs_status_queued ON job_runs(status, queued_at)",
        "CREATE INDEX IF NOT EXISTS idx_job_runs_user_status ON job_runs(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_user_type ON jobs(user_id, job_type)",
    ]

    with engine.connect() as conn:
        for idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                print(f"✓ Índice criado: {idx_sql.split()[-1]}")
            except Exception as e:
                # Índice pode já existir
                if "already exists" not in str(e).lower():
                    print(f"⚠ Aviso ao criar índice: {e}")
        conn.commit()


def run_migration():
    """Executa migração completa"""
    print("\n" + "=" * 60)
    print("  MIGRATION: Create Jobs Schema")
    print("=" * 60 + "\n")

    create_tables()
    create_indexes()

    print("\n" + "=" * 60)
    print("  MIGRATION COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_migration()
