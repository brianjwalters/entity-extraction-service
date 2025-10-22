"""
Service Health Check Module for Entity Extraction Service Testing Framework

This module provides comprehensive health checking for the Entity Extraction Service
running on port 8007. It verifies service availability, endpoint accessibility, and
basic functionality before running extraction tests.

Features:
- Port availability checking (8007)
- Health endpoint verification
- Extraction endpoint validation with minimal payload
- Response time measurement
- Comprehensive error reporting
"""

import socket
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Results from service health check."""
    service_up: bool
    port_listening: bool
    health_endpoint_ok: bool
    extract_endpoint_ok: bool
    response_time_ms: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ServiceHealthChecker:
    """
    Health checker for Entity Extraction Service.

    Performs comprehensive health checks including:
    1. Port availability (8007)
    2. Health ping endpoint
    3. Extract endpoint with minimal payload
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8007,
        timeout: int = 30
    ):
        """
        Initialize health checker.

        Args:
            host: Service hostname
            port: Service port (default 8007)
            timeout: Request timeout in seconds (default 30 to accommodate vLLM inference ~16s)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"

    def check_port_listening(self) -> bool:
        """
        Check if service port is listening.

        Returns:
            bool: True if port is listening
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"Port check failed: {e}")
            return False

    def check_health_endpoint(self) -> tuple[bool, Optional[float]]:
        """
        Check health ping endpoint.

        Returns:
            tuple: (success: bool, response_time_ms: Optional[float])
        """
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/api/v1/health/ping",
                timeout=self.timeout
            )
            response_time_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return True, response_time_ms
            else:
                logger.warning(f"Health endpoint returned status {response.status_code}")
                return False, response_time_ms

        except requests.exceptions.RequestException as e:
            logger.error(f"Health endpoint check failed: {e}")
            return False, None

    def check_extract_endpoint(self) -> tuple[bool, Optional[float], Optional[Dict]]:
        """
        Check extract endpoint with minimal test payload.

        Returns:
            tuple: (success: bool, response_time_ms: Optional[float], response_data: Optional[Dict])
        """
        try:
            # Minimal test payload
            test_payload = {
                "document_text": "Test document: United States v. Rahimi, 602 U.S. 1 (2024)",
                "document_id": "health_check_test"
            }

            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/v2/process/extract",
                json=test_payload,
                timeout=self.timeout
            )
            response_time_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return True, response_time_ms, response.json()
            else:
                logger.warning(f"Extract endpoint returned status {response.status_code}")
                return False, response_time_ms, None

        except requests.exceptions.RequestException as e:
            logger.error(f"Extract endpoint check failed: {e}")
            return False, None, None

    def perform_health_check(self) -> HealthCheckResult:
        """
        Perform comprehensive health check.

        Returns:
            HealthCheckResult: Complete health check results
        """
        logger.info(f"Starting health check for {self.base_url}")

        # Check 1: Port listening
        port_listening = self.check_port_listening()
        if not port_listening:
            return HealthCheckResult(
                service_up=False,
                port_listening=False,
                health_endpoint_ok=False,
                extract_endpoint_ok=False,
                response_time_ms=0.0,
                error_message=f"Port {self.port} is not listening"
            )

        # Check 2: Health endpoint
        health_ok, health_time = self.check_health_endpoint()

        # Check 3: Extract endpoint
        extract_ok, extract_time, extract_data = self.check_extract_endpoint()

        # Calculate overall response time
        response_time = 0.0
        if health_time:
            response_time += health_time
        if extract_time:
            response_time += extract_time

        # Determine overall service status
        service_up = port_listening and health_ok and extract_ok

        # Build error message if needed
        error_message = None
        if not service_up:
            errors = []
            if not health_ok:
                errors.append("Health endpoint failed")
            if not extract_ok:
                errors.append("Extract endpoint failed")
            error_message = "; ".join(errors)

        # Build details
        details = {
            "base_url": self.base_url,
            "health_response_ms": health_time,
            "extract_response_ms": extract_time,
            "extract_test_data": extract_data
        }

        return HealthCheckResult(
            service_up=service_up,
            port_listening=port_listening,
            health_endpoint_ok=health_ok,
            extract_endpoint_ok=extract_ok,
            response_time_ms=response_time,
            error_message=error_message,
            details=details
        )


def check_service_health(
    host: str = "localhost",
    port: int = 8007,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Convenience function to check service health.

    Args:
        host: Service hostname
        port: Service port
        timeout: Request timeout

    Returns:
        dict: Health check results as dictionary
    """
    checker = ServiceHealthChecker(host=host, port=port, timeout=timeout)
    result = checker.perform_health_check()

    return {
        "service_up": result.service_up,
        "port_listening": result.port_listening,
        "health_endpoint_ok": result.health_endpoint_ok,
        "extract_endpoint_ok": result.extract_endpoint_ok,
        "response_time_ms": result.response_time_ms,
        "error_message": result.error_message,
        "details": result.details
    }


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run health check
    result = check_service_health()

    # Print results
    print("\n" + "="*70)
    print("Entity Extraction Service Health Check")
    print("="*70)
    print(f"Service Status: {'✅ HEALTHY' if result['service_up'] else '❌ UNHEALTHY'}")
    print(f"Port 8007 Listening: {'✅' if result['port_listening'] else '❌'}")
    print(f"Health Endpoint: {'✅' if result['health_endpoint_ok'] else '❌'}")
    print(f"Extract Endpoint: {'✅' if result['extract_endpoint_ok'] else '❌'}")
    print(f"Response Time: {result['response_time_ms']:.2f}ms")

    if result['error_message']:
        print(f"\n❌ Errors: {result['error_message']}")

    if result['details']:
        print(f"\nDetails:")
        print(f"  Base URL: {result['details']['base_url']}")
        if result['details']['health_response_ms']:
            print(f"  Health Response: {result['details']['health_response_ms']:.2f}ms")
        if result['details']['extract_response_ms']:
            print(f"  Extract Response: {result['details']['extract_response_ms']:.2f}ms")

    print("="*70 + "\n")
