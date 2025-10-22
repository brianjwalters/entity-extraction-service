"""
Token Estimation Module for Document Processing

This module provides accurate token estimation for documents to determine
if chunking is needed for vLLM processing with the Granite 3.3-2b model.
Uses empirical ratio of 1.3 tokens per character with adjustments for
legal document complexity.
"""

import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum


class DocumentType(Enum):
    """Document type classifications for token estimation adjustments."""
    ENGLISH = "english"
    LEGAL_ENGLISH = "legal_english"
    CODE = "code"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class TokenEstimate:
    """Token estimation results with detailed breakdown."""
    raw_characters: int
    estimated_tokens: int
    total_with_overhead: int
    chunks_needed: int
    safe_chunk_size_chars: int
    document_type: DocumentType
    overhead_breakdown: Dict[str, int]
    requires_chunking: bool
    confidence: float  # Confidence in estimation (0-1)


class TokenEstimator:
    """
    Accurate token estimation for vLLM with Granite model.
    
    This estimator accounts for:
    - Base character-to-token ratio (1.3)
    - Document type multipliers (legal text is more complex)
    - System prompt and instruction overheads
    - Entity list definitions
    - Safety margins to prevent context overflow
    """
    
    # Base estimation ratios (validated through empirical testing)
    CHAR_TO_TOKEN_RATIO = 1.3  # Average: 1 token per 0.77 characters
    
    # Language-specific adjustments based on document complexity
    LANGUAGE_MULTIPLIERS = {
        DocumentType.ENGLISH: 1.0,
        DocumentType.LEGAL_ENGLISH: 1.15,  # Legal text has more complex terms
        DocumentType.CODE: 0.85,           # Code is more compact
        DocumentType.MIXED: 1.1,           # Documents with citations/references
        DocumentType.UNKNOWN: 1.1          # Conservative estimate
    }
    
    # Overhead calculations (in tokens)
    SYSTEM_PROMPT_TOKENS = 2500      # Base system prompt for extraction
    ENTITY_LIST_OVERHEAD = 4000      # Full 272+ entity type definitions
    INSTRUCTION_OVERHEAD = 1500      # Task instructions and examples
    RESPONSE_FORMAT_OVERHEAD = 500   # JSON structure requirements
    BUFFER_OVERHEAD = 1000           # Additional safety buffer
    
    # Context limits
    MAX_CONTEXT_TOKENS = 131072     # 128K for Granite 3.3-2b
    SAFETY_FACTOR = 0.85            # Use only 85% of available context
    
    # Chunk sizing
    TARGET_CHUNK_TOKENS = 75000     # Conservative chunk size
    MIN_CHUNK_TOKENS = 10000        # Minimum viable chunk
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the token estimator with optional logger."""
        self.logger = logger or logging.getLogger(__name__)
        self.usable_context = int(self.MAX_CONTEXT_TOKENS * self.SAFETY_FACTOR)
        
    def detect_document_type(self, text: str) -> DocumentType:
        """
        Detect document type based on content analysis.
        
        Args:
            text: Document text to analyze
            
        Returns:
            DocumentType: Detected document type
        """
        # Sample first 5000 characters for type detection
        sample = text[:5000] if len(text) > 5000 else text
        
        # Legal document indicators
        legal_indicators = [
            "pursuant to", "heretofore", "whereas", "plaintiff", "defendant",
            "court", "judge", "U.S.C.", "F.3d", "S.Ct.", "L.Ed.", "App.",
            "opinion", "dissent", "concur", "remand", "affirm", "reverse"
        ]
        
        # Code indicators
        code_indicators = [
            "def ", "class ", "import ", "function", "{", "}", "return",
            "if ", "else:", "for ", "while", "```", "var ", "const "
        ]
        
        # Count indicators
        legal_count = sum(1 for indicator in legal_indicators 
                         if indicator.lower() in sample.lower())
        code_count = sum(1 for indicator in code_indicators 
                        if indicator in sample)
        
        # Determine type based on indicator density
        if legal_count >= 5:
            return DocumentType.LEGAL_ENGLISH
        elif code_count >= 5:
            return DocumentType.CODE
        elif legal_count >= 2 or "citation" in sample.lower():
            return DocumentType.MIXED
        else:
            return DocumentType.ENGLISH
    
    def estimate_document_tokens(
        self, 
        text: str, 
        doc_type: Optional[DocumentType] = None
    ) -> TokenEstimate:
        """
        Estimate tokens for a document including all overheads.
        
        Args:
            text: Document text to estimate
            doc_type: Optional document type override
            
        Returns:
            TokenEstimate: Detailed token estimation results
        """
        # Auto-detect document type if not provided
        if doc_type is None:
            doc_type = self.detect_document_type(text)
            confidence = 0.85  # Lower confidence for auto-detection
        else:
            confidence = 0.95  # Higher confidence for explicit type
        
        # Calculate base tokens
        char_count = len(text)
        base_tokens = char_count * self.CHAR_TO_TOKEN_RATIO
        
        # Apply document type multiplier
        multiplier = self.LANGUAGE_MULTIPLIERS[doc_type]
        adjusted_tokens = int(base_tokens * multiplier)
        
        # Calculate total overhead
        overhead_breakdown = {
            "system_prompt": self.SYSTEM_PROMPT_TOKENS,
            "entity_definitions": self.ENTITY_LIST_OVERHEAD,
            "instructions": self.INSTRUCTION_OVERHEAD,
            "response_format": self.RESPONSE_FORMAT_OVERHEAD,
            "safety_buffer": self.BUFFER_OVERHEAD
        }
        total_overhead = sum(overhead_breakdown.values())
        
        # Total tokens with overhead
        total_tokens = adjusted_tokens + total_overhead
        
        # Calculate chunks needed
        available_for_content = self.usable_context - total_overhead
        chunks_needed = max(1, (adjusted_tokens + available_for_content - 1) // available_for_content)
        
        # Calculate safe chunk size in characters
        safe_chunk_tokens = min(self.TARGET_CHUNK_TOKENS, available_for_content)
        safe_chunk_chars = int(safe_chunk_tokens / (self.CHAR_TO_TOKEN_RATIO * multiplier))
        
        # Determine if chunking is required
        requires_chunking = total_tokens > self.usable_context
        
        self.logger.info(
            f"Token estimation: {char_count:,} chars → {adjusted_tokens:,} tokens "
            f"(+{total_overhead:,} overhead) = {total_tokens:,} total. "
            f"Chunks needed: {chunks_needed}"
        )
        
        return TokenEstimate(
            raw_characters=char_count,
            estimated_tokens=adjusted_tokens,
            total_with_overhead=total_tokens,
            chunks_needed=chunks_needed,
            safe_chunk_size_chars=safe_chunk_chars,
            document_type=doc_type,
            overhead_breakdown=overhead_breakdown,
            requires_chunking=requires_chunking,
            confidence=confidence
        )
    
    def calculate_safe_chunk_size(
        self, 
        max_context: int = None,
        doc_type: DocumentType = DocumentType.LEGAL_ENGLISH
    ) -> int:
        """
        Calculate maximum safe chunk size in characters.
        
        Args:
            max_context: Optional override for max context tokens
            doc_type: Document type for multiplier adjustment
            
        Returns:
            int: Safe chunk size in characters
        """
        if max_context is None:
            max_context = self.MAX_CONTEXT_TOKENS
            
        # Apply safety factor
        usable_tokens = int(max_context * self.SAFETY_FACTOR)
        
        # Subtract fixed overheads
        available_for_content = usable_tokens - sum([
            self.SYSTEM_PROMPT_TOKENS,
            self.ENTITY_LIST_OVERHEAD,
            self.INSTRUCTION_OVERHEAD,
            self.RESPONSE_FORMAT_OVERHEAD,
            self.BUFFER_OVERHEAD
        ])
        
        # Convert to characters based on document type
        multiplier = self.LANGUAGE_MULTIPLIERS[doc_type]
        max_chars = int(available_for_content / (self.CHAR_TO_TOKEN_RATIO * multiplier))
        
        return max_chars
    
    def estimate_chunks(
        self, 
        text: str,
        chunk_size_chars: Optional[int] = None,
        overlap_chars: int = 5000
    ) -> List[Tuple[int, int]]:
        """
        Estimate chunk boundaries for a document.
        
        Args:
            text: Document text to chunk
            chunk_size_chars: Optional chunk size override
            overlap_chars: Overlap between chunks
            
        Returns:
            List of (start, end) character positions for each chunk
        """
        if chunk_size_chars is None:
            doc_type = self.detect_document_type(text)
            chunk_size_chars = self.calculate_safe_chunk_size(doc_type=doc_type)
        
        chunks = []
        text_length = len(text)
        current_pos = 0
        
        while current_pos < text_length:
            # Calculate chunk end
            chunk_end = min(current_pos + chunk_size_chars, text_length)
            chunks.append((current_pos, chunk_end))
            
            # Break if we've reached the end
            if chunk_end >= text_length:
                break
            
            # Move to next chunk with overlap
            current_pos = chunk_end - overlap_chars
            
            # Ensure we make progress
            if current_pos <= chunks[-1][0]:
                current_pos = chunks[-1][1]
        
        return chunks
    
    def format_estimation_report(self, estimate: TokenEstimate) -> str:
        """
        Format a human-readable estimation report.
        
        Args:
            estimate: Token estimation results
            
        Returns:
            str: Formatted report
        """
        report = []
        report.append("=" * 60)
        report.append("TOKEN ESTIMATION REPORT")
        report.append("=" * 60)
        report.append(f"Document Type: {estimate.document_type.value}")
        report.append(f"Confidence: {estimate.confidence:.1%}")
        report.append("")
        
        report.append("CHARACTER & TOKEN COUNTS:")
        report.append(f"  Raw Characters: {estimate.raw_characters:,}")
        report.append(f"  Estimated Tokens: {estimate.estimated_tokens:,}")
        report.append(f"  Total with Overhead: {estimate.total_with_overhead:,}")
        report.append("")
        
        report.append("OVERHEAD BREAKDOWN:")
        for component, tokens in estimate.overhead_breakdown.items():
            report.append(f"  {component.replace('_', ' ').title()}: {tokens:,} tokens")
        report.append(f"  TOTAL OVERHEAD: {sum(estimate.overhead_breakdown.values()):,} tokens")
        report.append("")
        
        report.append("CHUNKING REQUIREMENTS:")
        report.append(f"  Requires Chunking: {'YES' if estimate.requires_chunking else 'NO'}")
        if estimate.requires_chunking:
            report.append(f"  Chunks Needed: {estimate.chunks_needed}")
            report.append(f"  Safe Chunk Size: {estimate.safe_chunk_size_chars:,} characters")
        report.append("")
        
        report.append("CONTEXT UTILIZATION:")
        utilization = (estimate.total_with_overhead / self.MAX_CONTEXT_TOKENS) * 100
        report.append(f"  Context Usage: {utilization:.1f}% of {self.MAX_CONTEXT_TOKENS:,} tokens")
        if utilization > 100:
            overflow = estimate.total_with_overhead - self.MAX_CONTEXT_TOKENS
            report.append(f"  ⚠️  OVERFLOW: {overflow:,} tokens over limit!")
        report.append("=" * 60)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the estimator with sample text
    
    logging.basicConfig(level=logging.INFO)
    estimator = TokenEstimator()
    
    # Test with different document sizes
    test_sizes = [
        ("Small", "x" * 10000),      # ~10K chars
        ("Medium", "x" * 100000),    # ~100K chars  
        ("Large", "x" * 500000),     # ~500K chars
        ("Huge", "x" * 2000000),     # ~2M chars
    ]
    
    for name, text in test_sizes:
        print(f"\n{name} Document Test:")
        estimate = estimator.estimate_document_tokens(text)
        print(estimator.format_estimation_report(estimate))