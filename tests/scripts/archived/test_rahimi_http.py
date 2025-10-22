#!/usr/bin/env python3
"""
Rahimi extraction test using HTTP vLLM client (connects to running service).
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

# Add src to path for imports

from src.vllm_client.factory import VLLMClientFactory, VLLMClientType
from src.vllm_client.models import VLLMConfig
from src.core.extraction_orchestrator import ExtractionOrchestrator
from src.routing.document_router import DocumentRouter
from src.routing.size_detector import SizeDetector


async def main():
    print("=" * 80)
    print("RAHIMI EXTRACTION TEST - HTTP CLIENT TO RUNNING vLLM SERVICE")
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

    # Create HTTP client using factory
    print("Creating HTTP vLLM client (port 8080)...")

    # Configure to use HTTP client
    config = VLLMConfig(
        model="qwen-instruct-160k",
        base_url="http://localhost:8080",
        max_model_len=32768,
        http_timeout=300
    )

    client = await VLLMClientFactory.create_client(
        preferred_type=VLLMClientType.HTTP_API,
        config=config,
        enable_fallback=False
    )

    print(f"✅ Connected to vLLM service")
    print(f"   Client type: {type(client).__name__}")

    # Create orchestrator
    orchestrator = ExtractionOrchestrator(vllm_client=client)

    # Route and analyze
    router = DocumentRouter()
    size_detector = SizeDetector()
    size_info = size_detector.detect(test_text)
    routing = router.route(test_text, extract_relationships=True)

    print(f"   Strategy: {routing.strategy.value}")
    print(f"\nStarting extraction...")

    start = time.time()
    result = await orchestrator.extract(test_text, routing, size_info)
    duration = time.time() - start

    print(f"\n{'=' * 80}")
    print("RESULTS")
    print("=" * 80)
    print(f"Duration: {duration:.1f}s")
    print(f"Strategy: {result.strategy.value}")
    print(f"Waves: {result.waves_executed}")
    print(f"Tokens: {result.tokens_used:,}")
    print(f"Entities: {len(result.entities)}")
    print(f"Relationships: {len(result.relationships)}")

    # Entity types (FIX: use 'entity_type' not 'type')
    types = {}
    for e in result.entities:
        # Entities are dicts with 'entity_type' field
        t = e.get('entity_type', e.get('type', 'UNKNOWN'))
        types[t] = types.get(t, 0) + 1

    print(f"\nEntity types ({len(types)}):")
    for t, count in sorted(types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {t}: {count}")

    # Sample entities
    print(f"\nSample entities:")
    for i, e in enumerate(result.entities[:5], 1):
        entity_type = e.get('entity_type', e.get('type', 'UNKNOWN'))
        entity_text = e.get('text', e.get('entity_text', ''))[:40]
        confidence = e.get('confidence', 0.0)
        print(f"  {i}. [{entity_type}] \"{entity_text}...\" (conf: {confidence:.2f})")

    # Sample relationships
    if result.relationships:
        print(f"\nSample relationships:")
        for i, r in enumerate(result.relationships[:5], 1):
            source = r.get('source_entity_id', '?')
            target = r.get('target_entity_id', '?')
            rel_type = r.get('relationship_type', r.get('type', '?'))
            print(f"  {i}. {source} --[{rel_type}]--> {target}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("tests/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    result_file = results_dir / f"pipeline_test_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'document': 'Rahimi.pdf',
            'text_length': len(test_text),
            'duration_seconds': duration,
            'strategy': result.strategy.value,
            'waves_executed': result.waves_executed,
            'tokens_used': result.tokens_used,
            'entity_count': len(result.entities),
            'relationship_count': len(result.relationships),
            'entity_types': types,
            'entities': result.entities[:10],  # First 10
            'relationships': result.relationships[:5]  # First 5
        }, f, indent=2)

    print(f"\n✅ Results saved to: {result_file}")

    print(f"\n{'=' * 80}")
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
