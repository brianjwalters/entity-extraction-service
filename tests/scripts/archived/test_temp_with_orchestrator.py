#!/usr/bin/env python3
"""
Temperature Comparison with Full Extraction Orchestrator
Tests temperature 0.0 vs 0.3 using the actual extraction pipeline with proper entity patterns.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'

import asyncio
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from vllm_client.factory import get_default_client
from core.extraction_orchestrator import ExtractionOrchestrator
from routing.document_router import DocumentRouter
from routing.size_detector import SizeDetector


async def test_extraction_with_temperature(temperature: float, test_name: str, sample_text: str, client):
    """
    Run full extraction with orchestrator at specific temperature.

    Args:
        temperature: Temperature setting (0.0 or 0.3)
        test_name: Name for this test
        sample_text: Text to extract entities from
        client: Shared vLLM client
    """
    print("=" * 80)
    print(f"TEST: {test_name}")
    print(f"Temperature: {temperature}")
    print("=" * 80)

    # Temporarily update environment variable for this test
    original_temp = os.environ.get('EXTRACTION_ENTITY_TEMPERATURE')
    os.environ['EXTRACTION_ENTITY_TEMPERATURE'] = str(temperature)
    os.environ['EXTRACTION_RELATIONSHIP_TEMPERATURE'] = str(temperature)

    # Create orchestrator with shared client
    orchestrator = ExtractionOrchestrator(vllm_client=client)

    # Route document
    router = DocumentRouter()
    size_detector = SizeDetector()
    size_info = size_detector.detect(sample_text)
    routing = router.route(sample_text, extract_relationships=False)

    print(f"Strategy: {routing.strategy.value}")
    print(f"Document size: {len(sample_text):,} chars")
    print("Starting extraction...\n")

    import time
    start = time.time()
    result = await orchestrator.extract(sample_text, routing, size_info)
    duration = time.time() - start

    # Restore original environment variable
    if original_temp:
        os.environ['EXTRACTION_ENTITY_TEMPERATURE'] = original_temp
    else:
        os.environ.pop('EXTRACTION_ENTITY_TEMPERATURE', None)

    print(f"\n{'=' * 80}")
    print("RESULTS")
    print("=" * 80)
    print(f"Duration: {duration:.1f}s")
    print(f"Strategy: {result.strategy.value}")
    print(f"Waves Executed: {result.waves_executed}")
    print(f"Tokens Used: {result.tokens_used:,}")
    print(f"Total Entities: {len(result.entities)}")

    # Group entities by type
    entities_by_type = defaultdict(list)
    for entity in result.entities:
        entity_type = entity.get('entity_type', 'UNKNOWN')
        entities_by_type[entity_type].append(entity)

    print(f"\nEntity types ({len(entities_by_type)} unique types):")
    for entity_type, entities in sorted(entities_by_type.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {entity_type}: {len(entities)}")

    # Sample entities
    print(f"\nAll extracted entities:")
    for i, e in enumerate(result.entities, 1):
        entity_type = e.get('entity_type', 'UNKNOWN')
        text = e.get('text', '')
        confidence = e.get('confidence', 0.0)
        wave = e.get('wave_number', '?')
        print(f"  {i}. [Wave {wave}] [{entity_type}] \"{text}\" (conf: {confidence:.2f})")

    # Save results
    output_file = Path(f"orchestrator_temp_{temperature}_results.json")
    output_data = {
        "metadata": {
            "test_name": test_name,
            "temperature": temperature,
            "document": "Rahimi.pdf",
            "text_length": len(sample_text),
            "timestamp": datetime.now().isoformat(),
            "strategy": result.strategy.value,
            "waves_executed": result.waves_executed,
            "tokens_used": result.tokens_used,
            "duration_seconds": duration,
            "total_entities": len(result.entities),
            "entity_types_count": len(entities_by_type),
            "used_patterns_api": True
        },
        "entities": result.entities,
        "entity_type_counts": {
            entity_type: len(entities)
            for entity_type, entities in entities_by_type.items()
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to: {output_file}")
    print("=" * 80)

    return output_data


async def main():
    print("=" * 80)
    print("TEMPERATURE COMPARISON - FULL EXTRACTION ORCHESTRATOR")
    print("Using patterns API and proper entity classification")
    print("=" * 80)

    # Load document sample
    rahimi_path = Path("/srv/luris/be/tests/docs/Rahimi.pdf")
    import fitz
    doc = fitz.open(rahimi_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Use first 5000 chars for comprehensive extraction
    sample_text = text[:5000]
    print(f"\nUsing first 5,000 chars from Rahimi.pdf")
    print(f"Sample text preview: {sample_text[:200]}...")
    print()

    # Initialize shared client ONCE
    print("Initializing vLLM client (shared for both tests)...")
    client = await get_default_client(enable_fallback=False)
    print("✅ Client initialized\n")

    # Test 1: Temperature 0.0 (Deterministic)
    temp0_results = await test_extraction_with_temperature(
        temperature=0.0,
        test_name="Deterministic Extraction (Temperature 0.0)",
        sample_text=sample_text,
        client=client
    )

    print("\n\n")

    # Test 2: Temperature 0.3 (Creative)
    temp03_results = await test_extraction_with_temperature(
        temperature=0.3,
        test_name="Creative Extraction (Temperature 0.3)",
        sample_text=sample_text,
        client=client
    )

    # Compare
    print("\n" + "=" * 80)
    print("TEMPERATURE COMPARISON ANALYSIS")
    print("=" * 80)

    temp0_count = len(temp0_results['entities'])
    temp03_count = len(temp03_results['entities'])

    print(f"\n📊 Entity Counts:")
    print(f"  Temperature 0.0: {temp0_count} entities")
    print(f"  Temperature 0.3: {temp03_count} entities")
    print(f"  Difference: {temp03_count - temp0_count} entities")

    # Entity type comparison
    temp0_types = set(temp0_results['entity_type_counts'].keys())
    temp03_types = set(temp03_results['entity_type_counts'].keys())

    print(f"\n🏷️  Entity Type Diversity:")
    print(f"  Temperature 0.0: {len(temp0_types)} unique types")
    print(f"  Temperature 0.3: {len(temp03_types)} unique types")
    print(f"  Shared types: {len(temp0_types & temp03_types)}")

    if temp0_types and temp03_types:
        only_0 = temp0_types - temp03_types
        only_03 = temp03_types - temp0_types

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

    # Check for COURT entities specifically
    temp0_courts = [e for e in temp0_results['entities'] if 'COURT' in e.get('entity_type', '')]
    temp03_courts = [e for e in temp03_results['entities'] if 'COURT' in e.get('entity_type', '')]

    print(f"\n⚖️  Court Entity Classification:")
    print(f"  Temperature 0.0: {len(temp0_courts)} court entities")
    if temp0_courts:
        for c in temp0_courts[:5]:
            print(f"    - [{c.get('entity_type')}] {c.get('text')}")

    print(f"  Temperature 0.3: {len(temp03_courts)} court entities")
    if temp03_courts:
        for c in temp03_courts[:5]:
            print(f"    - [{c.get('entity_type')}] {c.get('text')}")

    print("\n" + "=" * 80)
    print("✅ COMPARISON COMPLETE")
    print("=" * 80)
    print("\nResult files:")
    print("  - orchestrator_temp_0.0_results.json")
    print("  - orchestrator_temp_0.3_results.json")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
