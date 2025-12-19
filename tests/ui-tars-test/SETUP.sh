#!/bin/bash

# ByteDance UI-TARS Setup Script
# This script sets up the environment for running UI-TARS tests

set -e

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║            ByteDance UI-TARS Testing Environment Setup                ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}[1/5] Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
else
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi

# Install Playwright
echo -e "\n${BLUE}[2/5] Installing Playwright...${NC}"
if pip show playwright &> /dev/null; then
    echo -e "${GREEN}✓ Playwright already installed${NC}"
else
    echo -e "${YELLOW}  Installing Playwright...${NC}"
    pip install playwright
    echo -e "${GREEN}✓ Playwright installed${NC}"
fi

# Install Playwright browsers
echo -e "\n${BLUE}[3/5] Installing Playwright browsers...${NC}"
if [ -d "$HOME/.cache/ms-playwright" ]; then
    BROWSER_COUNT=$(find $HOME/.cache/ms-playwright -name "chrome-linux" -o -name "firefox-linux" | wc -l)
    if [ $BROWSER_COUNT -gt 0 ]; then
        echo -e "${GREEN}✓ Browsers already installed${NC}"
    else
        echo -e "${YELLOW}  Installing browsers...${NC}"
        playwright install chromium
        echo -e "${GREEN}✓ Browsers installed${NC}"
    fi
else
    echo -e "${YELLOW}  Installing browsers...${NC}"
    playwright install chromium
    echo -e "${GREEN}✓ Browsers installed${NC}"
fi

# Install requests (for OpenRouter API)
echo -e "\n${BLUE}[4/5] Checking dependencies...${NC}"
if pip show requests &> /dev/null; then
    echo -e "${GREEN}✓ Requests library installed${NC}"
else
    echo -e "${YELLOW}  Installing requests...${NC}"
    pip install requests
    echo -e "${GREEN}✓ Requests installed${NC}"
fi

# Check for OpenRouter API key
echo -e "\n${BLUE}[5/5] Checking OpenRouter configuration...${NC}"
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${YELLOW}⚠ OpenRouter API key not set${NC}"
    echo -e "${YELLOW}  (Optional for AI-powered tests)${NC}"
    echo -e "${YELLOW}  To enable: export OPENROUTER_API_KEY='your-key'${NC}"
else
    echo -e "${GREEN}✓ OpenRouter API key configured${NC}"
fi

# Summary
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete!${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}Next Steps:${NC}"
echo -e "  1. Make sure the server is running:"
echo -e "     ${YELLOW}export DEMO_MODE=true${NC}"
echo -e "     ${YELLOW}python -m uvicorn src.main:app --host 0.0.0.0 --port 8000${NC}"
echo -e ""
echo -e "  2. Run comprehensive tests:"
echo -e "     ${YELLOW}python ui_tars_comprehensive_test.py${NC}"
echo -e ""
echo -e "  3. Or run AI-powered tests (requires OpenRouter key):"
echo -e "     ${YELLOW}export OPENROUTER_API_KEY='your-key'${NC}"
echo -e "     ${YELLOW}python ui_tars_openrouter.py${NC}"
echo -e ""
echo -e "  4. View results:"
echo -e "     ${YELLOW}cat /tmp/ui_tars_test_report.md${NC}"
echo -e ""
echo -e "${BLUE}Documentation:${NC}"
echo -e "  - README.md - Full documentation"
echo -e "  - INDEX.md - Quick reference and results"
echo -e "  - USAGE_EXAMPLES.md - Usage examples and scenarios"
echo -e ""
echo -e "${GREEN}Ready to test! 🚀${NC}"
