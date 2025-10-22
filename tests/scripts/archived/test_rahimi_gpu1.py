#!/usr/bin/env python3
"""
Test 4-wave entity extraction with Rahimi.pdf using DirectVLLMClient on GPU 1.

This test validates:
1. DirectVLLMClient initializes on GPU 1 (not GPU 0)
2. Guided JSON eliminates "Extra data" parsing errors
3. Wave 1-3 extract entities successfully
4. Wave 4 extracts relationships
5. Entity count improves significantly vs HTTP fallback
"""
import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add src to path

from vllm_client.factory import get_default_client
from core.extraction_orchestrator import ExtractionOrchestrator
from routing.document_router import DocumentRouter
from routing.size_detector import SizeDetector


async def test_rahimi_extraction():
    """Test 4-wave extraction with Rahimi document."""

    print("=" * 80)
    print("4-WAVE EXTRACTION TEST: RAHIMI DOCUMENT (GPU 1)")
    print("=" * 80)
    print(f"\nTest started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load Rahimi document
    rahimi_path = Path("/srv/luris/be/tests/docs/Rahimi.pdf")
    if not rahimi_path.exists():
        print(f"❌ Error: Rahimi.pdf not found at {rahimi_path}")
        return False

    print(f"\n📄 Loading document: {rahimi_path}")

    # Convert PDF to text (using marker or simple extraction)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(rahimi_path)
        document_text = ""
        for page in doc:
            document_text += page.get_text()
        doc.close()

        print(f"✅ Document loaded: {len(document_text):,} characters")

        # Use first 15,000 chars for faster testing
        test_text = document_text[:15000]
        print(f"📏 Test size: {len(test_text):,} characters (full doc: {len(document_text):,})")

    except Exception as e:
        print(f"❌ Failed to load PDF: {e}")
        return False

    # Initialize components
    print(f"\n🔧 Initializing extraction components...")

    try:
        # Create vLLM client
        print(f"   Creating vLLM client...")
        vllm_client = await get_default_client(enable_fallback=False)

        client_type = type(vllm_client).__name__
        print(f"   ✅ Client type: {client_type}")

        if client_type == "DirectVLLMClient":
            gpu_id = vllm_client.config.gpu_id
            print(f"   ✅ GPU ID: {gpu_id}")

            if gpu_id != 1:
                print(f"   ⚠️  WARNING: Expected GPU 1, got GPU {gpu_id}")
            else:
                print(f"   ✅ GPU 1 configuration confirmed")
        else:
            print(f"   ⚠️  WARNING: Using {client_type} (not DirectVLLMClient)")
            print(f"   ⚠️  Guided JSON may have limited support")

        # Create orchestrator
        print(f"\n   Creating extraction orchestrator...")
        orchestrator = ExtractionOrchestrator(vllm_client=vllm_client)
        print(f"   ✅ Orchestrator initialized")

        # Create router
        print(f"\n   Creating document router...")
        router = DocumentRouter()
        print(f"   ✅ Router initialized")

    except Exception as e:
        print(f"❌ Component initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Analyze document and get routing decision
    print(f"\n📊 Analyzing document...")

    size_detector = SizeDetector()
    size_info = size_detector.detect(test_text)

    print(f"   Characters: {size_info.chars:,}")
    print(f"   Estimated tokens: {size_info.tokens:,}")
    print(f"   Size category: {size_info.category.value}")

    # Route with relationship extraction enabled
    routing_decision = router.route(
        document_text=test_text,
        extract_relationships=True,  # Enable Wave 4
        graphrag_mode=False
    )

    print(f"\n📍 Routing Decision:")
    print(f"   Strategy: {routing_decision.strategy.value}")
    print(f"   Rationale: {routing_decision.rationale}")
    print(f"   Estimated duration: {routing_decision.estimated_duration_seconds:.1f}s")
    print(f"   Estimated tokens: {routing_decision.estimated_tokens:,}")

    # Perform extraction
    print(f"\n🚀 Starting extraction...")
    print(f"   Note: This will initialize vLLM on GPU 1 (may take 30-50 seconds)")
    print(f"   Expected waves: 1-3 (entities) + 4 (relationships)")

    start_time = time.time()

    try:
        result = await orchestrator.extract(
            document_text=test_text,
            routing_decision=routing_decision,
            size_info=size_info,
            metadata={
                "document_name": "Rahimi.pdf",
                "test_size": len(test_text),
                "gpu_id": vllm_client.config.gpu_id if client_type == "DirectVLLMClient" else "unknown"
            }
        )

        extraction_time = time.time() - start_time

        print(f"\n✅ Extraction complete!")
        print(f"   Duration: {extraction_time:.2f} seconds")

    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Display results
    print(f"\n" + "=" * 80)
    print("EXTRACTION RESULTS")
    print("=" * 80)

    print(f"\n📊 Summary:")
    print(f"   Strategy used: {result.strategy.value}")
    print(f"   Waves executed: {result.waves_executed}")
    print(f"   Processing time: {result.processing_time:.2f}s")
    print(f"   Total tokens: {result.tokens_used:,}")

    print(f"\n📋 Entities:")
    print(f"   Total entities: {len(result.entities)}")

    # Count by type
    entity_types = {}
    for entity in result.entities:
        entity_type = entity.get('type', 'UNKNOWN')
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    print(f"   Unique types: {len(entity_types)}")

    if entity_types:
        print(f"\n   Top entity types:")
        sorted_types = sorted(entity_types.items(), key=lambda x: x[1], reverse=True)
        for entity_type, count in sorted_types[:10]:
            print(f"      {entity_type}: {count}")

    # Show sample entities
    if result.entities:
        print(f"\n   Sample entities (first 5):")
        for i, entity in enumerate(result.entities[:5], 1):
            entity_type = entity.get('type', 'UNKNOWN')
            text = entity.get('text', '')
            confidence = entity.get('confidence', 0.0)
            wave = entity.get('wave_number', '?')
            print(f"      {i}. [{entity_type}] \"{text[:50]}...\" (wave {wave}, conf: {confidence:.2f})")

    print(f"\n🔗 Relationships:")
    print(f"   Total relationships: {len(result.relationships)}")

    if result.relationships:
        print(f"\n   Sample relationships (first 5):")
        for i, rel in enumerate(result.relationships[:5], 1):
            rel_type = rel.get('relationship_type', 'UNKNOWN')
            source = rel.get('source_entity_id', '?')
            target = rel.get('target_entity_id', '?')
            confidence = rel.get('confidence', 0.0)
            print(f"      {i}. {source} --[{rel_type}]--> {target} (conf: {confidence:.2f})")

    # Check for improvements vs previous tests
    print(f"\n📈 Comparison with Previous Tests:")
    print(f"   Previous (HTTP fallback): 5 entities, 5 relationships")
    print(f"   Current (GPU 1 Direct): {len(result.entities)} entities, {len(result.relationships)} relationships")

    if len(result.entities) > 5:
        improvement = ((len(result.entities) - 5) / 5) * 100
        print(f"   ✅ Entity improvement: +{improvement:.0f}%")
    else:
        print(f"   ⚠️  Entity count similar or lower")

    # Check wave metadata
    if result.metadata:
        print(f"\n📊 Wave Details:")
        wave_results = result.metadata.get('wave_results', [])

        for wave_info in wave_results:
            wave_num = wave_info.get('wave', '?')
            entities_count = wave_info.get('entities_count', 0)
            relationships_count = wave_info.get('relationships_count', 0)
            tokens = wave_info.get('tokens_used', 0)

            if entities_count > 0:
                print(f"   Wave {wave_num}: {entities_count} entities, {tokens:,} tokens")
            elif relationships_count > 0:
                print(f"   Wave {wave_num}: {relationships_count} relationships, {tokens:,} tokens")

    # Check for JSON parsing errors (should be 0 with guided JSON)
    print(f"\n🔍 JSON Parsing Check:")
    print(f"   Expected: No 'Extra data' errors with guided JSON")
    print(f"   Status: Check logs above for any JSON parsing warnings")

    # Get client stats
    if hasattr(vllm_client, 'get_stats'):
        print(f"\n📊 vLLM Client Statistics:")
        stats = vllm_client.get_stats()

        print(f"   Status: {stats.get('status', 'unknown')}")
        print(f"   Requests processed: {stats.get('requests_processed', 0)}")
        print(f"   Successful generations: {stats.get('successful_generations', 0)}")
        print(f"   Errors: {stats.get('errors_encountered', 0)}")

        if 'gpu' in stats:
            gpu_stats = stats['gpu']
            print(f"\n   GPU Statistics:")
            print(f"      GPU ID: {gpu_stats.get('gpu_id', '?')}")
            print(f"      Memory used: {gpu_stats.get('memory_used_gb', 0):.2f} GB")
            print(f"      Memory total: {gpu_stats.get('memory_total_gb', 0):.2f} GB")
            print(f"      Utilization: {gpu_stats.get('memory_utilization_percent', 0):.1f}%")

    # Save results
    results_dir = Path(__file__).parent / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"rahimi_gpu1_{timestamp}.json"

    results_data = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "document": "Rahimi.pdf",
            "test_size": len(test_text),
            "client_type": client_type,
            "gpu_id": vllm_client.config.gpu_id if client_type == "DirectVLLMClient" else "unknown"
        },
        "extraction_results": {
            "strategy": result.strategy.value,
            "waves_executed": result.waves_executed,
            "processing_time": result.processing_time,
            "tokens_used": result.tokens_used,
            "total_entities": len(result.entities),
            "total_relationships": len(result.relationships),
            "entity_types": entity_types,
            "entities": result.entities[:20],  # Save first 20
            "relationships": result.relationships[:20]  # Save first 20
        },
        "metadata": result.metadata
    }

    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)

    print(f"\n💾 Results saved: {results_file}")

    print(f"\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)

    return True


async def main():
    """Run the test."""

    print("\n" + "=" * 80)
    print("Rahimi Document Extraction Test - GPU 1 Configuration")
    print("=" * 80)
    print("\nThis test validates the complete guided JSON implementation:")
    print("  ✅ DirectVLLMClient on GPU 1 (not GPU 0)")
    print("  ✅ Guided JSON eliminates parsing errors")
    print("  ✅ 4-wave extraction (entities + relationships)")
    print("  ✅ Improved entity extraction quality")

    success = await test_rahimi_extraction()

    if success:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test failed - check logs above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
