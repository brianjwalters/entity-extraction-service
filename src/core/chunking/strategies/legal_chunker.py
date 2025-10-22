"""
Legal document specific chunking strategy.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import logging

# CLAUDE.md Compliant: Absolute imports
from src.core.chunking.strategies.semantic_chunker import SemanticChunker
from src.models.responses import DocumentChunk

logger = logging.getLogger(__name__)


class LegalChunker(SemanticChunker):
    """Legal document specific chunking that preserves citations and legal structure."""
    
    def __init__(self, settings):
        super().__init__(settings)
        
        # Legal citation patterns
        self.citation_patterns = [
            # Case citations: Brown v. Board, 347 U.S. 483 (1954)
            re.compile(r'\b[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+.*?\(\d{4}\)', re.IGNORECASE),
            # Statute citations: 42 U.S.C. § 1983
            re.compile(r'\b\d+\s+U\.S\.C\.?\s*§\s*\d+', re.IGNORECASE),
            # Code of Federal Regulations: 29 C.F.R. § 1630.2
            re.compile(r'\b\d+\s+C\.F\.R\.?\s*§\s*[\d.]+', re.IGNORECASE),
            # Federal Register: 65 Fed. Reg. 68,058
            re.compile(r'\b\d+\s+Fed\.?\s+Reg\.?\s+[\d,]+', re.IGNORECASE),
            # Court rules: Fed. R. Civ. P. 12(b)(6)
            re.compile(r'\b(?:Fed\.?\s+R\.?\s+(?:Civ\.?\s+P|Crim\.?\s+P|Evid\.?|App\.?\s+P)\.?\s*\d+(?:\([^)]+\))*)', re.IGNORECASE),
            # State citations: RCW 2.28.010
            re.compile(r'\b[A-Z]{2,4}\.?\s*\d+[\d.]*', re.IGNORECASE),
        ]
        
        # Legal structure patterns
        self.structure_patterns = {
            'section_header': re.compile(r'^\s*(?:SECTION|SEC\.|§)\s+\d+', re.MULTILINE | re.IGNORECASE),
            'subsection': re.compile(r'^\s*\([a-z0-9]+\)', re.MULTILINE),
            'numbered_paragraph': re.compile(r'^\s*\d+\.\s+', re.MULTILINE),
            'whereas_clause': re.compile(r'\bWHEREAS\b', re.IGNORECASE),
            'now_therefore': re.compile(r'\bNOW,?\s+THEREFORE\b', re.IGNORECASE),
            'legal_conclusion': re.compile(r'\b(?:HELD|CONCLUSION|RULING|ORDER)\b', re.IGNORECASE),
        }
    
    async def chunk_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk legal document preserving citations and legal structure.
        
        This method:
        1. Identifies legal citations and ensures they stay together
        2. Respects legal document structure (sections, subsections)
        3. Preserves legal reasoning flow
        4. Maintains statutory and case law references
        """
        self._validate_parameters(text, chunk_size, chunk_overlap)
        
        # Identify legal elements in the text
        legal_elements = self._identify_legal_elements(text)
        
        # Create chunks preserving legal structure
        chunks = await self._create_legal_chunks(
            text, legal_elements, chunk_size, chunk_overlap, metadata
        )
        
        logger.debug(f"LegalChunker created {len(chunks)} chunks preserving legal structure")
        return chunks
    
    def _identify_legal_elements(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Identify citations and structural elements in legal text."""
        elements = {
            'citations': [],
            'structure': [],
            'protected_spans': []  # Spans that should not be split
        }
        
        # Find citations
        for i, pattern in enumerate(self.citation_patterns):
            for match in pattern.finditer(text):
                elements['citations'].append({
                    'type': f'citation_type_{i}',
                    'content': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'pattern': i
                })
                
                # Mark citation as protected span
                elements['protected_spans'].append({
                    'start': match.start(),
                    'end': match.end(),
                    'type': 'citation'
                })
        
        # Find structural elements
        for struct_type, pattern in self.structure_patterns.items():
            for match in pattern.finditer(text):
                elements['structure'].append({
                    'type': struct_type,
                    'content': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Find legal reasoning blocks (paragraphs with legal terms)
        legal_terms = [
            r'\bheld\s+that\b', r'\bruling\s+that\b', r'\bdecision\s+in\b',
            r'\bstatute\s+provides\b', r'\bregulation\s+states\b',
            r'\bcourt\s+found\b', r'\bjudge\s+determined\b',
            r'\bplaintiff\s+argues\b', r'\bdefendant\s+contends\b'
        ]
        
        legal_term_pattern = re.compile('|'.join(legal_terms), re.IGNORECASE)
        
        # Find paragraphs with legal reasoning
        paragraphs = text.split('\n\n')
        current_pos = 0
        
        for paragraph in paragraphs:
            if legal_term_pattern.search(paragraph):
                para_start = text.find(paragraph, current_pos)
                if para_start >= 0:
                    elements['protected_spans'].append({
                        'start': para_start,
                        'end': para_start + len(paragraph),
                        'type': 'legal_reasoning'
                    })
            current_pos += len(paragraph) + 2  # Account for \n\n
        
        # Sort protected spans by position
        elements['protected_spans'].sort(key=lambda x: x['start'])
        
        return elements
    
    async def _create_legal_chunks(
        self,
        text: str,
        legal_elements: Dict[str, List[Dict[str, Any]]],
        chunk_size: int,
        chunk_overlap: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Create chunks that respect legal structure."""
        
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        # Create breakpoints that respect legal structure
        breakpoints = self._create_legal_breakpoints(text, legal_elements)
        
        while current_pos < len(text):
            chunk_start = current_pos
            target_end = chunk_start + chunk_size
            
            # Find best end position respecting legal elements
            chunk_end = self._find_legal_chunk_end(
                text, chunk_start, target_end, breakpoints, legal_elements
            )
            
            # Extract chunk content
            chunk_content = text[chunk_start:chunk_end].strip()
            
            if chunk_content:
                # Analyze chunk for legal content
                chunk_analysis = self._analyze_legal_chunk(chunk_content, legal_elements)
                
                # Create chunk with legal metadata
                legal_metadata = {
                    **(metadata or {}),
                    "chunking_strategy": "legal",
                    "preserves_citations": True,
                    "preserves_legal_structure": True,
                    **chunk_analysis
                }
                
                chunk = self._create_chunk(
                    content=chunk_content,
                    start_position=chunk_start,
                    end_position=chunk_end,
                    chunk_index=chunk_index,
                    metadata=legal_metadata
                )
                
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next position with overlap
            if chunk_end >= len(text):
                break
                
            # Calculate next start with legal-aware overlap
            next_start = self._calculate_legal_overlap(
                text, chunk_start, chunk_end, chunk_overlap, legal_elements
            )
            
            current_pos = max(next_start, current_pos + 1)  # Ensure progress
        
        return chunks
    
    def _create_legal_breakpoints(
        self, 
        text: str, 
        legal_elements: Dict[str, List[Dict[str, Any]]]
    ) -> List[int]:
        """Create breakpoints that respect legal structure."""
        breakpoints = [0]  # Start of document
        
        # Add structural breakpoints
        for element in legal_elements['structure']:
            breakpoints.append(element['start'])
            breakpoints.append(element['end'])
        
        # Add paragraph breaks (double newlines)
        for match in re.finditer(r'\n\s*\n', text):
            breakpoints.append(match.end())
        
        # Add sentence endings that are not within citations
        sentence_pattern = re.compile(r'[.!?]+\s+')
        protected_spans = legal_elements['protected_spans']
        
        for match in sentence_pattern.finditer(text):
            pos = match.end()
            
            # Check if this position is within a protected span
            in_protected = any(
                span['start'] <= pos <= span['end'] 
                for span in protected_spans
            )
            
            if not in_protected:
                breakpoints.append(pos)
        
        # Sort and remove duplicates
        breakpoints = sorted(set(breakpoints))
        
        # Add end of document
        if breakpoints[-1] != len(text):
            breakpoints.append(len(text))
        
        return breakpoints
    
    def _find_legal_chunk_end(
        self,
        text: str,
        start: int,
        target_end: int,
        breakpoints: List[int],
        legal_elements: Dict[str, List[Dict[str, Any]]]
    ) -> int:
        """Find the best end position for a legal chunk."""
        
        # Check if target_end would split a protected span
        for span in legal_elements['protected_spans']:
            if span['start'] < target_end < span['end']:
                # We would split a citation or legal reasoning
                if span['start'] > start + (target_end - start) * 0.5:
                    # Citation is in latter half, end before it
                    return span['start']
                else:
                    # Citation is in first half, include it
                    target_end = span['end']
                break
        
        # Find the best breakpoint near target_end
        best_end = target_end
        
        # Look for breakpoints within acceptable range
        acceptable_range = int(target_end - start) * 0.3  # 30% flexibility
        
        for bp in reversed(breakpoints):
            if start < bp <= target_end:
                best_end = bp
                break
            elif target_end < bp <= target_end + acceptable_range:
                # Slightly over target but at a good break
                best_end = bp
                break
        
        # Ensure we don't exceed document length
        return min(best_end, len(text))
    
    def _analyze_legal_chunk(
        self, 
        content: str, 
        legal_elements: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Analyze chunk content for legal elements."""
        analysis = {
            "citation_count": 0,
            "has_case_citations": False,
            "has_statute_citations": False,
            "has_legal_reasoning": False,
            "structural_elements": [],
            "legal_terms": []
        }
        
        # Count citations within this chunk
        for citation in legal_elements['citations']:
            if citation['content'] in content:
                analysis["citation_count"] += 1
                
                # Categorize citation type
                if 'v.' in citation['content'].lower():
                    analysis["has_case_citations"] = True
                if any(code in citation['content'] for code in ['U.S.C.', 'C.F.R.', 'RCW']):
                    analysis["has_statute_citations"] = True
        
        # Check for legal reasoning indicators
        reasoning_indicators = [
            'held that', 'ruling that', 'court found', 'judge determined',
            'plaintiff argues', 'defendant contends', 'therefore', 'however',
            'consequently', 'in conclusion'
        ]
        
        for indicator in reasoning_indicators:
            if indicator.lower() in content.lower():
                analysis["has_legal_reasoning"] = True
                analysis["legal_terms"].append(indicator)
        
        # Identify structural elements
        for element in legal_elements['structure']:
            if element['content'] in content:
                analysis["structural_elements"].append(element['type'])
        
        return analysis
    
    def _calculate_legal_overlap(
        self,
        text: str,
        chunk_start: int,
        chunk_end: int,
        overlap_size: int,
        legal_elements: Dict[str, List[Dict[str, Any]]]
    ) -> int:
        """Calculate overlap that respects legal elements."""
        if overlap_size <= 0:
            return chunk_end
        
        # Find a good overlap point that doesn't split legal elements
        overlap_start = max(chunk_end - overlap_size, chunk_start)
        
        # Check if overlap would split any protected spans
        for span in legal_elements['protected_spans']:
            if span['start'] < overlap_start < span['end']:
                # Move overlap start to avoid splitting
                if span['end'] < chunk_end:
                    overlap_start = span['end']
                else:
                    overlap_start = span['start']
                break
        
        return overlap_start