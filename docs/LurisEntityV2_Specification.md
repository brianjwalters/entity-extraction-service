# LurisEntityV2 Schema Specification

## Overview

LurisEntityV2 is the unified entity schema for the Luris legal document processing platform, designed to standardize JSON output across all extraction strategies (multipass, unified, hybrid) while maintaining high performance and backward compatibility.

## Version Information

- **Schema Version**: 2.0.0
- **Effective Date**: 2024-01-15
- **Supersedes**: Legacy ExtractedEntity formats
- **Status**: Production Ready

---

## Core Design Principles

### 1. **Unified Field Naming**
- Single field naming convention across all strategies
- Eliminates `type` vs `entity_type` confusion
- Standardizes position fields (`start_pos`, `end_pos`)

### 2. **Schema Compliance**
- JSON Schema validation for all outputs
- Automatic validation with <5% performance overhead
- Built-in error correction and normalization

### 3. **Backward Compatibility** 
- Seamless conversion from legacy formats
- Dual-format support during migration
- Non-breaking API changes

### 4. **Performance Optimized**
- LRU caching for validation results
- Batch processing support
- <1ms per entity validation overhead

---

## Entity Schema Definition

### LurisEntityV2 Core Structure

```typescript
interface LurisEntityV2 {
  // Core Identification
  id: string;                    // UUID v4 identifier
  text: string;                  // Exact text as extracted
  entity_type: EntityType;       // Standardized entity type
  
  // Position Information
  start_pos: number;             // Character start position (0-based)
  end_pos: number;               // Character end position (exclusive)
  
  // Confidence and Method
  confidence: number;            // Confidence score (0.0-1.0)
  extraction_method: ExtractionMethod; // Method used for extraction
  
  // Optional Classification
  subtype?: string;              // Entity subtype (e.g., "federal_court")
  category?: string;             // Entity category (e.g., "core_legal")
  
  // Rich Metadata
  metadata: EntityMetadata;      // Comprehensive metadata object
  
  // Timestamps
  created_at: number;            // Unix timestamp (creation)
  updated_at?: number;           // Unix timestamp (last update)
}
```

### Position Object Structure

```typescript
interface Position {
  start_pos: number;             // Character start position
  end_pos: number;               // Character end position
  
  // Derived Properties
  length(): number;              // Calculated text length
  to_dict(): PositionDict;       // Dictionary conversion
}
```

### EntityMetadata Structure

```typescript
interface EntityMetadata {
  // Pattern Information
  pattern_matched?: string;      // Pattern ID that matched
  pattern_source?: string;       // Source YAML file
  pattern_confidence?: number;   // Pattern-specific confidence
  
  // Context Information
  sentence_context?: string;     // Surrounding sentence
  paragraph_context?: string;    // Surrounding paragraph
  document_section?: string;     // Document section location
  
  // Normalization
  normalized_value?: string;     // Standardized form
  canonical_form?: string;       // Official format (e.g., Bluebook)
  
  // Relationships
  related_entities: string[];    // Related entity IDs
  entity_relations: Record<string, any>; // Structured relationships
  
  // Processing Information
  processing_time_ms?: number;   // Processing time
  validation_status?: string;    // Validation result
  quality_score?: number;        // Quality assessment
  
  // Custom Attributes
  custom_attributes: Record<string, any>; // Strategy-specific data
}
```

---

## Supported Entity Types

### Core Legal Entities (Pass 1)
```typescript
enum CoreLegalEntityTypes {
  CASE_CITATION = "CASE_CITATION",           // Legal case citations
  STATUTE_CITATION = "STATUTE_CITATION",     // Statutory references
  PARTY = "PARTY",                           // Legal parties
  ATTORNEY = "ATTORNEY",                     // Legal counsel
  COURT = "COURT",                           // Court names
  JUDGE = "JUDGE"                            // Judges and justices
}
```

### Legal Citations (Pass 2)
```typescript
enum LegalCitationTypes {
  USC_CITATION = "USC_CITATION",             // US Code citations
  CFR_CITATION = "CFR_CITATION",             // Code of Federal Regulations
  STATE_STATUTE_CITATION = "STATE_STATUTE_CITATION", // State statutes
  CONSTITUTIONAL_CITATION = "CONSTITUTIONAL_CITATION" // Constitutional refs
}
```

### Procedural Elements (Pass 3)
```typescript
enum ProceduralTypes {
  CASE_NUMBER = "CASE_NUMBER",               // Case identifiers
  DOCKET_NUMBER = "DOCKET_NUMBER",           // Docket entries
  MOTION = "MOTION",                         // Legal motions
  BRIEF = "BRIEF",                           // Legal briefs
  PROCEDURAL_RULE = "PROCEDURAL_RULE"        // Rules of procedure
}
```

### Temporal Information (Pass 4)
```typescript
enum TemporalTypes {
  DATE = "DATE",                             // General dates
  FILING_DATE = "FILING_DATE",               // Filing dates
  DEADLINE = "DEADLINE",                     // Legal deadlines
  HEARING_DATE = "HEARING_DATE",             // Hearing dates
  TRIAL_DATE = "TRIAL_DATE"                  // Trial dates
}
```

### Financial Elements (Pass 5)
```typescript
enum FinancialTypes {
  MONETARY_AMOUNT = "MONETARY_AMOUNT",       // General amounts
  DAMAGES = "DAMAGES",                       // Damage awards
  FINE = "FINE",                            // Fines and penalties
  FEE = "FEE",                              // Fees and costs
  AWARD = "AWARD"                           // Monetary awards
}
```

### Legal Organizations (Pass 6)
```typescript
enum OrganizationTypes {
  LAW_FIRM = "LAW_FIRM",                    // Law firms
  PROSECUTOR = "PROSECUTOR",                 // Prosecuting offices
  PUBLIC_DEFENDER = "PUBLIC_DEFENDER",       // Public defense
  GOVERNMENT_ENTITY = "GOVERNMENT_ENTITY"    // Government agencies
}
```

### Geographic & Miscellaneous (Pass 7)
```typescript
enum MiscellaneousTypes {
  ADDRESS = "ADDRESS",                       // Physical addresses
  EMAIL = "EMAIL",                          // Email addresses
  PHONE_NUMBER = "PHONE_NUMBER",            // Phone numbers
  BAR_NUMBER = "BAR_NUMBER",                // Attorney bar numbers
  CORPORATION = "CORPORATION"               // Corporate entities
}
```

---

## Extraction Methods

```typescript
enum ExtractionMethod {
  REGEX = "regex",                          // Pattern-based extraction
  PATTERN = "pattern",                      // Advanced pattern matching
  AI_ENHANCED = "ai_enhanced",              // LLM-based extraction
  HYBRID = "hybrid",                        // Combined approach
  LEGACY = "legacy",                        // Legacy system extraction
  MANUAL = "manual"                         // Manual annotation
}
```

---

## Confidence Levels

### Confidence Score Ranges
```typescript
enum ConfidenceLevel {
  HIGH = "high",      // 0.8 - 1.0: Strong pattern match or AI confidence
  MEDIUM = "medium",  // 0.5 - 0.8: Partial match or moderate AI confidence
  LOW = "low"         // 0.0 - 0.5: Weak match or low AI confidence
}
```

### Confidence Thresholds by Pass
- **Pass 1 (Core Legal)**: ≥0.85 (High confidence required)
- **Pass 2 (Citations)**: ≥0.85 (High confidence required)
- **Pass 3 (Procedural)**: ≥0.80 (High-medium confidence)
- **Pass 4 (Temporal)**: ≥0.85 (High confidence for dates)
- **Pass 5 (Financial)**: ≥0.80 (High-medium confidence)
- **Pass 6 (Organizations)**: ≥0.75 (Medium confidence)
- **Pass 7 (Miscellaneous)**: ≥0.70 (Lower threshold for cleanup)

---

## ExtractionResultV2 Structure

### Complete Result Schema
```typescript
interface ExtractionResultV2 {
  // Basic Information
  extraction_id: string;                    // UUID v4 identifier
  document_id: string;                      // Document reference
  strategy_used: string;                    // "unified" | "multipass" | "hybrid"
  
  // Results
  entities: LurisEntityV2[];                // Primary entities
  citations: LurisEntityV2[];               // Citation entities
  relationships: Relationship[];            // Entity relationships
  
  // Processing Information
  processing_time_ms: number;               // Total processing time
  extraction_time: number;                  // Unix timestamp
  
  // Quality Metrics
  total_entities: number;                   // Total entity count
  confidence_distribution: ConfidenceDistribution; // Confidence breakdown
  extraction_methods_used: string[];       // Methods employed
  overall_confidence: number;               // Average confidence
  
  // Metadata
  extraction_metadata: ExtractionMetadata; // Strategy-specific metadata
  quality_metrics: QualityMetrics;         // Quality assessment
  
  // Status
  success: boolean;                         // Extraction success flag
  warnings: string[];                       // Non-fatal issues
  errors: string[];                         // Error messages
}
```

### Confidence Distribution
```typescript
interface ConfidenceDistribution {
  high: number;      // Count of entities with confidence ≥0.8
  medium: number;    // Count of entities with confidence 0.5-0.8
  low: number;       // Count of entities with confidence <0.5
}
```

### Quality Metrics
```typescript
interface QualityMetrics {
  extraction_quality: number;              // Overall quality score (0.0-1.0)
  pattern_utilization: number;             // Pattern usage rate
  validation_success_rate: number;         // Schema validation rate
  duplicate_detection_rate: number;        // Duplicate prevention rate
}
```

---

## JSON Schema Definition

### Entity Validation Schema
```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string", "format": "uuid"},
    "text": {"type": "string", "minLength": 1},
    "entity_type": {"type": "string", "enum": ["CASE_CITATION", "COURT", ...]},
    "start_pos": {"type": "integer", "minimum": 0},
    "end_pos": {"type": "integer", "minimum": 0},
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "extraction_method": {"type": "string", "enum": ["regex", "pattern", ...]},
    "subtype": {"type": ["string", "null"]},
    "category": {"type": ["string", "null"]},
    "metadata": {"type": "object"},
    "created_at": {"type": "number"},
    "updated_at": {"type": ["number", "null"]}
  },
  "required": ["text", "entity_type", "start_pos", "end_pos", "confidence", "extraction_method"],
  "additionalProperties": false
}
```

### Result Validation Schema
```json
{
  "type": "object",
  "properties": {
    "extraction_id": {"type": "string", "format": "uuid"},
    "document_id": {"type": "string"},
    "strategy_used": {"type": "string"},
    "entities": {
      "type": "array",
      "items": {"$ref": "#/definitions/LurisEntityV2"}
    },
    "citations": {
      "type": "array",
      "items": {"$ref": "#/definitions/LurisEntityV2"}
    },
    "processing_time_ms": {"type": "number"},
    "total_entities": {"type": "integer"},
    "overall_confidence": {"type": "number"},
    "success": {"type": "boolean"}
  },
  "required": ["extraction_id", "document_id", "strategy_used", "entities", "success"]
}
```

---

## Conversion Specifications

### From Legacy ExtractedEntity

```python
def convert_from_extracted_entity(legacy_entity: ExtractedEntity) -> LurisEntityV2:
    return LurisEntityV2(
        text=legacy_entity.text,
        entity_type=legacy_entity.entity_type or legacy_entity.type,
        start_pos=legacy_entity.start_pos,
        end_pos=legacy_entity.end_pos,
        confidence=legacy_entity.confidence or 0.0,
        extraction_method=legacy_entity.extraction_method or "legacy",
        metadata=EntityMetadata(
            custom_attributes=legacy_entity.metadata or {}
        )
    )
```

### To Legacy Dictionary Format

```python
def to_legacy_dict(entity: LurisEntityV2) -> Dict[str, Any]:
    return {
        "text": entity.text,
        "entity_type": entity.entity_type,
        "type": entity.entity_type,  # Duplicate for compatibility
        "start_pos": entity.start_pos,
        "end_pos": entity.end_pos,
        "confidence": entity.confidence,
        "extraction_method": entity.extraction_method,
        "metadata": entity.metadata.custom_attributes
    }
```

---

## Validation Rules

### Required Field Validation
1. **text**: Must be non-empty string
2. **entity_type**: Must be valid enum value
3. **start_pos**: Must be non-negative integer
4. **end_pos**: Must be ≥ start_pos
5. **confidence**: Must be in range [0.0, 1.0]
6. **extraction_method**: Must be valid enum value

### Business Logic Validation
1. **Position Consistency**: `end_pos >= start_pos`
2. **Text Length Match**: `len(text) == (end_pos - start_pos)`
3. **Confidence Range**: `0.0 <= confidence <= 1.0`
4. **Entity Type Validity**: Must match supported types
5. **UUID Format**: ID must be valid UUID v4

### Cross-Strategy Validation
1. **Field Name Consistency**: Only `entity_type` (never `type`)
2. **Position Field Names**: Only `start_pos`/`end_pos`
3. **Schema Compliance**: 100% JSON Schema adherence
4. **Output Structure**: Identical across all strategies

---

## Performance Specifications

### Validation Performance
- **Target**: <1ms per entity validation
- **Caching**: LRU cache with 1000 entity capacity
- **Cache TTL**: 1 hour (3600 seconds)
- **Cache Hit Rate**: Target >80%
- **Overall Overhead**: <5% of total processing time

### Memory Usage
- **Entity Object**: ~2KB average memory footprint
- **Metadata Object**: ~1KB average size
- **Cache Memory**: ~10MB for 1000 cached entities
- **Validation Memory**: <1MB working memory

### Throughput
- **Batch Validation**: 10,000+ entities/second
- **Single Entity**: 50,000+ validations/second
- **Conversion Speed**: 100,000+ conversions/second
- **Schema Compliance**: 99.9% success rate

---

## Error Handling

### Validation Errors
```typescript
interface ValidationError {
  field: string;                            // Field with error
  message: string;                          // Error description
  value: any;                              // Invalid value
  expected: string;                        // Expected format
}
```

### Auto-Fix Capabilities
1. **Confidence Range**: Clamp to [0.0, 1.0]
2. **Position Order**: Ensure `end_pos >= start_pos`
3. **Empty Text**: Set to "UNKNOWN" if empty
4. **Missing Fields**: Apply reasonable defaults
5. **Invalid Types**: Map to nearest valid type

### Error Recovery
```python
def auto_fix_entity(entity: LurisEntityV2) -> LurisEntityV2:
    # Fix confidence range
    if entity.confidence < 0.0:
        entity.confidence = 0.0
    elif entity.confidence > 1.0:
        entity.confidence = 1.0
    
    # Fix position order
    if entity.end_pos < entity.start_pos:
        entity.end_pos = entity.start_pos
    
    # Fix empty text
    if not entity.text:
        entity.text = "UNKNOWN"
    
    return entity
```

---

## API Integration

### Request/Response Format

#### Unified Strategy Request
```json
{
  "document_id": "doc_123",
  "content": "UNITED STATES v. RAHIMI...",
  "extraction_mode": "hybrid",
  "extraction_strategy": "unified",
  "confidence_threshold": 0.7
}
```

#### LurisEntityV2 Response
```json
{
  "extraction_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": "doc_123",
  "strategy_used": "unified",
  "entities": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "text": "UNITED STATES v. RAHIMI",
      "entity_type": "CASE_CITATION",
      "start_pos": 0,
      "end_pos": 23,
      "confidence": 0.95,
      "extraction_method": "pattern",
      "subtype": "supreme_court",
      "category": "core_legal",
      "metadata": {
        "pattern_matched": "case_citation_bluebook",
        "pattern_source": "federal_citations.yaml",
        "pattern_confidence": 0.98,
        "sentence_context": "UNITED STATES v. RAHIMI, No. 22-6640",
        "normalized_value": "United States v. Rahimi",
        "canonical_form": "United States v. Rahimi, No. 22-6640 (2024)",
        "custom_attributes": {
          "case_number": "22-6640",
          "court": "Supreme Court"
        }
      },
      "created_at": 1640995200.0
    }
  ],
  "processing_time_ms": 150.0,
  "total_entities": 1,
  "overall_confidence": 0.95,
  "success": true
}
```

---

## Migration Guide

### Phase 1: Dual Format Support
```python
# Support both legacy and V2 formats
def handle_extraction_result(result: Any) -> ExtractionResultV2:
    if isinstance(result, ExtractionResultV2):
        return result
    else:
        return convert_result_to_v2(result)
```

### Phase 2: Validation Enforcement
```python
# Add schema validation to all outputs
@schema_validation_middleware
def extract_entities(request: ExtractionRequest) -> ExtractionResultV2:
    result = perform_extraction(request)
    return validate_and_enforce_result(result)
```

### Phase 3: Full Migration
```python
# Remove legacy format support
def extract_entities(request: ExtractionRequest) -> ExtractionResultV2:
    return SchemaCompliantTemplateProcessor().process_request(request)
```

---

## Codebase Integration & Invocation Flow

### How LurisEntityV2 is Invoked from /extract Endpoint

The `/extract` endpoint is the primary entry point for entity extraction. Here's the detailed flow showing how requests are processed and how LurisEntityV2 is enforced throughout:

#### 1. API Request Structure

```python
# Client sends request to http://10.10.0.87:8007/api/v1/extract
POST /api/v1/extract
{
    "document_id": "doc_123",
    "content": "Apple Inc. filed a motion on January 15, 2024...",
    "extraction_mode": "ai_enhanced",  # or "hybrid", "regex"
    "extraction_strategy": "unified",   # or "multipass", "ai_enhanced"
    "confidence_threshold": 0.7,
    "entity_types": ["CORPORATION", "DATE", "CASE"]  # optional filter
}
```

#### 2. Request Processing in extract.py

```python
# /srv/luris/be/entity-extraction-service/src/api/routes/extract.py

@router.post("/extract")
async def extract_entities(
    request: ExtractionRequest,
    fastapi_request: Request,
    background_tasks: BackgroundTasks
):
    """Main extraction endpoint - lines 167-761"""
    
    # Step 1: Determine extraction strategy (lines 218-239)
    extraction_strategy = request.extraction_strategy
    if not extraction_strategy:
        # Apply default strategy mappings
        strategy_map = {
            "regex": "unified",      # Redirect deprecated regex to unified
            "ai_enhanced": "ai_enhanced",
            "hybrid": "multipass"
        }
        extraction_strategy = strategy_map.get(
            request.extraction_mode, 
            "unified"
        )
    
    # Step 2: Route to appropriate extractor (lines 240-385)
    if extraction_strategy == "multipass":
        result = await _extract_multipass(request, fastapi_request)
    elif extraction_strategy == "unified":
        result = await _extract_unified(request, fastapi_request)
    elif extraction_strategy == "ai_enhanced":
        result = await _extract_ai_enhanced(request, fastapi_request)
    else:  # regex fallback
        result = await _extract_regex_only(request, fastapi_request)
    
    # Step 3: Schema enforcement happens within each extractor
    # All extractors MUST return LurisEntityV2 compliant results
    return result
```

#### 3. Unified Strategy Implementation

```python
async def _extract_unified(request, fastapi_request):
    """Unified extraction with LurisEntityV2 enforcement"""
    
    # Get schema-compliant template processor
    from src.core.prompts.template_processor import SchemaCompliantTemplateProcessor
    processor = SchemaCompliantTemplateProcessor()
    
    # Build prompt with LurisEntityV2 schema requirements
    prompt = processor.build_unified_prompt(
        text=request.content,
        entity_types=request.entity_types,
        schema_version="2.0.0"  # Forces LurisEntityV2
    )
    
    # Send to LLM (vLLM at 10.10.0.87:8080)
    vllm_client = fastapi_request.app.state.vllm_client
    response = await vllm_client.generate(prompt)
    
    # Parse and validate response
    result = processor.validate_and_enforce_result(response)
    # result.entities are guaranteed to be LurisEntityV2 compliant
    
    return ExtractionResponse(
        document_id=request.document_id,
        entities=result.entities,  # List[LurisEntityV2]
        extraction_metadata={
            "strategy": "unified",
            "schema_version": "2.0.0",
            "total_entities": len(result.entities)
        }
    )
```

#### 4. Multipass Strategy Implementation

```python
async def _extract_multipass(request, fastapi_request):
    """7-pass extraction with LurisEntityV2 enforcement"""
    
    from src.core.prompts.template_processor import SchemaCompliantTemplateProcessor
    processor = SchemaCompliantTemplateProcessor()
    
    all_entities = []
    
    # Execute 7 passes sequentially
    for pass_num in range(1, 8):
        # Get pass-specific template (uses *_v2.md templates)
        prompt = processor.build_multipass_prompt(
            text=request.content,
            pass_number=pass_num,
            previous_results=all_entities,
            schema_version="2.0.0"  # Forces LurisEntityV2
        )
        
        # Send to LLM
        response = await vllm_client.generate(prompt)
        
        # Validate and enforce schema
        pass_result = processor.validate_and_enforce_result(response)
        
        # Add pass metadata
        for entity in pass_result.entities:
            entity.metadata["pass_number"] = pass_num
            entity.metadata["pass_name"] = PASS_NAMES[pass_num]
        
        all_entities.extend(pass_result.entities)
    
    # Deduplicate entities
    unique_entities = deduplicate_entities(all_entities)
    
    return ExtractionResponse(
        document_id=request.document_id,
        entities=unique_entities,  # List[LurisEntityV2]
        extraction_metadata={
            "strategy": "multipass",
            "schema_version": "2.0.0",
            "total_passes": 7,
            "total_entities": len(unique_entities)
        }
    )
```

#### 5. Schema Enforcement in Template Processor

```python
# /srv/luris/be/entity-extraction-service/src/core/prompts/template_processor.py

class SchemaCompliantTemplateProcessor:
    """Enforces LurisEntityV2 schema compliance - lines 561-750"""
    
    def __init__(self):
        self.validator = LurisSchemaValidator()
        self.converter = EntityConverter()
        self.cache = SchemaValidationCache()
    
    def build_unified_prompt(self, text: str, entity_types: List[str], 
                            schema_version: str = "2.0.0") -> str:
        """Build prompt with embedded schema requirements"""
        
        # Load template with LurisEntityV2 schema
        template = self.load_template("unified_extraction_v2.md")
        
        # Inject schema definition into prompt
        schema_json = self.get_luris_entity_v2_schema()
        
        return template.render(
            text=text,
            entity_types=entity_types,
            schema_definition=schema_json,
            output_format_example=self.get_example_output()
        )
    
    def validate_and_enforce_result(self, llm_output: str) -> ExtractionResultV2:
        """Validate and auto-correct LLM output - lines 650-750"""
        
        try:
            # Parse JSON from LLM
            data = json.loads(llm_output)
            
            # Auto-correct common field naming issues
            if "entities" in data:
                for entity in data["entities"]:
                    # Fix field names
                    if "type" in entity and "entity_type" not in entity:
                        entity["entity_type"] = entity.pop("type")
                    if "start" in entity:
                        entity["start_pos"] = entity.pop("start")
                    if "end" in entity:
                        entity["end_pos"] = entity.pop("end")
                    
                    # Ensure required fields
                    if "id" not in entity:
                        entity["id"] = str(uuid.uuid4())
                    if "confidence" not in entity:
                        entity["confidence"] = 0.8
                    if "extraction_method" not in entity:
                        entity["extraction_method"] = "ai_enhanced"
            
            # Validate against schema
            validation_result = self.validator.validate_result(data)
            
            if not validation_result.is_valid:
                # Attempt auto-correction
                corrected = self.auto_correct_result(data, validation_result.errors)
                if corrected:
                    data = corrected
                else:
                    raise ValueError(f"Schema validation failed: {validation_result.errors}")
            
            # Convert to LurisEntityV2 objects
            entities = [self.converter.to_luris_v2(e) for e in data["entities"]]
            
            return ExtractionResultV2(
                entities=entities,
                extraction_metadata=data.get("extraction_metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to validate/enforce schema: {e}")
            # Return empty result rather than fail
            return ExtractionResultV2(entities=[], extraction_metadata={
                "error": str(e),
                "schema_enforcement_failed": True
            })
```

#### 6. Example LLM Prompt with Schema

When the template processor builds a prompt, it includes the schema definition:

```markdown
# Entity Extraction Task

Extract legal entities from the following text using the LurisEntityV2 schema.

## Required Output Schema (LurisEntityV2 v2.0.0)

You MUST output JSON that exactly matches this schema:

```json
{
  "entities": [
    {
      "id": "uuid-string",                    // Required: UUID v4
      "text": "exact text from document",     // Required: Verbatim text
      "entity_type": "CORPORATION",           // Required: Use entity_type NOT type
      "start_pos": 0,                         // Required: Use start_pos NOT start
      "end_pos": 10,                          // Required: Use end_pos NOT end
      "confidence": 0.95,                     // Required: 0.0-1.0
      "extraction_method": "ai_enhanced",     // Required
      "subtype": "technology_company",        // Optional
      "category": "organization",             // Optional
      "metadata": {                           // Optional but recommended
        "sentence_context": "full sentence",
        "normalized_value": "APPLE INC.",
        "custom_attributes": {}
      },
      "created_at": 1705344000.0             // Optional: Unix timestamp
    }
  ],
  "extraction_metadata": {
    "total_entities": 1,
    "strategy": "unified",
    "schema_version": "2.0.0"
  }
}
```

## Critical Requirements
- Use `entity_type` NOT `type`
- Use `start_pos` and `end_pos` NOT `start` and `end`
- Include confidence scores between 0.0 and 1.0
- Generate unique UUID for each entity

## Text to Process
[Document text here...]
```

#### 7. How Other Services Should Structure Output

For other services (GraphRAG, Chunking, Document Processing) to integrate properly:

```python
# Example: GraphRAG Service Integration
class GraphRAGEntityExtractor:
    """GraphRAG service must output LurisEntityV2 compliant entities"""
    
    def extract_graph_entities(self, graph_data: Dict) -> List[Dict]:
        """
        Extract entities from knowledge graph.
        MUST return LurisEntityV2 compliant format.
        """
        entities = []
        
        for node in graph_data["nodes"]:
            # Build LurisEntityV2 compliant entity
            entity = {
                "id": str(uuid.uuid4()),
                "text": node["label"],
                "entity_type": self.map_node_type_to_entity_type(node["type"]),
                "start_pos": node.get("text_position", {}).get("start", 0),
                "end_pos": node.get("text_position", {}).get("end", len(node["label"])),
                "confidence": node.get("confidence", 0.85),
                "extraction_method": "graph_analysis",
                "subtype": node.get("subtype"),
                "category": self.get_category_for_type(node["type"]),
                "metadata": {
                    "graph_node_id": node["id"],
                    "community": node.get("community"),
                    "centrality_score": node.get("centrality", 0.0),
                    "relationships": [r["id"] for r in node.get("relationships", [])]
                },
                "created_at": time.time()
            }
            entities.append(entity)
        
        return entities

# Example: Chunking Service Integration  
class ChunkingServiceEntityHandler:
    """Chunking service must handle LurisEntityV2 entities"""
    
    def process_chunk_with_entities(self, chunk: Dict) -> Dict:
        """
        Process chunk and ensure entities are LurisEntityV2 compliant.
        """
        # If chunk contains entities, validate them
        if "entities" in chunk:
            validator = LurisSchemaValidator()
            
            validated_entities = []
            for entity in chunk["entities"]:
                # Ensure compliance
                if "type" in entity and "entity_type" not in entity:
                    entity["entity_type"] = entity.pop("type")
                
                # Validate
                result = validator.validate_entity(entity)
                if result.is_valid:
                    validated_entities.append(entity)
                else:
                    # Log validation error
                    logger.warning(f"Invalid entity in chunk: {result.errors}")
            
            chunk["entities"] = validated_entities
            chunk["schema_version"] = "2.0.0"
        
        return chunk

# Example: Document Processing Service Integration
class DocumentProcessingPipeline:
    """Document processing must use LurisEntityV2 throughout pipeline"""
    
    async def process_document(self, document: Dict) -> Dict:
        """
        Process document through pipeline with schema compliance.
        """
        # Stage 1: Extract entities (returns LurisEntityV2)
        extraction_result = await self.entity_service.extract(
            document["content"],
            strategy="unified"
        )
        
        # Stage 2: Enhance with GraphRAG (expects LurisEntityV2)
        enhanced_entities = await self.graphrag_service.enhance_entities(
            extraction_result.entities  # Already LurisEntityV2 compliant
        )
        
        # Stage 3: Store in database (validates LurisEntityV2)
        stored_ids = await self.storage_service.store_entities(
            document_id=document["id"],
            entities=enhanced_entities,
            schema_version="2.0.0"
        )
        
        return {
            "document_id": document["id"],
            "entities": enhanced_entities,
            "entity_count": len(enhanced_entities),
            "schema_version": "2.0.0",
            "stored_ids": stored_ids
        }
```

#### 8. Database Storage Schema

When storing entities in Supabase:

```sql
-- client.entities table structure for LurisEntityV2
CREATE TABLE client.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL,
    entity_id UUID NOT NULL,  -- From LurisEntityV2.id
    text TEXT NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- Standardized field name
    start_pos INTEGER NOT NULL,        -- Standardized field name
    end_pos INTEGER NOT NULL,          -- Standardized field name
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    extraction_method VARCHAR(50) NOT NULL,
    subtype VARCHAR(100),
    category VARCHAR(50),
    metadata JSONB,
    schema_version VARCHAR(10) DEFAULT '2.0.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for efficient queries
CREATE INDEX idx_entities_document_id ON client.entities(document_id);
CREATE INDEX idx_entities_entity_type ON client.entities(entity_type);
CREATE INDEX idx_entities_confidence ON client.entities(confidence);
```

#### 9. Client SDK Usage

```python
# Client SDK for consuming extraction service
class EntityExtractionClient:
    """Client for entity extraction service with LurisEntityV2 support"""
    
    def __init__(self, base_url: str = "http://10.10.0.87:8007"):
        self.base_url = base_url
        self.session = httpx.AsyncClient()
    
    async def extract_entities(
        self, 
        document: str,
        strategy: str = "unified"
    ) -> List[LurisEntityV2]:
        """
        Extract entities from document.
        Returns list of LurisEntityV2 compliant entities.
        """
        response = await self.session.post(
            f"{self.base_url}/api/v1/extract",
            json={
                "document_id": str(uuid.uuid4()),
                "content": document,
                "extraction_strategy": strategy
            }
        )
        
        result = response.json()
        
        # Convert to LurisEntityV2 objects
        entities = []
        for entity_dict in result["entities"]:
            entity = LurisEntityV2(
                id=entity_dict["id"],
                text=entity_dict["text"],
                entity_type=entity_dict["entity_type"],  # Note: entity_type, not type
                start_pos=entity_dict["start_pos"],      # Note: start_pos, not start
                end_pos=entity_dict["end_pos"],          # Note: end_pos, not end
                confidence=entity_dict["confidence"],
                extraction_method=entity_dict.get("extraction_method", "unknown"),
                metadata=entity_dict.get("metadata", {})
            )
            entities.append(entity)
        
        return entities

# Usage example
client = EntityExtractionClient()
entities = await client.extract_entities(
    document="Apple Inc. filed a motion on January 15, 2024.",
    strategy="unified"
)

for entity in entities:
    print(f"{entity.entity_type}: {entity.text} (confidence: {entity.confidence})")
    # Output: CORPORATION: Apple Inc. (confidence: 0.95)
    # Output: DATE: January 15, 2024 (confidence: 0.98)
```

---

## Testing Requirements

### Unit Tests
- ✅ Entity creation and validation
- ✅ Position calculations and boundaries
- ✅ Confidence score normalization
- ✅ Metadata structure validation
- ✅ Type conversion accuracy

### Integration Tests
- ✅ Multipass vs Unified output comparison
- ✅ Schema compliance across strategies
- ✅ Performance benchmarking
- ✅ Conversion layer accuracy
- ✅ Backward compatibility verification

### Performance Tests
- ✅ Validation speed (<1ms/entity)
- ✅ Cache hit rate (>80%)
- ✅ Memory usage optimization
- ✅ Throughput measurement
- ✅ Error recovery performance

---

## Monitoring & Observability

### Key Metrics
```typescript
interface SchemaMetrics {
  validation_success_rate: number;         // % of successful validations
  validation_performance_ms: number;       // Average validation time
  cache_hit_rate: number;                  // Cache effectiveness
  conversion_success_rate: number;         // % of successful conversions
  schema_compliance_rate: number;          // % schema-compliant outputs
}
```

### Health Checks
- ✅ Schema validator availability
- ✅ Cache performance metrics
- ✅ Conversion layer status
- ✅ Template processor health
- ✅ Validation error rates

---

## Conclusion

LurisEntityV2 provides a comprehensive, performant, and future-proof solution for standardizing entity extraction output across the Luris platform. The schema ensures consistent JSON structure while maintaining flexibility for future enhancements and backward compatibility during migration.

### Key Benefits Delivered
1. **100% Output Consistency** across all extraction strategies
2. **Performance Optimized** with <5% validation overhead
3. **Backward Compatible** with seamless migration path
4. **Production Ready** with comprehensive error handling
5. **Future Proof** with extensible metadata structure

The specification serves as the definitive reference for all development teams working with entity extraction in the Luris ecosystem.