"""
Cost Optimizer Service - DumontCloud

Daemon que monitora e otimiza custos de GPU em múltiplos provedores:
- Pausa automaticamente máquinas com <10% GPU utilization
- Deleta automaticamente máquinas idle por >24h
- Suporta: Vast.ai, TensorDock, GCP

Autor: DumontCloud Team
Data: 2024-12-20
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cost_optimizer')


class InstanceStatus(Enum):
    """Status possíveis de uma instância"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class ProviderType(Enum):
    """Tipos de provedores suportados"""
    VAST_AI = "vast.ai"
    TENSOR_DOCK = "tensordock"
    GCP = "gcp"


@dataclass
class InstanceMetrics:
    """Métricas de utilização de instância (GPU + CPU)"""
    gpu_utilization: float = 0.0  # 0-100% (0 se não tiver GPU)
    cpu_utilization: float = 0.0  # 0-100%
    memory_used: float      # GB
    memory_total: float     # GB
    temperature: float      # Celsius
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def memory_utilization(self) -> float:
        """Retorna % de memória utilizada"""
        if self.memory_total == 0:
            return 0
        return (self.memory_used / self.memory_total) * 100


@dataclass
class Instance:
    """Representa uma instância de GPU em qualquer provider"""
    id: str
    provider: ProviderType
    name: str
    gpu_name: str
    status: InstanceStatus
    ip_address: Optional[str] = None
    hourly_cost: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    metrics: Optional[GpuMetrics] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def idle_hours(self) -> float:
        """Horas desde última atividade"""
        delta = datetime.now() - self.last_activity
        return delta.total_seconds() / 3600


class GpuProvider(ABC):
    """Interface abstrata para provedores de GPU"""
    
    @abstractmethod
    async def list_instances(self) -> List[Instance]:
        """Lista todas as instâncias ativas"""
        pass
    
    @abstractmethod
    async def get_gpu_metrics(self, instance: Instance) -> Optional[GpuMetrics]:
        """Obtém métricas de GPU de uma instância"""
        pass
    
    @abstractmethod
    async def pause_instance(self, instance: Instance) -> bool:
        """Pausa uma instância (mantém dados)"""
        pass
    
    @abstractmethod
    async def resume_instance(self, instance: Instance) -> bool:
        """Resume uma instância pausada"""
        pass
    
    @abstractmethod
    async def delete_instance(self, instance: Instance) -> bool:
        """Deleta permanentemente uma instância"""
        pass


class VastAiProvider(GpuProvider):
    """Implementação para Vast.ai"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://console.vast.ai/api/v0"
    
    async def list_instances(self) -> List[Instance]:
        """Lista instâncias no Vast.ai"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with session.get(
                f"{self.api_url}/instances",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Vast.ai API error: {resp.status}")
                    return []
                
                data = await resp.json()
                instances = []
                
                for inst in data.get("instances", []):
                    status = InstanceStatus.RUNNING
                    if inst.get("actual_status") == "stopped":
                        status = InstanceStatus.STOPPED
                    elif inst.get("actual_status") == "paused":
                        status = InstanceStatus.PAUSED
                    
                    instances.append(Instance(
                        id=str(inst["id"]),
                        provider=ProviderType.VAST_AI,
                        name=inst.get("label", f"vast-{inst['id']}"),
                        gpu_name=inst.get("gpu_name", "unknown"),
                        status=status,
                        ip_address=inst.get("public_ipaddr"),
                        hourly_cost=inst.get("dph_total", 0),
                        created_at=datetime.fromtimestamp(inst.get("start_date", 0)),
                        last_activity=datetime.now(),  # Será atualizado com métricas
                        metadata=inst
                    ))
                
                return instances
    
    async def get_gpu_metrics(self, instance: Instance) -> Optional[GpuMetrics]:
        """Obtém métricas via SSH nvidia-smi"""
        if not instance.ip_address:
            return None
        
        try:
            # Executa nvidia-smi via SSH
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
                f"root@{instance.ip_address}",
                "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            
            if proc.returncode == 0:
                parts = stdout.decode().strip().split(",")
                if len(parts) >= 4:
                    return GpuMetrics(
                        gpu_utilization=float(parts[0].strip()),
                        memory_used=float(parts[1].strip()) / 1024,  # MB to GB
                        memory_total=float(parts[2].strip()) / 1024,
                        temperature=float(parts[3].strip())
                    )
        except Exception as e:
            logger.warning(f"Failed to get metrics for {instance.id}: {e}")
        
        return None
    
    async def pause_instance(self, instance: Instance) -> bool:
        """Pausa instância no Vast.ai (stop)"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with session.put(
                f"{self.api_url}/instances/{instance.id}/",
                headers=headers,
                json={"state": "stopped"}
            ) as resp:
                success = resp.status == 200
                if success:
                    logger.info(f"Paused Vast.ai instance {instance.id}")
                return success
    
    async def resume_instance(self, instance: Instance) -> bool:
        """Resume instância no Vast.ai"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with session.put(
                f"{self.api_url}/instances/{instance.id}/",
                headers=headers,
                json={"state": "running"}
            ) as resp:
                success = resp.status == 200
                if success:
                    logger.info(f"Resumed Vast.ai instance {instance.id}")
                return success
    
    async def delete_instance(self, instance: Instance) -> bool:
        """Deleta instância no Vast.ai"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with session.delete(
                f"{self.api_url}/instances/{instance.id}/",
                headers=headers
            ) as resp:
                success = resp.status == 200
                if success:
                    logger.info(f"Deleted Vast.ai instance {instance.id}")
                return success


class TensorDockProvider(GpuProvider):
    """Implementação para TensorDock"""
    
    def __init__(self, api_key: str, api_token: str):
        self.api_key = api_key
        self.api_token = api_token
        self.api_url = "https://marketplace.tensordock.com/api/v0"
    
    async def list_instances(self) -> List[Instance]:
        """Lista VMs no TensorDock"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            params = {"api_key": self.api_key, "api_token": self.api_token}
            async with session.get(
                f"{self.api_url}/client/list",
                params=params
            ) as resp:
                if resp.status != 200:
                    logger.error(f"TensorDock API error: {resp.status}")
                    return []
                
                data = await resp.json()
                instances = []
                
                for vm_id, vm in data.get("virtualmachines", {}).items():
                    status = InstanceStatus.RUNNING
                    if vm.get("status") == "stopped":
                        status = InstanceStatus.STOPPED
                    
                    instances.append(Instance(
                        id=vm_id,
                        provider=ProviderType.TENSOR_DOCK,
                        name=vm.get("name", f"td-{vm_id}"),
                        gpu_name=vm.get("gpu_model", "unknown"),
                        status=status,
                        ip_address=vm.get("ip"),
                        hourly_cost=vm.get("cost_per_hour", 0),
                        metadata=vm
                    ))
                
                return instances
    
    async def get_gpu_metrics(self, instance: Instance) -> Optional[GpuMetrics]:
        """Obtém métricas via SSH"""
        if not instance.ip_address:
            return None
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
                f"user@{instance.ip_address}",
                "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            
            if proc.returncode == 0:
                parts = stdout.decode().strip().split(",")
                if len(parts) >= 4:
                    return GpuMetrics(
                        gpu_utilization=float(parts[0].strip()),
                        memory_used=float(parts[1].strip()) / 1024,
                        memory_total=float(parts[2].strip()) / 1024,
                        temperature=float(parts[3].strip())
                    )
        except Exception as e:
            logger.warning(f"Failed to get metrics for {instance.id}: {e}")
        
        return None
    
    async def pause_instance(self, instance: Instance) -> bool:
        """Para VM no TensorDock"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            params = {
                "api_key": self.api_key,
                "api_token": self.api_token,
                "server": instance.id
            }
            async with session.get(
                f"{self.api_url}/client/stop",
                params=params
            ) as resp:
                success = resp.status == 200
                if success:
                    logger.info(f"Stopped TensorDock VM {instance.id}")
                return success
    
    async def resume_instance(self, instance: Instance) -> bool:
        """Inicia VM no TensorDock"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            params = {
                "api_key": self.api_key,
                "api_token": self.api_token,
                "server": instance.id
            }
            async with session.get(
                f"{self.api_url}/client/start",
                params=params
            ) as resp:
                success = resp.status == 200
                if success:
                    logger.info(f"Started TensorDock VM {instance.id}")
                return success
    
    async def delete_instance(self, instance: Instance) -> bool:
        """Deleta VM no TensorDock"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            params = {
                "api_key": self.api_key,
                "api_token": self.api_token,
                "server": instance.id
            }
            async with session.get(
                f"{self.api_url}/client/delete",
                params=params
            ) as resp:
                success = resp.status == 200
                if success:
                    logger.info(f"Deleted TensorDock VM {instance.id}")
                return success


class GcpProvider(GpuProvider):
    """Implementação para Google Cloud Platform"""
    
    def __init__(self, project_id: str, zone: str = "us-central1-a"):
        self.project_id = project_id
        self.zone = zone
    
    async def list_instances(self) -> List[Instance]:
        """Lista VMs GPU no GCP"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gcloud", "compute", "instances", "list",
                f"--project={self.project_id}",
                "--filter=guestAccelerators:*",
                "--format=json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error("Failed to list GCP instances")
                return []
            
            data = json.loads(stdout.decode())
            instances = []
            
            for vm in data:
                status = InstanceStatus.RUNNING
                if vm.get("status") == "TERMINATED":
                    status = InstanceStatus.STOPPED
                elif vm.get("status") == "SUSPENDED":
                    status = InstanceStatus.PAUSED
                
                # Extrair info de GPU
                gpu_name = "unknown"
                accelerators = vm.get("guestAccelerators", [])
                if accelerators:
                    gpu_type = accelerators[0].get("acceleratorType", "")
                    gpu_name = gpu_type.split("/")[-1] if "/" in gpu_type else gpu_type
                
                # IP externo
                ip = None
                for iface in vm.get("networkInterfaces", []):
                    for access in iface.get("accessConfigs", []):
                        if "natIP" in access:
                            ip = access["natIP"]
                            break
                
                instances.append(Instance(
                    id=vm["name"],
                    provider=ProviderType.GCP,
                    name=vm["name"],
                    gpu_name=gpu_name,
                    status=status,
                    ip_address=ip,
                    metadata=vm
                ))
            
            return instances
        
        except Exception as e:
            logger.error(f"GCP list error: {e}")
            return []
    
    async def get_gpu_metrics(self, instance: Instance) -> Optional[GpuMetrics]:
        """Obtém métricas via SSH"""
        if not instance.ip_address:
            return None
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "gcloud", "compute", "ssh", instance.id,
                f"--project={self.project_id}",
                f"--zone={self.zone}",
                "--command=nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0:
                parts = stdout.decode().strip().split(",")
                if len(parts) >= 4:
                    return GpuMetrics(
                        gpu_utilization=float(parts[0].strip()),
                        memory_used=float(parts[1].strip()) / 1024,
                        memory_total=float(parts[2].strip()) / 1024,
                        temperature=float(parts[3].strip())
                    )
        except Exception as e:
            logger.warning(f"Failed to get GCP metrics: {e}")
        
        return None
    
    async def pause_instance(self, instance: Instance) -> bool:
        """Suspende VM no GCP"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gcloud", "compute", "instances", "suspend", instance.id,
                f"--project={self.project_id}",
                f"--zone={self.zone}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            success = proc.returncode == 0
            if success:
                logger.info(f"Suspended GCP instance {instance.id}")
            return success
        except Exception as e:
            logger.error(f"GCP suspend error: {e}")
            return False
    
    async def resume_instance(self, instance: Instance) -> bool:
        """Resume VM no GCP"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gcloud", "compute", "instances", "resume", instance.id,
                f"--project={self.project_id}",
                f"--zone={self.zone}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            success = proc.returncode == 0
            if success:
                logger.info(f"Resumed GCP instance {instance.id}")
            return success
        except Exception as e:
            logger.error(f"GCP resume error: {e}")
            return False
    
    async def delete_instance(self, instance: Instance) -> bool:
        """Deleta VM no GCP"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gcloud", "compute", "instances", "delete", instance.id,
                f"--project={self.project_id}",
                f"--zone={self.zone}",
                "--quiet",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            success = proc.returncode == 0
            if success:
                logger.info(f"Deleted GCP instance {instance.id}")
            return success
        except Exception as e:
            logger.error(f"GCP delete error: {e}")
            return False


@dataclass
class OptimizerConfig:
    """Configuração do Cost Optimizer"""
    # Thresholds
    pause_threshold_gpu: float = 10.0      # Pausar se GPU < 10%
    pause_threshold_cpu: float = 5.0       # Pausar se CPU < 5%      # Pausar se GPU < 10%
    pause_threshold_minutes: int = 5      # Por quanto tempo antes de pausar
    delete_threshold_hours: int = 24       # Deletar se idle > 24h
    
    # Intervalos
    check_interval_seconds: int = 30       # Checar a cada 1 minuto
    metrics_window_minutes: int = 5       # Janela de métricas para decisão
    
    # Proteções
    min_instance_age_hours: float = 1.0    # Não deletar instâncias novas
    protected_instances: List[str] = field(default_factory=list)  # IDs protegidos
    
    # Notificações
    notify_on_pause: bool = True
    notify_on_delete: bool = True
    webhook_url: Optional[str] = None


class CostOptimizer:
    """
    Daemon principal de otimização de custos.
    
    Monitora continuamente todas as instâncias GPU e:
    1. Pausa automaticamente instâncias com baixa utilização (<10% GPU por 30min)
    2. Deleta automaticamente instâncias idle por mais de 24h
    3. Envia notificações de ações tomadas
    """
    
    def __init__(self, config: Optional[OptimizerConfig] = None):
        self.config = config or OptimizerConfig()
        self.providers: Dict[ProviderType, GpuProvider] = {}
        self.metrics_history: Dict[str, List[GpuMetrics]] = {}  # instance_id -> metrics
        self.running = False
        self._last_activity: Dict[str, datetime] = {}
    
    def add_provider(self, provider_type: ProviderType, provider: GpuProvider):
        """Adiciona um provider ao optimizer"""
        self.providers[provider_type] = provider
        logger.info(f"Added provider: {provider_type.value}")
    
    async def _get_all_instances(self) -> List[Instance]:
        """Obtém todas as instâncias de todos os providers"""
        all_instances = []
        
        for provider_type, provider in self.providers.items():
            try:
                instances = await provider.list_instances()
                all_instances.extend(instances)
                logger.debug(f"Found {len(instances)} instances in {provider_type.value}")
            except Exception as e:
                logger.error(f"Error listing {provider_type.value}: {e}")
        
        return all_instances
    
    async def _update_metrics(self, instance: Instance) -> Optional[GpuMetrics]:
        """Atualiza métricas de uma instância"""
        provider = self.providers.get(instance.provider)
        if not provider:
            return None
        
        metrics = await provider.get_gpu_metrics(instance)
        
        if metrics:
            # Salvar no histórico
            if instance.id not in self.metrics_history:
                self.metrics_history[instance.id] = []
            
            self.metrics_history[instance.id].append(metrics)
            
            # Manter apenas últimos N minutos
            cutoff = datetime.now() - timedelta(minutes=self.config.metrics_window_minutes)
            self.metrics_history[instance.id] = [
                m for m in self.metrics_history[instance.id]
                if m.timestamp > cutoff
            ]
            
            # Atualizar última atividade se GPU > threshold
            if metrics.gpu_utilization > self.config.pause_threshold_gpu:
                self._last_activity[instance.id] = datetime.now()
        
        return metrics
    
    def _get_average_utilization(self, instance_id: str) -> Optional[float]:
        """Calcula utilização média de GPU na janela de tempo"""
        history = self.metrics_history.get(instance_id, [])
        if not history:
            return None
        
        return sum(m.gpu_utilization for m in history) / len(history)
    
    def _should_pause(self, instance: Instance) -> bool:
        """Verifica se instância deve ser pausada"""
        # Ignorar instâncias já pausadas/paradas
        if instance.status != InstanceStatus.RUNNING:
            return False
        
        # Ignorar instâncias protegidas
        if instance.id in self.config.protected_instances:
            return False
        
        # Verificar utilização média
        avg_util = self._get_average_utilization(instance.id)
        if avg_util is None:
            return False
        
        # Verificar se está abaixo do threshold por tempo suficiente
        history = self.metrics_history.get(instance.id, [])
        if len(history) < 5:  # Precisa de pelo menos 5 amostras
            return False
        
        # Verificar se TODOS os samples estão abaixo do threshold
        # Para GPU: verificar se abaixo do threshold
        gpu_low = all(m.gpu_utilization < self.config.pause_threshold_gpu for m in history)
        
        # Para CPU: verificar se abaixo do threshold (5%)
        cpu_low = all(m.cpu_utilization < self.config.pause_threshold_cpu for m in history)
        
        # Pausar se GPU E CPU estiverem baixos (ambos ociosos)
        all_low = gpu_low and cpu_low
        
        return all_low
    
    def _should_delete(self, instance: Instance) -> bool:
        """Verifica se instância deve ser deletada"""
        # Ignorar instâncias protegidas
        if instance.id in self.config.protected_instances:
            return False
        
        # Verificar idade mínima
        age_hours = (datetime.now() - instance.created_at).total_seconds() / 3600
        if age_hours < self.config.min_instance_age_hours:
            return False
        
        # Verificar última atividade
        last_activity = self._last_activity.get(instance.id, instance.created_at)
        idle_hours = (datetime.now() - last_activity).total_seconds() / 3600
        
        return idle_hours >= self.config.delete_threshold_hours
    
    async def _notify(self, action: str, instance: Instance, details: str = ""):
        """Envia notificação de ação"""
        message = f"[CostOptimizer] {action}: {instance.provider.value}/{instance.id} ({instance.gpu_name})"
        if details:
            message += f" - {details}"
        
        logger.info(message)
        
        # Webhook notification
        if self.config.webhook_url:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        self.config.webhook_url,
                        json={"text": message}
                    )
            except Exception as e:
                logger.warning(f"Webhook failed: {e}")
    
    async def _process_instance(self, instance: Instance):
        """Processa uma instância individual"""
        provider = self.providers.get(instance.provider)
        if not provider:
            return
        
        # Atualizar métricas
        metrics = await self._update_metrics(instance)
        
        if metrics:
            logger.debug(
                f"{instance.provider.value}/{instance.id}: "
                f"GPU={metrics.gpu_utilization:.1f}%, "
                f"Mem={metrics.memory_utilization:.1f}%"
            )
        
        # Verificar se deve pausar
        if self._should_pause(instance):
            avg_util = self._get_average_utilization(instance.id)
            if self.config.notify_on_pause:
                await self._notify(
                    "PAUSE",
                    instance,
                    f"GPU avg={avg_util:.1f}% (threshold={self.config.pause_threshold_gpu}%)"
                )
            
            success = await provider.pause_instance(instance)
            if success:
                logger.info(f"Successfully paused {instance.id}")
            else:
                logger.error(f"Failed to pause {instance.id}")
        
        # Verificar se deve deletar
        elif self._should_delete(instance):
            last_activity = self._last_activity.get(instance.id, instance.created_at)
            idle_hours = (datetime.now() - last_activity).total_seconds() / 3600
            
            if self.config.notify_on_delete:
                await self._notify(
                    "DELETE",
                    instance,
                    f"Idle for {idle_hours:.1f}h (threshold={self.config.delete_threshold_hours}h)"
                )
            
            success = await provider.delete_instance(instance)
            if success:
                logger.info(f"Successfully deleted {instance.id}")
                # Limpar histórico
                self.metrics_history.pop(instance.id, None)
                self._last_activity.pop(instance.id, None)
            else:
                logger.error(f"Failed to delete {instance.id}")
    
    async def run_once(self):
        """Executa um ciclo de verificação"""
        logger.info("Running optimization cycle...")
        
        instances = await self._get_all_instances()
        logger.info(f"Found {len(instances)} total instances")
        
        # Processar cada instância
        tasks = [self._process_instance(inst) for inst in instances]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Resumo
        running = sum(1 for i in instances if i.status == InstanceStatus.RUNNING)
        paused = sum(1 for i in instances if i.status in (InstanceStatus.PAUSED, InstanceStatus.STOPPED))
        logger.info(f"Cycle complete: {running} running, {paused} paused/stopped")
    
    async def run(self):
        """Loop principal do daemon"""
        self.running = True
        logger.info("Cost Optimizer started")
        logger.info(f"Config: pause_threshold={self.config.pause_threshold_gpu}%, "
                    f"delete_after={self.config.delete_threshold_hours}h")
        
        while self.running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"Error in optimization cycle: {e}")
            
            await asyncio.sleep(self.config.check_interval_seconds)
    
    def stop(self):
        """Para o daemon"""
        self.running = False
        logger.info("Cost Optimizer stopped")


async def main():
    """Ponto de entrada principal"""
    # Carregar configuração do ambiente
    config = OptimizerConfig(
        pause_threshold_gpu=float(os.getenv("PAUSE_THRESHOLD_GPU", "10")),
        delete_threshold_hours=int(os.getenv("DELETE_THRESHOLD_HOURS", "24")),
        check_interval_seconds=int(os.getenv("CHECK_INTERVAL", "60")),
        webhook_url=os.getenv("WEBHOOK_URL"),
    )
    
    optimizer = CostOptimizer(config)
    
    # Adicionar providers baseado nas variáveis de ambiente
    if os.getenv("VAST_API_KEY"):
        optimizer.add_provider(
            ProviderType.VAST_AI,
            VastAiProvider(os.getenv("VAST_API_KEY"))
        )
    
    if os.getenv("TENSORDOCK_API_KEY") and os.getenv("TENSORDOCK_API_TOKEN"):
        optimizer.add_provider(
            ProviderType.TENSOR_DOCK,
            TensorDockProvider(
                os.getenv("TENSORDOCK_API_KEY"),
                os.getenv("TENSORDOCK_API_TOKEN")
            )
        )
    
    if os.getenv("GCP_PROJECT_ID"):
        optimizer.add_provider(
            ProviderType.GCP,
            GcpProvider(
                os.getenv("GCP_PROJECT_ID"),
                os.getenv("GCP_ZONE", "us-central1-a")
            )
        )
    
    if not optimizer.providers:
        logger.error("No providers configured! Set API keys in environment.")
        return
    
    # Rodar
    try:
        await optimizer.run()
    except KeyboardInterrupt:
        optimizer.stop()


if __name__ == "__main__":
    asyncio.run(main())
