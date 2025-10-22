# Dobbs.pdf Entity Extraction Test Results

## Test Execution Summary
**Date**: September 5, 2025  
**Document**: Dobbs v. Jackson Women's Health Organization (2022)  
**File**: `/srv/luris/be/tests/docs/dobbs.pdf`  
**Document Size**: 461,994 characters

## Test Results by Extraction Mode

### 1. Regex Extraction (SUCCESS)
- **Status**: ✓ Completed successfully
- **Processing Time**: 32.87 seconds
- **Entities Found**: 6,031
- **Citations Found**: 0
- **Performance**: ~183 entities/second
- **Issues**: All entities marked as "UNKNOWN" type in summary (data structure issue)

### 2. SpaCy Extraction (FAILED)
- **Status**: ✗ Not supported
- **Error**: "Invalid extraction_mode. Must be one of: ['regex', 'ai_enhanced', 'hybrid']"
- **Note**: SpaCy mode has been removed from supported modes

### 3. AI-Enhanced Extraction (TIMEOUT)
All AI-enhanced strategies timed out after 120 seconds:

| Strategy | Status | Time |
|----------|--------|------|
| base_extraction | TIMEOUT | 120s |
| enhanced_extraction | TIMEOUT | 120s |
| structured_extraction | TIMEOUT | 120s |
| graph_aware_extraction | TIMEOUT | 120s |
| legal_specialized_extraction | TIMEOUT | 120s |

**Root Cause**: Document size (462K chars) exceeds practical processing limits for LLM

### 4. Hybrid Extraction (TIMEOUT)
- **Full Document**: TIMEOUT after 180 seconds
- **Sample (50K chars)**: TIMEOUT after 60 seconds
- **Issue**: Even small samples cause timeouts in hybrid mode

## Key Findings

### Performance Bottlenecks
1. **Document Size**: Dobbs.pdf (462K chars) is too large for AI/hybrid modes
2. **LLM Processing**: vLLM service (IBM Granite 3.3 2B) receiving requests but timing out
3. **Chunking Required**: Need to process in much smaller chunks (<10K chars) for AI modes

### Entity Type Coverage (Regex Mode)
Despite showing "UNKNOWN" in summary, actual entities include:
- PARTY (multiple instances)
- COURT (multiple instances)
- GOVERNMENT_ENTITY
- LAW_FIRM
- ADDRESS
- CFR_CITATION
- FEDERAL_REGISTER
- EXECUTIVE_ORDER

### Data Structure Issues
1. Entity type field inconsistency between extraction and summary
2. No citations detected despite legal document nature
3. Confidence scores present but not properly aggregated

## Recommendations

### Immediate Actions
1. **Fix Entity Type Mapping**: Resolve "UNKNOWN" type issue in results aggregation
2. **Implement Chunking**: Process documents >50K chars in smaller segments
3. **Adjust Timeouts**: Increase timeout for large documents or implement streaming

### Performance Optimization
1. **Adaptive Chunking**: Use smaller chunks (5-10K chars) for AI modes
2. **Parallel Processing**: Process chunks concurrently for AI extraction
3. **Cache Results**: Store extraction results for document segments

### Testing Strategy
1. **Baseline Testing**: Use smaller test documents for AI mode validation
2. **Progressive Testing**: Start with small chunks, gradually increase size
3. **Mode Selection**: Default to regex for large documents, AI for specific sections

## Service Status

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| Document Upload | 8008 | ✓ Running | Working correctly |
| Entity Extraction | 8007 | ✓ Running | Regex mode functional |
| vLLM (LLM) | 8080 | ✓ Running | Processing but slow for large docs |
| vLLM (Embeddings) | 8081 | Unknown | Not tested in this run |

## Next Steps

1. **Create chunked extraction pipeline** for large documents
2. **Fix entity type mapping** in results aggregation
3. **Test with smaller documents** to validate AI modes
4. **Implement progress tracking** for long-running extractions
5. **Add citation extraction patterns** for legal documents

## Test Artifacts

- Full regex results: `/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results/dobbs_regex_20250905_182143.json`
- Test logs: Available in service journals
- Sample entities: 6,031 entities extracted successfully via regex

## Conclusion

The Dobbs.pdf extraction test revealed that:
- Regex extraction works well and is fast (32.87s for 462K chars)
- AI-enhanced modes need significant optimization for large documents
- Document chunking is essential for AI/hybrid modes
- The system can handle large documents but needs mode-appropriate strategies