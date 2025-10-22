"""
Luris Entity Schema Package

This package provides unified schema, validation, and conversion capabilities
for all entity extraction results across multipass and unified strategies.
"""

from .luris_entity_schema import (
    LurisEntityV2,
    ExtractionResultV2,
    Position,
    EntityMetadata,
    EntityType,
    ExtractionMethod,
    ConfidenceLevel,
    LURIS_ENTITY_V2_SCHEMA,
    EXTRACTION_RESULT_V2_SCHEMA
)

from .schema_validator import (
    LurisSchemaValidator,
    ValidationResult,
    SchemaEnforcer,
    get_global_validator,
    validate_entity_schema,
    validate_result_schema,
    schema_validation_middleware
)

from .conversion_layer import (
    EntityConverter,
    ResultConverter,
    ConversionMiddleware,
    get_entity_converter,
    get_result_converter,
    convert_to_luris_v2,
    convert_to_dict,
    convert_to_legacy_dict,
    convert_result_to_v2,
    convert_result_to_dict,
    convert_result_to_legacy_dict,
    standardize_entities,
    standardize_result
)

__all__ = [
    # Schema classes
    'LurisEntityV2',
    'ExtractionResultV2', 
    'Position',
    'EntityMetadata',
    'EntityType',
    'ExtractionMethod',
    'ConfidenceLevel',
    
    # Schema definitions
    'LURIS_ENTITY_V2_SCHEMA',
    'EXTRACTION_RESULT_V2_SCHEMA',
    
    # Validation
    'LurisSchemaValidator',
    'ValidationResult',
    'SchemaEnforcer',
    'get_global_validator',
    'validate_entity_schema',
    'validate_result_schema',
    'schema_validation_middleware',
    
    # Conversion
    'EntityConverter',
    'ResultConverter',
    'ConversionMiddleware',
    'get_entity_converter',
    'get_result_converter',
    'convert_to_luris_v2',
    'convert_to_dict',
    'convert_to_legacy_dict',
    'convert_result_to_v2',
    'convert_result_to_dict',
    'convert_result_to_legacy_dict',
    'standardize_entities',
    'standardize_result'
]

__version__ = "2.0.0"