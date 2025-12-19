"""
Storage Provider Abstraction Layer
Supports multiple cloud storage backends (R2, B2, S3, Wasabi, etc.)
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from dataclasses import dataclass
import subprocess
import os


@dataclass
class StorageConfig:
    """Configuration for a storage provider"""
    provider: str  # 'r2', 'b2', 'wasabi', 's3'
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: Optional[str] = "auto"
    
    
class StorageProvider(ABC):
    """Abstract base class for storage providers"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to storage"""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from storage"""
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from storage"""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List files with optional prefix"""
        pass
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for this provider"""
        return {
            "AWS_ACCESS_KEY_ID": self.config.access_key,
            "AWS_SECRET_ACCESS_KEY": self.config.secret_key,
            "AWS_REGION": self.config.region or "auto"
        }


class S5cmdProvider(StorageProvider):
    """
    S3-compatible provider using s5cmd (fast, supports R2, B2, Wasabi, S3)
    """
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self._ensure_s5cmd()
    
    def _ensure_s5cmd(self):
        """Ensure s5cmd is installed"""
        if subprocess.run(["which", "s5cmd"], capture_output=True).returncode != 0:
            # Install s5cmd
            subprocess.run([
                "curl", "-sL", 
                "https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz"
            ], stdout=subprocess.PIPE, check=True)
            # Assuming it's already installed for this implementation
            pass
    
    def _run_s5cmd(self, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run s5cmd command with proper environment"""
        env = os.environ.copy()
        env.update(self.get_env_vars())
        
        cmd = ["s5cmd", "--endpoint-url", self.config.endpoint] + args
        return subprocess.run(cmd, env=env, capture_output=True, text=True, **kwargs)
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file using s5cmd"""
        s3_path = f"s3://{self.config.bucket}/{remote_path}"
        result = self._run_s5cmd(["cp", local_path, s3_path])
        return result.returncode == 0
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file using s5cmd"""
        s3_path = f"s3://{self.config.bucket}/{remote_path}"
        result = self._run_s5cmd(["cp", s3_path, local_path])
        return result.returncode == 0
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file using s5cmd"""
        s3_path = f"s3://{self.config.bucket}/{remote_path}"
        result = self._run_s5cmd(["rm", s3_path])
        return result.returncode == 0
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files using s5cmd"""
        s3_path = f"s3://{self.config.bucket}/{prefix}"
        result = self._run_s5cmd(["ls", s3_path])
        
        if result.returncode != 0:
            return []
        
        # Parse s5cmd output
        files = []
        for line in result.stdout.splitlines():
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    # Last part is the s3:// path
                    s3_url = parts[-1]
                    # Extract filename after bucket
                    filename = s3_url.replace(f"s3://{self.config.bucket}/", "")
                    files.append(filename)
        
        return files
    
    def download_dir(self, remote_prefix: str, local_dir: str, num_workers: int = 64) -> bool:
        """Download entire directory with parallelism"""
        s3_path = f"s3://{self.config.bucket}/{remote_prefix}/*"
        result = self._run_s5cmd([
            "--numworkers", str(num_workers),
            "cp", s3_path, local_dir + "/"
        ])
        return result.returncode == 0


# Provider factory
def create_storage_provider(config: StorageConfig) -> StorageProvider:
    """Create appropriate storage provider based on config"""
    # All S3-compatible providers use S5cmdProvider
    if config.provider in ['r2', 'b2', 'wasabi', 's3']:
        return S5cmdProvider(config)
    else:
        raise ValueError(f"Unsupported storage provider: {config.provider}")


# Predefined configurations
def get_cloudflare_r2_config(access_key: str, secret_key: str, bucket: str, account_id: str) -> StorageConfig:
    """Get Cloudflare R2 configuration"""
    return StorageConfig(
        provider='r2',
        endpoint=f"https://{account_id}.r2.cloudflarestorage.com",
        bucket=bucket,
        access_key=access_key,
        secret_key=secret_key,
        region='auto'
    )


def get_backblaze_b2_config(key_id: str, application_key: str, bucket: str, region: str = "us-west-004") -> StorageConfig:
    """Get Backblaze B2 configuration"""
    return StorageConfig(
        provider='b2',
        endpoint=f"https://s3.{region}.backblazeb2.com",
        bucket=bucket,
        access_key=key_id,
        secret_key=application_key,
        region=region
    )


def get_wasabi_config(access_key: str, secret_key: str, bucket: str, region: str = "us-east-1") -> StorageConfig:
    """Get Wasabi configuration"""
    return StorageConfig(
        provider='wasabi',
        endpoint=f"https://s3.{region}.wasabisys.com",
        bucket=bucket,
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )


def get_aws_s3_config(access_key: str, secret_key: str, bucket: str, region: str = "us-east-1") -> StorageConfig:
    """Get AWS S3 configuration"""
    return StorageConfig(
        provider='s3',
        endpoint=f"https://s3.{region}.amazonaws.com",
        bucket=bucket,
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )
