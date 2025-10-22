"""
Anthropic Contextual Enhancer for Chunking Service.

This module implements Anthropic's 4-layer contextualization approach for improving
retrieval accuracy and semantic search quality. It provides comprehensive context
enhancement for legal documents with support for large chunks (8000 tokens).

Key Features:
- 4-layer contextualization: original, contextual, BM25-optimized, and cleaned content
- Large chunk support (up to 8000 tokens) for entity extraction
- Document-level context prepending with title, type, section, and summaries
- Previous chunk summarization and entity tracking
- BM25 optimization and text normalization
- Integration with existing chunking service architecture
"""

import asyncio
import hashlib
import json
import logging
import multiprocessing
import re
import httpx
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from collections import defaultdict

# Fix vLLM CUDA multiprocessing error
# Must use 'spawn' method instead of 'fork' to prevent CUDA re-initialization errors
try:
    multiprocessing.set_start_method('spawn', force=True)
    logging.getLogger(__name__).info("Set multiprocessing start method to 'spawn' for vLLM CUDA compatibility")
except RuntimeError:
    # Already set, ignore
    pass

from ..models.responses import DocumentChunk
from .config import get_settings
from .vllm_embedding_manager_simple import (
    VLLMEmbeddingManager,
    EmbeddingConfig,
    get_embedding_manager
)

logger = logging.getLogger(__name__)


class ContextLayer(str, Enum):
    """Four layers of contextualization per Anthropic methodology."""
    ORIGINAL = "original_content"
    CONTEXTUAL = "contextual_content"
    BM25_OPTIMIZED = "bm25_content"
    CLEANED = "cleaned_content"


class ChunkType(str, Enum):
    """Types of chunks for different purposes."""
    STANDARD = "standard"  # ~512 tokens for general retrieval
    LARGE = "large"  # ~8000 tokens for entity extraction
    SEMANTIC = "semantic"  # Variable size based on semantic boundaries


@dataclass
class DocumentContext:
    """Comprehensive document context for prepending."""
    document_id: str
    title: str
    document_type: str
    total_chunks: int
    current_section: Optional[str] = None
    current_chapter: Optional[str] = None
    document_summary: Optional[str] = None
    key_entities: List[str] = field(default_factory=list)
    legal_jurisdiction: Optional[str] = None
    date_context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkContext:
    """Context information for a specific chunk."""
    chunk_index: int
    previous_chunk_summary: Optional[str] = None
    previous_entities: List[str] = field(default_factory=list)
    next_chunk_preview: Optional[str] = None
    section_context: Optional[str] = None
    semantic_neighbors: List[str] = field(default_factory=list)
    contextual_keywords: List[str] = field(default_factory=list)


@dataclass
class EnhancedChunkResult:
    """Result containing all 4 layers of contextualized content."""
    chunk_id: str
    chunk_index: int
    
    # 4-layer content
    original_content: str
    contextual_content: str
    bm25_content: str
    cleaned_content: str
    
    # Metadata
    token_count: int
    chunk_type: ChunkType
    context_quality_score: float
    entities_extracted: List[str]
    keywords_for_search: List[str]
    
    # Embeddings (optional)
    embedding_vector: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    
    # Performance metrics
    processing_time_ms: int = 0
    enhancement_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchEnhancementResult:
    """Result for batch chunk enhancement."""
    document_id: str
    total_chunks: int
    enhanced_chunks: List[EnhancedChunkResult]
    document_context: DocumentContext
    processing_time_ms: int
    average_quality_score: float
    total_entities: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnthropicContextualEnhancer:
    """
    Implements Anthropic's 4-layer contextualization methodology.
    
    This enhancer creates four distinct representations of each chunk:
    1. Original: Raw chunk text
    2. Contextual: Prepended with rich document context
    3. BM25: Optimized for keyword search
    4. Cleaned: Normalized for processing
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        max_chunk_tokens: int = 8000,
        standard_chunk_tokens: int = 512
    ):
        # Load configuration
        self.config = config or {}
        
        # Use vLLM services directly (NOT Prompt Service)
        # FIXED: Use correct vLLM URL at 10.10.0.87:8080 (not localhost)
        self.vllm_text_url = self.config.get('vllm_text_url', 'http://10.10.0.87:8080')
        
        # Initialize vLLM embedding manager (replaces port 8081)
        settings = get_settings()
        embedding_config = EmbeddingConfig(
            embedding_dim=settings.embedding_dimensions,  # From environment
            gpu_memory_utilization=settings.embedding_gpu_memory_utilization,
            max_batch_size=settings.embedding_batch_size
        )
        self.embedding_manager = get_embedding_manager(embedding_config)
        
        # Context generation configuration (all configurable)
        self.context_config = self.config.get('context_generation', {})
        self.max_tokens = self.context_config.get('max_tokens', 200)
        self.temperature = self.context_config.get('temperature', 0.0)
        self.top_p = self.context_config.get('top_p', 1.0)
        self.frequency_penalty = self.context_config.get('frequency_penalty', 0.0)
        self.presence_penalty = self.context_config.get('presence_penalty', 0.0)
        self.timeout_seconds = self.context_config.get('timeout_seconds', 120)
        self.model = self.context_config.get('model', 'qwen3-4b')
        self.embedding_model = self.config.get('embedding_model', settings.embedding_model_path)
        
        # Document handling
        self.max_document_tokens = self.context_config.get('max_document_tokens', 100000)
        self.truncation_strategy = self.context_config.get('truncation_strategy', 'middle')
        
        # Anthropic prompt template
        self.prompt_template = self.context_config.get('prompt_template', 
            "<document>\n{whole_document}\n</document>\n\n"
            "Here is the chunk we want to situate within the whole document:\n"
            "<chunk>\n{chunk_content}\n</chunk>\n\n"
            "Please give a short succinct context to situate this chunk within "
            "the overall document for the purposes of improving search retrieval "
            "of the chunk. Answer only with the succinct context and nothing else."
        )
        
        self.max_chunk_tokens = max_chunk_tokens
        self.standard_chunk_tokens = standard_chunk_tokens
        
        # Caches for performance
        self._document_context_cache: Dict[str, DocumentContext] = {}
        self._chunk_summary_cache: Dict[str, str] = {}
        self._entity_cache: Dict[str, List[str]] = {}
        
        # Pattern matching for legal content
        self._initialize_patterns()
        
        # Performance tracking
        self._stats = {
            'chunks_enhanced': 0,
            'large_chunks_created': 0,
            'entities_extracted': 0,
            'avg_quality_score': 0.0,
            'processing_times': []
        }
    
    def _initialize_patterns(self):
        """Initialize regex patterns for legal content analysis."""
        self._patterns = {
            # Legal entities
            'person': re.compile(
                r'\b(?:[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)\b'
            ),
            'organization': re.compile(
                r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|LLC|Corp|Co|Ltd|LLP|LP|PC|PA|PLLC|Association|Foundation|Institute|University|College|Company|Group|Partners)\.?)\b'
            ),
            'court': re.compile(
                r'\b(?:Supreme Court|Court of Appeals|Circuit Court|District Court|Superior Court|Tax Court|Bankruptcy Court|Family Court|Probate Court)\b',
                re.IGNORECASE
            ),
            
            # Legal references
            'case_citation': re.compile(
                r'\b\d+\s+(?:F\.|F\.2d|F\.3d|F\.4th|S\.Ct\.|U\.S\.|F\.Supp\.|F\.Supp\.2d|F\.Supp\.3d)\s+\d+(?:\s*\([^)]+\d{4}\))?'
            ),
            'statute': re.compile(
                r'\b(?:\d+\s+U\.S\.C\.?|[A-Z]{2,}\s+(?:Rev\.\s*)?(?:Stat\.|Code)|(?:§|Section)\s*\d+[\d.-]*)\b',
                re.IGNORECASE
            ),
            'regulation': re.compile(
                r'\b\d+\s+C\.F\.R\.?\s*(?:§|Part)?\s*[\d.]+\b',
                re.IGNORECASE
            ),
            
            # Document structure
            'section_header': re.compile(
                r'^(?:(?:SECTION|ARTICLE|CHAPTER|PART)\s+[IVX\d]+[:\.]?\s*.+|[IVX]+\.\s+.+|\d+\.\s+[A-Z].+)$',
                re.MULTILINE | re.IGNORECASE
            ),
            'subsection': re.compile(
                r'^(?:\([a-z]\)|\d+\.\d+|\([0-9]+\))\s+',
                re.MULTILINE
            ),
            
            # Legal concepts
            'legal_standard': re.compile(
                r'\b(?:reasonable\s+(?:doubt|person|care)|preponderance\s+of\s+(?:the\s+)?evidence|'
                r'clear\s+and\s+convincing|strict\s+scrutiny|rational\s+basis|intermediate\s+scrutiny|'
                r'arbitrary\s+and\s+capricious|de\s+novo|abuse\s+of\s+discretion)\b',
                re.IGNORECASE
            ),
            'legal_term': re.compile(
                r'\b(?:plaintiff|defendant|appellant|appellee|petitioner|respondent|'
                r'jurisdiction|venue|standing|mootness|ripeness|precedent|stare\s+decisis|'
                r'holding|dicta|remand|affirm|reverse|vacate|motion|brief|complaint|answer)\b',
                re.IGNORECASE
            )
        }
    
    async def initialize(self):
        """Initialize the enhancer and verify service connectivity."""
        logger.info("Initializing Anthropic Contextual Enhancer with 4-layer methodology...")
        
        # Verify vLLM services connectivity
        await self._verify_vllm_services()
        
        logger.info(f"Initialized with max chunk size: {self.max_chunk_tokens} tokens")
    
    async def _verify_vllm_services(self):
        """Verify vLLM text service connectivity and embedding manager initialization."""
        # Check vLLM text service (port 8080)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.vllm_text_url}/health",
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info(f"vLLM text service connectivity verified at {self.vllm_text_url}")
                else:
                    logger.warning(f"vLLM text service health check returned {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to verify vLLM text service: {e}")
        
        # Verify embedding manager is initialized
        if self.embedding_manager and self.embedding_manager._initialized:
            logger.info("vLLM embedding manager is initialized and ready")
            stats = self.embedding_manager.get_stats()
            logger.info(f"Embedding manager stats: {stats}")
        else:
            logger.warning("vLLM embedding manager not initialized, attempting initialization...")
            if self.embedding_manager.initialize():
                logger.info("vLLM embedding manager initialized successfully")
            else:
                logger.error("Failed to initialize vLLM embedding manager")
    
    async def enhance_chunk_with_four_layers(
        self,
        chunk: DocumentChunk,
        whole_document: str,  # CRITICAL: Need the whole document!
        document_context: DocumentContext,
        chunk_context: ChunkContext,
        chunk_type: ChunkType = ChunkType.STANDARD
    ) -> EnhancedChunkResult:
        """
        Create 4-layer contextualization for a chunk.
        
        Args:
            chunk: The document chunk to enhance
            document_context: Document-level context information
            chunk_context: Chunk-specific context information
            chunk_type: Type of chunk (standard, large, semantic)
            
        Returns:
            EnhancedChunkResult with all 4 layers
        """
        start_time = datetime.now()
        
        try:
            # Layer 1: Original content (unchanged)
            original_content = chunk.content
            
            # Layer 2: Contextual content (with prepended context)
            contextual_content = await self._create_contextual_layer(
                original_content,
                whole_document,
                document_context,
                chunk_context
            )
            
            # Layer 3: BM25-optimized content
            bm25_content = await self._create_bm25_layer(
                original_content,
                document_context,
                chunk_context
            )
            
            # Layer 4: Cleaned content (normalized)
            cleaned_content = await self._create_cleaned_layer(original_content)
            
            # Extract entities from the content
            entities = await self._extract_entities(original_content)
            
            # Generate search keywords
            keywords = await self._generate_search_keywords(
                original_content,
                entities,
                chunk_context
            )
            
            # Calculate token count
            token_count = await self._estimate_token_count(contextual_content)
            
            # Assess quality
            quality_score = await self._assess_enhancement_quality(
                original_content,
                contextual_content,
                entities
            )
            
            # Generate embedding if requested
            embedding_vector = None
            embedding_model = None
            if chunk_type != ChunkType.LARGE:  # Don't embed large chunks
                embedding_result = await self._generate_embedding(contextual_content)
                if embedding_result:
                    embedding_vector = embedding_result['vector']
                    embedding_model = embedding_result['model']
            
            # Update statistics
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self._update_stats(quality_score, processing_time, len(entities))
            
            return EnhancedChunkResult(
                chunk_id=chunk.chunk_id,
                chunk_index=chunk_context.chunk_index,
                original_content=original_content,
                contextual_content=contextual_content,
                bm25_content=bm25_content,
                cleaned_content=cleaned_content,
                token_count=token_count,
                chunk_type=chunk_type,
                context_quality_score=quality_score,
                entities_extracted=entities,
                keywords_for_search=keywords,
                embedding_vector=embedding_vector,
                embedding_model=embedding_model,
                processing_time_ms=processing_time,
                enhancement_metadata={
                    'document_type': document_context.document_type,
                    'section': chunk_context.section_context,
                    'has_previous_summary': chunk_context.previous_chunk_summary is not None,
                    'entity_count': len(entities),
                    'keyword_count': len(keywords)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to enhance chunk {chunk.chunk_id}: {e}")
            # Return minimal enhancement on failure
            return self._create_fallback_enhancement(chunk, chunk_context, str(e))
    
    async def _create_contextual_layer(
        self,
        original_content: str,
        whole_document: str,
        document_context: DocumentContext,
        chunk_context: ChunkContext
    ) -> str:
        """
        Create the contextual layer using Anthropic's exact methodology.
        
        This uses the WHOLE DOCUMENT to generate situating context,
        then prepends it to the chunk content.
        """
        # Generate situating context using the whole document
        situating_context = await self._generate_situating_context(
            whole_document=whole_document,
            chunk_content=original_content,
            chunk_index=chunk_context.chunk_index
        )
        
        # Prepend the situating context to create enhanced content
        contextual_content = f"{situating_context}\n\n{original_content}"
        
        return contextual_content
    
    async def _generate_situating_context(
        self,
        whole_document: str,
        chunk_content: str,
        chunk_index: int
    ) -> str:
        """
        Generate situating context using Anthropic's EXACT methodology.
        This is the CORE of contextual retrieval!
        """
        # Prepare document (handle large documents)
        prepared_document = await self._prepare_document_for_context(whole_document)
        
        # Format the prompt using Anthropic's exact template
        prompt = self.prompt_template.format(
            whole_document=prepared_document,
            chunk_content=chunk_content
        )
        
        # Call vLLM service directly (NOT Prompt Service)
        try:
            logger.info(f"Calling vLLM service at {self.vllm_text_url} with model {self.model}")
            async with httpx.AsyncClient() as client:
                request_data = {
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }],
                    # All configurable parameters
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty
                }
                logger.debug(f"vLLM request data: {request_data}")
                
                response = await client.post(
                    f"{self.vllm_text_url}/v1/chat/completions",
                    json=request_data,
                    timeout=self.timeout_seconds
                )
                
                if response.status_code == 200:
                    result = response.json()
                    situating_context = result["choices"][0]["message"]["content"]
                    logger.info(f"Generated context: {situating_context[:100]}...")
                    return situating_context.strip()
                else:
                    logger.error(f"vLLM request failed: {response.status_code} - {response.text}")
                    return f"Chunk {chunk_index + 1}: This section contains important content from the document."
                    
        except Exception as e:
            logger.error(f"Failed to generate situating context: {e}")
            # Fallback context
            return f"Chunk {chunk_index + 1}: This section contains important content from the document."
    
    async def _prepare_document_for_context(self, document: str) -> str:
        """
        Prepare document for context generation, handling large documents.
        """
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(document) // 4
        
        if estimated_tokens <= self.max_document_tokens:
            return document
        
        # Document too large, apply truncation strategy
        if self.truncation_strategy == "middle":
            # Keep beginning and end, truncate middle
            chars_to_keep = self.max_document_tokens * 4
            beginning = document[:chars_to_keep // 2]
            end = document[-(chars_to_keep // 2):]
            return f"{beginning}\n\n[... document middle truncated for context window ...]\n\n{end}"
        elif self.truncation_strategy == "end":
            # Keep only beginning
            chars_to_keep = self.max_document_tokens * 4
            return document[:chars_to_keep] + "\n\n[... rest of document truncated for context window ...]"
        else:
            # Smart truncation - try to keep section headers
            return self._smart_truncate(document, self.max_document_tokens * 4)
    
    async def _create_bm25_layer(
        self,
        original_content: str,
        document_context: DocumentContext,
        chunk_context: ChunkContext
    ) -> str:
        """
        Create BM25-optimized content for keyword search.
        
        This layer:
        - Expands abbreviations
        - Adds synonyms for key terms
        - Includes related legal concepts
        - Optimizes for keyword matching
        """
        bm25_parts = []
        
        # Add searchable document metadata
        bm25_parts.append(f"Document: {document_context.title}")
        bm25_parts.append(f"Type: {document_context.document_type}")
        
        # Expand legal abbreviations
        expanded_content = self._expand_legal_abbreviations(original_content)
        
        # Add synonyms and related terms
        legal_terms = self._extract_legal_terms(expanded_content)
        if legal_terms:
            synonyms = self._get_legal_synonyms(legal_terms)
            bm25_parts.append(f"Related Terms: {', '.join(synonyms)}")
        
        # Add the expanded content
        bm25_parts.append(expanded_content)
        
        # Add entities for searchability
        entities = await self._extract_entities(original_content)
        if entities:
            bm25_parts.append(f"Entities: {', '.join(entities)}")
        
        # Add contextual keywords
        if chunk_context.contextual_keywords:
            bm25_parts.append(f"Keywords: {', '.join(chunk_context.contextual_keywords)}")
        
        # Add section identifiers
        if chunk_context.section_context:
            bm25_parts.append(f"Section: {chunk_context.section_context}")
        
        return " ".join(bm25_parts)
    
    async def _create_cleaned_layer(self, original_content: str) -> str:
        """
        Create cleaned/normalized content.
        
        This layer:
        - Removes special characters
        - Normalizes whitespace
        - Standardizes legal citations
        - Removes redundant information
        """
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', original_content)
        
        # Standardize legal citations
        cleaned = self._standardize_citations(cleaned)
        
        # Remove special characters but keep legal symbols
        cleaned = re.sub(r'[^\w\s§¶•\-.,;:()"\'/]', '', cleaned)
        
        # Normalize case for consistent processing
        # Keep original case for proper nouns and legal terms
        words = cleaned.split()
        normalized_words = []
        
        for word in words:
            if self._is_legal_term(word) or self._is_proper_noun(word):
                normalized_words.append(word)
            else:
                normalized_words.append(word.lower())
        
        cleaned = ' '.join(normalized_words)
        
        # Remove redundant punctuation
        cleaned = re.sub(r'([.;!?])\1+', r'\1', cleaned)
        
        return cleaned.strip()
    
    async def _extract_entities(self, content: str) -> List[str]:
        """Extract legal entities from content."""
        entities = set()
        
        # Extract persons
        for match in self._patterns['person'].findall(content):
            if len(match.split()) >= 2:  # At least first and last name
                entities.add(match)
        
        # Extract organizations
        for match in self._patterns['organization'].findall(content):
            entities.add(match)
        
        # Extract courts
        for match in self._patterns['court'].findall(content):
            entities.add(match)
        
        # Cache entities for future reference
        content_hash = hashlib.md5(content.encode()).hexdigest()
        self._entity_cache[content_hash] = list(entities)
        
        return list(entities)[:20]  # Limit to top 20 entities
    
    async def _generate_search_keywords(
        self,
        content: str,
        entities: List[str],
        chunk_context: ChunkContext
    ) -> List[str]:
        """Generate keywords optimized for search."""
        keywords = set()
        
        # Add entities as keywords
        for entity in entities[:10]:
            # Simplify entity names for search
            simplified = re.sub(r'\b(?:Inc|LLC|Corp|Co|Ltd)\.?\b', '', entity).strip()
            keywords.add(simplified.lower())
        
        # Extract case names from citations
        citations = self._patterns['case_citation'].findall(content)
        for citation in citations[:5]:
            # Try to extract case name
            parts = citation.split()
            if parts:
                keywords.add(parts[0].lower())
        
        # Add legal standards
        standards = self._patterns['legal_standard'].findall(content)
        for standard in standards[:5]:
            keywords.add(standard.lower())
        
        # Add contextual keywords
        keywords.update(chunk_context.contextual_keywords)
        
        # Add section identifiers
        section_headers = self._patterns['section_header'].findall(content)
        for header in section_headers[:3]:
            # Clean and add section name
            clean_header = re.sub(r'^(?:SECTION|ARTICLE|CHAPTER|PART)\s+[IVX\d]+[:\.]?\s*', '', header, flags=re.IGNORECASE)
            if clean_header:
                keywords.add(clean_header.lower()[:50])  # Limit length
        
        return list(keywords)[:30]  # Return top 30 keywords
    
    async def _estimate_token_count(self, content: str) -> int:
        """Estimate token count for content."""
        # Rough estimation: 1 token ≈ 4 characters
        return len(content) // 4
    
    async def _assess_enhancement_quality(
        self,
        original: str,
        contextual: str,
        entities: List[str]
    ) -> float:
        """Assess the quality of enhancement."""
        score = 0.0
        
        # Context expansion score
        if len(contextual) > len(original) * 1.5:
            score += 0.3
        
        # Entity richness score
        if len(entities) > 5:
            score += 0.3
        elif len(entities) > 2:
            score += 0.2
        
        # Structure score (headers, sections)
        if '##' in contextual or '#' in contextual:
            score += 0.2
        
        # Metadata presence score
        if 'Document:' in contextual and 'Type:' in contextual:
            score += 0.2
        
        return min(1.0, score)
    
    async def _generate_embedding(self, content: str) -> Optional[Dict[str, Any]]:
        """Generate embedding for content using vLLM embedding manager."""
        try:
            # Use the embedding manager to generate embedding
            embedding_vector = await self.embedding_manager.generate_single_embedding(content)
            
            if embedding_vector:
                # Already truncated to 1536 dimensions by the manager
                return {
                    'vector': embedding_vector,
                    'model': self.embedding_model
                }
            else:
                logger.error("Failed to generate embedding")
                return None
                    
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def create_large_chunks_for_entity_extraction(
        self,
        chunks: List[DocumentChunk],
        document_context: DocumentContext,
        target_tokens: int = 8000
    ) -> List[EnhancedChunkResult]:
        """
        Create large chunks (8000 tokens) optimized for entity extraction.
        
        Args:
            chunks: Original document chunks
            document_context: Document context
            target_tokens: Target token count for large chunks
            
        Returns:
            List of large enhanced chunks
        """
        logger.info(f"Creating large chunks for entity extraction (target: {target_tokens} tokens)")
        
        large_chunks = []
        current_content = []
        current_tokens = 0
        current_entities = set()
        chunk_start_index = 0
        
        for i, chunk in enumerate(chunks):
            chunk_tokens = await self._estimate_token_count(chunk.content)
            
            # Check if adding this chunk would exceed target
            if current_tokens + chunk_tokens > target_tokens and current_content:
                # Create large chunk from accumulated content
                large_chunk_content = "\n\n".join(current_content)
                
                # Create chunk context
                chunk_context = ChunkContext(
                    chunk_index=len(large_chunks),
                    previous_entities=list(current_entities)[:20],
                    section_context=f"Chunks {chunk_start_index+1} to {i}"
                )
                
                # Create enhanced chunk
                enhanced = await self.enhance_chunk_with_four_layers(
                    DocumentChunk(
                        chunk_id=f"large_chunk_{len(large_chunks)}",
                        content=large_chunk_content,
                        start_position=chunks[chunk_start_index].start_position,
                        end_position=chunks[i-1].end_position,
                        chunk_index=len(large_chunks),
                        character_count=len(large_chunk_content),
                        metadata={'source_chunks': i - chunk_start_index}
                    ),
                    document_context,
                    chunk_context,
                    ChunkType.LARGE
                )
                
                large_chunks.append(enhanced)
                
                # Update current entities
                current_entities.update(enhanced.entities_extracted)
                
                # Reset for next large chunk
                current_content = [chunk.content]
                current_tokens = chunk_tokens
                chunk_start_index = i
            else:
                # Accumulate content
                current_content.append(chunk.content)
                current_tokens += chunk_tokens
        
        # Create final large chunk if content remains
        if current_content:
            large_chunk_content = "\n\n".join(current_content)
            
            chunk_context = ChunkContext(
                chunk_index=len(large_chunks),
                previous_entities=list(current_entities)[:20],
                section_context=f"Chunks {chunk_start_index+1} to {len(chunks)}"
            )
            
            enhanced = await self.enhance_chunk_with_four_layers(
                DocumentChunk(
                    chunk_id=f"large_chunk_{len(large_chunks)}",
                    content=large_chunk_content,
                    start_position=chunks[chunk_start_index].start_position,
                    end_position=chunks[-1].end_position,
                    chunk_index=len(large_chunks),
                    character_count=len(large_chunk_content),
                    metadata={'source_chunks': len(chunks) - chunk_start_index}
                ),
                document_context,
                chunk_context,
                ChunkType.LARGE
            )
            
            large_chunks.append(enhanced)
        
        logger.info(f"Created {len(large_chunks)} large chunks from {len(chunks)} original chunks")
        self._stats['large_chunks_created'] += len(large_chunks)
        
        return large_chunks
    
    async def batch_enhance_chunks(
        self,
        chunks: List[DocumentChunk],
        whole_document: str,  # CRITICAL: Need the whole document for context generation!
        document_context: DocumentContext,
        generate_summaries: bool = True,
        max_concurrent: int = 5
    ) -> BatchEnhancementResult:
        """
        Enhance multiple chunks with full context tracking.
        
        Args:
            chunks: List of chunks to enhance
            whole_document: Complete document text for context generation
            document_context: Document context
            generate_summaries: Whether to generate chunk summaries
            max_concurrent: Maximum concurrent operations
            
        Returns:
            BatchEnhancementResult with all enhanced chunks
        """
        start_time = datetime.now()
        logger.info(f"Starting batch enhancement of {len(chunks)} chunks")
        
        enhanced_chunks = []
        all_entities = set()
        
        # Process chunks sequentially to maintain context
        previous_summary = None
        previous_entities = []
        
        for i, chunk in enumerate(chunks):
            # Detect section context
            section_context = await self._detect_section_context(chunk.content)
            
            # Create chunk context
            chunk_context = ChunkContext(
                chunk_index=i,
                previous_chunk_summary=previous_summary,
                previous_entities=previous_entities,
                section_context=section_context,
                contextual_keywords=await self._extract_contextual_keywords(chunk.content)
            )
            
            # Look ahead for next chunk preview
            if i < len(chunks) - 1:
                next_preview = chunks[i + 1].content[:100] + "..."
                chunk_context.next_chunk_preview = next_preview
            
            # Enhance chunk
            enhanced = await self.enhance_chunk_with_four_layers(
                chunk,
                whole_document,
                document_context,
                chunk_context,
                ChunkType.STANDARD
            )
            
            enhanced_chunks.append(enhanced)
            all_entities.update(enhanced.entities_extracted)
            
            # Generate summary for next chunk's context
            if generate_summaries and i < len(chunks) - 1:
                previous_summary = await self._generate_chunk_summary(chunk.content)
                previous_entities = enhanced.entities_extracted
        
        # Calculate overall metrics
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        avg_quality = sum(c.context_quality_score for c in enhanced_chunks) / len(enhanced_chunks) if enhanced_chunks else 0.0
        
        return BatchEnhancementResult(
            document_id=document_context.document_id,
            total_chunks=len(enhanced_chunks),
            enhanced_chunks=enhanced_chunks,
            document_context=document_context,
            processing_time_ms=processing_time,
            average_quality_score=avg_quality,
            total_entities=list(all_entities),
            metadata={
                'enhancement_method': 'anthropic_4_layer',
                'summaries_generated': generate_summaries,
                'unique_entities': len(all_entities)
            }
        )
    
    async def _generate_chunk_summary(self, content: str) -> str:
        """Generate a summary of chunk content for context."""
        try:
            # Use Prompt Service to generate summary
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.prompt_service_url}/api/v1/simple/generate",
                    json={
                        "prompt": f"Summarize this legal text in 2-3 sentences, focusing on key points and entities:\n\n{content[:1000]}",
                        "max_tokens": 100,
                        "temperature": 0.3
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
        
        # Fallback to simple extraction
        sentences = re.split(r'[.!?]+', content)
        return sentences[0][:200] if sentences else content[:200]
    
    async def _detect_section_context(self, content: str) -> Optional[str]:
        """Detect section or chapter context from content."""
        # Look for section headers
        section_matches = self._patterns['section_header'].findall(content)
        if section_matches:
            return section_matches[0]
        
        # Look for chapter indicators
        chapter_pattern = re.compile(r'Chapter\s+[IVX\d]+[:\.]?\s*(.+)', re.IGNORECASE)
        chapter_match = chapter_pattern.search(content)
        if chapter_match:
            return chapter_match.group(0)
        
        return None
    
    async def _extract_contextual_keywords(self, content: str) -> List[str]:
        """Extract contextual keywords from content."""
        keywords = set()
        
        # Extract legal terms
        legal_terms = self._patterns['legal_term'].findall(content)
        keywords.update(term.lower() for term in legal_terms[:10])
        
        # Extract court names
        courts = self._patterns['court'].findall(content)
        keywords.update(court.lower() for court in courts[:5])
        
        # Extract simplified statute references
        statutes = self._patterns['statute'].findall(content)
        for statute in statutes[:5]:
            # Simplify statute reference
            simplified = re.sub(r'[^\w\s]', '', statute).lower()
            keywords.add(simplified)
        
        return list(keywords)[:20]
    
    def _expand_legal_abbreviations(self, content: str) -> str:
        """Expand common legal abbreviations for better search."""
        abbreviations = {
            r'\bU\.S\.C\.?\b': 'United States Code USC',
            r'\bC\.F\.R\.?\b': 'Code of Federal Regulations CFR',
            r'\bF\.3d\b': 'Federal Reporter Third Series F3d',
            r'\bF\.2d\b': 'Federal Reporter Second Series F2d',
            r'\bF\.Supp\.?\b': 'Federal Supplement FSupp',
            r'\bS\.Ct\.?\b': 'Supreme Court Reporter SCt',
            r'\bCt\.?\b': 'Court',
            r'\bDist\.?\b': 'District',
            r'\bCir\.?\b': 'Circuit',
            r'\bApp\.?\b': 'Appeals Appellate',
            r'\bDef\.?\b': 'Defendant',
            r'\bPl\.?\b': 'Plaintiff',
            r'\bResp\.?\b': 'Respondent',
            r'\bPet\.?\b': 'Petitioner'
        }
        
        expanded = content
        for pattern, replacement in abbreviations.items():
            expanded = re.sub(pattern, replacement, expanded)
        
        return expanded
    
    def _extract_legal_terms(self, content: str) -> List[str]:
        """Extract legal terms from content."""
        terms = []
        
        # Find legal terms
        legal_matches = self._patterns['legal_term'].findall(content)
        terms.extend(legal_matches)
        
        # Find legal standards
        standard_matches = self._patterns['legal_standard'].findall(content)
        terms.extend(standard_matches)
        
        return list(set(terms))[:20]
    
    def _get_legal_synonyms(self, terms: List[str]) -> List[str]:
        """Get synonyms for legal terms."""
        synonym_map = {
            'plaintiff': ['complainant', 'petitioner', 'claimant'],
            'defendant': ['respondent', 'accused', 'party'],
            'motion': ['request', 'application', 'petition'],
            'brief': ['memorandum', 'submission', 'argument'],
            'complaint': ['petition', 'claim', 'filing'],
            'jurisdiction': ['authority', 'power', 'venue'],
            'precedent': ['case law', 'authority', 'ruling'],
            'holding': ['ruling', 'decision', 'determination'],
            'remand': ['return', 'send back', 'refer'],
            'affirm': ['uphold', 'confirm', 'sustain'],
            'reverse': ['overturn', 'vacate', 'set aside']
        }
        
        synonyms = []
        for term in terms:
            term_lower = term.lower()
            if term_lower in synonym_map:
                synonyms.extend(synonym_map[term_lower])
        
        return list(set(synonyms))
    
    def _standardize_citations(self, content: str) -> str:
        """Standardize legal citations for consistency."""
        # Standardize U.S.C. citations
        content = re.sub(r'(\d+)\s+USC\s+§?\s*(\d+)', r'\1 U.S.C. § \2', content)
        
        # Standardize C.F.R. citations
        content = re.sub(r'(\d+)\s+CFR\s+§?\s*(\d+)', r'\1 C.F.R. § \2', content)
        
        # Standardize section symbols
        content = re.sub(r'(?:Section|Sec\.?)\s+(\d+)', r'§ \1', content)
        
        return content
    
    def _is_legal_term(self, word: str) -> bool:
        """Check if a word is a legal term."""
        legal_terms = {
            'plaintiff', 'defendant', 'appellant', 'appellee', 'petitioner',
            'respondent', 'jurisdiction', 'venue', 'standing', 'mootness',
            'ripeness', 'precedent', 'holding', 'dicta', 'remand', 'affirm',
            'reverse', 'vacate', 'motion', 'brief', 'complaint', 'answer'
        }
        return word.lower() in legal_terms
    
    def _is_proper_noun(self, word: str) -> bool:
        """Check if a word is likely a proper noun."""
        # Simple heuristic: starts with capital, not at sentence start
        return word[0].isupper() and len(word) > 1
    
    def _create_fallback_enhancement(
        self,
        chunk: DocumentChunk,
        chunk_context: ChunkContext,
        error_msg: str
    ) -> EnhancedChunkResult:
        """Create fallback enhancement when processing fails."""
        return EnhancedChunkResult(
            chunk_id=chunk.chunk_id,
            chunk_index=chunk_context.chunk_index,
            original_content=chunk.content,
            contextual_content=chunk.content,
            bm25_content=chunk.content,
            cleaned_content=chunk.content,
            token_count=len(chunk.content) // 4,
            chunk_type=ChunkType.STANDARD,
            context_quality_score=0.0,
            entities_extracted=[],
            keywords_for_search=[],
            enhancement_metadata={'error': error_msg}
        )
    
    def _update_stats(self, quality_score: float, processing_time: int, entity_count: int):
        """Update performance statistics."""
        self._stats['chunks_enhanced'] += 1
        self._stats['entities_extracted'] += entity_count
        self._stats['processing_times'].append(processing_time)
        
        # Update average quality score
        current_avg = self._stats['avg_quality_score']
        total = self._stats['chunks_enhanced']
        self._stats['avg_quality_score'] = (
            (current_avg * (total - 1) + quality_score) / total
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self._stats.copy()
        
        if stats['processing_times']:
            stats['avg_processing_time_ms'] = sum(stats['processing_times']) / len(stats['processing_times'])
            stats['min_processing_time_ms'] = min(stats['processing_times'])
            stats['max_processing_time_ms'] = max(stats['processing_times'])
        
        return stats
    
    async def clear_caches(self):
        """Clear all caches."""
        self._document_context_cache.clear()
        self._chunk_summary_cache.clear()
        self._entity_cache.clear()
        logger.info("All caches cleared")
    
    async def shutdown(self):
        """Shutdown the enhancer."""
        await self.clear_caches()
        logger.info("Anthropic Contextual Enhancer shutdown complete")