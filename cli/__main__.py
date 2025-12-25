"""
Dumont Cloud CLI - Main entry point

Usage:
    dumont                           # Show help
    dumont config setup              # Configure API key
    dumont spot monitor              # Market data
    dumont instances list            # List instances
    dumont api GET /api/v1/health    # Direct API call
"""
import argparse
import sys
import os

from .utils.api_client import APIClient
from .commands.config import ConfigManager, ConfigCommands, ensure_configured
from .commands.api import APICommands, SmartRouter
from .commands.base import CommandBuilder
from .commands.wizard import WizardCommands
from .commands.model import ModelCommands
from .commands.models import ModelsCommands


def main():
    parser = argparse.ArgumentParser(
        prog="dumont",
        description="Dumont Cloud CLI - GPU Cloud Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  dumont config setup                # Configurar API key
  dumont spot monitor                # Ver preços de GPUs
  dumont spot predict RTX4090        # Previsão de preço
  dumont instances list              # Listar instâncias
  dumont api GET /api/v1/health      # Chamada direta à API

Comandos de Configuração:
  dumont config setup                # Setup interativo
  dumont config show                 # Mostrar configuração
  dumont config set-key <key>        # Definir API key
  dumont config set-url <url>        # Definir URL da API

Comandos de Mercado (Spot):
  dumont spot monitor                # Preços atuais
  dumont spot predict <gpu>          # Previsão de preço
  dumont spot reliability            # Confiabilidade de providers
  dumont spot llm-gpus               # GPUs recomendadas para LLM
  dumont spot training-cost          # Estimativa de custos

Comandos de Instâncias:
  dumont instances list              # Listar instâncias
  dumont instance get <id>           # Detalhes de instância
  dumont instance pause <id>         # Pausar instância
  dumont instance resume <id>        # Resumir instância

Comandos de Deploy:
  dumont wizard deploy               # Deploy rápido
  dumont models deploy llm <model>   # Deploy de modelo

API Direta:
  dumont api list                    # Listar todos endpoints
  dumont api GET /path               # GET request
  dumont api POST /path key=value    # POST request
        """
    )

    parser.add_argument(
        "--api-url",
        help="URL da API (default: ~/.dumont/config.json ou localhost:8000)"
    )

    parser.add_argument(
        "--api-key",
        help="API Key (default: ~/.dumont/config.json ou DUMONT_API_KEY)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug"
    )

    parser.add_argument("command", nargs="?", help="Comando ou recurso")
    parser.add_argument("subcommand", nargs="?", help="Subcomando ou ação")
    parser.add_argument("args", nargs="*", help="Argumentos adicionais")

    args = parser.parse_args()

    # Handle config commands (don't require API key)
    if args.command == "config":
        config_cmd = ConfigCommands()

        if args.subcommand == "setup" or args.subcommand is None:
            config_cmd.setup(
                api_key=args.args[0] if args.args else None,
                api_url=args.api_url
            )
            return

        if args.subcommand == "show":
            config_cmd.show()
            return

        if args.subcommand == "set-key":
            if not args.args:
                print("❌ Uso: dumont config set-key <api_key>")
                sys.exit(1)
            config_cmd.set_key(args.args[0])
            return

        if args.subcommand == "set-url":
            if not args.args:
                print("❌ Uso: dumont config set-url <url>")
                sys.exit(1)
            config_cmd.set_url(args.args[0])
            return

        if args.subcommand == "clear":
            config_cmd.clear()
            return

        print(f"❌ Subcomando desconhecido: {args.subcommand}")
        print("Disponíveis: setup, show, set-key, set-url, clear")
        sys.exit(1)

    # Handle help
    if args.command in (None, "help", "--help", "-h"):
        parser.print_help()
        return

    # Handle version
    if args.command in ("version", "--version", "-v"):
        print("Dumont Cloud CLI v1.0.0")
        return

    # For other commands, ensure configured (will prompt if needed)
    try:
        config = ensure_configured()
    except SystemExit:
        return

    # Get API URL and key
    api_url = args.api_url or config.get_api_url()
    api_key = args.api_key or config.get_api_key()

    # Create API client
    api = APIClient(base_url=api_url)
    if api_key:
        api.token_manager.save(api_key)

    # Handle direct API commands
    if args.command == "api":
        api_cmd = APICommands(api)
        all_args = [args.subcommand] if args.subcommand else []
        all_args.extend(args.args or [])
        api_cmd.execute(all_args)
        return

    # Handle wizard commands
    if args.command == "wizard":
        wizard = WizardCommands(api)
        if args.subcommand == "deploy" or args.subcommand is None:
            # Parse wizard args
            gpu_name = None
            speed = "fast"
            max_price = 2.0
            region = "global"

            for arg in args.args or []:
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
                    if not gpu_name:
                        gpu_name = arg

            if args.subcommand is None:
                print("🧙 Wizard Deploy - Quick GPU Provisioning")
                print("")
                print("Usage: dumont wizard deploy [gpu] [options]")
                print("")
                print("Options:")
                print("  gpu=<name>       GPU type (e.g., 'RTX 4090', 'A100')")
                print("  speed=<mode>     fast (default), slow, ultrafast")
                print("  price=<$>        Max price per hour (default: 2.0)")
                print("  region=<name>    Region filter (default: global)")
                return

            wizard.deploy(gpu_name=gpu_name, speed=speed, max_price=max_price, region=region)
            return

    # Handle model install
    if args.command == "model" and args.subcommand == "install":
        model = ModelCommands(api)
        if len(args.args or []) < 2:
            print("❌ Usage: dumont model install <instance_id> <model_id>")
            sys.exit(1)
        model.install(args.args[0], args.args[1])
        return

    # Handle models commands
    if args.command == "models":
        models_cmd = ModelsCommands(api)

        if args.subcommand == "list" or args.subcommand is None:
            models_cmd.list()
            return

        if args.subcommand == "templates":
            models_cmd.templates()
            return

        if args.subcommand == "deploy":
            if len(args.args or []) < 2:
                print("❌ Usage: dumont models deploy <type> <model_id> [options]")
                sys.exit(1)

            model_type = args.args[0]
            model_id = args.args[1]
            options = {}
            for arg in args.args[2:]:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    options[key] = value

            models_cmd.deploy(model_type, model_id, **options)
            return

        if args.subcommand in ("get", "stop", "delete", "logs"):
            if not args.args:
                print(f"❌ Usage: dumont models {args.subcommand} <deployment_id>")
                sys.exit(1)

            method = getattr(models_cmd, args.subcommand)
            method(args.args[0])
            return

    # Try smart routing for shortcuts
    router = SmartRouter(api)
    all_args = [args.command]
    if args.subcommand:
        all_args.append(args.subcommand)
    all_args.extend(args.args or [])

    if router.route(all_args):
        return

    # Fall back to command builder (OpenAPI discovery)
    builder = CommandBuilder(api)
    builder.execute(args.command, args.subcommand, args.args or [])


if __name__ == "__main__":
    main()
