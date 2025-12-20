"""
Volume Service - Gerencia volumes VAST.ai para GPU Warm Pool.

Volumes sao storage persistente que podem ser compartilhados
entre GPUs do mesmo host fisico.
"""
import logging
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)


class VolumeState(str, Enum):
    """Estados possiveis de um volume"""
    CREATING = "creating"
    AVAILABLE = "available"
    IN_USE = "in_use"
    DELETING = "deleting"
    ERROR = "error"


@dataclass
class Volume:
    """Representa um volume VAST.ai"""
    volume_id: int
    machine_id: int
    size_gb: int
    state: VolumeState
    attached_instance_id: Optional[int] = None
    mount_path: str = "/data"
    created_at: Optional[str] = None


class VolumeService:
    """
    Gerencia volumes no VAST.ai.

    Volumes sao usados para:
    - Compartilhar dados entre GPUs do mesmo host
    - Persistir dados entre reinicializacoes
    - Permitir failover rapido (dados ja estao no volume)
    """

    def __init__(self, vast_api_key: str):
        self.api_key = vast_api_key
        self.api_url = "https://console.vast.ai/api/v0"

    async def create_volume(
        self,
        machine_id: int,
        size_gb: int = 100,
        name: Optional[str] = None
    ) -> Optional[Volume]:
        """
        Cria um novo volume em um host especifico.

        Args:
            machine_id: ID da maquina/host
            size_gb: Tamanho do volume em GB
            name: Nome opcional do volume

        Returns:
            Volume criado ou None se falhou
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                payload = {
                    "machine_id": machine_id,
                    "size": size_gb,
                }

                if name:
                    payload["name"] = name

                async with session.post(
                    f"{self.api_url}/volumes/",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status not in [200, 201]:
                        text = await response.text()
                        logger.error(f"Failed to create volume: {response.status} - {text}")
                        return None

                    data = await response.json()

                    volume = Volume(
                        volume_id=data.get("id"),
                        machine_id=machine_id,
                        size_gb=size_gb,
                        state=VolumeState.AVAILABLE,
                        created_at=data.get("created_at"),
                    )

                    logger.info(f"Created volume {volume.volume_id} on machine {machine_id}")
                    return volume

        except Exception as e:
            logger.error(f"Failed to create volume: {e}")
            return None

    async def get_volume(self, volume_id: int) -> Optional[Volume]:
        """
        Obtem informacoes de um volume.

        Args:
            volume_id: ID do volume

        Returns:
            Volume ou None se nao encontrado
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.get(
                    f"{self.api_url}/volumes/{volume_id}/",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

                    # Determinar estado
                    state = VolumeState.AVAILABLE
                    if data.get("attached_instance"):
                        state = VolumeState.IN_USE

                    return Volume(
                        volume_id=data.get("id"),
                        machine_id=data.get("machine_id"),
                        size_gb=data.get("size", 0),
                        state=state,
                        attached_instance_id=data.get("attached_instance"),
                        created_at=data.get("created_at"),
                    )

        except Exception as e:
            logger.error(f"Failed to get volume {volume_id}: {e}")
            return None

    async def list_volumes(self) -> List[Volume]:
        """
        Lista todos os volumes do usuario.

        Returns:
            Lista de volumes
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.get(
                    f"{self.api_url}/volumes/",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    volumes_data = data.get("volumes", [])

                    volumes = []
                    for vol_data in volumes_data:
                        state = VolumeState.AVAILABLE
                        if vol_data.get("attached_instance"):
                            state = VolumeState.IN_USE

                        volumes.append(Volume(
                            volume_id=vol_data.get("id"),
                            machine_id=vol_data.get("machine_id"),
                            size_gb=vol_data.get("size", 0),
                            state=state,
                            attached_instance_id=vol_data.get("attached_instance"),
                            created_at=vol_data.get("created_at"),
                        ))

                    return volumes

        except Exception as e:
            logger.error(f"Failed to list volumes: {e}")
            return []

    async def delete_volume(self, volume_id: int) -> bool:
        """
        Deleta um volume.

        O volume deve estar desanexado de qualquer instancia.

        Args:
            volume_id: ID do volume

        Returns:
            True se deletou com sucesso
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.delete(
                    f"{self.api_url}/volumes/{volume_id}/",
                    headers=headers
                ) as response:
                    if response.status not in [200, 204]:
                        text = await response.text()
                        logger.error(f"Failed to delete volume: {response.status} - {text}")
                        return False

                    logger.info(f"Deleted volume {volume_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to delete volume {volume_id}: {e}")
            return False

    async def attach_volume_to_instance(
        self,
        volume_id: int,
        instance_id: int,
        mount_path: str = "/data"
    ) -> bool:
        """
        Anexa um volume a uma instancia.

        Nota: No VAST.ai, o volume e especificado na criacao da instancia.
        Este metodo e usado para referencia e tracking.

        Args:
            volume_id: ID do volume
            instance_id: ID da instancia
            mount_path: Caminho de montagem

        Returns:
            True se anexou com sucesso
        """
        try:
            # No VAST.ai, volumes sao anexados na criacao da instancia
            # Este metodo atualiza o tracking local
            logger.info(f"Volume {volume_id} attached to instance {instance_id} at {mount_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to attach volume: {e}")
            return False

    async def get_volumes_by_machine(self, machine_id: int) -> List[Volume]:
        """
        Lista volumes de um host especifico.

        Args:
            machine_id: ID da maquina

        Returns:
            Lista de volumes do host
        """
        all_volumes = await self.list_volumes()
        return [v for v in all_volumes if v.machine_id == machine_id]

    async def find_or_create_volume(
        self,
        machine_id: int,
        size_gb: int = 100,
        name: Optional[str] = None
    ) -> Optional[Volume]:
        """
        Encontra um volume existente ou cria um novo.

        Args:
            machine_id: ID da maquina
            size_gb: Tamanho minimo do volume
            name: Nome do volume

        Returns:
            Volume encontrado ou criado
        """
        # Primeiro, verificar se ja existe um volume neste host
        existing_volumes = await self.get_volumes_by_machine(machine_id)

        for vol in existing_volumes:
            if vol.size_gb >= size_gb and vol.state == VolumeState.AVAILABLE:
                logger.info(f"Found existing volume {vol.volume_id} on machine {machine_id}")
                return vol

        # Criar novo volume
        return await self.create_volume(machine_id, size_gb, name)

    # Versoes sincronas

    def create_volume_sync(self, **kwargs) -> Optional[Volume]:
        """Versao sincrona de create_volume"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.create_volume(**kwargs))
        finally:
            loop.close()

    def get_volume_sync(self, volume_id: int) -> Optional[Volume]:
        """Versao sincrona de get_volume"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.get_volume(volume_id))
        finally:
            loop.close()

    def list_volumes_sync(self) -> List[Volume]:
        """Versao sincrona de list_volumes"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.list_volumes())
        finally:
            loop.close()

    def delete_volume_sync(self, volume_id: int) -> bool:
        """Versao sincrona de delete_volume"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.delete_volume(volume_id))
        finally:
            loop.close()

    def find_or_create_volume_sync(self, **kwargs) -> Optional[Volume]:
        """Versao sincrona de find_or_create_volume"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.find_or_create_volume(**kwargs))
        finally:
            loop.close()
