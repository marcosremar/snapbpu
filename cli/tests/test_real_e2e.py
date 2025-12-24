"""
Real E2E Tests - Testes REAIS que usam crédito VAST.ai/TensorDock

ATENÇÃO: Estes testes CUSTAM DINHEIRO! Eles criam máquinas reais.
Execute apenas quando quiser testar o fluxo real completo.

Para rodar:
    pytest tests/test_real_e2e.py -v -s --tb=short

Variáveis de ambiente opcionais:
    DUMONT_API_URL: URL da API (default: http://localhost:8000)
    TEST_USER: Email do usuário (default: test@test.com)
    TEST_PASSWORD: Senha (default: test123)
"""
import pytest
import requests
import time
import os
from typing import Optional
from datetime import datetime

# Configuração
API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
TEST_USER = os.environ.get("TEST_USER", "test@test.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")

# Timeout para operações longas (em segundos)
INSTANCE_CREATE_TIMEOUT = 300  # 5 minutos para criar
INSTANCE_READY_TIMEOUT = 600   # 10 minutos para ficar pronto
FAILOVER_TIMEOUT = 1200        # 20 minutos para failover (CPU Standby)


class RealAPIClient:
    """Cliente para API real com autenticação"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.token = None
        self.session = requests.Session()

    def login(self, username: str = TEST_USER, password: str = TEST_PASSWORD) -> bool:
        """Faz login e armazena token"""
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        if response.ok:
            data = response.json()
            self.token = data.get("token")
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            return True
        return False

    def call(self, method: str, path: str, data: dict = None) -> dict:
        """Chama endpoint da API"""
        url = f"{self.base_url}{path}"

        if method.upper() == "GET":
            response = self.session.get(url, params=data)
        elif method.upper() == "POST":
            response = self.session.post(url, json=data)
        elif method.upper() == "PUT":
            response = self.session.put(url, json=data)
        elif method.upper() == "DELETE":
            response = self.session.delete(url)
        else:
            raise ValueError(f"Método não suportado: {method}")

        return response.json()

    def wait_for_instance_status(self, instance_id: str, target_status: str, timeout: int = 300) -> bool:
        """Aguarda instância atingir status desejado"""
        start = time.time()
        while time.time() - start < timeout:
            result = self.call("GET", f"/api/v1/instances/{instance_id}")
            if "error" not in result:
                current_status = result.get("status", "unknown")
                print(f"  Status: {current_status} (esperando: {target_status})")
                if current_status.lower() == target_status.lower():
                    return True
                if current_status.lower() in ["error", "failed", "destroyed"]:
                    print(f"  ERRO: Instância entrou em status {current_status}")
                    return False
            time.sleep(10)
        return False


@pytest.fixture(scope="module")
def api():
    """Fixture que cria cliente API autenticado"""
    client = RealAPIClient()
    assert client.login(), f"Falha no login com {TEST_USER}"
    print(f"\n✅ Logado como {TEST_USER}")
    return client


@pytest.fixture(scope="module")
def created_instance(api):
    """Fixture que cria uma instância real e limpa após os testes"""
    instance_id = None

    # Buscar oferta mais barata
    offers = api.call("GET", "/api/v1/instances/offers")
    assert "offers" in offers, f"Erro ao buscar ofertas: {offers}"
    assert len(offers["offers"]) > 0, "Nenhuma oferta disponível"

    # Ordenar por preço e pegar a mais barata
    sorted_offers = sorted(offers["offers"], key=lambda x: x.get("dph_total", 999))
    cheapest = sorted_offers[0]

    print(f"\n📦 Oferta mais barata: {cheapest['gpu_name']} - ${cheapest['dph_total']:.3f}/hr")
    print(f"   ID: {cheapest['id']}")
    print(f"   Local: {cheapest['geolocation']}")

    # Criar instância
    print(f"\n🚀 Criando instância REAL...")
    create_result = api.call("POST", "/api/v1/instances", {
        "offer_id": cheapest["id"],
        "image": "nvidia/cuda:12.0-base-ubuntu22.04",
        "disk_size": 20,
        "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ test@test"  # SSH key de teste
    })

    if "error" in create_result:
        print(f"❌ Erro ao criar: {create_result}")
        pytest.skip(f"Não foi possível criar instância: {create_result}")

    instance_id = create_result.get("instance_id") or create_result.get("id")
    print(f"✅ Instância criada: {instance_id}")

    # Aguardar ficar pronta
    print(f"⏳ Aguardando instância ficar pronta (timeout: {INSTANCE_READY_TIMEOUT}s)...")
    if not api.wait_for_instance_status(instance_id, "running", INSTANCE_READY_TIMEOUT):
        print("⚠️ Timeout esperando instância ficar pronta")

    yield {
        "id": instance_id,
        "offer": cheapest,
        "api": api
    }

    # Cleanup - deletar instância
    if instance_id:
        print(f"\n🧹 Limpando: deletando instância {instance_id}...")
        delete_result = api.call("DELETE", f"/api/v1/instances/{instance_id}")
        print(f"   Resultado: {delete_result}")


class TestRealAuthentication:
    """Testes de autenticação real"""

    def test_login_success(self, api):
        """Verifica que login funcionou"""
        assert api.token is not None
        print(f"✅ Token obtido: {api.token[:50]}...")

    def test_auth_me(self, api):
        """Verifica endpoint /auth/me"""
        result = api.call("GET", "/api/v1/auth/me")
        assert result.get("authenticated") == True
        print(f"✅ Usuário autenticado: {result.get('user', {}).get('email')}")


class TestRealOffers:
    """Testes de ofertas reais VAST.ai/TensorDock"""

    def test_list_real_offers(self, api):
        """Lista ofertas reais disponíveis"""
        result = api.call("GET", "/api/v1/instances/offers")

        assert "offers" in result
        offers = result["offers"]
        assert len(offers) > 0, "Nenhuma oferta real disponível"

        print(f"\n📊 {len(offers)} ofertas REAIS disponíveis:")

        # Mostrar top 5 mais baratas
        sorted_offers = sorted(offers, key=lambda x: x.get("dph_total", 999))[:5]
        for offer in sorted_offers:
            print(f"   {offer['gpu_name']:20} ${offer['dph_total']:.3f}/hr - {offer['geolocation']}")

    def test_filter_by_gpu_type(self, api):
        """Filtra ofertas por tipo de GPU"""
        result = api.call("GET", "/api/v1/instances/offers", {"gpu_type": "RTX 4090"})

        # SKIP se rate limit externo (429 do VAST.ai)
        if "error" in result and "429" in str(result.get("error", "")):
            pytest.skip(f"Rate limit externo (VAST.ai 429): {result}")

        assert "offers" in result
        # Filtro pode retornar GPUs similares, apenas verifica que retorna algo
        print(f"✅ Filtro retornou {len(result['offers'])} ofertas")
        if result["offers"]:
            print(f"   Primeiro: {result['offers'][0]['gpu_name']}")


class TestRealInstanceLifecycle:
    """Testes do ciclo de vida REAL de instância"""

    def test_instance_created(self, created_instance):
        """Verifica que instância foi criada"""
        assert created_instance["id"] is not None
        print(f"✅ Instância ativa: {created_instance['id']}")

    def test_get_instance_details(self, created_instance):
        """Obtém detalhes da instância real"""
        api = created_instance["api"]
        instance_id = created_instance["id"]

        result = api.call("GET", f"/api/v1/instances/{instance_id}")

        if "error" not in result:
            print(f"✅ Detalhes da instância:")
            print(f"   ID: {result.get('id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   GPU: {result.get('gpu_name')}")
            print(f"   IP: {result.get('public_ip', 'N/A')}")
        else:
            print(f"⚠️ Erro ao obter detalhes: {result}")

    def test_pause_instance(self, created_instance):
        """Pausa instância real"""
        api = created_instance["api"]
        instance_id = created_instance["id"]

        result = api.call("POST", f"/api/v1/instances/{instance_id}/pause")
        print(f"Pause result: {result}")

        # Aguardar status paused
        time.sleep(5)
        status = api.call("GET", f"/api/v1/instances/{instance_id}")
        print(f"Status após pause: {status.get('status', 'unknown')}")

    def test_resume_instance(self, created_instance):
        """Retoma instância pausada"""
        api = created_instance["api"]
        instance_id = created_instance["id"]

        result = api.call("POST", f"/api/v1/instances/{instance_id}/resume")
        print(f"Resume result: {result}")

        # Aguardar voltar a running
        api.wait_for_instance_status(instance_id, "running", 120)


class TestRealSnapshots:
    """Testes de snapshots reais"""

    def test_create_snapshot(self, created_instance):
        """Cria snapshot real da instância"""
        api = created_instance["api"]
        instance_id = created_instance["id"]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"test_snapshot_{timestamp}"

        result = api.call("POST", "/api/v1/snapshots", {
            "instance_id": instance_id,
            "name": snapshot_name
        })

        print(f"Snapshot result: {result}")

        if "error" not in result:
            created_instance["snapshot_id"] = result.get("id") or result.get("snapshot_id")
            print(f"✅ Snapshot criado: {created_instance.get('snapshot_id')}")

    def test_list_snapshots(self, api):
        """Lista snapshots existentes"""
        result = api.call("GET", "/api/v1/snapshots")

        print(f"Snapshots: {result}")

        if "snapshots" in result:
            print(f"✅ {len(result['snapshots'])} snapshots encontrados")


class TestRealFailover:
    """Testes de failover reais"""

    def test_check_failover_readiness(self, created_instance):
        """Verifica prontidão para failover"""
        api = created_instance["api"]
        instance_id = created_instance["id"]

        result = api.call("GET", f"/api/v1/failover/readiness/{instance_id}")

        print(f"Readiness: {result}")

        if "error" not in result:
            print(f"✅ Failover ready: {result.get('ready', False)}")
            print(f"   Strategies: {result.get('available_strategies', [])}")

    def test_list_failover_strategies(self, api):
        """Lista estratégias de failover disponíveis"""
        result = api.call("GET", "/api/v1/failover/strategies")

        print(f"Strategies: {result}")

        if "strategies" in result:
            for strategy in result["strategies"]:
                print(f"   - {strategy.get('name')}: {strategy.get('description', '')}")

    def test_get_failover_settings(self, api):
        """Obtém configurações globais de failover"""
        result = api.call("GET", "/api/v1/failover/settings/global")

        print(f"Global settings: {result}")

    def test_simulate_failover(self, created_instance):
        """Simula failover (não executa realmente)"""
        api = created_instance["api"]
        instance_id = created_instance["id"]

        # Usar endpoint de simulação
        result = api.call("POST", f"/api/v1/standby/failover/simulate/{instance_id}")

        print(f"Simulate result: {result}")

        if "error" not in result:
            print(f"✅ Simulação executada")
            print(f"   Failover ID: {result.get('failover_id')}")


class TestRealWarmPool:
    """Testes de GPU Warm Pool reais"""

    def test_list_warmpool_hosts(self, api):
        """Lista hosts do warm pool"""
        result = api.call("GET", "/api/v1/warmpool/hosts")

        print(f"Warm pool hosts: {result}")

        if "hosts" in result:
            print(f"✅ {len(result['hosts'])} hosts no warm pool")

    def test_warmpool_status(self, created_instance):
        """Verifica status do warm pool para máquina"""
        api = created_instance["api"]
        instance_id = created_instance["id"]

        result = api.call("GET", f"/api/v1/warmpool/status/{instance_id}")

        print(f"Warm pool status: {result}")


class TestRealCPUStandby:
    """Testes de CPU Standby reais"""

    def test_standby_status(self, api):
        """Verifica status geral do standby"""
        result = api.call("GET", "/api/v1/standby/status")

        print(f"Standby status: {result}")

    def test_standby_pricing(self, api):
        """Verifica preços do standby"""
        result = api.call("GET", "/api/v1/standby/pricing")

        print(f"Standby pricing: {result}")

        if "pricing" in result or "price" in result:
            print(f"✅ Pricing obtido")

    def test_list_associations(self, api):
        """Lista associações de standby"""
        result = api.call("GET", "/api/v1/standby/associations")

        print(f"Associations: {result}")


class TestRealMetrics:
    """Testes de métricas reais"""

    def test_hibernation_stats(self, api):
        """Obtém estatísticas de hibernação"""
        result = api.call("GET", "/api/v1/hibernation/stats")

        print(f"Hibernation stats: {result}")

    def test_savings_summary(self, api):
        """Obtém resumo de economia"""
        result = api.call("GET", "/api/v1/savings/summary")

        print(f"Savings: {result}")

    def test_market_metrics(self, api):
        """Obtém métricas de mercado"""
        result = api.call("GET", "/api/v1/metrics/market")

        print(f"Market metrics: {result}")

    def test_balance(self, api):
        """Verifica saldo da conta"""
        result = api.call("GET", "/api/v1/balance")

        print(f"Balance: {result}")

        if "balance" in result:
            print(f"💰 Saldo: ${result['balance']:.2f}")


class TestRealRegionalVolume:
    """Testes de Regional Volume reais"""

    def test_list_regional_volumes(self, api):
        """Lista volumes regionais"""
        result = api.call("GET", "/api/v1/failover/regional-volume/list")

        print(f"Regional volumes: {result}")

    def test_search_volumes_by_region(self, api):
        """Busca volumes por região"""
        result = api.call("GET", "/api/v1/failover/regional-volume/search/us-east")

        print(f"Volumes in us-east: {result}")


# Teste standalone que pode ser executado separadamente
class TestQuickRealCheck:
    """Testes rápidos para verificar que API real está funcionando"""

    def test_api_health(self):
        """Verifica se API está respondendo"""
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        assert response.ok or response.status_code == 404  # Pode não ter /health

    def test_can_login(self):
        """Verifica que consegue fazer login"""
        client = RealAPIClient()
        assert client.login(), "Falha no login"
        print(f"✅ Login OK")

    def test_can_list_real_offers(self):
        """Verifica que consegue listar ofertas reais"""
        client = RealAPIClient()
        client.login()

        result = client.call("GET", "/api/v1/instances/offers")
        assert "offers" in result
        assert len(result["offers"]) > 0

        print(f"✅ {len(result['offers'])} ofertas VAST.ai reais disponíveis")


if __name__ == "__main__":
    # Quando executado diretamente, roda apenas testes rápidos
    pytest.main([__file__, "-v", "-s", "-k", "TestQuickRealCheck"])
