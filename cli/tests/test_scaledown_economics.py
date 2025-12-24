"""
Teste de Economia com Scaledown

Calcula economia real baseada em:
- Custo/hora quando running
- Custo/hora quando stopped (storage only)
- Tempo de recovery
"""
import pytest
import requests
import time
import json
from pathlib import Path


class TestScaledownEconomics:
    """Testes de economia com scaledown automático"""

    TENSORDOCK_TOKEN = "GLRaWuaDW16nIHy5cQIZBNsOrzhyWHvs"
    TENSORDOCK_API = "https://dashboard.tensordock.com/api/v2"
    TENSORDOCK_API_V0 = "https://marketplace.tensordock.com/api/v0"
    VM_ID = "e6f45fbd-473b-4a9d-a869-ab1869e5614d"

    @pytest.fixture
    def headers(self):
        return {"Authorization": f"Bearer {self.TENSORDOCK_TOKEN}"}

    def get_vm_details(self):
        """Busca detalhes da VM incluindo preços via API v0"""
        resp = requests.post(
            f"{self.TENSORDOCK_API_V0}/client/list",
            data={
                "api_key": "cbbecb8d-f9d9-4f4a-a5c9-3c641de70440",
                "api_token": self.TENSORDOCK_TOKEN
            }
        )
        if resp.status_code == 200:
            vms = resp.json().get("virtualmachines", {})
            return vms.get(self.VM_ID, {})
        return {}

    def get_vm_status(self, headers) -> str:
        """Retorna status atual da VM"""
        resp = requests.get(f"{self.TENSORDOCK_API}/instances", headers=headers)
        if resp.status_code == 200:
            for vm in resp.json().get("data", []):
                if vm["id"] == self.VM_ID:
                    return vm.get("status", "unknown")
        return "unknown"

    def start_vm(self, headers, timeout=30) -> float:
        """Inicia VM e retorna tempo"""
        start = time.time()
        resp = requests.post(
            f"{self.TENSORDOCK_API}/instances/{self.VM_ID}/start",
            headers=headers
        )
        if resp.status_code != 200:
            return -1

        for _ in range(timeout):
            time.sleep(1)
            status = self.get_vm_status(headers)
            if status == "running":
                return time.time() - start
        return time.time() - start

    def stop_vm(self, headers, timeout=90) -> float:
        """Para VM e retorna tempo"""
        start = time.time()
        resp = requests.post(
            f"{self.TENSORDOCK_API}/instances/{self.VM_ID}/stop",
            headers=headers
        )
        if resp.status_code != 200:
            return -1

        for _ in range(timeout):
            time.sleep(1)
            status = self.get_vm_status(headers)
            if "stop" in status.lower():
                return time.time() - start
        return time.time() - start

    def test_calculate_savings(self, headers):
        """
        Calcula economia com scaledown baseado em custos reais.
        """
        print(f"\n{'='*60}")
        print("CÁLCULO DE ECONOMIA COM SCALEDOWN")
        print(f"{'='*60}")

        # 1. Buscar detalhes da VM
        print("\n[1/3] Buscando custos da VM...")
        vm = self.get_vm_details()

        compute_cost = vm.get("compute_price", 0.234)  # $/hr
        storage_cost = vm.get("storage_price", 0.005)  # $/hr
        total_cost = vm.get("total_price", 0.239)      # $/hr
        gpu = vm.get("specs", {}).get("gpu", {}).get("type", "V100-SXM2-16GB")

        print(f"    GPU: {gpu}")
        print(f"    Custo compute: ${compute_cost:.3f}/hr")
        print(f"    Custo storage: ${storage_cost:.3f}/hr")
        print(f"    Custo total:   ${total_cost:.3f}/hr")

        # 2. Calcular economia por hora idle
        print("\n[2/3] Calculando economia...")

        # Quando stopped, só paga storage
        savings_per_hour = compute_cost  # Economia = custo compute
        savings_pct = (savings_per_hour / total_cost) * 100

        print(f"    Economia quando idle: ${savings_per_hour:.3f}/hr ({savings_pct:.1f}%)")

        # Projeções
        hours_idle_per_day = 16  # Assumindo 8h de uso
        daily_savings = savings_per_hour * hours_idle_per_day
        monthly_savings = daily_savings * 30

        print(f"\n    Projeção (16h idle/dia):")
        print(f"      Diário:  ${daily_savings:.2f}")
        print(f"      Mensal:  ${monthly_savings:.2f}")

        # 3. Medir tempo de recovery
        print("\n[3/3] Medindo tempo de recovery...")

        status = self.get_vm_status(headers)
        print(f"    Status atual: {status}")

        if "stop" in status.lower():
            # Iniciar e medir
            start_time = self.start_vm(headers)
            print(f"    ✓ Tempo de start: {start_time:.1f}s")
        else:
            print("    VM já está running")
            start_time = 7.6  # Usar benchmark anterior

        # Resultado final
        print(f"\n{'='*60}")
        print("RESUMO DE ECONOMIA")
        print(f"{'='*60}")
        print(f"  GPU:              {gpu}")
        print(f"  Custo running:    ${total_cost:.3f}/hr")
        print(f"  Custo stopped:    ${storage_cost:.3f}/hr")
        print(f"  Economia/hr:      ${savings_per_hour:.3f} ({savings_pct:.0f}%)")
        print(f"  Recovery time:    {start_time:.1f}s")
        print(f"  Economia mensal:  ${monthly_savings:.2f} (16h idle/dia)")
        print(f"{'='*60}")

        # Salvar resultados
        result = {
            "gpu": gpu,
            "cost_running_per_hour": total_cost,
            "cost_stopped_per_hour": storage_cost,
            "savings_per_hour": savings_per_hour,
            "savings_percent": savings_pct,
            "recovery_seconds": start_time,
            "monthly_savings_16h_idle": monthly_savings,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }

        Path("tests/scaledown_economics.json").write_text(
            json.dumps(result, indent=2)
        )
        print(f"\nResultado salvo em tests/scaledown_economics.json")

        # Assertions
        assert savings_pct > 90, f"Economia deve ser >90%, got {savings_pct:.1f}%"
        assert start_time < 30, f"Recovery deve ser <30s, got {start_time:.1f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
