# Eyecite Hybrid Architecture - Proof of Concept
# All code in this module is self-contained and does not modify the main codebase

from .luris_entity_v2 import (
    LurisEntityV2,
    EntityType,
    ExtractionMethod,
    create_entity,
)

from .eyecite_to_luris_mapper import (
    EyeciteToLurisMapper,
    map_eyecite_citations,
)

from .llm_unknown_classifier import (
    LLMUnknownClassifier,
    ClassificationResult,
    extract_context_window,
)

from .hybrid_extraction_pipeline import (
    HybridExtractionPipeline,
    generate_entity_report,
)

__all__ = [
    "LurisEntityV2",
    "EntityType",
    "ExtractionMethod",
    "create_entity",
    "EyeciteToLurisMapper",
    "map_eyecite_citations",
    "LLMUnknownClassifier",
    "ClassificationResult",
    "extract_context_window",
    "HybridExtractionPipeline",
    "generate_entity_report",
]
