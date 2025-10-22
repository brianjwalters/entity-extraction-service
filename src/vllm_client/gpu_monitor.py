"""
GPU memory monitoring utilities for vLLM.

Monitors GPU utilization and alerts on memory pressure.
Uses nvidia-smi for GPU statistics.

All default values now loaded from centralized config.py.
"""

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, List
from .exceptions import GPUMemoryError

logger = logging.getLogger(__name__)


@dataclass
class GPUStats:
    """GPU statistics."""

    gpu_id: int
    memory_used_mb: float
    memory_total_mb: float
    memory_free_mb: float
    utilization_percent: float
    temperature_c: Optional[float] = None
    power_draw_w: Optional[float] = None

    @property
    def memory_used_gb(self) -> float:
        return self.memory_used_mb / 1024.0

    @property
    def memory_total_gb(self) -> float:
        return self.memory_total_mb / 1024.0

    @property
    def memory_free_gb(self) -> float:
        return self.memory_free_mb / 1024.0

    @property
    def memory_utilization_percent(self) -> float:
        if self.memory_total_mb == 0:
            return 0.0
        return (self.memory_used_mb / self.memory_total_mb) * 100.0

    def to_dict(self) -> dict:
        return {
            "gpu_id": self.gpu_id,
            "memory": {
                "used_mb": self.memory_used_mb,
                "used_gb": self.memory_used_gb,
                "total_mb": self.memory_total_mb,
                "total_gb": self.memory_total_gb,
                "free_mb": self.memory_free_mb,
                "free_gb": self.memory_free_gb,
                "utilization_percent": self.memory_utilization_percent
            },
            "gpu_utilization_percent": self.utilization_percent,
            "temperature_c": self.temperature_c,
            "power_draw_w": self.power_draw_w
        }


class GPUMonitor:
    """
    GPU memory and utilization monitor.

    Uses nvidia-smi to query GPU statistics.
    """

    def __init__(self, gpu_id: int = 0, memory_threshold: float = 0.90):
        """
        Initialize GPU monitor.

        Args:
            gpu_id: GPU device ID to monitor
            memory_threshold: Alert threshold (0.0-1.0)
        """
        self.gpu_id = gpu_id
        self.memory_threshold = memory_threshold
        self.alert_count = 0
        self.last_alert_time = 0.0

    def get_stats(self) -> Optional[GPUStats]:
        """
        Get current GPU statistics.

        Returns:
            GPUStats or None if nvidia-smi unavailable
        """
        try:
            # Query nvidia-smi for GPU stats
            cmd = [
                "nvidia-smi",
                f"--id={self.gpu_id}",
                "--query-gpu=memory.used,memory.total,memory.free,utilization.gpu,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.warning(f"nvidia-smi returned error: {result.stderr}")
                return None

            # Parse output
            values = result.stdout.strip().split(", ")
            if len(values) < 4:
                logger.warning(f"Unexpected nvidia-smi output: {result.stdout}")
                return None

            memory_used = float(values[0])
            memory_total = float(values[1])
            memory_free = float(values[2])
            utilization = float(values[3])

            # Optional values
            temperature = float(values[4]) if len(values) > 4 and values[4] else None
            power_draw = float(values[5]) if len(values) > 5 and values[5] else None

            stats = GPUStats(
                gpu_id=self.gpu_id,
                memory_used_mb=memory_used,
                memory_total_mb=memory_total,
                memory_free_mb=memory_free,
                utilization_percent=utilization,
                temperature_c=temperature,
                power_draw_w=power_draw
            )

            # Check memory threshold
            if stats.memory_utilization_percent / 100.0 > self.memory_threshold:
                self._alert_high_memory(stats)

            return stats

        except FileNotFoundError:
            logger.warning("nvidia-smi not found - GPU monitoring disabled")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi timeout")
            return None
        except Exception as e:
            logger.warning(f"Failed to get GPU stats: {e}")
            return None

    def _alert_high_memory(self, stats: GPUStats):
        """Alert on high memory usage."""
        current_time = time.time()

        # Rate limit alerts (max 1 per minute)
        if current_time - self.last_alert_time < 60:
            return

        self.alert_count += 1
        self.last_alert_time = current_time

        logger.warning(
            f"GPU {stats.gpu_id} memory HIGH: "
            f"{stats.memory_utilization_percent:.1f}% "
            f"({stats.memory_used_gb:.1f}GB / {stats.memory_total_gb:.1f}GB) "
            f"- Alert #{self.alert_count}"
        )

    def check_memory_available(self, required_gb: float) -> bool:
        """
        Check if sufficient GPU memory is available.

        Args:
            required_gb: Required memory in GB

        Returns:
            True if sufficient memory available
        """
        stats = self.get_stats()
        if not stats:
            # Can't check, assume available
            logger.warning("GPU stats unavailable, assuming memory is available")
            return True

        available_gb = stats.memory_free_gb

        if available_gb < required_gb:
            logger.warning(
                f"Insufficient GPU memory: {available_gb:.1f}GB available, "
                f"{required_gb:.1f}GB required"
            )
            return False

        return True

    def wait_for_memory(
        self,
        required_gb: float,
        timeout_seconds: float = 300,
        check_interval: float = 5
    ) -> bool:
        """
        Wait for sufficient GPU memory to become available.

        Args:
            required_gb: Required memory in GB
            timeout_seconds: Maximum wait time
            check_interval: Check interval in seconds

        Returns:
            True if memory became available, False if timeout
        """
        start_time = time.time()
        attempts = 0

        while time.time() - start_time < timeout_seconds:
            if self.check_memory_available(required_gb):
                if attempts > 0:
                    logger.info(
                        f"GPU memory available after {attempts} checks "
                        f"({time.time() - start_time:.1f}s)"
                    )
                return True

            attempts += 1
            if attempts == 1:
                logger.info(
                    f"Waiting for {required_gb:.1f}GB GPU memory "
                    f"(timeout: {timeout_seconds}s)..."
                )

            time.sleep(check_interval)

        logger.error(
            f"Timeout waiting for GPU memory after {timeout_seconds}s "
            f"({attempts} checks)"
        )
        return False

    def validate_or_raise(self, required_gb: float):
        """
        Validate GPU memory or raise GPUMemoryError.

        Args:
            required_gb: Required memory in GB

        Raises:
            GPUMemoryError: If insufficient memory
        """
        stats = self.get_stats()
        if not stats:
            # Can't validate, allow to proceed
            return

        if stats.memory_free_gb < required_gb:
            raise GPUMemoryError(
                f"Insufficient GPU memory: {stats.memory_free_gb:.1f}GB available, "
                f"{required_gb:.1f}GB required",
                used_memory_gb=stats.memory_used_gb,
                total_memory_gb=stats.memory_total_gb,
                utilization_percent=stats.memory_utilization_percent
            )

    def get_stats_summary(self) -> str:
        """Get human-readable stats summary."""
        stats = self.get_stats()
        if not stats:
            return "GPU stats unavailable"

        summary = (
            f"GPU {stats.gpu_id}: "
            f"{stats.memory_utilization_percent:.1f}% memory "
            f"({stats.memory_used_gb:.1f}GB / {stats.memory_total_gb:.1f}GB), "
            f"{stats.utilization_percent:.0f}% utilization"
        )

        if stats.temperature_c:
            summary += f", {stats.temperature_c:.0f}°C"

        return summary


def get_all_gpu_stats() -> List[GPUStats]:
    """
    Get statistics for all available GPUs.

    Returns:
        List of GPUStats for each GPU
    """
    stats_list = []

    try:
        # Query all GPUs
        cmd = [
            "nvidia-smi",
            "--query-gpu=index,memory.used,memory.total,memory.free,utilization.gpu,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.warning(f"nvidia-smi returned error: {result.stderr}")
            return []

        # Parse each line
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            values = line.split(", ")
            if len(values) < 5:
                continue

            gpu_id = int(values[0])
            memory_used = float(values[1])
            memory_total = float(values[2])
            memory_free = float(values[3])
            utilization = float(values[4])
            temperature = float(values[5]) if len(values) > 5 and values[5] else None
            power_draw = float(values[6]) if len(values) > 6 and values[6] else None

            stats = GPUStats(
                gpu_id=gpu_id,
                memory_used_mb=memory_used,
                memory_total_mb=memory_total,
                memory_free_mb=memory_free,
                utilization_percent=utilization,
                temperature_c=temperature,
                power_draw_w=power_draw
            )

            stats_list.append(stats)

    except Exception as e:
        logger.warning(f"Failed to get all GPU stats: {e}")

    return stats_list
