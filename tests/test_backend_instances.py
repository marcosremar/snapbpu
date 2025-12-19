#!/usr/bin/env python3
"""
Testes Backend - Gerenciamento de Instâncias GPU

Testa endpoints de gerenciamento de instâncias do sistema Dumont Cloud:
- GET /api/v1/instances/search - Busca de ofertas GPU
- POST /api/v1/instances/create - Criação de instância
- GET /api/v1/instances/list - Listagem de instâncias
- GET /api/v1/instances/{id} - Detalhes da instância
- POST /api/v1/instances/{id}/pause - Pausar instância
- POST /api/v1/instances/{id}/resume - Resumir instância
- DELETE /api/v1/instances/{id} - Destruir instância
- POST /api/v1/instances/multi-status - Status múltiplas instâncias

Uso:
    pytest tests/test_backend_instances.py -v
    pytest tests/test_backend_instances.py -v -k "test_search"
"""

import pytest
import requests
import json
import time
from datetime import datetime, timedelta
import sys
import os

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuração
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8766")
TEST_USER = os.environ.get("TEST_USER", "test@example.com")
TEST_PASS = os.environ.get("TEST_PASS", "test123")


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


@pytest.fixture(scope="module")
def auth_session():
    """Cria sessão autenticada para os testes."""
    s = requests.Session()
    
    # Faz login
    resp = s.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": TEST_USER, "password": TEST_PASS},
        timeout=10
    )
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        if token:
            s.headers.update({"Authorization": f"Bearer {token}"})
            print(f"{Colors.GREEN}✓ Login JWT OK{Colors.END}")
            return s
    
    pytest.fail(f"Não foi possível fazer login: {resp.text}")


class TestInstanceSearch:
    """Testes para busca de ofertas GPU"""
    
    def test_search_basic(self, auth_session):
        """GET /api/v1/instances/search - Busca básica"""
        resp = auth_session.get(
            f"{BASE_URL}/api/v1/instances/search",
            params={"gpu": "rtx_4090", "limit": 10},
            timeout=30
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "offers" in data
        assert isinstance(data["offers"], list)
        assert len(data["offers"]) <= 10
        
        if data["offers"]:
            offer = data["offers"][0]
            required_fields = ["id", "gpu_name", "price", "cpu_cores", "ram", "disk_space"]
            for field in required_fields:
                assert field in offer, f"Campo {field} faltando na oferta"
        
        print(f"  ✓ Busca básica: {len(data['offers'])} ofertas encontradas")
    
    def test_search_with_filters(self, auth_session):
        """GET /api/v1/instances/search - Busca com filtros avançados"""
        resp = auth_session.get(
            f"{BASE_URL}/api/v1/instances/search",
            params={
                "gpu": "rtx_4090",
                "min_cpu": 8,
                "min_ram": 32,
                "min_disk": 500,
                "max_price": 1.0,
                "verified": True,
                "limit": 5
            },
            timeout=30
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Validar filtros aplicados
        for offer in data["offers"]:
            assert offer["cpu_cores"] >= 8, f"CPU {offer['cpu_cores']} < 8"
            assert offer["ram"] >= 32, f"RAM {offer['ram']} < 32"
            assert offer["disk_space"] >= 500, f"Disk {offer['disk_space']} < 500"
            assert offer["price"] <= 1.0, f"Price {offer['price']} > 1.0"
        
        print(f"  ✓ Busca com filtros: {len(data['offers'])} ofertas filtradas")
    
    def test_search_price_range(self, auth_session):
        """GET /api/v1/instances/search - Busca por faixa de preço"""
        resp = auth_session.get(
            f"{BASE_URL}/api/v1/instances/search",
            params={
                "min_price": 0.2,
                "max_price": 0.5,
                "limit": 10
            },
            timeout=30
        )
        
        assert resp.status_code == 200
        data = resp.json()
        
        for offer in data["offers"]:
            assert 0.2 <= offer["price"] <= 0.5, f"Price {offer['price']} fora do range"
        
        print(f"  ✓ Faixa de preço: {len(data['offers'])} ofertas no range")
    
    def test_search_gpu_models(self, auth_session):
        """GET /api/v1/instances/search - Busca por modelos específicos"""
        gpu_models = ["rtx_4090", "rtx_3090", "a100"]
        
        for gpu in gpu_models:
            resp = auth_session.get(
                f"{BASE_URL}/api/v1/instances/search",
                params={"gpu": gpu, "limit": 3},
                timeout=30
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            for offer in data["offers"]:
                assert gpu.lower() in offer["gpu_name"].lower(), \
                    f"GPU {gpu} não encontrado em {offer['gpu_name']}"
        
        print(f"  ✓ Modelos específicos: {len(gpu_models)} GPUs testadas")
    
    def test_search_pagination(self, auth_session):
        """GET /api/v1/instances/search - Paginação de resultados"""
        # Primeira página
        resp1 = auth_session.get(
            f"{BASE_URL}/api/v1/instances/search",
            params={"gpu": "rtx_4090", "limit": 5, "offset": 0},
            timeout=30
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        
        # Segunda página
        resp2 = auth_session.get(
            f"{BASE_URL}/api/v1/instances/search",
            params={"gpu": "rtx_4090", "limit": 5, "offset": 5},
            timeout=30
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        
        # Verificar que são diferentes
        if len(data1["offers"]) > 0 and len(data2["offers"]) > 0:
            assert data1["offers"][0]["id"] != data2["offers"][0]["id"], \
                "Paginação não funcionando"
        
        print(f"  ✓ Paginação: página 1={len(data1['offers'])}, página 2={len(data2['offers'])}")
    
    def test_search_no_results(self, auth_session):
        """GET /api/v1/instances/search - Busca sem resultados"""
        resp = auth_session.get(
            f"{BASE_URL}/api/v1/instances/search",
            params={
                "gpu": "nonexistent_gpu_model",
                "min_price": 0.01,
                "max_price": 0.02
            },
            timeout=30
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["offers"] == []
        
        print(f"  ✓ Busca sem resultados: lista vazia retornada")


class TestInstanceLifecycle:
    """Testes para ciclo de vida de instâncias"""
    
    def test_list_instances(self, auth_session):
        """GET /api/v1/instances/list - Listar instâncias do usuário"""
        resp = auth_session.get(
            f"{BASE_URL}/api/v1/instances/list",
            timeout=30
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "instances" in data
        assert isinstance(data["instances"], list)
        
        for instance in data["instances"]:
            required_fields = ["id", "name", "status", "gpu_name", "price", "created_at"]
            for field in required_fields:
                assert field in instance, f"Campo {field} faltando na instância"
        
        print(f"  ✓ Listar instâncias: {len(data['instances'])} encontradas")
    
    def test_get_instance_details(self, auth_session):
        """GET /api/v1/instances/{id} - Detalhes de instância específica"""
        # Primeiro listar para obter um ID
        list_resp = auth_session.get(
            f"{BASE_URL}/api/v1/instances/list",
            timeout=30
        )
        
        if list_resp.status_code == 200:
            instances = list_resp.json()["instances"]
            if instances:
                instance_id = instances[0]["id"]
                
                # Obter detalhes
                resp = auth_session.get(
                    f"{BASE_URL}/api/v1/instances/{instance_id}",
                    timeout=30
                )
                
                assert resp.status_code == 200
                data = resp.json()
                
                required_fields = [
                    "id", "name", "status", "gpu_name", "price", "cpu_cores",
                    "ram", "disk_space", "ssh_host", "ssh_port", "created_at"
                ]
                for field in required_fields:
                    assert field in data, f"Campo {field} faltando nos detalhes"
                
                print(f"  ✓ Detalhes da instância {instance_id}: status={data['status']}")
            else:
                print(f"  ⚠ Nenhuma instância encontrada para testar detalhes")
    
    def test_create_instance_validation(self, auth_session):
        """POST /api/v1/instances/create - Validação de criação"""
        # Testa sem offer_id
        resp = auth_session.post(
            f"{BASE_URL}/api/v1/instances/create",
            json={},
            timeout=30
        )
        
        # Deve retornar erro de validação
        assert resp.status_code in [400, 422], f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "error" in data or "detail" in data, "Erro de validação não retornado"
        print(f"  ✓ Validação criação: offer_id obrigatório")
    
    def test_create_instance_full(self, auth_session):
        """POST /api/v1/instances/create - Criação completa (simulada)"""
        # Primeiro buscar uma oferta
        search_resp = auth_session.get(
            f"{BASE_URL}/api/v1/instances/search",
            params={"gpu": "rtx_4090", "limit": 1},
            timeout=30
        )
        
        if search_resp.status_code == 200:
            offers = search_resp.json()["offers"]
            if offers:
                offer = offers[0]
                
                # Tentar criar instância (pode falhar se não tiver saldo)
                create_resp = auth_session.post(
                    f"{BASE_URL}/api/v1/instances/create",
                    json={
                        "offer_id": offer["id"],
                        "name": f"test-instance-{int(time.time())}",
                        "image": "pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
                        "disk_space": 100
                    },
                    timeout=60
                )
                
                # Pode ser 201 (criado) ou 403/500 (sem saldo/erro)
                if create_resp.status_code in [200, 201]:
                    data = create_resp.json()
                    assert "instance_id" in data
                    print(f"  ✓ Instância criada: {data['instance_id']}")
                elif create_resp.status_code in [403, 500]:
                    print(f"  ⚠ Criação falhou (sem saldo ou erro API)")
                else:
                    print(f"  ⚠ Status inesperado: {create_resp.status_code}")
            else:
                print(f"  ⚠ Nenhuma oferta encontrada para criar instância")
    
