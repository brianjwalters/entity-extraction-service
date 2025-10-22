#!/usr/bin/env python3
"""
Temperature Comparison - No Guided JSON
Compare raw LLM output at temperature 0.0 vs 0.3 without guided JSON constraints.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'

import asyncio
import json
from pathlib import Path
from datetime import datetime


from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from vllm_client.factory import get_default_client
from vllm_client.models import VLLMRequest


async def test_temperature(temperature: float, sample_text: str, test_name: str, client):
    """
    Test LLM extraction at specific temperature WITHOUT guided JSON.

    Args:
        temperature: Temperature setting (0.0 or 0.3)
        sample_text: Text to extract entities from
        test_name: Name for this test
        client: Shared vLLM client instance
    """
    print("=" * 80)
    print(f"TEST: {test_name}")
    print(f"Temperature: {temperature}")
    print("=" * 80)

    # Create simple extraction prompt
    prompt = f"""Extract legal entities from this text. Return JSON format.

Text:
{sample_text}

Extract entities and return JSON in this format:
{{
  "entities": [
    {{"entity_type": "PERSON", "text": "John Doe", "confidence": 0.95}},
    {{"entity_type": "CASE_CITATION", "text": "Smith v. Jones", "confidence": 0.90}}
  ]
}}

Return ONLY the JSON object, no other text.
"""

    # Create request WITHOUT guided_json
    request = VLLMRequest(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=temperature,
        seed=42,
        stream=False
    )

    print(f"Calling vLLM with temperature={temperature}, NO guided JSON...")

    import time
    start = time.time()
    response = await client.generate_chat_completion(request)
    duration = time.time() - start

    print(f"\n{'=' * 80}")
    print("RAW LLM RESPONSE")
    print("=" * 80)
    print(response.content)
    print("=" * 80)
    print(f"Duration: {duration:.2f}s")
    print(f"Tokens: {response.usage.total_tokens}")

    # Try to parse JSON
    try:
        parsed = json.loads(response.content)
        entities = parsed.get('entities', [])
        print(f"\n✅ Valid JSON with {len(entities)} entities")

        if entities:
            print("\nExtracted entities:")
            for i, e in enumerate(entities[:10], 1):
                print(f"  {i}. [{e.get('entity_type')}] \"{e.get('text')}\" (conf: {e.get('confidence', 0):.2f})")
        else:
            print("\n⚠️  Empty entities array")

    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON: {e}")
        entities = []

    # Save results
    output_file = Path(f"temp_{temperature}_no_guided.json")
    output_data = {
        "metadata": {
            "test_name": test_name,
            "temperature": temperature,
            "guided_json": False,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "tokens": response.usage.total_tokens,
            "total_entities": len(entities)
        },
        "raw_response": response.content,
        "entities": entities
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to: {output_file}")
    print("=" * 80)

    return output_data


async def main():
    print("=" * 80)
    print("TEMPERATURE COMPARISON - NO GUIDED JSON")
    print("Testing raw LLM output at temperature 0.0 vs 0.3")
    print("=" * 80)

    # Load document sample
    rahimi_path = Path("/srv/luris/be/tests/docs/Rahimi.pdf")
    import fitz
    doc = fitz.open(rahimi_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Use first 3000 chars for faster testing
    sample_text = text[:3000]
    print(f"\nUsing first 3,000 chars from Rahimi.pdf")
    print(f"Sample text preview: {sample_text[:200]}...")
    print()

    # Initialize shared client ONCE
    print("Initializing vLLM client (shared for both tests)...")
    client = await get_default_client(enable_fallback=False)
    print("✅ Client initialized\n")

    # Test 1: Temperature 0.0 (Deterministic)
    temp0_results = await test_temperature(
        temperature=0.0,
        sample_text=sample_text,
        test_name="Deterministic (Temperature 0.0)",
        client=client
    )

    print("\n\n")

    # Test 2: Temperature 0.3 (Creative)
    temp03_results = await test_temperature(
        temperature=0.3,
        sample_text=sample_text,
        test_name="Creative (Temperature 0.3)",
        client=client
    )

    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    temp0_count = len(temp0_results['entities'])
    temp03_count = len(temp03_results['entities'])

    print(f"\n📊 Entity Counts:")
    print(f"  Temperature 0.0: {temp0_count} entities")
    print(f"  Temperature 0.3: {temp03_count} entities")
    print(f"  Difference: {temp03_count - temp0_count} entities")

    # Entity type comparison
    temp0_types = set(e.get('entity_type') for e in temp0_results['entities'])
    temp03_types = set(e.get('entity_type') for e in temp03_results['entities'])

    print(f"\n🏷️  Entity Types:")
    print(f"  Temperature 0.0: {len(temp0_types)} unique types")
    print(f"  Temperature 0.3: {len(temp03_types)} unique types")

    if temp0_types and temp03_types:
        shared = temp0_types & temp03_types
        only_0 = temp0_types - temp03_types
        only_03 = temp03_types - temp0_types

        print(f"  Shared: {len(shared)}")
        if only_0:
            print(f"  Only in 0.0: {sorted(only_0)}")
        if only_03:
            print(f"  Only in 0.3: {sorted(only_03)}")

    # Text comparison
    temp0_texts = set(e.get('text') for e in temp0_results['entities'])
    temp03_texts = set(e.get('text') for e in temp03_results['entities'])

    print(f"\n📝 Entity Text Overlap:")
    print(f"  Exact matches: {len(temp0_texts & temp03_texts)}")
    print(f"  Only in 0.0: {len(temp0_texts - temp03_texts)}")
    print(f"  Only in 0.3: {len(temp03_texts - temp0_texts)}")

    print("\n" + "=" * 80)
    print("✅ COMPARISON COMPLETE")
    print("=" * 80)
    print("\nResult files:")
    print("  - temp_0.0_no_guided.json")
    print("  - temp_0.3_no_guided.json")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
