# Entity Display Feature - Test Framework Enhancement

## Overview

The Entity Extraction Test Framework now includes **enhanced entity display** in console output, showing all extracted entities, entity type breakdowns, and entity relationships in terminal-friendly tables.

## Features Implemented

### 1. Entity Table Display
- **Terminal-friendly table** with Unicode box-drawing characters
- Shows: Entity number, type, text, position, confidence
- Configurable entity limit (default: 50, max: unlimited)
- Pagination message when entities exceed limit

### 2. Entity Type Breakdown
- **Count and average confidence** per entity type
- Sorted by count (descending)
- Shows top 10 types by default
- Displays remaining type count if truncated

### 3. Entity Relationships Display
- **Wave 4 relationship extraction** results
- Shows: Relationship type, source/target entities, confidence, evidence
- Configurable display limit (default: 20 relationships)
- Entity lookup for readable relationship display

## Usage

### Command Line Interface

```bash
# Default behavior (50 entities displayed)
python -m tests.test_framework.test_runner --chars 10000

# Show only first 10 entities
python -m tests.test_framework.test_runner --chars 10000 --max-entities 10

# Show all entities (no limit)
python -m tests.test_framework.test_runner --chars 10000 --max-entities 0

# Disable entity display (summary only)
python -m tests.test_framework.test_runner --chars 10000 --no-entity-display

# Full document with entity display
python -m tests.test_framework.test_runner --max-entities 100
```

### Programmatic Usage

```python
from tests.test_framework.test_runner import TestRunner

# Create runner
runner = TestRunner(char_limit=10000)

# Run test with custom entity display options
success = runner.run_test_with_options(
    show_entities=True,  # Enable entity display
    max_entities=50      # Show up to 50 entities
)

# Or use metrics collector directly
from tests.test_framework.metrics_collector import MetricsCollector

collector = MetricsCollector()
metrics = collector.collect_metrics(api_response, execution_time)

# Format with entity display
summary = collector.format_metrics_summary(
    metrics,
    show_entities=True,
    max_entities=50
)
print(summary)
```

## Output Examples

### Default Output (50 entities max)

```
======================================================================
Entity Extraction Test Results
======================================================================
Test ID: test_1760889741115
Document: test_doc
Timestamp: 2025-10-19 10:02:21

Routing Decision:
  Strategy: single_pass
  Prompt Version: v2
  Estimated Tokens: 5,000
  Estimated Duration: 1.50s

Wave Execution:
  Wave 1:
    Entities: 5
    Tokens: 4,500
    Duration: 1.20s
    Types: 4

Entity Distribution:
  Total Entities: 5
  Unique Types: 4
  Avg Confidence: 0.932
  Confidence Range: [0.880, 0.980]

Performance:
  Total Duration: 1.20s
  Entities/Second: 4.17
  Tokens/Second: 3750.00
  Avg Wave Latency: 1.20s
  Total Tokens: 4,500

Quality:
  Avg Confidence: 0.932
  High Confidence: 4 (≥0.9)
  Medium Confidence: 1 (0.7-0.9)
  Low Confidence: 0 (<0.7)
  Validation: ✅ PASSED
======================================================================

Extracted Entities (5 total):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ #   ┃ Type                 ┃ Text                                     ┃ Position     ┃ Conf   ┃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 1   ┃ STATUTE_CITATION     ┃ 18 U.S.C. § 922(g)(8)                    ┃ [0-21]       ┃ 0.950 ┃
┃ 2   ┃ CASE_CITATION        ┃ United States v. Rahimi                  ┃ [100-123]    ┃ 0.980 ┃
┃ 3   ┃ COURT                ┃ Supreme Court of the United States       ┃ [200-234]    ┃ 0.920 ┃
┃ 4   ┃ DATE                 ┃ June 21, 2024                            ┃ [300-313]    ┃ 0.880 ┃
┃ 5   ┃ STATUTE_CITATION     ┃ 28 U.S.C. § 1331                         ┃ [400-416]    ┃ 0.930 ┃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Entity Type Breakdown:
  • STATUTE_CITATION: 2 entities (avg confidence: 0.940)
  • CASE_CITATION: 1 entities (avg confidence: 0.980)
  • COURT: 1 entities (avg confidence: 0.920)
  • DATE: 1 entities (avg confidence: 0.880)

Entity Relationships (2 total):

  1. CITES (confidence: 0.900)
     Source: United States v. Rahimi
     Target: 18 U.S.C. § 922(g)(8)
     Evidence: "In United States v. Rahimi, the Court analyzed 18 U.S.C. § 922(g)(8)"

  2. DECIDED_BY (confidence: 0.950)
     Source: United States v. Rahimi
     Target: Supreme Court of the United States
     Evidence: "United States v. Rahimi was decided by the Supreme Court"
```

### Limited Display (--max-entities 2)

```
Extracted Entities (5 total):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ #   ┃ Type                 ┃ Text                                     ┃ Position     ┃ Conf   ┃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 1   ┃ STATUTE_CITATION     ┃ 18 U.S.C. § 922(g)(8)                    ┃ [0-21]       ┃ 0.950 ┃
┃ 2   ┃ CASE_CITATION        ┃ United States v. Rahimi                  ┃ [100-123]    ┃ 0.980 ┃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

... and 3 more entities (use --max-entities 0 to show all)
```

### Summary Only (--no-entity-display)

```
======================================================================
Entity Extraction Test Results
======================================================================
[... summary sections only, no entity table ...]
======================================================================
```

## Implementation Details

### Files Modified

1. **tests/test_framework/metrics_collector.py**
   - Added `format_entities_table()` method (lines 327-373)
   - Added `format_entity_type_breakdown()` method (lines 375-419)
   - Added `format_relationships_table()` method (lines 421-470)
   - Updated `format_metrics_summary()` with entity display parameters (lines 472-548)

2. **tests/test_framework/test_runner.py**
   - Added `--max-entities` CLI argument (lines 427-432)
   - Added `--no-entity-display` CLI argument (lines 433-437)
   - Added `run_test_with_options()` method (lines 306-389)
   - Updated `main()` to use new options (lines 551-556)

### Key Design Decisions

1. **Backward Compatibility**: Default behavior shows entities (show_entities=True, max_entities=50)
2. **Unicode Box Drawing**: Used Unicode characters (━, ┃) for clean terminal display
3. **Flexible Field Mapping**: Supports both `type`/`entity_type`, `start`/`start_pos`, `end`/`end_pos` field names
4. **Performance**: Efficient pagination with `max_display` parameter (0 = unlimited)
5. **Relationships**: Automatic display when relationships exist in API response
6. **Type Safety**: Proper type hints for all methods (List[Dict[str, Any]], int, str, bool)

### Schema Compatibility

Works with both field naming conventions:
- **Legacy**: `type`, `start`, `end`
- **LurisEntityV2**: `entity_type`, `start_pos`, `end_pos`

All entities from `/api/v2/process/extract` endpoint are automatically displayed.

## Configuration Options

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--max-entities` | int | 50 | Maximum entities to display (0 = unlimited) |
| `--no-entity-display` | flag | False | Disable entity table (summary only) |
| `--chars` | int | None | Limit document to first N characters |
| `--document` | Path | Rahimi.pdf | Path to test document |
| `--verbose` | flag | False | Enable verbose logging |

### Method Parameters

**`format_metrics_summary(metrics, show_entities, max_entities)`**
- `metrics`: ComprehensiveMetrics instance
- `show_entities`: bool (default: True) - Show entity table
- `max_entities`: int (default: 50) - Max entities to display (0 = unlimited)

**`format_entities_table(entities, max_display)`**
- `entities`: List[Dict[str, Any]] - Entity list
- `max_display`: int (default: 50) - Max entities (0 = unlimited)

**`format_entity_type_breakdown(entities, top_n)`**
- `entities`: List[Dict[str, Any]] - Entity list
- `top_n`: int (default: 10) - Show top N types

**`format_relationships_table(relationships, entities, max_display)`**
- `relationships`: List[Dict[str, Any]] - Relationship list
- `entities`: List[Dict[str, Any]] - Entity list for lookup
- `max_display`: int (default: 20) - Max relationships (0 = unlimited)

## Testing

### Quick Test

```bash
# Activate venv
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Test with small document (10K chars)
python -m tests.test_framework.test_runner --chars 10000

# Test with limited entity display
python -m tests.test_framework.test_runner --chars 10000 --max-entities 10

# Test with entity display disabled
python -m tests.test_framework.test_runner --chars 10000 --no-entity-display

# Test with unlimited entities
python -m tests.test_framework.test_runner --chars 10000 --max-entities 0
```

### Expected Behavior

✅ **Test 1** (Default): Shows up to 50 entities in table + type breakdown + relationships
✅ **Test 2** (Limited): Shows first 10 entities + "... and N more entities" message
✅ **Test 3** (Disabled): Shows summary statistics only (no entity table)
✅ **Test 4** (Unlimited): Shows all entities regardless of count

## Benefits

1. **Immediate Visibility**: See extracted entities directly in console output
2. **Quality Validation**: Quickly verify entity extraction quality and accuracy
3. **Type Analysis**: Understand entity type distribution at a glance
4. **Relationship Insight**: See entity relationships with evidence
5. **Flexible Control**: Configure display based on output needs
6. **Performance**: Efficient pagination for large entity sets
7. **Debugging**: Rapid debugging with entity position and confidence information

## Future Enhancements

- [ ] Color-coded confidence levels (high/medium/low)
- [ ] Entity filtering by type (e.g., show only STATUTE_CITATION)
- [ ] Export entity table to CSV/JSON
- [ ] Interactive entity browser (curses-based TUI)
- [ ] Entity deduplication detection and highlighting
- [ ] Cross-document entity comparison

## Dependencies

- Python 3.10+
- No new external dependencies (uses built-in collections, dataclasses, typing)
- Compatible with existing test framework infrastructure

## Migration Notes

### Breaking Changes
**NONE** - Backward compatible with existing code.

### Deprecations
**NONE** - All existing methods and interfaces maintained.

### New Features
- `format_entities_table()` - New public method
- `format_entity_type_breakdown()` - New public method
- `format_relationships_table()` - New public method
- `run_test_with_options()` - New runner method
- `--max-entities` CLI argument - New option
- `--no-entity-display` CLI argument - New option

## Support

For issues or questions:
- Check `/srv/luris/be/entity-extraction-service/tests/test_framework/` for implementation
- Review test output for examples
- Consult `/srv/luris/be/entity-extraction-service/api.md` for API details

---

**Last Updated**: October 19, 2025
**Version**: 1.0.0
**Status**: ✅ Production Ready
