# Entity Extraction Service Test Framework

## Overview
A comprehensive test framework has been designed to ensure all extraction strategies work properly before running tests, with detailed debugging and actionable insights.

## Components Created

### 1. Pre-Test Health Check (`pre_test_health_check.py`)
**Purpose**: Ensures all required services are running before tests

**Features**:
- Checks health of Entity Extraction Service (port 8007)
- Checks health of vLLM Service (port 8080)
- Checks optional services (Embeddings, Document Upload)
- Shows systemd status for each service
- Can auto-start services with `--auto-start` flag
- Continuous monitoring mode with `--monitor` flag
- Clear visual status indicators

**Usage**:
```bash
# Basic health check
python tests/pre_test_health_check.py

# Auto-start unhealthy services
python tests/pre_test_health_check.py --auto-start

# Continuous monitoring
python tests/pre_test_health_check.py --monitor --interval 5
```

### 2. Debug Strategy Failures (`debug_strategy_failures.py`)
**Purpose**: Identifies exactly why extraction strategies fail

**Features**:
- Tests all extraction modes (regex, spacy, ai_enhanced, hybrid)
- Tests all prompt strategies (5 different strategies)
- Detailed debug steps for each test
- Error classification and pattern analysis
- Actionable recommendations based on failures
- JSON export of detailed results

**Usage**:
```bash
# Test all strategies with verbose output
python tests/debug_strategy_failures.py --verbose

# Test specific strategy
python tests/debug_strategy_failures.py --strategy ai_enhanced_legal_specialized_extraction
```

### 3. Comprehensive Test Framework (`comprehensive_test_framework.py`)
**Purpose**: Complete end-to-end testing with HTML reporting

**Features**:
- Pre-test health checks for all services
- Tests all extraction strategies systematically
- Generates beautiful HTML reports with charts
- Calculates comparison metrics between strategies
- Provides actionable insights and recommendations
- Saves JSON results for programmatic analysis
- Interactive visualizations using Chart.js

**Usage**:
```bash
# Run complete test suite
python tests/comprehensive_test_framework.py
```

## Key Findings from Initial Tests

### Critical Issue Discovered
**All extraction strategies are failing with HTTP 422 errors because the `document_id` field is required but not being provided in test requests.**

### Current Test Results
- **Services**: All healthy and running ✅
- **API Issue**: Missing required `document_id` parameter in requests
- **Impact**: 100% test failure rate until this is fixed

### Error Details
```json
{
  "type": "missing",
  "loc": ["body", "document_id"],
  "msg": "Field required"
}
```

## Test Execution Flow

### 1. Pre-Test Phase
```bash
# Step 1: Check service health
python tests/pre_test_health_check.py

# Step 2: Start any unhealthy services
python tests/pre_test_health_check.py --auto-start
```

### 2. Debug Phase (if issues exist)
```bash
# Debug specific failures
python tests/debug_strategy_failures.py --verbose
```

### 3. Comprehensive Testing
```bash
# Run full test suite
python tests/comprehensive_test_framework.py
```

### 4. Review Results
- HTML Report: `/srv/luris/be/entity-extraction-service/tests/results/test_report_[timestamp].html`
- JSON Results: `/srv/luris/be/entity-extraction-service/tests/results/test_results_[timestamp].json`
- Debug Logs: `debug_results_[timestamp].json`

## Benefits of This Framework

### 1. **Early Problem Detection**
- Health checks prevent wasted test runs
- Clear identification of service issues
- Automatic service startup options

### 2. **Detailed Debugging**
- Step-by-step execution tracking
- Error classification and patterns
- Response time measurements
- Memory usage tracking

### 3. **Comprehensive Comparison**
- Side-by-side strategy comparison
- Performance metrics (speed vs accuracy)
- Entity type distribution analysis
- Confidence score statistics

### 4. **Actionable Insights**
- Specific recommendations for failures
- Optimal strategy selection
- Performance optimization suggestions
- Service configuration advice

### 5. **Professional Reporting**
- Executive-friendly HTML reports
- Interactive charts and visualizations
- Exportable data for further analysis
- Historical tracking capability

## Next Steps

### Immediate Actions Required
1. **Fix API Calls**: Add `document_id` parameter to all extraction requests
2. **Update Test Data**: Ensure proper document IDs are generated
3. **Re-run Tests**: Validate all strategies work correctly

### Framework Enhancements
1. **Add Performance Benchmarking**: Load testing with concurrent requests
2. **Implement Regression Testing**: Compare against baseline results
3. **Add Configuration Testing**: Test different threshold and parameter combinations
4. **Create CI/CD Integration**: Automated testing on code changes

## Configuration Requirements

### Required Python Packages
- requests
- rich (for beautiful console output)
- pandas (for data analysis)
- tabulate (for table formatting)

### Service Dependencies
- Entity Extraction Service (port 8007) - REQUIRED
- vLLM Service (port 8080) - REQUIRED for AI modes
- vLLM Embeddings Service (port 8081) - Optional
- Document Upload Service (port 8008) - Optional

## Summary

This comprehensive test framework provides:
- **Reliability**: Pre-test health checks ensure services are running
- **Visibility**: Detailed debugging shows exactly why tests fail
- **Insights**: Comparison metrics help choose optimal strategies
- **Documentation**: HTML reports provide clear test evidence
- **Actionability**: Specific recommendations for improvements

The framework has already identified a critical API issue (missing document_id) that was causing 100% test failure. Once fixed, it will provide ongoing value for:
- Development testing
- Performance optimization
- Regression prevention
- Quality assurance
- Documentation and compliance