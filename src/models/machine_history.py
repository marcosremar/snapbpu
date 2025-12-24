"""
Machine History & Blacklist Models

Rastreia tentativas de criação de instâncias e máquinas problemáticas.
Usado para evitar máquinas que falham consistentemente.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, Index, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from src.config.database import Base


class MachineAttempt(Base):
    """
    Histórico de tentativas de criação de instância em uma máquina.

    Cada vez que tentamos criar uma instância, registramos o resultado
    para poder identificar máquinas problemáticas.
    """
    __tablename__ = "machine_attempts"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação da máquina
    provider = Column(String(50), nullable=False, index=True)  # vast, tensordock, etc
    machine_id = Column(String(100), nullable=False, index=True)  # ID no provider
    offer_id = Column(String(100), nullable=True)  # ID da oferta específica

    # Detalhes da máquina
    gpu_name = Column(String(100), nullable=True)
    gpu_count = Column(Integer, nullable=True)
    price_per_hour = Column(Float, nullable=True)
    geolocation = Column(String(100), nullable=True)
    reliability_score = Column(Float, nullable=True)  # Score do provider
    verified = Column(Boolean, nullable=True)  # Se é máquina verificada

    # Resultado da tentativa
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=False)
    instance_id = Column(String(100), nullable=True)  # ID da instância criada (se sucesso)

    # Detalhes do resultado
    failure_stage = Column(String(50), nullable=True)  # creating, loading, connecting, rejected
    failure_reason = Column(String(500), nullable=True)
    time_to_ready_seconds = Column(Float, nullable=True)  # Tempo até ficar running
    time_to_failure_seconds = Column(Float, nullable=True)  # Tempo até falhar

    # Metadados
    user_id = Column(String(100), nullable=True)  # Usuário que tentou
    extra_data = Column(JSON, nullable=True)  # Dados adicionais

    __table_args__ = (
        Index('idx_machine_attempt_provider_machine', 'provider', 'machine_id'),
        Index('idx_machine_attempt_time', 'attempted_at'),
        Index('idx_machine_attempt_success', 'success', 'attempted_at'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "machine_id": self.machine_id,
            "offer_id": self.offer_id,
            "gpu_name": self.gpu_name,
            "price_per_hour": self.price_per_hour,
            "attempted_at": self.attempted_at.isoformat() if self.attempted_at else None,
            "success": self.success,
            "instance_id": self.instance_id,
            "failure_stage": self.failure_stage,
            "failure_reason": self.failure_reason,
            "time_to_ready_seconds": self.time_to_ready_seconds,
        }

    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"<MachineAttempt {status} {self.provider}:{self.machine_id} @ {self.attempted_at}>"


class MachineBlacklist(Base):
    """
    Lista de máquinas bloqueadas.

    Máquinas com muitas falhas são automaticamente adicionadas aqui.
    Também suporta blacklist manual.
    """
    __tablename__ = "machine_blacklist"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação
    provider = Column(String(50), nullable=False)
    machine_id = Column(String(100), nullable=False)

    # Configuração do bloqueio
    blacklist_type = Column(String(30), nullable=False, default="auto")  # auto, manual, temporary

    # Estatísticas que levaram ao bloqueio
    total_attempts = Column(Integer, default=0)
    failed_attempts = Column(Integer, default=0)
    failure_rate = Column(Float, default=0.0)  # 0.0 a 1.0
    last_failure_reason = Column(String(500), nullable=True)

    # Timestamps
    first_failure_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    blacklisted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # NULL = permanente

    # Metadados
    reason = Column(String(500), nullable=True)  # Razão manual ou automática
    blocked_by = Column(String(100), nullable=True)  # user_id ou "system"
    gpu_name = Column(String(100), nullable=True)  # Para referência

    __table_args__ = (
        Index('idx_blacklist_provider_machine', 'provider', 'machine_id', unique=True),
        Index('idx_blacklist_expires', 'expires_at'),
        Index('idx_blacklist_type', 'blacklist_type'),
    )

    @property
    def is_active(self) -> bool:
        """Verifica se o bloqueio ainda está ativo."""
        if self.expires_at is None:
            return True
        return datetime.utcnow() < self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "machine_id": self.machine_id,
            "blacklist_type": self.blacklist_type,
            "total_attempts": self.total_attempts,
            "failed_attempts": self.failed_attempts,
            "failure_rate": self.failure_rate,
            "last_failure_reason": self.last_failure_reason,
            "blacklisted_at": self.blacklisted_at.isoformat() if self.blacklisted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "reason": self.reason,
            "gpu_name": self.gpu_name,
        }

    def __repr__(self):
        status = "ACTIVE" if self.is_active else "EXPIRED"
        return f"<MachineBlacklist [{status}] {self.provider}:{self.machine_id}>"


class MachineStats(Base):
    """
    Estatísticas agregadas por máquina.

    View materializada das tentativas para consulta rápida.
    Atualizada periodicamente ou on-demand.
    """
    __tablename__ = "machine_stats"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação
    provider = Column(String(50), nullable=False)
    machine_id = Column(String(100), nullable=False)

    # Estatísticas
    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    failed_attempts = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # 0.0 a 1.0

    # Tempos médios
    avg_time_to_ready = Column(Float, nullable=True)  # segundos
    avg_time_to_failure = Column(Float, nullable=True)  # segundos

    # Última atividade
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)

    # Informações da máquina (cache)
    gpu_name = Column(String(100), nullable=True)
    geolocation = Column(String(100), nullable=True)
    verified = Column(Boolean, nullable=True)

    # Status
    is_blacklisted = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_stats_provider_machine', 'provider', 'machine_id', unique=True),
        Index('idx_stats_success_rate', 'success_rate'),
        Index('idx_stats_blacklisted', 'is_blacklisted'),
    )

    @property
    def reliability_status(self) -> str:
        """Retorna status de confiabilidade baseado na taxa de sucesso."""
        if self.total_attempts < 3:
            return "unknown"
        if self.success_rate >= 0.9:
            return "excellent"
        if self.success_rate >= 0.7:
            return "good"
        if self.success_rate >= 0.5:
            return "fair"
        return "poor"

    def to_dict(self):
        return {
            "provider": self.provider,
            "machine_id": self.machine_id,
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": self.success_rate,
            "avg_time_to_ready": self.avg_time_to_ready,
            "reliability_status": self.reliability_status,
            "is_blacklisted": self.is_blacklisted,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "gpu_name": self.gpu_name,
        }

    def __repr__(self):
        return f"<MachineStats {self.provider}:{self.machine_id} {self.success_rate:.1%}>"


class OfferStability(Base):
    """
    Rastreia estabilidade de ofertas de máquinas.

    Monitora quando ofertas aparecem e desaparecem do mercado.
    Máquinas que somem/aparecem frequentemente são consideradas instáveis.

    Usado para filtrar ofertas spot que têm alta probabilidade de serem
    interrompidas rapidamente (porque outro usuário pagou mais).
    """
    __tablename__ = "offer_stability"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação
    provider = Column(String(50), nullable=False)
    machine_id = Column(String(100), nullable=False)
    offer_id = Column(String(100), nullable=True)

    # Detalhes da máquina (cache)
    gpu_name = Column(String(100), nullable=True)
    gpu_count = Column(Integer, default=1)
    price_per_hour = Column(Float, nullable=True)
    geolocation = Column(String(100), nullable=True)
    machine_type = Column(String(30), nullable=True)  # on-demand, interruptible

    # Contadores de aparições/desaparecimentos
    times_appeared = Column(Integer, default=0)  # Quantas vezes apareceu
    times_disappeared = Column(Integer, default=0)  # Quantas vezes sumiu

    # Tempo de disponibilidade
    total_available_seconds = Column(Integer, default=0)  # Tempo total disponível
    longest_available_seconds = Column(Integer, default=0)  # Maior período contínuo
    shortest_available_seconds = Column(Integer, default=0)  # Menor período contínuo
    avg_available_seconds = Column(Float, default=0.0)  # Média de disponibilidade

    # Tracking atual
    is_available = Column(Boolean, default=False)  # Disponível agora?
    last_seen_at = Column(DateTime, nullable=True)  # Última vez vista
    first_seen_at = Column(DateTime, nullable=True)  # Primeira vez vista
    current_session_start = Column(DateTime, nullable=True)  # Início da sessão atual

    # Score de estabilidade (0.0 a 1.0)
    # 1.0 = muito estável (fica disponível por muito tempo)
    # 0.0 = muito instável (aparece e some frequentemente)
    stability_score = Column(Float, default=0.5)

    # Configurações de filtro
    is_unstable = Column(Boolean, default=False)  # Flag: muito instável
    exclude_from_default = Column(Boolean, default=False)  # Não mostrar por padrão

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_stability_provider_machine', 'provider', 'machine_id'),
        Index('idx_stability_score', 'stability_score'),
        Index('idx_stability_unstable', 'is_unstable'),
        Index('idx_stability_exclude', 'exclude_from_default'),
        Index('idx_stability_available', 'is_available'),
    )

    # Configurações de estabilidade
    STABILITY_CONFIG = {
        # Mínimo de aparições para calcular score
        "min_appearances": 3,
        # Tempo mínimo de disponibilidade para ser estável (em segundos)
        "min_stable_duration_seconds": 3600,  # 1 hora
        # Score abaixo deste é considerado instável
        "unstable_threshold": 0.3,
        # Peso do tempo médio de disponibilidade no score
        "avg_duration_weight": 0.6,
        # Peso da frequência de aparições no score
        "frequency_weight": 0.4,
    }

    def calculate_stability_score(self) -> float:
        """
        Calcula score de estabilidade.

        Baseado em:
        1. Tempo médio de disponibilidade (quanto mais, melhor)
        2. Frequência de aparições/desaparecimentos (quanto menos, melhor)

        Returns:
            float: Score entre 0.0 (instável) e 1.0 (estável)
        """
        if self.times_appeared < self.STABILITY_CONFIG["min_appearances"]:
            return 0.5  # Score neutro para máquinas novas

        # Score baseado em duração média
        min_stable = self.STABILITY_CONFIG["min_stable_duration_seconds"]
        duration_score = min(1.0, self.avg_available_seconds / min_stable) if self.avg_available_seconds else 0

        # Score baseado em frequência (menos aparições = mais estável)
        # Se apareceu muitas vezes em pouco tempo, é instável
        if self.first_seen_at:
            hours_tracked = (datetime.utcnow() - self.first_seen_at).total_seconds() / 3600
            if hours_tracked > 0:
                appearances_per_hour = self.times_appeared / hours_tracked
                # Menos de 1 aparição por hora é bom
                frequency_score = max(0, 1 - (appearances_per_hour / 2))
            else:
                frequency_score = 0.5
        else:
            frequency_score = 0.5

        # Score combinado
        w_duration = self.STABILITY_CONFIG["avg_duration_weight"]
        w_frequency = self.STABILITY_CONFIG["frequency_weight"]
        score = (duration_score * w_duration) + (frequency_score * w_frequency)

        return round(max(0.0, min(1.0, score)), 3)

    def update_stability(self) -> None:
        """Atualiza score e flags de estabilidade."""
        self.stability_score = self.calculate_stability_score()
        self.is_unstable = self.stability_score < self.STABILITY_CONFIG["unstable_threshold"]
        self.exclude_from_default = self.is_unstable
        self.updated_at = datetime.utcnow()

    def record_appeared(self, price: float = None, gpu_name: str = None, geolocation: str = None) -> None:
        """Registra que a oferta apareceu no mercado."""
        now = datetime.utcnow()

        # Garantir que campos int estão inicializados
        if self.times_appeared is None:
            self.times_appeared = 0
        if self.times_disappeared is None:
            self.times_disappeared = 0
        if self.total_available_seconds is None:
            self.total_available_seconds = 0
        if self.longest_available_seconds is None:
            self.longest_available_seconds = 0
        if self.shortest_available_seconds is None:
            self.shortest_available_seconds = 0

        self.times_appeared += 1
        self.is_available = True
        self.last_seen_at = now
        self.current_session_start = now

        if not self.first_seen_at:
            self.first_seen_at = now

        if price:
            self.price_per_hour = price
        if gpu_name:
            self.gpu_name = gpu_name
        if geolocation:
            self.geolocation = geolocation

        self.update_stability()

    def record_disappeared(self) -> None:
        """Registra que a oferta desapareceu do mercado."""
        now = datetime.utcnow()

        # Garantir que campos int estão inicializados
        if self.times_appeared is None:
            self.times_appeared = 0
        if self.times_disappeared is None:
            self.times_disappeared = 0
        if self.total_available_seconds is None:
            self.total_available_seconds = 0
        if self.longest_available_seconds is None:
            self.longest_available_seconds = 0
        if self.shortest_available_seconds is None:
            self.shortest_available_seconds = 0

        self.times_disappeared += 1
        self.is_available = False

        # Calcular duração desta sessão
        if self.current_session_start:
            session_duration = int((now - self.current_session_start).total_seconds())
            self.total_available_seconds += session_duration

            if session_duration > self.longest_available_seconds:
                self.longest_available_seconds = session_duration

            if self.shortest_available_seconds == 0 or session_duration < self.shortest_available_seconds:
                self.shortest_available_seconds = session_duration

            # Atualizar média
            if self.times_disappeared > 0:
                self.avg_available_seconds = self.total_available_seconds / self.times_disappeared

        self.current_session_start = None
        self.update_stability()

    @property
    def stability_status(self) -> str:
        """Retorna status legível da estabilidade."""
        if self.times_appeared < self.STABILITY_CONFIG["min_appearances"]:
            return "new"
        if self.stability_score >= 0.8:
            return "very_stable"
        if self.stability_score >= 0.5:
            return "stable"
        if self.stability_score >= 0.3:
            return "moderate"
        return "unstable"

    @property
    def avg_available_minutes(self) -> float:
        """Retorna tempo médio de disponibilidade em minutos."""
        return round(self.avg_available_seconds / 60, 1) if self.avg_available_seconds else 0

    def to_dict(self):
        return {
            "provider": self.provider,
            "machine_id": self.machine_id,
            "gpu_name": self.gpu_name,
            "price_per_hour": self.price_per_hour,
            "geolocation": self.geolocation,
            "times_appeared": self.times_appeared,
            "times_disappeared": self.times_disappeared,
            "avg_available_minutes": self.avg_available_minutes,
            "longest_available_seconds": self.longest_available_seconds,
            "stability_score": self.stability_score,
            "stability_status": self.stability_status,
            "is_unstable": self.is_unstable,
            "is_available": self.is_available,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }

    def __repr__(self):
        return f"<OfferStability {self.provider}:{self.machine_id} score={self.stability_score:.2f} [{self.stability_status}]>"
