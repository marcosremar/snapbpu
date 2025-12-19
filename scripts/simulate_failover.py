#!/usr/bin/env python3
"""
SIMULADOR DE FAILOVER AUTOMÁTICO
==================================

Simula o fluxo completo de:
1. Máquina GPU rodando normalmente
2. Sincronização contínua com CPU standby
3. Detecção de falha GPU
4. Acionamento automático de failover
5. CPU assume como endpoint principal
6. Auto-recovery provisiona nova GPU
7. Dados restaurados, sistema volta ao normal

Com coleta detalhada de performance metrics.
"""

import time
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple
from enum import Enum
import json
import os


class SimulationPhase(Enum):
    """Fases da simulação"""
    SETUP = "setup"
    NORMAL_OPERATION = "normal_operation"
    GPU_FAILURE = "gpu_failure"
    FAILOVER_DETECTION = "failover_detection"
    FAILOVER_ACTIVATION = "failover_activation"
    AUTO_RECOVERY = "auto_recovery"
    RECOVERY_COMPLETE = "recovery_complete"


@dataclass
class PerformanceData:
    """Dados de performance coletados"""
    phase: SimulationPhase
    timestamp: float
    event: str
    duration: float = 0.0
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class FailoverSimulator:
    """Simulador de failover automático"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.performance_data: List[PerformanceData] = []
        self.current_phase = SimulationPhase.SETUP
        self.start_time = time.time()
        self.simulation_time = 0.0

        # Estado simulado
        self.gpu_status = "RUNNING"
        self.cpu_status = "RUNNING"
        self.gpu_health_checks = 0
        self.gpu_failures = 0
        self.sync_operations = 0
        self.data_synced = False

    def log(self, message: str, level: str = "INFO", phase: SimulationPhase = None):
        """Registra mensagem com timestamp"""
        if phase is None:
            phase = self.current_phase

        timestamp = time.time() - self.start_time
        self.simulation_time = timestamp

        colors = {
            "INFO": "\033[94m",  # Blue
            "SYNC": "\033[92m",  # Green
            "HEALTH": "\033[93m",  # Yellow
            "ERROR": "\033[91m",  # Red
            "SUCCESS": "\033[92m",  # Green
            "PHASE": "\033[95m",  # Magenta
            "METRIC": "\033[96m",  # Cyan
        }
        reset = "\033[0m"

        color = colors.get(level, "")

        if self.verbose:
            print(f"{color}[T{timestamp:06.2f}s] [{level:7s}] {message}{reset}")

        # Registrar performance data
        self.performance_data.append(PerformanceData(
            phase=phase,
            timestamp=timestamp,
            event=message,
            metadata={"level": level}
        ))

    def print_header(self, title: str):
        """Imprime cabeçalho"""
        print("\n" + "="*90)
        print(f"  {title}".center(90))
        print("="*90 + "\n")

    def print_state(self):
        """Imprime estado atual"""
        print(f"\n{'-'*90}")
        print(f"GPU Status: {self.gpu_status:15s} | CPU Status: {self.cpu_status:15s} | "
              f"Syncs: {self.sync_operations:3d} | Health Checks: {self.gpu_health_checks:3d}")
        print(f"{'-'*90}\n")

    def phase_setup(self):
        """Fase 1: Setup"""
        self.print_header("FASE 1: SETUP INICIAL")
        self.current_phase = SimulationPhase.SETUP

        self.log("Iniciando simulador de failover automático...", "PHASE")
        time.sleep(0.5)

        self.log("Configurando GPU instance (Vast.ai)...", "INFO")
        self.gpu_status = "RUNNING"
        time.sleep(0.3)

        self.log(f"  ✓ GPU Instance ID: 123456", "INFO")
        self.log(f"  ✓ GPU Model: RTX 4090", "INFO")
        self.log(f"  ✓ SSH Host: gpu.vastai.com:12345", "INFO")
        time.sleep(0.3)

        self.log("Provisionando CPU standby (GCP)...", "INFO")
        self.cpu_status = "RUNNING"
        time.sleep(0.3)

        self.log(f"  ✓ CPU Instance: dumont-gpu-123456-1702854321", "INFO")
        self.log(f"  ✓ Machine Type: e2-medium (1 vCPU, 4GB)", "INFO")
        self.log(f"  ✓ IP Externo: 35.204.123.45", "INFO")
        self.log(f"  ✓ Spot: True (Preço: $0.01/hr)", "INFO")
        time.sleep(0.3)

        self.log("Iniciando sincronização contínua GPU → CPU...", "INFO")
        self.data_synced = True
        time.sleep(0.3)

        self.log("✅ Setup completo! Sistema pronto.", "SUCCESS")
        self.print_state()

    def phase_normal_operation(self):
        """Fase 2: Operação normal"""
        self.print_header("FASE 2: OPERAÇÃO NORMAL (GPU rodando)")
        self.current_phase = SimulationPhase.NORMAL_OPERATION

        self.log("Sistema operacional normal. GPU processando workload...", "PHASE")
        time.sleep(0.5)

        # Simular 5 ciclos de sync + health check
        for cycle in range(1, 6):
            # Sync
            self.log(f"Ciclo {cycle}: Sincronizando GPU → CPU...", "SYNC")
            start = time.time()
            time.sleep(0.2)  # Simular latência de sync
            elapsed = time.time() - start
            self.sync_operations += 1
            self.log(f"  ✓ Sync #{self.sync_operations} completo ({elapsed:.3f}s)", "SYNC")

            # Workspace sync
            self.log(f"  ↳ /workspace: 1.2 GB sincronizados (dedup: 80%)", "METRIC")
            time.sleep(0.1)

            # Health check
            self.log(f"Verificando saúde da GPU...", "HEALTH")
            time.sleep(0.1)
            self.gpu_health_checks += 1
            self.log(f"  ✓ Health check #{self.gpu_health_checks}: GPU OK (utilização: 87%)", "HEALTH")
            time.sleep(0.2)

            if cycle < 5:
                self.print_state()

        self.log("✅ Operação normal estável. Todos os sistemas OK.", "SUCCESS")
        self.print_state()

    def phase_gpu_failure(self):
        """Fase 3: Falha da GPU"""
        self.print_header("FASE 3: GPU FALHA (Simulado)")
        self.current_phase = SimulationPhase.GPU_FAILURE

        self.log("🚨 SIMULANDO FALHA GPU...", "ERROR", SimulationPhase.GPU_FAILURE)
        time.sleep(0.5)

        # Possíveis razões
        failure_reasons = [
            "Spot Instance Interruption",
            "GPU Timeout (CUDA out of memory)",
            "Network Connectivity Lost"
        ]
        reason = failure_reasons[0]

        self.log(f"Razão da falha: {reason}", "ERROR")
        time.sleep(0.3)

        self.gpu_status = "OFFLINE"
        self.log(f"GPU agora está: {self.gpu_status}", "ERROR")
        time.sleep(0.3)

        self.log("Última sincronização: 2 segundos atrás", "METRIC")
        self.log("Dados em CPU: COMPLETO (sincronizado)", "METRIC")
        time.sleep(0.3)

        self.print_state()

    def phase_failover_detection(self):
        """Fase 4: Detecção de falha e threshold"""
        self.print_header("FASE 4: DETECÇÃO DE FALHA (Health Check Threshold)")
        self.current_phase = SimulationPhase.FAILOVER_DETECTION

        self.log("Sistema continua monitorando saúde da GPU...", "PHASE")
        time.sleep(0.3)

        # 3 health checks falhando
        for check_num in range(1, 4):
            self.log(f"Health check #{self.gpu_health_checks + check_num}...", "HEALTH")
            time.sleep(0.2)
            self.gpu_failures += 1
            self.log(f"  ❌ GPU OFFLINE (falha {check_num}/3 detectadas)", "ERROR")
            time.sleep(0.3)

        self.log(f"Threshold atingido: {self.gpu_failures}/3 falhas consecutivas", "HEALTH")
        time.sleep(0.3)

        self.print_state()

    def phase_failover_activation(self):
        """Fase 5: Ativação de failover"""
        self.print_header("FASE 5: ATIVAÇÃO DE FAILOVER (CPU é novo endpoint)")
        self.current_phase = SimulationPhase.FAILOVER_ACTIVATION

        self.log("🚔 FAILOVER AUTOMÁTICO ACIONADO!", "ERROR")
        time.sleep(0.5)

        self.log("Estado: GPU OFFLINE | CPU ONLINE ↔ Mudando endpoint...", "PHASE")
        time.sleep(0.3)

        self.log("Transição de Estado:", "PHASE")
        time.sleep(0.2)
        self.log("  ANTES: GPU é endpoint principal", "INFO")
        time.sleep(0.2)
        self.log("  DEPOIS: CPU standby é endpoint principal", "SUCCESS")
        time.sleep(0.3)

        self.log("Redirecionando conexões:", "PHASE")
        time.sleep(0.2)
        self.log("  SSH: gpu.vastai.com:12345 → 35.204.123.45:22", "SUCCESS")
        time.sleep(0.2)
        self.log("  Workspace: /workspace (já sincronizado no CPU)", "SUCCESS")
        time.sleep(0.3)

        self.log("Iniciando auto-recovery (background thread)...", "INFO")
        time.sleep(0.3)

        self.log("✅ Failover completo! CPU é novo endpoint.", "SUCCESS")
        self.print_state()

    def phase_auto_recovery(self):
        """Fase 6: Auto-recovery"""
        self.print_header("FASE 6: AUTO-RECOVERY (Provisionar nova GPU)")
        self.current_phase = SimulationPhase.AUTO_RECOVERY

        self.log("🔄 AUTO-RECOVERY INICIADO (rodando em background)", "PHASE")
        time.sleep(0.5)

        # PASSO 1: Buscar GPU
        self.log("PASSO 1: Buscando GPU disponível...", "PHASE")
        time.sleep(0.3)
        self.log("  Critérios:", "INFO")
        self.log("    - RAM: ≥ 8GB", "INFO")
        self.log("    - Preço: ≤ $0.50/hr", "INFO")
        self.log("    - Regiões preferidas: TH, VN, JP, EU", "INFO")
        time.sleep(0.3)

        start = time.time()
        time.sleep(0.5)  # Simular busca
        elapsed = time.time() - start
        self.log(f"  ✓ Encontrada em {elapsed:.3f}s: RTX 4090 @ $0.45/hr (TH)", "SUCCESS")
        time.sleep(0.3)

        # PASSO 2: Provisionar
        self.log("PASSO 2: Provisionando nova GPU...", "PHASE")
        time.sleep(0.3)

        start = time.time()
        self.log("  Enviando requisição para Vast.ai...", "INFO")
        time.sleep(0.3)
        self.log("  Nova GPU ID: 888888", "SUCCESS")
        self.log("  Status: provisioning → running", "SUCCESS")
        elapsed = time.time() - start
        self.log(f"  ✓ Provisionada em {elapsed:.3f}s", "SUCCESS")
        time.sleep(0.3)

        # PASSO 3: Aguardar SSH
        self.log("PASSO 3: Aguardando SSH ficar pronto...", "PHASE")
        time.sleep(0.3)

        start = time.time()
        for wait_cycle in range(1, 4):
            self.log(f"  Tentativa {wait_cycle}: Verificando SSH...", "INFO")
            time.sleep(0.2)
        self.log("  SSH Pronto! (gpu-new.vastai.com:54321)", "SUCCESS")
        elapsed = time.time() - start
        self.log(f"  ✓ SSH pronto em {elapsed:.3f}s", "SUCCESS")
        time.sleep(0.3)

        # PASSO 4: Restaurar dados
        self.log("PASSO 4: Restaurando dados (CPU → nova GPU)...", "PHASE")
        time.sleep(0.3)

        start = time.time()
        self.log("  Iniciando rsync CPU → GPU...", "INFO")
        time.sleep(0.1)
        self.log("    /workspace: 1.2 GB", "METRIC")
        time.sleep(0.1)
        self.log("    model.pt: 950 MB", "METRIC")
        time.sleep(0.1)
        self.log("    data.csv: 240 MB", "METRIC")
        time.sleep(0.2)
        self.log("  ✓ Rsync completo!", "SUCCESS")
        elapsed = time.time() - start
        self.log(f"  ✓ Dados restaurados em {elapsed:.3f}s", "SUCCESS")
        time.sleep(0.3)

        # PASSO 5: Retomar sincronização
        self.log("PASSO 5: Retomando sincronização GPU → CPU...", "PHASE")
        time.sleep(0.3)
        self.log("  ✓ Sincronização GPU → CPU retomada", "SUCCESS")
        self.log("  ✓ Sistema volta a SYNCING (GPU saudável)", "SUCCESS")
        time.sleep(0.3)

        self.log("✅ Auto-recovery completo!", "SUCCESS")
        self.print_state()

    def phase_recovery_complete(self):
        """Fase 7: Recovery completo"""
        self.print_header("FASE 7: SISTEMA RECUPERADO")
        self.current_phase = SimulationPhase.RECOVERY_COMPLETE

        self.gpu_status = "RUNNING"

        self.log("🎉 SISTEMA COMPLETAMENTE RECUPERADO!", "SUCCESS")
        time.sleep(0.5)

        self.log("Status Final:", "PHASE")
        time.sleep(0.2)
        self.log(f"  GPU Principal: {self.gpu_status} (Nova: ID 888888)", "SUCCESS")
        time.sleep(0.2)
        self.log(f"  CPU Standby: {self.cpu_status} (Pronto para failover)", "SUCCESS")
        time.sleep(0.2)
        self.log(f"  Sincronização: ATIVA (30s interval)", "SUCCESS")
        time.sleep(0.3)

        self.log("Dados e Estado:", "PHASE")
        time.sleep(0.2)
        self.log(f"  ✓ Workspace: Completo e atualizado", "SUCCESS")
        time.sleep(0.2)
        self.log(f"  ✓ Consistência: OK (verificado)", "SUCCESS")
        time.sleep(0.2)
        self.log(f"  ✓ Nenhum dado perdido", "SUCCESS")
        time.sleep(0.3)

        self.print_state()

    def generate_report(self):
        """Gera relatório de performance"""
        print("\n" + "="*90)
        print("  RELATÓRIO DE PERFORMANCE".center(90))
        print("="*90 + "\n")

        # Tempos das fases
        phase_times = {}
        for i, data in enumerate(self.performance_data):
            phase_key = data.phase.value
            if phase_key not in phase_times:
                phase_times[phase_key] = {
                    'start': data.timestamp,
                    'end': data.timestamp,
                    'events': 0
                }
            else:
                phase_times[phase_key]['end'] = data.timestamp
            phase_times[phase_key]['events'] += 1

        print("📊 DURAÇÃO POR FASE:")
        total_duration = 0
        for phase in [e.value for e in SimulationPhase]:
            if phase in phase_times:
                data = phase_times[phase]
                duration = data['end'] - data['start']
                total_duration += duration
                print(f"  {phase:25s}: {duration:6.2f}s ({data['events']:3d} eventos)")

        print(f"\n  {'TOTAL':25s}: {total_duration:6.2f}s")

        # Eventos críticos
        print("\n⏱️  EVENTOS CRÍTICOS:")
        critical_events = [
            ("GPU OFFLINE", "Falha detectada"),
            ("FAILOVER AUTOMÁTICO ACIONADO", "Failover ativado"),
            ("PASSO 1: Buscando GPU", "Recovery iniciado"),
            ("PASSO 4: Restaurando dados", "Restauração iniciada"),
            ("Auto-recovery completo", "Recovery concluído"),
        ]

        for event_substring, label in critical_events:
            for data in self.performance_data:
                if event_substring in data.event:
                    print(f"  {label:30s}: T{data.timestamp:6.2f}s")
                    break

        # Operações
        print(f"\n📈 OPERAÇÕES REALIZADAS:")
        print(f"  Sincronizações (GPU → CPU): {self.sync_operations}")
        print(f"  Health checks: {self.gpu_health_checks + self.gpu_failures}")
        print(f"  Falhas detectadas: {self.gpu_failures}")

        # Timeline visual
        print(f"\n📋 TIMELINE VISUAL:")
        timeline_data = [
            ("Operação Normal", 0, 2.5, "🟢"),
            ("GPU Falha + Detecção", 2.5, 3.5, "🔴"),
            ("Failover", 3.5, 4.0, "🔶"),
            ("Auto-Recovery", 4.0, 6.0, "🟡"),
            ("Sistema Recuperado", 6.0, 6.5, "🟢"),
        ]

        for label, start, end, emoji in timeline_data:
            bar_length = int((end - start) * 20)
            bar = "█" * bar_length
            print(f"  {emoji} {label:25s} {bar:20s} {start:.1f}s → {end:.1f}s")

        print("\n" + "="*90)

    def run(self):
        """Executa simulação completa"""
        self.print_header("SIMULADOR DE FAILOVER AUTOMÁTICO - CPU STANDBY")
        self.log("Iniciando simulação...", "PHASE")

        try:
            self.phase_setup()
            time.sleep(1)

            self.phase_normal_operation()
            time.sleep(1)

            self.phase_gpu_failure()
            time.sleep(1)

            self.phase_failover_detection()
            time.sleep(1)

            self.phase_failover_activation()
            time.sleep(1)

            self.phase_auto_recovery()
            time.sleep(1)

            self.phase_recovery_complete()
            time.sleep(1)

            self.generate_report()

        except KeyboardInterrupt:
            print("\n\n❌ Simulação interrompida pelo usuário.")
            sys.exit(1)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Simulador de Failover Automático com CPU Standby"
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Modo silencioso (sem output detalhado)'
    )

    args = parser.parse_args()

    simulator = FailoverSimulator(verbose=not args.quiet)
    simulator.run()


if __name__ == '__main__':
    main()
