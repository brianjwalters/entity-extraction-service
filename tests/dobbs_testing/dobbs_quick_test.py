#!/usr/bin/env python3
"""
Quick test focusing on regex extraction for Dobbs.pdf.
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path
from collections import Counter

# Service URLs
UPLOAD_URL = "http://localhost:8008/api/v1/upload"
EXTRACT_URL = "http://localhost:8007/api/v1/extract"

# Test configuration
DOBBS_PDF = "/srv/luris/be/tests/docs/dobbs.pdf"
OUTPUT_DIR = Path("/srv/luris/be/entity-extraction-service/tests/dobbs_testing/results")

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\nDobbs.pdf Extraction Test - {timestamp}")
    print("=" * 60)
    
    # 1. Upload document
    print("\n1. Uploading Dobbs.pdf...")
    with open(DOBBS_PDF, 'rb') as f:
        files = {'file': f}
        data = {
            'client_id': 'test_client_dobbs',
            'case_id': f'dobbs_quick_{timestamp}'
        }
        response = requests.post(UPLOAD_URL, files=files, data=data, timeout=120)
    
    if response.status_code != 200:
        print(f"✗ Upload failed: {response.text}")
        return
    
    upload_result = response.json()
    document_id = upload_result['document_id']
    markdown_content = upload_result['markdown_content']
    
    print(f"✓ Document uploaded: {document_id}")
    print(f"  Content length: {len(markdown_content):,} characters")
    
    # 2. Test regex extraction
    print("\n2. Testing regex extraction...")
    start_time = time.time()
    
    payload = {
        "document_id": document_id,
        "content": markdown_content,
        "extraction_mode": "regex",
        "confidence_threshold": 0.7
    }
    
    response = requests.post(EXTRACT_URL, json=payload, timeout=180)
    elapsed = time.time() - start_time
    
    if response.status_code != 200:
        print(f"✗ Extraction failed: {response.text}")
        return
    
    result = response.json()
    entities = result.get("entities", [])
    citations = result.get("citations", [])
    
    print(f"✓ Extraction completed in {elapsed:.2f}s")
    print(f"  Total entities: {len(entities)}")
    print(f"  Total citations: {len(citations)}")
    print(f"  Processing time: {result.get('processing_time_ms', 0)}ms")
    
    # 3. Analyze entity types
    print("\n3. Entity Type Analysis:")
    entity_types = Counter()
    for entity in entities:
        entity_types[entity.get("entity_type", "UNKNOWN")] += 1
    
    print(f"  Unique entity types: {len(entity_types)}")
    print("\n  Top 15 Entity Types:")
    for etype, count in entity_types.most_common(15):
        print(f"    - {etype}: {count}")
    
    # 4. Show sample entities
    print("\n4. Sample Entities (first 10):")
    for i, entity in enumerate(entities[:10], 1):
        text = entity.get("entity_text", "")[:60]
        etype = entity.get("entity_type", "UNKNOWN")
        conf = entity.get("confidence", 0)
        print(f"  {i}. [{etype}] {text}... (conf: {conf:.2f})")
    
    # 5. Save results
    results = {
        "timestamp": timestamp,
        "document_id": document_id,
        "content_length": len(markdown_content),
        "extraction_mode": "regex",
        "elapsed_time": elapsed,
        "total_entities": len(entities),
        "total_citations": len(citations),
        "unique_entity_types": len(entity_types),
        "entity_type_counts": dict(entity_types),
        "processing_time_ms": result.get("processing_time_ms", 0),
        "entities": entities[:100]  # Save first 100 for analysis
    }
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / f"dobbs_regex_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n5. Results saved to: {output_file}")
    
    # 6. Test hybrid mode if time permits
    print("\n6. Testing hybrid extraction (quick test)...")
    start_time = time.time()
    
    # Use only first 50k chars for hybrid to avoid timeout
    sample_content = markdown_content[:50000]
    payload = {
        "document_id": document_id,
        "content": sample_content,
        "extraction_mode": "hybrid",
        "confidence_threshold": 0.7
    }
    
    try:
        response = requests.post(EXTRACT_URL, json=payload, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            hybrid_result = response.json()
            print(f"✓ Hybrid extraction (sample) completed in {elapsed:.2f}s")
            print(f"  Entities found: {len(hybrid_result.get('entities', []))}")
        else:
            print(f"✗ Hybrid extraction failed: {response.status_code}")
    except requests.Timeout:
        print(f"✗ Hybrid extraction timed out after 60s")
    except Exception as e:
        print(f"✗ Hybrid extraction error: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    main()