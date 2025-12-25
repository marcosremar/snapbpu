"""
Serverless Module - Fallback Strategies

Estratégias de fallback quando resume falha:
1. Snapshot Restore: Restaurar snapshot em nova máquina
2. Disk Migration: Migrar disco para nova máquina
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class FallbackResult:
    """Resultado de operação de fallback"""
    success: bool
    method: str  # "snapshot" ou "disk_migration"
    new_instance_id: Optional[int] = None
    original_instance_id: Optional[int] = None
    duration_seconds: float = 0
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SnapshotFallbackStrategy:
    """
    Estratégia de fallback usando snapshot.

    Quando resume falha:
    1. Buscar snapshot mais recente válido
    2. Buscar GPU disponível similar
    3. Criar nova instância com o snapshot
    4. Atualizar registros no banco
    """

    def __init__(self, vast_provider, session_factory):
        self.vast_provider = vast_provider
        self.session_factory = session_factory

    def execute(
        self,
        original_instance_id: int,
        user_id: str,
        gpu_name: Optional[str] = None,
        max_price: float = 1.0,
    ) -> FallbackResult:
        """
        Executa fallback com snapshot.

        Args:
            original_instance_id: ID da instância que falhou resume
            user_id: ID do usuário
            gpu_name: Nome da GPU preferida (opcional)
            max_price: Preço máximo por hora

        Returns:
            FallbackResult com detalhes da operação
        """
        start = time.time()

        try:
            from .repository import ServerlessRepository

            with self.session_factory() as session:
                repo = ServerlessRepository(session)

                # 1. Buscar instância original
                instance = repo.get_instance(original_instance_id)
                if not instance:
                    return FallbackResult(
                        success=False,
                        method="snapshot",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error="Original instance not found in database"
                    )

                # 2. Buscar snapshot mais recente
                snapshot = repo.get_latest_snapshot(instance.id)
                if not snapshot or not snapshot.vast_snapshot_id:
                    return FallbackResult(
                        success=False,
                        method="snapshot",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error="No valid snapshot found"
                    )

                logger.info(f"Found snapshot {snapshot.vast_snapshot_id} for fallback")

                # 3. Buscar GPU disponível
                target_gpu = gpu_name or instance.gpu_name or "RTX 4090"

                offers = self.vast_provider.search_offers(
                    gpu_name=target_gpu,
                    max_price_per_hour=max_price,
                    verified=True,
                    limit=5
                )

                if not offers:
                    # Tentar qualquer GPU disponível
                    offers = self.vast_provider.search_offers(
                        max_price_per_hour=max_price,
                        verified=True,
                        limit=5
                    )

                if not offers:
                    return FallbackResult(
                        success=False,
                        method="snapshot",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error=f"No GPU available under ${max_price}/hr"
                    )

                best_offer = offers[0]
                logger.info(f"Found GPU {best_offer.gpu_name} @ ${best_offer.dph_total}/hr for fallback")

                # 4. Criar nova instância com snapshot
                # NOTA: VAST.ai suporta criar instância a partir de template/snapshot
                # via parâmetro template_id ou usando a API de clones
                new_instance_id = self._create_instance_from_snapshot(
                    offer=best_offer,
                    snapshot_id=snapshot.vast_snapshot_id,
                    original_instance=instance,
                )

                if not new_instance_id:
                    return FallbackResult(
                        success=False,
                        method="snapshot",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error="Failed to create new instance from snapshot"
                    )

                # 5. Aguardar nova instância ficar pronta
                if not self._wait_for_running(new_instance_id, timeout=120):
                    return FallbackResult(
                        success=False,
                        method="snapshot",
                        original_instance_id=original_instance_id,
                        new_instance_id=new_instance_id,
                        duration_seconds=time.time() - start,
                        error="New instance did not become running"
                    )

                # 6. Atualizar registros
                self._update_records(
                    session, repo, instance,
                    new_instance_id, best_offer
                )

                duration = time.time() - start
                logger.info(f"Snapshot fallback completed in {duration:.1f}s")

                return FallbackResult(
                    success=True,
                    method="snapshot",
                    original_instance_id=original_instance_id,
                    new_instance_id=new_instance_id,
                    duration_seconds=duration,
                    details={
                        "snapshot_id": snapshot.vast_snapshot_id,
                        "new_gpu": best_offer.gpu_name,
                        "new_cost": best_offer.dph_total,
                    }
                )

        except Exception as e:
            logger.error(f"Snapshot fallback failed: {e}")
            return FallbackResult(
                success=False,
                method="snapshot",
                original_instance_id=original_instance_id,
                duration_seconds=time.time() - start,
                error=str(e)
            )

    def _create_instance_from_snapshot(
        self,
        offer,
        snapshot_id: str,
        original_instance,
    ) -> Optional[int]:
        """Cria nova instância a partir de snapshot"""
        try:
            # VAST.ai permite usar template_id para criar instância com estado salvo
            # Alternativa: usar API de clone se snapshot_id for um template

            # Tentar criar com template
            new_id = self.vast_provider.create_instance(
                offer_id=offer.id,
                template_id=int(snapshot_id) if snapshot_id.isdigit() else None,
                disk=original_instance.disk_space if hasattr(original_instance, 'disk_space') else 50,
                label=f"dumont:fallback:{original_instance.vast_instance_id}",
            )

            return new_id

        except Exception as e:
            logger.error(f"Failed to create instance from snapshot: {e}")
            return None

    def _wait_for_running(self, instance_id: int, timeout: int = 120) -> bool:
        """Aguarda instância ficar running"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                status = self.vast_provider.get_instance_status(instance_id)
                if status.get("actual_status") == "running":
                    return True
            except Exception:
                pass
            time.sleep(5)
        return False

    def _update_records(self, session, repo, old_instance, new_instance_id, offer):
        """Atualiza registros após fallback bem-sucedido"""
        from .models import InstanceStateEnum

        # Marcar instância antiga como destroyed
        repo.update_instance_state(
            old_instance.vast_instance_id,
            InstanceStateEnum.DESTROYED
        )

        # Criar registro para nova instância
        new_instance = repo.create_instance(
            user_id=old_instance.user_id,
            vast_instance_id=new_instance_id,
            mode=old_instance.mode.value,
            scale_down_timeout=old_instance.scale_down_timeout_seconds,
            gpu_name=offer.gpu_name,
            hourly_cost=offer.dph_total,
            destroy_after_hours_paused=old_instance.destroy_after_hours_paused,
        )

        # Copiar métricas acumuladas
        new_instance.total_runtime_seconds = old_instance.total_runtime_seconds
        new_instance.total_paused_seconds = old_instance.total_paused_seconds
        new_instance.total_savings_usd = old_instance.total_savings_usd
        new_instance.fallback_count = old_instance.fallback_count + 1
        session.commit()


class DiskMigrationStrategy:
    """
    Estratégia de fallback usando migração de disco.

    Quando snapshot não está disponível:
    1. Obter ID do disco da instância pausada
    2. Buscar GPU disponível
    3. Criar nova instância anexando o disco existente
    """

    def __init__(self, vast_provider, session_factory):
        self.vast_provider = vast_provider
        self.session_factory = session_factory

    def execute(
        self,
        original_instance_id: int,
        user_id: str,
        max_price: float = 1.0,
    ) -> FallbackResult:
        """
        Executa fallback com migração de disco.

        Args:
            original_instance_id: ID da instância que falhou resume
            user_id: ID do usuário
            max_price: Preço máximo por hora

        Returns:
            FallbackResult com detalhes da operação
        """
        start = time.time()

        try:
            from .repository import ServerlessRepository

            with self.session_factory() as session:
                repo = ServerlessRepository(session)

                # 1. Buscar instância original
                instance = repo.get_instance(original_instance_id)
                if not instance:
                    return FallbackResult(
                        success=False,
                        method="disk_migration",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error="Original instance not found in database"
                    )

                # 2. Obter info do disco
                disk_id = instance.disk_id
                if not disk_id:
                    # Tentar obter da API
                    disk_id = self._get_disk_id(original_instance_id)

                if not disk_id:
                    return FallbackResult(
                        success=False,
                        method="disk_migration",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error="No disk ID found for instance"
                    )

                logger.info(f"Found disk {disk_id} for migration")

                # 3. Buscar GPU disponível
                offers = self.vast_provider.search_offers(
                    gpu_name=instance.gpu_name,
                    max_price_per_hour=max_price,
                    verified=True,
                    limit=5
                )

                if not offers:
                    return FallbackResult(
                        success=False,
                        method="disk_migration",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error="No GPU available for migration"
                    )

                best_offer = offers[0]

                # 4. Criar nova instância com disco anexado
                # NOTA: Esta funcionalidade depende da API do VAST.ai
                # suportar anexar disco existente a nova instância
                new_instance_id = self._create_with_disk(
                    offer=best_offer,
                    disk_id=disk_id,
                    original_instance=instance,
                )

                if not new_instance_id:
                    return FallbackResult(
                        success=False,
                        method="disk_migration",
                        original_instance_id=original_instance_id,
                        duration_seconds=time.time() - start,
                        error="Failed to create instance with migrated disk"
                    )

                duration = time.time() - start
                logger.info(f"Disk migration completed in {duration:.1f}s")

                return FallbackResult(
                    success=True,
                    method="disk_migration",
                    original_instance_id=original_instance_id,
                    new_instance_id=new_instance_id,
                    duration_seconds=duration,
                    details={
                        "disk_id": disk_id,
                        "new_gpu": best_offer.gpu_name,
                    }
                )

        except Exception as e:
            logger.error(f"Disk migration failed: {e}")
            return FallbackResult(
                success=False,
                method="disk_migration",
                original_instance_id=original_instance_id,
                duration_seconds=time.time() - start,
                error=str(e)
            )

    def _get_disk_id(self, instance_id: int) -> Optional[str]:
        """Obtém ID do disco da instância via API"""
        try:
            # VAST.ai não tem endpoint direto para isso
            # Pode ser obtido via instance details ou user disks
            status = self.vast_provider.get_instance_status(instance_id)
            return status.get("disk_id") or status.get("storage_id")
        except Exception:
            return None

    def _create_with_disk(self, offer, disk_id: str, original_instance) -> Optional[int]:
        """Cria nova instância anexando disco existente"""
        try:
            # Esta é uma operação complexa que depende da API do VAST.ai
            # Por enquanto, retornamos None para indicar que não está implementado

            # Quando implementado:
            # new_id = self.vast_provider.create_instance(
            #     offer_id=offer.id,
            #     attach_disk_id=disk_id,
            #     ...
            # )

            logger.warning("Disk migration not yet fully implemented in VAST.ai API")
            return None

        except Exception as e:
            logger.error(f"Failed to create instance with disk: {e}")
            return None


class FallbackOrchestrator:
    """
    Orquestrador de estratégias de fallback.

    Tenta estratégias em ordem de preferência:
    1. Resume normal
    2. Snapshot restore
    3. Disk migration
    """

    def __init__(self, vast_provider, session_factory):
        self.vast_provider = vast_provider
        self.session_factory = session_factory
        self.snapshot_strategy = SnapshotFallbackStrategy(vast_provider, session_factory)
        self.disk_strategy = DiskMigrationStrategy(vast_provider, session_factory)

    def execute_fallback(
        self,
        instance_id: int,
        user_id: str,
        gpu_name: Optional[str] = None,
        max_price: float = 1.0,
        prefer_snapshot: bool = True,
    ) -> FallbackResult:
        """
        Executa fallback com estratégias em ordem.

        Args:
            instance_id: ID da instância que falhou resume
            user_id: ID do usuário
            gpu_name: GPU preferida (opcional)
            max_price: Preço máximo
            prefer_snapshot: Se True, tenta snapshot antes de disk migration

        Returns:
            FallbackResult da primeira estratégia que funcionar
        """
        strategies = []

        if prefer_snapshot:
            strategies = [
                ("snapshot", self.snapshot_strategy),
                ("disk_migration", self.disk_strategy),
            ]
        else:
            strategies = [
                ("disk_migration", self.disk_strategy),
                ("snapshot", self.snapshot_strategy),
            ]

        last_result = None

        for name, strategy in strategies:
            logger.info(f"Attempting fallback strategy: {name}")

            # Snapshot aceita gpu_name, disk_migration não
            if name == "snapshot":
                result = strategy.execute(
                    original_instance_id=instance_id,
                    user_id=user_id,
                    gpu_name=gpu_name,
                    max_price=max_price,
                )
            else:
                result = strategy.execute(
                    original_instance_id=instance_id,
                    user_id=user_id,
                    max_price=max_price,
                )

            if result.success:
                logger.info(f"Fallback strategy {name} succeeded")
                return result

            logger.warning(f"Fallback strategy {name} failed: {result.error}")
            last_result = result

        # Nenhuma estratégia funcionou
        return FallbackResult(
            success=False,
            method="all_failed",
            original_instance_id=instance_id,
            duration_seconds=last_result.duration_seconds if last_result else 0,
            error="All fallback strategies failed"
        )


# Singleton para uso global
_fallback_orchestrator: Optional[FallbackOrchestrator] = None


def get_fallback_orchestrator(
    vast_provider=None,
    session_factory=None
) -> FallbackOrchestrator:
    """Retorna orquestrador de fallback singleton"""
    global _fallback_orchestrator

    if _fallback_orchestrator is None:
        if vast_provider is None or session_factory is None:
            raise ValueError("vast_provider and session_factory required for first call")
        _fallback_orchestrator = FallbackOrchestrator(vast_provider, session_factory)

    return _fallback_orchestrator
