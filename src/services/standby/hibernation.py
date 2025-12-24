"""
Auto Hibernation Manager - Gerencia hibernação automática de instâncias GPU

Roda como agente em background no servidor de controle (VPS).
Monitora status de todas as instâncias e automatically:
- Hiberna GPUs ociosas > 3 min
- Deleta instâncias hibernadas > 30 min (mantém snapshot)
- Acorda instâncias sob demanda

Integra com:
- GPUSnapshotService (criar/restaurar snapshots ANS)
- VastService (criar/destruir instâncias)
- Database (InstanceStatus, HibernationEvent)
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.services.agent_manager import Agent
from src.services.gpu.snapshot import GPUSnapshotService
from src.services.gpu.vast import VastService
from src.config.database import SessionLocal
from src.models.instance_status import InstanceStatus, HibernationEvent
from src.services.usage_service import UsageService

logger = logging.getLogger(__name__)


class AutoHibernationManager(Agent):
    """Gerenciador de auto-hibernação de instâncias GPU multi-provider."""

    def __init__(
        self,
        vast_api_key: str,
        r2_endpoint: str,
        r2_bucket: str,
        check_interval: int = 30,
        tensordock_auth_id: str = None,
        tensordock_api_token: str = None,
        gcp_credentials: dict = None,
        gcp_project_id: str = None,
    ):
        """
        Inicializa o manager de auto-hibernação multi-provider.

        Args:
            vast_api_key: API key da Vast.ai
            r2_endpoint: Endpoint do Cloudflare R2
            r2_bucket: Nome do bucket R2
            check_interval: Intervalo de verificação em segundos (padrão: 30)
            tensordock_auth_id: Auth ID do TensorDock (opcional)
            tensordock_api_token: API Token do TensorDock (opcional)
            gcp_credentials: Credenciais GCP em formato dict (opcional)
            gcp_project_id: Project ID do GCP (opcional)
        """
        super().__init__(name="AutoHibernation")

        self.vast_service = VastService(api_key=vast_api_key)
        self.snapshot_service = GPUSnapshotService(r2_endpoint, r2_bucket)
        self.check_interval = check_interval
        
        # TensorDock
        self.tensordock_auth_id = tensordock_auth_id
        self.tensordock_api_token = tensordock_api_token
        self.tensordock_enabled = bool(tensordock_auth_id and tensordock_api_token)
        
        # GCP
        self.gcp_credentials = gcp_credentials
        self.gcp_project_id = gcp_project_id or (gcp_credentials.get('project_id') if gcp_credentials else None)
        self.gcp_enabled = bool(gcp_credentials and self.gcp_project_id)

        providers = ["Vast.ai"]
        if self.tensordock_enabled:
            providers.append("TensorDock")
        if self.gcp_enabled:
            providers.append("GCP")
            
        logger.info(f"AutoHibernationManager inicializado (interval={check_interval}s, providers={providers})")

    def run(self):
        """Loop principal do agente."""
        logger.info("Iniciando loop de auto-hibernação...")

        while self.running:
            try:
                self._check_all_instances()
            except Exception as e:
                logger.error(f"Erro no ciclo de verificação: {e}", exc_info=True)

            # Aguardar próximo ciclo (sleep interrompível)
            if self.running:
                self.sleep(self.check_interval)

        logger.info("Loop de auto-hibernação finalizado")

    def _check_all_instances(self):
        """Verifica status de todas as instâncias e aplica políticas de hibernação."""
        db = SessionLocal()
        try:
            # 1. Verificar instâncias REGISTRADAS no DB (comportamento original)
            instances = db.query(InstanceStatus).filter(
                InstanceStatus.auto_hibernation_enabled == True
            ).all()

            logger.debug(f"Verificando {len(instances)} instâncias registradas no DB...")

            for instance in instances:
                try:
                    self._check_instance(db, instance)
                except Exception as e:
                    logger.error(f"Erro ao verificar instância {instance.instance_id}: {e}")

            db.commit()

            # 2. Verificar instâncias NÃO REGISTRADAS diretamente na Vast.ai
            self._check_untracked_vast_instances(db)
            
            # 3. Verificar instâncias no TensorDock
            if self.tensordock_enabled:
                self._check_tensordock_instances()
            
            # 4. Verificar instâncias no GCP
            if self.gcp_enabled:
                self._check_gcp_instances()

        except Exception as e:
            logger.error(f"Erro ao buscar instâncias: {e}")
            db.rollback()
        finally:
            db.close()

    def _check_untracked_vast_instances(self, db):
        """
        Verifica instâncias na Vast.ai que não estão sendo rastreadas.

        Lógica de hibernação (TODAS as instâncias, independente de label):
        - Se GPU >= 2% → ATIVA (continua)
        - Se GPU < 2% MAS CPU >= 15% → ATIVA (continua)
        - Se GPU < 2% E CPU < 15% → IDLE → PAUSAR
        - Depois de 24h pausada → DESTRUIR

        Labels (dumont:wizard, dumont:job, etc) são apenas para identificação/logging,
        NÃO afetam a lógica de hibernação.
        """
        import subprocess

        # Thresholds
        GPU_THRESHOLD = 2.0   # % - Abaixo disso é considerado idle
        CPU_THRESHOLD = 15.0  # % - Abaixo disso é considerado idle
        GRACE_PERIOD_MINUTES = 15  # Tempo antes de pausar uma instância idle
        PAUSED_DESTROY_HOURS = 24  # Horas pausada antes de destruir

        try:
            vast_instances = self.vast_service.get_my_instances()

            if not vast_instances:
                return

            # IDs das instâncias rastreadas no DB
            tracked_ids = set()
            tracked = db.query(InstanceStatus.vast_instance_id).all()
            for t in tracked:
                if t.vast_instance_id:
                    tracked_ids.add(t.vast_instance_id)

            # Verificar instâncias não rastreadas
            untracked = [i for i in vast_instances if i.get('id') not in tracked_ids]

            if untracked:
                logger.info(f"Encontradas {len(untracked)} instâncias Vast.ai não rastreadas")

            for inst in untracked:
                inst_id = inst.get('id')
                status = inst.get('actual_status')
                gpu = inst.get('gpu_name', 'Unknown')
                dph = inst.get('dph_total', 0)
                ssh_host = inst.get('ssh_host')
                ssh_port = inst.get('ssh_port')
                inst_label = inst.get('label', '') or ''  # Apenas para logging

                # === Instâncias PAUSED - verificar se devem ser destruídas ===
                if status == 'paused':
                    # Verificar quanto tempo está pausada
                    stop_date = inst.get('stop_date')  # Unix timestamp quando parou
                    paused_hours = 999  # Default alto para destruir se não tiver data

                    if stop_date:
                        try:
                            paused_seconds = time.time() - float(stop_date)
                            paused_hours = paused_seconds / 3600
                        except:
                            paused_hours = 999

                    if paused_hours >= PAUSED_DESTROY_HOURS:
                        logger.warning(f"⚠ Instância {inst_id} ({gpu}) pausada há {paused_hours:.1f}h (>{PAUSED_DESTROY_HOURS}h) - DESTRUINDO")
                        if inst_label:
                            logger.info(f"  Label: {inst_label}")
                        try:
                            self.vast_service.destroy_instance(inst_id)
                            logger.info(f"✓ Instância {inst_id} destruída (pausada por {paused_hours:.1f}h)")
                        except Exception as e:
                            logger.error(f"Erro ao destruir {inst_id}: {e}")
                    else:
                        logger.debug(f"Instância {inst_id} ({gpu}) pausada há {paused_hours:.1f}h - aguardando ({PAUSED_DESTROY_HOURS}h para destruir)")
                    continue

                # === Instâncias EXITED - destruir imediatamente ===
                if status == 'exited':
                    logger.warning(f"Destruindo instância exited não rastreada: {inst_id} ({gpu})")
                    if inst_label:
                        logger.info(f"  Label: {inst_label}")
                    try:
                        self.vast_service.destroy_instance(inst_id)
                        logger.info(f"✓ Instância {inst_id} destruída (era exited)")
                    except Exception as e:
                        logger.error(f"Erro ao destruir {inst_id}: {e}")
                    continue

                # === Instâncias RUNNING - verificar uso de GPU E CPU ===
                if status == 'running' and ssh_host and ssh_port:
                    logger.info(f"Verificando uso em instância: {inst_id} ({gpu})")
                    if inst_label:
                        logger.info(f"  Label: {inst_label}")

                    try:
                        # Verificar uso de GPU E CPU via SSH
                        check_cmd = """
                            gpu_usage=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
                            cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' 2>/dev/null || echo "0")
                            echo "GPU:$gpu_usage CPU:$cpu_usage"
                        """

                        result = subprocess.run(
                            ["ssh", "-i", "/home/marcos/.ssh/id_rsa",
                             "-o", "StrictHostKeyChecking=no",
                             "-o", "ConnectTimeout=5",
                             "-o", "BatchMode=yes",
                             "-p", str(ssh_port),
                             f"root@{ssh_host}",
                             check_cmd],
                            capture_output=True, timeout=15, text=True
                        )

                        gpu_usage = 0.0
                        cpu_usage = 0.0

                        if result.returncode == 0 and result.stdout.strip():
                            output = result.stdout.strip()
                            for part in output.split():
                                if part.startswith("GPU:"):
                                    try:
                                        gpu_usage = float(part.replace("GPU:", ""))
                                    except:
                                        pass
                                elif part.startswith("CPU:"):
                                    try:
                                        cpu_usage = float(part.replace("CPU:", ""))
                                    except:
                                        pass

                        # Verificar se está ATIVA (GPU >= 2% OU CPU >= 15%)
                        is_active = (gpu_usage >= GPU_THRESHOLD) or (cpu_usage >= CPU_THRESHOLD)

                        if is_active:
                            logger.info(f"  ✓ Instância {inst_id} ATIVA (GPU: {gpu_usage}%, CPU: {cpu_usage}%) - mantendo")
                        else:
                            # IDLE - verificar grace period antes de pausar
                            start_date = inst.get("start_date")
                            running_minutes = 0
                            if start_date:
                                try:
                                    running_minutes = (time.time() - float(start_date)) / 60
                                except:
                                    running_minutes = 0

                            if running_minutes > GRACE_PERIOD_MINUTES:
                                logger.warning(f"  ⚠ Instância {inst_id} IDLE (GPU: {gpu_usage}%, CPU: {cpu_usage}%) há {running_minutes:.1f} min - PAUSANDO")
                                try:
                                    self.vast_service.pause_instance(inst_id)
                                    logger.info(f"  ✓ Instância {inst_id} pausada (será destruída após {PAUSED_DESTROY_HOURS}h)")
                                except Exception as e:
                                    logger.error(f"  Erro ao pausar {inst_id}: {e}")
                            else:
                                logger.info(f"  Instância {inst_id} idle mas nova ({running_minutes:.1f} min) - grace period ({GRACE_PERIOD_MINUTES} min)")

                    except subprocess.TimeoutExpired:
                        logger.warning(f"  Timeout SSH ao verificar {inst_id} - instância ainda inicializando, mantendo")
                    except Exception as e:
                        logger.error(f"  Erro ao verificar {inst_id}: {e}")

                # === Instâncias em estados problemáticos ===
                elif status in ['loading', 'created', 'unknown', None]:
                    start_date = inst.get('start_date')
                    stuck_minutes = 999

                    if start_date:
                        try:
                            stuck_seconds = time.time() - float(start_date)
                            stuck_minutes = stuck_seconds / 60
                        except:
                            stuck_minutes = 999

                    if stuck_minutes > GRACE_PERIOD_MINUTES:
                        logger.warning(f"Destruindo instância '{status}' há {stuck_minutes:.1f} min: {inst_id} ({gpu})")
                        if inst_label:
                            logger.info(f"  Label: {inst_label}")
                        try:
                            self.vast_service.destroy_instance(inst_id)
                            logger.info(f"✓ Instância {inst_id} destruída (estado: {status})")
                        except Exception as e:
                            logger.error(f"Erro ao destruir {inst_id}: {e}")
                    else:
                        logger.debug(f"Instância {inst_id} em '{status}' há {stuck_minutes:.1f} min - grace period")

        except Exception as e:
            logger.error(f"Erro ao verificar instâncias Vast.ai não rastreadas: {e}")

    def _check_tensordock_instances(self):
        """
        Verifica instâncias no TensorDock e destrói as ociosas.
        """
        import requests
        
        try:
            logger.info("Verificando instâncias TensorDock...")
            
            # Listar VMs do TensorDock
            url = "https://marketplace.tensordock.com/api/v0/client/list"
            resp = requests.post(
                url,
                data={
                    "api_key": self.tensordock_auth_id,
                    "api_token": self.tensordock_api_token
                },
                timeout=30
            )
            
            if resp.status_code != 200:
                logger.error(f"Erro ao listar VMs TensorDock: {resp.status_code}")
                return
                
            data = resp.json()
            vms = data.get('virtualmachines', {})
            
            if not vms:
                logger.debug("Nenhuma VM TensorDock encontrada")
                return
                
            logger.info(f"Encontradas {len(vms)} VMs no TensorDock")
            
            for vm_id, vm_info in vms.items():
                status = vm_info.get('status', 'unknown')
                gpu = vm_info.get('gpu_model', 'Unknown')
                cost = vm_info.get('price_per_hour', 0)
                
                # Destruir VMs paradas (stopped) ou com erro
                if status in ['stopped', 'error', 'failed']:
                    logger.warning(f"Destruindo VM TensorDock '{status}': {vm_id} ({gpu}) - ${cost}/hr")
                    try:
                        delete_url = "https://marketplace.tensordock.com/api/v0/client/delete"
                        del_resp = requests.post(
                            delete_url,
                            data={
                                "api_key": self.tensordock_auth_id,
                                "api_token": self.tensordock_api_token,
                                "server": vm_id
                            },
                            timeout=30
                        )
                        if del_resp.status_code == 200:
                            logger.info(f"✓ VM TensorDock {vm_id} destruída")
                        else:
                            logger.error(f"Erro ao destruir VM TensorDock {vm_id}: {del_resp.text}")
                    except Exception as e:
                        logger.error(f"Erro ao destruir VM TensorDock {vm_id}: {e}")
                        
                elif status == 'running':
                    # Para VMs running, verificar uso de GPU (se possível via API)
                    # TensorDock não fornece uso de GPU via API, então apenas logar
                    logger.debug(f"VM TensorDock running: {vm_id} ({gpu}) - ${cost}/hr")
                    
        except Exception as e:
            logger.error(f"Erro ao verificar instâncias TensorDock: {e}")

    def _check_gcp_instances(self):
        """
        Verifica instâncias no GCP e destrói as ociosas.
        """
        try:
            from google.oauth2 import service_account
            from googleapiclient import discovery
            
            logger.info("Verificando instâncias GCP...")
            
            # Criar credenciais
            credentials = service_account.Credentials.from_service_account_info(
                self.gcp_credentials,
                scopes=['https://www.googleapis.com/auth/compute']
            )
            
            # Criar cliente Compute
            compute = discovery.build('compute', 'v1', credentials=credentials)
            
            # Listar todas as zonas e instâncias
            zones_result = compute.zones().list(project=self.gcp_project_id).execute()
            zones = [z['name'] for z in zones_result.get('items', [])]
            
            total_instances = 0
            for zone in zones:
                try:
                    result = compute.instances().list(project=self.gcp_project_id, zone=zone).execute()
                    instances = result.get('items', [])
                    
                    for inst in instances:
                        total_instances += 1
                        name = inst.get('name')
                        status = inst.get('status')  # RUNNING, STOPPED, TERMINATED, etc.
                        machine_type = inst.get('machineType', '').split('/')[-1]
                        
                        # Destruir instâncias paradas ou terminadas
                        if status in ['STOPPED', 'TERMINATED', 'SUSPENDED']:
                            logger.warning(f"Destruindo instância GCP '{status}': {name} ({machine_type}) em {zone}")
                            try:
                                compute.instances().delete(
                                    project=self.gcp_project_id,
                                    zone=zone,
                                    instance=name
                                ).execute()
                                logger.info(f"✓ Instância GCP {name} destruída")
                            except Exception as e:
                                logger.error(f"Erro ao destruir instância GCP {name}: {e}")
                                
                        elif status == 'RUNNING':
                            logger.debug(f"Instância GCP running: {name} ({machine_type}) em {zone}")
                            
                except Exception as e:
                    logger.debug(f"Erro ao listar instâncias na zona {zone}: {e}")
                    
            if total_instances > 0:
                logger.info(f"Verificadas {total_instances} instâncias GCP")
            else:
                logger.debug("Nenhuma instância GCP encontrada")
                
        except ImportError:
            logger.warning("google-cloud-compute não instalado - monitoramento GCP desabilitado")
        except Exception as e:
            logger.error(f"Erro ao verificar instâncias GCP: {e}")

    def _check_instance(self, db, instance: InstanceStatus):
        """
        Verifica uma instância e aplica política de hibernação.

        Args:
            db: Sessão do banco de dados
            instance: Instância a verificar
        """
        now = datetime.utcnow()

        # 1. Verificar se deve hibernar (ociosa > threshold)
        if instance.status == "idle":
            idle_duration = (now - instance.idle_since).total_seconds() / 60  # minutos

            if idle_duration >= instance.pause_after_minutes:
                logger.info(f"Instância {instance.instance_id} ociosa por {idle_duration:.1f} min - hibernando...")
                self._hibernate_instance(db, instance)
                return

        # 2. Verificar se deve deletar instância hibernada
        if instance.status == "hibernated" and instance.hibernated_at:
            hibernated_duration = (now - instance.hibernated_at).total_seconds() / 60

            if hibernated_duration >= instance.delete_after_minutes:
                logger.info(f"Instância {instance.instance_id} hibernada por {hibernated_duration:.1f} min - marcando como deleted...")
                self._mark_instance_deleted(db, instance)
                return

        # 3. Verificar heartbeat - se não recebe status há muito tempo, tentar recovery
        if instance.last_heartbeat:
            heartbeat_age = (now - instance.last_heartbeat).total_seconds() / 60

            if heartbeat_age > 5 and instance.status == "running":  # 5 min sem heartbeat
                logger.warning(f"Instância {instance.instance_id} sem heartbeat há {heartbeat_age:.1f} min")

                # Tentar verificar se SSH ainda funciona
                if instance.ssh_host and instance.ssh_port:
                    ssh_works = self._verify_ssh_connection(
                        instance.ssh_host, instance.ssh_port
                    )

                    if ssh_works:
                        # SSH funciona, pode ser problema só do agent
                        logger.info(f"Instância {instance.instance_id} SSH OK, apenas heartbeat perdido")
                        instance.status = "running"  # Manter running
                        # Registrar warning
                        event = HibernationEvent(
                            instance_id=instance.instance_id,
                            event_type="heartbeat_lost",
                            reason=f"Heartbeat perdido há {heartbeat_age:.1f}min mas SSH OK"
                        )
                        db.add(event)
                    else:
                        # SSH não funciona - instância pode estar morta
                        logger.error(f"Instância {instance.instance_id} SSH FALHOU - tentando recovery")
                        instance.status = "unknown"

                        # Tentar auto-recovery se configurado
                        if instance.auto_recovery_enabled:
                            self._attempt_instance_recovery(db, instance)
                else:
                    instance.status = "unknown"

                db.commit()

    def _verify_ssh_connection(self, ssh_host: str, ssh_port: int, timeout: int = 10) -> bool:
        """Verifica se SSH está funcionando com comando real"""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", f"ConnectTimeout={timeout}",
                    "-o", "BatchMode=yes",
                    "-p", str(ssh_port),
                    f"root@{ssh_host}",
                    "echo SSH_OK"
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )
            return result.returncode == 0 and "SSH_OK" in result.stdout
        except Exception as e:
            logger.debug(f"SSH verification failed: {e}")
            return False

    def _attempt_instance_recovery(self, db, instance: InstanceStatus):
        """
        Tenta recuperar uma instância que perdeu conectividade.

        Fluxo:
        1. Verificar status na Vast.ai
        2. Se pausada -> tentar resume
        3. Se não existe ou erro -> provisionar nova e restaurar snapshot
        """
        import threading

        logger.info(f"[Recovery] Tentando recuperar instância {instance.instance_id}")

        # Registrar tentativa
        event = HibernationEvent(
            instance_id=instance.instance_id,
            event_type="recovery_attempt",
            reason="Heartbeat e SSH falharam"
        )
        db.add(event)
        db.commit()

        def recovery_task():
            """Executa recovery em background"""
            try:
                # 1. Verificar status na Vast.ai
                vast_status = None
                if instance.vast_instance_id:
                    try:
                        vast_status = self.vast_service.get_instance_status(instance.vast_instance_id)
                    except Exception as e:
                        logger.warning(f"[Recovery] Falha ao obter status Vast.ai: {e}")

                actual_status = vast_status.get("actual_status") if vast_status else None

                # 2. Decidir ação baseado no status
                if actual_status == "paused":
                    # Tentar resume
                    logger.info(f"[Recovery] Instância pausada, tentando resume...")
                    success = self.vast_service.resume_instance(instance.vast_instance_id)

                    if success:
                        # Aguardar SSH voltar
                        for _ in range(30):  # 60 segundos max
                            time.sleep(2)
                            if self._verify_ssh_connection(instance.ssh_host, instance.ssh_port):
                                logger.info(f"[Recovery] Resume bem-sucedido!")
                                self._update_recovery_status(instance.instance_id, "recovered", "Resume OK")
                                return

                    logger.warning(f"[Recovery] Resume falhou, tentando nova GPU...")

                # 3. Provisionar nova GPU com failover
                if instance.last_snapshot_id:
                    logger.info(f"[Recovery] Provisionando nova GPU com snapshot {instance.last_snapshot_id}")

                    # Usar wake_instance_with_failover
                    result = self.wake_instance_with_failover(
                        instance_id=instance.instance_id,
                        gpu_type=instance.gpu_type,
                        max_price=1.0,
                        parallel_backup=True,
                    )

                    if result.get("success"):
                        logger.info(f"[Recovery] Nova GPU provisionada: {result}")
                        self._update_recovery_status(
                            instance.instance_id,
                            "recovered",
                            f"Nova GPU via {result.get('method')}"
                        )
                    else:
                        logger.error(f"[Recovery] Falha ao provisionar nova GPU")
                        self._update_recovery_status(
                            instance.instance_id,
                            "failed",
                            result.get("error", "Provisioning failed")
                        )
                else:
                    logger.error(f"[Recovery] Sem snapshot para restaurar")
                    self._update_recovery_status(
                        instance.instance_id,
                        "failed",
                        "No snapshot available"
                    )

            except Exception as e:
                logger.error(f"[Recovery] Erro: {e}", exc_info=True)
                self._update_recovery_status(instance.instance_id, "failed", str(e))

        # Executar em thread separada para não bloquear o loop principal
        thread = threading.Thread(target=recovery_task, daemon=True)
        thread.start()

        logger.info(f"[Recovery] Task iniciada em background para {instance.instance_id}")

    def _update_recovery_status(self, instance_id: str, status: str, reason: str):
        """Atualiza status após tentativa de recovery"""
        db = SessionLocal()
        try:
            instance = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()

            if instance:
                if status == "recovered":
                    instance.status = "running"
                else:
                    instance.status = "failed"

                event = HibernationEvent(
                    instance_id=instance_id,
                    event_type=f"recovery_{status}",
                    reason=reason
                )
                db.add(event)
                db.commit()

                logger.info(f"[Recovery] {instance_id}: {status} - {reason}")
        except Exception as e:
            logger.error(f"[Recovery] Falha ao atualizar status: {e}")
            db.rollback()
        finally:
            db.close()

    def _hibernate_instance(self, db, instance: InstanceStatus):
        """
        Hiberna uma instância (snapshot + destroy).

        Args:
            db: Sessão do banco de dados
            instance: Instância a hibernar
        """
        try:
            logger.info(f"=== Hibernando instância {instance.instance_id} ===")

            # 1. Criar snapshot
            logger.info(f"  [1/3] Criando snapshot...")
            snapshot_info = self.snapshot_service.create_snapshot(
                instance_id=instance.instance_id,
                ssh_host=instance.ssh_host,
                ssh_port=instance.ssh_port,
                workspace_path="/workspace",
                snapshot_name=f"{instance.instance_id}_hibernate_{int(time.time())}"
            )

            snapshot_id = snapshot_info['snapshot_id']
            logger.info(f"  ✓ Snapshot criado: {snapshot_id}")

            # 2. Destruir instância vast.ai
            if instance.vast_instance_id:
                logger.info(f"  [2/3] Destruindo instância vast.ai {instance.vast_instance_id}...")
                success = self.vast_service.destroy_instance(instance.vast_instance_id)

                if success:
                    logger.info(f"  ✓ Instância vast.ai destruída")
                else:
                    logger.warning(f"  ⚠ Falha ao destruir instância vast.ai (pode já estar destruída)")

            # 3. Atualizar status no DB
            logger.info(f"  [3/3] Atualizando status no banco...")
            instance.status = "hibernated"
            instance.hibernated_at = datetime.utcnow()
            instance.snapshot_id = snapshot_id
            instance.last_snapshot_id = snapshot_id
            
            # Parar tracking de uso
            usage_service = UsageService(db)
            usage_service.stop_usage(instance.instance_id)
            
            # Calcular economia: horas desde idle × preço/hora
            idle_hours = 0.0
            savings_usd = 0.0
            dph_total = 0.0
            
            if instance.idle_since:
                idle_duration = datetime.utcnow() - instance.idle_since
                idle_hours = idle_duration.total_seconds() / 3600
                
                # Buscar preço da instância (estimativa se não disponível)
                try:
                    vast_info = self.vast_service.get_instance_status(instance.vast_instance_id)
                    if vast_info and 'dph_total' in vast_info:
                        dph_total = vast_info['dph_total']
                except:
                    # Estimativa baseada no tipo de GPU
                    gpu_prices = {
                        'RTX 4090': 0.40, 'RTX 3090': 0.25, 'RTX 3080': 0.20,
                        'A100': 1.50, 'H100': 3.00, 'A6000': 0.60
                    }
                    dph_total = gpu_prices.get(instance.gpu_type, 0.30)
                
                savings_usd = idle_hours * dph_total
            
            instance.idle_since = None

            # Registrar evento com economia
            event = HibernationEvent(
                instance_id=instance.instance_id,
                event_type="hibernated",
                gpu_utilization=instance.gpu_utilization,
                snapshot_id=snapshot_id,
                reason=f"GPU ociosa por {instance.pause_after_minutes} minutos",
                dph_total=dph_total,
                idle_hours=idle_hours,
                savings_usd=savings_usd
            )
            db.add(event)
            db.commit()

            logger.info(f"=== Hibernação concluída: {instance.instance_id} ===")

        except Exception as e:
            logger.error(f"Erro ao hibernar instância {instance.instance_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def _mark_instance_deleted(self, db, instance: InstanceStatus):
        """
        Marca instância como deletada (mantém snapshot no R2).

        Args:
            db: Sessão do banco de dados
            instance: Instância a marcar como deletada
        """
        try:
            logger.info(f"Marcando instância {instance.instance_id} como deleted")

            instance.status = "deleted"

            # Registrar evento
            event = HibernationEvent(
                instance_id=instance.instance_id,
                event_type="deleted",
                snapshot_id=instance.snapshot_id,
                reason=f"Instância hibernada por {instance.delete_after_minutes} minutos"
            )
            db.add(event)
            db.commit()

            logger.info(f"✓ Instância {instance.instance_id} marcada como deleted (snapshot mantido)")

        except Exception as e:
            logger.error(f"Erro ao marcar instância como deleted: {e}")
            db.rollback()

    def wake_instance(
        self,
        instance_id: str,
        gpu_type: Optional[str] = None,
        region: Optional[str] = None,
        max_price: float = 1.0
    ) -> Dict:
        """
        Acorda uma instância hibernada (create + restore).

        Args:
            instance_id: ID da instância
            gpu_type: Tipo de GPU desejado (ex: "RTX 3090")
            region: Região desejada (ex: "EU")
            max_price: Preço máximo por hora

        Returns:
            {
                'success': bool,
                'instance_id': str,
                'vast_instance_id': int,
                'ssh_host': str,
                'ssh_port': int,
                'snapshot_restored': bool,
                'time_taken': float
            }
        """
        db = SessionLocal()
        try:
            start_time = time.time()

            # Buscar instância no DB
            instance = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()

            if not instance:
                raise ValueError(f"Instância {instance_id} não encontrada")

            if instance.status not in ["hibernated", "deleted"]:
                raise ValueError(f"Instância {instance_id} não está hibernada (status: {instance.status})")

            if not instance.snapshot_id:
                raise ValueError(f"Instância {instance_id} não possui snapshot")

            logger.info(f"=== Acordando instância {instance_id} ===")

            # Usar configurações salvas se não especificadas
            gpu_type = gpu_type or instance.gpu_type or "RTX 3090"
            region = region or instance.region

            # 1. Buscar ofertas disponíveis
            logger.info(f"  [1/4] Buscando ofertas {gpu_type} em {region}...")
            offers = self.vast_service.search_offers(
                gpu_name=gpu_type,
                region=region,
                max_price=max_price,
                limit=10
            )

            if not offers:
                raise Exception(f"Nenhuma oferta disponível para {gpu_type} em {region}")

            logger.info(f"  ✓ Encontradas {len(offers)} ofertas")

            # 2. Criar instância
            logger.info(f"  [2/4] Criando instância vast.ai...")
            offer_id = offers[0]['id']

            new_vast_id = self.vast_service.create_instance(
                offer_id=offer_id,
                image="nvidia/cuda:12.0.0-devel-ubuntu22.04",
                disk=100
            )

            if not new_vast_id:
                raise Exception("Falha ao criar instância vast.ai")

            logger.info(f"  ✓ Instância criada: {new_vast_id}")

            # 3. Aguardar instância ficar pronta
            logger.info(f"  [3/4] Aguardando instância ficar pronta...")
            max_wait = 180  # 3 minutos
            wait_start = time.time()

            while time.time() - wait_start < max_wait:
                status = self.vast_service.get_instance_status(new_vast_id)

                if status.get('status') == 'running' and status.get('ssh_host'):
                    ssh_host = status['ssh_host']
                    ssh_port = status['ssh_port']
                    logger.info(f"  ✓ Instância pronta: {ssh_host}:{ssh_port}")
                    break

                time.sleep(5)
            else:
                raise Exception(f"Timeout aguardando instância ficar pronta")

            # 4. Restaurar snapshot
            logger.info(f"  [4/4] Restaurando snapshot {instance.snapshot_id}...")
            restore_info = self.snapshot_service.restore_snapshot(
                snapshot_id=instance.snapshot_id,
                ssh_host=ssh_host,
                ssh_port=ssh_port,
                workspace_path="/workspace"
            )

            logger.info(f"  ✓ Snapshot restaurado em {restore_info['total_time']:.1f}s")

            # 5. Atualizar DB
            instance.status = "running"
            instance.vast_instance_id = new_vast_id
            instance.ssh_host = ssh_host
            instance.ssh_port = ssh_port
            instance.woke_at = datetime.utcnow()
            instance.hibernated_at = None

            # Iniciar tracking de uso
            usage_service = UsageService(db)
            usage_service.start_usage(
                user_id=instance.user_id,
                instance_id=instance.instance_id,
                gpu_type=instance.gpu_type
            )

            # Registrar evento
            event = HibernationEvent(
                instance_id=instance_id,
                event_type="woke_up",
                snapshot_id=instance.snapshot_id,
                reason="Wake manual via API"
            )
            db.add(event)
            db.commit()

            total_time = time.time() - start_time

            logger.info(f"=== Instância {instance_id} acordada em {total_time:.1f}s ===")

            return {
                'success': True,
                'instance_id': instance_id,
                'vast_instance_id': new_vast_id,
                'ssh_host': ssh_host,
                'ssh_port': ssh_port,
                'snapshot_restored': True,
                'time_taken': total_time
            }

        except Exception as e:
            logger.error(f"Erro ao acordar instância {instance_id}: {e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()

    def wake_instance_with_failover(
        self,
        instance_id: str,
        gpu_type: Optional[str] = None,
        region: Optional[str] = None,
        max_price: float = 1.0,
        parallel_backup: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> Dict:
        """
        Acorda uma instância hibernada com failover robusto.

        Se a primeira GPU não conseguir SSH funcionando, automaticamente
        provisiona uma segunda em paralelo e faz race entre elas.

        Este é o método recomendado para produção.

        Args:
            instance_id: ID da instância hibernada
            gpu_type: Tipo de GPU desejado
            region: Região desejada
            max_price: Preço máximo por hora
            parallel_backup: Se True, já lança backup em paralelo
            progress_callback: Callback para updates de progresso

        Returns:
            {
                'success': bool,
                'instance_id': str,
                'vast_instance_id': int,
                'ssh_host': str,
                'ssh_port': int,
                'snapshot_restored': bool,
                'time_taken': float,
                'method': str,  # 'primary' or 'fallback'
            }
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import subprocess

        db = SessionLocal()
        try:
            start_time = time.time()

            # Buscar instância no DB
            instance = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()

            if not instance:
                raise ValueError(f"Instância {instance_id} não encontrada")

            if instance.status not in ["hibernated", "deleted"]:
                raise ValueError(f"Instância {instance_id} não está hibernada (status: {instance.status})")

            if not instance.snapshot_id:
                raise ValueError(f"Instância {instance_id} não possui snapshot")

            def report_progress(status: str, message: str, progress: int = 0):
                if progress_callback:
                    progress_callback(status, message, progress)
                logger.info(f"[HibernationWake] {status}: {message}")

            report_progress("starting", f"Acordando instância {instance_id}...", 5)

            # Usar configurações salvas se não especificadas
            gpu_type = gpu_type or instance.gpu_type or "RTX 3090"
            region = region or instance.region

            # 1. Buscar ofertas
            report_progress("searching", f"Buscando ofertas {gpu_type}...", 10)
            offers = self.vast_service.search_offers(
                gpu_name=gpu_type,
                region=region,
                max_price=max_price,
                limit=10
            )

            if not offers:
                raise Exception(f"Nenhuma oferta disponível para {gpu_type}")

            report_progress("found", f"Encontradas {len(offers)} ofertas", 15)

            # 2. Criar instâncias em paralelo (principal + backup)
            def create_and_wait_ssh(offer_index: int, label: str) -> Dict:
                """Cria instância e aguarda SSH funcionar"""
                offer = offers[offer_index]
                offer_id = offer['id']

                logger.info(f"[{label}] Criando instância com oferta {offer_id}...")

                vast_id = self.vast_service.create_instance(
                    offer_id=offer_id,
                    image="nvidia/cuda:12.0.0-devel-ubuntu22.04",
                    disk=100
                )

                if not vast_id:
                    return {"success": False, "error": "Falha ao criar instância"}

                logger.info(f"[{label}] Instância criada: {vast_id}")

                # Aguardar SSH funcionar
                max_wait = 180
                wait_start = time.time()

                while time.time() - wait_start < max_wait:
                    try:
                        status = self.vast_service.get_instance_status(vast_id)

                        if status.get('status') == 'running' and status.get('ssh_host'):
                            ssh_host = status['ssh_host']
                            ssh_port = status['ssh_port']

                            # Verificar SSH com comando real
                            result = subprocess.run(
                                [
                                    "ssh",
                                    "-o", "StrictHostKeyChecking=no",
                                    "-o", "UserKnownHostsFile=/dev/null",
                                    "-o", "ConnectTimeout=10",
                                    "-o", "BatchMode=yes",
                                    "-p", str(ssh_port),
                                    f"root@{ssh_host}",
                                    "echo SSH_OK"
                                ],
                                capture_output=True,
                                text=True,
                                timeout=15,
                            )

                            if result.returncode == 0 and "SSH_OK" in result.stdout:
                                logger.info(f"[{label}] SSH funcionando em {ssh_host}:{ssh_port}")
                                return {
                                    "success": True,
                                    "vast_id": vast_id,
                                    "ssh_host": ssh_host,
                                    "ssh_port": ssh_port,
                                    "label": label,
                                }
                    except Exception as e:
                        logger.debug(f"[{label}] Aguardando SSH: {e}")

                    time.sleep(5)

                return {"success": False, "vast_id": vast_id, "error": "Timeout SSH", "label": label}

            # Lançar principal (e backup se paralelo)
            report_progress("provisioning", "Provisionando GPU(s)...", 20)

            futures = {}
            with ThreadPoolExecutor(max_workers=2) as executor:
                # Sempre lançar principal
                futures["primary"] = executor.submit(create_and_wait_ssh, 0, "primary")

                # Lançar backup em paralelo se configurado e houver mais ofertas
                if parallel_backup and len(offers) > 1:
                    futures["backup"] = executor.submit(create_and_wait_ssh, 1, "backup")

                # Aguardar primeiro sucesso
                winner = None
                loser_vast_ids = []

                for future in as_completed(futures.values()):
                    result = future.result()

                    if result.get("success"):
                        if winner is None:
                            winner = result
                            report_progress("ready", f"{result['label']} pronto!", 80)
                        else:
                            # Já temos vencedor, destruir este
                            loser_vast_ids.append(result.get("vast_id"))
                    else:
                        # Falhou, destruir se criou
                        if result.get("vast_id"):
                            loser_vast_ids.append(result["vast_id"])

            # 3. Se não temos vencedor, tentar sequencial com outras ofertas
            if not winner and len(offers) > 2:
                report_progress("retrying", "Tentando ofertas alternativas...", 60)

                for i in range(2, min(len(offers), 5)):
                    result = create_and_wait_ssh(i, f"retry_{i}")
                    if result.get("success"):
                        winner = result
                        break
                    elif result.get("vast_id"):
                        loser_vast_ids.append(result["vast_id"])

            # 4. Limpar perdedores
            for vast_id in loser_vast_ids:
                try:
                    logger.info(f"[Cleanup] Destruindo instância perdedora {vast_id}")
                    self.vast_service.destroy_instance(vast_id)
                except Exception as e:
                    logger.warning(f"[Cleanup] Falha ao destruir {vast_id}: {e}")

            if not winner:
                raise Exception("Todas as tentativas de provisionar GPU falharam")

            # 5. Restaurar snapshot no vencedor
            report_progress("restoring", f"Restaurando snapshot...", 85)

            restore_info = self.snapshot_service.restore_snapshot(
                snapshot_id=instance.snapshot_id,
                ssh_host=winner["ssh_host"],
                ssh_port=winner["ssh_port"],
                workspace_path="/workspace"
            )

            report_progress("restored", f"Snapshot restaurado em {restore_info['total_time']:.1f}s", 95)

            # 6. Atualizar DB
            instance.status = "running"
            instance.vast_instance_id = winner["vast_id"]
            instance.ssh_host = winner["ssh_host"]
            instance.ssh_port = winner["ssh_port"]
            instance.woke_at = datetime.utcnow()
            instance.hibernated_at = None

            # Iniciar tracking de uso
            usage_service = UsageService(db)
            usage_service.start_usage(
                user_id=instance.user_id,
                instance_id=instance.instance_id,
                gpu_type=instance.gpu_type
            )

            # Registrar evento
            event = HibernationEvent(
                instance_id=instance_id,
                event_type="woke_up",
                snapshot_id=instance.snapshot_id,
                reason=f"Wake with failover via {winner['label']}"
            )
            db.add(event)
            db.commit()

            total_time = time.time() - start_time
            report_progress("complete", f"Instância acordada em {total_time:.1f}s", 100)

            return {
                'success': True,
                'instance_id': instance_id,
                'vast_instance_id': winner["vast_id"],
                'ssh_host': winner["ssh_host"],
                'ssh_port': winner["ssh_port"],
                'snapshot_restored': True,
                'time_taken': total_time,
                'method': winner["label"],
            }

        except Exception as e:
            logger.error(f"Erro ao acordar instância com failover {instance_id}: {e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()

    def update_instance_status(
        self,
        instance_id: str,
        gpu_utilization: float,
        gpu_threshold: float = 5.0
    ):
        """
        Atualiza status de uma instância baseado em heartbeat do DumontAgent.

        Args:
            instance_id: ID da instância
            gpu_utilization: Utilização da GPU em %
            gpu_threshold: Threshold para considerar ociosa
        """
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            instance = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()

            if not instance:
                # Criar nova instância no DB
                logger.info(f"Nova instância detectada: {instance_id}")
                instance = InstanceStatus(
                    instance_id=instance_id,
                    user_id="unknown",  # Será atualizado depois
                    status="running",
                    gpu_utilization=gpu_utilization,
                    last_heartbeat=now,
                    last_activity=now
                )
                db.add(instance)
            else:
                # Atualizar instância existente
                instance.gpu_utilization = gpu_utilization
                instance.last_heartbeat = now

                # Determinar se está ociosa
                is_idle = gpu_utilization < instance.gpu_usage_threshold

                if is_idle:
                    if instance.status == "running":
                        # Primeira vez ociosa - marcar timestamp
                        instance.status = "idle"
                        instance.idle_since = now
                        logger.info(f"Instância {instance_id} ficou ociosa ({gpu_utilization}%)")

                        # Registrar evento
                        event = HibernationEvent(
                            instance_id=instance_id,
                            event_type="idle_detected",
                            gpu_utilization=gpu_utilization,
                            reason=f"GPU utilização < {instance.gpu_usage_threshold}%"
                        )
                        db.add(event)
                else:
                    if instance.status == "idle":
                        # Voltou a ser usada
                        instance.status = "running"
                        instance.idle_since = None
                        logger.info(f"Instância {instance_id} voltou a ser usada ({gpu_utilization}%)")

                    instance.last_activity = now

            db.commit()

        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
            db.rollback()
        finally:
            db.close()

    def get_all_instance_status(self) -> List[Dict]:
        """Retorna status de todas as instâncias rastreadas."""
        db = SessionLocal()
        try:
            instances = db.query(InstanceStatus).all()
            result = []
            for inst in instances:
                result.append({
                    "instance_id": inst.instance_id,
                    "status": inst.status,
                    "gpu_utilization": inst.gpu_utilization or 0,
                    "last_heartbeat": inst.last_heartbeat.isoformat() if inst.last_heartbeat else None,
                    "idle_since": inst.idle_since.isoformat() if inst.idle_since else None,
                    "will_hibernate_at": self._calculate_hibernate_time(inst),
                    "auto_hibernation_enabled": inst.auto_hibernation_enabled,
                })
            return result
        finally:
            db.close()

    def get_instance_status(self, instance_id: str) -> Optional[Dict]:
        """Retorna status de uma instância específica."""
        db = SessionLocal()
        try:
            inst = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()
            if not inst:
                return None
            return {
                "instance_id": inst.instance_id,
                "status": inst.status,
                "gpu_utilization": inst.gpu_utilization or 0,
                "last_heartbeat": inst.last_heartbeat.isoformat() if inst.last_heartbeat else None,
                "idle_since": inst.idle_since.isoformat() if inst.idle_since else None,
                "will_hibernate_at": self._calculate_hibernate_time(inst),
                "auto_hibernation_enabled": inst.auto_hibernation_enabled,
                "idle_timeout_seconds": inst.idle_timeout_seconds,
                "gpu_usage_threshold": inst.gpu_usage_threshold,
                "snapshot_id": inst.last_snapshot_id,
            }
        finally:
            db.close()

    def _calculate_hibernate_time(self, instance: InstanceStatus) -> Optional[str]:
        """Calcula quando a instância será hibernada."""
        if instance.status != "idle" or not instance.idle_since:
            return None
        hibernate_at = instance.idle_since + timedelta(seconds=instance.idle_timeout_seconds)
        return hibernate_at.isoformat()

    def extend_keep_alive(self, instance_id: str, minutes: int = 30) -> bool:
        """Estende o tempo antes de hibernar uma instância."""
        db = SessionLocal()
        try:
            inst = db.query(InstanceStatus).filter(
                InstanceStatus.instance_id == instance_id
            ).first()
            if not inst:
                return False
            
            # Resetar idle_since para agora + minutos extras
            inst.idle_since = datetime.utcnow() + timedelta(minutes=minutes)
            inst.status = "running"  # Temporariamente marcar como running
            db.commit()
            logger.info(f"Keep-alive estendido para {instance_id} por {minutes} minutos")
            return True
        except Exception as e:
            logger.error(f"Erro ao estender keep-alive: {e}")
            db.rollback()
            return False
        finally:
            db.close()


# Singleton global
_auto_hibernation_manager: Optional[AutoHibernationManager] = None


def get_auto_hibernation_manager() -> Optional[AutoHibernationManager]:
    """Retorna a instância global do AutoHibernationManager."""
    return _auto_hibernation_manager


def init_auto_hibernation_manager(
    vast_api_key: str,
    r2_endpoint: str,
    r2_bucket: str,
    check_interval: int = 30
) -> AutoHibernationManager:
    """Inicializa e retorna o AutoHibernationManager global."""
    global _auto_hibernation_manager
    if _auto_hibernation_manager is None:
        _auto_hibernation_manager = AutoHibernationManager(
            vast_api_key=vast_api_key,
            r2_endpoint=r2_endpoint,
            r2_bucket=r2_bucket,
            check_interval=check_interval
        )
    return _auto_hibernation_manager
