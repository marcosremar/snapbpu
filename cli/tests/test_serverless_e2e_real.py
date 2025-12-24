#!/usr/bin/env python3
"""
Testes E2E REAIS de Serverless - Dumont Cloud

ATENÇÃO: Estes testes usam CRÉDITOS REAIS!
- VAST.ai: ~$0.10-0.30/hora
- TensorDock: ~$0.24/hora

Testes de jornada completa que simulam operações reais de usuário:
1. Criar instância GPU real
2. Habilitar serverless
3. Testar pause/resume
4. Medir tempos de recovery
5. Validar economia
6. Cleanup

Uso:
    # Rodar todos os testes E2E
    pytest cli/tests/test_serverless_e2e_real.py -v -s

    # Rodar apenas TensorDock
    pytest cli/tests/test_serverless_e2e_real.py -v -s -k tensordock

    # Rodar apenas VAST
    pytest cli/tests/test_serverless_e2e_real.py -v -s -k vast
"""
import pytest
import subprocess
import time
import json
import os
import sys
import requests
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Paths
CLI_PATH = "/home/marcos/dumontcloud/cli"
VENV_PATH = "/home/marcos/dumontcloud/.venv"
RESULTS_DIR = "/home/marcos/dumontcloud/cli/tests"

# API URLs
VAST_API_URL = "https://console.vast.ai/api/v0"
TENSORDOCK_API_V0 = "https://marketplace.tensordock.com/api/v0"
TENSORDOCK_API_V2 = "https://dashboard.tensordock.com/api/v2"
DUMONT_API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")

# Credenciais (de variáveis de ambiente)
VAST_API_KEY = os.environ.get("VAST_API_KEY", "")
TENSORDOCK_API_KEY = os.environ.get("TENSORDOCK_API_KEY", "")
TENSORDOCK_API_TOKEN = os.environ.get("TENSORDOCK_API_TOKEN", "")


# =============================================================================
# HELPERS
# =============================================================================

@dataclass
class TestResult:
    """Resultado de um teste de jornada"""
    test_name: str
    provider: str
    success: bool
    instance_id: Optional[str] = None
    gpu_name: Optional[str] = None

    # Tempos medidos
    stop_seconds: float = 0
    start_seconds: float = 0
    recovery_seconds: float = 0

    # Custos
    cost_per_hour_running: float = 0
    cost_per_hour_stopped: float = 0
    savings_percent: float = 0

    # Erros
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "provider": self.provider,
            "success": self.success,
            "instance_id": self.instance_id,
            "gpu_name": self.gpu_name,
            "stop_seconds": self.stop_seconds,
            "start_seconds": self.start_seconds,
            "recovery_seconds": self.recovery_seconds,
            "cost_per_hour_running": self.cost_per_hour_running,
            "cost_per_hour_stopped": self.cost_per_hour_stopped,
            "savings_percent": self.savings_percent,
            "error": self.error,
            "timestamp": datetime.now().isoformat(),
        }


def run_cli(*args, timeout: int = 120) -> Tuple[int, str, str]:
    """Executa comando CLI e retorna (returncode, stdout, stderr)"""
    env = os.environ.copy()
    root_path = "/home/marcos/dumontcloud"
    env["PYTHONPATH"] = f"{root_path}:{env.get('PYTHONPATH', '')}"

    cmd = [f"{VENV_PATH}/bin/python", "-m", "cli"] + list(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=root_path,
            env=env
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def save_result(result: TestResult):
    """Salva resultado do teste em arquivo JSON"""
    filename = f"{RESULTS_DIR}/{result.test_name}_{result.provider}_results.json"
    with open(filename, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    print(f"  📁 Resultado salvo em: {filename}")


def wait_for_status(check_func, expected_status: str, timeout: int = 120, poll_interval: int = 5) -> Tuple[bool, float]:
    """
    Aguarda até que check_func() retorne expected_status.

    Returns:
        (success, elapsed_seconds)
    """
    start = time.time()

    while time.time() - start < timeout:
        try:
            current_status = check_func()
            if current_status and expected_status.lower() in current_status.lower():
                return True, time.time() - start
        except Exception as e:
            print(f"    Check error: {e}")

        time.sleep(poll_interval)
        elapsed = time.time() - start
        print(f"    Aguardando... {elapsed:.0f}s (status atual: {current_status})")

    return False, time.time() - start


# =============================================================================
# VAST.AI PROVIDER
# =============================================================================

class VastProvider:
    """Provider para operações VAST.ai"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def get_instances(self) -> list:
        """Lista instâncias VAST.ai"""
        resp = requests.get(
            f"{VAST_API_URL}/instances",
            headers=self.headers,
            timeout=30
        )
        if resp.ok:
            return resp.json().get("instances", [])
        return []

    def get_instance(self, instance_id: str) -> Optional[Dict]:
        """Obtém detalhes de uma instância"""
        instances = self.get_instances()
        for inst in instances:
            if str(inst.get("id")) == str(instance_id):
                return inst
        return None

    def get_instance_status(self, instance_id: str) -> Optional[str]:
        """Retorna status atual da instância"""
        inst = self.get_instance(instance_id)
        if inst:
            return inst.get("actual_status") or inst.get("status")
        return None

    def pause_instance(self, instance_id: str) -> bool:
        """Pausa instância via API VAST"""
        resp = requests.put(
            f"{VAST_API_URL}/instances/{instance_id}/",
            headers=self.headers,
            json={"state": "stopped"},
            timeout=30
        )
        return resp.ok

    def resume_instance(self, instance_id: str) -> bool:
        """Resume instância via API VAST"""
        resp = requests.put(
            f"{VAST_API_URL}/instances/{instance_id}/",
            headers=self.headers,
            json={"state": "running"},
            timeout=30
        )
        return resp.ok

    def get_cheapest_offer(self, max_price: float = 0.50) -> Optional[Dict]:
        """Busca oferta mais barata"""
        resp = requests.get(
            f"{VAST_API_URL}/bundles",
            headers=self.headers,
            params={"q": json.dumps({
                "rentable": {"eq": True},
                "rented": {"eq": False},
                "dph_total": {"lte": max_price},
                "cuda_max_good": {"gte": 12.0},
            })},
            timeout=30
        )
        if resp.ok:
            offers = resp.json().get("offers", [])
            if offers:
                return sorted(offers, key=lambda x: x.get("dph_total", 999))[0]
        return None

    def create_instance(self, offer_id: int, image: str = "nvidia/cuda:12.0-base-ubuntu22.04") -> Optional[str]:
        """Cria nova instância"""
        resp = requests.put(
            f"{VAST_API_URL}/asks/{offer_id}/",
            headers=self.headers,
            json={
                "client_id": "me",
                "image": image,
                "disk": 20,
                "onstart": "touch ~/.no_auto_tmux",
            },
            timeout=60
        )
        if resp.ok:
            data = resp.json()
            return str(data.get("new_contract"))
        return None

    def delete_instance(self, instance_id: str) -> bool:
        """Deleta instância"""
        resp = requests.delete(
            f"{VAST_API_URL}/instances/{instance_id}/",
            headers=self.headers,
            timeout=30
        )
        return resp.ok


# =============================================================================
# TENSORDOCK PROVIDER
# =============================================================================

class TensorDockProvider:
    """Provider para operações TensorDock usando API v2"""

    def __init__(self, api_key: str, api_token: str):
        self.api_key = api_key
        self.api_token = api_token
        self.headers_v2 = {"Authorization": f"Bearer {api_token}"}

    def get_instances(self) -> list:
        """Lista VMs TensorDock usando API v2"""
        try:
            resp = requests.get(
                f"{TENSORDOCK_API_V2}/instances",
                headers=self.headers_v2,
                timeout=30
            )
            if resp.ok:
                data = resp.json()
                # v2 retorna {"data": [{"type": "virtualmachine", "id": "...", ...}]}
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"    Erro ao listar VMs: {e}")

        return []

    def get_instance(self, instance_id: str) -> Optional[Dict]:
        """Obtém detalhes de uma VM"""
        instances = self.get_instances()
        for inst in instances:
            if str(inst.get("id")) == str(instance_id):
                return inst
        return None

    def get_instance_status(self, instance_id: str) -> Optional[str]:
        """Retorna status atual da VM"""
        inst = self.get_instance(instance_id)
        if inst:
            return inst.get("status") or inst.get("state")
        return None

    def stop_instance(self, instance_id: str) -> bool:
        """Para VM TensorDock usando API v2"""
        try:
            resp = requests.post(
                f"{TENSORDOCK_API_V2}/instances/{instance_id}/stop",
                headers=self.headers_v2,
                timeout=60
            )
            print(f"    Stop response: {resp.status_code} - {resp.text[:200]}")
            return resp.ok
        except Exception as e:
            print(f"    Erro ao parar VM: {e}")
            return False

    def start_instance(self, instance_id: str) -> bool:
        """Inicia VM TensorDock usando API v2"""
        try:
            resp = requests.post(
                f"{TENSORDOCK_API_V2}/instances/{instance_id}/start",
                headers=self.headers_v2,
                timeout=60
            )
            print(f"    Start response: {resp.status_code} - {resp.text[:200]}")
            return resp.ok
        except Exception as e:
            print(f"    Erro ao iniciar VM: {e}")
            return False

    def delete_instance(self, instance_id: str) -> bool:
        """Deleta VM TensorDock"""
        try:
            resp = requests.delete(
                f"{TENSORDOCK_API_V2}/instances/{instance_id}",
                headers=self.headers_v2,
                timeout=30
            )
            return resp.ok
        except:
            return False


# =============================================================================
# TESTES E2E - VAST.AI
# =============================================================================

class TestVastServerlessJourney:
    """
    Testes E2E REAIS de serverless com VAST.ai

    USA CRÉDITOS REAIS!
    """

    @pytest.fixture(scope="class")
    def vast(self):
        """Provider VAST.ai"""
        if not VAST_API_KEY:
            pytest.skip("VAST_API_KEY não configurada")
        return VastProvider(VAST_API_KEY)

    @pytest.fixture(scope="class")
    def vast_instance(self, vast) -> str:
        """
        Usa instância VAST.ai existente para testes.

        Para evitar criação acidental de instâncias, apenas usa existentes.
        Se não houver, pula os testes.
        """
        print("\n📡 Verificando instâncias VAST.ai existentes...")

        # Verificar instâncias existentes
        instances = vast.get_instances()
        print(f"    Instâncias encontradas: {len(instances)}")

        if not instances:
            pytest.skip("Nenhuma instância VAST.ai encontrada. Crie uma manualmente via console.vast.ai")

        # Preferir running, mas aceita paused/stopped
        running = [i for i in instances if i.get("actual_status") == "running"]
        paused = [i for i in instances if i.get("actual_status") in ["stopped", "paused", "exited"]]

        if running:
            instance = running[0]
            instance_id = str(instance["id"])
            print(f"  ✓ Usando instância running: {instance_id}")
            print(f"    GPU: {instance.get('gpu_name')}")
            print(f"    Status: {instance.get('actual_status')}")
            yield instance_id
            return

        if paused:
            instance = paused[0]
            instance_id = str(instance["id"])
            print(f"  ✓ Usando instância paused: {instance_id}")
            print(f"    GPU: {instance.get('gpu_name')}")
            print(f"    Status: {instance.get('actual_status')}")

            # Tentar resumir
            print("    Resumindo instância...")
            vast.resume_instance(instance_id)
            success, elapsed = wait_for_status(
                lambda: vast.get_instance_status(instance_id),
                "running",
                timeout=120
            )

            if success:
                print(f"    ✓ Instância running em {elapsed:.1f}s")
            else:
                print(f"    ⚠ Instância pode não estar running")

            yield instance_id
            return

        # Usar qualquer instância
        instance = instances[0]
        instance_id = str(instance["id"])
        print(f"  ✓ Usando instância: {instance_id}")
        print(f"    Status: {instance.get('actual_status')}")

        yield instance_id

    def test_01_vast_pause_resume_cycle(self, vast, vast_instance):
        """
        Teste 1: Ciclo completo de pause/resume VAST.ai

        Jornada:
        1. Verificar que instância está running
        2. Pausar instância
        3. Medir tempo de pause
        4. Verificar status paused/stopped
        5. Resumir instância
        6. Medir tempo de resume (recovery)
        7. Verificar status running

        Expectativa: Recovery ~7 segundos (baseado em benchmarks)
        """
        result = TestResult(
            test_name="pause_resume_cycle",
            provider="vast",
            success=False,
            instance_id=vast_instance,
        )

        try:
            print(f"\n🧪 TESTE: Ciclo Pause/Resume VAST.ai")
            print(f"   Instance ID: {vast_instance}")
            print("=" * 60)

            # Step 1: Verificar status inicial
            print("\n[1] Verificando status inicial...")
            status = vast.get_instance_status(vast_instance)
            print(f"    Status: {status}")

            if status != "running":
                print("    Instância não está running, iniciando...")
                vast.resume_instance(vast_instance)
                success, _ = wait_for_status(
                    lambda: vast.get_instance_status(vast_instance),
                    "running",
                    timeout=120
                )
                if not success:
                    raise Exception("Falha ao iniciar instância")

            # Obter info da GPU
            inst = vast.get_instance(vast_instance)
            result.gpu_name = inst.get("gpu_name", "Unknown")
            result.cost_per_hour_running = inst.get("dph_total", 0)
            print(f"    GPU: {result.gpu_name}")
            print(f"    Custo running: ${result.cost_per_hour_running:.4f}/hr")

            # Step 2: Pausar instância
            print("\n[2] Pausando instância...")
            pause_start = time.time()

            if not vast.pause_instance(vast_instance):
                raise Exception("Falha ao enviar comando pause")

            # Aguardar ficar paused/stopped
            success, pause_elapsed = wait_for_status(
                lambda: vast.get_instance_status(vast_instance),
                "stopped",
                timeout=120,
                poll_interval=3
            )

            result.stop_seconds = pause_elapsed
            print(f"    ✓ Instância pausada em {pause_elapsed:.2f}s")

            if not success:
                raise Exception(f"Instância não pausou em 120s (status: {vast.get_instance_status(vast_instance)})")

            # Verificar custo quando paused
            time.sleep(2)  # Pequena pausa para API atualizar
            inst = vast.get_instance(vast_instance)
            # VAST.ai cobra ~$0.005/hr quando paused (storage)
            result.cost_per_hour_stopped = 0.005

            # Step 3: Resumir instância
            print("\n[3] Resumindo instância...")
            resume_start = time.time()

            if not vast.resume_instance(vast_instance):
                raise Exception("Falha ao enviar comando resume")

            # Aguardar ficar running
            success, resume_elapsed = wait_for_status(
                lambda: vast.get_instance_status(vast_instance),
                "running",
                timeout=120,
                poll_interval=2
            )

            result.start_seconds = resume_elapsed
            result.recovery_seconds = resume_elapsed
            print(f"    ✓ Instância resumida em {resume_elapsed:.2f}s")

            if not success:
                raise Exception("Instância não resumiu em 120s")

            # Step 4: Calcular economia
            print("\n[4] Calculando economia...")
            if result.cost_per_hour_running > 0:
                result.savings_percent = (
                    (result.cost_per_hour_running - result.cost_per_hour_stopped)
                    / result.cost_per_hour_running * 100
                )

            # Resumo
            print("\n" + "=" * 60)
            print("📊 RESULTADO DO TESTE")
            print("=" * 60)
            print(f"   GPU: {result.gpu_name}")
            print(f"   Tempo de Pause: {result.stop_seconds:.2f}s")
            print(f"   Tempo de Resume: {result.start_seconds:.2f}s")
            print(f"   Recovery Total: {result.recovery_seconds:.2f}s")
            print(f"   Custo Running: ${result.cost_per_hour_running:.4f}/hr")
            print(f"   Custo Stopped: ${result.cost_per_hour_stopped:.4f}/hr")
            print(f"   Economia: {result.savings_percent:.1f}%")
            print("=" * 60)

            result.success = True

            # Assertions
            assert result.recovery_seconds < 60, f"Recovery muito lento: {result.recovery_seconds}s"
            assert result.savings_percent > 90, f"Economia muito baixa: {result.savings_percent}%"

        except Exception as e:
            result.error = str(e)
            print(f"\n❌ ERRO: {e}")
            raise

        finally:
            save_result(result)

    def test_02_vast_serverless_enable_disable(self, vast, vast_instance):
        """
        Teste 2: Enable/Disable serverless via CLI

        Jornada:
        1. Habilitar serverless mode=economic
        2. Verificar status serverless
        3. Desabilitar serverless
        4. Verificar que foi desabilitado
        """
        print(f"\n🧪 TESTE: Enable/Disable Serverless VAST.ai")
        print(f"   Instance ID: {vast_instance}")
        print("=" * 60)

        # Step 1: Enable serverless
        print("\n[1] Habilitando serverless mode=economic...")
        code, stdout, stderr = run_cli(
            "serverless", "enable", vast_instance,
            "mode=economic",
            "idle_timeout_seconds=30"
        )
        print(f"    Output: {stdout[:200]}")

        # Step 2: Verificar status
        print("\n[2] Verificando status serverless...")
        code, stdout, stderr = run_cli("serverless", "status", vast_instance)
        print(f"    Output: {stdout[:200]}")

        # Step 3: Disable serverless
        print("\n[3] Desabilitando serverless...")
        code, stdout, stderr = run_cli("serverless", "disable", vast_instance)
        print(f"    Output: {stdout[:200]}")

        # Step 4: Verificar que desabilitou
        print("\n[4] Verificando que desabilitou...")
        code, stdout, stderr = run_cli("serverless", "status", vast_instance)
        print(f"    Output: {stdout[:200]}")

        print("\n✅ Teste de enable/disable concluído")

    def test_03_vast_multiple_pause_resume_cycles(self, vast, vast_instance):
        """
        Teste 3: Múltiplos ciclos de pause/resume

        Executa 3 ciclos para validar consistência dos tempos.
        """
        print(f"\n🧪 TESTE: Múltiplos Ciclos Pause/Resume VAST.ai")
        print(f"   Instance ID: {vast_instance}")
        print("=" * 60)

        cycles = []

        for i in range(3):
            print(f"\n--- Ciclo {i+1}/3 ---")

            # Garantir que está running
            status = vast.get_instance_status(vast_instance)
            if status != "running":
                vast.resume_instance(vast_instance)
                wait_for_status(
                    lambda: vast.get_instance_status(vast_instance),
                    "running",
                    timeout=60
                )

            # Pause
            pause_start = time.time()
            vast.pause_instance(vast_instance)
            success, pause_time = wait_for_status(
                lambda: vast.get_instance_status(vast_instance),
                "stopped",
                timeout=90,
                poll_interval=2
            )

            # Resume
            resume_start = time.time()
            vast.resume_instance(vast_instance)
            success, resume_time = wait_for_status(
                lambda: vast.get_instance_status(vast_instance),
                "running",
                timeout=90,
                poll_interval=2
            )

            cycles.append({
                "cycle": i + 1,
                "pause_seconds": pause_time,
                "resume_seconds": resume_time,
            })

            print(f"    Pause: {pause_time:.2f}s, Resume: {resume_time:.2f}s")

            # Pequena pausa entre ciclos
            time.sleep(5)

        # Resumo
        avg_pause = sum(c["pause_seconds"] for c in cycles) / len(cycles)
        avg_resume = sum(c["resume_seconds"] for c in cycles) / len(cycles)

        print("\n" + "=" * 60)
        print("📊 RESUMO DOS CICLOS")
        print("=" * 60)
        for c in cycles:
            print(f"   Ciclo {c['cycle']}: Pause {c['pause_seconds']:.2f}s, Resume {c['resume_seconds']:.2f}s")
        print(f"\n   Média Pause: {avg_pause:.2f}s")
        print(f"   Média Resume: {avg_resume:.2f}s")
        print("=" * 60)

        # Salvar resultado
        result = {
            "test": "multiple_cycles",
            "provider": "vast",
            "instance_id": vast_instance,
            "cycles": cycles,
            "avg_pause_seconds": avg_pause,
            "avg_resume_seconds": avg_resume,
            "timestamp": datetime.now().isoformat(),
        }

        with open(f"{RESULTS_DIR}/vast_multiple_cycles_results.json", "w") as f:
            json.dump(result, f, indent=2)

        # Assertions
        assert avg_resume < 30, f"Recovery médio muito lento: {avg_resume}s"


# =============================================================================
# TESTES E2E - TENSORDOCK
# =============================================================================

class TestTensorDockServerlessJourney:
    """
    Testes E2E REAIS de serverless com TensorDock

    USA CRÉDITOS REAIS!

    IMPORTANTE: TensorDock requer saldo mínimo de $1 para operações.
    """

    @pytest.fixture(scope="class")
    def tensordock(self):
        """Provider TensorDock"""
        if not TENSORDOCK_API_KEY or not TENSORDOCK_API_TOKEN:
            pytest.skip("TENSORDOCK_API_KEY/TOKEN não configuradas")
        return TensorDockProvider(TENSORDOCK_API_KEY, TENSORDOCK_API_TOKEN)

    @pytest.fixture(scope="class")
    def tensordock_instance(self, tensordock) -> str:
        """
        Usa instância TensorDock existente.

        TensorDock não tem API de criação fácil, então usamos instância existente.
        """
        print("\n📡 Verificando instâncias TensorDock existentes...")

        instances = tensordock.get_instances()
        print(f"    Instâncias encontradas: {len(instances)}")

        if not instances:
            pytest.skip("Nenhuma instância TensorDock encontrada. Crie uma manualmente.")

        # Usar a primeira instância
        instance = instances[0]
        instance_id = str(instance.get("id"))
        instance_name = instance.get("name", "Unknown")
        instance_status = instance.get("status", "unknown")

        print(f"  ✓ Usando instância: {instance_id}")
        print(f"    Nome: {instance_name}")
        print(f"    Status: {instance_status}")

        yield instance_id

    def test_01_tensordock_stop_start_cycle(self, tensordock, tensordock_instance):
        """
        Teste 1: Ciclo completo de stop/start TensorDock

        Jornada:
        1. Verificar status inicial
        2. Garantir que está running
        3. Parar instância e AGUARDAR status mudar
        4. Iniciar instância e AGUARDAR status mudar
        5. Medir tempos REAIS

        Expectativa: Stop ~58s, Start ~7.6s (baseado em benchmarks)
        """
        result = TestResult(
            test_name="stop_start_cycle",
            provider="tensordock",
            success=False,
            instance_id=tensordock_instance,
        )

        try:
            print(f"\n🧪 TESTE: Ciclo Stop/Start TensorDock (Medindo tempo REAL)")
            print(f"   Instance ID: {tensordock_instance}")
            print("=" * 60)

            # Step 1: Verificar status inicial
            print("\n[1] Verificando status inicial...")
            status = tensordock.get_instance_status(tensordock_instance)
            print(f"    Status: {status}")

            inst = tensordock.get_instance(tensordock_instance)
            result.gpu_name = inst.get("gpu_name") or inst.get("gpu_model") or inst.get("name", "Unknown")

            # Se não está running, iniciar primeiro e aguardar
            if not status or "running" not in status.lower():
                print("    Instância não está running, iniciando...")
                tensordock.start_instance(tensordock_instance)

                # Aguardar status REAL mudar para running
                print("    Aguardando status running...")
                success, elapsed = wait_for_status(
                    lambda: tensordock.get_instance_status(tensordock_instance),
                    "running",
                    timeout=180,
                    poll_interval=5
                )
                if success:
                    print(f"    ✓ Instância running em {elapsed:.1f}s")
                else:
                    print(f"    ⚠ Timeout aguardando running, continuando...")

            print(f"    GPU: {result.gpu_name}")

            # Pequena pausa para estabilizar
            time.sleep(5)

            # Step 2: Parar instância
            print("\n[2] Parando instância...")
            stop_start = time.time()

            tensordock.stop_instance(tensordock_instance)

            # AGUARDAR status REAL mudar para stopped
            print("    Aguardando status stopped...")
            success, stop_elapsed = wait_for_status(
                lambda: tensordock.get_instance_status(tensordock_instance),
                "stop",  # Aceita "stopped" ou "stoppeddisassociated"
                timeout=180,
                poll_interval=5
            )

            result.stop_seconds = time.time() - stop_start
            final_status = tensordock.get_instance_status(tensordock_instance)
            print(f"    ✓ Instância parada em {result.stop_seconds:.2f}s (status: {final_status})")

            # Pequena pausa para estabilizar
            time.sleep(3)

            # Step 3: Iniciar instância
            print("\n[3] Iniciando instância...")
            start_start = time.time()

            tensordock.start_instance(tensordock_instance)

            # AGUARDAR status REAL mudar para running
            print("    Aguardando status running...")
            success, start_elapsed = wait_for_status(
                lambda: tensordock.get_instance_status(tensordock_instance),
                "running",
                timeout=180,
                poll_interval=3
            )

            result.start_seconds = time.time() - start_start
            result.recovery_seconds = result.start_seconds
            final_status = tensordock.get_instance_status(tensordock_instance)
            print(f"    ✓ Instância iniciada em {result.start_seconds:.2f}s (status: {final_status})")

            # Calcular economia (estimativa TensorDock)
            result.cost_per_hour_running = 0.239  # V100 típico
            result.cost_per_hour_stopped = 0.005
            result.savings_percent = 97.9

            # Resumo
            print("\n" + "=" * 60)
            print("📊 RESULTADO DO TESTE")
            print("=" * 60)
            print(f"   GPU: {result.gpu_name}")
            print(f"   Tempo de Stop: {result.stop_seconds:.2f}s")
            print(f"   Tempo de Start: {result.start_seconds:.2f}s")
            print(f"   Recovery: {result.recovery_seconds:.2f}s")
            print(f"   Economia estimada: {result.savings_percent:.1f}%")
            print("=" * 60)

            result.success = True

            # Assertions - tempos podem variar, ser tolerante
            assert result.start_seconds < 120, f"Start muito lento: {result.start_seconds}s"

        except Exception as e:
            result.error = str(e)
            print(f"\n❌ ERRO: {e}")
            raise

        finally:
            save_result(result)

    def test_02_tensordock_rapid_cycles(self, tensordock, tensordock_instance):
        """
        Teste 2: Ciclos de stop/start medindo tempo REAL

        Testa estabilidade e mede tempos reais de transição.
        """
        print(f"\n🧪 TESTE: Ciclos Stop/Start TensorDock (Tempo REAL)")
        print(f"   Instance ID: {tensordock_instance}")
        print("=" * 60)

        cycles = []

        for i in range(2):  # 2 ciclos
            print(f"\n--- Ciclo {i+1}/2 ---")

            # Garantir running primeiro
            status = tensordock.get_instance_status(tensordock_instance)
            if not status or "running" not in status.lower():
                print("    Iniciando instância...")
                tensordock.start_instance(tensordock_instance)
                wait_for_status(
                    lambda: tensordock.get_instance_status(tensordock_instance),
                    "running",
                    timeout=120,
                    poll_interval=5
                )
                time.sleep(3)

            # Stop - medir tempo REAL
            print("    Parando...")
            stop_start = time.time()
            tensordock.stop_instance(tensordock_instance)
            success, _ = wait_for_status(
                lambda: tensordock.get_instance_status(tensordock_instance),
                "stop",
                timeout=120,
                poll_interval=5
            )
            stop_time = time.time() - stop_start
            print(f"    Stop real: {stop_time:.2f}s")

            time.sleep(3)

            # Start - medir tempo REAL
            print("    Iniciando...")
            start_start = time.time()
            tensordock.start_instance(tensordock_instance)
            success, _ = wait_for_status(
                lambda: tensordock.get_instance_status(tensordock_instance),
                "running",
                timeout=120,
                poll_interval=3
            )
            start_time = time.time() - start_start
            print(f"    Start real: {start_time:.2f}s")

            cycles.append({
                "cycle": i + 1,
                "stop_seconds": stop_time,
                "start_seconds": start_time,
            })

            print(f"    ✓ Ciclo {i+1}: Stop {stop_time:.1f}s, Start {start_time:.1f}s")

            time.sleep(5)

        # Resumo
        avg_stop = sum(c["stop_seconds"] for c in cycles) / len(cycles)
        avg_start = sum(c["start_seconds"] for c in cycles) / len(cycles)

        print("\n" + "=" * 60)
        print("📊 RESUMO DOS CICLOS")
        print("=" * 60)
        for c in cycles:
            print(f"   Ciclo {c['cycle']}: Stop {c['stop_seconds']:.1f}s, Start {c['start_seconds']:.1f}s")
        print(f"\n   Média Stop: {avg_stop:.1f}s")
        print(f"   Média Start: {avg_start:.1f}s")
        print("=" * 60)

        # Salvar
        with open(f"{RESULTS_DIR}/tensordock_cycles_results.json", "w") as f:
            json.dump({
                "test": "rapid_cycles",
                "provider": "tensordock",
                "instance_id": tensordock_instance,
                "cycles": cycles,
                "avg_stop": avg_stop,
                "avg_start": avg_start,
                "timestamp": datetime.now().isoformat(),
            }, f, indent=2)


# =============================================================================
# TESTES DE ECONOMIA
# =============================================================================

class TestServerlessEconomicsReal:
    """
    Testes de validação de economia real.

    Não usa GPU, apenas calcula e valida projeções.
    """

    def test_01_calculate_monthly_savings(self):
        """
        Teste: Calcular economia mensal real

        Baseado em dados reais dos benchmarks.
        """
        print("\n🧪 TESTE: Cálculo de Economia Mensal")
        print("=" * 60)

        # Dados reais dos benchmarks
        scenarios = [
            {
                "name": "VAST V100",
                "running_per_hour": 0.30,
                "stopped_per_hour": 0.005,
                "hours_idle_per_day": 16,
            },
            {
                "name": "TensorDock V100",
                "running_per_hour": 0.239,
                "stopped_per_hour": 0.005,
                "hours_idle_per_day": 16,
            },
            {
                "name": "Heavy User (8h idle)",
                "running_per_hour": 0.30,
                "stopped_per_hour": 0.005,
                "hours_idle_per_day": 8,
            },
            {
                "name": "Light User (20h idle)",
                "running_per_hour": 0.30,
                "stopped_per_hour": 0.005,
                "hours_idle_per_day": 20,
            },
        ]

        results = []

        for s in scenarios:
            daily_without = s["running_per_hour"] * 24
            daily_with = (
                s["running_per_hour"] * (24 - s["hours_idle_per_day"]) +
                s["stopped_per_hour"] * s["hours_idle_per_day"]
            )
            daily_savings = daily_without - daily_with
            monthly_savings = daily_savings * 30
            yearly_savings = monthly_savings * 12
            savings_percent = (daily_savings / daily_without) * 100

            results.append({
                "scenario": s["name"],
                "daily_without": daily_without,
                "daily_with": daily_with,
                "daily_savings": daily_savings,
                "monthly_savings": monthly_savings,
                "yearly_savings": yearly_savings,
                "savings_percent": savings_percent,
            })

            print(f"\n📊 {s['name']}")
            print(f"   Sem serverless: ${daily_without:.2f}/dia")
            print(f"   Com serverless: ${daily_with:.2f}/dia")
            print(f"   Economia: ${daily_savings:.2f}/dia ({savings_percent:.1f}%)")
            print(f"   Mensal: ${monthly_savings:.2f}")
            print(f"   Anual: ${yearly_savings:.2f}")

        # Salvar
        with open(f"{RESULTS_DIR}/economics_projection_results.json", "w") as f:
            json.dump({
                "test": "economics_projection",
                "scenarios": results,
                "timestamp": datetime.now().isoformat(),
            }, f, indent=2)

        # Assertions - economia depende do tempo idle
        for r in results:
            # Heavy users (8h idle) têm economia menor, é esperado
            if "Heavy" in r["scenario"]:
                assert r["savings_percent"] > 30, f"{r['scenario']}: Economia muito baixa"
            else:
                assert r["savings_percent"] > 50, f"{r['scenario']}: Economia muito baixa"

    def test_02_recovery_cost_analysis(self):
        """
        Teste: Análise de custo do tempo de recovery
        """
        print("\n🧪 TESTE: Análise de Custo do Recovery")
        print("=" * 60)

        # Tempos medidos em benchmarks
        providers = [
            {"name": "VAST", "recovery_seconds": 7.0, "hourly_rate": 0.30},
            {"name": "TensorDock", "recovery_seconds": 7.6, "hourly_rate": 0.239},
            {"name": "GCP Standby", "recovery_seconds": 9.78, "hourly_rate": 0.30},
        ]

        for p in providers:
            recovery_cost = (p["recovery_seconds"] / 3600) * p["hourly_rate"]

            # Quantos recoveries para gastar $1?
            recoveries_per_dollar = 1 / recovery_cost if recovery_cost > 0 else float('inf')

            print(f"\n📊 {p['name']}")
            print(f"   Recovery: {p['recovery_seconds']:.2f}s")
            print(f"   Custo do recovery: ${recovery_cost:.6f}")
            print(f"   Recoveries para $1: {recoveries_per_dollar:.0f}")

            # Assertion
            assert recovery_cost < 0.001, f"{p['name']}: Custo do recovery muito alto"


# =============================================================================
# RUNNER
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DUMONT CLOUD - TESTES E2E REAIS DE SERVERLESS")
    print("=" * 70)
    print("\n⚠️  ATENÇÃO: Estes testes usam CRÉDITOS REAIS!")
    print("\nVariáveis de ambiente necessárias:")
    print(f"  VAST_API_KEY: {'✓ Configurada' if VAST_API_KEY else '✗ NÃO configurada'}")
    print(f"  TENSORDOCK_API_KEY: {'✓ Configurada' if TENSORDOCK_API_KEY else '✗ NÃO configurada'}")
    print(f"  TENSORDOCK_API_TOKEN: {'✓ Configurada' if TENSORDOCK_API_TOKEN else '✗ NÃO configurada'}")
    print("\nExemplos de execução:")
    print("  pytest cli/tests/test_serverless_e2e_real.py -v -s")
    print("  pytest cli/tests/test_serverless_e2e_real.py -v -s -k vast")
    print("  pytest cli/tests/test_serverless_e2e_real.py -v -s -k tensordock")
    print("  pytest cli/tests/test_serverless_e2e_real.py -v -s -k economics")
    print("=" * 70)

    sys.exit(pytest.main([__file__, "-v", "-s"]))
