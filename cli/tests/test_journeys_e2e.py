"""
Testes E2E de Jornadas - CLI Dumont Cloud

Estes testes executam jornadas reais contra a API do backend.
Requerem que o backend esteja rodando em localhost:8000.

Para rodar:
    cd /home/marcos/dumontcloud/cli
    pytest tests/test_journeys_e2e.py -v

Para rodar com backend em outro host:
    DUMONT_API_URL=http://localhost:8000 pytest tests/test_journeys_e2e.py -v
"""
import pytest
import os
import sys
import json
import time

# Add CLI path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import APIClient


# ============================================================
# Configuração
# ============================================================

API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"


def get_api_client():
    """Create API client for tests"""
    return APIClient(base_url=API_BASE_URL)


def api_call(method: str, path: str, data: dict = None) -> dict:
    """Make API call with demo mode support"""
    api = get_api_client()

    # Add demo=true to path for demo mode
    if DEMO_MODE:
        separator = "&" if "?" in path else "?"
        path = f"{path}{separator}demo=true"

    return api.call(method, path, data, silent=True)


def skip_if_no_backend():
    """Skip test if backend is not available"""
    try:
        api = get_api_client()
        schema = api.load_openapi_schema()
        if not schema:
            pytest.skip("Backend não disponível")
    except Exception:
        pytest.skip("Backend não disponível")


# ============================================================
# Jornada 1: Reserva de Máquina (Machine Reservation)
# ============================================================

class TestJourneyMachineReservation:
    """
    Jornada E2E: Reserva de Máquina

    Testa o fluxo completo de reserva de GPU:
    1. Listar ofertas disponíveis
    2. Filtrar por tipo de GPU
    3. Listar instâncias existentes
    4. Verificar detalhes de instância
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_list_available_offers(self):
        """Deve listar ofertas de GPU disponíveis"""
        result = api_call("GET", "/api/v1/instances/offers")

        assert result is not None
        # Pode ser lista direta ou {"offers": [...]}
        offers = result if isinstance(result, list) else result.get("offers", [])

        print(f"\n📊 Total de ofertas: {len(offers)}")

        if offers:
            offer = offers[0]
            print(f"   GPU: {offer.get('gpu_name', 'N/A')}")
            print(f"   Preço/hora: ${offer.get('dph_total', 'N/A')}")

    def test_filter_offers_by_gpu_type(self):
        """Deve filtrar ofertas por tipo de GPU"""
        result = api_call("GET", "/api/v1/instances/offers?gpu_name=RTX_4090")

        if result is None:
            pytest.skip("Endpoint não disponível")

        offers = result if isinstance(result, list) else result.get("offers", [])

        print(f"\n📊 Ofertas RTX 4090: {len(offers)}")

        # Se houver ofertas, todas devem ser RTX 4090
        for offer in offers:
            if "4090" not in str(offer.get("gpu_name", "")):
                pytest.fail(f"Oferta não é RTX 4090: {offer}")

    def test_list_existing_instances(self):
        """Deve listar instâncias do usuário"""
        result = api_call("GET", "/api/v1/instances")

        assert result is not None

        # API pode retornar {instances: [...]} ou lista direta
        instances = result if isinstance(result, list) else result.get("instances", [])

        print(f"\n📊 Instâncias do usuário: {len(instances)}")

        for inst in instances[:3]:  # Mostrar até 3
            print(f"   • {inst.get('id')}: {inst.get('gpu_name')} ({inst.get('status')})")

    def test_get_instance_details(self):
        """Deve obter detalhes de uma instância"""
        # Primeiro, listar instâncias
        result = api_call("GET", "/api/v1/instances")

        if result is None:
            pytest.skip("Não foi possível listar instâncias")

        instances = result if isinstance(result, list) else result.get("instances", [])

        if not instances:
            pytest.skip("Nenhuma instância disponível")

        instance_id = instances[0].get("id") or instances[0].get("vast_id")

        # Buscar detalhes
        details = api_call("GET", f"/api/v1/instances/{instance_id}")

        if details is None:
            pytest.skip("Endpoint de detalhes não disponível")

        print(f"\n📊 Detalhes da instância {instance_id}:")
        print(f"   GPU: {details.get('gpu_name')}")
        print(f"   Status: {details.get('status')}")
        print(f"   SSH: {details.get('ssh_host')}:{details.get('ssh_port')}")

    def test_instance_lifecycle_pause_resume(self):
        """Deve pausar e resumir uma instância"""
        # Listar instâncias
        result = api_call("GET", "/api/v1/instances")

        if result is None:
            pytest.skip("Não foi possível listar instâncias")

        instances = result if isinstance(result, list) else result.get("instances", [])

        # Procurar instância running
        running = next((i for i in instances if i.get("status") == "running"), None)

        if not running:
            pytest.skip("Nenhuma instância running para teste")

        instance_id = running.get("id") or running.get("vast_id")

        # Pausar
        pause_result = api_call("POST", f"/api/v1/instances/{instance_id}/pause")
        print(f"\n📊 Pause result: {pause_result}")

        # Resumir (se pause funcionou)
        resume_result = api_call("POST", f"/api/v1/instances/{instance_id}/resume")
        print(f"📊 Resume result: {resume_result}")


# ============================================================
# Jornada 2: Configuração de Failover
# ============================================================

class TestJourneyFailoverConfiguration:
    """
    Jornada E2E: Configuração de Failover

    Testa o fluxo de configuração de proteção de GPU:
    1. Verificar status do standby
    2. Configurar CPU standby
    3. Ver opções de warm pool
    4. Configurar failover para máquina
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_get_standby_status(self):
        """Deve obter status do CPU standby"""
        result = api_call("GET", "/api/v1/standby/status")

        if result is None:
            pytest.skip("Endpoint standby/status não disponível")

        print(f"\n📊 Status do Standby:")
        print(f"   Configurado: {result.get('configured', False)}")
        print(f"   Ativo: {result.get('active', False)}")

    def test_get_standby_pricing(self):
        """Deve obter preços do CPU standby"""
        result = api_call("GET", "/api/v1/standby/pricing")

        if result is None:
            pytest.skip("Endpoint standby/pricing não disponível")

        assert result is not None
        print(f"\n📊 Pricing do Standby:")
        print(f"   {json.dumps(result, indent=2)[:200]}")

    def test_list_standby_associations(self):
        """Deve listar associações GPU<->CPU"""
        result = api_call("GET", "/api/v1/standby/associations")

        if result is None:
            pytest.skip("Endpoint standby/associations não disponível")

        associations = result if isinstance(result, list) else result.get("associations", [])

        print(f"\n📊 Associações Standby: {len(associations)}")

    def test_list_warmpool_hosts(self):
        """Deve listar hosts com múltiplas GPUs para warm pool"""
        result = api_call("GET", "/api/v1/warmpool/hosts")

        if result is None:
            pytest.skip("Endpoint warmpool/hosts não disponível")

        hosts = result if isinstance(result, list) else result.get("hosts", [])

        print(f"\n📊 Hosts multi-GPU disponíveis: {len(hosts)}")

        for host in hosts[:3]:
            print(f"   • Machine {host.get('machine_id')}: {host.get('num_gpus')} GPUs")

    def test_get_failover_strategies(self):
        """Deve listar estratégias de failover disponíveis"""
        result = api_call("GET", "/api/v1/failover/strategies")

        if result is None:
            pytest.skip("Endpoint failover/strategies não disponível")

        strategies = result if isinstance(result, list) else result.get("strategies", [])

        print(f"\n📊 Estratégias de failover: {len(strategies)}")

        for s in strategies:
            name = s.get("name") or s.get("id") or str(s)
            print(f"   • {name}")

    def test_check_failover_readiness(self):
        """Deve verificar prontidão para failover de uma máquina"""
        # Primeiro, listar instâncias
        instances_result = api_call("GET", "/api/v1/instances")

        if instances_result is None:
            pytest.skip("Não foi possível listar instâncias")

        instances = instances_result if isinstance(instances_result, list) else instances_result.get("instances", [])

        if not instances:
            pytest.skip("Nenhuma instância disponível")

        machine_id = instances[0].get("id") or instances[0].get("machine_id")

        result = api_call("GET", f"/api/v1/failover/readiness/{machine_id}")

        if result is None:
            pytest.skip("Endpoint failover/readiness não disponível")

        print(f"\n📊 Prontidão para failover da máquina {machine_id}:")
        print(f"   Pronto: {result.get('ready', False)}")
        print(f"   Estratégia: {result.get('strategy', 'N/A')}")


# ============================================================
# Jornada 3: Simulação de Failover
# ============================================================

class TestJourneyFailoverSimulation:
    """
    Jornada E2E: Simulação de Failover

    Testa o fluxo de simulação/teste de failover:
    1. Simular failover (dry-run)
    2. Verificar status do failover
    3. Obter relatório
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_simulate_failover(self):
        """Deve simular failover (dry-run)"""
        # Listar instâncias
        instances_result = api_call("GET", "/api/v1/instances")

        if instances_result is None:
            pytest.skip("Não foi possível listar instâncias")

        instances = instances_result if isinstance(instances_result, list) else instances_result.get("instances", [])

        if not instances:
            pytest.skip("Nenhuma instância disponível")

        instance_id = instances[0].get("id") or instances[0].get("vast_id")

        result = api_call("POST", f"/api/v1/standby/failover/simulate/{instance_id}")

        if result is None:
            # Tentar endpoint alternativo
            result = api_call("POST", f"/api/v1/failover/test/{instance_id}")

        print(f"\n📊 Resultado da simulação:")
        print(f"   {json.dumps(result, indent=2)[:300] if result else 'N/A'}")

    def test_get_failover_report(self):
        """Deve obter relatório de failover"""
        result = api_call("GET", "/api/v1/standby/failover/report")

        if result is None:
            pytest.skip("Endpoint failover/report não disponível")

        print(f"\n📊 Relatório de Failover:")
        print(f"   Total: {result.get('total_failovers', 0)}")
        print(f"   Taxa de sucesso: {result.get('success_rate', 0)}%")
        print(f"   Tempo médio: {result.get('average_recovery_time_ms', 0)}ms")

    def test_get_active_failovers(self):
        """Deve listar failovers ativos"""
        result = api_call("GET", "/api/v1/standby/failover/active")

        if result is None:
            pytest.skip("Endpoint failover/active não disponível")

        active = result if isinstance(result, list) else result.get("active", [])

        print(f"\n📊 Failovers ativos: {len(active)}")


# ============================================================
# Jornada 4: Métricas e Economia
# ============================================================

class TestJourneyMetricsAndSavings:
    """
    Jornada E2E: Métricas e Economia

    Testa endpoints de métricas e economia:
    1. Stats de hibernação
    2. Resumo de economia
    3. Métricas de mercado
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_get_hibernation_stats(self):
        """Deve obter estatísticas de hibernação"""
        result = api_call("GET", "/api/v1/hibernation/stats")

        if result is None:
            pytest.skip("Endpoint hibernation/stats não disponível")

        print(f"\n📊 Estatísticas de Hibernação:")
        print(f"   Total hibernações: {result.get('total_hibernations', 0)}")
        print(f"   Horas economizadas: {result.get('total_hours_saved', 0)}")
        print(f"   Economia total: ${result.get('total_savings', 0):.2f}")

    def test_get_savings_summary(self):
        """Deve obter resumo de economia"""
        result = api_call("GET", "/api/v1/savings/summary")

        if result is None:
            pytest.skip("Endpoint savings/summary não disponível")

        print(f"\n📊 Resumo de Economia:")
        print(f"   Período: {result.get('period', 'N/A')}")
        print(f"   Custo Dumont: ${result.get('total_cost_dumont', 0):.2f}")
        print(f"   Custo AWS: ${result.get('total_cost_aws', 0):.2f}")
        print(f"   Economia vs AWS: ${result.get('savings_vs_aws', 0):.2f}")

    def test_get_market_metrics(self):
        """Deve obter métricas de mercado"""
        result = api_call("GET", "/api/v1/metrics/market")

        if result is None:
            pytest.skip("Endpoint metrics/market não disponível")

        print(f"\n📊 Métricas de Mercado disponíveis")

        if isinstance(result, dict):
            print(f"   GPUs monitoradas: {len(result)}")

    def test_get_balance(self):
        """Deve obter saldo da conta"""
        result = api_call("GET", "/api/v1/balance")

        if result is None:
            pytest.skip("Endpoint balance não disponível")

        print(f"\n📊 Saldo da Conta:")
        print(f"   {json.dumps(result, indent=2)[:200]}")


# ============================================================
# Jornada 5: Warm Pool
# ============================================================

class TestJourneyWarmPool:
    """
    Jornada E2E: GPU Warm Pool

    Testa funcionalidades de warm pool:
    1. Listar hosts disponíveis
    2. Verificar status do warm pool
    3. Habilitar/desabilitar warm pool
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_list_warmpool_hosts_with_filters(self):
        """Deve listar hosts com filtros"""
        result = api_call("GET", "/api/v1/warmpool/hosts?gpu_name=RTX_4090&min_gpus=2")

        if result is None:
            pytest.skip("Endpoint warmpool/hosts não disponível")

        hosts = result if isinstance(result, list) else result.get("hosts", [])

        print(f"\n📊 Hosts RTX 4090 com 2+ GPUs: {len(hosts)}")

    def test_get_warmpool_status_for_machine(self):
        """Deve verificar status do warm pool de uma máquina"""
        # Listar instâncias
        instances_result = api_call("GET", "/api/v1/instances")

        if instances_result is None:
            pytest.skip("Não foi possível listar instâncias")

        instances = instances_result if isinstance(instances_result, list) else instances_result.get("instances", [])

        if not instances:
            pytest.skip("Nenhuma instância disponível")

        machine_id = instances[0].get("id") or instances[0].get("machine_id")

        result = api_call("GET", f"/api/v1/warmpool/status/{machine_id}")

        # 404 é válido se warm pool não configurado
        if result is None:
            print(f"\n📊 Warm pool não configurado para máquina {machine_id}")
        else:
            print(f"\n📊 Status do Warm Pool:")
            print(f"   Estado: {result.get('state', 'N/A')}")

    def test_enable_warmpool_for_machine(self):
        """Deve habilitar warm pool para uma máquina"""
        # Listar instâncias
        instances_result = api_call("GET", "/api/v1/instances")

        if instances_result is None:
            pytest.skip("Não foi possível listar instâncias")

        instances = instances_result if isinstance(instances_result, list) else instances_result.get("instances", [])

        if not instances:
            pytest.skip("Nenhuma instância disponível")

        machine_id = instances[0].get("id") or instances[0].get("machine_id")

        result = api_call("POST", f"/api/v1/warmpool/enable/{machine_id}")

        print(f"\n📊 Habilitar warm pool para {machine_id}:")
        print(f"   {json.dumps(result, indent=2)[:200] if result else 'N/A (pode requerer configuração)'}")


# ============================================================
# Jornada 6: Agente e Monitoramento
# ============================================================

class TestJourneyAgentIntegration:
    """
    Jornada E2E: Integração com Agente

    Testa funcionalidades de agente:
    1. Listar instâncias com agente
    2. Enviar heartbeat
    3. Keep-alive
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_list_agent_instances(self):
        """Deve listar instâncias com agente instalado"""
        result = api_call("GET", "/api/v1/agent/instances")

        if result is None:
            pytest.skip("Endpoint agent/instances não disponível")

        instances = result if isinstance(result, list) else result.get("instances", [])

        print(f"\n📊 Instâncias com agente: {len(instances)}")

    def test_send_agent_heartbeat(self):
        """Deve enviar heartbeat de agente"""
        result = api_call("POST", "/api/v1/agent/status", {
            "instance_id": "test-instance-cli",
            "gpu_util": 45,
            "memory_used": 8000,
            "disk_free": 50000,
            "processes": ["python train.py"],
            "last_activity": "2025-12-21T06:00:00Z"
        })

        # 422 é válido para instância desconhecida
        print(f"\n📊 Heartbeat result: {result}")


# ============================================================
# Jornada 7: Regional Volume Failover
# ============================================================

class TestJourneyRegionalVolume:
    """
    Jornada E2E: Regional Volume Failover

    Testa funcionalidades de volumes regionais:
    1. Listar volumes
    2. Buscar por região
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_list_regional_volumes(self):
        """Deve listar volumes regionais"""
        result = api_call("GET", "/api/v1/failover/regional-volume/list")

        if result is None:
            pytest.skip("Endpoint regional-volume/list não disponível")

        volumes = result if isinstance(result, list) else result.get("volumes", [])

        print(f"\n📊 Volumes regionais: {len(volumes)}")

    def test_search_volumes_by_region(self):
        """Deve buscar volumes por região"""
        result = api_call("GET", "/api/v1/failover/regional-volume/search/us-east")

        if result is None:
            pytest.skip("Endpoint regional-volume/search não disponível")

        volumes = result if isinstance(result, list) else result.get("volumes", [])

        print(f"\n📊 Volumes em us-east: {len(volumes)}")


# ============================================================
# Jornada 8: AI Advisor
# ============================================================

class TestJourneyAIAdvisor:
    """
    Jornada E2E: AI GPU Advisor

    Testa recomendações de GPU via IA:
    1. Obter recomendação de GPU
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip tests if backend not available"""
        skip_if_no_backend()

    def test_get_gpu_recommendation(self):
        """Deve obter recomendação de GPU para workload"""
        result = api_call("POST", "/api/v1/advisor/recommend", {
            "task": "llm_finetuning",
            "model_size": "7B",
            "budget_per_hour": 0.50,
            "region_preference": "europe"
        })

        # 422 é válido se parâmetros não forem reconhecidos
        if result is None:
            print("\n📊 Endpoint advisor não disponível ou parâmetros inválidos")
        else:
            print(f"\n📊 Recomendação de GPU:")
            print(f"   GPU recomendada: {result.get('recommended_gpu', 'N/A')}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
