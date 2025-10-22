#!/usr/bin/env python3
"""
Simple validation test for guided JSON improvements.

Tests the HTTP client with guided JSON support without requiring
DirectVLLMClient initialization (which would conflict with running vLLM service).
"""
import asyncio
import json
from pathlib import Path
import sys

# Add src to path

from client.vllm_http_client import HTTPVLLMClient
from vllm_client.models import VLLMRequest, VLLMConfig
from core.entity_models import EntityExtractionResponse


async def test_http_client_guided_json():
    """Test that HTTPVLLMClient handles guided JSON parameter."""

    print("=" * 80)
    print("TESTING: HTTP Client Guided JSON Support")
    print("=" * 80)

    # Create HTTP client (uses existing vLLM service on port 8080)
    config = VLLMConfig(
        base_url="http://10.10.0.87:8080",
        api_key="test-key",
        model_name="qwen-instruct-160k",
        timeout=180
    )

    client = HTTPVLLMClient(config)

    print(f"\n✅ HTTPVLLMClient initialized")
    print(f"   Base URL: {config.base_url}")
    print(f"   Model: {config.model_name}")

    # Create simple test prompt
    test_prompt = """Extract legal entities from this text:

"John Smith filed a lawsuit against ABC Corporation in California Supreme Court on January 15, 2024."

Return JSON with this structure:
{
  "entities": [
    {"type": "PERSON", "text": "John Smith", "confidence": 0.95},
    {"type": "ORGANIZATION", "text": "ABC Corporation", "confidence": 0.95},
    {"type": "COURT", "text": "California Supreme Court", "confidence": 0.95},
    {"type": "DATE", "text": "January 15, 2024", "confidence": 0.95}
  ]
}
"""

    # Get JSON schema from Pydantic model
    json_schema = EntityExtractionResponse.model_json_schema()

    print(f"\n📋 Using guided JSON schema: EntityExtractionResponse")
    print(f"   Schema keys: {list(json_schema.keys())}")

    # Create request with guided_json in extra_body
    request = VLLMRequest(
        messages=[{"role": "user", "content": test_prompt}],
        max_tokens=1024,
        temperature=0.0,
        seed=42,
        stream=False,
        extra_body={"guided_json": json_schema}  # This should trigger warning
    )

    print(f"\n🔧 VLLMRequest created with guided_json parameter")
    print(f"   Max tokens: {request.max_tokens}")
    print(f"   Temperature: {request.temperature}")
    print(f"   Extra body keys: {list(request.extra_body.keys())}")

    # Call HTTP client
    print(f"\n📡 Calling vLLM HTTP API...")

    try:
        response = await client.generate_chat_completion(request)

        print(f"\n✅ Response received")
        print(f"   Total tokens: {response.usage.total_tokens}")
        print(f"   Content length: {len(response.content)} chars")

        # Try to parse response as JSON
        print(f"\n🔍 Parsing JSON response...")

        try:
            parsed = json.loads(response.content)
            print(f"✅ JSON parsing successful!")

            # Validate with Pydantic
            validated = EntityExtractionResponse.model_validate(parsed)
            print(f"✅ Pydantic validation successful!")
            print(f"   Entities extracted: {len(validated.entities)}")

            # Display extracted entities
            if validated.entities:
                print(f"\n📊 Extracted Entities:")
                for i, entity in enumerate(validated.entities, 1):
                    print(f"   {i}. {entity.type}: \"{entity.text}\" (conf: {entity.confidence})")

            return True

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"   Response preview: {response.content[:500]}")
            return False

    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_factory_client_type():
    """Test which client type the factory creates."""

    print("\n" + "=" * 80)
    print("TESTING: Factory Client Type")
    print("=" * 80)

    try:
        from vllm.factory import create_vllm_client

        print(f"\n🏭 Creating vLLM client via factory...")
        client = create_vllm_client()

        client_type = type(client).__name__
        print(f"\n✅ Client created: {client_type}")

        if client_type == "DirectVLLMClient":
            print(f"   ✅ DirectVLLMClient - Guided JSON fully supported!")
            print(f"   ✅ vLLM library properly installed")
        elif client_type == "HTTPVLLMClient":
            print(f"   ⚠️  HTTPVLLMClient - Limited guided JSON support")
            print(f"   ⚠️  DirectVLLMClient likely failed (GPU conflict or vLLM issue)")
        else:
            print(f"   ❓ Unknown client type: {client_type}")

        return client_type

    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all validation tests."""

    print("\n" + "=" * 80)
    print("GUIDED JSON VALIDATION TEST SUITE")
    print("=" * 80)
    print("\nThis tests the guided JSON improvements without DirectVLLMClient")
    print("initialization (which would conflict with running vLLM service).\n")

    results = {}

    # Test 1: Factory client type
    client_type = await test_factory_client_type()
    results['factory'] = client_type is not None

    # Test 2: HTTP client with guided JSON
    http_success = await test_http_client_guided_json()
    results['http_guided_json'] = http_success

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print(f"\n✅ ALL TESTS PASSED")
    else:
        print(f"\n⚠️  SOME TESTS FAILED")

    print("\n" + "=" * 80)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
