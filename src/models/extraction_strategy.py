"""
Extraction strategy definitions and configurations.

This module defines the available extraction strategies and their specific configurations.
Each strategy represents a different approach to entity extraction optimized for different use cases.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ExtractionStrategy(str, Enum):
    """Available extraction strategies for entity extraction."""
    
    MULTIPASS = "multipass"
    """7-pass sequential extraction with progressive refinement. 
    Best for comprehensive legal analysis requiring maximum recall."""
    
    AI_ENHANCED = "ai_enhanced"
    """AI-first extraction with deep NLP analysis.
    Best for complex documents requiring semantic understanding."""
    
    UNIFIED = "unified"
    """Single-pass comprehensive extraction.
    Best balance of speed and accuracy for standard documents."""
    
    REGEX = "regex"
    """Pure regex-based extraction without AI enhancement.
    Fastest but may miss contextual entities."""
    
    HYBRID = "hybrid"
    """Legacy mode: Regex extraction with AI validation.
    Maintained for backward compatibility."""
    
    PAGEBATCH = "pagebatch"
    """Page-batch extraction with comprehensive entity coverage.
    Processes documents in configurable page batches with ALL 195+ entity types.
    Optimized for complex documents requiring full contextualization."""


class MultipassConfig(BaseModel):
    """Configuration for multipass extraction strategy."""
    
    num_passes: int = Field(default=7, description="Number of extraction passes")
    parallel_passes: bool = Field(default=True, description="Execute passes in parallel where possible")
    min_confidence_pass1: float = Field(default=0.3, description="Minimum confidence for pass 1")
    max_confidence_pass1: float = Field(default=0.7, description="Maximum confidence for pass 1")
    confidence_boost_per_pass: float = Field(default=0.1, description="Confidence increase per pass")
    enable_validation_passes: bool = Field(default=True, description="Enable validation in passes 2-6")
    final_sweep_threshold: float = Field(default=0.5, description="Confidence threshold for final pass")


class AIEnhancedConfig(BaseModel):
    """Configuration for AI-enhanced extraction strategy."""
    
    enable_coreference_resolution: bool = Field(default=True, description="Resolve pronouns to entities")
    enable_semantic_similarity: bool = Field(default=True, description="Use semantic matching")
    context_weight: float = Field(default=0.3, description="Weight for contextual relevance")
    linguistic_weight: float = Field(default=0.3, description="Weight for linguistic patterns")
    semantic_weight: float = Field(default=0.4, description="Weight for semantic clarity")
    min_confidence_threshold: float = Field(default=0.6, description="Minimum confidence for inclusion")
    enable_relationship_inference: bool = Field(default=True, description="Infer relationships from context")


class UnifiedConfig(BaseModel):
    """Configuration for unified extraction strategy."""
    
    min_confidence: float = Field(default=0.6, description="Minimum confidence threshold")
    entity_priority_order: list[str] = Field(
        default=["PERSON", "ORGANIZATION", "CASE", "STATUTE", "DATE", "MONETARY", "LEGAL_CONCEPT"],
        description="Order of entity type extraction priority"
    )
    max_entities_per_type: Optional[int] = Field(default=None, description="Maximum entities per type")
    enable_comprehensive_scan: bool = Field(default=True, description="Scan for all 160 entity types")
    balance_precision_recall: bool = Field(default=True, description="Balance precision and recall equally")


class PageBatchConfig(BaseModel):
    """Configuration for page-batch extraction strategy."""
    
    batch_size: int = Field(default=3, description="Number of pages per batch (1-10)")
    min_confidence: float = Field(default=0.7, description="Minimum confidence threshold")
    overlap_pages: int = Field(default=0, description="Number of pages to overlap between batches")
    maintain_context: bool = Field(default=True, description="Maintain entity context across batches")
    extract_relationships: bool = Field(default=True, description="Extract entity relationships within and across batches")
    comprehensive_coverage: bool = Field(default=True, description="Include all 195+ entity types")
    summarize_batches: bool = Field(default=True, description="Generate batch summaries for context")


class StrategyConfig(BaseModel):
    """Combined configuration for all strategies."""
    
    strategy: ExtractionStrategy = Field(description="The extraction strategy to use")
    multipass_config: Optional[MultipassConfig] = Field(default=None, description="Multipass strategy config")
    ai_enhanced_config: Optional[AIEnhancedConfig] = Field(default=None, description="AI-enhanced strategy config")
    unified_config: Optional[UnifiedConfig] = Field(default=None, description="Unified strategy config")
    pagebatch_config: Optional[PageBatchConfig] = Field(default=None, description="PageBatch strategy config")
    
    def get_active_config(self):
        """Get the configuration for the active strategy."""
        if self.strategy == ExtractionStrategy.MULTIPASS:
            return self.multipass_config or MultipassConfig()
        elif self.strategy == ExtractionStrategy.AI_ENHANCED:
            return self.ai_enhanced_config or AIEnhancedConfig()
        elif self.strategy == ExtractionStrategy.UNIFIED:
            return self.unified_config or UnifiedConfig()
        elif self.strategy == ExtractionStrategy.PAGEBATCH:
            return self.pagebatch_config or PageBatchConfig()
        return None


def get_strategy_description(strategy: ExtractionStrategy) -> str:
    """Get a detailed description of the extraction strategy."""
    descriptions = {
        ExtractionStrategy.MULTIPASS: (
            "Multipass extraction uses 7 sequential passes to progressively refine entity extraction. "
            "Pass 1 casts a wide net with low confidence (0.3-0.7), subsequent passes validate and "
            "enhance results, and the final pass catches any missed entities. This strategy provides "
            "the highest recall and is ideal for comprehensive legal document analysis where missing "
            "an entity could have significant consequences."
        ),
        ExtractionStrategy.AI_ENHANCED: (
            "AI-enhanced extraction leverages advanced NLP capabilities in a single deep-analysis pass. "
            "It uses coreference resolution, semantic similarity, and contextual understanding to "
            "identify entities that regex patterns might miss. Confidence is calculated using multiple "
            "signals (context, linguistics, semantics) and is ideal for complex documents with "
            "ambiguous language or implicit references."
        ),
        ExtractionStrategy.UNIFIED: (
            "Unified extraction performs comprehensive single-pass extraction of all entity types. "
            "It balances precision and recall equally, maintains a minimum confidence threshold of 0.6, "
            "and processes entities in priority order. This strategy is optimized for speed and "
            "efficiency, making it suitable for standard documents or when processing time is critical."
        ),
        ExtractionStrategy.REGEX: (
            "Pure regex-based extraction using predefined patterns without AI enhancement. "
            "This is the fastest extraction method but may miss contextual entities or those "
            "requiring semantic understanding. Best for structured documents with consistent formatting."
        ),
        ExtractionStrategy.HYBRID: (
            "Legacy hybrid mode that combines regex extraction with AI validation. "
            "Regex patterns identify candidates which are then validated and enhanced by AI. "
            "Maintained for backward compatibility with existing workflows."
        ),
        ExtractionStrategy.PAGEBATCH: (
            "Page-batch extraction processes documents in configurable page batches with comprehensive "
            "entity coverage. Each batch includes all 195+ entity types with contextual summaries, "
            "cross-batch relationship tracking, and full document contextualization. This strategy "
            "is optimized for complex legal documents requiring detailed analysis and rich "
            "relationship discovery for knowledge graph construction."
        )
    }
    return descriptions.get(strategy, "No description available")


def get_optimal_strategy(
    document_type: str = None,
    document_length: int = None,
    time_constraint_ms: int = None,
    accuracy_requirement: float = None
) -> ExtractionStrategy:
    """
    Recommend an optimal extraction strategy based on document characteristics and requirements.
    
    Args:
        document_type: Type of document (e.g., "contract", "court_opinion", "statute")
        document_length: Length of document in characters
        time_constraint_ms: Maximum allowed processing time in milliseconds
        accuracy_requirement: Required accuracy/recall (0.0 to 1.0)
    
    Returns:
        Recommended extraction strategy
    """
    # If strict time constraint, use fastest strategies
    if time_constraint_ms and time_constraint_ms < 1000:
        return ExtractionStrategy.REGEX
    elif time_constraint_ms and time_constraint_ms < 5000:
        return ExtractionStrategy.UNIFIED
    
    # If high accuracy required, use multipass
    if accuracy_requirement and accuracy_requirement > 0.9:
        return ExtractionStrategy.MULTIPASS
    
    # Document type specific recommendations
    if document_type:
        if document_type in ["court_opinion", "appellate_decision"]:
            # Complex legal documents benefit from multipass
            return ExtractionStrategy.MULTIPASS
        elif document_type in ["contract", "agreement"]:
            # Contracts benefit from AI understanding of terms
            return ExtractionStrategy.AI_ENHANCED
        elif document_type in ["statute", "regulation"]:
            # Structured documents work well with unified
            return ExtractionStrategy.UNIFIED
    
    # Document length considerations
    if document_length:
        if document_length > 100000:  # Very long documents
            return ExtractionStrategy.MULTIPASS  # Worth the extra time for completeness
        elif document_length > 20000:  # Medium documents
            return ExtractionStrategy.AI_ENHANCED
        else:  # Short documents
            return ExtractionStrategy.UNIFIED
    
    # Default recommendation
    return ExtractionStrategy.UNIFIED