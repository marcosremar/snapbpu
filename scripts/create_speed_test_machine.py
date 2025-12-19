#!/usr/bin/env python3
"""
Cria uma nova máquina para teste de velocidade do snapshot
"""
import json
import os
import requests
import time
import subprocess
import sys

def create_test_machine():
    # Load config
    config_file = "/home/ubuntu/dumont-cloud/config.json"
    if not os.path.exists(config_file):
        print("❌ Config não encontrado")
        return None
    
    with open(config_file) as f:
        config = json.load(f)
    
    # Get API key
    users = config.get("users", {})
    api_key = None
    for email, user_data in users.items():
        api_key = user_data.get("vast_api_key")
        if api_key:
            break
    
    if not api_key:
        print("❌ API Key não encontrada")
        return None
    
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print("="*70)
    print("CRIANDO MÁQUINA PARA TESTE DE SNAPSHOT")
    print("="*70)
    
    # Buscar ofertas com alta banda e baixo custo
    print("\n📡 Buscando ofertas com internet rápida...")
    resp = requests.get(
        "https://console.vast.ai/api/v0/bundles",
        params={
            "q": json.dumps({
                "verified": {"eq": True},
                "rentable": {"eq": True},
                "type": "on-demand",
                "inet_down": {"gte": 500},  # >= 500 Mbps download
                "inet_up": {"gte": 500},    # >= 500 Mbps upload
                "disk_space": {"gte": 50},  # >= 50GB disk
                "order": [["dph_total", "asc"]],
                "limit": 20
            })
        },
        headers=headers
    )
    
    if not resp.ok:
        print(f"❌ Erro ao buscar ofertas: {resp.status_code}")
        print(resp.text[:500])
        return None
    
    offers = resp.json().get("offers", [])
    
    if not offers:
        print("❌ Nenhuma oferta disponível com os requisitos")
        return None
    
    # Mostrar top 5
    print(f"\n✓ Encontradas {len(offers)} ofertas. Top 5:\n")
    for i, o in enumerate(offers[:5]):
        print(f"#{i+1}: ID={o['id']}")
        print(f"   GPU: {o.get('gpu_name', 'N/A')}")
        print(f"   Preço: ${o.get('dph_total', 0):.4f}/h")
        print(f"   Download: {o.get('inet_down', 0):.0f} Mbps")
        print(f"   Upload: {o.get('inet_up', 0):.0f} Mbps")
        print(f"   Disk: {o.get('disk_space', 0):.0f} GB")
        print(f"   Loc: {o.get('geolocation', 'N/A')}\n")
    
    # Escolher a melhor oferta (equilibrando preço e velocidade)
    best = offers[0]
    offer_id = best['id']
    
    print(f"🚀 Criando máquina (ID: {offer_id})...")
    
    # Criar instância
    create_resp = requests.put(
        f"https://console.vast.ai/api/v0/asks/{offer_id}/",
        headers=headers,
        json={
            "image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
            "disk": 50,
            "label": "dumont-snapshot-speed-test",
            "onstart": "bash -c 'apt-get update && apt-get install -y curl wget'"
        }
    )
    
    if not create_resp.ok:
        print(f"❌ Erro ao criar: {create_resp.status_code}")
        print(create_resp.text[:500])
        return None
    
    result = create_resp.json()
    instance_id = result.get("new_contract")
    
    if not instance_id:
        print("❌ Instance ID não retornado")
        print(result)
        return None
    
    print(f"✓ Máquina criada! Instance ID: {instance_id}")
    
    # Aguardar inicialização
    print("\n⏳ Aguardando inicialização...")
    max_wait = 180  # 3 minutos
    start = time.time()
    ssh_info = None
    
    while time.time() - start < max_wait:
        time.sleep(10)
        
        status_resp = requests.get(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers=headers
        )
        
        if status_resp.ok:
            data = status_resp.json()
            instances = data.get("instances", {})
            if instances and instance_id in instances:
                inst = instances[instance_id]
                status = inst.get("actual_status", "unknown")
                ssh_host = inst.get("ssh_host")
                ssh_port = inst.get("ssh_port")
                
                print(f"   Status: {status} ({int(time.time() - start)}s)", end="\r")
                
                if status == "running" and ssh_host and ssh_port:
                    ssh_info = {
                        "host": ssh_host,
                        "port": ssh_port,
                        "instance_id": instance_id,
                        "ip": inst.get("public_ipaddr"),
                        "inet_down": inst.get("inet_down", 0),
                        "inet_up": inst.get("inet_up", 0)
                    }
                    break
    
    if not ssh_info:
        print("\n❌ Timeout aguardando inicialização")
        return None
    
    print(f"\n\n✓ Máquina pronta!")
    print(f"   SSH: {ssh_info['host']}:{ssh_info['port']}")
    print(f"   IP: {ssh_info['ip']}")
    print(f"   Download: {ssh_info['inet_down']:.0f} Mbps")
    print(f"   Upload: {ssh_info['inet_up']:.0f} Mbps")
    
    # Aguardar mais um pouco para SSH estar 100% pronto
    print("\n⏳ Aguardando SSH ficar pronto (30s)...")
    time.sleep(30)
    
    # Testar SSH
    print("🔌 Testando conexão SSH...")
    test_cmd = [
        'ssh', '-p', str(ssh_info['port']),
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        f"root@{ssh_info['host']}",
        'echo "SSH OK"'
    ]
    
    for attempt in range(5):
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ SSH conectado!")
            break
        print(f"   Tentativa {attempt+1}/5 falhou, aguardando...")
        time.sleep(10)
    else:
        print("❌ SSH não conectou após 5 tentativas")
        return ssh_info  # Retorna mesmo assim
    
    # Popular workspace
    print("\n📦 Populando workspace com dados de teste (4.2GB)...")
    populate_cmd = f"""ssh -p {ssh_info['port']} -o StrictHostKeyChecking=no root@{ssh_info['host']} 'cd /workspace && pip install -q huggingface_hub && python3 << "PYEOF"
from huggingface_hub import hf_hub_download
import shutil
p = hf_hub_download("TinyLlama/TinyLlama-1.1B-Chat-v1.0", "model.safetensors", cache_dir="/tmp/hf")
shutil.copy(p, "/workspace/model.safetensors")
shutil.copy(p, "/workspace/model_copy.safetensors")
print("OK")
PYEOF
du -sh /workspace'"""
    
    result = subprocess.run(populate_cmd, shell=True, capture_output=True, text=True)
    if "OK" in result.stdout:
        print("✓ Workspace populado!")
        print(result.stdout.strip().split('\n')[-1])
    else:
        print("⚠️  Erro ao popular workspace")
        print(result.stdout)
    
    return ssh_info

def cleanup_machine(instance_id, api_key):
    """Destroi a máquina de teste"""
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.delete(
        f"https://console.vast.ai/api/v0/instances/{instance_id}/",
        headers=headers
    )
    if resp.ok:
        print(f"✓ Máquina {instance_id} destruída")
    else:
        print(f"❌ Erro ao destruir: {resp.text}")

if __name__ == "__main__":
    ssh_info = create_test_machine()
    
    if ssh_info:
        print("\n" + "="*70)
        print("MÁQUINA PRONTA PARA TESTES!")
        print("="*70)
        print(f"Host: {ssh_info['host']}")
        print(f"Port: {ssh_info['port']}")
        print(f"Instance ID: {ssh_info['instance_id']}")
        print(f"\nPara rodar o teste:")
        print(f"  python3 scripts/test_snapshot_speed.py {ssh_info['host']} {ssh_info['port']}")
        print(f"\nPara destruir:")
        print(f"  # Use a API do Vast.ai")
        
        # Salvar info para script de teste
        with open("/tmp/test_machine_info.json", "w") as f:
            json.dump(ssh_info, f, indent=2)
        print(f"\nInfo salva em: /tmp/test_machine_info.json")
    else:
        print("\n❌ Falha ao criar máquina")
        sys.exit(1)
