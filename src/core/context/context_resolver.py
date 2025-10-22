"""
Context Resolver for CALES Entity Extraction Service

This module provides multi-stage context resolution combining pattern-based analysis,
semantic analysis with Legal-BERT, dependency parsing with SpaCy, and section-based analysis.
"""

import re
import logging
import torch
import numpy as np
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import spacy
from spacy.tokens import Doc, Token, Span
from transformers import AutoModel, AutoTokenizer
import nltk
from nltk.corpus import wordnet
from collections import defaultdict, Counter

# Import local modules
from .context_mappings import ContextMappings, ContextType, EntityContextMapping
from .context_window_extractor import (
    ContextWindowExtractor, 
    ContextWindow, 
    ExtractedEntity,
    WindowLevel
)

# Configure logging
logger = logging.getLogger(__name__)


class ContextResolutionMethod(Enum):
    """Methods used for context resolution"""
    PATTERN_BASED = "pattern_based"
    SEMANTIC = "semantic"
    DEPENDENCY = "dependency"
    SECTION_BASED = "section_based"
    HYBRID = "hybrid"


@dataclass
class ContextSignal:
    """Individual context signal from a resolution method"""
    method: ContextResolutionMethod
    confidence: float
    context_type: Optional[ContextType]
    evidence: Dict[str, Any]
    weight: float = 1.0


@dataclass
class ResolvedContext:
    """Final resolved context for an entity"""
    entity: ExtractedEntity
    primary_context: ContextType
    secondary_contexts: List[ContextType]
    confidence: float
    signals: List[ContextSignal]
    context_window: ContextWindow
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextResolver:
    """
    Multi-stage context resolver that combines multiple analysis methods
    to determine the contextual role of entities in legal documents.
    """
    
    def __init__(self,
                 dynamic_model_loader: Optional[Any] = None,
                 use_semantic_analysis: bool = True,
                 use_dependency_parsing: bool = True,
                 confidence_threshold: float = 0.6):
        """
        Initialize the context resolver.
        
        Args:
            dynamic_model_loader: Dynamic model loader for Legal-BERT and SpaCy
            use_semantic_analysis: Whether to use Legal-BERT for semantic analysis
            use_dependency_parsing: Whether to use SpaCy for dependency parsing
            confidence_threshold: Minimum confidence for context resolution
        """
        self.dynamic_model_loader = dynamic_model_loader
        self.use_semantic_analysis = use_semantic_analysis
        self.use_dependency_parsing = use_dependency_parsing
        self.confidence_threshold = confidence_threshold
        
        # Initialize components
        self.context_mappings = ContextMappings()
        self.window_extractor = ContextWindowExtractor()
        
        # Model containers
        self.legal_bert_model = None
        self.legal_bert_tokenizer = None
        self.spacy_model = None
        
        # Load models if available
        self._load_models()
        
        # Initialize pattern matchers
        self._init_pattern_matchers()
        
        # Weight configuration for signal combination
        self.method_weights = {
            ContextResolutionMethod.PATTERN_BASED: 0.3,
            ContextResolutionMethod.SEMANTIC: 0.35,
            ContextResolutionMethod.DEPENDENCY: 0.2,
            ContextResolutionMethod.SECTION_BASED: 0.15
        }
    
    def _load_models(self):
        """Load required models using dynamic model loader"""
        if self.dynamic_model_loader:
            try:
                # Load Legal-BERT for semantic analysis
                if self.use_semantic_analysis:
                    model_info = self.dynamic_model_loader.load_model(
                        model_id="legal-bert",
                        model_type="transformer",
                        task_type="embeddings"
                    )
                    if model_info:
                        self.legal_bert_model = model_info.model
                        self.legal_bert_tokenizer = model_info.tokenizer
                        logger.info("Loaded Legal-BERT for semantic analysis")
            except Exception as e:
                logger.warning(f"Could not load Legal-BERT: {e}")
                # Try fallback to base BERT
                try:
                    self.legal_bert_tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
                    self.legal_bert_model = AutoModel.from_pretrained("bert-base-uncased")
                    logger.info("Loaded base BERT as fallback")
                except Exception as e2:
                    logger.warning(f"Could not load fallback BERT: {e2}")
            
            try:
                # Load SpaCy for dependency parsing
                if self.use_dependency_parsing:
                    model_info = self.dynamic_model_loader.load_model(
                        model_id="spacy-legal",
                        model_type="spacy"
                    )
                    if model_info:
                        self.spacy_model = model_info.model
                        logger.info("Loaded SpaCy for dependency parsing")
            except Exception as e:
                logger.warning(f"Could not load SpaCy model: {e}")
                # Try fallback to base SpaCy
                try:
                    import spacy
                    self.spacy_model = spacy.load("en_core_web_sm")
                    logger.info("Loaded base SpaCy as fallback")
                except Exception as e2:
                    logger.warning(f"Could not load fallback SpaCy: {e2}")
    
    def _init_pattern_matchers(self):
        """Initialize regex patterns for context detection"""
        self.context_patterns = {
            ContextType.CASE_HEADER: [
                r"(?i)in\s+the\s+.*court",
                r"(?i)case\s+no\.?\s*:?\s*[\d\-]+",
                r"(?i)docket\s+no\.?\s*:?\s*[\d\-]+",
                r"(?i)before.*judge",
                r"(?i)plaintiff.*v\..*defendant"
            ],
            ContextType.PARTY_SECTION: [
                r"(?i)plaintiff[s]?\s*:?",
                r"(?i)defendant[s]?\s*:?",
                r"(?i)represented\s+by",
                r"(?i)attorney[s]?\s+for",
                r"(?i)counsel\s+for"
            ],
            ContextType.DATES_DEADLINES: [
                r"\d{1,2}/\d{1,2}/\d{2,4}",
                r"(?i)(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}",
                r"(?i)deadline",
                r"(?i)due\s+date",
                r"(?i)effective\s+date"
            ],
            ContextType.MONETARY: [
                r"\$[\d,]+(?:\.\d{2})?",
                r"(?i)dollars",
                r"(?i)amount",
                r"(?i)damages",
                r"(?i)compensation"
            ],
            ContextType.LEGAL_CITATIONS: [
                r"\d+\s+[A-Z]\.\d[a-z]+\s+\d+",
                r"\d+\s+U\.S\.C\.",
                r"\d+\s+C\.F\.R\.",
                r"(?i)citing",
                r"(?i)see\s+also"
            ],
            ContextType.PROCEDURAL: [
                r"(?i)motion\s+to",
                r"(?i)order",
                r"(?i)judgment",
                r"(?i)hearing",
                r"(?i)trial"
            ],
            ContextType.CONTRACTUAL: [
                r"(?i)agreement",
                r"(?i)contract",
                r"(?i)party",
                r"(?i)shall",
                r"(?i)terms\s+and\s+conditions"
            ],
            ContextType.CRIMINAL: [
                r"(?i)guilty",
                r"(?i)not\s+guilty",
                r"(?i)sentence[d]?",
                r"(?i)conviction",
                r"(?i)charge[d]?"
            ]
        }
    
    def resolve_context(self,
                        text: str,
                        entity: ExtractedEntity,
                        all_entities: Optional[List[ExtractedEntity]] = None) -> ResolvedContext:
        """
        Resolve the context for an entity using multi-stage analysis.
        
        Args:
            text: Full document text
            entity: Entity to resolve context for
            all_entities: All entities in the document (for relationship analysis)
        
        Returns:
            ResolvedContext with combined analysis results
        """
        # Extract context window
        context_window = self.window_extractor.extract_window(
            text, entity, WindowLevel.SENTENCE, window_size=3
        )
        
        # Collect signals from different methods
        signals = []
        
        # 1. Pattern-based analysis
        pattern_signal = self._analyze_patterns(context_window, entity)
        if pattern_signal:
            signals.append(pattern_signal)
        
        # 2. Semantic analysis with Legal-BERT
        if self.use_semantic_analysis and self.legal_bert_model:
            semantic_signal = self._analyze_semantic(context_window, entity)
            if semantic_signal:
                signals.append(semantic_signal)
        
        # 3. Dependency parsing with SpaCy
        if self.use_dependency_parsing and self.spacy_model:
            dependency_signal = self._analyze_dependencies(context_window, entity)
            if dependency_signal:
                signals.append(dependency_signal)
        
        # 4. Section-based analysis
        section_signal = self._analyze_section(text, entity)
        if section_signal:
            signals.append(section_signal)
        
        # Combine signals to determine final context
        resolved = self._combine_signals(signals, entity, context_window)
        
        # Add relationship information if available
        if all_entities:
            resolved.metadata['nearby_entities'] = self._analyze_nearby_entities(
                text, entity, all_entities
            )
        
        return resolved
    
    def _analyze_patterns(self, 
                         context_window: ContextWindow,
                         entity: ExtractedEntity) -> Optional[ContextSignal]:
        """Pattern-based context analysis using regex indicators"""
        window_text = context_window.text.lower()
        pattern_matches = defaultdict(int)
        
        # Check each context type's patterns
        for context_type, patterns in self.context_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, window_text)
                if matches:
                    pattern_matches[context_type] += len(matches)
        
        if not pattern_matches:
            return None
        
        # Find strongest matching context
        best_context = max(pattern_matches.items(), key=lambda x: x[1])
        context_type, match_count = best_context
        
        # Calculate confidence based on match strength
        total_matches = sum(pattern_matches.values())
        confidence = match_count / total_matches if total_matches > 0 else 0
        
        # Check entity-specific indicators
        entity_mapping = self.context_mappings.get_entity_context(entity.type)
        if entity_mapping:
            # Check if context matches expected context for entity type
            if entity_mapping.primary_context == context_type:
                confidence = min(1.0, confidence + 0.2)
            
            # Check proximity words
            for word in entity_mapping.proximity_words:
                if word.lower() in window_text:
                    confidence = min(1.0, confidence + 0.05)
        
        return ContextSignal(
            method=ContextResolutionMethod.PATTERN_BASED,
            confidence=confidence,
            context_type=context_type,
            evidence={
                'pattern_matches': dict(pattern_matches),
                'total_matches': total_matches,
                'window_text_sample': window_text[:200]
            },
            weight=self.method_weights[ContextResolutionMethod.PATTERN_BASED]
        )
    
    def _analyze_semantic(self,
                         context_window: ContextWindow,
                         entity: ExtractedEntity) -> Optional[ContextSignal]:
        """Semantic context analysis using Legal-BERT embeddings"""
        if not self.legal_bert_model or not self.legal_bert_tokenizer:
            return None
        
        try:
            # Prepare text for BERT
            window_text = context_window.text
            entity_text = entity.text
            
            # Tokenize and get embeddings
            inputs = self.legal_bert_tokenizer(
                window_text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            )
            
            with torch.no_grad():
                outputs = self.legal_bert_model(**inputs)
                # Use CLS token embedding as context representation
                context_embedding = outputs.last_hidden_state[:, 0, :].numpy()
            
            # Compare with known context embeddings
            # In a real implementation, you would have pre-computed embeddings
            # for different context types to compare against
            
            # For now, use a simplified heuristic based on attention patterns
            attention_weights = outputs.attentions[-1] if hasattr(outputs, 'attentions') else None
            
            # Analyze semantic similarity to context keywords
            context_scores = {}
            for context_type in ContextType:
                # Get context indicators
                indicators = self.context_mappings.get_context_indicators_for_type(context_type)
                if indicators and 'keywords' in indicators:
                    keywords = indicators['keywords']
                    # Simple keyword matching in tokenized text
                    tokens = self.legal_bert_tokenizer.tokenize(window_text.lower())
                    keyword_matches = sum(1 for kw in keywords if kw in tokens)
                    context_scores[context_type] = keyword_matches
            
            if not context_scores:
                return None
            
            # Find best matching context
            best_context = max(context_scores.items(), key=lambda x: x[1])
            context_type, score = best_context
            
            # Calculate confidence
            total_score = sum(context_scores.values())
            confidence = score / total_score if total_score > 0 else 0
            
            return ContextSignal(
                method=ContextResolutionMethod.SEMANTIC,
                confidence=confidence,
                context_type=context_type,
                evidence={
                    'context_scores': context_scores,
                    'embedding_shape': context_embedding.shape,
                    'model_used': 'legal-bert'
                },
                weight=self.method_weights[ContextResolutionMethod.SEMANTIC]
            )
            
        except Exception as e:
            logger.warning(f"Semantic analysis failed: {e}")
            return None
    
    def _analyze_dependencies(self,
                             context_window: ContextWindow,
                             entity: ExtractedEntity) -> Optional[ContextSignal]:
        """Dependency parsing analysis using SpaCy"""
        if not self.spacy_model:
            return None
        
        try:
            # Process text with SpaCy
            doc = self.spacy_model(context_window.text)
            
            # Find entity in SpaCy doc
            entity_span = None
            for ent in doc.ents:
                if ent.text == entity.text:
                    entity_span = ent
                    break
            
            if not entity_span:
                # Try to find entity by position
                for token in doc:
                    if entity.text in token.text:
                        entity_span = token
                        break
            
            if not entity_span:
                return None
            
            # Analyze syntactic patterns
            dependency_patterns = self._extract_dependency_patterns(doc, entity_span)
            
            # Map dependency patterns to context types
            context_scores = defaultdict(float)
            
            # Legal subject patterns
            if 'nsubj' in dependency_patterns or 'nsubjpass' in dependency_patterns:
                if any(tok.text.lower() in ['court', 'judge'] for tok in doc):
                    context_scores[ContextType.CASE_HEADER] += 0.3
                if any(tok.text.lower() in ['plaintiff', 'defendant'] for tok in doc):
                    context_scores[ContextType.PARTY_SECTION] += 0.3
            
            # Object patterns
            if 'dobj' in dependency_patterns or 'pobj' in dependency_patterns:
                if any(tok.text.lower() in ['motion', 'order', 'judgment'] for tok in doc):
                    context_scores[ContextType.PROCEDURAL] += 0.3
                if any(tok.text.lower() in ['contract', 'agreement'] for tok in doc):
                    context_scores[ContextType.CONTRACTUAL] += 0.3
            
            # Prepositional patterns
            if 'prep' in dependency_patterns:
                prep_text = dependency_patterns.get('prep_text', '')
                if 'before' in prep_text.lower():
                    context_scores[ContextType.CASE_HEADER] += 0.2
                if 'pursuant to' in prep_text.lower():
                    context_scores[ContextType.LEGAL_CITATIONS] += 0.2
            
            if not context_scores:
                return None
            
            # Find best context
            best_context = max(context_scores.items(), key=lambda x: x[1])
            context_type, score = best_context
            
            # Normalize confidence
            confidence = min(1.0, score)
            
            return ContextSignal(
                method=ContextResolutionMethod.DEPENDENCY,
                confidence=confidence,
                context_type=context_type,
                evidence={
                    'dependency_patterns': dependency_patterns,
                    'context_scores': dict(context_scores),
                    'entity_label': entity_span.label_ if hasattr(entity_span, 'label_') else None
                },
                weight=self.method_weights[ContextResolutionMethod.DEPENDENCY]
            )
            
        except Exception as e:
            logger.warning(f"Dependency analysis failed: {e}")
            return None
    
    def _extract_dependency_patterns(self, 
                                    doc: Doc,
                                    entity_span: Union[Span, Token]) -> Dict[str, Any]:
        """Extract dependency patterns around an entity"""
        patterns = {}
        
        if isinstance(entity_span, Token):
            # Single token entity
            patterns['dep'] = entity_span.dep_
            patterns['head'] = entity_span.head.text
            patterns['children'] = [child.dep_ for child in entity_span.children]
            
            # Get prepositional phrases
            if entity_span.dep_ == 'pobj':
                patterns['prep_text'] = ' '.join([t.text for t in entity_span.head.subtree])
            
        elif isinstance(entity_span, Span):
            # Multi-token entity
            root = entity_span.root
            patterns['root_dep'] = root.dep_
            patterns['root_head'] = root.head.text
            patterns['span_deps'] = [token.dep_ for token in entity_span]
            
            # Check if entity is subject or object
            for token in entity_span:
                if token.dep_ in ['nsubj', 'nsubjpass']:
                    patterns['nsubj'] = True
                if token.dep_ in ['dobj', 'pobj']:
                    patterns['dobj'] = True
        
        return patterns
    
    def _analyze_section(self,
                        text: str,
                        entity: ExtractedEntity) -> Optional[ContextSignal]:
        """Section-based context analysis"""
        # Extract section context
        section_window = self.window_extractor.extract_window(
            text, entity, WindowLevel.SECTION
        )
        
        # Analyze section metadata
        section_title = section_window.metadata.get('section_title', '').lower()
        
        # Map section titles to context types
        section_context_map = {
            'parties': ContextType.PARTY_SECTION,
            'case information': ContextType.CASE_HEADER,
            'facts': ContextType.EVIDENCE,
            'procedural history': ContextType.PROCEDURAL,
            'claims': ContextType.LEGAL_CONCEPTS,
            'relief': ContextType.LEGAL_CONCEPTS,
            'contract': ContextType.CONTRACTUAL,
            'agreement': ContextType.CONTRACTUAL,
            'criminal charges': ContextType.CRIMINAL,
            'sentence': ContextType.CRIMINAL,
            'damages': ContextType.MONETARY,
            'citations': ContextType.LEGAL_CITATIONS,
            'authorities': ContextType.LEGAL_CITATIONS
        }
        
        # Find matching context
        context_type = None
        confidence = 0.0
        
        for keyword, ctx_type in section_context_map.items():
            if keyword in section_title:
                context_type = ctx_type
                confidence = 0.7
                break
        
        if not context_type:
            # Try pattern matching on section content
            section_text = section_window.text[:500].lower()
            for ctx_type, patterns in self.context_patterns.items():
                matches = sum(1 for p in patterns if re.search(p, section_text))
                if matches >= 2:
                    context_type = ctx_type
                    confidence = 0.5
                    break
        
        if not context_type:
            return None
        
        return ContextSignal(
            method=ContextResolutionMethod.SECTION_BASED,
            confidence=confidence,
            context_type=context_type,
            evidence={
                'section_title': section_window.metadata.get('section_title'),
                'section_number': section_window.metadata.get('section_number'),
                'total_sections': section_window.metadata.get('total_sections')
            },
            weight=self.method_weights[ContextResolutionMethod.SECTION_BASED]
        )
    
    def _combine_signals(self,
                        signals: List[ContextSignal],
                        entity: ExtractedEntity,
                        context_window: ContextWindow) -> ResolvedContext:
        """Combine multiple context signals into final resolution"""
        if not signals:
            # No signals available, use entity type mapping as fallback
            entity_mapping = self.context_mappings.get_entity_context(entity.type)
            if entity_mapping:
                return ResolvedContext(
                    entity=entity,
                    primary_context=entity_mapping.primary_context,
                    secondary_contexts=entity_mapping.secondary_contexts,
                    confidence=0.5,
                    signals=[],
                    context_window=context_window,
                    metadata={'fallback': True}
                )
            else:
                # Ultimate fallback
                return ResolvedContext(
                    entity=entity,
                    primary_context=ContextType.GENERAL_PARTIES,
                    secondary_contexts=[],
                    confidence=0.3,
                    signals=[],
                    context_window=context_window,
                    metadata={'fallback': True, 'no_mapping': True}
                )
        
        # Aggregate context votes weighted by confidence and method weight
        context_votes = defaultdict(float)
        
        for signal in signals:
            if signal.context_type:
                vote_weight = signal.confidence * signal.weight
                context_votes[signal.context_type] += vote_weight
        
        # Sort contexts by vote weight
        sorted_contexts = sorted(context_votes.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_contexts:
            # No valid context found
            entity_mapping = self.context_mappings.get_entity_context(entity.type)
            primary_context = entity_mapping.primary_context if entity_mapping else ContextType.GENERAL_PARTIES
            secondary_contexts = entity_mapping.secondary_contexts if entity_mapping else []
            confidence = 0.4
        else:
            # Primary context is the highest voted
            primary_context = sorted_contexts[0][0]
            
            # Secondary contexts are other high-scoring contexts
            secondary_contexts = [ctx for ctx, score in sorted_contexts[1:3] if score > 0.2]
            
            # Calculate overall confidence
            total_weight = sum(s.weight for s in signals)
            weighted_confidence = sum(s.confidence * s.weight for s in signals)
            confidence = weighted_confidence / total_weight if total_weight > 0 else 0
            
            # Boost confidence if entity type matches expected context
            entity_mapping = self.context_mappings.get_entity_context(entity.type)
            if entity_mapping and entity_mapping.primary_context == primary_context:
                confidence = min(1.0, confidence + entity_mapping.confidence_boost)
        
        return ResolvedContext(
            entity=entity,
            primary_context=primary_context,
            secondary_contexts=secondary_contexts,
            confidence=confidence,
            signals=signals,
            context_window=context_window,
            metadata={
                'context_votes': dict(context_votes),
                'methods_used': [s.method.value for s in signals]
            }
        )
    
    def _analyze_nearby_entities(self,
                                text: str,
                                entity: ExtractedEntity,
                                all_entities: List[ExtractedEntity]) -> List[Dict[str, Any]]:
        """Analyze entities appearing near the target entity"""
        nearby = self.window_extractor.extract_surrounding_entities(
            entity, all_entities, max_distance=200
        )
        
        nearby_info = []
        for nearby_entity in nearby[:5]:  # Top 5 nearest
            nearby_info.append({
                'text': nearby_entity.text,
                'type': nearby_entity.type,
                'distance': abs(nearby_entity.start_pos - entity.start_pos)
            })
        
        return nearby_info
    
    def batch_resolve_contexts(self,
                              text: str,
                              entities: List[ExtractedEntity],
                              batch_size: int = 10) -> List[ResolvedContext]:
        """
        Resolve contexts for multiple entities in batch.
        
        Args:
            text: Full document text
            entities: List of entities to resolve
            batch_size: Number of entities to process together
        
        Returns:
            List of resolved contexts
        """
        resolved_contexts = []
        
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            
            for entity in batch:
                try:
                    resolved = self.resolve_context(text, entity, entities)
                    resolved_contexts.append(resolved)
                except Exception as e:
                    logger.error(f"Failed to resolve context for entity {entity.text}: {e}")
                    # Create fallback resolution
                    resolved_contexts.append(
                        ResolvedContext(
                            entity=entity,
                            primary_context=ContextType.GENERAL_PARTIES,
                            secondary_contexts=[],
                            confidence=0.0,
                            signals=[],
                            context_window=self.window_extractor.extract_window(
                                text, entity, WindowLevel.SENTENCE
                            ),
                            metadata={'error': str(e)}
                        )
                    )
        
        return resolved_contexts
    
    def get_context_quality_score(self, resolved_context: ResolvedContext) -> float:
        """
        Calculate a quality score for the resolved context.
        
        Args:
            resolved_context: The resolved context to evaluate
        
        Returns:
            Quality score between 0 and 1
        """
        scores = []
        
        # Confidence score
        scores.append(resolved_context.confidence)
        
        # Signal diversity score (multiple methods agreeing is good)
        methods_used = len(set(s.method for s in resolved_context.signals))
        diversity_score = methods_used / len(ContextResolutionMethod)
        scores.append(diversity_score)
        
        # Signal agreement score
        if resolved_context.signals:
            context_types = [s.context_type for s in resolved_context.signals if s.context_type]
            if context_types:
                most_common = Counter(context_types).most_common(1)[0]
                agreement_score = most_common[1] / len(context_types)
                scores.append(agreement_score)
        
        # Window quality score
        window_quality = self.window_extractor.analyze_context_quality(
            resolved_context.context_window
        )
        if window_quality:
            scores.append(window_quality.get('completeness', 0.5))
        
        # Average all scores
        return sum(scores) / len(scores) if scores else 0.0