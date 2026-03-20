#!/bin/bash
# Deploy Script — Comunidades AI-Only
# Usage: ./deploy.sh [staging|production]

set -e

ENV=${1:-staging}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Comunidades AI-Only to $ENV"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate environment
if [[ "$ENV" != "staging" && "$ENV" != "production" ]]; then
    echo -e "${RED}Error: Environment must be 'staging' or 'production'${NC}"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker not found${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose not found${NC}"
    exit 1
fi

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "📝 Loading environment from .env"
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found, using defaults${NC}"
fi

# Pre-deploy checks
echo "🔍 Pre-deploy checks..."

# Check if ports are available
if lsof -Pi :8765 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Port 8765 is already in use${NC}"
fi

if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Port 8080 is already in use${NC}"
fi

# Backup data if exists
if [ -d "$PROJECT_DIR/data" ]; then
    BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    echo "💾 Creating backup at $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -r "$PROJECT_DIR/data" "$BACKUP_DIR/"
fi

# Build and deploy
echo "🏗️ Building images..."
cd "$PROJECT_DIR"
docker-compose build --no-cache

echo "🚀 Starting services..."
if [ "$ENV" == "production" ]; then
    # Production: detached mode with restart
    docker-compose up -d
    
    # Health check
    echo "🏥 Health check..."
    sleep 5
    
    if curl -s http://localhost:8080/stats > /dev/null; then
        echo -e "${GREEN}✅ API is healthy${NC}"
    else
        echo -e "${RED}❌ API health check failed${NC}"
        docker-compose logs api
        exit 1
    fi
else
    # Staging: foreground for debugging
    docker-compose up
fi

# Post-deploy
echo ""
echo "========================================"
echo -e "${GREEN}✅ Deploy completed!${NC}"
echo ""
echo "Services:"
echo "  Relay (WebSocket):  ws://localhost:8765"
echo "  API (HTTP):         http://localhost:8080"
echo ""
echo "Commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop:         docker-compose down"
echo "  Restart:      docker-compose restart"
echo ""
echo "========================================"
