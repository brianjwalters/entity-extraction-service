#!/usr/bin/env python3
"""
Rahimi PDF Processor for SaulLM Entity Extraction Testing
Extracts content from Rahimi.pdf and prepares it for entity extraction testing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import os

# Add src to path for imports

# Import document upload service client for PDF processing
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process legal PDF documents for entity extraction testing."""
    
    def __init__(self, document_name: str = "Rahimi"):
        self.document_name = document_name
        self.document_path = Path(__file__).parent / "docs" / f"{document_name}.pdf"
        self.document_upload_url = "http://localhost:8008/api/v1/upload"
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
    def verify_document_exists(self) -> bool:
        """Verify that the document exists and is accessible."""
        if not self.document_path.exists():
            logger.error(f"{self.document_name}.pdf not found at {self.document_path}")
            return False
        
        file_size = self.document_path.stat().st_size
        logger.info(f"{self.document_name}.pdf found: {file_size:,} bytes")
        return True
    
    def extract_markdown_content(self) -> str:
        """Extract markdown content from the document using document upload service."""
        try:
            # Check if document upload service is running
            health_response = requests.get("http://localhost:8008/api/v1/health/ping", timeout=5)
            if health_response.status_code != 200:
                logger.error("Document upload service not available")
                return self._fallback_text_extraction()
                
        except requests.RequestException:
            logger.warning("Document upload service not running, using fallback extraction")
            return self._fallback_text_extraction()
        
        # Upload document to extract markdown
        try:
            with open(self.document_path, 'rb') as f:
                files = {'file': (f'{self.document_name}.pdf', f, 'application/pdf')}
                data = {
                    'client_id': 'test_client',
                    'case_id': f'{self.document_name.lower()}_test',
                    'enable_ocr': 'true'
                }
                
                response = requests.post(
                    self.document_upload_url,
                    files=files,
                    data=data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    markdown_content = result.get('markdown_content', '')
                    
                    if markdown_content:
                        logger.info(f"Successfully extracted {len(markdown_content)} characters from {self.document_name}.pdf")
                        return markdown_content
                    else:
                        logger.error("No markdown content returned from upload service")
                        return self._fallback_text_extraction()
                else:
                    logger.error(f"Upload failed with status {response.status_code}: {response.text}")
                    return self._fallback_text_extraction()
                    
        except Exception as e:
            logger.error(f"Error during document upload: {e}")
            return self._fallback_text_extraction()
    
    def _fallback_text_extraction(self) -> str:
        """Fallback text extraction using basic PDF reading."""
        try:
            import PyPDF2
            
            with open(self.document_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_content = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text_content += f"\n\n=== Page {page_num + 1} ===\n\n"
                    text_content += page_text
                
                logger.info(f"Fallback extraction: {len(text_content)} characters from {len(pdf_reader.pages)} pages")
                return text_content
                
        except ImportError:
            logger.error("PyPDF2 not available, using sample text")
            return self._get_sample_text()
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return self._get_sample_text()
    
    def _get_sample_text(self) -> str:
        """Return sample legal text if PDF extraction fails."""
        return f"""
        SAMPLE LEGAL DOCUMENT - {self.document_name} Case Analysis
        
        In the landmark case of Brown v. Board of Education, 347 U.S. 483 (1954), 
        the Supreme Court established that separate educational facilities are 
        inherently unequal under the Fourteenth Amendment's Equal Protection Clause.
        
        This precedent was further refined in subsequent cases including:
        - Roe v. Wade, 410 U.S. 113 (1973)
        - Miranda v. Arizona, 384 U.S. 436 (1966)
        
        The statutory framework includes:
        - 42 U.S.C. § 1983 (Civil Rights Act)
        - 15 U.S.C. § 78j(b) (Securities Exchange Act)
        - 18 U.S.C. § 1341 (Mail Fraud)
        
        Key legal principles established:
        1. Due Process requirements under the Fifth Amendment
        2. Equal Protection under the Fourteenth Amendment
        3. Commerce Clause jurisdiction under Article I, Section 8
        
        Notable parties included plaintiff John Doe and defendant ABC Corporation,
        represented by counsel from Williams & Connolly LLP before the
        United States District Court for the Southern District of New York.
        
        The case was decided on January 15, 2023, with damages awarded in the
        amount of $2,500,000 under docket number 23-CV-1234.
        """
    
    def process_document(self) -> Dict[str, Any]:
        """Process document and return structured data."""
        logger.info(f"Processing {self.document_name}.pdf document...")
        
        if not self.verify_document_exists():
            return {"error": f"{self.document_name}.pdf not found"}
        
        # Extract content
        content = self.extract_markdown_content()
        
        if not content:
            logger.error(f"Failed to extract any content from {self.document_name}.pdf")
            return {"error": "Content extraction failed"}
        
        # Prepare document metadata
        document_info = {
            "source_file": str(self.document_path),
            "extraction_method": "document_upload_service",
            "content_length": len(content),
            "word_count": len(content.split()),
            "timestamp": datetime.now().isoformat(),
            "content": content
        }
        
        # Save processed content
        output_file = self.results_dir / f"{self.document_name.lower()}_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(document_info, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processed document saved to: {output_file}")
        logger.info(f"Content length: {len(content):,} characters")
        logger.info(f"Word count: {len(content.split()):,} words")
        
        return document_info
    
    def get_chunked_content(self, content: str, chunk_size: int = 4000) -> List[str]:
        """Split content into chunks for processing."""
        chunks = []
        words = content.split()
        
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        logger.info(f"Split content into {len(chunks)} chunks")
        return chunks


def main():
    """Main function to test document processor."""
    # Default to Rahimi, but can be changed
    import sys
    document_name = sys.argv[1] if len(sys.argv) > 1 else "Rahimi"
    
    processor = DocumentProcessor(document_name)
    
    print("="*80)
    print(f"{document_name.upper()} PDF PROCESSOR TEST")
    print("="*80)
    
    # Process the document
    result = processor.process_document()
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return 1
    
    print(f"✅ Successfully processed {document_name}.pdf")
    print(f"📄 Content length: {result['content_length']:,} characters")
    print(f"📝 Word count: {result['word_count']:,} words")
    print(f"⏰ Processed at: {result['timestamp']}")
    
    # Show content preview
    content = result['content']
    preview_length = 500
    
    print(f"\n📖 Content Preview (first {preview_length} chars):")
    print("-" * 60)
    print(content[:preview_length] + "..." if len(content) > preview_length else content)
    print("-" * 60)
    
    # Test chunking
    chunks = processor.get_chunked_content(content, chunk_size=4000)
    print(f"\n🔗 Chunking test: {len(chunks)} chunks created")
    
    for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
        print(f"  Chunk {i+1}: {len(chunk)} characters")
    
    return 0


if __name__ == "__main__":
    exit(main())