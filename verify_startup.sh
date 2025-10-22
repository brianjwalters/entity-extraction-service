#!/bin/bash
# Entity Extraction Service - Startup Verification Script
# This script verifies the service can start and all endpoints are operational

set -e

SERVICE_NAME="luris-entity-extraction"
SERVICE_PORT=8007
SERVICE_HOST="localhost"
HEALTH_ENDPOINT="http://${SERVICE_HOST}:${SERVICE_PORT}/api/v1/health"
PATTERNS_ENDPOINT="http://${SERVICE_HOST}:${SERVICE_PORT}/api/v1/patterns"
EXTRACT_ENDPOINT="http://${SERVICE_HOST}:${SERVICE_PORT}/api/v1/extract"

echo "============================================="
echo "Entity Extraction Service - Startup Test"
echo "============================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error
error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# Function to print warning
warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to print info
info() {
    echo "ℹ $1"
}

# Step 1: Check if service is running
info "Step 1: Checking service status..."
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
    success "Service is running"
else
    warning "Service is not running. Attempting to start..."
    sudo systemctl start ${SERVICE_NAME}
    sleep 5
    if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
        success "Service started successfully"
    else
        error "Failed to start service"
    fi
fi

# Step 2: Wait for service initialization
info "Step 2: Waiting for service initialization (15 seconds)..."
sleep 15

# Step 3: Check health endpoint
info "Step 3: Checking health endpoint..."
HEALTH_RESPONSE=$(curl -s ${HEALTH_ENDPOINT})
HEALTH_STATUS=$(echo ${HEALTH_RESPONSE} | jq -r '.status' 2>/dev/null || echo "error")

if [ "$HEALTH_STATUS" = "healthy" ]; then
    success "Health endpoint responding: ${HEALTH_STATUS}"
    SERVICE_VERSION=$(echo ${HEALTH_RESPONSE} | jq -r '.service_version')
    UPTIME=$(echo ${HEALTH_RESPONSE} | jq -r '.uptime_seconds')
    info "  Service version: ${SERVICE_VERSION}"
    info "  Uptime: ${UPTIME} seconds"
else
    error "Health endpoint failed: ${HEALTH_STATUS}"
fi

# Step 4: Check patterns loaded
info "Step 4: Checking pattern library..."
PATTERN_COUNT=$(curl -s ${PATTERNS_ENDPOINT} | jq -r '.total_count' 2>/dev/null || echo "0")

if [ "$PATTERN_COUNT" -gt 0 ]; then
    success "Pattern library loaded: ${PATTERN_COUNT} patterns"
else
    error "Pattern library failed to load"
fi

# Step 5: Test extraction endpoint
info "Step 5: Testing extraction endpoint..."
TEST_PAYLOAD='{
  "document_id": "verify-startup-test",
  "content": "Test document: Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)",
  "entity_types": ["case_citation"],
  "extraction_mode": "regex"
}'

EXTRACT_RESPONSE=$(curl -s -X POST ${EXTRACT_ENDPOINT} \
  -H "Content-Type: application/json" \
  -d "${TEST_PAYLOAD}")

ENTITY_COUNT=$(echo ${EXTRACT_RESPONSE} | jq -r '.total_entities' 2>/dev/null || echo "0")

if [ "$ENTITY_COUNT" -gt 0 ]; then
    success "Extraction endpoint working: ${ENTITY_COUNT} entities extracted"
    PROCESSING_TIME=$(echo ${EXTRACT_RESPONSE} | jq -r '.processing_time_ms')
    info "  Processing time: ${PROCESSING_TIME} ms"
else
    error "Extraction endpoint failed"
fi

# Step 6: Check service logs for errors
info "Step 6: Checking recent service logs for critical errors..."
ERROR_COUNT=$(sudo journalctl -u ${SERVICE_NAME} --since "1 minute ago" | grep -i "CRITICAL\|FATAL" | wc -l)

if [ "$ERROR_COUNT" -eq 0 ]; then
    success "No critical errors in recent logs"
else
    warning "Found ${ERROR_COUNT} critical errors in logs (check journalctl)"
fi

# Step 7: Memory usage check
info "Step 7: Checking memory usage..."
MEMORY_MB=$(sudo systemctl show ${SERVICE_NAME} --property=MemoryCurrent | cut -d= -f2)
MEMORY_MB_READABLE=$((MEMORY_MB / 1024 / 1024))

if [ "$MEMORY_MB_READABLE" -gt 0 ] && [ "$MEMORY_MB_READABLE" -lt 2000 ]; then
    success "Memory usage: ${MEMORY_MB_READABLE} MB (within normal range)"
elif [ "$MEMORY_MB_READABLE" -ge 2000 ]; then
    warning "Memory usage high: ${MEMORY_MB_READABLE} MB"
else
    info "Memory usage: ${MEMORY_MB_READABLE} MB"
fi

# Final summary
echo ""
echo "============================================="
echo -e "${GREEN}All startup verification checks passed!${NC}"
echo "============================================="
echo ""
echo "Service Details:"
echo "  - Service: ${SERVICE_NAME}"
echo "  - Port: ${SERVICE_PORT}"
echo "  - Version: ${SERVICE_VERSION}"
echo "  - Status: healthy"
echo "  - Patterns: ${PATTERN_COUNT}"
echo "  - Uptime: ${UPTIME}s"
echo "  - Memory: ${MEMORY_MB_READABLE} MB"
echo ""
echo "Endpoints:"
echo "  - Health: ${HEALTH_ENDPOINT}"
echo "  - Patterns: ${PATTERNS_ENDPOINT}"
echo "  - Extract: ${EXTRACT_ENDPOINT}"
echo ""
echo "Service is ready for production use!"
echo ""
