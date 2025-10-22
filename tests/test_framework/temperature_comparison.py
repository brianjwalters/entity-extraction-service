"""
Temperature Comparison Module for Entity Extraction Service Testing Framework

This module runs extraction at multiple temperatures and compares results.
It replicates the analysis from test_temp_with_orchestrator.py but integrates
with the test framework infrastructure.

Usage:
    comparison = TemperatureComparison(vllm_client=client)
    result = await comparison.run_comparison(
        document_path=Path("/srv/luris/be/tests/docs/Rahimi.pdf"),
        char_count=5000,
        temperatures=[0.0, 0.3],
        validate_patterns=True
    )
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .orchestrator_test_runner import OrchestratorTestRunner

logger = logging.getLogger(__name__)


class TemperatureComparison:
    """
    Run extraction at multiple temperatures and compare results.

    This module replicates the analysis from test_temp_with_orchestrator.py
    but integrates with the test framework infrastructure.
    """

    def __init__(self, vllm_client=None):
        """
        Initialize temperature comparison.

        Args:
            vllm_client: Shared vLLM client (optional)
        """
        self.vllm_client = vllm_client
        self.runner = OrchestratorTestRunner(vllm_client=vllm_client)

    async def run_comparison(
        self,
        document_path: Path,
        char_count: int = 5000,
        temperatures: List[float] = [0.0, 0.3],
        validate_patterns: bool = False
    ) -> Dict[str, Any]:
        """
        Run extraction at multiple temperatures and compare.

        Args:
            document_path: Path to PDF document
            char_count: Number of characters to extract
            temperatures: List of temperatures to test (default: [0.0, 0.3])
            validate_patterns: Run pattern validation (optional)

        Returns:
            {
                "tests": [
                    {"temperature": 0.0, "result": {...}},
                    {"temperature": 0.3, "result": {...}}
                ],
                "comparison": {
                    "entity_count_diff": 0,
                    "entity_type_overlap": ["CASE_CITATION", ...],
                    "entity_text_overlap_count": 5,
                    "court_entities": {...}
                }
            }
        """
        logger.info("="*70)
        logger.info("TEMPERATURE COMPARISON TEST")
        logger.info("="*70)
        logger.info(f"Document: {document_path.name}")
        logger.info(f"Characters: {char_count:,}")
        logger.info(f"Temperatures: {temperatures}")
        if validate_patterns:
            logger.info("Pattern Validation: Enabled")
        logger.info("="*70)
        logger.info("")

        results = []

        # Run test for each temperature
        for temp in temperatures:
            test_name = f"Temperature {temp}"
            logger.info(f"\n{'='*70}")
            logger.info(f"Running test at temperature {temp}...")
            logger.info(f"{'='*70}\n")

            result = await self.runner.run_extraction_test(
                document_path=document_path,
                char_count=char_count,
                temperature=temp,
                test_name=test_name,
                validate_patterns=validate_patterns
            )

            if result:
                results.append({
                    "temperature": temp,
                    "result": result
                })

        # Generate comparison analysis
        comparison = self._analyze_comparison(results)

        # Print comparison summary
        self._print_comparison_summary(results, comparison)

        return {
            "tests": results,
            "comparison": comparison
        }

    def _analyze_comparison(self, results: List[Dict]) -> Dict[str, Any]:
        """
        Analyze differences between temperature tests.

        Replicates analysis from test_temp_with_orchestrator.py lines 178-230.

        Args:
            results: List of test results

        Returns:
            dict: Comparison analysis
        """
        if len(results) < 2:
            logger.warning("Need at least 2 results for comparison")
            return {}

        temp0_result = results[0]["result"]
        temp1_result = results[1]["result"]

        # Extract entities
        temp0_entities = temp0_result["raw_response"]["entities"]
        temp1_entities = temp1_result["raw_response"]["entities"]

        # Entity count comparison
        entity_count_diff = len(temp1_entities) - len(temp0_entities)

        # Entity type comparison
        temp0_types = set(e.get("entity_type") for e in temp0_entities if e.get("entity_type"))
        temp1_types = set(e.get("entity_type") for e in temp1_entities if e.get("entity_type"))

        type_overlap = temp0_types & temp1_types
        only_temp0 = temp0_types - temp1_types
        only_temp1 = temp1_types - temp0_types

        # Entity text comparison
        temp0_texts = set(e.get("text") for e in temp0_entities if e.get("text"))
        temp1_texts = set(e.get("text") for e in temp1_entities if e.get("text"))

        text_overlap = temp0_texts & temp1_texts
        only_temp0_texts = temp0_texts - temp1_texts
        only_temp1_texts = temp1_texts - temp0_texts

        # Court entity comparison
        temp0_courts = [e for e in temp0_entities if "COURT" in e.get("entity_type", "")]
        temp1_courts = [e for e in temp1_entities if "COURT" in e.get("entity_type", "")]

        return {
            "entity_count_diff": entity_count_diff,
            "temp0_count": len(temp0_entities),
            "temp1_count": len(temp1_entities),
            "entity_type_overlap": sorted(list(type_overlap)),
            "entity_types_only_temp0": sorted(list(only_temp0)),
            "entity_types_only_temp1": sorted(list(only_temp1)),
            "entity_text_overlap_count": len(text_overlap),
            "entity_texts_only_temp0": sorted(list(only_temp0_texts))[:5],  # Limit to first 5
            "entity_texts_only_temp1": sorted(list(only_temp1_texts))[:5],  # Limit to first 5
            "court_entities": {
                "temp0_count": len(temp0_courts),
                "temp1_count": len(temp1_courts),
                "temp0_entities": temp0_courts[:5],  # Limit to first 5
                "temp1_entities": temp1_courts[:5]   # Limit to first 5
            }
        }

    def _print_comparison_summary(
        self,
        results: List[Dict],
        comparison: Dict[str, Any]
    ) -> None:
        """
        Print comparison summary.

        Replicates output from test_temp_with_orchestrator.py lines 178-238.

        Args:
            results: List of test results
            comparison: Comparison analysis
        """
        if not results or len(results) < 2:
            logger.warning("Cannot print comparison summary: insufficient results")
            return

        print("\n" + "="*70)
        print("TEMPERATURE COMPARISON ANALYSIS")
        print("="*70)

        temp0 = results[0]["temperature"]
        temp1 = results[1]["temperature"]
        temp0_count = comparison['temp0_count']
        temp1_count = comparison['temp1_count']

        print(f"\n📊 Entity Counts:")
        print(f"  Temperature {temp0}: {temp0_count} entities")
        print(f"  Temperature {temp1}: {temp1_count} entities")
        print(f"  Difference: {comparison['entity_count_diff']} entities")

        print(f"\n🏷️  Entity Type Diversity:")
        print(f"  Temperature {temp0}: {len(results[0]['result']['entity_distribution']['entities_by_type'])} unique types")
        print(f"  Temperature {temp1}: {len(results[1]['result']['entity_distribution']['entities_by_type'])} unique types")
        print(f"  Shared types: {len(comparison['entity_type_overlap'])}")

        if comparison.get('entity_types_only_temp0'):
            print(f"  Only in {temp0}: {comparison['entity_types_only_temp0']}")
        if comparison.get('entity_types_only_temp1'):
            print(f"  Only in {temp1}: {comparison['entity_types_only_temp1']}")

        print(f"\n📝 Entity Text Overlap:")
        print(f"  Exact matches: {comparison['entity_text_overlap_count']}")
        print(f"  Only in {temp0}: {len(comparison['entity_texts_only_temp0'])} entities")
        if comparison['entity_texts_only_temp0']:
            for text in comparison['entity_texts_only_temp0']:
                print(f"    - {text[:80]}...")  # Truncate long texts
        print(f"  Only in {temp1}: {len(comparison['entity_texts_only_temp1'])} entities")
        if comparison['entity_texts_only_temp1']:
            for text in comparison['entity_texts_only_temp1']:
                print(f"    - {text[:80]}...")  # Truncate long texts

        print(f"\n⚖️  Court Entity Classification:")
        court_data = comparison['court_entities']
        print(f"  Temperature {temp0}: {court_data['temp0_count']} court entities")
        if court_data['temp0_entities']:
            for e in court_data['temp0_entities']:
                print(f"    - [{e.get('entity_type')}] {e.get('text')}")

        print(f"  Temperature {temp1}: {court_data['temp1_count']} court entities")
        if court_data['temp1_entities']:
            for e in court_data['temp1_entities']:
                print(f"    - [{e.get('entity_type')}] {e.get('text')}")

        # Check for missing Supreme Court entity
        all_entities = []
        for result in results:
            all_entities.extend(result["result"]["raw_response"]["entities"])

        supreme_court_found = any(
            "supreme court" in e.get("text", "").lower()
            for e in all_entities
        )

        if not supreme_court_found:
            print(f"\n  ⚠️  Issue: SUPREME COURT not extracted in either test")
            print(f"     Expected entity type: FEDERAL_COURTS")

        print("\n" + "="*70)
        print("✅ COMPARISON COMPLETE")
        print("="*70)
