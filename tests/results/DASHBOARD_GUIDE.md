# Entity Extraction Test Dashboard Guide

## Overview

The Entity Extraction Test Dashboard is a self-contained, interactive HTML visualization tool that provides comprehensive insights into test performance, entity extraction quality, and historical trends. The dashboard automatically updates after each test run and provides detailed metrics with Chart.js visualizations.

## Opening the Dashboard

The dashboard is a standalone HTML file that can be opened directly in any modern web browser:

### Linux/Ubuntu
```bash
# Open in default browser
xdg-open /srv/luris/be/entity-extraction-service/tests/results/dashboard.html

# Or use specific browser
firefox /srv/luris/be/entity-extraction-service/tests/results/dashboard.html
google-chrome /srv/luris/be/entity-extraction-service/tests/results/dashboard.html
```

### Direct Browser Access
Copy this path and paste into your browser's address bar:
```
file:///srv/luris/be/entity-extraction-service/tests/results/dashboard.html
```

### After Test Completion
The dashboard URL is displayed after each test run. Simply click the clickable link in the terminal output.

## Dashboard Sections

### 1. Summary Cards (Top Section)

The summary cards provide high-level metrics across all test runs:

- **Total Tests**: Total number of tests in the history
- **Avg Duration**: Average extraction time across all tests (seconds)
- **Avg Entities**: Average number of entities extracted per test
- **Avg Confidence**: Average confidence score across all entities
- **Pass Rate**: Percentage of tests that passed validation (≥0.7 avg confidence, ≥80% high/medium confidence)

**Example Interpretation**:
```
Total Tests: 15
Avg Duration: 32.5s
Avg Entities: 42
Avg Confidence: 0.89
Pass Rate: 93%
```
This indicates 15 test runs with consistent extraction quality (89% confidence) and high pass rate.

### 2. Interactive Charts

#### Performance Over Time
**What it shows**: Extraction duration trend across test runs

**Use cases**:
- Detect performance regressions after code changes
- Identify optimization improvements
- Track impact of document size on processing time

**Interpretation**:
- Upward trend → Performance degradation, investigate recent changes
- Downward trend → Performance improvements, optimizations working
- Flat line → Consistent performance, no regressions

#### Wave Execution Times
**What it shows**: Time spent in each extraction wave (Waves 1-4)

**Availability**: Only displays when multi-wave test data exists

**Use cases**:
- Identify which wave consumes most processing time
- Optimize slow waves
- Understand wave execution balance

**Missing Data Message**:
```
No multi-wave test data available.
Run a three_wave or four_wave test to see wave breakdown.
```

**Solution**: Run a larger test to trigger multi-wave strategy:
```bash
/test-entity-extraction --chars 50000
```

#### Entities Per Wave
**What it shows**: Number of entities extracted in each wave

**Availability**: Only displays when multi-wave test data exists

**Use cases**:
- Understand entity distribution across waves
- Validate wave system working correctly (Wave 1 should have most entities)
- Identify wave extraction patterns

**Expected Pattern**:
- Wave 1 (Core Legal): Highest entity count (40-60% of total)
- Wave 2 (Procedural): Medium count (20-30%)
- Wave 3 (Supporting): Medium count (15-25%)
- Wave 4 (Relationships): Lower count (5-15%)

#### Confidence Distribution
**What it shows**: Breakdown of entities by confidence level

**Confidence Levels**:
- **High Confidence** (≥0.9): Green - High-quality extractions
- **Medium Confidence** (0.7-0.9): Yellow - Acceptable quality
- **Low Confidence** (<0.7): Red - Requires review

**Use cases**:
- Assess overall extraction quality
- Identify tests with low-confidence entities
- Track quality improvements over time

**Interpretation**:
- High % green → Excellent extraction quality
- High % yellow → Acceptable but can improve
- High % red → Quality issues, review prompts and patterns

#### Top Entity Types
**What it shows**: Most frequently extracted entity types across all tests

**Use cases**:
- Understand document content patterns
- Validate extraction coverage
- Identify missing entity types

**Example**:
```
1. STATUTE_CITATION: 245 entities
2. CASE_CITATION: 187 entities
3. PARTY: 156 entities
4. COURT: 98 entities
5. DATE: 87 entities
```

#### Throughput Metrics
**What it shows**: Entities extracted per second over time

**Use cases**:
- Track extraction efficiency
- Identify performance bottlenecks
- Compare optimization strategies

**Interpretation**:
- Higher throughput → Better performance
- Declining throughput → Performance degradation
- Consistent throughput → Stable extraction speed

### 3. Recent Test Results Table

The bottom table displays the 10 most recent test runs with key metrics:

**Columns**:
- **Test ID**: Unique identifier (timestamp-based)
- **Timestamp**: When test was run
- **Strategy**: Extraction strategy used (single_pass, three_wave, four_wave)
- **Duration**: Total extraction time (seconds)
- **Entities**: Number of entities extracted
- **Avg Confidence**: Average confidence score
- **Status**: Test validation result (✅ PASSED or ❌ FAILED)

**Status Indicators**:
- ✅ **PASSED**: Avg confidence ≥0.7 AND ≥80% entities with confidence ≥0.7
- ❌ **FAILED**: Quality validation failed

**Use cases**:
- Review recent test history
- Compare test runs
- Identify failing tests
- Track strategy usage

## Wave Chart Behavior

### When Wave Data is Available

The dashboard displays two detailed wave charts:
1. **Wave Execution Times**: Stacked bar chart showing time per wave
2. **Entities Per Wave**: Bar chart showing entity counts per wave

**Trigger Conditions**:
- Test uses `three_wave`, `four_wave`, or `three_wave_chunked` strategy
- Document size triggers multi-wave routing (typically >10,000 characters)
- Wave details are present in test results

### When Wave Data is Missing

The dashboard shows an informative message:
```
No multi-wave test data available.
Run a three_wave or four_wave test to see wave breakdown.
```

**Why this happens**:
- All tests used `single_pass` strategy (small documents)
- Test document was truncated below multi-wave threshold
- No tests in history have wave data

**Solution**:
```bash
# Run a larger test to generate wave data
/test-entity-extraction --chars 50000

# Or run full document test
/test-entity-extraction
```

## Regenerating the Dashboard

### Automatic Regeneration
The dashboard updates automatically after each test run with the latest results.

### Manual Regeneration
Regenerate the dashboard from existing test history without running a new test:

```bash
/test-entity-extraction --dashboard-only
```

**Use cases**:
- Dashboard file was accidentally deleted
- Testing dashboard changes
- Viewing updated test history after multiple tests

## Dashboard Features

### Interactive Charts
- **Hover**: Shows detailed values for each data point
- **Zoom**: Click and drag to zoom on chart areas
- **Pan**: Move around zoomed charts
- **Reset**: Double-click to reset zoom

### Responsive Design
- Dashboard adapts to different screen sizes
- Mobile-friendly layout
- Print-friendly styling

### Data Persistence
- All test results stored in `test_history.jsonl`
- Dashboard reads from history file
- No data loss between regenerations

### Color Coding
- **Green**: High quality, passing tests, good performance
- **Yellow**: Medium quality, acceptable performance
- **Red**: Low quality, failing tests, performance issues
- **Blue**: Neutral information, trends, metadata

## Troubleshooting

### Dashboard Shows "No Data"
**Cause**: No tests in history or test_history.jsonl is empty

**Solution**:
```bash
# Run a test to generate data
/test-entity-extraction --chars 10000
```

### Wave Charts Empty
**Cause**: No multi-wave tests in history

**Solution**:
```bash
# Run larger test to trigger multi-wave
/test-entity-extraction --chars 50000
```

### Dashboard Won't Open
**Cause**: File path incorrect or permissions issue

**Solution**:
```bash
# Check file exists
ls -la /srv/luris/be/entity-extraction-service/tests/results/dashboard.html

# Fix permissions if needed
chmod 644 /srv/luris/be/entity-extraction-service/tests/results/dashboard.html
```

### Charts Not Rendering
**Cause**: JavaScript disabled or browser compatibility

**Solution**:
- Enable JavaScript in browser
- Use modern browser (Chrome, Firefox, Safari, Edge)
- Check browser console for errors (F12)

### Old Data Showing
**Cause**: Dashboard not regenerated after new tests

**Solution**:
```bash
# Regenerate dashboard
/test-entity-extraction --dashboard-only
```

## Advanced Usage

### Analyzing Trends

**Performance Regression Detection**:
1. Check "Performance Over Time" chart for upward trends
2. Compare recent tests to historical average
3. Investigate code changes during performance decline

**Quality Improvement Tracking**:
1. Monitor "Confidence Distribution" over time
2. Track increase in high-confidence entities
3. Correlate with prompt engineering changes

**Strategy Optimization**:
1. Compare duration across different strategies
2. Analyze wave execution times for bottlenecks
3. Optimize slow waves with targeted improvements

### Comparing Test Runs

Use the Recent Test Results table to compare:
- Different character limits (--chars parameter)
- Strategy effectiveness (single_pass vs multi-wave)
- Before/after optimization changes
- Impact of prompt template updates

### Export and Sharing

The dashboard is a standalone HTML file that can be:
- Emailed to team members
- Uploaded to documentation sites
- Embedded in reports
- Archived for historical reference

**No external dependencies required** - all CSS and JavaScript is embedded.

## Best Practices

### Regular Testing
- Run tests after code changes
- Maintain test history for trend analysis
- Archive dashboard snapshots for major releases

### Quality Gates
- Set minimum confidence threshold (≥0.7)
- Require high pass rate (≥90%)
- Monitor low-confidence entity trends

### Performance Monitoring
- Track extraction duration trends
- Set performance baselines
- Alert on significant regressions (>20% slower)

### Dashboard Maintenance
- Archive old test_history.jsonl periodically
- Keep last 100 test runs for active analysis
- Document significant test configuration changes

## Related Documentation

- **Test Command Documentation**: `.claude/commands/test-entity-extraction.md`
- **Entity Extraction Service README**: `entity-extraction-service/README.md`
- **Test Framework Code**: `tests/test_framework/metrics_collector.py`
- **Test History File**: `tests/results/test_history.jsonl`

## Support

For issues or questions:
1. Check test framework documentation
2. Review test_history.jsonl for data consistency
3. Examine browser console for JavaScript errors
4. Verify test service is running (port 8007)
5. Regenerate dashboard with `--dashboard-only` flag
