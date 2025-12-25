"""
Jobs Module - Repository

Repositório para persistência de Jobs e JobRuns.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from .models import Job, JobRun, JobLog, JobType, JobStatus, JobPriority

logger = logging.getLogger(__name__)


class JobRepository:
    """Repositório para operações com Jobs"""

    def __init__(self, session: Session):
        self.session = session

    # ==================== Job CRUD ====================

    def create_job(
        self,
        user_id: str,
        name: str,
        docker_image: str,
        job_type: JobType = JobType.CUSTOM,
        description: Optional[str] = None,
        gpu_name: Optional[str] = None,
        min_vram_gb: Optional[int] = None,
        max_price_per_hour: float = 1.0,
        command: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        input_path: Optional[str] = None,
        output_path: Optional[str] = None,
        timeout_seconds: int = 3600,
        max_retries: int = 2,
        disk_gb: int = 50,
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Job:
        """Cria um novo job"""
        job = Job(
            user_id=user_id,
            name=name,
            description=description,
            job_type=job_type,
            gpu_name=gpu_name,
            min_vram_gb=min_vram_gb,
            max_price_per_hour=max_price_per_hour,
            docker_image=docker_image,
            command=command,
            env_vars=env_vars,
            input_path=input_path,
            output_path=output_path,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            disk_gb=disk_gb,
            config=config,
            tags=tags,
        )
        self.session.add(job)
        self.session.commit()
        logger.info(f"Created job {job.id}: {name}")
        return job

    def get_job(self, job_id: int) -> Optional[Job]:
        """Busca job por ID"""
        return self.session.query(Job).filter(Job.id == job_id).first()

    def get_jobs_by_user(
        self,
        user_id: str,
        job_type: Optional[JobType] = None,
        limit: int = 50,
    ) -> List[Job]:
        """Lista jobs de um usuário"""
        query = self.session.query(Job).filter(Job.user_id == user_id)

        if job_type:
            query = query.filter(Job.job_type == job_type)

        return query.order_by(desc(Job.created_at)).limit(limit).all()

    def update_job(self, job_id: int, **kwargs) -> Optional[Job]:
        """Atualiza um job"""
        job = self.get_job(job_id)
        if not job:
            return None

        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        job.updated_at = datetime.utcnow()
        self.session.commit()
        return job

    def delete_job(self, job_id: int) -> bool:
        """Deleta um job (e seus runs)"""
        job = self.get_job(job_id)
        if not job:
            return False

        self.session.delete(job)
        self.session.commit()
        logger.info(f"Deleted job {job_id}")
        return True

    # ==================== JobRun CRUD ====================

    def create_run(
        self,
        job_id: int,
        user_id: str,
        priority: JobPriority = JobPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JobRun:
        """Cria uma nova execução de job"""
        # Contar runs anteriores
        run_count = self.session.query(JobRun).filter(
            JobRun.job_id == job_id
        ).count()

        run = JobRun(
            job_id=job_id,
            user_id=user_id,
            run_number=run_count + 1,
            priority=priority,
            status=JobStatus.PENDING,
            queued_at=datetime.utcnow(),
            run_metadata=metadata,
        )
        self.session.add(run)
        self.session.commit()
        logger.info(f"Created run {run.id} for job {job_id}")
        return run

    def get_run(self, run_id: int) -> Optional[JobRun]:
        """Busca run por ID"""
        return self.session.query(JobRun).filter(JobRun.id == run_id).first()

    def get_run_by_instance(self, vast_instance_id: int) -> Optional[JobRun]:
        """Busca run por ID da instância VAST"""
        return self.session.query(JobRun).filter(
            JobRun.vast_instance_id == vast_instance_id,
            JobRun.status == JobStatus.RUNNING
        ).first()

    def get_runs_by_job(
        self,
        job_id: int,
        limit: int = 20,
    ) -> List[JobRun]:
        """Lista runs de um job"""
        return self.session.query(JobRun).filter(
            JobRun.job_id == job_id
        ).order_by(desc(JobRun.queued_at)).limit(limit).all()

    def get_runs_by_user(
        self,
        user_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 50,
    ) -> List[JobRun]:
        """Lista runs de um usuário"""
        query = self.session.query(JobRun).filter(JobRun.user_id == user_id)

        if status:
            query = query.filter(JobRun.status == status)

        return query.order_by(desc(JobRun.queued_at)).limit(limit).all()

    def get_pending_runs(self, limit: int = 10) -> List[JobRun]:
        """Busca runs pendentes ordenados por prioridade"""
        priority_order = [
            JobPriority.URGENT,
            JobPriority.HIGH,
            JobPriority.NORMAL,
            JobPriority.LOW,
        ]

        return self.session.query(JobRun).filter(
            JobRun.status == JobStatus.PENDING
        ).order_by(
            # Ordenar por prioridade (usando case)
            func.field(JobRun.priority, *[p.value for p in priority_order]),
            JobRun.queued_at
        ).limit(limit).all()

    def get_running_runs(self) -> List[JobRun]:
        """Busca runs em execução"""
        return self.session.query(JobRun).filter(
            JobRun.status.in_([JobStatus.RUNNING, JobStatus.PROVISIONING])
        ).all()

    def update_run_status(
        self,
        run_id: int,
        status: JobStatus,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None,
    ) -> Optional[JobRun]:
        """Atualiza status de um run"""
        run = self.get_run(run_id)
        if not run:
            return None

        run.status = status

        if status == JobStatus.RUNNING and not run.started_at:
            run.started_at = datetime.utcnow()

        if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMEOUT]:
            run.completed_at = datetime.utcnow()
            if run.started_at:
                duration = (run.completed_at - run.started_at).total_seconds()
                run.gpu_seconds = duration
                if run.hourly_rate:
                    run.cost_usd = (duration / 3600) * run.hourly_rate

        if error_message:
            run.error_message = error_message
            run.last_error = error_message

        if exit_code is not None:
            run.exit_code = exit_code

        self.session.commit()
        logger.info(f"Updated run {run_id} status to {status.value}")
        return run

    def update_run_instance(
        self,
        run_id: int,
        vast_instance_id: int,
        vast_offer_id: Optional[int] = None,
        gpu_name: Optional[str] = None,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        hourly_rate: Optional[float] = None,
    ) -> Optional[JobRun]:
        """Atualiza informações da instância de um run"""
        run = self.get_run(run_id)
        if not run:
            return None

        run.vast_instance_id = vast_instance_id
        run.vast_offer_id = vast_offer_id
        run.gpu_name = gpu_name
        run.ssh_host = ssh_host
        run.ssh_port = ssh_port
        run.hourly_rate = hourly_rate

        self.session.commit()
        return run

    def increment_retry(self, run_id: int, error: str) -> Optional[JobRun]:
        """Incrementa contador de retry"""
        run = self.get_run(run_id)
        if not run:
            return None

        run.retry_count += 1
        run.last_error = error
        run.status = JobStatus.PENDING  # Volta para a fila
        run.vast_instance_id = None

        self.session.commit()
        logger.info(f"Run {run_id} retry {run.retry_count}")
        return run

    # ==================== JobLog ====================

    def add_log(
        self,
        run_id: int,
        message: str,
        level: str = "INFO",
        stage: Optional[str] = None,
    ) -> JobLog:
        """Adiciona log a um run"""
        log = JobLog(
            run_id=run_id,
            message=message,
            level=level,
            stage=stage,
        )
        self.session.add(log)
        self.session.commit()
        return log

    def get_logs(
        self,
        run_id: int,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobLog]:
        """Busca logs de um run"""
        query = self.session.query(JobLog).filter(JobLog.run_id == run_id)

        if level:
            query = query.filter(JobLog.level == level)

        return query.order_by(JobLog.timestamp).limit(limit).all()

    # ==================== Estatísticas ====================

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de jobs de um usuário"""
        runs = self.session.query(JobRun).filter(
            JobRun.user_id == user_id
        ).all()

        total_runs = len(runs)
        completed = sum(1 for r in runs if r.status == JobStatus.COMPLETED)
        failed = sum(1 for r in runs if r.status == JobStatus.FAILED)
        running = sum(1 for r in runs if r.status == JobStatus.RUNNING)
        pending = sum(1 for r in runs if r.status == JobStatus.PENDING)

        total_gpu_seconds = sum(r.gpu_seconds or 0 for r in runs)
        total_cost = sum(r.cost_usd or 0 for r in runs)

        return {
            "total_runs": total_runs,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "success_rate": completed / total_runs if total_runs > 0 else 0,
            "total_gpu_hours": total_gpu_seconds / 3600,
            "total_cost_usd": total_cost,
        }

    def get_stale_runs(self, timeout_minutes: int = 60) -> List[JobRun]:
        """Busca runs que estão rodando há muito tempo (possivelmente travados)"""
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        return self.session.query(JobRun).filter(
            JobRun.status == JobStatus.RUNNING,
            JobRun.started_at < threshold
        ).all()
