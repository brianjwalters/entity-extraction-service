# CALES Pipeline Progressive Testing Plan

## Executive Summary
This comprehensive testing plan provides a systematic approach to evaluate the CALES (Context-Aware Legal Entity Service) pipeline using the Rahimi.pdf document. The plan enables progressive activation of pipeline components to monitor extraction quality at each stage, with visual inspection capabilities and detailed quality metrics.

## Testing Overview

### Current Baseline
- **Mode**: REGEX_ONLY
- **Document**: `/srv/luris/be/entity-extraction-service/tests/docs/Rahimi.pdf`
- **Baseline Results**: 2,736 entities extracted with 60 unique entity types
- **Service Port**: 8007

### Pipeline Components to Test
1. **REGEX_ONLY** - Pattern-based extraction (baseline)
2. **enable_fast_ai** - Lightweight NER models (DistilBERT, Legal-BERT)
3. **enable_vllm** - Direct vLLM extraction
4. **enable_coreference** - Coreference resolution
5. **enable_relationships** - Entity relationship extraction
6. **enable_unpatterned** - Unpatterned entity detection

## Phase 1: Baseline Validation (REGEX_ONLY)

### Objectives
- Establish baseline performance metrics
- Validate pattern coverage and accuracy
- Identify entity type distribution

### Configuration
```python
config = ExtractionConfig(
    mode=ExtractionMode.REGEX_ONLY,
    enable_regex=True,
    enable_fast_ai=False,
    enable_vllm=False,
    enable_context=False,
    enable_relationships=False,
    enable_unpatterned=False
)
```

### Metrics to Collect
- Total entities extracted
- Unique entity types
- Entity distribution by type
- Processing time
- Memory usage
- Pattern match confidence scores

### Quality Assessment Criteria
- **Coverage**: >= 2,500 entities expected
- **Precision**: Manual validation of 100 random entities
- **Entity Types**: >= 50 unique types
- **Performance**: < 5 seconds processing time

### Visualization Requirements
- Entity type distribution bar chart
- Entity density heatmap across document
- Sample entities table with context (first 50)

## Phase 2: AI Enhancement (enable_fast_ai)

### Objectives
- Measure improvement from lightweight NER models
- Assess entity disambiguation capabilities
- Evaluate confidence score improvements

### Configuration
```python
config = ExtractionConfig(
    mode=ExtractionMode.FAST_AI,
    enable_regex=True,
    enable_fast_ai=True,  # NEW
    enable_vllm=False,
    enable_context=True,   # Enable context for AI
    enable_relationships=False,
    enable_unpatterned=False
)
```

### Metrics to Collect
- New entities discovered by AI
- Confidence score distribution
- Entity type refinements
- Processing time increase
- GPU memory usage
- Model-specific contribution (DistilBERT vs Legal-BERT)

### Quality Assessment Criteria
- **Entity Gain**: +10-20% new entities expected
- **Confidence**: Average confidence > 0.7
- **False Positives**: < 5% error rate
- **Performance**: < 15 seconds processing time

### Visualization Requirements
- Comparison chart: REGEX vs REGEX+AI
- Confidence score distribution histogram
- New entities highlight table
- Model contribution breakdown

## Phase 3: Deep Learning Enhancement (enable_vllm)

### Objectives
- Evaluate vLLM contribution to complex entity extraction
- Assess context understanding improvements
- Measure performance impact

### Configuration
```python
config = ExtractionConfig(
    mode=ExtractionMode.FULL_AI,
    enable_regex=True,
    enable_fast_ai=True,
    enable_vllm=True,      # NEW
    enable_context=True,
    enable_relationships=False,
    enable_unpatterned=False,
    max_document_size_for_vllm=10000  # Increase for Rahimi.pdf
)
```

### Metrics to Collect
- vLLM-specific entities
- Context window accuracy
- Complex entity resolution rate
- Processing time with vLLM
- Token usage statistics
- Memory footprint

### Quality Assessment Criteria
- **Complex Entities**: Successful extraction of multi-word entities
- **Context Accuracy**: > 85% context relevance
- **Performance**: < 30 seconds processing time
- **Memory**: < 4GB GPU memory usage

### Visualization Requirements
- vLLM contribution analysis
- Context quality heatmap
- Complex entity examples table
- Processing pipeline timeline

## Phase 4: Coreference Resolution (enable_coreference)

### Objectives
- Resolve entity mentions to canonical forms
- Link pronouns and references
- Reduce entity duplication

### Configuration
```python
config = ExtractionConfig(
    mode=ExtractionMode.FULL_AI,
    enable_regex=True,
    enable_fast_ai=True,
    enable_vllm=True,
    enable_context=True,
    enable_coreference=True,  # NEW (if available)
    enable_relationships=False,
    enable_unpatterned=False
)
```

### Metrics to Collect
- Coreference chains identified
- Entity consolidation rate
- Pronoun resolution accuracy
- Duplicate entity reduction

### Quality Assessment Criteria
- **Resolution Rate**: > 70% of pronouns resolved
- **Consolidation**: 20-30% reduction in duplicate entities
- **Accuracy**: > 90% correct resolutions (manual check)

### Visualization Requirements
- Coreference chain visualization
- Entity consolidation before/after
- Resolution examples with context

## Phase 5: Relationship Extraction (enable_relationships)

### Objectives
- Extract legal relationships between entities
- Build entity interaction graph
- Identify key legal connections

### Configuration
```python
config = ExtractionConfig(
    mode=ExtractionMode.FULL_AI,
    enable_regex=True,
    enable_fast_ai=True,
    enable_vllm=True,
    enable_context=True,
    enable_relationships=True,  # NEW
    enable_unpatterned=False
)
```

### Metrics to Collect
- Total relationships extracted
- Relationship type distribution
- Entity connectivity metrics
- Relationship confidence scores

### Quality Assessment Criteria
- **Coverage**: >= 100 relationships expected
- **Type Diversity**: >= 10 relationship types
- **Accuracy**: > 80% valid relationships
- **Confidence**: Average confidence > 0.6

### Visualization Requirements
- Entity relationship graph
- Relationship type distribution
- Top connected entities table
- Sample relationships with context

## Phase 6: Unpatterned Entity Detection (enable_unpatterned)

### Objectives
- Discover entities without predefined patterns
- Capture domain-specific terminology
- Identify emerging entity types

### Configuration
```python
config = ExtractionConfig(
    mode=ExtractionMode.FULL_AI,
    enable_regex=True,
    enable_fast_ai=True,
    enable_vllm=True,
    enable_context=True,
    enable_relationships=True,
    enable_unpatterned=True,  # NEW
    unpatterned_types=['legal_concept', 'jurisdiction', 'remedy']
)
```

### Metrics to Collect
- Unpatterned entities discovered
- New entity type suggestions
- Pattern recommendation confidence
- Processing overhead

### Quality Assessment Criteria
- **Discovery Rate**: >= 50 new entities
- **Relevance**: > 70% legally relevant
- **Type Accuracy**: > 60% correct type assignment
- **Performance Impact**: < 10% processing increase

### Visualization Requirements
- Unpatterned entity showcase
- Suggested pattern analysis
- Entity type evolution chart
- Discovery confidence distribution

## Testing Implementation Framework

### Test Script Structure
```python
class CALESPipelineTestFramework:
    def __init__(self):
        self.test_document = "Rahimi.pdf"
        self.results = {}
        self.metrics = {}
        
    async def run_phase(self, phase_name, config):
        """Execute a single test phase"""
        # 1. Configure pipeline
        # 2. Process document
        # 3. Collect metrics
        # 4. Generate visualizations
        # 5. Save results
        
    async def compare_phases(self):
        """Compare results across phases"""
        # Generate comparative analysis
        
    async def generate_report(self):
        """Create comprehensive HTML report"""
        # Compile all results and visualizations
```

### Output Structure
```
/srv/luris/be/entity-extraction-service/tests/results/cales_pipeline_test_[timestamp]/
├── phase1_regex_only/
│   ├── entities.json
│   ├── metrics.json
│   ├── visualizations/
│   └── quality_assessment.md
├── phase2_fast_ai/
│   └── ...
├── phase3_vllm/
│   └── ...
├── phase4_coreference/
│   └── ...
├── phase5_relationships/
│   └── ...
├── phase6_unpatterned/
│   └── ...
├── comparative_analysis/
│   ├── phase_comparison.json
│   ├── improvement_metrics.json
│   └── visualizations/
└── final_report.html
```

## Quality Monitoring Dashboard

### Real-time Metrics Display
- Entity extraction rate (entities/second)
- Memory usage graph
- GPU utilization
- Error rate tracking
- Confidence score trends

### Interactive Visualizations
- Entity browser with filtering
- Context viewer with highlighting
- Relationship network explorer
- Quality metrics dashboard

### Export Capabilities
- JSON data export
- CSV entity lists
- HTML comprehensive report
- Markdown quality assessment

## Success Criteria

### Overall Pipeline Performance
- **Total Entity Coverage**: >= 3,000 entities
- **Unique Entity Types**: >= 70 types
- **Relationship Extraction**: >= 150 relationships
- **Processing Time**: < 60 seconds total
- **Memory Usage**: < 6GB peak
- **Quality Score**: > 85% accuracy

### Phase Progression Improvements
- Each phase should show measurable improvement
- No regression in previous capabilities
- Incremental processing time acceptable
- Quality metrics maintained or improved

## Risk Mitigation

### Performance Risks
- **GPU Memory**: Monitor and implement batching if needed
- **Processing Time**: Set timeouts and fallback strategies
- **API Rate Limits**: Implement request throttling

### Quality Risks
- **False Positives**: Implement confidence thresholds
- **Entity Duplication**: Apply deduplication logic
- **Context Drift**: Validate context windows

### Technical Risks
- **Service Dependencies**: Health checks before testing
- **Model Loading**: Lazy loading with fallbacks
- **Data Persistence**: Incremental result saving

## Execution Timeline

### Estimated Duration
- **Phase 1**: 15 minutes (baseline + validation)
- **Phase 2**: 20 minutes (AI models initialization)
- **Phase 3**: 25 minutes (vLLM processing)
- **Phase 4**: 15 minutes (coreference resolution)
- **Phase 5**: 20 minutes (relationship extraction)
- **Phase 6**: 20 minutes (unpatterned detection)
- **Analysis & Report**: 30 minutes

**Total Estimated Time**: 2.5 - 3 hours

## Next Steps

1. **Environment Preparation**
   - Verify all services are running
   - Check GPU availability
   - Ensure test document accessibility

2. **Test Execution**
   - Run phases sequentially
   - Monitor metrics in real-time
   - Save intermediate results

3. **Analysis & Reporting**
   - Generate comparative visualizations
   - Compile quality assessments
   - Create final recommendations

4. **Optimization Recommendations**
   - Based on bottlenecks identified
   - Configuration tuning suggestions
   - Architecture improvements

This plan provides a comprehensive framework for systematically evaluating the CALES pipeline with progressive component activation, ensuring thorough quality monitoring and visual inspection capabilities at each stage.