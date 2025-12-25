"""
API Commands - Direct wrapper for all API endpoints

Uses OpenAPI schema for auto-discovery. Commands follow API structure exactly:
- dumont GET /api/v1/instances
- dumont POST /api/v1/auth/login email=x password=y
- dumont GET /api/v1/metrics/spot/monitor

Or simplified:
- dumont instances list
- dumont auth login email=x password=y
- dumont spot monitor
"""
import re
import json
import sys
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode


class APICommands:
    """Direct API wrapper with auto-discovery"""

    def __init__(self, api_client):
        self.api = api_client
        self._schema = None
        self._endpoints = None

    def load_schema(self) -> Optional[Dict]:
        """Load OpenAPI schema"""
        if self._schema:
            return self._schema

        self._schema = self.api.load_openapi_schema()
        return self._schema

    def get_endpoints(self) -> Dict[str, Dict]:
        """Get all API endpoints organized by path"""
        if self._endpoints:
            return self._endpoints

        schema = self.load_schema()
        if not schema:
            return {}

        self._endpoints = {}
        paths = schema.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                key = f"{method.upper()} {path}"
                self._endpoints[key] = {
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "parameters": details.get("parameters", []),
                    "requestBody": details.get("requestBody"),
                    "tags": details.get("tags", []),
                }

        return self._endpoints

    def list_endpoints(self, filter_tag: str = None):
        """List all available endpoints"""
        endpoints = self.get_endpoints()

        if not endpoints:
            print("❌ Não foi possível carregar endpoints da API")
            print(f"   URL: {self.api.base_url}")
            return

        # Group by tag
        by_tag = {}
        for key, info in endpoints.items():
            tags = info.get("tags", ["Other"])
            for tag in tags:
                if filter_tag and filter_tag.lower() not in tag.lower():
                    continue
                if tag not in by_tag:
                    by_tag[tag] = []
                by_tag[tag].append((key, info))

        print("\n🚀 Dumont Cloud API Endpoints")
        print("=" * 70)

        for tag in sorted(by_tag.keys()):
            print(f"\n📦 {tag}")
            for key, info in sorted(by_tag[tag], key=lambda x: x[0]):
                method = info["method"]
                path = info["path"]
                summary = info.get("summary", "")[:40]
                print(f"  {method:6} {path:40} {summary}")

        print("\n" + "=" * 70)
        print("💡 Uso:")
        print("   dumont api GET /api/v1/health")
        print("   dumont api GET /api/v1/metrics/spot/monitor")
        print("   dumont api POST /api/v1/auth/login email=x password=y")

    def call(self, method: str, path: str, args: List[str] = None):
        """Execute an API call directly"""
        args = args or []

        # Replace path parameters from args
        path_params = re.findall(r'\{([^}]+)\}', path)
        remaining_args = []

        for arg in args:
            if "=" not in arg and path_params:
                # Positional arg for path parameter
                param = path_params.pop(0)
                path = path.replace(f"{{{param}}}", arg)
            else:
                remaining_args.append(arg)

        # Check for missing path params
        if path_params:
            print(f"❌ Parâmetros faltando: {', '.join(path_params)}")
            return None

        # Parse remaining args as query params or body
        data = None
        params = {}

        for arg in remaining_args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                # Type conversion
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)

                if method in ("POST", "PUT", "PATCH"):
                    if data is None:
                        data = {}
                    data[key] = value
                else:
                    params[key] = value

        # Check for JSON body
        for arg in remaining_args:
            if arg.startswith("{"):
                try:
                    data = json.loads(arg)
                    break
                except json.JSONDecodeError:
                    pass

        print(f"🔄 {method} {path}")
        return self.api.call(method, path, data, params if params else None)

    def execute(self, args: List[str]):
        """Execute command from args"""
        if not args:
            self.list_endpoints()
            return

        # Handle: dumont api list [tag]
        if args[0] == "list":
            tag = args[1] if len(args) > 1 else None
            self.list_endpoints(tag)
            return

        # Handle: dumont api GET /path
        if args[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            method = args[0].upper()
            if len(args) < 2:
                print(f"❌ Uso: dumont api {method} <path> [args...]")
                return
            path = args[1]
            self.call(method, path, args[2:])
            return

        # Handle: dumont api /path (default GET)
        if args[0].startswith("/"):
            self.call("GET", args[0], args[1:])
            return

        print("❌ Formato inválido")
        print("\n💡 Uso:")
        print("   dumont api list                    # Listar endpoints")
        print("   dumont api GET /api/v1/health      # GET request")
        print("   dumont api POST /path key=value    # POST request")


class SmartRouter:
    """
    Smart router that maps friendly commands to API endpoints.

    Mappings are auto-discovered from OpenAPI schema.
    Example: 'spot monitor' -> GET /api/v1/metrics/spot/monitor
    """

    # Manual shortcuts for common operations
    SHORTCUTS = {
        # Health
        ("health",): ("GET", "/health"),

        # Auth
        ("auth", "login"): ("POST", "/api/v1/auth/login"),
        ("auth", "me"): ("GET", "/api/v1/auth/me"),
        ("auth", "logout"): ("POST", "/api/v1/auth/logout"),

        # Instances
        ("instances",): ("GET", "/api/v1/instances"),
        ("instances", "list"): ("GET", "/api/v1/instances"),
        ("instance", "get"): ("GET", "/api/v1/instances/{instance_id}"),
        ("instance", "pause"): ("POST", "/api/v1/instances/{instance_id}/pause"),
        ("instance", "resume"): ("POST", "/api/v1/instances/{instance_id}/resume"),
        ("instance", "delete"): ("DELETE", "/api/v1/instances/{instance_id}"),

        # Spot/Market
        ("spot", "monitor"): ("GET", "/api/v1/metrics/spot/monitor"),
        ("spot", "prices"): ("GET", "/api/v1/metrics/spot/monitor"),
        ("spot", "predict"): ("GET", "/api/v1/metrics/spot/prediction/{gpu_name}"),
        ("spot", "prediction"): ("GET", "/api/v1/metrics/spot/prediction/{gpu_name}"),
        ("spot", "reliability"): ("GET", "/api/v1/metrics/spot/reliability"),
        ("spot", "llm-gpus"): ("GET", "/api/v1/metrics/spot/llm-gpus"),
        ("spot", "training-cost"): ("GET", "/api/v1/metrics/spot/training-cost"),
        ("spot", "fleet-strategy"): ("GET", "/api/v1/metrics/spot/fleet-strategy"),
        ("spot", "savings"): ("GET", "/api/v1/metrics/spot/savings"),

        # Savings
        ("savings", "summary"): ("GET", "/api/v1/savings/summary"),
        ("savings", "history"): ("GET", "/api/v1/savings/history"),
        ("savings", "breakdown"): ("GET", "/api/v1/savings/breakdown"),

        # Jobs
        ("jobs",): ("GET", "/api/v1/jobs"),
        ("jobs", "list"): ("GET", "/api/v1/jobs"),
        ("job", "get"): ("GET", "/api/v1/jobs/{job_id}"),
        ("job", "create"): ("POST", "/api/v1/jobs"),
        ("job", "cancel"): ("POST", "/api/v1/jobs/{job_id}/cancel"),

        # Snapshots
        ("snapshots",): ("GET", "/api/v1/snapshots"),
        ("snapshots", "list"): ("GET", "/api/v1/snapshots"),
        ("snapshot", "create"): ("POST", "/api/v1/snapshots"),
        ("snapshot", "restore"): ("POST", "/api/v1/snapshots/restore"),
        ("snapshot", "delete"): ("DELETE", "/api/v1/snapshots/{snapshot_id}"),

        # Serverless
        ("serverless", "status"): ("GET", "/api/v1/serverless/status"),
        ("serverless", "enable"): ("POST", "/api/v1/serverless/enable"),
        ("serverless", "disable"): ("POST", "/api/v1/serverless/disable"),

        # Warmpool
        ("warmpool", "status"): ("GET", "/api/v1/warmpool/status/{machine_id}"),
        ("warmpool", "enable"): ("POST", "/api/v1/warmpool/enable"),
        ("warmpool", "disable"): ("POST", "/api/v1/warmpool/disable"),

        # Models
        ("models",): ("GET", "/api/v1/models/deployments"),
        ("models", "list"): ("GET", "/api/v1/models/deployments"),
        ("models", "templates"): ("GET", "/api/v1/models/templates"),
        ("models", "deploy"): ("POST", "/api/v1/models/deploy"),

        # Hibernation
        ("hibernation", "stats"): ("GET", "/api/v1/hibernation/stats"),

        # Finetune
        ("finetune", "jobs"): ("GET", "/api/v1/finetune/jobs"),
        ("finetune", "models"): ("GET", "/api/v1/finetune/models"),
        ("finetune", "create"): ("POST", "/api/v1/finetune/jobs"),
    }

    def __init__(self, api_client):
        self.api = api_client
        self.api_commands = APICommands(api_client)

    def route(self, args: List[str]) -> bool:
        """
        Route command to API endpoint.
        Returns True if handled, False otherwise.
        """
        if not args:
            return False

        # Try to match shortcuts
        for length in range(min(3, len(args)), 0, -1):
            key = tuple(args[:length])
            if key in self.SHORTCUTS:
                method, path = self.SHORTCUTS[key]
                remaining = args[length:]
                self.api_commands.call(method, path, remaining)
                return True

        return False

    def help(self):
        """Show available shortcuts"""
        print("\n🚀 Dumont Cloud CLI - Comandos Disponíveis")
        print("=" * 60)

        # Group by first word
        groups = {}
        for key, (method, path) in self.SHORTCUTS.items():
            group = key[0]
            if group not in groups:
                groups[group] = []
            cmd = " ".join(key)
            groups[group].append((cmd, method, path))

        for group in sorted(groups.keys()):
            print(f"\n📦 {group.upper()}")
            for cmd, method, path in sorted(groups[group]):
                # Simplify path for display
                display_path = path.replace("/api/v1/", "")
                print(f"  {cmd:25} {method:6} {display_path}")

        print("\n" + "=" * 60)
        print("💡 Exemplos:")
        print("   dumont spot monitor")
        print("   dumont spot predict RTX4090")
        print("   dumont instances list")
        print("   dumont auth login email=x password=y")
        print("\n   dumont api GET /api/v1/health  # Acesso direto à API")
