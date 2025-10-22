"""
Guided JSON Schemas for vLLM Entity Extraction

This module contains Pydantic schemas designed specifically for use with vLLM's guided_json feature.
These schemas ensure that LLM outputs strictly conform to the LurisEntityV2 structure, preventing
malformed JSON and ensuring consistent entity extraction across the Luris platform.

## Purpose

vLLM's guided_json feature constrains the LLM's output to match a specific JSON schema, eliminating
common issues like:
- Malformed JSON syntax
- Missing required fields
- Invalid field types
- Non-standard entity structures

## Integration Points

These schemas replace legacy schemas from `src/core/entity_models.py`:

1. **LurisEntityV2ExtractionResponse** replaces:
   - `EntityExtractionResponse` (extraction_orchestrator.py lines 1122-1125)
   - `SinglePassExtractionResponse` (extraction_orchestrator.py lines 1179-1182)

2. **LurisRelationshipExtractionResponse** replaces:
   - `DetailedRelationshipExtractionResponse` (extraction_orchestrator.py lines 689-692)

## Usage with vLLM

```python
from src.schemas.guided_json_schemas import LurisEntityV2ExtractionResponse
from openai import OpenAI

# Initialize vLLM client (OpenAI compatible)
client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")

# Get JSON schema for guided generation
schema = LurisEntityV2ExtractionResponse.model_json_schema()

# Make LLM call with guided JSON
response = client.chat.completions.create(
    model="qwen3-vl-instruct-384k",
    messages=[
        {"role": "system", "content": "Extract legal entities in LurisEntityV2 format"},
        {"role": "user", "content": document_text}
    ],
    temperature=0.0,
    extra_body={"guided_json": schema}  # Constrains output to schema
)

# Parse response (guaranteed to match schema)
import json
result = LurisEntityV2ExtractionResponse.model_validate_json(
    response.choices[0].message.content
)

entities = result.entities  # List[LurisEntityV2]
```

## Schema Compliance

All schemas in this file:
- Use LurisEntityV2 with 160 canonical entity types
- Follow Pydantic V2 standards
- Generate valid JSON Schema via model_json_schema()
- Are compatible with vLLM's guided_json implementation
- Enforce strict field name compliance (entity_type, start_pos, end_pos)

## vLLM Guided JSON Documentation

https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#guided-decoding

## Migration Notes

When migrating from entity_models.py to these schemas:
1. Replace `EntityExtractionResponse` with `LurisEntityV2ExtractionResponse`
2. Replace `SinglePassExtractionResponse` with `LurisEntityV2ExtractionResponse`
3. Replace `DetailedRelationshipExtractionResponse` with `LurisRelationshipExtractionResponse`
4. Update guided_json calls to use new schemas
5. Validate that entities conform to LurisEntityV2 structure

## Authors

- Backend Engineer Agent (Entity Extraction Service Team)
- Created: 2025-10-18
- Schema Version: 2.0 (LurisEntityV2 compliant)
"""

import uuid
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

# Import canonical LurisEntityV2 schema with 160 entity types
from src.core.schema.luris_entity_schema import (
    LurisEntityV2,
    EntityType,
    ExtractionMethod,
    Position,
    EntityMetadata
)


class LurisEntityV2ExtractionResponse(BaseModel):
    """
    Guided JSON schema for entity extraction using LurisEntityV2.

    This schema is designed for use with vLLM's guided_json feature to ensure
    the LLM outputs strictly conform to the LurisEntityV2 structure. It replaces
    both EntityExtractionResponse and SinglePassExtractionResponse from entity_models.py.

    ## Usage

    ### With vLLM Guided JSON
    ```python
    schema = LurisEntityV2ExtractionResponse.model_json_schema()
    extra_body = {"guided_json": schema}

    response = client.chat.completions.create(
        model="qwen3-vl-instruct-384k",
        messages=[...],
        extra_body=extra_body
    )
    ```

    ### Used In

    - extraction_orchestrator.py:
      - Lines 1122-1125: Wave 1/2/3 entity extraction
      - Lines 1179-1182: Single-pass entity extraction (small documents)
    - Wave System entity extraction (Waves 1, 2, 3)

    ## Fields

    - **entities**: List of extracted entities following LurisEntityV2 schema
    - **metadata**: Optional extraction metadata (wave number, timing, model info)

    ## Schema Guarantees

    When using guided_json with this schema:
    1. All entities will have required LurisEntityV2 fields
    2. Field names will be correct (entity_type, start_pos, end_pos)
    3. Confidence scores will be in valid range [0.0, 1.0]
    4. Entity types will use canonical EntityType enum values
    5. JSON structure will be valid and parseable

    ## Validation

    Pydantic automatically validates:
    - All required fields present
    - Field types match schema
    - Confidence scores in [0.0, 1.0] range
    - Position values are non-negative
    - Entity types are valid strings
    """

    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of extracted entities following LurisEntityV2 schema. "
            "Each entity must have: id, text, entity_type, start_pos, end_pos, "
            "confidence, extraction_method, metadata, created_at"
        )
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Additional extraction metadata including: "
            "wave_number (1-4), extraction_time (seconds), "
            "model_name, temperature, entity_count, etc."
        )
    )

    @field_validator('entities')
    @classmethod
    def validate_entities(cls, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate that all entities conform to LurisEntityV2 structure.

        Checks:
        1. Required fields present (text, entity_type, start_pos, end_pos, confidence, extraction_method)
        2. Field types are correct
        3. Confidence scores in [0.0, 1.0]
        4. Position values non-negative
        5. No forbidden field names (type, start, end)

        Raises:
            ValueError: If entity structure is invalid
        """
        for i, entity in enumerate(entities):
            # Check for forbidden field names
            if 'type' in entity:
                raise ValueError(
                    f"Entity {i}: Forbidden field 'type' detected. "
                    "Use 'entity_type' instead per LurisEntityV2 standard."
                )
            if 'start' in entity:
                raise ValueError(
                    f"Entity {i}: Forbidden field 'start' detected. "
                    "Use 'start_pos' instead per LurisEntityV2 standard."
                )
            if 'end' in entity:
                raise ValueError(
                    f"Entity {i}: Forbidden field 'end' detected. "
                    "Use 'end_pos' instead per LurisEntityV2 standard."
                )

            # Check required fields
            required_fields = {
                'text', 'entity_type', 'confidence',
                'extraction_method'
            }
            missing_fields = required_fields - set(entity.keys())
            if missing_fields:
                raise ValueError(
                    f"Entity {i}: Missing required fields: {missing_fields}"
                )

            # Validate confidence range
            confidence = entity.get('confidence', 0.0)
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                raise ValueError(
                    f"Entity {i}: Confidence {confidence} must be float in range [0.0, 1.0]"
                )

            # Validate position fields if present
            if 'start_pos' in entity:
                start_pos = entity['start_pos']
                if not isinstance(start_pos, int) or start_pos < 0:
                    raise ValueError(
                        f"Entity {i}: start_pos must be non-negative integer, got {start_pos}"
                    )

            if 'end_pos' in entity:
                end_pos = entity['end_pos']
                if not isinstance(end_pos, int) or end_pos < 0:
                    raise ValueError(
                        f"Entity {i}: end_pos must be non-negative integer, got {end_pos}"
                    )

            # Validate positions are consistent
            if 'start_pos' in entity and 'end_pos' in entity:
                if entity['end_pos'] < entity['start_pos']:
                    raise ValueError(
                        f"Entity {i}: end_pos ({entity['end_pos']}) must be >= "
                        f"start_pos ({entity['start_pos']})"
                    )

        return entities

    @model_validator(mode='after')
    def populate_metadata(self):
        """
        Auto-populate metadata fields if not provided.

        Adds:
        - entity_count: Total number of extracted entities
        - timestamp: Current extraction time
        - schema_version: LurisEntityV2 version identifier
        """
        if not self.metadata:
            self.metadata = {}

        # Add entity count
        if 'entity_count' not in self.metadata:
            self.metadata['entity_count'] = len(self.entities)

        # Add timestamp if missing
        if 'timestamp' not in self.metadata:
            self.metadata['timestamp'] = time.time()

        # Add schema version
        if 'schema_version' not in self.metadata:
            self.metadata['schema_version'] = 'LurisEntityV2'

        return self

    def to_luris_entities(self) -> List[LurisEntityV2]:
        """
        Convert entity dictionaries to LurisEntityV2 objects.

        This method transforms the raw entity dictionaries returned by the LLM
        into fully validated LurisEntityV2 objects with proper typing, Position
        objects, and EntityMetadata.

        Returns:
            List[LurisEntityV2]: Validated entity objects

        Example:
            >>> response = LurisEntityV2ExtractionResponse(entities=[...])
            >>> entities = response.to_luris_entities()
            >>> for entity in entities:
            ...     print(f"{entity.text}: {entity.entity_type}")
        """
        luris_entities = []

        for entity_dict in self.entities:
            # Prepare entity data for LurisEntityV2
            entity_data = entity_dict.copy()

            # Extract metadata and convert to custom_attributes format
            # to avoid EntityMetadata field mismatch issues
            raw_metadata = entity_data.get('metadata', {})
            if isinstance(raw_metadata, dict):
                # Store custom metadata in EntityMetadata.custom_attributes
                entity_metadata = EntityMetadata(custom_attributes=raw_metadata)
                entity_data['metadata'] = entity_metadata

            # Create Position object from start_pos/end_pos
            position = Position(
                start_pos=entity_data.get('start_pos', 0),
                end_pos=entity_data.get('end_pos', 0)
            )

            # Create LurisEntityV2 directly with proper types
            entity = LurisEntityV2(
                id=entity_data.get('id', str(uuid.uuid4())),
                text=entity_data.get('text', ''),
                entity_type=entity_data.get('entity_type', EntityType.UNKNOWN.value),
                position=position,
                confidence=entity_data.get('confidence', 0.0),
                extraction_method=entity_data.get('extraction_method', ExtractionMethod.REGEX.value),
                subtype=entity_data.get('subtype'),
                category=entity_data.get('category'),
                metadata=entity_data.get('metadata', EntityMetadata()),
                created_at=entity_data.get('created_at', time.time()),
                updated_at=entity_data.get('updated_at')
            )

            luris_entities.append(entity)

        return luris_entities

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "title": "LurisEntityV2 Extraction Response",
            "description": (
                "Guided JSON schema for entity extraction using LurisEntityV2. "
                "Use with vLLM's guided_json feature for guaranteed schema compliance."
            ),
            "example": {
                "entities": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "text": "28 U.S.C. § 1331",
                        "entity_type": "STATUTE_CITATION",
                        "start_pos": 0,
                        "end_pos": 17,
                        "confidence": 0.95,
                        "extraction_method": "ai_enhanced",
                        "subtype": "federal",
                        "category": "statutory",
                        "metadata": {
                            "jurisdiction": "federal",
                            "citation_format": "bluebook_22",
                            "context_before": "jurisdiction under ",
                            "context_after": " for federal questions"
                        },
                        "created_at": 1704067200000
                    },
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440001",
                        "text": "Miranda v. Arizona",
                        "entity_type": "CASE_CITATION",
                        "start_pos": 100,
                        "end_pos": 118,
                        "confidence": 0.98,
                        "extraction_method": "ai_enhanced",
                        "subtype": "supreme_court",
                        "category": "case_law",
                        "metadata": {
                            "court": "Supreme Court",
                            "year": "1966",
                            "landmark": True
                        },
                        "created_at": 1704067200000
                    }
                ],
                "metadata": {
                    "wave_number": 1,
                    "extraction_time": 0.5,
                    "model_name": "qwen3-vl-instruct-384k",
                    "temperature": 0.0,
                    "entity_count": 2,
                    "timestamp": 1704067200.0,
                    "schema_version": "LurisEntityV2"
                }
            }
        }


class LurisRelationshipExtractionResponse(BaseModel):
    """
    Guided JSON schema for Wave 4 relationship extraction.

    This schema extracts relationships between entities identified in Waves 1-3.
    Uses LurisEntityV2 for entity references and provides detailed relationship
    context including evidence text and surrounding context.

    ## Purpose

    Wave 4 focuses on extracting relationships between entities:
    - CITES: Entity A cites Entity B
    - PARTY_TO_CASE: Entity A is party to Case B
    - DECIDED_BY: Case A was decided by Judge B
    - RELIES_ON: Argument A relies on Precedent B
    - And 30+ other relationship types

    ## Usage

    ### With vLLM Guided JSON
    ```python
    schema = LurisRelationshipExtractionResponse.model_json_schema()

    response = client.chat.completions.create(
        model="qwen3-vl-instruct-384k",
        messages=[...],
        extra_body={"guided_json": schema}
    )
    ```

    ### Used In

    - extraction_orchestrator.py:
      - Lines 689-692: Wave 4 relationship extraction
    - Wave System relationship extraction (Wave 4 only)

    ## Fields

    - **relationships**: List of relationship items with detailed context
    - **entities**: Entities referenced in relationships (LurisEntityV2 format)
    - **metadata**: Relationship extraction metadata (wave 4, timing, counts)

    ## Schema Guarantees

    When using guided_json with this schema:
    1. All relationships have source/target entity IDs
    2. Relationship types are valid strings
    3. Confidence scores in [0.0, 1.0] range
    4. Evidence text and context provided
    5. Entity references are LurisEntityV2 compliant
    """

    relationships: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of entity relationships with detailed context. "
            "Each relationship must have: source_entity_id, target_entity_id, "
            "relationship_type, confidence, evidence_text, context_before, context_after"
        )
    )

    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Entities referenced in relationships (LurisEntityV2 format). "
            "Provides full entity information for relationship endpoints. "
            "May include entities from Waves 1-3 that participate in relationships."
        )
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Relationship extraction metadata including: "
            "wave_number (always 4), extraction_time, model_name, "
            "relationship_count, entity_count, etc."
        )
    )

    @field_validator('relationships')
    @classmethod
    def validate_relationships(cls, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate that all relationships have required fields and valid structure.

        Checks:
        1. Required fields present
        2. Confidence scores in [0.0, 1.0]
        3. Evidence text is non-empty
        4. Source and target IDs are non-empty strings

        Raises:
            ValueError: If relationship structure is invalid
        """
        for i, rel in enumerate(relationships):
            # Check required fields
            required_fields = {
                'source_entity_id', 'target_entity_id',
                'relationship_type', 'confidence', 'evidence_text'
            }
            missing_fields = required_fields - set(rel.keys())
            if missing_fields:
                raise ValueError(
                    f"Relationship {i}: Missing required fields: {missing_fields}"
                )

            # Validate confidence
            confidence = rel.get('confidence', 0.0)
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                raise ValueError(
                    f"Relationship {i}: Confidence {confidence} must be in range [0.0, 1.0]"
                )

            # Validate entity IDs are non-empty
            if not rel.get('source_entity_id'):
                raise ValueError(f"Relationship {i}: source_entity_id cannot be empty")
            if not rel.get('target_entity_id'):
                raise ValueError(f"Relationship {i}: target_entity_id cannot be empty")

            # Validate evidence text is non-empty
            if not rel.get('evidence_text', '').strip():
                raise ValueError(f"Relationship {i}: evidence_text cannot be empty")

        return relationships

    @field_validator('entities')
    @classmethod
    def validate_entities(cls, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate that all entities conform to LurisEntityV2 structure.

        Uses same validation as LurisEntityV2ExtractionResponse.validate_entities.
        """
        # Reuse validation logic from LurisEntityV2ExtractionResponse
        return LurisEntityV2ExtractionResponse.validate_entities(entities)

    @model_validator(mode='after')
    def populate_metadata(self):
        """
        Auto-populate metadata fields if not provided.

        Adds:
        - wave_number: Always 4 (relationship extraction wave)
        - relationship_count: Total relationships extracted
        - entity_count: Total entities referenced
        - timestamp: Current extraction time
        - schema_version: LurisEntityV2 identifier
        """
        if not self.metadata:
            self.metadata = {}

        # Wave 4 is always relationship extraction
        self.metadata['wave_number'] = 4

        # Add counts
        if 'relationship_count' not in self.metadata:
            self.metadata['relationship_count'] = len(self.relationships)
        if 'entity_count' not in self.metadata:
            self.metadata['entity_count'] = len(self.entities)

        # Add timestamp
        if 'timestamp' not in self.metadata:
            self.metadata['timestamp'] = time.time()

        # Add schema version
        if 'schema_version' not in self.metadata:
            self.metadata['schema_version'] = 'LurisEntityV2'

        return self

    def to_luris_entities(self) -> List[LurisEntityV2]:
        """
        Convert entity dictionaries to LurisEntityV2 objects.

        Returns:
            List[LurisEntityV2]: Validated entity objects referenced in relationships
        """
        luris_entities = []

        for entity_dict in self.entities:
            # Prepare entity data for LurisEntityV2
            entity_data = entity_dict.copy()

            # Extract metadata and convert to custom_attributes format
            raw_metadata = entity_data.get('metadata', {})
            if isinstance(raw_metadata, dict):
                entity_metadata = EntityMetadata(custom_attributes=raw_metadata)
                entity_data['metadata'] = entity_metadata

            # Create Position object
            position = Position(
                start_pos=entity_data.get('start_pos', 0),
                end_pos=entity_data.get('end_pos', 0)
            )

            # Create LurisEntityV2 directly
            entity = LurisEntityV2(
                id=entity_data.get('id', str(uuid.uuid4())),
                text=entity_data.get('text', ''),
                entity_type=entity_data.get('entity_type', EntityType.UNKNOWN.value),
                position=position,
                confidence=entity_data.get('confidence', 0.0),
                extraction_method=entity_data.get('extraction_method', ExtractionMethod.REGEX.value),
                subtype=entity_data.get('subtype'),
                category=entity_data.get('category'),
                metadata=entity_data.get('metadata', EntityMetadata()),
                created_at=entity_data.get('created_at', time.time()),
                updated_at=entity_data.get('updated_at')
            )

            luris_entities.append(entity)

        return luris_entities

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "title": "LurisEntityV2 Relationship Extraction Response",
            "description": (
                "Guided JSON schema for Wave 4 relationship extraction. "
                "Use with vLLM's guided_json feature for guaranteed schema compliance."
            ),
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
                            "citation_type": "direct",
                            "page_number": 12,
                            "strength": "strong"
                        }
                    },
                    {
                        "source_entity_id": "entity_67",
                        "target_entity_id": "entity_89",
                        "relationship_type": "DECIDED_BY",
                        "confidence": 0.98,
                        "evidence_text": "Justice Rehnquist delivered the opinion of the Court",
                        "context_before": "In a 7-2 decision,",
                        "context_after": "joining the majority opinion",
                        "metadata": {
                            "role": "majority_author",
                            "vote": "7-2"
                        }
                    }
                ],
                "entities": [
                    {
                        "id": "entity_12",
                        "text": "Roe v. Wade",
                        "entity_type": "CASE_CITATION",
                        "start_pos": 50,
                        "end_pos": 61,
                        "confidence": 0.98,
                        "extraction_method": "ai_enhanced",
                        "metadata": {"court": "Supreme Court", "year": "1973"},
                        "created_at": 1704067200000
                    },
                    {
                        "id": "entity_45",
                        "text": "Griswold v. Connecticut",
                        "entity_type": "CASE_CITATION",
                        "start_pos": 100,
                        "end_pos": 123,
                        "confidence": 0.97,
                        "extraction_method": "ai_enhanced",
                        "metadata": {"court": "Supreme Court", "year": "1965"},
                        "created_at": 1704067200000
                    }
                ],
                "metadata": {
                    "wave_number": 4,
                    "extraction_time": 1.2,
                    "model_name": "qwen3-vl-instruct-384k",
                    "temperature": 0.0,
                    "relationship_count": 2,
                    "entity_count": 2,
                    "timestamp": 1704067200.0,
                    "schema_version": "LurisEntityV2"
                }
            }
        }


# Export public API
__all__ = [
    'LurisEntityV2ExtractionResponse',
    'LurisRelationshipExtractionResponse',
]
