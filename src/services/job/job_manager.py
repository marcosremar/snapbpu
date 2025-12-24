"""
JobManager Service - Execute and Destroy GPU Jobs

This service manages GPU jobs that:
1. Provision a GPU instance
2. Download/setup from Hugging Face (or git/command)
3. Execute the job
4. Save outputs to cloud
5. DESTROY the GPU instance (no hibernation)

Different from Serverless which hibernates for future use.
"""
import asyncio
import json
import logging
import time
import subprocess
import threading
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.models.job import (
    Job, JobConfig, JobStatus, JobSource, JobCompletionReason
)
from src.services.gpu.vast import VastService
from src.services.deploy_wizard import (
    DeployWizardService, DeployConfig, SSH_INSTALL_SCRIPT, DOCKER_IMAGES
)

logger = logging.getLogger(__name__)

# Job completion marker file
JOB_COMPLETE_MARKER = "/workspace/.job_complete"
JOB_FAILED_MARKER = "/workspace/.job_failed"

# Monitoring intervals
MONITOR_INTERVAL_SECONDS = 10
GPU_IDLE_THRESHOLD = 5  # GPU < 5% for completion detection
GPU_IDLE_MINUTES = 5    # 5 minutes of idle = job complete

# Global job storage (shared across JobManager instances)
_global_jobs: Dict[str, "Job"] = {}
_global_monitor_threads: Dict[str, threading.Thread] = {}


class JobManager:
    """
    Manages GPU Jobs (Execute and Destroy)

    Key features:
    - Hugging Face repo integration (clone, install, run)
    - Git repo support
    - Command execution
    - Auto-destroy on completion
    - Logs and output collection
    """

    def __init__(self, vast_api_key: str, demo_mode: bool = False):
        self.api_key = vast_api_key
        self.demo_mode = demo_mode
        self.vast = VastService(vast_api_key) if not demo_mode else None
        self.deploy_wizard = DeployWizardService(vast_api_key) if not demo_mode else None
        # Use global storage to persist jobs across requests
        self.jobs = _global_jobs
        self._monitor_threads = _global_monitor_threads

    def create_job(self, config: JobConfig, user_id: str) -> Job:
        """
        Create and start a new GPU job.

        Args:
            config: Job configuration
            user_id: User ID

        Returns:
            Job object with ID and initial status
        """
        job_id = f"job_{uuid4().hex[:8]}"

        job = Job(
            id=job_id,
            user_id=user_id,
            config=config,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        self.jobs[job_id] = job

        # Start job execution in background
        thread = threading.Thread(
            target=self._run_job_sync,
            args=(job,),
            daemon=True,
            name=f"job-{job_id}"
        )
        self._monitor_threads[job_id] = thread
        thread.start()

        logger.info(f"Created job {job_id}: {config.name}")
        return job

    def _run_job_sync(self, job: Job):
        """Synchronous wrapper for async job execution"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run_job(job))
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
        finally:
            loop.close()

    async def _run_job(self, job: Job):
        """
        Main job execution flow:
        1. Provision GPU
        2. Setup (HF repo, git, etc)
        3. Execute command
        4. Monitor completion
        5. Collect outputs
        6. DESTROY GPU
        """
        try:
            # 1. Provision GPU
            job.status = JobStatus.PROVISIONING
            logger.info(f"[{job.id}] Provisioning GPU: {job.config.gpu_type}")

            instance_info = await self._provision_gpu(job)
            if not instance_info:
                job.status = JobStatus.FAILED
                job.error_message = "Failed to provision GPU"
                return

            job.instance_id = instance_info["instance_id"]
            job.ssh_host = instance_info["ssh_host"]
            job.ssh_port = instance_info["ssh_port"]
            job.cost_per_hour = instance_info.get("cost_per_hour", 0)
            job.started_at = datetime.utcnow()

            logger.info(f"[{job.id}] GPU ready: {job.ssh_host}:{job.ssh_port}")

            # 2. Setup environment
            job.status = JobStatus.STARTING
            logger.info(f"[{job.id}] Setting up environment...")

            setup_success = await self._setup_environment(job)
            if not setup_success:
                job.status = JobStatus.FAILED
                await self._destroy_instance(job, "setup_failed")
                return

            # 3. Execute command
            job.status = JobStatus.RUNNING
            logger.info(f"[{job.id}] Executing command...")

            exec_success = await self._execute_command(job)
            if not exec_success:
                job.status = JobStatus.FAILED
                await self._collect_outputs(job)
                await self._destroy_instance(job, "execution_failed")
                return

            # 4. Monitor completion
            logger.info(f"[{job.id}] Monitoring completion...")

            completion_reason = await self._monitor_completion(job)
            job.completion_reason = completion_reason

            # 5. Collect outputs
            job.status = JobStatus.COMPLETING
            logger.info(f"[{job.id}] Collecting outputs...")

            await self._collect_outputs(job)

            # 6. DESTROY GPU (always!)
            job.status = JobStatus.COMPLETED if completion_reason != JobCompletionReason.ERROR else JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.update_cost()

            logger.info(f"[{job.id}] Job completed: {completion_reason.value}")

        except Exception as e:
            logger.error(f"[{job.id}] Job error: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)

        finally:
            # ALWAYS destroy the GPU
            await self._destroy_instance(job, "completed")

    async def _provision_gpu(self, job: Job) -> Optional[Dict[str, Any]]:
        """Provision GPU instance using DeployWizard pattern"""
        try:
            # Determine machine type based on use_spot setting
            # use_spot=True (default) -> spot/interruptible (cheaper but can be preempted)
            # use_spot=False -> on-demand (stable, more expensive)
            machine_type = "interruptible" if job.config.use_spot else "on-demand"
            logger.info(f"[{job.id}] Using machine_type={machine_type} (use_spot={job.config.use_spot})")

            # Build deploy config
            deploy_config = DeployConfig(
                speed_tier="fast",
                gpu_name=job.config.gpu_type,
                disk_space=int(job.config.disk_size),
                max_price=2.0,  # Max $2/hr
                use_ollama_image=False,  # Use PyTorch image for jobs
                image=job.config.image,
                machine_type=machine_type,  # on-demand or interruptible (spot)
            )

            # Search for offers
            offers, _ = self.deploy_wizard.get_offers(deploy_config, filter_blacklist=True)

            if not offers:
                logger.error(f"[{job.id}] No offers available for {job.config.gpu_type}")
                return None

            # Try first offer
            offer = offers[0]
            logger.info(f"[{job.id}] Creating instance from offer {offer['id']}")

            # Create instance
            instance_id = self.vast.create_instance(
                offer_id=offer["id"],
                image=job.config.image,
                disk=int(job.config.disk_size),
                onstart_cmd=SSH_INSTALL_SCRIPT,
                use_template=False,
            )

            if not instance_id:
                return None

            # Store instance_id immediately so cancel can destroy it
            job.instance_id = instance_id

            # Wait for instance to be ready
            logger.info(f"[{job.id}] Waiting for instance {instance_id} to be ready...")

            ready_info = await self._wait_for_instance(instance_id, timeout=600)  # 10 min for GPU boot
            if not ready_info:
                # Destroy failed instance
                try:
                    self.vast.destroy_instance(instance_id)
                except:
                    pass
                return None

            return {
                "instance_id": instance_id,
                "ssh_host": ready_info["ssh_host"],
                "ssh_port": ready_info["ssh_port"],
                "cost_per_hour": offer.get("dph_total", 0),
            }

        except Exception as e:
            logger.error(f"[{job.id}] Provisioning failed: {e}")
            return None

    async def _wait_for_instance(self, instance_id: int, timeout: int = 120) -> Optional[Dict[str, Any]]:
        """Wait for instance to be ready with SSH"""
        start = time.time()
        check_count = 0

        while time.time() - start < timeout:
            check_count += 1
            elapsed = int(time.time() - start)
            try:
                status = self.vast.get_instance_status(instance_id)
                actual_status = status.get("actual_status") or status.get("status", "unknown")
                logger.info(f"[wait] Check {check_count}: instance {instance_id} status={actual_status} ({elapsed}s/{timeout}s)")

                if actual_status == "running":
                    ssh_host = status.get("ssh_host")
                    ssh_port = status.get("ssh_port")

                    if ssh_host and ssh_port:
                        logger.info(f"[wait] Instance running, testing SSH: {ssh_host}:{ssh_port}")
                        # Test SSH connection
                        if self._test_ssh(ssh_host, int(ssh_port)):
                            logger.info(f"[wait] SSH OK!")
                            return {
                                "ssh_host": ssh_host,
                                "ssh_port": int(ssh_port),
                            }
                        else:
                            logger.info(f"[wait] SSH not ready yet")

            except Exception as e:
                logger.warning(f"[wait] Status check failed: {e}")

            await asyncio.sleep(5)

        logger.warning(f"[wait] Timeout after {timeout}s for instance {instance_id}")
        return None

    def _test_ssh(self, host: str, port: int, timeout: int = 5) -> bool:
        """Test SSH connection"""
        try:
            result = subprocess.run(
                ["ssh", "-i", "/home/marcos/.ssh/id_rsa",
                 "-o", "StrictHostKeyChecking=no",
                 "-o", f"ConnectTimeout={timeout}",
                 "-o", "BatchMode=yes",
                 "-p", str(port),
                 f"root@{host}",
                 "echo ok"],
                capture_output=True, timeout=timeout + 2, text=True
            )
            return result.returncode == 0 and "ok" in result.stdout
        except:
            return False

    def _ssh_exec(self, job: Job, command: str, timeout: int = 300, retries: int = 3) -> tuple[bool, str]:
        """Execute command via SSH with retry logic"""
        last_error = ""
        for attempt in range(retries):
            try:
                result = subprocess.run(
                    ["ssh", "-i", "/home/marcos/.ssh/id_rsa",
                     "-o", "StrictHostKeyChecking=no",
                     "-o", "ConnectTimeout=10",
                     "-o", "ServerAliveInterval=5",
                     "-o", "ServerAliveCountMax=3",
                     "-p", str(job.ssh_port),
                     f"root@{job.ssh_host}",
                     command],
                    capture_output=True, timeout=timeout, text=True
                )
                output = result.stdout + result.stderr
                if result.returncode == 0:
                    return True, output
                # Check if it's a connection error (retry) vs command error (don't retry)
                if "Connection refused" in output or "Connection reset" in output:
                    last_error = output
                    if attempt < retries - 1:
                        logger.info(f"[{job.id}] SSH retry {attempt + 1}/{retries} - connection issue")
                        time.sleep(5)
                        continue
                return result.returncode == 0, output
            except subprocess.TimeoutExpired:
                last_error = "Command timed out"
                if attempt < retries - 1:
                    logger.info(f"[{job.id}] SSH retry {attempt + 1}/{retries} - timeout")
                    time.sleep(5)
                    continue
            except Exception as e:
                last_error = str(e)
                if "Connection refused" in str(e) or "Connection reset" in str(e):
                    if attempt < retries - 1:
                        logger.info(f"[{job.id}] SSH retry {attempt + 1}/{retries} - {e}")
                        time.sleep(5)
                        continue
                return False, str(e)
        return False, last_error

    async def _setup_and_execute_single_shot(self, job: Job) -> bool:
        """
        Single-shot approach: Create ONE script that does everything.
        This avoids multiple SSH connections which are unstable on VAST.ai.

        The script:
        1. Installs dependencies (git-lfs)
        2. Clones the repo
        3. Installs requirements
        4. Executes the command
        5. Creates marker file when done
        """
        config = job.config

        logger.info(f"[{job.id}] Using single-shot execution mode")

        # Build the complete job script
        script_parts = []
        script_parts.append("#!/bin/bash")
        script_parts.append("set -e")  # Exit on error
        script_parts.append(f"echo '[JOB] Starting job at $(date)'")
        script_parts.append(f"mkdir -p {config.working_dir}")
        script_parts.append(f"cd {config.working_dir}")

        # Determine working directory for execution
        if config.source == JobSource.HUGGINGFACE and config.hf_repo:
            exec_dir = f"{config.working_dir}/model"

            # HuggingFace setup using huggingface_hub Python package
            # This avoids apt-get install which causes SSH instability
            hf_repo = config.hf_repo
            branch = config.hf_revision or "main"

            script_parts.append("echo '[JOB] Installing huggingface_hub...'")
            script_parts.append("pip install -q huggingface_hub")
            script_parts.append("echo '[JOB] Downloading HuggingFace repo...'")

            # Use huggingface_hub to download the repo
            if config.hf_token:
                script_parts.append(f"export HF_TOKEN='{config.hf_token}'")
                script_parts.append(f"python -c \"from huggingface_hub import snapshot_download; snapshot_download('{hf_repo}', local_dir='model', revision='{branch}', token='{config.hf_token}')\"")
            else:
                script_parts.append(f"python -c \"from huggingface_hub import snapshot_download; snapshot_download('{hf_repo}', local_dir='model', revision='{branch}')\"")

            script_parts.append("echo '[JOB] Repo downloaded successfully'")

            # Install requirements if exists
            script_parts.append("cd model && [ -f requirements.txt ] && pip install -q -r requirements.txt || true")

        elif config.source == JobSource.GIT and config.git_url:
            exec_dir = f"{config.working_dir}/repo"

            branch_opt = f"-b {config.git_branch}" if config.git_branch else ""
            script_parts.append("echo '[JOB] Cloning git repo...'")
            script_parts.append(f"git clone {branch_opt} {config.git_url} repo")
            script_parts.append("cd repo")
            script_parts.append("[ -f requirements.txt ] && pip install -q -r requirements.txt || true")

        else:
            exec_dir = config.working_dir

        # Install additional pip packages
        if config.pip_packages:
            packages = " ".join(config.pip_packages)
            script_parts.append(f"echo '[JOB] Installing pip packages...'")
            script_parts.append(f"pip install -q {packages}")

        # Run custom setup script if provided
        if config.setup_script:
            script_parts.append("echo '[JOB] Running setup script...'")
            script_parts.append(config.setup_script)

        # Execute the main command
        if config.command:
            script_parts.append(f"echo '[JOB] Executing command...'")
            script_parts.append(f"cd {exec_dir}")

            # Add environment variables
            for key, value in config.env_vars.items():
                script_parts.append(f"export {key}='{value}'")

            script_parts.append(config.command)

        # Create completion marker
        script_parts.append(f"echo '[JOB] Job completed successfully at $(date)'")
        script_parts.append(f"touch {JOB_COMPLETE_MARKER}")

        # Build the complete script
        job_script = "\n".join(script_parts)

        # Create wrapper that handles errors and runs in background
        wrapper_script = f'''
cat > /workspace/job_runner.sh << 'JOBSCRIPT'
{job_script}
JOBSCRIPT

chmod +x /workspace/job_runner.sh

nohup bash -c '
/workspace/job_runner.sh > /workspace/job.log 2>&1
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "Job failed with exit code $EXIT_CODE" >> /workspace/job.log
    touch {JOB_FAILED_MARKER}
fi
' &

echo $!
'''

        logger.info(f"[{job.id}] Sending single-shot job script...")

        # Execute the wrapper script (this is the ONLY SSH call needed)
        ok, output = self._ssh_exec(job, wrapper_script, timeout=60, retries=5)
        if not ok:
            job.error_message = f"Failed to start job script: {output}"
            return False

        # Get PID
        try:
            job.pid = int(output.strip().split()[-1])
            logger.info(f"[{job.id}] Job script started with PID {job.pid}")
        except:
            logger.warning(f"[{job.id}] Could not parse PID from: {output}")

        return True

    async def _setup_environment(self, job: Job) -> bool:
        """Setup job environment - now uses single-shot mode"""
        # Single-shot mode handles everything
        return True

    async def _execute_command(self, job: Job) -> bool:
        """Execute using single-shot mode"""
        return await self._setup_and_execute_single_shot(job)

    async def _monitor_completion(self, job: Job) -> JobCompletionReason:
        """Monitor job until completion"""
        config = job.config
        start_time = time.time()
        max_duration = config.timeout_minutes * 60
        idle_start = None
        consecutive_ssh_failures = 0
        max_ssh_failures = 10  # After 10 consecutive SSH failures, check instance status

        while True:
            elapsed = time.time() - start_time

            # Check timeout
            if elapsed > max_duration:
                logger.info(f"[{job.id}] Job timed out after {config.timeout_minutes} minutes")
                return JobCompletionReason.TIMEOUT

            # Check marker files
            ok, _ = self._ssh_exec(job, f"test -f {JOB_COMPLETE_MARKER}", timeout=10)
            if ok:
                logger.info(f"[{job.id}] Completion marker found")
                consecutive_ssh_failures = 0
                return JobCompletionReason.MARKER_FILE

            ok, _ = self._ssh_exec(job, f"test -f {JOB_FAILED_MARKER}", timeout=10)
            if ok:
                logger.info(f"[{job.id}] Failed marker found")
                consecutive_ssh_failures = 0
                return JobCompletionReason.ERROR

            # Track SSH failures
            ok_ssh, _ = self._ssh_exec(job, "echo ok", timeout=10)
            if not ok_ssh:
                consecutive_ssh_failures += 1
                logger.warning(f"[{job.id}] SSH failure {consecutive_ssh_failures}/{max_ssh_failures}")

                # After many consecutive failures, check if instance still exists
                if consecutive_ssh_failures >= max_ssh_failures:
                    logger.info(f"[{job.id}] Too many SSH failures, checking instance status...")
                    instance_exists = await self._check_instance_exists(job)
                    if not instance_exists:
                        logger.error(f"[{job.id}] Instance no longer exists! Job failed.")
                        job.error_message = "Instance was destroyed/preempted during execution"
                        return JobCompletionReason.ERROR
                    else:
                        # Instance exists but SSH is failing, reset counter and wait
                        logger.info(f"[{job.id}] Instance still exists, continuing to monitor...")
                        consecutive_ssh_failures = 0
                        await asyncio.sleep(30)  # Wait longer before retrying
                        continue
            else:
                consecutive_ssh_failures = 0

            # Check if process still running
            if job.pid:
                ok, _ = self._ssh_exec(job, f"ps -p {job.pid}", timeout=10)
                if not ok:
                    logger.info(f"[{job.id}] Process {job.pid} exited")

                    # Check exit code
                    ok, _ = self._ssh_exec(job, f"test -f {JOB_COMPLETE_MARKER}", timeout=10)
                    if ok:
                        return JobCompletionReason.EXIT_CODE
                    return JobCompletionReason.ERROR

            # Check GPU idle (optional, for long-running jobs)
            gpu_util = await self._get_gpu_utilization(job)
            if gpu_util is not None and gpu_util < GPU_IDLE_THRESHOLD:
                if idle_start is None:
                    idle_start = time.time()
                elif time.time() - idle_start > GPU_IDLE_MINUTES * 60:
                    logger.info(f"[{job.id}] GPU idle for {GPU_IDLE_MINUTES} minutes")
                    return JobCompletionReason.GPU_IDLE
            else:
                idle_start = None

            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)

    async def _check_instance_exists(self, job: Job) -> bool:
        """Check if the instance still exists on VAST.ai"""
        if not job.instance_id:
            return False

        try:
            status = self.vast.get_instance_status(job.instance_id)
            if not status:
                return False

            actual_status = status.get("actual_status") or status.get("status", "unknown")
            logger.info(f"[{job.id}] Instance {job.instance_id} status: {actual_status}")

            # Instance exists if it's running or loading
            return actual_status in ["running", "loading", "starting", "created"]
        except Exception as e:
            logger.warning(f"[{job.id}] Error checking instance status: {e}")
            # If we can't check, assume it might still exist
            return True

    async def _get_gpu_utilization(self, job: Job) -> Optional[float]:
        """Get current GPU utilization"""
        try:
            ok, output = self._ssh_exec(job,
                "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits",
                timeout=10
            )
            if ok and output.strip():
                return float(output.strip().split()[0])
        except:
            pass
        return None

    async def _collect_outputs(self, job: Job):
        """Collect logs and outputs from job"""
        # Get logs
        ok, logs = self._ssh_exec(job, "cat /workspace/job.log 2>/dev/null || echo 'No logs'", timeout=30)
        if ok:
            job.logs = logs[:50000]  # Limit to 50KB

        # TODO: Upload outputs to R2 if configured
        if job.config.upload_outputs_to_r2:
            for output_path in job.config.output_paths:
                # Check if path exists
                ok, _ = self._ssh_exec(job, f"test -d {output_path} || test -f {output_path}", timeout=10)
                if ok:
                    logger.info(f"[{job.id}] Output found at {output_path}")
                    # TODO: Upload to R2

    async def _destroy_instance(self, job: Job, reason: str):
        """DESTROY the GPU instance - always called"""
        if not job.instance_id:
            return

        logger.info(f"[{job.id}] DESTROYING instance {job.instance_id} (reason: {reason})")

        try:
            self.vast.destroy_instance(job.instance_id)
            logger.info(f"[{job.id}] Instance {job.instance_id} destroyed")
        except Exception as e:
            logger.error(f"[{job.id}] Failed to destroy instance: {e}")

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        job = self.jobs.get(job_id)
        if not job:
            return False

        if job.is_finished:
            return False

        job.status = JobStatus.CANCELLED
        job.completion_reason = JobCompletionReason.USER_CANCEL
        job.completed_at = datetime.utcnow()
        job.update_cost()

        # Destroy instance
        if job.instance_id:
            try:
                self.vast.destroy_instance(job.instance_id)
            except:
                pass

        logger.info(f"Job {job_id} cancelled")
        return True

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def list_jobs(self, user_id: Optional[str] = None, limit: int = 50) -> List[Job]:
        """List jobs, optionally filtered by user"""
        jobs = list(self.jobs.values())

        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]

        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def get_job_logs(self, job_id: str) -> Optional[str]:
        """Get logs for a job"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        return job.logs


# Singleton instance
_job_manager: Optional[JobManager] = None
_jobs_store: Dict[str, Job] = {}


def get_job_manager(api_key: str) -> JobManager:
    """Get or create JobManager singleton"""
    global _job_manager

    if _job_manager is None or _job_manager.api_key != api_key:
        _job_manager = JobManager(api_key)
        _job_manager.jobs = _jobs_store

    return _job_manager
