"""Base command builder for API-backed commands - Auto-discovery only"""
import re
import json
import sys
from typing import Dict, Any, List, Optional


class CommandBuilder:
    """Build and execute commands from OpenAPI schema (auto-discovery)"""

    def __init__(self, api_client):
        self.api = api_client
        self.commands_cache = None

    def build_command_tree(self) -> Dict[str, Any]:
        """Build command tree from OpenAPI schema (auto-discovery)"""
        if self.commands_cache:
            return self.commands_cache

        schema = self.api.load_openapi_schema()

        if not schema:
            print("\n❌ Não foi possível conectar ao backend.")
            print(f"   URL: {self.api.base_url}")
            print("\n💡 Verifique se o backend está rodando:")
            print("   cd /home/marcos/dumontcloud && python -m src.main")
            print("")
            sys.exit(1)

        paths = schema.get("paths", {})
        commands = {}

        # Auto-discover ALL endpoints from OpenAPI schema
        for path, methods in paths.items():
            # Skip non-API paths
            if not path.startswith("/api"):
                continue

            # Parse path into resource and action
            parts = [p for p in path.split("/") if p and p not in ["api", "v1", "auth"]]
            if not parts:
                continue

            # Determine resource name
            resource = parts[0]

            # Handle special cases for better naming
            if path.startswith("/api/auth"):
                resource = "auth"
                parts = [p for p in path.split("/") if p and p not in ["api", "auth"]]

            # Singularize resource names (instances -> instance)
            # Exceções: palavras que terminam em 's' mas não devem ser singularizadas
            no_singularize = ["settings", "metrics", "stats", "savings", "serverless", "status"]
            if resource.endswith("s") and resource not in no_singularize:
                resource = resource[:-1]

            for method, details in methods.items():
                method_upper = method.upper()

                # Determine action name
                action = self._determine_action(path, parts, method_upper)

                # Initialize resource if needed
                if resource not in commands:
                    commands[resource] = {}

                # Add command (don't overwrite existing)
                if action not in commands[resource]:
                    commands[resource][action] = {
                        "method": method_upper,
                        "path": path,
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "requestBody": details.get("requestBody"),
                        "tags": details.get("tags", []),
                    }

        self.commands_cache = commands
        return commands

    def _show_resource_help(self, resource: str, actions: Dict[str, Any], failed_action: Optional[str] = None):
        """Show help for a specific resource"""
        # Resource-specific titles
        resource_titles = {
            "job": "GPU Job Commands",
            "finetune": "Fine-Tuning Commands",
            "instance": "Instance Management",
            "snapshot": "Snapshot Commands",
            "warmpool": "Warm Pool Commands",
            "failover": "Failover Commands",
            "serverless": "Serverless Mode Commands",
            "auth": "Authentication Commands",
            "setting": "Settings Commands",
            "savings": "Savings & Cost Commands",
            "history": "History Commands",
            "spot": "Spot GPU Commands",
        }

        title = resource_titles.get(resource, f"{resource.title()} Commands")

        if failed_action:
            print(f"❌ Ação desconhecida '{failed_action}' para {resource}\n")

        print(f"🔧 {title}\n")
        print(f"Usage: dumont {resource} <action> [options]\n")
        print("Actions:")

        for action_name, info in sorted(actions.items()):
            summary = info.get("summary", "")
            method = info.get("method", "")
            if len(summary) > 50:
                summary = summary[:47] + "..."
            print(f"  {action_name:20} {summary}")

        print("")

        # Resource-specific examples
        examples = {
            "job": [
                f"dumont job list",
                f"dumont job get <job_id>",
                f"dumont job create instance_id=123 command='python train.py'",
            ],
            "finetune": [
                f"dumont finetune list",
                f"dumont finetune create model=llama3 dataset=my-data",
                f"dumont finetune get <job_id>",
            ],
            "instance": [
                f"dumont instance list",
                f"dumont instance get <instance_id>",
                f"dumont instance pause <instance_id>",
            ],
            "auth": [
                f"dumont auth login <email> <password>",
                f"dumont auth me",
            ],
        }

        if resource in examples:
            print("Examples:")
            for ex in examples[resource]:
                print(f"  {ex}")
            print("")

    def _determine_action(self, path: str, parts: List[str], method: str) -> str:
        """Determine action name from path and method"""
        # Special handling for auth endpoints - use the last path segment
        # e.g., /api/auth/login -> action = "login"
        # e.g., /api/auth/me -> action = "me"
        if "/api/auth/" in path:
            auth_parts = path.split("/api/auth/")[-1].split("/")
            if auth_parts and auth_parts[0]:
                return auth_parts[0]

        # If path has a sub-resource after the main resource
        # e.g., /api/v1/instances/{id}/pause -> action = "pause"
        # e.g., /api/v1/failover/settings/global -> action = "settings-global" or smart naming

        if len(parts) >= 2:
            # Check if second part is a path parameter
            if "{" in parts[1]:
                # /resource/{id} -> get, delete, update based on method
                if len(parts) >= 3:
                    # /resource/{id}/action -> use action name
                    action_parts = [p for p in parts[2:] if "{" not in p]
                    if action_parts:
                        return "-".join(action_parts)
                # Just /resource/{id}
                if method == "GET":
                    return "get"
                elif method == "DELETE":
                    return "delete"
                elif method == "PUT":
                    return "update"
                elif method == "POST":
                    return "create"
            else:
                # /resource/sub-resource/... -> join with dashes
                action_parts = [p for p in parts[1:] if "{" not in p]
                if action_parts:
                    return "-".join(action_parts)

        # Default actions based on method for base resource
        if method == "GET":
            return "list"
        elif method == "POST":
            return "create"
        elif method == "PUT":
            return "update"
        elif method == "DELETE":
            return "delete"
        else:
            return "run"

    def list_commands(self):
        """List all discovered commands"""
        commands = self.build_command_tree()

        total_commands = sum(len(actions) for actions in commands.values())

        print(f"\n🚀 Dumont Cloud CLI - {total_commands} comandos disponíveis\n")
        print("Usage: dumont <resource> <action> [args...]")
        print("-" * 70)

        for resource in sorted(commands.keys()):
            print(f"\n📦 {resource.upper()}")
            for action, info in sorted(commands[resource].items()):
                summary = info.get("summary", "")
                method = info.get("method", "")
                # Truncate long summaries
                if len(summary) > 45:
                    summary = summary[:42] + "..."
                print(f"  {action:25} [{method:6}] {summary}")

        print("\n" + "-" * 70)
        print("💡 Exemplos:")
        print("   dumont auth login <email> <password>")
        print("   dumont instance list")
        print("   dumont instance get <instance_id>")
        print("   dumont warmpool status <machine_id>")
        print("")

    def execute(self, resource: str, action: str, args: List[str]):
        """Execute a command"""
        if resource == "help" or (resource == "list" and not action):
            self.list_commands()
            return

        commands = self.build_command_tree()

        if resource not in commands:
            print(f"❌ Recurso desconhecido: {resource}")
            print(f"\n💡 Recursos disponíveis: {', '.join(sorted(commands.keys()))}")
            sys.exit(1)

        # Show help for resource when no action is provided
        if action is None or action not in commands[resource]:
            self._show_resource_help(resource, commands[resource], action)
            sys.exit(1 if action is not None else 0)

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
                    print(f"❌ Parâmetro obrigatório faltando: {param_name}")
                    print(f"\n💡 Uso: dumont {resource} {action} <{param_name}>")
                    sys.exit(1)
            args = args[len(path_params):]

        print(f"🔄 {method} {path}")

        # Parse request body (requestBody can be {} which is falsy, so check is not None)
        if cmd_info.get("requestBody") is not None and args:
            if args[0].startswith("{"):
                try:
                    data = json.loads(args[0])
                except json.JSONDecodeError as e:
                    print(f"❌ JSON inválido: {e}")
                    sys.exit(1)
            else:
                # Special handling for login
                if action == "login" and resource == "auth":
                    if len(args) >= 2:
                        data = {"username": args[0], "password": args[1]}
                    else:
                        print("❌ Uso: dumont auth login <email> <password>")
                        sys.exit(1)
                else:
                    # Parse key=value pairs
                    data = {}
                    for arg in args:
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
                            data[key] = value

        # Parse query parameters (for GET requests without body)
        if not data:
            for arg in args:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    params[key] = value

        self.api.call(method, path, data, params if params else None)
