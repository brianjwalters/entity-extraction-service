#!/usr/bin/env python3
"""
Comprehensive vLLM Optimization Test Orchestrator

This module manages the complete testing cycle for vLLM configurations:
1. Iterates through all 24 vLLM configurations
2. Manages vLLM service lifecycle (stop/start/health check)
3. Tests entity extraction on multiple documents with different strategies
4. Collects performance metrics and entity extraction results
5. Handles failures gracefully and continues testing

Author: Test Engineering Team
Date: 2025-09-09
"""

import asyncio
import json
import subprocess
import time
import aiohttp
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import signal

# Add parent directory to path for imports
from metrics_collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'vllm_optimization_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from a single extraction test"""
    test_id: str
    config_id: str
    document: str
    strategy: str
    extraction_time_ms: float
    entities: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    entity_count: int = 0
    citation_count: int = 0
    
    def __post_init__(self):
        """Calculate counts after initialization"""
        self.entity_count = len(self.entities) if self.entities else 0
        self.citation_count = len(self.citations) if self.citations else 0


class VLLMServiceManager:
    """Manages vLLM service lifecycle"""
    
    def __init__(self, timeout: int = 120):
        """
        Initialize service manager
        
        Args:
            timeout: Maximum time to wait for service startup in seconds
        """
        self.timeout = timeout
        self.current_config: Optional[str] = None
        
    async def stop_service(self) -> bool:
        """Stop the current vLLM service"""
        try:
            logger.info("Stopping vLLM service...")
            
            # Stop the service
            result = subprocess.run(
                ["sudo", "systemctl", "stop", "luris-vllm"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to stop service: {result.stderr}")
                # Try force kill as fallback
                subprocess.run(["sudo", "pkill", "-9", "-f", "vllm"], capture_output=True)
            
            # Wait for service to fully stop
            await asyncio.sleep(5)
            
            # Verify service is stopped
            status_result = subprocess.run(
                ["sudo", "systemctl", "is-active", "luris-vllm"],
                capture_output=True,
                text=True
            )
            
            is_stopped = status_result.stdout.strip() == "inactive"
            logger.info(f"Service stopped: {is_stopped}")
            return is_stopped
            
        except Exception as e:
            logger.error(f"Error stopping service: {e}")
            return False
    
    async def start_service(self, config_id: str) -> bool:
        """
        Start vLLM service with specific configuration
        
        Args:
            config_id: Configuration identifier (e.g., 'dual_gpu_config_021')
        
        Returns:
            True if service started successfully
        """
        try:
            logger.info(f"Starting vLLM service with config: {config_id}")
            
            # Path to the configuration shell script
            config_script = f"/srv/luris/be/entity-extraction-service/tests/vllm_configs/{config_id}.sh"
            
            if not Path(config_script).exists():
                logger.error(f"Configuration script not found: {config_script}")
                return False
            
            # Execute the configuration script
            result = subprocess.run(
                ["sudo", "bash", config_script],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start service: {result.stderr}")
                return False
            
            self.current_config = config_id
            
            # Wait for service to be ready
            return await self.wait_for_service()
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout starting service with config: {config_id}")
            return False
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            return False
    
    async def wait_for_service(self) -> bool:
        """Wait for vLLM service to be ready"""
        logger.info("Waiting for vLLM service to be ready...")
        
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < self.timeout:
                try:
                    # Check vLLM health endpoint
                    async with session.get(
                        "http://localhost:8080/health",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.info("vLLM service is ready")
                            return True
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass
                
                await asyncio.sleep(5)
        
        logger.error(f"vLLM service failed to start within {self.timeout} seconds")
        return False


class EntityExtractionTester:
    """Manages entity extraction testing"""
    
    def __init__(self, base_url: str = "http://localhost:8007", timeout: int = 2700):
        """
        Initialize extraction tester
        
        Args:
            base_url: Base URL for entity extraction service
            timeout: Request timeout in seconds (45 minutes default)
        """
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.upload_url = "http://localhost:8008"
        
    async def upload_document(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Upload document and get markdown content
        
        Returns:
            Tuple of (document_id, markdown_content) or (None, None) on error
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare multipart form data
                with open(file_path, 'rb') as f:
                    form_data = aiohttp.FormData()
                    form_data.add_field('file', f, filename=Path(file_path).name)
                    form_data.add_field('client_id', 'vllm_optimization_test')
                    form_data.add_field('case_id', f'test_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                    
                    # Upload document
                    async with session.post(
                        f"{self.upload_url}/api/v1/upload",
                        data=form_data,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result.get('document_id'), result.get('markdown_content')
                        else:
                            logger.error(f"Upload failed with status {response.status}")
                            return None, None
                            
        except Exception as e:
            logger.error(f"Error uploading document {file_path}: {e}")
            return None, None
    
    async def extract_entities(
        self,
        document_id: str,
        content: str,
        strategy: str,
        extraction_mode: str = "ai_enhanced"
    ) -> Optional[Dict[str, Any]]:
        """
        Extract entities from document content
        
        Args:
            document_id: Document identifier
            content: Markdown content
            strategy: Extraction strategy (AI_ENHANCED, UNIFIED, etc.)
            extraction_mode: Extraction mode (ai_enhanced, hybrid, etc.)
        
        Returns:
            Extraction results or None on error
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare extraction request
                payload = {
                    "document_id": document_id,
                    "content": content,
                    "extraction_mode": extraction_mode,
                    "extraction_strategy": strategy.lower(),
                    "confidence_threshold": 0.7,
                    "enable_relationships": True,
                    "max_entities": 500
                }
                
                # Make extraction request
                start_time = time.time()
                async with session.post(
                    f"{self.base_url}/api/v1/extract",
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    extraction_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        result['extraction_time_ms'] = extraction_time_ms
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Extraction failed with status {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error(f"Extraction timeout after {self.timeout.total} seconds")
            return None
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return None
    
    async def test_extraction(
        self,
        config_id: str,
        document_path: str,
        strategy: str,
        metrics_collector: Optional[MetricsCollector] = None
    ) -> ExtractionResult:
        """
        Test entity extraction for a specific configuration and document
        
        Args:
            config_id: vLLM configuration ID
            document_path: Path to test document
            strategy: Extraction strategy
            metrics_collector: Optional metrics collector
        
        Returns:
            ExtractionResult with test results
        """
        document_name = Path(document_path).name
        test_id = f"test_{config_id}_{document_name.replace('.', '_')}_{strategy.lower()}"
        
        logger.info(f"Testing extraction - Config: {config_id}, Doc: {document_name}, Strategy: {strategy}")
        
        try:
            # Upload document
            document_id, markdown_content = await self.upload_document(document_path)
            if not document_id or not markdown_content:
                return ExtractionResult(
                    test_id=test_id,
                    config_id=config_id,
                    document=document_name,
                    strategy=strategy,
                    extraction_time_ms=0,
                    entities=[],
                    citations=[],
                    metrics={},
                    success=False,
                    error="Document upload failed"
                )
            
            # Extract entities
            result = await self.extract_entities(document_id, markdown_content, strategy)
            
            if not result:
                return ExtractionResult(
                    test_id=test_id,
                    config_id=config_id,
                    document=document_name,
                    strategy=strategy,
                    extraction_time_ms=0,
                    entities=[],
                    citations=[],
                    metrics={},
                    success=False,
                    error="Entity extraction failed"
                )
            
            # Collect metrics if collector is available
            metrics = {}
            if metrics_collector:
                metrics = metrics_collector.get_summary_statistics()
            
            # Parse entities and citations
            entities = result.get('entities', [])
            citations = result.get('citations', [])
            
            # Create structured entity list with all details
            structured_entities = []
            for entity in entities:
                structured_entities.append({
                    "type": entity.get("entity_type", "UNKNOWN"),
                    "value": entity.get("text", entity.get("cleaned_text", "")),
                    "confidence": entity.get("confidence_score", 0.0),
                    "position": entity.get("position", {}),
                    "extraction_method": entity.get("extraction_method", "unknown"),
                    "attributes": entity.get("attributes", {})
                })
            
            # Create structured citation list
            structured_citations = []
            for citation in citations:
                structured_citations.append({
                    "type": citation.get("citation_type", "UNKNOWN"),
                    "value": citation.get("original_text", citation.get("cleaned_citation", "")),
                    "confidence": citation.get("confidence_score", 0.0),
                    "position": citation.get("position", {}),
                    "components": citation.get("components", {}),
                    "bluebook_compliant": citation.get("bluebook_compliant", False)
                })
            
            return ExtractionResult(
                test_id=test_id,
                config_id=config_id,
                document=document_name,
                strategy=strategy,
                extraction_time_ms=result.get('extraction_time_ms', result.get('processing_time_ms', 0)),
                entities=structured_entities,
                citations=structured_citations,
                metrics=metrics,
                success=True,
                error=None
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in test_extraction: {e}")
            return ExtractionResult(
                test_id=test_id,
                config_id=config_id,
                document=document_name,
                strategy=strategy,
                extraction_time_ms=0,
                entities=[],
                citations=[],
                metrics={},
                success=False,
                error=str(e)
            )


class TestOrchestrator:
    """Main test orchestration controller"""
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize test orchestrator
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir or Path("/srv/luris/be/entity-extraction-service/tests/results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.service_manager = VLLMServiceManager()
        self.extraction_tester = EntityExtractionTester()
        self.results: List[ExtractionResult] = []
        self.config_failures: Dict[str, str] = {}
        
        # Test configuration
        self.test_documents = [
            "/srv/luris/be/tests/docs/Rahimi.pdf",
            "/srv/luris/be/tests/docs/dobbs.pdf"
        ]
        self.test_strategies = ["AI_ENHANCED", "UNIFIED"]
        
        # Load vLLM configurations
        self.vllm_configs = self._load_configurations()
        
    def _load_configurations(self) -> List[str]:
        """Load list of vLLM configurations"""
        config_dir = Path("/srv/luris/be/entity-extraction-service/tests/vllm_configs")
        configs = []
        
        # Look for all configuration JSON files
        for config_file in sorted(config_dir.glob("*.json")):
            config_name = config_file.stem
            if config_name.startswith(("single_gpu_config_", "dual_gpu_config_")):
                configs.append(config_name)
        
        logger.info(f"Loaded {len(configs)} vLLM configurations")
        return configs
    
    async def run_tests(self, specific_configs: Optional[List[str]] = None):
        """
        Run complete test suite
        
        Args:
            specific_configs: Optional list of specific configs to test
        """
        configs_to_test = specific_configs or self.vllm_configs
        total_configs = len(configs_to_test)
        
        logger.info(f"Starting test orchestration for {total_configs} configurations")
        logger.info(f"Test documents: {self.test_documents}")
        logger.info(f"Test strategies: {self.test_strategies}")
        
        for idx, config_id in enumerate(configs_to_test, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing configuration {idx}/{total_configs}: {config_id}")
            logger.info(f"{'='*60}")
            
            try:
                # Stop any existing service
                await self.service_manager.stop_service()
                
                # Start service with new configuration
                if not await self.service_manager.start_service(config_id):
                    logger.error(f"Failed to start service for {config_id}")
                    self.config_failures[config_id] = "Service startup failed"
                    continue
                
                # Initialize metrics collector for this configuration
                metrics_collector = MetricsCollector(
                    config_id=config_id,
                    collection_interval=2.0,
                    gpu_ids=[0, 1],
                    output_dir=self.output_dir / "metrics"
                )
                
                # Start metrics collection
                await metrics_collector.start(enable_display=False)
                
                # Test each document with each strategy
                for document_path in self.test_documents:
                    for strategy in self.test_strategies:
                        # Run extraction test
                        result = await self.extraction_tester.test_extraction(
                            config_id=config_id,
                            document_path=document_path,
                            strategy=strategy,
                            metrics_collector=metrics_collector
                        )
                        
                        # Retry once if failed
                        if not result.success:
                            logger.warning(f"Retrying failed test: {result.test_id}")
                            await asyncio.sleep(5)
                            result = await self.extraction_tester.test_extraction(
                                config_id=config_id,
                                document_path=document_path,
                                strategy=strategy,
                                metrics_collector=metrics_collector
                            )
                        
                        # Store result
                        self.results.append(result)
                        
                        # Log summary
                        if result.success:
                            logger.info(f"✓ Test successful: {result.test_id}")
                            logger.info(f"  - Entities found: {result.entity_count}")
                            logger.info(f"  - Citations found: {result.citation_count}")
                            logger.info(f"  - Extraction time: {result.extraction_time_ms:.2f}ms")
                        else:
                            logger.error(f"✗ Test failed: {result.test_id}")
                            logger.error(f"  - Error: {result.error}")
                        
                        # Save intermediate results
                        self._save_intermediate_results(config_id, result)
                
                # Stop metrics collection
                await metrics_collector.stop()
                
                # Export metrics
                metrics_collector.export_json(f"metrics_{config_id}.json")
                
                logger.info(f"Completed testing for {config_id}")
                
            except Exception as e:
                logger.error(f"Unexpected error testing {config_id}: {e}")
                self.config_failures[config_id] = str(e)
            
            finally:
                # Always try to stop the service before next config
                await self.service_manager.stop_service()
                await asyncio.sleep(5)  # Brief pause between configs
        
        # Generate final report
        self._generate_final_report()
    
    def _save_intermediate_results(self, config_id: str, result: ExtractionResult):
        """Save intermediate results for a test"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{config_id}_{result.document.replace('.', '_')}_{result.strategy}_{timestamp}.json"
            filepath = self.output_dir / "intermediate" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(asdict(result), f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving intermediate results: {e}")
    
    def _generate_final_report(self):
        """Generate comprehensive final report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare summary statistics
        summary = {
            "test_metadata": {
                "timestamp": timestamp,
                "total_configurations": len(self.vllm_configs),
                "configurations_tested": len(set(r.config_id for r in self.results)),
                "total_tests": len(self.results),
                "successful_tests": sum(1 for r in self.results if r.success),
                "failed_tests": sum(1 for r in self.results if not r.success),
                "documents_tested": self.test_documents,
                "strategies_tested": self.test_strategies
            },
            "configuration_results": {},
            "entity_statistics": {},
            "performance_metrics": {},
            "failures": self.config_failures,
            "detailed_results": [asdict(r) for r in self.results]
        }
        
        # Analyze results by configuration
        for config_id in self.vllm_configs:
            config_results = [r for r in self.results if r.config_id == config_id]
            if config_results:
                summary["configuration_results"][config_id] = {
                    "total_tests": len(config_results),
                    "successful": sum(1 for r in config_results if r.success),
                    "failed": sum(1 for r in config_results if not r.success),
                    "avg_extraction_time_ms": sum(r.extraction_time_ms for r in config_results) / len(config_results),
                    "total_entities": sum(r.entity_count for r in config_results),
                    "total_citations": sum(r.citation_count for r in config_results),
                    "entity_types": self._get_entity_type_distribution(config_results)
                }
        
        # Calculate entity statistics
        all_entities = []
        for result in self.results:
            if result.success:
                all_entities.extend(result.entities)
        
        if all_entities:
            entity_types = {}
            for entity in all_entities:
                entity_type = entity.get("type", "UNKNOWN")
                if entity_type not in entity_types:
                    entity_types[entity_type] = {
                        "count": 0,
                        "samples": [],
                        "avg_confidence": 0,
                        "confidences": []
                    }
                entity_types[entity_type]["count"] += 1
                entity_types[entity_type]["confidences"].append(entity.get("confidence", 0))
                if len(entity_types[entity_type]["samples"]) < 5:
                    entity_types[entity_type]["samples"].append(entity.get("value", ""))
            
            # Calculate average confidences
            for entity_type in entity_types:
                confidences = entity_types[entity_type]["confidences"]
                if confidences:
                    entity_types[entity_type]["avg_confidence"] = sum(confidences) / len(confidences)
                del entity_types[entity_type]["confidences"]  # Remove raw data from summary
            
            summary["entity_statistics"] = entity_types
        
        # Calculate performance metrics
        if self.results:
            successful_results = [r for r in self.results if r.success]
            if successful_results:
                summary["performance_metrics"] = {
                    "avg_extraction_time_ms": sum(r.extraction_time_ms for r in successful_results) / len(successful_results),
                    "min_extraction_time_ms": min(r.extraction_time_ms for r in successful_results),
                    "max_extraction_time_ms": max(r.extraction_time_ms for r in successful_results),
                    "avg_entities_per_doc": sum(r.entity_count for r in successful_results) / len(successful_results),
                    "avg_citations_per_doc": sum(r.citation_count for r in successful_results) / len(successful_results)
                }
        
        # Save comprehensive report
        report_path = self.output_dir / f"vllm_optimization_test_report_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info("TEST ORCHESTRATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total configurations tested: {summary['test_metadata']['configurations_tested']}")
        logger.info(f"Total tests run: {summary['test_metadata']['total_tests']}")
        logger.info(f"Successful tests: {summary['test_metadata']['successful_tests']}")
        logger.info(f"Failed tests: {summary['test_metadata']['failed_tests']}")
        logger.info(f"Report saved to: {report_path}")
        
        # Print top performing configurations
        if summary["configuration_results"]:
            sorted_configs = sorted(
                summary["configuration_results"].items(),
                key=lambda x: x[1]["avg_extraction_time_ms"]
            )
            logger.info("\nTop 5 Fastest Configurations:")
            for config_id, stats in sorted_configs[:5]:
                logger.info(f"  {config_id}: {stats['avg_extraction_time_ms']:.2f}ms avg")
    
    def _get_entity_type_distribution(self, results: List[ExtractionResult]) -> Dict[str, int]:
        """Get entity type distribution from results"""
        distribution = {}
        for result in results:
            if result.success:
                for entity in result.entities:
                    entity_type = entity.get("type", "UNKNOWN")
                    distribution[entity_type] = distribution.get(entity_type, 0) + 1
        return distribution


async def main():
    """Main entry point"""
    # Handle command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="vLLM Optimization Test Orchestrator")
    parser.add_argument(
        "--configs",
        nargs="+",
        help="Specific configurations to test (e.g., dual_gpu_config_021 dual_gpu_config_022)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/srv/luris/be/entity-extraction-service/tests/results",
        help="Output directory for results"
    )
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = TestOrchestrator(output_dir=Path(args.output_dir))
    
    # Set up signal handling for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, cleaning up...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run tests
        await orchestrator.run_tests(specific_configs=args.configs)
    except Exception as e:
        logger.error(f"Fatal error in test orchestration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure entity extraction and document upload services are running
    logger.info("Starting vLLM Optimization Test Orchestrator")
    logger.info("Ensuring required services are running...")
    
    # Check service health
    import requests
    try:
        # Check document upload service
        upload_health = requests.get("http://localhost:8008/api/v1/health", timeout=5)
        if upload_health.status_code != 200:
            logger.error("Document Upload Service is not healthy!")
            logger.error("Please start it with: sudo systemctl start luris-document-upload")
            sys.exit(1)
        
        # Check entity extraction service
        extraction_health = requests.get("http://localhost:8007/api/v1/health", timeout=5)
        if extraction_health.status_code != 200:
            logger.error("Entity Extraction Service is not healthy!")
            logger.error("Please start it with: sudo systemctl start luris-entity-extraction")
            sys.exit(1)
        
        logger.info("All required services are healthy")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to check service health: {e}")
        logger.error("Please ensure the following services are running:")
        logger.error("  - Document Upload Service (port 8008)")
        logger.error("  - Entity Extraction Service (port 8007)")
        sys.exit(1)
    
    # Run the async main function
    asyncio.run(main())