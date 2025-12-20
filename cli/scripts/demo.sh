#!/bin/bash
# Test script for CLI demos

echo "🚀 DUMONT CLOUD CLI - DEMO AUTOMÁTICO"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. Testando Health Check...${NC}"
./dc call GET /api/health
echo ""

echo -e "${BLUE}2. Testando Login...${NC}"
./dc call POST /api/auth/login --data '{"username":"marcosremar@gmail.com","password":"123456"}'
echo ""

echo -e "${BLUE}3. Verificando Autenticação...${NC}"
./dc call GET /api/auth/me
echo ""

echo -e "${BLUE}4. Listando Instâncias GPU...${NC}"
./dc call GET /api/instances
echo ""

echo -e "${BLUE}5. Listando Snapshots...${NC}"
./dc call GET /api/snapshots
echo ""

echo -e "${GREEN}✅ Demo Completo!${NC}"
echo ""
echo "💡 Para ver todos os endpoints: ./dc list"
echo "📖 Para ver o guia completo: ./cli-help.sh"
