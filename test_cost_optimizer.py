#!/usr/bin/env python3
"""Teste do Cost Optimizer com TensorDock VM real"""

import asyncio
import sys
sys.path.insert(0, '/home/marcos/dumontcloud')

from services.cost_optimizer import (
    CostOptimizer, OptimizerConfig, 
    TensorDockProvider, ProviderType,
    Instance, InstanceStatus, GpuMetrics
)
from datetime import datetime

async def test_gpu_metrics():
    """Testa coleta de métricas da VM TensorDock real"""
    print("=" * 60)
    print("TESTE: Cost Optimizer - Coleta de Métricas GPU")
    print("=" * 60)
    
    # Criar instância fake representando a VM TensorDock
    instance = Instance(
        id="tensordock-test",
        provider=ProviderType.TENSOR_DOCK,
        name="test-v100",
        gpu_name="Tesla V100",
        status=InstanceStatus.RUNNING,
        ip_address="66.172.10.10",
        hourly_cost=0.45
    )
    
    print(f"\nVM: {instance.name}")
    print(f"IP: {instance.ip_address}")
    print(f"GPU: {instance.gpu_name}")
    print(f"Cost: ${instance.hourly_cost}/hr")
    
    # Coletar métricas via SSH
    print("\n[1] Coletando métricas GPU via SSH...")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
            f"user@{instance.ip_address}",
            "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        
        if proc.returncode == 0:
            parts = stdout.decode().strip().split(",")
            if len(parts) >= 4:
                metrics = GpuMetrics(
                    gpu_utilization=float(parts[0].strip()),
                    memory_used=float(parts[1].strip()) / 1024,
                    memory_total=float(parts[2].strip()) / 1024,
                    temperature=float(parts[3].strip())
                )
                
                print(f"\n✅ Métricas coletadas com sucesso!")
                print(f"   GPU Utilization: {metrics.gpu_utilization:.1f}%")
                print(f"   Memory Used: {metrics.memory_used:.1f} GB / {metrics.memory_total:.1f} GB ({metrics.memory_utilization:.1f}%)")
                print(f"   Temperature: {metrics.temperature:.0f}°C")
                
                # Verificar threshold
                threshold = 10.0
                print(f"\n[2] Verificando threshold (pause se < {threshold}%)...")
                
                if metrics.gpu_utilization < threshold:
                    print(f"   ⚠️  GPU está ABAIXO do threshold!")
                    print(f"   → Em produção, seria PAUSADA após 5 min neste estado")
                else:
                    print(f"   ✅ GPU está ACIMA do threshold, continua rodando")
                
                return True
            else:
                print(f"❌ Formato inesperado: {stdout.decode()}")
        else:
            print(f"❌ SSH falhou: {stderr.decode()}")
            
    except asyncio.TimeoutError:
        print("❌ Timeout ao conectar via SSH")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    return False


async def test_decision_logic():
    """Testa a lógica de decisão do optimizer"""
    print("\n" + "=" * 60)
    print("TESTE: Lógica de Decisão")
    print("=" * 60)
    
    config = OptimizerConfig(
        pause_threshold_gpu=10.0,
        pause_threshold_minutes=5,
        delete_threshold_hours=24
    )
    
    optimizer = CostOptimizer(config)
    
    # Simular instância com métricas baixas
    instance = Instance(
        id="test-vm",
        provider=ProviderType.TENSOR_DOCK,
        name="test-vm",
        gpu_name="V100",
        status=InstanceStatus.RUNNING,
        ip_address="1.2.3.4"
    )
    
    # Adicionar histórico de métricas baixas
    from datetime import timedelta
    
    for i in range(6):  # 6 samples = mais que 5 necessários
        metrics = GpuMetrics(
            gpu_utilization=3.0,  # Abaixo do threshold
            memory_used=2.0,
            memory_total=16.0,
            temperature=45.0,
            timestamp=datetime.now() - timedelta(minutes=i)
        )
        if instance.id not in optimizer.metrics_history:
            optimizer.metrics_history[instance.id] = []
        optimizer.metrics_history[instance.id].append(metrics)
    
    should_pause = optimizer._should_pause(instance)
    
    print(f"\nCenário: 6 amostras com GPU=3% (abaixo de 10%)")
    print(f"Decisão _should_pause(): {should_pause}")
    
    if should_pause:
        print("✅ Lógica correta! VM seria pausada")
    else:
        print("❌ Erro na lógica")
    
    return should_pause


async def main():
    print("\n🔧 COST OPTIMIZER - TESTE COMPLETO\n")
    
    # Teste 1: Métricas reais
    metrics_ok = await test_gpu_metrics()
    
    # Teste 2: Lógica
    logic_ok = await test_decision_logic()
    
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    print(f"Coleta de métricas: {'✅ OK' if metrics_ok else '❌ FALHOU'}")
    print(f"Lógica de decisão:  {'✅ OK' if logic_ok else '❌ FALHOU'}")
    print()
    
    if metrics_ok and logic_ok:
        print("🎉 Cost Optimizer está funcionando corretamente!")
    else:
        print("⚠️  Alguns testes falharam")


if __name__ == "__main__":
    asyncio.run(main())
