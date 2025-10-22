# Entity Extraction Service Testing Standards

## Overview
This document defines the testing standards for the Entity Extraction Service. All tests MUST follow these standards to ensure consistency and comprehensive coverage.

## Standard Test Document
- **Primary**: `/srv/luris/be/tests/docs/Rahimi.pdf`
- **Secondary**: `/srv/luris/be/entity-extraction-service/tests/docs/range_v_garland_3rd_circuit.pdf`

## Required Test Result Structure

All entity extraction tests MUST generate results in the exact JSON structure defined in:
`/srv/luris/be/AGENT_DEFINITIONS.md` - "Standardized Testing Requirements" section

## Test Execution Procedure

### 1. Environment Setup
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
```

### 2. Service Health Check
```bash
curl -s http://localhost:8007/api/v1/health | jq
```

### 3. Run Standard Test
```bash
python tests/result_generator.py --mode regex --save --example
```

### 4. Run Full Pipeline Test
```bash
python tests/standard_test_runner.py
```

## Test Modes

### Regex Mode
- Pattern-based extraction using YAML pattern files
- Located in: `src/patterns/`
- 295 patterns across 53 YAML files
- Fastest execution, deterministic results

### SpaCy Mode
- NLP-based entity recognition
- Uses pre-trained legal NER models
- Better context understanding
- Moderate speed

### AI Enhanced Mode
- Uses vLLM service (port 8080)
- Requires prompt service running
- Best accuracy for complex entities
- Slowest but most accurate

## Performance Benchmarks

Expected performance targets:
- **Regex Mode**: < 500ms per document
- **SpaCy Mode**: < 2000ms per document
- **AI Enhanced**: < 5000ms per document
- **Memory Usage**: < 512MB
- **Entities/Second**: > 10

## Quality Metrics

### Required Metrics
- **Precision**: > 95%
- **Recall**: > 90%
- **F1 Score**: > 92.5%

### Entity Type Coverage
All 31 legal entity types must be tested:

**Citations (9 types)**
- CASE_CITATION
- STATUTE_CITATION
- REGULATION_CITATION
- CONSTITUTIONAL_CITATION
- LAW_REVIEW_CITATION
- BOOK_CITATION
- NEWSPAPER_CITATION
- WEB_CITATION
- PARALLEL_CITATION

**Legal Entities (7 types)**
- COURT
- JUDGE
- ATTORNEY
- PARTY
- LAW_FIRM
- GOVERNMENT_ENTITY
- JURISDICTION

**Legal Concepts (9 types)**
- LEGAL_DOCTRINE
- PROCEDURAL_TERM
- CLAIM_TYPE
- MOTION_TYPE
- LEGAL_STANDARD
- REMEDY
- LEGAL_ISSUE
- HOLDING
- RULING

**Document Elements (6 types)**
- MONETARY_AMOUNT
- DATE
- DOCKET_NUMBER
- EXHIBIT
- DEPOSITION
- INTERROGATORY

## Result Storage

### Naming Convention
- JSON: `extraction_[YYYYMMDD_HHMMSS].json`
- Markdown: `extraction_[YYYYMMDD_HHMMSS].md`
- Logs: `test_log_[YYYYMMDD_HHMMSS].txt`

### Storage Location
All results MUST be saved to: `/srv/luris/be/entity-extraction-service/tests/results/`

## Validation Checklist

Before marking a test as complete, verify:
- [ ] All service health checks pass
- [ ] Result structure matches standard
- [ ] Performance metrics collected
- [ ] Quality metrics calculated
- [ ] Markdown report generated
- [ ] Results saved with timestamp
- [ ] All 31 entity types covered
- [ ] Bluebook format validated for citations

## Common Issues and Solutions

### Issue: Service Not Running
```bash
sudo systemctl start luris-entity-extraction
sudo systemctl status luris-entity-extraction
```

### Issue: vLLM Not Available for AI Mode
```bash
sudo systemctl start luris-vllm
curl http://localhost:8080/health
```

### Issue: Missing Pattern Files
```bash
ls -la src/patterns/*.yaml | wc -l  # Should show 53 files
```

### Issue: Memory Errors
- Reduce batch size in configuration
- Process documents sequentially
- Monitor with: `htop` or `ps aux | grep python`

## Integration with Other Services

### Dependencies
- **Log Service** (8001): Required for logging
- **Prompt Service** (8003): Required for AI-enhanced mode
- **vLLM Service** (8080): Required for AI-enhanced mode

### Downstream Services
- **GraphRAG Service** (8010): Consumes entity extraction results
- **Document Processing** (8000): Orchestrates full pipeline

## Test Automation

### Continuous Testing
```bash
# Run all test modes
for mode in regex spacy ai_enhanced; do
    python tests/result_generator.py --mode $mode --save
    echo "Completed $mode test"
done
```

### Batch Testing
```bash
# Test multiple documents
for doc in tests/docs/*.pdf; do
    python tests/standard_test_runner.py --document "$doc"
done
```

## Reporting Requirements

Every test report MUST include:
1. Executive summary
2. Service health status
3. Performance metrics table
4. Entity type distribution
5. Top 5 entity examples
6. Top 5 citation examples
7. Quality metrics (precision, recall, F1)
8. Recommendations for improvements

## Contact

For questions about testing standards:
- Review: `/srv/luris/be/AGENT_DEFINITIONS.md`
- Check: `/srv/luris/be/CLAUDE.md`
- Service API: `entity-extraction-service/api.md`