# Smart Chunking Strategy for Legal Documents

## Overview

This document describes the smart chunking strategy optimized for the Dobbs v. Jackson Women's Health Organization Supreme Court opinion and similar legal documents. The strategy balances the need to preserve legal document structure with the practical constraints of vLLM context windows.

## Strategy Rationale

### 1. Conservative Chunk Size (3000 characters)

**Rationale**: While vLLM supports 128K context, we use 3000 characters per chunk for several reasons:

- **Processing Efficiency**: Smaller chunks allow parallel processing and reduce memory overhead
- **Entity Extraction Precision**: Focused context improves entity extraction accuracy
- **Error Recovery**: If one chunk fails processing, impact is minimized
- **Context Relevance**: Keeps related legal concepts together without overwhelming the model
- **Token Budget**: ~750-1000 tokens per chunk leaves room for system prompts and responses

### 2. Legal-Aware Boundaries

**Key Principle**: Never split legal atoms - the fundamental units of legal text that must remain intact.

#### Citation Preservation
Legal citations are atomic references that lose meaning if split:
- **Case Citations**: "Roe v. Wade, 410 U.S. 113 (1973)" must remain intact
- **Statutory Citations**: "42 U.S.C. § 1983" cannot be split
- **Reporter Citations**: "123 F.3d 456" must stay together

**Implementation**: Pattern matching identifies citation boundaries and adjusts chunk splits to preserve them.

#### Quote Preservation
Legal opinions frequently quote precedents, statutes, and arguments:
- Quotes under 2000 characters are kept intact
- Longer quotes may be split at sentence boundaries
- Opening and closing quotation marks are kept together

#### Section Structure
Legal documents follow hierarchical organization:
- Roman numerals (I., II., III.) indicate major sections
- Letters (A., B., C.) indicate subsections  
- Numbers (1., 2., 3.) indicate points
- Parenthetical letters ((a), (b), (c)) indicate sub-points

**Implementation**: Section markers influence but don't force chunk boundaries.

### 3. Overlap Strategy (300 characters / 10%)

**Rationale**: Overlapping chunks provide several benefits:

- **Context Continuity**: Entities mentioned at chunk boundaries aren't lost
- **Relationship Preservation**: Legal relationships spanning chunks are maintained
- **Cross-Reference Resolution**: Citations referencing nearby text remain connected
- **Sliding Window Effect**: Improves recall for entities near boundaries

**Implementation**: Each chunk includes the last 300 characters of the previous chunk, creating a sliding window effect.

### 4. Entity Boundary Tracking

**Purpose**: Maintain entity coherence across chunk boundaries.

**Tracked Entities**:
- Case citations
- Statutes and regulations
- Constitutional provisions
- Judges and parties
- Courts and jurisdictions
- Legal concepts and doctrines
- Dates and time periods
- Precedents and holdings

**Metadata Preservation**:
- Each chunk carries metadata about entities it contains
- Entity spans crossing boundaries are noted
- Coreference chains are tracked across chunks

### 5. Smart Splitting Heuristics

**Split Priority** (in order of preference):
1. **Paragraph Boundaries**: Natural topical breaks
2. **Sentence Boundaries**: Complete thoughts preserved
3. **Semicolons**: Major clause boundaries
4. **Commas**: Last resort for clause breaks

**Forbidden Splits**:
- Within citations
- Within quoted text
- Within parenthetical expressions
- Within footnote references
- Mid-sentence citations

### 6. Performance Optimizations

#### Sequential Processing
Legal documents require maintaining narrative flow and argumentative structure. Sequential processing ensures:
- Proper section ordering
- Chronological precedent references
- Logical argument progression

#### Chunk Caching
Processed chunks are cached to enable:
- Rapid re-processing with different parameters
- Incremental updates for document revisions
- Consistent chunk IDs across processing runs

#### Validation Framework
Every chunking operation validates:
- Citation integrity (>95% preservation required)
- Quote completeness
- Section marker preservation
- Size constraint compliance
- Overlap consistency

## Validation Metrics

### Required Thresholds
- **Citation Preservation**: ≥95% of citations must remain intact
- **Quote Preservation**: ≥90% of quotes under 2000 chars intact
- **Size Compliance**: 100% of chunks within size limits
- **Overlap Consistency**: ≥90% of chunks have proper overlap

### Quality Indicators
- **Average Chunk Size**: Target ~2800 characters (leaving buffer)
- **Size Variance**: Standard deviation <500 characters
- **Entity Continuity**: >80% of entities tracked across boundaries
- **Section Coherence**: >90% of sections properly contextualized

## Testing Methodology

### 1. PDF Text Extraction
Uses pdfplumber (primary) with PyPDF2 fallback to:
- Extract text while preserving formatting
- Track page boundaries for reference
- Maintain paragraph structure

### 2. Pattern Recognition
Regex patterns identify:
- 10+ citation formats (Bluebook compliant)
- Quote boundaries with nesting support
- Section markers at 4 hierarchical levels
- Footnote references and markers

### 3. Chunk Generation
Iterative algorithm:
1. Start at document beginning
2. Calculate ideal chunk end (start + 3000)
3. Find safe split point near ideal end
4. Extract chunk with trimming
5. Calculate overlap start for next chunk
6. Repeat until document end

### 4. Validation Process
Post-processing validation:
1. Check all chunks for size compliance
2. Verify citation preservation
3. Validate quote integrity
4. Confirm overlap presence
5. Generate quality metrics

### 5. Result Reporting
Comprehensive output includes:
- JSON chunks with full metadata
- Validation report with metrics
- Error log for debugging
- Summary statistics

## Usage Examples

### Basic Usage
```python
from test_smart_chunking import LegalChunker, run_chunking_test

# Simple test run
result = run_chunking_test(
    pdf_path="/srv/luris/be/tests/docs/Dobbs.pdf",
    config_path="chunking_config.yaml"
)

# Check results
print(f"Created {len(result.chunks)} chunks")
print(f"Citation preservation: {result.validation_report['quality_metrics']['citation_preservation_rate']}%")
```

### Custom Configuration
```python
# Initialize with custom config
chunker = LegalChunker("custom_config.yaml")

# Extract and chunk
text, metadata = chunker.extract_text_from_pdf("document.pdf")
chunks = chunker.create_chunks(text, metadata)

# Validate
validation = chunker.validate_chunks(chunks, text)
```

### Programmatic Validation
```python
# Check if chunking meets requirements
if validation['quality_metrics']['citation_preservation_rate'] >= 95:
    print("✓ Chunking meets legal document standards")
else:
    print("⚠ Review chunking parameters")
```

## Integration with Entity Extraction Pipeline

### 1. Document Upload Service
Receives PDF and triggers chunking with legal-aware strategy.

### 2. Chunking Service Integration
This configuration integrates with the existing chunking service:
- Strategy: "legal_aware" 
- Config: Loaded from YAML
- Validation: Built-in quality checks

### 3. Entity Extraction Service
Processes chunks with preserved legal structure:
- Citations remain intact for accurate extraction
- Entity boundaries tracked across chunks
- Context windows optimized for vLLM

### 4. GraphRAG Service
Builds knowledge graph with:
- Complete citation networks
- Preserved legal relationships
- Section-aware entity clustering

## Benefits of This Approach

### 1. Legal Accuracy
- Preserves critical legal references
- Maintains argumentative structure
- Respects document hierarchy

### 2. Processing Efficiency
- Optimized chunk sizes for vLLM
- Parallel processing capability
- Reduced memory footprint

### 3. Extraction Quality
- Higher entity extraction precision
- Better relationship detection
- Improved coreference resolution

### 4. Flexibility
- Configurable parameters via YAML
- Extensible pattern library
- Adaptable to different legal document types

### 5. Robustness
- Comprehensive validation
- Graceful error handling
- Detailed logging and debugging

## Future Enhancements

### Short Term
- Add support for footnote preservation
- Implement table detection and handling
- Enhance quote nesting support

### Medium Term
- Machine learning-based split point prediction
- Dynamic chunk sizing based on content density
- Cross-document chunking consistency

### Long Term
- Semantic chunking with embedding similarity
- Hierarchical chunking for nested structures
- Adaptive overlap based on entity density

## Conclusion

This smart chunking strategy provides a robust foundation for processing legal documents while preserving their essential structure. By prioritizing legal accuracy while respecting technical constraints, it enables high-quality entity extraction and knowledge graph construction from complex legal texts like the Dobbs opinion.