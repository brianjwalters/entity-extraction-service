#!/usr/bin/env python3
"""
Show raw LLM responses during Rahimi extraction.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'

import asyncio
import json
from pathlib import Path


from vllm_client.factory import get_default_client
from vllm_client.models import VLLMRequest
from core.entity_models import EntityExtractionResponse


async def main():
    print("=" * 80)
    print("RAW LLM RESPONSE INSPECTION")
    print("=" * 80)

    # Load tiny sample
    rahimi_path = Path("/srv/luris/be/tests/docs/Rahimi.pdf")
    import fitz
    doc = fitz.open(rahimi_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    sample_text = text[:1000]
    print(f"\nSample text: {len(sample_text)} chars")

    # Create client
    print("Initializing client...")
    client = await get_default_client(enable_fallback=False)

    # Get JSON schema from actual entity model
    json_schema = EntityExtractionResponse.model_json_schema()

    print(f"\nEntity JSON Schema:")
    print("-" * 60)
    print(json.dumps(json_schema, indent=2))
    print("-" * 60)

    # Create prompt (simplified)
    prompt = f'''Extract legal entities from this text. Return JSON with entities array.

Text:
{sample_text}

Return format matching this schema:
- entity_type: Type of entity (e.g., PERSON, ORGANIZATION, CASE_CITATION)
- text: The entity text
- confidence: Score from 0.7-1.0
- start_pos: Optional start position
- end_pos: Optional end position

Extract entities and return as JSON.'''

    # Create request with guided JSON using actual schema
    request = VLLMRequest(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.0,
        seed=42,
        extra_body={"guided_json": json_schema}
    )

    print("\n" + "=" * 80)
    print("CALLING VLLM WITH GUIDED JSON (EntityExtractionResponse schema)")
    print("=" * 80)

    response = await client.generate_chat_completion(request)

    print(f"\nRaw LLM Response:")
    print("-" * 60)
    print(response.content)
    print("-" * 60)
    print(f"Length: {len(response.content)} chars")
    print(f"Tokens: {response.usage.completion_tokens}")

    # Try to parse
    try:
        parsed = json.loads(response.content)
        print(f"\n✅ Valid JSON!")
        print(f"Keys: {list(parsed.keys())}")

        if "entities" in parsed:
            entities = parsed["entities"]
            print(f"Entities array length: {len(entities)}")

            if entities:
                print("\nFirst entity:")
                first = entities[0]
                print(f"  Keys: {list(first.keys())}")
                print(f"  Full entity: {json.dumps(first, indent=2)}")
            else:
                print("\n⚠️  EMPTY ENTITIES ARRAY!")
        else:
            print("\n❌ No 'entities' key in response!")

    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON: {e}")


if __name__ == "__main__":
    asyncio.run(main())
