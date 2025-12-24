"""
Testes de Integração REAIS - Dumont Cloud CLI

ATENÇÃO: Estes testes USAM CRÉDITOS REAIS da VAST.ai!
Cada teste provisiona máquinas reais e custa dinheiro.

Para rodar:
    cd /home/marcos/dumontcloud/cli
    source ../venv/bin/activate
    pytest tests/test_real_integration.py -v -s --tb=short

Variáveis de ambiente:
    DUMONT_API_URL: URL da API (default: http://localhost:8000)
    TEST_USER: Email (default: test@test.com)
    TEST_PASSWORD: Senha (default: test123)
"""
import pytest
import requests
import time
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict

# ============================================================
# Configuração
# ============================================================

API_BASE_URL = os.environ.get("DUMONT_API_URL", "http://localhost:8000")
TEST_USER = os.environ.get("TEST_USER", "test@test.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")

# Timeouts em segundos
INSTANCE_CREATE_TIMEOUT = 300   # 5 min
INSTANCE_READY_TIMEOUT = 600    # 10 min
SSH_READY_TIMEOUT = 120         # 2 min após running
MODEL_INSTALL_TIMEOUT = 1200    # 20 min
SNAPSHOT_TIMEOUT = 600          # 10 min
FAILOVER_TIMEOUT = 1200         # 20 min

# Rate limiting
RATE_LIMIT_INITIAL_DELAY = 3    # segundos
RATE_LIMIT_MAX_DELAY = 60       # segundos máximo
RATE_LIMIT_MAX_RETRIES = 10

# Delays entre operações para evitar rate limit
DELAY_BETWEEN_CALLS = 2         # segundos entre chamadas API
DELAY_AFTER_CREATE = 5          # segundos após criar instância
DELAY_POLL_STATUS = 15          # segundos entre polls de status


# ============================================================
# Métricas
# ============================================================

@dataclass
class TestMetrics:
    """Métricas coletadas durante os testes"""
    test_name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    instance_id: Optional[str] = None
    gpu_name: Optional[str] = None
    gpu_cost_per_hour: float = 0
    total_cost: float = 0
    success: bool = False
    error_message: Optional[str] = None

    # Métricas de tempo específicas
    time_to_running: float = 0
    time_to_ssh_ready: float = 0
    time_to_model_install: float = 0
    time_to_snapshot: float = 0
    time_to_failover: float = 0
    time_to_restore: float = 0

    def finish(self, success: bool = True, error: str = None):
        """Finaliza as métricas"""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error_message = error

        # Calcular custo estimado
        if self.gpu_cost_per_hour > 0:
            hours = self.duration_seconds / 3600
            self.total_cost = hours * self.gpu_cost_per_hour

    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return asdict(self)


class MetricsCollector:
    """Coletor de métricas para relatório final"""

    def __init__(self):
        self.metrics: List[TestMetrics] = []
        self.start_time = datetime.now()

    def add(self, metrics: TestMetrics):
        self.metrics.append(metrics)

    def generate_report(self) -> str:
        """Gera relatório final"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        total_cost = sum(m.total_cost for m in self.metrics)
        success_count = sum(1 for m in self.metrics if m.success)

        lines = [
            "=" * 60,
            "RELATÓRIO DE TESTES REAIS DE INTEGRAÇÃO",
            "=" * 60,
            f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duração total: {total_duration/60:.1f} minutos",
            f"Custo total estimado: ${total_cost:.4f}",
            "",
            "TESTES EXECUTADOS:",
        ]

        for m in self.metrics:
            status = "✅" if m.success else "❌"
            cost_str = f"${m.total_cost:.4f}" if m.total_cost > 0 else "N/A"
            duration_str = f"{m.duration_seconds/60:.1f} min"
            gpu_str = m.gpu_name or "N/A"
            lines.append(f"  {status} {m.test_name}: {duration_str} ({gpu_str}, {cost_str})")

            if not m.success and m.error_message:
                lines.append(f"      Erro: {m.error_message[:100]}")

        lines.extend([
            "",
            "MÉTRICAS MÉDIAS:",
            f"  - Tempo para running: {self._avg('time_to_running'):.1f}s",
            f"  - Tempo para SSH: {self._avg('time_to_ssh_ready'):.1f}s",
            f"  - Tempo para snapshot: {self._avg('time_to_snapshot'):.1f}s",
            f"  - Tempo para failover: {self._avg('time_to_failover'):.1f}s",
            "",
            f"Taxa de sucesso: {success_count}/{len(self.metrics)} ({100*success_count/len(self.metrics) if self.metrics else 0:.0f}%)",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _avg(self, field: str) -> float:
        values = [getattr(m, field) for m in self.metrics if getattr(m, field, 0) > 0]
        return sum(values) / len(values) if values else 0


# Coletor global
metrics_collector = MetricsCollector()


# ============================================================
# Cliente API com Rate Limiting
# ============================================================

class RealAPIClient:
    """Cliente para API real com rate limiting e retry"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.token = None
        self.session = requests.Session()
        self.last_call_time = 0

    def _wait_rate_limit(self):
        """Espera tempo mínimo entre chamadas"""
        elapsed = time.time() - self.last_call_time
        if elapsed < DELAY_BETWEEN_CALLS:
            time.sleep(DELAY_BETWEEN_CALLS - elapsed)
        self.last_call_time = time.time()

    def login(self, username: str = TEST_USER, password: str = TEST_PASSWORD) -> bool:
        """Faz login com retry"""
        return self._call_with_retry(
            lambda: self._do_login(username, password)
        )

    def _do_login(self, username: str, password: str) -> bool:
        """Executa login"""
        self._wait_rate_limit()
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        if response.ok:
            data = response.json()
            self.token = data.get("access_token") or data.get("token")
            if self.token:
                self.session.headers["Authorization"] = f"Bearer {self.token}"
            return True
        return False

    def call(self, method: str, path: str, data: dict = None) -> Optional[dict]:
        """Chama API com retry automático"""
        return self._call_with_retry(
            lambda: self._do_call(method, path, data)
        )

    def _do_call(self, method: str, path: str, data: dict = None) -> dict:
        """Executa chamada HTTP"""
        self._wait_rate_limit()
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

        # Rate limit check
        if response.status_code == 429:
            raise RateLimitError("429 Too Many Requests")

        try:
            return response.json()
        except:
            return {"status": response.status_code, "text": response.text[:200]}

    def _call_with_retry(self, func, max_retries: int = RATE_LIMIT_MAX_RETRIES):
        """Executa função com backoff exponencial em rate limit"""
        delay = RATE_LIMIT_INITIAL_DELAY

        for attempt in range(max_retries):
            try:
                result = func()

                # Verificar se resposta indica rate limit
                if isinstance(result, dict):
                    error = result.get("error", "")
                    if "429" in str(error) or "Too Many Requests" in str(error):
                        raise RateLimitError(error)

                return result

            except RateLimitError as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Rate limit (tentativa {attempt + 1}/{max_retries}). Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                    delay = min(delay * 1.5, RATE_LIMIT_MAX_DELAY)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Erro de conexão. Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                    delay = min(delay * 1.5, RATE_LIMIT_MAX_DELAY)
                else:
                    raise

        raise Exception(f"Max retries ({max_retries}) exceeded")

    def wait_for_status(self, instance_id: str, target_status: str, timeout: int = 600) -> bool:
        """Aguarda instância atingir status desejado"""
        start = time.time()
        while time.time() - start < timeout:
            result = self.call("GET", f"/api/v1/instances/{instance_id}")

            if result and "error" not in result:
                current = result.get("status", "").lower()
                actual = result.get("actual_status", "").lower()

                print(f"  Status: {current} (actual: {actual}) - aguardando: {target_status}")

                if current == target_status.lower() or actual == target_status.lower():
                    return True

                if current in ["error", "failed", "destroyed"]:
                    print(f"  ❌ Instância em estado de erro: {current}")
                    return False

            time.sleep(DELAY_POLL_STATUS)

        return False


class RateLimitError(Exception):
    """Erro de rate limit"""
    pass


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="module")
def api():
    """Cliente API autenticado"""
    client = RealAPIClient()

    print(f"\n🔐 Fazendo login como {TEST_USER}...")
    if not client.login():
        pytest.fail(f"Falha no login com {TEST_USER}")

    print(f"✅ Login OK")
    return client


def create_instance_with_retry(api, max_retries: int = 5, image: str = "nvidia/cuda:12.0-base-ubuntu22.04", use_ondemand: bool = True):
    """
    Cria uma instância com retry, tentando diferentes ofertas se necessário.
    Usa ofertas on-demand (estáveis) por padrão ao invés de spot/interruptíveis.
    Tenta ofertas mais caras (menos disputadas) se as baratas não funcionarem.
    Retorna (instance_id, offer_info) ou (None, None) se falhar.
    """
    retry_delay = 3
    machine_type = "on-demand" if use_ondemand else None

    # Estratégia: Começar com preço baixo e aumentar a cada retry
    price_limits = [1.0, 2.0, 3.0, 4.0, 5.0]

    for attempt in range(max_retries):
        max_price = price_limits[min(attempt, len(price_limits) - 1)]

        # Buscar ofertas on-demand (mais estáveis, não são interrompidas)
        url = f"/api/v1/instances/offers?max_price={max_price}&limit=50"
        if machine_type:
            url += f"&machine_type={machine_type}"

        result = api.call("GET", url)

        if not result or "error" in result:
            print(f"⚠️ Tentativa {attempt + 1}/{max_retries}: Erro ao buscar ofertas: {result}")
            time.sleep(retry_delay)
            retry_delay *= 1.5
            continue

        offers = result.get("offers", [])
        if not offers:
            print(f"⚠️ Tentativa {attempt + 1}/{max_retries}: Nenhuma oferta disponível até ${max_price}/hr")
            time.sleep(retry_delay)
            retry_delay *= 1.5
            continue

        # Ordenar por preço e tentar MAIS ofertas (10 ao invés de 5)
        # Também incluir ofertas um pouco mais caras que são menos disputadas
        sorted_offers = sorted(offers, key=lambda x: x.get("dph_total", 999))

        # Estratégia: tentar algumas baratas + algumas do meio da lista
        offers_to_try = sorted_offers[:5] + sorted_offers[10:15] if len(sorted_offers) > 15 else sorted_offers[:10]

        for offer in offers_to_try:
            offer_type = "on-demand" if machine_type else "spot"
            print(f"🔄 Tentando criar instância {offer_type} com {offer.get('gpu_name')} (${offer.get('dph_total', 0):.4f}/hr)...")

            create_result = api.call("POST", "/api/v1/instances", {
                "offer_id": offer["id"],
                "image": image,
                "disk_size": 20,
                "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ test@test",
                "skip_validation": True  # Skip pre-validation to avoid race condition
            })

            if create_result and "error" not in create_result:
                instance_id = create_result.get("instance_id") or create_result.get("id")
                if instance_id:
                    print(f"✅ Instância criada: {instance_id}")
                    return instance_id, offer

            print(f"   ❌ Falha: {create_result}")
            time.sleep(1)  # Delay menor entre ofertas

        print(f"⚠️ Nenhuma das ofertas funcionou. Tentando com preço maior...")
        time.sleep(retry_delay)
        retry_delay *= 1.2

    return None, None


@pytest.fixture(scope="module")
def cheapest_offer(api):
    """Busca a oferta de GPU on-demand mais barata disponível com retry"""
    print("\n🔍 Buscando ofertas de GPU on-demand (estáveis)...")

    # Retry com backoff se não encontrar ofertas
    max_retries = 5
    retry_delay = 10  # segundos

    for attempt in range(max_retries):
        # Buscar ofertas ON-DEMAND (estáveis, não são interrompidas)
        result = api.call("GET", "/api/v1/instances/offers?machine_type=on-demand&max_price=5.0")

        if not result or "error" in result:
            if attempt < max_retries - 1:
                print(f"⚠️ Tentativa {attempt + 1}/{max_retries} falhou: {result}")
                print(f"   Aguardando {retry_delay}s antes de tentar novamente...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
                continue
            pytest.skip(f"Não foi possível buscar ofertas após {max_retries} tentativas: {result}")

        offers = result.get("offers", [])
        if not offers:
            if attempt < max_retries - 1:
                print(f"⚠️ Tentativa {attempt + 1}/{max_retries}: Nenhuma oferta on-demand disponível")
                print(f"   Aguardando {retry_delay}s antes de tentar novamente...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
                continue
            pytest.skip(f"Nenhuma oferta on-demand disponível após {max_retries} tentativas")

        # Ordenar por preço
        sorted_offers = sorted(offers, key=lambda x: x.get("dph_total", 999))
        cheapest = sorted_offers[0]

        print(f"📦 Oferta on-demand mais barata: {cheapest.get('gpu_name')} - ${cheapest.get('dph_total', 0):.4f}/hr")
        print(f"   ID: {cheapest.get('id')}")
        print(f"   RAM: {cheapest.get('gpu_ram', 'N/A')} GB")
        print(f"   Local: {cheapest.get('geolocation', 'N/A')}")

        return cheapest

    pytest.skip("Nenhuma oferta on-demand disponível após todas as tentativas")


@pytest.fixture
def cleanup_instances(api):
    """Fixture que garante limpeza de instâncias ao final"""
    created_instances: List[str] = []

    yield created_instances

    # Cleanup
    for instance_id in created_instances:
        try:
            print(f"\n🧹 Deletando instância {instance_id}...")
            result = api.call("DELETE", f"/api/v1/instances/{instance_id}")
            print(f"   Resultado: {result}")
        except Exception as e:
            print(f"   ⚠️ Erro ao deletar: {e}")


# ============================================================
# Testes Rápidos (sem criar instância)
# ============================================================

class TestQuickRealChecks:
    """Testes rápidos de verificação da API real"""

    def test_api_health(self):
        """Verifica se API está respondendo"""
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        assert response.ok, f"API não está healthy: {response.status_code}"
        print(f"✅ API healthy: {response.json()}")

    def test_login_real(self, api):
        """Verifica login real"""
        assert api.token is not None
        print(f"✅ Token: {api.token[:30]}...")

    def test_list_real_offers(self, api):
        """Lista ofertas reais da VAST.ai"""
        result = api.call("GET", "/api/v1/instances/offers")

        assert result is not None
        assert "error" not in result, f"Erro: {result}"

        offers = result.get("offers", [])
        print(f"\n📊 {len(offers)} ofertas REAIS disponíveis")

        if offers:
            sorted_offers = sorted(offers, key=lambda x: x.get("dph_total", 999))[:5]
            print("\nTop 5 mais baratas:")
            for offer in sorted_offers:
                print(f"  • {offer.get('gpu_name', 'N/A'):20} "
                      f"${offer.get('dph_total', 0):.4f}/hr "
                      f"RAM:{offer.get('gpu_ram', 'N/A')}GB "
                      f"({offer.get('geolocation', 'N/A')})")

    def test_check_balance(self, api):
        """Verifica saldo da conta"""
        result = api.call("GET", "/api/v1/balance")

        if result and "balance" in result:
            print(f"\n💰 Saldo: ${result['balance']:.2f}")
        else:
            print(f"\n💰 Resposta balance: {result}")


# ============================================================
# Jornada 1: Ciclo de Vida Completo de Instância
# ============================================================

class TestRealInstanceLifecycleJourney:
    """
    Jornada REAL de ciclo de vida de instância:
    1. Criar instância com GPU mais barata
    2. Aguardar ficar running
    3. Verificar detalhes
    4. Pausar
    5. Resumir
    6. Deletar

    Mede tempo de cada etapa.
    """

    def test_full_instance_lifecycle(self, api, cleanup_instances):
        """Testa ciclo de vida completo de uma instância real"""
        metrics = TestMetrics(test_name="Instance Lifecycle")
        instance_id = None

        try:
            # 1. Criar instância com retry (tenta várias ofertas se necessário)
            print(f"\n🚀 Criando instância REAL...")
            create_start = time.time()

            instance_id, offer = create_instance_with_retry(api, max_retries=3)

            if not instance_id:
                pytest.skip("Não foi possível criar instância após várias tentativas")

            cleanup_instances.append(instance_id)
            metrics.instance_id = instance_id
            metrics.gpu_name = offer.get("gpu_name") if offer else "N/A"
            metrics.gpu_cost_per_hour = offer.get("dph_total", 0) if offer else 0

            print(f"✅ Instância criada: {instance_id}")

            time.sleep(DELAY_AFTER_CREATE)

            # 2. Aguardar running
            print(f"\n⏳ Aguardando instância ficar running (timeout: {INSTANCE_READY_TIMEOUT}s)...")

            if not api.wait_for_status(instance_id, "running", INSTANCE_READY_TIMEOUT):
                pytest.fail("Timeout aguardando instância ficar running")

            metrics.time_to_running = time.time() - create_start
            print(f"✅ Instância running em {metrics.time_to_running:.1f}s")

            # 3. Verificar detalhes
            print("\n📋 Verificando detalhes...")
            details = api.call("GET", f"/api/v1/instances/{instance_id}")

            assert details and "error" not in details
            print(f"   GPU: {details.get('gpu_name')}")
            print(f"   Status: {details.get('status')}")
            print(f"   SSH: {details.get('ssh_host')}:{details.get('ssh_port')}")
            print(f"   IP: {details.get('public_ip', 'N/A')}")

            # 4. Pausar
            print("\n⏸️ Pausando instância...")
            pause_start = time.time()

            pause_result = api.call("POST", f"/api/v1/instances/{instance_id}/pause")
            print(f"   Resultado: {pause_result}")

            # Aguardar status paused
            time.sleep(10)
            status = api.call("GET", f"/api/v1/instances/{instance_id}")
            print(f"   Status após pause: {status.get('status')}")

            # 5. Resumir
            print("\n▶️ Resumindo instância...")

            resume_result = api.call("POST", f"/api/v1/instances/{instance_id}/resume")
            print(f"   Resultado: {resume_result}")

            # Aguardar voltar a running
            api.wait_for_status(instance_id, "running", 120)

            print(f"\n✅ Ciclo de vida completo testado com sucesso!")
            metrics.finish(success=True)

        except Exception as e:
            metrics.finish(success=False, error=str(e))
            raise

        finally:
            metrics_collector.add(metrics)

            # Deletar instância
            if instance_id:
                print(f"\n🗑️ Deletando instância {instance_id}...")
                delete_result = api.call("DELETE", f"/api/v1/instances/{instance_id}")
                print(f"   Resultado: {delete_result}")

                # Remover da lista de cleanup se já deletamos
                if instance_id in cleanup_instances:
                    cleanup_instances.remove(instance_id)


# ============================================================
# Jornada 2: Snapshot e Restore
# ============================================================

class TestRealSnapshotJourney:
    """
    Jornada REAL de snapshot:
    1. Criar instância
    2. Aguardar running
    3. Criar snapshot
    4. Verificar snapshot criado
    5. Deletar instância
    6. Medir tempos
    """

    def test_create_snapshot_real(self, api, cleanup_instances):
        """Testa criação de snapshot real"""
        metrics = TestMetrics(test_name="Snapshot Create")
        instance_id = None
        snapshot_id = None

        try:
            # 1. Criar instância com retry
            print(f"\n🚀 Criando instância para snapshot...")

            instance_id, offer = create_instance_with_retry(api, max_retries=3)

            if not instance_id:
                pytest.skip("Não foi possível criar instância após várias tentativas")

            cleanup_instances.append(instance_id)
            metrics.instance_id = instance_id
            metrics.gpu_name = offer.get("gpu_name") if offer else "N/A"
            metrics.gpu_cost_per_hour = offer.get("dph_total", 0) if offer else 0

            print(f"✅ Instância: {instance_id}")

            time.sleep(DELAY_AFTER_CREATE)

            # 2. Aguardar running
            print(f"\n⏳ Aguardando running...")
            if not api.wait_for_status(instance_id, "running", INSTANCE_READY_TIMEOUT):
                pytest.fail("Timeout aguardando running")

            # 3. Criar snapshot
            print("\n📸 Criando snapshot...")
            snapshot_start = time.time()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_result = api.call("POST", "/api/v1/snapshots", {
                "instance_id": instance_id,
                "name": f"test_snapshot_{timestamp}"
            })

            print(f"   Resultado: {snapshot_result}")

            if snapshot_result and "error" not in snapshot_result:
                snapshot_id = snapshot_result.get("id") or snapshot_result.get("snapshot_id")
                metrics.time_to_snapshot = time.time() - snapshot_start
                print(f"✅ Snapshot criado: {snapshot_id} em {metrics.time_to_snapshot:.1f}s")

            # 4. Listar snapshots
            print("\n📋 Listando snapshots...")
            snapshots = api.call("GET", "/api/v1/snapshots")
            print(f"   Snapshots: {snapshots}")

            metrics.finish(success=True)

        except Exception as e:
            metrics.finish(success=False, error=str(e))
            raise

        finally:
            metrics_collector.add(metrics)

            # Cleanup
            if instance_id:
                print(f"\n🗑️ Deletando instância {instance_id}...")
                api.call("DELETE", f"/api/v1/instances/{instance_id}")
                if instance_id in cleanup_instances:
                    cleanup_instances.remove(instance_id)

            if snapshot_id:
                print(f"🗑️ Deletando snapshot {snapshot_id}...")
                api.call("DELETE", f"/api/v1/snapshots/{snapshot_id}")


# ============================================================
# Jornada 3: Failover Status e Estratégias
# ============================================================

class TestRealFailoverJourney:
    """
    Jornada REAL de failover:
    1. Criar instância
    2. Verificar prontidão para failover
    3. Listar estratégias disponíveis
    4. Verificar configurações
    5. Simular failover (se disponível)
    """

    def test_failover_readiness_real(self, api, cleanup_instances):
        """Testa verificação de prontidão para failover"""
        metrics = TestMetrics(test_name="Failover Readiness")
        instance_id = None

        try:
            # 1. Criar instância com retry
            print(f"\n🚀 Criando instância para teste de failover...")

            instance_id, offer = create_instance_with_retry(api, max_retries=3)

            if not instance_id:
                pytest.skip("Não foi possível criar instância após várias tentativas")

            cleanup_instances.append(instance_id)
            metrics.instance_id = instance_id
            metrics.gpu_name = offer.get("gpu_name") if offer else "N/A"
            metrics.gpu_cost_per_hour = offer.get("dph_total", 0) if offer else 0

            print(f"✅ Instância: {instance_id}")

            time.sleep(DELAY_AFTER_CREATE)

            # 2. Aguardar running
            print(f"\n⏳ Aguardando running...")
            api.wait_for_status(instance_id, "running", INSTANCE_READY_TIMEOUT)

            # 3. Verificar prontidão
            print("\n🔍 Verificando prontidão para failover...")
            readiness = api.call("GET", f"/api/v1/failover/readiness/{instance_id}")
            print(f"   Prontidão: {readiness}")

            # 4. Listar estratégias
            print("\n📋 Listando estratégias de failover...")
            strategies = api.call("GET", "/api/v1/failover/strategies")
            print(f"   Estratégias: {strategies}")

            # 5. Verificar configurações globais
            print("\n⚙️ Verificando configurações de failover...")
            settings = api.call("GET", "/api/v1/failover/settings/global")
            print(f"   Config global: {settings}")

            # 6. Simular failover (dry-run)
            print("\n🧪 Simulando failover...")
            failover_start = time.time()

            simulate = api.call("POST", f"/api/v1/standby/failover/simulate/{instance_id}")
            print(f"   Simulação: {simulate}")

            if simulate and "error" not in simulate:
                metrics.time_to_failover = time.time() - failover_start

            metrics.finish(success=True)

        except Exception as e:
            metrics.finish(success=False, error=str(e))
            raise

        finally:
            metrics_collector.add(metrics)

            if instance_id:
                print(f"\n🗑️ Deletando instância {instance_id}...")
                api.call("DELETE", f"/api/v1/instances/{instance_id}")
                if instance_id in cleanup_instances:
                    cleanup_instances.remove(instance_id)


# ============================================================
# Jornada 4: Warm Pool
# ============================================================

class TestRealWarmPoolJourney:
    """Testa funcionalidades de GPU Warm Pool"""

    def test_warmpool_hosts_real(self, api):
        """Lista hosts com múltiplas GPUs disponíveis"""
        print("\n🔥 Listando hosts multi-GPU para warm pool...")

        result = api.call("GET", "/api/v1/warmpool/hosts")

        if result and "error" not in result:
            hosts = result.get("hosts", [])
            print(f"   {len(hosts)} hosts disponíveis")

            for host in hosts[:5]:
                print(f"   • Machine {host.get('machine_id')}: "
                      f"{host.get('num_gpus')} GPUs "
                      f"({host.get('gpu_name', 'N/A')})")

    def test_warmpool_status_real(self, api, cleanup_instances):
        """Testa status de warm pool para instância"""
        metrics = TestMetrics(test_name="Warm Pool Status")
        instance_id = None

        try:
            # Criar instância com retry
            print(f"\n🚀 Criando instância para warm pool test...")

            instance_id, offer = create_instance_with_retry(api, max_retries=3)

            if not instance_id:
                pytest.skip("Não foi possível criar instância após várias tentativas")

            cleanup_instances.append(instance_id)
            metrics.instance_id = instance_id
            metrics.gpu_name = offer.get("gpu_name") if offer else "N/A"
            metrics.gpu_cost_per_hour = offer.get("dph_total", 0) if offer else 0

            time.sleep(DELAY_AFTER_CREATE)

            # Verificar status warm pool
            print("\n🔥 Verificando warm pool status...")
            status = api.call("GET", f"/api/v1/warmpool/status/{instance_id}")
            print(f"   Status: {status}")

            metrics.finish(success=True)

        except Exception as e:
            metrics.finish(success=False, error=str(e))
            raise

        finally:
            metrics_collector.add(metrics)

            if instance_id:
                print(f"\n🗑️ Deletando {instance_id}...")
                api.call("DELETE", f"/api/v1/instances/{instance_id}")
                if instance_id in cleanup_instances:
                    cleanup_instances.remove(instance_id)


# ============================================================
# Jornada 5: CPU Standby
# ============================================================

class TestRealCPUStandbyJourney:
    """Testa funcionalidades de CPU Standby"""

    def test_standby_status_real(self, api):
        """Verifica status do sistema CPU Standby"""
        print("\n💻 Verificando status do CPU Standby...")

        result = api.call("GET", "/api/v1/standby/status")
        print(f"   Status: {result}")

        pricing = api.call("GET", "/api/v1/standby/pricing")
        print(f"   Pricing: {pricing}")

        associations = api.call("GET", "/api/v1/standby/associations")
        print(f"   Associações: {associations}")


# ============================================================
# Relatório Final
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def print_final_report(request):
    """Imprime relatório final após todos os testes"""
    yield

    print("\n\n")
    print(metrics_collector.generate_report())


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-x"  # Para no primeiro erro
    ])
