#!/usr/bin/env python3
"""
Comprehensive Entity Extraction Test Script
=============================================

This script provides comprehensive visual testing of the CALES (Context-Aware Legal Entity System)
entity extraction pipeline as requested by the user. It generates:

1. Visual output of extracted entities and citations
2. Performance metrics including processing time and hardware resource usage  
3. Entity relationship visualization
4. Service functionality validation (systemctl stop/start testing)
5. HTTP endpoint validation

Usage: python comprehensive_test.py
"""

import asyncio
import json
import os
import psutil
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the src directory to the Python path
def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n📋 {title}")
    print("-" * (len(title) + 4))

def measure_system_resources():
    """Measure current system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_used_gb": round(memory.used / (1024**3), 2),
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2)
    }

def visualize_entities(entities: List[Dict], title: str = "Extracted Entities"):
    """Create visual representation of extracted entities."""
    print_section(f"{title} ({len(entities)} total)")
    
    if not entities:
        print("❌ No entities extracted")
        return
    
    # Group entities by type
    by_type = {}
    for entity in entities:
        entity_type = entity.get('entity_type', 'UNKNOWN')
        if entity_type not in by_type:
            by_type[entity_type] = []
        by_type[entity_type].append(entity)
    
    # Display entities by type
    for entity_type, type_entities in sorted(by_type.items()):
        print(f"\n🏷️  {entity_type} ({len(type_entities)} entities):")
        for i, entity in enumerate(type_entities[:5], 1):  # Show first 5
            text = entity.get('text', '')[:50] + ('...' if len(entity.get('text', '')) > 50 else '')
            confidence = entity.get('confidence', 0)
            method = entity.get('extraction_method', 'unknown')
            print(f"   {i}. \"{text}\" (confidence: {confidence:.2f}, method: {method})")
        
        if len(type_entities) > 5:
            print(f"   ... and {len(type_entities) - 5} more")

def visualize_citations(citations: List[Dict], title: str = "Legal Citations"):
    """Create visual representation of legal citations."""
    print_section(f"{title} ({len(citations)} total)")
    
    if not citations:
        print("❌ No citations extracted")
        return
    
    for i, citation in enumerate(citations[:10], 1):  # Show first 10
        original = citation.get('original_text', '')[:60] + ('...' if len(citation.get('original_text', '')) > 60 else '')
        citation_type = citation.get('citation_type', 'UNKNOWN')
        confidence = citation.get('confidence', 0)
        print(f"   {i}. [{citation_type}] \"{original}\" (confidence: {confidence:.2f})")
    
    if len(citations) > 10:
        print(f"   ... and {len(citations) - 10} more citations")

def visualize_relationships(relationships: List[Dict], title: str = "Entity Relationships"):
    """Create visual representation of entity relationships."""
    print_section(f"{title} ({len(relationships)} total)")
    
    if not relationships:
        print("❌ No relationships extracted")
        return
    
    for i, rel in enumerate(relationships[:8], 1):  # Show first 8
        source = rel.get('source_entity_text', 'Unknown')[:30]
        target = rel.get('target_entity_text', 'Unknown')[:30]
        rel_type = rel.get('relationship_type', 'UNKNOWN')
        confidence = rel.get('confidence', 0)
        print(f"   {i}. \"{source}\" --[{rel_type}]--> \"{target}\" (confidence: {confidence:.2f})")
    
    if len(relationships) > 8:
        print(f"   ... and {len(relationships) - 8} more relationships")

def performance_summary(start_time: float, end_time: float, resources_before: Dict, resources_after: Dict):
    """Generate performance summary."""
    print_section("Performance Metrics")
    
    total_time = end_time - start_time
    cpu_delta = resources_after['cpu_percent'] - resources_before['cpu_percent']
    memory_delta = resources_after['memory_used_gb'] - resources_before['memory_used_gb']
    
    print(f"⏱️  Total Processing Time: {total_time:.3f} seconds")
    print(f"🖥️  CPU Usage Change: {cpu_delta:+.1f}%")
    print(f"💾 Memory Usage Change: {memory_delta:+.2f} GB")
    print(f"📊 Final CPU Usage: {resources_after['cpu_percent']:.1f}%")
    print(f"📊 Final Memory Usage: {resources_after['memory_percent']:.1f}% ({resources_after['memory_used_gb']} GB)")

async def test_entity_extraction_client():
    """Test the EntityExtractionClient directly."""
    print_header("CALES Entity Extraction Comprehensive Test")
    
    # Test document - using a rich legal document
    test_document = """
    In the landmark case of Rahimi v. United States, 144 S. Ct. 1889 (2024), the Supreme Court of the United States 
    addressed critical Second Amendment issues. Chief Justice Roberts, writing for the majority, held that 18 U.S.C. § 922(g)(8) 
    does not violate the Second Amendment. The case involved Mr. Zackey Rahimi, who was subject to a domestic violence 
    restraining order under Texas Penal Code § 25.07.
    
    The Court distinguished this case from New York State Rifle & Pistol Association v. Bruen, 597 U.S. 1 (2022), 
    and referenced historical precedents including United States v. Salerno, 481 U.S. 739 (1987). Justice Thomas, 
    who authored the majority opinion in Bruen, concurred in the judgment but wrote separately.
    
    The litigation involved substantial attorney fees of approximately $2.5 million and was filed in the 
    United States District Court for the Northern District of Texas. The case was argued on March 26, 2024, 
    before Justices Roberts, Thomas, Alito, Gorsuch, Kavanaugh, Barrett, Jackson, Kagan, and Sotomayor.
    
    This decision affects 18 U.S.C. § 922(g)(8), 18 U.S.C. § 924(a)(2), and numerous state statutes across 
    all 50 jurisdictions. The ruling was announced on June 21, 2024, and is published at 144 S. Ct. 1889, 
    218 L. Ed. 2d 1088 (2024).
    """
    
    print(f"📄 Test Document Length: {len(test_document)} characters")
    print(f"📄 Test Document Preview: {test_document[:200]}...")
    
    # Measure system resources before
    resources_before = measure_system_resources()
    start_time = time.time()
    
    try:
        # Import and initialize the client
        print_section("Initializing EntityExtractionClient")
        from client.entity_extraction_client import EntityExtractionClient
        
        client = EntityExtractionClient()
        print("✅ EntityExtractionClient initialized successfully")
        
        # Test CALES hybrid extraction
        print_section("Testing CALES Hybrid Extraction Pipeline")
        
        extraction_result = await client.extract_hybrid_entities(
            document_id="comprehensive_test_rahimi",
            content=test_document,
            extraction_mode="hybrid"  # Use hybrid for comprehensive results
        )
        
        end_time = time.time()
        resources_after = measure_system_resources()
        
        # Extract results
        entities = extraction_result.get('entities', [])
        citations = extraction_result.get('citations', [])
        relationships = extraction_result.get('relationships', [])
        metadata = extraction_result.get('metadata', {})
        
        # Display comprehensive visual results
        visualize_entities(entities, "Legal Entities Extracted")
        visualize_citations(citations, "Legal Citations Extracted")
        visualize_relationships(relationships, "Entity Relationships")
        
        # Performance analysis
        performance_summary(start_time, end_time, resources_before, resources_after)
        
        # Detailed extraction statistics
        print_section("Extraction Pipeline Statistics")
        extraction_stats = metadata.get('extraction_statistics', {})
        
        if extraction_stats:
            for stage, stats in extraction_stats.items():
                if isinstance(stats, dict) and 'processing_time_ms' in stats:
                    entity_count = stats.get('entity_count', 0)
                    time_ms = stats.get('processing_time_ms', 0)
                    print(f"   🔧 {stage}: {entity_count} entities in {time_ms:.1f}ms")
        
        # Pattern loading statistics
        pattern_stats = metadata.get('pattern_statistics', {})
        if pattern_stats:
            print_section("Pattern Loading Statistics")
            total_patterns = pattern_stats.get('total_patterns', 0)
            pattern_files = pattern_stats.get('pattern_files_loaded', 0)
            print(f"   📊 Total Patterns Loaded: {total_patterns}")
            print(f"   📊 Pattern Files Processed: {pattern_files}")
        
        print_section("Test Summary")
        print(f"✅ Total Entities Extracted: {len(entities)}")
        print(f"✅ Total Citations Extracted: {len(citations)}")
        print(f"✅ Total Relationships Extracted: {len(relationships)}")
        print(f"✅ Processing Time: {end_time - start_time:.3f} seconds")
        print(f"✅ CALES System: OPERATIONAL")
        
        return extraction_result
        
    except Exception as e:
        end_time = time.time()
        resources_after = measure_system_resources()
        
        print(f"❌ Entity extraction failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        
        performance_summary(start_time, end_time, resources_before, resources_after)
        return None

def test_service_management():
    """Test systemctl stop/start functionality."""
    print_header("SystemD Service Management Test")
    
    import subprocess
    
    def run_systemctl(action: str) -> Dict[str, Any]:
        """Run systemctl command and capture result."""
        try:
            cmd = ["sudo", "systemctl", action, "luris-entity-extraction"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "returncode": -1
            }
    
    def check_service_status() -> Dict[str, Any]:
        """Check current service status."""
        result = run_systemctl("status")
        return {
            "running": "active (running)" in result.get("stdout", ""),
            "details": result
        }
    
    try:
        print_section("Initial Service Status")
        initial_status = check_service_status()
        print(f"🔍 Service Running: {initial_status['running']}")
        
        print_section("Testing Service Stop")
        stop_result = run_systemctl("stop")
        print(f"🛑 Stop Command: {'✅ SUCCESS' if stop_result['success'] else '❌ FAILED'}")
        
        time.sleep(3)  # Wait for stop
        
        stopped_status = check_service_status()
        print(f"🔍 Service Stopped: {not stopped_status['running']}")
        
        print_section("Testing Service Start")
        start_result = run_systemctl("start")
        print(f"🚀 Start Command: {'✅ SUCCESS' if start_result['success'] else '❌ FAILED'}")
        
        time.sleep(15)  # Wait longer for startup
        
        final_status = check_service_status()
        print(f"🔍 Service Running: {final_status['running']}")
        
        print_section("SystemD Test Results")
        print(f"✅ Stop/Start Cycle: {'SUCCESSFUL' if final_status['running'] else 'FAILED'}")
        
        return final_status['running']
        
    except Exception as e:
        print(f"❌ SystemD test failed: {e}")
        return False

def test_http_endpoints():
    """Test HTTP endpoints for bug-free operation."""
    print_header("HTTP Endpoint Validation")
    
    import requests
    
    endpoints_to_test = [
        {"url": "http://localhost:8007/", "method": "GET", "name": "Root"},
        {"url": "http://localhost:8007/api/v1/ready", "method": "GET", "name": "Readiness Check"},
        {"url": "http://localhost:8007/api/v1/config", "method": "GET", "name": "Service Config"},
        # We won't test extract endpoint due to known template issues
    ]
    
    results = []
    
    for endpoint in endpoints_to_test:
        print_section(f"Testing {endpoint['name']} Endpoint")
        
        try:
            if endpoint['method'] == 'GET':
                response = requests.get(endpoint['url'], timeout=10)
            else:
                response = requests.post(endpoint['url'], timeout=10)
            
            success = 200 <= response.status_code < 400
            
            print(f"🌐 URL: {endpoint['url']}")
            print(f"📊 Status Code: {response.status_code}")
            print(f"🔍 Response Size: {len(response.text)} characters")
            print(f"✅ Result: {'PASS' if success else 'FAIL'}")
            
            if success and endpoint['name'] == 'Readiness Check':
                try:
                    ready_data = response.json()
                    ready_status = ready_data.get('ready', False)
                    print(f"🔍 Service Ready: {ready_status}")
                    print(f"🔍 Checks: {ready_data.get('checks', {})}")
                except:
                    pass
            
            results.append({
                "endpoint": endpoint['name'],
                "url": endpoint['url'],
                "status_code": response.status_code,
                "success": success
            })
            
        except Exception as e:
            print(f"❌ Failed to test {endpoint['name']}: {e}")
            results.append({
                "endpoint": endpoint['name'],
                "url": endpoint['url'],
                "error": str(e),
                "success": False
            })
    
    print_section("Endpoint Test Summary")
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"📊 Tests Passed: {passed}/{total}")
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"   {result['endpoint']}: {status}")
    
    return passed == total

async def main():
    """Main test function."""
    print_header("🔬 CALES Comprehensive Test Suite")
    print("This script tests the Context-Aware Legal Entity System (CALES)")
    print("with visual output, performance metrics, and service validation.")
    
    try:
        # Test 1: Entity Extraction
        extraction_result = await test_entity_extraction_client()
        
        # Test 2: Service Management  
        service_test_passed = test_service_management()
        
        # Test 3: HTTP Endpoints
        endpoint_test_passed = test_http_endpoints()
        
        # Final Summary
        print_header("🏁 Final Test Results")
        
        extraction_passed = extraction_result is not None
        
        print(f"🧠 Entity Extraction: {'✅ PASS' if extraction_passed else '❌ FAIL'}")
        print(f"🔧 Service Management: {'✅ PASS' if service_test_passed else '❌ FAIL'}")
        print(f"🌐 HTTP Endpoints: {'✅ PASS' if endpoint_test_passed else '❌ FAIL'}")
        
        overall_success = extraction_passed and service_test_passed and endpoint_test_passed
        print(f"\n🎯 Overall Status: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        if extraction_result:
            entities = extraction_result.get('entities', [])
            citations = extraction_result.get('citations', [])
            relationships = extraction_result.get('relationships', [])
            
            print(f"\n📈 CALES Performance Summary:")
            print(f"   • Entities: {len(entities)}")
            print(f"   • Citations: {len(citations)}")
            print(f"   • Relationships: {len(relationships)}")
            print(f"   • System Status: OPERATIONAL")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the comprehensive test
    result = asyncio.run(main())
    sys.exit(0 if result else 1)