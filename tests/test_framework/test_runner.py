"""
Test Runner Module for Entity Extraction Service Testing Framework

This is the main orchestrator that coordinates all components:
1. Service health checking
2. Document loading (Rahimi.pdf)
3. API request execution
4. Metrics collection
5. Result storage
6. Dashboard generation

Usage:
    runner = TestRunner()
    runner.run_test()

Command Line:
    python test_runner.py
    python test_runner.py --document /path/to/document.pdf
    python test_runner.py --dashboard-only  # Regenerate dashboard from history
"""

import sys
import time
import logging
import argparse
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# Import framework modules
from .service_health import ServiceHealthChecker, check_service_health
from .metrics_collector import MetricsCollector
from .storage_handler import StorageHandler
from .html_generator import HTMLDashboardGenerator

logger = logging.getLogger(__name__)


class TestRunner:
    """
    Main orchestrator for entity extraction testing.

    Coordinates all testing components and provides a simple interface
    for running extraction tests and generating dashboards.
    """

    def __init__(
        self,
        service_host: str = "localhost",
        service_port: int = 8007,
        results_dir: Optional[Path] = None,
        start_chars: Optional[int] = None,
        end_chars: Optional[int] = None
    ):
        """
        Initialize test runner.

        Args:
            service_host: Entity extraction service hostname
            service_port: Entity extraction service port
            results_dir: Directory for test results (default: tests/results/)
            start_chars: Starting character position (default: 0)
            end_chars: Ending character position (default: None = end of document)
        """
        self.service_host = service_host
        self.service_port = service_port
        self.service_url = f"http://{service_host}:{service_port}"

        # Set up results directory
        if results_dir is None:
            results_dir = Path(__file__).parent.parent / "results"
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Store character range for document loading
        self.start_chars = start_chars if start_chars is not None else 0
        self.end_chars = end_chars  # None means end of document

        # Initialize components
        self.health_checker = ServiceHealthChecker(host=service_host, port=service_port)
        self.metrics_collector = MetricsCollector()
        self.storage_handler = StorageHandler()
        self.dashboard_generator = HTMLDashboardGenerator()

        # Default test document
        self.default_test_document = Path(__file__).parent.parent.parent.parent / "tests" / "docs" / "Rahimi.pdf"

    def check_service_health(self) -> bool:
        """
        Check if service is healthy.

        Returns:
            bool: True if service is healthy
        """
        logger.info("Checking service health...")
        health_result = self.health_checker.perform_health_check()

        if health_result.service_up:
            logger.info("✅ Service is healthy")
            logger.info(f"   Response time: {health_result.response_time_ms:.2f}ms")
            return True
        else:
            logger.error("❌ Service is unhealthy")
            logger.error(f"   Error: {health_result.error_message}")
            return False

    def load_test_document(self, document_path: Optional[Path] = None) -> Optional[str]:
        """
        Load test document content with optional character limit.

        Args:
            document_path: Path to document (default: Rahimi.pdf)

        Returns:
            str: Document content (range extracted if start_chars/end_chars set), or None if loading fails
        """
        if document_path is None:
            document_path = self.default_test_document

        logger.info(f"Loading test document: {document_path}")

        if not document_path.exists():
            logger.error(f"Document not found: {document_path}")
            return None

        try:
            # Load PDF using PyMuPDF (same pattern as orchestrator_test_runner.py)
            import fitz  # PyMuPDF
            doc = fitz.open(document_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            # Apply character range if specified
            original_length = len(text)
            start = self.start_chars
            end = self.end_chars if self.end_chars is not None else original_length

            # Validate range against document length
            if start >= original_length:
                logger.error(
                    f"Error: start_chars ({start:,}) exceeds document length ({original_length:,})"
                )
                return None

            if end > original_length:
                logger.error(
                    f"Error: end_chars ({end:,}) exceeds document length ({original_length:,})"
                )
                return None

            # Extract character range
            if start == 0 and end >= original_length:
                # Full document
                logger.info(f"Loaded {len(text):,} chars (full document)")
            else:
                # Range extraction
                text = text[start:end]
                range_length = len(text)
                percentage = (range_length / original_length) * 100

                logger.info(
                    f"Loaded {range_length:,} chars from range [{start:,}-{end:,}] "
                    f"({percentage:.1f}% of document, total: {original_length:,} chars)"
                )

            return text

        except ImportError:
            logger.error(
                "PyMuPDF (fitz) not installed. Install with: pip install PyMuPDF>=1.23.0"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to load document: {e}", exc_info=True)
            return None

    def call_extraction_api(
        self,
        document_text: str,
        document_id: str = "rahimi_2024",
        use_guided_json: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Call entity extraction API.

        Args:
            document_text: Document content
            document_id: Document identifier
            use_guided_json: Enable guided JSON schema enforcement (default: True)

        Returns:
            dict: API response, or None on failure
        """
        logger.info("Calling entity extraction API...")

        try:
            payload = {
                "document_text": document_text,
                "document_id": document_id
            }

            # Add guided_json schema if enabled
            if use_guided_json:
                from src.schemas.guided_json_schemas import LurisEntityV2ExtractionResponse
                schema = LurisEntityV2ExtractionResponse.model_json_schema()
                payload["extra_body"] = {"guided_json": schema}
                logger.info("✅ Using guided JSON schema for strict validation")

            start_time = time.time()
            response = requests.post(
                f"{self.service_url}/api/v2/process/extract",
                json=payload,
                timeout=240  # 240 second timeout for extraction (Rahimi document takes ~103s)
            )
            execution_time = time.time() - start_time

            if response.status_code == 200:
                logger.info(f"✅ Extraction completed in {execution_time:.2f}s")
                result = response.json()

                # Validate response against LurisEntityV2 schema if guided_json was used
                if use_guided_json:
                    try:
                        from src.schemas.guided_json_schemas import LurisEntityV2ExtractionResponse
                        validated = LurisEntityV2ExtractionResponse.model_validate(result)
                        logger.info(f"✅ Schema validation passed: {len(validated.entities)} entities")
                    except Exception as e:
                        logger.warning(f"⚠️ Schema validation failed: {e}")

                result["_execution_time"] = execution_time  # Add execution time to response
                return result
            else:
                logger.error(f"❌ API returned status {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("❌ API request timed out")
            return None
        except Exception as e:
            logger.error(f"❌ API request failed: {e}", exc_info=True)
            return None

    def run_test(
        self,
        document_path: Optional[Path] = None,
        skip_health_check: bool = False
    ) -> bool:
        """
        Run complete extraction test.

        Args:
            document_path: Path to test document (default: Rahimi.pdf)
            skip_health_check: Skip health check (for testing)

        Returns:
            bool: True if test completed successfully
        """
        logger.info("="*70)
        logger.info("Starting Entity Extraction Test")
        logger.info("="*70)

        # Step 1: Health check
        if not skip_health_check:
            if not self.check_service_health():
                logger.error("Service health check failed. Aborting test.")
                return False

        # Step 2: Load document
        document_text = self.load_test_document(document_path)
        if document_text is None:
            logger.error("Failed to load test document. Aborting test.")
            return False

        document_id = document_path.stem if document_path else "rahimi_2024"

        # Step 3: Call extraction API
        api_response = self.call_extraction_api(document_text, document_id)
        if api_response is None:
            logger.error("API request failed. Aborting test.")
            return False

        execution_time = api_response.pop("_execution_time")

        # Step 4: Collect metrics
        logger.info("Collecting metrics...")
        metrics = self.metrics_collector.collect_metrics(
            api_response=api_response,
            execution_time=execution_time,
            document_id=document_id
        )

        # Step 5: Save results
        logger.info("Saving test results...")
        metrics_dict = self.metrics_collector.metrics_to_dict(metrics)
        if not self.storage_handler.save_test_result(metrics_dict):
            logger.warning("Failed to save test results to storage")

        # Step 6: Generate dashboard
        logger.info("Generating dashboard...")
        all_results = self.storage_handler.load_all_results()
        dashboard_path = self.results_dir / "dashboard.html"
        if self.dashboard_generator.generate_dashboard(all_results, dashboard_path):
            logger.info(f"✅ Dashboard generated: {dashboard_path}")
        else:
            logger.warning("Failed to generate dashboard")

        # Step 7: Print summary
        logger.info("")
        logger.info("="*70)
        logger.info("Test Completed Successfully")
        logger.info("="*70)
        print(self.metrics_collector.format_metrics_summary(metrics))

        logger.info("")
        logger.info(f"📊 Dashboard: file://{dashboard_path.absolute()}")
        logger.info(f"💾 Test history: {self.storage_handler.storage_path}")

        return True

    def run_test_with_options(
        self,
        document_path: Optional[Path] = None,
        skip_health_check: bool = False,
        show_entities: bool = True,
        max_entities: int = 50
    ) -> bool:
        """
        Run complete extraction test with entity display options.

        Args:
            document_path: Path to test document (default: Rahimi.pdf)
            skip_health_check: Skip health check (for testing)
            show_entities: Whether to display entity table (default: True)
            max_entities: Maximum entities to display (default: 50)

        Returns:
            bool: True if test completed successfully
        """
        logger.info("="*70)
        logger.info("Starting Entity Extraction Test")
        logger.info("="*70)

        # Step 1: Health check
        if not skip_health_check:
            if not self.check_service_health():
                logger.error("Service health check failed. Aborting test.")
                return False

        # Step 2: Load document
        document_text = self.load_test_document(document_path)
        if document_text is None:
            logger.error("Failed to load test document. Aborting test.")
            return False

        document_id = document_path.stem if document_path else "rahimi_2024"

        # Step 3: Call extraction API
        api_response = self.call_extraction_api(document_text, document_id)
        if api_response is None:
            logger.error("API request failed. Aborting test.")
            return False

        execution_time = api_response.pop("_execution_time")

        # Step 4: Collect metrics
        logger.info("Collecting metrics...")
        metrics = self.metrics_collector.collect_metrics(
            api_response=api_response,
            execution_time=execution_time,
            document_id=document_id
        )

        # Step 5: Save results
        logger.info("Saving test results...")
        metrics_dict = self.metrics_collector.metrics_to_dict(metrics)
        if not self.storage_handler.save_test_result(metrics_dict):
            logger.warning("Failed to save test results to storage")

        # Step 6: Generate dashboard
        logger.info("Generating dashboard...")
        all_results = self.storage_handler.load_all_results()
        dashboard_path = self.results_dir / "dashboard.html"
        if self.dashboard_generator.generate_dashboard(all_results, dashboard_path):
            logger.info(f"✅ Dashboard generated: {dashboard_path}")
        else:
            logger.warning("Failed to generate dashboard")

        # Step 7: Print summary with entity display options
        logger.info("")
        logger.info("="*70)
        logger.info("Test Completed Successfully")
        logger.info("="*70)
        print(self.metrics_collector.format_metrics_summary(
            metrics,
            show_entities=show_entities,
            max_entities=max_entities
        ))

        logger.info("")
        logger.info(f"📊 Dashboard: file://{dashboard_path.absolute()}")
        logger.info(f"💾 Test history: {self.storage_handler.storage_path}")

        return True

    def test_wave4_relationships(
        self,
        document_path: Optional[Path] = None
    ) -> bool:
        """
        Test Wave 4 relationship extraction with guided JSON.

        Args:
            document_path: Path to test document (default: Rahimi.pdf)

        Returns:
            bool: True if test passed
        """
        from src.schemas.guided_json_schemas import LurisRelationshipExtractionResponse

        logger.info("="*70)
        logger.info("Testing Wave 4 Relationship Extraction")
        logger.info("="*70)

        # Load document
        document_text = self.load_test_document(document_path)
        if not document_text:
            logger.error("Failed to load test document")
            return False

        # Call relationship extraction endpoint
        schema = LurisRelationshipExtractionResponse.model_json_schema()
        payload = {
            "document_text": document_text,
            "extract_relationships": True,
            "extra_body": {"guided_json": schema}
        }

        try:
            logger.info("Calling Wave 4 relationship extraction API...")
            start_time = time.time()
            response = requests.post(
                f"{self.service_url}/api/v2/process/extract/relationships",
                json=payload,
                timeout=300
            )
            execution_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                # Validate with schema
                validated = LurisRelationshipExtractionResponse.model_validate(result)

                logger.info(f"✅ Wave 4 extraction completed in {execution_time:.2f}s")
                logger.info(f"✅ Relationships extracted: {len(validated.relationships)}")
                logger.info(f"✅ Entities in relationships: {len(validated.entities)}")

                # Print sample relationships
                if validated.relationships:
                    logger.info("\n📊 Sample Relationships:")
                    for i, rel in enumerate(validated.relationships[:3]):
                        logger.info(f"   {i+1}. {rel.get('relationship_type', 'UNKNOWN')}: "
                                  f"{rel.get('source_entity_id', 'N/A')} → {rel.get('target_entity_id', 'N/A')} "
                                  f"(confidence: {rel.get('confidence', 0):.2%})")

                return True
            else:
                logger.error(f"❌ Relationship extraction failed: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Relationship extraction error: {e}", exc_info=True)
            return False

    def regenerate_dashboard(self) -> bool:
        """
        Regenerate dashboard from stored test history.

        Returns:
            bool: True if dashboard generated successfully
        """
        logger.info("Regenerating dashboard from test history...")

        all_results = self.storage_handler.load_all_results()
        if not all_results:
            logger.error("No test results found in history")
            return False

        dashboard_path = self.results_dir / "dashboard.html"
        if self.dashboard_generator.generate_dashboard(all_results, dashboard_path):
            logger.info(f"✅ Dashboard regenerated: {dashboard_path}")
            logger.info(f"   Total tests: {len(all_results)}")
            return True
        else:
            logger.error("Failed to regenerate dashboard")
            return False


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Entity Extraction Service Test Runner"
    )
    parser.add_argument(
        "--document",
        type=Path,
        help="Path to test document (default: Rahimi.pdf)"
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Only regenerate dashboard from test history"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--start_chars",
        type=int,
        default=None,
        help="Starting character position for document extraction (default: 0). "
             "Example: --start_chars 5000 starts extraction at character 5000"
    )
    parser.add_argument(
        "--end_chars",
        type=int,
        default=None,
        help="Ending character position for document extraction (default: end of document). "
             "Example: --end_chars 10000 extracts up to character 10000"
    )
    parser.add_argument(
        "--max-entities",
        type=int,
        default=50,
        help="Maximum entities to display in console (default: 50, use 0 for unlimited)"
    )
    parser.add_argument(
        "--no-entity-display",
        action="store_true",
        help="Disable entity table in console output (show summary stats only)"
    )

    args = parser.parse_args()

    # Validate character range parameters
    if args.start_chars is not None and args.start_chars < 0:
        parser.error("--start_chars must be a non-negative integer")

    if args.end_chars is not None and args.end_chars <= 0:
        parser.error("--end_chars must be a positive integer")

    if args.start_chars is not None and args.end_chars is not None:
        if args.start_chars >= args.end_chars:
            parser.error(
                f"--start_chars ({args.start_chars}) must be less than "
                f"--end_chars ({args.end_chars})"
            )

    # Validate --max-entities if provided
    if args.max_entities < 0:
        parser.error("--max-entities must be non-negative (use 0 for unlimited)")

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Create runner
    runner = TestRunner(
        start_chars=args.start_chars,
        end_chars=args.end_chars
    )

    # Execute command
    if args.dashboard_only:
        success = runner.regenerate_dashboard()
    else:
        # Use run_test_with_options to pass entity display parameters
        success = runner.run_test_with_options(
            document_path=args.document,
            show_entities=not args.no_entity_display,
            max_entities=args.max_entities
        )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
