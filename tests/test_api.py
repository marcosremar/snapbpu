#!/usr/bin/env python3
"""
SnapGPU API Tests
Testes automatizados para todas as APIs do dashboard SnapGPU.

APIs Testadas:
- GET  /api/snapshots          - Lista snapshots com deduplicacao
- GET  /api/snapshot/<id>/folders - Lista pastas do snapshot
- POST /api/snapshot/<id>/tag  - Adiciona tag ao snapshot
- GET  /api/machines           - Lista maquinas ativas
- GET  /api/offers             - Lista ofertas vast.ai com filtros
- GET  /api/price-ranges       - Ranges de preco por perfil
- POST /api/create-instance    - Cria instancia vast.ai
- GET  /api/instance-status/<id> - Status da instancia
- DELETE /api/destroy-instance/<id> - Destroi instancia
- POST /api/multi-status       - Status de multiplas instancias
- POST /api/install-restic     - Instala restic na maquina
- POST /api/restore-snapshot   - Restaura snapshot na maquina
- POST /api/migrate            - Migra dados entre maquinas (Hot Start)
- POST /api/save-api-key       - Salva API key do usuario

Uso:
    python test_api.py                    # Testa contra servidor de producao
    python test_api.py --local            # Testa contra localhost:8765
    python test_api.py --url http://...   # Testa contra URL especifica
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuracao
BASE_URL = "http://vps-a84d392b.vps.ovh.net:8765"
SESSION_COOKIE = None

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_success(msg):
    print(f"{Colors.GREEN}[PASS]{Colors.END} {msg}")

def log_fail(msg):
    print(f"{Colors.RED}[FAIL]{Colors.END} {msg}")

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {msg}")


class APITester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results = {"passed": 0, "failed": 0, "skipped": 0}

    def login(self, username="marcoslogin", password="marcos123"):
        """Faz login e obtem cookie de sessao"""
        try:
            resp = self.session.post(
                f"{self.base_url}/login",
                data={"username": username, "password": password},
                allow_redirects=False
            )
            if resp.status_code in [200, 302]:
                log_success(f"Login OK (status={resp.status_code})")
                return True
            else:
                log_fail(f"Login falhou (status={resp.status_code})")
                return False
        except Exception as e:
            log_fail(f"Login erro: {e}")
            return False

    def test_endpoint(self, method, endpoint, expected_keys=None, data=None,
                      expected_status=200, description=None):
        """Testa um endpoint generico"""
        url = f"{self.base_url}{endpoint}"
        desc = description or f"{method} {endpoint}"

        try:
            if method == "GET":
                resp = self.session.get(url, timeout=30)
            elif method == "POST":
                resp = self.session.post(url, json=data, timeout=30)
            elif method == "DELETE":
                resp = self.session.delete(url, timeout=30)
            else:
                log_fail(f"{desc}: Metodo {method} nao suportado")
                self.results["failed"] += 1
                return None

            # Verifica status code
            if resp.status_code != expected_status:
                log_fail(f"{desc}: Status {resp.status_code} (esperado {expected_status})")
                self.results["failed"] += 1
                return None

            # Tenta parsear JSON
            try:
                result = resp.json()
            except:
                if expected_keys:
                    log_fail(f"{desc}: Resposta nao e JSON valido")
                    self.results["failed"] += 1
                    return None
                result = resp.text

            # Verifica chaves esperadas
            if expected_keys:
                missing = [k for k in expected_keys if k not in result]
                if missing:
                    log_fail(f"{desc}: Chaves faltando: {missing}")
                    self.results["failed"] += 1
                    return None

            log_success(f"{desc}")
            self.results["passed"] += 1
            return result

        except requests.exceptions.Timeout:
            log_fail(f"{desc}: Timeout")
            self.results["failed"] += 1
            return None
        except Exception as e:
            log_fail(f"{desc}: {e}")
            self.results["failed"] += 1
            return None

    # ==================== TESTES DAS APIs ====================

    def test_snapshots(self):
        """GET /api/snapshots - Lista snapshots com deduplicacao"""
        result = self.test_endpoint(
            "GET", "/api/snapshots",
            expected_keys=["snapshots"],
            description="Lista snapshots"
        )
        if result:
            log_info(f"  -> {len(result.get('snapshots', []))} snapshots encontrados")
            if result.get('snapshots'):
                # Verifica estrutura do snapshot
                snap = result['snapshots'][0]
                required = ['id', 'time', 'hostname']
                missing = [k for k in required if k not in snap]
                if missing:
                    log_warn(f"  -> Snapshot sem campos: {missing}")
                else:
                    log_info(f"  -> Primeiro: {snap['id'][:8]}... ({snap.get('hostname', '?')})")
        return result

    def test_snapshot_folders(self, snapshot_id=None):
        """GET /api/snapshot/<id>/folders - Lista pastas do snapshot"""
        if not snapshot_id:
            # Pega o primeiro snapshot disponivel
            snaps = self.test_endpoint("GET", "/api/snapshots")
            if not snaps or not isinstance(snaps, dict) or not snaps.get('snapshots'):
                log_warn("Sem snapshots para testar folders")
                self.results["skipped"] += 1
                return None
            snapshot_id = snaps['snapshots'][0]['id']

        result = self.test_endpoint(
            "GET", f"/api/snapshot/{snapshot_id}/folders",
            expected_keys=["folders"],
            description=f"Lista pastas do snapshot {snapshot_id[:8]}..."
        )
        if result:
            folders = result.get('folders', [])
            log_info(f"  -> {len(folders)} pastas encontradas")
            for f in folders[:3]:
                log_info(f"     - {f.get('name', '?')}: {f.get('size_human', '?')}")
        return result

    def test_machines(self):
        """GET /api/machines - Lista maquinas ativas do usuario"""
        result = self.test_endpoint(
            "GET", "/api/machines",
            expected_keys=["machines"],
            description="Lista maquinas ativas"
        )
        if result:
            machines = result.get('machines', [])
            log_info(f"  -> {len(machines)} maquinas ativas")
            for m in machines[:3]:
                log_info(f"     - ID {m.get('id')}: {m.get('status', '?')}")
        return result

    def test_offers(self):
        """GET /api/offers - Lista ofertas vast.ai"""
        result = self.test_endpoint(
            "GET", "/api/offers",
            expected_keys=["offers"],
            description="Lista ofertas vast.ai"
        )
        if result:
            offers = result.get('offers', [])
            log_info(f"  -> {len(offers)} ofertas disponiveis")
            if offers:
                o = offers[0]
                log_info(f"     - GPU: {o.get('gpu_name', '?')}, ${o.get('dph_total', '?')}/h")
        return result

    def test_offers_with_filters(self):
        """GET /api/offers com filtros"""
        # Teste com filtros de velocidade
        filters = {
            "min_download": 2000,
            "max_download": 4000,
            "verified": "true"
        }
        result = self.test_endpoint(
            "GET", f"/api/offers?{'&'.join(f'{k}={v}' for k,v in filters.items())}",
            expected_keys=["offers"],
            description="Lista ofertas com filtros (2000-4000 Mbps)"
        )
        if result:
            log_info(f"  -> {len(result.get('offers', []))} ofertas filtradas")
        return result

    def test_price_ranges(self):
        """GET /api/price-ranges - Ranges de preco por perfil"""
        result = self.test_endpoint(
            "GET", "/api/price-ranges",
            description="Ranges de preco por perfil"
        )
        if result:
            for profile in ['slow', 'economy', 'balanced', 'performance']:
                if profile in result:
                    p = result[profile]
                    log_info(f"  -> {profile}: ${p.get('min', 0):.2f}-${p.get('max', 0):.2f}/h ({p.get('count', 0)} ofertas)")
        return result

    def test_multi_status(self):
        """POST /api/multi-status - Status de multiplas instancias"""
        # Teste com IDs inexistentes (deve retornar lista vazia, nao erro)
        result = self.test_endpoint(
            "POST", "/api/multi-status",
            data={"instance_ids": [99999999]},
            expected_keys=["instances"],
            description="Multi-status (IDs inexistentes)"
        )
        if result:
            log_info(f"  -> {len(result.get('instances', []))} instancias encontradas")
        return result

    def test_save_api_key(self):
        """POST /api/save-api-key - Salva API key (teste sem alterar)"""
        # Nao vamos alterar a API key real, apenas testar o endpoint
        result = self.test_endpoint(
            "POST", "/api/save-api-key",
            data={"api_key": ""},  # String vazia para nao alterar
            expected_keys=["success"],
            description="Salvar API key (vazia)"
        )
        return result

    # ==================== TESTES SIMULADOS ====================
    # Estes testes verificam a estrutura das APIs sem criar recursos reais

    def test_create_instance_validation(self):
        """POST /api/create-instance - Testa validacao (sem offer_id)"""
        result = self.test_endpoint(
            "POST", "/api/create-instance",
            data={},  # Sem offer_id
            expected_status=200,  # Retorna JSON com erro
            description="Criar instancia (sem offer_id)"
        )
        if result and isinstance(result, dict) and not result.get('success'):
            log_info(f"  -> Validacao OK: {result.get('error', 'sem offer_id')}")
        return result

    def test_install_restic_validation(self):
        """POST /api/install-restic - Testa validacao"""
        result = self.test_endpoint(
            "POST", "/api/install-restic",
            data={"ssh_host": "", "ssh_port": ""},
            expected_status=200,
            description="Install restic (dados invalidos)"
        )
        return result

    def test_restore_validation(self):
        """POST /api/restore-snapshot - Testa validacao"""
        result = self.test_endpoint(
            "POST", "/api/restore-snapshot",
            data={"snapshot_id": "latest", "ssh_host": "", "ssh_port": ""},
            expected_status=200,
            description="Restore snapshot (dados invalidos)"
        )
        return result

    def test_migrate_validation(self):
        """POST /api/migrate - Testa validacao (Hot Start)"""
        result = self.test_endpoint(
            "POST", "/api/migrate",
            data={},  # Sem parametros
            expected_status=200,
            description="Migrate (Hot Start) - validacao"
        )
        if result and isinstance(result, dict) and not result.get('success'):
            log_info(f"  -> Validacao OK: {result.get('error', 'parametros faltando')}")
        return result

    def test_destroy_nonexistent(self):
        """DELETE /api/destroy-instance/<id> - Testa com ID inexistente"""
        result = self.test_endpoint(
            "DELETE", "/api/destroy-instance/99999999",
            expected_status=200,
            description="Destroy instancia (ID inexistente)"
        )
        return result

    def test_snapshot_tag(self):
        """POST /api/snapshot/<id>/tag - Testa adicionar tag"""
        # Pega o primeiro snapshot
        snaps = self.test_endpoint("GET", "/api/snapshots")
        if not snaps or not isinstance(snaps, dict) or not snaps.get('snapshots'):
            log_warn("Sem snapshots para testar tag")
            self.results["skipped"] += 1
            return None

        snapshot_id = snaps['snapshots'][0]['id']
        result = self.test_endpoint(
            "POST", f"/api/snapshot/{snapshot_id}/tag",
            data={"tag": f"test-{int(time.time())}"},
            description=f"Tag snapshot {snapshot_id[:8]}..."
        )
        return result

    def test_agent_settings_get(self):
        """GET /api/settings/agent - Testa leitura das configuracoes do agente"""
        result = self.test_endpoint(
            "GET", "/api/settings/agent",
            description="Agent Settings (GET)"
        )
        if result and isinstance(result, dict):
            if 'sync_interval' in result and 'keep_last' in result:
                log_info(f"  -> sync_interval: {result['sync_interval']}s, keep_last: {result['keep_last']}")
            else:
                log_warn("  -> Campos esperados nao encontrados")
        return result

    def test_agent_settings_put(self):
        """PUT /api/settings/agent - Testa atualizacao das configuracoes do agente"""
        # Primeiro, salvar as configuracoes atuais
        current = self.test_endpoint("GET", "/api/settings/agent")
        original_interval = current.get('sync_interval', 30) if current else 30
        original_keep = current.get('keep_last', 10) if current else 10

        # Atualizar para valores de teste
        result = self.test_endpoint(
            "PUT", "/api/settings/agent",
            data={"sync_interval": 60, "keep_last": 20},
            description="Agent Settings (PUT)"
        )
        if result and result.get('success'):
            log_info(f"  -> Salvo: sync_interval=60, keep_last=20")

        # Restaurar valores originais
        self.test_endpoint(
            "PUT", "/api/settings/agent",
            data={"sync_interval": original_interval, "keep_last": original_keep},
            expected_status=200,
            description="Restaurar configuracoes originais"
        )
        return result

    def test_agent_settings_validation(self):
        """PUT /api/settings/agent - Testa validacao de parametros"""
        # Testar intervalo muito baixo
        result = self.test_endpoint(
            "PUT", "/api/settings/agent",
            data={"sync_interval": 5, "keep_last": 10},
            expected_status=400,
            description="Agent Settings - validacao intervalo minimo"
        )
        if result and 'error' in result:
            log_info(f"  -> Validacao OK: {result['error']}")

        # Testar keep_last muito baixo
        result2 = self.test_endpoint(
            "PUT", "/api/settings/agent",
            data={"sync_interval": 30, "keep_last": 0},
            expected_status=400,
            description="Agent Settings - validacao keep_last minimo"
        )
        if result2 and 'error' in result2:
            log_info(f"  -> Validacao OK: {result2['error']}")

        return result

    # ==================== EXECUCAO ====================

    def run_all_tests(self):
        """Executa todos os testes"""
        print(f"\n{'='*60}")
        print(f"SnapGPU API Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base URL: {self.base_url}")
        print(f"{'='*60}\n")

        # Login primeiro
        print("[1/14] Autenticacao")
        if not self.login():
            log_fail("Nao foi possivel fazer login. Abortando testes.")
            return self.results

        # Testes de leitura (GET)
        print("\n[2/14] Snapshots")
        self.test_snapshots()

        print("\n[3/14] Folders do Snapshot")
        self.test_snapshot_folders()

        print("\n[4/14] Maquinas Ativas")
        self.test_machines()

        print("\n[5/14] Ofertas Vast.ai")
        self.test_offers()

        print("\n[6/14] Ofertas com Filtros")
        self.test_offers_with_filters()

        print("\n[7/14] Price Ranges")
        self.test_price_ranges()

        # Testes de validacao (sem criar recursos)
        print("\n[8/14] Multi-Status")
        self.test_multi_status()

        print("\n[9/14] Validacao Create Instance")
        self.test_create_instance_validation()

        print("\n[10/14] Validacao Install Restic")
        self.test_install_restic_validation()

        print("\n[11/14] Validacao Restore")
        self.test_restore_validation()

        print("\n[12/14] Validacao Migrate (Hot Start)")
        self.test_migrate_validation()

        print("\n[13/14] Destroy Inexistente")
        self.test_destroy_nonexistent()

        print("\n[14/17] Save API Key")
        self.test_save_api_key()

        print("\n[15/17] Agent Settings GET")
        self.test_agent_settings_get()

        print("\n[16/17] Agent Settings PUT")
        self.test_agent_settings_put()

        print("\n[17/17] Agent Settings Validation")
        self.test_agent_settings_validation()

        # Resumo
        print(f"\n{'='*60}")
        print("RESUMO DOS TESTES")
        print(f"{'='*60}")
        total = self.results["passed"] + self.results["failed"] + self.results["skipped"]
        print(f"{Colors.GREEN}Passou:  {self.results['passed']}{Colors.END}")
        print(f"{Colors.RED}Falhou:  {self.results['failed']}{Colors.END}")
        print(f"{Colors.YELLOW}Pulados: {self.results['skipped']}{Colors.END}")
        print(f"Total:   {total}")

        if self.results["failed"] == 0:
            print(f"\n{Colors.GREEN}Todos os testes passaram!{Colors.END}")
        else:
            print(f"\n{Colors.RED}Alguns testes falharam.{Colors.END}")

        return self.results


def main():
    global BASE_URL

    # Processa argumentos
    if "--local" in sys.argv:
        BASE_URL = "http://localhost:8765"
    elif "--url" in sys.argv:
        idx = sys.argv.index("--url")
        if idx + 1 < len(sys.argv):
            BASE_URL = sys.argv[idx + 1]

    # Executa testes
    tester = APITester(BASE_URL)
    results = tester.run_all_tests()

    # Exit code baseado nos resultados
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
