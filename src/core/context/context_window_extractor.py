"""
Context Window Extractor for CALES Entity Extraction Service

This module provides functionality to extract contextual windows around entities,
handling sentence-level and paragraph-level context extraction with edge cases.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
# SpaCy import handled in ContextResolver when needed

# Configure logging
logger = logging.getLogger(__name__)

# Download required NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except Exception as e:
        logger.warning(f"Could not download NLTK punkt tokenizer: {e}")


class WindowLevel(Enum):
    """Context window extraction levels"""
    TOKEN = "token"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    DOCUMENT = "document"


@dataclass
class ContextWindow:
    """Container for extracted context window"""
    text: str
    start_pos: int
    end_pos: int
    level: WindowLevel
    entity_start: int  # Entity position relative to window start
    entity_end: int    # Entity position relative to window start
    sentences: List[str]
    tokens: List[str]
    metadata: Dict[str, Any]


@dataclass
class ExtractedEntity:
    """Entity with position information"""
    text: str
    type: str = None  # Can be set via type or entity_type
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 0.0
    entity_type: str = None  # Alias for type, for backward compatibility
    extraction_method: str = "unknown"  # Additional field for compatibility
    metadata: Dict[str, Any] = None  # Additional field for compatibility
    
    def __post_init__(self):
        """Handle backward compatibility for type/entity_type parameters"""
        # If entity_type is provided but type is not, use entity_type
        if self.entity_type is not None and self.type is None:
            self.type = self.entity_type
        # If type is provided but entity_type is not, use type
        elif self.type is not None and self.entity_type is None:
            self.entity_type = self.type
        # If both are provided, ensure they match
        elif self.type is not None and self.entity_type is not None:
            if self.type != self.entity_type:
                logger.warning(f"Mismatched type ({self.type}) and entity_type ({self.entity_type}), using type")
            self.entity_type = self.type
        # If neither is provided, set to 'unknown'
        else:
            self.type = 'unknown'
            self.entity_type = 'unknown'
        
        # Initialize metadata if not provided
        if self.metadata is None:
            self.metadata = {}


class ContextWindowExtractor:
    """
    Extracts contextual windows around entities with configurable window sizes
    and multiple extraction levels (token, sentence, paragraph, section).
    """
    
    def __init__(self, 
                 spacy_model: Optional[Any] = None,
                 default_sentence_window: int = 3,
                 default_token_window: int = 50,
                 default_paragraph_window: int = 1):
        """
        Initialize the context window extractor.
        
        Args:
            spacy_model: Pre-loaded SpaCy model (optional)
            default_sentence_window: Number of sentences to include (before + after)
            default_token_window: Number of tokens to include (before + after)
            default_paragraph_window: Number of paragraphs to include
        """
        self.spacy_model = spacy_model
        self.default_sentence_window = default_sentence_window
        self.default_token_window = default_token_window
        self.default_paragraph_window = default_paragraph_window
        
        # Paragraph detection patterns
        self.paragraph_patterns = [
            r'\n\n+',  # Double newlines
            r'\n\s*\n',  # Newlines with whitespace
            r'\r\n\r\n',  # Windows-style double newlines
        ]
        
        # Section header patterns for legal documents
        self.section_patterns = [
            r'^[IVX]+\.\s+[A-Z][A-Z\s]+$',  # Roman numeral sections
            r'^\d+\.\s+[A-Z][A-Z\s]+$',  # Numbered sections
            r'^[A-Z][A-Z\s]+:$',  # All caps headers with colon
            r'^ARTICLE\s+\d+',  # Article headers
            r'^SECTION\s+\d+',  # Section headers
            r'^EXHIBIT\s+[A-Z]',  # Exhibit headers
        ]
        
        # Initialize sentence splitter
        self._init_sentence_splitter()
    
    def _init_sentence_splitter(self):
        """Initialize custom sentence splitter for legal text"""
        # Legal abbreviations that don't end sentences
        self.legal_abbreviations = {
            'v.', 'vs.', 'cf.', 'e.g.', 'i.e.', 'viz.', 'al.', 'et.',
            'Inc.', 'Corp.', 'Co.', 'Ltd.', 'LLC', 'L.L.C.', 'P.C.',
            'Esq.', 'Jr.', 'Sr.', 'Ph.D.', 'M.D.', 'J.D.',
            'No.', 'Nos.', 'Art.', 'Sec.', 'Para.', 'Subpara.',
            'U.S.C.', 'F.3d', 'F.2d', 'F.Supp.', 'Cal.App.', 'N.Y.',
            'Jan.', 'Feb.', 'Mar.', 'Apr.', 'Jun.', 'Jul.', 'Aug.',
            'Sep.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'
        }
    
    def extract_window(self,
                      text: str,
                      entity: ExtractedEntity,
                      level: WindowLevel = WindowLevel.SENTENCE,
                      window_size: Optional[int] = None) -> ContextWindow:
        """
        Extract context window around an entity.
        
        Args:
            text: Full document text
            entity: Entity with position information
            level: Window extraction level
            window_size: Custom window size (overrides defaults)
        
        Returns:
            ContextWindow with extracted context
        """
        if level == WindowLevel.TOKEN:
            return self._extract_token_window(text, entity, window_size)
        elif level == WindowLevel.SENTENCE:
            return self._extract_sentence_window(text, entity, window_size)
        elif level == WindowLevel.PARAGRAPH:
            return self._extract_paragraph_window(text, entity, window_size)
        elif level == WindowLevel.SECTION:
            return self._extract_section_window(text, entity)
        elif level == WindowLevel.DOCUMENT:
            return self._extract_document_window(text, entity)
        else:
            raise ValueError(f"Unknown window level: {level}")
    
    def extract_multi_level_context(self,
                                  text: str,
                                  entity: ExtractedEntity) -> Dict[WindowLevel, ContextWindow]:
        """
        Extract context at multiple levels for comprehensive analysis.
        
        Args:
            text: Full document text
            entity: Entity with position information
        
        Returns:
            Dictionary mapping window levels to extracted contexts
        """
        contexts = {}
        
        for level in [WindowLevel.TOKEN, WindowLevel.SENTENCE, 
                     WindowLevel.PARAGRAPH, WindowLevel.SECTION]:
            try:
                contexts[level] = self.extract_window(text, entity, level)
            except Exception as e:
                logger.warning(f"Failed to extract {level} context: {e}")
                contexts[level] = None
        
        return contexts
    
    def _extract_token_window(self, 
                            text: str, 
                            entity: ExtractedEntity,
                            window_size: Optional[int] = None) -> ContextWindow:
        """Extract token-based context window"""
        window_size = window_size or self.default_token_window
        
        # Tokenize the text
        tokens = word_tokenize(text)
        
        # Find entity position in tokens
        entity_tokens = word_tokenize(entity.text)
        entity_start_token = None
        
        for i in range(len(tokens) - len(entity_tokens) + 1):
            if tokens[i:i+len(entity_tokens)] == entity_tokens:
                entity_start_token = i
                break
        
        if entity_start_token is None:
            # Fallback to character position based extraction
            return self._extract_character_window(text, entity, window_size * 5)
        
        # Calculate window boundaries
        start_token = max(0, entity_start_token - window_size)
        end_token = min(len(tokens), entity_start_token + len(entity_tokens) + window_size)
        
        # Extract window tokens
        window_tokens = tokens[start_token:end_token]
        window_text = ' '.join(window_tokens)
        
        # Calculate character positions
        char_pos = 0
        for i, token in enumerate(tokens):
            if i == start_token:
                start_pos = char_pos
            if i == end_token:
                end_pos = char_pos
                break
            char_pos += len(token) + 1  # +1 for space
        else:
            end_pos = len(text)
        
        # Entity position relative to window
        entity_start_rel = entity_start_token - start_token
        entity_end_rel = entity_start_rel + len(entity_tokens)
        
        return ContextWindow(
            text=window_text,
            start_pos=start_pos,
            end_pos=end_pos,
            level=WindowLevel.TOKEN,
            entity_start=entity_start_rel,
            entity_end=entity_end_rel,
            sentences=sent_tokenize(window_text),
            tokens=window_tokens,
            metadata={
                'window_size': window_size,
                'total_tokens': len(window_tokens),
                'entity_tokens': len(entity_tokens)
            }
        )
    
    def _extract_sentence_window(self,
                                text: str,
                                entity: ExtractedEntity,
                                window_size: Optional[int] = None) -> ContextWindow:
        """Extract sentence-based context window"""
        window_size = window_size or self.default_sentence_window
        
        # Split text into sentences
        sentences = self._split_sentences(text)
        
        # Find entity's sentence
        entity_sentence_idx = None
        sentence_positions = []
        current_pos = 0
        
        for i, sentence in enumerate(sentences):
            sentence_start = text.find(sentence, current_pos)
            sentence_end = sentence_start + len(sentence)
            sentence_positions.append((sentence_start, sentence_end))
            
            if entity.start_pos >= sentence_start and entity.start_pos < sentence_end:
                entity_sentence_idx = i
            
            current_pos = sentence_end
        
        if entity_sentence_idx is None:
            # Entity spans multiple sentences or not found
            entity_sentence_idx = self._find_closest_sentence(entity.start_pos, sentence_positions)
        
        # Calculate window boundaries
        start_idx = max(0, entity_sentence_idx - window_size)
        end_idx = min(len(sentences), entity_sentence_idx + window_size + 1)
        
        # Extract window sentences
        window_sentences = sentences[start_idx:end_idx]
        window_text = ' '.join(window_sentences)
        
        # Calculate positions
        start_pos = sentence_positions[start_idx][0] if sentence_positions else 0
        end_pos = sentence_positions[end_idx - 1][1] if end_idx > 0 and sentence_positions else len(text)
        
        # Entity position relative to window
        entity_start_rel = entity.start_pos - start_pos
        entity_end_rel = entity.end_pos - start_pos
        
        return ContextWindow(
            text=window_text,
            start_pos=start_pos,
            end_pos=end_pos,
            level=WindowLevel.SENTENCE,
            entity_start=entity_start_rel,
            entity_end=entity_end_rel,
            sentences=window_sentences,
            tokens=word_tokenize(window_text),
            metadata={
                'window_size': window_size,
                'total_sentences': len(window_sentences),
                'entity_sentence_idx': entity_sentence_idx - start_idx
            }
        )
    
    def _extract_paragraph_window(self,
                                 text: str,
                                 entity: ExtractedEntity,
                                 window_size: Optional[int] = None) -> ContextWindow:
        """Extract paragraph-based context window"""
        window_size = window_size or self.default_paragraph_window
        
        # Split text into paragraphs
        paragraphs = self._split_paragraphs(text)
        
        # Find entity's paragraph
        entity_para_idx = None
        para_positions = []
        current_pos = 0
        
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
                
            para_start = text.find(paragraph, current_pos)
            para_end = para_start + len(paragraph)
            para_positions.append((para_start, para_end, i))
            
            if entity.start_pos >= para_start and entity.start_pos < para_end:
                entity_para_idx = i
            
            current_pos = para_end
        
        if entity_para_idx is None and para_positions:
            # Find closest paragraph
            entity_para_idx = self._find_closest_paragraph(entity.start_pos, para_positions)
        
        if entity_para_idx is None:
            # Fallback to sentence window
            return self._extract_sentence_window(text, entity, window_size * 3)
        
        # Calculate window boundaries
        start_idx = max(0, entity_para_idx - window_size)
        end_idx = min(len(paragraphs), entity_para_idx + window_size + 1)
        
        # Extract window paragraphs
        window_paragraphs = [p for p in paragraphs[start_idx:end_idx] if p.strip()]
        window_text = '\n\n'.join(window_paragraphs)
        
        # Calculate positions
        if para_positions:
            start_pos = min(p[0] for p in para_positions if p[2] >= start_idx)
            end_pos = max(p[1] for p in para_positions if p[2] < end_idx)
        else:
            start_pos = 0
            end_pos = len(text)
        
        # Entity position relative to window
        entity_start_rel = entity.start_pos - start_pos
        entity_end_rel = entity.end_pos - start_pos
        
        return ContextWindow(
            text=window_text,
            start_pos=start_pos,
            end_pos=end_pos,
            level=WindowLevel.PARAGRAPH,
            entity_start=entity_start_rel,
            entity_end=entity_end_rel,
            sentences=sent_tokenize(window_text),
            tokens=word_tokenize(window_text),
            metadata={
                'window_size': window_size,
                'total_paragraphs': len(window_paragraphs),
                'entity_paragraph_idx': entity_para_idx - start_idx
            }
        )
    
    def _extract_section_window(self,
                               text: str,
                               entity: ExtractedEntity) -> ContextWindow:
        """Extract section-based context window"""
        sections = self._split_sections(text)
        
        # Find entity's section
        entity_section_idx = None
        section_positions = []
        
        for i, section in enumerate(sections):
            section_start = text.find(section['text'])
            section_end = section_start + len(section['text'])
            section_positions.append((section_start, section_end, i))
            
            if entity.start_pos >= section_start and entity.start_pos < section_end:
                entity_section_idx = i
                break
        
        if entity_section_idx is None:
            # Fallback to paragraph window
            return self._extract_paragraph_window(text, entity, 2)
        
        section = sections[entity_section_idx]
        section_text = section['text']
        section_start = section_positions[entity_section_idx][0]
        
        # Entity position relative to section
        entity_start_rel = entity.start_pos - section_start
        entity_end_rel = entity.end_pos - section_start
        
        return ContextWindow(
            text=section_text,
            start_pos=section_start,
            end_pos=section_start + len(section_text),
            level=WindowLevel.SECTION,
            entity_start=entity_start_rel,
            entity_end=entity_end_rel,
            sentences=sent_tokenize(section_text),
            tokens=word_tokenize(section_text),
            metadata={
                'section_title': section.get('title', 'Untitled'),
                'section_number': entity_section_idx,
                'total_sections': len(sections)
            }
        )
    
    def _extract_document_window(self,
                                text: str,
                                entity: ExtractedEntity) -> ContextWindow:
        """Extract full document as context"""
        return ContextWindow(
            text=text,
            start_pos=0,
            end_pos=len(text),
            level=WindowLevel.DOCUMENT,
            entity_start=entity.start_pos,
            entity_end=entity.end_pos,
            sentences=sent_tokenize(text),
            tokens=word_tokenize(text),
            metadata={
                'document_length': len(text),
                'total_sentences': len(sent_tokenize(text)),
                'total_tokens': len(word_tokenize(text))
            }
        )
    
    def _extract_character_window(self,
                                 text: str,
                                 entity: ExtractedEntity,
                                 char_window: int = 250) -> ContextWindow:
        """Fallback character-based window extraction"""
        start_pos = max(0, entity.start_pos - char_window)
        end_pos = min(len(text), entity.end_pos + char_window)
        
        window_text = text[start_pos:end_pos]
        
        # Entity position relative to window
        entity_start_rel = entity.start_pos - start_pos
        entity_end_rel = entity.end_pos - start_pos
        
        return ContextWindow(
            text=window_text,
            start_pos=start_pos,
            end_pos=end_pos,
            level=WindowLevel.TOKEN,
            entity_start=entity_start_rel,
            entity_end=entity_end_rel,
            sentences=sent_tokenize(window_text),
            tokens=word_tokenize(window_text),
            metadata={
                'fallback_method': 'character_window',
                'char_window': char_window
            }
        )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with legal text handling"""
        # Use NLTK sentence tokenizer
        sentences = sent_tokenize(text)
        
        # Post-process to handle legal abbreviations
        processed_sentences = []
        buffer = ""
        
        for sentence in sentences:
            if buffer:
                sentence = buffer + " " + sentence
                buffer = ""
            
            # Check if sentence ends with a legal abbreviation
            words = sentence.split()
            if words and words[-1] in self.legal_abbreviations:
                buffer = sentence
            else:
                processed_sentences.append(sentence)
        
        if buffer:
            processed_sentences.append(buffer)
        
        return processed_sentences
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Try different paragraph separators
        for pattern in self.paragraph_patterns:
            paragraphs = re.split(pattern, text)
            if len(paragraphs) > 1:
                return [p.strip() for p in paragraphs if p.strip()]
        
        # Fallback: treat entire text as one paragraph
        return [text]
    
    def _split_sections(self, text: str) -> List[Dict[str, str]]:
        """Split text into sections based on headers"""
        sections = []
        current_section = {'title': 'Introduction', 'text': ''}
        
        lines = text.split('\n')
        for line in lines:
            # Check if line is a section header
            is_header = False
            for pattern in self.section_patterns:
                if re.match(pattern, line.strip()):
                    # Save current section if it has content
                    if current_section['text'].strip():
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = {'title': line.strip(), 'text': ''}
                    is_header = True
                    break
            
            if not is_header:
                current_section['text'] += line + '\n'
        
        # Add last section
        if current_section['text'].strip():
            sections.append(current_section)
        
        # If no sections found, treat entire text as one section
        if not sections:
            sections = [{'title': 'Document', 'text': text}]
        
        return sections
    
    def _find_closest_sentence(self, 
                              position: int, 
                              sentence_positions: List[Tuple[int, int]]) -> int:
        """Find closest sentence to a position"""
        min_distance = float('inf')
        closest_idx = 0
        
        for i, (start, end) in enumerate(sentence_positions):
            # Calculate distance to sentence
            if position < start:
                distance = start - position
            elif position > end:
                distance = position - end
            else:
                return i  # Position is within this sentence
            
            if distance < min_distance:
                min_distance = distance
                closest_idx = i
        
        return closest_idx
    
    def _find_closest_paragraph(self,
                               position: int,
                               para_positions: List[Tuple[int, int, int]]) -> int:
        """Find closest paragraph to a position"""
        min_distance = float('inf')
        closest_idx = 0
        
        for start, end, idx in para_positions:
            # Calculate distance to paragraph
            if position < start:
                distance = start - position
            elif position > end:
                distance = position - end
            else:
                return idx  # Position is within this paragraph
            
            if distance < min_distance:
                min_distance = distance
                closest_idx = idx
        
        return closest_idx
    
    def extract_surrounding_entities(self,
                                    target_entity: ExtractedEntity,
                                    all_entities: List[ExtractedEntity],
                                    max_distance: int = 500) -> List[ExtractedEntity]:
        """
        Extract entities that appear near the target entity.
        
        Args:
            target_entity: The entity to find neighbors for
            all_entities: All entities in the document
            max_distance: Maximum character distance to consider
        
        Returns:
            List of nearby entities sorted by distance
        """
        nearby_entities = []
        
        for entity in all_entities:
            if entity == target_entity:
                continue
            
            # Calculate distance
            if entity.end_pos < target_entity.start_pos:
                distance = target_entity.start_pos - entity.end_pos
            elif entity.start_pos > target_entity.end_pos:
                distance = entity.start_pos - target_entity.end_pos
            else:
                # Entities overlap
                distance = 0
            
            if distance <= max_distance:
                nearby_entities.append((entity, distance))
        
        # Sort by distance
        nearby_entities.sort(key=lambda x: x[1])
        
        return [entity for entity, _ in nearby_entities]
    
    def analyze_context_quality(self, context_window: ContextWindow) -> Dict[str, Any]:
        """
        Analyze the quality and characteristics of a context window.
        
        Args:
            context_window: The context window to analyze
        
        Returns:
            Dictionary with quality metrics
        """
        quality_metrics = {
            'completeness': 0.0,
            'coherence': 0.0,
            'relevance': 0.0,
            'edge_handling': 'good',
            'issues': []
        }
        
        # Check completeness
        if context_window.level == WindowLevel.SENTENCE:
            # Check if we have complete sentences
            first_sentence = context_window.sentences[0] if context_window.sentences else ""
            last_sentence = context_window.sentences[-1] if context_window.sentences else ""
            
            # Check for sentence fragments
            if first_sentence and not first_sentence[0].isupper():
                quality_metrics['issues'].append('First sentence may be incomplete')
                quality_metrics['completeness'] -= 0.2
            
            if last_sentence and not last_sentence.rstrip().endswith(('.', '!', '?')):
                quality_metrics['issues'].append('Last sentence may be incomplete')
                quality_metrics['completeness'] -= 0.2
        
        # Check coherence
        if len(context_window.sentences) > 1:
            quality_metrics['coherence'] = min(1.0, len(context_window.sentences) / 5)
        else:
            quality_metrics['coherence'] = 0.5
        
        # Check edge handling
        if context_window.start_pos == 0:
            quality_metrics['edge_handling'] = 'start_of_document'
        elif context_window.end_pos >= len(context_window.text):
            quality_metrics['edge_handling'] = 'end_of_document'
        
        # Calculate overall completeness
        quality_metrics['completeness'] = max(0.0, 1.0 + quality_metrics['completeness'])
        
        # Add statistics
        quality_metrics['statistics'] = {
            'window_size_chars': len(context_window.text),
            'sentence_count': len(context_window.sentences),
            'token_count': len(context_window.tokens),
            'entity_position': f"{context_window.entity_start}-{context_window.entity_end}"
        }
        
        return quality_metrics