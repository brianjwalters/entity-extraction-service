"""
Optimized parallel chunk processing for entity extraction.
This module provides parallel processing capabilities for the extraction service.
"""

import asyncio
from typing import List, Dict, Any, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChunkResult:
    """Result from processing a single chunk."""
    entities: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    tokens_used: int
    processing_time_ms: float
    chunk_index: int


class ParallelExtractionProcessor:
    """Handles parallel processing of document chunks for entity extraction."""
    
    def __init__(self, multi_pass_extractor, logger=None):
        """Initialize the parallel processor."""
        self.multi_pass_extractor = multi_pass_extractor
        self.logger = logger or logging.getLogger(__name__)
        self.max_concurrent = int(os.environ.get("PERFORMANCE_MAX_CONCURRENT", "8"))
        self.batch_size = int(os.environ.get("CHUNKING_BATCH_SIZE", "8"))
    
    async def process_chunks_parallel(
        self,
        chunks: List[Any],
        request: Any,
        entity_type_mapping: Dict[str, str],
        entity_subtype_mapping: Dict[str, str]
    ) -> Tuple[List[Dict], List[Dict], int]:
        """
        Process multiple chunks in parallel for maximum GPU utilization.
        
        Args:
            chunks: List of document chunks to process
            request: The extraction request object
            entity_type_mapping: Mapping for entity types
            entity_subtype_mapping: Mapping for entity subtypes
            
        Returns:
            Tuple of (all_entities, all_citations, total_tokens)
        """
        import time
        start_time = time.time()
        
        self.logger.info(f"🚀 Starting PARALLEL processing of {len(chunks)} chunks")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Create tasks for all chunks
        tasks = []
        for i, chunk in enumerate(chunks):
            task = self._process_single_chunk_with_semaphore(
                semaphore=semaphore,
                chunk=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                request=request,
                entity_type_mapping=entity_type_mapping,
                entity_subtype_mapping=entity_subtype_mapping
            )
            tasks.append(task)
        
        # Process all chunks in parallel
        self.logger.info(f"⚡ Launching {len(tasks)} parallel extraction tasks")
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        all_entities = []
        all_citations = []
        total_tokens = 0
        successful_chunks = 0
        failed_chunks = 0
        
        for i, result in enumerate(chunk_results):
            if isinstance(result, Exception):
                self.logger.error(f"❌ Chunk {i+1} failed: {str(result)}")
                failed_chunks += 1
                continue
            
            if isinstance(result, ChunkResult):
                all_entities.extend(result.entities)
                all_citations.extend(result.citations)
                total_tokens += result.tokens_used
                successful_chunks += 1
                self.logger.debug(
                    f"✅ Chunk {i+1} completed: {len(result.entities)} entities, "
                    f"{result.tokens_used} tokens, {result.processing_time_ms:.0f}ms"
                )
        
        # Deduplicate entities based on text and type
        unique_entities = self._deduplicate_entities(all_entities)
        unique_citations = self._deduplicate_citations(all_citations)
        
        elapsed_time = (time.time() - start_time) * 1000
        self.logger.info(
            f"🎯 PARALLEL processing complete in {elapsed_time:.0f}ms: "
            f"{successful_chunks}/{len(chunks)} chunks successful, "
            f"{len(unique_entities)} unique entities, "
            f"{len(unique_citations)} unique citations, "
            f"{total_tokens} total tokens"
        )
        
        # Calculate speedup
        if successful_chunks > 0:
            avg_chunk_time = elapsed_time / successful_chunks
            sequential_estimate = avg_chunk_time * len(chunks)
            speedup = sequential_estimate / elapsed_time
            self.logger.info(f"⚡ Parallel speedup: {speedup:.1f}x faster than sequential")
        
        return unique_entities, unique_citations, total_tokens
    
    async def _process_single_chunk_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
        request: Any,
        entity_type_mapping: Dict[str, str],
        entity_subtype_mapping: Dict[str, str]
    ) -> ChunkResult:
        """Process a single chunk with semaphore control."""
        async with semaphore:
            return await self._process_single_chunk(
                chunk, chunk_index, total_chunks, request,
                entity_type_mapping, entity_subtype_mapping
            )
    
    async def _process_single_chunk(
        self,
        chunk: Any,
        chunk_index: int,
        total_chunks: int,
        request: Any,
        entity_type_mapping: Dict[str, str],
        entity_subtype_mapping: Dict[str, str]
    ) -> ChunkResult:
        """Process a single chunk and return results."""
        import time
        start_time = time.time()
        
        self.logger.debug(
            f"Processing chunk {chunk_index+1}/{total_chunks} "
            f"(chars {chunk.start_pos}-{chunk.end_pos})"
        )
        
        try:
            # Run extraction on this chunk
            entities_matches, metrics = await self.multi_pass_extractor.extract_multi_pass(
                chunk_id=f"{request.document_id}_chunk_{chunk_index}",
                chunk_content=chunk.text,
                document_id=request.document_id,
                chunk_index=chunk_index,
                whole_document=request.text,
                selected_passes=None,
                parallel_execution=True
            )
            
            # Process entities
            processed_entities = []
            processed_citations = []
            
            for match in entities_matches:
                # Adjust positions to document level
                if hasattr(match, 'position') and match.position:
                    match.position['start'] += chunk.start_pos
                    match.position['end'] += chunk.start_pos
                
                # Map entity types
                entity_type = str(match.entity_type).upper() if hasattr(match, 'entity_type') else 'OTHER'
                mapped_type = entity_type_mapping.get(entity_type, entity_type)
                mapped_subtype = entity_subtype_mapping.get(mapped_type, 'other')
                
                # Create entity dict
                entity_dict = {
                    'text': match.text if hasattr(match, 'text') else '',
                    'entity_type': mapped_type,
                    'entity_subtype': mapped_subtype,
                    'confidence_score': getattr(match, 'confidence_score', 0.85),
                    'position': getattr(match, 'position', None),
                    'chunk_index': str(chunk_index)
                }
                
                # Check if it's a citation
                if mapped_type in ['CASE_CITATION', 'STATUTE', 'REGULATION', 'CITATION']:
                    processed_citations.append(entity_dict)
                else:
                    processed_entities.append(entity_dict)
            
            processing_time = (time.time() - start_time) * 1000
            tokens_used = metrics.get('total_tokens', 0) if metrics else 0
            
            return ChunkResult(
                entities=processed_entities,
                citations=processed_citations,
                tokens_used=tokens_used,
                processing_time_ms=processing_time,
                chunk_index=chunk_index
            )
            
        except Exception as e:
            self.logger.error(f"Error processing chunk {chunk_index+1}: {str(e)}")
            raise
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on text and type."""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.get('text', '').lower(), entity.get('entity_type', ''))
            if key not in seen and key[0]:  # Skip empty text
                seen.add(key)
                unique.append(entity)
        
        return unique
    
    def _deduplicate_citations(self, citations: List[Dict]) -> List[Dict]:
        """Remove duplicate citations based on text."""
        seen = set()
        unique = []
        
        for citation in citations:
            text = citation.get('text', '').lower()
            if text and text not in seen:
                seen.add(text)
                unique.append(citation)
        
        return unique


# Import for environment variables
import os