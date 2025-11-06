#!/usr/bin/env python3
"""
Eyecite Citation Extraction Test Script

Extracts legal citations from PDF documents using Eyecite library.
Outputs both structured JSON and human-readable TXT formats.
"""

import json
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

import pypdf
from eyecite import clean_text, get_citations, resolve_citations
from eyecite.models import (
    FullCaseCitation,
    ShortCaseCitation,
    IdCitation,
    SupraCitation,
)


class CitationExtractor:
    """Extract legal citations from PDF documents using Eyecite."""

    def __init__(self, docs_dir: Path, results_dir: Path):
        """
        Initialize extractor.

        Args:
            docs_dir: Directory containing test PDF documents
            results_dir: Directory to save extraction results
        """
        self.docs_dir = docs_dir
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content
        """
        print(f"📄 Extracting text from {pdf_path.name}...")
        reader = pypdf.PdfReader(str(pdf_path))
        text_parts = []

        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            text_parts.append(text)
            print(f"   Extracted page {page_num}/{len(reader.pages)}")

        full_text = "\n\n".join(text_parts)
        print(f"   ✓ Extracted {len(full_text):,} characters from {len(reader.pages)} pages")
        return full_text

    def extract_citations(self, text: str) -> tuple[List[Any], Dict[Any, List[Any]], str]:
        """
        Extract citations using Eyecite.

        Args:
            text: Document text

        Returns:
            Tuple of (citations list, resolved citations dict, cleaned text)
        """
        print("🔍 Cleaning text...")
        cleaned_text = clean_text(text, ["all_whitespace"])
        print(f"   ✓ Cleaned text: {len(cleaned_text):,} characters")

        print("🔍 Extracting citations with Eyecite...")
        start_time = time.time()
        citations = get_citations(cleaned_text)
        extraction_time = time.time() - start_time
        print(f"   ✓ Found {len(citations)} citations in {extraction_time:.2f} seconds")

        print("🔗 Resolving citation references...")
        resolutions = resolve_citations(citations)
        print(f"   ✓ Resolved to {len(resolutions)} unique resources")

        return citations, resolutions, cleaned_text

    def citation_to_dict(self, citation: Any) -> Dict[str, Any]:
        """
        Convert citation object to dictionary.

        Args:
            citation: Eyecite citation object

        Returns:
            Dictionary representation
        """
        citation_type = type(citation).__name__

        base_dict = {
            "type": citation_type,
            "text": citation.matched_text(),
            "span": {"start": citation.span()[0], "end": citation.span()[1]},
        }

        # Add type-specific fields
        if isinstance(citation, FullCaseCitation):
            metadata = citation.metadata
            base_dict.update({
                "volume": getattr(citation, "volume", None),
                "reporter": getattr(citation, "reporter", None),
                "page": getattr(citation, "page", None),
                "year": getattr(metadata, "year", None),
                "court": str(getattr(metadata, "court", "")),
                "plaintiff": getattr(metadata, "plaintiff", None),
                "defendant": getattr(metadata, "defendant", None),
                "pin_cite": getattr(metadata, "pin_cite", None),
            })
        elif isinstance(citation, ShortCaseCitation):
            metadata = citation.metadata
            base_dict.update({
                "volume": getattr(citation, "volume", None),
                "reporter": getattr(citation, "reporter", None),
                "page": getattr(citation, "page", None),
                "pin_cite": getattr(metadata, "pin_cite", None),
            })
        elif isinstance(citation, IdCitation):
            base_dict.update({
                "id_type": str(citation),
            })
        elif isinstance(citation, SupraCitation):
            base_dict.update({
                "volume": getattr(citation, "volume", None),
            })

        return base_dict

    def generate_human_readable_output(
        self,
        citations: List[Any],
        resolutions: Dict[Any, List[Any]],
        cleaned_text: str,
    ) -> str:
        """
        Generate human-readable citation report.

        Args:
            citations: List of citation objects
            resolutions: Dictionary of resolved citations
            cleaned_text: Cleaned document text

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("EYECITE CITATION EXTRACTION RESULTS")
        lines.append("=" * 80)
        lines.append("")

        # Statistics
        lines.append("📊 EXTRACTION STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Total citations found: {len(citations)}")
        lines.append(f"Unique resources: {len(resolutions)}")

        # Citation type breakdown
        type_counts = Counter(type(c).__name__ for c in citations)
        lines.append(f"\nCitation types:")
        for citation_type, count in type_counts.most_common():
            lines.append(f"  - {citation_type}: {count}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("ALL CITATIONS (Grouped by Resource)")
        lines.append("=" * 80)
        lines.append("")

        # Group by resolved resource
        for idx, (resource, cites) in enumerate(resolutions.items(), 1):
            lines.append(f"\n[{idx}] RESOURCE: {resource.citation.matched_text()}")
            lines.append("-" * 80)

            for cite_idx, cite in enumerate(cites, 1):
                citation_type = type(cite).__name__
                matched_text = cite.matched_text()
                span_start, span_end = cite.span()

                # Get context (50 chars before and after)
                context_start = max(0, span_start - 50)
                context_end = min(len(cleaned_text), span_end + 50)
                context = cleaned_text[context_start:context_end]
                context = context.replace("\n", " ").strip()

                lines.append(f"\n  Citation {cite_idx}: [{citation_type}]")
                lines.append(f"    Text: {matched_text}")
                lines.append(f"    Position: {span_start}-{span_end}")

                # Add metadata for FullCaseCitation
                if isinstance(cite, FullCaseCitation):
                    metadata = cite.metadata
                    if metadata.year:
                        lines.append(f"    Year: {metadata.year}")
                    if metadata.court:
                        lines.append(f"    Court: {metadata.court}")
                    if metadata.plaintiff and metadata.defendant:
                        lines.append(f"    Parties: {metadata.plaintiff} v. {metadata.defendant}")

                lines.append(f"    Context: ...{context}...")

        lines.append("")
        lines.append("=" * 80)
        lines.append("INDIVIDUAL CITATIONS (Sequential Order)")
        lines.append("=" * 80)
        lines.append("")

        for idx, cite in enumerate(citations, 1):
            citation_type = type(cite).__name__
            matched_text = cite.matched_text()
            lines.append(f"{idx:4d}. [{citation_type:20s}] {matched_text}")

        return "\n".join(lines)

    def save_results(
        self,
        document_name: str,
        citations: List[Any],
        resolutions: Dict[Any, List[Any]],
        cleaned_text: str,
    ):
        """
        Save extraction results to JSON and TXT files.

        Args:
            document_name: Name of source document
            citations: List of citation objects
            resolutions: Dictionary of resolved citations
            cleaned_text: Cleaned document text
        """
        base_name = Path(document_name).stem

        # Save JSON (structured data)
        json_data = {
            "document": document_name,
            "total_citations": len(citations),
            "unique_resources": len(resolutions),
            "citation_types": dict(Counter(type(c).__name__ for c in citations)),
            "citations": [self.citation_to_dict(c) for c in citations],
            "resolved_resources": {
                str(resource.citation.matched_text()): [
                    self.citation_to_dict(cite) for cite in cites
                ]
                for resource, cites in resolutions.items()
            },
        }

        json_path = self.results_dir / f"{base_name}_citations.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved JSON results: {json_path}")

        # Save TXT (human-readable)
        txt_content = self.generate_human_readable_output(citations, resolutions, cleaned_text)
        txt_path = self.results_dir / f"{base_name}_citations.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)
        print(f"💾 Saved TXT results: {txt_path}")

    def process_document(self, document_name: str):
        """
        Process a single PDF document.

        Args:
            document_name: Name of PDF file (e.g., 'rahimi.pdf')
        """
        print(f"\n{'=' * 80}")
        print(f"PROCESSING: {document_name}")
        print(f"{'=' * 80}\n")

        pdf_path = self.docs_dir / document_name
        if not pdf_path.exists():
            print(f"❌ Error: File not found: {pdf_path}")
            return

        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)

        # Extract citations
        citations, resolutions, cleaned_text = self.extract_citations(text)

        # Save results
        self.save_results(document_name, citations, resolutions, cleaned_text)

        print(f"\n✅ Successfully processed {document_name}")
        print(f"   Total citations: {len(citations)}")
        print(f"   Unique resources: {len(resolutions)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract legal citations from PDF documents using Eyecite"
    )
    parser.add_argument(
        "--doc",
        choices=["rahimi", "dobbs", "all"],
        default="all",
        help="Document to process (default: all)",
    )

    args = parser.parse_args()

    # Setup paths
    script_dir = Path(__file__).parent
    docs_dir = script_dir.parent / "docs"
    results_dir = script_dir / "results"

    # Create extractor
    extractor = CitationExtractor(docs_dir, results_dir)

    # Process documents
    if args.doc == "all":
        extractor.process_document("Rahimi.pdf")
        extractor.process_document("dobbs.pdf")
    elif args.doc == "rahimi":
        extractor.process_document("Rahimi.pdf")
    elif args.doc == "dobbs":
        extractor.process_document("dobbs.pdf")

    print(f"\n{'=' * 80}")
    print("🎉 EXTRACTION COMPLETE!")
    print(f"{'=' * 80}")
    print(f"\nResults saved to: {results_dir}")
    print("\nReview the following files:")
    print(f"  - {results_dir}/rahimi_citations.txt (human-readable)")
    print(f"  - {results_dir}/rahimi_citations.json (structured data)")
    print(f"  - {results_dir}/dobbs_citations.txt (human-readable)")
    print(f"  - {results_dir}/dobbs_citations.json (structured data)")


if __name__ == "__main__":
    main()
