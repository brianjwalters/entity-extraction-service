"""
Entity Processor Module

Provides deduplication, normalization, and grouping capabilities for extracted entities.
This module ensures that duplicate entities are removed, text is normalized, and 
entities are properly organized by type for better downstream processing.
"""

import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessedEntity:
    """Represents a processed entity with normalized fields."""
    text: str
    cleaned_text: str
    entity_type: str
    entity_subtype: str
    confidence_score: float
    positions: List[Dict[str, Any]]  # List of all positions where this entity appears
    extraction_method: str
    attributes: Dict[str, Any]
    ai_enhancements: List[str]
    first_occurrence: int  # Position of first occurrence
    occurrence_count: int  # Number of times this entity appears


class EntityProcessor:
    """
    Processes extracted entities to remove duplicates, normalize text,
    and organize entities for optimal downstream processing.
    """
    
    # Common articles and prepositions to remove for normalization
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'over'
    }
    
    # Legal abbreviations that should be preserved
    LEGAL_ABBREVIATIONS = {
        'U.S.', 'v.', 'vs.', 'Inc.', 'Corp.', 'LLC', 'L.L.C.', 'Ltd.',
        'P.C.', 'L.P.', 'LLP', 'L.L.P.', 'Co.', 'Assn.', 'Assoc.',
        'Fed.', 'App.', 'Cir.', 'Dist.', 'Ct.', 'Sup.', 'S.Ct.'
    }
    
    def __init__(self, 
                 similarity_threshold: float = 0.85,
                 preserve_legal_formatting: bool = True):
        """
        Initialize the EntityProcessor.
        
        Args:
            similarity_threshold: Threshold for considering entities as duplicates (0.0-1.0)
            preserve_legal_formatting: Whether to preserve legal formatting conventions
        """
        self.similarity_threshold = similarity_threshold
        self.preserve_legal_formatting = preserve_legal_formatting
        self.processing_stats = defaultdict(int)
    
    def process_entities(self, entities: List[Dict[str, Any]], 
                        chunk_info: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Process a list of entities to remove duplicates and normalize text.
        
        Args:
            entities: List of entity dictionaries from extraction
            chunk_info: Optional information about document chunks for position adjustment
            
        Returns:
            List of processed, deduplicated entities
        """
        if not entities:
            return []
        
        logger.info(f"Processing {len(entities)} entities for deduplication and normalization")
        
        # Reset stats for this processing run
        self.processing_stats.clear()
        self.processing_stats['input_count'] = len(entities)
        
        # Step 1: Normalize entity text for comparison
        normalized_entities = self._normalize_entities(entities)
        
        # Step 2: Group entities by normalized key
        entity_groups = self._group_entities(normalized_entities)
        
        # Step 3: Deduplicate within groups, keeping highest confidence
        deduplicated = self._deduplicate_groups(entity_groups)
        
        # Step 4: Adjust positions for chunked documents if needed
        if chunk_info:
            deduplicated = self._adjust_positions_for_chunks(deduplicated, chunk_info)
        
        # Step 5: Sort by first occurrence position
        deduplicated.sort(key=lambda e: e.get('position', {}).get('start', 0))
        
        self.processing_stats['output_count'] = len(deduplicated)
        self.processing_stats['duplicates_removed'] = (
            self.processing_stats['input_count'] - self.processing_stats['output_count']
        )
        
        logger.info(f"Entity processing complete: {self.processing_stats['output_count']} unique entities "
                   f"({self.processing_stats['duplicates_removed']} duplicates removed)")
        
        return deduplicated
    
    def _normalize_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize entity text for comparison while preserving original text.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of entities with normalized text added
        """
        normalized = []
        
        for entity in entities:
            # Create a copy to avoid modifying original
            normalized_entity = entity.copy()
            
            # Get the text field (handle both 'text' and 'entity_text')
            text = entity.get('text') or entity.get('entity_text', '')
            
            # Normalize the text for comparison
            normalized_text = self._normalize_text(text)
            normalized_entity['normalized_text'] = normalized_text
            
            # Ensure we have the correct field names
            if 'entity_type' not in normalized_entity and 'type' in normalized_entity:
                normalized_entity['entity_type'] = normalized_entity['type']
            
            normalized.append(normalized_entity)
        
        return normalized
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for entity comparison.
        
        Args:
            text: Original entity text
            
        Returns:
            Normalized text for comparison
        """
        if not text:
            return ""
        
        normalized = text.strip()
        
        # Convert to lowercase for comparison
        normalized = normalized.lower()
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Remove possessive forms
        normalized = re.sub(r"'s\b", "", normalized)
        
        # Remove common articles at the beginning (unless it's a legal abbreviation)
        words = normalized.split()
        if words and words[0] in self.STOP_WORDS:
            # Check if it's part of a legal entity name that should be preserved
            if not self.preserve_legal_formatting or not self._is_legal_entity(text):
                words = words[1:]
                normalized = ' '.join(words)
        
        # Remove punctuation except for legal abbreviations
        if not self.preserve_legal_formatting:
            normalized = re.sub(r'[^\w\s]', '', normalized)
        else:
            # Preserve periods in legal abbreviations
            normalized = self._preserve_legal_punctuation(normalized)
        
        return normalized
    
    def _preserve_legal_punctuation(self, text: str) -> str:
        """
        Preserve punctuation in legal abbreviations while removing other punctuation.
        
        Args:
            text: Text to process
            
        Returns:
            Text with selective punctuation preservation
        """
        # Split into tokens
        tokens = re.split(r'(\s+)', text)
        processed_tokens = []
        
        for token in tokens:
            if token.strip():
                # Check if token is a legal abbreviation
                if any(abbr.lower() in token.lower() for abbr in self.LEGAL_ABBREVIATIONS):
                    processed_tokens.append(token)
                else:
                    # Remove punctuation from non-legal terms
                    cleaned = re.sub(r'[^\w\s\-]', '', token)
                    processed_tokens.append(cleaned)
            else:
                processed_tokens.append(token)
        
        return ''.join(processed_tokens)
    
    def _is_legal_entity(self, text: str) -> bool:
        """
        Check if text appears to be a legal entity name.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a legal entity
        """
        # Check for common legal entity indicators
        legal_indicators = [
            r'\bv\.\s+\w+',  # Case citations (e.g., "Smith v. Jones")
            r'\b(?:Inc|Corp|LLC|Ltd|Co)\b',  # Corporate entities
            r'\b(?:Court|District|Circuit|Judge)\b',  # Court-related
            r'\b(?:United States|U\.S\.)\b',  # Government entities
        ]
        
        for pattern in legal_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _group_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group entities by their normalized text and type.
        
        Args:
            entities: List of normalized entities
            
        Returns:
            Dictionary mapping group keys to lists of entities
        """
        groups = defaultdict(list)
        
        for entity in entities:
            # Create a grouping key from normalized text and entity type
            entity_type = entity.get('entity_type', 'UNKNOWN')
            normalized_text = entity.get('normalized_text', '')
            
            # Additional normalization for common variations
            # Handle U.S. vs United States
            normalized_text = normalized_text.replace('u.s.', 'united states')
            normalized_text = normalized_text.replace('us ', 'united states ')
            
            # Remove 'the' at the beginning for grouping
            if normalized_text.startswith('the '):
                normalized_text = normalized_text[4:]
            
            # Group by type and normalized text
            group_key = f"{entity_type}::{normalized_text}"
            groups[group_key].append(entity)
        
        self.processing_stats['unique_groups'] = len(groups)
        
        return groups
    
    def _deduplicate_groups(self, entity_groups: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Deduplicate entities within each group, keeping the highest confidence version.
        
        Args:
            entity_groups: Dictionary of grouped entities
            
        Returns:
            List of deduplicated entities
        """
        deduplicated = []
        
        for group_key, group_entities in entity_groups.items():
            if not group_entities:
                continue
            
            # Sort by confidence score (descending) to get the best version
            sorted_entities = sorted(
                group_entities,
                key=lambda e: e.get('confidence_score', 0.0) if isinstance(e.get('confidence_score'), (int, float)) else 0.0,
                reverse=True
            )
            
            # Take the highest confidence entity as the representative
            best_entity = sorted_entities[0].copy()
            
            # Collect all positions where this entity appears
            all_positions = []
            for entity in group_entities:
                position = entity.get('position')
                if position:
                    all_positions.append(position)
            
            # Update the best entity with aggregated information
            best_entity['positions'] = all_positions
            best_entity['occurrence_count'] = len(group_entities)
            
            # Keep the earliest position as the primary position
            if all_positions:
                earliest_position = min(all_positions, key=lambda p: p.get('start', float('inf')))
                best_entity['position'] = earliest_position
                best_entity['first_occurrence'] = earliest_position.get('start', 0)
            
            # Merge AI enhancements from all occurrences
            all_enhancements = set()
            for entity in group_entities:
                enhancements = entity.get('ai_enhancements', [])
                if enhancements:
                    all_enhancements.update(enhancements)
            
            if all_enhancements:
                best_entity['ai_enhancements'] = list(all_enhancements)
            
            # Track deduplication stats
            if len(group_entities) > 1:
                self.processing_stats['groups_with_duplicates'] += 1
                self.processing_stats['total_duplicates'] += (len(group_entities) - 1)
            
            deduplicated.append(best_entity)
        
        return deduplicated
    
    def _adjust_positions_for_chunks(self, entities: List[Dict[str, Any]], 
                                    chunk_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Adjust entity positions for chunked documents.
        
        Args:
            entities: List of entities
            chunk_info: Information about document chunks
            
        Returns:
            Entities with adjusted positions
        """
        chunk_offset = chunk_info.get('offset', 0)
        chunk_id = chunk_info.get('chunk_id', '')
        
        for entity in entities:
            # Adjust primary position
            position = entity.get('position')
            if position and isinstance(position, dict):
                position['start'] = position.get('start', 0) + chunk_offset
                position['end'] = position.get('end', 0) + chunk_offset
                position['chunk_id'] = chunk_id
            
            # Adjust all positions
            positions = entity.get('positions', [])
            for pos in positions:
                if isinstance(pos, dict):
                    pos['start'] = pos.get('start', 0) + chunk_offset
                    pos['end'] = pos.get('end', 0) + chunk_offset
                    pos['chunk_id'] = chunk_id
        
        return entities
    
    def group_entities_by_type(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group processed entities by their type.
        
        Args:
            entities: List of processed entities
            
        Returns:
            Dictionary mapping entity types to lists of entities
        """
        grouped = defaultdict(list)
        
        for entity in entities:
            entity_type = entity.get('entity_type', 'UNKNOWN')
            grouped[entity_type].append(entity)
        
        # Sort entities within each group by position
        for entity_type in grouped:
            grouped[entity_type].sort(
                key=lambda e: e.get('position', {}).get('start', 0)
            )
        
        return dict(grouped)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics from the last processing run.
        
        Returns:
            Dictionary of processing statistics
        """
        return dict(self.processing_stats)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize both texts
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Simple Jaccard similarity on word tokens
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 and not words2:
            return 1.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)