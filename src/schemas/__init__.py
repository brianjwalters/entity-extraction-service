"""
Schemas Package for Entity Extraction Service

This package contains Pydantic schemas for use with vLLM's guided_json feature
and other schema validation needs.

Modules:
- guided_json_schemas: Schemas for vLLM guided JSON generation
  - LurisEntityV2ExtractionResponse: Entity extraction with LurisEntityV2
  - LurisRelationshipExtractionResponse: Wave 4 relationship extraction
"""

from src.schemas.guided_json_schemas import (
    LurisEntityV2ExtractionResponse,
    LurisRelationshipExtractionResponse,
)

__all__ = [
    'LurisEntityV2ExtractionResponse',
    'LurisRelationshipExtractionResponse',
]
