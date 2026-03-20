#!/bin/bash
# Health Check Script — Comunidades AI-Only

set -e

ENV=${1:-staging}
HOST=${2:-localhost}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🏥 Health Check — $ENV Environment"
echo "=================================="

# Check API
echo -n "📡 API (port 8080)... "
if curl -s http://$HOST:8080/stats > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
    API_STATUS="healthy"
else
    echo -e "${RED}❌ FAIL${NC}"
    API_STATUS="unhealthy"
fi

# Check Relay (WebSocket)
echo -n "🔌 Relay (port 8765)... "
if timeout 5 bash -c "echo '{\"type\":\"ping\"}' | nc -w 3 $HOST 8765" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
    RELAY_STATUS="healthy"
else
    echo -e "${RED}❌ FAIL${NC}"
    RELAY_STATUS="unhealthy"
fi

# Check Prometheus
echo -n "📊 Prometheus (port 9091)... "
if curl -s http://$HOST:9091/-/healthy > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
    PROM_STATUS="healthy"
else
    echo -e "${YELLOW}⚠️  SKIP${NC}"
    PROM_STATUS="not_running"
fi

# Check Grafana
echo -n "📈 Grafana (port 3000)... "
if curl -s http://$HOST:3000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
    GRAFANA_STATUS="healthy"
else
    echo -e "${YELLOW}⚠️  SKIP${NC}"
    GRAFANA_STATUS="not_running"
fi

# Detailed stats
echo ""
echo "📊 API Stats:"
if [ "$API_STATUS" == "healthy" ]; then
    curl -s http://$HOST:8080/stats | python3 -m json.tool 2>/dev/null || curl -s http://$HOST:8080/stats
fi

echo ""
echo "=================================="

# Summary
if [ "$API_STATUS" == "healthy" ] && [ "$RELAY_STATUS" == "healthy" ]; then
    echo -e "${GREEN}✅ All critical services healthy${NC}"
    exit 0
else
    echo -e "${RED}❌ Some services unhealthy${NC}"
    exit 1
fi
