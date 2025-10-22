"""
Database module for Document Intelligence Service v2.0.0

Provides database storage services for graph.chunks and graph.entities.
"""

from .graph_storage import GraphStorageService, create_graph_storage_service

__all__ = [
    "GraphStorageService",
    "create_graph_storage_service"
]
