"""
Race Strategy for GPU Provisioning

Creates multiple machines in parallel (batches of N).
First machine to have SSH accessible wins.
Losers are destroyed.

This is the most reliable strategy for fast provisioning,
as Vast.ai machines can have variable startup times.

Improvements:
- SSH Retry: If winner fails SSH command after winning, automatically
  destroy it and continue racing with remaining candidates
- Failover: Configurable max_ssh_retries to try multiple machines
"""
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import (
    ProvisioningStrategy,
    ProvisionConfig,
    ProvisionResult,
    MachineCandidate,
    ProvisionStatus,
)

logger = logging.getLogger(__name__)


# Default max retries when SSH fails on winner
DEFAULT_MAX_SSH_RETRIES = 3


class RaceStrategy(ProvisioningStrategy):
    """
    Race Strategy: Create multiple machines in parallel, first ready wins.

    Algorithm:
    1. Search for available offers
    2. Create batch_size machines in parallel
    3. Poll all machines for SSH readiness (every check_interval seconds)
    4. First machine with SSH accessible wins
    5. Destroy all losers
    6. If no winner in batch_timeout, try next batch
    7. Repeat up to max_batches times

    This strategy is optimized for speed and reliability.
    """

    @property
    def name(self) -> str:
        return "race"

    def provision(
        self,
        config: ProvisionConfig,
        vast_service: Any,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """Execute race strategy provisioning"""
        start_time = time.time()
        total_machines_tried = 0
        total_machines_created = 0
        all_candidates: List[Tuple[MachineCandidate, float]] = []

        def report_progress(status: str, message: str, progress: int = 0):
            if progress_callback:
                progress_callback(status, message, progress)
            logger.info(f"[RaceStrategy] {status}: {message}")

        try:
            # Search for offers
            report_progress("searching", "Searching for GPU offers...", 5)
            offers = self._search_offers(vast_service, config)

            if not offers:
                return ProvisionResult(
                    success=False,
                    error="No offers found matching criteria",
                    total_time_seconds=time.time() - start_time,
                )

            report_progress("searching", f"Found {len(offers)} offers", 10)

            winner: Optional[MachineCandidate] = None

            # Process in batches
            for batch_num in range(config.max_batches):
                if winner:
                    break

                batch_start_idx = batch_num * config.batch_size
                batch_offers = offers[batch_start_idx:batch_start_idx + config.batch_size]

                if not batch_offers:
                    break

                batch_progress_base = 10 + (batch_num * 25)
                report_progress(
                    "creating",
                    f"Batch {batch_num + 1}/{config.max_batches}: Creating {len(batch_offers)} machines...",
                    batch_progress_base,
                )

                # Create machines in parallel
                batch_candidates = self._create_batch(
                    vast_service, batch_offers, config
                )

                total_machines_tried += len(batch_offers)
                total_machines_created += len(batch_candidates)
                all_candidates.extend(batch_candidates)

                if not batch_candidates:
                    report_progress(
                        "waiting",
                        f"Batch {batch_num + 1}: No machines created, trying next batch",
                        batch_progress_base + 5,
                    )
                    continue

                # Race for SSH connection
                report_progress(
                    "waiting",
                    f"Waiting for first machine to be ready ({len(batch_candidates)} racing)...",
                    batch_progress_base + 10,
                )

                winner = self._race_for_ready(
                    vast_service,
                    batch_candidates,
                    config,
                    progress_callback=lambda s, m, p: report_progress(
                        s, m, batch_progress_base + 10 + int(p * 0.15)
                    ),
                )

                if not winner:
                    report_progress(
                        "waiting",
                        f"Batch {batch_num + 1}: No machine ready in {config.batch_timeout}s",
                        batch_progress_base + 25,
                    )

            # Cleanup - destroy all non-winners
            destroyed = self._cleanup(vast_service, all_candidates, winner)
            logger.info(f"[RaceStrategy] Cleaned up {destroyed} machines")

            total_time = time.time() - start_time

            if winner:
                report_progress("ready", f"Machine ready: {winner.gpu_name}", 100)
                return ProvisionResult(
                    success=True,
                    instance_id=winner.instance_id,
                    ssh_host=winner.ssh_host,
                    ssh_port=winner.ssh_port,
                    public_ip=winner.public_ip or winner.ssh_host,
                    gpu_name=winner.gpu_name,
                    dph_total=winner.dph_total,
                    port_mappings=winner.port_mappings,
                    rounds_attempted=batch_num + 1,
                    machines_tried=total_machines_tried,
                    machines_created=total_machines_created,
                    total_time_seconds=total_time,
                    time_to_ready_seconds=winner.ready_time,
                )
            else:
                report_progress("failed", "No machine became ready", 100)
                return ProvisionResult(
                    success=False,
                    error=f"No machine ready after {config.max_batches} batches ({total_machines_tried} tried)",
                    rounds_attempted=config.max_batches,
                    machines_tried=total_machines_tried,
                    machines_created=total_machines_created,
                    total_time_seconds=total_time,
                )

        except Exception as e:
            logger.error(f"[RaceStrategy] Error: {e}")
            # Emergency cleanup
            self._cleanup(vast_service, all_candidates, None)
            return ProvisionResult(
                success=False,
                error=str(e),
                machines_tried=total_machines_tried,
                machines_created=total_machines_created,
                total_time_seconds=time.time() - start_time,
            )

    def _search_offers(
        self,
        vast_service: Any,
        config: ProvisionConfig,
    ) -> List[Dict[str, Any]]:
        """Search for matching GPU offers"""
        offers = vast_service.search_offers(
            gpu_name=config.gpu_name,
            num_gpus=config.num_gpus,
            max_price=config.max_price,
            min_disk=config.disk_space,
            min_inet_down=config.min_inet_down,
            min_reliability=config.min_reliability,
            region=config.region if config.region != "global" else None,
            machine_type=config.machine_type,
            limit=config.batch_size * config.max_batches * 2,
        )

        # Sort by reliability (higher = better) then by internet speed
        # Prioritize machines with high reliability scores - they start faster
        offers.sort(
            key=lambda o: (
                o.get("reliability2", o.get("reliability", 0)),  # Primary: reliability
                o.get("inet_down", 0),  # Secondary: internet speed
            ),
            reverse=True,
        )
        return offers

    def _create_batch(
        self,
        vast_service: Any,
        offers: List[Dict[str, Any]],
        config: ProvisionConfig,
    ) -> List[Tuple[MachineCandidate, float]]:
        """Create machines in parallel, return list of (candidate, start_time)"""
        candidates = []

        def create_one(offer: Dict[str, Any], delay: float) -> Optional[Tuple[MachineCandidate, float]]:
            if delay > 0:
                time.sleep(delay)

            start_time = time.time()
            max_retries = 2
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    instance_id = vast_service.create_instance(
                        offer_id=offer["id"],
                        image=config.image or "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
                        disk=config.disk_space,
                        ports=config.ports,
                        onstart_cmd=config.onstart_cmd,
                        docker_options=config.docker_options,
                        label=config.label,
                        use_template=False,
                    )

                    if instance_id:
                        candidate = MachineCandidate(
                            instance_id=instance_id,
                            offer_id=offer["id"],
                            gpu_name=offer.get("gpu_name", "unknown"),
                            dph_total=offer.get("dph_total", 0),
                            provision_start_time=start_time,
                            offer=offer,
                        )
                        logger.info(f"[RaceStrategy] Created {offer.get('gpu_name')} (ID: {instance_id})")
                        return (candidate, start_time)
                    break  # No instance_id but no exception - don't retry

                except Exception as e:
                    error_str = str(e).lower()
                    # Retry on rate limit (429)
                    if "429" in str(e) or "too many" in error_str:
                        if attempt < max_retries - 1:
                            logger.info(f"[RaceStrategy] Rate limited, waiting {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                    # Don't retry on 400 Bad Request (offer unavailable)
                    logger.warning(f"[RaceStrategy] Failed to create offer {offer['id']}: {e}")
                    break

            return None

        # Stagger creation to avoid rate limits (500ms between each)
        with ThreadPoolExecutor(max_workers=min(len(offers), 3)) as executor:  # Max 3 parallel
            futures = {
                executor.submit(create_one, offer, idx * 0.5): offer
                for idx, offer in enumerate(offers)
            }

            for future in as_completed(futures, timeout=30):
                try:
                    result = future.result()
                    if result:
                        candidates.append(result)
                except Exception:
                    pass

        return candidates

    def _race_for_ready(
        self,
        vast_service: Any,
        candidates: List[Tuple[MachineCandidate, float]],
        config: ProvisionConfig,
        progress_callback: Optional[callable] = None,
    ) -> Optional[MachineCandidate]:
        """
        Race all candidates - first with SSH ready wins.

        Returns the winning candidate or None.
        """
        batch_start = time.time()
        destroyed_ids = set()

        while time.time() - batch_start < config.batch_timeout:
            # Update SSH info for all candidates
            active_candidates = [
                (c, t) for c, t in candidates
                if c.instance_id not in destroyed_ids
            ]

            if not active_candidates:
                return None

            # Check all candidates in parallel
            winner = self._check_candidates_parallel(
                vast_service, active_candidates, config
            )

            if winner:
                return winner

            elapsed = int(time.time() - batch_start)
            if progress_callback:
                progress = int((elapsed / config.batch_timeout) * 100)
                progress_callback(
                    "waiting",
                    f"Waiting... ({elapsed}s/{config.batch_timeout}s, {len(active_candidates)} machines)",
                    progress,
                )

            time.sleep(config.check_interval)

        return None

    def _check_candidates_parallel(
        self,
        vast_service: Any,
        candidates: List[Tuple[MachineCandidate, float]],
        config: ProvisionConfig,
    ) -> Optional[MachineCandidate]:
        """Check SSH connectivity for all candidates in parallel"""

        def check_one(candidate: MachineCandidate, start_time: float) -> Optional[MachineCandidate]:
            try:
                status = vast_service.get_instance_status(candidate.instance_id)
                actual_status = status.get("status")

                if actual_status == "running":
                    ssh_host = status.get("ssh_host")
                    ssh_port = status.get("ssh_port")

                    if ssh_host and ssh_port:
                        candidate.ssh_host = ssh_host
                        candidate.ssh_port = int(ssh_port)
                        candidate.public_ip = status.get("public_ipaddr", ssh_host)

                        # Get port mappings
                        ports = status.get("ports", {})
                        for port in config.ports:
                            mapped = self._get_mapped_port(ports, port)
                            if mapped:
                                candidate.port_mappings[port] = mapped

                        # Test SSH
                        if self._test_ssh_connection(ssh_host, int(ssh_port)):
                            candidate.connected = True
                            candidate.status = "ready"
                            candidate.ready_time = time.time() - start_time
                            logger.info(
                                f"[RaceStrategy] {candidate.gpu_name} ready in "
                                f"{candidate.ready_time:.1f}s at {ssh_host}:{ssh_port}"
                            )
                            return candidate

            except Exception as e:
                logger.debug(f"[RaceStrategy] Check failed for {candidate.instance_id}: {e}")

            return None

        with ThreadPoolExecutor(max_workers=len(candidates)) as executor:
            futures = {
                executor.submit(check_one, c, t): (c, t)
                for c, t in candidates
            }

            for future in as_completed(futures, timeout=10):
                try:
                    result = future.result()
                    if result:
                        return result
                except Exception:
                    pass

        return None

    def _cleanup(
        self,
        vast_service: Any,
        candidates: List[Tuple[MachineCandidate, float]],
        winner: Optional[MachineCandidate],
    ) -> int:
        """Destroy all non-winning machines"""
        destroyed = 0
        winner_id = winner.instance_id if winner else None

        for candidate, _ in candidates:
            if candidate.instance_id != winner_id:
                try:
                    vast_service.destroy_instance(candidate.instance_id)
                    destroyed += 1
                    logger.debug(f"[RaceStrategy] Destroyed loser {candidate.instance_id}")
                except Exception as e:
                    logger.warning(f"[RaceStrategy] Failed to destroy {candidate.instance_id}: {e}")

        return destroyed

    def _verify_ssh_works(
        self,
        candidate: MachineCandidate,
        timeout: int = 30,
    ) -> bool:
        """
        Verify SSH connection actually works with a real command.

        This is more thorough than just testing if port is open.
        Some machines have SSH port open but fail to accept connections.
        """
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
                    "-o", f"ConnectTimeout={timeout}",
                    "-o", "BatchMode=yes",
                    "-p", str(candidate.ssh_port),
                    f"root@{candidate.ssh_host}",
                    "echo SSH_VERIFIED && hostname"
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )

            if result.returncode == 0 and "SSH_VERIFIED" in result.stdout:
                logger.info(
                    f"[RaceStrategy] SSH verified for {candidate.gpu_name} "
                    f"({candidate.ssh_host}:{candidate.ssh_port}): {result.stdout.strip()}"
                )
                return True
            else:
                logger.warning(
                    f"[RaceStrategy] SSH verification failed for {candidate.gpu_name}: "
                    f"returncode={result.returncode}, stderr={result.stderr[:200]}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.warning(
                f"[RaceStrategy] SSH verification timed out for {candidate.gpu_name} "
                f"({candidate.ssh_host}:{candidate.ssh_port})"
            )
            return False
        except Exception as e:
            logger.warning(
                f"[RaceStrategy] SSH verification error for {candidate.gpu_name}: {e}"
            )
            return False

    def provision_with_failover(
        self,
        config: ProvisionConfig,
        vast_service: Any,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """
        Provision with automatic failover if SSH fails.

        This is the recommended method for production use:
        1. Run standard race strategy
        2. Verify winner's SSH actually works
        3. If SSH fails, destroy winner and try next candidate
        4. Repeat up to max_ssh_retries times

        Args:
            config: Provisioning configuration
            vast_service: VastService instance
            progress_callback: Optional callback for progress updates

        Returns:
            ProvisionResult with verified working SSH
        """
        start_time = time.time()
        ssh_attempts = 0
        failed_instances: List[int] = []

        def report_progress(status: str, message: str, progress: int = 0):
            if progress_callback:
                progress_callback(status, message, progress)
            logger.info(f"[RaceStrategy] {status}: {message}")

        # First, run normal provisioning
        result = self.provision(config, vast_service, progress_callback)

        if not result.success:
            return result

        # Verify SSH works with a real command
        while ssh_attempts < config.max_ssh_retries:
            ssh_attempts += 1

            candidate = MachineCandidate(
                instance_id=result.instance_id,
                offer_id=0,
                gpu_name=result.gpu_name or "unknown",
                ssh_host=result.ssh_host,
                ssh_port=result.ssh_port,
            )

            report_progress(
                "verifying",
                f"Verifying SSH works (attempt {ssh_attempts}/{config.max_ssh_retries})...",
                90 + ssh_attempts,
            )

            if self._verify_ssh_works(candidate, config.ssh_command_timeout):
                # SSH works! Return success
                result.total_time_seconds = time.time() - start_time
                return result

            # SSH failed - destroy this instance and try another
            logger.warning(
                f"[RaceStrategy] SSH failed for {result.instance_id}, "
                f"destroying and trying next (attempt {ssh_attempts}/{config.max_ssh_retries})"
            )

            failed_instances.append(result.instance_id)

            try:
                vast_service.destroy_instance(result.instance_id)
            except Exception as e:
                logger.warning(f"[RaceStrategy] Failed to destroy {result.instance_id}: {e}")

            # Try to provision again
            report_progress(
                "retrying",
                f"SSH failed, provisioning new machine (attempt {ssh_attempts + 1}/{config.max_ssh_retries})...",
                50,
            )

            result = self.provision(config, vast_service, progress_callback)

            if not result.success:
                # No more machines available
                result.error = (
                    f"SSH verification failed after {ssh_attempts} attempts. "
                    f"Failed instances: {failed_instances}. Last error: {result.error}"
                )
                result.total_time_seconds = time.time() - start_time
                return result

        # All retries exhausted
        return ProvisionResult(
            success=False,
            error=f"SSH verification failed after {ssh_attempts} attempts. Failed instances: {failed_instances}",
            machines_tried=result.machines_tried,
            machines_created=result.machines_created,
            total_time_seconds=time.time() - start_time,
        )
