#!/bin/bash
# Setup Script — Comunidades AI-Only
# Usage: ./setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 Setting up Comunidades AI-Only"
echo "=================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create directories
echo "📁 Creating directories..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/data/index"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/backups"

# Check Python version
echo "🐍 Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "Found Python $PYTHON_VERSION"
    
    if [[ "$PYTHON_VERSION" < "3.9" ]]; then
        echo -e "${YELLOW}Warning: Python 3.9+ recommended${NC}"
    fi
else
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

# Setup virtual environment
echo "🌿 Setting up virtual environment..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi

# Activate and install dependencies
echo "📦 Installing dependencies..."
source "$PROJECT_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/sdk/python/requirements.txt"

echo -e "${GREEN}✅ Dependencies installed${NC}"

# Create .env if not exists
echo "⚙️  Configuration..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env with your configuration${NC}"
else
    echo -e "${YELLOW}.env file already exists${NC}"
fi

# Make scripts executable
echo "🔐 Setting permissions..."
chmod +x "$PROJECT_DIR/scripts/"*.sh

# Run tests
echo "🧪 Running tests..."
cd "$PROJECT_DIR"
if python -m pytest tests/ -v --tb=short 2>/dev/null; then
    echo -e "${GREEN}✅ Tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed (this is OK for initial setup)${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo ""
echo -e "${BLUE}1. Edit configuration:${NC}"
echo "   nano .env"
echo ""
echo -e "${BLUE}2. Start locally:${NC}"
echo "   python api/relay_server.py --port 8765"
echo "   python api/indexer_service.py --api-port 8080"
echo ""
echo -e "${BLUE}3. Or use Docker:${NC}"
echo "   docker-compose up -d"
echo ""
echo -e "${BLUE}4. Test:${NC}"
echo "   curl http://localhost:8080/stats"
echo ""
echo "=================================="
