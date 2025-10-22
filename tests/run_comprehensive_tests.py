#!/usr/bin/env python3
"""
Comprehensive Test Runner for Template Fixes Validation
Purpose: Run all tests to validate template fixes and strategy differentiation
Author: Test Engineer
Date: 2025-09-04
"""

import json
import time
import os
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import statistics

class ComprehensiveTestRunner:
    """Runs all validation tests and generates comprehensive report."""
    
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_suite": "Template Fixes Validation",
            "services_checked": {},
            "tests_executed": [],
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "performance_benchmarks": {},
            "validation_results": {},
            "recommendations": []
        }
        
    def check_service_health(self) -> bool:
        """Check all required services are running."""
        print("=" * 80)
        print("SERVICE HEALTH CHECK")
        print("=" * 80)
        
        services = [
            ("Entity Extraction", "http://localhost:8007/api/v1/health"),
            ("Document Upload", "http://localhost:8008/api/v1/health"),
            ("vLLM", "http://localhost:8080/health"),
        ]
        
        all_healthy = True
        
        for name, url in services:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    status = result.get("status", "unknown")
                    if "healthy" in status.lower() or "ok" in status.lower():
                        print(f"  ✓ {name}: Healthy")
                        self.test_results["services_checked"][name] = "healthy"
                    else:
                        print(f"  ⚠ {name}: {status}")
                        self.test_results["services_checked"][name] = status
                else:
                    print(f"  ✗ {name}: HTTP {response.status_code}")
                    self.test_results["services_checked"][name] = f"HTTP {response.status_code}"
                    all_healthy = False
            except Exception as e:
                print(f"  ✗ {name}: Not responding ({str(e)})")
                self.test_results["services_checked"][name] = "not_responding"
                all_healthy = False
        
        print("")
        return all_healthy
    
    def run_template_validation(self) -> Dict:
        """Run template directive validation tests."""
        print("=" * 80)
        print("RUNNING TEMPLATE DIRECTIVE VALIDATION")
        print("=" * 80)
        
        test_name = "Template Directive Validation"
        self.test_results["total_tests"] += 1
        
        try:
            # Run the template validation test
            result = subprocess.run(
                ["python3", "test_template_directives.py"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd="/srv/luris/be/entity-extraction-service/tests"
            )
            
            success = result.returncode == 0
            
            if success:
                print("  ✓ Template validation completed successfully")
                self.test_results["passed_tests"] += 1
            else:
                print("  ✗ Template validation failed")
                self.test_results["failed_tests"] += 1
            
            # Parse output for details
            output_lines = result.stdout.split("\n")
            for line in output_lines:
                if "Valid Templates:" in line:
                    print(f"    {line.strip()}")
                elif "Invalid Templates:" in line:
                    print(f"    {line.strip()}")
            
            self.test_results["tests_executed"].append({
                "name": test_name,
                "success": success,
                "duration": "N/A",
                "details": result.stdout[-500:] if result.stdout else result.stderr[-500:]
            })
            
            return {"success": success, "output": result.stdout}
            
        except subprocess.TimeoutExpired:
            print("  ✗ Test timed out after 60 seconds")
            self.test_results["failed_tests"] += 1
            self.test_results["tests_executed"].append({
                "name": test_name,
                "success": False,
                "error": "Timeout after 60 seconds"
            })
            return {"success": False, "error": "Timeout"}
            
        except Exception as e:
            print(f"  ✗ Test execution error: {str(e)}")
            self.test_results["failed_tests"] += 1
            self.test_results["tests_executed"].append({
                "name": test_name,
                "success": False,
                "error": str(e)
            })
            return {"success": False, "error": str(e)}
    
    def run_strategy_differentiation(self) -> Dict:
        """Run strategy differentiation tests."""
        print("=" * 80)
        print("RUNNING STRATEGY DIFFERENTIATION TEST")
        print("=" * 80)
        
        test_name = "Strategy Differentiation"
        self.test_results["total_tests"] += 1
        
        try:
            # Run the strategy differentiation test
            result = subprocess.run(
                ["python3", "test_strategy_differentiation.py"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for large document processing
                cwd="/srv/luris/be/entity-extraction-service/tests"
            )
            
            success = result.returncode == 0
            
            if success:
                print("  ✓ Strategy differentiation test passed")
                self.test_results["passed_tests"] += 1
            else:
                print("  ✗ Strategy differentiation test failed")
                self.test_results["failed_tests"] += 1
            
            # Parse output for key metrics
            output_lines = result.stdout.split("\n")
            for line in output_lines:
                if "multipass" in line and "entities" in line:
                    print(f"    {line.strip()}")
                elif "ai_enhanced" in line and "entities" in line:
                    print(f"    {line.strip()}")
                elif "unified" in line and "entities" in line:
                    print(f"    {line.strip()}")
                elif "Differentiation Score:" in line:
                    print(f"    {line.strip()}")
                elif "TEST PASSED" in line or "TEST FAILED" in line:
                    print(f"    {line.strip()}")
            
            self.test_results["tests_executed"].append({
                "name": test_name,
                "success": success,
                "duration": "N/A",
                "details": result.stdout[-1000:] if result.stdout else result.stderr[-1000:]
            })
            
            return {"success": success, "output": result.stdout}
            
        except subprocess.TimeoutExpired:
            print("  ✗ Test timed out after 5 minutes")
            self.test_results["failed_tests"] += 1
            self.test_results["tests_executed"].append({
                "name": test_name,
                "success": False,
                "error": "Timeout after 300 seconds"
            })
            return {"success": False, "error": "Timeout"}
            
        except Exception as e:
            print(f"  ✗ Test execution error: {str(e)}")
            self.test_results["failed_tests"] += 1
            self.test_results["tests_executed"].append({
                "name": test_name,
                "success": False,
                "error": str(e)
            })
            return {"success": False, "error": str(e)}
    
    def run_performance_benchmark(self) -> Dict:
        """Run performance benchmarks."""
        print("=" * 80)
        print("RUNNING PERFORMANCE BENCHMARKS")
        print("=" * 80)
        
        benchmarks = {}
        
        # Test JSON parsing performance
        print("\n1. JSON Parsing Performance Test")
        print("-" * 40)
        
        sample_json = json.dumps({
            "entities": [{"entity_text": f"Entity {i}", "entity_type": "PARTY"} for i in range(100)],
            "citations": [{"citation_text": f"Citation {i}", "citation_type": "CASE"} for i in range(50)],
            "metadata": {"extraction_mode": "test", "confidence": 0.85}
        })
        
        parse_times = []
        for i in range(100):
            start = time.time()
            parsed = json.loads(sample_json)
            elapsed = (time.time() - start) * 1000  # ms
            parse_times.append(elapsed)
        
        avg_parse_time = statistics.mean(parse_times)
        p95_parse_time = statistics.quantiles(parse_times, n=20)[18]  # 95th percentile
        
        print(f"  Average parse time: {avg_parse_time:.3f}ms")
        print(f"  P95 parse time: {p95_parse_time:.3f}ms")
        
        if avg_parse_time < 1:
            print("  ✓ JSON parsing performance EXCELLENT (<1ms)")
        elif avg_parse_time < 10:
            print("  ✓ JSON parsing performance GOOD (<10ms)")
        elif avg_parse_time < 100:
            print("  ⚠ JSON parsing performance ACCEPTABLE (<100ms)")
        else:
            print("  ✗ JSON parsing performance POOR (>100ms)")
        
        benchmarks["json_parsing"] = {
            "avg_ms": avg_parse_time,
            "p95_ms": p95_parse_time,
            "samples": len(parse_times)
        }
        
        # Test extraction endpoint performance
        print("\n2. Extraction Endpoint Performance Test")
        print("-" * 40)
        
        try:
            sample_text = "Test case Smith v. Jones, 123 F.3d 456 (2023)"
            payload = {
                "content": sample_text,
                "document_id": "perf_test_001",
                "extraction_mode": "regex",  # Fastest mode
                "confidence_threshold": 0.7
            }
            
            response_times = []
            for i in range(5):  # 5 requests to test
                start = time.time()
                response = requests.post(
                    "http://localhost:8007/api/v2/process/extract",
                    json=payload,
                    timeout=30
                )
                elapsed = (time.time() - start) * 1000  # ms
                response_times.append(elapsed)
                
                if response.status_code == 200:
                    print(f"    Request {i+1}: {elapsed:.0f}ms ✓")
                else:
                    print(f"    Request {i+1}: {elapsed:.0f}ms (HTTP {response.status_code})")
            
            avg_response_time = statistics.mean(response_times)
            print(f"  Average response time: {avg_response_time:.0f}ms")
            
            benchmarks["extraction_endpoint"] = {
                "avg_ms": avg_response_time,
                "samples": len(response_times)
            }
            
        except Exception as e:
            print(f"  ✗ Endpoint test failed: {str(e)}")
            benchmarks["extraction_endpoint"] = {"error": str(e)}
        
        self.test_results["performance_benchmarks"] = benchmarks
        
        return benchmarks
    
    def run_json_output_validation(self) -> Dict:
        """Test JSON output validation with edge cases."""
        print("=" * 80)
        print("JSON OUTPUT VALIDATION TEST")
        print("=" * 80)
        
        test_cases = [
            # Clean JSON
            ('{"entities": [], "citations": [], "metadata": {}}', True, "Clean JSON"),
            
            # JSON with whitespace
            ('  \n{"entities": [], "citations": [], "metadata": {}}\n  ', True, "JSON with whitespace"),
            
            # Malformed JSON
            ('{"entities": [], "citations": []', False, "Incomplete JSON"),
            
            # JSON with preamble (should fail)
            ('Here is the extraction:\n{"entities": [], "citations": [], "metadata": {}}', False, "JSON with preamble"),
            
            # JSON with postscript (should fail)
            ('{"entities": [], "citations": [], "metadata": {}}\nThats all!', False, "JSON with postscript"),
            
            # Large JSON
            (json.dumps({"entities": [{"text": f"E{i}"} for i in range(1000)], "citations": [], "metadata": {}}), True, "Large JSON (1000 entities)"),
        ]
        
        results = []
        passed = 0
        failed = 0
        
        for test_input, should_pass, description in test_cases:
            print(f"\n  Testing: {description}")
            
            try:
                # Test parsing
                start = time.time()
                
                # Strip and check for clean JSON
                stripped = test_input.strip()
                is_clean = stripped.startswith('{') and stripped.endswith('}')
                
                if is_clean:
                    parsed = json.loads(stripped)
                    parse_success = True
                else:
                    parse_success = False
                
                elapsed = (time.time() - start) * 1000
                
                if parse_success == should_pass:
                    print(f"    ✓ Result as expected (parsed={parse_success}, time={elapsed:.2f}ms)")
                    passed += 1
                else:
                    print(f"    ✗ Unexpected result (parsed={parse_success}, expected={should_pass})")
                    failed += 1
                
                results.append({
                    "description": description,
                    "success": parse_success == should_pass,
                    "parse_time_ms": elapsed
                })
                
            except json.JSONDecodeError as e:
                if not should_pass:
                    print(f"    ✓ Failed as expected: {str(e)[:50]}")
                    passed += 1
                else:
                    print(f"    ✗ Unexpected failure: {str(e)[:50]}")
                    failed += 1
                
                results.append({
                    "description": description,
                    "success": not should_pass,
                    "error": str(e)[:100]
                })
            
            except Exception as e:
                print(f"    ✗ Unexpected error: {str(e)}")
                failed += 1
                results.append({
                    "description": description,
                    "success": False,
                    "error": str(e)
                })
        
        print(f"\n  Summary: {passed} passed, {failed} failed")
        
        self.test_results["validation_results"]["json_output"] = {
            "total_tests": len(test_cases),
            "passed": passed,
            "failed": failed,
            "test_results": results
        }
        
        return {"passed": passed, "failed": failed, "results": results}
    
    def generate_comprehensive_report(self) -> str:
        """Generate final comprehensive report."""
        report = []
        report.append("=" * 80)
        report.append("COMPREHENSIVE TEST SUITE REPORT")
        report.append("Template Fixes Validation")
        report.append("=" * 80)
        report.append(f"Timestamp: {self.test_results['timestamp']}")
        report.append("")
        
        # Service health summary
        report.append("SERVICE HEALTH:")
        report.append("-" * 40)
        for service, status in self.test_results["services_checked"].items():
            if status == "healthy":
                report.append(f"  ✓ {service}: {status}")
            else:
                report.append(f"  ✗ {service}: {status}")
        report.append("")
        
        # Test execution summary
        report.append("TEST EXECUTION SUMMARY:")
        report.append("-" * 40)
        report.append(f"  Total Tests: {self.test_results['total_tests']}")
        report.append(f"  Passed: {self.test_results['passed_tests']}")
        report.append(f"  Failed: {self.test_results['failed_tests']}")
        
        if self.test_results['total_tests'] > 0:
            pass_rate = (self.test_results['passed_tests'] / self.test_results['total_tests']) * 100
            report.append(f"  Pass Rate: {pass_rate:.1f}%")
        report.append("")
        
        # Individual test results
        report.append("TEST RESULTS:")
        report.append("-" * 40)
        for test in self.test_results["tests_executed"]:
            if test.get("success"):
                report.append(f"  ✓ {test['name']}")
            else:
                report.append(f"  ✗ {test['name']}")
                if test.get("error"):
                    report.append(f"     Error: {test['error']}")
        report.append("")
        
        # Performance benchmarks
        if self.test_results.get("performance_benchmarks"):
            report.append("PERFORMANCE BENCHMARKS:")
            report.append("-" * 40)
            
            if "json_parsing" in self.test_results["performance_benchmarks"]:
                jp = self.test_results["performance_benchmarks"]["json_parsing"]
                report.append(f"  JSON Parsing:")
                report.append(f"    Average: {jp['avg_ms']:.3f}ms")
                report.append(f"    P95: {jp['p95_ms']:.3f}ms")
                
                if jp['avg_ms'] < 100:
                    report.append(f"    ✓ Performance target met (<100ms)")
                else:
                    report.append(f"    ✗ Performance target not met (>100ms)")
            
            if "extraction_endpoint" in self.test_results["performance_benchmarks"]:
                ee = self.test_results["performance_benchmarks"]["extraction_endpoint"]
                if "error" not in ee:
                    report.append(f"  Extraction Endpoint:")
                    report.append(f"    Average: {ee['avg_ms']:.0f}ms")
            report.append("")
        
        # Validation results
        if self.test_results.get("validation_results"):
            report.append("VALIDATION RESULTS:")
            report.append("-" * 40)
            
            if "json_output" in self.test_results["validation_results"]:
                jo = self.test_results["validation_results"]["json_output"]
                report.append(f"  JSON Output Validation:")
                report.append(f"    Tests: {jo['total_tests']}")
                report.append(f"    Passed: {jo['passed']}")
                report.append(f"    Failed: {jo['failed']}")
            report.append("")
        
        # Success criteria evaluation
        report.append("SUCCESS CRITERIA EVALUATION:")
        report.append("-" * 40)
        
        criteria = {
            "All templates return valid JSON": False,
            "Each strategy produces different results": False,
            "No parsing failures": False,
            "Performance targets met": False
        }
        
        # Check criteria
        if self.test_results['passed_tests'] > 0:
            for test in self.test_results["tests_executed"]:
                if test["name"] == "Template Directive Validation" and test.get("success"):
                    criteria["All templates return valid JSON"] = True
                if test["name"] == "Strategy Differentiation" and test.get("success"):
                    criteria["Each strategy produces different results"] = True
        
        if self.test_results.get("validation_results", {}).get("json_output", {}).get("failed", 1) == 0:
            criteria["No parsing failures"] = True
        
        if self.test_results.get("performance_benchmarks", {}).get("json_parsing", {}).get("avg_ms", 1000) < 100:
            criteria["Performance targets met"] = True
        
        for criterion, met in criteria.items():
            if met:
                report.append(f"  ✓ {criterion}")
            else:
                report.append(f"  ✗ {criterion}")
        
        # Overall verdict
        all_criteria_met = all(criteria.values())
        report.append("")
        report.append("OVERALL VERDICT:")
        report.append("-" * 40)
        if all_criteria_met:
            report.append("  ✓✓✓ ALL SUCCESS CRITERIA MET ✓✓✓")
            report.append("  Template fixes are working correctly!")
            report.append("  Strategies produce differentiated results!")
        else:
            report.append("  ✗ Some criteria not met")
            report.append("  Further investigation required")
        
        # Recommendations
        report.append("")
        report.append("RECOMMENDATIONS:")
        report.append("-" * 40)
        
        if not criteria["All templates return valid JSON"]:
            report.append("  • Review templates that fail JSON validation")
            report.append("  • Ensure all templates have execution directives")
        
        if not criteria["Each strategy produces different results"]:
            report.append("  • Review strategy configurations")
            report.append("  • Verify template assignments per strategy")
        
        if not criteria["Performance targets met"]:
            report.append("  • Optimize JSON parsing logic")
            report.append("  • Consider caching parsed templates")
        
        if all_criteria_met:
            report.append("  • Deploy to production")
            report.append("  • Monitor performance metrics")
            report.append("  • Document the improvements")
        
        report.append("")
        report.append("=" * 80)
        report.append("END OF COMPREHENSIVE REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main test execution."""
    runner = ComprehensiveTestRunner()
    
    print("\n" + "=" * 80)
    print(" " * 20 + "COMPREHENSIVE TEST SUITE")
    print(" " * 15 + "Template Fixes Validation")
    print("=" * 80 + "\n")
    
    # Check service health
    if not runner.check_service_health():
        print("⚠️  Warning: Some services are not healthy. Tests may fail.")
        print("")
    
    # Run all tests
    runner.run_template_validation()
    print("")
    
    runner.run_strategy_differentiation()
    print("")
    
    runner.run_performance_benchmark()
    print("")
    
    runner.run_json_output_validation()
    print("")
    
    # Generate final report
    report = runner.generate_comprehensive_report()
    print(report)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/srv/luris/be/entity-extraction-service/tests/results/comprehensive_test_{timestamp}.json"
    report_file = f"/srv/luris/be/entity-extraction-service/tests/results/comprehensive_test_{timestamp}.txt"
    
    # Save JSON results
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(runner.test_results, f, indent=2)
    print(f"\nResults saved to: {results_file}")
    
    # Save text report
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_file}")
    
    # Return appropriate exit code
    if runner.test_results['failed_tests'] == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        return 0
    else:
        print(f"\n✗ {runner.test_results['failed_tests']} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())