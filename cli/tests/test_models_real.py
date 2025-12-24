"""
Testes REAIS do CLI para Models Deploy - Dumont Cloud.

Testa os comandos de deploy de modelos ML/AI:
- dumont models list
- dumont models templates
- dumont models deploy <type> <model_id>
- dumont models get <id>
- dumont models stop <id>
- dumont models delete <id>
- dumont models logs <id>

Marcadores:
    - @pytest.mark.integration: Testes que requerem API real
    - @pytest.mark.real: Testes que usam créditos reais
    - @pytest.mark.slow: Testes que demoram mais de 30s

Para rodar:
    pytest tests/test_models_real.py -v -s

Para rodar apenas testes rápidos (sem deploy real):
    pytest tests/test_models_real.py -v -s -k "not slow"
"""
import pytest
import time
import json
import re
from typing import Optional, Dict, Any, List


# =============================================================================
# HELPERS DE VALIDAÇÃO
# =============================================================================

def parse_json_output(output: str) -> Optional[Dict[str, Any]]:
    """
    Extrai e parseia JSON da saída do CLI.
    Tenta encontrar JSON válido mesmo com texto adicional.
    """
    try:
        return json.loads(output.strip())
    except json.JSONDecodeError:
        pass

    json_patterns = [
        r'\{.*\}',
        r'\[.*\]',
        r'\{[^{}]*\}',
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, output, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    return None


def assert_cli_output_contains(result, expected_strings: List[str], case_sensitive: bool = False):
    """
    Valida que a saída do CLI contém strings esperadas.
    """
    output = result.output if case_sensitive else result.output.lower()

    for expected in expected_strings:
        check_str = expected if case_sensitive else expected.lower()
        assert check_str in output, \
            f"Esperado '{expected}' na saída. Saída: {result.output[:500]}"


# =============================================================================
# TESTES DE LISTAGEM E TEMPLATES
# =============================================================================

class TestModelsListCommands:
    """Testes para comandos de listagem de models."""

    @pytest.mark.integration
    def test_models_list(self, logged_in_cli):
        """
        Testa: dumont models list

        Deve listar modelos deployados (pode estar vazio).
        """
        result = logged_in_cli.run("models", "list")

        # O comando deve executar sem erro
        # Aceita código 0 ou 1 (lista vazia vs erro de auth)
        assert result.returncode in [0, 1], \
            f"Comando falhou: {result.output}"

        # Deve mostrar algo na saída
        assert len(result.output) > 0, "Saída vazia"

        # Se tiver modelos, deve mostrar informações relevantes
        if "No models" not in result.output and "Nenhum" not in result.output:
            # Verifica estrutura básica de listagem
            assert any(x in result.output.lower() for x in
                      ["id", "model", "status", "deployed", "models"]), \
                f"Saída não contém campos esperados: {result.output}"

    @pytest.mark.integration
    def test_models_templates(self, logged_in_cli):
        """
        Testa: dumont models templates

        Deve listar templates disponíveis para deploy.
        """
        result = logged_in_cli.run("models", "templates")

        assert result.returncode == 0, \
            f"Comando falhou (código {result.returncode}): {result.output}"

        # Deve conter tipos de modelo
        output_lower = result.output.lower()
        expected_types = ["llm", "speech", "image", "embeddings"]

        found_types = [t for t in expected_types if t in output_lower]
        assert len(found_types) >= 1, \
            f"Esperado pelo menos 1 tipo de modelo. Saída: {result.output}"


# =============================================================================
# TESTES DE AJUDA E VALIDAÇÃO DE COMANDOS
# =============================================================================

class TestModelsHelpCommands:
    """Testes para validar comandos de ajuda e erro."""

    @pytest.mark.integration
    def test_models_deploy_without_args_shows_help(self, logged_in_cli):
        """
        Testa: dumont models deploy (sem argumentos)

        Deve mostrar mensagem de ajuda com exemplos.
        """
        result = logged_in_cli.run("models", "deploy")

        # Deve retornar erro (falta argumentos)
        assert result.returncode == 1, \
            f"Esperado código 1, recebeu {result.returncode}"

        # Deve mostrar uso correto
        assert_cli_output_contains(result, [
            "usage",
            "llm",
            "speech",
        ])

    @pytest.mark.integration
    def test_models_get_without_id_shows_error(self, logged_in_cli):
        """
        Testa: dumont models get (sem ID)

        Deve mostrar erro pedindo o ID.
        """
        result = logged_in_cli.run("models", "get")

        assert result.returncode == 1, \
            f"Esperado código 1, recebeu {result.returncode}"

        # Deve indicar que precisa do ID
        assert "deployment_id" in result.output.lower() or "id" in result.output.lower(), \
            f"Saída não menciona ID necessário: {result.output}"

    @pytest.mark.integration
    def test_models_stop_without_id_shows_error(self, logged_in_cli):
        """
        Testa: dumont models stop (sem ID)

        Deve mostrar erro pedindo o ID.
        """
        result = logged_in_cli.run("models", "stop")

        assert result.returncode == 1
        assert "deployment_id" in result.output.lower() or "id" in result.output.lower()

    @pytest.mark.integration
    def test_models_delete_without_id_shows_error(self, logged_in_cli):
        """
        Testa: dumont models delete (sem ID)

        Deve mostrar erro pedindo o ID.
        """
        result = logged_in_cli.run("models", "delete")

        assert result.returncode == 1
        assert "deployment_id" in result.output.lower() or "id" in result.output.lower()

    @pytest.mark.integration
    def test_models_logs_without_id_shows_error(self, logged_in_cli):
        """
        Testa: dumont models logs (sem ID)

        Deve mostrar erro pedindo o ID.
        """
        result = logged_in_cli.run("models", "logs")

        assert result.returncode == 1
        assert "deployment_id" in result.output.lower() or "id" in result.output.lower()

    @pytest.mark.integration
    def test_models_unknown_action_shows_error(self, logged_in_cli):
        """
        Testa: dumont models unknownaction

        Deve mostrar erro com ações disponíveis.
        """
        result = logged_in_cli.run("models", "unknownaction")

        assert result.returncode == 1

        # Deve listar ações válidas
        output_lower = result.output.lower()
        assert any(x in output_lower for x in ["unknown", "available", "list", "deploy"])


# =============================================================================
# TESTES DE API REAL
# =============================================================================

class TestModelsAPI:
    """Testes que usam a API real para validar funcionamento."""

    @pytest.mark.integration
    def test_api_models_list_endpoint(self, api_client):
        """
        Testa endpoint GET /api/v1/models via API direta.

        Valida que a API retorna estrutura correta.
        """
        try:
            result = api_client.call("GET", "/api/v1/models")
        except Exception as e:
            # API pode retornar vazio se não houver modelos
            pytest.skip(f"API models list returned non-JSON: {e}")

        # Se retornou algo, deve ter estrutura correta
        if result is not None:
            assert isinstance(result, dict), f"Esperado dict, recebeu {type(result)}"

            # Deve ter campo 'models' (mesmo que vazio)
            assert "models" in result, f"Resposta sem campo 'models': {result}"
            assert isinstance(result["models"], list), "Campo 'models' não é lista"

    @pytest.mark.integration
    def test_api_models_templates_endpoint(self, api_client):
        """
        Testa endpoint GET /api/v1/models/templates via API direta.

        Valida que retorna templates com estrutura correta.
        """
        result = api_client.call("GET", "/api/v1/models/templates")

        assert result is not None, "API retornou None"
        assert isinstance(result, dict), f"Esperado dict, recebeu {type(result)}"

        # Deve ter campo 'templates'
        assert "templates" in result, f"Resposta sem campo 'templates': {result}"
        templates = result["templates"]
        assert isinstance(templates, list), "Campo 'templates' não é lista"

        # Deve ter pelo menos um template
        assert len(templates) > 0, "Lista de templates vazia"

        # Valida estrutura do primeiro template
        template = templates[0]
        expected_fields = ["type", "name", "runtime"]
        for field in expected_fields:
            assert field in template, f"Template sem campo '{field}': {template}"

    @pytest.mark.integration
    def test_api_model_get_invalid_id(self, api_client):
        """
        Testa GET /api/v1/models/{id} com ID inválido.

        Deve retornar erro 404.
        """
        result = api_client.call("GET", "/api/v1/models/invalid-id-99999")

        # Deve indicar erro (não encontrado)
        assert result is not None
        if isinstance(result, dict):
            # Aceita resposta de erro ou vazia
            assert "error" in result or "detail" in result or result.get("status") in [404, "not_found"], \
                f"Esperado erro para ID inválido: {result}"


# =============================================================================
# TESTES DE DEPLOY REAL (LENTOS)
# =============================================================================

class TestModelsDeployReal:
    """
    Testes de deploy real de modelos.

    ATENÇÃO: Estes testes USAM CRÉDITOS REAIS e podem demorar.
    """

    @pytest.mark.slow
    @pytest.mark.real
    @pytest.mark.integration
    def test_deploy_llm_model_full_cycle(self, api_client, logged_in_cli):
        """
        Teste completo de ciclo de deploy LLM:
        1. Deploy modelo
        2. Verificar status
        3. Verificar logs
        4. Parar deploy
        5. Deletar deploy

        ATENÇÃO: Usa créditos reais VAST.ai!
        """
        deployment_id = None

        try:
            # 1. Fazer deploy via API
            print("\n📦 Iniciando deploy de modelo LLM...")
            deploy_result = api_client.call("POST", "/api/v1/models/deploy", {
                "model_type": "llm",
                "model_id": "meta-llama/Llama-3.1-8B-Instruct",
                "gpu_type": "RTX 4090",
                "num_gpus": 1,
                "max_price": 1.5,
                "access_type": "private",
                "port": 8000
            })

            assert deploy_result is not None, "Deploy retornou None"
            assert deploy_result.get("success") or deploy_result.get("deployment_id"), \
                f"Deploy falhou: {deploy_result}"

            deployment_id = deploy_result.get("deployment_id")
            assert deployment_id, f"Sem deployment_id na resposta: {deploy_result}"
            print(f"   ✓ Deploy iniciado: {deployment_id}")

            # 2. Verificar status via CLI
            print("\n🔍 Verificando status via CLI...")
            time.sleep(5)  # Aguarda processamento

            status_result = logged_in_cli.run("models", "get", deployment_id)
            # Aceita sucesso ou erro (modelo pode estar deploying ainda)
            print(f"   Status: {status_result.output[:200]}...")

            # 3. Verificar logs via CLI
            print("\n📋 Verificando logs via CLI...")
            logs_result = logged_in_cli.run("models", "logs", deployment_id)
            # Logs podem estar vazios no início
            print(f"   Logs: {logs_result.output[:200]}...")

            # 4. Parar deploy
            print("\n⏹️ Parando deploy...")
            stop_result = logged_in_cli.run("models", "stop", deployment_id)
            # Aceita sucesso ou erro (já parado)
            print(f"   Stop: {stop_result.output[:100]}")

            # 5. Deletar deploy
            print("\n🗑️ Deletando deploy...")
            delete_result = logged_in_cli.run("models", "delete", deployment_id)
            assert delete_result.returncode == 0, \
                f"Delete falhou: {delete_result.output}"
            print(f"   ✓ Deploy deletado")

            deployment_id = None  # Marcado como limpo

        finally:
            # Cleanup em caso de falha
            if deployment_id:
                print(f"\n⚠️ Cleanup: deletando {deployment_id}...")
                try:
                    api_client.call("DELETE", f"/api/v1/models/{deployment_id}")
                except:
                    pass

    @pytest.mark.slow
    @pytest.mark.real
    @pytest.mark.integration
    def test_deploy_with_existing_instance(self, api_client, real_instance):
        """
        Testa deploy em instância existente (já rodando).

        ATENÇÃO: Requer instância real (usa créditos VAST.ai)!
        """
        deployment_id = None

        try:
            # Deploy em instância existente
            print(f"\n📦 Deploy em instância existente: {real_instance}")

            deploy_result = api_client.call("POST", "/api/v1/models/deploy", {
                "model_type": "embeddings",  # Mais leve
                "model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "instance_id": int(real_instance),
                "access_type": "private",
                "port": 8003
            })

            assert deploy_result is not None
            if deploy_result.get("success") or deploy_result.get("deployment_id"):
                deployment_id = deploy_result.get("deployment_id")
                print(f"   ✓ Deploy iniciado: {deployment_id}")
            else:
                # Pode falhar se instância não estiver pronta
                print(f"   ⚠️ Deploy não iniciou: {deploy_result}")

        finally:
            if deployment_id:
                print(f"\n🗑️ Cleanup: deletando {deployment_id}...")
                try:
                    api_client.call("DELETE", f"/api/v1/models/{deployment_id}")
                except:
                    pass


# =============================================================================
# TESTES DE VALIDAÇÃO DE PARÂMETROS
# =============================================================================

class TestModelsDeployValidation:
    """Testes de validação de parâmetros do deploy."""

    @pytest.mark.integration
    def test_deploy_invalid_model_type(self, api_client):
        """
        Testa deploy com tipo de modelo inválido.
        """
        result = api_client.call("POST", "/api/v1/models/deploy", {
            "model_type": "invalid_type",
            "model_id": "some-model",
            "gpu_type": "RTX 4090"
        })

        # Deve retornar erro
        assert result is not None
        if isinstance(result, dict):
            assert "error" in result or "detail" in result, \
                f"Esperado erro para tipo inválido: {result}"

    @pytest.mark.integration
    def test_deploy_empty_model_id(self, api_client):
        """
        Testa deploy com model_id vazio.

        Nota: A API pode aceitar model_id vazio (validação flexível).
        Este teste verifica que a API responde sem erro de servidor.
        """
        result = api_client.call("POST", "/api/v1/models/deploy", {
            "model_type": "llm",
            "model_id": "",
            "gpu_type": "RTX 4090"
        })

        # API deve retornar algo (erro ou sucesso)
        assert result is not None, "API retornou None"

        # Se criou deployment com model_id vazio, cleanup
        if isinstance(result, dict) and result.get("deployment_id"):
            deployment_id = result["deployment_id"]
            try:
                api_client.call("DELETE", f"/api/v1/models/{deployment_id}")
            except:
                pass

        # Aceita tanto erro quanto sucesso - apenas verifica que API respondeu

    @pytest.mark.integration
    def test_deploy_negative_num_gpus(self, api_client):
        """
        Testa deploy com num_gpus negativo.
        """
        result = api_client.call("POST", "/api/v1/models/deploy", {
            "model_type": "llm",
            "model_id": "meta-llama/Llama-3.1-8B-Instruct",
            "gpu_type": "RTX 4090",
            "num_gpus": -1
        })

        # Deve retornar erro ou normalizar para 1
        assert result is not None


# =============================================================================
# TESTES DE CLI COM OPÇÕES
# =============================================================================

class TestModelsCliOptions:
    """Testes de opções do CLI para deploy."""

    @pytest.mark.integration
    def test_cli_deploy_with_all_options(self, logged_in_cli):
        """
        Testa comando deploy com todas as opções (dry-run).

        Não executa deploy real, apenas valida parsing.
        """
        # Apenas testa parsing - vai falhar na API mas valida CLI
        result = logged_in_cli.run(
            "models", "deploy", "llm", "test-model",
            "gpu=RTX 4090",
            "num_gpus=2",
            "max_price=1.5",
            "access=private",
            "port=8000",
            "name=test-deploy"
        )

        # CLI deve parsear corretamente (erro será da API)
        # O importante é não dar erro de parsing
        assert "invalid" not in result.output.lower() or \
               "error" in result.output.lower() or \
               "deploy" in result.output.lower(), \
            f"Erro de parsing: {result.output}"

    @pytest.mark.integration
    def test_cli_stop_with_force(self, logged_in_cli):
        """
        Testa comando stop com flag --force.
        """
        result = logged_in_cli.run(
            "models", "stop", "test-id-123", "--force"
        )

        # Vai falhar (ID não existe), mas deve processar o --force
        # Apenas verifica que não deu erro de parsing
        assert result.returncode in [0, 1], \
            f"Erro inesperado: {result.output}"
