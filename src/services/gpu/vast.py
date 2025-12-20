"""
Service para interacao com a API do vast.ai
"""
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class GpuOffer:
    """Representa uma oferta de GPU"""
    id: int
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    inet_down: float
    inet_up: float
    dph_total: float
    geolocation: str
    reliability: float
    cuda_version: str
    verified: bool
    static_ip: bool


class VastService:
    """Service para gerenciar instancias vast.ai"""

    API_URL = "https://console.vast.ai/api/v0"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        min_gpu_ram: float = 0,
        min_cpu_cores: int = 1,
        min_cpu_ram: float = 1,
        min_disk: float = 50,
        min_inet_down: float = 500,
        max_price: float = 1.0,
        min_cuda: str = "11.0",
        min_reliability: float = 0.0,
        region: Optional[str] = None,
        verified_only: bool = False,
        static_ip: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Busca ofertas de GPU com filtros"""
        import json

        print(f"[DEBUG search_offers] gpu_name={gpu_name}, min_inet_down={min_inet_down}, "
              f"max_price={max_price}, min_disk={min_disk}, region={region}, "
              f"min_reliability={min_reliability}, verified_only={verified_only}")

        query = {
            "rentable": {"eq": True},
            "num_gpus": {"eq": num_gpus},
            "disk_space": {"gte": min_disk},
            "inet_down": {"gte": min_inet_down},
            "dph_total": {"lte": max_price},
        }

        if verified_only:
            query["verified"] = {"eq": True}

        if gpu_name:
            query["gpu_name"] = {"eq": gpu_name}

        if static_ip:
            query["static_ip"] = {"eq": True}

        params = {
            "q": json.dumps(query),
            "order": "dph_total",
            "type": "on-demand",
            "limit": limit,
        }

        try:
            resp = requests.get(
                f"{self.API_URL}/bundles",
                params=params,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            offers = data.get("offers", []) if isinstance(data, dict) else data

            if region:
                region_codes = self._get_region_codes(region)
                offers = [
                    o for o in offers
                    if any(code in str(o.get("geolocation", "")) for code in region_codes)
                ]

            print(f"[DEBUG search_offers] API retornou {len(offers)} ofertas, apos filtro regiao: {len(offers)}")
            return offers
        except Exception as e:
            print(f"Erro ao buscar ofertas: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _get_region_codes(self, region: str) -> List[str]:
        """Retorna codigos de paises para uma regiao"""
        regions = {
            "EU": ["ES", "DE", "FR", "NL", "IT", "PL", "CZ", "BG", "UK", "GB",
                   "Spain", "Germany", "France", "Netherlands", "Poland",
                   "Czechia", "Bulgaria", "Sweden", "Norway", "Finland"],
            "US": ["US", "United States", "CA", "Canada"],
            "ASIA": ["JP", "Japan", "KR", "Korea", "SG", "Singapore", "TW", "Taiwan"],
        }
        return regions.get(region.upper(), [])

    def create_instance(
        self,
        offer_id: int,
        image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        disk: int = 50,
        docker_options: Optional[str] = None,
        tailscale_authkey: Optional[str] = None,
        instance_id_hint: Optional[int] = None,
        template_id: Optional[int] = None,
        ports: Optional[List[int]] = None,
        onstart_cmd: Optional[str] = None,
        use_template: bool = True,
    ) -> Optional[int]:
        """
        Cria uma nova instancia.

        Args:
            offer_id: ID da oferta
            image: Imagem Docker (usado se use_template=False)
            disk: Espaco em disco (GB)
            docker_options: Opcoes extras do Docker
            tailscale_authkey: Chave do Tailscale (opcional)
            instance_id_hint: Hint para hostname
            template_id: ID do template vast.ai (se especificado e use_template=True)
            ports: Lista de portas TCP para abrir
            onstart_cmd: Comando para executar no startup (usado se use_template=False)
            use_template: Se True, usa template. Se False, usa imagem diretamente
        """
        import os

        # Usar portas padrao se nao especificado
        if ports is None:
            default_ports_str = os.environ.get("VAST_DEFAULT_PORTS", "3000,5173,7860,8000,8080")
            ports = [int(p.strip()) for p in default_ports_str.split(",") if p.strip()]

        # Script de startup
        onstart_script = "touch ~/.no_auto_tmux"
        
        # Adicionar comando customizado se fornecido
        if onstart_cmd:
            onstart_script = f"#\!/bin/bash\ntouch ~/.no_auto_tmux\n{onstart_cmd}"
        elif tailscale_authkey:
            hostname = f"gpu-{instance_id_hint or new}"
            onstart_script = f"""#\!/bin/bash
touch ~/.no_auto_tmux
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey={tailscale_authkey} --hostname={hostname} --ssh &
"""

        try:
            # Montar extra_env com portas
            extra_env = []
            for port in ports:
                extra_env.append([f"-p {port}:{port}", "1"])

            payload = {
                "client_id": "me",
                "disk": disk,
                "onstart": onstart_script,
                "extra_env": extra_env,
            }

            # Decidir entre template ou imagem direta
            if use_template:
                # Usar template padrao do .env se nao especificado
                if template_id is None:
                    template_id = int(os.environ.get("VAST_DEFAULT_TEMPLATE_ID", 312840))
                payload["template_id"] = template_id
                print(f"[DEBUG create_instance] offer_id={offer_id}, TEMPLATE={template_id}, disk={disk}")
            else:
                # Usar imagem diretamente (sem template)
                payload["image"] = image
                print(f"[DEBUG create_instance] offer_id={offer_id}, IMAGE={image}, disk={disk}")

            resp = requests.put(
                f"{self.API_URL}/asks/{offer_id}/",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            instance_id = data.get("new_contract")
            print(f"[DEBUG create_instance] Criada instancia {instance_id}")
            return instance_id
        except Exception as e:
            print(f"Erro ao criar instancia: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_instance_status(self, instance_id: int) -> Dict[str, Any]:
        """Retorna status de uma instancia"""
        try:
            resp = requests.get(
                f"{self.API_URL}/instances/{instance_id}/",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            instances_data = data.get("instances")
            if isinstance(instances_data, list):
                instance = instances_data[0] if instances_data else {}
            elif isinstance(instances_data, dict):
                instance = instances_data
            else:
                instance = data

            return {
                "id": instance.get("id"),
                "status": instance.get("actual_status", "unknown"),
                "ssh_host": instance.get("ssh_host"),
                "ssh_port": instance.get("ssh_port"),
                "gpu_name": instance.get("gpu_name"),
                "num_gpus": instance.get("num_gpus"),
                "public_ipaddr": instance.get("public_ipaddr"),
                "ports": instance.get("ports", {}),
            }
        except Exception as e:
            return {"error": str(e), "status": "error"}

    def destroy_instance(self, instance_id: int) -> bool:
        """Destroi uma instancia"""
        try:
            resp = requests.delete(
                f"{self.API_URL}/instances/{instance_id}/",
                headers=self.headers,
                timeout=30,
            )
            return resp.status_code in [200, 204]
        except Exception as e:
            print(f"Erro ao destruir instancia: {e}")
            return False

    def pause_instance(self, instance_id: int) -> bool:
        """Pausa uma instancia (stop sem destruir)"""
        try:
            resp = requests.put(
                f"{self.API_URL}/instances/{instance_id}/",
                headers={"Accept": "application/json"},
                params={"api_key": self.api_key},
                json={"paused": True},
                timeout=30,
            )
            return resp.status_code == 200 and resp.json().get("success", False)
        except Exception as e:
            print(f"Erro ao pausar instancia: {e}")
            return False

    def resume_instance(self, instance_id: int) -> bool:
        """Resume uma instancia pausada"""
        try:
            resp = requests.put(
                f"{self.API_URL}/instances/{instance_id}/",
                headers={"Accept": "application/json"},
                params={"api_key": self.api_key},
                json={"paused": False},
                timeout=30,
            )
            return resp.status_code == 200 and resp.json().get("success", False)
        except Exception as e:
            print(f"Erro ao resumir instancia: {e}")
            return False

    def get_instance_logs(self, instance_id: int) -> str:
        """Retorna logs de uma instancia"""
        try:
            resp = requests.get(
                f"{self.API_URL}/instances/{instance_id}/",
                headers=self.headers,
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                instances_data = data.get("instances")
                if isinstance(instances_data, list):
                    instance = instances_data[0] if instances_data else {}
                elif isinstance(instances_data, dict):
                    instance = instances_data
                else:
                    instance = data

                logs_parts = []
                status_msg = instance.get("status_msg", "")
                if status_msg:
                    logs_parts.append(f"Status: {status_msg}")

                actual_status = instance.get("actual_status", "unknown")
                logs_parts.append(f"Estado atual: {actual_status}")

                ssh_host = instance.get("ssh_host")
                ssh_port = instance.get("ssh_port")
                if ssh_host and ssh_port:
                    logs_parts.append(f"SSH: {ssh_host}:{ssh_port}")

                public_ip = instance.get("public_ipaddr")
                if public_ip:
                    logs_parts.append(f"IP publico: {public_ip}")

                gpu_name = instance.get("gpu_name")
                num_gpus = instance.get("num_gpus")
                if gpu_name:
                    logs_parts.append(f"GPU: {num_gpus}x {gpu_name}")

                disk_space = instance.get("disk_space")
                disk_usage = instance.get("disk_usage")
                if disk_space:
                    logs_parts.append(f"Disco: {disk_usage or 0:.1f}GB / {disk_space:.1f}GB")

                start_date = instance.get("start_date")
                if start_date:
                    import time
                    uptime_secs = time.time() - start_date
                    hours = int(uptime_secs // 3600)
                    mins = int((uptime_secs % 3600) // 60)
                    logs_parts.append(f"Uptime: {hours}h {mins}min")

                dph_total = instance.get("dph_total")
                if dph_total:
                    logs_parts.append(f"Custo: ${dph_total:.4f}/hora")

                ports = instance.get("ports", {})
                if ports:
                    port_list = [f"{k}" for k in ports.keys() if k]
                    if port_list:
                        logs_parts.append(f"Portas: {', '.join(port_list[:5])}")

                if logs_parts:
                    return "\n".join(logs_parts)
                return "Nenhuma informacao de log disponivel."

            return f"Erro ao buscar logs: Status {resp.status_code}"
        except Exception as e:
            return f"Erro ao buscar logs: {e}"

    def get_my_instances(self) -> List[Dict[str, Any]]:
        """Lista todas as instancias do usuario"""
        try:
            resp = requests.get(
                f"{self.API_URL}/instances/",
                params={"owner": "me"},
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("instances", [])
        except Exception as e:
            print(f"Erro ao listar instancias: {e}")
            return []

    def get_balance(self) -> Dict[str, Any]:
        """Retorna o saldo da conta vast.ai"""
        try:
            resp = requests.get(
                f"{self.API_URL}/users/current/",
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "credit": data.get("credit", 0),
                "balance": data.get("balance", 0),
                "balance_threshold": data.get("balance_threshold", 0),
                "email": data.get("email", ""),
            }
        except Exception as e:
            print(f"Erro ao buscar saldo: {e}")
            return {"error": str(e), "credit": 0}

    def search_cpu_offers(
        self,
        min_cpu_cores: int = 4,
        min_cpu_ram: float = 8,
        min_disk: float = 50,
        min_inet_down: float = 100,
        max_price: float = 0.10,
        region: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Busca ofertas de instancias CPU-only (sem GPU)."""
        import json

        print(f"[DEBUG search_cpu_offers] min_cpu_cores={min_cpu_cores}, min_cpu_ram={min_cpu_ram}, "
              f"max_price={max_price}, min_disk={min_disk}, region={region}")

        query = {
            "rentable": {"eq": True},
            "num_gpus": {"eq": 0},
            "cpu_cores_effective": {"gte": min_cpu_cores},
            "cpu_ram": {"gte": min_cpu_ram * 1024},
            "disk_space": {"gte": min_disk},
            "inet_down": {"gte": min_inet_down},
            "dph_total": {"lte": max_price},
        }

        params = {
            "q": json.dumps(query),
            "order": "dph_total",
            "type": "on-demand",
            "limit": limit,
        }

        try:
            resp = requests.get(
                f"{self.API_URL}/bundles",
                params=params,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            offers = data.get("offers", []) if isinstance(data, dict) else data

            if region:
                region_codes = self._get_region_codes(region)
                offers = [
                    o for o in offers
                    if any(code in str(o.get("geolocation", "")) for code in region_codes)
                ]

            print(f"[DEBUG search_cpu_offers] API retornou {len(offers)} ofertas CPU-only")
            return offers
        except Exception as e:
            print(f"Erro ao buscar ofertas CPU: {e}")
            import traceback
            traceback.print_exc()
            return []

    def create_cpu_instance(
        self,
        offer_id: int,
        disk: int = 50,
        instance_id_hint: Optional[int] = None,
        ports: Optional[List[int]] = None,
    ) -> Optional[int]:
        """Cria uma instancia CPU-only (sem GPU)."""
        import os

        if ports is None:
            default_ports_str = os.environ.get("VAST_DEFAULT_PORTS", "3000,5173,7860,8000,8080")
            ports = [int(p.strip()) for p in default_ports_str.split(",") if p.strip()]

        onstart_script = """#\!/bin/bash
touch ~/.no_auto_tmux
apt-get update -qq && apt-get install -y -qq rsync rclone restic
"""

        try:
            extra_env = []
            for port in ports:
                extra_env.append([f"-p {port}:{port}", "1"])

            payload = {
                "client_id": "me",
                "image": "ubuntu:22.04",
                "disk": disk,
                "onstart": onstart_script,
                "extra_env": extra_env,
            }

            print(f"[DEBUG create_cpu_instance] offer_id={offer_id}, disk={disk}, ports={ports}")

            resp = requests.put(
                f"{self.API_URL}/asks/{offer_id}/",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            instance_id = data.get("new_contract")
            print(f"[DEBUG create_cpu_instance] Criada instancia CPU {instance_id}")
            return instance_id
        except Exception as e:
            print(f"Erro ao criar instancia CPU: {e}")
            import traceback
            traceback.print_exc()
            return None
