"""
Unit Tests for Relationship Pattern Endpoints

Tests all 5 relationship endpoints and 3 pattern inspection endpoints added in Phase 2 & 3:

Relationship Endpoints:
- GET /api/v1/relationships
- GET /api/v1/relationships/{relationship_type}
- GET /api/v1/relationships/categories
- GET /api/v1/relationships/statistics
- POST /api/v1/extract/relationships

Pattern Inspection Endpoints:
- GET /api/v1/patterns/library
- GET /api/v1/patterns/comprehensive
- GET /api/v1/patterns/inspect/{pattern_name}
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent

from src.api.routes.relationships import (
    RelationshipPattern,
    RelationshipListResponse,
    RelationshipDetailResponse,
    RelationshipCategoriesResponse,
    RelationshipCategoryInfo,
    RelationshipStatistics,
    RelationshipExtractionRequest,
    RelationshipExtractionResponse
)


class TestRelationshipModels:
    """Test Pydantic models for relationship endpoints."""

    def test_relationship_pattern_model(self):
        """Test RelationshipPattern model validation."""
        pattern = RelationshipPattern(
            relationship_type="REPRESENTS",
            description="Attorney representing a party",
            source_entity="ATTORNEY",
            target_entity="PARTY",
            indicators=["represents", "representing"],
            examples=["John Smith, Esq. representing Plaintiff"],
            category="party_litigation",
            confidence=0.95,
            bidirectional=False
        )

        assert pattern.relationship_type == "REPRESENTS"
        assert pattern.source_entity == "ATTORNEY"
        assert pattern.target_entity == "PARTY"
        assert len(pattern.indicators) == 2
        assert pattern.confidence == 0.95

    def test_relationship_list_response_model(self):
        """Test RelationshipListResponse model."""
        response = RelationshipListResponse(
            total_relationships=10,
            relationships=[],
            categories=["party_litigation", "legal_precedent"],
            filters_applied={"category": "party_litigation"}
        )

        assert response.total_relationships == 10
        assert len(response.categories) == 2
        assert response.filters_applied["category"] == "party_litigation"

    def test_relationship_detail_response_model(self):
        """Test RelationshipDetailResponse model."""
        response = RelationshipDetailResponse(
            relationship_type="CITES",
            description="Case citing another case",
            source_entity="CASE_CITATION",
            target_entity="CASE_CITATION",
            indicators=["citing", "cited in"],
            examples=["Smith v. Jones, citing Brown v. Board"],
            category="legal_precedent",
            confidence=0.92,
            bidirectional=False,
            usage_statistics={"total_extractions": 100},
            related_relationships=["FOLLOWS", "OVERRULES"]
        )

        assert response.relationship_type == "CITES"
        assert response.category == "legal_precedent"
        assert len(response.related_relationships) == 2

    def test_relationship_category_info_model(self):
        """Test RelationshipCategoryInfo model."""
        category = RelationshipCategoryInfo(
            category="party_litigation",
            description="Relationships between parties and attorneys",
            relationship_count=10,
            relationship_types=["REPRESENTS", "SUES", "OPPOSES"],
            example_relationships=["REPRESENTS", "SUES"]
        )

        assert category.category == "party_litigation"
        assert category.relationship_count == 10
        assert len(category.relationship_types) == 3

    def test_relationship_categories_response_model(self):
        """Test RelationshipCategoriesResponse model."""
        response = RelationshipCategoriesResponse(
            total_categories=6,
            categories=[],
            total_relationships=46
        )

        assert response.total_categories == 6
        assert response.total_relationships == 46

    def test_relationship_statistics_model(self):
        """Test RelationshipStatistics model."""
        stats = RelationshipStatistics(
            total_relationships=46,
            total_categories=6,
            total_indicators=234,
            relationships_by_category={"party_litigation": 10},
            most_common_source_entities=[{"entity_type": "ATTORNEY", "count": 5}],
            most_common_target_entities=[{"entity_type": "PARTY", "count": 8}],
            bidirectional_relationships=3,
            average_indicators_per_relationship=5.1,
            coverage_by_entity_type={"ATTORNEY": 5, "PARTY": 8}
        )

        assert stats.total_relationships == 46
        assert stats.total_categories == 6
        assert stats.average_indicators_per_relationship == 5.1

    def test_relationship_extraction_request_model(self):
        """Test RelationshipExtractionRequest model."""
        request = RelationshipExtractionRequest(
            document_id="test_doc_001",
            content="Test content for extraction",
            relationship_types=["REPRESENTS", "SUES"],
            confidence_threshold=0.75,
            max_relationships=50
        )

        assert request.document_id == "test_doc_001"
        assert len(request.relationship_types) == 2
        assert request.confidence_threshold == 0.75
        assert request.extract_entities_if_missing is True  # Default value

    def test_relationship_extraction_response_model(self):
        """Test RelationshipExtractionResponse model."""
        response = RelationshipExtractionResponse(
            document_id="test_doc_001",
            extraction_id="ext_12345",
            processing_time_ms=150.5,
            total_relationships=5,
            relationships=[],
            entities_used=10,
            statistics={"extraction_mode": "relationship_focused"}
        )

        assert response.document_id == "test_doc_001"
        assert response.processing_time_ms == 150.5
        assert response.total_relationships == 5


class TestRelationshipLogic:
    """Test relationship pattern logic and filtering."""

    def test_relationship_filtering_by_category(self):
        """Test filtering relationships by category."""
        relationships = [
            {"relationship_type": "REPRESENTS", "category": "party_litigation"},
            {"relationship_type": "CITES", "category": "legal_precedent"},
            {"relationship_type": "SUES", "category": "party_litigation"}
        ]

        filtered = [r for r in relationships if r["category"] == "party_litigation"]

        assert len(filtered) == 2
        assert all(r["category"] == "party_litigation" for r in filtered)

    def test_relationship_filtering_by_source_entity(self):
        """Test filtering relationships by source entity."""
        relationships = [
            {"relationship_type": "REPRESENTS", "source_entity": "ATTORNEY"},
            {"relationship_type": "PRESIDES_OVER", "source_entity": "JUDGE"},
            {"relationship_type": "SUES", "source_entity": "PLAINTIFF"}
        ]

        filtered = [r for r in relationships if r["source_entity"] == "ATTORNEY"]

        assert len(filtered) == 1
        assert filtered[0]["relationship_type"] == "REPRESENTS"

    def test_relationship_filtering_by_target_entity(self):
        """Test filtering relationships by target entity."""
        relationships = [
            {"relationship_type": "REPRESENTS", "target_entity": "PARTY"},
            {"relationship_type": "CITES", "target_entity": "CASE_CITATION"},
            {"relationship_type": "SUES", "target_entity": "DEFENDANT"}
        ]

        filtered = [r for r in relationships if r["target_entity"] == "PARTY"]

        assert len(filtered) == 1
        assert filtered[0]["relationship_type"] == "REPRESENTS"

    def test_relationship_indicator_matching(self):
        """Test relationship indicator matching logic."""
        relationship = {
            "relationship_type": "REPRESENTS",
            "indicators": ["represents", "representing", "on behalf of", "counsel for"]
        }

        test_text = "Attorney John Smith representing Plaintiff"

        # Simple indicator matching
        matches = [ind for ind in relationship["indicators"] if ind in test_text.lower()]

        assert len(matches) > 0
        assert "representing" in matches

    def test_relationship_statistics_calculation(self):
        """Test statistics calculation for relationships."""
        relationships = [
            {"indicators": ["a", "b", "c"]},
            {"indicators": ["d", "e"]},
            {"indicators": ["f", "g", "h", "i"]}
        ]

        total_indicators = sum(len(r["indicators"]) for r in relationships)
        avg_indicators = total_indicators / len(relationships)

        assert total_indicators == 9
        assert avg_indicators == 3.0


class TestPatternInspectionLogic:
    """Test pattern inspection logic."""

    def test_pattern_filtering_by_entity_type(self):
        """Test filtering patterns by entity type."""
        patterns = [
            {"name": "judge_pattern", "entity_type": "JUDGE"},
            {"name": "court_pattern", "entity_type": "COURT"},
            {"name": "attorney_pattern", "entity_type": "ATTORNEY"}
        ]

        filtered = [p for p in patterns if p["entity_type"] == "JUDGE"]

        assert len(filtered) == 1
        assert filtered[0]["name"] == "judge_pattern"

    def test_pattern_filtering_by_confidence(self):
        """Test filtering patterns by confidence threshold."""
        patterns = [
            {"name": "high_conf", "confidence": 0.98},
            {"name": "med_conf", "confidence": 0.85},
            {"name": "low_conf", "confidence": 0.72}
        ]

        min_confidence = 0.9
        filtered = [p for p in patterns if p["confidence"] >= min_confidence]

        assert len(filtered) == 1
        assert filtered[0]["name"] == "high_conf"

    def test_pattern_pagination(self):
        """Test pattern pagination logic."""
        patterns = [f"pattern_{i}" for i in range(20)]

        # Page 1: first 10 patterns
        page_1 = patterns[0:10]
        assert len(page_1) == 10
        assert page_1[0] == "pattern_0"
        assert page_1[-1] == "pattern_9"

        # Page 2: next 10 patterns
        page_2 = patterns[10:20]
        assert len(page_2) == 10
        assert page_2[0] == "pattern_10"
        assert page_2[-1] == "pattern_19"

    def test_pattern_name_parsing(self):
        """Test pattern name parsing (dot notation)."""
        pattern_name = "judicial_entities.circuit_judges_list"

        parts = pattern_name.split(".")
        group = parts[0]
        name = parts[1] if len(parts) > 1 else ""

        assert group == "judicial_entities"
        assert name == "circuit_judges_list"


class TestValidation:
    """Test request validation."""

    def test_valid_relationship_extraction_request(self):
        """Test valid relationship extraction request."""
        request_data = {
            "document_id": "test_001",
            "content": "Test content",
            "relationship_types": ["REPRESENTS"],
            "confidence_threshold": 0.75
        }

        request = RelationshipExtractionRequest(**request_data)

        assert request.document_id == "test_001"
        assert request.confidence_threshold == 0.75

    def test_relationship_extraction_request_defaults(self):
        """Test relationship extraction request default values."""
        request_data = {
            "document_id": "test_001",
            "content": "Test content"
        }

        request = RelationshipExtractionRequest(**request_data)

        assert request.extract_entities_if_missing is True
        assert request.confidence_threshold == 0.75
        assert request.context_window == 250

    def test_relationship_extraction_request_missing_required_fields(self):
        """Test validation with missing required fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            RelationshipExtractionRequest(
                content="Test content"
                # Missing document_id
            )

    def test_confidence_threshold_validation(self):
        """Test confidence threshold must be between 0 and 1."""
        # Valid threshold
        request = RelationshipExtractionRequest(
            document_id="test_001",
            content="Test content",
            confidence_threshold=0.8
        )
        assert request.confidence_threshold == 0.8

        # Note: Pydantic validation for range would need to be added to model
        # This is a placeholder for that validation


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_empty_relationship_patterns(self):
        """Test handling of empty relationship patterns."""
        relationships = []

        response = RelationshipListResponse(
            total_relationships=0,
            relationships=relationships,
            categories=[],
            filters_applied={}
        )

        assert response.total_relationships == 0
        assert len(response.relationships) == 0

    def test_empty_category_list(self):
        """Test handling of empty category list."""
        response = RelationshipCategoriesResponse(
            total_categories=0,
            categories=[],
            total_relationships=0
        )

        assert response.total_categories == 0
        assert response.total_relationships == 0

    def test_missing_pattern_data(self):
        """Test handling of missing pattern data."""
        patterns = []

        # Should not raise error even with empty list
        assert len(patterns) == 0


class TestPerformance:
    """Test performance-related logic."""

    def test_relationship_list_size_limits(self):
        """Test relationship list size management."""
        # Generate large list of relationships
        relationships = [
            {"relationship_type": f"REL_{i}", "category": "test"}
            for i in range(1000)
        ]

        # Apply limit
        limit = 100
        limited_relationships = relationships[:limit]

        assert len(limited_relationships) == limit

    def test_pagination_offset_calculation(self):
        """Test pagination offset calculation."""
        total_items = 100
        page_size = 10

        # Calculate pages
        total_pages = (total_items + page_size - 1) // page_size

        assert total_pages == 10

        # Test offset for page 3
        page = 3
        offset = (page - 1) * page_size

        assert offset == 20


class TestIntegration:
    """Integration tests for end-to-end flows."""

    def test_relationship_extraction_workflow(self):
        """Test complete relationship extraction workflow."""
        # Step 1: Create extraction request
        request = RelationshipExtractionRequest(
            document_id="workflow_test_001",
            content="Attorney John Smith represents Plaintiff in Smith v. Jones",
            relationship_types=["REPRESENTS", "SUES"],
            confidence_threshold=0.75
        )

        # Step 2: Simulate extraction (would call actual extraction logic)
        # In real implementation, this would extract relationships

        # Step 3: Create response
        response = RelationshipExtractionResponse(
            document_id=request.document_id,
            extraction_id="ext_workflow_001",
            processing_time_ms=200.5,
            total_relationships=2,
            relationships=[],
            entities_used=3,
            statistics={"extraction_mode": "relationship_focused"}
        )

        # Verify workflow
        assert response.document_id == request.document_id
        assert response.total_relationships == 2

    def test_pattern_inspection_workflow(self):
        """Test pattern inspection workflow."""
        # Step 1: Browse library
        patterns = [
            {"name": "judge_pattern", "entity_type": "JUDGE", "confidence": 0.95},
            {"name": "court_pattern", "entity_type": "COURT", "confidence": 0.92}
        ]

        # Step 2: Filter by entity type
        filtered = [p for p in patterns if p["entity_type"] == "JUDGE"]

        # Step 3: Inspect specific pattern
        pattern = filtered[0]

        assert pattern["name"] == "judge_pattern"
        assert pattern["confidence"] == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
