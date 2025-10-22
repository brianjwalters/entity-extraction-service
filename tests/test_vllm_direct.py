#!/usr/bin/env python3
"""
Direct test of vLLM communication to debug entity extraction issues.
This script bypasses all the service layers and tests vLLM directly.
"""

import asyncio
import json
import httpx
from datetime import datetime

# vLLM server settings
VLLM_URL = "http://localhost:8080/v1/chat/completions"

async def test_vllm_basic():
    """Test basic vLLM connectivity and response."""
    print("=" * 80)
    print("TEST 1: Basic vLLM Connectivity Test")
    print("=" * 80)
    
    # Simple test prompt
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that extracts entities from text. Always respond with valid JSON."
        },
        {
            "role": "user", 
            "content": """Extract entities from this text and return as JSON:
            
"John Smith filed a lawsuit in the U.S. District Court for the Eastern District of California against ABC Corporation."

Return JSON with this structure:
{
    "entities": [
        {"text": "entity text", "type": "entity type"}
    ]
}"""
        }
    ]
    
    request_data = {
        "model": "mistral-nemo-12b-instruct-128k",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 500,
        "response_format": {"type": "json_object"}
    }
    
    print(f"Request URL: {VLLM_URL}")
    print(f"Request data: {json.dumps(request_data, indent=2)}")
    print("\nSending request...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(VLLM_URL, json=request_data)
            response.raise_for_status()
            
            result = response.json()
            print(f"\nResponse status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"\nFull response:\n{json.dumps(result, indent=2)}")
            
            # Extract the actual content
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                print(f"\n✅ CONTENT RECEIVED (length: {len(content)} chars):")
                print(content)
                
                # Try to parse as JSON
                try:
                    parsed_json = json.loads(content)
                    print(f"\n✅ JSON PARSING SUCCESSFUL:")
                    print(json.dumps(parsed_json, indent=2))
                    
                    # Check if entities were found
                    if "entities" in parsed_json:
                        print(f"\n✅ ENTITIES FOUND: {len(parsed_json['entities'])}")
                        for entity in parsed_json['entities']:
                            print(f"  - {entity.get('type', 'UNKNOWN')}: {entity.get('text', 'N/A')}")
                    else:
                        print("\n❌ No 'entities' key in response")
                        
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON PARSING FAILED: {e}")
                    print(f"Raw content that failed to parse:\n{content}")
            else:
                print("\n❌ No choices in response or empty choices")
                
    except httpx.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response body: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")


async def test_vllm_entity_extraction():
    """Test vLLM with actual entity extraction prompt."""
    print("\n" + "=" * 80)
    print("TEST 2: Entity Extraction Prompt Test")
    print("=" * 80)
    
    # More complex legal text
    test_text = """
    In the case of Miranda v. Arizona, 384 U.S. 436 (1966), the Supreme Court of the United States
    ruled that detained criminal suspects must be informed of their constitutional rights before police
    questioning. Chief Justice Earl Warren delivered the opinion. The defendant, Ernesto Miranda, was
    arrested in Phoenix, Arizona and convicted based on his confession.
    """
    
    messages = [
        {
            "role": "system",
            "content": "You are a legal entity extraction expert. Extract all legal entities from the text and categorize them. Return valid JSON only."
        },
        {
            "role": "user",
            "content": f"""Extract all entities from this legal text:

{test_text}

Return a JSON object with this exact structure:
{{
    "entities": [
        {{"text": "extracted text", "type": "PERSON|CASE|COURT|LOCATION|LAW|DATE", "confidence": 0.0-1.0}}
    ],
    "citations": [
        {{"text": "citation text", "type": "case_citation|statute", "normalized": "normalized format"}}
    ]
}}"""
        }
    ]
    
    request_data = {
        "model": "mistral-nemo-12b-instruct-128k",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1000,
        "response_format": {"type": "json_object"}
    }
    
    print(f"Testing with legal text ({len(test_text)} chars)")
    print("\nSending request...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = datetime.now()
            response = await client.post(VLLM_URL, json=request_data)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\n✅ Response received in {elapsed:.2f} seconds")
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                print(f"Content length: {len(content)} chars")
                
                try:
                    parsed = json.loads(content)
                    
                    entities = parsed.get("entities", [])
                    citations = parsed.get("citations", [])
                    
                    print(f"\n✅ EXTRACTION RESULTS:")
                    print(f"  - Entities found: {len(entities)}")
                    print(f"  - Citations found: {len(citations)}")
                    
                    if entities:
                        print("\nEntities:")
                        for e in entities[:5]:  # Show first 5
                            print(f"  - {e.get('type', 'UNKNOWN')}: {e.get('text', 'N/A')} (conf: {e.get('confidence', 0)})")
                    
                    if citations:
                        print("\nCitations:")
                        for c in citations[:5]:  # Show first 5
                            print(f"  - {c.get('type', 'UNKNOWN')}: {c.get('text', 'N/A')}")
                            
                    # Check for expected entities
                    expected_entities = ["Miranda v. Arizona", "Supreme Court", "Earl Warren", "Ernesto Miranda", "Phoenix", "Arizona"]
                    found_texts = [e.get('text', '').lower() for e in entities]
                    
                    print("\n📊 Expected Entity Coverage:")
                    for expected in expected_entities:
                        found = any(expected.lower() in text for text in found_texts)
                        status = "✅" if found else "❌"
                        print(f"  {status} {expected}")
                        
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON parsing failed: {e}")
                    print(f"Raw content:\n{content[:500]}...")  # Show first 500 chars
            else:
                print("\n❌ No choices in response")
                
    except Exception as e:
        print(f"\n❌ Test failed: {type(e).__name__}: {e}")


async def test_vllm_with_empty_response():
    """Test what happens when we ask for entities that don't exist."""
    print("\n" + "=" * 80)
    print("TEST 3: Empty/No Entities Test")
    print("=" * 80)
    
    messages = [
        {
            "role": "system",
            "content": "Extract legal entities from text. If no entities found, return empty arrays."
        },
        {
            "role": "user",
            "content": """Extract entities from: "The weather is nice today."
            
Return JSON: {"entities": [], "citations": []}"""
        }
    ]
    
    request_data = {
        "model": "mistral-nemo-12b-instruct-128k",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 200,
        "response_format": {"type": "json_object"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(VLLM_URL, json=request_data)
            result = response.json()
            
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                print(f"Response content:\n{content}")
                
                parsed = json.loads(content)
                print(f"\nParsed result: {json.dumps(parsed, indent=2)}")
                print(f"Entities: {len(parsed.get('entities', []))}")
                print(f"Citations: {len(parsed.get('citations', []))}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all tests."""
    print("🔍 vLLM Direct Communication Test Suite")
    print(f"📅 {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Check vLLM health first
    print("\nChecking vLLM server health...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get("http://localhost:8080/health")
            print(f"✅ vLLM server is healthy: {health_response.text}")
    except Exception as e:
        print(f"❌ vLLM server health check failed: {e}")
        print("Make sure vLLM is running on port 8080")
        return
    
    # Run tests
    await test_vllm_basic()
    await test_vllm_entity_extraction()
    await test_vllm_with_empty_response()
    
    print("\n" + "=" * 80)
    print("🏁 All tests completed")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())