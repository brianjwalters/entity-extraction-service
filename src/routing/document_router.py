"""
Intelligent Document Router

Routes documents to optimal processing strategy based on size and characteristics.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, Literal
import logging

from .size_detector import SizeDetector, DocumentSizeInfo, SizeCategory

logger = logging.getLogger(__name__)


class ProcessingStrategy(str, Enum):
    """Processing strategies for entity extraction"""
    SINGLE_PASS = "single_pass"                    # Very small docs: single consolidated prompt
    THREE_WAVE = "three_wave"                      # Small docs: 3-wave optimized
    FOUR_WAVE = "four_wave"                        # Small-medium docs: 4-wave with relationships
    THREE_WAVE_CHUNKED = "three_wave_chunked"     # Medium/large docs: 3-wave + chunking
    ADAPTIVE = "adaptive"                          # Adaptive strategy selection
    EIGHT_WAVE_FALLBACK = "eight_wave_fallback"   # Fallback to 8-wave for critical docs
    EMPTY_DOCUMENT = "empty_document"              # Edge case: empty document
    TOO_SMALL = "too_small"                        # Edge case: document too small
    INVALID_DOCUMENT = "invalid_document"          # Edge case: malformed/binary


@dataclass
class ChunkConfig:
    """
    Configuration for document chunking.

    Attributes:
        strategy: Chunking strategy name
        chunk_size: Size of each chunk in tokens
        overlap_size: Overlap between chunks in tokens
        preserve_boundaries: Boundary type to preserve when chunking
    """
    strategy: Literal["extraction", "page_based", "none"]
    chunk_size: int
    overlap_size: int
    preserve_boundaries: Literal["sentence", "paragraph", "section", "page"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "strategy": self.strategy,
            "chunk_size": self.chunk_size,
            "overlap_size": self.overlap_size,
            "preserve_boundaries": self.preserve_boundaries
        }


@dataclass
class RoutingDecision:
    """
    Complete routing decision with metadata.

    Attributes:
        strategy: Selected processing strategy
        prompt_version: Prompt version to use
        chunk_config: Chunking configuration (if needed)
        estimated_tokens: Estimated total token usage
        estimated_duration: Estimated processing time in seconds
        estimated_cost: Estimated processing cost in USD
        expected_accuracy: Expected accuracy percentage (0.0-1.0)
        size_info: Document size information
        rationale: Human-readable explanation of decision
        num_chunks: Number of chunks required (0 if no chunking)
        extract_relationships: Whether to extract relationships (FOUR_WAVE)
    """
    strategy: ProcessingStrategy
    prompt_version: Optional[str]
    chunk_config: Optional[ChunkConfig]
    estimated_tokens: int
    estimated_duration: float
    estimated_cost: float
    expected_accuracy: float
    size_info: DocumentSizeInfo
    rationale: str
    num_chunks: int = 0
    extract_relationships: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "strategy": self.strategy.value,
            "prompt_version": self.prompt_version,
            "chunk_config": self.chunk_config.to_dict() if self.chunk_config else None,
            "estimated_tokens": self.estimated_tokens,
            "estimated_duration": self.estimated_duration,
            "estimated_cost": self.estimated_cost,
            "expected_accuracy": self.expected_accuracy,
            "size_info": self.size_info.to_dict(),
            "rationale": self.rationale,
            "num_chunks": self.num_chunks,
            "extract_relationships": self.extract_relationships
        }

    def __repr__(self) -> str:
        return (
            f"RoutingDecision(strategy={self.strategy.value}, "
            f"tokens={self.estimated_tokens:,}, "
            f"accuracy={self.expected_accuracy:.1%}, "
            f"chunks={self.num_chunks})"
        )


class DocumentRouter:
    """
    Intelligent document router for entity extraction.

    Routes documents to optimal processing strategy based on:
    - Document size and characteristics
    - Token budget constraints
    - Accuracy requirements
    - Performance targets
    """

    # vLLM context limit
    MAX_CONTEXT_LENGTH = 32_768
    SAFETY_MARGIN = 2_000

    # Token estimates per strategy (from design doc)
    SINGLE_PASS_PROMPT_TOKENS = 5_000
    THREE_WAVE_PROMPT_TOKENS = 17_500
    FOUR_WAVE_PROMPT_TOKENS = 45_000  # Wave 1: 15K + Wave 2: 10K + Wave 3: 8K + Wave 4: 12K
    EIGHT_WAVE_PROMPT_TOKENS = 26_900

    SINGLE_PASS_RESPONSE_TOKENS = 1_000
    THREE_WAVE_RESPONSE_TOKENS = 4_096
    FOUR_WAVE_RESPONSE_TOKENS = 6_000  # Comprehensive extraction with relationships
    EIGHT_WAVE_RESPONSE_TOKENS = 8_000

    # Default chunking parameters
    DEFAULT_CHUNK_SIZE = 8_000  # tokens
    DEFAULT_OVERLAP = 500       # tokens
    LARGE_DOC_OVERLAP = 1_000   # tokens for large documents

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize document router.

        Args:
            config: Optional configuration dict with custom thresholds
        """
        self.config = config or {}
        self.size_detector = SizeDetector()

        # Allow configuration overrides
        self.max_context = self.config.get("max_context_length", self.MAX_CONTEXT_LENGTH)
        self.safety_margin = self.config.get("safety_margin", self.SAFETY_MARGIN)
        self.enable_adaptive = self.config.get("enable_adaptive", False)
        self.force_strategy = self.config.get("force_strategy", None)

        logger.info(
            f"DocumentRouter initialized (max_context={self.max_context}, "
            f"safety_margin={self.safety_margin}, adaptive={self.enable_adaptive})"
        )

    def route(
        self,
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        strategy_override: Optional[str] = None,
        extract_relationships: bool = False,
        graphrag_mode: bool = False
    ) -> RoutingDecision:
        """
        Route document to optimal processing strategy.

        Args:
            document_text: Full document text content
            metadata: Optional document metadata
            strategy_override: Manual strategy override (use with caution)
            extract_relationships: Request relationship extraction (triggers FOUR_WAVE)
            graphrag_mode: GraphRAG mode (always uses FOUR_WAVE)

        Returns:
            RoutingDecision with complete routing information

        Raises:
            ValueError: If document_text is None or invalid
        """
        if document_text is None:
            raise ValueError("document_text cannot be None")

        metadata = metadata or {}

        # Step 1: Detect document size
        size_info = self.size_detector.detect(document_text, metadata)

        logger.info(
            f"Routing document: {size_info.category.value} "
            f"({size_info.chars:,} chars, {size_info.tokens:,} tokens) | "
            f"GraphRAG: {graphrag_mode} | Relationships: {extract_relationships}"
        )

        # Step 2: Handle edge cases
        edge_case_decision = self._check_edge_cases(document_text, size_info)
        if edge_case_decision:
            logger.warning(f"Edge case detected: {edge_case_decision.strategy.value}")
            return edge_case_decision

        # Step 3: Check for GraphRAG mode or explicit relationship extraction
        if graphrag_mode:
            logger.info("GraphRAG mode enabled - routing to FOUR_WAVE")
            decision = self._route_four_wave(
                size_info,
                graphrag_mode=True,
                explicit_relationships=False
            )
            logger.info(
                f"Routing decision: {decision.strategy.value} | "
                f"Accuracy: {decision.expected_accuracy:.1%} | "
                f"Tokens: {decision.estimated_tokens:,} | "
                f"Cost: ${decision.estimated_cost:.4f} | "
                f"Duration: {decision.estimated_duration:.2f}s"
            )
            return decision

        # Step 4: Check for strategy override
        if strategy_override:
            logger.info(f"Strategy override requested: {strategy_override}")
            return self._apply_strategy_override(strategy_override, size_info, document_text)

        if self.force_strategy:
            logger.info(f"Forced strategy from config: {self.force_strategy}")
            return self._apply_strategy_override(self.force_strategy, size_info, document_text)

        # Step 5: Check for relationship extraction or large document
        if extract_relationships and size_info.chars > 5_000:
            logger.info("Relationships requested for medium/large doc - routing to FOUR_WAVE")
            decision = self._route_four_wave(
                size_info,
                graphrag_mode=False,
                explicit_relationships=True
            )
        elif size_info.chars > 20_000:
            logger.info("Large document detected - routing to FOUR_WAVE for comprehensive extraction")
            decision = self._route_four_wave(
                size_info,
                graphrag_mode=False,
                explicit_relationships=False
            )
        # Step 6: Route based on size category (standard routing)
        elif size_info.category == SizeCategory.VERY_SMALL:
            decision = self._route_very_small(size_info)
        elif size_info.category == SizeCategory.SMALL:
            decision = self._route_small(size_info)
        elif size_info.category == SizeCategory.MEDIUM:
            decision = self._route_medium(size_info)
        else:  # LARGE
            decision = self._route_large(size_info)

        logger.info(
            f"Routing decision: {decision.strategy.value} | "
            f"Accuracy: {decision.expected_accuracy:.1%} | "
            f"Tokens: {decision.estimated_tokens:,} | "
            f"Cost: ${decision.estimated_cost:.4f} | "
            f"Duration: {decision.estimated_duration:.2f}s"
        )

        return decision

    def _check_edge_cases(
        self,
        document_text: str,
        size_info: DocumentSizeInfo
    ) -> Optional[RoutingDecision]:
        """
        Check for edge cases that require special handling.

        Returns:
            RoutingDecision if edge case detected, None otherwise
        """
        # Empty document
        if not document_text or len(document_text.strip()) == 0:
            return RoutingDecision(
                strategy=ProcessingStrategy.EMPTY_DOCUMENT,
                prompt_version=None,
                chunk_config=None,
                estimated_tokens=0,
                estimated_duration=0.0,
                estimated_cost=0.0,
                expected_accuracy=0.0,
                size_info=size_info,
                rationale="Empty document - no extraction needed"
            )

        # Too small (< 50 characters - likely fragment)
        if size_info.chars < 50:
            return RoutingDecision(
                strategy=ProcessingStrategy.TOO_SMALL,
                prompt_version=None,
                chunk_config=None,
                estimated_tokens=size_info.tokens,
                estimated_duration=0.0,
                estimated_cost=0.0,
                expected_accuracy=0.0,
                size_info=size_info,
                rationale="Document too small (<50 chars) - likely fragment"
            )

        # Check for binary/malformed data
        if not self._is_text_document(document_text):
            return RoutingDecision(
                strategy=ProcessingStrategy.INVALID_DOCUMENT,
                prompt_version=None,
                chunk_config=None,
                estimated_tokens=0,
                estimated_duration=0.0,
                estimated_cost=0.0,
                expected_accuracy=0.0,
                size_info=size_info,
                rationale="Document contains binary data or is malformed"
            )

        # Extremely large document (>1M chars) - warn but process
        if size_info.chars > 1_000_000:
            logger.warning(
                f"Extremely large document ({size_info.chars:,} chars). "
                "Processing may be slow."
            )

        return None

    def _is_text_document(self, text: str) -> bool:
        """
        Check if document contains valid text (not binary data).

        Args:
            text: Document text to check

        Returns:
            True if document is valid text, False if binary/malformed
        """
        if not text:
            return True

        # Count non-printable characters (excluding common whitespace)
        non_printable = sum(
            1 for c in text[:1000]  # Check first 1000 chars
            if ord(c) < 32 and c not in '\n\r\t'
        )

        # If >5% non-printable, likely binary
        return (non_printable / min(len(text), 1000)) <= 0.05

    def _route_very_small(self, size_info: DocumentSizeInfo) -> RoutingDecision:
        """
        Route very small documents (<5K chars).

        Strategy: Single pass with consolidated prompt (15 entity types)
        - Fastest processing (~500ms)
        - Lowest cost ($0.0038)
        - Acceptable accuracy (85-90%)
        """
        estimated_tokens = (
            self.SINGLE_PASS_PROMPT_TOKENS +
            size_info.tokens +
            self.SINGLE_PASS_RESPONSE_TOKENS
        )

        return RoutingDecision(
            strategy=ProcessingStrategy.SINGLE_PASS,
            prompt_version="single_pass_consolidated_v1",
            chunk_config=None,
            estimated_tokens=estimated_tokens,
            estimated_duration=0.5,
            estimated_cost=0.0038,
            expected_accuracy=0.87,
            size_info=size_info,
            rationale="Very small document - single pass optimization for speed and cost",
            num_chunks=0
        )

    def _route_small(self, size_info: DocumentSizeInfo) -> RoutingDecision:
        """
        Route small documents (5K-50K chars).

        Strategy: 3-wave optimized (34 entity types + relationships)
        - Balanced processing (~850-1200ms)
        - Moderate cost ($0.0159)
        - High accuracy (88-93%)
        - May require chunking if near context limit
        """
        estimated_tokens = (
            self.THREE_WAVE_PROMPT_TOKENS +
            size_info.tokens +
            self.THREE_WAVE_RESPONSE_TOKENS
        )

        # Check if fits in context window
        available_context = self.max_context - self.safety_margin

        if estimated_tokens <= available_context:
            # Fits without chunking
            return RoutingDecision(
                strategy=ProcessingStrategy.THREE_WAVE,
                prompt_version="three_wave_optimized_v1",
                chunk_config=None,
                estimated_tokens=estimated_tokens,
                estimated_duration=1.0,
                estimated_cost=0.0159,
                expected_accuracy=0.90,
                size_info=size_info,
                rationale="Small document - 3-wave optimized extraction",
                num_chunks=0
            )
        else:
            # Near context limit - use chunking
            num_chunks = self._calculate_num_chunks(size_info.tokens, self.DEFAULT_CHUNK_SIZE)

            return RoutingDecision(
                strategy=ProcessingStrategy.THREE_WAVE_CHUNKED,
                prompt_version="three_wave_optimized_v1",
                chunk_config=ChunkConfig(
                    strategy="extraction",
                    chunk_size=self.DEFAULT_CHUNK_SIZE,
                    overlap_size=self.DEFAULT_OVERLAP,
                    preserve_boundaries="paragraph"
                ),
                estimated_tokens=estimated_tokens,
                estimated_duration=num_chunks * 0.85,
                estimated_cost=num_chunks * 0.0159,
                expected_accuracy=0.89,
                size_info=size_info,
                rationale="Small document near context limit - chunked 3-wave",
                num_chunks=num_chunks
            )

    def _route_medium(self, size_info: DocumentSizeInfo) -> RoutingDecision:
        """
        Route medium documents (50K-150K chars).

        Strategy: 3-wave with ExtractionChunker
        - Chunked processing (~2-4s)
        - Variable cost based on chunks
        - High accuracy (90-93%)
        """
        num_chunks = self._calculate_num_chunks(size_info.tokens, self.DEFAULT_CHUNK_SIZE)

        estimated_duration = num_chunks * 0.85
        estimated_cost = num_chunks * 0.0159

        return RoutingDecision(
            strategy=ProcessingStrategy.THREE_WAVE_CHUNKED,
            prompt_version="three_wave_optimized_v1",
            chunk_config=ChunkConfig(
                strategy="extraction",
                chunk_size=self.DEFAULT_CHUNK_SIZE,
                overlap_size=self.DEFAULT_OVERLAP,
                preserve_boundaries="paragraph"
            ),
            estimated_tokens=size_info.tokens,
            estimated_duration=estimated_duration,
            estimated_cost=estimated_cost,
            expected_accuracy=0.91,
            size_info=size_info,
            rationale=f"Medium document - chunked 3-wave with deduplication ({num_chunks} chunks)",
            num_chunks=num_chunks
        )

    def _route_four_wave(
        self,
        size_info: DocumentSizeInfo,
        graphrag_mode: bool = False,
        explicit_relationships: bool = False
    ) -> RoutingDecision:
        """
        Route documents to FOUR_WAVE strategy with relationship extraction.

        Strategy: 4-wave optimized (195 entity types + 34 relationships)
        - Comprehensive extraction (~150-200s)
        - Higher cost ($0.033)
        - Highest accuracy (92-95%)
        - Includes relationship extraction for GraphRAG
        """
        estimated_tokens = (
            self.FOUR_WAVE_PROMPT_TOKENS +
            size_info.tokens +
            self.FOUR_WAVE_RESPONSE_TOKENS
        )

        # Determine rationale based on trigger
        if graphrag_mode:
            rationale = "GraphRAG mode: full 4-wave extraction with relationships for knowledge graph"
            estimated_duration = 180.0  # 3 minutes for GraphRAG
            expected_accuracy = 0.95
        elif explicit_relationships:
            rationale = "Relationships requested: 4-wave extraction with entity relationships"
            estimated_duration = 150.0  # 2.5 minutes
            expected_accuracy = 0.92
        elif size_info.chars > 20_000:
            rationale = "Large document: comprehensive 4-wave extraction with relationships"
            estimated_duration = 200.0  # 3.3 minutes for large docs
            expected_accuracy = 0.95
        else:
            rationale = "4-wave extraction with comprehensive entity coverage and relationships"
            estimated_duration = 150.0
            expected_accuracy = 0.92

        # Calculate cost based on token usage (approximate: $0.00075 per 1K tokens)
        estimated_cost = (estimated_tokens / 1000) * 0.00075

        return RoutingDecision(
            strategy=ProcessingStrategy.FOUR_WAVE,
            prompt_version="four_wave_optimized_v1",
            chunk_config=None,
            estimated_tokens=estimated_tokens,
            estimated_duration=estimated_duration,
            estimated_cost=estimated_cost,
            expected_accuracy=expected_accuracy,
            size_info=size_info,
            rationale=rationale,
            num_chunks=0,
            extract_relationships=True
        )

    def _route_large(self, size_info: DocumentSizeInfo) -> RoutingDecision:
        """
        Route large documents (>150K chars).

        Strategy: 3-wave with ExtractionChunker and larger overlap
        - Chunked processing with section preservation
        - Variable cost (can be expensive)
        - Highest accuracy (90-95%)
        """
        num_chunks = self._calculate_num_chunks(size_info.tokens, self.DEFAULT_CHUNK_SIZE)

        estimated_duration = num_chunks * 1.0  # Slightly longer per chunk
        estimated_cost = num_chunks * 0.0159

        return RoutingDecision(
            strategy=ProcessingStrategy.THREE_WAVE_CHUNKED,
            prompt_version="three_wave_optimized_v1",
            chunk_config=ChunkConfig(
                strategy="extraction",
                chunk_size=self.DEFAULT_CHUNK_SIZE,
                overlap_size=self.LARGE_DOC_OVERLAP,  # Larger overlap for large docs
                preserve_boundaries="section"
            ),
            estimated_tokens=size_info.tokens,
            estimated_duration=estimated_duration,
            estimated_cost=estimated_cost,
            expected_accuracy=0.92,
            size_info=size_info,
            rationale=f"Large document - chunked 3-wave with section preservation ({num_chunks} chunks)",
            num_chunks=num_chunks
        )

    def _calculate_num_chunks(self, total_tokens: int, chunk_size: int) -> int:
        """
        Calculate number of chunks needed.

        Args:
            total_tokens: Total document tokens
            chunk_size: Size of each chunk in tokens

        Returns:
            Number of chunks required
        """
        if total_tokens <= chunk_size:
            return 1

        # Account for overlap in calculation
        effective_chunk_size = chunk_size - self.DEFAULT_OVERLAP
        return (total_tokens // effective_chunk_size) + 1

    def _apply_strategy_override(
        self,
        strategy: str,
        size_info: DocumentSizeInfo,
        document_text: str
    ) -> RoutingDecision:
        """
        Apply manual strategy override.

        Args:
            strategy: Strategy name to force
            size_info: Document size information
            document_text: Full document text

        Returns:
            RoutingDecision with overridden strategy
        """
        logger.warning(f"Applying strategy override: {strategy}")

        # Map string to enum
        try:
            strategy_enum = ProcessingStrategy(strategy)
        except ValueError:
            logger.error(f"Invalid strategy override: {strategy}. Using default routing.")
            # Fallback to normal routing
            if size_info.category == SizeCategory.VERY_SMALL:
                return self._route_very_small(size_info)
            elif size_info.category == SizeCategory.SMALL:
                return self._route_small(size_info)
            elif size_info.category == SizeCategory.MEDIUM:
                return self._route_medium(size_info)
            else:
                return self._route_large(size_info)

        # Create decision based on override
        if strategy_enum == ProcessingStrategy.SINGLE_PASS:
            return self._route_very_small(size_info)
        elif strategy_enum == ProcessingStrategy.THREE_WAVE:
            decision = self._route_small(size_info)
            decision.rationale += " (manual override)"
            return decision
        elif strategy_enum == ProcessingStrategy.FOUR_WAVE:
            decision = self._route_four_wave(
                size_info,
                graphrag_mode=False,
                explicit_relationships=True
            )
            decision.rationale += " (manual override)"
            return decision
        elif strategy_enum == ProcessingStrategy.THREE_WAVE_CHUNKED:
            if size_info.category in [SizeCategory.MEDIUM, SizeCategory.LARGE]:
                decision = self._route_medium(size_info)
            else:
                decision = self._route_small(size_info)
            decision.rationale += " (manual override)"
            return decision
        elif strategy_enum == ProcessingStrategy.EIGHT_WAVE_FALLBACK:
            # Fallback to 8-wave system
            return RoutingDecision(
                strategy=ProcessingStrategy.EIGHT_WAVE_FALLBACK,
                prompt_version="eight_wave_multipass_v2",
                chunk_config=None,
                estimated_tokens=self.EIGHT_WAVE_PROMPT_TOKENS + size_info.tokens,
                estimated_duration=2.0,
                estimated_cost=0.0254,
                expected_accuracy=0.93,
                size_info=size_info,
                rationale="8-wave fallback (manual override for maximum accuracy)",
                num_chunks=0
            )
        else:
            logger.warning(f"Unsupported strategy override: {strategy}. Using default routing.")
            return self._route_small(size_info)

    def validate_decision(self, decision: RoutingDecision) -> tuple[bool, list[str]]:
        """
        Validate routing decision for sanity checks.

        Args:
            decision: Routing decision to validate

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        # Check token budget
        if decision.estimated_tokens > self.max_context:
            warnings.append(
                f"WARNING: Estimated tokens ({decision.estimated_tokens:,}) "
                f"exceed context limit ({self.max_context:,})"
            )

        # Check for unreasonably high cost
        if decision.estimated_cost > 1.0:  # $1 per document
            warnings.append(
                f"WARNING: Estimated cost (${decision.estimated_cost:.2f}) is very high. "
                f"Consider document sampling or alternative strategies."
            )

        # Check for unreasonably long processing time
        if decision.estimated_duration > 60.0:  # 60 seconds
            warnings.append(
                f"WARNING: Estimated duration ({decision.estimated_duration:.1f}s) is very long. "
                f"Consider batch processing or document splitting."
            )

        # Check for zero estimated tokens (edge cases should be handled)
        if decision.estimated_tokens == 0 and decision.strategy not in [
            ProcessingStrategy.EMPTY_DOCUMENT,
            ProcessingStrategy.INVALID_DOCUMENT
        ]:
            warnings.append("WARNING: Zero estimated tokens for non-edge-case strategy")

        is_valid = len(warnings) == 0

        return is_valid, warnings
