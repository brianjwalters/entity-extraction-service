"""
Hybrid chunking strategy that combines multiple approaches.
"""

from typing import List, Dict, Any, Optional
import logging

# CLAUDE.md Compliant: Absolute imports
from src.core.chunking.strategies.base_chunker import BaseChunker
from src.core.chunking.strategies.simple_chunker import SimpleChunker
from src.core.chunking.strategies.semantic_chunker import SemanticChunker
from src.models.responses import DocumentChunk

logger = logging.getLogger(__name__)


class HybridChunker(BaseChunker):
    """Combines multiple chunking strategies for optimal results."""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.simple_chunker = SimpleChunker(settings)
        self.semantic_chunker = SemanticChunker(settings)
        
        # Default strategy weights
        self.strategy_weights = getattr(settings, 'hybrid_strategy_weights', {
            'semantic': 0.7,
            'simple': 0.3
        })
    
    async def initialize(self):
        """Initialize all component chunkers."""
        await super().initialize()
        await self.simple_chunker.initialize()
        await self.semantic_chunker.initialize()
        logger.debug("HybridChunker initialized with component strategies")
    
    async def shutdown(self):
        """Shutdown component chunkers."""
        await self.simple_chunker.shutdown()
        await self.semantic_chunker.shutdown()
        await super().shutdown()
    
    async def chunk_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk text using hybrid approach.
        
        This method:
        1. Tries semantic chunking first
        2. Falls back to simple chunking for problematic sections
        3. Optimizes chunk boundaries
        4. Validates and refines results
        """
        self._validate_parameters(text, chunk_size, chunk_overlap)
        
        # Try semantic chunking first
        try:
            semantic_chunks = await self.semantic_chunker.chunk_text(
                text, chunk_size, chunk_overlap, metadata
            )
            
            # Evaluate semantic chunks quality
            if self._evaluate_chunks_quality(semantic_chunks, chunk_size):
                # Good quality - use semantic chunks with minor refinements
                refined_chunks = await self._refine_semantic_chunks(semantic_chunks, text)
                logger.debug(f"HybridChunker using refined semantic chunks: {len(refined_chunks)}")
                return refined_chunks
            else:
                # Poor quality - fall back to hybrid approach
                logger.debug("Semantic chunks quality insufficient, using hybrid approach")
                
        except Exception as e:
            logger.warning(f"Semantic chunking failed: {e}, falling back to hybrid approach")
        
        # Hybrid approach: combine strategies
        hybrid_chunks = await self._create_hybrid_chunks(text, chunk_size, chunk_overlap, metadata)
        
        logger.debug(f"HybridChunker created {len(hybrid_chunks)} chunks using hybrid approach")
        return hybrid_chunks
    
    def _evaluate_chunks_quality(self, chunks: List[DocumentChunk], target_size: int) -> bool:
        """Evaluate the quality of generated chunks."""
        if not chunks:
            return False
        
        quality_score = 0.0
        total_chunks = len(chunks)
        
        for chunk in chunks:
            chunk_score = 1.0
            
            # Size variance penalty
            size_ratio = len(chunk.content) / target_size
            if size_ratio < 0.3 or size_ratio > 2.0:  # Too small or too large
                chunk_score *= 0.5
            elif size_ratio < 0.5 or size_ratio > 1.5:
                chunk_score *= 0.8
            
            # Content quality
            if hasattr(chunk, 'quality_score') and chunk.quality_score:
                chunk_score *= chunk.quality_score
            
            # Boundary quality
            content = chunk.content.strip()
            if content:
                # Bonus for ending with punctuation
                if content.endswith(('.', '!', '?')):
                    chunk_score *= 1.1
                
                # Penalty for starting mid-word
                if not content[0].isupper() and not content[0].isspace():
                    chunk_score *= 0.9
            
            quality_score += chunk_score
        
        average_quality = quality_score / total_chunks
        return average_quality >= 0.7  # Threshold for acceptable quality
    
    async def _refine_semantic_chunks(
        self, 
        chunks: List[DocumentChunk], 
        original_text: str
    ) -> List[DocumentChunk]:
        """Refine semantic chunks to improve quality."""
        refined_chunks = []
        
        for i, chunk in enumerate(chunks):
            refined_chunk = chunk
            
            # Trim whitespace and improve boundaries
            content = chunk.content.strip()
            if content != chunk.content:
                # Recalculate positions
                original_start = original_text.find(content, chunk.start_position)
                if original_start >= 0:
                    refined_chunk = self._create_chunk(
                        content=content,
                        start_position=original_start,
                        end_position=original_start + len(content),
                        chunk_index=chunk.chunk_index,
                        metadata={
                            **(chunk.metadata or {}),
                            "chunking_strategy": "hybrid_refined_semantic",
                            "refined": True
                        }
                    )
            
            refined_chunks.append(refined_chunk)
        
        return refined_chunks
    
    async def _create_hybrid_chunks(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Create chunks using hybrid approach."""
        
        # Strategy 1: Identify natural breakpoints in the text
        breakpoints = self._identify_breakpoints(text)
        
        # Strategy 2: Create initial chunks respecting breakpoints
        initial_chunks = self._create_chunks_with_breakpoints(
            text, breakpoints, chunk_size, chunk_overlap
        )
        
        # Strategy 3: Optimize chunk boundaries
        optimized_chunks = await self._optimize_chunk_boundaries(initial_chunks, text)
        
        # Add hybrid metadata
        hybrid_chunks = []
        for i, chunk in enumerate(optimized_chunks):
            hybrid_chunk = self._create_chunk(
                content=chunk['content'],
                start_position=chunk['start'],
                end_position=chunk['end'],
                chunk_index=i,
                metadata={
                    **(metadata or {}),
                    "chunking_strategy": "hybrid",
                    "uses_breakpoints": True,
                    "boundary_optimized": True,
                    "strategy_weights": self.strategy_weights
                }
            )
            hybrid_chunks.append(hybrid_chunk)
        
        return hybrid_chunks
    
    def _identify_breakpoints(self, text: str) -> List[int]:
        """Identify natural breakpoints in text."""
        breakpoints = [0]  # Start of text
        
        # Add paragraph breaks
        current_pos = 0
        while True:
            pos = text.find('\n\n', current_pos)
            if pos == -1:
                break
            breakpoints.append(pos + 2)
            current_pos = pos + 2
        
        # Add sentence endings
        import re
        sentence_pattern = re.compile(r'[.!?]+\s+')
        for match in sentence_pattern.finditer(text):
            breakpoints.append(match.end())
        
        # Add section headers (common patterns)
        header_patterns = [
            re.compile(r'\n[A-Z][A-Z\s]+\n', re.MULTILINE),  # ALL CAPS headers
            re.compile(r'\n\d+\.\s+[A-Z]', re.MULTILINE),     # Numbered sections
            re.compile(r'\n[A-Z][a-z]+:', re.MULTILINE),      # Labeled sections
        ]
        
        for pattern in header_patterns:
            for match in pattern.finditer(text):
                breakpoints.append(match.start() + 1)
        
        # Remove duplicates and sort
        breakpoints = sorted(set(breakpoints))
        
        # Add end of text
        if breakpoints[-1] != len(text):
            breakpoints.append(len(text))
        
        return breakpoints
    
    def _create_chunks_with_breakpoints(
        self,
        text: str,
        breakpoints: List[int],
        chunk_size: int,
        chunk_overlap: int
    ) -> List[Dict[str, Any]]:
        """Create chunks respecting natural breakpoints."""
        chunks = []
        current_start = 0
        
        while current_start < len(text):
            # Find the best end position
            target_end = current_start + chunk_size
            
            # Find the nearest breakpoint before or at target_end
            best_end = target_end
            for bp in breakpoints:
                if current_start < bp <= target_end:
                    best_end = bp
                elif bp > target_end:
                    # If no good breakpoint found, use the next one if it's close
                    if bp - target_end < chunk_size * 0.2:  # Within 20% of chunk size
                        best_end = bp
                    break
            
            # Ensure minimum chunk size
            if best_end - current_start < chunk_size * 0.3:  # Less than 30% of target
                best_end = min(current_start + chunk_size, len(text))
            
            # Create chunk
            content = text[current_start:best_end].strip()
            if content:
                chunks.append({
                    'content': content,
                    'start': current_start,
                    'end': best_end
                })
            
            # Move to next position with overlap
            if best_end >= len(text):
                break
            
            current_start = max(best_end - chunk_overlap, current_start + 1)
        
        return chunks
    
    async def _optimize_chunk_boundaries(
        self, 
        chunks: List[Dict[str, Any]], 
        text: str
    ) -> List[Dict[str, Any]]:
        """Optimize chunk boundaries for better readability."""
        optimized_chunks = []
        
        for chunk_data in chunks:
            content = chunk_data['content']
            start = chunk_data['start']
            end = chunk_data['end']
            
            # Trim leading/trailing whitespace
            trimmed_content = content.strip()
            if trimmed_content != content:
                # Recalculate positions
                trim_start = content.find(trimmed_content)
                trim_end = trim_start + len(trimmed_content)
                start = start + trim_start
                end = start + len(trimmed_content)
                content = trimmed_content
            
            # Ensure we don't have empty chunks
            if content:
                optimized_chunks.append({
                    'content': content,
                    'start': start,
                    'end': end
                })
        
        return optimized_chunks