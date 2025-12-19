"""
Demo GPU Provider Implementation
Returns mock data for testing and demo purposes
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...domain.repositories import IGpuProvider
from ...domain.models import GpuOffer, Instance

logger = logging.getLogger(__name__)

# Demo GPU offers data
DEMO_OFFERS = [
    # RTX 3060 offers
    {
        "id": 100001,
        "gpu_name": "RTX_3060",
        "num_gpus": 1,
        "gpu_ram": 12,
        "cpu_cores": 8,
        "cpu_ram": 32,
        "disk_space": 100,
        "inet_down": 500,
        "inet_up": 200,
        "dph_total": 0.10,
        "geolocation": "US",
        "reliability": 0.95,
        "cuda_version": "12.1",
        "verified": True,
        "static_ip": False,
        "dlperf": 15.2,
        "pcie_bw": 12.5,
    },
    {
        "id": 100002,
        "gpu_name": "RTX_3060",
        "num_gpus": 1,
        "gpu_ram": 12,
        "cpu_cores": 6,
        "cpu_ram": 24,
        "disk_space": 80,
        "inet_down": 400,
        "inet_up": 150,
        "dph_total": 0.08,
        "geolocation": "EU",
        "reliability": 0.90,
        "cuda_version": "11.8",
        "verified": False,
        "static_ip": False,
        "dlperf": 14.8,
        "pcie_bw": 11.2,
    },
    # RTX 4060 offers
    {
        "id": 100003,
        "gpu_name": "RTX_4060",
        "num_gpus": 1,
        "gpu_ram": 8,
        "cpu_cores": 8,
        "cpu_ram": 32,
        "disk_space": 100,
        "inet_down": 600,
        "inet_up": 250,
        "dph_total": 0.12,
        "geolocation": "US",
        "reliability": 0.97,
        "cuda_version": "12.2",
        "verified": True,
        "static_ip": True,
        "dlperf": 22.5,
        "pcie_bw": 15.8,
    },
    # RTX 4070 offers
    {
        "id": 100004,
        "gpu_name": "RTX_4070",
        "num_gpus": 1,
        "gpu_ram": 12,
        "cpu_cores": 12,
        "cpu_ram": 48,
        "disk_space": 150,
        "inet_down": 800,
        "inet_up": 400,
        "dph_total": 0.18,
        "geolocation": "EU",
        "reliability": 0.98,
        "cuda_version": "12.2",
        "verified": True,
        "static_ip": False,
        "dlperf": 32.1,
        "pcie_bw": 18.5,
    },
    # RTX 4080 offers
    {
        "id": 100005,
        "gpu_name": "RTX_4080",
        "num_gpus": 1,
        "gpu_ram": 16,
        "cpu_cores": 16,
        "cpu_ram": 64,
        "disk_space": 200,
        "inet_down": 1000,
        "inet_up": 500,
        "dph_total": 0.35,
        "geolocation": "US",
        "reliability": 0.99,
        "cuda_version": "12.4",
        "verified": True,
        "static_ip": True,
        "dlperf": 48.7,
        "pcie_bw": 22.3,
    },
    {
        "id": 100006,
        "gpu_name": "RTX_4080",
        "num_gpus": 1,
        "gpu_ram": 16,
        "cpu_cores": 12,
        "cpu_ram": 48,
        "disk_space": 150,
        "inet_down": 800,
        "inet_up": 350,
        "dph_total": 0.32,
        "geolocation": "EU",
        "reliability": 0.96,
        "cuda_version": "12.2",
        "verified": True,
        "static_ip": False,
        "dlperf": 46.2,
        "pcie_bw": 20.1,
    },
    # RTX 4090 offers
    {
        "id": 100007,
        "gpu_name": "RTX_4090",
        "num_gpus": 1,
        "gpu_ram": 24,
        "cpu_cores": 24,
        "cpu_ram": 128,
        "disk_space": 500,
        "inet_down": 2000,
        "inet_up": 1000,
        "dph_total": 0.70,
        "geolocation": "US",
        "reliability": 0.99,
        "cuda_version": "12.4",
        "verified": True,
        "static_ip": True,
        "dlperf": 85.3,
        "pcie_bw": 28.5,
    },
    {
        "id": 100008,
        "gpu_name": "RTX_4090",
        "num_gpus": 1,
        "gpu_ram": 24,
        "cpu_cores": 16,
        "cpu_ram": 96,
        "disk_space": 300,
        "inet_down": 1500,
        "inet_up": 750,
        "dph_total": 0.65,
        "geolocation": "EU",
        "reliability": 0.97,
        "cuda_version": "12.2",
        "verified": True,
        "static_ip": False,
        "dlperf": 82.1,
        "pcie_bw": 26.8,
    },
    # RTX 3090 offers
    {
        "id": 100009,
        "gpu_name": "RTX_3090",
        "num_gpus": 1,
        "gpu_ram": 24,
        "cpu_cores": 12,
        "cpu_ram": 64,
        "disk_space": 200,
        "inet_down": 800,
        "inet_up": 400,
        "dph_total": 0.40,
        "geolocation": "US",
        "reliability": 0.94,
        "cuda_version": "12.1",
        "verified": True,
        "static_ip": False,
        "dlperf": 55.2,
        "pcie_bw": 18.2,
    },
    # A6000 offers
    {
        "id": 100010,
        "gpu_name": "A6000",
        "num_gpus": 1,
        "gpu_ram": 48,
        "cpu_cores": 32,
        "cpu_ram": 128,
        "disk_space": 500,
        "inet_down": 2000,
        "inet_up": 1000,
        "dph_total": 1.00,
        "geolocation": "US",
        "reliability": 0.99,
        "cuda_version": "12.4",
        "verified": True,
        "static_ip": True,
        "dlperf": 95.8,
        "pcie_bw": 32.5,
    },
    # A100 offers
    {
        "id": 100011,
        "gpu_name": "A100",
        "num_gpus": 1,
        "gpu_ram": 80,
        "cpu_cores": 64,
        "cpu_ram": 256,
        "disk_space": 1000,
        "inet_down": 5000,
        "inet_up": 2500,
        "dph_total": 2.50,
        "geolocation": "US",
        "reliability": 0.99,
        "cuda_version": "12.4",
        "verified": True,
        "static_ip": True,
        "dlperf": 180.5,
        "pcie_bw": 52.0,
    },
    # H100 offers
    {
        "id": 100012,
        "gpu_name": "H100",
        "num_gpus": 1,
        "gpu_ram": 80,
        "cpu_cores": 96,
        "cpu_ram": 512,
        "disk_space": 2000,
        "inet_down": 10000,
        "inet_up": 5000,
        "dph_total": 4.00,
        "geolocation": "US",
        "reliability": 0.99,
        "cuda_version": "12.4",
        "verified": True,
        "static_ip": True,
        "dlperf": 320.0,
        "pcie_bw": 80.0,
    },
]


class DemoProvider(IGpuProvider):
    """
    Demo implementation of IGpuProvider.
    Returns mock data for testing and demo purposes.
    """

    def __init__(self):
        """Initialize Demo provider"""
        logger.info("Demo provider initialized - returning mock data")

    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        num_gpus: int = 1,
        min_gpu_ram: float = 0,
        min_cpu_cores: int = 1,
        min_cpu_ram: float = 1,
        min_disk: float = 50,
        min_inet_down: float = 100,
        max_price: float = 10.0,
        min_cuda: str = "11.0",
        min_reliability: float = 0.0,
        region: Optional[str] = None,
        verified_only: bool = False,
        static_ip: bool = False,
        limit: int = 50,
        **kwargs
    ) -> List[GpuOffer]:
        """Search for available GPU offers (returns mock data)"""
        logger.debug(f"Demo search: gpu={gpu_name}, region={region}, max_price={max_price}")

        # Filter offers based on criteria
        filtered = []
        for offer_data in DEMO_OFFERS:
            # GPU name filter
            if gpu_name and offer_data["gpu_name"] != gpu_name:
                continue

            # GPU RAM filter
            if offer_data["gpu_ram"] < min_gpu_ram:
                continue

            # Price filter
            if offer_data["dph_total"] > max_price:
                continue

            # Disk filter
            if offer_data["disk_space"] < min_disk:
                continue

            # Network filter
            if offer_data["inet_down"] < min_inet_down:
                continue

            # Reliability filter
            if offer_data["reliability"] < min_reliability:
                continue

            # Region filter
            if region:
                if region.upper() == "US" and offer_data["geolocation"] != "US":
                    continue
                if region.upper() == "EU" and offer_data["geolocation"] != "EU":
                    continue

            # Verified filter
            if verified_only and not offer_data["verified"]:
                continue

            # Static IP filter
            if static_ip and not offer_data["static_ip"]:
                continue

            filtered.append(self._parse_offer(offer_data))

        # Sort by price
        filtered.sort(key=lambda x: x.dph_total)

        # Apply limit
        return filtered[:limit]

    def create_instance(
        self,
        offer_id: int,
        image: str,
        disk_size: float,
        label: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        onstart_cmd: Optional[str] = None,
    ) -> Instance:
        """Create a new GPU instance (demo mode - not implemented)"""
        raise NotImplementedError("Demo mode: Instance creation not available")

    def get_instance(self, instance_id: int) -> Instance:
        """Get instance details by ID (demo mode - not implemented)"""
        raise NotImplementedError("Demo mode: Instance details not available")

    def list_instances(self) -> List[Instance]:
        """List all user instances (demo mode - returns empty)"""
        return []

    def destroy_instance(self, instance_id: int) -> bool:
        """Destroy an instance (demo mode - not implemented)"""
        raise NotImplementedError("Demo mode: Instance destruction not available")

    def pause_instance(self, instance_id: int) -> bool:
        """Pause an instance (demo mode - not implemented)"""
        raise NotImplementedError("Demo mode: Instance pause not available")

    def resume_instance(self, instance_id: int) -> bool:
        """Resume a paused instance (demo mode - not implemented)"""
        raise NotImplementedError("Demo mode: Instance resume not available")

    def get_instance_metrics(self, instance_id: int) -> Dict[str, Any]:
        """Get real-time metrics for an instance"""
        return {}

    def get_balance(self) -> Dict[str, Any]:
        """Get account balance (demo mode - returns mock)"""
        return {
            "credit": 100.00,
            "balance": 100.00,
            "balance_threshold": 10.00,
            "email": "demo@example.com",
        }

    def _parse_offer(self, data: Dict[str, Any]) -> GpuOffer:
        """Parse offer data to domain model"""
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
            reliability=data.get("reliability", 0),
            cuda_version=data.get("cuda_version", "Unknown"),
            verified=data.get("verified", False),
            static_ip=data.get("static_ip", False),
            dlperf=data.get("dlperf"),
            pcie_bw=data.get("pcie_bw"),
        )
