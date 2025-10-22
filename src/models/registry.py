"""
Entity Registry Models for Cross-Chunk Context Preservation

This module provides models for tracking entities across document chunks,
resolving references, and maintaining global entity context.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Set, Any, Tuple
from datetime import datetime
from enum import Enum
import uuid

from .entities import EntityType, TextPosition, EntityAttributes


class ResolutionStatus(str, Enum):
    """Status of entity resolution and deduplication."""
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    MERGED = "merged"
    CANONICAL = "canonical"
    AMBIGUOUS = "ambiguous"
    REFERENCE = "reference"


class ReferenceType(str, Enum):
    """Types of entity references for co-reference resolution."""
    FULL_NAME = "full_name"
    LAST_NAME = "last_name"
    FIRST_NAME = "first_name"
    TITLE = "title"
    PRONOUN = "pronoun"
    DEFINITE_ARTICLE = "definite_article"  # "the defendant"
    POSSESSIVE = "possessive"  # "plaintiff's counsel"
    ABBREVIATION = "abbreviation"
    ACRONYM = "acronym"
    ALIAS = "alias"
    ROLE_REFERENCE = "role_reference"  # "opposing counsel"
    POSITIONAL = "positional"  # "aforementioned party"


class EntityOccurrence(BaseModel):
    """Single occurrence of an entity within a chunk."""
    
    chunk_id: str = Field(
        ...,
        description="ID of the chunk containing this occurrence"
    )
    
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Sequential index of the chunk in the document"
    )
    
    position: TextPosition = Field(
        ...,
        description="Position within the chunk"
    )
    
    global_position: TextPosition = Field(
        ...,
        description="Position within the entire document"
    )
    
    text_variant: str = Field(
        ...,
        description="Exact text as it appears in this occurrence"
    )
    
    reference_type: ReferenceType = Field(
        ...,
        description="How the entity is referenced in this occurrence"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this specific occurrence"
    )
    
    context_before: str = Field(
        default="",
        max_length=500,
        description="Text context before the entity"
    )
    
    context_after: str = Field(
        default="",
        max_length=500,
        description="Text context after the entity"
    )
    
    extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata from extraction process"
    )
    
    @validator('text_variant')
    def validate_text_variant(cls, v):
        """Ensure text variant is not empty."""
        if not v or not v.strip():
            raise ValueError('Text variant cannot be empty')
        return v.strip()


class EntityRelationship(BaseModel):
    """Relationship between two entities in the registry."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique relationship identifier"
    )
    
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
        description="Type of relationship (e.g., 'represents', 'opposes', 'presides_over')"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this relationship"
    )
    
    evidence: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Evidence supporting this relationship"
    )
    
    chunk_ids: List[str] = Field(
        default_factory=list,
        description="Chunks where this relationship was observed"
    )
    
    bidirectional: bool = Field(
        default=False,
        description="Whether the relationship is bidirectional"
    )
    
    temporal_scope: Optional[str] = Field(
        None,
        description="Temporal scope of the relationship if applicable"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional relationship metadata"
    )


class RegisteredEntity(BaseModel):
    """Entity registered globally across all chunks with merged information."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique entity identifier in registry"
    )
    
    canonical_text: str = Field(
        ...,
        description="Canonical/normalized form of the entity"
    )
    
    entity_type: EntityType = Field(
        ...,
        description="Primary entity classification"
    )
    
    entity_subtype: str = Field(
        ...,
        description="Detailed entity subclassification"
    )
    
    all_variants: Set[str] = Field(
        default_factory=set,
        description="All text variants found for this entity"
    )
    
    occurrences: List[EntityOccurrence] = Field(
        default_factory=list,
        description="All occurrences across chunks"
    )
    
    merged_from: List[str] = Field(
        default_factory=list,
        description="IDs of entities merged into this one"
    )
    
    resolution_status: ResolutionStatus = Field(
        default=ResolutionStatus.UNRESOLVED,
        description="Current resolution status"
    )
    
    aggregate_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregated confidence score across all occurrences"
    )
    
    attributes: EntityAttributes = Field(
        default_factory=EntityAttributes,
        description="Merged attributes from all occurrences"
    )
    
    relationships: List[str] = Field(
        default_factory=list,
        description="IDs of relationships involving this entity"
    )
    
    reference_chains: List[List[str]] = Field(
        default_factory=list,
        description="Chains of references resolved to this entity"
    )
    
    first_seen_chunk: str = Field(
        ...,
        description="ID of chunk where entity was first seen"
    )
    
    last_seen_chunk: str = Field(
        ...,
        description="ID of chunk where entity was last seen"
    )
    
    chunk_span: Tuple[int, int] = Field(
        ...,
        description="Range of chunk indices containing this entity"
    )
    
    total_occurrences: int = Field(
        default=0,
        ge=0,
        description="Total number of occurrences"
    )
    
    extraction_methods_used: Set[str] = Field(
        default_factory=set,
        description="All extraction methods that found this entity"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional entity metadata"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Registration timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    @validator('canonical_text')
    def validate_canonical_text(cls, v):
        """Ensure canonical text is not empty."""
        if not v or not v.strip():
            raise ValueError('Canonical text cannot be empty')
        return v.strip()
    
    @validator('total_occurrences')
    def validate_occurrence_count(cls, v, values):
        """Ensure occurrence count matches occurrences list."""
        if 'occurrences' in values:
            actual_count = len(values['occurrences'])
            if v != actual_count:
                return actual_count
        return v
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class RegistryMetadata(BaseModel):
    """Metadata about the entity registry itself."""
    
    document_id: str = Field(
        ...,
        description="ID of the document being processed"
    )
    
    document_name: str = Field(
        ...,
        description="Name of the document"
    )
    
    total_chunks: int = Field(
        ...,
        ge=1,
        description="Total number of chunks in document"
    )
    
    processed_chunks: int = Field(
        default=0,
        ge=0,
        description="Number of chunks processed"
    )
    
    total_entities: int = Field(
        default=0,
        ge=0,
        description="Total unique entities registered"
    )
    
    total_relationships: int = Field(
        default=0,
        ge=0,
        description="Total relationships discovered"
    )
    
    entity_type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of entities by type"
    )
    
    resolution_statistics: Dict[str, int] = Field(
        default_factory=dict,
        description="Statistics on entity resolution"
    )
    
    merge_operations: int = Field(
        default=0,
        ge=0,
        description="Number of entity merges performed"
    )
    
    reference_resolutions: int = Field(
        default=0,
        ge=0,
        description="Number of references resolved"
    )
    
    processing_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total processing time in milliseconds"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Registry creation timestamp"
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Registry configuration parameters"
    )
    
    quality_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Quality metrics for the registry"
    )


class EntityGraph(BaseModel):
    """Graph representation of entities and their relationships."""
    
    nodes: List[RegisteredEntity] = Field(
        default_factory=list,
        description="Entity nodes in the graph"
    )
    
    edges: List[EntityRelationship] = Field(
        default_factory=list,
        description="Relationship edges in the graph"
    )
    
    clusters: List[List[str]] = Field(
        default_factory=list,
        description="Entity clusters/communities"
    )
    
    centrality_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Entity centrality scores"
    )
    
    metadata: RegistryMetadata = Field(
        ...,
        description="Registry metadata"
    )


class ResolutionCandidate(BaseModel):
    """Candidate for entity resolution/merging."""
    
    entity_id: str = Field(
        ...,
        description="ID of the candidate entity"
    )
    
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score to target entity"
    )
    
    matching_features: List[str] = Field(
        default_factory=list,
        description="Features that match between entities"
    )
    
    conflicting_features: List[str] = Field(
        default_factory=list,
        description="Features that conflict between entities"
    )
    
    resolution_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in resolution"
    )
    
    resolution_method: str = Field(
        ...,
        description="Method used for resolution scoring"
    )


class RegistrySnapshot(BaseModel):
    """Snapshot of registry state for persistence."""
    
    snapshot_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique snapshot identifier"
    )
    
    entities: Dict[str, RegisteredEntity] = Field(
        default_factory=dict,
        description="All registered entities by ID"
    )
    
    relationships: Dict[str, EntityRelationship] = Field(
        default_factory=dict,
        description="All relationships by ID"
    )
    
    metadata: RegistryMetadata = Field(
        ...,
        description="Registry metadata"
    )
    
    checkpoint_chunk_id: Optional[str] = Field(
        None,
        description="Last processed chunk ID for resumption"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Snapshot creation timestamp"
    )
    
    compression: Optional[str] = Field(
        None,
        description="Compression method if applied"
    )
    
    checksum: Optional[str] = Field(
        None,
        description="Checksum for integrity verification"
    )