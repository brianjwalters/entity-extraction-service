#!/usr/bin/env python3
"""Test smart chunking with different document sizes"""

import requests
import time
import json

def create_large_doc(size_chars):
    """Create a test document of specified size"""
    base = """
    In the matter of State v. Anderson, Case No. 2023-CR-12345, the Washington Supreme Court
    addressed constitutional implications of RCW 9A.44.073. Judge Martinez, writing for the 
    majority, held that the statute violated the Fourth Amendment. The defendant, represented by 
    Attorney Sarah Johnson of Johnson & Associates Law Firm, successfully argued that the 
    $50,000 bail amount was excessive under the Eighth Amendment. The Court cited United States v. 
    Salerno, 481 U.S. 739 (1987) and Stack v. Boyle, 342 U.S. 1 (1951) in its analysis.
    The case was remanded to King County Superior Court for further proceedings scheduled on 
    January 15, 2024. Judge Thompson will preside over the remand proceedings.
    """
    
    result = ""
    counter = 0
    while len(result) < size_chars:
        counter += 1
        # Vary the content slightly
        modified = base.replace("Anderson", f"Anderson-{counter}")
        modified = modified.replace("12345", f"{12345 + counter}")
        modified = modified.replace("Martinez", f"Martinez-{counter % 5}")
        result += modified + "\n\n"
    
    return result[:size_chars]

def test_document_size(size_chars, label):
    """Test extraction with a document of specified size"""
    print(f"\n{'='*60}")
    print(f"Testing {label} document ({size_chars:,} characters)")
    print(f"{'='*60}")
    
    content = create_large_doc(size_chars)
    
    # Test extraction
    start_time = time.time()
    try:
        response = requests.post(
            "http://localhost:8007/api/v1/extract",
            json={
                "content": content,
                "document_id": f"test_{label}_{int(time.time())}",
                "extraction_mode": "ai_enhanced",
                "confidence_threshold": 0.7
            },
            timeout=120
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✓ Success!")
            print(f"  - Extraction time: {elapsed:.2f} seconds")
            print(f"  - Entities found: {result.get('total_entities', 0)}")
            print(f"  - Processing time (API): {result.get('processing_time_ms', 0)/1000:.2f}s")
            print(f"  - Characters per second: {size_chars/elapsed:.0f}")
            
            # Check if chunking likely occurred
            if size_chars > 50000:
                if elapsed > 10:
                    print(f"  - Smart chunking: LIKELY (time > 10s)")
                else:
                    print(f"  - Smart chunking: UNLIKELY (time < 10s)")
            else:
                print(f"  - Smart chunking: NOT EXPECTED (< 50K chars)")
                
            # Show some sample entities
            entities = result.get('entities', [])[:3]
            if entities:
                print(f"  - Sample entities:")
                for e in entities:
                    print(f"    • {e['entity_type']}: {e['text'][:50]}...")
                    
            return elapsed, result.get('total_entities', 0)
            
        else:
            print(f"✗ Failed with status {response.status_code}")
            print(f"  Error: {response.text[:200]}")
            return None, 0
            
    except requests.Timeout:
        elapsed = time.time() - start_time
        print(f"✗ Request timed out after {elapsed:.1f} seconds")
        return None, 0
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None, 0

def main():
    print("\n" + "="*60)
    print("SMART CHUNKING THRESHOLD TEST")
    print("Testing document sizes around the 50K character threshold")
    print("="*60)
    
    # Test different document sizes
    test_cases = [
        (5_000, "Small"),
        (25_000, "Medium"),
        (45_000, "Below threshold"),
        (50_000, "At threshold"),
        (55_000, "Above threshold"),
        (75_000, "Large"),
        (100_000, "Very large")
    ]
    
    results = []
    
    for size, label in test_cases:
        time_taken, entities = test_document_size(size, label)
        if time_taken:
            results.append({
                "size": size,
                "label": label,
                "time": time_taken,
                "entities": entities,
                "chars_per_sec": size / time_taken
            })
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if results:
        print("\n| Size (chars) | Label | Time (s) | Entities | Chars/sec |")
        print("|--------------|-------|----------|----------|-----------|")
        for r in results:
            print(f"| {r['size']:12,} | {r['label']:15} | {r['time']:8.2f} | {r['entities']:8} | {r['chars_per_sec']:9.0f} |")
        
        # Check for chunking behavior
        below_50k = [r for r in results if r['size'] < 50000]
        above_50k = [r for r in results if r['size'] >= 50000]
        
        if below_50k and above_50k:
            avg_speed_below = sum(r['chars_per_sec'] for r in below_50k) / len(below_50k)
            avg_speed_above = sum(r['chars_per_sec'] for r in above_50k) / len(above_50k)
            
            print(f"\nAverage speed below 50K: {avg_speed_below:.0f} chars/sec")
            print(f"Average speed above 50K: {avg_speed_above:.0f} chars/sec")
            
            if avg_speed_above < avg_speed_below * 0.7:
                print("✓ Smart chunking appears to be working (significant slowdown above 50K)")
            else:
                print("⚠ Smart chunking may not be activating properly")
    
    # Save results
    output_file = f"/srv/luris/be/entity-extraction-service/tests/results/chunking_test_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "test_cases": test_cases,
            "results": results,
            "timestamp": time.time()
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()