#!/usr/bin/env python3
"""Convert Rahimi PDF to markdown for entity extraction."""

import json
from pathlib import Path
from markitdown import MarkItDown

def convert_pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to markdown using MarkItDown."""
    md_converter = MarkItDown()
    result = md_converter.convert(pdf_path)
    return result.text_content

def main():
    pdf_path = "/srv/luris/be/entity-extraction-service/tests/docs/Rahimi.pdf"
    
    print(f"Converting {pdf_path} to markdown...")
    markdown_text = convert_pdf_to_markdown(pdf_path)
    
    # Save the markdown text
    output_path = Path("rahimi_document.md")
    output_path.write_text(markdown_text)
    print(f"Saved markdown to {output_path}")
    
    # Also save as JSON for structured access
    json_output = {
        "filename": "Rahimi.pdf",
        "markdown": markdown_text,
        "length": len(markdown_text)
    }
    
    json_path = Path("rahimi_document.json")
    with open(json_path, 'w') as f:
        json.dump(json_output, f, indent=2)
    print(f"Saved JSON to {json_path}")
    
    print(f"Document length: {len(markdown_text)} characters")
    print("\nFirst 500 characters:")
    print(markdown_text[:500])

if __name__ == "__main__":
    main()