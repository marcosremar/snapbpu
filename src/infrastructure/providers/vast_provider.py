"""
Vast.ai GPU Provider Implementation
Implements IGpuProvider interface (Dependency Inversion Principle)
"""
import json
import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...core.exceptions import VastAPIException, ServiceUnavailableException
from ...core.constants import VAST_API_URL, VAST_DEFAULT_TIMEOUT
from ...domain.repositories import IGpuProvider
from ...domain.models import GpuOffer, Instance

logger = logging.getLogger(__name__)


class VastProvider(IGpuProvider):
    """
    Vast.ai implementation of IGpuProvider.
    Handles all communication with vast.ai API.
    """

    def __init__(self, api_key: str, api_url: str = VAST_API_URL, timeout: int = VAST_DEFAULT_TIMEOUT):
        """
        Initialize Vast provider

        Args:
            api_key: Vast.ai API key
            api_url: Vast.ai API URL (optional, for testing)
            timeout: Request timeout in seconds
        """
        if not api_key:
            raise ValueError("Vast.ai API key is required")

        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout
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
    ) -> List[GpuOffer]:
        """Search for available GPU offers"""
        logger.debug(f"Searching offers: gpu={gpu_name}, region={region}, max_price={max_price}")

        # Build query for vast.ai API - minimal filters
        # NOTE: Excessive filters eliminate valid offers like RTX 5090
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
                f"{self.api_url}/bundles",
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            offers_data = data.get("offers", []) if isinstance(data, dict) else data

            # Filter by region if specified
            if region:
                region_codes = self._get_region_codes(region)
                offers_data = [
                    o for o in offers_data
                    if any(code in str(o.get("geolocation", "")) for code in region_codes)
                ]

            # Convert to domain models
            offers = []
            for offer_data in offers_data:
                try:
                    offers.append(self._parse_offer(offer_data))
                except Exception as e:
                    logger.warning(f"Failed to parse offer: {e}")
                    continue

            logger.debug(f"Found {len(offers)} offers")
            return offers

        except requests.RequestException as e:
            logger.error(f"Failed to search offers: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error searching offers: {e}")
            raise VastAPIException(f"Failed to search offers: {e}")

    def create_instance(
        self,
        offer_id: int,
        image: str,
        disk_size: float,
        label: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        onstart_cmd: Optional[str] = None,
    ) -> Instance:
        """Create a new GPU instance"""
        logger.info(f"Creating instance from offer {offer_id}")

        # Default onstart script
        if not onstart_cmd:
            onstart_cmd = "touch ~/.no_auto_tmux"

        # Parse env_vars to vast.ai format
        extra_env = []
        if env_vars:
            for key, value in env_vars.items():
                if key.startswith("PORT_"):
                    # Port mapping: PORT_8080 -> -p 8080:8080
                    port = key.replace("PORT_", "")
                    extra_env.append([f"-p {port}:{port}", "1"])
                else:
                    extra_env.append([key, value])

        payload = {
            "client_id": "me",
            "image": image,
            "disk": int(disk_size),
            "onstart": onstart_cmd,
            "extra_env": extra_env,
        }

        if label:
            payload["label"] = label

        try:
            resp = requests.put(
                f"{self.api_url}/asks/{offer_id}/",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            instance_id = data.get("new_contract")

            if not instance_id:
                raise VastAPIException("No instance ID returned from vast.ai")

            logger.info(f"Created instance {instance_id}")

            # Get full instance details
            return self.get_instance(instance_id)

        except requests.RequestException as e:
            logger.error(f"Failed to create instance: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating instance: {e}")
            raise VastAPIException(f"Failed to create instance: {e}")

    def get_instance(self, instance_id: int) -> Instance:
        """Get instance details by ID"""
        try:
            resp = requests.get(
                f"{self.api_url}/instances/{instance_id}/",
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            # vast.ai returns 'instances' as object or list
            instances_data = data.get("instances")
            if isinstance(instances_data, list):
                instance_data = instances_data[0] if instances_data else {}
            elif isinstance(instances_data, dict):
                instance_data = instances_data
            else:
                instance_data = data

            return self._parse_instance(instance_data)

        except requests.RequestException as e:
            logger.error(f"Failed to get instance {instance_id}: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting instance: {e}")
            raise VastAPIException(f"Failed to get instance: {e}")

    def list_instances(self) -> List[Instance]:
        """List all user instances"""
        try:
            resp = requests.get(
                f"{self.api_url}/instances/",
                params={"owner": "me"},
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            instances_data = data.get("instances", [])

            instances = []
            for instance_data in instances_data:
                try:
                    instances.append(self._parse_instance(instance_data))
                except Exception as e:
                    logger.warning(f"Failed to parse instance: {e}")
                    continue

            return instances

        except requests.RequestException as e:
            logger.error(f"Failed to list instances: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing instances: {e}")
            raise VastAPIException(f"Failed to list instances: {e}")

    def destroy_instance(self, instance_id: int) -> bool:
        """Destroy an instance"""
        logger.info(f"Destroying instance {instance_id}")
        try:
            resp = requests.delete(
                f"{self.api_url}/instances/{instance_id}/",
                headers=self.headers,
                timeout=self.timeout,
            )
            success = resp.status_code in [200, 204]
            if success:
                logger.info(f"Instance {instance_id} destroyed")
            return success

        except requests.RequestException as e:
            logger.error(f"Failed to destroy instance: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error destroying instance: {e}")
            return False

    def pause_instance(self, instance_id: int) -> bool:
        """Pause an instance"""
        logger.info(f"Pausing instance {instance_id}")
        try:
            resp = requests.put(
                f"{self.api_url}/instances/{instance_id}/",
                headers={"Accept": "application/json"},
                params={"api_key": self.api_key},
                json={"paused": True},
                timeout=self.timeout,
            )
            success = resp.status_code == 200 and resp.json().get("success", False)
            if success:
                logger.info(f"Instance {instance_id} paused")
            return success

        except requests.RequestException as e:
            logger.error(f"Failed to pause instance: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error pausing instance: {e}")
            return False

    def resume_instance(self, instance_id: int) -> bool:
        """Resume a paused instance"""
        logger.info(f"Resuming instance {instance_id}")
        try:
            resp = requests.put(
                f"{self.api_url}/instances/{instance_id}/",
                headers={"Accept": "application/json"},
                params={"api_key": self.api_key},
                json={"paused": False},
                timeout=self.timeout,
            )
            success = resp.status_code == 200 and resp.json().get("success", False)
            if success:
                logger.info(f"Instance {instance_id} resumed")
            return success

        except requests.RequestException as e:
            logger.error(f"Failed to resume instance: {e}")
            raise ServiceUnavailableException(f"Vast.ai API unreachable: {e}")
        except Exception as e:
            logger.error(f"Unexpected error resuming instance: {e}")
            return False

    def get_instance_metrics(self, instance_id: int) -> Dict[str, Any]:
        """Get real-time metrics for an instance (via SSH)"""
        # This would require SSH access - implement via SSH client
        # For now, return empty metrics
        logger.warning("get_instance_metrics not yet implemented via SSH")
        return {}

    def get_balance(self) -> Dict[str, Any]:
        """Get account balance (not part of IGpuProvider, but useful)"""
        try:
            resp = requests.get(
                f"{self.api_url}/users/current/",
                headers=self.headers,
                timeout=self.timeout,
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
            logger.error(f"Failed to get balance: {e}")
            return {"error": str(e), "credit": 0}

    # Helper methods

    def _get_region_codes(self, region: str) -> List[str]:
        """Get country codes for a region"""
        regions = {
            "EU": ["ES", "DE", "FR", "NL", "IT", "PL", "CZ", "BG", "UK", "GB",
                   "Spain", "Germany", "France", "Netherlands", "Poland",
                   "Czechia", "Bulgaria", "Sweden", "Norway", "Finland"],
            "US": ["US", "United States", "CA", "Canada"],
            "ASIA": ["JP", "Japan", "KR", "Korea", "SG", "Singapore", "TW", "Taiwan"],
        }
        return regions.get(region.upper(), [])

    def _parse_offer(self, data: Dict[str, Any]) -> GpuOffer:
        """Parse offer data from vast.ai API"""
        return GpuOffer(
            id=data.get("id", 0),
            gpu_name=data.get("gpu_name", "Unknown"),
            num_gpus=data.get("num_gpus", 1),
            gpu_ram=data.get("gpu_ram", 0),
            cpu_cores=data.get("cpu_cores", 0),
            cpu_ram=data.get("cpu_ram", 0),
            disk_space=data.get("disk_space", 0),
            inet_down=data.get("inet_down", 0),
            inet_up=data.get("inet_up", 0),
            dph_total=data.get("dph_total", 0),
            geolocation=data.get("geolocation", "Unknown"),
            reliability=data.get("reliability2", 0),
            cuda_version=data.get("cuda_max_good", "Unknown"),
            verified=data.get("verified", False),
            static_ip=data.get("static_ip", False),
            storage_cost=data.get("storage_cost"),
            inet_up_cost=data.get("inet_up_cost"),
            inet_down_cost=data.get("inet_down_cost"),
            machine_id=data.get("machine_id"),
            hostname=data.get("hostname"),
        )

    def _parse_instance(self, data: Dict[str, Any]) -> Instance:
        """Parse instance data from vast.ai API"""
        # Extract SSH info from ports
        ports = data.get("ports", {})
        ssh_mapping = ports.get("22/tcp", [{}])
        ssh_port = ssh_mapping[0].get("HostPort") if ssh_mapping else None

        # Parse dates
        start_date = None
        end_date = None
        if data.get("start_date"):
            try:
                start_date = datetime.fromtimestamp(data["start_date"])
            except:
                pass
        if data.get("end_date"):
            try:
                end_date = datetime.fromtimestamp(data["end_date"])
            except:
                pass

        return Instance(
            id=data.get("id", 0),
            status=data.get("intended_status", "unknown"),
            actual_status=data.get("actual_status", "unknown"),
            gpu_name=data.get("gpu_name", "Unknown"),
            num_gpus=data.get("num_gpus", 1),
            gpu_ram=data.get("gpu_ram", 0),
            cpu_cores=data.get("cpu_cores", 0),
            cpu_ram=data.get("cpu_ram", 0),
            disk_space=data.get("disk_space", 0),
            dph_total=data.get("dph_total", 0),
            public_ipaddr=data.get("public_ipaddr"),
            ssh_host=data.get("ssh_host"),
            ssh_port=ssh_port,
            start_date=start_date,
            end_date=end_date,
            image_uuid=data.get("image_uuid"),
            label=data.get("label"),
            ports=ports,
            machine_id=data.get("machine_id"),
            hostname=data.get("hostname"),
            geolocation=data.get("geolocation"),
            reliability=data.get("reliability2"),
            cuda_version=data.get("cuda_max_good"),
        )
