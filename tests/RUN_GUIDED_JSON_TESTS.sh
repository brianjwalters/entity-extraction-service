#!/usr/bin/env bash
#
# Guided JSON Test Execution Script
#
# This script safely runs the guided JSON validation tests by:
# 1. Stopping the vLLM service (frees GPU 0)
# 2. Running the tests
# 3. Restarting the vLLM service
#
# Usage:
#   cd /srv/luris/be/entity-extraction-service
#   chmod +x tests/RUN_GUIDED_JSON_TESTS.sh
#   sudo tests/RUN_GUIDED_JSON_TESTS.sh

set -e  # Exit on error

echo "================================================================================"
echo "GUIDED JSON VALIDATION TEST SUITE"
echo "================================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ ERROR: This script must be run as root (for systemctl commands)${NC}"
    echo "Please run: sudo tests/RUN_GUIDED_JSON_TESTS.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo -e "${YELLOW}Running as user: $ACTUAL_USER${NC}"
echo ""

# Step 1: Stop vLLM service
echo "Step 1: Stopping vLLM service..."
if systemctl is-active --quiet luris-vllm; then
    systemctl stop luris-vllm
    echo -e "${GREEN}✅ vLLM service stopped${NC}"
else
    echo -e "${YELLOW}⚠️  vLLM service was not running${NC}"
fi

# Step 2: Wait for GPU to clear
echo ""
echo "Step 2: Waiting for GPU memory to clear..."
sleep 5

# Check GPU status
echo ""
echo "GPU Status:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits | while IFS=, read -r gpu_idx gpu_name mem_used mem_total util; do
    echo "  GPU $gpu_idx: $gpu_name"
    echo "    Memory: ${mem_used}MB / ${mem_total}MB"
    echo "    Utilization: ${util}%"
done

# Step 3: Activate venv and run tests
echo ""
echo "Step 3: Running guided JSON validation tests..."
echo ""

cd /srv/luris/be/entity-extraction-service

# Run as the actual user (not root)
su - $ACTUAL_USER -c "
    cd /srv/luris/be/entity-extraction-service
    source venv/bin/activate
    echo 'venv activated for user: $ACTUAL_USER'
    echo ''
    echo 'Running pytest tests...'
    echo ''
    pytest tests/test_guided_json.py -v --tb=short -x
"

TEST_EXIT_CODE=$?

# Step 4: Restart vLLM service
echo ""
echo "Step 4: Restarting vLLM service..."
systemctl start luris-vllm

# Wait for service to be ready
echo "Waiting for vLLM service to start..."
sleep 10

if systemctl is-active --quiet luris-vllm; then
    echo -e "${GREEN}✅ vLLM service restarted${NC}"
else
    echo -e "${RED}❌ WARNING: vLLM service failed to restart${NC}"
    echo "Check service status with: sudo systemctl status luris-vllm"
fi

# Step 5: Summary
echo ""
echo "================================================================================"
echo "TEST SUMMARY"
echo "================================================================================"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ ALL GUIDED JSON TESTS PASSED${NC}"
    echo ""
    echo "Guided JSON support is working correctly!"
    echo "- DirectVLLMClient initializes successfully"
    echo "- GuidedDecodingParams are applied correctly"
    echo "- LLM output matches schemas exactly"
    echo "- No JSON parsing errors occur"
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Review the test output above for details."
    echo ""
    echo "Common issues:"
    echo "  1. vLLM library not installed: pip install vllm==0.6.3"
    echo "  2. GPU memory insufficient: Check nvidia-smi"
    echo "  3. CUDA conflicts: Ensure vLLM service is stopped"
fi

echo ""
echo "================================================================================"
echo "DOCUMENTATION"
echo "================================================================================"
echo ""
echo "Test file:       tests/test_guided_json.py"
echo "README:          tests/GUIDED_JSON_TEST_README.md"
echo "Summary:         tests/GUIDED_JSON_VALIDATION_SUMMARY.md"
echo "Implementation:  src/vllm/client.py (lines 233-309)"
echo ""
echo "vLLM service:    sudo systemctl status luris-vllm"
echo "GPU status:      nvidia-smi"
echo ""
echo "================================================================================"

exit $TEST_EXIT_CODE
