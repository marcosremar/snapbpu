"""
Jobs Module

Sistema de gerenciamento de jobs GPU para tarefas de ML:
- Fine-tuning de modelos
- Treinamento
- Inferência batch
- Scripts customizados

Diferente do módulo serverless (pause/resume), este módulo:
- Cria GPU -> Executa tarefa -> Destrói GPU
- Ideal para jobs batch onde cold start é aceitável
"""

from .models import Job, JobRun, JobLog, JobType, JobStatus, JobPriority
from .repository import JobRepository
from .executor import JobExecutor, FineTuneExecutor, ExecutionResult
from .service import JobService, get_job_service

__all__ = [
    # Models
    "Job",
    "JobRun",
    "JobLog",
    "JobType",
    "JobStatus",
    "JobPriority",
    # Repository
    "JobRepository",
    # Executors
    "JobExecutor",
    "FineTuneExecutor",
    "ExecutionResult",
    # Service
    "JobService",
    "get_job_service",
]
