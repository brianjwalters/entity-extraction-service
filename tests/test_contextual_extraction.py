#!/usr/bin/env python3
"""
Test script for contextual entity extraction with Rahimi document content.
Tests coreference resolution, semantic similarity, and entity relationships.
"""

import json
import requests
import time
from typing import Dict, List, Any
from datetime import datetime

# Service configuration
BASE_URL = "http://localhost:8007/api/v1"
HEADERS = {"Content-Type": "application/json"}

# Test documents with various entity types that have patterns
TEST_DOCUMENTS = [
    {
        "id": "test_judges_attorneys",
        "content": """
        District Judge Williams presided over the case. Attorney John Smith, Esq. 
        represented the plaintiff. Counsel Mary Johnson appeared for the defendant.
        Judge Williams ruled in favor of the plaintiff. Smith argued that his client
        deserved compensation. The judge agreed with attorney Smith's arguments.
        """,
        "entity_types": ["JUDGE", "ATTORNEY", "PARTY"],
        "expected_entities": ["District Judge Williams", "Attorney John Smith", "Counsel Mary Johnson"]
    },
    {
        "id": "test_parties_motions",
        "content": """
        Plaintiff ABC Corporation filed a motion for summary judgment against 
        Defendant XYZ Inc. The Appellant seeks reversal of the lower court's decision.
        Appellee opposes the motion. The motion to dismiss was denied. 
        Plaintiff's motion to compel discovery was granted.
        """,
        "entity_types": ["PLAINTIFF", "DEFENDANT", "APPELLANT", "APPELLEE", "MOTION"],
        "expected_entities": ["Plaintiff", "Defendant", "Appellant", "Appellee", "motion for summary judgment"]
    },
    {
        "id": "test_government_entities",
        "content": """
        The United States brought this action under federal law. The FBI conducted 
        the investigation. Department of Justice attorneys prosecuted the case.
        The SEC filed enforcement proceedings. State of California intervened.
        """,
        "entity_types": ["GOVERNMENT_ENTITY", "FEDERAL_AGENCY"],
        "expected_entities": ["United States", "FBI", "Department of Justice", "SEC", "State of California"]
    },
    {
        "id": "test_rahimi_content",
        "content": """
        In Rahimi v. State Bar, District Judge Thompson ruled that attorney 
        disciplinary proceedings require due process. Attorney Michael Rahimi, Esq.,
        the Appellant, was represented by Johnson & Associates Law Firm. 
        The State Bar, as Appellee, argued its position. Judge Thompson emphasized
        that Mr. Rahimi deserved fair proceedings. The attorney's case was distinguished
        from earlier precedents. Johnson & Associates filed a motion to dismiss.
        """,
        "entity_types": ["JUDGE", "ATTORNEY", "LAW_FIRM", "APPELLANT", "APPELLEE", "MOTION", "PARTY"],
        "expected_entities": ["District Judge Thompson", "Attorney Michael Rahimi", "Johnson & Associates"]
    }
]

def test_contextual_extraction(document: Dict[str, Any]) -> Dict[str, Any]:
    """Test contextual extraction for a single document."""
    
    # Prepare request
    request_data = {
        "document_id": document["id"],
        "content": document["content"],
        "entity_types": document["entity_types"],
        "confidence_threshold": 0.3,  # Lower threshold to catch more entities
        "context_features": {
            "coreference_resolution": True,
            "semantic_similarity": True,
            "entity_relationships": True,
            "context_aware_confidence": True
        }
    }
    
    # Test contextual endpoint
    print(f"\n{'='*60}")
    print(f"Testing document: {document['id']}")
    print(f"Entity types: {', '.join(document['entity_types'])}")
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/extract/contextual",
        headers=HEADERS,
        json=request_data
    )
    processing_time = (time.time() - start_time) * 1000
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Contextual extraction successful")
        print(f"  Processing time: {processing_time:.2f}ms")
        print(f"  Total entities found: {result.get('total_entities', 0)}")
        
        # Display entities
        entities = result.get('entities', [])
        if entities:
            print(f"\n  Entities found:")
            for entity in entities[:10]:  # Show first 10
                print(f"    - {entity.get('text', 'N/A')} ({entity.get('entity_type', 'N/A')}) "
                      f"[confidence: {entity.get('confidence_score', 0):.2f}]")
        
        # Display relationships
        relationships = result.get('relationships', [])
        if relationships:
            print(f"\n  Relationships found: {len(relationships)}")
            for rel in relationships[:5]:  # Show first 5
                print(f"    - {rel.get('type', 'N/A')}: {rel.get('source', 'N/A')} → {rel.get('target', 'N/A')}")
        
        # Display unpatterned entities
        unpatterned = result.get('unpatterned_entities', [])
        if unpatterned:
            print(f"\n  Unpatterned entities: {len(unpatterned)}")
            for ent in unpatterned[:5]:  # Show first 5
                print(f"    - {ent.get('text', 'N/A')} ({ent.get('entity_type', 'N/A')})")
        
        return result
    else:
        print(f"✗ Extraction failed: {response.status_code}")
        print(f"  Error: {response.text[:200]}")
        return None

def test_standard_extraction(document: Dict[str, Any]) -> Dict[str, Any]:
    """Test standard extraction for comparison."""
    
    request_data = {
        "document_id": document["id"] + "_standard",
        "content": document["content"],
        "extraction_mode": "regex",
        "entity_types": document["entity_types"],
        "confidence_threshold": 0.3
    }
    
    response = requests.post(
        f"{BASE_URL}/extract",
        headers=HEADERS,
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n  Standard extraction comparison:")
        print(f"    Entities found: {result.get('total_entities', 0)}")
        return result
    return None

def analyze_results(results: List[Dict[str, Any]]) -> None:
    """Analyze and summarize test results."""
    
    print(f"\n{'='*60}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r is not None)
    total_entities = sum(r.get('total_entities', 0) for r in results if r)
    total_relationships = sum(len(r.get('relationships', [])) for r in results if r)
    total_unpatterned = sum(len(r.get('unpatterned_entities', [])) for r in results if r)
    
    print(f"Tests completed: {successful_tests}/{total_tests}")
    print(f"Total entities extracted: {total_entities}")
    print(f"Total relationships found: {total_relationships}")
    print(f"Total unpatterned entities: {total_unpatterned}")
    
    if results:
        avg_confidence = sum(r.get('overall_confidence', 0) for r in results if r) / len([r for r in results if r])
        print(f"Average confidence: {avg_confidence:.2f}")
    
    # Context-aware features analysis
    print(f"\nContext-Aware Features:")
    for result in results:
        if result:
            print(f"  {result.get('document_id', 'N/A')}:")
            print(f"    - Context resolution rate: {result.get('context_resolution_rate', 0):.1%}")
            print(f"    - Relationship extraction rate: {result.get('relationship_extraction_rate', 0):.1%}")
            print(f"    - Unpatterned detection rate: {result.get('unpatterned_detection_rate', 0):.1%}")

def save_results(results: List[Dict[str, Any]], filename: str) -> None:
    """Save test results to file."""
    
    output = {
        "test_timestamp": datetime.now().isoformat(),
        "test_type": "contextual_extraction",
        "results": results,
        "summary": {
            "total_tests": len(results),
            "successful_tests": sum(1 for r in results if r is not None),
            "total_entities": sum(r.get('total_entities', 0) for r in results if r),
            "total_relationships": sum(len(r.get('relationships', [])) for r in results if r),
            "total_unpatterned": sum(len(r.get('unpatterned_entities', [])) for r in results if r)
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: {filename}")

def main():
    """Run all contextual extraction tests."""
    
    print("="*60)
    print("CONTEXTUAL ENTITY EXTRACTION TEST SUITE")
    print("="*60)
    print(f"Testing endpoint: {BASE_URL}/extract/contextual")
    print(f"Test documents: {len(TEST_DOCUMENTS)}")
    
    # Check service health
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code == 200:
            print("✓ Entity extraction service is healthy")
        else:
            print("✗ Service health check failed")
            return
    except Exception as e:
        print(f"✗ Cannot connect to service: {e}")
        return
    
    # Run tests
    results = []
    for document in TEST_DOCUMENTS:
        result = test_contextual_extraction(document)
        if result:
            # Also test standard extraction for comparison
            standard_result = test_standard_extraction(document)
            result['standard_comparison'] = standard_result
        results.append(result)
    
    # Analyze and save results
    analyze_results(results)
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/srv/luris/be/entity-extraction-service/tests/results/contextual_test_{timestamp}.json"
    save_results(results, output_file)
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60)

if __name__ == "__main__":
    main()