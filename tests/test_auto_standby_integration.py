#!/usr/bin/env python3
"""
Teste de Integração: Auto-Standby
Verifica se CPU standby é criada/destruída automaticamente com GPU

FLUXO TESTADO:
1. Configurar auto-standby
2. Criar GPU → verificar se CPU standby foi criada
3. Verificar sync funcionando
4. Destruir GPU → verificar se CPU standby foi destruída
"""
import os
import sys
import json
import time
import logging

sys.path.insert(0, '/home/ubuntu/dumont-cloud')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def check(condition: bool, msg: str) -> bool:
    """Helper para verificar condição e imprimir resultado"""
    if condition:
        print(f"{GREEN}✅ {msg}{RESET}")
        return True
    else:
        print(f"{RED}❌ {msg}{RESET}")
        return False


def info(msg: str):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def warn(msg: str):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def main():
    print("\n" + "=" * 60)
    print("🧪 TESTE DE INTEGRAÇÃO: AUTO-STANDBY")
    print("=" * 60 + "\n")

    results = []
    gpu_instance_id = None
    cpu_instance_name = None

    try:
        # ============================================================
        # SETUP: Carregar credenciais
        # ============================================================
        info("Carregando credenciais...")

        # GCP
        gcp_creds_path = 'credentials/gcp-service-account.json'
        if not os.path.exists(gcp_creds_path):
            print(f"{RED}❌ Arquivo {gcp_creds_path} não encontrado{RESET}")
            return False

        with open(gcp_creds_path) as f:
            gcp_credentials = json.load(f)

        # Vast.ai
        vast_api_key = os.environ.get('VAST_API_KEY', '')
        if not vast_api_key:
            # Tentar carregar do config.json do projeto
            config_paths = [
                '/home/ubuntu/dumont-cloud/config.json',
                os.path.expanduser('~/.dumont/config.json'),
            ]
            for config_path in config_paths:
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        config = json.load(f)
                        users = config.get('users', {})
                        for email, user in users.items():
                            if user.get('vast_api_key'):
                                vast_api_key = user['vast_api_key']
                                info(f"API key carregada de {config_path}")
                                break
                    if vast_api_key:
                        break

        if not vast_api_key:
            print(f"{RED}❌ VAST_API_KEY não configurada{RESET}")
            return False

        results.append(check(True, "Credenciais carregadas"))

        # ============================================================
        # TESTE 1: Configurar StandbyManager
        # ============================================================
        print(f"\n{BLUE}--- TESTE 1: Configurar StandbyManager ---{RESET}")

        from src.services.standby_manager import get_standby_manager, StandbyManager

        # Resetar singleton para teste limpo
        StandbyManager._instance = None

        manager = get_standby_manager()
        manager.configure(
            gcp_credentials=gcp_credentials,
            vast_api_key=vast_api_key,
            auto_standby_enabled=True,
            config={
                'gcp_zone': 'europe-west1-b',
                'gcp_machine_type': 'e2-medium',
                'gcp_disk_size': 50,  # Menor para teste
                'gcp_spot': True,
                'sync_interval': 30,
                'auto_failover': True,
            }
        )

        results.append(check(manager.is_configured(), "StandbyManager configurado"))
        results.append(check(manager.is_auto_standby_enabled(), "Auto-standby habilitado"))

        # ============================================================
        # TESTE 2: Criar GPU e verificar se CPU é criada automaticamente
        # ============================================================
        print(f"\n{BLUE}--- TESTE 2: Criar GPU (com auto-standby) ---{RESET}")

        from src.infrastructure.providers.vast_provider import VastProvider

        vast = VastProvider(api_key=vast_api_key)

        # Buscar oferta barata
        info("Buscando oferta de GPU barata...")
        offers = vast.search_offers(
            max_price=0.15,
            min_gpu_ram=4,
            min_disk=20,
            limit=10
        )

        if not offers:
            warn("Nenhuma oferta encontrada com preço <= $0.15/h")
            offers = vast.search_offers(max_price=0.30, min_gpu_ram=4, limit=5)

        results.append(check(len(offers) > 0, f"Ofertas encontradas: {len(offers)}"))

        if not offers:
            print(f"{RED}❌ Não foi possível encontrar ofertas{RESET}")
            return False

        # Criar instância
        offer = offers[0]
        info(f"Criando GPU: {offer.gpu_name} @ ${offer.dph_total:.3f}/h")

        instance = vast.create_instance(
            offer_id=offer.id,
            image="pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
            disk_size=20,
            label="auto-standby-test"
        )

        gpu_instance_id = instance.id
        results.append(check(gpu_instance_id is not None, f"GPU criada: ID {gpu_instance_id}"))

        # Simular callback de criação (normalmente feito pelo endpoint)
        info("Disparando callback on_gpu_created...")
        standby_result = manager.on_gpu_created(
            gpu_instance_id=gpu_instance_id,
            label="auto-standby-test"
        )

        if standby_result:
            cpu_instance_name = standby_result.get('cpu_standby', {}).get('name')
            results.append(check(True, f"CPU standby criada: {cpu_instance_name}"))
        else:
            results.append(check(False, "CPU standby criada"))

        # Verificar associação
        association = manager.get_association(gpu_instance_id)
        results.append(check(association is not None, "Associação GPU→CPU registrada"))

        if association:
            info(f"  GPU: {gpu_instance_id}")
            info(f"  CPU: {association['cpu_standby']['name']}")
            info(f"  IP:  {association['cpu_standby']['ip']}")

        # ============================================================
        # TESTE 3: Verificar CPU standby está acessível
        # ============================================================
        print(f"\n{BLUE}--- TESTE 3: Verificar CPU standby ---{RESET}")

        if association:
            cpu_ip = association['cpu_standby']['ip']
            info(f"Aguardando CPU standby ficar pronta ({cpu_ip})...")

            # Aguardar SSH ficar disponível
            import subprocess

            ssh_ready = False
            for attempt in range(12):  # 2 minutos
                result = subprocess.run(
                    ['ssh', '-o', 'StrictHostKeyChecking=no',
                     '-o', 'ConnectTimeout=5',
                     '-o', 'BatchMode=yes',
                     f'root@{cpu_ip}', 'echo ok'],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    ssh_ready = True
                    break
                info(f"  Tentativa {attempt + 1}/12...")
                time.sleep(10)

            results.append(check(ssh_ready, f"SSH para CPU standby ({cpu_ip})"))

        # ============================================================
        # TESTE 4: Listar associações
        # ============================================================
        print(f"\n{BLUE}--- TESTE 4: Listar associações ---{RESET}")

        associations = manager.list_associations()
        results.append(check(gpu_instance_id in associations, "GPU está nas associações"))
        info(f"Total de associações: {len(associations)}")

        # ============================================================
        # TESTE 5: Destruir GPU e verificar se CPU é destruída
        # ============================================================
        print(f"\n{BLUE}--- TESTE 5: Destruir GPU (com auto-cleanup) ---{RESET}")

        info(f"Destruindo GPU {gpu_instance_id}...")
        destroy_success = vast.destroy_instance(gpu_instance_id)
        results.append(check(destroy_success, f"GPU {gpu_instance_id} destruída"))

        # Simular callback de destruição
        info("Disparando callback on_gpu_destroyed...")
        cleanup_success = manager.on_gpu_destroyed(gpu_instance_id)
        results.append(check(cleanup_success, "CPU standby destruída"))

        # Verificar que associação foi removida
        association_after = manager.get_association(gpu_instance_id)
        results.append(check(association_after is None, "Associação removida"))

        # Marcar GPU como None para não tentar limpar novamente
        gpu_instance_id = None

        # ============================================================
        # TESTE 6: Verificar que CPU não existe mais no GCP
        # ============================================================
        print(f"\n{BLUE}--- TESTE 6: Verificar limpeza no GCP ---{RESET}")

        from src.infrastructure.providers.gcp_provider import GCPProvider
        gcp = GCPProvider(json.dumps(gcp_credentials))

        # Aguardar um pouco para a operação de delete completar
        time.sleep(5)

        instances = gcp.list_instances()
        cpu_still_exists = any(
            cpu_instance_name and cpu_instance_name in inst.get('name', '')
            for inst in instances
        )
        results.append(check(not cpu_still_exists, "CPU não existe mais no GCP"))

        # ============================================================
        # RESUMO
        # ============================================================
        print("\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES")
        print("=" * 60)

        passed = sum(results)
        total = len(results)
        all_passed = passed == total

        for i, result in enumerate(results, 1):
            status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            print(f"  Teste {i}: [{status}]")

        print(f"\n  Total: {passed}/{total}")

        if all_passed:
            print(f"\n{GREEN}🎉 TODOS OS TESTES PASSARAM!{RESET}")
            print(f"{GREEN}   Auto-standby está funcionando corretamente.{RESET}")
        else:
            print(f"\n{RED}⚠️  Alguns testes falharam.{RESET}")

        return all_passed

    except Exception as e:
        print(f"\n{RED}❌ ERRO: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # ============================================================
        # CLEANUP
        # ============================================================
        print(f"\n{BLUE}--- CLEANUP ---{RESET}")

        # Destruir GPU se ainda existir
        if gpu_instance_id:
            try:
                info(f"Limpando GPU {gpu_instance_id}...")
                vast = VastProvider(api_key=vast_api_key)
                vast.destroy_instance(gpu_instance_id)
            except Exception as e:
                warn(f"Erro ao limpar GPU: {e}")

        # Limpar associações órfãs
        try:
            manager = get_standby_manager()
            for gid in list(manager._associations.keys()):
                info(f"Limpando associação {gid}...")
                manager.on_gpu_destroyed(gid)
        except:
            pass

        # Limpar VMs GCP órfãs
        try:
            from src.infrastructure.providers.gcp_provider import GCPProvider
            with open('credentials/gcp-service-account.json') as f:
                gcp_creds = json.load(f)
            gcp = GCPProvider(json.dumps(gcp_creds))
            instances = gcp.list_instances()
            for inst in instances:
                name = inst.get('name', '')
                zone = inst.get('zone', '')
                if 'test' in name.lower() or 'standby' in name.lower():
                    info(f"Limpando GCP VM: {name}")
                    gcp.delete_instance(name, zone)
        except Exception as e:
            warn(f"Erro ao limpar GCP: {e}")

        print(f"\n{GREEN}✓ Cleanup concluído{RESET}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
