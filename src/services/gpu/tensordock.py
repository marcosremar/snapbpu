"""
TensorDock GPU Provider

Provider para provisionar GPUs via TensorDock API.
TensorDock é ideal para serverless porque:
- Suporta cuda-checkpoint nativamente (bare metal)
- Cold start rápido (~20s para deploy)
- API simples para start/stop

Endpoints API v2:
- GET    /api/v2/instances          - Listar instâncias
- GET    /api/v2/instances/{id}     - Detalhes da instância
- POST   /api/v2/instances          - Criar instância
- POST   /api/v2/instances/{id}/start  - Iniciar
- POST   /api/v2/instances/{id}/stop   - Parar
- DELETE /api/v2/instances/{id}     - Destruir
"""

import os
import time
import logging
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# API v2 com Bearer token
BASE_URL = "https://dashboard.tensordock.com/api/v2"


@dataclass
class TensorDockInstance:
    """Representa uma instância TensorDock"""
    id: str
    name: str
    status: str
    gpu_model: str
    gpu_count: int
    vcpu: int
    ram_gb: int
    storage_gb: int
    ip_address: Optional[str] = None
    ssh_port: int = 22
    hourly_cost: float = 0.0
    location: Optional[str] = None


class TensorDockService:
    """
    Serviço para gerenciar GPUs no TensorDock.

    Features:
    - Deploy de VMs com GPU
    - Start/Stop para serverless
    - Suporte a cuda-checkpoint

    API v2: https://dashboard.tensordock.com/api/v2
    Auth: Bearer token
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
    ):
        """
        Args:
            api_token: TensorDock API Token (Bearer)
        """
        self.api_token = api_token or os.environ.get("TENSORDOCK_API_TOKEN", "")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Faz requisição autenticada à API v2"""
        url = f"{BASE_URL}{endpoint}"

        try:
            if method.upper() == "GET":
                response = self._session.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self._session.post(url, json=data, params=params, timeout=60)
            elif method.upper() == "PUT":
                response = self._session.put(url, json=data, params=params, timeout=60)
            elif method.upper() == "DELETE":
                response = self._session.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Método não suportado: {method}")

            response.raise_for_status()
            # DELETE pode retornar 204 No Content
            if response.status_code == 204 or not response.content:
                return {"success": True}
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"TensorDock API error: {e.response.status_code} - {e.response.text}")
            # Tentar extrair mensagem de erro do JSON
            try:
                error_data = e.response.json()
                if isinstance(error_data, list) and error_data:
                    error_msg = error_data[0].get("message", str(e))
                elif isinstance(error_data, dict):
                    error_msg = error_data.get("message", error_data.get("error", str(e)))
                else:
                    error_msg = str(e)
            except:
                error_msg = e.response.text or str(e)
            raise ValueError(error_msg) from e
        except Exception as e:
            logger.error(f"TensorDock request error: {e}")
            raise

    # =========================================================================
    # LISTING
    # =========================================================================

    def list_instances(self) -> List[TensorDockInstance]:
        """Lista todas as instâncias do usuário (API v2)"""
        try:
            result = self._request("GET", "/instances")

            instances = []
            # API v2 retorna {"data": [...]}
            for vm in result.get("data", []):
                attrs = vm.get("attributes", vm)
                resources = attrs.get("resources", {})
                gpus = resources.get("gpus", {})

                # Pegar primeiro modelo de GPU
                gpu_model = ""
                gpu_count = 0
                for model, info in gpus.items():
                    gpu_model = model
                    gpu_count = info.get("count", 1)
                    break

                instances.append(TensorDockInstance(
                    id=vm.get("id", ""),
                    name=attrs.get("name", ""),
                    status=attrs.get("status", "unknown"),
                    gpu_model=gpu_model,
                    gpu_count=gpu_count,
                    vcpu=resources.get("vcpu_count", 0),
                    ram_gb=resources.get("ram_gb", 0),
                    storage_gb=resources.get("storage_gb", 0),
                    ip_address=attrs.get("networking", {}).get("ip_address"),
                    ssh_port=attrs.get("networking", {}).get("ports", {}).get("22", 22),
                    hourly_cost=attrs.get("cost_per_hour", 0),
                    location=attrs.get("location_id"),
                ))

            return instances

        except Exception as e:
            logger.error(f"Erro listando instâncias: {e}")
            return []

    def get_instance(self, instance_id: str) -> Optional[TensorDockInstance]:
        """Retorna detalhes de uma instância (API v2)"""
        try:
            result = self._request("GET", f"/instances/{instance_id}")

            vm = result.get("data", {})
            if not vm:
                return None

            attrs = vm.get("attributes", vm)
            resources = attrs.get("resources", {})
            gpus = resources.get("gpus", {})
            networking = attrs.get("networking", {})

            # Pegar primeiro modelo de GPU
            gpu_model = ""
            gpu_count = 0
            for model, info in gpus.items():
                gpu_model = model
                gpu_count = info.get("count", 1)
                break

            return TensorDockInstance(
                id=vm.get("id", instance_id),
                name=attrs.get("name", ""),
                status=attrs.get("status", "unknown"),
                gpu_model=gpu_model,
                gpu_count=gpu_count,
                vcpu=resources.get("vcpu_count", 0),
                ram_gb=resources.get("ram_gb", 0),
                storage_gb=resources.get("storage_gb", 0),
                ip_address=networking.get("ip_address"),
                ssh_port=networking.get("ports", {}).get("22", 22),
                hourly_cost=attrs.get("cost_per_hour", 0),
                location=attrs.get("location_id"),
            )

        except Exception as e:
            logger.error(f"Erro obtendo instância {instance_id}: {e}")
            return None

    def get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """Retorna status da instância (compatível com interface VAST)"""
        instance = self.get_instance(instance_id)
        if not instance:
            return {"status": "not_found"}

        return {
            "instance_id": instance.id,
            "actual_status": instance.status,
            "gpu_name": instance.gpu_model,
            "gpu_count": instance.gpu_count,
            "ssh_host": instance.ip_address,
            "ssh_port": instance.ssh_port,
            "dph_total": instance.hourly_cost,
        }

    # =========================================================================
    # LOCATIONS / HOSTNODES
    # =========================================================================

    def list_locations(self) -> List[Dict]:
        """Lista locations disponíveis (API v2)"""
        try:
            result = self._request("GET", "/locations")
            locations = []

            # API v2: {"data": {"locations": [...]}}
            data = result.get("data", {})
            locs_list = data.get("locations", []) if isinstance(data, dict) else []

            for loc in locs_list:
                gpus_list = loc.get("gpus", [])
                locations.append({
                    "id": loc.get("id"),
                    "city": loc.get("city", ""),
                    "country": loc.get("country", ""),
                    "tier": loc.get("tier"),
                    "gpus": [g.get("displayName") for g in gpus_list],
                })

            return locations

        except Exception as e:
            logger.error(f"Erro listando locations: {e}")
            return []

    def list_hostnodes(
        self,
        gpu_model: Optional[str] = None,
        min_gpu_count: int = 1,
    ) -> List[Dict]:
        """Lista hostnodes disponíveis com GPUs (API v2)"""
        try:
            result = self._request("GET", "/hostnodes")

            hostnodes = []
            # API v2: {"data": {"hostnodes": [...]}}
            data = result.get("data", {})
            nodes_list = data.get("hostnodes", []) if isinstance(data, dict) else []

            for node in nodes_list:
                available = node.get("available_resources", {})
                gpus_list = available.get("gpus", [])
                location = node.get("location", {})

                for gpu in gpus_list:
                    gpu_name = gpu.get("v0Name", "")
                    available_count = gpu.get("availableCount", 0)

                    # Filtrar por GPU model se especificado
                    if gpu_model and gpu_model.lower() not in gpu_name.lower():
                        continue

                    if available_count >= min_gpu_count:
                        hostnodes.append({
                            "hostnode_id": node.get("id"),
                            "location_id": node.get("location_id"),
                            "city": location.get("city", ""),
                            "country": location.get("country", ""),
                            "gpu_model": gpu_name,
                            "gpu_count": available_count,
                            "price_per_hour": gpu.get("price_per_hr", 0),
                        })

            return hostnodes

        except Exception as e:
            logger.error(f"Erro listando hostnodes: {e}")
            return []

    # =========================================================================
    # DEPLOY
    # =========================================================================

    def deploy(
        self,
        name: str,
        gpu_model: str,
        gpu_count: int = 1,
        vcpu: int = 4,
        ram_gb: int = 16,
        storage_gb: int = 100,
        operating_system: str = "ubuntu2404_nvidia_550",
        ssh_key: Optional[str] = None,
        location_id: Optional[str] = None,
        cloud_init: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deploy de nova instância GPU (API v2).

        Args:
            name: Nome da instância
            gpu_model: Modelo da GPU (ex: "A100_PCIE_80GB")
            gpu_count: Quantidade de GPUs
            vcpu: Número de vCPUs
            ram_gb: RAM em GB
            storage_gb: Storage em GB (mínimo 100)
            operating_system: Sistema operacional
            ssh_key: Chave SSH pública (obrigatória)
            location_id: ID da location (opcional - usa auto-select se não especificado)
            cloud_init: Script cloud-init (opcional)
        """
        if not ssh_key:
            # Tentar ler chave SSH padrão
            for key_path in ["~/.ssh/id_ed25519.pub", "~/.ssh/id_rsa.pub"]:
                expanded = os.path.expanduser(key_path)
                if os.path.exists(expanded):
                    with open(expanded) as f:
                        ssh_key = f.read().strip()
                    break
            else:
                raise ValueError("SSH key obrigatória para deploy")

        # Formato JSON:API v2
        data = {
            "data": {
                "type": "virtualmachine",
                "attributes": {
                    "name": name,
                    "type": "virtualmachine",
                    "image": operating_system,
                    "resources": {
                        "vcpu_count": vcpu,
                        "ram_gb": ram_gb,
                        "storage_gb": storage_gb,
                        "gpus": {
                            gpu_model: {"count": gpu_count}
                        }
                    },
                    "ssh_key": ssh_key,
                    # Port forwarding obrigatório para SSH (external=0 = auto-assign)
                    "port_forwards": [
                        {"protocol": "tcp", "internal_port": 22, "external_port": 22}
                    ],
                }
            }
        }

        if location_id:
            data["data"]["attributes"]["location_id"] = location_id

        if cloud_init:
            data["data"]["attributes"]["cloud_init"] = cloud_init

        try:
            # API v2: POST /instances para criar nova instância
            result = self._request("POST", "/instances", data=data)

            # API v2 retorna {"data": {"id": "...", "attributes": {...}}}
            vm_data = result.get("data", {})
            if vm_data:
                attrs = vm_data.get("attributes", {})
                networking = attrs.get("networking", {})
                return {
                    "success": True,
                    "instance_id": vm_data.get("id"),
                    "ip_address": networking.get("ip_address"),
                    "ssh_port": networking.get("ports", {}).get("22", 22),
                    "password": attrs.get("password"),  # Para Windows
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", result.get("errors", "Deploy failed")),
                }

        except Exception as e:
            logger.error(f"Erro no deploy: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # LIFECYCLE (START/STOP/DELETE)
    # =========================================================================

    def start_instance(self, instance_id: str) -> bool:
        """Inicia uma instância parada (API v2)"""
        try:
            result = self._request("POST", f"/instances/{instance_id}/start")
            # API v2 retorna {"data": {...}} em caso de sucesso
            success = "data" in result or result.get("success", False)
            if success:
                logger.info(f"Instância {instance_id} iniciada")
            return success
        except Exception as e:
            logger.error(f"Erro iniciando instância {instance_id}: {e}")
            return False

    def stop_instance(self, instance_id: str) -> bool:
        """Para uma instância em execução (API v2)"""
        try:
            result = self._request("POST", f"/instances/{instance_id}/stop")
            # API v2 retorna {"data": {...}} em caso de sucesso
            success = "data" in result or result.get("success", False)
            if success:
                logger.info(f"Instância {instance_id} parada")
            return success
        except Exception as e:
            logger.error(f"Erro parando instância {instance_id}: {e}")
            return False

    def destroy_instance(self, instance_id: str) -> bool:
        """Destrói uma instância (API v2)"""
        try:
            result = self._request("DELETE", f"/instances/{instance_id}")
            # DELETE pode retornar 204 No Content ou {"data": null}
            success = True  # Se não deu exceção, funcionou
            logger.info(f"Instância {instance_id} destruída")
            return success
        except Exception as e:
            logger.error(f"Erro destruindo instância {instance_id}: {e}")
            return False

    # Aliases para compatibilidade com interface VAST
    def pause_instance(self, instance_id: str) -> bool:
        """Alias para stop_instance (compatibilidade VAST)"""
        return self.stop_instance(instance_id)

    def resume_instance(self, instance_id: str) -> bool:
        """Alias para start_instance (compatibilidade VAST)"""
        return self.start_instance(instance_id)

    # =========================================================================
    # WAIT HELPERS
    # =========================================================================

    def wait_for_status(
        self,
        instance_id: str,
        target_status: str,
        timeout: int = 300,
        poll_interval: float = 3.0,
    ) -> bool:
        """Aguarda instância atingir status específico"""
        start = time.time()

        while time.time() - start < timeout:
            instance = self.get_instance(instance_id)
            if instance and instance.status.lower() == target_status.lower():
                return True
            time.sleep(poll_interval)

        return False

    def wait_for_ssh(
        self,
        instance_id: str,
        timeout: int = 300,
    ) -> Optional[Dict[str, Any]]:
        """Aguarda SSH estar disponível"""
        import subprocess

        start = time.time()

        while time.time() - start < timeout:
            instance = self.get_instance(instance_id)
            if not instance or not instance.ip_address:
                time.sleep(3)
                continue

            # Testar SSH
            try:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null",
                        "-o", "ConnectTimeout=5",
                        "-p", str(instance.ssh_port),
                        f"root@{instance.ip_address}",
                        "echo SSH_OK",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if "SSH_OK" in result.stdout:
                    return {
                        "ssh_host": instance.ip_address,
                        "ssh_port": instance.ssh_port,
                        "instance_id": instance_id,
                    }

            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                logger.debug(f"SSH test failed: {e}")

            time.sleep(3)

        return None

    # =========================================================================
    # DEPLOY WITH WAIT
    # =========================================================================

    def deploy_and_wait(
        self,
        name: str,
        gpu_model: str,
        gpu_count: int = 1,
        vcpu: int = 4,
        ram_gb: int = 16,
        storage_gb: int = 100,
        ssh_key: Optional[str] = None,
        cloud_init: Optional[str] = None,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Deploy e aguarda SSH estar disponível"""
        deploy_result = self.deploy(
            name=name,
            gpu_model=gpu_model,
            gpu_count=gpu_count,
            vcpu=vcpu,
            ram_gb=ram_gb,
            storage_gb=storage_gb,
            ssh_key=ssh_key,
            cloud_init=cloud_init,
        )

        if not deploy_result.get("success"):
            return deploy_result

        instance_id = deploy_result["instance_id"]
        logger.info(f"Deploy iniciado, aguardando SSH para {instance_id}...")

        ssh_info = self.wait_for_ssh(instance_id, timeout=timeout)

        if ssh_info:
            return {
                "success": True,
                "instance_id": instance_id,
                "ssh_host": ssh_info["ssh_host"],
                "ssh_port": ssh_info["ssh_port"],
                "ip_address": deploy_result.get("ip_address"),
            }
        else:
            # Destruir instância se SSH não ficou disponível
            self.destroy_instance(instance_id)
            return {
                "success": False,
                "error": "SSH timeout - instance destroyed",
                "instance_id": instance_id,
            }


# Singleton
_tensordock_service: Optional[TensorDockService] = None


def get_tensordock_service() -> TensorDockService:
    """Retorna instância singleton do serviço"""
    global _tensordock_service
    if _tensordock_service is None:
        _tensordock_service = TensorDockService()
    return _tensordock_service
