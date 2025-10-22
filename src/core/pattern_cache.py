"""
Enhanced Pattern Caching System with LRU + TTL for Entity Extraction Service.

This module provides a high-performance caching layer for pattern loading operations
with support for time-to-live (TTL) expiration and comprehensive metrics tracking.
"""

import time
import logging
from functools import lru_cache, wraps
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import threading


@dataclass
class CacheEntry:
    """Individual cache entry with TTL tracking."""
    data: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    cache_key: str = ""


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    expirations: int = 0
    evictions: int = 0
    total_requests: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        if self.total_requests == 0:
            return 0.0
        return self.misses / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "expirations": self.expirations,
            "evictions": self.evictions,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 4),
            "miss_rate": round(self.miss_rate, 4)
        }


class PatternCache:
    """
    High-performance pattern cache with LRU eviction and TTL expiration.

    Features:
    - LRU (Least Recently Used) eviction policy
    - TTL (Time To Live) expiration with hourly cache keys
    - Thread-safe operations
    - Comprehensive metrics tracking
    - Configurable cache size and TTL
    - Cache warming support
    """

    def __init__(
        self,
        max_size: int = 128,
        ttl_seconds: int = 3600,  # 1 hour default
        enable_metrics: bool = True
    ):
        """
        Initialize PatternCache.

        Args:
            max_size: Maximum number of cache entries
            ttl_seconds: Time-to-live for cache entries in seconds
            enable_metrics: Enable detailed metrics tracking
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_metrics = enable_metrics

        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # Metrics
        self._metrics = CacheMetrics()
        self._method_metrics: Dict[str, CacheMetrics] = defaultdict(CacheMetrics)

        # Logger
        self.logger = logging.getLogger(__name__)

        self.logger.info(
            f"PatternCache initialized: max_size={max_size}, "
            f"ttl_seconds={ttl_seconds}, enable_metrics={enable_metrics}"
        )

    @staticmethod
    def get_time_based_cache_key(granularity: str = "hour") -> str:
        """
        Generate time-based cache key for TTL implementation.

        Args:
            granularity: Time granularity - "hour", "day", "minute"

        Returns:
            str: Time-based cache key
        """
        now = datetime.now()

        if granularity == "minute":
            return now.strftime("%Y%m%d%H%M")
        elif granularity == "day":
            return now.strftime("%Y%m%d")
        else:  # hour (default)
            return now.strftime("%Y%m%d%H")

    def _generate_cache_key(self, method_name: str, *args, **kwargs) -> str:
        """
        Generate unique cache key from method name and arguments.

        Args:
            method_name: Name of the cached method
            *args: Method arguments
            **kwargs: Method keyword arguments

        Returns:
            str: Unique cache key
        """
        # Include time-based component for TTL
        time_key = self.get_time_based_cache_key("hour")

        # Build argument signature
        arg_parts = [str(arg) for arg in args if arg is not None]
        kwarg_parts = [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]

        arg_signature = "_".join(arg_parts + kwarg_parts)

        # Create full cache key
        cache_key = f"{method_name}:{time_key}:{arg_signature}"

        return cache_key

    def _is_expired(self, entry: CacheEntry) -> bool:
        """
        Check if cache entry is expired based on TTL.

        Args:
            entry: Cache entry to check

        Returns:
            bool: True if expired, False otherwise
        """
        age = time.time() - entry.created_at
        return age > self.ttl_seconds

    def _evict_lru(self) -> None:
        """Evict least recently used entry when cache is full."""
        if not self._cache:
            return

        # Find LRU entry (oldest accessed_at)
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].accessed_at)

        del self._cache[lru_key]

        if self.enable_metrics:
            self._metrics.evictions += 1

        self.logger.debug(f"Evicted LRU entry: {lru_key}")

    def _cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            int: Number of entries removed
        """
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                if self.enable_metrics:
                    self._metrics.expirations += 1

        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired entries")

        return len(expired_keys)

    def get(self, cache_key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            cache_key: Cache key

        Returns:
            Optional[Any]: Cached value or None if not found/expired
        """
        with self._lock:
            if cache_key not in self._cache:
                if self.enable_metrics:
                    self._metrics.misses += 1
                    self._metrics.total_requests += 1
                return None

            entry = self._cache[cache_key]

            # Check expiration
            if self._is_expired(entry):
                del self._cache[cache_key]
                if self.enable_metrics:
                    self._metrics.expirations += 1
                    self._metrics.misses += 1
                    self._metrics.total_requests += 1
                return None

            # Update access tracking
            entry.accessed_at = time.time()
            entry.access_count += 1

            if self.enable_metrics:
                self._metrics.hits += 1
                self._metrics.total_requests += 1

            return entry.data

    def set(self, cache_key: str, value: Any) -> None:
        """
        Store value in cache.

        Args:
            cache_key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Cleanup expired entries periodically
            if len(self._cache) % 10 == 0:
                self._cleanup_expired()

            # Evict LRU if cache is full
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                self._evict_lru()

            # Store new entry
            now = time.time()
            self._cache[cache_key] = CacheEntry(
                data=value,
                created_at=now,
                accessed_at=now,
                access_count=1,
                cache_key=cache_key
            )

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            entry_count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cache cleared: {entry_count} entries removed")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache metrics.

        Returns:
            Dict[str, Any]: Cache metrics
        """
        with self._lock:
            return {
                "overall": self._metrics.to_dict(),
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "utilization": round(len(self._cache) / self.max_size, 4) if self.max_size > 0 else 0,
                "method_metrics": {
                    method: metrics.to_dict()
                    for method, metrics in self._method_metrics.items()
                }
            }

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information including entry details.

        Returns:
            Dict[str, Any]: Detailed cache information
        """
        with self._lock:
            entries = []
            now = time.time()

            for key, entry in self._cache.items():
                age = now - entry.created_at
                time_since_access = now - entry.accessed_at

                entries.append({
                    "key": key,
                    "age_seconds": round(age, 2),
                    "time_since_access": round(time_since_access, 2),
                    "access_count": entry.access_count,
                    "is_expired": self._is_expired(entry)
                })

            # Sort by most recently accessed
            entries.sort(key=lambda e: e["time_since_access"])

            return {
                "total_entries": len(entries),
                "entries": entries[:20],  # Limit to top 20
                "metrics": self.get_metrics()
            }

    def cached_method(self, method_name: Optional[str] = None):
        """
        Decorator for caching method results with TTL.

        Args:
            method_name: Optional method name for metrics tracking

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            func_name = method_name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(func_name, *args, **kwargs)

                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    # Update method-specific metrics
                    if self.enable_metrics:
                        with self._lock:
                            self._method_metrics[func_name].hits += 1
                            self._method_metrics[func_name].total_requests += 1

                    self.logger.debug(f"Cache hit for {func_name}: {cache_key}")
                    return cached_value

                # Cache miss - execute function
                self.logger.debug(f"Cache miss for {func_name}: {cache_key}")
                result = func(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result)

                # Update method-specific metrics
                if self.enable_metrics:
                    with self._lock:
                        self._method_metrics[func_name].misses += 1
                        self._method_metrics[func_name].total_requests += 1

                return result

            return wrapper
        return decorator


class CachedPatternLoader:
    """
    Wrapper for PatternLoader that adds caching capabilities.

    This class wraps an existing PatternLoader instance and adds
    caching to frequently called methods.
    """

    def __init__(
        self,
        pattern_loader,
        cache_size: int = 128,
        ttl_seconds: int = 3600
    ):
        """
        Initialize CachedPatternLoader.

        Args:
            pattern_loader: Underlying PatternLoader instance
            cache_size: Maximum cache size
            ttl_seconds: Cache entry TTL in seconds
        """
        self._pattern_loader = pattern_loader
        self._cache = PatternCache(max_size=cache_size, ttl_seconds=ttl_seconds)
        self.logger = logging.getLogger(__name__)

        self.logger.info(
            f"CachedPatternLoader initialized with cache_size={cache_size}, "
            f"ttl_seconds={ttl_seconds}"
        )

    @property
    def cache(self) -> PatternCache:
        """Get the underlying cache instance."""
        return self._cache

    def get_entity_types(self) -> List[str]:
        """Get all entity types (cached)."""
        @self._cache.cached_method("get_entity_types")
        def _get_entity_types():
            return self._pattern_loader.get_entity_types()

        return _get_entity_types()

    def get_patterns_by_entity_type(self, entity_type: str):
        """Get patterns by entity type (cached)."""
        @self._cache.cached_method("get_patterns_by_entity_type")
        def _get_patterns(et: str):
            return self._pattern_loader.get_patterns_by_entity_type(et)

        return _get_patterns(entity_type)

    def get_all_aggregated_examples(self) -> Dict[str, List[str]]:
        """Get all aggregated examples (cached)."""
        @self._cache.cached_method("get_all_aggregated_examples")
        def _get_examples():
            return self._pattern_loader.get_all_aggregated_examples()

        return _get_examples()

    def get_relationship_types(self) -> List[str]:
        """Get all relationship types (cached)."""
        @self._cache.cached_method("get_relationship_types")
        def _get_relationship_types():
            return self._pattern_loader.get_relationship_types()

        return _get_relationship_types()

    def get_entity_type_info(self, entity_type: str) -> Dict[str, Any]:
        """Get entity type info (cached)."""
        @self._cache.cached_method("get_entity_type_info")
        def _get_info(et: str):
            return self._pattern_loader.get_entity_type_info(et)

        return _get_info(entity_type)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return self._cache.get_metrics()

    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        return self._cache.get_cache_info()

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def __getattr__(self, name: str):
        """
        Proxy all other attributes to underlying PatternLoader.

        This allows the CachedPatternLoader to be used as a drop-in
        replacement for PatternLoader.
        """
        return getattr(self._pattern_loader, name)
