"""
Entity Extraction Service - Request Models

This module contains Pydantic models for entity extraction requests including
configuration options for the hybrid REGEX + AI workflow.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, Literal
from .extraction_strategy import (
    ExtractionStrategy, 
    MultipassConfig, 
    AIEnhancedConfig, 
    UnifiedConfig
)


class ExtractionOptions(BaseModel):
    """Configuration options for the extraction process."""
    
    include_confidence_scores: bool = Field(
        True, 
        description="Include confidence scores for all extracted items"
    )
    enable_relationship_extraction: bool = Field(
        True, 
        description="Extract semantic relationships between entities"
    )
    bluebook_compliance_level: Literal["strict", "standard", "relaxed"] = Field(
        "strict", 
        description="Level of Bluebook citation compliance enforcement"
    )
    ai_enhancement_mode: Literal["regex_only", "validation_only", "correction_only", "comprehensive"] = Field(
        "comprehensive",
        description="AI enhancement processing mode: 'regex_only' (no AI), 'validation_only' (AI validation), 'correction_only' (AI correction), 'comprehensive' (full AI enhancement)"
    )
    extraction_strategy: Optional[ExtractionStrategy] = Field(
        None,
        description="Extraction strategy: 'multipass' (7-pass refinement), 'unified' (single comprehensive), 'ai_enhanced' (NLP-powered), or 'regex' (pattern-only)"
    )
    multipass_config: Optional[MultipassConfig] = Field(
        None,
        description="Configuration for multipass strategy"
    )
    ai_enhanced_config: Optional[AIEnhancedConfig] = Field(
        None,
        description="Configuration for AI-enhanced strategy"  
    )
    unified_config: Optional[UnifiedConfig] = Field(
        None,
        description="Configuration for unified strategy"
    )
    max_entities_per_type: int = Field(
        1000, 
        ge=1,
        le=5000,
        description="Maximum number of entities per type to extract"
    )
    confidence_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for including results"
    )
    enable_parallel_citations: bool = Field(
        True, 
        description="Extract parallel citation forms when available"
    )
    enable_context_analysis: bool = Field(
        True, 
        description="Analyze surrounding text context for better accuracy"
    )
    extraction_timeout_seconds: int = Field(
        2700,  # 45 minutes - extended timeout for very large documents
        ge=10,
        le=2700,  # Updated max limit to 45 minutes to match service configuration
        description="Maximum time allowed for extraction process"
    )
    # ADD NEW CONTEXT AND WINDOW FIELDS
    include_context: bool = Field(
        True,
        description="Whether to include context around extracted entities"
    )
    context_window: int = Field(
        150,
        ge=50,
        le=500,
        description="Character window around extracted entities for context"
    )
    relationship_context_window: int = Field(
        250,
        ge=100,
        le=1000,
        description="Context window for relationship extraction (larger than entity context)"
    )
    relationship_confidence_threshold: float = Field(
        0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for relationship extraction"
    )


class ExtractionRequest(BaseModel):
    """Complete extraction request model for the /extract endpoint."""
    
    document_id: str = Field(
        ..., 
        min_length=3,
        max_length=255,
        description="Unique document identifier for tracking and logging"
    )
    text: str = Field(
        ..., 
        max_length=10_485_760,  # 10MB limit
        description="Legal text content to analyze for entities and citations"
    )
    options: Optional[ExtractionOptions] = Field(
        default_factory=ExtractionOptions,
        description="Extraction configuration options"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Additional metadata for processing context"
    )
    
    @validator('text')
    def validate_text_content(cls, v):
        """Validate text content requirements."""
        if not v or not v.strip():
            raise ValueError('Text content cannot be empty or whitespace only')
        
        # Check byte size to ensure it's within the 10MB limit
        if len(v.encode('utf-8')) > 10_485_760:
            raise ValueError('Text content exceeds maximum size limit of 10MB')
        
        return v.strip()
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Validate document ID format and length."""
        if not v or len(v.strip()) < 3:
            raise ValueError('Document ID must be at least 3 characters long')
        
        # Remove any leading/trailing whitespace
        v = v.strip()
        
        # Check for invalid characters that could cause issues
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\n', '\r', '\t']
        if any(char in v for char in invalid_chars):
            raise ValueError('Document ID contains invalid characters')
        
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata doesn't contain sensitive information."""
        if v is None:
            return {}
        
        # Check for potentially sensitive keys
        sensitive_keys = ['password', 'token', 'secret', 'key', 'auth']
        for key in v.keys():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                raise ValueError(f'Metadata key "{key}" appears to contain sensitive information')
        
        return v

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "document_id": "supreme_court_opinion_2024_001",
                "text": "In the matter of Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held that state laws establishing separate public schools for black and white students were unconstitutional.",
                "options": {
                    "include_confidence_scores": True,
                    "enable_relationship_extraction": True,
                    "bluebook_compliance_level": "strict",
                    "ai_enhancement_mode": "comprehensive",
                    "max_entities_per_type": 1000,
                    "confidence_threshold": 0.7,
                    "enable_parallel_citations": True,
                    "enable_context_analysis": True,
                    "extraction_timeout_seconds": 1200  # 20 minutes - extended
                },
                "metadata": {
                    "source": "court_database",
                    "jurisdiction": "federal",
                    "document_type": "opinion",
                    "processing_priority": "high"
                }
            }
        }