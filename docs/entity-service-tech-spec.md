# Entity Extraction Service Technical Specification

**Version**: 3.0.0  
**Service Port**: 8007  
**Last Updated**: January 2025  
**Maintainer**: Legal Data Engineer  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Pattern Library Reference](#3-pattern-library-reference)
4. [AI Enhancement System](#4-ai-enhancement-system)
5. [API Documentation](#5-api-documentation)
6. [Data Models](#6-data-models)
7. [Client Integration](#7-client-integration)
8. [Deployment Guide](#8-deployment-guide)
9. [Performance & Quality](#9-performance--quality)
10. [Integration Examples](#10-integration-examples)
11. [Appendices](#11-appendices)

---

## 1. Executive Summary

The Entity Extraction Service is a sophisticated legal document processing system that combines high-performance regex pattern matching with self-contained local AI enhancement. Operating on port 8007, this service serves as a critical component in the Luris legal document processing pipeline, providing accurate extraction and classification of legal entities, citations, and relationships from legal documents with breakthrough 176ms performance.

### Key Capabilities

- **Comprehensive Pattern Coverage**: 53 YAML pattern files covering federal jurisdiction and all 49 US states
- **Local AI Integration**: Self-contained IBM Granite 3.3-8B model for breakthrough 176ms performance
- **5 Performance Profiles**: Optimized configurations for different use cases (breakthrough, speed, batch, memory, quality)
- **High Performance**: 176ms-1000ms response times depending on configuration profile
- **Bluebook Compliance**: Full compliance with Bluebook 22nd Edition citation standards
- **Entity Recognition**: 31 legal entity types with rich attribute modeling
- **AI Enhancement**: 5 specialized AI prompt templates for validation, enhancement, and relationship discovery
- **Self-Contained Architecture**: No external AI service dependencies for maximum reliability

### Business Value

The Entity Extraction Service enables automated legal document analysis at scale, providing:
- Accurate entity extraction with 94-98% precision across different pattern types
- Standardized legal citation formatting and validation
- Relationship discovery between legal entities
- Integration with GraphRAG pipeline for knowledge graph construction
- Significant time savings for legal document processing workflows

### Technical Architecture

Built on FastAPI with asynchronous processing capabilities, the service implements a sophisticated hybrid workflow that combines:
- Regex-based pattern matching for high-speed, accurate extraction
- Local AI-powered validation and enhancement via LlamaLocalClient
- GPU-accelerated processing with up to 64 GPU layers
- Advanced memory management with automatic cleanup at 85% threshold
- Real-time performance monitoring with breakthrough achievement tracking
- Comprehensive data models with UUID-based entity tracking
- Flexible attribute system supporting diverse legal entity types
- Performance optimization for batch document processing

---

## 2. Architecture Overview

### Service Architecture

The Entity Extraction Service follows a modular, scalable architecture designed for high-performance legal document processing:

```
┌─────────────────────────────────────────────────────────────┐
│                    Entity Extraction Service                │
│                         (Port 8007)                        │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                       │
│  ├── Health Endpoints (/api/v1/health)                     │
│  ├── Extraction Endpoints (/api/v1/extract)                │
│  └── Authentication & Rate Limiting                        │
├─────────────────────────────────────────────────────────────┤
│  Core Processing Engine                                     │
│  ├── Extraction Service (extraction_service.py)           │
│  ├── Regex Engine (regex_engine.py)                        │
│  ├── AI Enhancer (ai_enhancer.py)                         │
│  └── Pattern System (patterns/)                            │
├─────────────────────────────────────────────────────────────┤
│  Local AI Integration (Self-Contained)                     │
│  ├── LlamaLocalClient (llama_local_client.py)             │
│  ├── IBM Granite 3.3-8B Model                              │
│  ├── 5 Performance Profiles                                │
│  ├── GPU Acceleration (64 GPU layers)                      │
│  ├── Performance Monitoring                                │
│  └── Memory Management (85% threshold cleanup)             │
├─────────────────────────────────────────────────────────────┤
│  Pattern Library (53 YAML Files)                           │
│  ├── Federal Patterns (4 files)                            │
│  │   ├── Supreme Court                                      │
│  │   ├── Appellate Courts                                   │
│  │   ├── District Courts                                    │
│  │   ├── USC Statutes                                       │
│  │   └── CFR Regulations                                    │
│  └── State Patterns (49 files)                             │
│      └── All US States + DC                                │
├─────────────────────────────────────────────────────────────┤
│  AI Prompt Templates (5 Templates)                         │
│  ├── Entity Validation                                     │
│  ├── Relationship Extraction                               │
│  ├── Context Enhancement                                   │
│  ├── Citation Refinement                                   │
│  └── Error Correction                                      │
├─────────────────────────────────────────────────────────────┤
│  Data Models & Storage                                      │
│  ├── Entity Models (entities.py)                           │
│  ├── Request/Response Models                               │
│  └── UUID-based Entity Tracking                            │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    External Service Integration
                    ├── Log Service (Port 8001)
                    └── Supabase Service (Port 8002)
```

### Core Components

#### 1. Extraction Service (`src/core/extraction_service.py`)
The main orchestration engine that coordinates the hybrid extraction workflow:

```python
class ExtractionService:
    """Main extraction service coordinating regex and AI processing."""
    
    def __init__(self):
        self.regex_engine = RegexEngine()
        self.ai_enhancer = AIEnhancer()
        self.pattern_loader = PatternLoader()
    
    async def extract_entities(self, text: str, extraction_mode: str) -> ExtractionResult:
        """Primary extraction method supporting multiple modes."""
        pass
```

**Key Responsibilities:**
- Orchestrates regex pattern matching
- Coordinates AI enhancement workflow
- Manages extraction mode selection
- Handles confidence scoring and validation
- Produces final extraction results

#### 2. Regex Engine (`src/core/regex_engine.py`)
High-performance pattern matching engine supporting all legal citation formats:

**Features:**
- Concurrent pattern processing for optimal performance
- Support for 53 jurisdiction-specific pattern files
- Advanced confidence scoring algorithms
- Bluebook 22nd Edition compliance validation
- Context-aware entity extraction

#### 3. AI Enhancer (`src/core/ai_enhancer.py`)
Local AI-powered validation and enhancement system with breakthrough performance:

**Capabilities:**
- Entity validation and confidence refinement via LlamaLocalClient
- Relationship discovery between entities with GPU acceleration
- Citation format standardization with 176ms target response time
- Context enhancement and error correction with local processing
- Self-contained AI processing with no external service dependencies
- Real-time performance monitoring and breakthrough achievement tracking

#### 4. Pattern System (`src/patterns/`)
Comprehensive pattern library covering all US legal jurisdictions:

**Structure:**
- **Federal patterns**: Supreme Court, Circuit Courts, District Courts, Statutes, Regulations
- **State patterns**: Complete coverage of all 49 states plus Washington D.C.
- **Pattern metadata**: Confidence thresholds, validation rules, examples
- **Testing framework**: Automated pattern validation and performance benchmarks

### Processing Workflow

The Entity Extraction Service implements a sophisticated hybrid workflow:

1. **Document Preprocessing**: Text normalization and structure analysis
2. **Regex Pattern Matching**: High-speed pattern application across all jurisdictions
3. **Initial Entity Extraction**: Primary entity identification with confidence scoring
4. **AI Validation & Enhancement**: LLM-powered validation and enhancement
5. **Relationship Discovery**: AI-driven relationship identification between entities
6. **Quality Assurance**: Confidence calibration and validation
7. **Result Compilation**: Final entity and relationship compilation with metadata

---

## 3. Pattern Library Reference

The Entity Extraction Service maintains a comprehensive pattern library consisting of 53 YAML files covering federal and state jurisdictions. Each pattern file contains sophisticated regex patterns optimized for accuracy and performance.

### Pattern File Structure

Every pattern file follows a standardized YAML structure:

```yaml
metadata:
  pattern_type: "jurisdiction_type"
  jurisdiction: "jurisdiction_name"
  court_level: "court_hierarchy_level"
  bluebook_compliance: "22nd_edition"
  pattern_version: "1.0"
  created_date: "2025-07-29"
  description: "Pattern description"

# Citation patterns
case_citations:
  pattern_name:
    name: "descriptive_pattern_name"
    pattern: 'regex_pattern_with_named_groups'
    confidence: 0.95
    components:
      field_name: "field_description"
    examples:
      - "Example citation 1"
      - "Example citation 2"

# Entity classification
entity_types:
  - name: "ENTITY_TYPE_NAME"
    description: "Entity description"
    confidence_threshold: 0.90

# Validation rules
validation:
  year_range:
    min_year: 1850
    max_year: 2025
  volume_ranges:
    reporter_name:
      min_volume: 1
      max_volume: 999

# Quality metrics
quality_metrics:
  precision_target: 0.96
  recall_target: 0.94
  processing_speed: "1000_citations_per_second"
```

### Federal Pattern Coverage

#### Supreme Court Patterns (`federal/supreme_court.yaml`)

**Case Citation Patterns:**
- **U.S. Reports**: Primary Supreme Court reporter
  ```
  Pattern: Brown v. Board of Education, 347 U.S. 483 (1954)
  Confidence: 0.98
  Components: case_name, volume, page, year
  ```

- **Supreme Court Reporter**: West's Supreme Court Reporter
  ```
  Pattern: Brown v. Board of Education, 74 S. Ct. 686 (1954)  
  Confidence: 0.95
  Components: case_name, volume, page, year
  ```

- **Lawyers' Edition**: LexisNexis Supreme Court reporter
  ```
  Pattern: Brown v. Board of Education, 98 L. Ed. 873 (1954)
  Confidence: 0.92
  ```

**Justice Patterns:**
- Justice name recognition with titles
- Opinion authorship attribution
- Court procedural elements

#### Circuit Court Patterns (`federal/appellate_courts.yaml`)

**Federal Reporter Citations:**
- **F.2d, F.3d, F.4th Series**: Complete Federal Reporter coverage
- **Circuit Identification**: All 13 circuits (1st-11th, D.C., Fed.)
- **Unpublished Decisions**: Westlaw citation format support

```yaml
federal_reporter:
  pattern: 'United States v. Nixon, 418 F.2d 1110 (D.C. Cir. 1969)'
  confidence: 0.96
  components:
    - case_name: "Full case name with parties"
    - volume: "Federal Reporter volume number" 
    - series: "Federal Reporter series (2d, 3d, 4th)"
    - page: "Starting page number"
    - circuit: "Circuit court designation"
    - year: "Decision year"
```

#### District Court Patterns (`federal/district_courts.yaml`)

**Federal Supplement Citations:**
- **F. Supp., F. Supp. 2d, F. Supp. 3d**: Complete coverage
- **District Identification**: All 94 federal districts
- **Geographic Mapping**: State-to-district relationships

**Federal Rules Integration:**
- Civil Procedure Rules (Fed. R. Civ. P.)
- Criminal Procedure Rules (Fed. R. Crim. P.)
- Evidence Rules (Fed. R. Evid.)

#### Statutory Patterns (`federal/usc_statutes.yaml`)

**U.S. Code Citations:**
- **Basic USC Format**: `42 U.S.C. § 1983`
- **Range Citations**: `42 U.S.C. §§ 1981-1988`
- **Subsection Support**: Complex section hierarchies

**Title-Specific Patterns:**
- **Title 42**: Civil Rights provisions
- **Title 28**: Federal Courts and jurisdiction
- **Title 15**: Securities and commerce
- **Title 17**: Copyright law
- **Title 26**: Internal Revenue Code

#### Regulatory Patterns (`federal/cfr_regulations.yaml`)

**Code of Federal Regulations:**
- **Basic CFR Format**: `17 C.F.R. § 240.10b-5`
- **Federal Register**: Daily publication citations
- **Agency-Specific Patterns**: SEC, IRS, OSHA, EPA regulations

### State Pattern Coverage

The service includes comprehensive patterns for all 49 US states plus Washington D.C. Each state pattern file contains:

#### Example: California Patterns (`states/california.yaml`)

**Court Hierarchy:**
- **California Supreme Court**: Cal. reports series
- **California Court of Appeal**: Cal. App. reports with district designation  
- **California Superior Court**: County-specific trial courts

```yaml
ca_supreme_court_cal_reports:
  pattern: 'People v. Davis, 15 Cal. 5th 1239 (2024)'
  confidence: 0.92
  entity_type: "CASE_CITATION"
  entity_subtype: "california_supreme"
```

**California Codes:**
- Civil Code, Penal Code, Business & Professions Code
- Complete section numbering support
- Constitutional article and section references

#### Example: Washington Patterns (`states/washington.yaml`)

**Court System:**
- **Washington Supreme Court**: Washington Reports and Pacific Reporter
- **Washington Court of Appeals**: Three-division structure
- **Superior and District Courts**: County-specific jurisdiction

**Statutory Citations:**
- **Revised Code of Washington (RCW)**: Complete statutory coverage
- **Washington Administrative Code**: Regulatory citations
- **Washington Constitution**: Article and section references

### Pattern Performance Metrics

Each pattern includes comprehensive performance benchmarks:

| Pattern Type | Precision Target | Recall Target | Processing Speed |
|--------------|------------------|---------------|------------------|
| Federal Supreme Court | 0.98 | 0.95 | 1000 cites/sec |
| Federal Appellate | 0.96 | 0.93 | 800 cites/sec |
| Federal District | 0.95 | 0.92 | 750 cites/sec |
| USC Statutes | 0.96 | 0.94 | 1200 cites/sec |
| CFR Regulations | 0.95 | 0.93 | 1000 cites/sec |
| State Courts (avg) | 0.94 | 0.91 | 850 cites/sec |

### Pattern Validation and Testing

Each pattern file includes comprehensive testing configuration:

```yaml
testing:
  test_cases:
    - pattern: "case_citations.primary_citation"
      text: "Brown v. Board of Education, 347 U.S. 483 (1954)"
      expected_entities: 1
      expected_confidence: 0.98
  performance_benchmarks:
    document_processing_time: "< 2 seconds"
    memory_usage: "< 100MB"  
    accuracy_threshold: 0.95
```

---

## 4. Local AI Enhancement System

The Entity Extraction Service implements a sophisticated local AI enhancement system that augments regex-based extraction with self-contained LLM-powered validation, enhancement, and discovery capabilities. This hybrid approach combines the speed and reliability of regex patterns with the contextual understanding and flexibility of local AI processing, achieving breakthrough 176ms performance with no external service dependencies.

### AI Architecture

```
┌─────────────────────────────────────────────────────────┐
│            Local AI Enhancement Pipeline               │
│          (LlamaLocalClient Integration)                 │
├─────────────────────────────────────────────────────────┤
│  Input: Regex-extracted entities + Document context    │
├─────────────────────────────────────────────────────────┤
│  Stage 1: Entity Validation (Local AI)                 │
│  ├── Confidence refinement (176ms target)              │
│  ├── Bluebook compliance validation                    │
│  ├── Entity type verification                          │
│  └── Context coherence checking                        │
├─────────────────────────────────────────────────────────┤
│  Stage 2: Entity Enhancement (GPU Accelerated)         │
│  ├── Text cleaning and standardization                 │
│  ├── Canonical name resolution                         │
│  ├── Attribute enrichment                              │
│  └── Alternative name discovery                        │
├─────────────────────────────────────────────────────────┤
│  Stage 3: Relationship Discovery (Breakthrough)        │
│  ├── Entity-to-entity relationship identification      │
│  ├── Legal authority relationship mapping              │
│  ├── Procedural relationship discovery                 │
│  └── Temporal relationship analysis                    │
├─────────────────────────────────────────────────────────┤
│  Stage 4: Citation Refinement (Local Processing)       │
│  ├── Citation format standardization                   │
│  ├── Parallel citation identification                  │
│  ├── Authority weight calculation                      │
│  └── Cross-reference validation                        │
├─────────────────────────────────────────────────────────┤
│  Stage 5: Error Correction (Self-Contained)            │
│  ├── Pattern matching error detection                  │
│  ├── Context-based error correction                    │
│  ├── False positive elimination                        │
│  └── Missing entity discovery                          │
├─────────────────────────────────────────────────────────┤
│  Output: Enhanced entities with local AI metadata      │
│  Performance: 176ms-1000ms (profile dependent)         │
└─────────────────────────────────────────────────────────┘
```

### AI Prompt Templates

The service includes 5 specialized prompt templates for different AI enhancement tasks:

#### 1. Entity Validation (`prompts/entity_validation.md`)

**Purpose**: Validate and score entities extracted by regex patterns

**Key Features:**
- Bluebook 22nd Edition compliance validation
- Confidence score refinement (0.0-1.0 scale)
- Entity type accuracy verification
- Context coherence validation

**Input Parameters:**
```yaml
variables:
  - entities: List of regex-extracted entities
  - document_text: Full document text
  - document_type: Document classification
  - jurisdiction: Legal jurisdiction
  - extraction_confidence: Initial regex confidence
```

**Confidence Scoring Methodology:**
- **High Confidence (0.8-1.0)**: Perfect Bluebook compliance, clear context
- **Medium Confidence (0.5-0.79)**: Minor issues, recognizable format
- **Low Confidence (0.0-0.49)**: Major violations, ambiguous text

**Example Response:**
```json
{
  "validation_summary": {
    "total_entities_processed": 15,
    "overall_quality_score": 0.92,
    "bluebook_compliance_rate": 0.87
  },
  "validated_entities": [
    {
      "original_entity_id": "uuid",
      "validation_result": "ENHANCED",
      "confidence_score": 0.94,
      "cleaned_text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "bluebook_compliant": true,
      "ai_enhancements": [
        "Standardized case name format",
        "Verified citation accuracy"
      ]
    }
  ]
}
```

#### 2. Relationship Extraction (`prompts/relationship_extraction.md`)

**Purpose**: Discover and categorize relationships between legal entities

**Relationship Types:**
- **Legal Authority**: `CITES`, `RELIES_ON`, `FOLLOWS`, `OVERRULES`
- **Jurisdictional**: `HAS_JURISDICTION_OVER`, `APPEALS_TO`, `REVIEWS`
- **Procedural**: `REPRESENTS`, `DECIDES`, `FILES_AGAINST`, `MOVES_FOR`
- **Temporal**: `PRECEDES`, `FOLLOWS_IN_TIME`, `IS_DEADLINE_FOR`
- **Business**: `CONTRACTS_WITH`, `OWNS`, `SEEKS_DAMAGES_FROM`

**Example Response:**
```json
{
  "relationships": [
    {
      "source_entity_id": "entity-123",
      "target_entity_id": "entity-456",
      "relationship_type": "CITES",
      "confidence_score": 0.89,
      "evidence_text": "Following the precedent established in Brown v. Board",
      "relationship_attributes": {
        "authority_level": "binding",
        "legal_weight": 0.95
      }
    }
  ]
}
```

#### 3. Context Enhancement (`prompts/context_enhancement.md`)

**Purpose**: Enhance entity extraction with broader document context

**Features:**
- Document structure analysis
- Section-aware entity categorization
- Cross-reference identification
- Contextual attribute extraction

#### 4. Citation Refinement (`prompts/citation_refinement.md`)

**Purpose**: Standardize and enhance legal citations

**Capabilities:**
- Bluebook format standardization
- Parallel citation discovery
- Authority weight calculation
- Cross-reference validation

#### 5. Error Correction (`prompts/error_correction.md`)

**Purpose**: Identify and correct extraction errors

**Error Types:**
- False positive elimination
- Missing entity discovery
- Context-based corrections
- Format standardization

### AI Integration Workflow

The AI enhancement system integrates seamlessly with the core extraction workflow:

```python
class AIEnhancer:
    """AI enhancement coordinator for entity extraction."""
    
    def __init__(self):
        self.prompt_service = PromptServiceClient()
        self.templates = {
            'validation': 'entity_validation.md',
            'relationships': 'relationship_extraction.md',
            'context': 'context_enhancement.md',
            'citations': 'citation_refinement.md',
            'correction': 'error_correction.md'
        }
    
    async def enhance_entities(
        self, 
        entities: List[Entity], 
        document_text: str,
        enhancement_mode: str = "full"
    ) -> EnhancedExtractionResult:
        """
        Enhance regex-extracted entities with AI processing.
        
        Args:
            entities: List of regex-extracted entities
            document_text: Full document text for context
            enhancement_mode: AI processing intensity
            
        Returns:
            Enhanced entities with AI metadata
        """
        
        # Stage 1: Entity validation
        validated_entities = await self._validate_entities(
            entities, document_text
        )
        
        # Stage 2: Relationship discovery
        relationships = await self._extract_relationships(
            validated_entities, document_text
        )
        
        # Stage 3: Citation refinement
        refined_citations = await self._refine_citations(
            validated_entities, document_text
        )
        
        # Stage 4: Error correction
        corrected_entities = await self._correct_errors(
            validated_entities, document_text
        )
        
        return EnhancedExtractionResult(
            entities=corrected_entities,
            relationships=relationships,
            ai_metadata=self._compile_ai_metadata(),
            enhancement_summary=self._create_summary()
        )
```

### AI Processing Modes

The service supports multiple AI processing modes:

#### 1. Traditional Mode (`extraction_mode: "traditional"`)
- Regex-only extraction
- No AI enhancement
- Maximum processing speed
- Confidence scores from regex patterns only

#### 2. AI Enhanced Mode (`extraction_mode: "ai_enhanced"`)
- Regex extraction + AI validation
- Entity confidence refinement
- Basic relationship discovery
- Balanced speed and accuracy

#### 3. Hybrid Mode (`extraction_mode: "hybrid"`)
- Full AI enhancement pipeline
- Complete relationship extraction
- Citation refinement and standardization
- Maximum accuracy with moderate speed

#### 4. AI Discovered Mode (`extraction_mode: "ai_discovered"`)
- AI-first entity discovery
- Regex validation of AI findings
- Novel entity pattern discovery
- Highest accuracy, slower processing

### Performance Optimization

The AI enhancement system includes several performance optimizations:

**Caching Strategy:**
- Template compilation caching
- Response caching for similar document patterns
- Entity validation result caching

**Batch Processing:**
- Entity batching for AI requests
- Parallel processing of independent enhancements
- Optimized prompt template loading

**Quality Gates:**
- Confidence threshold filtering
- Processing time limits
- Error detection and fallback

### AI Quality Metrics

The AI system maintains comprehensive quality metrics:

```yaml
ai_quality_metrics:
  entity_validation:
    accuracy_improvement: 12%  # Over regex-only
    bluebook_compliance_rate: 94%
    false_positive_reduction: 18%
  
  relationship_discovery:
    precision: 0.87
    recall: 0.82
    novel_relationships_found: 23%
  
  citation_refinement:
    bluebook_standardization_rate: 96%
    parallel_citation_discovery: 31%
    authority_weight_accuracy: 0.91
  
  processing_performance:
    average_enhancement_time: 2.3s
    batch_processing_efficiency: 85%
    cache_hit_rate: 67%
```

### Local AI Performance Profiles

The Entity Extraction Service includes 5 optimized configuration profiles for different use cases and performance requirements:

#### 1. Breakthrough Optimized (Default)
**Profile**: `breakthrough_optimized`  
**Target**: ≤176ms response time (SS tier performance)

```yaml
Configuration:
  model: "Qwen/Qwen3-VL-8B-Instruct-FP8-GGUF"
  n_gpu_layers: 64      # Heavy GPU utilization
  n_parallel: 48        # Optimized parallelization
  n_batch: 32768        # Large batch processing
  n_ubatch: 8192        # Critical performance parameter
  n_ctx: 768            # Optimized context for legal entities
  n_threads: 12         # Stable threading
  memory_limit_gb: 8.0  # Memory management

Performance Characteristics:
  target_response_time: 176ms
  memory_usage: 8GB
  gpu_utilization: High
  best_for: "Production APIs requiring ultra-fast response"
```

#### 2. Speed Optimized
**Profile**: `speed_optimized`  
**Target**: ≤100ms response time (SS Lightning tier)

```yaml
Configuration:
  n_gpu_layers: 64      # Maximum GPU utilization
  n_parallel: 32        # Single-document focus
  n_batch: 16384        # Faster response batches
  n_ubatch: 4096        # Low latency optimization
  n_ctx: 512            # Minimal context for speed
  n_threads: 8          # Reduced thread contention
  memory_limit_gb: 4.0  # Efficient memory usage

Performance Characteristics:
  target_response_time: 100ms
  memory_usage: 4GB
  gpu_utilization: Maximum
  best_for: "Real-time UIs requiring absolute minimum latency"
```

#### 3. Batch Optimized
**Profile**: `batch_optimized`  
**Target**: ≤300ms response time with high throughput

```yaml
Configuration:
  n_gpu_layers: 64      # Maximum GPU utilization
  n_parallel: 64        # High parallelization
  n_batch: 65536        # Large batch processing
  n_ubatch: 16384       # Large micro-batches
  n_ctx: 1024           # Larger context for complex docs
  n_threads: 16         # More threads for batch processing
  memory_limit_gb: 12.0 # Higher memory for throughput

Performance Characteristics:
  target_response_time: 300ms
  memory_usage: 12GB
  gpu_utilization: Maximum
  best_for: "Bulk document processing with high throughput"
```

#### 4. Memory Constrained
**Profile**: `memory_constrained`  
**Target**: ≤500ms response time with minimal memory usage

```yaml
Configuration:
  n_gpu_layers: 32      # Reduced GPU layers
  n_parallel: 16        # Lower parallelization
  n_batch: 8192         # Smaller batches
  n_ubatch: 2048        # Smaller micro-batches
  n_ctx: 512            # Minimal context
  use_mmap: true        # Enable memory mapping
  memory_limit_gb: 3.0  # Conservative memory usage

Performance Characteristics:
  target_response_time: 500ms
  memory_usage: 3GB
  gpu_utilization: Moderate
  best_for: "Resource-constrained environments"
```

#### 5. Quality Focused
**Profile**: `quality_focused`  
**Target**: ≤1000ms response time with maximum accuracy

```yaml
Configuration:
  n_gpu_layers: 64      # Maximum GPU utilization
  n_parallel: 24        # Moderate parallelization
  n_batch: 16384        # Medium batches
  n_ubatch: 4096        # Quality-optimized batching
  n_ctx: 2048           # Larger context for understanding
  cache_type_k: "f32"   # Higher precision cache
  cache_type_v: "f32"   # Higher precision cache
  memory_limit_gb: 10.0 # Quality-focused memory

Performance Characteristics:
  target_response_time: 1000ms
  memory_usage: 10GB
  gpu_utilization: High
  best_for: "Critical legal analysis requiring maximum accuracy"
```

### Performance Profile Selection Matrix

| Use Case | Profile | Response Time | Memory | GPU | Accuracy |
|----------|---------|---------------|--------|-----|----------|
| Production API | breakthrough_optimized | ≤176ms | 8GB | High | High |
| Real-time UI | speed_optimized | ≤100ms | 4GB | Max | High |
| Bulk Processing | batch_optimized | ≤300ms | 12GB | Max | High |
| Development/Testing | memory_constrained | ≤500ms | 3GB | Mod | Medium |
| Legal Analysis | quality_focused | ≤1000ms | 10GB | High | Maximum |

### Configuration Usage Examples

```python
# Programmatic profile selection
from src.client.llama_local_client import (
    create_optimized_client,
    create_speed_optimized_client,
    create_batch_optimized_client,
    create_memory_constrained_client,
    create_quality_focused_client
)

# Use breakthrough configuration (default)
client = create_optimized_client()

# Use speed-optimized for real-time processing
speed_client = create_speed_optimized_client()

# Use batch-optimized for bulk processing
batch_client = create_batch_optimized_client()
```

```bash
# Environment variable configuration
export LLAMA_CONFIG_PROFILE=speed_optimized
export LLAMA_GPU_LAYERS=64
export LLAMA_MEMORY_LIMIT_GB=4

# YAML configuration
llama_local:
  profile_name: "breakthrough_optimized"
  target_response_time_ms: 176
  n_gpu_layers: 64
```

---

## 5. API Documentation

The Entity Extraction Service provides a comprehensive REST API built on FastAPI, offering high-performance entity extraction capabilities with flexible processing modes and detailed response formatting.

### 📋 Complete API Reference

For exhaustive API documentation including all endpoints, schemas, examples, and integration patterns, see:

**[Entity Types and Patterns API Technical Specification](./ENTITY_TYPES_PATTERNS_API_SPECIFICATION.md)**

This comprehensive specification document covers:
- **Complete API Endpoints**: All entity-types and patterns endpoints with full schemas
- **Request/Response Examples**: Every endpoint variation with real examples
- **Integration Patterns**: Python and JavaScript client libraries with error handling
- **Performance Guidelines**: Response times, caching strategies, optimization patterns
- **Error Handling**: Complete error codes and recovery strategies

### Base Configuration

- **Service URL**: `http://localhost:8007`
- **API Version**: `v1`
- **Base Path**: `/api/v1`
- **Authentication**: Development mode (no auth required)
- **Content Type**: `application/json`
- **Rate Limiting**: 100 requests/minute per IP
- **Local AI**: IBM Granite 3.3-8B with breakthrough 176ms performance

### Key API Endpoints Summary

#### Entity Types Discovery
- `GET /api/v1/entity-types` - Get all 160 entity types + 112 citation types
- `GET /api/v1/entity-types/categories` - Get categorized entity type summary  
- `GET /api/v1/entity-types/{entity_type}` - Get detailed entity type information

#### Pattern Management
- `GET /api/v1/patterns/detailed` - Get all 396 regex patterns with metadata
- `GET /api/v1/patterns/comprehensive` - Get comprehensive pattern coverage with deduplication

#### Extraction Core
- `POST /api/v1/extract` - Primary entity extraction endpoint
- `GET /api/v1/extract/{id}/status` - Check extraction progress
- `GET /api/v1/extract/{id}` - Retrieve extraction results

### Authentication

**Development Mode**: The service currently runs in development mode with no authentication required. All endpoints are accessible without tokens.

**Production Deployment**: JWT Bearer tokens will be required for production deployment:

```bash
# Development mode (current) - no auth required
curl -H "Content-Type: application/json" \
     http://localhost:8007/api/v1/entity-types

# Production mode (future) - JWT required  
curl -H "Authorization: Bearer <jwt_token>" \
     -H "Content-Type: application/json" \
     http://localhost:8007/api/v1/entity-types
```

### Health Endpoints

#### GET `/api/v1/health/ping`
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "entity-extraction-service",
  "version": "2.1.0",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### GET `/api/v1/health/detailed`
Comprehensive health status with system metrics.

**Response:**
```json
{
  "status": "healthy",
  "service": "entity-extraction-service",
  "version": "2.1.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "system_metrics": {
    "patterns_loaded": 53,
    "ai_templates_available": 5,
    "memory_usage_mb": 245,
    "cpu_usage_percent": 12.5,
    "uptime_seconds": 86400
  },
  "dependencies": {
    "llama_local_client": "healthy",
    "log_service": "healthy",
    "regex_engine": "healthy",
    "pattern_loader": "healthy"
  }
}
```

### Primary Extraction Endpoints

#### POST `/api/v1/extract`
Main entity extraction endpoint supporting multiple processing modes.

**Request Parameters:**
```json
{
  "text": "string (required)",
  "document_id": "string (optional)",
  "extraction_mode": "traditional|ai_enhanced|hybrid|ai_discovered (default: hybrid)",
  "confidence_threshold": "float (0.0-1.0, default: 0.7)",
  "include_relationships": "boolean (default: true)",
  "include_citations": "boolean (default: true)",
  "jurisdiction_hint": "string (optional)",
  "document_type": "string (optional)",
  "enable_ai_enhancement": "boolean (default: true)",
  "max_entities": "integer (optional, default: 1000)"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8007/api/v1/extract" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court unanimously held that state laws establishing separate public schools for black and white students were unconstitutional. Chief Justice Warren delivered the opinion of the Court.",
    "document_id": "legal_doc_001",
    "extraction_mode": "hybrid",
    "confidence_threshold": 0.8,
    "jurisdiction_hint": "federal",
    "document_type": "case_law"
  }'
```

**Response:**
```json
{
  "document_id": "legal_doc_001",
  "extraction_mode": "hybrid",
  "processing_summary": {
    "total_entities_extracted": 4,
    "total_relationships_discovered": 2,
    "extraction_confidence_avg": 0.91,
    "processing_time_ms": 1250,
    "ai_enhancement_applied": true,
    "patterns_matched": 8
  },
  "entities": [
    {
      "id": "entity-123e4567-e89b-12d3-a456-426614174000",
      "text": "Brown v. Board of Education",
      "cleaned_text": "Brown v. Board of Education",
      "entity_type": "CASE_LAW",
      "entity_subtype": "supreme_court_case",
      "confidence_score": 0.95,
      "extraction_method": "regex_with_ai_validation",
      "position": {
        "start": 3,
        "end": 30,
        "line_number": 1
      },
      "attributes": {
        "court_name": "Supreme Court of the United States",
        "court_level": "supreme",
        "jurisdiction": "federal",
        "canonical_name": "Brown v. Board of Education of Topeka",
        "bluebook_abbreviation": "Brown"
      },
      "ai_enhancements": [
        "Standardized case name format",
        "Added canonical case name",
        "Verified court jurisdiction"
      ],
      "context_snippet": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court",
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": "entity-456e4567-e89b-12d3-a456-426614174001", 
      "text": "347 U.S. 483 (1954)",
      "cleaned_text": "347 U.S. 483 (1954)",
      "entity_type": "CASE_LAW",
      "entity_subtype": "supreme_court_citation",
      "confidence_score": 0.98,
      "extraction_method": "regex_with_ai_validation",
      "position": {
        "start": 32,
        "end": 51
      },
      "attributes": {
        "volume": "347",
        "reporter": "U.S.",
        "page": "483",
        "year": "1954",
        "bluebook_compliant": true,
        "authority_weight": 1.0
      },
      "ai_enhancements": [
        "Verified citation accuracy",
        "Added authority weight"
      ]
    },
    {
      "id": "entity-789e4567-e89b-12d3-a456-426614174002",
      "text": "Supreme Court",
      "cleaned_text": "Supreme Court of the United States", 
      "entity_type": "COURT",
      "entity_subtype": "federal_supreme",
      "confidence_score": 0.96,
      "extraction_method": "ai_discovered",
      "position": {
        "start": 57,
        "end": 70
      },
      "attributes": {
        "court_name": "Supreme Court of the United States",
        "court_level": "supreme", 
        "jurisdiction": "federal",
        "authority_level": 1
      }
    },
    {
      "id": "entity-012e4567-e89b-12d3-a456-426614174003",
      "text": "Chief Justice Warren",
      "cleaned_text": "Chief Justice Earl Warren",
      "entity_type": "JUDGE",
      "entity_subtype": "chief_justice",
      "confidence_score": 0.89,
      "extraction_method": "regex_with_ai_enhancement",
      "position": {
        "start": 195,
        "end": 215
      },
      "attributes": {
        "judge_title": "Chief Justice",
        "judge_name": "Earl Warren",
        "court_type": "supreme",
        "jurisdiction": "federal"
      },
      "ai_enhancements": [
        "Added full judge name",
        "Verified judicial title"
      ]
    }
  ],
  "relationships": [
    {
      "id": "rel-123e4567-e89b-12d3-a456-426614174000",
      "source_entity_id": "entity-012e4567-e89b-12d3-a456-426614174003",
      "target_entity_id": "entity-123e4567-e89b-12d3-a456-426614174000", 
      "relationship_type": "DECIDES",
      "confidence_score": 0.92,
      "evidence_text": "Chief Justice Warren delivered the opinion of the Court",
      "extraction_method": "ai_discovered",
      "relationship_attributes": {
        "authority_level": "binding",
        "procedural_stage": "decision"
      },
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": "rel-456e4567-e89b-12d3-a456-426614174001",
      "source_entity_id": "entity-789e4567-e89b-12d3-a456-426614174002",
      "target_entity_id": "entity-123e4567-e89b-12d3-a456-426614174000",
      "relationship_type": "HAS_JURISDICTION_OVER", 
      "confidence_score": 0.88,
      "evidence_text": "the Supreme Court unanimously held",
      "extraction_method": "ai_discovered",
      "relationship_attributes": {
        "jurisdiction_type": "federal",
        "authority_level": "supreme"
      }
    }
  ],
  "ai_metadata": {
    "enhancement_applied": true,
    "templates_used": ["entity_validation", "relationship_extraction"],
    "ai_processing_time_ms": 890,
    "entities_enhanced": 4,
    "relationships_discovered": 2,
    "confidence_improvements": 3,
    "bluebook_corrections": 1
  },
  "quality_metrics": {
    "overall_confidence": 0.91,
    "bluebook_compliance_rate": 0.75,
    "entity_completeness": 0.94,
    "relationship_coverage": 0.87
  }
}
```

#### POST `/api/v1/extract/batch`
Batch processing endpoint for multiple documents.

**Request Parameters:**
```json
{
  "documents": [
    {
      "document_id": "doc_001",
      "text": "Document text...",
      "metadata": {
        "jurisdiction": "federal",
        "document_type": "case_law"
      }
    }
  ],
  "extraction_mode": "hybrid",
  "confidence_threshold": 0.7,
  "processing_options": {
    "parallel_processing": true,
    "max_concurrent": 5,
    "enable_caching": true
  }
}
```

**Response:**
```json
{
  "batch_id": "batch-123e4567-e89b-12d3-a456-426614174000",
  "total_documents": 10,
  "processing_summary": {
    "successful": 9,
    "failed": 1,
    "total_processing_time_ms": 5240,
    "average_processing_time_ms": 524
  },
  "results": [
    {
      "document_id": "doc_001",
      "status": "success",
      "entities": [...],
      "relationships": [...],
      "processing_time_ms": 1250
    }
  ],
  "failed_documents": [
    {
      "document_id": "doc_010",
      "error": "Document too large",
      "error_code": "DOCUMENT_SIZE_EXCEEDED"
    }
  ]
}
```

### Specialized Endpoints

#### POST `/api/v1/extract/citations`
Extract only citation entities from text.

**Request:**
```json
{
  "text": "string (required)",
  "citation_types": ["CASE_CITATION", "STATUTE_CITATION"],
  "bluebook_validation": true,
  "include_parallel_citations": true
}
```

#### POST `/api/v1/extract/relationships`
Extract relationships between provided entities.

**Request:**
```json
{
  "text": "string (required)",
  "entities": [
    {
      "id": "entity-123",
      "text": "Brown v. Board",
      "entity_type": "CASE_LAW"
    }
  ],
  "relationship_types": ["CITES", "RELIES_ON", "OVERRULES"]
}
```

#### GET `/api/v1/patterns/jurisdictions`
List available jurisdictions and their pattern coverage.

**Response:**
```json
{
  "jurisdictions": [
    {
      "name": "federal",
      "patterns": 4,
      "coverage": ["supreme_court", "appellate_courts", "district_courts", "statutes", "regulations"]
    },
    {
      "name": "california", 
      "patterns": 1,
      "coverage": ["supreme_court", "appellate_courts", "superior_courts", "codes"]
    }
  ],
  "total_patterns": 53,
  "total_jurisdictions": 50
}
```

### Error Handling

The API uses standard HTTP status codes and provides detailed error responses:

#### Error Response Format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Specific field that caused the error",
      "value": "Invalid value"
    },
    "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

#### Common Error Codes:

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Malformed request body or parameters |
| 400 | `TEXT_TOO_LARGE` | Document text exceeds size limit |
| 400 | `INVALID_EXTRACTION_MODE` | Unknown extraction mode specified |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `EXTRACTION_FAILED` | Internal extraction error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

#### Example Error Response:
```json
{
  "error": {
    "code": "TEXT_TOO_LARGE",
    "message": "Document text exceeds maximum size limit of 100KB",
    "details": {
      "text_size": 150000,
      "max_size": 100000
    },
    "request_id": "req-456e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

---

## 6. Data Models

The Entity Extraction Service uses comprehensive Pydantic models to ensure type safety and data validation throughout the extraction pipeline.

### Core Entity Types

The service supports 20+ legal entity types with rich attribute modeling:

```python
class EntityType(str, Enum):
    """Legal entity types for classification."""
    COURT = "COURT"                                    # Courts at all levels
    JUDGE = "JUDGE"                                    # Judges and justices
    PARTY = "PARTY"                                    # Parties to legal proceedings
    ATTORNEY = "ATTORNEY"                              # Legal representatives
    DOCUMENT = "DOCUMENT"                              # Legal documents
    JURISDICTION = "JURISDICTION"                      # Geographic/subject matter jurisdiction
    LAW_FIRM = "LAW_FIRM"                             # Law firms and legal organizations
    GOVERNMENT_ENTITY = "GOVERNMENT_ENTITY"            # Government agencies and departments
    LEGAL_CONCEPT = "LEGAL_CONCEPT"                    # Legal concepts and doctrines
    STATUTE = "STATUTE"                                # Statutory provisions
    REGULATION = "REGULATION"                          # Administrative regulations
    CASE_LAW = "CASE_LAW"                             # Case law and precedents
    CONSTITUTIONAL_PROVISION = "CONSTITUTIONAL_PROVISION"  # Constitutional provisions
    LEGAL_STANDARD = "LEGAL_STANDARD"                  # Legal tests and standards
    PROCEDURAL_RULE = "PROCEDURAL_RULE"               # Court rules and procedures
    EVIDENCE_TYPE = "EVIDENCE_TYPE"                    # Types of evidence
    DAMAGES = "DAMAGES"                                # Monetary damages and relief
    RELIEF_REQUESTED = "RELIEF_REQUESTED"             # Relief sought in litigation
    LEGAL_DOCTRINE = "LEGAL_DOCTRINE"                  # Legal doctrines and principles
    PRECEDENT = "PRECEDENT"                           # Legal precedents
```

### Entity Model Structure

```python
class Entity(BaseModel):
    """Complete legal entity model with AI enhancements."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = Field(..., min_length=1, description="Original extracted text")
    cleaned_text: str = Field(..., description="AI-refined and cleaned text")
    entity_type: EntityType = Field(..., description="Primary entity classification")
    entity_subtype: str = Field(..., description="Detailed subclassification")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    extraction_method: ExtractionMethod = Field(...)
    position: TextPosition = Field(...)
    attributes: EntityAttributes = Field(default_factory=EntityAttributes)
    ai_enhancements: List[str] = Field(default_factory=list)
    context_snippet: Optional[str] = Field(None, max_length=1000)
    validation_notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Citation Models

```python
class CitationType(str, Enum):
    """Legal citation types for classification."""
    CASE_CITATION = "CASE_CITATION"                    # Case law citations
    STATUTE_CITATION = "STATUTE_CITATION"              # Statutory citations
    REGULATION_CITATION = "REGULATION_CITATION"        # Administrative regulations
    CONSTITUTIONAL_CITATION = "CONSTITUTIONAL_CITATION"  # Constitutional provisions
    LAW_REVIEW_CITATION = "LAW_REVIEW_CITATION"        # Academic articles
    BOOK_CITATION = "BOOK_CITATION"                    # Legal treatises and books
    COURT_RULE_CITATION = "COURT_RULE_CITATION"       # Court rules and procedures

class Citation(BaseModel):
    """Complete legal citation model with Bluebook compliance validation."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_text: str = Field(..., description="Original citation text")
    cleaned_citation: str = Field(..., description="Bluebook-compliant citation")
    citation_type: CitationType = Field(...)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    extraction_method: ExtractionMethod = Field(...)
    position: TextPosition = Field(...)
    components: CitationComponents = Field(default_factory=CitationComponents)
    bluebook_compliant: bool = Field(...)
    parallel_citations: List[str] = Field(default_factory=list)
    authority_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
```

---

## 7. Client Integration

### EntityExtractionClient

The service provides a comprehensive Python client library for seamless integration:

```python
from services.entity_extraction_service.src.client.entity_extraction_client import EntityExtractionClient

# Initialize client
client = EntityExtractionClient(
    base_url="http://localhost:8004",
    jwt_token="your_jwt_token",
    timeout=30.0
)

# Basic extraction
result = await client.extract_entities(
    text="Brown v. Board of Education, 347 U.S. 483 (1954)",
    extraction_mode="hybrid",
    confidence_threshold=0.8
)

# Batch processing
batch_result = await client.extract_batch(
    documents=[
        {"document_id": "doc_001", "text": "Document text..."},
        {"document_id": "doc_002", "text": "More text..."}
    ],
    extraction_mode="ai_enhanced"
)

# Health checking
health = await client.health_check()
```

### Integration Patterns

```python
# Document Service Integration Example
class DocumentProcessor:
    def __init__(self):
        self.entity_client = EntityExtractionClient()
    
    async def process_document(self, document_text: str) -> ProcessedDocument:
        # Extract entities
        extraction_result = await self.entity_client.extract_entities(
            text=document_text,
            extraction_mode="hybrid",
            include_relationships=True
        )
        
        # Process for GraphRAG pipeline
        entities = extraction_result.entities
        relationships = extraction_result.relationships
        
        return ProcessedDocument(
            entities=entities,
            relationships=relationships,
            processing_metadata=extraction_result.processing_summary
        )
```

---

## 8. Deployment Guide

### System Requirements

- **Python**: 3.9+
- **Memory**: 4GB minimum, 8GB recommended
- **CPU**: 4 cores minimum for optimal performance
- **Storage**: 2GB for patterns and models
- **Dependencies**: FastAPI, Pydantic, PyYAML, httpx

### Installation

```bash
# 1. Clone repository and navigate to service directory
cd services/entity-extraction-service

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export JWT_SECRET_KEY="your_jwt_secret"
export LOG_SERVICE_URL="http://localhost:8001"
export PROMPT_SERVICE_URL="http://localhost:8003"

# 5. Start service
python run.py
```

### Configuration Options

```yaml
# config/settings.yaml
service:
  name: "entity-extraction-service"
  version: "2.1.0"
  port: 8004
  log_level: "INFO"

patterns:
  base_path: "src/patterns"
  cache_enabled: true
  cache_size: 1000

ai_enhancement:
  enabled: true
  prompt_service_url: "http://localhost:8003"
  timeout_seconds: 30
  max_retries: 3

performance:
  max_concurrent_requests: 100
  request_timeout: 60
  batch_size_limit: 50
```

---

## 9. Performance & Quality

### Performance Benchmarks

| Metric | Value | Notes |
|--------|-------|-------|
| **Processing Speed** | 785-1200 cites/sec | Varies by pattern complexity |
| **Memory Usage** | <150MB | During large document processing |
| **Latency** | <2s average | For documents under 10KB |
| **Throughput** | 500 req/min | Per service instance |
| **Cache Hit Rate** | 67% | Pattern and AI response caching |

### Quality Metrics

```yaml
quality_standards:
  precision_targets:
    federal_supreme_court: 0.98
    federal_appellate: 0.96
    federal_district: 0.95
    state_courts: 0.94
    statutes: 0.96
    
  recall_targets:
    federal_supreme_court: 0.95
    federal_appellate: 0.93
    federal_district: 0.92
    state_courts: 0.91
    statutes: 0.94

  bluebook_compliance:
    citation_standardization: 0.96
    format_accuracy: 0.94
    parallel_citation_discovery: 0.31
```

---

## 10. Integration Examples

### Document Service Pipeline Integration

```python
# GraphRAG Pipeline Integration
class GraphRAGProcessor:
    async def process_legal_document(self, document: Document) -> GraphRAGResult:
        # Stage 1: Entity Extraction
        entities = await self.entity_client.extract_entities(
            text=document.content,
            extraction_mode="hybrid",
            document_type=document.type,
            jurisdiction_hint=document.jurisdiction
        )
        
        # Stage 2: Knowledge Graph Construction
        graph_nodes = self._create_graph_nodes(entities.entities)
        graph_edges = self._create_graph_edges(entities.relationships)
        
        return GraphRAGResult(
            nodes=graph_nodes,
            edges=graph_edges,
            extraction_metadata=entities.processing_summary
        )
```

### Batch Document Processing

```python
# High-volume document processing
async def process_document_batch(documents: List[str]) -> BatchResult:
    client = EntityExtractionClient()
    
    batch_request = {
        "documents": [
            {"document_id": f"doc_{i}", "text": doc}
            for i, doc in enumerate(documents)
        ],
        "extraction_mode": "ai_enhanced",
        "processing_options": {
            "parallel_processing": True,
            "max_concurrent": 10,
            "enable_caching": True
        }
    }
    
    result = await client.extract_batch(**batch_request)
    
    return BatchResult(
        total_processed=result.total_documents,
        success_rate=result.processing_summary.successful / result.total_documents,
        entities_extracted=sum(len(r.entities) for r in result.results),
        processing_time=result.processing_summary.total_processing_time_ms
    )
```

---

## 11. Appendices

### A. Complete Entity Type Reference

| Entity Type | Description | Example Subtypes |
|-------------|-------------|------------------|
| COURT | Legal courts at all levels | `federal_supreme`, `state_appellate`, `district_court` |
| JUDGE | Judges and judicial officers | `chief_justice`, `circuit_judge`, `magistrate_judge` |
| PARTY | Parties to legal proceedings | `plaintiff`, `defendant`, `appellant`, `intervenor` |
| ATTORNEY | Legal representatives | `lead_counsel`, `associate_attorney`, `pro_se` |
| CASE_LAW | Case law and precedents | `supreme_court_case`, `circuit_decision`, `trial_order` |
| STATUTE | Statutory provisions | `usc_section`, `state_statute`, `municipal_code` |
| REGULATION | Administrative regulations | `cfr_section`, `agency_rule`, `executive_order` |

### B. Pattern Coverage Summary

- **Total Pattern Files**: 53
- **Federal Jurisdictions**: 5 (Supreme Court, Circuit Courts, District Courts, USC, CFR)
- **State Jurisdictions**: 49 (All US states + Washington D.C.)
- **Total Patterns**: 2,847 individual regex patterns
- **Bluebook Compliance**: 22nd Edition standards

### C. Performance Optimization Guide

**Memory Management:**
- Pattern compilation caching reduces memory usage by 40%
- Entity deduplication prevents memory bloat
- Streaming processing for large documents

**Processing Speed:**
- Concurrent pattern matching across multiple threads
- AI request batching and caching
- Optimized regex compilation with lazy loading

### D. Troubleshooting Guide

**Common Issues:**

1. **Slow Processing**: Check AI enhancement settings, reduce confidence thresholds
2. **Low Accuracy**: Verify jurisdiction hints, check pattern file coverage
3. **Memory Issues**: Enable streaming mode, reduce batch sizes
4. **API Errors**: Verify JWT tokens, check service health endpoints

**Support Resources:**
- Service logs: `/logs/entity-extraction_service.log`
- Health endpoint: `GET /api/v1/health/detailed`
- Pattern validation: Built-in pattern testing framework
- Performance monitoring: Integrated metrics collection

---

**Document Version**: 2.1.0  
**Last Updated**: January 2025  
**Total Pages**: Comprehensive technical specification  
**Maintainer**: Legal Data Engineer Team

This technical specification serves as the definitive reference for the Entity Extraction Service, providing complete documentation for developers, integrators, and maintainers of this critical Luris component.
