#!/bin/bash
# Dumont Cloud CLI - System Installation Script

set -e

echo "🚀 Installing Dumont Cloud CLI system-wide..."
echo ""

# Get the CLI directory (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_BIN="$SCRIPT_DIR/bin/dumont"

# Check if bin/dumont exists
if [ ! -f "$CLI_BIN" ]; then
    echo "❌ Error: bin/dumont not found in $SCRIPT_DIR"
    exit 1
fi

# Create the global command via symlink
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

COMMAND_NAME="dumont"
COMMAND_PATH="$BIN_DIR/$COMMAND_NAME"

echo "📝 Creating global command: $COMMAND_NAME"

# Remove old symlink/file if exists
rm -f "$COMMAND_PATH"

# Create symlink to bin/dumont
ln -s "$CLI_BIN" "$COMMAND_PATH"

echo "✅ Command created at: $COMMAND_PATH"
echo "   → Links to: $CLI_BIN"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  WARNING: $HOME/.local/bin is not in your PATH"
    echo ""
    echo "To fix this, add this line to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then run: source ~/.bashrc (or restart your terminal)"
    echo ""
else
    echo "✅ $HOME/.local/bin is already in PATH"
    echo ""
fi

echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✅ Installation Complete!"
echo ""
echo "You can now use 'dumont' from anywhere:"
echo ""
echo "  dumont instance list                 # List instances"
echo "  dumont auth login user@email.com ... # Login"
echo "  dumont wizard deploy 'RTX 4090'      # Deploy GPU"
echo "  dumont model install 12345 llama3.2  # Install model"
echo ""
echo "Quick start:"
echo "  dumont --help"
echo ""
echo "════════════════════════════════════════════════════════════════"
