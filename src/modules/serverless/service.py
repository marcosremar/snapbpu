"""
Serverless Module - Service Layer

Lógica de negócio para:
- Scale down/up automático
- Auto-destroy após X horas pausado
- Fallback: snapshot ou migração de disco quando resume falha
- Suporte a cuda-checkpoint (TensorDock)

Providers suportados:
- TensorDock (recomendado): Suporta cuda-checkpoint, cold start ~20s
- VAST.ai: Fallback, cold start ~30-60s
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from .repository import ServerlessRepository
from .models import (
    ServerlessInstance,
    ServerlessUserSettings,
    InstanceStateEnum,
    EventTypeEnum,
    create_serverless_schema,
)
from .fallback import FallbackOrchestrator, FallbackResult
from .checkpoint import GPUCheckpointService, get_checkpoint_service

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Tipo de provider GPU"""
    TENSORDOCK = "tensordock"
    VAST = "vast"


@runtime_checkable
class GPUProvider(Protocol):
    """Interface para providers de GPU"""

    def get_instance_status(self, instance_id: str) -> Dict[str, Any]: ...
    def pause_instance(self, instance_id: str) -> bool: ...
    def resume_instance(self, instance_id: str) -> bool: ...
    def destroy_instance(self, instance_id: str) -> bool: ...


@dataclass
class ScaleDownResult:
    """Resultado de operação scale down"""
    success: bool
    instance_id: int
    duration_seconds: float
    error: Optional[str] = None


@dataclass
class ScaleUpResult:
    """Resultado de operação scale up"""
    success: bool
    instance_id: int
    cold_start_seconds: float
    method: str = "resume"  # "resume", "snapshot", "disk_migration"
    new_instance_id: Optional[int] = None  # Se criou nova instância
    error: Optional[str] = None


class ServerlessService:
    """
    Serviço principal de Serverless.

    Responsabilidades:
    - Monitorar instâncias para scale down
    - Executar scale down (pause) quando idle
    - Executar scale up (resume) quando requisição chega
    - Auto-destroy instâncias pausadas por muito tempo
    - Fallback para snapshot/disco quando resume falha
    - Suporte a cuda-checkpoint para cold start rápido (TensorDock)
    """

    def __init__(
        self,
        session_factory,
        gpu_provider: GPUProvider,
        provider_type: ProviderType = ProviderType.TENSORDOCK,
        check_interval: float = 1.0,  # Verificar a cada 1s para scale down rápido
        enable_cuda_checkpoint: bool = True,  # Usar cuda-checkpoint quando disponível
    ):
        self.session_factory = session_factory
        self.gpu_provider = gpu_provider
        self.provider_type = provider_type
        self.check_interval = check_interval
        self.enable_cuda_checkpoint = enable_cuda_checkpoint

        # Alias para compatibilidade
        self.vast_provider = gpu_provider

        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._destroy_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Cache de última requisição (em memória para performance)
        self._last_request: Dict[str, datetime] = {}

        # Serviço de checkpoint GPU (para TensorDock)
        self._checkpoint_service: Optional[GPUCheckpointService] = None
        if enable_cuda_checkpoint and provider_type == ProviderType.TENSORDOCK:
            self._checkpoint_service = get_checkpoint_service()
            logger.info("cuda-checkpoint habilitado (TensorDock)")

        # Fallback orchestrator para quando resume falha
        self._fallback_orchestrator = FallbackOrchestrator(
            vast_provider=gpu_provider,
            session_factory=session_factory
        )

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def start(self):
        """Inicia serviço de monitoramento"""
        if self._running:
            return

        self._running = True

        # Thread de scale down (verifica a cada 1s)
        self._monitor_thread = threading.Thread(
            target=self._scale_down_loop,
            daemon=True,
            name="serverless-scaledown"
        )
        self._monitor_thread.start()

        # Thread de auto-destroy (verifica a cada 5 min)
        self._destroy_thread = threading.Thread(
            target=self._auto_destroy_loop,
            daemon=True,
            name="serverless-destroy"
        )
        self._destroy_thread.start()

        logger.info("ServerlessService started")

    def stop(self):
        """Para serviço"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        if self._destroy_thread:
            self._destroy_thread.join(timeout=5)
        logger.info("ServerlessService stopped")

    # =========================================================================
    # REQUEST TRACKING (chamado pelo middleware da API)
    # =========================================================================

    def on_request_start(self, instance_id: int):
        """
        Chamado quando uma requisição chega.
        Se instância estiver pausada, faz scale up.
        """
        with self._lock:
            self._last_request[instance_id] = datetime.utcnow()

        # Verificar se precisa acordar
        with self.session_factory() as session:
            repo = ServerlessRepository(session)
            instance = repo.get_instance(instance_id)

            if instance and instance.state == InstanceStateEnum.PAUSED:
                logger.info(f"Request received for paused instance {instance_id}, waking up...")
                return self._scale_up(instance_id)

        return None

    def on_request_end(self, instance_id: int):
        """Chamado quando requisição termina - reseta timer de idle"""
        with self._lock:
            self._last_request[instance_id] = datetime.utcnow()

        with self.session_factory() as session:
            repo = ServerlessRepository(session)
            repo.update_last_request(instance_id)

    # =========================================================================
    # SCALE DOWN (Pause)
    # =========================================================================

    def _scale_down_loop(self):
        """Loop de verificação de scale down"""
        while self._running:
            try:
                self._check_scale_down()
            except Exception as e:
                logger.error(f"Error in scale down loop: {e}")
            time.sleep(self.check_interval)

    def _check_scale_down(self):
        """Verifica instâncias que devem fazer scale down"""
        now = datetime.utcnow()

        with self.session_factory() as session:
            repo = ServerlessRepository(session)

            # Verificar cache de última requisição (mais preciso que DB)
            with self._lock:
                for instance_id, last_req in list(self._last_request.items()):
                    instance = repo.get_instance(instance_id)
                    if not instance or instance.state != InstanceStateEnum.RUNNING:
                        continue

                    idle_seconds = (now - last_req).total_seconds()

                    if idle_seconds >= instance.scale_down_timeout_seconds:
                        logger.info(
                            f"Instance {instance_id} idle for {idle_seconds:.1f}s "
                            f"(timeout: {instance.scale_down_timeout_seconds}s), scaling down..."
                        )
                        self._scale_down(instance_id)

    def _scale_down(self, instance_id: str) -> ScaleDownResult:
        """
        Executa scale down (pause) de uma instância.

        Com TensorDock + cuda-checkpoint:
        1. Cria checkpoint do estado GPU (VRAM + processos)
        2. Para a instância

        Sem cuda-checkpoint:
        1. Para a instância diretamente
        """
        start = time.time()
        checkpoint_id = None

        try:
            # Obter info da instância
            with self.session_factory() as session:
                repo = ServerlessRepository(session)
                instance = repo.get_instance(instance_id)

            # 1. Criar cuda-checkpoint antes de pausar (se habilitado)
            if self._checkpoint_service and instance:
                logger.info(f"Criando cuda-checkpoint para {instance_id}...")
                checkpoint_result = self._checkpoint_service.create_checkpoint(
                    instance_id=str(instance_id),
                    ssh_host=instance.ssh_host,
                    ssh_port=instance.ssh_port,
                )
                if checkpoint_result.get("success"):
                    checkpoint_id = checkpoint_result.get("checkpoint_id")
                    logger.info(f"Checkpoint criado: {checkpoint_id} ({checkpoint_result.get('vram_gb', 0):.1f}GB VRAM)")
                else:
                    logger.warning(f"Checkpoint falhou: {checkpoint_result.get('error')}")

            # 2. Pausar via provider
            success = self.gpu_provider.pause_instance(str(instance_id))

            if not success:
                return ScaleDownResult(
                    success=False,
                    instance_id=instance_id,
                    duration_seconds=time.time() - start,
                    error=f"{self.provider_type.value} pause failed"
                )

            # 3. Atualizar estado no banco
            with self.session_factory() as session:
                repo = ServerlessRepository(session)
                repo.update_instance_state(instance_id, InstanceStateEnum.PAUSED)

                # Salvar checkpoint_id se criado
                if checkpoint_id and instance:
                    repo.update_instance_checkpoint(instance_id, checkpoint_id)

                # Registrar evento
                instance = repo.get_instance(instance_id)
                if instance:
                    repo.log_event(
                        instance_id=instance.id,
                        user_id=instance.user_id,
                        event_type=EventTypeEnum.SCALE_DOWN,
                        duration_seconds=time.time() - start,
                        details={
                            "reason": "idle_timeout",
                            "checkpoint_id": checkpoint_id,
                            "provider": self.provider_type.value,
                        }
                    )

            # 4. Remover do cache
            with self._lock:
                self._last_request.pop(instance_id, None)

            duration = time.time() - start
            logger.info(f"Instance {instance_id} scaled down in {duration:.2f}s (checkpoint: {checkpoint_id or 'none'})")

            return ScaleDownResult(
                success=True,
                instance_id=instance_id,
                duration_seconds=duration
            )

        except Exception as e:
            logger.error(f"Scale down failed for {instance_id}: {e}")
            return ScaleDownResult(
                success=False,
                instance_id=instance_id,
                duration_seconds=time.time() - start,
                error=str(e)
            )

    # =========================================================================
    # SCALE UP (Resume / Fallback)
    # =========================================================================

    def _scale_up(self, instance_id: str) -> ScaleUpResult:
        """
        Executa scale up de uma instância.

        Ordem de tentativa:
        1. Resume + cuda-checkpoint restore (TensorDock)
        2. Resume normal
        3. Se falhar: Restaurar snapshot em nova máquina
        4. Se falhar: Migrar disco para nova máquina
        """
        start = time.time()

        # Tentativa 1: Resume com cuda-checkpoint (se disponível)
        logger.info(f"Attempting resume for {instance_id} (provider: {self.provider_type.value})")
        result = self._try_resume(instance_id)

        if result.success:
            self._log_scale_up_event(instance_id, result, start)
            return result

        # Tentativa 2: Fallback com snapshot
        logger.warning(f"Normal resume failed for {instance_id}, trying snapshot fallback...")
        result = self._try_snapshot_fallback(instance_id)

        if result.success:
            self._log_scale_up_event(instance_id, result, start)
            return result

        # Tentativa 3: Fallback com migração de disco
        logger.warning(f"Snapshot fallback failed for {instance_id}, trying disk migration...")
        result = self._try_disk_migration(instance_id)

        self._log_scale_up_event(instance_id, result, start)
        return result

    def _try_resume(self, instance_id: str) -> ScaleUpResult:
        """
        Tentativa de resume com cuda-checkpoint (se disponível).

        Fluxo TensorDock:
        1. Start instância
        2. Aguardar running
        3. Restaurar cuda-checkpoint (VRAM + processos)

        Fluxo VAST:
        1. Resume instância
        2. Aguardar running
        """
        start = time.time()
        checkpoint_id = None

        try:
            # Verificar se tem checkpoint salvo
            with self.session_factory() as session:
                repo = ServerlessRepository(session)
                instance = repo.get_instance(instance_id)
                if instance:
                    checkpoint_id = getattr(instance, 'last_checkpoint_id', None)

            # 1. Resume/Start via provider
            success = self.gpu_provider.resume_instance(str(instance_id))

            if not success:
                return ScaleUpResult(
                    success=False,
                    instance_id=instance_id,
                    cold_start_seconds=time.time() - start,
                    method="resume",
                    error=f"{self.provider_type.value} resume failed"
                )

            # 2. Aguardar instância ficar running
            for _ in range(60):  # 60 * 0.5 = 30s timeout
                status = self.gpu_provider.get_instance_status(str(instance_id))
                actual_status = status.get("actual_status", status.get("status", ""))
                if actual_status.lower() in ("running", "active"):
                    break
                time.sleep(0.5)
            else:
                return ScaleUpResult(
                    success=False,
                    instance_id=instance_id,
                    cold_start_seconds=time.time() - start,
                    method="resume",
                    error="Instance did not become running"
                )

            # 3. Restaurar cuda-checkpoint (se disponível)
            if self._checkpoint_service and checkpoint_id and instance:
                logger.info(f"Restaurando cuda-checkpoint: {checkpoint_id}")
                restore_start = time.time()

                restore_result = self._checkpoint_service.restore_checkpoint(
                    instance_id=str(instance_id),
                    ssh_host=instance.ssh_host,
                    ssh_port=instance.ssh_port,
                    checkpoint_id=checkpoint_id,
                )

                if restore_result.get("success"):
                    restore_time = time.time() - restore_start
                    logger.info(f"Checkpoint restaurado em {restore_time:.2f}s")
                else:
                    logger.warning(f"Restore checkpoint falhou: {restore_result.get('error')}")

            # 4. Atualizar estado
            with self.session_factory() as session:
                repo = ServerlessRepository(session)
                repo.update_instance_state(instance_id, InstanceStateEnum.RUNNING)

            return ScaleUpResult(
                success=True,
                instance_id=instance_id,
                cold_start_seconds=time.time() - start,
                method="resume"
            )

        except Exception as e:
            return ScaleUpResult(
                success=False,
                instance_id=instance_id,
                cold_start_seconds=time.time() - start,
                method="resume",
                error=str(e)
            )

    def _try_snapshot_fallback(self, instance_id: int) -> ScaleUpResult:
        """
        Fallback: Restaurar snapshot em nova máquina.

        Usa o FallbackOrchestrator.snapshot_strategy para:
        1. Buscar snapshot mais recente
        2. Buscar GPU similar disponível
        3. Criar nova instância com snapshot
        """
        start = time.time()

        try:
            with self.session_factory() as session:
                repo = ServerlessRepository(session)
                instance = repo.get_instance(instance_id)

                if not instance:
                    return ScaleUpResult(
                        success=False,
                        instance_id=instance_id,
                        cold_start_seconds=time.time() - start,
                        method="snapshot",
                        error="Instance not found in DB"
                    )

                # Usar estratégia de snapshot do orchestrator
                user_settings = repo.get_user_settings(instance.user_id)
                max_price = user_settings.fallback_max_price if user_settings else 1.0

                fallback_result = self._fallback_orchestrator.snapshot_strategy.execute(
                    original_instance_id=instance_id,
                    user_id=instance.user_id,
                    gpu_name=instance.gpu_name,
                    max_price=max_price,
                )

                return ScaleUpResult(
                    success=fallback_result.success,
                    instance_id=instance_id,
                    cold_start_seconds=fallback_result.duration_seconds,
                    method="snapshot",
                    new_instance_id=fallback_result.new_instance_id,
                    error=fallback_result.error
                )

        except Exception as e:
            return ScaleUpResult(
                success=False,
                instance_id=instance_id,
                cold_start_seconds=time.time() - start,
                method="snapshot",
                error=str(e)
            )

    def _try_disk_migration(self, instance_id: int) -> ScaleUpResult:
        """
        Fallback: Migrar disco para nova máquina.

        Usa o FallbackOrchestrator.disk_strategy para:
        1. Obter ID do disco da instância pausada
        2. Buscar GPU disponível
        3. Criar nova instância anexando o disco existente
        """
        start = time.time()

        try:
            with self.session_factory() as session:
                repo = ServerlessRepository(session)
                instance = repo.get_instance(instance_id)

                if not instance:
                    return ScaleUpResult(
                        success=False,
                        instance_id=instance_id,
                        cold_start_seconds=time.time() - start,
                        method="disk_migration",
                        error="Instance not found in DB"
                    )

                # Usar estratégia de disk migration do orchestrator
                user_settings = repo.get_user_settings(instance.user_id)
                max_price = user_settings.fallback_max_price if user_settings else 1.0

                fallback_result = self._fallback_orchestrator.disk_strategy.execute(
                    original_instance_id=instance_id,
                    user_id=instance.user_id,
                    max_price=max_price,
                )

                return ScaleUpResult(
                    success=fallback_result.success,
                    instance_id=instance_id,
                    cold_start_seconds=fallback_result.duration_seconds,
                    method="disk_migration",
                    new_instance_id=fallback_result.new_instance_id,
                    error=fallback_result.error
                )

        except Exception as e:
            return ScaleUpResult(
                success=False,
                instance_id=instance_id,
                cold_start_seconds=time.time() - start,
                method="disk_migration",
                error=str(e)
            )

    def _log_scale_up_event(self, instance_id: int, result: ScaleUpResult, start_time: float):
        """Registra evento de scale up"""
        try:
            with self.session_factory() as session:
                repo = ServerlessRepository(session)
                instance = repo.get_instance(instance_id)

                if instance:
                    event_type = EventTypeEnum.SCALE_UP
                    if not result.success:
                        event_type = EventTypeEnum.RESUME_FAILED
                    elif result.method == "snapshot":
                        event_type = EventTypeEnum.FALLBACK_SNAPSHOT
                    elif result.method == "disk_migration":
                        event_type = EventTypeEnum.FALLBACK_DISK

                    repo.log_event(
                        instance_id=instance.id,
                        user_id=instance.user_id,
                        event_type=event_type,
                        duration_seconds=result.cold_start_seconds,
                        details={
                            "method": result.method,
                            "success": result.success,
                            "error": result.error,
                            "new_instance_id": result.new_instance_id
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to log scale up event: {e}")

    # =========================================================================
    # AUTO-DESTROY
    # =========================================================================

    def _auto_destroy_loop(self):
        """Loop de verificação de auto-destroy"""
        while self._running:
            try:
                self._check_auto_destroy()
            except Exception as e:
                logger.error(f"Error in auto-destroy loop: {e}")
            time.sleep(300)  # Verificar a cada 5 minutos

    def _check_auto_destroy(self):
        """Verifica e destrói instâncias pausadas por muito tempo"""
        with self.session_factory() as session:
            repo = ServerlessRepository(session)
            instances_to_destroy = repo.get_instances_to_destroy()

            for instance in instances_to_destroy:
                logger.info(
                    f"Instance {instance.vast_instance_id} paused for "
                    f"{instance.hours_paused:.1f}h (limit: {instance.destroy_after_hours_paused}h), "
                    "destroying..."
                )
                self._destroy_instance(instance)

    def _destroy_instance(self, instance: ServerlessInstance):
        """Destrói instância pausada por muito tempo"""
        try:
            # Criar snapshot antes de destruir (para possível recovery futuro)
            # TODO: Implementar snapshot antes de destroy

            # Destruir no VAST.ai
            success = self.vast_provider.destroy_instance(instance.vast_instance_id)

            if success:
                with self.session_factory() as session:
                    repo = ServerlessRepository(session)

                    # Atualizar estado
                    repo.update_instance_state(
                        instance.vast_instance_id,
                        InstanceStateEnum.DESTROYED
                    )

                    # Registrar evento
                    repo.log_event(
                        instance_id=instance.id,
                        user_id=instance.user_id,
                        event_type=EventTypeEnum.AUTO_DESTROY,
                        details={
                            "hours_paused": instance.hours_paused,
                            "limit_hours": instance.destroy_after_hours_paused,
                            "total_savings": instance.total_savings_usd
                        }
                    )

                logger.info(f"Instance {instance.vast_instance_id} auto-destroyed")

        except Exception as e:
            logger.error(f"Failed to auto-destroy instance {instance.vast_instance_id}: {e}")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def configure_user(
        self,
        user_id: str,
        scale_down_timeout: Optional[int] = None,
        destroy_after_hours: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Configura settings de serverless para um usuário"""
        with self.session_factory() as session:
            repo = ServerlessRepository(session)
            settings = repo.update_user_settings(
                user_id=user_id,
                scale_down_timeout=scale_down_timeout,
                destroy_after_hours=destroy_after_hours,
                **kwargs
            )
            return {
                "user_id": settings.user_id,
                "scale_down_timeout_seconds": settings.scale_down_timeout_seconds,
                "destroy_after_hours_paused": settings.destroy_after_hours_paused,
                "default_mode": settings.default_mode.value,
                "fallback_enabled": settings.fallback_enabled,
            }

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de uso serverless do usuário"""
        with self.session_factory() as session:
            repo = ServerlessRepository(session)
            return repo.get_user_stats(user_id)

    def enable_for_instance(
        self,
        user_id: str,
        instance_id: int,
        scale_down_timeout: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Habilita serverless para uma instância"""
        with self.session_factory() as session:
            repo = ServerlessRepository(session)

            # Obter info da instância
            status = self.vast_provider.get_instance_status(instance_id)

            # Usar timeout do usuário se não especificado
            if scale_down_timeout is None:
                user_settings = repo.get_or_create_user_settings(user_id)
                scale_down_timeout = user_settings.scale_down_timeout_seconds

            instance = repo.create_instance(
                user_id=user_id,
                vast_instance_id=instance_id,
                scale_down_timeout=scale_down_timeout,
                gpu_name=status.get("gpu_name"),
                hourly_cost=status.get("dph_total", 0),
                ssh_host=status.get("ssh_host"),
                ssh_port=status.get("ssh_port"),
                **kwargs
            )

            # Inicializar timestamp de última requisição
            with self._lock:
                self._last_request[instance_id] = datetime.utcnow()

            return {
                "instance_id": instance_id,
                "scale_down_timeout_seconds": instance.scale_down_timeout_seconds,
                "destroy_after_hours_paused": instance.destroy_after_hours_paused,
                "state": instance.state.value,
            }
