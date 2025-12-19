"""
Helper functions for GPUSnapshotService with different storage providers
"""
from .gpu_snapshot_service import GPUSnapshotService


def create_snapshot_service_b2(
    key_id: str,
    application_key: str,
    bucket: str,
    region: str = "us-west-004"
) -> GPUSnapshotService:
    """
    Create GPUSnapshotService configured for Backblaze B2
    
    Args:
        key_id: Backblaze B2 keyID (S3-compatible)
        application_key: Backblaze B2 application key
        bucket: Bucket name
        region: B2 region (default: us-west-004)
    
    Returns:
        Configured GPUSnapshotService instance
    """
    endpoint = f"https://s3.{region}.backblazeb2.com"
    service = GPUSnapshotService(endpoint, bucket)
    
    # Override credentials in generated scripts
    service._b2_key_id = key_id
    service._b2_app_key = application_key
    
    return service


def create_snapshot_service_r2(
    account_id: str,
    access_key: str,
    secret_key: str,
    bucket: str
) -> GPUSnapshotService:
    """
    Create GPUSnapshotService configured for Cloudflare R2
    
    Args:
        account_id: Cloudflare account ID
        access_key: R2 access key
        secret_key: R2 secret key
        bucket: Bucket name
    
    Returns:
        Configured GPUSnapshotService instance
    """
    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    service = GPUSnapshotService(endpoint, bucket)
    
    # Override credentials
    service._r2_access_key = access_key
    service._r2_secret_key = secret_key
    
    return service


# Default recommended configuration
def create_snapshot_service_default() -> GPUSnapshotService:
    """
    Create GPUSnapshotService with default recommended provider (Backblaze B2)
    Reads configuration from environment variables
    """
    import os
    
    key_id = os.getenv("B2_KEY_ID", "003a1ef6268a3f30000000002")
    app_key = os.getenv("B2_APPLICATION_KEY", "K003vYodS+gmuU83zDEDNy2EIv5ddnQ")
    bucket = os.getenv("B2_BUCKET", "dumoncloud-snapshot")
    region = os.getenv("B2_REGION", "us-west-004")
    
    return create_snapshot_service_b2(key_id, app_key, bucket, region)
