#!/usr/bin/env python3
"""
Script para testar criação de máquina GPU barata
"""
import json
import os
import requests
import time

def main():
    # Carregar configurações
    config_file = "/home/ubuntu/dumont-cloud/config.json"
    if not os.path.exists(config_file):
        print("Config não encontrado")
        return

    with open(config_file) as f:
        config = json.load(f)

    users = config.get("users", {})
    api_key = None
    email = None

    for e, user_data in users.items():
        api_key = user_data.get("vast_api_key")
        if api_key:
            email = e
            break

    if not api_key:
        print("API Key não encontrada")
        return

    print(f"User: {email}")
    print(f"API Key: {api_key[:10]}...{api_key[-5:]}")

    # Buscar ofertas baratas
    headers = {"Authorization": f"Bearer {api_key}"}

    print("\n=== Buscando ofertas baratas ===")
    resp = requests.get(
        "https://console.vast.ai/api/v0/bundles",
        params={
            "q": json.dumps({
                "verified": {"eq": True},
                "rentable": {"eq": True},
                "type": "on-demand",
                "order": [["dph_total", "asc"]],
                "limit": 10
            })
        },
        headers=headers
    )

    if not resp.ok:
        print(f"Erro ao buscar ofertas: {resp.status_code}")
        print(resp.text[:500])
        return

    offers = resp.json().get("offers", [])
    print(f"Encontradas {len(offers)} ofertas\n")

    if not offers:
        print("Nenhuma oferta disponível")
        return

    # Mostrar as 5 mais baratas
    print("=== TOP 5 Mais Baratas ===")
    for i, o in enumerate(offers[:5]):
        print(f"\n#{i+1}: ID={o['id']}")
        print(f"   GPU: {o.get('gpu_name', 'N/A')}")
        print(f"   Preço: ${o.get('dph_total', 0):.4f}/h")
        print(f"   VRAM: {o.get('gpu_ram', 0):.0f} GB")
        print(f"   Loc: {o.get('geolocation', 'N/A')}")

    # Pegar a oferta mais barata
    cheapest = offers[0]
    offer_id = cheapest['id']
    price = cheapest.get('dph_total', 0)

    print(f"\n=== Criando máquina (ID: {offer_id}, ${price:.4f}/h) ===")

    # Criar a instância
    create_resp = requests.put(
        f"https://console.vast.ai/api/v0/asks/{offer_id}/",
        headers=headers,
        json={
            "image": "pytorch/pytorch:latest",
            "disk": 20,
            "label": "dumont-test-sync"
        }
    )

    if create_resp.ok:
        result = create_resp.json()
        instance_id = result.get("new_contract")
        print(f"✓ Máquina criada! Instance ID: {instance_id}")

        # Aguardar inicialização
        print("\n=== Aguardando inicialização (30s) ===")
        time.sleep(30)

        # Verificar status
        status_resp = requests.get(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers=headers
        )

        if status_resp.ok:
            inst = status_resp.json().get("instances", {})
            print(f"\nStatus: {inst.get('actual_status', 'unknown')}")
            print(f"SSH: {inst.get('ssh_host')}:{inst.get('ssh_port')}")
            print(f"IP: {inst.get('public_ipaddr')}")

        # Retornar o instance_id para possível destruição
        return instance_id
    else:
        print(f"✗ Erro ao criar: {create_resp.status_code}")
        print(create_resp.text[:500])
        return None


if __name__ == "__main__":
    instance_id = main()
    if instance_id:
        print(f"\n=== Instance ID: {instance_id} ===")
        print(f"Para destruir: DELETE /api/v1/instances/{instance_id}")
