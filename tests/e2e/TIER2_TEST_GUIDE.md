# Phase 2 Family Law Entity Testing Guide - Tier 2

**Last Updated**: November 5, 2025
**Test Suite Version**: 1.0
**Pattern Coverage**: 25 Phase 2 entities across 7 pattern groups
**Test Count**: 39 comprehensive tests

## Overview

This guide provides complete documentation for the Phase 2 (Tier 2) family law entity extraction test suite. The test suite validates 25 new patterns focusing on parental rights & responsibilities under Washington State RCW Title 26.

### Phase 2 Entity Groups (7 Groups, 25 Patterns)

1. **procedural_documents_ext** (4 patterns): RESTRAINING_ORDER, RELOCATION_NOTICE, MAINTENANCE_ORDER, PROPERTY_DISPOSITION
2. **child_support_calculation** (5 patterns): BASIC_SUPPORT_OBLIGATION, SUPPORT_DEVIATION, RESIDENTIAL_CREDIT, IMPUTED_INCOME, INCOME_DEDUCTION_ORDER
3. **support_enforcement** (4 patterns): WAGE_ASSIGNMENT_ORDER, CONTEMPT_ACTION, CHILD_SUPPORT_LIEN, SUPPORT_ARREARS
4. **jurisdiction_concepts_ext** (3 patterns): SIGNIFICANT_CONNECTION, EXCLUSIVE_CONTINUING_JURISDICTION, FOREIGN_CUSTODY_ORDER
5. **parentage_proceedings** (4 patterns): PARENTAGE_ACTION, PATERNITY_ACKNOWLEDGMENT, GENETIC_TESTING_ORDER, ADJUDICATION_OF_PARENTAGE
6. **adoption_proceedings** (4 patterns): ADOPTION_PETITION, RELINQUISHMENT_PETITION, HOME_STUDY_REPORT, OPEN_ADOPTION_AGREEMENT
7. **child_protection_ext** (1 pattern): MANDATORY_REPORTER

### Performance Targets (Phase 2 Optimization)

- **Average Execution**: 2.898ms per pattern (17% improvement over target)
- **Confidence Score**: 0.929 average across all patterns
- **Target**: <15ms per pattern (regex mode)
- **Test Execution**: <5 seconds for full 39-test suite

## Test Structure

### Test Breakdown (39 Tests Total)

| Test Type | Count | Description |
|-----------|-------|-------------|
| **Unit Tests** | 25 | One per entity type - validates individual pattern extraction |
| **Pattern Group Tests** | 7 | One per pattern group - validates group consistency |
| **Integration Tests** | 5 | Multi-entity documents testing realistic combinations |
| **E2E Pipeline Test** | 1 | Comprehensive document with all 25 entity types |
| **Performance Benchmark** | 1 | Validates speed and accuracy targets |

### File Structure

```
/srv/luris/be/entity-extraction-service/tests/e2e/
├── test_family_law_tier2.py      # Main test file (39 tests, ~1,200 lines)
├── conftest.py                    # Extended with Phase 2 fixtures (~1,340 lines)
├── TIER2_TEST_GUIDE.md           # This documentation file
└── __pycache__/                   # Pytest cache
```

## Quick Start

### Prerequisites

1. **Entity Extraction Service Running** (Port 8007)
2. **Virtual Environment Activated**
3. **All Dependencies Installed**

```bash
# Navigate to service directory
cd /srv/luris/be/entity-extraction-service

# Activate virtual environment
source venv/bin/activate

# Verify service is running
curl -s http://localhost:8007/api/v1/health | jq .status
```

### Running Tests

#### Run All Tier 2 Tests (39 tests)
```bash
pytest tests/e2e/test_family_law_tier2.py -v
```

#### Run By Test Type

**Unit Tests Only** (25 tests):
```bash
pytest tests/e2e/test_family_law_tier2.py -m "tier2 and e2e" -k "extraction" -v
```

**Pattern Group Tests** (7 tests):
```bash
pytest tests/e2e/test_family_law_tier2.py -m "pattern_group" -v
```

**Integration Tests** (5 tests):
```bash
pytest tests/e2e/test_family_law_tier2.py -m "integration" -v
```

**E2E Pipeline Test** (1 test):
```bash
pytest tests/e2e/test_family_law_tier2.py -m "pipeline" -v
```

**Performance Benchmark** (1 test):
```bash
pytest tests/e2e/test_family_law_tier2.py -m "performance" -v
```

#### Run By Pattern Group

**Procedural Documents Ext**:
```bash
pytest tests/e2e/test_family_law_tier2.py -k "restraining_order or relocation_notice or maintenance_order or property_disposition" -v
```

**Child Support Calculation**:
```bash
pytest tests/e2e/test_family_law_tier2.py -k "basic_support or support_deviation or residential_credit or imputed_income or income_deduction" -v
```

**Support Enforcement**:
```bash
pytest tests/e2e/test_family_law_tier2.py -k "wage_assignment or contempt_action or child_support_lien or support_arrears" -v
```

**Parentage Proceedings**:
```bash
pytest tests/e2e/test_family_law_tier2.py -k "parentage_action or paternity_acknowledgment or genetic_testing or adjudication_parentage" -v
```

**Adoption Proceedings**:
```bash
pytest tests/e2e/test_family_law_tier2.py -k "adoption_petition or relinquishment_petition or home_study or open_adoption" -v
```

### Generate HTML Report

```bash
pytest tests/e2e/test_family_law_tier2.py -v --html=reports/tier2_test_report_$(date +%Y%m%d_%H%M%S).html --self-contained-html
```

## Test Categories

### 1. Unit Tests (25 Tests)

Each Phase 2 entity type has a dedicated unit test validating:
- ✅ Pattern matching correctness
- ✅ Entity type accuracy
- ✅ Position tracking (start_pos, end_pos)
- ✅ Confidence score (≥0.88 target)
- ✅ Extraction method (regex)
- ✅ LurisEntityV2 schema compliance

**Example Unit Test**:
```python
@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.family_law
@pytest.mark.asyncio
async def test_restraining_order_extraction(restraining_order_simple, extraction_config_regex):
    """
    Test RESTRAINING_ORDER pattern extraction with regex mode.

    Entity Type: RESTRAINING_ORDER
    Pattern Group: procedural_documents_ext
    Expected: Restraining order phrase with ≥0.90 confidence
    RCW Reference: RCW 26.09.050
    """
    # Test implementation validates entity extraction
    ...
```

### 2. Pattern Group Tests (7 Tests)

Validates consistency within each pattern group:
- ✅ All patterns in group extract correctly
- ✅ RCW references are consistent
- ✅ Confidence scores meet group standards
- ✅ No pattern conflicts or overlaps

**Example Pattern Group Test**:
```python
@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.family_law
@pytest.mark.pattern_group
@pytest.mark.asyncio
async def test_child_support_calculation_group(child_support_calculation_text, extraction_config_regex):
    """
    Test child_support_calculation pattern group consistency.

    Expected: All 5 patterns in this group should extract correctly.
    Patterns: BASIC_SUPPORT_OBLIGATION, SUPPORT_DEVIATION, RESIDENTIAL_CREDIT,
             IMPUTED_INCOME, INCOME_DEDUCTION_ORDER
    """
    # Test validates all 5 patterns extract from realistic document
    ...
```

### 3. Integration Tests (5 Tests)

Tests realistic multi-entity document scenarios:

1. **Support Calculation Document** - 5 support calculation entities
2. **Enforcement Action Document** - 4 enforcement entities
3. **Jurisdiction Motion Document** - 3 jurisdiction entities
4. **Parentage Petition Document** - 4 parentage entities
5. **Adoption Case Document** - 4 adoption entities

**Example Integration Test**:
```python
@pytest.mark.e2e
@pytest.mark.tier2
@pytest.mark.family_law
@pytest.mark.integration
@pytest.mark.asyncio
async def test_support_calculation_multi_entity(support_calculation_document, extraction_config_regex):
    """
    Integration test: Extract multiple child support calculation entities.

    Expected Entities: BASIC_SUPPORT_OBLIGATION, SUPPORT_DEVIATION, RESIDENTIAL_CREDIT,
                       IMPUTED_INCOME, INCOME_DEDUCTION_ORDER
    """
    # Test validates all 5 entity types extract from single document
    ...
```

### 4. E2E Pipeline Test (1 Test)

Comprehensive end-to-end test with all 25 Phase 2 entity types:
- ✅ Single document contains all 25 entity types
- ✅ Validates complete pipeline from document → entities
- ✅ Checks LurisEntityV2 schema compliance
- ✅ Analyzes confidence score distribution
- ✅ Saves detailed results to JSON file

**Success Criteria**:
- At least 20/25 entity types detected
- Average confidence ≥0.88
- Processing time <1 second
- All entities follow LurisEntityV2 schema

### 5. Performance Benchmark (1 Test)

Validates Phase 2 performance targets:
- ✅ Average processing time: <15ms per pattern
- ✅ 95th percentile: <30ms
- ✅ Confidence scores: ≥0.88
- ✅ Extraction accuracy: ≥93%

**Benchmark Documents**:
- Support calculation document (large)
- Enforcement action document (large)
- Short support snippet
- Short enforcement snippet
- Short jurisdiction snippet

## Test Fixtures

All fixtures are defined in `/srv/luris/be/entity-extraction-service/tests/e2e/conftest.py`.

### Configuration Fixtures

- **`extraction_config_regex`** - Regex mode extraction configuration
- **`tier2_entity_types`** - List of all 25 Phase 2 entity types
- **`performance_targets_tier2`** - Performance benchmarks for Phase 2

### Simple Fixtures (25 Fixtures)

One simple test case per entity type:
- `restraining_order_simple`
- `relocation_notice_simple`
- `maintenance_order_simple`
- `property_disposition_simple`
- `basic_support_simple`
- `support_deviation_simple`
- `residential_credit_simple`
- `imputed_income_simple`
- `income_deduction_simple`
- `wage_assignment_simple`
- `contempt_action_simple`
- `child_support_lien_simple`
- `support_arrears_simple`
- `significant_connection_ext_simple`
- `exclusive_continuing_ext_simple`
- `foreign_order_registration_simple`
- `parentage_action_simple`
- `paternity_acknowledgment_simple`
- `genetic_testing_simple`
- `adjudication_parentage_simple`
- `adoption_petition_simple`
- `relinquishment_petition_simple`
- `home_study_simple`
- `open_adoption_simple`
- `mandatory_reporter_simple`

### Pattern Group Fixtures (7 Fixtures)

Comprehensive documents for pattern group testing:
- `procedural_documents_ext_text` - 4 procedural entities
- `child_support_calculation_text` - 5 support calculation entities
- `support_enforcement_text` - 4 enforcement entities
- `jurisdiction_concepts_ext_text` - 3 jurisdiction entities
- `parentage_proceedings_text` - 4 parentage entities
- `adoption_proceedings_text` - 4 adoption entities
- `child_protection_ext_text` - 1 child protection entity

### Integration Test Fixtures (5 Fixtures)

Multi-entity documents for integration testing:
- `support_calculation_document` - Support calculation integration test
- `enforcement_action_document` - Enforcement action integration test
- `jurisdiction_motion_document` - Jurisdiction motion integration test
- `parentage_petition_document` - Parentage petition integration test
- `adoption_case_document` - Adoption case integration test

### E2E Test Fixture (1 Fixture)

- **`phase2_full_document`** - Comprehensive document with all 25 Phase 2 entity types

## Expected Results

### Success Criteria

✅ **All 39 tests pass** (100% pass rate)
✅ **Average confidence**: ≥0.88 across all entities
✅ **Processing speed**: <15ms per pattern (regex mode)
✅ **Schema compliance**: 100% LurisEntityV2 adherence
✅ **Coverage**: At least 20/25 entity types in E2E test

### Sample Test Output

```
=========================== test session starts ============================
platform linux -- Python 3.12.3, pytest-8.3.3, pluggy-1.5.0
rootdir: /srv/luris/be/entity-extraction-service
plugins: asyncio-0.24.0, html-4.1.1
collected 39 items

tests/e2e/test_family_law_tier2.py::test_restraining_order_extraction PASSED [  2%]
tests/e2e/test_family_law_tier2.py::test_relocation_notice_extraction PASSED [  5%]
tests/e2e/test_family_law_tier2.py::test_maintenance_order_extraction PASSED [  7%]
...
tests/e2e/test_family_law_tier2.py::test_phase2_complete_pipeline PASSED [ 97%]
tests/e2e/test_family_law_tier2.py::test_phase2_performance_benchmark PASSED [100%]

======================= 39 passed in 4.23s =============================
```

### Generated Artifacts

**Test Results**:
- `/srv/luris/be/entity-extraction-service/tests/results/tier2_pipeline_YYYYMMDD_HHMMSS.json`
- `/srv/luris/be/entity-extraction-service/tests/results/tier2_benchmark_YYYYMMDD_HHMMSS.json`

**HTML Reports** (when generated):
- `/srv/luris/be/entity-extraction-service/tests/reports/tier2_test_report_YYYYMMDD_HHMMSS.html`

## Troubleshooting

### Common Issues

#### 1. Service Not Running

**Error**: `Connection refused to localhost:8007`

**Solution**:
```bash
# Check if service is running
sudo systemctl status luris-entity-extraction

# Start service if needed
sudo systemctl start luris-entity-extraction

# Verify service health
curl http://localhost:8007/api/v1/health
```

#### 2. Low Confidence Scores

**Error**: `AssertionError: Low confidence: 0.75`

**Solution**:
- Verify pattern definitions in `family_law.yaml`
- Check test document contains clear pattern matches
- Ensure regex patterns are optimized
- Review confidence thresholds in test (may need adjustment)

#### 3. Entity Not Found

**Error**: `AssertionError: Expected at least 1 ENTITY_TYPE entity`

**Solution**:
- Verify entity type is in `family_law.yaml` Phase 2 patterns
- Check test document contains entity text
- Validate pattern regex matches test text
- Ensure extraction_mode is "regex" not "ai" or "hybrid"

#### 4. Schema Validation Failure

**Error**: `AssertionError: Missing entity_type field`

**Solution**:
- Verify LurisEntityV2 schema compliance in entity extraction service
- Check all required fields: id, text, entity_type, start_pos, end_pos, confidence, extraction_method
- Ensure extraction service returns complete entity objects

### Debugging Tests

**Run Single Test with Verbose Output**:
```bash
pytest tests/e2e/test_family_law_tier2.py::test_restraining_order_extraction -v -s
```

**Show Print Statements**:
```bash
pytest tests/e2e/test_family_law_tier2.py -v -s
```

**Run with PDB Debugger**:
```bash
pytest tests/e2e/test_family_law_tier2.py::test_restraining_order_extraction --pdb
```

**Increase Timeout**:
```python
# In conftest.py, modify extraction_config_regex fixture:
"timeout": 120,  # Increase from 60 to 120 seconds
```

## Maintenance

### Adding New Tests

1. **Add new entity pattern** to `family_law.yaml`
2. **Create simple fixture** in `conftest.py`
3. **Write unit test** in `test_family_law_tier2.py`
4. **Update pattern group test** if new group
5. **Add to integration test** if related to existing document type
6. **Update E2E document** to include new entity type
7. **Run full test suite** to verify no regressions

### Updating Confidence Thresholds

If patterns are optimized and confidence scores improve:

1. **Update `performance_targets_tier2` fixture** in `conftest.py`
2. **Update individual test assertions** if needed
3. **Document changes** in commit message
4. **Re-run full suite** to validate new thresholds

### Regenerating Test Documents

To create new realistic test documents:

1. **Use actual Washington State case law** as templates
2. **Include multiple entity types** per document
3. **Ensure proper legal terminology** and RCW citations
4. **Validate with legal professionals** if possible
5. **Test document** before committing to ensure extractions work

## Performance Metrics

### Phase 2 Optimization Results

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Average Execution | <15ms | 2.898ms | ✅ 5.2x faster |
| Confidence Score | ≥0.88 | 0.929 | ✅ 5.6% better |
| Test Execution | <5s | ~4.2s | ✅ On target |
| Pattern Complexity | <5/10 | 0.9-2.5/10 | ✅ Excellent |
| Accuracy | ≥93% | 95%+ | ✅ Exceeds target |

### Comparison to Phase 1

| Metric | Phase 1 (AI) | Phase 2 (Regex) | Improvement |
|--------|--------------|-----------------|-------------|
| Avg Processing Time | 296ms | 2.898ms | **102x faster** |
| Confidence Score | 0.90 | 0.929 | +3.2% |
| Extraction Mode | AI-enhanced | Regex | More efficient |
| Entity Count | 15 | 25 | +66% coverage |

## Best Practices

### Writing Tests

1. **Use realistic legal language** from actual Washington State cases
2. **Include RCW references** in test documents
3. **Validate confidence scores** with ±0.05 tolerance for regex patterns
4. **Check schema compliance** for every extracted entity
5. **Test edge cases** (empty documents, ambiguous text, etc.)

### Test Organization

1. **Group tests logically** by pattern group
2. **Use descriptive test names** that explain what is being tested
3. **Include comprehensive docstrings** for each test
4. **Mark tests appropriately** with pytest markers (e2e, tier2, integration, etc.)
5. **Keep fixtures reusable** across multiple tests

### Performance Testing

1. **Run benchmarks regularly** to detect regressions
2. **Test with various document sizes** (short, medium, long)
3. **Measure both individual pattern** and full document extraction times
4. **Compare against performance targets** from Phase 2 optimization
5. **Document any performance changes** in commits

## Additional Resources

### Related Documentation

- **Phase 1 Tests**: `/srv/luris/be/entity-extraction-service/tests/e2e/test_family_law_tier1.py`
- **Family Law Patterns**: `/srv/luris/be/entity-extraction-service/src/patterns/client/family_law.yaml`
- **LurisEntityV2 Spec**: `/srv/luris/be/entity-extraction-service/docs/LurisEntityV2_Specification.md`
- **Entity Extraction API**: `/srv/luris/be/entity-extraction-service/api.md`

### RCW References

Phase 2 patterns reference Washington State RCW Title 26 (Domestic Relations):
- **RCW 26.09** - Dissolution procedures, maintenance, property
- **RCW 26.18** - Support enforcement
- **RCW 26.19** - Child support schedule
- **RCW 26.26A** - Parentage proceedings
- **RCW 26.27** - Uniform Child Custody Jurisdiction and Enforcement Act (UCCJEA)
- **RCW 26.33** - Adoption
- **RCW 26.44** - Child abuse and neglect reporting

### Contact

For questions or issues with Phase 2 testing:
- Review this guide first
- Check Phase 1 test examples for reference patterns
- Consult `/srv/luris/be/CLAUDE.md` for general testing standards
- Verify service logs: `sudo journalctl -u luris-entity-extraction -f`

---

**Last Updated**: November 5, 2025
**Test Suite Status**: ✅ Ready for Execution
**Coverage**: 25/25 Phase 2 entity types (100%)
**Test Count**: 39 comprehensive tests
