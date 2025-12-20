"""
Host Finder - Busca hosts com multiplas GPUs disponiveis no VAST.ai.

Permite encontrar hosts onde e possivel criar um GPU Warm Pool
(requer minimo 2 GPUs disponiveis no mesmo host).
"""
import logging
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class GPUOffer:
    """Representa uma oferta de GPU no VAST.ai"""
    offer_id: int
    machine_id: int
    gpu_name: str
    num_gpus: int
    gpu_ram_mb: int
    cpu_cores: int
    ram_mb: int
    disk_space_gb: float
    price_per_hour: float
    reliability: float
    verified: bool
    static_ip: bool
    geolocation: str
    inet_up_bps: float
    inet_down_bps: float
    cuda_max_good: str
    rentable: bool


@dataclass
class MultiGPUHost:
    """Representa um host com multiplas GPUs disponiveis"""
    machine_id: int
    total_gpus: int
    available_gpus: int
    gpu_name: str
    offers: List[GPUOffer] = field(default_factory=list)
    avg_price_per_hour: float = 0.0
    reliability: float = 0.0
    verified: bool = False
    geolocation: str = ""

    @property
    def can_create_warm_pool(self) -> bool:
        """Verifica se pode criar warm pool (minimo 2 GPUs)"""
        return self.available_gpus >= 2


class HostFinder:
    """
    Busca hosts com multiplas GPUs no VAST.ai.

    Filtra por:
    - Numero minimo de GPUs
    - Tipo de GPU
    - Verificado
    - Preco maximo
    """

    def __init__(self, vast_api_key: str):
        self.api_key = vast_api_key
        self.api_url = "https://console.vast.ai/api/v0"

    async def search_offers(
        self,
        gpu_name: Optional[str] = None,
        min_gpus: int = 1,
        max_price: Optional[float] = None,
        verified: bool = True,
        min_reliability: float = 0.9,
        geolocation: Optional[str] = None,
    ) -> List[GPUOffer]:
        """
        Busca ofertas de GPU no VAST.ai.

        Args:
            gpu_name: Nome da GPU (ex: "RTX_4090", "A100")
            min_gpus: Numero minimo de GPUs
            max_price: Preco maximo por hora
            verified: Apenas hosts verificados
            min_reliability: Confiabilidade minima (0-1)
            geolocation: Codigo de pais (ex: "US", "DE")

        Returns:
            Lista de ofertas de GPU
        """
        try:
            # Construir query
            query = {
                "verified": {"eq": verified},
                "rentable": {"eq": True},
                "num_gpus": {"gte": min_gpus},
                "reliability2": {"gte": min_reliability},
            }

            if gpu_name:
                query["gpu_name"] = {"eq": gpu_name}

            if max_price:
                query["dph_total"] = {"lte": max_price}

            if geolocation:
                query["geolocation"] = {"eq": geolocation}

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }

                async with session.get(
                    f"{self.api_url}/bundles/",
                    headers=headers,
                    params={"q": str(query)}
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"VAST API error: {response.status} - {text}")
                        return []

                    data = await response.json()
                    offers_data = data.get("offers", [])

                    offers = []
                    for offer_data in offers_data:
                        try:
                            offer = GPUOffer(
                                offer_id=offer_data.get("id"),
                                machine_id=offer_data.get("machine_id"),
                                gpu_name=offer_data.get("gpu_name", ""),
                                num_gpus=offer_data.get("num_gpus", 1),
                                gpu_ram_mb=offer_data.get("gpu_ram", 0),
                                cpu_cores=offer_data.get("cpu_cores", 0),
                                ram_mb=offer_data.get("cpu_ram", 0),
                                disk_space_gb=offer_data.get("disk_space", 0),
                                price_per_hour=offer_data.get("dph_total", 0),
                                reliability=offer_data.get("reliability2", 0),
                                verified=offer_data.get("verified", False),
                                static_ip=offer_data.get("static_ip", False),
                                geolocation=offer_data.get("geolocation", ""),
                                inet_up_bps=offer_data.get("inet_up_bps", 0),
                                inet_down_bps=offer_data.get("inet_down_bps", 0),
                                cuda_max_good=offer_data.get("cuda_max_good", ""),
                                rentable=offer_data.get("rentable", False),
                            )
                            offers.append(offer)
                        except Exception as e:
                            logger.warning(f"Failed to parse offer: {e}")
                            continue

                    logger.info(f"Found {len(offers)} GPU offers")
                    return offers

        except Exception as e:
            logger.error(f"Failed to search offers: {e}")
            return []

    async def find_multi_gpu_hosts(
        self,
        gpu_name: Optional[str] = None,
        min_gpus: int = 2,
        max_price: Optional[float] = None,
        verified: bool = True,
        preferred_gpu_names: Optional[List[str]] = None,
    ) -> List[MultiGPUHost]:
        """
        Busca hosts com multiplas GPUs disponiveis.

        Args:
            gpu_name: Nome especifico da GPU
            min_gpus: Numero minimo de GPUs por host
            max_price: Preco maximo por GPU por hora
            verified: Apenas hosts verificados
            preferred_gpu_names: Lista de GPUs preferidas

        Returns:
            Lista de hosts com multiplas GPUs
        """
        # Se nao especificou GPU, buscar todas as preferidas
        gpu_names_to_search = [gpu_name] if gpu_name else (preferred_gpu_names or [None])

        all_offers = []
        for gpu in gpu_names_to_search:
            offers = await self.search_offers(
                gpu_name=gpu,
                min_gpus=1,  # Buscar todas, vamos agrupar depois
                max_price=max_price,
                verified=verified,
            )
            all_offers.extend(offers)

        # Agrupar por machine_id
        hosts_map: Dict[int, List[GPUOffer]] = {}
        for offer in all_offers:
            if offer.machine_id not in hosts_map:
                hosts_map[offer.machine_id] = []
            hosts_map[offer.machine_id].append(offer)

        # Filtrar hosts com multiplas GPUs
        multi_gpu_hosts = []
        for machine_id, offers in hosts_map.items():
            # Contar GPUs disponiveis
            total_gpus = sum(o.num_gpus for o in offers)

            if total_gpus < min_gpus:
                continue

            # Calcular metricas agregadas
            avg_price = sum(o.price_per_hour for o in offers) / len(offers)
            avg_reliability = sum(o.reliability for o in offers) / len(offers)
            verified = all(o.verified for o in offers)
            geolocation = offers[0].geolocation if offers else ""
            gpu_name = offers[0].gpu_name if offers else ""

            host = MultiGPUHost(
                machine_id=machine_id,
                total_gpus=total_gpus,
                available_gpus=len(offers),  # Numero de slots disponiveis
                gpu_name=gpu_name,
                offers=offers,
                avg_price_per_hour=avg_price,
                reliability=avg_reliability,
                verified=verified,
                geolocation=geolocation,
            )

            multi_gpu_hosts.append(host)

        # Ordenar por melhor custo-beneficio (reliability / price)
        multi_gpu_hosts.sort(
            key=lambda h: (h.reliability / max(h.avg_price_per_hour, 0.01)),
            reverse=True
        )

        logger.info(f"Found {len(multi_gpu_hosts)} hosts with {min_gpus}+ GPUs")
        return multi_gpu_hosts

    async def get_host_by_machine_id(self, machine_id: int) -> Optional[MultiGPUHost]:
        """
        Busca um host especifico pelo machine_id.

        Args:
            machine_id: ID da maquina

        Returns:
            Host ou None se nao encontrado
        """
        try:
            # Buscar ofertas do mesmo machine_id
            all_offers = await self.search_offers(min_gpus=1, verified=False)

            host_offers = [o for o in all_offers if o.machine_id == machine_id]

            if not host_offers:
                return None

            total_gpus = sum(o.num_gpus for o in host_offers)
            avg_price = sum(o.price_per_hour for o in host_offers) / len(host_offers)
            avg_reliability = sum(o.reliability for o in host_offers) / len(host_offers)

            return MultiGPUHost(
                machine_id=machine_id,
                total_gpus=total_gpus,
                available_gpus=len(host_offers),
                gpu_name=host_offers[0].gpu_name,
                offers=host_offers,
                avg_price_per_hour=avg_price,
                reliability=avg_reliability,
                verified=host_offers[0].verified,
                geolocation=host_offers[0].geolocation,
            )

        except Exception as e:
            logger.error(f"Failed to get host {machine_id}: {e}")
            return None

    def search_offers_sync(self, **kwargs) -> List[GPUOffer]:
        """Versao sincrona de search_offers"""
        return asyncio.get_event_loop().run_until_complete(
            self.search_offers(**kwargs)
        )

    def find_multi_gpu_hosts_sync(self, **kwargs) -> List[MultiGPUHost]:
        """Versao sincrona de find_multi_gpu_hosts"""
        return asyncio.get_event_loop().run_until_complete(
            self.find_multi_gpu_hosts(**kwargs)
        )
