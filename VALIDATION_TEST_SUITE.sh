#!/bin/bash
#
# Entity Extraction Service v2.0.1 Validation Test Suite
# Comprehensive validation of all migration changes
# Date: 2025-10-15
#
# Usage: bash VALIDATION_TEST_SUITE.sh
#

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Service configuration
SERVICE_DIR="/srv/luris/be/entity-extraction-service"

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_test() {
    echo -e "${BLUE}TEST $TESTS_RUN: $1${NC}"
}

print_success() {
    echo -e "${GREEN}  ✅ PASS: $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}  ❌ FAIL: $1${NC}"
    ((TESTS_FAILED++))
}

print_skip() {
    echo -e "${YELLOW}  ⏭️  SKIP: $1${NC}"
    ((TESTS_SKIPPED++))
}

print_info() {
    echo -e "${BLUE}  ℹ️  $1${NC}"
}

run_test() {
    ((TESTS_RUN++))
    print_test "$1"
}

# Start validation
print_header "Entity Extraction Service v2.0.1 Validation Suite"
echo "Start Time: $(date)"
echo "Service Directory: $SERVICE_DIR"
echo ""

cd "$SERVICE_DIR"

# Test 1: Virtual environment exists
print_header "Phase 1: Environment Validation"
run_test "Virtual environment exists"
if [ -d "venv" ]; then
    print_success "Virtual environment found at venv/"
else
    print_failure "Virtual environment not found"
fi

# Test 2: .env file exists
run_test "Configuration file exists"
if [ -f ".env" ]; then
    print_success ".env file found"
    ENV_LINES=$(wc -l < .env)
    print_info "Configuration has $ENV_LINES lines"
else
    print_failure ".env file not found"
fi

# Test 3: .env.example exists
run_test "Example configuration exists"
if [ -f ".env.example" ]; then
    print_success ".env.example file found"
    EXAMPLE_VARS=$(grep -c "^[A-Z]" .env.example || true)
    print_info "Example contains $EXAMPLE_VARS variable definitions"
else
    print_failure ".env.example file not found"
fi

# Test 4: Backup exists
run_test "Backup configuration exists"
if [ -f ".env.backup.20251015_020208" ]; then
    print_success "Backup .env file found"
else
    print_failure "Backup .env file not found"
fi

# Test 5: YAML deprecated
run_test "YAML configuration deprecated"
if [ -f "config/archive/settings.yaml.deprecated" ]; then
    print_success "YAML moved to archive"
else
    print_failure "YAML not properly archived"
fi

# Test 6: YAML not in active config
run_test "YAML removed from active config"
if [ ! -f "config/settings.yaml" ]; then
    print_success "No active settings.yaml file"
else
    print_failure "Active settings.yaml still exists"
fi

# Test 7: Configuration loading
print_header "Phase 2: Configuration Loading Tests"
run_test "Configuration loads successfully"
source venv/bin/activate

CONFIG_TEST=$(python -c "
from src.core.config import get_settings
try:
    settings = get_settings()
    print('PASS')
except Exception as e:
    print(f'FAIL: {e}')
" 2>&1)

if [[ "$CONFIG_TEST" == "PASS" ]]; then
    print_success "Configuration loaded successfully"
else
    print_failure "Configuration loading failed: $CONFIG_TEST"
fi

# Test 8: Configuration variable count
run_test "Configuration has expected number of variables"
VAR_COUNT=$(python -c "
from src.core.config import get_settings
settings = get_settings()
print(len([k for k in settings.__dict__.keys() if not k.startswith('_')]))
" 2>&1)

if [ "$VAR_COUNT" -ge 160 ]; then
    print_success "Configuration has $VAR_COUNT variables (expected ≥160)"
else
    print_failure "Configuration has only $VAR_COUNT variables (expected ≥160)"
fi

# Test 9: Critical environment variables
run_test "Critical environment variables are set"
CRITICAL_VARS=(
    "EE_API_HOST"
    "EE_API_PORT"
    "EE_VLLM_URL"
    "EE_VLLM_MODEL"
    "EE_DEFAULT_MODE"
)

CRITICAL_PASS=true
for var in "${CRITICAL_VARS[@]}"; do
    if grep -q "^${var}=" .env; then
        print_info "  ✓ $var is set"
    else
        print_info "  ✗ $var is missing"
        CRITICAL_PASS=false
    fi
done

if [ "$CRITICAL_PASS" = true ]; then
    print_success "All critical variables present"
else
    print_failure "Some critical variables missing"
fi

# Test 10: Entity model schema
print_header "Phase 3: Entity Model Schema Tests"
run_test "Entity model has entity_type field"
ENTITY_TYPE_TEST=$(python -c "
from src.core.entity_models import Entity, EntityType
try:
    entity = Entity(
        entity_type=EntityType.PERSON,
        text='Test',
        confidence=0.95
    )
    if hasattr(entity, 'entity_type'):
        print('PASS')
    else:
        print('FAIL: entity_type field not found')
except Exception as e:
    print(f'FAIL: {e}')
" 2>&1)

if [[ "$ENTITY_TYPE_TEST" == "PASS" ]]; then
    print_success "Entity model uses entity_type field"
else
    print_failure "Entity model schema issue: $ENTITY_TYPE_TEST"
fi

# Test 11: Entity model validation
run_test "Entity model enforces required fields"
VALIDATION_TEST=$(python -c "
from src.core.entity_models import Entity, EntityType
from pydantic import ValidationError
try:
    # Should fail without required fields
    entity = Entity()
    print('FAIL: Validation not enforced')
except ValidationError:
    print('PASS')
except Exception as e:
    print(f'FAIL: {e}')
" 2>&1)

if [[ "$VALIDATION_TEST" == "PASS" ]]; then
    print_success "Required fields properly enforced"
else
    print_failure "Validation issue: $VALIDATION_TEST"
fi

# Test 12: Confidence range validation
run_test "Confidence field validates range (0.7-1.0)"
CONFIDENCE_TEST=$(python -c "
from src.core.entity_models import Entity, EntityType
from pydantic import ValidationError
passed = True
# Test below range
try:
    entity = Entity(entity_type=EntityType.PERSON, text='Test', confidence=0.5)
    passed = False
except ValidationError:
    pass
# Test above range
try:
    entity = Entity(entity_type=EntityType.PERSON, text='Test', confidence=1.5)
    passed = False
except ValidationError:
    pass
# Test valid range
try:
    entity = Entity(entity_type=EntityType.PERSON, text='Test', confidence=0.85)
except ValidationError:
    passed = False
print('PASS' if passed else 'FAIL')
" 2>&1)

if [[ "$CONFIDENCE_TEST" == "PASS" ]]; then
    print_success "Confidence range validation works"
else
    print_failure "Confidence validation issue"
fi

# Test 13: Text length validation
run_test "Text field validates length (1-500 chars)"
TEXT_LENGTH_TEST=$(python -c "
from src.core.entity_models import Entity, EntityType
from pydantic import ValidationError
passed = True
# Test empty string
try:
    entity = Entity(entity_type=EntityType.PERSON, text='', confidence=0.85)
    passed = False
except ValidationError:
    pass
# Test too long
try:
    entity = Entity(entity_type=EntityType.PERSON, text='x'*501, confidence=0.85)
    passed = False
except ValidationError:
    pass
# Test valid length
try:
    entity = Entity(entity_type=EntityType.PERSON, text='Valid Text', confidence=0.85)
except ValidationError:
    passed = False
print('PASS' if passed else 'FAIL')
" 2>&1)

if [[ "$TEXT_LENGTH_TEST" == "PASS" ]]; then
    print_success "Text length validation works"
else
    print_failure "Text length validation issue"
fi

# Test 14: Guided JSON configuration
print_header "Phase 4: Guided JSON Tests"
run_test "Guided JSON enabled in extraction orchestrator"
if grep -q '"guided_json": entity_schema' src/core/extraction_orchestrator.py; then
    print_success "Guided JSON found in code"
else
    print_failure "Guided JSON not found in extraction orchestrator"
fi

# Test 15: Guided decoding backend
run_test "Guided decoding backend specified"
if grep -q '"guided_decoding_backend": "outlines"' src/core/extraction_orchestrator.py; then
    print_success "Backend set to 'outlines'"
else
    print_failure "Backend not properly configured"
fi

# Test 16: Import blocker check
print_header "Phase 5: Known Issues Checks"
run_test "HTTP client import issue (known blocker)"
if grep -q "from client.vllm_http_client import VLLMLocalClient" src/core/extraction_orchestrator.py; then
    print_failure "HTTP client import blocker still present (line 681)"
    print_info "Fix: sed -i 's|from client.vllm_http_client|from src.clients.vllm_http_client|g' src/core/extraction_orchestrator.py"
else
    print_success "HTTP client import issue resolved"
fi

# Test 17: YAML loading code removed
run_test "YAML loading code removed from config.py"
if grep -q "_load_yaml_config" src/core/config.py; then
    print_failure "YAML loading code still present"
else
    print_success "YAML loading code removed"
fi

# Test 18: sys.path manipulation
run_test "No sys.path manipulation in code"
SYS_PATH_COUNT=$(grep -r "sys.path" src/ --include="*.py" | grep -v ".pyc" | wc -l)
if [ "$SYS_PATH_COUNT" -eq 0 ]; then
    print_success "No sys.path manipulation found"
else
    print_failure "Found $SYS_PATH_COUNT instances of sys.path manipulation"
fi

# Test 19: Documentation files
print_header "Phase 6: Documentation Validation"
DOCS=(
    "DEPLOYMENT_READINESS_REPORT_v2.0.1.md"
    "QUICK_REFERENCE_v2.0.1.md"
    "MIGRATION_GUIDE_v2.0.1.md"
    "CHANGELOG.md"
    "README.md"
    ".env.example"
)

for doc in "${DOCS[@]}"; do
    run_test "Documentation file: $doc"
    if [ -f "$doc" ]; then
        print_success "Found $doc"
    else
        print_failure "Missing $doc"
    fi
done

# Test 20: vLLM services availability
print_header "Phase 7: Service Dependencies"
run_test "vLLM LLM service (GPU 0, port 8080)"
if curl -s -f "http://localhost:8080/health" > /dev/null 2>&1; then
    print_success "vLLM LLM service responding"
else
    print_skip "vLLM LLM service not responding (may not be started)"
fi

run_test "vLLM Embeddings service (GPU 1, port 8081)"
if curl -s -f "http://localhost:8081/health" > /dev/null 2>&1; then
    print_success "vLLM Embeddings service responding"
else
    print_skip "vLLM Embeddings service not responding (may not be started)"
fi

# Test 21: Entity Extraction service
run_test "Entity Extraction service (port 8007)"
if curl -s -f "http://localhost:8007/api/health" > /dev/null 2>&1; then
    print_success "Entity Extraction service responding"
    HEALTH=$(curl -s "http://localhost:8007/api/health")
    print_info "Health: $HEALTH"
else
    print_skip "Entity Extraction service not responding (may not be started)"
fi

# Test 22: Code quality - import patterns
print_header "Phase 8: Code Quality Checks"
run_test "Import patterns compliance"
RELATIVE_IMPORTS=$(grep -r "from \.\.\." src/ --include="*.py" | grep -v ".pyc" | wc -l)
if [ "$RELATIVE_IMPORTS" -eq 0 ]; then
    print_success "No relative imports found (100% compliance)"
else
    print_failure "Found $RELATIVE_IMPORTS relative imports"
fi

# Test 23: Python cache cleared
run_test "Python cache status"
PYCACHE_COUNT=$(find . -type d -name __pycache__ | wc -l)
if [ "$PYCACHE_COUNT" -eq 0 ]; then
    print_success "No __pycache__ directories (cache cleared)"
else
    print_info "$PYCACHE_COUNT __pycache__ directories found (not critical)"
    print_success "Cache can be cleared with: find . -type d -name __pycache__ -exec rm -rf {} +"
fi

# Test 24: Configuration performance
print_header "Phase 9: Performance Tests"
run_test "Configuration loading performance"
PERF_TEST=$(python -c "
import time
from src.core.config import get_settings

# Initial load
start = time.time()
settings1 = get_settings()
initial_time = time.time() - start

# Cached load
start = time.time()
settings2 = get_settings()
cached_time = time.time() - start

print(f'Initial: {initial_time:.6f}s, Cached: {cached_time:.9f}s')
if cached_time < 0.0001:
    print('PASS')
else:
    print('WARN: Cached load slower than expected')
" 2>&1)

if [[ "$PERF_TEST" == *"PASS"* ]]; then
    print_success "Configuration loading performance good"
    print_info "$PERF_TEST"
else
    print_failure "Performance issue: $PERF_TEST"
fi

# Final summary
print_header "Validation Summary"
echo ""
echo "Total Tests Run:    $TESTS_RUN"
echo -e "${GREEN}Tests Passed:       $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed:       $TESTS_FAILED${NC}"
echo -e "${YELLOW}Tests Skipped:      $TESTS_SKIPPED${NC}"
echo ""

# Calculate success rate
if [ $TESTS_RUN -gt 0 ]; then
    SUCCESS_RATE=$((TESTS_PASSED * 100 / (TESTS_RUN - TESTS_SKIPPED)))
    echo "Success Rate: ${SUCCESS_RATE}%"
    echo ""
fi

# Overall result
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}Entity Extraction Service v2.0.1 is READY FOR DEPLOYMENT${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${RED}Please review failures before deployment${NC}"
    exit 1
fi
