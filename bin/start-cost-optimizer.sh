#!/bin/bash
# Start Cost Optimizer Daemon

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Carregar .env se existir
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Valores padrão
export PAUSE_THRESHOLD_GPU="${PAUSE_THRESHOLD_GPU:-10}"
export DELETE_THRESHOLD_HOURS="${DELETE_THRESHOLD_HOURS:-24}"
export CHECK_INTERVAL="${CHECK_INTERVAL:-60}"

echo "=========================================="
echo "  DumontCloud Cost Optimizer"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  - Pause threshold: ${PAUSE_THRESHOLD_GPU}% GPU utilization"
echo "  - Delete after: ${DELETE_THRESHOLD_HOURS}h idle"
echo "  - Check interval: ${CHECK_INTERVAL}s"
echo ""
echo "Providers:"
[ -n "$VAST_API_KEY" ] && echo "  ✓ Vast.ai"
[ -n "$TENSORDOCK_API_KEY" ] && echo "  ✓ TensorDock"
[ -n "$GCP_PROJECT_ID" ] && echo "  ✓ GCP ($GCP_PROJECT_ID)"
echo ""
echo "Starting daemon..."
echo ""

cd "$PROJECT_DIR"
python3 services/cost_optimizer.py
