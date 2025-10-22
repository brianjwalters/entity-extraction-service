"""
Relationship Pattern Routes for Entity Extraction Service

Provides comprehensive API endpoints for exploring and querying the 46 relationship types
supported by the Entity Extraction Service, organized across 6 relationship categories.
"""

import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter()


class RelationshipIndicator(BaseModel):
    """Model for relationship indicators."""
    text: str = Field(..., description="Indicator text or phrase")
    confidence: float = Field(default=0.8, description="Confidence score for this indicator")


class RelationshipPattern(BaseModel):
    """Complete relationship pattern information."""
    relationship_type: str = Field(..., description="Type of relationship (e.g., REPRESENTS, CITES)")
    description: str = Field(..., description="Human-readable description of the relationship")
    source_entity: str = Field(..., description="Source entity type")
    target_entity: str = Field(..., description="Target entity type")
    indicators: List[str] = Field(..., description="Textual indicators for this relationship")
    examples: List[str] = Field(..., description="Example sentences showing this relationship")
    category: Optional[str] = Field(None, description="Relationship category")
    confidence: float = Field(default=0.8, description="Base confidence for this pattern")
    bidirectional: bool = Field(default=False, description="Whether relationship can work both ways")


class RelationshipListResponse(BaseModel):
    """Response for listing relationship types."""
    total_relationships: int = Field(..., description="Total number of relationship types")
    relationships: List[RelationshipPattern] = Field(..., description="List of relationship patterns")
    categories: List[str] = Field(..., description="Available relationship categories")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filters that were applied")


class RelationshipDetailResponse(BaseModel):
    """Detailed response for a specific relationship type."""
    relationship_type: str
    description: str
    source_entity: str
    target_entity: str
    indicators: List[str]
    examples: List[str]
    category: str
    confidence: float
    bidirectional: bool
    usage_statistics: Optional[Dict[str, Any]] = Field(
        None,
        description="Usage statistics for this relationship type"
    )
    related_relationships: Optional[List[str]] = Field(
        None,
        description="Related relationship types"
    )


class RelationshipCategoryInfo(BaseModel):
    """Information about a relationship category."""
    category: str = Field(..., description="Category name")
    description: str = Field(..., description="Category description")
    relationship_count: int = Field(..., description="Number of relationships in this category")
    relationship_types: List[str] = Field(..., description="List of relationship types in this category")
    example_relationships: List[str] = Field(..., description="Example relationship types")


class RelationshipCategoriesResponse(BaseModel):
    """Response for relationship categories endpoint."""
    total_categories: int = Field(..., description="Total number of categories")
    categories: List[RelationshipCategoryInfo] = Field(..., description="List of categories")
    total_relationships: int = Field(..., description="Total relationships across all categories")


class RelationshipStatistics(BaseModel):
    """Comprehensive relationship pattern statistics."""
    total_relationships: int
    total_categories: int
    total_indicators: int
    relationships_by_category: Dict[str, int]
    most_common_source_entities: List[Dict[str, Any]]
    most_common_target_entities: List[Dict[str, Any]]
    bidirectional_relationships: int
    average_indicators_per_relationship: float
    coverage_by_entity_type: Dict[str, int]


class RelationshipExtractionRequest(BaseModel):
    """Request model for dedicated relationship extraction."""
    document_id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Document content to extract relationships from")
    entities: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Pre-extracted entities to use for relationship extraction"
    )
    extract_entities_if_missing: bool = Field(
        default=True,
        description="Extract entities first if not provided"
    )
    relationship_types: Optional[List[str]] = Field(
        None,
        description="Specific relationship types to extract"
    )
    confidence_threshold: float = Field(
        default=0.75,
        description="Minimum confidence threshold for relationships"
    )
    max_relationships: Optional[int] = Field(
        None,
        description="Maximum number of relationships to return"
    )
    context_window: int = Field(
        default=250,
        description="Character window for relationship context"
    )


class ExtractedRelationship(BaseModel):
    """Model for an extracted relationship."""
    relationship_id: str
    relationship_type: str
    source_entity: Dict[str, Any]
    target_entity: Dict[str, Any]
    confidence: float
    evidence_text: str
    position: Dict[str, int]
    indicators_found: List[str]


class RelationshipExtractionResponse(BaseModel):
    """Response for relationship extraction."""
    document_id: str
    extraction_id: str
    processing_time_ms: float
    total_relationships: int
    relationships: List[ExtractedRelationship]
    entities_used: int
    statistics: Dict[str, Any]


@router.get("/relationships", response_model=RelationshipListResponse)
async def list_relationships(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category"),
    source_entity: Optional[str] = Query(None, description="Filter by source entity type"),
    target_entity: Optional[str] = Query(None, description="Filter by target entity type"),
    include_examples: bool = Query(True, description="Include example sentences"),
    limit: Optional[int] = Query(None, description="Maximum relationships to return")
):
    """
    List all 46 relationship types with comprehensive filtering.

    This endpoint provides access to the complete relationship pattern library,
    supporting filtering by category, source entity, target entity, and more.

    **Relationship Categories:**
    - party_litigation: Relationships between parties, attorneys, and courts
    - legal_precedent: Citation and precedent relationships
    - statutory_regulatory: Statute and regulation relationships
    - temporal_procedural: Temporal and procedural relationships
    - jurisdictional_venue: Jurisdiction and venue relationships
    - contractual_financial: Contract and financial relationships

    **Query Parameters:**
    - category: Filter by relationship category
    - source_entity: Filter by source entity type (e.g., ATTORNEY, JUDGE)
    - target_entity: Filter by target entity type (e.g., PARTY, COURT)
    - include_examples: Whether to include example sentences
    - limit: Maximum number of relationships to return

    Returns comprehensive relationship information including indicators, examples,
    and metadata for each relationship type.
    """
    try:
        # Get pattern loader from app state
        pattern_loader = getattr(request.app.state, "pattern_loader", None)
        if not pattern_loader:
            raise HTTPException(
                status_code=503,
                detail="Pattern loader not available"
            )

        # Get all relationship patterns organized by category
        relationship_patterns = pattern_loader.get_relationship_patterns()

        if not relationship_patterns:
            logger.warning("No relationship patterns loaded")
            return RelationshipListResponse(
                total_relationships=0,
                relationships=[],
                categories=[],
                filters_applied={}
            )

        # Collect all relationships across categories
        all_relationships = []
        all_categories = set()

        for category_name, patterns in relationship_patterns.items():
            all_categories.add(category_name)

            # Validate patterns data structure
            if patterns is None:
                logger.warning(f"Category {category_name} has None patterns, skipping")
                continue

            if not isinstance(patterns, list):
                logger.error(f"Category {category_name} patterns is not a list: {type(patterns)}")
                continue

            for pattern_data in patterns:
                # Validate pattern data type
                if not isinstance(pattern_data, dict):
                    logger.warning(f"Invalid pattern data type in {category_name}: {type(pattern_data)}, skipping")
                    continue
                # Apply category filter
                if category and category_name != category:
                    continue

                # Apply source entity filter
                if source_entity and pattern_data.get("source_entity") != source_entity:
                    continue

                # Apply target entity filter
                if target_entity and pattern_data.get("target_entity") != target_entity:
                    continue

                # Create relationship pattern object with validation error handling
                try:
                    relationship = RelationshipPattern(
                        relationship_type=pattern_data.get("relationship_type", "UNKNOWN"),
                        description=pattern_data.get("description", ""),
                        source_entity=pattern_data.get("source_entity", "UNKNOWN"),
                        target_entity=pattern_data.get("target_entity", "UNKNOWN"),
                        indicators=pattern_data.get("indicators", []),
                        examples=pattern_data.get("examples", []) if include_examples else [],
                        category=category_name,
                        confidence=pattern_data.get("confidence", 0.8),
                        bidirectional=pattern_data.get("bidirectional", False)
                    )
                    all_relationships.append(relationship)
                except ValidationError as e:
                    logger.error(f"Pattern validation failed for {pattern_data.get('relationship_type', 'UNKNOWN')} in {category_name}: {e}")
                    continue  # Skip invalid pattern, don't fail entire request

        # Apply limit if specified
        if limit:
            all_relationships = all_relationships[:limit]

        filters_applied = {}
        if category:
            filters_applied["category"] = category
        if source_entity:
            filters_applied["source_entity"] = source_entity
        if target_entity:
            filters_applied["target_entity"] = target_entity

        return RelationshipListResponse(
            total_relationships=len(all_relationships),
            relationships=all_relationships,
            categories=sorted(list(all_categories)),
            filters_applied=filters_applied
        )

    except HTTPException:
        raise
    except (TypeError, KeyError, AttributeError) as e:
        logger.error(f"Data structure error in relationships endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Invalid pattern data structure. Pattern files may be corrupted."
        )
    except ValidationError as e:
        logger.error(f"Pattern validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Pattern schema validation failed. Check pattern file format."
        )
    except Exception as e:
        logger.error(f"Unexpected error listing relationships: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/relationships/{relationship_type}", response_model=RelationshipDetailResponse)
async def get_relationship_details(
    relationship_type: str,
    request: Request
):
    """
    Get detailed information about a specific relationship type.

    Provides comprehensive details including:
    - Full description and usage guidelines
    - Source and target entity types
    - All textual indicators
    - Example sentences
    - Usage statistics (if available)
    - Related relationship types

    **Path Parameters:**
    - relationship_type: The relationship type to get details for (e.g., REPRESENTS, CITES)

    **Example:**
    ```
    GET /api/v1/relationships/REPRESENTS
    ```

    Returns detailed information about the REPRESENTS relationship type,
    including all indicators, examples, and usage patterns.
    """
    try:
        # Get pattern loader from app state
        pattern_loader = getattr(request.app.state, "pattern_loader", None)
        if not pattern_loader:
            raise HTTPException(
                status_code=503,
                detail="Pattern loader not available"
            )

        # Get all relationship patterns
        relationship_patterns = pattern_loader.get_relationship_patterns()

        # Search for the specific relationship type
        found_relationship = None
        found_category = None

        for category_name, patterns in relationship_patterns.items():
            for pattern_data in patterns:
                if pattern_data.get("relationship_type", "").upper() == relationship_type.upper():
                    found_relationship = pattern_data
                    found_category = category_name
                    break
            if found_relationship:
                break

        if not found_relationship:
            raise HTTPException(
                status_code=404,
                detail=f"Relationship type '{relationship_type}' not found"
            )

        # Find related relationships (same source or target entity)
        related_relationships = []
        source_entity = found_relationship.get("source_entity")
        target_entity = found_relationship.get("target_entity")

        for category_name, patterns in relationship_patterns.items():
            for pattern_data in patterns:
                rel_type = pattern_data.get("relationship_type", "")
                if rel_type.upper() != relationship_type.upper():
                    if (pattern_data.get("source_entity") == source_entity or
                        pattern_data.get("target_entity") == target_entity or
                        pattern_data.get("source_entity") == target_entity or
                        pattern_data.get("target_entity") == source_entity):
                        related_relationships.append(rel_type)

        # Usage statistics (placeholder - would be populated from actual usage data)
        usage_stats = {
            "total_extractions": 0,
            "average_confidence": found_relationship.get("confidence", 0.8),
            "most_common_contexts": [],
            "success_rate": 0.0
        }

        return RelationshipDetailResponse(
            relationship_type=found_relationship.get("relationship_type", "UNKNOWN"),
            description=found_relationship.get("description", ""),
            source_entity=found_relationship.get("source_entity", "UNKNOWN"),
            target_entity=found_relationship.get("target_entity", "UNKNOWN"),
            indicators=found_relationship.get("indicators", []),
            examples=found_relationship.get("examples", []),
            category=found_category,
            confidence=found_relationship.get("confidence", 0.8),
            bidirectional=found_relationship.get("bidirectional", False),
            usage_statistics=usage_stats,
            related_relationships=related_relationships[:10] if related_relationships else []
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relationship details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get relationship details: {str(e)}"
        )


@router.get("/relationships/categories", response_model=RelationshipCategoriesResponse)
async def get_relationship_categories(
    request: Request
):
    """
    Get summary of all 6 relationship categories.

    Provides an overview of relationship categories with:
    - Category name and description
    - Count of relationship types in each category
    - List of all relationship types per category
    - Example relationships for each category

    **Relationship Categories:**
    1. **party_litigation**: Relationships between parties, attorneys, and courts
    2. **legal_precedent**: Citation and precedent relationships
    3. **statutory_regulatory**: Statute and regulation relationships
    4. **temporal_procedural**: Temporal and procedural relationships
    5. **jurisdictional_venue**: Jurisdiction and venue relationships
    6. **contractual_financial**: Contract and financial relationships

    **Example:**
    ```
    GET /api/v1/relationships/categories
    ```

    Returns comprehensive information about all relationship categories,
    organized for easy navigation and discovery.
    """
    try:
        # Get pattern loader from app state
        pattern_loader = getattr(request.app.state, "pattern_loader", None)
        if not pattern_loader:
            raise HTTPException(
                status_code=503,
                detail="Pattern loader not available"
            )

        # Get relationship categories from pattern loader
        relationship_categories = pattern_loader.get_relationship_categories()

        if not relationship_categories:
            logger.warning("No relationship categories loaded")
            return RelationshipCategoriesResponse(
                total_categories=0,
                categories=[],
                total_relationships=0
            )

        # Category descriptions
        category_descriptions = {
            "party_litigation": "Relationships between parties, attorneys, courts, and litigation participants",
            "legal_precedent": "Citation relationships, precedents, and case law references",
            "statutory_regulatory": "Relationships between statutes, regulations, and legal codes",
            "temporal_procedural": "Temporal sequences, procedural steps, and timeline relationships",
            "jurisdictional_venue": "Jurisdiction, venue, and court hierarchy relationships",
            "contractual_financial": "Contract relationships, financial obligations, and agreements"
        }

        categories_info = []
        total_relationships = 0

        for category_name, relationship_types in relationship_categories.items():
            category_info = RelationshipCategoryInfo(
                category=category_name,
                description=category_descriptions.get(category_name, f"Relationships in {category_name} category"),
                relationship_count=len(relationship_types),
                relationship_types=relationship_types,
                example_relationships=relationship_types[:3] if len(relationship_types) > 3 else relationship_types
            )
            categories_info.append(category_info)
            total_relationships += len(relationship_types)

        return RelationshipCategoriesResponse(
            total_categories=len(categories_info),
            categories=categories_info,
            total_relationships=total_relationships
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relationship categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get relationship categories: {str(e)}"
        )


@router.get("/relationships/statistics", response_model=RelationshipStatistics)
async def get_relationship_statistics(
    request: Request
):
    """
    Get comprehensive relationship pattern statistics.

    Provides detailed analytics about the relationship pattern library:
    - Total relationship types and categories
    - Total indicators across all relationships
    - Distribution of relationships by category
    - Most common source and target entity types
    - Bidirectional relationship count
    - Average indicators per relationship
    - Coverage analysis by entity type

    **Use Cases:**
    - Pattern library health monitoring
    - Coverage gap identification
    - Relationship type usage analysis
    - Entity type relationship mapping

    **Example:**
    ```
    GET /api/v1/relationships/statistics
    ```

    Returns comprehensive statistics for operational monitoring
    and pattern library optimization.
    """
    try:
        # Get pattern loader from app state
        pattern_loader = getattr(request.app.state, "pattern_loader", None)
        if not pattern_loader:
            raise HTTPException(
                status_code=503,
                detail="Pattern loader not available"
            )

        # Get all relationship patterns
        relationship_patterns = pattern_loader.get_relationship_patterns()
        relationship_categories = pattern_loader.get_relationship_categories()

        if not relationship_patterns:
            logger.warning("No relationship patterns loaded")
            return RelationshipStatistics(
                total_relationships=0,
                total_categories=0,
                total_indicators=0,
                relationships_by_category={},
                most_common_source_entities=[],
                most_common_target_entities=[],
                bidirectional_relationships=0,
                average_indicators_per_relationship=0.0,
                coverage_by_entity_type={}
            )

        # Calculate statistics
        total_indicators = 0
        source_entity_counts = defaultdict(int)
        target_entity_counts = defaultdict(int)
        bidirectional_count = 0
        indicator_counts = []
        entity_relationship_coverage = defaultdict(int)

        relationships_by_category = {}
        for category_name, rel_types in relationship_categories.items():
            relationships_by_category[category_name] = len(rel_types)

        for category_name, patterns in relationship_patterns.items():
            for pattern_data in patterns:
                # Count indicators
                indicators = pattern_data.get("indicators", [])
                total_indicators += len(indicators)
                indicator_counts.append(len(indicators))

                # Count source and target entities
                source_entity = pattern_data.get("source_entity", "UNKNOWN")
                target_entity = pattern_data.get("target_entity", "UNKNOWN")
                source_entity_counts[source_entity] += 1
                target_entity_counts[target_entity] += 1

                # Count bidirectional relationships
                if pattern_data.get("bidirectional", False):
                    bidirectional_count += 1

                # Track entity coverage
                entity_relationship_coverage[source_entity] += 1
                entity_relationship_coverage[target_entity] += 1

        # Calculate average indicators
        avg_indicators = sum(indicator_counts) / len(indicator_counts) if indicator_counts else 0.0

        # Get most common entities
        most_common_sources = [
            {"entity_type": entity, "count": count}
            for entity, count in sorted(source_entity_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        most_common_targets = [
            {"entity_type": entity, "count": count}
            for entity, count in sorted(target_entity_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return RelationshipStatistics(
            total_relationships=sum(len(patterns) for patterns in relationship_patterns.values()),
            total_categories=len(relationship_categories),
            total_indicators=total_indicators,
            relationships_by_category=relationships_by_category,
            most_common_source_entities=most_common_sources,
            most_common_target_entities=most_common_targets,
            bidirectional_relationships=bidirectional_count,
            average_indicators_per_relationship=round(avg_indicators, 2),
            coverage_by_entity_type=dict(entity_relationship_coverage)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relationship statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get relationship statistics: {str(e)}"
        )


@router.post("/extract/relationships", response_model=RelationshipExtractionResponse)
async def extract_relationships(
    request_body: RelationshipExtractionRequest,
    request: Request
):
    """
    Dedicated relationship extraction endpoint.

    Extracts relationships between entities in a document, either using:
    1. Pre-extracted entities (if provided)
    2. Automatic entity extraction (if entities not provided)

    **Key Features:**
    - Focused relationship extraction without full entity processing
    - Support for pre-extracted entities for efficiency
    - Configurable confidence thresholds
    - Filtering by specific relationship types
    - Context window configuration

    **Request Body:**
    ```json
    {
      "document_id": "doc_001",
      "content": "John Smith, Esq. representing Plaintiff in Smith v. Jones",
      "entities": [...],  // Optional pre-extracted entities
      "extract_entities_if_missing": true,
      "relationship_types": ["REPRESENTS", "SUES"],  // Optional filter
      "confidence_threshold": 0.75,
      "max_relationships": 50,
      "context_window": 250
    }
    ```

    **Returns:**
    Extracted relationships with full context, evidence text, and confidence scores.
    """
    try:
        import time
        import uuid
        from src.core.relationships.relationship_extractor import (
            RelationshipExtractor,
            ExtractionConfig,
            EntityMention
        )

        start_time = time.time()
        extraction_id = str(uuid.uuid4())

        # Get required services from app state
        pattern_loader = getattr(request.app.state, "pattern_loader", None)
        if not pattern_loader:
            raise HTTPException(
                status_code=503,
                detail="Pattern loader not available"
            )

        # Configure extraction (pattern-based only, no spaCy or ML)
        config = ExtractionConfig(
            use_patterns=True,
            use_dependency_parsing=False,  # No spaCy
            use_coreference=False,  # Keep simple for now
            use_proximity=True,
            use_ml_model=False,
            pattern_confidence_threshold=request_body.confidence_threshold,
            proximity_window=request_body.context_window,
            max_entity_distance=request_body.context_window * 2,
            overall_confidence_threshold=request_body.confidence_threshold,
            include_context=True,
            context_window=50,
            merge_duplicates=True
        )

        # Create extractor - Note: extractor will create LegalRelationshipPatterns by default
        # but we'll use proximity-based extraction which doesn't require patterns
        extractor = RelationshipExtractor(config)

        # Convert request entities to EntityMention objects
        entity_mentions = []
        entities = request_body.entities or []

        if not entities and request_body.extract_entities_if_missing:
            # Simple entity extraction using regex engine
            logger.info("Extracting entities for relationship extraction")

            # Get regex engine from app state if available
            regex_engine = getattr(request.app.state, "regex_engine", None)

            if regex_engine:
                # Extract entities from content using async method
                from src.core.regex_engine import ExtractionContext

                context = ExtractionContext(
                    document_id=request_body.document_id,
                    confidence_threshold=request_body.confidence_threshold
                )

                # RegexEngine returns Tuple[List[Entity], List[Citation]]
                extracted_entities, extracted_citations = await regex_engine.extract_entities(
                    text=request_body.content,
                    context=context
                )

                # Convert Entity objects to dictionary format
                entities = [
                    {
                        "entity_id": e.id,
                        "entity_type": e.entity_type.value,
                        "entity_text": e.text,
                        "start_position": e.position.start,
                        "end_position": e.position.end,
                        "confidence": e.confidence_score
                    }
                    for e in extracted_entities
                ]

                logger.info(f"Extracted {len(entities)} entities for relationship extraction")
            else:
                logger.warning("RegexEngine not available, skipping entity extraction")

        # Convert entities to EntityMention objects
        for entity in entities:
            entity_mention = EntityMention(
                entity_id=entity.get("entity_id", str(uuid.uuid4())),
                entity_type=entity.get("entity_type", "UNKNOWN"),
                entity_text=entity.get("entity_text", ""),
                start_position=entity.get("start_position", 0),
                end_position=entity.get("end_position", 0),
                confidence=entity.get("confidence", 0.7),
                canonical_name=entity.get("canonical_name"),
                metadata=entity.get("metadata", {})
            )
            entity_mentions.append(entity_mention)

        logger.info(f"Processing {len(entity_mentions)} entities for relationship extraction")

        # Extract relationships using the extractor
        result = extractor.extract_relationships(
            text=request_body.content,
            entities=entity_mentions,
            document_id=request_body.document_id
        )

        # Helper function to convert entity to dictionary format
        # Handles both EntityMention objects and Entity objects for compatibility
        def entity_to_dict(entity) -> Dict[str, Any]:
            """
            Convert entity object to dictionary format for API response.

            Supports both EntityMention and Entity objects for backward compatibility:
            - EntityMention: Has entity_id, entity_type, entity_text, start_position, end_position, confidence
            - Entity: Has id, entity_type (enum), text, position (object), confidence_score
            """
            return {
                "entity_id": getattr(entity, 'entity_id', getattr(entity, 'id', None)),
                "entity_type": (
                    entity.entity_type if isinstance(entity.entity_type, str)
                    else entity.entity_type.value
                ),
                "entity_text": getattr(entity, 'entity_text', getattr(entity, 'text', '')),
                "start_position": (
                    getattr(entity, 'start_position', None) or
                    getattr(getattr(entity, 'position', None), 'start', 0)
                ),
                "end_position": (
                    getattr(entity, 'end_position', None) or
                    getattr(getattr(entity, 'position', None), 'end', 0)
                ),
                "confidence": getattr(entity, 'confidence', getattr(entity, 'confidence_score', 0.0))
            }

        # Format relationships as API response
        extracted_relationships = []

        for rel in result.relationships:
            # Apply relationship type filter if specified
            if request_body.relationship_types:
                if rel.relationship_type.value.upper() not in [rt.upper() for rt in request_body.relationship_types]:
                    continue

            # Create API response object using helper function for entity conversion
            extracted_rel = ExtractedRelationship(
                relationship_id=rel.relationship_id,
                relationship_type=rel.relationship_type.value,
                source_entity=entity_to_dict(rel.source_entity),
                target_entity=entity_to_dict(rel.target_entity),
                confidence=rel.confidence,
                evidence_text=rel.context,
                position={
                    "start": rel.context_start,
                    "end": rel.context_end
                },
                indicators_found=rel.evidence
            )

            extracted_relationships.append(extracted_rel)

        # Apply max_relationships limit if specified
        if request_body.max_relationships:
            # Sort by confidence descending
            extracted_relationships.sort(key=lambda r: r.confidence, reverse=True)
            extracted_relationships = extracted_relationships[:request_body.max_relationships]

        processing_time = (time.time() - start_time) * 1000

        # Build response statistics
        response_statistics = {
            "extraction_mode": "relationship_focused",
            "extraction_methods": dict(result.statistics.get("extraction_methods", {})),
            "relationship_types": dict(result.statistics.get("relationship_types", {})),
            "confidence_distribution": result.statistics.get("confidence_distribution", {}),
            "confidence_threshold": request_body.confidence_threshold,
            "relationship_types_requested": request_body.relationship_types,
            "context_window": request_body.context_window,
            "entities_extracted": len(entity_mentions),
            "patterns_used": config.use_patterns,
            "proximity_used": config.use_proximity
        }

        return RelationshipExtractionResponse(
            document_id=request_body.document_id,
            extraction_id=extraction_id,
            processing_time_ms=round(processing_time, 2),
            total_relationships=len(extracted_relationships),
            relationships=extracted_relationships,
            entities_used=len(entity_mentions),
            statistics=response_statistics
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting relationships: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract relationships: {str(e)}"
        )
