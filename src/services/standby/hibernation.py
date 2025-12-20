"""
Auto Hibernation Manager - Gerencia hibernação automática de instâncias GPU

Roda como agente em background no servidor de controle (VPS).
Monitora status de todas as instâncias e automatically:
- Hiberna GPUs ociosas > 3 min
- Deleta instâncias hibernadas > 30 min (mantém snapshot)
- Acorda instâncias sob demanda

Integra com:
- GPUSnapshotService (criar/restaurar snapshots ANS)
- VastService (criar/destruir instâncias)
- Database (InstanceStatus, HibernationEvent)
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.services.agent_manager import Agent
from src.services.gpu.snapshot import GPUSnapshotService
from src.services.gpu.vast import VastService
from src.config.database import SessionLocal
from src.models.instance_status import InstanceStatus, HibernationEvent
from src.services.usage_service import UsageService

logger = logging.getLogger(__name__)


class AutoHibernationManager(Agent):
    """Gerenciador de auto-hibernação de instâncias GPU."""

    def __init__(
        self,
        vast_api_key: str,
        r2_endpoint: str,
        r2_bucket: str,
        check_interval: int = 30
    ):
        """
        Inicializa o manager de auto-hibernação.

        Args:
            vast_api_key: API key da Vast.ai
            r2_endpoint: Endpoint do Cloudflare R2
            r2_bucket: Nome do bucket R2
            check_interval: Intervalo de verificação em segundos (padrão: 30)
        """
        super().__init__(name="AutoHibernation")

        self.vast_service = VastService(api_key=vast_api_key)
        self.snapshot_service = GPUSnapshotService(r2_endpoint, r2_bucket)
        self.check_interval = check_interval

        logger.info(f"AutoHibernationManager inicializado (interval={check_interval}s)")

    def run(self):
        """Loop principal do agente."""
        logger.info("Iniciando loop de auto-hibernação...")

        while self.running:
            try:
                self._check_all_instances()
            except Exception as e:
                logger.error(f"Erro no ciclo de verificação: {e}", exc_info=True)

            # Aguardar próximo ciclo (sleep interrompível)
            if self.running:
                self.sleep(self.check_interval)

        logger.info("Loop de auto-hibernação finalizado")

    def _check_all_instances(self):
        """Verifica status de todas as instâncias e aplica políticas de hibernação."""
        db = SessionLocal()
        try:
            # Buscar todas as instâncias ativas
            instances = db.query(InstanceStatus).filter(
                InstanceStatus.auto_hibernation_enabled == True
            ).all()

            logger.debug(f"Verificando {len(instances)} instâncias...")

            for instance in instances:
                try:
                    self._check_instance(db, instance)
                except Exception as e:
                    logger.error(f"Erro ao verificar instância {instance.instance_id}: {e}")

            db.commit()

        except Exception as e:
            logger.error(f"Erro ao buscar instâncias: {e}")
            db.rollback()
        finally:
            db.close()

    def _check_instance(self, db, instance: InstanceStatus):
        """
        Verifica uma instância e aplica política de hibernação.

        Args:
            db: Sessão do banco de dados
            instance: Instância a verificar
        """
        now = datetime.utcnow()

        # 1. Verificar se deve hibernar (ociosa > threshold)
        if instance.status == "idle":
            idle_duration = (now - instance.idle_since).total_seconds() / 60  # minutos

            if idle_duration >= instance.pause_after_minutes:
                logger.info(f"Instância {instance.instance_id} ociosa por {idle_duration:.1f} min - hibernando...")
                self._hibernate_instance(db, instance)
                return

        # 2. Verificar se deve deletar instância hibernada
        if instance.status == "hibernated" and instance.hibernated_at:
            hibernated_duration = (now - instance.hibernated_at).total_seconds() / 60

            if hibernated_duration >= instance.delete_after_minutes:
                logger.info(f"Instância {instance.instance_id} hibernada por {hibernated_duration:.1f} min - marcando como deleted...")
                self._mark_instance_deleted(db, instance)
                return

        # 3. Verificar heartbeat - se não recebe status há muito tempo, marcar como unknown
        if instance.last_heartbeat:
            heartbeat_age = (now - instance.last_heartbeat).total_seconds() / 60

            if heartbeat_age > 5 and instance.status == "running":  # 5 min sem heartbeat
                logger.warning(f"Instância {instance.instance_id} sem heartbeat há {heartbeat_age:.1f} min")
                instance.status = "unknown"
                db.commit()

    def _hibernate_instance(self, db, instance: InstanceStatus):
        """
        Hiberna uma instância (snapshot + destroy).

        Args:
            db: Sessão do banco de dados
            instance: Instância a hibernar
        """
        try:
            logger.info(f"=== Hibernando instância {instance.instance_id} ===")

            # 1. Criar snapshot
            logger.info(f"  [1/3] Criando snapshot...")
            snapshot_info = self.snapshot_service.create_snapshot(
                instance_id=instance.instance_id,
                ssh_host=instance.ssh_host,
                ssh_port=instance.ssh_port,
                workspace_path="/workspace",
                snapshot_name=f"{instance.instance_id}_hibernate_{int(time.time())}"
            )

            snapshot_id = snapshot_info['snapshot_id']
            logger.info(f"  ✓ Snapshot criado: {snapshot_id}")

            # 2. Destruir instância vast.ai
            if instance.vast_instance_id:
                logger.info(f"  [2/3] Destruindo instância vast.ai {instance.vast_instance_id}...")
                success = self.vast_service.destroy_instance(instance.vast_instance_id)

                if success:
                    logger.info(f"  ✓ Instância vast.ai destruída")
                else:
                    logger.warning(f"  ⚠ Falha ao destruir instância vast.ai (pode já estar destruída)")

            # 3. Atualizar status no DB
            logger.info(f"  [3/3] Atualizando status no banco...")
            instance.status = "hibernated"
            instance.hibernated_at = datetime.utcnow()
            instance.snapshot_id = snapshot_id
            instance.last_snapshot_id = snapshot_id
            
            # Parar tracking de uso
            usage_service = UsageService(db)
            usage_service.stop_usage(instance.instance_id)
            
            # Calcular economia: horas desde idle × preço/hora
            idle_hours = 0.0
            savings_usd = 0.0
            dph_total = 0.0
            
            if instance.idle_since:
                idle_duration = datetime.utcnow() - instance.idle_since
                idle_hours = idle_duration.total_seconds() / 3600
                
                # Buscar preço da instância (estimativa se não disponível)
                try:
                    vast_info = self.vast_service.get_instance_status(instance.vast_instance_id)
                    if vast_info and 'dph_total' in vast_info:
                        dph_total = vast_info['dph_total']
                except:
                    # Estimativa baseada no tipo de GPU
                    gpu_prices = {
                        'RTX 4090': 0.40, 'RTX 3090': 0.25, 'RTX 3080': 0.20,
                        'A100': 1.50, 'H100': 3.00, 'A6000': 0.60
                    }
                    dph_total = gpu_prices.get(instance.gpu_type, 0.30)
                
                savings_usd = idle_hours * dph_total
            
            instance.idle_since = None

            # Registrar evento com economia
            event = HibernationEvent(
                instance_id=instance.instance_id,
                event_type="hibernated",
                gpu_utilization=instance.gpu_utilization,
                snapshot_id=snapshot_id,
                reason=f"GPU ociosa por {instance.pause_after_minutes} minutos",
                dph_total=dph_total,
                idle_hours=idle_hours,
                savings_usd=savings_usd
            )
            db.add(event)
            db.commit()

            logger.info(f"=== Hibernação concluída: {instance.instance_id} ===")

        except Exception as e:
            logger.error(f"Erro ao hibernar instância {instance.instance_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def _mark_instance_deleted(self, db, instance: InstanceStatus):
        """
        Marca instância como deletada (mantém snapshot no R2).

        Args:
            db: Sessão do banco de dados
            instance: Instância a marcar como deletada
        """
        try:
            logger.info(f"Marcando instância {instance.instance_id} como deleted")

            instance.status = "deleted"

            # Registrar evento
            event = HibernationEvent(
                instance_id=instance.instance_id,
                event_type="deleted",
                snapshot_id=instance.snapshot_id,
                reason=f"Instância hibernada por {instance.delete_after_minutes} minutos"
            )
            db.add(event)
            db.commit()

            logger.info(f"✓ Instância {instance.instance_id} marcada como deleted (snapshot mantido)")

        except Exception as e:
            logger.error(f"Erro ao marcar instância como deleted: {e}")
            db.rollback()

    def wake_instance(
        self,
        instance_id: str,
        gpu_type: Optional[str] = None,
        region: Optional[str] = None,
        max_price: float = 1.0
    ) -> Dict:
        """
        Acorda uma instância hibernada (create + restore).

        Args:
            instance_id: ID da instância
            gpu_type: Tipo de GPU desejado (ex: "RTX 3090")
            region: Região desejada (ex: "EU")
            max_price: Preço máximo por hora

        Returns:
            {
                'success': bool,
                'instance_id': str,
                'vast_instance_id': int,
                'ssh_host': str,
                'ssh_port': int,
                'snapshot_restored': bool,
                'time_taken': float
            }
        """
        db = SessionLocal()
        try:
            start_time = time.time()

            # Buscar instância no DB
            instance = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()

            if not instance:
                raise ValueError(f"Instância {instance_id} não encontrada")

            if instance.status not in ["hibernated", "deleted"]:
                raise ValueError(f"Instância {instance_id} não está hibernada (status: {instance.status})")

            if not instance.snapshot_id:
                raise ValueError(f"Instância {instance_id} não possui snapshot")

            logger.info(f"=== Acordando instância {instance_id} ===")

            # Usar configurações salvas se não especificadas
            gpu_type = gpu_type or instance.gpu_type or "RTX 3090"
            region = region or instance.region

            # 1. Buscar ofertas disponíveis
            logger.info(f"  [1/4] Buscando ofertas {gpu_type} em {region}...")
            offers = self.vast_service.search_offers(
                gpu_name=gpu_type,
                region=region,
                max_price=max_price,
                limit=10
            )

            if not offers:
                raise Exception(f"Nenhuma oferta disponível para {gpu_type} em {region}")

            logger.info(f"  ✓ Encontradas {len(offers)} ofertas")

            # 2. Criar instância
            logger.info(f"  [2/4] Criando instância vast.ai...")
            offer_id = offers[0]['id']

            new_vast_id = self.vast_service.create_instance(
                offer_id=offer_id,
                image="nvidia/cuda:12.0.0-devel-ubuntu22.04",
                disk=100
            )

            if not new_vast_id:
                raise Exception("Falha ao criar instância vast.ai")

            logger.info(f"  ✓ Instância criada: {new_vast_id}")

            # 3. Aguardar instância ficar pronta
            logger.info(f"  [3/4] Aguardando instância ficar pronta...")
            max_wait = 180  # 3 minutos
            wait_start = time.time()

            while time.time() - wait_start < max_wait:
                status = self.vast_service.get_instance_status(new_vast_id)

                if status.get('status') == 'running' and status.get('ssh_host'):
                    ssh_host = status['ssh_host']
                    ssh_port = status['ssh_port']
                    logger.info(f"  ✓ Instância pronta: {ssh_host}:{ssh_port}")
                    break

                time.sleep(5)
            else:
                raise Exception(f"Timeout aguardando instância ficar pronta")

            # 4. Restaurar snapshot
            logger.info(f"  [4/4] Restaurando snapshot {instance.snapshot_id}...")
            restore_info = self.snapshot_service.restore_snapshot(
                snapshot_id=instance.snapshot_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                workspace_path="/workspace"
            )

            logger.info(f"  ✓ Snapshot restaurado em {restore_info['total_time']:.1f}s")

            # 5. Atualizar DB
            instance.status = "running"
            instance.vast_instance_id = new_vast_id
            instance.ssh_host = ssh_host
            instance.ssh_port = ssh_port
            instance.woke_at = datetime.utcnow()
            instance.hibernated_at = None

            # Iniciar tracking de uso
            usage_service = UsageService(db)
            usage_service.start_usage(
                user_id=instance.user_id,
                instance_id=instance.instance_id,
                gpu_type=instance.gpu_type
            )

            # Registrar evento
            event = HibernationEvent(
                instance_id=instance_id,
                event_type="woke_up",
                snapshot_id=instance.snapshot_id,
                reason="Wake manual via API"
            )
            db.add(event)
            db.commit()

            total_time = time.time() - start_time

            logger.info(f"=== Instância {instance_id} acordada em {total_time:.1f}s ===")

            return {
                'success': True,
                'instance_id': instance_id,
                'vast_instance_id': new_vast_id,
                'ssh_host': ssh_host,
                'ssh_port': ssh_port,
                'snapshot_restored': True,
                'time_taken': total_time
            }

        except Exception as e:
            logger.error(f"Erro ao acordar instância {instance_id}: {e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()

    def update_instance_status(
        self,
        instance_id: str,
        gpu_utilization: float,
        gpu_threshold: float = 5.0
    ):
        """
        Atualiza status de uma instância baseado em heartbeat do DumontAgent.

        Args:
            instance_id: ID da instância
            gpu_utilization: Utilização da GPU em %
            gpu_threshold: Threshold para considerar ociosa
        """
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            instance = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()

            if not instance:
                # Criar nova instância no DB
                logger.info(f"Nova instância detectada: {instance_id}")
                instance = InstanceStatus(
                    instance_id=instance_id,
                    user_id="unknown",  # Será atualizado depois
                    status="running",
                    gpu_utilization=gpu_utilization,
                    last_heartbeat=now,
                    last_activity=now
                )
                db.add(instance)
            else:
                # Atualizar instância existente
                instance.gpu_utilization = gpu_utilization
                instance.last_heartbeat = now

                # Determinar se está ociosa
                is_idle = gpu_utilization < instance.gpu_usage_threshold

                if is_idle:
                    if instance.status == "running":
                        # Primeira vez ociosa - marcar timestamp
                        instance.status = "idle"
                        instance.idle_since = now
                        logger.info(f"Instância {instance_id} ficou ociosa ({gpu_utilization}%)")

                        # Registrar evento
                        event = HibernationEvent(
                            instance_id=instance_id,
                            event_type="idle_detected",
                            gpu_utilization=gpu_utilization,
                            reason=f"GPU utilização < {instance.gpu_usage_threshold}%"
                        )
                        db.add(event)
                else:
                    if instance.status == "idle":
                        # Voltou a ser usada
                        instance.status = "running"
                        instance.idle_since = None
                        logger.info(f"Instância {instance_id} voltou a ser usada ({gpu_utilization}%)")

                    instance.last_activity = now

            db.commit()

        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
            db.rollback()
        finally:
            db.close()

    def get_all_instance_status(self) -> List[Dict]:
        """Retorna status de todas as instâncias rastreadas."""
        db = SessionLocal()
        try:
            instances = db.query(InstanceStatus).all()
            result = []
            for inst in instances:
                result.append({
                    "instance_id": inst.instance_id,
                    "status": inst.status,
                    "gpu_utilization": inst.gpu_utilization or 0,
                    "last_heartbeat": inst.last_heartbeat.isoformat() if inst.last_heartbeat else None,
                    "idle_since": inst.idle_since.isoformat() if inst.idle_since else None,
                    "will_hibernate_at": self._calculate_hibernate_time(inst),
                    "auto_hibernation_enabled": inst.auto_hibernation_enabled,
                })
            return result
        finally:
            db.close()

    def get_instance_status(self, instance_id: str) -> Optional[Dict]:
        """Retorna status de uma instância específica."""
        db = SessionLocal()
        try:
            inst = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()
            if not inst:
                return None
            return {
                "instance_id": inst.instance_id,
                "status": inst.status,
                "gpu_utilization": inst.gpu_utilization or 0,
                "last_heartbeat": inst.last_heartbeat.isoformat() if inst.last_heartbeat else None,
                "idle_since": inst.idle_since.isoformat() if inst.idle_since else None,
                "will_hibernate_at": self._calculate_hibernate_time(inst),
                "auto_hibernation_enabled": inst.auto_hibernation_enabled,
                "idle_timeout_seconds": inst.idle_timeout_seconds,
                "gpu_usage_threshold": inst.gpu_usage_threshold,
                "snapshot_id": inst.last_snapshot_id,
            }
        finally:
            db.close()

    def _calculate_hibernate_time(self, instance: InstanceStatus) -> Optional[str]:
        """Calcula quando a instância será hibernada."""
        if instance.status != "idle" or not instance.idle_since:
            return None
        hibernate_at = instance.idle_since + timedelta(seconds=instance.idle_timeout_seconds)
        return hibernate_at.isoformat()

    def extend_keep_alive(self, instance_id: str, minutes: int = 30) -> bool:
        """Estende o tempo antes de hibernar uma instância."""
        db = SessionLocal()
        try:
            inst = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()
            if not inst:
                return False
            
            # Resetar idle_since para agora + minutos extras
            inst.idle_since = datetime.utcnow() + timedelta(minutes=minutes)
            inst.status = "running"  # Temporariamente marcar como running
            db.commit()
            logger.info(f"Keep-alive estendido para {instance_id} por {minutes} minutos")
            return True
        except Exception as e:
            logger.error(f"Erro ao estender keep-alive: {e}")
            db.rollback()
            return False
        finally:
            db.close()


# Singleton global
_auto_hibernation_manager: Optional[AutoHibernationManager] = None


def get_auto_hibernation_manager() -> Optional[AutoHibernationManager]:
    """Retorna a instância global do AutoHibernationManager."""
    return _auto_hibernation_manager


def init_auto_hibernation_manager(
    vast_api_key: str,
    r2_endpoint: str,
    r2_bucket: str,
    check_interval: int = 30
) -> AutoHibernationManager:
    """Inicializa e retorna o AutoHibernationManager global."""
    global _auto_hibernation_manager
    if _auto_hibernation_manager is None:
        _auto_hibernation_manager = AutoHibernationManager(
            vast_api_key=vast_api_key,
            r2_endpoint=r2_endpoint,
            r2_bucket=r2_bucket,
            check_interval=check_interval
        )
    return _auto_hibernation_manager
