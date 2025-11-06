"""
Unified Patterns API Endpoint for Entity Extraction Service.

This module provides a unified API endpoint to access both entity patterns
and relationship patterns from the pattern library.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Query, Request, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from collections import defaultdict
import yaml

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class EntityPatternInfo(BaseModel):
    """Information about entity patterns."""
    entity_type: str = Field(..., description="Entity type name")
    category: str = Field(..., description="Entity category")
    total_patterns: int = Field(..., description="Total number of unique patterns")
    total_examples: int = Field(..., description="Total number of examples")
    average_confidence: float = Field(..., description="Average confidence score")
    pattern_sources: Dict[str, int] = Field(..., description="Number of patterns from each source")
    patterns: Optional[List[Dict[str, Any]]] = Field(default=None, description="Pattern details if requested")
    examples: Optional[List[str]] = Field(default=None, description="Examples if requested")
    jurisdictions: List[str] = Field(default_factory=list, description="Jurisdictions covered")


class RelationshipPatternInfo(BaseModel):
    """Information about relationship patterns."""
    relationship_type: str = Field(..., description="Relationship type name")
    description: str = Field(..., description="Relationship description")
    source_entity: str = Field(..., description="Source entity type")
    target_entity: str = Field(..., description="Target entity type")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction (if applicable)")
    indicators: Optional[List[str]] = Field(default=None, description="Relationship indicators if requested")
    examples: Optional[List[str]] = Field(default=None, description="Examples if requested")
    pattern_file: Optional[str] = Field(None, description="Source pattern file")


class UnifiedPatternResponse(BaseModel):
    """Response for unified pattern endpoint."""
    type: str = Field(..., description="Type of patterns returned: entities, relationships, or all")
    total_count: int = Field(..., description="Total number of patterns returned")
    entities: Optional[List[EntityPatternInfo]] = Field(default=None, description="Entity patterns if requested")
    relationships: Optional[List[RelationshipPatternInfo]] = Field(default=None, description="Relationship patterns if requested")
    metadata: Dict[str, Any] = Field(..., description="Query metadata and statistics")


def categorize_entity_type(entity_type: str) -> str:
    """
    Categorize entity type into a high-level category.
    Reuses logic from entity_types.py but simplified.
    """
    entity_type_upper = entity_type.upper()

    # Courts and Judicial
    if any(term in entity_type_upper for term in ["COURT", "JUDGE", "JUSTICE", "MAGISTRATE"]):
        return "Courts and Judicial"

    # Case Citations
    if "CITATION" in entity_type_upper or "PARALLEL" in entity_type_upper:
        return "Citations"

    # Legal Parties
    if any(term in entity_type_upper for term in ["PARTY", "PLAINTIFF", "DEFENDANT", "APPELLANT", "APPELLEE", "PETITIONER", "RESPONDENT"]):
        return "Legal Parties"

    # Legal Professionals
    if any(term in entity_type_upper for term in ["ATTORNEY", "COUNSEL", "LAWYER", "LAW_FIRM"]):
        return "Legal Professionals"

    # Temporal
    if any(term in entity_type_upper for term in ["DATE", "TIME", "DEADLINE", "PERIOD"]):
        return "Temporal"

    # Financial
    if any(term in entity_type_upper for term in ["AMOUNT", "MONEY", "CURRENCY", "FINANCIAL"]):
        return "Financial"

    # Statutory
    if any(term in entity_type_upper for term in ["STATUTE", "CODE", "REGULATION", "USC", "CFR"]):
        return "Statutory"

    # Legal Concepts
    if any(term in entity_type_upper for term in ["DOCTRINE", "STANDARD", "TEST", "CONCEPT", "CAUSE"]):
        return "Legal Concepts"

    return "Miscellaneous"


def load_entity_patterns(
    pattern_loader,
    entity_type_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    min_confidence: float = 0.0
) -> List[EntityPatternInfo]:
    """
    Load entity patterns from PatternLoader.

    Args:
        pattern_loader: The PatternLoader instance
        entity_type_filter: Optional filter for specific entity type
        category_filter: Optional filter for category
        min_confidence: Minimum confidence score threshold

    Returns:
        List of EntityPatternInfo objects
    """
    entity_patterns = []

    if not pattern_loader:
        return entity_patterns

    try:
        # Get all entity types from the loader
        all_entity_types = pattern_loader.get_entity_types()

        for entity_type in all_entity_types:
            # Apply entity type filter if specified
            if entity_type_filter and entity_type != entity_type_filter:
                continue

            # Determine category
            category = categorize_entity_type(entity_type)

            # Apply category filter if specified
            if category_filter and category_filter.lower() not in category.lower():
                continue

            # Get patterns for this entity type
            patterns = pattern_loader.get_patterns_by_entity_type(entity_type)

            # Track pattern info
            pattern_list = []
            confidence_scores = []
            sources = defaultdict(int)
            jurisdictions = set()
            pattern_names = set()

            for pattern in patterns:
                # Skip duplicate patterns
                pattern_str = pattern.pattern
                if pattern_str in pattern_names:
                    continue

                pattern_names.add(pattern_str)

                # Filter by confidence
                if pattern.confidence < min_confidence:
                    continue

                confidence_scores.append(pattern.confidence)

                # Extract source from metadata
                source = "unknown"
                file_path = None
                if hasattr(pattern, 'metadata') and pattern.metadata:
                    if hasattr(pattern.metadata, 'file_path') and pattern.metadata.file_path:
                        file_path = str(pattern.metadata.file_path)
                        path_obj = Path(pattern.metadata.file_path)
                        if path_obj.parent.name in ["federal", "states", "legal", "client", "comprehensive"]:
                            source = path_obj.parent.name
                        elif path_obj.parent.parent.name in ["federal", "states", "legal", "client", "comprehensive"]:
                            source = path_obj.parent.parent.name

                    # Extract jurisdiction
                    if hasattr(pattern.metadata, 'jurisdiction') and pattern.metadata.jurisdiction:
                        jurisdictions.add(pattern.metadata.jurisdiction)

                sources[source] += 1

                # Add pattern details
                pattern_info = {
                    "name": pattern.name,
                    "pattern": pattern_str,
                    "confidence": pattern.confidence,
                    "source": source,
                    "file_path": file_path,
                    "examples": pattern.examples if hasattr(pattern, 'examples') else []
                }

                pattern_list.append(pattern_info)

            # Skip if no patterns match filters
            if not pattern_list:
                continue

            # Get all examples (including aggregated ones)
            all_examples = set()
            try:
                aggregated_examples = pattern_loader.get_all_aggregated_examples()
                if entity_type in aggregated_examples:
                    all_examples.update(aggregated_examples[entity_type])
            except Exception as e:
                logger.warning(f"Could not load aggregated examples: {e}")

            # Add examples from patterns
            for p in pattern_list:
                if p.get("examples"):
                    all_examples.update(p["examples"])

            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

            entity_patterns.append(EntityPatternInfo(
                entity_type=entity_type,
                category=category,
                total_patterns=len(pattern_list),
                total_examples=len(all_examples),
                average_confidence=round(avg_confidence, 3),
                pattern_sources=dict(sources),
                patterns=pattern_list,
                examples=list(all_examples),
                jurisdictions=list(jurisdictions)
            ))

    except Exception as e:
        logger.error(f"Error loading entity patterns: {e}", exc_info=True)

    return entity_patterns


def load_relationship_patterns(
    relationship_type_filter: Optional[str] = None,
    source_entity_filter: Optional[str] = None,
    target_entity_filter: Optional[str] = None
) -> List[RelationshipPatternInfo]:
    """
    Load relationship patterns from YAML files.

    Args:
        relationship_type_filter: Optional filter for specific relationship type
        source_entity_filter: Optional filter for source entity
        target_entity_filter: Optional filter for target entity

    Returns:
        List of RelationshipPatternInfo objects
    """
    relationship_patterns = []

    # Define relationship patterns directory
    patterns_dir = Path("/srv/luris/be/entity-extraction-service/src/patterns/relationships")

    if not patterns_dir.exists():
        logger.warning(f"Relationship patterns directory not found: {patterns_dir}")
        return relationship_patterns

    try:
        # Load all YAML files in relationships directory
        for yaml_file in patterns_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                if not data or 'patterns' not in data:
                    continue

                jurisdiction = data.get('jurisdiction')

                for pattern in data['patterns']:
                    relationship_type = pattern.get('relationship_type')
                    source_entity = pattern.get('source_entity')
                    target_entity = pattern.get('target_entity')

                    # Apply filters
                    if relationship_type_filter and relationship_type != relationship_type_filter:
                        continue

                    if source_entity_filter and source_entity != source_entity_filter:
                        continue

                    if target_entity_filter and target_entity != target_entity_filter:
                        continue

                    relationship_patterns.append(RelationshipPatternInfo(
                        relationship_type=relationship_type,
                        description=pattern.get('description', ''),
                        source_entity=source_entity,
                        target_entity=target_entity,
                        jurisdiction=jurisdiction,
                        indicators=pattern.get('indicators', []),
                        examples=pattern.get('examples', []),
                        pattern_file=yaml_file.name
                    ))

            except Exception as e:
                logger.warning(f"Error loading relationship pattern file {yaml_file}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error loading relationship patterns: {e}", exc_info=True)

    return relationship_patterns


@router.get(
    "/patterns",
    response_model=UnifiedPatternResponse,
    summary="Get Unified Patterns (Entities and Relationships)",
    description="""
    **Unified Pattern API - Access All Pattern Types**

    This endpoint provides a single, unified interface to access both entity patterns
    and relationship patterns from the Entity Extraction Service pattern library.

    ### Pattern Types
    - **entities**: Entity extraction patterns (courts, judges, citations, etc.)
    - **relationships**: Relationship patterns (cites, represents, sues, etc.)
    - **all**: Both entity and relationship patterns

    ### Query Parameters

    **Pattern Type Selection:**
    - `type`: Choose "entities", "relationships", or "all" (default: "all")

    **Entity Filters:**
    - `entity_type`: Filter by specific entity type (e.g., COURT, JUDGE)
    - `category`: Filter by category (e.g., "Courts and Judicial")
    - `min_confidence`: Minimum confidence score (0.0-1.0)

    **Relationship Filters:**
    - `relationship_type`: Filter by relationship type (e.g., CITES, REPRESENTS)
    - `source_entity`: Filter by source entity type
    - `target_entity`: Filter by target entity type

    **Content Control:**
    - `include_patterns`: Include full pattern details (default: true)
    - `include_examples`: Include pattern examples (default: true)
    - `include_descriptions`: Include detailed descriptions (default: true)
    - `format`: Response format - "summary", "detailed", "minimal" (default: "detailed")

    ### Response Structure
    - **type**: Type of patterns returned (entities/relationships/all)
    - **total_count**: Total number of patterns
    - **entities**: Entity pattern information (if requested)
    - **relationships**: Relationship pattern information (if requested)
    - **metadata**: Query metadata, cache status, and timing information

    ### Examples

    Get all entity patterns for COURT entity type:
    ```
    GET /api/v1/patterns?type=entities&entity_type=COURT
    ```

    Get all relationship patterns where source is CASE_CITATION:
    ```
    GET /api/v1/patterns?type=relationships&source_entity=CASE_CITATION
    ```

    Get everything (entities and relationships):
    ```
    GET /api/v1/patterns?type=all&format=detailed
    ```

    Get summary without examples:
    ```
    GET /api/v1/patterns?format=summary&include_examples=false
    ```
    """,
    responses={
        200: {
            "description": "Patterns retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "type": "all",
                        "total_count": 125,
                        "entities": [
                            {
                                "entity_type": "COURT",
                                "category": "Courts and Judicial",
                                "total_patterns": 47,
                                "total_examples": 125,
                                "average_confidence": 0.92,
                                "pattern_sources": {
                                    "federal": 12,
                                    "states": 30,
                                    "legal": 5
                                },
                                "jurisdictions": ["federal", "california", "new_york"]
                            }
                        ],
                        "relationships": [
                            {
                                "relationship_type": "CITES",
                                "description": "Case citing another case",
                                "source_entity": "CASE_CITATION",
                                "target_entity": "CASE_CITATION",
                                "jurisdiction": "federal",
                                "indicators": ["citing", "cited in", "as noted in"],
                                "examples": ["Smith v. Jones, citing Brown v. Board"]
                            }
                        ],
                        "metadata": {
                            "cache_hit": False,
                            "query_time_ms": 42.5,
                            "pattern_sources": ["federal", "states", "legal", "relationships"],
                            "filters_applied": {
                                "type": "all",
                                "min_confidence": 0.0
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_unified_patterns(
    request: Request,
    type: Optional[str] = Query("all", enum=["entities", "relationships", "all"], description="Type of patterns to retrieve"),
    entity_type: Optional[str] = Query(None, description="Filter by specific entity type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    source_entity: Optional[str] = Query(None, description="Filter by source entity type"),
    target_entity: Optional[str] = Query(None, description="Filter by target entity type"),
    include_patterns: bool = Query(True, description="Include full pattern details"),
    include_examples: bool = Query(True, description="Include pattern examples"),
    include_descriptions: bool = Query(True, description="Include detailed descriptions"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score for entity patterns"),
    format: str = Query("detailed", enum=["summary", "detailed", "minimal"], description="Response format level")
):
    """Get unified patterns for entities and/or relationships."""
    start_time = time.time()

    try:
        # Adjust includes based on format
        if format == "minimal":
            include_patterns = False
            include_examples = False
            include_descriptions = False
        elif format == "summary":
            include_patterns = False
            include_examples = True
            include_descriptions = True
        # detailed format uses the specified includes

        # Initialize response data
        entity_patterns = None
        relationship_patterns = None
        pattern_loader = None  # Initialize pattern_loader to avoid UnboundLocalError

        # Load entity patterns if requested
        if type in ["entities", "all"]:
            pattern_loader = getattr(request.app.state, "pattern_loader", None)

            if not pattern_loader:
                logger.warning("Pattern loader not available for entity patterns")
                if type == "entities":
                    raise HTTPException(
                        status_code=503,
                        detail="Pattern loader not available for entity patterns"
                    )
            else:
                entity_patterns = load_entity_patterns(
                    pattern_loader=pattern_loader,
                    entity_type_filter=entity_type,
                    category_filter=category,
                    min_confidence=min_confidence
                )

                # Remove pattern/example details if not requested
                if not include_patterns or format == "minimal":
                    for pattern in entity_patterns:
                        pattern.patterns = None

                if not include_examples or format == "minimal":
                    for pattern in entity_patterns:
                        pattern.examples = None

        # Load relationship patterns if requested
        if type in ["relationships", "all"]:
            relationship_patterns = load_relationship_patterns(
                relationship_type_filter=relationship_type,
                source_entity_filter=source_entity,
                target_entity_filter=target_entity
            )

            # Remove details if not requested
            if not include_examples or format == "minimal":
                for pattern in relationship_patterns:
                    pattern.examples = None

            if not include_descriptions or format == "minimal":
                for pattern in relationship_patterns:
                    pattern.indicators = None

        # Calculate total count
        total_count = 0
        if entity_patterns:
            total_count += sum(p.total_patterns for p in entity_patterns)
        if relationship_patterns:
            total_count += len(relationship_patterns)

        # Build metadata
        query_time_ms = round((time.time() - start_time) * 1000, 2)

        pattern_sources = set()
        if entity_patterns:
            for pattern in entity_patterns:
                pattern_sources.update(pattern.pattern_sources.keys())
        if relationship_patterns:
            pattern_sources.add("relationships")

        # Get cache statistics if cached pattern loader is available
        cache_stats = None
        if pattern_loader and hasattr(pattern_loader, 'get_cache_stats'):
            try:
                cache_stats = pattern_loader.get_cache_stats()
            except Exception as e:
                logger.debug(f"Could not retrieve cache stats: {e}")

        metadata = {
            "cache_stats": cache_stats,
            "query_time_ms": query_time_ms,
            "pattern_sources": sorted(list(pattern_sources)),
            "filters_applied": {
                "type": type,
                "entity_type": entity_type,
                "category": category,
                "relationship_type": relationship_type,
                "source_entity": source_entity,
                "target_entity": target_entity,
                "min_confidence": min_confidence if min_confidence > 0 else None,
                "format": format
            },
            "counts": {
                "entity_types": len(entity_patterns) if entity_patterns else 0,
                "relationships": len(relationship_patterns) if relationship_patterns else 0,
                "total_patterns": total_count
            }
        }

        # Log the request
        log_client = getattr(request.app.state, "log_client", None)
        if log_client:
            await log_client.log(
                level="INFO",
                message="Unified patterns requested",
                service="entity-extraction-service",
                request_id=getattr(request.state, "request_id", ""),
                metadata={
                    "type": type,
                    "entity_type": entity_type,
                    "relationship_type": relationship_type,
                    "total_count": total_count,
                    "query_time_ms": query_time_ms
                }
            )

        return UnifiedPatternResponse(
            type=type,
            total_count=total_count,
            entities=entity_patterns if type in ["entities", "all"] else None,
            relationships=relationship_patterns if type in ["relationships", "all"] else None,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get unified patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve unified patterns: {str(e)}"
        )


@router.get(
    "/patterns/cache/stats",
    summary="Get Pattern Cache Statistics",
    description="""
    **Pattern Cache Performance Metrics**

    Get detailed performance statistics for the pattern caching system.

    ### Cache Metrics
    - **hits**: Number of cache hits (data found in cache)
    - **misses**: Number of cache misses (data loaded from disk)
    - **hit_rate**: Percentage of requests served from cache
    - **expirations**: Number of expired cache entries removed
    - **evictions**: Number of entries removed due to cache size limits
    - **cache_size**: Current number of entries in cache
    - **utilization**: Percentage of cache capacity used

    ### Method-Specific Metrics
    Cache statistics broken down by PatternLoader method:
    - `get_entity_types`: Entity type listing performance
    - `get_patterns_by_entity_type`: Pattern retrieval performance
    - `get_all_aggregated_examples`: Example aggregation performance

    ### Use Cases
    - Monitor cache effectiveness and hit rates
    - Identify caching bottlenecks
    - Tune cache size and TTL parameters
    - Debug performance issues
    """,
    responses={
        200: {
            "description": "Cache statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "cache_enabled": True,
                        "overall": {
                            "hits": 142,
                            "misses": 18,
                            "hit_rate": 0.8875,
                            "total_requests": 160,
                            "expirations": 3,
                            "evictions": 0
                        },
                        "cache_size": 24,
                        "max_size": 128,
                        "utilization": 0.1875,
                        "ttl_seconds": 3600,
                        "method_metrics": {
                            "get_entity_types": {
                                "hits": 45,
                                "misses": 1,
                                "hit_rate": 0.9783,
                                "total_requests": 46
                            },
                            "get_patterns_by_entity_type": {
                                "hits": 89,
                                "misses": 15,
                                "hit_rate": 0.8558,
                                "total_requests": 104
                            }
                        },
                        "timestamp": 1704736800.123
                    }
                }
            }
        }
    }
)
async def get_cache_statistics(request: Request):
    """Get detailed pattern cache statistics."""
    try:
        pattern_loader = getattr(request.app.state, "pattern_loader", None)

        if not pattern_loader:
            return {
                "cache_enabled": False,
                "message": "Pattern loader not available",
                "timestamp": time.time()
            }

        # Check if cache is available
        if not hasattr(pattern_loader, 'get_cache_stats'):
            return {
                "cache_enabled": False,
                "message": "Caching not enabled for pattern loader",
                "timestamp": time.time()
            }

        # Get cache statistics
        cache_stats = pattern_loader.get_cache_stats()
        cache_stats["cache_enabled"] = True
        cache_stats["timestamp"] = time.time()

        return cache_stats

    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cache statistics: {str(e)}"
        )


@router.post(
    "/patterns/cache/clear",
    summary="Clear Pattern Cache",
    description="""
    **Clear Pattern Cache**

    Clear all entries from the pattern cache. This forces fresh loading
    from disk on the next pattern request.

    ### Use Cases
    - Force pattern reload after YAML file updates
    - Clear cache during development/testing
    - Reset cache after pattern modifications
    - Debug caching issues

    ### Effects
    - All cached patterns are removed
    - Next pattern request will be a cache miss
    - Cache metrics are preserved
    """,
    responses={
        200: {
            "description": "Cache cleared successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Pattern cache cleared successfully",
                        "previous_size": 42,
                        "timestamp": 1704736800.123
                    }
                }
            }
        }
    }
)
async def clear_cache(request: Request):
    """Clear the pattern cache."""
    try:
        pattern_loader = getattr(request.app.state, "pattern_loader", None)

        if not pattern_loader:
            raise HTTPException(
                status_code=503,
                detail="Pattern loader not available"
            )

        # Check if cache is available
        if not hasattr(pattern_loader, 'clear_cache'):
            raise HTTPException(
                status_code=501,
                detail="Cache clearing not supported for this pattern loader"
            )

        # Get size before clearing
        previous_stats = pattern_loader.get_cache_stats() if hasattr(pattern_loader, 'get_cache_stats') else {}
        previous_size = previous_stats.get('cache_size', 0)

        # Clear the cache
        pattern_loader.clear_cache()

        logger.info(f"Pattern cache cleared: {previous_size} entries removed")

        return {
            "success": True,
            "message": "Pattern cache cleared successfully",
            "previous_size": previous_size,
            "timestamp": time.time()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )
