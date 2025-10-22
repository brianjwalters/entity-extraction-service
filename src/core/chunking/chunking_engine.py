"""
Core chunking engine for the Chunking Service.

Provides intelligent document chunking with multiple strategies.
"""

import asyncio
import uuid
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from ..models.requests import ChunkingStrategy, DocumentToChunk
from ..models.responses import DocumentChunk, ChunkingStatus, BatchChunkingStatus
from .cache_manager import CacheManager
from .chunking_strategies import (
    SimpleChunker,
    SemanticChunker,
    HybridChunker,
    LegalChunker,
    MarkdownChunker,
    LegalDensityAdaptiveChunker,
    ExtractionChunker
)
from .anthropic_contextual_enhancer import AnthropicContextualEnhancer

logger = logging.getLogger(__name__)


class ChunkingEngine:
    """Main chunking engine that coordinates different chunking strategies."""
    
    def __init__(self, settings, cache_manager: Optional[CacheManager] = None, prompt_client=None, supabase_client=None):
        self.settings = settings
        self.cache_manager = cache_manager
        self.chunkers = {}
        self.batch_operations: Dict[str, Dict[str, Any]] = {}
        self._batch_lock = asyncio.Lock()

        # Phase 3: Contextual Enhancement
        self.contextual_enhancer = None
        self.prompt_client = prompt_client
        self.enable_contextual_enhancement = getattr(settings, 'enable_contextual_enhancement', True)

        # GraphRAG Integration: Database storage for chunks
        self.supabase_client = supabase_client
        self.enable_graph_storage = getattr(settings, 'enable_graph_storage', True)
        
    async def initialize(self):
        """Initialize the chunking engine and all strategies with fail-safe protection."""
        logger.info("Initializing ChunkingEngine with fail-safe protection...")
        
        # Start with guaranteed working chunkers
        self.chunkers = {
            ChunkingStrategy.SIMPLE: SimpleChunker(self.settings),
            ChunkingStrategy.MARKDOWN: MarkdownChunker(self.settings),
            ChunkingStrategy.EXTRACTION: ExtractionChunker(self.settings)
        }
        
        # Initialize basic chunkers first
        await self._initialize_basic_chunkers()
        
        # Add advanced chunkers with timeout protection
        await self._initialize_advanced_chunkers_safely()
        
        # Anthropic Contextual Enhancement (uses vLLM directly, no PromptClient needed)
        if self.enable_contextual_enhancement:
            try:
                logger.info("Initializing AnthropicContextualEnhancer with vLLM integration...")
                self.contextual_enhancer = AnthropicContextualEnhancer(
                    config={},  # Uses default vLLM URL from our fix: 10.10.0.87:8080
                    max_chunk_tokens=8000,
                    standard_chunk_tokens=512
                )
                await self.contextual_enhancer.initialize()
                logger.info("✅ AnthropicContextualEnhancer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AnthropicContextualEnhancer: {e}")
                self.enable_contextual_enhancement = False
                
        logger.info("ChunkingEngine initialization complete")
    
    async def _initialize_basic_chunkers(self):
        """Initialize basic chunkers that should always work."""
        basic_strategies = [ChunkingStrategy.SIMPLE, ChunkingStrategy.MARKDOWN, ChunkingStrategy.EXTRACTION]
        
        for strategy in basic_strategies:
            chunker = self.chunkers.get(strategy)
            if chunker:
                try:
                    await asyncio.wait_for(chunker.initialize(), timeout=5.0)
                    logger.info(f"✅ Initialized {strategy} chunker")
                except asyncio.TimeoutError:
                    logger.error(f"❌ {strategy} chunker initialization timed out")
                    del self.chunkers[strategy]
                except Exception as e:
                    logger.error(f"❌ Failed to initialize {strategy} chunker: {e}")
                    del self.chunkers[strategy]
    
    async def _initialize_advanced_chunkers_safely(self):
        """Initialize advanced chunkers with timeout and fallback protection."""
        logger.info("🚀 Initializing advanced chunkers with dependency fixes...")
        
        # Advanced chunkers with proper error handling
        advanced_chunkers = [
            (ChunkingStrategy.SEMANTIC, SemanticChunker),
            (ChunkingStrategy.HYBRID, HybridChunker), 
            (ChunkingStrategy.LEGAL, LegalChunker),
            (ChunkingStrategy.LEGAL_DENSITY_ADAPTIVE, LegalDensityAdaptiveChunker)
        ]
        
        for strategy, chunker_class in advanced_chunkers:
            try:
                logger.info(f"🔧 Initializing {strategy.value} chunker...")
                
                # Create chunker with timeout protection
                chunker = await asyncio.wait_for(
                    self._create_chunker_safely(chunker_class, self.settings),
                    timeout=20.0  # 20 second timeout per chunker creation
                )
                
                if chunker:
                    # Initialize chunker with extended timeout for spaCy model loading
                    await asyncio.wait_for(chunker.initialize(), timeout=30.0)  # Extended to 30 seconds
                    self.chunkers[strategy] = chunker
                    logger.info(f"✅ {strategy.value} chunker initialized successfully")
                else:
                    logger.warning(f"⚠️ Failed to create {strategy.value} chunker")
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ {strategy.value} chunker initialization timed out, skipping")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize {strategy.value} chunker: {e}")
        
        working_chunkers = list(self.chunkers.keys())
        logger.info(f"🎯 ChunkingEngine initialized with {len(working_chunkers)} strategies: {[s.value for s in working_chunkers]}")
    
    async def _create_chunker_safely(self, chunker_class, settings):
        """Create a chunker instance safely with error handling."""
        try:
            # Run chunker creation in thread pool to prevent blocking
            def create_chunker():
                return chunker_class(settings)
            
            # Use run_in_executor to prevent blocking the event loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, create_chunker)
        except Exception as e:
            logger.warning(f"Failed to create {chunker_class.__name__}: {e}")
            return None
        
    async def chunk_text(
        self,
        text: str,
        strategy: str = "semantic",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk text using the specified strategy.
        
        Args:
            text: Text to chunk
            strategy: Chunking strategy to use
            chunk_size: Target chunk size (None for default)
            chunk_overlap: Overlap between chunks (None for default)
            metadata: Additional metadata
            
        Returns:
            List of DocumentChunk objects
        """
        try:
            # Validate inputs
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
                
            if len(text) > self.settings.max_document_size_mb * 1024 * 1024:
                raise ValueError(f"Document exceeds maximum size of {self.settings.max_document_size_mb}MB")
            
            # Use defaults if not specified
            chunk_size = chunk_size or self.settings.default_chunk_size
            chunk_overlap = chunk_overlap or self.settings.default_chunk_overlap
            
            # Validate chunk parameters
            if chunk_size > self.settings.max_chunk_size:
                chunk_size = self.settings.max_chunk_size
            elif chunk_size < self.settings.min_chunk_size:
                chunk_size = self.settings.min_chunk_size
                
            if chunk_overlap >= chunk_size:
                chunk_overlap = min(chunk_overlap, chunk_size // 2)
            
            # Check cache if enabled
            cache_key = None
            if self.cache_manager:
                cache_key = self._generate_cache_key(text, strategy, chunk_size, chunk_overlap)
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for chunking request")
                    return cached_result
            
            # Get the appropriate chunker
            chunker_strategy = ChunkingStrategy(strategy)
            chunker = self.chunkers.get(chunker_strategy)
            if not chunker:
                # Fallback to simple chunker if requested strategy unavailable
                logger.warning(f"Chunking strategy '{strategy}' not available, falling back to 'simple'")
                chunker_strategy = ChunkingStrategy.SIMPLE
                chunker = self.chunkers.get(chunker_strategy)
                if not chunker:
                    raise ValueError(f"Critical error: Simple chunker not available")
            
            # Perform chunking
            chunks = await chunker.chunk_text(
                text=text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                metadata=metadata
            )
            
            # Validate and enhance chunks
            enhanced_chunks = await self._enhance_chunks(chunks, text, metadata)
            
            # Cache result if enabled
            if self.cache_manager and cache_key:
                await self.cache_manager.set(cache_key, enhanced_chunks)
            
            logger.info(f"Successfully chunked text into {len(enhanced_chunks)} chunks using {strategy} strategy")
            return enhanced_chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {e}")
            raise
    
    async def start_batch_chunking(
        self,
        documents: List[DocumentToChunk],
        default_strategy: str = "semantic",
        default_chunk_size: int = 1000,
        default_chunk_overlap: int = 200
    ) -> str:
        """
        Start batch chunking operation.
        
        Returns:
            Batch ID for tracking progress
        """
        batch_id = str(uuid.uuid4())
        
        async with self._batch_lock:
            self.batch_operations[batch_id] = {
                "status": ChunkingStatus.PENDING,
                "total_documents": len(documents),
                "processed_documents": 0,
                "failed_documents": 0,
                "results": {},
                "created_at": datetime.utcnow(),
                "started_at": None,
                "completed_at": None,
                "error_message": None
            }
        
        # Start background processing
        asyncio.create_task(self._process_batch(
            batch_id, documents, default_strategy, default_chunk_size, default_chunk_overlap
        ))
        
        logger.info(f"Started batch chunking operation: {batch_id}")
        return batch_id
    
    async def get_batch_status(self, batch_id: str) -> Optional[BatchChunkingStatus]:
        """Get status of batch chunking operation."""
        async with self._batch_lock:
            batch_info = self.batch_operations.get(batch_id)
            if not batch_info:
                return None
            
            progress_percentage = 0.0
            if batch_info["total_documents"] > 0:
                progress_percentage = (batch_info["processed_documents"] / batch_info["total_documents"]) * 100
            
            return BatchChunkingStatus(
                batch_id=batch_id,
                status=batch_info["status"],
                total_documents=batch_info["total_documents"],
                processed_documents=batch_info["processed_documents"],
                failed_documents=batch_info["failed_documents"],
                progress_percentage=progress_percentage,
                created_at=batch_info["created_at"],
                started_at=batch_info.get("started_at"),
                completed_at=batch_info.get("completed_at"),
                error_message=batch_info.get("error_message")
            )
    
    async def get_batch_results(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get results of completed batch operation."""
        async with self._batch_lock:
            batch_info = self.batch_operations.get(batch_id)
            if not batch_info or batch_info["status"] != ChunkingStatus.COMPLETED:
                return None
            
            return {
                "batch_id": batch_id,
                "status": batch_info["status"],
                "results": batch_info["results"],
                "summary": {
                    "total_documents": batch_info["total_documents"],
                    "processed_documents": batch_info["processed_documents"],
                    "failed_documents": batch_info["failed_documents"],
                    "success_rate": batch_info["processed_documents"] / batch_info["total_documents"]
                },
                "created_at": batch_info["created_at"],
                "completed_at": batch_info["completed_at"]
            }
    
    async def cancel_batch_chunking(self, batch_id: str) -> bool:
        """Cancel a batch chunking operation."""
        async with self._batch_lock:
            batch_info = self.batch_operations.get(batch_id)
            if not batch_info:
                return False
                
            if batch_info["status"] in [ChunkingStatus.COMPLETED, ChunkingStatus.FAILED, ChunkingStatus.CANCELLED]:
                return False
                
            batch_info["status"] = ChunkingStatus.CANCELLED
            batch_info["completed_at"] = datetime.utcnow()
            logger.info(f"Cancelled batch chunking operation: {batch_id}")
            return True
    
    async def shutdown(self):
        """Shutdown the chunking engine."""
        logger.info("Shutting down ChunkingEngine...")
        
        # Cancel all pending batch operations
        async with self._batch_lock:
            for batch_id, batch_info in self.batch_operations.items():
                if batch_info["status"] in [ChunkingStatus.PENDING, ChunkingStatus.PROCESSING]:
                    batch_info["status"] = ChunkingStatus.CANCELLED
                    batch_info["completed_at"] = datetime.utcnow()
        
        # Shutdown chunkers
        for chunker in self.chunkers.values():
            if hasattr(chunker, 'shutdown'):
                await chunker.shutdown()
                
        logger.info("ChunkingEngine shutdown complete")
    
    async def _process_batch(
        self,
        batch_id: str,
        documents: List[DocumentToChunk],
        default_strategy: str,
        default_chunk_size: int,
        default_chunk_overlap: int
    ):
        """Process documents in batch."""
        try:
            async with self._batch_lock:
                self.batch_operations[batch_id]["status"] = ChunkingStatus.PROCESSING
                self.batch_operations[batch_id]["started_at"] = datetime.utcnow()
            
            # Process documents with concurrency limit
            semaphore = asyncio.Semaphore(self.settings.max_concurrent_chunks)
            tasks = []
            
            for document in documents:
                task = asyncio.create_task(self._process_single_document(
                    semaphore, batch_id, document, default_strategy, default_chunk_size, default_chunk_overlap
                ))
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update final status
            async with self._batch_lock:
                batch_info = self.batch_operations[batch_id]
                if batch_info["status"] != ChunkingStatus.CANCELLED:
                    batch_info["status"] = ChunkingStatus.COMPLETED
                batch_info["completed_at"] = datetime.utcnow()
                
        except Exception as e:
            async with self._batch_lock:
                self.batch_operations[batch_id]["status"] = ChunkingStatus.FAILED
                self.batch_operations[batch_id]["error_message"] = str(e)
                self.batch_operations[batch_id]["completed_at"] = datetime.utcnow()
            logger.error(f"Batch processing failed for {batch_id}: {e}")
    
    async def _process_single_document(
        self,
        semaphore: asyncio.Semaphore,
        batch_id: str,
        document: DocumentToChunk,
        default_strategy: str,
        default_chunk_size: int,
        default_chunk_overlap: int
    ):
        """Process a single document in the batch."""
        async with semaphore:
            try:
                # Use document-specific settings or defaults
                strategy = document.strategy or default_strategy
                chunk_size = document.chunk_size or default_chunk_size
                chunk_overlap = document.chunk_overlap or default_chunk_overlap
                
                # Chunk the document
                chunks = await self.chunk_text(
                    text=document.text,
                    strategy=strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    metadata=document.metadata
                )
                
                # Store result
                async with self._batch_lock:
                    self.batch_operations[batch_id]["results"][document.document_id] = {
                        "status": ChunkingStatus.COMPLETED,
                        "chunks": chunks,
                        "chunk_count": len(chunks)
                    }
                    self.batch_operations[batch_id]["processed_documents"] += 1
                
            except Exception as e:
                # Store error
                async with self._batch_lock:
                    self.batch_operations[batch_id]["results"][document.document_id] = {
                        "status": ChunkingStatus.FAILED,
                        "error_message": str(e)
                    }
                    self.batch_operations[batch_id]["failed_documents"] += 1
                
                logger.error(f"Failed to process document {document.document_id}: {e}")
    
    async def _enhance_chunks(
        self,
        chunks: List[DocumentChunk],
        original_text: str,
        metadata: Optional[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Enhance chunks with additional information and validation."""
        enhanced_chunks = []
        
        # Anthropic Contextual Enhancement requires the WHOLE document
        # This is incompatible with the current _enhance_chunks architecture
        # TODO: Refactor to call AnthropicContextualEnhancer at a higher level
        # where we have access to the complete document text
        contextual_results = None
        if self.enable_contextual_enhancement and self.contextual_enhancer:
            logger.debug("Anthropic contextual enhancement requires architectural refactoring - skipping for now")
            # The Anthropic enhancer needs:
            # - whole_document: Complete document text (not available here)
            # - document_context: DocumentContext object with metadata
            # This should be called from the API layer, not from _enhance_chunks
        
        for i, chunk in enumerate(chunks):
            # Add quality scoring if enabled
            if self.settings.enable_quality_validation:
                quality_score = await self._calculate_chunk_quality(chunk.content, original_text)
                # Ensure quality_score is not None
                if quality_score is None:
                    quality_score = 0.5  # Default quality score
                if quality_score < self.settings.min_chunk_quality_score:
                    logger.warning(f"Chunk {i} has low quality score: {quality_score}")
                chunk.quality_score = quality_score
            
            # Add word and sentence counts
            chunk.word_count = len(chunk.content.split())
            chunk.sentence_count = len(re.split(r'[.!?]+', chunk.content))
            
            # Add boundary information
            chunk.boundary_info = {
                "starts_with_sentence": chunk.content.strip()[0].isupper() if chunk.content.strip() else False,
                "ends_with_sentence": chunk.content.rstrip().endswith(('.', '!', '?')),
                "has_complete_sentences": chunk.sentence_count > 0
            }
            
            # Phase 3: Add contextual enhancement data
            if contextual_results and i < len(contextual_results):
                enhancement_result = contextual_results[i]
                
                # Add enhancement metadata to chunk
                chunk.metadata.update({
                    'contextual_enhancement': {
                        'enhanced': True,
                        'strategy_used': enhancement_result.strategy_used.value,
                        'template_used': enhancement_result.template_used,
                        'quality_score': enhancement_result.quality_metrics.overall_score,
                        'context_length': len(enhancement_result.context_added),
                        'processing_time_ms': enhancement_result.processing_time_ms,
                        'embedding_ready': enhancement_result.embedding_vector is not None
                    }
                })
                
                # Store enhanced content and embedding vector
                chunk.enhanced_content = enhancement_result.enhanced_content
                chunk.embedding_vector = enhancement_result.embedding_vector
                chunk.context_quality_score = enhancement_result.quality_metrics.overall_score
                
                # Update chunk quality score if contextual enhancement improved it
                current_quality = getattr(chunk, 'quality_score', 0.5)
                enhanced_quality = enhancement_result.quality_metrics.overall_score
                if current_quality is not None and enhanced_quality is not None and enhanced_quality > current_quality:
                    chunk.quality_score = enhanced_quality
            else:
                # Mark as not contextually enhanced
                chunk.metadata.update({
                    'contextual_enhancement': {
                        'enhanced': False,
                        'reason': 'contextual_enhancer_unavailable'
                    }
                })
            
            enhanced_chunks.append(chunk)
        
        # Deduplicate if enabled
        if self.settings.enable_chunk_deduplication:
            enhanced_chunks = await self._deduplicate_chunks(enhanced_chunks)
        
        return enhanced_chunks
    
    async def _calculate_chunk_quality(self, chunk_content: str, original_text: str) -> float:
        """Calculate quality score for a chunk."""
        # Simple quality scoring based on various factors
        score = 1.0
        
        # Penalize very short chunks
        if len(chunk_content) < self.settings.min_chunk_size:
            score *= 0.5
        
        # Penalize chunks that don't end with proper punctuation
        if not chunk_content.rstrip().endswith(('.', '!', '?', ':')):
            score *= 0.8
        
        # Bonus for complete sentences
        sentences = re.split(r'[.!?]+', chunk_content)
        complete_sentences = [s for s in sentences if len(s.strip()) > 10]
        if len(complete_sentences) > 0:
            score *= 1.1
        
        return min(score, 1.0)
    
    async def _deduplicate_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Remove duplicate chunks based on content similarity."""
        # Simple deduplication based on exact content match
        seen_content = set()
        deduplicated = []
        
        for chunk in chunks:
            content_hash = hash(chunk.content.strip().lower())
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                deduplicated.append(chunk)
            else:
                logger.debug(f"Removed duplicate chunk: {chunk.chunk_id}")
        
        return deduplicated
    
    def _generate_cache_key(self, text: str, strategy: str, chunk_size: int, chunk_overlap: int) -> str:
        """Generate cache key for chunking request."""
        text_hash = hash(text)
        return f"chunk:{text_hash}:{strategy}:{chunk_size}:{chunk_overlap}"

    async def store_chunks_in_graph(
        self,
        chunks: List[DocumentChunk],
        document_id: str,
        document_type: Optional[str] = None
    ) -> bool:
        """
        Store chunks in graph.chunks table for GraphRAG integration.

        This method persists generated chunks to the graph.chunks table,
        enabling GraphRAG operations including:
        - Document chunk retrieval
        - Semantic search via embeddings
        - Text unit tracking
        - Entity-chunk associations

        Args:
            chunks: List of DocumentChunk objects to store
            document_id: Document identifier (must exist in graph.document_registry)
            document_type: Optional document type for content_type classification

        Returns:
            True if storage successful, False otherwise
        """
        if not self.enable_graph_storage:
            logger.info(f"Graph storage disabled, skipping chunk storage for {document_id}")
            return False

        if not self.supabase_client:
            logger.error("SupabaseClient not available for graph storage")
            return False

        if not chunks:
            logger.warning(f"No chunks to store for document {document_id}")
            return True

        try:
            # Prepare chunk records for database insertion
            chunk_records = []

            for chunk in chunks:
                # Determine content type (default: text)
                content_type = self._determine_content_type(chunk, document_type)

                # Extract embedding vector from chunk
                embedding_vector = None
                if hasattr(chunk, 'embedding_vector') and chunk.embedding_vector:
                    embedding_vector = chunk.embedding_vector
                    # Verify dimension (must be 2048 for Jina v4)
                    if len(embedding_vector) != 2048:
                        logger.warning(
                            f"Invalid embedding dimension: {len(embedding_vector)} (expected 2048), "
                            f"chunk {chunk.chunk_id}"
                        )
                        embedding_vector = None

                # Build chunk record matching graph.chunks schema
                chunk_record = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "content_type": content_type,
                    "token_count": chunk.word_count * 1.3 if chunk.word_count else len(chunk.content) // 4,  # Rough estimate
                    "chunk_size": chunk.character_count,
                    "overlap_size": chunk.metadata.get('overlap', 0) if chunk.metadata else 0,
                    "chunk_method": chunk.metadata.get('chunking_strategy', 'semantic') if chunk.metadata else 'semantic',
                    "parent_chunk_id": chunk.metadata.get('parent_chunk_id') if chunk.metadata else None,
                    "context_before": chunk.metadata.get('context_before') if chunk.metadata else None,
                    "context_after": chunk.metadata.get('context_after') if chunk.metadata else None,
                    "metadata": {
                        "quality_score": chunk.quality_score,
                        "word_count": chunk.word_count,
                        "sentence_count": chunk.sentence_count,
                        "boundary_info": chunk.boundary_info,
                        "contextual_enhancement": chunk.metadata.get('contextual_enhancement') if chunk.metadata else None,
                        "start_position": chunk.start_position,
                        "end_position": chunk.end_position
                    },
                    "content_embedding": embedding_vector  # 2048-dim vector or None
                }

                chunk_records.append(chunk_record)

            # Batch insert chunks using admin operation (bypasses RLS)
            logger.info(f"Storing {len(chunk_records)} chunks for document {document_id} in graph.chunks")

            result = await self.supabase_client.insert(
                "graph.chunks",
                chunk_records,
                admin_operation=True
            )

            if result:
                logger.info(
                    f"Successfully stored {len(result)} chunks for document {document_id} "
                    f"(embeddings_included={sum(1 for r in chunk_records if r['content_embedding'] is not None)})"
                )
                return True
            else:
                logger.error(f"Failed to store chunks for document {document_id}: No result returned")
                return False

        except Exception as e:
            logger.error(
                f"Error storing chunks in graph.chunks for document {document_id}: {e} "
                f"(document_id={document_id}, chunk_count={len(chunks)})"
            )
            return False

    def _determine_content_type(self, chunk: DocumentChunk, document_type: Optional[str]) -> str:
        """
        Determine content_type for graph.chunks based on chunk metadata.

        Valid content_types: text, heading, list, table, code

        Args:
            chunk: DocumentChunk with metadata
            document_type: Optional document type hint

        Returns:
            Content type string (default: 'text')
        """
        # Check chunk metadata for explicit content_type
        if chunk.metadata and 'content_type' in chunk.metadata:
            content_type = chunk.metadata['content_type'].lower()
            # Validate against allowed types
            if content_type in ['text', 'heading', 'list', 'table', 'code']:
                return content_type

        # Heuristic detection based on content patterns
        content = chunk.content.strip()

        # Detect heading (short, ends without period, title case)
        if len(content) < 100 and not content.endswith('.') and content.istitle():
            return 'heading'

        # Detect list items (starts with bullet, dash, or number)
        if content.startswith(('-', '*', '•')) or (content[0].isdigit() and '. ' in content[:5]):
            return 'list'

        # Detect code (contains code-like patterns)
        if any(pattern in content for pattern in ['def ', 'function ', 'class ', '```', 'import ']):
            return 'code'

        # Detect table (contains pipe or tab separators)
        if '|' in content or '\t' in content:
            return 'table'

        # Default to text
        return 'text'