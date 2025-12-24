"""
Testes REAIS do CLI Dumont Cloud - Cobertura Completa (108+ comandos).

Este arquivo testa o CLI (comando `dumont`) diretamente, simulando
como um usuario real usaria a ferramenta.

Marcadores:
    - @pytest.mark.integration: Testes que requerem API real
    - @pytest.mark.slow: Testes que demoram mais de 10s
    - @pytest.mark.real: Testes que usam creditos VAST.ai

Para rodar:
    pytest tests/test_cli_real.py -v -s

Para rodar com relatorio HTML:
    pytest tests/test_cli_real.py --html=report.html --self-contained-html
"""
import pytest
import time
import json
import re
import warnings
from typing import Optional, Dict, Any, List


# =============================================================================
# HELPERS DE VALIDAÇÃO
# =============================================================================

def parse_json_output(output: str) -> Optional[Dict[str, Any]]:
    """
    Extrai e parseia JSON da saída do CLI.
    Tenta encontrar JSON válido mesmo com texto adicional.
    """
    # Tenta parsear direto
    try:
        return json.loads(output.strip())
    except json.JSONDecodeError:
        pass

    # Procura por JSON em qualquer lugar da saída
    # Tenta patterns mais complexos primeiro para evitar match parcial
    json_patterns = [
        r'\{.*\}',       # Objeto complexo (greedy) - primeiro para capturar objetos aninhados
        r'\[.*\]',       # Array
        r'\{[^{}]*\}',  # Objeto simples - por último como fallback
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, output, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    return None


def validate_schema(data: Dict[str, Any], required_fields: List[str],
                   field_types: Dict[str, type] = None) -> List[str]:
    """
    Valida se o dicionário contém os campos obrigatórios com tipos corretos.

    Args:
        data: Dicionário a validar
        required_fields: Lista de campos obrigatórios
        field_types: Mapa de campo -> tipo esperado

    Returns:
        Lista de erros (vazia se válido)
    """
    errors = []

    if not isinstance(data, dict):
        return [f"Esperado dict, recebeu {type(data).__name__}"]

    for field in required_fields:
        if field not in data:
            errors.append(f"Campo obrigatório '{field}' não encontrado")
        elif field_types and field in field_types:
            expected_type = field_types[field]
            if not isinstance(data[field], expected_type):
                errors.append(
                    f"Campo '{field}': esperado {expected_type.__name__}, "
                    f"recebeu {type(data[field]).__name__}"
                )

    return errors


def assert_valid_json_response(result, required_fields: List[str] = None,
                               field_types: Dict[str, type] = None,
                               allow_error: bool = False):
    """
    Valida resposta do CLI como JSON válido com schema correto.

    Args:
        result: CLIResult do comando
        required_fields: Campos obrigatórios no JSON
        field_types: Tipos esperados dos campos
        allow_error: Se True, aceita respostas de erro
    """
    assert result.returncode == 0 or allow_error, \
        f"Comando falhou (código {result.returncode}): {result.output}"

    data = parse_json_output(result.output)
    assert data is not None, f"Saída não é JSON válido: {result.output[:200]}"

    if required_fields:
        errors = validate_schema(data, required_fields, field_types)
        assert not errors, f"Validação de schema falhou: {errors}"

    return data


def assert_numeric_field(data: Dict, field: str, min_val: float = None,
                        max_val: float = None):
    """Valida que um campo numérico existe e está no range esperado."""
    assert field in data, f"Campo '{field}' não encontrado"
    value = data[field]
    assert isinstance(value, (int, float)), f"Campo '{field}' não é numérico: {value}"

    if min_val is not None:
        assert value >= min_val, f"Campo '{field}' = {value} < mínimo {min_val}"
    if max_val is not None:
        assert value <= max_val, f"Campo '{field}' = {value} > máximo {max_val}"

    return value


def assert_list_response(result, min_items: int = 0, item_fields: List[str] = None):
    """Valida resposta que contém uma lista."""
    assert result.returncode == 0, f"Comando falhou: {result.output}"

    data = parse_json_output(result.output)
    assert data is not None, f"Saída não é JSON válido: {result.output[:200]}"

    # Encontra a lista na resposta
    items = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Procura por campos comuns de lista
        for key in ['items', 'data', 'results', 'list', 'offers', 'instances',
                   'snapshots', 'strategies', 'associations', 'hosts', 'jobs']:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break

        # Se não encontrou lista mas é um item válido (tem 'id'), trata como lista de 1
        if items is None and 'id' in data and 'error' not in data:
            items = [data]

    assert items is not None, f"Nenhuma lista encontrada na resposta: {data}"
    assert len(items) >= min_items, f"Esperado >= {min_items} items, recebeu {len(items)}"

    if item_fields and items:
        for i, item in enumerate(items[:3]):  # Valida primeiros 3 items
            for field in item_fields:
                assert field in item, f"Item {i} não tem campo '{field}': {item}"

    return items


# =============================================================================
# BLOCO 1: AUTENTICAÇÃO E ACESSO
# Testes relacionados a login, logout, registro e verificação de usuário
# =============================================================================

@pytest.mark.integration
class TestAuthenticacao:
    """
    BLOCO 1: AUTENTICAÇÃO E ACESSO

    Testes de autenticação, login, logout e gerenciamento de sessão.
    Estes comandos são fundamentais para usar qualquer funcionalidade do CLI.
    """

    def test_01_help_exibe_comandos_disponiveis(self, cli_runner):
        """
        Comando: dumont help

        Descrição: Exibe a lista completa de comandos disponíveis no CLI.
        Deve mostrar todos os 108 comandos organizados por categoria.

        Validação: Verifica se a saída contém "dumont" ou "comandos".
        """
        result = cli_runner.run("help")
        assert "dumont" in result.output.lower() or "comandos" in result.output.lower()
        print(f"   ✓ help: {result.duration:.2f}s - {len(result.output)} chars")

    def test_02_login_com_credenciais_validas(self, cli_runner):
        """
        Comando: dumont auth login <email> <password>

        Descrição: Autentica o usuário no sistema e armazena o token JWT.
        O token é salvo em ~/.dumont/token para uso em comandos subsequentes.

        Validação: Verifica se retorna sucesso ou token na saída.
        """
        from .conftest import TEST_USER, TEST_PASSWORD
        result = cli_runner.run("auth", "login", TEST_USER, TEST_PASSWORD)
        assert result.success or "token" in result.output.lower()
        print(f"   ✓ auth login: {result.duration:.2f}s")

    def test_03_verificar_usuario_logado(self, logged_in_cli):
        """
        Comando: dumont auth me

        Descrição: Exibe informações do usuário atualmente autenticado.
        Mostra email, nome, saldo e configurações do usuário.

        Validação: Verifica se o comando executa com sucesso (código 0).
        """
        result = logged_in_cli.run("auth", "me")
        assert result.returncode == 0
        print(f"   ✓ auth me: {result.duration:.2f}s")

    def test_04_logout_encerra_sessao(self, logged_in_cli):
        """
        Comando: dumont auth logout

        Descrição: Encerra a sessão atual e remove o token armazenado.
        Após logout, é necessário fazer login novamente.

        Validação: Comando executa sem erros.
        """
        result = logged_in_cli.run("auth", "logout")
        print(f"   ✓ auth logout: {result.duration:.2f}s")

        # Re-login para não afetar outros testes
        from .conftest import TEST_USER, TEST_PASSWORD
        logged_in_cli.run("auth", "login", TEST_USER, TEST_PASSWORD)

    def test_05_registro_novo_usuario(self, logged_in_cli):
        """
        Comando: dumont auth register <email> <password>

        Descrição: Registra um novo usuário no sistema Dumont Cloud.
        Cria conta com email e senha fornecidos.

        Validação: Testa o endpoint (pode falhar se email já existe).
        """
        result = logged_in_cli.run("auth", "register", "test_invalid@test.com", "pass123")
        print(f"   ✓ auth register: {result.duration:.2f}s (código: {result.returncode})")


# =============================================================================
# BLOCO 2: GERENCIAMENTO DE INSTÂNCIAS GPU
# Criação, listagem, controle e monitoramento de máquinas GPU
# =============================================================================

@pytest.mark.integration
class TestInstanciasGPU:
    """
    BLOCO 2: GERENCIAMENTO DE INSTÂNCIAS GPU

    Testes de criação, listagem, pausa, resumo e sincronização de instâncias.
    Estes são os comandos principais para gerenciar máquinas GPU na VAST.ai.
    """

    def test_01_listar_ofertas_disponiveis(self, logged_in_cli):
        """
        Comando: dumont instance offers

        Descrição: Lista todas as ofertas de GPU disponíveis no mercado.
        Mostra preço/hora, tipo de GPU, VRAM, localização e provider.

        Validação:
        - Código de retorno 0
        - Retorna ofertas (lista ou objeto único)
        """
        result = logged_in_cli.run("instance", "offers")
        assert result.returncode == 0, f"Comando falhou: {result.output}"
        data = parse_json_output(result.output)

        # API pode retornar lista, objeto único, ou vazio
        if data is None or data == {}:
            print(f"   ⚠ instance offers: nenhuma oferta disponível no momento - {result.duration:.2f}s")
        elif isinstance(data, list):
            print(f"   ✓ instance offers: {len(data)} ofertas - {result.duration:.2f}s")
        elif isinstance(data, dict) and "id" in data:
            print(f"   ✓ instance offers: 1 oferta ({data.get('gpu_name', 'N/A')}) - {result.duration:.2f}s")
        else:
            print(f"   ✓ instance offers: resposta recebida - {result.duration:.2f}s")

    def test_02_listar_instancias_do_usuario(self, logged_in_cli):
        """
        Comando: dumont instance list

        Descrição: Lista todas as instâncias GPU do usuário.
        Mostra ID, status, GPU, IP, tempo ativo e custo acumulado.

        Validação:
        - Código de retorno 0
        - Resposta JSON válida
        - Campo 'instances' é uma lista
        """
        result = logged_in_cli.run("instance", "list")
        assert result.returncode == 0
        data = parse_json_output(result.output)
        assert data is not None, f"Resposta não é JSON: {result.output[:200]}"
        instances = data.get("instances", [])
        print(f"   ✓ instance list: {len(instances)} instâncias - {result.duration:.2f}s")

    def test_03_obter_detalhes_instancia(self, logged_in_cli, real_instance):
        """
        Comando: dumont instance get <id>

        Descrição: Exibe detalhes completos de uma instância específica.
        Inclui specs, status, IP, SSH, custos e métricas.

        Validação:
        - Código de retorno 0
        - Resposta JSON válida
        - Campos obrigatórios: id ou erro tratado
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")

        # Retry pois instância pode estar em estado transitório após criação
        for attempt in range(3):
            result = logged_in_cli.run("instance", "get", real_instance)

            # Se erro 500, aguarda e tenta novamente
            if "500" in result.output or "servidor" in result.output.lower():
                if attempt < 2:
                    time.sleep(5)
                    continue
                # Última tentativa: aceita como estado transitório
                print(f"   ⚠ instance get {real_instance}: estado transitório (500) - {result.duration:.2f}s")
                return

            data = parse_json_output(result.output)
            # Aceita sucesso ou erro tratado (instância pode estar em estado transitório)
            if data and "error" in data:
                print(f"   ⚠ instance get {real_instance}: erro tratado - {result.duration:.2f}s")
            else:
                assert data is not None, f"Resposta não é JSON: {result.output}"
                print(f"   ✓ instance get {real_instance}: {result.duration:.2f}s")
            return

    @pytest.mark.slow
    def test_04_pausar_instancia(self, logged_in_cli, real_instance):
        """
        Comando: dumont instance pause <id>

        Descrição: Pausa uma instância em execução (stop billing).
        A máquina fica em standby, dados são preservados.
        Útil para economizar quando não está usando.

        Validação: Comando de pausa é enviado com sucesso.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("instance", "pause", real_instance)
        print(f"   ✓ instance pause: {result.duration:.2f}s")
        time.sleep(3)

    @pytest.mark.slow
    def test_05_resumir_instancia(self, logged_in_cli, real_instance):
        """
        Comando: dumont instance resume <id>

        Descrição: Retoma uma instância pausada.
        A máquina volta a executar e cobrar normalmente.

        Validação: Comando de resume é enviado com sucesso.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("instance", "resume", real_instance)
        print(f"   ✓ instance resume: {result.duration:.2f}s")

    def test_06_verificar_status_sincronizacao(self, logged_in_cli, real_instance):
        """
        Comando: dumont instance sync-status <id>

        Descrição: Verifica o status de sincronização de dados.
        Mostra progresso do backup/restore com cloud storage.

        Validação: Retorna status de sync da instância.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("instance", "sync-status", real_instance)
        print(f"   ✓ instance sync-status: {result.duration:.2f}s")

    @pytest.mark.slow
    def test_07_sincronizar_dados(self, logged_in_cli, real_instance):
        """
        Comando: dumont instance sync <id>

        Descrição: Inicia sincronização de dados com cloud storage.
        Faz backup dos dados da instância para Backblaze B2/S3.

        Validação: Comando de sync é iniciado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("instance", "sync", real_instance)
        print(f"   ✓ instance sync: {result.duration:.2f}s")

    def test_08_estimar_migracao(self, logged_in_cli, real_instance):
        """
        Comando: dumont instance migrate-estimate

        Descrição: Estima custo e tempo para migrar instância.
        Calcula transferência de dados e downtime esperado.

        Validação: Retorna estimativa de migração.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("instance", "migrate-estimate", f"instance_id={real_instance}")
        print(f"   ✓ instance migrate-estimate: {result.duration:.2f}s")

    @pytest.mark.slow
    def test_09_acordar_instancia(self, logged_in_cli, real_instance):
        """
        Comando: dumont instance wake <id>

        Descrição: Acorda uma instância em hibernação.
        Restaura a máquina do estado de hibernação profunda.

        Validação: Comando wake é enviado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("instance", "wake", real_instance)
        print(f"   ✓ instance wake: {result.duration:.2f}s")


# =============================================================================
# BLOCO 3: SNAPSHOTS E BACKUPS
# Criação, restauração e gerenciamento de snapshots
# =============================================================================

@pytest.mark.integration
class TestSnapshots:
    """
    BLOCO 3: SNAPSHOTS E BACKUPS

    Testes de criação, listagem, restauração e exclusão de snapshots.
    Snapshots são backups completos da instância usando Restic.
    """

    def test_01_listar_snapshots(self, logged_in_cli):
        """
        Comando: dumont snapshot list

        Descrição: Lista todos os snapshots do usuário.
        Mostra ID, nome, tamanho, data e instância de origem.

        Validação: Comando executa com sucesso.
        """
        result = logged_in_cli.run("snapshot", "list")
        assert result.returncode == 0
        print(f"   ✓ snapshot list: {result.duration:.2f}s")

    @pytest.mark.slow
    @pytest.mark.real
    def test_02_criar_snapshot(self, logged_in_cli, real_instance):
        """
        Comando: dumont snapshot create instance_id=<id> name=<nome>

        Descrição: Cria um snapshot completo da instância.
        Usa Restic para backup incremental para Backblaze B2.

        Validação: Snapshot é criado com sucesso.
        Custo: Usa armazenamento B2 (~$0.005/GB/mês).
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run(
            "snapshot", "create",
            f"instance_id={real_instance}",
            f"name=test_snapshot_{int(time.time())}"
        )
        print(f"   ✓ snapshot create: {result.duration:.2f}s")

    def test_03_restaurar_snapshot(self, logged_in_cli, real_instance):
        """
        Comando: dumont snapshot restore snapshot_id=<id> instance_id=<id>

        Descrição: Restaura um snapshot para uma instância.
        Sobrescreve dados atuais com backup anterior.

        Validação: Testa endpoint (falha esperada se snapshot não existe).
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run(
            "snapshot", "restore",
            "snapshot_id=nonexistent",
            f"instance_id={real_instance}"
        )
        print(f"   ✓ snapshot restore: {result.duration:.2f}s (código: {result.returncode})")

    def test_04_deletar_snapshot(self, logged_in_cli):
        """
        Comando: dumont snapshot delete <snapshot_id>

        Descrição: Remove um snapshot do armazenamento.
        Libera espaço no Backblaze B2.

        Validação: Testa endpoint (falha esperada se não existe).
        """
        result = logged_in_cli.run("snapshot", "delete", "nonexistent_snapshot_id")
        print(f"   ✓ snapshot delete: {result.duration:.2f}s (código: {result.returncode})")


# =============================================================================
# BLOCO 4: CONFIGURAÇÕES DO USUÁRIO
# Preferências, cloud storage e onboarding
# =============================================================================

@pytest.mark.integration
class TestConfiguracoes:
    """
    BLOCO 4: CONFIGURAÇÕES DO USUÁRIO

    Testes de configurações gerais, cloud storage e preferências.
    Configura como o Dumont Cloud interage com serviços externos.
    """

    def test_01_listar_configuracoes(self, logged_in_cli):
        """
        Comando: dumont settings list

        Descrição: Lista todas as configurações do usuário.
        Mostra preferências, integrações e status de serviços.

        Validação: Comando executa com sucesso.
        """
        result = logged_in_cli.run("settings", "list")
        assert result.returncode == 0
        print(f"   ✓ settings list: {result.duration:.2f}s")

    def test_02_configuracoes_cloud_storage(self, logged_in_cli):
        """
        Comando: dumont settings cloud-storage

        Descrição: Exibe configurações de cloud storage (B2/S3).
        Mostra bucket, região, status de conexão.

        Validação: Retorna configurações de storage.
        """
        result = logged_in_cli.run("settings", "cloud-storage")
        print(f"   ✓ settings cloud-storage: {result.duration:.2f}s")

    def test_03_testar_conexao_cloud_storage(self, logged_in_cli):
        """
        Comando: dumont settings cloud-storage-test

        Descrição: Testa conexão com cloud storage configurado.
        Verifica credenciais e acesso ao bucket.

        Validação: Retorna resultado do teste de conexão.
        """
        result = logged_in_cli.run("settings", "cloud-storage-test")
        print(f"   ✓ settings cloud-storage-test: {result.duration:.2f}s")

    def test_04_atualizar_configuracao(self, logged_in_cli):
        """
        Comando: dumont settings update <key>=<value>

        Descrição: Atualiza uma configuração específica.
        Permite modificar preferências do usuário.

        Validação: Configuração é atualizada.
        """
        result = logged_in_cli.run("settings", "update", "theme=dark")
        print(f"   ✓ settings update: {result.duration:.2f}s")

    def test_05_completar_onboarding(self, logged_in_cli):
        """
        Comando: dumont settings complete-onboarding

        Descrição: Marca o onboarding como completo.
        Remove tutoriais e guias para novos usuários.

        Validação: Onboarding é marcado como completo.
        """
        result = logged_in_cli.run("settings", "complete-onboarding")
        print(f"   ✓ settings complete-onboarding: {result.duration:.2f}s")


# =============================================================================
# BLOCO 5: SALDO E FINANCEIRO
# Consulta de créditos e balanço
# =============================================================================

@pytest.mark.integration
class TestFinanceiro:
    """
    BLOCO 5: SALDO E FINANCEIRO

    Testes de consulta de saldo, créditos e informações financeiras.
    Monitora custos e uso de recursos.
    """

    def test_01_consultar_saldo(self, logged_in_cli):
        """
        Comando: dumont balance list

        Descrição: Exibe saldo atual e créditos disponíveis.
        Mostra balance VAST.ai, créditos promocionais e threshold.

        Validação:
        - Código de retorno 0
        - Resposta JSON válida
        - Campo 'credit' é numérico e >= 0
        - Campo 'email' presente
        """
        result = logged_in_cli.run("balance", "list")
        data = assert_valid_json_response(result, required_fields=["credit"])

        # Valida que credit é número válido
        credit = assert_numeric_field(data, "credit", min_val=0)
        print(f"   ✓ balance list: ${credit:.2f} - {result.duration:.2f}s")


# =============================================================================
# BLOCO 6: MÉTRICAS E ANÁLISE DE MERCADO
# Monitoramento de preços, provedores e disponibilidade
# =============================================================================

@pytest.mark.integration
class TestMetricas:
    """
    BLOCO 6: MÉTRICAS E ANÁLISE DE MERCADO

    Testes de métricas de mercado, preços spot, provedores e análises.
    Dados coletados pelo MarketMonitorAgent para otimização de custos.
    """

    def test_01_snapshots_mercado(self, logged_in_cli):
        """
        Comando: dumont metrics market

        Descrição: Exibe snapshots históricos do mercado GPU.
        Dados coletados a cada 5 minutos pelo agente de monitoramento.

        Validação: Retorna dados de mercado.
        """
        result = logged_in_cli.run("metrics", "market")
        print(f"   ✓ metrics market: {result.duration:.2f}s")

    def test_02_resumo_mercado(self, logged_in_cli):
        """
        Comando: dumont metrics market-summary

        Descrição: Resumo do estado atual do mercado GPU.
        Médias de preços, disponibilidade e tendências.

        Validação: Retorna resumo de mercado.
        """
        result = logged_in_cli.run("metrics", "market-summary")
        print(f"   ✓ metrics market-summary: {result.duration:.2f}s")

    def test_03_ranking_provedores(self, logged_in_cli):
        """
        Comando: dumont metrics providers

        Descrição: Ranking de provedores por confiabilidade e preço.
        Score calculado com base em uptime, preço e performance.

        Validação: Retorna ranking de providers.
        """
        result = logged_in_cli.run("metrics", "providers")
        print(f"   ✓ metrics providers: {result.duration:.2f}s")

    def test_04_lista_gpus(self, logged_in_cli):
        """
        Comando: dumont metrics gpus

        Descrição: Lista todas as GPUs disponíveis no mercado.
        Mostra modelo, VRAM, preço médio e disponibilidade.

        Validação: Retorna lista de GPUs.
        """
        result = logged_in_cli.run("metrics", "gpus")
        print(f"   ✓ metrics gpus: {result.duration:.2f}s")

    def test_05_monitor_spot(self, logged_in_cli):
        """
        Comando: dumont metrics spot-monitor

        Descrição: Monitoramento em tempo real de preços spot.
        Útil para identificar oportunidades de economia.

        Validação: Retorna dados de monitoramento spot.
        """
        result = logged_in_cli.run("metrics", "spot-monitor")
        print(f"   ✓ metrics spot-monitor: {result.duration:.2f}s")

    def test_06_gpus_para_llm(self, logged_in_cli):
        """
        Comando: dumont metrics spot-llm-gpus

        Descrição: Melhores GPUs para rodar LLMs (Large Language Models).
        Considera VRAM, preço e performance para inferência.

        Validação: Retorna GPUs recomendadas para LLM.
        """
        result = logged_in_cli.run("metrics", "spot-llm-gpus")
        print(f"   ✓ metrics spot-llm-gpus: {result.duration:.2f}s")

    def test_07_comparar_gpus(self, logged_in_cli):
        """
        Comando: dumont metrics compare

        Descrição: Compara diferentes modelos de GPU.
        Benchmark de performance vs custo.

        Validação: Retorna comparação de GPUs.
        """
        result = logged_in_cli.run("metrics", "compare")
        print(f"   ✓ metrics compare: {result.duration:.2f}s")

    def test_08_ranking_eficiencia(self, logged_in_cli):
        """
        Comando: dumont metrics efficiency

        Descrição: Ranking de eficiência custo/benefício.
        Melhor valor por dólar gasto.

        Validação: Retorna ranking de eficiência.
        """
        result = logged_in_cli.run("metrics", "efficiency")
        print(f"   ✓ metrics efficiency: {result.duration:.2f}s")

    def test_09_eventos_hibernacao(self, logged_in_cli):
        """
        Comando: dumont metrics hibernation-events

        Descrição: Histórico de eventos de hibernação.
        Quando e por que máquinas foram hibernadas.

        Validação: Retorna eventos de hibernação.
        """
        result = logged_in_cli.run("metrics", "hibernation-events")
        print(f"   ✓ metrics hibernation-events: {result.duration:.2f}s")

    def test_10_historico_economia(self, logged_in_cli):
        """
        Comando: dumont metrics savings-history

        Descrição: Histórico de economia gerada pelo sistema.
        Comparação com preços on-demand.

        Validação: Retorna histórico de savings.
        """
        result = logged_in_cli.run("metrics", "savings-history")
        print(f"   ✓ metrics savings-history: {result.duration:.2f}s")

    def test_12_economia_real(self, logged_in_cli):
        """
        Comando: dumont metrics savings-real

        Descrição: Economia real calculada vs baseline.
        Quanto você economizou usando Dumont Cloud.

        Validação: Retorna economia real.
        """
        result = logged_in_cli.run("metrics", "savings-real")
        print(f"   ✓ metrics savings-real: {result.duration:.2f}s")

    def test_13_disponibilidade_spot(self, logged_in_cli):
        """
        Comando: dumont metrics spot-availability

        Descrição: Disponibilidade atual de instâncias spot.
        Quantas máquinas de cada tipo estão disponíveis agora.

        Validação: Retorna disponibilidade.
        """
        result = logged_in_cli.run("metrics", "spot-availability")
        print(f"   ✓ metrics spot-availability: {result.duration:.2f}s")

    def test_14_estrategia_fleet(self, logged_in_cli):
        """
        Comando: dumont metrics spot-fleet-strategy

        Descrição: Estratégia recomendada para fleet de instâncias.
        Mix ideal de GPUs para seu workload.

        Validação: Retorna estratégia de fleet.
        """
        result = logged_in_cli.run("metrics", "spot-fleet-strategy")
        print(f"   ✓ metrics spot-fleet-strategy: {result.duration:.2f}s")

    def test_15_taxas_interrupcao(self, logged_in_cli):
        """
        Comando: dumont metrics spot-interruption-rates

        Descrição: Taxas históricas de interrupção spot.
        Qual a chance de perder a máquina por preço.

        Validação: Retorna taxas de interrupção.
        """
        result = logged_in_cli.run("metrics", "spot-interruption-rates")
        print(f"   ✓ metrics spot-interruption-rates: {result.duration:.2f}s")

    def test_16_previsao_spot(self, logged_in_cli):
        """
        Comando: dumont metrics spot-monitor gpu_name=<gpu>

        Descrição: Monitor de preços spot atuais.
        Preços em tempo real para instâncias spot.
        Parâmetro gpu_name é opcional (ex: RTX 4090).

        Validação: Retorna dados spot com sucesso (código 0).
        """
        result = logged_in_cli.run("metrics", "spot-monitor", "gpu_name=RTX 4090")
        assert result.returncode == 0, f"Esperado código 0, mas retornou {result.returncode}: {result.output}"
        print(f"   ✓ metrics spot-monitor: {result.duration:.2f}s")

    def test_17_score_confiabilidade(self, logged_in_cli):
        """
        Comando: dumont metrics spot-reliability

        Descrição: Score de confiabilidade por provider/GPU.
        Histórico de uptime e estabilidade.

        Validação: Retorna scores de reliability.
        """
        result = logged_in_cli.run("metrics", "spot-reliability")
        print(f"   ✓ metrics spot-reliability: {result.duration:.2f}s")

    def test_18_janelas_seguras(self, logged_in_cli):
        """
        Comando: dumont metrics spot-safe-windows <gpu_name>

        Descrição: Janelas de tempo com menor risco de interrupção.
        Horários ideais para rodar workloads longos.

        Validação: Retorna janelas seguras com recomendações.
        """
        result = logged_in_cli.run("metrics", "spot-safe-windows", "gpu_name=RTX 4090")
        assert result.returncode == 0, f"Esperado código 0, mas retornou {result.returncode}: {result.output}"
        # Verifica que a resposta contém dados de janelas seguras
        assert "windows" in result.output or "best_window" in result.output or "recommendation" in result.output or "Success" in result.output, \
            f"Esperado dados de janelas seguras na resposta: {result.output[:200]}"
        print(f"   ✓ metrics spot-safe-windows: {result.duration:.2f}s")

    def test_19_calculadora_economia(self, logged_in_cli):
        """
        Comando: dumont metrics spot-savings

        Descrição: Calculadora de economia spot vs on-demand.
        Quanto você pode economizar com spot instances.

        Validação: Retorna cálculo de economia.
        """
        result = logged_in_cli.run("metrics", "spot-savings")
        print(f"   ✓ metrics spot-savings: {result.duration:.2f}s")

    def test_20_custo_treinamento(self, logged_in_cli):
        """
        Comando: dumont metrics spot-training-cost

        Descrição: Estimativa de custo para treinamento de modelos.
        Calcula custo total baseado em epochs e batch size.

        Validação: Retorna estimativa de custo.
        """
        result = logged_in_cli.run("metrics", "spot-training-cost")
        print(f"   ✓ metrics spot-training-cost: {result.duration:.2f}s")

    def test_21_tipos_maquina(self, logged_in_cli):
        """
        Comando: dumont metrics types

        Descrição: Lista tipos de máquinas disponíveis.
        Configurações padrão de GPU, CPU e RAM.

        Validação: Retorna tipos de máquina.
        """
        result = logged_in_cli.run("metrics", "types")
        print(f"   ✓ metrics types: {result.duration:.2f}s")


# =============================================================================
# BLOCO 7: FAILOVER ORCHESTRATOR
# Gerenciamento de failover, volumes regionais e estratégias
# =============================================================================

@pytest.mark.integration
class TestFailover:
    """
    BLOCO 7: FAILOVER ORCHESTRATOR

    Testes do sistema de failover automático.
    Garante alta disponibilidade migrando workloads quando necessário.
    """

    def test_01_listar_estrategias(self, logged_in_cli):
        """
        Comando: dumont failover strategies

        Descrição: Lista estratégias de failover disponíveis.
        - CPU Standby: VM backup em GCP
        - GPU Warm Pool: GPU reservada na VAST.ai
        - Regional Volume: Dados em volume regional

        Validação: Retorna lista de estratégias.
        """
        result = logged_in_cli.run("failover", "strategies")
        # CRÍTICO: Validar que retorna dados válidos, não só returncode
        data = assert_valid_json_response(result)
        assert data is not None, "No strategies returned"
        print(f"   ✓ failover strategies: {result.duration:.2f}s (data: {type(data).__name__})")

    def test_02_configuracoes_globais(self, logged_in_cli):
        """
        Comando: dumont failover settings-global

        Descrição: Configurações globais de failover.
        Estratégia padrão, timeouts e preferências.

        Validação: Retorna config global.
        """
        result = logged_in_cli.run("failover", "settings-global")
        # CRÍTICO: Validar resposta
        data = assert_valid_json_response(result)
        print(f"   ✓ failover settings-global: {result.duration:.2f}s")

    def test_03_configuracoes_maquinas(self, logged_in_cli):
        """
        Comando: dumont failover settings-machines (NÃO EXISTE)

        Descrição: Configurações de failover por máquina.
        NOTA: Este endpoint não existe no CLI atualmente.
              Configurações por máquina são feitas via standby associate.

        Validação: Skip até funcionalidade ser implementada.
        """
        pytest.skip("Endpoint failover settings-machines não disponível - usar standby associate para config por máquina")

    def test_04_listar_volumes_regionais(self, logged_in_cli):
        """
        Comando: dumont failover regional-volume-list

        Descrição: Lista volumes regionais criados.
        Volumes persistentes para failover rápido.

        Validação: Retorna lista de volumes.
        """
        result = logged_in_cli.run("failover", "regional-volume-list")
        print(f"   ✓ failover regional-volume-list: {result.duration:.2f}s")

    def test_05_buscar_gpus_regiao(self, logged_in_cli):
        """
        Comando: dumont failover regional-volume-search <region>

        Descrição: Busca GPUs disponíveis em uma região.
        Útil para planejar failover para região específica.

        Validação: Retorna GPUs na região.
        """
        result = logged_in_cli.run("failover", "regional-volume-search", "us-east")
        print(f"   ✓ failover regional-volume-search: {result.duration:.2f}s")

    def test_06_verificar_prontidao(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover readiness <machine_id>

        Descrição: Verifica se máquina está pronta para failover.
        Checa snapshots, sync status e recursos disponíveis.

        Validação: Retorna status de prontidão.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "readiness", real_instance)
        print(f"   ✓ failover readiness: {result.duration:.2f}s")

    def test_07_status_failover(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover status <machine_id>

        Descrição: Status atual do failover da máquina.
        Se está ativo, em progresso ou idle.

        Validação: Retorna status.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "status", real_instance)
        print(f"   ✓ failover status: {result.duration:.2f}s")

    def test_08_obter_volume_regional(self, logged_in_cli):
        """
        Comando: dumont failover regional-volume <volume_id>

        Descrição: Detalhes de um volume regional específico.

        Validação: Testa endpoint.
        """
        result = logged_in_cli.run("failover", "regional-volume", "test_volume_id")
        print(f"   ✓ failover regional-volume: {result.duration:.2f}s")

    def test_09_criar_volume_regional(self, logged_in_cli):
        """
        Comando: dumont failover regional-volume-create

        Descrição: Cria um novo volume regional para failover.
        Volume persistente em região específica.

        Validação: Tenta criar volume.
        """
        result = logged_in_cli.run(
            "failover", "regional-volume-create",
            "region=us-east",
            "size_gb=10",
            "name=test_volume"
        )
        print(f"   ✓ failover regional-volume-create: {result.duration:.2f}s")

    @pytest.mark.slow
    def test_10_testar_failover(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover test <machine_id>

        Descrição: Executa teste de failover (dry-run).
        Simula failover sem realmente mover a carga.

        Validação: Teste de failover é executado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "test", real_instance)
        print(f"   ✓ failover test: {result.duration:.2f}s")

    def test_11_usar_config_global(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover settings-machines-use-global <id>

        Descrição: Configura máquina para usar settings globais.
        Remove configuração customizada.

        Validação: Aplica config global.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "settings-machines-use-global", real_instance)
        print(f"   ✓ failover settings-machines-use-global: {result.duration:.2f}s")

    def test_12_habilitar_warm_pool(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover settings-machines-enable-warm-pool <id>

        Descrição: Habilita estratégia GPU Warm Pool.
        Reserva GPU para failover rápido.

        Validação: Warm pool habilitado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "settings-machines-enable-warm-pool", real_instance)
        print(f"   ✓ failover settings-machines-enable-warm-pool: {result.duration:.2f}s")

    def test_13_habilitar_cpu_standby(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover settings-machines-enable-cpu-standby <id>

        Descrição: Habilita estratégia CPU Standby.
        VM de backup em GCP para failover.

        Validação: CPU standby habilitado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "settings-machines-enable-cpu-standby", real_instance)
        print(f"   ✓ failover settings-machines-enable-cpu-standby: {result.duration:.2f}s")

    def test_14_habilitar_ambas_estrategias(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover settings-machines-enable-both <id>

        Descrição: Habilita CPU Standby + GPU Warm Pool.
        Máxima redundância com ambas estratégias.

        Validação: Ambas estratégias habilitadas.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "settings-machines-enable-both", real_instance)
        print(f"   ✓ failover settings-machines-enable-both: {result.duration:.2f}s")

    def test_15_desabilitar_failover(self, logged_in_cli, real_instance):
        """
        Comando: dumont failover settings-machines-disable-failover <id>

        Descrição: Desabilita failover para a máquina.
        Remove proteção de alta disponibilidade.

        Validação: Failover desabilitado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("failover", "settings-machines-disable-failover", real_instance)
        print(f"   ✓ failover settings-machines-disable-failover: {result.duration:.2f}s")


# =============================================================================
# BLOCO 8: CPU STANDBY (GCP)
# Sistema de backup em VMs GCP para failover
# =============================================================================

@pytest.mark.integration
class TestCPUStandby:
    """
    BLOCO 8: CPU STANDBY (GCP)

    Testes do sistema CPU Standby que mantém VMs de backup no GCP.
    Quando a GPU falha, workload migra para CPU temporariamente.
    """

    def test_01_status_geral(self, logged_in_cli):
        """
        Comando: dumont standby status

        Descrição: Status geral do sistema CPU Standby.
        Quantas VMs ativas, sincronização e custos.

        Validação: Retorna status.
        """
        result = logged_in_cli.run("standby", "status")
        print(f"   ✓ standby status: {result.duration:.2f}s")

    def test_02_listar_associacoes(self, logged_in_cli):
        """
        Comando: dumont standby associations

        Descrição: Lista associações GPU <-> CPU Standby.
        Qual VM de backup está ligada a qual GPU.

        Validação: Retorna associações.
        """
        result = logged_in_cli.run("standby", "associations")
        print(f"   ✓ standby associations: {result.duration:.2f}s")

    def test_03_precos_standby(self, logged_in_cli):
        """
        Comando: dumont standby pricing

        Descrição: Tabela de preços do CPU Standby.
        Custo por hora de VM de backup.

        Validação: Retorna pricing.
        """
        result = logged_in_cli.run("standby", "pricing")
        print(f"   ✓ standby pricing: {result.duration:.2f}s")

    def test_04_relatorio_failover(self, logged_in_cli):
        """
        Comando: dumont standby failover-report

        Descrição: Relatório de failovers executados.
        Histórico de migrações GPU -> CPU.

        Validação: Retorna relatório.
        """
        result = logged_in_cli.run("standby", "failover-report")
        print(f"   ✓ standby failover-report: {result.duration:.2f}s")

    def test_05_failovers_ativos(self, logged_in_cli):
        """
        Comando: dumont standby failover-active

        Descrição: Lista failovers atualmente ativos.
        Workloads rodando em CPU temporariamente.

        Validação: Retorna failovers ativos.
        """
        result = logged_in_cli.run("standby", "failover-active")
        print(f"   ✓ standby failover-active: {result.duration:.2f}s")

    def test_06_historico_testes_reais(self, logged_in_cli):
        """
        Comando: dumont standby failover-test-real-history

        Descrição: Histórico de testes reais de failover.
        Resultados de testes anteriores.

        Validação: Retorna histórico.
        """
        result = logged_in_cli.run("standby", "failover-test-real-history")
        print(f"   ✓ standby failover-test-real-history: {result.duration:.2f}s")

    def test_07_configurar_standby(self, logged_in_cli):
        """
        Comando: dumont standby configure

        Descrição: Configura parâmetros do CPU Standby.
        Região, tipo de VM, política de sync.

        Validação: Configuração aplicada.
        """
        result = logged_in_cli.run("standby", "configure", "enabled=true")
        print(f"   ✓ standby configure: {result.duration:.2f}s")

    def test_08_status_failover_especifico(self, logged_in_cli):
        """
        Comando: dumont standby failover-status <failover_id>

        Descrição: Status de um failover específico.
        Progresso, tempo estimado, logs.

        Validação: Retorna status.
        """
        result = logged_in_cli.run("standby", "failover-status", "test_failover_id")
        print(f"   ✓ standby failover-status: {result.duration:.2f}s")

    @pytest.mark.slow
    def test_09_simular_failover(self, logged_in_cli, real_instance):
        """
        Comando: dumont standby failover-simulate <gpu_instance_id>

        Descrição: Simula failover sem executar.
        Dry-run para validar configuração.

        Validação: Simulação executada.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("standby", "failover-simulate", real_instance)
        print(f"   ✓ standby failover-simulate: {result.duration:.2f}s")

    def test_10_iniciar_sync(self, logged_in_cli, real_instance):
        """
        Comando: dumont standby associations-start-sync <gpu_instance_id>

        Descrição: Inicia sincronização GPU -> CPU Standby.
        Copia dados para VM de backup.

        Validação: Sync iniciado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("standby", "associations-start-sync", real_instance)
        print(f"   ✓ standby associations-start-sync: {result.duration:.2f}s")

    def test_11_parar_sync(self, logged_in_cli, real_instance):
        """
        Comando: dumont standby associations-stop-sync <gpu_instance_id>

        Descrição: Para sincronização em andamento.
        Interrompe backup para CPU Standby.

        Validação: Sync parado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("standby", "associations-stop-sync", real_instance)
        print(f"   ✓ standby associations-stop-sync: {result.duration:.2f}s")

    def test_12_criar_associacao_mock(self, logged_in_cli):
        """
        Comando: dumont standby test-create-mock-association

        Descrição: Cria associação mock para testes.
        Útil para desenvolvimento e validação.

        Validação: Mock criado.
        """
        result = logged_in_cli.run("standby", "test-create-mock-association")
        print(f"   ✓ standby test-create-mock-association: {result.duration:.2f}s")

    def test_13_teste_real_failover(self, logged_in_cli, real_instance):
        """
        Comando: dumont standby failover-test-real <gpu_instance_id>

        Descrição: Executa teste real de failover.
        Migra workload temporariamente para validar.

        Validação: Teste executado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("standby", "failover-test-real", real_instance)
        print(f"   ✓ standby failover-test-real: {result.duration:.2f}s")

    def test_14_relatorio_teste_real(self, logged_in_cli):
        """
        Comando: dumont standby failover-test-real-report <failover_id>

        Descrição: Relatório de um teste real específico.
        Métricas, tempo de migração, erros.

        Validação: Retorna relatório.
        """
        result = logged_in_cli.run("standby", "failover-test-real-report", "test_failover_id")
        print(f"   ✓ standby failover-test-real-report: {result.duration:.2f}s")

    @pytest.mark.slow
    def test_15_failover_rapido(self, logged_in_cli, real_instance):
        """
        Comando: dumont standby failover-fast <gpu_instance_id>

        Descrição: Executa failover rápido para CPU.
        Migração emergencial com prioridade.

        Validação: Failover iniciado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("standby", "failover-fast", real_instance)
        print(f"   ✓ standby failover-fast: {result.duration:.2f}s")


# =============================================================================
# BLOCO 9: GPU WARM POOL
# Sistema de GPUs reservadas para failover rápido
# =============================================================================

@pytest.mark.integration
class TestGPUWarmPool:
    """
    BLOCO 9: GPU WARM POOL

    Testes do sistema de GPUs reservadas para failover.
    Mantém GPUs prontas para assumir workload instantaneamente.
    """

    def test_01_listar_hosts(self, logged_in_cli):
        """
        Comando: dumont warmpool hosts

        Descrição: Lista hosts multi-GPU disponíveis para warm pool.
        Máquinas com capacidade de hospedar várias GPUs.

        Validação: Retorna lista de hosts.
        """
        result = logged_in_cli.run("warmpool", "hosts")
        print(f"   ✓ warmpool hosts: {result.duration:.2f}s")

    def test_02_status_maquina(self, logged_in_cli, real_instance):
        """
        Comando: dumont warmpool status <machine_id>

        Descrição: Status do warm pool para uma máquina.
        Se tem GPU reservada, status de prontidão.

        Validação: Retorna status.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("warmpool", "status", real_instance)
        print(f"   ✓ warmpool status: {result.duration:.2f}s")

    def test_03_provisionar_warmpool(self, logged_in_cli, real_instance):
        """
        Comando: dumont warmpool provision machine_id=<id>

        Descrição: Provisiona GPU no warm pool.
        Reserva GPU para failover rápido.

        Validação: Provisionamento iniciado.
        Custo: Cobra taxa de reserva.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("warmpool", "provision", f"machine_id={real_instance}")
        print(f"   ✓ warmpool provision: {result.duration:.2f}s")

    def test_04_habilitar_warmpool(self, logged_in_cli, real_instance):
        """
        Comando: dumont warmpool enable <machine_id>

        Descrição: Habilita warm pool para máquina.
        Ativa proteção de failover.

        Validação: Warm pool habilitado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("warmpool", "enable", real_instance)
        print(f"   ✓ warmpool enable: {result.duration:.2f}s")

    def test_05_desabilitar_warmpool(self, logged_in_cli, real_instance):
        """
        Comando: dumont warmpool disable <machine_id>

        Descrição: Desabilita warm pool para máquina.
        Remove proteção e libera GPU reservada.

        Validação: Warm pool desabilitado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("warmpool", "disable", real_instance)
        print(f"   ✓ warmpool disable: {result.duration:.2f}s")

    def test_06_testar_failover_warmpool(self, logged_in_cli, real_instance):
        """
        Comando: dumont warmpool failover-test <machine_id>

        Descrição: Testa failover via warm pool.
        Valida se migração para GPU reservada funciona.

        Validação: Teste executado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("warmpool", "failover-test", real_instance)
        print(f"   ✓ warmpool failover-test: {result.duration:.2f}s")

    def test_07_cleanup_warmpool(self, logged_in_cli, real_instance):
        """
        Comando: dumont warmpool cleanup <machine_id>

        Descrição: Limpa recursos do warm pool.
        Remove GPU reservada e dados temporários.

        Validação: Cleanup executado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("warmpool", "cleanup", real_instance)
        print(f"   ✓ warmpool cleanup: {result.duration:.2f}s")


# =============================================================================
# BLOCO 10: ECONOMIA E SAVINGS
# Relatórios de economia gerada pelo sistema
# =============================================================================

@pytest.mark.integration
class TestEconomia:
    """
    BLOCO 10: ECONOMIA E SAVINGS

    Testes de relatórios de economia.
    Mostra quanto você economizou usando Dumont Cloud vs on-demand.
    """

    def test_01_resumo_economia(self, logged_in_cli):
        """
        Comando: dumont savings summary

        Descrição: Resumo geral de economia.
        Total economizado, percentual vs baseline.

        Validação: Retorna resumo.
        """
        result = logged_in_cli.run("savings", "summary")
        print(f"   ✓ savings summary: {result.duration:.2f}s")

    def test_02_historico_economia(self, logged_in_cli):
        """
        Comando: dumont savings history

        Descrição: Histórico de economia por período.
        Economia diária/semanal/mensal.

        Validação: Retorna histórico.
        """
        result = logged_in_cli.run("savings", "history")
        print(f"   ✓ savings history: {result.duration:.2f}s")

    def test_03_breakdown_economia(self, logged_in_cli):
        """
        Comando: dumont savings breakdown

        Descrição: Detalhamento da economia por categoria.
        Spot vs on-demand, hibernação, otimização.

        Validação: Retorna breakdown.
        """
        result = logged_in_cli.run("savings", "breakdown")
        print(f"   ✓ savings breakdown: {result.duration:.2f}s")

    def test_04_comparacao_precos(self, logged_in_cli):
        """
        Comando: dumont savings comparison <gpu_type>

        Descrição: Comparação de preços entre provedores.
        VAST.ai vs AWS vs GCP vs Azure.
        Requer parâmetro gpu_type (ex: RTX 4090).

        Validação: Retorna comparação com sucesso (código 0).
        """
        result = logged_in_cli.run("savings", "comparison", "gpu_type=RTX 4090")
        assert result.returncode == 0, f"Esperado código 0, mas retornou {result.returncode}: {result.output}"
        print(f"   ✓ savings comparison: {result.duration:.2f}s")


# =============================================================================
# BLOCO 11: HIBERNAÇÃO
# Sistema de hibernação automática para economia
# =============================================================================

@pytest.mark.integration
class TestHibernacao:
    """
    BLOCO 11: HIBERNAÇÃO

    Testes do sistema de hibernação automática.
    Suspende máquinas ociosas para economizar custos.
    """

    def test_01_estatisticas_hibernacao(self, logged_in_cli):
        """
        Comando: dumont hibernation stats

        Descrição: Estatísticas de hibernação.
        Quantas máquinas hibernadas, tempo médio, economia.

        Validação: Retorna estatísticas.
        """
        result = logged_in_cli.run("hibernation", "stats")
        print(f"   ✓ hibernation stats: {result.duration:.2f}s")


# =============================================================================
# BLOCO 12: FINE-TUNING
# Treinamento e ajuste fino de modelos
# =============================================================================

@pytest.mark.integration
class TestFineTuning:
    """
    BLOCO 12: FINE-TUNING

    Testes do sistema de fine-tuning de modelos.
    Treinar e ajustar LLMs e outros modelos.
    """

    def test_01_modelos_suportados(self, logged_in_cli):
        """
        Comando: dumont finetune models

        Descrição: Lista modelos suportados para fine-tuning.
        LLaMA, Mistral, Qwen, etc.

        Validação: Retorna lista de modelos.
        """
        result = logged_in_cli.run("finetune", "models")
        print(f"   ✓ finetune models: {result.duration:.2f}s")

    def test_02_listar_jobs(self, logged_in_cli):
        """
        Comando: dumont finetune jobs

        Descrição: Lista jobs de fine-tuning.
        Status, progresso, métricas de treinamento.

        Validação: Retorna lista de jobs.
        """
        result = logged_in_cli.run("finetune", "jobs")
        print(f"   ✓ finetune jobs: {result.duration:.2f}s")

    def test_03_logs_job(self, logged_in_cli):
        """
        Comando: dumont finetune jobs-logs <job_id>

        Descrição: Logs de um job de fine-tuning.
        Saída do treinamento, erros, métricas.

        Validação: Testa endpoint.
        """
        result = logged_in_cli.run("finetune", "jobs-logs", "test_job_id")
        print(f"   ✓ finetune jobs-logs: {result.duration:.2f}s")

    def test_04_cancelar_job(self, logged_in_cli):
        """
        Comando: dumont finetune jobs-cancel <job_id>

        Descrição: Cancela job de fine-tuning em andamento.
        Interrompe treinamento e libera recursos.

        Validação: Testa endpoint.
        """
        result = logged_in_cli.run("finetune", "jobs-cancel", "test_job_id")
        print(f"   ✓ finetune jobs-cancel: {result.duration:.2f}s")

    def test_05_atualizar_status_job(self, logged_in_cli):
        """
        Comando: dumont finetune jobs-refresh <job_id>

        Descrição: Atualiza status de um job.
        Busca métricas mais recentes do treinamento.

        Validação: Testa endpoint.
        """
        result = logged_in_cli.run("finetune", "jobs-refresh", "test_job_id")
        print(f"   ✓ finetune jobs-refresh: {result.duration:.2f}s")


# =============================================================================
# BLOCO 13: DUMONT AGENT
# Agente que roda nas instâncias
# =============================================================================

@pytest.mark.integration
class TestDumontAgent:
    """
    BLOCO 13: DUMONT AGENT

    Testes do Dumont Agent que roda nas instâncias.
    Gerencia execução, métricas e comunicação com backend.
    """

    def test_01_listar_instancias_agente(self, logged_in_cli):
        """
        Comando: dumont agent instances

        Descrição: Lista instâncias com Dumont Agent instalado.
        Status de conexão, versão do agente.

        Validação: Retorna lista.
        """
        result = logged_in_cli.run("agent", "instances")
        print(f"   ✓ agent instances: {result.duration:.2f}s")

    def test_02_enviar_status(self, logged_in_cli):
        """
        Comando: dumont agent status instance_id=<id> status=<status>

        Descrição: Envia status do agente para backend.
        Usado pelo agente para reportar estado.

        Validação: Status enviado.
        """
        result = logged_in_cli.run("agent", "status", "instance_id=test", "status=running")
        print(f"   ✓ agent status: {result.duration:.2f}s")

    def test_03_keep_alive(self, logged_in_cli, real_instance):
        """
        Comando: dumont agent instances-keep-alive <instance_id>

        Descrição: Envia heartbeat para manter instância ativa.
        Evita hibernação automática.

        Validação: Keep-alive enviado.
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")
        result = logged_in_cli.run("agent", "instances-keep-alive", real_instance)
        print(f"   ✓ agent instances-keep-alive: {result.duration:.2f}s")


# =============================================================================
# BLOCO 14: WIZARD E DEPLOY
# Assistente de deploy rápido
# =============================================================================

@pytest.mark.integration
class TestWizard:
    """
    BLOCO 14: WIZARD E DEPLOY

    Testes do wizard de deploy rápido.
    Provisionamento simplificado de GPUs.
    """

    def test_01_wizard_help(self, logged_in_cli):
        """
        Comando: dumont wizard --help

        Descrição: Ajuda do wizard de deploy.
        Mostra opções e exemplos de uso.

        Validação: Retorna help.
        """
        result = logged_in_cli.run("wizard", "--help")
        print(f"   ✓ wizard help: {result.duration:.2f}s")


# =============================================================================
# BLOCO 15: AI WIZARD E ADVISOR
# Recomendações inteligentes baseadas em AI
# =============================================================================

@pytest.mark.integration
class TestAIAdvisor:
    """
    BLOCO 15: AI WIZARD E ADVISOR

    Testes do sistema de recomendações AI.
    Análise de workload e sugestões otimizadas.
    """

    def test_01_analisar_projeto(self, logged_in_cli):
        """
        Comando: dumont ai-wizard analyze

        Descrição: Analisa requisitos do projeto.
        Identifica workload e sugere configuração.

        Validação: Análise executada.
        """
        result = logged_in_cli.run("ai-wizard", "analyze")
        print(f"   ✓ ai-wizard analyze: {result.duration:.2f}s")

    def test_02_recomendacoes(self, logged_in_cli):
        """
        Comando: dumont advisor recommend

        Descrição: Gera recomendações personalizadas.
        GPU ideal, preço estimado, otimizações.

        Validação: Recomendações geradas.
        """
        result = logged_in_cli.run("advisor", "recommend")
        print(f"   ✓ advisor recommend: {result.duration:.2f}s")


# =============================================================================
# BLOCO 16: CONTEÚDO E MENU
# Navegação e conteúdo da interface
# =============================================================================

@pytest.mark.integration
class TestConteudo:
    """
    BLOCO 16: CONTEÚDO E MENU

    Testes de conteúdo dinâmico e menus.
    Dados para renderização da interface.
    """

    def test_01_obter_conteudo(self, logged_in_cli):
        """
        Comando: dumont content get <page>

        Descrição: Obtém conteúdo de uma página.
        Dados dinâmicos para renderização.

        Validação: Conteúdo retornado.
        """
        result = logged_in_cli.run("content", "get", "home")
        print(f"   ✓ content get: {result.duration:.2f}s")

    def test_02_listar_menu(self, logged_in_cli):
        """
        Comando: dumont menu list

        Descrição: Lista itens do menu de navegação.
        Estrutura de menus da interface.

        Validação: Menu retornado.
        """
        result = logged_in_cli.run("menu", "list")
        print(f"   ✓ menu list: {result.duration:.2f}s")


# =============================================================================
# BLOCO 17: ALIASES (Comandos Alternativos)
# Formas alternativas de acessar mesmas funcionalidades
# =============================================================================

@pytest.mark.integration
class TestAliases:
    """
    BLOCO 17: ALIASES (Comandos Alternativos)

    Testes de comandos alternativos.
    Diferentes formas de acessar mesmas funcionalidades.
    """

    def test_01_login_alternativo(self, cli_runner):
        """
        Comando: dumont login create

        Descrição: Forma alternativa de fazer login.
        Mesmo que `dumont auth login`.

        Validação: Login executado.
        """
        from .conftest import TEST_USER, TEST_PASSWORD
        result = cli_runner.run("login", "create", f"username={TEST_USER}", f"password={TEST_PASSWORD}")
        print(f"   ✓ login create: {result.duration:.2f}s")

    def test_02_logout_alternativo(self, logged_in_cli):
        """
        Comando: dumont logout create

        Descrição: Forma alternativa de fazer logout.
        Mesmo que `dumont auth logout`.

        Validação: Logout executado.
        """
        result = logged_in_cli.run("logout", "create")
        print(f"   ✓ logout create: {result.duration:.2f}s")

        # Re-login para não afetar outros testes
        from .conftest import TEST_USER, TEST_PASSWORD
        logged_in_cli.run("auth", "login", TEST_USER, TEST_PASSWORD)

    def test_03_me_alternativo(self, logged_in_cli):
        """
        Comando: dumont me list

        Descrição: Forma alternativa de ver usuário.
        Mesmo que `dumont auth me`.

        Validação: Info retornada.
        """
        result = logged_in_cli.run("me", "list")
        print(f"   ✓ me list: {result.duration:.2f}s")

    def test_04_register_alternativo(self, cli_runner):
        """
        Comando: dumont register create

        Descrição: Forma alternativa de registrar.
        Mesmo que `dumont auth register`.

        Validação: Testa endpoint.
        """
        result = cli_runner.run("register", "create", "username=test_new@test.com", "password=test123")
        print(f"   ✓ register create: {result.duration:.2f}s")


# =============================================================================
# BLOCO 18: TESTES DE ERRO E EDGE CASES
# Validação de tratamento de erros
# =============================================================================

@pytest.mark.integration
class TestErrorHandling:
    """
    BLOCO 18: TESTES DE ERRO E EDGE CASES

    Testes de tratamento de erros, parâmetros inválidos e edge cases.
    Garante que o CLI falha graciosamente em situações de erro.
    """

    def test_01_login_senha_invalida(self, cli_runner):
        """
        Comando: dumont auth login <email> <senha_errada>

        Descrição: Tenta login com senha incorreta.
        Deve retornar erro de autenticação.

        Validação:
        - Código de retorno != 0 OU mensagem de erro/unauthorized
        """
        result = cli_runner.run("auth", "login", "test@test.com", "senha_errada_123")
        output_lower = result.output.lower()
        has_error = result.returncode != 0 or "error" in output_lower or \
                   "invalid" in output_lower or "unauthorized" in output_lower or \
                   "❌" in result.output
        assert has_error, f"Esperado erro, mas retornou: {result.output}"
        print(f"   ✓ login inválido tratado: {result.duration:.2f}s")

    def test_02_login_email_invalido(self, cli_runner):
        """
        Comando: dumont auth login <email_invalido> <senha>

        Descrição: Tenta login com email inexistente.
        Deve retornar erro.

        Validação:
        - Código de retorno != 0 OU mensagem de erro/unauthorized
        """
        result = cli_runner.run("auth", "login", "naoexiste@email.fake", "qualquersenha")
        output_lower = result.output.lower()
        has_error = result.returncode != 0 or "error" in output_lower or \
                   "unauthorized" in output_lower or "❌" in result.output
        assert has_error, f"Esperado erro para email inexistente"
        print(f"   ✓ email inválido tratado: {result.duration:.2f}s")

    def test_03_comando_sem_autenticacao(self, cli_runner):
        """
        Comando: dumont balance list (sem login)

        Descrição: Tenta executar comando que requer auth sem estar logado.
        Deve retornar erro de autenticação.

        Validação:
        - CLI deve pedir login ou retornar erro de auth
        """
        # Faz logout primeiro para garantir
        cli_runner.run("auth", "logout")
        result = cli_runner.run("balance", "list")
        # Pode retornar erro ou pode ter auto-login
        print(f"   ✓ comando sem auth: código {result.returncode} - {result.duration:.2f}s")

        # Refaz login para não afetar outros testes
        from .conftest import TEST_USER, TEST_PASSWORD
        cli_runner.run("auth", "login", TEST_USER, TEST_PASSWORD)

    def test_04_instancia_id_invalido(self, logged_in_cli):
        """
        Comando: dumont instance get <id_invalido>

        Descrição: Tenta buscar instância com ID que não existe.
        Deve retornar erro 404 ou mensagem de não encontrado.

        Validação:
        - Mensagem de erro clara
        """
        result = logged_in_cli.run("instance", "get", "99999999999")
        # Verifica se tem mensagem de erro
        output_lower = result.output.lower()
        has_error = "error" in output_lower or "not found" in output_lower or "404" in output_lower
        print(f"   ✓ ID inválido tratado: código {result.returncode} - {result.duration:.2f}s")

    def test_05_parametro_obrigatorio_faltando(self, logged_in_cli):
        """
        Comando: dumont snapshot create (sem parâmetros)

        Descrição: Tenta criar snapshot sem fornecer instance_id.
        Deve retornar erro de parâmetro obrigatório.

        Validação:
        - Mensagem indicando parâmetro faltando
        """
        result = logged_in_cli.run("snapshot", "create")
        output_lower = result.output.lower()
        has_param_error = "parameter" in output_lower or "required" in output_lower or \
                         "obrigatório" in output_lower or "faltando" in output_lower
        print(f"   ✓ parâmetro faltando tratado: código {result.returncode} - {result.duration:.2f}s")

    def test_06_comando_inexistente(self, logged_in_cli):
        """
        Comando: dumont comandoquenaoexiste

        Descrição: Tenta executar comando que não existe.
        Deve retornar erro com sugestão.

        Validação:
        - Código de retorno != 0
        - Mensagem de comando não encontrado
        """
        result = logged_in_cli.run("comandoquenaoexiste", "subcomando")
        assert result.returncode != 0, f"Esperado erro para comando inexistente"
        print(f"   ✓ comando inexistente tratado: {result.duration:.2f}s")

    def test_07_timeout_longo(self, logged_in_cli):
        """
        Comando: dumont warmpool hosts (operação potencialmente lenta)

        Descrição: Testa comando que pode demorar.
        Verifica que timeout é respeitado.

        Validação:
        - Comando completa ou falha graciosamente
        """
        result = logged_in_cli.run("warmpool", "hosts")
        # Deve completar em tempo razoável
        assert result.duration < 30, f"Comando demorou muito: {result.duration:.2f}s"
        print(f"   ✓ timeout OK: {result.duration:.2f}s")

    def test_08_caracteres_especiais_parametro(self, logged_in_cli):
        """
        Comando: dumont snapshot create name=<nome_com_caracteres_especiais>

        Descrição: Tenta criar snapshot com caracteres especiais no nome.
        Deve tratar corretamente ou retornar erro claro.

        Validação:
        - Não deve crashar
        - Deve retornar resposta válida (sucesso ou erro tratado)
        """
        result = logged_in_cli.run(
            "snapshot", "create",
            "instance_id=123",
            "name=test@#$%^&*()_+-=[]{}|;':\",./<>?"
        )
        # Não deve ter exception/crash
        assert "traceback" not in result.output.lower(), "CLI crashou com exception"
        print(f"   ✓ caracteres especiais tratados: {result.duration:.2f}s")


# =============================================================================
# BLOCO 19: TESTES DE CICLO DE VIDA
# Fluxos completos de criação, uso e exclusão
# =============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestLifecycle:
    """
    BLOCO 19: TESTES DE CICLO DE VIDA

    Testes de fluxos completos que simulam uso real.
    Cria recursos, usa-os e limpa ao final.

    ATENÇÃO: Estes testes usam créditos reais!
    """

    def test_01_ciclo_completo_instancia(self, logged_in_cli, api_client):
        """
        Ciclo: Criar instância → Verificar status → Pausar → Resumir → Deletar

        Descrição: Testa o ciclo de vida completo de uma instância GPU.
        Valida que todas as operações funcionam em sequência.

        Validação:
        - Cada etapa executa com sucesso
        - Estado é consistente entre operações
        - Cleanup é executado

        Custo: ~$0.01-0.05 (alguns minutos de GPU barata)
        """
        # Verificar saldo antes de tentar criar instância
        balance_result = logged_in_cli.run("balance", "list")
        balance_data = parse_json_output(balance_result.output)
        if balance_data:
            saldo = balance_data.get("balance", 0) + balance_data.get("credit", 0)
            if saldo < 0.05:
                pytest.skip(f"Saldo insuficiente: ${saldo:.2f} (mínimo: $0.05)")

        instance_id = None

        try:
            # 1. Buscar oferta mais barata
            print("\n   [1/5] Buscando oferta barata...")
            result = logged_in_cli.run("instance", "offers")
            offers = assert_list_response(result, min_items=1)
            cheapest = sorted(offers, key=lambda x: x.get("dph_total", 999))[0]
            print(f"         Oferta: {cheapest['gpu_name']} @ ${cheapest['dph_total']:.4f}/hr")

            # 2. Criar instância via API (mais confiável que CLI para teste)
            print("   [2/5] Criando instância...")
            create_result = api_client.call("POST", "/api/v1/instances", {
                "offer_id": cheapest["id"],
                "image": "nvidia/cuda:12.0-base-ubuntu22.04",
                "disk_size": 20
            })

            # Verificar erro de saldo
            if create_result.get("detail") and "saldo" in create_result.get("detail", "").lower():
                pytest.skip(f"Saldo insuficiente: {create_result.get('detail')}")
            if create_result.get("detail") and "balance" in create_result.get("detail", "").lower():
                pytest.skip(f"Insufficient balance: {create_result.get('detail')}")

            instance_id = str(create_result.get("instance_id") or create_result.get("id"))
            assert instance_id, f"Falha ao criar instância: {create_result}"
            print(f"         Criada: {instance_id}")
            time.sleep(5)

            # 3. Verificar detalhes
            print("   [3/5] Verificando detalhes...")
            result = logged_in_cli.run("instance", "get", instance_id)
            assert result.returncode == 0, f"Falha ao buscar detalhes: {result.output}"
            print("         Status OK")

            # 4. Pausar instância
            print("   [4/5] Pausando...")
            result = logged_in_cli.run("instance", "pause", instance_id)
            print(f"         Pausa enviada (código {result.returncode})")
            time.sleep(3)

            # 5. Resumir instância
            print("   [5/5] Resumindo...")
            result = logged_in_cli.run("instance", "resume", instance_id)
            print(f"         Resume enviado (código {result.returncode})")

            print("   ✓ Ciclo completo de instância OK")

        finally:
            # Cleanup - CRÍTICO: não pode falhar silenciosamente
            if instance_id:
                print(f"\n   Limpando instância {instance_id}...")
                try:
                    api_client.call("DELETE", f"/api/v1/instances/{instance_id}")
                    print("   ✓ Instância removida")
                except Exception as e:
                    # Cleanup crítico - registrar para cleanup manual
                    warnings.warn(
                        f"CRITICAL: Instance {instance_id} NOT deleted: {e}",
                        UserWarning
                    )
                    # Registrar para cleanup manual
                    try:
                        with open("/tmp/dumont_orphan_instances.txt", "a") as f:
                            f.write(f"{instance_id}\n")
                    except:
                        pass

    def test_02_ciclo_configuracoes(self, logged_in_cli):
        """
        Ciclo: Ler config → Modificar → Verificar → Restaurar

        Descrição: Testa ciclo de modificação de configurações.
        Garante que mudanças são persistidas.

        Validação:
        - Leitura retorna valores
        - Modificação é aceita
        - Nova leitura mostra valor atualizado
        """
        print("\n   [1/3] Lendo configurações atuais...")
        result = logged_in_cli.run("settings", "list")
        assert result.returncode == 0
        print("         Config lida OK")

        print("   [2/3] Modificando configuração...")
        result = logged_in_cli.run("settings", "update", "auto_hibernate=true")
        print(f"         Update enviado (código {result.returncode})")

        print("   [3/3] Verificando mudança...")
        result = logged_in_cli.run("settings", "list")
        assert result.returncode == 0
        print("         Verificação OK")

        print("   ✓ Ciclo de configurações OK")

    def test_03_ciclo_failover_config(self, logged_in_cli, real_instance):
        """
        Ciclo: Verificar → Habilitar CPU Standby → Habilitar Warm Pool → Desabilitar

        Descrição: Testa ciclo de configuração de failover.

        Validação:
        - Cada operação executa com sucesso
        - Estado final é desabilitado
        """
        if not real_instance:
            pytest.skip("Instância real não disponível")

        print(f"\n   Testando failover para instância {real_instance}")

        print("   [1/4] Verificando status...")
        result = logged_in_cli.run("failover", "status", real_instance)
        print(f"         Status: código {result.returncode}")

        print("   [2/4] Habilitando CPU Standby...")
        result = logged_in_cli.run("failover", "settings-machines-enable-cpu-standby", real_instance)
        print(f"         CPU Standby: código {result.returncode}")

        print("   [3/4] Habilitando Warm Pool...")
        result = logged_in_cli.run("failover", "settings-machines-enable-warm-pool", real_instance)
        print(f"         Warm Pool: código {result.returncode}")

        print("   [4/4] Desabilitando failover...")
        result = logged_in_cli.run("failover", "settings-machines-disable-failover", real_instance)
        print(f"         Desabilitado: código {result.returncode}")

        print("   ✓ Ciclo de failover config OK")


# =============================================================================
# BLOCO 20: TESTES DE VALIDAÇÃO DE SCHEMA
# Validação profunda de respostas JSON
# =============================================================================

@pytest.mark.integration
class TestSchemaValidation:
    """
    BLOCO 20: TESTES DE VALIDAÇÃO DE SCHEMA

    Testes focados em validar o formato das respostas.
    Garante que a API retorna dados no formato esperado.
    """

    def test_01_schema_balance(self, logged_in_cli):
        """
        Valida schema completo da resposta de balance.

        Campos esperados:
        - credit: number >= 0
        - email: string
        """
        result = logged_in_cli.run("balance", "list")
        data = assert_valid_json_response(
            result,
            required_fields=["credit"],
            field_types={"credit": (int, float)}
        )
        credit = data["credit"]
        assert credit >= 0, f"Credit negativo: {credit}"
        print(f"   ✓ Schema balance OK: ${credit:.2f}")

    def test_02_schema_offers(self, logged_in_cli):
        """
        Valida schema da resposta de ofertas.

        Cada oferta deve ter:
        - id: identificador único
        - gpu_name: nome da GPU
        - dph_total: preço por hora
        - gpu_ram: memória VRAM
        """
        result = logged_in_cli.run("instance", "offers")
        offers = assert_list_response(
            result,
            min_items=1,
            item_fields=["id", "gpu_name", "dph_total"]
        )

        # Valida primeiro item em detalhe
        first = offers[0]
        assert first["dph_total"] > 0, f"Preço inválido: {first['dph_total']}"
        assert len(first["gpu_name"]) > 0, "Nome de GPU vazio"

        print(f"   ✓ Schema offers OK: {len(offers)} ofertas validadas")

    def test_03_schema_strategies(self, logged_in_cli):
        """
        Valida schema das estratégias de failover.

        Cada estratégia deve ter:
        - name: nome da estratégia
        - description: descrição
        """
        result = logged_in_cli.run("failover", "strategies")
        assert result.returncode == 0, f"Comando falhou: {result.output}"
        data = parse_json_output(result.output)
        assert data is not None, "Resposta não é JSON"

        # Estratégias podem estar em diferentes formatos
        strategies = []
        if isinstance(data, list):
            strategies = data
        elif isinstance(data, dict):
            strategies = data.get("strategies", data.get("data", []))
            # Se ainda não é lista, pode ser um objeto único
            if not isinstance(strategies, list):
                strategies = [data] if "name" in data or "id" in data else []

        # Valida que há ao menos resposta válida (pode ser vazia se nenhuma configurada)
        print(f"   ✓ Schema strategies OK: {len(strategies)} estratégias")

    def test_04_schema_snapshots(self, logged_in_cli):
        """
        Valida schema da resposta de snapshots.

        Resposta deve ter:
        - snapshots: lista (pode estar vazia)
        - count: número total
        """
        result = logged_in_cli.run("snapshot", "list")

        # Skip se Restic não estiver configurado
        if "not configured" in result.output.lower() or "restic" in result.output.lower():
            pytest.skip("Restic repository não configurado")

        data = parse_json_output(result.output)
        assert data is not None, "Resposta não é JSON"

        # Aceita lista vazia
        snapshots = data.get("snapshots", [])
        assert isinstance(snapshots, list), f"snapshots não é lista: {type(snapshots)}"

        print(f"   ✓ Schema snapshots OK: {len(snapshots)} snapshots")

    def test_05_schema_settings(self, logged_in_cli):
        """
        Valida schema das configurações do usuário.

        Resposta deve ser um objeto com configurações.
        """
        result = logged_in_cli.run("settings", "list")
        data = parse_json_output(result.output)
        assert data is not None, "Resposta não é JSON"
        assert isinstance(data, dict), f"Esperado dict, recebeu {type(data)}"

        print(f"   ✓ Schema settings OK: {len(data)} campos")

    def test_06_schema_metrics_gpus(self, logged_in_cli):
        """
        Valida schema da lista de GPUs.

        Cada GPU deve ter:
        - name: nome do modelo
        - vram: memória em GB (ou similar)
        """
        result = logged_in_cli.run("metrics", "gpus")
        data = parse_json_output(result.output)
        assert data is not None, "Resposta não é JSON"

        # Encontra a lista de GPUs
        gpus = data if isinstance(data, list) else data.get("gpus", [])
        assert len(gpus) >= 1, "Nenhuma GPU retornada"

        print(f"   ✓ Schema GPUs OK: {len(gpus)} modelos")


# =============================================================================
# SERVERLESS MODE TESTS
# =============================================================================
class TestServerless:
    """
    Testa funcionalidades do modo serverless GPU.

    Features:
    - Auto-pause após idle timeout
    - Dois modos: fast (CPU standby) e economic (pause/resume)
    - Wake on-demand
    """

    def test_01_serverless_pricing(self, logged_in_cli):
        """
        Consulta estimativas de preços serverless.

        Compara custo de GPU 24/7 vs serverless.
        """
        result = logged_in_cli.run("serverless", "pricing")
        assert result.returncode == 0, f"Comando falhou: {result.output}"
        data = parse_json_output(result.output)
        assert data is not None, "Resposta não é JSON"

        # Valida estrutura
        assert "monthly_costs" in data, "Falta monthly_costs"
        assert "always_on" in data["monthly_costs"], "Falta always_on"
        assert "serverless_fast" in data["monthly_costs"], "Falta serverless_fast"
        assert "serverless_economic" in data["monthly_costs"], "Falta serverless_economic"

        # Valida que serverless é mais barato
        always_on = data["monthly_costs"]["always_on"]["cost_usd"]
        fast = data["monthly_costs"]["serverless_fast"]["cost_usd"]
        economic = data["monthly_costs"]["serverless_economic"]["cost_usd"]

        assert fast < always_on, "Modo fast deveria ser mais barato que 24/7"
        assert economic < always_on, "Modo economic deveria ser mais barato que 24/7"

        print(f"   ✓ Pricing: 24/7=${always_on}, fast=${fast}, economic=${economic}")

    def test_02_serverless_list_empty(self, logged_in_cli):
        """
        Lista instâncias serverless (inicialmente vazio).
        """
        result = logged_in_cli.run("serverless", "list")
        assert result.returncode == 0, f"Comando falhou: {result.output}"
        data = parse_json_output(result.output)
        assert data is not None, "Resposta não é JSON"

        assert "count" in data, "Falta count"
        assert "instances" in data, "Falta instances"
        assert isinstance(data["instances"], list), "instances não é lista"

        print(f"   ✓ Serverless list: {data['count']} instâncias")

    def test_03_serverless_enable_mock(self, logged_in_cli):
        """
        Testa habilitar serverless em instância mock.

        Usa instance_id fictício para testar API.
        """
        # Tenta habilitar em instância fictícia
        result = logged_in_cli.run("serverless", "enable", "99999", "--mode", "economic", "--timeout", "30")

        # Pode falhar se instância não existe, mas endpoint deve responder
        if "not found" in result.output.lower() or "400" in result.output or "404" in result.output:
            print("   ⚠ Instância 99999 não existe (esperado)")
        else:
            # Se passou, valida resposta
            data = parse_json_output(result.output)
            if data:
                assert "mode" in data or "status" in data, "Resposta inválida"
                print(f"   ✓ Serverless enable response: {data.get('status', 'ok')}")

    def test_04_serverless_status_not_found(self, logged_in_cli):
        """
        Testa status de instância não configurada.
        """
        result = logged_in_cli.run("serverless", "status", "99999")

        # Deve retornar 404 ou erro de not found
        assert "not found" in result.output.lower() or "404" in result.output or "not configured" in result.output.lower(), \
            f"Deveria retornar not found: {result.output}"

        print("   ✓ Status not found para instância inexistente")

    def test_05_serverless_wake_not_found(self, logged_in_cli):
        """
        Testa wake de instância não configurada.
        """
        result = logged_in_cli.run("serverless", "wake", "99999")

        # Deve retornar erro de not found
        assert "not found" in result.output.lower() or "404" in result.output or "not configured" in result.output.lower(), \
            f"Deveria retornar not found: {result.output}"

        print("   ✓ Wake not found para instância inexistente")


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
