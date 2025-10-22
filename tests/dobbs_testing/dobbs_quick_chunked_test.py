#!/usr/bin/env python3
"""
Quick chunked test for Dobbs.pdf to validate SmartChunker integration.
Tests only first few chunks to verify the approach works.
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
from collections import Counter
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
TEST_TIMEOUT = 30  # seconds per chunk
MAX_CHUNKS_TO_TEST = 5  # Only test first 5 chunks for quick validation

class QuickChunkedTest:
    def __init__(self):
        self.smart_chunker = SmartChunker()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {}
        
    async def upload_document(self) -> Tuple[str, str]:
        """Upload Dobbs.pdf and get document ID and markdown content."""
        logger.info("Uploading Dobbs.pdf...")
        
        async with aiohttp.ClientSession() as session:
            with open(DOBBS_PDF, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='dobbs.pdf')
                data.add_field('client_id', 'test_quick_chunked')
                data.add_field('case_id', f'dobbs_quick_chunked_{self.timestamp}')
                
                async with session.post(
                    f"{UPLOAD_SERVICE_URL}/upload",
                    data=data,
                    timeout=ClientTimeout(total=60)
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        raise Exception(f"Upload failed: {result}")
                    
                    return result['document_id'], result['markdown_content']
    
    async def test_extraction_mode(
        self,
        document_id: str,
        content: str,
        mode: str,
        strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test extraction with chunking."""
        
        # For regex, use full document
        if mode == "regex":
            logger.info(f"Testing {mode} on full document (no chunking)...")
            return await self._test_full_document(document_id, content, mode)
        
        # For AI modes, use smart chunking
        logger.info(f"Testing {mode}/{strategy} with smart chunking...")
        
        # Create chunks
        chunks = self.smart_chunker.chunk_document(
            text=content,
            strategy=ChunkingStrategy.LEGAL_AWARE,
            document_type=DocumentType.OPINION
        )
        
        logger.info(f"Created {len(chunks)} chunks, testing first {MAX_CHUNKS_TO_TEST}")
        
        # Test only first few chunks
        test_chunks = chunks[:MAX_CHUNKS_TO_TEST]
        all_entities = []
        total_time = 0
        
        async with aiohttp.ClientSession() as session:
            for i, chunk in enumerate(test_chunks, 1):
                logger.info(f"  Processing chunk {i}/{len(test_chunks)} ({chunk.length} chars)")
                
                payload = {
                    "document_id": f"{document_id}_chunk_{i}",
                    "content": chunk.text,
                    "extraction_mode": mode,
                    "confidence_threshold": 0.6
                }
                
                if strategy:
                    payload["prompt_strategy"] = strategy
                
                start_time = time.time()
                
                try:
                    async with session.post(
                        f"{EXTRACT_SERVICE_URL}/extract",
                        json=payload,
                        timeout=ClientTimeout(total=TEST_TIMEOUT)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            entities = result.get("entities", [])
                            all_entities.extend(entities)
                            elapsed = time.time() - start_time
                            total_time += elapsed
                            logger.info(f"    ✓ Found {len(entities)} entities in {elapsed:.2f}s")
                        else:
                            error = await response.text()
                            logger.error(f"    ✗ Failed: {error}")
                except asyncio.TimeoutError:
                    logger.error(f"    ✗ Timeout after {TEST_TIMEOUT}s")
                except Exception as e:
                    logger.error(f"    ✗ Error: {e}")
        
        # Aggregate results
        entity_types = Counter(e.get("entity_type") for e in all_entities)
        
        return {
            "mode": mode,
            "strategy": strategy or "default",
            "total_entities": len(all_entities),
            "unique_types": len(entity_types),
            "entity_types": dict(entity_types.most_common(10)),
            "chunks_tested": len(test_chunks),
            "total_chunks": len(chunks),
            "total_time": total_time,
            "avg_time_per_chunk": total_time / len(test_chunks) if test_chunks else 0
        }
    
    async def _test_full_document(
        self,
        document_id: str,
        content: str,
        mode: str
    ) -> Dict[str, Any]:
        """Test on full document without chunking."""
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "document_id": document_id,
                "content": content,
                "extraction_mode": mode,
                "confidence_threshold": 0.6
            }
            
            start_time = time.time()
            
            try:
                async with session.post(
                    f"{EXTRACT_SERVICE_URL}/extract",
                    json=payload,
                    timeout=ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        entities = result.get("entities", [])
                        entity_types = Counter(e.get("entity_type") for e in entities)
                        
                        return {
                            "mode": mode,
                            "strategy": "none",
                            "total_entities": len(entities),
                            "unique_types": len(entity_types),
                            "entity_types": dict(entity_types.most_common(10)),
                            "chunks_tested": 0,
                            "total_chunks": 0,
                            "total_time": time.time() - start_time
                        }
                    else:
                        error = await response.text()
                        return {"mode": mode, "error": error}
            except Exception as e:
                return {"mode": mode, "error": str(e)}
    
    async def run_quick_test(self):
        """Run quick validation test."""
        
        print("\n" + "="*80)
        print("QUICK SMART CHUNKING VALIDATION TEST")
        print("="*80)
        print(f"Testing first {MAX_CHUNKS_TO_TEST} chunks only for quick validation")
        print("-"*80)
        
        # Upload document
        document_id, content = await self.upload_document()
        logger.info(f"Document uploaded: {document_id}")
        logger.info(f"Content length: {len(content):,} characters")
        
        # Analyze chunking
        chunks = self.smart_chunker.chunk_document(
            text=content,
            strategy=ChunkingStrategy.LEGAL_AWARE,
            document_type=DocumentType.OPINION
        )
        
        print(f"\nChunking Analysis:")
        print(f"  Total chunks created: {len(chunks)}")
        print(f"  Average chunk size: {sum(c.length for c in chunks) / len(chunks):.0f} chars")
        print(f"  Min/Max size: {min(c.length for c in chunks)}/{max(c.length for c in chunks)} chars")
        print(f"  Testing first {MAX_CHUNKS_TO_TEST} chunks")
        
        # Test configurations
        test_configs = [
            ("regex", None),  # Full document
            ("ai_enhanced", "unified"),  # Chunked
            ("hybrid", "unified"),  # Chunked
        ]
        
        print("\n" + "-"*80)
        print("Test Results:")
        print("-"*80)
        
        for mode, strategy in test_configs:
            print(f"\nTesting {mode}/{strategy or 'none'}...")
            result = await self.test_extraction_mode(document_id, content, mode, strategy)
            
            if "error" in result:
                print(f"  ✗ Error: {result['error']}")
            else:
                print(f"  ✓ Entities: {result['total_entities']}")
                print(f"  ✓ Types: {result['unique_types']}")
                print(f"  ✓ Time: {result['total_time']:.2f}s")
                if result['chunks_tested'] > 0:
                    print(f"  ✓ Chunks: {result['chunks_tested']}/{result['total_chunks']}")
                    print(f"  ✓ Avg/chunk: {result['avg_time_per_chunk']:.2f}s")
                
                if result['entity_types']:
                    top_types = [str(k) for k in list(result['entity_types'].keys())[:5] if k is not None]
                    if top_types:
                        print(f"  Top types: {', '.join(top_types)}")
            
            self.results[f"{mode}_{strategy or 'none'}"] = result
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Save results
        output_file = Path(f"/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results/quick_chunked_{self.timestamp}.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("\n" + "="*80)
        print("VALIDATION COMPLETE")
        print(f"Results saved to: {output_file}")
        print("="*80)


async def main():
    """Run quick validation test."""
    
    # Set environment variables
    os.environ["CHUNKING_MAX_SIZE"] = "3000"
    os.environ["CHUNKING_OVERLAP"] = "300"
    os.environ["CHUNKING_MIN_SIZE"] = "500"
    os.environ["CHUNKING_ENABLE_SMART"] = "true"
    
    test = QuickChunkedTest()
    await test.run_quick_test()


if __name__ == "__main__":
    asyncio.run(main())