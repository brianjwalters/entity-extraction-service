"""
Entity Registry for Cross-Chunk Context Preservation

This module provides a comprehensive entity registry system for tracking entities
across document chunks, resolving references, and maintaining global context.
Supports the 7-pass extraction strategy with deduplication and normalization.
"""

import asyncio
import re
from collections import defaultdict, Counter
from typing import List, Dict, Optional, Set, Tuple, Any
from datetime import datetime
from difflib import SequenceMatcher
import logging
from pathlib import Path
import pickle
import zlib

from ..models.registry import (
    RegisteredEntity,
    EntityOccurrence,
    EntityRelationship,
    RegistryMetadata,
    ResolutionStatus,
    ReferenceType,
    EntityGraph,
    ResolutionCandidate,
    RegistrySnapshot
)
from ..models.entities import Entity, EntityType, TextPosition, EntityAttributes
from ..utils.pattern_loader import PatternLoader


class EntityRegistry:
    """
    Global entity registry for cross-chunk context preservation.
    
    Handles entity deduplication, reference resolution, and relationship mapping
    across document chunks while maintaining positional accuracy and supporting
    parallel processing.
    """
    
    def __init__(
        self,
        document_id: str,
        document_name: str,
        total_chunks: int,
        similarity_threshold: float = 0.85,
        enable_caching: bool = True,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the entity registry.
        
        Args:
            document_id: Unique document identifier
            document_name: Document name
            total_chunks: Total number of chunks in document
            similarity_threshold: Threshold for entity similarity matching (0.0-1.0)
            enable_caching: Enable registry caching for large documents
            cache_dir: Directory for cache files
        """
        self.logger = logging.getLogger(__name__)
        
        # Core registry storage
        self.entities: Dict[str, RegisteredEntity] = {}
        self.relationships: Dict[str, EntityRelationship] = {}
        self.entity_index: Dict[str, Set[str]] = defaultdict(set)  # text -> entity IDs
        self.type_index: Dict[EntityType, Set[str]] = defaultdict(set)  # type -> entity IDs
        self.chunk_index: Dict[str, Set[str]] = defaultdict(set)  # chunk -> entity IDs
        
        # Reference resolution
        self.reference_map: Dict[str, str] = {}  # reference text -> canonical entity ID
        self.pronoun_context: Dict[str, List[str]] = defaultdict(list)  # chunk -> recent entities
        
        # Metadata
        self.metadata = RegistryMetadata(
            document_id=document_id,
            document_name=document_name,
            total_chunks=total_chunks,
            configuration={
                "similarity_threshold": similarity_threshold,
                "enable_caching": enable_caching
            }
        )
        
        # Configuration
        self.similarity_threshold = similarity_threshold
        self.enable_caching = enable_caching
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./cache/registry")
        if self.enable_caching:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Performance tracking
        self.start_time = datetime.utcnow()
        
        # Pattern loader for entity variations
        try:
            self.pattern_loader = PatternLoader()
        except Exception as e:
            self.logger.warning(f"Could not load patterns: {e}")
            self.pattern_loader = None
    
    async def register_entity(
        self,
        entity: Entity,
        chunk_id: str,
        chunk_index: int,
        global_offset: int = 0
    ) -> str:
        """
        Register an entity occurrence from a chunk.
        
        Args:
            entity: Entity to register
            chunk_id: ID of the chunk containing the entity
            chunk_index: Sequential index of the chunk
            global_offset: Character offset of chunk start in document
            
        Returns:
            ID of the registered entity (may be merged with existing)
        """
        async with self._lock:
            # Create global position
            global_position = TextPosition(
                start=entity.position.start + global_offset,
                end=entity.position.end + global_offset,
                line_number=entity.position.line_number,
                context_start=entity.position.context_start + global_offset if entity.position.context_start else None,
                context_end=entity.position.context_end + global_offset if entity.position.context_end else None
            )
            
            # Create occurrence
            occurrence = EntityOccurrence(
                chunk_id=chunk_id,
                chunk_index=chunk_index,
                position=entity.position,
                global_position=global_position,
                text_variant=entity.text,
                reference_type=self._determine_reference_type(entity.text, entity.entity_type),
                confidence=entity.confidence_score,
                context_before=entity.context_snippet[:250] if entity.context_snippet else "",
                context_after=entity.context_snippet[-250:] if entity.context_snippet else "",
                extraction_metadata={
                    "method": entity.extraction_method.value,
                    "ai_enhancements": entity.ai_enhancements
                }
            )
            
            # Find or create registered entity
            registered_id = await self._find_or_create_entity(
                entity, occurrence, chunk_id, chunk_index
            )
            
            # Update indices
            self.entity_index[entity.text.lower()].add(registered_id)
            self.entity_index[entity.cleaned_text.lower()].add(registered_id)
            self.type_index[entity.entity_type].add(registered_id)
            self.chunk_index[chunk_id].add(registered_id)
            
            # Update metadata
            self.metadata.processed_chunks = max(
                self.metadata.processed_chunks, 
                chunk_index + 1
            )
            
            return registered_id
    
    async def _find_or_create_entity(
        self,
        entity: Entity,
        occurrence: EntityOccurrence,
        chunk_id: str,
        chunk_index: int
    ) -> str:
        """Find existing entity or create new one."""
        # Look for existing matches
        candidates = await self._find_similar_entities(entity)
        
        if candidates:
            # Merge with best match
            best_match = candidates[0]
            existing = self.entities[best_match.entity_id]
            
            # Add occurrence to existing entity
            existing.occurrences.append(occurrence)
            existing.all_variants.add(entity.text)
            existing.all_variants.add(entity.cleaned_text)
            existing.last_seen_chunk = chunk_id
            existing.chunk_span = (
                existing.chunk_span[0],
                max(existing.chunk_span[1], chunk_index)
            )
            existing.total_occurrences += 1
            existing.extraction_methods_used.add(entity.extraction_method.value)
            
            # Update confidence (weighted average)
            total_weight = existing.total_occurrences
            existing.aggregate_confidence = (
                (existing.aggregate_confidence * (total_weight - 1) + entity.confidence_score) 
                / total_weight
            )
            
            # Merge attributes
            self._merge_attributes(existing.attributes, entity.attributes)
            
            existing.updated_at = datetime.utcnow()
            
            return best_match.entity_id
        
        else:
            # Create new registered entity
            registered = RegisteredEntity(
                canonical_text=entity.cleaned_text,
                entity_type=entity.entity_type,
                entity_subtype=entity.entity_subtype,
                all_variants={entity.text, entity.cleaned_text},
                occurrences=[occurrence],
                resolution_status=ResolutionStatus.UNRESOLVED,
                aggregate_confidence=entity.confidence_score,
                attributes=entity.attributes,
                first_seen_chunk=chunk_id,
                last_seen_chunk=chunk_id,
                chunk_span=(chunk_index, chunk_index),
                total_occurrences=1,
                extraction_methods_used={entity.extraction_method.value}
            )
            
            self.entities[registered.id] = registered
            self.metadata.total_entities += 1
            
            # Update type distribution
            entity_type_str = entity.entity_type.value
            self.metadata.entity_type_distribution[entity_type_str] = \
                self.metadata.entity_type_distribution.get(entity_type_str, 0) + 1
            
            return registered.id
    
    async def _find_similar_entities(self, entity: Entity) -> List[ResolutionCandidate]:
        """Find similar entities for potential merging."""
        candidates = []
        
        # Get potential matches from indices
        potential_ids = set()
        
        # Check exact matches
        for variant in [entity.text.lower(), entity.cleaned_text.lower()]:
            potential_ids.update(self.entity_index.get(variant, set()))
        
        # Check same type entities
        type_entities = self.type_index.get(entity.entity_type, set())
        
        # Score each potential match
        for entity_id in potential_ids | type_entities:
            existing = self.entities[entity_id]
            
            # Skip if different types (unless related)
            if not self._are_compatible_types(entity.entity_type, existing.entity_type):
                continue
            
            # Calculate similarity
            similarity, features = self._calculate_similarity(entity, existing)
            
            if similarity >= self.similarity_threshold:
                candidates.append(ResolutionCandidate(
                    entity_id=entity_id,
                    similarity_score=similarity,
                    matching_features=features["matching"],
                    conflicting_features=features["conflicting"],
                    resolution_confidence=similarity,
                    resolution_method="similarity_matching"
                ))
        
        # Sort by similarity score
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return candidates
    
    def _calculate_similarity(
        self, 
        entity: Entity, 
        registered: RegisteredEntity
    ) -> Tuple[float, Dict[str, List[str]]]:
        """Calculate similarity between entities."""
        scores = []
        features = {"matching": [], "conflicting": []}
        
        # Text similarity
        text_sim = max(
            SequenceMatcher(None, entity.text.lower(), variant.lower()).ratio()
            for variant in registered.all_variants
        )
        scores.append(text_sim * 0.4)  # 40% weight
        if text_sim > 0.8:
            features["matching"].append("text_similarity")
        
        # Cleaned text similarity
        cleaned_sim = SequenceMatcher(
            None, 
            entity.cleaned_text.lower(), 
            registered.canonical_text.lower()
        ).ratio()
        scores.append(cleaned_sim * 0.3)  # 30% weight
        if cleaned_sim > 0.8:
            features["matching"].append("canonical_match")
        
        # Type match
        if entity.entity_type == registered.entity_type:
            scores.append(0.2)  # 20% weight
            features["matching"].append("same_type")
        else:
            features["conflicting"].append("different_type")
        
        # Subtype match
        if entity.entity_subtype == registered.entity_subtype:
            scores.append(0.1)  # 10% weight
            features["matching"].append("same_subtype")
        
        # Check for conflicting attributes
        if self._have_conflicting_attributes(entity.attributes, registered.attributes):
            scores.append(-0.2)  # Penalty for conflicts
            features["conflicting"].append("attribute_conflict")
        
        total_score = min(1.0, max(0.0, sum(scores)))
        
        return total_score, features
    
    def _are_compatible_types(self, type1: EntityType, type2: EntityType) -> bool:
        """Check if entity types are compatible for merging."""
        # Same type is always compatible
        if type1 == type2:
            return True
        
        # Define compatible type groups
        compatible_groups = [
            {EntityType.PLAINTIFF, EntityType.DEFENDANT, EntityType.PARTY},
            {EntityType.ATTORNEY, EntityType.LAW_FIRM},
            {EntityType.JUDGE, EntityType.MAGISTRATE, EntityType.ARBITRATOR},
            {EntityType.MOTION, EntityType.BRIEF, EntityType.DOCUMENT},
            {EntityType.FEDERAL_AGENCY, EntityType.STATE_AGENCY, EntityType.GOVERNMENT_ENTITY}
        ]
        
        for group in compatible_groups:
            if type1 in group and type2 in group:
                return True
        
        return False
    
    def _have_conflicting_attributes(
        self, 
        attrs1: EntityAttributes, 
        attrs2: EntityAttributes
    ) -> bool:
        """Check if attributes have conflicts."""
        # Check specific conflicting fields
        conflict_fields = [
            "court_name", "judge_title", "party_type", "filing_date"
        ]
        
        for field in conflict_fields:
            val1 = getattr(attrs1, field, None)
            val2 = getattr(attrs2, field, None)
            
            if val1 and val2 and val1 != val2:
                # Allow some flexibility for similar values
                if isinstance(val1, str) and isinstance(val2, str):
                    similarity = SequenceMatcher(None, val1.lower(), val2.lower()).ratio()
                    if similarity < 0.8:
                        return True
                else:
                    return True
        
        return False
    
    def _merge_attributes(
        self, 
        target: EntityAttributes, 
        source: EntityAttributes
    ) -> None:
        """Merge attributes from source into target."""
        # Merge all non-None attributes
        for field in source.__fields__:
            source_val = getattr(source, field)
            target_val = getattr(target, field)
            
            if source_val and not target_val:
                setattr(target, field, source_val)
            elif source_val and target_val:
                if field == "alternate_names" and isinstance(source_val, list):
                    # Merge lists
                    existing = set(target_val)
                    for name in source_val:
                        if name not in existing:
                            target_val.append(name)
                elif field == "additional_attributes" and isinstance(source_val, dict):
                    # Merge dictionaries
                    target_val.update(source_val)
    
    def _determine_reference_type(self, text: str, entity_type: EntityType) -> ReferenceType:
        """Determine the type of reference for an entity occurrence."""
        text_lower = text.lower()
        
        # Pronouns
        if text_lower in ["he", "she", "it", "they", "him", "her", "them"]:
            return ReferenceType.PRONOUN
        
        # Definite articles
        if text_lower.startswith("the "):
            return ReferenceType.DEFINITE_ARTICLE
        
        # Possessives
        if "'s" in text or text.endswith("'"):
            return ReferenceType.POSSESSIVE
        
        # Titles
        if any(title in text_lower for title in ["mr.", "ms.", "dr.", "judge", "justice"]):
            return ReferenceType.TITLE
        
        # Abbreviations/Acronyms
        if text.isupper() and len(text) <= 10:
            return ReferenceType.ACRONYM
        
        # Role references
        role_terms = ["counsel", "plaintiff", "defendant", "witness", "party"]
        if any(term in text_lower for term in role_terms):
            return ReferenceType.ROLE_REFERENCE
        
        # Check for last name only (for person entities)
        if entity_type in [EntityType.JUDGE, EntityType.ATTORNEY, EntityType.PARTY]:
            words = text.split()
            if len(words) == 1 and words[0][0].isupper():
                return ReferenceType.LAST_NAME
        
        # Default to full name
        return ReferenceType.FULL_NAME
    
    async def resolve_references(
        self, 
        chunk_id: str, 
        chunk_text: str
    ) -> Dict[str, str]:
        """
        Resolve entity references within a chunk.
        
        Args:
            chunk_id: Chunk identifier
            chunk_text: Full text of the chunk
            
        Returns:
            Mapping of reference text to canonical entity IDs
        """
        async with self._lock:
            resolutions = {}
            
            # Get entities from this chunk
            chunk_entities = [
                self.entities[eid] for eid in self.chunk_index.get(chunk_id, set())
            ]
            
            # Sort by position for context
            chunk_entities.sort(
                key=lambda e: min(occ.position.start for occ in e.occurrences if occ.chunk_id == chunk_id)
            )
            
            # Build context for pronoun resolution
            recent_persons = []
            recent_orgs = []
            
            for entity in chunk_entities:
                # Track recent person/org entities for pronoun resolution
                if entity.entity_type in [EntityType.JUDGE, EntityType.ATTORNEY, EntityType.PARTY]:
                    recent_persons.append(entity.id)
                elif entity.entity_type in [EntityType.LAW_FIRM, EntityType.GOVERNMENT_ENTITY]:
                    recent_orgs.append(entity.id)
                
                # Resolve definite article references
                for occ in entity.occurrences:
                    if occ.chunk_id != chunk_id:
                        continue
                    
                    if occ.reference_type == ReferenceType.DEFINITE_ARTICLE:
                        # Look for earlier full reference
                        base_text = occ.text_variant.replace("the ", "", 1)
                        for candidate_id in self.entity_index.get(base_text.lower(), set()):
                            candidate = self.entities[candidate_id]
                            if candidate.entity_type == entity.entity_type:
                                resolutions[occ.text_variant] = candidate_id
                                self.metadata.reference_resolutions += 1
                                break
            
            # Resolve pronouns based on context
            pronoun_patterns = {
                r'\b(he|him|his)\b': recent_persons[-1] if recent_persons else None,
                r'\b(she|her|hers)\b': recent_persons[-1] if recent_persons else None,
                r'\b(it|its)\b': recent_orgs[-1] if recent_orgs else None,
                r'\b(they|them|their)\b': recent_persons[-2:] if len(recent_persons) >= 2 else None
            }
            
            for pattern, entity_ref in pronoun_patterns.items():
                if entity_ref:
                    matches = re.finditer(pattern, chunk_text, re.IGNORECASE)
                    for match in matches:
                        pronoun = match.group()
                        if isinstance(entity_ref, list):
                            # Multiple entities (e.g., "they")
                            resolutions[pronoun] = entity_ref
                        else:
                            resolutions[pronoun] = entity_ref
                        self.metadata.reference_resolutions += 1
            
            return resolutions
    
    async def merge_duplicates(
        self, 
        aggressive: bool = False
    ) -> List[Tuple[str, str]]:
        """
        Merge duplicate entities.
        
        Args:
            aggressive: Use more aggressive merging with lower threshold
            
        Returns:
            List of (merged_from_id, merged_into_id) tuples
        """
        async with self._lock:
            merges = []
            threshold = 0.7 if aggressive else self.similarity_threshold
            
            # Group entities by type for efficient comparison
            for entity_type, entity_ids in self.type_index.items():
                entities = [self.entities[eid] for eid in entity_ids]
                
                # Compare each pair
                for i, entity1 in enumerate(entities):
                    if entity1.resolution_status == ResolutionStatus.MERGED:
                        continue
                    
                    for entity2 in entities[i+1:]:
                        if entity2.resolution_status == ResolutionStatus.MERGED:
                            continue
                        
                        # Calculate similarity
                        similarity, _ = self._calculate_similarity_between_registered(
                            entity1, entity2
                        )
                        
                        if similarity >= threshold:
                            # Merge entity2 into entity1
                            self._perform_merge(entity1, entity2)
                            merges.append((entity2.id, entity1.id))
                            self.metadata.merge_operations += 1
            
            return merges
    
    def _calculate_similarity_between_registered(
        self, 
        entity1: RegisteredEntity, 
        entity2: RegisteredEntity
    ) -> Tuple[float, Dict]:
        """Calculate similarity between two registered entities."""
        scores = []
        features = {"matching": [], "conflicting": []}
        
        # Canonical text similarity
        canonical_sim = SequenceMatcher(
            None, 
            entity1.canonical_text.lower(), 
            entity2.canonical_text.lower()
        ).ratio()
        scores.append(canonical_sim * 0.4)
        
        # Variant overlap
        variant_overlap = len(entity1.all_variants & entity2.all_variants)
        if variant_overlap > 0:
            scores.append(0.3)
            features["matching"].append("variant_overlap")
        
        # Type match
        if entity1.entity_type == entity2.entity_type:
            scores.append(0.2)
            features["matching"].append("same_type")
        
        # Chunk proximity
        chunk_distance = abs(entity1.chunk_span[0] - entity2.chunk_span[0])
        if chunk_distance <= 2:
            scores.append(0.1)
            features["matching"].append("chunk_proximity")
        
        return min(1.0, sum(scores)), features
    
    def _perform_merge(
        self, 
        target: RegisteredEntity, 
        source: RegisteredEntity
    ) -> None:
        """Merge source entity into target."""
        # Merge occurrences
        target.occurrences.extend(source.occurrences)
        
        # Merge variants
        target.all_variants.update(source.all_variants)
        
        # Update chunk span
        target.chunk_span = (
            min(target.chunk_span[0], source.chunk_span[0]),
            max(target.chunk_span[1], source.chunk_span[1])
        )
        
        # Update chunks
        target.first_seen_chunk = (
            source.first_seen_chunk 
            if source.chunk_span[0] < target.chunk_span[0] 
            else target.first_seen_chunk
        )
        target.last_seen_chunk = (
            source.last_seen_chunk 
            if source.chunk_span[1] > target.chunk_span[1] 
            else target.last_seen_chunk
        )
        
        # Update counts
        target.total_occurrences += source.total_occurrences
        target.extraction_methods_used.update(source.extraction_methods_used)
        
        # Merge relationships
        target.relationships.extend(source.relationships)
        
        # Update confidence (weighted average)
        total_weight = target.total_occurrences
        target.aggregate_confidence = (
            (target.aggregate_confidence * (total_weight - source.total_occurrences) + 
             source.aggregate_confidence * source.total_occurrences) / total_weight
        )
        
        # Merge attributes
        self._merge_attributes(target.attributes, source.attributes)
        
        # Track merge
        target.merged_from.append(source.id)
        source.resolution_status = ResolutionStatus.MERGED
        target.resolution_status = ResolutionStatus.RESOLVED
        
        target.updated_at = datetime.utcnow()
    
    async def build_entity_graph(self) -> EntityGraph:
        """
        Build a graph representation of entities and relationships.
        
        Returns:
            EntityGraph with nodes, edges, and metadata
        """
        async with self._lock:
            # Get active entities (not merged)
            active_entities = [
                entity for entity in self.entities.values()
                if entity.resolution_status != ResolutionStatus.MERGED
            ]
            
            # Calculate centrality scores
            centrality_scores = self._calculate_centrality(
                active_entities, 
                list(self.relationships.values())
            )
            
            # Detect communities
            clusters = self._detect_communities(
                active_entities,
                list(self.relationships.values())
            )
            
            # Update metadata
            self.metadata.updated_at = datetime.utcnow()
            processing_time = (datetime.utcnow() - self.start_time).total_seconds() * 1000
            self.metadata.processing_time_ms = processing_time
            
            return EntityGraph(
                nodes=active_entities,
                edges=list(self.relationships.values()),
                clusters=clusters,
                centrality_scores=centrality_scores,
                metadata=self.metadata
            )
    
    def _calculate_centrality(
        self, 
        entities: List[RegisteredEntity], 
        relationships: List[EntityRelationship]
    ) -> Dict[str, float]:
        """Calculate entity centrality scores."""
        centrality = {}
        
        # Count connections for each entity
        connection_counts = Counter()
        for rel in relationships:
            connection_counts[rel.source_entity_id] += 1
            if rel.bidirectional:
                connection_counts[rel.target_entity_id] += 1
        
        # Normalize to 0-1 scale
        max_connections = max(connection_counts.values()) if connection_counts else 1
        
        for entity in entities:
            connections = connection_counts.get(entity.id, 0)
            # Also consider occurrence frequency
            frequency_score = min(1.0, entity.total_occurrences / 100)
            # Combined centrality
            centrality[entity.id] = (
                0.7 * (connections / max_connections) + 
                0.3 * frequency_score
            )
        
        return centrality
    
    def _detect_communities(
        self, 
        entities: List[RegisteredEntity],
        relationships: List[EntityRelationship]
    ) -> List[List[str]]:
        """Detect entity communities/clusters."""
        # Build adjacency list
        adjacency = defaultdict(set)
        for rel in relationships:
            adjacency[rel.source_entity_id].add(rel.target_entity_id)
            if rel.bidirectional:
                adjacency[rel.target_entity_id].add(rel.source_entity_id)
        
        # Find connected components
        visited = set()
        communities = []
        
        for entity in entities:
            if entity.id not in visited:
                # BFS to find connected component
                component = []
                queue = [entity.id]
                
                while queue:
                    current = queue.pop(0)
                    if current in visited:
                        continue
                    
                    visited.add(current)
                    component.append(current)
                    
                    # Add neighbors
                    for neighbor in adjacency.get(current, set()):
                        if neighbor not in visited:
                            queue.append(neighbor)
                
                if len(component) > 1:  # Only keep multi-entity communities
                    communities.append(component)
        
        return communities
    
    async def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        confidence: float = 0.8,
        evidence: Optional[List[Dict]] = None,
        chunk_ids: Optional[List[str]] = None,
        bidirectional: bool = False
    ) -> str:
        """
        Add a relationship between entities.
        
        Args:
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship
            confidence: Confidence score
            evidence: Supporting evidence
            chunk_ids: Chunks where relationship was observed
            bidirectional: Whether relationship is bidirectional
            
        Returns:
            Relationship ID
        """
        async with self._lock:
            # Verify entities exist
            if source_entity_id not in self.entities:
                raise ValueError(f"Source entity {source_entity_id} not found")
            if target_entity_id not in self.entities:
                raise ValueError(f"Target entity {target_entity_id} not found")
            
            # Create relationship
            relationship = EntityRelationship(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type,
                confidence=confidence,
                evidence=evidence or [],
                chunk_ids=chunk_ids or [],
                bidirectional=bidirectional
            )
            
            # Store relationship
            self.relationships[relationship.id] = relationship
            
            # Update entity relationship lists
            self.entities[source_entity_id].relationships.append(relationship.id)
            self.entities[target_entity_id].relationships.append(relationship.id)
            
            # Update metadata
            self.metadata.total_relationships += 1
            
            return relationship.id
    
    def get_entity_context(
        self, 
        entity_id: str,
        context_window: int = 500
    ) -> Dict[str, Any]:
        """
        Get full context for an entity across all occurrences.
        
        Args:
            entity_id: Entity ID
            context_window: Characters of context to include
            
        Returns:
            Dictionary with entity details and context
        """
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")
        
        entity = self.entities[entity_id]
        
        # Gather context from all occurrences
        contexts = []
        for occ in entity.occurrences:
            contexts.append({
                "chunk_id": occ.chunk_id,
                "text": occ.text_variant,
                "position": {
                    "chunk": occ.position.dict(),
                    "global": occ.global_position.dict()
                },
                "context": f"{occ.context_before} [{occ.text_variant}] {occ.context_after}"
            })
        
        # Get related entities
        related = []
        for rel_id in entity.relationships:
            rel = self.relationships.get(rel_id)
            if rel:
                other_id = (
                    rel.target_entity_id 
                    if rel.source_entity_id == entity_id 
                    else rel.source_entity_id
                )
                other = self.entities.get(other_id)
                if other:
                    related.append({
                        "entity": other.canonical_text,
                        "type": other.entity_type.value,
                        "relationship": rel.relationship_type
                    })
        
        return {
            "entity_id": entity_id,
            "canonical_text": entity.canonical_text,
            "type": entity.entity_type.value,
            "subtype": entity.entity_subtype,
            "variants": list(entity.all_variants),
            "total_occurrences": entity.total_occurrences,
            "confidence": entity.aggregate_confidence,
            "chunk_span": entity.chunk_span,
            "attributes": entity.attributes.dict(),
            "occurrences": contexts,
            "relationships": related,
            "resolution_status": entity.resolution_status.value
        }
    
    async def export_registry(
        self,
        include_merged: bool = False,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export the registry in a structured format.
        
        Args:
            include_merged: Include merged entities
            format: Export format (json, pickle)
            
        Returns:
            Exported registry data
        """
        async with self._lock:
            # Filter entities
            entities_to_export = [
                entity.dict() for entity in self.entities.values()
                if include_merged or entity.resolution_status != ResolutionStatus.MERGED
            ]
            
            # Prepare export data
            export_data = {
                "metadata": self.metadata.dict(),
                "entities": entities_to_export,
                "relationships": [rel.dict() for rel in self.relationships.values()],
                "statistics": {
                    "total_entities": len(entities_to_export),
                    "total_relationships": len(self.relationships),
                    "merge_operations": self.metadata.merge_operations,
                    "reference_resolutions": self.metadata.reference_resolutions,
                    "entity_types": dict(self.metadata.entity_type_distribution)
                }
            }
            
            if format == "pickle":
                return pickle.dumps(export_data)
            else:
                return export_data
    
    async def save_snapshot(self, checkpoint_chunk_id: Optional[str] = None) -> str:
        """
        Save a snapshot of the registry for persistence.
        
        Args:
            checkpoint_chunk_id: Last processed chunk for resumption
            
        Returns:
            Snapshot ID
        """
        snapshot = RegistrySnapshot(
            entities=self.entities,
            relationships=self.relationships,
            metadata=self.metadata,
            checkpoint_chunk_id=checkpoint_chunk_id
        )
        
        if self.enable_caching:
            # Save to cache directory
            snapshot_file = self.cache_dir / f"snapshot_{snapshot.snapshot_id}.pkl"
            
            # Compress snapshot
            snapshot_data = pickle.dumps(snapshot.dict())
            compressed_data = zlib.compress(snapshot_data)
            
            with open(snapshot_file, 'wb') as f:
                f.write(compressed_data)
            
            self.logger.info(f"Saved snapshot {snapshot.snapshot_id} to {snapshot_file}")
        
        return snapshot.snapshot_id
    
    async def load_snapshot(self, snapshot_id: str) -> bool:
        """
        Load a snapshot from persistence.
        
        Args:
            snapshot_id: Snapshot ID to load
            
        Returns:
            True if loaded successfully
        """
        if not self.enable_caching:
            return False
        
        snapshot_file = self.cache_dir / f"snapshot_{snapshot_id}.pkl"
        
        if not snapshot_file.exists():
            self.logger.error(f"Snapshot {snapshot_id} not found")
            return False
        
        try:
            with open(snapshot_file, 'rb') as f:
                compressed_data = f.read()
            
            snapshot_data = zlib.decompress(compressed_data)
            snapshot_dict = pickle.loads(snapshot_data)
            
            # Restore registry state
            snapshot = RegistrySnapshot(**snapshot_dict)
            self.entities = snapshot.entities
            self.relationships = snapshot.relationships
            self.metadata = snapshot.metadata
            
            # Rebuild indices
            self._rebuild_indices()
            
            self.logger.info(f"Loaded snapshot {snapshot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load snapshot: {e}")
            return False
    
    def _rebuild_indices(self):
        """Rebuild indices after loading snapshot."""
        self.entity_index.clear()
        self.type_index.clear()
        self.chunk_index.clear()
        
        for entity_id, entity in self.entities.items():
            # Text index
            for variant in entity.all_variants:
                self.entity_index[variant.lower()].add(entity_id)
            
            # Type index
            self.type_index[entity.entity_type].add(entity_id)
            
            # Chunk index
            for occ in entity.occurrences:
                self.chunk_index[occ.chunk_id].add(entity_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        active_entities = [
            e for e in self.entities.values() 
            if e.resolution_status != ResolutionStatus.MERGED
        ]
        
        return {
            "total_entities": len(active_entities),
            "total_occurrences": sum(e.total_occurrences for e in active_entities),
            "total_relationships": len(self.relationships),
            "chunks_processed": self.metadata.processed_chunks,
            "chunks_total": self.metadata.total_chunks,
            "merge_operations": self.metadata.merge_operations,
            "reference_resolutions": self.metadata.reference_resolutions,
            "entity_type_distribution": dict(self.metadata.entity_type_distribution),
            "average_confidence": (
                sum(e.aggregate_confidence for e in active_entities) / len(active_entities)
                if active_entities else 0
            ),
            "processing_time_ms": self.metadata.processing_time_ms
        }