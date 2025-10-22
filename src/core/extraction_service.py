"""
Entity Extraction Service - Main Orchestrator

This module contains the ExtractionService class that coordinates entity extraction
workflows. It supports multiple extraction modes including regex-only, AI-enhanced,
and hybrid approaches. The RegexEngine provides fast pattern-based extraction,
while AI components enhance accuracy and coverage.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager

from ..models.requests import ExtractionRequest, ExtractionOptions
from ..models.responses import ExtractionResponse, ProcessingSummary
from ..models.entities import Entity, Citation, EntityRelationship, ExtractionMethod, TextPosition, EntityType
from ..models.extraction_strategy import ExtractionStrategy, UnifiedConfig, PageBatchConfig
from .page_batch_processor import PageBatchProcessor
from .config import get_settings, Settings
from .config import get_runtime_config
from .response_cache import get_response_cache
from .multi_pass_extractor import MultiPassExtractor
from .smart_chunker import SmartChunker, ChunkingStrategy
from .throttled_vllm_client import ThrottledVLLMClient
from .extraction_service_parallel import ParallelExtractionProcessor
from .entity_processor import EntityProcessor
from .regex_engine import RegexEngine


class ExtractionMode(Enum):
    """Supported extraction modes."""
    REGEX_ONLY = "regex_only"  # Direct regex pattern matching only
    AI_ENHANCED = "ai_enhanced"
    AI_ONLY = "ai_only"


class ExtractionStage(Enum):
    """Processing stages for extraction pipeline."""
    INITIALIZATION = "initialization"
    # REGEX_EXTRACTION = "regex_extraction"  # Deprecated
    AI_VALIDATION = "ai_validation"
    AI_ENHANCEMENT = "ai_enhancement"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    CONFIDENCE_SCORING = "confidence_scoring"
    RESULT_COMPILATION = "result_compilation"


class ExtractionError(Exception):
    """Custom exception for extraction service errors."""


class ExtractionService:
    """
    Main orchestrator for hybrid REGEX + AI entity extraction workflow.
    
    This service coordinates the complete extraction pipeline from raw text to
    validated legal entities, supporting multiple extraction modes and providing
    comprehensive error handling, logging, and performance optimization.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize ExtractionService with configuration and dependencies.
        
        Args:
            settings: Optional configuration settings
        """
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Load runtime configuration
        self.runtime_config = get_runtime_config()
        
        # Initialize components (these will be injected via dependency injection)
        self._regex_engine = None  # RegexEngine for direct pattern matching
        self._ai_enhancer = None
        self._vllm_client = None  # vLLM client for high-performance inference
        self._throttled_vllm_client = None  # Throttled wrapper for vLLM client
        self._supabase_client = None
        self._multi_pass_extractor = None  # MultiPassExtractor for strategy-based extraction
        self._smart_chunker = None  # SmartChunker for handling large documents
        self._entity_processor = EntityProcessor()  # EntityProcessor for deduplication and normalization
        self._parallel_processor = None  # ParallelExtractionProcessor for parallel chunk processing

        # Performance tracking
        self._extraction_stats = {
            "total_requests": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "avg_processing_time_ms": 0.0,
            "stage_times": {}
        }
        
        # Processing semaphore for concurrency control
        self._processing_semaphore = asyncio.Semaphore(
            self.settings.extraction.max_concurrent_extractions
        )
        
        # Cache for AI responses
        self._ai_response_cache = {}
        
        self.logger.info(
            f"ExtractionService initialized with mode: {self.settings.extraction.default_extraction_mode}, "
            f"chunking threshold: {self.runtime_config.chunking.max_chunk_size} chars"
        )
    
    def inject_dependencies(
        self,
        pattern_loader=None,  # Deprecated - use regex_engine directly
        regex_engine=None,    # RegexEngine for pattern-based extraction
        ai_enhancer=None,
        vllm_client=None,
        supabase_client=None,
        multi_pass_extractor=None
    ):
        """
        Inject service dependencies via dependency injection pattern.
        
        Args:
            pattern_loader: (Deprecated) No longer used
            regex_engine: RegexEngine instance for pattern-based extraction
            ai_enhancer: AIEnhancer instance for AI processing
            vllm_client: VLLMLocalClient for high-performance vLLM inference
            supabase_client: SupabaseClient for data persistence
            multi_pass_extractor: MultiPassExtractor for strategy-based extraction
        """
        # Deprecated components - log warning if pattern_loader provided
        if pattern_loader:
            self.logger.warning(
                "Pattern loader is deprecated. Using regex engine directly."
            )
        
        # Assign components
        self._regex_engine = regex_engine
        self._ai_enhancer = ai_enhancer
        self._vllm_client = vllm_client
        self._supabase_client = supabase_client
        self._multi_pass_extractor = multi_pass_extractor
        
        # Create throttled wrapper for vLLM client if available
        if vllm_client:
            self._throttled_vllm_client = ThrottledVLLMClient(
                vllm_client, 
                self.runtime_config
            )
            self.logger.info("Initialized ThrottledVLLMClient for rate limiting")
            
            # Update AI enhancer to use throttled client
            if self._ai_enhancer:
                self._ai_enhancer._vllm_client = self._throttled_vllm_client
        
        # Initialize SmartChunker with config
        self._smart_chunker = SmartChunker(self.runtime_config)
        self.logger.info(
            f"Initialized SmartChunker with max_chunk_size={self.runtime_config.chunking.max_chunk_size}"
        )
        
        # Initialize MultiPassExtractor if vLLM client is available but extractor not provided
        if vllm_client and not multi_pass_extractor:
            # Initialize without entity registry to avoid initialization errors
            # Use throttled client for MultiPassExtractor
            self._multi_pass_extractor = MultiPassExtractor(
                self._throttled_vllm_client or vllm_client, 
                use_entity_registry=False
            )
            self.logger.info("Initialized MultiPassExtractor with throttled vLLM client")
            
            # Initialize parallel processor for optimized chunk processing
            self._parallel_processor = ParallelExtractionProcessor(
                self._multi_pass_extractor,
                self.logger
            )
            self.logger.info("Initialized ParallelExtractionProcessor for parallel chunk processing")
        
        # Log dependency injection status
        vllm_status = "enabled" if vllm_client and vllm_client.is_ready() else "disabled"
        multi_pass_status = "enabled" if self._multi_pass_extractor else "disabled"
        chunker_status = "enabled" if self._smart_chunker else "disabled"
        
        self.logger.info(
            f"ExtractionService dependencies injected successfully. "
            f"vLLMClient: {vllm_status}, MultiPassExtractor: {multi_pass_status}, "
            f"SmartChunker: {chunker_status}"
        )
    
    def _get_chunking_config(self) -> Dict[str, Any]:
        """
        Prepare chunking configuration for AI agents.
        
        Returns:
            Dictionary containing chunking configuration parameters
        """
        return {
            'disable_micro_chunking': self.runtime_config.chunking.disable_micro_chunking,
            'force_unified_processing': self.runtime_config.chunking.force_unified_processing,
            'bypass_chunking': self.runtime_config.chunking.bypass_chunking,
            'discovery_chunk_size': self.runtime_config.chunking.discovery_chunk_size,
            'max_unified_document_size': self.runtime_config.chunking.max_unified_document_size
        }
    
    async def extract_entities(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Main extraction method that orchestrates the hybrid workflow.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Complete extraction results with metadata
            
        Raises:
            ExtractionError: If extraction fails due to critical errors
        """
        async with self._processing_semaphore:
            start_time = time.time()
            request_id = f"extract_{int(start_time * 1000)}"
            
            # Check cache first for performance optimization
            cache = get_response_cache()
            extraction_mode = self._determine_extraction_mode(request.options)
            # Get strategy value - handle both enum and string cases
            strategy = None
            if request.options and hasattr(request.options, 'extraction_strategy'):
                strategy_raw = request.options.extraction_strategy
                # If it's an enum, get its value; if it's already a string, use it directly
                strategy = strategy_raw.value if hasattr(strategy_raw, 'value') else strategy_raw
            
            # Try to get cached response
            cached_response = await cache.get(
                text=request.text,
                extraction_mode=extraction_mode.value,
                strategy=strategy,
                options=request.options.dict() if request.options else None
            )
            
            if cached_response:
                self.logger.info(
                    f"Cache HIT for document_id: {request.document_id}, strategy: {strategy}",
                    extra={
                        "event_type": "cache_hit",
                        "document_id": request.document_id,
                        "request_id": request_id,
                        "strategy": strategy,
                        "cache_response_time_ms": (time.time() - start_time) * 1000
                    }
                )
                # Update statistics for cache hit
                self._extraction_stats["total_requests"] += 1
                self._extraction_stats["successful_extractions"] += 1
                return cached_response
            
            self.logger.info(
                f"Starting extraction for document_id: {request.document_id} (cache MISS)",
                extra={
                    "event_type": "extraction_start",
                    "document_id": request.document_id,
                    "request_id": request_id,
                    "content_length": len(request.text),
                    "extraction_options": request.options.dict() if request.options else {},
                    "strategy": strategy
                }
            )

            try:
                # Default to UNIFIED strategy if not specified
                if strategy is None or strategy not in [ExtractionStrategy.MULTIPASS.value, 
                                                         ExtractionStrategy.AI_ENHANCED.value,
                                                         ExtractionStrategy.UNIFIED.value,
                                                         ExtractionStrategy.REGEX.value,
                                                         ExtractionStrategy.PAGEBATCH.value]:
                    strategy = ExtractionStrategy.UNIFIED.value
                    self.logger.info(f"No valid strategy specified, defaulting to UNIFIED for document_id: {request.document_id}")
                
                # Try primary strategy (UNIFIED) with fallback to MULTIPASS
                if strategy == ExtractionStrategy.UNIFIED.value:
                    try:
                        self.logger.info(f"Using UNIFIED strategy (primary) for document_id: {request.document_id}")
                        return await self._run_unified_extraction(request)
                    except Exception as unified_error:
                        # Log the unified extraction failure
                        self.logger.warning(
                            f"UNIFIED extraction failed for document {request.document_id}, "
                            f"falling back to MULTIPASS strategy. Error: {str(unified_error)}",
                            extra={
                                "event_type": "unified_extraction_failed",
                                "document_id": request.document_id,
                                "error": str(unified_error),
                                "fallback_strategy": "multipass"
                            }
                        )
                        # Fallback to MULTIPASS strategy
                        try:
                            self.logger.info(f"Using MULTIPASS strategy (fallback) for document_id: {request.document_id}")
                            return await self._run_multipass_extraction(request)
                        except Exception as multipass_error:
                            # Both strategies failed, re-raise the original unified error with context
                            self.logger.error(
                                f"Both UNIFIED and MULTIPASS strategies failed for document {request.document_id}",
                                extra={
                                    "unified_error": str(unified_error),
                                    "multipass_error": str(multipass_error)
                                }
                            )
                            raise Exception(
                                f"All extraction strategies failed. UNIFIED: {str(unified_error)[:200]}, "
                                f"MULTIPASS: {str(multipass_error)[:200]}"
                            )
                
                # Route to other specific strategies if explicitly requested
                elif strategy == ExtractionStrategy.MULTIPASS.value:
                    self.logger.info(f"Using MULTIPASS strategy (explicit) for document_id: {request.document_id}")
                    return await self._run_multipass_extraction(request)
                elif strategy == ExtractionStrategy.AI_ENHANCED.value:
                    self.logger.info(f"Using AI_ENHANCED strategy (explicit) for document_id: {request.document_id}")
                    return await self._run_ai_enhanced_extraction(request)
                elif strategy == ExtractionStrategy.REGEX.value:
                    # Redirect REGEX to UNIFIED for better accuracy
                    self.logger.warning(
                        f"REGEX strategy requested for document {request.document_id}, "
                        "redirecting to UNIFIED for better accuracy."
                    )
                    return await self._run_unified_extraction(request)
                elif strategy == ExtractionStrategy.PAGEBATCH.value:
                    self.logger.info(f"Using PAGEBATCH strategy (explicit) for document_id: {request.document_id}")
                    return await self._run_pagebatch_extraction(request)
                
                # Fallback to legacy hybrid flow (should not reach here)
                # Initialize response tracking
                processing_summary = ProcessingSummary(
                    total_processing_time_ms=0,
                    regex_stage_time_ms=0,
                    ai_enhancement_time_ms=0,
                    entities_found=0,
                    citations_found=0,
                    relationships_found=0,
                    ai_enhancements_applied=0,
                    processing_stages_completed=[]
                )
                
                entities = []
                citations = []
                relationships = []
                warnings = []
                errors = []
                metadata = {"request_id": request_id}
                
                # Determine extraction mode
                extraction_mode = self._determine_extraction_mode(request.options)

                # Stage 1: REGEX Pattern Extraction
                if extraction_mode == ExtractionMode.REGEX_ONLY:
                    # Run regex-only extraction - fast pattern matching without AI
                    self.logger.info(f"Running REGEX_ONLY extraction for document {request.document_id}")
                    entities, citations, regex_time = await self._run_regex_extraction(
                        request.text, request.document_id, request.options
                    )
                    processing_summary.regex_stage_time_ms = regex_time
                    processing_summary.processing_stages_completed.append("regex_extraction")

                    # Skip AI processing for REGEX_ONLY mode
                    self.logger.info(f"REGEX_ONLY extraction completed: {len(entities)} entities, {len(citations)} citations")

                else:
                    # Stage 2: AI Enhancement/Validation (for non-regex modes)
                    # Run AI extraction for AI_ENHANCED and AI_ONLY modes
                    # Calculate document size hint for vLLM optimization
                    document_size_hint = len(request.text) if request.text else 0
                    
                    ai_entities, ai_citations, ai_relationships, ai_time, ai_enhancements = await self._run_ai_enhancement(
                        request.text, entities, citations, request.document_id, request.options,
                        document_size_hint=document_size_hint
                    )
                    
                    # Merge AI results with regex results
                    entities, citations = self._merge_extraction_results(
                        entities, citations, ai_entities, ai_citations
                    )
                    relationships.extend(ai_relationships)
                    processing_summary.ai_enhancement_time_ms = ai_time
                    processing_summary.ai_enhancements_applied = ai_enhancements
                    processing_summary.processing_stages_completed.extend([
                        "ai_validation", "ai_enhancement"
                    ])
                
                # Stage 3: Relationship Extraction (if enabled)
                if request.options and request.options.enable_relationship_extraction:
                    relationship_time_start = time.time()
                    additional_relationships = await self._extract_relationships(
                        entities, citations, request.text, request.document_id
                    )
                    relationships.extend(additional_relationships)
                    relationship_time = int((time.time() - relationship_time_start) * 1000)
                    metadata["relationship_extraction_time_ms"] = relationship_time
                    processing_summary.processing_stages_completed.append("relationship_extraction")
                
                # Stage 4: Confidence Scoring and Validation
                entities, citations, relationships = await self._apply_confidence_scoring(
                    entities, citations, relationships, request.options
                )
                processing_summary.processing_stages_completed.append("confidence_scoring")
                
                # Stage 5: Apply confidence threshold filtering
                if request.options:
                    entities = [e for e in entities if e.confidence_score >= request.options.confidence_threshold]
                    citations = [c for c in citations if c.confidence_score >= request.options.confidence_threshold]
                    relationships = [r for r in relationships if r.confidence_score >= request.options.confidence_threshold]
                
                # Update processing summary
                total_time = int((time.time() - start_time) * 1000)
                processing_summary.total_processing_time_ms = total_time
                processing_summary.entities_found = len(entities)
                processing_summary.citations_found = len(citations)
                processing_summary.relationships_found = len(relationships)
                processing_summary.processing_stages_completed.append("result_compilation")
                
                # Calculate confidence distribution
                processing_summary.confidence_distribution = self._calculate_confidence_distribution(
                    entities + citations + relationships
                )
                
                # Calculate average confidence
                all_items = entities + citations + relationships
                if all_items:
                    processing_summary.avg_confidence_score = sum(
                        item.confidence_score for item in all_items
                    ) / len(all_items)
                
                # Store results if enabled
                if self.settings.store_extraction_results and self._supabase_client:
                    await self._store_extraction_results(
                        request.document_id, entities, citations, relationships, processing_summary
                    )
                
                # Update statistics
                self._update_extraction_stats(True, total_time)
                
                # Create response
                response = ExtractionResponse(
                    document_id=request.document_id,
                    processing_summary=processing_summary,
                    entities=entities,
                    citations=citations,
                    relationships=relationships,
                    metadata=metadata,
                    warnings=warnings,
                    errors=errors,
                    request_id=request_id,
                    success=True
                )
                
                # Store in cache for future requests
                await cache.set(
                    text=request.text,
                    extraction_mode=extraction_mode.value,
                    value=response,
                    strategy=strategy,
                    options=request.options.dict() if request.options else None,
                    ttl=3600  # 1 hour TTL
                )
                
                self.logger.info(
                    f"Extraction completed successfully for document_id: {request.document_id} (cached)",
                    extra={
                        "event_type": "extraction_complete",
                        "document_id": request.document_id,
                        "request_id": request_id,
                        "processing_time_ms": total_time,
                        "entities_found": len(entities),
                        "citations_found": len(citations),
                        "relationships_found": len(relationships),
                        "strategy": strategy,
                        "cached": True
                    }
                )
                
                return response
                
            except Exception as e:
                total_time = int((time.time() - start_time) * 1000)
                self._update_extraction_stats(False, total_time)
                
                self.logger.error(
                    f"Extraction failed for document_id: {request.document_id}",
                    extra={
                        "event_type": "extraction_error",
                        "document_id": request.document_id,
                        "request_id": request_id,
                        "error": str(e),
                        "processing_time_ms": total_time
                    },
                    exc_info=True
                )
                
                raise ExtractionError(f"Extraction failed: {str(e)}") from e
    
    async def _run_multipass_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run multipass extraction strategy with 7 progressive extraction passes.
        
        This strategy runs 7 specialized passes with progressive confidence refinement,
        optimized for maximum recall in comprehensive legal document analysis.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Extraction results from multipass strategy
        """
        start_time = time.time()
        request_id = f"multipass_{int(start_time * 1000)}"
        document_chars = len(request.text)
        
        try:
            # Ensure MultiPassExtractor is available
            if not self._multi_pass_extractor:
                if self._throttled_vllm_client or self._vllm_client:
                    # Use throttled client if available
                    client = self._throttled_vllm_client or self._vllm_client
                    self._multi_pass_extractor = MultiPassExtractor(client, use_entity_registry=False)
                    self.logger.info("Initialized MultiPassExtractor on-demand with throttled client")
                else:
                    raise ExtractionError("MultiPassExtractor requires vLLM client")
            
            # Check if document needs smart chunking for large documents
            if not self._smart_chunker:
                self._smart_chunker = SmartChunker(self.runtime_config)
            
            if self._smart_chunker.should_use_smart_chunking(request.text):
                self.logger.info(
                    f"Document size ({document_chars} chars) exceeds smart chunking threshold. "
                    f"Using smart chunked multipass extraction."
                )
                return await self._run_smart_chunked_multipass_extraction(request)
            elif document_chars > self.runtime_config.chunking.max_chunk_size:
                self.logger.info(
                    f"Document size ({document_chars} chars) exceeds standard threshold. "
                    f"Using chunked multipass extraction."
                )
                return await self._run_chunked_multipass_extraction(request)
            
            # Run 7-pass extraction on full document
            entities_matches, metrics = await self._multi_pass_extractor.extract_multi_pass(
                chunk_id=request.document_id,
                chunk_content=request.text,
                document_id=request.document_id,
                chunk_index=0,
                whole_document=request.text,
                selected_passes=None,  # Run all 7 passes
                parallel_execution=True
            )
            
            # Convert EntityMatch objects to Entity/Citation objects
            entities = []
            citations = []
            
            # Entity type mapping from AI-generated types to valid EntityType enum values
            entity_type_mapping = {
                # Organizational entities
                "ORGANIZATION": "CORPORATION",  # Map generic organization to corporation
                "COMPANY": "CORPORATION",
                "CORP": "CORPORATION", 
                "CORPORATION": "CORPORATION",
                "LLC": "LLC",
                "PARTNERSHIP": "PARTNERSHIP",
                "NONPROFIT": "NONPROFIT",
                "GOVERNMENT_ENTITY": "GOVERNMENT_ENTITY",
                "LAW_FIRM": "LAW_FIRM",
                
                # People and parties
                "PARTY": "PARTY",
                "PERSON": "PARTY",  # Map generic person to party for legal context
                "ATTORNEY": "ATTORNEY",
                "PLAINTIFF": "PLAINTIFF",
                "DEFENDANT": "DEFENDANT",
                "JUDGE": "JUDGE",
                
                # Courts and judicial
                "COURT": "COURT",
                "JUSTICE": "JUDGE",  # Map justice to judge
                "MAGISTRATE": "MAGISTRATE",
                
                # Documents and legal concepts
                "DOCUMENT": "DOCUMENT",
                "LEGAL_CONCEPT": "LEGAL_CONCEPT",
                "DOCTRINE": "LEGAL_DOCTRINE",
                "STANDARD": "LEGAL_STANDARD",
                "PROCEDURE": "PROCEDURAL_RULE",
                
                # Dates and temporal
                "DATE": "DATE",
                "DEADLINE": "DEADLINE", 
                "TIME_PERIOD": "DATE",  # Map time period to date
                "FILING_DATE": "FILING_DATE",
                
                # Other common mappings
                "OTHER": "LEGAL_CONCEPT"  # Default fallback for "other" type
            }
            
            # Entity subtype mapping based on entity type
            entity_subtype_mapping = {
                "CORPORATION": "business_entity",
                "LLC": "business_entity", 
                "PARTNERSHIP": "business_entity",
                "NONPROFIT": "organization",
                "GOVERNMENT_ENTITY": "government",
                "LAW_FIRM": "legal_organization",
                "PARTY": "legal_party",
                "ATTORNEY": "legal_professional",
                "PLAINTIFF": "legal_party",
                "DEFENDANT": "legal_party",
                "JUDGE": "judicial_officer",
                "COURT": "judicial_institution",
                "MAGISTRATE": "judicial_officer",
                "DOCUMENT": "legal_document",
                "LEGAL_CONCEPT": "legal_principle",
                "LEGAL_DOCTRINE": "legal_principle",
                "LEGAL_STANDARD": "legal_test",
                "PROCEDURAL_RULE": "court_procedure",
                "DATE": "temporal_reference",
                "DEADLINE": "temporal_reference",
                "FILING_DATE": "procedural_date"
            }
            
            for match in entities_matches:
                # Normalize entity type
                raw_entity_type = match.entity_type.upper() if isinstance(match.entity_type, str) else str(match.entity_type).upper()
                
                # Map AI-generated type to valid EntityType enum value
                mapped_entity_type = entity_type_mapping.get(raw_entity_type, raw_entity_type)
                
                # Validate that mapped type exists in EntityType enum
                from ..models.entities import EntityType
                try:
                    entity_type_enum = EntityType(mapped_entity_type)
                except ValueError:
                    # If still invalid, use a default valid type
                    self.logger.warning(f"Invalid entity type '{mapped_entity_type}' from AI output '{raw_entity_type}', using LEGAL_CONCEPT as fallback")
                    entity_type_enum = EntityType.LEGAL_CONCEPT
                    mapped_entity_type = "LEGAL_CONCEPT"
                
                # Generate entity subtype
                entity_subtype = entity_subtype_mapping.get(mapped_entity_type, "unspecified")
                
                # Determine if this is a citation based on entity type
                is_citation = raw_entity_type in [
                    "CASE_CITATION", "STATUTE_CITATION", "REGULATION_CITATION", 
                    "DOCKET_NUMBER", "CFR_CITATION", "FEDERAL_REGISTER",
                    "ADMINISTRATIVE_CODE", "EXECUTIVE_ORDER"
                ] or "citation" in raw_entity_type.lower() or "docket" in raw_entity_type.lower()
                
                # Extract pass information from metadata
                pass_number = 1  # Default
                if match.metadata:
                    # MultiPassExtractor stores pass number as 'extraction_pass'
                    pass_number = match.metadata.get('extraction_pass', match.metadata.get('pass', 1))
                
                if is_citation:
                    from ..models.entities import TextPosition, CitationType, CitationComponents
                    # Map AI-generated citation types to valid CitationType enum values
                    citation_type_mapping = {
                        "CASE_CITATION": CitationType.CASE_CITATION,
                        "STATUTE_CITATION": CitationType.STATUTE_CITATION,
                        "REGULATION_CITATION": CitationType.REGULATION_CITATION,
                        "DOCKET_NUMBER": CitationType.CASE_CITATION,  # Docket numbers are case-related
                        "CFR_CITATION": CitationType.CFR_CITATION,
                        "FEDERAL_REGISTER": CitationType.FEDERAL_REGISTER_CITATION,
                        "ADMINISTRATIVE_CODE": CitationType.ADMINISTRATIVE_CODE_CITATION,
                        "EXECUTIVE_ORDER": CitationType.EXECUTIVE_ORDER_CITATION
                    }
                    
                    # Get the appropriate citation type
                    citation_type = citation_type_mapping.get(raw_entity_type, CitationType.CASE_CITATION)
                    
                    # Store metadata in components.additional_components
                    metadata_dict = match.metadata or {}
                    metadata_dict.update({'pass': str(pass_number), 'mapped_from': raw_entity_type})
                    
                    citation = Citation(
                        original_text=match.text,
                        cleaned_citation=match.text,  # Required field - updated field name
                        citation_type=citation_type,
                        position=TextPosition(
                            start=match.start_position,
                            end=match.end_position
                        ),
                        confidence_score=min(0.3 + (pass_number * 0.1), 0.95),  # Progressive confidence
                        extraction_method=ExtractionMethod.AI_DISCOVERED,
                        bluebook_compliant=False,  # Required field - default to False for AI-discovered
                        components=CitationComponents(
                            additional_components=metadata_dict
                        )
                    )
                    citations.append(citation)
                else:
                    from ..models.entities import TextPosition, EntityAttributes
                    # Store metadata in attributes.additional_attributes
                    metadata_dict = match.metadata or {}
                    metadata_dict.update({
                        'pass': str(pass_number),
                        'mapped_from': raw_entity_type,
                        'original_ai_type': raw_entity_type
                    })
                    
                    entity = Entity(
                        text=match.text,
                        cleaned_text=match.text,  # Required field
                        entity_type=entity_type_enum,  # Use the validated enum value
                        entity_subtype=entity_subtype,  # Required field - now provided
                        position=TextPosition(
                            start=match.start_position,
                            end=match.end_position
                        ),
                        confidence_score=min(0.3 + (pass_number * 0.1), 0.95),  # Progressive confidence
                        extraction_method=ExtractionMethod.AI_DISCOVERED,
                        context_snippet=match.context,  # Updated field name
                        attributes=EntityAttributes(
                            additional_attributes=metadata_dict
                        )
                    )
                    entities.append(entity)
            
            # Calculate processing summary
            processing_time = int((time.time() - start_time) * 1000)
            processing_summary = ProcessingSummary(
                total_processing_time_ms=processing_time,
                regex_stage_time_ms=0,  # No separate regex stage in multipass
                ai_enhancement_time_ms=processing_time,  # All time is AI processing
                entities_found=len(entities),
                citations_found=len(citations),
                relationships_found=0,  # Relationships handled separately if needed
                ai_enhancements_applied=len(entities_matches),
                processing_stages_completed=[
                    f"multipass_{i+1}" for i in range(metrics.successful_passes)
                ],
                confidence_distribution=self._calculate_confidence_distribution(entities + citations),
                avg_confidence_score=sum(e.confidence_score for e in entities + citations) / max(1, len(entities + citations))
            )
            
            # Create response
            response = ExtractionResponse(
                document_id=request.document_id,
                processing_summary=processing_summary,
                entities=entities,
                citations=citations,
                relationships=[],
                metadata={
                    "request_id": request_id,
                    "strategy": ExtractionStrategy.MULTIPASS.value,
                    "passes_executed": metrics.total_passes_executed,
                    "successful_passes": metrics.successful_passes,
                    "tokens_used": metrics.total_tokens_used,
                    "duplicates_removed": metrics.duplicates_removed
                },
                warnings=[],
                errors=[],
                request_id=request_id,
                success=True
            )
            
            # Cache the response
            cache = get_response_cache()
            await cache.set(
                text=request.text,
                extraction_mode="multipass",
                value=response,
                strategy=ExtractionStrategy.MULTIPASS.value,
                options=request.options.dict() if request.options else None,
                ttl=3600
            )
            
            # Track confidence distribution metrics
            confidence_dist = self._calculate_confidence_distribution(entities + citations)
            avg_confidence = sum(e.confidence_score for e in entities + citations) / max(1, len(entities + citations))
            
            self.logger.info(
                f"Multipass extraction completed for document_id: {request.document_id}",
                extra={
                    "event_type": "multipass_extraction_complete",
                    "document_id": request.document_id,
                    "entities_found": len(entities),
                    "citations_found": len(citations),
                    "passes_executed": metrics.total_passes_executed,
                    "processing_time_ms": processing_time,
                    "avg_confidence": avg_confidence,
                    "confidence_distribution": confidence_dist,
                    "performance_metrics": {
                        "entities_per_pass": len(entities) / max(1, metrics.successful_passes),
                        "confidence_range": f"{min(e.confidence_score for e in entities + citations) if entities + citations else 0:.2f}-{max(e.confidence_score for e in entities + citations) if entities + citations else 0:.2f}"
                    }
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Multipass extraction failed: {str(e)}", exc_info=True)
            raise ExtractionError(f"Multipass extraction failed: {str(e)}") from e
    
    async def _run_chunked_multipass_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run multipass extraction on chunked document.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Extraction results from chunked multipass strategy
        """
        start_time = time.time()
        request_id = f"chunked_multipass_{int(start_time * 1000)}"
        
        # Use SmartChunker for multipass
        if not self._smart_chunker:
            self._smart_chunker = SmartChunker(self.runtime_config)
        
        chunks = self._smart_chunker.chunk_document(
            request.text,
            strategy="legal"  # Legal chunking for multipass
        )
        
        self.logger.info(f"Processing {len(chunks)} chunks with multipass extraction")
        
        all_entities = []
        all_citations = []
        total_tokens = 0
        
        for i, chunk in enumerate(chunks):
            self.logger.info(
                f"Processing chunk {i+1}/{len(chunks)} with multipass "
                f"(chars {chunk.start_pos}-{chunk.end_pos})"
            )
            
            try:
                # Run multipass on this chunk
                entities_matches, metrics = await self._multi_pass_extractor.extract_multi_pass(
                    chunk_id=f"{request.document_id}_chunk_{i}",
                    chunk_content=chunk.text,
                    document_id=request.document_id,
                    chunk_index=i,
                    whole_document=request.text,  # Still provide full document for context
                    selected_passes=None,
                    parallel_execution=True
                )
                
                # Convert and adjust positions - Use same logic as main multipass extraction
                entity_type_mapping = {
                    "ORGANIZATION": "CORPORATION", "COMPANY": "CORPORATION", "CORP": "CORPORATION",
                    "CORPORATION": "CORPORATION", "LLC": "LLC", "PARTNERSHIP": "PARTNERSHIP",
                    "NONPROFIT": "NONPROFIT", "GOVERNMENT_ENTITY": "GOVERNMENT_ENTITY",
                    "LAW_FIRM": "LAW_FIRM", "PARTY": "PARTY", "PERSON": "PARTY",
                    "ATTORNEY": "ATTORNEY", "PLAINTIFF": "PLAINTIFF", "DEFENDANT": "DEFENDANT",
                    "JUDGE": "JUDGE", "COURT": "COURT", "JUSTICE": "JUDGE", "MAGISTRATE": "MAGISTRATE",
                    "DOCUMENT": "DOCUMENT", "LEGAL_CONCEPT": "LEGAL_CONCEPT", "DOCTRINE": "LEGAL_DOCTRINE",
                    "STANDARD": "LEGAL_STANDARD", "PROCEDURE": "PROCEDURAL_RULE",
                    "DATE": "DATE", "DEADLINE": "DEADLINE", "TIME_PERIOD": "DATE", "FILING_DATE": "FILING_DATE",
                    "OTHER": "LEGAL_CONCEPT"
                }
                entity_subtype_mapping = {
                    "CORPORATION": "business_entity", "LLC": "business_entity", "PARTNERSHIP": "business_entity",
                    "NONPROFIT": "organization", "GOVERNMENT_ENTITY": "government", "LAW_FIRM": "legal_organization",
                    "PARTY": "legal_party", "ATTORNEY": "legal_professional", "PLAINTIFF": "legal_party",
                    "DEFENDANT": "legal_party", "JUDGE": "judicial_officer", "COURT": "judicial_institution",
                    "MAGISTRATE": "judicial_officer", "DOCUMENT": "legal_document", "LEGAL_CONCEPT": "legal_principle",
                    "LEGAL_DOCTRINE": "legal_principle", "LEGAL_STANDARD": "legal_test",
                    "PROCEDURAL_RULE": "court_procedure", "DATE": "temporal_reference",
                    "DEADLINE": "temporal_reference", "FILING_DATE": "procedural_date"
                }
                
                for match in entities_matches:
                    # Normalize entity type
                    raw_entity_type = match.entity_type.upper() if isinstance(match.entity_type, str) else str(match.entity_type).upper()
                    
                    # Map AI-generated type to valid EntityType enum value
                    mapped_entity_type = entity_type_mapping.get(raw_entity_type, raw_entity_type)
                    
                    # Validate that mapped type exists in EntityType enum
                    from ..models.entities import EntityType
                    try:
                        entity_type_enum = EntityType(mapped_entity_type)
                    except ValueError:
                        # If still invalid, use a default valid type
                        self.logger.warning(f"Invalid entity type '{mapped_entity_type}' from AI output '{raw_entity_type}', using LEGAL_CONCEPT as fallback")
                        entity_type_enum = EntityType.LEGAL_CONCEPT
                        mapped_entity_type = "LEGAL_CONCEPT"
                    
                    # Generate entity subtype
                    entity_subtype = entity_subtype_mapping.get(mapped_entity_type, "unspecified")
                    
                    # Determine if this is a citation based on entity type
                    is_citation = raw_entity_type in [
                        "CASE_CITATION", "STATUTE_CITATION", "REGULATION_CITATION", 
                        "DOCKET_NUMBER", "CFR_CITATION", "FEDERAL_REGISTER",
                        "ADMINISTRATIVE_CODE", "EXECUTIVE_ORDER"
                    ] or "citation" in raw_entity_type.lower() or "docket" in raw_entity_type.lower()
                    
                    pass_number = match.metadata.get('extraction_pass', 1) if match.metadata else 1
                    
                    if is_citation:
                        from ..models.entities import TextPosition, CitationType
                        # Map AI-generated citation types to valid CitationType enum values
                        citation_type_mapping = {
                            "CASE_CITATION": CitationType.CASE_CITATION,
                            "STATUTE_CITATION": CitationType.STATUTE_CITATION,
                            "REGULATION_CITATION": CitationType.REGULATION_CITATION,
                            "DOCKET_NUMBER": CitationType.CASE_CITATION,  # Docket numbers are case-related
                            "CFR_CITATION": CitationType.CFR_CITATION,
                            "FEDERAL_REGISTER": CitationType.FEDERAL_REGISTER_CITATION,
                            "ADMINISTRATIVE_CODE": CitationType.ADMINISTRATIVE_CODE_CITATION,
                            "EXECUTIVE_ORDER": CitationType.EXECUTIVE_ORDER_CITATION
                        }
                        
                        # Get the appropriate citation type
                        citation_type = citation_type_mapping.get(raw_entity_type, CitationType.CASE_CITATION)
                        
                        from ..models.entities import CitationComponents
                        # Store metadata in components.additional_components
                        metadata_dict = match.metadata or {}
                        metadata_dict.update({'pass': str(pass_number), 'chunk': str(i), 'mapped_from': raw_entity_type})
                        
                        citation = Citation(
                            original_text=match.text,
                            cleaned_citation=match.text,  # Updated field name
                            citation_type=citation_type,
                            position=TextPosition(
                                start=match.start_position + chunk.start_pos,
                                end=match.end_position + chunk.start_pos
                            ),
                            confidence_score=min(0.3 + (pass_number * 0.1), 0.95),
                            extraction_method=ExtractionMethod.AI_DISCOVERED,
                            bluebook_compliant=False,  # Required field
                            components=CitationComponents(
                                additional_components=metadata_dict
                            )
                        )
                        all_citations.append(citation)
                    else:
                        from ..models.entities import TextPosition, EntityAttributes
                        # Store metadata in attributes.additional_attributes
                        metadata_dict = match.metadata or {}
                        metadata_dict.update({
                            'pass': str(pass_number),
                            'chunk': str(i),
                            'mapped_from': raw_entity_type,
                            'original_ai_type': raw_entity_type
                        })
                        
                        entity = Entity(
                            text=match.text,
                            cleaned_text=match.text,
                            entity_type=entity_type_enum,  # Use the validated enum value
                            entity_subtype=entity_subtype,  # Required field - now provided
                            position=TextPosition(
                                start=match.start_position + chunk.start_pos,
                                end=match.end_position + chunk.start_pos
                            ),
                            confidence_score=min(0.3 + (pass_number * 0.1), 0.95),
                            extraction_method=ExtractionMethod.AI_DISCOVERED,
                            context_snippet=match.context,  # Updated field name
                            attributes=EntityAttributes(
                                additional_attributes=metadata_dict
                            )
                        )
                        all_entities.append(entity)
                
                total_tokens += metrics.total_tokens_used
                
            except Exception as e:
                self.logger.error(f"Failed to process chunk {i+1} with multipass: {str(e)}")
                continue
        
        # Deduplicate
        unique_entities = self._deduplicate_entities(all_entities)
        unique_citations = self._deduplicate_citations(all_citations)
        
        # Calculate processing summary
        processing_time = int((time.time() - start_time) * 1000)
        processing_summary = ProcessingSummary(
            total_processing_time_ms=processing_time,
            regex_stage_time_ms=0,
            ai_enhancement_time_ms=processing_time,
            entities_found=len(unique_entities),
            citations_found=len(unique_citations),
            relationships_found=0,
            ai_enhancements_applied=len(unique_entities) + len(unique_citations),
            processing_stages_completed=[f"chunked_multipass_{len(chunks)}_chunks"],
            confidence_distribution=self._calculate_confidence_distribution(unique_entities + unique_citations),
            avg_confidence_score=sum(e.confidence_score for e in unique_entities + unique_citations) / max(1, len(unique_entities + unique_citations))
        )
        
        # Create response
        response = ExtractionResponse(
            document_id=request.document_id,
            processing_summary=processing_summary,
            entities=unique_entities,
            citations=unique_citations,
            relationships=[],
            metadata={
                "request_id": request_id,
                "strategy": ExtractionStrategy.MULTIPASS.value,
                "chunked": True,
                "chunks_processed": len(chunks),
                "tokens_used": total_tokens
            },
            warnings=[],
            errors=[],
            request_id=request_id,
            success=True
        )
        
        # Cache the response
        cache = get_response_cache()
        await cache.set(
            text=request.text,
            extraction_mode="multipass",
            value=response,
            strategy=ExtractionStrategy.MULTIPASS.value,
            options=request.options.dict() if request.options else None,
            ttl=3600
        )
        
        self.logger.info(
            f"Chunked multipass extraction completed: {len(unique_entities)} entities, "
            f"{len(unique_citations)} citations from {len(chunks)} chunks"
        )
        
        return response
    
    async def _run_smart_chunked_multipass_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run multipass extraction on very large documents using smart chunking.
        
        This method is specifically for documents >50K characters, using the formula:
        (doc_chars / context_window) * 0.8 to determine optimal chunk sizes.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Extraction results from smart chunked multipass strategy
        """
        start_time = time.time()
        request_id = f"smart_chunked_multipass_{int(start_time * 1000)}"
        
        # Use SmartChunker with smart_chunk_document for large documents
        if not self._smart_chunker:
            self._smart_chunker = SmartChunker(self.runtime_config)
        
        # Use the smart chunking method for documents >50K
        chunks = self._smart_chunker.smart_chunk_document(
            request.text,
            strategy=ChunkingStrategy.LEGAL_AWARE,  # Use legal-aware for multipass
            document_type=self._smart_chunker.detect_document_type(request.text)
        )
        
        self.logger.info(f"Smart chunking: Processing {len(chunks)} optimized chunks with multipass extraction")
        
        all_entities = []
        all_citations = []
        total_tokens = 0
        
        for i, chunk in enumerate(chunks):
            self.logger.info(
                f"Processing smart chunk {i+1}/{len(chunks)} with multipass "
                f"(size: {len(chunk.text):,} chars, overlap: {chunk.metadata.get('overlap_before', 0)} chars)"
            )
            
            try:
                # Run multipass on this chunk
                entities_matches, metrics = await self._multi_pass_extractor.extract_multi_pass(
                    chunk_id=f"{request.document_id}_smart_chunk_{i}",
                    chunk_content=chunk.text,
                    document_id=request.document_id,
                    chunk_index=i,
                    whole_document=request.text,  # Still provide full document for context
                    selected_passes=None,
                    parallel_execution=True
                )
                
                # Process entities and citations (same as regular chunked method)
                # ... [entity processing logic same as _run_chunked_multipass_extraction]
                
                # Convert and adjust positions - Use same logic as main multipass extraction
                entity_type_mapping = {
                    "ORGANIZATION": "CORPORATION", "COMPANY": "CORPORATION", "CORP": "CORPORATION",
                    "CORPORATION": "CORPORATION", "LLC": "LLC", "PARTNERSHIP": "PARTNERSHIP",
                    "NONPROFIT": "NONPROFIT", "GOVERNMENT_ENTITY": "GOVERNMENT_ENTITY",
                    "LAW_FIRM": "LAW_FIRM", "PARTY": "PARTY", "PERSON": "PARTY",
                    "ATTORNEY": "ATTORNEY", "PLAINTIFF": "PLAINTIFF", "DEFENDANT": "DEFENDANT",
                    "JUDGE": "JUDGE", "COURT": "COURT", "JUSTICE": "JUDGE", "MAGISTRATE": "MAGISTRATE",
                    "DOCUMENT": "DOCUMENT", "LEGAL_CONCEPT": "LEGAL_CONCEPT", "DOCTRINE": "LEGAL_DOCTRINE",
                    "STANDARD": "LEGAL_STANDARD", "PROCEDURE": "PROCEDURAL_RULE",
                    "DATE": "DATE", "DEADLINE": "DEADLINE", "TIME_PERIOD": "DATE", "FILING_DATE": "FILING_DATE",
                    "OTHER": "LEGAL_CONCEPT"
                }
                entity_subtype_mapping = {
                    "CORPORATION": "business_entity", "LLC": "business_entity", "PARTNERSHIP": "business_entity",
                    "NONPROFIT": "organization", "GOVERNMENT_ENTITY": "government", "LAW_FIRM": "legal_organization",
                    "PARTY": "legal_party", "ATTORNEY": "legal_professional", "PLAINTIFF": "legal_party",
                    "DEFENDANT": "legal_party", "JUDGE": "judicial_officer", "COURT": "judicial_institution",
                    "MAGISTRATE": "judicial_officer", "DOCUMENT": "legal_document", "LEGAL_CONCEPT": "legal_principle",
                    "LEGAL_DOCTRINE": "legal_principle", "LEGAL_STANDARD": "legal_test",
                    "PROCEDURAL_RULE": "court_procedure", "DATE": "temporal_reference",
                    "DEADLINE": "temporal_reference", "FILING_DATE": "procedural_date"
                }
                
                for match in entities_matches:
                    # Process entities (same logic as regular chunked method)
                    raw_entity_type = match.entity_type.upper() if isinstance(match.entity_type, str) else str(match.entity_type).upper()
                    mapped_entity_type = entity_type_mapping.get(raw_entity_type, raw_entity_type)
                    
                    from ..models.entities import EntityType, TextPosition, Citation, CitationType
                    try:
                        entity_type_enum = EntityType(mapped_entity_type)
                    except ValueError:
                        self.logger.warning(f"Invalid entity type '{mapped_entity_type}', using LEGAL_CONCEPT")
                        entity_type_enum = EntityType.LEGAL_CONCEPT
                        mapped_entity_type = "LEGAL_CONCEPT"
                    
                    entity_subtype = entity_subtype_mapping.get(mapped_entity_type, "unspecified")
                    
                    is_citation = raw_entity_type in [
                        "CASE_CITATION", "STATUTE_CITATION", "REGULATION_CITATION", 
                        "DOCKET_NUMBER", "CFR_CITATION", "FEDERAL_REGISTER",
                        "ADMINISTRATIVE_CODE", "EXECUTIVE_ORDER"
                    ] or "citation" in raw_entity_type.lower() or "docket" in raw_entity_type.lower()
                    
                    pass_number = match.metadata.get('extraction_pass', 1) if match.metadata else 1
                    
                    if is_citation:
                        citation_type_mapping = {
                            "CASE_CITATION": CitationType.CASE_CITATION,
                            "STATUTE_CITATION": CitationType.STATUTE_CITATION,
                            "REGULATION_CITATION": CitationType.REGULATION_CITATION,
                            "DOCKET_NUMBER": CitationType.CASE_CITATION,
                            "CFR_CITATION": CitationType.CFR_CITATION,
                            "FEDERAL_REGISTER": CitationType.FEDERAL_REGISTER_CITATION,
                            "ADMINISTRATIVE_CODE": CitationType.ADMINISTRATIVE_CODE_CITATION,
                            "EXECUTIVE_ORDER": CitationType.EXECUTIVE_ORDER_CITATION
                        }
                        
                        citation_type = citation_type_mapping.get(raw_entity_type, CitationType.CASE_CITATION)
                        
                        from ..models.entities import CitationComponents
                        # Store metadata in components.additional_components
                        metadata_dict = match.metadata or {}
                        metadata_dict.update({
                            'pass': str(pass_number),
                            'smart_chunk': str(i),
                            'chunk_size': str(len(chunk.text)),
                            'overlap': str(chunk.metadata.get('overlap_before', 0))
                        })
                        
                        citation = Citation(
                            original_text=match.text,
                            cleaned_citation=match.text,
                            citation_type=citation_type,
                            position=TextPosition(
                                start=match.start_position + chunk.start_pos,
                                end=match.end_position + chunk.start_pos
                            ),
                            confidence_score=min(0.3 + (pass_number * 0.1), 0.95),
                            extraction_method=ExtractionMethod.AI_DISCOVERED,
                            bluebook_compliant=False,
                            components=CitationComponents(
                                additional_components=metadata_dict
                            )
                        )
                        all_citations.append(citation)
                    else:
                        from ..models.entities import EntityAttributes
                        # Store metadata in attributes.additional_attributes
                        metadata_dict = match.metadata or {}
                        metadata_dict.update({
                            'pass': str(pass_number),
                            'smart_chunk': str(i),
                            'chunk_size': str(len(chunk.text)),
                            'overlap': str(chunk.metadata.get('overlap_before', 0))
                        })
                        
                        entity = Entity(
                            text=match.text,
                            cleaned_text=match.text,
                            entity_type=entity_type_enum,
                            entity_subtype=entity_subtype,
                            position=TextPosition(
                                start=match.start_position + chunk.start_pos,
                                end=match.end_position + chunk.start_pos
                            ),
                            confidence_score=min(0.3 + (pass_number * 0.1), 0.95),
                            extraction_method=ExtractionMethod.AI_DISCOVERED,
                            context_snippet=match.context,
                            attributes=EntityAttributes(
                                additional_attributes=metadata_dict
                            )
                        )
                        all_entities.append(entity)
                
                total_tokens += metrics.total_tokens_used
                
            except Exception as e:
                self.logger.error(f"Failed to process smart chunk {i+1} with multipass: {str(e)}")
                continue
        
        # Enhanced deduplication for overlapping chunks
        unique_entities = self._deduplicate_entities_with_overlap(all_entities)
        unique_citations = self._deduplicate_citations_with_overlap(all_citations)
        
        # Calculate processing summary
        processing_time = int((time.time() - start_time) * 1000)
        processing_summary = ProcessingSummary(
            total_processing_time_ms=processing_time,
            regex_stage_time_ms=0,
            ai_enhancement_time_ms=processing_time,
            entities_found=len(unique_entities),
            citations_found=len(unique_citations),
            relationships_found=0,
            ai_enhancements_applied=len(unique_entities) + len(unique_citations),
            processing_stages_completed=[f"smart_chunked_multipass_{len(chunks)}_chunks"],
            confidence_distribution=self._calculate_confidence_distribution(unique_entities + unique_citations),
            avg_confidence_score=sum(e.confidence_score for e in unique_entities + unique_citations) / max(1, len(unique_entities + unique_citations))
        )
        
        # Create response
        response = ExtractionResponse(
            document_id=request.document_id,
            processing_summary=processing_summary,
            entities=unique_entities,
            citations=unique_citations,
            relationships=[],
            metadata={
                "request_id": request_id,
                "strategy": ExtractionStrategy.MULTIPASS.value,
                "smart_chunked": True,
                "chunks_processed": len(chunks),
                "document_size": len(request.text),
                "avg_chunk_size": sum(len(c.text) for c in chunks) / len(chunks),
                "tokens_used": total_tokens
            },
            warnings=[],
            errors=[],
            request_id=request_id,
            success=True
        )
        
        # Cache the response
        cache = get_response_cache()
        await cache.set(
            text=request.text,
            extraction_mode="smart_multipass",
            value=response,
            strategy=ExtractionStrategy.MULTIPASS.value,
            options=request.options.dict() if request.options else None,
            ttl=3600
        )
        
        self.logger.info(
            f"Smart chunked multipass extraction completed: {len(unique_entities)} entities, "
            f"{len(unique_citations)} citations from {len(chunks)} smart chunks"
        )
        
        return response
    
    async def _run_ai_enhanced_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run AI-enhanced extraction strategy with deep NLP analysis.
        
        This strategy skips regex extraction and goes directly to AI with enhanced
        confidence scoring using context, linguistic, and semantic weights.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Extraction results from AI-enhanced strategy
        """
        start_time = time.time()
        request_id = f"ai_enhanced_{int(start_time * 1000)}"
        document_chars = len(request.text)
        
        try:
            # Ensure AI enhancer is available
            if not self._ai_enhancer or not self._vllm_client:
                raise ExtractionError("AI-enhanced strategy requires AI enhancer and vLLM client")
            
            # Check if document needs smart chunking for large documents
            if not self._smart_chunker:
                self._smart_chunker = SmartChunker(self.runtime_config)
            
            if self._smart_chunker.should_use_smart_chunking(request.text):
                self.logger.info(
                    f"Document size ({document_chars} chars) exceeds smart chunking threshold. "
                    f"Using smart chunked AI-enhanced extraction."
                )
                return await self._run_smart_chunked_ai_enhanced_extraction(request)
            elif document_chars > self.runtime_config.chunking.max_chunk_size:
                self.logger.info(
                    f"Document size ({document_chars} chars) exceeds standard threshold. "
                    f"Using chunked AI-enhanced extraction."
                )
                return await self._run_chunked_ai_enhanced_extraction(request)
            
            # Skip regex, go directly to AI extraction with enhanced features
            # Use AI discovery to find all entities in a single deep-analysis pass
            chunking_config = self._get_chunking_config()
            self.logger.info(f"🔍 DEBUG extraction_service: Calling discover_entities_compatibility with text length: {len(request.text)}")
            
            ai_entities, ai_citations = await self._ai_enhancer.discover_entities_compatibility(
                request.text,  # document_text (positional)
                [],  # existing_entities_and_citations (positional)
                strategy=ExtractionStrategy.AI_ENHANCED.value,
                chunking_config=chunking_config
            )
            
            # DEBUG: Log what we got back
            self.logger.info(f"🔍 DEBUG extraction_service: Got back {len(ai_entities)} entities, {len(ai_citations)} citations")
            if ai_entities:
                self.logger.info(f"🔍 DEBUG extraction_service: First 5 entities: {[e.text for e in ai_entities[:5]]}")
            else:
                self.logger.error(f"❌ DEBUG extraction_service: NO ENTITIES returned from discover_entities_compatibility")
            
            # Apply AI-enhanced confidence scoring using the new method
            for entity in ai_entities:
                entity.confidence_score = self._calculate_strategy_confidence(
                    entity, ExtractionStrategy.AI_ENHANCED.value
                )
                # Set extraction method to indicate AI-enhanced processing
                entity.extraction_method = ExtractionMethod.AI_DISCOVERED
                entity.ai_enhancements.append("ai_strategy:enhanced_nlp")
            
            for citation in ai_citations:
                citation.confidence_score = self._calculate_strategy_confidence(
                    citation, ExtractionStrategy.AI_ENHANCED.value
                )
                citation.extraction_method = ExtractionMethod.AI_DISCOVERED
                citation.ai_enhancements.append("ai_strategy:enhanced_nlp")
            
            # Apply strategy-specific filtering
            ai_entities, ai_citations = self._apply_strategy_filters(
                ai_entities, ai_citations, 
                ExtractionStrategy.AI_ENHANCED.value
            )
            
            # Extract relationships if enabled
            relationships = []
            if request.options and request.options.enable_relationship_extraction:
                relationships = await self._ai_enhancer.extract_relationships(
                    ai_entities, ai_citations, request.text,
                    strategy=ExtractionStrategy.AI_ENHANCED.value
                )
            
            # Calculate processing summary
            processing_time = int((time.time() - start_time) * 1000)
            processing_summary = ProcessingSummary(
                total_processing_time_ms=processing_time,
                regex_stage_time_ms=0,  # No regex stage
                ai_enhancement_time_ms=processing_time,  # All AI processing
                entities_found=len(ai_entities),
                citations_found=len(ai_citations),
                relationships_found=len(relationships),
                ai_enhancements_applied=len(ai_entities) + len(ai_citations),
                processing_stages_completed=["ai_deep_analysis", "nlp_enhancement", "confidence_scoring"],
                confidence_distribution=self._calculate_confidence_distribution(ai_entities + ai_citations + relationships),
                avg_confidence_score=sum(e.confidence_score for e in ai_entities + ai_citations) / max(1, len(ai_entities + ai_citations))
            )
            
            # Create response
            response = ExtractionResponse(
                document_id=request.document_id,
                processing_summary=processing_summary,
                entities=ai_entities,
                citations=ai_citations,
                relationships=relationships,
                metadata={
                    "request_id": request_id,
                    "strategy": ExtractionStrategy.AI_ENHANCED.value,
                    "nlp_features": ["coreference_resolution", "semantic_similarity", "context_analysis"]
                },
                warnings=[],
                errors=[],
                request_id=request_id,
                success=True
            )
            
            # Cache the response
            cache = get_response_cache()
            await cache.set(
                text=request.text,
                extraction_mode="ai_enhanced",
                value=response,
                strategy=ExtractionStrategy.AI_ENHANCED.value,
                options=request.options.dict() if request.options else None,
                ttl=3600
            )
            
            # Track confidence distribution metrics
            confidence_dist = self._calculate_confidence_distribution(ai_entities + ai_citations)
            avg_confidence = sum(e.confidence_score for e in ai_entities + ai_citations) / max(1, len(ai_entities + ai_citations))
            
            self.logger.info(
                f"AI-enhanced extraction completed for document_id: {request.document_id}",
                extra={
                    "event_type": "ai_enhanced_extraction_complete",
                    "document_id": request.document_id,
                    "entities_found": len(ai_entities),
                    "citations_found": len(ai_citations),
                    "relationships_found": len(relationships),
                    "processing_time_ms": processing_time,
                    "avg_confidence": avg_confidence,
                    "confidence_distribution": confidence_dist,
                    "performance_metrics": {
                        "multi_signal_avg": avg_confidence,
                        "confidence_range": f"{min(e.confidence_score for e in ai_entities + ai_citations) if ai_entities + ai_citations else 0:.2f}-{max(e.confidence_score for e in ai_entities + ai_citations) if ai_entities + ai_citations else 0:.2f}",
                        "high_confidence_ratio": sum(1 for e in ai_entities + ai_citations if e.confidence_score >= 0.7) / max(1, len(ai_entities + ai_citations))
                    }
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"AI-enhanced extraction failed: {str(e)}", exc_info=True)
            raise ExtractionError(f"AI-enhanced extraction failed: {str(e)}") from e
    
    async def _run_chunked_ai_enhanced_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run AI-enhanced extraction on chunked document.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Extraction results from chunked AI-enhanced strategy
        """
        start_time = time.time()
        request_id = f"chunked_ai_enhanced_{int(start_time * 1000)}"
        
        # Use SmartChunker for AI-enhanced
        if not self._smart_chunker:
            self._smart_chunker = SmartChunker(self.runtime_config)
        
        chunks = self._smart_chunker.chunk_document(
            request.text,
            strategy="semantic"  # Semantic chunking for AI-enhanced
        )
        
        self.logger.info(f"Processing {len(chunks)} chunks with AI-enhanced extraction")
        
        all_entities = []
        all_citations = []
        
        for i, chunk in enumerate(chunks):
            self.logger.info(
                f"Processing chunk {i+1}/{len(chunks)} with AI-enhanced "
                f"(chars {chunk.start_pos}-{chunk.end_pos})"
            )
            
            try:
                # AI-enhanced extraction on chunk
                chunking_config = self._get_chunking_config()
                ai_entities, ai_citations = await self._ai_enhancer.discover_entities_compatibility(
                    chunk.text,
                    [],
                    strategy=ExtractionStrategy.AI_ENHANCED.value,
                    chunking_config=chunking_config
                )
                
                # Adjust positions and apply confidence scoring
                for entity in ai_entities:
                    if entity.position:
                        entity.position.start += chunk.start_pos
                        entity.position.end += chunk.start_pos
                    entity.confidence_score = self._calculate_strategy_confidence(
                        entity, ExtractionStrategy.AI_ENHANCED.value
                    )
                    entity.extraction_method = ExtractionMethod.AI_DISCOVERED
                    entity.ai_enhancements.append("ai_strategy:enhanced_nlp")
                    entity.ai_enhancements.append(f"chunk:{i}")
                
                for citation in ai_citations:
                    if citation.position:
                        citation.position.start += chunk.start_pos
                        citation.position.end += chunk.start_pos
                    citation.confidence_score = self._calculate_strategy_confidence(
                        citation, ExtractionStrategy.AI_ENHANCED.value
                    )
                    citation.extraction_method = ExtractionMethod.AI_DISCOVERED
                    citation.ai_enhancements.append("ai_strategy:enhanced_nlp")
                    citation.ai_enhancements.append(f"chunk:{i}")
                
                all_entities.extend(ai_entities)
                all_citations.extend(ai_citations)
                
            except Exception as e:
                self.logger.error(f"Failed to process chunk {i+1} with AI-enhanced: {str(e)}")
                continue
        
        # Deduplicate and filter
        unique_entities = self._deduplicate_entities(all_entities)
        unique_citations = self._deduplicate_citations(all_citations)
        
        # Apply strategy-specific filtering
        filtered_entities, filtered_citations = self._apply_strategy_filters(
            unique_entities, unique_citations,
            ExtractionStrategy.AI_ENHANCED.value
        )
        
        # Calculate processing summary
        processing_time = int((time.time() - start_time) * 1000)
        processing_summary = ProcessingSummary(
            total_processing_time_ms=processing_time,
            regex_stage_time_ms=0,
            ai_enhancement_time_ms=processing_time,
            entities_found=len(filtered_entities),
            citations_found=len(filtered_citations),
            relationships_found=0,
            ai_enhancements_applied=len(filtered_entities) + len(filtered_citations),
            processing_stages_completed=[f"chunked_ai_enhanced_{len(chunks)}_chunks"],
            confidence_distribution=self._calculate_confidence_distribution(filtered_entities + filtered_citations),
            avg_confidence_score=sum(e.confidence_score for e in filtered_entities + filtered_citations) / max(1, len(filtered_entities + filtered_citations))
        )
        
        # Create response
        response = ExtractionResponse(
            document_id=request.document_id,
            processing_summary=processing_summary,
            entities=filtered_entities,
            citations=filtered_citations,
            relationships=[],
            metadata={
                "request_id": request_id,
                "strategy": ExtractionStrategy.AI_ENHANCED.value,
                "chunked": True,
                "chunks_processed": len(chunks),
                "nlp_features": ["coreference_resolution", "semantic_similarity", "context_analysis"]
            },
            warnings=[],
            errors=[],
            request_id=request_id,
            success=True
        )
        
        # Cache the response
        cache = get_response_cache()
        await cache.set(
            text=request.text,
            extraction_mode="ai_enhanced",
            value=response,
            strategy=ExtractionStrategy.AI_ENHANCED.value,
            options=request.options.dict() if request.options else None,
            ttl=3600
        )
        
        self.logger.info(
            f"Chunked AI-enhanced extraction completed: {len(filtered_entities)} entities, "
            f"{len(filtered_citations)} citations from {len(chunks)} chunks"
        )
        
        return response
    
    async def _run_smart_chunked_ai_enhanced_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run AI-enhanced extraction on very large documents using smart chunking.
        
        This method is specifically for documents >50K characters, using optimized chunk sizes
        based on the formula: (doc_chars / context_window) * 0.8.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Extraction results from smart chunked AI-enhanced strategy
        """
        start_time = time.time()
        request_id = f"smart_chunked_ai_enhanced_{int(start_time * 1000)}"
        
        # Use SmartChunker with smart_chunk_document for large documents
        if not self._smart_chunker:
            self._smart_chunker = SmartChunker(self.runtime_config)
        
        # Use the smart chunking method for documents >50K
        chunks = self._smart_chunker.smart_chunk_document(
            request.text,
            strategy=ChunkingStrategy.LEGAL_AWARE,  # Use legal-aware for AI-enhanced
            document_type=self._smart_chunker.detect_document_type(request.text)
        )
        
        self.logger.info(f"Smart chunking: Processing {len(chunks)} optimized chunks with AI-enhanced extraction")
        
        all_entities = []
        all_citations = []
        
        for i, chunk in enumerate(chunks):
            self.logger.info(
                f"Processing smart chunk {i+1}/{len(chunks)} with AI-enhanced "
                f"(size: {len(chunk.text):,} chars, overlap: {chunk.metadata.get('overlap_before', 0)} chars)"
            )
            
            try:
                # AI-enhanced extraction on smart chunk
                chunking_config = self._get_chunking_config()
                ai_entities, ai_citations = await self._ai_enhancer.discover_entities_compatibility(
                    chunk.text,
                    [],
                    strategy=ExtractionStrategy.AI_ENHANCED.value,
                    chunking_config=chunking_config
                )
                
                # Adjust positions and apply confidence scoring
                for entity in ai_entities:
                    if entity.position:
                        entity.position.start += chunk.start_pos
                        entity.position.end += chunk.start_pos
                    entity.confidence_score = self._calculate_strategy_confidence(
                        entity, ExtractionStrategy.AI_ENHANCED.value
                    )
                    entity.extraction_method = ExtractionMethod.AI_DISCOVERED
                    entity.ai_enhancements.append("ai_strategy:enhanced_nlp")
                    if not entity.attributes.additional_attributes:
                        entity.attributes.additional_attributes = {}
                    entity.attributes.additional_attributes.update({
                        'smart_chunk': i,
                        'chunk_size': len(chunk.text),
                        'overlap': chunk.metadata.get('overlap_before', 0)
                    })
                
                for citation in ai_citations:
                    if citation.position:
                        citation.position.start += chunk.start_pos
                        citation.position.end += chunk.start_pos
                    citation.confidence_score = self._calculate_strategy_confidence(
                        citation, ExtractionStrategy.AI_ENHANCED.value
                    )
                    citation.extraction_method = ExtractionMethod.AI_DISCOVERED
                    citation.ai_enhancements.append("ai_strategy:enhanced_nlp")
                    if not citation.components.additional_components:
                        citation.components.additional_components = {}
                    citation.components.additional_components.update({
                        'smart_chunk': str(i),
                        'chunk_size': str(len(chunk.text)),
                        'overlap': str(chunk.metadata.get('overlap_before', 0))
                    })
                
                all_entities.extend(ai_entities)
                all_citations.extend(ai_citations)
                
            except Exception as e:
                self.logger.error(f"Failed to process smart chunk {i+1} with AI-enhanced: {str(e)}")
                continue
        
        # Enhanced deduplication for overlapping chunks
        unique_entities = self._deduplicate_entities_with_overlap(all_entities)
        unique_citations = self._deduplicate_citations_with_overlap(all_citations)
        
        # Apply strategy-specific filtering
        filtered_entities, filtered_citations = self._apply_strategy_filters(
            unique_entities, unique_citations,
            ExtractionStrategy.AI_ENHANCED.value
        )
        
        # Calculate processing summary
        processing_time = int((time.time() - start_time) * 1000)
        processing_summary = ProcessingSummary(
            total_processing_time_ms=processing_time,
            regex_stage_time_ms=0,
            ai_enhancement_time_ms=processing_time,
            entities_found=len(filtered_entities),
            citations_found=len(filtered_citations),
            relationships_found=0,
            ai_enhancements_applied=len(filtered_entities) + len(filtered_citations),
            processing_stages_completed=[f"smart_chunked_ai_enhanced_{len(chunks)}_chunks"],
            confidence_distribution=self._calculate_confidence_distribution(filtered_entities + filtered_citations),
            avg_confidence_score=sum(e.confidence_score for e in filtered_entities + filtered_citations) / max(1, len(filtered_entities + filtered_citations))
        )
        
        # Create response
        response = ExtractionResponse(
            document_id=request.document_id,
            processing_summary=processing_summary,
            entities=filtered_entities,
            citations=filtered_citations,
            relationships=[],
            metadata={
                "request_id": request_id,
                "strategy": ExtractionStrategy.AI_ENHANCED.value,
                "smart_chunked": True,
                "chunks_processed": len(chunks),
                "document_size": len(request.text),
                "avg_chunk_size": sum(len(c.text) for c in chunks) / len(chunks),
                "nlp_features": ["coreference_resolution", "semantic_similarity", "context_analysis"]
            },
            warnings=[],
            errors=[],
            request_id=request_id,
            success=True
        )
        
        # Cache the response
        cache = get_response_cache()
        await cache.set(
            text=request.text,
            extraction_mode="smart_ai_enhanced",
            value=response,
            strategy=ExtractionStrategy.AI_ENHANCED.value,
            options=request.options.dict() if request.options else None,
            ttl=3600
        )
        
        self.logger.info(
            f"Smart chunked AI-enhanced extraction completed: {len(filtered_entities)} entities, "
            f"{len(filtered_citations)} citations from {len(chunks)} smart chunks"
        )
        
        return response
    
    async def _run_unified_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run unified extraction strategy with comprehensive single-pass extraction.
        
        This strategy performs a single comprehensive pass extracting all entity types
        with balanced precision/recall and minimum 0.6 confidence threshold.
        
        Args:
            request: ExtractionRequest with document content and options
            
        Returns:
            ExtractionResponse: Extraction results from unified strategy
        """
        start_time = time.time()
        request_id = f"unified_{int(start_time * 1000)}"
        
        # Track AI enhancement status
        ai_enhancement_status = "not_attempted"
        ai_enhancement_details = {}
        document_chars = len(request.text)
        estimated_tokens = document_chars * 1.3  # Rough estimate
        
        try:
            # Run regex extraction first for base entity detection
            if self._regex_engine:
                start_time = time.time()
                # The extract_entities method returns a tuple of (entities, citations)
                entities, citations = await self._regex_engine.extract_entities(
                    request.text
                )
                # Convert Entity/Citation objects to dicts for compatibility
                regex_entities = [e.to_dict() if hasattr(e, 'to_dict') else e for e in entities]
                regex_citations = [c.to_dict() if hasattr(c, 'to_dict') else c for c in citations]
                regex_time = int((time.time() - start_time) * 1000)
                regex_stats = {
                    "entities_found": len(regex_entities),
                    "citations_found": len(regex_citations)
                }
                
                self.logger.info(
                    f"UNIFIED: Regex found {len(regex_entities)} entities, {len(regex_citations)} citations in {regex_time:.2f}ms"
                )
            else:
                regex_entities = []
                regex_citations = []
                regex_time = 0
                self.logger.warning("UNIFIED: RegexEngine not available, skipping regex extraction")
            
            # Run single-pass AI enhancement for comprehensive coverage
            ai_entities = []
            ai_citations = []
            ai_time = 0
            
            # Log document size for diagnostics
            self.logger.info(
                f"Unified extraction - Document size: {document_chars} chars (~{estimated_tokens:.0f} tokens)"
            )
            
            if self._ai_enhancer and self._vllm_client:
                ai_enhancement_status = "attempting"
                
                # Check if document exceeds safe context limit from config
                if document_chars > self.runtime_config.chunking.max_chunk_size:
                    self.logger.warning(
                        f"Document size ({document_chars} chars) exceeds safe AI context limit. "
                        f"Implementing chunking strategy for AI enhancement."
                    )
                    ai_enhancement_status = "chunking_required"
                    ai_enhancement_details["reason"] = "document_exceeds_context_limit"
                    ai_enhancement_details["document_chars"] = document_chars
                    ai_enhancement_details["estimated_tokens"] = estimated_tokens
                    
                    # Use resilience manager for chunked processing
                    try:
                        ai_entities, ai_citations = await self._run_chunked_ai_enhancement(
                            regex_entities, regex_citations, request.text,
                            strategy=ExtractionStrategy.UNIFIED.value
                        )
                        if ai_entities or ai_citations:
                            ai_enhancement_status = "success_with_chunking"
                            ai_enhancement_details["chunks_processed"] = True
                        else:
                            ai_enhancement_status = "failed_empty_response"
                    except Exception as e:
                        self.logger.error(f"Chunked AI enhancement failed: {str(e)}")
                        ai_enhancement_status = "failed_with_chunking"
                        ai_enhancement_details["error"] = str(e)
                else:
                    # Document is small enough for direct processing
                    try:
                        # Use unified strategy for balanced extraction
                        enhanced_entities, enhanced_citations = await self._ai_enhancer.validate_extractions(
                            regex_entities, regex_citations, request.text,
                            strategy=ExtractionStrategy.UNIFIED.value
                        )
                        
                        # Also discover any missed entities in a single pass
                        chunking_config = self._get_chunking_config()
                        discovered_entities, discovered_citations = await self._ai_enhancer.discover_entities_compatibility(
                            request.text,  # document_text (positional)
                            regex_entities + regex_citations,  # existing_entities_and_citations (positional)
                            strategy=ExtractionStrategy.UNIFIED.value,
                            chunking_config=chunking_config
                        )
                        
                        ai_entities = enhanced_entities + discovered_entities
                        ai_citations = enhanced_citations + discovered_citations
                        
                        if ai_entities or ai_citations:
                            ai_enhancement_status = "success"
                            self.logger.info(
                                f"AI enhancement successful: {len(ai_entities)} entities, {len(ai_citations)} citations"
                            )
                        else:
                            ai_enhancement_status = "no_enhancements_found"
                            self.logger.warning("AI enhancement returned no results")
                            
                    except Exception as e:
                        error_str = str(e).lower()
                        if "context" in error_str or "token" in error_str or "length" in error_str:
                            ai_enhancement_status = "failed_context_limit"
                            ai_enhancement_details["error"] = "Context limit exceeded"
                            ai_enhancement_details["document_chars"] = document_chars
                            self.logger.error(
                                f"AI enhancement failed due to context limit: {document_chars} chars"
                            )
                        else:
                            ai_enhancement_status = "failed_unknown"
                            ai_enhancement_details["error"] = str(e)
                            self.logger.error(f"AI enhancement failed: {str(e)}")
                
                ai_time = int((time.time() - start_time - regex_time/1000) * 1000)
            else:
                ai_enhancement_status = "skipped_no_client"
                ai_enhancement_details["ai_enhancer_available"] = self._ai_enhancer is not None
                ai_enhancement_details["vllm_client_available"] = self._vllm_client is not None
                self.logger.warning(
                    f"AI enhancement skipped - ai_enhancer: {self._ai_enhancer is not None}, "
                    f"vllm_client: {self._vllm_client is not None}"
                )
            
            # Apply strategy-aware confidence scoring before merging
            for entity in regex_entities:
                entity.confidence_score = self._calculate_strategy_confidence(
                    entity, ExtractionStrategy.UNIFIED.value
                )
            
            for citation in regex_citations:
                citation.confidence_score = self._calculate_strategy_confidence(
                    citation, ExtractionStrategy.UNIFIED.value
                )
            
            for entity in ai_entities:
                entity.confidence_score = self._calculate_strategy_confidence(
                    entity, ExtractionStrategy.UNIFIED.value
                )
            
            for citation in ai_citations:
                citation.confidence_score = self._calculate_strategy_confidence(
                    citation, ExtractionStrategy.UNIFIED.value
                )
            
            # Use strategy-aware merging
            all_entities, all_citations = self._merge_strategy_aware(
                regex_entities, regex_citations, ai_entities, ai_citations,
                ExtractionStrategy.UNIFIED.value
            )
            
            # Apply strategy-specific filtering
            filtered_entities, filtered_citations = self._apply_strategy_filters(
                all_entities, all_citations,
                ExtractionStrategy.UNIFIED.value
            )
            
            # Balance entity types if configured
            unified_config = UnifiedConfig()
            if unified_config.balance_precision_recall:
                # Ensure reasonable distribution across entity types
                entity_type_counts = {}
                for entity in filtered_entities:
                    entity_type_counts[entity.entity_type] = entity_type_counts.get(entity.entity_type, 0) + 1
                
                # Log distribution for monitoring
                self.logger.debug(f"Entity type distribution: {entity_type_counts}")
            
            # Calculate processing summary
            processing_time = int((time.time() - start_time) * 1000)
            processing_summary = ProcessingSummary(
                total_processing_time_ms=processing_time,
                regex_stage_time_ms=regex_time,
                ai_enhancement_time_ms=ai_time,
                entities_found=len(filtered_entities),
                citations_found=len(filtered_citations),
                relationships_found=0,
                ai_enhancements_applied=len(ai_entities) + len(ai_citations),
                processing_stages_completed=["regex_extraction", "unified_ai_pass", "confidence_filtering"],
                confidence_distribution=self._calculate_confidence_distribution(filtered_entities + filtered_citations),
                avg_confidence_score=sum(e.confidence_score for e in filtered_entities + filtered_citations) / max(1, len(filtered_entities + filtered_citations))
            )
            
            # Create response
            response = ExtractionResponse(
                document_id=request.document_id,
                processing_summary=processing_summary,
                entities=filtered_entities,
                citations=filtered_citations,
                relationships=[],
                metadata={
                    "request_id": request_id,
                    "strategy": ExtractionStrategy.UNIFIED.value,
                    "min_confidence": unified_config.min_confidence,
                    "entities_before_filter": len(all_entities),
                    "entities_after_filter": len(filtered_entities),
                    "citations_before_filter": len(all_citations),
                    "citations_after_filter": len(filtered_citations),
                    "ai_enhancement_used": ai_enhancement_status.startswith("success"),
                    "ai_enhancement_status": ai_enhancement_status,
                    "ai_enhancement_details": ai_enhancement_details,
                    "ai_coverage_percentage": (len(ai_entities) + len(ai_citations)) / max(1, len(filtered_entities) + len(filtered_citations)) * 100 if ai_enhancement_status.startswith("success") else 0
                },
                warnings=[],
                errors=[],
                request_id=request_id,
                success=True
            )
            
            # Cache the response
            cache = get_response_cache()
            await cache.set(
                text=request.text,
                extraction_mode="unified",
                value=response,
                strategy=ExtractionStrategy.UNIFIED.value,
                options=request.options.dict() if request.options else None,
                ttl=3600
            )
            
            # Track confidence distribution metrics
            confidence_dist = self._calculate_confidence_distribution(filtered_entities + filtered_citations)
            avg_confidence = sum(e.confidence_score for e in filtered_entities + filtered_citations) / max(1, len(filtered_entities + filtered_citations))
            
            self.logger.info(
                f"Unified extraction completed for document_id: {request.document_id}",
                extra={
                    "event_type": "unified_extraction_complete",
                    "document_id": request.document_id,
                    "entities_found": len(filtered_entities),
                    "citations_found": len(filtered_citations),
                    "processing_time_ms": processing_time,
                    "avg_confidence": avg_confidence,
                    "confidence_distribution": confidence_dist,
                    "performance_metrics": {
                        "filtered_out_count": len(all_entities) + len(all_citations) - len(filtered_entities) - len(filtered_citations),
                        "confidence_range": f"{min(e.confidence_score for e in filtered_entities + filtered_citations) if filtered_entities + filtered_citations else 0:.2f}-{max(e.confidence_score for e in filtered_entities + filtered_citations) if filtered_entities + filtered_citations else 0:.2f}",
                        "above_threshold_ratio": len(filtered_entities + filtered_citations) / max(1, len(all_entities + all_citations))
                    }
                }
            )
            
            return response

        except Exception as e:
            self.logger.error(f"Unified extraction failed: {str(e)}", exc_info=True)
            raise ExtractionError(f"Unified extraction failed: {str(e)}") from e

    async def _run_chunked_ai_enhancement(
        self,
        regex_entities: List[Entity],
        regex_citations: List[Citation],
        document_text: str,
        strategy: str = "unified",
        chunk_size: int = 50000,
        overlap: int = 5000
    ) -> Tuple[List[Entity], List[Citation]]:
        """
        Run AI enhancement on large documents using SmartChunker.
        
        Args:
            regex_entities: Entities found by regex
            regex_citations: Citations found by regex
            document_text: Full document text
            strategy: Extraction strategy
            chunk_size: Size of each chunk in characters (unused - from config)
            overlap: Overlap between chunks (unused - from config)
            
        Returns:
            Tuple of (ai_enhanced_entities, ai_enhanced_citations)
        """
        if not self._smart_chunker:
            # Fallback to manual chunking if SmartChunker not available
            self.logger.warning("SmartChunker not available, using manual chunking")
            return await self._run_manual_chunked_ai_enhancement(
                regex_entities, regex_citations, document_text, 
                strategy, chunk_size, overlap
            )
        
        # Use SmartChunker with appropriate strategy
        chunking_strategy = self._get_chunking_strategy(strategy)
        chunks = self._smart_chunker.chunk_document(
            document_text, 
            strategy=chunking_strategy
        )
        
        self.logger.info(
            f"SmartChunker created {len(chunks)} chunks using {chunking_strategy} strategy"
        )
        
        # Process each chunk
        all_ai_entities = []
        all_ai_citations = []
        successful_chunks = []
        failed_chunks = []
        
        self.logger.info(
            f"📊 CHUNK PROCESSING START: Document has {len(document_text)} chars, "
            f"processing {len(chunks)} chunks"
        )
        
        for i, chunk in enumerate(chunks):
            chunk_start = chunk.start_pos
            chunk_end = chunk.end_pos
            chunk_text = chunk.text
            
            self.logger.info(
                f"🔄 Processing chunk {i+1}/{len(chunks)} "
                f"(chars {chunk_start}-{chunk_end}, size: {len(chunk_text)})"
            )
            
            try:
                # Filter regex entities/citations to those in this chunk
                chunk_regex_entities = [
                    e for e in regex_entities
                    if e.position and chunk_start <= e.position.start < chunk_end
                ]
                chunk_regex_citations = [
                    c for c in regex_citations
                    if c.position and chunk_start <= c.position.start < chunk_end
                ]
                
                # Use throttled client for AI enhancement
                enhanced_entities, enhanced_citations = await self._ai_enhancer.validate_extractions(
                    chunk_regex_entities, chunk_regex_citations, chunk_text,
                    strategy=strategy
                )
                
                # Discover new entities in chunk
                # IMPORTANT: Tell discover_entities NOT to re-chunk since we're already passing a chunk
                chunking_config = self._get_chunking_config()
                chunking_config['disable_micro_chunking'] = True  # Prevent double-chunking
                chunking_config['chunk_offset'] = chunk_start  # Pass chunk offset for position calculation
                
                self.logger.info(
                    f"🔍 Discovering entities in chunk {i+1} with disable_micro_chunking=True"
                )
                
                discovered_entities, discovered_citations = await self._ai_enhancer.discover_entities_compatibility(
                    chunk_text,
                    chunk_regex_entities + chunk_regex_citations,
                    strategy=strategy,
                    chunking_config=chunking_config
                )
                
                # Adjust positions for chunk offset
                for entity in enhanced_entities + discovered_entities:
                    if entity.position:
                        entity.position.start += chunk_start
                        entity.position.end += chunk_start
                
                for citation in enhanced_citations + discovered_citations:
                    if citation.position:
                        citation.position.start += chunk_start
                        citation.position.end += chunk_start
                
                # Track entities before extension for debugging
                entities_before = len(all_ai_entities)
                citations_before = len(all_ai_citations)
                
                all_ai_entities.extend(enhanced_entities + discovered_entities)
                all_ai_citations.extend(enhanced_citations + discovered_citations)
                
                successful_chunks.append(i)
                
                self.logger.info(
                    f"✅ Chunk {i+1} SUCCESS: Found {len(enhanced_entities + discovered_entities)} entities, "
                    f"{len(enhanced_citations + discovered_citations)} citations. "
                    f"Total so far: {len(all_ai_entities)} entities, {len(all_ai_citations)} citations"
                )
                
            except Exception as e:
                failed_chunks.append(i)
                self.logger.error(
                    f"❌ Chunk {i+1} FAILED: {str(e)}. "
                    f"Continuing with remaining chunks..."
                )
                # Continue with other chunks even if one fails
                continue
        
        # Deduplicate entities and citations
        unique_entities = self._deduplicate_entities(all_ai_entities)
        unique_citations = self._deduplicate_citations(all_ai_citations)
        
        # Log comprehensive summary
        self.logger.info(
            f"📊 CHUNK PROCESSING COMPLETE:\n"
            f"  - Successful chunks: {len(successful_chunks)}/{len(chunks)}\n"
            f"  - Failed chunks: {len(failed_chunks)}/{len(chunks)}\n"
            f"  - Total entities found: {len(all_ai_entities)}\n"
            f"  - Total citations found: {len(all_ai_citations)}\n"
            f"  - Unique entities after dedup: {len(unique_entities)}\n"
            f"  - Unique citations after dedup: {len(unique_citations)}"
        )
        
        if failed_chunks:
            self.logger.warning(f"⚠️ Failed chunk indices: {failed_chunks}")
        
        if len(all_ai_entities) > 0:
            # Log position distribution to verify all chunks were processed
            positions = [e.position.start for e in all_ai_entities if e.position]
            if positions:
                self.logger.info(
                    f"📍 Entity position range: {min(positions)} - {max(positions)} "
                    f"(document size: {len(document_text)})"
                )
        
        return unique_entities, unique_citations
    
    def _get_chunking_strategy(self, extraction_strategy: str) -> str:
        """
        Map extraction strategy to appropriate chunking strategy.
        
        Args:
            extraction_strategy: The extraction strategy being used
            
        Returns:
            str: The appropriate chunking strategy
        """
        # Map extraction strategies to chunking strategies
        strategy_mapping = {
            ExtractionStrategy.MULTIPASS.value: "legal",  # Legal docs benefit from legal chunking
            ExtractionStrategy.AI_ENHANCED.value: "semantic",  # AI-enhanced uses semantic understanding
            ExtractionStrategy.UNIFIED.value: "hybrid",  # Unified uses hybrid approach
            "regex_only": "simple",  # Simple chunking for regex-only
        }
        
        return strategy_mapping.get(extraction_strategy, "hybrid")  # Default to hybrid
    
    async def _run_manual_chunked_ai_enhancement(
        self,
        regex_entities: List[Entity],
        regex_citations: List[Citation],
        document_text: str,
        strategy: str = "unified",
        chunk_size: int = 50000,
        overlap: int = 5000
    ) -> Tuple[List[Entity], List[Citation]]:
        """
        Fallback manual chunking method when SmartChunker is not available.
        
        Args:
            regex_entities: Entities found by regex
            regex_citations: Citations found by regex
            document_text: Full document text
            strategy: Extraction strategy
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            Tuple of (ai_enhanced_entities, ai_enhanced_citations)
        """
        self.logger.info(
            f"Using manual chunking with chunk_size={chunk_size}, overlap={overlap}"
        )
        
        # Create chunks manually
        chunks = []
        text_length = len(document_text)
        start = 0
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = document_text[start:end]
            chunks.append((start, end, chunk))
            
            if end >= text_length:
                break
            
            start = end - overlap
        
        self.logger.info(f"Created {len(chunks)} manual chunks for AI processing")
        
        # Process each chunk
        all_ai_entities = []
        all_ai_citations = []
        
        for i, (chunk_start, chunk_end, chunk_text) in enumerate(chunks):
            self.logger.info(
                f"Processing manual chunk {i+1}/{len(chunks)} "
                f"(chars {chunk_start}-{chunk_end}, size: {len(chunk_text)})"
            )
            
            try:
                # Filter regex entities/citations to those in this chunk
                chunk_regex_entities = [
                    e for e in regex_entities
                    if e.position and chunk_start <= e.position.start < chunk_end
                ]
                chunk_regex_citations = [
                    c for c in regex_citations
                    if c.position and chunk_start <= c.position.start < chunk_end
                ]
                
                # Run AI enhancement on chunk
                enhanced_entities, enhanced_citations = await self._ai_enhancer.validate_extractions(
                    chunk_regex_entities, chunk_regex_citations, chunk_text,
                    strategy=strategy
                )
                
                # Discover new entities in chunk
                # IMPORTANT: Tell discover_entities NOT to re-chunk since we're already passing a chunk
                chunking_config = self._get_chunking_config()
                chunking_config['disable_micro_chunking'] = True  # Prevent double-chunking
                chunking_config['chunk_offset'] = chunk_start  # Pass chunk offset for position calculation
                
                self.logger.info(
                    f"🔍 Discovering entities in chunk {i+1} with disable_micro_chunking=True"
                )
                
                discovered_entities, discovered_citations = await self._ai_enhancer.discover_entities_compatibility(
                    chunk_text,
                    chunk_regex_entities + chunk_regex_citations,
                    strategy=strategy,
                    chunking_config=chunking_config
                )
                
                # Adjust positions for chunk offset
                for entity in enhanced_entities + discovered_entities:
                    if entity.position:
                        entity.position.start += chunk_start
                        entity.position.end += chunk_start
                
                for citation in enhanced_citations + discovered_citations:
                    if citation.position:
                        citation.position.start += chunk_start
                        citation.position.end += chunk_start
                
                all_ai_entities.extend(enhanced_entities + discovered_entities)
                all_ai_citations.extend(enhanced_citations + discovered_citations)
                
                self.logger.info(
                    f"Manual chunk {i+1} results: {len(enhanced_entities + discovered_entities)} entities, "
                    f"{len(enhanced_citations + discovered_citations)} citations"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to process manual chunk {i+1}: {str(e)}")
                # Continue with other chunks even if one fails
                continue
        
        # Deduplicate entities and citations
        unique_entities = self._deduplicate_entities(all_ai_entities)
        unique_citations = self._deduplicate_citations(all_ai_citations)
        
        self.logger.info(
            f"Manual chunked AI enhancement complete: {len(unique_entities)} unique entities, "
            f"{len(unique_citations)} unique citations"
        )
        
        return unique_entities, unique_citations
    
    def _deduplicate_entities_with_overlap(self, entities: List[Entity]) -> List[Entity]:
        """
        Enhanced deduplication for entities from overlapping chunks.
        
        This method handles entities that may appear in multiple overlapping chunks,
        preferring entities with higher confidence scores and merging metadata.
        
        Args:
            entities: List of entities potentially containing duplicates from overlapping chunks
            
        Returns:
            List of unique entities with merged metadata
        """
        if not entities:
            return []
        
        # Group entities by normalized key (text + approximate position)
        entity_groups = {}
        position_tolerance = 10  # Allow 10 character position variance
        
        for entity in entities:
            # Create a normalized key
            norm_text = entity.text.lower().strip()
            approx_pos = entity.position.start // position_tolerance * position_tolerance
            key = (norm_text, approx_pos)
            
            if key not in entity_groups:
                entity_groups[key] = []
            entity_groups[key].append(entity)
        
        # Select best entity from each group
        unique_entities = []
        for key, group in entity_groups.items():
            if len(group) == 1:
                unique_entities.append(group[0])
            else:
                # Select entity with highest confidence score
                best_entity = max(group, key=lambda e: e.confidence_score)
                
                # Merge metadata from all occurrences
                merged_metadata = {}
                chunks_found_in = []
                for entity in group:
                    if hasattr(entity.attributes, 'additional_attributes') and entity.attributes.additional_attributes:
                        merged_metadata.update(entity.attributes.additional_attributes)
                        if 'smart_chunk' in entity.attributes.additional_attributes:
                            chunks_found_in.append(entity.attributes.additional_attributes['smart_chunk'])
                
                # Update metadata to show it was found in multiple chunks
                if chunks_found_in:
                    merged_metadata['found_in_chunks'] = list(set(chunks_found_in))
                    merged_metadata['occurrences'] = len(group)
                
                best_entity.attributes.additional_attributes = merged_metadata
                unique_entities.append(best_entity)
        
        self.logger.info(f"Deduplicated {len(entities)} entities to {len(unique_entities)} unique entities")
        return unique_entities
    
    def _deduplicate_citations_with_overlap(self, citations: List[Citation]) -> List[Citation]:
        """
        Enhanced deduplication for citations from overlapping chunks.
        
        This method handles citations that may appear in multiple overlapping chunks,
        preferring citations with higher confidence scores and merging metadata.
        
        Args:
            citations: List of citations potentially containing duplicates from overlapping chunks
            
        Returns:
            List of unique citations with merged metadata
        """
        if not citations:
            return []
        
        # Group citations by normalized text
        citation_groups = {}
        position_tolerance = 10  # Allow 10 character position variance
        
        for citation in citations:
            # Create a normalized key
            norm_text = citation.original_text.lower().strip()
            approx_pos = citation.position.start // position_tolerance * position_tolerance
            key = (norm_text, approx_pos)
            
            if key not in citation_groups:
                citation_groups[key] = []
            citation_groups[key].append(citation)
        
        # Select best citation from each group
        unique_citations = []
        for key, group in citation_groups.items():
            if len(group) == 1:
                unique_citations.append(group[0])
            else:
                # Select citation with highest confidence score
                best_citation = max(group, key=lambda c: c.confidence_score)
                
                # Merge metadata from all occurrences
                merged_metadata = {}
                chunks_found_in = []
                for citation in group:
                    if hasattr(citation.components, 'additional_components') and citation.components.additional_components:
                        merged_metadata.update(citation.components.additional_components)
                        if 'smart_chunk' in citation.components.additional_components:
                            chunks_found_in.append(citation.components.additional_components['smart_chunk'])
                
                # Update metadata to show it was found in multiple chunks
                if chunks_found_in:
                    merged_metadata['found_in_chunks'] = [str(c) for c in list(set(chunks_found_in))]
                    merged_metadata['occurrences'] = str(len(group))
                
                best_citation.components.additional_components = merged_metadata
                unique_citations.append(best_citation)
        
        self.logger.info(f"Deduplicated {len(citations)} citations to {len(unique_citations)} unique citations")
        return unique_citations
    
    def _deduplicate_citations(self, citations: List[Citation]) -> List[Citation]:
        """Remove duplicate citations based on text."""
        seen = set()
        unique = []
        
        for citation in citations:
            key = citation.original_text.lower().strip()
            
            if key not in seen:
                seen.add(key)
                unique.append(citation)
        
        return unique
    
    def _determine_extraction_mode(self, options: Optional[ExtractionOptions]) -> ExtractionMode:
        """
        Determine the extraction mode based on request options.
        Note: regex_only mode has been deprecated and redirects to unified extraction.
        
        Args:
            options: Extraction options from request
            
        Returns:
            ExtractionMode: Determined extraction mode
        """
        if not options:
            return ExtractionMode.AI_ENHANCED
        
        ai_mode = options.ai_enhancement_mode

        # Map AI enhancement modes to extraction modes correctly
        if ai_mode == "regex_only":
            # Deprecated - redirect to AI_ENHANCED for better accuracy
            self.logger.warning(
                "regex_only mode is deprecated. Using AI_ENHANCED mode instead for better accuracy."
            )
            return ExtractionMode.AI_ENHANCED       # Redirect to AI-powered extraction
        elif ai_mode == "validation_only":
            return ExtractionMode.AI_ENHANCED       # AI validation
        elif ai_mode == "comprehensive":
            return ExtractionMode.AI_ENHANCED       # Comprehensive AI enhancement
        else:
            # Default fallback for unknown modes
            return ExtractionMode.AI_ENHANCED
    
    async def _run_regex_extraction(
        self,
        text: str,
        document_id: str,
        options: Optional[ExtractionOptions]
    ) -> Tuple[List[Entity], List[Citation], int]:
        """
        Run direct regex pattern extraction using RegexEngine.
        This provides fast pattern matching without AI overhead.
        
        Args:
            text: Text content to analyze
            document_id: Document identifier
            options: Extraction options
            
        Returns:
            Tuple of (entities, citations, processing_time_ms)
        """
        start_time = time.time()
        
        try:
            # Check if regex engine is available
            if not self._regex_engine:
                self.logger.error("RegexEngine not initialized for REGEX_ONLY mode")
                return [], [], 0
            
            # Run regex pattern extraction
            entities, citations = await self._regex_engine.extract_all(text)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            self.logger.info(
                f"REGEX_ONLY extraction completed: {len(entities)} entities, {len(citations)} citations in {processing_time}ms",
                extra={
                    "event_type": "regex_extraction_complete",
                    "document_id": document_id,
                    "entities_found": len(entities),
                    "citations_found": len(citations),
                    "processing_time_ms": processing_time
                }
            )
            
            return entities, citations, processing_time
            
        except Exception as e:
            self.logger.error(
                f"REGEX_ONLY extraction failed: {str(e)}",
                extra={
                    "event_type": "regex_extraction_error",
                    "document_id": document_id,
                    "error": str(e)
                }
            )
            raise ExtractionError(f"REGEX extraction failed: {str(e)}") from e
    
    async def _run_ai_enhancement(
        self,
        text: str,
        existing_entities: List[Entity],
        existing_citations: List[Citation],
        document_id: str,
        options: Optional[ExtractionOptions],
        document_size_hint: Optional[int] = None
    ) -> Tuple[List[Entity], List[Citation], List[EntityRelationship], int, int]:
        """
        Run Stage 2: AI enhancement and validation.
        
        Args:
            text: Original text content
            existing_entities: Entities from regex stage
            existing_citations: Citations from regex stage
            document_id: Document identifier
            options: Extraction options
            
        Returns:
            Tuple of (ai_entities, ai_citations, relationships, processing_time_ms, enhancements_count)
        """
        start_time = time.time()
        
        try:
            if not self._ai_enhancer:
                raise ExtractionError("AIEnhancer not available")
            
            # Use vLLM client for AI enhancement
            if not self._vllm_client or not self._vllm_client.is_ready():
                raise ExtractionError("vLLM client not available or not ready for AI processing")
            
            self.logger.info(f"Using vLLM client for AI enhancement (document size: {document_size_hint})")
            
            # Use AI to enhance and validate extractions
            ai_entities = []
            ai_citations = []
            relationships = []
            enhancements_applied = 0
            
            # Get extraction strategy from options
            strategy = options.extraction_strategy if options and hasattr(options, 'extraction_strategy') else None
            
            # AI validation and enhancement using local processing only - with individual error handling
            if options and options.ai_enhancement_mode in ["comprehensive", "validation_only"]:
                try:
                    validated_entities, validated_citations = await self._ai_enhancer.validate_extractions(
                        existing_entities, existing_citations, text, strategy=strategy
                    )
                    ai_entities.extend(validated_entities)
                    ai_citations.extend(validated_citations)
                    enhancements_applied += len(validated_entities) + len(validated_citations)
                    self.logger.info(f"AI validation successful (strategy: {strategy}): {len(validated_entities)} entities, {len(validated_citations)} citations")
                except Exception as e:
                    self.logger.warning(f"AI validation failed but continuing: {e}")
                    # Continue with other AI operations even if validation fails
            
            # AI discovery of missed entities using local processing - with individual error handling
            if options and options.ai_enhancement_mode == "comprehensive":
                try:
                    chunking_config = self._get_chunking_config()
                    discovered_entities, discovered_citations = await self._ai_enhancer.discover_entities_compatibility(
                        text,  # document_text (positional)
                        existing_entities + existing_citations,  # existing_entities_and_citations (positional)
                        strategy=strategy,
                        chunking_config=chunking_config
                    )
                    ai_entities.extend(discovered_entities)
                    ai_citations.extend(discovered_citations)
                    enhancements_applied += len(discovered_entities) + len(discovered_citations)
                    self.logger.info(f"AI discovery successful (strategy: {strategy}): {len(discovered_entities)} entities, {len(discovered_citations)} citations")
                except Exception as e:
                    self.logger.warning(f"AI discovery failed but continuing: {e}")
                    # Continue with relationship extraction even if discovery fails
            
            # Extract relationships using local processing if enabled - with individual error handling
            if options and options.enable_relationship_extraction:
                try:
                    all_entities = existing_entities + ai_entities
                    all_citations = existing_citations + ai_citations
                    relationships = await self._ai_enhancer.extract_relationships(
                        all_entities, all_citations, text, strategy=strategy
                    )
                    self.logger.info(f"AI relationships successful: {len(relationships)} relationships")
                except Exception as e:
                    self.logger.warning(f"AI relationship extraction failed: {e}")
                    relationships = []  # Empty relationships but continue
            
            processing_time = int((time.time() - start_time) * 1000)
            
            self.logger.debug(
                f"AI enhancement completed: {len(ai_entities)} entities, {len(ai_citations)} citations, {len(relationships)} relationships",
                extra={
                    "event_type": "ai_enhancement_complete",
                    "document_id": document_id,
                    "ai_entities_found": len(ai_entities),
                    "ai_citations_found": len(ai_citations),
                    "relationships_found": len(relationships),
                    "enhancements_applied": enhancements_applied,
                    "processing_time_ms": processing_time
                }
            )
            
            return ai_entities, ai_citations, relationships, processing_time, enhancements_applied
            
        except Exception as e:
            self.logger.error(
                f"AI enhancement failed: {str(e)}",
                extra={
                    "event_type": "ai_enhancement_error",
                    "document_id": document_id,
                    "error": str(e)
                }
            )
            
            # CRITICAL FIX: Don't silently fall back - this masks critical errors
            # Log detailed diagnostic information for troubleshooting
            self.logger.critical(
                f"🚨 CRITICAL AI ENHANCEMENT FAILURE - This indicates a serious system problem: {str(e)}",
                extra={
                    "event_type": "critical_ai_failure",
                    "document_id": document_id,
                    "error": str(e),
                    "vllm_client_available": self._vllm_client is not None,
                    "vllm_client_ready": self._vllm_client.is_ready() if self._vllm_client else False,
                    "ai_enhancer_available": self._ai_enhancer is not None
                }
            )
            
            # For now, allow fallback but make it very obvious in the logs
            if self.settings.ai.enable_ai_fallback:
                self.logger.warning(f"⚠️ CONTINUING WITH REGEX-ONLY due to AI failure - Results will be incomplete!")
                # IMPORTANT: Return empty arrays means NO AI enhancement happens at all
                # This is why all entities remain as "regex_only" - the AI results are empty!
                return [], [], [], 0, 0
            else:
                raise ExtractionError(f"Local AI enhancement failed: {str(e)}") from e
    
    def _merge_extraction_results(
        self,
        regex_entities: List[Entity],
        regex_citations: List[Citation],
        ai_entities: List[Entity],
        ai_citations: List[Citation]
    ) -> Tuple[List[Entity], List[Citation]]:
        """
        Merge results from regex and AI extraction stages with comprehensive deduplication.
        
        This method performs intelligent merging with:
        - Position-based deduplication
        - Text similarity matching for near-duplicates
        - Overlapping entity resolution
        - Confidence score preservation
        
        Args:
            regex_entities: Entities from regex extraction
            regex_citations: Citations from regex extraction
            ai_entities: Entities from AI enhancement (enhanced versions + discoveries)
            ai_citations: Citations from AI enhancement (enhanced versions + discoveries)
            
        Returns:
            Tuple of (merged_entities, merged_citations)
        """
        self.logger.info(f"Merging results: {len(regex_entities)} regex entities + {len(ai_entities)} AI entities")
        
        # Enhanced deduplication and merging
        if ai_entities or ai_citations:
            self.logger.info(f"AI enhancement available - proceeding with comprehensive merge")
            
            # Use enhanced deduplication for entities
            merged_entities = self._deduplicate_entities(
                regex_entities, ai_entities, similarity_threshold=0.85
            )
            
            # Use enhanced deduplication for citations
            merged_citations = self._deduplicate_citations(
                regex_citations, ai_citations, similarity_threshold=0.90
            )
            
            self.logger.info(f"Merge complete: {len(merged_entities)} entities, {len(merged_citations)} citations")
            return merged_entities, merged_citations
        
        else:
            # No AI enhancement - deduplicate regex results only
            self.logger.info(f"No AI enhancement - deduplicating {len(regex_entities)} regex entities")
            
            # Deduplicate regex entities among themselves
            deduplicated_entities = self._deduplicate_entities(
                regex_entities, [], similarity_threshold=0.85
            )
            
            # Deduplicate regex citations among themselves
            deduplicated_citations = self._deduplicate_citations(
                regex_citations, [], similarity_threshold=0.90
            )
            
            # Set extraction method for all
            for entity in deduplicated_entities:
                if not hasattr(entity, 'extraction_method') or entity.extraction_method is None:
                    entity.extraction_method = ExtractionMethod.REGEX_ONLY
            
            for citation in deduplicated_citations:
                if not hasattr(citation, 'extraction_method') or citation.extraction_method is None:
                    citation.extraction_method = ExtractionMethod.REGEX_ONLY
            
            return deduplicated_entities, deduplicated_citations
    
    def _deduplicate_entities(
        self,
        primary_entities: List[Entity],
        secondary_entities: Optional[List[Entity]] = None,
        similarity_threshold: float = 0.85
    ) -> List[Entity]:
        """
        Unified deduplication method that handles both single-list and cross-list deduplication.
        
        Args:
            primary_entities: Primary list of entities (or the only list for single-list dedup)
            secondary_entities: Optional secondary list of entities (e.g., AI-enhanced)
            similarity_threshold: Threshold for text similarity (0.0 to 1.0)
            
        Returns:
            List of deduplicated entities
        """
        # Handle single-list deduplication (backward compatibility)
        if secondary_entities is None:
            if not primary_entities:
                return []
            
            # Use entity processor for advanced deduplication
            if hasattr(self, '_entity_processor'):
                # Convert Entity objects to dictionaries for processing
                entity_dicts = []
                for entity in primary_entities:
                    entity_dict = {
                        'text': entity.text,
                        'cleaned_text': entity.cleaned_text,
                        'entity_type': entity.entity_type.value if hasattr(entity.entity_type, 'value') else entity.entity_type,
                        'entity_subtype': entity.entity_subtype,
                        'confidence_score': entity.confidence_score,
                        'extraction_method': entity.extraction_method.value if hasattr(entity.extraction_method, 'value') else entity.extraction_method,
                        'position': {
                            'start': entity.position.start,
                            'end': entity.position.end,
                            'line_number': entity.position.line_number,
                            'context_start': entity.position.context_start,
                            'context_end': entity.position.context_end
                        } if entity.position else None,
                        'attributes': entity.attributes.dict() if hasattr(entity.attributes, 'dict') else entity.attributes,
                        'ai_enhancements': entity.ai_enhancements,
                        'context_snippet': entity.context_snippet,
                        'validation_notes': entity.validation_notes
                    }
                    entity_dicts.append(entity_dict)
                
                # Process entities for deduplication and normalization
                processed_entities = self._entity_processor.process_entities(entity_dicts)
                
                # Convert back to Entity objects
                unique_entities = []
                for entity_dict in processed_entities:
                    # Build Entity object from processed dictionary
                    from ..models.entities import EntityType, ExtractionMethod, TextPosition, EntityAttributes
                    
                    # Handle position
                    position = None
                    if entity_dict.get('position'):
                        pos_data = entity_dict['position']
                        position = TextPosition(
                            start=pos_data.get('start', 0),
                            end=pos_data.get('end', 0),
                            line_number=pos_data.get('line_number'),
                            context_start=pos_data.get('context_start'),
                            context_end=pos_data.get('context_end')
                        )
                    
                    # Handle attributes
                    attributes = EntityAttributes()
                    if entity_dict.get('attributes'):
                        attr_data = entity_dict['attributes']
                        if isinstance(attr_data, dict):
                            for key, value in attr_data.items():
                                if hasattr(attributes, key):
                                    setattr(attributes, key, value)
                    
                    # Create Entity object
                    entity = Entity(
                        text=entity_dict.get('text', ''),
                        cleaned_text=entity_dict.get('cleaned_text', entity_dict.get('text', '')),
                        entity_type=EntityType(entity_dict.get('entity_type', 'COURT')),
                        entity_subtype=entity_dict.get('entity_subtype', 'general'),
                        confidence_score=entity_dict.get('confidence_score', 0.5),
                        extraction_method=ExtractionMethod(entity_dict.get('extraction_method', 'regex_only')),
                        position=position,
                        attributes=attributes,
                        ai_enhancements=entity_dict.get('ai_enhancements', []),
                        context_snippet=entity_dict.get('context_snippet'),
                        validation_notes=entity_dict.get('validation_notes', [])
                    )
                    unique_entities.append(entity)
                
                # Log deduplication stats
                original_count = len(primary_entities)
                unique_count = len(unique_entities)
                if original_count > unique_count:
                    self.logger.info(
                        f"Entity deduplication: {original_count} → {unique_count} "
                        f"({original_count - unique_count} duplicates removed)"
                    )
                
                return unique_entities
            else:
                # Fallback: Simple deduplication based on text
                seen = set()
                unique = []
                for entity in primary_entities:
                    if entity.text not in seen:
                        seen.add(entity.text)
                        unique.append(entity)
                return unique
        
        # Handle cross-list deduplication (new functionality)
        from difflib import SequenceMatcher
        
        # Result list
        deduplicated = []
        processed_positions = set()
        
        # First, add all secondary entities (AI has priority)
        for entity in secondary_entities:
            if entity.position:
                key = (entity.position.start, entity.position.end)
                if key not in processed_positions:
                    deduplicated.append(entity)
                    processed_positions.add(key)
                    # Also mark overlapping positions as processed
                    for pos in range(entity.position.start - 10, entity.position.end + 10):
                        processed_positions.add((pos, pos))
            else:
                deduplicated.append(entity)
        
        # Then add primary entities that don't overlap
        for entity in primary_entities:
            if not entity.position:
                # If no position info, just add it
                deduplicated.append(entity)
                continue
                
            # Check for exact position match
            key = (entity.position.start, entity.position.end)
            if key in processed_positions:
                continue
            
            # Check for overlapping positions
            overlaps = False
            for existing in deduplicated:
                if not existing.position:
                    continue
                    
                # Check if positions overlap
                if (entity.position.start < existing.position.end and 
                    entity.position.end > existing.position.start):
                    # Check text similarity
                    similarity = SequenceMatcher(
                        None, 
                        entity.text.lower().strip(), 
                        existing.text.lower().strip()
                    ).ratio()
                    
                    if similarity >= similarity_threshold:
                        overlaps = True
                        # Keep the one with higher confidence
                        if entity.confidence_score > existing.confidence_score:
                            deduplicated.remove(existing)
                            deduplicated.append(entity)
                        break
            
            if not overlaps:
                deduplicated.append(entity)
                processed_positions.add(key)
        
        # Sort by position for consistent output (only for entities with positions)
        entities_with_pos = [e for e in deduplicated if e.position]
        entities_without_pos = [e for e in deduplicated if not e.position]
        entities_with_pos.sort(key=lambda e: (e.position.start, e.position.end))
        
        return entities_with_pos + entities_without_pos
    
    def _deduplicate_citations(
        self,
        primary_citations: List[Citation],
        secondary_citations: List[Citation],
        similarity_threshold: float = 0.90
    ) -> List[Citation]:
        """
        Deduplicate citations with position overlap and text similarity detection.
        
        Args:
            primary_citations: Primary list of citations (e.g., regex)
            secondary_citations: Secondary list of citations (e.g., AI-enhanced)
            similarity_threshold: Threshold for text similarity (0.0 to 1.0)
            
        Returns:
            List of deduplicated citations
        """
        from difflib import SequenceMatcher
        
        # Result list
        deduplicated = []
        processed_positions = set()
        
        # First, add all secondary citations (AI has priority)
        for citation in secondary_citations:
            key = (citation.position.start, citation.position.end)
            if key not in processed_positions:
                deduplicated.append(citation)
                processed_positions.add(key)
        
        # Then add primary citations that don't overlap
        for citation in primary_citations:
            # Check for exact position match
            key = (citation.position.start, citation.position.end)
            if key in processed_positions:
                continue
            
            # Check for overlapping positions and similar text
            overlaps = False
            for existing in deduplicated:
                # Check if positions overlap
                if (citation.position.start < existing.position.end and 
                    citation.position.end > existing.position.start):
                    # Check text similarity
                    similarity = SequenceMatcher(
                        None, 
                        citation.original_text.lower().strip(), 
                        existing.original_text.lower().strip()
                    ).ratio()
                    
                    if similarity >= similarity_threshold:
                        overlaps = True
                        # Keep the one with higher confidence
                        if citation.confidence_score > existing.confidence_score:
                            deduplicated.remove(existing)
                            deduplicated.append(citation)
                        break
            
            if not overlaps:
                deduplicated.append(citation)
                processed_positions.add(key)
        
        # Sort by position for consistent output
        deduplicated.sort(key=lambda c: (c.position.start, c.position.end))
        
        return deduplicated
    
    async def _extract_relationships(
        self,
        entities: List[Entity],
        citations: List[Citation],
        text: str,
        document_id: str
    ) -> List[EntityRelationship]:
        """
        Extract relationships between entities and citations.
        
        Args:
            entities: Extracted entities
            citations: Extracted citations
            text: Original text content
            document_id: Document identifier
            
        Returns:
            List[EntityRelationship]: Identified relationships
        """
        try:
            if not self._ai_enhancer or not self._vllm_client:
                return []
            
            relationships = await self._ai_enhancer.extract_relationships(
                entities, citations, text
            )
            
            self.logger.debug(
                f"Extracted {len(relationships)} relationships",
                extra={
                    "event_type": "relationship_extraction",
                    "document_id": document_id,
                    "relationships_found": len(relationships)
                }
            )
            
            return relationships
            
        except Exception as e:
            self.logger.warning(
                f"Relationship extraction failed: {str(e)}",
                extra={
                    "event_type": "relationship_extraction_error",
                    "document_id": document_id,
                    "error": str(e)
                }
            )
            return []
    
    async def _apply_confidence_scoring(
        self,
        entities: List[Entity],
        citations: List[Citation],
        relationships: List[EntityRelationship],
        options: Optional[ExtractionOptions]
    ) -> Tuple[List[Entity], List[Citation], List[EntityRelationship]]:
        """
        Apply confidence scoring to all extracted items.
        
        Args:
            entities: Extracted entities
            citations: Extracted citations
            relationships: Extracted relationships
            options: Extraction options
            
        Returns:
            Tuple of (scored_entities, scored_citations, scored_relationships)
        """
        # Get the extraction strategy if available
        strategy = options.extraction_strategy if options and hasattr(options, 'extraction_strategy') else None
        
        # Apply strategy-aware confidence scoring
        for entity in entities:
            if strategy:
                entity.confidence_score = self._calculate_strategy_confidence(entity, strategy)
            elif entity.confidence_score == 0.0:
                # Fallback to default scoring for non-strategy extractions
                if entity.extraction_method == ExtractionMethod.REGEX_ONLY:
                    entity.confidence_score = 0.8
                elif entity.extraction_method in [ExtractionMethod.AI_DISCOVERED, ExtractionMethod.HYBRID_CONSENSUS]:
                    entity.confidence_score = 0.9
                elif entity.extraction_method in [ExtractionMethod.REGEX_WITH_AI_VALIDATION, ExtractionMethod.REGEX_WITH_AI_ENHANCEMENT]:
                    entity.confidence_score = 0.85
                else:
                    entity.confidence_score = 0.8
        
        for citation in citations:
            if strategy:
                citation.confidence_score = self._calculate_strategy_confidence(citation, strategy)
            elif citation.confidence_score == 0.0:
                if citation.extraction_method == ExtractionMethod.REGEX_ONLY:
                    citation.confidence_score = 0.8
                elif citation.extraction_method in [ExtractionMethod.AI_DISCOVERED, ExtractionMethod.HYBRID_CONSENSUS]:
                    citation.confidence_score = 0.9
                elif citation.extraction_method in [ExtractionMethod.REGEX_WITH_AI_VALIDATION, ExtractionMethod.REGEX_WITH_AI_ENHANCEMENT]:
                    citation.confidence_score = 0.85
                else:
                    citation.confidence_score = 0.8
        
        for relationship in relationships:
            if relationship.confidence_score == 0.0:
                relationship.confidence_score = 0.7  # Relationships are inherently less certain
        
        return entities, citations, relationships
    
    def _calculate_strategy_confidence(
        self, 
        entity: Union[Entity, Citation], 
        strategy: str,
        pass_number: Optional[int] = None
    ) -> float:
        """
        Calculate confidence score based on extraction strategy.
        
        Args:
            entity: Entity or Citation to score
            strategy: Extraction strategy name
            pass_number: Optional pass number for multipass strategy
            
        Returns:
            float: Calculated confidence score
        """
        # Get base confidence from entity if available
        base_confidence = entity.confidence_score if entity.confidence_score > 0 else 0.5
        
        if strategy == ExtractionStrategy.MULTIPASS.value:
            # Multipass: Progressive confidence based on pass number
            if pass_number is not None:
                # Start at 0.3 for pass 1, increase by 0.1 per pass
                return min(0.3 + (pass_number * 0.1), 0.95)
            
            # If no pass number, use metadata to determine pass
            if hasattr(entity, 'attributes') and hasattr(entity.attributes, 'additional_attributes') and entity.attributes.additional_attributes:
                pass_info = entity.attributes.additional_attributes.get('pass', 1)
                return min(0.3 + (pass_info * 0.1), 0.95)
            
            # Default multipass confidence
            return max(base_confidence, 0.65)
        
        elif strategy == ExtractionStrategy.AI_ENHANCED.value:
            # AI-enhanced: Multi-signal weighted scoring
            context_score = 0.85 if hasattr(entity, 'context') and entity.context else 0.5
            
            # Check for linguistic patterns in metadata
            linguistic_score = 0.6  # Default
            if hasattr(entity, 'attributes') and hasattr(entity.attributes, 'additional_attributes') and entity.attributes.additional_attributes:
                if entity.attributes.additional_attributes.get('linguistic_pattern'):
                    linguistic_score = 0.9
                elif entity.attributes.additional_attributes.get('validated'):
                    linguistic_score = 0.8
            
            # Use base confidence as semantic score
            semantic_score = base_confidence
            
            # Get config weights (default to AI_ENHANCED defaults)
            context_weight = 0.3
            linguistic_weight = 0.3
            semantic_weight = 0.4
            
            # Calculate weighted average
            return (
                context_score * context_weight +
                linguistic_score * linguistic_weight +
                semantic_score * semantic_weight
            )
        
        elif strategy == ExtractionStrategy.UNIFIED.value:
            # Unified: Consistent scoring with 0.6 minimum threshold
            # Balance between precision and recall
            if entity.extraction_method == ExtractionMethod.AI_DISCOVERED:
                # AI discoveries get higher confidence in unified mode
                return max(base_confidence, 0.75)
            elif entity.extraction_method == ExtractionMethod.REGEX_ONLY:
                # Regex gets moderate confidence
                return max(base_confidence, 0.65)
            else:
                # Hybrid methods get balanced confidence
                return max(base_confidence, 0.7)
        
        else:
            # Default regex strategy or unknown
            if entity.extraction_method == ExtractionMethod.REGEX_ONLY:
                return max(base_confidence, 0.8)
            else:
                return base_confidence
    
    def _calculate_confidence_distribution(self, items: List[Union[Entity, Citation, EntityRelationship]]) -> Dict[str, int]:
        """
        Calculate confidence score distribution.
        
        Args:
            items: List of extracted items
            
        Returns:
            Dict[str, int]: Confidence distribution by range
        """
        distribution = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0
        }
        
        for item in items:
            score = item.confidence_score
            if score < 0.2:
                distribution["0.0-0.2"] += 1
            elif score < 0.4:
                distribution["0.2-0.4"] += 1
            elif score < 0.6:
                distribution["0.4-0.6"] += 1
            elif score < 0.8:
                distribution["0.6-0.8"] += 1
            else:
                distribution["0.8-1.0"] += 1
        
        return distribution
    
    def _merge_strategy_aware(
        self,
        regex_entities: List[Entity],
        regex_citations: List[Citation],
        ai_entities: List[Entity],
        ai_citations: List[Citation],
        strategy: str
    ) -> Tuple[List[Entity], List[Citation]]:
        """
        Merge results with strategy-specific logic.
        
        Args:
            regex_entities: Entities from regex extraction
            regex_citations: Citations from regex extraction
            ai_entities: Entities from AI processing
            ai_citations: Citations from AI processing
            strategy: Extraction strategy
            
        Returns:
            Tuple of (merged_entities, merged_citations)
        """
        if strategy == ExtractionStrategy.MULTIPASS.value:
            # Multipass: Skip merging, MultiPassExtractor already deduplicates
            # Just combine and return (should mostly be AI entities)
            return ai_entities, ai_citations
        
        elif strategy == ExtractionStrategy.AI_ENHANCED.value:
            # AI-enhanced: Prioritize AI discoveries with higher confidence
            merged_entities = []
            merged_citations = []
            
            # Track which regex items were enhanced by AI
            ai_entity_keys = {(e.text, e.position.start, e.position.end) for e in ai_entities}
            ai_citation_keys = {(c.original_text, c.position.start, c.position.end) for c in ai_citations}
            
            # Add all AI entities (they have priority)
            merged_entities.extend(ai_entities)
            merged_citations.extend(ai_citations)
            
            # Add regex entities that weren't enhanced by AI
            for entity in regex_entities:
                key = (entity.text, entity.position.start, entity.position.end)
                if key not in ai_entity_keys:
                    # Lower confidence for non-AI-enhanced regex
                    entity.confidence_score *= 0.8
                    merged_entities.append(entity)
            
            for citation in regex_citations:
                key = (citation.original_text, citation.position.start, citation.position.end)
                if key not in ai_citation_keys:
                    # Lower confidence for non-AI-enhanced regex
                    citation.confidence_score *= 0.8
                    merged_citations.append(citation)
            
            return merged_entities, merged_citations
        
        elif strategy == ExtractionStrategy.UNIFIED.value:
            # Unified: Balance regex and AI equally
            return self._merge_extraction_results(
                regex_entities, regex_citations, ai_entities, ai_citations
            )
        
        else:
            # Default: Use standard merging
            return self._merge_extraction_results(
                regex_entities, regex_citations, ai_entities, ai_citations
            )
    
    def _get_confidence(self, item) -> float:
        """Safely extract confidence score from dict or object."""
        if isinstance(item, dict):
            return item.get('confidence', item.get('confidence_score', 0.0))
        else:
            return getattr(item, 'confidence_score', getattr(item, 'confidence', 0.0))
    
    def _apply_strategy_filters(
        self,
        entities: List[Entity],
        citations: List[Citation],
        strategy: str,
        config: Optional[Any] = None
    ) -> Tuple[List[Entity], List[Citation]]:
        """
        Apply strategy-specific filtering to entities and citations.
        
        Args:
            entities: Entities to filter
            citations: Citations to filter
            strategy: Extraction strategy
            config: Optional strategy configuration
            
        Returns:
            Tuple of (filtered_entities, filtered_citations)
        """
        if strategy == ExtractionStrategy.MULTIPASS.value:
            # Multipass: Apply pass-specific thresholds
            # Pass 1-3: Lower threshold (0.3-0.5)
            # Pass 4-5: Medium threshold (0.5-0.7)
            # Pass 6-7: Higher threshold (0.7-0.9)
            filtered_entities = []
            filtered_citations = []
            
            for entity in entities:
                pass_num = entity.attributes.additional_attributes.get('pass', 7) if hasattr(entity, 'attributes') and hasattr(entity.attributes, 'additional_attributes') and entity.attributes.additional_attributes else 7
                if pass_num <= 3:
                    threshold = 0.3
                elif pass_num <= 5:
                    threshold = 0.5
                else:
                    threshold = 0.7
                
                if entity.confidence_score >= threshold:
                    filtered_entities.append(entity)
            
            for citation in citations:
                pass_num = citation.components.additional_components.get('pass', '7') if hasattr(citation, 'components') and hasattr(citation.components, 'additional_components') and citation.components.additional_components else 7
                # Convert string pass number to int if needed
                if isinstance(pass_num, str):
                    pass_num = int(pass_num)
                if pass_num <= 3:
                    threshold = 0.3
                elif pass_num <= 5:
                    threshold = 0.5
                else:
                    threshold = 0.7
                
                if citation.confidence_score >= threshold:
                    filtered_citations.append(citation)
            
            return filtered_entities, filtered_citations
        
        elif strategy == ExtractionStrategy.AI_ENHANCED.value:
            # AI-enhanced: Filter by multi-signal score threshold (0.55)
            threshold = 0.55
            filtered_entities = [e for e in entities if e.confidence_score >= threshold]
            filtered_citations = [c for c in citations if c.confidence_score >= threshold]
            return filtered_entities, filtered_citations
        
        elif strategy == ExtractionStrategy.UNIFIED.value:
            # Unified: Apply strict 0.6 minimum confidence
            threshold = 0.6
            filtered_entities = [e for e in entities if self._get_confidence(e) >= threshold]
            filtered_citations = [c for c in citations if self._get_confidence(c) >= threshold]
            return filtered_entities, filtered_citations
        
        else:
            # Default: No additional filtering
            return entities, citations
    
    async def _store_extraction_results(
        self,
        document_id: str,
        entities: List[Entity],
        citations: List[Citation],
        relationships: List[EntityRelationship],
        processing_summary: ProcessingSummary
    ):
        """
        Store extraction results in database.
        
        Args:
            document_id: Document identifier
            entities: Extracted entities
            citations: Extracted citations
            relationships: Extracted relationships
            processing_summary: Processing performance summary
        """
        try:
            if self._supabase_client:
                # Store results in the database
                await self._supabase_client.store_extraction_results(
                    document_id, entities, citations, relationships, processing_summary
                )
                
                self.logger.debug(
                    f"Stored extraction results for document_id: {document_id}",
                    extra={
                        "event_type": "results_stored",
                        "document_id": document_id,
                        "entities_stored": len(entities),
                        "citations_stored": len(citations),
                        "relationships_stored": len(relationships)
                    }
                )
        except Exception as e:
            self.logger.warning(
                f"Failed to store extraction results: {str(e)}",
                extra={
                    "event_type": "storage_error",
                    "document_id": document_id,
                    "error": str(e)
                }
            )
    
    def _update_extraction_stats(self, success: bool, processing_time: int):
        """
        Update internal extraction statistics.
        
        Args:
            success: Whether extraction was successful
            processing_time: Processing time in milliseconds
        """
        self._extraction_stats["total_requests"] += 1
        
        if success:
            self._extraction_stats["successful_extractions"] += 1
        else:
            self._extraction_stats["failed_extractions"] += 1
        
        # Update average processing time
        current_avg = self._extraction_stats["avg_processing_time_ms"]
        total_requests = self._extraction_stats["total_requests"]
        self._extraction_stats["avg_processing_time_ms"] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get service health status and statistics.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "entity-extraction-service",
            "extraction_stats": self._extraction_stats.copy(),
            "dependencies": {
                "pattern_loader": False,  # Deprecated
                "regex_engine": False,  # Deprecated
                "ai_enhancer": self._ai_enhancer is not None,
                "vllm_client": self._vllm_client is not None and self._vllm_client.is_ready(),
                "supabase_client": self._supabase_client is not None
            },
            "configuration": {
                "max_concurrent_extractions": self.settings.extraction.max_concurrent_extractions,
                "processing_timeout_seconds": self.settings.extraction.processing_timeout_seconds,
                "default_extraction_mode": self.settings.extraction.default_extraction_mode,
                "ai_fallback_enabled": self.settings.ai.enable_ai_fallback
            }
        }
        
        # Check vLLM client health
        if self._vllm_client:
            try:
                health_result = await self._vllm_client.health_check()
                health_status["dependencies"]["vllm_client_health"] = health_result
                health_status["dependencies"]["vllm_client_ready"] = self._vllm_client.is_ready()
            except Exception as e:
                health_status["dependencies"]["vllm_client_healthy"] = False
                health_status["dependencies"]["vllm_client_error"] = str(e)
        
        # Check AI enhancer health
        if self._ai_enhancer:
            try:
                ai_health = await self._ai_enhancer.health_check()
                health_status["dependencies"]["ai_enhancer_health"] = ai_health
            except Exception as e:
                health_status["dependencies"]["ai_enhancer_healthy"] = False
                health_status["dependencies"]["ai_enhancer_error"] = str(e)
        
        return health_status
    
    async def _run_pagebatch_extraction(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Run PageBatch extraction strategy with comprehensive page-batch processing.
        
        This strategy processes documents in configurable page batches with ALL 195+ entity types.
        Each batch is processed with full contextualization and cross-batch relationship tracking.
        Optimized for complex documents requiring detailed analysis for knowledge graph construction.
        """
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        self.logger.info(
            f"Starting PageBatch extraction for document_id: {request.document_id}",
            extra={
                "event_type": "pagebatch_extraction_started",
                "request_id": request_id,
                "document_id": request.document_id,
                "strategy": "PAGEBATCH"
            }
        )
        
        try:
            # Get PageBatch configuration
            strategy_config = getattr(request, 'strategy_config', None)
            if strategy_config and hasattr(strategy_config, 'pagebatch_config'):
                config = strategy_config.pagebatch_config or PageBatchConfig()
            else:
                config = PageBatchConfig()
            
            # Process document in page batches
            all_entities = []
            all_relationships = []
            batch_summaries = []
            cross_references = []
            
            # Initialize PageBatch processor with configuration
            processor = PageBatchProcessor(config)
            
            # Process document into intelligent page batches
            page_batches = processor.process_document(
                content=request.text,
                document_metadata={"document_id": request.document_id}
            )
            
            total_batches = len(page_batches)
            self.logger.info(f"Processing {total_batches} intelligent page batches for document {request.document_id}")
            
            # Log batch statistics for debugging
            batch_stats = processor.get_batch_statistics(page_batches)
            self.logger.info(f"Batch statistics: {batch_stats['avg_pages_per_batch']:.1f} pages/batch, "
                           f"{batch_stats['complexity_distribution']}")
            
            # Process each page batch using the comprehensive PageBatch prompt
            for batch in page_batches:
                batch_start_time = time.time()
                
                # Prepare batch context variables using PageBatch data
                batch_variables = {
                    "start_page": batch.start_page,
                    "end_page": batch.end_page, 
                    "total_pages": batch_stats['total_pages'],
                    "document_type": getattr(request, 'document_type', 'legal_document'),
                    "jurisdiction": getattr(request, 'jurisdiction', 'federal'),
                    "page_batch_text": batch.combined_content
                }
                
                # Send batch to prompt service for processing
                try:
                    # Use existing vLLM client (DirectVLLMEngine) with correct method
                    if not self._vllm_client:
                        # Initialize vLLM client if not available
                        from ..client.vllm_direct_client import DirectVLLMEngine
                        self._vllm_client = DirectVLLMEngine()
                    
                    # Load the comprehensive PageBatch prompt template
                    template_path = "/srv/luris/be/entity-extraction-service/src/prompts/strategies/pagebatch/pagebatch_comprehensive.md"
                    
                    try:
                        with open(template_path, 'r') as f:
                            prompt_template = f.read()
                    except FileNotFoundError:
                        self.logger.warning(f"PageBatch prompt template not found at {template_path}, using fallback")
                        prompt_template = """
# PageBatch Legal Entity Extraction - Comprehensive

Extract ALL entities from legal document pages with full contextualization.

## Batch Context
- **Pages**: {{start_page}}-{{end_page}} of {{total_pages}}
- **Document**: {{document_type}} 
- **Jurisdiction**: {{jurisdiction}}

## Page Batch Text
{{page_batch_text}}

## Required JSON Output
{
  "batch_summary": "Brief description of batch content",
  "entities": [
    {
      "text": "exact text span",
      "type": "ENTITY_TYPE", 
      "position": {"start": 0, "end": 10},
      "confidence": 0.95,
      "context": "surrounding text"
    }
  ],
  "relationships": [
    {
      "source": "entity text",
      "target": "related entity", 
      "type": "relationship_type",
      "confidence": 0.9
    }
  ]
}

Extract comprehensive entities with exact positions. Focus on legal significance and relationships.
"""
                    
                    # Replace template variables
                    for key, value in batch_variables.items():
                        prompt_template = prompt_template.replace(f"{{{{{key}}}}}", str(value))
                    
                    # Create VLLMRequest for DirectVLLMEngine
                    from ..client.vllm_direct_client import VLLMRequest
                    vllm_request = VLLMRequest(
                        messages=[{"role": "user", "content": prompt_template}],
                        max_tokens=4000,
                        temperature=0.1,
                        model="qwen3-4b"  # Use default model name for vLLM
                    )
                    
                    # Send to vLLM for processing using correct method
                    vllm_response = await self._vllm_client.generate_chat_completion(vllm_request)
                    batch_response = vllm_response.content if hasattr(vllm_response, 'content') else str(vllm_response)
                    
                    # Parse JSON response
                    batch_result = self._parse_batch_response(batch_response, batch.batch_id)
                    
                    # Add batch results to overall results
                    if batch_result:
                        all_entities.extend(batch_result.get('entities', []))
                        all_relationships.extend(batch_result.get('relationships', []))
                        
                        if batch_result.get('batch_summary'):
                            batch_summaries.append({
                                'batch_id': batch.batch_id,
                                'page_range': batch.page_range,
                                'summary': batch_result['batch_summary'],
                                'entity_count': len(batch_result.get('entities', [])),
                                'word_count': batch.word_count,
                                'complexity': batch.estimated_complexity
                            })
                        
                        if batch_result.get('cross_references'):
                            cross_references.extend(batch_result['cross_references'])
                    
                    batch_time = time.time() - batch_start_time
                    self.logger.info(f"Completed batch {batch.batch_id} ({batch.page_range}) in {batch_time:.2f}s - "
                                   f"{len(batch_result.get('entities', []) if batch_result else [])} entities extracted")
                    
                except Exception as batch_error:
                    self.logger.error(f"Error processing batch {batch.batch_id} ({batch.page_range}): {str(batch_error)}")
                    continue
            
            # Apply confidence filtering
            filtered_entities = [
                entity for entity in all_entities 
                if self._get_confidence(entity) >= config.min_confidence
            ]
            
            # Create processing summary
            total_time = time.time() - start_time
            processing_summary = ProcessingSummary(
                total_processing_time_ms=int(total_time * 1000),
                regex_stage_time_ms=0,
                ai_enhancement_time_ms=int(total_time * 1000),
                entities_found=len(filtered_entities),
                citations_found=0,  # Could be counted from entities
                relationships_found=len(all_relationships),
                ai_enhancements_applied=total_batches,
                processing_stages_completed=[f"PageBatch_{i}" for i in range(total_batches)]
            )
            
            self.logger.info(
                f"PageBatch extraction completed for document {request.document_id}: "
                f"{len(filtered_entities)} entities, {len(all_relationships)} relationships in {total_time:.2f}s"
            )
            
            return ExtractionResponse(
                request_id=request_id,
                document_id=request.document_id,
                entities=filtered_entities,
                citations=[],  # Could be extracted from entities
                relationships=all_relationships,
                processing_summary=processing_summary,
                warnings=[],
                errors=[],
                metadata={
                    "strategy": "PAGEBATCH",
                    "total_batches": total_batches,
                    "batch_summaries": batch_summaries,
                    "cross_references": cross_references,
                    "config": {
                        "batch_size": config.batch_size,
                        "min_confidence": config.min_confidence,
                        "comprehensive_coverage": config.comprehensive_coverage
                    }
                }
            )
            
        except Exception as e:
            error_msg = f"PageBatch extraction failed for document {request.document_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ExtractionResponse(
                request_id=request_id,
                document_id=request.document_id,
                entities=[],
                citations=[],
                relationships=[],
                processing_summary=ProcessingSummary(
                    total_processing_time_ms=int((time.time() - start_time) * 1000),
                    regex_stage_time_ms=0,
                    ai_enhancement_time_ms=int((time.time() - start_time) * 1000),
                    entities_found=0,
                    citations_found=0,
                    relationships_found=0,
                    ai_enhancements_applied=0,
                    processing_stages_completed=[]
                ),
                warnings=[],
                errors=[error_msg],
                metadata={"strategy": "PAGEBATCH", "error": str(e)}
            )
    
    def _parse_batch_response(self, response_text: str, batch_idx: int) -> dict:
        """Parse batch response JSON from vLLM and convert to Entity objects."""
        try:
            import json
            import re
            from ..models.entities import Entity, EntityType, TextPosition, EntityAttributes, ExtractionMethod
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                self.logger.warning(f"No JSON found in batch {batch_idx} response")
                return {}
            
            json_str = json_match.group()
            parsed_json = json.loads(json_str)
            
            # Convert raw entities to Entity objects
            entity_objects = []
            for entity_dict in parsed_json.get('entities', []):
                try:
                    # Map entity type to valid EntityType enum
                    entity_type_str = entity_dict.get('type', 'LEGAL_CONCEPT').upper()
                    
                    # Common entity type mappings
                    type_mapping = {
                        'CASE': 'CASE_CITATION',
                        'STATUTE': 'STATUTE_CITATION', 
                        'REGULATION': 'REGULATION_CITATION',
                        'PERSON': 'PARTY',
                        'ORGANIZATION': 'CORPORATION',
                        'COURT_NAME': 'COURT',
                        'JUDGE_NAME': 'JUDGE',
                        'DATE_VALUE': 'DATE',
                        'LEGAL_TERM': 'LEGAL_CONCEPT'
                    }
                    
                    entity_type_str = type_mapping.get(entity_type_str, entity_type_str)
                    
                    # Try to get valid enum value
                    try:
                        entity_type = EntityType(entity_type_str)
                    except ValueError:
                        # Default to LEGAL_CONCEPT if type is invalid
                        entity_type = EntityType.LEGAL_CONCEPT
                    
                    # Create Entity object
                    position = entity_dict.get('position', {})
                    entity = Entity(
                        text=entity_dict.get('text', ''),
                        cleaned_text=entity_dict.get('text', ''),
                        entity_type=entity_type,
                        entity_subtype=entity_dict.get('subtype', 'unspecified'),
                        position=TextPosition(
                            start=position.get('start', 0),
                            end=position.get('end', 0)
                        ),
                        confidence_score=entity_dict.get('confidence', 0.8),
                        extraction_method=ExtractionMethod.AI_DISCOVERED,
                        context_snippet=entity_dict.get('context', ''),
                        attributes=EntityAttributes(
                            additional_attributes={'batch_id': batch_idx}
                        )
                    )
                    entity_objects.append(entity)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to convert entity in batch {batch_idx}: {e}")
                    continue
            
            # Return modified result with Entity objects
            result = {
                'batch_summary': parsed_json.get('batch_summary', ''),
                'entities': entity_objects,  # Now contains Entity objects
                'relationships': parsed_json.get('relationships', []),
                'cross_references': parsed_json.get('cross_references', [])
            }
            
            self.logger.info(f"Batch {batch_idx} parsed successfully: {len(entity_objects)} entities extracted")
            return result
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from batch {batch_idx}: {str(e)}")
            return {}
        except Exception as e:
            self.logger.error(f"Error parsing batch {batch_idx} response: {str(e)}")
            return {}
    
    async def cleanup(self):
        """Clean up resources and connections."""
        try:
            # Cleanup vLLM client
            if self._vllm_client:
                await self._vllm_client.close()
                self.logger.info("vLLM client shutdown completed")
            
            self.logger.info("ExtractionService cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    @asynccontextmanager
    async def extraction_context(self):
        """Async context manager for extraction operations."""
        try:
            yield self
        finally:
            await self.cleanup()


# Factory function for easy instantiation
def create_extraction_service(settings: Optional[Settings] = None) -> ExtractionService:
    """
    Factory function to create ExtractionService with default configuration.
    
    Args:
        settings: Optional configuration settings
        
    Returns:
        ExtractionService: Configured service instance
    """
    return ExtractionService(settings)