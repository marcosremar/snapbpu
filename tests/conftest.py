"""
Dumont Cloud - Global Test Configuration

Configuração centralizada para TODOS os testes do projeto.
Usa Pydantic-Settings para carregar configurações do .env automaticamente.

Este arquivo fornece:
- Configuração centralizada via get_settings()
- APIClient com rate limiting e retry
- CLIRunner para testes de CLI
- GPU cleanup com signal handlers
- Fixtures compartilhadas
- Markers e hooks do pytest

Estrutura de Testes:
    tests/
    ├── conftest.py          # Este arquivo (GLOBAL)
    ├── backend/             # Testes de API backend
    │   └── api/
    └── cli/
        └── conftest.py      # Fixtures específicas do CLI (imports daqui)
"""
import os
import sys
import time
import json
import re
import atexit
import signal
import logging
import hashlib
import subprocess
import warnings
import pytest
import requests
from pathlib import Path
from typing import Optional, Dict, Any, Generator, List, Set
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CENTRALIZED CONFIGURATION (via Pydantic-Settings)
# =============================================================================

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import centralized settings - auto-loads .env via pydantic-settings
from src.core.config import get_settings

_settings = get_settings()


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# API Configuration
API_BASE_URL = os.environ.get("DUMONT_API_URL", f"http://localhost:{_settings.app.port}")
TEST_USER = os.environ.get("TEST_USER", "test@test.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")

# Rate Limiting Configuration
RATE_LIMIT_DELAY = float(os.environ.get("RATE_LIMIT_DELAY", "1.0"))
RATE_LIMIT_MAX_RETRIES = int(os.environ.get("RATE_LIMIT_MAX_RETRIES", "5"))
RATE_LIMIT_INITIAL_BACKOFF = float(os.environ.get("RATE_LIMIT_INITIAL_BACKOFF", "2.0"))
RATE_LIMIT_MAX_BACKOFF = float(os.environ.get("RATE_LIMIT_MAX_BACKOFF", "60.0"))

# CLI Configuration
CLI_PATH = str(PROJECT_ROOT / "cli")
VENV_PATH = str(PROJECT_ROOT / ".venv")

# GPU Cleanup Configuration
VAST_API_KEY = _settings.vast.api_key
TEST_LABEL_PREFIX = "dumont:test:"


# =============================================================================
# COLORS (for terminal output)
# =============================================================================

class Colors:
    """Terminal colors for test output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'


# =============================================================================
# DEFAULT CONFIG (for backward compatibility)
# =============================================================================

DEFAULT_CONFIG = {
    "BASE_URL": API_BASE_URL,
    "TIMEOUT": 30,
    "TEST_USER": TEST_USER,
    "TEST_PASSWORD": TEST_PASSWORD,
}


# =============================================================================
# BASE TEST CASE (for structured test output)
# =============================================================================

class BaseTestCase:
    """Base class for test cases with structured logging."""

    def log_info(self, message: str):
        """Log an info message."""
        print(f"{Colors.BLUE}[INFO]{Colors.END} {message}")

    def log_success(self, message: str):
        """Log a success message."""
        print(f"{Colors.GREEN}[OK]{Colors.END} {message}")

    def log_warning(self, message: str):
        """Log a warning message."""
        print(f"{Colors.YELLOW}[WARN]{Colors.END} {message}")

    def log_error(self, message: str):
        """Log an error message."""
        print(f"{Colors.RED}[ERROR]{Colors.END} {message}")


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class RateLimiter:
    """Rate limiter with exponential backoff for API calls."""

    def __init__(
        self,
        delay: float = RATE_LIMIT_DELAY,
        max_retries: int = RATE_LIMIT_MAX_RETRIES,
        initial_backoff: float = RATE_LIMIT_INITIAL_BACKOFF,
        max_backoff: float = RATE_LIMIT_MAX_BACKOFF,
    ):
        self.delay = delay
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.last_call = 0.0

    def wait(self):
        """Wait between API calls to respect rate limits."""
        elapsed = time.time() - self.last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call = time.time()

    def call_with_retry(self, func, *args, **kwargs):
        """Execute function with exponential backoff on rate limit errors."""
        backoff = self.initial_backoff

        for attempt in range(self.max_retries):
            self.wait()

            try:
                result = func(*args, **kwargs)

                # Check for rate limit in response
                if isinstance(result, dict):
                    error = str(result.get("error", ""))
                    if "429" in error or "rate limit" in error.lower():
                        raise RateLimitError(error)

                return result

            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    print(f"  Rate limit hit. Waiting {backoff:.1f}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * 1.5, self.max_backoff)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                if "429" in str(e):
                    if attempt < self.max_retries - 1:
                        print(f"  Rate limit (429). Waiting {backoff:.1f}s...")
                        time.sleep(backoff)
                        backoff = min(backoff * 1.5, self.max_backoff)
                    else:
                        raise
                else:
                    raise

        raise RateLimitError(f"All {self.max_retries} retries exhausted")


# =============================================================================
# API CLIENT
# =============================================================================

class APIClient:
    """
    API client with rate limiting and authentication.

    Thread-safe for parallel test execution with pytest-xdist.
    """

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = timeout
        self.timeout = timeout
        self.token = None
        self.rate_limiter = RateLimiter()
        self.last_response = None

    def login(self, username: str = TEST_USER, password: str = TEST_PASSWORD) -> bool:
        """Authenticate and store token."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            self.last_response = response

            if response.ok:
                data = response.json()
                # API returns "token" not "access_token"
                self.token = data.get("token") or data.get("access_token")
                if self.token:
                    self.session.headers["Authorization"] = f"Bearer {self.token}"
                    logger.info(f"Login OK: {username}")
                    return True

            logger.warning(f"Login failed: {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def call(self, method: str, path: str, data: dict = None, params: dict = None) -> dict:
        """Make API call with rate limiting."""
        def _do_call():
            url = f"{self.base_url}{path}"
            if method.upper() == "GET":
                resp = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == "POST":
                resp = self.session.post(url, json=data, timeout=self.timeout)
            elif method.upper() == "PUT":
                resp = self.session.put(url, json=data, timeout=self.timeout)
            elif method.upper() == "DELETE":
                resp = self.session.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            self.last_response = resp
            return self._handle_response(resp)

        return self.rate_limiter.call_with_retry(_do_call)

    def get(self, path: str, params: dict = None, timeout: int = None) -> Dict[str, Any]:
        """GET request."""
        return self.call("GET", path, params=params)

    def post(self, path: str, data: dict = None, timeout: int = None) -> Dict[str, Any]:
        """POST request."""
        return self.call("POST", path, data=data)

    def put(self, path: str, data: dict = None, timeout: int = None) -> Dict[str, Any]:
        """PUT request."""
        return self.call("PUT", path, data=data)

    def delete(self, path: str, timeout: int = None) -> Dict[str, Any]:
        """DELETE request."""
        return self.call("DELETE", path)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle response and return dict."""
        try:
            data = response.json()
            data["_status_code"] = response.status_code
            data["_ok"] = response.ok
            return data
        except Exception:
            return {
                "text": response.text[:500] if response.text else "",
                "_status_code": response.status_code,
                "_ok": response.ok
            }


# =============================================================================
# CLI RUNNER
# =============================================================================

@dataclass
class CLIResult:
    """Result of CLI command execution."""
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration: float

    @property
    def success(self) -> bool:
        return self.returncode == 0

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


class CLIRunner:
    """CLI command runner with rate limiting."""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = f"{PROJECT_ROOT}:{self.env.get('PYTHONPATH', '')}"

    def run(self, *args, timeout: int = 60) -> CLIResult:
        """Execute CLI command."""
        self.rate_limiter.wait()

        # Use modular CLI (__main__.py) via python -m cli
        cmd = [f"{VENV_PATH}/bin/python", "-m", "cli"] + list(args)
        cmd_str = " ".join(["dumont"] + list(args))
        start = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(PROJECT_ROOT),
                env=self.env
            )
            elapsed = time.time() - start

            return CLIResult(
                command=cmd_str,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=elapsed
            )

        except subprocess.TimeoutExpired:
            return CLIResult(
                command=cmd_str,
                returncode=-1,
                stdout="",
                stderr="TIMEOUT",
                duration=time.time() - start
            )

        except Exception as e:
            return CLIResult(
                command=cmd_str,
                returncode=-1,
                stdout="",
                stderr=str(e),
                duration=time.time() - start
            )


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TestResult:
    """Result of an API test."""
    endpoint: str
    method: str
    success: bool
    status_code: int
    response_time: float
    error: Optional[str] = None
    response_preview: Optional[str] = None


@dataclass
class TestReport:
    """Complete test report."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    results: List[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)

    def summary(self) -> Dict[str, Any]:
        self.end_time = datetime.now()
        passed = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        return {
            "total": len(self.results),
            "passed": len(passed),
            "failed": len(failed),
            "success_rate": f"{len(passed)/len(self.results)*100:.1f}%" if self.results else "0%",
            "duration": str(self.end_time - self.start_time),
            "avg_response_time": f"{sum(r.response_time for r in self.results)/len(self.results):.2f}s" if self.results else "0s",
        }


# =============================================================================
# GPU INSTANCE CLEANUP SYSTEM
# =============================================================================

# Global state for crash-safe cleanup
_created_instances: Set[int] = set()
_vast_client = None


def _get_vast_client():
    """Get or create VastService client."""
    global _vast_client
    if _vast_client is None and VAST_API_KEY:
        try:
            from src.services.gpu.vast import VastService
            _vast_client = VastService(VAST_API_KEY)
        except RuntimeError:
            # Python is shutting down - can't create new threads
            return None
        except Exception as e:
            try:
                logger.warning(f"Could not create VastService: {e}")
            except (ValueError, RuntimeError):
                pass
    return _vast_client


def register_instance(instance_id: int):
    """Register an instance for cleanup tracking."""
    _created_instances.add(instance_id)
    logger.info(f"[CLEANUP-TRACKER] Registered instance {instance_id}")


def unregister_instance(instance_id: int):
    """Unregister an instance (already cleaned up)."""
    _created_instances.discard(instance_id)
    logger.info(f"[CLEANUP-TRACKER] Unregistered instance {instance_id}")


def _safe_log(level, msg):
    """Safe logging that doesn't fail during Python shutdown."""
    try:
        if level == "info":
            logger.info(msg)
        elif level == "warning":
            logger.warning(msg)
    except (ValueError, RuntimeError):
        # Ignore logging errors during shutdown
        pass


def _cleanup_all_test_instances():
    """
    Emergency cleanup of ALL test instances.
    Called on crash, timeout, or session end.
    """
    if not VAST_API_KEY:
        return

    client = _get_vast_client()
    if not client:
        return

    _safe_log("info", "[CLEANUP] Starting emergency cleanup of all test instances...")

    # Method 1: Clean registered instances
    for instance_id in list(_created_instances):
        try:
            _safe_log("info", f"[CLEANUP] Destroying registered instance {instance_id}")
            client.destroy_instance(instance_id)
            _created_instances.discard(instance_id)
        except Exception as e:
            _safe_log("warning", f"[CLEANUP] Failed to destroy {instance_id}: {e}")

    # Method 2: Clean all instances with test label (fallback)
    try:
        instances = client.list_instances()
        for inst in instances:
            label = inst.get("label", "") or ""
            if label.startswith(TEST_LABEL_PREFIX) or label.startswith("pytest-"):
                inst_id = inst.get("id")
                try:
                    _safe_log("info", f"[CLEANUP] Destroying label-matched instance {inst_id} (label: {label})")
                    client.destroy_instance(inst_id)
                except Exception as e:
                    _safe_log("warning", f"[CLEANUP] Failed to destroy {inst_id}: {e}")
    except Exception as e:
        _safe_log("warning", f"[CLEANUP] Failed to list instances: {e}")

    _safe_log("info", "[CLEANUP] Emergency cleanup complete")


# =============================================================================
# SIGNAL HANDLERS FOR CRASH-SAFE CLEANUP
# =============================================================================

def _signal_handler(signum, frame):
    """Handle termination signals to ensure cleanup."""
    sig_name = signal.Signals(signum).name
    logger.info(f"[SIGNAL] Received {sig_name} - initiating cleanup...")
    _cleanup_all_test_instances()
    sys.exit(1)


# Register signal handlers (may fail in some environments)
for sig in [signal.SIGINT, signal.SIGTERM]:
    try:
        signal.signal(sig, _signal_handler)
    except Exception:
        pass

# Register atexit handler
atexit.register(_cleanup_all_test_instances)


# =============================================================================
# PYTEST HOOKS
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "real: marks tests using real GPU resources (deselect with '-m \"not real\"')")
    config.addinivalue_line("markers", "benchmark: marks benchmark tests")
    config.addinivalue_line("markers", "unit: marks unit tests")
    config.addinivalue_line("markers", "failover: marks failover tests")
    config.addinivalue_line("markers", "images: marks docker image tests")
    config.addinivalue_line("markers", "expensive: marks tests that consume significant credits")
    config.addinivalue_line("markers", "creates_machine: marks tests that create their own GPU machine")
    config.addinivalue_line("markers", "uses_shared_machine: marks tests that use a shared GPU machine")

    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}Dumont Cloud Tests{Colors.END}")
    print(f"{Colors.CYAN}API URL: {API_BASE_URL}{Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")


def pytest_sessionfinish(session, exitstatus):
    """Called after all tests complete (success or failure)."""
    logger.info(f"[PYTEST] Session finished with exit status: {exitstatus}")
    _cleanup_all_test_instances()
    print(f"\n{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}Tests Finished (exit: {exitstatus}){Colors.END}")
    print(f"{Colors.CYAN}{'='*60}{Colors.END}")


def pytest_keyboard_interrupt(excinfo):
    """Called when user presses Ctrl+C."""
    logger.info("[PYTEST] Keyboard interrupt detected - cleaning up...")
    _cleanup_all_test_instances()


def pytest_collection_modifyitems(config, items):
    """Automatically add markers based on test location/name."""
    for item in items:
        # Add markers based on file name
        if "real" in item.fspath.basename:
            item.add_marker(pytest.mark.real)
            item.add_marker(pytest.mark.integration)

        if "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)

        if "benchmark" in item.fspath.basename:
            item.add_marker(pytest.mark.benchmark)

        # Add slow marker for tests with certain patterns
        if "lifecycle" in item.name.lower() or "failover" in item.name.lower():
            item.add_marker(pytest.mark.slow)


def pytest_report_header(config):
    """Add custom header to test report."""
    return [
        "Dumont Cloud Tests",
        f"API URL: {API_BASE_URL}",
        f"Test User: {TEST_USER}",
        f"Rate Limit Delay: {RATE_LIMIT_DELAY}s",
    ]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def settings():
    """
    Centralized Pydantic settings fixture.

    Provides typed access to all configuration:
        settings.vast.api_key
        settings.app.port
        settings.r2.bucket
        etc.
    """
    return _settings


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for API."""
    return API_BASE_URL


@pytest.fixture(scope="session")
def vast_api_key(settings) -> str:
    """Get VAST API key from centralized settings."""
    key = settings.vast.api_key
    if not key:
        pytest.skip("VAST_API_KEY not configured")
    return key


@pytest.fixture(scope="session")
def tensordock_credentials() -> Dict[str, str]:
    """Get TensorDock credentials from .env."""
    api_key = os.environ.get("TENSORDOCK_AUTH_ID")
    api_token = os.environ.get("TENSORDOCK_API_TOKEN")

    if not api_key or not api_token:
        pytest.skip("TensorDock credentials not in .env")

    return {"api_key": api_key, "api_token": api_token}


@pytest.fixture(scope="session")
def rate_limiter() -> RateLimiter:
    """Session-scoped rate limiter."""
    return RateLimiter()


@pytest.fixture(scope="session")
def api_client(api_base_url) -> Generator[APIClient, None, None]:
    """Session-scoped authenticated API client."""
    client = APIClient(api_base_url)
    if not client.login():
        pytest.skip(f"Could not authenticate with {api_base_url}")
    yield client


@pytest.fixture(scope="module")
def module_api_client(api_base_url) -> APIClient:
    """Module-scoped API client for isolated tests."""
    client = APIClient(api_base_url)
    if not client.login():
        pytest.skip(f"Could not authenticate with {api_base_url}")
    return client


@pytest.fixture(scope="function")
def fresh_api_client(api_base_url) -> APIClient:
    """Fresh API client for each test (isolated sessions)."""
    client = APIClient(api_base_url)
    if not client.login():
        pytest.skip(f"Could not authenticate with {api_base_url}")
    return client


@pytest.fixture(scope="session")
def cli_runner() -> CLIRunner:
    """Session-scoped CLI runner."""
    return CLIRunner()


@pytest.fixture(scope="session")
def logged_in_cli(cli_runner) -> CLIRunner:
    """CLI runner with login performed."""
    result = cli_runner.run("auth", "login", TEST_USER, TEST_PASSWORD)
    if not result.success:
        pytest.skip(f"Could not login via CLI: {result.stderr}")
    return cli_runner


@pytest.fixture(scope="session", autouse=True)
def session_cleanup():
    """
    Session-level cleanup fixture.
    Runs before and after all tests.
    """
    # Pre-test cleanup
    logger.info("[SESSION] Starting test session - cleaning orphaned instances...")
    _cleanup_all_test_instances()

    yield

    # Post-test cleanup
    logger.info("[SESSION] Test session ending - final cleanup...")
    _cleanup_all_test_instances()


@pytest.fixture
def auto_cleanup_instance(request):
    """
    Fixture that automatically destroys an instance when the test ends.

    Usage:
        def test_something(auto_cleanup_instance):
            instance_id = create_some_instance()
            auto_cleanup_instance(instance_id)  # Will be destroyed on test end
    """
    instances_to_cleanup = []

    def _register(instance_id: int):
        instances_to_cleanup.append(instance_id)
        register_instance(instance_id)
        return instance_id

    yield _register

    # Cleanup all registered instances
    client = _get_vast_client()
    if client:
        for instance_id in instances_to_cleanup:
            try:
                logger.info(f"[AUTO-CLEANUP] Destroying instance {instance_id}")
                client.destroy_instance(instance_id)
                unregister_instance(instance_id)
            except Exception as e:
                logger.warning(f"[AUTO-CLEANUP] Failed to destroy {instance_id}: {e}")


@pytest.fixture(scope="function")
def sample_instance_data():
    """Sample instance data for tests."""
    return {
        "offer_id": "test_offer_123",
        "name": "test-instance-api",
        "image": "pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
        "disk_space": 100,
        "gpu_count": 1
    }


@pytest.fixture(scope="function")
def sample_snapshot_data():
    """Sample snapshot data for tests."""
    return {
        "instance_id": "test_instance_123",
        "name": "test-snapshot-api",
        "compression": "bitshuffle_lz4",
        "deduplicate": True
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_json_output(output: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from CLI output robustly.

    Tries multiple strategies:
    1. Direct parse of output
    2. Extract JSON block with regex
    3. Search for lines starting with { or [
    """
    if not output:
        return None

    # Strategy 1: Direct parse
    try:
        return json.loads(output.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract JSON block with regex
    json_patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # JSON object
        r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # JSON array
    ]
    for pattern in json_patterns:
        match = re.search(pattern, output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    # Strategy 3: Search line by line
    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('{') or line.startswith('['):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    return None


def assert_valid_response(
    result: CLIResult,
    expected_keys: Optional[List[str]] = None,
    min_items: Optional[int] = None,
    allow_empty: bool = False
) -> Dict[str, Any]:
    """
    Validate CLI response robustly.

    Args:
        result: CLI runner result
        expected_keys: Expected keys in response dict
        min_items: Minimum items if response is a list
        allow_empty: If True, allows empty response

    Returns:
        Parsed dict/list from response

    Raises:
        AssertionError: If validation fails
    """
    assert result.returncode == 0, f"Command failed (code {result.returncode}): {result.stderr}"

    data = parse_json_output(result.output)

    if not allow_empty:
        assert data is not None, f"Invalid JSON response: {result.output[:500]}"

    if expected_keys and isinstance(data, dict):
        for key in expected_keys:
            assert key in data, f"Missing required key '{key}' in response: {list(data.keys())}"

    if min_items is not None and isinstance(data, list):
        assert len(data) >= min_items, f"Expected at least {min_items} items, got {len(data)}"

    return data


# =============================================================================
# SLA TARGETS
# =============================================================================

SLA_TARGETS = {
    "cpu_standby_detection": 30,    # 30 seconds
    "cpu_standby_migration": 120,   # 2 minutes
    "cpu_standby_total": 180,       # 3 minutes
    "warmpool_detection": 10,       # 10 seconds
    "warmpool_migration": 30,       # 30 seconds
    "warmpool_total": 60,           # 1 minute
}

SLA_MARGIN = 1.2  # 20% tolerance margin


def assert_sla(metric_name: str, actual_value: float, margin: float = SLA_MARGIN):
    """
    Assert metric is within SLA with configurable margin.

    Args:
        metric_name: Metric name (must exist in SLA_TARGETS)
        actual_value: Measured value in seconds
        margin: Margin multiplier (1.0 = no margin, 1.2 = 20% margin)

    Raises:
        AssertionError: If SLA is violated
    """
    if metric_name not in SLA_TARGETS:
        raise ValueError(f"Unknown SLA metric: {metric_name}. Valid: {list(SLA_TARGETS.keys())}")

    target = SLA_TARGETS[metric_name]
    max_allowed = target * margin

    assert actual_value <= max_allowed, (
        f"SLA VIOLATION: {metric_name}={actual_value:.2f}s > {max_allowed:.2f}s "
        f"(target={target}s, margin={margin}x)"
    )
