"""
Pattern Validation Module for Entity Extraction Service Testing Framework

This module validates extracted entities against pattern API definitions.
It ensures:
1. All entity types exist in pattern API
2. Court entities use proper types (FEDERAL_COURTS, not ORGANIZATION)
3. Entity subtypes match pattern expectations

Usage:
    validator = PatternValidator()
    await validator.load_patterns()
    validation_results = validator.validate_entity_types(entities)
"""

import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PatternValidator:
    """
    Validate extracted entities against pattern API definitions.

    This validator ensures:
    1. All entity types exist in pattern API
    2. Court entities use proper types (FEDERAL_COURTS, not ORGANIZATION)
    3. Entity subtypes match pattern expectations
    """

    def __init__(
        self,
        pattern_api_url: str = "http://10.10.0.87:8007/api/v1/patterns"
    ):
        """
        Initialize pattern validator.

        Args:
            pattern_api_url: Base URL for pattern API
        """
        self.pattern_api_url = pattern_api_url
        self._patterns = None  # Cache patterns
        self._entity_types = set()  # Valid entity types
        self._court_patterns = {}  # Court-specific patterns

    async def load_patterns(self) -> Dict[str, Any]:
        """
        Fetch patterns from API.

        Endpoint: GET /api/v1/patterns?format=detailed
        Returns: {"patterns": [{"entity_type": "FEDERAL_COURTS", ...}, ...]}

        Returns:
            dict: Pattern data from API
        """
        try:
            response = requests.get(
                f"{self.pattern_api_url}?format=detailed",
                timeout=10
            )
            response.raise_for_status()

            self._patterns = response.json()

            # Extract valid entity types
            patterns_list = self._patterns.get("patterns", [])
            if not patterns_list:
                logger.warning("No patterns returned from API")
                return self._patterns

            for pattern in patterns_list:
                entity_type = pattern.get("entity_type")
                if entity_type:
                    self._entity_types.add(entity_type)

                    # Store court patterns separately
                    if "COURT" in entity_type:
                        self._court_patterns[entity_type] = pattern

            logger.info(f"Loaded {len(self._entity_types)} entity types from pattern API")
            logger.info(f"Found {len(self._court_patterns)} court-related patterns")
            return self._patterns

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to load patterns from API: {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading patterns: {e}", exc_info=True)
            return {}

    def validate_entity_types(
        self,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate extracted entity types match pattern definitions.

        Args:
            entities: List of extracted entities

        Returns:
            {
                "total_entities": 5,
                "valid_types": 5,
                "invalid_types": 0,
                "invalid_entities": [],
                "court_entities": [
                    {
                        "text": "SUPREME COURT OF THE UNITED STATES",
                        "type": "ORGANIZATION",
                        "expected": False,
                        "suggested_type": "FEDERAL_COURTS"
                    }
                ],
                "pattern_coverage": 1.0
            }
        """
        if not self._patterns:
            logger.warning("Patterns not loaded. Call load_patterns() first.")
            return {
                "error": "Patterns not loaded",
                "total_entities": len(entities),
                "valid_types": 0,
                "invalid_types": 0,
                "pattern_coverage": 0.0
            }

        valid_count = 0
        invalid_entities = []
        court_entities = []

        for entity in entities:
            entity_type = entity.get("entity_type")
            entity_text = entity.get("text", "")

            # Check if entity type is valid
            if entity_type in self._entity_types:
                valid_count += 1
            else:
                invalid_entities.append({
                    "text": entity_text,
                    "type": entity_type,
                    "reason": "Type not found in pattern API"
                })

            # Special validation for court entities
            if self._should_be_court_entity(entity_text):
                is_court_type = "COURT" in entity_type
                court_entities.append({
                    "text": entity_text,
                    "type": entity_type,
                    "expected": is_court_type,
                    "suggested_type": self._suggest_court_type(entity_text)
                })

        total_entities = len(entities)
        invalid_count = len(invalid_entities)
        pattern_coverage = valid_count / total_entities if total_entities > 0 else 0.0

        return {
            "total_entities": total_entities,
            "valid_types": valid_count,
            "invalid_types": invalid_count,
            "invalid_entities": invalid_entities,
            "court_entities": court_entities,
            "pattern_coverage": pattern_coverage
        }

    def _should_be_court_entity(self, text: str) -> bool:
        """
        Check if text should be classified as a court entity.

        Args:
            text: Entity text

        Returns:
            bool: True if text appears to be a court reference
        """
        court_keywords = [
            "court",
            "supreme court",
            "district court",
            "circuit",
            "appeals",
            "tribunal",
            "judiciary"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in court_keywords)

    def _suggest_court_type(self, text: str) -> Optional[str]:
        """
        Suggest appropriate court entity type.

        Args:
            text: Entity text

        Returns:
            str: Suggested entity type, or None
        """
        text_lower = text.lower()

        if "supreme court" in text_lower:
            if "united states" in text_lower or "u.s." in text_lower or "u. s." in text_lower:
                return "FEDERAL_COURTS"
            else:
                return "STATE_COURTS"
        elif "circuit" in text_lower:
            return "CIRCUITS"
        elif "district" in text_lower:
            if "federal" in text_lower or "united states" in text_lower:
                return "DISTRICT"
            else:
                return "STATE_COURTS"
        elif "bankruptcy" in text_lower or "tax court" in text_lower:
            return "SPECIALIZED_COURTS"
        elif "appeals" in text_lower:
            return "CIRCUITS"
        else:
            return "COURT"

    def get_pattern_summary(self) -> Dict[str, Any]:
        """
        Get summary of loaded patterns.

        Returns:
            dict: Pattern summary
        """
        if not self._patterns:
            return {
                "loaded": False,
                "total_types": 0,
                "court_types": 0
            }

        return {
            "loaded": True,
            "total_types": len(self._entity_types),
            "court_types": len(self._court_patterns),
            "entity_types": sorted(list(self._entity_types)),
            "court_entity_types": sorted(list(self._court_patterns.keys()))
        }


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def test_validator():
        """Test pattern validator with mock entities."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        validator = PatternValidator()

        # Load patterns
        print("Loading patterns from API...")
        await validator.load_patterns()

        # Get summary
        summary = validator.get_pattern_summary()
        print(f"\nPattern Summary:")
        print(f"  Total Types: {summary['total_types']}")
        print(f"  Court Types: {summary['court_types']}")

        # Mock entities for testing
        mock_entities = [
            {
                "entity_type": "CASE_CITATION",
                "text": "United States v. Rahimi",
                "confidence": 0.95
            },
            {
                "entity_type": "ORGANIZATION",  # Should be FEDERAL_COURTS
                "text": "SUPREME COURT OF THE UNITED STATES",
                "confidence": 1.0
            },
            {
                "entity_type": "STATUTE_CITATION",
                "text": "18 U.S.C. § 922(g)(8)",
                "confidence": 0.92
            }
        ]

        # Validate
        print("\nValidating mock entities...")
        results = validator.validate_entity_types(mock_entities)

        print(f"\nValidation Results:")
        print(f"  Total Entities: {results['total_entities']}")
        print(f"  Valid Types: {results['valid_types']}")
        print(f"  Invalid Types: {results['invalid_types']}")
        print(f"  Pattern Coverage: {results['pattern_coverage']:.1%}")

        if results['court_entities']:
            print(f"\nCourt Entity Validation:")
            for entity in results['court_entities']:
                status = "✅" if entity['expected'] else "⚠️"
                suggested = f" (Expected: {entity['suggested_type']})" if not entity['expected'] else ""
                print(f"  {status} {entity['text']}: {entity['type']}{suggested}")

    asyncio.run(test_validator())
