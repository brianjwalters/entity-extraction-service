"""
Unpatterned Entity Extraction Module

This module handles entity extraction for entity types that don't have regex patterns,
using advanced NLP techniques including zero-shot classification, NER, and contextual validation.
"""

from .unpatterned_entity_handler import (
    UnpatternedEntityHandler,
    UnpatternedEntity,
    ProcessingMode
)

from .entity_strategies import (
    ExtractionStrategy,
    ExtractionResult,
    ZeroShotClassificationStrategy,
    NamedEntityRecognitionStrategy,
    NounPhraseExtractionStrategy,
    SemanticSimilarityStrategy,
    create_strategy
)

from .entity_candidates import (
    EntityCandidate,
    EntityCandidateGenerator,
    CandidateType,
    CandidateCache
)

__all__ = [
    # Main handler
    'UnpatternedEntityHandler',
    'UnpatternedEntity',
    'ProcessingMode',
    
    # Strategies
    'ExtractionStrategy',
    'ExtractionResult',
    'ZeroShotClassificationStrategy',
    'NamedEntityRecognitionStrategy',
    'NounPhraseExtractionStrategy',
    'SemanticSimilarityStrategy',
    'create_strategy',
    
    # Candidates
    'EntityCandidate',
    'EntityCandidateGenerator',
    'CandidateType',
    'CandidateCache'
]