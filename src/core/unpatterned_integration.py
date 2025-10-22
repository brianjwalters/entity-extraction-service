"""
Unpatterned Entity Integration

This module integrates the unpatterned entity handler with the existing extraction pipeline,
adding it as an additional pass in the multi-pass extraction system.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Internal imports
from .unpatterned import (
    UnpatternedEntityHandler,
    UnpatternedEntity,
    ProcessingMode
)
from .multi_pass_extractor import EntityMatch, PassResult, ExtractionPass
from .model_management.dynamic_model_loader import DynamicModelLoader

logger = logging.getLogger(__name__)


class UnpatternedExtractionPass(Enum):
    """Additional extraction pass for unpatterned entities."""
    UNPATTERNED = 8  # New pass for unpatterned entities


@dataclass
class UnpatternedPassResult:
    """Results from unpatterned entity extraction pass."""
    pass_type: str = "unpatterned"
    entities: List[EntityMatch] = None
    processing_time_ms: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
        if self.metadata is None:
            self.metadata = {}


class UnpatternedExtractor:
    """
    Integrates unpatterned entity extraction with the existing pipeline.
    
    This class acts as a bridge between the existing multi-pass extraction system
    and the new unpatterned entity handler.
    """
    
    def __init__(self,
                 cales_config_path: str = "/srv/luris/be/entity-extraction-service/config/archive/cales_config.yaml",
                 model_loader: Optional[DynamicModelLoader] = None):
        """
        Initialize the unpatterned extractor.
        
        Args:
            cales_config_path: Path to CALES configuration file
            model_loader: Optional pre-initialized model loader
        """
        self.cales_config_path = cales_config_path
        self.model_loader = model_loader or DynamicModelLoader()
        
        # Initialize handler (lazy loading)
        self._handler = None
        
        # Statistics
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "avg_processing_time_ms": 0.0,
            "total_entities_found": 0
        }
        
        logger.info("UnpatternedExtractor initialized")
    
    async def _ensure_handler_loaded(self):
        """Lazy load the unpatterned entity handler"""
        if self._handler is None:
            try:
                self._handler = UnpatternedEntityHandler(
                    cales_config_path=self.cales_config_path,
                    model_loader=self.model_loader
                )
                logger.info("UnpatternedEntityHandler loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load UnpatternedEntityHandler: {e}")
                raise
    
    async def extract_unpatterned_entities(self, 
                                          text: str,
                                          mode: ProcessingMode = ProcessingMode.ADAPTIVE,
                                          target_types: Optional[List[str]] = None,
                                          chunk_info: Optional[Dict[str, Any]] = None) -> UnpatternedPassResult:
        """
        Extract unpatterned entities and return in the expected format.
        
        Args:
            text: Input text to process
            mode: Processing mode (fast, comprehensive, adaptive)
            target_types: Specific entity types to target (optional)
            chunk_info: Information about document chunks for position adjustment
            
        Returns:
            UnpatternedPassResult containing extracted entities
        """
        start_time = time.time()
        
        try:
            # Ensure handler is loaded
            await self._ensure_handler_loaded()
            
            # Extract entities
            unpatterned_entities = await self._handler.extract_entities(
                text=text,
                mode=mode,
                target_types=target_types
            )
            
            # Convert to EntityMatch format
            entity_matches = []
            
            for entity in unpatterned_entities:
                # Adjust positions if chunk info is provided
                adjusted_start = entity.start_position
                adjusted_end = entity.end_position
                
                if chunk_info:
                    chunk_offset = chunk_info.get('start_position', 0)
                    adjusted_start += chunk_offset
                    adjusted_end += chunk_offset
                
                entity_match = EntityMatch(
                    entity_type=entity.entity_type,
                    text=entity.text,
                    confidence=entity.confidence_score,
                    start_position=adjusted_start,
                    end_position=adjusted_end,
                    context=entity.context,
                    extraction_method=f"unpatterned_{entity.extraction_method}",
                    metadata={
                        "original_metadata": entity.metadata,
                        "validation_score": entity.validation_score,
                        "extraction_method_detail": entity.extraction_method,
                        "chunk_info": chunk_info
                    }
                )
                entity_matches.append(entity_match)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(len(entity_matches), processing_time, success=True)
            
            result = UnpatternedPassResult(
                entities=entity_matches,
                processing_time_ms=processing_time,
                success=True,
                metadata={
                    "handler_stats": self._handler.get_stats() if self._handler else {},
                    "processing_mode": mode.value,
                    "target_types": target_types,
                    "entities_found": len(entity_matches)
                }
            )
            
            logger.info(f"Unpatterned extraction completed: {len(entity_matches)} entities in {processing_time:.2f}ms")
            return result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._update_stats(0, processing_time, success=False)
            
            error_msg = f"Unpatterned entity extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return UnpatternedPassResult(
                processing_time_ms=processing_time,
                success=False,
                error_message=error_msg
            )
    
    def convert_to_pass_result(self, unpatterned_result: UnpatternedPassResult) -> PassResult:
        """
        Convert UnpatternedPassResult to standard PassResult format.
        
        Args:
            unpatterned_result: Result from unpatterned extraction
            
        Returns:
            PassResult compatible with existing pipeline
        """
        return PassResult(
            pass_type=UnpatternedExtractionPass.UNPATTERNED,
            entities=unpatterned_result.entities,
            processing_time_ms=unpatterned_result.processing_time_ms,
            token_usage={"input_tokens": 0, "output_tokens": 0},  # Not applicable for this method
            success=unpatterned_result.success,
            error_message=unpatterned_result.error_message,
            retry_count=0
        )
    
    async def extract_as_pass(self, 
                             text: str,
                             mode: ProcessingMode = ProcessingMode.ADAPTIVE,
                             chunk_info: Optional[Dict[str, Any]] = None) -> PassResult:
        """
        Extract unpatterned entities in PassResult format for direct integration.
        
        Args:
            text: Input text to process
            mode: Processing mode
            chunk_info: Chunk information for position adjustment
            
        Returns:
            PassResult compatible with existing pipeline
        """
        unpatterned_result = await self.extract_unpatterned_entities(
            text=text,
            mode=mode,
            chunk_info=chunk_info
        )
        
        return self.convert_to_pass_result(unpatterned_result)
    
    def _update_stats(self, entities_found: int, processing_time: float, success: bool):
        """Update extraction statistics"""
        self.extraction_stats["total_extractions"] += 1
        
        if success:
            self.extraction_stats["successful_extractions"] += 1
            self.extraction_stats["total_entities_found"] += entities_found
        else:
            self.extraction_stats["failed_extractions"] += 1
        
        # Update average processing time
        total = self.extraction_stats["total_extractions"]
        current_avg = self.extraction_stats["avg_processing_time_ms"]
        self.extraction_stats["avg_processing_time_ms"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        stats = self.extraction_stats.copy()
        
        # Add handler stats if available
        if self._handler:
            stats["handler_stats"] = self._handler.get_stats()
        
        # Add model loader stats if available
        if self.model_loader:
            stats["model_cache_stats"] = self.model_loader.cache.get_stats()
        
        return stats
    
    def clear_cache(self):
        """Clear caches"""
        if self._handler:
            self._handler.clear_cache()
        
        if self.model_loader:
            self.model_loader.clear_cache()
        
        logger.info("Cleared unpatterned extractor caches")


class EnhancedMultiPassExtractor:
    """
    Enhanced multi-pass extractor that includes unpatterned entity extraction.
    
    This class extends the existing multi-pass extraction system by adding
    an additional pass for unpatterned entities.
    """
    
    def __init__(self, 
                 original_extractor,  # The original MultiPassExtractor instance
                 unpatterned_extractor: Optional[UnpatternedExtractor] = None):
        """
        Initialize enhanced multi-pass extractor.
        
        Args:
            original_extractor: Original MultiPassExtractor instance
            unpatterned_extractor: Optional UnpatternedExtractor instance
        """
        self.original_extractor = original_extractor
        self.unpatterned_extractor = unpatterned_extractor or UnpatternedExtractor()
        
        # Track enhancement statistics
        self.enhancement_stats = {
            "total_enhanced_extractions": 0,
            "unpatterned_entities_added": 0,
            "enhancement_time_ms": 0.0
        }
        
        logger.info("EnhancedMultiPassExtractor initialized")
    
    async def extract_entities(self, 
                              text: str, 
                              request_id: str = "unknown",
                              processing_mode: str = "adaptive",
                              **kwargs) -> Tuple[List[EntityMatch], Dict[str, Any]]:
        """
        Enhanced entity extraction that includes unpatterned entities.
        
        Args:
            text: Text to extract entities from
            request_id: Request identifier for tracking
            processing_mode: Processing mode (fast, comprehensive, adaptive)
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (entities, metadata) with unpatterned entities included
        """
        start_time = time.time()
        
        try:
            # Run original extraction
            logger.info(f"Running original multi-pass extraction for request {request_id}")
            original_entities, original_metadata = await self.original_extractor.extract_entities(
                text=text,
                request_id=request_id,
                **kwargs
            )
            
            # Run unpatterned extraction
            logger.info(f"Running unpatterned entity extraction for request {request_id}")
            mode_map = {
                "fast": ProcessingMode.FAST,
                "comprehensive": ProcessingMode.COMPREHENSIVE,
                "adaptive": ProcessingMode.ADAPTIVE
            }
            unpatterned_mode = mode_map.get(processing_mode, ProcessingMode.ADAPTIVE)
            
            unpatterned_result = await self.unpatterned_extractor.extract_unpatterned_entities(
                text=text,
                mode=unpatterned_mode,
                chunk_info=kwargs.get('chunk_info')
            )
            
            # Combine results
            all_entities = original_entities + unpatterned_result.entities
            
            # Update metadata
            enhanced_metadata = original_metadata.copy()
            enhanced_metadata.update({
                "unpatterned_extraction": {
                    "success": unpatterned_result.success,
                    "entities_found": len(unpatterned_result.entities),
                    "processing_time_ms": unpatterned_result.processing_time_ms,
                    "error_message": unpatterned_result.error_message,
                    "metadata": unpatterned_result.metadata
                },
                "total_entities_with_unpatterned": len(all_entities),
                "original_entities_count": len(original_entities),
                "unpatterned_entities_count": len(unpatterned_result.entities)
            })
            
            # Update enhancement statistics
            enhancement_time = (time.time() - start_time) * 1000
            self._update_enhancement_stats(len(unpatterned_result.entities), enhancement_time)
            
            logger.info(f"Enhanced extraction completed for {request_id}: "
                       f"{len(original_entities)} original + {len(unpatterned_result.entities)} unpatterned = "
                       f"{len(all_entities)} total entities")
            
            return all_entities, enhanced_metadata
            
        except Exception as e:
            logger.error(f"Enhanced extraction failed for {request_id}: {e}", exc_info=True)
            # Fallback to original extraction
            return await self.original_extractor.extract_entities(
                text=text,
                request_id=request_id,
                **kwargs
            )
    
    def _update_enhancement_stats(self, unpatterned_entities: int, enhancement_time: float):
        """Update enhancement statistics"""
        self.enhancement_stats["total_enhanced_extractions"] += 1
        self.enhancement_stats["unpatterned_entities_added"] += unpatterned_entities
        self.enhancement_stats["enhancement_time_ms"] += enhancement_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        stats = {
            "enhancement_stats": self.enhancement_stats.copy(),
            "unpatterned_stats": self.unpatterned_extractor.get_stats()
        }
        
        # Add original extractor stats if available
        if hasattr(self.original_extractor, 'get_stats'):
            stats["original_extractor_stats"] = self.original_extractor.get_stats()
        
        return stats
    
    def clear_caches(self):
        """Clear all caches"""
        self.unpatterned_extractor.clear_cache()
        
        # Clear original extractor caches if available
        if hasattr(self.original_extractor, 'clear_caches'):
            self.original_extractor.clear_caches()
        
        logger.info("Cleared all enhanced extractor caches")


# Factory function for creating enhanced extractor
def create_enhanced_extractor(original_extractor, 
                            cales_config_path: Optional[str] = None,
                            model_loader: Optional[DynamicModelLoader] = None) -> EnhancedMultiPassExtractor:
    """
    Create an enhanced multi-pass extractor with unpatterned entity support.
    
    Args:
        original_extractor: Original MultiPassExtractor instance
        cales_config_path: Optional path to CALES configuration
        model_loader: Optional model loader instance
        
    Returns:
        EnhancedMultiPassExtractor instance
    """
    unpatterned_extractor = UnpatternedExtractor(
        cales_config_path=cales_config_path or "/srv/luris/be/entity-extraction-service/config/archive/cales_config.yaml",
        model_loader=model_loader
    )
    
    return EnhancedMultiPassExtractor(
        original_extractor=original_extractor,
        unpatterned_extractor=unpatterned_extractor
    )


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_integration():
        """Test the unpatterned entity integration"""
        extractor = UnpatternedExtractor()
        
        test_text = """
        The plaintiff, John Smith, filed a complaint against ABC Corporation
        in the Superior Court of California. Judge Mary Johnson presided over
        the case, which involved a breach of contract claim regarding a
        software licensing agreement worth $500,000. Attorney Jane Doe
        represents the plaintiff, while the defendant is represented by
        the law firm of Wilson & Associates LLP.
        """
        
        # Test unpatterned extraction
        result = await extractor.extract_unpatterned_entities(
            text=test_text,
            mode=ProcessingMode.COMPREHENSIVE
        )
        
        print(f"Unpatterned extraction result:")
        print(f"  Success: {result.success}")
        print(f"  Entities found: {len(result.entities)}")
        print(f"  Processing time: {result.processing_time_ms:.2f}ms")
        
        for entity in result.entities:
            print(f"    {entity.text} -> {entity.entity_type} (conf: {entity.confidence:.2f})")
        
        # Test conversion to PassResult
        pass_result = extractor.convert_to_pass_result(result)
        print(f"\nConverted to PassResult:")
        print(f"  Pass type: {pass_result.pass_type}")
        print(f"  Success: {pass_result.success}")
        print(f"  Entities: {len(pass_result.entities)}")
        
        print(f"\nExtractor stats: {extractor.get_stats()}")
    
    asyncio.run(test_integration())