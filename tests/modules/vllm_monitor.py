"""
vLLM Health Monitor Module

This module monitors vLLM service health and detects failures indicated by
'regex_only' extraction mode. It provides automated troubleshooting and
recovery mechanisms to ensure AI enhancement remains operational.
"""

import asyncio
import logging
import subprocess
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import httpx
import psutil


class ServiceStatus(Enum):
    """vLLM service status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    RECOVERING = "recovering"


class FailureType(Enum):
    """Types of vLLM failures."""
    SERVICE_DOWN = "service_down"
    GPU_OOM = "gpu_out_of_memory"
    CPU_DEADLOCK = "cpu_deadlock"
    CONTEXT_OVERFLOW = "context_overflow"
    REGEX_ONLY_FALLBACK = "regex_only_fallback"
    SLOW_RESPONSE = "slow_response"
    CONNECTION_ERROR = "connection_error"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    status: ServiceStatus
    response_time_ms: Optional[float]
    model_loaded: bool
    gpu_memory_used: Optional[float]
    gpu_memory_total: Optional[float]
    cpu_usage: Optional[float]
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def gpu_utilization(self) -> Optional[float]:
        """Calculate GPU memory utilization percentage."""
        if self.gpu_memory_used and self.gpu_memory_total:
            return (self.gpu_memory_used / self.gpu_memory_total) * 100
        return None


@dataclass
class TroubleshootingResult:
    """Result of troubleshooting attempts."""
    problem_detected: FailureType
    resolution_attempted: bool
    resolution_successful: bool
    steps_taken: List[str]
    recommendations: List[str]
    service_restarted: bool
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class VLLMMonitor:
    """
    Monitor vLLM service health and detect failures.
    
    This monitor performs:
    - Health endpoint checks
    - GPU memory monitoring
    - CPU usage tracking
    - Extraction mode validation
    - Automated troubleshooting
    - Service recovery attempts
    """
    
    # Service endpoints
    VLLM_BASE_URL = "http://localhost:8080"
    VLLM_HEALTH_ENDPOINT = f"{VLLM_BASE_URL}/health"
    VLLM_MODELS_ENDPOINT = f"{VLLM_BASE_URL}/v1/models"
    
    # Entity extraction service endpoint
    EXTRACTION_BASE_URL = "http://localhost:8007"
    EXTRACTION_HEALTH_ENDPOINT = f"{EXTRACTION_BASE_URL}/api/v1/health"
    
    # Monitoring thresholds
    MAX_RESPONSE_TIME_MS = 5000      # 5 seconds
    MAX_GPU_UTILIZATION = 95.0       # 95% GPU memory
    MAX_CPU_USAGE = 90.0              # 90% CPU usage
    HEALTH_CHECK_TIMEOUT = 10         # 10 seconds timeout
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the vLLM monitor."""
        self.logger = logger or logging.getLogger(__name__)
        self.last_health_check: Optional[HealthCheckResult] = None
        self.failure_history: List[Tuple[FailureType, datetime]] = []
        self.client = httpx.AsyncClient(timeout=self.HEALTH_CHECK_TIMEOUT)
    
    async def check_health(self) -> HealthCheckResult:
        """
        Perform comprehensive health check of vLLM service.
        
        Returns:
            HealthCheckResult with current service status
        """
        start_time = time.time()
        
        try:
            # Check vLLM health endpoint
            response = await self.client.get(self.VLLM_HEALTH_ENDPOINT)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return HealthCheckResult(
                    status=ServiceStatus.FAILED,
                    response_time_ms=response_time,
                    model_loaded=False,
                    gpu_memory_used=None,
                    gpu_memory_total=None,
                    cpu_usage=None,
                    error_message=f"Health check failed with status {response.status_code}"
                )
            
            # Check if model is loaded
            models_response = await self.client.get(self.VLLM_MODELS_ENDPOINT)
            model_loaded = False
            
            if models_response.status_code == 200:
                models_data = models_response.json()
                model_loaded = len(models_data.get("data", [])) > 0
            
            # Get GPU memory stats
            gpu_memory_used, gpu_memory_total = self._get_gpu_memory_stats()
            
            # Get CPU usage
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # Determine overall status
            status = ServiceStatus.HEALTHY
            
            if response_time > self.MAX_RESPONSE_TIME_MS:
                status = ServiceStatus.DEGRADED
            
            if not model_loaded:
                status = ServiceStatus.FAILED
            
            if gpu_memory_used and gpu_memory_total:
                gpu_util = (gpu_memory_used / gpu_memory_total) * 100
                if gpu_util > self.MAX_GPU_UTILIZATION:
                    status = ServiceStatus.DEGRADED
            
            if cpu_usage > self.MAX_CPU_USAGE:
                status = ServiceStatus.DEGRADED
            
            result = HealthCheckResult(
                status=status,
                response_time_ms=response_time,
                model_loaded=model_loaded,
                gpu_memory_used=gpu_memory_used,
                gpu_memory_total=gpu_memory_total,
                cpu_usage=cpu_usage
            )
            
            self.last_health_check = result
            return result
            
        except httpx.RequestError as e:
            self.logger.error(f"vLLM health check failed: {e}")
            
            result = HealthCheckResult(
                status=ServiceStatus.FAILED,
                response_time_ms=None,
                model_loaded=False,
                gpu_memory_used=None,
                gpu_memory_total=None,
                cpu_usage=None,
                error_message=str(e)
            )
            
            self.last_health_check = result
            return result
    
    def _get_gpu_memory_stats(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get GPU memory statistics using nvidia-smi.
        
        Returns:
            Tuple of (used_memory_mb, total_memory_mb)
        """
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    # Parse first GPU (GPU 0 for vLLM)
                    lines = output.split('\n')
                    if lines:
                        used, total = lines[0].split(',')
                        return float(used.strip()), float(total.strip())
        except Exception as e:
            self.logger.warning(f"Failed to get GPU memory stats: {e}")
        
        return None, None
    
    def validate_extraction_mode(self, extraction_result: Dict[str, Any]) -> bool:
        """
        Validate that extraction is not in regex_only mode.
        
        Args:
            extraction_result: Result from entity extraction service
            
        Returns:
            True if AI enhancement is active, False if regex_only detected
        """
        # Check extraction mode
        extraction_mode = extraction_result.get("extraction_mode", "").lower()
        
        if extraction_mode == "regex_only":
            self.logger.error(
                "🚨 CRITICAL: regex_only mode detected! vLLM service has failed!"
            )
            self.failure_history.append((FailureType.REGEX_ONLY_FALLBACK, datetime.now()))
            return False
        
        # Check AI enhancement status
        ai_status = extraction_result.get("ai_enhancement_status", {})
        if ai_status.get("ai_used") is False:
            self.logger.warning(
                f"AI enhancement not used: {ai_status.get('reason', 'Unknown reason')}"
            )
            return False
        
        return True
    
    async def troubleshoot_failure(
        self,
        failure_type: Optional[FailureType] = None
    ) -> TroubleshootingResult:
        """
        Attempt to troubleshoot and resolve vLLM failures.
        
        Args:
            failure_type: Specific failure type to troubleshoot
            
        Returns:
            TroubleshootingResult with steps taken and recommendations
        """
        steps_taken = []
        recommendations = []
        resolution_successful = False
        service_restarted = False
        
        # Determine failure type if not provided
        if failure_type is None:
            health = await self.check_health()
            
            if health.status == ServiceStatus.FAILED:
                if not health.model_loaded:
                    failure_type = FailureType.SERVICE_DOWN
                elif health.error_message and "connection" in health.error_message.lower():
                    failure_type = FailureType.CONNECTION_ERROR
            elif health.gpu_utilization and health.gpu_utilization > 95:
                failure_type = FailureType.GPU_OOM
            elif health.cpu_usage and health.cpu_usage > 90:
                failure_type = FailureType.CPU_DEADLOCK
            else:
                failure_type = FailureType.REGEX_ONLY_FALLBACK
        
        self.logger.info(f"Troubleshooting {failure_type.value}...")
        
        # Troubleshooting based on failure type
        if failure_type == FailureType.SERVICE_DOWN:
            steps_taken.append("Checking if vLLM service is running")
            
            # Check service status
            status_result = subprocess.run(
                ["sudo", "systemctl", "status", "luris-vllm"],
                capture_output=True,
                text=True
            )
            
            if "inactive" in status_result.stdout or "failed" in status_result.stdout:
                steps_taken.append("Service is down, attempting restart")
                
                # Restart service
                restart_result = subprocess.run(
                    ["sudo", "systemctl", "restart", "luris-vllm"],
                    capture_output=True,
                    text=True
                )
                
                if restart_result.returncode == 0:
                    steps_taken.append("Service restarted successfully")
                    service_restarted = True
                    
                    # Wait for service to initialize
                    await asyncio.sleep(30)
                    
                    # Verify service is healthy
                    health = await self.check_health()
                    if health.status == ServiceStatus.HEALTHY:
                        resolution_successful = True
                else:
                    steps_taken.append("Service restart failed")
                    recommendations.append("Manual intervention required: Check service logs with 'sudo journalctl -u luris-vllm -n 100'")
        
        elif failure_type == FailureType.GPU_OOM:
            steps_taken.append("GPU memory exhausted, checking for hung processes")
            
            # Kill any zombie vLLM processes
            kill_result = subprocess.run(
                ["pkill", "-f", "vllm.entrypoints.openai.api_server"],
                capture_output=True,
                text=True
            )
            
            steps_taken.append("Killed zombie processes")
            
            # Restart service
            steps_taken.append("Restarting vLLM service to clear GPU memory")
            restart_result = subprocess.run(
                ["sudo", "systemctl", "restart", "luris-vllm"],
                capture_output=True,
                text=True
            )
            
            if restart_result.returncode == 0:
                service_restarted = True
                await asyncio.sleep(30)
                
                health = await self.check_health()
                if health.gpu_utilization and health.gpu_utilization < 90:
                    resolution_successful = True
            
            recommendations.append("Consider reducing batch size or max sequences in vLLM configuration")
            recommendations.append("Monitor GPU memory with 'nvidia-smi -l 1'")
        
        elif failure_type == FailureType.CPU_DEADLOCK:
            steps_taken.append("CPU deadlock detected, likely tensor parallelism issue")
            
            # Check for spinning processes
            cpu_check = subprocess.run(
                ["top", "-b", "-n", "1"],
                capture_output=True,
                text=True
            )
            
            if "vllm" in cpu_check.stdout:
                steps_taken.append("vLLM processes consuming high CPU")
                
                # Force kill and restart
                subprocess.run(["pkill", "-9", "-f", "vllm"], capture_output=True)
                steps_taken.append("Force killed vLLM processes")
                
                await asyncio.sleep(5)
                
                restart_result = subprocess.run(
                    ["sudo", "systemctl", "restart", "luris-vllm"],
                    capture_output=True,
                    text=True
                )
                
                if restart_result.returncode == 0:
                    service_restarted = True
                    await asyncio.sleep(30)
                    resolution_successful = True
            
            recommendations.append("Verify vLLM is configured for single GPU (tensor-parallel-size=1)")
            recommendations.append("Check for tensor parallelism issues in service configuration")
        
        elif failure_type == FailureType.CONTEXT_OVERFLOW:
            steps_taken.append("Context overflow detected")
            recommendations.append("Reduce chunk size in document processing")
            recommendations.append("Implement more aggressive document chunking")
            recommendations.append("Consider using summarization for very large documents")
        
        elif failure_type == FailureType.REGEX_ONLY_FALLBACK:
            steps_taken.append("regex_only fallback detected, checking vLLM availability")
            
            # Full health check
            health = await self.check_health()
            
            if health.status != ServiceStatus.HEALTHY:
                # Recursive troubleshooting based on health status
                return await self.troubleshoot_failure()
            else:
                steps_taken.append("vLLM appears healthy but not being used")
                recommendations.append("Check entity extraction service configuration")
                recommendations.append("Verify vLLM client initialization in extraction service")
                recommendations.append("Review extraction service logs: 'sudo journalctl -u luris-entity-extraction -n 100'")
        
        return TroubleshootingResult(
            problem_detected=failure_type,
            resolution_attempted=True,
            resolution_successful=resolution_successful,
            steps_taken=steps_taken,
            recommendations=recommendations,
            service_restarted=service_restarted
        )
    
    def format_health_report(self, health: HealthCheckResult) -> str:
        """
        Format a human-readable health report.
        
        Args:
            health: Health check result
            
        Returns:
            Formatted health report string
        """
        report = []
        report.append("=" * 60)
        report.append("vLLM SERVICE HEALTH REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {health.timestamp.isoformat()}")
        report.append(f"Status: {health.status.value.upper()}")
        
        if health.status == ServiceStatus.HEALTHY:
            report.append("✅ Service is healthy and operational")
        elif health.status == ServiceStatus.DEGRADED:
            report.append("⚠️  Service is degraded but functional")
        else:
            report.append("🚨 Service has FAILED - immediate action required!")
        
        report.append("")
        report.append("METRICS:")
        
        if health.response_time_ms:
            report.append(f"  Response Time: {health.response_time_ms:.1f}ms")
            if health.response_time_ms > self.MAX_RESPONSE_TIME_MS:
                report.append(f"    ⚠️  Exceeds threshold of {self.MAX_RESPONSE_TIME_MS}ms")
        
        report.append(f"  Model Loaded: {'✅ Yes' if health.model_loaded else '❌ No'}")
        
        if health.gpu_memory_used and health.gpu_memory_total:
            gpu_util = health.gpu_utilization
            report.append(f"  GPU Memory: {health.gpu_memory_used:.0f}MB / {health.gpu_memory_total:.0f}MB ({gpu_util:.1f}%)")
            if gpu_util > self.MAX_GPU_UTILIZATION:
                report.append(f"    ⚠️  Exceeds threshold of {self.MAX_GPU_UTILIZATION}%")
        
        if health.cpu_usage:
            report.append(f"  CPU Usage: {health.cpu_usage:.1f}%")
            if health.cpu_usage > self.MAX_CPU_USAGE:
                report.append(f"    ⚠️  Exceeds threshold of {self.MAX_CPU_USAGE}%")
        
        if health.error_message:
            report.append("")
            report.append(f"ERROR: {health.error_message}")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    async def monitor_extraction(
        self,
        extraction_func,
        *args,
        **kwargs
    ) -> Tuple[Any, bool]:
        """
        Monitor an extraction operation for regex_only fallback.
        
        Args:
            extraction_func: Async function to call for extraction
            *args, **kwargs: Arguments for extraction function
            
        Returns:
            Tuple of (extraction_result, is_healthy)
        """
        # Pre-flight health check
        health = await self.check_health()
        
        if health.status == ServiceStatus.FAILED:
            self.logger.error("vLLM service is not healthy, attempting troubleshooting...")
            troubleshoot_result = await self.troubleshoot_failure()
            
            if not troubleshoot_result.resolution_successful:
                raise RuntimeError(
                    f"vLLM service failure could not be resolved: {troubleshoot_result.recommendations}"
                )
        
        # Run extraction
        result = await extraction_func(*args, **kwargs)
        
        # Validate extraction mode
        is_healthy = self.validate_extraction_mode(result)
        
        if not is_healthy:
            self.logger.error("Extraction fell back to regex_only mode!")
            
            # Attempt troubleshooting
            troubleshoot_result = await self.troubleshoot_failure(
                FailureType.REGEX_ONLY_FALLBACK
            )
            
            if troubleshoot_result.resolution_successful:
                # Retry extraction
                self.logger.info("Retrying extraction after troubleshooting...")
                result = await extraction_func(*args, **kwargs)
                is_healthy = self.validate_extraction_mode(result)
        
        return result, is_healthy
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.check_health()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


if __name__ == "__main__":
    # Test the monitor
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_monitor():
        monitor = VLLMMonitor()
        
        # Check health
        print("Checking vLLM health...")
        health = await monitor.check_health()
        print(monitor.format_health_report(health))
        
        # Test extraction validation
        test_result_healthy = {
            "extraction_mode": "ai_enhanced",
            "ai_enhancement_status": {
                "ai_used": True,
                "chunks_processed": 3
            }
        }
        
        test_result_failed = {
            "extraction_mode": "regex_only",
            "ai_enhancement_status": {
                "ai_used": False,
                "reason": "vLLM service unavailable"
            }
        }
        
        print("\nValidating healthy extraction result:")
        is_healthy = monitor.validate_extraction_mode(test_result_healthy)
        print(f"  Result: {'✅ Healthy' if is_healthy else '❌ Failed'}")
        
        print("\nValidating failed extraction result:")
        is_healthy = monitor.validate_extraction_mode(test_result_failed)
        print(f"  Result: {'✅ Healthy' if is_healthy else '❌ Failed'}")
        
        if not is_healthy:
            print("\n🔧 Attempting troubleshooting...")
            troubleshoot = await monitor.troubleshoot_failure()
            print(f"  Resolution successful: {troubleshoot.resolution_successful}")
            print(f"  Steps taken: {troubleshoot.steps_taken}")
            print(f"  Recommendations: {troubleshoot.recommendations}")
        
        await monitor.client.aclose()
    
    asyncio.run(test_monitor())