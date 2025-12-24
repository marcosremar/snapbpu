"""Main entry point for Dumont CLI"""
import argparse
import os
import sys

from .utils.api_client import APIClient, DEFAULT_API_URL
from .commands.base import CommandBuilder
from .commands.wizard import WizardCommands
from .commands.model import ModelCommands
from .commands.models import ModelsCommands


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

  # Model Deployment (with API endpoint)
  dumont models list                     # List deployed models
  dumont models templates                # Show available templates
  dumont models deploy llm meta-llama/Llama-3.1-8B-Instruct
  dumont models deploy speech openai/whisper-large-v3
  dumont models deploy image stabilityai/stable-diffusion-xl-base-1.0
  dumont models stop <deployment_id>     # Stop a deployment
  dumont models delete <deployment_id>   # Delete a deployment

  # Model Installation (Ollama on instance)
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

  # Snapshots
  dumont snapshot list
  dumont snapshot create name=backup instance_id=12345
        """
    )

    parser.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Base URL of the API (default: {DEFAULT_API_URL}, env: DUMONT_API_URL)"
    )

    parser.add_argument("resource", nargs="?", help="Resource (instance, wizard, model, auth, etc)")
    parser.add_argument("action", nargs="?", help="Action (list, deploy, install, etc)")
    parser.add_argument("args", nargs="*", help="Additional arguments")

    args = parser.parse_args()

    # Create API client
    api = APIClient(base_url=args.base_url)

    # Get resource and action
    resource = args.resource or "help"
    action = args.action

    # Handle wizard commands
    if resource == "wizard":
        wizard = WizardCommands(api)

        if action == "deploy" or action is None:
            gpu_name = None
            speed = "fast"
            max_price = 2.0
            region = "global"
            machine_type = "on-demand"

            for arg in args.args:
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
                    elif key == "type":
                        machine_type = value
                else:
                    # First positional arg is GPU name
                    if not gpu_name:
                        gpu_name = arg

            if action is None:
                # Show help
                print("🧙 Wizard Deploy - Quick GPU Provisioning")
                print("")
                print("Usage: dumont wizard deploy [gpu] [options]")
                print("")
                print("Options:")
                print("  gpu=<name>       GPU type (e.g., 'RTX 4090', 'A100')")
                print("  speed=<mode>     fast (default), slow, ultrafast")
                print("  price=<$>        Max price per hour (default: 2.0)")
                print("  region=<name>    Region filter (default: global)")
                print("  type=<mode>      on-demand (default), spot")
                print("")
                print("Examples:")
                print("  dumont wizard deploy                    # Any GPU, fast")
                print("  dumont wizard deploy 'RTX 4090'         # Specific GPU")
                print("  dumont wizard deploy gpu=A100 price=3   # A100, max $3/hr")
                print("  dumont wizard deploy type=spot          # Spot instance")
                return

            wizard.deploy(gpu_name=gpu_name, speed=speed, max_price=max_price, region=region)
            return

        print(f"❌ Unknown wizard action: {action}")
        print("Available: deploy")
        sys.exit(1)

    if resource == "model" and action == "install":
        model = ModelCommands(api)
        if len(args.args) < 2:
            print("❌ Usage: dumont model install <instance_id> <model_id>")
            print("")
            print("Examples:")
            print("  dumont model install 12345 llama3.2")
            print("  dumont model install 12345 qwen3:0.6b")
            print("  dumont model install 12345 codellama:7b")
            sys.exit(1)

        model.install(args.args[0], args.args[1])
        return

    # Handle models commands (deploy, list, etc)
    if resource == "models":
        models_cmd = ModelsCommands(api)

        if action == "list" or action is None:
            models_cmd.list()
            return

        if action == "templates":
            models_cmd.templates()
            return

        if action == "deploy":
            if len(args.args) < 2:
                print("❌ Usage: dumont models deploy <type> <model_id> [options]")
                print("")
                print("Types: llm, speech, image, embeddings, vision, video")
                print("")
                print("Examples:")
                print("  dumont models deploy llm meta-llama/Llama-3.1-8B-Instruct")
                print("  dumont models deploy speech openai/whisper-large-v3")
                print("  dumont models deploy image stabilityai/stable-diffusion-xl-base-1.0")
                print("  dumont models deploy embeddings BAAI/bge-large-en-v1.5")
                print("  dumont models deploy vision HuggingFaceTB/SmolVLM-256M-Instruct")
                print("  dumont models deploy video damo-vilab/text-to-video-ms-1.7b")
                print("")
                print("Options:")
                print("  gpu=<type>       GPU type (default: RTX 4090)")
                print("  num_gpus=<n>     Number of GPUs (default: 1)")
                print("  max_price=<$>    Max price per hour (default: 2.0)")
                print("  access=<type>    private or public (default: private)")
                print("  port=<n>         Port (default: 8000)")
                print("  name=<name>      Deployment name")
                sys.exit(1)

            model_type = args.args[0]
            model_id = args.args[1]

            # Parse options
            options = {}
            for arg in args.args[2:]:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    options[key] = value

            models_cmd.deploy(model_type, model_id, **options)
            return

        if action == "get":
            if len(args.args) < 1:
                print("❌ Usage: dumont models get <deployment_id>")
                sys.exit(1)
            models_cmd.get(args.args[0])
            return

        if action == "stop":
            if len(args.args) < 1:
                print("❌ Usage: dumont models stop <deployment_id>")
                sys.exit(1)
            force = "--force" in args.args or "force=true" in args.args
            models_cmd.stop(args.args[0], force=force)
            return

        if action == "delete":
            if len(args.args) < 1:
                print("❌ Usage: dumont models delete <deployment_id>")
                sys.exit(1)
            models_cmd.delete(args.args[0])
            return

        if action == "logs":
            if len(args.args) < 1:
                print("❌ Usage: dumont models logs <deployment_id>")
                sys.exit(1)
            models_cmd.logs(args.args[0])
            return

        print(f"❌ Unknown models action: {action}")
        print("Available: list, templates, deploy, get, stop, delete, logs")
        sys.exit(1)

    # Handle regular API commands
    builder = CommandBuilder(api)
    builder.execute(resource, action, args.args)


if __name__ == "__main__":
    main()
