"""
Document Size Detection and Categorization

Analyzes document characteristics and categorizes by size for routing decisions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SizeCategory(str, Enum):
    """Document size categories for routing"""
    VERY_SMALL = "VERY_SMALL"  # 0-5K chars
    SMALL = "SMALL"            # 5K-50K chars
    MEDIUM = "MEDIUM"          # 50K-150K chars
    LARGE = "LARGE"            # >150K chars


@dataclass
class DocumentSizeInfo:
    """
    Complete document size analysis information.

    Attributes:
        chars: Total character count in document
        tokens: Estimated token count (4 chars per token)
        pages: Number of pages (if available from metadata)
        category: Size category (VERY_SMALL, SMALL, MEDIUM, LARGE)
        words: Approximate word count
        lines: Line count in document
    """
    chars: int
    tokens: int
    pages: int
    category: SizeCategory
    words: int
    lines: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "chars": self.chars,
            "tokens": self.tokens,
            "pages": self.pages,
            "category": self.category.value,
            "words": self.words,
            "lines": self.lines
        }

    def __repr__(self) -> str:
        return (
            f"DocumentSizeInfo(chars={self.chars:,}, tokens={self.tokens:,}, "
            f"pages={self.pages}, category={self.category.value})"
        )


class SizeDetector:
    """
    Detects and categorizes document size for routing decisions.

    Based on thresholds defined in intelligent_routing_and_prompts_design.md:
    - Very Small: 0-5,000 chars (~0-1,250 tokens)
    - Small: 5,001-50,000 chars (~1,251-12,500 tokens)
    - Medium: 50,001-150,000 chars (~12,501-37,500 tokens)
    - Large: >150,000 chars (>37,500 tokens)
    """

    # Size thresholds in characters
    VERY_SMALL_THRESHOLD = 5_000
    SMALL_THRESHOLD = 50_000
    MEDIUM_THRESHOLD = 150_000

    # Token estimation factor (characters per token)
    CHARS_PER_TOKEN = 4.0  # Conservative estimate for legal text

    def __init__(self, chars_per_token: float = CHARS_PER_TOKEN):
        """
        Initialize size detector.

        Args:
            chars_per_token: Characters per token ratio (default: 4.0)
        """
        self.chars_per_token = chars_per_token
        logger.debug(f"SizeDetector initialized with chars_per_token={chars_per_token}")

    def detect(self, document_text: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentSizeInfo:
        """
        Analyze document and determine size category.

        Args:
            document_text: Full document text content
            metadata: Optional metadata dict containing page count, etc.

        Returns:
            DocumentSizeInfo with complete size analysis

        Raises:
            ValueError: If document_text is None
        """
        if document_text is None:
            raise ValueError("document_text cannot be None")

        metadata = metadata or {}

        # Calculate document characteristics
        chars = len(document_text)
        tokens = self._estimate_tokens(chars)
        pages = self._extract_page_count(metadata)
        words = self._estimate_words(document_text)
        lines = self._count_lines(document_text)

        # Determine category
        category = self._categorize(chars)

        size_info = DocumentSizeInfo(
            chars=chars,
            tokens=tokens,
            pages=pages,
            category=category,
            words=words,
            lines=lines
        )

        logger.info(
            f"Document size detected: {category.value} "
            f"({chars:,} chars, {tokens:,} tokens, {pages} pages)"
        )

        return size_info

    def _estimate_tokens(self, char_count: int) -> int:
        """
        Estimate token count from character count.

        Based on empirical analysis:
        - English legal text: ~4 characters per token
        - Conservative estimate: 4.0 characters/token
        - Accounts for legal terminology, citations, and formatting

        Args:
            char_count: Number of characters in document

        Returns:
            Estimated token count
        """
        return int(char_count / self.chars_per_token)

    def _extract_page_count(self, metadata: Dict[str, Any]) -> int:
        """
        Extract page count from metadata if available.

        Args:
            metadata: Document metadata dictionary

        Returns:
            Page count (0 if not available)
        """
        # Try various common metadata keys
        for key in ['pages', 'page_count', 'num_pages', 'pageCount']:
            if key in metadata and metadata[key]:
                try:
                    return int(metadata[key])
                except (ValueError, TypeError):
                    continue

        return 0

    def _estimate_words(self, document_text: str) -> int:
        """
        Estimate word count in document.

        Args:
            document_text: Full document text

        Returns:
            Approximate word count
        """
        if not document_text:
            return 0

        # Simple whitespace-based word count
        return len(document_text.split())

    def _count_lines(self, document_text: str) -> int:
        """
        Count lines in document.

        Args:
            document_text: Full document text

        Returns:
            Line count
        """
        if not document_text:
            return 0

        return document_text.count('\n') + 1

    def _categorize(self, char_count: int) -> SizeCategory:
        """
        Determine size category based on character count.

        Thresholds:
        - Very Small: 0-5,000 chars
        - Small: 5,001-50,000 chars
        - Medium: 50,001-150,000 chars
        - Large: >150,000 chars

        Args:
            char_count: Number of characters in document

        Returns:
            SizeCategory enum value
        """
        if char_count <= self.VERY_SMALL_THRESHOLD:
            return SizeCategory.VERY_SMALL
        elif char_count <= self.SMALL_THRESHOLD:
            return SizeCategory.SMALL
        elif char_count <= self.MEDIUM_THRESHOLD:
            return SizeCategory.MEDIUM
        else:
            return SizeCategory.LARGE

    def estimate_processing_time(self, size_info: DocumentSizeInfo) -> float:
        """
        Estimate processing time in seconds based on size category.

        Estimates based on intelligent_routing_and_prompts_design.md:
        - Very Small: ~0.5s (single pass)
        - Small: ~0.85-1.2s (3-wave parallel)
        - Medium: ~2-4s (3-wave chunked)
        - Large: ~4s+ (3-wave chunked, many chunks)

        Args:
            size_info: Document size information

        Returns:
            Estimated processing time in seconds
        """
        if size_info.category == SizeCategory.VERY_SMALL:
            return 0.5
        elif size_info.category == SizeCategory.SMALL:
            return 1.0
        elif size_info.category == SizeCategory.MEDIUM:
            # Estimate based on chunks needed
            chunks_needed = (size_info.chars // 32_000) + 1  # ~8K tokens per chunk
            return min(4.0, chunks_needed * 0.85)
        else:  # LARGE
            chunks_needed = (size_info.chars // 32_000) + 1
            return chunks_needed * 1.0

    def estimate_cost(self, size_info: DocumentSizeInfo) -> float:
        """
        Estimate processing cost in USD based on size category.

        Cost estimates from intelligent_routing_and_prompts_design.md:
        - Very Small: $0.0038 (5,810 tokens)
        - Small: $0.0159 (30,838 tokens)
        - Medium: Variable based on chunks
        - Large: Variable based on chunks

        Args:
            size_info: Document size information

        Returns:
            Estimated cost in USD
        """
        # Cost per 1K tokens (example rate)
        COST_PER_1K_TOKENS = 0.000656  # Approximate

        if size_info.category == SizeCategory.VERY_SMALL:
            return 5810 * COST_PER_1K_TOKENS / 1000
        elif size_info.category == SizeCategory.SMALL:
            return 30838 * COST_PER_1K_TOKENS / 1000
        elif size_info.category == SizeCategory.MEDIUM:
            chunks_needed = (size_info.chars // 32_000) + 1
            return chunks_needed * 30838 * COST_PER_1K_TOKENS / 1000
        else:  # LARGE
            chunks_needed = (size_info.chars // 32_000) + 1
            return chunks_needed * 30838 * COST_PER_1K_TOKENS / 1000
