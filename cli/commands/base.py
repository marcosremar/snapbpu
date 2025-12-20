"""Base command builder for API-backed commands"""
import re
import json
import sys
from typing import Dict, Any, List, Optional


class CommandBuilder:
    """Build and execute commands from OpenAPI schema"""

    def __init__(self, api_client):
        self.api = api_client
        self.commands_cache = None

    def build_command_tree(self) -> Dict[str, Any]:
        """Build command tree from OpenAPI schema with manual overrides"""
        if self.commands_cache:
            return self.commands_cache

        schema = self.api.load_openapi_schema()
        if not schema:
            return {}

        paths = schema.get("paths", {})
        commands = {}

        # Manual overrides for better command mapping
        overrides = {
            "auth": {
                "login": ["POST", "/api/auth/login"],
                "logout": ["POST", "/api/auth/logout"],
                "me": ["GET", "/api/auth/me"],
                "register": ["POST", "/api/auth/register"],
            },
            "instance": {
                "list": ["GET", "/api/v1/instances"],
                "create": ["POST", "/api/v1/instances"],
                "get": ["GET", "/api/v1/instances/{instance_id}"],
                "delete": ["DELETE", "/api/v1/instances/{instance_id}"],
                "pause": ["POST", "/api/v1/instances/{instance_id}/pause"],
                "resume": ["POST", "/api/v1/instances/{instance_id}/resume"],
                "wake": ["POST", "/api/v1/instances/{instance_id}/wake"],
                "migrate": ["POST", "/api/v1/instances/{instance_id}/migrate"],
                "migrate-estimate": ["POST", "/api/v1/instances/{instance_id}/migrate/estimate"],
                "sync": ["POST", "/api/v1/instances/{instance_id}/sync"],
                "sync-status": ["GET", "/api/v1/instances/{instance_id}/sync/status"],
                "offers": ["GET", "/api/v1/instances/offers"],
            },
            "snapshot": {
                "list": ["GET", "/api/v1/snapshots"],
                "create": ["POST", "/api/v1/snapshots"],
                "restore": ["POST", "/api/v1/snapshots/restore"],
                "delete": ["DELETE", "/api/v1/snapshots/{snapshot_id}"],
            },
            "finetune": {
                "list": ["GET", "/api/v1/finetune/jobs"],
                "create": ["POST", "/api/v1/finetune/jobs"],
                "get": ["GET", "/api/v1/finetune/jobs/{job_id}"],
                "logs": ["GET", "/api/v1/finetune/jobs/{job_id}/logs"],
                "cancel": ["POST", "/api/v1/finetune/jobs/{job_id}/cancel"],
                "refresh": ["POST", "/api/v1/finetune/jobs/{job_id}/refresh"],
                "models": ["GET", "/api/v1/finetune/models"],
                "upload-dataset": ["POST", "/api/v1/finetune/jobs/upload-dataset"],
            },
            "savings": {
                "summary": ["GET", "/api/v1/savings/summary"],
                "history": ["GET", "/api/v1/savings/history"],
                "breakdown": ["GET", "/api/v1/savings/breakdown"],
                "comparison": ["GET", "/api/v1/savings/comparison/{gpu_type}"],
            },
            "metrics": {
                "market": ["GET", "/api/v1/metrics/market"],
                "market-summary": ["GET", "/api/v1/metrics/market/summary"],
                "providers": ["GET", "/api/v1/metrics/providers"],
                "efficiency": ["GET", "/api/v1/metrics/efficiency"],
                "predictions": ["GET", "/api/v1/metrics/predictions/{gpu_name}"],
                "compare": ["GET", "/api/v1/metrics/compare"],
                "gpus": ["GET", "/api/v1/metrics/gpus"],
                "types": ["GET", "/api/v1/metrics/types"],
                "savings-real": ["GET", "/api/v1/metrics/savings/real"],
                "savings-history": ["GET", "/api/v1/metrics/savings/history"],
                "hibernation-events": ["GET", "/api/v1/metrics/hibernation/events"],
            },
            "settings": {
                "get": ["GET", "/api/v1/settings"],
                "update": ["PUT", "/api/v1/settings"],
            },
        }

        for resource, actions in overrides.items():
            if resource not in commands:
                commands[resource] = {}
            for action, info in actions.items():
                method, path = info
                dest_path_info = paths.get(path, {}).get(method.lower())
                if dest_path_info:
                    commands[resource][action] = {
                        "method": method,
                        "path": path,
                        "summary": dest_path_info.get("summary", ""),
                        "parameters": dest_path_info.get("parameters", []),
                        "requestBody": dest_path_info.get("requestBody"),
                    }
                else:
                    # Still add even if not in schema
                    commands[resource][action] = {
                        "method": method,
                        "path": path,
                        "summary": f"{action} {resource}",
                        "parameters": [],
                        "requestBody": None,
                    }

        # Auto-discover from OpenAPI
        for path, methods in paths.items():
            parts = [p for p in path.split("/") if p and p not in ["api", "v1"]]
            if not parts:
                continue

            resource = parts[0]
            if resource.endswith("s") and resource not in ["settings", "metrics", "stats"]:
                resource = resource[:-1]

            for method, details in methods.items():
                method_upper = method.upper()

                if len(parts) > 1 and "{" not in parts[1]:
                    action = parts[1]
                elif method_upper == "GET" and "{" in path:
                    action = "get"
                elif method_upper == "GET":
                    action = "list"
                elif method_upper == "POST":
                    action = "create"
                elif method_upper == "DELETE":
                    action = "delete"
                elif method_upper == "PUT":
                    action = "update"
                else:
                    action = "run"

                if resource not in commands:
                    commands[resource] = {}

                if action not in commands[resource]:
                    commands[resource][action] = {
                        "method": method_upper,
                        "path": path,
                        "summary": details.get("summary", ""),
                        "parameters": details.get("parameters", []),
                        "requestBody": details.get("requestBody"),
                    }

        self.commands_cache = commands
        return commands

    def list_commands(self):
        """List all discovered commands"""
        commands = self.build_command_tree()
        print("\n🚀 Dumont Cloud - Command Reference\n")
        print("Usage: dumont <resource> <action> [args...]")
        print("-" * 60)

        for resource in sorted(commands.keys()):
            print(f"\n📦 {resource.upper()}")
            for action, info in sorted(commands[resource].items()):
                summary = info.get("summary", "")
                print(f"  - {action:15} {summary}")

        print("\n" + "-" * 60)
        print("Type 'dumont --help' for examples.\n")

    def execute(self, resource: str, action: str, args: List[str]):
        """Execute a command"""
        if resource == "help" or (resource == "list" and not action):
            self.list_commands()
            return

        commands = self.build_command_tree()

        if resource not in commands:
            print(f"❌ Unknown resource: {resource}")
            print(f"\n💡 Available resources: {', '.join(commands.keys())}")
            sys.exit(1)

        if action not in commands[resource]:
            print(f"❌ Unknown action '{action}' for {resource}")
            print(f"\n💡 Available actions: {', '.join(commands[resource].keys())}")
            sys.exit(1)

        cmd_info = commands[resource][action]
        method = cmd_info["method"]
        path = cmd_info["path"]

        params = {}
        data = None

        # Replace path parameters
        path_params = re.findall(r'\{([^}]+)\}', path)
        if path_params:
            for i, param_name in enumerate(path_params):
                if i < len(args):
                    path = path.replace(f"{{{param_name}}}", args[i])
                else:
                    print(f"❌ Missing required parameter: {param_name}")
                    sys.exit(1)
            args = args[len(path_params):]

        print(f"🔄 {method} {path}")

        # Parse request body
        if "requestBody" in cmd_info and args:
            if args[0].startswith("{"):
                data = json.loads(args[0])
            else:
                # Special handling for specific commands
                if action == "login" and resource == "auth":
                    if len(args) >= 2:
                        data = {}
                        data["username"] = args[0]
                        data["password"] = args[1]
                else:
                    # Parse key=value pairs
                    data = {}
                    for arg in args:
                        if "=" in arg:
                            key, value = arg.split("=", 1)
                            try:
                                if value.lower() == "true":
                                    value = True
                                elif value.lower() == "false":
                                    value = False
                                elif value.isdigit():
                                    value = int(value)
                            except:
                                pass
                            data[key] = value

        # Parse query parameters
        for arg in args:
            if "=" in arg and (data is None or arg not in str(data)):
                key, value = arg.split("=", 1)
                params[key] = value

        self.api.call(method, path, data, params if params else None)
