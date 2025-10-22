"""
Models package for Entity Extraction Service.

Contains comprehensive Pydantic models for the hybrid REGEX + AI extraction workflow,
including request/response validation, entity/citation models, and relationship tracking.
"""

from .requests import ExtractionRequest, ExtractionOptions
from .responses import ExtractionResponse, ProcessingSummary
from .entities import (
    Entity, Citation, EntityRelationship,
    EntityType, CitationType, ExtractionMethod,
    EntityAttributes, CitationComponents, TextPosition
)

__all__ = [
    # Request models
    "ExtractionRequest",
    "ExtractionOptions",
    
    # Response models
    "ExtractionResponse", 
    "ProcessingSummary",
    
    # Entity and Citation models
    "Entity",
    "Citation", 
    "EntityRelationship",
    
    # Enums
    "EntityType",
    "CitationType", 
    "ExtractionMethod",
    
    # Component models
    "EntityAttributes",
    "CitationComponents",
    "TextPosition",
]