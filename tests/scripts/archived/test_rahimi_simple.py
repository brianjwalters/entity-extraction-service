#!/usr/bin/env python3
"""
Simple Rahimi extraction test - minimal output, maximum results.
"""
# CRITICAL: Set CUDA_VISIBLE_DEVICES before ANY imports
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'  # Use both GPUs with tensor parallelism

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime


from vllm_client.factory import get_default_client
from core.extraction_orchestrator import ExtractionOrchestrator
from routing.document_router import DocumentRouter
from routing.size_detector import SizeDetector


async def main():
    print("=" * 80)
    print("RAHIMI EXTRACTION TEST - WITH GUIDED JSON IMPROVEMENTS")
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

    # Create Direct vLLM client (will use both GPUs with tensor parallelism)
    print("Creating Direct vLLM client (GPUs 0,1 with tensor parallelism)...")
    client = await get_default_client(enable_fallback=False)
    print(f"✅ Client created: {type(client).__name__}")

    # Create orchestrator
    orchestrator = ExtractionOrchestrator(vllm_client=client)

    # Route and analyze
    router = DocumentRouter()
    size_detector = SizeDetector()
    size_info = size_detector.detect(test_text)
    routing = router.route(test_text, extract_relationships=True)

    print(f"Strategy: {routing.strategy.value}")
    print(f"Extract Relationships: {routing.extract_relationships}")
    print(f"Expected Waves: 4 (Waves 1-3: entities, Wave 4: relationships)")
    print(f"\nStarting extraction...")

    start = time.time()
    result = await orchestrator.extract(test_text, routing, size_info)
    duration = time.time() - start

    print(f"\n{'=' * 80}")
    print("RESULTS")
    print("=" * 80)
    print(f"Duration: {duration:.1f}s")
    print(f"Strategy: {result.strategy.value}")
    print(f"Waves Executed: {result.waves_executed} (Expected: 4)")

    # Verify all 4 waves ran
    if result.waves_executed == 4:
        print("✅ All 4 waves executed successfully!")
    else:
        print(f"⚠️  WARNING: Expected 4 waves, got {result.waves_executed}")

    print(f"Tokens: {result.tokens_used:,}")
    print(f"Entities: {len(result.entities)}")
    print(f"Relationships: {len(result.relationships)}")

    # Temperature validation
    print(f"\n🌡️  Temperature Configuration:")
    from core.config import get_settings
    settings = get_settings()
    print(f"  Entity Temperature: {settings.extraction.entity_temperature}")
    print(f"  Relationship Temperature: {settings.extraction.relationship_temperature}")
    print(f"  vLLM Default Temperature: {settings.vllm_direct.vllm_temperature}")

    # Entity types
    types = {}
    for e in result.entities:
        t = e.get('type', 'UNKNOWN')
        types[t] = types.get(t, 0) + 1

    print(f"\nEntity types ({len(types)}):")
    for t, count in sorted(types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {t}: {count}")

    # Sample entities
    print(f"\nSample entities:")
    for i, e in enumerate(result.entities[:5], 1):
        print(f"  {i}. [{e.get('type')}] \"{e.get('text', '')[:40]}...\"")

    # Sample relationships
    if result.relationships:
        print(f"\nSample relationships:")
        for i, r in enumerate(result.relationships[:5], 1):
            print(f"  {i}. {r.get('source_entity_id', '?')} --[{r.get('relationship_type')}]--> {r.get('target_entity_id', '?')}")

    print(f"\n{'=' * 80}")
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
