"""
Domain model for GPU Jobs (Execute and Destroy)

Jobs are one-time tasks that:
1. Provision a GPU
2. Execute a command/script
3. Save outputs (optional)
4. DESTROY the GPU (no hibernation, no snapshot)
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"           # Job created, waiting to start
    PROVISIONING = "provisioning" # GPU being provisioned
    STARTING = "starting"         # Instance up, running setup
    RUNNING = "running"           # Command executing
    COMPLETING = "completing"     # Saving outputs, collecting logs
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"             # Error occurred
    CANCELLED = "cancelled"       # User cancelled
    TIMEOUT = "timeout"           # Exceeded max time


class JobCompletionReason(str, Enum):
    """How the job was detected as complete"""
    MARKER_FILE = "marker_file"   # /workspace/.job_complete found
    GPU_IDLE = "gpu_idle"         # GPU < 5% for 5 minutes
    EXIT_CODE = "exit_code"       # Process exited
    TIMEOUT = "timeout"           # Max time exceeded
    USER_CANCEL = "user_cancel"   # User cancelled
    ERROR = "error"               # Error occurred


class JobSource(str, Enum):
    """Source type for the job"""
    COMMAND = "command"         # Just a command to run
    HUGGINGFACE = "huggingface" # Clone HF repo and run
    GIT = "git"                 # Clone git repo and run
    SCRIPT = "script"           # Upload script to run


@dataclass
class JobConfig:
    """Job configuration"""
    name: str

    # Source - what to run
    source: JobSource = JobSource.COMMAND
    command: str = ""           # Command to execute (or entry point for repos)

    # Hugging Face specific
    hf_repo: Optional[str] = None      # e.g., "unsloth/llama-3-8b-Instruct-bnb-4bit"
    hf_revision: Optional[str] = None  # Branch/tag/commit
    hf_token: Optional[str] = None     # For private repos

    # Git specific
    git_url: Optional[str] = None      # Git clone URL
    git_branch: Optional[str] = None

    # Setup
    setup_script: Optional[str] = None  # Script to run before main command
    requirements_file: Optional[str] = None  # pip install -r <file>
    pip_packages: List[str] = field(default_factory=list)  # Extra pip packages

    # GPU requirements
    gpu_type: str = "RTX 4090"
    num_gpus: int = 1
    region: Optional[str] = None
    use_spot: bool = True  # False = on-demand (more stable, more expensive)

    # Storage
    disk_size: float = 50.0
    image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"

    # Execution
    timeout_minutes: int = 480  # 8 hours max
    working_dir: str = "/workspace"
    env_vars: Dict[str, str] = field(default_factory=dict)

    # Output handling
    output_paths: List[str] = field(default_factory=lambda: ["/workspace/output"])
    save_logs: bool = True
    upload_outputs_to_r2: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'source': self.source.value,
            'command': self.command,
            'hf_repo': self.hf_repo,
            'hf_revision': self.hf_revision,
            'hf_token': self.hf_token,
            'git_url': self.git_url,
            'git_branch': self.git_branch,
            'setup_script': self.setup_script,
            'requirements_file': self.requirements_file,
            'pip_packages': self.pip_packages,
            'gpu_type': self.gpu_type,
            'num_gpus': self.num_gpus,
            'region': self.region,
            'use_spot': self.use_spot,
            'disk_size': self.disk_size,
            'image': self.image,
            'timeout_minutes': self.timeout_minutes,
            'working_dir': self.working_dir,
            'env_vars': self.env_vars,
            'output_paths': self.output_paths,
            'save_logs': self.save_logs,
            'upload_outputs_to_r2': self.upload_outputs_to_r2,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobConfig":
        """Create from dictionary"""
        return cls(
            name=data['name'],
            source=JobSource(data.get('source', 'command')),
            command=data.get('command', ''),
            hf_repo=data.get('hf_repo'),
            hf_revision=data.get('hf_revision'),
            hf_token=data.get('hf_token'),
            git_url=data.get('git_url'),
            git_branch=data.get('git_branch'),
            setup_script=data.get('setup_script'),
            requirements_file=data.get('requirements_file'),
            pip_packages=data.get('pip_packages', []),
            gpu_type=data.get('gpu_type', 'RTX 4090'),
            num_gpus=data.get('num_gpus', 1),
            region=data.get('region'),
            use_spot=data.get('use_spot', True),
            disk_size=data.get('disk_size', 50.0),
            image=data.get('image', 'pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime'),
            timeout_minutes=data.get('timeout_minutes', 480),
            working_dir=data.get('working_dir', '/workspace'),
            env_vars=data.get('env_vars', {}),
            output_paths=data.get('output_paths', ['/workspace/output']),
            save_logs=data.get('save_logs', True),
            upload_outputs_to_r2=data.get('upload_outputs_to_r2', True),
        )


@dataclass
class Job:
    """
    Represents a GPU Job (Execute and Destroy)

    Different from Serverless mode:
    - Serverless: hibernate -> wake -> run -> hibernate
    - Job: create -> run -> DESTROY (one-time execution)
    """
    id: str
    user_id: str
    config: JobConfig
    status: JobStatus = JobStatus.PENDING

    # Instance info
    instance_id: Optional[int] = None
    provider: str = "vast"
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None

    # Execution info
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    completion_reason: Optional[JobCompletionReason] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Cost tracking
    total_cost: float = 0.0
    cost_per_hour: float = 0.0
    gpu_hours: float = 0.0

    # Logs and outputs
    logs: str = ""
    output_urls: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence/API"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'config': self.config.to_dict(),
            'status': self.status.value,
            'instance_id': self.instance_id,
            'provider': self.provider,
            'ssh_host': self.ssh_host,
            'ssh_port': self.ssh_port,
            'pid': self.pid,
            'exit_code': self.exit_code,
            'completion_reason': self.completion_reason.value if self.completion_reason else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_cost': self.total_cost,
            'cost_per_hour': self.cost_per_hour,
            'gpu_hours': self.gpu_hours,
            'logs': self.logs,
            'output_urls': self.output_urls,
            'error_message': self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create from dictionary"""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            config=JobConfig.from_dict(data['config']),
            status=JobStatus(data['status']),
            instance_id=data.get('instance_id'),
            provider=data.get('provider', 'vast'),
            ssh_host=data.get('ssh_host'),
            ssh_port=data.get('ssh_port'),
            pid=data.get('pid'),
            exit_code=data.get('exit_code'),
            completion_reason=JobCompletionReason(data['completion_reason']) if data.get('completion_reason') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            total_cost=data.get('total_cost', 0.0),
            cost_per_hour=data.get('cost_per_hour', 0.0),
            gpu_hours=data.get('gpu_hours', 0.0),
            logs=data.get('logs', ''),
            output_urls=data.get('output_urls', []),
            error_message=data.get('error_message'),
        )

    @property
    def is_running(self) -> bool:
        """Check if job is actively running"""
        return self.status in (JobStatus.PROVISIONING, JobStatus.STARTING, JobStatus.RUNNING)

    @property
    def is_completed(self) -> bool:
        """Check if job completed successfully"""
        return self.status == JobStatus.COMPLETED

    @property
    def is_finished(self) -> bool:
        """Check if job finished (success or failure)"""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMEOUT)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    @property
    def duration_formatted(self) -> str:
        """Get job duration as formatted string"""
        seconds = self.duration_seconds
        if seconds is None:
            return "N/A"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def update_cost(self):
        """Update cost based on duration and hourly rate"""
        if self.started_at and self.cost_per_hour > 0:
            hours = (self.duration_seconds or 0) / 3600
            self.gpu_hours = round(hours, 4)
            self.total_cost = round(hours * self.cost_per_hour, 4)
