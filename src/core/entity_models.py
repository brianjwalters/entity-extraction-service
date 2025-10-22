"""
Pydantic models for structured entity extraction using vLLM guided_json.

⚠️  DEPRECATED: This module is deprecated and will be removed in a future version.
    Use src.schemas.guided_json_schemas instead.

Migration Guide:
  EntityExtractionResponse → LurisEntityV2ExtractionResponse
  SinglePassExtractionResponse → LurisEntityV2ExtractionResponse
  DetailedRelationshipExtractionResponse → LurisRelationshipExtractionResponse

All new code should use the LurisEntityV2-based schemas from guided_json_schemas.py.
These schemas provide better compliance with the canonical LurisEntityV2 structure
and support the 160 standardized entity types.
"""

import warnings
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Issue deprecation warning when this module is imported
warnings.warn(
    "entity_models.py is deprecated and will be removed in a future version. "
    "Use src.schemas.guided_json_schemas instead. "
    "Migration: "
    "  EntityExtractionResponse → LurisEntityV2ExtractionResponse "
    "  SinglePassExtractionResponse → LurisEntityV2ExtractionResponse "
    "  DetailedRelationshipExtractionResponse → LurisRelationshipExtractionResponse",
    DeprecationWarning,
    stacklevel=2
)


class ExtractedEntity(BaseModel):
    """A single extracted entity with metadata."""

    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Legal entity type (e.g., PERSON, CASE_CITATION, STATUTE, etc.)"
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The extracted entity text as it appears in the document"
    )
    start_pos: Optional[int] = Field(
        None,
        description="Character position where entity starts in document"
    )
    end_pos: Optional[int] = Field(
        None,
        description="Character position where entity ends in document"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this entity (0.0-1.0)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the entity"
    )


class EntityExtractionResponse(BaseModel):
    """
    Complete response from entity extraction.

    ⚠️  DEPRECATED: Use LurisEntityV2ExtractionResponse from src.schemas.guided_json_schemas
    """

    entities: List[ExtractedEntity] = Field(
        ...,
        description="List of all extracted entities from the document (required, non-empty)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "entities": [
                    {
                        "entity_type": "CASE_CITATION",
                        "text": "United States v. Rahimi, No. 22-915 (U.S. Jun. 21, 2024)",
                        "start_pos": 0,
                        "end_pos": 58,
                        "confidence": 0.98,
                        "metadata": {
                            "court": "Supreme Court",
                            "case_number": "22-915",
                            "decision_date": "2024-06-21"
                        }
                    },
                    {
                        "entity_type": "STATUTE",
                        "text": "18 U.S.C. § 922(g)(8)",
                        "start_pos": 120,
                        "end_pos": 141,
                        "confidence": 0.95
                    }
                ]
            }
        }


# ============================================================================
# Enhanced Models for Quality Testing
# ============================================================================

class EnhancedExtractedEntity(BaseModel):
    """Enhanced entity with quality testing fields."""

    # Core fields (same as ExtractedEntity)
    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Legal entity type (e.g., PERSON, CASE_CITATION, STATUTE, etc.)"
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The extracted entity text as it appears in the document"
    )
    start_pos: Optional[int] = Field(
        None,
        description="Character position where entity starts in document"
    )
    end_pos: Optional[int] = Field(
        None,
        description="Character position where entity ends in document"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this entity (0.0-1.0)"
    )

    # NEW: Quality testing fields
    prompt_template: str = Field(
        ...,
        description="Prompt that generated this entity (e.g., 'wave1', 'wave2', 'wave3', 'single_pass')"
    )
    wave_number: Optional[int] = Field(
        None,
        description="Wave number (1-3) for 3-wave strategy, None for single-pass"
    )
    context_before: str = Field(
        "",
        description="Text context before entity (up to 50 chars)"
    )
    context_after: str = Field(
        "",
        description="Text context after entity (up to 50 chars)"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the entity"
    )


class SimpleRelationship(BaseModel):
    """A simple relationship between two entities (for testing)."""

    source_entity_id: str = Field(
        ...,
        description="ID of the source entity"
    )
    target_entity_id: str = Field(
        ...,
        description="ID of the target entity"
    )
    relationship_type: str = Field(
        ...,
        description="Relationship type (e.g., CITES, PARTY_TO_CASE, DECIDED_BY, etc.)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this relationship (0.0-1.0)"
    )


class RelationshipExtractionItem(BaseModel):
    """Detailed relationship item for Wave 4 extraction with full context."""

    source_entity_id: str = Field(
        ...,
        description="ID of the source entity"
    )
    target_entity_id: str = Field(
        ...,
        description="ID of the target entity"
    )
    relationship_type: str = Field(
        ...,
        description="Relationship type (e.g., CITES, PARTY_TO_CASE, DECIDED_BY)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this relationship (0.0-1.0)"
    )
    evidence_text: str = Field(
        ...,
        description="Text evidence for this relationship from the document"
    )
    context_before: str = Field(
        ...,
        description="Text context before the relationship evidence"
    )
    context_after: str = Field(
        ...,
        description="Text context after the relationship evidence"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (positions, wave number, patterns, etc.)"
    )


class RelationshipExtractionResponse(BaseModel):
    """Response for relationship extraction (simplified for testing)."""

    relationships: List[SimpleRelationship] = Field(
        default_factory=list,
        description="List of all extracted relationships between entities"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "relationships": [
                    {
                        "source_entity_id": "e1",
                        "target_entity_id": "e2",
                        "relationship_type": "CITES",
                        "confidence": 0.95
                    }
                ]
            }
        }


class DetailedRelationshipExtractionResponse(BaseModel):
    """
    Response for Wave 4 detailed relationship extraction with full context.

    ⚠️  DEPRECATED: Use LurisRelationshipExtractionResponse from src.schemas.guided_json_schemas
    """

    relationships: List[RelationshipExtractionItem] = Field(
        default_factory=list,
        description="List of all extracted relationships with detailed context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "relationships": [
                    {
                        "source_entity_id": "entity_12",
                        "target_entity_id": "entity_45",
                        "relationship_type": "CITES_CASE",
                        "confidence": 0.95,
                        "evidence_text": "In Roe v. Wade, the Court cited Griswold v. Connecticut",
                        "context_before": "The majority opinion thoroughly analyzed",
                        "context_after": "as precedent for privacy rights",
                        "metadata": {
                            "evidence_start_pos": 12450,
                            "evidence_end_pos": 12537,
                            "wave_number": 4,
                            "relationship_category": "case_to_case"
                        }
                    }
                ]
            }
        }


class SinglePassExtractionResponse(BaseModel):
    """
    Combined response for single-pass extraction (entities + relationships).

    ⚠️  DEPRECATED: Use LurisEntityV2ExtractionResponse from src.schemas.guided_json_schemas

    Used for SINGLE_PASS strategy on very small documents (<5K chars).
    Extracts both entities and relationships in a single LLM call.
    """

    entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="All extracted entities from single pass"
    )

    relationships: List[SimpleRelationship] = Field(
        default_factory=list,
        description="All extracted relationships from single pass"
    )

    extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about single-pass extraction (strategy, timing, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "entities": [
                    {
                        "entity_type": "CASE_CITATION",
                        "text": "United States v. Rahimi, 602 U.S. ___ (2024)",
                        "start_pos": 0,
                        "end_pos": 43,
                        "confidence": 0.98
                    }
                ],
                "relationships": [
                    {
                        "source_entity_id": "e1",
                        "target_entity_id": "e2",
                        "relationship_type": "CITES",
                        "confidence": 0.92
                    }
                ],
                "extraction_metadata": {
                    "strategy": "single_pass",
                    "total_entities": 15,
                    "total_relationships": 8
                }
            }
        }


class ExtractedRelationship(BaseModel):
    """A relationship between two extracted entities."""

    relationship_id: str = Field(
        ...,
        description="Unique identifier for this relationship"
    )
    type: str = Field(
        ...,
        description="Relationship type (e.g., CITES, PARTY_TO_CASE, DECIDED_BY, etc.)"
    )
    source_entity_id: str = Field(
        ...,
        description="ID of the source entity"
    )
    target_entity_id: str = Field(
        ...,
        description="ID of the target entity"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this relationship (0.0-1.0)"
    )
    prompt_template: str = Field(
        ...,
        description="Prompt that generated this relationship"
    )
    wave_number: Optional[int] = Field(
        None,
        description="Wave number (typically 3 for relationships)"
    )
    context: str = Field(
        "",
        description="Textual context describing the relationship"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the relationship"
    )


class EnhancedExtractionResponse(BaseModel):
    """Enhanced response with entities, relationships, and detailed metadata."""

    entities: List[EnhancedExtractedEntity] = Field(
        default_factory=list,
        description="List of all extracted entities with quality testing fields"
    )
    relationships: List[ExtractedRelationship] = Field(
        default_factory=list,
        description="List of all extracted relationships between entities"
    )
    extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the extraction process"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "entities": [
                    {
                        "entity_type": "CASE_CITATION",
                        "text": "United States v. Rahimi, No. 22-915 (U.S. Jun. 21, 2024)",
                        "start_pos": 145,
                        "end_pos": 202,
                        "context_before": "IN THE SUPREME COURT OF THE UNITED STATES\n\n",
                        "context_after": "\n\nCertiorari to the United States Court...",
                        "confidence": 0.98,
                        "prompt_template": "wave1",
                        "wave_number": 1,
                        "metadata": {
                            "court": "Supreme Court",
                            "case_number": "22-915"
                        }
                    }
                ],
                "relationships": [
                    {
                        "relationship_id": "rel_001",
                        "type": "CITES",
                        "source_entity_id": "ent_001",
                        "target_entity_id": "ent_002",
                        "confidence": 0.92,
                        "prompt_template": "wave3",
                        "wave_number": 3,
                        "context": "The case challenges the constitutionality of 18 U.S.C. § 922(g)(8)..."
                    }
                ],
                "extraction_metadata": {
                    "strategy": "three_wave",
                    "waves_executed": 3,
                    "processing_time_seconds": 45.2,
                    "total_tokens_used": 15234,
                    "prompt_templates_used": ["wave1", "wave2", "wave3"]
                }
            }
        }
