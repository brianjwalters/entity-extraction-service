#!/usr/bin/env python3
"""
Performance Benchmark Test Suite

Measures and validates performance metrics for template rendering,
vLLM response times, JSON parsing, and end-to-end extraction.
"""

import json
import time
import requests
import asyncio
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import threading


class PerformanceBenchmarkTester:
    """Test performance metrics and benchmarks"""
    
    def __init__(self):
        self.base_url = "http://localhost:8007/api/v1"
        self.metrics = {
            "template_rendering": [],
            "vllm_response": [],
            "json_parsing": [],
            "end_to_end": [],
            "concurrent": []
        }
        self.test_texts = self.create_test_texts()
        
    def create_test_texts(self) -> Dict[str, str]:
        """Create test texts of varying sizes"""
        base_text = """
        In United States v. Smith, 123 F.3d 456 (9th Cir. 2023), Judge Johnson ruled
        that defendant ABC Corporation violated 18 U.S.C. § 1234. Attorney Michael Davis
        of Davis & Associates represented the plaintiff, seeking $5,000,000 in damages.
        """
        
        return {
            "small": base_text,  # ~500 chars
            "medium": base_text * 20,  # ~10KB
            "large": base_text * 200,  # ~100KB
            "xlarge": base_text * 1000  # ~500KB
        }
    
    def measure_template_rendering(self) -> Dict[str, Any]:
        """Measure template rendering performance"""
        print("\n  Measuring template rendering performance...")
        
        # Test endpoint that renders templates without extraction
        test_payload = {
            "content": self.test_texts["small"],
            "document_id": f"perf_template_{int(time.time())}",
            "extraction_mode": "unified",
            "test_mode": "template_only"  # Special flag if supported
        }
        
        times = []
        for i in range(10):
            start = time.time()
            try:
                response = requests.post(
                    f"{self.base_url}/extract",
                    json=test_payload,
                    timeout=10
                )
                elapsed = time.time() - start
                times.append(elapsed * 1000)  # Convert to ms
            except Exception as e:
                print(f"    Warning: Template test {i+1} failed: {e}")
        
        if times:
            return {
                "avg_ms": statistics.mean(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "p95_ms": sorted(times)[int(len(times)*0.95)] if len(times) > 1 else times[0],
                "samples": len(times)
            }
        return {"error": "No successful measurements"}
    
    def measure_vllm_response(self, strategy: str, size: str) -> Dict[str, Any]:
        """Measure vLLM response time for a strategy"""
        print(f"\n  Measuring vLLM response for {strategy} with {size} text...")
        
        payload = {
            "content": self.test_texts[size],
            "document_id": f"perf_vllm_{strategy}_{size}_{int(time.time())}",
            "extraction_mode": strategy,
            "confidence_threshold": 0.7
        }
        
        times = []
        entity_counts = []
        
        for i in range(3):  # Fewer iterations for vLLM due to cost
            start = time.time()
            try:
                response = requests.post(
                    f"{self.base_url}/extract",
                    json=payload,
                    timeout=60
                )
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    result = response.json()
                    times.append(elapsed)
                    entity_counts.append(len(result.get("entities", [])))
                    print(f"      Run {i+1}: {elapsed:.2f}s, {entity_counts[-1]} entities")
            except Exception as e:
                print(f"    Warning: vLLM test {i+1} failed: {e}")
        
        if times:
            return {
                "strategy": strategy,
                "text_size": size,
                "avg_seconds": statistics.mean(times),
                "min_seconds": min(times),
                "max_seconds": max(times),
                "avg_entities": statistics.mean(entity_counts) if entity_counts else 0,
                "throughput_entities_per_sec": statistics.mean(entity_counts) / statistics.mean(times) if entity_counts else 0,
                "samples": len(times)
            }
        return {"error": f"No successful measurements for {strategy}"}
    
    def measure_json_parsing(self) -> Dict[str, Any]:
        """Measure JSON parsing performance directly"""
        print("\n  Measuring JSON parsing performance...")
        
        # Create sample JSON responses of varying sizes
        test_jsons = [
            json.dumps({"entities": [{"entity_text": f"Entity {i}", "entity_type": "PARTY"} for i in range(10)]}),
            json.dumps({"entities": [{"entity_text": f"Entity {i}", "entity_type": "PARTY"} for i in range(100)]}),
            json.dumps({"entities": [{"entity_text": f"Entity {i}", "entity_type": "PARTY"} for i in range(1000)]})
        ]
        
        results = []
        for idx, test_json in enumerate(test_jsons):
            size = 10 ** (idx + 1)  # 10, 100, 1000
            times = []
            
            for _ in range(100):
                start = time.time()
                parsed = json.loads(test_json)
                elapsed = (time.time() - start) * 1000  # Convert to ms
                times.append(elapsed)
            
            results.append({
                "entity_count": size,
                "json_size_bytes": len(test_json),
                "avg_ms": statistics.mean(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "p99_ms": sorted(times)[int(len(times)*0.99)]
            })
        
        return {"parsing_benchmarks": results}
    
    def measure_end_to_end(self, strategy: str) -> Dict[str, Any]:
        """Measure end-to-end extraction performance"""
        print(f"\n  Measuring end-to-end performance for {strategy}...")
        
        results = {}
        
        for size_name, text in self.test_texts.items():
            print(f"    Testing {size_name} text...")
            
            payload = {
                "content": text,
                "document_id": f"perf_e2e_{strategy}_{size_name}_{int(time.time())}",
                "extraction_mode": strategy,
                "confidence_threshold": 0.7
            }
            
            # Measure with warmup
            warmup_times = []
            regular_times = []
            
            # Warmup run
            try:
                start = time.time()
                response = requests.post(f"{self.base_url}/extract", json=payload, timeout=60)
                warmup_times.append(time.time() - start)
            except:
                pass
            
            # Regular runs
            for i in range(3):
                try:
                    start = time.time()
                    response = requests.post(f"{self.base_url}/extract", json=payload, timeout=60)
                    elapsed = time.time() - start
                    
                    if response.status_code == 200:
                        regular_times.append(elapsed)
                        result = response.json()
                        entities = len(result.get("entities", []))
                        print(f"      Run {i+1}: {elapsed:.2f}s, {entities} entities")
                except Exception as e:
                    print(f"      Run {i+1} failed: {e}")
            
            if regular_times:
                results[size_name] = {
                    "text_size_chars": len(text),
                    "warmup_time": warmup_times[0] if warmup_times else None,
                    "avg_seconds": statistics.mean(regular_times),
                    "min_seconds": min(regular_times),
                    "max_seconds": max(regular_times),
                    "throughput_chars_per_sec": len(text) / statistics.mean(regular_times)
                }
        
        return results
    
    def measure_concurrent_performance(self, concurrent_requests: int = 5) -> Dict[str, Any]:
        """Measure performance under concurrent load"""
        print(f"\n  Measuring concurrent performance ({concurrent_requests} parallel requests)...")
        
        def make_request(request_id: int) -> Dict:
            payload = {
                "content": self.test_texts["small"],
                "document_id": f"perf_concurrent_{request_id}_{int(time.time())}",
                "extraction_mode": "unified",
                "confidence_threshold": 0.7
            }
            
            start = time.time()
            try:
                response = requests.post(f"{self.base_url}/extract", json=payload, timeout=30)
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "request_id": request_id,
                        "success": True,
                        "response_time": elapsed,
                        "entity_count": len(result.get("entities", []))
                    }
                else:
                    return {
                        "request_id": request_id,
                        "success": False,
                        "response_time": elapsed,
                        "status_code": response.status_code
                    }
            except Exception as e:
                return {
                    "request_id": request_id,
                    "success": False,
                    "response_time": time.time() - start,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        # Calculate metrics
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        metrics = {
            "total_requests": concurrent_requests,
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": (len(successful) / concurrent_requests) * 100
        }
        
        if successful:
            response_times = [r["response_time"] for r in successful]
            metrics.update({
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p95_response_time": sorted(response_times)[int(len(response_times)*0.95)] if len(response_times) > 1 else response_times[0]
            })
        
        return metrics
    
    def measure_resource_usage(self) -> Dict[str, Any]:
        """Measure system resource usage"""
        process = psutil.Process()
        
        return {
            "cpu_percent": process.cpu_percent(interval=1),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "num_threads": process.num_threads(),
            "num_fds": process.num_fds() if hasattr(process, "num_fds") else None
        }
    
    def run_tests(self) -> None:
        """Run all performance benchmarks"""
        print("=" * 80)
        print("PERFORMANCE BENCHMARK TEST SUITE")
        print("=" * 80)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {}
        }
        
        # 1. Template Rendering Performance
        print("\n1. TEMPLATE RENDERING PERFORMANCE")
        print("-" * 40)
        template_results = self.measure_template_rendering()
        results["benchmarks"]["template_rendering"] = template_results
        
        if "avg_ms" in template_results:
            print(f"  Average: {template_results['avg_ms']:.2f}ms")
            print(f"  Min/Max: {template_results['min_ms']:.2f}ms / {template_results['max_ms']:.2f}ms")
        
        # 2. vLLM Response Time
        print("\n2. vLLM RESPONSE TIME")
        print("-" * 40)
        vllm_results = {}
        
        for strategy in ["unified", "ai_enhanced"]:
            for size in ["small", "medium"]:
                result = self.measure_vllm_response(strategy, size)
                vllm_results[f"{strategy}_{size}"] = result
        
        results["benchmarks"]["vllm_response"] = vllm_results
        
        # 3. JSON Parsing Performance
        print("\n3. JSON PARSING PERFORMANCE")
        print("-" * 40)
        json_results = self.measure_json_parsing()
        results["benchmarks"]["json_parsing"] = json_results
        
        for benchmark in json_results["parsing_benchmarks"]:
            print(f"  {benchmark['entity_count']} entities: {benchmark['avg_ms']:.3f}ms avg, {benchmark['p99_ms']:.3f}ms p99")
        
        # 4. End-to-End Performance
        print("\n4. END-TO-END PERFORMANCE")
        print("-" * 40)
        e2e_results = {}
        
        for strategy in ["unified", "ai_enhanced", "multipass"]:
            print(f"\n  Strategy: {strategy}")
            e2e_results[strategy] = self.measure_end_to_end(strategy)
        
        results["benchmarks"]["end_to_end"] = e2e_results
        
        # 5. Concurrent Request Performance
        print("\n5. CONCURRENT REQUEST PERFORMANCE")
        print("-" * 40)
        concurrent_results = self.measure_concurrent_performance(5)
        results["benchmarks"]["concurrent"] = concurrent_results
        
        print(f"  Success Rate: {concurrent_results.get('success_rate', 0):.1f}%")
        if "avg_response_time" in concurrent_results:
            print(f"  Avg Response: {concurrent_results['avg_response_time']:.2f}s")
            print(f"  P95 Response: {concurrent_results.get('p95_response_time', 0):.2f}s")
        
        # 6. Resource Usage
        print("\n6. RESOURCE USAGE")
        print("-" * 40)
        resource_results = self.measure_resource_usage()
        results["benchmarks"]["resources"] = resource_results
        
        print(f"  CPU Usage: {resource_results['cpu_percent']:.1f}%")
        print(f"  Memory Usage: {resource_results['memory_mb']:.1f}MB ({resource_results['memory_percent']:.1f}%)")
        
        # Performance Targets Validation
        print("\n" + "=" * 80)
        print("PERFORMANCE TARGET VALIDATION")
        print("=" * 80)
        
        targets_met = []
        
        # Check template rendering < 100ms
        if "avg_ms" in template_results:
            template_ok = template_results["avg_ms"] < 100
            targets_met.append(template_ok)
            print(f"  Template Rendering < 100ms: {'✓' if template_ok else '✗'} ({template_results['avg_ms']:.2f}ms)")
        
        # Check JSON parsing < 10ms for typical response
        if json_results["parsing_benchmarks"]:
            json_ok = json_results["parsing_benchmarks"][0]["avg_ms"] < 10
            targets_met.append(json_ok)
            print(f"  JSON Parsing < 10ms: {'✓' if json_ok else '✗'} ({json_results['parsing_benchmarks'][0]['avg_ms']:.2f}ms)")
        
        # Check end-to-end < 2s for small text
        if "unified" in e2e_results and "small" in e2e_results["unified"]:
            e2e_ok = e2e_results["unified"]["small"]["avg_seconds"] < 2.0
            targets_met.append(e2e_ok)
            print(f"  End-to-End < 2s (small): {'✓' if e2e_ok else '✗'} ({e2e_results['unified']['small']['avg_seconds']:.2f}s)")
        
        # Check concurrent success rate > 95%
        concurrent_ok = concurrent_results.get("success_rate", 0) >= 95
        targets_met.append(concurrent_ok)
        print(f"  Concurrent Success > 95%: {'✓' if concurrent_ok else '✗'} ({concurrent_results.get('success_rate', 0):.1f}%)")
        
        # Overall verdict
        all_targets_met = all(targets_met) if targets_met else False
        
        print("\n" + "=" * 80)
        if all_targets_met:
            print("✓ ALL PERFORMANCE TARGETS MET")
        else:
            print(f"✗ PERFORMANCE TARGETS NOT MET ({sum(targets_met)}/{len(targets_met)} passed)")
        
        # Save results
        output_file = f"tests/results/performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDetailed results saved to: {output_file}")
        
        return 0 if all_targets_met else 1


if __name__ == "__main__":
    tester = PerformanceBenchmarkTester()
    exit_code = tester.run_tests()
    exit(exit_code)