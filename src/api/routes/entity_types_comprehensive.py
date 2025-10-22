"""
Comprehensive Pattern Merging Extension for Entity Types Routes.

This module provides the comprehensive pattern merging functionality
that aggregates patterns from all sources for maximum coverage.
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import Query, Request, HTTPException, Response
from pydantic import BaseModel, Field
from pathlib import Path
from collections import defaultdict
import yaml

# CLAUDE.md Compliant: Absolute imports
from src.api.routes.entity_types import router, categorize_entity_type, categorize_citation_type
from src.models.entities import EntityType, CitationType

logger = logging.getLogger(__name__)


class ComprehensivePatternInfo(BaseModel):
    """Comprehensive pattern information for an entity type."""
    entity_type: str = Field(..., description="Entity type name")
    category: str = Field(..., description="Entity category")
    total_patterns: int = Field(..., description="Total number of unique patterns")
    total_examples: int = Field(..., description="Total number of examples")
    average_confidence: float = Field(..., description="Average confidence score across all patterns")
    pattern_sources: Dict[str, int] = Field(..., description="Number of patterns from each source")
    patterns: List[Dict[str, Any]] = Field(..., description="All patterns with metadata")
    examples: List[str] = Field(..., description="All unique examples")
    jurisdictions: List[str] = Field(default_factory=list, description="Jurisdictions covered")
    bluebook_compliant: bool = Field(False, description="Whether patterns are Bluebook compliant")
    
    
class ComprehensivePatternResponse(BaseModel):
    """Response for comprehensive pattern endpoint."""
    entity_types: List[ComprehensivePatternInfo] = Field(..., description="Pattern info for each entity type")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


def load_comprehensive_patterns(pattern_loader, entity_type_filter: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Load and merge patterns from all sources comprehensively.
    
    Args:
        pattern_loader: The PatternLoader instance
        entity_type_filter: Optional filter for specific entity type
        
    Returns:
        Dict mapping entity types to comprehensive pattern information
    """
    comprehensive_patterns = defaultdict(lambda: {
        "patterns": [],
        "examples": set(),
        "sources": defaultdict(int),
        "jurisdictions": set(),
        "confidence_scores": [],
        "pattern_names": set()
    })
    
    # Define all pattern directories to scan
    pattern_dirs = ["federal", "states", "legal", "client", "comprehensive"]
    base_path = Path("/srv/luris/be/entity-extraction-service/src/patterns")
    
    # Load patterns from PatternLoader (which handles all YAML files)
    if pattern_loader:
        try:
            # Get all entity types from the loader
            all_entity_types = pattern_loader.get_entity_types()
            
            for entity_type in all_entity_types:
                # Apply filter if specified
                if entity_type_filter and entity_type != entity_type_filter:
                    continue
                    
                # Get patterns for this entity type
                patterns = pattern_loader.get_patterns_by_entity_type(entity_type)
                
                for pattern in patterns:
                    # Skip duplicate patterns based on regex string
                    pattern_str = pattern.pattern
                    if pattern_str in comprehensive_patterns[entity_type]["pattern_names"]:
                        continue
                        
                    comprehensive_patterns[entity_type]["pattern_names"].add(pattern_str)
                    
                    # Extract source and file path from metadata if available
                    source = "unknown"
                    full_file_path = None
                    if hasattr(pattern, 'metadata') and pattern.metadata:
                        if hasattr(pattern.metadata, 'file_path') and pattern.metadata.file_path:
                            # Store the full file path
                            full_file_path = str(pattern.metadata.file_path)
                            # Extract directory name from file path
                            file_path = Path(pattern.metadata.file_path)
                            if file_path.parent.name in pattern_dirs:
                                source = file_path.parent.name
                            elif file_path.parent.parent.name in pattern_dirs:
                                source = file_path.parent.parent.name
                                
                    comprehensive_patterns[entity_type]["sources"][source] += 1
                    
                    # Add pattern info with file path
                    pattern_info = {
                        "name": pattern.name,
                        "pattern": pattern_str,
                        "confidence": pattern.confidence,
                        "source": source,
                        "file_path": full_file_path,
                        "examples": pattern.examples if hasattr(pattern, 'examples') else []
                    }
                    
                    # Add jurisdiction info if available
                    if hasattr(pattern, 'metadata') and pattern.metadata:
                        if hasattr(pattern.metadata, 'jurisdiction') and pattern.metadata.jurisdiction:
                            comprehensive_patterns[entity_type]["jurisdictions"].add(pattern.metadata.jurisdiction)
                            pattern_info["jurisdiction"] = pattern.metadata.jurisdiction
                    
                    comprehensive_patterns[entity_type]["patterns"].append(pattern_info)
                    comprehensive_patterns[entity_type]["confidence_scores"].append(pattern.confidence)
                    
                    # Add examples from pattern
                    if pattern.examples:
                        comprehensive_patterns[entity_type]["examples"].update(pattern.examples)
                        
        except Exception as e:
            logger.warning(f"Error loading patterns from PatternLoader: {e}")
    
    # Load aggregated examples from PatternLoader
    if pattern_loader:
        try:
            # Get all aggregated examples from patterns
            all_aggregated_examples = pattern_loader.get_all_aggregated_examples()

            for entity_type, examples in all_aggregated_examples.items():
                # Apply filter if specified
                if entity_type_filter and entity_type != entity_type_filter:
                    continue

                # Add aggregated examples to comprehensive patterns
                if examples:
                    comprehensive_patterns[entity_type]["examples"].update(examples)

            logger.info(f"Loaded aggregated examples for {len(all_aggregated_examples)} entity types from patterns")

        except Exception as e:
            logger.warning(f"Error loading aggregated examples from PatternLoader: {e}")
    
    # Convert sets to lists for JSON serialization
    for entity_type in comprehensive_patterns:
        comprehensive_patterns[entity_type]["examples"] = list(comprehensive_patterns[entity_type]["examples"])
        comprehensive_patterns[entity_type]["jurisdictions"] = list(comprehensive_patterns[entity_type]["jurisdictions"])
        comprehensive_patterns[entity_type]["sources"] = dict(comprehensive_patterns[entity_type]["sources"])
        del comprehensive_patterns[entity_type]["pattern_names"]  # Remove internal tracking set
    
    return dict(comprehensive_patterns)


@router.get("/patterns/comprehensive",
    response_model=ComprehensivePatternResponse,
    deprecated=True,
    summary="[DEPRECATED] Get Comprehensive Pattern Coverage",
    description="""
    **⚠️ DEPRECATED**: This endpoint is deprecated and will be removed in version 3.0.0.

    **Migration Guide**:
    - **Old**: `GET /api/v1/patterns/comprehensive`
    - **New**: `GET /api/v1/patterns?type=all&format=detailed`

    **Removal Date**: January 1, 2026

    **Why Deprecated**: This endpoint has been superseded by the unified `/api/v1/patterns`
    endpoint which provides:
    - Better query parameter design
    - Consistent response formats
    - Improved performance
    - More flexible filtering options

    **Example Migration**:
    ```bash
    # Old endpoint
    GET /api/v1/patterns/comprehensive?entity_type=COURT&include_examples=true

    # New endpoint (equivalent)
    GET /api/v1/patterns?type=all&entity_type=COURT&include_examples=true&format=detailed
    ```

    ---

    **Maximum Pattern Coverage for Regex Extraction**

    This endpoint provides comprehensive pattern information by merging patterns
    from ALL sources to maximize regex extraction quality and compete with LLM extraction.

    ### Pattern Sources
    - **federal/**: Federal court and statute patterns
    - **states/**: State-specific legal patterns (all 50 states)
    - **legal/**: General legal patterns and structures
    - **client/**: Client-specific and custom patterns
    - **comprehensive/**: Entity examples and supplemental patterns

    ### What's Merged
    - **Regex Patterns**: All unique patterns from every source
    - **Real Examples**: Examples aggregated from all pattern files
    - **Confidence Scores**: Pattern quality metrics
    - **Jurisdictions**: Coverage across federal and state jurisdictions
    - **Pattern Statistics**: Count, sources, and coverage metrics

    ### Key Features
    - **Deduplication**: Removes duplicate patterns while preserving unique ones
    - **Maximum Coverage**: Combines all available patterns for each entity type
    - **Real-World Examples**: Merges pattern examples with curated examples
    - **Source Attribution**: Tracks which directory each pattern comes from
    - **Confidence Scoring**: Average confidence across all patterns

    ### Query Parameters
    - **entity_type**: Filter for specific entity type (e.g., COURT, JUDGE)
    - **category**: Filter by category (e.g., 'Courts and Judicial', 'Legal Professionals')
    - **min_confidence**: Minimum confidence score threshold (0.0-1.0)
    - **bluebook_compliant**: Filter for Bluebook-compliant patterns only
    - **has_patterns**: Filter for entity types with (true) or without (false) regex patterns
    - **has_examples**: Filter for entity types with (true) or without (false) examples
    - **include_patterns**: Include full pattern details (default: true)
    - **include_examples**: Include all examples (default: true)

    ### Response Structure
    - **entity_types**: Comprehensive info for each entity type
    - **summary**: Overall statistics and coverage metrics
    - **metadata**: Service information and pattern sources

    ### Use Cases
    - **Pattern Quality Improvement**: Identify gaps in pattern coverage
    - **Regex Optimization**: Find high-confidence patterns for production
    - **Coverage Analysis**: Evaluate pattern coverage by entity type
    - **Example Generation**: Get real-world examples for testing
    """,
    responses={
        200: {
            "description": "Comprehensive patterns retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "entity_types": [
                            {
                                "entity_type": "COURT",
                                "category": "Courts and Judicial",
                                "total_patterns": 47,
                                "total_examples": 125,
                                "average_confidence": 0.92,
                                "pattern_sources": {
                                    "federal": 12,
                                    "states": 30,
                                    "legal": 3,
                                    "client": 2
                                },
                                "jurisdictions": ["federal", "california", "new_york", "texas"],
                                "bluebook_compliant": True,
                                "patterns": [
                                    {
                                        "name": "us_district_court",
                                        "pattern": "U\\.S\\. District Court",
                                        "confidence": 0.95,
                                        "source": "federal",
                                        "examples": ["U.S. District Court for the Southern District"]
                                    }
                                ],
                                "examples": [
                                    "United States District Court",
                                    "Supreme Court of the United States",
                                    "Court of Appeals for the Ninth Circuit"
                                ]
                            }
                        ],
                        "summary": {
                            "total_entity_types": 31,
                            "total_patterns": 295,
                            "total_examples": 1500,
                            "average_confidence": 0.88,
                            "pattern_sources": ["federal", "states", "legal", "client", "comprehensive"],
                            "coverage_percentage": 95.2
                        },
                        "metadata": {
                            "service_version": "2.0.0",
                            "pattern_loader_version": "1.0",
                            "merge_strategy": "comprehensive_deduplication"
                        }
                    }
                }
            }
        }
    }
)
async def get_comprehensive_patterns(
    fastapi_request: Request,
    response: Response,
    entity_type: Optional[str] = Query(None, description="Filter for specific entity type"),
    category: Optional[str] = Query(None, description="Filter by category (e.g., 'Courts and Judicial', 'Legal Professionals')"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence score"),
    bluebook_compliant: Optional[bool] = Query(None, description="Filter for Bluebook-compliant patterns only"),
    has_patterns: Optional[bool] = Query(None, description="Filter for entity types with/without regex patterns"),
    has_examples: Optional[bool] = Query(None, description="Filter for entity types with/without examples"),
    include_patterns: bool = Query(True, description="Include full pattern details"),
    include_examples: bool = Query(True, description="Include all examples")
):
    """Get comprehensive pattern coverage for maximum regex extraction quality."""
    # Add deprecation headers
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Tue, 01 Jan 2026 00:00:00 GMT"
    response.headers["Link"] = '</api/v1/patterns>; rel="successor-version"'

    # Log deprecation warning
    logger.warning(
        "DEPRECATED endpoint /api/v1/patterns/comprehensive accessed. "
        "Use /api/v1/patterns?type=all&format=detailed instead. "
        "This endpoint will be removed on 2026-01-01."
    )

    try:
        # Get pattern loader from app state
        pattern_loader = getattr(fastapi_request.app.state, "pattern_loader", None)
        
        if not pattern_loader:
            raise HTTPException(
                status_code=503,
                detail="Pattern loader not available"
            )
        
        # Load comprehensive patterns
        comprehensive_data = load_comprehensive_patterns(pattern_loader, entity_type)
        
        # Build response for each entity type
        entity_types_list = []
        total_patterns = 0
        total_examples = 0
        all_confidence_scores = []
        all_sources = set()
        
        for entity_type_name, entity_data in comprehensive_data.items():
            # Filter by confidence if specified
            patterns = entity_data["patterns"]
            if min_confidence > 0:
                patterns = [p for p in patterns if p["confidence"] >= min_confidence]
            
            # Calculate average confidence
            confidence_scores = entity_data["confidence_scores"]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Determine entity's category
            entity_category = "Miscellaneous"
            try:
                # Try to categorize as entity type
                entity_category = categorize_entity_type(entity_type_name)
            except:
                try:
                    # Try to categorize as citation type
                    entity_category = categorize_citation_type(entity_type_name)
                except:
                    pass
            
            # Check Bluebook compliance (heuristic based on pattern names and sources)
            # Patterns from federal, states, and legal directories are generally Bluebook compliant
            # Also check for explicit bluebook references in pattern names
            is_bluebook_compliant = any(
                "bluebook" in str(p.get("name", "")).lower() or 
                p.get("source") in ["federal", "states", "legal"] or
                "citation" in str(p.get("name", "")).lower()
                for p in patterns[:10] if patterns
            )
            
            # Apply category filter if specified
            if category is not None:
                # Skip entity types that don't match the category filter
                if category.lower() not in entity_category.lower():
                    continue
            
            # Apply has_patterns filter if specified
            if has_patterns is not None:
                # Check if entity has patterns
                entity_has_patterns = len(patterns) > 0
                # Skip entity types that don't match the filter
                if entity_has_patterns != has_patterns:
                    continue
            
            # Apply has_examples filter if specified
            if has_examples is not None:
                # Check if entity has examples
                entity_has_examples = len(entity_data["examples"]) > 0
                # Skip entity types that don't match the filter
                if entity_has_examples != has_examples:
                    continue
            
            # Apply Bluebook compliance filter if specified
            if bluebook_compliant is not None:
                # Skip entity types that don't match the filter
                if is_bluebook_compliant != bluebook_compliant:
                    continue
            
            pattern_info = ComprehensivePatternInfo(
                entity_type=entity_type_name,
                category=entity_category,
                total_patterns=len(patterns),
                total_examples=len(entity_data["examples"]),
                average_confidence=avg_confidence,
                pattern_sources=entity_data["sources"],
                patterns=patterns if include_patterns else [],
                examples=entity_data["examples"] if include_examples else [],
                jurisdictions=entity_data["jurisdictions"],
                bluebook_compliant=is_bluebook_compliant
            )
            
            entity_types_list.append(pattern_info)
            
            # Update totals
            total_patterns += len(patterns)
            total_examples += len(entity_data["examples"])
            all_confidence_scores.extend(confidence_scores)
            all_sources.update(entity_data["sources"].keys())
        
        # Calculate summary statistics
        avg_overall_confidence = sum(all_confidence_scores) / len(all_confidence_scores) if all_confidence_scores else 0.0
        
        # Estimate coverage percentage (based on having patterns for entity types)
        total_possible_types = len(EntityType) + len(CitationType)
        covered_types = len(entity_types_list)
        coverage_percentage = (covered_types / total_possible_types * 100) if total_possible_types > 0 else 0.0
        
        summary = {
            "total_entity_types": len(entity_types_list),
            "total_patterns": total_patterns,
            "total_examples": total_examples,
            "average_confidence": round(avg_overall_confidence, 3),
            "pattern_sources": sorted(list(all_sources)),
            "coverage_percentage": round(coverage_percentage, 1),
            "filtered_by_confidence": min_confidence if min_confidence > 0 else None,
            "filtered_by_bluebook": bluebook_compliant,
            "filtered_by_category": category,
            "filtered_by_patterns": has_patterns,
            "filtered_by_examples": has_examples
        }
        
        metadata = {
            "service_version": "2.0.0",
            "pattern_loader_version": "1.0",
            "merge_strategy": "comprehensive_deduplication",
            "pattern_directories_scanned": ["federal", "states", "legal", "client", "comprehensive"],
            "entity_type_filter": entity_type,
            "category_filter": category,
            "min_confidence_filter": min_confidence,
            "bluebook_compliant_filter": bluebook_compliant,
            "has_patterns_filter": has_patterns,
            "has_examples_filter": has_examples
        }
        
        # Log the request
        log_client = getattr(fastapi_request.app.state, "log_client", None)
        if log_client:
            await log_client.log(
                level="INFO",
                message="Comprehensive patterns requested",
                service="entity-extraction-service",
                request_id=getattr(fastapi_request.state, "request_id", ""),
                metadata={
                    "entity_type": entity_type,
                    "min_confidence": min_confidence,
                    "bluebook_compliant": bluebook_compliant,
                    "total_patterns": total_patterns,
                    "total_entity_types": len(entity_types_list)
                }
            )
        
        return ComprehensivePatternResponse(
            entity_types=entity_types_list,
            summary=summary,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get comprehensive patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve comprehensive patterns: {str(e)}"
        )