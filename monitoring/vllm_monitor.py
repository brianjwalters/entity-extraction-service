#!/usr/bin/env python3
"""
vLLM Service Performance Monitor

Comprehensive monitoring solution for vLLM services including:
- GPU utilization and memory tracking
- Response time monitoring with alert thresholds
- Timeout threshold warnings (50%, 75%, 90% of limits)
- Large document processing metrics
- Service health monitoring and automated alerts
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Deque, Tuple
import httpx
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ProcessingStatus(Enum):
    """Document processing status."""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT_WARNING = "timeout_warning"
    TIMEOUT_CRITICAL = "timeout_critical"


@dataclass
class GPUMetrics:
    """GPU utilization metrics."""
    timestamp: datetime
    gpu_id: int
    gpu_name: str
    memory_used_mb: int
    memory_total_mb: int
    memory_utilization_percent: float
    gpu_utilization_percent: int
    temperature_celsius: int
    power_draw_watts: Optional[float] = None


@dataclass
class ServiceMetrics:
    """Service performance metrics."""
    timestamp: datetime
    service_name: str
    response_time_ms: float
    request_id: str
    document_size_kb: Optional[int] = None
    chunk_count: Optional[int] = None
    token_count: Optional[int] = None
    success: bool
    error_type: Optional[str] = None
    timeout_percentage: float = 0.0  # Percentage of timeout limit used


@dataclass
class Alert:
    """System alert."""
    timestamp: datetime
    level: AlertLevel
    service: str
    message: str
    metrics: Dict[str, Any]
    auto_resolved: bool = False


class VLLMMonitor:
    """
    Comprehensive monitoring system for vLLM services.

    Features:
    - Real-time GPU monitoring (memory, utilization, temperature)
    - Service response time tracking with multi-tier alerts
    - Timeout threshold warnings at 50%, 75%, and 90% of limits
    - Large document processing performance tracking
    - Automated alert generation and resolution
    - Performance dashboard generation
    """

    def __init__(
        self,
        vllm_service_url: str = "http://localhost:8080",
        entity_extraction_url: str = "http://localhost:8007",
        document_upload_url: str = "http://localhost:8008",
        monitoring_interval: int = 30,  # seconds
        gpu_check_interval: int = 10,   # seconds
        max_history_size: int = 10000,
        alert_log_path: str = "/srv/luris/be/monitoring/alerts.log",
        metrics_export_path: str = "/srv/luris/be/monitoring/metrics"
    ):
        """
        Initialize vLLM Monitor.

        Args:
            vllm_service_url: vLLM service endpoint
            entity_extraction_url: Entity extraction service endpoint
            document_upload_url: Document upload service endpoint
            monitoring_interval: Interval for service health checks
            gpu_check_interval: Interval for GPU monitoring
            max_history_size: Maximum metrics history to retain
            alert_log_path: Path for alert logs
            metrics_export_path: Path for metrics export
        """
        self.vllm_service_url = vllm_service_url
        self.entity_extraction_url = entity_extraction_url
        self.document_upload_url = document_upload_url
        self.monitoring_interval = monitoring_interval
        self.gpu_check_interval = gpu_check_interval
        self.max_history_size = max_history_size
        self.alert_log_path = Path(alert_log_path)
        self.metrics_export_path = Path(metrics_export_path)

        # Ensure directories exist
        self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_export_path.mkdir(parents=True, exist_ok=True)

        # Metrics storage
        self.gpu_metrics: Deque[GPUMetrics] = deque(maxlen=max_history_size)
        self.service_metrics: Deque[ServiceMetrics] = deque(maxlen=max_history_size)
        self.alerts: Deque[Alert] = deque(maxlen=1000)
        self.active_requests: Dict[str, Dict[str, Any]] = {}

        # Alert thresholds
        self.thresholds = {
            # Response time thresholds (milliseconds)
            "response_time_warning": 30000,      # 30 seconds
            "response_time_critical": 60000,     # 1 minute

            # Timeout thresholds (percentage of limit)
            "timeout_warning_1": 50,             # 50% of timeout (15 minutes)
            "timeout_warning_2": 75,             # 75% of timeout (22.5 minutes)
            "timeout_critical": 90,              # 90% of timeout (27 minutes)

            # GPU thresholds
            "gpu_memory_warning": 85,            # 85% memory utilization
            "gpu_memory_critical": 95,           # 95% memory utilization
            "gpu_utilization_low": 20,           # Under-utilization warning
            "gpu_temperature_warning": 80,       # 80°C temperature warning
            "gpu_temperature_critical": 85,      # 85°C temperature critical

            # Service health
            "error_rate_warning": 5,             # 5% error rate
            "error_rate_critical": 10,           # 10% error rate
        }

        # Timeout configurations (milliseconds)
        self.timeout_limits = {
            "vllm_service": 1800000,             # 30 minutes
            "entity_extraction": 1800000,        # 30 minutes
            "document_upload": 1800000,          # 30 minutes (Marker)
        }

        # Monitoring tasks
        self.monitoring_tasks = []
        self.shutdown_event = asyncio.Event()

        logger.info(f"vLLM Monitor initialized - Monitoring interval: {monitoring_interval}s")

    async def start(self):
        """Start all monitoring tasks."""
        logger.info("Starting vLLM monitoring system...")

        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._gpu_monitoring_loop()),
            asyncio.create_task(self._service_monitoring_loop()),
            asyncio.create_task(self._timeout_monitoring_loop()),
            asyncio.create_task(self._alert_processing_loop()),
            asyncio.create_task(self._metrics_export_loop()),
        ]

        logger.info("All monitoring tasks started successfully")

    async def stop(self):
        """Stop all monitoring tasks."""
        logger.info("Stopping vLLM monitoring system...")
        self.shutdown_event.set()

        # Cancel all tasks
        for task in self.monitoring_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)

        # Export final metrics
        await self.export_metrics()

        logger.info("vLLM monitoring system stopped")

    async def _gpu_monitoring_loop(self):
        """Monitor GPU utilization and memory."""
        while not self.shutdown_event.is_set():
            try:
                gpu_metrics = await self.collect_gpu_metrics()

                for metric in gpu_metrics:
                    self.gpu_metrics.append(metric)
                    await self.check_gpu_thresholds(metric)

                await asyncio.sleep(self.gpu_check_interval)

            except Exception as e:
                logger.error(f"GPU monitoring error: {e}")
                await asyncio.sleep(self.gpu_check_interval)

    async def collect_gpu_metrics(self) -> List[GPUMetrics]:
        """Collect GPU metrics using nvidia-smi."""
        try:
            # Query GPU metrics
            cmd = [
                "nvidia-smi",
                "--query-gpu=timestamp,index,name,memory.used,memory.total,utilization.gpu,utilization.memory,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                logger.error(f"nvidia-smi failed: {result.stderr}")
                return []

            metrics = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split(', ')
                if len(parts) >= 8:
                    try:
                        metric = GPUMetrics(
                            timestamp=datetime.now(),
                            gpu_id=int(parts[1]),
                            gpu_name=parts[2],
                            memory_used_mb=int(float(parts[3])),
                            memory_total_mb=int(float(parts[4])),
                            memory_utilization_percent=float(parts[6]) if parts[6] != '[N/A]' else 0.0,
                            gpu_utilization_percent=int(parts[5]) if parts[5] != '[N/A]' else 0,
                            temperature_celsius=int(parts[7]) if parts[7] != '[N/A]' else 0,
                            power_draw_watts=float(parts[8]) if len(parts) > 8 and parts[8] != '[N/A]' else None
                        )
                        metrics.append(metric)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse GPU metric line: {line}, error: {e}")

            return metrics

        except subprocess.TimeoutExpired:
            logger.error("nvidia-smi command timed out")
            return []
        except Exception as e:
            logger.error(f"Failed to collect GPU metrics: {e}")
            return []

    async def check_gpu_thresholds(self, metric: GPUMetrics):
        """Check GPU metrics against thresholds and generate alerts."""
        alerts_generated = []

        # Memory utilization checks
        memory_percent = (metric.memory_used_mb / metric.memory_total_mb) * 100

        if memory_percent >= self.thresholds["gpu_memory_critical"]:
            alerts_generated.append(Alert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                service=f"GPU_{metric.gpu_id}",
                message=f"Critical GPU memory usage: {memory_percent:.1f}% ({metric.memory_used_mb}MB/{metric.memory_total_mb}MB)",
                metrics={
                    "gpu_id": metric.gpu_id,
                    "memory_percent": memory_percent,
                    "memory_used_mb": metric.memory_used_mb,
                    "threshold": self.thresholds["gpu_memory_critical"]
                }
            ))
        elif memory_percent >= self.thresholds["gpu_memory_warning"]:
            alerts_generated.append(Alert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                service=f"GPU_{metric.gpu_id}",
                message=f"High GPU memory usage: {memory_percent:.1f}% ({metric.memory_used_mb}MB/{metric.memory_total_mb}MB)",
                metrics={
                    "gpu_id": metric.gpu_id,
                    "memory_percent": memory_percent,
                    "memory_used_mb": metric.memory_used_mb,
                    "threshold": self.thresholds["gpu_memory_warning"]
                }
            ))

        # GPU utilization checks
        if metric.gpu_utilization_percent < self.thresholds["gpu_utilization_low"] and memory_percent > 50:
            alerts_generated.append(Alert(
                timestamp=datetime.now(),
                level=AlertLevel.INFO,
                service=f"GPU_{metric.gpu_id}",
                message=f"GPU under-utilized: {metric.gpu_utilization_percent}% with {memory_percent:.1f}% memory used",
                metrics={
                    "gpu_id": metric.gpu_id,
                    "gpu_utilization": metric.gpu_utilization_percent,
                    "memory_percent": memory_percent
                }
            ))

        # Temperature checks
        if metric.temperature_celsius >= self.thresholds["gpu_temperature_critical"]:
            alerts_generated.append(Alert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                service=f"GPU_{metric.gpu_id}",
                message=f"Critical GPU temperature: {metric.temperature_celsius}°C",
                metrics={
                    "gpu_id": metric.gpu_id,
                    "temperature": metric.temperature_celsius,
                    "threshold": self.thresholds["gpu_temperature_critical"]
                }
            ))
        elif metric.temperature_celsius >= self.thresholds["gpu_temperature_warning"]:
            alerts_generated.append(Alert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                service=f"GPU_{metric.gpu_id}",
                message=f"High GPU temperature: {metric.temperature_celsius}°C",
                metrics={
                    "gpu_id": metric.gpu_id,
                    "temperature": metric.temperature_celsius,
                    "threshold": self.thresholds["gpu_temperature_warning"]
                }
            ))

        # Add alerts to queue
        for alert in alerts_generated:
            self.alerts.append(alert)
            logger.warning(f"GPU Alert: {alert.message}")

    async def _service_monitoring_loop(self):
        """Monitor service health and response times."""
        while not self.shutdown_event.is_set():
            try:
                # Check vLLM service
                await self.check_service_health("vllm_service", self.vllm_service_url)

                # Check entity extraction service
                await self.check_service_health("entity_extraction", self.entity_extraction_url)

                # Check document upload service
                await self.check_service_health("document_upload", self.document_upload_url)

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Service monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def check_service_health(self, service_name: str, service_url: str):
        """Check service health and response time."""
        try:
            start_time = time.time()

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service_url}/health")
                response_time_ms = (time.time() - start_time) * 1000

                metric = ServiceMetrics(
                    timestamp=datetime.now(),
                    service_name=service_name,
                    response_time_ms=response_time_ms,
                    request_id=f"health_check_{int(time.time())}",
                    success=response.status_code == 200,
                    error_type=None if response.status_code == 200 else f"HTTP_{response.status_code}"
                )

                self.service_metrics.append(metric)

                # Check response time thresholds
                if response_time_ms > self.thresholds["response_time_critical"]:
                    self.alerts.append(Alert(
                        timestamp=datetime.now(),
                        level=AlertLevel.CRITICAL,
                        service=service_name,
                        message=f"Critical response time: {response_time_ms:.0f}ms",
                        metrics={"response_time_ms": response_time_ms}
                    ))
                elif response_time_ms > self.thresholds["response_time_warning"]:
                    self.alerts.append(Alert(
                        timestamp=datetime.now(),
                        level=AlertLevel.WARNING,
                        service=service_name,
                        message=f"Slow response time: {response_time_ms:.0f}ms",
                        metrics={"response_time_ms": response_time_ms}
                    ))

        except httpx.TimeoutException:
            self.alerts.append(Alert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                service=service_name,
                message=f"Service health check timeout",
                metrics={"timeout": True}
            ))
        except Exception as e:
            self.alerts.append(Alert(
                timestamp=datetime.now(),
                level=AlertLevel.CRITICAL,
                service=service_name,
                message=f"Service health check failed: {str(e)}",
                metrics={"error": str(e)}
            ))

    def track_request_start(self, request_id: str, service_name: str, document_size_kb: Optional[int] = None):
        """Track the start of a request for timeout monitoring."""
        self.active_requests[request_id] = {
            "service": service_name,
            "start_time": time.time(),
            "document_size_kb": document_size_kb,
            "warnings_sent": set()
        }
        logger.info(f"Tracking request {request_id} for {service_name}")

    def track_request_complete(self, request_id: str, success: bool = True, error_type: Optional[str] = None):
        """Track request completion."""
        if request_id in self.active_requests:
            request_data = self.active_requests.pop(request_id)
            elapsed_ms = (time.time() - request_data["start_time"]) * 1000

            metric = ServiceMetrics(
                timestamp=datetime.now(),
                service_name=request_data["service"],
                response_time_ms=elapsed_ms,
                request_id=request_id,
                document_size_kb=request_data.get("document_size_kb"),
                success=success,
                error_type=error_type,
                timeout_percentage=(elapsed_ms / self.timeout_limits.get(request_data["service"], 1800000)) * 100
            )

            self.service_metrics.append(metric)
            logger.info(f"Request {request_id} completed in {elapsed_ms:.0f}ms ({metric.timeout_percentage:.1f}% of timeout)")

    async def _timeout_monitoring_loop(self):
        """Monitor active requests for timeout warnings."""
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()

                for request_id, request_data in list(self.active_requests.items()):
                    elapsed_ms = (current_time - request_data["start_time"]) * 1000
                    service = request_data["service"]
                    timeout_limit = self.timeout_limits.get(service, 1800000)
                    timeout_percentage = (elapsed_ms / timeout_limit) * 100

                    # Check timeout thresholds
                    if timeout_percentage >= self.thresholds["timeout_critical"] and "90" not in request_data["warnings_sent"]:
                        self.alerts.append(Alert(
                            timestamp=datetime.now(),
                            level=AlertLevel.CRITICAL,
                            service=service,
                            message=f"Request {request_id} at {timeout_percentage:.0f}% of timeout ({elapsed_ms/1000:.0f}s/{timeout_limit/1000:.0f}s)",
                            metrics={
                                "request_id": request_id,
                                "elapsed_ms": elapsed_ms,
                                "timeout_percentage": timeout_percentage,
                                "document_size_kb": request_data.get("document_size_kb")
                            }
                        ))
                        request_data["warnings_sent"].add("90")

                    elif timeout_percentage >= self.thresholds["timeout_warning_2"] and "75" not in request_data["warnings_sent"]:
                        self.alerts.append(Alert(
                            timestamp=datetime.now(),
                            level=AlertLevel.WARNING,
                            service=service,
                            message=f"Request {request_id} at {timeout_percentage:.0f}% of timeout ({elapsed_ms/1000:.0f}s/{timeout_limit/1000:.0f}s)",
                            metrics={
                                "request_id": request_id,
                                "elapsed_ms": elapsed_ms,
                                "timeout_percentage": timeout_percentage,
                                "document_size_kb": request_data.get("document_size_kb")
                            }
                        ))
                        request_data["warnings_sent"].add("75")

                    elif timeout_percentage >= self.thresholds["timeout_warning_1"] and "50" not in request_data["warnings_sent"]:
                        self.alerts.append(Alert(
                            timestamp=datetime.now(),
                            level=AlertLevel.INFO,
                            service=service,
                            message=f"Request {request_id} at {timeout_percentage:.0f}% of timeout ({elapsed_ms/1000:.0f}s/{timeout_limit/1000:.0f}s)",
                            metrics={
                                "request_id": request_id,
                                "elapsed_ms": elapsed_ms,
                                "timeout_percentage": timeout_percentage,
                                "document_size_kb": request_data.get("document_size_kb")
                            }
                        ))
                        request_data["warnings_sent"].add("50")

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Timeout monitoring error: {e}")
                await asyncio.sleep(30)

    async def _alert_processing_loop(self):
        """Process and log alerts."""
        while not self.shutdown_event.is_set():
            try:
                # Process recent alerts
                if self.alerts:
                    await self.process_alerts()

                await asyncio.sleep(60)  # Process alerts every minute

            except Exception as e:
                logger.error(f"Alert processing error: {e}")
                await asyncio.sleep(60)

    async def process_alerts(self):
        """Process and log recent alerts."""
        try:
            # Group alerts by service and level
            alert_summary = defaultdict(lambda: defaultdict(list))

            for alert in list(self.alerts)[-100:]:  # Process last 100 alerts
                alert_summary[alert.service][alert.level].append(alert)

            # Log alert summary
            if alert_summary:
                with open(self.alert_log_path, 'a') as f:
                    timestamp = datetime.now().isoformat()
                    f.write(f"\n=== Alert Summary {timestamp} ===\n")

                    for service, levels in alert_summary.items():
                        f.write(f"\nService: {service}\n")
                        for level, alerts in levels.items():
                            f.write(f"  {level.value.upper()}: {len(alerts)} alerts\n")
                            for alert in alerts[-5:]:  # Show last 5 of each type
                                f.write(f"    - {alert.message}\n")

                logger.info(f"Processed {sum(len(alerts) for levels in alert_summary.values() for alerts in levels.values())} alerts")

        except Exception as e:
            logger.error(f"Failed to process alerts: {e}")

    async def _metrics_export_loop(self):
        """Periodically export metrics to files."""
        while not self.shutdown_event.is_set():
            try:
                await self.export_metrics()
                await asyncio.sleep(300)  # Export every 5 minutes

            except Exception as e:
                logger.error(f"Metrics export error: {e}")
                await asyncio.sleep(300)

    async def export_metrics(self):
        """Export current metrics to JSON files."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Export GPU metrics
            gpu_file = self.metrics_export_path / f"gpu_metrics_{timestamp}.json"
            gpu_data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": [asdict(m) for m in list(self.gpu_metrics)[-1000:]],
                "summary": self.get_gpu_summary()
            }

            with open(gpu_file, 'w') as f:
                json.dump(gpu_data, f, indent=2, default=str)

            # Export service metrics
            service_file = self.metrics_export_path / f"service_metrics_{timestamp}.json"
            service_data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": [asdict(m) for m in list(self.service_metrics)[-1000:]],
                "summary": self.get_service_summary()
            }

            with open(service_file, 'w') as f:
                json.dump(service_data, f, indent=2, default=str)

            # Export alerts
            alert_file = self.metrics_export_path / f"alerts_{timestamp}.json"
            alert_data = {
                "timestamp": datetime.now().isoformat(),
                "alerts": [asdict(a) for a in list(self.alerts)[-500:]],
                "summary": self.get_alert_summary()
            }

            with open(alert_file, 'w') as f:
                json.dump(alert_data, f, indent=2, default=str)

            logger.info(f"Metrics exported to {self.metrics_export_path}")

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

    def get_gpu_summary(self) -> Dict[str, Any]:
        """Get GPU metrics summary."""
        if not self.gpu_metrics:
            return {"message": "No GPU metrics available"}

        recent_metrics = list(self.gpu_metrics)[-100:]

        # Group by GPU ID
        gpu_summaries = defaultdict(lambda: {
            "memory_used_mb": [],
            "memory_percent": [],
            "gpu_utilization": [],
            "temperature": []
        })

        for metric in recent_metrics:
            memory_percent = (metric.memory_used_mb / metric.memory_total_mb) * 100
            gpu_summaries[metric.gpu_id]["memory_used_mb"].append(metric.memory_used_mb)
            gpu_summaries[metric.gpu_id]["memory_percent"].append(memory_percent)
            gpu_summaries[metric.gpu_id]["gpu_utilization"].append(metric.gpu_utilization_percent)
            gpu_summaries[metric.gpu_id]["temperature"].append(metric.temperature_celsius)

        summary = {}
        for gpu_id, data in gpu_summaries.items():
            summary[f"GPU_{gpu_id}"] = {
                "avg_memory_mb": sum(data["memory_used_mb"]) / len(data["memory_used_mb"]),
                "max_memory_mb": max(data["memory_used_mb"]),
                "avg_memory_percent": sum(data["memory_percent"]) / len(data["memory_percent"]),
                "max_memory_percent": max(data["memory_percent"]),
                "avg_gpu_utilization": sum(data["gpu_utilization"]) / len(data["gpu_utilization"]),
                "max_gpu_utilization": max(data["gpu_utilization"]),
                "avg_temperature": sum(data["temperature"]) / len(data["temperature"]),
                "max_temperature": max(data["temperature"])
            }

        return summary

    def get_service_summary(self) -> Dict[str, Any]:
        """Get service metrics summary."""
        if not self.service_metrics:
            return {"message": "No service metrics available"}

        recent_metrics = list(self.service_metrics)[-500:]

        # Group by service
        service_summaries = defaultdict(lambda: {
            "response_times": [],
            "success_count": 0,
            "error_count": 0,
            "timeout_percentages": []
        })

        for metric in recent_metrics:
            service_summaries[metric.service_name]["response_times"].append(metric.response_time_ms)
            if metric.success:
                service_summaries[metric.service_name]["success_count"] += 1
            else:
                service_summaries[metric.service_name]["error_count"] += 1
            if metric.timeout_percentage > 0:
                service_summaries[metric.service_name]["timeout_percentages"].append(metric.timeout_percentage)

        summary = {}
        for service, data in service_summaries.items():
            response_times = sorted(data["response_times"])
            total_requests = data["success_count"] + data["error_count"]

            summary[service] = {
                "total_requests": total_requests,
                "success_rate": (data["success_count"] / total_requests * 100) if total_requests > 0 else 0,
                "error_rate": (data["error_count"] / total_requests * 100) if total_requests > 0 else 0,
                "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "p50_response_time_ms": response_times[len(response_times)//2] if response_times else 0,
                "p95_response_time_ms": response_times[int(len(response_times)*0.95)] if response_times else 0,
                "p99_response_time_ms": response_times[int(len(response_times)*0.99)] if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "avg_timeout_percentage": sum(data["timeout_percentages"]) / len(data["timeout_percentages"]) if data["timeout_percentages"] else 0,
                "max_timeout_percentage": max(data["timeout_percentages"]) if data["timeout_percentages"] else 0
            }

        return summary

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        if not self.alerts:
            return {"message": "No alerts"}

        recent_alerts = list(self.alerts)[-100:]

        # Count by level and service
        alert_counts = defaultdict(lambda: defaultdict(int))

        for alert in recent_alerts:
            alert_counts[alert.level.value][alert.service] += 1

        return {
            "total_alerts": len(recent_alerts),
            "by_level": dict(alert_counts),
            "most_recent": recent_alerts[-1].message if recent_alerts else None
        }

    async def generate_dashboard(self) -> str:
        """Generate a text-based performance dashboard."""
        dashboard = []
        dashboard.append("=" * 80)
        dashboard.append(f"vLLM Performance Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        dashboard.append("=" * 80)

        # GPU Status
        dashboard.append("\n### GPU Status ###")
        gpu_summary = self.get_gpu_summary()
        for gpu_name, stats in gpu_summary.items():
            if isinstance(stats, dict):
                dashboard.append(f"\n{gpu_name}:")
                dashboard.append(f"  Memory: {stats['avg_memory_mb']:.0f}MB avg, {stats['max_memory_mb']:.0f}MB max ({stats['avg_memory_percent']:.1f}% avg)")
                dashboard.append(f"  GPU Util: {stats['avg_gpu_utilization']:.0f}% avg, {stats['max_gpu_utilization']:.0f}% max")
                dashboard.append(f"  Temperature: {stats['avg_temperature']:.0f}°C avg, {stats['max_temperature']:.0f}°C max")

        # Service Status
        dashboard.append("\n### Service Performance ###")
        service_summary = self.get_service_summary()
        for service, stats in service_summary.items():
            if isinstance(stats, dict):
                dashboard.append(f"\n{service}:")
                dashboard.append(f"  Requests: {stats['total_requests']} total, {stats['success_rate']:.1f}% success rate")
                dashboard.append(f"  Response Time: {stats['avg_response_time_ms']:.0f}ms avg, {stats['p95_response_time_ms']:.0f}ms p95, {stats['max_response_time_ms']:.0f}ms max")
                if stats['max_timeout_percentage'] > 0:
                    dashboard.append(f"  Timeout Usage: {stats['avg_timeout_percentage']:.1f}% avg, {stats['max_timeout_percentage']:.1f}% max")

        # Active Requests
        dashboard.append("\n### Active Requests ###")
        if self.active_requests:
            for request_id, data in list(self.active_requests.items())[:5]:
                elapsed_s = time.time() - data["start_time"]
                timeout_pct = (elapsed_s * 1000 / self.timeout_limits.get(data["service"], 1800000)) * 100
                dashboard.append(f"  {request_id}: {data['service']} - {elapsed_s:.0f}s ({timeout_pct:.0f}% of timeout)")
        else:
            dashboard.append("  No active requests")

        # Recent Alerts
        dashboard.append("\n### Recent Alerts ###")
        alert_summary = self.get_alert_summary()
        if alert_summary.get("by_level"):
            for level, services in alert_summary["by_level"].items():
                dashboard.append(f"  {level.upper()}: {sum(services.values())} alerts")
                for service, count in list(services.items())[:3]:
                    dashboard.append(f"    - {service}: {count} alerts")
        else:
            dashboard.append("  No recent alerts")

        dashboard.append("\n" + "=" * 80)

        return "\n".join(dashboard)


async def main():
    """Main monitoring loop."""
    monitor = VLLMMonitor()

    try:
        await monitor.start()

        # Print dashboard periodically
        while True:
            dashboard = await monitor.generate_dashboard()
            print("\033[2J\033[H")  # Clear screen
            print(dashboard)

            # Example: Track a simulated request
            if len(monitor.active_requests) < 2:
                request_id = f"test_{int(time.time())}"
                monitor.track_request_start(request_id, "vllm_service", document_size_kb=1024)

            await asyncio.sleep(30)

    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())