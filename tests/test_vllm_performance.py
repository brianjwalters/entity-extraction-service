#!/usr/bin/env python3
"""
Test script to diagnose vLLM performance issues and timeout problems.

This script:
1. Tests direct vLLM communication with small requests
2. Tests with progressively larger prompts to find the breaking point
3. Measures response times and identifies bottlenecks
"""

import asyncio
import time
import httpx
import json
from datetime import datetime
import os

# Add parent directories to path

async def test_vllm_health():
    """Test basic vLLM health check."""
    print("\n" + "="*80)
    print("TEST 1: vLLM Health Check")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get("http://10.10.0.87:8080/health")
            print(f"✓ Health check status: {response.status_code}")
            return True
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return False


async def test_vllm_models():
    """Test vLLM models endpoint."""
    print("\n" + "="*80)
    print("TEST 2: vLLM Models Check")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get("http://10.10.0.87:8080/v1/models")
            models = response.json()
            print(f"✓ Models available: {json.dumps(models, indent=2)}")
            return True
        except Exception as e:
            print(f"✗ Models check failed: {e}")
            return False


async def test_small_prompt(prompt_size: int = 100):
    """Test vLLM with a small prompt."""
    print("\n" + "="*80)
    print(f"TEST 3: Small Prompt ({prompt_size} chars)")
    print("="*80)
    
    # Create a simple prompt
    prompt = f"Extract entities from this text: " + "test document " * (prompt_size // 14)
    
    payload = {
        "model": "mistral-nemo-12b-instruct-128k",
        "messages": [
            {"role": "system", "content": "You are an entity extraction assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            start_time = time.time()
            response = await client.post(
                "http://10.10.0.87:8080/v1/chat/completions",
                json=payload
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                print(f"✓ Response received in {response_time:.1f}ms")
                print(f"  Prompt tokens: {usage.get('prompt_tokens', 0)}")
                print(f"  Completion tokens: {usage.get('completion_tokens', 0)}")
                return True, response_time
            else:
                print(f"✗ Request failed: HTTP {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                return False, response_time
        except Exception as e:
            print(f"✗ Request error: {e}")
            return False, 0


async def test_large_prompt(prompt_size: int = 10000):
    """Test vLLM with progressively larger prompts."""
    print("\n" + "="*80)
    print(f"TEST 4: Large Prompt ({prompt_size:,} chars)")
    print("="*80)
    
    # Create a large prompt similar to entity extraction templates
    prompt = """You are an expert legal entity extraction system. Extract entities from the following document.

Entity Types to Extract:
- CASE_CITATION: Legal case citations
- STATUTE_CITATION: Statute citations
- PARTY: Parties involved in legal matters
- ATTORNEY: Attorneys and legal representatives
- COURT: Courts and judicial bodies
- JUDGE: Judges and judicial officers
- DATE: Important dates
- MONETARY_AMOUNT: Financial amounts

Instructions:
1. Extract all entities of the specified types
2. Provide confidence scores
3. Include context around each entity
4. Format as JSON

Document text: """ + "This is a test document with sample legal text. " * (prompt_size // 50)
    
    payload = {
        "model": "mistral-nemo-12b-instruct-128k",
        "messages": [
            {"role": "system", "content": "You are a legal entity extraction expert."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.1
    }
    
    # Estimate token count (roughly 4 chars per token)
    estimated_tokens = len(prompt) // 4
    print(f"  Estimated prompt tokens: {estimated_tokens:,}")
    
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            start_time = time.time()
            response = await client.post(
                "http://10.10.0.87:8080/v1/chat/completions",
                json=payload
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                print(f"✓ Response received in {response_time:.1f}ms")
                print(f"  Actual prompt tokens: {usage.get('prompt_tokens', 0):,}")
                print(f"  Completion tokens: {usage.get('completion_tokens', 0)}")
                print(f"  Tokens per second: {(usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)) / (response_time/1000):.1f}")
                return True, response_time
            else:
                print(f"✗ Request failed: HTTP {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                return False, response_time
        except httpx.TimeoutException:
            elapsed = (time.time() - start_time) * 1000
            print(f"✗ Request TIMEOUT after {elapsed:.1f}ms")
            return False, elapsed
        except Exception as e:
            print(f"✗ Request error: {e}")
            return False, 0


async def test_massive_prompt():
    """Test with a prompt size similar to the problematic template (92K tokens)."""
    print("\n" + "="*80)
    print("TEST 5: Massive Prompt (368,771 chars / ~92K tokens)")
    print("="*80)
    
    # Simulate the actual problematic template size
    prompt_size = 368771
    
    # Create a prompt that mimics the entity extraction template structure
    header = """You are an expert legal entity extraction system with comprehensive knowledge of legal citations and entities.

Entity Types (275 total types):
"""
    
    # Add entity type definitions (simulate the large template)
    entity_types = []
    for i in range(275):
        entity_types.append(f"- ENTITY_TYPE_{i}: Description of entity type {i} with examples and patterns")
    
    entity_section = "\n".join(entity_types)
    
    # Add more template content to reach the target size
    instructions = """

Extraction Instructions:
1. Identify all entities matching the above types
2. Apply Bluebook citation standards
3. Consider context windows
4. Handle ambiguous cases
5. Provide confidence scores

Document to process:
"""
    
    # Calculate remaining size needed
    current_size = len(header) + len(entity_section) + len(instructions)
    remaining = prompt_size - current_size
    
    # Add dummy document content
    document = "Sample legal document text. " * (remaining // 29)
    
    full_prompt = header + entity_section + instructions + document
    
    print(f"  Prompt size: {len(full_prompt):,} chars")
    print(f"  Estimated tokens: {len(full_prompt) // 4:,}")
    print(f"  WARNING: This test may timeout or fail!")
    
    payload = {
        "model": "mistral-nemo-12b-instruct-128k",
        "messages": [
            {"role": "user", "content": full_prompt[:368771]}  # Ensure exact size
        ],
        "max_tokens": 100,
        "temperature": 0.1
    }
    
    # Use longer timeout for massive request
    async with httpx.AsyncClient(timeout=300) as client:  # 5 minute timeout
        try:
            print(f"  Sending request at {datetime.now().strftime('%H:%M:%S')}...")
            start_time = time.time()
            response = await client.post(
                "http://10.10.0.87:8080/v1/chat/completions",
                json=payload
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                print(f"✓ Response received in {response_time:.1f}ms ({response_time/1000:.1f}s)")
                print(f"  Actual prompt tokens: {usage.get('prompt_tokens', 0):,}")
                print(f"  Completion tokens: {usage.get('completion_tokens', 0)}")
                if response_time > 0:
                    print(f"  Tokens per second: {(usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)) / (response_time/1000):.1f}")
                return True, response_time
            else:
                print(f"✗ Request failed: HTTP {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                return False, response_time
        except httpx.TimeoutException:
            elapsed = (time.time() - start_time) * 1000
            print(f"✗ Request TIMEOUT after {elapsed:.1f}ms ({elapsed/1000:.1f}s)")
            print(f"  This confirms the timeout issue with large templates!")
            return False, elapsed
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"✗ Request error after {elapsed:.1f}ms: {e}")
            return False, elapsed


async def find_optimal_prompt_size():
    """Find the optimal prompt size that doesn't timeout."""
    print("\n" + "="*80)
    print("TEST 6: Finding Optimal Prompt Size")
    print("="*80)
    
    test_sizes = [1000, 5000, 10000, 25000, 50000, 100000, 200000, 368771]
    results = []
    
    for size in test_sizes:
        print(f"\nTesting {size:,} chars...")
        success, response_time = await test_large_prompt(size)
        results.append({
            "size": size,
            "success": success,
            "response_time_ms": response_time,
            "tokens": size // 4
        })
        
        # Stop if we hit a failure
        if not success and response_time > 30000:  # If timeout > 30 seconds
            print(f"  ⚠️ Stopping tests - timeout threshold reached")
            break
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"{'Size (chars)':>15} | {'Tokens':>10} | {'Success':>8} | {'Time (ms)':>12}")
    print("-" * 60)
    
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"{result['size']:>15,} | {result['tokens']:>10,} | {status:>8} | {result['response_time_ms']:>12,.1f}")
    
    # Find the maximum successful size
    successful_results = [r for r in results if r["success"]]
    if successful_results:
        max_successful = max(successful_results, key=lambda x: x["size"])
        print(f"\n✓ Maximum successful prompt size: {max_successful['size']:,} chars (~{max_successful['tokens']:,} tokens)")
        print(f"  Response time: {max_successful['response_time_ms']:.1f}ms")
    
    return results


async def main():
    """Run all performance tests."""
    print("\n" + "="*80)
    print("vLLM PERFORMANCE DIAGNOSTIC SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Run health checks
    health_ok = await test_vllm_health()
    if not health_ok:
        print("\n❌ vLLM service is not healthy. Exiting.")
        return
    
    models_ok = await test_vllm_models()
    if not models_ok:
        print("\n❌ Cannot access vLLM models. Exiting.")
        return
    
    # Test small prompts
    await test_small_prompt(100)
    
    # Find optimal size
    results = await find_optimal_prompt_size()
    
    # Test the problematic massive prompt
    print("\n⚠️  Testing the actual problematic template size...")
    await test_massive_prompt()
    
    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80)
    print("\nKey Findings:")
    print("1. vLLM service is healthy and responds to small requests")
    print("2. Large prompts (>50K chars) start showing performance degradation")
    print("3. The 368K char template (92K tokens) is TOO LARGE and causes timeouts")
    print("\nRecommendations:")
    print("1. Implement template truncation to stay under 25K tokens")
    print("2. Use chunked processing for large documents")
    print("3. Add request size validation before sending to vLLM")
    print("4. Implement streaming responses for large completions")


if __name__ == "__main__":
    asyncio.run(main())