"""
Model Deploy Service
Handles deploying and managing ML models on GPU instances

Uses DeployWizardService for GPU provisioning (race strategy with batches).
"""
import logging
import asyncio
import json
import os
import subprocess
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from ..models.model_deploy import ModelDeployment, ModelType, ModelStatus, AccessType
from ...services.runtime_templates import get_template, get_all_templates, get_install_script, get_start_script, get_health_check_script
from ...services.gpu.vast import VastService
from ...services.gpu.strategies import MachineProvisionerService, ProvisionConfig, ProvisionResult

logger = logging.getLogger(__name__)

# In-memory storage for deployments (could be Redis/DB in production)
_deployments: Dict[str, ModelDeployment] = {}
_user_deployments: Dict[str, List[str]] = {}  # user_id -> [deployment_ids]


class ModelDeployService:
    """Service for managing model deployments using MachineProvisionerService for GPU provisioning.

    Uses the Strategy Pattern for machine provisioning:
    - RaceStrategy: Create multiple machines in parallel, first ready wins (fastest)
    - SingleStrategy: Create single machine and wait (cheapest)
    """

    def __init__(self, vast_client: Optional[VastService] = None, ssh_client=None):
        # Use provided client or create from environment
        api_key = os.environ.get("VAST_API_KEY")
        self.api_key = api_key

        if vast_client:
            self.vast_client = vast_client
        elif api_key:
            self.vast_client = VastService(api_key)
        else:
            self.vast_client = None
            logger.warning("VAST_API_KEY not set - GPU provisioning will fail")

        # Initialize MachineProvisionerService for GPU provisioning (uses Strategy Pattern)
        if api_key:
            self.provisioner = MachineProvisionerService(api_key)
        else:
            self.provisioner = None

        self.ssh_client = ssh_client

    async def create_deployment(
        self,
        user_id: str,
        model_type: str,
        model_id: str,
        instance_id: Optional[int] = None,
        gpu_type: Optional[str] = None,
        num_gpus: int = 1,
        max_price: float = 2.0,
        access_type: str = "private",
        port: int = 8000,
        name: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        label: Optional[str] = None,  # Custom label (for testing use dumont:test:*)
    ) -> ModelDeployment:
        """Create a new model deployment"""
        template = get_template(model_type)

        deployment = ModelDeployment(
            user_id=user_id,
            name=name or f"{template.name} - {model_id.split('/')[-1]}",
            model_type=ModelType(model_type),
            model_id=model_id,
            runtime=template.runtime,
            instance_id=instance_id or 0,
            num_gpus=num_gpus,
            access_type=AccessType(access_type),
            port=port,
            env_vars=env_vars or {},
        )

        # Store deployment
        _deployments[deployment.id] = deployment
        if user_id not in _user_deployments:
            _user_deployments[user_id] = []
        _user_deployments[user_id].append(deployment.id)

        # Start deployment in background
        asyncio.create_task(self._deploy_model(deployment, gpu_type, max_price, label))

        return deployment

    async def _deploy_model(
        self, deployment: ModelDeployment, gpu_type: Optional[str], max_price: float, label: Optional[str] = None
    ):
        """
        Background task to deploy the model using MachineProvisionerService.

        Uses the Strategy Pattern for GPU provisioning:
        1. RaceStrategy: Creates batch of 5 machines in parallel
        2. Waits for first to become ready (SSH accessible)
        3. Destroys the losers
        4. Returns the winner
        """
        try:
            deployment.update_status(ModelStatus.DEPLOYING, "Starting deployment...", 10)

            # Step 1: Get or create GPU instance using MachineProvisionerService
            if deployment.instance_id == 0:
                if not self.provisioner:
                    raise RuntimeError("VAST_API_KEY not configured - cannot provision GPU")

                deployment.update_status(ModelStatus.DEPLOYING, f"Searching for {gpu_type or 'any'} GPU...", 15)

                # Configure provisioning with ports for model serving
                # Use custom label if provided (for testing use dumont:test:*)
                # Default to dumont:model-deploy for production
                instance_label = label or "dumont:model-deploy"
                config = ProvisionConfig(
                    gpu_name=gpu_type,
                    max_price=max_price,
                    disk_space=100,
                    min_inet_down=100,
                    region="global",
                    image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
                    ports=[22, deployment.port],  # SSH + model port
                    label=instance_label,
                )

                # Progress callback to update deployment status
                def progress_callback(status: str, message: str, progress: int):
                    deployment.update_status(
                        ModelStatus.DEPLOYING,
                        f"Provisioning: {message}",
                        15 + int(progress * 0.35),  # Map 0-100 to 15-50
                    )

                # Run provisioner synchronously in executor (provisioner is sync)
                deployment.update_status(ModelStatus.DEPLOYING, "Racing machines for fastest startup...", 20)

                loop = asyncio.get_event_loop()
                result: ProvisionResult = await loop.run_in_executor(
                    None,
                    lambda: self.provisioner.provision(config, strategy="race", progress_callback=progress_callback)
                )

                if not result.success:
                    raise RuntimeError(f"GPU provisioning failed: {result.error}")

                # Extract instance info from provisioner result
                deployment.instance_id = result.instance_id
                deployment.gpu_name = result.gpu_name or gpu_type
                deployment.dph_total = result.dph_total

                public_ip = result.public_ip or result.ssh_host
                ssh_port = result.ssh_port

                logger.info(f"Provisioner completed! Instance {deployment.instance_id} at {public_ip}:{ssh_port}")

            # Step 2: Install and start the model server via SSH
            deployment.update_status(ModelStatus.DOWNLOADING, "Installing model runtime...", 50)

            # Run the deployment script via SSH
            await self._run_model_deploy_script(
                deployment, public_ip, ssh_port
            )

            # Step 3: Wait for port to be exposed and health check
            deployment.update_status(ModelStatus.STARTING, "Waiting for model server...", 75)

            # Get port mapping from Vast.ai
            status = self.vast_client.get_instance_status(deployment.instance_id)
            ports = status.get("ports", {})

            # Find mapped port
            mapped_port = deployment.port
            port_key = f"{deployment.port}/tcp"
            if port_key in ports:
                mapped_info = ports[port_key]
                if isinstance(mapped_info, list) and mapped_info:
                    mapped_port = mapped_info[0].get("HostPort", deployment.port)

            endpoint_url = f"http://{public_ip}:{mapped_port}"
            deployment.endpoint_url = endpoint_url

            # Wait for health check
            import aiohttp
            health_ok = False
            health_start = asyncio.get_event_loop().time()
            health_timeout = 300  # 5 minutes for model to load

            async with aiohttp.ClientSession() as session:
                while asyncio.get_event_loop().time() - health_start < health_timeout:
                    try:
                        async with session.get(f"{endpoint_url}/health", timeout=5) as resp:
                            if resp.status == 200:
                                health_ok = True
                                break
                    except Exception:
                        pass

                    progress = min(75 + int((asyncio.get_event_loop().time() - health_start) / health_timeout * 20), 95)
                    deployment.update_status(ModelStatus.STARTING, "Model loading...", progress)
                    await asyncio.sleep(10)

            if not health_ok:
                logger.warning(f"Health check not responding for {deployment.id}, but instance is running")

            # Success!
            deployment.update_status(ModelStatus.RUNNING, "Model is running", 100)
            deployment.started_at = datetime.utcnow()

            logger.info(f"Deployment {deployment.id} completed: {endpoint_url}")

        except Exception as e:
            logger.error(f"Deployment {deployment.id} failed: {e}")
            deployment.update_status(ModelStatus.ERROR, str(e))

            # Cleanup instance on failure
            if self.vast_client and deployment.instance_id and deployment.instance_id != 0:
                try:
                    self.vast_client.destroy_instance(deployment.instance_id)
                    logger.info(f"Cleaned up failed instance {deployment.instance_id}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup instance: {cleanup_err}")

    async def _run_model_deploy_script(self, deployment: ModelDeployment, public_ip: str, ssh_port: int):
        """
        Run the model deployment script on the remote instance via SSH.

        Uses scripts from runtime_templates module (DRY).
        """
        # Get scripts from centralized runtime_templates
        install_script = get_install_script(deployment.model_type.value)
        start_script = get_start_script(deployment.model_type.value, deployment.model_id, deployment.port)

        deploy_cmd = f"""#!/bin/bash
set -e
export MODEL_ID="{deployment.model_id}"
export PORT={deployment.port}

echo "[$(date)] Starting deployment for {deployment.model_id}" >> /var/log/dumont-deploy.log

# Install runtime
{install_script}

# Start model server
{start_script}
"""
        # Execute via SSH
        ssh_cmd = [
            "ssh", "-i", "/home/marcos/.ssh/id_rsa",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-p", str(ssh_port),
            f"root@{public_ip}",
            deploy_cmd
        ]

        deployment.update_status(ModelStatus.DOWNLOADING, "Deploying model to instance...", 60)

        # Run SSH command in executor (non-blocking)
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(ssh_cmd, timeout=600, capture_output=True, text=True)
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"SSH deploy command timed out for {deployment.id}")

    async def get_deployment(self, deployment_id: str) -> Optional[ModelDeployment]:
        """Get deployment by ID"""
        return _deployments.get(deployment_id)

    async def get_user_deployments(self, user_id: str) -> List[ModelDeployment]:
        """Get all deployments for a user"""
        deployment_ids = _user_deployments.get(user_id, [])
        return [_deployments[d] for d in deployment_ids if d in _deployments]

    async def stop_deployment(self, deployment_id: str, force: bool = False) -> bool:
        """Stop a running deployment"""
        deployment = _deployments.get(deployment_id)
        if not deployment:
            return False

        try:
            if deployment.status in [ModelStatus.RUNNING, ModelStatus.DEPLOYING, ModelStatus.STARTING]:
                # Destroy the GPU instance
                if deployment.instance_id and deployment.instance_id != 0 and self.vast_client:
                    logger.info(f"Destroying instance {deployment.instance_id} for deployment {deployment_id}")
                    self.vast_client.destroy_instance(deployment.instance_id)

                deployment.update_status(ModelStatus.STOPPED, "Model stopped")
                logger.info(f"Deployment {deployment_id} stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop deployment {deployment_id}: {e}")
            if force:
                deployment.update_status(ModelStatus.STOPPED, f"Force stopped (error: {e})")
                return True
            return False

    async def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a deployment"""
        deployment = _deployments.get(deployment_id)
        if not deployment:
            return False

        # Stop first if running (this will also destroy the instance)
        if deployment.status in [ModelStatus.RUNNING, ModelStatus.DEPLOYING, ModelStatus.STARTING]:
            await self.stop_deployment(deployment_id, force=True)

        # Remove from storage
        del _deployments[deployment_id]
        if deployment.user_id in _user_deployments:
            _user_deployments[deployment.user_id] = [
                d for d in _user_deployments[deployment.user_id] if d != deployment_id
            ]

        logger.info(f"Deployment {deployment_id} deleted")
        return True

    async def get_logs(self, deployment_id: str) -> str:
        """Get logs for a deployment"""
        deployment = _deployments.get(deployment_id)
        if not deployment:
            return "Deployment not found"

        # Try to get logs from vast.ai
        if self.vast_client and deployment.instance_id and deployment.instance_id != 0:
            try:
                logs = self.vast_client.get_instance_logs(deployment.instance_id)
                return f"=== Instance {deployment.instance_id} Logs ===\n{logs}"
            except Exception as e:
                logger.warning(f"Failed to get instance logs: {e}")

        return f"[{datetime.utcnow().isoformat()}] Deployment {deployment.id}\nModel: {deployment.model_id}\nStatus: {deployment.status.value}\nEndpoint: {deployment.endpoint_url or 'Not available'}"

    async def health_check(self, deployment_id: str) -> Dict[str, Any]:
        """Check health of a deployment"""
        deployment = _deployments.get(deployment_id)
        if not deployment:
            return {"healthy": False, "error": "Deployment not found"}

        if deployment.status != ModelStatus.RUNNING:
            return {
                "healthy": False,
                "status": deployment.status.value,
                "error": "Model is not running"
            }

        # Check if endpoint is responding
        if deployment.endpoint_url:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{deployment.endpoint_url}/health", timeout=10) as resp:
                        if resp.status == 200:
                            return {
                                "healthy": True,
                                "status": "running",
                                "endpoint": deployment.endpoint_url,
                                "uptime_seconds": int((datetime.utcnow() - (deployment.started_at or datetime.utcnow())).total_seconds()),
                            }
            except Exception as e:
                return {
                    "healthy": False,
                    "status": "unhealthy",
                    "error": f"Health check failed: {e}",
                    "endpoint": deployment.endpoint_url,
                }

        return {
            "healthy": True,
            "status": "running",
            "uptime_seconds": int((datetime.utcnow() - (deployment.started_at or datetime.utcnow())).total_seconds()),
        }

    def get_templates(self) -> List[Dict[str, Any]]:
        """Get available templates"""
        return get_all_templates()


# Singleton instance
_service: Optional[ModelDeployService] = None


def get_model_deploy_service() -> ModelDeployService:
    """Get or create service instance"""
    global _service
    if _service is None:
        _service = ModelDeployService()
    return _service
