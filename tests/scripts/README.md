# Entity Extraction Service - Utility Scripts

This directory contains utility scripts for debugging, analysis, testing, and development of the entity extraction service. These scripts have been organized from the root directory to maintain a clean codebase structure.

## 📁 Directory Structure

```
scripts/
├── debug/           # Debug utilities (1 script)
├── analysis/        # Analysis and fine-tuning scripts (4 scripts)
├── archived/        # Deprecated test scripts (10 scripts)
├── utilities/       # General utilities (18 scripts)
└── README.md        # This file
```

**Total Scripts**: 33 organized scripts

## 🚀 Usage

All scripts require the virtual environment to be activated and should be run from the service root directory:

```bash
# Navigate to service root
cd /srv/luris/be/entity-extraction-service

# Activate virtual environment (REQUIRED)
source venv/bin/activate

# Run any script
python tests/scripts/[category]/[script_name].py
```

## 🐛 Debug Scripts (`debug/`)

Debugging utilities for troubleshooting entity extraction issues.

### `debug_extraction.py`
- **Purpose**: Debug entity extraction pipeline with detailed logging
- **Use Case**: Troubleshoot extraction issues, inspect intermediate results
- **Usage**: `python tests/scripts/debug/debug_extraction.py`

## 📊 Analysis Scripts (`analysis/`)

Scripts for analyzing patterns, evaluating fine-tuning results, and performance analysis.

### `analyze_patterns_for_fine_tuning.py`
- **Purpose**: Analyze entity extraction patterns to prepare data for model fine-tuning
- **Use Case**: Generate fine-tuning datasets, identify pattern improvements
- **Usage**: `python tests/scripts/analysis/analyze_patterns_for_fine_tuning.py`

### `fixed_fine_tuned_inference.py`
- **Purpose**: Run inference with a fixed fine-tuned model
- **Use Case**: Test fine-tuned model performance, compare with base model
- **Usage**: `python tests/scripts/analysis/fixed_fine_tuned_inference.py`

### `improved_fine_tuned_inference.py`
- **Purpose**: Run inference with improved fine-tuned model
- **Use Case**: Evaluate enhanced fine-tuning approaches
- **Usage**: `python tests/scripts/analysis/improved_fine_tuned_inference.py`

### `run_saullm_fine_tuning.py`
- **Purpose**: Execute SaulLM model fine-tuning for legal entity extraction
- **Use Case**: Fine-tune legal-specific language models
- **Usage**: `python tests/scripts/analysis/run_saullm_fine_tuning.py`

## 🗄️ Archived Scripts (`archived/`)

**⚠️ DEPRECATED**: These scripts are archived and should NOT be used for new development. They are kept for historical reference and backward compatibility.

### Recommended Alternatives
- **For testing**: Use `tests/unit/` and `tests/integration/` directories
- **For benchmarking**: Use `tests/test_framework/` with standardized test cases

### Archived Test Scripts

#### `test_gpu1_direct_vllm.py`
- **Status**: DEPRECATED
- **Alternative**: Use standard vLLM integration in `src/clients/vllm_client.py`
- **Original Purpose**: Direct vLLM testing on GPU 1

#### `test_guided_json_simple.py`
- **Status**: DEPRECATED
- **Alternative**: Use `tests/integration/test_guided_json.py`
- **Original Purpose**: Simple guided JSON schema testing

#### `test_rahimi_final.py`
- **Status**: DEPRECATED
- **Alternative**: Use `tests/test_framework/test_rahimi_extraction.py`
- **Original Purpose**: Final Rahimi document extraction test

#### `test_rahimi_gpu1_isolated.py`
- **Status**: DEPRECATED
- **Alternative**: Use standard test framework with GPU selection
- **Original Purpose**: Isolated Rahimi test on GPU 1

#### `test_rahimi_gpu1.py`
- **Status**: DEPRECATED
- **Alternative**: Use `tests/test_framework/test_rahimi_extraction.py`
- **Original Purpose**: Rahimi extraction test on GPU 1

#### `test_rahimi_http.py`
- **Status**: DEPRECATED
- **Alternative**: Use `tests/integration/test_http_extraction.py`
- **Original Purpose**: HTTP-based Rahimi extraction test

#### `test_rahimi_simple.py`
- **Status**: DEPRECATED
- **Alternative**: Use `tests/test_framework/test_rahimi_extraction.py`
- **Original Purpose**: Simple Rahimi extraction test

#### `test_temperature_comparison.py`
- **Status**: DEPRECATED
- **Alternative**: Use parameterized tests in `tests/unit/test_extraction_parameters.py`
- **Original Purpose**: Compare extraction quality at different temperatures

#### `test_temp_no_guided_json.py`
- **Status**: DEPRECATED
- **Alternative**: Use configuration-based testing in test framework
- **Original Purpose**: Test extraction without guided JSON

#### `test_temp_with_orchestrator.py`
- **Status**: DEPRECATED
- **Alternative**: Use `tests/integration/test_orchestrator.py`
- **Original Purpose**: Test orchestrator with temperature variations

## 🛠️ Utilities (`utilities/`)

General-purpose utilities for document processing, visualization, and service operations.

### Document Processing

#### `convert_pdf_to_markdown.py`
- **Purpose**: Convert PDF documents to Markdown format using MarkItDown
- **Use Case**: Prepare documents for text extraction
- **Usage**: `python tests/scripts/utilities/convert_pdf_to_markdown.py [input.pdf]`

#### `extract_rahimi_text.py`
- **Purpose**: Extract text from the Rahimi.pdf test document
- **Use Case**: Generate test data for extraction benchmarks
- **Usage**: `python tests/scripts/utilities/extract_rahimi_text.py`

### Testing Utilities

#### `comprehensive_test.py`
- **Purpose**: Comprehensive test suite for entity extraction
- **Use Case**: Full pipeline testing with detailed metrics
- **Usage**: `python tests/scripts/utilities/comprehensive_test.py`

#### `focused_base_test.py`
- **Purpose**: Focused test on specific extraction scenarios
- **Use Case**: Targeted testing of specific entity types
- **Usage**: `python tests/scripts/utilities/focused_base_test.py`

#### `full_document_base_test.py`
- **Purpose**: Full document extraction baseline test
- **Use Case**: Benchmark extraction on complete documents
- **Usage**: `python tests/scripts/utilities/full_document_base_test.py`

#### `quick_base_test.py`
- **Purpose**: Quick baseline test for rapid validation
- **Use Case**: Fast smoke testing during development
- **Usage**: `python tests/scripts/utilities/quick_base_test.py`

#### `ultra_quick_base_test.py`
- **Purpose**: Ultra-fast baseline test (minimal extraction)
- **Use Case**: Immediate validation of basic functionality
- **Usage**: `python tests/scripts/utilities/ultra_quick_base_test.py`

### Visualization & Analysis

#### `generate_cales_html_dashboard.py`
- **Purpose**: Generate HTML dashboard for CALES (Citation And Legal Entity System)
- **Use Case**: Visualize extraction results and metrics
- **Usage**: `python tests/scripts/utilities/generate_cales_html_dashboard.py`

#### `show_entities.py`
- **Purpose**: Display extracted entities in readable format
- **Use Case**: Quick inspection of extraction results
- **Usage**: `python tests/scripts/utilities/show_entities.py [results_file]`

#### `show_raw_llm_response.py`
- **Purpose**: Display raw LLM responses for debugging
- **Use Case**: Debug LLM output parsing issues
- **Usage**: `python tests/scripts/utilities/show_raw_llm_response.py`

### Fine-Tuning Utilities

#### `compare_fine_tuning_results.py`
- **Purpose**: Compare results between base and fine-tuned models
- **Use Case**: Evaluate fine-tuning effectiveness
- **Usage**: `python tests/scripts/utilities/compare_fine_tuning_results.py`

#### `generate_fine_tuning_prompt_with_examples.py`
- **Purpose**: Generate fine-tuning prompts with example entities
- **Use Case**: Prepare training data for model fine-tuning
- **Usage**: `python tests/scripts/utilities/generate_fine_tuning_prompt_with_examples.py`

### Service Utilities

#### `example_usage.py`
- **Purpose**: Example usage of entity extraction service API
- **Use Case**: Quick reference for API integration
- **Usage**: `python tests/scripts/utilities/example_usage.py`

#### `run_simple.py`
- **Purpose**: Simple service runner for testing
- **Use Case**: Quick service startup without systemd
- **Usage**: `python tests/scripts/utilities/run_simple.py`

#### `serve_legalbert.py`
- **Purpose**: Serve LegalBERT model for entity extraction
- **Use Case**: Alternative model serving (deprecated in favor of vLLM)
- **Usage**: `python tests/scripts/utilities/serve_legalbert.py`

### Validation Utilities

#### `fix_imports.py`
- **Purpose**: Fix import statements across codebase
- **Use Case**: Migrate from relative to absolute imports
- **Usage**: `python tests/scripts/utilities/fix_imports.py`

#### `verify_schema_fix.py`
- **Purpose**: Verify LurisEntityV2 schema compliance
- **Use Case**: Validate schema migrations and compliance
- **Usage**: `python tests/scripts/utilities/verify_schema_fix.py`

#### `verify_vllm_installation.py`
- **Purpose**: Verify vLLM installation and GPU availability
- **Use Case**: Troubleshoot vLLM setup issues
- **Usage**: `python tests/scripts/utilities/verify_vllm_installation.py`

## 📝 Migration Guide

### For Scripts That Referenced Old Locations

**Before** (root directory):
```bash
cd /srv/luris/be/entity-extraction-service
python debug_extraction.py
```

**After** (organized structure):
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python tests/scripts/debug/debug_extraction.py
```

### For Code That Imports These Scripts

**Before**:
```python
# Import from root
from debug_extraction import debug_function
```

**After**:
```python
# Import from organized structure
from tests.scripts.debug.debug_extraction import debug_function
```

## ⚠️ Import Standards (MANDATORY)

All scripts follow **absolute import standards** as defined in CLAUDE.md:

### ✅ CORRECT - Absolute Imports
```python
from src.core.extraction_service import ExtractionService
from src.models.entities import EntityType, LurisEntityV2
from shared.clients.supabase_client import create_supabase_client
```

### ❌ FORBIDDEN - Relative Imports
```python
# FORBIDDEN: sys.path manipulation
import sys
sys.path.append('../..')

# FORBIDDEN: Relative imports
from ...src.core.extraction_service import ExtractionService
```

### Pre-Execution Checklist

Before running ANY script in this directory:

1. ✅ **Navigate to service root**: `cd /srv/luris/be/entity-extraction-service`
2. ✅ **Activate virtual environment**: `source venv/bin/activate`
3. ✅ **Verify venv activation**: `which python` should show `.../venv/bin/python`
4. ✅ **Run script**: `python tests/scripts/[category]/[script_name].py`

## 🔧 Maintenance

### Adding New Scripts

**Debug Scripts**: Add to `debug/` directory
```bash
# Create new debug script
touch tests/scripts/debug/debug_new_feature.py

# Follow absolute import standards
# Add usage documentation header
```

**Analysis Scripts**: Add to `analysis/` directory
```bash
# Create new analysis script
touch tests/scripts/analysis/analyze_performance.py
```

**Utilities**: Add to `utilities/` directory
```bash
# Create new utility script
touch tests/scripts/utilities/utility_name.py
```

### Deprecating Scripts

When a script becomes obsolete:

1. Move to `archived/` directory
2. Add deprecation notice at top of file
3. Update this README with alternative recommendations
4. Document in git commit message

### Script Template

All new scripts should follow this template:

```python
#!/usr/bin/env python3
"""
script_name.py - Brief description

Purpose:
    Detailed purpose of the script

Usage:
    cd /srv/luris/be/entity-extraction-service
    source venv/bin/activate
    python tests/scripts/[category]/script_name.py [args]

Examples:
    python tests/scripts/debug/script_name.py --verbose
"""

# Absolute imports only
from src.core.extraction_service import ExtractionService
from src.models.entities import EntityType


def main():
    """Main script logic."""
    pass


if __name__ == '__main__':
    main()
```

## 📊 Script Statistics

- **Total Scripts**: 33
- **Debug Scripts**: 1
- **Analysis Scripts**: 4
- **Archived Scripts**: 10
- **Utility Scripts**: 18

### Size Analysis
- **Average Script Size**: ~3-5 KB
- **Total Scripts Size**: ~150 KB
- **Root Directory Cleanup**: 33 files removed from root

## 🔗 Related Documentation

- **Service API**: `/srv/luris/be/entity-extraction-service/api.md`
- **LurisEntityV2 Specification**: `/srv/luris/be/entity-extraction-service/docs/LurisEntityV2_Specification.md`
- **CLAUDE.md**: `/srv/luris/be/CLAUDE.md` (Import standards and architecture)
- **Test Framework**: `/srv/luris/be/entity-extraction-service/tests/test_framework/README.md`

## 🐛 Troubleshooting

### Script Won't Run - ModuleNotFoundError

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
1. Ensure you're in the service root: `cd /srv/luris/be/entity-extraction-service`
2. Activate venv: `source venv/bin/activate`
3. Verify venv: `which python` should show `.../venv/bin/python`

### Script Has sys.path Manipulation

**Problem**: Script still contains `sys.path.insert()` or `sys.path.append()`

**Solution**:
1. Remove sys.path lines from script
2. Use absolute imports: `from src.module import Class`
3. Run from service root with venv activated

### Archived Script Needed

**Problem**: Need to use an archived test script

**Solution**:
1. Check `archived/` directory for the script
2. Review README for recommended alternative
3. If no alternative exists, consider updating the script to current standards
4. Move to appropriate category if script is still useful

## 📞 Support

For questions about these scripts or to report issues:

1. Check this README for usage instructions
2. Review service API documentation
3. Consult CLAUDE.md for architectural guidelines
4. Check git history for script evolution

---

**Last Updated**: October 2025
**Maintained By**: Luris Development Team
**Organization Date**: October 2025
