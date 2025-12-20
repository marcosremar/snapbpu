"""
Standby Manager - Gerencia associações GPU ↔ CPU Standby

Responsável por:
1. Auto-criar CPU standby quando GPU é criada (se configurado)
2. Auto-destruir CPU standby quando GPU é destruída
3. Manter mapeamento GPU → CPU standby
4. Integrar com FailoverSettingsManager para configurações

Agora integrado com o sistema unificado de failover que suporta:
- GPU Warm Pool (estratégia primária)
- CPU Standby + Snapshot (estratégia de fallback)
"""
import os
import json
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StandbyAssociation:
    """Associação entre GPU e CPU Standby"""
    gpu_instance_id: int
    cpu_instance_name: str
    cpu_instance_zone: str
    cpu_instance_ip: Optional[str] = None
    sync_enabled: bool = False
    created_at: Optional[str] = None
    # Campos para tracking de falha de GPU
    gpu_failed: bool = False
    failure_reason: Optional[str] = None
    failed_at: Optional[str] = None


class StandbyManager:
    """
    Gerenciador global de CPU Standby.
    Singleton que mantém associações GPU → CPU.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._associations: Dict[int, StandbyAssociation] = {}
        self._services: Dict[int, Any] = {}  # GPU ID → CPUStandbyService
        self._gcp_credentials: Optional[dict] = None
        self._vast_api_key: Optional[str] = None
        self._auto_standby_enabled: bool = False
        self._config: Dict[str, Any] = {}

        # Carregar associações salvas
        self._load_associations()

        logger.info("StandbyManager initialized")

    def configure(
        self,
        gcp_credentials: dict,
        vast_api_key: str,
        auto_standby_enabled: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Configura o manager com credenciais.

        Args:
            gcp_credentials: Credenciais GCP (dict ou JSON string)
            vast_api_key: API key da Vast.ai
            auto_standby_enabled: Se True, cria CPU standby automaticamente
            config: Configurações adicionais (zone, machine_type, etc)
        """
        if isinstance(gcp_credentials, str):
            self._gcp_credentials = json.loads(gcp_credentials)
        else:
            self._gcp_credentials = gcp_credentials

        self._vast_api_key = vast_api_key
        self._auto_standby_enabled = auto_standby_enabled
        self._config = config or {}

        logger.info(f"StandbyManager configured (auto_standby={auto_standby_enabled})")

    def is_configured(self) -> bool:
        """Verifica se o manager está configurado"""
        return self._gcp_credentials is not None and self._vast_api_key is not None

    def is_auto_standby_enabled(self) -> bool:
        """Verifica se auto-standby está habilitado"""
        return self._auto_standby_enabled and self.is_configured()

    def should_create_cpu_standby(self, machine_id: int) -> bool:
        """
        Verifica se deve criar CPU standby para uma máquina.

        Consulta o FailoverSettingsManager para determinar se
        CPU Standby está habilitado para esta máquina.

        Args:
            machine_id: ID da máquina

        Returns:
            True se CPU Standby deve ser criado
        """
        if not self.is_configured():
            return False

        try:
            from src.config.failover_settings import get_failover_settings_manager
            settings_manager = get_failover_settings_manager()
            effective_config = settings_manager.get_effective_config(machine_id)

            strategy = effective_config.get('effective_strategy', 'both')
            cpu_standby_enabled = effective_config.get('cpu_standby', {}).get('enabled', True)

            # CPU Standby deve ser criado se:
            # 1. Estratégia é 'cpu_standby' ou 'both'
            # 2. E cpu_standby está habilitado nas configurações
            return strategy in ['cpu_standby', 'both'] and cpu_standby_enabled

        except Exception as e:
            logger.warning(f"Failed to check failover settings for machine {machine_id}: {e}")
            # Fallback: usar configuração local
            return self._auto_standby_enabled

    def on_gpu_created(self, gpu_instance_id: int, label: Optional[str] = None, machine_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Callback quando uma GPU é criada.
        Cria CPU standby automaticamente se configurado.

        Consulta FailoverSettingsManager para verificar se CPU Standby
        está habilitado para esta máquina.

        Args:
            gpu_instance_id: ID da instância GPU (Vast.ai)
            label: Label opcional da GPU
            machine_id: ID interno da máquina (para consultar configurações)

        Returns:
            Dict com informações do CPU standby criado, ou None se não criou
        """
        # Usar machine_id se fornecido, senão usar gpu_instance_id
        config_machine_id = machine_id if machine_id else gpu_instance_id

        # Verificar se deve criar CPU standby baseado nas configurações
        if not self.should_create_cpu_standby(config_machine_id):
            logger.debug(f"CPU Standby not enabled for machine {config_machine_id}, skipping")
            return None

        # Verificar se já existe associação
        if gpu_instance_id in self._associations:
            logger.info(f"GPU {gpu_instance_id} already has standby association")
            return self._get_association_info(gpu_instance_id)

        try:
            logger.info(f"Creating CPU standby for GPU {gpu_instance_id}")

            # Criar serviço de standby
            from src.services.standby.cpu import CPUStandbyService, CPUStandbyConfig

            config = CPUStandbyConfig(
                gcp_zone=self._config.get('gcp_zone', 'europe-west1-b'),
                gcp_machine_type=self._config.get('gcp_machine_type', 'e2-medium'),
                gcp_disk_size=self._config.get('gcp_disk_size', 100),
                gcp_spot=self._config.get('gcp_spot', True),
                sync_interval_seconds=self._config.get('sync_interval', 30),
                auto_failover=self._config.get('auto_failover', True),
                auto_recovery=self._config.get('auto_recovery', True),
            )

            service = CPUStandbyService(
                vast_api_key=self._vast_api_key,
                gcp_credentials=self._gcp_credentials,
                config=config
            )

            # Gerar nome único para o standby
            name_suffix = label or f"gpu-{gpu_instance_id}"

            # Provisionar CPU standby
            instance_id = service.provision_cpu_standby(name_suffix)

            if not instance_id:
                logger.error(f"Failed to provision CPU standby for GPU {gpu_instance_id}")
                return None

            # Registrar GPU
            if not service.register_gpu_instance(gpu_instance_id):
                logger.warning(f"Failed to register GPU {gpu_instance_id} - GPU may not be ready yet")
                # Não falha, GPU pode ainda estar inicializando

            # Salvar associação
            association = StandbyAssociation(
                gpu_instance_id=gpu_instance_id,
                cpu_instance_name=service.cpu_instance.get('name'),
                cpu_instance_zone=service.cpu_instance.get('zone'),
                cpu_instance_ip=service.cpu_instance.get('external_ip'),
                sync_enabled=False,
            )

            self._associations[gpu_instance_id] = association
            self._services[gpu_instance_id] = service
            self._save_associations()

            logger.info(f"CPU standby created for GPU {gpu_instance_id}: {association.cpu_instance_name}")

            return {
                'gpu_instance_id': gpu_instance_id,
                'cpu_standby': {
                    'name': association.cpu_instance_name,
                    'zone': association.cpu_instance_zone,
                    'ip': association.cpu_instance_ip,
                },
                'sync_enabled': False,
                'message': 'CPU standby created. Sync will start when GPU is ready.'
            }

        except Exception as e:
            logger.error(f"Failed to create CPU standby for GPU {gpu_instance_id}: {e}")
            return None

    def mark_gpu_failed(self, gpu_instance_id: int, reason: str = "unknown") -> bool:
        """
        Marca que a GPU falhou, mas mantém o CPU standby para backup/restore.

        Args:
            gpu_instance_id: ID da instância GPU que falhou
            reason: Motivo da falha (gpu_failure, spot_interruption, etc)

        Returns:
            True se marcou com sucesso
        """
        if gpu_instance_id not in self._associations:
            logger.debug(f"No standby association for GPU {gpu_instance_id}")
            return False

        association = self._associations[gpu_instance_id]
        logger.info(f"Marking GPU {gpu_instance_id} as failed (reason={reason}), keeping CPU standby {association.cpu_instance_name}")

        # Atualizar estado da associação
        association.gpu_failed = True
        association.failure_reason = reason
        association.failed_at = datetime.now().isoformat()

        # Parar sync se estiver rodando (GPU não existe mais)
        if gpu_instance_id in self._services:
            try:
                self._services[gpu_instance_id].stop_sync()
            except Exception as e:
                logger.warning(f"Failed to stop sync for failed GPU {gpu_instance_id}: {e}")

        self._save_associations()

        logger.info(f"GPU {gpu_instance_id} marked as failed. CPU standby kept for backup/restore.")
        return True

    def on_gpu_destroyed(self, gpu_instance_id: int) -> bool:
        """
        Callback quando uma GPU é destruída (por solicitação do usuário).
        Destroi o CPU standby associado.

        Args:
            gpu_instance_id: ID da instância GPU

        Returns:
            True se limpou com sucesso
        """
        if gpu_instance_id not in self._associations:
            logger.debug(f"No standby association for GPU {gpu_instance_id}")
            return True

        association = self._associations[gpu_instance_id]
        logger.info(f"Destroying CPU standby {association.cpu_instance_name} for GPU {gpu_instance_id}")

        try:
            # Parar serviço se existir
            if gpu_instance_id in self._services:
                service = self._services[gpu_instance_id]
                service.cleanup()
                del self._services[gpu_instance_id]
            else:
                # Destruir diretamente via GCP provider
                from src.infrastructure.providers.gcp_provider import GCPProvider

                gcp = GCPProvider(json.dumps(self._gcp_credentials))
                gcp.delete_instance(
                    name=association.cpu_instance_name,
                    zone=association.cpu_instance_zone
                )

            # Remover associação
            del self._associations[gpu_instance_id]
            self._save_associations()

            logger.info(f"CPU standby {association.cpu_instance_name} destroyed")
            return True

        except Exception as e:
            logger.error(f"Failed to destroy CPU standby for GPU {gpu_instance_id}: {e}")
            # Remover associação mesmo com erro para não bloquear
            if gpu_instance_id in self._associations:
                del self._associations[gpu_instance_id]
                self._save_associations()
            return False

    def start_sync(self, gpu_instance_id: int) -> bool:
        """
        Inicia sincronização para uma GPU.

        Args:
            gpu_instance_id: ID da instância GPU

        Returns:
            True se iniciou sync
        """
        if gpu_instance_id not in self._services:
            logger.warning(f"No service for GPU {gpu_instance_id}")
            return False

        service = self._services[gpu_instance_id]

        # Registrar GPU se ainda não estiver
        if not service.gpu_instance_id:
            if not service.register_gpu_instance(gpu_instance_id):
                logger.error(f"Failed to register GPU {gpu_instance_id}")
                return False

        # Iniciar sync
        if service.start_sync():
            if gpu_instance_id in self._associations:
                self._associations[gpu_instance_id].sync_enabled = True
                self._save_associations()
            return True

        return False

    def stop_sync(self, gpu_instance_id: int) -> bool:
        """Para sincronização para uma GPU."""
        if gpu_instance_id not in self._services:
            return False

        service = self._services[gpu_instance_id]
        service.stop_sync()

        if gpu_instance_id in self._associations:
            self._associations[gpu_instance_id].sync_enabled = False
            self._save_associations()

        return True

    def get_association(self, gpu_instance_id: int) -> Optional[Dict[str, Any]]:
        """Retorna informações da associação GPU → CPU standby"""
        return self._get_association_info(gpu_instance_id)

    def get_service(self, gpu_instance_id: int) -> Optional[Any]:
        """Retorna o CPUStandbyService para uma GPU"""
        return self._services.get(gpu_instance_id)

    def list_associations(self) -> Dict[int, Dict[str, Any]]:
        """Lista todas as associações ativas"""
        return {
            gpu_id: self._get_association_info(gpu_id)
            for gpu_id in self._associations
        }

    def get_status(self) -> Dict[str, Any]:
        """Retorna status geral do manager"""
        # Converter chaves de associações para string para compatibilidade JSON/Pydantic
        associations = {str(k): v for k, v in self.list_associations().items()}
        
        return {
            'configured': self.is_configured(),
            'auto_standby_enabled': self._auto_standby_enabled,
            'active_associations': len(self._associations),
            'associations': associations,
            'config': {
                'gcp_zone': self._config.get('gcp_zone', 'europe-west1-b'),
                'gcp_machine_type': self._config.get('gcp_machine_type', 'e2-medium'),
                'auto_failover': self._config.get('auto_failover', True),
            }
        }

    def _get_association_info(self, gpu_instance_id: int) -> Optional[Dict[str, Any]]:
        """Retorna info formatada de uma associação"""
        if gpu_instance_id not in self._associations:
            return None

        assoc = self._associations[gpu_instance_id]
        service = self._services.get(gpu_instance_id)

        result = {
            'gpu_instance_id': assoc.gpu_instance_id,
            'cpu_standby': {
                'name': assoc.cpu_instance_name,
                'zone': assoc.cpu_instance_zone,
                'ip': assoc.cpu_instance_ip,
            },
            'sync_enabled': assoc.sync_enabled,
            'gpu_failed': assoc.gpu_failed,
            'failure_reason': assoc.failure_reason,
            'failed_at': assoc.failed_at,
        }

        if service:
            result['state'] = service.state.value
            result['sync_count'] = service.sync_count
            result['health_status'] = getattr(service, 'health_status', 'unknown')

        return result

    def _load_associations(self):
        """Carrega associações do disco"""
        assoc_file = os.path.expanduser("~/.dumont/standby_associations.json")

        if os.path.exists(assoc_file):
            try:
                with open(assoc_file, 'r') as f:
                    data = json.load(f)

                for gpu_id_str, assoc_data in data.items():
                    gpu_id = int(gpu_id_str)
                    self._associations[gpu_id] = StandbyAssociation(
                        gpu_instance_id=gpu_id,
                        cpu_instance_name=assoc_data['cpu_instance_name'],
                        cpu_instance_zone=assoc_data['cpu_instance_zone'],
                        cpu_instance_ip=assoc_data.get('cpu_instance_ip'),
                        sync_enabled=assoc_data.get('sync_enabled', False),
                        gpu_failed=assoc_data.get('gpu_failed', False),
                        failure_reason=assoc_data.get('failure_reason'),
                        failed_at=assoc_data.get('failed_at'),
                    )

                logger.info(f"Loaded {len(self._associations)} standby associations")
            except Exception as e:
                logger.warning(f"Failed to load associations: {e}")

    def _save_associations(self):
        """Salva associações no disco"""
        assoc_file = os.path.expanduser("~/.dumont/standby_associations.json")
        os.makedirs(os.path.dirname(assoc_file), exist_ok=True)

        try:
            data = {}
            for gpu_id, assoc in self._associations.items():
                data[str(gpu_id)] = {
                    'cpu_instance_name': assoc.cpu_instance_name,
                    'cpu_instance_zone': assoc.cpu_instance_zone,
                    'cpu_instance_ip': assoc.cpu_instance_ip,
                    'sync_enabled': assoc.sync_enabled,
                    'gpu_failed': assoc.gpu_failed,
                    'failure_reason': assoc.failure_reason,
                    'failed_at': assoc.failed_at,
                }

            with open(assoc_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save associations: {e}")


# Singleton instance
_standby_manager: Optional[StandbyManager] = None


def get_standby_manager() -> StandbyManager:
    """Retorna a instância global do StandbyManager"""
    global _standby_manager
    if _standby_manager is None:
        _standby_manager = StandbyManager()
    return _standby_manager
