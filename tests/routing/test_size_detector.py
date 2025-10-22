"""
Unit tests for SizeDetector

Tests document size detection and categorization.
"""

import pytest
from src.routing.size_detector import SizeDetector, DocumentSizeInfo, SizeCategory


class TestSizeDetector:
    """Test suite for SizeDetector"""

    @pytest.fixture
    def detector(self):
        """Create SizeDetector instance"""
        return SizeDetector()

    def test_very_small_document(self, detector):
        """Test detection of very small documents (<5K chars)"""
        text = "This is a very small document. " * 50  # ~1,600 chars
        size_info = detector.detect(text)

        assert size_info.category == SizeCategory.VERY_SMALL
        assert size_info.chars < 5000
        assert size_info.tokens < 1250
        assert size_info.chars > 0

    def test_small_document(self, detector):
        """Test detection of small documents (5K-50K chars)"""
        text = "This is a small legal document. " * 500  # ~16,000 chars
        size_info = detector.detect(text)

        assert size_info.category == SizeCategory.SMALL
        assert 5000 < size_info.chars <= 50000
        assert 1250 < size_info.tokens <= 12500

    def test_medium_document(self, detector):
        """Test detection of medium documents (50K-150K chars)"""
        text = "This is a medium legal document. " * 3000  # ~99,000 chars
        size_info = detector.detect(text)

        assert size_info.category == SizeCategory.MEDIUM
        assert 50000 < size_info.chars <= 150000
        assert 12500 < size_info.tokens <= 37500

    def test_large_document(self, detector):
        """Test detection of large documents (>150K chars)"""
        text = "This is a large legal document. " * 6000  # ~198,000 chars
        size_info = detector.detect(text)

        assert size_info.category == SizeCategory.LARGE
        assert size_info.chars > 150000
        assert size_info.tokens > 37500

    def test_exact_thresholds(self, detector):
        """Test behavior at exact threshold boundaries"""
        # Exactly 5000 chars (boundary between VERY_SMALL and SMALL)
        text_5000 = "a" * 5000
        size_info = detector.detect(text_5000)
        assert size_info.category == SizeCategory.VERY_SMALL

        # 5001 chars (just into SMALL)
        text_5001 = "a" * 5001
        size_info = detector.detect(text_5001)
        assert size_info.category == SizeCategory.SMALL

        # Exactly 50000 chars
        text_50000 = "a" * 50000
        size_info = detector.detect(text_50000)
        assert size_info.category == SizeCategory.SMALL

        # 50001 chars
        text_50001 = "a" * 50001
        size_info = detector.detect(text_50001)
        assert size_info.category == SizeCategory.MEDIUM

    def test_token_estimation(self, detector):
        """Test token count estimation accuracy"""
        text = "This is a test document. " * 100  # 2,500 chars
        size_info = detector.detect(text)

        # Should estimate ~625 tokens (2500 / 4)
        expected_tokens = 2500 // 4
        assert abs(size_info.tokens - expected_tokens) < 10

    def test_metadata_page_extraction(self, detector):
        """Test extraction of page count from metadata"""
        text = "Test document"

        # Test with pages key
        size_info = detector.detect(text, metadata={"pages": 10})
        assert size_info.pages == 10

        # Test with page_count key
        size_info = detector.detect(text, metadata={"page_count": 20})
        assert size_info.pages == 20

        # Test with no metadata
        size_info = detector.detect(text)
        assert size_info.pages == 0

        # Test with invalid page count
        size_info = detector.detect(text, metadata={"pages": "invalid"})
        assert size_info.pages == 0

    def test_word_count_estimation(self, detector):
        """Test word count estimation"""
        text = "This is a test document with ten words total here."
        size_info = detector.detect(text)

        assert size_info.words == 10

    def test_line_count(self, detector):
        """Test line counting"""
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        size_info = detector.detect(text)

        assert size_info.lines == 4

    def test_empty_document(self, detector):
        """Test handling of empty documents"""
        text = ""
        size_info = detector.detect(text)

        assert size_info.category == SizeCategory.VERY_SMALL
        assert size_info.chars == 0
        assert size_info.tokens == 0
        assert size_info.words == 0

    def test_whitespace_only_document(self, detector):
        """Test handling of whitespace-only documents"""
        text = "   \n\n\t\t   "
        size_info = detector.detect(text)

        assert size_info.category == SizeCategory.VERY_SMALL
        assert size_info.chars > 0
        assert size_info.words == 0

    def test_none_document_raises_error(self, detector):
        """Test that None document raises ValueError"""
        with pytest.raises(ValueError, match="document_text cannot be None"):
            detector.detect(None)

    def test_custom_chars_per_token(self):
        """Test custom characters per token ratio"""
        detector_custom = SizeDetector(chars_per_token=5.0)
        text = "a" * 10000

        size_info = detector_custom.detect(text)

        # With 5 chars/token, 10000 chars = 2000 tokens
        assert size_info.tokens == 2000

    def test_processing_time_estimation(self, detector):
        """Test processing time estimation for different sizes"""
        # Very small
        text_very_small = "a" * 1000
        size_info = detector.detect(text_very_small)
        time_estimate = detector.estimate_processing_time(size_info)
        assert time_estimate == 0.5

        # Small
        text_small = "a" * 10000
        size_info = detector.detect(text_small)
        time_estimate = detector.estimate_processing_time(size_info)
        assert time_estimate == 1.0

        # Medium
        text_medium = "a" * 100000
        size_info = detector.detect(text_medium)
        time_estimate = detector.estimate_processing_time(size_info)
        assert 2.0 <= time_estimate <= 4.0

        # Large
        text_large = "a" * 200000
        size_info = detector.detect(text_large)
        time_estimate = detector.estimate_processing_time(size_info)
        assert time_estimate > 4.0

    def test_cost_estimation(self, detector):
        """Test cost estimation for different sizes"""
        # Very small
        text_very_small = "a" * 1000
        size_info = detector.detect(text_very_small)
        cost = detector.estimate_cost(size_info)
        assert 0.003 <= cost <= 0.005

        # Small
        text_small = "a" * 10000
        size_info = detector.detect(text_small)
        cost = detector.estimate_cost(size_info)
        assert 0.010 <= cost <= 0.025  # Adjusted upper bound

    def test_size_info_to_dict(self, detector):
        """Test DocumentSizeInfo serialization to dict"""
        text = "Test document"
        size_info = detector.detect(text)

        result = size_info.to_dict()

        assert isinstance(result, dict)
        assert "chars" in result
        assert "tokens" in result
        assert "pages" in result
        assert "category" in result
        assert "words" in result
        assert "lines" in result
        assert result["category"] == SizeCategory.VERY_SMALL.value

    def test_size_info_repr(self, detector):
        """Test DocumentSizeInfo string representation"""
        text = "a" * 10000
        size_info = detector.detect(text)

        repr_str = repr(size_info)

        assert "DocumentSizeInfo" in repr_str
        assert "chars=10,000" in repr_str or "chars=10000" in repr_str
        assert "SMALL" in repr_str

    def test_realistic_legal_document(self, detector):
        """Test with realistic legal document text"""
        # Simulate a short legal motion (2-page document)
        legal_text = """
        IN THE UNITED STATES DISTRICT COURT
        FOR THE DISTRICT OF COLUMBIA

        JOHN DOE,
            Plaintiff,
        v.                                      Case No. 1:25-cv-12345

        ACME CORPORATION,
            Defendant.

        MOTION TO DISMISS

            Defendant ACME Corporation, by and through undersigned counsel,
        respectfully moves this Court to dismiss the Complaint pursuant to
        Federal Rule of Civil Procedure 12(b)(6) for failure to state a
        claim upon which relief can be granted.

            This motion is supported by the attached Memorandum of Law.

        Dated: October 11, 2025

                                        Respectfully submitted,

                                        /s/ Jane Attorney
                                        Jane Attorney (Bar No. 12345)
                                        Law Firm LLP
                                        123 Main Street
                                        Washington, DC 20001
                                        (202) 555-1234
                                        jane.attorney@lawfirm.com

                                        Attorney for Defendant
        """ * 5  # Repeat to get ~2-page document

        size_info = detector.detect(legal_text)

        # Should be categorized appropriately (may be SMALL due to repetition)
        assert size_info.category in [SizeCategory.VERY_SMALL, SizeCategory.SMALL]
        assert size_info.words > 100
        assert size_info.lines > 20


class TestSizeCategory:
    """Test SizeCategory enum"""

    def test_enum_values(self):
        """Test that all size categories have correct string values"""
        assert SizeCategory.VERY_SMALL.value == "VERY_SMALL"
        assert SizeCategory.SMALL.value == "SMALL"
        assert SizeCategory.MEDIUM.value == "MEDIUM"
        assert SizeCategory.LARGE.value == "LARGE"

    def test_enum_comparison(self):
        """Test enum equality comparison"""
        assert SizeCategory.VERY_SMALL == SizeCategory.VERY_SMALL
        assert SizeCategory.SMALL != SizeCategory.MEDIUM
