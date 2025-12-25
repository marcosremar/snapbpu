"""
E2E Tests - Local Configuration

Fixtures específicas para testes E2E que requerem o servidor backend rodando.
Este conftest inicia o uvicorn automaticamente, tornando os testes autossuficientes.

NOTA: Os fixtures usam prefixo "e2e_" para evitar conflito com fixtures globais.
"""
import os
import sys
import time
import socket
import subprocess
import pytest
import requests
from pathlib import Path
from typing import Generator, Optional, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.conftest import Colors


# =============================================================================
# CONFIGURATION
# =============================================================================

E2E_SERVER_PORT = int(os.environ.get("E2E_SERVER_PORT", "8000"))
E2E_SERVER_HOST = "127.0.0.1"
E2E_SERVER_STARTUP_TIMEOUT = 30  # seconds

# Test credentials (unique per run to avoid conflicts)
E2E_TEST_EMAIL = f"e2e_auto_{int(time.time())}@example.com"
E2E_TEST_PASSWORD = "e2e_test_password_123"


def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def _wait_for_server(base_url: str, timeout: int = E2E_SERVER_STARTUP_TIMEOUT) -> bool:
    """Wait for server to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    return False


# =============================================================================
# E2E API CLIENT (returns raw Response objects)
# =============================================================================

class E2EClient:
    """
    Simple E2E test client that wraps requests and returns Response objects.
    Unlike APIClient, this returns the raw Response for direct status_code access.
    """

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout
        self.token: Optional[str] = None

    def login(self, username: str = None, password: str = None) -> bool:
        """Authenticate and store token. Auto-registers if user doesn't exist."""
        if username is None:
            username = E2E_TEST_EMAIL
        if password is None:
            password = E2E_TEST_PASSWORD
            
        try:
            # Try login first
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.ok:
                data = response.json()
                self.token = data.get("token") or data.get("access_token")
                if self.token:
                    self.session.headers["Authorization"] = f"Bearer {self.token}"
                    print(f"{Colors.GREEN}[E2E] Logged in as {username}{Colors.END}")
                    return True
            
            # If login fails, try to register
            if response.status_code == 401:
                print(f"{Colors.YELLOW}[E2E] User not found, registering {username}...{Colors.END}")
                reg_resp = self.session.post(
                    f"{self.base_url}/api/v1/auth/register",
                    json={"email": username, "password": password},
                    timeout=10
                )
                
                if reg_resp.ok:
                    data = reg_resp.json()
                    self.token = data.get("token") or data.get("access_token")
                    if self.token:
                        self.session.headers["Authorization"] = f"Bearer {self.token}"
                        print(f"{Colors.GREEN}[E2E] Registered and logged in as {username}{Colors.END}")
                        return True
                    
                    # If no token in register response, try login again
                    login2 = self.session.post(
                        f"{self.base_url}/api/v1/auth/login",
                        json={"username": username, "password": password},
                        timeout=10
                    )
                    if login2.ok:
                        data = login2.json()
                        self.token = data.get("token") or data.get("access_token")
                        if self.token:
                            self.session.headers["Authorization"] = f"Bearer {self.token}"
                            print(f"{Colors.GREEN}[E2E] Logged in as {username}{Colors.END}")
                            return True
                
                print(f"{Colors.RED}[E2E] Registration failed: {reg_resp.status_code}{Colors.END}")
                
            return False
        except Exception as e:
            print(f"{Colors.RED}[E2E] Login error: {e}{Colors.END}")
            return False

    def get(self, path: str, params: dict = None, headers: dict = None) -> requests.Response:
        """GET request returning raw Response."""
        url = f"{self.base_url}{path}"
        return self.session.get(url, params=params, headers=headers, timeout=self.timeout)

    def post(self, path: str, json: dict = None, data: dict = None, headers: dict = None) -> requests.Response:
        """POST request returning raw Response."""
        url = f"{self.base_url}{path}"
        return self.session.post(url, json=json or data, headers=headers, timeout=self.timeout)

    def put(self, path: str, json: dict = None, headers: dict = None) -> requests.Response:
        """PUT request returning raw Response."""
        url = f"{self.base_url}{path}"
        return self.session.put(url, json=json, headers=headers, timeout=self.timeout)

    def delete(self, path: str, headers: dict = None) -> requests.Response:
        """DELETE request returning raw Response."""
        url = f"{self.base_url}{path}"
        return self.session.delete(url, headers=headers, timeout=self.timeout)


# =============================================================================
# BACKEND SERVER FIXTURE (autouse to ensure server starts first)
# =============================================================================

_server_process = None


@pytest.fixture(scope="module", autouse=True)
def e2e_backend_server():
    """
    Start uvicorn server for E2E tests (autouse=True).
    
    This fixture is autossuficiente (self-contained):
    - Starts the server automatically before tests
    - Stops the server after tests complete
    - Reuses existing server if already running (for manual testing)
    """
    global _server_process
    
    base_url = f"http://{E2E_SERVER_HOST}:{E2E_SERVER_PORT}"
    
    # Check if server is already running
    if _is_port_in_use(E2E_SERVER_PORT, E2E_SERVER_HOST):
        print(f"{Colors.YELLOW}[E2E] Server already running on port {E2E_SERVER_PORT}{Colors.END}")
        yield base_url
        return
    
    # Start uvicorn server
    print(f"{Colors.CYAN}[E2E] Starting backend server on port {E2E_SERVER_PORT}...{Colors.END}")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "src.main:app",
            "--host", E2E_SERVER_HOST,
            "--port", str(E2E_SERVER_PORT),
            "--log-level", "warning"
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _server_process = proc
    
    # Wait for server to start
    if _wait_for_server(base_url):
        print(f"{Colors.GREEN}[E2E] Server started successfully{Colors.END}")
        yield base_url
    else:
        proc.terminate()
        proc.wait()
        stdout, stderr = proc.communicate(timeout=5)
        pytest.fail(
            f"Failed to start backend server within {E2E_SERVER_STARTUP_TIMEOUT}s.\n"
            f"stdout: {stdout.decode()[:500]}\n"
            f"stderr: {stderr.decode()[:500]}"
        )
        return
    
    # Cleanup: stop server
    print(f"{Colors.CYAN}[E2E] Stopping backend server...{Colors.END}")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    _server_process = None
    print(f"{Colors.GREEN}[E2E] Server stopped{Colors.END}")


# =============================================================================
# API CLIENT FIXTURES (override global fixtures)
# =============================================================================

@pytest.fixture(scope="module")
def e2e_api_client(e2e_backend_server) -> Generator[E2EClient, None, None]:
    """
    Module-scoped authenticated API client for E2E tests.
    
    OVERRIDES global api_client fixture.
    Depends on e2e_backend_server to ensure server is running.
    Returns E2EClient which provides raw Response objects.
    Auto-registers user if doesn't exist.
    """
    client = E2EClient(e2e_backend_server)
    if not client.login():
        pytest.skip(f"Could not authenticate with {e2e_backend_server}")
    yield client


@pytest.fixture(scope="module")
def e2e_unauth_client(e2e_backend_server) -> Generator[E2EClient, None, None]:
    """
    Module-scoped unauthenticated API client.
    
    For testing registration, login, and unauthenticated endpoints.
    Does NOT call login(), just provides raw HTTP access.
    """
    client = E2EClient(e2e_backend_server)
    yield client
