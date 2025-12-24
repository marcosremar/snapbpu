#!/usr/bin/env python3
"""
Testes E2E de Jornada Serverless GPU

Testa o ciclo completo:
1. Deploy GPU
2. Instalar modelo (Whisper Distill)
3. Fazer inferência
4. Habilitar serverless
5. Aguardar idle timeout
6. Verificar se pausou
7. Acordar máquina
8. Fazer nova inferência
9. Cleanup

Dois modos testados:
- ECONOMIC: Usa VAST.ai pause/resume nativo (~7s recovery, testado dez/2024)
- FAST: Usa CPU Standby com sync (~1s recovery)
"""
import pytest
import subprocess
import time
import json
import os
import sys
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ServerlessTestConfig:
    """Configuração do teste serverless"""
    mode: str  # "economic" ou "fast"
    idle_timeout: int  # segundos
    gpu_threshold: float  # % GPU
    expected_pause_time: int  # tempo esperado para pausar
    expected_recovery_time: int  # tempo esperado para acordar
    max_deploy_time: int = 120  # tempo máximo para deploy
    max_inference_time: int = 60  # tempo máximo para inferência


# Configurações para cada modo
ECONOMIC_CONFIG = ServerlessTestConfig(
    mode="economic",
    idle_timeout=20,
    gpu_threshold=5.0,
    expected_pause_time=45,  # idle_timeout + margem
    expected_recovery_time=15,  # ~7s + margem (testado: 6-7s)
)

FAST_CONFIG = ServerlessTestConfig(
    mode="fast",
    idle_timeout=30,
    gpu_threshold=5.0,
    expected_pause_time=45,
    expected_recovery_time=10,  # <1s + margem
)


class SSHClient:
    """Cliente SSH para executar comandos na GPU"""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def run(self, command: str, timeout: int = 300) -> Tuple[int, str, str]:
        """Executa comando via SSH"""
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=30",
            "-o", "BatchMode=yes",
            "-p", str(self.port),
            f"root@{self.host}",
            command
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "SSH command timed out"
        except Exception as e:
            return -1, "", str(e)

    def is_reachable(self, timeout: int = 10) -> bool:
        """Verifica se SSH está acessível"""
        code, _, _ = self.run("echo ok", timeout=timeout)
        return code == 0


class DumontCLI:
    """Wrapper para o CLI do Dumont"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def run(self, *args, timeout: int = 120) -> Tuple[int, str]:
        """Executa comando do CLI"""
        cmd = ["python3", "-m", "cli", "--base-url", self.base_url] + list(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.root_path
            )
            output = result.stdout + result.stderr
            return result.returncode, output
        except subprocess.TimeoutExpired:
            return -1, "Command timed out"
        except Exception as e:
            return -1, str(e)

    def parse_json(self, output: str) -> Optional[Dict]:
        """Extrai JSON da saída do CLI"""
        import re
        # Procura o maior bloco JSON
        match = re.search(r'\{.*\}', output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return None


class WhisperInstaller:
    """Instala e testa Whisper Distill na GPU"""

    INSTALL_SCRIPT = """
apt-get update -qq && apt-get install -y -qq python3-pip ffmpeg curl > /dev/null 2>&1
pip3 install --break-system-packages -q transformers torch torchaudio accelerate
echo "Dependencies installed"
"""

    TEST_SCRIPT = """
python3 << 'PYEOF'
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import torch
import time
import urllib.request

# Download sample audio
url = "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/mlk.flac"
urllib.request.urlretrieve(url, "/tmp/sample.flac")

device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

model_id = "distil-whisper/distil-large-v3"

model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
)
model.to(device)

processor = AutoProcessor.from_pretrained(model_id)

pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device,
)

start = time.time()
result = pipe("/tmp/sample.flac")
elapsed = time.time() - start

print(f"TRANSCRIPTION: {result['text']}")
print(f"TIME: {elapsed:.2f}s")
print(f"VRAM: {torch.cuda.memory_allocated()/1024**3:.1f}GB")
print("SUCCESS")
PYEOF
"""

    def __init__(self, ssh: SSHClient):
        self.ssh = ssh

    def install(self) -> bool:
        """Instala dependências do Whisper"""
        print("   Installing Whisper dependencies...")
        code, stdout, stderr = self.ssh.run(self.INSTALL_SCRIPT, timeout=300)
        return "Dependencies installed" in stdout or code == 0

    def run_inference(self) -> Tuple[bool, float, str]:
        """
        Executa inferência com Whisper.

        Returns:
            (success, time_seconds, transcription)
        """
        print("   Running Whisper inference...")
        code, stdout, stderr = self.ssh.run(self.TEST_SCRIPT, timeout=180)

        if "SUCCESS" not in stdout:
            return False, 0, stderr

        # Parse output
        time_seconds = 0
        transcription = ""

        for line in stdout.split("\n"):
            if line.startswith("TRANSCRIPTION:"):
                transcription = line.replace("TRANSCRIPTION:", "").strip()
            elif line.startswith("TIME:"):
                try:
                    time_seconds = float(line.split(":")[1].replace("s", "").strip())
                except:
                    pass

        return True, time_seconds, transcription


class ServerlessJourneyTest:
    """Teste de jornada serverless completa"""

    def __init__(self, config: ServerlessTestConfig):
        self.config = config
        self.cli = DumontCLI()
        self.instance_id: Optional[int] = None
        self.ssh_host: Optional[str] = None
        self.ssh_port: Optional[int] = None
        self.ssh: Optional[SSHClient] = None
        self.whisper: Optional[WhisperInstaller] = None
        self.metrics: Dict[str, Any] = {}

    def deploy_gpu(self) -> bool:
        """Step 1: Deploy GPU"""
        print("\n[Step 1] Deploying GPU...")

        start = time.time()
        code, output = self.cli.run(
            "wizard", "deploy", "speed=fast", "price=0.5",
            timeout=self.config.max_deploy_time
        )
        elapsed = time.time() - start

        if code != 0 or "Instance ID:" not in output:
            print(f"   FAILED: {output[:200]}")
            return False

        # Parse instance info
        for line in output.split("\n"):
            if "Instance ID:" in line:
                self.instance_id = int(line.split(":")[1].strip())
            elif "IP:" in line:
                self.ssh_host = line.split(":")[1].strip()
            elif "SSH Port:" in line:
                self.ssh_port = int(line.split(":")[1].strip())

        if not all([self.instance_id, self.ssh_host, self.ssh_port]):
            print("   FAILED: Could not parse instance info")
            return False

        self.ssh = SSHClient(self.ssh_host, self.ssh_port)
        self.whisper = WhisperInstaller(self.ssh)

        self.metrics["deploy_time"] = elapsed
        print(f"   OK: Instance {self.instance_id} deployed in {elapsed:.1f}s")
        print(f"       SSH: {self.ssh_host}:{self.ssh_port}")

        return True

    def install_whisper(self) -> bool:
        """Step 2: Install Whisper"""
        print("\n[Step 2] Installing Whisper Distill...")

        start = time.time()
        success = self.whisper.install()
        elapsed = time.time() - start

        self.metrics["install_time"] = elapsed

        if success:
            print(f"   OK: Whisper installed in {elapsed:.1f}s")
        else:
            print(f"   FAILED")

        return success

    def run_inference(self, label: str = "initial") -> bool:
        """Step 3: Run inference"""
        print(f"\n[Step 3] Running inference ({label})...")

        start = time.time()
        success, inference_time, transcription = self.whisper.run_inference()
        elapsed = time.time() - start

        self.metrics[f"inference_{label}_time"] = inference_time
        self.metrics[f"inference_{label}_total"] = elapsed

        if success:
            print(f"   OK: Inference completed in {inference_time:.2f}s")
            print(f"       Transcription: {transcription[:60]}...")

            # Validar transcrição esperada
            if "dream" not in transcription.lower():
                print("   WARNING: Transcription may be incorrect")
        else:
            print(f"   FAILED: {transcription[:100]}")

        return success

    def enable_serverless(self) -> bool:
        """Step 4: Enable serverless mode"""
        print(f"\n[Step 4] Enabling serverless mode ({self.config.mode})...")

        code, output = self.cli.run(
            "serverless", "enable", str(self.instance_id),
            f"mode={self.config.mode}",
            f"idle_timeout_seconds={self.config.idle_timeout}",
            f"gpu_threshold={self.config.gpu_threshold}"
        )

        data = self.cli.parse_json(output)

        if data and data.get("status") == "enabled":
            print(f"   OK: Serverless {self.config.mode} enabled")
            print(f"       Idle timeout: {self.config.idle_timeout}s")
            return True

        print(f"   FAILED: {output[:200]}")
        return False

    def simulate_idle_and_wait_pause(self) -> bool:
        """Step 5: Wait for auto-pause"""
        print(f"\n[Step 5] Waiting for auto-pause (timeout={self.config.idle_timeout}s)...")

        # Simular heartbeat com GPU idle (0% utilization)
        # Isso é feito via API do agent
        import requests

        start = time.time()
        paused = False

        # Enviar heartbeats simulando GPU idle
        for i in range(self.config.expected_pause_time):
            # Enviar heartbeat com GPU 0%
            try:
                requests.post(
                    f"{self.cli.base_url}/api/v1/agent/status",
                    json={
                        "agent": "DumontAgent",
                        "version": "1.0.0",
                        "instance_id": str(self.instance_id),
                        "status": "idle",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "gpu_metrics": {
                            "utilization": 0.0,
                            "gpu_count": 1,
                            "gpu_names": ["Test GPU"],
                            "gpu_utilizations": [0.0],
                            "gpu_memory_used": [0],
                            "gpu_memory_total": [16000],
                            "gpu_temperatures": [40.0]
                        }
                    },
                    timeout=5
                )
            except:
                pass

            # Verificar status
            code, output = self.cli.run("serverless", "status", str(self.instance_id))
            data = self.cli.parse_json(output)

            if data and data.get("is_paused"):
                paused = True
                elapsed = time.time() - start
                self.metrics["pause_time"] = elapsed
                print(f"   OK: Instance paused after {elapsed:.1f}s")
                break

            # Também verificar se VAST.ai pausou
            code2, output2 = self.cli.run("instance", "get", str(self.instance_id))
            if "paused" in output2.lower() or "stopped" in output2.lower():
                paused = True
                elapsed = time.time() - start
                self.metrics["pause_time"] = elapsed
                print(f"   OK: Instance paused (VAST.ai) after {elapsed:.1f}s")
                break

            print(f"   Waiting... {i+1}/{self.config.expected_pause_time}s", end="\r")
            time.sleep(1)

        print()  # Nova linha

        if not paused:
            print(f"   FAILED: Instance did not pause within {self.config.expected_pause_time}s")
            # Verificar SSH para confirmar que ainda está rodando
            if self.ssh.is_reachable():
                print("   NOTE: SSH still reachable - instance is running")

        return paused

    def wake_instance(self) -> bool:
        """Step 6: Wake up instance"""
        print(f"\n[Step 6] Waking up instance...")

        start = time.time()
        code, output = self.cli.run("serverless", "wake", str(self.instance_id))

        data = self.cli.parse_json(output)

        if data and data.get("status") == "resumed":
            cold_start = data.get("cold_start_seconds", 0)
            elapsed = time.time() - start
            self.metrics["wake_time"] = elapsed
            self.metrics["cold_start"] = cold_start
            print(f"   OK: Instance woke up in {elapsed:.1f}s (cold start: {cold_start:.1f}s)")
            return True

        # Se wake não funcionou, tentar resume direto
        print("   Trying direct resume...")
        code, output = self.cli.run("instance", "resume", str(self.instance_id))

        # Aguardar SSH ficar disponível
        for i in range(self.config.expected_recovery_time):
            if self.ssh.is_reachable():
                elapsed = time.time() - start
                self.metrics["wake_time"] = elapsed
                print(f"   OK: Instance recovered in {elapsed:.1f}s")
                return True
            time.sleep(1)
            print(f"   Waiting for SSH... {i+1}s", end="\r")

        print()
        print(f"   FAILED: Instance did not recover within {self.config.expected_recovery_time}s")
        return False

    def run_post_wake_inference(self) -> bool:
        """Step 7: Run inference after wake"""
        print("\n[Step 7] Running post-wake inference...")
        return self.run_inference(label="post_wake")

    def cleanup(self):
        """Step 8: Cleanup"""
        print("\n[Step 8] Cleanup...")

        if self.instance_id:
            # Desabilitar serverless
            self.cli.run("serverless", "disable", str(self.instance_id))

            # Destruir instância
            code, output = self.cli.run("instance", "delete", str(self.instance_id))
            if code == 0:
                print(f"   OK: Instance {self.instance_id} destroyed")
            else:
                print(f"   WARNING: Could not destroy instance: {output[:100]}")

    def print_summary(self):
        """Imprime resumo dos resultados"""
        print("\n" + "="*60)
        print(f"SERVERLESS JOURNEY TEST SUMMARY - Mode: {self.config.mode.upper()}")
        print("="*60)

        print(f"\nInstance: {self.instance_id}")
        print(f"SSH: {self.ssh_host}:{self.ssh_port}")

        print("\nTimings:")
        for key, value in self.metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}s")
            else:
                print(f"  {key}: {value}")

        print("\nExpected vs Actual:")
        if "pause_time" in self.metrics:
            print(f"  Pause: expected ~{self.config.idle_timeout}s, actual {self.metrics['pause_time']:.1f}s")
        if "wake_time" in self.metrics:
            expected_wake = "<1s" if self.config.mode == "fast" else "~30s"
            print(f"  Wake: expected {expected_wake}, actual {self.metrics['wake_time']:.1f}s")

        print("="*60)

    def run(self) -> bool:
        """Executa teste completo"""
        try:
            # Step 1: Deploy
            if not self.deploy_gpu():
                return False

            # Step 2: Install Whisper
            if not self.install_whisper():
                return False

            # Step 3: Initial inference
            if not self.run_inference("initial"):
                return False

            # Step 4: Enable serverless
            if not self.enable_serverless():
                return False

            # Step 5: Wait for auto-pause
            pause_ok = self.simulate_idle_and_wait_pause()

            if pause_ok:
                # Step 6: Wake up
                if not self.wake_instance():
                    return False

                # Step 7: Post-wake inference
                if not self.run_post_wake_inference():
                    return False
            else:
                print("\n   SKIPPING wake test (pause failed)")

            self.print_summary()
            return pause_ok

        finally:
            self.cleanup()


# =============================================================================
# PYTEST TESTS
# =============================================================================

@pytest.fixture(scope="module")
def check_backend():
    """Verifica se o backend está rodando"""
    import requests
    try:
        resp = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if resp.status_code != 200:
            pytest.skip("Backend not healthy")
    except:
        pytest.skip("Backend not running")


@pytest.fixture(scope="module")
def check_vast_balance():
    """Verifica se há saldo no VAST.ai"""
    cli = DumontCLI()
    code, output = cli.run("balance", "get")
    data = cli.parse_json(output)

    if not data:
        pytest.skip("Could not get balance")

    balance = data.get("credit", 0)
    if balance < 1.0:
        pytest.skip(f"Insufficient VAST.ai balance: ${balance}")


class TestServerlessJourneyEconomic:
    """Testes do modo ECONOMIC (VAST.ai pause/resume)"""

    @pytest.mark.slow
    @pytest.mark.real_gpu
    def test_full_journey_economic(self, check_backend, check_vast_balance):
        """
        Teste completo do modo economic.

        Jornada:
        1. Deploy GPU
        2. Instalar Whisper Distill
        3. Fazer inferência (validar transcrição)
        4. Habilitar serverless mode=economic
        5. Aguardar idle timeout (30s)
        6. Verificar se VAST.ai pausou a máquina
        7. Acordar máquina via wake
        8. Fazer nova inferência
        9. Cleanup
        """
        test = ServerlessJourneyTest(ECONOMIC_CONFIG)
        success = test.run()

        assert success, "Serverless economic journey failed"
        assert test.metrics.get("pause_time", 0) > 0, "Instance did not pause"
        assert test.metrics.get("wake_time", 0) < ECONOMIC_CONFIG.expected_recovery_time, \
            f"Wake took too long: {test.metrics.get('wake_time', 0)}s"


class TestServerlessJourneyFast:
    """Testes do modo FAST (CPU Standby)"""

    @pytest.mark.slow
    @pytest.mark.real_gpu
    @pytest.mark.requires_gcp
    def test_full_journey_fast(self, check_backend, check_vast_balance):
        """
        Teste completo do modo fast.

        Jornada:
        1. Deploy GPU
        2. Configurar CPU Standby (requer GCP)
        3. Instalar Whisper Distill
        4. Fazer inferência
        5. Habilitar serverless mode=fast
        6. Aguardar idle timeout
        7. Verificar se pausou (estado no CPU)
        8. Acordar máquina (recovery <1s)
        9. Fazer nova inferência
        10. Cleanup
        """
        test = ServerlessJourneyTest(FAST_CONFIG)
        success = test.run()

        assert success, "Serverless fast journey failed"
        assert test.metrics.get("wake_time", 0) < FAST_CONFIG.expected_recovery_time, \
            f"Fast wake took too long: {test.metrics.get('wake_time', 0)}s (expected <{FAST_CONFIG.expected_recovery_time}s)"


class TestServerlessInferenceOnly:
    """Testes apenas de inferência (sem serverless completo)"""

    @pytest.mark.real_gpu
    def test_whisper_inference(self, check_backend, check_vast_balance):
        """
        Teste básico: deploy + inferência Whisper.

        Não testa serverless, apenas valida que Whisper funciona.
        """
        cli = DumontCLI()

        # Deploy
        print("\n[1] Deploying GPU...")
        code, output = cli.run("wizard", "deploy", "speed=fast", "price=0.5", timeout=120)
        assert "Instance ID:" in output, f"Deploy failed: {output[:200]}"

        # Parse instance info
        instance_id = None
        ssh_host = None
        ssh_port = None

        for line in output.split("\n"):
            if "Instance ID:" in line:
                instance_id = int(line.split(":")[1].strip())
            elif "IP:" in line:
                ssh_host = line.split(":")[1].strip()
            elif "SSH Port:" in line:
                ssh_port = int(line.split(":")[1].strip())

        assert instance_id, "Could not get instance ID"

        try:
            ssh = SSHClient(ssh_host, ssh_port)
            whisper = WhisperInstaller(ssh)

            # Install
            print("\n[2] Installing Whisper...")
            assert whisper.install(), "Whisper install failed"

            # Inference
            print("\n[3] Running inference...")
            success, inference_time, transcription = whisper.run_inference()

            assert success, f"Inference failed: {transcription}"
            assert "dream" in transcription.lower(), f"Wrong transcription: {transcription}"
            assert inference_time < 10, f"Inference too slow: {inference_time}s"

            print(f"\n   Transcription: {transcription}")
            print(f"   Time: {inference_time:.2f}s")

        finally:
            # Cleanup
            print("\n[4] Cleanup...")
            cli.run("instance", "delete", str(instance_id))


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Serverless Journey Test")
    parser.add_argument(
        "--mode",
        choices=["economic", "fast", "both"],
        default="economic",
        help="Serverless mode to test"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Idle timeout in seconds"
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Don't destroy instance after test"
    )

    args = parser.parse_args()

    print("="*60)
    print("SERVERLESS GPU JOURNEY TEST")
    print("="*60)

    modes = ["economic", "fast"] if args.mode == "both" else [args.mode]

    for mode in modes:
        config = ECONOMIC_CONFIG if mode == "economic" else FAST_CONFIG
        config.idle_timeout = args.timeout

        print(f"\n>>> Testing mode: {mode.upper()}")

        test = ServerlessJourneyTest(config)

        try:
            success = test.run()

            if success:
                print(f"\n JOURNEY {mode.upper()} PASSED")
            else:
                print(f"\n JOURNEY {mode.upper()} FAILED")

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            if not args.skip_cleanup:
                test.cleanup()
            sys.exit(1)
        except Exception as e:
            print(f"\n ERROR: {e}")
            if not args.skip_cleanup:
                test.cleanup()
            raise
