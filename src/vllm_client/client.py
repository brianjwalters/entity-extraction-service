"""
vLLM Client Interface and Implementations.

Provides abstract interface and concrete implementations:
- DirectVLLMClient: Direct Python API (primary)
- HTTPVLLMClient: HTTP API (fallback)
"""

import asyncio
import logging
import time
import concurrent.futures
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from .models import (
    VLLMConfig,
    VLLMRequest,
    VLLMResponse,
    VLLMUsage,
    ModelStatus,
    ClientStats,
    VLLMClientType
)
from .exceptions import (
    ModelNotLoadedError,
    GenerationError,
    ContextOverflowError,
    GPUMemoryError,
    ConnectionError as VLLMConnectionError
)
from .token_estimator import TokenEstimator
from .gpu_monitor import GPUMonitor

logger = logging.getLogger(__name__)


class VLLMClientInterface(ABC):
    """
    Abstract interface for vLLM clients.

    This interface ensures both HTTP and Direct API clients
    provide identical functionality, enabling seamless switching.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Initialize/connect to vLLM service."""
        pass

    @abstractmethod
    async def generate_chat_completion(self, request: VLLMRequest) -> VLLMResponse:
        """Generate single completion."""
        pass

    @abstractmethod
    async def generate_batch(self, requests: List[VLLMRequest]) -> List[VLLMResponse]:
        """Generate batch of completions."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if client is ready for inference."""
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """Get performance statistics."""
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass


class DirectVLLMClient(VLLMClientInterface):
    """
    Direct vLLM Python API client - optimized for performance.

    Key Features:
    - Zero network overhead (direct Python API)
    - Native batch processing support
    - Proactive token estimation
    - GPU memory monitoring
    - Reproducibility enforcement (temperature=0.0, seed=42)
    """

    def __init__(self, config: Optional[VLLMConfig] = None):
        """
        Initialize Direct vLLM client.

        Args:
            config: VLLMConfig instance (if None, loads from centralized settings)
        """
        # Load from centralized config if not provided
        if config is None:
            from src.core.config import get_settings
            settings = get_settings()
            config = VLLMConfig.from_settings(settings)

        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize utilities (now using config.gpu_id from centralized settings)
        self.token_estimator = TokenEstimator(self.config)
        self.gpu_monitor = GPUMonitor(
            gpu_id=self.config.gpu_id,  # Now from centralized config
            memory_threshold=self.config.gpu_memory_threshold
        ) if self.config.enable_gpu_monitoring else None

        # vLLM engine (lazy initialization)
        self._llm = None
        self._initialization_lock = asyncio.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="vllm-direct"
        )

        # State tracking
        self._status = ModelStatus(status="not_loaded")
        self._stats = ClientStats()

        self.logger.info(
            f"DirectVLLMClient initialized - Model: {self.config.model}, "
            f"Max context: {self.config.max_model_len:,} tokens"
        )

    async def connect(self) -> bool:
        """
        Initialize vLLM engine.

        Returns:
            bool: True if initialization successful
        """
        if self._status.is_ready():
            self.logger.debug("Direct vLLM client already connected")
            return True

        async with self._initialization_lock:
            # Double-check after acquiring lock
            if self._status.is_ready():
                return True

            try:
                self.logger.info("Initializing Direct vLLM engine...")
                self._status = ModelStatus(status="loading", model_name=self.config.model)
                start_time = time.time()

                # Check GPU memory before initialization
                if self.gpu_monitor:
                    stats = self.gpu_monitor.get_stats()
                    if stats:
                        self.logger.info(f"GPU status: {self.gpu_monitor.get_stats_summary()}")

                # Set CUDA_VISIBLE_DEVICES BEFORE thread pool execution
                # This must happen before any CUDA initialization
                import os
                original_cuda_devices = os.environ.get('CUDA_VISIBLE_DEVICES')

                # Critical: When using CUDA_VISIBLE_DEVICES, we need to:
                # 1. Set CUDA_VISIBLE_DEVICES to the physical GPU we want
                # 2. Tell vLLM to use device 0 (which will be remapped to our target GPU)
                if original_cuda_devices is None:
                    # No prior CUDA_VISIBLE_DEVICES set, so we set it
                    os.environ['CUDA_VISIBLE_DEVICES'] = str(self.config.gpu_id)
                    self.logger.info(f"Set CUDA_VISIBLE_DEVICES={self.config.gpu_id} for GPU isolation")
                    self.logger.info(f"vLLM will see physical GPU {self.config.gpu_id} as CUDA device 0")
                else:
                    # CUDA_VISIBLE_DEVICES already set (e.g., in test script), use it
                    self.logger.info(f"Using existing CUDA_VISIBLE_DEVICES={original_cuda_devices}")
                    self.logger.info(f"vLLM will use CUDA device 0 (which maps to physical GPU {original_cuda_devices})")

                # Initialize LLM in thread pool (blocking operation)
                loop = asyncio.get_event_loop()

                def init_llm():
                    try:
                        from vllm import LLM
                    except ImportError as e:
                        raise ImportError(
                            "vLLM library not found. Install with: pip install vllm"
                        ) from e

                    self.logger.info(f"Initializing vLLM on GPU {self.config.gpu_id} (CUDA will see it as device 0)")

                    llm = LLM(
                        model=self.config.model,
                        max_model_len=self.config.max_model_len,
                        gpu_memory_utilization=self.config.gpu_memory_utilization,
                        tensor_parallel_size=self.config.tensor_parallel_size,
                        trust_remote_code=True,
                        enable_prefix_caching=self.config.enable_prefix_caching,
                        enable_chunked_prefill=self.config.enable_chunked_prefill,
                        max_num_seqs=self.config.max_num_seqs,
                        max_num_batched_tokens=self.config.max_num_batched_tokens,
                        seed=self.config.seed,
                        disable_log_stats=self.config.disable_log_stats
                    )

                    self.logger.info(f"✅ vLLM initialized successfully on GPU {self.config.gpu_id}")
                    return llm

                try:
                    self._llm = await loop.run_in_executor(self._executor, init_llm)
                except Exception as e:
                    # On error, restore original CUDA_VISIBLE_DEVICES
                    if original_cuda_devices is not None:
                        os.environ['CUDA_VISIBLE_DEVICES'] = original_cuda_devices
                    elif 'CUDA_VISIBLE_DEVICES' in os.environ and original_cuda_devices is None:
                        del os.environ['CUDA_VISIBLE_DEVICES']
                    raise

                # SUCCESS: Keep CUDA_VISIBLE_DEVICES set for future generations
                # Don't restore it - we want to stay on the same GPU
                self.logger.info(f"Keeping CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')} for inference")

                initialization_time = (time.time() - start_time) * 1000
                self._status = ModelStatus(
                    status="ready",
                    model_name=self.config.model,
                    initialization_time_ms=initialization_time
                )

                self.logger.info(
                    f"Direct vLLM engine initialized in {initialization_time:.1f}ms"
                )

                # Warmup with small request
                await self._warmup()

                return True

            except Exception as e:
                error_msg = f"Failed to initialize Direct vLLM engine: {e}"
                self.logger.error(error_msg)
                self._status = ModelStatus(
                    status="error",
                    model_name=self.config.model,
                    error_message=str(e)
                )
                return False

    async def _warmup(self):
        """Warm up the model with a small generation."""
        try:
            # Use from_settings() for centralized warmup config
            from src.core.config import get_settings
            settings = get_settings()

            warmup_request = VLLMRequest(
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=settings.vllm_direct.vllm_warmup_max_tokens,
                temperature=self.config.default_temperature,
                seed=self.config.seed
            )

            if settings.vllm_direct.vllm_warmup_enabled:
                await self.generate_chat_completion(warmup_request)
                self.logger.info("Model warmup completed")
            else:
                self.logger.info("Model warmup disabled in config")

        except Exception as e:
            self.logger.warning(f"Warmup failed (non-critical): {e}")

    def _create_sampling_params(self, request: VLLMRequest):
        """
        Create SamplingParams with reproducibility enforcement and guided JSON support.

        CRITICAL: Always enforces temperature=0.0 and seed=42 for determinism.
        Supports guided_json for structured output when provided in extra_body.

        Guided JSON Implementation:
        - Uses vLLM v0.8.2 GuidedDecodingParams with outlines backend
        - Ensures LLM output matches JSON schema exactly
        - Raises errors on failure (fail-fast approach)
        """
        try:
            from vllm import SamplingParams
        except ImportError:
            raise ImportError("vLLM library not found")

        # Use request temperature if provided, otherwise use default
        # For entity extraction, we need some randomness (temperature > 0) to improve diversity
        temperature = request.temperature if request.temperature is not None else self.config.default_temperature
        seed = request.seed if request.seed is not None else self.config.seed

        if temperature != self.config.default_temperature:
            self.logger.info(
                f"Using request temperature={temperature} (default={self.config.default_temperature}) "
                f"for improved generation diversity"
            )

        # Build sampling params dict
        sampling_params_dict = {
            "n": 1,
            "temperature": temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "seed": seed,
            "max_tokens": request.max_tokens,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "stop": request.stop,
            "skip_special_tokens": True
        }

        # Add guided_json if provided in extra_body (for structured output)
        if request.extra_body and "guided_json" in request.extra_body:
            guided_json_schema = request.extra_body["guided_json"]
            self.logger.info(f"Using guided JSON for structured output (backend: outlines)")

            try:
                from vllm.sampling_params import GuidedDecodingParams
                import json

                # Convert schema dict to JSON string (vLLM requires string format)
                if isinstance(guided_json_schema, dict):
                    json_schema_str = json.dumps(guided_json_schema)
                    self.logger.debug(f"Converted schema dict to JSON string ({len(json_schema_str)} chars)")
                else:
                    json_schema_str = guided_json_schema
                    self.logger.debug(f"Using provided JSON schema string ({len(json_schema_str)} chars)")

                # Create GuidedDecodingParams with outlines backend
                # outlines is the most stable backend for JSON schema constraints
                guided_decoding = GuidedDecodingParams(
                    backend="outlines",  # outlines is most stable for JSON schemas
                    json=json_schema_str
                )

                sampling_params_dict["guided_decoding"] = guided_decoding
                self.logger.info("✅ Guided JSON decoding enabled - LLM output will match schema exactly")

            except ImportError as e:
                self.logger.error(f"❌ GuidedDecodingParams not available: {e}")
                self.logger.error("Install vLLM with: pip install vllm")
                raise RuntimeError("vLLM library required for guided JSON decoding") from e
            except Exception as e:
                self.logger.error(f"❌ Failed to create GuidedDecodingParams: {e}")
                raise

        return SamplingParams(**sampling_params_dict)

    async def generate_chat_completion(self, request: VLLMRequest) -> VLLMResponse:
        """
        Generate completion using vLLM direct API.

        Args:
            request: VLLMRequest with messages and parameters

        Returns:
            VLLMResponse: Generated response

        Raises:
            ModelNotLoadedError: If engine is not ready
            ContextOverflowError: If prompt exceeds context limit
            GenerationError: If generation fails
        """
        if not self.is_ready():
            success = await self.connect()
            if not success:
                raise ModelNotLoadedError("DirectVLLMEngine not initialized")

        start_time = time.time()

        try:
            # Convert messages to prompt
            prompt = request.to_prompt_string()

            # Token estimation and validation
            try:
                prompt_tokens, adjusted_max_tokens = self.token_estimator.estimate_prompt_tokens(
                    prompt, request.max_tokens
                )
                if adjusted_max_tokens != request.max_tokens:
                    self.logger.warning(
                        f"Adjusted max_tokens from {request.max_tokens} to {adjusted_max_tokens} "
                        f"due to context limit"
                    )
                    request.max_tokens = adjusted_max_tokens
            except ContextOverflowError as e:
                self._stats.context_overflows += 1
                raise

            # Check GPU memory if monitoring enabled
            if self.gpu_monitor:
                stats = self.gpu_monitor.get_stats()
                if stats and stats.memory_utilization_percent > 95:
                    self._stats.gpu_memory_alerts += 1
                    self.logger.warning(
                        f"GPU memory critical: {stats.memory_utilization_percent:.1f}% "
                        f"- Generation may be slower"
                    )

            # Create sampling parameters
            sampling_params = self._create_sampling_params(request)

            # Log request info
            self.logger.info(
                f"Direct API request: ~{prompt_tokens:,} tokens "
                f"(max completion: {request.max_tokens})"
            )

            # Generate using synchronous LLM in thread pool
            generation_start = time.time()

            # Run generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def generate_sync():
                try:
                    from vllm.utils import random_uuid
                except ImportError:
                    pass
                return self._llm.generate([prompt], sampling_params)

            # Execute in thread pool
            outputs = await loop.run_in_executor(self._executor, generate_sync)

            generation_time = (time.time() - generation_start) * 1000
            total_time = (time.time() - start_time) * 1000

            # Extract response details from first (and only) output
            final_output = outputs[0]
            output = final_output.outputs[0]
            generated_text = output.text
            finish_reason = output.finish_reason

            # Calculate token usage
            actual_prompt_tokens = len(final_output.prompt_token_ids)
            completion_tokens = len(output.token_ids)
            total_tokens = actual_prompt_tokens + completion_tokens

            # Update statistics
            self._stats.requests_processed += 1
            self._stats.successful_generations += 1
            self._stats.total_tokens_generated += completion_tokens
            self._stats.total_processing_time_ms += total_time
            self._stats.average_response_time_ms = (
                self._stats.total_processing_time_ms / self._stats.requests_processed
            )
            self._stats.last_request_time = datetime.now().isoformat()

            # Log performance
            tokens_per_second = completion_tokens / (generation_time / 1000) if generation_time > 0 else 0
            self.logger.info(
                f"Generation completed: {completion_tokens} tokens in {generation_time:.1f}ms "
                f"({tokens_per_second:.1f} tokens/sec)"
            )

            # Create response
            usage = VLLMUsage(
                prompt_tokens=actual_prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )

            response = VLLMResponse(
                content=generated_text,
                model=self.config.model,
                usage=usage,
                finish_reason=finish_reason,
                response_time_ms=total_time,
                metadata={
                    "api_type": "direct_python",
                    "generation_time_ms": generation_time,
                    "tokens_per_second": tokens_per_second,
                    "estimated_prompt_tokens": prompt_tokens,
                    "actual_prompt_tokens": actual_prompt_tokens
                }
            )

            return response

        except (ModelNotLoadedError, ContextOverflowError):
            # Re-raise these without wrapping
            raise

        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            self._stats.errors_encountered += 1

            self.logger.error(f"Generation failed after {error_time:.1f}ms: {str(e)}")

            raise GenerationError(
                f"DirectVLLM generation failed: {str(e)}",
                generation_attempt=1,
                max_retries=1,
                original_error=e
            )

    async def generate_batch(self, requests: List[VLLMRequest]) -> List[VLLMResponse]:
        """
        Generate completions for multiple requests using native batching.

        Args:
            requests: List of VLLMRequest objects

        Returns:
            List[VLLMResponse]: Generated responses in same order as requests
        """
        if not self.is_ready():
            success = await self.connect()
            if not success:
                raise ModelNotLoadedError("DirectVLLMEngine not initialized")

        if not requests:
            return []

        start_time = time.time()

        try:
            # Convert all requests to prompts and sampling params
            prompts = []
            sampling_params_list = []

            for request in requests:
                prompt = request.to_prompt_string()

                # Validate each request
                try:
                    self.token_estimator.validate_request(prompt, request.max_tokens)
                except ContextOverflowError as e:
                    self.logger.error(f"Request in batch exceeds context: {e}")
                    self._stats.context_overflows += 1
                    raise

                sampling_params = self._create_sampling_params(request)

                prompts.append(prompt)
                sampling_params_list.append(sampling_params)

            self.logger.info(f"Batch generation: {len(requests)} requests")

            # Process batch using native vLLM batching
            batch_start = time.time()

            # Run batch generation in thread pool
            loop = asyncio.get_event_loop()

            def generate_batch_sync():
                # vLLM handles batching internally for optimal performance
                # Use first sampling params (assuming all are the same for batch)
                return self._llm.generate(prompts, sampling_params_list[0])

            # Execute batch in thread pool
            outputs = await loop.run_in_executor(self._executor, generate_batch_sync)

            batch_time = (time.time() - batch_start) * 1000

            # Process all outputs
            responses = []
            for i, final_output in enumerate(outputs):
                # Extract response details
                output = final_output.outputs[0]
                generated_text = output.text
                finish_reason = output.finish_reason

                # Calculate token usage
                prompt_tokens = len(final_output.prompt_token_ids)
                completion_tokens = len(output.token_ids)
                total_tokens = prompt_tokens + completion_tokens

                # Create response
                usage = VLLMUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )

                response = VLLMResponse(
                    content=generated_text,
                    model=self.config.model,
                    usage=usage,
                    finish_reason=finish_reason,
                    response_time_ms=batch_time / len(outputs),
                    metadata={
                        "api_type": "direct_python_batch",
                        "batch_position": i,
                        "batch_size": len(outputs)
                    }
                )

                responses.append(response)

            # Update batch statistics
            total_time = (time.time() - start_time) * 1000
            total_completion_tokens = sum(r.usage.completion_tokens for r in responses)

            self._stats.requests_processed += len(requests)
            self._stats.batch_requests_processed += 1
            self._stats.successful_generations += len(responses)
            self._stats.total_tokens_generated += total_completion_tokens

            batch_tokens_per_second = total_completion_tokens / (batch_time / 1000) if batch_time > 0 else 0

            self.logger.info(
                f"Batch completed: {len(responses)} responses in {total_time:.1f}ms "
                f"({batch_tokens_per_second:.1f} tokens/sec total)"
            )

            return responses

        except (ModelNotLoadedError, ContextOverflowError):
            raise

        except Exception as e:
            self._stats.errors_encountered += 1
            self.logger.error(f"Batch generation failed: {str(e)}")

            raise GenerationError(
                f"DirectVLLM batch generation failed: {str(e)}",
                generation_attempt=1,
                max_retries=1,
                original_error=e
            )

    def is_ready(self) -> bool:
        """Check if the engine is ready for inference."""
        return self._status.is_ready() and self._llm is not None

    def get_stats(self) -> dict:
        """Get performance statistics."""
        stats_dict = self._stats.to_dict()
        stats_dict["status"] = self._status.status
        stats_dict["model"] = self._status.model_name
        stats_dict["token_estimator"] = self.token_estimator.get_stats()

        if self.gpu_monitor:
            gpu_stats = self.gpu_monitor.get_stats()
            if gpu_stats:
                stats_dict["gpu"] = gpu_stats.to_dict()

        return stats_dict

    async def close(self):
        """Clean up resources."""
        if self._llm:
            try:
                self._llm = None
                self.logger.info("DirectVLLMEngine closed")
            except Exception as e:
                self.logger.warning(f"Error during DirectVLLMEngine cleanup: {e}")

        # Shutdown executor
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=False)

        self._status = ModelStatus(status="not_loaded")


class HTTPVLLMClient(VLLMClientInterface):
    """
    HTTP vLLM client with multi-service support.

    Uses httpx to make HTTP calls to vLLM's OpenAI-compatible API with service routing:
    - INSTRUCT: Port 8080 - Entity extraction (fast)
    - THINKING: Port 8082 - Relationship extraction (complex reasoning)
    - EMBEDDINGS: Port 8081 - Document embeddings
    """

    def __init__(
        self,
        config: Optional[VLLMConfig] = None,
        service_type: Optional["VLLMServiceType"] = None
    ):
        """
        Initialize HTTP vLLM client with service routing.

        Args:
            config: VLLMConfig instance (if None, loads from centralized settings)
            service_type: Service type for routing (INSTRUCT, THINKING, EMBEDDINGS)
        """
        # Load from centralized config if not provided
        if config is None:
            from src.core.config import get_settings
            settings = get_settings()
            config = VLLMConfig.from_settings(settings)

        self.config = config
        self.service_type = service_type
        self.logger = logging.getLogger(__name__)

        # Determine base URL and model based on service type
        if service_type:
            from .models import VLLMServiceType
            self.base_url, self.model_name = self._get_service_endpoint(service_type)
        else:
            # Default to instruct service for backward compatibility
            self.base_url = self.config.base_url
            self.model_name = self.config.model_id

        # Create httpx client
        import httpx
        self._httpx_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.http_timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

        # State tracking
        self._is_ready = False
        self._stats = ClientStats()

        self.logger.info(
            f"HTTPVLLMClient initialized - Service: {service_type or 'default'}, "
            f"URL: {self.base_url}, Model: {self.model_name}"
        )

    def _get_service_endpoint(self, service_type: "VLLMServiceType") -> tuple[str, str]:
        """
        Get endpoint and model for service type.

        Args:
            service_type: Service type enum

        Returns:
            Tuple of (base_url, model_name)
        """
        from .models import VLLMServiceType

        if service_type == VLLMServiceType.INSTRUCT:
            return self.config.instruct_url, self.config.instruct_model
        elif service_type == VLLMServiceType.THINKING:
            return self.config.thinking_url, self.config.thinking_model
        elif service_type == VLLMServiceType.EMBEDDINGS:
            return self.config.embeddings_url, self.config.embeddings_model
        else:
            # Fallback to legacy base_url
            self.logger.warning(f"Unknown service type: {service_type}, using default")
            return self.config.base_url, self.config.model_id

    async def connect(self) -> bool:
        """Connect to vLLM HTTP server and verify it's ready."""
        if self._is_ready:
            self.logger.debug("Already connected to vLLM HTTP server")
            return True

        try:
            self.logger.info(f"Connecting to vLLM server at {self.base_url}...")

            # Health check using /v1/models endpoint (OpenAI-compatible)
            response = await self._httpx_client.get(f"{self.base_url}/models")

            if response.status_code == 200:
                models_data = response.json()
                if models_data.get("data"):
                    model_info = models_data["data"][0]
                    self.logger.info(f"Connected to model: {model_info.get('id', 'unknown')}")

                self._is_ready = True
                self.logger.info(f"Successfully connected to vLLM server at {self.base_url}")
                return True
            else:
                self.logger.error(f"Server returned {response.status_code}: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to connect to vLLM server: {str(e)}")
            return False

    async def generate_chat_completion(self, request: VLLMRequest) -> VLLMResponse:
        """Generate completion via HTTP API."""
        if not self._is_ready:
            success = await self.connect()
            if not success:
                from .exceptions import ModelNotLoadedError
                raise ModelNotLoadedError(f"vLLM server not available at {self.base_url}")

        start_time = time.time()

        try:
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "presence_penalty": request.presence_penalty,
                "frequency_penalty": request.frequency_penalty,
                "stream": request.stream
            }

            # Add stop sequences if provided
            if request.stop:
                payload["stop"] = request.stop

            # Add extra_body parameters (guided_json, etc.)
            if request.extra_body:
                payload.update(request.extra_body)
                self.logger.info(f"Added extra_body parameters: {list(request.extra_body.keys())}")

            self.logger.debug(f"Sending HTTP request to {self.base_url}/chat/completions")

            # Make HTTP request to vLLM
            http_response = await self._httpx_client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )

            if http_response.status_code != 200:
                from .exceptions import GenerationError
                raise GenerationError(
                    f"Server returned {http_response.status_code}: {http_response.text}",
                    generation_attempt=1,
                    max_retries=1
                )

            # Parse response
            response_data = http_response.json()
            choices = response_data.get("choices", [])
            if not choices:
                from .exceptions import GenerationError
                raise GenerationError("No choices in response", generation_attempt=1, max_retries=1)

            content = choices[0].get("message", {}).get("content", "")
            response_time = (time.time() - start_time) * 1000

            # Extract usage information
            usage_data = response_data.get("usage", {})
            usage = VLLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0)
            )

            # Update statistics
            self._stats.requests_processed += 1
            self._stats.successful_generations += 1
            self._stats.total_tokens_generated += usage.completion_tokens
            self._stats.total_processing_time_ms += response_time
            self._stats.average_response_time_ms = (
                self._stats.total_processing_time_ms / self._stats.requests_processed
            )
            self._stats.last_request_time = datetime.now().isoformat()

            self.logger.info(f"Generation completed in {response_time:.1f}ms")

            return VLLMResponse(
                content=content,
                model=response_data.get("model", self.model_name),
                usage=usage,
                finish_reason=choices[0].get("finish_reason", "stop"),
                response_time_ms=response_time,
                metadata={"api_type": "http", "service": self.service_type or "default"}
            )

        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            self._stats.errors_encountered += 1
            self.logger.error(f"Generation failed after {error_time:.1f}ms: {str(e)}")
            raise

    async def generate_batch(self, requests: List[VLLMRequest]) -> List[VLLMResponse]:
        """Generate batch via sequential HTTP calls (no native batching)."""
        responses = []
        for request in requests:
            response = await self.generate_chat_completion(request)
            responses.append(response)
        self._stats.batch_requests_processed += 1
        return responses

    def is_ready(self) -> bool:
        """Check if HTTP client is ready."""
        return self._is_ready

    def get_stats(self) -> dict:
        """Get HTTP client statistics."""
        stats_dict = self._stats.to_dict()
        stats_dict["service_type"] = self.service_type or "default"
        stats_dict["base_url"] = self.base_url
        stats_dict["model_name"] = self.model_name
        return stats_dict

    async def close(self):
        """Close HTTP client."""
        if self._httpx_client:
            await self._httpx_client.aclose()
            self._is_ready = False
            self.logger.info("HTTPVLLMClient closed")
