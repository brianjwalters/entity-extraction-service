"""
LurisEntityV2 Schema Definition (Standalone for PoC)

This is a simplified version of LurisEntityV2 for proof of concept.
Does not import from main codebase.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class LurisEntityV2:
    """
    LurisEntityV2 entity schema for legal document processing.

    This is the standardized entity format used across all Luris services.
    Field naming is strict: entity_type (NOT type), start_pos (NOT start), end_pos (NOT end).
    """

    # Core Identification (REQUIRED)
    id: str
    text: str
    entity_type: str  # NOT "type"

    # Position Information (REQUIRED)
    start_pos: int  # NOT "start"
    end_pos: int    # NOT "end"

    # Confidence and Method (REQUIRED)
    confidence: float  # 0.0-1.0
    extraction_method: str  # "eyecite" | "hybrid_eyecite_llm" | "llm"

    # Optional Classification
    subtype: Optional[str] = None
    category: Optional[str] = None

    # Rich Metadata (REQUIRED)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps (REQUIRED)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "entity_type": self.entity_type,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "subtype": self.subtype,
            "category": self.category,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LurisEntityV2":
        """Create entity from dictionary."""
        return cls(**data)


# Entity type constants (subset for citation extraction)
class EntityType:
    """LurisEntityV2 entity types relevant to citation extraction."""

    # Case Citations
    CASE_CITATION = "CASE_CITATION"
    CASE_CITATION_SHORT = "CASE_CITATION_SHORT"

    # Statutory Citations
    STATUTE_CITATION = "STATUTE_CITATION"
    USC_CITATION = "USC_CITATION"
    USC_SUBSECTION_CITATION = "USC_SUBSECTION_CITATION"
    CFR_CITATION = "CFR_CITATION"
    STATE_STATUTE_CITATION = "STATE_STATUTE_CITATION"

    # Journal/Law Review Citations
    JOURNAL_CITATION = "JOURNAL_CITATION"
    LAW_REVIEW_CITATION = "LAW_REVIEW_CITATION"

    # Reference Citations
    ID_CITATION = "ID_CITATION"
    SUPRA_CITATION = "SUPRA_CITATION"
    INTERNAL_REFERENCE = "INTERNAL_REFERENCE"

    # Unknown/Other
    UNKNOWN_CITATION = "UNKNOWN_CITATION"


# Extraction method constants
class ExtractionMethod:
    """Extraction method identifiers."""

    EYECITE = "eyecite"
    LLM = "llm"
    HYBRID_EYECITE_LLM = "hybrid_eyecite_llm"
    REGEX = "regex"
    AI_ENHANCED = "ai_enhanced"


def create_entity(
    text: str,
    entity_type: str,
    start_pos: int,
    end_pos: int,
    confidence: float,
    extraction_method: str,
    metadata: Optional[Dict[str, Any]] = None,
    subtype: Optional[str] = None,
    category: Optional[str] = None,
) -> LurisEntityV2:
    """
    Factory function to create LurisEntityV2 entity.

    Args:
        text: Extracted text
        entity_type: Entity type (use EntityType constants)
        start_pos: Start position in document
        end_pos: End position in document
        confidence: Confidence score (0.0-1.0)
        extraction_method: Method used (use ExtractionMethod constants)
        metadata: Additional metadata
        subtype: Optional subtype
        category: Optional category

    Returns:
        LurisEntityV2 entity
    """
    return LurisEntityV2(
        id=str(uuid.uuid4()),
        text=text,
        entity_type=entity_type,
        start_pos=start_pos,
        end_pos=end_pos,
        confidence=confidence,
        extraction_method=extraction_method,
        metadata=metadata or {},
        subtype=subtype,
        category=category,
    )
