# vLLM Optimization Test Orchestrator

## Overview

The `vllm_optimization_test.py` script is a comprehensive test orchestrator that manages the complete lifecycle of vLLM service testing across multiple configurations. It automatically:

1. Iterates through all 24 vLLM configurations (12 single-GPU, 12 dual-GPU)
2. Manages vLLM service lifecycle (stop/start/health check)
3. Tests entity extraction on multiple documents with different strategies
4. Collects GPU, system, and performance metrics
5. Handles failures gracefully and continues testing
6. Generates comprehensive reports with all extracted entities

## Prerequisites

### Required Services

Before running the test orchestrator, ensure these services are running:

```bash
# Check service status
sudo systemctl status luris-document-upload
sudo systemctl status luris-entity-extraction

# Start services if not running
sudo systemctl start luris-document-upload
sudo systemctl start luris-entity-extraction
```

### Python Environment

```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Test All Configurations

```bash
# Test all 24 configurations
python tests/vllm_optimization_test.py
```

### Test Specific Configurations

```bash
# Test specific configurations only
python tests/vllm_optimization_test.py --configs dual_gpu_config_021 dual_gpu_config_022 single_gpu_config_001
```

### Custom Output Directory

```bash
# Specify custom output directory
python tests/vllm_optimization_test.py --output-dir /path/to/results
```

## Test Process

For each configuration, the orchestrator:

1. **Stops** the current vLLM service
2. **Starts** vLLM with the new configuration using the `.sh` script
3. **Waits** for model loading (health check with 120s timeout)
4. **Tests** entity extraction on:
   - `/srv/luris/be/tests/docs/Rahimi.pdf` (459KB)
   - `/srv/luris/be/tests/docs/dobbs.pdf` (1.2MB)
5. **Extracts** entities using strategies:
   - `AI_ENHANCED` - Enhanced AI extraction with context
   - `UNIFIED` - Single-pass comprehensive extraction
6. **Collects** metrics:
   - GPU utilization and memory
   - Extraction time
   - Entity counts and types
   - Confidence scores
7. **Saves** results before moving to next configuration

## Output Structure

```
results/
├── vllm_optimization_test_report_YYYYMMDD_HHMMSS.json  # Final comprehensive report
├── intermediate/                                        # Per-test results
│   ├── config_XXX_document_strategy_timestamp.json
│   └── ...
└── metrics/                                            # Performance metrics
    ├── metrics_single_gpu_config_001.json
    ├── metrics_dual_gpu_config_021.json
    └── ...
```

## Result Format

Each test result contains:

```json
{
  "test_id": "test_dual_gpu_config_021_Rahimi_pdf_ai_enhanced",
  "config_id": "dual_gpu_config_021",
  "document": "Rahimi.pdf",
  "strategy": "AI_ENHANCED",
  "extraction_time_ms": 2500.5,
  "entity_count": 47,
  "citation_count": 12,
  "entities": [
    {
      "type": "CASE",
      "value": "United States v. Rahimi",
      "confidence": 0.95,
      "position": {"start": 100, "end": 125},
      "extraction_method": "ai_enhanced",
      "attributes": {...}
    },
    ...
  ],
  "citations": [
    {
      "type": "CASE_CITATION",
      "value": "347 U.S. 483 (1954)",
      "confidence": 0.98,
      "position": {...},
      "components": {...},
      "bluebook_compliant": true
    },
    ...
  ],
  "metrics": {
    "gpu_statistics": {...},
    "vllm_statistics": {...},
    "system_statistics": {...}
  },
  "success": true,
  "error": null
}
```

## Final Report Structure

The comprehensive report includes:

- **Test Metadata**: Total tests, success/failure counts, configurations tested
- **Configuration Results**: Per-configuration performance and entity statistics
- **Entity Statistics**: Distribution of entity types with samples and confidence scores
- **Performance Metrics**: Average, min, max extraction times
- **Detailed Results**: Complete data for every test run

## Timeout Configuration

All extraction requests have a **45-minute timeout** (2700 seconds) to accommodate:
- Large documents
- Complex extraction strategies
- Multiple retry attempts
- Model loading delays

## Error Handling

- **Service Startup Failures**: Logged and skipped, continues to next configuration
- **Extraction Failures**: Automatically retried once before marking as failed
- **Graceful Shutdown**: Handles SIGINT/SIGTERM for clean termination

## Monitoring Progress

The script provides detailed logging:
- Console output with progress indicators
- Log file: `vllm_optimization_test_YYYYMMDD_HHMMSS.log`
- Real-time entity counts and extraction times
- Success/failure indicators for each test

## Best Practices

1. **Run During Low Usage**: Tests can consume significant GPU resources
2. **Monitor GPU Memory**: Use `nvidia-smi -l 1` in another terminal
3. **Check Service Logs**: Monitor vLLM logs for issues:
   ```bash
   sudo journalctl -u luris-vllm -f
   ```
4. **Incremental Testing**: Use `--configs` to test configurations incrementally
5. **Backup Results**: Results are saved incrementally, safe to interrupt

## Troubleshooting

### Service Won't Start
```bash
# Check if port is in use
sudo lsof -i :8080

# Force stop any hanging processes
sudo pkill -9 -f vllm

# Restart the test
```

### Extraction Timeouts
- Increase timeout in EntityExtractionTester.__init__
- Check vLLM service health during tests
- Monitor GPU memory for OOM issues

### Missing Results
- Check intermediate/ directory for partial results
- Review log file for specific errors
- Verify document upload service is working

## Performance Expectations

- **Per Configuration**: 10-15 minutes (including model loading)
- **Full Test Suite**: 4-6 hours for all 24 configurations
- **Entity Extraction**: 1-5 seconds per document (typical)
- **Model Loading**: 30-60 seconds per configuration switch