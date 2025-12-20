"""Model installation commands"""
import json
import sys
from ..utils.ssh_client import SSHClient


class ModelCommands:
    """Install and manage models on instances"""

    def __init__(self, api_client):
        self.api = api_client

    def install(self, instance_id: str, model_id: str):
        """Install Ollama and a model on a running instance"""
        print(f"\n🚀 Installing model '{model_id}' on instance {instance_id}\n")
        print("=" * 60)

        # Step 1: Get instance info
        print("\n📡 Step 1: Getting instance information...")
        instances = self.api.call("GET", "/api/v1/instances", silent=True)

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

        # Create SSH client
        ssh = SSHClient(public_ip, ssh_port)

        # Step 2: Install Ollama
        print("\n📦 Step 2: Installing Ollama...")

        install_script = '''#!/bin/bash
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

        success, stdout, stderr = ssh.execute(install_script, timeout=300)

        if "OLLAMA_INSTALL_COMPLETE=yes" in stdout:
            if "already_installed" in stdout:
                print("   ✓ Ollama already installed")
            else:
                print("   ✓ Ollama installed successfully")

            if "OLLAMA_RUNNING=yes" in stdout:
                print("   ✓ Ollama service running")
            else:
                print("   ⚠ Ollama service may not be running")
        else:
            print(f"   ⚠ Installation output: {stdout}")
            if stderr:
                print(f"   ⚠ Errors: {stderr}")

        # Step 3: Pull the model
        print(f"\n🤖 Step 3: Pulling model '{model_id}'...")
        print("   (This may take a while depending on model size)")

        pull_script = f'''#!/bin/bash

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

        success, stdout, stderr = ssh.execute(pull_script, timeout=1800)

        if "MODEL_PULL_SUCCESS=yes" in stdout:
            print(f"   ✓ Model '{model_id}' pulled successfully")
        else:
            print(f"   ❌ Failed to pull model")
            print(f"   Output: {stdout}")
            if stderr:
                print(f"   Errors: {stderr}")
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
        print(f"   SSH:        {ssh.get_connection_string()}")
        print(f"   Ollama API: {connection_info['ollama_url']}")
        print("-" * 40)

        print("\n🔧 Quick Test Commands:")
        print(f"   curl {connection_info['ollama_url']}/api/generate -d '{{\"model\": \"{model_id}\", \"prompt\": \"Hello!\"}}'")
        print(f"   {ssh.get_connection_string()} 'ollama run {model_id}'")

        print("\n" + json.dumps(connection_info, indent=2))

        return connection_info
