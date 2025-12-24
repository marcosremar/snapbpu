"""Model Deploy CLI commands
Deploy and manage ML models (LLM, Whisper, Diffusion, Embeddings) via API
"""
import json
import sys
import time


class ModelsCommands:
    """Deploy and manage model endpoints"""

    def __init__(self, api_client):
        self.api = api_client

    def list(self):
        """List all deployed models"""
        print("\n📦 Deployed Models\n")
        print("=" * 70)

        response = self.api.call("GET", "/api/v1/models", silent=True)

        if not response:
            print("❌ Could not fetch models. Make sure you are logged in.")
            sys.exit(1)

        models = response.get("models", [])

        if not models:
            print("\n   No models deployed yet.")
            print("\n💡 Deploy a model:")
            print("   dumont models deploy llm meta-llama/Llama-3.1-8B-Instruct")
            print("   dumont models deploy whisper openai/whisper-large-v3")
            print("   dumont models deploy image stabilityai/stable-diffusion-xl-base-1.0")
            return

        for model in models:
            status_emoji = {
                "running": "🟢",
                "deploying": "🔵",
                "downloading": "🔵",
                "starting": "🔵",
                "stopped": "⚫",
                "error": "🔴",
            }.get(model.get("status", "pending"), "⚪")

            print(f"\n{status_emoji} {model.get('name', model.get('model_id', 'Unknown'))}")
            print(f"   ID:     {model.get('id')}")
            print(f"   Model:  {model.get('model_id')}")
            print(f"   Type:   {model.get('model_type')}")
            print(f"   Status: {model.get('status')} ({model.get('status_message', '')})")

            if model.get("status") == "running":
                print(f"   URL:    {model.get('endpoint_url')}")
                if model.get("access_type") == "private" and model.get("api_key"):
                    print(f"   Key:    {model.get('api_key')[:25]}...")
                print(f"   Cost:   ${model.get('dph_total', 0):.2f}/h")

            if model.get("status") in ["deploying", "downloading", "starting"]:
                print(f"   Progress: {model.get('progress', 0):.0f}%")

        print("\n" + "=" * 70)

    def templates(self):
        """List available templates"""
        print("\n📋 Available Model Templates\n")
        print("=" * 70)

        response = self.api.call("GET", "/api/v1/models/templates", silent=True)

        if not response:
            print("❌ Could not fetch templates.")
            sys.exit(1)

        templates = response.get("templates", [])

        for template in templates:
            type_emoji = {
                "llm": "🤖",
                "speech": "🎤",
                "image": "🎨",
                "embeddings": "📊",
            }.get(template.get("type", ""), "📦")

            print(f"\n{type_emoji} {template.get('name')}")
            print(f"   Type:    {template.get('type')}")
            print(f"   Runtime: {template.get('runtime')}")
            print(f"   Port:    {template.get('default_port')}")
            print(f"   GPU:     {template.get('gpu_memory_required')}GB+ required")
            print("\n   Popular models:")
            for model in template.get("popular_models", [])[:3]:
                print(f"     - {model.get('id')} ({model.get('size')})")

        print("\n" + "=" * 70)

    def deploy(self, model_type: str, model_id: str, **kwargs):
        """Deploy a new model"""
        print(f"\n🚀 Deploying {model_type} model: {model_id}\n")
        print("=" * 60)

        # Build payload
        payload = {
            "model_type": model_type,
            "model_id": model_id,
            "gpu_type": kwargs.get("gpu", "RTX 4090"),
            "num_gpus": int(kwargs.get("num_gpus", 1)),
            "max_price": float(kwargs.get("max_price", 2.0)),
            "access_type": kwargs.get("access", "private"),
            "port": int(kwargs.get("port", 8000)),
        }

        if kwargs.get("name"):
            payload["name"] = kwargs["name"]

        if kwargs.get("instance_id"):
            payload["instance_id"] = int(kwargs["instance_id"])

        response = self.api.call("POST", "/api/v1/models/deploy", json=payload, silent=True)

        if not response or not response.get("success"):
            error = response.get("detail", "Unknown error") if response else "Failed to connect"
            print(f"❌ Deploy failed: {error}")
            sys.exit(1)

        deployment_id = response.get("deployment_id")
        print(f"✅ Deployment started!")
        print(f"   ID: {deployment_id}")
        print(f"   Estimated time: ~{response.get('estimated_time_seconds', 180) // 60} minutes")

        # Wait for deployment
        if kwargs.get("wait", True):
            print("\n⏳ Waiting for deployment to complete...")
            self._wait_for_deployment(deployment_id)

        return deployment_id

    def _wait_for_deployment(self, deployment_id: str, timeout: int = 600):
        """Wait for deployment to complete"""
        start_time = time.time()
        last_progress = -1

        while time.time() - start_time < timeout:
            response = self.api.call("GET", f"/api/v1/models/{deployment_id}", silent=True)

            if not response:
                print("   ⚠ Could not check status")
                time.sleep(5)
                continue

            status = response.get("status")
            progress = response.get("progress", 0)
            message = response.get("status_message", "")

            # Print progress if changed
            if progress != last_progress:
                bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                print(f"\r   [{bar}] {progress:.0f}% - {message}", end="", flush=True)
                last_progress = progress

            if status == "running":
                print(f"\n\n✅ Deployment complete!")
                print(f"   Endpoint: {response.get('endpoint_url')}")
                if response.get("access_type") == "private" and response.get("api_key"):
                    print(f"   API Key:  {response.get('api_key')}")
                print(f"   Cost:     ${response.get('dph_total', 0):.2f}/h")
                return True

            if status == "error":
                print(f"\n\n❌ Deployment failed: {message}")
                return False

            time.sleep(5)

        print("\n\n⚠ Timeout waiting for deployment")
        return False

    def get(self, deployment_id: str):
        """Get deployment details"""
        response = self.api.call("GET", f"/api/v1/models/{deployment_id}", silent=True)

        if not response:
            print(f"❌ Deployment {deployment_id} not found")
            sys.exit(1)

        print(f"\n📦 Deployment Details\n")
        print("=" * 60)
        print(json.dumps(response, indent=2))

    def stop(self, deployment_id: str, force: bool = False):
        """Stop a running deployment"""
        print(f"\n⏹️ Stopping deployment {deployment_id}...")

        response = self.api.call(
            "POST",
            f"/api/v1/models/{deployment_id}/stop",
            json={"force": force},
            silent=True
        )

        if not response:
            print(f"❌ Failed to stop deployment")
            sys.exit(1)

        print(f"✅ Deployment stopped")

    def delete(self, deployment_id: str):
        """Delete a deployment"""
        print(f"\n🗑️ Deleting deployment {deployment_id}...")

        response = self.api.call(
            "DELETE",
            f"/api/v1/models/{deployment_id}",
            silent=True
        )

        # DELETE returns 204 No Content, so response may be empty
        print(f"✅ Deployment deleted")

    def logs(self, deployment_id: str):
        """Get deployment logs"""
        response = self.api.call("GET", f"/api/v1/models/{deployment_id}/logs", silent=True)

        if not response:
            print(f"❌ Could not fetch logs for {deployment_id}")
            sys.exit(1)

        print(f"\n📋 Logs for {deployment_id}\n")
        print("=" * 60)
        print(response.get("logs", "No logs available"))
