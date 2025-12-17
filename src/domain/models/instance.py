"""
Domain model for GPU instances
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Instance:
    """Represents a running GPU instance"""
    id: int
    status: str
    actual_status: str
    gpu_name: str
    num_gpus: int
    gpu_ram: float
    cpu_cores: int
    cpu_ram: float
    disk_space: float
    dph_total: float
    public_ipaddr: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    image_uuid: Optional[str] = None
    label: Optional[str] = None
    ports: Dict[str, Any] = field(default_factory=dict)
    machine_id: Optional[int] = None
    hostname: Optional[str] = None
    geolocation: Optional[str] = None
    reliability: Optional[float] = None
    cuda_version: Optional[str] = None

    # Real-time metrics
    gpu_util: Optional[float] = None
    gpu_temp: Optional[float] = None
    gpu_power: Optional[float] = None
    gpu_memory_used: Optional[float] = None
    gpu_memory_total: Optional[float] = None
    cpu_util: Optional[float] = None
    ram_used: Optional[float] = None
    ram_total: Optional[float] = None
    disk_used: Optional[float] = None
    disk_total: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'status': self.status,
            'actual_status': self.actual_status,
            'gpu_name': self.gpu_name,
            'num_gpus': self.num_gpus,
            'gpu_ram': self.gpu_ram,
            'cpu_cores': self.cpu_cores,
            'cpu_ram': self.cpu_ram,
            'disk_space': self.disk_space,
            'dph_total': self.dph_total,
            'public_ipaddr': self.public_ipaddr,
            'ssh_host': self.ssh_host,
            'ssh_port': self.ssh_port,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'image_uuid': self.image_uuid,
            'label': self.label,
            'ports': self.ports,
            'machine_id': self.machine_id,
            'hostname': self.hostname,
            'geolocation': self.geolocation,
            'reliability': self.reliability,
            'cuda_version': self.cuda_version,
            'gpu_util': self.gpu_util,
            'gpu_temp': self.gpu_temp,
            'gpu_power': self.gpu_power,
            'gpu_memory_used': self.gpu_memory_used,
            'gpu_memory_total': self.gpu_memory_total,
            'cpu_util': self.cpu_util,
            'ram_used': self.ram_used,
            'ram_total': self.ram_total,
            'disk_used': self.disk_used,
            'disk_total': self.disk_total,
        }

    @property
    def is_running(self) -> bool:
        """Check if instance is running"""
        return self.actual_status == 'running'

    @property
    def ssh_connection_string(self) -> Optional[str]:
        """Get SSH connection string"""
        if self.ssh_host and self.ssh_port:
            return f"ssh -p {self.ssh_port} root@{self.ssh_host}"
        return None
