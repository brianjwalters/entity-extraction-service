#!/usr/bin/env python3
"""
Simple comprehensive test for Dobbs.pdf entity extraction using direct HTTP requests.
Tests all extraction modes and strategies.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from collections import defaultdict, Counter
from aiohttp import ClientTimeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service URLs
UPLOAD_SERVICE_URL = "http://localhost:8008/api/v1"
EXTRACT_SERVICE_URL = "http://localhost:8007/api/v1"

# Test configuration
DOBBS_PDF = "/srv/luris/be/tests/docs/dobbs.pdf"
TEST_TIMEOUT = 120  # seconds per extraction

# Extraction modes and strategies
EXTRACTION_MODES = ["regex", "spacy", "ai_enhanced", "hybrid"]
PROMPT_STRATEGIES = [
    "base_extraction",
    "enhanced_extraction", 
    "structured_extraction",
    "graph_aware_extraction",
    "legal_specialized_extraction"
]

class DobbsTestRunner:
    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")
        self.output_dir.mkdir(exist_ok=True)
        
    async def upload_document(self, session: aiohttp.ClientSession) -> tuple[str, str]:
        """Upload Dobbs.pdf and get document ID and markdown content."""
        logger.info("Uploading Dobbs.pdf...")
        
        with open(DOBBS_PDF, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='dobbs.pdf')
            data.add_field('client_id', 'test_client_dobbs')
            data.add_field('case_id', f'dobbs_test_{self.timestamp}')
            
            async with session.post(
                f"{UPLOAD_SERVICE_URL}/upload",
                data=data,
                timeout=ClientTimeout(total=120)
            ) as response:
                result = await response.json()
                
                if response.status != 200:
                    raise Exception(f"Upload failed: {result}")
                
                logger.info(f"Document uploaded: {result['document_id']}")
                return result['document_id'], result['markdown_content']
    
    async def test_extraction_mode(
        self, 
        session: aiohttp.ClientSession,
        document_id: str,
        content: str,
        mode: str,
        strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test a single extraction mode/strategy combination."""
        
        test_key = f"{mode}_{strategy}" if strategy else mode
        logger.info(f"Testing: {test_key}")
        
        payload = {
            "document_id": document_id,
            "content": content,
            "extraction_mode": mode,
            "confidence_threshold": 0.7
        }
        
        if strategy and mode == "ai_enhanced":
            payload["prompt_strategy"] = strategy
            
        start_time = time.time()
        
        try:
            async with session.post(
                f"{EXTRACT_SERVICE_URL}/extract",
                json=payload,
                timeout=ClientTimeout(total=TEST_TIMEOUT)
            ) as response:
                result = await response.json()
                elapsed = time.time() - start_time
                
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": result.get("detail", "Unknown error"),
                        "elapsed_time": elapsed
                    }
                
                # Count entities by type
                entity_types = Counter()
                citation_types = Counter()
                
                for entity in result.get("entities", []):
                    entity_types[entity.get("entity_type", "UNKNOWN")] += 1
                    
                for citation in result.get("citations", []):
                    citation_types[citation.get("citation_type", "UNKNOWN")] += 1
                
                return {
                    "status": "success",
                    "elapsed_time": elapsed,
                    "total_entities": len(result.get("entities", [])),
                    "total_citations": len(result.get("citations", [])),
                    "unique_entity_types": len(entity_types),
                    "unique_citation_types": len(citation_types),
                    "entity_types": dict(entity_types),
                    "citation_types": dict(citation_types),
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "sample_entities": result.get("entities", [])[:5]  # First 5 for inspection
                }
                
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Timeout for {test_key} after {elapsed:.2f}s")
            return {
                "status": "timeout",
                "elapsed_time": elapsed,
                "error": f"Extraction timed out after {TEST_TIMEOUT}s"
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error for {test_key}: {str(e)}")
            return {
                "status": "error",
                "elapsed_time": elapsed,
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all extraction tests on Dobbs.pdf."""
        
        timeout = ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Upload document
            try:
                document_id, markdown_content = await self.upload_document(session)
                
                # Store document info
                self.results["document"] = {
                    "document_id": document_id,
                    "content_length": len(markdown_content),
                    "timestamp": self.timestamp
                }
                
                logger.info(f"Document content length: {len(markdown_content)} chars")
                
            except Exception as e:
                logger.error(f"Failed to upload document: {e}")
                return
            
            # Test each mode
            self.results["extractions"] = {}
            
            for mode in EXTRACTION_MODES:
                if mode == "ai_enhanced":
                    # Test each prompt strategy for AI mode
                    for strategy in PROMPT_STRATEGIES:
                        test_key = f"{mode}_{strategy}"
                        result = await self.test_extraction_mode(
                            session, document_id, markdown_content, mode, strategy
                        )
                        self.results["extractions"][test_key] = result
                        
                        # Log summary
                        if result["status"] == "success":
                            logger.info(
                                f"✓ {test_key}: {result['total_entities']} entities, "
                                f"{result['total_citations']} citations, "
                                f"{result['elapsed_time']:.2f}s"
                            )
                        else:
                            logger.error(
                                f"✗ {test_key}: {result['status']} - {result.get('error', 'Unknown')}"
                            )
                else:
                    # Test other modes without strategies
                    result = await self.test_extraction_mode(
                        session, document_id, markdown_content, mode
                    )
                    self.results["extractions"][mode] = result
                    
                    # Log summary
                    if result["status"] == "success":
                        logger.info(
                            f"✓ {mode}: {result['total_entities']} entities, "
                            f"{result['total_citations']} citations, "
                            f"{result['elapsed_time']:.2f}s"
                        )
                    else:
                        logger.error(
                            f"✗ {mode}: {result['status']} - {result.get('error', 'Unknown')}"
                        )
    
    def save_results(self):
        """Save test results to JSON file."""
        output_file = self.output_dir / f"dobbs_test_{self.timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        logger.info(f"Results saved to: {output_file}")
        return output_file
    
    def print_summary(self):
        """Print a summary of test results."""
        print("\n" + "="*80)
        print("DOBBS.PDF EXTRACTION TEST SUMMARY")
        print("="*80)
        
        if "extractions" not in self.results:
            print("No extraction results available")
            return
            
        # Summary statistics
        successful = 0
        failed = 0
        timeouts = 0
        total_entities = 0
        total_citations = 0
        
        print("\nExtraction Results:")
        print("-"*80)
        
        for test_key, result in self.results["extractions"].items():
            status = result["status"]
            elapsed = result["elapsed_time"]
            
            if status == "success":
                successful += 1
                entities = result["total_entities"]
                citations = result["total_citations"]
                total_entities += entities
                total_citations += citations
                
                print(f"✓ {test_key:40} | {entities:5} entities | {citations:5} citations | {elapsed:6.2f}s")
            elif status == "timeout":
                timeouts += 1
                print(f"⏱ {test_key:40} | TIMEOUT after {elapsed:6.2f}s")
            else:
                failed += 1
                error = result.get("error", "Unknown error")[:40]
                print(f"✗ {test_key:40} | ERROR: {error}")
        
        print("\n" + "="*80)
        print(f"Summary: {successful} successful, {failed} failed, {timeouts} timeouts")
        print(f"Total entities found: {total_entities}")
        print(f"Total citations found: {total_citations}")
        print("="*80)

async def main():
    """Main test execution."""
    runner = DobbsTestRunner()
    
    try:
        await runner.run_all_tests()
        runner.save_results()
        runner.print_summary()
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())