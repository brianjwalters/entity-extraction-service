#!/usr/bin/env python3
"""
Extract text from Rahimi.pdf using PyMuPDF (fitz) for PageBatch entity extraction testing.
"""

import os
import time
import fitz  # PyMuPDF

def extract_text_from_rahimi():
    """
    Extract text from Rahimi.pdf using PyMuPDF (fitz).
    """
    # Input and output paths
    pdf_path = "/srv/luris/be/entity-extraction-service/tests/docs/Rahimi.pdf"
    output_dir = "/srv/luris/be/entity-extraction-service/tests/results"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Output file paths
    text_output_path = os.path.join(output_dir, "rahimi_extracted_text.txt")
    metadata_output_path = os.path.join(output_dir, "rahimi_extraction_metadata.txt")
    
    print(f"Extracting text from: {pdf_path}")
    print(f"Output text file: {text_output_path}")
    print(f"Output metadata file: {metadata_output_path}")
    
    # Extract text using PyMuPDF
    print("Extracting text with PyMuPDF...")
    extraction_start = time.time()
    
    try:
        # Open PDF document
        doc = fitz.open(pdf_path)
        
        # Extract text from all pages
        full_text = ""
        page_texts = []
        page_count = doc.page_count  # Store before closing
        
        for page_num in range(page_count):
            page = doc[page_num]
            page_text = page.get_text()
            page_texts.append(f"--- PAGE {page_num + 1} ---\n{page_text}\n")
            full_text += page_text + "\n"
        
        doc.close()
        
        extraction_time = time.time() - extraction_start
        
        # Save extracted text
        with open(text_output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        # Save extraction metadata
        with open(metadata_output_path, 'w', encoding='utf-8') as f:
            f.write("Rahimi.pdf Text Extraction Metadata\n")
            f.write("="*50 + "\n\n")
            f.write(f"PDF Path: {pdf_path}\n")
            f.write(f"PDF Size: {os.path.getsize(pdf_path):,} bytes\n")
            f.write(f"Extraction Tool: PyMuPDF (fitz)\n")
            f.write(f"Text Extraction Time: {extraction_time:.2f} seconds\n")
            f.write(f"Extracted Text Length: {len(full_text):,} characters\n")
            f.write(f"Number of Pages: {page_count}\n")
            
            # Basic text statistics
            f.write(f"\nText Statistics:\n")
            f.write(f"  Lines: {len(full_text.splitlines())}\n")
            f.write(f"  Words (approx): {len(full_text.split())}\n")
            f.write(f"  Paragraphs (empty line separated): {len([p for p in full_text.split('\\n\\n') if p.strip()])}\n")
            
            # Page-by-page statistics
            f.write(f"\nPage Statistics:\n")
            for i, page_text in enumerate(page_texts):
                page_content = page_text.split('\n', 1)[1] if '\n' in page_text else page_text
                f.write(f"  Page {i+1}: {len(page_content.strip())} characters\n")
        
        print(f"\n✅ Text extraction completed successfully!")
        print(f"   - Extracted text: {len(full_text):,} characters")
        print(f"   - Processing time: {extraction_time:.2f} seconds")
        print(f"   - Text saved to: {text_output_path}")
        print(f"   - Metadata saved to: {metadata_output_path}")
        
        # Preview first 500 characters
        print(f"\n📄 Text Preview (first 500 characters):")
        print("-" * 60)
        print(full_text[:500])
        if len(full_text) > 500:
            print("...")
        print("-" * 60)
        
        return text_output_path, metadata_output_path, full_text
        
    except Exception as e:
        print(f"❌ Error during text extraction: {e}")
        raise

if __name__ == "__main__":
    extract_text_from_rahimi()