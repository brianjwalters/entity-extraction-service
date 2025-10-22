"""
Base chunker class for all chunking strategies.
"""

import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

# CLAUDE.md Compliant: Absolute import
from src.models.responses import DocumentChunk

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """Base class for all chunking strategies."""
    
    def __init__(self, settings):
        self.settings = settings
        self.name = self.__class__.__name__
        
    async def initialize(self):
        """Initialize the chunker. Override if needed."""
        logger.debug(f"Initializing {self.name}")
        
    async def shutdown(self):
        """Shutdown the chunker. Override if needed."""
        logger.debug(f"Shutting down {self.name}")
    
    @abstractmethod
    async def chunk_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk the given text into segments.
        
        Args:
            text: Text to chunk
            chunk_size: Target size for each chunk
            chunk_overlap: Overlap between chunks
            metadata: Additional metadata
            
        Returns:
            List of DocumentChunk objects
        """
        pass
    
    def _create_chunk(
        self,
        content: str,
        start_position: int,
        end_position: int,
        chunk_index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentChunk:
        """Create a DocumentChunk object."""
        return DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            content=content,
            start_position=start_position,
            end_position=end_position,
            chunk_index=chunk_index,
            character_count=len(content),
            metadata=metadata or {}
        )
    
    def _validate_parameters(self, text: str, chunk_size: int, chunk_overlap: int):
        """Validate chunking parameters."""
        if not text:
            raise ValueError("Text cannot be empty")
        
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
            
        if chunk_overlap < 0:
            raise ValueError("Chunk overlap cannot be negative")
            
        if chunk_overlap >= chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
    
    def _calculate_positions(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[tuple]:
        """
        Calculate start and end positions for chunks.
        
        Returns:
            List of (start_pos, end_pos) tuples
        """
        positions = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            positions.append((start, end))
            
            # Move to next position with overlap
            if end >= text_length:
                break
                
            start = end - chunk_overlap
            
            # Avoid infinite loop if overlap equals chunk size
            if start <= positions[-1][0] if positions else 0:
                start = end
        
        return positions
    
    def _adjust_boundaries(
        self,
        text: str,
        start: int,
        end: int,
        preserve_words: bool = True,
        preserve_sentences: bool = False
    ) -> tuple:
        """
        Adjust chunk boundaries to avoid cutting words or sentences.
        
        Args:
            text: Full text
            start: Initial start position
            end: Initial end position
            preserve_words: Avoid cutting words
            preserve_sentences: Avoid cutting sentences
            
        Returns:
            Adjusted (start, end) positions
        """
        adjusted_start = start
        adjusted_end = end
        
        # Adjust start position (move forward to avoid cutting words)
        if preserve_words and start > 0:
            # Look for word boundary
            while adjusted_start > 0 and not text[adjusted_start].isspace():
                adjusted_start += 1
        
        # Adjust end position (move backward to avoid cutting words/sentences)
        if preserve_sentences:
            # Look for sentence boundary
            sentence_endings = '.!?'
            while adjusted_end > adjusted_start and adjusted_end < len(text):
                if text[adjusted_end-1] in sentence_endings:
                    break
                adjusted_end -= 1
        elif preserve_words:
            # Look for word boundary
            while adjusted_end > adjusted_start and adjusted_end < len(text):
                if text[adjusted_end].isspace():
                    break
                adjusted_end -= 1
        
        # Ensure we have meaningful content
        if adjusted_end <= adjusted_start:
            adjusted_end = min(end, len(text))
        
        return adjusted_start, adjusted_end
    
    def _get_chunk_quality_score(self, content: str) -> float:
        """Calculate a quality score for a chunk (0.0 to 1.0)."""
        if not content or not content.strip():
            return 0.0
        
        score = 1.0
        
        # Penalize very short chunks
        if len(content) < 50:
            score *= 0.5
        
        # Bonus for chunks that end with punctuation
        if content.rstrip().endswith(('.', '!', '?')):
            score *= 1.1
        
        # Penalize chunks with too many incomplete words
        words = content.split()
        if words:
            incomplete_words = sum(1 for word in words if not word.isalnum())
            incomplete_ratio = incomplete_words / len(words)
            score *= (1.0 - incomplete_ratio * 0.5)
        
        return min(score, 1.0)