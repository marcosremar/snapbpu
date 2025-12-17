#!/bin/bash
# Start Dumont Cloud FastAPI Application

echo "🚀 Starting Dumont Cloud FastAPI..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing FastAPI dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements-fastapi.txt

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run FastAPI
echo ""
echo "✓ Starting FastAPI on http://0.0.0.0:8767"
echo "  API Docs: http://localhost:8767/docs"
echo "  Health: http://localhost:8767/health"
echo ""

uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8767 \
    --reload \
    --log-level info
