"""
Warm Pool Manager - Gerenciador principal de GPU Warm Pool.

Coordena:
- Busca de hosts com multiplas GPUs
- Criacao de volumes
- Provisioning de GPU principal e standby
- Failover automatico
- Integracao com CPU Standby (fallback)
"""
import os
import json
import logging
import asyncio
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import aiohttp

from src.config.failover_settings import (
    FailoverSettings, MachineFailoverConfig, WarmPoolConfig,
    get_failover_settings_manager, FailoverStrategy
)
from .host_finder import HostFinder, MultiGPUHost, GPUOffer
from .volume_service import VolumeService, Volume

logger = logging.getLogger(__name__)


class WarmPoolState(str, Enum):
    """Estados do Warm Pool"""
    DISABLED = "disabled"              # Desabilitado
    SEARCHING = "searching"            # Buscando host com multi-GPU
    PROVISIONING = "provisioning"      # Criando volume e instancias
    ACTIVE = "active"                  # GPU #1 running, GPU #2 stopped
    FAILOVER = "failover"              # GPU #2 iniciando
    RECOVERING = "recovering"          # Provisionando nova GPU standby
    DEGRADED = "degraded"              # Sem warm pool, fallback ativo
    ERROR = "error"                    # Erro


@dataclass
class WarmPoolStatus:
    """Status atual do Warm Pool para uma maquina"""
    machine_id: int
    state: WarmPoolState = WarmPoolState.DISABLED
    host_machine_id: Optional[int] = None         # ID do host VAST.ai
    volume_id: Optional[int] = None               # ID do volume
    primary_gpu_id: Optional[int] = None          # ID da GPU principal
    standby_gpu_id: Optional[int] = None          # ID da GPU standby
    standby_state: str = "none"                   # none, stopped, starting, running
    primary_ssh_host: Optional[str] = None
    primary_ssh_port: Optional[int] = None
    last_health_check: Optional[str] = None
    failover_count: int = 0
    last_failover_at: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['state'] = self.state.value
        return result


class WarmPoolManager:
    """
    Gerenciador de GPU Warm Pool.

    Estrategia principal de failover - habilitada por padrao.
    """

    _instances: Dict[int, 'WarmPoolManager'] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        machine_id: int,
        vast_api_key: str,
        config: Optional[WarmPoolConfig] = None
    ):
        self.machine_id = machine_id
        self.api_key = vast_api_key
        self.api_url = "https://console.vast.ai/api/v0"

        # Configuracao
        self.config = config or WarmPoolConfig()

        # Servicos
        self.host_finder = HostFinder(vast_api_key)
        self.volume_service = VolumeService(vast_api_key)

        # Estado
        self.status = WarmPoolStatus(machine_id=machine_id)

        # Health check
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

        # Referencia ao CPU Standby (fallback)
        self._cpu_standby_service = None

        logger.info(f"WarmPoolManager initialized for machine {machine_id}")

    @classmethod
    def get_instance(cls, machine_id: int, vast_api_key: str) -> 'WarmPoolManager':
        """Obtem ou cria instancia do manager para uma maquina"""
        with cls._lock:
            if machine_id not in cls._instances:
                cls._instances[machine_id] = cls(machine_id, vast_api_key)
            return cls._instances[machine_id]

    def set_cpu_standby_service(self, service):
        """Define o servico de CPU Standby para fallback"""
        self._cpu_standby_service = service

    async def find_suitable_host(
        self,
        gpu_name: Optional[str] = None,
        max_price: Optional[float] = None
    ) -> Optional[MultiGPUHost]:
        """
        Busca um host adequado para warm pool.

        Args:
            gpu_name: Nome da GPU desejada
            max_price: Preco maximo por hora

        Returns:
            Host encontrado ou None
        """
        self.status.state = WarmPoolState.SEARCHING

        try:
            hosts = await self.host_finder.find_multi_gpu_hosts(
                gpu_name=gpu_name,
                min_gpus=self.config.min_gpus_per_host,
                max_price=max_price,
                verified=True,
                preferred_gpu_names=self.config.preferred_gpu_names,
            )

            if not hosts:
                logger.warning(f"No hosts with {self.config.min_gpus_per_host}+ GPUs found")
                self.status.state = WarmPoolState.DEGRADED
                return None

            # Retornar o melhor host
            best_host = hosts[0]
            logger.info(f"Found suitable host: {best_host.machine_id} with {best_host.available_gpus} GPUs")
            return best_host

        except Exception as e:
            logger.error(f"Failed to find suitable host: {e}")
            self.status.state = WarmPoolState.ERROR
            self.status.error_message = str(e)
            return None

    async def provision_warm_pool(
        self,
        host: MultiGPUHost,
        image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        disk_size: int = 50,
        onstart_script: Optional[str] = None
    ) -> bool:
        """
        Provisiona warm pool completo em um host.

        Args:
            host: Host com multiplas GPUs
            image: Imagem Docker
            disk_size: Tamanho do disco da instancia
            onstart_script: Script de inicializacao

        Returns:
            True se provisionou com sucesso
        """
        self.status.state = WarmPoolState.PROVISIONING
        self.status.host_machine_id = host.machine_id

        try:
            # 1. Criar ou encontrar volume no host
            logger.info(f"Creating volume on host {host.machine_id}")
            volume = await self.volume_service.find_or_create_volume(
                machine_id=host.machine_id,
                size_gb=self.config.volume_size_gb,
                name=f"warmpool-{self.machine_id}"
            )

            if not volume:
                raise Exception("Failed to create volume")

            self.status.volume_id = volume.volume_id
            logger.info(f"Volume {volume.volume_id} ready")

            # 2. Selecionar 2 ofertas do mesmo host
            if len(host.offers) < 2:
                raise Exception(f"Host {host.machine_id} has only {len(host.offers)} offers, need 2+")

            primary_offer = host.offers[0]
            standby_offer = host.offers[1]

            # 3. Provisionar GPU principal
            logger.info(f"Provisioning primary GPU from offer {primary_offer.offer_id}")
            primary_instance = await self._create_instance(
                offer_id=primary_offer.offer_id,
                volume_id=volume.volume_id,
                image=image,
                disk_size=disk_size,
                onstart_script=onstart_script,
                label=f"warmpool-primary-{self.machine_id}"
            )

            if not primary_instance:
                raise Exception("Failed to create primary GPU instance")

            self.status.primary_gpu_id = primary_instance['id']
            logger.info(f"Primary GPU {self.status.primary_gpu_id} created")

            # 4. Aguardar GPU principal ficar pronta
            ssh_info = await self._wait_for_instance_ready(self.status.primary_gpu_id)
            if ssh_info:
                self.status.primary_ssh_host = ssh_info.get('ssh_host')
                self.status.primary_ssh_port = ssh_info.get('ssh_port')

            # 5. Provisionar GPU standby (e parar)
            logger.info(f"Provisioning standby GPU from offer {standby_offer.offer_id}")
            standby_instance = await self._create_instance(
                offer_id=standby_offer.offer_id,
                volume_id=volume.volume_id,
                image=image,
                disk_size=disk_size,
                onstart_script=onstart_script,
                label=f"warmpool-standby-{self.machine_id}"
            )

            if not standby_instance:
                logger.warning("Failed to create standby GPU, warm pool degraded")
                self.status.state = WarmPoolState.DEGRADED
                return False

            self.status.standby_gpu_id = standby_instance['id']
            self.status.standby_state = "starting"
            logger.info(f"Standby GPU {self.status.standby_gpu_id} created")

            # 6. Parar GPU standby para economizar
            await asyncio.sleep(30)  # Aguardar um pouco antes de parar
            await self._stop_instance(self.status.standby_gpu_id)
            self.status.standby_state = "stopped"
            logger.info(f"Standby GPU {self.status.standby_gpu_id} stopped")

            # 7. Atualizar estado
            self.status.state = WarmPoolState.ACTIVE
            self._save_status()

            # 8. Iniciar health check
            self._start_health_check()

            logger.info(f"Warm pool active: primary={self.status.primary_gpu_id}, standby={self.status.standby_gpu_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to provision warm pool: {e}")
            self.status.state = WarmPoolState.ERROR
            self.status.error_message = str(e)

            # Fallback para CPU Standby
            if self.config.fallback_to_cpu_standby and self._cpu_standby_service:
                logger.info("Falling back to CPU Standby")
                self.status.state = WarmPoolState.DEGRADED
                # Ativar CPU Standby aqui

            return False

    async def trigger_failover(self) -> bool:
        """
        Aciona failover: inicia GPU standby.

        Returns:
            True se failover foi bem-sucedido
        """
        if self.status.state != WarmPoolState.ACTIVE:
            logger.warning(f"Cannot trigger failover in state {self.status.state}")
            return False

        if not self.status.standby_gpu_id:
            logger.error("No standby GPU available")
            return False

        self.status.state = WarmPoolState.FAILOVER
        failover_start = datetime.now()

        try:
            logger.info(f"Starting failover: activating GPU {self.status.standby_gpu_id}")

            # 1. Iniciar GPU standby
            await self._start_instance(self.status.standby_gpu_id)
            self.status.standby_state = "starting"

            # 2. Aguardar SSH ready
            ssh_info = await self._wait_for_instance_ready(
                self.status.standby_gpu_id,
                timeout=self.config.failover_timeout_seconds
            )

            if not ssh_info:
                raise Exception("Standby GPU failed to become ready")

            self.status.standby_state = "running"

            # 3. Swap: standby vira principal
            old_primary = self.status.primary_gpu_id
            self.status.primary_gpu_id = self.status.standby_gpu_id
            self.status.primary_ssh_host = ssh_info.get('ssh_host')
            self.status.primary_ssh_port = ssh_info.get('ssh_port')
            self.status.standby_gpu_id = None
            self.status.standby_state = "none"

            # 4. Atualizar stats
            self.status.failover_count += 1
            self.status.last_failover_at = datetime.now().isoformat()

            failover_duration = (datetime.now() - failover_start).total_seconds()
            logger.info(f"Failover complete in {failover_duration:.1f}s. New primary: {self.status.primary_gpu_id}")

            # 5. Cleanup GPU antiga (em background)
            if old_primary:
                asyncio.create_task(self._cleanup_failed_instance(old_primary))

            # 6. Provisionar nova standby (em background)
            if self.config.auto_reprovision_standby:
                self.status.state = WarmPoolState.RECOVERING
                asyncio.create_task(self._provision_new_standby())
            else:
                self.status.state = WarmPoolState.DEGRADED

            self._save_status()
            return True

        except Exception as e:
            logger.error(f"Failover failed: {e}")
            self.status.state = WarmPoolState.ERROR
            self.status.error_message = str(e)

            # Fallback para CPU Standby
            if self.config.fallback_to_cpu_standby and self._cpu_standby_service:
                logger.info("Failover failed, falling back to CPU Standby")
                # Acionar failover do CPU Standby

            return False

    async def _provision_new_standby(self):
        """Provisiona nova GPU standby apos failover"""
        try:
            logger.info("Provisioning new standby GPU")

            # Buscar oferta no mesmo host
            host = await self.host_finder.get_host_by_machine_id(self.status.host_machine_id)

            if not host or not host.offers:
                logger.warning("No available GPU on host for new standby")
                self.status.state = WarmPoolState.DEGRADED
                return

            # Criar nova instancia
            standby_instance = await self._create_instance(
                offer_id=host.offers[0].offer_id,
                volume_id=self.status.volume_id,
                label=f"warmpool-standby-{self.machine_id}"
            )

            if not standby_instance:
                logger.warning("Failed to create new standby GPU")
                self.status.state = WarmPoolState.DEGRADED
                return

            self.status.standby_gpu_id = standby_instance['id']
            self.status.standby_state = "starting"

            # Parar a instancia
            await asyncio.sleep(30)
            await self._stop_instance(self.status.standby_gpu_id)
            self.status.standby_state = "stopped"

            self.status.state = WarmPoolState.ACTIVE
            self._save_status()

            logger.info(f"New standby GPU {self.status.standby_gpu_id} ready")

        except Exception as e:
            logger.error(f"Failed to provision new standby: {e}")
            self.status.state = WarmPoolState.DEGRADED

    async def _cleanup_failed_instance(self, instance_id: int):
        """Limpa instancia que falhou"""
        try:
            logger.info(f"Cleaning up failed instance {instance_id}")
            await self._destroy_instance(instance_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup instance {instance_id}: {e}")

    async def _create_instance(
        self,
        offer_id: int,
        volume_id: Optional[int] = None,
        image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        disk_size: int = 50,
        onstart_script: Optional[str] = None,
        label: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Cria instancia no VAST.ai"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                payload = {
                    "client_id": "me",
                    "image": image,
                    "disk": disk_size,
                    "runtype": "ssh",
                }

                if volume_id:
                    payload["volume_id"] = volume_id

                if onstart_script:
                    payload["onstart"] = onstart_script

                if label:
                    payload["label"] = label

                async with session.put(
                    f"{self.api_url}/asks/{offer_id}/",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status not in [200, 201]:
                        text = await response.text()
                        logger.error(f"Failed to create instance: {response.status} - {text}")
                        return None

                    data = await response.json()
                    return data

        except Exception as e:
            logger.error(f"Failed to create instance: {e}")
            return None

    async def _start_instance(self, instance_id: int) -> bool:
        """Inicia instancia parada"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.put(
                    f"{self.api_url}/instances/{instance_id}/",
                    headers=headers,
                    json={"state": "running"}
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Failed to start instance {instance_id}: {e}")
            return False

    async def _stop_instance(self, instance_id: int) -> bool:
        """Para instancia"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.put(
                    f"{self.api_url}/instances/{instance_id}/",
                    headers=headers,
                    json={"state": "stopped"}
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Failed to stop instance {instance_id}: {e}")
            return False

    async def _destroy_instance(self, instance_id: int) -> bool:
        """Destroi instancia"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.delete(
                    f"{self.api_url}/instances/{instance_id}/",
                    headers=headers
                ) as response:
                    return response.status in [200, 204]

        except Exception as e:
            logger.error(f"Failed to destroy instance {instance_id}: {e}")
            return False

    async def _get_instance(self, instance_id: int) -> Optional[Dict[str, Any]]:
        """Obtem informacoes de uma instancia"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.get(
                    f"{self.api_url}/instances/{instance_id}/",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return None
                    return await response.json()

        except Exception as e:
            logger.error(f"Failed to get instance {instance_id}: {e}")
            return None

    async def _wait_for_instance_ready(
        self,
        instance_id: int,
        timeout: int = 120
    ) -> Optional[Dict[str, Any]]:
        """Aguarda instancia ficar pronta (SSH disponivel)"""
        start = datetime.now()

        while (datetime.now() - start).total_seconds() < timeout:
            instance = await self._get_instance(instance_id)

            if instance:
                status = instance.get('actual_status', '')
                ssh_host = instance.get('ssh_host')
                ssh_port = instance.get('ssh_port')

                if status == 'running' and ssh_host and ssh_port:
                    logger.info(f"Instance {instance_id} ready: {ssh_host}:{ssh_port}")
                    return {
                        'ssh_host': ssh_host,
                        'ssh_port': ssh_port,
                        'status': status
                    }

            await asyncio.sleep(5)

        logger.warning(f"Instance {instance_id} not ready after {timeout}s")
        return None

    def _start_health_check(self):
        """Inicia task de health check"""
        if self._health_check_task:
            return

        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    def _stop_health_check(self):
        """Para task de health check"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None

    async def _health_check_loop(self):
        """Loop de health check"""
        consecutive_failures = 0

        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)

                if self.status.state != WarmPoolState.ACTIVE:
                    continue

                # Verificar GPU principal
                instance = await self._get_instance(self.status.primary_gpu_id)

                if not instance:
                    consecutive_failures += 1
                    logger.warning(f"Health check failed ({consecutive_failures})")
                else:
                    status = instance.get('actual_status', '')
                    if status != 'running':
                        consecutive_failures += 1
                        logger.warning(f"GPU not running: {status} ({consecutive_failures})")
                    else:
                        consecutive_failures = 0
                        self.status.last_health_check = datetime.now().isoformat()

                # Acionar failover se necessario
                if consecutive_failures >= 3:
                    logger.error("GPU failed health check 3 times, triggering failover")
                    await self.trigger_failover()
                    consecutive_failures = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    def _save_status(self):
        """Salva status no disco"""
        status_file = os.path.expanduser(f"~/.dumont/warmpool_{self.machine_id}.json")
        os.makedirs(os.path.dirname(status_file), exist_ok=True)

        try:
            with open(status_file, 'w') as f:
                json.dump(self.status.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save status: {e}")

    def _load_status(self):
        """Carrega status do disco"""
        status_file = os.path.expanduser(f"~/.dumont/warmpool_{self.machine_id}.json")

        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    data = json.load(f)
                    self.status = WarmPoolStatus(
                        machine_id=self.machine_id,
                        state=WarmPoolState(data.get('state', 'disabled')),
                        host_machine_id=data.get('host_machine_id'),
                        volume_id=data.get('volume_id'),
                        primary_gpu_id=data.get('primary_gpu_id'),
                        standby_gpu_id=data.get('standby_gpu_id'),
                        standby_state=data.get('standby_state', 'none'),
                        primary_ssh_host=data.get('primary_ssh_host'),
                        primary_ssh_port=data.get('primary_ssh_port'),
                        failover_count=data.get('failover_count', 0),
                        last_failover_at=data.get('last_failover_at'),
                    )
            except Exception as e:
                logger.warning(f"Failed to load status: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual"""
        return self.status.to_dict()

    async def cleanup(self):
        """Limpa recursos do warm pool"""
        self._stop_health_check()

        try:
            # Destruir instancias
            if self.status.primary_gpu_id:
                await self._destroy_instance(self.status.primary_gpu_id)
            if self.status.standby_gpu_id:
                await self._destroy_instance(self.status.standby_gpu_id)

            # Deletar volume
            if self.status.volume_id:
                await self.volume_service.delete_volume(self.status.volume_id)

            # Limpar status
            self.status = WarmPoolStatus(machine_id=self.machine_id)
            self._save_status()

            logger.info(f"Warm pool for machine {self.machine_id} cleaned up")

        except Exception as e:
            logger.error(f"Failed to cleanup warm pool: {e}")


# Singleton global manager
_warm_pool_managers: Dict[int, WarmPoolManager] = {}


def get_warm_pool_manager(machine_id: int, vast_api_key: str) -> WarmPoolManager:
    """Obtem ou cria WarmPoolManager para uma maquina"""
    global _warm_pool_managers
    if machine_id not in _warm_pool_managers:
        _warm_pool_managers[machine_id] = WarmPoolManager(machine_id, vast_api_key)
    return _warm_pool_managers[machine_id]
