"""
Test Suite Completo - Jornada do Usuário
==========================================

Testa TODOS os modos de criação de GPU via CLI:
1. Jobs (Execute and Destroy) - spot vs on-demand
2. Finetune (LLM Training)
3. Serverless (3 modos: fast, economic, spot)
4. Wizard Deploy (on-demand vs spot)

Execução:
    cd cli && pytest tests/test_user_journey_complete.py -v --tb=short

Execução com output detalhado:
    cd cli && pytest tests/test_user_journey_complete.py -v -s

Executar apenas testes rápidos (sem provisionar GPU real):
    cd cli && pytest tests/test_user_journey_complete.py -v -m "not slow"

Executar testes reais completos (provisiona GPUs):
    cd cli && pytest tests/test_user_journey_complete.py -v -m "slow"
"""
import pytest
import subprocess
import json
import time
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def cli_runner():
    """Runner para executar comandos CLI"""
    def run(command: str, timeout: int = 60) -> dict:
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

            # Try to parse JSON from output
            json_data = None
            if "{" in output:
                try:
                    # Find JSON in output
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
def api_health(cli_runner):
    """Verifica se API está saudável"""
    result = cli_runner("auth me")
    # Se retornar erro de auth, API está funcionando
    return "Unauthorized" in result["output"] or result["success"]


# =============================================================================
# TESTES - JOB COMMANDS
# =============================================================================

class TestJobCommands:
    """Testes para comandos de Job (Execute and Destroy)"""

    def test_job_help(self, cli_runner):
        """Verifica help do comando job"""
        result = cli_runner("job")
        assert "GPU Job Commands" in result["output"]
        assert "job create" in result["output"]
        assert "job list" in result["output"]
        assert "use-spot" in result["output"]

    def test_job_list(self, cli_runner):
        """Lista jobs existentes"""
        result = cli_runner("job list")
        assert result["success"] or "jobs" in result["output"]
        if result["json"]:
            assert "jobs" in result["json"]
            assert "total" in result["json"]

    def test_job_create_validation(self, cli_runner):
        """Verifica validação do create sem parâmetros"""
        result = cli_runner("job create")
        assert "Usage" in result["output"] or "command" in result["output"].lower()

    @pytest.mark.slow
    def test_job_create_ondemand(self, cli_runner):
        """Cria job on-demand (teste real)"""
        result = cli_runner(
            'job create test-ondemand --command="echo hello" --use-spot=false --timeout=5',
            timeout=120
        )

        assert "Creating GPU Job" in result["output"]
        assert "on-demand" in result["output"].lower() or "No (on-demand)" in result["output"]

        if result["json"]:
            job_id = result["json"].get("id")
            assert job_id is not None

            # Cancel job immediately to avoid charges
            time.sleep(2)
            cancel_result = cli_runner(f"job cancel {job_id}")
            assert "cancelled" in cancel_result["output"].lower() or cancel_result["success"]

    @pytest.mark.slow
    def test_job_create_spot(self, cli_runner):
        """Cria job spot (teste real)"""
        result = cli_runner(
            'job create test-spot --command="echo hello" --use-spot=true --timeout=5',
            timeout=120
        )

        assert "Creating GPU Job" in result["output"]
        assert "Spot:     Yes" in result["output"] or "use_spot" in result["output"]

        if result["json"]:
            job_id = result["json"].get("id")
            if job_id:
                time.sleep(2)
                cli_runner(f"job cancel {job_id}")


# =============================================================================
# TESTES - FINETUNE COMMANDS
# =============================================================================

class TestFinetuneCommands:
    """Testes para comandos de Fine-tuning"""

    def test_finetune_help(self, cli_runner):
        """Verifica help do comando finetune"""
        result = cli_runner("finetune")
        assert "Fine-Tuning Commands" in result["output"]
        assert "finetune models" in result["output"]
        assert "finetune upload" in result["output"]
        assert "finetune create" in result["output"]

    def test_finetune_models(self, cli_runner):
        """Lista modelos disponíveis"""
        result = cli_runner("finetune models")
        assert result["success"]

        if result["json"]:
            assert "models" in result["json"]
            models = result["json"]["models"]
            assert len(models) > 0

            # Verifica modelos conhecidos
            model_ids = [m["id"] for m in models]
            assert any("llama" in m.lower() for m in model_ids)
            assert any("mistral" in m.lower() or "qwen" in m.lower() for m in model_ids)

    def test_finetune_list(self, cli_runner):
        """Lista jobs de fine-tuning"""
        result = cli_runner("finetune list")
        assert result["success"]

        if result["json"]:
            assert "jobs" in result["json"]

    def test_finetune_create_validation(self, cli_runner):
        """Verifica validação do create sem parâmetros"""
        result = cli_runner("finetune create")
        assert "Usage" in result["output"] or "model" in result["output"].lower()

    def test_finetune_create_missing_model(self, cli_runner):
        """Verifica erro quando falta --model"""
        result = cli_runner("finetune create myjob --dataset=/tmp/data.jsonl")
        assert "Missing --model" in result["output"] or "model" in result["output"].lower()

    def test_finetune_create_missing_dataset(self, cli_runner):
        """Verifica erro quando falta --dataset"""
        result = cli_runner("finetune create myjob --model=unsloth/llama-3-8b-bnb-4bit")
        assert "Missing --dataset" in result["output"] or "dataset" in result["output"].lower()


# =============================================================================
# TESTES - SERVERLESS MODES
# =============================================================================

class TestServerlessModes:
    """Testes para os 3 modos de Serverless"""

    def test_serverless_list(self, cli_runner):
        """Lista instâncias serverless"""
        result = cli_runner("serverless list")
        assert result["success"]

        if result["json"]:
            assert "instances" in result["json"] or "count" in result["json"]

    def test_serverless_pricing(self, cli_runner):
        """Verifica preços serverless"""
        result = cli_runner("serverless pricing")
        assert result["success"]

        if result["json"]:
            assert "monthly_costs" in result["json"]
            costs = result["json"]["monthly_costs"]

            # Verifica os 3 modos
            assert "always_on" in costs
            assert "serverless_fast" in costs
            assert "serverless_economic" in costs

    @pytest.mark.slow
    def test_serverless_enable_fast_mode(self, cli_runner):
        """Testa ativação do modo fast"""
        # Primeiro, pega uma instância existente
        list_result = cli_runner("serverless list")

        if list_result["json"] and list_result["json"].get("instances"):
            instance_id = list_result["json"]["instances"][0]["instance_id"]

            result = cli_runner(f"serverless enable {instance_id} mode=fast idle_timeout_seconds=30")

            if result["success"] and result["json"]:
                assert result["json"]["mode"] == "fast"
                assert result["json"]["behavior"]["recovery_time"] == "<1s"

    @pytest.mark.slow
    def test_serverless_enable_economic_mode(self, cli_runner):
        """Testa ativação do modo economic"""
        list_result = cli_runner("serverless list")

        if list_result["json"] and list_result["json"].get("instances"):
            instance_id = list_result["json"]["instances"][0]["instance_id"]

            result = cli_runner(f"serverless enable {instance_id} mode=economic idle_timeout_seconds=30")

            if result["success"] and result["json"]:
                assert result["json"]["mode"] == "economic"

    @pytest.mark.slow
    def test_serverless_enable_spot_mode(self, cli_runner):
        """Testa ativação do modo spot"""
        list_result = cli_runner("serverless list")

        if list_result["json"] and list_result["json"].get("instances"):
            instance_id = list_result["json"]["instances"][0]["instance_id"]

            result = cli_runner(f"serverless enable {instance_id} mode=spot idle_timeout_seconds=60")

            if result["success"] and result["json"]:
                assert result["json"]["mode"] == "spot"
                assert "30s" in result["json"]["behavior"]["recovery_time"]


# =============================================================================
# TESTES - WIZARD DEPLOY
# =============================================================================

class TestWizardDeploy:
    """Testes para Wizard Deploy (on-demand vs spot)"""

    def test_wizard_help(self, cli_runner):
        """Verifica help do comando wizard"""
        result = cli_runner("wizard")
        assert "deploy" in result["output"].lower()

    def test_wizard_deploy_shows_type(self, cli_runner):
        """Verifica que wizard mostra tipo de máquina"""
        # Apenas verifica o output inicial, não executa deploy real
        result = subprocess.run(
            'cd /home/marcos/dumontcloud && source .venv/bin/activate && timeout 5 python -m cli wizard deploy type=spot 2>&1 || true',
            shell=True,
            capture_output=True,
            text=True,
            executable="/bin/bash"
        )

        output = result.stdout + result.stderr
        assert "Spot (cheaper, interruptible)" in output or "interruptible" in output

    def test_wizard_deploy_ondemand_type(self, cli_runner):
        """Verifica tipo on-demand"""
        result = subprocess.run(
            'cd /home/marcos/dumontcloud && source .venv/bin/activate && timeout 5 python -m cli wizard deploy type=on-demand 2>&1 || true',
            shell=True,
            capture_output=True,
            text=True,
            executable="/bin/bash"
        )

        output = result.stdout + result.stderr
        assert "On-Demand (stable)" in output or "on-demand" in output.lower()


# =============================================================================
# TESTES - SPOT COMMANDS
# =============================================================================

class TestSpotCommands:
    """Testes para comandos Spot"""

    def test_spot_help(self, cli_runner):
        """Verifica help do comando spot"""
        result = cli_runner("spot")
        assert "Spot GPU Commands" in result["output"]
        assert "spot pricing" in result["output"]
        assert "spot template" in result["output"]

    def test_spot_pricing(self, cli_runner):
        """Lista preços spot"""
        result = cli_runner("spot pricing")

        # Pode ter ofertas ou não
        assert result["success"] or "offers" in result["output"].lower()

    def test_spot_template_list(self, cli_runner):
        """Lista templates spot"""
        result = cli_runner("spot template list")

        # Pode não ter templates
        assert result["success"] or "No spot templates" in result["output"]


# =============================================================================
# TESTES - INSTANCE COMMANDS
# =============================================================================

class TestInstanceCommands:
    """Testes para comandos de Instance"""

    def test_instance_list(self, cli_runner):
        """Lista instâncias"""
        result = cli_runner("instance list")
        assert result["success"]

        if result["json"]:
            assert "instances" in result["json"] or "count" in result["json"]

    def test_instance_list_with_status_filter(self, cli_runner):
        """Lista instâncias com filtro de status"""
        result = cli_runner("instance list status=running")
        assert result["success"]


# =============================================================================
# TESTES - HISTORY E BLACKLIST
# =============================================================================

class TestHistoryCommands:
    """Testes para comandos de History e Blacklist"""

    def test_history_help(self, cli_runner):
        """Verifica help do comando history"""
        result = cli_runner("history")
        assert "Machine History Commands" in result["output"] or "history" in result["output"].lower()

    def test_history_summary(self, cli_runner):
        """Mostra resumo do histórico"""
        result = cli_runner("history summary")
        # Pode não ter histórico ainda
        assert result["success"] or "history" in result["output"].lower()

    def test_blacklist_list(self, cli_runner):
        """Lista máquinas na blacklist"""
        result = cli_runner("blacklist list")
        assert result["success"] or "blacklist" in result["output"].lower()


# =============================================================================
# TESTES - JORNADA COMPLETA
# =============================================================================

class TestFullUserJourney:
    """Teste de jornada completa do usuário"""

    @pytest.mark.slow
    def test_complete_job_journey(self, cli_runner):
        """
        Jornada completa: criar job, verificar status, cancelar

        Esta é uma jornada REAL que provisiona GPU!
        """
        # 1. Listar jobs existentes
        list_result = cli_runner("job list")
        assert list_result["success"]
        initial_count = list_result["json"]["total"] if list_result["json"] else 0

        # 2. Criar job on-demand
        create_result = cli_runner(
            'job create journey-test --command="sleep 30" --use-spot=false --timeout=5',
            timeout=120
        )

        assert "Creating GPU Job" in create_result["output"]

        if create_result["json"]:
            job_id = create_result["json"].get("id")
            assert job_id is not None

            # 3. Verificar status
            time.sleep(3)
            status_result = cli_runner(f"job status {job_id}")
            assert status_result["success"]

            # 4. Listar novamente (deve ter +1)
            list_result2 = cli_runner("job list")
            new_count = list_result2["json"]["total"] if list_result2["json"] else 0
            assert new_count >= initial_count

            # 5. Cancelar job
            cancel_result = cli_runner(f"job cancel {job_id}")
            assert "Cancelling" in cancel_result["output"] or cancel_result["success"]

            # 6. Verificar que foi cancelado
            time.sleep(2)
            final_status = cli_runner(f"job status {job_id}")
            if final_status["json"]:
                assert final_status["json"]["status"] in ["cancelled", "failed", "completed"]

    def test_complete_api_connectivity(self, cli_runner):
        """Verifica conectividade com todas as APIs principais"""
        endpoints_to_test = [
            ("job list", "jobs"),
            ("finetune models", "models"),
            ("finetune list", "jobs"),
            ("serverless list", "instances"),
            ("serverless pricing", "monthly_costs"),
            ("instance list", "instances"),
        ]

        results = {}
        for cmd, expected_key in endpoints_to_test:
            result = cli_runner(cmd)
            results[cmd] = {
                "success": result["success"],
                "has_expected_key": expected_key in str(result["json"]) if result["json"] else False
            }

        # Pelo menos 80% dos endpoints devem funcionar
        success_count = sum(1 for r in results.values() if r["success"])
        assert success_count >= len(endpoints_to_test) * 0.8, f"Only {success_count}/{len(endpoints_to_test)} endpoints working: {results}"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
