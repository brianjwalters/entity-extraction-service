"""
Entity Extraction Strategies for Unpatterned Entities

This module defines different strategies for extracting entities that don't have
regex patterns, including zero-shot classification, NER, noun phrase extraction,
and semantic similarity approaches.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import numpy as np
import torch
import re
from collections import Counter, defaultdict

# NLP libraries
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span
from transformers import pipeline, Pipeline, AutoTokenizer, AutoModel
import sentence_transformers
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from an extraction strategy"""
    text: str
    entity_type: str
    start_position: int
    end_position: int
    confidence_score: float
    strategy_name: str
    metadata: Dict[str, Any]


class ExtractionStrategy(ABC):
    """Abstract base class for entity extraction strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.extraction_count = 0
        self.total_processing_time = 0.0
    
    @abstractmethod
    async def extract(self, text: str, entity_types: List[Dict[str, Any]], **kwargs) -> List[ExtractionResult]:
        """Extract entities using this strategy"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            "name": self.name,
            "extraction_count": self.extraction_count,
            "total_processing_time": self.total_processing_time,
            "avg_processing_time": (
                self.total_processing_time / self.extraction_count 
                if self.extraction_count > 0 else 0
            )
        }


class ZeroShotClassificationStrategy(ExtractionStrategy):
    """
    Zero-shot classification strategy using pre-trained models
    to classify text segments without task-specific training.
    """
    
    def __init__(self):
        super().__init__("zero_shot_classification")
        self.classifier = None
        self.model_name = "facebook/bart-large-mnli"
        self.min_confidence = 0.7
        self.max_sequence_length = 512
    
    async def _ensure_model_loaded(self):
        """Lazy load the zero-shot classifier"""
        if self.classifier is None:
            try:
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model=self.model_name,
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info(f"Loaded zero-shot classifier: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load zero-shot classifier: {e}")
                raise
    
    async def extract(self, text: str, entity_types: List[Dict[str, Any]], **kwargs) -> List[ExtractionResult]:
        """
        Extract entities using zero-shot classification.
        
        Args:
            text: Input text
            entity_types: List of entity type configurations
            **kwargs: Additional parameters including 'candidates' for pre-generated candidates
            
        Returns:
            List of extraction results
        """
        import time
        start_time = time.time()
        
        try:
            await self._ensure_model_loaded()
            
            if not self.classifier:
                return []
            
            results = []
            candidates = kwargs.get('candidates', [])
            
            # If no candidates provided, create text segments
            if not candidates:
                segments = self._create_text_segments(text)
            else:
                segments = [(c.text, c.start, c.end) for c in candidates]
            
            # Create labels from entity types
            labels = []
            type_descriptions = {}
            
            for entity_type in entity_types:
                label = entity_type['type']
                labels.append(label)
                
                # Create description from entity type info
                description = entity_type.get('description', '')
                examples = entity_type.get('examples', [])
                keywords = entity_type.get('context_keywords', [])
                
                # Build a rich description for better classification
                desc_parts = [description]
                if examples:
                    desc_parts.append(f"Examples: {', '.join(examples[:3])}")
                if keywords:
                    desc_parts.append(f"Keywords: {', '.join(keywords[:5])}")
                
                type_descriptions[label] = ". ".join(desc_parts)
            
            # Process segments in batches
            batch_size = kwargs.get('batch_size', 10)
            for i in range(0, len(segments), batch_size):
                batch = segments[i:i + batch_size]
                batch_results = await self._process_batch(batch, labels, type_descriptions, text)
                results.extend(batch_results)
            
            # Update statistics
            self.extraction_count += 1
            self.total_processing_time += (time.time() - start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in zero-shot classification strategy: {e}")
            return []
    
    def _create_text_segments(self, text: str, max_length: int = 200, overlap: int = 50) -> List[Tuple[str, int, int]]:
        """Create overlapping text segments for classification"""
        segments = []
        
        # Split by sentences first
        sentences = re.split(r'[.!?]+', text)
        current_pos = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                current_pos = text.find(sentence, current_pos) + len(sentence)
                continue
            
            start_pos = text.find(sentence, current_pos)
            end_pos = start_pos + len(sentence)
            
            # Create segments within long sentences
            if len(sentence) > max_length:
                for j in range(0, len(sentence), max_length - overlap):
                    segment_text = sentence[j:j + max_length]
                    if len(segment_text.strip()) > 20:
                        segments.append((
                            segment_text.strip(),
                            start_pos + j,
                            start_pos + j + len(segment_text.strip())
                        ))
            else:
                segments.append((sentence, start_pos, end_pos))
            
            current_pos = end_pos
        
        return segments
    
    async def _process_batch(self, 
                           batch: List[Tuple[str, int, int]], 
                           labels: List[str], 
                           type_descriptions: Dict[str, str],
                           full_text: str) -> List[ExtractionResult]:
        """Process a batch of text segments"""
        results = []
        
        try:
            for segment_text, start_pos, end_pos in batch:
                if len(segment_text.strip()) < 5:
                    continue
                
                # Perform zero-shot classification
                classification_result = self.classifier(segment_text, labels)
                
                # Process classification results
                for i, (label, score) in enumerate(zip(
                    classification_result['labels'], 
                    classification_result['scores']
                )):
                    if score >= self.min_confidence:
                        # Extract entity mentions from segment
                        entity_mentions = self._extract_entity_mentions(
                            segment_text, label, type_descriptions[label], full_text, start_pos
                        )
                        
                        for mention in entity_mentions:
                            result = ExtractionResult(
                                text=mention['text'],
                                entity_type=label,
                                start_position=mention['start'],
                                end_position=mention['end'],
                                confidence_score=score,
                                strategy_name=self.name,
                                metadata={
                                    "classification_rank": i,
                                    "segment_text": segment_text,
                                    "type_description": type_descriptions[label],
                                    "all_scores": dict(zip(classification_result['labels'], classification_result['scores']))
                                }
                            )
                            results.append(result)
                        
                        # Only take the top classification to reduce noise
                        break
                        
        except Exception as e:
            logger.error(f"Error processing batch in zero-shot classification: {e}")
        
        return results
    
    def _extract_entity_mentions(self, 
                                segment_text: str, 
                                entity_type: str, 
                                type_description: str, 
                                full_text: str, 
                                segment_start: int) -> List[Dict[str, Any]]:
        """Extract specific entity mentions from classified segment"""
        mentions = []
        
        # Use simple heuristics to identify entity mentions
        # This could be enhanced with more sophisticated NLP
        
        # Look for capitalized phrases (potential entities)
        capitalized_phrases = re.findall(r'\b[A-Z][a-zA-Z\s&.,\-]+(?:[A-Z][a-zA-Z\s&.,\-]*)*\b', segment_text)
        
        for phrase in capitalized_phrases:
            phrase = phrase.strip()
            if len(phrase) < 3 or len(phrase.split()) > 6:
                continue
            
            # Find position in segment
            phrase_start = segment_text.find(phrase)
            if phrase_start == -1:
                continue
            
            # Convert to full text positions
            full_start = segment_start + phrase_start
            full_end = full_start + len(phrase)
            
            # Basic relevance filtering
            if self._is_relevant_mention(phrase, entity_type, type_description):
                mentions.append({
                    'text': phrase,
                    'start': full_start,
                    'end': full_end
                })
        
        # If no capitalized phrases, use the whole segment as a potential mention
        if not mentions and self._is_relevant_mention(segment_text, entity_type, type_description):
            mentions.append({
                'text': segment_text.strip(),
                'start': segment_start,
                'end': segment_start + len(segment_text.strip())
            })
        
        return mentions
    
    def _is_relevant_mention(self, text: str, entity_type: str, type_description: str) -> bool:
        """Check if text mention is relevant for the entity type"""
        text_lower = text.lower()
        
        # Skip common words and phrases
        common_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'under', 'over'
        }
        
        if text_lower in common_words:
            return False
        
        # Must have at least one letter
        if not re.search(r'[a-zA-Z]', text):
            return False
        
        # Check against type-specific filters
        entity_type_lower = entity_type.lower()
        
        # Legal entity type heuristics
        if 'court' in entity_type_lower and ('court' in text_lower or 'tribunal' in text_lower):
            return True
        elif 'judge' in entity_type_lower and ('judge' in text_lower or 'justice' in text_lower):
            return True
        elif 'attorney' in entity_type_lower and ('attorney' in text_lower or 'lawyer' in text_lower):
            return True
        elif 'case' in entity_type_lower and ('v.' in text or 'versus' in text_lower):
            return True
        
        return True  # Default to relevant for further processing


class NamedEntityRecognitionStrategy(ExtractionStrategy):
    """
    Named Entity Recognition strategy using pre-trained NER models
    including Blackstone for legal entities and SpaCy for general entities.
    """
    
    def __init__(self):
        super().__init__("named_entity_recognition")
        self.blackstone_model = None
        self.spacy_model = None
        self.legal_model_name = "blackstone/nlp"
        self.general_model_name = "en_core_web_lg"
    
    async def _ensure_models_loaded(self):
        """Lazy load NER models"""
        try:
            if self.spacy_model is None:
                self.spacy_model = spacy.load(self.general_model_name)
                logger.info(f"Loaded SpaCy model: {self.general_model_name}")
        except Exception as e:
            logger.warning(f"Failed to load SpaCy model: {e}")
        
        try:
            if self.blackstone_model is None:
                # Try to load Blackstone if available
                import spacy
                self.blackstone_model = spacy.load("en_blackstone_proto")
                logger.info("Loaded Blackstone legal NER model")
        except Exception as e:
            logger.warning(f"Blackstone model not available: {e}")
    
    async def extract(self, text: str, entity_types: List[Dict[str, Any]], **kwargs) -> List[ExtractionResult]:
        """Extract entities using NER models"""
        import time
        start_time = time.time()
        
        try:
            await self._ensure_models_loaded()
            
            results = []
            
            # Apply Blackstone legal NER if available
            if self.blackstone_model:
                legal_results = await self._extract_with_blackstone(text, entity_types)
                results.extend(legal_results)
            
            # Apply general SpaCy NER
            if self.spacy_model:
                spacy_results = await self._extract_with_spacy(text, entity_types)
                results.extend(spacy_results)
            
            # Update statistics
            self.extraction_count += 1
            self.total_processing_time += (time.time() - start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in NER strategy: {e}")
            return []
    
    async def _extract_with_blackstone(self, text: str, entity_types: List[Dict[str, Any]]) -> List[ExtractionResult]:
        """Extract entities using Blackstone legal NER"""
        results = []
        
        try:
            doc = self.blackstone_model(text)
            
            # Map Blackstone labels to CALES types
            label_mapping = self._create_blackstone_mapping(entity_types)
            
            for ent in doc.ents:
                mapped_types = label_mapping.get(ent.label_, [])
                
                for entity_type in mapped_types:
                    result = ExtractionResult(
                        text=ent.text,
                        entity_type=entity_type['type'],
                        start_position=ent.start_char,
                        end_position=ent.end_char,
                        confidence_score=0.8,  # Default confidence for Blackstone
                        strategy_name=f"{self.name}_blackstone",
                        metadata={
                            "blackstone_label": ent.label_,
                            "entity_config": entity_type,
                            "sentence": ent.sent.text if ent.sent else ""
                        }
                    )
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error in Blackstone extraction: {e}")
        
        return results
    
    async def _extract_with_spacy(self, text: str, entity_types: List[Dict[str, Any]]) -> List[ExtractionResult]:
        """Extract entities using SpaCy general NER"""
        results = []
        
        try:
            doc = self.spacy_model(text)
            
            # Map SpaCy labels to CALES types
            label_mapping = self._create_spacy_mapping(entity_types)
            
            for ent in doc.ents:
                mapped_types = label_mapping.get(ent.label_, [])
                
                for entity_type in mapped_types:
                    result = ExtractionResult(
                        text=ent.text,
                        entity_type=entity_type['type'],
                        start_position=ent.start_char,
                        end_position=ent.end_char,
                        confidence_score=0.7,  # Default confidence for SpaCy
                        strategy_name=f"{self.name}_spacy",
                        metadata={
                            "spacy_label": ent.label_,
                            "entity_config": entity_type,
                            "pos_tags": [token.pos_ for token in ent],
                            "dep_tags": [token.dep_ for token in ent]
                        }
                    )
                    results.append(result)
                    
        except Exception as e:
            logger.error(f"Error in SpaCy extraction: {e}")
        
        return results
    
    def _create_blackstone_mapping(self, entity_types: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Create mapping from Blackstone labels to CALES entity types"""
        mapping = defaultdict(list)
        
        # Blackstone to CALES mapping
        blackstone_mappings = {
            "PERSON": ["JUDGE", "ATTORNEY", "WITNESS", "PLAINTIFF", "DEFENDANT", "PARTY"],
            "ORG": ["COURT", "LAW_FIRM", "CORPORATION", "LLC", "AGENCY"],
            "COURT": ["COURT"],
            "JUDGE": ["JUDGE"],
            "LAWYER": ["ATTORNEY"],
            "LEGISLATION": ["STATUTE", "REGULATION", "CONSTITUTIONAL_PROVISION"],
            "CASE_NAME": ["CASE"],
            "CITATION": ["CITATION", "DOCKET_NUMBER"],
            "PROVISION": ["STATUTE", "REGULATION"],
            "INSTRUMENT": ["CONTRACT", "AGREEMENT", "PLEADING"]
        }
        
        for entity_type in entity_types:
            type_name = entity_type['type']
            
            for blackstone_label, cales_types in blackstone_mappings.items():
                if type_name in cales_types:
                    mapping[blackstone_label].append(entity_type)
        
        return dict(mapping)
    
    def _create_spacy_mapping(self, entity_types: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Create mapping from SpaCy labels to CALES entity types"""
        mapping = defaultdict(list)
        
        # SpaCy to CALES mapping
        spacy_mappings = {
            "PERSON": ["JUDGE", "ATTORNEY", "WITNESS", "PLAINTIFF", "DEFENDANT", "PARTY"],
            "ORG": ["COURT", "LAW_FIRM", "CORPORATION", "LLC", "AGENCY", "NONPROFIT"],
            "GPE": ["JURISDICTION", "STATE", "CITY", "COUNTRY"],
            "MONEY": ["MONEY", "CONTRACT_AMOUNT"],
            "DATE": ["DATE", "CONTRACT_DATE", "EFFECTIVE_DATE", "EXPIRATION_DATE"],
            "PERCENT": ["PERCENTAGE", "INTEREST_RATE"],
            "LAW": ["STATUTE", "REGULATION"],
            "EVENT": ["HEARING", "TRIAL", "PROCEEDING"],
            "FAC": ["COURT", "FACILITY"]
        }
        
        for entity_type in entity_types:
            type_name = entity_type['type']
            
            for spacy_label, cales_types in spacy_mappings.items():
                if type_name in cales_types:
                    mapping[spacy_label].append(entity_type)
        
        return dict(mapping)


class NounPhraseExtractionStrategy(ExtractionStrategy):
    """
    Noun phrase extraction strategy that identifies potential entities
    based on grammatical structure and contextual relevance.
    """
    
    def __init__(self):
        super().__init__("noun_phrase_extraction")
        self.spacy_model = None
        self.model_name = "en_core_web_lg"
        self.min_phrase_length = 2
        self.max_phrase_length = 6
    
    async def _ensure_model_loaded(self):
        """Lazy load SpaCy model"""
        if self.spacy_model is None:
            try:
                self.spacy_model = spacy.load(self.model_name)
                logger.info(f"Loaded SpaCy model for noun phrase extraction: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load SpaCy model: {e}")
                raise
    
    async def extract(self, text: str, entity_types: List[Dict[str, Any]], **kwargs) -> List[ExtractionResult]:
        """Extract entities using noun phrase analysis"""
        import time
        start_time = time.time()
        
        try:
            await self._ensure_model_loaded()
            
            if not self.spacy_model:
                return []
            
            results = []
            doc = self.spacy_model(text)
            
            # Extract noun phrases
            noun_phrases = self._extract_noun_phrases(doc)
            
            # Score and match noun phrases to entity types
            for phrase_info in noun_phrases:
                matching_results = self._match_phrase_to_types(phrase_info, entity_types, text)
                results.extend(matching_results)
            
            # Update statistics
            self.extraction_count += 1
            self.total_processing_time += (time.time() - start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in noun phrase extraction strategy: {e}")
            return []
    
    def _extract_noun_phrases(self, doc: Doc) -> List[Dict[str, Any]]:
        """Extract and analyze noun phrases from document"""
        phrases = []
        
        # Extract noun chunks
        for chunk in doc.noun_chunks:
            phrase_length = len(chunk.text.split())
            
            # Filter by length
            if phrase_length < self.min_phrase_length or phrase_length > self.max_phrase_length:
                continue
            
            # Analyze phrase structure
            phrase_info = {
                'text': chunk.text,
                'start': chunk.start_char,
                'end': chunk.end_char,
                'root': chunk.root.text,
                'pos_tags': [token.pos_ for token in chunk],
                'dep_tags': [token.dep_ for token in chunk],
                'is_proper': any(token.pos_ == 'PROPN' for token in chunk),
                'has_title': self._has_title_words(chunk.text),
                'context': self._get_phrase_context(chunk, doc)
            }
            
            phrases.append(phrase_info)
        
        # Extract additional compound nouns and entities
        compound_phrases = self._extract_compound_phrases(doc)
        phrases.extend(compound_phrases)
        
        return phrases
    
    def _extract_compound_phrases(self, doc: Doc) -> List[Dict[str, Any]]:
        """Extract compound phrases that might be missed by noun chunking"""
        phrases = []
        
        # Look for patterns like "Title Name", "Name Title", etc.
        title_patterns = [
            r'\b(?:Judge|Justice|Attorney|Lawyer|Dr|Mr|Ms|Mrs|Prof|President|CEO|Director)\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*',
            r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Judge|Justice|Attorney|Lawyer|Esq|PhD|MD)',
            r'\b[A-Z][a-zA-Z]+\s+(?:v\.|vs\.)\s+[A-Z][a-zA-Z]+',  # Case names
            r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Inc|Corp|LLC|LLP|Ltd)',  # Company names
        ]
        
        text = doc.text
        for pattern in title_patterns:
            for match in re.finditer(pattern, text):
                phrase_text = match.group()
                
                phrase_info = {
                    'text': phrase_text,
                    'start': match.start(),
                    'end': match.end(),
                    'root': phrase_text.split()[-1] if phrase_text.split() else phrase_text,
                    'pos_tags': [],  # Would need to analyze separately
                    'dep_tags': [],
                    'is_proper': True,
                    'has_title': True,
                    'context': self._get_text_context(text, match.start(), match.end()),
                    'pattern_matched': pattern
                }
                
                phrases.append(phrase_info)
        
        return phrases
    
    def _has_title_words(self, text: str) -> bool:
        """Check if phrase contains title words"""
        title_words = {
            'judge', 'justice', 'attorney', 'lawyer', 'counsel', 'dr', 'doctor',
            'mr', 'ms', 'mrs', 'prof', 'professor', 'president', 'ceo', 'director',
            'chairman', 'member', 'chief', 'senior', 'junior', 'associate',
            'partner', 'firm', 'court', 'honorable', 'magistrate', 'commissioner'
        }
        
        text_words = set(text.lower().split())
        return bool(text_words & title_words)
    
    def _get_phrase_context(self, chunk: Span, doc: Doc) -> str:
        """Get context around a noun phrase"""
        start_token = max(0, chunk.start - 5)
        end_token = min(len(doc), chunk.end + 5)
        
        context_tokens = doc[start_token:end_token]
        return ' '.join([token.text for token in context_tokens])
    
    def _get_text_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get text context around a position"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _match_phrase_to_types(self, 
                              phrase_info: Dict[str, Any], 
                              entity_types: List[Dict[str, Any]], 
                              full_text: str) -> List[ExtractionResult]:
        """Match noun phrase to potential entity types"""
        results = []
        phrase_text = phrase_info['text']
        context = phrase_info.get('context', '')
        
        # Calculate scores for each entity type
        for entity_type in entity_types:
            score = self._calculate_phrase_score(phrase_info, entity_type)
            
            if score >= 0.5:  # Threshold for noun phrase matching
                result = ExtractionResult(
                    text=phrase_text,
                    entity_type=entity_type['type'],
                    start_position=phrase_info['start'],
                    end_position=phrase_info['end'],
                    confidence_score=score,
                    strategy_name=self.name,
                    metadata={
                        "phrase_info": phrase_info,
                        "entity_config": entity_type,
                        "score_breakdown": self._get_score_breakdown(phrase_info, entity_type)
                    }
                )
                results.append(result)
        
        return results
    
    def _calculate_phrase_score(self, phrase_info: Dict[str, Any], entity_type: Dict[str, Any]) -> float:
        """Calculate relevance score for phrase-entity type pair"""
        score = 0.0
        
        phrase_text = phrase_info['text'].lower()
        context = phrase_info.get('context', '').lower()
        
        # Keyword matching
        keywords = entity_type.get('context_keywords', [])
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in context)
        if keywords:
            score += 0.3 * (keyword_matches / len(keywords))
        
        # Example matching
        examples = entity_type.get('examples', [])
        example_similarity = 0.0
        if examples:
            for example in examples:
                similarity = self._text_similarity(phrase_text, example.lower())
                example_similarity = max(example_similarity, similarity)
            score += 0.3 * example_similarity
        
        # Structural features
        if phrase_info.get('is_proper', False):
            score += 0.2
        
        if phrase_info.get('has_title', False):
            score += 0.2
        
        # Entity type specific heuristics
        entity_type_name = entity_type['type'].lower()
        
        if 'person' in entity_type_name or 'judge' in entity_type_name or 'attorney' in entity_type_name:
            if phrase_info.get('is_proper', False) and phrase_info.get('has_title', False):
                score += 0.2
        
        if 'court' in entity_type_name and 'court' in phrase_text:
            score += 0.3
        
        if 'corporation' in entity_type_name or 'llc' in entity_type_name:
            if any(suffix in phrase_text for suffix in ['inc', 'corp', 'llc', 'ltd']):
                score += 0.3
        
        return min(1.0, score)
    
    def _get_score_breakdown(self, phrase_info: Dict[str, Any], entity_type: Dict[str, Any]) -> Dict[str, float]:
        """Get detailed score breakdown for debugging"""
        return {
            "keyword_score": 0.0,  # Would calculate actual scores here
            "example_score": 0.0,
            "structural_score": 0.0,
            "heuristic_score": 0.0
        }
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0


class SemanticSimilarityStrategy(ExtractionStrategy):
    """
    Semantic similarity strategy using sentence transformers
    to find entities based on semantic meaning rather than exact matches.
    """
    
    def __init__(self):
        super().__init__("semantic_similarity")
        self.sentence_model = None
        self.model_name = "all-MiniLM-L6-v2"
        self.similarity_threshold = 0.7
        self.max_candidates = 100
    
    async def _ensure_model_loaded(self):
        """Lazy load sentence transformer model"""
        if self.sentence_model is None:
            try:
                self.sentence_model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence transformer model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer model: {e}")
                # Fallback to simple similarity
                self.sentence_model = "fallback"
    
    async def extract(self, text: str, entity_types: List[Dict[str, Any]], **kwargs) -> List[ExtractionResult]:
        """Extract entities using semantic similarity"""
        import time
        start_time = time.time()
        
        try:
            await self._ensure_model_loaded()
            
            results = []
            candidates = kwargs.get('candidates', [])
            
            if not candidates:
                # Generate candidates from text
                candidates = self._generate_semantic_candidates(text)
            
            # Limit candidates to prevent excessive processing
            if len(candidates) > self.max_candidates:
                candidates = candidates[:self.max_candidates]
            
            # Calculate similarities
            if self.sentence_model and self.sentence_model != "fallback":
                results = await self._semantic_matching_with_transformers(candidates, entity_types, text)
            else:
                results = await self._semantic_matching_fallback(candidates, entity_types, text)
            
            # Update statistics
            self.extraction_count += 1
            self.total_processing_time += (time.time() - start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic similarity strategy: {e}")
            return []
    
    def _generate_semantic_candidates(self, text: str) -> List[Dict[str, Any]]:
        """Generate candidate phrases for semantic analysis"""
        candidates = []
        
        # Split into sentences and phrases
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Extract potential entity phrases
            phrases = self._extract_phrases_from_sentence(sentence)
            
            for phrase, start_pos in phrases:
                candidates.append({
                    'text': phrase,
                    'start': start_pos,
                    'end': start_pos + len(phrase),
                    'sentence': sentence
                })
        
        return candidates
    
    def _extract_phrases_from_sentence(self, sentence: str) -> List[Tuple[str, int]]:
        """Extract meaningful phrases from a sentence"""
        phrases = []
        
        # Extract capitalized phrases
        capitalized_pattern = r'\b[A-Z][a-zA-Z\s&.,\-]*(?:[A-Z][a-zA-Z\s&.,\-]*)*\b'
        for match in re.finditer(capitalized_pattern, sentence):
            phrase = match.group().strip()
            if len(phrase) > 3 and len(phrase.split()) <= 5:
                phrases.append((phrase, match.start()))
        
        # Extract quoted phrases
        quoted_pattern = r'"([^"]+)"'
        for match in re.finditer(quoted_pattern, sentence):
            phrase = match.group(1).strip()
            if len(phrase) > 3:
                phrases.append((phrase, match.start() + 1))  # +1 to skip the quote
        
        return phrases
    
    async def _semantic_matching_with_transformers(self, 
                                                  candidates: List[Dict[str, Any]], 
                                                  entity_types: List[Dict[str, Any]], 
                                                  text: str) -> List[ExtractionResult]:
        """Perform semantic matching using sentence transformers"""
        results = []
        
        try:
            # Prepare candidate texts
            candidate_texts = [c['text'] for c in candidates]
            
            # Encode candidates
            candidate_embeddings = self.sentence_model.encode(candidate_texts)
            
            # For each entity type, create reference embeddings
            for entity_type in entity_types:
                reference_texts = []
                
                # Add description
                if entity_type.get('description'):
                    reference_texts.append(entity_type['description'])
                
                # Add examples
                examples = entity_type.get('examples', [])
                reference_texts.extend(examples[:5])  # Limit examples
                
                # Add keyword phrases
                keywords = entity_type.get('context_keywords', [])
                if keywords:
                    keyword_phrase = ' '.join(keywords)
                    reference_texts.append(keyword_phrase)
                
                if not reference_texts:
                    continue
                
                # Encode references
                reference_embeddings = self.sentence_model.encode(reference_texts)
                
                # Calculate similarities
                from sentence_transformers.util import cos_sim
                similarities = cos_sim(candidate_embeddings, reference_embeddings)
                
                # Find matches above threshold
                for i, candidate in enumerate(candidates):
                    max_similarity = float(similarities[i].max())
                    
                    if max_similarity >= self.similarity_threshold:
                        result = ExtractionResult(
                            text=candidate['text'],
                            entity_type=entity_type['type'],
                            start_position=candidate['start'],
                            end_position=candidate['end'],
                            confidence_score=max_similarity,
                            strategy_name=self.name,
                            metadata={
                                "similarity_score": max_similarity,
                                "reference_texts": reference_texts,
                                "entity_config": entity_type,
                                "candidate_info": candidate
                            }
                        )
                        results.append(result)
                        
        except Exception as e:
            logger.error(f"Error in transformer-based semantic matching: {e}")
        
        return results
    
    async def _semantic_matching_fallback(self, 
                                         candidates: List[Dict[str, Any]], 
                                         entity_types: List[Dict[str, Any]], 
                                         text: str) -> List[ExtractionResult]:
        """Fallback semantic matching without transformers"""
        results = []
        
        for candidate in candidates:
            candidate_text = candidate['text'].lower()
            candidate_words = set(candidate_text.split())
            
            for entity_type in entity_types:
                score = 0.0
                
                # Compare with examples
                examples = entity_type.get('examples', [])
                for example in examples:
                    example_words = set(example.lower().split())
                    if example_words and candidate_words:
                        overlap = len(candidate_words & example_words)
                        total = len(candidate_words | example_words)
                        if total > 0:
                            score = max(score, overlap / total)
                
                # Compare with keywords
                keywords = entity_type.get('context_keywords', [])
                for keyword in keywords:
                    keyword_words = set(keyword.lower().split())
                    if keyword_words and candidate_words:
                        overlap = len(candidate_words & keyword_words)
                        total = len(candidate_words | keyword_words)
                        if total > 0:
                            score = max(score, overlap / total)
                
                if score >= self.similarity_threshold:
                    result = ExtractionResult(
                        text=candidate['text'],
                        entity_type=entity_type['type'],
                        start_position=candidate['start'],
                        end_position=candidate['end'],
                        confidence_score=score,
                        strategy_name=f"{self.name}_fallback",
                        metadata={
                            "similarity_score": score,
                            "entity_config": entity_type,
                            "candidate_info": candidate
                        }
                    )
                    results.append(result)
        
        return results


# Strategy factory function
def create_strategy(strategy_name: str) -> Optional[ExtractionStrategy]:
    """Create an extraction strategy by name"""
    strategies = {
        "zero_shot": ZeroShotClassificationStrategy,
        "ner": NamedEntityRecognitionStrategy,
        "noun_phrase": NounPhraseExtractionStrategy,
        "semantic": SemanticSimilarityStrategy
    }
    
    strategy_class = strategies.get(strategy_name)
    if strategy_class:
        return strategy_class()
    else:
        logger.error(f"Unknown strategy: {strategy_name}")
        return None


# Example usage
if __name__ == "__main__":
    import asyncio
    import yaml
    
    async def test_strategies():
        # Load test configuration
        with open("/srv/luris/be/entity-extraction-service/config/cales_config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract some entity types for testing
        test_types = []
        for category, types in config['entity_types'].items():
            test_types.extend(types[:2])  # Take first 2 from each category
            if len(test_types) >= 10:
                break
        
        test_text = """
        The plaintiff, John Smith, filed a complaint against ABC Corporation
        in the Superior Court of California. Judge Mary Johnson presided over
        the case, which involved a breach of contract claim regarding a
        software licensing agreement worth $500,000. Attorney Jane Doe
        represents the plaintiff, while the defendant is represented by
        the law firm of Wilson & Associates LLP.
        """
        
        # Test each strategy
        strategies = [
            ZeroShotClassificationStrategy(),
            NamedEntityRecognitionStrategy(),
            NounPhraseExtractionStrategy(),
            SemanticSimilarityStrategy()
        ]
        
        for strategy in strategies:
            print(f"\n--- Testing {strategy.name} ---")
            results = await strategy.extract(test_text, test_types)
            
            print(f"Found {len(results)} entities:")
            for result in results[:5]:  # Show first 5
                print(f"  {result.text} -> {result.entity_type} (conf: {result.confidence_score:.2f})")
            
            print(f"Strategy stats: {strategy.get_stats()}")
    
    asyncio.run(test_strategies())