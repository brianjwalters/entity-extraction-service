#!/usr/bin/env python3
"""
Comprehensive Metrics Collection System for vLLM Optimization Testing

This module provides real-time collection of GPU, vLLM performance, and system metrics
during optimization testing. It supports async collection, multiple export formats,
and real-time monitoring capabilities.

Author: Performance Engineer
Date: 2025-09-09
"""

import asyncio
import json
import csv
import subprocess
import time
import psutil
import aiohttp
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from collections import deque
from enum import Enum
import logging
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics being collected"""
    GPU = "gpu"
    VLLM = "vllm"
    SYSTEM = "system"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


@dataclass
class GPUMetrics:
    """GPU metrics for a single GPU"""
    gpu_id: int
    utilization_percent: float
    memory_used_mb: int
    memory_free_mb: int
    memory_total_mb: int
    temperature_c: Optional[float] = None
    power_draw_w: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class VLLMMetrics:
    """vLLM performance metrics"""
    tokens_per_second: float
    mean_latency_ms: float
    first_token_latency_ms: Optional[float] = None
    p50_latency_ms: Optional[float] = None
    p90_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None
    request_queue_size: Optional[int] = None
    active_batch_size: Optional[int] = None
    total_requests_processed: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SystemMetrics:
    """System-wide metrics"""
    cpu_percent: float
    memory_used_gb: float
    memory_available_gb: float
    memory_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    disk_read_bytes: int
    disk_write_bytes: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MetricsSnapshot:
    """Complete metrics snapshot at a point in time"""
    timestamp: str
    config_id: str
    gpu_metrics: Dict[str, GPUMetrics]
    vllm_metrics: Optional[VLLMMetrics]
    system_metrics: SystemMetrics
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "config_id": self.config_id,
            "gpu_metrics": {
                gpu_id: {
                    "utilization": metrics.utilization_percent,
                    "memory_used_mb": metrics.memory_used_mb,
                    "memory_free_mb": metrics.memory_free_mb,
                    "memory_total_mb": metrics.memory_total_mb,
                    "temp_c": metrics.temperature_c,
                    "power_w": metrics.power_draw_w
                }
                for gpu_id, metrics in self.gpu_metrics.items()
            },
            "vllm_metrics": {
                "tokens_per_second": self.vllm_metrics.tokens_per_second,
                "first_token_latency_ms": self.vllm_metrics.first_token_latency_ms,
                "mean_latency_ms": self.vllm_metrics.mean_latency_ms,
                "p50_latency_ms": self.vllm_metrics.p50_latency_ms,
                "p90_latency_ms": self.vllm_metrics.p90_latency_ms,
                "p99_latency_ms": self.vllm_metrics.p99_latency_ms,
                "request_queue_size": self.vllm_metrics.request_queue_size,
                "active_batch_size": self.vllm_metrics.active_batch_size,
                "total_requests": self.vllm_metrics.total_requests_processed
            } if self.vllm_metrics else None,
            "system_metrics": {
                "cpu_percent": self.system_metrics.cpu_percent,
                "memory_gb": self.system_metrics.memory_used_gb,
                "memory_available_gb": self.system_metrics.memory_available_gb,
                "network_sent_bytes": self.system_metrics.network_bytes_sent,
                "network_recv_bytes": self.system_metrics.network_bytes_recv,
                "disk_read_bytes": self.system_metrics.disk_read_bytes,
                "disk_write_bytes": self.system_metrics.disk_write_bytes
            }
        }


class GPUMonitor:
    """Monitor GPU metrics using nvidia-smi"""
    
    def __init__(self, gpu_ids: List[int] = None):
        """
        Initialize GPU monitor
        
        Args:
            gpu_ids: List of GPU IDs to monitor. If None, monitors all GPUs.
        """
        self.gpu_ids = gpu_ids or self._detect_gpus()
        logger.info(f"Monitoring GPUs: {self.gpu_ids}")
    
    def _detect_gpus(self) -> List[int]:
        """Detect available GPUs"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                check=True
            )
            return [int(idx.strip()) for idx in result.stdout.strip().split('\n')]
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("nvidia-smi not available, GPU monitoring disabled")
            return []
    
    async def collect_metrics(self) -> Dict[str, GPUMetrics]:
        """Collect current GPU metrics"""
        if not self.gpu_ids:
            return {}
        
        metrics = {}
        for gpu_id in self.gpu_ids:
            try:
                # Query nvidia-smi for specific GPU
                query_fields = [
                    "gpu_name",
                    "utilization.gpu",
                    "memory.used",
                    "memory.free",
                    "memory.total",
                    "temperature.gpu",
                    "power.draw"
                ]
                
                cmd = [
                    "nvidia-smi",
                    f"--id={gpu_id}",
                    f"--query-gpu={','.join(query_fields)}",
                    "--format=csv,noheader,nounits"
                ]
                
                # Run command asynchronously
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    values = stdout.decode().strip().split(', ')
                    
                    # Parse metrics
                    metrics[f"gpu_{gpu_id}"] = GPUMetrics(
                        gpu_id=gpu_id,
                        utilization_percent=float(values[1]) if values[1] != 'N/A' else 0.0,
                        memory_used_mb=int(values[2]) if values[2] != 'N/A' else 0,
                        memory_free_mb=int(values[3]) if values[3] != 'N/A' else 0,
                        memory_total_mb=int(values[4]) if values[4] != 'N/A' else 0,
                        temperature_c=float(values[5]) if values[5] != 'N/A' else None,
                        power_draw_w=float(values[6]) if values[6] != 'N/A' else None
                    )
                else:
                    logger.error(f"Failed to query GPU {gpu_id}: {stderr.decode()}")
                    
            except Exception as e:
                logger.error(f"Error collecting GPU {gpu_id} metrics: {e}")
        
        return metrics


class VLLMMonitor:
    """Monitor vLLM service metrics"""
    
    def __init__(self, base_url: str = "http://localhost:8080", metrics_port: int = None):
        """
        Initialize vLLM monitor
        
        Args:
            base_url: Base URL for vLLM service
            metrics_port: Port for Prometheus metrics endpoint (if available)
        """
        self.base_url = base_url
        self.metrics_url = f"http://localhost:{metrics_port}/metrics" if metrics_port else None
        self.session: Optional[aiohttp.ClientSession] = None
        self.latency_history = deque(maxlen=1000)  # Store last 1000 latencies
        self.request_count = 0
        self.total_tokens = 0
        self.start_time = time.time()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def collect_metrics(self) -> Optional[VLLMMetrics]:
        """Collect current vLLM metrics"""
        try:
            # Try to get metrics from Prometheus endpoint if available
            if self.metrics_url and self.session:
                try:
                    async with self.session.get(self.metrics_url, timeout=2) as response:
                        if response.status == 200:
                            metrics_text = await response.text()
                            return self._parse_prometheus_metrics(metrics_text)
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass
            
            # Calculate metrics from history
            if self.latency_history:
                latencies = list(self.latency_history)
                elapsed_time = time.time() - self.start_time
                
                return VLLMMetrics(
                    tokens_per_second=self.total_tokens / elapsed_time if elapsed_time > 0 else 0,
                    first_token_latency_ms=latencies[0] if latencies else None,
                    mean_latency_ms=np.mean(latencies),
                    p50_latency_ms=np.percentile(latencies, 50) if len(latencies) > 1 else None,
                    p90_latency_ms=np.percentile(latencies, 90) if len(latencies) > 1 else None,
                    p99_latency_ms=np.percentile(latencies, 99) if len(latencies) > 1 else None,
                    total_requests_processed=self.request_count
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error collecting vLLM metrics: {e}")
            return None
    
    def _parse_prometheus_metrics(self, metrics_text: str) -> Optional[VLLMMetrics]:
        """Parse Prometheus metrics format"""
        metrics = {}
        
        for line in metrics_text.split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            parts = line.split(' ')
            if len(parts) >= 2:
                metric_name = parts[0]
                metric_value = parts[1]
                
                # Extract relevant vLLM metrics
                if 'tokens_per_second' in metric_name:
                    metrics['tokens_per_second'] = float(metric_value)
                elif 'request_latency_seconds' in metric_name:
                    # Convert seconds to milliseconds
                    metrics['latency_ms'] = float(metric_value) * 1000
                elif 'queue_size' in metric_name:
                    metrics['queue_size'] = int(metric_value)
                elif 'batch_size' in metric_name:
                    metrics['batch_size'] = int(metric_value)
        
        if metrics:
            return VLLMMetrics(
                tokens_per_second=metrics.get('tokens_per_second', 0),
                mean_latency_ms=metrics.get('latency_ms', 0),
                request_queue_size=metrics.get('queue_size'),
                active_batch_size=metrics.get('batch_size')
            )
        
        return None
    
    def record_request(self, latency_ms: float, tokens_generated: int):
        """Record a request for metrics calculation"""
        self.latency_history.append(latency_ms)
        self.request_count += 1
        self.total_tokens += tokens_generated


class SystemMonitor:
    """Monitor system-wide metrics"""
    
    def __init__(self):
        """Initialize system monitor"""
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_time = time.time()
    
    async def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # CPU and memory
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Network I/O
        net_io = psutil.net_io_counters()
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_used_gb=memory.used / (1024**3),
            memory_available_gb=memory.available / (1024**3),
            memory_total_gb=memory.total / (1024**3),
            network_bytes_sent=net_io.bytes_sent,
            network_bytes_recv=net_io.bytes_recv,
            disk_read_bytes=disk_io.read_bytes,
            disk_write_bytes=disk_io.write_bytes
        )
        
        # Update last values
        self.last_net_io = net_io
        self.last_disk_io = disk_io
        self.last_time = time.time()
        
        return metrics


class MetricsCollector:
    """Main metrics collection orchestrator"""
    
    def __init__(
        self,
        config_id: str,
        collection_interval: float = 2.0,
        gpu_ids: List[int] = None,
        vllm_base_url: str = "http://localhost:8080",
        vllm_metrics_port: Optional[int] = None,
        output_dir: Path = None
    ):
        """
        Initialize metrics collector
        
        Args:
            config_id: Configuration identifier for this test run
            collection_interval: Seconds between metric collections
            gpu_ids: GPU IDs to monitor (None for all)
            vllm_base_url: Base URL for vLLM service
            vllm_metrics_port: Port for vLLM Prometheus metrics
            output_dir: Directory for output files
        """
        self.config_id = config_id
        self.collection_interval = collection_interval
        self.output_dir = output_dir or Path("./metrics_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize monitors
        self.gpu_monitor = GPUMonitor(gpu_ids)
        self.vllm_monitor = VLLMMonitor(vllm_base_url, vllm_metrics_port)
        self.system_monitor = SystemMonitor()
        
        # Storage
        self.metrics_history: List[MetricsSnapshot] = []
        self.collection_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Real-time display
        self.display_enabled = False
        self.display_task: Optional[asyncio.Task] = None
        
        logger.info(f"MetricsCollector initialized for config: {config_id}")
    
    async def start(self, enable_display: bool = False):
        """Start metrics collection"""
        if self.running:
            logger.warning("Metrics collection already running")
            return
        
        self.running = True
        self.display_enabled = enable_display
        
        # Start collection task
        self.collection_task = asyncio.create_task(self._collection_loop())
        
        # Start display task if enabled
        if enable_display:
            self.display_task = asyncio.create_task(self._display_loop())
        
        logger.info("Metrics collection started")
    
    async def stop(self):
        """Stop metrics collection"""
        self.running = False
        
        # Cancel tasks
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        if self.display_task:
            self.display_task.cancel()
            try:
                await self.display_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Metrics collection stopped. Collected {len(self.metrics_history)} snapshots")
    
    async def _collection_loop(self):
        """Main collection loop"""
        async with self.vllm_monitor:
            while self.running:
                try:
                    # Collect all metrics
                    gpu_metrics = await self.gpu_monitor.collect_metrics()
                    vllm_metrics = await self.vllm_monitor.collect_metrics()
                    system_metrics = await self.system_monitor.collect_metrics()
                    
                    # Create snapshot
                    snapshot = MetricsSnapshot(
                        timestamp=datetime.utcnow().isoformat(),
                        config_id=self.config_id,
                        gpu_metrics=gpu_metrics,
                        vllm_metrics=vllm_metrics,
                        system_metrics=system_metrics
                    )
                    
                    self.metrics_history.append(snapshot)
                    
                    # Sleep until next collection
                    await asyncio.sleep(self.collection_interval)
                    
                except Exception as e:
                    logger.error(f"Error in collection loop: {e}")
                    await asyncio.sleep(self.collection_interval)
    
    async def _display_loop(self):
        """Display real-time metrics"""
        while self.running and self.display_enabled:
            try:
                if self.metrics_history:
                    latest = self.metrics_history[-1]
                    self._display_metrics(latest)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in display loop: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def _display_metrics(self, snapshot: MetricsSnapshot):
        """Display metrics to console"""
        # Clear screen (optional)
        print("\033[2J\033[H")  # ANSI escape codes to clear screen
        
        print(f"=== Metrics Dashboard - Config: {self.config_id} ===")
        print(f"Timestamp: {snapshot.timestamp}")
        print()
        
        # GPU Metrics
        print("GPU Metrics:")
        for gpu_id, metrics in snapshot.gpu_metrics.items():
            print(f"  {gpu_id}:")
            print(f"    Utilization: {metrics.utilization_percent:.1f}%")
            print(f"    Memory: {metrics.memory_used_mb}/{metrics.memory_total_mb} MB")
            if metrics.temperature_c:
                print(f"    Temperature: {metrics.temperature_c:.1f}°C")
            if metrics.power_draw_w:
                print(f"    Power: {metrics.power_draw_w:.1f}W")
        print()
        
        # vLLM Metrics
        if snapshot.vllm_metrics:
            print("vLLM Metrics:")
            print(f"  Throughput: {snapshot.vllm_metrics.tokens_per_second:.1f} tokens/s")
            print(f"  Mean Latency: {snapshot.vllm_metrics.mean_latency_ms:.1f} ms")
            if snapshot.vllm_metrics.p99_latency_ms:
                print(f"  P99 Latency: {snapshot.vllm_metrics.p99_latency_ms:.1f} ms")
            if snapshot.vllm_metrics.request_queue_size is not None:
                print(f"  Queue Size: {snapshot.vllm_metrics.request_queue_size}")
            print()
        
        # System Metrics
        print("System Metrics:")
        print(f"  CPU: {snapshot.system_metrics.cpu_percent:.1f}%")
        print(f"  Memory: {snapshot.system_metrics.memory_used_gb:.1f}/{snapshot.system_metrics.memory_total_gb:.1f} GB")
        print()
    
    def export_json(self, filename: Optional[str] = None) -> Path:
        """Export metrics to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{self.config_id}_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        data = {
            "config_id": self.config_id,
            "collection_interval": self.collection_interval,
            "total_snapshots": len(self.metrics_history),
            "start_time": self.metrics_history[0].timestamp if self.metrics_history else None,
            "end_time": self.metrics_history[-1].timestamp if self.metrics_history else None,
            "metrics": [snapshot.to_dict() for snapshot in self.metrics_history]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported JSON metrics to {filepath}")
        return filepath
    
    def export_csv(self, filename: Optional[str] = None) -> Path:
        """Export metrics to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{self.config_id}_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        # Flatten metrics for CSV
        rows = []
        for snapshot in self.metrics_history:
            row = {
                "timestamp": snapshot.timestamp,
                "config_id": snapshot.config_id,
                "cpu_percent": snapshot.system_metrics.cpu_percent,
                "memory_gb": snapshot.system_metrics.memory_used_gb
            }
            
            # Add GPU metrics
            for gpu_id, gpu_metrics in snapshot.gpu_metrics.items():
                row[f"{gpu_id}_utilization"] = gpu_metrics.utilization_percent
                row[f"{gpu_id}_memory_mb"] = gpu_metrics.memory_used_mb
                row[f"{gpu_id}_temp_c"] = gpu_metrics.temperature_c
            
            # Add vLLM metrics
            if snapshot.vllm_metrics:
                row["tokens_per_second"] = snapshot.vllm_metrics.tokens_per_second
                row["mean_latency_ms"] = snapshot.vllm_metrics.mean_latency_ms
                row["p99_latency_ms"] = snapshot.vllm_metrics.p99_latency_ms
            
            rows.append(row)
        
        if rows:
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Exported CSV metrics to {filepath}")
        
        return filepath
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Calculate summary statistics from collected metrics"""
        if not self.metrics_history:
            return {}
        
        # GPU statistics
        gpu_stats = {}
        for gpu_id in self.metrics_history[0].gpu_metrics.keys():
            utilizations = [s.gpu_metrics[gpu_id].utilization_percent 
                           for s in self.metrics_history 
                           if gpu_id in s.gpu_metrics]
            memories = [s.gpu_metrics[gpu_id].memory_used_mb 
                       for s in self.metrics_history 
                       if gpu_id in s.gpu_metrics]
            
            gpu_stats[gpu_id] = {
                "avg_utilization": np.mean(utilizations),
                "max_utilization": np.max(utilizations),
                "avg_memory_mb": np.mean(memories),
                "max_memory_mb": np.max(memories)
            }
        
        # vLLM statistics
        vllm_stats = {}
        vllm_metrics = [s.vllm_metrics for s in self.metrics_history if s.vllm_metrics]
        if vllm_metrics:
            throughputs = [m.tokens_per_second for m in vllm_metrics]
            latencies = [m.mean_latency_ms for m in vllm_metrics]
            
            vllm_stats = {
                "avg_throughput": np.mean(throughputs),
                "max_throughput": np.max(throughputs),
                "avg_latency_ms": np.mean(latencies),
                "min_latency_ms": np.min(latencies),
                "max_latency_ms": np.max(latencies)
            }
        
        # System statistics
        cpu_usages = [s.system_metrics.cpu_percent for s in self.metrics_history]
        memory_usages = [s.system_metrics.memory_used_gb for s in self.metrics_history]
        
        system_stats = {
            "avg_cpu_percent": np.mean(cpu_usages),
            "max_cpu_percent": np.max(cpu_usages),
            "avg_memory_gb": np.mean(memory_usages),
            "max_memory_gb": np.max(memory_usages)
        }
        
        return {
            "config_id": self.config_id,
            "total_snapshots": len(self.metrics_history),
            "collection_duration_seconds": len(self.metrics_history) * self.collection_interval,
            "gpu_statistics": gpu_stats,
            "vllm_statistics": vllm_stats,
            "system_statistics": system_stats
        }


async def test_metrics_collector():
    """Test the metrics collector with a sample configuration"""
    
    # Create collector
    collector = MetricsCollector(
        config_id="test_config_001",
        collection_interval=2.0,
        gpu_ids=[0, 1],  # Monitor both GPUs
        vllm_base_url="http://localhost:8080",
        output_dir=Path("/srv/luris/be/entity-extraction-service/tests/metrics_output")
    )
    
    try:
        # Start collection with display
        await collector.start(enable_display=True)
        
        # Simulate some vLLM requests
        for i in range(10):
            # Record fake request metrics
            latency = np.random.uniform(50, 150)  # Random latency 50-150ms
            tokens = np.random.randint(100, 500)  # Random tokens
            collector.vllm_monitor.record_request(latency, tokens)
            await asyncio.sleep(1)
        
        # Run for 30 seconds
        await asyncio.sleep(30)
        
    finally:
        # Stop collection
        await collector.stop()
        
        # Export results
        json_path = collector.export_json()
        csv_path = collector.export_csv()
        
        # Print summary
        summary = collector.get_summary_statistics()
        print("\n=== Collection Summary ===")
        print(json.dumps(summary, indent=2))
        
        print(f"\nExported metrics to:")
        print(f"  JSON: {json_path}")
        print(f"  CSV: {csv_path}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal, stopping metrics collection...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run test
    asyncio.run(test_metrics_collector())