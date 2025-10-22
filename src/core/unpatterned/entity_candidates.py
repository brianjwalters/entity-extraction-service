"""
Entity Candidate Generation and Validation

This module generates and validates candidate entities for unpatterned entity extraction,
providing confidence scoring, candidate filtering, and caching mechanisms.
"""

import logging
import asyncio
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import re
import json

# NLP libraries
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token, Span
import numpy as np

# Internal imports
from .unpatterned_entity_handler import ProcessingMode

logger = logging.getLogger(__name__)


@dataclass
class EntityCandidate:
    """Represents a candidate entity for further processing"""
    text: str
    start: int
    end: int
    confidence: float
    candidate_type: str  # How the candidate was generated
    features: Dict[str, Any] = field(default_factory=dict)
    context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        self.text = self.text.strip()
        self.length = len(self.text)
        self.word_count = len(self.text.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert candidate to dictionary"""
        return {
            'text': self.text,
            'start': self.start,
            'end': self.end,
            'confidence': self.confidence,
            'candidate_type': self.candidate_type,
            'features': self.features,
            'context': self.context,
            'metadata': self.metadata,
            'length': self.length,
            'word_count': self.word_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityCandidate':
        """Create candidate from dictionary"""
        return cls(
            text=data['text'],
            start=data['start'],
            end=data['end'],
            confidence=data['confidence'],
            candidate_type=data['candidate_type'],
            features=data.get('features', {}),
            context=data.get('context', ''),
            metadata=data.get('metadata', {})
        )


class CandidateType(Enum):
    """Types of candidate generation methods"""
    CAPITALIZED_PHRASE = "capitalized_phrase"
    NOUN_PHRASE = "noun_phrase"
    QUOTED_TEXT = "quoted_text"
    TITLE_PATTERN = "title_pattern"
    NUMERICAL_PATTERN = "numerical_pattern"
    LEGAL_PATTERN = "legal_pattern"
    ORGANIZATION_PATTERN = "organization_pattern"
    CONTEXT_DRIVEN = "context_driven"
    SIMILARITY_BASED = "similarity_based"


@dataclass
class CacheEntry:
    """Cache entry for candidate generation results"""
    candidates: List[EntityCandidate]
    timestamp: datetime
    text_hash: str
    processing_mode: ProcessingMode
    entity_types: List[str]


class CandidateCache:
    """LRU cache for candidate generation results"""
    
    def __init__(self, max_size: int = 1000, ttl_minutes: int = 60):
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []
    
    def _generate_key(self, text: str, mode: ProcessingMode, entity_types: List[str]) -> str:
        """Generate cache key"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        types_str = ",".join(sorted(entity_types))
        return f"{text_hash}_{mode.value}_{hashlib.md5(types_str.encode()).hexdigest()}"
    
    def get(self, text: str, mode: ProcessingMode, entity_types: List[str]) -> Optional[List[EntityCandidate]]:
        """Get cached candidates if available and valid"""
        key = self._generate_key(text, mode, entity_types)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # Check TTL
            if datetime.now() - entry.timestamp < self.ttl:
                # Update access order
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                
                return entry.candidates
            else:
                # Expired entry
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
        
        return None
    
    def put(self, text: str, mode: ProcessingMode, entity_types: List[str], candidates: List[EntityCandidate]):
        """Cache candidates"""
        key = self._generate_key(text, mode, entity_types)
        
        # Evict if necessary
        while len(self.cache) >= self.max_size and self.access_order:
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.cache:
                del self.cache[oldest_key]
        
        # Add new entry
        text_hash = hashlib.md5(text.encode()).hexdigest()
        type_names = [et if isinstance(et, str) else et.get('type', '') for et in entity_types]
        
        entry = CacheEntry(
            candidates=candidates,
            timestamp=datetime.now(),
            text_hash=text_hash,
            processing_mode=mode,
            entity_types=type_names
        )
        
        self.cache[key] = entry
        self.access_order.append(key)
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": 0.0,  # Would need to track hits/misses
            "ttl_minutes": self.ttl.total_seconds() / 60
        }


class EntityCandidateGenerator:
    """
    Generates entity candidates using various heuristics and patterns.
    
    This class creates potential entity mentions that can then be classified
    and validated by the extraction strategies.
    """
    
    def __init__(self, 
                 entity_types: List[Dict[str, Any]],
                 cache_size: int = 1000,
                 min_confidence: float = 0.3):
        """
        Initialize the candidate generator.
        
        Args:
            entity_types: List of entity type configurations
            cache_size: Size of candidate cache
            min_confidence: Minimum confidence for candidates
        """
        self.entity_types = entity_types
        self.min_confidence = min_confidence
        self.cache = CandidateCache(max_size=cache_size)
        
        # Pre-compile patterns for efficiency
        self._compile_patterns()
        
        # Statistics
        self.stats = {
            "total_generations": 0,
            "cache_hits": 0,
            "candidate_counts_by_type": defaultdict(int),
            "processing_times": []
        }
        
        logger.info(f"EntityCandidateGenerator initialized with {len(entity_types)} entity types")
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for candidate generation"""
        self.patterns = {
            # Title patterns for people
            'title_person': re.compile(
                r'\b(?:Judge|Justice|Attorney|Lawyer|Dr|Mr|Ms|Mrs|Prof|President|CEO|Director|Chairman|Chief)\s+'
                r'[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:\s*,?\s*(?:Esq|Jr|Sr|PhD|MD))?'
            ),
            
            # Organization patterns
            'organization': re.compile(
                r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z&][a-zA-Z&]*)*\s+'
                r'(?:Inc|Corp|Corporation|LLC|LLP|Ltd|Limited|Company|Co|Group|Associates|Partners|Law|Firm)\b'
            ),
            
            # Case name patterns
            'case_name': re.compile(
                r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:v\.|vs\.|versus)\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*'
            ),
            
            # Court patterns
            'court': re.compile(
                r'\b(?:Supreme|District|Superior|Circuit|Appellate|Municipal|County|Federal|State)\s+'
                r'Court(?:\s+of\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)?'
            ),
            
            # Legal document patterns
            'legal_document': re.compile(
                r'\b(?:Motion|Order|Judgment|Decree|Opinion|Brief|Pleading|Complaint|Answer|Petition)\b'
                r'(?:\s+(?:for|to|of|in)\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)?'
            ),
            
            # Quoted text (potential entity names or terms)
            'quoted': re.compile(r'"([^"]{3,50})"'),
            
            # Parenthetical information
            'parenthetical': re.compile(r'\(([^)]{3,50})\)'),
            
            # Capitalized phrases (potential proper nouns)
            'capitalized': re.compile(
                r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*){1,4}\b'
            ),
            
            # Legal citations (basic pattern)
            'citation': re.compile(
                r'\b\d+\s+[A-Z][a-zA-Z.]*\s+\d+'
            ),
            
            # Statute references
            'statute': re.compile(
                r'\b(?:\d+\s+)?[A-Z][a-zA-Z.]*\s*(?:Code|CFR|USC)\s*(?:§|[Ss]ection)?\s*\d+'
            ),
        }
    
    async def generate_candidates(self, 
                                 text: str,
                                 entity_types: List[Dict[str, Any]],
                                 mode: ProcessingMode = ProcessingMode.ADAPTIVE) -> List[EntityCandidate]:
        """
        Generate entity candidates from text.
        
        Args:
            text: Input text
            entity_types: Entity types to consider
            mode: Processing mode
            
        Returns:
            List of entity candidates
        """
        start_time = time.time()
        
        try:
            # Check cache first
            type_names = [et['type'] for et in entity_types]
            cached_candidates = self.cache.get(text, mode, type_names)
            
            if cached_candidates is not None:
                self.stats["cache_hits"] += 1
                return cached_candidates
            
            # Generate candidates
            candidates = await self._generate_candidates_internal(text, entity_types, mode)
            
            # Filter and score candidates
            filtered_candidates = self._filter_and_score_candidates(candidates, text)
            
            # Cache results
            self.cache.put(text, mode, type_names, filtered_candidates)
            
            # Update statistics
            self.stats["total_generations"] += 1
            self.stats["processing_times"].append(time.time() - start_time)
            
            for candidate in filtered_candidates:
                self.stats["candidate_counts_by_type"][candidate.candidate_type] += 1
            
            logger.debug(f"Generated {len(filtered_candidates)} candidates in {time.time() - start_time:.3f}s")
            return filtered_candidates
            
        except Exception as e:
            logger.error(f"Error generating candidates: {e}")
            return []
    
    async def _generate_candidates_internal(self, 
                                           text: str,
                                           entity_types: List[Dict[str, Any]],
                                           mode: ProcessingMode) -> List[EntityCandidate]:
        """Internal candidate generation"""
        candidates = []
        
        # Determine which generators to use based on mode
        generators = self._select_generators(mode)
        
        # Run generators
        for generator_name in generators:
            generator_method = getattr(self, f"_generate_{generator_name}_candidates", None)
            if generator_method:
                generator_candidates = await generator_method(text, entity_types)
                candidates.extend(generator_candidates)
        
        return candidates
    
    def _select_generators(self, mode: ProcessingMode) -> List[str]:
        """Select candidate generators based on processing mode"""
        if mode == ProcessingMode.FAST:
            return ['pattern', 'capitalized']
        elif mode == ProcessingMode.COMPREHENSIVE:
            return ['pattern', 'capitalized', 'noun_phrase', 'context_driven', 'quoted']
        else:  # ADAPTIVE
            return ['pattern', 'capitalized', 'noun_phrase', 'quoted']
    
    async def _generate_pattern_candidates(self, 
                                          text: str,
                                          entity_types: List[Dict[str, Any]]) -> List[EntityCandidate]:
        """Generate candidates using regex patterns"""
        candidates = []
        
        for pattern_name, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                candidate_text = match.group(1) if pattern_name in ['quoted', 'parenthetical'] else match.group()
                
                # Calculate confidence based on pattern type
                confidence = self._calculate_pattern_confidence(pattern_name, candidate_text, text)
                
                if confidence >= self.min_confidence:
                    candidate = EntityCandidate(
                        text=candidate_text,
                        start=match.start(1) if pattern_name in ['quoted', 'parenthetical'] else match.start(),
                        end=match.end(1) if pattern_name in ['quoted', 'parenthetical'] else match.end(),
                        confidence=confidence,
                        candidate_type=f"pattern_{pattern_name}",
                        features={
                            'pattern_name': pattern_name,
                            'match_length': len(candidate_text),
                            'word_count': len(candidate_text.split())
                        },
                        context=self._extract_context(text, match.start(), match.end()),
                        metadata={'pattern': pattern.pattern}
                    )
                    candidates.append(candidate)
        
        return candidates
    
    async def _generate_capitalized_candidates(self, 
                                              text: str,
                                              entity_types: List[Dict[str, Any]]) -> List[EntityCandidate]:
        """Generate candidates from capitalized phrases"""
        candidates = []
        
        # Find capitalized words and phrases
        words = text.split()
        current_phrase = []
        phrase_start = 0
        
        for i, word in enumerate(words):
            # Clean word of punctuation for capitalization check
            clean_word = re.sub(r'[^\w]', '', word)
            
            if clean_word and clean_word[0].isupper() and len(clean_word) > 1:
                if not current_phrase:
                    # Start of phrase - find position in original text
                    phrase_start = self._find_word_position(text, word, i)
                current_phrase.append(word)
            else:
                # End of phrase
                if len(current_phrase) >= 2 and len(current_phrase) <= 5:
                    phrase_text = ' '.join(current_phrase)
                    phrase_end = phrase_start + len(phrase_text)
                    
                    # Calculate confidence
                    confidence = self._calculate_capitalized_confidence(phrase_text, text)
                    
                    if confidence >= self.min_confidence:
                        candidate = EntityCandidate(
                            text=phrase_text,
                            start=phrase_start,
                            end=phrase_end,
                            confidence=confidence,
                            candidate_type=CandidateType.CAPITALIZED_PHRASE.value,
                            features={
                                'word_count': len(current_phrase),
                                'has_common_words': self._has_common_words(phrase_text)
                            },
                            context=self._extract_context(text, phrase_start, phrase_end)
                        )
                        candidates.append(candidate)
                
                current_phrase = []
        
        # Handle phrase at end of text
        if len(current_phrase) >= 2:
            phrase_text = ' '.join(current_phrase)
            phrase_end = phrase_start + len(phrase_text)
            confidence = self._calculate_capitalized_confidence(phrase_text, text)
            
            if confidence >= self.min_confidence:
                candidate = EntityCandidate(
                    text=phrase_text,
                    start=phrase_start,
                    end=phrase_end,
                    confidence=confidence,
                    candidate_type=CandidateType.CAPITALIZED_PHRASE.value,
                    features={
                        'word_count': len(current_phrase),
                        'has_common_words': self._has_common_words(phrase_text)
                    },
                    context=self._extract_context(text, phrase_start, phrase_end)
                )
                candidates.append(candidate)
        
        return candidates
    
    async def _generate_noun_phrase_candidates(self, 
                                              text: str,
                                              entity_types: List[Dict[str, Any]]) -> List[EntityCandidate]:
        """Generate candidates using noun phrase extraction"""
        candidates = []
        
        try:
            # Load SpaCy model if available
            import spacy
            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("SpaCy model not available for noun phrase extraction")
                return candidates
            
            doc = nlp(text)
            
            # Extract noun chunks
            for chunk in doc.noun_chunks:
                # Filter noun chunks
                if (len(chunk.text) > 3 and 
                    len(chunk.text.split()) >= 2 and 
                    len(chunk.text.split()) <= 5):
                    
                    confidence = self._calculate_noun_phrase_confidence(chunk, text)
                    
                    if confidence >= self.min_confidence:
                        candidate = EntityCandidate(
                            text=chunk.text,
                            start=chunk.start_char,
                            end=chunk.end_char,
                            confidence=confidence,
                            candidate_type=CandidateType.NOUN_PHRASE.value,
                            features={
                                'pos_tags': [token.pos_ for token in chunk],
                                'dep_tags': [token.dep_ for token in chunk],
                                'root_pos': chunk.root.pos_,
                                'has_proper_noun': any(token.pos_ == 'PROPN' for token in chunk)
                            },
                            context=self._extract_context(text, chunk.start_char, chunk.end_char)
                        )
                        candidates.append(candidate)
                        
        except ImportError:
            logger.warning("SpaCy not available for noun phrase extraction")
        except Exception as e:
            logger.error(f"Error in noun phrase extraction: {e}")
        
        return candidates
    
    async def _generate_context_driven_candidates(self, 
                                                 text: str,
                                                 entity_types: List[Dict[str, Any]]) -> List[EntityCandidate]:
        """Generate candidates based on entity type contexts"""
        candidates = []
        
        # Create context keywords lookup
        context_keywords = defaultdict(list)
        for entity_type in entity_types:
            keywords = entity_type.get('context_keywords', [])
            for keyword in keywords:
                context_keywords[keyword.lower()].append(entity_type)
        
        # Find context keywords in text
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            sentence_lower = sentence.lower()
            
            # Check for context keywords
            found_keywords = []
            for keyword in context_keywords:
                if keyword in sentence_lower:
                    found_keywords.append(keyword)
            
            if found_keywords:
                # Extract potential entities from this sentence
                sentence_candidates = self._extract_entities_from_context_sentence(
                    sentence, found_keywords, context_keywords, text
                )
                candidates.extend(sentence_candidates)
        
        return candidates
    
    async def _generate_quoted_candidates(self, 
                                         text: str,
                                         entity_types: List[Dict[str, Any]]) -> List[EntityCandidate]:
        """Generate candidates from quoted text"""
        candidates = []
        
        # Find quoted text
        quote_patterns = [
            r'"([^"]{3,50})"',  # Double quotes
            r"'([^']{3,50})'",  # Single quotes
            r'`([^`]{3,50})`',  # Backticks
        ]
        
        for pattern in quote_patterns:
            for match in re.finditer(pattern, text):
                quoted_text = match.group(1).strip()
                
                if len(quoted_text) > 2:
                    confidence = self._calculate_quoted_confidence(quoted_text, text)
                    
                    if confidence >= self.min_confidence:
                        candidate = EntityCandidate(
                            text=quoted_text,
                            start=match.start(1),
                            end=match.end(1),
                            confidence=confidence,
                            candidate_type=CandidateType.QUOTED_TEXT.value,
                            features={
                                'quote_type': pattern,
                                'is_title_case': quoted_text.istitle(),
                                'has_spaces': ' ' in quoted_text
                            },
                            context=self._extract_context(text, match.start(), match.end())
                        )
                        candidates.append(candidate)
        
        return candidates
    
    def _calculate_pattern_confidence(self, pattern_name: str, candidate_text: str, full_text: str) -> float:
        """Calculate confidence score for pattern-based candidates"""
        base_confidence = {
            'title_person': 0.8,
            'organization': 0.7,
            'case_name': 0.9,
            'court': 0.8,
            'legal_document': 0.6,
            'quoted': 0.5,
            'parenthetical': 0.4,
            'capitalized': 0.5,
            'citation': 0.8,
            'statute': 0.8
        }
        
        confidence = base_confidence.get(pattern_name, 0.5)
        
        # Adjust based on candidate characteristics
        word_count = len(candidate_text.split())
        
        if word_count == 1:
            confidence *= 0.8  # Single words are less confident
        elif word_count > 5:
            confidence *= 0.9  # Very long phrases might be less precise
        
        # Boost confidence for proper nouns
        if candidate_text and candidate_text[0].isupper():
            confidence *= 1.1
        
        # Reduce confidence for common words
        if self._has_common_words(candidate_text):
            confidence *= 0.9
        
        return min(1.0, confidence)
    
    def _calculate_capitalized_confidence(self, phrase_text: str, full_text: str) -> float:
        """Calculate confidence for capitalized phrases"""
        base_confidence = 0.6
        
        # Boost for title-like patterns
        if any(word in phrase_text.lower() for word in ['judge', 'attorney', 'court', 'inc', 'corp']):
            base_confidence += 0.2
        
        # Reduce for common words
        if self._has_common_words(phrase_text):
            base_confidence -= 0.2
        
        # Boost for proper noun patterns
        words = phrase_text.split()
        if all(word[0].isupper() for word in words if word):
            base_confidence += 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_noun_phrase_confidence(self, chunk, full_text: str) -> float:
        """Calculate confidence for noun phrase candidates"""
        base_confidence = 0.5
        
        # Boost for proper nouns
        if any(token.pos_ == 'PROPN' for token in chunk):
            base_confidence += 0.2
        
        # Boost for title words
        title_words = {'judge', 'attorney', 'court', 'corporation', 'company'}
        if any(token.text.lower() in title_words for token in chunk):
            base_confidence += 0.2
        
        # Reduce for very common patterns
        if chunk.root.text.lower() in {'thing', 'person', 'place', 'time'}:
            base_confidence -= 0.2
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_quoted_confidence(self, quoted_text: str, full_text: str) -> float:
        """Calculate confidence for quoted text candidates"""
        base_confidence = 0.4
        
        # Boost for title case
        if quoted_text.istitle():
            base_confidence += 0.2
        
        # Boost for legal terms
        legal_indicators = ['v.', 'versus', 'inc', 'corp', 'llc', 'court']
        if any(indicator in quoted_text.lower() for indicator in legal_indicators):
            base_confidence += 0.3
        
        # Reduce for very short or long text
        if len(quoted_text) < 5 or len(quoted_text) > 30:
            base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _extract_entities_from_context_sentence(self, 
                                               sentence: str,
                                               found_keywords: List[str],
                                               context_keywords: Dict[str, List[Dict]],
                                               full_text: str) -> List[EntityCandidate]:
        """Extract potential entities from a sentence with context keywords"""
        candidates = []
        
        # Find the sentence position in full text
        sentence_start = full_text.find(sentence)
        if sentence_start == -1:
            return candidates
        
        # Look for capitalized phrases in the sentence
        capitalized_phrases = re.findall(r'\b[A-Z][a-zA-Z\s&.,\-]*(?:[A-Z][a-zA-Z\s&.,\-]*)*\b', sentence)
        
        for phrase in capitalized_phrases:
            phrase = phrase.strip()
            if len(phrase) < 3:
                continue
            
            phrase_start = sentence.find(phrase)
            if phrase_start == -1:
                continue
            
            # Calculate confidence based on keyword proximity
            confidence = self._calculate_context_confidence(phrase, found_keywords)
            
            if confidence >= self.min_confidence:
                full_start = sentence_start + phrase_start
                full_end = full_start + len(phrase)
                
                candidate = EntityCandidate(
                    text=phrase,
                    start=full_start,
                    end=full_end,
                    confidence=confidence,
                    candidate_type=CandidateType.CONTEXT_DRIVEN.value,
                    features={
                        'context_keywords': found_keywords,
                        'keyword_proximity': self._calculate_keyword_proximity(sentence, phrase, found_keywords)
                    },
                    context=sentence
                )
                candidates.append(candidate)
        
        return candidates
    
    def _calculate_context_confidence(self, phrase: str, keywords: List[str]) -> float:
        """Calculate confidence based on context keywords"""
        base_confidence = 0.5
        
        # Boost based on number of relevant keywords
        keyword_boost = min(0.3, len(keywords) * 0.1)
        base_confidence += keyword_boost
        
        # Boost for proper noun patterns
        if phrase and phrase[0].isupper():
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _calculate_keyword_proximity(self, sentence: str, phrase: str, keywords: List[str]) -> float:
        """Calculate how close the phrase is to context keywords"""
        phrase_pos = sentence.lower().find(phrase.lower())
        if phrase_pos == -1:
            return 0.0
        
        min_distance = float('inf')
        
        for keyword in keywords:
            keyword_pos = sentence.lower().find(keyword)
            if keyword_pos != -1:
                distance = abs(phrase_pos - keyword_pos)
                min_distance = min(min_distance, distance)
        
        if min_distance == float('inf'):
            return 0.0
        
        # Convert to proximity score (closer = higher score)
        max_sentence_len = len(sentence)
        proximity = 1.0 - (min_distance / max_sentence_len)
        
        return proximity
    
    def _find_word_position(self, text: str, word: str, word_index: int) -> int:
        """Find the position of a word in text by index"""
        words = text.split()
        if word_index >= len(words):
            return -1
        
        # Find cumulative position
        position = 0
        for i, w in enumerate(words):
            if i == word_index:
                return text.find(word, position)
            position = text.find(w, position) + len(w)
        
        return -1
    
    def _has_common_words(self, text: str) -> bool:
        """Check if text contains common words that reduce confidence"""
        common_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'under', 'over',
            'this', 'that', 'these', 'those', 'such', 'some', 'any', 'all'
        }
        
        text_words = set(text.lower().split())
        return bool(text_words & common_words)
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Extract context window around a position"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def _filter_and_score_candidates(self, 
                                    candidates: List[EntityCandidate],
                                    text: str) -> List[EntityCandidate]:
        """Filter and score candidates"""
        # Remove duplicates and overlaps
        candidates = self._remove_duplicates_and_overlaps(candidates)
        
        # Apply additional filtering
        filtered = []
        for candidate in candidates:
            if self._is_valid_candidate(candidate, text):
                # Recalculate confidence with additional features
                candidate.confidence = self._recalculate_confidence(candidate, text)
                if candidate.confidence >= self.min_confidence:
                    filtered.append(candidate)
        
        # Sort by confidence
        filtered.sort(key=lambda c: c.confidence, reverse=True)
        
        return filtered
    
    def _remove_duplicates_and_overlaps(self, candidates: List[EntityCandidate]) -> List[EntityCandidate]:
        """Remove duplicate and overlapping candidates"""
        if not candidates:
            return candidates
        
        # Sort by position
        candidates.sort(key=lambda c: (c.start, c.end))
        
        filtered = []
        
        for candidate in candidates:
            # Check for overlaps with existing candidates
            overlaps = False
            
            for existing in filtered:
                if (candidate.start < existing.end and candidate.end > existing.start):
                    # Overlap detected - keep the one with higher confidence
                    if candidate.confidence > existing.confidence:
                        filtered.remove(existing)
                        break
                    else:
                        overlaps = True
                        break
            
            if not overlaps:
                filtered.append(candidate)
        
        return filtered
    
    def _is_valid_candidate(self, candidate: EntityCandidate, text: str) -> bool:
        """Validate candidate based on various criteria"""
        # Basic length check
        if len(candidate.text.strip()) < 2:
            return False
        
        # Check for too many special characters
        special_chars = sum(1 for c in candidate.text if not c.isalnum() and c != ' ')
        if special_chars > len(candidate.text) * 0.3:
            return False
        
        # Check for reasonable word count
        if candidate.word_count > 6:
            return False
        
        # Check for all lowercase (unless it's a specific type)
        if (candidate.text.islower() and 
            candidate.candidate_type not in ['quoted_text', 'context_driven']):
            return False
        
        return True
    
    def _recalculate_confidence(self, candidate: EntityCandidate, text: str) -> float:
        """Recalculate confidence with additional features"""
        base_confidence = candidate.confidence
        
        # Adjust based on position (entities at start/end might be less reliable)
        text_position = candidate.start / len(text)
        if text_position < 0.1 or text_position > 0.9:
            base_confidence *= 0.95
        
        # Adjust based on surrounding punctuation
        before_char = text[candidate.start - 1] if candidate.start > 0 else ' '
        after_char = text[candidate.end] if candidate.end < len(text) else ' '
        
        if before_char in '.,;:' or after_char in '.,;:':
            base_confidence *= 1.05  # Slight boost for punctuation boundaries
        
        return min(1.0, base_confidence)
    
    def clear_cache(self):
        """Clear candidate cache"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics"""
        stats = self.stats.copy()
        
        if self.stats["processing_times"]:
            stats["avg_processing_time"] = sum(self.stats["processing_times"]) / len(self.stats["processing_times"])
            stats["max_processing_time"] = max(self.stats["processing_times"])
        else:
            stats["avg_processing_time"] = 0.0
            stats["max_processing_time"] = 0.0
        
        stats["cache_stats"] = self.cache.get_stats()
        
        return stats


# Example usage
if __name__ == "__main__":
    import asyncio
    import yaml
    
    async def test_candidate_generator():
        # Load test configuration
        with open("/srv/luris/be/entity-extraction-service/config/cales_config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract entity types
        entity_types = []
        for category, types in config['entity_types'].items():
            entity_types.extend(types[:5])  # Take first 5 from each category
        
        generator = EntityCandidateGenerator(entity_types)
        
        test_text = """
        The plaintiff, John Smith, filed a complaint against ABC Corporation
        in the Superior Court of California. Judge Mary Johnson presided over
        the case, which involved a breach of contract claim regarding a
        "software licensing agreement" worth $500,000. Attorney Jane Doe
        represents the plaintiff, while the defendant is represented by
        the law firm of Wilson & Associates LLP.
        """
        
        candidates = await generator.generate_candidates(
            test_text, 
            entity_types,
            ProcessingMode.COMPREHENSIVE
        )
        
        print(f"Generated {len(candidates)} candidates:")
        for candidate in candidates:
            print(f"  {candidate.text} -> {candidate.candidate_type} (conf: {candidate.confidence:.2f})")
        
        print(f"Statistics: {generator.get_stats()}")
    
    asyncio.run(test_candidate_generator())