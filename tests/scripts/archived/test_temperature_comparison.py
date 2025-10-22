#!/usr/bin/env python3
"""
Temperature Comparison Test - Extract entities with different temperatures.
"""
import os

# Set CUDA devices BEFORE any imports
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'

import asyncio
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# Load .env file through config system
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Now import after .env is loaded
from vllm_client.factory import get_default_client
from core.extraction_orchestrator import ExtractionOrchestrator
from routing.document_router import DocumentRouter
from routing.size_detector import SizeDetector
from core.config import get_settings

# Verify configuration loaded
print("Verifying configuration...")
settings = get_settings()
print(f"✓ Tensor Parallel Size: {settings.vllm_direct.vllm_tensor_parallel_size}")
print(f"✓ GPU Memory Utilization: {settings.vllm_direct.vllm_gpu_memory_utilization}")
print(f"✓ Max Model Length: {settings.vllm_direct.vllm_max_model_len:,}")
print(f"✓ Entity Temperature (default): {settings.extraction.entity_temperature}")
print(f"✓ Relationship Temperature (default): {settings.extraction.relationship_temperature}")
print()


async def run_extraction_with_temperature(temperature: float, test_name: str):
    """
    Run extraction with specified temperature.

    Args:
        temperature: Temperature setting (0.0 or 0.3)
        test_name: Name for this test run
    """
    print("=" * 80)
    print(f"TEST: {test_name}")
    print(f"Temperature: {temperature}")
    print("=" * 80)

    # Load document
    rahimi_path = Path("/srv/luris/be/tests/docs/Rahimi.pdf")
    import fitz
    doc = fitz.open(rahimi_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Use first 15K chars
    test_text = text[:15000]

    print(f"\nDocument: Rahimi.pdf ({len(test_text):,} chars)")
    print("Initializing Direct vLLM client...")

    # Temporarily update environment variable for this test
    import os
    original_temp = os.environ.get('EXTRACTION_ENTITY_TEMPERATURE')
    os.environ['EXTRACTION_ENTITY_TEMPERATURE'] = str(temperature)
    os.environ['EXTRACTION_RELATIONSHIP_TEMPERATURE'] = str(temperature)

    # Create client and orchestrator
    client = await get_default_client(enable_fallback=False)
    orchestrator = ExtractionOrchestrator(vllm_client=client)

    # Route and extract
    router = DocumentRouter()
    size_detector = SizeDetector()
    size_info = size_detector.detect(test_text)
    routing = router.route(test_text, extract_relationships=True)

    print(f"Strategy: {routing.strategy.value}")
    print("Starting extraction...\n")

    import time
    start = time.time()
    result = await orchestrator.extract(test_text, routing, size_info)
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
    print(f"Total Relationships: {len(result.relationships)}")

    # Group entities by type
    entities_by_type = defaultdict(list)
    for entity in result.entities:
        entity_type = entity.get('entity_type', 'UNKNOWN')
        entities_by_type[entity_type].append(entity)

    print(f"\nEntity types ({len(entities_by_type)} unique types):")
    for entity_type, entities in sorted(entities_by_type.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {entity_type}: {len(entities)}")

    # Sample entities
    print(f"\nSample entities (first 10):")
    for i, e in enumerate(result.entities[:10], 1):
        entity_type = e.get('entity_type', 'UNKNOWN')
        text = e.get('text', '')[:50]
        confidence = e.get('confidence', 0.0)
        print(f"  {i}. [{entity_type}] \"{text}\" (conf: {confidence:.2f})")

    # Save results
    output_file = Path(f"rahimi_temp_{temperature}_results.json")
    output_data = {
        "metadata": {
            "test_name": test_name,
            "temperature": temperature,
            "document": "Rahimi.pdf",
            "text_length": len(test_text),
            "timestamp": datetime.now().isoformat(),
            "strategy": result.strategy.value,
            "waves_executed": result.waves_executed,
            "tokens_used": result.tokens_used,
            "duration_seconds": duration,
            "total_entities": len(result.entities),
            "total_relationships": len(result.relationships),
            "entity_types_count": len(entities_by_type)
        },
        "entities": result.entities,
        "relationships": result.relationships,
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


async def compare_results(temp0_results, temp03_results):
    """
    Compare results from two temperature settings.

    Args:
        temp0_results: Results from temperature 0.0
        temp03_results: Results from temperature 0.3
    """
    print("\n" + "=" * 80)
    print("TEMPERATURE COMPARISON ANALYSIS")
    print("=" * 80)

    # Entity count comparison
    print("\n📊 Entity Counts:")
    print(f"  Temperature 0.0: {len(temp0_results['entities'])} entities")
    print(f"  Temperature 0.3: {len(temp03_results['entities'])} entities")
    print(f"  Difference: {len(temp03_results['entities']) - len(temp0_results['entities'])} entities")

    # Relationship count comparison
    print("\n🔗 Relationship Counts:")
    print(f"  Temperature 0.0: {len(temp0_results['relationships'])} relationships")
    print(f"  Temperature 0.3: {len(temp03_results['relationships'])} relationships")
    print(f"  Difference: {len(temp03_results['relationships']) - len(temp0_results['relationships'])} relationships")

    # Entity type diversity
    temp0_types = set(temp0_results['entity_type_counts'].keys())
    temp03_types = set(temp03_results['entity_type_counts'].keys())

    print("\n🏷️  Entity Type Diversity:")
    print(f"  Temperature 0.0: {len(temp0_types)} unique types")
    print(f"  Temperature 0.3: {len(temp03_types)} unique types")
    print(f"  Shared types: {len(temp0_types & temp03_types)}")
    print(f"  Only in 0.0: {len(temp0_types - temp03_types)}")
    print(f"  Only in 0.3: {len(temp03_types - temp0_types)}")

    if temp03_types - temp0_types:
        print(f"\n  New types in 0.3: {sorted(list(temp03_types - temp0_types))[:5]}")
    if temp0_types - temp03_types:
        print(f"  Lost types in 0.3: {sorted(list(temp0_types - temp03_types))[:5]}")

    # Entity text comparison (exact matches)
    temp0_texts = set(e.get('text', '') for e in temp0_results['entities'])
    temp03_texts = set(e.get('text', '') for e in temp03_results['entities'])

    print("\n📝 Entity Text Overlap:")
    print(f"  Exact matches: {len(temp0_texts & temp03_texts)}")
    print(f"  Only in 0.0: {len(temp0_texts - temp03_texts)}")
    print(f"  Only in 0.3: {len(temp03_texts - temp0_texts)}")

    # Performance comparison
    print("\n⚡ Performance:")
    print(f"  Temperature 0.0: {temp0_results['metadata']['duration_seconds']:.1f}s, {temp0_results['metadata']['tokens_used']:,} tokens")
    print(f"  Temperature 0.3: {temp03_results['metadata']['duration_seconds']:.1f}s, {temp03_results['metadata']['tokens_used']:,} tokens")

    # Confidence score comparison
    temp0_confidences = [e.get('confidence', 0) for e in temp0_results['entities'] if e.get('confidence')]
    temp03_confidences = [e.get('confidence', 0) for e in temp03_results['entities'] if e.get('confidence')]

    if temp0_confidences and temp03_confidences:
        print("\n🎯 Confidence Scores:")
        print(f"  Temperature 0.0: avg={sum(temp0_confidences)/len(temp0_confidences):.3f}, min={min(temp0_confidences):.3f}, max={max(temp0_confidences):.3f}")
        print(f"  Temperature 0.3: avg={sum(temp03_confidences)/len(temp03_confidences):.3f}, min={min(temp03_confidences):.3f}, max={max(temp03_confidences):.3f}")

    print("\n" + "=" * 80)


async def main():
    print("=" * 80)
    print("TEMPERATURE COMPARISON STUDY")
    print("Rahimi.pdf - First 15,000 characters")
    print("=" * 80)

    # Test 1: Temperature 0.0 (Deterministic)
    temp0_results = await run_extraction_with_temperature(
        temperature=0.0,
        test_name="Deterministic Extraction (Temperature 0.0)"
    )

    print("\n\n")

    # Test 2: Temperature 0.3 (Slightly Creative)
    temp03_results = await run_extraction_with_temperature(
        temperature=0.3,
        test_name="Creative Extraction (Temperature 0.3)"
    )

    # Compare results
    await compare_results(temp0_results, temp03_results)

    print("\n" + "=" * 80)
    print("✅ TEMPERATURE COMPARISON COMPLETE")
    print("=" * 80)
    print("\nResult files saved:")
    print("  - rahimi_temp_0.0_results.json")
    print("  - rahimi_temp_0.3_results.json")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
