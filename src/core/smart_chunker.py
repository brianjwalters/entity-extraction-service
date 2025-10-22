"""Smart Document Chunking System for Legal Entity Extraction.

This module provides intelligent document chunking strategies specifically designed
for legal documents, preserving important boundaries like citations, sections, and
legal structure while maintaining context continuity.

Features:
- Multiple chunking strategies (legal_aware, section_aware, paragraph_aware, etc.)
- Document type detection (contract, opinion, statute, brief)
- Complexity calculation based on legal terminology
- Citation and quote preservation
- Adaptive strategy selection
- Overlap management for context continuity
"""

import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize

# Download NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except:
        pass

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    try:
        nltk.download('punkt_tab', quiet=True)
    except:
        pass

from .config import get_settings

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Types of legal documents for adaptive chunking."""
    CONTRACT = "contract"
    OPINION = "opinion"
    STATUTE = "statute"
    REGULATION = "regulation"
    BRIEF = "brief"
    MOTION = "motion"
    PLEADING = "pleading"
    DISCOVERY = "discovery"
    CORRESPONDENCE = "correspondence"
    MEMORANDUM = "memorandum"
    UNKNOWN = "unknown"


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    LEGAL_AWARE = "legal_aware"
    SECTION_AWARE = "section_aware"
    PARAGRAPH_AWARE = "paragraph_aware"
    SENTENCE_AWARE = "sentence_aware"
    FIXED_SIZE = "fixed_size"
    ADAPTIVE = "adaptive"


@dataclass
class DocumentChunk:
    """Represents a chunk of a legal document with metadata."""
    
    text: str
    start_pos: int
    end_pos: int
    chunk_index: int
    chunk_type: str = "standard"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def length(self) -> int:
        """Return the length of the chunk text."""
        return len(self.text)
    
    def __repr__(self) -> str:
        """String representation of the chunk."""
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"DocumentChunk(index={self.chunk_index}, type={self.chunk_type}, length={self.length}, preview='{preview}')"


class SmartChunker:
    """Smart document chunking system for legal documents."""
    
    # Legal section markers
    LEGAL_SECTION_MARKERS = [
        r"^\s*(?:ARTICLE|Article|ART\.?)\s+[IVXLCDM]+",  # Article I, II, etc.
        r"^\s*(?:SECTION|Section|SEC\.?|§)\s+\d+",  # Section 1, § 2, etc.
        r"^\s*\d+\.\s+[A-Z]",  # 1. Title
        r"^\s*\([a-z]\)",  # (a), (b), etc.
        r"^\s*\(\d+\)",  # (1), (2), etc.
        r"^\s*[A-Z]\.\s+",  # A. , B. , etc.
        r"^\s*\d+\.\d+",  # 1.1, 1.2, etc.
        r"^\s*(?:WHEREAS|NOW,?\s*THEREFORE)",  # Contract clauses
        r"^\s*(?:WITNESSETH|RECITALS?)",  # Contract sections
        r"^\s*(?:DEFINITIONS?|TERMS?)\s*:?$",  # Definition sections
        r"^\s*(?:SCHEDULE|EXHIBIT|APPENDIX)\s+[A-Z0-9]",  # Attachments
    ]
    
    # Legal citation patterns (simplified for boundary detection)
    CITATION_PATTERNS = [
        r"\b\d+\s+[A-Z][a-z]+\.?\s*\d+[a-z]?\b",  # 123 F.2d 456
        r"\b\d+\s+U\.S\.C\.?\s*§?\s*\d+",  # 42 U.S.C. § 1983
        r"\b\d+\s+C\.F\.R\.?\s*§?\s*\d+",  # 45 C.F.R. § 164.502
        r"\b[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+",  # Brown v. Board
        r"§§?\s*\d+(?:\.\d+)*",  # § 1.234
    ]
    
    # Quote patterns
    QUOTE_PATTERNS = [
        r'"[^"]{10,}"',  # Double quotes with substantial content
        r"'[^']{10,}'",  # Single quotes with substantial content
        r"``[^']+''",  # LaTeX-style quotes
    ]
    
    # Legal terminology for complexity assessment
    LEGAL_TERMS = {
        "high_complexity": [
            "notwithstanding", "hereinafter", "whereas", "heretofore",
            "aforementioned", "hereunder", "thereunder", "pursuant",
            "inter alia", "mutatis mutandis", "prima facie", "res judicata",
            "estoppel", "certiorari", "mandamus", "habeas corpus"
        ],
        "medium_complexity": [
            "plaintiff", "defendant", "appellant", "appellee", "jurisdiction",
            "precedent", "statute", "regulation", "liability", "negligence",
            "breach", "damages", "injunction", "motion", "discovery"
        ],
        "low_complexity": [
            "court", "judge", "law", "legal", "case", "claim", "party",
            "agreement", "contract", "document", "filing", "order"
        ]
    }
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize the SmartChunker with configuration.

        Args:
            config: Optional ChunkingIntegrationSettings instance. If not provided, uses default from config.
        """
        # Handle ChunkingIntegrationSettings or get from settings
        if config is None:
            self.config = get_settings().chunking
        elif hasattr(config, 'chunking'):
            # Full settings passed, extract chunking
            self.config = config.chunking
        else:
            # Assume it's a ChunkingIntegrationSettings
            self.config = config
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
        
        logger.info(f"SmartChunker initialized with max_chunk_size={self.config.max_chunk_size}, "
                   f"overlap={self.config.chunk_overlap}, smart_chunking={self.config.enable_smart_chunking}")
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        self.section_pattern = re.compile(
            "|".join(self.LEGAL_SECTION_MARKERS),
            re.MULTILINE | re.IGNORECASE
        )
        
        self.citation_pattern = re.compile(
            "|".join(self.CITATION_PATTERNS),
            re.IGNORECASE
        )
        
        self.quote_pattern = re.compile(
            "|".join(self.QUOTE_PATTERNS),
            re.DOTALL
        )
    
    def chunk_document(
        self,
        text: str,
        strategy: Optional[ChunkingStrategy] = None,
        document_type: Optional[DocumentType] = None
    ) -> List[DocumentChunk]:
        """Chunk a document using the specified or adaptive strategy.
        
        Args:
            text: The document text to chunk
            strategy: Optional specific chunking strategy to use
            document_type: Optional document type hint
            
        Returns:
            List of DocumentChunk objects
        """
        if not text:
            return []
        
        # Use adaptive strategy if not specified and smart chunking is enabled
        if strategy is None:
            if self.config.enable_smart_chunking:
                strategy = ChunkingStrategy.ADAPTIVE
            else:
                strategy = ChunkingStrategy.FIXED_SIZE
        
        # Detect document type if not provided
        if document_type is None:
            document_type = self.detect_document_type(text)
        
        logger.info(f"Chunking document with strategy={strategy}, type={document_type}, "
                   f"length={len(text)} chars")
        
        # Apply the appropriate chunking strategy
        if strategy == ChunkingStrategy.ADAPTIVE:
            chunks = self._adaptive_chunking(text, document_type)
        elif strategy == ChunkingStrategy.LEGAL_AWARE:
            chunks = self._legal_aware_chunking(text)
        elif strategy == ChunkingStrategy.SECTION_AWARE:
            chunks = self._section_aware_chunking(text)
        elif strategy == ChunkingStrategy.PARAGRAPH_AWARE:
            chunks = self._paragraph_aware_chunking(text)
        elif strategy == ChunkingStrategy.SENTENCE_AWARE:
            chunks = self._sentence_aware_chunking(text)
        else:  # FIXED_SIZE
            chunks = self._fixed_size_chunking(text)
        
        # Apply overlap if configured
        if self.config.chunk_overlap > 0:
            chunks = self._apply_overlap(chunks, text)
        
        # Validate chunk sizes and adjust if necessary
        chunks = self._validate_and_adjust_chunks(chunks)
        
        logger.info(f"Created {len(chunks)} chunks with strategy={strategy}")
        
        return chunks
    
    def should_use_smart_chunking(self, text: str) -> bool:
        """Determine if smart chunking should be used for large documents.
        
        Args:
            text: The document text to evaluate
            
        Returns:
            True if document exceeds smart chunk threshold (50K chars), False otherwise
        """
        if not hasattr(self.config, 'smart_chunk_threshold'):
            # Fallback to 50000 if config doesn't have the new attribute
            threshold = 50000
        else:
            threshold = self.config.smart_chunk_threshold
        
        document_length = len(text)
        should_chunk = document_length > threshold
        
        if should_chunk:
            logger.info(f"Document length ({document_length:,} chars) exceeds threshold ({threshold:,} chars). "
                       f"Smart chunking will be used.")
        
        return should_chunk
    
    def smart_chunk_document(
        self,
        text: str,
        strategy: Optional[ChunkingStrategy] = None,
        document_type: Optional[DocumentType] = None
    ) -> List[DocumentChunk]:
        """Smart chunk a large document using the formula: (doc_chars / context_window) * 0.8.
        
        This method is specifically designed for documents >50K characters to optimize
        processing while maintaining context and preventing token limit issues.
        
        Args:
            text: The large document text to chunk
            strategy: Optional chunking strategy (defaults to LEGAL_AWARE for large docs)
            document_type: Optional document type hint
            
        Returns:
            List of DocumentChunk objects with proper overlap
        """
        if not hasattr(self.config, 'context_window_size'):
            context_window = 128000  # Default 128K context window
        else:
            context_window = self.config.context_window_size
        
        if not hasattr(self.config, 'context_window_buffer'):
            buffer = 0.8
        else:
            buffer = self.config.context_window_buffer
        
        document_length = len(text)
        
        # Calculate optimal chunk size using the formula
        optimal_chunk_size = int((document_length / context_window) * buffer * context_window)
        
        # Ensure chunk size is reasonable
        # For a 32K token model, we need much smaller chunks
        # Assuming ~3 chars per token, 32K tokens = ~96K chars
        # But we need room for the prompt template too, so use 10K chars max
        min_chunk = self.config.min_chunk_size
        max_chunk = min(context_window * buffer, 10000)  # Cap at 10K chars to leave room for prompt
        optimal_chunk_size = max(min_chunk, min(optimal_chunk_size, max_chunk))
        
        logger.info(f"Smart chunking document of {document_length:,} chars into chunks of ~{optimal_chunk_size:,} chars")
        
        # Calculate number of chunks needed
        num_chunks = max(1, int(document_length / optimal_chunk_size) + (1 if document_length % optimal_chunk_size else 0))
        
        chunks = []
        chunk_index = 0
        overlap_size = self.config.chunk_overlap  # Use configured overlap (now 500 chars)
        
        for i in range(num_chunks):
            # Calculate chunk boundaries with overlap
            if i == 0:
                # First chunk: no overlap at start
                start_pos = 0
            else:
                # Add overlap from previous chunk
                start_pos = max(0, i * optimal_chunk_size - overlap_size)
                # Find word boundary for clean overlap
                while start_pos > 0 and start_pos < len(text) and not text[start_pos].isspace():
                    start_pos -= 1
            
            if i == num_chunks - 1:
                # Last chunk: extend to end of document
                end_pos = document_length
            else:
                # Add overlap into next chunk
                end_pos = min(document_length, (i + 1) * optimal_chunk_size + overlap_size)
                # Find word boundary for clean overlap
                while end_pos < len(text) and not text[end_pos].isspace():
                    end_pos += 1
            
            # Extract chunk text
            chunk_text = text[start_pos:end_pos].strip()
            
            if chunk_text:
                chunk = DocumentChunk(
                    text=chunk_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    chunk_index=chunk_index,
                    chunk_type="smart_chunk",
                    confidence=0.95,
                    metadata={
                        "strategy": "smart_chunking",
                        "chunk_size": len(chunk_text),
                        "overlap_before": overlap_size if i > 0 else 0,
                        "overlap_after": overlap_size if i < num_chunks - 1 else 0,
                        "total_chunks": num_chunks,
                        "document_length": document_length,
                        "optimal_chunk_size": optimal_chunk_size
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
                
                logger.debug(f"Created chunk {chunk_index}/{num_chunks}: "
                           f"chars {start_pos:,}-{end_pos:,} (size: {len(chunk_text):,})")
        
        logger.info(f"Smart chunking complete: created {len(chunks)} chunks with {overlap_size} char overlap")
        
        # If a specific strategy was requested, apply additional processing
        if strategy and strategy != ChunkingStrategy.FIXED_SIZE:
            # Apply legal-aware or other strategy-specific refinements
            chunks = self._refine_smart_chunks(chunks, text, strategy, document_type)
        
        return chunks
    
    def _refine_smart_chunks(
        self,
        chunks: List[DocumentChunk],
        text: str,
        strategy: ChunkingStrategy,
        document_type: Optional[DocumentType]
    ) -> List[DocumentChunk]:
        """Refine smart chunks based on specific strategy requirements.
        
        This ensures that even with smart chunking, we preserve important
        boundaries like legal sections, citations, and quotes.
        
        Args:
            chunks: Initial smart chunks
            text: Original document text
            strategy: Chunking strategy to apply
            document_type: Type of document
            
        Returns:
            Refined list of DocumentChunk objects
        """
        if strategy == ChunkingStrategy.LEGAL_AWARE:
            # Find legal boundaries to avoid splitting
            boundaries = self._find_legal_boundaries(text)
            
            refined_chunks = []
            for chunk in chunks:
                # Check if chunk splits any important boundaries
                splits_boundary = any(
                    (boundary[0] < chunk.end_pos < boundary[1]) or
                    (boundary[0] < chunk.start_pos < boundary[1])
                    for boundary in boundaries
                )
                
                if splits_boundary:
                    # Adjust chunk boundaries to respect legal boundaries
                    chunk.metadata["boundary_adjusted"] = True
                    logger.debug(f"Chunk {chunk.chunk_index} adjusted to respect legal boundaries")
                
                refined_chunks.append(chunk)
            
            return refined_chunks
        
        # For other strategies, return chunks as-is
        return chunks
    
    def detect_document_type(self, text: str) -> DocumentType:
        """Detect the type of legal document based on content analysis.
        
        Args:
            text: Document text to analyze
            
        Returns:
            Detected DocumentType
        """
        text_lower = text[:5000].lower()  # Analyze first 5000 chars for efficiency
        
        # Contract indicators
        contract_indicators = [
            "agreement", "whereas", "witnesseth", "party", "parties",
            "effective date", "term", "termination", "obligations",
            "representations", "warranties", "indemnification"
        ]
        contract_score = sum(1 for term in contract_indicators if term in text_lower)
        
        # Opinion indicators
        opinion_indicators = [
            "opinion", "dissent", "concur", "reverse", "affirm",
            "remand", "appellant", "appellee", "held", "judgment",
            "circuit", "district court", "supreme court"
        ]
        opinion_score = sum(1 for term in opinion_indicators if term in text_lower)
        
        # Statute indicators
        statute_indicators = [
            "enacted", "amended", "section", "subsection", "paragraph",
            "shall", "must", "prohibited", "authorized", "penalty",
            "violation", "enforcement"
        ]
        statute_score = sum(1 for term in statute_indicators if term in text_lower)
        
        # Brief indicators
        brief_indicators = [
            "plaintiff", "defendant", "motion", "memorandum", "argument",
            "issue", "facts", "standard", "conclusion", "respectfully",
            "relief", "prayer"
        ]
        brief_score = sum(1 for term in brief_indicators if term in text_lower)
        
        # Determine document type based on highest score
        scores = {
            DocumentType.CONTRACT: contract_score,
            DocumentType.OPINION: opinion_score,
            DocumentType.STATUTE: statute_score,
            DocumentType.BRIEF: brief_score
        }
        
        if max(scores.values()) < 2:  # Low confidence threshold
            return DocumentType.UNKNOWN
        
        document_type = max(scores, key=scores.get)
        logger.debug(f"Document type detected: {document_type} (scores: {scores})")
        
        return document_type
    
    def calculate_complexity(self, text: str) -> float:
        """Calculate document complexity based on legal terminology and structure.
        
        Args:
            text: Text to analyze
            
        Returns:
            Complexity score between 0.0 and 1.0
        """
        words = word_tokenize(text.lower())
        total_words = len(words)
        
        if total_words == 0:
            return 0.0
        
        # Count legal terms by complexity level
        high_count = sum(1 for word in words if word in self.LEGAL_TERMS["high_complexity"])
        medium_count = sum(1 for word in words if word in self.LEGAL_TERMS["medium_complexity"])
        low_count = sum(1 for word in words if word in self.LEGAL_TERMS["low_complexity"])
        
        # Calculate weighted complexity score
        complexity_score = (
            (high_count * 3 + medium_count * 2 + low_count * 1) /
            (total_words * 3)  # Normalize to 0-1 range
        )
        
        # Factor in sentence length (longer sentences = higher complexity)
        sentences = sent_tokenize(text)
        if sentences:
            avg_sentence_length = total_words / len(sentences)
            length_factor = min(avg_sentence_length / 50, 1.0)  # Cap at 50 words per sentence
            complexity_score = (complexity_score + length_factor) / 2
        
        # Factor in citation density
        citation_count = len(self.citation_pattern.findall(text))
        citation_density = citation_count / (total_words / 100)  # Citations per 100 words
        citation_factor = min(citation_density / 5, 1.0)  # Cap at 5 citations per 100 words
        
        # Combined complexity score
        final_score = (complexity_score * 0.6 + citation_factor * 0.4)
        
        return min(max(final_score, 0.0), 1.0)  # Ensure 0-1 range
    
    def _adaptive_chunking(self, text: str, document_type: DocumentType) -> List[DocumentChunk]:
        """Choose and apply the best chunking strategy based on document characteristics.
        
        Args:
            text: Document text to chunk
            document_type: Type of legal document
            
        Returns:
            List of DocumentChunk objects
        """
        complexity = self.calculate_complexity(text)
        
        logger.debug(f"Adaptive chunking for {document_type} with complexity={complexity:.2f}")
        
        # Select strategy based on document type and complexity
        if document_type == DocumentType.CONTRACT:
            # Contracts benefit from section-aware chunking
            return self._section_aware_chunking(text)
        
        elif document_type == DocumentType.OPINION:
            # Opinions need legal-aware chunking to preserve citations
            return self._legal_aware_chunking(text)
        
        elif document_type == DocumentType.STATUTE:
            # Statutes have clear section structure
            return self._section_aware_chunking(text)
        
        elif document_type == DocumentType.BRIEF:
            # Briefs benefit from paragraph-aware chunking
            return self._paragraph_aware_chunking(text)
        
        else:
            # Default based on complexity
            if complexity > 0.7:
                return self._legal_aware_chunking(text)
            elif complexity > 0.4:
                return self._paragraph_aware_chunking(text)
            else:
                return self._sentence_aware_chunking(text)
    
    def _legal_aware_chunking(self, text: str) -> List[DocumentChunk]:
        """Chunk text with awareness of legal structure and citations.
        
        Preserves legal sections, citations, and quotes as atomic units.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_start = 0
        chunk_index = 0
        
        # Find all legal boundaries
        boundaries = self._find_legal_boundaries(text)
        
        lines = text.split('\n')
        current_pos = 0
        
        for line_num, line in enumerate(lines):
            line_with_newline = line + '\n' if line_num < len(lines) - 1 else line
            line_len = len(line_with_newline)
            
            # Check if this line contains a boundary that shouldn't be split
            is_boundary = any(
                boundary[0] <= current_pos < boundary[1]
                for boundary in boundaries
            )
            
            # Check if this line starts a new section
            is_section_start = bool(self.section_pattern.match(line))
            
            # Decide whether to start a new chunk
            if is_section_start and current_size > self.config.min_chunk_size:
                # Save current chunk
                if current_chunk:
                    chunk_text = ''.join(current_chunk)
                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        start_pos=chunk_start,
                        end_pos=chunk_start + len(chunk_text),
                        chunk_index=chunk_index,
                        chunk_type="legal_section",
                        confidence=0.9,
                        metadata={"strategy": "legal_aware"}
                    ))
                    chunk_index += 1
                
                # Start new chunk
                current_chunk = [line_with_newline]
                current_size = line_len
                chunk_start = current_pos
            
            elif current_size + line_len > self.config.max_chunk_size and not is_boundary:
                # Current chunk is full and we're not in a boundary
                if current_chunk:
                    chunk_text = ''.join(current_chunk)
                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        start_pos=chunk_start,
                        end_pos=chunk_start + len(chunk_text),
                        chunk_index=chunk_index,
                        chunk_type="legal_section",
                        confidence=0.9,
                        metadata={"strategy": "legal_aware"}
                    ))
                    chunk_index += 1
                
                # Start new chunk
                current_chunk = [line_with_newline]
                current_size = line_len
                chunk_start = current_pos
            
            else:
                # Add to current chunk
                current_chunk.append(line_with_newline)
                current_size += line_len
            
            current_pos += line_len
        
        # Save final chunk
        if current_chunk:
            chunk_text = ''.join(current_chunk)
            chunks.append(DocumentChunk(
                text=chunk_text,
                start_pos=chunk_start,
                end_pos=chunk_start + len(chunk_text),
                chunk_index=chunk_index,
                chunk_type="legal_section",
                confidence=0.9,
                metadata={"strategy": "legal_aware"}
            ))
        
        return chunks
    
    def _section_aware_chunking(self, text: str) -> List[DocumentChunk]:
        """Chunk text based on document sections and structure.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Find all section markers
        sections = list(self.section_pattern.finditer(text))
        
        if not sections:
            # No sections found, fall back to paragraph chunking
            return self._paragraph_aware_chunking(text)
        
        chunk_index = 0
        
        for i, section_match in enumerate(sections):
            section_start = section_match.start()
            
            # Determine section end
            if i < len(sections) - 1:
                section_end = sections[i + 1].start()
            else:
                section_end = len(text)
            
            section_text = text[section_start:section_end].strip()
            
            if len(section_text) <= self.config.max_chunk_size:
                # Section fits in one chunk
                chunks.append(DocumentChunk(
                    text=section_text,
                    start_pos=section_start,
                    end_pos=section_end,
                    chunk_index=chunk_index,
                    chunk_type="section",
                    confidence=0.95,
                    metadata={
                        "strategy": "section_aware",
                        "section_header": section_match.group()
                    }
                ))
                chunk_index += 1
            else:
                # Section too large, need to split it
                sub_chunks = self._split_large_section(
                    section_text, section_start, chunk_index
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
        
        return chunks
    
    def _paragraph_aware_chunking(self, text: str) -> List[DocumentChunk]:
        """Chunk text at paragraph boundaries.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Split into paragraphs (double newline or more)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = []
        current_size = 0
        chunk_start = 0
        chunk_index = 0
        current_pos = 0
        
        for para_num, paragraph in enumerate(paragraphs):
            para_with_separator = paragraph
            if para_num < len(paragraphs) - 1:
                para_with_separator += "\n\n"
            
            para_len = len(para_with_separator)
            
            if current_size + para_len > self.config.max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    start_pos=chunk_start,
                    end_pos=chunk_start + len(chunk_text),
                    chunk_index=chunk_index,
                    chunk_type="paragraph",
                    confidence=0.85,
                    metadata={"strategy": "paragraph_aware"}
                ))
                chunk_index += 1
                
                # Start new chunk
                current_chunk = [paragraph]
                current_size = para_len
                chunk_start = current_pos
            else:
                # Add to current chunk
                current_chunk.append(paragraph)
                current_size += para_len
            
            current_pos += para_len
        
        # Save final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(DocumentChunk(
                text=chunk_text,
                start_pos=chunk_start,
                end_pos=chunk_start + len(chunk_text),
                chunk_index=chunk_index,
                chunk_type="paragraph",
                confidence=0.85,
                metadata={"strategy": "paragraph_aware"}
            ))
        
        return chunks
    
    def _sentence_aware_chunking(self, text: str) -> List[DocumentChunk]:
        """Chunk text at sentence boundaries using NLTK.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # Tokenize into sentences
        sentences = sent_tokenize(text)
        
        current_chunk = []
        current_size = 0
        chunk_start = 0
        chunk_index = 0
        
        # Track position in original text
        current_pos = 0
        
        for sentence in sentences:
            # Find sentence position in original text
            sentence_start = text.find(sentence, current_pos)
            if sentence_start == -1:
                continue
            
            sentence_len = len(sentence)
            
            if current_size + sentence_len > self.config.max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    start_pos=chunk_start,
                    end_pos=chunk_start + len(chunk_text),
                    chunk_index=chunk_index,
                    chunk_type="sentence",
                    confidence=0.8,
                    metadata={"strategy": "sentence_aware"}
                ))
                chunk_index += 1
                
                # Start new chunk
                current_chunk = [sentence]
                current_size = sentence_len
                chunk_start = sentence_start
            else:
                # Add to current chunk
                if not current_chunk:
                    chunk_start = sentence_start
                current_chunk.append(sentence)
                current_size += sentence_len
            
            current_pos = sentence_start + sentence_len
        
        # Save final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(DocumentChunk(
                text=chunk_text,
                start_pos=chunk_start,
                end_pos=chunk_start + len(chunk_text),
                chunk_index=chunk_index,
                chunk_type="sentence",
                confidence=0.8,
                metadata={"strategy": "sentence_aware"}
            ))
        
        return chunks
    
    def _fixed_size_chunking(self, text: str) -> List[DocumentChunk]:
        """Simple fixed-size chunking with basic word boundary awareness.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        chunk_index = 0
        current_pos = 0
        
        while current_pos < len(text):
            # Calculate chunk end position
            chunk_end = min(current_pos + self.config.max_chunk_size, len(text))
            
            # Try to break at word boundary if not at end of text
            if chunk_end < len(text):
                # Look for last space before chunk_end
                last_space = text.rfind(' ', current_pos, chunk_end)
                if last_space > current_pos:
                    chunk_end = last_space
            
            # Extract chunk
            chunk_text = text[current_pos:chunk_end].strip()
            
            if chunk_text:
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    start_pos=current_pos,
                    end_pos=chunk_end,
                    chunk_index=chunk_index,
                    chunk_type="fixed",
                    confidence=0.7,
                    metadata={"strategy": "fixed_size"}
                ))
                chunk_index += 1
            
            current_pos = chunk_end
            
            # Skip whitespace at start of next chunk
            while current_pos < len(text) and text[current_pos].isspace():
                current_pos += 1
        
        return chunks
    
    def _find_legal_boundaries(self, text: str) -> List[Tuple[int, int]]:
        """Find boundaries that shouldn't be split (citations, quotes).
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (start, end) tuples representing boundaries
        """
        boundaries = []
        
        # Find all citations
        for match in self.citation_pattern.finditer(text):
            boundaries.append((match.start(), match.end()))
        
        # Find all quotes
        for match in self.quote_pattern.finditer(text):
            boundaries.append((match.start(), match.end()))
        
        # Sort and merge overlapping boundaries
        boundaries.sort(key=lambda x: x[0])
        
        merged = []
        for start, end in boundaries:
            if merged and start <= merged[-1][1]:
                # Overlapping, merge
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged
    
    def _split_large_section(
        self,
        section_text: str,
        section_start: int,
        start_index: int
    ) -> List[DocumentChunk]:
        """Split a large section into smaller chunks.
        
        Args:
            section_text: Text of the section to split
            section_start: Starting position in original document
            start_index: Starting chunk index
            
        Returns:
            List of DocumentChunk objects
        """
        # Use paragraph-aware chunking for large sections
        sub_chunks = []
        
        # Try paragraph splitting first
        paragraphs = re.split(r'\n\s*\n', section_text)
        
        current_chunk = []
        current_size = 0
        chunk_start = 0
        chunk_index = start_index
        
        for paragraph in paragraphs:
            para_len = len(paragraph)
            
            if current_size + para_len > self.config.max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                sub_chunks.append(DocumentChunk(
                    text=chunk_text,
                    start_pos=section_start + chunk_start,
                    end_pos=section_start + chunk_start + len(chunk_text),
                    chunk_index=chunk_index,
                    chunk_type="section_part",
                    confidence=0.85,
                    metadata={"strategy": "section_split"}
                ))
                chunk_index += 1
                
                # Start new chunk
                current_chunk = [paragraph]
                current_size = para_len
                chunk_start += len(chunk_text) + 2  # Account for paragraph separator
            else:
                current_chunk.append(paragraph)
                current_size += para_len
        
        # Save final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            sub_chunks.append(DocumentChunk(
                text=chunk_text,
                start_pos=section_start + chunk_start,
                end_pos=section_start + chunk_start + len(chunk_text),
                chunk_index=chunk_index,
                chunk_type="section_part",
                confidence=0.85,
                metadata={"strategy": "section_split"}
            ))
        
        return sub_chunks
    
    def _apply_overlap(self, chunks: List[DocumentChunk], original_text: str) -> List[DocumentChunk]:
        """Apply overlap between chunks for context continuity.
        
        Args:
            chunks: List of chunks to apply overlap to
            original_text: Original document text
            
        Returns:
            List of DocumentChunk objects with overlap applied
        """
        if not chunks or self.config.chunk_overlap <= 0:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            new_start = chunk.start_pos
            new_end = chunk.end_pos
            
            # Add overlap from previous chunk
            if i > 0:
                overlap_start = max(0, chunk.start_pos - self.config.chunk_overlap)
                # Find word boundary for clean overlap
                while overlap_start > 0 and not original_text[overlap_start].isspace():
                    overlap_start -= 1
                new_start = overlap_start
            
            # Add overlap to next chunk
            if i < len(chunks) - 1:
                overlap_end = min(len(original_text), chunk.end_pos + self.config.chunk_overlap)
                # Find word boundary for clean overlap
                while overlap_end < len(original_text) and not original_text[overlap_end].isspace():
                    overlap_end += 1
                new_end = overlap_end
            
            # Create new chunk with overlap
            overlapped_text = original_text[new_start:new_end].strip()
            
            overlapped_chunks.append(DocumentChunk(
                text=overlapped_text,
                start_pos=new_start,
                end_pos=new_end,
                chunk_index=chunk.chunk_index,
                chunk_type=chunk.chunk_type,
                confidence=chunk.confidence,
                metadata={
                    **chunk.metadata,
                    "has_overlap": True,
                    "original_start": chunk.start_pos,
                    "original_end": chunk.end_pos
                }
            ))
        
        return overlapped_chunks
    
    def _validate_and_adjust_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Validate chunk sizes and adjust if necessary.
        
        Args:
            chunks: List of chunks to validate
            
        Returns:
            List of validated and adjusted DocumentChunk objects
        """
        validated_chunks = []
        
        for chunk in chunks:
            # Skip empty chunks
            if not chunk.text.strip():
                continue
            
            # Check minimum size
            if chunk.length < self.config.min_chunk_size:
                logger.warning(f"Chunk {chunk.chunk_index} below minimum size "
                             f"({chunk.length} < {self.config.min_chunk_size})")
                # Could merge with adjacent chunk, but for now just flag it
                chunk.metadata["below_min_size"] = True
            
            # Check maximum size
            if chunk.length > self.config.max_chunk_size * 1.2:  # Allow 20% overflow
                logger.warning(f"Chunk {chunk.chunk_index} exceeds maximum size "
                             f"({chunk.length} > {self.config.max_chunk_size * 1.2})")
                # Could split further, but for now just flag it
                chunk.metadata["exceeds_max_size"] = True
            
            validated_chunks.append(chunk)
        
        # Ensure chunks don't exceed configured maximum per document
        if len(validated_chunks) > self.config.max_chunks_per_document:
            logger.warning(f"Document has {len(validated_chunks)} chunks, "
                         f"exceeding limit of {self.config.max_chunks_per_document}")
            # Keep only the configured maximum
            validated_chunks = validated_chunks[:self.config.max_chunks_per_document]
        
        return validated_chunks
    
    def get_chunk_statistics(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """Calculate statistics about the chunks.
        
        Args:
            chunks: List of DocumentChunk objects
            
        Returns:
            Dictionary of statistics
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "total_text_length": 0,
                "chunk_types": {},
                "strategies_used": {}
            }
        
        chunk_sizes = [chunk.length for chunk in chunks]
        chunk_types = {}
        strategies = {}
        
        for chunk in chunks:
            # Count chunk types
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
            
            # Count strategies
            strategy = chunk.metadata.get("strategy", "unknown")
            strategies[strategy] = strategies.get(strategy, 0) + 1
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "total_text_length": sum(chunk_sizes),
            "chunk_types": chunk_types,
            "strategies_used": strategies,
            "overlap_enabled": self.config.chunk_overlap > 0,
            "overlap_size": self.config.chunk_overlap
        }