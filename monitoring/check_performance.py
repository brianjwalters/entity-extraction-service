#!/usr/bin/env python3
"""
Performance Check Script

Quick performance check for vLLM and Entity Extraction services.
Provides instant metrics and recommendations.
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_colored(text: str, color: str = Colors.ENDC):
    """Print colored text."""
    print(f"{color}{text}{Colors.ENDC}")


def print_header(text: str):
    """Print section header."""
    print()
    print_colored("=" * 80, Colors.HEADER)
    print_colored(f"  {text}", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 80, Colors.HEADER)


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration to human readable string."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


class PerformanceChecker:
    """Check and report on system performance."""

    def __init__(self):
        self.vllm_url = "http://localhost:8080"
        self.entity_extraction_url = "http://localhost:8007"
        self.document_upload_url = "http://localhost:8008"
        self.results = {}

    async def check_gpu_status(self) -> Dict[str, Any]:
        """Check GPU status and utilization."""
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return {"error": "Failed to query GPU"}

            gpus = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split(', ')
                if len(parts) >= 6:
                    gpu_id = int(parts[0])
                    memory_used = int(float(parts[2]))
                    memory_total = int(float(parts[3]))
                    memory_percent = (memory_used / memory_total) * 100

                    gpus.append({
                        "id": gpu_id,
                        "name": parts[1],
                        "memory_used_mb": memory_used,
                        "memory_total_mb": memory_total,
                        "memory_percent": memory_percent,
                        "utilization": int(parts[4]) if parts[4] != '[N/A]' else 0,
                        "temperature": int(parts[5]) if parts[5] != '[N/A]' else 0
                    })

            return {"gpus": gpus}

        except Exception as e:
            return {"error": str(e)}

    async def check_service_health(self, service_name: str, url: str) -> Dict[str, Any]:
        """Check service health and response time."""
        try:
            start_time = time.time()

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/health")
                response_time = time.time() - start_time

                if response.status_code == 200:
                    health_data = response.json()
                    return {
                        "status": "healthy",
                        "response_time_ms": response_time * 1000,
                        "details": health_data
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "response_time_ms": response_time * 1000,
                        "status_code": response.status_code
                    }

        except httpx.TimeoutException:
            return {"status": "timeout", "error": "Health check timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def check_vllm_models(self) -> Dict[str, Any]:
        """Check vLLM model status."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.vllm_url}/v1/models")

                if response.status_code == 200:
                    models_data = response.json()
                    return {
                        "status": "available",
                        "models": models_data.get("data", [])
                    }
                else:
                    return {"status": "error", "status_code": response.status_code}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def test_inference_speed(self) -> Dict[str, Any]:
        """Test inference speed with a simple prompt."""
        try:
            test_prompt = "Extract the case name from: Smith v. Jones, 123 F.3d 456 (2024)"

            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()

                response = await client.post(
                    f"{self.vllm_url}/v1/completions",
                    json={
                        "model": "ibm-granite/granite-3.3-2b-instruct",
                        "prompt": test_prompt,
                        "max_tokens": 50,
                        "temperature": 0.1
                    }
                )

                response_time = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    tokens = len(result.get("choices", [{}])[0].get("text", "").split())

                    return {
                        "status": "success",
                        "response_time_ms": response_time * 1000,
                        "tokens_generated": tokens,
                        "tokens_per_second": tokens / response_time if response_time > 0 else 0
                    }
                else:
                    return {
                        "status": "error",
                        "response_time_ms": response_time * 1000,
                        "status_code": response.status_code
                    }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)

            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent": disk.percent
                }
            }

        except Exception as e:
            return {"error": str(e)}

    async def run_all_checks(self):
        """Run all performance checks."""
        print_header("vLLM Performance Check")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # GPU Status
        print_header("GPU Status")
        gpu_status = await self.check_gpu_status()

        if "error" in gpu_status:
            print_colored(f"  ❌ Error: {gpu_status['error']}", Colors.FAIL)
        else:
            for gpu in gpu_status["gpus"]:
                status_color = Colors.OKGREEN if gpu["memory_percent"] < 85 else Colors.WARNING
                if gpu["memory_percent"] > 95:
                    status_color = Colors.FAIL

                print(f"\n  GPU {gpu['id']}: {gpu['name']}")
                print_colored(
                    f"    Memory: {gpu['memory_used_mb']}MB / {gpu['memory_total_mb']}MB ({gpu['memory_percent']:.1f}%)",
                    status_color
                )
                print(f"    Utilization: {gpu['utilization']}%")
                print(f"    Temperature: {gpu['temperature']}°C")

                # Recommendations
                if gpu["memory_percent"] > 95:
                    print_colored("    ⚠️  Critical memory usage - may cause OOM errors", Colors.FAIL)
                elif gpu["memory_percent"] > 85:
                    print_colored("    ⚠️  High memory usage - monitor closely", Colors.WARNING)

                if gpu["utilization"] < 20 and gpu["memory_percent"] > 50:
                    print_colored("    💡 GPU underutilized - consider batch size optimization", Colors.OKCYAN)

        # Service Health
        print_header("Service Health")

        services = [
            ("vLLM Service", self.vllm_url),
            ("Entity Extraction", self.entity_extraction_url),
            ("Document Upload", self.document_upload_url)
        ]

        for service_name, url in services:
            health = await self.check_service_health(service_name, url)

            if health["status"] == "healthy":
                print_colored(
                    f"  ✅ {service_name}: Healthy ({health['response_time_ms']:.0f}ms)",
                    Colors.OKGREEN
                )
            elif health["status"] == "timeout":
                print_colored(f"  ⏱️  {service_name}: Timeout", Colors.WARNING)
            else:
                print_colored(f"  ❌ {service_name}: {health.get('error', 'Unhealthy')}", Colors.FAIL)

        # vLLM Models
        print_header("vLLM Models")
        models = await self.check_vllm_models()

        if models["status"] == "available":
            for model in models["models"]:
                print(f"  ✅ {model['id']}")
        else:
            print_colored(f"  ❌ Error checking models: {models.get('error', 'Unknown')}", Colors.FAIL)

        # Inference Speed Test
        print_header("Inference Speed Test")
        inference_test = await self.test_inference_speed()

        if inference_test["status"] == "success":
            response_time = inference_test["response_time_ms"]
            tps = inference_test["tokens_per_second"]

            if response_time < 1000:
                color = Colors.OKGREEN
                status = "Excellent"
            elif response_time < 3000:
                color = Colors.WARNING
                status = "Good"
            else:
                color = Colors.FAIL
                status = "Slow"

            print_colored(
                f"  Response Time: {response_time:.0f}ms ({status})",
                color
            )
            print(f"  Tokens/Second: {tps:.1f}")

            # Recommendations
            if response_time > 3000:
                print_colored("  💡 Consider optimizing model configuration for speed", Colors.OKCYAN)
        else:
            print_colored(f"  ❌ Test failed: {inference_test.get('error', 'Unknown')}", Colors.FAIL)

        # System Resources
        print_header("System Resources")
        resources = await self.check_system_resources()

        if "error" not in resources:
            cpu_color = Colors.OKGREEN if resources["cpu_percent"] < 70 else Colors.WARNING
            if resources["cpu_percent"] > 90:
                cpu_color = Colors.FAIL

            mem_color = Colors.OKGREEN if resources["memory"]["percent"] < 80 else Colors.WARNING
            if resources["memory"]["percent"] > 90:
                mem_color = Colors.FAIL

            print_colored(f"  CPU Usage: {resources['cpu_percent']:.1f}%", cpu_color)
            print_colored(
                f"  Memory: {resources['memory']['percent']:.1f}% "
                f"({resources['memory']['available_gb']:.1f}GB available)",
                mem_color
            )
            print(f"  Disk: {resources['disk']['percent']:.1f}% ({resources['disk']['free_gb']:.1f}GB free)")

        # Overall Recommendations
        print_header("Performance Recommendations")

        recommendations = []

        # Check for issues and generate recommendations
        if gpu_status.get("gpus"):
            for gpu in gpu_status["gpus"]:
                if gpu["memory_percent"] > 85:
                    recommendations.append("Consider reducing batch sizes or context length to free GPU memory")
                if gpu["temperature"] > 80:
                    recommendations.append("GPU running hot - ensure proper cooling")

        if inference_test.get("status") == "success":
            if inference_test["response_time_ms"] > 3000:
                recommendations.append("Inference is slow - review vLLM configuration settings")
            if inference_test["tokens_per_second"] < 10:
                recommendations.append("Low token throughput - consider enabling GPU optimization")

        if resources and "error" not in resources:
            if resources["cpu_percent"] > 80:
                recommendations.append("High CPU usage - may impact performance")
            if resources["memory"]["percent"] > 85:
                recommendations.append("High memory usage - monitor for potential issues")

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print_colored(f"  {i}. {rec}", Colors.OKCYAN)
        else:
            print_colored("  ✅ System performing optimally", Colors.OKGREEN)

        print()
        print_colored("=" * 80, Colors.HEADER)


async def main():
    """Main entry point."""
    checker = PerformanceChecker()
    await checker.run_all_checks()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nCheck interrupted by user")
        sys.exit(0)