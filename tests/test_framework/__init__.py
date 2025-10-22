"""
Entity Extraction Service Testing Framework

A comprehensive testing framework for the Entity Extraction Service featuring:
- Service health monitoring
- Comprehensive metrics collection (22+ metrics)
- Append-only JSON storage with atomic file locking
- Interactive HTML dashboards with Chart.js visualizations
- Command-line test runner
- Slash command integration for Claude Code
- Direct vLLM integration (no HTTP overhead)
- Temperature comparison testing
- Pattern API validation

Components:
- service_health: Health checking for port 8007
- metrics_collector: Extract 22+ metrics from API responses
- storage_handler: Thread-safe append-only JSON storage
- html_generator: Interactive dashboard generation
- test_runner: Main orchestrator (HTTP API)
- orchestrator_test_runner: Direct vLLM integration (NEW)
- temperature_comparison: Temperature comparison testing (NEW)
- pattern_validator: Pattern API validation (NEW)

Usage (HTTP API):
    from test_framework import TestRunner

    runner = TestRunner()
    runner.run_test()

Usage (vLLM Direct):
    from test_framework import OrchestratorTestRunner

    client = await get_default_client()
    runner = OrchestratorTestRunner(vllm_client=client)
    await runner.run_extraction_test(
        document_path=Path("/path/to/doc.pdf"),
        char_count=5000,
        temperature=0.0,
        validate_patterns=True
    )

Command Line:
    # HTTP API testing
    python -m test_framework.test_runner

    # vLLM Direct testing
    python -m test_framework.orchestrator_test_runner --chars 5000
    python -m test_framework.orchestrator_test_runner --compare-temps
    python -m test_framework.orchestrator_test_runner --validate-patterns
"""

from .service_health import ServiceHealthChecker, check_service_health
from .metrics_collector import MetricsCollector, ComprehensiveMetrics
from .storage_handler import StorageHandler
from .html_generator import HTMLDashboardGenerator
from .test_runner import TestRunner
from .orchestrator_test_runner import OrchestratorTestRunner
from .temperature_comparison import TemperatureComparison
from .pattern_validator import PatternValidator

__version__ = "2.0.0"
__all__ = [
    "ServiceHealthChecker",
    "check_service_health",
    "MetricsCollector",
    "ComprehensiveMetrics",
    "StorageHandler",
    "HTMLDashboardGenerator",
    "TestRunner",
    "OrchestratorTestRunner",
    "TemperatureComparison",
    "PatternValidator",
]
