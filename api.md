# Entity Extraction Service API Reference

## ⚠️ BREAKING CHANGES (v2.0.1)

**Version 2.0.1 introduces breaking schema changes. Update your client code immediately:**

### Entity Schema Changes
- **Field renamed**: `type` → `entity_type` in all entity objects
- **Required fields**: `entities` field is now required (never null), `confidence` is required
- **Minimum confidence**: All entities must have confidence ≥ 0.7

### Client Code Migration
```python
# ❌ OLD (v2.0.0) - Will fail with KeyError
entity_type = entity["type"]
entity.type

# ✅ NEW (v2.0.1) - Correct
entity_type = entity["entity_type"]
entity.entity_type
```

### Configuration Changes
- **YAML configuration deprecated**: All settings now in `.env` (161 variables)
- See `docs/MIGRATION_GUIDE_v2.0.1.md` for complete migration instructions

## Overview

**Version**: 2.0.1
**Last Updated**: 2025-10-15

The Entity Extraction Service provides comprehensive legal entity extraction capabilities through an **AI-powered Wave System architecture** with intelligent document routing and multi-stage extraction. The service supports **195+ entity types and 34 relationship types** across 4 specialized extraction waves, optimized for legal document processing with PatternLoader integration for few-shot learning.

### 🌟 Primary Extraction Method: Wave System v2 (ExtractionOrchestrator)

The **Wave System v2** is the primary extraction method, powered by ExtractionOrchestrator that uses vLLM directly for AI-powered entity extraction. It implements a 4-wave strategy with intelligent document routing:

- **Wave 1**: Core Legal Entities (92 types) - Parties, courts, judges, legal citations, temporal entities
- **Wave 2**: Procedural & Financial Elements (29 types) - Motions, appeals, monetary amounts, judgments
- **Wave 3**: Supporting & Structural Elements (40 types) - Contact info, constitutional entities, legal doctrines
- **Wave 4**: Entity Relationships (34 types) - Knowledge graph construction for GraphRAG

**Primary Endpoint**: `POST /api/v2/process/extract`

**Key Features**:
- Intelligent document routing based on size and complexity
- PatternLoader integration providing pattern examples for few-shot learning
- Optimized for AI-powered extraction with vLLM integration
- GraphRAG-ready relationship extraction in Wave 4

### ⚠️ Important: Wave System is the SOLE Extraction Method

The **Wave System** at `/api/v2/process/*` is the **only extraction method** in the Entity Extraction Service. Legacy multipass endpoints have been fully removed.

**Migration Complete**: All extraction functionality has been migrated to the Wave System for:
- Better performance through intelligent routing
- Improved accuracy with pattern-guided few-shot learning
- GraphRAG integration capabilities
- Modern AI architecture

**For extraction needs, use**: `POST /api/v2/process/extract`

## ⚠️ Critical Architecture Notes

### **Wave System Architecture (PRIMARY ⭐)**

The Wave System implements a sophisticated 4-wave extraction strategy that progressively extracts entities from simple to complex:

#### Wave 1: Core Legal Entities (92 types)
**Focus**: Foundational entities that later waves build upon
- Party & Actor Entities (25 types): Parties, plaintiffs, defendants, attorneys, judges
- Court & Judicial Entities (14 types): Courts, circuits, districts, judicial panels
- Legal Citations - Core (12 types): Case citations, statutes, USC, CFR, constitutional
- Legal Citations - Advanced (17 types): Parallel citations, electronic, law reviews, treatises
- Temporal Entities (14 types): Dates, filing dates, deadlines, decision dates
- Document Structure (10 types): Defined terms, section markers, Latin terms

**Confidence**: 0.80-0.95 depending on entity category

#### Wave 2: Procedural, Financial & Organizational Entities (29 types)
**Focus**: Procedural actions, financial values, and legal organizations
- Procedural Elements & Discovery (12 types): Motions, appeals, discovery, interrogatories
- Financial & Monetary Entities (12 types): Damages, bail, settlements, attorney fees
- Judgment & Relief Entities (4 types): Judgments, injunctions, protective orders
- Legal Organization Entities (1 type): Law firms (international/public interest)

**Confidence**: 0.80-0.95 with higher thresholds for financial entities

#### Wave 3: Supporting & Structural Elements (40 types)
**Focus**: Contextual information and legal doctrine entities
- Contact & Location Information (5 types): Addresses, emails, phone numbers, jurisdiction
- Constitutional Entities (14 types): Amendments, commerce clause, due process, equal protection
- Legal Doctrine Entities (8 types): Precedent, stare decisis, res judicata, immunity
- Administrative & Governmental (5 types): Administrative law, agencies, congressional
- Document Structure Elements (8 types): Legal markers, paragraph headers, signature blocks

**Confidence**: 0.70-0.90 depending on structural clarity

#### Wave 4: Entity Relationships (34 relationship types)
**Focus**: Knowledge graph construction for GraphRAG integration
- Case-to-Case Relationships (5 types): CITES_CASE, OVERRULES_CASE, DISTINGUISHES_CASE
- Statute Relationships (4 types): CITES_STATUTE, INTERPRETS_STATUTE, APPLIES_STATUTE
- Party Relationships (4 types): PARTY_VS_PARTY, REPRESENTS, EMPLOYED_BY
- Procedural Relationships (4 types): APPEALS_FROM, REMANDS_TO, CONSOLIDATES_WITH
- Document Relationships (4 types): REFERENCES_DOCUMENT, INCORPORATES_BY_REFERENCE, AMENDS
- Contractual Relationships (4 types): CONTRACTS_WITH, OBLIGATED_TO, BENEFITS
- Judicial Relationships (6 types): DECIDED_BY, AUTHORED_BY, JOINED_BY, DISSENTED_BY
- Temporal Relationships (3 types): OCCURRED_BEFORE, OCCURRED_AFTER, OCCURRED_DURING

**Confidence**: 0.85-0.98 with highest standards for critical relationships

### **PatternLoader System Integration**

The Wave System integrates PatternLoader to provide pattern examples that get injected into wave templates for few-shot learning:

**Pattern Database**: 286 patterns across 53 YAML configuration files
**Entity Type Coverage**: 144 pattern entity types mapped to 195+ wave entity types
**Integration Method**: Pattern examples injected into wave1-4.md templates at runtime

**Example Pattern Injection**:
```
Wave 1 Template + PatternLoader Examples → Few-Shot Prompt → vLLM Extraction
```

PatternLoader provides concrete examples for each entity type, enabling the Wave System to learn from established patterns while maintaining AI flexibility.

### **Intelligent Document Routing**

The Wave System automatically selects the optimal extraction strategy based on document characteristics:

| Document Size | Strategy | Description |
|--------------|----------|-------------|
| Very Small (<5K chars) | Single-pass | Consolidated prompt for all entities |
| Small (5-50K chars) | 3-wave | Optimized wave strategy (Waves 1-3) |
| Medium (50-150K chars) | 4-wave + chunking | Full wave system with intelligent chunking |
| Large (>150K chars) | Adaptive chunking | Chunked processing with wave extraction per chunk |

**Base URL**: `http://10.10.0.87:8007`
**Primary API**: `/api/v2/process/*` (Wave System - ACTIVE ⭐)
**Service Version**: 2.0.0
**Protocol**: HTTP/HTTPS
**Data Format**: JSON

**Note**: Legacy multipass extraction API has been removed. Use Wave System endpoints only.

## Prerequisites

### Virtual Environment Requirement

⚠️ **CRITICAL**: All Python operations with this service **MUST** be performed within the activated virtual environment.

**Correct Usage:**
```bash
# ALWAYS activate venv first
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Verify activation
which python  # Should show: .../venv/bin/python
which pytest  # Should show: .../venv/bin/pytest

# Now you can run service, tests, or scripts
python run.py
pytest tests/ -v
```

**❌ NEVER DO:**
```bash
# Don't create new venv (it already exists!)
python3 -m venv venv  # FORBIDDEN

# Don't run without activation
python run.py  # Will fail with import errors
pytest tests/  # Will fail with ModuleNotFoundError
```

### Service Dependencies Checklist

Before using the Entity Extraction Service, ensure all required services are running:

| Service | Port | Health Check | Purpose |
|---------|------|--------------|---------|
| **vLLM Service** | 8080 | `curl http://localhost:8080/v1/models` | LLM inference (required for ai_enhanced/hybrid modes) |
| **Prompt Service** | 8003 | `curl http://localhost:8003/api/v1/health/ping` | Template management (required for ai_enhanced mode) |
| **Log Service** | 8001 | `curl http://localhost:8001/api/v1/health` | Centralized logging (recommended) |
| **Supabase Service** | 8002 | `curl http://localhost:8002/health` | Database operations (recommended) |

**Quick Dependency Check:**
```bash
# Check all services at once
for port in 8080 8003 8001 8002; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health >/dev/null 2>&1 && echo "✅ UP" || echo "❌ DOWN"
done
```

**vLLM-Only Mode:**

The service can operate in "vLLM-only" mode where ExtractionService is not initialized. This is **intentional** for distributed architectures:

```bash
# Check if service is in vLLM-only mode
curl http://localhost:8007/api/v1/health/ready | jq '.mode'
# Returns: "vllm_only" or "full_service"
```

In vLLM-only mode:
- ✅ Health endpoints work
- ✅ vLLM inference endpoints work
- ❌ Full extraction endpoints unavailable
- ℹ️ This is expected behavior for microservices architecture

## Authentication

Currently, the service operates without authentication in development mode. For production deployments, API key authentication is recommended through the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-api-key" http://10.10.0.87:8007/api/v1/extract
```

### Future Authentication Support
- **API Key Authentication**: Planned for production deployments
- **JWT Token Support**: Under consideration for enterprise deployments
- **OAuth 2.0**: Planned for third-party integrations

## Rate Limiting

- **Default Limit**: 100 requests per minute per client
- **Burst Limit**: 20 requests per 10 seconds
- **Rate Limit Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Configurable**: Can be adjusted via environment variables

When rate limit is exceeded, the service returns HTTP 429 with retry information:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60,
    "current_limit": 100,
    "current_usage": 100
  }
}
```

## Request/Response Format

All requests and responses use JSON format with UTF-8 encoding.

### Common Headers

**Request Headers:**
```
Content-Type: application/json
X-Request-ID: <uuid> (optional, auto-generated if not provided)
X-API-Key: <key> (required in production)
User-Agent: <client-identifier>
```

**Response Headers:**
```
Content-Type: application/json; charset=utf-8
X-Request-ID: <uuid>
X-Processing-Time-Ms: <milliseconds>
X-RateLimit-Limit: <limit>
X-RateLimit-Remaining: <remaining>
X-RateLimit-Reset: <reset-timestamp>
```

### Request Size Limits
- **Maximum request size**: 10MB
- **Maximum content length**: 1MB per document
- **Maximum entities returned**: 1000 (configurable)

## Health Check Endpoints

### GET /health

Basic health check endpoint with service status information.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service",
  "version": "1.0.0",
  "uptime_seconds": 3600.45
}
```

**Response (503 Service Unavailable) - If unhealthy:**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service",
  "version": "1.0.0",
  "errors": ["pattern_loader_failed", "ai_service_unavailable"]
}
```

### GET /health/ping

Simple ping check for load balancers with minimal response data.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/health/ping
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service", 
  "version": "1.0.0",
  "uptime_seconds": 3600.45
}
```

**Response (503 Service Unavailable) - If unhealthy:**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service",
  "errors": ["pattern_loader_failed", "ai_service_unavailable"]
}
```

### GET /health/ready

Readiness check with dependency verification to ensure the service can process requests.

⚠️ **Note on vLLM-Only Mode**: As of P1-1 fix, this endpoint correctly reports service status when running in vLLM-only configuration. A 503 status with `"mode": "vllm_only"` is **expected behavior** and **NOT an error** for distributed architectures.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/health/ready
```

**Response (200 OK) - Ready to process requests (Full Service Mode):**
```json
{
  "status": "ready",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service",
  "version": "1.0.0",
  "ready": true,
  "mode": "full_service",
  "checks": {
    "pattern_loader": "healthy",
    "ai_service": "healthy",
    "log_service": "healthy",
    "database": "healthy",
    "extraction_service": "available"
  }
}
```

**Response (503 Service Unavailable) - vLLM-Only Mode (Expected for Microservices):**
```json
{
  "status": "not_ready",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service",
  "version": "1.0.0",
  "ready": false,
  "mode": "vllm_only",
  "notes": "ExtractionService not available - running with vLLM-only configuration",
  "checks": {
    "pattern_loader": "not_initialized",
    "ai_service": "healthy",
    "log_service": "healthy",
    "database": "healthy",
    "extraction_service": "unavailable"
  },
  "vllm_inference": "available",
  "recommended_action": "Use vLLM inference endpoints or enable full ExtractionService if needed"
}
```

**Response (503 Service Unavailable) - Service Issues:**
```json
{
  "status": "not_ready",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service",
  "version": "1.0.0",
  "ready": false,
  "mode": "full_service",
  "checks": {
    "pattern_loader": "healthy",
    "ai_service": "unhealthy",
    "log_service": "healthy",
    "database": "healthy",
    "extraction_service": "available"
  },
  "blocking_issues": ["ai_service_unavailable"]
}
```

**Understanding the Response:**

| Field | Description |
|-------|-------------|
| `mode` | Service operation mode: `"full_service"` or `"vllm_only"` |
| `notes` | Additional context about service configuration |
| `extraction_service` | Status of full extraction capabilities |
| `vllm_inference` | Status of vLLM-only inference capabilities |
| `blocking_issues` | Array of critical issues preventing service operation |

**When is 503 Status Expected?**

- ✅ **Expected**: `mode: "vllm_only"` - Service configured for distributed architecture
- ❌ **Error**: `blocking_issues` present - Actual service failures requiring attention

### GET /health/detailed

Comprehensive health check with component status, performance metrics, and system information.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/health/detailed
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "entity-extraction-service",
  "version": "1.0.0", 
  "uptime_seconds": 86400,
  "components": {
    "pattern_loader": {
      "status": "healthy",
      "patterns_loaded": 52,
      "last_reload": "2025-07-29T08:00:00Z",
      "load_time_ms": 2150
    },
    "local_ai": {
      "status": "healthy",
      "llama_model": "Qwen/Qwen3-VL-8B-Instruct-FP8",
      "model_loaded": true,
      "response_time_ms": 176,
      "breakthrough_achievements": 125,
      "memory_usage_mb": 4832,
      "gpu_layers": 64
    },
    "database": {
      "status": "healthy",
      "supabase_service": "connected",
      "connection_pool": "optimal"
    },
    "memory": {
      "status": "healthy",
      "usage_mb": 512,
      "limit_mb": 2048,
      "usage_percent": 25.0
    }
  },
  "extraction_modes": ["regex", "ai_enhanced", "hybrid"],
  "supported_entity_types": 31,
  "local_ai_integration": "available",
  "breakthrough_performance": "enabled",
  "performance_metrics": {
    "avg_extraction_time_ms": 850,
    "total_extractions": 15420,
    "success_rate": 0.989,
    "pattern_cache_hit_rate": 0.92
  }
}
```

### GET /health/dependencies

Detailed dependency check with response times and connectivity status.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/health/dependencies
```

**Response:**
```json
{
  "service": "entity-extraction-service",
  "timestamp": "2025-07-29T10:30:00Z",
  "overall_status": "healthy",
  "dependencies": {
    "log_service": {
      "url": "http://localhost:8001",
      "status": "healthy",
      "response_time_ms": 15.6,
      "last_check": "2025-07-29T10:29:30Z",
      "version": "1.0.0",
      "features_available": [
        "structured_logging",
        "request_tracking",
        "performance_metrics"
      ]
    },
    "llama_local_client": {
      "status": "healthy",
      "model_path": "Qwen/Qwen3-VL-8B-Instruct-FP8-GGUF",
      "model_loaded": true,
      "response_time_ms": 176.4,
      "last_check": "2025-07-29T10:29:30Z",
      "breakthrough_achievements": 89,
      "performance_tier": "SS_Ultra_Fast",
      "config_profile": "breakthrough_optimized",
      "memory_usage_mb": 4832,
      "gpu_layers": 64,
      "local_ai_enhancement": "available"
    },
    "supabase_service": {
      "url": "http://localhost:8002",
      "status": "healthy",
      "response_time_ms": 8.3,
      "last_check": "2025-07-29T10:29:30Z",
      "version": "1.0.0",
      "schemas_available": ["law", "client", "graph"]
    }
  },
  "dependency_summary": {
    "total_dependencies": 3,
    "healthy_dependencies": 3,
    "avg_response_time_ms": 67.2,
    "all_critical_services_available": true,
    "local_ai_status": "optimal",
    "breakthrough_performance": "active"
  }
}
```

## Entity Extraction Endpoints

### POST /extract

Extract legal entities from document content using the hybrid REGEX + AI system with comprehensive configuration options. This is the primary endpoint for entity extraction with support for multiple processing modes, confidence thresholds, and entity type filtering.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Unique document identifier |
| `content` | string | Yes | Document text content (max 1MB) |
| `extraction_mode` | string | No | Extraction mode: `regex`, `ai_enhanced`, or `hybrid` (default) |
| `extraction_strategy` | string | No | AI extraction strategy: `multipass`, `ai_enhanced`, or `unified` (default: auto-select based on mode) |
| `confidence_threshold` | float | No | Minimum confidence score (0.0-1.0, default: 0.7) |
| `entity_types` | array | No | Specific entity types to extract (default: all 31 types) |
| `relationship_types` | array | No | Specific relationship types to extract (default: all 46 types when `enable_relationships=true`) |
| `relationship_categories` | array | No | Relationship categories to extract (e.g., `legal_precedent`, `contractual_financial`) |
| `document_metadata` | object | No | Document context information |
| `chunk_size` | integer | No | Chunk size for large documents (default: 5000) |
| `enable_relationships` | boolean | No | Extract entity relationships (default: true) |
| `max_entities` | integer | No | Maximum entities to return (default: unlimited) |
| `max_relationships` | integer | No | Maximum relationships to return (default: unlimited) |
| `context_window` | integer | No | Character window around entities (default: 500) |

**Supported Entity Types (31 Total):**
- `case_citations`, `statute_citations`, `court_names`, `judges`, `attorneys`
- `parties`, `dates`, `monetary_amounts`, `legal_doctrines`, `procedural_terms`
- `contracts`, `agreements`, `legal_references`, `jurisdictions`, `legal_standards`
- `evidence_types`, `motion_types`, `filing_deadlines`, `legal_precedents`
- `constitutional_references`, `regulatory_citations`, `administrative_codes`
- `local_ordinances`, `international_law`, `treaty_references`, `arbitration_clauses`
- `settlement_terms`, `damages_calculations`, `legal_fees`, `court_costs`, `legal_entities`

### AI Extraction Strategies

The service provides three distinct AI extraction strategies, each optimized for different use cases:

#### 1. Multipass Strategy (`multipass`)
**Approach**: Progressive refinement across 7 specialized passes
- **Pass 1**: Case citations with high recall
- **Pass 2**: Statute and regulation citations  
- **Pass 3**: Regulatory references and administrative codes
- **Pass 4**: General entities (parties, judges, attorneys)
- **Pass 5**: Courts and judicial entities
- **Pass 6**: Temporal entities (dates, deadlines)
- **Pass 7**: Catch-all for remaining entities

**Characteristics**:
- Progressive confidence refinement (0.3-0.7 initial, refined in later passes)
- Highest accuracy through iterative validation
- Best for critical documents requiring maximum precision
- Longer processing time (3-5 seconds typical)

**When to Use**: Legal briefs, court opinions, regulatory documents requiring comprehensive analysis

#### 2. AI Enhanced Strategy (`ai_enhanced`)
**Approach**: Deep contextual analysis with advanced NLP
- Coreference resolution for pronoun entities
- Semantic similarity for variant detection  
- Contextual boundaries for multi-word entities
- Relationship inference from sentence structure
- Advanced confidence calculation using multiple signals

**Characteristics**:
- Contextual relevance scoring (0-0.3)
- Linguistic pattern analysis (0-0.3)
- Semantic clarity assessment (0-0.4)
- Best relationship extraction capabilities
- Balanced accuracy and speed (1-3 seconds typical)

**When to Use**: Complex contracts, multi-party agreements, documents with intricate entity relationships

#### 3. Unified Strategy (`unified`)
**Approach**: Single-pass comprehensive extraction
- All entity types processed simultaneously
- Optimized for speed and efficiency
- Minimum confidence threshold: 0.6
- No iterative refinement - single definitive pass

**Characteristics**:
- Fastest processing (<1 second typical)
- Good accuracy for straightforward documents
- Balanced precision and recall
- Optimal for high-volume processing

**When to Use**: Batch processing, real-time applications, simple documents, API integrations

### Strategy Performance Comparison

| Strategy | Processing Time | Accuracy | Entity Relationships | Best Use Case |
|----------|-----------------|----------|---------------------|---------------|
| `multipass` | 3-5 seconds | Highest (95%+) | Moderate | Critical documents |
| `ai_enhanced` | 1-3 seconds | High (90-95%) | Excellent | Complex documents |
| `unified` | <1 second | Good (85-90%) | Basic | High-volume processing |

### Strategy Auto-Selection

When `extraction_strategy` is not specified, the system automatically selects:
- **`multipass`**: For documents >10KB or when `max_entities` >100
- **`ai_enhanced`**: For documents with `enable_relationships=true` 
- **`unified`**: For documents <5KB or when `extraction_mode=hybrid`

**Request Body Example:**
```json
{
  "document_id": "legal_brief_001",
  "content": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held that state laws establishing separate public schools for the races are unconstitutional. Chief Justice Warren delivered the opinion of the Court.",
  "extraction_mode": "hybrid",
  "extraction_strategy": "ai_enhanced",
  "confidence_threshold": 0.7,
  "entity_types": ["case_citations", "court_names", "judges", "constitutional_references"],
  "relationship_types": ["CITES", "PRESIDES_OVER", "DECIDED_ON"],
  "relationship_categories": ["legal_precedent", "party_litigation"],
  "document_metadata": {
    "document_type": "court_opinion",
    "jurisdiction": "federal",
    "court_level": "supreme",
    "filing_date": "1954-05-17",
    "practice_area": "civil_rights"
  },
  "chunk_size": 5000,
  "enable_relationships": true,
  "max_entities": 100,
  "max_relationships": 50,
  "context_window": 300
}
```

**Successful Response (200 OK):**
```json
{
  "extraction_id": "ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "document_id": "legal_brief_001",
  "extraction_mode": "hybrid",
  "processing_time_ms": 1250,
  "entities": [
    {
      "id": "ent_12345678-90ab-cdef-1234-567890abcdef",
      "text": "Brown v. Board of Education",
      "cleaned_text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "entity_type": "CASE_LAW",
      "entity_subtype": "supreme_court_case",
      "confidence_score": 0.98,
      "extraction_method": "regex_with_ai_validation",
      "position": {
        "start": 3,
        "end": 30,
        "line_number": 1,
        "context_start": 0,
        "context_end": 80
      },
      "attributes": {
        "case_name": "Brown v. Board of Education",
        "court_name": "Supreme Court of the United States",
        "court_level": "supreme",
        "jurisdiction": "federal",
        "canonical_name": "Brown v. Board of Education of Topeka",
        "bluebook_abbreviation": "Brown",
        "alternate_names": ["Brown I"]
      },
      "ai_enhancements": [
        "canonical_name_resolution",
        "bluebook_format_validation",
        "parallel_citation_discovery"
      ],
      "context_snippet": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court",
      "validation_notes": [
        "Confirmed as landmark civil rights case",
        "Bluebook format validated and enhanced"
      ],
      "created_at": "2025-07-29T10:30:15Z"
    },
    {
      "id": "ent_23456789-01bc-def2-3456-789012bcdef3",
      "text": "Chief Justice Warren",
      "cleaned_text": "Chief Justice Warren",
      "entity_type": "JUDGE",
      "entity_subtype": "chief_justice",
      "confidence_score": 0.96,
      "extraction_method": "regex_with_ai_enhancement",
      "position": {
        "start": 157,
        "end": 177,
        "line_number": 1
      },
      "attributes": {
        "judge_title": "Chief Justice",
        "judge_name": "Earl Warren",
        "court_name": "Supreme Court of the United States",
        "appointment_type": "federal"
      },
      "created_at": "2025-07-29T10:30:15Z"
    }
  ],
  "citations": [
    {
      "id": "cit_34567890-12cd-ef34-5678-901234cdef45",
      "original_text": "347 U.S. 483 (1954)",
      "cleaned_citation": "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "citation_type": "CASE_CITATION",
      "confidence_score": 0.99,
      "extraction_method": "regex_with_ai_enhancement",
      "position": {
        "start": 32,
        "end": 51
      },
      "components": {
        "case_name": "Brown v. Board of Education",
        "volume": "347",
        "reporter": "U.S.",
        "page": "483",
        "year": "1954"
      },
      "bluebook_compliant": true,
      "parallel_citations": [
        "74 S. Ct. 686 (1954)",
        "98 L. Ed. 873 (1954)"
      ],
      "authority_weight": 1.0,
      "created_at": "2025-07-29T10:30:15Z"
    }
  ],
  "relationships": [
    {
      "id": "rel_45678901-23de-f456-7890-123456def567",
      "source_entity_id": "ent_12345678-90ab-cdef-1234-567890abcdef",
      "target_entity_id": "ent_23456789-01bc-def2-3456-789012bcdef3",
      "relationship_type": "decided_by",
      "confidence_score": 0.95,
      "evidence_text": "Chief Justice Warren delivered the opinion of the Court",
      "extraction_method": "ai_discovered",
      "created_at": "2025-07-29T10:30:15Z"
    }
  ],
  "processing_stats": {
    "total_entities": 15,
    "total_citations": 8,
    "total_relationships": 12,
    "processing_time_ms": 1250,
    "regex_entities": 12,
    "ai_enhanced_entities": 3,
    "confidence_distribution": {
      "high_confidence": 11,
      "medium_confidence": 3,
      "low_confidence": 1
    },
    "entity_type_counts": {
      "CASE_LAW": 8,
      "COURT": 3,
      "JUDGE": 2,
      "CONSTITUTIONAL_PROVISION": 2
    }
  },
  "quality_metrics": {
    "entity_completeness": 0.95,
    "legal_accuracy": 0.98,
    "bluebook_compliance": 0.92,
    "contextual_coherence": 0.89,
    "extraction_precision": 0.94
  }
}
```

**Async Processing Response (202 Accepted):**
```json
{
  "extraction_id": "ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "document_id": "legal_brief_001",
  "estimated_completion": "2025-07-29T10:32:00Z",
  "progress": 25,
  "message": "Entity extraction in progress. Use GET /extract/{extraction_id}/status to check progress."
}
```

## Chunked Entity Extraction Endpoint

### POST /extract/chunk

Extract entities from a single chunk using multi-pass extraction strategy. This endpoint is designed for chunked extraction where documents are processed by the chunking service first, then each chunk is processed with contextual information.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chunk_id` | string | Yes | Unique chunk identifier |
| `chunk_content` | string | Yes | Chunk content to extract entities from |
| `whole_document` | string | Yes | Complete document for context |
| `document_id` | string | Yes | Document ID this chunk belongs to |
| `chunk_index` | integer | Yes | Index of this chunk in the document |
| `extraction_pass` | string | No | Extraction pass: `actors`, `citations`, or `concepts` (default: `actors`) |
| `prompt_template` | string | No | Optional custom prompt template for extraction |
| `max_tokens` | integer | No | Maximum tokens for LLM response (uses config default if not specified) |
| `temperature` | float | No | Temperature for LLM (default: 0.0) |
| `entity_types` | array | No | Specific entity types to extract in this pass |
| `metadata` | object | No | Additional metadata for the extraction |
| `passes` | array | No | List of pass numbers (1-7) to execute. None means use profile default |
| `use_registry` | boolean | No | Use entity registry for cross-chunk deduplication (default: true) |
| `parallel_execution` | boolean | No | Execute passes in parallel for better performance (default: true) |
| `max_workers` | integer | No | Maximum parallel workers for extraction passes (default: 4, max: 7) |
| `extraction_profile` | string | No | Extraction profile: default, fast, citations, entities, temporal, discovery, litigation, contract, minimal, debug |
| `enable_multipass` | boolean | No | Enable multi-pass extraction strategy (7 passes) (default: false) |

**Request Body Example:**
```json
{
  "chunk_id": "chunk_001",
  "chunk_content": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held that state laws establishing separate public schools for the races are unconstitutional.",
  "whole_document": "The complete legal document text for context...",
  "document_id": "legal_brief_001",
  "chunk_index": 0,
  "extraction_pass": "citations",
  "enable_multipass": true,
  "extraction_profile": "citations",
  "max_workers": 4,
  "entity_types": ["CASE_CITATION", "COURT"]
}
```

**Successful Response (200 OK):**
```json
{
  "chunk_id": "chunk_001",
  "document_id": "legal_brief_001",
  "chunk_index": 0,
  "extraction_pass": "multipass",
  "entities": [
    {
      "entity_type": "CASE_CITATION",
      "text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "confidence": 0.98,
      "start_position": 3,
      "end_position": 51,
      "context": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court",
      "extraction_method": "ai_multipass",
      "metadata": {
        "chunk_id": "chunk_001",
        "extraction_pass": "multipass",
        "chunk_index": "0"
      }
    }
  ],
  "processing_time_ms": 850.5,
  "token_usage": {
    "prompt_tokens": 245,
    "completion_tokens": 89,
    "total_tokens": 334
  },
  "confidence_score": 0.85,
  "metadata": {
    "request_id": "req_12345",
    "entity_count": 1,
    "extraction_method": "ai_multipass",
    "profile_used": "citations"
  },
  "multipass_metrics": {
    "total_passes_executed": 7,
    "successful_passes": 7,
    "failed_passes": 0,
    "total_entities_extracted": 15,
    "unique_entities": 12,
    "duplicates_removed": 3,
    "total_processing_time_ms": 2400,
    "parallel_execution_time_ms": 850,
    "pass_metrics": {
      "1": {
        "entities_found": 3,
        "processing_time_ms": 120,
        "confidence_avg": 0.92
      }
    }
  },
  "passes_executed": [1, 2, 3, 4, 5, 6, 7],
  "extraction_profile_used": "citations"
}
```

## Extraction Profile Management

### GET /extraction-profiles

Get available extraction profiles and their configurations for multi-pass extraction.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/extraction-profiles
```

**Response:**
```json
{
  "total_profiles": 10,
  "profiles": {
    "default": {
      "name": "Default Profile",
      "description": "Balanced extraction with all passes enabled",
      "enabled_passes": [1, 2, 3, 4, 5, 6, 7],
      "parallel_execution": true,
      "max_workers": 4,
      "use_registry": true,
      "timeout_per_pass": 30,
      "retry_count": 2
    },
    "fast": {
      "name": "Fast Extraction",
      "description": "Quick extraction with essential passes only",
      "enabled_passes": [1, 4, 6],
      "parallel_execution": true,
      "max_workers": 6,
      "use_registry": false,
      "timeout_per_pass": 15,
      "retry_count": 1
    },
    "citations": {
      "name": "Citation Focused",
      "description": "Optimized for legal citations and references",
      "enabled_passes": [1, 2, 3],
      "parallel_execution": true,
      "max_workers": 3,
      "use_registry": true,
      "timeout_per_pass": 45,
      "retry_count": 3
    }
  },
  "pass_descriptions": {
    "1": "Case citations and references",
    "2": "Statutory citations and codes",
    "3": "Regulatory citations",
    "4": "Named entities (persons, organizations)",
    "5": "Courts and judges",
    "6": "Dates, times, and deadlines",
    "7": "Catch-all for missed entities and concepts"
  },
  "performance_settings": {
    "max_concurrent_chunks": 10,
    "chunk_timeout_seconds": 300,
    "retry_backoff_multiplier": 1.5
  },
  "pass_defaults": {
    "temperature": 0.1,
    "max_tokens": 1024,
    "confidence_threshold": 0.7
  }
}
```

### GET /extract/{extraction_id}/status

Check the status and progress of an extraction job with detailed processing information.

**Path Parameters:**
- `extraction_id`: Unique extraction identifier (UUID)

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/extract/ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890/status
```

**Response:**
```json
{
  "extraction_id": "ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "progress": 75,
  "current_stage": "ai_enhancement",
  "stages_completed": ["document_parsing", "regex_extraction"],
  "stages_remaining": ["relationship_extraction", "validation"],
  "estimated_completion": "2025-07-29T10:35:00Z",
  "processing_stats": {
    "entities_found": 12,
    "citations_found": 5,
    "elapsed_time_ms": 2100
  },
  "created_at": "2025-07-29T10:30:00Z",
  "last_updated": "2025-07-29T10:32:30Z"
}
```

**Status Values:**
- `queued`: Extraction request queued for processing
- `processing`: Extraction in progress
- `completed`: Extraction completed successfully
- `failed`: Extraction failed with errors
- `cancelled`: Extraction cancelled by user request

### GET /extract/{extraction_id}

Retrieve completed extraction results with full entity details.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/extract/ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response:**
Same format as successful POST /extract response.

### DELETE /extract/{extraction_id}

Cancel a running extraction or delete completed results.

**Response:**
```json
{
  "extraction_id": "ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "cancelled",
  "message": "Extraction cancelled successfully",
  "timestamp": "2025-07-29T10:30:00Z"
}
```

## Performance Profile Management Endpoints

### GET /api/v1/profiles

List all available performance profiles and their current status.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/profiles
```

**Response:**
```json
{
  "profiles": [
    {
      "profile": "breakthrough",
      "is_active": true,
      "is_loaded": true,
      "model_status": "loaded",
      "avg_response_time_ms": 176.4,
      "total_operations": 1250,
      "memory_usage_mb": 4832
    },
    {
      "profile": "speed_optimized",
      "is_active": false,
      "is_loaded": false,
      "model_status": "not_loaded",
      "avg_response_time_ms": 0,
      "total_operations": 0,
      "memory_usage_mb": 0
    }
  ],
  "recommendations": [
    {
      "profile": "breakthrough",
      "reason": "176ms SS tier - optimal balance"
    }
  ]
}
```

### POST /api/v1/profiles/{profile_name}/activate

Activate a specific performance profile.

**Request:**
```bash
curl -X POST "http://10.10.0.87:8007/api/v1/profiles/speed_optimized/activate"
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully activated profile: speed_optimized",
  "previous_profile": "breakthrough",
  "new_profile": "speed_optimized",
  "initialization_time_ms": 2340
}
```

### POST /api/v1/profiles/{profile_name}/benchmark

Benchmark a specific performance profile.

**Request:**
```bash
curl -X POST "http://10.10.0.87:8007/api/v1/profiles/breakthrough/benchmark" \
  -H "Content-Type: application/json" \
  -d '{"test_iterations": 10}'
```

**Response:**
```json
{
  "profile": "breakthrough",
  "avg_response_time_ms": 164.2,
  "min_response_time_ms": 145.1,
  "max_response_time_ms": 198.7,
  "success_rate": 1.0,
  "throughput_tokens_per_second": 45.6,
  "memory_usage_mb": 4832,
  "test_iterations": 10,
  "error_count": 0,
  "benchmark_timestamp": "2025-08-20T10:30:00Z"
}
```

### GET /api/v1/profiles/recommendations

Get performance profile recommendations based on workload type.

**Query Parameters:**
- `workload_type`: Type of workload (`general`, `speed`, `batch`, `memory`, `quality`)

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/profiles/recommendations?workload_type=speed"
```

**Response:**
```json
{
  "workload_type": "speed",
  "recommendations": [
    {
      "profile": "speed_optimized",
      "reason": "Optimized for sub-100ms response times"
    },
    {
      "profile": "breakthrough",
      "reason": "176ms SS tier performance as fallback"
    }
  ]
}
```

## Pattern Management Endpoints

✅ **FULLY INTEGRATED**: These endpoints now provide complete access to the PatternLoader system with 286 patterns from YAML files. All patterns are mapped to EntityType enum values and integrated with the extraction system through our entity type mapping layer.

### GET /patterns

List all available extraction patterns with metadata and performance statistics.

**Query Parameters:**
- `pattern_type`: Filter by pattern type (e.g., `federal_supreme_court`)
- `jurisdiction`: Filter by jurisdiction (e.g., `federal`, `california`)
- `entity_types`: Filter patterns that extract specific entity types

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/patterns?jurisdiction=federal&entity_types=case_citations"
```

**Response:**
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
    },
    {
      "name": "federal_district_courts",
      "type": "federal_district_courts",
      "jurisdiction": "federal",
      "confidence": 0.94,
      "entity_types": ["COURT", "CASE_LAW"],
      "pattern_count": 8,
      "last_updated": "2025-07-29T08:00:00Z"
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

### GET /patterns/detailed

Get comprehensive details of all regex patterns from YAML files with full metadata.

**Query Parameters:**
- `category`: Filter by pattern category (e.g., `case_citations`, `statute_citations`)
- `entity_type`: Filter by entity type (e.g., `JUDGE`, `CASE_CITATIONS`)

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/patterns/detailed"

# Filter by category
curl "http://10.10.0.87:8007/api/v1/patterns/detailed?category=case_citations"

# Filter by entity type
curl "http://10.10.0.87:8007/api/v1/patterns/detailed?entity_type=JUDGE"
```

**Response:**
```json
{
  "total_patterns": 286,
  "patterns_by_category": {
    "case_citations": [
      {
        "pattern_id": "case_citations.full_case_with_reporter",
        "entity_type": "CASE_CITATIONS",
        "pattern": "\\b[A-Z][a-zA-Z]+(?:\\s+[A-Za-z][a-zA-Z]+){0,8}...",
        "description": "Enhanced case citation patterns...",
        "examples": ["Brown v. Board, 347 U.S. 483 (1954)"],
        "flags": [],
        "source_file": "/srv/luris/be/entity-extraction-service/src/patterns/client/case_citations.yaml",
        "category": "case_citations",
        "confidence": 0.95
      }
    ]
  },
  "entity_types": ["CASE_CITATIONS", "JUDGE", "STATUTE_CITATION", ...],
  "statistics": {
    "total_patterns": 286,
    "patterns_from_yaml": 286,
    "loader_statistics": {
      "total_groups": 14,
      "total_patterns_from_yaml": 283,
      "confidence_distribution": {
        "0.8-0.9": 112,
        "0.9-1.0": 173
      },
      "entity_type_distribution": {
        "STATE_STATUTES": 21,
        "JUDGE": 12,
        ...
      }
    }
  }
}
```

This endpoint provides:
- All 286 regex patterns loaded from YAML files
- Complete regex pattern strings for each pattern
- Confidence scores for pattern matching
- Examples for each pattern
- Source file information
- Comprehensive statistics about pattern distribution

### GET /patterns/{pattern_name}

Get detailed information about a specific pattern.

**Response:**
```json
{
  "name": "supreme_court_citations",
  "type": "federal_supreme_court",
  "jurisdiction": "federal",
  "description": "Complete pattern library for U.S. Supreme Court citations and entities",
  "version": "1.0",
  "confidence": 0.98,
  "entity_types": ["CASE_LAW", "CONSTITUTIONAL_PROVISION"],
  "bluebook_compliance": "22nd_edition",
  "pattern_details": {
    "case_citations": 3,
    "justice_patterns": 2,
    "procedural_patterns": 2,
    "constitutional_patterns": 1
  },
  "validation_rules": {
    "year_range": {
      "min_year": 1789,
      "max_year": 2025
    },
    "volume_ranges": {
      "us_reports": {
        "min_volume": 1,
        "max_volume": 600
      }
    }
  },
  "examples": [
    {
      "text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "expected_entities": 1,
      "entity_type": "CASE_LAW"
    }
  ]
}
```

### GET /patterns/library

**NEW ENDPOINT** - Browse all patterns with filtering capabilities using the enhanced PatternLoader system.

**Query Parameters:**
- `entity_type`: Filter by specific entity type (e.g., `JUDGE`, `COURT`, `CASE_CITATION`)
- `min_confidence`: Minimum confidence threshold (0.0-1.0)
- `group`: Filter by pattern group/file name
- `limit`: Maximum patterns to return (default: 100, max: 500)
- `offset`: Pagination offset (default: 0)

**Request:**
```bash
# Get all patterns for JUDGE entity type
curl "http://10.10.0.87:8007/api/v1/patterns/library?entity_type=JUDGE&limit=5"

# Get high-confidence patterns
curl "http://10.10.0.87:8007/api/v1/patterns/library?min_confidence=0.95"

# Browse patterns with pagination
curl "http://10.10.0.87:8007/api/v1/patterns/library?limit=10&offset=20"
```

**Response:**
```json
{
  "patterns": [
    {
      "name": "judicial_entities.circuit_judges_list",
      "entity_type": "JUDGE",
      "confidence": 0.97,
      "pattern_preview": "\\b(?:CHAGARES|JORDAN|HARDIMAN|SHWARTZ...)...",
      "example_count": 3,
      "group": "judicial_entities"
    }
  ],
  "total_count": 12,
  "metadata": {
    "total_groups": 14,
    "entity_types_covered": 126,
    "average_confidence": 0.93,
    "confidence_distribution": {
      "0.9-1.0": 173,
      "0.8-0.9": 112,
      "0.7-0.8": 1
    },
    "filters_applied": {
      "entity_type": "JUDGE",
      "min_confidence": null,
      "group": null
    }
  }
}
```

### GET /patterns/comprehensive

**NEW ENDPOINT** - Get detailed information about all patterns including full regex, examples, metadata, and dependencies.

**Query Parameters:**
- `entity_type`: Filter by specific entity type
- `include_full_patterns`: Include complete pattern strings (default: true)
- `include_statistics`: Include detailed statistics (default: true)

**Request:**
```bash
# Get comprehensive details for all patterns
curl "http://10.10.0.87:8007/api/v1/patterns/comprehensive"

# Get detailed patterns for COURT entity type
curl "http://10.10.0.87:8007/api/v1/patterns/comprehensive?entity_type=COURT"
```

**Response:**
```json
{
  "patterns": [
    {
      "name": "specialized_court_citations.bankruptcy_citation",
      "pattern": "(?P<case_name>(?P<plaintiff>[A-Z][a-zA-Z]+...)\\s*,\\s*(?P<volume>\\d{1,4})\\s+B\\.R\\.\\s+(?P<page>\\d{1,4})",
      "entity_type": "COURT",
      "original_entity_type": "SPECIALIZED_COURTS",
      "confidence": 0.94,
      "examples": [
        "123 B.R. 456 (Bankr. S.D.N.Y. 2023)",
        "456 B.R. 789 (Bankr. C.D. Cal. 2022)"
      ],
      "components": {
        "case_name": "Full case name with parties",
        "volume": "Bankruptcy Reporter volume number",
        "page": "Starting page number"
      },
      "metadata": {
        "pattern_type": "specialized_court_citations",
        "jurisdiction": "federal",
        "court_level": "bankruptcy",
        "bluebook_compliance": "22nd_edition",
        "description": "Enhanced case citation patterns...",
        "file_path": "/srv/luris/be/entity-extraction-service/src/patterns/specialized/bankruptcy_courts.yaml"
      },
      "dependencies": [],
      "validation_rules": {},
      "group": "specialized_court_citations"
    }
  ],
  "total_count": 33,
  "statistics": {
    "total_patterns": 286,
    "total_groups": 14,
    "patterns_by_entity_type": {
      "COURT": 33,
      "JUDGE": 12,
      "CASE_CITATION": 45
    },
    "confidence_distribution": {
      "0.9-1.0": 173,
      "0.8-0.9": 112
    }
  }
}
```

### GET /patterns/inspect/{pattern_name}

**NEW ENDPOINT** - Get complete details about a specific pattern by name.

**Path Parameters:**
- `pattern_name`: Full pattern name using dot notation (e.g., `judicial_entities.circuit_judges_list`)

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/patterns/inspect/judicial_entities.circuit_judges_list"
```

**Response:**
```json
{
  "name": "judicial_entities.circuit_judges_list",
  "pattern": "\\b(?:CHAGARES|JORDAN|HARDIMAN|SHWARTZ|KRAUSE|RESTREPO|BIBAS|PORTER|MATEY|PHIPPS|FREEMAN|MONTGOMERY-REEVES),?\\s+(?:Chief\\s+Judge|Circuit\\s+Judge)",
  "entity_type": "JUDGE",
  "confidence": 0.97,
  "examples": [
    "CHAGARES, Chief Judge",
    "HARDIMAN, Circuit Judge",
    "AMBRO, Circuit Judge"
  ],
  "components": {
    "judge_names": "List of Third Circuit Court of Appeals judges",
    "judicial_title": "Title indicating judicial role"
  },
  "metadata": {
    "pattern_type": "judicial_entities",
    "jurisdiction": "federal",
    "court_level": "appellate",
    "bluebook_compliance": "22nd_edition",
    "description": "Patterns for identifying judges, justices, and judicial officers",
    "file_path": "/srv/luris/be/entity-extraction-service/src/patterns/federal/appellate_courts.yaml",
    "pattern_version": "1.0"
  },
  "dependencies": [],
  "validation_rules": {},
  "group": "judicial_entities"
}
```

### GET /patterns/statistics

Get comprehensive statistics and analytics about the pattern library.

This endpoint provides detailed analytics including jurisdiction breakdown, Bluebook compliance, coverage analysis, and pattern library health status. It's useful for monitoring pattern quality and identifying gaps in coverage.

**Request:**
```bash
curl http://10.10.0.87:8007/api/v1/patterns/statistics
```

**Response:**
```json
{
  "summary": {
    "total_patterns": 295,
    "total_pattern_groups": 53,
    "total_entity_types": 31,
    "covered_entity_types": 28,
    "total_examples": 487,
    "average_confidence": 0.85,
    "jurisdiction_distribution": {
      "federal": 145,
      "state": 89,
      "international": 12,
      "unknown": 49
    },
    "bluebook_compliant_patterns": 234,
    "validation_pass_rate": 92.5
  },
  "jurisdiction_breakdown": {
    "federal": 145,
    "state_specific": {
      "CA": 23,
      "NY": 18,
      "TX": 15,
      "FL": 12,
      "IL": 8,
      "PA": 7,
      "OH": 6
    },
    "state_agnostic": 45,
    "international": 12,
    "unknown": 49,
    "total_state_patterns": 89
  },
  "bluebook_compliance": {
    "bluebook_22nd_edition": 178,
    "bluebook_21st_edition": 45,
    "bluebook_20th_edition": 11,
    "non_bluebook": 32,
    "unknown_compliance": 29,
    "compliance_percentage": 90.2
  },
  "coverage_analysis": {
    "total_entity_types": 31,
    "covered_entity_types": 28,
    "uncovered_entity_types": ["FOOTNOTES", "APPENDIX_REFERENCES", "DISSENT_MARKERS"],
    "coverage_percentage": 90.3,
    "entity_type_details": [
      {
        "entity_type": "CASE_CITATIONS",
        "pattern_count": 45,
        "has_ai_enhancement": true,
        "has_regex_patterns": true,
        "confidence_avg": 0.92,
        "examples_count": 89,
        "jurisdictions": ["federal", "state", "international"]
      },
      {
        "entity_type": "JUDGE",
        "pattern_count": 23,
        "has_ai_enhancement": true,
        "has_regex_patterns": true,
        "confidence_avg": 0.87,
        "examples_count": 34,
        "jurisdictions": ["federal", "state"]
      }
    ],
    "high_coverage_types": ["CASE_CITATIONS", "STATUTE_CITATIONS", "COURT_NAMES"],
    "low_coverage_types": ["DISSENT_MARKERS", "CONCURRENCE_MARKERS", "LEGAL_STANDARDS"]
  },
  "confidence_distribution": {
    "very_low": 12,
    "low": 34,
    "medium": 67,
    "high": 112,
    "very_high": 70,
    "average": 0.85,
    "std_dev": 0.12
  },
  "validation_status": {
    "total_patterns": 295,
    "valid_patterns": 273,
    "invalid_patterns": 22,
    "validation_errors": {
      "pattern_123": ["Low confidence score"],
      "pattern_456": ["Missing examples", "Invalid regex"]
    },
    "untested_patterns": 45,
    "test_coverage": 84.7
  },
  "performance_metrics": {
    "average_compilation_time_ms": 2.3,
    "average_match_time_ms": 0.5,
    "cache_hit_rate": 0.85,
    "memory_usage_mb": 50.0,
    "patterns_in_cache": 295,
    "cache_size_limit": 1000
  },
  "pattern_groups": [
    {
      "group_name": "federal_supreme_court",
      "pattern_count": 12,
      "pattern_type": "case_citations",
      "jurisdiction": "federal",
      "bluebook_compliance": "22nd_edition",
      "version": "1.0",
      "last_updated": "2024-12-15T10:00:00Z",
      "file_path": "patterns/federal/supreme_court.yaml",
      "dependencies": []
    }
  ],
  "library_health": {
    "status": "healthy",
    "issues": [],
    "warnings": ["Low entity type coverage: 45.2% for dissent markers"],
    "last_reload": "2024-12-20T14:30:00Z",
    "reload_frequency_hours": 24.0,
    "pattern_conflicts": [],
    "duplicate_patterns": []
  },
  "metadata": {
    "generated_at": "2024-12-20T14:35:00Z",
    "pattern_loader_version": "2.0",
    "patterns_directory": "/srv/luris/be/entity-extraction-service/src/patterns",
    "dependency_count": 23,
    "ai_enhancement_available": true,
    "supported_jurisdictions": ["federal", "CA", "NY", "TX", "FL", "international"]
  }
}
```

## Relationship Pattern Endpoints

The Entity Extraction Service supports extraction of **46 different relationship types** across 6 categories, enabling comprehensive analysis of connections between legal entities. Relationship extraction is powered by the same YAML pattern system that provides entity extraction capabilities.

### Relationship Categories

| Category | Relationship Count | Description |
|----------|-------------------|-------------|
| **Contractual & Financial** | 10 | Contract parties, payments, obligations, damages |
| **Party & Litigation** | 10 | Legal representation, opposing parties, judicial assignments |
| **Legal Precedent** | 8 | Case citations, precedent following, judicial decisions |
| **Statutory & Regulatory** | 9 | Law amendments, regulatory implementation, compliance |
| **Temporal & Procedural** | 9 | Filing dates, deadlines, procedural sequences |
| **Jurisdictional & Venue** | 9 | Court jurisdiction, venue, geographic location |

### GET /api/v1/relationships

List all available relationship types with descriptions and examples.

**Query Parameters:**
- `category`: Filter by relationship category (e.g., `contractual_financial`, `party_litigation`)
- `source_entity_type`: Filter by source entity type
- `target_entity_type`: Filter by target entity type
- `include_examples`: Include example patterns (default: true)
- `include_indicators`: Include relationship indicators (default: false)

**Request:**
```bash
# Get all relationships
curl "http://10.10.0.87:8007/api/v1/relationships"

# Get relationships for specific category
curl "http://10.10.0.87:8007/api/v1/relationships?category=legal_precedent"

# Get relationships with source entity type COURT
curl "http://10.10.0.87:8007/api/v1/relationships?source_entity_type=COURT"

# Get relationships with full indicators
curl "http://10.10.0.87:8007/api/v1/relationships?include_indicators=true"
```

**Response (200 OK):**
```json
{
  "total_relationships": 46,
  "relationships_by_category": {
    "contractual_financial": {
      "count": 10,
      "relationships": [
        {
          "relationship_type": "PARTY_TO",
          "description": "Party to a contract or agreement",
          "source_entity": "CONTRACT_PARTY",
          "target_entity": "CONTRACT",
          "category": "contractual_financial",
          "indicators": ["party to", "signatory to", "entered into", "executed", "agrees to"],
          "examples": [
            "ABC Corp is party to the Agreement",
            "Parties entered into contract",
            "Smith executed the settlement"
          ]
        },
        {
          "relationship_type": "OBLIGATED_TO_PAY",
          "description": "Party obligated to pay amount",
          "source_entity": "PARTY",
          "target_entity": "MONETARY_AMOUNT",
          "category": "contractual_financial",
          "indicators": ["owes", "obligated to pay", "liable for", "must pay", "ordered to pay"],
          "examples": [
            "Defendant owes $2.5 million",
            "Party obligated to pay damages",
            "Ordered to pay $100,000 in fees"
          ]
        }
      ]
    },
    "legal_precedent": {
      "count": 8,
      "relationships": [
        {
          "relationship_type": "CITES",
          "description": "Case citing another case",
          "source_entity": "CASE_CITATION",
          "target_entity": "CASE_CITATION",
          "category": "legal_precedent",
          "indicators": ["citing", "cited in", "as noted in", "following", "see", "accord"],
          "examples": [
            "Smith v. Jones, citing Brown v. Board of Education",
            "Following the precedent set in Miranda v. Arizona",
            "As noted in Marbury v. Madison"
          ]
        }
      ]
    }
  },
  "categories": ["contractual_financial", "party_litigation", "legal_precedent", "statutory_regulatory", "temporal_procedural", "jurisdictional_venue"],
  "metadata": {
    "total_indicators": 234,
    "source_entity_types": ["CASE_CITATION", "COURT", "PARTY", "STATUTE_CITATION", "ATTORNEY", "JUDGE"],
    "target_entity_types": ["CASE_CITATION", "COURT", "PARTY", "CONTRACT", "MONETARY_AMOUNT", "JURISDICTION"],
    "pattern_version": "1.0",
    "last_updated": "2025-10-14T00:00:00Z"
  }
}
```

### GET /api/v1/relationships/{type}

Get detailed information about a specific relationship type.

**Path Parameters:**
- `type`: The relationship type name (e.g., `CITES`, `REPRESENTS`, `PARTY_TO`)

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/relationships/CITES"
```

**Response (200 OK):**
```json
{
  "relationship_type": "CITES",
  "description": "Case citing another case",
  "category": "legal_precedent",
  "source_entity": "CASE_CITATION",
  "target_entity": "CASE_CITATION",
  "indicators": [
    "citing",
    "cited in",
    "as noted in",
    "following",
    "see",
    "accord"
  ],
  "examples": [
    "Smith v. Jones, citing Brown v. Board of Education",
    "Following the precedent set in Miranda v. Arizona",
    "As noted in Marbury v. Madison"
  ],
  "extraction_confidence": 0.92,
  "pattern_count": 6,
  "usage_frequency": "very_high",
  "related_relationships": ["FOLLOWS", "DISTINGUISHES", "OVERRULES"],
  "metadata": {
    "jurisdiction": "federal",
    "source_file": "/srv/luris/be/entity-extraction-service/src/patterns/relationships/legal_precedent.yaml",
    "pattern_version": "1.0"
  }
}
```

**Response (404 Not Found):**
```json
{
  "error": {
    "code": "RELATIONSHIP_TYPE_NOT_FOUND",
    "message": "Relationship type 'INVALID_TYPE' not found",
    "available_types": ["CITES", "REPRESENTS", "PARTY_TO", "..."]
  }
}
```

### GET /api/v1/relationships/categories

Get summary of relationship categories with counts and descriptions.

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/relationships/categories"
```

**Response (200 OK):**
```json
{
  "total_categories": 6,
  "total_relationships": 46,
  "categories": {
    "contractual_financial": {
      "name": "Contractual and Financial Relationships",
      "count": 10,
      "description": "Relationships involving contracts, agreements, and financial matters",
      "relationship_types": [
        "PARTY_TO",
        "OBLIGATED_TO_PAY",
        "ENTITLED_TO",
        "GUARANTEES",
        "BREACHES",
        "SETTLES_FOR",
        "INDEMNIFIES",
        "DAMAGES_FOR",
        "PAYS_TO",
        "INTEREST_RATE_ON"
      ],
      "common_entities": ["CONTRACT_PARTY", "PARTY", "CONTRACT", "MONETARY_AMOUNT", "DAMAGES"]
    },
    "party_litigation": {
      "name": "Party and Litigation Relationships",
      "count": 10,
      "description": "Relationships between parties, attorneys, and courts in litigation",
      "relationship_types": [
        "REPRESENTS",
        "EMPLOYS",
        "SUES",
        "APPEALS_FROM",
        "PRESIDES_OVER",
        "OPPOSES",
        "JOINS",
        "SETTLES_WITH",
        "WITNESS_FOR",
        "FILES_IN"
      ],
      "common_entities": ["ATTORNEY", "PARTY", "PLAINTIFF", "DEFENDANT", "JUDGE", "COURT"]
    },
    "legal_precedent": {
      "name": "Legal Precedent and Case Relationships",
      "count": 8,
      "description": "Relationships between cases, precedents, and legal rulings",
      "relationship_types": [
        "CITES",
        "OVERRULES",
        "DISTINGUISHES",
        "AFFIRMS",
        "REVERSES",
        "REMANDS",
        "FOLLOWS",
        "MODIFIES"
      ],
      "common_entities": ["CASE_CITATION", "COURT"]
    },
    "statutory_regulatory": {
      "name": "Statutory and Regulatory Relationships",
      "count": 9,
      "description": "Relationships between statutes, regulations, and legal provisions",
      "relationship_types": [
        "AMENDS",
        "IMPLEMENTS",
        "INTERPRETS",
        "APPLIES",
        "SUPERSEDES",
        "REFERENCES",
        "CODIFIES",
        "VIOLATES",
        "ENFORCES"
      ],
      "common_entities": ["STATUTE_CITATION", "REGULATION_CITATION", "CASE_CITATION", "COURT", "PARTY", "FEDERAL_AGENCY"]
    },
    "temporal_procedural": {
      "name": "Temporal and Procedural Relationships",
      "count": 9,
      "description": "Relationships involving time, dates, and procedural sequences",
      "relationship_types": [
        "FILED_ON",
        "DECIDED_ON",
        "EFFECTIVE_AS_OF",
        "EXPIRES_ON",
        "PRECEDES",
        "DEADLINE_FOR",
        "DURING",
        "RESPONDS_TO",
        "SCHEDULED_FOR"
      ],
      "common_entities": ["MOTION", "CASE_CITATION", "STATUTE_CITATION", "CONTRACT", "FILING_DATE", "DECISION_DATE", "DEADLINE"]
    },
    "jurisdictional_venue": {
      "name": "Jurisdictional and Venue Relationships",
      "count": 9,
      "description": "Relationships involving jurisdiction, venue, and geographic elements",
      "relationship_types": [
        "HAS_JURISDICTION",
        "LOCATED_IN",
        "VENUE_IN",
        "TRANSFERRED_TO",
        "RESIDES_IN",
        "GOVERNS_IN",
        "CIRCUIT_INCLUDES",
        "EXERCISES_OVER",
        "REMOVED_TO"
      ],
      "common_entities": ["COURT", "PARTY", "JURISDICTION", "DISTRICT", "VENUE", "STATUTE_CITATION", "CIRCUITS"]
    }
  },
  "usage_statistics": {
    "most_common_relationships": [
      {"type": "CITES", "usage_count": 15420},
      {"type": "REPRESENTS", "usage_count": 8932},
      {"type": "FILED_ON", "usage_count": 7654}
    ],
    "most_common_source_entities": [
      {"entity": "CASE_CITATION", "relationship_count": 8},
      {"entity": "COURT", "relationship_count": 7},
      {"entity": "PARTY", "relationship_count": 6}
    ]
  }
}
```

### GET /api/v1/relationships/statistics

Get comprehensive statistics about relationship extraction patterns.

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/relationships/statistics"
```

**Response (200 OK):**
```json
{
  "summary": {
    "total_relationship_types": 46,
    "total_categories": 6,
    "total_indicators": 234,
    "average_indicators_per_type": 5.1,
    "total_examples": 138,
    "supported_jurisdictions": ["federal"]
  },
  "category_distribution": {
    "contractual_financial": 10,
    "party_litigation": 10,
    "legal_precedent": 8,
    "statutory_regulatory": 9,
    "temporal_procedural": 9,
    "jurisdictional_venue": 9
  },
  "entity_pair_statistics": {
    "total_unique_source_entities": 15,
    "total_unique_target_entities": 18,
    "most_connected_entities": [
      {
        "entity": "CASE_CITATION",
        "as_source": 8,
        "as_target": 8,
        "total_connections": 16
      },
      {
        "entity": "COURT",
        "as_source": 7,
        "as_target": 5,
        "total_connections": 12
      },
      {
        "entity": "PARTY",
        "as_source": 6,
        "as_target": 7,
        "total_connections": 13
      }
    ]
  },
  "confidence_distribution": {
    "high_confidence": 32,
    "medium_confidence": 12,
    "low_confidence": 2,
    "average_confidence": 0.89
  },
  "pattern_metrics": {
    "total_pattern_files": 6,
    "patterns_per_category": {
      "contractual_financial": 10,
      "party_litigation": 10,
      "legal_precedent": 8,
      "statutory_regulatory": 9,
      "temporal_procedural": 9,
      "jurisdictional_venue": 9
    },
    "indicators_by_category": {
      "contractual_financial": 50,
      "party_litigation": 46,
      "legal_precedent": 36,
      "statutory_regulatory": 41,
      "temporal_procedural": 37,
      "jurisdictional_venue": 24
    }
  },
  "extraction_performance": {
    "average_extraction_time_ms": 450,
    "success_rate": 0.94,
    "total_extractions": 32106,
    "cache_hit_rate": 0.87
  },
  "metadata": {
    "generated_at": "2025-10-14T10:30:00Z",
    "pattern_version": "1.0",
    "patterns_directory": "/srv/luris/be/entity-extraction-service/src/patterns/relationships"
  }
}
```

### POST /api/v1/extract/relationships

✅ **Status: FULLY IMPLEMENTED** (as of P1-2 fix)

Extract relationships from document content using relationship patterns and AI-enhanced detection.

This endpoint was previously stub status but is now **fully operational** with complete relationship extraction capabilities including pattern-based detection, AI enhancement, and comprehensive validation.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Unique document identifier |
| `content` | string | Yes | Document text content (max 1MB) |
| `relationship_types` | array | No | Specific relationship types to extract (default: all 46 types) |
| `categories` | array | No | Relationship categories to extract |
| `confidence_threshold` | float | No | Minimum confidence score (0.0-1.0, default: 0.7) |
| `include_entity_context` | boolean | No | Include full entity information in results (default: true) |
| `extraction_mode` | string | No | Extraction mode: `pattern`, `ai`, or `hybrid` (default: `hybrid`) |
| `max_relationships` | integer | No | Maximum relationships to return (default: unlimited) |

**Supported Relationship Types:**

**Contractual & Financial (10 types):**
- `PARTY_TO`, `OBLIGATED_TO_PAY`, `ENTITLED_TO`, `GUARANTEES`, `BREACHES`, `SETTLES_FOR`, `INDEMNIFIES`, `DAMAGES_FOR`, `PAYS_TO`, `INTEREST_RATE_ON`

**Party & Litigation (10 types):**
- `REPRESENTS`, `EMPLOYS`, `SUES`, `APPEALS_FROM`, `PRESIDES_OVER`, `OPPOSES`, `JOINS`, `SETTLES_WITH`, `WITNESS_FOR`, `FILES_IN`

**Legal Precedent (8 types):**
- `CITES`, `OVERRULES`, `DISTINGUISHES`, `AFFIRMS`, `REVERSES`, `REMANDS`, `FOLLOWS`, `MODIFIES`

**Statutory & Regulatory (9 types):**
- `AMENDS`, `IMPLEMENTS`, `INTERPRETS`, `APPLIES`, `SUPERSEDES`, `REFERENCES`, `CODIFIES`, `VIOLATES`, `ENFORCES`

**Temporal & Procedural (9 types):**
- `FILED_ON`, `DECIDED_ON`, `EFFECTIVE_AS_OF`, `EXPIRES_ON`, `PRECEDES`, `DEADLINE_FOR`, `DURING`, `RESPONDS_TO`, `SCHEDULED_FOR`

**Jurisdictional & Venue (9 types):**
- `HAS_JURISDICTION`, `LOCATED_IN`, `VENUE_IN`, `TRANSFERRED_TO`, `RESIDES_IN`, `GOVERNS_IN`, `CIRCUIT_INCLUDES`, `EXERCISES_OVER`, `REMOVED_TO`

**Request Body Example:**
```json
{
  "document_id": "legal_opinion_001",
  "content": "In Brown v. Board of Education, 347 U.S. 483 (1954), Chief Justice Warren delivered the opinion. The Court cited Plessy v. Ferguson, 163 U.S. 537 (1896), while distinguishing it from the facts at hand. The Supreme Court reversed the lower court's decision and remanded for further proceedings.",
  "relationship_types": ["CITES", "DISTINGUISHES", "REVERSES", "REMANDS"],
  "categories": ["legal_precedent"],
  "confidence_threshold": 0.75,
  "include_entity_context": true,
  "extraction_mode": "hybrid"
}
```

**Successful Response (200 OK):**
```json
{
  "extraction_id": "rel_ext_12345678-90ab-cdef-1234-567890abcdef",
  "status": "completed",
  "document_id": "legal_opinion_001",
  "processing_time_ms": 620,
  "relationships": [
    {
      "id": "rel_12345678-90ab-cdef-1234-567890abcdef",
      "relationship_type": "CITES",
      "category": "legal_precedent",
      "source_entity": {
        "id": "ent_source_001",
        "text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
        "entity_type": "CASE_CITATION",
        "position": {"start": 3, "end": 51}
      },
      "target_entity": {
        "id": "ent_target_001",
        "text": "Plessy v. Ferguson, 163 U.S. 537 (1896)",
        "entity_type": "CASE_CITATION",
        "position": {"start": 112, "end": 151}
      },
      "confidence_score": 0.96,
      "evidence_text": "The Court cited Plessy v. Ferguson",
      "extraction_method": "pattern_with_ai_validation",
      "indicators_matched": ["cited"],
      "context": "In Brown v. Board of Education, 347 U.S. 483 (1954), Chief Justice Warren delivered the opinion. The Court cited Plessy v. Ferguson, 163 U.S. 537 (1896), while distinguishing it from the facts at hand.",
      "metadata": {
        "bidirectional": false,
        "temporal_order": "source_after_target",
        "legal_significance": "precedent_reference"
      },
      "created_at": "2025-10-14T10:30:15Z"
    },
    {
      "id": "rel_23456789-01bc-def2-3456-789012bcdef3",
      "relationship_type": "DISTINGUISHES",
      "category": "legal_precedent",
      "source_entity": {
        "id": "ent_source_001",
        "text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
        "entity_type": "CASE_CITATION",
        "position": {"start": 3, "end": 51}
      },
      "target_entity": {
        "id": "ent_target_001",
        "text": "Plessy v. Ferguson, 163 U.S. 537 (1896)",
        "entity_type": "CASE_CITATION",
        "position": {"start": 112, "end": 151}
      },
      "confidence_score": 0.94,
      "evidence_text": "while distinguishing it from the facts at hand",
      "extraction_method": "ai_discovered",
      "indicators_matched": ["distinguishing"],
      "context": "The Court cited Plessy v. Ferguson, 163 U.S. 537 (1896), while distinguishing it from the facts at hand.",
      "metadata": {
        "bidirectional": false,
        "legal_significance": "precedent_distinction"
      },
      "created_at": "2025-10-14T10:30:15Z"
    },
    {
      "id": "rel_34567890-12cd-ef34-5678-901234cdef45",
      "relationship_type": "REVERSES",
      "category": "legal_precedent",
      "source_entity": {
        "id": "ent_court_001",
        "text": "Supreme Court",
        "entity_type": "COURT",
        "position": {"start": 164, "end": 177}
      },
      "target_entity": {
        "id": "ent_court_002",
        "text": "lower court",
        "entity_type": "COURT",
        "position": {"start": 191, "end": 202}
      },
      "confidence_score": 0.97,
      "evidence_text": "The Supreme Court reversed the lower court's decision",
      "extraction_method": "pattern_match",
      "indicators_matched": ["reversed"],
      "context": "The Supreme Court reversed the lower court's decision and remanded for further proceedings.",
      "metadata": {
        "bidirectional": false,
        "hierarchical": true,
        "appellate_action": "reversal"
      },
      "created_at": "2025-10-14T10:30:15Z"
    }
  ],
  "processing_stats": {
    "total_relationships": 4,
    "relationships_by_category": {
      "legal_precedent": 4
    },
    "relationships_by_type": {
      "CITES": 1,
      "DISTINGUISHES": 1,
      "REVERSES": 1,
      "REMANDS": 1
    },
    "confidence_distribution": {
      "high_confidence": 3,
      "medium_confidence": 1,
      "low_confidence": 0
    },
    "extraction_methods": {
      "pattern_match": 2,
      "ai_discovered": 1,
      "pattern_with_ai_validation": 1
    }
  },
  "quality_metrics": {
    "relationship_completeness": 0.95,
    "entity_linkage_accuracy": 0.98,
    "contextual_coherence": 0.92,
    "extraction_precision": 0.96
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_RELATIONSHIP_TYPE",
    "message": "Invalid relationship type specified: 'INVALID_TYPE'",
    "details": {
      "invalid_types": ["INVALID_TYPE"],
      "valid_types": ["CITES", "REPRESENTS", "PARTY_TO", "..."]
    }
  }
}
```

## Document Routing Endpoints

The Entity Extraction Service provides intelligent document routing capabilities that analyze document characteristics and automatically determine the optimal processing strategy. The routing system considers document size, complexity, and content type to select the most efficient extraction approach.

### Routing Strategies

The service supports multiple extraction strategies optimized for different document sizes:

- **Single Pass** (very small docs <5K chars): Consolidated extraction in a single prompt
- **Three Wave** (small-medium docs 5K-50K chars): Optimized 3-wave extraction
- **Three Wave Chunked** (medium-large docs 50K-150K chars): Chunked processing with wave system
- **Eight Wave Fallback** (critical accuracy): Full 8-wave extraction for maximum accuracy

### POST /api/v1/route

**Route Document for Optimal Processing Strategy**

Analyzes document characteristics and determines the optimal extraction strategy based on size, complexity, and content type.

**Request:**
```json
{
  "document_text": "Legal document text...",
  "document_id": "doc-123",
  "metadata": {
    "document_type": "brief",
    "jurisdiction": "federal"
  },
  "strategy_override": null
}
```

**Response:**
```json
{
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "routing_decision": {
    "strategy": "three_wave",
    "prompt_version": "v3",
    "chunk_config": null,
    "document_size": 45000,
    "size_category": "small",
    "expected_accuracy": 0.90,
    "estimated_cost": 0.018,
    "estimated_tokens": 11250,
    "processing_time_estimate_ms": 1000,
    "rationale": "Document size (45K chars) fits within three-wave processing limits with high accuracy"
  },
  "is_valid": true,
  "warnings": [],
  "timestamp": 1704067200.5
}
```

**Example:**
```bash
curl -X POST http://10.10.0.87:8007/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "Legal document text...",
    "document_id": "doc-123"
  }'
```

**Path Parameters:** None

**Query Parameters:** None

**Request Body Parameters:**
- `document_text` (string, required): Full document text to analyze
- `document_id` (string, optional): Document identifier for tracking
- `metadata` (object, optional): Additional document metadata
- `strategy_override` (string, optional): Force specific strategy ("single_pass", "three_wave", "three_wave_chunked", "eight_wave_fallback")

**Response Fields:**
- `success` (boolean): Whether routing succeeded
- `request_id` (string): Unique request identifier
- `routing_decision` (object): Complete routing decision with strategy, cost estimates, and configuration
- `is_valid` (boolean): Whether the routing decision is valid
- `warnings` (array): Any warnings about the routing decision
- `timestamp` (float): Unix timestamp of response

### GET /api/v1/strategies

**Get Available Processing Strategies**

Returns detailed information about all available document processing strategies including their characteristics, use cases, and performance metrics.

**Response:**
```json
{
  "strategies": {
    "single_pass": {
      "name": "Single Pass",
      "description": "Single consolidated prompt for very small documents (<5K chars)",
      "entity_types": 15,
      "expected_accuracy": 0.87,
      "cost_range": "$0.003-$0.005",
      "processing_time": "~500ms",
      "use_cases": [
        "Short motions",
        "Simple contracts",
        "Brief correspondence"
      ]
    },
    "three_wave": {
      "name": "Three Wave Optimized",
      "description": "3-wave extraction for small to medium documents",
      "entity_types": 34,
      "expected_accuracy": 0.90,
      "cost_range": "$0.015-$0.020",
      "processing_time": "~850-1200ms",
      "use_cases": [
        "Complaints",
        "Briefs",
        "Standard legal documents"
      ]
    },
    "three_wave_chunked": {
      "name": "Three Wave Chunked",
      "description": "3-wave extraction with document chunking for large documents",
      "entity_types": 34,
      "expected_accuracy": 0.91,
      "cost_range": "Variable (based on chunks)",
      "processing_time": "2-60+ seconds",
      "use_cases": [
        "Long briefs",
        "Depositions",
        "Trial transcripts"
      ]
    },
    "eight_wave_fallback": {
      "name": "Eight Wave Fallback",
      "description": "Full 8-wave extraction for maximum accuracy (fallback)",
      "entity_types": 34,
      "expected_accuracy": 0.93,
      "cost_range": "$0.025-$0.030",
      "processing_time": "~2000ms",
      "use_cases": [
        "Critical documents requiring maximum accuracy"
      ]
    }
  },
  "default_strategy": "automatic routing based on document size"
}
```

**Example:**
```bash
curl http://10.10.0.87:8007/api/v1/strategies
```

**Strategy Selection Logic:**
- Documents <5K chars → `single_pass`
- Documents 5K-50K chars → `three_wave`
- Documents 50K-150K chars → `three_wave_chunked`
- Documents >150K chars → `three_wave_chunked` with aggressive chunking
- Critical accuracy requirements → `eight_wave_fallback` (manual override)

### GET /api/v1/thresholds

**Get Document Size Thresholds**

Returns document size thresholds used for automatic routing decisions, including character ranges, token ranges, and corresponding strategies.

**Response:**
```json
{
  "thresholds": {
    "very_small": {
      "char_range": "0-5,000",
      "token_range": "0-1,250",
      "strategy": "single_pass",
      "pages": "~1-2 pages"
    },
    "small": {
      "char_range": "5,001-50,000",
      "token_range": "1,251-12,500",
      "strategy": "three_wave",
      "pages": "~2-20 pages"
    },
    "medium": {
      "char_range": "50,001-150,000",
      "token_range": "12,501-37,500",
      "strategy": "three_wave_chunked",
      "pages": "~20-60 pages"
    },
    "large": {
      "char_range": ">150,000",
      "token_range": ">37,500",
      "strategy": "three_wave_chunked",
      "pages": ">60 pages"
    }
  },
  "context_limit": {
    "max_tokens": 32768,
    "safety_margin": 2000,
    "effective_limit": 30768
  }
}
```

**Example:**
```bash
curl http://10.10.0.87:8007/api/v1/thresholds
```

**Threshold Categories:**
- **Very Small** (0-5K chars): Ultra-fast single-pass processing
- **Small** (5K-50K chars): Optimized 3-wave extraction
- **Medium** (50K-150K chars): Chunked processing required
- **Large** (>150K chars): Aggressive chunking with parallel processing

**Context Window Management:**
- Maximum context: 32,768 tokens (Qwen3-VL-8B model limit)
- Safety margin: 2,000 tokens for response generation
- Effective limit: 30,768 tokens for input processing

### GET /api/v1/health (Routing)

**Router Health Check**

Checks if the document router is initialized and ready to process routing requests. Returns router configuration and health status.

**Response:**
```json
{
  "status": "healthy",
  "router_initialized": true,
  "max_context": 32768,
  "safety_margin": 2000,
  "adaptive_enabled": true,
  "timestamp": 1704067200.5
}
```

**Example:**
```bash
curl http://10.10.0.87:8007/api/v1/health
```

**Health Status Values:**
- `healthy`: Router initialized and ready
- `unhealthy`: Router not initialized or error state

**Configuration Details:**
- `max_context`: Maximum token context window
- `safety_margin`: Reserved tokens for response generation
- `adaptive_enabled`: Whether adaptive routing is active
- `timestamp`: Current server timestamp

**Error Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "router_initialized": false,
  "error": "Document router not initialized",
  "timestamp": 1704067200.5
}
```

## Configuration Endpoint

The service provides a configuration endpoint that exposes current service settings including extraction modes, timeouts, rate limits, and performance settings (non-sensitive values only).

### GET /api/v1/config

**Get Service Configuration**

Returns current service configuration including extraction modes, timeouts, limits, and feature flags. This endpoint exposes only non-sensitive configuration values.

**Response:**
```json
{
  "extraction_modes": ["ai_enhanced", "multi_pass"],
  "default_extraction_mode": "ai_enhanced",
  "default_confidence_threshold": 0.7,
  "max_content_length": 1000000,
  "max_context_window": 32768,
  "max_concurrent_extractions": 5,
  "processing_timeout_seconds": 1800,
  "ai_timeout_seconds": 120,
  "ai_max_retries": 3,
  "enable_ai_fallback": true,
  "enable_pattern_caching": true,
  "pattern_cache_size": 1000,
  "supported_entity_types_count": 195,
  "store_extraction_results": true,
  "extraction_retention_days": 30,
  "enable_performance_monitoring": true,
  "enable_rate_limiting": true,
  "rate_limit_requests": 100,
  "max_request_size": 10485760
}
```

**Example:**
```bash
curl http://10.10.0.87:8007/api/v1/config
```

**Configuration Categories:**

**Extraction Settings:**
- `extraction_modes`: Available extraction modes
- `default_extraction_mode`: Default mode for extraction requests
- `default_confidence_threshold`: Minimum confidence for entity filtering
- `max_content_length`: Maximum document length (characters)
- `max_context_window`: Maximum LLM context window (tokens)
- `max_concurrent_extractions`: Maximum parallel extraction tasks

**Timeout & Retry Settings:**
- `processing_timeout_seconds`: Maximum time for extraction (30 minutes)
- `ai_timeout_seconds`: AI model timeout (2 minutes)
- `ai_max_retries`: Maximum retry attempts for AI operations
- `enable_ai_fallback`: Whether to fall back on AI failures

**Pattern Management:**
- `enable_pattern_caching`: Whether pattern caching is enabled
- `pattern_cache_size`: Maximum cached patterns
- `supported_entity_types_count`: Total supported entity types (195+)

**Storage & Retention:**
- `store_extraction_results`: Whether to store extraction results
- `extraction_retention_days`: Days to retain extraction results

**Performance & Rate Limiting:**
- `enable_performance_monitoring`: Performance metrics collection
- `enable_rate_limiting`: API rate limiting
- `rate_limit_requests`: Requests per minute limit
- `max_request_size`: Maximum request size (bytes)

**Error Response (500 Internal Server Error):**
```json
{
  "detail": "Failed to retrieve service configuration: <error message>"
}
```

## vLLM Integration Endpoints

### Model Backend Configuration

The Entity Extraction Service supports both llama_cpp and vLLM backends for AI-enhanced processing. vLLM provides superior performance through dynamic batching and optimized GPU utilization.

### GET /api/v1/model/backend

Get current model backend configuration and status.

**Response:**
```json
{
  "current_backend": "llama_cpp",
  "available_backends": ["llama_cpp", "vllm"],
  "backend_status": {
    "llama_cpp": {
      "enabled": true,
      "status": "ready",
      "model": "Qwen/Qwen3-VL-8B-Instruct-FP8-GGUF",
      "performance_profile": "breakthrough_optimized",
      "response_time_ms": 176,
      "memory_usage_gb": 8.2
    },
    "vllm": {
      "enabled": false,
      "status": "not_configured",
      "server_url": null,
      "expected_performance": {
        "latency_ms": "<50",
        "throughput_rps": "100+"
      }
    }
  },
  "migration_status": "planning"
}
```

### POST /api/v1/model/backend/switch

Switch between model backends (llama_cpp to vLLM or vice versa).

**Request Body:**
```json
{
  "target_backend": "vllm",
  "vllm_config": {
    "server_url": "http://10.10.0.87:8080",
    "api_key": "entity-extraction-service",
    "performance_tier": "balanced"
  },
  "enable_fallback": true,
  "validation_tests": true
}
```

**Response:**
```json
{
  "switch_status": "success",
  "previous_backend": "llama_cpp",
  "current_backend": "vllm",
  "switch_duration_ms": 2450,
  "validation_results": {
    "health_check": "passed",
    "performance_test": "passed",
    "compatibility_test": "passed",
    "estimated_performance_improvement": "8.5x"
  },
  "rollback_available": true
}
```

### GET /api/v1/model/vllm/config

Get current vLLM configuration and adaptive settings.

**Response:**
```json
{
  "vllm_config": {
    "server_url": "http://10.10.0.87:8080",
    "model": "Qwen/Qwen3-VL-8B-Instruct-FP8",
    "performance_tier": "balanced",
    "adaptive_config": {
      "small_documents": {
        "max_model_len": 1024,
        "max_num_seqs": 32,
        "target_latency_ms": 25
      },
      "medium_documents": {
        "max_model_len": 2048,
        "max_num_seqs": 16,
        "target_latency_ms": 75
      },
      "large_documents": {
        "max_model_len": 4096,
        "max_num_seqs": 8,
        "target_latency_ms": 150
      }
    }
  },
  "server_status": {
    "healthy": true,
    "model_loaded": true,
    "gpu_utilization_percent": 85,
    "memory_utilization_percent": 78,
    "active_requests": 4,
    "queue_depth": 0
  }
}
```

### POST /api/v1/model/vllm/config

Update vLLM configuration settings.

**Request Body:**
```json
{
  "performance_tier": "lightning",
  "adaptive_settings": {
    "enable_document_size_adaptation": true,
    "enable_load_based_scaling": true,
    "memory_utilization_target": 0.85
  },
  "generation_params": {
    "temperature": 0.05,
    "top_p": 0.85,
    "max_tokens": 512
  }
}
```

**Response:**
```json
{
  "update_status": "success",
  "previous_config": {
    "performance_tier": "balanced"
  },
  "current_config": {
    "performance_tier": "lightning",
    "expected_performance": {
      "target_latency_ms": 25,
      "expected_throughput_rps": 200
    }
  },
  "performance_impact": {
    "estimated_latency_improvement": "3x",
    "estimated_throughput_improvement": "2.5x",
    "memory_usage_change": "+0.5GB"
  }
}
```

### GET /api/v1/model/vllm/performance

Get detailed vLLM performance metrics and adaptive behavior.

**Response:**
```json
{
  "performance_metrics": {
    "latency": {
      "p50_ms": 45,
      "p95_ms": 78,
      "p99_ms": 125,
      "avg_ms": 52
    },
    "throughput": {
      "requests_per_second": 85,
      "tokens_per_second": 1240,
      "batch_efficiency": 0.87
    },
    "resource_utilization": {
      "gpu_utilization_percent": 92,
      "gpu_memory_used_gb": 10.2,
      "gpu_memory_total_gb": 16.0,
      "memory_utilization_percent": 64
    }
  },
  "adaptive_behavior": {
    "document_size_distribution": {
      "small": 0.45,
      "medium": 0.35,
      "large": 0.20
    },
    "configuration_adjustments_last_hour": [
      {
        "timestamp": "2025-01-15T10:30:00Z",
        "reason": "High load detected",
        "adjustment": "Increased max_num_seqs to 20",
        "performance_impact": "+15% throughput"
      }
    ],
    "optimization_recommendations": [
      {
        "type": "memory_optimization",
        "recommendation": "Consider increasing GPU memory utilization to 0.95",
        "expected_benefit": "10% latency improvement"
      }
    ]
  }
}
```

### POST /api/v1/model/vllm/benchmark

Run comprehensive vLLM performance benchmark.

**Request Body:**
```json
{
  "benchmark_type": "comprehensive",
  "test_duration_seconds": 300,
  "concurrency_levels": [1, 2, 4, 8, 16, 32],
  "document_types": ["small", "medium", "large"],
  "iterations_per_test": 10
}
```

**Response:**
```json
{
  "benchmark_id": "bench_001",
  "status": "running",
  "estimated_completion_time": "2025-01-15T11:15:00Z",
  "progress": {
    "completed_tests": 0,
    "total_tests": 180,
    "current_test": {
      "concurrency": 1,
      "document_type": "small",
      "iteration": 1
    }
  }
}
```

### GET /api/v1/model/vllm/benchmark/{benchmark_id}

Get benchmark results.

**Response:**
```json
{
  "benchmark_id": "bench_001",
  "status": "completed",
  "results": {
    "overall_performance": {
      "peak_throughput_rps": 156,
      "optimal_concurrency": 16,
      "best_latency_ms": 28,
      "performance_tier_achieved": "SS_Lightning"
    },
    "configuration_recommendations": [
      {
        "workload_type": "real_time_ui",
        "recommended_config": {
          "performance_tier": "lightning",
          "max_num_seqs": 8,
          "target_latency_ms": 25
        }
      },
      {
        "workload_type": "batch_processing",
        "recommended_config": {
          "performance_tier": "throughput",
          "max_num_seqs": 32,
          "target_latency_ms": 150
        }
      }
    ],
    "comparison_with_llama_cpp": {
      "latency_improvement": "8.2x",
      "throughput_improvement": "12.5x",
      "memory_efficiency": "15% better"
    }
  }
}
```

## vLLM Configuration Options

### Performance Tiers

The vLLM integration supports multiple performance tiers for different use cases:

#### Lightning Tier (Sub-50ms)
**Use Case**: Real-time UI components, instant entity extraction

**Configuration:**
```json
{
  "performance_tier": "lightning",
  "max_model_len": 1024,
  "max_num_seqs": 8,
  "max_num_batched_tokens": 2048,
  "gpu_memory_utilization": 0.80,
  "quantization": "fp16",
  "target_latency_ms": 25
}
```

#### Balanced Tier (Sub-100ms)
**Use Case**: Production API endpoints, document processing pipeline

**Configuration:**
```json
{
  "performance_tier": "balanced",
  "max_model_len": 2048,
  "max_num_seqs": 16,
  "max_num_batched_tokens": 4096,
  "gpu_memory_utilization": 0.90,
  "quantization": "fp16",
  "target_latency_ms": 75
}
```

#### Throughput Tier (Sub-200ms)
**Use Case**: Bulk document processing, high-volume extraction

**Configuration:**
```json
{
  "performance_tier": "throughput",
  "max_model_len": 4096,
  "max_num_seqs": 32,
  "max_num_batched_tokens": 8192,
  "gpu_memory_utilization": 0.95,
  "quantization": "fp16",
  "target_latency_ms": 150
}
```

### Feature Flags

Enable vLLM features through configuration:

```json
{
  "feature_flags": {
    "use_vllm": false,
    "enable_vllm_fallback": true,
    "enable_adaptive_batching": true,
    "enable_dynamic_config": true,
    "enable_performance_monitoring": true,
    "enable_a_b_testing": false
  }
}
```

### Environment Variables

Configure vLLM integration through environment variables:

```bash
# vLLM Backend Configuration
ENTITY_EXTRACTION_USE_VLLM=false
ENTITY_EXTRACTION_VLLM_SERVER_URL=http://10.10.0.87:8080
ENTITY_EXTRACTION_VLLM_API_KEY=entity-extraction-service
ENTITY_EXTRACTION_VLLM_PERFORMANCE_TIER=balanced

# Adaptive Configuration
ENTITY_EXTRACTION_VLLM_ENABLE_ADAPTIVE=true
ENTITY_EXTRACTION_VLLM_GPU_MEMORY_UTILIZATION=0.90
ENTITY_EXTRACTION_VLLM_MAX_NUM_SEQS=16

# Fallback Configuration
ENTITY_EXTRACTION_VLLM_ENABLE_FALLBACK=true
ENTITY_EXTRACTION_VLLM_FALLBACK_TIMEOUT_MS=5000
```

## Supported Entity Types

The service supports extraction of **272 legal entity and citation types** through the PatternLoader system:

### Current Coverage
- **160 EntityType enum values** - Legal entities like courts, judges, parties, documents
- **112 CitationType enum values** - Citations like case law, statutes, regulations  
- **43 entity types** actively have regex patterns (up from 0)
- **286 total patterns** loaded from YAML files
- **126 entity types** covered across all pattern categories

### How It Works
The service uses a sophisticated entity type mapping system that bridges pattern files with EntityType enums, ensuring all 286 patterns from YAML files are accessible through standard enum values.

### Primary Entity Types
- **case_citations**: Legal case citations in various formats
- **statute_citations**: Statutes, regulations, and codes  
- **court_names**: Court names and jurisdictions
- **judges**: Judge names and titles
- **attorneys**: Attorney and law firm names
- **parties**: Case parties, plaintiffs, defendants
- **dates**: Legal dates and deadlines
- **monetary_amounts**: Monetary amounts and damages
- **legal_doctrines**: Legal doctrines and principles
- **procedural_terms**: Procedural and jurisdictional terms

### Extended Entity Types
- **contracts**: Contract types and agreements
- **legal_references**: General legal references
- **jurisdictions**: Jurisdictional references
- **legal_standards**: Legal standards and tests
- **evidence_types**: Types of evidence
- **motion_types**: Legal motion types
- **filing_deadlines**: Court filing deadlines
- **legal_precedents**: Legal precedents
- **constitutional_references**: Constitutional references
- **regulatory_citations**: Regulatory citations
- **administrative_codes**: Administrative codes
- **local_ordinances**: Local ordinances
- **international_law**: International law references
- **treaty_references**: Treaty references
- **arbitration_clauses**: Arbitration clauses
- **settlement_terms**: Settlement terms
- **damages_calculations**: Damages calculations
- **legal_fees**: Legal fees
- **court_costs**: Court costs
- **legal_entities**: General legal entities

## Entity Type Discovery Endpoints

### GET /entity-types

**ENHANCED ENDPOINT** - Get comprehensive information about all supported entity and citation types with real pattern data from PatternLoader.

**Query Parameters:**
- `include_descriptions`: Include human-readable descriptions (default: true)
- `include_examples`: Include real examples from pattern files (default: false)

**Request:**
```bash
# Get all entity types with descriptions
curl "http://10.10.0.87:8007/api/v1/entity-types"

# Get entity types with real examples from patterns
curl "http://10.10.0.87:8007/api/v1/entity-types?include_examples=true"

# Get minimal entity type list
curl "http://10.10.0.87:8007/api/v1/entity-types?include_descriptions=false&include_examples=false"
```

**Response:**
```json
{
  "entity_types": [
    {
      "type": "COURT",
      "name": "Court",
      "category": "Courts and Judicial",
      "description": "Enhanced case citation patterns with precise pinpoint citation matching",
      "regex_supported": true,
      "ai_enhanced": true,
      "pattern_count": 33,
      "pattern_examples": [
        "123 B.R. 456 (Bankr. S.D.N.Y. 2023)",
        "456 B.R. 789 (Bankr. C.D. Cal. 2022)",
        "789 BR 123 (Bankr. D. Del. 2021)"
      ]
    },
    {
      "type": "JUDGE",
      "name": "Judge", 
      "category": "Courts and Judicial",
      "description": "Patterns for identifying judges, justices, and judicial officers",
      "regex_supported": true,
      "ai_enhanced": true,
      "pattern_count": 12,
      "pattern_examples": [
        "CHAGARES, Chief Judge",
        "HARDIMAN, Circuit Judge",
        "Pratter, District Judge"
      ]
    }
  ],
  "citation_types": [
    {
      "type": "CASE_CITATION",
      "name": "Case Citation",
      "category": "Case Citations",
      "description": "General case law citations",
      "regex_supported": true,
      "examples": ["Brown v. Board of Education, 347 U.S. 483 (1954)"],
      "pattern_count": 45,
      "pattern_examples": ["\\b[A-Z][a-zA-Z]+(?:\\s+[A-Za-z][a-zA-Z]+){0,8}..."]
    }
  ],
  "total_entity_types": 160,
  "total_citation_types": 112,
  "categories": {
    "Courts and Judicial": ["COURT", "JUDGE", "MAGISTRATE"],
    "Citation: Case Citations": ["CASE_CITATION", "FEDERAL_CASE_CITATION"]
  },
  "metadata": {
    "service_version": "2.0.0",
    "total_patterns_in_use": 286,
    "ai_enhancement_available": true,
    "pattern_loader_stats": {
      "total_patterns_loaded": 286,
      "total_pattern_groups": 14,
      "total_entity_types_with_patterns": 126
    }
  }
}
```

### GET /entity-types/categories

Get a summary of entity type categories with counts and capabilities.

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/entity-types/categories"
```

**Response:**
```json
{
  "entity_categories": {
    "Courts and Judicial": {
      "count": 8,
      "types": ["COURT", "JUDGE", "MAGISTRATE", "ARBITRATOR"],
      "has_regex": true,
      "has_ai_enhancement": true
    },
    "Legal Professionals": {
      "count": 8,
      "types": ["ATTORNEY", "LAW_FIRM", "PROSECUTOR"],
      "has_regex": true,
      "has_ai_enhancement": true
    }
  },
  "citation_categories": {
    "Case Citations": {
      "count": 12,
      "types": ["CASE_CITATION", "FEDERAL_CASE_CITATION"],
      "has_regex": true,
      "has_ai_enhancement": true
    }
  },
  "total_entity_categories": 18,
  "total_citation_categories": 11,
  "total_types": 272
}
```

### GET /entity-types/{entity_type}

Get detailed information about a specific entity or citation type.

**Path Parameters:**
- `entity_type`: The entity or citation type (e.g., 'COURT', 'CASE_CITATION')

**Request:**
```bash
curl "http://10.10.0.87:8007/api/v1/entity-types/COURT"
```

**Response:**
```json
{
  "type": "COURT",
  "name": "Court",
  "category": "Courts and Judicial",
  "description": "Enhanced case citation patterns with precise pinpoint citation matching",
  "is_entity": true,
  "is_citation": false,
  "regex_supported": true,
  "ai_enhanced": true,
  "extraction_modes": ["regex", "ai_enhanced", "hybrid"],
  "pattern_count": 33,
  "pattern_details": [
    {
      "name": "specialized_court_citations.bankruptcy_citation",
      "pattern": "(?P<case_name>(?P<plaintiff>[A-Z][a-zA-Z]+...)...",
      "confidence": 0.94,
      "examples": ["123 B.R. 456 (Bankr. S.D.N.Y. 2023)"]
    }
  ],
  "examples": [
    "123 B.R. 456 (Bankr. S.D.N.Y. 2023)",
    "456 B.R. 789 (Bankr. C.D. Cal. 2022)"
  ],
  "average_confidence": 0.91,
  "jurisdictions": ["federal", "state"],
  "pattern_types": ["specialized_court_citations", "bankruptcy_courts"]
}
```

## vLLM Troubleshooting

### Common vLLM Integration Issues

#### Issue: vLLM Server Connection Failed
**Error Message:**
```json
{
  "error": {
    "code": "VLLM_CONNECTION_ERROR",
    "message": "Failed to connect to vLLM server at http://10.10.0.87:8080",
    "details": {
      "server_url": "http://10.10.0.87:8080",
      "connection_timeout_ms": 5000,
      "retry_attempts": 3
    }
  }
}
```

**Solutions:**
1. **Check vLLM Server Status:**
   ```bash
   curl http://10.10.0.87:8080/health
   ```

2. **Start vLLM Server:**
   ```bash
   vllm serve Qwen/Qwen3-VL-8B-Instruct-FP8 \
     --host 0.0.0.0 \
     --port 8080 \
     --tensor-parallel-size 1 \
     --max-model-len 4096
   ```

3. **Verify Configuration:**
   ```bash
   curl http://10.10.0.87:8007/api/v1/model/vllm/config
   ```

#### Issue: GPU Memory Exhausted
**Error Message:**
```json
{
  "error": {
    "code": "VLLM_GPU_OOM",
    "message": "GPU out of memory during vLLM processing",
    "details": {
      "gpu_memory_required_gb": 12.5,
      "gpu_memory_available_gb": 8.0,
      "current_config": {
        "max_num_seqs": 32,
        "max_model_len": 4096
      }
    }
  }
}
```

**Solutions:**
1. **Reduce Memory Configuration:**
   ```json
   {
     "performance_tier": "memory_efficient",
     "max_num_seqs": 8,
     "max_model_len": 2048,
     "gpu_memory_utilization": 0.70
   }
   ```

2. **Enable Quantization:**
   ```json
   {
     "quantization": "int8",
     "gpu_memory_utilization": 0.75
   }
   ```

3. **Check GPU Memory:**
   ```bash
   nvidia-smi
   curl http://10.10.0.87:8007/api/v1/model/vllm/performance
   ```

#### Issue: Performance Degradation
**Symptoms:**
- Latency > 500ms consistently
- Throughput < 10 RPS
- High queue depth

**Diagnostic Steps:**
1. **Check Performance Metrics:**
   ```bash
   curl http://10.10.0.87:8007/api/v1/model/vllm/performance
   ```

2. **Analyze Configuration:**
   ```bash
   curl http://10.10.0.87:8007/api/v1/model/vllm/config
   ```

3. **Run Benchmark:**
   ```bash
   curl -X POST http://10.10.0.87:8007/api/v1/model/vllm/benchmark \
     -H "Content-Type: application/json" \
     -d '{"benchmark_type": "quick", "test_duration_seconds": 60}'
   ```

**Solutions:**
1. **Optimize for Current Workload:**
   - High small documents: Use `lightning` tier
   - Mixed document sizes: Use `balanced` tier  
   - Large documents: Use `throughput` tier

2. **Adjust Batching Configuration:**
   ```json
   {
     "adaptive_settings": {
       "enable_document_size_adaptation": true,
       "enable_load_based_scaling": true
     }
   }
   ```

#### Issue: Inconsistent Results vs llama_cpp
**Error Message:**
```json
{
  "error": {
    "code": "VLLM_COMPATIBILITY_ERROR",
    "message": "vLLM results differ significantly from llama_cpp baseline",
    "details": {
      "similarity_score": 0.45,
      "expected_similarity": 0.90,
      "differences_detected": ["entity_counts", "confidence_scores"]
    }
  }
}
```

**Solutions:**
1. **Verify Model Consistency:**
   ```bash
   # Check that both backends use same model
   curl http://10.10.0.87:8007/api/v1/model/backend
   ```

2. **Align Generation Parameters:**
   ```json
   {
     "generation_params": {
       "temperature": 0.1,
       "top_p": 0.9,
       "max_tokens": 1024
     }
   }
   ```

3. **Enable A/B Testing Mode:**
   ```json
   {
     "feature_flags": {
       "enable_a_b_testing": true,
       "a_b_split_ratio": 0.1
     }
   }
   ```

### Performance Optimization Guide

#### Step 1: Baseline Performance Assessment
```bash
# Get current performance metrics
curl http://10.10.0.87:8007/api/v1/model/vllm/performance

# Run comprehensive benchmark
curl -X POST http://10.10.0.87:8007/api/v1/model/vllm/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "benchmark_type": "comprehensive",
    "test_duration_seconds": 300
  }'
```

#### Step 2: Identify Performance Bottlenecks
- **GPU Utilization < 80%**: Increase batch size or concurrency
- **Memory Utilization > 95%**: Reduce model length or sequence count
- **Queue Depth > 10**: Increase server capacity or reduce request rate
- **Latency > Target**: Optimize configuration tier

#### Step 3: Apply Optimizations
```json
{
  "optimization_strategy": "performance_first",
  "adjustments": {
    "gpu_memory_utilization": 0.95,
    "max_num_seqs": 24,
    "enable_chunked_prefill": true,
    "quantization": "fp16"
  }
}
```

#### Step 4: Validate Improvements
```bash
# Compare before/after metrics
curl http://10.10.0.87:8007/api/v1/model/vllm/performance | jq '.performance_metrics'

# Run validation test using Wave System
curl -X POST http://10.10.0.87:8007/api/v2/process/extract \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "test_doc",
    "content": "Sample legal document content..."
  }'
```

### Health Monitoring

#### vLLM-Specific Health Checks
```bash
# Overall health
curl http://10.10.0.87:8007/api/v1/health/detailed

# vLLM server health
curl http://10.10.0.87:8080/health

# Performance health
curl http://10.10.0.87:8007/api/v1/model/vllm/performance
```

#### Key Metrics to Monitor
- **Latency P95**: Should be < target tier latency
- **Throughput**: Should meet workload requirements
- **GPU Utilization**: Should be 80-95%
- **Error Rate**: Should be < 1%
- **Queue Depth**: Should be < 10

#### Alert Conditions
```json
{
  "alert_thresholds": {
    "latency_p95_ms": 200,
    "throughput_rps": 10,
    "gpu_utilization_min": 60,
    "gpu_utilization_max": 98,
    "error_rate_max": 0.01,
    "queue_depth_max": 20
  }
}
```

## Error Handling

### HTTP Status Codes

- **200**: Success
- **400**: Bad Request (invalid parameters)
- **404**: Not Found (extraction ID not found)
- **422**: Unprocessable Entity (validation error)
- **500**: Internal Server Error
- **503**: Service Unavailable (dependencies down)

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "EXTRACTION_FAILED",
  "timestamp": 1693248000.123,
  "request_id": "req_123456"
}
```

### Common Error Codes

- `INVALID_EXTRACTION_MODE`: Invalid extraction mode specified
- `CONTENT_TOO_LARGE`: Content exceeds maximum size limit
- `EXTRACTION_TIMEOUT`: Processing timed out
- `LOCAL_AI_MODEL_NOT_LOADED`: Local AI model not loaded or failed to load
- `LOCAL_AI_GENERATION_FAILED`: Local AI generation encountered an error
- `GPU_MEMORY_INSUFFICIENT`: Insufficient GPU memory for current configuration
- `MODEL_LOADING_TIMEOUT`: Model loading exceeded timeout limit
- `PATTERN_COMPILATION_ERROR`: Error compiling regex patterns
- `DATABASE_ERROR`: Database operation failed
- `JSON_PARSING_FAILED`: AI response JSON parsing failed (resolved with new parser)
- `PATTERN_LOADER_DISCONNECT`: PatternLoader patterns not being used (architectural issue)
- `PROFILE_INITIALIZATION_FAILED`: Performance profile failed to initialize
- `PROFILE_NOT_FOUND`: Requested performance profile does not exist

## Performance

### Response Times (Local AI)
- **Regex extraction**: 50-200ms for typical documents
- **Local AI-enhanced extraction**: 176ms-1000ms depending on configuration profile
- **Hybrid extraction**: 200ms-1200ms for optimal results
- **Breakthrough performance**: ≤176ms with breakthrough_optimized profile

### Performance Tiers
- **SS Lightning** (≤100ms): speed_optimized profile
- **SS Ultra Fast** (100-250ms): breakthrough_optimized profile (default)
- **S Exceptional** (250-500ms): batch_optimized and memory_constrained profiles
- **A Fast** (500-1000ms): quality_focused profile

### Throughput
- **Concurrent requests**: Up to 64 simultaneous extractions (with n_parallel=64)
- **Document size**: Supports up to 1MB content per request
- **Rate limits**: 100 requests per minute per client
- **GPU acceleration**: Up to 64 GPU layers for maximum performance
- **Memory usage**: 3-12GB depending on configuration profile

## Integration Examples

### Basic Case Citation Extraction

Extract entities using the Wave System with intelligent routing:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: req_12345" \
  -d '{
    "document_id": "case_brief_001",
    "content": "The landmark case Brown v. Board of Education, 347 U.S. 483 (1954), established that separate educational facilities are inherently unequal. This decision overturned Plessy v. Ferguson, 163 U.S. 537 (1896).",
    "confidence_threshold": 0.8
  }'
```

### Supreme Court Opinion Extraction

Use Wave System for highest accuracy on critical documents:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "supreme_court_opinion",
    "content": "In Citizens United v. Federal Election Commission, 558 U.S. 310 (2010), Chief Justice Roberts and Justice Kennedy wrote for the majority. The Court held under the First Amendment that corporations have the same rights as individuals regarding political speech.",
    "confidence_threshold": 0.8
  }'
```

### Complex Court Opinion with Relationships

Use Wave System for comprehensive entity and relationship extraction:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "court_opinion_001",
    "content": "Chief Justice Roberts, writing for the majority in Citizens United v. FEC, 558 U.S. 310 (2010), held that political speech restrictions under Section 441b of the Bipartisan Campaign Reform Act violate the First Amendment. The Court awarded $2.5 million in damages.",
    "confidence_threshold": 0.7,
    "document_metadata": {
      "document_type": "court_opinion",
      "jurisdiction": "federal",
      "practice_area": "constitutional_law"
    }
  }'
```

### Contract Document Extraction

Use Wave System for contract entity extraction:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "batch_contract_001",
    "content": "This Employment Agreement between ABC Corp. and John Smith, effective January 1, 2024, provides for annual salary of $75,000. Termination notice must be given 30 days in advance.",
    "confidence_threshold": 0.6
  }'
```

### Settlement Agreement Extraction

Use Wave System for comprehensive extraction with specific focus areas:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "contract_001",
    "content": "This Settlement Agreement between Plaintiff Corporation and Defendant LLC, dated March 15, 2024, provides for payment of $500,000 within 30 days. Attorney fees of $125,000 shall be borne by Defendant.",
    "confidence_threshold": 0.75,
    "max_entities": 50
  }'
```

### Legal Precedent Relationship Extraction

Extract case citation relationships including citations, distinctions, and precedent following using Wave System Wave 4:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "supreme_court_opinion_001",
    "content": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court overruled Plessy v. Ferguson, 163 U.S. 537 (1896), citing Equal Protection Clause violations. The Court followed the precedent established in Sweatt v. Painter, 339 U.S. 629 (1950), while distinguishing it from Berea College v. Kentucky, 211 U.S. 45 (1908). Chief Justice Warren delivered the unanimous opinion.",
    "confidence_threshold": 0.75
  }'
```

**Expected Relationships Extracted:**
- **OVERRULES**: Brown v. Board → Plessy v. Ferguson (high confidence)
- **CITES**: Brown v. Board → Equal Protection Clause reference
- **FOLLOWS**: Brown v. Board → Sweatt v. Painter (precedent relationship)
- **DISTINGUISHES**: Brown v. Board → Berea College v. Kentucky (factual distinction)

### Contractual Relationship Extraction

Extract contract-related relationships including parties, obligations, and financial terms using Wave System:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "settlement_agreement_001",
    "content": "This Settlement Agreement between Plaintiff ABC Corporation and Defendant XYZ LLC, dated March 15, 2024, provides that Defendant is obligated to pay $2.5 million to Plaintiff within 30 days. ABC Corporation is party to this Agreement and agrees to release all claims. XYZ LLC indemnifies ABC Corporation against any third-party claims. The settlement amount includes $500,000 in attorney fees, which Defendant pays to Plaintiff counsel.",
    "confidence_threshold": 0.7
  }'
```

**Expected Relationships Extracted:**
- **PARTY_TO**: ABC Corporation → Settlement Agreement
- **PARTY_TO**: XYZ LLC → Settlement Agreement
- **OBLIGATED_TO_PAY**: XYZ LLC → $2.5 million
- **INDEMNIFIES**: XYZ LLC → ABC Corporation
- **PAYS_TO**: XYZ LLC → Plaintiff counsel
- **SETTLES_FOR**: Settlement Agreement → $2.5 million

### Party Litigation Relationship Extraction

Extract litigation relationships including representation, judicial assignments, and party opposition using Wave System:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "case_pleading_001",
    "content": "Plaintiff John Smith, represented by Smith & Associates law firm, sues Defendant ABC Corporation in the United States District Court for the Southern District of New York. Attorney Jane Doe of Jones Law Firm represents Defendant. The Honorable Judge Robert Miller presides over this case. The action was filed in the Southern District on January 15, 2024. Plaintiff opposes Defendant motion to dismiss.",
    "confidence_threshold": 0.75
  }'
```

**Expected Relationships Extracted:**
- **REPRESENTS**: Smith & Associates → John Smith (plaintiff representation)
- **REPRESENTS**: Jane Doe → ABC Corporation (defendant representation)
- **SUES**: John Smith → ABC Corporation (plaintiff action)
- **PRESIDES_OVER**: Judge Robert Miller → Case
- **FILES_IN**: John Smith → Southern District Court
- **OPPOSES**: Plaintiff → Defendant motion

### Multi-Category Relationship Extraction

Extract complex relationships spanning multiple categories for comprehensive document analysis using Wave System:

```bash
curl -X POST "http://10.10.0.87:8007/api/v2/process/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "court_decision_complex_001",
    "content": "In this case, Plaintiff Corporation sues Defendant LLC for breach of contract in the District Court, Southern District of New York, filed on June 1, 2023. Attorney Maria Rodriguez of Rodriguez & Partners represents Plaintiff. The Court applies Section 2-201 of the Uniform Commercial Code and cites Anderson v. Liberty Lobby, Inc., 477 U.S. 242 (1986). Judge Sarah Thompson presides over the case and reversed the Magistrate decision on summary judgment. The Court decided on December 15, 2023, that Defendant is obligated to pay $1.2 million in damages. This case follows the precedent established in Celotex Corp. v. Catrett, 477 U.S. 317 (1986).",
    "confidence_threshold": 0.7
  }'
```

**Expected Relationships Extracted (Multi-Category):**

**Party & Litigation:**
- REPRESENTS: Maria Rodriguez → Plaintiff Corporation
- SUES: Plaintiff Corporation → Defendant LLC
- PRESIDES_OVER: Judge Sarah Thompson → Case
- FILES_IN: Plaintiff → District Court Southern District NY

**Legal Precedent:**
- CITES: Current Case → Anderson v. Liberty Lobby
- FOLLOWS: Current Case → Celotex Corp. v. Catrett
- REVERSES: Judge Thompson → Magistrate decision

**Statutory & Regulatory:**
- APPLIES: Court → UCC Section 2-201
- INTERPRETS: Court → UCC provisions

**Temporal & Procedural:**
- FILED_ON: Case → June 1, 2023
- DECIDED_ON: Case → December 15, 2023

**Contractual & Financial:**
- OBLIGATED_TO_PAY: Defendant LLC → $1.2 million
- DAMAGES_FOR: $1.2 million → Breach of contract

### Check Extraction Status and Progress

```bash
curl "http://10.10.0.87:8007/api/v1/extract/ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890/status"
```

### Retrieve Completed Results

```bash
curl "http://10.10.0.87:8007/api/v1/extract/ext_a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### Get Pattern Information

```bash
# **NEW** - Browse patterns with filtering (PatternLoader integrated)
curl "http://10.10.0.87:8007/api/v1/patterns/library?entity_type=JUDGE&limit=5"

# **NEW** - Get comprehensive pattern details (PatternLoader integrated)
curl "http://10.10.0.87:8007/api/v1/patterns/comprehensive?entity_type=COURT"

# **NEW** - Inspect specific pattern
curl "http://10.10.0.87:8007/api/v1/patterns/inspect/judicial_entities.circuit_judges_list"

# List pattern summary (legacy endpoint)
curl "http://10.10.0.87:8007/api/v1/patterns"

# Get detailed patterns with full regex and metadata (legacy endpoint)  
curl "http://10.10.0.87:8007/api/v1/patterns/detailed"

# Filter detailed patterns by category (legacy endpoint)
curl "http://10.10.0.87:8007/api/v1/patterns/detailed?category=case_citations"

# Filter detailed patterns by entity type (legacy endpoint)
curl "http://10.10.0.87:8007/api/v1/patterns/detailed?entity_type=JUDGE"
```

### Get Entity Type Information

```bash
# **ENHANCED** - Get all entity types with real pattern data
curl "http://10.10.0.87:8007/api/v1/entity-types"

# Get entity types with real examples from patterns
curl "http://10.10.0.87:8007/api/v1/entity-types?include_examples=true"

# Get entity type categories
curl "http://10.10.0.87:8007/api/v1/entity-types/categories"

# Get detailed information about specific entity type
curl "http://10.10.0.87:8007/api/v1/entity-types/COURT"
```

### Health Check Integration

```bash
# Basic health check for load balancers
curl "http://10.10.0.87:8007/api/v1/health/ping"

# Detailed health with metrics
curl "http://10.10.0.87:8007/api/v1/health/detailed"

# Dependency status check
curl "http://10.10.0.87:8007/api/v1/health/dependencies"
```

### Configuration and Validation

```bash
# Get current configuration
curl "http://10.10.0.87:8007/api/v1/config"

# Validate production readiness
curl -X POST "http://10.10.0.87:8007/api/v1/config/validate"
```

## Client Integration Guidelines

### Python Client Example

```python
import requests
import json

class EntityExtractionClient:
    def __init__(self, base_url="http://10.10.0.87:8007/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def extract_entities(self, document_id, content, extraction_mode="hybrid", 
                        entity_types=None, confidence_threshold=0.7):
        """Extract entities from document content."""
        payload = {
            "document_id": document_id,
            "content": content,
            "extraction_mode": extraction_mode,
            "confidence_threshold": confidence_threshold
        }
        
        if entity_types:
            payload["entity_types"] = entity_types
        
        response = self.session.post(
            f"{self.base_url}/extract",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def get_extraction_status(self, extraction_id):
        """Get extraction status by ID."""
        response = self.session.get(f"{self.base_url}/extract/{extraction_id}/status")
        response.raise_for_status()
        return response.json()
    
    def health_check(self):
        """Perform basic health check."""
        response = self.session.get(f"{self.base_url}/health/ping")
        return response.status_code == 200

# Usage example
client = EntityExtractionClient()
result = client.extract_entities(
    document_id="legal_doc_001",
    content="Brown v. Board of Education, 347 U.S. 483 (1954)",
    entity_types=["case_citations", "court_names"]
)
print(f"Found {len(result['entities'])} entities")
```

### JavaScript Client Example

```javascript
class EntityExtractionClient {
    constructor(baseUrl = 'http://10.10.0.87:8007/api/v1') {
        this.baseUrl = baseUrl;
    }
    
    async extractEntities(documentId, content, options = {}) {
        const payload = {
            document_id: documentId,
            content: content,
            extraction_mode: options.extractionMode || 'hybrid',
            confidence_threshold: options.confidenceThreshold || 0.7,
            ...options
        };
        
        const response = await fetch(`${this.baseUrl}/extract`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`Extraction failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async getExtractionStatus(extractionId) {
        const response = await fetch(`${this.baseUrl}/extract/${extractionId}/status`);
        
        if (!response.ok) {
            throw new Error(`Status check failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async healthCheck() {
        try {
            const response = await fetch(`${this.baseUrl}/health/ping`);
            return response.ok;
        } catch (error) {
            return false;
        }
    }
}

// Usage example
const client = new EntityExtractionClient();
try {
    const result = await client.extractEntities(
        'legal_doc_001',
        'Brown v. Board of Education, 347 U.S. 483 (1954)',
        {
            entityTypes: ['case_citations', 'court_names'],
            extractionMode: 'hybrid'
        }
    );
    console.log(`Found ${result.entities.length} entities`);
} catch (error) {
    console.error('Extraction failed:', error.message);
}
```

---

## Appendix: Relationship Pattern Reference Tables

### Complete Relationship Type Reference

| Relationship Type | Category | Source Entity | Target Entity | Description | Indicators (Sample) |
|-------------------|----------|---------------|---------------|-------------|---------------------|
| **PARTY_TO** | Contractual & Financial | CONTRACT_PARTY | CONTRACT | Party to a contract or agreement | party to, signatory to, entered into, executed |
| **OBLIGATED_TO_PAY** | Contractual & Financial | PARTY | MONETARY_AMOUNT | Party obligated to pay amount | owes, obligated to pay, liable for, must pay |
| **ENTITLED_TO** | Contractual & Financial | PARTY | DAMAGES | Party entitled to payment or relief | entitled to, awarded, recovers, receives, due |
| **GUARANTEES** | Contractual & Financial | PARTY | CONTRACT | Party guaranteeing obligation | guarantees, guarantor of, surety for, backs |
| **BREACHES** | Contractual & Financial | PARTY | CONTRACT | Party breaching contract | breaches, breached, violates, defaults on |
| **SETTLES_FOR** | Contractual & Financial | SETTLEMENT | MONETARY_AMOUNT | Settlement for specific amount | settles for, settlement of, agreed to, resolved for |
| **INDEMNIFIES** | Contractual & Financial | PARTY | PARTY | Party indemnifying another | indemnifies, holds harmless, defends, protects |
| **DAMAGES_FOR** | Contractual & Financial | DAMAGES | LEGAL_MARKER | Damages for specific harm | damages for, compensation for, arising from |
| **PAYS_TO** | Contractual & Financial | PARTY | PARTY | Payment from one party to another | pays to, payment to, remits to, transfers to |
| **INTEREST_RATE_ON** | Contractual & Financial | INTEREST_RATE | MONETARY_AMOUNT | Interest rate on amount | interest on, rate of, % per annum, accruing at |
| **REPRESENTS** | Party & Litigation | ATTORNEY | PARTY | Attorney representing a party | represents, representing, on behalf of, counsel for |
| **EMPLOYS** | Party & Litigation | PARTY | LAW_FIRM | Party employing an attorney or firm | represented by, retained, hired, engaged |
| **SUES** | Party & Litigation | PLAINTIFF | DEFENDANT | Plaintiff suing defendant | v., versus, against, sues, brings action |
| **APPEALS_FROM** | Party & Litigation | APPELLANT | APPELLEE | Party appealing from another party | appeals from, appellant, appellee, on appeal from |
| **PRESIDES_OVER** | Party & Litigation | JUDGE | CASE_CITATION | Judge presiding over case | presiding, before Judge, Hon., Honorable |
| **OPPOSES** | Party & Litigation | PARTY | PARTY | Opposing parties in litigation | v., versus, opposing, adverse to, against |
| **JOINS** | Party & Litigation | PARTY | PARTY | Party joining another party | joins, joined by, consolidated with, intervenes |
| **SETTLES_WITH** | Party & Litigation | PARTY | PARTY | Parties settling dispute | settles with, settlement between, resolved |
| **WITNESS_FOR** | Party & Litigation | WITNESS_BLOCK | PARTY | Witness testifying for a party | witness for, testifies for, on behalf of, called by |
| **FILES_IN** | Party & Litigation | PARTY | COURT | Party filing in a court | filed in, files with, brought before, commenced in |
| **CITES** | Legal Precedent | CASE_CITATION | CASE_CITATION | Case citing another case | citing, cited in, as noted in, following, see |
| **OVERRULES** | Legal Precedent | CASE_CITATION | CASE_CITATION | Case overruling another case | overrules, overruling, overruled, supersedes |
| **DISTINGUISHES** | Legal Precedent | CASE_CITATION | CASE_CITATION | Case distinguishing from another | distinguishes, distinguished from, differs from |
| **AFFIRMS** | Legal Precedent | COURT | COURT | Higher court affirming lower court | affirms, affirmed, affirming, upheld, upholds |
| **REVERSES** | Legal Precedent | COURT | COURT | Higher court reversing lower court | reverses, reversed, reversing, vacated, vacates |
| **REMANDS** | Legal Precedent | COURT | COURT | Higher court remanding to lower court | remands, remanded, remanding, sent back |
| **FOLLOWS** | Legal Precedent | CASE_CITATION | CASE_CITATION | Case following precedent | follows, following, pursuant to, in accordance with |
| **MODIFIES** | Legal Precedent | CASE_CITATION | CASE_CITATION | Case modifying another case | modifies, modified, modifying, clarifies |
| **AMENDS** | Statutory & Regulatory | STATUTE_CITATION | STATUTE_CITATION | Statute/regulation amending another | amends, amended by, amending, as amended |
| **IMPLEMENTS** | Statutory & Regulatory | REGULATION_CITATION | STATUTE_CITATION | Regulation implementing statute | implements, implementing, pursuant to, under authority of |
| **INTERPRETS** | Statutory & Regulatory | CASE_CITATION | STATUTE_CITATION | Case interpreting statute/regulation | interprets, interpreting, construes, construing |
| **APPLIES** | Statutory & Regulatory | COURT | STATUTE_CITATION | Court applying statute/regulation | applies, applying, under, pursuant to, governed by |
| **SUPERSEDES** | Statutory & Regulatory | STATUTE_CITATION | STATUTE_CITATION | New law superseding old law | supersedes, superseding, replaces, repeals |
| **REFERENCES** | Statutory & Regulatory | STATUTE_CITATION | STATUTE_CITATION | Cross-reference between statutes | references, refers to, see, see also, as defined in |
| **CODIFIES** | Statutory & Regulatory | STATUTE_CITATION | LEGAL_MARKER | Statute codifying common law/practice | codifies, codifying, incorporates, adopts |
| **VIOLATES** | Statutory & Regulatory | PARTY | STATUTE_CITATION | Party violating statute/regulation | violates, violated, violating, breach of |
| **ENFORCES** | Statutory & Regulatory | FEDERAL_AGENCY | REGULATION_CITATION | Agency enforcing statute/regulation | enforces, enforcing, enforcement of, administers |
| **FILED_ON** | Temporal & Procedural | MOTION | FILING_DATE | Document filed on specific date | filed on, filed, submitted on, entered on, dated |
| **DECIDED_ON** | Temporal & Procedural | CASE_CITATION | DECISION_DATE | Case decided on specific date | decided, decided on, decision dated, opinion issued |
| **EFFECTIVE_AS_OF** | Temporal & Procedural | STATUTE_CITATION | EFFECTIVE_DATE | Law/regulation effective as of date | effective, effective as of, in effect from |
| **EXPIRES_ON** | Temporal & Procedural | CONTRACT | TERM_DATE | Document/agreement expiring on date | expires, expiring on, terminates, ends on |
| **PRECEDES** | Temporal & Procedural | MOTION | MOTION | One procedural step preceding another | before, prior to, preceding, followed by, then |
| **DEADLINE_FOR** | Temporal & Procedural | DEADLINE | MOTION | Deadline for filing or action | deadline for, due by, must be filed by, no later than |
| **DURING** | Temporal & Procedural | LEGAL_MARKER | DATE_RANGE | Event occurring during time period | during, throughout, between, from...to |
| **RESPONDS_TO** | Temporal & Procedural | BRIEF | MOTION | Document responding to another | in response to, responding to, reply to, opposition to |
| **SCHEDULED_FOR** | Temporal & Procedural | PROCEDURAL_RULE | DATE | Hearing/trial scheduled for date | scheduled for, set for, hearing on, trial date |
| **HAS_JURISDICTION** | Jurisdictional & Venue | COURT | JURISDICTION | Court having jurisdiction over case | has jurisdiction, jurisdiction over, subject matter jurisdiction |
| **LOCATED_IN** | Jurisdictional & Venue | COURT | DISTRICT | Court/party located in geographic area | located in, situated in, in the, for the, sitting in |
| **VENUE_IN** | Jurisdictional & Venue | CASE_CITATION | VENUE | Venue for case in specific court | venue in, venue lies in, proper venue, brought in |
| **TRANSFERRED_TO** | Jurisdictional & Venue | COURT | COURT | Case transferred to another court | transferred to, transfer to, moved to, change of venue to |
| **RESIDES_IN** | Jurisdictional & Venue | PARTY | JURISDICTION | Party residing in jurisdiction | resides in, resident of, domiciled in, citizen of |
| **GOVERNS_IN** | Jurisdictional & Venue | STATUTE_CITATION | JURISDICTION | Law governing in jurisdiction | governs in, applies in, law of, under the laws of |
| **CIRCUIT_INCLUDES** | Jurisdictional & Venue | CIRCUITS | DISTRICT | Circuit including district courts | includes, comprises, encompasses, covers, within |
| **EXERCISES_OVER** | Jurisdictional & Venue | SPECIALIZED_COURTS | SPECIALIZED_JURISDICTION | Court exercising authority over area | exercises authority over, has authority in |
| **REMOVED_TO** | Jurisdictional & Venue | STATE_COURTS | FEDERAL_COURTS | Case removed to federal court | removed to, removal to, removed from, notice of removal |

### Relationship Category Summary

| Category | Count | Common Use Cases | Typical Document Types |
|----------|-------|------------------|------------------------|
| **Contractual & Financial** | 10 | Contract analysis, settlement agreements, financial obligations | Contracts, Settlement Agreements, Financial Documents |
| **Party & Litigation** | 10 | Case party identification, representation tracking, procedural analysis | Pleadings, Court Filings, Case Documents |
| **Legal Precedent** | 8 | Precedent analysis, case law research, judicial reasoning | Court Opinions, Legal Briefs, Memoranda |
| **Statutory & Regulatory** | 9 | Regulatory compliance, statutory interpretation, enforcement | Regulations, Statutes, Compliance Documents |
| **Temporal & Procedural** | 9 | Timeline construction, procedural tracking, deadline management | Court Orders, Procedural Documents, Calendars |
| **Jurisdictional & Venue** | 9 | Venue determination, jurisdiction analysis, geographic mapping | Jurisdictional Motions, Transfer Orders, Venue Analysis |

### Entity-Relationship Compatibility Matrix

**Most Common Source→Target Entity Pairs:**

| Source Entity | Can Relate To (Target) | Relationship Types Available |
|---------------|------------------------|------------------------------|
| **CASE_CITATION** | CASE_CITATION | CITES, OVERRULES, FOLLOWS, DISTINGUISHES, MODIFIES |
| **CASE_CITATION** | STATUTE_CITATION | INTERPRETS |
| **CASE_CITATION** | DECISION_DATE | DECIDED_ON |
| **COURT** | COURT | AFFIRMS, REVERSES, REMANDS, TRANSFERRED_TO |
| **COURT** | STATUTE_CITATION | APPLIES |
| **COURT** | JURISDICTION | HAS_JURISDICTION |
| **COURT** | DISTRICT | LOCATED_IN |
| **PARTY** | PARTY | INDEMNIFIES, PAYS_TO, OPPOSES, JOINS, SETTLES_WITH |
| **PARTY** | CONTRACT | PARTY_TO, BREACHES, GUARANTEES |
| **PARTY** | MONETARY_AMOUNT | OBLIGATED_TO_PAY |
| **PARTY** | DAMAGES | ENTITLED_TO |
| **PARTY** | JURISDICTION | RESIDES_IN |
| **PARTY** | COURT | FILES_IN |
| **PARTY** | STATUTE_CITATION | VIOLATES |
| **ATTORNEY** | PARTY | REPRESENTS |
| **JUDGE** | CASE_CITATION | PRESIDES_OVER |
| **STATUTE_CITATION** | STATUTE_CITATION | AMENDS, SUPERSEDES, REFERENCES |
| **STATUTE_CITATION** | JURISDICTION | GOVERNS_IN |
| **REGULATION_CITATION** | STATUTE_CITATION | IMPLEMENTS |
| **FEDERAL_AGENCY** | REGULATION_CITATION | ENFORCES |
| **MOTION** | FILING_DATE | FILED_ON |
| **MOTION** | MOTION | PRECEDES |

### Relationship Indicators Quick Reference

**High-Frequency Indicators (appears in multiple relationship types):**

| Indicator | Relationship Types | Usage Context |
|-----------|-------------------|---------------|
| **"citing"** / **"cited in"** | CITES | Legal precedent references |
| **"represents"** / **"representing"** | REPRESENTS | Attorney-client relationships |
| **"filed in"** / **"filed on"** | FILES_IN, FILED_ON | Court filings and dates |
| **"applies"** / **"applied"** | APPLIES | Statutory application |
| **"amends"** / **"amended"** | AMENDS | Legislative changes |
| **"reverses"** / **"reversed"** | REVERSES | Appellate decisions |
| **"obligated to pay"** | OBLIGATED_TO_PAY | Financial obligations |
| **"party to"** | PARTY_TO | Contract parties |
| **"v."** / **"versus"** | SUES, OPPOSES | Litigation parties |
| **"presiding"** / **"presides over"** | PRESIDES_OVER | Judicial assignment |

**Category-Specific Indicators:**

**Legal Precedent:** citing, overrules, distinguishes, affirms, reverses, follows, modifies
**Contractual:** party to, obligated to pay, indemnifies, settles for, breaches
**Litigation:** represents, sues, appeals from, presides over, opposes
**Statutory:** amends, implements, interprets, applies, supersedes, enforces
**Temporal:** filed on, decided on, effective as of, expires on, during
**Jurisdictional:** has jurisdiction, located in, resides in, transferred to, governs in

---

## API Summary

**Entity Extraction Service** provides professional-grade legal entity extraction with:

- **195+ Legal Entity Types** across 4 specialized extraction waves
- **34 Relationship Types** for comprehensive knowledge graph construction
- **Wave System Architecture** with intelligent document routing
- **AI-Powered Extraction** using Qwen3-VL-8B models via vLLM
- **PatternLoader Integration** providing few-shot learning examples
- **Intelligent Document Routing** with automatic strategy selection
- **GraphRAG-Ready** relationship extraction for knowledge graph integration
- **Multiple Extraction Strategies** optimized for different document sizes
- **Real-time Performance Monitoring** with comprehensive health checks
- **Comprehensive API** with 28 endpoints including routing and configuration
- **Production Ready** with security, rate limiting, and monitoring capabilities

---

## Complete Endpoint Reference

### All Active Endpoints (26 Active + 2 Deprecated = 28 Total)

| Category | Method | Endpoint | Description | Status |
|----------|--------|----------|-------------|--------|
| **Primary Extraction** | POST | `/api/v2/process/extract` | Main Wave System extraction with intelligent routing | ⭐ Primary |
| **Primary Extraction** | GET | `/api/v2/info` | v2 API information and capabilities | Active |
| **Primary Extraction** | GET | `/api/v2/capabilities` | Detailed v2 API capabilities | Active |
| **Health & Monitoring** | GET | `/` | Root endpoint health check | Active |
| **Health & Monitoring** | GET | `/api/v1/health` | Basic health check | Active |
| **Health & Monitoring** | GET | `/api/v1/health/ping` | Lightweight ping for load balancers | Active |
| **Health & Monitoring** | GET | `/api/v1/health/ready` | Kubernetes readiness check | Active |
| **Health & Monitoring** | GET | `/api/v1/ready` | Kubernetes readiness (shorthand) | Active |
| **Health & Monitoring** | GET | `/api/v1/health/detailed` | Comprehensive health status with metrics | Active |
| **Health & Monitoring** | GET | `/api/v1/health/dependencies` | Dependency service status (vLLM, Supabase) | Active |
| **Health & Monitoring** | GET | `/api/v1/health/performance` | Performance metrics and statistics | Deprecated |
| **Patterns** | GET | `/api/v1/patterns` | Unified pattern API with comprehensive details | ⭐ Recommended |
| **Patterns** | GET | `/api/v1/patterns/cache/stats` | Pattern cache statistics | Active |
| **Patterns** | POST | `/api/v1/patterns/cache/clear` | Clear pattern cache | Active |
| **Entity Types** | GET | `/api/v1/entity-types` | List all 195+ entity types | Deprecated |
| **Entity Types** | GET | `/api/v1/entity-types/categories` | Entity type categories by wave | Active |
| **Entity Types** | GET | `/api/v1/entity-types/{entity_type}` | Specific entity type details | Active |
| **Relationships** | GET | `/api/v1/relationships` | List all 34 relationship types | Active |
| **Relationships** | GET | `/api/v1/relationships/categories` | Relationship categories | Active |
| **Relationships** | GET | `/api/v1/relationships/statistics` | Relationship extraction statistics | Active |
| **Relationships** | GET | `/api/v1/relationships/{relationship_type}` | Specific relationship type details | Active |
| **Relationships** | POST | `/api/v1/extract/relationships` | Extract relationships from text | Active |
| **Document Routing** | POST | `/api/v1/route` | Route document to optimal processing strategy | Active |
| **Document Routing** | GET | `/api/v1/strategies` | Get available extraction strategies | Active |
| **Document Routing** | GET | `/api/v1/thresholds` | Get document size thresholds | Active |
| **Configuration** | GET | `/api/v1/config` | Get service configuration (non-sensitive) | Active |
| **Documentation** | GET | `/api/v1/docs` | Interactive OpenAPI documentation | Active |
| **Documentation** | GET | `/api/v1/redoc` | Alternative ReDoc documentation | Active |

**Base URL:** `http://10.10.0.87:8007`

**OpenAPI Documentation:** http://10.10.0.87:8007/docs

**Total Active Endpoints:** 28 (26 active + 2 deprecated)

### Endpoint Categories Summary

**Core Extraction (3 endpoints):**
- Primary Wave System extraction endpoint with intelligent document routing
- API information and capabilities discovery
- Supports all 195+ entity types across 4 extraction waves

**Health & Monitoring (8 endpoints):**
- Multiple health check endpoints for different use cases (root, health, ping, ready, detailed)
- Comprehensive dependency monitoring (vLLM, Supabase)
- Performance metrics and statistics
- Kubernetes-compatible health checks

**Patterns & Entity Types (6 endpoints):**
- Unified pattern API with comprehensive pattern details
- Entity type discovery and categorization
- Pattern cache management

**Relationships (5 endpoints):**
- Complete relationship type library (34 types)
- Relationship extraction and statistics
- Category-based relationship discovery

**Document Routing (3 endpoints):**
- Intelligent document routing based on size and complexity
- Strategy information and selection logic
- Document size threshold configuration

**Configuration (1 endpoint):**
- Service configuration exposure (non-sensitive values)
- Feature flag discovery
- Rate limiting and timeout information

**Documentation (2 endpoints):**
- Interactive OpenAPI documentation (Swagger UI)
- Alternative ReDoc documentation interface

### API Usage Recommendations

**For Entity Extraction:**
1. **Use**: `POST /api/v2/process/extract` (Primary extraction endpoint)
2. **Check document size**: `GET /api/v1/thresholds` to understand routing
3. **Optional routing**: `POST /api/v1/route` to preview extraction strategy
4. **Monitor**: `GET /api/v1/health/detailed` for service health

**For Relationship Extraction:**
1. **Discover relationships**: `GET /api/v1/relationships` to see available types
2. **Extract relationships**: `POST /api/v1/extract/relationships` with text
3. **Check statistics**: `GET /api/v1/relationships/statistics` for performance metrics

**For Pattern Discovery:**
1. **Browse patterns**: `GET /api/v1/patterns` for comprehensive pattern library
2. **Check cache**: `GET /api/v1/patterns/cache/stats` for cache performance
3. **Clear cache**: `POST /api/v1/patterns/cache/clear` if needed

**For Service Monitoring:**
1. **Basic health**: `GET /api/v1/health` for quick status
2. **Detailed status**: `GET /api/v1/health/detailed` for comprehensive metrics
3. **Dependencies**: `GET /api/v1/health/dependencies` to check vLLM and Supabase
4. **Configuration**: `GET /api/v1/config` to understand service settings

---

**Migration Notes:**

**Deprecated Endpoints:**
- `/api/v1/extract` - Removed (use `/api/v2/process/extract`)
- `/api/v1/extract/chunk` - Removed (chunking now automatic via routing)
- `/api/v1/extract/enhance` - Removed (enhancement now built into Wave System)
- `/api/v1/training/*` - All training endpoints removed
- `/api/v1/health/performance` - Deprecated (use `/api/v1/health/detailed`)
- `/api/v1/entity-types` - Deprecated (use `/api/v1/entity-types/categories`)

**Primary Endpoint:** The Wave System at `/api/v2/process/extract` is now the **sole extraction method** and provides:
- Automatic document routing based on size
- Intelligent strategy selection
- PatternLoader integration for few-shot learning
- GraphRAG-ready relationship extraction
- Comprehensive entity extraction across all 195+ types

*For additional support and integration assistance, consult the service README.md and contact the development team.*