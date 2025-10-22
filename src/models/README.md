# Entity Extraction Service - Pydantic Models

This directory contains comprehensive Pydantic models for the Entity Extraction Service, implementing the hybrid REGEX + AI workflow as specified in the technical specification.

## Model Files

### 1. `requests.py` - Request Models
- **`ExtractionRequest`**: Main request model for the `/extract` endpoint
  - Document ID validation and text content validation (max 10MB)
  - Metadata validation to prevent sensitive information leakage
  - Comprehensive field validation with detailed error messages

- **`ExtractionOptions`**: Configuration options for extraction processing
  - AI enhancement modes: `comprehensive`, `validation_only`, `correction_only`
  - Bluebook compliance levels: `strict`, `standard`, `relaxed`
  - Confidence thresholds, parallel citations, context analysis controls
  - Timeout and result limits configuration

### 2. `entities.py` - Core Entity and Citation Models

#### Enums
- **`EntityType`**: 21 legal entity types (COURT, JUDGE, PARTY, ATTORNEY, etc.)
- **`CitationType`**: 14 citation types (CASE_CITATION, STATUTE_CITATION, etc.)
- **`ExtractionMethod`**: 5 extraction methods for hybrid workflow tracking

#### Core Models
- **`Entity`**: Complete legal entity with AI enhancements
  - UUID generation, confidence scoring, position tracking
  - Flexible attributes system for different entity types
  - AI enhancement tracking and validation notes

- **`Citation`**: Legal citation with Bluebook compliance
  - Structured citation components (volume, reporter, page, etc.)
  - Parallel citation support and authority weight scoring
  - Comprehensive validation for legal citation formats

- **`EntityRelationship`**: Semantic relationships between entities
  - Bidirectional relationship support
  - Evidence text and confidence scoring
  - Relationship type classification and attributes

#### Supporting Models
- **`TextPosition`**: Precise position tracking in source documents
- **`EntityAttributes`**: Flexible type-specific attributes
- **`CitationComponents`**: Structured citation parsing components

### 3. `responses.py` - Response Models
- **`ExtractionResponse`**: Complete response for `/extract` endpoint
  - Processing summary with performance metrics
  - Comprehensive validation and helper methods
  - Statistics calculation and filtering capabilities
  - Request tracking and timestamp management

- **`ProcessingSummary`**: Pipeline performance metrics
  - Stage-by-stage timing breakdown
  - Confidence distribution analysis
  - AI enhancement tracking and pattern match counts
  - Bluebook compliance rate calculation

## Key Features

### Validation & Data Integrity
- Comprehensive field validation with meaningful error messages
- UUID validation for entity relationships
- Text content size limits and encoding validation
- Confidence score bounds checking (0.0 to 1.0)

### AI Enhancement Support
- Tracks AI enhancements applied to each item
- Supports multiple extraction methods in hybrid workflow
- Enhancement mode configuration for different processing levels
- AI discovery tracking separate from regex matches

### Bluebook Compliance
- Citation component parsing for legal standards
- Compliance validation and correction tracking
- Parallel citation support for cross-referencing
- Authority weight scoring for legal precedence

### Performance Monitoring
- Processing time tracking by stage
- Confidence distribution analysis
- Enhancement effectiveness metrics
- Pattern matching success rates

### Flexibility & Extensibility
- Flexible attribute systems for different entity types
- Extensible relationship types and attributes
- Configurable confidence thresholds
- Metadata support for additional context

## Usage Examples

### Basic Request Creation
```python
from models import ExtractionRequest, ExtractionOptions

request = ExtractionRequest(
    document_id="case_001",
    text="Brown v. Board, 347 U.S. 483 (1954)",
    options=ExtractionOptions(
        ai_enhancement_mode="comprehensive",
        confidence_threshold=0.7
    )
)
```

### Entity Creation with AI Enhancement
```python
from models import Entity, EntityType, ExtractionMethod, TextPosition

entity = Entity(
    text="Supreme Court",
    cleaned_text="Supreme Court of the United States",
    entity_type=EntityType.COURT,
    entity_subtype="federal_supreme",
    confidence_score=0.95,
    extraction_method=ExtractionMethod.REGEX_WITH_AI_ENHANCEMENT,
    position=TextPosition(start=10, end=23),
    ai_enhancements=["standardized_name", "jurisdiction_added"]
)
```

### Complete Response with Statistics
```python
from models import ExtractionResponse

response = ExtractionResponse(
    document_id="case_001",
    processing_summary=summary,
    entities=entities,
    citations=citations,
    relationships=relationships
)

# Get statistics
stats = response.calculate_statistics()
high_confidence = response.get_high_confidence_items(0.9)
ai_enhanced = response.get_ai_enhanced_items()
```

## Validation Features

All models include comprehensive validation:
- **Request Validation**: Document ID format, text size limits, metadata security
- **Position Validation**: Start/end position consistency, context window validation
- **Confidence Validation**: Score bounds and distribution tracking
- **Relationship Validation**: Entity ID format and self-reference prevention
- **Count Validation**: Response counts match processing summary

## Integration Ready

These models are designed to integrate seamlessly with:
- FastAPI route handlers for the `/extract` endpoint
- Hybrid REGEX + AI extraction workflows
- PromptClient for AI enhancement processing
- LogClient for comprehensive logging and monitoring
- Database storage via SupabaseClient

The models support the full specification requirements including confidence scoring, AI enhancement tracking, Bluebook compliance validation, and comprehensive performance monitoring.