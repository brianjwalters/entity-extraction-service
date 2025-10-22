"""
Relationship Extraction Module for CALES Legal Entity System

This module provides comprehensive relationship extraction capabilities for legal documents,
including pattern-based, dependency parsing, coreference resolution, and machine learning approaches.
"""

from .relationship_models import (
    RelationshipType,
    EntityMention,
    RelationshipInstance,
    RelationshipExtractionResult,
    RelationshipExtractionModel
)

from .legal_relationship_patterns import (
    LegalRelationshipPatterns,
    RelationshipPattern
)

from .relationship_extractor import (
    RelationshipExtractor,
    ExtractionConfig
)

__all__ = [
    "RelationshipType",
    "EntityMention",
    "RelationshipInstance",
    "RelationshipExtractionResult",
    "RelationshipExtractionModel",
    "LegalRelationshipPatterns",
    "RelationshipPattern",
    "RelationshipExtractor",
    "ExtractionConfig"
]

__version__ = "1.0.0"
__author__ = "CALES Development Team"
__description__ = "Legal relationship extraction for entity analysis"