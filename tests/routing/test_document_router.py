"""
Unit tests for DocumentRouter

Tests intelligent routing logic for all document sizes and edge cases.
"""

import pytest
from src.routing.document_router import (
    DocumentRouter,
    RoutingDecision,
    ProcessingStrategy,
    ChunkConfig
)
from src.routing.size_detector import SizeCategory


class TestDocumentRouter:
    """Test suite for DocumentRouter"""

    @pytest.fixture
    def router(self):
        """Create DocumentRouter instance"""
        return DocumentRouter()

    def test_route_very_small_document(self, router):
        """Test routing for very small documents"""
        text = "This is a very small document. " * 50  # ~1,600 chars

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.SINGLE_PASS
        assert decision.prompt_version == "single_pass_consolidated_v1"
        assert decision.chunk_config is None
        assert decision.num_chunks == 0
        assert decision.expected_accuracy == 0.87
        assert decision.estimated_duration == 0.5
        assert decision.size_info.category == SizeCategory.VERY_SMALL

    def test_route_small_document(self, router):
        """Test routing for small documents"""
        text = "This is a small legal document. " * 500  # ~16,000 chars

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.THREE_WAVE
        assert decision.prompt_version == "three_wave_optimized_v1"
        assert decision.chunk_config is None
        assert decision.num_chunks == 0
        assert decision.expected_accuracy == 0.90
        assert decision.estimated_duration == 1.0
        assert decision.size_info.category == SizeCategory.SMALL

    def test_route_medium_document(self, router):
        """Test routing for medium documents"""
        text = "This is a medium legal document. " * 3000  # ~99,000 chars

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.THREE_WAVE_CHUNKED
        assert decision.prompt_version == "three_wave_optimized_v1"
        assert decision.chunk_config is not None
        assert decision.chunk_config.strategy == "extraction"
        assert decision.chunk_config.chunk_size == 8000
        assert decision.chunk_config.overlap_size == 500
        assert decision.chunk_config.preserve_boundaries == "paragraph"
        assert decision.num_chunks > 0
        assert decision.expected_accuracy == 0.91
        assert decision.size_info.category == SizeCategory.MEDIUM

    def test_route_large_document(self, router):
        """Test routing for large documents"""
        text = "This is a large legal document. " * 6000  # ~198,000 chars

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.THREE_WAVE_CHUNKED
        assert decision.prompt_version == "three_wave_optimized_v1"
        assert decision.chunk_config is not None
        assert decision.chunk_config.overlap_size == 1000  # Larger overlap for large docs
        assert decision.chunk_config.preserve_boundaries == "section"
        assert decision.num_chunks > 0
        assert decision.expected_accuracy == 0.92
        assert decision.size_info.category == SizeCategory.LARGE

    def test_empty_document_edge_case(self, router):
        """Test handling of empty documents"""
        text = ""

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.EMPTY_DOCUMENT
        assert decision.prompt_version is None
        assert decision.estimated_tokens == 0
        assert decision.expected_accuracy == 0.0
        assert "Empty document" in decision.rationale

    def test_too_small_document_edge_case(self, router):
        """Test handling of very small fragments"""
        text = "Hello"  # Only 5 chars

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.TOO_SMALL
        assert decision.prompt_version is None
        assert decision.expected_accuracy == 0.0
        assert "too small" in decision.rationale.lower()

    def test_binary_document_edge_case(self, router):
        """Test handling of binary/malformed documents"""
        # Create text with many non-printable characters
        text = "Hello\x00\x01\x02\x03\x04\x05" * 100

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.INVALID_DOCUMENT
        assert "binary" in decision.rationale.lower() or "malformed" in decision.rationale.lower()

    def test_extremely_large_document_warning(self, router, caplog):
        """Test warning for extremely large documents (>1M chars)"""
        text = "a" * 1_500_000  # 1.5M characters

        decision = router.route(text)

        # Should still route (to LARGE strategy)
        assert decision.strategy == ProcessingStrategy.THREE_WAVE_CHUNKED
        # Should log warning
        assert any("Extremely large document" in record.message for record in caplog.records)

    def test_none_document_raises_error(self, router):
        """Test that None document raises ValueError"""
        with pytest.raises(ValueError, match="document_text cannot be None"):
            router.route(None)

    def test_strategy_override_single_pass(self, router):
        """Test manual strategy override to single_pass"""
        text = "a" * 50000  # Would normally be SMALL (3-wave)

        decision = router.route(text, strategy_override="single_pass")

        assert decision.strategy == ProcessingStrategy.SINGLE_PASS
        assert "override" in decision.rationale.lower() or decision.prompt_version == "single_pass_consolidated_v1"

    def test_strategy_override_three_wave_chunked(self, router):
        """Test manual strategy override to three_wave_chunked"""
        text = "a" * 3000  # Very small, would normally be single_pass

        decision = router.route(text, strategy_override="three_wave_chunked")

        # Should apply override
        assert decision.strategy in [ProcessingStrategy.THREE_WAVE, ProcessingStrategy.THREE_WAVE_CHUNKED]

    def test_strategy_override_eight_wave(self, router):
        """Test manual strategy override to eight_wave_fallback"""
        text = "a" * 10000

        decision = router.route(text, strategy_override="eight_wave_fallback")

        assert decision.strategy == ProcessingStrategy.EIGHT_WAVE_FALLBACK
        assert decision.prompt_version == "eight_wave_multipass_v2"
        assert decision.expected_accuracy == 0.93

    def test_invalid_strategy_override(self, router):
        """Test invalid strategy override falls back to normal routing"""
        text = "a" * 10000

        decision = router.route(text, strategy_override="invalid_strategy")

        # Should ignore invalid override and use normal routing
        assert decision.strategy in [ProcessingStrategy.SINGLE_PASS, ProcessingStrategy.THREE_WAVE]

    def test_config_force_strategy(self):
        """Test configuration-based forced strategy"""
        config = {"force_strategy": "single_pass"}
        router = DocumentRouter(config=config)

        text = "a" * 50000  # Would normally be SMALL (3-wave)

        decision = router.route(text)

        assert decision.strategy == ProcessingStrategy.SINGLE_PASS

    def test_config_custom_thresholds(self):
        """Test custom configuration thresholds"""
        config = {
            "max_context_length": 16384,  # Half the default
            "safety_margin": 1000
        }
        router = DocumentRouter(config=config)

        assert router.max_context == 16384
        assert router.safety_margin == 1000

    def test_token_budget_estimation(self, router):
        """Test token budget estimation accuracy"""
        text = "a" * 10000  # 10K chars = ~2500 tokens

        decision = router.route(text)

        # Should estimate tokens for prompt + document + response
        assert decision.estimated_tokens > 0
        assert decision.estimated_tokens < 100000  # Reasonable upper bound

    def test_chunk_calculation(self, router):
        """Test chunk number calculation"""
        # Create document that requires multiple chunks
        text = "a" * 200000  # 200K chars = ~50K tokens

        decision = router.route(text)

        # Should calculate multiple chunks
        assert decision.num_chunks > 1
        # With 8K chunk size and overlap, should be ~6-7 chunks
        assert 5 <= decision.num_chunks <= 10

    def test_cost_estimation_accuracy(self, router):
        """Test cost estimation for different document sizes"""
        # Very small
        text_very_small = "a" * 2000
        decision = router.route(text_very_small)
        assert 0.003 <= decision.estimated_cost <= 0.005

        # Small
        text_small = "a" * 20000
        decision = router.route(text_small)
        assert 0.010 <= decision.estimated_cost <= 0.025

        # Medium (multiple chunks)
        text_medium = "a" * 100000
        decision = router.route(text_medium)
        assert decision.estimated_cost > 0.02

    def test_duration_estimation(self, router):
        """Test processing duration estimation"""
        # Very small: ~0.5s
        text_very_small = "a" * 2000
        decision = router.route(text_very_small)
        assert decision.estimated_duration == 0.5

        # Small: ~1.0s
        text_small = "a" * 20000
        decision = router.route(text_small)
        assert decision.estimated_duration == 1.0

        # Large: >4s
        text_large = "a" * 200000
        decision = router.route(text_large)
        assert decision.estimated_duration > 4.0

    def test_accuracy_expectations(self, router):
        """Test accuracy expectations for different strategies"""
        # Very small: 87%
        text_very_small = "a" * 2000
        decision = router.route(text_very_small)
        assert decision.expected_accuracy == 0.87

        # Small: 90%
        text_small = "a" * 20000
        decision = router.route(text_small)
        assert decision.expected_accuracy == 0.90

        # Medium: 91%
        text_medium = "a" * 100000
        decision = router.route(text_medium)
        assert decision.expected_accuracy == 0.91

        # Large: 92%
        text_large = "a" * 200000
        decision = router.route(text_large)
        assert decision.expected_accuracy == 0.92

    def test_metadata_usage(self, router):
        """Test that metadata is passed to size detector"""
        text = "a" * 10000
        metadata = {"pages": 10, "document_type": "complaint"}

        decision = router.route(text, metadata=metadata)

        assert decision.size_info.pages == 10

    def test_decision_validation_valid(self, router):
        """Test validation of valid routing decision"""
        text = "a" * 10000
        decision = router.route(text)

        is_valid, warnings = router.validate_decision(decision)

        assert is_valid
        assert len(warnings) == 0

    def test_decision_validation_exceeds_context(self, router):
        """Test validation warns when exceeding context limit"""
        # Create unrealistic decision that exceeds context
        text = "a" * 10000
        decision = router.route(text)
        decision.estimated_tokens = 40000  # Exceeds 32K limit

        is_valid, warnings = router.validate_decision(decision)

        assert not is_valid
        assert any("context limit" in w.lower() for w in warnings)

    def test_decision_validation_high_cost(self, router):
        """Test validation warns for unreasonably high cost"""
        text = "a" * 10000
        decision = router.route(text)
        decision.estimated_cost = 2.0  # $2 per document

        is_valid, warnings = router.validate_decision(decision)

        assert any("cost" in w.lower() for w in warnings)

    def test_decision_validation_long_duration(self, router):
        """Test validation warns for unreasonably long duration"""
        text = "a" * 10000
        decision = router.route(text)
        decision.estimated_duration = 120.0  # 2 minutes

        is_valid, warnings = router.validate_decision(decision)

        assert any("duration" in w.lower() for w in warnings)

    def test_routing_decision_to_dict(self, router):
        """Test RoutingDecision serialization to dict"""
        text = "a" * 10000
        decision = router.route(text)

        result = decision.to_dict()

        assert isinstance(result, dict)
        assert "strategy" in result
        assert "prompt_version" in result
        assert "chunk_config" in result
        assert "estimated_tokens" in result
        assert "estimated_duration" in result
        assert "estimated_cost" in result
        assert "expected_accuracy" in result
        assert "size_info" in result
        assert "rationale" in result
        assert "num_chunks" in result

    def test_routing_decision_repr(self, router):
        """Test RoutingDecision string representation"""
        text = "a" * 10000
        decision = router.route(text)

        repr_str = repr(decision)

        assert "RoutingDecision" in repr_str
        assert "strategy=" in repr_str
        assert "tokens=" in repr_str

    def test_chunk_config_to_dict(self, router):
        """Test ChunkConfig serialization"""
        text = "a" * 100000  # Medium document
        decision = router.route(text)

        chunk_dict = decision.chunk_config.to_dict()

        assert isinstance(chunk_dict, dict)
        assert "strategy" in chunk_dict
        assert "chunk_size" in chunk_dict
        assert "overlap_size" in chunk_dict
        assert "preserve_boundaries" in chunk_dict

    def test_realistic_legal_document_routing(self, router):
        """Test routing with realistic legal document"""
        # Simulate a 20-page complaint
        legal_text = """
        IN THE UNITED STATES DISTRICT COURT
        FOR THE DISTRICT OF COLUMBIA

        JOHN DOE,
            Plaintiff,
        v.                                      Case No. 1:25-cv-12345

        ACME CORPORATION,
            Defendant.

        COMPLAINT FOR DAMAGES

        1. INTRODUCTION

            Plaintiff John Doe brings this action against Defendant ACME Corporation
        for violations of federal employment discrimination laws. This complaint
        seeks compensatory and punitive damages, injunctive relief, and attorney's fees.

        2. JURISDICTION AND VENUE

            This Court has jurisdiction over this action pursuant to 42 U.S.C. § 2000e-5(f)(3)
        and 28 U.S.C. § 1331. Venue is proper in this District under 28 U.S.C. § 1391(b).

        3. PARTIES

            Plaintiff John Doe is an individual residing in Washington, DC.

            Defendant ACME Corporation is a Delaware corporation with its principal
        place of business in Washington, DC.

        4. FACTUAL ALLEGATIONS

            [Detailed factual allegations would continue...]

        """ * 100  # Repeat to simulate full complaint

        decision = router.route(legal_text, metadata={"pages": 20, "document_type": "complaint"})

        # Should route to appropriate strategy
        assert decision.strategy in [ProcessingStrategy.THREE_WAVE, ProcessingStrategy.THREE_WAVE_CHUNKED]
        assert decision.size_info.pages == 20
        assert decision.estimated_tokens > 0


class TestProcessingStrategy:
    """Test ProcessingStrategy enum"""

    def test_enum_values(self):
        """Test that all strategies have correct string values"""
        assert ProcessingStrategy.SINGLE_PASS.value == "single_pass"
        assert ProcessingStrategy.THREE_WAVE.value == "three_wave"
        assert ProcessingStrategy.THREE_WAVE_CHUNKED.value == "three_wave_chunked"
        assert ProcessingStrategy.ADAPTIVE.value == "adaptive"
        assert ProcessingStrategy.EIGHT_WAVE_FALLBACK.value == "eight_wave_fallback"
        assert ProcessingStrategy.EMPTY_DOCUMENT.value == "empty_document"
        assert ProcessingStrategy.TOO_SMALL.value == "too_small"
        assert ProcessingStrategy.INVALID_DOCUMENT.value == "invalid_document"


class TestIntegration:
    """Integration tests for routing system"""

    @pytest.fixture
    def router(self):
        """Create DocumentRouter instance"""
        return DocumentRouter()

    def test_end_to_end_very_small(self, router):
        """Test complete routing for very small document"""
        text = "Motion to Dismiss filed by Defendant. " * 100  # Make it >50 chars to avoid TOO_SMALL

        decision = router.route(text)
        is_valid, warnings = router.validate_decision(decision)

        assert is_valid
        assert decision.strategy == ProcessingStrategy.SINGLE_PASS
        assert decision.estimated_tokens < 10000

    def test_end_to_end_small(self, router):
        """Test complete routing for small document"""
        text = "Legal brief content. " * 1000

        decision = router.route(text)
        is_valid, warnings = router.validate_decision(decision)

        assert is_valid
        assert decision.strategy == ProcessingStrategy.THREE_WAVE
        assert 10000 < decision.estimated_tokens < 35000

    def test_end_to_end_with_override(self, router):
        """Test complete routing with manual override"""
        text = "Legal brief content. " * 1000

        decision = router.route(text, strategy_override="eight_wave_fallback")
        is_valid, warnings = router.validate_decision(decision)

        assert decision.strategy == ProcessingStrategy.EIGHT_WAVE_FALLBACK
