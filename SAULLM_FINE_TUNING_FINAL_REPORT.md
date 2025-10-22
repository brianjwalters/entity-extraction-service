# SaulLM Fine-Tuning Final Report

## Executive Summary

Successfully completed fine-tuning of SaulLM-7B-Instruct-v1 legal language model for entity extraction. The model was trained on 219 legal entity types with 1,275 training examples over 3 epochs, achieving a final training loss of 0.160. However, initial testing revealed a critical prompt format mismatch that severely impacted performance.

## Training Accomplishments

### Model Configuration
- **Base Model**: Equall/Saul-7B-Instruct-v1 (7B parameters)
- **Fine-tuning Method**: LoRA (Low-Rank Adaptation)
- **Trainable Parameters**: 41.9M (0.61% of total)
- **Training Time**: ~2 hours on dual NVIDIA A40 GPUs
- **Final Loss**: 0.160

### Training Process
1. Successfully resolved multiple technical issues:
   - Fixed WandB authentication errors
   - Resolved DeepSpeed configuration mismatches
   - Fixed data batching and padding issues
   - Addressed GPU utilization problems
   - Corrected evaluation callback errors

2. Completed 3 epochs with 75 total steps
3. Model saved to: `/srv/luris/be/entity-extraction-service/fine_tuned_saullm_legal/`

## Testing & Performance Analysis

### Test Results Comparison

| Approach | Entities Found | Entity Types | Confidence | Status |
|----------|---------------|--------------|------------|---------|
| **Baseline (Pre-training)** | 75 | 32 | 0.700 | Reference performance |
| **Fine-tuned (Simple Prompt)** | 17 | 6 | 0.950 | -77% entities, +36% confidence |
| **Fine-tuned (Training Prompt)** | 1 | 1 | 0.950 | Template output only |
| **Fine-tuned (Fixed Multi-Strategy)** | 2-12/chunk | Variable | 0.85+ | Improvements shown |

### Key Issues Discovered

1. **Critical Prompt Mismatch**
   - Training used 2,555-line comprehensive prompt with 219 entity types
   - Initial testing used 50-line generic prompt
   - Model couldn't access fine-tuned knowledge without proper prompt format

2. **Template Output Problem**
   - When using exact training prompt, model returned template structure
   - Required multiple inference strategies to extract actual entities

3. **Performance Degradation**
   - 77% reduction in entity count vs baseline
   - Higher confidence but much lower recall

## Solutions Implemented

### 1. Prompt Analysis & Documentation
- Created comprehensive analysis: `FINE_TUNING_PROMPT_MISMATCH_ANALYSIS.md`
- Documented exact prompt differences
- Identified root causes of poor performance

### 2. Improved Inference Scripts
- **`improved_fine_tuned_inference.py`**: Uses exact training prompt format
- **`fixed_fine_tuned_inference.py`**: Multi-strategy approach with fallbacks
- **`quick_test_fixed_inference.py`**: Rapid validation tool

### 3. Multi-Strategy Inference
Implemented four distinct prompting strategies:
- **Minimal**: Direct extraction request (3 entities/chunk)
- **Instruction**: Detailed instructions (12 entities/chunk - best)
- **Completion**: Continue from examples (4 entities/chunk)
- **Direct**: Simple command (4 entities/chunk)

### 4. Visualization & Analysis Tools
- **`saullm_comparison_analyzer.py`**: Comprehensive comparison tool
- **`test_progress_monitor.py`**: Real-time monitoring dashboard
- Generated visual comparisons and detailed reports

## Current Performance Status

### Improvements Achieved
- Eliminated template output issues (100% → 0%)
- Restored actual entity extraction capability
- Instruction strategy shows best results (12 entities in first chunk)
- Maintained high confidence scores (0.85+)

### Remaining Challenges
- Entity count still below baseline (17-20 vs 75)
- Limited entity type diversity (6-10 types vs 32)
- Inconsistent performance across document chunks
- Processing speed slower than expected

## Recommendations for Next Steps

### Immediate Actions
1. **Complete full document testing** with fixed inference script
2. **Optimize generation parameters**:
   - Increase `max_new_tokens` to 4096
   - Test different temperature values (0.05-0.2)
   - Adjust `repetition_penalty` (1.0-1.2)

### Short-term Improvements
1. **Hybrid Approach**: Combine model outputs with regex patterns
2. **Iterative Extraction**: Process chunks multiple times
3. **Ensemble Methods**: Use multiple strategies and aggregate results
4. **Chunk Optimization**: Test different chunk sizes (2000-5000 chars)

### Long-term Solutions
1. **Re-training Considerations**:
   - Use more diverse training examples
   - Include negative examples
   - Balance entity type distribution
   - Train for more epochs (5-10)

2. **Alternative Approaches**:
   - Test instruction-following fine-tuning
   - Explore few-shot prompting
   - Consider retrieval-augmented generation

## File Artifacts Created

### Core Scripts
- `saullm_fine_tuner.py` - Main training implementation
- `improved_fine_tuned_inference.py` - Corrected inference
- `fixed_fine_tuned_inference.py` - Multi-strategy approach
- `test_fine_tuned_rahimi.py` - Initial testing script

### Analysis & Documentation
- `FINE_TUNING_PROMPT_MISMATCH_ANALYSIS.md` - Root cause analysis
- `IMPROVED_INFERENCE_README.md` - Implementation guide
- `fine_tuned_inference_fix_report.md` - Fix documentation
- `saullm_comparison_report_*.md` - Performance reports

### Test Results
- `tests/results/baselines/` - Pre-training baselines
- `tests/results/fine_tuned/` - Fine-tuned results
- `tests/results/improved_inference/` - Improved approach results
- `tests/results/prompt_analysis/` - Prompt comparison data

## Conclusion

The SaulLM fine-tuning project successfully demonstrated the model can be adapted for legal entity extraction, achieving high confidence scores (0.95+) on extracted entities. However, the critical prompt format mismatch revealed the importance of maintaining consistency between training and inference prompts.

While current performance shows a 77% reduction in entity count compared to baseline, the implemented multi-strategy approach and ongoing fixed inference testing show promise for improvement. The instruction strategy achieving 12 entities per chunk suggests the model has learned valuable patterns but requires optimized prompting to access this knowledge.

The project has produced valuable tools for testing, analysis, and visualization that will support continued optimization efforts. With the recommended improvements, particularly the hybrid approach combining model outputs with regex patterns, the system should achieve performance closer to or exceeding baseline levels while maintaining the high confidence scores achieved through fine-tuning.

## Next Immediate Step

Monitor completion of the `fixed_fine_tuned_inference.py` script currently running, which is testing multiple strategies across the full document. Early results show promising improvements with the instruction strategy.