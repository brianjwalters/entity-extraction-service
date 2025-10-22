"""
Smart Document Chunking Module

This module provides intelligent document chunking with context preservation,
optimized for legal documents. It maintains semantic boundaries, preserves
citations across chunks, and adds contextual markers for AI processing.
"""

import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

# Download required NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    import ssl
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    nltk.download('punkt', quiet=True)


class BoundaryType(Enum):
    """Types of boundaries for chunking."""
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    WORD = "word"
    CITATION = "citation"
    SECTION = "section"


@dataclass
class DocumentChunk:
    """Represents a single chunk of a document."""
    text: str
    start_pos: int
    end_pos: int
    chunk_index: int
    total_chunks: int
    is_complete_doc: bool
    overlap_start: Optional[int] = None
    overlap_end: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def char_count(self) -> int:
        """Get character count of chunk."""
        return len(self.text)
    
    @property
    def has_overlap(self) -> bool:
        """Check if chunk has overlap regions."""
        return self.overlap_start is not None or self.overlap_end is not None


class DocumentChunker:
    """
    Smart document chunking with context preservation.
    
    This chunker intelligently splits documents while:
    - Preserving semantic boundaries (paragraphs, sentences)
    - Maintaining legal citations intact
    - Adding overlap for context continuity
    - Including contextual markers for AI understanding
    """
    
    # Citation patterns to preserve
    CITATION_PATTERNS = [
        r'\d+\s+U\.S\.C\.\s+§?\s*\d+',           # U.S.C. citations
        r'\d+\s+F\.\d+d\s+\d+',                  # Federal Reporter
        r'\d+\s+S\.\s*Ct\.\s+\d+',               # Supreme Court Reporter
        r'\d+\s+L\.\s*Ed\.\s*2d\s+\d+',          # Lawyers' Edition
        r'(?:No\.|Case)\s+\d+-\w+-\d+',          # Case numbers
        r'\d+\s+\w+\.\s*App\.\s*\d+d?\s+\d+',    # State reporters
    ]
    
    def __init__(
        self,
        max_chunk_size: int = 57700,  # ~75K tokens
        overlap_ratio: float = 0.15,   # 15% overlap
        min_chunk_size: int = 10000,   # Minimum viable chunk
        preserve_citations: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the document chunker.
        
        Args:
            max_chunk_size: Maximum characters per chunk
            overlap_ratio: Overlap ratio between chunks (0-0.5)
            min_chunk_size: Minimum chunk size in characters
            preserve_citations: Whether to preserve citation integrity
            logger: Optional logger instance
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_ratio = min(0.5, max(0, overlap_ratio))  # Clamp to 0-0.5
        self.overlap_size = int(max_chunk_size * overlap_ratio)
        self.min_chunk_size = min_chunk_size
        self.preserve_citations = preserve_citations
        self.logger = logger or logging.getLogger(__name__)
        
        # Compile citation patterns
        if preserve_citations:
            self.citation_regex = re.compile(
                '|'.join(self.CITATION_PATTERNS),
                re.IGNORECASE
            )
    
    def chunk_document(
        self,
        document: str,
        estimated_tokens: Optional[int] = None,
        force_chunking: bool = False
    ) -> List[DocumentChunk]:
        """
        Create overlapping chunks with smart boundaries.
        
        Args:
            document: Document text to chunk
            estimated_tokens: Optional pre-calculated token estimate
            force_chunking: Force chunking even for small documents
            
        Returns:
            List of DocumentChunk objects
        """
        # Quick check - is chunking needed?
        if not force_chunking and len(document) <= self.max_chunk_size:
            return [DocumentChunk(
                text=document,
                start_pos=0,
                end_pos=len(document),
                chunk_index=0,
                total_chunks=1,
                is_complete_doc=True,
                metadata={"chunking_reason": "document_within_limit"}
            )]
        
        # Split document into processable units
        paragraphs = self._split_into_paragraphs(document)
        sentences = self._split_into_sentences(document)
        
        # Create chunks
        chunks = []
        current_pos = 0
        chunk_index = 0
        doc_length = len(document)
        
        while current_pos < doc_length:
            # Find optimal chunk end
            ideal_end = min(current_pos + self.max_chunk_size, doc_length)
            
            # Find best boundary for chunk end
            chunk_end = self._find_optimal_boundary(
                document,
                current_pos,
                ideal_end,
                paragraphs,
                sentences
            )
            
            # Ensure minimum chunk size
            if chunk_end - current_pos < self.min_chunk_size and chunk_end < doc_length:
                chunk_end = min(current_pos + self.min_chunk_size, doc_length)
            
            # Extract chunk text
            chunk_text = document[current_pos:chunk_end]
            
            # Add context markers
            chunk_text = self._add_context_markers(
                chunk_text,
                chunk_index,
                current_pos > 0,
                chunk_end < doc_length
            )
            
            # Calculate overlap boundaries
            overlap_start = None
            overlap_end = None
            
            if chunk_index > 0:
                overlap_start = max(0, current_pos - self.overlap_size)
            
            if chunk_end < doc_length:
                overlap_end = min(doc_length, chunk_end + self.overlap_size)
            
            # Create chunk object
            chunks.append(DocumentChunk(
                text=chunk_text,
                start_pos=current_pos,
                end_pos=chunk_end,
                chunk_index=chunk_index,
                total_chunks=-1,  # Will be updated after all chunks created
                is_complete_doc=False,
                overlap_start=overlap_start,
                overlap_end=overlap_end,
                metadata={
                    "boundary_type": self._get_boundary_type(document, chunk_end),
                    "has_citations": bool(self.citation_regex.search(chunk_text)) if self.preserve_citations else False
                }
            ))
            
            # Move to next chunk with overlap
            if chunk_end >= doc_length:
                break
                
            next_start = chunk_end - self.overlap_size
            
            # Ensure progress
            if next_start <= current_pos:
                next_start = chunk_end
            
            current_pos = next_start
            chunk_index += 1
        
        # Update total_chunks for all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total_chunks
        
        self.logger.info(
            f"Document chunked: {doc_length:,} chars → {total_chunks} chunks "
            f"(avg {doc_length // total_chunks:,} chars/chunk)"
        )
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[Tuple[int, int]]:
        """
        Split text into paragraph boundaries.
        
        Args:
            text: Document text
            
        Returns:
            List of (start, end) positions for each paragraph
        """
        paragraphs = []
        
        # Find double newline positions (paragraph breaks)
        for match in re.finditer(r'\n\n+', text):
            paragraphs.append((match.start(), match.end()))
        
        # Add document boundaries
        if not paragraphs or paragraphs[0][0] > 0:
            paragraphs.insert(0, (0, 0))
        if not paragraphs or paragraphs[-1][1] < len(text):
            paragraphs.append((len(text), len(text)))
        
        return paragraphs
    
    def _split_into_sentences(self, text: str) -> List[Tuple[int, int]]:
        """
        Split text into sentence boundaries.
        
        Args:
            text: Document text
            
        Returns:
            List of (start, end) positions for each sentence
        """
        sentences = []
        
        try:
            # Use NLTK sentence tokenizer
            sent_tokens = sent_tokenize(text)
            current_pos = 0
            
            for sent in sent_tokens:
                start = text.find(sent, current_pos)
                if start != -1:
                    end = start + len(sent)
                    sentences.append((start, end))
                    current_pos = end
        except Exception as e:
            self.logger.warning(f"Sentence tokenization failed: {e}, using fallback")
            
            # Fallback to simple sentence detection
            for match in re.finditer(r'[.!?]\s+', text):
                sentences.append((match.start(), match.end()))
        
        return sentences
    
    def _find_optimal_boundary(
        self,
        text: str,
        start: int,
        ideal_end: int,
        paragraphs: List[Tuple[int, int]],
        sentences: List[Tuple[int, int]]
    ) -> int:
        """
        Find the best boundary for chunk end.
        
        Priority order:
        1. Paragraph boundary
        2. Sentence boundary
        3. Citation boundary (if preserving)
        4. Word boundary
        5. Fallback to ideal_end
        
        Args:
            text: Document text
            start: Chunk start position
            ideal_end: Ideal chunk end position
            paragraphs: List of paragraph boundaries
            sentences: List of sentence boundaries
            
        Returns:
            Optimal chunk end position
        """
        # Search window around ideal_end
        search_start = max(start + self.min_chunk_size, ideal_end - 1000)
        search_end = min(len(text), ideal_end + 1000)
        
        # 1. Look for paragraph break
        for para_start, para_end in paragraphs:
            if search_start <= para_end <= search_end:
                return para_end
        
        # 2. Look for sentence boundary
        best_sentence_end = None
        min_distance = float('inf')
        
        for sent_start, sent_end in sentences:
            if search_start <= sent_end <= search_end:
                distance = abs(sent_end - ideal_end)
                if distance < min_distance:
                    min_distance = distance
                    best_sentence_end = sent_end
        
        if best_sentence_end:
            return best_sentence_end
        
        # 3. Check for citation boundary (avoid splitting citations)
        if self.preserve_citations:
            # Check if we're in the middle of a citation
            citation_check = text[max(0, ideal_end - 100):min(len(text), ideal_end + 100)]
            citation_match = self.citation_regex.search(citation_check)
            
            if citation_match:
                # Adjust to avoid splitting the citation
                citation_global_start = max(0, ideal_end - 100) + citation_match.start()
                citation_global_end = max(0, ideal_end - 100) + citation_match.end()
                
                if citation_global_start <= ideal_end <= citation_global_end:
                    # We're in the middle of a citation, move to its end
                    return min(citation_global_end + 1, len(text))
        
        # 4. Fall back to word boundary
        space_before = text.rfind(' ', start, ideal_end)
        space_after = text.find(' ', ideal_end, min(len(text), ideal_end + 100))
        
        if space_before != -1 and space_after != -1:
            # Choose closest space
            if ideal_end - space_before < space_after - ideal_end:
                return space_before + 1
            else:
                return space_after + 1
        elif space_before != -1:
            return space_before + 1
        elif space_after != -1:
            return space_after + 1
        
        # 5. Fallback to ideal_end
        return ideal_end
    
    def _add_context_markers(
        self,
        chunk_text: str,
        chunk_index: int,
        has_previous: bool,
        has_next: bool
    ) -> str:
        """
        Add context markers to help AI understand chunk position.
        
        Args:
            chunk_text: Original chunk text
            chunk_index: Index of this chunk
            has_previous: Whether there's a previous chunk
            has_next: Whether there's a next chunk
            
        Returns:
            Text with context markers added
        """
        markers = []
        
        # Add header marker
        if has_previous:
            markers.append(f"[...Document Section {chunk_index + 1} - Continued from previous section...]")
            markers.append("")
        else:
            markers.append(f"[Document Section {chunk_index + 1} - Beginning]")
            markers.append("")
        
        # Add the main content
        markers.append(chunk_text.strip())
        
        # Add footer marker
        if has_next:
            markers.append("")
            markers.append("[...Continues in next section...]")
        else:
            markers.append("")
            markers.append("[Document End]")
        
        return "\n".join(markers)
    
    def _get_boundary_type(self, text: str, position: int) -> str:
        """
        Determine the type of boundary at a given position.
        
        Args:
            text: Document text
            position: Position to check
            
        Returns:
            Boundary type as string
        """
        if position >= len(text):
            return "document_end"
        
        # Check for paragraph boundary
        if position > 1 and text[position-2:position] == "\n\n":
            return "paragraph"
        
        # Check for sentence boundary
        if position > 0 and text[position-1] in '.!?':
            return "sentence"
        
        # Check for word boundary
        if position > 0 and text[position-1] == ' ':
            return "word"
        
        return "arbitrary"
    
    def merge_overlapping_results(
        self,
        chunk_results: List[Dict[str, Any]],
        chunks: List[DocumentChunk]
    ) -> Dict[str, Any]:
        """
        Merge results from overlapping chunks, removing duplicates.
        
        Args:
            chunk_results: Results from each chunk
            chunks: Original chunk objects
            
        Returns:
            Merged results with duplicates removed
        """
        # This is a placeholder - actual implementation would be in result_merger.py
        # Shown here for completeness
        merged = {
            "entities": [],
            "citations": [],
            "metadata": {
                "chunks_processed": len(chunks),
                "chunking_strategy": "smart_boundaries"
            }
        }
        
        # Would implement deduplication logic here
        
        return merged


if __name__ == "__main__":
    # Test the chunker
    from token_estimator import TokenEstimator
    
    logging.basicConfig(level=logging.INFO)
    
    # Create test document
    test_doc = """
    This is a test legal document with multiple paragraphs.
    
    The case of Smith v. Jones, 123 U.S. 456 (2020), established important precedent
    regarding contract interpretation. The court held that ambiguous terms should be
    construed against the drafter. See also Brown v. Green, 789 F.3d 101 (9th Cir. 2019).
    
    Another paragraph discusses procedural matters. The Federal Rules of Civil Procedure,
    particularly Rule 12(b)(6), provide the framework for motions to dismiss. Courts must
    accept all well-pleaded facts as true when evaluating such motions.
    
    """ * 100  # Repeat to create larger document
    
    # Test chunking
    chunker = DocumentChunker()
    chunks = chunker.chunk_document(test_doc)
    
    print(f"Document size: {len(test_doc):,} characters")
    print(f"Created {len(chunks)} chunks\n")
    
    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
        print(f"Chunk {i + 1}:")
        print(f"  Position: {chunk.start_pos:,} - {chunk.end_pos:,}")
        print(f"  Size: {chunk.char_count:,} chars")
        print(f"  Boundary: {chunk.metadata.get('boundary_type')}")
        print(f"  Has citations: {chunk.metadata.get('has_citations')}")
        print(f"  Preview: {chunk.text[:100]}...")
        print()