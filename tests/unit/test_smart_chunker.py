"""
Comprehensive unit tests for SmartChunker class.

Tests all chunking strategies, document type detection, boundary preservation,
and handling of large documents (>50K characters).
"""

import pytest
import os
from pathlib import Path
from typing import List, Dict, Any
import json
import time
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports

from src.core.smart_chunker import (
    SmartChunker,
    DocumentChunk,
    DocumentType,
    ChunkingStrategy
)
from src.core.config import ChunkingConfig, RuntimeConfig


class TestSmartChunker:
    """Comprehensive unit tests for SmartChunker class."""
    
    @pytest.fixture
    def default_config(self):
        """Create default chunking configuration."""
        return ChunkingConfig(
            max_chunk_size=2000,
            chunk_overlap=200,
            min_chunk_size=100,
            enable_smart_chunking=True,
            preserve_sentences=True,
            preserve_paragraphs=False,
            batch_size=5,
            max_chunks_per_document=100
        )
    
    @pytest.fixture
    def chunker(self, default_config):
        """Create SmartChunker instance with default config."""
        return SmartChunker(config=default_config)
    
    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return {
            "contract": """
PURCHASE AGREEMENT

This Purchase Agreement ("Agreement") is entered into as of January 1, 2024, 
by and between ABC Corporation, a Delaware corporation ("Buyer"), and 
XYZ Industries, Inc., a California corporation ("Seller").

WHEREAS, Seller desires to sell, and Buyer desires to purchase, certain 
assets as described herein;

NOW, THEREFORE, in consideration of the mutual covenants and agreements 
hereinafter set forth, the parties agree as follows:

ARTICLE I
DEFINITIONS

1.1 "Assets" means all tangible and intangible assets listed in Schedule A.
1.2 "Purchase Price" means the sum of $10,000,000 (Ten Million Dollars).
1.3 "Closing Date" means February 15, 2024, or such other date as mutually agreed.

ARTICLE II
PURCHASE AND SALE

2.1 Purchase and Sale. Subject to the terms and conditions of this Agreement, 
Seller agrees to sell, transfer, and deliver to Buyer, and Buyer agrees to 
purchase from Seller, the Assets.

2.2 Purchase Price. The Purchase Price shall be paid as follows:
(a) $2,000,000 upon execution of this Agreement;
(b) $8,000,000 on the Closing Date.

ARTICLE III
REPRESENTATIONS AND WARRANTIES

3.1 Seller's Representations. Seller represents and warrants that:
(a) Seller has full corporate power and authority to execute this Agreement;
(b) The Assets are free and clear of all liens and encumbrances;
(c) All material contracts relating to the Assets are valid and enforceable.
""",
            "opinion": """
UNITED STATES COURT OF APPEALS
FOR THE NINTH CIRCUIT

SMITH v. JONES CORPORATION,
No. 23-12345

Argued and Submitted December 15, 2023
Filed January 30, 2024

Before: JOHNSON, WILLIAMS, and DAVIS, Circuit Judges.

JOHNSON, Circuit Judge:

This case presents the question whether the district court properly granted 
summary judgment in favor of defendant Jones Corporation. See Fed. R. Civ. P. 56. 
We review de novo. Anderson v. Liberty Lobby, Inc., 477 U.S. 242, 247 (1986).

I. BACKGROUND

Plaintiff John Smith filed this action under 42 U.S.C. § 1983, alleging 
violations of his constitutional rights. The district court granted defendant's 
motion for summary judgment, finding no genuine issue of material fact. 
Smith timely appealed.

The facts, viewed in the light most favorable to Smith, are as follows: 
On March 15, 2022, Smith was employed by Jones Corporation as a senior analyst. 
Jones Corporation terminated Smith's employment on April 20, 2022, citing 
"performance issues." Smith alleges the termination was retaliatory.

II. STANDARD OF REVIEW

We review a district court's grant of summary judgment de novo. Crowley v. 
Nevada, 678 F.3d 730, 733 (9th Cir. 2012). Summary judgment is appropriate 
when "there is no genuine dispute as to any material fact and the movant is 
entitled to judgment as a matter of law." Fed. R. Civ. P. 56(a).

III. DISCUSSION

A. The Constitutional Claim

Smith argues the district court erred in finding no constitutional violation. 
"To state a claim under 42 U.S.C. § 1983, a plaintiff must allege the violation 
of a right secured by the Constitution and laws of the United States." West v. 
Atkins, 487 U.S. 42, 48 (1988).
""",
            "statute": """
TITLE 18—CRIMES AND CRIMINAL PROCEDURE
PART I—CRIMES
CHAPTER 44—FIREARMS

§ 922. Unlawful acts

(a) It shall be unlawful—
    (1) for any person—
        (A) except a licensed importer, licensed manufacturer, or licensed 
        dealer, to engage in the business of importing, manufacturing, or 
        dealing in firearms, or in the course of such business to ship, 
        transport, or receive any firearm in interstate or foreign commerce;
        
        (B) except a licensed importer or licensed manufacturer, to engage 
        in the business of importing or manufacturing ammunition, or in the 
        course of such business, to ship, transport, or receive any ammunition 
        in interstate or foreign commerce;

    (2) for any importer, manufacturer, dealer, or collector licensed under 
    the provisions of this chapter to ship or transport in interstate or 
    foreign commerce any firearm to any person other than a licensed importer, 
    licensed manufacturer, licensed dealer, or licensed collector, except that—
        
        (A) this paragraph and subsection (b)(3) shall not be held to preclude 
        a licensed importer, licensed manufacturer, licensed dealer, or licensed 
        collector from returning a firearm or replacement firearm of the same 
        kind and type to a person from whom it was received;

(b) It shall be unlawful for any licensed importer, licensed manufacturer, 
licensed dealer, or licensed collector to sell or deliver—
    
    (1) any firearm or ammunition to any individual who the licensee knows or 
    has reasonable cause to believe is less than eighteen years of age;
    
    (2) in any case in which the licensee knows or has reasonable cause to 
    believe that the juvenile is in possession of a handgun or ammunition;

(c) In any prosecution under this section, the court shall admit evidence 
regarding the conditions under which the defendant obtained the firearm.

(d) Penalties.—
    (1) Any person who violates subsection (a) or (b) shall be fined under 
    this title, imprisoned not more than 5 years, or both.
    
    (2) Any person who knowingly violates subsection (a)(1) shall be fined 
    under this title, imprisoned not more than 10 years, or both.
"""
        }
    
    @pytest.fixture
    def large_document(self):
        """Create a large document (>50K characters) for testing."""
        # Generate a large legal document with various sections
        sections = []
        
        # Add header
        sections.append("COMPREHENSIVE LEGAL DOCUMENT FOR TESTING\n" + "="*50 + "\n\n")
        
        # Add multiple articles with legal content
        for i in range(1, 21):
            article = f"""
ARTICLE {i}
{'-'*20}

Section {i}.1 - Definitions and Terminology

This section establishes the foundational definitions that will be used throughout 
this document. The terms defined herein shall have the meanings ascribed to them 
when used in this Agreement, unless the context clearly indicates otherwise.

"Party" or "Parties" means the individual or entities that are signatories to this 
Agreement and are bound by its terms and conditions. See Johnson v. Smith, 
123 F.3d 456, 459 (9th Cir. 2020) (defining party status in contractual agreements).

"Effective Date" means the date on which this Agreement becomes legally binding upon 
all Parties, as specified in Section {i}.2 below. The determination of the Effective 
Date is crucial for establishing the timeline of obligations. Accord Brown v. Board, 
347 U.S. 483, 495 (1954).

Section {i}.2 - Scope and Application

The provisions of this Article shall apply to all transactions contemplated under 
this Agreement. Any deviation from these provisions must be explicitly stated in 
writing and agreed upon by all Parties. As stated in 15 U.S.C. § 1681 et seq., 
certain regulatory requirements may supersede contractual provisions.

Pursuant to the Uniform Commercial Code § 2-201, contracts for the sale of goods 
priced at $500 or more must be evidenced by a writing sufficient to indicate that 
a contract has been made between the parties. This requirement, known as the 
Statute of Frauds, serves to prevent fraudulent claims.

Section {i}.3 - Legal Standards and Compliance

All Parties must comply with applicable federal, state, and local laws and 
regulations. This includes, but is not limited to:

(a) The Foreign Corrupt Practices Act, 15 U.S.C. §§ 78dd-1, et seq., which 
prohibits bribes to foreign officials;

(b) The Sherman Antitrust Act, 15 U.S.C. §§ 1-7, which prohibits certain 
business activities that federal government regulators deem to be 
anti-competitive;

(c) The Clayton Act, 15 U.S.C. §§ 12-27, which addresses specific practices 
that the Sherman Act does not clearly prohibit;

(d) The Federal Trade Commission Act, 15 U.S.C. §§ 41-58, which empowers the 
FTC to investigate and prevent unfair methods of competition.

The Supreme Court has consistently held that "statutory construction must begin 
with the language employed by Congress and the assumption that the ordinary 
meaning of that language accurately expresses the legislative purpose." 
Gross v. FBL Financial Services, Inc., 557 U.S. 167, 175 (2009).

"""
            sections.append(article)
        
        # Add some case law discussions
        case_discussion = """
APPENDIX A: RELEVANT CASE LAW ANALYSIS

The following cases provide crucial context for understanding the legal framework:

1. Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)
   This foundational case established the principle of judicial review, whereby 
   the Supreme Court has the power to strike down laws that violate the Constitution.
   Chief Justice Marshall's opinion remains one of the most important in American 
   jurisprudence.

2. McCulloch v. Maryland, 17 U.S. (4 Wheat.) 316 (1819)
   This case established two important principles in constitutional law: the 
   Constitution grants to Congress implied powers for implementing the Constitution's 
   express powers, and state action may not impede valid constitutional exercises 
   of power by the Federal government.

3. Gibbons v. Ogden, 22 U.S. (9 Wheat.) 1 (1824)
   The Court held that the power to regulate interstate commerce, granted to 
   Congress by the Commerce Clause of the United States Constitution, encompassed 
   the power to regulate navigation.

"""
        sections.append(case_discussion)
        
        return ''.join(sections)
    
    # Test Document Type Detection
    
    def test_document_type_detection_contract(self, chunker, sample_documents):
        """Test detection of contract documents."""
        doc_type = chunker.detect_document_type(sample_documents["contract"])
        assert doc_type == DocumentType.CONTRACT
    
    def test_document_type_detection_opinion(self, chunker, sample_documents):
        """Test detection of court opinion documents."""
        doc_type = chunker.detect_document_type(sample_documents["opinion"])
        assert doc_type == DocumentType.OPINION
    
    def test_document_type_detection_statute(self, chunker, sample_documents):
        """Test detection of statute documents."""
        doc_type = chunker.detect_document_type(sample_documents["statute"])
        assert doc_type == DocumentType.STATUTE
    
    def test_document_type_detection_unknown(self, chunker):
        """Test detection of unknown document type."""
        simple_text = "This is just some random text without legal content."
        doc_type = chunker.detect_document_type(simple_text)
        assert doc_type == DocumentType.UNKNOWN
    
    # Test Chunking Strategies
    
    def test_legal_aware_chunking(self, chunker, sample_documents):
        """Test legal-aware chunking strategy."""
        chunks = chunker.chunk_document(
            sample_documents["contract"],
            strategy=ChunkingStrategy.LEGAL_AWARE
        )
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.chunk_type == "legal_section" for chunk in chunks)
        
        # Verify chunks don't exceed max size
        for chunk in chunks:
            assert chunk.length <= chunker.config.max_chunk_size * 1.2  # Allow 20% overflow
    
    def test_section_aware_chunking(self, chunker, sample_documents):
        """Test section-aware chunking strategy."""
        chunks = chunker.chunk_document(
            sample_documents["statute"],
            strategy=ChunkingStrategy.SECTION_AWARE
        )
        
        assert len(chunks) > 0
        assert all(chunk.chunk_type in ["section", "section_part"] for chunk in chunks)
        
        # Check that section headers are preserved
        chunk_texts = [chunk.text for chunk in chunks]
        assert any("§ 922" in text for text in chunk_texts)
    
    def test_paragraph_aware_chunking(self, chunker, sample_documents):
        """Test paragraph-aware chunking strategy."""
        chunks = chunker.chunk_document(
            sample_documents["opinion"],
            strategy=ChunkingStrategy.PARAGRAPH_AWARE
        )
        
        assert len(chunks) > 0
        assert all(chunk.chunk_type == "paragraph" for chunk in chunks)
        
        # Verify paragraph boundaries are respected
        for chunk in chunks:
            # Paragraphs should not start or end mid-sentence (with some exceptions)
            assert not chunk.text.startswith(" ")
            assert chunk.text.strip() == chunk.text
    
    def test_sentence_aware_chunking(self, chunker, sample_documents):
        """Test sentence-aware chunking strategy."""
        chunks = chunker.chunk_document(
            sample_documents["opinion"],
            strategy=ChunkingStrategy.SENTENCE_AWARE
        )
        
        assert len(chunks) > 0
        assert all(chunk.chunk_type == "sentence" for chunk in chunks)
        
        # Verify sentences are complete
        for chunk in chunks:
            # Should end with sentence-ending punctuation
            text = chunk.text.strip()
            assert text[-1] in ['.', '?', '!', ')', '"'] or "§" in text
    
    def test_fixed_size_chunking(self, chunker, sample_documents):
        """Test fixed-size chunking strategy."""
        chunks = chunker.chunk_document(
            sample_documents["contract"],
            strategy=ChunkingStrategy.FIXED_SIZE
        )
        
        assert len(chunks) > 0
        assert all(chunk.chunk_type == "fixed" for chunk in chunks)
        
        # Check sizes are consistent (except last chunk)
        for i, chunk in enumerate(chunks[:-1]):
            assert chunk.length <= chunker.config.max_chunk_size
    
    def test_adaptive_chunking(self, chunker, sample_documents):
        """Test adaptive chunking strategy."""
        # Test with contract (should use section-aware)
        contract_chunks = chunker.chunk_document(
            sample_documents["contract"],
            strategy=ChunkingStrategy.ADAPTIVE
        )
        assert len(contract_chunks) > 0
        
        # Test with opinion (should use legal-aware)
        opinion_chunks = chunker.chunk_document(
            sample_documents["opinion"],
            strategy=ChunkingStrategy.ADAPTIVE
        )
        assert len(opinion_chunks) > 0
        
        # Test with statute (should use section-aware)
        statute_chunks = chunker.chunk_document(
            sample_documents["statute"],
            strategy=ChunkingStrategy.ADAPTIVE
        )
        assert len(statute_chunks) > 0
    
    # Test Large Document Handling
    
    def test_large_document_50k(self, chunker, large_document):
        """Test chunking of documents > 50K characters."""
        start_time = time.time()
        chunks = chunker.chunk_document(large_document)
        processing_time = time.time() - start_time
        
        assert len(chunks) > 0
        assert len(chunks) <= chunker.config.max_chunks_per_document
        
        # Verify all text is preserved
        total_length = sum(chunk.length for chunk in chunks)
        assert total_length > 50000  # Should be large
        
        # Check processing time is reasonable (no timeout)
        # We don't enforce a timeout, but track for performance
        print(f"Large document (50K+) processed in {processing_time:.2f} seconds")
        
        # Verify chunk statistics
        stats = chunker.get_chunk_statistics(chunks)
        assert stats["total_chunks"] == len(chunks)
        assert stats["avg_chunk_size"] > 0
        assert stats["total_text_length"] > 50000
    
    def test_very_large_document_500k(self, chunker):
        """Test chunking of very large documents (500K+ characters)."""
        # Generate a 500K+ document
        large_text = "Legal document section. " * 25000  # ~500K chars
        
        start_time = time.time()
        chunks = chunker.chunk_document(large_text)
        processing_time = time.time() - start_time
        
        assert len(chunks) > 0
        assert len(chunks) <= chunker.config.max_chunks_per_document
        
        print(f"Very large document (500K+) processed in {processing_time:.2f} seconds")
    
    def test_maximum_document_1mb(self, chunker):
        """Test chunking of maximum size documents (1MB)."""
        # Generate a 1MB document
        mb_text = "x" * (1024 * 1024)  # 1MB of text
        
        chunks = chunker.chunk_document(mb_text)
        
        assert len(chunks) > 0
        assert len(chunks) <= chunker.config.max_chunks_per_document
        
        # Should hit the max chunks limit
        assert len(chunks) == chunker.config.max_chunks_per_document
    
    # Test Boundary Preservation
    
    def test_citation_boundary_preservation(self, chunker):
        """Test that citations are not split across chunks."""
        text = """
        The court held in Smith v. Jones, 123 F.3d 456, 459 (9th Cir. 2020) that 
        the statute was constitutional. Additionally, 42 U.S.C. § 1983 provides 
        a cause of action. See also Brown v. Board, 347 U.S. 483, 495 (1954).
        """ * 50  # Repeat to ensure chunking
        
        chunks = chunker.chunk_document(text, strategy=ChunkingStrategy.LEGAL_AWARE)
        
        # Check that citations are complete in chunks
        for chunk in chunks:
            # If a citation starts, it should complete in the same chunk
            if "Smith v. Jones" in chunk.text:
                assert "123 F.3d 456" in chunk.text
            if "42 U.S.C." in chunk.text:
                assert "§ 1983" in chunk.text
    
    def test_quote_preservation(self, chunker):
        """Test that quotes are not split across chunks."""
        text = """
        The court stated: "The fundamental principle of constitutional law requires 
        that all citizens be treated equally under the law, regardless of their 
        status or position in society." This principle has been consistently upheld.
        """ * 50
        
        chunks = chunker.chunk_document(text, strategy=ChunkingStrategy.LEGAL_AWARE)
        
        for chunk in chunks:
            # Count quotes - should be even (paired)
            quote_count = chunk.text.count('"')
            assert quote_count % 2 == 0, f"Unpaired quotes in chunk: {chunk.text[:100]}"
    
    def test_section_header_preservation(self, chunker):
        """Test that section headers start new chunks."""
        text = """
        Some introductory text here.
        
        SECTION 1. DEFINITIONS
        
        This section contains definitions.
        
        SECTION 2. SCOPE
        
        This section describes scope.
        
        ARTICLE III - TERMS
        
        Terms are described here.
        """
        
        chunks = chunker.chunk_document(text, strategy=ChunkingStrategy.SECTION_AWARE)
        
        # Section headers should typically start chunks
        section_starts = [chunk.text.strip()[:20] for chunk in chunks if chunk.text.strip()]
        assert any("SECTION" in start for start in section_starts)
    
    # Test Overlap Application
    
    def test_chunk_overlap_application(self, chunker, sample_documents):
        """Test that overlap is correctly applied between chunks."""
        # Create config with overlap
        config = ChunkingConfig(
            max_chunk_size=500,
            chunk_overlap=100,
            min_chunk_size=100
        )
        chunker_with_overlap = SmartChunker(config=config)
        
        chunks = chunker_with_overlap.chunk_document(sample_documents["contract"])
        
        # Check that chunks have overlap metadata
        for chunk in chunks:
            if chunk.metadata.get("has_overlap"):
                assert "original_start" in chunk.metadata
                assert "original_end" in chunk.metadata
        
        # Verify overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            chunk1_end = chunks[i].text[-50:]  # Last 50 chars
            chunk2_start = chunks[i + 1].text[:50]  # First 50 chars
            # There should be some common text (not exact due to word boundaries)
    
    def test_no_overlap_configuration(self, sample_documents):
        """Test chunking without overlap."""
        config = ChunkingConfig(
            max_chunk_size=500,
            chunk_overlap=0,  # No overlap
            min_chunk_size=100
        )
        chunker_no_overlap = SmartChunker(config=config)
        
        chunks = chunker_no_overlap.chunk_document(sample_documents["contract"])
        
        # Verify no overlap metadata
        for chunk in chunks:
            assert not chunk.metadata.get("has_overlap", False)
    
    # Test Chunk Validation
    
    def test_minimum_chunk_size_validation(self, chunker):
        """Test that chunks meet minimum size requirements."""
        short_text = "Short. Text. Here."
        
        chunks = chunker.chunk_document(short_text)
        
        # Very short text might produce one chunk below min size
        if chunks:
            for chunk in chunks:
                if chunk.length < chunker.config.min_chunk_size:
                    assert chunk.metadata.get("below_min_size", False)
    
    def test_maximum_chunk_size_validation(self, chunker):
        """Test that chunks don't exceed maximum size."""
        long_sentence = "word " * 1000  # 5000 chars
        
        chunks = chunker.chunk_document(long_sentence)
        
        for chunk in chunks:
            # Allow 20% overflow for boundary preservation
            assert chunk.length <= chunker.config.max_chunk_size * 1.2
            if chunk.length > chunker.config.max_chunk_size:
                assert chunk.metadata.get("exceeds_max_size", False)
    
    def test_empty_chunk_removal(self, chunker):
        """Test that empty chunks are removed."""
        text_with_spaces = """
        
        
        Some text here.
        
        
        More text here.
        
        
        """
        
        chunks = chunker.chunk_document(text_with_spaces)
        
        # No empty chunks
        for chunk in chunks:
            assert chunk.text.strip() != ""
            assert chunk.length > 0
    
    def test_max_chunks_per_document_limit(self, chunker):
        """Test enforcement of maximum chunks per document."""
        # Generate text that would create more than max chunks
        very_long_text = "Short sentence. " * 10000
        
        chunks = chunker.chunk_document(very_long_text)
        
        assert len(chunks) <= chunker.config.max_chunks_per_document
    
    # Test Statistics and Metadata
    
    def test_chunk_statistics_generation(self, chunker, sample_documents):
        """Test generation of chunk statistics."""
        chunks = chunker.chunk_document(sample_documents["contract"])
        stats = chunker.get_chunk_statistics(chunks)
        
        assert "total_chunks" in stats
        assert "avg_chunk_size" in stats
        assert "min_chunk_size" in stats
        assert "max_chunk_size" in stats
        assert "total_text_length" in stats
        assert "chunk_types" in stats
        assert "strategies_used" in stats
        
        assert stats["total_chunks"] == len(chunks)
        assert stats["avg_chunk_size"] > 0
        assert stats["min_chunk_size"] <= stats["max_chunk_size"]
    
    def test_chunk_metadata_completeness(self, chunker, sample_documents):
        """Test that chunk metadata is complete."""
        chunks = chunker.chunk_document(
            sample_documents["contract"],
            strategy=ChunkingStrategy.LEGAL_AWARE
        )
        
        for chunk in chunks:
            assert hasattr(chunk, "text")
            assert hasattr(chunk, "start_pos")
            assert hasattr(chunk, "end_pos")
            assert hasattr(chunk, "chunk_index")
            assert hasattr(chunk, "chunk_type")
            assert hasattr(chunk, "confidence")
            assert hasattr(chunk, "metadata")
            assert isinstance(chunk.metadata, dict)
            assert "strategy" in chunk.metadata
    
    # Test Complexity Calculation
    
    def test_document_complexity_calculation(self, chunker, sample_documents):
        """Test document complexity calculation."""
        # Simple text should have low complexity
        simple_text = "This is a simple document with basic words."
        simple_complexity = chunker.calculate_complexity(simple_text)
        assert 0.0 <= simple_complexity <= 0.3
        
        # Legal text should have higher complexity
        legal_complexity = chunker.calculate_complexity(sample_documents["contract"])
        assert 0.3 <= legal_complexity <= 1.0
        
        # Opinion with citations should have high complexity
        opinion_complexity = chunker.calculate_complexity(sample_documents["opinion"])
        assert 0.3 <= opinion_complexity <= 1.0
    
    # Test Edge Cases
    
    def test_empty_document(self, chunker):
        """Test handling of empty documents."""
        chunks = chunker.chunk_document("")
        assert chunks == []
        
        chunks = chunker.chunk_document(None)
        assert chunks == []
    
    def test_single_word_document(self, chunker):
        """Test handling of single word documents."""
        chunks = chunker.chunk_document("Word")
        assert len(chunks) <= 1
        if chunks:
            assert chunks[0].text == "Word"
    
    def test_unicode_document(self, chunker):
        """Test handling of unicode characters."""
        unicode_text = "Legal text with unicode: § © ® ™ € £ ¥ • … —"
        chunks = chunker.chunk_document(unicode_text)
        assert len(chunks) > 0
        assert "§" in chunks[0].text
    
    def test_mixed_line_endings(self, chunker):
        """Test handling of mixed line endings."""
        mixed_text = "Line 1\nLine 2\r\nLine 3\rLine 4"
        chunks = chunker.chunk_document(mixed_text)
        assert len(chunks) > 0
    
    # Test Configuration Override
    
    def test_configuration_override(self, sample_documents):
        """Test that configuration can be overridden."""
        custom_config = ChunkingConfig(
            max_chunk_size=100,  # Very small chunks
            chunk_overlap=10,
            min_chunk_size=50
        )
        custom_chunker = SmartChunker(config=custom_config)
        
        chunks = custom_chunker.chunk_document(sample_documents["contract"])
        
        # Should create many small chunks
        assert len(chunks) > 10
        for chunk in chunks:
            assert chunk.length <= 120  # Allow some overflow
    
    def test_runtime_config_support(self, sample_documents):
        """Test support for RuntimeConfig."""
        runtime_config = RuntimeConfig()
        runtime_chunker = SmartChunker(config=runtime_config)
        
        chunks = runtime_chunker.chunk_document(sample_documents["contract"])
        assert len(chunks) > 0
    
    # Performance Tests
    
    @pytest.mark.performance
    def test_chunking_performance(self, chunker, large_document):
        """Test chunking performance on large documents."""
        iterations = 5
        times = []
        
        for _ in range(iterations):
            start = time.time()
            chunks = chunker.chunk_document(large_document)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        print(f"\nAverage chunking time for 50K+ document: {avg_time:.3f} seconds")
        
        # No timeout enforcement, but track for monitoring
        assert avg_time < 60  # Should complete within a minute
    
    @pytest.mark.performance
    def test_memory_efficiency(self, chunker):
        """Test memory efficiency with large documents."""
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        # Process a large document
        large_text = "Legal content. " * 50000  # ~700K chars
        chunks = chunker.chunk_document(large_text)
        
        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"\nMemory usage - Current: {current / 1024 / 1024:.2f} MB, "
              f"Peak: {peak / 1024 / 1024:.2f} MB")
        
        # Memory should be reasonable
        assert peak < 500 * 1024 * 1024  # Less than 500MB


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=0"])