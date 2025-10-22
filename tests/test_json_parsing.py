#!/usr/bin/env python3
"""
Test JSON Parsing Validation

Verifies that the enhanced JSON parser handles all edge cases correctly
and performs within target benchmarks.
"""

import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add parent directory to path for imports
from src.core.json_response_parser import JSONResponseParser as ResponseParser


class JSONParsingTester:
    """Test JSON parsing robustness and performance"""
    
    def __init__(self):
        self.parser = ResponseParser()
        self.test_cases = self.create_test_cases()
        
    def create_test_cases(self) -> List[Dict[str, Any]]:
        """Create comprehensive test cases for JSON parsing"""
        return [
            # Clean JSON (fast path)
            {
                "name": "clean_json",
                "input": '{"entities": [{"entity_text": "John Doe", "entity_type": "PARTY"}]}',
                "expected_success": True,
                "expected_time_ms": 10,
                "description": "Clean JSON should parse directly"
            },
            
            # JSON with leading whitespace
            {
                "name": "leading_whitespace",
                "input": '   \n\n  {"entities": [{"entity_text": "Test", "entity_type": "PARTY"}]}',
                "expected_success": True,
                "expected_time_ms": 10,
                "description": "Should handle leading whitespace"
            },
            
            # JSON with explanation prefix (should be cleaned)
            {
                "name": "explanation_prefix",
                "input": '''I'll extract the entities from this text. Here's the result:
                
{"entities": [{"entity_text": "United States", "entity_type": "PARTY"}], "citations": []}''',
                "expected_success": True,
                "expected_time_ms": 50,
                "description": "Should strip explanation text"
            },
            
            # Markdown code block
            {
                "name": "markdown_code_block",
                "input": '''```json
{"entities": [{"entity_text": "9th Circuit", "entity_type": "COURT"}]}
```''',
                "expected_success": True,
                "expected_time_ms": 30,
                "description": "Should extract from markdown blocks"
            },
            
            # Multiple JSON objects (take first valid)
            {
                "name": "multiple_json",
                "input": '''First attempt: {"invalid": }
                
Second attempt:
{"entities": [{"entity_text": "Judge Smith", "entity_type": "JUDGE"}]}

Third object: {"other": "data"}''',
                "expected_success": True,
                "expected_time_ms": 100,
                "description": "Should find first valid JSON"
            },
            
            # Nested JSON with complex structure
            {
                "name": "nested_complex",
                "input": '''{
                    "entities": [
                        {
                            "entity_text": "ABC Corp.",
                            "entity_type": "PARTY",
                            "metadata": {
                                "confidence": 0.95,
                                "positions": [{"start": 10, "end": 19}]
                            }
                        }
                    ],
                    "citations": [
                        {
                            "citation_text": "123 U.S. 456 (2023)",
                            "citation_type": "CASE_CITATION"
                        }
                    ],
                    "metadata": {
                        "extraction_method": "ai_enhanced",
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                }''',
                "expected_success": True,
                "expected_time_ms": 20,
                "description": "Should handle complex nested structures"
            },
            
            # JSON with special characters
            {
                "name": "special_characters",
                "input": r'{"entities": [{"entity_text": "O\'Malley & Sons \"Law Firm\"", "entity_type": "LAW_FIRM"}]}',
                "expected_success": True,
                "expected_time_ms": 15,
                "description": "Should handle escaped special characters"
            },
            
            # Truncated JSON (recovery attempt)
            {
                "name": "truncated_json",
                "input": '{"entities": [{"entity_text": "Test Entity", "entity_type": "PARTY"',
                "expected_success": False,  # Should fail gracefully
                "expected_time_ms": 200,
                "description": "Should attempt recovery but fail gracefully"
            },
            
            # Large JSON response
            {
                "name": "large_json",
                "input": json.dumps({
                    "entities": [
                        {
                            "entity_text": f"Entity {i}",
                            "entity_type": "PARTY",
                            "confidence": 0.8 + (i * 0.001)
                        }
                        for i in range(1000)
                    ],
                    "citations": [
                        {
                            "citation_text": f"{i} U.S. {i*10} (202{i%10})",
                            "citation_type": "CASE_CITATION"
                        }
                        for i in range(100, 200)
                    ]
                }),
                "expected_success": True,
                "expected_time_ms": 100,
                "description": "Should handle large JSON efficiently"
            },
            
            # JSON with comments (invalid but common)
            {
                "name": "json_with_comments",
                "input": '''{
                    // This is a comment
                    "entities": [
                        {"entity_text": "Test", "entity_type": "PARTY"} // inline comment
                    ]
                }''',
                "expected_success": True,  # Parser should clean comments
                "expected_time_ms": 50,
                "description": "Should strip JavaScript-style comments"
            },
            
            # Mixed content with JSON embedded
            {
                "name": "mixed_content",
                "input": '''Let me process this request.

The extraction found the following entities:

{"entities": [{"entity_text": "Supreme Court", "entity_type": "COURT"}], "citations": [{"citation_text": "Roe v. Wade", "citation_type": "CASE_CITATION"}]}

I hope this helps with your analysis.''',
                "expected_success": True,
                "expected_time_ms": 75,
                "description": "Should extract JSON from mixed content"
            },
            
            # Empty response variations
            {
                "name": "empty_entities",
                "input": '{"entities": [], "citations": []}',
                "expected_success": True,
                "expected_time_ms": 10,
                "description": "Should handle empty arrays"
            },
            
            # Malformed with recovery
            {
                "name": "malformed_recovery",
                "input": '{"entities": [{"entity_text": "Test" "entity_type": "PARTY"}]}',
                "expected_success": False,
                "expected_time_ms": 150,
                "description": "Missing comma - should fail"
            }
        ]
    
    def test_single_case(self, test_case: Dict) -> Dict[str, Any]:
        """Test a single parsing case"""
        start_time = time.time() * 1000  # Convert to milliseconds
        
        try:
            result = self.parser.parse(test_case["input"])
            parse_time = (time.time() * 1000) - start_time
            
            # Check if parsing succeeded as expected
            success = result is not None and isinstance(result, dict)
            
            # Validate structure if successful
            structure_valid = False
            if success:
                structure_valid = (
                    "entities" in result and
                    isinstance(result["entities"], list)
                ) or (
                    "citations" in result and
                    isinstance(result["citations"], list)
                )
            
            return {
                "name": test_case["name"],
                "success": success,
                "expected_success": test_case["expected_success"],
                "parse_time_ms": parse_time,
                "expected_time_ms": test_case["expected_time_ms"],
                "time_within_target": parse_time <= test_case["expected_time_ms"] * 1.5,  # 50% tolerance
                "structure_valid": structure_valid,
                "result": result if success else None,
                "error": None if success else "Failed to parse"
            }
            
        except Exception as e:
            parse_time = (time.time() * 1000) - start_time
            return {
                "name": test_case["name"],
                "success": False,
                "expected_success": test_case["expected_success"],
                "parse_time_ms": parse_time,
                "expected_time_ms": test_case["expected_time_ms"],
                "time_within_target": False,
                "structure_valid": False,
                "result": None,
                "error": str(e)
            }
    
    def run_performance_benchmark(self, iterations: int = 100) -> Dict[str, Any]:
        """Run performance benchmark on clean JSON"""
        clean_json = '{"entities": [{"entity_text": "Test Entity", "entity_type": "PARTY", "confidence": 0.95}]}'
        
        times = []
        for _ in range(iterations):
            start = time.time() * 1000
            self.parser.parse(clean_json)
            times.append((time.time() * 1000) - start)
        
        return {
            "iterations": iterations,
            "avg_time_ms": sum(times) / len(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "p50_ms": sorted(times)[len(times)//2],
            "p95_ms": sorted(times)[int(len(times)*0.95)],
            "p99_ms": sorted(times)[int(len(times)*0.99)]
        }
    
    def run_tests(self) -> None:
        """Run all JSON parsing tests"""
        print("=" * 80)
        print("JSON PARSING VALIDATION TEST SUITE")
        print("=" * 80)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_cases": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "performance_met": 0
            }
        }
        
        # Run each test case
        print("\nRunning test cases...")
        for test_case in self.test_cases:
            print(f"\n  Testing: {test_case['name']}")
            print(f"    Description: {test_case['description']}")
            
            result = self.test_single_case(test_case)
            results["test_cases"].append(result)
            results["summary"]["total"] += 1
            
            # Check if test passed
            test_passed = (result["success"] == result["expected_success"])
            
            if test_passed:
                results["summary"]["passed"] += 1
                print(f"    ✓ Result: PASSED")
            else:
                results["summary"]["failed"] += 1
                print(f"    ✗ Result: FAILED")
                if result["error"]:
                    print(f"    Error: {result['error']}")
            
            print(f"    Parse time: {result['parse_time_ms']:.2f}ms (target: {result['expected_time_ms']}ms)")
            
            if result["time_within_target"]:
                results["summary"]["performance_met"] += 1
                print(f"    ✓ Performance: Within target")
            else:
                print(f"    ✗ Performance: Exceeded target")
        
        # Run performance benchmark
        print("\n" + "=" * 80)
        print("PERFORMANCE BENCHMARK")
        print("=" * 80)
        
        benchmark = self.run_performance_benchmark(1000)
        results["benchmark"] = benchmark
        
        print(f"\nClean JSON Parsing (1000 iterations):")
        print(f"  Average: {benchmark['avg_time_ms']:.2f}ms")
        print(f"  Min: {benchmark['min_time_ms']:.2f}ms")
        print(f"  Max: {benchmark['max_time_ms']:.2f}ms")
        print(f"  P50: {benchmark['p50_ms']:.2f}ms")
        print(f"  P95: {benchmark['p95_ms']:.2f}ms")
        print(f"  P99: {benchmark['p99_ms']:.2f}ms")
        
        # Target validation
        target_met = benchmark["avg_time_ms"] < 10  # Target: <10ms for clean JSON
        print(f"\n  Target (<10ms avg): {'✓ MET' if target_met else '✗ NOT MET'}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        success_rate = (results["summary"]["passed"] / results["summary"]["total"]) * 100
        perf_rate = (results["summary"]["performance_met"] / results["summary"]["total"]) * 100
        
        print(f"Test Cases: {results['summary']['passed']}/{results['summary']['total']} passed ({success_rate:.1f}%)")
        print(f"Performance: {results['summary']['performance_met']}/{results['summary']['total']} within target ({perf_rate:.1f}%)")
        
        # Overall verdict
        all_passed = results["summary"]["failed"] == 0
        perf_good = perf_rate >= 80  # 80% of tests within performance target
        
        if all_passed and perf_good:
            print("\n✓ JSON PARSING VALIDATION: PASSED")
        else:
            print("\n✗ JSON PARSING VALIDATION: FAILED")
            if not all_passed:
                print(f"  - {results['summary']['failed']} test cases failed")
            if not perf_good:
                print(f"  - Performance targets not met (only {perf_rate:.1f}% within target)")
        
        # Save results
        output_file = f"tests/results/json_parsing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDetailed results saved to: {output_file}")
        
        return 0 if (all_passed and perf_good) else 1


if __name__ == "__main__":
    tester = JSONParsingTester()
    exit_code = tester.run_tests()
    exit(exit_code)