# Dobbs.pdf Comprehensive Testing Framework

A comprehensive testing framework for evaluating entity extraction performance on the Dobbs v. Jackson Supreme Court decision document.

## Overview

This framework provides tools to:
- Test all extraction modes (regex, ai_enhanced, hybrid)
- Test all strategies (unified, multipass, ai_enhanced)
- Track coverage of all 272 entity types
- Measure performance metrics and timeouts
- Generate visual quality reports and analysis
- Identify gaps in entity type extraction

## Components

### 1. `dobbs_comprehensive_test.py`
Main test runner that executes comprehensive extraction tests.

**Features:**
- Tests all extraction modes and strategies
- Tracks entity type coverage (272 types)
- Handles timeouts gracefully (300s timeout)
- Measures performance metrics
- Saves detailed results in JSON format

**Output:**
- Comprehensive test results with all metrics
- Entity type coverage matrix
- Performance statistics
- Sample entities for verification

### 2. `visual_quality_inspector.py`
Visual comparison and quality analysis tool.

**Features:**
- Side-by-side strategy comparisons
- Entity type coverage matrices
- Confidence score distributions
- Quality heatmap generation
- Both JSON and Markdown output formats

**Analysis Types:**
- Strategy performance comparison tables
- Entity type distribution charts
- Confidence score analysis
- Coverage gap identification

### 3. `entity_type_analyzer.py`
Deep analysis of entity type performance.

**Features:**
- Tracks which strategies find each entity type
- Calculates precision/recall per entity type
- Identifies missing expected entity types
- Compares performance across strategies
- Generates recommendations for improvement

**Metrics:**
- Entity type coverage scores
- Strategy comparison matrices
- Gap analysis (missing, low coverage, low confidence)
- Performance rankings

### 4. `run_test.sh`
Convenient bash script for running tests and analysis.

**Commands:**
- `test` - Run full test suite with analysis
- `analyze` - Analyze existing results
- `visual` - Run visual quality inspector only
- `types` - Run entity type analyzer only
- `clean` - Clean old results (keep last 5)
- `help` - Show usage information

## Installation

1. Ensure required services are running:
```bash
sudo systemctl start luris-document-upload
sudo systemctl start luris-entity-extraction
```

2. Check service health:
```bash
curl http://localhost:8008/api/v1/health
curl http://localhost:8007/api/v1/health
```

3. Activate the virtual environment:
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
```

## Usage

### Quick Start
Run the complete test suite:
```bash
./run_test.sh test
```

### Running Individual Components

#### Comprehensive Test
```bash
python3 dobbs_comprehensive_test.py
```

#### Visual Quality Analysis
```bash
# Analyze latest results
python3 visual_quality_inspector.py --latest --format both

# Analyze specific results
python3 visual_quality_inspector.py --results-file results/dobbs_test_20240101_120000.json
```

#### Entity Type Analysis
```bash
# Analyze latest results
python3 entity_type_analyzer.py --latest --format both

# Analyze specific results
python3 entity_type_analyzer.py --results-file results/dobbs_test_20240101_120000.json
```

### Using the Run Script

```bash
# Run full test suite
./run_test.sh test

# Analyze latest results
./run_test.sh analyze

# Analyze specific results file
./run_test.sh analyze results/dobbs_test_20240101_120000.json

# Run only visual analysis
./run_test.sh visual

# Run only entity type analysis
./run_test.sh types

# Clean old results
./run_test.sh clean

# Show help
./run_test.sh help
```

## Results Structure

Results are saved in the `results/` directory with timestamps:

```
results/
├── dobbs_test_YYYYMMDD_HHMMSS.json           # Raw test results
├── visual_analysis_YYYYMMDD_HHMMSS.json      # Visual analysis data
├── visual_analysis_YYYYMMDD_HHMMSS.md        # Visual analysis report
├── entity_type_analysis_YYYYMMDD_HHMMSS.json # Entity type analysis data
└── entity_type_analysis_YYYYMMDD_HHMMSS.md   # Entity type analysis report
```

## Test Configuration

### Extraction Modes Tested
- **regex** - Pattern-based extraction
- **ai_enhanced** - LLM-enhanced extraction with strategies:
  - unified
  - multipass
  - ai_enhanced
- **hybrid** - Combined approach with strategies:
  - unified
  - multipass

### Entity Types (272 Total)
The framework tracks all 272 defined entity types including:
- Courts and Judicial (9 types)
- Legal Professionals (14 types)
- Parties (15 types)
- Legal Concepts (18 types)
- Citations (13 types)
- Documents (25 types)
- Financial (15 types)
- Temporal (12 types)
- And many more...

### Expected Entity Types for Dobbs
The framework specifically looks for entity types expected in a Supreme Court opinion:
- COURT, JUDGE, CASE_CITATION, STATUTE_CITATION
- CONSTITUTIONAL_CITATION, OPINION, LEGAL_DOCTRINE
- CONSTITUTIONAL_RIGHT, PRECEDENT, HOLDING, RULING
- DISSENT, CONCURRENCE, APPELLANT, APPELLEE
- And others...

## Performance Considerations

### Timeouts
- Default timeout: 300 seconds per extraction
- Configurable in `dobbs_comprehensive_test.py`

### Content Limits
- AI-enhanced modes limited to 50,000 characters
- Full document used for regex mode

### Memory Usage
- Large document processing may require significant memory
- Monitor system resources during testing

## Troubleshooting

### Service Not Running
```bash
# Check service status
sudo systemctl status luris-document-upload
sudo systemctl status luris-entity-extraction

# Start services
sudo systemctl start luris-document-upload
sudo systemctl start luris-entity-extraction

# Check logs
sudo journalctl -u luris-entity-extraction -f
```

### Timeout Issues
- Increase timeout in `dobbs_comprehensive_test.py`
- Reduce document size for AI modes
- Check vLLM service status if using AI modes

### Missing Dependencies
```bash
# Activate virtual environment
source /srv/luris/be/entity-extraction-service/venv/bin/activate

# Install required packages
pip install pandas numpy aiohttp
```

## Interpreting Results

### Coverage Metrics
- **Entity Type Coverage**: Percentage of 272 types found
- **Strategy Coverage**: How many strategies found each type
- **Overall Coverage**: Combined coverage across all strategies

### Quality Indicators
- **High Coverage** (>80%): Excellent extraction
- **Medium Coverage** (50-80%): Good extraction, room for improvement
- **Low Coverage** (<50%): Needs enhancement

### Confidence Scores
- **Very High** (0.9-1.0): Highly reliable
- **High** (0.8-0.9): Reliable
- **Medium** (0.7-0.8): Moderately reliable
- **Low** (0.6-0.7): Less reliable
- **Very Low** (<0.6): Unreliable

## Future Enhancements

Potential improvements to the framework:
1. Add precision/recall calculation with ground truth
2. Implement entity deduplication analysis
3. Add position accuracy verification
4. Create interactive HTML dashboards
5. Add comparative analysis across documents
6. Implement batch testing for multiple documents
7. Add pattern contribution analysis
8. Create entity relationship extraction metrics

## License

Part of the Luris backend services.