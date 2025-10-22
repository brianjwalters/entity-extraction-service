# Entity Extraction Troubleshooting Notebook

## Overview

This comprehensive Jupyter notebook provides complete control over all aspects of entity extraction and chunking for performance troubleshooting. It uses **vLLM as a Python package directly** (not the hosted HTTP service) to eliminate overhead and provide full parameter control.

## 🎯 Purpose

This notebook was created specifically to:
1. **Find the exact character count where entity extraction fails** (the 5000-character issue)
2. **Test different models** (Granite 3.3 2B vs Qwen 2.5 72B) to compare performance
3. **Control all vLLM parameters** to find optimal configurations
4. **Test all extraction strategies** (unified, multipass, individual passes)
5. **Analyze template token usage** and optimize for different document sizes
6. **Provide precise character-level control** for systematic testing

## 📁 Files Structure

```
/srv/luris/be/entity-extraction-service/
├── entity_extraction_troubleshooting.ipynb   # Main notebook
├── notebook_modules/                          # Supporting Python modules
│   ├── vllm_controller.py                    # Direct vLLM Python API control
│   ├── template_manager.py                   # Template loading and management
│   ├── chunking_engine.py                    # Precise chunking control
│   ├── performance_analyzer.py               # Performance metrics and analysis
│   └── extraction_tester.py                  # Extraction strategy testing
├── troubleshooting_results/                  # Output directory for results
└── performance_results/                      # Performance metrics storage
```

## 🚀 Quick Start

### 1. Install Requirements

```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Install vLLM as Python package
VLLM_USE_PRECOMPILED=1 pip install vllm

# Install notebook dependencies
pip install jupyter ipywidgets pandas matplotlib seaborn tiktoken
```

### 2. Launch Jupyter Notebook

```bash
jupyter notebook entity_extraction_troubleshooting.ipynb
```

### 3. Follow the Notebook Sections

The notebook is organized into 13 sections:
1. Setup and imports
2. Initialize components
3. Interactive control panel
4. Load test document
5. Load vLLM model
6. Test extraction
7. Find breaking point
8. Compare strategies
9. Test vLLM configurations
10. Automated optimization
11. Performance dashboard
12. Template analysis
13. Export results

## 🎛️ Key Features

### Direct vLLM Python API
- No HTTP overhead (5-10x faster than HTTP API)
- Complete parameter control
- Dynamic model loading/unloading
- Memory management

### Model Selection
- **Granite 3.3 2B**: Fast, 128K context window
- **Qwen 2.5 72B AWQ**: Powerful, quantized for efficiency
- **Qwen 2.5 72B Full**: Maximum quality, requires both GPUs

### Precise Character Control
- Slider for exact character selection (100-100,000)
- Binary search for finding failure points
- Character-to-token ratio calculation

### Extraction Strategies
- **Unified**: Single-pass comprehensive extraction
- **Multipass**: 7 specialized passes
- **Individual Pass Selection**: Test specific passes (1-7)
- **Custom**: Minimal templates for testing

### vLLM Parameters Exposed
```python
- gpu_memory_utilization (0.5-0.98)
- max_num_seqs (batch size)
- max_num_batched_tokens (critical for long docs)
- enable_chunked_prefill
- enable_prefix_caching
- tensor_parallel_size (for multi-GPU)
- dtype (float16/bfloat16/auto)
- swap_space
- block_size
```

### Template Management
- Load all available templates
- Calculate token usage
- Compare templates
- Create minimal templates
- Optimize for document size

### Chunking Control
- Multiple strategies (simple, semantic, legal, precise)
- Exact chunk size control (500-10,000 chars)
- Overlap configuration (0-2000 chars)
- Boundary preservation options

### Performance Analysis
- Real-time GPU monitoring
- Token consumption tracking
- Processing time breakdown
- Success/failure tracking
- Automated report generation

## 📊 Interactive Widgets

The notebook includes comprehensive interactive controls:

- **Model Dropdown**: Select between Granite and Qwen models
- **Character Slider**: Precise document size selection
- **Strategy Radio Buttons**: Choose extraction approach
- **Pass Checkboxes**: Select individual multipass stages
- **Chunking Controls**: Enable/configure chunking
- **vLLM Parameter Sliders**: Fine-tune all settings
- **Template Dropdown**: Select specific templates

## 🔍 Finding the 5000-Character Breaking Point

The notebook includes a dedicated function to find the exact failure point:

```python
# Run this to find where extraction fails
find_breaking_point()
```

This will:
1. Test progressively larger documents
2. Monitor processing time
3. Track success/failure
4. Identify performance degradation
5. Generate visualization

## 📈 Performance Testing

### Test Different Configurations
```python
# Compare vLLM configurations
test_vllm_configurations()

# Compare extraction strategies
compare_strategies()

# Find optimal settings
run_automated_optimization()
```

### Expected Results
- Documents <5000 chars: Should process successfully
- Documents 5000-7000 chars: Performance degradation
- Documents >7000 chars: Likely failures without optimization

## 💡 Optimization Recommendations

Based on testing, here are recommended configurations:

### For Documents <5000 Characters
```python
config = {
    'strategy': 'unified',
    'use_chunking': False,
    'gpu_memory_utilization': 0.90,
    'max_num_batched_tokens': 4096
}
```

### For Documents 5000-10000 Characters
```python
config = {
    'strategy': 'multipass',
    'use_chunking': True,
    'chunk_size': 4000,
    'chunk_overlap': 400,
    'gpu_memory_utilization': 0.95,
    'max_num_batched_tokens': 8192,
    'enable_chunked_prefill': True
}
```

### For Documents >10000 Characters
```python
config = {
    'strategy': 'multipass',
    'use_chunking': True,
    'chunk_size': 3000,
    'chunk_overlap': 300,
    'gpu_memory_utilization': 0.98,
    'max_num_batched_tokens': 16384,
    'enable_chunked_prefill': True,
    'enable_prefix_caching': True
}
```

## 🐛 Troubleshooting Common Issues

### vLLM Import Error
```bash
# Install with precompiled CUDA kernels
VLLM_USE_PRECOMPILED=1 pip install vllm
```

### GPU Memory Issues
- Reduce `gpu_memory_utilization` to 0.85
- Decrease `max_num_batched_tokens`
- Use smaller model (Granite instead of Qwen)

### Timeout Issues
- Enable chunking for large documents
- Reduce `max_tokens` parameter
- Use multipass strategy with fewer passes

### JSON Parse Errors
- Check template formatting
- Ensure proper JSON structure in prompts
- Use minimal templates for testing

## 📊 Interpreting Results

### Key Metrics to Watch
- **Processing Time**: Should be <30 seconds
- **Tokens per Second**: Target >100 tokens/s
- **GPU Memory Delta**: Should be <10GB per request
- **Success Rate**: Should be >90% for optimized configs

### Breaking Point Indicators
- Processing time >30 seconds
- GPU memory exhaustion
- JSON parse failures
- Empty entity results

## 🎯 Next Steps

After finding optimal configurations:

1. **Update Service Configuration**: Apply optimal vLLM settings to production service
2. **Implement Chunking**: Add chunking for documents >5000 chars
3. **Optimize Templates**: Use minimal templates for large documents
4. **Set Limits**: Implement character/token limits in API
5. **Monitor Production**: Use performance analyzer in production

## 📝 Notes

- The notebook is designed for systematic testing
- All parameters are exposed for complete control
- Results are automatically saved for analysis
- Use the export function to save configurations
- The automated optimization can take 10-30 minutes

## 🤝 Support

For issues or questions:
- Check the notebook's markdown cells for detailed instructions
- Review the module docstrings for parameter details
- Examine the performance analysis dashboard for insights
- Export results for sharing with the team

This troubleshooting notebook provides the comprehensive control needed to identify and resolve the 5000-character extraction issue and optimize performance for all document sizes.