"""
Extraction Orchestrator Module

This module orchestrates the extraction process across multiple document chunks,
handling parallel processing, strategy testing, and result coordination.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx
import json
from pathlib import Path

from .token_estimator import TokenEstimator, TokenEstimate
from .document_chunker import DocumentChunker, DocumentChunk
from .vllm_monitor import VLLMMonitor, ServiceStatus, FailureType


class ExtractionStrategy(Enum):
    """Available extraction strategies."""
    MULTIPASS = "multipass"
    AI_ENHANCED = "ai_enhanced"
    UNIFIED = "unified"


@dataclass
class ChunkExtractionResult:
    """Result from extracting a single chunk."""
    chunk_index: int
    strategy: ExtractionStrategy
    entities: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    extraction_mode: str
    ai_used: bool
    processing_time_ms: float
    chunk_size_chars: int
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if extraction was successful."""
        return self.error is None and self.extraction_mode != "regex_only"


@dataclass
class DocumentExtractionResult:
    """Complete extraction result for a document."""
    document_path: str
    document_size_chars: int
    token_estimate: TokenEstimate
    chunks_created: int
    strategy: ExtractionStrategy
    total_entities: int
    total_citations: int
    unique_entities: int
    unique_citations: int
    extraction_mode: str
    ai_enhancement_rate: float
    total_processing_time_ms: float
    chunk_results: List[ChunkExtractionResult]
    merged_entities: List[Dict[str, Any]]
    merged_citations: List[Dict[str, Any]]
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if document extraction was successful."""
        return self.error is None and self.extraction_mode != "regex_only"
    
    @property
    def average_chunk_time_ms(self) -> float:
        """Calculate average processing time per chunk."""
        if not self.chunk_results:
            return 0
        return sum(c.processing_time_ms for c in self.chunk_results) / len(self.chunk_results)


class ExtractionOrchestrator:
    """
    Orchestrate extraction process across document chunks.
    
    This orchestrator:
    - Manages parallel chunk processing
    - Tests multiple extraction strategies
    - Monitors for vLLM failures
    - Coordinates result merging
    - Tracks performance metrics
    """
    
    # API endpoints
    EXTRACTION_API = "http://localhost:8007/api/v1"
    
    # Concurrency settings
    MAX_CONCURRENT_CHUNKS = 5
    CHUNK_TIMEOUT_SECONDS = 60
    
    def __init__(
        self,
        token_estimator: Optional[TokenEstimator] = None,
        document_chunker: Optional[DocumentChunker] = None,
        vllm_monitor: Optional[VLLMMonitor] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            token_estimator: Token estimation module
            document_chunker: Document chunking module
            vllm_monitor: vLLM health monitor
            logger: Optional logger instance
        """
        self.token_estimator = token_estimator or TokenEstimator()
        self.document_chunker = document_chunker or DocumentChunker()
        self.vllm_monitor = vllm_monitor or VLLMMonitor()
        self.logger = logger or logging.getLogger(__name__)
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=self.CHUNK_TIMEOUT_SECONDS)
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_CHUNKS)
        
        # Tracking
        self.stop_processing = False  # Emergency stop if regex_only detected
    
    async def extract_from_document(
        self,
        document_path: str,
        document_text: str,
        strategy: ExtractionStrategy,
        force_chunking: bool = False
    ) -> DocumentExtractionResult:
        """
        Extract entities from a document using specified strategy.
        
        Args:
            document_path: Path to the document
            document_text: Document text content
            strategy: Extraction strategy to use
            force_chunking: Force chunking even for small documents
            
        Returns:
            DocumentExtractionResult with complete extraction data
        """
        start_time = time.time()
        self.stop_processing = False
        
        try:
            # Pre-flight health check
            health = await self.vllm_monitor.check_health()
            if health.status == ServiceStatus.FAILED:
                self.logger.error("vLLM service is not healthy!")
                
                # Attempt troubleshooting
                troubleshoot = await self.vllm_monitor.troubleshoot_failure()
                if not troubleshoot.resolution_successful:
                    return DocumentExtractionResult(
                        document_path=document_path,
                        document_size_chars=len(document_text),
                        token_estimate=self.token_estimator.estimate_document_tokens(document_text),
                        chunks_created=0,
                        strategy=strategy,
                        total_entities=0,
                        total_citations=0,
                        unique_entities=0,
                        unique_citations=0,
                        extraction_mode="failed",
                        ai_enhancement_rate=0.0,
                        total_processing_time_ms=(time.time() - start_time) * 1000,
                        chunk_results=[],
                        merged_entities=[],
                        merged_citations=[],
                        error="vLLM service failure - cannot proceed",
                        metadata={"troubleshooting": troubleshoot.steps_taken}
                    )
            
            # Estimate tokens
            token_estimate = self.token_estimator.estimate_document_tokens(document_text)
            self.logger.info(
                f"Document: {Path(document_path).name}, "
                f"Size: {len(document_text):,} chars, "
                f"Estimated tokens: {token_estimate.estimated_tokens:,}, "
                f"Chunks needed: {token_estimate.chunks_needed}"
            )
            
            # Create chunks if needed
            chunks = self.document_chunker.chunk_document(
                document_text,
                estimated_tokens=token_estimate.estimated_tokens,
                force_chunking=force_chunking or token_estimate.requires_chunking
            )
            
            self.logger.info(f"Created {len(chunks)} chunks for processing")
            
            # Process chunks
            chunk_results = await self._process_chunks(chunks, strategy)
            
            # Check for regex_only fallback
            if self.stop_processing:
                return DocumentExtractionResult(
                    document_path=document_path,
                    document_size_chars=len(document_text),
                    token_estimate=token_estimate,
                    chunks_created=len(chunks),
                    strategy=strategy,
                    total_entities=0,
                    total_citations=0,
                    unique_entities=0,
                    unique_citations=0,
                    extraction_mode="regex_only",
                    ai_enhancement_rate=0.0,
                    total_processing_time_ms=(time.time() - start_time) * 1000,
                    chunk_results=chunk_results,
                    merged_entities=[],
                    merged_citations=[],
                    error="Extraction fell back to regex_only - vLLM failure detected",
                    metadata={"stop_reason": "regex_only_detected"}
                )
            
            # Merge results
            merged_entities, merged_citations = self._merge_chunk_results(chunk_results)
            
            # Calculate metrics
            total_entities = sum(len(r.entities) for r in chunk_results)
            total_citations = sum(len(r.citations) for r in chunk_results)
            ai_chunks = sum(1 for r in chunk_results if r.ai_used)
            ai_enhancement_rate = (ai_chunks / len(chunk_results)) * 100 if chunk_results else 0
            
            # Determine overall extraction mode
            extraction_modes = [r.extraction_mode for r in chunk_results]
            if all(m == "regex_only" for m in extraction_modes):
                overall_mode = "regex_only"
            elif any(m == "regex_only" for m in extraction_modes):
                overall_mode = "partial_ai"
            else:
                overall_mode = "ai_enhanced"
            
            return DocumentExtractionResult(
                document_path=document_path,
                document_size_chars=len(document_text),
                token_estimate=token_estimate,
                chunks_created=len(chunks),
                strategy=strategy,
                total_entities=total_entities,
                total_citations=total_citations,
                unique_entities=len(merged_entities),
                unique_citations=len(merged_citations),
                extraction_mode=overall_mode,
                ai_enhancement_rate=ai_enhancement_rate,
                total_processing_time_ms=(time.time() - start_time) * 1000,
                chunk_results=chunk_results,
                merged_entities=merged_entities,
                merged_citations=merged_citations,
                metadata={
                    "chunks_processed": len(chunk_results),
                    "parallel_processing": len(chunks) > 1
                }
            )
            
        except Exception as e:
            self.logger.error(f"Document extraction failed: {e}")
            return DocumentExtractionResult(
                document_path=document_path,
                document_size_chars=len(document_text),
                token_estimate=self.token_estimator.estimate_document_tokens(document_text),
                chunks_created=0,
                strategy=strategy,
                total_entities=0,
                total_citations=0,
                unique_entities=0,
                unique_citations=0,
                extraction_mode="failed",
                ai_enhancement_rate=0.0,
                total_processing_time_ms=(time.time() - start_time) * 1000,
                chunk_results=[],
                merged_entities=[],
                merged_citations=[],
                error=str(e)
            )
    
    async def _process_chunks(
        self,
        chunks: List[DocumentChunk],
        strategy: ExtractionStrategy
    ) -> List[ChunkExtractionResult]:
        """
        Process multiple chunks in parallel.
        
        Args:
            chunks: List of document chunks
            strategy: Extraction strategy to use
            
        Returns:
            List of chunk extraction results
        """
        if len(chunks) == 1:
            # Single chunk - process directly
            result = await self._process_single_chunk(chunks[0], strategy)
            return [result]
        
        # Multiple chunks - process in parallel with concurrency limit
        tasks = []
        for chunk in chunks:
            task = self._process_single_chunk(chunk, strategy)
            tasks.append(task)
        
        # Process with concurrency control
        results = []
        for i in range(0, len(tasks), self.MAX_CONCURRENT_CHUNKS):
            batch = tasks[i:i + self.MAX_CONCURRENT_CHUNKS]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Chunk processing failed: {result}")
                    # Create error result
                    results.append(ChunkExtractionResult(
                        chunk_index=i,
                        strategy=strategy,
                        entities=[],
                        citations=[],
                        extraction_mode="failed",
                        ai_used=False,
                        processing_time_ms=0,
                        chunk_size_chars=0,
                        error=str(result)
                    ))
                else:
                    results.append(result)
                    
                    # Check for regex_only fallback
                    if result.extraction_mode == "regex_only":
                        self.logger.error(
                            f"🚨 CRITICAL: Chunk {result.chunk_index} returned regex_only mode! "
                            "Stopping all processing - vLLM service has failed!"
                        )
                        self.stop_processing = True
                        break
            
            if self.stop_processing:
                break
        
        return results
    
    async def _process_single_chunk(
        self,
        chunk: DocumentChunk,
        strategy: ExtractionStrategy
    ) -> ChunkExtractionResult:
        """
        Process a single document chunk.
        
        Args:
            chunk: Document chunk to process
            strategy: Extraction strategy to use
            
        Returns:
            ChunkExtractionResult with extraction data
        """
        async with self.semaphore:  # Limit concurrent requests
            start_time = time.time()
            
            try:
                # Prepare extraction request
                request_data = {
                    "document_id": f"test_chunk_{chunk.chunk_index}",
                    "content": chunk.text,
                    "extraction_strategy": strategy.value,
                    "options": {
                        "confidence_threshold": 0.7,
                        "include_positions": True,
                        "include_context": True
                    }
                }
                
                # Send extraction request
                response = await self.client.post(
                    f"{self.EXTRACTION_API}/extract",
                    json=request_data
                )
                
                if response.status_code != 200:
                    raise Exception(f"Extraction failed with status {response.status_code}: {response.text}")
                
                result_data = response.json()
                
                # Extract key metrics
                extraction_mode = result_data.get("extraction_mode", "unknown")
                ai_status = result_data.get("ai_enhancement_status", {})
                ai_used = ai_status.get("ai_used", False)
                
                # Check for regex_only fallback
                if extraction_mode == "regex_only":
                    self.logger.error(f"Chunk {chunk.chunk_index} fell back to regex_only!")
                
                return ChunkExtractionResult(
                    chunk_index=chunk.chunk_index,
                    strategy=strategy,
                    entities=result_data.get("entities", []),
                    citations=result_data.get("citations", []),
                    extraction_mode=extraction_mode,
                    ai_used=ai_used,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    chunk_size_chars=chunk.char_count,
                    metadata={
                        "chunk_boundaries": chunk.metadata.get("boundary_type"),
                        "has_overlap": chunk.has_overlap,
                        "ai_status": ai_status
                    }
                )
                
            except Exception as e:
                self.logger.error(f"Failed to process chunk {chunk.chunk_index}: {e}")
                return ChunkExtractionResult(
                    chunk_index=chunk.chunk_index,
                    strategy=strategy,
                    entities=[],
                    citations=[],
                    extraction_mode="failed",
                    ai_used=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    chunk_size_chars=chunk.char_count,
                    error=str(e)
                )
    
    def _merge_chunk_results(
        self,
        chunk_results: List[ChunkExtractionResult]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Merge and deduplicate results from multiple chunks.
        
        Args:
            chunk_results: List of chunk extraction results
            
        Returns:
            Tuple of (merged_entities, merged_citations)
        """
        # Collect all entities and citations
        all_entities = []
        all_citations = []
        
        for result in chunk_results:
            # Add chunk index to each item for tracking
            for entity in result.entities:
                entity_copy = entity.copy()
                entity_copy["source_chunk"] = result.chunk_index
                all_entities.append(entity_copy)
            
            for citation in result.citations:
                citation_copy = citation.copy()
                citation_copy["source_chunk"] = result.chunk_index
                all_citations.append(citation_copy)
        
        # Deduplicate entities
        unique_entities = self._deduplicate_items(all_entities, ["text", "entity_type"])
        
        # Deduplicate citations
        unique_citations = self._deduplicate_items(all_citations, ["original_text"])
        
        self.logger.info(
            f"Merging complete: {len(all_entities)} → {len(unique_entities)} entities, "
            f"{len(all_citations)} → {len(unique_citations)} citations"
        )
        
        return unique_entities, unique_citations
    
    def _deduplicate_items(
        self,
        items: List[Dict[str, Any]],
        key_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate items based on key fields.
        
        Args:
            items: List of items to deduplicate
            key_fields: Fields to use for deduplication key
            
        Returns:
            List of unique items
        """
        seen = {}
        unique = []
        
        for item in items:
            # Create deduplication key
            key_values = []
            for field in key_fields:
                value = item.get(field, "")
                if isinstance(value, str):
                    value = value.lower().strip()
                key_values.append(str(value))
            
            key = "|".join(key_values)
            
            if key not in seen:
                seen[key] = item
                unique.append(item)
            else:
                # Merge metadata from duplicate
                existing = seen[key]
                
                # Track all source chunks
                existing_chunks = existing.get("source_chunks", [existing.get("source_chunk")])
                new_chunk = item.get("source_chunk")
                if new_chunk not in existing_chunks:
                    existing_chunks.append(new_chunk)
                existing["source_chunks"] = existing_chunks
                
                # Take higher confidence score if available
                if "confidence_score" in item and "confidence_score" in existing:
                    existing["confidence_score"] = max(
                        existing["confidence_score"],
                        item["confidence_score"]
                    )
        
        return unique
    
    async def test_all_strategies(
        self,
        document_path: str,
        document_text: str
    ) -> Dict[ExtractionStrategy, DocumentExtractionResult]:
        """
        Test all extraction strategies on a document.
        
        Args:
            document_path: Path to the document
            document_text: Document text content
            
        Returns:
            Dictionary mapping strategy to extraction result
        """
        results = {}
        
        for strategy in ExtractionStrategy:
            self.logger.info(f"\nTesting strategy: {strategy.value}")
            
            result = await self.extract_from_document(
                document_path,
                document_text,
                strategy
            )
            
            results[strategy] = result
            
            # Stop if regex_only detected
            if result.extraction_mode == "regex_only":
                self.logger.error(
                    f"🚨 Stopping all tests - regex_only mode detected with {strategy.value}!"
                )
                break
        
        return results
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


if __name__ == "__main__":
    # Test the orchestrator
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_orchestrator():
        # Create test document
        test_doc = "This is a test document. " * 10000  # Large document
        
        async with ExtractionOrchestrator() as orchestrator:
            result = await orchestrator.extract_from_document(
                "test_document.txt",
                test_doc,
                ExtractionStrategy.UNIFIED,
                force_chunking=True
            )
            
            print(f"\nExtraction Result:")
            print(f"  Document size: {result.document_size_chars:,} chars")
            print(f"  Chunks created: {result.chunks_created}")
            print(f"  Total entities: {result.total_entities}")
            print(f"  Unique entities: {result.unique_entities}")
            print(f"  Extraction mode: {result.extraction_mode}")
            print(f"  AI enhancement rate: {result.ai_enhancement_rate:.1f}%")
            print(f"  Processing time: {result.total_processing_time_ms:.1f}ms")
            
            if result.error:
                print(f"  ❌ Error: {result.error}")
    
    asyncio.run(test_orchestrator())