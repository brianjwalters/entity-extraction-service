# Entity Extraction Service Integration Guide

**Version**: 2.0.1
**Service**: Entity Extraction Service
**Base URL**: http://10.10.0.87:8007
**Last Updated**: 2025-10-30

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Extraction Modes](#extraction-modes)
4. [Wave-Based Extraction](#wave-based-extraction)
5. [Large Document Handling](#large-document-handling)
6. [Batch Processing](#batch-processing)
7. [Entity Deduplication](#entity-deduplication)
8. [Error Handling](#error-handling)
9. [Integration Patterns](#integration-patterns)
10. [Performance Optimization](#performance-optimization)
11. [Best Practices](#best-practices)

---

## Overview

The Entity Extraction Service provides advanced entity extraction using **195+ entity types** across **4 extraction waves**, with support for regex, AI-enhanced, and hybrid modes.

### Key Features

- **Wave System v2**: Intelligent 4-wave extraction for comprehensive entity coverage
- **Multi-Mode Extraction**: Regex, AI-enhanced, and hybrid strategies
- **Smart Document Routing**: Automatic strategy selection based on document size
- **LurisEntityV2 Schema**: Standardized entity format across all services
- **Direct vLLM Integration**: High-performance extraction using vLLM Instruct (Port 8080) and Thinking (Port 8082) services

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 Entity Extraction Service                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐      ┌────────────────┐            │
│  │ Document Router│─────▶│  Orchestrator  │            │
│  │ (Size-based)   │      │  (Wave Manager)│            │
│  └────────────────┘      └────────────────┘            │
│                                │                         │
│                    ┌───────────┴───────────┐            │
│                    ▼                       ▼            │
│          ┌─────────────────┐    ┌─────────────────┐    │
│          │ Regex Engine    │    │  vLLM Clients   │    │
│          │ (Pattern Match) │    │ (AI Extraction) │    │
│          └─────────────────┘    └─────────────────┘    │
│                    │                       │            │
│                    └───────────┬───────────┘            │
│                                ▼                         │
│                    ┌─────────────────────┐              │
│                    │ LurisEntityV2       │              │
│                    │ Schema Validator    │              │
│                    └─────────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Basic Entity Extraction

Extract entities from a legal document using the primary v2 endpoint:

#### Python Example

```python
import httpx
import asyncio
from typing import List, Dict, Any

async def extract_entities(document_text: str) -> List[Dict[str, Any]]:
    """
    Extract entities from document using Wave System v2.

    Args:
        document_text: Full document text

    Returns:
        List of entities in LurisEntityV2 format
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                "document_id": "doc_001",  # Optional
                "metadata": {
                    "source": "supreme_court",
                    "year": 2024
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        return result["entities"]


# Usage example
text = """
IN THE SUPREME COURT OF THE UNITED STATES

UNITED STATES v. ZACKEY RAHIMI

No. 22–6640

Decided June 21, 2024

The Second Amendment protects the right to keep and bear arms for
self-defense. See District of Columbia v. Heller, 554 U.S. 570 (2008).
This case concerns 18 U.S.C. § 922(g)(8), which prohibits individuals
subject to domestic violence restraining orders from possessing firearms.
"""

entities = asyncio.run(extract_entities(text))

# Display results
for entity in entities:
    print(f"{entity['entity_type']}: {entity['text']}")
    print(f"  Confidence: {entity['confidence']:.2f}")
    print(f"  Position: {entity['start_pos']}-{entity['end_pos']}")
    print(f"  Method: {entity['extraction_method']}")
    print()

# Example output:
# CASE_CITATION: UNITED STATES v. ZACKEY RAHIMI
#   Confidence: 0.98
#   Position: 35-68
#   Method: ai_enhanced
#
# CASE_NUMBER: No. 22–6640
#   Confidence: 0.95
#   Position: 70-82
#   Method: regex
#
# CASE_CITATION: District of Columbia v. Heller, 554 U.S. 570 (2008)
#   Confidence: 0.97
#   Position: 189-237
#   Method: pattern
#
# STATUTE_CITATION: 18 U.S.C. § 922(g)(8)
#   Confidence: 0.99
#   Position: 256-278
#   Method: regex
```

#### TypeScript Example

```typescript
interface LurisEntityV2 {
    id: string;
    text: string;
    entity_type: string;
    start_pos: number;
    end_pos: number;
    confidence: number;
    extraction_method: string;
    subtype?: string;
    category?: string;
    metadata: Record<string, any>;
    created_at: number;
}

interface ExtractionResponse {
    document_id: string;
    entities: LurisEntityV2[];
    routing_decision: {
        strategy: string;
        prompt_version: string;
        estimated_tokens: number;
        estimated_duration: number;
    };
    size_info: {
        chars: number;
        tokens: number;
        category: string;
    };
    processing_stats: {
        duration_seconds: number;
        entities_extracted: number;
        waves_executed: number;
    };
}

async function extractEntities(documentText: string): Promise<LurisEntityV2[]> {
    const response = await fetch('http://10.10.0.87:8007/api/v2/process/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            document_text: documentText,
            document_id: 'doc_001',
            metadata: {
                source: 'supreme_court',
                year: 2024
            }
        })
    });

    if (!response.ok) {
        throw new Error(`Extraction failed: ${response.status} ${response.statusText}`);
    }

    const result: ExtractionResponse = await response.json();
    return result.entities;
}

// Usage
const text = `IN THE SUPREME COURT OF THE UNITED STATES...`;

extractEntities(text).then(entities => {
    entities.forEach(entity => {
        console.log(`${entity.entity_type}: ${entity.text}`);
        console.log(`  Confidence: ${entity.confidence.toFixed(2)}`);
        console.log(`  Position: ${entity.start_pos}-${entity.end_pos}`);
        console.log(`  Method: ${entity.extraction_method}\n`);
    });
}).catch(error => {
    console.error('Extraction error:', error);
});
```

---

## Extraction Modes

The service supports multiple extraction modes based on document size and complexity.

### Understanding Extraction Strategies

The **DocumentRouter** automatically selects the optimal strategy based on document characteristics:

| Strategy | Document Size | Speed | Accuracy | Use Case |
|----------|---------------|-------|----------|----------|
| **SINGLE_PASS** | < 5K chars | Very Fast (~2s) | 90-92% | Short documents, quick extraction |
| **THREE_WAVE** | 5-150K chars | Fast (~5-10s) | 95-97% | Standard legal documents |
| **FOUR_WAVE** | 5-150K chars | Medium (~12-18s) | 98-99% | Complex documents requiring relationships |
| **THREE_WAVE_CHUNKED** | > 150K chars | Slow (~30-60s) | 96-98% | Large documents requiring chunking |

### Automatic Mode Selection

The service automatically selects the best strategy:

```python
async def extract_with_automatic_routing(document_text: str):
    """
    Extract entities with automatic strategy selection.
    The service analyzes document size and complexity.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text
                # No strategy specified - automatic routing
            }
        )
        result = response.json()

        # Check which strategy was selected
        strategy = result["routing_decision"]["strategy"]
        print(f"Strategy selected: {strategy}")
        print(f"Document size: {result['size_info']['chars']} chars")
        print(f"Estimated tokens: {result['routing_decision']['estimated_tokens']}")

        return result["entities"]
```

### Manual Strategy Override

Override automatic routing for specific requirements:

```python
async def extract_with_manual_strategy(
    document_text: str,
    force_strategy: str = "three_wave"
):
    """
    Force a specific extraction strategy.

    Args:
        document_text: Document text
        force_strategy: "single_pass", "three_wave", "four_wave", "three_wave_chunked"
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                "metadata": {
                    "force_strategy": force_strategy  # Override routing
                }
            }
        )
        return response.json()["entities"]
```

### Strategy Comparison

```python
async def compare_strategies(document_text: str):
    """
    Compare results across different extraction strategies.
    Useful for understanding accuracy/speed tradeoffs.
    """
    strategies = ["single_pass", "three_wave", "four_wave"]
    results = {}

    async with httpx.AsyncClient(timeout=180.0) as client:
        for strategy in strategies:
            start_time = time.time()

            response = await client.post(
                "http://10.10.0.87:8007/api/v2/process/extract",
                json={
                    "document_text": document_text,
                    "metadata": {"force_strategy": strategy}
                }
            )

            elapsed = time.time() - start_time
            data = response.json()

            results[strategy] = {
                "entities": len(data["entities"]),
                "duration": elapsed,
                "avg_confidence": sum(e["confidence"] for e in data["entities"]) / len(data["entities"]),
                "waves_executed": data["processing_stats"]["waves_executed"]
            }

    # Print comparison
    print("Strategy Comparison:")
    print(f"{'Strategy':<20} {'Entities':<10} {'Duration':<12} {'Avg Conf':<12} {'Waves':<8}")
    print("-" * 70)
    for strategy, stats in results.items():
        print(f"{strategy:<20} {stats['entities']:<10} {stats['duration']:<12.2f} {stats['avg_confidence']:<12.2f} {stats['waves_executed']:<8}")

    return results
```

---

## Wave-Based Extraction

The Entity Extraction Service uses a **4-wave extraction system** for comprehensive entity coverage.

### Understanding Entity Waves

Entities are organized into 4 extraction waves, processed sequentially:

#### Wave 1: Core Legal Entities (92 types)
- **Purpose**: Extract fundamental legal entities
- **Entity Types**: Federal citations, case citations, courts, parties, judges
- **Processing Time**: ~2-3 seconds
- **Confidence Threshold**: ≥ 0.85 (high confidence required)

**Example Entities**:
- `CASE_CITATION`: "United States v. Rahimi"
- `STATUTE_CITATION`: "18 U.S.C. § 922(g)(8)"
- `FEDERAL_COURT`: "Supreme Court of the United States"
- `PARTY`: "Zackey Rahimi"
- `JUDGE`: "Chief Justice Roberts"

#### Wave 2: Procedural & Financial (29 types)
- **Purpose**: Extract time-sensitive and monetary information
- **Entity Types**: Dates, deadlines, damages, fees, case numbers
- **Processing Time**: ~1-2 seconds
- **Confidence Threshold**: ≥ 0.80 (high-medium confidence)

**Example Entities**:
- `DATE`: "June 21, 2024"
- `FILING_DATE`: "Filed: March 15, 2024"
- `MONETARY_AMOUNT`: "$1,500,000"
- `DAMAGES`: "compensatory damages in the amount of $500,000"
- `CASE_NUMBER`: "No. 22-6640"

#### Wave 3: Supporting Elements (40 types)
- **Purpose**: Extract contextual information and supporting entities
- **Entity Types**: Legal principles, evidence, locations, organizations
- **Processing Time**: ~2-3 seconds
- **Confidence Threshold**: ≥ 0.75 (medium confidence)

**Example Entities**:
- `LEGAL_PRINCIPLE`: "strict scrutiny"
- `EVIDENCE`: "Exhibit A: Firearm purchase records"
- `ADDRESS`: "1234 Main St, Washington, DC 20001"
- `LAW_FIRM`: "Smith & Associates LLP"
- `GOVERNMENT_ENTITY`: "Department of Justice"

#### Wave 4: Relationships (34 types)
- **Purpose**: Extract inter-entity relationships
- **Entity Types**: Citations to, distinguished from, overruled by, relies on
- **Processing Time**: ~3-5 seconds (uses Thinking model for complex reasoning)
- **Confidence Threshold**: ≥ 0.70 (lower threshold for relationship detection)

**Example Relationships**:
- `CITES_CASE`: United States v. Rahimi → District of Columbia v. Heller
- `DISTINGUISHED_FROM`: Current case → Prior precedent
- `OVERRULED_BY`: Old case → New case
- `RELIES_ON_STATUTE`: Case → 18 U.S.C. § 922(g)(8)

### Wave Execution Flow

```python
async def understand_wave_execution(document_text: str):
    """
    Demonstrate wave-based extraction with detailed logging.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                "metadata": {
                    "force_strategy": "four_wave",  # All 4 waves
                    "include_wave_metadata": True   # Include per-wave stats
                }
            }
        )

        result = response.json()

        # Analyze entities by wave
        wave_stats = {}
        for entity in result["entities"]:
            wave = entity.get("metadata", {}).get("wave_number", 0)
            if wave not in wave_stats:
                wave_stats[wave] = []
            wave_stats[wave].append(entity)

        # Print wave statistics
        print("Wave Execution Summary:")
        print(f"Total waves: {result['processing_stats']['waves_executed']}")
        print(f"Total entities: {len(result['entities'])}\n")

        for wave_num in sorted(wave_stats.keys()):
            entities = wave_stats[wave_num]
            avg_conf = sum(e["confidence"] for e in entities) / len(entities)

            print(f"Wave {wave_num}:")
            print(f"  Entities extracted: {len(entities)}")
            print(f"  Average confidence: {avg_conf:.3f}")
            print(f"  Entity types: {set(e['entity_type'] for e in entities)}")
            print()

        return result
```

### Wave-Specific Extraction

Extract only specific waves for faster processing:

```python
async def extract_specific_waves(
    document_text: str,
    waves: List[int] = [1, 2]  # Only Waves 1 and 2
):
    """
    Extract entities from specific waves only.

    Args:
        document_text: Document text
        waves: List of wave numbers to execute (1-4)

    Returns:
        Entities from specified waves only
    """
    # Note: Currently the API executes all waves up to the highest requested
    # If you request waves [1, 3], it will execute waves 1, 2, and 3

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                "metadata": {
                    "force_strategy": "three_wave" if max(waves) <= 3 else "four_wave"
                }
            }
        )

        result = response.json()

        # Filter entities by requested waves
        filtered_entities = [
            e for e in result["entities"]
            if e.get("metadata", {}).get("wave_number") in waves
        ]

        return filtered_entities


# Example: Extract only core legal entities (Wave 1)
core_entities = await extract_specific_waves(text, waves=[1])

# Example: Extract core + procedural (Waves 1-2)
essential_entities = await extract_specific_waves(text, waves=[1, 2])

# Example: Extract all except relationships (Waves 1-3)
no_relationships = await extract_specific_waves(text, waves=[1, 2, 3])
```

---

## Large Document Handling

For documents exceeding 150K characters, the service automatically uses **smart chunking** with the `THREE_WAVE_CHUNKED` strategy.

### Automatic Chunking

```python
async def extract_large_document(document_text: str):
    """
    Extract entities from large document with automatic chunking.

    Documents > 150K chars automatically use THREE_WAVE_CHUNKED strategy.
    """
    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                # Automatic: Service detects large doc and chunks
            }
        )

        result = response.json()

        print(f"Document size: {result['size_info']['chars']} chars")
        print(f"Strategy used: {result['routing_decision']['strategy']}")
        print(f"Chunks processed: {result['processing_stats'].get('chunks_processed', 'N/A')}")
        print(f"Total entities: {len(result['entities'])}")

        return result["entities"]
```

### Manual Chunking Configuration

Control chunking parameters for fine-tuning:

```python
async def extract_with_custom_chunking(
    document_text: str,
    chunk_size: int = 8000,
    chunk_overlap: int = 500
):
    """
    Extract entities with custom chunking parameters.

    Args:
        document_text: Document text
        chunk_size: Size of each chunk in characters (default: 8000)
        chunk_overlap: Overlap between chunks to prevent entity splitting (default: 500)
    """
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                "metadata": {
                    "enable_smart_chunking": True,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                }
            }
        )

        return response.json()
```

### Smart Chunking Features

The chunking system includes intelligent features:

1. **Boundary Preservation**: Never splits entities mid-text
2. **Position Adjustment**: Adjusts entity positions across chunks
3. **Overlap Deduplication**: Removes duplicate entities in overlap regions
4. **Confidence Preservation**: Maintains entity confidence scores across chunks

```python
async def demonstrate_smart_chunking(long_document: str):
    """
    Demonstrate smart chunking features.
    """
    # Extract with chunking
    result = await extract_with_custom_chunking(
        long_document,
        chunk_size=10000,
        chunk_overlap=1000
    )

    # Analyze chunk boundaries
    chunk_metadata = result.get("processing_stats", {}).get("chunk_metadata", [])

    print("Chunk Analysis:")
    for i, chunk_info in enumerate(chunk_metadata):
        print(f"\nChunk {i + 1}:")
        print(f"  Start position: {chunk_info['start_pos']}")
        print(f"  End position: {chunk_info['end_pos']}")
        print(f"  Size: {chunk_info['size']} chars")
        print(f"  Entities extracted: {chunk_info['entities_count']}")
        print(f"  Deduplication: {chunk_info.get('duplicates_removed', 0)} duplicates removed")

    return result["entities"]
```

---

## Batch Processing

Process multiple documents efficiently using parallel requests.

### Simple Batch Processing

```python
import asyncio
from typing import List, Dict, Tuple

async def batch_extract_simple(documents: List[Tuple[str, str]]):
    """
    Extract entities from multiple documents in parallel.

    Args:
        documents: List of (document_id, document_text) tuples

    Returns:
        Dict mapping document_id to list of entities
    """
    async def extract_single(doc_id: str, text: str):
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://10.10.0.87:8007/api/v2/process/extract",
                json={
                    "document_text": text,
                    "document_id": doc_id
                }
            )
            result = response.json()
            return doc_id, result["entities"]

    # Execute all extractions in parallel
    tasks = [extract_single(doc_id, text) for doc_id, text in documents]
    results = await asyncio.gather(*tasks)

    return {doc_id: entities for doc_id, entities in results}


# Usage
documents = [
    ("case_001", "IN THE SUPREME COURT..."),
    ("case_002", "IN THE DISTRICT COURT..."),
    ("case_003", "IN THE COURT OF APPEALS...")
]

batch_results = await batch_extract_simple(documents)

for doc_id, entities in batch_results.items():
    print(f"{doc_id}: {len(entities)} entities extracted")
```

### Advanced Batch Processing with Rate Limiting

```python
from asyncio import Semaphore

async def batch_extract_with_rate_limit(
    documents: List[Tuple[str, str]],
    max_concurrent: int = 5
):
    """
    Extract entities with rate limiting to prevent overwhelming the service.

    Args:
        documents: List of (document_id, document_text) tuples
        max_concurrent: Maximum concurrent requests (default: 5)

    Returns:
        Dict mapping document_id to extraction results
    """
    semaphore = Semaphore(max_concurrent)

    async def extract_with_limit(doc_id: str, text: str):
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        "http://10.10.0.87:8007/api/v2/process/extract",
                        json={
                            "document_text": text,
                            "document_id": doc_id
                        }
                    )
                    response.raise_for_status()
                    result = response.json()

                    return {
                        "doc_id": doc_id,
                        "success": True,
                        "entities": result["entities"],
                        "stats": result["processing_stats"]
                    }
            except Exception as e:
                logger.error(f"Extraction failed for {doc_id}: {e}")
                return {
                    "doc_id": doc_id,
                    "success": False,
                    "error": str(e)
                }

    tasks = [extract_with_limit(doc_id, text) for doc_id, text in documents]
    results = await asyncio.gather(*tasks)

    # Separate successful and failed extractions
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"Batch completed: {len(successful)} successful, {len(failed)} failed")

    return {
        "successful": {r["doc_id"]: r["entities"] for r in successful},
        "failed": {r["doc_id"]: r["error"] for r in failed},
        "stats": {
            "total": len(documents),
            "success_rate": len(successful) / len(documents)
        }
    }
```

### Batch Processing with Progress Tracking

```python
from tqdm.asyncio import tqdm

async def batch_extract_with_progress(documents: List[Tuple[str, str]]):
    """
    Extract entities with progress bar for monitoring.
    """
    results = {}

    async with httpx.AsyncClient(timeout=120.0) as client:
        tasks = []
        for doc_id, text in documents:
            task = client.post(
                "http://10.10.0.87:8007/api/v2/process/extract",
                json={
                    "document_text": text,
                    "document_id": doc_id
                }
            )
            tasks.append((doc_id, task))

        # Execute with progress bar
        for doc_id, task in tqdm(tasks, desc="Extracting entities"):
            response = await task
            result = response.json()
            results[doc_id] = result["entities"]

    return results
```

---

## Entity Deduplication

The service includes built-in deduplication, but additional post-processing may be needed for specific use cases.

### Built-in Deduplication

The extraction service automatically deduplicates:
- Entities in chunk overlap regions
- Entities extracted by multiple waves
- Entities with exact text matches at same positions

### Custom Deduplication Strategies

#### Strategy 1: Exact Text Match

```python
def deduplicate_exact_text(entities: List[Dict]) -> List[Dict]:
    """
    Deduplicate entities with exact text matches.
    Keep highest confidence entity for each unique text.

    Args:
        entities: List of LurisEntityV2 entities

    Returns:
        Deduplicated entity list
    """
    from collections import defaultdict

    # Group by entity_type and normalized text
    groups = defaultdict(list)

    for entity in entities:
        # Normalize text
        normalized = entity["text"].lower().strip()
        key = (entity["entity_type"], normalized)
        groups[key].append(entity)

    # Keep highest confidence entity from each group
    deduped = []
    for group in groups.values():
        best = max(group, key=lambda e: e["confidence"])
        deduped.append(best)

    return deduped
```

#### Strategy 2: Position-Based Deduplication

```python
def deduplicate_overlapping_positions(entities: List[Dict]) -> List[Dict]:
    """
    Remove entities with overlapping positions.
    Keep entity with higher confidence when positions overlap.

    Args:
        entities: List of LurisEntityV2 entities

    Returns:
        Deduplicated entity list
    """
    # Sort by start position
    sorted_entities = sorted(entities, key=lambda e: e["start_pos"])

    deduped = []
    for entity in sorted_entities:
        # Check if overlaps with any kept entity
        overlaps = False
        for kept in deduped:
            if (entity["start_pos"] < kept["end_pos"] and
                entity["end_pos"] > kept["start_pos"]):
                # Overlaps - keep higher confidence
                if entity["confidence"] > kept["confidence"]:
                    deduped.remove(kept)
                    deduped.append(entity)
                overlaps = True
                break

        if not overlaps:
            deduped.append(entity)

    return deduped
```

#### Strategy 3: Fuzzy Text Matching

```python
from difflib import SequenceMatcher

def deduplicate_fuzzy_match(
    entities: List[Dict],
    similarity_threshold: float = 0.9
) -> List[Dict]:
    """
    Deduplicate entities using fuzzy text matching.

    Args:
        entities: List of LurisEntityV2 entities
        similarity_threshold: Minimum similarity ratio (0.0-1.0)

    Returns:
        Deduplicated entity list
    """
    def text_similarity(text1: str, text2: str) -> float:
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    deduped = []

    for entity in entities:
        # Check similarity with all kept entities
        is_duplicate = False
        for kept in deduped:
            if (entity["entity_type"] == kept["entity_type"] and
                text_similarity(entity["text"], kept["text"]) >= similarity_threshold):
                # Duplicate found - keep higher confidence
                if entity["confidence"] > kept["confidence"]:
                    deduped.remove(kept)
                    deduped.append(entity)
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(entity)

    return deduped
```

### Combined Deduplication Pipeline

```python
async def extract_and_deduplicate(
    document_text: str,
    dedup_strategy: str = "fuzzy"
):
    """
    Extract entities and apply custom deduplication.

    Args:
        document_text: Document text
        dedup_strategy: "exact", "position", "fuzzy", or "all"

    Returns:
        Deduplicated entities
    """
    # Extract entities
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={"document_text": document_text}
        )
        result = response.json()
        entities = result["entities"]

    # Apply deduplication
    if dedup_strategy == "exact":
        entities = deduplicate_exact_text(entities)
    elif dedup_strategy == "position":
        entities = deduplicate_overlapping_positions(entities)
    elif dedup_strategy == "fuzzy":
        entities = deduplicate_fuzzy_match(entities)
    elif dedup_strategy == "all":
        # Apply all strategies sequentially
        entities = deduplicate_exact_text(entities)
        entities = deduplicate_overlapping_positions(entities)
        entities = deduplicate_fuzzy_match(entities)

    return entities
```

---

## Error Handling

Robust error handling is essential for production integration.

### Common Error Scenarios

#### 1. Service Unavailable

```python
from httpx import HTTPStatusError, TimeoutException, ConnectError

async def extract_with_retry(
    document_text: str,
    max_retries: int = 3,
    retry_delay: float = 2.0
):
    """
    Extract entities with automatic retry on failure.

    Args:
        document_text: Document text
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Extraction result or None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://10.10.0.87:8007/api/v2/process/extract",
                    json={"document_text": document_text}
                )
                response.raise_for_status()
                return response.json()

        except ConnectError as e:
            logger.warning(f"Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise

        except TimeoutException as e:
            logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise

        except HTTPStatusError as e:
            if e.response.status_code >= 500:
                # Server error - retry
                logger.warning(f"Server error {e.response.status_code} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise
            else:
                # Client error - don't retry
                raise

    return None
```

#### 2. Insufficient Entities

```python
async def extract_with_quality_check(
    document_text: str,
    min_entities: int = 5,
    min_avg_confidence: float = 0.7
):
    """
    Extract entities with quality validation.

    Args:
        document_text: Document text
        min_entities: Minimum expected entities
        min_avg_confidence: Minimum average confidence

    Returns:
        Entities if quality checks pass

    Raises:
        ValueError: If quality checks fail
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={"document_text": document_text}
        )
        result = response.json()
        entities = result["entities"]

    # Quality check 1: Minimum entity count
    if len(entities) < min_entities:
        logger.warning(f"Only {len(entities)} entities extracted (minimum: {min_entities})")
        logger.warning("Document may be poor quality or extraction may have failed")

    # Quality check 2: Average confidence
    if entities:
        avg_conf = sum(e["confidence"] for e in entities) / len(entities)
        if avg_conf < min_avg_confidence:
            logger.warning(f"Low average confidence: {avg_conf:.3f} (minimum: {min_avg_confidence})")
            logger.warning("Consider using hybrid mode for better accuracy")

    return entities
```

#### 3. Request Timeout

```python
async def extract_with_adaptive_timeout(document_text: str):
    """
    Extract entities with timeout based on document size.

    Args:
        document_text: Document text

    Returns:
        Extraction result
    """
    # Calculate appropriate timeout based on document size
    doc_size = len(document_text)

    if doc_size < 10000:
        timeout = 30.0  # 30 seconds for small docs
    elif doc_size < 50000:
        timeout = 60.0  # 1 minute for medium docs
    elif doc_size < 150000:
        timeout = 120.0  # 2 minutes for large docs
    else:
        timeout = 300.0  # 5 minutes for very large docs

    logger.info(f"Document size: {doc_size} chars, timeout: {timeout}s")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "http://10.10.0.87:8007/api/v2/process/extract",
                json={"document_text": document_text}
            )
            return response.json()

    except TimeoutException:
        logger.error(f"Extraction timeout after {timeout}s")
        logger.info("Consider using chunking for this document size")
        raise
```

#### 4. Invalid Response Format

```python
from pydantic import BaseModel, ValidationError

class EntitySchema(BaseModel):
    id: str
    text: str
    entity_type: str
    start_pos: int
    end_pos: int
    confidence: float
    extraction_method: str

async def extract_with_validation(document_text: str):
    """
    Extract entities with response schema validation.

    Args:
        document_text: Document text

    Returns:
        Validated entities

    Raises:
        ValidationError: If response doesn't match schema
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={"document_text": document_text}
        )
        result = response.json()

    # Validate each entity
    validated_entities = []
    for entity_dict in result["entities"]:
        try:
            entity = EntitySchema(**entity_dict)
            validated_entities.append(entity_dict)
        except ValidationError as e:
            logger.error(f"Invalid entity format: {e}")
            logger.error(f"Entity data: {entity_dict}")

    if len(validated_entities) < len(result["entities"]):
        logger.warning(f"{len(result['entities']) - len(validated_entities)} entities failed validation")

    return validated_entities
```

---

## Integration Patterns

Common integration patterns for production systems.

### Pattern 1: Complete Document Processing Pipeline

```python
async def document_processing_pipeline(file_path: str):
    """
    Complete document processing pipeline:
    1. Upload document (convert to markdown)
    2. Extract entities
    3. Build knowledge graph
    4. Store results

    Args:
        file_path: Path to document file

    Returns:
        Complete processing results
    """
    # Stage 1: Upload and convert document
    async with httpx.AsyncClient(timeout=120.0) as upload_client:
        with open(file_path, 'rb') as f:
            upload_response = await upload_client.post(
                "http://10.10.0.87:8008/upload",
                files={"file": f}
            )
        upload_data = upload_response.json()
        markdown = upload_data["markdown_content"]
        document_id = upload_data["document_id"]

    logger.info(f"Document uploaded: {document_id}")

    # Stage 2: Extract entities
    async with httpx.AsyncClient(timeout=180.0) as extract_client:
        extract_response = await extract_client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": markdown,
                "document_id": document_id
            }
        )
        extract_data = extract_response.json()
        entities = extract_data["entities"]

    logger.info(f"Entities extracted: {len(entities)}")

    # Stage 3: Build knowledge graph
    async with httpx.AsyncClient(timeout=180.0) as graph_client:
        graph_response = await graph_client.post(
            "http://10.10.0.87:8010/graph/create",
            json={
                "document_id": document_id,
                "entities": entities,
                "metadata": {
                    "source_file": file_path,
                    "processing_date": datetime.now().isoformat()
                }
            }
        )
        graph_data = graph_response.json()

    logger.info(f"Knowledge graph created: {graph_data['graph_id']}")

    # Stage 4: Store in database
    # (Implementation depends on your storage layer)

    return {
        "document_id": document_id,
        "entities": entities,
        "graph": graph_data,
        "stats": {
            "entities_extracted": len(entities),
            "processing_time": extract_data["processing_stats"]["duration_seconds"]
        }
    }
```

### Pattern 2: Real-Time Extraction from Streaming Text

```python
from typing import AsyncIterator

async def real_time_extraction(
    text_stream: AsyncIterator[str],
    buffer_size: int = 5000
):
    """
    Extract entities from streaming text in real-time.

    Args:
        text_stream: Async iterator yielding text chunks
        buffer_size: Size of buffer before triggering extraction

    Yields:
        Entities as they are extracted
    """
    buffer = ""
    all_entities = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        async for chunk in text_stream:
            buffer += chunk

            # Extract when buffer reaches threshold
            if len(buffer) >= buffer_size:
                response = await client.post(
                    "http://10.10.0.87:8007/api/v2/process/extract",
                    json={
                        "document_text": buffer,
                        "metadata": {"force_strategy": "single_pass"}  # Fast extraction
                    }
                )
                result = response.json()

                # Yield new entities
                for entity in result["entities"]:
                    if entity not in all_entities:
                        all_entities.append(entity)
                        yield entity

                # Reset buffer
                buffer = ""

        # Process remaining buffer
        if buffer:
            response = await client.post(
                "http://10.10.0.87:8007/api/v2/process/extract",
                json={"document_text": buffer}
            )
            result = response.json()

            for entity in result["entities"]:
                if entity not in all_entities:
                    yield entity


# Usage example
async def process_streaming_document(text_stream):
    async for entity in real_time_extraction(text_stream):
        print(f"New entity: {entity['entity_type']} = {entity['text']}")
```

### Pattern 3: Multi-Stage Extraction with Enrichment

```python
async def multi_stage_extraction_with_enrichment(document_text: str):
    """
    Multi-stage extraction:
    1. Initial extraction (fast)
    2. Entity enrichment from external sources
    3. Relationship extraction (comprehensive)

    Args:
        document_text: Document text

    Returns:
        Enriched entities with relationships
    """
    # Stage 1: Fast initial extraction (Waves 1-2 only)
    async with httpx.AsyncClient(timeout=60.0) as client:
        initial_response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                "metadata": {"force_strategy": "three_wave"}  # Skip relationships
            }
        )
        initial_result = initial_response.json()
        entities = initial_result["entities"]

    logger.info(f"Stage 1: {len(entities)} entities extracted")

    # Stage 2: Enrich entities with external data
    enriched_entities = []
    for entity in entities:
        # Example: Look up case citations in database
        if entity["entity_type"] == "CASE_CITATION":
            # Call external API or database
            case_details = await lookup_case_citation(entity["text"])
            if case_details:
                entity["metadata"]["case_details"] = case_details

        # Example: Validate statute citations
        elif entity["entity_type"] == "STATUTE_CITATION":
            statute_valid = await validate_statute(entity["text"])
            entity["metadata"]["valid"] = statute_valid

        enriched_entities.append(entity)

    logger.info(f"Stage 2: {len(enriched_entities)} entities enriched")

    # Stage 3: Extract relationships with enriched context
    async with httpx.AsyncClient(timeout=120.0) as client:
        relationship_response = await client.post(
            "http://10.10.0.87:8007/api/v1/extract/relationships",
            json={
                "document_text": document_text,
                "existing_entities": enriched_entities
            }
        )
        relationships = relationship_response.json()["relationships"]

    logger.info(f"Stage 3: {len(relationships)} relationships extracted")

    return {
        "entities": enriched_entities,
        "relationships": relationships
    }


async def lookup_case_citation(citation: str) -> Dict:
    """Look up case citation details from external source."""
    # Placeholder - implement actual lookup
    return {"court": "Supreme Court", "year": 2024}

async def validate_statute(statute: str) -> bool:
    """Validate statute citation."""
    # Placeholder - implement actual validation
    return True
```

### Pattern 4: Incremental Document Analysis

```python
async def incremental_document_analysis(
    document_id: str,
    new_content: str,
    existing_entities: List[Dict]
):
    """
    Analyze new content added to existing document.
    Extract only new entities without re-processing entire document.

    Args:
        document_id: Existing document ID
        new_content: New content to analyze
        existing_entities: Previously extracted entities

    Returns:
        Combined entity list with new entities
    """
    # Extract entities from new content only
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": new_content,
                "document_id": f"{document_id}_incremental"
            }
        )
        result = response.json()
        new_entities = result["entities"]

    # Merge with existing entities
    all_entities = existing_entities + new_entities

    # Deduplicate
    all_entities = deduplicate_exact_text(all_entities)

    logger.info(f"Incremental analysis: {len(new_entities)} new entities, {len(all_entities)} total")

    return all_entities
```

---

## Performance Optimization

Optimize extraction performance for production workloads.

### 1. Connection Pooling

```python
import httpx

class EntityExtractionClient:
    """
    Reusable client with connection pooling for high-performance extraction.
    """

    def __init__(self, base_url: str = "http://10.10.0.87:8007"):
        self.base_url = base_url
        # Create persistent client with connection pool
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=120.0,
            limits=httpx.Limits(
                max_connections=100,  # Total connection pool size
                max_keepalive_connections=20  # Keep-alive connections
            )
        )

    async def extract(self, document_text: str, **kwargs) -> List[Dict]:
        """Extract entities using pooled connection."""
        response = await self.client.post(
            "/api/v2/process/extract",
            json={
                "document_text": document_text,
                **kwargs
            }
        )
        return response.json()["entities"]

    async def close(self):
        """Close client and cleanup connections."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Usage
async def high_performance_extraction(documents: List[str]):
    async with EntityExtractionClient() as client:
        tasks = [client.extract(doc) for doc in documents]
        results = await asyncio.gather(*tasks)
    return results
```

### 2. Caching Strategy

```python
from functools import lru_cache
import hashlib

class CachingEntityExtractor:
    """
    Entity extractor with result caching.
    """

    def __init__(self):
        self.cache = {}
        self.client = EntityExtractionClient()

    def _cache_key(self, document_text: str, **kwargs) -> str:
        """Generate cache key from document and parameters."""
        content = f"{document_text}:{sorted(kwargs.items())}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def extract(self, document_text: str, **kwargs) -> List[Dict]:
        """Extract with caching."""
        cache_key = self._cache_key(document_text, **kwargs)

        # Check cache
        if cache_key in self.cache:
            logger.info(f"Cache hit for document {cache_key[:8]}")
            return self.cache[cache_key]

        # Cache miss - extract
        logger.info(f"Cache miss for document {cache_key[:8]}")
        entities = await self.client.extract(document_text, **kwargs)

        # Store in cache
        self.cache[cache_key] = entities

        return entities

    def clear_cache(self):
        """Clear result cache."""
        self.cache.clear()

    async def close(self):
        await self.client.close()
```

### 3. Parallel Processing with Batching

```python
async def optimized_batch_extraction(
    documents: List[str],
    batch_size: int = 10
):
    """
    Process documents in optimized batches.

    Args:
        documents: List of document texts
        batch_size: Number of concurrent extractions

    Returns:
        All extraction results
    """
    async with EntityExtractionClient() as client:
        all_results = []

        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            # Extract batch in parallel
            tasks = [client.extract(doc) for doc in batch]
            batch_results = await asyncio.gather(*tasks)

            all_results.extend(batch_results)

            logger.info(f"Processed batch {i // batch_size + 1}, "
                       f"documents {i + 1}-{min(i + batch_size, len(documents))}")

        return all_results
```

### 4. Strategy Selection for Performance

```python
async def performance_optimized_extraction(
    document_text: str,
    priority: str = "balanced"
):
    """
    Select extraction strategy based on performance priority.

    Args:
        document_text: Document text
        priority: "speed", "accuracy", or "balanced"

    Returns:
        Entities optimized for priority
    """
    doc_size = len(document_text)

    if priority == "speed":
        # Prioritize speed
        if doc_size < 10000:
            strategy = "single_pass"
        else:
            strategy = "three_wave"

    elif priority == "accuracy":
        # Prioritize accuracy
        if doc_size < 150000:
            strategy = "four_wave"
        else:
            strategy = "three_wave_chunked"

    else:  # balanced
        # Balance speed and accuracy
        if doc_size < 5000:
            strategy = "single_pass"
        elif doc_size < 100000:
            strategy = "three_wave"
        else:
            strategy = "three_wave_chunked"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://10.10.0.87:8007/api/v2/process/extract",
            json={
                "document_text": document_text,
                "metadata": {"force_strategy": strategy}
            }
        )
        return response.json()["entities"]
```

---

## Best Practices

### 1. Document Preparation

```python
def prepare_document_for_extraction(raw_text: str) -> str:
    """
    Prepare document text for optimal extraction.

    Args:
        raw_text: Raw document text

    Returns:
        Cleaned text ready for extraction
    """
    import re

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', raw_text)

    # Remove control characters
    text = ''.join(c for c in text if c.isprintable() or c in '\n\t')

    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove excessive newlines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Trim
    text = text.strip()

    return text


# Usage
raw_document = """
IN  THE   SUPREME    COURT...


Lots   of   weird     spacing...
"""

cleaned = prepare_document_for_extraction(raw_document)
entities = await extract_entities(cleaned)
```

### 2. Error Recovery

```python
async def extract_with_fallback(document_text: str):
    """
    Extract with automatic fallback to simpler strategy on failure.
    """
    strategies = ["four_wave", "three_wave", "single_pass"]

    for strategy in strategies:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://10.10.0.87:8007/api/v2/process/extract",
                    json={
                        "document_text": document_text,
                        "metadata": {"force_strategy": strategy}
                    }
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"Extraction succeeded with strategy: {strategy}")
                return result["entities"]

        except Exception as e:
            logger.warning(f"Strategy {strategy} failed: {e}")
            if strategy == strategies[-1]:
                # Last strategy failed
                raise
            else:
                logger.info(f"Trying fallback strategy...")
                continue
```

### 3. Monitoring and Logging

```python
import logging
import time

async def extract_with_monitoring(document_text: str):
    """
    Extract entities with comprehensive monitoring.
    """
    start_time = time.time()

    logger.info(f"Starting extraction, document size: {len(document_text)} chars")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://10.10.0.87:8007/api/v2/process/extract",
                json={"document_text": document_text}
            )
            response.raise_for_status()
            result = response.json()

        elapsed = time.time() - start_time
        entities = result["entities"]

        # Log success metrics
        logger.info(f"Extraction completed in {elapsed:.2f}s")
        logger.info(f"Entities extracted: {len(entities)}")
        logger.info(f"Strategy used: {result['routing_decision']['strategy']}")
        logger.info(f"Waves executed: {result['processing_stats']['waves_executed']}")

        # Log confidence distribution
        high_conf = sum(1 for e in entities if e["confidence"] >= 0.9)
        med_conf = sum(1 for e in entities if 0.7 <= e["confidence"] < 0.9)
        low_conf = sum(1 for e in entities if e["confidence"] < 0.7)

        logger.info(f"Confidence: High={high_conf}, Medium={med_conf}, Low={low_conf}")

        return entities

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Extraction failed after {elapsed:.2f}s: {e}")
        raise
```

### 4. Result Validation

```python
def validate_extraction_result(entities: List[Dict], document_text: str) -> bool:
    """
    Validate extraction result quality.

    Args:
        entities: Extracted entities
        document_text: Original document text

    Returns:
        True if result passes validation
    """
    # Check 1: Entities extracted
    if not entities:
        logger.warning("No entities extracted")
        return False

    # Check 2: Position validity
    for entity in entities:
        start = entity["start_pos"]
        end = entity["end_pos"]

        if start < 0 or end > len(document_text) or start >= end:
            logger.error(f"Invalid position: {entity}")
            return False

        # Check text matches position
        expected_text = document_text[start:end]
        if expected_text != entity["text"]:
            logger.warning(f"Text mismatch: expected '{expected_text}', got '{entity['text']}'")

    # Check 3: Confidence scores
    avg_confidence = sum(e["confidence"] for e in entities) / len(entities)
    if avg_confidence < 0.5:
        logger.warning(f"Low average confidence: {avg_confidence:.3f}")

    # Check 4: Required fields
    required_fields = ["id", "text", "entity_type", "start_pos", "end_pos", "confidence"]
    for entity in entities:
        missing = [f for f in required_fields if f not in entity]
        if missing:
            logger.error(f"Missing required fields: {missing}")
            return False

    return True
```

---

## Summary

This integration guide covers:

✅ **Quick Start** - Basic extraction examples in Python and TypeScript
✅ **Extraction Modes** - Understanding strategies and automatic routing
✅ **Wave-Based Extraction** - 4-wave system for comprehensive entity coverage
✅ **Large Document Handling** - Smart chunking for documents >150K chars
✅ **Batch Processing** - Parallel extraction with rate limiting
✅ **Entity Deduplication** - Multiple deduplication strategies
✅ **Error Handling** - Robust error handling with retry logic
✅ **Integration Patterns** - Common patterns for production systems
✅ **Performance Optimization** - Connection pooling, caching, batching
✅ **Best Practices** - Document preparation, monitoring, validation

### Next Steps

1. **Review API Documentation**: Read `/srv/luris/be/entity-extraction-service/api.md` for complete endpoint reference
2. **Understand LurisEntityV2**: Read `/srv/luris/be/entity-extraction-service/docs/LurisEntityV2_Specification.md` for schema details
3. **Explore Entity Types**: Check `/srv/luris/be/entity-extraction-service/docs/EntityType_Quick_Reference.md` for all 195+ entity types
4. **Test Integration**: Use examples from this guide to build your integration

### Support

For questions or issues:
- Check service health: `curl http://10.10.0.87:8007/api/v1/health/detailed`
- View API docs: http://10.10.0.87:8007/api/v1/docs
- Contact: Luris Engineering Team

---

**Last Updated**: 2025-10-30
**Version**: 2.0.1
**Service**: Entity Extraction Service
