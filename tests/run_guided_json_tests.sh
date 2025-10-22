#!/bin/bash
#
# Run guided JSON validation tests
#
# This script properly sets up the Python path and runs the guided JSON tests.
# It works around pytest import issues by setting PYTHONPATH explicitly.
#
# Usage:
#   ./tests/run_guided_json_tests.sh
#
# Or with pytest:
#   PYTHONPATH=/srv/luris/be/entity-extraction-service/src pytest tests/test_guided_json.py -v
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}Guided JSON Validation Tests${NC}"
echo -e "${YELLOW}================================${NC}"
echo ""

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}✗ Virtual environment not found at $PROJECT_ROOT/venv${NC}"
    exit 1
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
echo -e "${GREEN}✓ PYTHONPATH set to: $PYTHONPATH${NC}"
echo ""

# Check if vLLM is installed
echo -e "${YELLOW}Checking vLLM installation...${NC}"
python -c "import vllm; print('vLLM version:', vllm.__version__)" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ vLLM is installed${NC}"
else
    echo -e "${RED}✗ vLLM is not installed${NC}"
    echo -e "${YELLOW}  Install with: source venv/bin/activate && pip install vllm==0.6.3${NC}"
    exit 1
fi
echo ""

# Run tests with pytest
echo -e "${YELLOW}Running tests with pytest...${NC}"
echo ""

pytest "$PROJECT_ROOT/tests/test_guided_json.py" \
    -v \
    --tb=short \
    --color=yes \
    -ra

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}✓ All tests PASSED${NC}"
    echo -e "${GREEN}================================${NC}"
else
    echo -e "${RED}================================${NC}"
    echo -e "${RED}✗ Some tests FAILED${NC}"
    echo -e "${RED}================================${NC}"
fi

exit $TEST_EXIT_CODE
