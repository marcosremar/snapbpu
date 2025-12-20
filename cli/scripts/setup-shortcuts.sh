#!/bin/bash
# Dumont Cloud CLI - Enhanced with natural command shortcuts

set -e

echo "🚀 Setting up Dumont CLI shortcuts (Natural Commands)..."
echo ""

# Add aliases to bashrc
BASHRC="$HOME/.bashrc"
ALIASES_MARKER="# Dumont Cloud CLI Aliases"

# Remove old aliases if they exist
sed -i "/$ALIASES_MARKER/,/^$/d" "$BASHRC" 2>/dev/null || true

echo "📝 Adding aliases to ~/.bashrc"
cat >> "$BASHRC" << 'EOF'

# Dumont Cloud CLI Aliases
alias dm='dumont'

# Authentication
alias dmlogin='dumont auth login'
alias dmme='dumont auth me'
alias dmlogout='dumont auth logout'

# Instances
alias dmls='dumont instance list'
alias dmcreate='dumont instance create'
alias dmget='dumont instance get'
alias dmrm='dumont instance delete'
alias dmpause='dumont instance pause'
alias dmresume='dumont instance resume'

# Snapshots
alias dmsnap='dumont snapshot list'
alias dmsnap-create='dumont snapshot create'
alias dmsnap-restore='dumont snapshot restore'

# Settings
alias dmconfig='dumont setting list'

# Quick login function (if you want shortcut)
dml() {
    dumont auth login "$1" "$2"
}

EOF
echo "✅ Aliases added!"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✅ Setup Complete!"
echo ""
echo "Available natural commands:"
echo ""
echo "Authentication:"
echo "  dumont auth login user@email.com password"
echo "  dumont auth me"
echo "  dmlogin user@email.com password      # alias"
echo "  dmme                                 # alias"
echo ""
echo "Instances:"
echo "  dumont instance list"
echo "  dumont instance create wizard rtx4090"
echo "  dumont instance create rtx4090 num_gpus=2"
echo "  dumont instance get 12345"
echo "  dumont instance delete 12345"
echo "  dumont instance pause 12345"
echo "  dumont instance resume 12345"
echo ""
echo "Shortcuts:"
echo "  dmls                    # list instances"
echo "  dmcreate wizard rtx4090 # create with wizard"
echo "  dmget 12345             # get instance"
echo "  dmrm 12345              # delete instance"
echo ""
echo "Snapshots:"
echo "  dumont snapshot list"
echo "  dumont snapshot create backup-1"
echo "  dmsnap                  # list snapshots"
echo "  dmsnap-create backup-1  # create snapshot"
echo ""
echo "To activate aliases now:"
echo "  source ~/.bashrc"
echo ""
echo "════════════════════════════════════════════════════════════════"
