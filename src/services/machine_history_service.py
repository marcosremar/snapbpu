"""
Machine History Service

Serviço para rastrear histórico de tentativas em máquinas e gerenciar blacklist.
Integra com o Wizard para filtrar máquinas problemáticas automaticamente.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.models.machine_history import MachineAttempt, MachineBlacklist, MachineStats
from src.config.database import get_db

logger = logging.getLogger(__name__)


# Configurações de auto-blacklist
BLACKLIST_CONFIG = {
    # Mínimo de tentativas antes de considerar blacklist
    "min_attempts": 3,

    # Taxa de falha mínima para blacklist automático (0.0 a 1.0)
    "failure_rate_threshold": 0.7,  # 70% de falhas

    # Duração padrão do blacklist temporário (em horas)
    "temp_blacklist_hours": 24,

    # Após quantas falhas consecutivas fazer blacklist imediato
    "consecutive_failures_threshold": 3,

    # Estágios de falha graves (blacklist mais rápido)
    "severe_failure_stages": ["rejected", "loading", "creating"],

    # Período para considerar tentativas recentes (em horas)
    "recent_window_hours": 72,  # 3 dias
}


class MachineHistoryService:
    """
    Serviço para gerenciar histórico de máquinas e blacklist.

    Funcionalidades:
    - Registra tentativas de criação de instância
    - Detecta máquinas problemáticas automaticamente
    - Gerencia blacklist (automático e manual)
    - Fornece estatísticas e recomendações
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Inicializa o serviço.

        Args:
            db: Sessão do banco de dados. Se None, será obtida via get_db()
        """
        self._db = db
        self._config = BLACKLIST_CONFIG.copy()

    @property
    def db(self) -> Session:
        """Obtém sessão do banco de dados."""
        if self._db is None:
            self._db = next(get_db())
        return self._db

    # ==================== REGISTRO DE TENTATIVAS ====================

    def record_attempt(
        self,
        provider: str,
        machine_id: str,
        success: bool,
        offer_id: Optional[str] = None,
        gpu_name: Optional[str] = None,
        gpu_count: Optional[int] = None,
        price_per_hour: Optional[float] = None,
        geolocation: Optional[str] = None,
        reliability_score: Optional[float] = None,
        verified: Optional[bool] = None,
        instance_id: Optional[str] = None,
        failure_stage: Optional[str] = None,
        failure_reason: Optional[str] = None,
        time_to_ready_seconds: Optional[float] = None,
        time_to_failure_seconds: Optional[float] = None,
        user_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> MachineAttempt:
        """
        Registra uma tentativa de criação de instância.

        Args:
            provider: Nome do provider (vast, tensordock, etc)
            machine_id: ID da máquina no provider
            success: Se a tentativa foi bem sucedida
            offer_id: ID da oferta específica
            gpu_name: Nome da GPU
            failure_stage: Estágio em que falhou (creating, loading, connecting, rejected)
            failure_reason: Descrição do erro
            time_to_ready_seconds: Tempo até ficar pronta (se sucesso)
            time_to_failure_seconds: Tempo até falhar (se falha)

        Returns:
            MachineAttempt: O registro criado
        """
        attempt = MachineAttempt(
            provider=provider,
            machine_id=str(machine_id),
            offer_id=str(offer_id) if offer_id else None,
            gpu_name=gpu_name,
            gpu_count=gpu_count,
            price_per_hour=price_per_hour,
            geolocation=geolocation,
            reliability_score=reliability_score,
            verified=verified,
            success=success,
            instance_id=str(instance_id) if instance_id else None,
            failure_stage=failure_stage,
            failure_reason=failure_reason[:500] if failure_reason else None,
            time_to_ready_seconds=time_to_ready_seconds,
            time_to_failure_seconds=time_to_failure_seconds,
            user_id=user_id,
            extra_data=extra_data,
        )

        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)

        logger.info(
            f"Recorded attempt: {provider}:{machine_id} - "
            f"{'SUCCESS' if success else f'FAILED ({failure_stage})'}"
        )

        # Atualizar estatísticas e verificar blacklist
        self._update_machine_stats(provider, machine_id)

        if not success:
            self._check_auto_blacklist(provider, machine_id)

        return attempt

    # ==================== BLACKLIST ====================

    def is_blacklisted(self, provider: str, machine_id: str) -> bool:
        """
        Verifica se uma máquina está na blacklist.

        Args:
            provider: Nome do provider
            machine_id: ID da máquina

        Returns:
            bool: True se está blacklisted e ativo
        """
        entry = self.db.query(MachineBlacklist).filter(
            MachineBlacklist.provider == provider,
            MachineBlacklist.machine_id == str(machine_id),
        ).first()

        if entry is None:
            return False

        # Verifica se expirou
        if entry.expires_at and datetime.utcnow() >= entry.expires_at:
            # Remover blacklist expirado
            self.db.delete(entry)
            self.db.commit()
            logger.info(f"Blacklist expired: {provider}:{machine_id}")
            return False

        return True

    def get_blacklist_info(self, provider: str, machine_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações de blacklist de uma máquina.

        Returns:
            Dict com informações ou None se não blacklisted
        """
        entry = self.db.query(MachineBlacklist).filter(
            MachineBlacklist.provider == provider,
            MachineBlacklist.machine_id == str(machine_id),
        ).first()

        if entry and entry.is_active:
            return entry.to_dict()
        return None

    def add_to_blacklist(
        self,
        provider: str,
        machine_id: str,
        reason: str,
        blacklist_type: str = "manual",
        blocked_by: str = "user",
        duration_hours: Optional[int] = None,
        gpu_name: Optional[str] = None,
    ) -> MachineBlacklist:
        """
        Adiciona uma máquina à blacklist manualmente.

        Args:
            provider: Nome do provider
            machine_id: ID da máquina
            reason: Razão do bloqueio
            blacklist_type: Tipo (manual, auto, temporary)
            blocked_by: Quem bloqueou (user_id ou "system")
            duration_hours: Duração em horas (None = permanente)

        Returns:
            MachineBlacklist: O registro criado/atualizado
        """
        # Verificar se já existe
        existing = self.db.query(MachineBlacklist).filter(
            MachineBlacklist.provider == provider,
            MachineBlacklist.machine_id == str(machine_id),
        ).first()

        expires_at = None
        if duration_hours:
            expires_at = datetime.utcnow() + timedelta(hours=duration_hours)

        if existing:
            # Atualizar existente
            existing.blacklist_type = blacklist_type
            existing.reason = reason
            existing.blocked_by = blocked_by
            existing.expires_at = expires_at
            existing.blacklisted_at = datetime.utcnow()
            self.db.commit()
            entry = existing
        else:
            # Criar novo
            entry = MachineBlacklist(
                provider=provider,
                machine_id=str(machine_id),
                blacklist_type=blacklist_type,
                reason=reason,
                blocked_by=blocked_by,
                expires_at=expires_at,
                gpu_name=gpu_name,
            )
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)

        # Atualizar flag nas stats
        self._update_blacklist_flag(provider, machine_id, True)

        logger.warning(
            f"Blacklisted: {provider}:{machine_id} - {reason} "
            f"(type={blacklist_type}, expires={expires_at})"
        )

        return entry

    def remove_from_blacklist(self, provider: str, machine_id: str) -> bool:
        """
        Remove uma máquina da blacklist.

        Returns:
            bool: True se foi removida, False se não estava na lista
        """
        entry = self.db.query(MachineBlacklist).filter(
            MachineBlacklist.provider == provider,
            MachineBlacklist.machine_id == str(machine_id),
        ).first()

        if entry:
            self.db.delete(entry)
            self.db.commit()
            self._update_blacklist_flag(provider, machine_id, False)
            logger.info(f"Removed from blacklist: {provider}:{machine_id}")
            return True

        return False

    def list_blacklist(
        self,
        provider: Optional[str] = None,
        blacklist_type: Optional[str] = None,
        include_expired: bool = False,
    ) -> List[MachineBlacklist]:
        """
        Lista máquinas na blacklist.

        Args:
            provider: Filtrar por provider
            blacklist_type: Filtrar por tipo (auto, manual, temporary)
            include_expired: Incluir blacklists expirados
        """
        query = self.db.query(MachineBlacklist)

        if provider:
            query = query.filter(MachineBlacklist.provider == provider)

        if blacklist_type:
            query = query.filter(MachineBlacklist.blacklist_type == blacklist_type)

        if not include_expired:
            query = query.filter(
                or_(
                    MachineBlacklist.expires_at.is_(None),
                    MachineBlacklist.expires_at > datetime.utcnow()
                )
            )

        return query.order_by(MachineBlacklist.blacklisted_at.desc()).all()

    # ==================== ESTATÍSTICAS ====================

    def get_machine_stats(self, provider: str, machine_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém estatísticas de uma máquina específica.
        """
        stats = self.db.query(MachineStats).filter(
            MachineStats.provider == provider,
            MachineStats.machine_id == str(machine_id),
        ).first()

        if stats:
            return stats.to_dict()
        return None

    def get_problematic_machines(
        self,
        provider: Optional[str] = None,
        min_attempts: int = 3,
        max_success_rate: float = 0.5,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Lista máquinas problemáticas (baixa taxa de sucesso).

        Args:
            provider: Filtrar por provider
            min_attempts: Mínimo de tentativas para considerar
            max_success_rate: Taxa de sucesso máxima (0.0 a 1.0)

        Returns:
            Lista de máquinas com baixa performance
        """
        query = self.db.query(MachineStats).filter(
            MachineStats.total_attempts >= min_attempts,
            MachineStats.success_rate <= max_success_rate,
        )

        if provider:
            query = query.filter(MachineStats.provider == provider)

        stats = query.order_by(MachineStats.success_rate.asc()).limit(limit).all()

        return [s.to_dict() for s in stats]

    def get_reliable_machines(
        self,
        provider: Optional[str] = None,
        min_attempts: int = 5,
        min_success_rate: float = 0.8,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Lista máquinas confiáveis (alta taxa de sucesso).
        """
        query = self.db.query(MachineStats).filter(
            MachineStats.total_attempts >= min_attempts,
            MachineStats.success_rate >= min_success_rate,
            MachineStats.is_blacklisted == False,
        )

        if provider:
            query = query.filter(MachineStats.provider == provider)

        stats = query.order_by(MachineStats.success_rate.desc()).limit(limit).all()

        return [s.to_dict() for s in stats]

    def get_history(
        self,
        provider: Optional[str] = None,
        machine_id: Optional[str] = None,
        success_only: Optional[bool] = None,
        hours: int = 72,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Obtém histórico de tentativas recentes.
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(MachineAttempt).filter(
            MachineAttempt.attempted_at >= since
        )

        if provider:
            query = query.filter(MachineAttempt.provider == provider)

        if machine_id:
            query = query.filter(MachineAttempt.machine_id == str(machine_id))

        if success_only is not None:
            query = query.filter(MachineAttempt.success == success_only)

        attempts = query.order_by(MachineAttempt.attempted_at.desc()).limit(limit).all()

        return [a.to_dict() for a in attempts]

    def get_summary(self, provider: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Obtém resumo de estatísticas.
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(MachineAttempt).filter(
            MachineAttempt.attempted_at >= since
        )

        if provider:
            query = query.filter(MachineAttempt.provider == provider)

        total = query.count()
        successful = query.filter(MachineAttempt.success == True).count()
        failed = query.filter(MachineAttempt.success == False).count()

        # Falhas por estágio
        failure_stages = self.db.query(
            MachineAttempt.failure_stage,
            func.count(MachineAttempt.id)
        ).filter(
            MachineAttempt.attempted_at >= since,
            MachineAttempt.success == False,
        )

        if provider:
            failure_stages = failure_stages.filter(MachineAttempt.provider == provider)

        failure_stages = dict(failure_stages.group_by(MachineAttempt.failure_stage).all())

        # Blacklist ativo
        blacklist_query = self.db.query(MachineBlacklist).filter(
            or_(
                MachineBlacklist.expires_at.is_(None),
                MachineBlacklist.expires_at > datetime.utcnow()
            )
        )

        if provider:
            blacklist_query = blacklist_query.filter(MachineBlacklist.provider == provider)

        blacklist_count = blacklist_query.count()

        return {
            "period_hours": hours,
            "provider": provider or "all",
            "total_attempts": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "failure_stages": failure_stages,
            "blacklisted_machines": blacklist_count,
        }

    # ==================== FILTRAGEM PARA WIZARD ====================

    def filter_offers(
        self,
        offers: List[Dict[str, Any]],
        provider: str,
        exclude_blacklisted: bool = True,
        exclude_low_reliability: bool = True,
        min_success_rate: float = 0.3,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filtra ofertas removendo máquinas problemáticas.

        Esta função é usada pelo Wizard antes de tentar criar instâncias.

        Args:
            offers: Lista de ofertas do provider
            provider: Nome do provider
            exclude_blacklisted: Remover máquinas na blacklist
            exclude_low_reliability: Remover máquinas com baixa taxa de sucesso
            min_success_rate: Taxa mínima de sucesso (para exclude_low_reliability)

        Returns:
            Tuple[filtered_offers, excluded_offers]:
            - filtered_offers: Ofertas filtradas (seguras)
            - excluded_offers: Ofertas removidas com razão
        """
        filtered = []
        excluded = []

        # Cache de blacklist e stats
        blacklisted_ids = set()
        stats_cache = {}

        if exclude_blacklisted:
            blacklist = self.list_blacklist(provider=provider)
            blacklisted_ids = {b.machine_id for b in blacklist}

        if exclude_low_reliability:
            problematic = self.db.query(MachineStats).filter(
                MachineStats.provider == provider,
                MachineStats.total_attempts >= self._config["min_attempts"],
                MachineStats.success_rate < min_success_rate,
            ).all()
            stats_cache = {s.machine_id: s for s in problematic}

        for offer in offers:
            machine_id = str(offer.get("machine_id") or offer.get("id"))

            # Verificar blacklist
            if machine_id in blacklisted_ids:
                offer["_excluded_reason"] = "blacklisted"
                excluded.append(offer)
                continue

            # Verificar baixa confiabilidade
            if machine_id in stats_cache:
                stats = stats_cache[machine_id]
                offer["_excluded_reason"] = f"low_reliability ({stats.success_rate:.0%})"
                offer["_success_rate"] = stats.success_rate
                excluded.append(offer)
                continue

            # Adicionar info de stats se disponível
            machine_stats = self.get_machine_stats(provider, machine_id)
            if machine_stats:
                offer["_machine_stats"] = machine_stats

            filtered.append(offer)

        logger.info(
            f"Filtered offers for {provider}: "
            f"{len(filtered)} passed, {len(excluded)} excluded "
            f"({len(blacklisted_ids)} blacklisted)"
        )

        return filtered, excluded

    def annotate_offers(
        self,
        offers: List[Dict[str, Any]],
        provider: str,
    ) -> List[Dict[str, Any]]:
        """
        Anota ofertas com informações de histórico.

        Usado para mostrar na UI quais máquinas são problemáticas.

        Adiciona campos:
        - _is_blacklisted: bool
        - _blacklist_reason: str
        - _success_rate: float (0.0 a 1.0)
        - _total_attempts: int
        - _reliability_status: str (excellent, good, fair, poor, unknown)
        """
        # Cache de dados
        blacklist_map = {}
        stats_map = {}

        blacklist = self.list_blacklist(provider=provider)
        for b in blacklist:
            blacklist_map[b.machine_id] = b

        all_stats = self.db.query(MachineStats).filter(
            MachineStats.provider == provider
        ).all()
        for s in all_stats:
            stats_map[s.machine_id] = s

        for offer in offers:
            machine_id = str(offer.get("machine_id") or offer.get("id"))

            # Blacklist info
            if machine_id in blacklist_map:
                b = blacklist_map[machine_id]
                offer["_is_blacklisted"] = True
                offer["_blacklist_reason"] = b.reason
                offer["_blacklist_type"] = b.blacklist_type
            else:
                offer["_is_blacklisted"] = False

            # Stats info
            if machine_id in stats_map:
                s = stats_map[machine_id]
                offer["_success_rate"] = s.success_rate
                offer["_total_attempts"] = s.total_attempts
                offer["_reliability_status"] = s.reliability_status
                offer["_avg_time_to_ready"] = s.avg_time_to_ready
            else:
                offer["_success_rate"] = None
                offer["_total_attempts"] = 0
                offer["_reliability_status"] = "unknown"

        return offers

    # ==================== MÉTODOS PRIVADOS ====================

    def _update_machine_stats(self, provider: str, machine_id: str):
        """Atualiza estatísticas agregadas de uma máquina."""
        # Buscar todas as tentativas
        attempts = self.db.query(MachineAttempt).filter(
            MachineAttempt.provider == provider,
            MachineAttempt.machine_id == str(machine_id),
        ).all()

        if not attempts:
            return

        # Calcular estatísticas
        total = len(attempts)
        successful = sum(1 for a in attempts if a.success)
        failed = total - successful
        success_rate = successful / total if total > 0 else 0

        # Tempos médios
        ready_times = [a.time_to_ready_seconds for a in attempts if a.time_to_ready_seconds]
        failure_times = [a.time_to_failure_seconds for a in attempts if a.time_to_failure_seconds]

        avg_time_to_ready = sum(ready_times) / len(ready_times) if ready_times else None
        avg_time_to_failure = sum(failure_times) / len(failure_times) if failure_times else None

        # Timestamps (filter out None values)
        valid_timestamps = [a.attempted_at for a in attempts if a.attempted_at is not None]
        first_seen = min(valid_timestamps) if valid_timestamps else None
        last_seen = max(valid_timestamps) if valid_timestamps else None

        successes = [a for a in attempts if a.success]
        failures = [a for a in attempts if not a.success]

        success_timestamps = [a.attempted_at for a in successes if a.attempted_at is not None]
        failure_timestamps = [a.attempted_at for a in failures if a.attempted_at is not None]

        last_success = max(success_timestamps) if success_timestamps else None
        last_failure = max(failure_timestamps) if failure_timestamps else None

        # Info da máquina (do último attempt com timestamp válido, ou o primeiro)
        attempts_with_ts = [a for a in attempts if a.attempted_at is not None]
        latest = max(attempts_with_ts, key=lambda a: a.attempted_at) if attempts_with_ts else attempts[0]

        # Buscar ou criar stats
        stats = self.db.query(MachineStats).filter(
            MachineStats.provider == provider,
            MachineStats.machine_id == str(machine_id),
        ).first()

        if stats:
            stats.total_attempts = total
            stats.successful_attempts = successful
            stats.failed_attempts = failed
            stats.success_rate = success_rate
            stats.avg_time_to_ready = avg_time_to_ready
            stats.avg_time_to_failure = avg_time_to_failure
            stats.first_seen = first_seen
            stats.last_seen = last_seen
            stats.last_success = last_success
            stats.last_failure = last_failure
            stats.gpu_name = latest.gpu_name
            stats.geolocation = latest.geolocation
            stats.verified = latest.verified
        else:
            stats = MachineStats(
                provider=provider,
                machine_id=str(machine_id),
                total_attempts=total,
                successful_attempts=successful,
                failed_attempts=failed,
                success_rate=success_rate,
                avg_time_to_ready=avg_time_to_ready,
                avg_time_to_failure=avg_time_to_failure,
                first_seen=first_seen,
                last_seen=last_seen,
                last_success=last_success,
                last_failure=last_failure,
                gpu_name=latest.gpu_name,
                geolocation=latest.geolocation,
                verified=latest.verified,
            )
            self.db.add(stats)

        self.db.commit()

    def _check_auto_blacklist(self, provider: str, machine_id: str):
        """
        Verifica se a máquina deve ser adicionada à blacklist automaticamente.

        Critérios:
        1. Taxa de falha >= threshold após N tentativas
        2. N falhas consecutivas
        3. Falha em estágios graves (rejected, etc)
        """
        # Já está blacklisted?
        if self.is_blacklisted(provider, machine_id):
            return

        # Buscar tentativas recentes
        since = datetime.utcnow() - timedelta(hours=self._config["recent_window_hours"])
        recent_attempts = self.db.query(MachineAttempt).filter(
            MachineAttempt.provider == provider,
            MachineAttempt.machine_id == str(machine_id),
            MachineAttempt.attempted_at >= since,
        ).order_by(MachineAttempt.attempted_at.desc()).all()

        if len(recent_attempts) < self._config["min_attempts"]:
            return

        # Verificar falhas consecutivas
        consecutive_failures = 0
        for attempt in recent_attempts:
            if not attempt.success:
                consecutive_failures += 1
            else:
                break

        if consecutive_failures >= self._config["consecutive_failures_threshold"]:
            self.add_to_blacklist(
                provider=provider,
                machine_id=machine_id,
                reason=f"{consecutive_failures} falhas consecutivas",
                blacklist_type="auto",
                blocked_by="system",
                duration_hours=self._config["temp_blacklist_hours"],
                gpu_name=recent_attempts[0].gpu_name if recent_attempts else None,
            )
            return

        # Verificar taxa de falha
        total = len(recent_attempts)
        failed = sum(1 for a in recent_attempts if not a.success)
        failure_rate = failed / total

        if failure_rate >= self._config["failure_rate_threshold"]:
            # Verificar se tem falhas graves
            severe_failures = [
                a for a in recent_attempts
                if not a.success and a.failure_stage in self._config["severe_failure_stages"]
            ]

            if severe_failures:
                self.add_to_blacklist(
                    provider=provider,
                    machine_id=machine_id,
                    reason=f"Taxa de falha {failure_rate:.0%} ({failed}/{total}) com falhas graves",
                    blacklist_type="auto",
                    blocked_by="system",
                    duration_hours=self._config["temp_blacklist_hours"] * 2,  # Mais tempo
                    gpu_name=recent_attempts[0].gpu_name if recent_attempts else None,
                )
            else:
                self.add_to_blacklist(
                    provider=provider,
                    machine_id=machine_id,
                    reason=f"Taxa de falha {failure_rate:.0%} ({failed}/{total})",
                    blacklist_type="auto",
                    blocked_by="system",
                    duration_hours=self._config["temp_blacklist_hours"],
                    gpu_name=recent_attempts[0].gpu_name if recent_attempts else None,
                )

            # Atualizar stats com info de blacklist
            stats = self.db.query(MachineStats).filter(
                MachineStats.provider == provider,
                MachineStats.machine_id == str(machine_id),
            ).first()

            if stats:
                stats.is_blacklisted = True
                self.db.commit()

    def _update_blacklist_flag(self, provider: str, machine_id: str, is_blacklisted: bool):
        """Atualiza flag de blacklist nas stats."""
        stats = self.db.query(MachineStats).filter(
            MachineStats.provider == provider,
            MachineStats.machine_id == str(machine_id),
        ).first()

        if stats:
            stats.is_blacklisted = is_blacklisted
            self.db.commit()


# Singleton global
_service_instance: Optional[MachineHistoryService] = None


def get_machine_history_service(db: Optional[Session] = None) -> MachineHistoryService:
    """
    Obtém instância do serviço de histórico de máquinas.

    Usage:
        service = get_machine_history_service()
        service.record_attempt(...)
    """
    global _service_instance

    if _service_instance is None or db is not None:
        _service_instance = MachineHistoryService(db)

    return _service_instance
