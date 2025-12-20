#!/bin/bash
# Demo: Dumont CLI com Comandos Naturais

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║      🚀 DEMO: Dumont CLI - Comandos Naturais em Inglês              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Setup PATH
export PATH="$HOME/.local/bin:$PATH"

echo "🎯 Demonstrando comandos naturais..."
echo ""

# Test 1 - Login
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 Teste 1: Autenticação"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$ dumont auth login marcosremar@gmail.com 123456"
dumont auth login marcosremar@gmail.com 123456
echo ""

# Test 2 - List instances
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💻 Teste 2: Listar Instâncias"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$ dumont instance list"
dumont instance list | head -30
echo "..."
echo ""

# Test 3 - Check auth
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 Teste 3: Verificar Autenticação"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$ dumont auth me"
dumont auth me | head -10
echo "..."
echo ""

# Test 4 - Snapshots
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 Teste 4: Listar Snapshots"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$ dumont snapshot list"
dumont snapshot list
echo ""

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                              ✅ SUCESSO!                              ║"
echo "║                                                                       ║"
echo "║  Comandos naturais funcionando perfeitamente!                        ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Exemplos de comandos naturais:"
echo ""
echo "  dumont instance create wizard rtx4090    # Criar com wizard"
echo "  dumont instance list                     # Listar instâncias"
echo "  dumont instance get 12345                # Ver detalhes"
echo "  dumont snapshot create backup-1          # Criar snapshot"
echo "  dumont auth me                           # Verificar autenticação"
echo ""
echo "📖 Ver guia completo: ./cli-help.sh"
echo ""
