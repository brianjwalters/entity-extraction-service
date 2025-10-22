#!/usr/bin/env python3
"""
Main Test Runner for Template Fix Validation

Runs all test suites to validate template fixes and strategy differentiation.
Generates comprehensive test report with pass/fail statistics.
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple


class MainTestRunner:
    """Orchestrates execution of all test suites"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.test_suites = [
            {
                "name": "Template Execution",
                "script": "test_template_execution.py",
                "description": "Validates templates execute and return JSON",
                "required": True
            },
            {
                "name": "Strategy Differentiation",
                "script": "test_strategy_differentiation_v2.py",
                "description": "Verifies strategies produce different results",
                "required": True
            },
            {
                "name": "JSON Parsing",
                "script": "test_json_parsing.py",
                "description": "Tests JSON parser robustness and performance",
                "required": True
            },
            {
                "name": "Performance Benchmarks",
                "script": "test_performance.py",
                "description": "Measures performance against targets",
                "required": False  # May take longer
            }
        ]
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "suites_run": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
    
    def check_service_health(self) -> bool:
        """Check if required services are running"""
        print("Checking service health...")
        
        services = [
            ("Entity Extraction", "http://localhost:8007/api/v1/health"),
            ("vLLM", "http://localhost:8080/health"),
            ("Document Upload", "http://localhost:8008/api/v1/health")
        ]
        
        all_healthy = True
        
        for name, url in services:
            try:
                import requests
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"  ✓ {name}: Healthy")
                else:
                    print(f"  ✗ {name}: Unhealthy (status {response.status_code})")
                    all_healthy = False
            except Exception as e:
                print(f"  ✗ {name}: Not responding ({e})")
                all_healthy = False
        
        return all_healthy
    
    def run_test_suite(self, suite: Dict) -> Tuple[bool, Dict]:
        """Run a single test suite"""
        script_path = self.test_dir / suite["script"]
        
        if not script_path.exists():
            return False, {"error": f"Test script not found: {script_path}"}
        
        print(f"\n{'='*80}")
        print(f"Running: {suite['name']}")
        print(f"Description: {suite['description']}")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            # Run the test script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=str(self.test_dir.parent),  # Run from entity-extraction-service dir
                timeout=300  # 5 minute timeout
            )
            
            elapsed_time = time.time() - start_time
            
            # Parse output for results
            output_lines = result.stdout.split('\n')
            stderr_lines = result.stderr.split('\n')
            
            # Look for summary indicators
            passed = False
            if result.returncode == 0:
                passed = True
            
            # Extract key metrics from output
            metrics = self.extract_metrics(output_lines)
            
            return passed, {
                "name": suite["name"],
                "script": suite["script"],
                "passed": passed,
                "elapsed_time": elapsed_time,
                "return_code": result.returncode,
                "metrics": metrics,
                "output_sample": '\n'.join(output_lines[-20:]) if output_lines else "",
                "errors": '\n'.join(stderr_lines) if stderr_lines and result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            return False, {
                "name": suite["name"],
                "script": suite["script"],
                "passed": False,
                "error": "Test timed out after 5 minutes"
            }
        except Exception as e:
            return False, {
                "name": suite["name"],
                "script": suite["script"],
                "passed": False,
                "error": str(e)
            }
    
    def extract_metrics(self, output_lines: List[str]) -> Dict:
        """Extract key metrics from test output"""
        metrics = {}
        
        for line in output_lines:
            # Look for common metric patterns
            if "Total Tests:" in line:
                try:
                    metrics["total_tests"] = int(line.split(":")[-1].strip())
                except:
                    pass
            elif "Passed:" in line and "/" in line:
                try:
                    parts = line.split(":")[-1].strip().split()
                    if "/" in parts[0]:
                        passed, total = parts[0].split("/")
                        metrics["tests_passed"] = int(passed)
                        metrics["tests_total"] = int(total)
                except:
                    pass
            elif "entities" in line.lower() and any(char.isdigit() for char in line):
                # Extract entity counts
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    metrics["entity_count"] = int(numbers[0])
            elif "Success Rate:" in line:
                try:
                    rate = float(line.split(":")[-1].strip().rstrip('%'))
                    metrics["success_rate"] = rate
                except:
                    pass
        
        return metrics
    
    def generate_html_report(self) -> str:
        """Generate HTML report of test results"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Template Fix Validation Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .summary-card .value {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .passed {{ color: #10b981; }}
        .failed {{ color: #ef4444; }}
        .skipped {{ color: #f59e0b; }}
        .test-suite {{
            background: white;
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .suite-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .suite-name {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }}
        .suite-status {{
            padding: 5px 15px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
        }}
        .status-passed {{
            background: #10b981;
        }}
        .status-failed {{
            background: #ef4444;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            padding: 10px;
            background: #f9f9f9;
            border-radius: 5px;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .metric-value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }}
        .error-box {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 5px;
            padding: 15px;
            margin-top: 15px;
        }}
        .error-title {{
            color: #dc2626;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .conclusion {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 30px 0;
            text-align: center;
        }}
        .conclusion h2 {{
            margin: 0 0 20px 0;
        }}
        .verdict {{
            font-size: 48px;
            font-weight: bold;
            margin: 20px 0;
        }}
        .requirements {{
            text-align: left;
            margin: 20px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 5px;
        }}
        .requirement {{
            padding: 8px 0;
            display: flex;
            align-items: center;
        }}
        .requirement .icon {{
            width: 24px;
            margin-right: 10px;
        }}
        pre {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Template Fix Validation Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Comprehensive validation of template execution fixes and strategy differentiation</p>
    </div>
    
    <div class="summary">
        <div class="summary-card">
            <h3>Total Suites</h3>
            <div class="value">{self.results['summary']['total']}</div>
        </div>
        <div class="summary-card">
            <h3>Passed</h3>
            <div class="value passed">{self.results['summary']['passed']}</div>
        </div>
        <div class="summary-card">
            <h3>Failed</h3>
            <div class="value failed">{self.results['summary']['failed']}</div>
        </div>
        <div class="summary-card">
            <h3>Success Rate</h3>
            <div class="value">{self.calculate_success_rate():.1f}%</div>
        </div>
    </div>
"""
        
        # Add individual test suite results
        for suite_result in self.results["suites_run"]:
            status_class = "status-passed" if suite_result.get("passed") else "status-failed"
            status_text = "PASSED" if suite_result.get("passed") else "FAILED"
            
            html += f"""
    <div class="test-suite">
        <div class="suite-header">
            <div class="suite-name">{suite_result.get('name', 'Unknown')}</div>
            <div class="suite-status {status_class}">{status_text}</div>
        </div>
"""
            
            # Add metrics if available
            metrics = suite_result.get("metrics", {})
            if metrics:
                html += '<div class="metrics">'
                for key, value in metrics.items():
                    display_key = key.replace("_", " ").title()
                    display_value = f"{value:.1f}%" if "rate" in key.lower() else str(value)
                    html += f"""
                <div class="metric">
                    <div class="metric-label">{display_key}</div>
                    <div class="metric-value">{display_value}</div>
                </div>"""
                html += '</div>'
            
            # Add execution time
            if "elapsed_time" in suite_result:
                html += f"""
        <div class="metric">
            <div class="metric-label">Execution Time</div>
            <div class="metric-value">{suite_result['elapsed_time']:.2f}s</div>
        </div>"""
            
            # Add error if present
            if suite_result.get("error") or suite_result.get("errors"):
                error_content = suite_result.get("error") or suite_result.get("errors", "")
                html += f"""
        <div class="error-box">
            <div class="error-title">Error Details:</div>
            <pre>{error_content[:500]}...</pre>
        </div>"""
            
            html += '</div>'
        
        # Add conclusion section
        all_passed = self.results['summary']['failed'] == 0
        verdict_class = "passed" if all_passed else "failed"
        verdict_text = "✅ ALL TESTS PASSED" if all_passed else "❌ TESTS FAILED"
        
        html += f"""
    <div class="conclusion">
        <h2>Test Verdict</h2>
        <div class="verdict {verdict_class}">{verdict_text}</div>
        
        <div class="requirements">
            <h3>Validation Requirements:</h3>
            {self.generate_requirements_checklist()}
        </div>
        
        <p><strong>Next Steps:</strong></p>
        <p>{self.generate_next_steps()}</p>
    </div>
</body>
</html>
"""
        return html
    
    def calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        total = self.results['summary']['total']
        if total == 0:
            return 0.0
        return (self.results['summary']['passed'] / total) * 100
    
    def generate_requirements_checklist(self) -> str:
        """Generate requirements checklist HTML"""
        requirements = [
            ("All templates return JSON starting with {", self.check_requirement("template_json")),
            ("Each strategy produces different entity counts (>5% diff)", self.check_requirement("strategy_diff")),
            ("JSON parsing success rate = 100%", self.check_requirement("json_parsing")),
            ("No explanatory text in responses", self.check_requirement("no_explanation")),
            ("Performance meets targets (<2s per request)", self.check_requirement("performance"))
        ]
        
        html = ""
        for req, met in requirements:
            icon = "✅" if met else "❌"
            html += f"""
            <div class="requirement">
                <span class="icon">{icon}</span>
                <span>{req}</span>
            </div>"""
        
        return html
    
    def check_requirement(self, requirement: str) -> bool:
        """Check if a specific requirement is met"""
        # Check based on test results
        for suite in self.results["suites_run"]:
            if requirement == "template_json" and "Template Execution" in suite.get("name", ""):
                return suite.get("passed", False)
            elif requirement == "strategy_diff" and "Strategy Differentiation" in suite.get("name", ""):
                return suite.get("passed", False)
            elif requirement == "json_parsing" and "JSON Parsing" in suite.get("name", ""):
                return suite.get("passed", False)
            elif requirement == "performance" and "Performance" in suite.get("name", ""):
                return suite.get("passed", False)
        
        return False
    
    def generate_next_steps(self) -> str:
        """Generate next steps based on results"""
        if self.results['summary']['failed'] == 0:
            return "All validation tests passed! The template fixes are working correctly and strategies are properly differentiated. The system is ready for production use."
        else:
            failed_tests = [s['name'] for s in self.results['suites_run'] if not s.get('passed')]
            return f"Please review and fix the following failed tests: {', '.join(failed_tests)}. Check the detailed error messages above for specific issues."
    
    def run_all_tests(self) -> int:
        """Run all test suites and generate report"""
        print("=" * 80)
        print("TEMPLATE FIX VALIDATION - MAIN TEST RUNNER")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test Directory: {self.test_dir}")
        
        # Check service health first
        print("\n" + "=" * 80)
        print("PREREQUISITE CHECK")
        print("=" * 80)
        
        if not self.check_service_health():
            print("\n⚠️  WARNING: Some services are not healthy. Tests may fail.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Aborting test run.")
                return 1
        
        # Run each test suite
        for suite in self.test_suites:
            self.results['summary']['total'] += 1
            
            if suite.get("required") or True:  # Run all for now
                passed, result = self.run_test_suite(suite)
                
                if passed:
                    self.results['summary']['passed'] += 1
                else:
                    self.results['summary']['failed'] += 1
                
                self.results['suites_run'].append(result)
            else:
                print(f"\nSkipping optional test: {suite['name']}")
                self.results['summary']['skipped'] += 1
        
        # Generate summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Suites Run: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Failed: {self.results['summary']['failed']}")
        print(f"Success Rate: {self.calculate_success_rate():.1f}%")
        
        # Save JSON results
        json_file = self.results_dir / f"all_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nJSON results saved to: {json_file}")
        
        # Generate HTML report
        html_file = self.results_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w') as f:
            f.write(self.generate_html_report())
        print(f"HTML report saved to: {html_file}")
        
        # Final verdict
        print("\n" + "=" * 80)
        if self.results['summary']['failed'] == 0:
            print("✅ ALL VALIDATION TESTS PASSED!")
            print("Template fixes are working correctly.")
            print("Strategies produce differentiated results.")
            return 0
        else:
            print(f"❌ VALIDATION FAILED: {self.results['summary']['failed']} test suite(s) failed")
            print("Please review the detailed report for failure details.")
            return 1


if __name__ == "__main__":
    runner = MainTestRunner()
    exit_code = runner.run_all_tests()
    exit(exit_code)