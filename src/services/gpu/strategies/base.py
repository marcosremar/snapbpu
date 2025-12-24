"""
Base classes for GPU Provisioning Strategies

Defines the Strategy Pattern interface and common data structures.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import time


class ProvisionStatus(str, Enum):
    """Status of a provisioning operation"""
    PENDING = "pending"
    SEARCHING = "searching"
    CREATING = "creating"
    WAITING = "waiting"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProvisionConfig:
    """
    Configuration for machine provisioning.

    Unified config used by all strategies.
    """
    # GPU requirements
    gpu_name: Optional[str] = None
    min_gpu_ram: int = 10000  # MB
    num_gpus: int = 1

    # Pricing
    max_price: float = 2.0  # $/hr
    machine_type: str = "on-demand"  # "on-demand" or "interruptible" (spot)

    # Resources
    disk_space: int = 50  # GB
    min_inet_down: int = 100  # Mbps
    min_reliability: float = 0.9  # Minimum reliability score (0-1)

    # Region
    region: str = "global"

    # Docker
    image: Optional[str] = None  # Custom image, or None for default
    onstart_cmd: Optional[str] = None
    docker_options: Optional[str] = None

    # Ports to expose
    ports: List[int] = field(default_factory=lambda: [22])

    # Labels
    label: str = "dumont:provisioned"

    # Strategy-specific options
    batch_size: int = 5  # For RaceStrategy
    batch_timeout: int = 60  # seconds
    max_batches: int = 3
    check_interval: float = 2.0  # seconds

    # SSH failover options
    max_ssh_retries: int = 3  # Max machines to try if SSH fails after win
    ssh_command_timeout: int = 30  # Timeout for SSH commands (seconds)
    verify_ssh_with_command: bool = True  # Run 'echo ok' to verify SSH works


@dataclass
class MachineCandidate:
    """
    A machine candidate during provisioning.

    Used by strategies to track provisioned instances.
    """
    instance_id: int
    offer_id: int
    gpu_name: str

    # Connection info (set when available)
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    public_ip: Optional[str] = None

    # Port mappings (set when available)
    port_mappings: Dict[int, int] = field(default_factory=dict)

    # Status
    status: str = "provisioning"  # provisioning, waiting, ready, failed
    connected: bool = False

    # Timing
    provision_start_time: float = 0.0
    ready_time: Optional[float] = None

    # Pricing
    dph_total: float = 0.0

    # Original offer for history tracking
    offer: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProvisionResult:
    """
    Result of a provisioning operation.

    Returned by all strategies.
    """
    success: bool

    # Machine info (if success)
    instance_id: Optional[int] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    public_ip: Optional[str] = None
    gpu_name: Optional[str] = None
    dph_total: float = 0.0

    # Port mappings
    port_mappings: Dict[int, int] = field(default_factory=dict)

    # Statistics
    rounds_attempted: int = 0
    machines_tried: int = 0
    machines_created: int = 0
    total_time_seconds: float = 0.0
    time_to_ready_seconds: Optional[float] = None

    # Error info (if failed)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API responses"""
        return {
            "success": self.success,
            "instance_id": self.instance_id,
            "ssh_host": self.ssh_host,
            "ssh_port": self.ssh_port,
            "public_ip": self.public_ip,
            "gpu_name": self.gpu_name,
            "dph_total": self.dph_total,
            "port_mappings": self.port_mappings,
            "rounds_attempted": self.rounds_attempted,
            "machines_tried": self.machines_tried,
            "machines_created": self.machines_created,
            "total_time_seconds": self.total_time_seconds,
            "time_to_ready_seconds": self.time_to_ready_seconds,
            "error": self.error,
        }


class ProvisioningStrategy(ABC):
    """
    Abstract base class for provisioning strategies.

    Strategies implement different approaches to provisioning:
    - RaceStrategy: Create multiple machines, first ready wins
    - SingleStrategy: Create one machine and wait
    - SpotStrategy: Use spot/interruptible instances

    Each strategy is responsible for:
    1. Creating machine(s)
    2. Waiting for readiness (SSH/port accessible)
    3. Cleaning up losers/failures
    4. Returning the result
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name"""
        pass

    @abstractmethod
    def provision(
        self,
        config: ProvisionConfig,
        vast_service: Any,  # VastService
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Execute the provisioning strategy.

        Args:
            config: Provisioning configuration
            vast_service: VastService instance for API calls
            progress_callback: Optional callback for progress updates
                               Signature: callback(status: str, message: str, progress: int)

        Returns:
            ProvisionResult with success/failure and machine info
        """
        pass

    def _test_ssh_connection(
        self,
        ssh_host: str,
        ssh_port: int,
        timeout: int = 5,
        ssh_key_path: Optional[str] = None,
    ) -> bool:
        """
        Test if SSH connection is available.

        Common utility for all strategies.
        """
        import subprocess
        import os

        # Use provided key or find default
        if ssh_key_path is None:
            ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-i", ssh_key_path,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", f"ConnectTimeout={timeout}",
                    "-o", "BatchMode=yes",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    "echo ok"
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 2,
            )
            return result.returncode == 0 and "ok" in result.stdout
        except Exception:
            return False

    def _get_mapped_port(
        self,
        ports: Dict[str, Any],
        target_port: int,
    ) -> Optional[int]:
        """
        Extract mapped port from Vast.ai ports dict.

        Ports format: {"8003/tcp": [{"HostPort": 12345}], ...}
        """
        port_key = f"{target_port}/tcp"
        if port_key in ports:
            mapped_info = ports[port_key]
            if isinstance(mapped_info, list) and mapped_info:
                return int(mapped_info[0].get("HostPort", target_port))
        return None
