"""
Schema Validation Framework for Luris Entity Extraction

This module provides high-performance schema validation with caching
to ensure consistent JSON output across all extraction strategies.
"""

import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from functools import lru_cache, wraps
from dataclasses import dataclass
import jsonschema
from jsonschema import validate, ValidationError, FormatChecker

from .luris_entity_schema import (
    LurisEntityV2, 
    ExtractionResultV2,
    LURIS_ENTITY_V2_SCHEMA,
    EXTRACTION_RESULT_V2_SCHEMA
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of schema validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validation_time_ms: float
    schema_version: str = "v2"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "validation_time_ms": self.validation_time_ms,
            "schema_version": self.schema_version
        }


class SchemaValidationCache:
    """High-performance cache for schema validation results."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[ValidationResult, float]] = {}
        self.access_times: Dict[str, float] = {}
        
    def _generate_key(self, data: Any) -> str:
        """Generate cache key from data."""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            normalized = json.dumps(data, sort_keys=True)
        else:
            normalized = str(data)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, data: Any) -> Optional[ValidationResult]:
        """Get cached validation result."""
        key = self._generate_key(data)
        current_time = time.time()
        
        if key in self.cache:
            result, cache_time = self.cache[key]
            # Check TTL
            if current_time - cache_time < self.ttl_seconds:
                self.access_times[key] = current_time
                return result
            else:
                # Expired, remove
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        
        return None
    
    def put(self, data: Any, result: ValidationResult):
        """Cache validation result."""
        key = self._generate_key(data)
        current_time = time.time()
        
        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            # Find oldest accessed key
            oldest_key = min(self.access_times.keys(), 
                           key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = (result, current_time)
        self.access_times[key] = current_time
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
        self.access_times.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(1 for _, cache_time in self.cache.values() 
                           if current_time - cache_time < self.ttl_seconds)
        
        return {
            "size": len(self.cache),
            "valid_entries": valid_entries,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


class LurisSchemaValidator:
    """High-performance schema validator for Luris entities and results."""
    
    def __init__(self, enable_cache: bool = True, cache_size: int = 1000):
        self.enable_cache = enable_cache
        self.cache = SchemaValidationCache(max_size=cache_size) if enable_cache else None
        
        # Pre-compile schemas for performance
        self.entity_schema = LURIS_ENTITY_V2_SCHEMA
        self.result_schema = EXTRACTION_RESULT_V2_SCHEMA
        
        # Create validators with format checking
        self.format_checker = FormatChecker()
        self.entity_validator = jsonschema.Draft7Validator(
            self.entity_schema,
            format_checker=self.format_checker
        )
        self.result_validator = jsonschema.Draft7Validator(
            self.result_schema,
            format_checker=self.format_checker
        )
        
        # Performance counters
        self.validation_count = 0
        self.cache_hits = 0
        self.total_validation_time = 0.0
        
        logger.info(f"Schema validator initialized with caching: {enable_cache}")
    
    def validate_entity(self, entity_data: Union[Dict[str, Any], LurisEntityV2]) -> ValidationResult:
        """
        Validate a single entity against the LurisEntityV2 schema.
        
        Args:
            entity_data: Entity data as dict or LurisEntityV2 object
            
        Returns:
            ValidationResult with validation status and details
        """
        start_time = time.time()
        
        # Convert to dict if needed
        if isinstance(entity_data, LurisEntityV2):
            data = entity_data.to_dict()
        else:
            data = entity_data
        
        # Check cache first
        if self.enable_cache and self.cache:
            cached_result = self.cache.get(data)
            if cached_result is not None:
                self.cache_hits += 1
                return cached_result
        
        # Perform validation
        errors = []
        warnings = []
        
        try:
            # JSONSchema validation
            self.entity_validator.validate(data)
            
            # Additional business logic validation
            if isinstance(entity_data, LurisEntityV2):
                entity_issues = entity_data.validate()
                if entity_issues:
                    warnings.extend(entity_issues)
            else:
                # Validate dictionary format
                if data.get('start_pos', 0) > data.get('end_pos', 0):
                    warnings.append("End position is before start position")
                
                confidence = data.get('confidence', 0.0)
                if not (0.0 <= confidence <= 1.0):
                    warnings.append(f"Confidence {confidence} is not in range [0.0, 1.0]")
            
            is_valid = len(errors) == 0
            
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            is_valid = False
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            is_valid = False
        
        # Create result
        validation_time = (time.time() - start_time) * 1000
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validation_time_ms=validation_time
        )
        
        # Cache result
        if self.enable_cache and self.cache:
            self.cache.put(data, result)
        
        # Update stats
        self.validation_count += 1
        self.total_validation_time += validation_time
        
        return result
    
    def validate_extraction_result(self, result_data: Union[Dict[str, Any], ExtractionResultV2]) -> ValidationResult:
        """
        Validate extraction result against the ExtractionResultV2 schema.
        
        Args:
            result_data: Result data as dict or ExtractionResultV2 object
            
        Returns:
            ValidationResult with validation status and details
        """
        start_time = time.time()
        
        # Convert to dict if needed
        if isinstance(result_data, ExtractionResultV2):
            data = result_data.to_dict()
        else:
            data = result_data
        
        # Check cache first
        if self.enable_cache and self.cache:
            cached_result = self.cache.get(data)
            if cached_result is not None:
                self.cache_hits += 1
                return cached_result
        
        # Perform validation
        errors = []
        warnings = []
        
        try:
            # JSONSchema validation
            self.result_validator.validate(data)
            
            # Validate individual entities
            entities = data.get('entities', [])
            for i, entity in enumerate(entities):
                entity_result = self.validate_entity(entity)
                if not entity_result.is_valid:
                    errors.extend([f"Entity {i}: {error}" for error in entity_result.errors])
                if entity_result.warnings:
                    warnings.extend([f"Entity {i}: {warning}" for warning in entity_result.warnings])
            
            # Validate citations
            citations = data.get('citations', [])
            for i, citation in enumerate(citations):
                citation_result = self.validate_entity(citation)
                if not citation_result.is_valid:
                    errors.extend([f"Citation {i}: {error}" for error in citation_result.errors])
                if citation_result.warnings:
                    warnings.extend([f"Citation {i}: {warning}" for warning in citation_result.warnings])
            
            # Business logic validation
            if data.get('total_entities', 0) != len(entities):
                warnings.append(f"Total entities count mismatch: declared {data.get('total_entities')}, actual {len(entities)}")
            
            is_valid = len(errors) == 0
            
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            is_valid = False
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            is_valid = False
        
        # Create result
        validation_time = (time.time() - start_time) * 1000
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validation_time_ms=validation_time
        )
        
        # Cache result
        if self.enable_cache and self.cache:
            self.cache.put(data, result)
        
        # Update stats
        self.validation_count += 1
        self.total_validation_time += validation_time
        
        return result
    
    def validate_batch(self, entities: List[Union[Dict[str, Any], LurisEntityV2]]) -> List[ValidationResult]:
        """
        Validate a batch of entities efficiently.
        
        Args:
            entities: List of entity data
            
        Returns:
            List of ValidationResult objects
        """
        return [self.validate_entity(entity) for entity in entities]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        cache_stats = self.cache.stats() if self.cache else {}
        
        avg_validation_time = (
            self.total_validation_time / self.validation_count 
            if self.validation_count > 0 else 0.0
        )
        
        cache_hit_rate = (
            self.cache_hits / self.validation_count 
            if self.validation_count > 0 else 0.0
        )
        
        return {
            "total_validations": self.validation_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "average_validation_time_ms": avg_validation_time,
            "total_validation_time_ms": self.total_validation_time,
            "cache_enabled": self.enable_cache,
            "cache_stats": cache_stats
        }
    
    def clear_cache(self):
        """Clear validation cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Validation cache cleared")


# Global validator instance
_global_validator: Optional[LurisSchemaValidator] = None


def get_global_validator() -> LurisSchemaValidator:
    """Get the global schema validator instance."""
    global _global_validator
    if _global_validator is None:
        _global_validator = LurisSchemaValidator(enable_cache=True, cache_size=1000)
    return _global_validator


def validate_entity_schema(entity_data: Union[Dict[str, Any], LurisEntityV2]) -> ValidationResult:
    """Convenience function to validate entity schema."""
    return get_global_validator().validate_entity(entity_data)


def validate_result_schema(result_data: Union[Dict[str, Any], ExtractionResultV2]) -> ValidationResult:
    """Convenience function to validate extraction result schema."""
    return get_global_validator().validate_extraction_result(result_data)


def schema_validation_middleware(func):
    """
    Decorator to add automatic schema validation to extraction functions.
    
    Usage:
        @schema_validation_middleware
        def extract_entities(document_text: str) -> ExtractionResultV2:
            # ... extraction logic
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Execute the function
        result = func(*args, **kwargs)
        
        # Validate the result
        if isinstance(result, (dict, ExtractionResultV2)):
            validation_result = validate_result_schema(result)
            
            if not validation_result.is_valid:
                logger.error(f"Function {func.__name__} returned invalid result: {validation_result.errors}")
                # Could raise exception or return error result based on configuration
            
            if validation_result.warnings:
                logger.warning(f"Function {func.__name__} result has warnings: {validation_result.warnings}")
        
        return result
    
    return wrapper


class SchemaEnforcer:
    """Enforces schema compliance across the extraction pipeline."""
    
    def __init__(self, strict_mode: bool = False, auto_fix: bool = True):
        """
        Initialize schema enforcer.
        
        Args:
            strict_mode: If True, raises exceptions on validation errors
            auto_fix: If True, attempts to fix common validation issues
        """
        self.strict_mode = strict_mode
        self.auto_fix = auto_fix
        self.validator = get_global_validator()
        
    def enforce_entity_schema(self, entity_data: Any) -> LurisEntityV2:
        """
        Enforce entity schema compliance, with optional auto-fixing.
        
        Args:
            entity_data: Entity data in any format
            
        Returns:
            LurisEntityV2 object that complies with schema
            
        Raises:
            ValueError: If strict_mode is True and validation fails
        """
        # Convert to LurisEntityV2
        if isinstance(entity_data, LurisEntityV2):
            entity = entity_data
        else:
            entity = LurisEntityV2.from_legacy_entity(entity_data)
        
        # Validate
        validation_result = self.validator.validate_entity(entity)
        
        if not validation_result.is_valid:
            if self.auto_fix:
                # Attempt to fix common issues
                entity = self._auto_fix_entity(entity, validation_result.errors)
                
                # Re-validate after fixes
                validation_result = self.validator.validate_entity(entity)
            
            if not validation_result.is_valid and self.strict_mode:
                raise ValueError(f"Entity validation failed: {validation_result.errors}")
        
        return entity
    
    def _auto_fix_entity(self, entity: LurisEntityV2, errors: List[str]) -> LurisEntityV2:
        """Attempt to automatically fix common entity validation issues."""
        # Fix confidence range
        if entity.confidence < 0.0:
            entity.confidence = 0.0
        elif entity.confidence > 1.0:
            entity.confidence = 1.0
        
        # Fix position issues
        if entity.position.start_pos < 0:
            entity.position.start_pos = 0
        if entity.position.end_pos < entity.position.start_pos:
            entity.position.end_pos = entity.position.start_pos
        
        # Fix empty text
        if not entity.text:
            entity.text = "UNKNOWN"
        
        return entity
    
    def enforce_result_schema(self, result_data: Any) -> ExtractionResultV2:
        """
        Enforce extraction result schema compliance.
        
        Args:
            result_data: Result data in any format
            
        Returns:
            ExtractionResultV2 object that complies with schema
        """
        if isinstance(result_data, ExtractionResultV2):
            result = result_data
        else:
            # Convert from legacy format
            result = self._convert_legacy_result(result_data)
        
        # Enforce entity schemas
        result.entities = [
            self.enforce_entity_schema(entity) 
            for entity in result.entities
        ]
        
        result.citations = [
            self.enforce_entity_schema(citation) 
            for citation in result.citations
        ]
        
        # Recalculate derived fields
        result.__post_init__()
        
        return result
    
    def _convert_legacy_result(self, result_data: Any) -> ExtractionResultV2:
        """Convert legacy result format to ExtractionResultV2."""
        if isinstance(result_data, dict):
            entities = []
            if 'entities' in result_data:
                entities = [
                    LurisEntityV2.from_legacy_entity(e) 
                    for e in result_data['entities']
                ]
            
            citations = []
            if 'citations' in result_data:
                citations = [
                    LurisEntityV2.from_legacy_entity(c) 
                    for c in result_data['citations']
                ]
            
            return ExtractionResultV2(
                extraction_id=result_data.get('extraction_id', ''),
                document_id=result_data.get('document_id', ''),
                strategy_used=result_data.get('strategy_used', 'unknown'),
                entities=entities,
                citations=citations,
                relationships=result_data.get('relationships', []),
                processing_time_ms=result_data.get('processing_time_ms', 0.0),
                extraction_metadata=result_data.get('extraction_metadata', {}),
                quality_metrics=result_data.get('quality_metrics', {}),
                success=result_data.get('success', True)
            )
        else:
            # Fallback for unknown formats
            return ExtractionResultV2(
                entities=[],
                success=False,
                errors=[f"Unknown result format: {type(result_data)}"]
            )