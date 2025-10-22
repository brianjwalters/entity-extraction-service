"""
Result Merger Module

This module provides sophisticated entity and citation deduplication across
document chunks, with confidence score aggregation and relationship extraction.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
from difflib import SequenceMatcher
import json


@dataclass
class EntityMatch:
    """Represents a matched entity across chunks."""
    text: str
    entity_type: str
    confidence_scores: List[float]
    source_chunks: Set[int]
    positions: List[Dict[str, int]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score."""
        return sum(self.confidence_scores) / len(self.confidence_scores) if self.confidence_scores else 0.0
    
    @property
    def max_confidence(self) -> float:
        """Get maximum confidence score."""
        return max(self.confidence_scores) if self.confidence_scores else 0.0
    
    @property
    def occurrence_count(self) -> int:
        """Get number of occurrences across chunks."""
        return len(self.positions)


@dataclass
class CitationMatch:
    """Represents a matched citation across chunks."""
    original_text: str
    normalized_text: str
    citation_type: Optional[str]
    confidence_scores: List[float]
    source_chunks: Set[int]
    positions: List[Dict[str, int]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score."""
        return sum(self.confidence_scores) / len(self.confidence_scores) if self.confidence_scores else 0.0


@dataclass
class MergedResults:
    """Complete merged extraction results."""
    entities: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    deduplication_stats: Dict[str, int]
    confidence_adjustments: Dict[str, int]
    metadata: Dict[str, Any]


class ResultMerger:
    """
    Sophisticated result merger for multi-chunk document processing.
    
    This merger handles:
    - Entity deduplication with fuzzy matching
    - Citation normalization and deduplication
    - Confidence score aggregation
    - Cross-chunk relationship extraction
    - Position adjustment for document-level coordinates
    """
    
    # Similarity thresholds
    ENTITY_SIMILARITY_THRESHOLD = 0.85
    CITATION_SIMILARITY_THRESHOLD = 0.90
    
    # Confidence adjustments
    MULTI_CHUNK_CONFIDENCE_BOOST = 0.10
    OVERLAP_CONFIDENCE_PENALTY = 0.05
    HIGH_OCCURRENCE_BOOST = 0.05
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the result merger."""
        self.logger = logger or logging.getLogger(__name__)
        self.dedup_stats = defaultdict(int)
        self.confidence_adjustments = defaultdict(int)
    
    def merge_chunk_results(
        self,
        chunk_results: List[Dict[str, Any]],
        chunk_boundaries: List[Tuple[int, int]],
        document_text: Optional[str] = None
    ) -> MergedResults:
        """
        Merge extraction results from multiple chunks.
        
        Args:
            chunk_results: List of extraction results from each chunk
            chunk_boundaries: List of (start, end) positions for each chunk
            document_text: Optional full document text for validation
            
        Returns:
            MergedResults with deduplicated and enhanced data
        """
        self.dedup_stats.clear()
        self.confidence_adjustments.clear()
        
        # Collect and adjust positions
        all_entities = self._collect_entities(chunk_results, chunk_boundaries)
        all_citations = self._collect_citations(chunk_results, chunk_boundaries)
        
        # Deduplicate entities
        unique_entities = self._deduplicate_entities(all_entities)
        self.logger.info(
            f"Entity deduplication: {len(all_entities)} → {len(unique_entities)} "
            f"({len(all_entities) - len(unique_entities)} duplicates removed)"
        )
        
        # Deduplicate citations
        unique_citations = self._deduplicate_citations(all_citations)
        self.logger.info(
            f"Citation deduplication: {len(all_citations)} → {len(unique_citations)} "
            f"({len(all_citations) - len(unique_citations)} duplicates removed)"
        )
        
        # Extract relationships
        relationships = self._extract_relationships(unique_entities, unique_citations)
        
        # Convert to final format
        final_entities = self._format_entities(unique_entities)
        final_citations = self._format_citations(unique_citations)
        final_relationships = self._format_relationships(relationships)
        
        # Validate if document text provided
        if document_text:
            self._validate_positions(final_entities, document_text, "entity")
            self._validate_positions(final_citations, document_text, "citation")
        
        return MergedResults(
            entities=final_entities,
            citations=final_citations,
            relationships=final_relationships,
            deduplication_stats=dict(self.dedup_stats),
            confidence_adjustments=dict(self.confidence_adjustments),
            metadata={
                "chunks_processed": len(chunk_results),
                "unique_entity_types": len(set(e["entity_type"] for e in final_entities)),
                "unique_citation_types": len(set(c.get("citation_type", "unknown") for c in final_citations)),
                "average_entity_confidence": sum(e.get("confidence_score", 0) for e in final_entities) / len(final_entities) if final_entities else 0,
                "average_citation_confidence": sum(c.get("confidence_score", 0) for c in final_citations) / len(final_citations) if final_citations else 0
            }
        )
    
    def _collect_entities(
        self,
        chunk_results: List[Dict[str, Any]],
        chunk_boundaries: List[Tuple[int, int]]
    ) -> List[Dict[str, Any]]:
        """
        Collect entities from all chunks with position adjustment.
        
        Args:
            chunk_results: Extraction results from each chunk
            chunk_boundaries: Chunk boundary positions
            
        Returns:
            List of entities with adjusted positions
        """
        all_entities = []
        
        for i, (result, (chunk_start, chunk_end)) in enumerate(zip(chunk_results, chunk_boundaries)):
            entities = result.get("entities", [])
            
            for entity in entities:
                entity_copy = entity.copy()
                
                # Adjust positions to document level
                if "position" in entity_copy:
                    pos = entity_copy["position"]
                    if isinstance(pos, dict):
                        pos["start"] = pos.get("start", 0) + chunk_start
                        pos["end"] = pos.get("end", 0) + chunk_start
                
                # Add chunk source
                entity_copy["source_chunk"] = i
                entity_copy["chunk_boundaries"] = (chunk_start, chunk_end)
                
                all_entities.append(entity_copy)
        
        return all_entities
    
    def _collect_citations(
        self,
        chunk_results: List[Dict[str, Any]],
        chunk_boundaries: List[Tuple[int, int]]
    ) -> List[Dict[str, Any]]:
        """
        Collect citations from all chunks with position adjustment.
        
        Args:
            chunk_results: Extraction results from each chunk
            chunk_boundaries: Chunk boundary positions
            
        Returns:
            List of citations with adjusted positions
        """
        all_citations = []
        
        for i, (result, (chunk_start, chunk_end)) in enumerate(zip(chunk_results, chunk_boundaries)):
            citations = result.get("citations", [])
            
            for citation in citations:
                citation_copy = citation.copy()
                
                # Adjust positions to document level
                if "position" in citation_copy:
                    pos = citation_copy["position"]
                    if isinstance(pos, dict):
                        pos["start"] = pos.get("start", 0) + chunk_start
                        pos["end"] = pos.get("end", 0) + chunk_start
                
                # Add chunk source
                citation_copy["source_chunk"] = i
                citation_copy["chunk_boundaries"] = (chunk_start, chunk_end)
                
                all_citations.append(citation_copy)
        
        return all_citations
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[EntityMatch]:
        """
        Deduplicate entities using fuzzy matching.
        
        Args:
            entities: List of entities to deduplicate
            
        Returns:
            List of unique EntityMatch objects
        """
        entity_matches = {}
        
        for entity in entities:
            text = entity.get("text", "").strip()
            entity_type = entity.get("entity_type", "unknown")
            confidence = entity.get("confidence_score", 0.7)
            position = entity.get("position", {})
            source_chunk = entity.get("source_chunk", 0)
            
            # Normalize text for matching
            normalized_text = self._normalize_text(text)
            
            # Look for existing matches
            match_found = False
            for key, match in entity_matches.items():
                if match.entity_type != entity_type:
                    continue
                
                # Calculate similarity
                similarity = self._calculate_similarity(
                    normalized_text,
                    self._normalize_text(match.text)
                )
                
                if similarity >= self.ENTITY_SIMILARITY_THRESHOLD:
                    # Merge with existing match
                    match.confidence_scores.append(confidence)
                    match.source_chunks.add(source_chunk)
                    match.positions.append(position)
                    
                    # Update text to longest version
                    if len(text) > len(match.text):
                        match.text = text
                    
                    match_found = True
                    self.dedup_stats["entities_merged"] += 1
                    break
            
            if not match_found:
                # Create new match
                key = f"{entity_type}:{normalized_text}"
                entity_matches[key] = EntityMatch(
                    text=text,
                    entity_type=entity_type,
                    confidence_scores=[confidence],
                    source_chunks={source_chunk},
                    positions=[position],
                    metadata=entity.get("metadata", {})
                )
                self.dedup_stats["entities_unique"] += 1
        
        return list(entity_matches.values())
    
    def _deduplicate_citations(self, citations: List[Dict[str, Any]]) -> List[CitationMatch]:
        """
        Deduplicate citations using normalization and fuzzy matching.
        
        Args:
            citations: List of citations to deduplicate
            
        Returns:
            List of unique CitationMatch objects
        """
        citation_matches = {}
        
        for citation in citations:
            original_text = citation.get("original_text", "").strip()
            citation_type = citation.get("citation_type")
            confidence = citation.get("confidence_score", 0.7)
            position = citation.get("position", {})
            source_chunk = citation.get("source_chunk", 0)
            
            # Normalize citation
            normalized = self._normalize_citation(original_text)
            
            # Look for existing matches
            match_found = False
            for key, match in citation_matches.items():
                # Calculate similarity
                similarity = self._calculate_similarity(
                    normalized,
                    match.normalized_text
                )
                
                if similarity >= self.CITATION_SIMILARITY_THRESHOLD:
                    # Merge with existing match
                    match.confidence_scores.append(confidence)
                    match.source_chunks.add(source_chunk)
                    match.positions.append(position)
                    
                    # Update to most complete version
                    if len(original_text) > len(match.original_text):
                        match.original_text = original_text
                    
                    match_found = True
                    self.dedup_stats["citations_merged"] += 1
                    break
            
            if not match_found:
                # Create new match
                key = normalized
                citation_matches[key] = CitationMatch(
                    original_text=original_text,
                    normalized_text=normalized,
                    citation_type=citation_type,
                    confidence_scores=[confidence],
                    source_chunks={source_chunk},
                    positions=[position],
                    metadata=citation.get("metadata", {})
                )
                self.dedup_stats["citations_unique"] += 1
        
        return list(citation_matches.values())
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for entity matching.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove punctuation at ends
        normalized = normalized.strip(' .,;:!?')
        
        return normalized
    
    def _normalize_citation(self, citation: str) -> str:
        """
        Normalize citation for matching.
        
        Args:
            citation: Citation text to normalize
            
        Returns:
            Normalized citation
        """
        # Remove spaces around punctuation
        normalized = re.sub(r'\s*([.,§])\s*', r'\1', citation)
        
        # Standardize section symbols
        normalized = normalized.replace('Section', '§').replace('section', '§')
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Convert to lowercase for comparison
        normalized = normalized.lower().strip()
        
        return normalized
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _extract_relationships(
        self,
        entities: List[EntityMatch],
        citations: List[CitationMatch]
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships between entities and citations.
        
        Args:
            entities: Deduplicated entities
            citations: Deduplicated citations
            
        Returns:
            List of extracted relationships
        """
        relationships = []
        
        # Find entity-citation relationships based on proximity
        for entity in entities:
            for citation in citations:
                # Check if they appear in the same chunks
                common_chunks = entity.source_chunks & citation.source_chunks
                
                if common_chunks:
                    # Check proximity in each common chunk
                    for chunk in common_chunks:
                        # Find positions in this chunk
                        entity_positions = [p for p in entity.positions 
                                          if entity.source_chunks]
                        citation_positions = [p for p in citation.positions 
                                            if citation.source_chunks]
                        
                        if entity_positions and citation_positions:
                            # Simple proximity check (within 200 chars)
                            for e_pos in entity_positions:
                                for c_pos in citation_positions:
                                    if abs(e_pos.get("start", 0) - c_pos.get("start", 0)) < 200:
                                        relationships.append({
                                            "type": "entity_cited_in",
                                            "source": {
                                                "text": entity.text,
                                                "type": entity.entity_type
                                            },
                                            "target": {
                                                "text": citation.original_text,
                                                "type": citation.citation_type
                                            },
                                            "confidence": (entity.average_confidence + citation.average_confidence) / 2,
                                            "source_chunks": list(common_chunks)
                                        })
                                        break
        
        self.dedup_stats["relationships_extracted"] = len(relationships)
        return relationships
    
    def _format_entities(self, entity_matches: List[EntityMatch]) -> List[Dict[str, Any]]:
        """
        Format EntityMatch objects to final entity format.
        
        Args:
            entity_matches: List of EntityMatch objects
            
        Returns:
            List of formatted entity dictionaries
        """
        formatted = []
        
        for match in entity_matches:
            # Adjust confidence based on occurrences
            confidence = match.max_confidence
            
            # Multi-chunk boost
            if len(match.source_chunks) > 1:
                confidence = min(1.0, confidence + self.MULTI_CHUNK_CONFIDENCE_BOOST)
                self.confidence_adjustments["multi_chunk_boost"] += 1
            
            # High occurrence boost
            if match.occurrence_count > 3:
                confidence = min(1.0, confidence + self.HIGH_OCCURRENCE_BOOST)
                self.confidence_adjustments["high_occurrence_boost"] += 1
            
            # Use first position as primary
            primary_position = match.positions[0] if match.positions else {}
            
            formatted.append({
                "text": match.text,
                "entity_type": match.entity_type,
                "confidence_score": confidence,
                "position": primary_position,
                "occurrences": match.occurrence_count,
                "source_chunks": list(match.source_chunks),
                "all_positions": match.positions,
                "metadata": match.metadata
            })
        
        return formatted
    
    def _format_citations(self, citation_matches: List[CitationMatch]) -> List[Dict[str, Any]]:
        """
        Format CitationMatch objects to final citation format.
        
        Args:
            citation_matches: List of CitationMatch objects
            
        Returns:
            List of formatted citation dictionaries
        """
        formatted = []
        
        for match in citation_matches:
            # Adjust confidence
            confidence = match.average_confidence
            
            # Multi-chunk boost
            if len(match.source_chunks) > 1:
                confidence = min(1.0, confidence + self.MULTI_CHUNK_CONFIDENCE_BOOST)
                self.confidence_adjustments["multi_chunk_boost"] += 1
            
            # Use first position as primary
            primary_position = match.positions[0] if match.positions else {}
            
            formatted.append({
                "original_text": match.original_text,
                "normalized_text": match.normalized_text,
                "citation_type": match.citation_type,
                "confidence_score": confidence,
                "position": primary_position,
                "occurrences": len(match.positions),
                "source_chunks": list(match.source_chunks),
                "all_positions": match.positions,
                "metadata": match.metadata
            })
        
        return formatted
    
    def _format_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format relationships to final format.
        
        Args:
            relationships: List of raw relationships
            
        Returns:
            List of formatted relationships
        """
        # Remove duplicate relationships
        unique_relationships = []
        seen = set()
        
        for rel in relationships:
            # Create unique key
            key = (
                rel["type"],
                rel["source"]["text"],
                rel["target"]["text"]
            )
            
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)
        
        return unique_relationships
    
    def _validate_positions(
        self,
        items: List[Dict[str, Any]],
        document_text: str,
        item_type: str
    ):
        """
        Validate that positions correctly map to document text.
        
        Args:
            items: List of items with positions
            document_text: Full document text
            item_type: Type of items (for logging)
        """
        validation_errors = 0
        
        for item in items:
            position = item.get("position", {})
            if position and "start" in position and "end" in position:
                start = position["start"]
                end = position["end"]
                
                # Check bounds
                if start < 0 or end > len(document_text) or start >= end:
                    self.logger.warning(
                        f"Invalid {item_type} position: start={start}, end={end}, "
                        f"doc_length={len(document_text)}"
                    )
                    validation_errors += 1
                    continue
                
                # Extract text at position
                extracted = document_text[start:end]
                expected = item.get("text", item.get("original_text", ""))
                
                # Check if text matches (fuzzy)
                similarity = self._calculate_similarity(
                    extracted.lower().strip(),
                    expected.lower().strip()
                )
                
                if similarity < 0.8:
                    self.logger.warning(
                        f"{item_type} text mismatch at position {start}-{end}: "
                        f"expected '{expected[:50]}...', got '{extracted[:50]}...'"
                    )
                    validation_errors += 1
        
        if validation_errors > 0:
            self.logger.warning(
                f"Position validation found {validation_errors} errors in {len(items)} {item_type}s"
            )


if __name__ == "__main__":
    # Test the merger
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    # Create test data
    chunk_results = [
        {
            "entities": [
                {"text": "John Smith", "entity_type": "PERSON", "confidence_score": 0.9, "position": {"start": 0, "end": 10}},
                {"text": "U.S. District Court", "entity_type": "COURT", "confidence_score": 0.8, "position": {"start": 20, "end": 39}}
            ],
            "citations": [
                {"original_text": "123 U.S. 456", "citation_type": "USC", "confidence_score": 0.9, "position": {"start": 50, "end": 62}}
            ]
        },
        {
            "entities": [
                {"text": "John Smith", "entity_type": "PERSON", "confidence_score": 0.85, "position": {"start": 0, "end": 10}},
                {"text": "Jane Doe", "entity_type": "PERSON", "confidence_score": 0.75, "position": {"start": 100, "end": 108}}
            ],
            "citations": [
                {"original_text": "123 U.S. 456", "citation_type": "USC", "confidence_score": 0.88, "position": {"start": 150, "end": 162}}
            ]
        }
    ]
    
    chunk_boundaries = [(0, 1000), (900, 1900)]
    
    merger = ResultMerger()
    results = merger.merge_chunk_results(chunk_results, chunk_boundaries)
    
    print(f"Merged Results:")
    print(f"  Unique entities: {len(results.entities)}")
    print(f"  Unique citations: {len(results.citations)}")
    print(f"  Relationships: {len(results.relationships)}")
    print(f"  Deduplication stats: {results.deduplication_stats}")
    print(f"  Confidence adjustments: {results.confidence_adjustments}")
    
    print(f"\nEntities:")
    for entity in results.entities:
        print(f"  - {entity['text']} ({entity['entity_type']}): {entity['confidence_score']:.2f}")
    
    print(f"\nCitations:")
    for citation in results.citations:
        print(f"  - {citation['original_text']}: {citation['confidence_score']:.2f}")