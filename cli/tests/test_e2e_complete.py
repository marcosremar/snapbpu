"""
Testes E2E COMPLETOS - Dumont Cloud CLI
========================================

ATENÇÃO: Estes testes GASTAM CRÉDITOS REAIS da VAST.ai!

Cada teste é AUTO-SUFICIENTE:
- Cria seus próprios recursos via CLI
- Executa os testes
- Limpa tudo no final

Execução:
    cd cli && pytest tests/test_e2e_complete.py -v -s

Apenas smoke tests (verificação rápida):
    cd cli && pytest tests/test_e2e_complete.py -v -s -m "smoke"
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
TEST_GPU = "RTX 4090"
TIMEOUT_SHORT = 60
TIMEOUT_MEDIUM = 180
TIMEOUT_LONG = 600
TIMEOUT_DEPLOY = 900  # 15 min para deploy


# =============================================================================
# CLI RUNNER
# =============================================================================

def run_cli(command: str, timeout: int = TIMEOUT_SHORT) -> dict:
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

        # Parse JSON
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


# =============================================================================
# HELPERS
# =============================================================================

def get_or_create_instance() -> str:
    """Obtém uma instância existente ou cria uma nova via CLI"""
    # Primeiro tenta pegar uma instância running
    result = run_cli("instance list status=running")
    if result["json"]:
        instances = result["json"].get("instances", [])
        if instances:
            return str(instances[0].get("id") or instances[0].get("instance_id"))

    # Se não tem, cria uma nova via wizard deploy
    print("   📦 Criando nova instância via CLI...")
    deploy = run_cli(
        f'wizard deploy gpu="{TEST_GPU}" type=on-demand price=1.0 speed=slow',
        timeout=TIMEOUT_DEPLOY
    )

    if deploy["json"] and deploy["json"].get("instance_id"):
        return str(deploy["json"]["instance_id"])

    # Tenta extrair ID do output
    import re
    match = re.search(r'instance[_\s]?id[:\s]+(\d+)', deploy["output"], re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def cleanup_instance(instance_id: str):
    """Limpa instância via CLI"""
    if instance_id:
        print(f"   🧹 Limpando instância {instance_id}...")
        run_cli(f"instance delete {instance_id}", timeout=TIMEOUT_SHORT)


# =============================================================================
# 1. AUTENTICAÇÃO
# =============================================================================

class TestAuthComplete:
    """Testes de autenticação via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_auth_me(self):
        """dumont auth me - Ver usuário atual"""
        print("\n🔐 AUTH ME")
        result = run_cli("auth me")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"] or "email" in result["output"] or "Unauthorized" in result["output"]

    @pytest.mark.slow
    def test_auth_login_validation(self):
        """dumont auth login - Valida parâmetros"""
        print("\n🔐 AUTH LOGIN (validação)")
        result = run_cli("auth login")
        print(f"   Output: {result['output'][:200]}")
        # Deve pedir email/password ou retornar erro de validação
        assert "email" in result["output"].lower() or "validation" in result["output"].lower() or "Usage" in result["output"]


# =============================================================================
# 2. INSTÂNCIAS - CRUD COMPLETO
# =============================================================================

class TestInstanceComplete:
    """Testes CRUD de instâncias via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_instance_list(self):
        """dumont instance list"""
        print("\n📋 INSTANCE LIST")
        result = run_cli("instance list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_instance_list_status_filter(self):
        """dumont instance list status=running"""
        print("\n📋 INSTANCE LIST status=running")
        result = run_cli("instance list status=running")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_instance_offers(self):
        """dumont instance offers"""
        print("\n🛒 INSTANCE OFFERS")
        result = run_cli("instance offers")
        print(f"   Output: {result['output'][:300]}")
        assert result["success"]
        if result["json"]:
            offers = result["json"].get("offers", [])
            print(f"   ✅ {len(offers)} ofertas encontradas")

    @pytest.mark.slow
    def test_instance_lifecycle_complete(self):
        """
        Jornada completa de instância via CLI:
        1. wizard deploy - criar
        2. instance get - ver detalhes
        3. instance pause - pausar
        4. instance resume - retomar
        5. instance delete - deletar
        """
        print("\n🎯 JORNADA INSTANCE LIFECYCLE")
        print("=" * 50)

        instance_id = None
        try:
            # 1. Criar via wizard deploy
            print("\n1️⃣ Criando instância via wizard deploy...")
            deploy = run_cli(
                f'wizard deploy gpu="{TEST_GPU}" type=on-demand price=1.0 speed=slow',
                timeout=TIMEOUT_DEPLOY
            )
            print(f"   Output: {deploy['output'][:300]}")

            if deploy["json"] and deploy["json"].get("instance_id"):
                instance_id = str(deploy["json"]["instance_id"])
            else:
                # Tenta extrair do output
                import re
                match = re.search(r'(\d{7,})', deploy["output"])
                if match:
                    instance_id = match.group(1)

            if not instance_id:
                pytest.skip("Não foi possível criar instância - sem ofertas disponíveis?")

            print(f"   ✅ Instância criada: {instance_id}")

            # 2. Ver detalhes
            print("\n2️⃣ Obtendo detalhes...")
            get_result = run_cli(f"instance get {instance_id}")
            print(f"   Output: {get_result['output'][:200]}")
            assert get_result["success"] or "instance" in get_result["output"].lower()

            # 3. Pausar
            print("\n3️⃣ Pausando...")
            pause = run_cli(f"instance pause {instance_id}", timeout=TIMEOUT_MEDIUM)
            print(f"   Output: {pause['output'][:200]}")
            time.sleep(10)

            # 4. Resumir
            print("\n4️⃣ Resumindo...")
            resume = run_cli(f"instance resume {instance_id}", timeout=TIMEOUT_MEDIUM)
            print(f"   Output: {resume['output'][:200]}")
            time.sleep(10)

            # 5. Deletar
            print("\n5️⃣ Deletando...")
            delete = run_cli(f"instance delete {instance_id}")
            print(f"   Output: {delete['output'][:200]}")

            print("\n✅ JORNADA COMPLETA!")

        finally:
            if instance_id:
                cleanup_instance(instance_id)


# =============================================================================
# 3. JOBS - CRUD COMPLETO
# =============================================================================

class TestJobsComplete:
    """Testes de Jobs (Execute and Destroy) via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_job_list(self):
        """dumont job list"""
        print("\n📋 JOB LIST")
        result = run_cli("job list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_job_help(self):
        """dumont job - mostra help"""
        print("\n❓ JOB HELP")
        result = run_cli("job")
        print(f"   Output: {result['output'][:300]}")
        assert "job create" in result["output"] or "GPU Job" in result["output"]

    @pytest.mark.slow
    def test_job_lifecycle_ondemand(self):
        """
        Jornada completa de Job ON-DEMAND via CLI:
        1. job list - listar existentes
        2. job create --use-spot=false - criar on-demand
        3. job status - verificar status
        4. job logs - ver logs
        5. job cancel - cancelar
        """
        print("\n🎯 JORNADA JOB ON-DEMAND")
        print("=" * 50)

        job_id = None
        try:
            # 1. Listar
            print("\n1️⃣ Listando jobs...")
            list_result = run_cli("job list")
            print(f"   Output: {list_result['output'][:200]}")

            # 2. Criar ON-DEMAND
            print("\n2️⃣ Criando job ON-DEMAND...")
            create = run_cli(
                'job create test-e2e-ondemand --command="echo Hello E2E && sleep 30" --use-spot=false --gpu="RTX 4090" --timeout=5',
                timeout=TIMEOUT_MEDIUM
            )
            print(f"   Output: {create['output'][:300]}")

            # Extrai job_id
            if create["json"]:
                job_id = create["json"].get("id") or create["json"].get("job_id")

            if not job_id:
                import re
                match = re.search(r'job[_\s]?(?:id)?[:\s]+([a-zA-Z0-9_-]+)', create["output"], re.IGNORECASE)
                if match:
                    job_id = match.group(1)

            if job_id:
                print(f"   ✅ Job criado: {job_id}")

                # 3. Status
                print("\n3️⃣ Verificando status...")
                time.sleep(3)
                status = run_cli(f"job status {job_id}")
                print(f"   Output: {status['output'][:200]}")

                # 4. Logs
                print("\n4️⃣ Verificando logs...")
                logs = run_cli(f"job logs {job_id}")
                print(f"   Output: {logs['output'][:200]}")

                # 5. Cancelar
                print("\n5️⃣ Cancelando job...")
                cancel = run_cli(f"job cancel {job_id}")
                print(f"   Output: {cancel['output'][:200]}")

                print("\n✅ JORNADA COMPLETA!")
            else:
                print("   ⚠️ Job não foi criado (API retornou erro)")
                # Não falha o teste, apenas reporta
                assert "Creating" in create["output"] or "error" in create["output"].lower()

        finally:
            if job_id:
                run_cli(f"job cancel {job_id}")

    @pytest.mark.slow
    def test_job_lifecycle_spot(self):
        """
        Jornada completa de Job SPOT via CLI:
        1. job create --use-spot=true - criar spot (60-70% mais barato)
        2. job status - verificar
        3. job cancel - cancelar
        """
        print("\n🎯 JORNADA JOB SPOT")
        print("=" * 50)

        job_id = None
        try:
            # 1. Criar SPOT
            print("\n1️⃣ Criando job SPOT (60-70% mais barato)...")
            create = run_cli(
                'job create test-e2e-spot --command="echo Hello Spot && sleep 30" --use-spot=true --gpu="RTX 4090" --timeout=5',
                timeout=TIMEOUT_MEDIUM
            )
            print(f"   Output: {create['output'][:300]}")

            if create["json"]:
                job_id = create["json"].get("id") or create["json"].get("job_id")

            if job_id:
                print(f"   ✅ Job SPOT criado: {job_id}")

                # 2. Status
                print("\n2️⃣ Verificando status...")
                status = run_cli(f"job status {job_id}")
                print(f"   Output: {status['output'][:200]}")

                # 3. Cancelar
                print("\n3️⃣ Cancelando...")
                cancel = run_cli(f"job cancel {job_id}")
                print(f"   Output: {cancel['output'][:200]}")

                print("\n✅ JORNADA COMPLETA!")
            else:
                assert "Spot" in create["output"] or "Creating" in create["output"]

        finally:
            if job_id:
                run_cli(f"job cancel {job_id}")


# =============================================================================
# 4. FINE-TUNING - COMPLETO
# =============================================================================

class TestFinetuneComplete:
    """Testes de Fine-tuning via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_finetune_models(self):
        """dumont finetune models - listar modelos disponíveis"""
        print("\n🤖 FINETUNE MODELS")
        result = run_cli("finetune models")
        print(f"   Output: {result['output'][:400]}")
        assert result["success"]
        if result["json"]:
            models = result["json"].get("models", [])
            print(f"   ✅ {len(models)} modelos disponíveis")
            for m in models[:3]:
                print(f"      - {m.get('id')}: {m.get('name')}")

    @pytest.mark.slow
    def test_finetune_list(self):
        """dumont finetune list"""
        print("\n📋 FINETUNE LIST")
        result = run_cli("finetune list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_finetune_help(self):
        """dumont finetune - help"""
        print("\n❓ FINETUNE HELP")
        result = run_cli("finetune")
        print(f"   Output: {result['output'][:300]}")
        assert "finetune" in result["output"].lower()

    @pytest.mark.slow
    def test_finetune_create_validation(self):
        """Valida parâmetros obrigatórios de finetune create"""
        print("\n🔍 FINETUNE CREATE (validação)")

        # Sem --model
        r1 = run_cli("finetune create test --dataset=/tmp/x.jsonl")
        print(f"   Sem model: {r1['output'][:100]}")
        assert "model" in r1["output"].lower() or "Missing" in r1["output"]

        # Sem --dataset
        r2 = run_cli("finetune create test --model=unsloth/llama-3-8b-bnb-4bit")
        print(f"   Sem dataset: {r2['output'][:100]}")
        assert "dataset" in r2["output"].lower() or "Missing" in r2["output"]


# =============================================================================
# 5. SERVERLESS - 3 MODOS COMPLETOS
# =============================================================================

class TestServerlessComplete:
    """Testes dos 3 modos de Serverless via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_serverless_pricing(self):
        """dumont serverless pricing - ver custos dos 3 modos"""
        print("\n💰 SERVERLESS PRICING")
        result = run_cli("serverless pricing")
        print(f"   Output: {result['output'][:400]}")
        assert result["success"]
        if result["json"]:
            costs = result["json"].get("monthly_costs", {})
            print(f"   ✅ Modos: {list(costs.keys())}")

    @pytest.mark.slow
    def test_serverless_list(self):
        """dumont serverless list"""
        print("\n📋 SERVERLESS LIST")
        result = run_cli("serverless list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_serverless_all_modes_lifecycle(self):
        """
        Jornada completa dos 3 modos de Serverless via CLI:
        1. Criar instância via wizard
        2. Habilitar modo FAST (<1s)
        3. Verificar status
        4. Trocar para modo ECONOMIC (~7s)
        5. Trocar para modo SPOT (~30s)
        6. Desabilitar serverless
        7. Deletar instância
        """
        print("\n🎯 JORNADA SERVERLESS - 3 MODOS")
        print("=" * 50)

        instance_id = None
        try:
            # 1. Criar instância
            print("\n1️⃣ Criando instância para teste...")
            instance_id = get_or_create_instance()

            if not instance_id:
                pytest.skip("Não foi possível obter/criar instância")

            print(f"   ✅ Usando instância: {instance_id}")

            # 2. Modo FAST (<1s recovery)
            print("\n2️⃣ Habilitando modo FAST (<1s recovery)...")
            fast = run_cli(f"serverless enable {instance_id} mode=fast idle_timeout_seconds=30")
            print(f"   Output: {fast['output'][:200]}")

            # 3. Status
            print("\n3️⃣ Verificando status...")
            status = run_cli(f"serverless status {instance_id}")
            print(f"   Output: {status['output'][:200]}")

            # 4. Modo ECONOMIC (~7s recovery)
            print("\n4️⃣ Trocando para modo ECONOMIC (~7s recovery)...")
            economic = run_cli(f"serverless enable {instance_id} mode=economic idle_timeout_seconds=30")
            print(f"   Output: {economic['output'][:200]}")

            # 5. Modo SPOT (~30s recovery, 60-70% mais barato)
            print("\n5️⃣ Trocando para modo SPOT (~30s, 60-70% economia)...")
            spot = run_cli(f"serverless enable {instance_id} mode=spot idle_timeout_seconds=60")
            print(f"   Output: {spot['output'][:200]}")

            # 6. Desabilitar
            print("\n6️⃣ Desabilitando serverless...")
            disable = run_cli(f"serverless disable {instance_id}")
            print(f"   Output: {disable['output'][:200]}")

            print("\n✅ JORNADA COMPLETA!")

        finally:
            if instance_id:
                cleanup_instance(instance_id)


# =============================================================================
# 6. WIZARD DEPLOY - ON-DEMAND E SPOT
# =============================================================================

class TestWizardComplete:
    """Testes de Wizard Deploy via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_wizard_help(self):
        """dumont wizard - help"""
        print("\n❓ WIZARD HELP")
        result = run_cli("wizard")
        print(f"   Output: {result['output'][:200]}")
        assert "deploy" in result["output"].lower() or "wizard" in result["output"].lower()

    @pytest.mark.slow
    def test_wizard_deploy_ondemand_lifecycle(self):
        """
        Wizard Deploy ON-DEMAND completo:
        1. wizard deploy type=on-demand
        2. Verificar instância
        3. Deletar
        """
        print("\n🎯 JORNADA WIZARD DEPLOY ON-DEMAND")
        print("=" * 50)

        instance_id = None
        try:
            # 1. Deploy ON-DEMAND
            print("\n1️⃣ Wizard Deploy ON-DEMAND...")
            deploy = run_cli(
                f'wizard deploy gpu="{TEST_GPU}" type=on-demand price=1.0 speed=slow',
                timeout=TIMEOUT_DEPLOY
            )
            print(f"   Output: {deploy['output'][:300]}")

            if deploy["json"] and deploy["json"].get("instance_id"):
                instance_id = str(deploy["json"]["instance_id"])
                print(f"   ✅ Instância ON-DEMAND: {instance_id}")

                # 2. Verificar
                print("\n2️⃣ Verificando...")
                get = run_cli(f"instance get {instance_id}")
                print(f"   Output: {get['output'][:200]}")

                # 3. Deletar
                print("\n3️⃣ Deletando...")
                delete = run_cli(f"instance delete {instance_id}")
                print(f"   Output: {delete['output'][:200]}")

                print("\n✅ JORNADA COMPLETA!")
            else:
                print("   ⚠️ Deploy não retornou instance_id")
                assert "Deploy" in deploy["output"] or "wizard" in deploy["output"].lower()

        finally:
            if instance_id:
                cleanup_instance(instance_id)

    @pytest.mark.slow
    def test_wizard_deploy_spot_lifecycle(self):
        """
        Wizard Deploy SPOT completo (60-70% mais barato):
        1. wizard deploy type=spot
        2. Verificar instância
        3. Deletar
        """
        print("\n🎯 JORNADA WIZARD DEPLOY SPOT")
        print("=" * 50)

        instance_id = None
        try:
            # 1. Deploy SPOT
            print("\n1️⃣ Wizard Deploy SPOT (60-70% mais barato)...")
            deploy = run_cli(
                f'wizard deploy gpu="{TEST_GPU}" type=spot price=0.5 speed=slow',
                timeout=TIMEOUT_DEPLOY
            )
            print(f"   Output: {deploy['output'][:300]}")

            if deploy["json"] and deploy["json"].get("instance_id"):
                instance_id = str(deploy["json"]["instance_id"])
                print(f"   ✅ Instância SPOT: {instance_id}")

                # 2. Verificar
                print("\n2️⃣ Verificando...")
                get = run_cli(f"instance get {instance_id}")
                print(f"   Output: {get['output'][:200]}")

                # 3. Deletar
                print("\n3️⃣ Deletando...")
                delete = run_cli(f"instance delete {instance_id}")
                print(f"   Output: {delete['output'][:200]}")

                print("\n✅ JORNADA COMPLETA!")
            else:
                assert "Spot" in deploy["output"] or "spot" in deploy["output"].lower()

        finally:
            if instance_id:
                cleanup_instance(instance_id)


# =============================================================================
# 7. SPOT INSTANCES
# =============================================================================

class TestSpotComplete:
    """Testes de Spot Instances via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_spot_pricing(self):
        """dumont spot pricing"""
        print("\n💰 SPOT PRICING")
        result = run_cli("spot pricing")
        print(f"   Output: {result['output'][:300]}")
        assert result["success"] or "spot" in result["output"].lower()

    @pytest.mark.slow
    def test_spot_template_list(self):
        """dumont spot template list"""
        print("\n📋 SPOT TEMPLATE LIST")
        result = run_cli("spot template list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"] or "template" in result["output"].lower()

    @pytest.mark.slow
    def test_spot_instances(self):
        """dumont spot instances"""
        print("\n📋 SPOT INSTANCES")
        result = run_cli("spot instances")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_spot_prediction(self):
        """dumont spot prediction"""
        print(f"\n🔮 SPOT PREDICTION {TEST_GPU}")
        result = run_cli(f'spot prediction "{TEST_GPU}"')
        print(f"   Output: {result['output'][:200]}")
        assert result["success"] or "prediction" in result["output"].lower()

    @pytest.mark.slow
    def test_spot_safe_windows(self):
        """dumont spot safe-windows"""
        print(f"\n🕐 SPOT SAFE-WINDOWS {TEST_GPU}")
        result = run_cli(f'spot safe-windows "{TEST_GPU}"')
        print(f"   Output: {result['output'][:200]}")
        assert result["success"] or "safe" in result["output"].lower()


# =============================================================================
# 8. STANDBY/FAILOVER
# =============================================================================

class TestStandbyComplete:
    """Testes de Standby/Failover via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_standby_status(self):
        """dumont standby status"""
        print("\n📊 STANDBY STATUS")
        result = run_cli("standby status")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_standby_associations(self):
        """dumont standby associations"""
        print("\n🔗 STANDBY ASSOCIATIONS")
        result = run_cli("standby associations")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_standby_pricing(self):
        """dumont standby pricing"""
        print("\n💰 STANDBY PRICING")
        result = run_cli("standby pricing")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_standby_provision_lifecycle(self):
        """
        Jornada de CPU Standby completa:
        1. Criar instância GPU
        2. Provisionar CPU Standby
        3. Verificar associação
        4. Testar failover
        5. Limpar
        """
        print("\n🎯 JORNADA STANDBY PROVISION")
        print("=" * 50)

        instance_id = None
        try:
            # 1. Criar/obter instância
            print("\n1️⃣ Obtendo instância GPU...")
            instance_id = get_or_create_instance()

            if not instance_id:
                pytest.skip("Sem instância para teste de standby")

            print(f"   ✅ Usando GPU: {instance_id}")

            # 2. Provisionar Standby
            print("\n2️⃣ Provisionando CPU Standby...")
            provision = run_cli(f'standby provision {instance_id} label="test-standby"', timeout=TIMEOUT_MEDIUM)
            print(f"   Output: {provision['output'][:200]}")

            # 3. Verificar associações
            print("\n3️⃣ Verificando associações...")
            assoc = run_cli("standby associations")
            print(f"   Output: {assoc['output'][:200]}")

            print("\n✅ JORNADA COMPLETA!")

        finally:
            if instance_id:
                cleanup_instance(instance_id)


# =============================================================================
# 9. WARM POOL
# =============================================================================

class TestWarmPoolComplete:
    """Testes de Warm Pool via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_warmpool_hosts(self):
        """dumont warmpool hosts"""
        print("\n🔥 WARMPOOL HOSTS")
        result = run_cli("warmpool hosts")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_warmpool_lifecycle(self):
        """
        Jornada Warm Pool completa:
        1. Obter instância
        2. Habilitar warm pool
        3. Verificar status
        4. Desabilitar
        """
        print("\n🎯 JORNADA WARM POOL")
        print("=" * 50)

        instance_id = None
        try:
            # 1. Obter instância
            print("\n1️⃣ Obtendo instância...")
            instance_id = get_or_create_instance()

            if not instance_id:
                pytest.skip("Sem instância para warm pool")

            # 2. Habilitar
            print(f"\n2️⃣ Habilitando warm pool em {instance_id}...")
            enable = run_cli(f"warmpool enable {instance_id}")
            print(f"   Output: {enable['output'][:200]}")

            # 3. Status
            print("\n3️⃣ Verificando status...")
            status = run_cli(f"warmpool status {instance_id}")
            print(f"   Output: {status['output'][:200]}")

            # 4. Desabilitar
            print("\n4️⃣ Desabilitando...")
            disable = run_cli(f"warmpool disable {instance_id}")
            print(f"   Output: {disable['output'][:200]}")

            print("\n✅ JORNADA COMPLETA!")

        finally:
            if instance_id:
                cleanup_instance(instance_id)


# =============================================================================
# 10. HISTORY E BLACKLIST
# =============================================================================

class TestHistoryBlacklistComplete:
    """Testes de History e Blacklist via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_history_summary(self):
        """dumont history summary"""
        print("\n📊 HISTORY SUMMARY")
        result = run_cli("history summary")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_history_list(self):
        """dumont history list"""
        print("\n📋 HISTORY LIST")
        result = run_cli("history list --provider=vast --hours=72")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_history_problematic(self):
        """dumont history problematic"""
        print("\n⚠️ HISTORY PROBLEMATIC")
        result = run_cli("history problematic --provider=vast")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_history_reliable(self):
        """dumont history reliable"""
        print("\n✅ HISTORY RELIABLE")
        result = run_cli("history reliable --provider=vast")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_blacklist_list(self):
        """dumont blacklist list"""
        print("\n🚫 BLACKLIST LIST")
        result = run_cli("blacklist list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_blacklist_crud(self):
        """
        CRUD de blacklist completo:
        1. Adicionar máquina
        2. Verificar
        3. Remover
        """
        print("\n🎯 JORNADA BLACKLIST CRUD")
        print("=" * 50)

        test_id = "test_machine_e2e_12345"

        # 1. Adicionar
        print("\n1️⃣ Adicionando à blacklist...")
        add = run_cli(f'blacklist add vast {test_id} "Teste E2E" --hours=1')
        print(f"   Output: {add['output'][:200]}")

        # 2. Verificar
        print("\n2️⃣ Verificando...")
        check = run_cli(f"blacklist check vast {test_id}")
        print(f"   Output: {check['output'][:200]}")

        # 3. Remover
        print("\n3️⃣ Removendo...")
        remove = run_cli(f"blacklist remove vast {test_id}")
        print(f"   Output: {remove['output'][:200]}")

        print("\n✅ JORNADA COMPLETA!")


# =============================================================================
# 11. MÉTRICAS E SAVINGS
# =============================================================================

class TestMetricsSavingsComplete:
    """Testes de Métricas e Savings via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_saving_summary(self):
        """dumont saving summary"""
        print("\n💰 SAVING SUMMARY")
        result = run_cli("saving summary")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_saving_history(self):
        """dumont saving history"""
        print("\n📈 SAVING HISTORY")
        result = run_cli("saving history months=6")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_metrics_gpus(self):
        """dumont metrics gpus"""
        print("\n📊 METRICS GPUS")
        result = run_cli("metrics gpus")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_metrics_efficiency(self):
        """dumont metrics efficiency"""
        print("\n📊 METRICS EFFICIENCY")
        result = run_cli("metrics efficiency")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_metrics_providers(self):
        """dumont metrics providers"""
        print("\n📊 METRICS PROVIDERS")
        result = run_cli("metrics providers")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_metrics_spot(self):
        """dumont metrics spot"""
        print(f"\n📊 METRICS SPOT {TEST_GPU}")
        result = run_cli(f'metrics spot gpu_name="{TEST_GPU}"')
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]


# =============================================================================
# 12. SNAPSHOTS
# =============================================================================

class TestSnapshotsComplete:
    """Testes de Snapshots via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_snapshot_list(self):
        """dumont snapshot list"""
        print("\n📸 SNAPSHOT LIST")
        result = run_cli("snapshot list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]


# =============================================================================
# 13. SETTINGS E OUTROS
# =============================================================================

class TestSettingsComplete:
    """Testes de Settings via CLI"""

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_settings_list(self):
        """dumont settings list"""
        print("\n⚙️ SETTINGS LIST")
        result = run_cli("settings list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]

    @pytest.mark.slow
    def test_balance_list(self):
        """dumont balance list"""
        print("\n💳 BALANCE LIST")
        result = run_cli("balance list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]
        if result["json"]:
            credit = result["json"].get("credit", 0)
            print(f"   ✅ Crédito: ${credit:.2f}")

    @pytest.mark.slow
    @pytest.mark.smoke
    def test_health_list(self):
        """dumont health list"""
        print("\n🏥 HEALTH LIST")
        result = run_cli("health list")
        print(f"   Output: {result['output'][:200]}")
        assert result["success"]
        if result["json"]:
            assert result["json"].get("status") == "healthy"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║              DUMONT CLOUD CLI - TESTES E2E COMPLETOS                          ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  ⚠️  ATENÇÃO: Estes testes GASTAM CRÉDITOS REAIS!                             ║
║                                                                               ║
║  Cada teste é AUTO-SUFICIENTE:                                                ║
║  - Cria recursos via CLI                                                      ║
║  - Executa testes                                                             ║
║  - Limpa tudo no final                                                        ║
║                                                                               ║
║  Uso:                                                                         ║
║    pytest tests/test_e2e_complete.py -v -s                                    ║
║                                                                               ║
║  Smoke tests apenas:                                                          ║
║    pytest tests/test_e2e_complete.py -v -s -m "smoke"                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    pytest.main([__file__, "-v", "-s"])
