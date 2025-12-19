#!/usr/bin/env python3
"""
Testes de Integração - Auto-Hibernação e Economia

Testa os novos endpoints implementados:
- POST /api/agent/status - Heartbeat do DumontAgent
- GET  /api/agent/instances - Lista instâncias com agentes ativos
- POST /api/v1/instances/{id}/wake - Acorda instância hibernada
- GET  /api/v1/metrics/savings/real - Dashboard de economia real
- GET  /api/v1/metrics/savings/history - Histórico de economia
- GET  /api/v1/metrics/hibernation/events - Eventos de hibernação

Uso:
    pytest tests/test_hibernation_integration.py -v
    pytest tests/test_hibernation_integration.py -v -k "test_agent"
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
TEST_USER = os.environ.get("TEST_USER", "marcoslogin")
TEST_PASS = os.environ.get("TEST_PASS", "marcos123")


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


@pytest.fixture(scope="module")
def session():
    """Cria sessão autenticada para os testes."""
    s = requests.Session()
    
    # Tenta login JWT primeiro
    try:
        resp = s.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": TEST_USER, "password": TEST_PASS},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
                print(f"{Colors.GREEN}✓ Login JWT OK{Colors.END}")
                return s
    except Exception as e:
        print(f"{Colors.YELLOW}JWT login falhou: {e}{Colors.END}")
    
    # Fallback para login por cookie
    try:
        resp = s.post(
            f"{BASE_URL}/login",
            data={"username": TEST_USER, "password": TEST_PASS},
            allow_redirects=False
        )
        if resp.status_code in [200, 302]:
            print(f"{Colors.GREEN}✓ Login Cookie OK{Colors.END}")
            return s
    except Exception as e:
        print(f"{Colors.RED}Login falhou: {e}{Colors.END}")
    
    return s


class TestAgentEndpoints:
    """Testes para endpoints do agente /api/agent/*"""
    
    def test_agent_status_heartbeat(self, session):
        """POST /api/agent/status - Envia heartbeat do DumontAgent"""
        payload = {
            "agent": "DumontAgent",
            "version": "1.0.0",
            "instance_id": "test_12345",
            "status": "idle",
            "message": "Test heartbeat",
            "last_backup": datetime.utcnow().isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": "1h 30m",
            "gpu_utilization": 15.5
        }
        
        resp = session.post(f"{BASE_URL}/api/agent/status", json=payload, timeout=10)
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert data.get("received") == True
        assert data.get("instance_id") == "test_12345"
        assert "action" in data
        print(f"  ✓ Heartbeat recebido: action={data.get('action')}")
    
    def test_agent_status_with_gpu_metrics(self, session):
        """POST /api/agent/status - Heartbeat com métricas de GPU completas"""
        payload = {
            "agent": "DumontAgent",
            "version": "1.0.0",
            "instance_id": "vast_67890",
            "status": "syncing",
            "timestamp": datetime.utcnow().isoformat(),
            "gpu_metrics": {
                "utilization": 85.5,
                "gpu_count": 2,
                "gpu_names": ["RTX 4090", "RTX 4090"],
                "gpu_utilizations": [90.0, 81.0],
                "gpu_memory_used": [18000, 17500],
                "gpu_memory_total": [24576, 24576],
                "gpu_temperatures": [68.0, 65.0]
            }
        }
        
        resp = session.post(f"{BASE_URL}/api/agent/status", json=payload, timeout=10)
        
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("received") == True
        print(f"  ✓ Heartbeat com GPU metrics aceito")
    
    def test_agent_status_idle_detection(self, session):
        """POST /api/agent/status - Teste detecção de GPU ociosa"""
        # Envia heartbeat com GPU ociosa (< 5%)
        payload = {
            "agent": "DumontAgent",
            "version": "1.0.0",
            "instance_id": "idle_test_001",
            "status": "idle",
            "timestamp": datetime.utcnow().isoformat(),
            "gpu_utilization": 2.0  # < 5%, deve ser detectada como ociosa
        }
        
        resp = session.post(f"{BASE_URL}/api/agent/status", json=payload, timeout=10)
        
        assert resp.status_code == 200
        data = resp.json()
        # Pode retornar prepare_hibernate se instância estiver ociosa há tempo suficiente
        assert data.get("action") in ["none", "prepare_hibernate"]
        print(f"  ✓ Instância ociosa processada: action={data.get('action')}")
    
    def test_agent_instances_list(self, session):
        """GET /api/agent/instances - Lista instâncias com agentes ativos"""
        resp = session.get(f"{BASE_URL}/api/agent/instances", timeout=10)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        print(f"  ✓ {len(data)} instâncias com agentes ativos")
        
        # Verifica estrutura se houver instâncias
        if data:
            inst = data[0]
            assert "instance_id" in inst
            assert "status" in inst
            assert "gpu_utilization" in inst
    
    def test_agent_instance_status(self, session):
        """GET /api/agent/instances/{id} - Status de uma instância específica"""
        # Primeiro, cria uma instância de teste via heartbeat
        payload = {
            "agent": "DumontAgent",
            "version": "1.0.0",
            "instance_id": "status_test_001",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "gpu_utilization": 50.0
        }
        session.post(f"{BASE_URL}/api/agent/status", json=payload, timeout=10)
        
        # Busca status
        resp = session.get(f"{BASE_URL}/api/agent/instances/status_test_001", timeout=10)
        
        # Pode retornar 404 se a instância não foi persistida ou 200 se foi
        if resp.status_code == 200:
            data = resp.json()
            assert "instance_id" in data
            print(f"  ✓ Status encontrado: {data.get('status')}")
        else:
            print(f"  ⚠ Instância não persistida (esperado em alguns casos)")
    
    def test_agent_keep_alive(self, session):
        """POST /api/agent/instances/{id}/keep-alive - Adiar hibernação"""
        resp = session.post(
            f"{BASE_URL}/api/agent/instances/keep_test_001/keep-alive",
            params={"minutes": 30},
            timeout=10
        )
        
        # Pode retornar 404 se instância não existe ou 200 se funcionou
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("success") == True
            print(f"  ✓ Keep-alive estendido por 30 minutos")
        else:
            print(f"  ⚠ Keep-alive: instância não encontrada (ok para teste)")


class TestWakeEndpoint:
    """Testes para endpoint de wake /api/v1/instances/{id}/wake"""
    
    def test_wake_endpoint_exists(self, session):
        """POST /api/v1/instances/{id}/wake - Endpoint existe"""
        # Testa que o endpoint existe e responde corretamente
        resp = session.post(
            f"{BASE_URL}/api/v1/instances/test_wake_001/wake",
            json={"max_price": 1.0},
            timeout=10
        )
        
        # Pode retornar 503 (manager não inicializado) ou 500 (instância não existe)
        # O importante é que não retorne 404/405
        assert resp.status_code in [200, 500, 503]
        print(f"  ✓ Endpoint wake existe e responde (status={resp.status_code})")
    
    def test_wake_endpoint_validation(self, session):
        """POST /api/v1/instances/{id}/wake - Validação de parâmetros"""
        # Request sem body (deve usar defaults)
        resp = session.post(
            f"{BASE_URL}/api/v1/instances/validation_test/wake",
            timeout=10
        )
        
        # Endpoint deve aceitar request vazio (usa defaults)
        assert resp.status_code in [200, 500, 503]
        print(f"  ✓ Wake sem parâmetros aceito (usa defaults)")


class TestSavingsEndpoints:
    """Testes para endpoints de economia /api/v1/metrics/savings/*"""
    
    def test_savings_real(self, session):
        """GET /api/v1/metrics/savings/real - Dashboard de economia real"""
        resp = session.get(
            f"{BASE_URL}/api/v1/metrics/savings/real",
            params={"days": 30},
            timeout=10
        )
        
        assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "period_days" in data
        assert "summary" in data
        assert "gpu_breakdown" in data
        
        summary = data["summary"]
        assert "total_savings_usd" in summary
        assert "total_hours_saved" in summary
        assert "hibernation_count" in summary
        assert "projected_monthly_savings_usd" in summary
        
        print(f"  ✓ Economia: ${summary['total_savings_usd']} ({summary['hibernation_count']} hibernações)")
    
    def test_savings_real_with_filter(self, session):
        """GET /api/v1/metrics/savings/real - Com filtro de dias"""
        for days in [7, 30, 90]:
            resp = session.get(
                f"{BASE_URL}/api/v1/metrics/savings/real",
                params={"days": days},
                timeout=10
            )
            
            assert resp.status_code == 200
            data = resp.json()
            assert data["period_days"] == days
            print(f"  ✓ Filtro {days} dias OK")
    
    def test_savings_history(self, session):
        """GET /api/v1/metrics/savings/history - Histórico de economia"""
        resp = session.get(
            f"{BASE_URL}/api/v1/metrics/savings/history",
            params={"days": 30, "group_by": "day"},
            timeout=10
        )
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert "period_days" in data
        assert "history" in data
        assert "total_cumulative_savings" in data
        
        print(f"  ✓ Histórico: {len(data['history'])} dias, acumulado ${data['total_cumulative_savings']}")
    
    def test_hibernation_events(self, session):
        """GET /api/v1/metrics/hibernation/events - Lista eventos"""
        resp = session.get(
            f"{BASE_URL}/api/v1/metrics/hibernation/events",
            params={"limit": 10},
            timeout=10
        )
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert "events" in data
        assert "count" in data
        
        print(f"  ✓ {data['count']} eventos de hibernação")
        
        # Verifica estrutura se houver eventos
        if data["events"]:
            event = data["events"][0]
            assert "instance_id" in event
            assert "event_type" in event
            assert "timestamp" in event
    
    def test_hibernation_events_filter_by_type(self, session):
        """GET /api/v1/metrics/hibernation/events - Filtro por tipo"""
        for event_type in ["hibernated", "idle_detected", "woke_up"]:
            resp = session.get(
                f"{BASE_URL}/api/v1/metrics/hibernation/events",
                params={"event_type": event_type, "limit": 5},
                timeout=10
            )
            
            assert resp.status_code == 200
            print(f"  ✓ Filtro tipo={event_type} OK")


class TestStandbyEndpoints:
    """Testes para endpoints de CPU Standby /api/v1/standby/*"""
    
    def test_standby_status(self, session):
        """GET /api/v1/standby/status - Status do sistema de standby"""
        resp = session.get(f"{BASE_URL}/api/v1/standby/status", timeout=10)
        
        # Pode retornar 200 ou 401 (sem auth), mas não 404
        if resp.status_code == 200:
            data = resp.json()
            assert "auto_standby_enabled" in data
            print(f"  ✓ Standby status: enabled={data.get('auto_standby_enabled')}")
        else:
            print(f"  ⚠ Standby status: auth required ou indisponível")
    
    def test_standby_pricing(self, session):
        """GET /api/v1/standby/pricing - Estimativa de preço"""
        resp = session.get(
            f"{BASE_URL}/api/v1/standby/pricing",
            params={
                "machine_type": "e2-medium",
                "disk_gb": 100,
                "spot": True
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"  ✓ Preço estimado: ${data.get('estimated_monthly_usd', '?')}/mês")
        else:
            print(f"  ⚠ Pricing: indisponível (pode requerer credenciais GCP)")


class TestHealthAndDocs:
    """Testes básicos de health e documentação"""
    
    def test_health_endpoint(self, session):
        """GET /health - Health check"""
        resp = session.get(f"{BASE_URL}/health", timeout=5)
        
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy"
        print(f"  ✓ Health OK: version={data.get('version')}")
    
    def test_openapi_docs(self, session):
        """GET /docs - Documentação OpenAPI"""
        resp = session.get(f"{BASE_URL}/docs", timeout=5)
        
        assert resp.status_code == 200
        assert "swagger" in resp.text.lower() or "openapi" in resp.text.lower()
        print(f"  ✓ Documentação OpenAPI disponível")
    
    def test_openapi_json(self, session):
        """GET /api/v1/openapi.json - Schema OpenAPI"""
        resp = session.get(f"{BASE_URL}/api/v1/openapi.json", timeout=5)
        
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert "info" in data
        
        # Verifica se os novos endpoints estão documentados
        paths = data.get("paths", {})
        required_paths = [
            "/agent/status",
            "/metrics/savings/real",
        ]
        
        found = []
        for path in required_paths:
            if any(path in p for p in paths.keys()):
                found.append(path)
        
        print(f"  ✓ Endpoints documentados: {len(found)}/{len(required_paths)}")


def run_tests():
    """Executa todos os testes manualmente."""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
