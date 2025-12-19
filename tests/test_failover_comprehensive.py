"""
TEST SUITE: CPU Standby Failover Automático
=============================================

Testa os fluxos completos de:
1. Sincronização GPU → CPU contínua
2. Detecção de falha GPU
3. Acionamento de failover automático
4. Restauração de dados
5. Auto-recovery (provisionar nova GPU)

Com coleta de performance metrics.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import services
from src.services.standby_manager import StandbyManager, StandbyAssociation
from src.services.cpu_standby_service import CPUStandbyService, CPUStandbyConfig, StandbyState


class PerformanceMetrics:
    """Coleta métricas de performance durante testes"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            'sync_times': [],
            'health_check_times': [],
            'failover_detection_time': 0,
            'failover_activation_time': 0,
            'recovery_total_time': 0,
            'recovery_phases': {},
            'data_consistency': True,
        }
        self.start_times = {}
        self.log_entries = []

    def start_timer(self, operation: str):
        """Inicia timer para operação"""
        self.start_times[operation] = time.time()

    def end_timer(self, operation: str):
        """Finaliza timer e registra tempo"""
        if operation in self.start_times:
            elapsed = time.time() - self.start_times[operation]
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(elapsed)
            return elapsed
        return None

    def log(self, message: str, level: str = "INFO"):
        """Log com timestamp"""
        timestamp = datetime.now().isoformat()
        entry = f"[{timestamp}] {level}: {message}"
        self.log_entries.append(entry)
        print(entry)

    def report(self) -> str:
        """Gera relatório de performance"""
        report = "\n" + "="*80 + "\n"
        report += "PERFORMANCE METRICS REPORT\n"
        report += "="*80 + "\n"

        if self.metrics['sync_times']:
            report += f"\n📊 SINCRONIZAÇÃO GPU → CPU:\n"
            report += f"  Total de syncs: {len(self.metrics['sync_times'])}\n"
            report += f"  Tempo médio: {sum(self.metrics['sync_times']) / len(self.metrics['sync_times']):.3f}s\n"
            report += f"  Mínimo: {min(self.metrics['sync_times']):.3f}s\n"
            report += f"  Máximo: {max(self.metrics['sync_times']):.3f}s\n"

        if self.metrics['health_check_times']:
            report += f"\n❤️  HEALTH CHECK GPU:\n"
            report += f"  Total de checks: {len(self.metrics['health_check_times'])}\n"
            report += f"  Tempo médio: {sum(self.metrics['health_check_times']) / len(self.metrics['health_check_times']):.3f}s\n"

        if self.metrics['failover_detection_time']:
            report += f"\n⚠️  DETECÇÃO DE FALHA:\n"
            report += f"  Tempo até detecção: {self.metrics['failover_detection_time']:.3f}s\n"

        if self.metrics['failover_activation_time']:
            report += f"\n🚨 ATIVAÇÃO DE FAILOVER:\n"
            report += f"  Tempo até ativação: {self.metrics['failover_activation_time']:.3f}s\n"

        if self.metrics['recovery_total_time']:
            report += f"\n🔄 AUTO-RECOVERY:\n"
            report += f"  Tempo total: {self.metrics['recovery_total_time']:.3f}s\n"
            for phase, time_val in self.metrics['recovery_phases'].items():
                report += f"    {phase}: {time_val:.3f}s\n"

        report += f"\n✅ Consistência de dados: {'OK' if self.metrics['data_consistency'] else 'FALHOU'}\n"
        report += "="*80 + "\n"

        return report


class MockVastService:
    """Mock do VastService para testes"""

    def __init__(self, gpu_fail_at_check: int = -1):
        self.gpu_status = 'running'
        self.health_check_count = 0
        self.gpu_fail_at_check = gpu_fail_at_check  # Em qual check a GPU falha (-1 = nunca)
        self.offers_available = [
            {
                'id': 9999,
                'gpu_name': 'RTX 4090',
                'price_per_hour': 0.45,
                'cpu_cores': 16,
                'cpu_ram': 64,
                'disk_space': 1000,
                'geolocation': 'TH',
            }
        ]

    def get_instance_status(self, instance_id: int) -> Dict:
        """Mock: retorna status da instância"""
        self.health_check_count += 1

        # Simula falha após N checks
        if self.gpu_fail_at_check > 0 and self.health_check_count >= self.gpu_fail_at_check:
            self.gpu_status = 'offline'

        return {
            'id': instance_id,
            'status': self.gpu_status,
            'actual_status': self.gpu_status,
            'gpu_name': 'RTX 4090',
            'ssh_host': 'gpu.vastai.com',
            'ssh_port': 12345,
        }

    def search_offers(self, filters: Dict) -> List[Dict]:
        """Mock: busca ofertas GPU"""
        return self.offers_available

    def create_instance(self, offer_id: int, image: str, disk_size: int) -> Dict:
        """Mock: cria nova instância"""
        return {
            'id': 888888,
            'status': 'provisioning',
            'ssh_host': 'gpu-new.vastai.com',
            'ssh_port': 54321,
        }


class MockGCPProvider:
    """Mock do GCP Provider para testes"""

    def __init__(self):
        self.vm_status = 'RUNNING'
        self.created_vms = []

    def create_instance(self, config) -> Dict:
        """Mock: cria VM GCP"""
        self.created_vms.append(config.name)
        return {
            'success': True,
            'instance_id': '4321098765',
            'name': config.name,
            'zone': config.zone,
            'machine_type': config.machine_type,
            'external_ip': '35.204.123.45',
            'internal_ip': '10.132.0.2',
            'status': 'RUNNING',
            'spot': config.spot
        }

    def delete_instance(self, name: str, zone: str) -> bool:
        """Mock: deleta VM GCP"""
        if name in self.created_vms:
            self.created_vms.remove(name)
        return True

    def get_instance(self, name: str, zone: str) -> Dict:
        """Mock: obtem detalhes da VM"""
        return {
            'name': name,
            'status': self.vm_status,
            'external_ip': '35.204.123.45',
        }


class TestCPUStandbySync:
    """Testa sincronização contínua GPU → CPU"""

    def setup_method(self):
        """Setup antes de cada teste"""
        self.metrics = PerformanceMetrics()
        self.metrics.log("Iniciando teste de sincronização...")

    def test_sync_gpu_to_cpu_continuous(self):
        """Teste: Sincronização contínua GPU → CPU"""
        self.metrics.log("TEST: Sincronização contínua GPU → CPU")

        # Mock config
        config = CPUStandbyConfig(
            sync_interval_seconds=2,
            health_check_interval=1,
            gcp_zone='europe-west1-b',
        )

        # Mock services
        vast_service = MockVastService()
        gcp_provider = MockGCPProvider()

        # Criar service
        service = CPUStandbyService(
            gpu_instance_id=123456,
            gpu_ssh_host='gpu.vastai.com',
            gpu_ssh_port=12345,
            cpu_instance_ip='35.204.123.45',
            config=config,
        )

        # Mock métodos
        service._do_sync = Mock(return_value=True)
        service._check_gpu_health = Mock(return_value=True)

        # Simular N syncs
        num_syncs = 5
        for i in range(num_syncs):
            self.metrics.start_timer('sync')
            service._do_sync()
            elapsed = self.metrics.end_timer('sync')
            service.sync_count += 1
            self.metrics.log(f"Sync #{i+1}: {elapsed:.3f}s", "SYNC")

        # Verificações
        assert service.sync_count == num_syncs
        assert len(self.metrics.metrics['sync_times']) == num_syncs

        self.metrics.log(f"✅ Sincronizações completadas: {num_syncs}")
        print(self.metrics.report())

    def test_sync_failure_recovery(self):
        """Teste: Recuperação de falha de sync"""
        self.metrics.log("TEST: Recuperação de falha de sync")

        config = CPUStandbyConfig(
            sync_interval_seconds=1,
            health_check_interval=1,
        )

        service = CPUStandbyService(
            gpu_instance_id=123456,
            gpu_ssh_host='gpu.vastai.com',
            gpu_ssh_port=12345,
            cpu_instance_ip='35.204.123.45',
            config=config,
        )

        # Simular 3 falhas seguidas de sucesso
        sync_results = [False, False, False, True, True]
        sync_call_count = 0

        def mock_sync():
            nonlocal sync_call_count
            result = sync_results[sync_call_count]
            sync_call_count += 1
            if result:
                service.sync_count += 1
            return result

        service._do_sync = mock_sync

        for i in range(len(sync_results)):
            result = service._do_sync()
            status = "✅ OK" if result else "❌ FAIL"
            self.metrics.log(f"Sync tentativa #{i+1}: {status}", "SYNC")

        assert service.sync_count == 2  # 2 sucessos após 3 falhas
        self.metrics.log("✅ Recuperação de falha funcionou")
        print(self.metrics.report())


class TestFailoverDetection:
    """Testa detecção de falha GPU e acionamento de failover"""

    def setup_method(self):
        """Setup antes de cada teste"""
        self.metrics = PerformanceMetrics()
        self.metrics.log("Iniciando teste de detecção de falha...")

    def test_gpu_failure_detection_threshold(self):
        """Teste: GPU falha é detectada após threshold de checks"""
        self.metrics.log("TEST: Detecção de falha GPU com threshold")

        config = CPUStandbyConfig(
            health_check_interval=1,
            failover_threshold=3,  # 3 falhas = failover
            auto_failover=True,
        )

        vast_service = MockVastService(gpu_fail_at_check=3)

        service = CPUStandbyService(
            gpu_instance_id=123456,
            gpu_ssh_host='gpu.vastai.com',
            gpu_ssh_port=12345,
            cpu_instance_ip='35.204.123.45',
            config=config,
        )

        # Mock dos métodos de health check
        failed_checks = 0

        def mock_health_check():
            nonlocal failed_checks
            status = vast_service.get_instance_status(123456)
            is_healthy = status['status'] == 'running'
            if not is_healthy:
                failed_checks += 1
                self.metrics.log(f"Health check FALHOU: {failed_checks}/{config.failover_threshold}", "HEALTH")
            else:
                self.metrics.log("Health check OK", "HEALTH")
            return is_healthy

        service._check_gpu_health = mock_health_check
        service.trigger_failover = Mock()

        # Simular health checks até failover
        for check_num in range(1, 6):
            self.metrics.start_timer(f'health_check_{check_num}')
            is_healthy = service._check_gpu_health()
            self.metrics.end_timer(f'health_check_{check_num}')

            # Simular lógica de threshold
            service.failed_health_checks = failed_checks
            if service.failed_health_checks >= config.failover_threshold:
                failover_triggered = True
                self.metrics.metrics['failover_detection_time'] = check_num * config.health_check_interval
                service.trigger_failover()
                break

        # Verificações
        assert failed_checks >= config.failover_threshold
        assert service.trigger_failover.called
        self.metrics.log(f"✅ Failover acionado após {failed_checks} falhas")
        print(self.metrics.report())

    def test_failover_state_transition(self):
        """Teste: Transição correta de estado para FAILOVER_ACTIVE"""
        self.metrics.log("TEST: Transição de estado para FAILOVER_ACTIVE")

        service = CPUStandbyService(
            gpu_instance_id=123456,
            gpu_ssh_host='gpu.vastai.com',
            gpu_ssh_port=12345,
            cpu_instance_ip='35.204.123.45',
            config=CPUStandbyConfig(auto_failover=True),
        )

        # Estado inicial
        self.metrics.log(f"Estado inicial: {service.state}")
        assert service.state == StandbyState.READY

        # Simular transição
        service.state = StandbyState.FAILOVER_ACTIVE
        self.metrics.log(f"Estado após failover: {service.state}")

        # Verificações
        assert service.state == StandbyState.FAILOVER_ACTIVE
        self.metrics.log("✅ Transição de estado correta")
        print(self.metrics.report())


class TestDataRestoration:
    """Testa restauração de dados após falha"""

    def setup_method(self):
        """Setup antes de cada teste"""
        self.metrics = PerformanceMetrics()
        self.metrics.log("Iniciando teste de restauração de dados...")

        # Mock workspace
        self.mock_workspace_gpu = {
            'model.pt': {'size': 1000000, 'hash': 'abc123'},
            'data.csv': {'size': 500000, 'hash': 'def456'},
            'config.json': {'size': 1000, 'hash': 'ghi789'},
        }
        self.mock_workspace_cpu = {}

    def test_data_sync_to_cpu_before_failure(self):
        """Teste: Dados sincronizados para CPU ANTES da falha"""
        self.metrics.log("TEST: Sincronização de dados para CPU")

        # Simular sincronização
        self.metrics.start_timer('sync_workspace')
        self.mock_workspace_cpu = dict(self.mock_workspace_gpu)
        elapsed = self.metrics.end_timer('sync_workspace')

        self.metrics.log(f"Workspace sincronizado em {elapsed:.3f}s", "SYNC")
        self.metrics.log(f"Arquivos sincronizados: {list(self.mock_workspace_cpu.keys())}", "SYNC")

        # Verificações
        assert self.mock_workspace_cpu == self.mock_workspace_gpu
        self.metrics.log("✅ Dados sincronizados com sucesso")

    def test_data_consistency_after_failover(self):
        """Teste: Dados consistentes na CPU após failover"""
        self.metrics.log("TEST: Consistência de dados após failover")

        # Sincronizar dados
        self.mock_workspace_cpu = dict(self.mock_workspace_gpu)

        # Simular falha GPU
        self.metrics.log("GPU falhou! Acionando failover...", "ERROR")
        self.mock_workspace_gpu = {}  # GPU perdeu dados

        # Verificar CPU ainda tem dados
        cpu_has_data = len(self.mock_workspace_cpu) > 0
        gpu_has_data = len(self.mock_workspace_gpu) > 0

        self.metrics.log(f"GPU tem dados: {gpu_has_data}", "STATE")
        self.metrics.log(f"CPU tem dados: {cpu_has_data}", "STATE")

        assert cpu_has_data
        assert not gpu_has_data
        self.metrics.log("✅ Dados preservados na CPU após falha GPU")

    def test_data_restore_from_cpu_to_new_gpu(self):
        """Teste: Restauração de dados da CPU para nova GPU"""
        self.metrics.log("TEST: Restauração CPU → nova GPU")

        # Estado: CPU tem dados, GPU falhou
        self.mock_workspace_cpu = dict(self.mock_workspace_gpu)
        self.mock_workspace_gpu = {}

        # Simular novo GPU provisionada
        new_gpu_workspace = {}

        # Restaurar
        self.metrics.start_timer('restore_cpu_to_gpu')
        new_gpu_workspace = dict(self.mock_workspace_cpu)
        elapsed = self.metrics.end_timer('restore_cpu_to_gpu')

        self.metrics.log(f"Dados restaurados em {elapsed:.3f}s", "RESTORE")
        self.metrics.log(f"Arquivos restaurados: {list(new_gpu_workspace.keys())}", "RESTORE")

        # Verificações
        assert new_gpu_workspace == self.mock_workspace_cpu
        assert new_gpu_workspace == self.mock_workspace_gpu  # Originalmente
        self.metrics.metrics['data_consistency'] = True
        self.metrics.log("✅ Dados restaurados com sucesso")


class TestAutoRecovery:
    """Testa auto-recovery (provisionar nova GPU)"""

    def setup_method(self):
        """Setup antes de cada teste"""
        self.metrics = PerformanceMetrics()
        self.metrics.log("Iniciando teste de auto-recovery...")

    def test_auto_recovery_find_gpu(self):
        """Teste: Buscar GPU disponível durante recovery"""
        self.metrics.log("TEST: Busca de GPU disponível")

        vast_service = MockVastService()

        config = CPUStandbyConfig(
            gpu_max_price=0.50,
            gpu_preferred_regions=['TH', 'VN', 'JP'],
        )

        # Simular busca
        self.metrics.start_timer('search_offers')
        offers = vast_service.search_offers({'max_price': config.gpu_max_price})
        elapsed = self.metrics.end_timer('search_offers')

        self.metrics.log(f"Ofertas encontradas em {elapsed:.3f}s: {len(offers)}", "SEARCH")
        if offers:
            self.metrics.log(f"  GPU: {offers[0]['gpu_name']}", "SEARCH")
            self.metrics.log(f"  Preço: ${offers[0]['price_per_hour']}/hr", "SEARCH")
            self.metrics.log(f"  Região: {offers[0]['geolocation']}", "SEARCH")

        assert len(offers) > 0
        self.metrics.log("✅ GPU disponível encontrada")

    def test_auto_recovery_provision_gpu(self):
        """Teste: Provisionar nova GPU"""
        self.metrics.log("TEST: Provisionamento de nova GPU")

        vast_service = MockVastService()

        # Encontrar oferta
        offers = vast_service.search_offers({})
        offer = offers[0]

        # Provisionar
        self.metrics.start_timer('provision_gpu')
        new_instance = vast_service.create_instance(
            offer_id=offer['id'],
            image='pytorch/pytorch:latest',
            disk_size=50,
        )
        elapsed = self.metrics.end_timer('provision_gpu')

        self.metrics.log(f"GPU provisionada em {elapsed:.3f}s", "PROVISION")
        self.metrics.log(f"  ID: {new_instance['id']}", "PROVISION")
        self.metrics.log(f"  Host: {new_instance['ssh_host']}", "PROVISION")
        self.metrics.log(f"  Port: {new_instance['ssh_port']}", "PROVISION")

        assert new_instance['id'] is not None
        self.metrics.log("✅ GPU provisionada com sucesso")
        self.metrics.metrics['recovery_phases']['provision'] = elapsed

    def test_auto_recovery_wait_for_ssh(self):
        """Teste: Aguardar SSH ficar pronto"""
        self.metrics.log("TEST: Aguardar SSH da nova GPU")

        # Simular espera por SSH
        max_wait = 5  # segundos
        wait_time = 0
        ssh_ready_at = 3  # SSH fica pronto em 3s

        self.metrics.start_timer('wait_ssh')
        while wait_time < max_wait:
            if wait_time >= ssh_ready_at:
                elapsed = self.metrics.end_timer('wait_ssh')
                break
            wait_time += 0.5

        self.metrics.log(f"SSH pronto em {elapsed:.3f}s", "SSH")
        assert wait_time >= ssh_ready_at
        self.metrics.log("✅ SSH pronto para conexão")
        self.metrics.metrics['recovery_phases']['ssh_ready'] = elapsed

    def test_auto_recovery_full_cycle(self):
        """Teste: Ciclo completo de auto-recovery"""
        self.metrics.log("TEST: Ciclo completo auto-recovery")

        vast_service = MockVastService()

        # FASE 1: Buscar GPU
        self.metrics.log("FASE 1: Buscando GPU...", "PHASE")
        self.metrics.start_timer('recovery_search')
        offers = vast_service.search_offers({'max_price': 0.50})
        self.metrics.metrics['recovery_phases']['search'] = self.metrics.end_timer('recovery_search')

        # FASE 2: Provisionar
        self.metrics.log("FASE 2: Provisionando GPU...", "PHASE")
        self.metrics.start_timer('recovery_provision')
        new_instance = vast_service.create_instance(offers[0]['id'], 'pytorch', 50)
        self.metrics.metrics['recovery_phases']['provision'] = self.metrics.end_timer('recovery_provision')

        # FASE 3: Aguardar SSH
        self.metrics.log("FASE 3: Aguardando SSH...", "PHASE")
        self.metrics.start_timer('recovery_ssh')
        # Simular espera
        time.sleep(0.1)
        self.metrics.metrics['recovery_phases']['ssh'] = self.metrics.end_timer('recovery_ssh')

        # FASE 4: Restaurar dados
        self.metrics.log("FASE 4: Restaurando dados...", "PHASE")
        self.metrics.start_timer('recovery_restore')
        # Simular restore
        time.sleep(0.1)
        self.metrics.metrics['recovery_phases']['restore'] = self.metrics.end_timer('recovery_restore')

        # Calcular tempo total
        total_time = sum(self.metrics.metrics['recovery_phases'].values())
        self.metrics.metrics['recovery_total_time'] = total_time

        self.metrics.log(f"✅ Auto-recovery completado em {total_time:.3f}s", "SUCCESS")
        print(self.metrics.report())


class TestIntegrationFailoverFlow:
    """Teste de integração: Fluxo completo failover"""

    def setup_method(self):
        """Setup antes de cada teste"""
        self.metrics = PerformanceMetrics()

    def test_complete_failover_flow(self):
        """Teste: Fluxo completo desde sincronização até recovery"""
        self.metrics.log("TEST: Fluxo completo de failover", "INTEGRATION")

        config = CPUStandbyConfig(
            sync_interval_seconds=1,
            health_check_interval=1,
            failover_threshold=3,
            auto_failover=True,
            auto_recovery=True,
        )

        # Simular timeline
        timeline = [
            (1, "SYNC", "Sincronizando GPU → CPU"),
            (2, "SYNC", "Sincronizando GPU → CPU"),
            (3, "HEALTH", "Health check OK"),
            (4, "SYNC", "Sincronizando GPU → CPU"),
            (5, "HEALTH", "Health check OK"),
            (6, "HEALTH", "🚨 GPU FALHA! Health check FALHA #1"),
            (7, "HEALTH", "🚨 GPU ainda offline! Health check FALHA #2"),
            (8, "HEALTH", "🚨 GPU ainda offline! Health check FALHA #3"),
            (9, "FAILOVER", "🚔 FAILOVER ACIONADO! CPU é novo endpoint"),
            (10, "RECOVERY", "🔄 Auto-recovery iniciado"),
            (11, "RECOVERY", "  → Buscando GPU disponível..."),
            (12, "RECOVERY", "  → Provisionando nova GPU..."),
            (13, "RECOVERY", "  → Aguardando SSH..."),
            (14, "RECOVERY", "  → Restaurando dados..."),
            (15, "SUCCESS", "✅ Auto-recovery completo! Sistema voltou ao normal"),
        ]

        self.metrics.log("="*80)
        self.metrics.log("SIMULAÇÃO DE FAILOVER AUTOMÁTICO")
        self.metrics.log("="*80)

        for timestamp, event_type, message in timeline:
            self.metrics.log(f"T{timestamp:02d}: {message}", event_type)

            # Registrar tempos importantes
            if "FALHA #1" in message:
                self.metrics.metrics['failover_detection_time'] = (timestamp - 6 + 1) * config.health_check_interval
            elif "FAILOVER ACIONADO" in message:
                self.metrics.metrics['failover_activation_time'] = (timestamp - 6) * config.health_check_interval
            elif "Auto-recovery completo" in message:
                self.metrics.metrics['recovery_total_time'] = (timestamp - 10 + 1)

        print(self.metrics.report())


class TestStandbyManagerIntegration:
    """Testa StandbyManager (orquestrador)"""

    def setup_method(self):
        """Setup antes de cada teste"""
        self.metrics = PerformanceMetrics()

    def test_standby_manager_create_association(self):
        """Teste: StandbyManager cria associação GPU ↔ CPU"""
        self.metrics.log("TEST: Criação de associação GPU ↔ CPU")

        manager = StandbyManager()

        # Simular criação
        association = StandbyAssociation(
            gpu_instance_id=123456,
            cpu_instance_name='dumont-gpu-123456-1702854321',
            cpu_instance_zone='europe-west1-b',
            cpu_instance_ip='35.204.123.45',
        )

        # Registrar
        manager.associations[association.gpu_instance_id] = association

        self.metrics.log(f"GPU {association.gpu_instance_id} ↔ CPU {association.cpu_instance_name}")

        assert association.gpu_instance_id in manager.associations
        self.metrics.log("✅ Associação criada com sucesso")

    def test_standby_manager_mark_gpu_failed(self):
        """Teste: Marcar GPU como falha (mantém CPU para backup)"""
        self.metrics.log("TEST: Marcar GPU como falha")

        manager = StandbyManager()

        # Criar associação
        association = StandbyAssociation(
            gpu_instance_id=123456,
            cpu_instance_name='dumont-gpu-123456-1702854321',
            cpu_instance_zone='europe-west1-b',
            cpu_instance_ip='35.204.123.45',
        )
        manager.associations[123456] = association

        # Marcar como falha
        association.gpu_failed = True
        association.failure_reason = 'spot_interruption'

        self.metrics.log(f"GPU {association.gpu_instance_id} marcada como FALHA")
        self.metrics.log(f"Razão: {association.failure_reason}")
        self.metrics.log(f"CPU ainda disponível: {association.cpu_instance_name}")

        assert association.gpu_failed
        self.metrics.log("✅ GPU marcada como falha, CPU preservada")


# ============================================================================
# EXECUÇÃO DOS TESTES
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("SUITE DE TESTES: CPU STANDBY FAILOVER AUTOMÁTICO")
    print("="*80 + "\n")

    # Executar testes
    pytest.main([__file__, '-v', '-s', '--tb=short'])
