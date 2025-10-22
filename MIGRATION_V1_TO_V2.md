# Migration Guide: v1 to v2 Wave System

## Overview

Entity Extraction Service v2 represents a complete architectural overhaul from the legacy v1 multipass system to an **intelligent Wave System** with direct vLLM integration. This guide will help you migrate from v1 endpoints to the v2 Wave System.

## Breaking Changes Summary

### 🚨 Removed Endpoints (v1)

All legacy v1 extraction endpoints have been **permanently removed**:

| **Removed Endpoint** | **Status** | **Migration Path** |
|---------------------|------------|-------------------|
| `POST /api/v1/extract` | ❌ **REMOVED** | Use `POST /api/v2/process/extract` |
| `POST /api/v1/extract/multipass` | ❌ **REMOVED** | Use `POST /api/v2/process/extract` |
| `POST /api/v1/extract/chunk` | ❌ **REMOVED** | Use `POST /api/v2/process/extract` (chunking automatic) |
| `POST /api/v1/extract/enhance` | ❌ **REMOVED** | Use `POST /api/v2/process/extract` |
| `POST /api/v1/training/*` | ❌ **REMOVED** | Training endpoints never implemented |

### ✅ Current v2 Endpoint

| **Endpoint** | **Status** | **Purpose** |
|-------------|-----------|-------------|
| `POST /api/v2/process/extract` | ✅ **ACTIVE** | Primary entity extraction with Wave System |

## Schema Changes: LurisEntityV2

### Field Naming (MANDATORY)

The Wave System uses **LurisEntityV2 schema** exclusively. All field names have been standardized:

| **v1 Field** | **v2 Field (LurisEntityV2)** | **Required** |
|-------------|------------------------------|--------------|
| `type` | `entity_type` | ✅ Yes |
| `start` | `start_pos` | ✅ Yes |
| `end` | `end_pos` | ✅ Yes |
| `score` | `confidence` | ✅ Yes |
| `method` | `extraction_method` | ✅ Yes |
| N/A | `metadata` | ✅ Yes |

### Example Entity Comparison

**❌ v1 Entity (DEPRECATED)**
```python
{
    "id": "ent_123",
    "text": "28 U.S.C. § 1331",
    "type": "STATUTE",                # ❌ WRONG
    "start": 10,                      # ❌ WRONG
    "end": 25,                        # ❌ WRONG
    "score": 0.95                     # ❌ WRONG
}
```

**✅ v2 Entity (LurisEntityV2)**
```python
{
    "id": "ent_123",
    "text": "28 U.S.C. § 1331",
    "entity_type": "STATUTE_CITATION",  # ✅ CORRECT
    "start_pos": 10,                    # ✅ CORRECT
    "end_pos": 25,                      # ✅ CORRECT
    "confidence": 0.95,                 # ✅ CORRECT
    "extraction_method": "ai_enhanced", # ✅ REQUIRED
    "metadata": {                       # ✅ REQUIRED
        "jurisdiction": "federal",
        "citation_format": "bluebook_22"
    },
    "created_at": 1704067200000         # ✅ REQUIRED
}
```

## Migration Steps

### Step 1: Update Request Format

**v1 Request (DEPRECATED)**
```python
import requests

# ❌ OLD - Will fail with 404
response = requests.post(
    "http://localhost:8007/api/v1/extract",
    json={
        "document_id": "doc_001",
        "content": "Legal document text...",
        "extraction_mode": "hybrid",
        "extraction_strategy": "multipass",  # ❌ No longer exists
        "confidence_threshold": 0.7
    }
)
```

**v2 Request (CORRECT)**
```python
import requests

# ✅ NEW - Wave System
response = requests.post(
    "http://localhost:8007/api/v2/process/extract",
    json={
        "document_text": "Legal document text...",  # Changed from 'content'
        "document_id": "doc_001",
        "metadata": {
            "court": "Supreme Court",
            "year": 2024
        },
        "force_strategy": None  # Let intelligent routing decide
    }
)
```

### Step 2: Update Response Parsing

**v1 Response Parsing (DEPRECATED)**
```python
# ❌ OLD - Will fail with KeyError
result = response.json()
entities = result["entities"]

for entity in entities:
    entity_type = entity["type"]        # ❌ KeyError!
    start = entity["start"]             # ❌ KeyError!
    end = entity["end"]                 # ❌ KeyError!
```

**v2 Response Parsing (CORRECT)**
```python
# ✅ NEW - LurisEntityV2 schema
result = response.json()
entities = result["entities"]

for entity in entities:
    entity_type = entity["entity_type"]  # ✅ CORRECT
    start_pos = entity["start_pos"]      # ✅ CORRECT
    end_pos = entity["end_pos"]          # ✅ CORRECT
    confidence = entity["confidence"]    # ✅ CORRECT
    method = entity["extraction_method"] # ✅ CORRECT
```

### Step 3: Update Entity Validation

**v1 Validation (DEPRECATED)**
```python
def validate_entity(entity: dict) -> bool:
    # ❌ OLD - Will fail on v2 entities
    required_fields = ["id", "text", "type", "start", "end"]
    return all(field in entity for field in required_fields)
```

**v2 Validation (CORRECT)**
```python
from pydantic import BaseModel, ValidationError

def validate_entity(entity: dict) -> bool:
    """Validate entity against LurisEntityV2 schema"""
    try:
        from src.models.entities import LurisEntityV2
        entity_obj = LurisEntityV2(**entity)

        # Additional field name checks
        if "type" in entity or "start" in entity or "end" in entity:
            raise ValueError(
                "Forbidden field names detected. "
                "Use entity_type, start_pos, end_pos"
            )

        return True
    except ValidationError as e:
        print(f"Schema validation failed: {e}")
        return False
```

## Key Differences: v1 vs v2

### Architecture Changes

| **Feature** | **v1 Multipass** | **v2 Wave System** |
|------------|------------------|-------------------|
| **Strategy** | 7-pass multipass | 4-wave progressive extraction |
| **Routing** | Manual mode selection | Intelligent document routing |
| **Chunking** | External service | Automatic for large docs |
| **Performance** | 3-5 seconds | 30-50% faster (0.8-3s) |
| **Accuracy** | 90-95% | 95%+ with pattern guidance |

### Request Parameters

| **v1 Parameter** | **v2 Parameter** | **Notes** |
|-----------------|------------------|-----------|
| `content` | `document_text` | Field renamed |
| `extraction_mode` | Removed | Auto-routing replaces this |
| `extraction_strategy` | `force_strategy` | Optional override only |
| `enable_multipass` | Removed | Wave System always active |
| N/A | `metadata` | New: Additional context |

### Response Structure

| **v1 Response** | **v2 Response** | **Notes** |
|----------------|-----------------|-----------|
| `extraction_id` | `document_id` | Simplified ID |
| `entities[].type` | `entities[].entity_type` | LurisEntityV2 schema |
| `entities[].start` | `entities[].start_pos` | LurisEntityV2 schema |
| `entities[].end` | `entities[].end_pos` | LurisEntityV2 schema |
| `multipass_metrics` | `routing_decision` | New intelligent routing |
| N/A | `processing_stats.waves_executed` | Wave System metrics |

## Wave System vs Multipass

### Multipass (v1) - REMOVED

The legacy 7-pass multipass strategy has been **completely removed**:

- **Pass 1**: Case citations
- **Pass 2**: Statutes and regulations
- **Pass 3**: Regulatory references
- **Pass 4**: General entities
- **Pass 5**: Courts and judicial entities
- **Pass 6**: Temporal entities
- **Pass 7**: Catch-all

**Issues with Multipass**:
- ❌ Fixed 7 passes regardless of document complexity
- ❌ No intelligent routing
- ❌ Redundant processing
- ❌ Slower performance (3-5 seconds)
- ❌ No pattern-guided few-shot learning

### Wave System (v2) - ACTIVE

The new **4-wave system** provides intelligent, progressive extraction:

- **Wave 1**: Core Legal Entities (92 types)
  - Parties, courts, judges, citations, temporal entities
  - Confidence: 0.80-0.95

- **Wave 2**: Procedural & Financial (29 types)
  - Motions, appeals, monetary amounts, judgments
  - Confidence: 0.80-0.95

- **Wave 3**: Supporting Elements (40 types)
  - Contact info, constitutional entities, legal doctrines
  - Confidence: 0.70-0.90

- **Wave 4**: Relationships (34 types)
  - Entity relationships for knowledge graph construction
  - Confidence: 0.75-0.90

**Advantages of Wave System**:
- ✅ Intelligent document routing (small/medium/large)
- ✅ Pattern-guided few-shot learning with PatternLoader
- ✅ Automatic chunking for large documents
- ✅ 30-50% faster processing
- ✅ GraphRAG-ready relationship extraction
- ✅ Progressive extraction from simple to complex

## Intelligent Routing

The v2 Wave System includes **automatic intelligent routing** based on document characteristics:

### Routing Strategies

| **Strategy** | **Document Size** | **Processing Time** | **Use Case** |
|-------------|------------------|---------------------|--------------|
| `single_pass` | <5K chars | 0.3-0.5 seconds | Very small documents |
| `three_wave` | 5-150K chars | 0.8-15 seconds | Small-medium documents |
| `chunked` | >150K chars | 30-120 seconds | Large documents |

### Automatic Strategy Selection

```python
# ✅ Let intelligent routing decide (RECOMMENDED)
response = requests.post(
    "http://localhost:8007/api/v2/process/extract",
    json={
        "document_text": legal_text,
        "document_id": "doc_001"
        # No force_strategy - routing auto-selects
    }
)

# Strategy selection logic:
# - Very small (<5K chars): single_pass
# - Small-medium (5-150K): three_wave
# - Large (>150K): chunked with parallel processing
```

### Manual Strategy Override (Optional)

```python
# Override routing for specific needs
response = requests.post(
    "http://localhost:8007/api/v2/process/extract",
    json={
        "document_text": legal_text,
        "document_id": "doc_001",
        "force_strategy": "three_wave"  # Force 3-wave strategy
    }
)
```

## Code Migration Examples

### Example 1: Basic Extraction

**Before (v1)**
```python
def extract_entities_v1(text: str) -> list:
    response = requests.post(
        "http://localhost:8007/api/v1/extract",
        json={
            "document_id": "doc_001",
            "content": text,
            "extraction_mode": "ai_enhanced",
            "extraction_strategy": "multipass",
            "confidence_threshold": 0.7
        }
    )

    entities = response.json()["entities"]

    # Parse v1 entities
    parsed = []
    for ent in entities:
        parsed.append({
            "type": ent["type"],
            "text": ent["text"],
            "start": ent["start"],
            "end": ent["end"]
        })

    return parsed
```

**After (v2)**
```python
def extract_entities_v2(text: str) -> list:
    response = requests.post(
        "http://localhost:8007/api/v2/process/extract",
        json={
            "document_text": text,
            "document_id": "doc_001",
            "metadata": {}
        }
    )

    entities = response.json()["entities"]

    # Parse LurisEntityV2 entities
    parsed = []
    for ent in entities:
        parsed.append({
            "entity_type": ent["entity_type"],
            "text": ent["text"],
            "start_pos": ent["start_pos"],
            "end_pos": ent["end_pos"],
            "confidence": ent["confidence"],
            "extraction_method": ent["extraction_method"]
        })

    return parsed
```

### Example 2: Batch Processing

**Before (v1)**
```python
def batch_extract_v1(documents: list[dict]) -> list:
    results = []

    for doc in documents:
        response = requests.post(
            "http://localhost:8007/api/v1/extract",
            json={
                "document_id": doc["id"],
                "content": doc["text"],
                "extraction_mode": "hybrid",
                "extraction_strategy": "multipass"
            }
        )
        results.append(response.json())

    return results
```

**After (v2)**
```python
def batch_extract_v2(documents: list[dict]) -> list:
    results = []

    for doc in documents:
        response = requests.post(
            "http://localhost:8007/api/v2/process/extract",
            json={
                "document_text": doc["text"],
                "document_id": doc["id"],
                "metadata": {
                    "title": doc.get("title"),
                    "court": doc.get("court")
                }
                # Let intelligent routing decide strategy
            }
        )
        results.append(response.json())

    return results
```

### Example 3: Error Handling

**Before (v1)**
```python
try:
    response = requests.post(
        "http://localhost:8007/api/v1/extract",
        json={"content": text, "document_id": "doc_001"}
    )
    response.raise_for_status()

    entities = response.json()["entities"]
    for ent in entities:
        process_entity(ent["type"], ent["text"])

except requests.HTTPError as e:
    print(f"HTTP error: {e}")
```

**After (v2)**
```python
try:
    response = requests.post(
        "http://localhost:8007/api/v2/process/extract",
        json={"document_text": text, "document_id": "doc_001"}
    )
    response.raise_for_status()

    result = response.json()
    entities = result["entities"]
    routing = result["routing_decision"]

    # Process entities with LurisEntityV2 schema
    for ent in entities:
        process_entity(
            entity_type=ent["entity_type"],
            text=ent["text"],
            confidence=ent["confidence"]
        )

    # Access routing information
    print(f"Strategy used: {routing['strategy']}")
    print(f"Processing time: {routing['estimated_duration']}s")

except requests.HTTPError as e:
    error_detail = e.response.json().get("detail", {})
    print(f"HTTP error: {error_detail.get('message')}")
except KeyError as e:
    print(f"Schema error: Missing field {e}")
```

## Testing Your Migration

### Validation Script

Use this script to validate your migration:

```python
import requests
import json

def test_v2_migration(document_text: str):
    """Test v2 endpoint and validate LurisEntityV2 schema"""

    # Test v2 endpoint
    print("Testing v2 Wave System endpoint...")
    response = requests.post(
        "http://localhost:8007/api/v2/process/extract",
        json={
            "document_text": document_text,
            "document_id": "migration_test"
        }
    )

    if response.status_code != 200:
        print(f"❌ FAILED: HTTP {response.status_code}")
        print(f"Error: {response.text}")
        return False

    result = response.json()

    # Validate response structure
    required_fields = ["document_id", "entities", "routing_decision", "processing_stats"]
    for field in required_fields:
        if field not in result:
            print(f"❌ FAILED: Missing response field '{field}'")
            return False

    # Validate entities use LurisEntityV2 schema
    entities = result["entities"]
    print(f"✅ Extracted {len(entities)} entities")

    for i, entity in enumerate(entities):
        # Check for v2 fields
        required_entity_fields = [
            "entity_type", "start_pos", "end_pos",
            "confidence", "extraction_method", "metadata"
        ]

        for field in required_entity_fields:
            if field not in entity:
                print(f"❌ FAILED: Entity {i} missing field '{field}'")
                return False

        # Check for forbidden v1 fields
        forbidden_fields = ["type", "start", "end", "score"]
        for field in forbidden_fields:
            if field in entity:
                print(f"❌ FAILED: Entity {i} has forbidden v1 field '{field}'")
                print(f"   Use '{field}' → LurisEntityV2 equivalent")
                return False

    print("✅ All entities use LurisEntityV2 schema")

    # Print routing decision
    routing = result["routing_decision"]
    print(f"✅ Strategy: {routing['strategy']}")
    print(f"✅ Processing time: {routing['estimated_duration']}s")

    return True

# Run test
sample_text = "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held..."
if test_v2_migration(sample_text):
    print("\n🎉 Migration validation PASSED")
else:
    print("\n❌ Migration validation FAILED")
```

## Troubleshooting

### Common Migration Issues

#### Issue 1: `KeyError: 'type'`

**Cause**: Code still using v1 field names

**Solution**: Update to LurisEntityV2 field names
```python
# ❌ OLD
entity_type = entity["type"]

# ✅ NEW
entity_type = entity["entity_type"]
```

#### Issue 2: `404 Not Found` for `/api/v1/extract`

**Cause**: Using removed v1 endpoint

**Solution**: Update to v2 endpoint
```python
# ❌ OLD
url = "http://localhost:8007/api/v1/extract"

# ✅ NEW
url = "http://localhost:8007/api/v2/process/extract"
```

#### Issue 3: `multipass` strategy not found

**Cause**: Multipass strategy removed

**Solution**: Remove strategy parameter (let intelligent routing decide)
```python
# ❌ OLD
json={"extraction_strategy": "multipass"}

# ✅ NEW
json={"force_strategy": None}  # Or omit completely
```

#### Issue 4: Missing `confidence` field

**Cause**: Not using LurisEntityV2 validation

**Solution**: Use proper entity validation
```python
from src.models.entities import LurisEntityV2

# Validate entity
try:
    entity_obj = LurisEntityV2(**entity)
except ValidationError as e:
    print(f"Invalid entity: {e}")
```

## Performance Comparison

### Benchmark Results: v1 vs v2

**Test Document**: Rahimi Supreme Court opinion (45K chars, 11K tokens)

| **Metric** | **v1 Multipass** | **v2 Wave System** | **Improvement** |
|-----------|------------------|-------------------|-----------------|
| **Processing Time** | 4.2 seconds | 2.1 seconds | 50% faster ✅ |
| **Entities Extracted** | 138 | 142 | +2.9% accuracy ✅ |
| **API Calls** | 7 passes | 3 waves | 57% fewer calls ✅ |
| **Token Usage** | ~35K tokens | ~22K tokens | 37% reduction ✅ |
| **Accuracy** | 92% | 96% | +4% accuracy ✅ |

## Migration Checklist

### Pre-Migration

- [ ] Read this migration guide completely
- [ ] Identify all code using v1 endpoints
- [ ] Review LurisEntityV2 schema documentation
- [ ] Set up v2 test environment

### Code Updates

- [ ] Update all endpoint URLs to `/api/v2/process/extract`
- [ ] Change `content` parameter to `document_text`
- [ ] Remove `extraction_strategy: "multipass"` references
- [ ] Update entity field access: `type` → `entity_type`
- [ ] Update entity field access: `start` → `start_pos`
- [ ] Update entity field access: `end` → `end_pos`
- [ ] Add `metadata` field to entities
- [ ] Update response parsing for `routing_decision`
- [ ] Update entity validation for LurisEntityV2

### Testing

- [ ] Run validation script on sample documents
- [ ] Test error handling with v2 responses
- [ ] Verify all entities use LurisEntityV2 schema
- [ ] Performance test with various document sizes
- [ ] Integration test with downstream services

### Deployment

- [ ] Deploy updated code to staging
- [ ] Run integration tests
- [ ] Monitor for migration issues
- [ ] Deploy to production
- [ ] Remove v1 compatibility code

## Additional Resources

- **LurisEntityV2 Specification**: `/srv/luris/be/entity-extraction-service/docs/LurisEntityV2_Specification.md`
- **API Documentation**: `/srv/luris/be/entity-extraction-service/api.md`
- **Wave System Documentation**: See api.md section on "Wave System Architecture"
- **Intelligent Routing**: See api.md section on "Intelligent Document Routing"

## Support

For migration assistance or questions:

1. Check the LurisEntityV2 specification
2. Review api.md for endpoint documentation
3. Test with the validation script above
4. Check logs for detailed error messages

## Summary

The migration from v1 to v2 requires:

1. **Endpoint Update**: `/api/v1/extract` → `/api/v2/process/extract`
2. **Schema Update**: v1 entity fields → LurisEntityV2 fields
3. **Parameter Update**: `content` → `document_text`
4. **Strategy Removal**: Remove `multipass` references (intelligent routing replaces this)

The v2 Wave System provides **50% faster processing**, **higher accuracy**, and **automatic intelligent routing** compared to the legacy v1 multipass system.

**Migration is mandatory** - all v1 endpoints have been permanently removed.
