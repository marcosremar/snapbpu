"""
Failover Service - Execução de failover via snapshot

Este serviço implementa o fluxo completo de failover:
1. Criar snapshot da GPU atual
2. Provisionar nova GPU
3. Restaurar snapshot
4. Validar e testar
"""

import asyncio
import time
import logging
import subprocess
from typing import Optional, Dict, Any

from .models import FailoverResult, FailoverPhase

logger = logging.getLogger(__name__)


class FailoverService:
    """
    Serviço de failover via snapshot.

    Fluxo:
    1. Criar snapshot (full ou incremental)
    2. Provisionar nova GPU via race strategy
    3. Restaurar snapshot
    4. Validar restore
    5. (Opcional) Testar inferência

    Uso:
        service = FailoverService(vast_api_key="...")
        result = await service.execute(
            gpu_instance_id=12345,
            ssh_host="ssh.vast.ai",
            ssh_port=12345,
        )
    """

    def __init__(
        self,
        vast_api_key: str,
        b2_endpoint: str = "https://s3.us-west-004.backblazeb2.com",
        b2_bucket: str = "dumoncloud-snapshot",
    ):
        self.vast_api_key = vast_api_key
        self.b2_endpoint = b2_endpoint
        self.b2_bucket = b2_bucket

        # Lazy init
        self._gpu_provisioner = None
        self._snapshot_service = None

    @property
    def gpu_provisioner(self):
        if self._gpu_provisioner is None:
            from src.services.gpu.provisioner import GPUProvisioner
            self._gpu_provisioner = GPUProvisioner(self.vast_api_key)
        return self._gpu_provisioner

    @property
    def snapshot_service(self):
        if self._snapshot_service is None:
            from src.services.gpu.snapshot import GPUSnapshotService
            self._snapshot_service = GPUSnapshotService(self.b2_endpoint, self.b2_bucket)
        return self._snapshot_service

    async def execute(
        self,
        gpu_instance_id: int,
        ssh_host: str,
        ssh_port: int,
        failover_id: str,
        workspace_path: str = "/workspace",
        model: Optional[str] = None,
        test_prompt: str = "Hello",
        min_gpu_ram: int = 10000,
        max_gpu_price: float = 1.0,
    ) -> FailoverResult:
        """
        Executa failover completo via snapshot.

        Fases:
        1. Criar snapshot
        2. Provisionar GPU
        3. Restaurar snapshot
        4. Validar
        5. (Opcional) Testar inferência

        Returns:
            FailoverResult com todos os detalhes
        """
        start_time = time.time()
        phase_timings = {}

        result = FailoverResult(
            success=False,
            failover_id=failover_id,
            machine_id=0,
            strategy_attempted="cpu_standby",
            original_gpu_id=gpu_instance_id,
            original_ssh_host=ssh_host,
            original_ssh_port=ssh_port,
        )

        try:
            # ============================================================
            # FASE 1: Criar Snapshot
            # ============================================================
            logger.info(f"[{failover_id}] Phase 1: Creating snapshot...")
            result.phase_history.append((FailoverPhase.SNAPSHOT_CREATION.value, time.time()))
            phase_start = time.time()

            snapshot_name = f"failover-{failover_id}"

            # Tentar encontrar snapshot base para incremental
            base_snapshot_id = self._find_base_snapshot(gpu_instance_id)

            if base_snapshot_id:
                logger.info(f"[{failover_id}] Found base: {base_snapshot_id}, using incremental...")
                try:
                    snapshot_info = self.snapshot_service.create_incremental_snapshot(
                        instance_id=str(gpu_instance_id),
                        ssh_host=ssh_host,
                        ssh_port=ssh_port,
                        base_snapshot_id=base_snapshot_id,
                        workspace_path=workspace_path,
                        snapshot_name=snapshot_name,
                    )
                    snapshot_info["snapshot_type"] = "incremental"
                except Exception as e:
                    logger.warning(f"[{failover_id}] Incremental failed, using full: {e}")
                    base_snapshot_id = None

            if not base_snapshot_id:
                logger.info(f"[{failover_id}] Creating full snapshot...")
                snapshot_info = self.snapshot_service.create_snapshot(
                    instance_id=str(gpu_instance_id),
                    ssh_host=ssh_host,
                    ssh_port=ssh_port,
                    workspace_path=workspace_path,
                    snapshot_name=snapshot_name,
                )
                snapshot_info["snapshot_type"] = "full"

            phase_timings["snapshot_creation"] = int((time.time() - phase_start) * 1000)
            result.snapshot_creation_ms = phase_timings["snapshot_creation"]
            result.snapshot_id = snapshot_info.get("snapshot_id", snapshot_name)
            result.snapshot_size_bytes = snapshot_info.get("size_compressed", 0)
            result.snapshot_type = snapshot_info.get("snapshot_type", "full")
            result.base_snapshot_id = base_snapshot_id
            result.files_changed = snapshot_info.get("files_changed")

            logger.info(
                f"[{failover_id}] Snapshot created ({result.snapshot_type}): "
                f"{result.snapshot_id} in {result.snapshot_creation_ms}ms"
            )

            # ============================================================
            # FASE 2: Provisionar Nova GPU
            # ============================================================
            logger.info(f"[{failover_id}] Phase 2: Provisioning new GPU...")
            result.phase_history.append((FailoverPhase.GPU_PROVISIONING.value, time.time()))
            phase_start = time.time()

            provision_result = await self.gpu_provisioner.provision_fast(
                min_gpu_ram=min_gpu_ram,
                max_price=max_gpu_price,
                gpus_per_round=5,
                timeout_per_round=90,
                max_rounds=2,
            )

            phase_timings["gpu_provisioning"] = int((time.time() - phase_start) * 1000)
            result.gpu_provisioning_ms = phase_timings["gpu_provisioning"]
            result.gpus_tried = provision_result.gpus_tried
            result.rounds_attempted = provision_result.rounds_attempted

            if not provision_result.success:
                raise Exception(f"GPU provisioning failed: {provision_result.error}")

            result.new_gpu_id = provision_result.instance_id
            result.new_ssh_host = provision_result.ssh_host
            result.new_ssh_port = provision_result.ssh_port
            result.new_gpu_name = provision_result.gpu_name

            logger.info(
                f"[{failover_id}] GPU provisioned: {result.new_gpu_name} "
                f"({result.new_ssh_host}:{result.new_ssh_port}) in {result.gpu_provisioning_ms}ms"
            )

            # ============================================================
            # FASE 3: Restaurar Snapshot
            # ============================================================
            logger.info(f"[{failover_id}] Phase 3: Restoring snapshot...")
            result.phase_history.append((FailoverPhase.SNAPSHOT_RESTORE.value, time.time()))
            phase_start = time.time()

            restore_info = self.snapshot_service.restore_snapshot(
                snapshot_id=snapshot_name,
                ssh_host=result.new_ssh_host,
                ssh_port=result.new_ssh_port,
                workspace_path=workspace_path,
            )

            phase_timings["restore"] = int((time.time() - phase_start) * 1000)
            result.restore_ms = phase_timings["restore"]

            logger.info(f"[{failover_id}] Snapshot restored in {result.restore_ms}ms")

            # ============================================================
            # FASE 4: Validar Restore
            # ============================================================
            logger.info(f"[{failover_id}] Phase 4: Validating restore...")
            result.phase_history.append((FailoverPhase.VALIDATION.value, time.time()))
            phase_start = time.time()

            validation = self._validate_restore(
                ssh_host=result.new_ssh_host,
                ssh_port=result.new_ssh_port,
                workspace_path=workspace_path,
                snapshot_info=snapshot_info,
            )

            phase_timings["validation"] = int((time.time() - phase_start) * 1000)
            result.validation_ms = phase_timings["validation"]

            if not validation["success"]:
                raise Exception(f"Validation failed: {validation.get('error')}")

            logger.info(f"[{failover_id}] Validation passed in {result.validation_ms}ms")

            # ============================================================
            # FASE 5: Testar Inferência (Opcional)
            # ============================================================
            if model:
                logger.info(f"[{failover_id}] Phase 5: Testing inference...")
                result.phase_history.append((FailoverPhase.INFERENCE_TEST.value, time.time()))
                phase_start = time.time()

                inference = await self._test_inference(
                    ssh_host=result.new_ssh_host,
                    ssh_port=result.new_ssh_port,
                    model=model,
                    prompt=test_prompt,
                )

                phase_timings["inference_test"] = int((time.time() - phase_start) * 1000)
                result.inference_test_ms = phase_timings["inference_test"]
                result.inference_success = inference.get("success", False)
                result.inference_response = inference.get("response")

                if result.inference_success:
                    logger.info(f"[{failover_id}] Inference test passed")
                else:
                    logger.warning(f"[{failover_id}] Inference test failed")

            # ============================================================
            # SUCESSO
            # ============================================================
            result.success = True
            result.total_ms = int((time.time() - start_time) * 1000)
            result.phase_timings = phase_timings
            result.phase_history.append((FailoverPhase.COMPLETED.value, time.time()))

            logger.info(
                f"[{failover_id}] FAILOVER COMPLETE in {result.total_ms}ms "
                f"(snapshot: {result.snapshot_creation_ms}ms, "
                f"gpu: {result.gpu_provisioning_ms}ms, "
                f"restore: {result.restore_ms}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"[{failover_id}] FAILOVER FAILED: {e}")
            result.error = str(e)
            result.total_ms = int((time.time() - start_time) * 1000)
            result.phase_timings = phase_timings
            result.phase_history.append((FailoverPhase.FAILED.value, time.time()))

            # Determinar fase que falhou
            if "snapshot_creation" not in phase_timings:
                result.failed_phase = "snapshot_creation"
            elif "gpu_provisioning" not in phase_timings:
                result.failed_phase = "gpu_provisioning"
            elif "restore" not in phase_timings:
                result.failed_phase = "restore"
            elif "validation" not in phase_timings:
                result.failed_phase = "validation"
            else:
                result.failed_phase = "inference_test"

            return result

    def _find_base_snapshot(self, gpu_instance_id: int) -> Optional[str]:
        """Encontra snapshot base mais recente para incremental"""
        try:
            result = subprocess.run(
                [
                    "s5cmd",
                    "--endpoint-url", self.b2_endpoint,
                    "ls",
                    f"s3://{self.b2_bucket}/snapshots/"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                base_snapshots = []

                for line in lines:
                    if f"periodic-{gpu_instance_id}-" in line or f"base-{gpu_instance_id}-" in line:
                        parts = line.split('/')
                        if parts:
                            snapshot_name = parts[-1].rstrip('/')
                            if snapshot_name:
                                base_snapshots.append(snapshot_name)

                if base_snapshots:
                    base_snapshots.sort()
                    latest = base_snapshots[-1]
                    logger.info(f"[FailoverService] Found base snapshot: {latest}")
                    return latest

        except Exception as e:
            logger.warning(f"[FailoverService] Error finding base snapshot: {e}")

        return None

    def _validate_restore(
        self,
        ssh_host: str,
        ssh_port: int,
        workspace_path: str,
        snapshot_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Valida que o restore foi feito corretamente"""
        try:
            count_cmd = f"find {workspace_path} -type f | wc -l"
            result = subprocess.run(
                [
                    "ssh", "-p", str(ssh_port),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    f"root@{ssh_host}",
                    count_cmd
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Failed to list files: {result.stderr.strip()[:200]}"
                }

            files_count = int(result.stdout.strip())

            # Verificar count esperado
            expected_files = None
            if "files" in snapshot_info:
                expected_files = len(snapshot_info["files"])
            elif "num_files" in snapshot_info:
                expected_files = snapshot_info["num_files"]

            if expected_files is not None:
                tolerance = max(1, int(expected_files * 0.05))
                if abs(files_count - expected_files) > tolerance:
                    return {
                        "success": False,
                        "error": f"File count mismatch: expected ~{expected_files}, got {files_count}",
                        "files_count": files_count,
                        "expected_files": expected_files
                    }

            if files_count == 0:
                return {
                    "success": False,
                    "error": "Workspace is empty after restore",
                    "files_count": 0
                }

            return {
                "success": True,
                "files_count": files_count,
                "expected_files": expected_files
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Validation timeout"}
        except Exception as e:
            return {"success": False, "error": f"Validation error: {str(e)}"}

    async def _test_inference(
        self,
        ssh_host: str,
        ssh_port: int,
        model: str,
        prompt: str,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Testa inferência Ollama na GPU"""
        try:
            # Verificar/iniciar Ollama
            check_cmd = f"curl -s http://localhost:11434/api/tags"
            result = subprocess.run(
                [
                    "ssh", "-p", str(ssh_port),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    f"root@{ssh_host}",
                    check_cmd
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                subprocess.run(
                    [
                        "ssh", "-p", str(ssh_port),
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null",
                        f"root@{ssh_host}",
                        "nohup ollama serve > /dev/null 2>&1 &"
                    ],
                    capture_output=True,
                    timeout=10
                )
                await asyncio.sleep(5)

            # Rodar inferência
            inference_cmd = f'ollama run {model} "{prompt}"'
            result = subprocess.run(
                [
                    "ssh", "-p", str(ssh_port),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    f"root@{ssh_host}",
                    inference_cmd
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "response": result.stdout.strip()[:500],
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip()[:200],
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Inference timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Função de conveniência
async def execute_failover(
    machine_id: int,
    gpu_instance_id: int,
    ssh_host: str,
    ssh_port: int,
    vast_api_key: Optional[str] = None,
    **kwargs
) -> FailoverResult:
    """Executa failover de forma rápida"""
    import os
    from .orchestrator import get_failover_orchestrator

    if not vast_api_key:
        vast_api_key = os.getenv("VAST_API_KEY", "")

    orchestrator = get_failover_orchestrator(vast_api_key)
    return await orchestrator.execute(
        machine_id=machine_id,
        gpu_instance_id=gpu_instance_id,
        ssh_host=ssh_host,
        ssh_port=ssh_port,
        **kwargs
    )
