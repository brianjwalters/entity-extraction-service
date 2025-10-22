"""
Advanced semantic chunking strategy with intelligent boundary detection.

Implements Phase 2 features:
- BoundaryDetector for semantic, paragraph, and sentence boundaries
- EntityPositionMapper for precise entity location tracking
- ChunkQualityScorer for multi-dimensional quality assessment
- Configurable boundary types and intelligent size optimization
"""

import asyncio
import re
import spacy
import time
from typing import List, Dict, Any, Optional, Union, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import uuid

# CLAUDE.md Compliant: Absolute imports only
from src.core.chunking.strategies.base_chunker import BaseChunker
from src.models.responses import DocumentChunk
from src.core.chunking.async_spacy_wrapper import AsyncSpacyWrapper, CircuitConfig

logger = logging.getLogger(__name__)


class BoundaryType(str, Enum):
    """Types of boundaries for chunking."""
    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    FIXED = "fixed"


@dataclass
class Boundary:
    """Represents a text boundary."""
    position: int
    boundary_type: BoundaryType
    strength: float  # 0.0 to 1.0, higher is stronger boundary
    metadata: Dict[str, Any]


@dataclass
class EntityPosition:
    """Represents an entity position within a chunk."""
    entity_type: str
    text: str
    start_char: int  # Relative to chunk start
    end_char: int    # Relative to chunk start
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class QualityMetrics:
    """Quality assessment metrics for a chunk."""
    completeness: float      # 0.0 to 1.0
    coherence: float        # 0.0 to 1.0
    entity_density: float   # 0.0 to 1.0
    boundary_quality: float # 0.0 to 1.0
    size_optimality: float  # 0.0 to 1.0
    overall_score: float    # 0.0 to 1.0
    

class BoundaryDetector:
    """Detects various types of text boundaries with confidence scores."""
    
    def __init__(self):
        # Initialize AsyncSpacyWrapper with optimized performance configuration
        config = CircuitConfig(
            failure_threshold=3,          # Optimized for faster detection
            recovery_timeout=30.0,        # Stable recovery period
            operation_timeout=12.0,       # Aligned with system hierarchy
            max_text_length=10000,
            consecutive_success_threshold=3,  # More reliable recovery
            enable_progressive_timeouts=True,  # Enable progressive timeouts
            progressive_timeouts=[8.0, 15.0, 30.0],  # Aligned with system hierarchy
            similarity_timeout=8.0,       # Aligned with base timeout
            # Enhanced recovery configuration
            recovery_backoff_factor=1.5,
            max_recovery_attempts=5,
            extended_recovery_timeout=300.0,
            # Performance tuning
            enable_auto_tuning=True,
            performance_window=100,
            target_success_rate=0.95
        )
        self.spacy_wrapper = AsyncSpacyWrapper(config)
        
        self._legal_patterns = {
            'section_header': re.compile(r'^\s*(?:§|Section|Part|Chapter)\s+\d+', re.MULTILINE | re.IGNORECASE),
            'citation': re.compile(r'\d+\s+[A-Za-z.]+\s+\d+|\d+\s+U\.S\.C?\.\s*§?\s*\d+'),
            'subsection': re.compile(r'^\s*\([a-z0-9]+\)', re.MULTILINE),
            'numbered_list': re.compile(r'^\s*\d+\.\s+', re.MULTILINE),
            'legal_conclusion': re.compile(r'\b(?:HELD|CONCLUSION|RULING|ORDER)\b', re.IGNORECASE),
            'paragraph_break': re.compile(r'\n\s*\n'),
            'topic_shift': re.compile(r'\b(?:however|moreover|furthermore|nevertheless|therefore)\b', re.IGNORECASE)
        }
        
    async def initialize(self):
        """Initialize spaCy wrapper with comprehensive hanging prevention."""
        return await self.spacy_wrapper.initialize()
    
    async def detect_boundaries(self, text: str, boundary_types: List[BoundaryType]) -> List[Boundary]:
        """Detect all specified boundary types in text."""
        boundaries = []
        
        for boundary_type in boundary_types:
            if boundary_type == BoundaryType.SEMANTIC:
                semantic_boundaries = await self._detect_semantic_boundaries(text)
                boundaries.extend(semantic_boundaries)
            elif boundary_type == BoundaryType.PARAGRAPH:
                boundaries.extend(self._detect_paragraph_boundaries(text))
            elif boundary_type == BoundaryType.SENTENCE:
                sentence_boundaries = await self._detect_sentence_boundaries(text)
                boundaries.extend(sentence_boundaries)
        
        # Sort by position and remove duplicates
        boundaries.sort(key=lambda b: b.position)
        return self._deduplicate_boundaries(boundaries)
    
    async def _detect_semantic_boundaries(self, text: str) -> List[Boundary]:
        """Detect semantic boundaries using NLP analysis with optimized timeout hierarchy."""
        boundaries = []
        
        # Always include heuristic boundaries as baseline
        heuristic_boundaries = self._detect_heuristic_semantic_boundaries(text)
        boundaries.extend(heuristic_boundaries)
        
        # Try spaCy analysis using AsyncSpacyWrapper with optimized timeout
        try:
            # Use hierarchical timeout aligned with system architecture
            doc = await asyncio.wait_for(
                self.spacy_wrapper.process_text(text),
                timeout=12.0  # Aligned with boundary detection sub-operation timeout
            )
        except asyncio.TimeoutError:
            logger.debug("Document processing timed out after 12s, using enhanced heuristic boundaries")
            doc = None
        except Exception as e:
            logger.debug(f"Document processing failed: {e}, using enhanced heuristic boundaries")
            doc = None
        
        if doc is not None:
            try:
                # Detect topic shifts based on semantic similarity
                sentences = list(doc.sents)
                spacy_boundary_count = 0
                
                for i in range(1, len(sentences)):
                    prev_sent = sentences[i-1]
                    curr_sent = sentences[i]
                    
                    # Calculate semantic similarity with comprehensive protection
                    try:
                        similarity = await self.spacy_wrapper.compute_similarity_protected(prev_sent, curr_sent)
                        
                        # Validate similarity result
                        if similarity is None or not isinstance(similarity, (int, float)):
                            similarity = 0.5  # Default neutral similarity
                        else:
                            similarity = float(similarity)
                        
                        # Lower similarity indicates potential topic shift
                        if similarity < 0.3:  # Threshold for topic shift
                            strength = max(0.1, min(1.0, 1.0 - similarity))  # Ensure valid range
                            boundaries.append(Boundary(
                                position=curr_sent.start_char,
                                boundary_type=BoundaryType.SEMANTIC,
                                strength=strength,
                                metadata={'similarity': similarity, 'method': 'spacy_async_protected'}
                            ))
                            spacy_boundary_count += 1
                    except Exception as sim_e:
                        logger.debug(f"Protected similarity calculation failed: {sim_e}")
                        # Add heuristic boundary at sentence position as fallback
                        boundaries.append(Boundary(
                            position=curr_sent.start_char,
                            boundary_type=BoundaryType.SEMANTIC,
                            strength=0.4,  # Lower strength for fallback
                            metadata={'method': 'heuristic_fallback', 'reason': str(sim_e)}
                        ))
                        continue
                        
                logger.debug(f"✅ spaCy semantic analysis completed, found {spacy_boundary_count} semantic boundaries")
                
            except Exception as e:
                logger.warning(f"spaCy semantic analysis failed during processing: {e}")
        else:
            logger.debug("🔄 Using regex-only semantic boundaries (spaCy unavailable)")
        
        return boundaries
    
    def _detect_heuristic_semantic_boundaries(self, text: str) -> List[Boundary]:
        """Detect semantic boundaries using enhanced heuristic patterns."""
        boundaries = []
        
        # Legal document structure patterns with enhanced scoring
        pattern_weights = {
            'section_header': 0.9,     # Strongest boundaries
            'legal_conclusion': 0.85,  # Strong topic boundaries
            'citation': 0.7,           # Citation boundaries
            'subsection': 0.75,        # Subsection boundaries
            'numbered_list': 0.6,      # List item boundaries
            'paragraph_break': 0.5,    # Basic paragraph boundaries
            'topic_shift': 0.65        # Transition word boundaries
        }
        
        for pattern_name, pattern in self._legal_patterns.items():
            strength = pattern_weights.get(pattern_name, 0.6)
            
            for match in pattern.finditer(text):
                # Additional context-based scoring
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end]
                
                # Boost strength for certain contexts
                if pattern_name == 'section_header' and any(word in context.lower() for word in ['whereas', 'therefore', 'held']):
                    strength += 0.1
                elif pattern_name == 'citation' and 'see also' in context.lower():
                    strength += 0.05
                
                boundaries.append(Boundary(
                    position=match.start(),
                    boundary_type=BoundaryType.SEMANTIC,
                    strength=min(1.0, strength),
                    metadata={
                        'pattern': pattern_name, 
                        'method': 'heuristic',
                        'context_boosted': strength > pattern_weights.get(pattern_name, 0.6)
                    }
                ))
        
        return boundaries
    
    def _detect_paragraph_boundaries(self, text: str) -> List[Boundary]:
        """Detect paragraph boundaries."""
        boundaries = []
        pattern = re.compile(r'\n\s*\n')
        
        for match in pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.end(),
                boundary_type=BoundaryType.PARAGRAPH,
                strength=0.7,
                metadata={'method': 'regex'}
            ))
        
        return boundaries
    
    async def _detect_sentence_boundaries(self, text: str) -> List[Boundary]:
        """Detect sentence boundaries with async spaCy wrapper and fallback protection."""
        boundaries = []
        
        # Always get regex boundaries as fallback
        regex_boundaries = self._detect_regex_sentence_boundaries(text)
        boundaries.extend(regex_boundaries)
        
        # Try spaCy using AsyncSpacyWrapper with circuit breaker
        doc = await self.spacy_wrapper.process_text(text)
        
        if doc is not None:
            try:
                spacy_boundaries = []
                for sent in doc.sents:
                    if sent.end_char < len(text):
                        spacy_boundaries.append(Boundary(
                            position=sent.end_char,
                            boundary_type=BoundaryType.SENTENCE,
                            strength=0.6,  # Slightly higher than regex
                            metadata={'method': 'spacy_async'}
                        ))
                
                # Merge spaCy boundaries with regex boundaries, preferring spaCy
                boundaries.extend(spacy_boundaries)
                logger.debug(f"✅ spaCy sentence detection completed, found {len(spacy_boundaries)} sentences")
                
            except Exception as e:
                logger.warning(f"spaCy sentence processing failed during boundary detection: {e}")
        else:
            logger.debug("🔄 Using regex-only sentence boundaries (spaCy circuit open or timed out)")
        
        return boundaries
    
    def _detect_regex_sentence_boundaries(self, text: str) -> List[Boundary]:
        """Detect sentence boundaries using regex."""
        boundaries = []
        pattern = re.compile(r'[.!?]+\s+')
        
        for match in pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.end(),
                boundary_type=BoundaryType.SENTENCE,
                strength=0.4,
                metadata={'method': 'regex'}
            ))
        
        return boundaries
    
    def _deduplicate_boundaries(self, boundaries: List[Boundary]) -> List[Boundary]:
        """Remove duplicate boundaries, keeping the strongest one."""
        if not boundaries:
            return boundaries
        
        deduplicated = []
        current_pos = -1
        current_boundary = None
        
        for boundary in boundaries:
            if boundary.position != current_pos:
                if current_boundary:
                    deduplicated.append(current_boundary)
                current_boundary = boundary
                current_pos = boundary.position
            else:
                # Keep the stronger boundary
                if boundary.strength > current_boundary.strength:
                    current_boundary = boundary
        
        if current_boundary:
            deduplicated.append(current_boundary)
        
        return deduplicated


class EntityPositionMapper:
    """Maps entity positions within chunks for precise location tracking."""
    
    def __init__(self):
        # Initialize AsyncSpacyWrapper with entity-specific optimized config
        config = CircuitConfig(
            failure_threshold=3,          # Optimized for faster detection
            recovery_timeout=30.0,        # Stable recovery period
            operation_timeout=10.0,       # Entity processing timeout
            max_text_length=3000,         # Smaller text limit for entities
            consecutive_success_threshold=3,  # More reliable recovery
            enable_progressive_timeouts=True,  # Enable progressive timeouts
            progressive_timeouts=[6.0, 10.0, 15.0],  # Entity-specific progressive values
            similarity_timeout=6.0,       # Entity similarity timeout
            # Enhanced recovery configuration
            recovery_backoff_factor=1.5,
            max_recovery_attempts=5,
            extended_recovery_timeout=300.0,
            # Performance tuning
            enable_auto_tuning=True,
            performance_window=100,
            target_success_rate=0.95
        )
        self.spacy_wrapper = AsyncSpacyWrapper(config)
        
        self._legal_entity_patterns = {
            'case_citation': re.compile(r'\d+\s+[A-Za-z.]+\s+\d+'),
            'statute': re.compile(r'\d+\s+U\.S\.C?\.\s*§?\s*\d+'),
            'code_section': re.compile(r'§\s*\d+(?:\.\d+)*'),
            'court_name': re.compile(r'(?:Supreme Court|Court of Appeals|District Court)'),
            'judge_name': re.compile(r'Justice\s+[A-Z][a-z]+|Judge\s+[A-Z][a-z]+'),
            'party_name': re.compile(r'\b[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+', re.IGNORECASE),
            'legal_term': re.compile(r'\b(?:plaintiff|defendant|appellant|appellee|petitioner|respondent)\b', re.IGNORECASE),
            'date_reference': re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'),
            'monetary_amount': re.compile(r'\$[\d,]+(?:\.\d{2})?')
        }
    
    async def initialize(self):
        """Initialize spaCy wrapper for entity recognition with hanging prevention."""
        return await self.spacy_wrapper.initialize()
    
    async def map_entities(self, chunk_content: str, original_start: int) -> List[EntityPosition]:
        """Map all entities within a chunk with relative positions using async spaCy wrapper."""
        entities = []
        
        # Legal pattern-based entities (always available)
        entities.extend(self._extract_legal_entities(chunk_content))
        
        # NLP-based entities with circuit breaker protection
        nlp_entities = await self._extract_nlp_entities_async(chunk_content)
        entities.extend(nlp_entities)
        
        return entities
    
    def _extract_legal_entities(self, text: str) -> List[EntityPosition]:
        """Extract legal entities using pattern matching."""
        entities = []
        
        for entity_type, pattern in self._legal_entity_patterns.items():
            for match in pattern.finditer(text):
                entities.append(EntityPosition(
                    entity_type=entity_type,
                    text=match.group(),
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=0.8,
                    metadata={'method': 'pattern', 'pattern': entity_type}
                ))
        
        return entities
    
    async def _extract_nlp_entities_async(self, text: str) -> List[EntityPosition]:
        """Extract entities using AsyncSpacyWrapper with comprehensive hanging prevention."""
        entities = []
        
        # Process text using AsyncSpacyWrapper with circuit breaker
        doc = await self.spacy_wrapper.process_text(text)
        
        if doc is not None:
            try:
                for ent in doc.ents:
                    # Filter for relevant entity types
                    if ent.label_ in ['PERSON', 'ORG', 'DATE', 'MONEY', 'LAW', 'GPE', 'CARDINAL']:
                        entities.append(EntityPosition(
                            entity_type=ent.label_,
                            text=ent.text.strip(),
                            start_char=ent.start_char,
                            end_char=ent.end_char,
                            confidence=0.8,  # Confidence for auto-detected entities
                            metadata={'method': 'spacy_async', 'label': ent.label_}
                        ))
                        
                logger.debug(f"✅ spaCy entity extraction completed, found {len(entities)} entities")
                
            except Exception as e:
                logger.warning(f"spaCy entity processing failed during extraction: {e}")
        else:
            logger.debug("🔄 Using regex-only entities (spaCy circuit open or timed out)")
        
        return entities


class ChunkQualityScorer:
    """Assesses chunk quality across multiple dimensions."""
    
    def __init__(self):
        self.entity_mapper = EntityPositionMapper()
    
    async def initialize(self):
        """Initialize the quality scorer."""
        await self.entity_mapper.initialize()
    
    async def score_chunk(
        self,
        content: str,
        boundaries: List[Boundary],
        target_size: int,
        entities: Optional[List[EntityPosition]] = None
    ) -> QualityMetrics:
        """Calculate comprehensive quality metrics for a chunk."""
        
        if entities is None:
            entities = await self.entity_mapper.map_entities(content, 0)
        
        completeness = self._score_completeness(content) or 0.5
        coherence = self._score_coherence(content) or 0.5
        entity_density = self._score_entity_density(content, entities) or 0.5
        boundary_quality = self._score_boundary_quality(content, boundaries) or 0.5
        size_optimality = self._score_size_optimality(len(content), target_size) or 0.5
        
        # Ensure all scores are valid numbers
        scores = [completeness, coherence, entity_density, boundary_quality, size_optimality]
        valid_scores = [max(0.0, min(1.0, float(s))) for s in scores if s is not None]
        
        if len(valid_scores) != len(scores):
            # Some scores were invalid, use defaults
            valid_scores = [0.5, 0.5, 0.5, 0.5, 0.5]
            completeness, coherence, entity_density, boundary_quality, size_optimality = valid_scores
        
        # Weighted overall score
        overall_score = (
            completeness * 0.25 +
            coherence * 0.25 +
            entity_density * 0.2 +
            boundary_quality * 0.2 +
            size_optimality * 0.1
        )
        
        return QualityMetrics(
            completeness=completeness,
            coherence=coherence,
            entity_density=entity_density,
            boundary_quality=boundary_quality,
            size_optimality=size_optimality,
            overall_score=overall_score
        )
    
    def _score_completeness(self, content: str) -> float:
        """Score how complete/self-contained the chunk is."""
        score = 1.0
        
        # Check for complete sentences
        if not content.strip().endswith(('.', '!', '?')):
            score -= 0.3
        
        # Check for sentence fragments at the beginning
        if content.strip().startswith(('and', 'or', 'but', 'however')):
            score -= 0.2
        
        # Check for incomplete parentheses/quotes
        open_parens = content.count('(') - content.count(')')
        open_quotes = content.count('"') % 2
        if open_parens != 0 or open_quotes != 0:
            score -= 0.2
        
        return max(0.0, score)
    
    def _score_coherence(self, content: str) -> float:
        """Score the internal coherence of the chunk."""
        try:
            # Simple heuristics for coherence
            words = content.split()
            if len(words) < 5:
                return 0.3
            
            # Check for topic consistency (basic keyword overlap)
            sentences = re.split(r'[.!?]+', content)
            if len(sentences) < 2:
                return 0.8
            
            # Calculate word overlap between sentences (simple coherence measure)
            overlaps = []
            for i in range(len(sentences) - 1):
                words1 = set(sentences[i].lower().split())
                words2 = set(sentences[i + 1].lower().split())
                if words1 and words2:
                    overlap = len(words1.intersection(words2)) / len(words1.union(words2))
                    overlaps.append(overlap)
            
            if overlaps:
                avg_overlap = sum(overlaps) / len(overlaps)
                # Ensure valid range [0, 1]
                return max(0.0, min(1.0, avg_overlap))
            else:
                return 0.5
                
        except Exception as e:
            logger.debug(f"Coherence scoring failed: {e}, using default")
            return 0.5
    
    def _score_entity_density(self, content: str, entities: List[EntityPosition]) -> float:
        """Score based on entity density (legal documents should have entities)."""
        if not content:
            return 0.0
        
        entity_chars = sum(len(entity.text) for entity in entities)
        density = entity_chars / len(content)
        
        # Optimal density is around 10-20% for legal documents
        if density < 0.05:
            return density * 4  # Scale up low densities
        elif density > 0.3:
            return 1.0 - (density - 0.3) * 2  # Penalize very high densities
        else:
            return min(1.0, density * 5)  # Reward moderate densities
    
    def _score_boundary_quality(self, content: str, boundaries: List[Boundary]) -> float:
        """Score the quality of chunk boundaries."""
        if not boundaries:
            return 0.5
        
        # Average boundary strength
        avg_strength = sum(b.strength for b in boundaries) / len(boundaries)
        return avg_strength
    
    def _score_size_optimality(self, actual_size: int, target_size: int) -> float:
        """Score how close the chunk size is to the target."""
        if target_size == 0:
            return 1.0
        
        ratio = actual_size / target_size
        
        # Optimal range is 80% to 120% of target
        if 0.8 <= ratio <= 1.2:
            return 1.0
        elif 0.6 <= ratio < 0.8 or 1.2 < ratio <= 1.5:
            return 0.7
        elif 0.4 <= ratio < 0.6 or 1.5 < ratio <= 2.0:
            return 0.4
        else:
            return 0.1


class SemanticChunker(BaseChunker):
    """Advanced semantic chunking with intelligent boundary detection."""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.boundary_detector = BoundaryDetector()
        self.entity_mapper = EntityPositionMapper()
        self.quality_scorer = ChunkQualityScorer()
        
        # Default configuration
        self.default_boundary_types = [BoundaryType.SEMANTIC, BoundaryType.PARAGRAPH, BoundaryType.SENTENCE]
        self.min_chunk_size = 200
        self.max_chunk_size = 2000
    
    async def initialize(self):
        """Initialize all components."""
        await super().initialize()
        await self.boundary_detector.initialize()
        await self.entity_mapper.initialize()
        await self.quality_scorer.initialize()
        logger.debug("SemanticChunker Phase 2 initialized successfully")
    
    async def chunk_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Advanced semantic chunking with intelligent boundary detection.
        
        Features:
        - Multi-type boundary detection (semantic, paragraph, sentence)
        - Entity-aware positioning
        - Quality-based optimization
        - Legal document awareness
        - Configurable chunking strategies
        """
        # Optimized progressive timeout strategy aligned with system hierarchy
        timeouts = [8.0, 15.0, 30.0]  # Aligned with AsyncSpacyWrapper timeouts
        
        for attempt, timeout in enumerate(timeouts):
            try:
                logger.debug(f"Attempting semantic chunking (attempt {attempt + 1}/{len(timeouts)}, timeout: {timeout}s)")
                
                # Track timing for performance analysis
                start_time = time.time()
                
                result = await asyncio.wait_for(
                    self._chunk_text_internal(text, chunk_size, chunk_overlap, metadata),
                    timeout=timeout
                )
                
                processing_time = time.time() - start_time
                
                # Validate result
                if result and all(isinstance(chunk, DocumentChunk) for chunk in result):
                    logger.info(f"✅ Semantic chunking succeeded on attempt {attempt + 1} in {processing_time:.2f}s")
                    return result
                else:
                    logger.warning(f"Invalid chunking result on attempt {attempt + 1} after {processing_time:.2f}s, retrying...")
                    continue
                    
            except asyncio.TimeoutError:
                if attempt < len(timeouts) - 1:
                    logger.warning(f"Semantic chunking timed out after {timeout}s, retrying with longer timeout...")
                    continue
                else:
                    logger.warning(f"Semantic chunking timed out after all attempts, falling back to simple chunking")
                    # Fallback to simple chunking
                    return await self._create_simple_fallback_chunks(text, chunk_size, chunk_overlap, metadata)
            except Exception as e:
                logger.error(f"Semantic chunking failed on attempt {attempt + 1}: {e}")
                if attempt < len(timeouts) - 1:
                    continue
                else:
                    # Final fallback
                    return await self._create_simple_fallback_chunks(text, chunk_size, chunk_overlap, metadata)
        
        # Should not reach here, but provide fallback
        return await self._create_simple_fallback_chunks(text, chunk_size, chunk_overlap, metadata)
    
    async def _chunk_text_internal(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Internal chunking method with timeout protection."""
        self._validate_parameters(text, chunk_size, chunk_overlap)
        
        # Extract configuration from metadata
        config = self._extract_chunking_config(metadata)
        boundary_types = config.get('boundary_types', self.default_boundary_types)
        
        # Detect all boundaries
        boundaries = await self.boundary_detector.detect_boundaries(text, boundary_types)
        logger.debug(f"Detected {len(boundaries)} boundaries of types: {boundary_types}")
        
        # Create chunks using intelligent boundary selection
        chunks = await self._create_intelligent_chunks(
            text=text,
            boundaries=boundaries,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            config=config
        )
        
        # Apply quality scoring and optimization
        chunks = await self._optimize_chunks_by_quality(chunks, chunk_size, config)
        
        # Add comprehensive metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'chunking_strategy': 'semantic_v2',
                'phase': 2,
                'boundary_types_used': [bt.value for bt in boundary_types],
                'quality_optimized': True
            })
        
        logger.info(f"SemanticChunker Phase 2 created {len(chunks)} high-quality chunks")
        return chunks
    
    def _extract_chunking_config(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract chunking configuration from metadata."""
        if not metadata:
            return {}
        
        config = {}
        
        # Boundary type configuration
        if 'boundary_types' in metadata:
            boundary_types = []
            for bt in metadata['boundary_types']:
                try:
                    boundary_types.append(BoundaryType(bt))
                except ValueError:
                    logger.warning(f"Invalid boundary type: {bt}")
            config['boundary_types'] = boundary_types
        
        # Quality thresholds
        config['min_quality_score'] = metadata.get('min_quality_score', 0.6)
        config['optimize_for_entities'] = metadata.get('optimize_for_entities', True)
        config['preserve_legal_structure'] = metadata.get('preserve_legal_structure', True)
        
        return config
    
    async def _create_intelligent_chunks(
        self,
        text: str,
        boundaries: List[Boundary],
        chunk_size: int,
        chunk_overlap: int,
        config: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Create chunks using intelligent boundary selection."""
        if not boundaries:
            # Fallback to fixed-size chunking
            return await self._create_fixed_chunks(text, chunk_size, chunk_overlap)
        
        chunks = []
        chunk_index = 0
        current_start = 0
        
        # Sort boundaries by position
        boundaries.sort(key=lambda b: b.position)
        
        while current_start < len(text):
            # Find the best chunk end position
            chunk_end = await self._find_optimal_chunk_end(
                text=text,
                start_pos=current_start,
                target_size=chunk_size,
                boundaries=boundaries,
                config=config
            )
            
            if chunk_end <= current_start:
                break
            
            # Extract chunk content
            chunk_content = text[current_start:chunk_end].strip()
            
            if chunk_content:
                # Map entities within this chunk
                entities = await self.entity_mapper.map_entities(chunk_content, current_start)
                
                # Create chunk with enhanced metadata
                chunk = await self._create_enhanced_chunk(
                    content=chunk_content,
                    start_position=current_start,
                    end_position=chunk_end,
                    chunk_index=chunk_index,
                    entities=entities,
                    boundaries=self._get_chunk_boundaries(boundaries, current_start, chunk_end),
                    target_size=chunk_size
                )
                
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next chunk with overlap
            if chunk_overlap > 0:
                # Ensure overlap doesn't create negative positions
                current_start = max(0, chunk_end - chunk_overlap)
            else:
                current_start = chunk_end
            
            # Ensure we make progress
            if current_start >= chunk_end:
                current_start = chunk_end
        
        return chunks
    
    async def _find_optimal_chunk_end(
        self,
        text: str,
        start_pos: int,
        target_size: int,
        boundaries: List[Boundary],
        config: Dict[str, Any]
    ) -> int:
        """Find the optimal end position for a chunk."""
        ideal_end = start_pos + target_size
        
        if ideal_end >= len(text):
            return len(text)
        
        # Find boundaries within reasonable range of ideal end
        candidate_boundaries = []
        search_range = target_size // 4  # 25% flexibility
        
        for boundary in boundaries:
            if (ideal_end - search_range) <= boundary.position <= (ideal_end + search_range):
                candidate_boundaries.append(boundary)
        
        if not candidate_boundaries:
            # No good boundaries found, use word boundary
            return self._find_word_boundary(text, ideal_end)
        
        # Score each candidate boundary
        best_boundary = max(
            candidate_boundaries,
            key=lambda b: self._score_boundary_position(
                boundary=b,
                ideal_pos=ideal_end,
                start_pos=start_pos,
                target_size=target_size
            )
        )
        
        return best_boundary.position
    
    def _score_boundary_position(
        self,
        boundary: Boundary,
        ideal_pos: int,
        start_pos: int,
        target_size: int
    ) -> float:
        """Score a boundary position for chunking quality."""
        # Distance penalty (closer to ideal is better)
        distance = abs(boundary.position - ideal_pos)
        distance_score = 1.0 - (distance / target_size)
        
        # Boundary strength bonus
        strength_score = boundary.strength
        
        # Size penalty for very small chunks
        chunk_size = boundary.position - start_pos
        size_score = 1.0 if chunk_size >= self.min_chunk_size else chunk_size / self.min_chunk_size
        
        # Combined score
        return (distance_score * 0.4) + (strength_score * 0.4) + (size_score * 0.2)
    
    def _find_word_boundary(self, text: str, position: int) -> int:
        """Find nearest word boundary to avoid cutting words."""
        if position >= len(text):
            return len(text)
        
        # Look backward for whitespace
        while position > 0 and not text[position].isspace():
            position -= 1
        
        return position
    
    def _get_chunk_boundaries(self, boundaries: List[Boundary], start: int, end: int) -> List[Boundary]:
        """Get boundaries that fall within chunk range."""
        return [b for b in boundaries if start <= b.position <= end]
    
    async def _create_enhanced_chunk(
        self,
        content: str,
        start_position: int,
        end_position: int,
        chunk_index: int,
        entities: List[EntityPosition],
        boundaries: List[Boundary],
        target_size: int
    ) -> DocumentChunk:
        """Create a chunk with enhanced metadata and quality scoring."""
        
        # Calculate quality metrics
        quality_metrics = await self.quality_scorer.score_chunk(
            content=content,
            boundaries=boundaries,
            target_size=target_size,
            entities=entities
        )
        
        # Prepare enhanced metadata
        enhanced_metadata = {
            'entities': [{
                'type': e.entity_type,
                'text': e.text,
                'start_char': e.start_char,
                'end_char': e.end_char,
                'confidence': e.confidence,
                'metadata': e.metadata
            } for e in entities],
            'boundaries': [{
                'position': b.position - start_position,  # Relative to chunk
                'type': b.boundary_type.value,
                'strength': b.strength,
                'metadata': b.metadata
            } for b in boundaries],
            'quality': {
                'completeness': quality_metrics.completeness,
                'coherence': quality_metrics.coherence,
                'entity_density': quality_metrics.entity_density,
                'boundary_quality': quality_metrics.boundary_quality,
                'size_optimality': quality_metrics.size_optimality,
                'overall_score': quality_metrics.overall_score
            }
        }
        
        # Create chunk with all enhancements
        chunk = self._create_chunk(
            content=content,
            start_position=start_position,
            end_position=end_position,
            chunk_index=chunk_index,
            metadata=enhanced_metadata
        )
        
        # Set additional fields
        chunk.quality_score = quality_metrics.overall_score
        chunk.sentence_count = len(re.findall(r'[.!?]+', content))
        chunk.word_count = len(content.split())
        chunk.boundary_info = {
            'boundary_count': len(boundaries),
            'strongest_boundary': max(boundaries, key=lambda b: b.strength).boundary_type.value if boundaries else None,
            'avg_boundary_strength': sum(b.strength for b in boundaries) / len(boundaries) if boundaries else 0.0
        }
        
        return chunk
    
    async def _optimize_chunks_by_quality(
        self,
        chunks: List[DocumentChunk],
        target_size: int,
        config: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Optimize chunks based on quality metrics."""
        min_quality = config.get('min_quality_score', 0.6)
        optimized_chunks = []
        
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            
            # Check if chunk meets quality threshold
            chunk_quality = getattr(chunk, 'quality_score', 0.6)
            # Handle None values safely
            if chunk_quality is None:
                chunk_quality = 0.6  # Default quality score
            
            if chunk_quality >= min_quality:
                optimized_chunks.append(chunk)
                i += 1
                continue
            
            # Try to improve low-quality chunks
            improved_chunks = await self._improve_chunk_quality(
                chunk=chunk,
                next_chunk=chunks[i + 1] if i + 1 < len(chunks) else None,
                target_size=target_size,
                config=config
            )
            
            optimized_chunks.extend(improved_chunks)
            
            # Skip next chunk if it was merged
            if len(improved_chunks) == 1 and i + 1 < len(chunks):
                i += 2  # Skip merged chunk
            else:
                i += 1
        
        logger.debug(f"Quality optimization: {len(chunks)} -> {len(optimized_chunks)} chunks")
        return optimized_chunks
    
    async def _improve_chunk_quality(
        self,
        chunk: DocumentChunk,
        next_chunk: Optional[DocumentChunk],
        target_size: int,
        config: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Improve chunk quality through merging or splitting."""
        
        # If chunk is too small and incomplete, try merging with next
        if (chunk.character_count < target_size // 2 and 
            next_chunk and 
            chunk.character_count + next_chunk.character_count <= target_size * 1.5):
            
            return [await self._merge_chunks(chunk, next_chunk, target_size)]
        
        # If chunk is too large with low coherence, try splitting
        quality = chunk.metadata.get('quality', {})
        if (chunk.character_count > target_size * 1.5 and 
            quality.get('coherence', 1.0) < 0.4):
            
            return await self._split_chunk_intelligently(chunk, target_size)
        
        # Return original chunk if no improvement possible
        return [chunk]
    
    async def _merge_chunks(self, chunk1: DocumentChunk, chunk2: DocumentChunk, target_size: int) -> DocumentChunk:
        """Merge two chunks intelligently."""
        merged_content = chunk1.content + " " + chunk2.content
        
        # Re-analyze merged content
        entities = await self.entity_mapper.map_entities(merged_content, chunk1.start_position)
        boundaries = []  # Would need to recalculate
        
        quality_metrics = await self.quality_scorer.score_chunk(
            content=merged_content,
            boundaries=boundaries,
            target_size=target_size,
            entities=entities
        )
        
        # Create merged chunk
        merged_chunk = self._create_chunk(
            content=merged_content,
            start_position=chunk1.start_position,
            end_position=chunk2.end_position,
            chunk_index=chunk1.chunk_index,
            metadata={
                'merged_from': [chunk1.chunk_id, chunk2.chunk_id],
                'quality': quality_metrics.__dict__
            }
        )
        
        merged_chunk.quality_score = quality_metrics.overall_score
        return merged_chunk
    
    async def _split_chunk_intelligently(self, chunk: DocumentChunk, target_size: int) -> List[DocumentChunk]:
        """Split a chunk at the best semantic boundary."""
        # For now, return the original chunk (splitting is complex)
        # In a full implementation, this would find the best split point
        return [chunk]
    
    async def _create_fixed_chunks(
        self, text: str, chunk_size: int, chunk_overlap: int
    ) -> List[DocumentChunk]:
        """Fallback to fixed-size chunking when no boundaries are found."""
        chunks = []
        positions = self._calculate_positions(text, chunk_size, chunk_overlap)
        
        for i, (start, end) in enumerate(positions):
            content = text[start:end].strip()
            if content:
                chunk = self._create_chunk(
                    content=content,
                    start_position=start,
                    end_position=end,
                    chunk_index=i,
                    metadata={'chunking_method': 'fixed_fallback'}
                )
                chunks.append(chunk)
        
        return chunks
    
    async def _create_simple_fallback_chunks(
        self, text: str, chunk_size: int, chunk_overlap: int, metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Create simple fallback chunks when semantic chunking fails."""
        chunks = []
        positions = self._calculate_positions(text, chunk_size, chunk_overlap)
        
        for i, (start, end) in enumerate(positions):
            content = text[start:end].strip()
            if content:
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=content,
                    start_position=start,
                    end_position=end,
                    chunk_index=i,
                    character_count=len(content),
                    word_count=len(content.split()),
                    sentence_count=len([s for s in content.split('.') if s.strip()]),
                    quality_score=0.6,  # Default quality for fallback
                    metadata={
                        'chunking_strategy': 'semantic_fallback',
                        'fallback_reason': 'timeout_or_error',
                        **(metadata or {})
                    },
                    boundary_info={
                        'starts_with_sentence': content[0].isupper() if content else False,
                        'ends_with_sentence': content.endswith('.') if content else False,
                        'has_complete_sentences': '.' in content
                    },
                    enhanced_content=None,
                    embedding_vector=None,
                    context_quality_score=None
                )
                chunks.append(chunk)
        
        return chunks
