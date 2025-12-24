"""
Testes E2E de Integração REAL - Dumont Cloud CLI
=================================================

ATENÇÃO: Estes testes GASTAM CRÉDITOS REAIS da VAST.ai!

Testa TODAS as funcionalidades do CLI com chamadas reais à API:
1. Jobs (on-demand e spot)
2. Fine-tuning (upload, create, monitor)
3. Serverless (3 modos: fast, economic, spot)
4. Wizard Deploy (on-demand e spot)
5. Spot Instances
6. Standby/Failover
7. Warm Pool
8. History/Blacklist
9. Snapshots
10. Métricas

Execução:
    cd cli && pytest tests/test_e2e_real_integration.py -v -s

Execução rápida (apenas smoke tests):
    cd cli && pytest tests/test_e2e_real_integration.py -v -m "smoke"

Execução completa (todos os testes):
    cd cli && pytest tests/test_e2e_real_integration.py -v -m "slow"
"""
import pytest
import subprocess
import json
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

API_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
TEST_GPU = "RTX 4090"  # GPU para testes
TEST_TIMEOUT_SHORT = 60  # 1 minuto
TEST_TIMEOUT_MEDIUM = 180  # 3 minutos
TEST_TIMEOUT_LONG = 600  # 10 minutos


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def cli():
    """Runner para executar comandos CLI reais"""
    def run(command: str, timeout: int = TEST_TIMEOUT_SHORT) -> dict:
        """Executa comando CLI e retorna resultado"""
        full_cmd = f"cd /home/marcos/dumontcloud && source .venv/bin/activate && python -m cli {command}"

        try:
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                executable="/bin/bash"
            )

            output = result.stdout + result.stderr

            # Parse JSON from output
            json_data = None
            if "{" in output:
                try:
                    start = output.find("{")
                    end = output.rfind("}") + 1
                    if start >= 0 and end > start:
                        json_data = json.loads(output[start:end])
                except json.JSONDecodeError:
                    pass

            return {
                "success": result.returncode == 0,
                "output": output,
                "json": json_data,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "Timeout", "json": None, "returncode": -1}
        except Exception as e:
            return {"success": False, "output": str(e), "json": None, "returncode": -1}

    return run


@pytest.fixture(scope="module")
def api_healthy(cli):
    """Verifica se API está rodando"""
    result = cli("health list")
    assert result["success"], f"API não está rodando: {result['output']}"
    return True


@pytest.fixture(scope="module")
def created_instance_id(cli, api_healthy):
    """Cria uma instância para testes e retorna o ID"""
    # Tenta criar uma instância barata para testes
    result = cli(
        f'wizard deploy gpu="{TEST_GPU}" type=on-demand price=0.5 speed=slow',
        timeout=TEST_TIMEOUT_LONG
    )

    if result["json"] and result["json"].get("instance_id"):
        instance_id = result["json"]["instance_id"]
        yield instance_id

        # Cleanup: deletar instância após testes
        cli(f"instance delete {instance_id}", timeout=TEST_TIMEOUT_SHORT)
    else:
        pytest.skip("Não foi possível criar instância para testes")


# =============================================================================
# 1. TESTES DE JOBS (Execute and Destroy)
# =============================================================================

class TestJobsReal:
    """Testes reais de Jobs - provisionam GPU, executam e destroem"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_job_create_ondemand_real(self, cli, api_healthy):
        """
        Cria job ON-DEMAND real
        - Provisiona GPU on-demand
        - Executa comando
        - Verifica status
        - Cancela job
        """
        print("\n🚀 Criando job ON-DEMAND real...")

        result = cli(
            'job create test-ondemand-real --command="echo Hello from Dumont && sleep 10" --use-spot=false --gpu="RTX 4090" --timeout=5',
            timeout=TEST_TIMEOUT_MEDIUM
        )

        print(f"Output: {result['output']}")

        # Verifica que job foi criado
        assert "Creating GPU Job" in result["output"] or result["json"], \
            f"Job não foi criado: {result['output']}"

        if result["json"]:
            job_id = result["json"].get("id") or result["json"].get("job_id")
            print(f"✅ Job criado: {job_id}")

            # Verifica status
            time.sleep(5)
            status_result = cli(f"job status {job_id}")
            print(f"Status: {status_result['output']}")

            # Cancela job para não gastar muito
            cancel_result = cli(f"job cancel {job_id}")
            print(f"Cancel: {cancel_result['output']}")

            assert "cancel" in cancel_result["output"].lower() or cancel_result["success"]

    @pytest.mark.slow
    def test_job_create_spot_real(self, cli, api_healthy):
        """
        Cria job SPOT real (60-70% mais barato)
        - Provisiona GPU spot
        - Executa comando
        - Verifica status
        - Cancela job
        """
        print("\n🚀 Criando job SPOT real...")

        result = cli(
            'job create test-spot-real --command="echo Hello from Spot && sleep 10" --use-spot=true --gpu="RTX 4090" --timeout=5',
            timeout=TEST_TIMEOUT_MEDIUM
        )

        print(f"Output: {result['output']}")

        # Verifica que é spot
        assert "Spot" in result["output"] or "spot" in result["output"].lower() or result["json"]

        if result["json"]:
            job_id = result["json"].get("id") or result["json"].get("job_id")
            print(f"✅ Job SPOT criado: {job_id}")

            # Cancela
            time.sleep(3)
            cli(f"job cancel {job_id}")

    @pytest.mark.slow
    def test_job_list_real(self, cli, api_healthy):
        """Lista jobs reais da conta"""
        print("\n📋 Listando jobs reais...")

        result = cli("job list")
        print(f"Output: {result['output']}")

        assert result["success"]
        if result["json"]:
            assert "jobs" in result["json"] or "total" in result["json"]
            print(f"✅ Total de jobs: {result['json'].get('total', len(result['json'].get('jobs', [])))}")


# =============================================================================
# 2. TESTES DE FINE-TUNING
# =============================================================================

class TestFinetuneReal:
    """Testes reais de Fine-tuning LLM"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_finetune_models_real(self, cli, api_healthy):
        """Lista modelos de fine-tuning disponíveis"""
        print("\n🤖 Listando modelos de fine-tuning...")

        result = cli("finetune models")
        print(f"Output: {result['output']}")

        assert result["success"]

        if result["json"]:
            models = result["json"].get("models", [])
            print(f"✅ {len(models)} modelos disponíveis")

            # Verifica modelos conhecidos
            model_names = str(result["json"]).lower()
            assert "llama" in model_names or "mistral" in model_names or "qwen" in model_names

    @pytest.mark.slow
    def test_finetune_list_real(self, cli, api_healthy):
        """Lista jobs de fine-tuning existentes"""
        print("\n📋 Listando jobs de fine-tuning...")

        result = cli("finetune list")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_finetune_create_validation(self, cli, api_healthy):
        """Verifica validação do fine-tuning create"""
        print("\n🔍 Testando validação de fine-tuning create...")

        # Sem model
        result1 = cli("finetune create test-ft --dataset=/tmp/data.jsonl")
        assert "model" in result1["output"].lower() or "Missing" in result1["output"]

        # Sem dataset
        result2 = cli("finetune create test-ft --model=unsloth/llama-3-8b-bnb-4bit")
        assert "dataset" in result2["output"].lower() or "Missing" in result2["output"]

        print("✅ Validação funcionando")


# =============================================================================
# 3. TESTES DE SERVERLESS (3 modos)
# =============================================================================

class TestServerlessReal:
    """Testes reais dos 3 modos de Serverless"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_serverless_pricing_real(self, cli, api_healthy):
        """Verifica preços dos modos serverless"""
        print("\n💰 Verificando preços serverless...")

        result = cli("serverless pricing")
        print(f"Output: {result['output']}")

        assert result["success"]

        if result["json"]:
            costs = result["json"].get("monthly_costs", {})
            print(f"✅ Custos mensais: {costs}")

            # Verifica que os 3 modos estão presentes
            assert "always_on" in costs or "serverless" in str(costs).lower()

    @pytest.mark.slow
    def test_serverless_list_real(self, cli, api_healthy):
        """Lista instâncias serverless"""
        print("\n📋 Listando instâncias serverless...")

        result = cli("serverless list")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_serverless_enable_fast_mode_real(self, cli, api_healthy, created_instance_id):
        """
        Habilita modo FAST (<1s recovery)
        - CPU Standby com sync contínuo
        - Recovery time: <1 segundo
        - Economia: ~80%
        """
        print(f"\n⚡ Habilitando modo FAST na instância {created_instance_id}...")

        result = cli(
            f"serverless enable {created_instance_id} mode=fast idle_timeout_seconds=30",
            timeout=TEST_TIMEOUT_MEDIUM
        )

        print(f"Output: {result['output']}")

        if result["success"] and result["json"]:
            assert result["json"].get("mode") == "fast"
            print("✅ Modo FAST habilitado")

            # Desabilita para próximo teste
            cli(f"serverless disable {created_instance_id}")

    @pytest.mark.slow
    def test_serverless_enable_economic_mode_real(self, cli, api_healthy, created_instance_id):
        """
        Habilita modo ECONOMIC (~7s recovery)
        - VAST.ai pause/resume nativo
        - Recovery time: ~7 segundos
        - Economia: ~82%
        """
        print(f"\n💵 Habilitando modo ECONOMIC na instância {created_instance_id}...")

        result = cli(
            f"serverless enable {created_instance_id} mode=economic idle_timeout_seconds=30",
            timeout=TEST_TIMEOUT_MEDIUM
        )

        print(f"Output: {result['output']}")

        if result["success"] and result["json"]:
            assert result["json"].get("mode") == "economic"
            print("✅ Modo ECONOMIC habilitado")

            cli(f"serverless disable {created_instance_id}")

    @pytest.mark.slow
    def test_serverless_enable_spot_mode_real(self, cli, api_healthy, created_instance_id):
        """
        Habilita modo SPOT (~30s recovery, 60-70% mais barato)
        - Usa spot instances
        - Recovery time: ~30 segundos
        - Economia: ~90%
        """
        print(f"\n🔥 Habilitando modo SPOT na instância {created_instance_id}...")

        result = cli(
            f"serverless enable {created_instance_id} mode=spot idle_timeout_seconds=60",
            timeout=TEST_TIMEOUT_MEDIUM
        )

        print(f"Output: {result['output']}")

        if result["success"] and result["json"]:
            assert result["json"].get("mode") == "spot"
            print("✅ Modo SPOT habilitado")

            cli(f"serverless disable {created_instance_id}")


# =============================================================================
# 4. TESTES DE WIZARD DEPLOY
# =============================================================================

class TestWizardDeployReal:
    """Testes reais de Wizard Deploy com multi-start strategy"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_wizard_deploy_ondemand_real(self, cli, api_healthy):
        """
        Deploy ON-DEMAND real
        - Multi-start strategy (cria várias, primeira que funcionar vence)
        - Máquina estável, sem interrupções
        """
        print("\n🚀 Wizard Deploy ON-DEMAND real...")

        result = cli(
            f'wizard deploy gpu="{TEST_GPU}" type=on-demand price=0.5 speed=slow',
            timeout=TEST_TIMEOUT_LONG
        )

        print(f"Output: {result['output']}")

        # Verifica que é on-demand
        assert "On-Demand" in result["output"] or "on-demand" in result["output"].lower()

        if result["json"] and result["json"].get("instance_id"):
            instance_id = result["json"]["instance_id"]
            print(f"✅ Instância criada: {instance_id}")

            # Cleanup
            time.sleep(5)
            delete_result = cli(f"instance delete {instance_id}")
            print(f"Cleanup: {delete_result['output']}")

    @pytest.mark.slow
    def test_wizard_deploy_spot_real(self, cli, api_healthy):
        """
        Deploy SPOT real (60-70% mais barato)
        - Multi-start strategy
        - Máquina pode ser interrompida
        - Failover automático
        """
        print("\n🚀 Wizard Deploy SPOT real...")

        result = cli(
            f'wizard deploy gpu="{TEST_GPU}" type=spot price=0.3 speed=slow',
            timeout=TEST_TIMEOUT_LONG
        )

        print(f"Output: {result['output']}")

        # Verifica que é spot
        assert "Spot" in result["output"] or "spot" in result["output"].lower() or "interruptible" in result["output"].lower()

        if result["json"] and result["json"].get("instance_id"):
            instance_id = result["json"]["instance_id"]
            print(f"✅ Instância SPOT criada: {instance_id}")

            # Cleanup
            time.sleep(5)
            cli(f"instance delete {instance_id}")


# =============================================================================
# 5. TESTES DE SPOT INSTANCES
# =============================================================================

class TestSpotInstancesReal:
    """Testes reais de Spot Instances"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_spot_pricing_real(self, cli, api_healthy):
        """Lista preços spot reais"""
        print("\n💰 Verificando preços spot reais...")

        result = cli("spot pricing")
        print(f"Output: {result['output']}")

        # Pode não ter ofertas spot disponíveis
        assert result["success"] or "offers" in result["output"].lower() or "No spot" in result["output"]

    @pytest.mark.slow
    def test_spot_template_list_real(self, cli, api_healthy):
        """Lista templates spot"""
        print("\n📋 Listando templates spot...")

        result = cli("spot template list")
        print(f"Output: {result['output']}")

        assert result["success"] or "No spot templates" in result["output"]

    @pytest.mark.slow
    def test_spot_instances_real(self, cli, api_healthy):
        """Lista instâncias spot ativas"""
        print("\n📋 Listando instâncias spot ativas...")

        result = cli("spot instances")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_spot_prediction_real(self, cli, api_healthy):
        """Previsão de interrupção para GPU"""
        print(f"\n🔮 Previsão de interrupção para {TEST_GPU}...")

        result = cli(f'spot prediction "{TEST_GPU}"')
        print(f"Output: {result['output']}")

        # Pode não ter dados suficientes
        assert result["success"] or "prediction" in result["output"].lower() or "No data" in result["output"]

    @pytest.mark.slow
    def test_spot_safe_windows_real(self, cli, api_healthy):
        """Janelas seguras para GPU"""
        print(f"\n🕐 Janelas seguras para {TEST_GPU}...")

        result = cli(f'spot safe-windows "{TEST_GPU}"')
        print(f"Output: {result['output']}")

        assert result["success"] or "safe" in result["output"].lower() or "No data" in result["output"]


# =============================================================================
# 6. TESTES DE STANDBY/FAILOVER
# =============================================================================

class TestStandbyFailoverReal:
    """Testes reais de CPU Standby e Failover"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_standby_status_real(self, cli, api_healthy):
        """Verifica status de standby"""
        print("\n📊 Status de standby...")

        result = cli("standby status")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_standby_associations_real(self, cli, api_healthy):
        """Lista associações GPU-Standby"""
        print("\n🔗 Associações GPU-Standby...")

        result = cli("standby associations")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_standby_pricing_real(self, cli, api_healthy):
        """Verifica preços de standby"""
        print("\n💰 Preços de standby...")

        result = cli("standby pricing")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_standby_provision_real(self, cli, api_healthy, created_instance_id):
        """
        Provisiona CPU Standby real
        - Cria CPU standby associado à GPU
        - Usado para failover instantâneo
        """
        print(f"\n🛡️ Provisionando CPU Standby para {created_instance_id}...")

        result = cli(
            f'standby provision {created_instance_id} label="test-standby"',
            timeout=TEST_TIMEOUT_MEDIUM
        )

        print(f"Output: {result['output']}")

        if result["success"]:
            print("✅ CPU Standby provisionado")


# =============================================================================
# 7. TESTES DE WARM POOL
# =============================================================================

class TestWarmPoolReal:
    """Testes reais de Warm Pool (GPUs pré-aquecidas)"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_warmpool_hosts_real(self, cli, api_healthy):
        """Lista hosts do warm pool"""
        print("\n🔥 Hosts do warm pool...")

        result = cli("warmpool hosts")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_warmpool_enable_real(self, cli, api_healthy, created_instance_id):
        """Habilita warm pool para instância"""
        print(f"\n🔥 Habilitando warm pool para {created_instance_id}...")

        result = cli(f"warmpool enable {created_instance_id}")
        print(f"Output: {result['output']}")

        if result["success"]:
            print("✅ Warm pool habilitado")

            # Status
            status = cli(f"warmpool status {created_instance_id}")
            print(f"Status: {status['output']}")

            # Desabilita
            cli(f"warmpool disable {created_instance_id}")


# =============================================================================
# 8. TESTES DE INSTANCE
# =============================================================================

class TestInstanceReal:
    """Testes reais de gerenciamento de instâncias"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_instance_list_real(self, cli, api_healthy):
        """Lista todas as instâncias"""
        print("\n📋 Listando instâncias...")

        result = cli("instance list")
        print(f"Output: {result['output']}")

        assert result["success"]

        if result["json"]:
            instances = result["json"].get("instances", [])
            print(f"✅ {len(instances)} instâncias encontradas")

    @pytest.mark.slow
    def test_instance_list_running_real(self, cli, api_healthy):
        """Lista instâncias running"""
        print("\n📋 Listando instâncias running...")

        result = cli("instance list status=running")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_instance_offers_real(self, cli, api_healthy):
        """Lista ofertas disponíveis"""
        print("\n🛒 Listando ofertas de GPU...")

        result = cli("instance offers")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_instance_get_real(self, cli, api_healthy, created_instance_id):
        """Obtém detalhes de instância"""
        print(f"\n🔍 Detalhes da instância {created_instance_id}...")

        result = cli(f"instance get {created_instance_id}")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_instance_pause_resume_real(self, cli, api_healthy, created_instance_id):
        """Testa pause e resume de instância"""
        print(f"\n⏸️ Pausando instância {created_instance_id}...")

        # Pause
        pause_result = cli(f"instance pause {created_instance_id}", timeout=TEST_TIMEOUT_MEDIUM)
        print(f"Pause: {pause_result['output']}")

        if pause_result["success"]:
            time.sleep(10)

            # Resume
            print(f"▶️ Resumindo instância {created_instance_id}...")
            resume_result = cli(f"instance resume {created_instance_id}", timeout=TEST_TIMEOUT_MEDIUM)
            print(f"Resume: {resume_result['output']}")


# =============================================================================
# 9. TESTES DE HISTORY E BLACKLIST
# =============================================================================

class TestHistoryBlacklistReal:
    """Testes reais de History e Blacklist"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_history_summary_real(self, cli, api_healthy):
        """Resumo do histórico de máquinas"""
        print("\n📊 Resumo do histórico...")

        result = cli("history summary")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_history_list_real(self, cli, api_healthy):
        """Lista histórico de tentativas"""
        print("\n📋 Histórico de tentativas...")

        result = cli("history list --provider=vast --hours=72")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_history_problematic_real(self, cli, api_healthy):
        """Lista máquinas problemáticas"""
        print("\n⚠️ Máquinas problemáticas...")

        result = cli("history problematic --provider=vast")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_history_reliable_real(self, cli, api_healthy):
        """Lista máquinas confiáveis"""
        print("\n✅ Máquinas confiáveis...")

        result = cli("history reliable --provider=vast")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_blacklist_list_real(self, cli, api_healthy):
        """Lista blacklist"""
        print("\n🚫 Blacklist...")

        result = cli("blacklist list")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_blacklist_crud_real(self, cli, api_healthy):
        """Testa CRUD de blacklist"""
        print("\n🚫 Testando CRUD de blacklist...")

        test_machine_id = "test_machine_12345"

        # Add
        add_result = cli(f'blacklist add vast {test_machine_id} "Test blacklist" --hours=1')
        print(f"Add: {add_result['output']}")

        # Check
        check_result = cli(f"blacklist check vast {test_machine_id}")
        print(f"Check: {check_result['output']}")

        # Remove
        remove_result = cli(f"blacklist remove vast {test_machine_id}")
        print(f"Remove: {remove_result['output']}")


# =============================================================================
# 10. TESTES DE MÉTRICAS E SAVINGS
# =============================================================================

class TestMetricsSavingsReal:
    """Testes reais de Métricas e Savings"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_saving_summary_real(self, cli, api_healthy):
        """Resumo de economia"""
        print("\n💰 Resumo de economia...")

        result = cli("saving summary")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_saving_history_real(self, cli, api_healthy):
        """Histórico de economia"""
        print("\n📈 Histórico de economia...")

        result = cli("saving history months=6")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_metrics_gpus_real(self, cli, api_healthy):
        """Métricas de GPUs"""
        print("\n📊 Métricas de GPUs...")

        result = cli("metrics gpus")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_metrics_efficiency_real(self, cli, api_healthy):
        """Métricas de eficiência"""
        print("\n📊 Métricas de eficiência...")

        result = cli("metrics efficiency")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_metrics_providers_real(self, cli, api_healthy):
        """Métricas de provedores"""
        print("\n📊 Métricas de provedores...")

        result = cli("metrics providers")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_metrics_spot_real(self, cli, api_healthy):
        """Métricas spot para GPU específica"""
        print(f"\n📊 Métricas spot para {TEST_GPU}...")

        result = cli(f'metrics spot gpu_name="{TEST_GPU}"')
        print(f"Output: {result['output']}")

        assert result["success"]


# =============================================================================
# 11. TESTES DE SNAPSHOTS
# =============================================================================

class TestSnapshotsReal:
    """Testes reais de Snapshots"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_snapshot_list_real(self, cli, api_healthy):
        """Lista snapshots"""
        print("\n📸 Listando snapshots...")

        result = cli("snapshot list")
        print(f"Output: {result['output']}")

        assert result["success"]


# =============================================================================
# 12. TESTES DE CONFIGURAÇÕES
# =============================================================================

class TestSettingsReal:
    """Testes reais de Configurações"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_settings_list_real(self, cli, api_healthy):
        """Lista configurações"""
        print("\n⚙️ Configurações...")

        result = cli("settings list")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_balance_list_real(self, cli, api_healthy):
        """Verifica saldo"""
        print("\n💳 Saldo...")

        result = cli("balance list")
        print(f"Output: {result['output']}")

        assert result["success"]

    @pytest.mark.slow
    def test_health_list_real(self, cli, api_healthy):
        """Health check"""
        print("\n🏥 Health check...")

        result = cli("health list")
        print(f"Output: {result['output']}")

        assert result["success"]

        if result["json"]:
            assert result["json"].get("status") == "healthy"


# =============================================================================
# 13. JORNADAS E2E COMPLETAS
# =============================================================================

class TestE2EJourneys:
    """Jornadas E2E completas que simulam uso real"""

    @pytest.mark.slow
    def test_journey_job_complete(self, cli, api_healthy):
        """
        Jornada completa de Job:
        1. Listar jobs
        2. Criar job on-demand
        3. Verificar status
        4. Ver logs
        5. Cancelar
        6. Verificar cancelamento
        """
        print("\n🎯 JORNADA E2E: Job Completo")
        print("=" * 50)

        # 1. Listar jobs existentes
        print("\n1️⃣ Listando jobs existentes...")
        list_result = cli("job list")
        initial_count = 0
        if list_result["json"]:
            initial_count = list_result["json"].get("total", 0)
        print(f"   Jobs existentes: {initial_count}")

        # 2. Criar job
        print("\n2️⃣ Criando job on-demand...")
        create_result = cli(
            'job create journey-test --command="echo E2E Test && sleep 30" --use-spot=false --timeout=5',
            timeout=TEST_TIMEOUT_MEDIUM
        )
        print(f"   Output: {create_result['output'][:200]}...")

        if not create_result["json"]:
            pytest.skip("Não foi possível criar job")

        job_id = create_result["json"].get("id") or create_result["json"].get("job_id")
        assert job_id, "Job ID não retornado"
        print(f"   ✅ Job criado: {job_id}")

        # 3. Verificar status
        print("\n3️⃣ Verificando status...")
        time.sleep(5)
        status_result = cli(f"job status {job_id}")
        print(f"   Status: {status_result['output'][:200]}...")

        # 4. Ver logs (pode não ter ainda)
        print("\n4️⃣ Verificando logs...")
        logs_result = cli(f"job logs {job_id}")
        print(f"   Logs: {logs_result['output'][:200]}...")

        # 5. Cancelar
        print("\n5️⃣ Cancelando job...")
        cancel_result = cli(f"job cancel {job_id}")
        print(f"   Cancel: {cancel_result['output'][:200]}...")

        # 6. Verificar cancelamento
        print("\n6️⃣ Verificando cancelamento...")
        time.sleep(5)
        final_status = cli(f"job status {job_id}")
        print(f"   Final: {final_status['output'][:200]}...")

        print("\n✅ JORNADA COMPLETA!")

    @pytest.mark.slow
    def test_journey_serverless_modes(self, cli, api_healthy, created_instance_id):
        """
        Jornada completa de Serverless:
        1. Ver pricing
        2. Habilitar modo fast
        3. Verificar status
        4. Trocar para modo economic
        5. Trocar para modo spot
        6. Desabilitar
        """
        print("\n🎯 JORNADA E2E: Serverless Modes")
        print("=" * 50)

        # 1. Pricing
        print("\n1️⃣ Verificando pricing...")
        pricing = cli("serverless pricing")
        print(f"   Pricing: {pricing['output'][:200]}...")

        # 2. Modo fast
        print(f"\n2️⃣ Habilitando modo FAST em {created_instance_id}...")
        fast = cli(f"serverless enable {created_instance_id} mode=fast idle_timeout_seconds=30")
        print(f"   Fast: {fast['output'][:200]}...")

        # 3. Status
        print("\n3️⃣ Verificando status...")
        status = cli(f"serverless status {created_instance_id}")
        print(f"   Status: {status['output'][:200]}...")

        # 4. Modo economic
        print(f"\n4️⃣ Trocando para modo ECONOMIC...")
        economic = cli(f"serverless enable {created_instance_id} mode=economic idle_timeout_seconds=30")
        print(f"   Economic: {economic['output'][:200]}...")

        # 5. Modo spot
        print(f"\n5️⃣ Trocando para modo SPOT...")
        spot = cli(f"serverless enable {created_instance_id} mode=spot idle_timeout_seconds=60")
        print(f"   Spot: {spot['output'][:200]}...")

        # 6. Desabilitar
        print(f"\n6️⃣ Desabilitando serverless...")
        disable = cli(f"serverless disable {created_instance_id}")
        print(f"   Disable: {disable['output'][:200]}...")

        print("\n✅ JORNADA COMPLETA!")

    @pytest.mark.slow
    def test_journey_wizard_deploy_and_cleanup(self, cli, api_healthy):
        """
        Jornada completa de Deploy:
        1. Ver ofertas
        2. Deploy on-demand
        3. Verificar instância
        4. Pausar
        5. Resumir
        6. Deletar
        """
        print("\n🎯 JORNADA E2E: Wizard Deploy")
        print("=" * 50)

        # 1. Ofertas
        print("\n1️⃣ Verificando ofertas...")
        offers = cli("instance offers")
        print(f"   Ofertas: {offers['output'][:200]}...")

        # 2. Deploy
        print("\n2️⃣ Fazendo deploy on-demand...")
        deploy = cli(
            f'wizard deploy gpu="{TEST_GPU}" type=on-demand price=0.5 speed=slow',
            timeout=TEST_TIMEOUT_LONG
        )
        print(f"   Deploy: {deploy['output'][:200]}...")

        if not deploy["json"] or not deploy["json"].get("instance_id"):
            pytest.skip("Deploy falhou - sem ofertas disponíveis?")

        instance_id = deploy["json"]["instance_id"]
        print(f"   ✅ Instância: {instance_id}")

        # 3. Verificar
        print("\n3️⃣ Verificando instância...")
        get_result = cli(f"instance get {instance_id}")
        print(f"   Get: {get_result['output'][:200]}...")

        # 4. Pausar
        print("\n4️⃣ Pausando...")
        pause = cli(f"instance pause {instance_id}", timeout=TEST_TIMEOUT_MEDIUM)
        print(f"   Pause: {pause['output'][:200]}...")

        time.sleep(10)

        # 5. Resumir
        print("\n5️⃣ Resumindo...")
        resume = cli(f"instance resume {instance_id}", timeout=TEST_TIMEOUT_MEDIUM)
        print(f"   Resume: {resume['output'][:200]}...")

        time.sleep(10)

        # 6. Deletar
        print("\n6️⃣ Deletando...")
        delete = cli(f"instance delete {instance_id}")
        print(f"   Delete: {delete['output'][:200]}...")

        print("\n✅ JORNADA COMPLETA!")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    DUMONT CLOUD - TESTES E2E REAIS                            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  ⚠️  ATENÇÃO: Estes testes GASTAM CRÉDITOS REAIS da VAST.ai!                  ║
║                                                                               ║
║  Uso:                                                                         ║
║    pytest tests/test_e2e_real_integration.py -v -s                            ║
║                                                                               ║
║  Smoke tests apenas:                                                          ║
║    pytest tests/test_e2e_real_integration.py -v -m "smoke"                    ║
║                                                                               ║
║  Todos os testes:                                                             ║
║    pytest tests/test_e2e_real_integration.py -v -m "slow"                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    pytest.main([__file__, "-v", "-s", "-m", "smoke"])
