# Wave Chart Fix Summary

## Problem Description
The dashboard at `/srv/luris/be/entity-extraction-service/tests/results/dashboard.html` had 2 empty charts:
- **Wave Execution Times** chart (showing no data)
- **Entities Per Wave** chart (showing no data)

## Root Cause
In `/srv/luris/be/entity-extraction-service/tests/test_framework/html_generator.py`:
- Lines 375-380: The code used `latest_test = test_results[-1]` to extract wave data
- The latest test in the test history was a "single_pass" strategy with an empty `waves: []` array
- This resulted in empty chart data arrays: `wave_labels: []`, `wave_durations: []`, `wave_entities: []`
- Chart.js rendered empty charts with no explanation

## Solution Implemented

### 1. Updated `_prepare_chart_data()` Method (Lines 375-387)

**Before:**
```python
# Wave execution (use latest test)
latest_test = test_results[-1]
waves = latest_test.get("waves", [])
wave_labels = [f"Wave {w['wave_number']}" for w in waves]
wave_durations = [w["duration_seconds"] for w in waves]
wave_entities = [w["entities_extracted"] for w in waves]
```

**After:**
```python
# Wave execution (search for most recent test with wave data)
wave_labels = []
wave_durations = []
wave_entities = []

# Search test results in reverse order for most recent test with wave data
for test_result in reversed(test_results):
    waves = test_result.get("waves", [])
    if waves:  # Found test with wave data
        wave_labels = [f"Wave {w['wave_number']}" for w in waves]
        wave_durations = [w["duration_seconds"] for w in waves]
        wave_entities = [w["entities_extracted"] for w in waves]
        break
```

**Improvement:** Now searches through test history for the most recent test containing wave data, rather than blindly using the latest test.

### 2. Updated `_get_chart_scripts()` Method (Lines 439-474, 477-511)

Added JavaScript conditional logic to both wave charts:

**Wave Execution Times Chart:**
```javascript
(function() {
    const waveLabels = [...];
    const waveDurations = [...];
    const canvas = document.getElementById('waveTimesChart');

    if (waveLabels.length === 0 || waveDurations.length === 0) {
        // Display informative message when no wave data
        const ctx = canvas.getContext('2d');
        canvas.height = 200;
        ctx.font = '16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.fillStyle = '#718096';
        ctx.textAlign = 'center';
        ctx.fillText('No multi-wave test data available.', canvas.width / 2, canvas.height / 2 - 20);
        ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.fillText('Run a three_wave or four_wave test to see wave breakdown.', canvas.width / 2, canvas.height / 2 + 10);
    } else {
        new Chart(canvas, {
            // Chart.js configuration...
        });
    }
})();
```

**Entities Per Wave Chart:** Same pattern applied.

**Improvement:** Charts now gracefully handle empty wave data by displaying an informative message explaining why the data is missing and how to generate it.

## Expected Behavior

### Scenario 1: Historical Test with Wave Data Exists
- Dashboard searches test history for most recent test with wave data
- Displays actual wave breakdown in both charts
- Shows wave execution times and entity counts per wave

### Scenario 2: No Historical Test with Wave Data
- Dashboard detects empty wave arrays
- Displays informative message in both wave charts:
  - **Line 1:** "No multi-wave test data available."
  - **Line 2:** "Run a three_wave or four_wave test to see wave breakdown."
- Other 4 charts continue to work correctly

## Files Modified
- `/srv/luris/be/entity-extraction-service/tests/test_framework/html_generator.py`
  - Modified `_prepare_chart_data()` method (lines 375-387)
  - Modified `_get_chart_scripts()` method (lines 439-474, 477-511)

## Testing & Validation

### Test 1: Dashboard Generation
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python -m tests.test_framework.test_runner --dashboard-only
```
**Result:** ✅ Dashboard regenerated successfully with informative messages

### Test 2: Dashboard with Wave Data
Created mock test with wave data containing 4 waves:
- Wave 1: 0.6s, 120 entities
- Wave 2: 0.5s, 80 entities
- Wave 3: 0.7s, 60 entities
- Wave 4: 0.7s, 40 entities

**Result:** ✅ Charts display actual wave breakdown correctly

### Test 3: Dashboard without Wave Data
Created mock test with empty `waves: []` array.

**Result:** ✅ Charts display informative message as expected

### Test 4: Comprehensive Validation
All validation checks passed:
- ✅ Conditional wave data checks present in both charts
- ✅ Informative message code present in generated HTML
- ✅ Dashboard with waves displays actual data
- ✅ Dashboard without waves displays informative message
- ✅ Chart.js initialization works in else branch
- ✅ Both wave charts have conditional logic

## Benefits of This Fix

1. **Better User Experience:** Users immediately understand why charts are empty and what action to take
2. **Historical Data Support:** If wave data exists in test history, it will be displayed even if latest test doesn't have it
3. **Self-Contained Dashboard:** No external dependencies required, works offline
4. **Graceful Degradation:** Dashboard continues to work correctly with other 4 charts unaffected
5. **Clear Instructions:** Message tells users exactly what to do: run three_wave or four_wave tests

## Future Test Recommendations

To populate wave charts with actual data:
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python -m tests.test_framework.test_runner --strategy four_wave
```

This will:
1. Run entity extraction using 4-wave strategy
2. Save test results with wave breakdown
3. Automatically regenerate dashboard with populated wave charts
4. Display actual wave execution times and entity counts

## Verification

To verify the fix is working:
1. Open `/srv/luris/be/entity-extraction-service/tests/results/dashboard.html` in a browser
2. Scroll to "Wave Execution Times" chart
3. Should see informative message: "No multi-wave test data available."
4. Scroll to "Entities Per Wave" chart
5. Should see same informative message
6. All other 4 charts should display data correctly

---

**Fix Applied:** October 19, 2025
**Status:** ✅ Verified and Working
**Lines Modified:** 37 lines in `html_generator.py`
