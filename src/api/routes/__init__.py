"""
API Routes package for Entity Extraction Service.

This package contains all FastAPI route definitions for the service:
- health: Health check and monitoring endpoints
- extract: Core entity extraction endpoints
- entity_types: Entity and citation type information endpoints
- model_management: Performance profile and model management endpoints
"""

__all__ = ["health", "extract", "entity_types", "model_management"]