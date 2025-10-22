"""
Performance Monitor for Entity Extraction Service

Comprehensive performance monitoring system for tracking local LLM processing,
breakthrough configuration validation, and real-time performance analytics.
Includes monitoring for the 176ms SS tier configuration and fallback behavior.
"""

import asyncio
import json
import logging
import psutil
import threading
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Deque
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PerformanceTier(Enum):
    """Performance tier classifications based on response times."""
    SS_LIGHTNING = "SS+ Lightning"      # < 100ms
    SS_ULTRA_FAST = "SS Ultra-Fast"     # 100-250ms 
    S_EXCEPTIONAL = "S+ Exceptional"    # 250-500ms
    A_FAST = "A Fast"                   # 500-1000ms
    B_STANDARD = "B Standard"           # 1000-2000ms
    C_SLOW = "C Slow"                   # 2000-5000ms
    D_VERY_SLOW = "D Very Slow"         # > 5000ms


class ProcessingMode(Enum):
    """AI processing mode for tracking."""
    LOCAL_ONLY = "local_only"
    REMOTE_ONLY = "remote_only" 
    LOCAL_WITH_REMOTE_FALLBACK = "local_with_remote_fallback"
    REMOTE_WITH_LOCAL_FALLBACK = "remote_with_local_fallback"
    HYBRID_AUTO = "hybrid_auto"


@dataclass
class PerformanceMetric:
    """Individual performance measurement."""
    timestamp: datetime
    operation_type: str
    processing_mode: ProcessingMode
    response_time_ms: float
    performance_tier: PerformanceTier
    tokens_processed: int = 0
    model_config: Dict[str, Any] = None
    success: bool = True
    error_type: Optional[str] = None
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    gpu_usage_percent: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class AggregatedMetrics:
    """Aggregated performance statistics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    performance_tier_distribution: Dict[str, int]
    processing_mode_distribution: Dict[str, int]
    total_tokens_processed: int
    tokens_per_second: float
    error_rate_percent: float
    breakthrough_config_usage_percent: float
    local_processing_success_rate: float
    remote_fallback_rate: float


class PerformanceMonitor:
    """
    Comprehensive performance monitoring for Entity Extraction Service.
    
    Features:
    - Real-time performance tracking for local and remote AI processing
    - Breakthrough configuration validation and monitoring
    - Performance tier classification (SS+ Lightning to D Very Slow)
    - Resource usage monitoring (CPU, memory, GPU)
    - Automatic performance degradation detection
    - Historical performance analytics
    - Health score calculation
    """
    
    def __init__(
        self,
        max_history_size: int = 1000,
        monitoring_interval: float = 30.0,
        performance_window_minutes: int = 15,
        enable_gpu_monitoring: bool = True,
        enable_detailed_logging: bool = True
    ):
        """
        Initialize PerformanceMonitor.
        
        Args:
            max_history_size: Maximum number of metrics to keep in memory
            monitoring_interval: Interval in seconds for background monitoring
            performance_window_minutes: Time window for performance calculations
            enable_gpu_monitoring: Whether to monitor GPU usage
            enable_detailed_logging: Whether to log detailed performance metrics
        """
        self.max_history_size = max_history_size
        self.monitoring_interval = monitoring_interval
        self.performance_window_minutes = performance_window_minutes
        self.enable_gpu_monitoring = enable_gpu_monitoring
        self.enable_detailed_logging = enable_detailed_logging
        
        # Thread-safe metrics storage
        self._metrics_lock = threading.RLock()
        self._metrics_history: Deque[PerformanceMetric] = deque(maxlen=max_history_size)
        
        # Real-time tracking
        self._current_requests = 0
        self._active_operations: Dict[str, datetime] = {}
        
        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Performance baselines and thresholds
        self._breakthrough_thresholds = {
            "target_response_time_ms": 176,  # Target SS tier performance
            "acceptable_response_time_ms": 250,  # SS Ultra-Fast threshold
            "degraded_response_time_ms": 500,   # Performance degradation threshold
            "critical_response_time_ms": 2000   # Critical performance threshold
        }
        
        # LlamaLocalClient-specific monitoring
        self._llama_client_stats = {
            "configuration_profile": None,
            "model_configurations": {},
            "configuration_changes": [],
            "optimization_recommendations": [],
            "last_optimization_check": None
        }
        
        # System resource tracking
        self._system_metrics = {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "last_resource_check": time.time()
        }
        
        logger.info(f"PerformanceMonitor initialized with {max_history_size} history size")
    
    async def start_monitoring(self):
        """Start background performance monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Performance monitoring already running")
            return
        
        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop background performance monitoring."""
        self._shutdown_event.set()
        
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Collect system metrics
                    await self._collect_system_metrics()
                    
                    # Check for performance degradation
                    await self._check_performance_health()
                    
                    # Clean up old metrics
                    await self._cleanup_old_metrics()
                    
                    # Wait for next interval
                    await asyncio.sleep(self.monitoring_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(self.monitoring_interval)
                    
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Performance monitoring loop stopped")
    
    def record_operation_start(self, operation_id: str, operation_type: str) -> str:
        """
        Record the start of an operation.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (e.g., 'entity_validation', 'citation_refinement')
            
        Returns:
            Operation ID for tracking
        """
        with self._metrics_lock:
            self._active_operations[operation_id] = datetime.now()
            self._current_requests += 1
        
        if self.enable_detailed_logging:
            logger.debug(f"Started operation {operation_id} ({operation_type})")
        
        return operation_id
    
    def record_operation_complete(
        self,
        operation_id: str,
        operation_type: str,
        processing_mode: ProcessingMode,
        tokens_processed: int = 0,
        model_config: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record the completion of an operation.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation
            processing_mode: AI processing mode used
            tokens_processed: Number of tokens processed
            model_config: Model configuration used
            success: Whether operation was successful
            error_type: Type of error if failed
            metadata: Additional metadata
        """
        with self._metrics_lock:
            if operation_id not in self._active_operations:
                logger.warning(f"Operation {operation_id} not found in active operations")
                return
            
            start_time = self._active_operations.pop(operation_id)
            self._current_requests = max(0, self._current_requests - 1)
            
            # Calculate response time
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Determine performance tier
            performance_tier = self._classify_performance_tier(response_time_ms)
            
            # Get current system metrics
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent()
            
            # Create performance metric
            metric = PerformanceMetric(
                timestamp=end_time,
                operation_type=operation_type,
                processing_mode=processing_mode,
                response_time_ms=response_time_ms,
                performance_tier=performance_tier,
                tokens_processed=tokens_processed,
                model_config=model_config or {},
                success=success,
                error_type=error_type,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                metadata=metadata or {}
            )
            
            # Store metric
            self._metrics_history.append(metric)
        
        # Log performance results
        if self.enable_detailed_logging:
            status = "SUCCESS" if success else f"FAILED ({error_type})"
            logger.info(
                f"Operation {operation_id} completed: {response_time_ms:.1f}ms "
                f"({performance_tier.value}) - {status}"
            )
            
            # Log breakthrough performance achievements
            if success and response_time_ms <= self._breakthrough_thresholds["target_response_time_ms"]:
                logger.info(f"🚀 BREAKTHROUGH PERFORMANCE: {response_time_ms:.1f}ms (Target: 176ms)")
    
    def _classify_performance_tier(self, response_time_ms: float) -> PerformanceTier:
        """Classify response time into performance tier."""
        if response_time_ms < 100:
            return PerformanceTier.SS_LIGHTNING
        elif response_time_ms < 250:
            return PerformanceTier.SS_ULTRA_FAST
        elif response_time_ms < 500:
            return PerformanceTier.S_EXCEPTIONAL
        elif response_time_ms < 1000:
            return PerformanceTier.A_FAST
        elif response_time_ms < 2000:
            return PerformanceTier.B_STANDARD
        elif response_time_ms < 5000:
            return PerformanceTier.C_SLOW
        else:
            return PerformanceTier.D_VERY_SLOW
    
    async def _collect_system_metrics(self):
        """Collect system resource metrics."""
        try:
            # Update system metrics
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            with self._metrics_lock:
                self._system_metrics.update({
                    "memory_available_gb": memory.available / (1024**3),
                    "memory_used_percent": memory.percent,
                    "cpu_usage_percent": psutil.cpu_percent(interval=1),
                    "disk_available_gb": disk.free / (1024**3),
                    "active_requests": self._current_requests,
                    "last_resource_check": time.time()
                })
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _check_performance_health(self):
        """Check for performance degradation and alert if necessary."""
        try:
            recent_metrics = self.get_recent_metrics(minutes=5)
            if len(recent_metrics) < 5:  # Need minimum data points
                return
            
            # Calculate recent average response time
            response_times = [m.response_time_ms for m in recent_metrics if m.success]
            if not response_times:
                return
            
            avg_response_time = sum(response_times) / len(response_times)
            error_rate = (len([m for m in recent_metrics if not m.success]) / len(recent_metrics)) * 100
            
            # Check for performance degradation
            if avg_response_time > self._breakthrough_thresholds["critical_response_time_ms"]:
                logger.warning(
                    f"CRITICAL performance degradation detected: {avg_response_time:.1f}ms "
                    f"(threshold: {self._breakthrough_thresholds['critical_response_time_ms']}ms)"
                )
            elif avg_response_time > self._breakthrough_thresholds["degraded_response_time_ms"]:
                logger.warning(
                    f"Performance degradation detected: {avg_response_time:.1f}ms "
                    f"(threshold: {self._breakthrough_thresholds['degraded_response_time_ms']}ms)"
                )
            
            # Check error rate
            if error_rate > 10:  # 10% error threshold
                logger.warning(f"High error rate detected: {error_rate:.1f}%")
            
        except Exception as e:
            logger.error(f"Error checking performance health: {e}")
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics beyond the configured window."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)  # Keep 24 hours of data
            
            with self._metrics_lock:
                # Remove old metrics (deque automatically handles max size)
                while self._metrics_history and self._metrics_history[0].timestamp < cutoff_time:
                    self._metrics_history.popleft()
                    
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")
    
    def record_llama_client_stats(self, client_stats: Dict[str, Any]):
        """
        Record LlamaLocalClient performance statistics.
        
        Args:
            client_stats: Statistics from LlamaLocalClient.get_stats()
        """
        with self._metrics_lock:
            # Update configuration profile tracking
            current_profile = client_stats.get("configuration", {}).get("profile_name")
            if current_profile != self._llama_client_stats["configuration_profile"]:
                self._llama_client_stats["configuration_profile"] = current_profile
                self._llama_client_stats["configuration_changes"].append({
                    "timestamp": datetime.now(),
                    "new_profile": current_profile,
                    "configuration": client_stats.get("configuration", {})
                })
            
            # Store current model configuration
            self._llama_client_stats["model_configurations"][current_profile or "default"] = client_stats.get("configuration", {})
    
    async def analyze_llama_performance_and_recommend(self, client_stats: Dict[str, Any]) -> List[str]:
        """
        Analyze LlamaLocalClient performance and provide optimization recommendations.
        
        Args:
            client_stats: Statistics from LlamaLocalClient.get_stats()
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        try:
            performance_analysis = client_stats.get("performance_analysis", {})
            config = client_stats.get("configuration", {})
            
            # Analyze breakthrough achievement rate
            breakthrough_rate = performance_analysis.get("breakthrough_achievement_rate", 0)
            avg_response_time = performance_analysis.get("avg_response_time_ms", float('inf'))
            memory_utilization = performance_analysis.get("memory_utilization", 0)
            error_rate = performance_analysis.get("error_rate", 0)
            
            # Breakthrough performance recommendations
            if breakthrough_rate < 0.8:  # Less than 80% breakthrough achievement
                if avg_response_time > self._breakthrough_thresholds["target_response_time_ms"] * 2:
                    recommendations.append(
                        f"Poor breakthrough performance ({breakthrough_rate:.1%} achievement rate). "
                        f"Consider switching to 'speed_optimized' profile for sub-100ms targets."
                    )
                elif avg_response_time > self._breakthrough_thresholds["target_response_time_ms"] * 1.5:
                    recommendations.append(
                        f"Suboptimal breakthrough performance. Consider reducing n_ctx from "
                        f"{config.get('n_ctx', 'unknown')} to 512 for faster entity extraction."
                    )
            
            # Memory optimization recommendations
            if memory_utilization > 0.9:
                recommendations.append(
                    f"High memory usage ({memory_utilization:.1%}). "
                    f"Consider 'memory_constrained' profile or reduce batch sizes."
                )
            elif memory_utilization > 0.8:
                recommendations.append(
                    f"Elevated memory usage. Consider reducing n_parallel from "
                    f"{config.get('n_parallel', 'unknown')} or enabling memory mapping."
                )
            
            # Error rate recommendations
            if error_rate > 0.1:  # Over 10% error rate
                recommendations.append(
                    f"High error rate ({error_rate:.1%}). Consider increasing timeouts "
                    f"or switching to 'quality_focused' profile for stability."
                )
            elif error_rate > 0.05:  # Over 5% error rate
                recommendations.append(
                    f"Moderate error rate. Consider reducing n_parallel to "
                    f"{max(config.get('n_parallel', 48) - 8, 16)} for better stability."
                )
            
            # Performance tier analysis
            tier_distribution = performance_analysis.get("performance_tier_distribution", {})
            
            # Check for slow performance patterns
            slow_percentage = (
                tier_distribution.get("C_Slow", {}).get("percentage", 0) +
                tier_distribution.get("D_Very_Slow", {}).get("percentage", 0)
            )
            
            if slow_percentage > 20:  # More than 20% slow requests
                recommendations.append(
                    f"High slow request rate ({slow_percentage:.1f}%). "
                    f"Current profile '{config.get('profile_name', 'unknown')}' may not be optimal. "
                    f"Consider 'breakthrough_optimized' profile for consistent performance."
                )
            
            # Configuration-specific recommendations
            current_profile = config.get("profile_name")
            
            if current_profile == "batch_optimized" and breakthrough_rate < 0.5:
                recommendations.append(
                    "Batch profile showing poor breakthrough performance for single documents. "
                    "Consider 'speed_optimized' profile for single-document entity extraction."
                )
            
            if current_profile == "quality_focused" and avg_response_time > 2000:
                recommendations.append(
                    "Quality profile showing excessive latency. Consider 'breakthrough_optimized' "
                    "profile for better balance of quality and speed."
                )
            
            # Resource utilization recommendations
            tokens_per_second = performance_analysis.get("tokens_per_second", 0)
            if tokens_per_second > 0 and tokens_per_second < 50:
                recommendations.append(
                    f"Low token processing rate ({tokens_per_second:.1f} tokens/sec). "
                    f"Consider increasing n_threads from {config.get('n_threads', 'unknown')} "
                    f"or checking GPU utilization."
                )
            
            # Store recommendations
            with self._metrics_lock:
                self._llama_client_stats["optimization_recommendations"] = recommendations
                self._llama_client_stats["last_optimization_check"] = datetime.now()
            
            if recommendations:
                logger.info(f"LlamaLocalClient optimization recommendations generated: {len(recommendations)} items")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing LlamaLocalClient performance: {e}")
            return ["Error analyzing performance - check logs for details"]
    
    def get_llama_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive LlamaLocalClient optimization report."""
        with self._metrics_lock:
            recent_metrics = self.get_recent_metrics(minutes=15)
            
            # Analyze recent performance trends
            if recent_metrics:
                response_times = [m.response_time_ms for m in recent_metrics if m.success]
                breakthrough_count = len([rt for rt in response_times if rt <= self._breakthrough_thresholds["target_response_time_ms"]])
                
                performance_trend = {
                    "total_requests": len(recent_metrics),
                    "successful_requests": len(response_times),
                    "breakthrough_achievements": breakthrough_count,
                    "breakthrough_rate": breakthrough_count / max(len(response_times), 1),
                    "avg_response_time_ms": sum(response_times) / max(len(response_times), 1),
                    "fastest_response_ms": min(response_times) if response_times else 0,
                    "slowest_response_ms": max(response_times) if response_times else 0
                }
            else:
                performance_trend = {"message": "No recent data available"}
            
            return {
                "report_timestamp": datetime.now().isoformat(),
                "current_configuration": self._llama_client_stats.get("configuration_profile"),
                "available_configurations": list(self._llama_client_stats["model_configurations"].keys()),
                "recent_performance": performance_trend,
                "optimization_recommendations": self._llama_client_stats["optimization_recommendations"],
                "configuration_changes_history": [
                    {**change, "timestamp": change["timestamp"].isoformat()} 
                    for change in self._llama_client_stats["configuration_changes"]
                ],
                "last_optimization_check": (
                    self._llama_client_stats["last_optimization_check"].isoformat() 
                    if self._llama_client_stats["last_optimization_check"] else None
                ),
                "breakthrough_thresholds": self._breakthrough_thresholds.copy()
            }
    
    def get_recent_metrics(self, minutes: int = 15) -> List[PerformanceMetric]:
        """Get metrics from the last N minutes."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._metrics_lock:
            return [m for m in self._metrics_history if m.timestamp >= cutoff_time]
    
    def get_aggregated_metrics(self, minutes: int = 15) -> AggregatedMetrics:
        """Get aggregated performance metrics for the specified time window."""
        recent_metrics = self.get_recent_metrics(minutes)
        
        if not recent_metrics:
            return AggregatedMetrics(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0.0,
                min_response_time_ms=0.0,
                max_response_time_ms=0.0,
                p50_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                performance_tier_distribution={},
                processing_mode_distribution={},
                total_tokens_processed=0,
                tokens_per_second=0.0,
                error_rate_percent=0.0,
                breakthrough_config_usage_percent=0.0,
                local_processing_success_rate=0.0,
                remote_fallback_rate=0.0
            )
        
        # Basic counts
        total_requests = len(recent_metrics)
        successful_requests = len([m for m in recent_metrics if m.success])
        failed_requests = total_requests - successful_requests
        
        # Response time statistics
        response_times = [m.response_time_ms for m in recent_metrics]
        response_times.sort()
        
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        p50_index = int(len(response_times) * 0.5)
        p95_index = int(len(response_times) * 0.95)
        p99_index = int(len(response_times) * 0.99)
        
        p50_response_time = response_times[p50_index] if p50_index < len(response_times) else 0
        p95_response_time = response_times[p95_index] if p95_index < len(response_times) else 0
        p99_response_time = response_times[p99_index] if p99_index < len(response_times) else 0
        
        # Performance tier distribution
        tier_counts = defaultdict(int)
        for metric in recent_metrics:
            tier_counts[metric.performance_tier.value] += 1
        
        # Processing mode distribution
        mode_counts = defaultdict(int)
        for metric in recent_metrics:
            mode_counts[metric.processing_mode.value] += 1
        
        # Token processing
        total_tokens = sum(m.tokens_processed for m in recent_metrics)
        time_span_seconds = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds()
        tokens_per_second = total_tokens / max(time_span_seconds, 1)
        
        # Error rate
        error_rate_percent = (failed_requests / total_requests) * 100
        
        # Breakthrough config usage (local processing with fast response)
        breakthrough_requests = len([
            m for m in recent_metrics 
            if m.processing_mode in [ProcessingMode.LOCAL_ONLY, ProcessingMode.LOCAL_WITH_REMOTE_FALLBACK]
            and m.response_time_ms <= self._breakthrough_thresholds["acceptable_response_time_ms"]
            and m.success
        ])
        breakthrough_config_usage_percent = (breakthrough_requests / total_requests) * 100
        
        # Local processing success rate
        local_requests = [
            m for m in recent_metrics
            if m.processing_mode in [ProcessingMode.LOCAL_ONLY, ProcessingMode.LOCAL_WITH_REMOTE_FALLBACK]
        ]
        local_processing_success_rate = (
            len([m for m in local_requests if m.success]) / max(len(local_requests), 1)
        ) * 100
        
        # Remote fallback rate
        fallback_requests = len([
            m for m in recent_metrics
            if m.processing_mode in [ProcessingMode.LOCAL_WITH_REMOTE_FALLBACK, ProcessingMode.REMOTE_WITH_LOCAL_FALLBACK]
        ])
        remote_fallback_rate = (fallback_requests / total_requests) * 100
        
        return AggregatedMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p50_response_time_ms=p50_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            performance_tier_distribution=dict(tier_counts),
            processing_mode_distribution=dict(mode_counts),
            total_tokens_processed=total_tokens,
            tokens_per_second=tokens_per_second,
            error_rate_percent=error_rate_percent,
            breakthrough_config_usage_percent=breakthrough_config_usage_percent,
            local_processing_success_rate=local_processing_success_rate,
            remote_fallback_rate=remote_fallback_rate
        )
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall health score based on recent performance."""
        metrics = self.get_aggregated_metrics(minutes=15)
        
        if metrics.total_requests == 0:
            return {
                "overall_score": 100,
                "status": "healthy",
                "details": "No recent activity to analyze"
            }
        
        # Calculate component scores (0-100)
        scores = {}
        
        # Response time score (target: 176ms breakthrough performance)
        if metrics.avg_response_time_ms <= self._breakthrough_thresholds["target_response_time_ms"]:
            scores["response_time"] = 100
        elif metrics.avg_response_time_ms <= self._breakthrough_thresholds["acceptable_response_time_ms"]:
            scores["response_time"] = 90
        elif metrics.avg_response_time_ms <= self._breakthrough_thresholds["degraded_response_time_ms"]:
            scores["response_time"] = 70
        elif metrics.avg_response_time_ms <= self._breakthrough_thresholds["critical_response_time_ms"]:
            scores["response_time"] = 40
        else:
            scores["response_time"] = 20
        
        # Error rate score
        if metrics.error_rate_percent <= 1:
            scores["error_rate"] = 100
        elif metrics.error_rate_percent <= 5:
            scores["error_rate"] = 80
        elif metrics.error_rate_percent <= 10:
            scores["error_rate"] = 60
        elif metrics.error_rate_percent <= 20:
            scores["error_rate"] = 40
        else:
            scores["error_rate"] = 20
        
        # Breakthrough config usage score
        if metrics.breakthrough_config_usage_percent >= 80:
            scores["breakthrough_usage"] = 100
        elif metrics.breakthrough_config_usage_percent >= 60:
            scores["breakthrough_usage"] = 80
        elif metrics.breakthrough_config_usage_percent >= 40:
            scores["breakthrough_usage"] = 60
        elif metrics.breakthrough_config_usage_percent >= 20:
            scores["breakthrough_usage"] = 40
        else:
            scores["breakthrough_usage"] = 20
        
        # Local processing success score
        if metrics.local_processing_success_rate >= 95:
            scores["local_processing"] = 100
        elif metrics.local_processing_success_rate >= 90:
            scores["local_processing"] = 90
        elif metrics.local_processing_success_rate >= 80:
            scores["local_processing"] = 70
        elif metrics.local_processing_success_rate >= 70:
            scores["local_processing"] = 50
        else:
            scores["local_processing"] = 30
        
        # Calculate weighted overall score
        weights = {
            "response_time": 0.4,
            "error_rate": 0.3,
            "breakthrough_usage": 0.2,
            "local_processing": 0.1
        }
        
        overall_score = sum(scores[key] * weights[key] for key in scores)
        
        # Determine status
        if overall_score >= 90:
            status = "excellent"
        elif overall_score >= 80:
            status = "healthy"
        elif overall_score >= 70:
            status = "good"
        elif overall_score >= 60:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            "overall_score": round(overall_score, 1),
            "status": status,
            "component_scores": scores,
            "metrics": asdict(metrics),
            "system_metrics": self._system_metrics.copy(),
            "thresholds": self._breakthrough_thresholds.copy()
        }
    
    def export_metrics(self, file_path: str, format: str = "json"):
        """Export performance metrics to file."""
        try:
            metrics_data = {
                "export_timestamp": datetime.now().isoformat(),
                "metrics": [asdict(m) for m in self._metrics_history],
                "aggregated": asdict(self.get_aggregated_metrics()),
                "health_score": self.get_health_score(),
                "system_metrics": self._system_metrics.copy()
            }
            
            # Convert datetime objects to strings for JSON serialization
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            with open(file_path, 'w') as f:
                if format.lower() == "json":
                    json.dump(metrics_data, f, indent=2, default=serialize_datetime)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Performance metrics exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_monitoring()


# Utility functions for integration
def create_performance_monitor(settings) -> PerformanceMonitor:
    """Create PerformanceMonitor with service settings."""
    return PerformanceMonitor(
        max_history_size=settings.performance.result_cache_size,
        monitoring_interval=settings.performance.memory_check_interval_seconds,
        performance_window_minutes=15,
        enable_gpu_monitoring=True,
        enable_detailed_logging=settings.logging.log_performance_metrics
    )