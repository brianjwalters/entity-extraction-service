"""
Conversion Layer for Luris Entity Schema

This module provides bidirectional conversion between different entity formats:
- Legacy ExtractedEntity objects
- Dictionary representations 
- LurisEntityV2 unified schema

Ensures backward compatibility while migrating to unified schema.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union, Type
from dataclasses import asdict

from .luris_entity_schema import LurisEntityV2, ExtractionResultV2, Position, EntityMetadata
from .schema_validator import get_global_validator, ValidationResult

# CLAUDE.md Compliant: Absolute import for legacy types (optional dependency)
try:
    from src.core.context.context_window_extractor import ExtractedEntity
except ImportError:
    # Optional legacy type - not an import fallback
    ExtractedEntity = None

logger = logging.getLogger(__name__)


class EntityConverter:
    """Handles conversion between different entity formats."""
    
    def __init__(self, validate_conversions: bool = True):
        """
        Initialize entity converter.
        
        Args:
            validate_conversions: If True, validates converted entities
        """
        self.validate_conversions = validate_conversions
        self.validator = get_global_validator()
        
        # Conversion statistics
        self.conversion_count = 0
        self.validation_failures = 0
        self.conversion_time = 0.0
    
    def to_luris_v2(self, entity: Any) -> LurisEntityV2:
        """
        Convert any entity format to LurisEntityV2.
        
        Args:
            entity: Entity in any supported format
            
        Returns:
            LurisEntityV2 object
        """
        start_time = time.time()
        
        try:
            if isinstance(entity, LurisEntityV2):
                # Already in correct format
                result = entity
            elif isinstance(entity, dict):
                result = self._dict_to_luris_v2(entity)
            elif ExtractedEntity and isinstance(entity, ExtractedEntity):
                result = self._extracted_entity_to_luris_v2(entity)
            elif hasattr(entity, '__dict__'):
                # Generic object with attributes
                result = self._object_to_luris_v2(entity)
            else:
                # Fallback: treat as text
                result = LurisEntityV2(text=str(entity) if entity else "")
            
            # Validate if enabled
            if self.validate_conversions:
                validation_result = self.validator.validate_entity(result)
                if not validation_result.is_valid:
                    self.validation_failures += 1
                    logger.warning(f"Converted entity failed validation: {validation_result.errors}")
            
            self.conversion_count += 1
            self.conversion_time += (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to convert entity to LurisEntityV2: {e}")
            # Return minimal valid entity
            return LurisEntityV2(
                text=str(entity) if entity else "CONVERSION_FAILED",
                entity_type="UNKNOWN"
            )
    
    def _dict_to_luris_v2(self, data: Dict[str, Any]) -> LurisEntityV2:
        """Convert dictionary to LurisEntityV2."""
        # Handle position information
        if 'position' in data and isinstance(data['position'], dict):
            position = Position(
                start_pos=data['position'].get('start_pos', 0),
                end_pos=data['position'].get('end_pos', 0)
            )
        else:
            # Handle flat position fields
            start_pos = data.get('start_pos', data.get('start_position', 0))
            end_pos = data.get('end_pos', data.get('end_position', 0))
            position = Position(start_pos=start_pos, end_pos=end_pos)
        
        # Handle entity type field naming
        entity_type = (
            data.get('entity_type') or 
            data.get('type') or 
            'UNKNOWN'
        )
        
        # Handle metadata
        metadata_data = data.get('metadata', {})
        if isinstance(metadata_data, dict):
            metadata = EntityMetadata(**metadata_data)
        else:
            metadata = EntityMetadata()
        
        return LurisEntityV2(
            id=data.get('id'),
            text=data.get('text', ''),
            entity_type=entity_type,
            position=position,
            confidence=float(data.get('confidence', 0.0)),
            extraction_method=data.get('extraction_method', 'unknown'),
            subtype=data.get('subtype'),
            category=data.get('category'),
            metadata=metadata,
            created_at=data.get('created_at', time.time()),
            updated_at=data.get('updated_at')
        )
    
    def _extracted_entity_to_luris_v2(self, entity: 'ExtractedEntity') -> LurisEntityV2:
        """Convert ExtractedEntity to LurisEntityV2."""
        # Get entity type (handle both 'type' and 'entity_type')
        entity_type = getattr(entity, 'entity_type', None) or getattr(entity, 'type', 'UNKNOWN')
        
        # Create metadata from existing metadata
        metadata = EntityMetadata()
        if hasattr(entity, 'metadata') and entity.metadata:
            if isinstance(entity.metadata, dict):
                metadata.custom_attributes = entity.metadata.copy()
        
        return LurisEntityV2(
            text=getattr(entity, 'text', ''),
            entity_type=entity_type,
            position=Position(
                start_pos=getattr(entity, 'start_pos', 0),
                end_pos=getattr(entity, 'end_pos', 0)
            ),
            confidence=float(getattr(entity, 'confidence', 0.0)),
            extraction_method=getattr(entity, 'extraction_method', 'legacy'),
            metadata=metadata
        )
    
    def _object_to_luris_v2(self, obj: Any) -> LurisEntityV2:
        """Convert generic object with attributes to LurisEntityV2."""
        # Extract common attributes
        text = getattr(obj, 'text', getattr(obj, 'value', str(obj)))
        entity_type = (
            getattr(obj, 'entity_type', None) or
            getattr(obj, 'type', None) or
            getattr(obj, 'label', 'UNKNOWN')
        )
        
        # Position information
        start_pos = getattr(obj, 'start_pos', getattr(obj, 'start', 0))
        end_pos = getattr(obj, 'end_pos', getattr(obj, 'end', 0))
        
        # Confidence
        confidence = getattr(obj, 'confidence', getattr(obj, 'score', 0.0))
        
        return LurisEntityV2(
            text=text,
            entity_type=entity_type,
            position=Position(start_pos=start_pos, end_pos=end_pos),
            confidence=float(confidence),
            extraction_method=getattr(obj, 'extraction_method', 'unknown')
        )
    
    def to_dict(self, entity: Union[LurisEntityV2, Any]) -> Dict[str, Any]:
        """
        Convert entity to dictionary format.
        
        Args:
            entity: Entity in any format
            
        Returns:
            Dictionary representation
        """
        if isinstance(entity, LurisEntityV2):
            return entity.to_dict()
        elif isinstance(entity, dict):
            # Standardize dictionary format
            luris_entity = self.to_luris_v2(entity)
            return luris_entity.to_dict()
        else:
            # Convert through LurisEntityV2
            luris_entity = self.to_luris_v2(entity)
            return luris_entity.to_dict()
    
    def to_legacy_dict(self, entity: Union[LurisEntityV2, Any]) -> Dict[str, Any]:
        """
        Convert entity to legacy dictionary format for backward compatibility.
        
        Args:
            entity: Entity in any format
            
        Returns:
            Legacy dictionary format
        """
        if isinstance(entity, LurisEntityV2):
            return entity.to_legacy_dict()
        else:
            # Convert through LurisEntityV2
            luris_entity = self.to_luris_v2(entity)
            return luris_entity.to_legacy_dict()
    
    def to_extracted_entity(self, entity: Union[LurisEntityV2, Dict[str, Any]]) -> Optional['ExtractedEntity']:
        """
        Convert to ExtractedEntity object (if available).
        
        Args:
            entity: Entity in LurisEntityV2 or dict format
            
        Returns:
            ExtractedEntity object or None if ExtractedEntity not available
        """
        if ExtractedEntity is None:
            logger.warning("ExtractedEntity class not available for conversion")
            return None
        
        if isinstance(entity, LurisEntityV2):
            return ExtractedEntity(
                text=entity.text,
                entity_type=entity.entity_type,
                start_pos=entity.position.start_pos,
                end_pos=entity.position.end_pos,
                confidence=entity.confidence,
                extraction_method=entity.extraction_method,
                metadata=entity.metadata.custom_attributes
            )
        elif isinstance(entity, dict):
            # Convert dict to ExtractedEntity
            return ExtractedEntity(
                text=entity.get('text', ''),
                entity_type=entity.get('entity_type', entity.get('type', 'UNKNOWN')),
                start_pos=entity.get('start_pos', 0),
                end_pos=entity.get('end_pos', 0),
                confidence=entity.get('confidence', 0.0),
                extraction_method=entity.get('extraction_method', 'unknown'),
                metadata=entity.get('metadata', {})
            )
        else:
            logger.warning(f"Cannot convert {type(entity)} to ExtractedEntity")
            return None
    
    def convert_batch(self, entities: List[Any], target_format: str = 'luris_v2') -> List[Any]:
        """
        Convert a batch of entities to specified format.
        
        Args:
            entities: List of entities in any format
            target_format: Target format ('luris_v2', 'dict', 'legacy_dict', 'extracted_entity')
            
        Returns:
            List of entities in target format
        """
        if target_format == 'luris_v2':
            return [self.to_luris_v2(entity) for entity in entities]
        elif target_format == 'dict':
            return [self.to_dict(entity) for entity in entities]
        elif target_format == 'legacy_dict':
            return [self.to_legacy_dict(entity) for entity in entities]
        elif target_format == 'extracted_entity':
            results = []
            for entity in entities:
                converted = self.to_extracted_entity(entity)
                if converted is not None:
                    results.append(converted)
            return results
        else:
            raise ValueError(f"Unknown target format: {target_format}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        avg_conversion_time = (
            self.conversion_time / self.conversion_count 
            if self.conversion_count > 0 else 0.0
        )
        
        validation_failure_rate = (
            self.validation_failures / self.conversion_count 
            if self.conversion_count > 0 else 0.0
        )
        
        return {
            "total_conversions": self.conversion_count,
            "validation_failures": self.validation_failures,
            "validation_failure_rate": validation_failure_rate,
            "average_conversion_time_ms": avg_conversion_time,
            "total_conversion_time_ms": self.conversion_time
        }


class ResultConverter:
    """Handles conversion between different extraction result formats."""
    
    def __init__(self, entity_converter: Optional[EntityConverter] = None):
        """
        Initialize result converter.
        
        Args:
            entity_converter: EntityConverter instance to use
        """
        self.entity_converter = entity_converter or EntityConverter()
        self.conversion_count = 0
        self.conversion_time = 0.0
    
    def to_extraction_result_v2(self, result: Any) -> ExtractionResultV2:
        """
        Convert any result format to ExtractionResultV2.
        
        Args:
            result: Result in any supported format
            
        Returns:
            ExtractionResultV2 object
        """
        start_time = time.time()
        
        try:
            if isinstance(result, ExtractionResultV2):
                # Already in correct format
                converted_result = result
            elif isinstance(result, dict):
                converted_result = self._dict_to_extraction_result_v2(result)
            else:
                # Fallback: create minimal result
                converted_result = ExtractionResultV2(
                    entities=[],
                    success=False,
                    errors=[f"Unknown result format: {type(result)}"]
                )
            
            self.conversion_count += 1
            self.conversion_time += (time.time() - start_time) * 1000
            
            return converted_result
            
        except Exception as e:
            logger.error(f"Failed to convert result to ExtractionResultV2: {e}")
            return ExtractionResultV2(
                entities=[],
                success=False,
                errors=[f"Conversion failed: {str(e)}"]
            )
    
    def _dict_to_extraction_result_v2(self, data: Dict[str, Any]) -> ExtractionResultV2:
        """Convert dictionary to ExtractionResultV2."""
        # Convert entities
        entities = []
        if 'entities' in data:
            entities = [
                self.entity_converter.to_luris_v2(entity) 
                for entity in data['entities']
            ]
        
        # Convert citations
        citations = []
        if 'citations' in data:
            citations = [
                self.entity_converter.to_luris_v2(citation) 
                for citation in data['citations']
            ]
        
        # Extract metadata
        extraction_metadata = data.get('extraction_metadata', {})
        quality_metrics = data.get('quality_metrics', {})
        
        return ExtractionResultV2(
            extraction_id=data.get('extraction_id', ''),
            document_id=data.get('document_id', ''),
            strategy_used=data.get('strategy_used', 'unknown'),
            entities=entities,
            citations=citations,
            relationships=data.get('relationships', []),
            processing_time_ms=data.get('processing_time_ms', 0.0),
            extraction_time=data.get('extraction_time', time.time()),
            extraction_metadata=extraction_metadata,
            quality_metrics=quality_metrics,
            success=data.get('success', True),
            warnings=data.get('warnings', []),
            errors=data.get('errors', [])
        )
    
    def to_legacy_dict(self, result: Union[ExtractionResultV2, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert result to legacy dictionary format.
        
        Args:
            result: Result in ExtractionResultV2 or dict format
            
        Returns:
            Legacy dictionary format
        """
        if isinstance(result, ExtractionResultV2):
            return result.to_legacy_dict()
        elif isinstance(result, dict):
            # Already a dict, ensure it has legacy format
            extraction_result = self.to_extraction_result_v2(result)
            return extraction_result.to_legacy_dict()
        else:
            # Fallback
            extraction_result = self.to_extraction_result_v2(result)
            return extraction_result.to_legacy_dict()
    
    def to_dict(self, result: Union[ExtractionResultV2, Any]) -> Dict[str, Any]:
        """
        Convert result to standard dictionary format.
        
        Args:
            result: Result in any format
            
        Returns:
            Dictionary representation
        """
        if isinstance(result, ExtractionResultV2):
            return result.to_dict()
        else:
            extraction_result = self.to_extraction_result_v2(result)
            return extraction_result.to_dict()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        avg_conversion_time = (
            self.conversion_time / self.conversion_count 
            if self.conversion_count > 0 else 0.0
        )
        
        return {
            "total_conversions": self.conversion_count,
            "average_conversion_time_ms": avg_conversion_time,
            "total_conversion_time_ms": self.conversion_time,
            "entity_converter_stats": self.entity_converter.get_stats()
        }


# Global converter instances
_global_entity_converter: Optional[EntityConverter] = None
_global_result_converter: Optional[ResultConverter] = None


def get_entity_converter() -> EntityConverter:
    """Get the global entity converter instance."""
    global _global_entity_converter
    if _global_entity_converter is None:
        _global_entity_converter = EntityConverter(validate_conversions=True)
    return _global_entity_converter


def get_result_converter() -> ResultConverter:
    """Get the global result converter instance."""
    global _global_result_converter
    if _global_result_converter is None:
        _global_result_converter = ResultConverter(get_entity_converter())
    return _global_result_converter


# Convenience functions
def convert_to_luris_v2(entity: Any) -> LurisEntityV2:
    """Convert any entity to LurisEntityV2 format."""
    return get_entity_converter().to_luris_v2(entity)


def convert_to_dict(entity: Any) -> Dict[str, Any]:
    """Convert any entity to dictionary format."""
    return get_entity_converter().to_dict(entity)


def convert_to_legacy_dict(entity: Any) -> Dict[str, Any]:
    """Convert any entity to legacy dictionary format."""
    return get_entity_converter().to_legacy_dict(entity)


def convert_result_to_v2(result: Any) -> ExtractionResultV2:
    """Convert any result to ExtractionResultV2 format."""
    return get_result_converter().to_extraction_result_v2(result)


def convert_result_to_dict(result: Any) -> Dict[str, Any]:
    """Convert any result to dictionary format."""
    return get_result_converter().to_dict(result)


def convert_result_to_legacy_dict(result: Any) -> Dict[str, Any]:
    """Convert any result to legacy dictionary format."""
    return get_result_converter().to_legacy_dict(result)


def standardize_entities(entities: List[Any]) -> List[LurisEntityV2]:
    """Standardize a list of entities to LurisEntityV2 format."""
    return get_entity_converter().convert_batch(entities, 'luris_v2')


def standardize_result(result: Any) -> ExtractionResultV2:
    """Standardize any result to ExtractionResultV2 format."""
    return get_result_converter().to_extraction_result_v2(result)


class ConversionMiddleware:
    """Middleware to automatically convert between entity formats."""
    
    def __init__(self, input_format: str = 'auto', output_format: str = 'luris_v2'):
        """
        Initialize conversion middleware.
        
        Args:
            input_format: Expected input format ('auto', 'dict', 'extracted_entity', etc.)
            output_format: Desired output format ('luris_v2', 'dict', 'legacy_dict')
        """
        self.input_format = input_format
        self.output_format = output_format
        self.entity_converter = get_entity_converter()
        self.result_converter = get_result_converter()
    
    def process_entities(self, entities: List[Any]) -> List[Any]:
        """Process entities according to configured formats."""
        return self.entity_converter.convert_batch(entities, self.output_format)
    
    def process_result(self, result: Any) -> Any:
        """Process extraction result according to configured formats."""
        if self.output_format == 'luris_v2':
            return self.result_converter.to_extraction_result_v2(result)
        elif self.output_format == 'dict':
            return self.result_converter.to_dict(result)
        elif self.output_format == 'legacy_dict':
            return self.result_converter.to_legacy_dict(result)
        else:
            return result