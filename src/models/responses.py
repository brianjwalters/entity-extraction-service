"""
Entity Extraction Service - Response Models

This module contains Pydantic models for entity extraction responses including
processing summaries and performance metrics.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .entities import Entity, Citation, EntityRelationship


class ProcessingSummary(BaseModel):
    """Summary of processing pipeline performance and results."""
    
    total_processing_time_ms: int = Field(
        ..., 
        ge=0,
        description="Total processing time in milliseconds"
    )
    regex_stage_time_ms: int = Field(
        ..., 
        ge=0,
        description="Time spent in regex extraction stage"
    )
    ai_enhancement_time_ms: int = Field(
        ..., 
        ge=0,
        description="Time spent in AI enhancement stage"
    )
    entities_found: int = Field(
        ..., 
        ge=0,
        description="Total number of entities extracted"
    )
    citations_found: int = Field(
        ..., 
        ge=0,
        description="Total number of citations extracted"
    )
    relationships_found: int = Field(
        ..., 
        ge=0,
        description="Total number of relationships identified"
    )
    ai_enhancements_applied: int = Field(
        ..., 
        ge=0,
        description="Number of AI enhancements applied during processing"
    )
    confidence_distribution: Dict[str, int] = Field(
        default_factory=dict, 
        description="Distribution of confidence scores by range"
    )
    processing_stages_completed: List[str] = Field(
        default_factory=list, 
        description="List of successfully completed processing stages"
    )
    pattern_matches: Dict[str, int] = Field(
        default_factory=dict,
        description="Number of matches per regex pattern"
    )
    ai_discoveries: int = Field(
        0,
        ge=0,
        description="Number of entities/citations discovered by AI that regex missed"
    )
    bluebook_compliance_rate: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Percentage of citations that are Bluebook compliant"
    )
    avg_confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Average confidence score across all extractions"
    )
    
    @validator('total_processing_time_ms')
    def validate_total_time(cls, v, values):
        """Ensure total time is at least the sum of stage times."""
        regex_time = values.get('regex_stage_time_ms', 0)
        ai_time = values.get('ai_enhancement_time_ms', 0)
        if v < (regex_time + ai_time):
            # Allow some tolerance for parallel processing
            if v < (regex_time + ai_time) * 0.5:
                raise ValueError('Total processing time cannot be less than half the sum of stage times')
        return v


class ExtractionResponse(BaseModel):
    """Complete extraction service response for the /extract endpoint."""
    
    document_id: str = Field(
        ..., 
        description="Document identifier from the original request"
    )
    processing_summary: ProcessingSummary = Field(
        ..., 
        description="Processing performance summary and metrics"
    )
    entities: List[Entity] = Field(
        default_factory=list, 
        description="List of extracted legal entities with confidence scores"
    )
    citations: List[Citation] = Field(
        default_factory=list, 
        description="List of extracted legal citations with Bluebook compliance"
    )
    relationships: List[EntityRelationship] = Field(
        default_factory=list, 
        description="List of identified relationships between entities"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional processing metadata and context"
    )
    warnings: List[str] = Field(
        default_factory=list, 
        description="Non-fatal processing warnings"
    )
    errors: List[str] = Field(
        default_factory=list, 
        description="Non-fatal processing errors that did not stop extraction"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="Unique request identifier for tracking"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Response generation timestamp"
    )
    success: bool = Field(
        True,
        description="Whether the extraction process completed successfully"
    )
    
    @validator('entities')
    def validate_entity_count(cls, v, values):
        """Validate entity count matches processing summary."""
        summary = values.get('processing_summary')
        if summary and len(v) != summary.entities_found:
            raise ValueError(f'Entity count mismatch: {len(v)} vs {summary.entities_found}')
        return v
    
    @validator('citations')
    def validate_citation_count(cls, v, values):
        """Validate citation count matches processing summary."""
        summary = values.get('processing_summary')
        if summary and len(v) != summary.citations_found:
            raise ValueError(f'Citation count mismatch: {len(v)} vs {summary.citations_found}')
        return v
    
    @validator('relationships')
    def validate_relationship_count(cls, v, values):
        """Validate relationship count matches processing summary."""
        summary = values.get('processing_summary')
        if summary and len(v) != summary.relationships_found:
            raise ValueError(f'Relationship count mismatch: {len(v)} vs {summary.relationships_found}')
        return v
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a specific type."""
        return [entity for entity in self.entities if entity.entity_type.value == entity_type]
    
    def get_citations_by_type(self, citation_type: str) -> List[Citation]:
        """Get all citations of a specific type."""
        return [citation for citation in self.citations if citation.citation_type.value == citation_type]
    
    def get_high_confidence_items(self, threshold: float = 0.8) -> Dict[str, List]:
        """Get all items above a confidence threshold."""
        high_confidence_entities = [e for e in self.entities if e.confidence_score >= threshold]
        high_confidence_citations = [c for c in self.citations if c.confidence_score >= threshold]
        high_confidence_relationships = [r for r in self.relationships if r.confidence_score >= threshold]
        
        return {
            'entities': high_confidence_entities,
            'citations': high_confidence_citations,
            'relationships': high_confidence_relationships
        }
    
    def get_ai_enhanced_items(self) -> Dict[str, List]:
        """Get all items that were enhanced by AI."""
        ai_enhanced_entities = [e for e in self.entities if e.ai_enhancements]
        ai_enhanced_citations = [c for c in self.citations if c.ai_enhancements]
        
        return {
            'entities': ai_enhanced_entities,
            'citations': ai_enhanced_citations
        }
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive extraction statistics."""
        all_items = self.entities + self.citations + self.relationships
        
        if not all_items:
            return {
                'total_items': 0,
                'average_confidence': 0.0,
                'confidence_distribution': {},
                'extraction_methods': {},
                'ai_enhancement_rate': 0.0
            }
        
        # Calculate confidence distribution
        confidence_ranges = {
            '0.0-0.2': 0, '0.2-0.4': 0, '0.4-0.6': 0, 
            '0.6-0.8': 0, '0.8-1.0': 0
        }
        
        extraction_methods = {}
        ai_enhanced_count = 0
        
        for item in all_items:
            # Confidence distribution
            score = item.confidence_score
            if score < 0.2:
                confidence_ranges['0.0-0.2'] += 1
            elif score < 0.4:
                confidence_ranges['0.2-0.4'] += 1
            elif score < 0.6:
                confidence_ranges['0.4-0.6'] += 1
            elif score < 0.8:
                confidence_ranges['0.6-0.8'] += 1
            else:
                confidence_ranges['0.8-1.0'] += 1
            
            # Extraction methods
            method = item.extraction_method.value
            extraction_methods[method] = extraction_methods.get(method, 0) + 1
            
            # AI enhancement tracking
            if hasattr(item, 'ai_enhancements') and item.ai_enhancements:
                ai_enhanced_count += 1
        
        return {
            'total_items': len(all_items),
            'average_confidence': sum(item.confidence_score for item in all_items) / len(all_items),
            'confidence_distribution': confidence_ranges,
            'extraction_methods': extraction_methods,
            'ai_enhancement_rate': ai_enhanced_count / len(all_items) if all_items else 0.0,
            'entities_by_type': {
                entity_type.value: len([e for e in self.entities if e.entity_type == entity_type])
                for entity_type in {e.entity_type for e in self.entities}
            },
            'citations_by_type': {
                citation_type.value: len([c for c in self.citations if c.citation_type == citation_type])
                for citation_type in {c.citation_type for c in self.citations}
            }
        }

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "document_id": "supreme_court_opinion_2024_001",
                "processing_summary": {
                    "total_processing_time_ms": 2500,
                    "regex_stage_time_ms": 800,
                    "ai_enhancement_time_ms": 1200,
                    "entities_found": 15,
                    "citations_found": 8,
                    "relationships_found": 6,
                    "ai_enhancements_applied": 12,
                    "confidence_distribution": {
                        "0.8-1.0": 18,
                        "0.6-0.8": 8,
                        "0.4-0.6": 3
                    },
                    "processing_stages_completed": [
                        "regex_extraction",
                        "ai_validation", 
                        "ai_enhancement",
                        "relationship_extraction",
                        "confidence_scoring"
                    ],
                    "bluebook_compliance_rate": 0.875,
                    "avg_confidence_score": 0.82
                },
                "entities": [],  # Would contain Entity objects
                "citations": [],  # Would contain Citation objects
                "relationships": [],  # Would contain EntityRelationship objects
                "metadata": {
                    "source_length": 5420,
                    "patterns_matched": 23,
                    "ai_model_version": "luris-legal-gpt-v2.1",
                    "processing_mode": "comprehensive"
                },
                "warnings": [
                    "Two potential citations could not be validated against known reporters"
                ],
                "errors": [],
                "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2024-07-24T10:30:45.123456Z",
                "success": True
            }
        }