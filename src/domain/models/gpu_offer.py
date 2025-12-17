"""
Domain model for GPU offers
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GpuOffer:
    """Represents a GPU offer from a provider"""
    id: int
    gpu_name: str
    num_gpus: int
    gpu_ram: float  # GB
    cpu_cores: int
    cpu_ram: float  # GB
    disk_space: float  # GB
    inet_down: float  # Mbps
    inet_up: float  # Mbps
    dph_total: float  # Price per hour
    geolocation: str
    reliability: float
    cuda_version: str
    verified: bool
    static_ip: bool
    storage_cost: Optional[float] = None
    inet_up_cost: Optional[float] = None
    inet_down_cost: Optional[float] = None
    machine_id: Optional[int] = None
    hostname: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'gpu_name': self.gpu_name,
            'num_gpus': self.num_gpus,
            'gpu_ram': self.gpu_ram,
            'cpu_cores': self.cpu_cores,
            'cpu_ram': self.cpu_ram,
            'disk_space': self.disk_space,
            'inet_down': self.inet_down,
            'inet_up': self.inet_up,
            'dph_total': self.dph_total,
            'geolocation': self.geolocation,
            'reliability': self.reliability,
            'cuda_version': self.cuda_version,
            'verified': self.verified,
            'static_ip': self.static_ip,
            'storage_cost': self.storage_cost,
            'inet_up_cost': self.inet_up_cost,
            'inet_down_cost': self.inet_down_cost,
            'machine_id': self.machine_id,
            'hostname': self.hostname,
        }
