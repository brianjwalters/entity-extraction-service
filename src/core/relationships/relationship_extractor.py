"""
Relationship Extractor for CALES Legal Entity System

This module provides comprehensive relationship extraction capabilities
using pattern matching, dependency parsing, coreference resolution,
and proximity-based methods.
"""

import re
import logging
import time
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import uuid
from datetime import datetime
import spacy
from spacy.tokens import Doc, Span, Token
import numpy as np

from .relationship_models import (
    EntityMention,
    RelationshipInstance,
    RelationshipType,
    RelationshipExtractionResult,
    RelationshipExtractionModel
)
from .legal_relationship_patterns import (
    LegalRelationshipPatterns,
    RelationshipPattern
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for relationship extraction"""
    use_patterns: bool = True
    use_dependency_parsing: bool = True
    use_coreference: bool = True
    use_proximity: bool = True
    use_ml_model: bool = False
    
    # Thresholds
    pattern_confidence_threshold: float = 0.7
    dependency_confidence_threshold: float = 0.65
    proximity_confidence_threshold: float = 0.5
    ml_confidence_threshold: float = 0.75
    overall_confidence_threshold: float = 0.6
    
    # Windows and distances
    proximity_window: int = 100  # characters
    sentence_window: int = 2  # sentences
    max_entity_distance: int = 200  # characters
    
    # Model settings
    spacy_model: str = "en_core_web_lg"
    use_gpu: bool = True
    batch_size: int = 32
    
    # Output settings
    merge_duplicates: bool = True
    include_context: bool = True
    context_window: int = 50  # characters around relationship


class RelationshipExtractor:
    """
    Main class for extracting relationships between legal entities.
    Combines multiple extraction methods for comprehensive coverage.
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize the RelationshipExtractor.
        
        Args:
            config: Extraction configuration
        """
        self.config = config or ExtractionConfig()
        
        # Initialize components
        self.patterns = LegalRelationshipPatterns() if self.config.use_patterns else None
        self.nlp = self._load_spacy_model() if self.config.use_dependency_parsing else None
        self.ml_model = None
        
        # Initialize ML model if configured
        if self.config.use_ml_model:
            try:
                self.ml_model = RelationshipExtractionModel()
            except Exception as e:
                logger.warning(f"Failed to load ML model: {e}. Falling back to pattern-based extraction.")
                self.config.use_ml_model = False
        
        # Coreference resolution tracking
        self.coreference_chains: Dict[str, List[EntityMention]] = {}
        
        # Statistics
        self.extraction_stats = defaultdict(int)
    
    def _load_spacy_model(self) -> Optional[Any]:
        """Load SpaCy model for dependency parsing"""
        try:
            nlp = spacy.load(self.config.spacy_model)
            
            # Enable GPU if available and configured
            if self.config.use_gpu:
                spacy.prefer_gpu()
            
            # Add custom pipeline components if needed
            if not nlp.has_pipe("merge_entities"):
                nlp.add_pipe("merge_entities")
            
            return nlp
        except Exception as e:
            logger.error(f"Failed to load SpaCy model: {e}")
            return None
    
    def extract_relationships(self,
                             text: str,
                             entities: List[EntityMention],
                             document_id: str = "") -> RelationshipExtractionResult:
        """
        Extract all relationships from text given entities.
        
        Args:
            text: Document text
            entities: List of extracted entities
            document_id: Document identifier
            
        Returns:
            RelationshipExtractionResult with all extracted relationships
        """
        start_time = time.time()
        relationships = []
        
        # Build entity index for efficient lookup
        entity_index = self._build_entity_index(entities)
        
        # Resolve coreferences if enabled
        if self.config.use_coreference:
            self._resolve_coreferences(text, entities)
        
        # Extract using different methods
        if self.config.use_patterns:
            pattern_rels = self._extract_pattern_relationships(text, entities, entity_index)
            relationships.extend(pattern_rels)
            self.extraction_stats["pattern_relationships"] = len(pattern_rels)
        
        if self.config.use_dependency_parsing and self.nlp:
            dep_rels = self._extract_dependency_relationships(text, entities, entity_index)
            relationships.extend(dep_rels)
            self.extraction_stats["dependency_relationships"] = len(dep_rels)
        
        if self.config.use_proximity:
            prox_rels = self._extract_proximity_relationships(text, entities)
            relationships.extend(prox_rels)
            self.extraction_stats["proximity_relationships"] = len(prox_rels)
        
        if self.config.use_ml_model and self.ml_model:
            ml_rels = self._extract_ml_relationships(text, entities)
            relationships.extend(ml_rels)
            self.extraction_stats["ml_relationships"] = len(ml_rels)
        
        # Merge duplicate relationships if configured
        if self.config.merge_duplicates:
            relationships = self._merge_duplicate_relationships(relationships)
        
        # Filter by confidence threshold
        relationships = [r for r in relationships 
                        if r.confidence >= self.config.overall_confidence_threshold]
        
        # Add context to relationships if configured
        if self.config.include_context:
            self._add_context_to_relationships(text, relationships)
        
        # Calculate statistics
        extraction_time = (time.time() - start_time) * 1000  # Convert to ms
        statistics = self._calculate_statistics(relationships, entities)
        
        return RelationshipExtractionResult(
            document_id=document_id,
            relationships=relationships,
            entities=entities,
            extraction_time_ms=extraction_time,
            model_used=self._get_model_description(),
            extraction_config=self.config.__dict__,
            statistics=statistics
        )
    
    def _build_entity_index(self, entities: List[EntityMention]) -> Dict:
        """Build index for efficient entity lookup"""
        index = {
            "by_position": defaultdict(list),
            "by_type": defaultdict(list),
            "by_text": defaultdict(list)
        }
        
        for entity in entities:
            # Index by position range
            for pos in range(entity.start_position, entity.end_position + 1):
                index["by_position"][pos].append(entity)
            
            # Index by type
            index["by_type"][entity.entity_type].append(entity)
            
            # Index by text (lowercase for matching)
            index["by_text"][entity.entity_text.lower()].append(entity)
        
        return index
    
    def _resolve_coreferences(self, text: str, entities: List[EntityMention]):
        """
        Resolve coreferences between entities.
        Simple heuristic-based approach for legal documents.
        """
        # Group entities by type
        entities_by_type = defaultdict(list)
        for entity in entities:
            entities_by_type[entity.entity_type].append(entity)
        
        # Resolve pronouns and references
        for entity_type, entity_list in entities_by_type.items():
            if entity_type in ["PARTY", "PLAINTIFF", "DEFENDANT", "PERSON"]:
                self._resolve_party_coreferences(text, entity_list)
            elif entity_type in ["JUDGE"]:
                self._resolve_judge_coreferences(text, entity_list)
            elif entity_type in ["COURT"]:
                self._resolve_court_coreferences(text, entity_list)
    
    def _resolve_party_coreferences(self, text: str, entities: List[EntityMention]):
        """Resolve coreferences for party entities"""
        # Common pronouns and references in legal text
        party_references = {
            "plaintiff": ["the plaintiff", "plaintiffs", "petitioner", "complainant"],
            "defendant": ["the defendant", "defendants", "respondent", "accused"],
            "party": ["the party", "the parties", "such party", "said party"]
        }
        
        # Build coreference chains
        for entity in entities:
            canonical = entity.canonical_name or entity.entity_text
            chain_id = f"party_{canonical.lower().replace(' ', '_')}"
            
            if chain_id not in self.coreference_chains:
                self.coreference_chains[chain_id] = []
            
            self.coreference_chains[chain_id].append(entity)
            
            # Look for references in surrounding text
            context_start = max(0, entity.start_position - 200)
            context_end = min(len(text), entity.end_position + 200)
            context = text[context_start:context_end].lower()
            
            for ref_type, refs in party_references.items():
                for ref in refs:
                    if ref in context:
                        # Create a reference entity
                        ref_entity = EntityMention(
                            entity_id=f"{entity.entity_id}_ref",
                            entity_type=entity.entity_type,
                            entity_text=ref,
                            start_position=context_start + context.index(ref),
                            end_position=context_start + context.index(ref) + len(ref),
                            confidence=0.7,
                            canonical_name=canonical,
                            metadata={"coreference": True, "refers_to": entity.entity_id}
                        )
                        self.coreference_chains[chain_id].append(ref_entity)
    
    def _resolve_judge_coreferences(self, text: str, entities: List[EntityMention]):
        """Resolve coreferences for judge entities"""
        judge_references = ["the court", "this court", "the judge", "his honor", "her honor"]
        
        for entity in entities:
            canonical = entity.canonical_name or entity.entity_text
            chain_id = f"judge_{canonical.lower().replace(' ', '_')}"
            
            if chain_id not in self.coreference_chains:
                self.coreference_chains[chain_id] = []
            
            self.coreference_chains[chain_id].append(entity)
    
    def _resolve_court_coreferences(self, text: str, entities: List[EntityMention]):
        """Resolve coreferences for court entities"""
        court_references = ["this court", "the court", "the tribunal"]
        
        for entity in entities:
            canonical = entity.canonical_name or entity.entity_text
            chain_id = f"court_{canonical.lower().replace(' ', '_')}"
            
            if chain_id not in self.coreference_chains:
                self.coreference_chains[chain_id] = []
            
            self.coreference_chains[chain_id].append(entity)
    
    def _extract_pattern_relationships(self,
                                      text: str,
                                      entities: List[EntityMention],
                                      entity_index: Dict) -> List[RelationshipInstance]:
        """Extract relationships using regex patterns"""
        relationships = []
        
        if not self.patterns:
            return relationships
        
        # Get all patterns
        all_patterns = self.patterns.get_all_patterns()
        
        for pattern in all_patterns:
            # Skip low confidence patterns if threshold is set
            if pattern.confidence < self.config.pattern_confidence_threshold:
                continue
            
            # Find all matches
            matches = pattern.compiled_regex.finditer(text)
            
            for match in matches:
                # Extract entities from match groups
                rel = self._create_relationship_from_pattern(
                    match, pattern, text, entities, entity_index
                )
                
                if rel:
                    relationships.append(rel)
                    
                    # Handle bidirectional relationships
                    if pattern.bidirectional:
                        reverse_rel = self._create_reverse_relationship(rel)
                        if reverse_rel:
                            relationships.append(reverse_rel)
        
        return relationships
    
    def _create_relationship_from_pattern(self,
                                         match,
                                         pattern: RelationshipPattern,
                                         text: str,
                                         entities: List[EntityMention],
                                         entity_index: Dict) -> Optional[RelationshipInstance]:
        """Create relationship instance from pattern match"""
        try:
            # Get match span
            start_pos = match.start()
            end_pos = match.end()
            
            # Find entities in the match
            matched_entities = self._find_entities_in_span(
                start_pos, end_pos, entities, entity_index
            )
            
            if len(matched_entities) < 2:
                return None
            
            # Determine source and target based on pattern
            source_entity = None
            target_entity = None
            
            # Try to match entities to expected types
            for entity in matched_entities:
                if entity.entity_type in pattern.subject_types and not source_entity:
                    source_entity = entity
                elif entity.entity_type in pattern.object_types and not target_entity:
                    target_entity = entity
            
            if not source_entity or not target_entity:
                # Fallback: use first two entities
                if len(matched_entities) >= 2:
                    source_entity = matched_entities[0]
                    target_entity = matched_entities[1]
                else:
                    return None
            
            # Create relationship instance
            rel_id = str(uuid.uuid4())
            context = text[start_pos:end_pos]
            
            return RelationshipInstance(
                relationship_id=rel_id,
                relationship_type=RelationshipType(pattern.relationship_type),
                source_entity=source_entity,
                target_entity=target_entity,
                confidence=pattern.confidence,
                extraction_method="pattern",
                context=context,
                context_start=start_pos,
                context_end=end_pos,
                evidence=[pattern.pattern],
                metadata={
                    "pattern_category": pattern.relationship_type,
                    "pattern_confidence": pattern.confidence
                }
            )
            
        except Exception as e:
            logger.debug(f"Error creating relationship from pattern: {e}")
            return None
    
    def _find_entities_in_span(self,
                               start: int,
                               end: int,
                               entities: List[EntityMention],
                               entity_index: Dict) -> List[EntityMention]:
        """Find entities within a text span"""
        found_entities = set()
        
        # Use position index for efficient lookup
        for pos in range(start, end + 1):
            if pos in entity_index["by_position"]:
                for entity in entity_index["by_position"][pos]:
                    # Check if entity is fully within span
                    if entity.start_position >= start and entity.end_position <= end:
                        found_entities.add(entity)
        
        return list(found_entities)
    
    def _create_reverse_relationship(self, 
                                    rel: RelationshipInstance) -> Optional[RelationshipInstance]:
        """Create reverse relationship for bidirectional patterns"""
        try:
            reverse_rel = RelationshipInstance(
                relationship_id=f"{rel.relationship_id}_reverse",
                relationship_type=rel.relationship_type,
                source_entity=rel.target_entity,  # Swap source and target
                target_entity=rel.source_entity,
                confidence=rel.confidence * 0.9,  # Slightly lower confidence for reverse
                extraction_method=rel.extraction_method,
                context=rel.context,
                context_start=rel.context_start,
                context_end=rel.context_end,
                evidence=rel.evidence + ["bidirectional"],
                metadata={**rel.metadata, "is_reverse": True}
            )
            return reverse_rel
        except Exception as e:
            logger.debug(f"Error creating reverse relationship: {e}")
            return None
    
    def _extract_dependency_relationships(self,
                                         text: str,
                                         entities: List[EntityMention],
                                         entity_index: Dict) -> List[RelationshipInstance]:
        """Extract relationships using dependency parsing"""
        relationships = []
        
        if not self.nlp:
            return relationships
        
        # Process text with SpaCy
        doc = self.nlp(text)
        
        # Map entities to SpaCy tokens
        entity_tokens = self._map_entities_to_tokens(entities, doc)
        
        # Extract relationships from dependencies
        for sent in doc.sents:
            sent_relationships = self._extract_sentence_dependencies(
                sent, entity_tokens, entities
            )
            relationships.extend(sent_relationships)
        
        return relationships
    
    def _map_entities_to_tokens(self,
                                entities: List[EntityMention],
                                doc: Doc) -> Dict[EntityMention, List[Token]]:
        """Map entities to SpaCy tokens"""
        entity_tokens = {}
        
        for entity in entities:
            tokens = []
            for token in doc:
                # Check if token overlaps with entity
                if (token.idx >= entity.start_position and 
                    token.idx + len(token.text) <= entity.end_position):
                    tokens.append(token)
            
            if tokens:
                entity_tokens[entity] = tokens
        
        return entity_tokens
    
    def _extract_sentence_dependencies(self,
                                      sent: Span,
                                      entity_tokens: Dict,
                                      entities: List[EntityMention]) -> List[RelationshipInstance]:
        """Extract relationships from sentence dependencies"""
        relationships = []
        
        # Find entities in this sentence
        sent_entities = []
        for entity, tokens in entity_tokens.items():
            if any(token in sent for token in tokens):
                sent_entities.append(entity)
        
        if len(sent_entities) < 2:
            return relationships
        
        # Analyze dependency paths between entities
        for i, entity1 in enumerate(sent_entities):
            for entity2 in sent_entities[i+1:]:
                dep_rel = self._analyze_dependency_path(
                    entity1, entity2, entity_tokens, sent
                )
                if dep_rel:
                    relationships.append(dep_rel)
        
        return relationships
    
    def _analyze_dependency_path(self,
                                entity1: EntityMention,
                                entity2: EntityMention,
                                entity_tokens: Dict,
                                sent: Span) -> Optional[RelationshipInstance]:
        """Analyze dependency path between two entities"""
        try:
            tokens1 = entity_tokens.get(entity1, [])
            tokens2 = entity_tokens.get(entity2, [])
            
            if not tokens1 or not tokens2:
                return None
            
            # Get head tokens
            head1 = self._get_head_token(tokens1)
            head2 = self._get_head_token(tokens2)
            
            # Find path between heads
            path = self._find_dependency_path(head1, head2)
            
            if not path:
                return None
            
            # Analyze path to determine relationship
            rel_type, confidence = self._classify_dependency_path(path, entity1, entity2)
            
            if confidence < self.config.dependency_confidence_threshold:
                return None
            
            # Create relationship
            rel_id = str(uuid.uuid4())
            context = sent.text
            
            return RelationshipInstance(
                relationship_id=rel_id,
                relationship_type=rel_type,
                source_entity=entity1,
                target_entity=entity2,
                confidence=confidence,
                extraction_method="dependency",
                context=context,
                context_start=sent.start_char,
                context_end=sent.end_char,
                evidence=[f"dep_path: {' -> '.join([t.dep_ for t in path])}"],
                metadata={
                    "dependency_path": [t.dep_ for t in path],
                    "path_length": len(path)
                }
            )
            
        except Exception as e:
            logger.debug(f"Error analyzing dependency path: {e}")
            return None
    
    def _get_head_token(self, tokens: List[Token]) -> Token:
        """Get the head token from a list of tokens"""
        # Find the token that is the head of the phrase
        for token in tokens:
            if token.head not in tokens:
                return token
        return tokens[0]  # Fallback to first token
    
    def _find_dependency_path(self, token1: Token, token2: Token) -> List[Token]:
        """Find shortest dependency path between two tokens"""
        # Simple BFS to find path
        visited = set()
        queue = [(token1, [token1])]
        
        while queue:
            current, path = queue.pop(0)
            
            if current == token2:
                return path
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Add head and children
            if current.head != current:
                queue.append((current.head, path + [current.head]))
            
            for child in current.children:
                queue.append((child, path + [child]))
        
        return []
    
    def _classify_dependency_path(self,
                                 path: List[Token],
                                 entity1: EntityMention,
                                 entity2: EntityMention) -> Tuple[RelationshipType, float]:
        """Classify relationship based on dependency path"""
        # Extract dependency labels and lemmas
        deps = [t.dep_ for t in path]
        lemmas = [t.lemma_ for t in path]
        
        # Legal relationship patterns in dependencies
        patterns = {
            ("nsubj", "dobj"): (RelationshipType.RELATED_TO, 0.7),
            ("nsubj", "represent"): (RelationshipType.REPRESENTS, 0.85),
            ("nsubj", "sue"): (RelationshipType.SUES, 0.9),
            ("nsubj", "charge"): (RelationshipType.CHARGED_WITH, 0.85),
            ("nsubj", "convict"): (RelationshipType.CONVICTED_OF, 0.9),
            ("nsubj", "own"): (RelationshipType.OWNS, 0.85),
            ("nsubj", "employ"): (RelationshipType.EMPLOYS, 0.85),
            ("nsubj", "preside"): (RelationshipType.PRESIDES_OVER, 0.9),
            ("nsubj", "rule"): (RelationshipType.RULED_ON, 0.85),
            ("nsubj", "file"): (RelationshipType.FILED_BY, 0.85),
            ("nsubj", "award"): (RelationshipType.AWARDED_TO, 0.85),
        }
        
        # Check for known patterns
        for pattern, (rel_type, conf) in patterns.items():
            if all(p in deps or p in lemmas for p in pattern):
                return rel_type, conf
        
        # Default relationship
        return RelationshipType.RELATED_TO, 0.65
    
    def _extract_proximity_relationships(self,
                                        text: str,
                                        entities: List[EntityMention]) -> List[RelationshipInstance]:
        """Extract relationships based on entity proximity"""
        relationships = []
        
        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.start_position)
        
        for i, entity1 in enumerate(sorted_entities):
            for entity2 in sorted_entities[i+1:]:
                # Check distance
                distance = entity2.start_position - entity1.end_position
                
                if distance > self.config.max_entity_distance:
                    break  # Entities are too far apart
                
                if distance <= self.config.proximity_window:
                    # Create proximity relationship
                    rel = self._create_proximity_relationship(
                        entity1, entity2, text, distance
                    )
                    if rel:
                        relationships.append(rel)
        
        return relationships
    
    def _create_proximity_relationship(self,
                                      entity1: EntityMention,
                                      entity2: EntityMention,
                                      text: str,
                                      distance: int) -> Optional[RelationshipInstance]:
        """Create relationship based on proximity"""
        # Calculate confidence based on distance
        confidence = max(
            self.config.proximity_confidence_threshold,
            1.0 - (distance / self.config.max_entity_distance)
        )
        
        # Determine relationship type based on entity types
        rel_type = self._infer_relationship_type(entity1, entity2, text)
        
        # Extract context
        context_start = entity1.start_position
        context_end = entity2.end_position
        context = text[context_start:context_end]
        
        rel_id = str(uuid.uuid4())
        
        return RelationshipInstance(
            relationship_id=rel_id,
            relationship_type=rel_type,
            source_entity=entity1,
            target_entity=entity2,
            confidence=confidence,
            extraction_method="proximity",
            context=context,
            context_start=context_start,
            context_end=context_end,
            evidence=[f"proximity_distance: {distance}"],
            metadata={
                "distance": distance,
                "proximity_confidence": confidence
            }
        )
    
    def _infer_relationship_type(self,
                                entity1: EntityMention,
                                entity2: EntityMention,
                                text: str) -> RelationshipType:
        """Infer relationship type based on entity types and context"""
        # Type-based inference rules
        type_rules = {
            ("ATTORNEY", "PLAINTIFF"): RelationshipType.REPRESENTS,
            ("ATTORNEY", "DEFENDANT"): RelationshipType.REPRESENTS,
            ("LAW_FIRM", "PARTY"): RelationshipType.REPRESENTS,
            ("JUDGE", "CASE"): RelationshipType.PRESIDES_OVER,
            ("PLAINTIFF", "DEFENDANT"): RelationshipType.SUES,
            ("CORPORATION", "CORPORATION"): RelationshipType.ASSOCIATED_WITH,
            ("PERSON", "CORPORATION"): RelationshipType.ASSOCIATED_WITH,
            ("COURT", "CASE"): RelationshipType.VENUE_FOR,
            ("PARTY", "CONTRACT"): RelationshipType.PART_OF,
        }
        
        # Check direct type match
        type_pair = (entity1.entity_type, entity2.entity_type)
        if type_pair in type_rules:
            return type_rules[type_pair]
        
        # Check reverse type match
        reverse_pair = (entity2.entity_type, entity1.entity_type)
        if reverse_pair in type_rules:
            return type_rules[reverse_pair]
        
        # Default to generic relationship
        return RelationshipType.RELATED_TO
    
    def _extract_ml_relationships(self,
                                 text: str,
                                 entities: List[EntityMention]) -> List[RelationshipInstance]:
        """Extract relationships using ML model"""
        relationships = []
        
        if not self.ml_model:
            return relationships
        
        # Create entity pairs for classification
        entity_pairs = []
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Filter by distance
                distance = abs(entity2.start_position - entity1.start_position)
                if distance <= self.config.max_entity_distance:
                    entity_pairs.append((entity1, entity2))
        
        if not entity_pairs:
            return relationships
        
        # Batch predict relationships
        predictions = self.ml_model.batch_predict(
            text, 
            entity_pairs,
            batch_size=self.config.batch_size
        )
        
        # Create relationship instances
        for (entity1, entity2), (rel_type, confidence) in zip(entity_pairs, predictions):
            if confidence >= self.config.ml_confidence_threshold:
                rel_id = str(uuid.uuid4())
                
                # Extract context
                context_start = min(entity1.start_position, entity2.start_position)
                context_end = max(entity1.end_position, entity2.end_position)
                context = text[context_start:context_end]
                
                rel = RelationshipInstance(
                    relationship_id=rel_id,
                    relationship_type=rel_type,
                    source_entity=entity1,
                    target_entity=entity2,
                    confidence=confidence,
                    extraction_method="model",
                    context=context,
                    context_start=context_start,
                    context_end=context_end,
                    evidence=["ml_model_prediction"],
                    metadata={
                        "model_confidence": confidence,
                        "model_name": self.ml_model.model_name
                    }
                )
                relationships.append(rel)
        
        return relationships
    
    def _merge_duplicate_relationships(self,
                                      relationships: List[RelationshipInstance]) -> List[RelationshipInstance]:
        """Merge duplicate relationships and boost confidence"""
        merged = {}
        
        for rel in relationships:
            # Create key for deduplication
            key = (
                rel.source_entity.entity_id,
                rel.target_entity.entity_id,
                rel.relationship_type.value
            )
            
            if key in merged:
                # Merge with existing
                existing = merged[key]
                
                # Boost confidence
                existing.confidence = min(1.0, existing.confidence + rel.confidence * 0.1)
                
                # Combine evidence
                existing.evidence.extend(rel.evidence)
                existing.evidence = list(set(existing.evidence))
                
                # Update metadata
                if "extraction_methods" not in existing.metadata:
                    existing.metadata["extraction_methods"] = [existing.extraction_method]
                existing.metadata["extraction_methods"].append(rel.extraction_method)
                existing.metadata["merged_count"] = existing.metadata.get("merged_count", 1) + 1
            else:
                merged[key] = rel
        
        return list(merged.values())
    
    def _add_context_to_relationships(self,
                                     text: str,
                                     relationships: List[RelationshipInstance]):
        """Add expanded context to relationships"""
        for rel in relationships:
            if not rel.context:
                # Extract context if not present
                window = self.config.context_window
                start = max(0, rel.context_start - window)
                end = min(len(text), rel.context_end + window)
                
                # Expand to word boundaries
                while start > 0 and text[start] not in ' \n\t':
                    start -= 1
                while end < len(text) and text[end] not in ' \n\t':
                    end += 1
                
                rel.context = text[start:end].strip()
                rel.context_start = start
                rel.context_end = end
    
    def _calculate_statistics(self,
                            relationships: List[RelationshipInstance],
                            entities: List[EntityMention]) -> Dict[str, Any]:
        """Calculate extraction statistics"""
        stats = {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "unique_entity_pairs": len(set(
                (r.source_entity.entity_id, r.target_entity.entity_id) 
                for r in relationships
            )),
            "relationship_types": defaultdict(int),
            "extraction_methods": defaultdict(int),
            "confidence_distribution": {
                "high": 0,  # >= 0.8
                "medium": 0,  # 0.6 - 0.8
                "low": 0  # < 0.6
            },
            "entity_participation": defaultdict(int)
        }
        
        for rel in relationships:
            # Count by type
            stats["relationship_types"][rel.relationship_type.value] += 1
            
            # Count by extraction method
            stats["extraction_methods"][rel.extraction_method] += 1
            
            # Confidence distribution
            if rel.confidence >= 0.8:
                stats["confidence_distribution"]["high"] += 1
            elif rel.confidence >= 0.6:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1
            
            # Entity participation
            stats["entity_participation"][rel.source_entity.entity_id] += 1
            stats["entity_participation"][rel.target_entity.entity_id] += 1
        
        # Add extraction method statistics
        stats.update(self.extraction_stats)
        
        # Convert defaultdicts to regular dicts for serialization
        stats["relationship_types"] = dict(stats["relationship_types"])
        stats["extraction_methods"] = dict(stats["extraction_methods"])
        stats["entity_participation"] = dict(stats["entity_participation"])
        
        return stats
    
    def _get_model_description(self) -> str:
        """Get description of models/methods used"""
        methods = []
        
        if self.config.use_patterns:
            methods.append("patterns")
        if self.config.use_dependency_parsing:
            methods.append(f"dependency ({self.config.spacy_model})")
        if self.config.use_coreference:
            methods.append("coreference")
        if self.config.use_proximity:
            methods.append("proximity")
        if self.config.use_ml_model and self.ml_model:
            methods.append(f"ml_model ({self.ml_model.model_name})")
        
        return f"RelationshipExtractor[{', '.join(methods)}]"
    
    def get_configuration(self) -> Dict:
        """Get current configuration"""
        return self.config.__dict__
    
    def update_configuration(self, **kwargs):
        """Update configuration parameters"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def get_statistics(self) -> Dict:
        """Get cumulative extraction statistics"""
        return dict(self.extraction_stats)