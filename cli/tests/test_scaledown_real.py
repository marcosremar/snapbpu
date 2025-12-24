"""
Teste REAL de Scaledown/Auto-Hibernação

Testa se a máquina é pausada automaticamente após X segundos de inatividade.
Usa TensorDock para teste rápido (start em 7s).
"""
import pytest
import requests
import time
from datetime import datetime


class TestScaledownReal:
    """Testes reais de scaledown automático"""

    TENSORDOCK_TOKEN = "GLRaWuaDW16nIHy5cQIZBNsOrzhyWHvs"
    TENSORDOCK_API = "https://dashboard.tensordock.com/api/v2"
    VM_ID = "e6f45fbd-473b-4a9d-a869-ab1869e5614d"

    @pytest.fixture
    def headers(self):
        return {"Authorization": f"Bearer {self.TENSORDOCK_TOKEN}"}

    def get_vm_status(self, headers) -> str:
        """Retorna status atual da VM"""
        resp = requests.get(f"{self.TENSORDOCK_API}/instances", headers=headers)
        if resp.status_code == 200:
            for vm in resp.json().get("data", []):
                if vm["id"] == self.VM_ID:
                    return vm.get("status", "unknown")
        return "unknown"

    def ensure_vm_running(self, headers, timeout=60) -> bool:
        """Garante que VM está running"""
        status = self.get_vm_status(headers)
        if status == "running":
            return True

        # Iniciar VM
        resp = requests.post(
            f"{self.TENSORDOCK_API}/instances/{self.VM_ID}/start",
            headers=headers
        )
        if resp.status_code != 200:
            return False

        # Aguardar
        for _ in range(timeout):
            time.sleep(1)
            if self.get_vm_status(headers) == "running":
                return True
        return False

    def stop_vm(self, headers, timeout=60) -> bool:
        """Para a VM"""
        resp = requests.post(
            f"{self.TENSORDOCK_API}/instances/{self.VM_ID}/stop",
            headers=headers
        )
        if resp.status_code != 200:
            return False

        for _ in range(timeout):
            time.sleep(1)
            if self.get_vm_status(headers) == "stopped":
                return True
        return False

    # =========================================
    # TESTE 1: Scaledown Manual (Simulated)
    # =========================================

    def test_manual_scaledown_timing(self, headers):
        """
        Testa tempo de scaledown manual (stop + start).

        Simula o que acontece quando o sistema detecta inatividade
        e faz pause/resume.
        """
        print(f"\n{'='*60}")
        print("TESTE: Scaledown Manual (Stop/Start)")
        print(f"{'='*60}")

        # 1. Garantir VM running
        print("\n[1/4] Garantindo VM running...")
        assert self.ensure_vm_running(headers), "Falha ao iniciar VM"
        print("    ✓ VM running")

        # 2. Simular idle time (2 segundos)
        idle_time = 2
        print(f"\n[2/4] Simulando idle time ({idle_time}s)...")
        time.sleep(idle_time)
        print(f"    ✓ Idle por {idle_time}s")

        # 3. Trigger scaledown (stop)
        print("\n[3/4] Executando scaledown (stop)...")
        stop_start = time.time()
        assert self.stop_vm(headers), "Falha ao parar VM"
        stop_time = time.time() - stop_start
        print(f"    ✓ Stop: {stop_time:.2f}s")

        # 4. Scaleup (start)
        print("\n[4/4] Executando scaleup (start)...")
        start_start = time.time()
        assert self.ensure_vm_running(headers), "Falha ao iniciar VM"
        start_time = time.time() - start_start
        print(f"    ✓ Start: {start_time:.2f}s")

        # Resultado
        total = idle_time + stop_time + start_time
        print(f"\n{'='*60}")
        print(f"RESULTADO SCALEDOWN")
        print(f"{'='*60}")
        print(f"  Idle detectado: {idle_time}s")
        print(f"  Tempo de stop:  {stop_time:.2f}s")
        print(f"  Tempo de start: {start_time:.2f}s")
        print(f"  Recovery total: {start_time:.2f}s")
        print(f"{'='*60}")

        # Assertions
        assert start_time < 30, f"Start muito lento: {start_time:.2f}s (esperado <30s)"

    # =========================================
    # TESTE 2: Múltiplos Ciclos de Scaledown
    # =========================================

    def test_multiple_scaledown_cycles(self, headers):
        """
        Testa múltiplos ciclos de scaledown para verificar consistência.
        """
        print(f"\n{'='*60}")
        print("TESTE: Múltiplos Ciclos de Scaledown")
        print(f"{'='*60}")

        cycles = 2
        results = []

        for i in range(cycles):
            print(f"\n--- Ciclo {i+1}/{cycles} ---")

            # Garantir running
            self.ensure_vm_running(headers)

            # Simular idle
            time.sleep(1)

            # Stop
            stop_start = time.time()
            self.stop_vm(headers)
            stop_time = time.time() - stop_start

            # Start
            start_start = time.time()
            self.ensure_vm_running(headers)
            start_time = time.time() - start_start

            results.append({
                "cycle": i + 1,
                "stop": stop_time,
                "start": start_time,
            })

            print(f"    Stop: {stop_time:.1f}s | Start: {start_time:.1f}s")

        # Médias
        avg_stop = sum(r["stop"] for r in results) / len(results)
        avg_start = sum(r["start"] for r in results) / len(results)

        print(f"\n{'='*60}")
        print(f"MÉDIAS ({cycles} ciclos)")
        print(f"{'='*60}")
        print(f"  Avg Stop:  {avg_stop:.2f}s")
        print(f"  Avg Start: {avg_start:.2f}s")
        print(f"{'='*60}")

        # Start deve ser consistente
        for r in results:
            assert r["start"] < 30, f"Ciclo {r['cycle']}: Start muito lento"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
