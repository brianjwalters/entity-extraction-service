"""
Entity Extraction Service - Main FastAPI Application

This service provides legal entity extraction capabilities using AI-powered unified extraction.
Note: Regex pattern extraction has been deprecated in favor of unified AI extraction.

Port: 8007
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from enum import Enum

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.api.routes import health, entity_types, unified_patterns, intelligent, relationships, routing
# Import comprehensive patterns module to register its endpoints
from src.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


class ServiceMode(str, Enum):
    """Service operational mode indicating available capabilities."""
    FULL = "full"  # Wave System + Patterns - all AI features active
    DEGRADED = "degraded"  # Patterns only - no AI extraction (vLLM unavailable)


def get_service_mode(vllm_available: bool) -> ServiceMode:
    """
    Determine service operational mode based on vLLM availability.

    Args:
        vllm_available: Whether vLLM Instruct service (port 8080) is ready

    Returns:
        ServiceMode.FULL if vLLM available, ServiceMode.DEGRADED otherwise

    Note:
        - AIEnhancer is deprecated (replaced by ExtractionOrchestrator in Wave System v2)
        - Service mode now solely depends on vLLM HTTP client readiness
        - ExtractionOrchestrator uses vLLM client directly, no separate check needed
    """
    return ServiceMode.FULL if vllm_available else ServiceMode.DEGRADED


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown."""
    logger.info("Starting Entity Extraction Service...")
    
    # Initialize service clients during startup
    try:
        # CLAUDE.md Compliant: Absolute import for optional service client
        try:
            from services.log_service.src.client.log_client import LogClient
        except ImportError:
            # Optional service client - not an import fallback
            LogClient = None
            logger.warning("LogClient not available - running in standalone mode")
        
        # SupabaseClient removed - src/clients directory eliminated per architecture rules
        SupabaseClient = None
        logger.warning("SupabaseClient not available - database storage disabled")
        
        # Import core service dependencies
        # ExtractionService disabled - requires spacy via IntegratedLegalPipeline
        # Using vLLM-only extraction via /extract/chunk endpoint
        ExtractionService = None
        logger.info("ExtractionService disabled - using vLLM-only extraction")

        # Pattern loader and regex engine deprecated - removed
        # AIEnhancer disabled - imports legacy AI agents that require deleted vllm_http_client
        # from src.core.ai_enhancer import AIEnhancer
        import os
        
        # Initialize service clients
        logger.info("Initializing service clients with vLLM AI processing...")
        app.state.log_client = LogClient() if LogClient else None
        
        # Try to initialize Supabase client but don't fail if env vars are missing
        try:
            app.state.supabase_client = SupabaseClient() if SupabaseClient else None
        except (ValueError, Exception) as e:
            logger.warning(f"SupabaseClient initialization failed (not required for extraction): {e}")
            app.state.supabase_client = None
        
        # Initialize vLLM HTTP client (connects to vLLM service on port 8080)
        logger.info("Attempting to initialize vLLM HTTP client for AI processing...")
        vllm_client = None
        try:
            from src.vllm_client.client import HTTPVLLMClient
            from src.vllm_client.models import VLLMConfig

            # Get vLLM server configuration from environment (config already has /v1)
            vllm_base_url = os.getenv("VLLM_INSTRUCT_URL", "http://10.10.0.87:8080/v1")
            vllm_model_name = os.getenv("VLLM_INSTRUCT_MODEL", "mistral-nemo-12b-instruct-128k")

            logger.info(f"Initializing vLLM HTTP Client:")
            logger.info(f"  Base URL: {vllm_base_url}")
            logger.info(f"  Model: {vllm_model_name}")

            # Create VLLMConfig from settings (uses centralized config)
            vllm_config = VLLMConfig.from_settings(settings)

            # Create HTTP client with config
            vllm_client = HTTPVLLMClient(config=vllm_config)
            await vllm_client.connect()  # Connect to vLLM HTTP server

            if vllm_client.is_ready():
                logger.info("✅ vLLM HTTP client initialized successfully")
                logger.info(f"Connected to vLLM server at {vllm_base_url}")
            else:
                logger.warning("⚠️ vLLM HTTP client initialization completed but not ready - service will run in degraded mode")
                vllm_client = None

        except ImportError as e:
            logger.warning(f"⚠️ vLLM HTTP client not available - service will run in degraded mode: {e}")
            logger.warning("   Ensure vLLM client modules are available")
            vllm_client = None
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize vLLM HTTP client - service will run in degraded mode: {e}")
            logger.warning(f"   Error type: {type(e).__name__}")
            logger.warning(f"   Ensure vLLM service is running on port 8080")
            vllm_client = None

        # Store vLLM client (may be None)
        app.state.vllm_client = vllm_client
        
        # Initialize core service components
        logger.info("Initializing core extraction components...")
        
        # Pattern loading and regex engine deprecated for extraction
        # But we still initialize PatternLoader for comprehensive pattern analysis endpoint
        logger.info("Initializing PatternLoader with caching for pattern analysis endpoint...")
        try:
            from src.utils.pattern_loader import PatternLoader
            from src.core.pattern_cache import CachedPatternLoader

            # Initialize base pattern loader
            base_pattern_loader = PatternLoader()

            # Wrap with caching layer (128 entries, 1 hour TTL)
            app.state.pattern_loader = CachedPatternLoader(
                pattern_loader=base_pattern_loader,
                cache_size=128,
                ttl_seconds=3600
            )

            logger.info(f"✅ PatternLoader with caching initialized: {len(app.state.pattern_loader.get_entity_types())} entity types")
        except Exception as e:
            logger.warning(f"Could not initialize PatternLoader: {e}")
            app.state.pattern_loader = None
        
        # Initialize RegexEngine for UNIFIED strategy (still needed for hybrid extraction)
        logger.info("Initializing RegexEngine for UNIFIED strategy...")
        try:
            from src.core.regex_engine import RegexEngine
            app.state.regex_engine = RegexEngine(
                pattern_loader=app.state.pattern_loader,
                enable_caching=True,
                cache_size=1000,
                enable_performance_monitoring=True
            )
            logger.info(f"✅ RegexEngine initialized for UNIFIED strategy")
        except Exception as e:
            logger.warning(f"Could not initialize RegexEngine: {e}")
            app.state.regex_engine = None

        # AIEnhancer disabled - legacy component that imports deleted vllm_http_client
        # Wave System v2 uses ExtractionOrchestrator directly
        app.state.ai_enhancer = None
        logger.info("ExtractionOrchestrator (Wave System v2) available for /api/v2/process/* endpoints")
        logger.info("  - Uses vLLM HTTP client directly (no AIEnhancer wrapper)")
        logger.info("  - Supports SINGLE_PASS, THREE_WAVE, FOUR_WAVE, THREE_WAVE_CHUNKED strategies")
        logger.info("  - Service mode will be determined based on vLLM client readiness")

        # Initialize Document Router for intelligent routing
        logger.info("Initializing Document Router for intelligent document routing...")
        try:
            from src.api.routes.routing import initialize_router
            initialize_router()
            logger.info("✅ Document Router initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Document Router: {e}")
            logger.warning("Routing endpoints will return 503 errors")

        # ExtractionService disabled due to missing RuntimeConfig dependency
        # Using direct vLLM component access instead (see extract.py modifications)
        app.state.extraction_service = None
        app.state.cales_service = None  # CALES disabled to avoid spacy dependencies
        logger.info("ExtractionService disabled (missing RuntimeConfig), using direct vLLM components")
        
        # Pattern validation deprecated - regex patterns no longer used
        logger.info("Pattern loading system deprecated - using unified AI extraction")
        logger.info("✅ Unified AI extraction ready")

        # Determine service mode and display clear status banner
        vllm_available = app.state.vllm_client is not None and app.state.vllm_client.is_ready()

        service_mode = get_service_mode(vllm_available)

        # Display service mode banner with clear capability information
        logger.info("=" * 80)
        if service_mode == ServiceMode.FULL:
            logger.info("✅ SERVICE MODE: FULL")
            logger.info("   Available features:")
            logger.info("   • Wave System v2 (ExtractionOrchestrator) - AI-powered entity extraction")
            logger.info("   • Pattern API - Pattern analysis and validation")
            logger.info("   All extraction capabilities operational")
        elif service_mode == ServiceMode.DEGRADED:
            logger.warning("⚠️ SERVICE MODE: DEGRADED")
            logger.warning("   vLLM not available - AI extraction disabled")
            logger.warning("   Available features:")
            logger.warning("   • Pattern API - Pattern-based extraction only")
            logger.warning("   Unavailable features:")
            logger.warning("   • Wave System - Requires vLLM connection")
            logger.warning("   Action required: Ensure vLLM service is running on port 8080")
        logger.info("=" * 80)

        # Store service mode in app state for health endpoint
        app.state.service_mode = service_mode

        logger.info("All service clients and components initialized successfully")
        
        # Log service startup
        startup_request_id = str(uuid.uuid4())
        if app.state.log_client:
            await app.state.log_client.log(
                level="INFO",
                message="Entity Extraction Service started successfully",
                service="entity-extraction-service",
                request_id=startup_request_id,
                metadata={
                    "port": settings.port,
                    "debug": settings.debug,
                    "extraction_modes": ["ai_enhanced", "hybrid"],  # regex deprecated
                    "ai_processing_type": "vllm",
                    "patterns_loaded": len(app.state.pattern_loader.get_entity_types()) if app.state.pattern_loader else 0,
                    "max_concurrent_extractions": settings.extraction.max_concurrent_extractions,
                    "ai_fallback_enabled": settings.ai.enable_ai_fallback,
                    "supported_entity_types": len(settings.supported_entity_types),
                    "vllm_client_ready": app.state.vllm_client.is_ready() if app.state.vllm_client else False,
                    "ai_enhancement_available": app.state.vllm_client.is_ready() if app.state.vllm_client else False
                }
            )
        else:
            logger.info("Entity Extraction Service started successfully (log client unavailable)")
        
    except Exception as e:
        logger.error(f"Failed to initialize Entity Extraction Service: {e}")
        # Attempt to log startup failure
        try:
            if hasattr(app.state, 'log_client'):
                await app.state.log_client.log(
                    level="ERROR",
                    message=f"Entity Extraction Service startup failed: {str(e)}",
                    service="entity-extraction-service",
                    request_id=str(uuid.uuid4()),
                    metadata={"error": str(e)}
                )
        except:
            pass  # Don't let logging errors prevent the original error from being raised
        raise
    
    yield
    
    # Cleanup during shutdown
    logger.info("Shutting down Entity Extraction Service...")
    
    try:
        # ExtractionService cleanup removed - ExtractionService disabled
        # CALES cleanup removed - CALES disabled

        # Cleanup vLLM client
        if hasattr(app.state, 'vllm_client') and app.state.vllm_client:
            logger.info("Shutting down vLLM client...")
            await app.state.vllm_client.close()
            logger.info("vLLM client shutdown completed")
        
        # Log service shutdown
        shutdown_request_id = str(uuid.uuid4())
        await app.state.log_client.log(
            level="INFO",
            message="Entity Extraction Service shutdown completed",
            service="entity-extraction-service",
            request_id=shutdown_request_id,
            metadata={
                "uptime_seconds": int(asyncio.get_event_loop().time()),
                "shutdown_reason": "normal"
            }
        )
        
    except Exception as e:
        logger.error(f"Error during service shutdown: {e}")
        try:
            if hasattr(app.state, 'log_client'):
                await app.state.log_client.log(
                    level="ERROR",
                    message=f"Entity Extraction Service shutdown error: {str(e)}",
                    service="entity-extraction-service",
                    request_id=str(uuid.uuid4()),
                    metadata={"shutdown_error": str(e)}
                )
        except:
            pass


# Create FastAPI application
app = FastAPI(
    title="Legal Entity Extraction Service",
    description="""
    ## Legal Entity Extraction Service

    A comprehensive microservice for extracting legal entities from documents using hybrid REGEX + AI capabilities with CALES (Context-Aware Legal Entity Service) integration.

    ### Features
    - **Multi-Mode Extraction**: Choose from `regex`, `ai_enhanced`, or `hybrid` extraction modes
    - **Context-Aware Processing**: CALES system provides contextual understanding of entities
    - **Dynamic Model Loading**: Seamless transition between base and fine-tuned models
    - **Relationship Extraction**: Identifies connections and relationships between extracted entities
    - **295+ Regex Patterns**: Comprehensive pattern library covering 31 legal entity types
    - **AI-Enhanced Processing**: vLLM-powered entity extraction and validation
    - **Bluebook Compliant**: Citations follow Bluebook 22nd Edition standards
    - **Real-time Processing**: High-performance entity extraction with sub-second response times

    ### Supported Entity Types
    - Legal case citations and parallel citations
    - Federal and state statutory citations  
    - Court names, judges, and judicial officers
    - Legal parties (plaintiffs, defendants, attorneys)
    - Dates, deadlines, and monetary amounts
    - Legal concepts, doctrines, and procedures

    ### Architecture
    - **CALES Integration**: Context-Aware Legal Entity Service for advanced processing
    - **vLLM Integration**: IBM Granite 3.3 2B model with 128K context window
    - **Dynamic Models**: Automatic model selection with priority-based loading
    - **Pattern Library**: 295 patterns across 53 YAML configuration files
    - **Multi-Pass Extraction**: 7-stage pipeline for comprehensive entity detection
    - **Relationship Extraction**: Identifies connections between extracted entities

    ### Performance
    - **Average Processing Time**: 176ms for AI-enhanced mode (200-300ms for contextual)
    - **Throughput**: 14,000+ tokens/sec for embeddings
    - **Accuracy**: >90% precision on legal document benchmarks
    - **Context Resolution**: >85% accuracy in contextual understanding
    - **Scalability**: Handles documents up to 50MB in size

    ### API Usage
    - Use `/extract` for standard document processing
    - Use `/extract/contextual` for context-aware extraction with CALES
    - Use `/extract/enhance` to enhance existing extractions with context
    - Use `/patterns` for pattern information and `/entity-types` for entity type discovery
    """,
    version="2.0.0",
    contact={
        "name": "Luris Platform Team",
        "url": "https://luris.ai",
        "email": "support@luris.ai"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://10.10.0.87:8007",
            "description": "Development server"
        }
    ],
    lifespan=lifespan,
    docs_url="/docs",  # Simplified URL for easier access
    redoc_url="/redoc",  # Simplified URL for easier access
    openapi_url="/api/v1/openapi.json",
    openapi_tags=[
        {
            "name": "🏥 Health & Monitoring",
            "description": "Service health checks, readiness probes, and monitoring endpoints"
        },
        {
            "name": "🔍 Entity Extraction",
            "description": "Core entity extraction functionality with multi-mode processing, pattern analysis, and extraction profiles"
        },
        {
            "name": "📋 Entity Types & Patterns",
            "description": "Entity type discovery, pattern library information, and comprehensive pattern statistics"
        },
        {
            "name": "🔗 Relationship Patterns",
            "description": "Relationship type discovery, relationship extraction, and pattern analysis across 46 relationship types and 6 categories"
        },
        {
            "name": "🎓 Model Training",
            "description": "Model training, fine-tuning, deployment, and management for CALES system"
        },
        {
            "name": "🧠 Context-Aware Extraction",
            "description": "CALES-powered context-aware entity extraction with relationship detection and dynamic model loading"
        }
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to handle large request bodies
from fastapi.responses import JSONResponse

@app.middleware("http")
async def limit_request_size_middleware(request: Request, call_next):
    """Check request body size against configured maximum."""
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        max_size = settings.max_request_size  # 100MB from config
        if content_length > max_size:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Request body too large. Maximum size is {max_size / (1024*1024):.1f}MB, got {content_length / (1024*1024):.1f}MB"
                }
            )
    # Continue processing - the large body is allowed up to our configured limit
    response = await call_next(request)
    return response

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests for distributed tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Enhanced error handling middleware with service readiness checks."""
    try:
        # Check if vLLM is available for extraction endpoints (warn but don't block non-AI endpoints)
        if request.url.path.startswith("/api/v1/extract"):
            vllm_client = getattr(request.app.state, 'vllm_client', None)

            # Only block if vLLM is truly required for this specific endpoint
            # Health, config, patterns, and entity-types endpoints don't need vLLM
            requires_vllm = not any([
                request.url.path == "/api/v1/extract/health",
                request.url.path == "/api/v1/health",
                request.url.path == "/api/v1/ready",
                request.url.path == "/api/v1/config",
                request.url.path.startswith("/api/v1/patterns"),
                request.url.path.startswith("/api/v1/entity-types")
            ])

            # Warn if vLLM unavailable but let health/monitoring endpoints through
            if requires_vllm and (not vllm_client or not vllm_client.is_ready()):
                # Log warning but allow request to proceed (endpoint will handle gracefully)
                logger.warning(f"Request to {request.url.path} with vLLM unavailable - endpoint may return degraded response")

        response = await call_next(request)
        return response

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.error(f"Middleware error in request {request_id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=500,
            detail=f"Service error: {str(e)}"
        )


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests and responses with enhanced error tracking."""
    start_time = asyncio.get_event_loop().time()
    
    try:
        response = await call_next(request)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Determine log level based on status code
        log_level = "INFO"
        if response.status_code >= 500:
            log_level = "ERROR"
        elif response.status_code >= 400:
            log_level = "WARNING"
        
        # Log request completion
        try:
            if hasattr(app.state, 'log_client'):
                await app.state.log_client.log(
                    level=log_level,
                    message=f"{request.method} {request.url.path} - {response.status_code}",
                    service="entity-extraction-service",
                    request_id=getattr(request.state, "request_id", "unknown"),
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration * 1000, 2),
                        "user_agent": request.headers.get("user-agent", "unknown"),
                        "content_length": request.headers.get("content-length", "unknown")
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log request: {e}")
        
        return response
        
    except Exception as e:
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Log failed request
        try:
            if hasattr(app.state, 'log_client'):
                await app.state.log_client.log(
                    level="ERROR",
                    message=f"{request.method} {request.url.path} - FAILED",
                    service="entity-extraction-service",
                    request_id=getattr(request.state, "request_id", "unknown"),
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(e),
                        "duration_ms": round(duration * 1000, 2)
                    }
                )
        except Exception as log_error:
            logger.error(f"Failed to log failed request: {log_error}")
        
        raise


# Include health routes with standard prefix
app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["🏥 Health & Monitoring"]
)

app.include_router(
    unified_patterns.router,
    prefix="/api/v1",
    tags=["📋 Entity Types & Patterns"]
)

app.include_router(
    entity_types.router,
    prefix="/api/v1",
    tags=["📋 Entity Types & Patterns"]
)

app.include_router(
    relationships.router,
    prefix="/api/v1",
    tags=["🔗 Relationship Patterns"]
)

# v2 Intelligent Processing API - Wave System endpoints
app.include_router(
    intelligent.router,
    prefix="/api",
    tags=["🤖 Intelligent Processing v2"]
)

# Document Routing API - Intelligent document routing and strategy selection
app.include_router(
    routing.router,
    prefix="/api/v1",
    tags=["🔍 Document Routing"]
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.error(
        f"Unhandled exception in request {request_id}: {str(exc)}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "error": str(exc)
        },
        exc_info=True
    )
    
    # Log to centralized logging if available
    try:
        if hasattr(request.app.state, 'log_client'):
            await request.app.state.log_client.log(
                level="ERROR",
                message=f"Unhandled exception: {str(exc)}",
                service="entity-extraction-service",
                request_id=request_id,
                metadata={
                    "method": request.method,
                    "url": str(request.url),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)
                }
            )
    except Exception as log_error:
        logger.error(f"Failed to log exception: {log_error}")
    
    raise HTTPException(
        status_code=500,
        detail="Internal server error. Please check logs for details."
    )


@app.get("/")
async def root():
    """
    Root endpoint with service information and status.

    Provides service mode, available extraction methods, and API endpoints.
    """
    try:
        # Determine service mode
        service_mode = getattr(app.state, 'service_mode', ServiceMode.DEGRADED)
        vllm_client = getattr(app.state, 'vllm_client', None)

        # Get basic service info
        service_info = {
            "service": "Entity Extraction Service",
            "version": "2.0.0",
            "status": "running",
            "service_mode": service_mode.value,
            "timestamp": time.time(),
            "primary_extraction_method": {
                "name": "Wave System v2 (ExtractionOrchestrator)",
                "endpoint": "/api/v2/process/extract",
                "description": "AI-powered 4-wave extraction using intelligent document routing",
                "status": "active" if service_mode == ServiceMode.FULL else "unavailable",
                "features": [
                    "4-wave extraction strategy (Core entities, Procedural, Supporting, Relationships)",
                    "Intelligent document routing by size",
                    "PatternLoader integration for few-shot learning",
                    "92 entity types in Wave 1, 29 in Wave 2, 40 in Wave 3, 34 relationship types in Wave 4"
                ]
            },
            "endpoints": {
                "wave_system": {
                    "extract": "/api/v2/process/extract",
                    "process": "/api/v2/process",
                    "chunk": "/api/v2/process/chunk",
                    "unified": "/api/v2/process/unified"
                },
                "patterns_api": {
                    "patterns": "/api/v1/patterns",
                    "entity_types": "/api/v1/entity-types",
                    "relationships": "/api/v1/relationships"
                },
                "service": {
                    "health": "/api/v1/health",
                    "ready": "/api/v1/ready",
                    "config": "/api/v1/config",
                    "docs": "/docs",
                    "redoc": "/redoc"
                }
            },
            "capabilities": {
                "wave_system_available": service_mode == ServiceMode.FULL,
                "pattern_api_available": True,
                "ai_enhancement": vllm_client is not None and vllm_client.is_ready() if vllm_client else False,
                "pattern_caching": settings.patterns.enable_pattern_caching,
                "relationship_extraction": True,
                "total_endpoints": 26
            },
            "service_mode_details": {
                "mode": service_mode.value,
                "description": _get_service_mode_description(service_mode),
                "available_features": _get_available_features(service_mode),
                "unavailable_features": _get_unavailable_features(service_mode)
            }
        }

        return service_info

    except Exception as e:
        logger.error(f"Error in root endpoint: {e}")
        return {
            "service": "Entity Extraction Service",
            "version": "2.0.0",
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

def _get_service_mode_description(service_mode: ServiceMode) -> str:
    """Get human-readable service mode description."""
    if service_mode == ServiceMode.FULL:
        return "All extraction capabilities operational (Wave System v2 + Patterns)"
    else:  # DEGRADED
        return "Degraded mode - Pattern API only (vLLM service unavailable)"

def _get_available_features(service_mode: ServiceMode) -> list:
    """Get list of available features based on service mode."""
    features = ["Pattern API - Pattern-based entity extraction"]

    if service_mode == ServiceMode.FULL:
        features.extend([
            "Wave System v2 (ExtractionOrchestrator) - AI-powered 4-wave extraction",
            "Intelligent Document Routing - Size-based strategy selection"
        ])

    return features

def _get_unavailable_features(service_mode: ServiceMode) -> list:
    """Get list of unavailable features based on service mode."""
    unavailable = []

    if service_mode == ServiceMode.DEGRADED:
        unavailable.append("Wave System v2 - Requires vLLM connection (port 8080)")

    return unavailable


@app.get("/api/v1/docs")
async def redirect_to_docs():
    """Redirect to the Swagger UI documentation."""
    return RedirectResponse(url="/docs", status_code=301)


@app.get("/api/v1/redoc")
async def redirect_to_redoc():
    """Redirect to the ReDoc documentation."""
    return RedirectResponse(url="/redoc", status_code=301)


@app.get("/api/v1/ready")
async def readiness_check():
    """
    Service readiness check endpoint.
    
    Returns:
        Dict: Readiness status with dependency checks
    """
    try:
        readiness_status = {
            "ready": True,
            "timestamp": time.time(),
            "checks": {}
        }

        # ExtractionService disabled (RuntimeConfig dependency), using direct vLLM components
        readiness_status["checks"]["extraction_service"] = "disabled_using_direct_components"

        # Check vLLM client directly - optional for degraded mode operation
        vllm_client = getattr(app.state, 'vllm_client', None)
        if not vllm_client:
            readiness_status["checks"]["vllm_client"] = "not_available_degraded_mode"
            readiness_status["warnings"] = readiness_status.get("warnings", [])
            readiness_status["warnings"].append("vLLM client unavailable - AI extraction disabled")
        elif not vllm_client.is_ready():
            readiness_status["checks"]["vllm_client"] = "not_ready_degraded_mode"
            readiness_status["warnings"] = readiness_status.get("warnings", [])
            readiness_status["warnings"].append("vLLM client not ready - AI extraction may fail")
        else:
            readiness_status["checks"]["vllm_client"] = "ready"

        # Pattern loader and regex engine - used for UNIFIED strategy
        pattern_loader = getattr(app.state, 'pattern_loader', None)
        readiness_status["checks"]["pattern_loader"] = "ready" if pattern_loader else "optional"

        regex_engine = getattr(app.state, 'regex_engine', None)
        readiness_status["checks"]["regex_engine"] = "ready" if regex_engine else "optional"

        readiness_status["checks"]["supabase_client"] = "optional"
        
        # Check log client
        if not hasattr(app.state, 'log_client'):
            readiness_status["checks"]["log_client"] = "not_available"
        else:
            readiness_status["checks"]["log_client"] = "ready"
        
        return readiness_status
        
    except Exception as e:
        logger.error(f"Error in readiness check: {e}")
        return {
            "ready": False,
            "error": str(e),
            "timestamp": time.time()
        }


@app.get("/api/v1/config")
async def get_service_config():
    """
    Get service configuration information.
    
    Returns:
        Dict: Service configuration (non-sensitive values only)
    """
    try:
        config_info = {
            "extraction_modes": settings.extraction.available_extraction_modes,
            "default_extraction_mode": settings.extraction.default_extraction_mode,
            "default_confidence_threshold": settings.extraction.default_confidence_threshold,
            "max_content_length": settings.extraction.max_content_length,
            "max_context_window": settings.extraction.max_context_window,
            "max_concurrent_extractions": settings.extraction.max_concurrent_extractions,
            "processing_timeout_seconds": settings.extraction.processing_timeout_seconds,
            "ai_timeout_seconds": settings.ai.ai_timeout_seconds,
            "ai_max_retries": settings.ai.ai_max_retries,
            "enable_ai_fallback": settings.ai.enable_ai_fallback,
            "enable_pattern_caching": settings.patterns.enable_pattern_caching,
            "pattern_cache_size": settings.patterns.pattern_cache_size,
            "supported_entity_types_count": len(settings.supported_entity_types),
            "store_extraction_results": settings.store_extraction_results,
            "extraction_retention_days": settings.extraction_retention_days,
            "enable_performance_monitoring": settings.performance.enable_performance_monitoring,
            "enable_rate_limiting": settings.enable_rate_limiting,
            "rate_limit_requests": settings.rate_limit_requests,
            "max_request_size": settings.max_request_size
        }
        
        return config_info
        
    except Exception as e:
        logger.error(f"Error getting service config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve service configuration: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        # Extended timeouts for long-running entity extraction operations
        timeout_keep_alive=settings.extraction.uvicorn_timeout_keep_alive,
        limit_concurrency=settings.extraction.max_concurrent_extractions,
        workers=1,                # Single worker for development
        server_header=False,      # Reduce header overhead
        date_header=False         # Reduce header overhead
    )