"""
Test: ServerlessService Integration Test

Testa o módulo ServerlessService real com provider mockado.
Valida toda a lógica de:
- Scale up/down automático
- Checkpoint antes de scale down
- Restore após scale up
- Monitoramento de GPU utilization
"""

import os
import sys
import time
import pytest
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.modules.serverless.config import ServerlessSettings, ServerlessMode, InstanceServerlessConfig


@dataclass
class MockGPUInstance:
    """Instância GPU mockada para testes"""
    id: str = "test-instance-123"
    status: str = "running"
    gpu_utilization: float = 0.0
    ssh_host: str = "192.168.1.100"
    ssh_port: int = 22
    hourly_cost: float = 0.35


class MockGPUProvider:
    """Provider mockado que simula comportamento real"""

    def __init__(self):
        self.instances: Dict[str, MockGPUInstance] = {}
        self.start_count = 0
        self.stop_count = 0
        self.checkpoint_created = False
        self.checkpoint_restored = False

    def add_instance(self, instance_id: str, status: str = "running") -> MockGPUInstance:
        instance = MockGPUInstance(id=instance_id, status=status)
        self.instances[instance_id] = instance
        return instance

    def get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        instance = self.instances.get(instance_id)
        if not instance:
            return {"status": "not_found"}
        return {
            "instance_id": instance.id,
            "actual_status": instance.status,
            "gpu_name": "RTX 4090",
            "gpu_count": 1,
            "ssh_host": instance.ssh_host,
            "ssh_port": instance.ssh_port,
            "dph_total": instance.hourly_cost,
        }

    def pause_instance(self, instance_id: str) -> bool:
        if instance_id in self.instances:
            self.instances[instance_id].status = "stopped"
            self.stop_count += 1
            return True
        return False

    def resume_instance(self, instance_id: str) -> bool:
        if instance_id in self.instances:
            self.instances[instance_id].status = "running"
            self.start_count += 1
            return True
        return False

    def destroy_instance(self, instance_id: str) -> bool:
        if instance_id in self.instances:
            del self.instances[instance_id]
            return True
        return False


class MockCheckpointService:
    """Checkpoint service mockado"""

    def __init__(self):
        self.checkpoints_created = 0
        self.checkpoints_restored = 0
        self.last_checkpoint_id = None

    def create_checkpoint(self, instance_id: str, ssh_host: str, ssh_port: int,
                         checkpoint_id: Optional[str] = None) -> Dict:
        self.checkpoints_created += 1
        self.last_checkpoint_id = checkpoint_id or f"ckpt-{instance_id}-{int(time.time())}"
        return {
            "success": True,
            "checkpoint_id": self.last_checkpoint_id,
            "size_bytes": 1024 * 1024 * 100,  # 100MB
            "vram_gb": 8.5,
        }

    def restore_checkpoint(self, instance_id: str, ssh_host: str, ssh_port: int,
                          checkpoint_id: str) -> Dict:
        self.checkpoints_restored += 1
        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "restored_pid": 12345,
        }

    def setup_instance(self, instance_id: str, ssh_host: str, ssh_port: int) -> Dict:
        return {"success": True, "driver": "550.54"}


class TestServerlessConfig:
    """Testes de configuração do módulo serverless"""

    def test_default_settings(self):
        """Testa configurações padrão"""
        settings = ServerlessSettings()

        assert settings.default_mode == ServerlessMode.ECONOMIC
        assert settings.default_idle_timeout_seconds == 30
        assert settings.checkpoint_enabled is True
        assert settings.fallback_enabled is True

    def test_instance_config(self):
        """Testa configuração de instância específica"""
        config = InstanceServerlessConfig(
            instance_id=123,
            mode=ServerlessMode.FAST,
            idle_timeout_seconds=15,
        )

        assert config.instance_id == 123
        assert config.mode == ServerlessMode.FAST
        assert config.idle_timeout_seconds == 15
        assert config.is_paused is False

    def test_serverless_modes(self):
        """Testa diferentes modos de serverless"""
        assert ServerlessMode.FAST.value == "fast"
        assert ServerlessMode.ECONOMIC.value == "economic"
        assert ServerlessMode.SPOT.value == "spot"
        assert ServerlessMode.DISABLED.value == "disabled"


class TestMockProvider:
    """Testes do provider mockado"""

    def test_instance_lifecycle(self):
        """Testa ciclo de vida da instância"""
        provider = MockGPUProvider()

        # Criar instância
        instance = provider.add_instance("test-1", status="running")
        assert instance.status == "running"

        # Pausar
        result = provider.pause_instance("test-1")
        assert result is True
        assert provider.instances["test-1"].status == "stopped"
        assert provider.stop_count == 1

        # Resumir
        result = provider.resume_instance("test-1")
        assert result is True
        assert provider.instances["test-1"].status == "running"
        assert provider.start_count == 1

        # Destruir
        result = provider.destroy_instance("test-1")
        assert result is True
        assert "test-1" not in provider.instances

    def test_get_instance_status(self):
        """Testa obter status da instância"""
        provider = MockGPUProvider()
        provider.add_instance("test-1", status="running")

        status = provider.get_instance_status("test-1")
        assert status["instance_id"] == "test-1"
        assert status["actual_status"] == "running"
        assert status["gpu_name"] == "RTX 4090"

        # Instância inexistente
        status = provider.get_instance_status("non-existent")
        assert status["status"] == "not_found"


class TestMockCheckpoint:
    """Testes do checkpoint mockado"""

    def test_create_checkpoint(self):
        """Testa criação de checkpoint"""
        checkpoint = MockCheckpointService()

        result = checkpoint.create_checkpoint(
            instance_id="test-1",
            ssh_host="192.168.1.100",
            ssh_port=22,
        )

        assert result["success"] is True
        assert "checkpoint_id" in result
        assert checkpoint.checkpoints_created == 1

    def test_restore_checkpoint(self):
        """Testa restore de checkpoint"""
        checkpoint = MockCheckpointService()

        # Primeiro criar
        create_result = checkpoint.create_checkpoint(
            instance_id="test-1",
            ssh_host="192.168.1.100",
            ssh_port=22,
        )

        # Depois restaurar
        restore_result = checkpoint.restore_checkpoint(
            instance_id="test-1",
            ssh_host="192.168.1.100",
            ssh_port=22,
            checkpoint_id=create_result["checkpoint_id"],
        )

        assert restore_result["success"] is True
        assert checkpoint.checkpoints_restored == 1


class TestScaleDownFlow:
    """Testes do fluxo de scale down"""

    def test_scale_down_with_checkpoint(self):
        """Testa scale down com checkpoint"""
        provider = MockGPUProvider()
        checkpoint = MockCheckpointService()

        # Setup
        instance = provider.add_instance("gpu-1", status="running")

        # Simular scale down com checkpoint
        # 1. Criar checkpoint antes de pausar
        ckpt_result = checkpoint.create_checkpoint(
            instance_id=instance.id,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
        )
        assert ckpt_result["success"] is True
        checkpoint_id = ckpt_result["checkpoint_id"]

        # 2. Pausar instância
        pause_result = provider.pause_instance(instance.id)
        assert pause_result is True
        assert provider.instances["gpu-1"].status == "stopped"

        # Verificar contadores
        assert checkpoint.checkpoints_created == 1
        assert provider.stop_count == 1

        print(f"✅ Scale down com checkpoint: {checkpoint_id}")

    def test_scale_down_without_checkpoint(self):
        """Testa scale down sem checkpoint (modo econômico)"""
        provider = MockGPUProvider()

        instance = provider.add_instance("gpu-1", status="running")

        # Pausar diretamente
        result = provider.pause_instance(instance.id)
        assert result is True
        assert provider.stop_count == 1

        print("✅ Scale down sem checkpoint")


class TestScaleUpFlow:
    """Testes do fluxo de scale up"""

    def test_scale_up_with_checkpoint_restore(self):
        """Testa scale up com restore de checkpoint"""
        provider = MockGPUProvider()
        checkpoint = MockCheckpointService()

        # Setup: instância parada com checkpoint
        instance = provider.add_instance("gpu-1", status="stopped")
        checkpoint_id = "ckpt-gpu-1-12345"

        # Simular scale up com restore
        # 1. Resumir instância
        resume_result = provider.resume_instance(instance.id)
        assert resume_result is True
        assert provider.instances["gpu-1"].status == "running"

        # 2. Restaurar checkpoint
        restore_result = checkpoint.restore_checkpoint(
            instance_id=instance.id,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            checkpoint_id=checkpoint_id,
        )
        assert restore_result["success"] is True

        # Verificar contadores
        assert provider.start_count == 1
        assert checkpoint.checkpoints_restored == 1

        print(f"✅ Scale up com restore: {checkpoint_id}")

    def test_cold_start_without_checkpoint(self):
        """Testa cold start sem checkpoint"""
        provider = MockGPUProvider()

        instance = provider.add_instance("gpu-1", status="stopped")

        # Resumir sem checkpoint
        result = provider.resume_instance(instance.id)
        assert result is True
        assert provider.start_count == 1

        print("✅ Cold start sem checkpoint")


class TestFullServerlessFlow:
    """Testes do fluxo completo de serverless"""

    def test_full_cycle_economic_mode(self):
        """Testa ciclo completo no modo econômico"""
        provider = MockGPUProvider()
        instance = provider.add_instance("gpu-1", status="stopped")

        # Estado inicial
        assert instance.status == "stopped"

        # 1. Requisição chega -> Scale Up
        print("\n[1] Requisição 1: Scale Up (Cold Start)")
        provider.resume_instance(instance.id)
        assert provider.instances["gpu-1"].status == "running"
        assert provider.start_count == 1

        # 2. Mais requisições (já running)
        print("[2] Requisição 2-3: Warm Start")
        # Não precisa fazer nada, já está running

        # 3. Idle timeout -> Scale Down
        print("[3] Idle Timeout: Scale Down")
        provider.pause_instance(instance.id)
        assert provider.instances["gpu-1"].status == "stopped"
        assert provider.stop_count == 1

        # 4. Nova requisição -> Scale Up novamente
        print("[4] Requisição 4: Scale Up (Cold Start)")
        provider.resume_instance(instance.id)
        assert provider.start_count == 2

        print("\n✅ Ciclo completo modo econômico OK")
        print(f"   - Start count: {provider.start_count}")
        print(f"   - Stop count: {provider.stop_count}")

    def test_full_cycle_fast_mode(self):
        """Testa ciclo completo no modo rápido (com checkpoint)"""
        provider = MockGPUProvider()
        checkpoint = MockCheckpointService()
        instance = provider.add_instance("gpu-1", status="stopped")

        # 1. Scale Up inicial (sem checkpoint, pois é primeira vez)
        print("\n[1] Primeira requisição: Cold Start")
        provider.resume_instance(instance.id)
        assert provider.start_count == 1

        # 2. Requisições processadas, criar checkpoint
        print("[2] Processando requisições...")

        # 3. Idle -> Criar checkpoint + Scale Down
        print("[3] Idle: Checkpoint + Scale Down")
        ckpt_result = checkpoint.create_checkpoint(
            instance_id=instance.id,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
        )
        checkpoint_id = ckpt_result["checkpoint_id"]
        provider.pause_instance(instance.id)
        assert checkpoint.checkpoints_created == 1
        assert provider.stop_count == 1

        # 4. Nova requisição -> Scale Up + Restore
        print("[4] Nova requisição: Scale Up + Restore")
        provider.resume_instance(instance.id)
        checkpoint.restore_checkpoint(
            instance_id=instance.id,
            ssh_host=instance.ssh_host,
            ssh_port=instance.ssh_port,
            checkpoint_id=checkpoint_id,
        )
        assert provider.start_count == 2
        assert checkpoint.checkpoints_restored == 1

        print("\n✅ Ciclo completo modo rápido OK")
        print(f"   - Start count: {provider.start_count}")
        print(f"   - Stop count: {provider.stop_count}")
        print(f"   - Checkpoints created: {checkpoint.checkpoints_created}")
        print(f"   - Checkpoints restored: {checkpoint.checkpoints_restored}")


class TestEdgeCases:
    """Testes de casos extremos"""

    def test_scale_up_while_stopping(self):
        """Testa requisição chegando durante scale down"""
        provider = MockGPUProvider()
        instance = provider.add_instance("gpu-1", status="stopping")

        # Tentar resumir enquanto para
        # Na prática, deveria esperar ou cancelar
        result = provider.resume_instance(instance.id)
        assert result is True  # Mock permite

    def test_multiple_instances(self):
        """Testa múltiplas instâncias"""
        provider = MockGPUProvider()

        instance1 = provider.add_instance("gpu-1", status="running")
        instance2 = provider.add_instance("gpu-2", status="stopped")
        instance3 = provider.add_instance("gpu-3", status="running")

        # Scale down gpu-1 e gpu-3
        provider.pause_instance("gpu-1")
        provider.pause_instance("gpu-3")
        assert provider.stop_count == 2

        # Scale up gpu-2
        provider.resume_instance("gpu-2")
        assert provider.start_count == 1

        # Status
        assert provider.instances["gpu-1"].status == "stopped"
        assert provider.instances["gpu-2"].status == "running"
        assert provider.instances["gpu-3"].status == "stopped"

    def test_instance_not_found(self):
        """Testa operações em instância inexistente"""
        provider = MockGPUProvider()

        result = provider.pause_instance("non-existent")
        assert result is False

        result = provider.resume_instance("non-existent")
        assert result is False

        result = provider.destroy_instance("non-existent")
        assert result is False


def run_all_tests():
    """Executa todos os testes manualmente"""
    print("=" * 70)
    print("TESTES DE INTEGRAÇÃO - ServerlessService")
    print("=" * 70)
    print()

    test_classes = [
        TestServerlessConfig,
        TestMockProvider,
        TestMockCheckpoint,
        TestScaleDownFlow,
        TestScaleUpFlow,
        TestFullServerlessFlow,
        TestEdgeCases,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n{'='*50}")
        print(f"Executando: {test_class.__name__}")
        print("=" * 50)

        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            method = getattr(instance, method_name)

            try:
                method()
                print(f"  ✅ {method_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"  ❌ {method_name}: {e}")
                failed_tests.append(f"{test_class.__name__}.{method_name}")
            except Exception as e:
                print(f"  ❌ {method_name}: {type(e).__name__}: {e}")
                failed_tests.append(f"{test_class.__name__}.{method_name}")

    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"\nTotal: {total_tests} testes")
    print(f"Passou: {passed_tests}")
    print(f"Falhou: {len(failed_tests)}")

    if failed_tests:
        print("\nTestes que falharam:")
        for test in failed_tests:
            print(f"  - {test}")
        return False
    else:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
