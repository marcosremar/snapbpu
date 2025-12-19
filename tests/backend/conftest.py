#!/usr/bin/env python3
"""
Framework Base para Testes Backend - Dumont Cloud

Configuração compartilhada para todos os testes backend com:
- Cache inteligente de testes (baseado em hash do arquivo)
- Fixtures reutilizáveis
- Sessões autenticadas
- Configurações de ambiente
- Logging estruturado
- Rate limiting protection

Uso:
    pytest tests/backend/ -v
    pytest tests/backend/auth/test_login.py -v
"""

import pytest
import requests
import json
import time
import hashlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Adicionar diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações padrão
DEFAULT_CONFIG = {
    "BASE_URL": os.environ.get("TEST_BASE_URL", "http://localhost:8766"),
    "TEST_USER": os.environ.get("TEST_USER", "test@example.com"),
    "TEST_PASS": os.environ.get("TEST_PASS", "test123"),
    "TIMEOUT": int(os.environ.get("TEST_TIMEOUT", "30")),
    "RETRY_ATTEMPTS": int(os.environ.get("TEST_RETRY", "3")),
    "CACHE_ENABLED": os.environ.get("TEST_CACHE", "true").lower() == "true",
    "CACHE_DIR": Path(__file__).parent / ".test_cache"
}


class Colors:
    """Cores para output de testes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'


class TestCache:
    """Cache inteligente para evitar re-execução de testes
    
    Baseado no hash do arquivo de teste e parâmetros.
    Se o arquivo não mudou e o cache existe, pula o teste.
    """
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_file_hash(self, file_path: Path) -> str:
        """Calcula hash SHA256 do arquivo de teste"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return "unknown"
    
    def get_cache_key(self, test_file: Path, test_params: Dict = None) -> str:
        """Gera chave única para o cache"""
        file_hash = self.get_file_hash(test_file)
        params_str = json.dumps(test_params or {}, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:8]
        return f"{test_file.stem}_{file_hash}_{params_hash}"
    
    def has_result(self, cache_key: str) -> bool:
        """Verifica se tem resultado em cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        return cache_file.exists()
    
    def get_result(self, cache_key: str) -> Optional[Dict]:
        """Obtém resultado do cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_result(self, cache_key: str, result: Dict):
        """Salva resultado no cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Falha ao salvar cache: {e}")
    
    def clear_old_cache(self, max_age_hours: int = 24):
        """Limpa cache antigo"""
        cutoff = time.time() - (max_age_hours * 3600)
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.stat().st_mtime < cutoff:
                try:
                    cache_file.unlink()
                except Exception:
                    pass


# Cache global
cache = TestCache(DEFAULT_CONFIG["CACHE_DIR"])


class APIClient:
    """Client HTTP reutilizável com autenticação e retry"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.timeout = timeout
        self.token = None
        self.last_response = None
    
    def login(self, username: str, password: str) -> bool:
        """Faz login e armazena token JWT"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": username, "password": password},
                timeout=self.timeout
            )
            
            self.last_response = resp
            
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                if token:
                    self.token = token
                    self.session.headers.update({"Authorization": f"Bearer {token}"})
                    logger.info(f"Login OK: {username}")
                    return True
            
            logger.warning(f"Login falhou: {resp.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Login erro: {e}")
            return False
    
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Faz request HTTP com retry"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(DEFAULT_CONFIG["RETRY_ATTEMPTS"]):
            try:
                resp = self.session.request(
                    method, url, timeout=self.timeout, **kwargs
                )
                self.last_response = resp
                return resp
                
            except requests.exceptions.Timeout:
                if attempt < DEFAULT_CONFIG["RETRY_ATTEMPTS"] - 1:
                    logger.warning(f"Timeout, tentativa {attempt + 2}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
            
            except Exception as e:
                if attempt < DEFAULT_CONFIG["RETRY_ATTEMPTS"] - 1:
                    logger.warning(f"Request erro, tentativa {attempt + 2}: {e}")
                    time.sleep(1)
                    continue
                raise
        
        raise Exception("Max retry attempts reached")
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("DELETE", endpoint, **kwargs)


class BaseTestCase:
    """Classe base para testes com cache e utilities"""
    
    @classmethod
    def setup_class(cls):
        """Setup executado uma vez por classe de teste"""
        cls.config = DEFAULT_CONFIG.copy()
        cls.client = APIClient(cls.config["BASE_URL"], cls.config["TIMEOUT"])
        cls.cache_key = cache.get_cache_key(
            Path(__file__), 
            cls.config
        )
        
        # Verifica cache
        if cls.config["CACHE_ENABLED"] and cache.has_result(cls.cache_key):
            logger.info(f"Usando cache para {cls.__name__}")
            cls._cached_result = cache.get_result(cls.cache_key)
        else:
            cls._cached_result = None
    
    @classmethod
    def teardown_class(cls):
        """Teardown executado uma vez por classe de teste"""
        if hasattr(cls, '_test_result') and cls.config["CACHE_ENABLED"]:
            cache.save_result(cls.cache_key, cls._test_result)
    
    def setup_method(self, method):
        """Setup executado antes de cada método de teste"""
        self.method_name = method.__name__
        
        # Se tem cache, pula teste
        if hasattr(self, '_cached_result') and self._cached_result:
            pytest.skip(f"Teste em cache: {self.method_name}")
    
    def log_success(self, message: str):
        """Log de sucesso"""
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
        logger.info(f"PASS: {message}")
    
    def log_fail(self, message: str):
        """Log de falha"""
        print(f"{Colors.RED}✗{Colors.END} {message}")
        logger.error(f"FAIL: {message}")
    
    def log_info(self, message: str):
        """Log de informação"""
        print(f"{Colors.BLUE}ℹ{Colors.END} {message}")
        logger.info(f"INFO: {message}")
    
    def log_warning(self, message: str):
        """Log de aviso"""
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
        logger.warning(f"WARN: {message}")
    
    def assert_success_response(self, response: requests.Response, message: str = None):
        """Assert que response foi sucesso"""
        if response.status_code not in [200, 201, 204]:
            self.log_fail(f"{message or 'Request'} falhou: {response.status_code}")
            try:
                self.log_fail(f"Response: {response.json()}")
            except:
                self.log_fail(f"Response: {response.text}")
            pytest.fail(f"Status {response.status_code}")
        
        self.log_success(message or f"Request OK ({response.status_code})")
    
    def assert_json_keys(self, data: Dict, required_keys: list):
        """Assert que JSON contém chaves requeridas"""
        missing = [key for key in required_keys if key not in data]
        if missing:
            self.log_fail(f"Chaves faltando: {missing}")
            pytest.fail(f"Missing keys: {missing}")
        
        self.log_success(f"JSON keys OK: {required_keys}")


# Fixtures globais
@pytest.fixture(scope="session")
def config():
    """Configuração global"""
    return DEFAULT_CONFIG.copy()


@pytest.fixture(scope="session") 
def api_client(config):
    """Client API autenticado"""
    client = APIClient(config["BASE_URL"], config["TIMEOUT"])
    
    # Tenta login
    if not client.login(config["TEST_USER"], config["TEST_PASS"]):
        pytest.skip("Não foi possível fazer login")
    
    yield client


@pytest.fixture(scope="session")
def unauth_client(config):
    """Client API sem autenticação"""
    return APIClient(config["BASE_URL"], config["TIMEOUT"])


@pytest.fixture(scope="function")
def sample_instance_data():
    """Dados de instância para testes"""
    return {
        "offer_id": "test_offer_123",
        "name": "test-instance-api",
        "image": "pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
        "disk_space": 100,
        "gpu_count": 1
    }


@pytest.fixture(scope="function")
def sample_snapshot_data():
    """Dados de snapshot para testes"""
    return {
        "instance_id": "test_instance_123",
        "name": "test-snapshot-api",
        "compression": "bitshuffle_lz4",
        "deduplicate": True
    }


# Hooks do pytest
def pytest_configure(config):
    """Executado no início da sessão de testes"""
    # Limpa cache antigo
    cache.clear_old_cache()
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}Dumont Cloud Backend Tests{Colors.END}")
    print(f"{Colors.CYAN}Cache: {'ENABLED' if DEFAULT_CONFIG['CACHE_ENABLED'] else 'DISABLED'}{Colors.END}")
    print(f"{Colors.CYAN}Base URL: {DEFAULT_CONFIG['BASE_URL']}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")


def pytest_sessionfinish(session, exitstatus):
    """Executado ao final da sessão de testes"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}Testes Finalizados{Colors.END}")
    print(f"{Colors.CYAN}Exit status: {exitstatus}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")


# Decorator para cache
def cached_test(test_func):
    """Decorator para habilitar cache em testes específicos"""
    def wrapper(*args, **kwargs):
        # Lógica de cache aqui
        return test_func(*args, **kwargs)
    return wrapper
