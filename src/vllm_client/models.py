"""
Data models for vLLM integration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class VLLMClientType(Enum):
    """Client implementation type."""
    DIRECT_API = "direct_api"
    HTTP_API = "http_api"


class VLLMServiceType(str, Enum):
    """vLLM service types for routing."""
    INSTRUCT = "instruct"      # Fast entity extraction (Port 8080)
    THINKING = "thinking"      # Complex reasoning (Port 8082)
    EMBEDDINGS = "embeddings"  # Document embeddings (Port 8081)


@dataclass
class VLLMConfig:
    """
    Configuration for vLLM client with multi-service support.

    All defaults are now pulled from centralized config.py.
    Use from_settings() class method to initialize from Settings.

    Multi-Service Architecture:
    - instruct_url: Port 8080 - Qwen3-VL-8B-Instruct-FP8 (384K context) - Entity extraction
    - thinking_url: Port 8082 - Qwen3-VL-8B-Thinking-FP8 (256K context) - Relationship extraction
    - embeddings_url: Port 8081 - Jina Embeddings v4 - Document embeddings
    """

    # Model configuration (legacy single-service)
    model: str = "mistral-nemo-12b-instruct-128k"
    model_id: str = "mistral-nemo-12b-instruct-128k"
    base_url: str = "http://10.10.0.87:8080/v1"

    # Multi-service endpoints (3-service architecture)
    instruct_url: str = "http://10.10.0.87:8080/v1"
    instruct_model: str = "mistral-nemo-12b-instruct-128k"
    thinking_url: str = "http://10.10.0.87:8082/v1"
    thinking_model: str = "qwen-thinking-256k"
    embeddings_url: str = "http://10.10.0.87:8081/v1"
    embeddings_model: str = "jina-embeddings-v4"

    # Context limits (IBM Granite 128K context)
    max_model_len: int = 131072
    max_prompt_tokens: int = 120000
    max_completion_tokens: int = 4096

    # GPU configuration
    gpu_memory_utilization: float = 0.85
    tensor_parallel_size: int = 1

    # Performance optimizations
    enable_prefix_caching: bool = True
    enable_chunked_prefill: bool = True
    kv_cache_dtype: str = "auto"

    # Batching configuration
    max_num_seqs: int = 256
    max_num_batched_tokens: int = 16384

    # Reproducibility (CRITICAL)
    seed: int = 42
    default_temperature: float = 0.0

    # HTTP fallback configuration
    http_timeout: int = 1800
    http_max_retries: int = 3

    # Token estimation
    chars_per_token: float = 4.0
    use_accurate_tokenizer: bool = False

    # GPU monitoring
    enable_gpu_monitoring: bool = True
    gpu_memory_threshold: float = 0.90
    gpu_id: int = 0

    # Logging
    disable_log_stats: bool = False

    @classmethod
    def from_settings(cls, settings=None) -> "VLLMConfig":
        """
        Create VLLMConfig from centralized settings.

        Args:
            settings: EntityExtractionServiceSettings instance (or None to load from get_settings())

        Returns:
            VLLMConfig initialized with centralized configuration values
        """
        if settings is None:
            from src.core.config import get_settings
            settings = get_settings()

        vllm = settings.vllm_direct

        # Multi-service URLs (load from environment or use defaults)
        import os
        instruct_url = os.getenv("VLLM_INSTRUCT_URL", "http://10.10.0.87:8080/v1")
        instruct_model = os.getenv("VLLM_INSTRUCT_MODEL", "qwen-instruct-384k")
        thinking_url = os.getenv("VLLM_THINKING_URL", "http://10.10.0.87:8082/v1")
        thinking_model = os.getenv("VLLM_THINKING_MODEL", "qwen-thinking-256k")
        embeddings_url = os.getenv("VLLM_EMBEDDINGS_URL", "http://10.10.0.87:8081/v1")
        embeddings_model = os.getenv("VLLM_EMBEDDINGS_MODEL", "jina-embeddings-v4")

        return cls(
            # Model configuration (legacy)
            model=vllm.vllm_model_name,
            model_id=vllm.vllm_model_name,
            base_url=f"http://{vllm.vllm_host}:{vllm.vllm_port}/v1",  # FIXED: Add /v1 for OpenAI-compatible API

            # Multi-service endpoints
            instruct_url=instruct_url,
            instruct_model=instruct_model,
            thinking_url=thinking_url,
            thinking_model=thinking_model,
            embeddings_url=embeddings_url,
            embeddings_model=embeddings_model,

            # Context limits
            max_model_len=vllm.vllm_max_model_len,
            max_prompt_tokens=vllm.vllm_max_model_len - vllm.vllm_max_tokens,
            max_completion_tokens=vllm.vllm_max_tokens,

            # GPU configuration
            gpu_memory_utilization=vllm.vllm_gpu_memory_utilization,
            tensor_parallel_size=vllm.vllm_tensor_parallel_size,  # Multi-GPU support with tensor parallelism

            # Performance optimizations
            enable_prefix_caching=vllm.vllm_enable_prefix_caching,
            enable_chunked_prefill=vllm.vllm_enable_chunked_prefill,
            kv_cache_dtype="auto",

            # Batching configuration
            max_num_seqs=vllm.vllm_max_num_seqs,
            max_num_batched_tokens=vllm.vllm_max_num_batched_tokens,

            # Reproducibility
            seed=vllm.vllm_seed,
            default_temperature=vllm.vllm_temperature,

            # HTTP fallback configuration
            http_timeout=vllm.vllm_timeout_seconds,
            http_max_retries=vllm.vllm_max_retries,

            # Token estimation
            chars_per_token=vllm.vllm_chars_per_token,
            use_accurate_tokenizer=False,

            # GPU monitoring
            enable_gpu_monitoring=vllm.vllm_enable_gpu_monitoring,
            gpu_memory_threshold=vllm.vllm_gpu_memory_threshold,
            gpu_id=vllm.vllm_gpu_id,

            # Logging
            disable_log_stats=False
        )


@dataclass
class VLLMRequest:
    """
    Request for vLLM generation.

    Note: Default values pulled from centralized config are shown in from_config().
    Direct instantiation uses hardcoded fallback values for backwards compatibility.
    """

    messages: List[Dict[str, str]]
    max_tokens: int = 4096  # Fallback (use from_config() for centralized value)
    temperature: float = 0.0  # Fallback (use from_config() for centralized value)
    top_p: float = 1.0
    top_k: int = -1
    seed: Optional[int] = 42  # Fallback (use from_config() for centralized value)
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop: Optional[List[str]] = None
    stream: bool = False
    response_format: Optional[Dict[str, Any]] = None  # Support JSON mode
    extra_body: Optional[Dict[str, Any]] = None  # vLLM-specific params (guided_json, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(
        cls,
        messages: List[Dict[str, str]],
        settings=None,
        **kwargs
    ) -> "VLLMRequest":
        """
        Create VLLMRequest with defaults from centralized config.

        Args:
            messages: Chat messages
            settings: EntityExtractionServiceSettings instance (or None to load from get_settings())
            **kwargs: Override any default parameter

        Returns:
            VLLMRequest with centralized config defaults
        """
        if settings is None:
            from src.core.config import get_settings
            settings = get_settings()

        vllm = settings.vllm_direct

        # Build with centralized defaults
        params = {
            "messages": messages,
            "max_tokens": vllm.vllm_max_tokens,
            "temperature": vllm.vllm_temperature,
            "top_p": vllm.vllm_top_p,
            "top_k": vllm.vllm_top_k,
            "seed": vllm.vllm_seed,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
        }

        # Apply any overrides from kwargs
        params.update(kwargs)

        return cls(**params)

    def to_prompt_string(self) -> str:
        """Convert messages to single prompt string."""
        parts = []
        for msg in self.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant:")
        return "\n".join(parts)

    def estimate_prompt_length(self) -> int:
        """Estimate prompt length in characters."""
        return sum(len(msg.get("content", "")) for msg in self.messages)


@dataclass
class VLLMUsage:
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }


@dataclass
class VLLMResponse:
    """Response from vLLM generation."""

    content: str
    model: str
    usage: VLLMUsage
    finish_reason: str
    response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VLLMResponse":
        """Create VLLMResponse from dictionary."""
        usage_data = data.get("usage", {})
        usage = VLLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )

        return cls(
            content=data.get("content", ""),
            model=data.get("model", ""),
            usage=usage,
            finish_reason=data.get("finish_reason", "stop"),
            response_time_ms=data.get("response_time_ms", 0.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class ModelStatus:
    """Model loading and health status."""

    status: str  # "not_loaded", "loading", "ready", "error"
    model_name: Optional[str] = None
    initialization_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    last_request_time: Optional[str] = None

    def is_ready(self) -> bool:
        return self.status == "ready"


@dataclass
class ClientStats:
    """Performance statistics for vLLM client."""

    requests_processed: int = 0
    batch_requests_processed: int = 0
    total_tokens_generated: int = 0
    total_processing_time_ms: float = 0.0
    average_response_time_ms: float = 0.0
    errors_encountered: int = 0
    successful_generations: int = 0
    cache_hits: int = 0
    context_overflows: int = 0
    gpu_memory_alerts: int = 0
    http_fallback_count: int = 0
    last_request_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_processed": self.requests_processed,
            "batch_requests_processed": self.batch_requests_processed,
            "total_tokens_generated": self.total_tokens_generated,
            "total_processing_time_ms": self.total_processing_time_ms,
            "average_response_time_ms": self.average_response_time_ms,
            "errors_encountered": self.errors_encountered,
            "successful_generations": self.successful_generations,
            "cache_hits": self.cache_hits,
            "context_overflows": self.context_overflows,
            "gpu_memory_alerts": self.gpu_memory_alerts,
            "http_fallback_count": self.http_fallback_count,
            "last_request_time": self.last_request_time
        }
