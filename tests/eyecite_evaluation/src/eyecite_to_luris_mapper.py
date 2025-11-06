"""
Eyecite to LurisEntityV2 Mapper

Maps Eyecite citation objects to standardized LurisEntityV2 entities.
"""

from typing import Any, Optional
from eyecite.models import (
    FullCaseCitation,
    ShortCaseCitation,
    IdCitation,
    SupraCitation,
    FullJournalCitation,
    FullLawCitation,
    UnknownCitation,
)

from .luris_entity_v2 import (
    LurisEntityV2,
    EntityType,
    ExtractionMethod,
    create_entity,
)


class EyeciteToLurisMapper:
    """Maps Eyecite citations to LurisEntityV2 entities."""

    def __init__(self):
        """Initialize mapper."""
        self.default_eyecite_confidence = 0.95

    def map_citation(self, citation: Any) -> LurisEntityV2:
        """
        Map any Eyecite citation to LurisEntityV2 entity.

        Args:
            citation: Eyecite citation object

        Returns:
            LurisEntityV2 entity

        Raises:
            ValueError: If citation type is not supported
        """
        citation_type = type(citation).__name__

        if isinstance(citation, FullCaseCitation):
            return self._map_full_case_citation(citation)
        elif isinstance(citation, ShortCaseCitation):
            return self._map_short_case_citation(citation)
        elif isinstance(citation, IdCitation):
            return self._map_id_citation(citation)
        elif isinstance(citation, SupraCitation):
            return self._map_supra_citation(citation)
        elif isinstance(citation, FullJournalCitation):
            return self._map_journal_citation(citation)
        elif isinstance(citation, FullLawCitation):
            return self._map_law_citation(citation)
        elif isinstance(citation, UnknownCitation):
            return self._map_unknown_citation(citation)
        else:
            raise ValueError(f"Unsupported citation type: {citation_type}")

    def _map_full_case_citation(self, citation: FullCaseCitation) -> LurisEntityV2:
        """Map FullCaseCitation to LurisEntityV2."""
        start_pos, end_pos = citation.span()
        metadata = citation.metadata

        return create_entity(
            text=citation.matched_text(),
            entity_type=EntityType.CASE_CITATION,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=self.default_eyecite_confidence,
            extraction_method=ExtractionMethod.EYECITE,
            metadata={
                "volume": getattr(citation, "volume", None),
                "reporter": getattr(citation, "reporter", None),
                "page": getattr(citation, "page", None),
                "year": getattr(metadata, "year", None),
                "court": str(getattr(metadata, "court", "")) if metadata.court else None,
                "plaintiff": getattr(metadata, "plaintiff", None),
                "defendant": getattr(metadata, "defendant", None),
                "pin_cite": getattr(metadata, "pin_cite", None),
                "parenthetical": getattr(metadata, "parenthetical", None),
                "citation_type": "FullCaseCitation",
            },
            subtype="full_case",
            category="case_law",
        )

    def _map_short_case_citation(self, citation: ShortCaseCitation) -> LurisEntityV2:
        """Map ShortCaseCitation to LurisEntityV2."""
        start_pos, end_pos = citation.span()
        metadata = citation.metadata

        return create_entity(
            text=citation.matched_text(),
            entity_type=EntityType.CASE_CITATION_SHORT,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=self.default_eyecite_confidence,
            extraction_method=ExtractionMethod.EYECITE,
            metadata={
                "volume": getattr(citation, "volume", None),
                "reporter": getattr(citation, "reporter", None),
                "page": getattr(citation, "page", None),
                "pin_cite": getattr(metadata, "pin_cite", None),
                "antecedent_guess": getattr(metadata, "antecedent_guess", None),
                "citation_type": "ShortCaseCitation",
            },
            subtype="short_case",
            category="case_law",
        )

    def _map_id_citation(self, citation: IdCitation) -> LurisEntityV2:
        """Map IdCitation to LurisEntityV2."""
        start_pos, end_pos = citation.span()
        metadata = citation.metadata

        return create_entity(
            text=citation.matched_text(),
            entity_type=EntityType.ID_CITATION,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=self.default_eyecite_confidence,
            extraction_method=ExtractionMethod.EYECITE,
            metadata={
                "pin_cite": getattr(metadata, "pin_cite", None),
                "citation_type": "IdCitation",
                "reference_type": "immediate_preceding",
            },
            subtype="id_reference",
            category="reference_citation",
        )

    def _map_supra_citation(self, citation: SupraCitation) -> LurisEntityV2:
        """Map SupraCitation to LurisEntityV2."""
        start_pos, end_pos = citation.span()

        return create_entity(
            text=citation.matched_text(),
            entity_type=EntityType.SUPRA_CITATION,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=self.default_eyecite_confidence,
            extraction_method=ExtractionMethod.EYECITE,
            metadata={
                "volume": getattr(citation, "volume", None),
                "citation_type": "SupraCitation",
                "reference_type": "supra",
            },
            subtype="supra_reference",
            category="reference_citation",
        )

    def _map_journal_citation(self, citation: FullJournalCitation) -> LurisEntityV2:
        """Map FullJournalCitation to LurisEntityV2."""
        start_pos, end_pos = citation.span()

        return create_entity(
            text=citation.matched_text(),
            entity_type=EntityType.JOURNAL_CITATION,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=self.default_eyecite_confidence,
            extraction_method=ExtractionMethod.EYECITE,
            metadata={
                "volume": getattr(citation, "volume", None),
                "reporter": getattr(citation, "reporter", None),
                "page": getattr(citation, "page", None),
                "citation_type": "FullJournalCitation",
            },
            subtype="law_review",
            category="secondary_source",
        )

    def _map_law_citation(self, citation: FullLawCitation) -> LurisEntityV2:
        """Map FullLawCitation to LurisEntityV2."""
        start_pos, end_pos = citation.span()

        # Try to determine if USC, CFR, or state statute
        text = citation.matched_text()
        if "U. S. C." in text or "U.S.C." in text:
            entity_type = EntityType.USC_CITATION
            subtype = "usc"
        elif "CFR" in text:
            entity_type = EntityType.CFR_CITATION
            subtype = "cfr"
        elif "Stat." in text:
            entity_type = EntityType.STATUTE_CITATION
            subtype = "federal_statute"
        else:
            # Likely state statute
            entity_type = EntityType.STATE_STATUTE_CITATION
            subtype = "state_statute"

        return create_entity(
            text=text,
            entity_type=entity_type,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=self.default_eyecite_confidence,
            extraction_method=ExtractionMethod.EYECITE,
            metadata={
                "volume": getattr(citation, "volume", None),
                "reporter": getattr(citation, "reporter", None),
                "page": getattr(citation, "page", None),
                "citation_type": "FullLawCitation",
            },
            subtype=subtype,
            category="statutory",
        )

    def _map_unknown_citation(self, citation: UnknownCitation) -> LurisEntityV2:
        """
        Map UnknownCitation to LurisEntityV2.

        Note: These will need LLM classification in the hybrid pipeline.
        For now, we create an UNKNOWN_CITATION entity.
        """
        start_pos, end_pos = citation.span()

        return create_entity(
            text=citation.matched_text(),
            entity_type=EntityType.UNKNOWN_CITATION,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=0.5,  # Low confidence for unknowns
            extraction_method=ExtractionMethod.EYECITE,
            metadata={
                "citation_type": "UnknownCitation",
                "requires_llm_classification": True,
                "reason": "Eyecite detected potential citation but couldn't classify type",
            },
            subtype="unknown",
            category="unknown",
        )


def map_eyecite_citations(citations: list) -> list[LurisEntityV2]:
    """
    Batch map Eyecite citations to LurisEntityV2 entities.

    Args:
        citations: List of Eyecite citation objects

    Returns:
        List of LurisEntityV2 entities
    """
    mapper = EyeciteToLurisMapper()
    entities = []

    for citation in citations:
        try:
            entity = mapper.map_citation(citation)
            entities.append(entity)
        except Exception as e:
            print(f"Warning: Failed to map citation {citation}: {e}")
            continue

    return entities
