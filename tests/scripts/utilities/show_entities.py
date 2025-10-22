#!/usr/bin/env python3
"""
Display extracted entities from Rahimi test with detailed analysis.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'

import asyncio
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


from vllm_client.factory import get_default_client
from core.extraction_orchestrator import ExtractionOrchestrator
from routing.document_router import DocumentRouter
from routing.size_detector import SizeDetector


async def main():
    print("=" * 80)
    print("RAHIMI ENTITY EXTRACTION - DETAILED RESULTS")
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

    result = await orchestrator.extract(test_text, routing, size_info)

    # ========================================================================
    # DETAILED ENTITY ANALYSIS
    # ========================================================================

    print("=" * 80)
    print("ENTITY EXTRACTION RESULTS")
    print("=" * 80)
    print(f"\nTotal Entities: {len(result.entities)}")
    print(f"Total Relationships: {len(result.relationships)}")
    print(f"Waves Executed: {result.waves_executed}")
    print(f"Tokens Used: {result.tokens_used:,}")

    # Group entities by type
    entities_by_type = defaultdict(list)
    for entity in result.entities:
        entity_type = entity.get('type', 'UNKNOWN')
        entities_by_type[entity_type].append(entity)

    print(f"\n{'=' * 80}")
    print(f"ENTITY TYPES SUMMARY ({len(entities_by_type)} unique types)")
    print("=" * 80)

    # Sort by count
    sorted_types = sorted(entities_by_type.items(), key=lambda x: len(x[1]), reverse=True)

    for entity_type, entities in sorted_types:
        print(f"\n{entity_type}: {len(entities)} entities")
        print("-" * 60)

        # Show first 5 examples
        for i, entity in enumerate(entities[:5], 1):
            text = entity.get('text', '')
            confidence = entity.get('confidence', 0.0)
            entity_id = entity.get('id', 'N/A')

            # Truncate long text
            display_text = text if len(text) <= 60 else text[:57] + "..."

            print(f"  {i}. \"{display_text}\"")
            print(f"     ID: {entity_id} | Confidence: {confidence:.2f}")

        if len(entities) > 5:
            print(f"  ... and {len(entities) - 5} more")

    # ========================================================================
    # RELATIONSHIP ANALYSIS
    # ========================================================================

    if result.relationships:
        print(f"\n{'=' * 80}")
        print(f"RELATIONSHIP EXTRACTION RESULTS ({len(result.relationships)} relationships)")
        print("=" * 80)

        # Group relationships by type
        rels_by_type = defaultdict(list)
        for rel in result.relationships:
            rel_type = rel.get('relationship_type', 'UNKNOWN')
            rels_by_type[rel_type].append(rel)

        for rel_type, rels in sorted(rels_by_type.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n{rel_type}: {len(rels)} relationships")
            print("-" * 60)

            # Show first 5 examples
            for i, rel in enumerate(rels[:5], 1):
                source_id = rel.get('source_entity_id', '?')
                target_id = rel.get('target_entity_id', '?')
                confidence = rel.get('confidence', 0.0)

                # Find source and target entity text
                source_entity = next((e for e in result.entities if e.get('id') == source_id), None)
                target_entity = next((e for e in result.entities if e.get('id') == target_id), None)

                source_text = source_entity.get('text', source_id) if source_entity else source_id
                target_text = target_entity.get('text', target_id) if target_entity else target_id

                # Truncate long text
                if len(source_text) > 30:
                    source_text = source_text[:27] + "..."
                if len(target_text) > 30:
                    target_text = target_text[:27] + "..."

                print(f"  {i}. \"{source_text}\" --[{rel_type}]--> \"{target_text}\"")
                print(f"     Confidence: {confidence:.2f}")

            if len(rels) > 5:
                print(f"  ... and {len(rels) - 5} more")

    # ========================================================================
    # SAVE FULL RESULTS TO JSON
    # ========================================================================

    output_file = Path("rahimi_extraction_results.json")
    output_data = {
        "metadata": {
            "document": "Rahimi.pdf",
            "text_length": len(test_text),
            "timestamp": datetime.now().isoformat(),
            "strategy": result.strategy.value,
            "waves_executed": result.waves_executed,
            "tokens_used": result.tokens_used,
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

    print(f"\n{'=' * 80}")
    print(f"Full results saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
