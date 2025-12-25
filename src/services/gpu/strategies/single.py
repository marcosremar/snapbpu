"""
Single Strategy for GPU Provisioning

Creates a single machine and waits for it to be ready.
Simpler and cheaper than RaceStrategy but slower.

Best for:
- Cost-sensitive workloads
- When you don't need fast startup
- Testing/development
"""
import time
import logging
from typing import Optional, List, Dict, Any

from .base import (
    ProvisioningStrategy,
    ProvisionConfig,
    ProvisionResult,
    MachineCandidate,
)

logger = logging.getLogger(__name__)


class SingleStrategy(ProvisioningStrategy):
    """
    Single Strategy: Create one machine and wait.

    Algorithm:
    1. Search for available offers
    2. Try to create machine from best offer
    3. If creation fails, try next offer (up to max_retries)
    4. Poll for SSH readiness
    5. Return result (success or timeout)

    This strategy is simpler but may be slower than RaceStrategy.
    Use when cost is more important than startup time.
    """

    MAX_CREATE_RETRIES = 5  # Try up to 5 different offers if creation fails

    @property
    def name(self) -> str:
        return "single"

    def provision(
        self,
        config: ProvisionConfig,
        vast_service: Any,
        progress_callback: Optional[callable] = None,
    ) -> ProvisionResult:
        """Execute single-machine provisioning with retry on creation failure"""
        start_time = time.time()
        candidate: Optional[MachineCandidate] = None
        machines_tried = 0

        def report_progress(status: str, message: str, progress: int = 0):
            if progress_callback:
                progress_callback(status, message, progress)
            logger.info(f"[SingleStrategy] {status}: {message}")

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

            # Try to create machine, with retry on failure
            max_retries = min(self.MAX_CREATE_RETRIES, len(offers))
            last_error = None

            for i in range(max_retries):
                offer = offers[i]
                machines_tried += 1

                report_progress(
                    "creating",
                    f"Creating {offer.get('gpu_name')} @ ${offer.get('dph_total', 0):.2f}/hr... (attempt {i+1}/{max_retries})",
                    20,
                )

                candidate = self._create_machine(vast_service, offer, config)

                if candidate:
                    # Successfully created, break out of retry loop
                    break
                else:
                    last_error = f"Failed to create machine from offer {offer.get('id')}"
                    logger.warning(f"[SingleStrategy] {last_error}, trying next offer...")
                    candidate = None
                    # Small delay before trying next offer to avoid rate limiting
                    time.sleep(1)

            if not candidate:
                return ProvisionResult(
                    success=False,
                    error=f"Failed to create machine after {machines_tried} attempts: {last_error}",
                    machines_tried=machines_tried,
                    total_time_seconds=time.time() - start_time,
                )

            report_progress("waiting", "Waiting for machine to be ready...", 30)

            # Wait for SSH
            timeout = config.batch_timeout * config.max_batches  # Use total timeout
            ready = self._wait_for_ready(
                vast_service,
                candidate,
                config,
                timeout,
                progress_callback=lambda s, m, p: report_progress(s, m, 30 + int(p * 0.6)),
            )

            total_time = time.time() - start_time

            if ready:
                report_progress("ready", f"Machine ready: {candidate.gpu_name}", 100)
                return ProvisionResult(
                    success=True,
                    instance_id=candidate.instance_id,
                    ssh_host=candidate.ssh_host,
                    ssh_port=candidate.ssh_port,
                    public_ip=candidate.public_ip or candidate.ssh_host,
                    gpu_name=candidate.gpu_name,
                    dph_total=candidate.dph_total,
                    port_mappings=candidate.port_mappings,
                    rounds_attempted=1,
                    machines_tried=machines_tried,
                    machines_created=1,
                    total_time_seconds=total_time,
                    time_to_ready_seconds=candidate.ready_time,
                )
            else:
                # Cleanup failed machine
                self._cleanup(vast_service, candidate)

                report_progress("failed", f"Machine did not become ready in {timeout}s", 100)
                return ProvisionResult(
                    success=False,
                    error=f"Machine did not become ready in {timeout}s",
                    rounds_attempted=1,
                    machines_tried=machines_tried,
                    machines_created=1,
                    total_time_seconds=total_time,
                )

        except Exception as e:
            logger.error(f"[SingleStrategy] Error: {e}")
            if candidate:
                self._cleanup(vast_service, candidate)

            return ProvisionResult(
                success=False,
                error=str(e),
                machines_tried=machines_tried,
                machines_created=1 if candidate else 0,
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
            limit=20,  # Get more offers for retry capability
        )

        # Sort by reliability first (higher = faster startup), then by price
        offers.sort(
            key=lambda o: (
                -o.get("reliability2", o.get("reliability", 0)),  # Negative for descending
                o.get("dph_total", 999),  # Then by price ascending
            )
        )
        return offers

    def _create_machine(
        self,
        vast_service: Any,
        offer: Dict[str, Any],
        config: ProvisionConfig,
    ) -> Optional[MachineCandidate]:
        """Create a single machine"""
        start_time = time.time()

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
                logger.info(f"[SingleStrategy] Created {offer.get('gpu_name')} (ID: {instance_id})")
                return MachineCandidate(
                    instance_id=instance_id,
                    offer_id=offer["id"],
                    gpu_name=offer.get("gpu_name", "unknown"),
                    dph_total=offer.get("dph_total", 0),
                    provision_start_time=start_time,
                    offer=offer,
                )

        except Exception as e:
            logger.warning(f"[SingleStrategy] Failed to create machine from offer {offer.get('id')}: {e}")

        return None

    def _wait_for_ready(
        self,
        vast_service: Any,
        candidate: MachineCandidate,
        config: ProvisionConfig,
        timeout: int,
        progress_callback: Optional[callable] = None,
    ) -> bool:
        """Wait for machine to have SSH ready"""
        start_time = time.time()

        while time.time() - start_time < timeout:
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
                            candidate.ready_time = time.time() - candidate.provision_start_time
                            logger.info(
                                f"[SingleStrategy] Ready in {candidate.ready_time:.1f}s"
                            )
                            return True

            except Exception as e:
                logger.debug(f"[SingleStrategy] Status check failed: {e}")

            elapsed = int(time.time() - start_time)
            if progress_callback:
                progress = int((elapsed / timeout) * 100)
                progress_callback("waiting", f"Waiting... ({elapsed}s/{timeout}s)", progress)

            time.sleep(config.check_interval)

        return False

    def _cleanup(self, vast_service: Any, candidate: MachineCandidate) -> None:
        """Destroy failed machine"""
        try:
            vast_service.destroy_instance(candidate.instance_id)
            logger.info(f"[SingleStrategy] Destroyed {candidate.instance_id}")
        except Exception as e:
            logger.warning(f"[SingleStrategy] Failed to destroy {candidate.instance_id}: {e}")
