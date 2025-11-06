"""
Hybrid Citation Extraction Pipeline

Combines Eyecite (fast citation extraction) with LLM (contextual classification)
for optimal speed and accuracy.

Architecture:
1. Eyecite extracts all citations (3-10 seconds)
2. Known citations → Direct mapping to LurisEntityV2
3. Unknown citations → LLM classification with context
4. Merge results into final entity list
"""

import time
from typing import List, Dict, Any, Tuple
from collections import Counter

import pypdf
from eyecite import clean_text, get_citations, resolve_citations
from eyecite.models import UnknownCitation

from .luris_entity_v2 import LurisEntityV2, EntityType
from .eyecite_to_luris_mapper import map_eyecite_citations
from .llm_unknown_classifier import LLMUnknownClassifier


class HybridExtractionPipeline:
    """
    Hybrid citation extraction pipeline.

    Combines Eyecite's fast deterministic extraction with LLM's
    contextual understanding for unknown citations.
    """

    def __init__(self, use_mock_llm: bool = True):
        """
        Initialize pipeline.

        Args:
            use_mock_llm: If True, use mock LLM classifier (for PoC).
                         If False, use real vLLM API (requires service running).
        """
        self.use_mock_llm = use_mock_llm
        self.llm_classifier = LLMUnknownClassifier(use_mock=use_mock_llm)

        # Statistics
        self.stats = {
            "eyecite_time": 0.0,
            "llm_time": 0.0,
            "total_time": 0.0,
            "total_citations": 0,
            "known_citations": 0,
            "unknown_citations": 0,
            "llm_classified": 0,
            "false_positives": 0,
        }

    def extract_from_pdf(self, pdf_path: str) -> Tuple[List[LurisEntityV2], Dict[str, Any]]:
        """
        Extract citations from PDF document.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (entities list, statistics dict)
        """
        print(f"\n{'='*80}")
        print(f"HYBRID EXTRACTION PIPELINE: {pdf_path}")
        print(f"{'='*80}\n")

        total_start = time.time()

        # Step 1: Extract text from PDF
        print("📄 Step 1: Extracting text from PDF...")
        text = self._extract_text_from_pdf(pdf_path)
        print(f"   ✓ Extracted {len(text):,} characters\n")

        # Step 2: Eyecite extraction
        print("🔍 Step 2: Eyecite citation extraction...")
        eyecite_start = time.time()
        cleaned_text = clean_text(text, ["all_whitespace"])
        citations = get_citations(cleaned_text)
        eyecite_time = time.time() - eyecite_start

        print(f"   ✓ Found {len(citations)} citations in {eyecite_time:.2f} seconds\n")

        # Step 3: Separate known from unknown
        print("📊 Step 3: Categorizing citations...")
        known_citations = [c for c in citations if not isinstance(c, UnknownCitation)]
        unknown_citations = [c for c in citations if isinstance(c, UnknownCitation)]

        print(f"   ✓ Known citations: {len(known_citations)} ({len(known_citations)/len(citations)*100:.1f}%)")
        print(f"   ⚠️  Unknown citations: {len(unknown_citations)} ({len(unknown_citations)/len(citations)*100:.1f}%)\n")

        # Step 4: Map known citations
        print("🔄 Step 4: Mapping known citations to LurisEntityV2...")
        known_entities = map_eyecite_citations(known_citations)
        print(f"   ✓ Mapped {len(known_entities)} known entities\n")

        # Step 5: LLM classification of unknowns
        print(f"🤖 Step 5: LLM classification of {len(unknown_citations)} unknown citations...")
        llm_start = time.time()

        # Map unknowns to entities first (for context extraction)
        unknown_entities = map_eyecite_citations(unknown_citations)

        # Classify with LLM
        classified_entities = self.llm_classifier.classify_unknown_entities(
            unknown_entities,
            cleaned_text
        )
        llm_time = time.time() - llm_start

        false_positives = len(unknown_entities) - len(classified_entities)

        print(f"   ✓ Classified in {llm_time:.2f} seconds")
        print(f"   ✓ Valid citations: {len(classified_entities)}")
        print(f"   ✓ False positives filtered: {false_positives}\n")

        # Step 6: Merge results
        print("🔗 Step 6: Merging results...")
        all_entities = known_entities + classified_entities

        # Sort by position
        all_entities.sort(key=lambda e: e.start_pos)

        total_time = time.time() - total_start

        print(f"   ✓ Total entities: {len(all_entities)}")
        print(f"   ✓ Total time: {total_time:.2f} seconds\n")

        # Update statistics
        self.stats = {
            "eyecite_time": eyecite_time,
            "llm_time": llm_time,
            "total_time": total_time,
            "total_citations": len(citations),
            "known_citations": len(known_citations),
            "unknown_citations": len(unknown_citations),
            "llm_classified": len(classified_entities),
            "false_positives": false_positives,
            "final_entity_count": len(all_entities),
        }

        return all_entities, self.stats

    def extract_from_text(self, text: str) -> Tuple[List[LurisEntityV2], Dict[str, Any]]:
        """
        Extract citations from plain text.

        Args:
            text: Document text

        Returns:
            Tuple of (entities list, statistics dict)
        """
        total_start = time.time()

        # Eyecite extraction
        eyecite_start = time.time()
        cleaned_text = clean_text(text, ["all_whitespace"])
        citations = get_citations(cleaned_text)
        eyecite_time = time.time() - eyecite_start

        # Separate known from unknown
        known_citations = [c for c in citations if not isinstance(c, UnknownCitation)]
        unknown_citations = [c for c in citations if isinstance(c, UnknownCitation)]

        # Map known citations
        known_entities = map_eyecite_citations(known_citations)

        # LLM classification of unknowns
        llm_start = time.time()
        unknown_entities = map_eyecite_citations(unknown_citations)
        classified_entities = self.llm_classifier.classify_unknown_entities(
            unknown_entities,
            cleaned_text
        )
        llm_time = time.time() - llm_start

        # Merge results
        all_entities = known_entities + classified_entities
        all_entities.sort(key=lambda e: e.start_pos)

        total_time = time.time() - total_start

        # Statistics
        self.stats = {
            "eyecite_time": eyecite_time,
            "llm_time": llm_time,
            "total_time": total_time,
            "total_citations": len(citations),
            "known_citations": len(known_citations),
            "unknown_citations": len(unknown_citations),
            "llm_classified": len(classified_entities),
            "false_positives": len(unknown_citations) - len(classified_entities),
            "final_entity_count": len(all_entities),
        }

        return all_entities, self.stats

    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        return self.stats

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        reader = pypdf.PdfReader(pdf_path)
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            text_parts.append(text)

        return "\n\n".join(text_parts)


def generate_entity_report(
    entities: List[LurisEntityV2],
    stats: Dict[str, Any],
) -> str:
    """
    Generate human-readable report of extracted entities.

    Args:
        entities: List of extracted entities
        stats: Extraction statistics

    Returns:
        Formatted report string
    """
    lines = []

    lines.append("=" * 80)
    lines.append("HYBRID EXTRACTION RESULTS")
    lines.append("=" * 80)
    lines.append("")

    # Performance statistics
    lines.append("⏱️  PERFORMANCE STATISTICS")
    lines.append("-" * 80)
    lines.append(f"Eyecite extraction time: {stats['eyecite_time']:.2f}s")
    lines.append(f"LLM classification time: {stats['llm_time']:.2f}s")
    lines.append(f"Total processing time:   {stats['total_time']:.2f}s")
    lines.append("")

    # Citation statistics
    lines.append("📊 CITATION STATISTICS")
    lines.append("-" * 80)
    lines.append(f"Total citations found:       {stats['total_citations']}")
    lines.append(f"Known citations (Eyecite):   {stats['known_citations']} ({stats['known_citations']/stats['total_citations']*100:.1f}%)")
    lines.append(f"Unknown citations:           {stats['unknown_citations']} ({stats['unknown_citations']/stats['total_citations']*100:.1f}%)")
    lines.append(f"LLM classified:              {stats['llm_classified']}")
    lines.append(f"False positives filtered:    {stats['false_positives']}")
    lines.append(f"Final entity count:          {stats['final_entity_count']}")
    lines.append("")

    # Entity type breakdown
    entity_types = Counter(e.entity_type for e in entities)
    extraction_methods = Counter(e.extraction_method for e in entities)

    lines.append("🏷️  ENTITY TYPE BREAKDOWN")
    lines.append("-" * 80)
    for entity_type, count in entity_types.most_common():
        percentage = count / len(entities) * 100
        lines.append(f"{entity_type:35s} {count:5d} ({percentage:5.1f}%)")
    lines.append("")

    lines.append("🔧 EXTRACTION METHOD BREAKDOWN")
    lines.append("-" * 80)
    for method, count in extraction_methods.most_common():
        percentage = count / len(entities) * 100
        lines.append(f"{method:35s} {count:5d} ({percentage:5.1f}%)")
    lines.append("")

    # Sample entities
    lines.append("📋 SAMPLE ENTITIES (First 20)")
    lines.append("-" * 80)
    for i, entity in enumerate(entities[:20], 1):
        lines.append(f"{i:3d}. [{entity.entity_type:25s}] {entity.text}")
        lines.append(f"      Method: {entity.extraction_method} | Confidence: {entity.confidence:.2f}")
        if entity.metadata.get("llm_reasoning"):
            lines.append(f"      LLM: {entity.metadata['llm_reasoning']}")
    lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)
