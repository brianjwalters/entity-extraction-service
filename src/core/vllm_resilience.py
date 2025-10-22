"""
vLLM Resilience and Fallback System

Comprehensive fallback and retry strategies for handling vLLM failures
with intelligent recovery mechanisms and hybrid extraction approaches.
"""

import asyncio
import json
import logging
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from functools import wraps
import random


logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of vLLM failures."""
    EMPTY_RESPONSE = "empty_response"           # {"entities": []}
    MALFORMED_JSON = "malformed_json"          # Invalid JSON structure
    CONNECTION_ERROR = "connection_error"       # Cannot reach vLLM
    TIMEOUT = "timeout"                        # Request timed out
    RATE_LIMIT = "rate_limit"                  # Too many requests
    CONTEXT_OVERFLOW = "context_overflow"      # Too much input
    SERVER_ERROR = "server_error"              # 5xx errors
    MODEL_OVERLOAD = "model_overload"          # GPU OOM or similar
    INVALID_FORMAT = "invalid_format"          # Response not in expected format


class RecoveryStrategy(Enum):
    """Recovery strategies for different failure types."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    REDUCE_CONTEXT = "reduce_context"
    FALLBACK_TO_REGEX = "fallback_to_regex"
    HYBRID_EXTRACTION = "hybrid_extraction"
    CHUNK_AND_RETRY = "chunk_and_retry"
    USE_CACHED = "use_cached"
    SKIP_AND_LOG = "skip_and_log"
    ALTERNATIVE_PROMPT = "alternative_prompt"
    SIMPLIFIED_REQUEST = "simplified_request"


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    exponential_base: float = 2.0
    jitter_factor: float = 0.1
    retry_on_empty: bool = True
    retry_on_malformed: bool = True
    retry_on_timeout: bool = True
    retry_on_connection: bool = True
    timeout_multiplier: float = 1.5  # Increase timeout on retry


@dataclass
class FallbackConfig:
    """Configuration for fallback strategies."""
    enable_regex_fallback: bool = True
    enable_hybrid_mode: bool = True
    enable_caching: bool = True
    enable_context_reduction: bool = True
    enable_chunking: bool = True
    cache_ttl_seconds: int = 3600
    min_confidence_for_cache: float = 0.8
    chunk_size: int = 3000
    chunk_overlap: int = 200
    context_reduction_ratio: float = 0.5


@dataclass
class ResilienceMetrics:
    """Metrics for resilience system performance."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_attempts: int = 0
    successful_retries: int = 0
    fallback_activations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    failure_types: Dict[str, int] = field(default_factory=dict)
    recovery_strategies_used: Dict[str, int] = field(default_factory=dict)
    average_retry_count: float = 0.0
    success_rate: float = 0.0


class ResponseCache:
    """Intelligent caching system for vLLM responses."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[Any, datetime, float]] = {}
        self.ttl_seconds = ttl_seconds
        self.access_count: Dict[str, int] = {}
        
    def _generate_key(self, content: str, strategy: str, config: Dict) -> str:
        """Generate cache key from request parameters."""
        key_data = {
            "content_hash": hashlib.md5(content.encode()).hexdigest(),
            "strategy": strategy,
            "config": json.dumps(config, sort_keys=True)
        }
        return hashlib.sha256(json.dumps(key_data).encode()).hexdigest()
    
    def get(self, content: str, strategy: str, config: Dict) -> Optional[Any]:
        """Retrieve cached response if valid."""
        key = self._generate_key(content, strategy, config)
        
        if key in self.cache:
            response, timestamp, confidence = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                self.access_count[key] = self.access_count.get(key, 0) + 1
                logger.info(f"Cache hit for key {key[:8]}... (accessed {self.access_count[key]} times)")
                return response
            else:
                # Expired entry
                del self.cache[key]
                if key in self.access_count:
                    del self.access_count[key]
        
        return None
    
    def set(self, content: str, strategy: str, config: Dict, 
            response: Any, confidence: float = 1.0) -> None:
        """Cache response with confidence score."""
        key = self._generate_key(content, strategy, config)
        self.cache[key] = (response, datetime.now(), confidence)
        self.access_count[key] = 1
        
        # Implement simple LRU if cache gets too large
        if len(self.cache) > 1000:
            self._evict_least_used()
    
    def _evict_least_used(self) -> None:
        """Evict least recently used entries."""
        if not self.access_count:
            return
            
        # Find least accessed key
        min_key = min(self.access_count, key=self.access_count.get)
        if min_key in self.cache:
            del self.cache[min_key]
            del self.access_count[min_key]
    
    def clear_expired(self) -> int:
        """Clear all expired entries."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp, _) in self.cache.items()
            if now - timestamp >= timedelta(seconds=self.ttl_seconds)
        ]
        
        for key in expired_keys:
            del self.cache[key]
            if key in self.access_count:
                del self.access_count[key]
        
        return len(expired_keys)


class ResponseValidator:
    """Validate vLLM responses for correctness."""
    
    @staticmethod
    def validate_json_structure(response: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Validate JSON structure and parse it."""
        try:
            # Try to parse JSON
            data = json.loads(response)
            
            # Check for expected structure
            if not isinstance(data, dict):
                return False, None, "Response is not a JSON object"
            
            # Check for entities key
            if "entities" not in data:
                # Try common variations
                if "extracted_entities" in data:
                    data["entities"] = data["extracted_entities"]
                elif "results" in data:
                    data["entities"] = data["results"]
                else:
                    return False, None, "Missing 'entities' key in response"
            
            # Validate entities is a list
            if not isinstance(data["entities"], list):
                return False, None, "'entities' must be a list"
            
            # Validate each entity
            for i, entity in enumerate(data["entities"]):
                if not isinstance(entity, dict):
                    return False, None, f"Entity {i} is not a dictionary"
                
                # Check for required fields
                required_fields = ["text", "entity_type"]
                missing_fields = [f for f in required_fields if f not in entity]
                
                if missing_fields:
                    # Try to fix common field name variations
                    if "type" in entity and "entity_type" not in entity:
                        entity["entity_type"] = entity["type"]
                    if "value" in entity and "text" not in entity:
                        entity["text"] = entity["value"]
                    
                    # Re-check
                    missing_fields = [f for f in required_fields if f not in entity]
                    if missing_fields:
                        logger.warning(f"Entity {i} missing fields: {missing_fields}")
            
            return True, data, None
            
        except json.JSONDecodeError as e:
            # Try to fix common JSON errors
            fixed = ResponseValidator._attempt_json_repair(response)
            if fixed:
                return ResponseValidator.validate_json_structure(fixed)
            return False, None, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, None, f"Validation error: {str(e)}"
    
    @staticmethod
    def _attempt_json_repair(response: str) -> Optional[str]:
        """Attempt to repair common JSON formatting issues."""
        # Remove any markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        # Fix common issues
        response = response.strip()
        
        # Add missing closing brackets
        open_braces = response.count("{")
        close_braces = response.count("}")
        if open_braces > close_braces:
            response += "}" * (open_braces - close_braces)
        
        open_brackets = response.count("[")
        close_brackets = response.count("]")
        if open_brackets > close_brackets:
            response += "]" * (open_brackets - close_brackets)
        
        # Fix trailing commas
        import re
        response = re.sub(r',\s*}', '}', response)
        response = re.sub(r',\s*]', ']', response)
        
        return response
    
    @staticmethod
    def is_empty_response(data: Dict) -> bool:
        """Check if response contains no entities."""
        return not data.get("entities") or len(data["entities"]) == 0
    
    @staticmethod
    def calculate_confidence(data: Dict) -> float:
        """Calculate overall confidence for the response."""
        if ResponseValidator.is_empty_response(data):
            return 0.0
        
        entities = data.get("entities", [])
        if not entities:
            return 0.0
        
        # Calculate average confidence if available
        confidences = [
            e.get("confidence", 0.5) 
            for e in entities 
            if isinstance(e, dict)
        ]
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
        else:
            # Base confidence on entity count
            avg_confidence = min(0.3 + (len(entities) * 0.05), 0.9)
        
        return avg_confidence


class ExponentialBackoff:
    """Exponential backoff with jitter implementation."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        
    def get_delay_ms(self, attempt: int) -> int:
        """Calculate delay for given attempt number."""
        if attempt <= 0:
            return 0
        
        # Exponential calculation
        delay = min(
            self.config.initial_delay_ms * (self.config.exponential_base ** (attempt - 1)),
            self.config.max_delay_ms
        )
        
        # Add jitter
        if self.config.jitter_factor > 0:
            jitter = delay * self.config.jitter_factor * (2 * random.random() - 1)
            delay = max(0, delay + jitter)
        
        return int(delay)
    
    async def wait(self, attempt: int) -> None:
        """Wait for the calculated delay."""
        delay_ms = self.get_delay_ms(attempt)
        if delay_ms > 0:
            logger.info(f"Backing off for {delay_ms}ms (attempt {attempt})")
            await asyncio.sleep(delay_ms / 1000.0)


class VLLMResilienceManager:
    """
    Main resilience manager for vLLM operations.
    
    Coordinates fallback strategies, retry logic, and recovery mechanisms
    to ensure robust entity extraction even when vLLM fails.
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        fallback_config: Optional[FallbackConfig] = None,
        enable_metrics: bool = True
    ):
        self.retry_config = retry_config or RetryConfig()
        self.fallback_config = fallback_config or FallbackConfig()
        self.backoff = ExponentialBackoff(self.retry_config)
        self.cache = ResponseCache() if fallback_config and fallback_config.enable_caching else None
        self.validator = ResponseValidator()
        self.metrics = ResilienceMetrics() if enable_metrics else None
        
        # Strategy mappings
        self.failure_strategies = {
            FailureType.EMPTY_RESPONSE: [
                RecoveryStrategy.ALTERNATIVE_PROMPT,
                RecoveryStrategy.HYBRID_EXTRACTION,
                RecoveryStrategy.FALLBACK_TO_REGEX
            ],
            FailureType.MALFORMED_JSON: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.SIMPLIFIED_REQUEST,
                RecoveryStrategy.FALLBACK_TO_REGEX
            ],
            FailureType.CONNECTION_ERROR: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.USE_CACHED,
                RecoveryStrategy.FALLBACK_TO_REGEX
            ],
            FailureType.TIMEOUT: [
                RecoveryStrategy.REDUCE_CONTEXT,
                RecoveryStrategy.CHUNK_AND_RETRY,
                RecoveryStrategy.SIMPLIFIED_REQUEST
            ],
            FailureType.CONTEXT_OVERFLOW: [
                RecoveryStrategy.CHUNK_AND_RETRY,
                RecoveryStrategy.REDUCE_CONTEXT
            ],
            FailureType.RATE_LIMIT: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.USE_CACHED
            ],
            FailureType.SERVER_ERROR: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.FALLBACK_TO_REGEX
            ],
            FailureType.MODEL_OVERLOAD: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.SIMPLIFIED_REQUEST,
                RecoveryStrategy.REDUCE_CONTEXT
            ]
        }
    
    def classify_failure(self, error: Exception, response: Optional[str] = None) -> FailureType:
        """Classify the type of failure from error and response."""
        error_str = str(error).lower()
        
        # Connection errors
        if any(x in error_str for x in ["connection", "connect", "network", "refused"]):
            return FailureType.CONNECTION_ERROR
        
        # Timeout errors
        if any(x in error_str for x in ["timeout", "timed out", "deadline"]):
            return FailureType.TIMEOUT
        
        # Rate limiting
        if any(x in error_str for x in ["rate limit", "too many", "429"]):
            return FailureType.RATE_LIMIT
        
        # Context overflow
        if any(x in error_str for x in ["context", "token", "length", "overflow", "too long"]):
            return FailureType.CONTEXT_OVERFLOW
        
        # Server errors
        if any(x in error_str for x in ["500", "502", "503", "504", "server error"]):
            return FailureType.SERVER_ERROR
        
        # Model overload
        if any(x in error_str for x in ["oom", "memory", "cuda", "gpu"]):
            return FailureType.MODEL_OVERLOAD
        
        # Check response-based failures
        if response:
            valid, data, error_msg = self.validator.validate_json_structure(response)
            if not valid:
                return FailureType.MALFORMED_JSON
            if data and self.validator.is_empty_response(data):
                return FailureType.EMPTY_RESPONSE
        
        # Default to server error
        return FailureType.SERVER_ERROR
    
    async def execute_with_resilience(
        self,
        vllm_func: Callable,
        content: str,
        strategy: str = "ai_enhanced",
        config: Optional[Dict] = None,
        regex_fallback_func: Optional[Callable] = None,
        hybrid_func: Optional[Callable] = None
    ) -> Tuple[bool, Any, Dict[str, Any]]:
        """
        Execute vLLM function with comprehensive resilience.
        
        Args:
            vllm_func: The vLLM function to execute
            content: Content to process
            strategy: Extraction strategy
            config: Configuration dict
            regex_fallback_func: Function for regex-only extraction
            hybrid_func: Function for hybrid extraction
            
        Returns:
            Tuple of (success, result, metadata)
        """
        if self.metrics:
            self.metrics.total_requests += 1
        
        config = config or {}
        metadata = {
            "attempts": 0,
            "strategies_used": [],
            "failure_types": [],
            "final_strategy": None,
            "cached": False,
            "processing_time_ms": 0
        }
        
        start_time = time.time()
        
        # Check cache first
        if self.cache and self.fallback_config.enable_caching:
            cached_result = self.cache.get(content, strategy, config)
            if cached_result:
                if self.metrics:
                    self.metrics.cache_hits += 1
                    self.metrics.successful_requests += 1
                
                metadata["cached"] = True
                metadata["final_strategy"] = "cache"
                metadata["processing_time_ms"] = (time.time() - start_time) * 1000
                
                return True, cached_result, metadata
            elif self.metrics:
                self.metrics.cache_misses += 1
        
        # Try primary execution with retries
        for attempt in range(1, self.retry_config.max_retries + 1):
            metadata["attempts"] = attempt
            
            try:
                # Execute vLLM function
                result = await vllm_func(content, **config)
                
                # Validate response
                if isinstance(result, str):
                    valid, data, error_msg = self.validator.validate_json_structure(result)
                    if not valid:
                        raise ValueError(f"Invalid response format: {error_msg}")
                    result = data
                
                # Check for empty response
                if self.validator.is_empty_response(result):
                    if not self.retry_config.retry_on_empty:
                        break
                    
                    logger.warning(f"Empty response on attempt {attempt}, retrying...")
                    metadata["failure_types"].append(FailureType.EMPTY_RESPONSE.value)
                    
                    # Try alternative strategies
                    if attempt == 2 and hybrid_func:
                        # Second attempt: try hybrid
                        result = await self._try_hybrid_extraction(
                            hybrid_func, content, config
                        )
                        if result and not self.validator.is_empty_response(result):
                            metadata["strategies_used"].append("hybrid")
                            break
                    
                    await self.backoff.wait(attempt)
                    continue
                
                # Success!
                if self.metrics:
                    self.metrics.successful_requests += 1
                    if attempt > 1:
                        self.metrics.successful_retries += 1
                
                # Cache successful result
                if self.cache and self.fallback_config.enable_caching:
                    confidence = self.validator.calculate_confidence(result)
                    if confidence >= self.fallback_config.min_confidence_for_cache:
                        self.cache.set(content, strategy, config, result, confidence)
                
                metadata["final_strategy"] = "vllm"
                metadata["processing_time_ms"] = (time.time() - start_time) * 1000
                
                return True, result, metadata
                
            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {str(e)}")
                
                if self.metrics:
                    self.metrics.retry_attempts += 1
                
                # Classify failure
                failure_type = self.classify_failure(e, str(result) if 'result' in locals() else None)
                metadata["failure_types"].append(failure_type.value)
                
                # Get recovery strategies
                recovery_strategies = self.failure_strategies.get(
                    failure_type, 
                    [RecoveryStrategy.RETRY_WITH_BACKOFF]
                )
                
                # Apply recovery strategies
                for recovery_strategy in recovery_strategies:
                    if recovery_strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                        if attempt < self.retry_config.max_retries:
                            await self.backoff.wait(attempt)
                            continue
                    
                    elif recovery_strategy == RecoveryStrategy.REDUCE_CONTEXT:
                        if self.fallback_config.enable_context_reduction:
                            config = self._reduce_context(config)
                            metadata["strategies_used"].append("context_reduction")
                    
                    elif recovery_strategy == RecoveryStrategy.FALLBACK_TO_REGEX:
                        if regex_fallback_func and self.fallback_config.enable_regex_fallback:
                            result = await self._try_regex_fallback(
                                regex_fallback_func, content, config
                            )
                            if result:
                                metadata["final_strategy"] = "regex_fallback"
                                metadata["strategies_used"].append("regex_fallback")
                                
                                if self.metrics:
                                    self.metrics.fallback_activations += 1
                                    self.metrics.successful_requests += 1
                                
                                metadata["processing_time_ms"] = (time.time() - start_time) * 1000
                                return True, result, metadata
                    
                    elif recovery_strategy == RecoveryStrategy.CHUNK_AND_RETRY:
                        if self.fallback_config.enable_chunking:
                            result = await self._try_chunked_extraction(
                                vllm_func, content, config
                            )
                            if result:
                                metadata["final_strategy"] = "chunked"
                                metadata["strategies_used"].append("chunking")
                                
                                if self.metrics:
                                    self.metrics.successful_requests += 1
                                
                                metadata["processing_time_ms"] = (time.time() - start_time) * 1000
                                return True, result, metadata
                
                # If this is the last attempt and we have no result, try final fallback
                if attempt == self.retry_config.max_retries:
                    if regex_fallback_func and self.fallback_config.enable_regex_fallback:
                        result = await self._try_regex_fallback(
                            regex_fallback_func, content, config
                        )
                        if result:
                            metadata["final_strategy"] = "regex_final_fallback"
                            metadata["strategies_used"].append("regex_final_fallback")
                            
                            if self.metrics:
                                self.metrics.fallback_activations += 1
                                self.metrics.successful_requests += 1
                            
                            metadata["processing_time_ms"] = (time.time() - start_time) * 1000
                            return True, result, metadata
        
        # All attempts failed
        if self.metrics:
            self.metrics.failed_requests += 1
        
        metadata["processing_time_ms"] = (time.time() - start_time) * 1000
        return False, {"entities": []}, metadata
    
    async def _try_hybrid_extraction(
        self, 
        hybrid_func: Callable,
        content: str,
        config: Dict
    ) -> Optional[Dict]:
        """Try hybrid extraction approach."""
        try:
            logger.info("Attempting hybrid extraction as fallback")
            result = await hybrid_func(content, **config)
            return result
        except Exception as e:
            logger.error(f"Hybrid extraction failed: {str(e)}")
            return None
    
    async def _try_regex_fallback(
        self,
        regex_func: Callable,
        content: str,
        config: Dict
    ) -> Optional[Dict]:
        """Try regex-only extraction as fallback."""
        try:
            logger.info("Falling back to regex-only extraction")
            result = await regex_func(content)
            
            # Format result to match expected structure
            if isinstance(result, list):
                result = {"entities": result}
            
            return result
        except Exception as e:
            logger.error(f"Regex fallback failed: {str(e)}")
            return None
    
    async def _try_chunked_extraction(
        self,
        vllm_func: Callable,
        content: str,
        config: Dict
    ) -> Optional[Dict]:
        """Try extraction with content chunking."""
        try:
            logger.info("Attempting chunked extraction")
            
            # Split content into chunks
            chunks = self._create_chunks(
                content,
                self.fallback_config.chunk_size,
                self.fallback_config.chunk_overlap
            )
            
            all_entities = []
            for i, chunk in enumerate(chunks):
                try:
                    result = await vllm_func(chunk, **config)
                    if isinstance(result, dict) and "entities" in result:
                        all_entities.extend(result["entities"])
                except Exception as e:
                    logger.warning(f"Chunk {i} failed: {str(e)}")
                    continue
            
            # Deduplicate entities
            unique_entities = self._deduplicate_entities(all_entities)
            return {"entities": unique_entities}
            
        except Exception as e:
            logger.error(f"Chunked extraction failed: {str(e)}")
            return None
    
    def _reduce_context(self, config: Dict) -> Dict:
        """Reduce context size in configuration."""
        new_config = config.copy()
        
        # Reduce max tokens
        if "max_tokens" in new_config:
            new_config["max_tokens"] = int(
                new_config["max_tokens"] * self.fallback_config.context_reduction_ratio
            )
        
        # Reduce context window
        if "max_context_length" in new_config:
            new_config["max_context_length"] = int(
                new_config["max_context_length"] * self.fallback_config.context_reduction_ratio
            )
        
        return new_config
    
    def _create_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Create overlapping chunks from text."""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end >= text_length:
                break
            
            start = end - overlap
        
        return chunks
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on text and type."""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (
                entity.get("text", "").lower().strip(),
                entity.get("entity_type", "").lower()
            )
            
            if key not in seen and key[0]:
                seen.add(key)
                unique.append(entity)
        
        return unique
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of resilience metrics."""
        if not self.metrics:
            return {}
        
        total = self.metrics.total_requests or 1
        return {
            "total_requests": self.metrics.total_requests,
            "success_rate": self.metrics.successful_requests / total,
            "failure_rate": self.metrics.failed_requests / total,
            "retry_rate": self.metrics.retry_attempts / total,
            "fallback_rate": self.metrics.fallback_activations / total,
            "cache_hit_rate": self.metrics.cache_hits / (self.metrics.cache_hits + self.metrics.cache_misses)
            if (self.metrics.cache_hits + self.metrics.cache_misses) > 0 else 0,
            "average_retries": self.metrics.retry_attempts / total,
            "failure_breakdown": self.metrics.failure_types,
            "recovery_strategies": self.metrics.recovery_strategies_used
        }


def resilient_vllm_operation(
    retry_config: Optional[RetryConfig] = None,
    fallback_config: Optional[FallbackConfig] = None
):
    """
    Decorator for making vLLM operations resilient.
    
    Usage:
        @resilient_vllm_operation()
        async def extract_entities(content: str) -> Dict:
            # vLLM extraction logic
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = VLLMResilienceManager(retry_config, fallback_config)
            
            # Extract fallback functions if provided
            regex_fallback = kwargs.pop("regex_fallback", None)
            hybrid_fallback = kwargs.pop("hybrid_fallback", None)
            
            # Execute with resilience
            success, result, metadata = await manager.execute_with_resilience(
                func,
                args[0] if args else kwargs.get("content", ""),
                kwargs.get("strategy", "ai_enhanced"),
                kwargs,
                regex_fallback,
                hybrid_fallback
            )
            
            # Add metadata to result
            if isinstance(result, dict):
                result["_resilience_metadata"] = metadata
            
            return result
        
        return wrapper
    return decorator