#!/usr/bin/env python3
"""
Smart Chunking Test Script for Dobbs.pdf Legal Document
Tests legal-aware chunking with citation and quote preservation
"""

import yaml
import re
import json
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
import PyPDF2
import pdfplumber
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chunking_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Metadata for each chunk"""
    chunk_index: int
    total_chunks: int
    start_char: int
    end_char: int
    chunk_size: int
    overlap_size: int
    section_context: str
    contains_citations: bool
    citation_count: int
    entity_types: List[str]
    page_numbers: List[int]
    validation_passed: bool
    validation_errors: List[str]

@dataclass
class ChunkingResult:
    """Complete result of chunking operation"""
    chunks: List[Dict]
    metadata: List[ChunkMetadata]
    statistics: Dict
    validation_report: Dict
    timestamp: str

class LegalChunker:
    """Smart chunking implementation for legal documents"""
    
    def __init__(self, config_path: str):
        """Initialize with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.chunking_config = self.config['chunking']
        self.max_chunk_size = self.chunking_config['max_chunk_size']
        self.overlap_size = self.chunking_config['overlap_size']
        self.min_chunk_size = self.chunking_config['min_chunk_size']
        
        # Compile regex patterns for citations
        self.citation_patterns = []
        if self.chunking_config['preserve_boundaries']['citations']['enabled']:
            for pattern_config in self.chunking_config['preserve_boundaries']['citations']['patterns']:
                self.citation_patterns.append({
                    'regex': re.compile(pattern_config['pattern'], re.IGNORECASE),
                    'priority': pattern_config['priority']
                })
        
        # Section markers
        self.section_patterns = []
        if self.chunking_config['preserve_boundaries']['sections']['enabled']:
            for marker in self.chunking_config['preserve_boundaries']['sections']['markers']:
                self.section_patterns.append({
                    'regex': re.compile(marker['pattern'], re.MULTILINE),
                    'type': marker['type'],
                    'priority': marker['priority']
                })
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, Dict]:
        """Extract text from PDF with page tracking"""
        logger.info(f"Extracting text from: {pdf_path}")
        
        text_content = ""
        page_boundaries = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    start_pos = len(text_content)
                    text_content += page_text + "\n\n"
                    end_pos = len(text_content)
                    
                    page_boundaries.append({
                        'page': page_num,
                        'start': start_pos,
                        'end': end_pos
                    })
                    
                    logger.debug(f"Extracted page {page_num}: {len(page_text)} characters")
        
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            # Fallback to PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    start_pos = len(text_content)
                    text_content += page_text + "\n\n"
                    end_pos = len(text_content)
                    
                    page_boundaries.append({
                        'page': page_num + 1,
                        'start': start_pos,
                        'end': end_pos
                    })
        
        metadata = {
            'total_pages': len(page_boundaries),
            'total_characters': len(text_content),
            'page_boundaries': page_boundaries
        }
        
        logger.info(f"Extracted {len(text_content)} characters from {len(page_boundaries)} pages")
        return text_content, metadata
    
    def find_citations(self, text: str) -> List[Dict]:
        """Find all citations in text"""
        citations = []
        
        for pattern_config in self.citation_patterns:
            pattern = pattern_config['regex']
            for match in pattern.finditer(text):
                citations.append({
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'priority': pattern_config['priority']
                })
        
        # Sort by position
        citations.sort(key=lambda x: x['start'])
        return citations
    
    def find_quotes(self, text: str) -> List[Dict]:
        """Find quoted sections in text"""
        quotes = []
        quote_pattern = re.compile(r'[""]([^""]{10,}?)[""]', re.DOTALL)
        
        for match in quote_pattern.finditer(text):
            if len(match.group(1)) <= self.chunking_config['preserve_boundaries']['quotes']['max_quote_length']:
                quotes.append({
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'length': len(match.group())
                })
        
        return quotes
    
    def find_sections(self, text: str) -> List[Dict]:
        """Find section boundaries in text"""
        sections = []
        
        for pattern_config in self.section_patterns:
            pattern = pattern_config['regex']
            for match in pattern.finditer(text):
                sections.append({
                    'marker': match.group().strip(),
                    'start': match.start(),
                    'end': match.end(),
                    'type': pattern_config['type'],
                    'priority': pattern_config['priority']
                })
        
        sections.sort(key=lambda x: x['start'])
        return sections
    
    def find_safe_split_point(self, text: str, start: int, ideal_end: int, 
                            citations: List[Dict], quotes: List[Dict]) -> int:
        """Find a safe point to split the text"""
        # Check if ideal_end is within a citation or quote
        for citation in citations:
            if citation['start'] <= ideal_end <= citation['end']:
                # Move split point after the citation
                logger.debug(f"Adjusting split to preserve citation at {citation['start']}-{citation['end']}")
                return citation['end']
        
        for quote in quotes:
            if quote['start'] <= ideal_end <= quote['end']:
                # For long quotes, try to split at sentence boundary within quote
                if quote['length'] > self.max_chunk_size * 0.7:
                    # Find sentence boundary within quote
                    sentence_end = text.rfind('. ', quote['start'], ideal_end)
                    if sentence_end > quote['start']:
                        return sentence_end + 2
                # Otherwise, move split after the quote
                logger.debug(f"Adjusting split to preserve quote at {quote['start']}-{quote['end']}")
                return quote['end']
        
        # Try to find natural break points (in order of preference)
        search_window = 200  # Look within 200 chars of ideal point
        search_start = max(start, ideal_end - search_window)
        search_end = min(len(text), ideal_end + search_window)
        search_text = text[search_start:search_end]
        
        # 1. Paragraph boundary
        para_break = search_text.rfind('\n\n')
        if para_break != -1:
            return search_start + para_break + 2
        
        # 2. Sentence boundary
        sentence_ends = ['. ', '.\n', '? ', '?\n', '! ', '!\n']
        best_sentence_pos = -1
        for end_marker in sentence_ends:
            pos = search_text.rfind(end_marker)
            if pos > best_sentence_pos:
                best_sentence_pos = pos
        
        if best_sentence_pos != -1:
            return search_start + best_sentence_pos + 2
        
        # 3. Semicolon or colon
        semicolon = search_text.rfind('; ')
        colon = search_text.rfind(': ')
        best_punct = max(semicolon, colon)
        if best_punct != -1:
            return search_start + best_punct + 2
        
        # 4. Comma (last resort)
        comma = search_text.rfind(', ')
        if comma != -1:
            return search_start + comma + 2
        
        # If no good break point found, use the ideal end
        return ideal_end
    
    def create_chunks(self, text: str, pdf_metadata: Dict) -> List[Dict]:
        """Create chunks from text with smart boundaries"""
        logger.info("Starting smart chunking process")
        
        # Find all citations, quotes, and sections
        citations = self.find_citations(text)
        quotes = self.find_quotes(text)
        sections = self.find_sections(text)
        
        logger.info(f"Found {len(citations)} citations, {len(quotes)} quotes, {len(sections)} sections")
        
        chunks = []
        chunk_metadata = []
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            # Determine chunk end position
            ideal_chunk_end = current_pos + self.max_chunk_size
            
            # Don't go past text end
            if ideal_chunk_end >= len(text):
                chunk_end = len(text)
            else:
                # Find safe split point
                chunk_end = self.find_safe_split_point(
                    text, current_pos, ideal_chunk_end, citations, quotes
                )
            
            # Extract chunk text
            chunk_text = text[current_pos:chunk_end].strip()
            
            # Skip empty chunks
            if not chunk_text or len(chunk_text) < self.min_chunk_size:
                current_pos = chunk_end
                continue
            
            # Find which pages this chunk spans
            chunk_pages = []
            for page_info in pdf_metadata['page_boundaries']:
                if (page_info['start'] <= current_pos < page_info['end'] or
                    page_info['start'] < chunk_end <= page_info['end'] or
                    (current_pos <= page_info['start'] and chunk_end >= page_info['end'])):
                    chunk_pages.append(page_info['page'])
            
            # Count citations in this chunk
            chunk_citations = [c for c in citations 
                             if current_pos <= c['start'] < chunk_end]
            
            # Determine section context
            section_context = "Unknown"
            for section in reversed(sections):
                if section['start'] <= current_pos:
                    section_context = f"{section['type']}: {section['marker']}"
                    break
            
            # Create chunk with metadata
            chunk_data = {
                'chunk_id': f"chunk_{chunk_index:04d}",
                'text': chunk_text,
                'metadata': {
                    'chunk_index': chunk_index,
                    'start_char': current_pos,
                    'end_char': chunk_end,
                    'chunk_size': len(chunk_text),
                    'section_context': section_context,
                    'contains_citations': len(chunk_citations) > 0,
                    'citation_count': len(chunk_citations),
                    'page_numbers': chunk_pages
                }
            }
            
            chunks.append(chunk_data)
            
            # Calculate overlap start for next chunk
            if chunk_end < len(text):
                overlap_start = max(current_pos, chunk_end - self.overlap_size)
                current_pos = overlap_start
            else:
                current_pos = chunk_end
            
            chunk_index += 1
            
            if chunk_index % 10 == 0:
                logger.info(f"Created {chunk_index} chunks...")
        
        logger.info(f"Created {len(chunks)} total chunks")
        return chunks
    
    def validate_chunks(self, chunks: List[Dict], original_text: str) -> Dict:
        """Validate chunk quality and integrity"""
        logger.info("Validating chunks...")
        
        validation_report = {
            'total_chunks': len(chunks),
            'validation_errors': [],
            'statistics': {},
            'quality_metrics': {}
        }
        
        # Find all citations in original text
        all_citations = self.find_citations(original_text)
        all_quotes = self.find_quotes(original_text)
        
        # Track chunk sizes
        chunk_sizes = []
        citations_preserved = 0
        citations_split = 0
        quotes_preserved = 0
        quotes_split = 0
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk['text']
            chunk_meta = chunk['metadata']
            chunk_sizes.append(chunk_meta['chunk_size'])
            
            # Check chunk size limits
            if chunk_meta['chunk_size'] > self.max_chunk_size:
                validation_report['validation_errors'].append({
                    'chunk_id': chunk['chunk_id'],
                    'error': f"Chunk size {chunk_meta['chunk_size']} exceeds max {self.max_chunk_size}"
                })
            
            if chunk_meta['chunk_size'] < self.min_chunk_size and i < len(chunks) - 1:
                validation_report['validation_errors'].append({
                    'chunk_id': chunk['chunk_id'],
                    'error': f"Chunk size {chunk_meta['chunk_size']} below min {self.min_chunk_size}"
                })
            
            # Check citation integrity
            for citation in all_citations:
                if chunk_meta['start_char'] <= citation['start'] < chunk_meta['end_char']:
                    if citation['end'] <= chunk_meta['end_char']:
                        citations_preserved += 1
                    else:
                        citations_split += 1
                        validation_report['validation_errors'].append({
                            'chunk_id': chunk['chunk_id'],
                            'error': f"Citation split: {citation['text'][:50]}..."
                        })
            
            # Check quote integrity
            for quote in all_quotes:
                if chunk_meta['start_char'] <= quote['start'] < chunk_meta['end_char']:
                    if quote['end'] <= chunk_meta['end_char']:
                        quotes_preserved += 1
                    else:
                        if quote['length'] <= self.max_chunk_size * 0.7:
                            quotes_split += 1
                            validation_report['validation_errors'].append({
                                'chunk_id': chunk['chunk_id'],
                                'error': f"Quote split: {quote['text'][:50]}..."
                            })
            
            # Check overlap with next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap = chunk_meta['end_char'] - next_chunk['metadata']['start_char']
                if overlap < 0:
                    validation_report['validation_errors'].append({
                        'chunk_id': chunk['chunk_id'],
                        'error': f"Gap between chunks: {-overlap} characters"
                    })
                elif overlap < self.overlap_size * 0.8:
                    validation_report['validation_errors'].append({
                        'chunk_id': chunk['chunk_id'],
                        'warning': f"Overlap {overlap} below target {self.overlap_size}"
                    })
        
        # Calculate statistics
        import statistics as stats
        
        validation_report['statistics'] = {
            'total_chunks': len(chunks),
            'avg_chunk_size': stats.mean(chunk_sizes) if chunk_sizes else 0,
            'median_chunk_size': stats.median(chunk_sizes) if chunk_sizes else 0,
            'std_chunk_size': stats.stdev(chunk_sizes) if len(chunk_sizes) > 1 else 0,
            'min_chunk_size': min(chunk_sizes) if chunk_sizes else 0,
            'max_chunk_size': max(chunk_sizes) if chunk_sizes else 0
        }
        
        validation_report['quality_metrics'] = {
            'citations_found': len(all_citations),
            'citations_preserved': citations_preserved,
            'citations_split': citations_split,
            'citation_preservation_rate': (citations_preserved / len(all_citations) * 100) if all_citations else 100,
            'quotes_found': len(all_quotes),
            'quotes_preserved': quotes_preserved,
            'quotes_split': quotes_split,
            'quote_preservation_rate': (quotes_preserved / len(all_quotes) * 100) if all_quotes else 100,
            'validation_passed': len(validation_report['validation_errors']) == 0
        }
        
        logger.info(f"Validation complete. Errors: {len(validation_report['validation_errors'])}")
        logger.info(f"Citation preservation: {validation_report['quality_metrics']['citation_preservation_rate']:.1f}%")
        logger.info(f"Quote preservation: {validation_report['quality_metrics']['quote_preservation_rate']:.1f}%")
        
        return validation_report

def run_chunking_test(pdf_path: str, config_path: str, output_dir: str = None) -> ChunkingResult:
    """Run complete chunking test"""
    logger.info("=" * 80)
    logger.info("Starting Smart Chunking Test for Legal Document")
    logger.info("=" * 80)
    
    # Create output directory
    if output_dir is None:
        output_dir = Path(__file__).parent / "results"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize chunker
    chunker = LegalChunker(config_path)
    
    # Extract text from PDF
    text_content, pdf_metadata = chunker.extract_text_from_pdf(pdf_path)
    
    # Create chunks
    chunks = chunker.create_chunks(text_content, pdf_metadata)
    
    # Validate chunks
    validation_report = chunker.validate_chunks(chunks, text_content)
    
    # Create result object
    result = ChunkingResult(
        chunks=chunks,
        metadata=[],  # Would be populated with ChunkMetadata objects
        statistics=validation_report['statistics'],
        validation_report=validation_report,
        timestamp=datetime.now().isoformat()
    )
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save chunks to JSON
    chunks_file = output_dir / f"chunks_{timestamp}.json"
    with open(chunks_file, 'w') as f:
        json.dump({
            'config': chunker.config,
            'chunks': chunks,
            'validation_report': validation_report,
            'timestamp': result.timestamp
        }, f, indent=2)
    
    logger.info(f"Saved chunks to: {chunks_file}")
    
    # Save validation report
    report_file = output_dir / f"validation_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write("Smart Chunking Validation Report\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Timestamp: {result.timestamp}\n")
        f.write(f"PDF: {pdf_path}\n")
        f.write(f"Config: {config_path}\n\n")
        
        f.write("Statistics:\n")
        f.write("-" * 40 + "\n")
        for key, value in validation_report['statistics'].items():
            f.write(f"  {key}: {value}\n")
        
        f.write("\nQuality Metrics:\n")
        f.write("-" * 40 + "\n")
        for key, value in validation_report['quality_metrics'].items():
            f.write(f"  {key}: {value}\n")
        
        if validation_report['validation_errors']:
            f.write("\nValidation Issues:\n")
            f.write("-" * 40 + "\n")
            for error in validation_report['validation_errors'][:20]:  # First 20 errors
                f.write(f"  - {error}\n")
            
            if len(validation_report['validation_errors']) > 20:
                f.write(f"\n  ... and {len(validation_report['validation_errors']) - 20} more issues\n")
    
    logger.info(f"Saved validation report to: {report_file}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("CHUNKING TEST SUMMARY")
    print("=" * 80)
    print(f"Total chunks created: {len(chunks)}")
    print(f"Average chunk size: {validation_report['statistics']['avg_chunk_size']:.0f} characters")
    print(f"Citation preservation: {validation_report['quality_metrics']['citation_preservation_rate']:.1f}%")
    print(f"Quote preservation: {validation_report['quality_metrics']['quote_preservation_rate']:.1f}%")
    print(f"Validation passed: {validation_report['quality_metrics']['validation_passed']}")
    print(f"Results saved to: {output_dir}")
    print("=" * 80)
    
    return result

def main():
    """Main test execution"""
    # Paths
    pdf_path = "/srv/luris/be/tests/docs/dobbs.pdf"  # Note: lowercase 'dobbs.pdf'
    config_path = "/srv/luris/be/entity-extraction-service/tests/dobbs_testing/chunking_config.yaml"
    
    # Check if files exist
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        sys.exit(1)
    
    if not Path(config_path).exists():
        logger.error(f"Config not found: {config_path}")
        sys.exit(1)
    
    # Run test
    try:
        result = run_chunking_test(pdf_path, config_path)
        
        # Additional analysis
        if result.validation_report['quality_metrics']['validation_passed']:
            logger.info("✓ All validation checks passed!")
        else:
            logger.warning("⚠ Some validation issues detected. Review the report for details.")
        
        # Return success if citation preservation is above threshold
        if result.validation_report['quality_metrics']['citation_preservation_rate'] >= 95:
            logger.info("✓ Citation preservation target (95%) achieved!")
            return 0
        else:
            logger.warning("⚠ Citation preservation below target")
            return 1
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())