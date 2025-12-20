"""Main entry point for Dumont CLI"""
import argparse
import sys

from .utils.api_client import APIClient
from .commands.base import CommandBuilder
from .commands.wizard import WizardCommands
from .commands.model import ModelCommands


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

  # Snapshots
  dumont snapshot list
  dumont snapshot create name=backup instance_id=12345
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

    # Create API client
    api = APIClient(base_url=args.base_url)

    # Get resource and action
    resource = args.resource or "help"
    action = args.action

    # Handle special commands
    if resource == "wizard" and action == "deploy":
        wizard = WizardCommands(api)
        gpu_name = None
        speed = "fast"
        max_price = 2.0
        region = "global"

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
            else:
                # First positional arg is GPU name
                if not gpu_name:
                    gpu_name = arg

        wizard.deploy(gpu_name=gpu_name, speed=speed, max_price=max_price, region=region)
        return

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

    # Handle regular API commands
    builder = CommandBuilder(api)
    builder.execute(resource, action, args.args)


if __name__ == "__main__":
    main()
