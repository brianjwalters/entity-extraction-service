"""
Intelligent Document Router Module

This module provides size-based document routing for optimal entity extraction processing.
"""

from .size_detector import SizeDetector, DocumentSizeInfo, SizeCategory
from .document_router import (
    DocumentRouter,
    RoutingDecision,
    ProcessingStrategy,
    ChunkConfig
)

__all__ = [
    "SizeDetector",
    "DocumentSizeInfo",
    "SizeCategory",
    "DocumentRouter",
    "RoutingDecision",
    "ProcessingStrategy",
    "ChunkConfig"
]
