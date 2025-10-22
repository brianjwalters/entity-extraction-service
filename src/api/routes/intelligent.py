"""
Intelligent Processing API Routes - Document Intelligence Service v2.0.0

This module provides v2 API endpoints that leverage intelligent document routing,
direct vLLM integration, and consolidated prompting strategies.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import logging

# CLAUDE.md Compliant: Absolute imports
from src.routing.document_router import DocumentRouter, RoutingDecision, ProcessingStrategy
from src.routing.size_detector import SizeDetector, DocumentSizeInfo, SizeCategory
from src.core.config import get_settings
from src.core.extraction_orchestrator import ExtractionOrchestrator, ExtractionResult, create_extraction_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["Intelligent Processing v2"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ProcessRequest(BaseModel):
    """Request for intelligent document processing."""
    document_text: str = Field(..., description="Full document text")
    document_id: Optional[str] = Field(None, description="Document identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    force_strategy: Optional[str] = Field(None, description="Override routing: 'single_pass', 'three_wave', 'chunked'")
    enable_chunking: bool = Field(True, description="Enable intelligent chunking for large documents")
    enable_graph_storage: bool = Field(True, description="Store results in graph.chunks and graph.entities")

    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "IN THE SUPREME COURT OF THE UNITED STATES...",
                "document_id": "rahimi_2024",
                "metadata": {
                    "title": "United States v. Rahimi",
                    "court": "Supreme Court",
                    "year": 2024
                }
            }
        }


class ExtractRequest(BaseModel):
    """Request for entity extraction only (no chunking)."""
    document_text: str = Field(..., description="Full document text")
    document_id: Optional[str] = Field(None, description="Document identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    force_strategy: Optional[str] = Field(None, description="Override routing")

    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "Contract between Party A and Party B...",
                "document_id": "contract_001"
            }
        }


class ChunkRequest(BaseModel):
    """Request for chunking only (no extraction)."""
    document_text: str = Field(..., description="Full document text")
    document_id: Optional[str] = Field(None, description="Document identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    chunk_strategy: str = Field("extraction", description="Chunking strategy: 'extraction', 'semantic', 'legal'")
    chunk_size: int = Field(8000, description="Chunk size in characters")
    chunk_overlap: int = Field(500, description="Overlap between chunks")
    enable_graph_storage: bool = Field(True, description="Store chunks in graph.chunks")

    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "Long legal document...",
                "chunk_strategy": "extraction",
                "chunk_size": 8000
            }
        }


class UnifiedRequest(BaseModel):
    """Request for unified chunking + extraction in one call."""
    document_text: str = Field(..., description="Full document text")
    document_id: Optional[str] = Field(None, description="Document identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    force_strategy: Optional[str] = Field(None, description="Override routing")
    chunk_strategy: str = Field("extraction", description="Chunking strategy")
    chunk_size: int = Field(8000, description="Chunk size")
    chunk_overlap: int = Field(500, description="Overlap")
    enable_graph_storage: bool = Field(True, description="Store in graph tables")

    class Config:
        json_schema_extra = {
            "example": {
                "document_text": "Complex legal document requiring both chunking and extraction...",
                "document_id": "case_12345",
                "chunk_strategy": "legal"
            }
        }


class ProcessResponse(BaseModel):
    """Response from intelligent processing."""
    document_id: str
    routing_decision: Dict[str, Any]
    size_info: Dict[str, Any]
    chunks: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    processing_stats: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "rahimi_2024",
                "routing_decision": {
                    "strategy": "three_wave",
                    "prompt_version": "three_wave",
                    "estimated_tokens": 30838,
                    "estimated_duration": 0.85
                },
                "size_info": {
                    "chars": 45000,
                    "tokens": 11250,
                    "category": "SMALL"
                },
                "entities": [{"type": "CASE", "text": "United States v. Rahimi"}],
                "processing_stats": {
                    "duration_seconds": 0.92,
                    "entities_extracted": 142
                }
            }
        }


class ExtractResponse(BaseModel):
    """Response from extraction-only."""
    document_id: str
    entities: List[Dict[str, Any]]
    routing_decision: Dict[str, Any]
    processing_stats: Dict[str, Any]


class ChunkResponse(BaseModel):
    """Response from chunking-only."""
    document_id: str
    chunks: List[Dict[str, Any]]
    size_info: Dict[str, Any]
    processing_stats: Dict[str, Any]


class UnifiedResponse(BaseModel):
    """Response from unified processing."""
    document_id: str
    chunks: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    routing_decision: Dict[str, Any]
    size_info: Dict[str, Any]
    processing_stats: Dict[str, Any]


# ============================================================================
# Dependencies
# ============================================================================

async def get_document_router() -> DocumentRouter:
    """Get DocumentRouter instance."""
    settings = get_settings()
    # TODO: Initialize with actual configuration
    return DocumentRouter()


async def get_size_detector() -> SizeDetector:
    """Get SizeDetector instance."""
    settings = get_settings()
    # TODO: Initialize with actual configuration
    return SizeDetector()


async def get_extraction_orchestrator() -> ExtractionOrchestrator:
    """
    Get ExtractionOrchestrator instance with async vLLM client initialization.

    This factory function properly initializes the vLLM client asynchronously
    with corrected VLLMConfig parameter names.
    """
    # CLAUDE.md Compliant: Absolute imports
    from src.vllm_client.factory import VLLMClientFactory
    from src.vllm_client.models import VLLMClientType, VLLMConfig

    settings = get_settings()

    # Create VLLMConfig with CORRECTED parameter names
    config = VLLMConfig(
        model=settings.vllm_direct.vllm_model_name,  # ✅ Fixed: 'model' not 'model_name'
        base_url=f"http://{settings.vllm_direct.vllm_host}:{settings.vllm_direct.vllm_port}/v1",  # ✅ Fixed: Add /v1 for OpenAI-compatible API
        default_temperature=settings.vllm_direct.vllm_temperature,  # ✅ Fixed: 'default_temperature' not 'temperature'
        seed=settings.vllm_direct.vllm_seed,
        max_model_len=32768,  # 32K context limit
        gpu_memory_utilization=0.85  # Target 85% GPU utilization
    )

    # Determine preferred client type
    preferred = VLLMClientType.DIRECT_API if settings.vllm_direct.enable_vllm_direct else VLLMClientType.HTTP_API

    # Create vLLM client asynchronously with CORRECTED parameter name
    vllm_client = await VLLMClientFactory.create_client(
        preferred_type=preferred,  # ✅ Fixed: 'preferred_type' not 'use_direct'
        config=config,
        enable_fallback=True
    )

    # Return orchestrator with initialized client
    return ExtractionOrchestrator(
        prompt_manager=None,  # Will create default PromptManager
        vllm_client=vllm_client
    )


# ============================================================================
# v2 API Endpoints
# ============================================================================

@router.post("/process/extract", response_model=ExtractResponse, status_code=status.HTTP_200_OK)
async def extract_entities(
    request: ExtractRequest,
    router: DocumentRouter = Depends(get_document_router),
    orchestrator: ExtractionOrchestrator = Depends(get_extraction_orchestrator)
) -> ExtractResponse:
    """
    **Entity Extraction Only (v2)**

    Extracts entities without chunking. Uses intelligent routing to select
    optimal prompting strategy based on document size.

    **Use Cases:**
    - Small documents that fit in single LLM context
    - When chunking is not desired
    - When you only need entity extraction

    **Returns:**
    - Extracted entities
    - Routing decision
    - Processing statistics
    """
    document_id = request.document_id or f"doc_{hash(request.document_text) % 10000:04d}"
    logger.info(f"Extracting entities (v2): {document_id}")

    try:
        # Step 1: Route document
        routing_decision = router.route(
            document_text=request.document_text,
            metadata=request.metadata,
            strategy_override=request.force_strategy
        )

        # Step 2: Extract entities using orchestrator
        extraction_result = await orchestrator.extract(
            document_text=request.document_text,
            routing_decision=routing_decision,
            size_info=routing_decision.size_info,
            metadata=request.metadata
        )

        # Step 3: Build response
        return ExtractResponse(
            document_id=document_id,
            entities=extraction_result.entities,
            routing_decision={
                "strategy": routing_decision.strategy.value,
                "prompt_version": routing_decision.prompt_version,
                "estimated_tokens": routing_decision.estimated_tokens,
                "estimated_duration": routing_decision.estimated_duration
            },
            processing_stats={
                "duration_seconds": extraction_result.processing_time,
                "entities_extracted": len(extraction_result.entities),
                "waves_executed": extraction_result.waves_executed,
                "tokens_used": extraction_result.tokens_used,
                "metadata": extraction_result.metadata
            }
        )

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Entity extraction failed: {str(e)}",
                "document_id": document_id
            }
        )


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@router.get("/info", status_code=status.HTTP_200_OK)
async def v2_info() -> Dict[str, Any]:
    """
    **v2 API Information**

    Returns information about v2 intelligent processing capabilities.
    """
    settings = get_settings()

    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "api_version": "v2",
        "capabilities": {
            "intelligent_routing": True,
            "direct_vllm": settings.vllm_direct.enable_vllm_direct,
            "chunking_integration": settings.chunking.enable_contextual_enhancement,
            "reproducibility": settings.vllm_direct.enforce_reproducibility,
            "three_wave_system": settings.routing.enable_three_wave_prompts
        },
        "strategies": {
            "single_pass": "Very small documents (<5K chars)",
            "three_wave": "Small-medium documents (5-150K chars)",
            "chunked": "Large documents (>150K chars)"
        },
        "endpoints": {
            "extract": "POST /api/v2/process/extract - Entity extraction with intelligent routing (ACTIVE)"
        },
        "status": {
            "phase_3_1": "complete",
            "phase_3_4": "in_progress",
            "phase_3_6": "pending"
        }
    }


@router.get("/capabilities", status_code=status.HTTP_200_OK)
async def v2_capabilities() -> Dict[str, Any]:
    """
    **v2 Capabilities**

    Returns detailed capabilities and configuration of v2 API.
    """
    settings = get_settings()

    return {
        "intelligent_routing": {
            "enabled": settings.routing.enable_intelligent_routing,
            "size_thresholds": {
                "very_small": settings.routing.size_threshold_very_small,
                "small": settings.routing.size_threshold_small,
                "medium": settings.routing.size_threshold_medium
            },
            "strategies": ["single_pass", "three_wave", "chunked"]
        },
        "vllm_integration": {
            "direct_mode": settings.vllm_direct.enable_vllm_direct,
            "model": settings.vllm_direct.vllm_model_name,
            "context_limit": 32768,  # 32K context limit
            "max_tokens": settings.vllm_direct.vllm_max_tokens,
            "reproducibility": {
                "enabled": settings.vllm_direct.enforce_reproducibility,
                "temperature": settings.vllm_direct.vllm_temperature,
                "seed": settings.vllm_direct.vllm_seed
            }
        },
        "chunking": {
            "enabled": settings.chunking.enable_chunk_validation,
            "default_strategy": settings.chunking.default_chunking_strategy,
            "chunk_size": settings.routing.extraction_chunker_size,
            "chunk_overlap": settings.routing.extraction_chunker_overlap
        },
        "performance": {
            "expected_latency": {
                "very_small": "0.3-0.5s",
                "small": "0.8-1.2s",
                "medium": "5-15s",
                "large": "30-120s"
            },
            "cost_reduction": "30-40% vs v1",
            "latency_reduction": "30-50% vs v1"
        }
    }
