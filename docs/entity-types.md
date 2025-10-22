# Entity Extraction Service: Extremely Detailed Technical Specification
## `/entity-types` and `/patterns/*` Endpoints Complete Documentation

**Version**: 2.0.0  
**Last Updated**: 2025-01-10  
**Total Patterns**: 664  
**Total Entity/Citation Types**: 272  
**Pattern Files**: 74 YAML files  
**Jurisdictions**: Federal + All 50 US States + International  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Complete Entity Type System](#2-complete-entity-type-system)
3. [Pattern System Architecture](#3-pattern-system-architecture)
4. [Entity Types Endpoints](#4-entity-types-endpoints)
5. [Pattern Endpoints](#5-pattern-endpoints)
6. [Confidence Scoring System](#6-confidence-scoring-system)
7. [Entity Type Mapping System](#7-entity-type-mapping-system)
8. [Request/Response Schemas](#8-requestresponse-schemas)
9. [Pattern Statistics & Analytics](#9-pattern-statistics--analytics)
10. [Real-World Usage Examples](#10-real-world-usage-examples)
11. [Complete Pattern Catalog](#11-complete-pattern-catalog)
12. [Entity Type Coverage Analysis](#12-entity-type-coverage-analysis)
13. [Error Handling & Validation](#13-error-handling--validation)
14. [Performance Considerations](#14-performance-considerations)
15. [Migration & Deprecation Notes](#15-migration--deprecation-notes)

---

## 1. Executive Summary

The Entity Extraction Service provides a comprehensive legal entity and citation extraction system with:

- **664 Regex Patterns**: Covering federal, state, and international legal entities
- **272 Entity/Citation Types**: 160 EntityType + 112 CitationType enum values
- **Dual Extraction Modes**: Transitioning from regex-based to AI-enhanced extraction
- **Multi-Strategy System**: Multipass, AI-enhanced, and Unified strategies
- **Confidence Scoring**: Multi-signal weighted scoring with thresholds
- **Bluebook Compliance**: Following Bluebook 22nd Edition standards
- **Complete API Coverage**: 15+ endpoints for entity types and patterns

### Key Architecture Components

```
┌─────────────────────────────────────────────────────────┐
│                  Entity Extraction Service              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ PatternLoader│  │EntityType    │  │ Confidence   │ │
│  │ (664 patterns)│  │Mapper        │  │ Scorer       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                 │                   │         │
│         └─────────────────┼───────────────────┘         │
│                           ▼                             │
│                  ┌──────────────┐                       │
│                  │  Extraction  │                       │
│                  │   Strategies │                       │
│                  └──────────────┘                       │
│                           │                             │
│            ┌──────────────┼──────────────┐             │
│            ▼              ▼              ▼             │
│      ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│      │Multipass │  │AI-Enhanced│  │ Unified  │        │
│      │(7 passes)│  │(Context) │  │(Balanced)│        │
│      └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Core Endpoints

#### GET /entity-types
**Purpose**: Comprehensive discovery of all supported legal entity and citation types

**Request**:
```http
GET /api/v1/entity-types?include_descriptions=true&include_examples=true
Headers:
  Content-Type: application/json
  X-Request-ID: <uuid> (optional)
```

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| include_descriptions | boolean | No | true | Include human-readable descriptions |
| include_examples | boolean | No | false | Include regex patterns and examples |

**Response Schema** (abbreviated for space):
```json
{
  "entity_types": [...],
  "citation_types": [...],
  "total_entity_types": 160,
  "total_citation_types": 112,
  "categories": {...},
  "metadata": {...}
}
```

#### GET /patterns/comprehensive
**Purpose**: Get comprehensive pattern information with deduplication and enhanced metadata

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| entity_type | string | No | - | Filter for specific entity type |
| category | string | No | - | Filter by category |
| min_confidence | number | No | 0.0 | Minimum confidence threshold |
| bluebook_compliant | boolean | No | - | Filter Bluebook-compliant patterns |
| has_patterns | boolean | No | - | Filter types with/without patterns |
| has_examples | boolean | No | - | Filter types with/without examples |
| include_patterns | boolean | No | true | Include full pattern details |
| include_examples | boolean | No | true | Include all examples |


---

## 3. Entity and Pattern Mappings

### 3.1 Complete Entity Type Inventory (272 Total Types)

#### Entity Types (160 types) by Category

**Courts and Judicial (8 types)**:
COURT, JUDGE, MAGISTRATE, ARBITRATOR, MEDIATOR, SPECIAL_MASTER, COURT_CLERK, COURT_REPORTER

**Parties and Representatives (11 types)**:
PARTY, PLAINTIFF, DEFENDANT, APPELLANT, APPELLEE, PETITIONER, RESPONDENT, INTERVENOR, AMICUS_CURIAE, THIRD_PARTY, CLASS_REPRESENTATIVE

**Legal Professionals (8 types)**:
ATTORNEY, LAW_FIRM, PROSECUTOR, PUBLIC_DEFENDER, LEGAL_AID, PARALEGAL, EXPERT_WITNESS, LAY_WITNESS

**Government and Agencies (7 types)**:
GOVERNMENT_ENTITY, FEDERAL_AGENCY, STATE_AGENCY, LOCAL_AGENCY, REGULATORY_BODY, LEGISLATIVE_BODY, EXECUTIVE_OFFICE

**Documents and Filings (22 types)**:
DOCUMENT, MOTION, BRIEF, COMPLAINT, ANSWER, DISCOVERY_DOCUMENT, DEPOSITION, INTERROGATORY, AFFIDAVIT, DECLARATION, EXHIBIT, TRANSCRIPT, ORDER, JUDGMENT, VERDICT, SETTLEMENT, CONTRACT, AGREEMENT, PLEADING, FILING, PETITION, WRIT

#### Citation Types (112 types) by Category

**Case Citations (23 types)**:
CASE_CITATION, FEDERAL_CASE_CITATION, STATE_CASE_CITATION, SUPREME_COURT_CITATION, CIRCUIT_COURT_CITATION, DISTRICT_COURT_CITATION, BANKRUPTCY_COURT_CITATION, TAX_COURT_CITATION, and 15 more...

**Statutory Citations (15 types)**:
STATUTE_CITATION, USC_CITATION, USCA_CITATION, STATE_CODE_CITATION, STATE_STATUTE_CITATION, LOCAL_ORDINANCE_CITATION, and 9 more...

### 3.2 Pattern Coverage Analysis

#### Pattern Distribution by Source
- **Federal Patterns**: 97 patterns (8.4%)
- **State Patterns**: 686 patterns (59.3%)
- **Client Patterns**: 312 patterns (27.0%)
- **Comprehensive Patterns**: 33 patterns (2.9%)
- **Legal Structure Patterns**: 28 patterns (2.4%)

#### Entity Types with Pattern Coverage
- **Types with patterns**: 179 (65.7%)
- **Types without patterns**: 93 (34.3%)
- **Average patterns per type**: 6.5
- **Maximum patterns for single type**: 34 (COURT)

#### Confidence Score Distribution
| Confidence Range | Pattern Count | Percentage |
|-----------------|---------------|------------|
| 0.95-1.00 | 248 | 21.5% |
| 0.90-0.94 | 312 | 27.0% |
| 0.85-0.89 | 285 | 24.7% |
| 0.80-0.84 | 189 | 16.3% |
| 0.70-0.79 | 122 | 10.5% |

#### Orphaned Entity Types (93 types with no patterns)
**High Priority Missing Patterns**:
- PROSECUTOR, PUBLIC_DEFENDER (Legal Professionals)
- REGULATORY_BODY, LEGISLATIVE_BODY (Government)
- DEPOSITION, INTERROGATORY (Documents)
- BURDEN_OF_PROOF, STANDARD_OF_REVIEW (Legal Concepts)
- COMPENSATORY_DAMAGES, PUNITIVE_DAMAGES (Damages)

---

## 4. Regex Pattern Analysis

### 4.1 Complete Pattern Inventory (1,156 patterns)

#### Pattern Complexity Distribution
- **Simple Patterns** (< 50 chars): 1 pattern (0.09%)
- **Moderate Patterns** (50-150 chars): 83 patterns (7.18%)
- **Complex Patterns** (> 150 chars): 1,072 patterns (92.73%)

#### Pattern Metrics
- **Average Pattern Length**: 150.8 characters
- **Minimum Pattern Length**: 14 characters (simple year pattern)
- **Maximum Pattern Length**: 944 characters (New York Consolidated Laws)
- **Total YAML Lines**: 22,421 lines
- **Average Lines per Pattern**: 19.4

### 4.2 Technical Pattern Features

#### Named Capture Groups (2,270 total occurrences)
Top 10 Most Common:
1. year - 267 occurrences (date extraction)
2. section - 165 occurrences (statute sections)
3. case_name - 157 occurrences (full case names)
4. plaintiff - 155 occurrences (party names)
5. defendant - 154 occurrences (party names)
6. volume - 144 occurrences (reporter volumes)
7. page - 143 occurrences (page numbers)
8. county - 114 occurrences (jurisdiction)
9. pinpoint - 98 occurrences (specific page refs)
10. reporter - 84 occurrences (legal reporters)

#### Regex Feature Usage
- **Quantifiers** (*, +, ?, {n,m}): 23,977 occurrences
- **Non-capturing groups** (?:...): 4,913 occurrences
- **Alternation** (|): 4,404 occurrences
- **Character classes** ([...]): 3,685 occurrences
- **Named groups** (?P<name>...): 2,270 occurrences
- **Anchors** (^, $, \b): 1,185 occurrences
- **Lookahead assertions**: 7 occurrences
- **Lookbehind assertions**: 0 (avoided for performance)


---

## 5. Performance Analysis

### 5.1 Optimization Achievement Summary

| Metric | Before Optimization | After Optimization | Improvement |
|--------|-------------------|-------------------|-------------|
| **Processing Time** | 1800+ seconds | 6.11 seconds | **295x faster** |
| **GPU Utilization** | 40-45% | 94% | **2.1x better** |
| **Token Generation** | 183,822 tokens | ~8,000 tokens | **23x reduction** |
| **Throughput** | 114 chars/sec | 33,618 chars/sec | **295x faster** |
| **Token Rate** | 73 tokens/sec | ~1,300 tokens/sec | **18x faster** |
| **Memory Usage** | 40GB+ | 7.8GB | **5x reduction** |

### 5.2 Performance Bottlenecks Identified

#### Pattern Compilation Performance
- **Simple patterns** (18 chars): 26.26 MB/s throughput, 0.001ms compile
- **Moderate patterns** (62 chars): 24.37 MB/s throughput, 0.001ms compile
- **Complex patterns** (280 chars): 17.89 MB/s throughput, 0.001ms compile
- **Very complex patterns** (510 chars): 28.14 MB/s throughput, 0.000ms compile

#### Cache Performance Issues
- **Without cache**: 1.80 seconds
- **With cache enabled**: 2.04 seconds
- **Performance degradation**: -13.3% (cache overhead exceeds benefits)
- **Root cause**: Cache lookup overhead > pattern compilation time

### 5.3 Optimization Recommendations

#### Immediate Optimizations (Quick Wins)
1. **Remove cache implementation** - Eliminates 13.3% performance penalty
2. **Pattern prioritization** - Process high-confidence patterns first
3. **Early termination** - Stop after sufficient matches found
4. **Batch compilation** - Compile all patterns on startup

#### Medium-term Optimizations
1. **Pattern decomposition** - Break complex patterns into stages
2. **Trie-based alternations** - For large keyword lists
3. **Memory-mapped pattern storage** - Reduce memory footprint
4. **Parallel pattern execution** - Already implemented, 16x concurrency

#### Long-term Optimizations
1. **GPU-accelerated regex** - Use CUDA for pattern matching
2. **Custom pattern engine** - Optimized for legal patterns
3. **Machine learning replacement** - Train models for complex patterns
4. **Distributed processing** - Scale horizontally for large documents

### 5.4 Scalability Projections

With current optimizations:
- **1 document** (200KB): 6 seconds
- **10 documents**: ~1 minute
- **100 documents**: ~10 minutes
- **1,000 documents**: ~1.7 hours
- **10,000 documents**: ~17 hours

Theoretical limits:
- **Max throughput**: 33.6 MB/s
- **Max documents/hour**: 600
- **Max tokens/second**: 1,300
- **GPU saturation**: 94% utilization

---

## 6. Architecture Overview

### 6.1 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Client Applications                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Entity Extraction Service API               │
│                   (Port 8007)                            │
├─────────────────────────────────────────────────────────┤
│  Endpoints:                                              │
│  • /entity-types                                         │
│  • /entity-types/categories                              │
│  • /entity-types/{type}                                  │
│  • /patterns/detailed                                    │
│  • /patterns/comprehensive                               │
│  • /extract                                              │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬────────────┐
        ▼             ▼             ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│PatternLoader │ │  Regex   │ │  SpaCy   │ │   vLLM   │
│  (1,156)     │ │ Engine   │ │   NER    │ │ AI Mode  │
└──────────────┘ └──────────┘ └──────────┘ └──────────┘
        │             │             │            │
        └─────────────┴─────────────┴────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ Entity Results   │
            │  Aggregator      │
            └──────────────────┘
```

### 6.2 Component Architecture

#### PatternLoader System
- **Purpose**: Load and manage regex patterns from YAML files
- **Patterns Loaded**: 1,156 from 74 files
- **Architecture Issue**: Not used by EntityExtractionClient
- **Memory Usage**: ~500MB for compiled patterns
- **Initialization Time**: 2-3 seconds

#### EntityExtractionClient
- **Purpose**: Perform entity extraction
- **Patterns Used**: 85 hardcoded patterns
- **Architecture Issue**: Bypasses PatternLoader
- **Extraction Modes**: regex, spacy, ai_enhanced
- **Performance**: 6.11 seconds for 200KB document


---

## 7. Implementation Guidelines

### 7.1 For New Entity Extraction Features

#### Step 1: Define Entity Type
```python
# In models/entity_types.py
class EntityType(str, Enum):
    # Add new entity type
    NEW_ENTITY = "NEW_ENTITY"
```

#### Step 2: Create Pattern YAML
```yaml
# In src/patterns/client/new_patterns.yaml
metadata:
  pattern_type: new_entity_patterns
  jurisdiction: general
  bluebook_compliance: 22nd_edition
  pattern_version: "1.0.0"
  created_date: "2025-09-10"
  description: "Patterns for NEW_ENTITY extraction"

new_entity_patterns:
  basic_pattern:
    name: "new_entity.basic"
    pattern: "(?P<entity_name>[A-Z][a-zA-Z]+)"
    confidence: 0.85
    priority: 80
    examples:
      - "Example Entity"
```

#### Step 3: Register with PatternLoader (Currently NOT connected - needs implementation)

#### Step 4: Add to EntityExtractionClient
```python
# In src/core/entity_extraction_client.py
ENTITY_PATTERNS[EntityType.NEW_ENTITY] = [
    CompiledPattern(
        pattern=re.compile(r"(?P<entity_name>[A-Z][a-zA-Z]+)"),
        entity_type=EntityType.NEW_ENTITY,
        confidence=0.85
    )
]
```

### 7.2 For Performance Improvements

#### Performance Testing Framework
```python
import time
import psutil
import asyncio
from entity_extraction_client import EntityExtractionClient

async def performance_test(document_path: str):
    client = EntityExtractionClient()
    
    # Memory baseline
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024
    
    # Time extraction
    start_time = time.time()
    results = await client.extract_entities(
        document_path, 
        mode="regex"
    )
    end_time = time.time()
    
    # Memory after
    mem_after = process.memory_info().rss / 1024 / 1024
    
    # Calculate metrics
    processing_time = end_time - start_time
    memory_used = mem_after - mem_before
    entities_found = len(results.entities)
    
    return {
        "processing_time": processing_time,
        "memory_used_mb": memory_used,
        "entities_found": entities_found,
        "throughput": len(document_text) / processing_time
    }
```

---

## 8. Critical Issues

### 8.1 Architectural Disconnect

#### The Core Problem
**PatternLoader loads 1,156 patterns but EntityExtractionClient uses only 85 hardcoded patterns**

**Impact**:
- 93% of patterns are never used
- Maintenance nightmare with duplicated pattern definitions
- No single source of truth for patterns
- Difficult to add new patterns consistently

**Root Cause Analysis**:
1. PatternLoader was developed independently
2. EntityExtractionClient predates PatternLoader
3. No integration work completed
4. Different pattern format requirements

**Resolution Path**:
```python
# Step 1: Create adapter layer
class PatternAdapter:
    def convert_yaml_to_compiled(self, yaml_pattern):
        # Convert YAML format to CompiledPattern
        pass

# Step 2: Integrate in EntityExtractionClient
class EntityExtractionClient:
    def __init__(self):
        self.pattern_loader = PatternLoader()
        self.patterns = self._load_patterns_from_loader()
    
    def _load_patterns_from_loader(self):
        # Convert PatternLoader patterns to internal format
        pass
```

### 8.2 Entity Type Coverage Gaps

#### 93 Orphaned Entity Types
**High Priority Types Without Patterns**:
1. Legal Professionals: PROSECUTOR, PUBLIC_DEFENDER
2. Government: REGULATORY_BODY, LEGISLATIVE_BODY  
3. Documents: DEPOSITION, INTERROGATORY
4. Concepts: BURDEN_OF_PROOF, STANDARD_OF_REVIEW
5. Damages: COMPENSATORY_DAMAGES, PUNITIVE_DAMAGES

**Impact**:
- 34% of defined entity types cannot be extracted
- Incomplete entity coverage for legal documents
- GraphRAG missing critical entity relationships

### 8.3 Cache Performance Degradation

#### The Cache Paradox
**Cache makes extraction 13.3% SLOWER**

**Measurements**:
- Without cache: 1.80 seconds
- With cache: 2.04 seconds
- Overhead: 240ms

**Root Cause**:
- Pattern compilation is already fast (0.001ms)
- Cache lookup overhead > compilation time
- LRU cache with 1000 entries requires management
- Thread locking for cache access

**Solution**:
```python
# Remove cache entirely
class PatternManager:
    def __init__(self):
        # Compile all patterns once at startup
        self.compiled_patterns = self._compile_all_patterns()
    
    def _compile_all_patterns(self):
        # One-time compilation, no cache needed
        return {
            pattern_id: re.compile(pattern_str)
            for pattern_id, pattern_str in patterns.items()
        }
```

### 8.4 Memory Pressure Issues

#### Before Optimization
- **40GB+ memory usage** during extraction
- **Cause**: Entire document in memory multiple times
- **Impact**: OOM errors on large documents

#### After Optimization  
- **7.8GB memory usage**
- **Solution**: Streaming and chunking
- **Remaining Issue**: Pattern storage overhead


---

## 9. Future Roadmap

### 9.1 Immediate Priority (Sprint 1)

#### Week 1-2: Pattern Integration
- [ ] Connect PatternLoader to EntityExtractionClient
- [ ] Create pattern adapter layer
- [ ] Validate all 1,156 patterns work correctly
- [ ] Remove 85 hardcoded patterns
- [ ] Update tests for new pattern source

#### Week 3-4: Performance Fixes
- [ ] Remove cache implementation (-13.3% penalty)
- [ ] Implement startup pattern compilation
- [ ] Optimize memory usage for patterns
- [ ] Add pattern prioritization logic

### 9.2 Short Term (Quarter 1)

#### Missing Pattern Development
- [ ] Create patterns for 20 high-priority entity types
- [ ] Validate patterns with legal experts
- [ ] Add Bluebook compliance tests
- [ ] Document pattern creation guidelines

#### API Enhancements
- [ ] Add pattern CRUD endpoints
- [ ] Implement pattern versioning
- [ ] Add pattern testing endpoint
- [ ] Create pattern analytics dashboard

### 9.3 Medium Term (Quarter 2)

#### Architecture Refactor
- [ ] Unified pattern management system
- [ ] Plugin architecture for extraction modes
- [ ] Microservice decomposition
- [ ] Event-driven pattern updates

#### AI Integration
- [ ] Fine-tune vLLM for legal entities
- [ ] Implement pattern learning from corrections
- [ ] Hybrid extraction mode optimization
- [ ] Confidence score machine learning

### 9.4 Long Term (Year 1)

#### Advanced Features
- [ ] GPU-accelerated pattern matching
- [ ] Distributed extraction pipeline
- [ ] Real-time pattern updates
- [ ] Multi-language support
- [ ] Custom pattern DSL

#### Platform Evolution
- [ ] SaaS API offering
- [ ] Pattern marketplace
- [ ] Community-contributed patterns
- [ ] Automated pattern generation
- [ ] Legal AI assistant integration

---

## 10. Recommendations and Next Steps

### 10.1 Immediate Actions Required

1. **CRITICAL: Fix Pattern System Disconnect**
   - Assign senior engineer immediately
   - 2-week sprint to integrate PatternLoader
   - Daily progress reviews
   - Complete by end of September 2025

2. **Remove Cache Implementation**
   - 1-day task
   - Immediate 13.3% performance improvement
   - No risk, pure benefit

3. **Document Pattern Creation Process**
   - Create pattern development guide
   - Establish pattern review process
   - Set up pattern testing framework

### 10.2 Strategic Recommendations

#### Organizational
1. **Establish Pattern Governance Committee**
   - Legal experts for Bluebook compliance
   - Engineers for technical review
   - QA for pattern validation

2. **Create Entity Extraction Team**
   - Dedicated team for service ownership
   - Clear roadmap and priorities
   - Regular stakeholder updates

#### Technical
1. **Implement Continuous Pattern Improvement**
   - A/B testing for patterns
   - Automated performance regression tests
   - Pattern effectiveness metrics

2. **Build Pattern Analytics Platform**
   - Track pattern usage and effectiveness
   - Identify missing patterns from failures
   - Optimize based on real usage data

### 10.3 Risk Mitigation

#### High Risk Items
1. **Pattern System Disconnect**: Creates maintenance nightmare
2. **Memory Pressure**: Limits scalability
3. **Missing Entity Types**: Reduces extraction completeness

#### Mitigation Strategies
1. **Incremental Migration**: Phase PatternLoader integration
2. **Memory Monitoring**: Add alerts for memory usage
3. **Fallback Mechanisms**: Use AI mode for missing patterns

### 10.4 Success Metrics

#### Technical Metrics
- Pattern coverage: Target 95% of entity types
- Extraction speed: < 10 seconds for 500KB document  
- Memory usage: < 10GB for any document
- GPU utilization: > 90% for AI mode

#### Business Metrics
- Entity extraction accuracy: > 95%
- Document processing throughput: 1000/hour
- System availability: 99.9% uptime
- API response time: < 500ms for pattern endpoints

### 10.5 Final Recommendations

1. **Make Pattern Integration THE Top Priority**
   - This is blocking 93% of system capability
   - Every day of delay costs extraction quality

2. **Establish Single Source of Truth**
   - All patterns in PatternLoader
   - No hardcoded patterns anywhere
   - Version control for all patterns

3. **Invest in Pattern Development**
   - Hire legal pattern experts
   - Create pattern development tools
   - Build pattern testing infrastructure

4. **Monitor Everything**
   - Pattern effectiveness metrics
   - Performance regression alerts
   - Memory usage tracking
   - GPU utilization monitoring

5. **Plan for Scale**
   - Horizontal scaling strategy
   - Distributed processing architecture
   - Cloud-native deployment
   - Auto-scaling based on load

---

## Appendices

### Appendix A: Complete Pattern File List (74 files)

#### Federal Patterns (5 files)
- /federal/supreme_court.yaml
- /federal/circuit_courts.yaml
- /federal/district_courts.yaml
- /federal/bankruptcy_courts.yaml
- /federal/specialized_courts.yaml

#### State Patterns (50 files)
- One file per state (e.g., /states/alabama.yaml)
- Each containing 12-19 state-specific patterns

#### Client Patterns (14 files)
- /client/case_citations.yaml
- /client/statutory_citations.yaml
- /client/dates.yaml
- /client/monetary_amounts.yaml
- /client/legal_terms.yaml
- /client/contracts.yaml
- /client/parties.yaml
- /client/courts.yaml
- /client/documents.yaml
- /client/procedures.yaml
- /client/remedies.yaml
- /client/specialized/*.yaml (3 files)

#### Comprehensive Patterns (4 files)
- /comprehensive/all_courts.yaml
- /comprehensive/all_citations.yaml
- /comprehensive/all_entities.yaml
- /comprehensive/bluebook_compliant.yaml

#### Legal Patterns (1 file)
- /legal/legal_structure.yaml

### Appendix B: Key Integration Points

- **vLLM Service** (Port 8080): Required for ai_enhanced mode
- **Log Service** (Port 8001): Centralized logging
- **Document Upload Service** (Port 8008): Document processing
- **GraphRAG Service** (Port 8010): Entity relationship mapping
- **Supabase**: Entity storage and retrieval

---

**Document Version**: 1.0.0  
**Total Sections**: 10 + Appendices  
**Last Updated**: September 10, 2025  
**Next Review**: October 1, 2025

**Authoritative Source**: This document represents the complete technical specification for the Entity Extraction Service entity-types and patterns endpoints, compiled from comprehensive multi-agent analysis. It consolidates findings from backend-engineer, legal-data-engineer, regex-expert, performance-engineer, and documentation-engineer into a single comprehensive reference.

## Summary of Critical Findings

1. **Pattern System Disconnect**: 1,156 patterns loaded but only 85 used (93% waste)
2. **Entity Coverage Gap**: 93 entity types without patterns (34% gap)
3. **Performance Achievement**: 295x speedup after optimization
4. **Cache Issue**: -13.3% performance with cache enabled
5. **Memory Optimization**: 5x reduction (40GB → 7.8GB)
6. **Bluebook Compliance**: 84.7% patterns compliant
7. **GPU Utilization**: 94% after optimization
8. **Throughput**: 33,618 chars/sec achieved

**IMMEDIATE ACTION REQUIRED**: Fix PatternLoader/EntityExtractionClient disconnect to unlock 93% of unused patterns.

