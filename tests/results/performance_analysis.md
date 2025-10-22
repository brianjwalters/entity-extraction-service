# Entity Extraction Service - Performance Analysis Report

**Generated:** 2025-10-15 18:55:53

**Total Tests Analyzed:** 6

---

## Executive Summary

- **Average Execution Time:** 50.66s
- **Execution Time Range:** 20.25s - 139.51s
- **Average Entities Extracted:** 8.7 entities/test
- **Average Extraction Rate:** 0.232 entities/second
- **Average Confidence Score:** 0.952

---

## Performance Metrics

### Execution Time Analysis

| Metric | Value |
|--------|-------|
| Mean | 50.66s |
| Median | 36.72s |
| Std Dev | 45.04s |
| Min | 20.25s |
| Max | 139.51s |


### Token Usage Efficiency

| Metric | Value |
|--------|-------|
| Avg Tokens per Character | 0.2500 |
| Avg Tokens per Entity | 1846.7 |
| Avg Characters per Entity | 7386.8 |


### Entity Extraction Throughput

| Metric | Value |
|--------|-------|
| Mean | 0.232 entities/sec |
| Median | 0.259 entities/sec |
| Min | 0.043 entities/sec |
| Max | 0.311 entities/sec |

---

## Correlation Analysis

| Correlation | Coefficient | Interpretation |
|-------------|-------------|----------------|
| Time Vs Doc Size | 0.983 | Strong correlation |
| Time Vs Entity Count | -0.038 | No significant correlation |
| Time Vs Tokens | 0.983 | Strong correlation |
| Entities Vs Doc Size | -0.220 | Weak correlation |
| Confidence Vs Time | -0.047 | No significant correlation |

---

## Strategy Comparison

| Strategy | Tests | Avg Time (s) | Min Time (s) | Max Time (s) | Avg Entities | Entities/Sec | Avg Confidence |
|----------|-------|--------------|--------------|--------------|--------------|--------------|----------------|
| single_pass | 5 | 32.89 | 20.25 | 48.25 | 9.2 | 0.280 | 0.953 |
| three_wave | 1 | 139.51 | 139.51 | 139.51 | 6.0 | 0.043 | 0.942 |


### Key Findings:

- **Speed:** `single_pass` is **324.1% faster** than `three_wave`
- **Entity Extraction:** `three_wave` extracts **34.8% fewer** entities on average
- **Confidence:** `three_wave` has **1.2% lower** average confidence

---

## Performance Bottlenecks

**Identified 1 performance bottleneck(s):**

| Test ID | Document | Time (s) | Strategy | Tokens | Entities | Issue |
|---------|----------|----------|----------|--------|----------|-------|
| 75343531 | case_004 | 139.51 | three_wave | 41973 | 6 | Significantly slower than average |

---

## Quality vs Performance Analysis

| Metric | Value |
|--------|-------|
| Average Confidence Score | 0.952 |
| Min Confidence Score | 0.930 |
| Max Confidence Score | 1.000 |
| Confidence-Time Correlation | -0.047 |


✅ **Finding:** Low correlation indicates quality is maintained across different processing speeds.


---

## Performance Optimization Recommendations

1. ✅ STRATEGY OPTIMIZATION: single_pass is 76.4% faster than three_wave (32.89s vs 139.51s). Prioritize single_pass for similar workloads.

2. ⚠️ DOCUMENT SIZE BOTTLENECK: Strong correlation (0.98) between document size and execution time. Consider chunking strategies for large documents.

3. ⚠️ EXECUTION TIME: Average execution time (50.66s) exceeds 30s. Consider parallel processing or caching strategies.

4. ⚠️ EXTRACTION RATE: Average extraction rate (0.232 entities/sec) is low. Consider optimizing pattern matching or LLM processing.

5. ✅ QUALITY MAINTAINED: Low correlation (-0.05) between confidence and time suggests quality is maintained across different speeds.


---

## Conclusion

The entity extraction service demonstrates **moderate** performance with:

- Average processing time of **50.66 seconds** per test
- Entity extraction rate of **0.232 entities/second**
- Consistent high-quality results with **95.2%** average confidence


The `single_pass` strategy offers optimal performance for most workloads, 
achieving **32.89s** average execution time.
