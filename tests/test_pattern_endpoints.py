#!/usr/bin/env python3
"""
Test script for pattern-related endpoints in Entity Extraction Service.

This script verifies the functionality of:
- GET /patterns/detailed - Detailed pattern information
- GET /patterns/statistics - Comprehensive pattern analytics
- GET /entity-types - Entity types with pattern counts
- GET /entity-types/{entity_type} - Detailed info for specific entity type
"""

import asyncio
import json
from typing import Dict, Any
import httpx
from datetime import datetime

# Service configuration
SERVICE_URL = "http://localhost:8007"
API_PREFIX = "/api/v1"
BASE_URL = f"{SERVICE_URL}{API_PREFIX}"


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(key: str, value: Any, indent: int = 0):
    """Print an info line with consistent formatting."""
    spacing = "  " * indent
    print(f"{spacing}{Colors.YELLOW}{key}:{Colors.END} {value}")


async def test_health_check(client: httpx.AsyncClient) -> bool:
    """Test the health check endpoint."""
    print_header("Testing Health Check")
    
    try:
        response = await client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Service is {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False


async def test_patterns_detailed(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Test the /patterns/detailed endpoint."""
    print_header("Testing GET /patterns/detailed")
    
    results = {
        "endpoint": "/patterns/detailed",
        "tests": []
    }
    
    # Test 1: Get all patterns
    try:
        response = await client.get(f"{BASE_URL}/patterns/detailed", timeout=30.0)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved {data['total_patterns']} patterns")
            print_info("Categories", len(data.get('patterns_by_category', {})))
            print_info("Entity types", len(data.get('entity_types', [])))
            
            # Display sample patterns
            if data.get('patterns_by_category'):
                for category, patterns in list(data['patterns_by_category'].items())[:3]:
                    print_info(f"Category '{category}'", f"{len(patterns)} patterns", indent=1)
                    if patterns:
                        sample = patterns[0]
                        print_info("Sample pattern", sample.get('pattern_id', 'unknown'), indent=2)
                        print_info("Entity type", sample.get('entity_type', 'unknown'), indent=2)
                        print_info("Confidence", sample.get('confidence', 'N/A'), indent=2)
            
            results["tests"].append({
                "test": "Get all patterns",
                "status": "passed",
                "patterns_count": data['total_patterns']
            })
        else:
            print_error(f"Failed to get patterns: {response.status_code}")
            results["tests"].append({
                "test": "Get all patterns",
                "status": "failed",
                "error": f"Status code {response.status_code}"
            })
    except Exception as e:
        print_error(f"Error getting patterns: {e}")
        results["tests"].append({
            "test": "Get all patterns",
            "status": "failed",
            "error": str(e)
        })
    
    # Test 2: Filter by category
    try:
        response = await client.get(
            f"{BASE_URL}/patterns/detailed",
            params={"category": "case_citations"},
            timeout=30.0
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Filtered by category: {data['total_patterns']} patterns")
            results["tests"].append({
                "test": "Filter by category",
                "status": "passed",
                "filtered_count": data['total_patterns']
            })
        else:
            print_error(f"Failed to filter by category: {response.status_code}")
            results["tests"].append({
                "test": "Filter by category",
                "status": "failed",
                "error": f"Status code {response.status_code}"
            })
    except Exception as e:
        print_error(f"Error filtering by category: {e}")
        results["tests"].append({
            "test": "Filter by category",
            "status": "failed",
            "error": str(e)
        })
    
    # Test 3: Filter by entity type
    try:
        response = await client.get(
            f"{BASE_URL}/patterns/detailed",
            params={"entity_type": "JUDGE"},
            timeout=30.0
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Filtered by entity type: {data['total_patterns']} patterns")
            results["tests"].append({
                "test": "Filter by entity type",
                "status": "passed",
                "filtered_count": data['total_patterns']
            })
        else:
            print_error(f"Failed to filter by entity type: {response.status_code}")
            results["tests"].append({
                "test": "Filter by entity type",
                "status": "failed",
                "error": f"Status code {response.status_code}"
            })
    except Exception as e:
        print_error(f"Error filtering by entity type: {e}")
        results["tests"].append({
            "test": "Filter by entity type",
            "status": "failed",
            "error": str(e)
        })
    
    return results


async def test_patterns_statistics(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Test the /patterns/statistics endpoint."""
    print_header("Testing GET /patterns/statistics")
    
    results = {
        "endpoint": "/patterns/statistics",
        "tests": []
    }
    
    try:
        response = await client.get(f"{BASE_URL}/patterns/statistics", timeout=30.0)
        if response.status_code == 200:
            data = response.json()
            print_success("Retrieved pattern statistics")
            
            # Display summary
            summary = data.get('summary', {})
            print_info("Total patterns", summary.get('total_patterns', 0))
            print_info("Total pattern groups", summary.get('total_pattern_groups', 0))
            print_info("Entity types covered", summary.get('covered_entity_types', 0))
            print_info("Average confidence", f"{summary.get('average_confidence', 0):.2f}")
            
            # Display jurisdiction breakdown
            jurisdiction = data.get('jurisdiction_breakdown', {})
            print_info("Jurisdiction breakdown", "", indent=1)
            print_info("Federal", jurisdiction.get('federal', 0), indent=2)
            print_info("State", jurisdiction.get('total_state_patterns', 0), indent=2)
            print_info("International", jurisdiction.get('international', 0), indent=2)
            
            # Display Bluebook compliance
            bluebook = data.get('bluebook_compliance', {})
            print_info("Bluebook compliance", "", indent=1)
            print_info("22nd Edition", bluebook.get('bluebook_22nd_edition', 0), indent=2)
            print_info("21st Edition", bluebook.get('bluebook_21st_edition', 0), indent=2)
            print_info("Compliance %", f"{bluebook.get('compliance_percentage', 0):.1f}%", indent=2)
            
            # Display coverage analysis
            coverage = data.get('coverage_analysis', {})
            print_info("Coverage analysis", "", indent=1)
            print_info("Coverage %", f"{coverage.get('coverage_percentage', 0):.1f}%", indent=2)
            print_info("High coverage types", len(coverage.get('high_coverage_types', [])), indent=2)
            print_info("Low coverage types", len(coverage.get('low_coverage_types', [])), indent=2)
            
            # Display library health
            health = data.get('library_health', {})
            print_info("Library health", health.get('status', 'unknown'), indent=1)
            if health.get('issues'):
                for issue in health['issues'][:3]:
                    print_info("Issue", issue, indent=2)
            
            results["tests"].append({
                "test": "Get pattern statistics",
                "status": "passed",
                "total_patterns": summary.get('total_patterns', 0),
                "library_health": health.get('status', 'unknown')
            })
        else:
            print_error(f"Failed to get statistics: {response.status_code}")
            results["tests"].append({
                "test": "Get pattern statistics",
                "status": "failed",
                "error": f"Status code {response.status_code}"
            })
    except Exception as e:
        print_error(f"Error getting statistics: {e}")
        results["tests"].append({
            "test": "Get pattern statistics",
            "status": "failed",
            "error": str(e)
        })
    
    return results


async def test_entity_types(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Test the /entity-types endpoints."""
    print_header("Testing GET /entity-types")
    
    results = {
        "endpoint": "/entity-types",
        "tests": []
    }
    
    # Test 1: Get all entity types
    try:
        response = await client.get(
            f"{BASE_URL}/entity-types",
            params={"include_descriptions": True, "include_examples": True},
            timeout=30.0
        )
        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved {data['total_entity_types']} entity types")
            print_success(f"Retrieved {data['total_citation_types']} citation types")
            
            # Display sample entity types with pattern counts
            if data.get('entity_types'):
                print_info("Sample entity types with patterns", "", indent=1)
                for entity in data['entity_types'][:5]:
                    if entity.get('pattern_count', 0) > 0:
                        print_info(
                            entity['type'],
                            f"{entity['pattern_count']} patterns",
                            indent=2
                        )
            
            # Check metadata for pattern statistics
            metadata = data.get('metadata', {})
            if 'pattern_loader_stats' in metadata:
                stats = metadata['pattern_loader_stats']
                print_info("Pattern loader statistics", "", indent=1)
                print_info("Total patterns loaded", stats.get('total_patterns_loaded', 0), indent=2)
                print_info("Pattern groups", stats.get('total_pattern_groups', 0), indent=2)
            
            results["tests"].append({
                "test": "Get all entity types",
                "status": "passed",
                "entity_types": data['total_entity_types'],
                "citation_types": data['total_citation_types']
            })
        else:
            print_error(f"Failed to get entity types: {response.status_code}")
            results["tests"].append({
                "test": "Get all entity types",
                "status": "failed",
                "error": f"Status code {response.status_code}"
            })
    except Exception as e:
        print_error(f"Error getting entity types: {e}")
        results["tests"].append({
            "test": "Get all entity types",
            "status": "failed",
            "error": str(e)
        })
    
    # Test 2: Get specific entity type details
    try:
        response = await client.get(f"{BASE_URL}/entity-types/JUDGE", timeout=30.0)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved details for JUDGE entity type")
            print_info("Pattern count", data.get('pattern_count', 0), indent=1)
            print_info("Regex supported", data.get('regex_supported', False), indent=1)
            print_info("AI enhanced", data.get('ai_enhanced', False), indent=1)
            
            # Display pattern details if available
            if data.get('pattern_details'):
                print_info("Sample patterns", "", indent=1)
                for pattern in data['pattern_details'][:3]:
                    print_info(pattern.get('name', 'unknown'), f"confidence {pattern.get('confidence', 0)}", indent=2)
            
            results["tests"].append({
                "test": "Get specific entity type",
                "status": "passed",
                "pattern_count": data.get('pattern_count', 0)
            })
        else:
            print_error(f"Failed to get entity type details: {response.status_code}")
            results["tests"].append({
                "test": "Get specific entity type",
                "status": "failed",
                "error": f"Status code {response.status_code}"
            })
    except Exception as e:
        print_error(f"Error getting entity type details: {e}")
        results["tests"].append({
            "test": "Get specific entity type",
            "status": "failed",
            "error": str(e)
        })
    
    return results


async def main():
    """Main test runner."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}Entity Extraction Service - Pattern Endpoints Test{Colors.END}")
    print(f"{Colors.CYAN}Testing service at: {SERVICE_URL}{Colors.END}")
    print(f"{Colors.CYAN}Timestamp: {datetime.now().isoformat()}{Colors.END}")
    
    all_results = {
        "service": "entity-extraction-service",
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "endpoints_tested": [],
        "summary": {
            "total_tests": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Check service health first
        if not await test_health_check(client):
            print_error("Service health check failed. Ensure the service is running.")
            return
        
        # Test each endpoint
        results = []
        
        # Test /patterns/detailed
        result = await test_patterns_detailed(client)
        results.append(result)
        all_results["endpoints_tested"].append(result)
        
        # Test /patterns/statistics
        result = await test_patterns_statistics(client)
        results.append(result)
        all_results["endpoints_tested"].append(result)
        
        # Test /entity-types
        result = await test_entity_types(client)
        results.append(result)
        all_results["endpoints_tested"].append(result)
        
        # Calculate summary
        for endpoint_result in results:
            for test in endpoint_result.get("tests", []):
                all_results["summary"]["total_tests"] += 1
                if test["status"] == "passed":
                    all_results["summary"]["passed"] += 1
                else:
                    all_results["summary"]["failed"] += 1
        
        # Print summary
        print_header("Test Summary")
        print_info("Total tests", all_results["summary"]["total_tests"])
        print_success(f"Passed: {all_results['summary']['passed']}")
        if all_results["summary"]["failed"] > 0:
            print_error(f"Failed: {all_results['summary']['failed']}")
        
        # Save results to file
        output_file = f"/srv/luris/be/entity-extraction-service/tests/results/pattern_endpoints_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            import os
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            print_success(f"Results saved to: {output_file}")
        except Exception as e:
            print_error(f"Failed to save results: {e}")
        
        # Exit with appropriate code
        if all_results["summary"]["failed"] > 0:
            sys.exit(1)
        else:
            print_success("\nAll tests passed successfully!")
            sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())