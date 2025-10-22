"""
Extraction-focused chunking strategy for AI entity extraction.

This chunker is optimized for AI-based entity extraction by creating larger chunks
that provide more context to the language model while minimizing overlap to avoid
duplicate entity extraction.
"""

import re
from typing import List, Dict, Any, Optional
import logging

# CLAUDE.md Compliant: Absolute imports
from src.core.chunking.strategies.base_chunker import BaseChunker
from src.models.responses import DocumentChunk

logger = logging.getLogger(__name__)


class ExtractionChunker(BaseChunker):
    """
    Chunking strategy optimized for AI entity extraction.
    
    Creates larger chunks (8000 chars) with minimal overlap (500 chars) to:
    - Provide sufficient context for AI models to understand entities
    - Minimize duplicate entity extraction across chunks
    - Preserve legal document boundaries (paragraphs, sentences, citations)
    """
    
    # Default settings for extraction-optimized chunking
    DEFAULT_CHUNK_SIZE = 8000  # 8K characters for more context
    DEFAULT_OVERLAP = 500  # Minimal overlap to avoid duplicates
    
    # Legal citation pattern to avoid breaking citations
    CITATION_PATTERN = re.compile(
        r'\b\d+\s+[A-Z][a-z]+\.?\s*\d+[a-z]?\s*\d*\b|'  # Volume reporter citations
        r'\b[A-Z][a-z]+\.\s*\d+[a-z]?\s*at\s*\d+\b|'    # Page citations
        r'\b§+\s*\d+[\.\d]*\b|'                          # Section citations
        r'\bId\.\s*at\s*\d+\b'                           # Id. citations
    )
    
    # Sentence boundary pattern
    SENTENCE_END_PATTERN = re.compile(r'[.!?]\s+(?=[A-Z])')
    
    # Paragraph boundary pattern (double newline or indentation)
    PARAGRAPH_PATTERN = re.compile(r'\n\s*\n|\n\t+|\n {4,}')
    
    async def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk text optimized for AI entity extraction.
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size (defaults to 8000 for extraction)
            chunk_overlap: Overlap between chunks (defaults to 500)
            metadata: Additional metadata
            
        Returns:
            List of DocumentChunk objects optimized for entity extraction
        """
        # Use extraction-optimized defaults if not specified
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        chunk_overlap = chunk_overlap or self.DEFAULT_OVERLAP
        
        # Validate parameters
        self._validate_parameters(text, chunk_size, chunk_overlap)
        
        # Pre-process text to identify important boundaries
        boundaries = self._identify_legal_boundaries(text)
        
        chunks = []
        current_pos = 0
        chunk_index = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # Calculate ideal chunk end position
            ideal_end = min(current_pos + chunk_size, text_length)
            
            # Find best boundary near ideal position
            chunk_end = self._find_optimal_boundary(
                text, current_pos, ideal_end, boundaries
            )
            
            # Extract chunk content
            content = text[current_pos:chunk_end].strip()
            
            if content:
                # Calculate chunk statistics
                word_count = len(content.split())
                sentence_count = len(self.SENTENCE_END_PATTERN.findall(content))
                
                # Check if chunk contains legal citations
                has_citations = bool(self.CITATION_PATTERN.search(content))
                
                chunk = self._create_chunk(
                    content=content,
                    start_position=current_pos,
                    end_position=chunk_end,
                    chunk_index=chunk_index,
                    metadata={
                        **(metadata or {}),
                        "chunking_strategy": "extraction",
                        "optimized_for": "ai_entity_extraction",
                        "chunk_size_target": chunk_size,
                        "overlap_size": chunk_overlap,
                        "word_count": word_count,
                        "sentence_count": sentence_count,
                        "has_legal_citations": has_citations,
                        "boundary_type": self._get_boundary_type(text, chunk_end)
                    }
                )
                
                # Add quality score based on extraction suitability
                chunk.quality_score = self._calculate_extraction_quality(content)
                chunk.word_count = word_count
                chunk.sentence_count = sentence_count
                
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next chunk position with minimal overlap
            if chunk_end >= text_length:
                break
            
            # Use minimal overlap for extraction to avoid duplicates
            current_pos = chunk_end - chunk_overlap
            
            # Ensure forward progress
            if current_pos <= chunks[-1].start_position if chunks else 0:
                current_pos = chunk_end
        
        logger.info(
            f"ExtractionChunker created {len(chunks)} chunks from {len(text)} characters "
            f"(avg size: {sum(c.character_count for c in chunks) / len(chunks):.0f} chars)"
        )
        
        return chunks
    
    def _identify_legal_boundaries(self, text: str) -> Dict[str, List[int]]:
        """
        Identify important boundaries in legal text.
        
        Returns:
            Dictionary mapping boundary types to positions
        """
        boundaries = {
            'paragraphs': [],
            'sentences': [],
            'citations': [],
            'sections': []
        }
        
        # Find paragraph boundaries
        for match in self.PARAGRAPH_PATTERN.finditer(text):
            boundaries['paragraphs'].append(match.end())
        
        # Find sentence boundaries
        for match in self.SENTENCE_END_PATTERN.finditer(text):
            boundaries['sentences'].append(match.end())
        
        # Find citation boundaries (end of citations)
        for match in self.CITATION_PATTERN.finditer(text):
            boundaries['citations'].append(match.end())
        
        # Find section headers (numbered sections)
        section_pattern = re.compile(r'\n\s*(?:\d+\.|\([a-z]\)|\([0-9]+\))\s+')
        for match in section_pattern.finditer(text):
            boundaries['sections'].append(match.start())
        
        return boundaries
    
    def _find_optimal_boundary(
        self,
        text: str,
        start: int,
        ideal_end: int,
        boundaries: Dict[str, List[int]]
    ) -> int:
        """
        Find the optimal chunk boundary near the ideal position.
        
        Prioritizes:
        1. Paragraph boundaries (strongest semantic break)
        2. Section boundaries (logical divisions)
        3. Sentence boundaries (complete thoughts)
        4. Citation boundaries (avoid breaking citations)
        5. Word boundaries (fallback)
        """
        # Search window for boundaries (10% of chunk size)
        search_window = int(self.DEFAULT_CHUNK_SIZE * 0.1)
        min_pos = max(start + self.DEFAULT_CHUNK_SIZE // 2, ideal_end - search_window)
        max_pos = min(len(text), ideal_end + search_window // 4)  # Prefer earlier boundaries
        
        # Priority order for boundary types
        boundary_priority = ['paragraphs', 'sections', 'sentences', 'citations']
        
        for boundary_type in boundary_priority:
            boundary_positions = boundaries.get(boundary_type, [])
            
            # Find boundaries within search window
            candidates = [
                pos for pos in boundary_positions
                if min_pos <= pos <= max_pos
            ]
            
            if candidates:
                # Choose boundary closest to ideal position
                return min(candidates, key=lambda x: abs(x - ideal_end))
        
        # Fallback: Find word boundary
        return self._find_word_boundary(text, ideal_end)
    
    def _find_word_boundary(self, text: str, position: int) -> int:
        """Find the nearest word boundary to the given position."""
        if position >= len(text):
            return len(text)
        
        # Look backward for space
        for i in range(position, max(position - 100, 0), -1):
            if text[i].isspace():
                return i
        
        # Look forward if no space found backward
        for i in range(position, min(position + 100, len(text))):
            if text[i].isspace():
                return i
        
        # Return original position if no boundary found
        return position
    
    def _get_boundary_type(self, text: str, position: int) -> str:
        """Determine what type of boundary ends at this position."""
        if position >= len(text):
            return "document_end"
        
        # Check for paragraph boundary
        if position > 1 and text[position-2:position] == '\n\n':
            return "paragraph"
        
        # Check for sentence boundary
        if position > 0 and text[position-1] in '.!?':
            return "sentence"
        
        # Check if we're at a section header
        if position < len(text) - 10:
            next_text = text[position:position+10]
            if re.match(r'^\s*(?:\d+\.|\([a-z]\))', next_text):
                return "section"
        
        return "word"
    
    def _calculate_extraction_quality(self, content: str) -> float:
        """
        Calculate quality score for entity extraction suitability.
        
        Higher scores indicate better suitability for extraction.
        """
        if not content or not content.strip():
            return 0.0
        
        score = 1.0
        content_length = len(content)
        
        # Ideal length for extraction (6000-10000 characters)
        if 6000 <= content_length <= 10000:
            score *= 1.2
        elif content_length < 2000:
            score *= 0.7  # Too short for good context
        elif content_length > 12000:
            score *= 0.9  # Might be too long for model context
        
        # Check for complete sentences
        sentence_count = len(self.SENTENCE_END_PATTERN.findall(content))
        if sentence_count > 5:
            score *= 1.1
        
        # Check for legal citations (good for entity extraction)
        if self.CITATION_PATTERN.search(content):
            score *= 1.15
        
        # Check for section structure
        if re.search(r'\n\s*(?:\d+\.|\([a-z]\))', content):
            score *= 1.1
        
        # Penalize chunks that start or end mid-word
        if content and not content[0].isupper() and not content[0].isdigit():
            score *= 0.95  # Likely starts mid-sentence
        
        if content and content[-1].isalpha():
            score *= 0.95  # Likely ends mid-word
        
        # Ensure score stays within bounds
        return min(max(score, 0.0), 1.0)