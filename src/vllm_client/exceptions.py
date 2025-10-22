"""
Exception classes for vLLM integration module.
"""

from typing import Optional
from datetime import datetime


class VLLMClientError(Exception):
    """Base exception for vLLM client errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.timestamp = datetime.utcnow()


class ModelNotLoadedError(VLLMClientError):
    """Raised when attempting to use model before it's loaded."""

    def __init__(self, message: str = "Model not loaded", retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.suggested_action = "Ensure vLLM engine is initialized and ready"


class GenerationError(VLLMClientError):
    """Raised when text generation fails."""

    def __init__(
        self,
        message: str = "Text generation failed",
        generation_attempt: int = 1,
        max_retries: int = 3,
        timeout_occurred: bool = False,
        server_error: bool = False,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.generation_attempt = generation_attempt
        self.max_retries = max_retries
        self.timeout_occurred = timeout_occurred
        self.server_error = server_error
        self.original_error = original_error
        self.can_retry = generation_attempt < max_retries and not server_error

        if timeout_occurred:
            self.suggested_action = "Reduce context size or increase timeout"
        elif server_error:
            self.suggested_action = "Check vLLM service status and connectivity"
        else:
            self.suggested_action = "Retry with exponential backoff"


class ContextOverflowError(VLLMClientError):
    """Raised when prompt exceeds context window limit."""

    def __init__(
        self,
        message: str,
        estimated_tokens: int,
        max_tokens: int,
        excess_tokens: int
    ):
        super().__init__(message)
        self.estimated_tokens = estimated_tokens
        self.max_tokens = max_tokens
        self.excess_tokens = excess_tokens
        self.suggested_action = (
            f"Reduce prompt by ~{excess_tokens} tokens or implement chunking strategy"
        )


class GPUMemoryError(VLLMClientError):
    """Raised when GPU memory is insufficient."""

    def __init__(
        self,
        message: str,
        used_memory_gb: float,
        total_memory_gb: float,
        utilization_percent: float
    ):
        super().__init__(message)
        self.used_memory_gb = used_memory_gb
        self.total_memory_gb = total_memory_gb
        self.utilization_percent = utilization_percent
        self.suggested_action = "Wait for GPU memory to free up or reduce batch size"


class ConnectionError(VLLMClientError):
    """Raised when connection to vLLM service fails."""

    def __init__(self, message: str, base_url: Optional[str] = None):
        super().__init__(message)
        self.base_url = base_url
        self.suggested_action = "Check vLLM service status and network connectivity"


class ConfigurationError(VLLMClientError):
    """Raised when vLLM client configuration is invalid."""

    def __init__(self, message: str, invalid_field: Optional[str] = None):
        super().__init__(message)
        self.invalid_field = invalid_field
        self.suggested_action = "Check configuration parameters and documentation"
