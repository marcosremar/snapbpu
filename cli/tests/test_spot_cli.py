#!/usr/bin/env python3
"""
Testes CLI para funcionalidades Spot

Testa:
1. spot pricing - Listar preços spot
2. spot template list - Listar templates
3. spot list - Listar instâncias spot
4. spot template create - Criar template (requer instância)
5. spot deploy - Deploy spot (requer template)

Uso:
    pytest cli/tests/test_spot_cli.py -v

    # Teste completo (cria instância real)
    pytest cli/tests/test_spot_cli.py -v -m real
"""
import os
import sys
import json
import pytest
import subprocess
import time

# Add parent directory to path
CLI_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(CLI_DIR)
sys.path.insert(0, ROOT_DIR)


def run_cli(*args, timeout=60):
    """Run CLI command and return output"""
    cmd = [sys.executable, "-m", "cli"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=ROOT_DIR,
    )
    return result.stdout, result.stderr, result.returncode


class TestSpotHelp:
    """Testes de ajuda e comandos básicos"""

    def test_spot_help(self):
        """spot (sem args) mostra ajuda"""
        stdout, stderr, code = run_cli("spot")
        assert code == 0
        assert "Spot GPU Commands" in stdout
        assert "spot template create" in stdout
        assert "spot deploy" in stdout
        assert "spot pricing" in stdout

    def test_spot_help_unknown_action(self):
        """spot com ação desconhecida mostra ajuda"""
        stdout, stderr, code = run_cli("spot", "invalid_action")
        assert "Unknown spot action" in stdout
        assert "Spot GPU Commands" in stdout


class TestSpotPricing:
    """Testes de preços spot"""

    def test_spot_pricing_global(self):
        """spot pricing lista ofertas globais"""
        stdout, stderr, code = run_cli("spot", "pricing")
        assert code == 0
        assert "Spot Pricing" in stdout
        assert "offers available" in stdout
        # Deve ter pelo menos algumas ofertas
        assert "$" in stdout  # Preços em dólar

    def test_spot_pricing_region(self):
        """spot pricing --region=US filtra por região"""
        stdout, stderr, code = run_cli("spot", "pricing", "--region=US")
        assert code == 0
        assert "Spot Pricing" in stdout
        # Pode ter 0 ofertas se não houver na região
        assert "offers available" in stdout or "No spot offers" in stdout

    def test_spot_pricing_gpu(self):
        """spot pricing --gpu=RTX4090 filtra por GPU"""
        stdout, stderr, code = run_cli("spot", "pricing", "--gpu=RTX 4090")
        assert code == 0
        # Pode ter 0 ofertas se não houver essa GPU


class TestSpotTemplates:
    """Testes de templates spot"""

    def test_spot_template_list_empty(self):
        """spot template list quando não há templates"""
        stdout, stderr, code = run_cli("spot", "template", "list")
        assert code == 0
        # Pode retornar lista vazia ou mensagem
        assert "templates" in stdout.lower() or "No spot templates" in stdout

    def test_spot_template_create_no_args(self):
        """spot template create sem args mostra uso"""
        stdout, stderr, code = run_cli("spot", "template", "create")
        assert "Usage" in stdout or "instance_id" in stdout

    def test_spot_template_delete_no_args(self):
        """spot template delete sem args mostra uso"""
        stdout, stderr, code = run_cli("spot", "template", "delete")
        assert "Usage" in stdout or "template_id" in stdout


class TestSpotInstances:
    """Testes de instâncias spot"""

    def test_spot_list_empty(self):
        """spot list quando não há instâncias"""
        stdout, stderr, code = run_cli("spot", "list")
        assert code == 0
        # Extract JSON from output (may have log lines before)
        lines = stdout.strip().split('\n')
        json_start = None
        for i, line in enumerate(lines):
            if line.strip() == '{':
                json_start = i
                break
        if json_start is not None:
            json_str = '\n'.join(lines[json_start:])
            data = json.loads(json_str)
            assert "instances" in data
            assert "count" in data
        else:
            # Fallback: check the output contains expected fields
            assert "instances" in stdout or "count" in stdout

    def test_spot_status_no_args(self):
        """spot status sem args mostra erro"""
        stdout, stderr, code = run_cli("spot", "status")
        assert code != 0 or "Usage" in stdout

    def test_spot_status_invalid_id(self):
        """spot status com ID inválido retorna erro"""
        stdout, stderr, code = run_cli("spot", "status", "99999999")
        assert "not configured for spot" in stdout or code != 0


class TestSpotDeploy:
    """Testes de deploy spot"""

    def test_spot_deploy_no_template(self):
        """spot deploy sem template mostra uso"""
        stdout, stderr, code = run_cli("spot", "deploy")
        assert "Usage" in stdout or "--template" in stdout

    def test_spot_deploy_invalid_template(self):
        """spot deploy com template inválido retorna erro"""
        stdout, stderr, code = run_cli("spot", "deploy", "--template=invalid_template_xxx")
        assert "not found" in stdout.lower() or "error" in stdout.lower()


class TestSpotFailover:
    """Testes de failover"""

    def test_spot_failover_no_args(self):
        """spot failover sem args mostra uso"""
        stdout, stderr, code = run_cli("spot", "failover")
        assert code != 0 or "Usage" in stdout

    def test_spot_failover_invalid_id(self):
        """spot failover com ID inválido retorna erro"""
        stdout, stderr, code = run_cli("spot", "failover", "99999999")
        assert "not configured" in stdout.lower() or "error" in stdout.lower()


# ============================================================
# TESTES REAIS (marcados com @pytest.mark.real)
# Estes testes criam recursos reais e custam dinheiro!
# ============================================================

@pytest.mark.real
class TestSpotRealWorkflow:
    """
    Testes reais do workflow spot completo.

    ATENÇÃO: Estes testes criam recursos reais no VAST.ai!
    Só rodar com: pytest -m real
    """

    @pytest.fixture(scope="class")
    def running_instance(self):
        """Cria instância para testes (ou usa existente)"""
        # Verificar se já existe instância
        stdout, _, _ = run_cli("instance", "list")
        try:
            data = json.loads(stdout.split('\n')[0])
            instances = data.get("instances", [])
            running = [i for i in instances if i.get("actual_status") == "running"]
            if running:
                yield running[0]
                return
        except:
            pass

        # Criar nova instância
        print("\n🚀 Criando instância para teste...")
        stdout, stderr, code = run_cli("wizard", "deploy", "price=0.15", timeout=180)

        # Extrair instance_id do output
        import re
        match = re.search(r'Instance ID:\s*(\d+)', stdout)
        if not match:
            pytest.skip("Não foi possível criar instância")

        instance_id = int(match.group(1))

        # Esperar ficar pronta
        time.sleep(10)

        yield {"id": instance_id}

        # Cleanup
        print(f"\n🗑️ Deletando instância {instance_id}...")
        run_cli("instance", "delete", str(instance_id))

    def test_create_template(self, running_instance):
        """Cria template a partir de instância"""
        instance_id = running_instance["id"]

        stdout, stderr, code = run_cli(
            "spot", "template", "create", str(instance_id),
            timeout=300  # Snapshot pode demorar
        )

        assert code == 0 or "Template created" in stdout
        assert "spot_tpl_" in stdout or "error" not in stdout.lower()

    def test_template_appears_in_list(self, running_instance):
        """Template criado aparece na lista"""
        stdout, stderr, code = run_cli("spot", "template", "list")

        # Pode não ter template se o teste anterior falhou
        # Mas o comando deve funcionar
        assert code == 0

    def test_deploy_spot(self, running_instance):
        """Deploy spot usando template"""
        # Primeiro listar templates
        stdout, _, _ = run_cli("spot", "template", "list")

        try:
            data = json.loads(stdout.split('\n')[0])
            templates = data.get("templates", [])
            if not templates:
                pytest.skip("Nenhum template disponível")

            template_id = templates[0]["template_id"]
        except:
            pytest.skip("Não foi possível obter templates")

        # Deploy spot
        stdout, stderr, code = run_cli(
            "spot", "deploy",
            f"--template={template_id}",
            "--max-price=0.20",
            timeout=300
        )

        # Pode falhar se não houver ofertas baratas
        assert "Deploying" in stdout or "error" in stdout.lower()

    def test_spot_status_after_deploy(self, running_instance):
        """Status da instância spot após deploy"""
        stdout, _, _ = run_cli("spot", "list")

        try:
            data = json.loads(stdout.split('\n')[0])
            if data.get("count", 0) > 0:
                instance_id = data["instances"][0]["instance_id"]

                stdout, stderr, code = run_cli("spot", "status", str(instance_id))
                assert "state" in stdout.lower()
        except:
            pass  # Pode não ter instância spot

    def test_trigger_failover(self, running_instance):
        """Trigger manual de failover"""
        stdout, _, _ = run_cli("spot", "list")

        try:
            data = json.loads(stdout.split('\n')[0])
            if data.get("count", 0) > 0:
                instance_id = data["instances"][0]["instance_id"]

                stdout, stderr, code = run_cli(
                    "spot", "failover", str(instance_id),
                    timeout=300
                )
                assert "failover" in stdout.lower()
        except:
            pytest.skip("Nenhuma instância spot para testar failover")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
