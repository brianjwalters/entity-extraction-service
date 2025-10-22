"""
Throttling wrapper for vLLM client to prevent service overload.

This module provides a wrapper around VLLMLocalClient that adds:
- Request throttling and rate limiting
- Circuit breaker pattern for resilience
- Adaptive throttling based on response times
- Request queue management
- Comprehensive performance monitoring

The wrapper is transparent - existing code continues to work unchanged.
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any, Deque, Union
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import statistics

from src.client.vllm_direct_client import (
    DirectVLLMEngine, 
    VLLMRequest, 
    VLLMResponse,
    GenerationError
)
# Compatibility alias
VLLMLocalClient = DirectVLLMEngine
from src.core.config import get_config

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit is tripped, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ThrottlingStats:
    """Statistics for throttling behavior."""
    total_requests: int = 0
    throttled_requests: int = 0
    rejected_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opens: int = 0
    average_response_time_ms: float = 0.0
    current_rate: float = 0.0  # requests per second
    queue_size: int = 0
    semaphore_available: int = 0
    circuit_state: str = CircuitState.CLOSED.value
    last_circuit_open: Optional[str] = None
    last_circuit_close: Optional[str] = None
    adaptive_delay_ms: float = 0.0
    

@dataclass
class RequestHistoryEntry:
    """Entry in request history for rate limiting."""
    timestamp: float
    response_time_ms: float
    success: bool
    error: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        half_open_requests: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_success_count = 0
        self.state_change_callbacks = []
        
    def call_succeeded(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_success_count += 1
            if self.half_open_success_count >= self.half_open_requests:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset on success
    
    def call_failed(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def can_execute(self) -> bool:
        """Check if circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
                return True
            return False
        else:  # HALF_OPEN
            return self.half_open_success_count < self.half_open_requests
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to try recovery."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.half_open_success_count = 0
        logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")
        self._notify_state_change()
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_success_count = 0
        logger.info("Circuit breaker HALF_OPEN - testing recovery")
        self._notify_state_change()
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_success_count = 0
        logger.info("Circuit breaker CLOSED - service recovered")
        self._notify_state_change()
    
    def _notify_state_change(self):
        """Notify callbacks of state change."""
        for callback in self.state_change_callbacks:
            try:
                callback(self.state)
            except Exception as e:
                logger.error(f"Error in circuit breaker callback: {e}")
    
    def add_state_change_callback(self, callback):
        """Add callback for state changes."""
        self.state_change_callbacks.append(callback)
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state


class AdaptiveThrottler:
    """Adaptive throttling based on response times."""
    
    def __init__(
        self,
        target_response_time_ms: float = 1000.0,
        min_delay_ms: float = 0.0,
        max_delay_ms: float = 5000.0,
        adaptation_rate: float = 0.1
    ):
        self.target_response_time_ms = target_response_time_ms
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.adaptation_rate = adaptation_rate
        
        self.current_delay_ms = min_delay_ms
        self.response_times: Deque[float] = deque(maxlen=10)
    
    def record_response_time(self, response_time_ms: float):
        """Record response time and adapt delay."""
        self.response_times.append(response_time_ms)
        self._adapt_delay()
    
    def get_delay_seconds(self) -> float:
        """Get current delay in seconds."""
        return self.current_delay_ms / 1000.0
    
    def _adapt_delay(self):
        """Adapt delay based on recent response times."""
        if len(self.response_times) < 3:
            return
        
        avg_response_time = statistics.mean(self.response_times)
        
        if avg_response_time > self.target_response_time_ms:
            # Increase delay if response times are high
            increase = (avg_response_time - self.target_response_time_ms) * self.adaptation_rate
            self.current_delay_ms = min(
                self.current_delay_ms + increase,
                self.max_delay_ms
            )
        else:
            # Decrease delay if response times are low
            decrease = (self.target_response_time_ms - avg_response_time) * self.adaptation_rate * 0.5
            self.current_delay_ms = max(
                self.current_delay_ms - decrease,
                self.min_delay_ms
            )
        
        logger.debug(f"Adaptive delay adjusted to {self.current_delay_ms:.1f}ms (avg response: {avg_response_time:.1f}ms)")


class ThrottledVLLMClient:
    """
    Throttling wrapper for VLLMLocalClient.
    
    This wrapper adds comprehensive throttling capabilities without
    modifying the underlying VLLMLocalClient implementation.
    """
    
    def __init__(
        self,
        base_client: VLLMLocalClient,
        config_override: Optional[Union[Dict[str, Any], "RuntimeConfig"]] = None
    ):
        """
        Initialize throttled wrapper.
        
        Args:
            base_client: The VLLMLocalClient instance to wrap
            config_override: Optional configuration overrides
        """
        self.base_client = base_client
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load configuration
        self.config = get_settings()
        
        # Apply any overrides
        if config_override:
            self._apply_config_overrides(config_override)
        
        # Initialize throttling components
        self._init_semaphore()
        self._init_rate_limiter()
        self._init_circuit_breaker()
        self._init_adaptive_throttler()
        self._init_statistics()
        
        # Request queue for rate limiting
        self.request_queue: Deque[asyncio.Event] = deque()
        self.queue_processor_task = None
        
        self.logger.info(
            f"ThrottledVLLMClient initialized: "
            f"concurrent_limit={self.max_concurrent}, "
            f"rate_limit={self.requests_per_minute} req/min, "
            f"circuit_breaker={'enabled' if self.circuit_breaker_enabled else 'disabled'}"
        )
    
    def _apply_config_overrides(self, overrides):
        """Apply configuration overrides."""
        # Handle both dictionary and RuntimeConfig objects
        if hasattr(overrides, 'vllm'):
            # It's a RuntimeConfig object, use its vllm settings
            if hasattr(overrides.vllm, '__dict__'):
                override_dict = overrides.vllm.__dict__
            else:
                override_dict = {}
        elif isinstance(overrides, dict):
            # It's already a dictionary
            override_dict = overrides
        else:
            # Unknown type, skip
            self.logger.warning(f"Unknown config override type: {type(overrides)}")
            return
            
        for key, value in override_dict.items():
            if hasattr(self.config.vllm, key):
                setattr(self.config.vllm, key, value)
                self.logger.info(f"Config override: {key}={value}")
    
    def _init_semaphore(self):
        """Initialize request semaphore for concurrent limiting."""
        self.max_concurrent = self.config.vllm.max_concurrent_requests
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.logger.debug(f"Request semaphore initialized with limit: {self.max_concurrent}")
    
    def _init_rate_limiter(self):
        """Initialize rate limiting."""
        self.requests_per_minute = self.config.vllm.requests_per_minute
        self.request_delay_ms = self.config.vllm.request_delay_ms
        self.request_history: Deque[RequestHistoryEntry] = deque()
        self.rate_limiter_lock = asyncio.Lock()
        self.logger.debug(f"Rate limiter initialized: {self.requests_per_minute} req/min")
    
    def _init_circuit_breaker(self):
        """Initialize circuit breaker."""
        self.circuit_breaker_enabled = self.config.vllm.enable_circuit_breaker
        
        if self.circuit_breaker_enabled:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=self.config.vllm.failure_threshold,
                recovery_timeout=self.config.vllm.recovery_timeout_seconds,
                half_open_requests=self.config.vllm.half_open_requests
            )
            # Add callback to update stats
            self.circuit_breaker.add_state_change_callback(self._on_circuit_state_change)
            self.logger.debug("Circuit breaker initialized and enabled")
        else:
            self.circuit_breaker = None
            self.logger.debug("Circuit breaker disabled")
    
    def _init_adaptive_throttler(self):
        """Initialize adaptive throttling."""
        # Use configurable target response time (default 1000ms)
        target_time = getattr(self.config.vllm, 'target_response_time_ms', 1000.0)
        
        self.adaptive_throttler = AdaptiveThrottler(
            target_response_time_ms=target_time,
            min_delay_ms=self.config.vllm.request_delay_ms,
            max_delay_ms=self.config.vllm.request_delay_ms * 10  # Max 10x configured delay
        )
        self.logger.debug(f"Adaptive throttler initialized with target: {target_time}ms")
    
    def _init_statistics(self):
        """Initialize statistics tracking."""
        self.stats = ThrottlingStats(
            semaphore_available=self.max_concurrent
        )
    
    def _on_circuit_state_change(self, new_state: CircuitState):
        """Handle circuit breaker state changes."""
        self.stats.circuit_state = new_state.value
        
        if new_state == CircuitState.OPEN:
            self.stats.circuit_opens += 1
            self.stats.last_circuit_open = datetime.now().isoformat()
        elif new_state == CircuitState.CLOSED:
            self.stats.last_circuit_close = datetime.now().isoformat()
    
    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        async with self.rate_limiter_lock:
            # Clean old entries (older than 1 minute)
            cutoff_time = time.time() - 60
            while self.request_history and self.request_history[0].timestamp < cutoff_time:
                self.request_history.popleft()
            
            # Check if we're at the rate limit
            if len(self.request_history) >= self.requests_per_minute:
                # Calculate how long to wait
                oldest_request = self.request_history[0]
                wait_time = 60 - (time.time() - oldest_request.timestamp)
                
                if wait_time > 0:
                    self.logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                    self.stats.throttled_requests += 1
                    await asyncio.sleep(wait_time)
                    
                    # Clean again after waiting
                    cutoff_time = time.time() - 60
                    while self.request_history and self.request_history[0].timestamp < cutoff_time:
                        self.request_history.popleft()
    
    async def _apply_request_delay(self):
        """Apply configured request delay."""
        base_delay = self.config.vllm.request_delay_ms / 1000.0
        adaptive_delay = self.adaptive_throttler.get_delay_seconds()
        
        # Use the maximum of base and adaptive delay
        total_delay = max(base_delay, adaptive_delay)
        
        if total_delay > 0:
            await asyncio.sleep(total_delay)
        
        self.stats.adaptive_delay_ms = adaptive_delay * 1000
    
    async def generate_chat_completion(self, request: VLLMRequest) -> VLLMResponse:
        """
        Generate completion with throttling.
        
        This method wraps the base client's generate_chat_completion
        with comprehensive throttling logic.
        
        Args:
            request: VLLMRequest with messages and parameters
            
        Returns:
            VLLMResponse: Generated response
            
        Raises:
            ModelNotLoadedError: If model is not ready
            GenerationError: If generation fails or circuit is open
        """
        self.stats.total_requests += 1
        
        # Check circuit breaker first
        if self.circuit_breaker_enabled and self.circuit_breaker:
            if not self.circuit_breaker.can_execute():
                self.stats.rejected_requests += 1
                raise GenerationError(
                    "Circuit breaker is OPEN - service unavailable",
                    generation_attempt=0,
                    max_retries=0,
                    timeout_occurred=False,
                    server_error=True
                )
        
        # Wait for rate limit if necessary
        await self._wait_for_rate_limit()
        
        # Apply request delay (base + adaptive)
        await self._apply_request_delay()
        
        # Acquire semaphore for concurrent limiting
        async with self.semaphore:
            self.stats.semaphore_available = self.semaphore._value
            self.stats.queue_size = len(self.request_queue)
            
            start_time = time.time()
            success = False
            error_msg = None
            
            try:
                # Call the base client
                response = await self.base_client.generate_chat_completion(request)
                
                # Record success
                success = True
                self.stats.successful_requests += 1
                
                # Update circuit breaker
                if self.circuit_breaker_enabled and self.circuit_breaker:
                    self.circuit_breaker.call_succeeded()
                
                return response
                
            except Exception as e:
                # Record failure
                self.stats.failed_requests += 1
                error_msg = str(e)
                
                # Update circuit breaker
                if self.circuit_breaker_enabled and self.circuit_breaker:
                    self.circuit_breaker.call_failed()
                
                # Re-raise the exception
                raise
                
            finally:
                # Calculate response time
                response_time_ms = (time.time() - start_time) * 1000
                
                # Update adaptive throttler
                self.adaptive_throttler.record_response_time(response_time_ms)
                
                # Record in history for rate limiting
                entry = RequestHistoryEntry(
                    timestamp=time.time(),
                    response_time_ms=response_time_ms,
                    success=success,
                    error=error_msg
                )
                self.request_history.append(entry)
                
                # Update statistics
                self._update_statistics(response_time_ms)
                
                # Update semaphore availability
                self.stats.semaphore_available = self.semaphore._value
    
    def _update_statistics(self, response_time_ms: float):
        """Update internal statistics."""
        # Calculate average response time
        if self.stats.successful_requests > 0:
            # Exponential moving average
            alpha = 0.1  # Smoothing factor
            if self.stats.average_response_time_ms == 0:
                self.stats.average_response_time_ms = response_time_ms
            else:
                self.stats.average_response_time_ms = (
                    alpha * response_time_ms + 
                    (1 - alpha) * self.stats.average_response_time_ms
                )
        
        # Calculate current request rate
        if len(self.request_history) > 1:
            time_span = self.request_history[-1].timestamp - self.request_history[0].timestamp
            if time_span > 0:
                self.stats.current_rate = len(self.request_history) / time_span
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Enhanced health check with throttling statistics.
        
        Returns:
            Dict containing health status and throttling stats
        """
        # Get base health check
        base_health = await self.base_client.health_check()
        
        # Add throttling statistics
        enhanced_health = {
            **base_health,
            "throttling": {
                "enabled": True,
                "stats": {
                    "total_requests": self.stats.total_requests,
                    "successful_requests": self.stats.successful_requests,
                    "failed_requests": self.stats.failed_requests,
                    "throttled_requests": self.stats.throttled_requests,
                    "rejected_requests": self.stats.rejected_requests,
                    "average_response_time_ms": round(self.stats.average_response_time_ms, 2),
                    "current_rate_per_sec": round(self.stats.current_rate, 2),
                    "queue_size": self.stats.queue_size,
                    "semaphore_available": self.stats.semaphore_available,
                    "semaphore_total": self.max_concurrent,
                    "adaptive_delay_ms": round(self.stats.adaptive_delay_ms, 2)
                },
                "circuit_breaker": {
                    "enabled": self.circuit_breaker_enabled,
                    "state": self.stats.circuit_state,
                    "opens_count": self.stats.circuit_opens,
                    "last_open": self.stats.last_circuit_open,
                    "last_close": self.stats.last_circuit_close
                } if self.circuit_breaker_enabled else {"enabled": False},
                "limits": {
                    "max_concurrent_requests": self.max_concurrent,
                    "requests_per_minute": self.requests_per_minute,
                    "base_request_delay_ms": self.config.vllm.request_delay_ms
                }
            }
        }
        
        return enhanced_health
    
    def get_throttling_stats(self) -> ThrottlingStats:
        """
        Get current throttling statistics.
        
        Returns:
            ThrottlingStats object with current metrics
        """
        return self.stats
    
    def reset_statistics(self):
        """Reset throttling statistics."""
        self.stats = ThrottlingStats(
            semaphore_available=self.max_concurrent
        )
        self.request_history.clear()
        self.adaptive_throttler.response_times.clear()
        self.adaptive_throttler.current_delay_ms = self.adaptive_throttler.min_delay_ms
        
        if self.circuit_breaker:
            self.circuit_breaker.failure_count = 0
            if self.circuit_breaker.state != CircuitState.CLOSED:
                self.circuit_breaker._transition_to_closed()
        
        self.logger.info("Throttling statistics reset")
    
    def update_limits(
        self,
        max_concurrent: Optional[int] = None,
        requests_per_minute: Optional[int] = None,
        request_delay_ms: Optional[float] = None
    ):
        """
        Dynamically update throttling limits.
        
        Args:
            max_concurrent: New concurrent request limit
            requests_per_minute: New rate limit
            request_delay_ms: New base request delay in milliseconds
        """
        if max_concurrent is not None and max_concurrent != self.max_concurrent:
            self.max_concurrent = max_concurrent
            self.semaphore = asyncio.Semaphore(max_concurrent)
            self.logger.info(f"Updated max_concurrent to {max_concurrent}")
        
        if requests_per_minute is not None:
            self.requests_per_minute = requests_per_minute
            self.logger.info(f"Updated requests_per_minute to {requests_per_minute}")
        
        if request_delay_ms is not None:
            self.config.vllm.request_delay_ms = request_delay_ms
            self.adaptive_throttler.min_delay_ms = request_delay_ms
            self.logger.info(f"Updated request_delay_ms to {request_delay_ms}")
    
    def __getattr__(self, name):
        """
        Delegate all other attributes/methods to the base client.
        
        This allows the wrapper to be a drop-in replacement for VLLMLocalClient.
        """
        return getattr(self.base_client, name)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Clean up if needed
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass


def create_throttled_client(
    base_client: Optional[VLLMLocalClient] = None,
    **kwargs
) -> ThrottledVLLMClient:
    """
    Factory function to create a throttled vLLM client.
    
    Args:
        base_client: Optional base VLLMLocalClient instance
        **kwargs: Arguments to pass to VLLMLocalClient if creating new
        
    Returns:
        ThrottledVLLMClient instance
    """
    if base_client is None:
        base_client = VLLMLocalClient(**kwargs)
    
    return ThrottledVLLMClient(base_client)


# Example usage and testing
async def example_usage():
    """Example of using the throttled client."""
    
    # Create base client
    base_client = VLLMLocalClient()
    
    # Wrap with throttling
    client = ThrottledVLLMClient(base_client)
    
    # Or use factory function
    # client = create_throttled_client()
    
    try:
        # Make a request
        request = VLLMRequest(
            messages=[
                {"role": "user", "content": "Extract entities from: John Doe filed a lawsuit."}
            ],
            max_tokens=100
        )
        
        response = await client.generate_chat_completion(request)
        print(f"Response: {response.content}")
        
        # Check health with stats
        health = await client.health_check()
        print(f"Health: {health}")
        
        # Get throttling stats
        stats = client.get_throttling_stats()
        print(f"Stats: {stats}")
        
    except GenerationError as e:
        if "Circuit breaker is OPEN" in str(e):
            print("Service is temporarily unavailable due to circuit breaker")
        else:
            print(f"Generation error: {e}")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Test the throttled client
    import asyncio
    asyncio.run(example_usage())