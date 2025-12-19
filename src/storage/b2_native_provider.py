"""
Backblaze B2 Native Provider
Uses B2 Native SDK instead of S3-compatible API (more reliable)
"""
from .storage_provider import StorageProvider, StorageConfig
from typing import List
import os


class B2NativeProvider(StorageProvider):
    """
    Backblaze B2 provider using native SDK (not S3-compatible)
    This is more reliable than S3 API and works with Master Application Keys
    """
    
    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self._ensure_b2sdk()
        self._bucket = None
    
    def _ensure_b2sdk(self):
        """Ensure b2sdk is installed"""
        try:
            import b2sdk
        except ImportError:
            import subprocess
            import sys
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "b2sdk"], check=True)
    
    def _get_bucket(self):
        """Get or create bucket connection"""
        if self._bucket is None:
            from b2sdk.v2 import InMemoryAccountInfo, B2Api
            
            info = InMemoryAccountInfo()
            b2_api = B2Api(info)
            b2_api.authorize_account(
                "production",
                self.config.access_key,
                self.config.secret_key
            )
            self._bucket = b2_api.get_bucket_by_name(self.config.bucket)
        
        return self._bucket
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file using B2 native SDK"""
        try:
            bucket = self._get_bucket()
            bucket.upload_local_file(
                local_file=local_path,
                file_name=remote_path
            )
            return True
        except Exception as e:
            print(f"B2 upload error: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file using B2 native SDK"""
        try:
            bucket = self._get_bucket()
            downloaded = bucket.download_file_by_name(remote_path)
            downloaded.save_to(local_path)
            return True
        except Exception as e:
            print(f"B2 download error: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file using B2 native SDK"""
        try:
            bucket = self._get_bucket()
            file_info = bucket.get_file_info_by_name(remote_path)
            bucket.api.delete_file_version(file_info.id_, remote_path)
            return True
        except Exception as e:
            print(f"B2 delete error: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files using B2 native SDK"""
        try:
            bucket = self._get_bucket()
            files = []
            for file_version, _ in bucket.ls(prefix):
                files.append(file_version.file_name)
            return files
        except Exception as e:
            print(f"B2 list error: {e}")
            return []
    
    def upload_bytes(self, data: bytes, remote_path: str) -> bool:
        """Upload bytes directly (useful for small files)"""
        try:
            bucket = self._get_bucket()
            bucket.upload_bytes(data, remote_path)
            return True
        except Exception as e:
            print(f"B2 upload_bytes error: {e}")
            return False


# Update storage_provider.py to use B2NativeProvider
def create_b2_provider(config: StorageConfig) -> StorageProvider:
    """
    Create B2 provider using native SDK
    This is more reliable than S3-compatible API
    """
    return B2NativeProvider(config)
