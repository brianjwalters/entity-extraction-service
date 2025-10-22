"""
vLLM Performance Optimizer for Entity Extraction Service

Provides advanced performance optimization components for vLLM integration including
intelligent request batching, memory optimization, performance profiling, and 
document size estimation. Designed to achieve breakthrough performance targets:
- Small documents (<500 tokens): <50ms
- Medium documents (500-2000 tokens): <150ms  
- Large documents (2000-10000 tokens): <500ms
- Extra-large documents (>10000 tokens): <2000ms
"""

import asyncio
import gc
import logging
import psutil
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict, field
import hashlib

logger = logging.getLogger(__name__)


class DocumentSizeTier(Enum):
    """Document size classification tiers for optimized processing."""
    SMALL = "small"          # <500 tokens
    MEDIUM = "medium"        # 500-2000 tokens
    LARGE = "large"          # 2000-10000 tokens
    EXTRA_LARGE = "xl"       # >10000 tokens


class BatchPriority(Enum):
    """Batch processing priority levels."""
    URGENT = 0      # Process immediately
    HIGH = 1        # Process within 10ms
    NORMAL = 2      # Process within 50ms
    LOW = 3         # Process within 200ms


@dataclass
class DocumentRequest:
    """Request for document processing with size and priority metadata."""
    id: str
    text: str
    size_tier: DocumentSizeTier
    estimated_tokens: int
    priority: BatchPriority = BatchPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None


@dataclass
class BatchConfig:
    """Configuration for adaptive batching by document size tier."""
    tier: DocumentSizeTier
    max_batch_size: int
    min_batch_size: int
    max_wait_time_ms: float
    optimal_tokens_per_batch: int
    memory_threshold_mb: float


@dataclass
class PerformanceMetrics:
    """Performance metrics for tracking and optimization."""
    tier: DocumentSizeTier
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    throughput_tokens_per_sec: float
    successful_requests: int
    failed_requests: int
    total_tokens_processed: int
    memory_peak_mb: float
    timestamp: datetime = field(default_factory=datetime.now)


class DocumentSizeEstimator:
    """
    Fast document size estimation and classification for optimal batching.
    
    Features:
    - Quick token count estimation without full tokenization
    - Caching for repeated documents
    - Size tier classification
    - Statistical modeling for improved accuracy over time
    """
    
    def __init__(
        self,
        cache_size: int = 10000,
        words_per_token_ratio: float = 0.75,  # Approximate for English text
        enable_cache: bool = True
    ):
        """
        Initialize DocumentSizeEstimator.
        
        Args:
            cache_size: Maximum number of cached estimates
            words_per_token_ratio: Average words per token ratio
            enable_cache: Whether to cache size estimates
        """
        self.cache_size = cache_size
        self.words_per_token_ratio = words_per_token_ratio
        self.enable_cache = enable_cache
        
        # Thread-safe cache
        self._cache_lock = threading.RLock()
        self._size_cache: Dict[str, Tuple[int, DocumentSizeTier]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Size tier thresholds (in tokens)
        self.tier_thresholds = {
            DocumentSizeTier.SMALL: 500,
            DocumentSizeTier.MEDIUM: 2000,
            DocumentSizeTier.LARGE: 10000
        }
        
        # Statistical learning for improved estimation
        self._estimation_history: deque = deque(maxlen=1000)
        self._adjustment_factor = 1.0
        
        logger.info(f"DocumentSizeEstimator initialized with cache_size={cache_size}")
    
    def estimate_tokens(self, text: str, use_cache: bool = True) -> int:
        """
        Estimate token count from text quickly.
        
        Args:
            text: Input text to estimate
            use_cache: Whether to use cached estimates
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Check cache first
        if self.enable_cache and use_cache:
            cache_key = self._get_cache_key(text)
            
            with self._cache_lock:
                if cache_key in self._size_cache:
                    self._cache_hits += 1
                    tokens, _ = self._size_cache[cache_key]
                    return tokens
                self._cache_misses += 1
        
        # Fast estimation based on character and word counts
        char_count = len(text)
        word_count = len(text.split())
        
        # Base estimation using character count (4 chars per token average)
        char_based_estimate = char_count / 4.0
        
        # Word-based estimation
        word_based_estimate = word_count / self.words_per_token_ratio
        
        # Weighted average with adjustment factor
        estimated_tokens = int(
            (char_based_estimate * 0.4 + word_based_estimate * 0.6) * self._adjustment_factor
        )
        
        # Account for special characters and punctuation
        special_char_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
        estimated_tokens += special_char_count // 10  # Rough adjustment
        
        # Cache the result
        if self.enable_cache and use_cache:
            tier = self.classify_size_tier(estimated_tokens)
            self._cache_estimate(text, estimated_tokens, tier)
        
        return estimated_tokens
    
    def classify_size_tier(self, token_count: int) -> DocumentSizeTier:
        """
        Classify document into size tier based on token count.
        
        Args:
            token_count: Number of tokens
            
        Returns:
            Document size tier
        """
        if token_count < self.tier_thresholds[DocumentSizeTier.SMALL]:
            return DocumentSizeTier.SMALL
        elif token_count < self.tier_thresholds[DocumentSizeTier.MEDIUM]:
            return DocumentSizeTier.MEDIUM
        elif token_count < self.tier_thresholds[DocumentSizeTier.LARGE]:
            return DocumentSizeTier.LARGE
        else:
            return DocumentSizeTier.EXTRA_LARGE
    
    def classify_document(self, text: str) -> Tuple[DocumentSizeTier, int]:
        """
        Classify document and return tier with estimated tokens.
        
        Args:
            text: Document text
            
        Returns:
            Tuple of (size_tier, estimated_tokens)
        """
        tokens = self.estimate_tokens(text)
        tier = self.classify_size_tier(tokens)
        return tier, tokens
    
    def update_estimation_accuracy(self, estimated: int, actual: int):
        """
        Update estimation model based on actual token count.
        
        Args:
            estimated: Estimated token count
            actual: Actual token count from tokenization
        """
        if estimated > 0:
            ratio = actual / estimated
            self._estimation_history.append(ratio)
            
            # Update adjustment factor using moving average
            if len(self._estimation_history) >= 10:
                avg_ratio = sum(self._estimation_history) / len(self._estimation_history)
                # Slowly adjust towards actual ratio
                self._adjustment_factor = (
                    0.9 * self._adjustment_factor + 0.1 * avg_ratio
                )
                
                if len(self._estimation_history) % 100 == 0:
                    logger.info(
                        f"Estimation accuracy updated: adjustment_factor={self._adjustment_factor:.3f}, "
                        f"avg_ratio={avg_ratio:.3f}"
                    )
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        # Use first 100 chars + length for quick hashing
        key_text = f"{text[:100]}_{len(text)}"
        return hashlib.md5(key_text.encode()).hexdigest()
    
    def _cache_estimate(self, text: str, tokens: int, tier: DocumentSizeTier):
        """Cache size estimate for text."""
        cache_key = self._get_cache_key(text)
        
        with self._cache_lock:
            # LRU eviction if cache is full
            if len(self._size_cache) >= self.cache_size:
                # Remove oldest entry (simple FIFO for now)
                oldest_key = next(iter(self._size_cache))
                del self._size_cache[oldest_key]
            
            self._size_cache[cache_key] = (tokens, tier)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / max(total_requests, 1)
            
            return {
                "cache_size": len(self._size_cache),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate": hit_rate,
                "adjustment_factor": self._adjustment_factor,
                "estimation_samples": len(self._estimation_history)
            }


class AdaptiveBatcher:
    """
    Intelligently batch requests based on document size for optimal throughput.
    
    Features:
    - Separate queues for different document sizes
    - Auto-flush timers for optimal latency
    - Dynamic batch size adjustment based on load
    - Priority-based processing
    - Thread-safe concurrent access
    """
    
    def __init__(
        self,
        process_batch_fn: Callable,
        size_estimator: Optional[DocumentSizeEstimator] = None,
        enable_auto_flush: bool = True
    ):
        """
        Initialize AdaptiveBatcher.
        
        Args:
            process_batch_fn: Async function to process a batch of requests
            size_estimator: DocumentSizeEstimator instance
            enable_auto_flush: Whether to enable auto-flush timers
        """
        self.process_batch_fn = process_batch_fn
        self.size_estimator = size_estimator or DocumentSizeEstimator()
        self.enable_auto_flush = enable_auto_flush
        
        # Thread-safe request queues by size tier
        self._queue_lock = threading.RLock()
        self._request_queues: Dict[DocumentSizeTier, deque] = {
            tier: deque() for tier in DocumentSizeTier
        }
        
        # Batch configurations by tier
        self._batch_configs = self._init_batch_configs()
        
        # Auto-flush management
        self._flush_tasks: Dict[DocumentSizeTier, Optional[asyncio.Task]] = {
            tier: None for tier in DocumentSizeTier
        }
        
        # Performance tracking
        self._batch_count = 0
        self._total_requests = 0
        self._tier_stats = defaultdict(lambda: {"count": 0, "total_time_ms": 0})
        
        # Dynamic adjustment parameters
        self._load_factor = 1.0
        self._last_adjustment = datetime.now()
        
        logger.info("AdaptiveBatcher initialized with auto_flush enabled")
    
    def _init_batch_configs(self) -> Dict[DocumentSizeTier, BatchConfig]:
        """Initialize batch configurations for each tier."""
        return {
            DocumentSizeTier.SMALL: BatchConfig(
                tier=DocumentSizeTier.SMALL,
                max_batch_size=32,
                min_batch_size=8,
                max_wait_time_ms=20,
                optimal_tokens_per_batch=5000,
                memory_threshold_mb=500
            ),
            DocumentSizeTier.MEDIUM: BatchConfig(
                tier=DocumentSizeTier.MEDIUM,
                max_batch_size=16,
                min_batch_size=4,
                max_wait_time_ms=50,
                optimal_tokens_per_batch=15000,
                memory_threshold_mb=1000
            ),
            DocumentSizeTier.LARGE: BatchConfig(
                tier=DocumentSizeTier.LARGE,
                max_batch_size=8,
                min_batch_size=2,
                max_wait_time_ms=100,
                optimal_tokens_per_batch=30000,
                memory_threshold_mb=2000
            ),
            DocumentSizeTier.EXTRA_LARGE: BatchConfig(
                tier=DocumentSizeTier.EXTRA_LARGE,
                max_batch_size=4,
                min_batch_size=1,
                max_wait_time_ms=200,
                optimal_tokens_per_batch=50000,
                memory_threshold_mb=4000
            )
        }
    
    async def add_request(
        self,
        text: str,
        request_id: Optional[str] = None,
        priority: BatchPriority = BatchPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """
        Add a request to the appropriate queue based on size.
        
        Args:
            text: Document text to process
            request_id: Optional request ID
            priority: Processing priority
            metadata: Additional metadata
            callback: Optional callback for result
            
        Returns:
            Request ID for tracking
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = f"req_{self._total_requests}_{int(time.time() * 1000)}"
        
        # Estimate size and classify
        tier, estimated_tokens = self.size_estimator.classify_document(text)
        
        # Create request object
        request = DocumentRequest(
            id=request_id,
            text=text,
            size_tier=tier,
            estimated_tokens=estimated_tokens,
            priority=priority,
            metadata=metadata or {},
            callback=callback
        )
        
        # Add to appropriate queue
        with self._queue_lock:
            self._request_queues[tier].append(request)
            self._total_requests += 1
        
        logger.debug(f"Added request {request_id} to {tier.value} queue (tokens: {estimated_tokens})")
        
        # Check if we should process immediately
        await self._check_and_process_batch(tier)
        
        return request_id
    
    async def _check_and_process_batch(self, tier: DocumentSizeTier):
        """
        Check if batch should be processed and trigger processing.
        
        Args:
            tier: Document size tier to check
        """
        config = self._batch_configs[tier]
        
        with self._queue_lock:
            queue_size = len(self._request_queues[tier])
            
            # Process immediately if batch is full
            if queue_size >= config.max_batch_size * self._load_factor:
                await self._process_tier_batch(tier)
                
            # Set up auto-flush timer if not already set
            elif (
                self.enable_auto_flush 
                and queue_size >= config.min_batch_size
                and not self._flush_tasks[tier]
            ):
                self._flush_tasks[tier] = asyncio.create_task(
                    self._auto_flush_timer(tier, config.max_wait_time_ms)
                )
    
    async def _auto_flush_timer(self, tier: DocumentSizeTier, wait_ms: float):
        """
        Auto-flush timer for a tier queue.
        
        Args:
            tier: Document size tier
            wait_ms: Maximum wait time in milliseconds
        """
        try:
            await asyncio.sleep(wait_ms / 1000.0)
            await self._process_tier_batch(tier)
        except asyncio.CancelledError:
            pass
        finally:
            with self._queue_lock:
                self._flush_tasks[tier] = None
    
    async def _process_tier_batch(self, tier: DocumentSizeTier):
        """
        Process a batch from specific tier queue.
        
        Args:
            tier: Document size tier to process
        """
        config = self._batch_configs[tier]
        
        # Collect batch
        batch_requests = []
        
        with self._queue_lock:
            queue = self._request_queues[tier]
            batch_size = min(len(queue), int(config.max_batch_size * self._load_factor))
            
            if batch_size == 0:
                return
            
            # Collect requests up to batch size
            for _ in range(batch_size):
                if queue:
                    batch_requests.append(queue.popleft())
            
            # Cancel any pending flush timer
            if self._flush_tasks[tier]:
                self._flush_tasks[tier].cancel()
                self._flush_tasks[tier] = None
        
        if not batch_requests:
            return
        
        # Process batch
        start_time = time.time()
        
        try:
            logger.info(
                f"Processing {tier.value} batch: {len(batch_requests)} requests, "
                f"~{sum(r.estimated_tokens for r in batch_requests)} tokens"
            )
            
            # Call the processing function
            results = await self.process_batch_fn(batch_requests)
            
            # Invoke callbacks if provided
            for request, result in zip(batch_requests, results):
                if request.callback:
                    try:
                        await request.callback(request.id, result)
                    except Exception as e:
                        logger.error(f"Callback error for {request.id}: {e}")
            
            # Update statistics
            processing_time_ms = (time.time() - start_time) * 1000
            
            with self._queue_lock:
                self._batch_count += 1
                self._tier_stats[tier]["count"] += len(batch_requests)
                self._tier_stats[tier]["total_time_ms"] += processing_time_ms
            
            logger.info(
                f"Processed {tier.value} batch in {processing_time_ms:.1f}ms "
                f"({len(batch_requests)} docs, "
                f"{processing_time_ms/len(batch_requests):.1f}ms per doc)"
            )
            
        except Exception as e:
            logger.error(f"Error processing {tier.value} batch: {e}")
            
            # Re-queue failed requests with increased priority
            with self._queue_lock:
                for request in batch_requests:
                    request.priority = BatchPriority.HIGH
                    self._request_queues[tier].appendleft(request)
        
        # Adjust batch parameters based on performance
        await self._adjust_batch_parameters(tier, processing_time_ms, len(batch_requests))
    
    async def _adjust_batch_parameters(
        self,
        tier: DocumentSizeTier,
        processing_time_ms: float,
        batch_size: int
    ):
        """
        Dynamically adjust batch parameters based on performance.
        
        Args:
            tier: Document size tier
            processing_time_ms: Processing time for batch
            batch_size: Number of documents in batch
        """
        # Only adjust every 30 seconds
        if (datetime.now() - self._last_adjustment).seconds < 30:
            return
        
        avg_time_per_doc = processing_time_ms / batch_size
        config = self._batch_configs[tier]
        
        # Performance targets by tier
        targets = {
            DocumentSizeTier.SMALL: 50,
            DocumentSizeTier.MEDIUM: 150,
            DocumentSizeTier.LARGE: 500,
            DocumentSizeTier.EXTRA_LARGE: 2000
        }
        
        target_ms = targets[tier]
        
        # Adjust load factor based on performance
        if avg_time_per_doc > target_ms * 1.5:
            # Reduce batch size if too slow
            self._load_factor = max(0.5, self._load_factor * 0.9)
            logger.info(f"Reducing batch size for {tier.value}: load_factor={self._load_factor:.2f}")
            
        elif avg_time_per_doc < target_ms * 0.7:
            # Increase batch size if fast enough
            self._load_factor = min(1.5, self._load_factor * 1.1)
            logger.info(f"Increasing batch size for {tier.value}: load_factor={self._load_factor:.2f}")
        
        self._last_adjustment = datetime.now()
    
    async def flush_all(self):
        """Force process all pending requests across all tiers."""
        for tier in DocumentSizeTier:
            await self._process_tier_batch(tier)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics."""
        with self._queue_lock:
            stats = {
                "total_requests": self._total_requests,
                "batch_count": self._batch_count,
                "load_factor": self._load_factor,
                "queues": {}
            }
            
            for tier in DocumentSizeTier:
                queue_size = len(self._request_queues[tier])
                tier_stat = self._tier_stats[tier]
                
                stats["queues"][tier.value] = {
                    "pending": queue_size,
                    "processed": tier_stat["count"],
                    "avg_time_ms": (
                        tier_stat["total_time_ms"] / tier_stat["count"]
                        if tier_stat["count"] > 0 else 0
                    )
                }
            
            return stats


class MemoryOptimizer:
    """
    Monitor and optimize memory usage for vLLM processing.
    
    Features:
    - Real-time GPU/CPU memory monitoring
    - Automatic cleanup when threshold exceeded
    - Cache eviction strategies
    - Multi-model tier management
    - Memory pressure detection and mitigation
    """
    
    def __init__(
        self,
        memory_threshold_percent: float = 90.0,
        cache_cleanup_threshold_percent: float = 85.0,
        check_interval_seconds: float = 5.0,
        enable_gpu_monitoring: bool = True
    ):
        """
        Initialize MemoryOptimizer.
        
        Args:
            memory_threshold_percent: Trigger cleanup at this memory usage
            cache_cleanup_threshold_percent: Start cache eviction at this level
            check_interval_seconds: Memory check interval
            enable_gpu_monitoring: Whether to monitor GPU memory
        """
        self.memory_threshold_percent = memory_threshold_percent
        self.cache_cleanup_threshold_percent = cache_cleanup_threshold_percent
        self.check_interval_seconds = check_interval_seconds
        self.enable_gpu_monitoring = enable_gpu_monitoring
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._memory_pressure = False
        
        # Cache management
        self._cache_registry: List[Any] = []  # Objects with cache to clear
        self._cleanup_callbacks: List[Callable] = []
        
        # Statistics
        self._stats_lock = threading.RLock()
        self._cleanup_count = 0
        self._memory_history = deque(maxlen=100)
        
        # GPU monitoring setup
        self._gpu_available = False
        if enable_gpu_monitoring:
            try:
                import pynvml
                pynvml.nvmlInit()
                self._gpu_available = True
                self._gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                logger.info("GPU memory monitoring enabled")
            except Exception as e:
                logger.warning(f"GPU monitoring not available: {e}")
                self._gpu_available = False
        
        logger.info(
            f"MemoryOptimizer initialized: threshold={memory_threshold_percent}%, "
            f"cache_threshold={cache_cleanup_threshold_percent}%"
        )
    
    async def start_monitoring(self):
        """Start memory monitoring background task."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Memory monitoring already running")
            return
        
        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Memory monitoring started")
    
    async def stop_monitoring(self):
        """Stop memory monitoring."""
        self._shutdown_event.set()
        
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Memory monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                # Check memory usage
                memory_status = await self.check_memory_status()
                
                # Store in history
                with self._stats_lock:
                    self._memory_history.append(memory_status)
                
                # Check if cleanup needed
                if memory_status["system_memory_percent"] > self.memory_threshold_percent:
                    await self.trigger_cleanup("system_memory_threshold")
                    
                elif memory_status["system_memory_percent"] > self.cache_cleanup_threshold_percent:
                    await self.evict_caches("memory_pressure")
                
                # GPU memory check
                if self._gpu_available and memory_status.get("gpu_memory_percent", 0) > self.memory_threshold_percent:
                    await self.trigger_cleanup("gpu_memory_threshold")
                
                # Update memory pressure flag
                self._memory_pressure = (
                    memory_status["system_memory_percent"] > self.cache_cleanup_threshold_percent
                )
                
                await asyncio.sleep(self.check_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                await asyncio.sleep(self.check_interval_seconds)
    
    async def check_memory_status(self) -> Dict[str, Any]:
        """
        Check current memory status.
        
        Returns:
            Dictionary with memory statistics
        """
        # System memory
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "system_memory_percent": memory.percent,
            "system_memory_used_gb": memory.used / (1024**3),
            "system_memory_available_gb": memory.available / (1024**3),
            "system_memory_total_gb": memory.total / (1024**3),
            "swap_percent": swap.percent,
            "swap_used_gb": swap.used / (1024**3),
            "memory_pressure": self._memory_pressure
        }
        
        # GPU memory if available
        if self._gpu_available:
            try:
                import pynvml
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(self._gpu_handle)
                status.update({
                    "gpu_memory_percent": (mem_info.used / mem_info.total) * 100,
                    "gpu_memory_used_gb": mem_info.used / (1024**3),
                    "gpu_memory_total_gb": mem_info.total / (1024**3),
                    "gpu_memory_free_gb": mem_info.free / (1024**3)
                })
            except Exception as e:
                logger.debug(f"GPU memory check failed: {e}")
        
        return status
    
    async def trigger_cleanup(self, reason: str):
        """
        Trigger memory cleanup.
        
        Args:
            reason: Reason for cleanup
        """
        logger.warning(f"Memory cleanup triggered: {reason}")
        
        with self._stats_lock:
            self._cleanup_count += 1
        
        # Force garbage collection
        gc.collect()
        
        # Clear caches
        await self.evict_caches(reason)
        
        # Run registered cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
        
        # Log memory status after cleanup
        post_cleanup_status = await self.check_memory_status()
        logger.info(
            f"Memory after cleanup: {post_cleanup_status['system_memory_percent']:.1f}% "
            f"(was {self._memory_history[-1]['system_memory_percent']:.1f}%)"
        )
    
    async def evict_caches(self, reason: str):
        """
        Evict caches to free memory.
        
        Args:
            reason: Reason for cache eviction
        """
        logger.info(f"Cache eviction started: {reason}")
        
        evicted_count = 0
        
        for cache_obj in self._cache_registry:
            try:
                if hasattr(cache_obj, 'clear_cache'):
                    cache_obj.clear_cache()
                    evicted_count += 1
                elif hasattr(cache_obj, 'clear'):
                    cache_obj.clear()
                    evicted_count += 1
            except Exception as e:
                logger.error(f"Cache eviction failed: {e}")
        
        logger.info(f"Evicted {evicted_count} caches")
    
    def register_cache(self, cache_obj: Any):
        """
        Register a cache object for memory management.
        
        Args:
            cache_obj: Object with cache to manage
        """
        if cache_obj not in self._cache_registry:
            self._cache_registry.append(cache_obj)
            logger.debug(f"Registered cache: {type(cache_obj).__name__}")
    
    def register_cleanup_callback(self, callback: Callable):
        """
        Register cleanup callback.
        
        Args:
            callback: Function to call during cleanup
        """
        self._cleanup_callbacks.append(callback)
        logger.debug(f"Registered cleanup callback: {callback.__name__}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        with self._stats_lock:
            if not self._memory_history:
                return {"message": "No memory data available"}
            
            recent = list(self._memory_history)[-10:]
            memory_percents = [m["system_memory_percent"] for m in recent]
            
            stats = {
                "current_memory_percent": recent[-1]["system_memory_percent"],
                "avg_memory_percent": sum(memory_percents) / len(memory_percents),
                "max_memory_percent": max(memory_percents),
                "min_memory_percent": min(memory_percents),
                "cleanup_count": self._cleanup_count,
                "memory_pressure": self._memory_pressure,
                "cache_count": len(self._cache_registry)
            }
            
            if self._gpu_available and "gpu_memory_percent" in recent[-1]:
                gpu_percents = [
                    m.get("gpu_memory_percent", 0) 
                    for m in recent 
                    if "gpu_memory_percent" in m
                ]
                if gpu_percents:
                    stats.update({
                        "current_gpu_percent": recent[-1]["gpu_memory_percent"],
                        "avg_gpu_percent": sum(gpu_percents) / len(gpu_percents)
                    })
            
            return stats
    
    def is_memory_constrained(self) -> bool:
        """Check if system is under memory pressure."""
        return self._memory_pressure


class PerformanceProfiler:
    """
    Track and analyze performance metrics for vLLM processing.
    
    Features:
    - Tier-based performance tracking
    - Throughput calculation
    - Auto-tuning based on metrics
    - Performance report generation
    - Trend analysis and alerting
    """
    
    def __init__(
        self,
        window_size_minutes: int = 15,
        enable_auto_tuning: bool = True
    ):
        """
        Initialize PerformanceProfiler.
        
        Args:
            window_size_minutes: Time window for metrics aggregation
            enable_auto_tuning: Whether to enable automatic tuning
        """
        self.window_size_minutes = window_size_minutes
        self.enable_auto_tuning = enable_auto_tuning
        
        # Thread-safe metrics storage
        self._metrics_lock = threading.RLock()
        self._metrics_history: Dict[DocumentSizeTier, deque] = {
            tier: deque(maxlen=1000) for tier in DocumentSizeTier
        }
        
        # Performance targets
        self._performance_targets = {
            DocumentSizeTier.SMALL: 50,      # ms
            DocumentSizeTier.MEDIUM: 150,    # ms
            DocumentSizeTier.LARGE: 500,     # ms
            DocumentSizeTier.EXTRA_LARGE: 2000  # ms
        }
        
        # Auto-tuning parameters
        self._tuning_params = {
            "batch_size_multiplier": 1.0,
            "timeout_multiplier": 1.0,
            "memory_threshold_multiplier": 1.0
        }
        
        # Statistics
        self._total_requests = 0
        self._total_tokens = 0
        self._start_time = datetime.now()
        
        logger.info(f"PerformanceProfiler initialized with {window_size_minutes}min window")
    
    def record_request(
        self,
        tier: DocumentSizeTier,
        response_time_ms: float,
        tokens_processed: int,
        success: bool = True,
        memory_usage_mb: Optional[float] = None
    ):
        """
        Record a request's performance metrics.
        
        Args:
            tier: Document size tier
            response_time_ms: Response time in milliseconds
            tokens_processed: Number of tokens processed
            success: Whether request succeeded
            memory_usage_mb: Memory usage in MB
        """
        metric = {
            "timestamp": datetime.now(),
            "response_time_ms": response_time_ms,
            "tokens_processed": tokens_processed,
            "success": success,
            "memory_usage_mb": memory_usage_mb or 0
        }
        
        with self._metrics_lock:
            self._metrics_history[tier].append(metric)
            self._total_requests += 1
            self._total_tokens += tokens_processed
        
        # Check performance against target
        target_ms = self._performance_targets[tier]
        if response_time_ms > target_ms * 1.5:
            logger.warning(
                f"{tier.value} performance degradation: {response_time_ms:.1f}ms "
                f"(target: {target_ms}ms)"
            )
        
        # Auto-tune if enabled
        if self.enable_auto_tuning and self._total_requests % 100 == 0:
            self._auto_tune_parameters()
    
    def calculate_tier_metrics(self, tier: DocumentSizeTier) -> Optional[PerformanceMetrics]:
        """
        Calculate aggregated metrics for a tier.
        
        Args:
            tier: Document size tier
            
        Returns:
            Performance metrics or None if insufficient data
        """
        cutoff_time = datetime.now() - timedelta(minutes=self.window_size_minutes)
        
        with self._metrics_lock:
            recent_metrics = [
                m for m in self._metrics_history[tier]
                if m["timestamp"] >= cutoff_time
            ]
        
        if not recent_metrics:
            return None
        
        # Calculate statistics
        response_times = [m["response_time_ms"] for m in recent_metrics if m["success"]]
        if not response_times:
            return None
        
        response_times.sort()
        
        # Calculate percentiles
        def percentile(data, p):
            n = len(data)
            idx = int(n * p / 100)
            return data[min(idx, n-1)]
        
        # Calculate throughput
        time_span = (recent_metrics[-1]["timestamp"] - recent_metrics[0]["timestamp"]).total_seconds()
        total_tokens = sum(m["tokens_processed"] for m in recent_metrics)
        throughput = total_tokens / max(time_span, 1)
        
        # Memory statistics
        memory_values = [m["memory_usage_mb"] for m in recent_metrics if m["memory_usage_mb"] > 0]
        memory_peak = max(memory_values) if memory_values else 0
        
        return PerformanceMetrics(
            tier=tier,
            avg_response_time_ms=sum(response_times) / len(response_times),
            min_response_time_ms=min(response_times),
            max_response_time_ms=max(response_times),
            p50_response_time_ms=percentile(response_times, 50),
            p95_response_time_ms=percentile(response_times, 95),
            p99_response_time_ms=percentile(response_times, 99),
            throughput_tokens_per_sec=throughput,
            successful_requests=len(response_times),
            failed_requests=len(recent_metrics) - len(response_times),
            total_tokens_processed=total_tokens,
            memory_peak_mb=memory_peak
        )
    
    def _auto_tune_parameters(self):
        """Automatically tune performance parameters based on metrics."""
        adjustments_made = False
        
        for tier in DocumentSizeTier:
            metrics = self.calculate_tier_metrics(tier)
            if not metrics:
                continue
            
            target_ms = self._performance_targets[tier]
            
            # Check if we're meeting targets
            if metrics.p95_response_time_ms > target_ms * 1.2:
                # Reduce batch sizes if too slow
                self._tuning_params["batch_size_multiplier"] *= 0.95
                adjustments_made = True
                
            elif metrics.p95_response_time_ms < target_ms * 0.5:
                # Increase batch sizes if very fast
                self._tuning_params["batch_size_multiplier"] *= 1.05
                adjustments_made = True
            
            # Adjust timeout based on p99
            if metrics.p99_response_time_ms > target_ms * 2:
                self._tuning_params["timeout_multiplier"] *= 1.1
                adjustments_made = True
        
        if adjustments_made:
            logger.info(f"Auto-tuned parameters: {self._tuning_params}")
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "tier_metrics": {},
            "tuning_parameters": self._tuning_params.copy()
        }
        
        # Add tier-specific metrics
        for tier in DocumentSizeTier:
            metrics = self.calculate_tier_metrics(tier)
            if metrics:
                report["tier_metrics"][tier.value] = asdict(metrics)
                
                # Add performance assessment
                target = self._performance_targets[tier]
                if metrics.avg_response_time_ms <= target:
                    assessment = "excellent"
                elif metrics.avg_response_time_ms <= target * 1.5:
                    assessment = "good"
                elif metrics.avg_response_time_ms <= target * 2:
                    assessment = "acceptable"
                else:
                    assessment = "poor"
                
                report["tier_metrics"][tier.value]["performance_assessment"] = assessment
                report["tier_metrics"][tier.value]["target_ms"] = target
        
        # Overall throughput
        if self._total_requests > 0:
            total_time = (datetime.now() - self._start_time).total_seconds()
            report["overall_throughput"] = {
                "requests_per_second": self._total_requests / total_time,
                "tokens_per_second": self._total_tokens / total_time
            }
        
        return report
    
    def get_tuning_recommendations(self) -> List[str]:
        """Get performance tuning recommendations."""
        recommendations = []
        
        for tier in DocumentSizeTier:
            metrics = self.calculate_tier_metrics(tier)
            if not metrics:
                continue
            
            target = self._performance_targets[tier]
            
            # Response time recommendations
            if metrics.avg_response_time_ms > target * 1.5:
                recommendations.append(
                    f"{tier.value}: Consider reducing batch size or increasing compute resources "
                    f"(avg: {metrics.avg_response_time_ms:.1f}ms, target: {target}ms)"
                )
            
            # Memory recommendations
            if metrics.memory_peak_mb > 4000:
                recommendations.append(
                    f"{tier.value}: High memory usage detected ({metrics.memory_peak_mb:.0f}MB), "
                    f"consider memory optimization"
                )
            
            # Throughput recommendations
            if metrics.throughput_tokens_per_sec < 100:
                recommendations.append(
                    f"{tier.value}: Low throughput ({metrics.throughput_tokens_per_sec:.1f} tokens/s), "
                    f"consider batch size optimization"
                )
        
        return recommendations


class VLLMPerformanceOptimizer:
    """
    Main orchestrator for vLLM performance optimization.
    
    Integrates all optimization components:
    - Document size estimation and classification
    - Adaptive request batching
    - Memory optimization
    - Performance profiling and auto-tuning
    """
    
    def __init__(
        self,
        process_batch_fn: Callable,
        enable_monitoring: bool = True,
        enable_auto_tuning: bool = True
    ):
        """
        Initialize VLLMPerformanceOptimizer.
        
        Args:
            process_batch_fn: Function to process batches
            enable_monitoring: Enable memory and performance monitoring
            enable_auto_tuning: Enable automatic parameter tuning
        """
        # Initialize components
        self.size_estimator = DocumentSizeEstimator()
        self.batcher = AdaptiveBatcher(
            process_batch_fn=process_batch_fn,
            size_estimator=self.size_estimator
        )
        self.memory_optimizer = MemoryOptimizer()
        self.profiler = PerformanceProfiler(enable_auto_tuning=enable_auto_tuning)
        
        # Configuration
        self.enable_monitoring = enable_monitoring
        self.enable_auto_tuning = enable_auto_tuning
        
        # Statistics
        self._start_time = datetime.now()
        self._optimization_enabled = True
        
        # Register memory management
        self.memory_optimizer.register_cache(self.size_estimator)
        self.memory_optimizer.register_cleanup_callback(self._cleanup_callback)
        
        logger.info("VLLMPerformanceOptimizer initialized")
    
    async def start(self):
        """Start all optimization components."""
        if self.enable_monitoring:
            await self.memory_optimizer.start_monitoring()
        
        logger.info("Performance optimization started")
    
    async def stop(self):
        """Stop all optimization components."""
        await self.batcher.flush_all()
        
        if self.enable_monitoring:
            await self.memory_optimizer.stop_monitoring()
        
        logger.info("Performance optimization stopped")
    
    async def process_document(
        self,
        text: str,
        request_id: Optional[str] = None,
        priority: BatchPriority = BatchPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a document with optimization.
        
        Args:
            text: Document text
            request_id: Optional request ID
            priority: Processing priority
            metadata: Additional metadata
            
        Returns:
            Request ID for tracking
        """
        # Add to batcher
        return await self.batcher.add_request(
            text=text,
            request_id=request_id,
            priority=priority,
            metadata=metadata
        )
    
    def record_performance(
        self,
        request_id: str,
        tier: DocumentSizeTier,
        response_time_ms: float,
        tokens_processed: int,
        success: bool = True
    ):
        """
        Record performance metrics for a request.
        
        Args:
            request_id: Request identifier
            tier: Document size tier
            response_time_ms: Response time
            tokens_processed: Tokens processed
            success: Whether request succeeded
        """
        # Get current memory usage
        memory_status = asyncio.run(self.memory_optimizer.check_memory_status())
        memory_mb = memory_status["system_memory_used_gb"] * 1024
        
        # Record in profiler
        self.profiler.record_request(
            tier=tier,
            response_time_ms=response_time_ms,
            tokens_processed=tokens_processed,
            success=success,
            memory_usage_mb=memory_mb
        )
    
    def _cleanup_callback(self):
        """Callback for memory cleanup."""
        logger.info("Performing optimization cleanup")
        # Clear any internal caches
        gc.collect()
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive optimization status."""
        return {
            "status": "enabled" if self._optimization_enabled else "disabled",
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "queue_stats": self.batcher.get_queue_stats(),
            "memory_stats": self.memory_optimizer.get_memory_stats(),
            "cache_stats": self.size_estimator.get_cache_stats(),
            "performance_report": self.profiler.generate_performance_report(),
            "recommendations": self.profiler.get_tuning_recommendations()
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


# Factory function for easy initialization
def create_performance_optimizer(
    process_batch_fn: Callable,
    enable_full_monitoring: bool = True
) -> VLLMPerformanceOptimizer:
    """
    Create a configured VLLMPerformanceOptimizer instance.
    
    Args:
        process_batch_fn: Batch processing function
        enable_full_monitoring: Enable all monitoring features
        
    Returns:
        Configured optimizer instance
    """
    return VLLMPerformanceOptimizer(
        process_batch_fn=process_batch_fn,
        enable_monitoring=enable_full_monitoring,
        enable_auto_tuning=True
    )