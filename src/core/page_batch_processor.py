"""
PageBatch Processor for Document-to-Pages Conversion

This module provides sophisticated page-batch processing for legal document analysis.
It handles document pagination, context preservation across batches, and optimized
batch size calculation for comprehensive entity extraction with 195+ entity types.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ..models.extraction_strategy import PageBatchConfig

logger = logging.getLogger(__name__)

@dataclass
class DocumentPage:
    """Represents a single page of a document."""
    page_number: int
    content: str
    word_count: int
    char_count: int
    estimated_complexity: str  # low, medium, high
    
    @property
    def is_substantial(self) -> bool:
        """Check if page has substantial content (>50 words)."""
        return self.word_count > 50

@dataclass
class PageBatch:
    """Represents a batch of document pages for processing."""
    batch_id: int
    pages: List[DocumentPage]
    start_page: int
    end_page: int
    combined_content: str
    word_count: int
    char_count: int
    estimated_complexity: str
    context_overlap: str  # Content overlapping with previous batch
    
    @property
    def page_range(self) -> str:
        """Get formatted page range."""
        if self.start_page == self.end_page:
            return f"Page {self.start_page}"
        return f"Pages {self.start_page}-{self.end_page}"

class PageBatchProcessor:
    """
    Advanced page-batch processor for legal document entity extraction.
    
    This processor intelligently divides documents into pages and creates
    optimized batches for comprehensive entity extraction with context preservation.
    """
    
    def __init__(self, config: Optional[PageBatchConfig] = None):
        """Initialize the PageBatch processor."""
        self.config = config or PageBatchConfig()
        self.logger = logging.getLogger(f"{__name__}.PageBatchProcessor")
        
    def process_document(self, content: str, document_metadata: Dict[str, Any] = None) -> List[PageBatch]:
        """
        Process a document into optimized page batches.
        
        Args:
            content: Full document text
            document_metadata: Optional metadata about the document
            
        Returns:
            List of PageBatch objects ready for entity extraction
        """
        self.logger.info(f"Processing document into page batches (batch_size: {self.config.batch_size})")
        
        # Split document into pages
        pages = self._split_into_pages(content)
        self.logger.info(f"Document split into {len(pages)} pages")
        
        # Create batches from pages
        batches = self._create_batches(pages)
        self.logger.info(f"Created {len(batches)} batches for processing")
        
        # Add context overlap if enabled
        if self.config.overlap_pages > 0:
            batches = self._add_context_overlap(batches, pages)
            
        return batches
    
    def _split_into_pages(self, content: str) -> List[DocumentPage]:
        """Split document content into individual pages."""
        
        # Method 1: Look for explicit page breaks
        page_breaks = [
            r'\f',  # Form feed character
            r'\n\s*Page\s+\d+\s*\n',  # "Page X" markers
            r'\n\s*-\s*\d+\s*-\s*\n',  # "- X -" page numbers
            r'\n\s*\d+\s*\n\s*\n',  # Standalone page numbers
        ]
        
        # Try to find explicit page breaks
        for pattern in page_breaks:
            if re.search(pattern, content, re.IGNORECASE):
                pages_content = re.split(pattern, content, flags=re.IGNORECASE)
                if len(pages_content) > 1:
                    return self._create_pages_from_content(pages_content)
        
        # Method 2: Heuristic page splitting based on content patterns
        pages_content = self._heuristic_page_split(content)
        return self._create_pages_from_content(pages_content)
    
    def _heuristic_page_split(self, content: str) -> List[str]:
        """Use heuristics to split content into logical pages."""
        
        # For legal documents, look for section breaks, case boundaries, etc.
        split_patterns = [
            r'\n\s*(?:CASE\s+NO\.?|Case\s+Number)\s*:?\s*\d+',  # Case number headers
            r'\n\s*(?:IN\s+THE\s+(?:UNITED\s+STATES\s+)?(?:DISTRICT\s+)?COURT)',  # Court headers
            r'\n\s*(?:UNITED\s+STATES\s+(?:DISTRICT\s+)?COURT)',  # US Court headers
            r'\n\s*(?:SUPERIOR\s+COURT\s+OF)',  # Superior court headers
            r'\n\s*(?:STATE\s+OF\s+\w+)',  # State headers
            r'\n\s*(?:BEFORE\s+THE\s+)',  # Administrative headers
            r'\n\s*(?:ORDER\s*(?:GRANTING|DENYING)?)',  # Order headers
            r'\n\s*(?:MEMORANDUM\s+(?:OPINION\s+)?(?:AND\s+)?ORDER)',  # Memorandum headers
        ]
        
        # Try splitting on legal document boundaries
        for pattern in split_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            if len(matches) > 1:
                pages = []
                start = 0
                for match in matches[1:]:  # Skip first match
                    pages.append(content[start:match.start()].strip())
                    start = match.start()
                pages.append(content[start:].strip())  # Last page
                
                # Filter out very short pages
                substantial_pages = [p for p in pages if len(p.split()) > 20]
                if len(substantial_pages) > 1:
                    return substantial_pages
        
        # Method 3: Split by estimated word count per page
        # Assume ~250-400 words per page for legal documents
        words = content.split()
        words_per_page = min(400, max(250, len(words) // max(1, len(words) // 400)))
        
        pages = []
        for i in range(0, len(words), words_per_page):
            page_words = words[i:i + words_per_page]
            page_content = ' '.join(page_words)
            if page_content.strip():
                pages.append(page_content.strip())
        
        return pages if pages else [content]
    
    def _create_pages_from_content(self, pages_content: List[str]) -> List[DocumentPage]:
        """Convert page content strings to DocumentPage objects."""
        pages = []
        
        for i, content in enumerate(pages_content, 1):
            content = content.strip()
            if not content:
                continue
                
            word_count = len(content.split())
            char_count = len(content)
            
            # Estimate complexity based on legal indicators
            complexity = self._estimate_page_complexity(content)
            
            page = DocumentPage(
                page_number=i,
                content=content,
                word_count=word_count,
                char_count=char_count,
                estimated_complexity=complexity
            )
            pages.append(page)
        
        return pages
    
    def _estimate_page_complexity(self, content: str) -> str:
        """Estimate the complexity of a page based on legal content indicators."""
        
        # High complexity indicators
        high_complexity_patterns = [
            r'\b(?:whereas|notwithstanding|heretofore|hereinafter)\b',  # Complex legal language
            r'\b(?:pursuant\s+to|in\s+accordance\s+with)\b',  # Formal legal phrases
            r'\(\w+\)\s*\([^\)]+\)',  # Nested citations
            r'\b\d+\s+U\.?S\.?C\.?\s*§?\s*\d+',  # USC citations
            r'\b\d+\s+F\.\d+\s+\d+',  # Federal reporter citations
            r'\bsee\s+also\b.*?\bcompare\b',  # Complex citation signals
        ]
        
        # Medium complexity indicators  
        medium_complexity_patterns = [
            r'\b(?:plaintiff|defendant|appellant|appellee)\b',  # Party references
            r'\b(?:motion|brief|order|judgment)\b',  # Legal documents
            r'\b\d+\s*U\.?S\.?C\.?\s*\d+',  # Simple USC citations
            r'\bCase\s+No\.?\s*\d+',  # Case numbers
            r'\b(?:court|judge|jury)\b',  # Court terminology
        ]
        
        content_lower = content.lower()
        
        high_matches = sum(1 for pattern in high_complexity_patterns 
                          if re.search(pattern, content_lower, re.IGNORECASE))
        medium_matches = sum(1 for pattern in medium_complexity_patterns 
                           if re.search(pattern, content_lower, re.IGNORECASE))
        
        if high_matches >= 3:
            return "high"
        elif high_matches >= 1 or medium_matches >= 3:
            return "medium"
        else:
            return "low"
    
    def _create_batches(self, pages: List[DocumentPage]) -> List[PageBatch]:
        """Create optimized batches from document pages."""
        batches = []
        batch_id = 1
        
        i = 0
        while i < len(pages):
            # Determine batch size (may be adaptive)
            batch_size = self._calculate_optimal_batch_size(pages[i:])
            batch_pages = pages[i:i + batch_size]
            
            if not batch_pages:
                break
            
            # Combine content from all pages in batch
            combined_content = self._combine_page_content(batch_pages)
            
            # Calculate batch statistics
            total_words = sum(page.word_count for page in batch_pages)
            total_chars = sum(page.char_count for page in batch_pages)
            
            # Determine overall batch complexity
            complexity_scores = {"low": 0, "medium": 1, "high": 2}
            avg_complexity = sum(complexity_scores[page.estimated_complexity] for page in batch_pages) / len(batch_pages)
            batch_complexity = "low" if avg_complexity < 0.5 else "medium" if avg_complexity < 1.5 else "high"
            
            batch = PageBatch(
                batch_id=batch_id,
                pages=batch_pages,
                start_page=batch_pages[0].page_number,
                end_page=batch_pages[-1].page_number,
                combined_content=combined_content,
                word_count=total_words,
                char_count=total_chars,
                estimated_complexity=batch_complexity,
                context_overlap=""  # Will be filled by _add_context_overlap if needed
            )
            
            batches.append(batch)
            batch_id += 1
            i += batch_size
            
        return batches
    
    def _calculate_optimal_batch_size(self, remaining_pages: List[DocumentPage]) -> int:
        """Calculate optimal batch size based on page characteristics."""
        
        if not remaining_pages:
            return self.config.batch_size
            
        # For complex pages, use smaller batches
        complex_pages = sum(1 for page in remaining_pages[:self.config.batch_size * 2] 
                           if page.estimated_complexity == "high")
        
        if complex_pages > self.config.batch_size // 2:
            return max(1, self.config.batch_size - 1)
        
        # For very short pages, might want larger batches
        short_pages = sum(1 for page in remaining_pages[:self.config.batch_size * 2]
                         if page.word_count < 100)
        
        if short_pages > self.config.batch_size:
            return min(len(remaining_pages), self.config.batch_size + 1)
            
        return min(len(remaining_pages), self.config.batch_size)
    
    def _combine_page_content(self, pages: List[DocumentPage]) -> str:
        """Intelligently combine content from multiple pages."""
        if not pages:
            return ""
            
        if len(pages) == 1:
            return pages[0].content
            
        # Combine pages with clear separators
        combined_parts = []
        for page in pages:
            page_header = f"\n=== Page {page.page_number} ===\n"
            combined_parts.append(page_header + page.content)
            
        return "\n\n".join(combined_parts)
    
    def _add_context_overlap(self, batches: List[PageBatch], pages: List[DocumentPage]) -> List[PageBatch]:
        """Add context overlap between batches for better entity continuity."""
        
        if self.config.overlap_pages == 0 or len(batches) <= 1:
            return batches
            
        # Add overlap content to each batch (except the first)
        for i in range(1, len(batches)):
            current_batch = batches[i]
            
            # Get pages from previous batch for overlap
            prev_batch = batches[i - 1]
            overlap_pages = prev_batch.pages[-self.config.overlap_pages:]
            
            if overlap_pages:
                overlap_content = self._combine_page_content(overlap_pages)
                current_batch.context_overlap = f"=== Context from Previous Batch ===\n{overlap_content}\n=== Current Batch Content ==="
                
                # Update combined content to include overlap
                current_batch.combined_content = current_batch.context_overlap + "\n\n" + current_batch.combined_content
                
        return batches
    
    def get_batch_statistics(self, batches: List[PageBatch]) -> Dict[str, Any]:
        """Get comprehensive statistics about the generated batches."""
        
        if not batches:
            return {"error": "No batches provided"}
            
        total_pages = sum(len(batch.pages) for batch in batches)
        total_words = sum(batch.word_count for batch in batches)
        total_chars = sum(batch.char_count for batch in batches)
        
        complexity_distribution = {}
        for batch in batches:
            complexity = batch.estimated_complexity
            complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
            
        return {
            "total_batches": len(batches),
            "total_pages": total_pages,
            "total_words": total_words,
            "total_characters": total_chars,
            "avg_pages_per_batch": total_pages / len(batches),
            "avg_words_per_batch": total_words / len(batches),
            "complexity_distribution": complexity_distribution,
            "batch_size_config": self.config.batch_size,
            "overlap_pages_config": self.config.overlap_pages,
            "batches_summary": [
                {
                    "batch_id": batch.batch_id,
                    "page_range": batch.page_range,
                    "word_count": batch.word_count,
                    "complexity": batch.estimated_complexity,
                    "has_overlap": bool(batch.context_overlap)
                }
                for batch in batches
            ]
        }