#!/bin/bash
# =============================================================================
# DumontCloud - Test Runner (Layered Execution)
# =============================================================================
#
# Executa testes em camadas para máxima eficiência:
#   1. MOCKS (rápidos, sem custo)
#   2. GPU REAL - SHARED (paralelo, 1 máquina compartilhada)
#   3. GPU REAL - LIFECYCLE (SEQUENCIAL para evitar rate limit)
#
# USO:
#   ./scripts/run_tests.sh           # Executa todas as camadas
#   ./scripts/run_tests.sh mock      # Apenas mocks
#   ./scripts/run_tests.sh gpu       # Apenas GPU real (shared + lifecycle)
#   ./scripts/run_tests.sh quick     # Mocks + smoke tests
#   ./scripts/run_tests.sh full      # Todas as camadas + relatório
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Activate virtualenv if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Default parallelism
MOCK_WORKERS=10
SHARED_WORKERS=4
# LIFECYCLE_WORKERS=1 to avoid Vast.ai 429 rate limit
LIFECYCLE_WORKERS=1

# Timing
START_TIME=$(date +%s)

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

calculate_duration() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    echo "${minutes}m ${seconds}s"
}

# =============================================================================
# Test Layers
# =============================================================================

run_mock_tests() {
    print_header "LAYER 1: MOCK TESTS (Fast, No Cost)"
    print_info "Workers: $MOCK_WORKERS | Timeout: 30s"

    pytest tests/backend/api/ \
        -v \
        --tb=short \
        -m "not real" \
        --ignore=tests/backend/api/test_gpu_real.py \
        -n $MOCK_WORKERS \
        --timeout=30 \
        "$@"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_success "Mock tests PASSED"
    else
        print_error "Mock tests FAILED"
        return $exit_code
    fi
}

run_shared_gpu_tests() {
    print_header "LAYER 2a: SHARED GPU TESTS (Parallel, 1 Shared Machine)"
    print_info "Workers: $SHARED_WORKERS | Timeout: 600s | Cost: ~\$0.01"

    pytest tests/backend/api/test_gpu_real.py \
        -v \
        --tb=short \
        -m "uses_shared_machine" \
        -n $SHARED_WORKERS \
        --timeout=600 \
        "$@"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_success "Shared GPU tests PASSED"
    else
        print_error "Shared GPU tests FAILED"
        return $exit_code
    fi
}

run_lifecycle_gpu_tests() {
    print_header "LAYER 2b: LIFECYCLE GPU TESTS (Sequential to Avoid Rate Limit)"
    print_info "Workers: $LIFECYCLE_WORKERS | Timeout: 600s | Cost: ~\$0.01"
    print_warning "Running sequentially to avoid Vast.ai 429 rate limit"

    pytest tests/backend/api/test_gpu_real.py \
        -v \
        --tb=short \
        -m "creates_machine" \
        -n $LIFECYCLE_WORKERS \
        --timeout=600 \
        "$@"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_success "Lifecycle GPU tests PASSED"
    else
        print_error "Lifecycle GPU tests FAILED"
        return $exit_code
    fi
}

run_gpu_tests() {
    print_header "LAYER 2: GPU REAL TESTS"
    print_warning "This will use REAL Vast.ai credits!"

    local shared_failed=0
    local lifecycle_failed=0

    # Shared tests (parallel)
    run_shared_gpu_tests "$@" || shared_failed=1

    # Lifecycle tests (sequential to avoid rate limit)
    run_lifecycle_gpu_tests "$@" || lifecycle_failed=1

    if [ $shared_failed -eq 0 ] && [ $lifecycle_failed -eq 0 ]; then
        print_success "All GPU tests PASSED"
        return 0
    else
        print_error "Some GPU tests FAILED"
        return 1
    fi
}

run_smoke_tests() {
    print_header "SMOKE TESTS (Critical Paths Only)"

    pytest tests/backend/api/ \
        -v \
        --tb=short \
        -m "smoke or critical" \
        -n $MOCK_WORKERS \
        --timeout=30 \
        "$@"
}

run_all_layers() {
    print_header "FULL TEST SUITE - ALL LAYERS"

    local mock_failed=0
    local shared_failed=0
    local lifecycle_failed=0

    # Layer 1: Mocks
    run_mock_tests || mock_failed=1

    if [ $mock_failed -eq 1 ]; then
        print_error "Mock tests failed. Stopping execution."
        print_error "Fix mock tests before running GPU tests (saves money!)."
        return 1
    fi

    # Layer 2a: GPU Shared (parallel)
    run_shared_gpu_tests || shared_failed=1

    # Layer 2b: GPU Lifecycle (sequential)
    run_lifecycle_gpu_tests || lifecycle_failed=1

    # Summary
    print_header "TEST SUMMARY"
    echo ""

    if [ $mock_failed -eq 0 ]; then
        print_success "  Mock Tests:      PASSED"
    else
        print_error "  Mock Tests:      FAILED"
    fi

    if [ $shared_failed -eq 0 ]; then
        print_success "  GPU Shared:      PASSED"
    else
        print_error "  GPU Shared:      FAILED"
    fi

    if [ $lifecycle_failed -eq 0 ]; then
        print_success "  GPU Lifecycle:   PASSED"
    else
        print_error "  GPU Lifecycle:   FAILED"
    fi

    echo ""
    print_info "Total Duration: $(calculate_duration)"

    if [ $mock_failed -eq 0 ] && [ $shared_failed -eq 0 ] && [ $lifecycle_failed -eq 0 ]; then
        print_success "ALL TESTS PASSED!"
        return 0
    else
        print_error "SOME TESTS FAILED"
        return 1
    fi
}

run_quick() {
    print_header "QUICK TESTS (Mocks + Smoke)"
    run_mock_tests
    print_info "Duration: $(calculate_duration)"
}

run_full_with_report() {
    print_header "FULL TEST SUITE WITH HTML REPORT"

    local report_dir="reports/tests"
    mkdir -p "$report_dir"

    local timestamp=$(date +%Y%m%d_%H%M%S)

    # Run all layers with HTML report
    run_mock_tests --html="$report_dir/mock_${timestamp}.html" --self-contained-html || true
    run_shared_gpu_tests --html="$report_dir/shared_${timestamp}.html" --self-contained-html || true
    run_lifecycle_gpu_tests --html="$report_dir/lifecycle_${timestamp}.html" --self-contained-html || true

    print_info "Reports saved to: $report_dir/"
    print_info "Duration: $(calculate_duration)"
}

# =============================================================================
# Usage
# =============================================================================

show_usage() {
    echo ""
    echo "DumontCloud Test Runner - Layered Execution"
    echo ""
    echo "Usage: $0 [command] [pytest-options]"
    echo ""
    echo "Commands:"
    echo "  (none)    Run all layers (mock -> shared -> lifecycle)"
    echo "  mock      Run mock tests only (fast, no cost)"
    echo "  gpu       Run GPU real tests (shared parallel + lifecycle sequential)"
    echo "  shared    Run shared GPU tests only (parallel, 1 machine)"
    echo "  lifecycle Run lifecycle GPU tests only (sequential, avoids rate limit)"
    echo "  smoke     Run smoke tests only"
    echo "  quick     Run mock + smoke tests"
    echo "  full      Run all layers + HTML report"
    echo "  help      Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                        # All layers"
    echo "  $0 mock                   # Only mocks"
    echo "  $0 gpu                    # Shared + lifecycle"
    echo "  $0 lifecycle -k pause     # Lifecycle tests matching 'pause'"
    echo "  $0 mock --lf              # Re-run last failed mocks"
    echo ""
    echo "Environment Variables:"
    echo "  MOCK_WORKERS=10       Workers for mock tests (parallel)"
    echo "  SHARED_WORKERS=4      Workers for shared GPU tests (parallel)"
    echo "  LIFECYCLE_WORKERS=1   Workers for lifecycle tests (sequential)"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Override defaults from environment
    MOCK_WORKERS=${MOCK_WORKERS:-10}
    SHARED_WORKERS=${SHARED_WORKERS:-4}
    LIFECYCLE_WORKERS=${LIFECYCLE_WORKERS:-1}

    case "${1:-}" in
        mock)
            shift
            run_mock_tests "$@"
            ;;
        gpu)
            shift
            run_gpu_tests "$@"
            ;;
        shared)
            shift
            run_shared_gpu_tests "$@"
            ;;
        lifecycle)
            shift
            run_lifecycle_gpu_tests "$@"
            ;;
        smoke)
            shift
            run_smoke_tests "$@"
            ;;
        quick)
            shift
            run_quick "$@"
            ;;
        full)
            shift
            run_full_with_report "$@"
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            run_all_layers "$@"
            ;;
    esac
}

main "$@"
