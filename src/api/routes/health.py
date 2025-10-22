"""
Health Check Routes for Entity Extraction Service

Standardized health monitoring endpoints following common patterns.
Includes performance monitoring and dependency checks.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# Track service start time
SERVICE_START_TIME = datetime.utcnow()
start_time = time.time()


# Standard Health Response Models
class HealthResponse(BaseModel):
    """Basic health check response model."""
    status: str = Field(..., description="Health status: 'healthy', 'degraded', or 'unhealthy'")
    service_name: str = Field(default="entity-extraction-service")
    service_version: str = Field(default="2.0.0")
    timestamp: str = Field(..., description="ISO format timestamp")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")


class PingResponse(BaseModel):
    """Simple ping response for load balancers."""
    ping: str = "pong"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ReadinessResponse(HealthResponse):
    """Readiness check response with dependency status."""
    ready: bool = Field(..., description="Whether the service is ready to handle requests")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Status of external dependencies")


class DetailedHealthResponse(HealthResponse):
    """Detailed health check response with all checks and metrics."""
    checks: Dict[str, Any] = Field(default_factory=dict, description="Component health checks")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="External dependency status")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance and resource metrics")
    extraction_modes: list = Field(default_factory=list, description="Available extraction modes")
    patterns_loaded: int = Field(default=0, description="Number of patterns loaded")
    ai_integration: str = Field(default="unavailable", description="AI integration status")
    service_mode: str = Field(default="unknown", description="Current service operational mode")
    wave_system_available: bool = Field(default=False, description="Wave System v2 (ExtractionOrchestrator) availability")
    capabilities: list = Field(default_factory=list, description="List of functional capabilities")


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns service status and basic information.
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    return HealthResponse(
        status="healthy",
        service_name="entity-extraction-service",
        service_version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime
    )


@router.get("/health/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    """
    Simple ping endpoint for load balancers.
    
    Returns a simple pong response with timestamp.
    """
    return PingResponse()


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(request: Request) -> ReadinessResponse:
    """
    Readiness check endpoint with dependency verification.
    
    Checks if the service and its dependencies are ready to handle requests.
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    # Check dependencies
    dependencies = await check_dependencies(request)
    
    # Determine if service is ready
    critical_deps = ["entity_extraction", "pattern_loader"]
    ready = all(
        dependencies.get(dep) == "healthy" 
        for dep in critical_deps 
        if dep in dependencies
    )
    
    # Calculate overall status
    if not ready:
        status = "unhealthy"
    elif any(v != "healthy" for v in dependencies.values()):
        status = "degraded"
    else:
        status = "healthy"
    
    return ReadinessResponse(
        status=status,
        service_name="entity-extraction-service",
        service_version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        ready=ready,
        dependencies=dependencies
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health(request: Request) -> DetailedHealthResponse:
    """
    Detailed health check endpoint with comprehensive information.

    Returns detailed health status including all checks, dependencies, and metrics.
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()

    # Check dependencies
    dependencies = await check_dependencies(request)

    # Check components
    checks = await check_components(request)

    # Collect metrics
    metrics = await collect_metrics(request)

    # Get extraction capabilities
    extraction_info = await get_extraction_capabilities(request)

    # Calculate overall status
    status = calculate_overall_status(checks, dependencies)

    # Get service mode and capabilities
    service_mode = getattr(request.app.state, 'service_mode', 'unknown')

    # Determine component availability
    vllm_client = getattr(request.app.state, 'vllm_client', None)
    pattern_loader = getattr(request.app.state, 'pattern_loader', None)

    # Wave System v2 is available when vLLM is ready (ExtractionOrchestrator uses vLLM directly)
    wave_system_available = vllm_client is not None and vllm_client.is_ready()

    # Build capabilities list
    capabilities = []
    if pattern_loader:
        capabilities.append("pattern_extraction")
    if wave_system_available:
        capabilities.append("wave_system_v2_extraction")
    if vllm_client and vllm_client.is_ready():
        capabilities.append("ai_processing")

    return DetailedHealthResponse(
        status=status,
        service_name="entity-extraction-service",
        service_version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        checks=checks,
        dependencies=dependencies,
        metrics=metrics,
        extraction_modes=extraction_info["modes"],
        patterns_loaded=extraction_info["patterns_loaded"],
        ai_integration=extraction_info["ai_integration"],
        service_mode=service_mode,
        wave_system_available=wave_system_available,
        capabilities=capabilities
    )


# Legacy endpoints for backward compatibility (will be deprecated)
@router.get("/health/dependencies")
async def check_dependencies_endpoint(request: Request) -> Dict[str, Any]:
    """
    Legacy endpoint for checking dependencies.
    Deprecated - use /health/detailed instead.
    """
    dependencies = await check_dependencies(request)
    return {
        "status": "operational" if all(v == "healthy" for v in dependencies.values()) else "degraded",
        "dependencies": dependencies,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "This endpoint is deprecated. Please use /health/detailed instead."
    }


@router.get("/health/performance")
async def performance_health(request: Request) -> Dict[str, Any]:
    """
    Legacy endpoint for performance metrics.
    Deprecated - use /health/detailed instead.
    """
    metrics = await collect_metrics(request)
    return {
        "status": "healthy",
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "This endpoint is deprecated. Please use /health/detailed instead."
    }


# Helper functions
async def check_dependencies(request: Request) -> Dict[str, str]:
    """Check status of external dependencies."""
    dependencies = {}
    
    # Check Log Service
    try:
        log_client = getattr(request.app.state, "log_client", None)
        if log_client:
            dependencies["log_service"] = "healthy"
        else:
            dependencies["log_service"] = "unavailable"
    except Exception as e:
        logger.warning(f"Log service health check failed: {e}")
        dependencies["log_service"] = "unhealthy"
    
    # Check vLLM client (primary AI service)
    try:
        vllm_client = getattr(request.app.state, "vllm_client", None)
        if vllm_client and vllm_client.is_ready():
            dependencies["vllm_service"] = "healthy"
        else:
            dependencies["vllm_service"] = "unavailable"
    except Exception as e:
        logger.warning(f"vLLM client health check failed: {e}")
        dependencies["vllm_service"] = "unhealthy"
    
    # Check Supabase Service
    try:
        supabase_client = getattr(request.app.state, "supabase_client", None)
        if supabase_client:
            dependencies["supabase_service"] = "healthy"
        else:
            dependencies["supabase_service"] = "unavailable"
    except Exception as e:
        logger.warning(f"Supabase service health check failed: {e}")
        dependencies["supabase_service"] = "unhealthy"
    
    return dependencies


async def check_components(request: Request) -> Dict[str, Any]:
    """Check status of internal components."""
    checks = {}

    # Check entity extraction - Wave System v2 uses ExtractionOrchestrator directly
    try:
        vllm_client = getattr(request.app.state, "vllm_client", None)

        if vllm_client and vllm_client.is_ready():
            checks["entity_extraction"] = {
                "status": "healthy",
                "message": "Entity extraction operational with Wave System v2 (ExtractionOrchestrator)",
                "mode": "wave_system_v2",
                "components": {
                    "vllm_client": "ready",
                    "extraction_orchestrator": "available"
                }
            }
        elif vllm_client:
            checks["entity_extraction"] = {
                "status": "degraded",
                "message": "vLLM client initialized but not ready",
                "mode": "wave_system_v2",
                "components": {
                    "vllm_client": "not_ready",
                    "extraction_orchestrator": "unavailable"
                }
            }
        else:
            checks["entity_extraction"] = {
                "status": "unhealthy",
                "message": "vLLM client not initialized - AI extraction unavailable",
                "components": {
                    "vllm_client": "missing",
                    "extraction_orchestrator": "unavailable"
                }
            }
    except Exception as e:
        checks["entity_extraction"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check pattern loader
    try:
        pattern_loader = getattr(request.app.state, "pattern_loader", None)
        if pattern_loader:
            pattern_count = len(pattern_loader.patterns) if hasattr(pattern_loader, "patterns") else 0
            checks["pattern_loader"] = {
                "status": "healthy",
                "patterns_loaded": pattern_count,
                "message": f"Loaded {pattern_count} patterns"
            }
        else:
            checks["pattern_loader"] = {
                "status": "unavailable",
                "message": "Pattern loader not initialized"
            }
    except Exception as e:
        checks["pattern_loader"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return checks


async def collect_metrics(request: Request) -> Dict[str, Any]:
    """Collect performance and resource metrics."""
    metrics = {}

    # Basic metrics
    metrics["uptime_seconds"] = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    metrics["current_time"] = datetime.utcnow().isoformat()

    # Request metrics (if tracked)
    try:
        request_counter = getattr(request.app.state, "request_counter", 0)
        metrics["total_requests"] = request_counter
    except:
        pass

    return metrics


async def get_extraction_capabilities(request: Request) -> Dict[str, Any]:
    """Get entity extraction capabilities."""
    # Get pattern count
    pattern_loader = getattr(request.app.state, "pattern_loader", None)
    patterns_loaded = len(pattern_loader.get_entity_types()) if pattern_loader else 0

    info = {
        "modes": ["ai_enhanced", "hybrid"],  # regex deprecated, spacy removed
        "patterns_loaded": patterns_loaded,
        "ai_integration": "unavailable"
    }

    # Check AI integration via vLLM
    try:
        vllm_client = getattr(request.app.state, "vllm_client", None)
        if vllm_client and vllm_client.is_ready():
            info["ai_integration"] = "vllm_available"
            info["ai_backend"] = "vllm_instruct"
            info["wave_system_v2"] = "available"
    except:
        pass

    return info


def calculate_overall_status(checks: Dict[str, Any], dependencies: Dict[str, str]) -> str:
    """Calculate overall health status based on checks and dependencies."""
    
    # Check for any unhealthy components
    for check in checks.values():
        if isinstance(check, dict) and check.get("status") == "unhealthy":
            return "unhealthy"
    
    for status in dependencies.values():
        if status == "unhealthy":
            return "unhealthy"
    
    # Check for degraded components
    for check in checks.values():
        if isinstance(check, dict) and check.get("status") == "degraded":
            return "degraded"
    
    for status in dependencies.values():
        if status == "degraded" or status == "unavailable":
            return "degraded"
    
    return "healthy"