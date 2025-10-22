"""
vLLM Integration Module

Direct Python API integration with vLLM for high-performance LLM inference.
Replaces HTTP-based calls with direct API access for entity extraction.

Key Features:
- Zero network overhead (direct Python API)
- Native batch processing support
- Proactive token estimation and context validation
- GPU memory monitoring
- Automatic fallback to HTTP on failure
- Reproducibility enforcement (temperature=0.0, seed=42)
"""

from .client import VLLMClientInterface, VLLMClientType
from .client import DirectVLLMClient, HTTPVLLMClient
from .factory import VLLMClientFactory
from .models import VLLMConfig, VLLMRequest, VLLMResponse, VLLMUsage
from .token_estimator import TokenEstimator, ContextOverflowError
from .gpu_monitor import GPUMonitor, GPUStats
from .exceptions import (
    VLLMClientError,
    ModelNotLoadedError,
    GenerationError,
    ContextOverflowError,
    GPUMemoryError
)

__all__ = [
    # Client interfaces
    "VLLMClientInterface",
    "VLLMClientType",
    "DirectVLLMClient",
    "HTTPVLLMClient",

    # Factory
    "VLLMClientFactory",

    # Models
    "VLLMConfig",
    "VLLMRequest",
    "VLLMResponse",
    "VLLMUsage",

    # Token estimation
    "TokenEstimator",
    "ContextOverflowError",

    # GPU monitoring
    "GPUMonitor",
    "GPUStats",

    # Exceptions
    "VLLMClientError",
    "ModelNotLoadedError",
    "GenerationError",
    "GPUMemoryError",
]

__version__ = "1.0.0"
