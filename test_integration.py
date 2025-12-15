#!/usr/bin/env python3
"""
SnapGPU Integration Tests - Testes de Integracao Completos
Testes que realmente criam e destroem recursos no vast.ai

ATENCAO: Estes testes CUSTAM DINHEIRO! Use com moderacao.

Fluxo testado:
1. Login
2. Buscar oferta mais barata
3. Criar instancia
4. Aguardar instancia ficar pronta
5. Verificar status
6. Destruir instancia

Uso:
    python test_integration.py              # Executa teste completo
    python test_integration.py --dry-run    # Apenas simula (nao cria maquina)
    python test_integration.py --profile slow  # Usa perfil especifico
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuracao
BASE_URL = "http://vps-a84d392b.vps.ovh.net:8765"
USERNAME = "marcoslogin"
PASSWORD = "marcos123"

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'

def log_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")

def log_fail(msg):
    print(f"{Colors.RED}[FAIL]{Colors.END} {msg}")

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {msg}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {msg}")

def log_step(step, msg):
    print(f"\n{Colors.CYAN}[STEP {step}]{Colors.END} {Colors.BOLD}{msg}{Colors.END}")

def log_money(msg):
    print(f"{Colors.MAGENTA}[$$$]{Colors.END} {msg}")


class IntegrationTester:
    def __init__(self, base_url, dry_run=False):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.dry_run = dry_run
        self.created_instance_id = None
        self.total_cost = 0.0

    def login(self):
        """Faz login e obtem cookie de sessao"""
        try:
            resp = self.session.post(
                f"{self.base_url}/login",
                data={"username": USERNAME, "password": PASSWORD},
                allow_redirects=False
            )
            if resp.status_code in [200, 302]:
                log_success(f"Login OK como '{USERNAME}'")
                return True
            else:
                log_fail(f"Login falhou (status={resp.status_code})")
                return False
        except Exception as e:
            log_fail(f"Login erro: {e}")
            return False

    def get_cheapest_offer(self, profile="slow"):
        """Busca a oferta mais barata disponivel"""
        try:
            # Nao passar filtros - a API ja retorna ofertas filtradas
            resp = self.session.get(
                f"{self.base_url}/api/offers",
                timeout=30
            )
            if resp.status_code != 200:
                log_fail(f"Erro ao buscar ofertas: {resp.status_code}")
                return None

            data = resp.json()
            offers = data.get("offers", [])

            if not offers:
                log_fail("Nenhuma oferta disponivel")
                log_warn("Verifique se a API Key do vast.ai esta configurada no dashboard!")
                log_info("Acesse http://vps-a84d392b.vps.ovh.net:8765 e configure sua API Key")
                return None

            # Ordena por preco (dph_total)
            offers_sorted = sorted(offers, key=lambda x: float(x.get("dph_total", 999)))
            cheapest = offers_sorted[0]

            log_success(f"Encontradas {len(offers)} ofertas")
            log_info(f"Mais barata: {cheapest.get('gpu_name', '?')} @ ${cheapest.get('dph_total', 0):.4f}/h")
            log_info(f"  ID: {cheapest.get('id')}")
            log_info(f"  Download: {cheapest.get('inet_down', 0):.0f} Mbps")
            log_info(f"  VRAM: {cheapest.get('gpu_ram', 0)/1024:.0f} GB")

            return cheapest
        except Exception as e:
            log_fail(f"Erro ao buscar ofertas: {e}")
            return None

    def create_instance(self, offer_id, snapshot_id="latest"):
        """Cria uma instancia vast.ai"""
        if self.dry_run:
            log_warn("DRY RUN - Nao criando instancia real")
            return {"success": True, "instance_id": "DRY_RUN_12345", "dry_run": True}

        try:
            resp = self.session.post(
                f"{self.base_url}/api/create-instance",
                json={
                    "offer_id": offer_id,
                    "snapshot_id": snapshot_id,
                    "image": "pytorch/pytorch:2.0.1-cuda11.7-cudnn8-devel",
                    "disk": 50
                },
                timeout=60
            )

            data = resp.json()

            if data.get("success"):
                instance_id = data.get("instance_id")
                self.created_instance_id = instance_id
                log_success(f"Instancia criada: ID {instance_id}")
                return data
            else:
                log_fail(f"Falha ao criar instancia: {data.get('error', 'Erro desconhecido')}")
                return None
        except Exception as e:
            log_fail(f"Erro ao criar instancia: {e}")
            return None

    def wait_for_instance(self, instance_id, timeout=300, interval=10):
        """Aguarda instancia ficar pronta"""
        if self.dry_run:
            log_warn("DRY RUN - Simulando espera...")
            time.sleep(2)
            return {"status": "running", "ssh_host": "dry.run.host", "ssh_port": 22}

        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            try:
                resp = self.session.get(
                    f"{self.base_url}/api/instance-status/{instance_id}",
                    timeout=30
                )

                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "unknown")

                    if status != last_status:
                        elapsed = int(time.time() - start_time)
                        log_info(f"Status: {status} ({elapsed}s)")
                        last_status = status

                    if status == "running":
                        ssh_host = data.get("ssh_host", "")
                        ssh_port = data.get("ssh_port", "")
                        log_success(f"Instancia pronta! SSH: {ssh_host}:{ssh_port}")
                        return data
                    elif status in ["exited", "error", "destroyed"]:
                        log_fail(f"Instancia falhou com status: {status}")
                        return None

                time.sleep(interval)
            except Exception as e:
                log_warn(f"Erro ao verificar status: {e}")
                time.sleep(interval)

        log_fail(f"Timeout ({timeout}s) aguardando instancia")
        return None

    def destroy_instance(self, instance_id):
        """Destroi uma instancia"""
        if self.dry_run:
            log_warn("DRY RUN - Nao destruindo instancia")
            return True

        try:
            resp = self.session.delete(
                f"{self.base_url}/api/destroy-instance/{instance_id}",
                timeout=30
            )

            data = resp.json()

            if data.get("success"):
                log_success(f"Instancia {instance_id} destruida")
                return True
            else:
                log_fail(f"Falha ao destruir: {data.get('error', 'Erro desconhecido')}")
                return False
        except Exception as e:
            log_fail(f"Erro ao destruir instancia: {e}")
            return False

    def get_machines(self):
        """Lista maquinas ativas"""
        try:
            resp = self.session.get(f"{self.base_url}/api/machines", timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                machines = data.get("machines", [])
                log_success(f"{len(machines)} maquinas ativas")
                for m in machines:
                    log_info(f"  ID {m.get('id')}: {m.get('actual_status', '?')} - {m.get('gpu_name', '?')}")
                return machines
            return []
        except Exception as e:
            log_fail(f"Erro ao listar maquinas: {e}")
            return []

    def run_full_integration_test(self, profile="slow"):
        """Executa teste de integracao completo"""
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}SnapGPU Integration Test{Colors.END}")
        print(f"{'='*70}")
        print(f"URL: {self.base_url}")
        print(f"Profile: {profile}")
        print(f"Dry Run: {self.dry_run}")
        print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")

        start_time = time.time()
        success = True

        try:
            # Step 1: Login
            log_step(1, "Autenticacao")
            if not self.login():
                return False

            # Step 2: Listar maquinas existentes
            log_step(2, "Verificando maquinas existentes")
            existing_machines = self.get_machines()

            # Step 3: Buscar oferta mais barata
            log_step(3, "Buscando oferta mais barata")
            offer = self.get_cheapest_offer(profile=profile)
            if not offer:
                return False

            price_per_hour = float(offer.get("dph_total", 0))
            log_money(f"Custo estimado: ${price_per_hour:.4f}/hora")

            # Step 4: Criar instancia
            log_step(4, "Criando instancia")
            result = self.create_instance(offer["id"])
            if not result:
                return False

            instance_id = result.get("instance_id")

            # Step 5: Aguardar instancia ficar pronta
            log_step(5, "Aguardando instancia ficar pronta")
            instance_info = self.wait_for_instance(instance_id, timeout=300)

            if instance_info:
                elapsed = time.time() - start_time
                log_success(f"Instancia pronta em {elapsed:.0f}s")

                # Calcular custo aproximado
                hours_used = elapsed / 3600
                cost = hours_used * price_per_hour
                self.total_cost += cost
                log_money(f"Custo desta sessao: ${cost:.4f}")
            else:
                success = False

            # Step 6: Verificar status
            log_step(6, "Verificando status da instancia")
            if not self.dry_run and instance_id:
                resp = self.session.get(f"{self.base_url}/api/instance-status/{instance_id}", timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    log_info(f"Status final: {data.get('status', '?')}")
                    if data.get("ssh_host"):
                        log_info(f"SSH: ssh -p {data.get('ssh_port')} root@{data.get('ssh_host')}")

            # Step 7: Destruir instancia
            log_step(7, "Destruindo instancia")
            if instance_id and not self.dry_run:
                if not self.destroy_instance(instance_id):
                    success = False

            # Step 8: Verificar que foi destruida
            log_step(8, "Verificando destruicao")
            time.sleep(3)
            final_machines = self.get_machines()

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrompido pelo usuario!{Colors.END}")
            if self.created_instance_id and not self.dry_run:
                log_warn(f"Limpando instancia {self.created_instance_id}...")
                self.destroy_instance(self.created_instance_id)
            success = False

        except Exception as e:
            log_fail(f"Erro inesperado: {e}")
            if self.created_instance_id and not self.dry_run:
                log_warn(f"Limpando instancia {self.created_instance_id}...")
                self.destroy_instance(self.created_instance_id)
            success = False

        # Resumo
        total_time = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}RESUMO{Colors.END}")
        print(f"{'='*70}")
        print(f"Tempo total: {total_time:.0f}s")
        print(f"Custo total: ${self.total_cost:.4f}")

        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}TESTE PASSOU!{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}TESTE FALHOU!{Colors.END}")

        return success


def main():
    global BASE_URL

    dry_run = "--dry-run" in sys.argv
    profile = "slow"

    # Parse argumentos
    if "--profile" in sys.argv:
        idx = sys.argv.index("--profile")
        if idx + 1 < len(sys.argv):
            profile = sys.argv[idx + 1]

    if "--url" in sys.argv:
        idx = sys.argv.index("--url")
        if idx + 1 < len(sys.argv):
            BASE_URL = sys.argv[idx + 1]

    if "--local" in sys.argv:
        BASE_URL = "http://localhost:8765"

    # Confirmacao antes de gastar dinheiro
    if not dry_run:
        print(f"\n{Colors.RED}{Colors.BOLD}ATENCAO: Este teste VAI CUSTAR DINHEIRO!{Colors.END}")
        print("Uma instancia vast.ai sera criada e destruida.")
        print("Use --dry-run para testar sem criar recursos.\n")

        confirm = input("Deseja continuar? (s/N): ").strip().lower()
        if confirm != 's':
            print("Cancelado.")
            sys.exit(0)

    tester = IntegrationTester(BASE_URL, dry_run=dry_run)
    success = tester.run_full_integration_test(profile=profile)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
