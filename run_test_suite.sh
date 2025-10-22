#!/bin/bash
# Test Suite Execution Script
# Runs 8 entity extraction tests with synthetic legal case documents
# Populates test_history.json and generates HTML dashboard

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Entity Extraction Test Suite - Synthetic Legal Case Data     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Navigate to service directory
cd /srv/luris/be/entity-extraction-service

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found"
    exit 1
fi

# Verify test data exists
if [ ! -d "tests/test_data/synthetic_cases" ]; then
    echo "❌ Test data directory not found: tests/test_data/synthetic_cases/"
    exit 1
fi

echo "✅ Test data directory found"
echo ""

# Count existing tests in history
if [ -f "tests/results/test_history.json" ]; then
    EXISTING_TESTS=$(python -c "import json; data = json.load(open('tests/results/test_history.json')); print(len(data.get('tests', [])))")
    echo "📊 Existing test history: $EXISTING_TESTS tests"
else
    EXISTING_TESTS=0
    echo "📊 No existing test history (starting fresh)"
fi
echo ""

# Test configuration
declare -a TEST_CONFIGS=(
    "case_001.txt:5000:0.0:true:Federal Criminal Case (temp 0.0 + validation)"
    "case_002.txt:5000:0.3:true:State Civil Rights Case (temp 0.3 + validation)"
    "case_003.txt:5000:0.0:false:Constitutional Law Case (temp 0.0)"
    "case_004.txt:8000:0.0:true:Contract Dispute (8000 chars + validation)"
    "case_005.txt:5000:0.3:false:Criminal Appeal (temp 0.3)"
    "case_006.txt:500:0.0:true:Quick Test Case (500 chars + validation)"
    "case_007.txt:20000:0.0:true:Complex Multi-Issue Case (20K chars + validation)"
    "case_001.txt:5000:0.0:false:Federal Criminal Case (repeat - consistency check)"
)

TOTAL_TESTS=${#TEST_CONFIGS[@]}
SUCCESSFUL_TESTS=0
FAILED_TESTS=0

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Test Execution: $TOTAL_TESTS tests scheduled                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Execute each test
for i in "${!TEST_CONFIGS[@]}"; do
    TEST_NUM=$((i + 1))
    IFS=':' read -r DOCUMENT CHARS TEMP VALIDATE DESCRIPTION <<< "${TEST_CONFIGS[$i]}"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧪 TEST $TEST_NUM/$TOTAL_TESTS: $DESCRIPTION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "   Document: $DOCUMENT"
    echo "   Characters: $CHARS"
    echo "   Temperature: $TEMP"
    echo "   Validate Patterns: $VALIDATE"
    echo ""

    # Build command
    CMD="python -m tests.test_framework.orchestrator_test_runner"
    CMD="$CMD --document tests/test_data/synthetic_cases/$DOCUMENT"
    CMD="$CMD --chars $CHARS"
    CMD="$CMD --temperature $TEMP"

    if [ "$VALIDATE" = "true" ]; then
        CMD="$CMD --validate-patterns"
    fi

    # Execute test
    START_TIME=$(date +%s)

    if eval $CMD; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        SUCCESSFUL_TESTS=$((SUCCESSFUL_TESTS + 1))
        echo ""
        echo "✅ TEST $TEST_NUM COMPLETED in ${DURATION}s"
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo ""
        echo "❌ TEST $TEST_NUM FAILED after ${DURATION}s"
    fi

    echo ""

    # Cooldown between tests (avoid overwhelming system)
    if [ $TEST_NUM -lt $TOTAL_TESTS ]; then
        echo "⏸️  Cooldown: 5 seconds before next test..."
        sleep 5
        echo ""
    fi
done

# Final summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    TEST SUITE SUMMARY                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Total Tests Run: $TOTAL_TESTS"
echo "✅ Successful: $SUCCESSFUL_TESTS"
echo "❌ Failed: $FAILED_TESTS"
echo ""

# Check final test history count
if [ -f "tests/results/test_history.json" ]; then
    FINAL_TESTS=$(python -c "import json; data = json.load(open('tests/results/test_history.json')); print(len(data.get('tests', [])))")
    NEW_TESTS=$((FINAL_TESTS - EXISTING_TESTS))
    echo "📈 Test History Statistics:"
    echo "   Previous: $EXISTING_TESTS tests"
    echo "   Current: $FINAL_TESTS tests"
    echo "   Added: $NEW_TESTS tests"
else
    echo "⚠️  Warning: test_history.json not found"
fi

echo ""

# Dashboard info
if [ -f "tests/results/dashboard.html" ]; then
    DASHBOARD_PATH="$(pwd)/tests/results/dashboard.html"
    echo "📊 Dashboard: file://$DASHBOARD_PATH"
    echo "💾 Test History: $(pwd)/tests/results/test_history.json"
else
    echo "⚠️  Warning: dashboard.html not found"
fi

echo ""

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
    exit 0
else
    echo "⚠️  SOME TESTS FAILED"
    exit 1
fi
