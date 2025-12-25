"""
Jobs Module - Service

Serviço principal para gerenciamento de jobs:
- Criação e submissão de jobs
- Processamento da fila
- Monitoramento de execução
- Cleanup e retry
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from contextlib import contextmanager

from .models import Job, JobRun, JobLog, JobType, JobStatus, JobPriority
from .repository import JobRepository
from .executor import JobExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class JobService:
    """
    Serviço de gerenciamento de jobs GPU.

    Responsabilidades:
    - CRUD de jobs e runs
    - Processamento da fila de jobs
    - Monitoramento de execução
    - Retry automático
    - Cleanup de recursos
    """

    def __init__(
        self,
        vast_service,
        session_factory: Callable,
        max_concurrent_jobs: int = 5,
        poll_interval: int = 10,
        auto_start: bool = False,
    ):
        """
        Args:
            vast_service: Serviço VAST.ai para provisionar GPUs
            session_factory: Factory para criar sessões do banco
            max_concurrent_jobs: Máximo de jobs simultâneos
            poll_interval: Intervalo de polling da fila (segundos)
            auto_start: Se True, inicia worker automaticamente
        """
        self.vast_service = vast_service
        self.session_factory = session_factory
        self.max_concurrent_jobs = max_concurrent_jobs
        self.poll_interval = poll_interval

        self.executor = JobExecutor(vast_service)

        # Worker thread
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Callbacks
        self._on_job_complete: Optional[Callable] = None
        self._on_job_failed: Optional[Callable] = None

        if auto_start:
            self.start()

    @contextmanager
    def _get_session(self):
        """Context manager para sessão do banco"""
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    # ==================== Job Management ====================

    def create_job(
        self,
        user_id: str,
        name: str,
        docker_image: str,
        job_type: JobType = JobType.CUSTOM,
        command: Optional[str] = None,
        gpu_name: Optional[str] = None,
        max_price_per_hour: float = 1.0,
        timeout_seconds: int = 3600,
        **kwargs,
    ) -> Job:
        """Cria um novo job"""
        with self._get_session() as session:
            repo = JobRepository(session)
            job = repo.create_job(
                user_id=user_id,
                name=name,
                docker_image=docker_image,
                job_type=job_type,
                command=command,
                gpu_name=gpu_name,
                max_price_per_hour=max_price_per_hour,
                timeout_seconds=timeout_seconds,
                **kwargs,
            )
            logger.info(f"Job criado: {job.id} - {name}")
            return job

    def get_job(self, job_id: int) -> Optional[Job]:
        """Busca job por ID"""
        with self._get_session() as session:
            repo = JobRepository(session)
            return repo.get_job(job_id)

    def list_jobs(
        self,
        user_id: str,
        job_type: Optional[JobType] = None,
        limit: int = 50,
    ) -> List[Job]:
        """Lista jobs de um usuário"""
        with self._get_session() as session:
            repo = JobRepository(session)
            return repo.get_jobs_by_user(user_id, job_type, limit)

    def delete_job(self, job_id: int) -> bool:
        """Deleta um job"""
        with self._get_session() as session:
            repo = JobRepository(session)
            return repo.delete_job(job_id)

    # ==================== Job Execution ====================

    def submit_job(
        self,
        job_id: int,
        priority: JobPriority = JobPriority.NORMAL,
        run_now: bool = False,
    ) -> JobRun:
        """
        Submete um job para execução.

        Args:
            job_id: ID do job a executar
            priority: Prioridade na fila
            run_now: Se True, executa imediatamente (bypass fila)

        Returns:
            JobRun criado
        """
        with self._get_session() as session:
            repo = JobRepository(session)

            job = repo.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} não encontrado")

            run = repo.create_run(
                job_id=job_id,
                user_id=job.user_id,
                priority=priority,
            )

            repo.add_log(run.id, f"Job submetido com prioridade {priority.value}", "INFO", "queue")

            logger.info(f"Job {job_id} submetido - Run {run.id}")

            if run_now:
                # Executar imediatamente em thread separada
                thread = threading.Thread(
                    target=self._execute_run,
                    args=(run.id,),
                    daemon=True,
                )
                thread.start()

            return run

    def cancel_run(self, run_id: int) -> bool:
        """Cancela um run em execução ou pendente"""
        with self._get_session() as session:
            repo = JobRepository(session)

            run = repo.get_run(run_id)
            if not run:
                return False

            if run.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False

            # Se estiver rodando, destruir instância
            if run.status == JobStatus.RUNNING and run.vast_instance_id:
                try:
                    self.vast_service.destroy_instance(run.vast_instance_id)
                except Exception as e:
                    logger.error(f"Erro destruindo instância {run.vast_instance_id}: {e}")

            repo.update_run_status(run_id, JobStatus.CANCELLED)
            repo.add_log(run_id, "Job cancelado pelo usuário", "INFO", "cancel")

            logger.info(f"Run {run_id} cancelado")
            return True

    def get_run(self, run_id: int) -> Optional[JobRun]:
        """Busca run por ID"""
        with self._get_session() as session:
            repo = JobRepository(session)
            return repo.get_run(run_id)

    def list_runs(
        self,
        user_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 50,
    ) -> List[JobRun]:
        """Lista runs de um usuário"""
        with self._get_session() as session:
            repo = JobRepository(session)
            return repo.get_runs_by_user(user_id, status, limit)

    def get_run_logs(self, run_id: int, limit: int = 100) -> List[JobLog]:
        """Busca logs de um run"""
        with self._get_session() as session:
            repo = JobRepository(session)
            return repo.get_logs(run_id, limit=limit)

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de jobs de um usuário"""
        with self._get_session() as session:
            repo = JobRepository(session)
            return repo.get_user_stats(user_id)

    # ==================== Worker ====================

    def start(self):
        """Inicia worker de processamento da fila"""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="JobWorker",
        )
        self._worker_thread.start()
        logger.info("Job worker iniciado")

    def stop(self):
        """Para worker"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=10)
        logger.info("Job worker parado")

    def _worker_loop(self):
        """Loop principal do worker"""
        while self._running:
            try:
                self._process_queue()
                self._check_timeouts()
            except Exception as e:
                logger.error(f"Erro no worker: {e}")

            time.sleep(self.poll_interval)

    def _process_queue(self):
        """Processa fila de jobs pendentes"""
        with self._get_session() as session:
            repo = JobRepository(session)

            # Verificar quantos jobs estão rodando
            running = repo.get_running_runs()
            running_count = len(running)

            if running_count >= self.max_concurrent_jobs:
                return

            # Buscar jobs pendentes
            slots = self.max_concurrent_jobs - running_count
            pending = repo.get_pending_runs(limit=slots)

            for run in pending:
                # Iniciar execução em thread separada
                thread = threading.Thread(
                    target=self._execute_run,
                    args=(run.id,),
                    daemon=True,
                )
                thread.start()

    def _execute_run(self, run_id: int):
        """Executa um run"""
        with self._get_session() as session:
            repo = JobRepository(session)

            run = repo.get_run(run_id)
            if not run or run.status != JobStatus.PENDING:
                return

            job = repo.get_job(run.job_id)
            if not job:
                repo.update_run_status(run_id, JobStatus.FAILED, "Job não encontrado")
                return

            # Atualizar status
            repo.update_run_status(run_id, JobStatus.PROVISIONING)
            repo.add_log(run_id, "Provisionando GPU...", "INFO", "provisioning")

            # Construir config de execução
            job_config = {
                "job_id": job.id,
                "docker_image": job.docker_image,
                "command": job.command,
                "gpu_name": job.gpu_name,
                "max_price": job.max_price_per_hour,
                "disk_gb": job.disk_gb,
                "env_vars": job.env_vars or {},
                "timeout_seconds": job.timeout_seconds,
                "input_path": job.input_path,
                "output_path": job.output_path,
            }

            # Callback para logs
            def on_log(level: str, message: str):
                with self._get_session() as s:
                    r = JobRepository(s)
                    r.add_log(run_id, message, level, "execution")

            # Executar
            try:
                result = self.executor.execute(job_config, on_log=on_log)

                # Atualizar run com resultado
                if result.instance_id:
                    repo.update_run_instance(
                        run_id,
                        vast_instance_id=result.instance_id,
                        gpu_name=result.gpu_name,
                        hourly_rate=result.cost_usd / (result.duration_seconds / 3600) if result.duration_seconds > 0 else None,
                    )

                if result.success:
                    repo.update_run_status(
                        run_id,
                        JobStatus.COMPLETED,
                        exit_code=result.exit_code,
                    )
                    run = repo.get_run(run_id)
                    run.cost_usd = result.cost_usd
                    run.gpu_seconds = result.duration_seconds
                    run.output_url = result.output_url
                    session.commit()

                    repo.add_log(run_id, f"Job concluído com sucesso em {result.duration_seconds:.0f}s", "INFO", "complete")

                    if self._on_job_complete:
                        self._on_job_complete(run)
                else:
                    # Verificar retry
                    if run.retry_count < job.max_retries:
                        repo.increment_retry(run_id, result.error or "Falha na execução")
                        repo.add_log(run_id, f"Retry {run.retry_count + 1}/{job.max_retries}: {result.error}", "WARNING", "retry")
                    else:
                        repo.update_run_status(
                            run_id,
                            JobStatus.FAILED,
                            error_message=result.error,
                            exit_code=result.exit_code,
                        )
                        repo.add_log(run_id, f"Job falhou: {result.error}", "ERROR", "failed")

                        if self._on_job_failed:
                            self._on_job_failed(run, result.error)

            except Exception as e:
                logger.exception(f"Erro executando run {run_id}")
                repo.update_run_status(run_id, JobStatus.FAILED, str(e))
                repo.add_log(run_id, f"Erro inesperado: {e}", "ERROR", "error")

    def _check_timeouts(self):
        """Verifica jobs que excederam timeout"""
        with self._get_session() as session:
            repo = JobRepository(session)

            # Buscar runs rodando há muito tempo
            stale_runs = repo.get_stale_runs(timeout_minutes=120)

            for run in stale_runs:
                job = repo.get_job(run.job_id)
                if not job:
                    continue

                # Verificar se excedeu timeout do job
                if run.started_at:
                    elapsed = (datetime.utcnow() - run.started_at).total_seconds()
                    if elapsed > job.timeout_seconds:
                        logger.warning(f"Run {run.id} excedeu timeout ({elapsed:.0f}s > {job.timeout_seconds}s)")

                        # Destruir instância
                        if run.vast_instance_id:
                            try:
                                self.vast_service.destroy_instance(run.vast_instance_id)
                            except:
                                pass

                        repo.update_run_status(run.id, JobStatus.TIMEOUT, "Timeout excedido")
                        repo.add_log(run.id, f"Job excedeu timeout de {job.timeout_seconds}s", "ERROR", "timeout")

    # ==================== Callbacks ====================

    def on_job_complete(self, callback: Callable):
        """Registra callback para quando job completa"""
        self._on_job_complete = callback

    def on_job_failed(self, callback: Callable):
        """Registra callback para quando job falha"""
        self._on_job_failed = callback


# Singleton global
_job_service: Optional[JobService] = None


def get_job_service(
    vast_service=None,
    session_factory=None,
    **kwargs,
) -> JobService:
    """Retorna instância singleton do JobService"""
    global _job_service

    if _job_service is None:
        if vast_service is None or session_factory is None:
            raise ValueError("vast_service e session_factory são obrigatórios na primeira chamada")
        _job_service = JobService(vast_service, session_factory, **kwargs)

    return _job_service
