#!/usr/bin/env python3
"""
Smart chunked test for Dobbs.pdf entity extraction using legal-aware chunking.
Processes document with SmartChunker to preserve legal boundaries.
"""

import asyncio
import aiohttp
import json
import time
import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from collections import defaultdict, Counter
from aiohttp import ClientTimeout

# Add parent directory to path for imports

from src.core.smart_chunker import SmartChunker, ChunkingStrategy, DocumentType
from src.core.config import get_config

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
TEST_TIMEOUT = 60  # seconds per chunk

# Extraction modes to test
EXTRACTION_MODES = ["regex", "ai_enhanced", "hybrid"]
AI_STRATEGIES = ["unified", "multipass", "ai_enhanced"]

class DobbsChunkedTestRunner:
    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize SmartChunker
        self.smart_chunker = SmartChunker()
        self.chunking_config = self._load_chunking_config()
        
    def _load_chunking_config(self) -> Dict:
        """Load chunking configuration from YAML."""
        config_path = Path(__file__).parent / "chunking_config.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded chunking config from {config_path}")
                return config.get("chunking", {})
        return {}
        
    async def upload_document(self, session: aiohttp.ClientSession) -> tuple[str, str]:
        """Upload Dobbs.pdf and get document ID and markdown content."""
        logger.info("Uploading Dobbs.pdf...")
        
        with open(DOBBS_PDF, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename='dobbs.pdf')
            data.add_field('client_id', 'test_client_dobbs')
            data.add_field('case_id', f'dobbs_chunked_test_{self.timestamp}')
            
            async with session.post(
                f"{UPLOAD_SERVICE_URL}/upload",
                data=data,
                timeout=ClientTimeout(total=120)
            ) as response:
                result = await response.json()
                
                if response.status != 200:
                    raise Exception(f"Upload failed: {result}")
                
                logger.info(f"Document uploaded: {result['document_id']}")
                logger.info(f"Content length: {len(result['markdown_content'])} chars")
                return result['document_id'], result['markdown_content']
    
    async def test_extraction_full(
        self, 
        session: aiohttp.ClientSession,
        document_id: str,
        content: str,
        mode: str
    ) -> Dict[str, Any]:
        """Test extraction on full document (for non-AI modes)."""
        
        logger.info(f"Testing {mode} on full document...")
        
        payload = {
            "document_id": document_id,
            "content": content,
            "extraction_mode": mode,
            "confidence_threshold": 0.7
        }
            
        start_time = time.time()
        
        try:
            async with session.post(
                f"{EXTRACT_SERVICE_URL}/extract",
                json=payload,
                timeout=ClientTimeout(total=180)  # 3 minutes for full doc
            ) as response:
                result = await response.json()
                elapsed = time.time() - start_time
                
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": result.get("detail", "Unknown error"),
                        "elapsed_time": elapsed
                    }
                
                # Count entities
                entity_types = Counter()
                for entity in result.get("entities", []):
                    entity_types[entity.get("entity_type", "UNKNOWN")] += 1
                
                return {
                    "status": "success",
                    "elapsed_time": elapsed,
                    "total_entities": len(result.get("entities", [])),
                    "unique_entity_types": len(entity_types),
                    "entity_types": dict(entity_types),
                    "top_entities": dict(entity_types.most_common(10)),
                    "processing_time_ms": result.get("processing_time_ms", 0)
                }
                
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"Timeout for {mode} after {elapsed:.2f}s")
            return {
                "status": "timeout",
                "elapsed_time": elapsed
            }
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error for {mode}: {str(e)}")
            return {
                "status": "error",
                "elapsed_time": elapsed,
                "error": str(e)
            }
    
    async def test_extraction_chunked(
        self, 
        session: aiohttp.ClientSession,
        document_id: str,
        content: str,
        mode: str,
        strategy: str = None
    ) -> Dict[str, Any]:
        """Test AI extraction using SmartChunker to avoid timeouts."""
        
        test_key = f"{mode}_{strategy}" if strategy else mode
        logger.info(f"Testing {test_key} with smart chunking...")
        
        # Use SmartChunker to create legal-aware chunks
        chunks = self.smart_chunker.chunk_document(
            text=content,
            strategy=ChunkingStrategy.LEGAL_AWARE,
            document_type=DocumentType.OPINION
        )
        
        logger.info(f"SmartChunker created {len(chunks)} chunks")
        logger.info(f"  Average chunk size: {sum(c.length for c in chunks) / len(chunks):.0f} chars")
        logger.info(f"  Min/Max: {min(c.length for c in chunks)}/{max(c.length for c in chunks)} chars")
        
        all_entities = []
        entity_map = {}  # For deduplication
        total_elapsed = 0
        chunk_results = []
        successful_chunks = 0
        
        # Process chunks with controlled concurrency
        batch_size = 5
        for batch_start in range(0, len(chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch = chunks[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size} "
                       f"(chunks {batch_start+1}-{batch_end})")
            
            batch_tasks = []
            for chunk in batch:
                payload = {
                    "document_id": f"{document_id}_chunk_{chunk.chunk_index}",
                    "content": chunk.text,
                    "extraction_mode": mode,
                    "confidence_threshold": 0.6
                }
                
                if strategy and mode in ["ai_enhanced", "hybrid"]:
                    payload["prompt_strategy"] = strategy
                
                batch_tasks.append(self._extract_chunk(session, payload, chunk.chunk_index))
            
            # Process batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for chunk_idx, result in enumerate(batch_results):
                chunk_num = batch_start + chunk_idx + 1
                
                if isinstance(result, Exception):
                    logger.error(f"  Chunk {chunk_num} error: {result}")
                    chunk_results.append({
                        "chunk": chunk_num,
                        "status": "error",
                        "error": str(result)
                    })
                elif result["status"] == "success":
                    entities = result["entities"]
                    elapsed = result["elapsed"]
                    total_elapsed += elapsed
                    
                    # Deduplicate entities
                    for entity in entities:
                        entity_key = f"{entity.get('entity_type')}:{entity.get('entity_text', '').lower().strip()}"
                        if entity_key not in entity_map or entity.get('confidence', 0) > entity_map[entity_key].get('confidence', 0):
                            entity_map[entity_key] = entity
                    
                    chunk_results.append({
                        "chunk": chunk_num,
                        "status": "success",
                        "entities": len(entities),
                        "time": elapsed
                    })
                    successful_chunks += 1
                    logger.info(f"  ✓ Chunk {chunk_num}: {len(entities)} entities in {elapsed:.2f}s")
                else:
                    chunk_results.append({
                        "chunk": chunk_num,
                        "status": result["status"],
                        "error": result.get("error")
                    })
                    logger.error(f"  ✗ Chunk {chunk_num}: {result.get('error', 'Failed')}")
            
            # Small delay between batches to avoid overloading vLLM
            if batch_end < len(chunks):
                await asyncio.sleep(1)
        
        # Get unique entities from map
        all_entities = list(entity_map.values())
        
        # Aggregate results
        entity_types = Counter()
        for entity in all_entities:
            entity_types[entity.get("entity_type", "UNKNOWN")] += 1
        
        return {
            "status": "success" if successful_chunks > 0 else "failed",
            "elapsed_time": total_elapsed,
            "chunks_total": len(chunks),
            "chunks_processed": successful_chunks,
            "chunks_failed": len(chunks) - successful_chunks,
            "total_entities": len(all_entities),
            "unique_entity_types": len(entity_types),
            "entity_types": dict(entity_types),
            "top_entities": dict(entity_types.most_common(10)),
            "chunk_results": chunk_results[:20],  # First 20 for summary
            "chunking_method": "SmartChunker with legal_aware strategy"
        }
    
    async def _extract_chunk(self, session: aiohttp.ClientSession, payload: Dict, chunk_index: int) -> Dict:
        """Extract entities from a single chunk."""
        start_time = time.time()
        
        try:
            async with session.post(
                f"{EXTRACT_SERVICE_URL}/extract",
                json=payload,
                timeout=ClientTimeout(total=TEST_TIMEOUT)
            ) as response:
                result = await response.json()
                elapsed = time.time() - start_time
                
                if response.status == 200:
                    return {
                        "status": "success",
                        "entities": result.get("entities", []),
                        "elapsed": elapsed
                    }
                else:
                    return {
                        "status": "error",
                        "error": result.get("detail", "Unknown error"),
                        "elapsed": elapsed
                    }
                    
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "error": f"Timeout after {TEST_TIMEOUT}s",
                "elapsed": time.time() - start_time
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "elapsed": time.time() - start_time
            }
    
    async def run_tests(self):
        """Run extraction tests on Dobbs.pdf."""
        
        timeout = ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Upload document
            try:
                document_id, markdown_content = await self.upload_document(session)
                
                self.results["document"] = {
                    "document_id": document_id,
                    "content_length": len(markdown_content),
                    "timestamp": self.timestamp
                }
                
                # Analyze chunking
                logger.info("\n=== Analyzing Document Chunking ===")
                chunks = self.smart_chunker.chunk_document(
                    text=markdown_content,
                    strategy=ChunkingStrategy.LEGAL_AWARE,
                    document_type=DocumentType.OPINION
                )
                
                self.results["chunking_analysis"] = {
                    "total_chunks": len(chunks),
                    "average_chunk_size": sum(c.length for c in chunks) / len(chunks),
                    "min_chunk_size": min(c.length for c in chunks),
                    "max_chunk_size": max(c.length for c in chunks)
                }
                
                logger.info(f"Document will be processed in {len(chunks)} chunks")
                logger.info(f"Average chunk size: {self.results['chunking_analysis']['average_chunk_size']:.0f} chars")
                
            except Exception as e:
                logger.error(f"Failed to upload document: {e}")
                return
            
            # Test results
            self.results["extractions"] = {}
            
            # Test regex on full document (no chunking needed)
            logger.info("\n=== Testing Regex Mode (Full Document - No Chunking) ===")
            result = await self.test_extraction_full(session, document_id, markdown_content, "regex")
            self.results["extractions"]["regex"] = result
            
            # Test AI Enhanced with different strategies using chunking
            for strategy in AI_STRATEGIES:
                logger.info(f"\n=== Testing AI Enhanced Mode - {strategy} (Smart Chunked) ===")
                result = await self.test_extraction_chunked(
                    session, document_id, markdown_content, "ai_enhanced", strategy
                )
                self.results["extractions"][f"ai_enhanced_{strategy}"] = result
                
                # Small delay between strategies
                await asyncio.sleep(2)
            
            # Test hybrid modes with chunking
            for strategy in ["unified", "multipass"]:
                logger.info(f"\n=== Testing Hybrid Mode - {strategy} (Smart Chunked) ===")
                result = await self.test_extraction_chunked(
                    session, document_id, markdown_content, "hybrid", strategy
                )
                self.results["extractions"][f"hybrid_{strategy}"] = result
                
                # Small delay between strategies
                await asyncio.sleep(2)
    
    def save_results(self):
        """Save test results to JSON file."""
        output_file = self.output_dir / f"dobbs_chunked_test_{self.timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        logger.info(f"\nResults saved to: {output_file}")
        return output_file
    
    def print_summary(self):
        """Print a summary of test results."""
        print("\n" + "="*80)
        print("DOBBS.PDF SMART CHUNKED EXTRACTION TEST SUMMARY")
        print("="*80)
        
        if "extractions" not in self.results:
            print("No extraction results available")
            return
        
        # Show chunking analysis
        if "chunking_analysis" in self.results:
            analysis = self.results["chunking_analysis"]
            print(f"\nDocument Chunking Analysis:")
            print(f"  Original size: {self.results['document']['content_length']:,} characters")
            print(f"  Total chunks: {analysis['total_chunks']}")
            print(f"  Average chunk: {analysis['average_chunk_size']:.0f} chars")
            print(f"  Min/Max size: {analysis['min_chunk_size']}/{analysis['max_chunk_size']} chars")
        
        print("\n" + "-"*80)
        print("Extraction Results:")
        print("-"*80)
        
        # Summarize results
        summary_data = []
        for test_key, result in self.results["extractions"].items():
            status = result["status"]
            elapsed = result.get("elapsed_time", 0)
            
            if status in ["success", "partial", "failed"]:
                row = {
                    "Mode": test_key,
                    "Status": status,
                    "Time": f"{elapsed:.1f}s",
                    "Entities": result.get("total_entities", 0),
                    "Types": result.get("unique_entity_types", 0),
                    "Method": "Chunked" if result.get("chunks_total") else "Full"
                }
                
                if result.get("chunks_total"):
                    row["Chunks"] = f"{result.get('chunks_processed', 0)}/{result.get('chunks_total', 0)}"
                
                summary_data.append(row)
        
        # Print table
        if summary_data:
            # Print header
            print(f"\n{'Mode':<25} {'Status':<10} {'Time':<10} {'Entities':<10} {'Types':<8} {'Method':<10} {'Chunks':<12}")
            print("-"*95)
            
            for row in summary_data:
                chunks = row.get('Chunks', '-')
                print(f"{row['Mode']:<25} {row['Status']:<10} {row['Time']:<10} "
                      f"{row['Entities']:<10} {row['Types']:<8} {row['Method']:<10} {chunks:<12}")
        
        # Show detailed results for successful tests
        print("\n" + "-"*80)
        print("Top Entity Types Found:")
        print("-"*80)
        
        for test_key, result in self.results["extractions"].items():
            if result.get("status") in ["success", "partial"] and result.get("top_entities"):
                print(f"\n{test_key}:")
                for i, (etype, count) in enumerate(result["top_entities"].items(), 1):
                    if i <= 5:  # Show top 5
                        print(f"  {i}. {etype}: {count}")
        
        # Show chunking effectiveness
        if any(r.get("chunks_total") for r in self.results["extractions"].values()):
            print("\n" + "-"*80)
            print("Chunking Effectiveness:")
            print("-"*80)
            
            for test_key, result in self.results["extractions"].items():
                if result.get("chunks_total"):
                    success_rate = (result.get("chunks_processed", 0) / result.get("chunks_total", 1)) * 100
                    avg_time = result.get("elapsed_time", 0) / max(result.get("chunks_processed", 1), 1)
                    print(f"\n{test_key}:")
                    print(f"  Success rate: {success_rate:.1f}%")
                    print(f"  Avg time/chunk: {avg_time:.2f}s")
                    print(f"  Chunking method: {result.get('chunking_method', 'Unknown')}")
        
        print("\n" + "="*80)

async def main():
    """Main test execution."""
    
    # Set environment variables for optimal chunking
    os.environ["CHUNKING_MAX_SIZE"] = "3000"
    os.environ["CHUNKING_OVERLAP"] = "300"
    os.environ["CHUNKING_MIN_SIZE"] = "500"
    os.environ["CHUNKING_ENABLE_SMART"] = "true"
    os.environ["CHUNKING_BATCH_SIZE"] = "5"
    
    logger.info("="*80)
    logger.info("SMART CHUNKED EXTRACTION TEST FOR DOBBS.PDF")
    logger.info("="*80)
    logger.info("\nEnvironment Configuration:")
    logger.info(f"  CHUNKING_MAX_SIZE: {os.environ['CHUNKING_MAX_SIZE']} chars")
    logger.info(f"  CHUNKING_OVERLAP: {os.environ['CHUNKING_OVERLAP']} chars")
    logger.info(f"  CHUNKING_MIN_SIZE: {os.environ['CHUNKING_MIN_SIZE']} chars")
    logger.info(f"  CHUNKING_ENABLE_SMART: {os.environ['CHUNKING_ENABLE_SMART']}")
    logger.info(f"  CHUNKING_BATCH_SIZE: {os.environ['CHUNKING_BATCH_SIZE']} chunks")
    
    runner = DobbsChunkedTestRunner()
    
    try:
        await runner.run_tests()
        runner.save_results()
        runner.print_summary()
        
        logger.info("\n✅ Test completed successfully!")
        logger.info("Check the results directory for detailed JSON output.")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())