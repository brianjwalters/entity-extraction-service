"""
Intelligent Document Routing API

Provides endpoints for document routing and routing metadata.
"""

import logging
import time
from typing import Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.routing.document_router import DocumentRouter, ProcessingStrategy

logger = logging.getLogger(__name__)

router = APIRouter()

# Global router instance (initialized on startup)
document_router: Optional[DocumentRouter] = None


class RouteRequest(BaseModel):
    """Request model for document routing"""
    document_text: str = Field(..., description="Full document text content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional document metadata (pages, type, etc.)")
    strategy_override: Optional[str] = Field(None, description="Manual strategy override (use with caution)")

    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "IN THE UNITED STATES DISTRICT COURT...",
                "metadata": {
                    "pages": 20,
                    "document_type": "complaint"
                },
                "strategy_override": None
            }
        }


class RouteResponse(BaseModel):
    """Response model for routing decision"""
    success: bool
    request_id: str
    routing_decision: Dict[str, Any]
    is_valid: bool
    warnings: list[str]
    timestamp: float


class ProcessRequest(BaseModel):
    """Request model for document processing with routing"""
    document_text: str = Field(..., description="Full document text content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional document metadata")
    strategy_override: Optional[str] = Field(None, description="Manual strategy override")
    return_routing_metadata: bool = Field(True, description="Include routing metadata in response")

    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "Legal document content...",
                "metadata": {"pages": 10},
                "strategy_override": None,
                "return_routing_metadata": True
            }
        }


def initialize_router(config: Optional[Dict[str, Any]] = None):
    """
    Initialize the global document router instance.

    Args:
        config: Optional router configuration
    """
    global document_router
    document_router = DocumentRouter(config=config)
    logger.info("Document router initialized")


def get_router() -> DocumentRouter:
    """
    Get the global document router instance.

    Returns:
        DocumentRouter instance

    Raises:
        HTTPException: If router not initialized
    """
    if document_router is None:
        raise HTTPException(
            status_code=503,
            detail="Document router not initialized"
        )
    return document_router


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="Route Document",
    description="""
    Analyze document and determine optimal processing strategy.

    Returns routing decision with:
    - Processing strategy (single_pass, three_wave, three_wave_chunked)
    - Prompt version to use
    - Chunking configuration (if needed)
    - Token estimates and cost projections
    - Expected accuracy and processing time
    """,
    tags=["🔍 Document Routing"]
)
async def route_document(
    request: RouteRequest,
    http_request: Request
) -> RouteResponse:
    """
    Route document to optimal processing strategy.

    Args:
        request: Routing request with document text and metadata
        http_request: FastAPI request object

    Returns:
        RouteResponse with routing decision and metadata

    Raises:
        HTTPException: If routing fails
    """
    request_id = getattr(http_request.state, "request_id", str(uuid4()))
    start_time = time.time()

    try:
        logger.info(f"[{request_id}] Routing document ({len(request.document_text):,} chars)")

        # Get router instance
        router_instance = get_router()

        # Perform routing
        decision = router_instance.route(
            document_text=request.document_text,
            metadata=request.metadata,
            strategy_override=request.strategy_override
        )

        # Validate decision
        is_valid, warnings = router_instance.validate_decision(decision)

        # Log warnings
        for warning in warnings:
            logger.warning(f"[{request_id}] {warning}")

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{request_id}] Routing complete: {decision.strategy.value} | "
            f"Accuracy: {decision.expected_accuracy:.1%} | "
            f"Cost: ${decision.estimated_cost:.4f} | "
            f"Duration: {duration_ms:.2f}ms"
        )

        return RouteResponse(
            success=True,
            request_id=request_id,
            routing_decision=decision.to_dict(),
            is_valid=is_valid,
            warnings=warnings,
            timestamp=time.time()
        )

    except ValueError as e:
        logger.error(f"[{request_id}] Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"[{request_id}] Routing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Routing failed: {str(e)}"
        )


@router.get(
    "/strategies",
    summary="Get Available Strategies",
    description="Get list of available processing strategies with descriptions",
    tags=["🔍 Document Routing"]
)
async def get_strategies():
    """
    Get available processing strategies.

    Returns:
        Dict with strategy information
    """
    strategies = {
        "single_pass": {
            "name": "Single Pass",
            "description": "Single consolidated prompt for very small documents (<5K chars)",
            "entity_types": 15,
            "expected_accuracy": 0.87,
            "cost_range": "$0.003-$0.005",
            "processing_time": "~500ms",
            "use_cases": ["Short motions", "Simple contracts", "Brief correspondence"]
        },
        "three_wave": {
            "name": "Three Wave Optimized",
            "description": "3-wave extraction for small to medium documents",
            "entity_types": 34,
            "expected_accuracy": 0.90,
            "cost_range": "$0.015-$0.020",
            "processing_time": "~850-1200ms",
            "use_cases": ["Complaints", "Briefs", "Standard legal documents"]
        },
        "three_wave_chunked": {
            "name": "Three Wave Chunked",
            "description": "3-wave extraction with document chunking for large documents",
            "entity_types": 34,
            "expected_accuracy": 0.91,
            "cost_range": "Variable (based on chunks)",
            "processing_time": "2-60+ seconds",
            "use_cases": ["Long briefs", "Depositions", "Trial transcripts"]
        },
        "eight_wave_fallback": {
            "name": "Eight Wave Fallback",
            "description": "Full 8-wave extraction for maximum accuracy (fallback)",
            "entity_types": 34,
            "expected_accuracy": 0.93,
            "cost_range": "$0.025-$0.030",
            "processing_time": "~2000ms",
            "use_cases": ["Critical documents requiring maximum accuracy"]
        }
    }

    return {
        "strategies": strategies,
        "default_strategy": "automatic routing based on document size"
    }


@router.get(
    "/thresholds",
    summary="Get Size Thresholds",
    description="Get document size thresholds for routing decisions",
    tags=["🔍 Document Routing"]
)
async def get_thresholds():
    """
    Get document size thresholds.

    Returns:
        Dict with threshold information
    """
    return {
        "thresholds": {
            "very_small": {
                "char_range": "0-5,000",
                "token_range": "0-1,250",
                "strategy": "single_pass",
                "pages": "~1-2 pages"
            },
            "small": {
                "char_range": "5,001-50,000",
                "token_range": "1,251-12,500",
                "strategy": "three_wave",
                "pages": "~2-20 pages"
            },
            "medium": {
                "char_range": "50,001-150,000",
                "token_range": "12,501-37,500",
                "strategy": "three_wave_chunked",
                "pages": "~20-60 pages"
            },
            "large": {
                "char_range": ">150,000",
                "token_range": ">37,500",
                "strategy": "three_wave_chunked",
                "pages": ">60 pages"
            }
        },
        "context_limit": {
            "max_tokens": 32_768,
            "safety_margin": 2_000,
            "effective_limit": 30_768
        }
    }


@router.get(
    "/health",
    summary="Router Health Check",
    description="Check if document router is initialized and ready",
    tags=["🔍 Document Routing"]
)
async def router_health_check():
    """
    Health check for document router.

    Returns:
        Dict with health status
    """
    try:
        router_instance = get_router()

        return {
            "status": "healthy",
            "router_initialized": True,
            "max_context": router_instance.max_context,
            "safety_margin": router_instance.safety_margin,
            "adaptive_enabled": router_instance.enable_adaptive,
            "timestamp": time.time()
        }

    except HTTPException:
        return {
            "status": "unhealthy",
            "router_initialized": False,
            "error": "Document router not initialized",
            "timestamp": time.time()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "router_initialized": False,
            "error": str(e),
            "timestamp": time.time()
        }
