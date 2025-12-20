#!/usr/bin/env python3
"""
Dumont Cloud CLI - Natural Commands
Automatically maps OpenAPI endpoints to natural CLI commands
"""
import argparse
import json
import sys
import requests
import subprocess
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
from pathlib import Path
import re
import os


TOKEN_FILE = Path.home() / ".dumont_token"
CONFIG_FILE = Path.home() / ".dumont_config"


class DumontCLI:
    def __init__(self, base_url: str = "http://localhost:8766"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.commands: Dict[str, Any] = {}
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication if available"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def load_token(self) -> Optional[str]:
        """Load saved token from file"""
        if TOKEN_FILE.exists():
            self.token = TOKEN_FILE.read_text().strip()
            return self.token
        return None

    def save_token(self, token: str):
        """Save token to file"""
        TOKEN_FILE.write_text(token)
        self.token = token

    def clear_token(self):
        """Remove saved token"""
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        self.token = None

    def get_vast_api_key(self) -> Optional[str]:
        """Get Vast API key from config or environment"""
        # Try environment variable first
        api_key = os.environ.get('VAST_API_KEY')
        if api_key:
            return api_key
        
        # Try config file
        if CONFIG_FILE.exists():
            try:
                config = json.loads(CONFIG_FILE.read_text())
                return config.get('vast_api_key')
            except:
                pass
        
        # Try to get from API
        try:
            result = self.call_api_silent("GET", "/api/v1/settings")
            if result:
                return result.get('vast_api_key')
        except:
            pass
        
        return None

    def call_api(self, method: str, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API call and handle response"""
        if not self.token:
            self.load_token()

        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=data, params=params)
            elif method == "PUT":
                response = self.session.put(url, headers=headers, json=data, params=params)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, params=params)
            else:
                print(f"❌ Unsupported method: {method}")
                sys.exit(1)

            if response.status_code == 401:
                print("❌ Unauthorized. Please login first: dumont auth login <email> <password>")
                sys.exit(1)

            if response.status_code == 404:
                print(f"❌ Not found: {path}")
                sys.exit(1)

            try:
                result = response.json()

                if "login" in path and ("access_token" in result or "token" in result):
                    token = result.get("access_token") or result.get("token")
                    self.save_token(token)
                    print(f"✅ Login successful! Token saved to {TOKEN_FILE}")
                    return result

                if "logout" in path:
                    self.clear_token()
                    print("✅ Logged out successfully.")
                    return result

                if response.ok:
                    print(f"✅ Success ({response.status_code})")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    return result
                else:
                    print(f"❌ Error ({response.status_code})")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    return None

            except json.JSONDecodeError:
                if response.ok:
                    print(f"✅ Success ({response.status_code})")
                    print(response.text)
                    return {"raw": response.text}
                else:
                    print(f"❌ Error ({response.status_code}): {response.text}")
                    return None

        except requests.exceptions.ConnectionError:
            print(f"❌ Could not connect to {self.base_url}")
            print("   Make sure the backend is running.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

    def call_api_silent(self, method: str, path: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API call without printing (for internal use)"""
        if not self.token:
            self.load_token()

        url = f"{self.base_url}{path}"
        headers = self._get_headers()

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=data, params=params)
            else:
                return None

            if response.ok:
                return response.json()
            return None
        except:
            return None

    def wizard_deploy(self, gpu_name: str = None, speed: str = "fast", max_price: float = 2.0, region: str = "global"):
        """
        Deploy a GPU instance using the wizard strategy.
        
        Strategy:
        1. Search for offers matching criteria
        2. Create batch of 5 machines in parallel
        3. Wait up to 90s for any to become ready
        4. If none ready, try another batch (up to 3 batches)
        5. First machine with SSH ready wins, others are destroyed
        """
        print(f"\n🚀 Wizard Deploy Starting\n")
        print("=" * 60)
        print(f"   GPU:       {gpu_name or 'Any'}")
        print(f"   Speed:     {speed}")
        print(f"   Max Price: ${max_price}/hr")
        print(f"   Region:    {region}")
        print("=" * 60)
        
        # Import the wizard service
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            from src.services.deploy_wizard import DeployWizardService, DeployConfig, SPEED_TIERS, BATCH_SIZE, MAX_BATCHES, BATCH_TIMEOUT
        except ImportError as e:
            print(f"❌ Could not import wizard service: {e}")
            print("   Make sure you're running from the dumontcloud directory")
            sys.exit(1)
        
        # Get API key
        api_key = self.get_vast_api_key()
        if not api_key:
            print("❌ No Vast.ai API key found")
            print("   Set VAST_API_KEY environment variable or configure via settings")
            sys.exit(1)
        
        print(f"\n📡 Step 1: Searching for offers...")
        
        # Create wizard service
        wizard = DeployWizardService(api_key)
        
        # Create config
        config = DeployConfig(
            speed_tier=speed,
            gpu_name=gpu_name,
            region=region,
            max_price=max_price,
            disk_space=50,
            setup_codeserver=True,
        )
        
        # Get offers
        offers = wizard.get_offers(config)
        
        if not offers:
            print("❌ No offers found matching criteria")
            print("💡 Try relaxing filters (higher price, different GPU, different region)")
            sys.exit(1)
        
        print(f"   ✓ Found {len(offers)} offers")
        
        # Show top 5 offers
        print("\n   Top offers:")
        for i, offer in enumerate(offers[:5]):
            print(f"   {i+1}. {offer.get('gpu_name')} - ${offer.get('dph_total', 0):.3f}/hr - {offer.get('inet_down', 0):.0f} Mbps")
        
        # Start deploy
        print(f"\n🔄 Step 2: Starting multi-start deployment...")
        print(f"   Strategy: Create {BATCH_SIZE} machines per batch, up to {MAX_BATCHES} batches")
        print(f"   Timeout: {BATCH_TIMEOUT}s per batch")
        
        job = wizard.start_deploy(config)
        
        # Poll for completion
        start_time = time.time()
        last_status = None
        
        while True:
            job = wizard.get_job(job.id)
            
            if job.status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"\n   [{elapsed}s] Status: {job.status}")
                print(f"   {job.message}")
                
                if job.status == 'creating':
                    print(f"   Batch {job.batch}/{MAX_BATCHES} - Machines created: {len(job.machines_created)}")
                elif job.status == 'waiting':
                    print(f"   Machines created: {job.machines_created}")
                
                last_status = job.status
            
            if job.status in ['completed', 'failed']:
                break
            
            time.sleep(2)
        
        # Handle result
        print("\n" + "=" * 60)
        
        if job.status == 'failed':
            print(f"❌ Deploy failed: {job.error}")
            print(f"\n   Machines tried: {job.machines_tried}")
            print(f"   Machines created: {len(job.machines_created)}")
            print(f"   Machines destroyed: {len(job.machines_destroyed)}")
            sys.exit(1)
        
        result = job.result
        print(f"\n✅ Deploy Complete!\n")
        print(f"📋 Instance Details:")
        print("-" * 40)
        print(f"   Instance ID: {result['instance_id']}")
        print(f"   GPU:         {result.get('gpu_name', 'Unknown')}")
        print(f"   IP:          {result['public_ip']}")
        print(f"   SSH Port:    {result['ssh_port']}")
        print(f"   Price:       ${result.get('dph_total', 0):.3f}/hr")
        print(f"   Speed:       {result.get('inet_down', 0):.0f} Mbps")
        print(f"   Ready in:    {result.get('ready_time', 0):.1f}s")
        print("-" * 40)
        print(f"\n🔗 SSH Command:")
        print(f"   {result['ssh_command']}")
        
        if result.get('codeserver_port'):
            print(f"\n💻 Code Server:")
            print(f"   http://{result['public_ip']}:{result['codeserver_port']}")
        
        # Save instance ID for later use
        print(f"\n💾 Instance ID saved: {result['instance_id']}")
        
        return result

    def install_model(self, instance_id: str, model_id: str):
        """Install Ollama and a model on a running instance"""
        print(f"\n🚀 Installing model '{model_id}' on instance {instance_id}\n")
        print("=" * 60)
        
        # Step 1: Get instance info
        print("\n📡 Step 1: Getting instance information...")
        instances = self.call_api_silent("GET", "/api/v1/instances")
        
        if not instances:
            print("❌ Could not fetch instances. Make sure you are logged in.")
            sys.exit(1)
        
        # Find the instance
        instance = None
        instance_list = instances.get("instances", instances) if isinstance(instances, dict) else instances
        
        for inst in instance_list:
            if str(inst.get("id")) == str(instance_id):
                instance = inst
                break
        
        if not instance:
            print(f"❌ Instance {instance_id} not found")
            print(f"💡 Available instances: {[i.get('id') for i in instance_list]}")
            sys.exit(1)
        
        # Check if running
        status = instance.get("actual_status", instance.get("status", "unknown"))
        if status != "running":
            print(f"❌ Instance is not running (status: {status})")
            print("💡 Start the instance first: dumont instance resume " + instance_id)
            sys.exit(1)
        
        # Get SSH connection info
        public_ip = instance.get("public_ipaddr") or instance.get("ssh_host")
        ssh_port = instance.get("ssh_port")
        
        # Try to get from ports mapping if not directly available
        if not ssh_port:
            ports = instance.get("ports", {})
            ssh_port_info = ports.get("22/tcp", [])
            if ssh_port_info:
                ssh_port = ssh_port_info[0].get("HostPort")
        
        if not public_ip or not ssh_port:
            print("❌ Could not get SSH connection info")
            print(f"   IP: {public_ip}, Port: {ssh_port}")
            sys.exit(1)
        
        print(f"   ✓ Instance found: {instance.get('gpu_name', 'GPU')} @ {public_ip}:{ssh_port}")
        
        # Step 2: Install Ollama
        print("\n📦 Step 2: Installing Ollama...")
        
        install_script = '''
#!/bin/bash
set -e

echo ">>> Checking for Ollama..."
if command -v ollama &> /dev/null; then
    echo "OLLAMA_STATUS=already_installed"
    ollama --version 2>/dev/null || echo "OLLAMA_VERSION=unknown"
else
    echo ">>> Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    echo "OLLAMA_STATUS=installed"
fi

# Start Ollama service if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo ">>> Starting Ollama service..."
    nohup ollama serve > /var/log/ollama.log 2>&1 &
    sleep 3
fi

# Verify Ollama is running
if pgrep -x "ollama" > /dev/null; then
    echo "OLLAMA_RUNNING=yes"
else
    echo "OLLAMA_RUNNING=no"
fi

echo "OLLAMA_INSTALL_COMPLETE=yes"
'''
        
        try:
            result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
                 '-p', str(ssh_port), f'root@{public_ip}', install_script],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if "OLLAMA_INSTALL_COMPLETE=yes" in result.stdout:
                if "already_installed" in result.stdout:
                    print("   ✓ Ollama already installed")
                else:
                    print("   ✓ Ollama installed successfully")
                
                if "OLLAMA_RUNNING=yes" in result.stdout:
                    print("   ✓ Ollama service running")
                else:
                    print("   ⚠ Ollama service may not be running")
            else:
                print(f"   ⚠ Installation output: {result.stdout}")
                if result.stderr:
                    print(f"   ⚠ Errors: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print("❌ Installation timed out")
            sys.exit(1)
        except Exception as e:
            print(f"❌ SSH error: {e}")
            sys.exit(1)
        
        # Step 3: Pull the model
        print(f"\n🤖 Step 3: Pulling model '{model_id}'...")
        print("   (This may take a while depending on model size)")
        
        pull_script = f'''
#!/bin/bash

# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    nohup ollama serve > /var/log/ollama.log 2>&1 &
    sleep 3
fi

echo ">>> Pulling model: {model_id}"
ollama pull {model_id}
PULL_STATUS=$?

if [ $PULL_STATUS -eq 0 ]; then
    echo "MODEL_PULL_SUCCESS=yes"
    echo "MODEL_NAME={model_id}"
else
    echo "MODEL_PULL_SUCCESS=no"
    echo "MODEL_PULL_ERROR=$PULL_STATUS"
fi

# List installed models
echo ">>> Installed models:"
ollama list
'''
        
        try:
            result = subprocess.run(
                ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30',
                 '-p', str(ssh_port), f'root@{public_ip}', pull_script],
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if "MODEL_PULL_SUCCESS=yes" in result.stdout:
                print(f"   ✓ Model '{model_id}' pulled successfully")
            else:
                print(f"   ❌ Failed to pull model")
                print(f"   Output: {result.stdout}")
                if result.stderr:
                    print(f"   Errors: {result.stderr}")
                sys.exit(1)
                
        except subprocess.TimeoutExpired:
            print("❌ Model pull timed out (>30 minutes)")
            sys.exit(1)
        except Exception as e:
            print(f"❌ SSH error: {e}")
            sys.exit(1)
        
        # Step 4: Get connection info
        print("\n" + "=" * 60)
        print("\n✅ Installation Complete!\n")
        
        ollama_port = "11434"
        
        connection_info = {
            "instance_id": instance_id,
            "model": model_id,
            "host": public_ip,
            "ssh_port": ssh_port,
            "ollama_port": ollama_port,
            "ollama_url": f"http://{public_ip}:{ollama_port}",
            "gpu": instance.get("gpu_name", "Unknown"),
            "status": "ready"
        }
        
        print("📋 Connection Details:")
        print("-" * 40)
        print(f"   Model:      {model_id}")
        print(f"   GPU:        {connection_info['gpu']}")
        print(f"   Host:       {public_ip}")
        print(f"   SSH:        ssh -p {ssh_port} root@{public_ip}")
        print(f"   Ollama API: {connection_info['ollama_url']}")
        print("-" * 40)
        
        print("\n🔧 Quick Test Commands:")
        print(f"   curl {connection_info['ollama_url']}/api/generate -d '{{\"model\": \"{model_id}\", \"prompt\": \"Hello!\"}}'")
        print(f"   ssh -p {ssh_port} root@{public_ip} 'ollama run {model_id}'")
        
        print("\n" + json.dumps(connection_info, indent=2))
        
        return connection_info

    def load_openapi_schema(self) -> Dict[str, Any]:
        """Load OpenAPI schema from FastAPI"""
        try:
            endpoints = ["/api/v1/openapi.json", "/openapi.json"]
            for endpoint in endpoints:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.HTTPError:
                    continue
            print(f"❌ Could not find OpenAPI schema")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading API schema: {e}")
            sys.exit(1)
    
    def build_command_tree(self) -> Dict[str, Any]:
        """Build command tree from OpenAPI schema with manual overrides"""
        schema = self.load_openapi_schema()
        paths = schema.get("paths", {})
        
        commands = {}
        
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
                "offers": ["GET", "/api/v1/instances/offers"],
            },
            "snapshot": {
                "list": ["GET", "/api/v1/snapshots"],
                "create": ["POST", "/api/v1/snapshots"],
                "restore": ["POST", "/api/v1/snapshots/restore"],
                "delete": ["DELETE", "/api/v1/snapshots/{snapshot_id}"],
            },
            "model": {
                "install": ["LOCAL", "install_model"],
            },
            "wizard": {
                "deploy": ["LOCAL", "wizard_deploy"],
            }
        }

        for resource, actions in overrides.items():
            if resource not in commands:
                commands[resource] = {}
            for action, info in actions.items():
                if info[0] == "LOCAL":
                    commands[resource][action] = {
                        "method": "LOCAL",
                        "handler": info[1],
                        "summary": f"Local command: {info[1]}",
                        "parameters": [],
                    }
                else:
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

        for path, methods in paths.items():
            parts = [p for p in path.split("/") if p and p not in ["api", "v1"]]
            if not parts: continue
            
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
        
        return commands

    def list_all_commands(self):
        """List all discovered commands in a readable way"""
        commands = self.build_command_tree()
        print("\n🚀 Dumont Cloud - Command Reference\n")
        print("Usage: dumont <resource> <action> [args...]")
        print("-" * 60)
        
        for resource in sorted(commands.keys()):
            print(f"\n📦 {resource.upper()}")
            for action, info in sorted(commands[resource].items()):
                summary = info.get("summary", "")
                if resource == "model" and action == "install":
                    summary = "Install Ollama + model on instance"
                if resource == "wizard" and action == "deploy":
                    summary = "Deploy GPU with multi-start wizard"
                print(f"  - {action:15} {summary}")
                
        print("\n" + "-" * 60)
        print("Type 'dumont --help' for examples.\n")

    def execute_command(self, resource: str, action: str, args: List[str]):
        """Execute a natural command or special command"""
        if resource == "help" or (resource == "list" and not action):
            self.list_all_commands()
            return

        # Handle wizard deploy
        if resource == "wizard" and action == "deploy":
            gpu_name = None
            speed = "fast"
            max_price = 2.0
            region = "global"
            
            for arg in args:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    if key == "gpu":
                        gpu_name = value
                    elif key == "speed":
                        speed = value
                    elif key == "price":
                        max_price = float(value)
                    elif key == "region":
                        region = value
                else:
                    # First positional arg is GPU name
                    if not gpu_name:
                        gpu_name = arg
            
            self.wizard_deploy(gpu_name=gpu_name, speed=speed, max_price=max_price, region=region)
            return

        # Handle model install
        if resource == "model" and action == "install":
            if len(args) < 2:
                print("❌ Usage: dumont model install <instance_id> <model_id>")
                print("")
                print("Examples:")
                print("  dumont model install 12345 llama3.2")
                print("  dumont model install 12345 qwen3:0.6b")
                print("  dumont model install 12345 codellama:7b")
                sys.exit(1)
            
            self.install_model(args[0], args[1])
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
        
        if cmd_info.get("method") == "LOCAL":
            print(f"❌ Local command not fully implemented: {cmd_info.get('handler')}")
            return
        
        method = cmd_info["method"]
        path = cmd_info["path"]

        params = {}
        data = {}

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
        
        if cmd_info.get("requestBody"):
            if args:
                if args[0].startswith("{"):
                    data = json.loads(args[0])
                else:
                    if action == "create" and resource == "instance":
                        if len(args) >= 1:
                            if args[0] == "wizard":
                                data["use_wizard"] = True
                                if len(args) > 1:
                                    data["gpu_name"] = args[1]
                            else:
                                data["gpu_name"] = args[0]
                            for arg in args[1:]:
                                if "=" in arg:
                                    key, value = arg.split("=", 1)
                                    data[key] = value
                    elif action == "login":
                        if len(args) >= 2:
                            data["username"] = args[0]
                            data["password"] = args[1]
                    else:
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
        
        for arg in args:
            if "=" in arg and arg not in data:
                key, value = arg.split("=", 1)
                params[key] = value
        
        self.call_api(method, path, data if data else None, params if params else None)


def main():
    parser = argparse.ArgumentParser(
        description="Dumont Cloud CLI - Natural Commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Wizard Deploy (multi-start strategy)
  dumont wizard deploy                          # Deploy any GPU
  dumont wizard deploy "RTX 4090"               # Deploy specific GPU
  dumont wizard deploy gpu="RTX 4090" speed=fast price=1.5
  
  # Model Installation
  dumont model install <instance_id> <model_id>
  dumont model install 12345 llama3.2
  dumont model install 12345 qwen3:0.6b

  # Instances
  dumont instance list
  dumont instance get 12345
  dumont instance pause 12345
  dumont instance resume 12345
  dumont instance delete 12345

  # Authentication
  dumont auth login user@email.com password
  dumont auth me
        """
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:8766",
        help="Base URL of the API"
    )
    
    parser.add_argument("resource", nargs="?", help="Resource (instance, wizard, model, auth, etc)")
    parser.add_argument("action", nargs="?", help="Action (list, deploy, install, etc)")
    parser.add_argument("args", nargs="*", help="Additional arguments")
    
    args = parser.parse_args()
    
    cli = DumontCLI(base_url=args.base_url)
    
    resource = args.resource or "help"
    action = args.action
    
    cli.execute_command(resource, action, args.args)


if __name__ == "__main__":
    main()
