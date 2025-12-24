"""
Cold Start Strategy for GPU Provisioning

Handles resume from paused/hibernated instances with automatic failover.

When resume fails (SSH not ready), automatically:
1. Launch backup machine from snapshot
2. Race between resume and backup
3. First to have working SSH wins
4. Destroy the loser
"""
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import (
    ProvisioningStrategy,
    ProvisionConfig,
    ProvisionResult,
    MachineCandidate,
)

logger = logging.getLogger(__name__)


@dataclass
class ColdStartConfig:
    """Configuration for cold start with failover"""
    # Instance to resume
    instance_id: int

    # Timeout to wait for resume before launching backup
    resume_timeout: int = 60

    # If True, immediately launch backup in parallel with resume
    # If False, wait for resume_timeout before launching backup
    parallel_backup: bool = True

    # Snapshot URL for backup machine (optional)
    # If not provided, will provision fresh machine
    snapshot_url: Optional[str] = None

    # Configuration for backup machine
    backup_config: Optional[ProvisionConfig] = None

    # Max time to wait for either machine
    total_timeout: int = 180

    # SSH verification timeout
    ssh_timeout: int = 30


class ColdStartStrategy(ProvisioningStrategy):
    """
    Cold Start Strategy: Resume with automatic failover.

    Algorithm:
    1. Start resume on paused instance
    2. Optionally start backup machine in parallel
    3. Poll both for SSH readiness
    4. First with working SSH wins
    5. Destroy the loser

    This strategy is designed for serverless/economic mode where
    instances are frequently paused and need fast cold starts.
    """

    @property
    def name(self) -> str:
        return "coldstart"

    def provision(
        self,
        config: ProvisionConfig,
        vast_service: Any,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Standard provision method - not used for cold start.

        Use resume_with_failover() instead.
        """
        return ProvisionResult(
            success=False,
            error="ColdStartStrategy requires resume_with_failover() method",
        )

    def resume_with_failover(
        self,
        coldstart_config: ColdStartConfig,
        vast_service: Any,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Resume a paused instance with automatic failover.

        If resume fails or SSH doesn't work, launch backup machine.

        Args:
            coldstart_config: Cold start configuration
            vast_service: VastService instance
            progress_callback: Optional callback for progress updates

        Returns:
            ProvisionResult with the winning machine
        """
        start_time = time.time()
        instance_id = coldstart_config.instance_id

        def report_progress(status: str, message: str, progress: int = 0):
            if progress_callback:
                progress_callback(status, message, progress)
            logger.info(f"[ColdStart] {status}: {message}")

        try:
            # Step 1: Start resume
            report_progress("resuming", f"Resuming instance {instance_id}...", 10)

            resume_success = vast_service.resume_instance(instance_id)
            if not resume_success:
                logger.warning(f"[ColdStart] Resume API call failed for {instance_id}")
                # Continue anyway - sometimes API fails but resume works

            # Step 2: Start backup if parallel mode
            backup_future = None
            backup_instance_id = None

            if coldstart_config.parallel_backup and coldstart_config.backup_config:
                report_progress(
                    "backup",
                    "Launching backup machine in parallel...",
                    20,
                )

                # Import here to avoid circular dependency
                from .race import RaceStrategy

                def launch_backup():
                    strategy = RaceStrategy()
                    return strategy.provision(
                        config=coldstart_config.backup_config,
                        vast_service=vast_service,
                        progress_callback=None,  # Don't spam logs
                    )

                with ThreadPoolExecutor(max_workers=1) as executor:
                    backup_future = executor.submit(launch_backup)

            # Step 3: Race for SSH readiness
            report_progress("waiting", "Waiting for SSH to be ready...", 30)

            winner_type = None  # "resume" or "backup"
            winner_result = None

            race_start = time.time()
            while time.time() - race_start < coldstart_config.total_timeout:
                elapsed = int(time.time() - race_start)
                progress = 30 + int((elapsed / coldstart_config.total_timeout) * 60)

                # Check resumed instance
                if self._check_ssh_ready(vast_service, instance_id, coldstart_config.ssh_timeout):
                    winner_type = "resume"
                    status = vast_service.get_instance_status(instance_id)
                    winner_result = ProvisionResult(
                        success=True,
                        instance_id=instance_id,
                        ssh_host=status.get("ssh_host"),
                        ssh_port=status.get("ssh_port"),
                        public_ip=status.get("public_ipaddr"),
                        gpu_name=status.get("gpu_name"),
                        dph_total=status.get("dph_total", 0),
                        total_time_seconds=time.time() - start_time,
                    )
                    break

                # Check backup if launched
                if backup_future and backup_future.done():
                    try:
                        backup_result = backup_future.result()
                        if backup_result.success:
                            # Verify SSH works on backup
                            if self._verify_ssh_command(
                                backup_result.ssh_host,
                                backup_result.ssh_port,
                                coldstart_config.ssh_timeout,
                            ):
                                winner_type = "backup"
                                winner_result = backup_result
                                backup_instance_id = backup_result.instance_id
                                break
                    except Exception as e:
                        logger.warning(f"[ColdStart] Backup failed: {e}")

                # Launch backup if not parallel and timeout reached
                if (
                    not coldstart_config.parallel_backup
                    and coldstart_config.backup_config
                    and elapsed >= coldstart_config.resume_timeout
                    and backup_future is None
                ):
                    report_progress(
                        "backup",
                        f"Resume timeout ({coldstart_config.resume_timeout}s), launching backup...",
                        50,
                    )

                    from .race import RaceStrategy

                    def launch_backup():
                        strategy = RaceStrategy()
                        return strategy.provision(
                            config=coldstart_config.backup_config,
                            vast_service=vast_service,
                        )

                    with ThreadPoolExecutor(max_workers=1) as executor:
                        backup_future = executor.submit(launch_backup)

                report_progress(
                    "waiting",
                    f"Waiting... ({elapsed}s/{coldstart_config.total_timeout}s)",
                    progress,
                )

                time.sleep(2)

            # Step 4: Cleanup loser
            if winner_result:
                if winner_type == "resume" and backup_instance_id:
                    # Resume won, destroy backup
                    report_progress("cleanup", f"Resume won! Destroying backup {backup_instance_id}...", 95)
                    try:
                        vast_service.destroy_instance(backup_instance_id)
                    except Exception as e:
                        logger.warning(f"[ColdStart] Failed to destroy backup: {e}")

                elif winner_type == "backup":
                    # Backup won, destroy paused instance
                    report_progress("cleanup", f"Backup won! Destroying paused instance {instance_id}...", 95)
                    try:
                        vast_service.destroy_instance(instance_id)
                    except Exception as e:
                        logger.warning(f"[ColdStart] Failed to destroy paused instance: {e}")

                report_progress("ready", f"{winner_type.title()} ready!", 100)
                return winner_result

            # No winner
            report_progress("failed", "Neither resume nor backup succeeded", 100)
            return ProvisionResult(
                success=False,
                error=f"Cold start failed after {coldstart_config.total_timeout}s",
                total_time_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"[ColdStart] Error: {e}")
            return ProvisionResult(
                success=False,
                error=str(e),
                total_time_seconds=time.time() - start_time,
            )

    def _check_ssh_ready(
        self,
        vast_service: Any,
        instance_id: int,
        timeout: int,
    ) -> bool:
        """Check if instance has SSH ready"""
        try:
            status = vast_service.get_instance_status(instance_id)
            actual_status = status.get("actual_status", "unknown")

            if actual_status != "running":
                return False

            ssh_host = status.get("ssh_host")
            ssh_port = status.get("ssh_port")

            if not ssh_host or not ssh_port:
                return False

            return self._verify_ssh_command(ssh_host, int(ssh_port), timeout)

        except Exception as e:
            logger.debug(f"[ColdStart] SSH check failed for {instance_id}: {e}")
            return False

    def _verify_ssh_command(
        self,
        ssh_host: str,
        ssh_port: int,
        timeout: int,
    ) -> bool:
        """Verify SSH works with a real command"""
        import subprocess
        import os

        ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-i", ssh_key_path,
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", f"ConnectTimeout={min(timeout, 10)}",
                    "-o", "BatchMode=yes",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    "echo SSH_OK"
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0 and "SSH_OK" in result.stdout

        except Exception:
            return False


# Convenience function for cold start with failover
def resume_with_failover(
    vast_service: Any,
    instance_id: int,
    backup_config: Optional[ProvisionConfig] = None,
    parallel_backup: bool = True,
    resume_timeout: int = 60,
    total_timeout: int = 180,
    progress_callback: Optional[callable] = None,
) -> ProvisionResult:
    """
    Resume a paused instance with automatic failover.

    Args:
        vast_service: VastService instance
        instance_id: Instance to resume
        backup_config: Config for backup machine (optional)
        parallel_backup: If True, launch backup immediately in parallel
        resume_timeout: Seconds to wait before launching backup (if not parallel)
        total_timeout: Max time to wait for either machine
        progress_callback: Optional callback for progress updates

    Returns:
        ProvisionResult with the winning machine

    Example:
        from src.services.gpu.strategies import resume_with_failover, ProvisionConfig

        # Resume with parallel backup
        result = resume_with_failover(
            vast_service=vast_client,
            instance_id=12345,
            backup_config=ProvisionConfig(
                gpu_name="RTX 4090",
                max_price=1.0,
            ),
            parallel_backup=True,
        )

        if result.success:
            print(f"Ready at {result.ssh_host}:{result.ssh_port}")
    """
    coldstart_config = ColdStartConfig(
        instance_id=instance_id,
        backup_config=backup_config,
        parallel_backup=parallel_backup,
        resume_timeout=resume_timeout,
        total_timeout=total_timeout,
    )

    strategy = ColdStartStrategy()
    return strategy.resume_with_failover(
        coldstart_config=coldstart_config,
        vast_service=vast_service,
        progress_callback=progress_callback,
    )
