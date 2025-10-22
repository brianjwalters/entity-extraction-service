#!/usr/bin/env python3
"""
Debug entity extraction - see raw LLM outputs.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'

import asyncio
import json
from pathlib import Path


from vllm_client.factory import get_default_client
from vllm_client.models import VLLMRequest


async def main():
    print("=" * 80)
    print("DEBUG: Entity Extraction with Guided JSON")
    print("=" * 80)

    # Load document
    rahimi_path = Path("/srv/luris/be/tests/docs/Rahimi.pdf")
    import fitz
    doc = fitz.open(rahimi_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Use tiny sample
    sample_text = text[:1000]
    print(f"\nSample text ({len(sample_text)} chars):")
    print("-" * 60)
    print(sample_text)
    print("-" * 60)

    # Create client
    print("\nInitializing vLLM client...")
    client = await get_default_client(enable_fallback=False)
    print(f"✅ Client ready: {type(client).__name__}")

    # Test 1: Simple extraction WITHOUT guided JSON
    print("\n" + "=" * 80)
    print("TEST 1: Simple extraction WITHOUT guided JSON")
    print("=" * 80)

    simple_prompt = f'''Extract legal entities from this text.

Text:
{sample_text}

Return JSON format:
{{
  "entities": [
    {{"type": "PERSON", "text": "John Doe", "id": "person_1"}}
  ]
}}
'''

    request1 = VLLMRequest(
        messages=[{"role": "user", "content": simple_prompt}],
        max_tokens=2000,
        temperature=0.0,
        seed=42
    )

    print("Generating response...")
    response1 = await client.generate_chat_completion(request1)
    print(f"\nResponse (first 500 chars):")
    print("-" * 60)
    print(response1.content[:500])
    print("-" * 60)
    print(f"Total length: {len(response1.content)} chars")
    print(f"Tokens: {response1.usage.completion_tokens}")

    # Try to parse as JSON
    try:
        parsed = json.loads(response1.content)
        print(f"\n✅ Valid JSON! Found {len(parsed.get('entities', []))} entities")
        if parsed.get('entities'):
            print("\nFirst few entities:")
            for i, e in enumerate(parsed['entities'][:3], 1):
                print(f"  {i}. [{e.get('type')}] \"{e.get('text')}\"")
    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON: {e}")

    # Test 2: Extraction WITH guided JSON
    print("\n" + "=" * 80)
    print("TEST 2: Extraction WITH guided JSON schema")
    print("=" * 80)

    # Simple JSON schema
    json_schema = {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "text": {"type": "string"},
                        "id": {"type": "string"}
                    },
                    "required": ["type", "text", "id"]
                }
            }
        },
        "required": ["entities"]
    }

    request2 = VLLMRequest(
        messages=[{"role": "user", "content": simple_prompt}],
        max_tokens=2000,
        temperature=0.0,
        seed=42,
        extra_body={"guided_json": json_schema}
    )

    print("Generating response with guided JSON...")
    response2 = await client.generate_chat_completion(request2)
    print(f"\nResponse:")
    print("-" * 60)
    print(response2.content)
    print("-" * 60)
    print(f"Total length: {len(response2.content)} chars")
    print(f"Tokens: {response2.usage.completion_tokens}")

    # Parse JSON
    try:
        parsed = json.loads(response2.content)
        print(f"\n✅ Valid JSON! Found {len(parsed.get('entities', []))} entities")
        if parsed.get('entities'):
            print("\nEntities extracted:")
            for i, e in enumerate(parsed['entities'], 1):
                print(f"  {i}. [{e.get('type')}] \"{e.get('text')}\" (ID: {e.get('id')})")
        else:
            print("\n⚠️  Empty entities array - LLM returned no entities")
    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON: {e}")

    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
