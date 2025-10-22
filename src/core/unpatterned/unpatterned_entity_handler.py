"""
Unpatterned Entity Handler for CALES Entity Extraction Service

This module handles entity extraction for entity types that don't have regex patterns,
using advanced NLP techniques including zero-shot classification, NER, and contextual validation.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import numpy as np
import torch
from pathlib import Path
import json
import time

# NLP libraries
import spacy
from spacy.language import Language
from transformers import pipeline, Pipeline, AutoTokenizer, AutoModelForSequenceClassification

# Internal imports
from ..model_management.dynamic_model_loader import DynamicModelLoader, LoadedModel
from .entity_strategies import (
    ZeroShotClassificationStrategy,
    NamedEntityRecognitionStrategy,
    NounPhraseExtractionStrategy,
    SemanticSimilarityStrategy
)
from .entity_candidates import EntityCandidateGenerator, EntityCandidate

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing modes for unpatterned entity extraction"""
    FAST = "fast"           # Quick processing with basic strategies
    COMPREHENSIVE = "comprehensive"  # Full processing with all strategies
    ADAPTIVE = "adaptive"   # Adaptive based on content and confidence


@dataclass
class UnpatternedEntity:
    """Represents an extracted unpatterned entity"""
    text: str
    entity_type: str
    start_position: int
    end_position: int
    confidence_score: float
    context: str
    extraction_method: str
    metadata: Dict[str, Any]
    validation_score: float = 0.0


class UnpatternedEntityHandler:
    """
    Handles extraction of entities without regex patterns using multiple NLP strategies.
    
    This handler processes the 150+ entity types from CALES that don't have predefined
    patterns, using zero-shot classification, NER, noun phrase extraction, and
    contextual validation techniques.
    """
    
    def __init__(self, 
                 cales_config_path: str = "/srv/luris/be/entity-extraction-service/config/cales_config.yaml",
                 model_loader: Optional[DynamicModelLoader] = None,
                 cache_size: int = 1000,
                 confidence_threshold: float = 0.7):
        """
        Initialize the UnpatternedEntityHandler.
        
        Args:
            cales_config_path: Path to CALES configuration file
            model_loader: Optional pre-initialized model loader
            cache_size: Size of entity candidate cache
            confidence_threshold: Minimum confidence threshold for entities
        """
        self.cales_config_path = cales_config_path
        self.confidence_threshold = confidence_threshold
        self.cache_size = cache_size
        
        # Initialize model loader
        self.model_loader = model_loader or DynamicModelLoader()
        
        # Load CALES configuration
        self.cales_config = self._load_cales_config()
        
        # Extract unpatterned entity types
        self.unpatterned_types = self._extract_unpatterned_types()
        
        # Initialize models (lazy loading)
        self.deberta_model = None
        self.deberta_tokenizer = None
        self.blackstone_model = None
        self.spacy_model = None
        self.zero_shot_classifier = None
        
        # Initialize strategies
        self._initialize_strategies()
        
        # Initialize candidate generator
        self.candidate_generator = EntityCandidateGenerator(
            entity_types=self.unpatterned_types,
            cache_size=cache_size
        )
        
        # Performance tracking
        self.extraction_stats = {
            "total_processed": 0,
            "entities_found": 0,
            "processing_time_ms": 0,
            "strategy_usage": {
                "zero_shot": 0,
                "ner": 0,
                "noun_phrase": 0,
                "semantic": 0
            }
        }
        
        logger.info(f"UnpatternedEntityHandler initialized with {len(self.unpatterned_types)} entity types")
    
    def _load_cales_config(self) -> Dict[str, Any]:
        """Load CALES configuration from YAML file"""
        try:
            import yaml
            with open(self.cales_config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load CALES config: {e}")
            raise
    
    def _extract_unpatterned_types(self) -> List[Dict[str, Any]]:
        """
        Extract entity types that don't have regex patterns.
        
        Returns:
            List of unpatterned entity type configurations
        """
        unpatterned = []
        entity_types = self.cales_config.get('entity_types', {})
        
        for category, types in entity_types.items():
            for entity_config in types:
                # Check if entity type has patterns (indicating it's handled elsewhere)
                if not self._has_patterns(entity_config):
                    entity_config['category'] = category
                    unpatterned.append(entity_config)
        
        logger.info(f"Found {len(unpatterned)} unpatterned entity types")
        return unpatterned
    
    def _has_patterns(self, entity_config: Dict[str, Any]) -> bool:
        """
        Check if an entity type has regex patterns defined.
        
        Args:
            entity_config: Entity configuration dictionary
            
        Returns:
            True if entity has patterns, False otherwise
        """
        # Simple heuristic: if entity type has very specific examples
        # or keywords that suggest pattern-based extraction
        examples = entity_config.get('examples', [])
        keywords = entity_config.get('context_keywords', [])
        
        # Check for pattern-like examples (dates, numbers, specific formats)
        pattern_indicators = [
            r'\d', r'No\.', r'§', r'U\.S\.C\.', r'CFR', r'F\.\d+d',
            r'\$', r'%', r'@', r'\.com', r'\.org', r'\.net'
        ]
        
        import re
        for example in examples:
            for indicator in pattern_indicators:
                if re.search(indicator, str(example)):
                    return True
        
        # Check for very specific keywords that suggest pattern matching
        specific_keywords = [
            'number', 'no.', 'id', 'code', 'section', '§', 'cfr', 'usc'
        ]
        
        for keyword in keywords:
            if any(specific in keyword.lower() for specific in specific_keywords):
                return True
        
        return False
    
    def _initialize_strategies(self):
        """Initialize extraction strategies"""
        self.zero_shot_strategy = ZeroShotClassificationStrategy()
        self.ner_strategy = NamedEntityRecognitionStrategy()
        self.noun_phrase_strategy = NounPhraseExtractionStrategy()
        self.semantic_strategy = SemanticSimilarityStrategy()
        
        logger.info("Initialized extraction strategies")
    
    async def _ensure_models_loaded(self):
        """Ensure required models are loaded (lazy initialization)"""
        if self.deberta_model is None:
            try:
                # Load DeBERTa for zero-shot classification
                self.deberta_model, self.deberta_tokenizer, _ = self.model_loader.load_model(
                    "microsoft/deberta-v3-base"
                )
                logger.info("Loaded DeBERTa model for zero-shot classification")
            except Exception as e:
                logger.warning(f"Failed to load DeBERTa model: {e}")
        
        if self.blackstone_model is None:
            try:
                # Load Blackstone for legal NER
                self.blackstone_model, _, _ = self.model_loader.load_model(
                    "iclr2020/blackstone-nlp"
                )
                logger.info("Loaded Blackstone model for legal NER")
            except Exception as e:
                logger.warning(f"Failed to load Blackstone model: {e}")
        
        if self.spacy_model is None:
            try:
                # Load SpaCy model for general NLP
                self.spacy_model, _, _ = self.model_loader.load_model(
                    "en_core_web_lg"
                )
                logger.info("Loaded SpaCy model for general NLP")
            except Exception as e:
                logger.warning(f"Failed to load SpaCy model: {e}")
        
        if self.zero_shot_classifier is None:
            try:
                # Initialize zero-shot classifier
                self.zero_shot_classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli"
                )
                logger.info("Initialized zero-shot classifier")
            except Exception as e:
                logger.warning(f"Failed to initialize zero-shot classifier: {e}")
    
    async def extract_entities(self, 
                             text: str,
                             mode: ProcessingMode = ProcessingMode.ADAPTIVE,
                             target_types: Optional[List[str]] = None) -> List[UnpatternedEntity]:
        """
        Extract unpatterned entities from text.
        
        Args:
            text: Input text to process
            mode: Processing mode (fast, comprehensive, adaptive)
            target_types: Specific entity types to target (optional)
            
        Returns:
            List of extracted unpatterned entities
        """
        start_time = time.time()
        
        try:
            # Ensure models are loaded
            await self._ensure_models_loaded()
            
            # Filter entity types if specified
            entity_types = self._filter_target_types(target_types)
            
            # Generate entity candidates
            candidates = await self.candidate_generator.generate_candidates(
                text, entity_types, mode
            )
            
            # Apply extraction strategies based on mode
            extracted_entities = await self._apply_strategies(
                text, candidates, entity_types, mode
            )
            
            # Post-process and validate entities
            validated_entities = self._validate_and_rank_entities(
                extracted_entities, text
            )
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self._update_stats(len(validated_entities), processing_time)
            
            logger.info(f"Extracted {len(validated_entities)} unpatterned entities in {processing_time:.2f}ms")
            return validated_entities
            
        except Exception as e:
            logger.error(f"Error in unpatterned entity extraction: {e}")
            return []
    
    def _filter_target_types(self, target_types: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Filter unpatterned types based on target types"""
        if not target_types:
            return self.unpatterned_types
        
        return [
            entity_type for entity_type in self.unpatterned_types
            if entity_type['type'] in target_types
        ]
    
    async def _apply_strategies(self,
                               text: str,
                               candidates: List[EntityCandidate],
                               entity_types: List[Dict[str, Any]],
                               mode: ProcessingMode) -> List[UnpatternedEntity]:
        """
        Apply extraction strategies based on processing mode.
        
        Args:
            text: Input text
            candidates: Pre-generated candidates
            entity_types: Entity type configurations
            mode: Processing mode
            
        Returns:
            List of extracted entities
        """
        extracted_entities = []
        
        # Determine strategies to use based on mode
        strategies_to_use = self._select_strategies(mode, len(candidates))
        
        # Apply zero-shot classification
        if 'zero_shot' in strategies_to_use:
            zero_shot_entities = await self._apply_zero_shot_classification(
                text, entity_types, candidates
            )
            extracted_entities.extend(zero_shot_entities)
            self.extraction_stats["strategy_usage"]["zero_shot"] += len(zero_shot_entities)
        
        # Apply NER strategies
        if 'ner' in strategies_to_use:
            ner_entities = await self._apply_ner_strategies(text, entity_types)
            extracted_entities.extend(ner_entities)
            self.extraction_stats["strategy_usage"]["ner"] += len(ner_entities)
        
        # Apply noun phrase extraction
        if 'noun_phrase' in strategies_to_use:
            np_entities = await self._apply_noun_phrase_extraction(text, entity_types)
            extracted_entities.extend(np_entities)
            self.extraction_stats["strategy_usage"]["noun_phrase"] += len(np_entities)
        
        # Apply semantic similarity
        if 'semantic' in strategies_to_use:
            semantic_entities = await self._apply_semantic_similarity(
                text, entity_types, candidates
            )
            extracted_entities.extend(semantic_entities)
            self.extraction_stats["strategy_usage"]["semantic"] += len(semantic_entities)
        
        return extracted_entities
    
    def _select_strategies(self, mode: ProcessingMode, num_candidates: int) -> List[str]:
        """Select strategies based on processing mode and content characteristics"""
        if mode == ProcessingMode.FAST:
            return ['zero_shot', 'ner']
        elif mode == ProcessingMode.COMPREHENSIVE:
            return ['zero_shot', 'ner', 'noun_phrase', 'semantic']
        else:  # ADAPTIVE
            strategies = ['zero_shot', 'ner']
            
            # Add more strategies for complex content
            if num_candidates > 20:
                strategies.append('noun_phrase')
            if num_candidates > 50:
                strategies.append('semantic')
            
            return strategies
    
    async def _apply_zero_shot_classification(self,
                                            text: str,
                                            entity_types: List[Dict[str, Any]],
                                            candidates: List[EntityCandidate]) -> List[UnpatternedEntity]:
        """Apply zero-shot classification strategy"""
        if not self.zero_shot_classifier:
            return []
        
        entities = []
        
        try:
            # Group candidates by similarity to reduce redundant classifications
            candidate_groups = self._group_similar_candidates(candidates)
            
            for group in candidate_groups:
                # Create labels from entity types
                labels = [et['type'] for et in entity_types]
                
                # Get representative candidate from group
                candidate = group[0]
                
                # Extract context window around candidate
                context = self._extract_context_window(text, candidate.start, candidate.end, window_size=100)
                
                # Perform zero-shot classification
                result = self.zero_shot_classifier(context, labels)
                
                # Process results
                for i, (label, score) in enumerate(zip(result['labels'], result['scores'])):
                    if score >= self.confidence_threshold:
                        # Find matching entity type config
                        entity_type_config = next(
                            (et for et in entity_types if et['type'] == label), None
                        )
                        
                        if entity_type_config:
                            entity = UnpatternedEntity(
                                text=candidate.text,
                                entity_type=label,
                                start_position=candidate.start,
                                end_position=candidate.end,
                                confidence_score=score,
                                context=context,
                                extraction_method="zero_shot_classification",
                                metadata={
                                    "candidate_score": candidate.confidence,
                                    "classification_rank": i,
                                    "entity_config": entity_type_config
                                }
                            )
                            entities.append(entity)
                            
                            # Apply to all candidates in group with adjusted confidence
                            for other_candidate in group[1:]:
                                if other_candidate != candidate:
                                    adjusted_score = score * 0.9  # Slight penalty for non-representative
                                    if adjusted_score >= self.confidence_threshold:
                                        other_context = self._extract_context_window(
                                            text, other_candidate.start, other_candidate.end, window_size=100
                                        )
                                        other_entity = UnpatternedEntity(
                                            text=other_candidate.text,
                                            entity_type=label,
                                            start_position=other_candidate.start,
                                            end_position=other_candidate.end,
                                            confidence_score=adjusted_score,
                                            context=other_context,
                                            extraction_method="zero_shot_classification_grouped",
                                            metadata={
                                                "candidate_score": other_candidate.confidence,
                                                "classification_rank": i,
                                                "entity_config": entity_type_config,
                                                "grouped_with": candidate.text
                                            }
                                        )
                                        entities.append(other_entity)
                        
                        # Only take top prediction to avoid noise
                        break
                
        except Exception as e:
            logger.error(f"Error in zero-shot classification: {e}")
        
        return entities
    
    async def _apply_ner_strategies(self,
                                   text: str,
                                   entity_types: List[Dict[str, Any]]) -> List[UnpatternedEntity]:
        """Apply NER strategies using Blackstone and SpaCy"""
        entities = []
        
        try:
            # Apply Blackstone legal NER
            if self.blackstone_model:
                blackstone_entities = await self._apply_blackstone_ner(text, entity_types)
                entities.extend(blackstone_entities)
            
            # Apply SpaCy general NER
            if self.spacy_model:
                spacy_entities = await self._apply_spacy_ner(text, entity_types)
                entities.extend(spacy_entities)
                
        except Exception as e:
            logger.error(f"Error in NER strategies: {e}")
        
        return entities
    
    async def _apply_blackstone_ner(self,
                                   text: str,
                                   entity_types: List[Dict[str, Any]]) -> List[UnpatternedEntity]:
        """Apply Blackstone legal NER"""
        entities = []
        
        try:
            # Process with Blackstone
            doc = self.blackstone_model(text)
            
            # Map Blackstone entities to CALES types
            for ent in doc.ents:
                mapped_type = self._map_blackstone_to_cales(ent.label_, entity_types)
                if mapped_type:
                    context = self._extract_context_window(text, ent.start_char, ent.end_char)
                    
                    entity = UnpatternedEntity(
                        text=ent.text,
                        entity_type=mapped_type['type'],
                        start_position=ent.start_char,
                        end_position=ent.end_char,
                        confidence_score=0.8,  # Default confidence for NER
                        context=context,
                        extraction_method="blackstone_ner",
                        metadata={
                            "blackstone_label": ent.label_,
                            "entity_config": mapped_type
                        }
                    )
                    entities.append(entity)
                    
        except Exception as e:
            logger.error(f"Error in Blackstone NER: {e}")
        
        return entities
    
    async def _apply_spacy_ner(self,
                              text: str,
                              entity_types: List[Dict[str, Any]]) -> List[UnpatternedEntity]:
        """Apply SpaCy general NER"""
        entities = []
        
        try:
            # Process with SpaCy
            doc = self.spacy_model(text)
            
            # Map SpaCy entities to CALES types
            for ent in doc.ents:
                mapped_type = self._map_spacy_to_cales(ent.label_, entity_types)
                if mapped_type:
                    context = self._extract_context_window(text, ent.start_char, ent.end_char)
                    
                    entity = UnpatternedEntity(
                        text=ent.text,
                        entity_type=mapped_type['type'],
                        start_position=ent.start_char,
                        end_position=ent.end_char,
                        confidence_score=0.7,  # Default confidence for general NER
                        context=context,
                        extraction_method="spacy_ner",
                        metadata={
                            "spacy_label": ent.label_,
                            "entity_config": mapped_type
                        }
                    )
                    entities.append(entity)
                    
        except Exception as e:
            logger.error(f"Error in SpaCy NER: {e}")
        
        return entities
    
    async def _apply_noun_phrase_extraction(self,
                                           text: str,
                                           entity_types: List[Dict[str, Any]]) -> List[UnpatternedEntity]:
        """Apply noun phrase extraction strategy"""
        entities = []
        
        try:
            if not self.spacy_model:
                return entities
            
            doc = self.spacy_model(text)
            
            # Extract noun phrases
            for chunk in doc.noun_chunks:
                # Filter out very short or common phrases
                if len(chunk.text.split()) < 2 or len(chunk.text) < 4:
                    continue
                
                # Check if chunk matches any entity type context
                matching_types = self._match_noun_phrase_to_types(chunk.text, entity_types)
                
                for entity_type in matching_types:
                    context = self._extract_context_window(text, chunk.start_char, chunk.end_char)
                    
                    entity = UnpatternedEntity(
                        text=chunk.text,
                        entity_type=entity_type['type'],
                        start_position=chunk.start_char,
                        end_position=chunk.end_char,
                        confidence_score=0.6,  # Lower confidence for noun phrases
                        context=context,
                        extraction_method="noun_phrase_extraction",
                        metadata={
                            "pos_tags": [token.pos_ for token in chunk],
                            "entity_config": entity_type
                        }
                    )
                    entities.append(entity)
                    
        except Exception as e:
            logger.error(f"Error in noun phrase extraction: {e}")
        
        return entities
    
    async def _apply_semantic_similarity(self,
                                        text: str,
                                        entity_types: List[Dict[str, Any]],
                                        candidates: List[EntityCandidate]) -> List[UnpatternedEntity]:
        """Apply semantic similarity strategy"""
        entities = []
        
        try:
            # This would use sentence transformers or similar for semantic matching
            # For now, implement a simplified version using keyword matching
            
            for candidate in candidates:
                best_match = None
                best_score = 0.0
                
                for entity_type in entity_types:
                    score = self._calculate_semantic_similarity(
                        candidate.text,
                        entity_type.get('examples', []),
                        entity_type.get('context_keywords', [])
                    )
                    
                    if score > best_score and score >= self.confidence_threshold:
                        best_score = score
                        best_match = entity_type
                
                if best_match:
                    context = self._extract_context_window(text, candidate.start, candidate.end)
                    
                    entity = UnpatternedEntity(
                        text=candidate.text,
                        entity_type=best_match['type'],
                        start_position=candidate.start,
                        end_position=candidate.end,
                        confidence_score=best_score,
                        context=context,
                        extraction_method="semantic_similarity",
                        metadata={
                            "candidate_score": candidate.confidence,
                            "entity_config": best_match
                        }
                    )
                    entities.append(entity)
                    
        except Exception as e:
            logger.error(f"Error in semantic similarity: {e}")
        
        return entities
    
    def _group_similar_candidates(self, candidates: List[EntityCandidate]) -> List[List[EntityCandidate]]:
        """Group similar candidates to reduce redundant processing"""
        groups = []
        used = set()
        
        for i, candidate in enumerate(candidates):
            if i in used:
                continue
            
            group = [candidate]
            used.add(i)
            
            for j, other_candidate in enumerate(candidates[i+1:], i+1):
                if j in used:
                    continue
                
                # Simple similarity check based on text
                if self._are_candidates_similar(candidate, other_candidate):
                    group.append(other_candidate)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    def _are_candidates_similar(self, candidate1: EntityCandidate, candidate2: EntityCandidate) -> bool:
        """Check if two candidates are similar enough to group together"""
        # Simple similarity based on text overlap and length
        text1 = candidate1.text.lower().strip()
        text2 = candidate2.text.lower().strip()
        
        # Exact match
        if text1 == text2:
            return True
        
        # High overlap
        if len(text1) > 0 and len(text2) > 0:
            overlap = len(set(text1.split()) & set(text2.split()))
            total = len(set(text1.split()) | set(text2.split()))
            if total > 0 and overlap / total > 0.7:
                return True
        
        return False
    
    def _extract_context_window(self, text: str, start: int, end: int, window_size: int = 100) -> str:
        """Extract context window around entity"""
        context_start = max(0, start - window_size)
        context_end = min(len(text), end + window_size)
        return text[context_start:context_end].strip()
    
    def _map_blackstone_to_cales(self, blackstone_label: str, entity_types: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Map Blackstone NER labels to CALES entity types"""
        mapping = {
            "PERSON": ["JUDGE", "ATTORNEY", "WITNESS", "PLAINTIFF", "DEFENDANT"],
            "ORG": ["COURT", "LAW_FIRM", "CORPORATION", "LLC"],
            "COURT": ["COURT"],
            "JUDGE": ["JUDGE"],
            "LEGISLATION": ["STATUTE", "REGULATION", "CONSTITUTIONAL_PROVISION"],
            "CASE_NAME": ["CASE"],
            "CITATION": ["CITATION"]
        }
        
        possible_types = mapping.get(blackstone_label, [])
        
        # Return first matching type
        for entity_type in entity_types:
            if entity_type['type'] in possible_types:
                return entity_type
        
        return None
    
    def _map_spacy_to_cales(self, spacy_label: str, entity_types: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Map SpaCy NER labels to CALES entity types"""
        mapping = {
            "PERSON": ["JUDGE", "ATTORNEY", "WITNESS", "PLAINTIFF", "DEFENDANT", "PARTY"],
            "ORG": ["COURT", "LAW_FIRM", "CORPORATION", "LLC", "AGENCY"],
            "GPE": ["JURISDICTION", "STATE", "CITY", "COUNTRY"],
            "MONEY": ["MONEY", "CONTRACT_AMOUNT"],
            "DATE": ["DATE", "CONTRACT_DATE"],
            "PERCENT": ["PERCENTAGE", "INTEREST_RATE"],
            "LAW": ["STATUTE", "REGULATION"]
        }
        
        possible_types = mapping.get(spacy_label, [])
        
        # Return first matching type
        for entity_type in entity_types:
            if entity_type['type'] in possible_types:
                return entity_type
        
        return None
    
    def _match_noun_phrase_to_types(self, phrase: str, entity_types: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match noun phrase to potential entity types based on keywords"""
        matches = []
        phrase_lower = phrase.lower()
        
        for entity_type in entity_types:
            keywords = entity_type.get('context_keywords', [])
            
            # Check if any keyword appears in the phrase
            for keyword in keywords:
                if keyword.lower() in phrase_lower:
                    matches.append(entity_type)
                    break
        
        return matches
    
    def _calculate_semantic_similarity(self, 
                                     candidate_text: str,
                                     examples: List[str],
                                     keywords: List[str]) -> float:
        """Calculate semantic similarity score (simplified version)"""
        candidate_lower = candidate_text.lower()
        candidate_words = set(candidate_lower.split())
        
        total_score = 0.0
        num_comparisons = 0
        
        # Compare with examples
        for example in examples:
            example_words = set(example.lower().split())
            if example_words and candidate_words:
                overlap = len(candidate_words & example_words)
                total = len(candidate_words | example_words)
                if total > 0:
                    total_score += overlap / total
                    num_comparisons += 1
        
        # Compare with keywords
        for keyword in keywords:
            keyword_words = set(keyword.lower().split())
            if keyword_words and candidate_words:
                overlap = len(candidate_words & keyword_words)
                total = len(candidate_words | keyword_words)
                if total > 0:
                    total_score += overlap / total
                    num_comparisons += 1
        
        return total_score / num_comparisons if num_comparisons > 0 else 0.0
    
    def _validate_and_rank_entities(self, 
                                   entities: List[UnpatternedEntity],
                                   text: str) -> List[UnpatternedEntity]:
        """Validate and rank extracted entities"""
        validated_entities = []
        
        for entity in entities:
            # Basic validation
            if len(entity.text.strip()) < 2:
                continue
            
            # Context validation
            validation_score = self._validate_entity_context(entity, text)
            entity.validation_score = validation_score
            
            # Apply combined confidence threshold
            combined_score = (entity.confidence_score + validation_score) / 2
            
            if combined_score >= self.confidence_threshold:
                validated_entities.append(entity)
        
        # Remove duplicates and overlaps
        validated_entities = self._remove_duplicates_and_overlaps(validated_entities)
        
        # Sort by confidence
        validated_entities.sort(key=lambda e: e.confidence_score, reverse=True)
        
        return validated_entities
    
    def _validate_entity_context(self, entity: UnpatternedEntity, text: str) -> float:
        """Validate entity based on context"""
        # Simple context validation based on surrounding words
        context_words = entity.context.lower().split()
        
        # Check for legal context indicators
        legal_indicators = [
            'court', 'judge', 'attorney', 'lawyer', 'case', 'legal', 'law', 
            'plaintiff', 'defendant', 'witness', 'testimony', 'contract',
            'agreement', 'statute', 'regulation', 'section', 'article'
        ]
        
        legal_score = sum(1 for word in context_words if word in legal_indicators)
        max_score = min(5, len(context_words) // 10)  # Normalize
        
        return min(1.0, legal_score / max_score) if max_score > 0 else 0.5
    
    def _remove_duplicates_and_overlaps(self, entities: List[UnpatternedEntity]) -> List[UnpatternedEntity]:
        """Remove duplicate and overlapping entities"""
        if not entities:
            return entities
        
        # Sort by position
        entities.sort(key=lambda e: (e.start_position, e.end_position))
        
        filtered = []
        
        for entity in entities:
            # Check for overlaps with existing entities
            overlaps = False
            
            for existing in filtered:
                if (entity.start_position < existing.end_position and 
                    entity.end_position > existing.start_position):
                    # Overlap detected - keep the one with higher confidence
                    if entity.confidence_score > existing.confidence_score:
                        filtered.remove(existing)
                        break
                    else:
                        overlaps = True
                        break
            
            if not overlaps:
                filtered.append(entity)
        
        return filtered
    
    def _update_stats(self, num_entities: int, processing_time: float):
        """Update extraction statistics"""
        self.extraction_stats["total_processed"] += 1
        self.extraction_stats["entities_found"] += num_entities
        self.extraction_stats["processing_time_ms"] += processing_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        stats = self.extraction_stats.copy()
        if stats["total_processed"] > 0:
            stats["avg_entities_per_doc"] = stats["entities_found"] / stats["total_processed"]
            stats["avg_processing_time_ms"] = stats["processing_time_ms"] / stats["total_processed"]
        else:
            stats["avg_entities_per_doc"] = 0
            stats["avg_processing_time_ms"] = 0
        
        stats["unpatterned_types_count"] = len(self.unpatterned_types)
        stats["model_cache_stats"] = self.model_loader.cache.get_stats()
        
        return stats
    
    def clear_cache(self):
        """Clear model cache and reset statistics"""
        self.model_loader.clear_cache()
        self.candidate_generator.clear_cache()
        
        # Reset models to force reload
        self.deberta_model = None
        self.blackstone_model = None
        self.spacy_model = None
        self.zero_shot_classifier = None
        
        logger.info("Cleared caches and reset models")


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_handler():
        handler = UnpatternedEntityHandler()
        
        test_text = """
        The plaintiff, John Smith, filed a complaint against ABC Corporation
        in the Superior Court of California. The case involves a breach of
        contract claim regarding a software licensing agreement worth $500,000.
        Attorney Jane Doe represents the plaintiff, while the defendant is
        represented by the law firm of Wilson & Associates LLP.
        """
        
        entities = await handler.extract_entities(
            test_text, 
            mode=ProcessingMode.COMPREHENSIVE
        )
        
        print(f"Extracted {len(entities)} entities:")
        for entity in entities:
            print(f"  {entity.text} -> {entity.entity_type} (confidence: {entity.confidence_score:.2f})")
        
        print(f"Statistics: {handler.get_stats()}")
    
    asyncio.run(test_handler())