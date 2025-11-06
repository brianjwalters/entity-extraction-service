"""
LLM-based UnknownCitation Classifier

Classifies UnknownCitation entries using LLM with contextual understanding.
For PoC, uses rule-based classification that simulates LLM behavior.

In production, replace MockLLMClassifier with actual vLLM API calls.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .luris_entity_v2 import (
    LurisEntityV2,
    EntityType,
    ExtractionMethod,
    create_entity,
)


@dataclass
class ClassificationResult:
    """Result of LLM classification."""

    entity_type: str
    confidence: float
    subtype: Optional[str] = None
    category: Optional[str] = None
    reasoning: Optional[str] = None
    is_valid_citation: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MockLLMClassifier:
    """
    Mock LLM classifier for proof of concept.

    In production, this would make API calls to vLLM (Port 8080).
    For PoC, uses intelligent rule-based classification that simulates
    what an LLM would determine from context.
    """

    def __init__(self):
        """Initialize classifier with pattern matchers."""
        # USC patterns
        self.usc_pattern = re.compile(
            r"§\s*(\d+)([A-Za-z]*)?\(([a-z0-9]+)\)(\([A-Za-z0-9]+\))*",
            re.IGNORECASE
        )

        # CFR patterns
        self.cfr_pattern = re.compile(
            r"§§?\s*(\d+)\.(\d+)",
            re.IGNORECASE
        )

        # Internal reference patterns (just section numbers)
        self.internal_pattern = re.compile(
            r"§§?\s*(\d{1,3})([-–](\d{1,3}))?[,;.]?$"
        )

    def classify_unknown_citation(
        self,
        citation_text: str,
        context_before: str,
        context_after: str,
        position: Tuple[int, int],
    ) -> ClassificationResult:
        """
        Classify an unknown citation using context.

        Args:
            citation_text: The citation text to classify
            context_before: Text before citation (up to 200 chars)
            context_after: Text after citation (up to 200 chars)
            position: (start, end) position in document

        Returns:
            ClassificationResult with type, confidence, and reasoning
        """
        # Combine context
        full_context = f"{context_before} {citation_text} {context_after}"

        # Check if this is a USC subsection
        if self._is_usc_subsection(citation_text, full_context):
            return self._classify_as_usc_subsection(citation_text, full_context)

        # Check if this is a CFR reference
        if self._is_cfr_reference(citation_text, full_context):
            return self._classify_as_cfr(citation_text, full_context)

        # Check if this is an internal document reference
        if self._is_internal_reference(citation_text, full_context):
            return self._classify_as_internal_reference(citation_text, full_context)

        # Check for malformed citations (false positives)
        if self._is_false_positive(citation_text, full_context):
            return self._classify_as_false_positive(citation_text, full_context)

        # Default: unknown statutory reference
        return self._classify_as_generic_statute(citation_text, full_context)

    def _is_usc_subsection(self, text: str, context: str) -> bool:
        """Check if this is a USC subsection reference."""
        # Look for USC parent statute in context
        has_usc_parent = bool(re.search(r"U\.?\s*S\.?\s*C\.?\s*§\s*\d+", context, re.IGNORECASE))

        # Check if text matches USC subsection pattern
        matches_pattern = bool(self.usc_pattern.search(text))

        return has_usc_parent and matches_pattern

    def _classify_as_usc_subsection(self, text: str, context: str) -> ClassificationResult:
        """Classify as USC subsection citation."""
        # Extract parent statute from context
        parent_match = re.search(r"(U\.?\s*S\.?\s*C\.?\s*§\s*\d+[A-Za-z]*)", context, re.IGNORECASE)
        parent = parent_match.group(1) if parent_match else "Unknown"

        return ClassificationResult(
            entity_type=EntityType.USC_SUBSECTION_CITATION,
            confidence=0.90,
            subtype="usc_subsection",
            category="statutory",
            reasoning=f"USC subsection reference. Parent statute: {parent}",
            metadata={
                "parent_statute": parent,
                "subsection": text.strip(),
            }
        )

    def _is_cfr_reference(self, text: str, context: str) -> bool:
        """Check if this is a CFR reference."""
        has_cfr_context = bool(re.search(r"CFR|C\.?\s*F\.?\s*R\.?", context, re.IGNORECASE))
        matches_pattern = bool(self.cfr_pattern.search(text))
        return has_cfr_context and matches_pattern

    def _classify_as_cfr(self, text: str, context: str) -> ClassificationResult:
        """Classify as CFR citation."""
        return ClassificationResult(
            entity_type=EntityType.CFR_CITATION,
            confidence=0.88,
            subtype="cfr_section",
            category="regulatory",
            reasoning="CFR section reference identified from context",
            metadata={
                "regulation_type": "cfr",
            }
        )

    def _is_internal_reference(self, text: str, context: str) -> bool:
        """Check if this is an internal document reference."""
        # Simple section numbers without clear statutory context
        if not self.internal_pattern.match(text.strip()):
            return False

        # Look for internal reference indicators in context
        internal_indicators = [
            "subsection",
            "section",
            "paragraph",
            "subparagraph",
            "as required by",
            "pursuant to",
            "under",
        ]

        context_lower = context.lower()
        return any(indicator in context_lower for indicator in internal_indicators)

    def _classify_as_internal_reference(self, text: str, context: str) -> ClassificationResult:
        """Classify as internal document reference."""
        return ClassificationResult(
            entity_type=EntityType.INTERNAL_REFERENCE,
            confidence=0.75,
            subtype="internal_section",
            category="reference_citation",
            reasoning="Internal document section reference",
            metadata={
                "reference_type": "internal",
            }
        )

    def _is_false_positive(self, text: str, context: str) -> bool:
        """Check if this is a false positive (not actually a citation)."""
        # Malformed patterns
        if "]" in text or ")" in text and "(" not in text:
            return True

        # Very short references without clear context
        if len(text.strip()) < 3:
            return True

        return False

    def _classify_as_false_positive(self, text: str, context: str) -> ClassificationResult:
        """Classify as false positive."""
        return ClassificationResult(
            entity_type=EntityType.UNKNOWN_CITATION,
            confidence=0.3,
            is_valid_citation=False,
            reasoning="Likely false positive - malformed or insufficient context",
            metadata={
                "classification": "false_positive",
            }
        )

    def _classify_as_generic_statute(self, text: str, context: str) -> ClassificationResult:
        """Classify as generic statutory reference (fallback)."""
        return ClassificationResult(
            entity_type=EntityType.STATUTE_CITATION,
            confidence=0.65,
            subtype="generic_statute",
            category="statutory",
            reasoning="Generic statutory reference - type unclear from context",
            metadata={
                "needs_manual_review": True,
            }
        )


class LLMUnknownClassifier:
    """
    LLM-based classifier for UnknownCitation entries.

    This is the main interface. In production, replace MockLLMClassifier
    with actual vLLM API client.
    """

    def __init__(self, use_mock: bool = True):
        """
        Initialize classifier.

        Args:
            use_mock: If True, use MockLLMClassifier. If False, use real vLLM API.
        """
        self.use_mock = use_mock

        if use_mock:
            self.classifier = MockLLMClassifier()
        else:
            # TODO: Initialize real vLLM client
            # from vllm_client import VLLMClient
            # self.classifier = VLLMClient(base_url="http://localhost:8080")
            raise NotImplementedError("Real vLLM integration not yet implemented")

    def classify_unknown_entities(
        self,
        unknown_entities: List[LurisEntityV2],
        document_text: str,
    ) -> List[LurisEntityV2]:
        """
        Classify unknown citation entities using LLM.

        Args:
            unknown_entities: List of entities with UNKNOWN_CITATION type
            document_text: Full document text for context extraction

        Returns:
            List of classified entities (LurisEntityV2)
        """
        classified_entities = []

        for entity in unknown_entities:
            # Extract context window
            start_pos = entity.start_pos
            end_pos = entity.end_pos

            context_start = max(0, start_pos - 200)
            context_end = min(len(document_text), end_pos + 200)

            context_before = document_text[context_start:start_pos]
            context_after = document_text[end_pos:context_end]

            # Classify with LLM
            classification = self.classifier.classify_unknown_citation(
                citation_text=entity.text,
                context_before=context_before,
                context_after=context_after,
                position=(start_pos, end_pos),
            )

            # Skip false positives
            if not classification.is_valid_citation:
                continue

            # Create new entity with LLM classification
            classified_entity = create_entity(
                text=entity.text,
                entity_type=classification.entity_type,
                start_pos=start_pos,
                end_pos=end_pos,
                confidence=classification.confidence,
                extraction_method=ExtractionMethod.HYBRID_EYECITE_LLM,
                metadata={
                    **entity.metadata,
                    **classification.metadata,
                    "llm_reasoning": classification.reasoning,
                    "original_classification": "UnknownCitation",
                    "classified_by_llm": True,
                },
                subtype=classification.subtype,
                category=classification.category,
            )

            classified_entities.append(classified_entity)

        return classified_entities


def extract_context_window(
    document_text: str,
    start_pos: int,
    end_pos: int,
    window_size: int = 200,
) -> Tuple[str, str]:
    """
    Extract context window around citation.

    Args:
        document_text: Full document text
        start_pos: Citation start position
        end_pos: Citation end position
        window_size: Size of context window (default: 200 chars)

    Returns:
        Tuple of (context_before, context_after)
    """
    context_start = max(0, start_pos - window_size)
    context_end = min(len(document_text), end_pos + window_size)

    context_before = document_text[context_start:start_pos]
    context_after = document_text[end_pos:context_end]

    return context_before, context_after
