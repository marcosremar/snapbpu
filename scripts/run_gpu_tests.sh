#!/bin/bash
# =============================================================================
# GPU Test Runner - Dumont Cloud
# =============================================================================
#
# COST-OPTIMIZED TEST EXECUTION:
#
# This script runs GPU tests with MAXIMUM PARALLELISM while MINIMIZING COST:
#
#   1. LIFECYCLE tests (creates_machine) -> 4 parallel workers
#      Each test creates its own GPU, so parallelism = faster completion
#
#   2. SHARED tests (uses_shared_machine) -> 1 worker, 1 GPU for all
#      All 9 tests share a single GPU = ~$0.02 total!
#
#   3. Both groups run SIMULTANEOUSLY in background processes!
#
# COST ESTIMATE:
#   - Lifecycle tests: 4 tests x $0.03 = ~$0.12
#   - Shared tests: 9 tests on 1 GPU = ~$0.02
#   - TOTAL: ~$0.15 per full run (vs $0.40+ without optimization)
#
# Usage:
#   ./scripts/run_gpu_tests.sh              # Optimized parallel run (DEFAULT)
#   ./scripts/run_gpu_tests.sh parallel     # Same as above
#   ./scripts/run_gpu_tests.sh lifecycle    # Only lifecycle tests (4 workers)
#   ./scripts/run_gpu_tests.sh shared       # Only shared tests (1 worker)
#   ./scripts/run_gpu_tests.sh cleanup      # Cleanup orphaned instances
#   ./scripts/run_gpu_tests.sh all-serial   # All tests serially (old mode)
#
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
MODE=${1:-"parallel"}
LIFECYCLE_WORKERS=${LIFECYCLE_WORKERS:-2}
TEST_FILE="tests/backend/api/test_gpu_real.py"
TIMEOUT=${TIMEOUT:-600}
LOG_DIR="/tmp/gpu_tests_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$LOG_DIR"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  GPU Test Runner - Dumont Cloud${NC}"
echo -e "${BLUE}  Cost-Optimized Parallel Execution${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

# Check if running remotely or locally
if [ -f ".env" ]; then
    echo -e "${GREEN}Running locally${NC}"
    # Export all variables from .env so they're available to pytest subprocess
    set -a  # automatically export all variables
    source .env 2>/dev/null || true
    set +a  # stop auto-exporting
else
    echo -e "${YELLOW}Running via SSH to dumontcloud-local${NC}"
fi

echo -e "  Mode: ${GREEN}$MODE${NC}"
echo -e "  Logs: ${YELLOW}$LOG_DIR${NC}"
echo -e "  Timeout: ${TIMEOUT}s"
echo ""

# Function definitions
run_lifecycle_tests() {
    echo -e "${GREEN}[LIFECYCLE]${NC} Starting $LIFECYCLE_WORKERS parallel lifecycle tests..."
    echo -e "  Each test creates its own GPU machine"
    python3 -m pytest "$TEST_FILE" \
        -v \
        --timeout=$TIMEOUT \
        -n $LIFECYCLE_WORKERS \
        -m "creates_machine" \
        2>&1 | tee "$LOG_DIR/lifecycle.log"
}

run_shared_tests() {
    echo -e "${GREEN}[SHARED]${NC} Starting shared machine tests (1 GPU for all 9 tests)..."
    echo -e "  Cost: ~\$0.02 total!"
    echo -e "  Note: Running WITHOUT xdist to share session fixture properly"
    # CRITICAL: We must disable xdist plugin completely!
    # The pytest.ini has 'addopts = -n 10' which forces parallelism.
    # With xdist, each worker gets its own session = multiple GPUs = expensive!
    # With -p no:xdist, all tests share the same session = 1 GPU for all tests = cheap!
    # We also need -o addopts="" to clear the -n 10 from pytest.ini
    python3 -m pytest "$TEST_FILE" \
        -v \
        --timeout=$TIMEOUT \
        -p no:xdist \
        -o "addopts=" \
        -m "uses_shared_machine" \
        2>&1 | tee "$LOG_DIR/shared.log"
}

run_cleanup() {
    echo -e "${YELLOW}Cleaning up orphaned test instances...${NC}"
    python3 -c "
import os
import requests

api_key = os.environ.get('VAST_API_KEY', '')
if not api_key:
    print('VAST_API_KEY not set')
    exit(0)

resp = requests.get(
    'https://console.vast.ai/api/v0/instances/',
    headers={'Authorization': f'Bearer {api_key}'},
    timeout=30
)
if not resp.ok:
    print(f'Could not fetch instances: {resp.status_code}')
    exit(0)

instances = resp.json().get('instances', [])
destroyed = 0
for inst in instances:
    label = inst.get('label', '') or ''
    if label.startswith('dumont:test:') or label.startswith('pytest-'):
        inst_id = inst.get('id')
        gpu = inst.get('gpu_name', 'unknown')
        print(f'Destroying {inst_id} ({gpu})...')
        del_resp = requests.delete(
            f'https://console.vast.ai/api/v0/instances/{inst_id}/',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30
        )
        if del_resp.ok:
            destroyed += 1
            print('  Destroyed')

print(f'Cleaned up {destroyed} instances')
"
}

case $MODE in
    "parallel"|"optimized")
        echo -e "${YELLOW}Running OPTIMIZED parallel execution...${NC}"
        echo -e "${GREEN}Lifecycle tests${NC}: 4 workers in parallel"
        echo -e "${GREEN}Shared tests${NC}: 1 worker (all tests share 1 GPU)"
        echo ""

        # Start both in parallel
        run_lifecycle_tests &
        LIFECYCLE_PID=$!

        sleep 3  # Small delay to avoid API rate limiting

        run_shared_tests &
        SHARED_PID=$!

        echo -e "${BLUE}Both test groups running in parallel:${NC}"
        echo -e "  Lifecycle PID: $LIFECYCLE_PID"
        echo -e "  Shared PID: $SHARED_PID"
        echo ""

        # Wait for both
        LIFECYCLE_EXIT=0
        SHARED_EXIT=0
        wait $LIFECYCLE_PID || LIFECYCLE_EXIT=$?
        wait $SHARED_PID || SHARED_EXIT=$?

        # Summary
        echo ""
        echo -e "${BLUE}=============================================${NC}"
        echo -e "${BLUE}  SUMMARY${NC}"
        echo -e "${BLUE}=============================================${NC}"

        if [ $LIFECYCLE_EXIT -eq 0 ]; then
            echo -e "  ${GREEN}[LIFECYCLE]${NC} PASSED"
        else
            echo -e "  ${RED}[LIFECYCLE]${NC} FAILED (exit $LIFECYCLE_EXIT)"
        fi

        if [ $SHARED_EXIT -eq 0 ]; then
            echo -e "  ${GREEN}[SHARED]${NC} PASSED"
        else
            echo -e "  ${RED}[SHARED]${NC} FAILED (exit $SHARED_EXIT)"
        fi

        echo ""
        echo -e "  Logs: ${YELLOW}$LOG_DIR/${NC}"

        if [ $LIFECYCLE_EXIT -ne 0 ] || [ $SHARED_EXIT -ne 0 ]; then
            exit 1
        fi
        ;;

    "lifecycle")
        run_lifecycle_tests
        ;;

    "shared")
        run_shared_tests
        ;;

    "cleanup")
        run_cleanup
        ;;

    "all-serial")
        echo -e "${YELLOW}Running all tests serially (expensive!)...${NC}"
        python3 -m pytest "$TEST_FILE" -v --timeout=$TIMEOUT -n 1
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo ""
        echo "Available modes:"
        echo "  parallel   - Optimized parallel execution (DEFAULT, cheapest)"
        echo "  lifecycle  - Only lifecycle tests (4 workers)"
        echo "  shared     - Only shared tests (1 worker, 1 GPU)"
        echo "  cleanup    - Cleanup orphaned instances"
        echo "  all-serial - All tests serially (expensive)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}  GPU Tests Complete${NC}"
echo -e "${GREEN}=============================================${NC}"

# Always run cleanup check
echo ""
run_cleanup
