#!/bin/bash

# NetResolve Setup Script

set -e

echo "=========================================="
echo "NetResolve Setup"
echo "=========================================="

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION found"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip setuptools wheel
pip install -q -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Create necessary directories
mkdir -p logs
mkdir -p postgres_data
mkdir -p prometheus_data
mkdir -p grafana_data

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start services: docker-compose up -d"
echo "2. Initialize database: python scripts/init_db.py"
echo "3. Run tests: pytest tests/"
echo "4. Start API: uvicorn app.main:app --reload"
echo ""
