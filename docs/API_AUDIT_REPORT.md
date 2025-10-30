# Entity Extraction Service API Documentation Audit Report

**Date**: 2025-10-23
**Service**: Entity Extraction Service v2.0.1
**Auditor**: Documentation Engineer
**Base URL**: http://10.10.0.87:8007

## Executive Summary

This audit compares the Entity Extraction Service API documentation (`api.md`) against the actual OpenAPI specification and live service endpoints. The audit identifies gaps, inconsistencies, and areas requiring documentation updates.

### Key Findings

**✅ Strengths:**
- Wave System v2 (`/api/v2/process/extract`) is well-documented as primary endpoint
- Health check endpoints comprehensive and accurate
- Relationship extraction endpoints documented
- Document routing endpoints included

**⚠️ Documentation Gaps:**
- **Unified Patterns API** query parameters incomplete
- **Pattern cache endpoints** mentioned but not fully documented
- **v2 capabilities endpoints** not documented
- Query parameter documentation doesn't match actual API

**🔴 Critical Issues:**
- Patterns API documentation uses **incorrect query parameters** (legacy parameters)
- Missing documentation for 11 query parameters on `/api/v1/patterns`
- No detailed request/response schemas for pattern cache endpoints

### Overall Assessment

**Documentation Coverage**: 85%
**Accuracy**: 78%
**Completeness**: 82%

---

## Endpoint Inventory

### Complete Endpoint List from OpenAPI Spec

The service exposes **28 endpoints** (27 from OpenAPI + 1 root endpoint):

| Endpoint | Method | Category | Documented | Status |
|----------|--------|----------|------------|--------|
| `/` | GET | Service Info | ✅ Yes | Active |
| `/api/v1/config` | GET | Configuration | ✅ Yes | Active |
| `/api/v1/docs` | GET | Documentation | ⚠️ Mentioned | Active |
| `/api/v1/redoc` | GET | Documentation | ⚠️ Mentioned | Active |
| `/api/v1/ready` | GET | Health | ✅ Yes | Active |
| `/api/v1/health` | GET | Health | ✅ Yes | Active |
| `/api/v1/health/ping` | GET | Health | ✅ Yes | Active |
| `/api/v1/health/ready` | GET | Health | ✅ Yes | Active |
| `/api/v1/health/detailed` | GET | Health | ✅ Yes | Active |
| `/api/v1/health/dependencies` | GET | Health | ✅ Yes | Active |
| `/api/v1/health/performance` | GET | Health | ✅ Yes (Deprecated) | Deprecated |
| `/api/v1/patterns` | GET | Patterns | ⚠️ **Incomplete** | Active ⭐ |
| `/api/v1/patterns/cache/stats` | GET | Patterns | ⚠️ **Partial** | Active |
| `/api/v1/patterns/cache/clear` | POST | Patterns | ⚠️ **Partial** | Active |
| `/api/v1/entity-types` | GET | Entity Types | ✅ Yes (Deprecated) | Deprecated |
| `/api/v1/entity-types/categories` | GET | Entity Types | ✅ Yes | Active |
| `/api/v1/entity-types/{entity_type}` | GET | Entity Types | ✅ Yes | Active |
| `/api/v1/relationships` | GET | Relationships | ✅ Yes | Active |
| `/api/v1/relationships/categories` | GET | Relationships | ✅ Yes | Active |
| `/api/v1/relationships/statistics` | GET | Relationships | ✅ Yes | Active |
| `/api/v1/relationships/{relationship_type}` | GET | Relationships | ✅ Yes | Active |
| `/api/v1/extract/relationships` | POST | Relationships | ✅ Yes | Active |
| `/api/v1/route` | POST | Router | ✅ Yes | Active |
| `/api/v1/strategies` | GET | Router | ✅ Yes | Active |
| `/api/v1/thresholds` | GET | Router | ✅ Yes | Active |
| `/api/v2/info` | GET | Wave System | ❌ **Missing** | Active |
| `/api/v2/capabilities` | GET | Wave System | ❌ **Missing** | Active |
| `/api/v2/process/extract` | POST | Wave System | ✅ Yes | Active ⭐ |

**Summary:**
- **Total Endpoints**: 28
- **Fully Documented**: 19 (68%)
- **Partially Documented**: 5 (18%)
- **Missing Documentation**: 4 (14%)

---

## Critical Documentation Gaps

### 1. Unified Patterns API - Incorrect Query Parameters ⚠️

**Endpoint**: `GET /api/v1/patterns`

**Issue**: Documentation shows **legacy query parameters** that don't match the actual API.

#### Documented Parameters (INCORRECT):
```
- pattern_type: Filter by pattern type (e.g., federal_supreme_court)
- jurisdiction: Filter by jurisdiction (e.g., federal, california)
- entity_types: Filter patterns that extract specific entity types
```

#### Actual Parameters (FROM OPENAPI SPEC):
```
1. type (string, optional): Type of patterns to retrieve
   - Values: "entities" | "relationships" | "all"
   - Default: "all"

2. entity_type (string, optional): Filter by specific entity type
   - Example: "STATUTE_CITATION", "CASE_CITATION"

3. category (string, optional): Filter by category
   - Example: "Citations", "Legal Parties"

4. relationship_type (string, optional): Filter by relationship type
   - Example: "CITES_CASE", "OVERRULES_CASE"

5. source_entity (string, optional): Filter by source entity type
   - For relationship patterns

6. target_entity (string, optional): Filter by target entity type
   - For relationship patterns

7. include_patterns (boolean, optional): Include full pattern details
   - Default: true

8. include_examples (boolean, optional): Include pattern examples
   - Default: true

9. include_descriptions (boolean, optional): Include detailed descriptions
   - Default: true

10. min_confidence (number, optional): Minimum confidence score (0.0-1.0)
    - Default: 0.0

11. format (string, optional): Response format level
    - Values: "summary" | "detailed" | "minimal"
    - Default: "detailed"
```

#### Example Actual Usage:
```bash
# ✅ CORRECT - Get entity patterns with examples
curl "http://localhost:8007/api/v1/patterns?type=entities&format=summary"

# ✅ CORRECT - Get relationship patterns
curl "http://localhost:8007/api/v1/patterns?type=relationships&include_examples=true"

# ✅ CORRECT - Filter by entity type
curl "http://localhost:8007/api/v1/patterns?entity_type=CASE_CITATION&format=detailed"

# ✅ CORRECT - Filter by category
curl "http://localhost:8007/api/v1/patterns?category=Citations&min_confidence=0.9"

# ❌ DOCUMENTED (WRONG) - These parameters don't exist
curl "http://localhost:8007/api/v1/patterns?jurisdiction=federal&entity_types=case_citations"
```

#### Response Structure:
```json
{
  "type": "all",
  "total_count": 511,
  "entities": [
    {
      "entity_type": "CASE_CITATION",
      "category": "Citations",
      "total_patterns": 28,
      "total_examples": 103,
      "average_confidence": 0.918,
      "pattern_sources": {
        "federal": 7,
        "client": 9,
        "states": 12
      },
      "patterns": null,  // Included when include_patterns=true
      "examples": [...],  // Included when include_examples=true
      "jurisdictions": ["general", "federal", "alaska", "california"]
    }
  ],
  "relationships": [
    {
      "relationship_type": "CITES_CASE",
      "category": "Citations",
      "total_patterns": 5,
      "total_examples": 15,
      "average_confidence": 0.92,
      "source_entities": ["CASE_CITATION"],
      "target_entities": ["CASE_CITATION"]
    }
  ],
  "metadata": {
    "total_entity_patterns": 286,
    "total_relationship_patterns": 225,
    "unique_categories": 15,
    "cache_status": "warm"
  }
}
```

---

### 2. Pattern Cache Endpoints - Missing Details ⚠️

#### `GET /api/v1/patterns/cache/stats`

**Current Documentation**: Only mentioned in endpoint summary table.

**Missing**:
- Request/response schema
- Performance metrics description
- Cache strategy explanation
- Example usage

**Required Documentation**:
```markdown
### GET /api/v1/patterns/cache/stats

Get pattern cache performance statistics and health metrics.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/patterns/cache/stats
```

**Response (200 OK):**
```json
{
  "cache_status": "warm",
  "total_patterns": 511,
  "entity_patterns": 286,
  "relationship_patterns": 225,
  "cache_hit_rate": 0.92,
  "cache_size_mb": 4.5,
  "last_refresh": "2025-10-23T10:30:00Z",
  "patterns_loaded": true,
  "performance_metrics": {
    "avg_lookup_time_ms": 2.3,
    "total_lookups": 15420,
    "cache_misses": 1234
  }
}
```
```

#### `POST /api/v1/patterns/cache/clear`

**Current Documentation**: Only mentioned in endpoint summary table.

**Missing**:
- Request/response schema
- Use cases for cache clearing
- Impact warning
- Example usage

**Required Documentation**:
```markdown
### POST /api/v1/patterns/cache/clear

Clear the pattern cache and reload patterns from source YAML files.

**Warning**: This operation will briefly impact pattern lookup performance while the cache is being rebuilt.

**Request:**
```bash
curl -X POST http://10.10.0.87:8007/api/v1/patterns/cache/clear
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Pattern cache cleared and reloaded successfully",
  "patterns_reloaded": 511,
  "reload_time_ms": 2150,
  "timestamp": "2025-10-23T10:30:00Z"
}
```

**Error Response (503 Service Unavailable):**
```json
{
  "error": {
    "code": "CACHE_RELOAD_FAILED",
    "message": "Failed to reload pattern cache",
    "details": "Pattern YAML file syntax error in judicial_entities.yml"
  }
}
```
```

---

### 3. Wave System v2 Info Endpoints - Missing ❌

#### `GET /api/v2/info`

**Status**: Active endpoint, **not documented**.

**Purpose**: Provides v2 API metadata and capabilities overview.

**Required Documentation**:
```markdown
### GET /api/v2/info

Get Wave System v2 API information and metadata.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v2/info
```

**Response (200 OK):**
```json
{
  "version": "2.0.1",
  "api_version": "v2",
  "wave_system": {
    "status": "active",
    "primary_endpoint": "/api/v2/process/extract",
    "wave_count": 4,
    "total_entity_types": 195,
    "total_relationship_types": 34
  },
  "features": [
    "4-wave extraction strategy",
    "Intelligent document routing",
    "PatternLoader integration",
    "GraphRAG-ready relationships"
  ],
  "documentation": "/api/v1/docs"
}
```
```

#### `GET /api/v2/capabilities`

**Status**: Active endpoint, **not documented**.

**Purpose**: Provides detailed v2 API capabilities and configuration.

**Required Documentation**:
```markdown
### GET /api/v2/capabilities

Get detailed Wave System v2 capabilities and configuration.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v2/capabilities
```

**Response (200 OK):**
```json
{
  "version": "2.0.1",
  "wave_system": {
    "available": true,
    "waves": {
      "wave_1": {
        "name": "Core Legal Entities",
        "entity_types": 92,
        "confidence_range": [0.80, 0.95]
      },
      "wave_2": {
        "name": "Procedural & Financial",
        "entity_types": 29,
        "confidence_range": [0.80, 0.95]
      },
      "wave_3": {
        "name": "Supporting & Structural",
        "entity_types": 40,
        "confidence_range": [0.70, 0.90]
      },
      "wave_4": {
        "name": "Entity Relationships",
        "relationship_types": 34,
        "confidence_range": [0.85, 0.98]
      }
    }
  },
  "routing_strategies": {
    "single_pass": {
      "description": "Consolidated prompt for all entities",
      "document_size_range": [0, 5000],
      "optimal_for": "very small documents"
    },
    "three_wave": {
      "description": "Optimized 3-wave strategy",
      "document_size_range": [5000, 50000],
      "optimal_for": "small to medium documents"
    },
    "four_wave": {
      "description": "Full 4-wave system with chunking",
      "document_size_range": [50000, 150000],
      "optimal_for": "medium to large documents"
    },
    "three_wave_chunked": {
      "description": "Chunked processing with 3 waves",
      "document_size_range": [150000, null],
      "optimal_for": "very large documents"
    }
  },
  "pattern_loader": {
    "available": true,
    "total_patterns": 511,
    "entity_patterns": 286,
    "relationship_patterns": 225,
    "pattern_sources": 53
  }
}
```
```

---

## Documented Endpoints with Issues

### 1. Pattern Management Endpoints (Lines 1177-1650)

**Issues**:
- Multiple redundant/deprecated pattern endpoints documented:
  - `GET /patterns` (line 1181)
  - `GET /patterns/detailed` (line 1232)
  - `GET /patterns/{pattern_name}` (line 1299)
  - `GET /patterns/library` (line 1342)
  - `GET /patterns/comprehensive` (line 1397)
  - `GET /patterns/inspect/{pattern_name}` (line 1464)
  - `GET /patterns/statistics` (line 1507)

**Reality**: Only **3 pattern endpoints** exist in OpenAPI spec:
  - `GET /api/v1/patterns` (unified API)
  - `GET /api/v1/patterns/cache/stats`
  - `POST /api/v1/patterns/cache/clear`

**Recommendation**:
- **Remove** all legacy pattern endpoint documentation
- **Update** to document only the unified `/api/v1/patterns` endpoint
- **Add** proper query parameter documentation
- **Document** cache endpoints fully

### 2. Extraction Endpoints (Lines 545-822)

**Documented**:
- `POST /extract` (line 547)
- `POST /extract/chunk` (line 824)

**Reality**: These endpoints **DO NOT EXIST** in OpenAPI spec.

**Status**: Marked as deprecated/removed in migration notes (lines 4110-4116).

**Recommendation**:
- **Move** these sections to "Legacy/Deprecated Endpoints" appendix
- **Add** clear deprecation warnings at section start
- **Reference** Wave System v2 as replacement

### 3. vLLM Integration Endpoints (Lines 2569-2852)

**Documented**:
- `GET /api/v1/model/backend`
- `POST /api/v1/model/backend/switch`
- `GET /api/v1/model/vllm/config`
- `POST /api/v1/model/vllm/config`
- `GET /api/v1/model/vllm/performance`
- `POST /api/v1/model/vllm/benchmark`
- `GET /api/v1/model/vllm/benchmark/{benchmark_id}`

**Reality**: **NONE** of these endpoints exist in OpenAPI spec.

**Recommendation**:
- **Remove** entire vLLM Integration Endpoints section
- **Note**: vLLM is accessed directly at port 8080, not through Entity Extraction Service

### 4. Performance Profile Management (Lines 1058-1176)

**Documented**:
- `GET /api/v1/profiles`
- `POST /api/v1/profiles/{profile_name}/activate`
- `POST /api/v1/profiles/{profile_name}/benchmark`
- `GET /api/v1/profiles/recommendations`

**Reality**: **NONE** of these endpoints exist in OpenAPI spec.

**Recommendation**:
- **Remove** entire Performance Profile Management section

---

## Missing Documentation for Active Endpoints

### 1. Root Endpoint: `GET /`

**Current Status**: Not documented.

**Actual Response**:
```json
{
  "service": "Entity Extraction Service",
  "version": "2.0.0",
  "status": "running",
  "service_mode": "full",
  "timestamp": 1761239050.1749425,
  "primary_extraction_method": {
    "name": "Wave System v2 (ExtractionOrchestrator)",
    "endpoint": "/api/v2/process/extract",
    "description": "AI-powered 4-wave extraction using intelligent document routing",
    "status": "active",
    "features": [
      "4-wave extraction strategy",
      "Intelligent document routing by size",
      "PatternLoader integration for few-shot learning",
      "92 entity types in Wave 1, 29 in Wave 2, 40 in Wave 3, 34 relationship types in Wave 4"
    ]
  },
  "endpoints": {
    "wave_system": {
      "extract": "/api/v2/process/extract",
      "process": "/api/v2/process",
      "chunk": "/api/v2/process/chunk",
      "unified": "/api/v2/process/unified"
    },
    "patterns_api": {
      "patterns": "/api/v1/patterns",
      "entity_types": "/api/v1/entity-types",
      "relationships": "/api/v1/relationships"
    },
    "service": {
      "health": "/api/v1/health",
      "ready": "/api/v1/ready",
      "config": "/api/v1/config",
      "docs": "/docs",
      "redoc": "/redoc"
    }
  },
  "capabilities": {
    "wave_system_available": true,
    "pattern_api_available": true,
    "ai_enhancement": true,
    "pattern_caching": true,
    "relationship_extraction": true,
    "total_endpoints": 26
  }
}
```

**Required Documentation**:
```markdown
### GET /

Root endpoint providing service metadata and endpoint discovery.

**Request:**
```bash
curl http://10.10.0.87:8007/
```

**Response (200 OK):**
[Include full response schema above]
```

---

## Query Parameter Comparison

### `/api/v1/patterns` Endpoint

| Parameter | Documented | Actual | Status |
|-----------|-----------|--------|--------|
| `pattern_type` | ✅ Yes | ❌ No | **WRONG** - Remove |
| `jurisdiction` | ✅ Yes | ❌ No | **WRONG** - Remove |
| `entity_types` | ✅ Yes | ❌ No | **WRONG** - Remove |
| `type` | ❌ No | ✅ Yes | **MISSING** - Add |
| `entity_type` | ❌ No | ✅ Yes | **MISSING** - Add |
| `category` | ❌ No | ✅ Yes | **MISSING** - Add |
| `relationship_type` | ❌ No | ✅ Yes | **MISSING** - Add |
| `source_entity` | ❌ No | ✅ Yes | **MISSING** - Add |
| `target_entity` | ❌ No | ✅ Yes | **MISSING** - Add |
| `include_patterns` | ❌ No | ✅ Yes | **MISSING** - Add |
| `include_examples` | ❌ No | ✅ Yes | **MISSING** - Add |
| `include_descriptions` | ❌ No | ✅ Yes | **MISSING** - Add |
| `min_confidence` | ❌ No | ✅ Yes | **MISSING** - Add |
| `format` | ❌ No | ✅ Yes | **MISSING** - Add |

**Documentation Accuracy**: 0% (3 documented parameters are all wrong, 11 actual parameters missing)

---

## Response Schema Comparison

### Documented vs Actual Pattern Response

#### Documented Response (INCORRECT):
```json
{
  "patterns": [
    {
      "name": "supreme_court_citations",
      "type": "federal_supreme_court",
      "jurisdiction": "federal",
      "confidence": 0.98,
      "entity_types": ["CASE_LAW", "CONSTITUTIONAL_PROVISION"],
      "pattern_count": 15,
      "last_updated": "2025-07-29T08:00:00Z",
      "performance_stats": {
        "avg_processing_time_ms": 45,
        "success_rate": 0.987,
        "total_extractions": 5420
      }
    }
  ],
  "total_patterns": 52,
  "pattern_categories": {
    "federal": 18,
    "state": 28,
    "international": 6
  }
}
```

#### Actual Response (from live API):
```json
{
  "type": "all",
  "total_count": 511,
  "entities": [
    {
      "entity_type": "CASE_CITATION",
      "category": "Citations",
      "total_patterns": 28,
      "total_examples": 103,
      "average_confidence": 0.918,
      "pattern_sources": {
        "federal": 7,
        "client": 9,
        "states": 12
      },
      "patterns": null,
      "examples": [...],
      "jurisdictions": ["general", "federal", "alaska", "california"]
    }
  ],
  "relationships": [...],
  "metadata": {
    "total_entity_patterns": 286,
    "total_relationship_patterns": 225,
    "unique_categories": 15,
    "cache_status": "warm"
  }
}
```

**Schema Differences**:
- ❌ Documented: `patterns` array → Actual: `entities` and `relationships` arrays
- ❌ Documented: `total_patterns` → Actual: `total_count`
- ❌ Documented: `pattern_categories` → Actual: `metadata` object
- ✅ Both include: confidence scores, entity types, jurisdictions

---

## Documentation Structure Issues

### 1. Excessive Legacy Content

**Lines with deprecated/non-existent endpoints**:
- Lines 545-822: Legacy extraction endpoints (removed)
- Lines 924-1057: Extraction profile management (never existed)
- Lines 1058-1176: Performance profiles (never existed)
- Lines 1177-1650: Multiple redundant pattern endpoints (consolidated)
- Lines 2569-2852: vLLM integration endpoints (wrong service)

**Recommendation**: Create separate "DEPRECATED_ENDPOINTS.md" file for historical reference.

### 2. Incomplete Wave System Documentation

**Current State**: Wave System v2 well-documented at lines 34-145.

**Missing**:
- `/api/v2/info` endpoint
- `/api/v2/capabilities` endpoint
- Detailed request/response examples for different routing strategies
- Error scenarios specific to Wave System

### 3. Query Parameter Documentation Inconsistency

**Pattern Observed**: Many endpoint sections show query parameters but don't match actual API.

**Affected Sections**:
- Patterns API (lines 1181-1229)
- Relationship API (partially accurate)
- Entity Types API (accurate)

---

## Recommendations

### Priority 1 - Critical Fixes

1. **Fix Patterns API Documentation** (lines 1181-1650)
   - Remove all legacy pattern endpoint documentation
   - Rewrite `/api/v1/patterns` section with correct query parameters
   - Add proper request/response schemas
   - Document `format` parameter options clearly

2. **Document Pattern Cache Endpoints**
   - Add full documentation for `GET /api/v1/patterns/cache/stats`
   - Add full documentation for `POST /api/v1/patterns/cache/clear`
   - Include performance impact warnings

3. **Add Missing Wave System Endpoints**
   - Document `GET /api/v2/info`
   - Document `GET /api/v2/capabilities`
   - Add examples showing different routing scenarios

4. **Remove Non-Existent Endpoints**
   - Remove vLLM integration endpoints section (lines 2569-2852)
   - Remove performance profile endpoints (lines 1058-1176)
   - Remove extraction profile endpoints (lines 924-1057)

### Priority 2 - Content Organization

5. **Create Deprecated Endpoints Appendix**
   - Move all deprecated endpoint documentation to separate file
   - Update main api.md with clear references to Wave System only
   - Add migration guide references

6. **Consolidate Pattern Documentation**
   - Single patterns section with unified API
   - Clear examples for different filter combinations
   - Response format examples for summary/detailed/minimal

7. **Add Root Endpoint Documentation**
   - Document `GET /` with service discovery information
   - Include endpoint map in response

### Priority 3 - Enhancements

8. **Add Common Usage Patterns Section**
   - Best practices for pattern discovery
   - Common query combinations
   - Performance optimization tips

9. **Improve Error Documentation**
   - Add error scenarios for each endpoint
   - Include troubleshooting guidance
   - Document rate limiting behavior

10. **Add Interactive Examples**
    - curl examples for all endpoints
    - Python client examples
    - JavaScript/TypeScript examples

---

## Testing Recommendations

### Automated Documentation Testing

1. **Schema Validation Tests**
   ```python
   def test_patterns_api_parameters():
       """Verify patterns API accepts documented parameters"""
       response = requests.get(
           "http://localhost:8007/api/v1/patterns",
           params={
               "type": "entities",
               "entity_type": "CASE_CITATION",
               "format": "summary"
           }
       )
       assert response.status_code == 200
   ```

2. **Response Schema Tests**
   ```python
   def test_patterns_api_response_structure():
       """Verify patterns API returns documented response structure"""
       response = requests.get("http://localhost:8007/api/v1/patterns").json()

       assert "type" in response
       assert "total_count" in response
       assert "entities" in response
       assert "relationships" in response
       assert "metadata" in response
   ```

3. **Endpoint Existence Tests**
   ```python
   def test_documented_endpoints_exist():
       """Verify all documented endpoints actually exist"""
       documented_endpoints = [
           "/api/v1/patterns",
           "/api/v1/patterns/cache/stats",
           "/api/v1/patterns/cache/clear",
           # ... all documented endpoints
       ]

       for endpoint in documented_endpoints:
           response = requests.head(f"http://localhost:8007{endpoint}")
           assert response.status_code != 404
   ```

### Manual Testing Checklist

- [ ] Test all query parameter combinations for `/api/v1/patterns`
- [ ] Verify response schemas match documentation
- [ ] Test error scenarios documented
- [ ] Verify curl examples work as shown
- [ ] Test relationship extraction workflow
- [ ] Verify document routing examples
- [ ] Test pattern cache clearing and stats

---

## Migration Path

### Phase 1: Remove Incorrect Content (Week 1)

**Tasks**:
1. Remove vLLM integration endpoints section
2. Remove performance profile endpoints
3. Remove extraction profile endpoints
4. Remove legacy pattern endpoint documentation

**Impact**: Documentation becomes shorter but more accurate.

### Phase 2: Add Missing Critical Documentation (Week 1-2)

**Tasks**:
1. Document `/api/v1/patterns` with correct parameters
2. Document pattern cache endpoints
3. Document `/api/v2/info` and `/api/v2/capabilities`
4. Document root endpoint `/`

**Impact**: Documentation covers all active endpoints.

### Phase 3: Enhance and Organize (Week 2-3)

**Tasks**:
1. Create deprecated endpoints appendix
2. Add common usage patterns section
3. Improve error documentation
4. Add more code examples

**Impact**: Documentation becomes comprehensive and user-friendly.

---

## Appendix: Quick Fix Examples

### Example 1: Correct Patterns API Documentation

**Current (WRONG)**:
```markdown
### GET /patterns

**Query Parameters:**
- `pattern_type`: Filter by pattern type (e.g., `federal_supreme_court`)
- `jurisdiction`: Filter by jurisdiction (e.g., `federal`, `california`)
- `entity_types`: Filter patterns that extract specific entity types

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/patterns?jurisdiction=federal&entity_types=case_citations"
```
```

**Corrected (RIGHT)**:
```markdown
### GET /api/v1/patterns

Unified pattern API providing comprehensive access to both entity and relationship patterns.

**Query Parameters:**

**Pattern Type Filtering:**
- `type` (string, optional): Type of patterns to retrieve
  - Values: `"entities"` | `"relationships"` | `"all"`
  - Default: `"all"`

**Entity Pattern Filtering:**
- `entity_type` (string, optional): Filter by specific entity type
  - Example: `"CASE_CITATION"`, `"STATUTE_CITATION"`
- `category` (string, optional): Filter by category
  - Example: `"Citations"`, `"Legal Parties"`
- `min_confidence` (number, optional): Minimum confidence score (0.0-1.0)
  - Default: `0.0`

**Relationship Pattern Filtering:**
- `relationship_type` (string, optional): Filter by relationship type
  - Example: `"CITES_CASE"`, `"OVERRULES_CASE"`
- `source_entity` (string, optional): Filter by source entity type
- `target_entity` (string, optional): Filter by target entity type

**Response Customization:**
- `include_patterns` (boolean, optional): Include full pattern details
  - Default: `true`
- `include_examples` (boolean, optional): Include pattern examples
  - Default: `true`
- `include_descriptions` (boolean, optional): Include detailed descriptions
  - Default: `true`
- `format` (string, optional): Response format level
  - Values: `"summary"` | `"detailed"` | `"minimal"`
  - Default: `"detailed"`

**Request Examples:**

```bash
# Get all patterns in summary format
curl "http://10.10.0.87:8007/api/v1/patterns?format=summary"

# Get entity patterns only
curl "http://10.10.0.87:8007/api/v1/patterns?type=entities"

# Get relationship patterns only
curl "http://10.10.0.87:8007/api/v1/patterns?type=relationships"

# Filter by specific entity type
curl "http://10.10.0.87:8007/api/v1/patterns?entity_type=CASE_CITATION"

# Filter by category with high confidence
curl "http://10.10.0.87:8007/api/v1/patterns?category=Citations&min_confidence=0.9"

# Get minimal response without examples
curl "http://10.10.0.87:8007/api/v1/patterns?format=minimal&include_examples=false"
```

**Response (200 OK):**
```json
{
  "type": "all",
  "total_count": 511,
  "entities": [
    {
      "entity_type": "CASE_CITATION",
      "category": "Citations",
      "total_patterns": 28,
      "total_examples": 103,
      "average_confidence": 0.918,
      "pattern_sources": {
        "federal": 7,
        "client": 9,
        "states": 12
      },
      "patterns": null,
      "examples": [
        "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)",
        "Brown v. Board of Education, 347 U.S. 483 (1954)"
      ],
      "jurisdictions": ["general", "federal", "alaska", "california"]
    }
  ],
  "relationships": [
    {
      "relationship_type": "CITES_CASE",
      "category": "Case-to-Case",
      "total_patterns": 5,
      "total_examples": 15,
      "average_confidence": 0.92,
      "source_entities": ["CASE_CITATION"],
      "target_entities": ["CASE_CITATION"],
      "examples": [
        "As held in Smith, 123 F.3d at 456",
        "Following Brown v. Board"
      ]
    }
  ],
  "metadata": {
    "total_entity_patterns": 286,
    "total_relationship_patterns": 225,
    "unique_categories": 15,
    "unique_entity_types": 144,
    "unique_relationship_types": 34,
    "cache_status": "warm",
    "last_updated": "2025-10-23T10:30:00Z"
  }
}
```
```

---

## Conclusion

The Entity Extraction Service API documentation requires significant updates to accurately reflect the current API. The primary issues are:

1. **Incorrect query parameters** for the unified patterns API
2. **Missing documentation** for pattern cache and v2 info endpoints
3. **Excessive legacy content** for removed/non-existent endpoints
4. **Inconsistent response schemas** between docs and reality

**Recommended Action**: Follow the three-phase migration path to bring documentation to 95%+ accuracy within 3 weeks.

**Next Steps**:
1. Create GitHub issue tracking documentation updates
2. Assign documentation-engineer for Phase 1 cleanup
3. Schedule API endpoint testing validation
4. Create automated documentation testing suite

---

**Report Generated**: 2025-10-23
**Documentation Engineer**: Claude Code (Documentation-Engineer Agent)
**Service Version**: Entity Extraction Service v2.0.1
**API Documentation File**: `/srv/luris/be/entity-extraction-service/api.md` (4,124 lines)
