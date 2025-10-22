#!/usr/bin/env python3
"""
Test script for unified extraction with multipass fallback.

This script tests the following scenarios:
1. Successful unified extraction
2. Unified extraction failure with multipass fallback
3. Entity deduplication and merging
4. Default strategy selection
"""

import asyncio
import json
import aiohttp
from typing import Dict, Any
import time
from datetime import datetime


class UnifiedExtractionTester:
    """Test unified extraction with fallback mechanism."""
    
    def __init__(self, base_url: str = "http://localhost:8007"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        
    async def test_health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "healthy"
                    return False
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    async def test_unified_extraction(self, test_content: str, document_id: str) -> Dict[str, Any]:
        """Test unified extraction strategy."""
        request_data = {
            "document_id": document_id,
            "content": test_content,
            "extraction_mode": "regex",  # Will be redirected to unified
            "confidence_threshold": 0.6,
            "include_context": True,
            "context_window": 150,
            "enable_relationships": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/extract",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        print(f"✅ Unified extraction successful for {document_id}")
                        return {
                            "success": True,
                            "status": response.status,
                            "data": result
                        }
                    else:
                        print(f"⚠️ Extraction returned status {response.status}")
                        return {
                            "success": False,
                            "status": response.status,
                            "error": result
                        }
                        
        except asyncio.TimeoutError:
            print(f"⏱️ Request timed out for {document_id}")
            return {
                "success": False,
                "error": "Request timed out"
            }
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_explicit_strategy(self, test_content: str, strategy: str) -> Dict[str, Any]:
        """Test explicit strategy selection."""
        request_data = {
            "document_id": f"test_{strategy}_{int(time.time())}",
            "content": test_content,
            "extraction_mode": "ai_enhanced",
            "extraction_strategy": strategy,
            "confidence_threshold": 0.5
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/extract",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    result = await response.json()
                    
                    return {
                        "success": response.status == 200,
                        "status": response.status,
                        "strategy": strategy,
                        "data": result if response.status == 200 else None,
                        "error": result if response.status != 200 else None
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "strategy": strategy,
                "error": str(e)
            }
    
    async def test_deduplication(self) -> Dict[str, Any]:
        """Test entity deduplication with overlapping text."""
        # Content with intentional duplicates and overlaps
        test_content = """
        In the case of Brown v. Board of Education, 347 U.S. 483 (1954),
        the Supreme Court ruled unanimously. The case Brown v. Board of Education
        was a landmark decision. Brown v. Board changed American education forever.
        
        Judge John Smith presided over the hearing. Judge John Smith made several
        key rulings. The honorable John Smith, Judge of the District Court, issued
        the final order.
        """
        
        result = await self.test_unified_extraction(
            test_content,
            f"dedup_test_{int(time.time())}"
        )
        
        if result["success"]:
            entities = result["data"].get("entities", [])
            citations = result["data"].get("citations", [])
            
            # Check for duplicates
            entity_texts = [e["text"] for e in entities]
            citation_texts = [c["text"] for c in citations]
            
            # Count unique vs total
            unique_entities = len(set(entity_texts))
            total_entities = len(entity_texts)
            
            unique_citations = len(set(citation_texts))
            total_citations = len(citation_texts)
            
            return {
                "success": True,
                "total_entities": total_entities,
                "unique_entities": unique_entities,
                "total_citations": total_citations,
                "unique_citations": unique_citations,
                "deduplication_rate": {
                    "entities": f"{((total_entities - unique_entities) / max(1, total_entities)) * 100:.1f}%",
                    "citations": f"{((total_citations - unique_citations) / max(1, total_citations)) * 100:.1f}%"
                }
            }
        
        return result
    
    async def run_all_tests(self):
        """Run all unified extraction tests."""
        print("\n" + "="*60)
        print("🧪 UNIFIED EXTRACTION TEST SUITE")
        print("="*60 + "\n")
        
        # Check service health
        print("1️⃣ Testing service health...")
        if not await self.test_health_check():
            print("❌ Service is not healthy. Please start the entity extraction service.")
            return
        print("✅ Service is healthy\n")
        
        # Test content samples
        simple_content = """
        The Supreme Court in Brown v. Board of Education, 347 U.S. 483 (1954),
        held that segregation in public schools violates the Equal Protection Clause.
        """
        
        complex_content = """
        In Miranda v. Arizona, 384 U.S. 436 (1966), the Supreme Court held that
        statements made by defendants during custodial interrogation are inadmissible
        unless the defendant was informed of their rights. Chief Justice Earl Warren
        delivered the opinion. The case was argued on February 28, 1966, and decided
        on June 13, 1966. See also Dickerson v. United States, 530 U.S. 428 (2000),
        which reaffirmed Miranda. The Court's decision in Miranda has been codified
        in 18 U.S.C. § 3501. The Miranda warnings must be given before any custodial
        interrogation begins.
        """
        
        # Test 1: Default unified extraction
        print("2️⃣ Testing default unified extraction (regex mode redirected)...")
        result1 = await self.test_unified_extraction(
            simple_content,
            "unified_test_simple"
        )
        if result1["success"]:
            data = result1["data"]
            print(f"   - Entities found: {len(data.get('entities', []))}")
            print(f"   - Citations found: {len(data.get('citations', []))}")
            print(f"   - Processing time: {data.get('processing_time_ms', 0)}ms")
        print()
        
        # Test 2: Complex content with unified
        print("3️⃣ Testing unified extraction with complex content...")
        result2 = await self.test_unified_extraction(
            complex_content,
            "unified_test_complex"
        )
        if result2["success"]:
            data = result2["data"]
            print(f"   - Entities found: {len(data.get('entities', []))}")
            print(f"   - Citations found: {len(data.get('citations', []))}")
            print(f"   - Processing time: {data.get('processing_time_ms', 0)}ms")
        print()
        
        # Test 3: Explicit strategies
        print("4️⃣ Testing explicit strategy selection...")
        strategies = ["unified", "multipass", "ai_enhanced"]
        for strategy in strategies:
            print(f"   Testing {strategy} strategy...")
            result = await self.test_explicit_strategy(complex_content, strategy)
            if result["success"]:
                data = result["data"]
                print(f"   ✅ {strategy}: {len(data.get('entities', []))} entities, "
                      f"{len(data.get('citations', []))} citations")
            else:
                print(f"   ❌ {strategy}: {result.get('error', 'Unknown error')}")
        print()
        
        # Test 4: Deduplication
        print("5️⃣ Testing entity deduplication...")
        dedup_result = await self.test_deduplication()
        if dedup_result.get("success"):
            print(f"   - Total entities: {dedup_result['total_entities']}")
            print(f"   - Unique entities: {dedup_result['unique_entities']}")
            print(f"   - Deduplication rate: {dedup_result['deduplication_rate']['entities']}")
            print(f"   - Total citations: {dedup_result['total_citations']}")
            print(f"   - Unique citations: {dedup_result['unique_citations']}")
            print(f"   - Deduplication rate: {dedup_result['deduplication_rate']['citations']}")
        print()
        
        # Test 5: Fallback mechanism (simulate failure)
        print("6️⃣ Testing fallback mechanism...")
        # Create very long content that might trigger fallback
        long_content = complex_content * 100  # Repeat to create large document
        
        result_fallback = await self.test_unified_extraction(
            long_content,
            "fallback_test"
        )
        if result_fallback["success"]:
            data = result_fallback["data"]
            print(f"   - Extraction succeeded (may have used fallback)")
            print(f"   - Entities found: {len(data.get('entities', []))}")
            print(f"   - Citations found: {len(data.get('citations', []))}")
            print(f"   - Processing time: {data.get('processing_time_ms', 0)}ms")
        else:
            print(f"   - Extraction failed: {result_fallback.get('error', 'Unknown error')}")
        
        print("\n" + "="*60)
        print("✅ TEST SUITE COMPLETED")
        print("="*60 + "\n")


async def main():
    """Main test execution."""
    tester = UnifiedExtractionTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print(f"Starting unified extraction tests at {datetime.now().isoformat()}")
    asyncio.run(main())