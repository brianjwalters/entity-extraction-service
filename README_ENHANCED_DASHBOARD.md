# Enhanced HTML Dashboard for CALES NLP/BERT Testing

## Overview

The enhanced HTML dashboard provides comprehensive visualization and analysis of CALES NLP/BERT entity extraction test results. It features interactive charts, sortable data tables, and detailed entity analysis capabilities.

## Key Features

### 🎯 Detailed Entity Analysis
- **Entity Breakdown Grid**: Interactive pie, bar, and scatter charts showing entity distribution, confidence levels, and position analysis
- **Context Windows**: View surrounding text for each extracted entity
- **Citation Analysis**: Bluebook compliance checking and format validation
- **Confidence Distribution**: Visual analysis of extraction confidence across entity types

### 📊 Interactive Charts
- **Bar Charts**: Entity counts by type and phase progression
- **Pie Charts**: Entity distribution percentages and processing time allocation  
- **Heatmaps**: Confidence scores across entity types and extraction methods
- **Line Charts**: Performance metrics across test phases
- **Scatter Plots**: Position vs confidence correlation analysis

### 📋 Sortable/Filterable Tables
- **Entity Details Table**: Complete entity information with filtering by type and confidence
- **Citation Analysis Table**: Bluebook format validation with component breakdown
- **Performance Metrics Table**: Processing time, memory usage, and throughput analysis

### 🎨 Visual Improvements
- **Responsive Design**: Mobile-friendly layout with Bootstrap-style components
- **Professional Styling**: Gradient backgrounds, hover effects, and modern UI elements
- **Export Functionality**: Download charts as images and data as JSON
- **Tooltip Details**: Hover for additional context and information

## Usage

### Generate Dashboard

```bash
# Activate virtual environment
source venv/bin/activate

# Generate dashboard from test results
python generate_cales_html_dashboard.py tests/results/your_test_results.json

# Dashboard will be created in the same directory as the input file
```

### Dashboard Navigation

The dashboard includes 5 main tabs:

1. **📊 Overview**: Executive summary with key metrics and phase comparison
2. **📈 Charts**: Interactive visualizations of entity detection and performance
3. **🎯 Entities**: Detailed entity analysis with filterable tables
4. **⚡ Performance**: Processing time, memory usage, and throughput metrics
5. **🔍 Comparison**: Side-by-side analysis between different test phases

### Interactive Features

#### Entity Analysis Tab
- **Entity Type Filter**: Filter entities by type (Judge, Citation, Court, etc.)
- **Confidence Range**: Adjust minimum confidence threshold with slider
- **Context Viewing**: Hover over entities to see surrounding text
- **Export Options**: Download entity data as JSON

#### Performance Tab
- **Throughput Analysis**: Entities processed per second across phases
- **Memory Efficiency**: Memory usage vs entity count correlation
- **GPU Utilization**: Hardware performance metrics (when available)
- **Processing Time Breakdown**: Time spent in different extraction phases

#### Comparison Tab
- **Phase Selection**: Choose any two phases for detailed comparison
- **Overlap Analysis**: Venn diagrams showing entity overlap between phases
- **Unique Entities**: Lists of entities found only in specific phases
- **Statistical Comparison**: Precision, recall, and F1 scores

## Expected Input Format

The dashboard expects JSON test results in this format:

```json
{
    "test_metadata": {
        "timestamp": "2025-09-11T16:01:55Z",
        "document": "Rahimi.pdf",
        "test_type": "CALES_NLP_BERT_Comprehensive"
    },
    "phase_results": {
        "Phase 1: REGEX Only": {
            "total_entities": 145,
            "entity_types": ["JUDGE", "CITATION", "COURT"],
            "avg_confidence": 0.87,
            "processing_time_seconds": 2.34,
            "memory_usage_mb": 89.5,
            "entity_mappings": [
                {
                    "text": "Chief Justice Roberts",
                    "entity_type": "JUDGE",
                    "confidence_score": 0.95,
                    "position": {"start": 1234, "end": 1255},
                    "context": "...delivered the opinion of the Court. Chief Justice Roberts...",
                    "normalized_text": "John G. Roberts Jr.",
                    "extraction_method": "regex"
                }
            ],
            "citation_mappings": [
                {
                    "text": "District of Columbia v. Heller",
                    "bluebook_format": "District of Columbia v. Heller, 554 U.S. 570 (2008)",
                    "components": {
                        "reporter": "U.S.",
                        "volume": "554",
                        "page": "570",
                        "year": "2008"
                    },
                    "confidence_score": 0.98,
                    "position": {"start": 2345, "end": 2375}
                }
            ]
        },
        "Phase 2: NLP Enhanced": {
            // Similar structure with additional entities
        }
    }
}
```

## Sample Dashboard Output

### Overview Tab
```
📊 Executive Summary
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   Test Phases   │ Successful      │ Best Entity     │ Improvement vs  │
│        4        │ Phases: 4       │ Count: 178      │ Baseline: 23%   │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘

💡 Key Findings:
• Baseline (REGEX Only): 145 entities
• Best Performance: Phase 3: BERT + Context with 178 entities  
• Overall Improvement: 23% increase in entity detection
• All NLP/BERT models successfully avoided vLLM timeout issues
```

### Entity Analysis Tab
```
🎯 Entity Distribution

JUDGES EXTRACTED (Confidence ≥ 0.8):
• "Chief Justice Roberts" → "John G. Roberts Jr." [0.95] 📍 pos:1234-1255
  Context: "...delivered the opinion of the Court. Chief Justice Roberts..."
• "Justice Scalia" → "Antonin Gregory Scalia" [0.92] 📍 pos:3456-3469
  Context: "...Justice Scalia wrote the majority opinion stating that..."

CASE CITATIONS EXTRACTED:
• "District of Columbia v. Heller" [0.98] 📍 pos:2345-2375
  Bluebook: District of Columbia v. Heller, 554 U.S. 570 (2008)
  Components: Reporter=U.S., Volume=554, Page=570, Year=2008
```

### Performance Tab
```
⚡ Performance Metrics

Processing Time by Phase:
Phase 1 (REGEX):     2.34s  |████████░░| 65 ent/s
Phase 2 (NLP):       4.67s  |████████░░| 58 ent/s  
Phase 3 (BERT):      6.12s  |██████████| 69 ent/s
Phase 4 (Context):   5.89s  |██████████| 72 ent/s

💡 Performance Insights:
• Fastest Phase: Phase 1 (REGEX Only)
• Most Efficient: Phase 4 (Context Enhanced) - 72 entities/sec
• Memory Optimization: BERT phases show best entity/memory ratios
• Scaling Potential: Linear time scaling observed across phases
```

## Technical Implementation

### Enhanced JavaScript Features
- **Dynamic Chart Creation**: Charts are generated based on actual data structure
- **Real-time Filtering**: Tables update immediately as filters are applied
- **Data Export**: Client-side JSON generation for easy data sharing
- **Responsive Charts**: Chart.js integration with mobile-friendly layouts

### CSS Enhancements
- **Modern Styling**: Gradient backgrounds, shadow effects, and smooth transitions
- **Grid Layouts**: CSS Grid for responsive component arrangement
- **Interactive Elements**: Hover effects, tooltips, and animated confidence bars
- **Professional Typography**: Segoe UI font stack with proper spacing

### Data Processing
- **Pandas Integration**: Backend data processing using pandas DataFrames
- **Statistical Analysis**: Confidence distributions and performance correlations
- **Entity Normalization**: Text cleanup and standardization
- **Citation Validation**: Bluebook format compliance checking

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+  
- ✅ Safari 14+
- ✅ Edge 90+

## File Size and Performance

- **HTML File Size**: ~2-5MB depending on data volume
- **Load Time**: <3 seconds for typical test results
- **Memory Usage**: ~50-100MB in browser
- **Chart Rendering**: <1 second for all visualizations

## Troubleshooting

### Common Issues

1. **Charts Not Displaying**
   - Ensure internet connection for CDN resources
   - Check browser console for JavaScript errors

2. **Tables Not Sorting**
   - Verify jQuery and DataTables are loaded
   - Check for JSON parsing errors

3. **Mobile Layout Issues**
   - Clear browser cache
   - Ensure viewport meta tag is present

### Support

For issues or enhancement requests, check the entity extraction service logs and verify test result JSON format compliance.