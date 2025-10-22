"""
CALES Model Management System

This package provides comprehensive model lifecycle management for the CALES
Entity Extraction Service, including model initialization, dynamic loading,
and version registry management.
"""

from .model_initializer import ModelInitializer, ModelInfo
from .dynamic_model_loader import DynamicModelLoader, ModelCache, LoadedModel, ModelPriority
from .model_registry import ModelRegistry, ModelVersion, DeploymentRecord, DeploymentStatus, ModelStage

__all__ = [
    'ModelInitializer',
    'ModelInfo',
    'DynamicModelLoader',
    'ModelCache',
    'LoadedModel',
    'ModelPriority',
    'ModelRegistry',
    'ModelVersion',
    'DeploymentRecord',
    'DeploymentStatus',
    'ModelStage'
]

__version__ = '1.0.0'