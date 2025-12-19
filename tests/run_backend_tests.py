#!/usr/bin/env python3
"""
Script de Execução Unificada - Testes Backend Dumont Cloud

Executa todos os testes backend de forma organizada com:
- Relatórios consolidados
- Cache inteligente
- Paralelização opcional
- Filtros por módulo
- Configurações de ambiente

Uso:
    python tests/run_backend_tests.py                    # Todos os testes
    python tests/run_backend_tests.py --module auth     # Apenas auth
    python tests/run_backend_tests.py --parallel 4      # Paralelo
    python tests/run_backend_tests.py --no-cache        # Sem cache
    python tests/run_backend_tests.py --report json     # Relatório JSON
"""

import subprocess
import sys
import os
import time
import json
import argparse
from pathlib import Path
from datetime import datetime


class TestRunner:
    """Executor unificado de testes backend"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_tests_dir = self.project_root / "backend"
        self.start_time = None
        self.end_time = None

    def get_available_modules(self):
        """Retorna lista de módulos disponíveis"""
        if not self.backend_tests_dir.exists():
            return []

        modules = []
        for item in self.backend_tests_dir.iterdir():
            if item.is_dir() and (item / f"test_{item.name}.py").exists():
                modules.append(item.name)

        return sorted(modules)

    def run_module_tests(self, module, use_cache=True, parallel=1, verbose=True):
        """Executa testes de um módulo específico"""
        test_file = self.backend_tests_dir / module / f"test_{module}.py"

        if not test_file.exists():
            print(f"❌ Módulo {module} não encontrado")
            return None

        # Configurar variáveis de ambiente
        env = os.environ.copy()
        env["TEST_CACHE"] = "true" if use_cache else "false"
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

        # Comando pytest
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v" if verbose else "-q",
            "--tb=short",
            f"-n{parallel}" if parallel > 1 else "",
            "--disable-warnings"
        ]

        # Remover elementos vazios
        cmd = [arg for arg in cmd if arg]

        print(f"🚀 Executando testes do módulo: {module}")
        print(f"   Arquivo: {test_file}")
        print(f"   Cache: {'habilitado' if use_cache else 'desabilitado'}")
        print(f"   Paralelo: {parallel} processo(s)")

        start_time = time.time()
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            env=env,
            capture_output=True,
            text=True
        )
        end_time = time.time()

        return {
            "module": module,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": end_time - start_time,
            "success": result.returncode == 0
        }

    def run_all_tests(self, use_cache=True, parallel=1, verbose=True, modules=None):
        """Executa todos os testes ou módulos específicos"""
        self.start_time = time.time()

        available_modules = self.get_available_modules()
        if not available_modules:
            print("❌ Nenhum módulo de teste encontrado")
            return {}

        # Filtrar módulos se especificado
        if modules:
            test_modules = [m for m in modules if m in available_modules]
            if not test_modules:
                print(f"❌ Nenhum dos módulos especificados encontrado: {modules}")
                return {}
        else:
            test_modules = available_modules

        print("=" * 60)
        print("🏗️  Dumont Cloud - Testes Backend")
        print("=" * 60)
        print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Diretório: {self.project_root}")
        print(f"📦 Módulos: {len(test_modules)} encontrados")
        print(f"🧵 Paralelo: {parallel} processo(s)")
        print(f"💾 Cache: {'habilitado' if use_cache else 'desabilitado'}")
        print("=" * 60)

        results = {}
        success_count = 0
        total_duration = 0

        for module in test_modules:
            print(f"\n🔍 Testando módulo: {module}")
            print("-" * 40)

            result = self.run_module_tests(module, use_cache, parallel, verbose)
            if result:
                results[module] = result
                total_duration += result["duration"]

                if result["success"]:
                    success_count += 1
                    print("✅ SUCESSO")
                else:
                    print("❌ FALHA")
                    print(f"   Código: {result['returncode']}")

                print(".2f"                # Mostrar output se falhou e verbose
                if not result["success"] and verbose:
                    if result["stderr"]:
                        print(f"   Erro: {result['stderr'].strip()}")
                    if result["stdout"]:
                        print(f"   Output: {result['stdout'].strip()[:500]}...")

        self.end_time = time.time()

        # Resumo final
        self.print_summary(results, success_count, total_duration)

        return results

    def print_summary(self, results, success_count, total_duration):
        """Imprime resumo dos testes"""
        print("\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES")
        print("=" * 60)

        total_modules = len(results)
        success_rate = (success_count / total_modules * 100) if total_modules > 0 else 0

        print(".2f"        print(".2f"        print(".1f"        print("=" * 60)

        # Detalhes por módulo
        if results:
            print("📋 DETALHES POR MÓDULO:")
            for module, result in results.items():
                status = "✅" if result["success"] else "❌"
                print(".2f"
        print("=" * 60)

        # Status final
        if success_count == total_modules:
            print("🎉 TODOS OS TESTES PASSARAM!")
        else:
            print(f"⚠️  {total_modules - success_count} módulo(s) com falha(s)")

    def generate_report(self, results, format="text"):
        """Gera relatório dos testes"""
        if format == "json":
            report_file = self.project_root / f"backend_test_report_{int(time.time())}.json"
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_modules": len(results),
                    "successful_modules": len([r for r in results.values() if r["success"]]),
                    "total_duration": sum(r["duration"] for r in results.values()),
                    "success_rate": len([r for r in results.values() if r["success"]]) / len(results) * 100 if results else 0
                },
                "results": results
            }

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            print(f"📄 Relatório JSON salvo: {report_file}")

        elif format == "html":
            # Implementar relatório HTML se necessário
            print("📄 Relatório HTML não implementado ainda")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Executor de testes backend Dumont Cloud")
    parser.add_argument("--module", "-m", nargs="+",
                       help="Módulos específicos para testar")
    parser.add_argument("--parallel", "-p", type=int, default=1,
                       help="Número de processos paralelos")
    parser.add_argument("--no-cache", action="store_true",
                       help="Desabilitar cache inteligente")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Modo quiet (menos output)")
    parser.add_argument("--report", choices=["text", "json", "html"], default="text",
                       help="Formato do relatório")
    parser.add_argument("--list-modules", action="store_true",
                       help="Listar módulos disponíveis")

    args = parser.parse_args()

    runner = TestRunner()

    # Listar módulos se solicitado
    if args.list_modules:
        modules = runner.get_available_modules()
        print("📦 Módulos disponíveis:")
        for module in modules:
            print(f"  • {module}")
        return

    # Executar testes
    use_cache = not args.no_cache
    verbose = not args.quiet

    results = runner.run_all_tests(
        use_cache=use_cache,
        parallel=args.parallel,
        verbose=verbose,
        modules=args.module
    )

    # Gerar relatório se solicitado
    if args.report != "text":
        runner.generate_report(results, args.report)

    # Exit code baseado nos resultados
    success_count = len([r for r in results.values() if r["success"]])
    total_count = len(results)
    sys.exit(0 if success_count == total_count else 1)


if __name__ == "__main__":
    main()
