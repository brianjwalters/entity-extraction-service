# Phase 4 Family Law Patterns - Test Execution Guide

## Overview

This guide provides instructions for executing the comprehensive Phase 4 family law patterns test suite.

## Test Suite Summary

- **Test File**: `/srv/luris/be/entity-extraction-service/tests/test_phase4_family_law_patterns.py`
- **Pattern File**: `/srv/luris/be/entity-extraction-service/phase4_family_law_patterns_final.yaml`
- **Total Test Cases**: 150+
- **Pattern Coverage**: 58 patterns (100%)
- **Entity Type Coverage**: 28 entity types (100%)

## Test Organization

### 8 Test Classes

1. **TestPhase4PatternCompilation** (7 tests)
   - Pattern file validation
   - YAML structure integrity
   - Compilation verification
   - Metadata completeness

2. **TestAdvancedEnforcement** (20+ tests)
   - 15 enforcement patterns
   - Interstate income withholding
   - License suspension
   - Credit reporting
   - FPLS, FIDM, passport denial
   - Employer reporting

3. **TestMilitaryFamilyProvisions** (18+ tests)
   - 11 military patterns
   - SCRA protections
   - USFSPA pension division
   - Deployment custody modifications
   - Military allotments
   - Combat zone suspensions

4. **TestInterstateInternationalCooperation** (22+ tests)
   - 13 interstate/international patterns
   - UIFSA provisions
   - Hague Convention
   - Tribal court cooperation
   - Canadian reciprocal enforcement
   - Foreign order registration

5. **TestSpecializedCourtProcedures** (18+ tests)
   - 11 specialized procedure patterns
   - Pro tempore judges
   - Sealed records (DV)
   - Mandatory settlement conferences
   - Case scheduling orders
   - Ex parte prohibitions

6. **TestAdvancedFinancialMechanisms** (16+ tests)
   - 11 financial mechanism patterns
   - QMCSO (medical support orders)
   - Education trust funds (529 plans)
   - Life insurance beneficiaries
   - Tax refund intercepts (IRS/TOP)

7. **TestPhase4Performance** (4 tests)
   - Single pattern performance
   - All patterns performance
   - Large document processing (>10KB)
   - Concurrent extraction

8. **TestPhase4Integration** (6 tests)
   - Service health checks
   - API pattern extraction
   - LurisEntityV2 schema compliance
   - Multi-mode extraction
   - Performance metrics
   - Batch extraction

## Prerequisites

### 1. Virtual Environment
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
```

### 2. Dependencies
```bash
pip install pytest pytest-html pytest-cov pyyaml requests
```

### 3. Service Requirements

**For Unit Tests Only**:
- No services required

**For Integration Tests**:
- Entity Extraction Service must be running on Port 8007
```bash
# Check service status
sudo systemctl status luris-entity-extraction

# Start service if needed
sudo systemctl start luris-entity-extraction

# Verify service health
curl http://localhost:8007/api/v2/health
```

## Test Execution

### Run All Tests
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

pytest tests/test_phase4_family_law_patterns.py -v
```

### Run Specific Test Classes

**Pattern Compilation Tests Only**:
```bash
pytest tests/test_phase4_family_law_patterns.py::TestPhase4PatternCompilation -v
```

**Advanced Enforcement Tests**:
```bash
pytest tests/test_phase4_family_law_patterns.py::TestAdvancedEnforcement -v
```

**Military Family Provisions Tests**:
```bash
pytest tests/test_phase4_family_law_patterns.py::TestMilitaryFamilyProvisions -v
```

**Interstate/International Tests**:
```bash
pytest tests/test_phase4_family_law_patterns.py::TestInterstateInternationalCooperation -v
```

**Specialized Procedures Tests**:
```bash
pytest tests/test_phase4_family_law_patterns.py::TestSpecializedCourtProcedures -v
```

**Financial Mechanisms Tests**:
```bash
pytest tests/test_phase4_family_law_patterns.py::TestAdvancedFinancialMechanisms -v
```

**Performance Tests**:
```bash
pytest tests/test_phase4_family_law_patterns.py::TestPhase4Performance -v
```

**Integration Tests** (requires service):
```bash
pytest tests/test_phase4_family_law_patterns.py::TestPhase4Integration -v
```

### Run by Test Markers

**Unit Tests Only** (no services required):
```bash
pytest tests/test_phase4_family_law_patterns.py -m unit -v
```

**Integration Tests Only** (requires service):
```bash
pytest tests/test_phase4_family_law_patterns.py -m "integration and requires_services" -v
```

**Performance Tests** (may be slow):
```bash
pytest tests/test_phase4_family_law_patterns.py -m slow -v
```

**Exclude Slow Tests**:
```bash
pytest tests/test_phase4_family_law_patterns.py -m "not slow" -v
```

### Generate HTML Report

```bash
pytest tests/test_phase4_family_law_patterns.py -v \
  --html=tests/results/phase4_test_report_$(date +%Y%m%d_%H%M%S).html \
  --self-contained-html
```

### Generate Coverage Report

```bash
pytest tests/test_phase4_family_law_patterns.py -v \
  --cov=src/core/pattern_loader \
  --cov=src/models/entities \
  --cov-report=html:tests/results/coverage_phase4 \
  --cov-report=term
```

### Run with Detailed Output

```bash
pytest tests/test_phase4_family_law_patterns.py -vv -s
```

### Run Specific Test
```bash
pytest tests/test_phase4_family_law_patterns.py::TestAdvancedEnforcement::test_interstate_withholding_false_positive -v
```

## Test Output Locations

### Results Directory
```
/srv/luris/be/entity-extraction-service/tests/results/
├── phase4_test_report_YYYYMMDD_HHMMSS.html  # HTML test report
├── phase4_test_report_YYYYMMDD_HHMMSS.md    # Markdown summary
└── coverage_phase4/                          # Coverage reports
    └── index.html
```

## Expected Test Results

### Success Criteria

✅ **Pattern Compilation**: All 58 patterns compile successfully
✅ **Entity Extraction**: 100% positive test pass rate
✅ **False Positive Prevention**: 100% negative test pass rate
✅ **Performance**: Average <15ms per pattern
✅ **Schema Compliance**: LurisEntityV2 fields validated
✅ **RCW Compliance**: All RCW references valid
✅ **Integration**: Service API responds correctly

### Performance Benchmarks

| Test Type | Target | Expected |
|-----------|--------|----------|
| Single Pattern | <15ms | 1-5ms |
| All Patterns | <15ms avg | 5-10ms avg |
| Large Document (>10KB) | <100ms | 20-50ms |
| Concurrent (50 extractions) | <30ms avg | 10-20ms avg |

### Coverage Goals

- **Pattern Coverage**: 100% (58/58 patterns)
- **Entity Type Coverage**: 100% (28/28 types)
- **Test Case Coverage**: 150+ test cases
- **Code Coverage**: ≥95% for pattern loader

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure venv is activated
source venv/bin/activate

# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**2. Pattern File Not Found**
```bash
# Verify pattern file exists
ls -la /srv/luris/be/entity-extraction-service/phase4_family_law_patterns_final.yaml
```

**3. Service Not Available (Integration Tests)**
```bash
# Check service status
sudo systemctl status luris-entity-extraction

# Check service logs
sudo journalctl -u luris-entity-extraction -f

# Verify port 8007
curl http://localhost:8007/api/v2/health
```

**4. Test Failures**
```bash
# Run with verbose output
pytest tests/test_phase4_family_law_patterns.py -vv -s --tb=long

# Run single failing test
pytest tests/test_phase4_family_law_patterns.py::TestClassName::test_name -vv
```

## Continuous Integration

### Pre-Commit Hook
```bash
#!/bin/bash
# Run Phase 4 tests before commit
source venv/bin/activate
pytest tests/test_phase4_family_law_patterns.py -m "unit" --tb=short
```

### CI/CD Pipeline Integration
```yaml
# Example GitHub Actions workflow
- name: Run Phase 4 Tests
  run: |
    source venv/bin/activate
    pytest tests/test_phase4_family_law_patterns.py -v \
      --html=test-results/phase4.html \
      --cov=src --cov-report=xml
```

## Test Maintenance

### Adding New Test Cases

1. **Identify Pattern**: Locate pattern in `phase4_family_law_patterns_final.yaml`
2. **Create Test**: Add test method to appropriate test class
3. **Follow Naming Convention**: `test_[pattern_group]_[specific_feature]`
4. **Include Parametrization**: Use `@pytest.mark.parametrize` for multiple examples
5. **Add Documentation**: Include docstring explaining test purpose

### Example Test Addition

```python
@pytest.mark.parametrize("text,expected_entity_type", [
    ("new pattern example text", "NEW_ENTITY_TYPE"),
])
def test_new_pattern_extraction(self, pattern_loader, text, expected_entity_type):
    """Test positive matches for new pattern"""
    entities = pattern_loader.extract_entities(text)
    matching_entities = [e for e in entities if e.entity_type == expected_entity_type]
    assert len(matching_entities) > 0
```

## Performance Optimization

### Profiling Tests
```bash
# Profile test execution
pytest tests/test_phase4_family_law_patterns.py --profile

# Profile with line profiler
kernprof -l -v tests/test_phase4_family_law_patterns.py
```

### Parallel Execution
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/test_phase4_family_law_patterns.py -n auto
```

## Reporting

### Generate Comprehensive Report
```bash
#!/bin/bash
# Generate all reports
source venv/bin/activate

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="tests/results/phase4_${TIMESTAMP}"
mkdir -p ${REPORT_DIR}

# Run tests with all reporting options
pytest tests/test_phase4_family_law_patterns.py -v \
  --html=${REPORT_DIR}/test_report.html \
  --self-contained-html \
  --cov=src \
  --cov-report=html:${REPORT_DIR}/coverage \
  --cov-report=term \
  --junit-xml=${REPORT_DIR}/junit.xml

echo "Reports generated in: ${REPORT_DIR}"
```

## Contact & Support

**Test Suite Author**: pipeline-test-engineer
**Pattern Authors**: legal-data-engineer, regex-expert
**Service Owner**: Entity Extraction Service Team
**Documentation**: `/srv/luris/be/entity-extraction-service/docs/`

## Appendix: Test Pattern Summary

### Group 1: Advanced Enforcement (15 patterns)
- Interstate income withholding (2 variants)
- Federal Parent Locator Service (3 variants)
- Credit reporting (2 variants)
- License suspension (1 pattern)
- Passport denial (1 pattern)
- FIDM (3 variants)
- Employer reporting (2 variants)
- Multiple income withholding (1 pattern)

### Group 2: Military Family Provisions (11 patterns)
- SCRA (3 variants)
- Military pension/USFSPA (2 variants)
- Deployment custody (2 variants)
- Military allotment (2 variants)
- Combat zone suspension (2 variants)

### Group 3: Interstate & International (13 patterns)
- UIFSA (3 variants)
- Canadian reciprocal (2 variants)
- Tribal court cooperation (2 variants)
- Hague Convention (3 variants)
- Interstate deposition (1 pattern)
- Foreign order registration (2 variants)

### Group 4: Specialized Procedures (11 patterns)
- Pro tempore judge (2 variants)
- Mandatory settlement (1 pattern)
- Case scheduling order (2 variants)
- Ex parte prohibition (2 variants)
- Sealed records DV (3 variants)

### Group 5: Advanced Financial (11 patterns)
- QMCSO (2 variants)
- Education trust (3 variants)
- Life insurance beneficiary (3 variants)
- Tax refund intercept (3 variants)

**Total: 58 patterns covering 28 entity types**
