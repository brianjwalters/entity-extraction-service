"""
Orchestrator Test Runner Module for Entity Extraction Service Testing Framework

This module provides direct vLLM integration using ExtractionOrchestrator (not HTTP API).
It's designed to work alongside the existing TestRunner but uses DirectVLLMClient for:
- Faster execution (no HTTP overhead)
- Direct access to extraction pipeline
- Fine-grained control over temperature and document size
- Pattern API validation
- Temperature comparison testing

Usage:
    runner = OrchestratorTestRunner(vllm_client=client)
    result = await runner.run_extraction_test(
        document_path=Path("/srv/luris/be/tests/docs/Rahimi.pdf"),
        char_count=5000,
        temperature=0.0,
        validate_patterns=True
    )

Command Line:
    python -m tests.test_framework.orchestrator_test_runner
    python -m tests.test_framework.orchestrator_test_runner --chars 10000
    python -m tests.test_framework.orchestrator_test_runner --compare-temps
    python -m tests.test_framework.orchestrator_test_runner --validate-patterns
"""

import os
import sys
import time
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Import extraction components
from src.vllm_client.factory import get_default_client
from src.core.extraction_orchestrator import ExtractionOrchestrator
from src.routing.document_router import DocumentRouter
from src.routing.size_detector import SizeDetector

# Import test framework components
from .metrics_collector import MetricsCollector
from .storage_handler import StorageHandler
from .html_generator import HTMLDashboardGenerator

logger = logging.getLogger(__name__)


class OrchestratorTestRunner:
    """
    Test runner using direct vLLM integration via ExtractionOrchestrator.

    Unlike TestRunner which uses HTTP API, this runner:
    - Uses DirectVLLMClient (no HTTP overhead)
    - Works with ExtractionOrchestrator directly
    - Supports shared vLLM client across tests
    - Integrates with existing metrics/storage/dashboard infrastructure
    """

    def __init__(
        self,
        vllm_client=None,
        results_dir: Optional[Path] = None
    ):
        """
        Initialize orchestrator test runner.

        Args:
            vllm_client: Shared vLLM client (optional, will create if None)
            results_dir: Directory for test results (default: tests/results/)
        """
        self.vllm_client = vllm_client
        self.orchestrator = ExtractionOrchestrator(vllm_client=vllm_client)

        # Reuse existing infrastructure
        self.metrics_collector = MetricsCollector()
        self.storage_handler = StorageHandler()
        self.dashboard_generator = HTMLDashboardGenerator()

        # Set up results directory
        if results_dir is None:
            results_dir = Path(__file__).parent.parent / "results"
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def load_document(
        self,
        document_path: Path,
        char_count: int = 5000
    ) -> Optional[str]:
        """
        Load document and extract first N characters.

        Args:
            document_path: Path to PDF document
            char_count: Number of characters to extract

        Returns:
            str: Document text (first char_count chars)
        """
        if not document_path.exists():
            logger.error(f"Document not found: {document_path}")
            return None

        try:
            # Use PyMuPDF (fitz) to extract text from PDF
            import fitz
            doc = fitz.open(document_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            # Extract first char_count characters
            sample_text = text[:char_count]
            logger.info(f"Loaded {len(sample_text):,} chars from {document_path.name}")
            return sample_text

        except Exception as e:
            logger.error(f"Failed to load document: {e}", exc_info=True)
            return None

    async def run_extraction_test(
        self,
        document_path: Path,
        char_count: int = 5000,
        temperature: float = 0.0,
        test_name: Optional[str] = None,
        validate_patterns: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Run direct vLLM extraction with orchestrator.

        Args:
            document_path: Path to PDF document
            char_count: Number of characters to extract
            temperature: Temperature setting for entity extraction
            test_name: Custom test name (optional)
            validate_patterns: Run pattern validation (optional)

        Returns:
            dict: Test results with metrics
        """
        logger.info("="*70)
        logger.info(f"Entity Extraction Test: {test_name or 'Direct vLLM'}")
        logger.info("="*70)

        # Step 1: Load document
        document_text = await self.load_document(document_path, char_count)
        if document_text is None:
            return None

        # Step 2: Set temperature environment variable
        original_temp = os.environ.get('EXTRACTION_ENTITY_TEMPERATURE')
        original_rel_temp = os.environ.get('EXTRACTION_RELATIONSHIP_TEMPERATURE')
        os.environ['EXTRACTION_ENTITY_TEMPERATURE'] = str(temperature)
        os.environ['EXTRACTION_RELATIONSHIP_TEMPERATURE'] = str(temperature)

        try:
            # Step 3: Route document
            router = DocumentRouter()
            size_detector = SizeDetector()
            size_info = size_detector.detect(document_text)
            routing = router.route(document_text, extract_relationships=False)

            logger.info(f"Strategy: {routing.strategy.value}")
            logger.info(f"Document size: {len(document_text):,} chars")
            logger.info(f"Temperature: {temperature}")
            logger.info("Starting extraction...\n")

            # Step 4: Execute extraction
            start = time.time()
            result = await self.orchestrator.extract(document_text, routing, size_info)
            execution_time = time.time() - start

            # Step 5: Convert ExtractionResult to API response format
            api_response = self._convert_to_api_format(result, routing, execution_time)

            # Step 6: Collect metrics
            logger.info("Collecting metrics...")
            metrics = self.metrics_collector.collect_metrics(
                api_response=api_response,
                execution_time=execution_time,
                document_id=document_path.stem
            )

            # Step 7: Pattern validation (optional)
            validation_results = None
            if validate_patterns:
                from .pattern_validator import PatternValidator
                validator = PatternValidator()
                await validator.load_patterns()
                validation_results = validator.validate_entity_types(result.entities)

            # Step 8: Save results
            logger.info("Saving test results...")
            metrics_dict = self.metrics_collector.metrics_to_dict(metrics)
            if validate_patterns and validation_results:
                metrics_dict["pattern_validation"] = validation_results

            self.storage_handler.save_test_result(metrics_dict)

            # Step 9: Generate dashboard
            logger.info("Generating dashboard...")
            all_results = self.storage_handler.load_all_results()
            dashboard_path = self.results_dir / "dashboard.html"
            self.dashboard_generator.generate_dashboard(all_results, dashboard_path)

            # Step 10: Print summary
            logger.info("")
            logger.info("="*70)
            logger.info("Test Completed Successfully")
            logger.info("="*70)
            print(self.metrics_collector.format_metrics_summary(metrics))

            if validate_patterns and validation_results:
                self._print_validation_summary(validation_results)

            logger.info("")
            logger.info(f"📊 Dashboard: file://{dashboard_path.absolute()}")
            logger.info(f"💾 Test history: {self.storage_handler.storage_path}")

            return metrics_dict

        finally:
            # Restore original temperature
            if original_temp:
                os.environ['EXTRACTION_ENTITY_TEMPERATURE'] = original_temp
            else:
                os.environ.pop('EXTRACTION_ENTITY_TEMPERATURE', None)

            if original_rel_temp:
                os.environ['EXTRACTION_RELATIONSHIP_TEMPERATURE'] = original_rel_temp
            else:
                os.environ.pop('EXTRACTION_RELATIONSHIP_TEMPERATURE', None)

    def _convert_to_api_format(
        self,
        result,
        routing,
        execution_time: float
    ) -> Dict[str, Any]:
        """
        Convert ExtractionResult to API response format for MetricsCollector.

        The MetricsCollector expects API response format:
        {
            "routing_decision": {...},
            "processing_stats": {...},
            "entities": [...]
        }

        But ExtractionOrchestrator returns ExtractionResult:
        {
            "entities": [...],
            "strategy": "single_pass",
            "waves_executed": 1,
            "tokens_used": 5920
        }
        """
        return {
            "routing_decision": {
                "strategy": result.strategy.value,
                "prompt_version": "wave_v1",
                "estimated_tokens": result.tokens_used,
                "estimated_duration": execution_time
            },
            "processing_stats": {
                "duration_seconds": execution_time,
                "entities_extracted": len(result.entities),
                "waves_executed": result.waves_executed,
                "tokens_used": result.tokens_used,
                "wave_details": []  # Could be expanded if needed
            },
            "entities": result.entities
        }

    def _print_validation_summary(self, validation_results: Dict[str, Any]) -> None:
        """Print pattern validation summary."""
        print("\n" + "="*70)
        print("Pattern Validation Results")
        print("="*70)
        print(f"Total Entities: {validation_results['total_entities']}")
        print(f"Valid Types: {validation_results['valid_types']}")
        print(f"Invalid Types: {validation_results['invalid_types']}")
        print(f"Pattern Coverage: {validation_results['pattern_coverage']:.1%}")

        if validation_results.get('court_entities'):
            print("\nCourt Entity Validation:")
            for entity in validation_results['court_entities']:
                status = "✅" if entity['expected'] else "⚠️"
                suggested = f" (Expected: {entity['suggested_type']})" if not entity['expected'] else ""
                print(f"  {status} {entity['text']}: {entity['type']}{suggested}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Entity Extraction Test with vLLM Direct Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test
  python -m tests.test_framework.orchestrator_test_runner

  # Custom character count
  python -m tests.test_framework.orchestrator_test_runner --chars 10000

  # Different temperature
  python -m tests.test_framework.orchestrator_test_runner --temperature 0.3

  # Temperature comparison
  python -m tests.test_framework.orchestrator_test_runner --compare-temps

  # With pattern validation
  python -m tests.test_framework.orchestrator_test_runner --validate-patterns

  # Full featured
  python -m tests.test_framework.orchestrator_test_runner \\
      --document /path/to/doc.pdf \\
      --chars 8000 \\
      --compare-temps \\
      --validate-patterns \\
      --verbose
        """
    )

    parser.add_argument(
        "--document",
        type=Path,
        default=Path("/srv/luris/be/tests/docs/Rahimi.pdf"),
        help="Path to PDF document (default: Rahimi.pdf)"
    )
    parser.add_argument(
        "--chars",
        type=int,
        default=5000,
        help="Number of characters to extract (default: 5000)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature for entity extraction (default: 0.0, range: 0.0-2.0)"
    )
    parser.add_argument(
        "--compare-temps",
        action="store_true",
        help="Run temperature comparison (0.0 vs 0.3)"
    )
    parser.add_argument(
        "--validate-patterns",
        action="store_true",
        help="Validate entities against pattern API"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Run test
    success = asyncio.run(run_test(args))

    # Exit with appropriate code
    sys.exit(0 if success else 1)


async def run_test(args) -> bool:
    """Execute test based on command-line arguments."""

    # Initialize vLLM client once
    logger.info("Initializing vLLM client (shared for all tests)...")
    client = await get_default_client(enable_fallback=True)
    logger.info("✅ Client initialized\n")

    try:
        if args.compare_temps:
            # Run temperature comparison
            from .temperature_comparison import TemperatureComparison
            comparison = TemperatureComparison(vllm_client=client)
            result = await comparison.run_comparison(
                document_path=args.document,
                char_count=args.chars,
                temperatures=[0.0, 0.3],
                validate_patterns=args.validate_patterns
            )
            return result is not None
        else:
            # Run single test
            runner = OrchestratorTestRunner(vllm_client=client)
            result = await runner.run_extraction_test(
                document_path=args.document,
                char_count=args.chars,
                temperature=args.temperature,
                validate_patterns=args.validate_patterns
            )
            return result is not None
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    main()
