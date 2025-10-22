#!/usr/bin/env python3
"""
Test DirectVLLMClient on GPU 1 with complete CUDA isolation.

This test sets CUDA_VISIBLE_DEVICES BEFORE any imports to ensure
CUDA initializes on GPU 1 only.
"""

# STEP 1: Set CUDA_VISIBLE_DEVICES before ANY imports
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '1'
print(f"✅ Set CUDA_VISIBLE_DEVICES=1 BEFORE all imports")

# STEP 2: Now import everything else
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
    print("RAHIMI EXTRACTION TEST - GPU 1 ISOLATED")
    print("=" * 80)
    print(f"\nCUDA_VISIBLE_DEVICES = {os.environ.get('CUDA_VISIBLE_DEVICES')}")

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

    # Create client
    print("\nCreating vLLM client...")
    print("Note: CUDA should see GPU 1 as device 0 due to CUDA_VISIBLE_DEVICES")

    client = await get_default_client(enable_fallback=False)
    print(f"Client type: {type(client).__name__}")

    # Check GPU assignment
    if hasattr(client, 'config'):
        gpu_id = client.config.gpu_id
        print(f"Config GPU ID: {gpu_id}")
        print(f"Expected: GPU 1 (physical) = GPU 0 (CUDA)")

    # Create orchestrator
    orchestrator = ExtractionOrchestrator(vllm_client=client)

    # Route and analyze
    router = DocumentRouter()
    size_detector = SizeDetector()
    size_info = size_detector.detect(test_text)
    routing = router.route(test_text, extract_relationships=True)

    print(f"\nStrategy: {routing.strategy.value}")
    print(f"Starting extraction...")

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
