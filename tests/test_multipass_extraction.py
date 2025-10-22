#!/usr/bin/env python3
"""
Test script for multi-pass entity extraction endpoint.

This script demonstrates how to use the enhanced /extract/chunk endpoint
with multi-pass extraction enabled.
"""

import asyncio
import httpx
import json
from typing import Dict, Any, List
from datetime import datetime


# Service configuration
SERVICE_URL = "http://localhost:8007"
ENDPOINT = "/api/v1/extract/chunk"


# Sample legal text for testing
SAMPLE_CHUNK = """
In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held that 
state laws establishing separate public schools for black and white students were 
unconstitutional. Chief Justice Earl Warren delivered the opinion of the Court on 
May 17, 1954. The case was argued by Thurgood Marshall, who later became the first 
African American Supreme Court Justice. The decision overturned Plessy v. Ferguson, 
163 U.S. 537 (1896), which had established the "separate but equal" doctrine.

Under 42 U.S.C. § 1983 and the Equal Protection Clause of the Fourteenth Amendment,
the Court found that segregation in public education violated constitutional principles.
The ruling was issued by the United States District Court for the District of Kansas
and affirmed by the Supreme Court. The deadline for implementation was set by the
subsequent Brown II decision in 1955.
"""

SAMPLE_DOCUMENT = """
UNITED STATES SUPREME COURT
Brown v. Board of Education of Topeka
347 U.S. 483 (1954)

[Full document context for situating the chunk...]
""" + SAMPLE_CHUNK


async def test_single_pass_extraction():
    """Test backward-compatible single-pass extraction."""
    print("\n" + "="*60)
    print("TEST 1: Single-Pass Extraction (Backward Compatible)")
    print("="*60)
    
    request_data = {
        "chunk_id": "test_chunk_001",
        "chunk_content": SAMPLE_CHUNK,
        "whole_document": SAMPLE_DOCUMENT,
        "document_id": "brown_v_board_1954",
        "chunk_index": 0,
        "extraction_pass": "citations",
        "max_tokens": 500,
        "temperature": 0.0,
        "enable_multipass": False  # Single-pass mode
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{SERVICE_URL}{ENDPOINT}",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Single-pass extraction successful")
                print(f"   - Entities found: {len(result.get('entities', []))}")
                print(f"   - Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                print(f"   - Extraction method: {result.get('metadata', {}).get('extraction_method')}")
                
                # Display some entities
                for entity in result.get('entities', [])[:5]:
                    print(f"   • {entity['entity_type']}: {entity['text']} (confidence: {entity['confidence']:.2f})")
                
                return result
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None


async def test_multipass_extraction_default():
    """Test multi-pass extraction with default profile."""
    print("\n" + "="*60)
    print("TEST 2: Multi-Pass Extraction (Default Profile)")
    print("="*60)
    
    request_data = {
        "chunk_id": "test_chunk_002",
        "chunk_content": SAMPLE_CHUNK,
        "whole_document": SAMPLE_DOCUMENT,
        "document_id": "brown_v_board_1954",
        "chunk_index": 0,
        "enable_multipass": True,  # Enable multi-pass
        "extraction_profile": "default",
        "parallel_execution": True,
        "max_workers": 4,
        "use_registry": True
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{SERVICE_URL}{ENDPOINT}",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Multi-pass extraction successful")
                print(f"   - Total entities: {len(result.get('entities', []))}")
                print(f"   - Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                print(f"   - Profile used: {result.get('extraction_profile_used')}")
                print(f"   - Passes executed: {result.get('passes_executed')}")
                
                # Display metrics
                metrics = result.get('multipass_metrics', {})
                if metrics:
                    print(f"\n   Metrics:")
                    print(f"   - Successful passes: {metrics.get('successful_passes')}/{metrics.get('total_passes_executed')}")
                    print(f"   - Unique entities: {metrics.get('unique_entities')}")
                    print(f"   - Duplicates removed: {metrics.get('duplicates_removed')}")
                    print(f"   - Parallel execution time: {metrics.get('parallel_execution_time_ms', 0):.2f}ms")
                
                # Display entities by type
                entity_types = {}
                for entity in result.get('entities', []):
                    entity_type = entity['entity_type']
                    if entity_type not in entity_types:
                        entity_types[entity_type] = []
                    entity_types[entity_type].append(entity['text'])
                
                print(f"\n   Entities by type:")
                for entity_type, entities in entity_types.items():
                    print(f"   • {entity_type}: {len(entities)} found")
                    for text in entities[:3]:  # Show first 3
                        print(f"     - {text}")
                
                return result
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None


async def test_multipass_extraction_fast():
    """Test multi-pass extraction with fast profile."""
    print("\n" + "="*60)
    print("TEST 3: Multi-Pass Extraction (Fast Profile)")
    print("="*60)
    
    request_data = {
        "chunk_id": "test_chunk_003",
        "chunk_content": SAMPLE_CHUNK,
        "whole_document": SAMPLE_DOCUMENT,
        "document_id": "brown_v_board_1954",
        "chunk_index": 0,
        "enable_multipass": True,
        "extraction_profile": "fast",  # Use fast profile
        "parallel_execution": True
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{SERVICE_URL}{ENDPOINT}",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Fast extraction successful")
                print(f"   - Total entities: {len(result.get('entities', []))}")
                print(f"   - Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                print(f"   - Passes executed: {result.get('passes_executed')} (reduced set)")
                
                return result
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None


async def test_multipass_extraction_custom():
    """Test multi-pass extraction with custom pass selection."""
    print("\n" + "="*60)
    print("TEST 4: Multi-Pass Extraction (Custom Passes)")
    print("="*60)
    
    request_data = {
        "chunk_id": "test_chunk_004",
        "chunk_content": SAMPLE_CHUNK,
        "whole_document": SAMPLE_DOCUMENT,
        "document_id": "brown_v_board_1954",
        "chunk_index": 0,
        "enable_multipass": True,
        "passes": [1, 4, 5],  # Only citations, entities, and courts
        "parallel_execution": True,
        "max_workers": 3
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{SERVICE_URL}{ENDPOINT}",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Custom passes extraction successful")
                print(f"   - Total entities: {len(result.get('entities', []))}")
                print(f"   - Processing time: {result.get('processing_time_ms', 0):.2f}ms")
                print(f"   - Passes executed: {result.get('passes_executed')}")
                
                return result
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None


async def test_extraction_profiles():
    """Test the extraction profiles endpoint."""
    print("\n" + "="*60)
    print("TEST 5: Get Available Extraction Profiles")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{SERVICE_URL}/api/v1/extraction-profiles")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Retrieved {result.get('total_profiles', 0)} extraction profiles")
                
                profiles = result.get('profiles', {})
                for profile_name, profile_data in profiles.items():
                    print(f"\n   Profile: {profile_name}")
                    print(f"   - Name: {profile_data.get('name')}")
                    print(f"   - Description: {profile_data.get('description')}")
                    print(f"   - Enabled passes: {profile_data.get('enabled_passes')}")
                    print(f"   - Parallel: {profile_data.get('parallel_execution')}")
                    print(f"   - Max workers: {profile_data.get('max_workers')}")
                
                return result
            else:
                print(f"❌ Request failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None


async def compare_performance():
    """Compare performance between single-pass and multi-pass extraction."""
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON")
    print("="*60)
    
    # Run single-pass
    single_result = await test_single_pass_extraction()
    
    # Run multi-pass default
    multi_default_result = await test_multipass_extraction_default()
    
    # Run multi-pass fast
    multi_fast_result = await test_multipass_extraction_fast()
    
    # Compare results
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    
    if single_result:
        print(f"\nSingle-Pass:")
        print(f"  - Entities: {len(single_result.get('entities', []))}")
        print(f"  - Time: {single_result.get('processing_time_ms', 0):.2f}ms")
    
    if multi_default_result:
        print(f"\nMulti-Pass (Default):")
        print(f"  - Entities: {len(multi_default_result.get('entities', []))}")
        print(f"  - Time: {multi_default_result.get('processing_time_ms', 0):.2f}ms")
        metrics = multi_default_result.get('multipass_metrics', {})
        if metrics:
            print(f"  - Unique entities: {metrics.get('unique_entities')}")
            print(f"  - Duplicates removed: {metrics.get('duplicates_removed')}")
    
    if multi_fast_result:
        print(f"\nMulti-Pass (Fast):")
        print(f"  - Entities: {len(multi_fast_result.get('entities', []))}")
        print(f"  - Time: {multi_fast_result.get('processing_time_ms', 0):.2f}ms")
    
    # Calculate improvement
    if single_result and multi_default_result:
        single_count = len(single_result.get('entities', []))
        multi_count = len(multi_default_result.get('entities', []))
        if single_count > 0:
            improvement = ((multi_count - single_count) / single_count) * 100
            print(f"\n📊 Multi-pass extracted {improvement:.1f}% more entities than single-pass")


async def main():
    """Main test function."""
    print("\n" + "="*60)
    print("MULTI-PASS ENTITY EXTRACTION TEST SUITE")
    print("="*60)
    print(f"Service URL: {SERVICE_URL}")
    print(f"Testing endpoint: {ENDPOINT}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check service health
    print("\nChecking service health...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            health_response = await client.get(f"{SERVICE_URL}/api/v1/health")
            if health_response.status_code == 200:
                print("✅ Entity Extraction Service is healthy")
            else:
                print("⚠️ Service health check returned non-200 status")
        except Exception as e:
            print(f"❌ Service not available: {e}")
            print("\nPlease ensure the Entity Extraction Service is running:")
            print("  sudo systemctl start luris-entity-extraction")
            return
    
    # Run tests
    await test_extraction_profiles()
    await compare_performance()
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())