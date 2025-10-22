"""
Context Resolution Module for CALES Entity Extraction Service

This module provides comprehensive context analysis for legal entities,
combining multiple resolution methods to accurately determine entity contexts.
"""

from .context_mappings import (
    ContextType,
    EntityContextMapping,
    ContextMappings
)

from .context_window_extractor import (
    WindowLevel,
    ContextWindow,
    ExtractedEntity,
    ContextWindowExtractor
)

from .context_resolver import (
    ContextResolutionMethod,
    ContextSignal,
    ResolvedContext,
    ContextResolver
)

__all__ = [
    # Context Mappings
    'ContextType',
    'EntityContextMapping', 
    'ContextMappings',
    
    # Window Extractor
    'WindowLevel',
    'ContextWindow',
    'ExtractedEntity',
    'ContextWindowExtractor',
    
    # Context Resolver
    'ContextResolutionMethod',
    'ContextSignal',
    'ResolvedContext',
    'ContextResolver'
]

# Version information
__version__ = '1.0.0'