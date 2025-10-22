#!/usr/bin/env python3
"""
vLLM Metrics Integration Example

This script demonstrates how to integrate the metrics collector with vLLM configuration
testing for comprehensive performance analysis.

Author: Performance Engineer
Date: 2025-09-09
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import aiohttp
from datetime import datetime

# Import our metrics collector
from metrics_collector import MetricsCollector, VLLMMonitor


class VLLMConfigTester:
    """Test vLLM configurations with integrated metrics collection"""
    
    def __init__(
        self,
        vllm_url: str = "http://localhost:8080",
        embeddings_url: str = "http://localhost:8081",
        output_dir: Path = None
    ):
        """
        Initialize vLLM configuration tester
        
        Args:
            vllm_url: URL for main vLLM service (GPU 0)
            embeddings_url: URL for embeddings service (GPU 1)
            output_dir: Directory for test results
        """
        self.vllm_url = vllm_url
        self.embeddings_url = embeddings_url
        self.output_dir = output_dir or Path("/srv/luris/be/entity-extraction-service/tests/vllm_metrics")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def test_configuration(
        self,
        config_id: str,
        config_params: Dict[str, Any],
        test_prompts: List[str],
        test_duration: int = 60
    ) -> Dict[str, Any]:
        """
        Test a specific vLLM configuration with metrics collection
        
        Args:
            config_id: Unique identifier for this configuration
            config_params: vLLM configuration parameters
            test_prompts: List of prompts to test
            test_duration: Duration of test in seconds
            
        Returns:
            Test results with performance metrics
        """
        print(f"\n=== Testing Configuration: {config_id} ===")
        print(f"Parameters: {json.dumps(config_params, indent=2)}")
        
        # Create metrics collector
        collector = MetricsCollector(
            config_id=config_id,
            collection_interval=2.0,
            gpu_ids=[0, 1],  # Monitor both GPUs
            vllm_base_url=self.vllm_url,
            output_dir=self.output_dir
        )
        
        # Start metrics collection
        await collector.start(enable_display=False)
        
        try:
            # Run test workload
            results = await self._run_test_workload(
                config_params,
                test_prompts,
                test_duration,
                collector.vllm_monitor
            )
            
        finally:
            # Stop collection
            await collector.stop()
            
            # Export metrics
            json_path = collector.export_json(f"{config_id}_metrics.json")
            csv_path = collector.export_csv(f"{config_id}_metrics.csv")
            
            # Get summary statistics
            summary = collector.get_summary_statistics()
            
            # Combine results
            test_results = {
                "config_id": config_id,
                "config_params": config_params,
                "test_duration": test_duration,
                "workload_results": results,
                "performance_summary": summary,
                "metrics_files": {
                    "json": str(json_path),
                    "csv": str(csv_path)
                }
            }
            
            # Save complete test results
            results_file = self.output_dir / f"{config_id}_results.json"
            with open(results_file, 'w') as f:
                json.dump(test_results, f, indent=2)
            
            print(f"\n=== Configuration {config_id} Test Complete ===")
            print(f"Results saved to: {results_file}")
            
            return test_results
    
    async def _run_test_workload(
        self,
        config_params: Dict[str, Any],
        test_prompts: List[str],
        duration: int,
        vllm_monitor: VLLMMonitor
    ) -> Dict[str, Any]:
        """Run test workload against vLLM service"""
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            end_time = start_time + duration
            
            successful_requests = 0
            failed_requests = 0
            total_tokens = 0
            latencies = []
            
            # Cycle through prompts until time is up
            prompt_index = 0
            
            while time.time() < end_time:
                prompt = test_prompts[prompt_index % len(test_prompts)]
                
                # Prepare request
                request_data = {
                    "model": "mistral-nemo-12b-instruct-128k",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": config_params.get("temperature", 0.7),
                    "max_tokens": config_params.get("max_tokens", 200),
                    "top_p": config_params.get("top_p", 0.95)
                }
                
                try:
                    # Send request
                    request_start = time.time()
                    
                    async with session.post(
                        f"{self.vllm_url}/v1/chat/completions",
                        json=request_data,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # Calculate metrics
                            request_time = (time.time() - request_start) * 1000  # ms
                            tokens_generated = result["usage"]["completion_tokens"]
                            
                            # Record in monitor
                            vllm_monitor.record_request(request_time, tokens_generated)
                            
                            # Track results
                            successful_requests += 1
                            total_tokens += tokens_generated
                            latencies.append(request_time)
                            
                        else:
                            failed_requests += 1
                            print(f"Request failed with status {response.status}")
                            
                except asyncio.TimeoutError:
                    failed_requests += 1
                    print("Request timed out")
                    
                except Exception as e:
                    failed_requests += 1
                    print(f"Request error: {e}")
                
                # Move to next prompt
                prompt_index += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            # Calculate final statistics
            actual_duration = time.time() - start_time
            
            return {
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "total_requests": successful_requests + failed_requests,
                "success_rate": successful_requests / max(successful_requests + failed_requests, 1),
                "total_tokens": total_tokens,
                "avg_tokens_per_request": total_tokens / max(successful_requests, 1),
                "throughput_rps": successful_requests / actual_duration,
                "throughput_tokens_per_second": total_tokens / actual_duration,
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "min_latency_ms": min(latencies) if latencies else 0,
                "max_latency_ms": max(latencies) if latencies else 0
            }
    
    async def test_multiple_configurations(
        self,
        configurations: List[Dict[str, Any]],
        test_prompts: List[str],
        test_duration: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Test multiple vLLM configurations sequentially
        
        Args:
            configurations: List of configuration dictionaries with 'id' and 'params'
            test_prompts: List of prompts to test
            test_duration: Duration per configuration test
            
        Returns:
            List of test results for all configurations
        """
        all_results = []
        
        for config in configurations:
            # Test configuration
            result = await self.test_configuration(
                config_id=config["id"],
                config_params=config["params"],
                test_prompts=test_prompts,
                test_duration=test_duration
            )
            
            all_results.append(result)
            
            # Wait between tests
            print("\nWaiting 10 seconds before next configuration...")
            await asyncio.sleep(10)
        
        # Generate comparison report
        await self._generate_comparison_report(all_results)
        
        return all_results
    
    async def _generate_comparison_report(self, results: List[Dict[str, Any]]):
        """Generate a comparison report for multiple configurations"""
        
        report_path = self.output_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_path, 'w') as f:
            f.write("# vLLM Configuration Comparison Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("## Summary Table\n\n")
            f.write("| Config ID | Throughput (tokens/s) | Avg Latency (ms) | Success Rate | GPU 0 Util | GPU 1 Util |\n")
            f.write("|-----------|----------------------|------------------|--------------|------------|------------|\n")
            
            for result in results:
                config_id = result["config_id"]
                workload = result["workload_results"]
                summary = result["performance_summary"]
                
                gpu0_util = summary["gpu_statistics"].get("gpu_0", {}).get("avg_utilization", 0)
                gpu1_util = summary["gpu_statistics"].get("gpu_1", {}).get("avg_utilization", 0)
                
                f.write(f"| {config_id} | {workload['throughput_tokens_per_second']:.1f} | "
                       f"{workload['avg_latency_ms']:.1f} | {workload['success_rate']:.2%} | "
                       f"{gpu0_util:.1f}% | {gpu1_util:.1f}% |\n")
            
            f.write("\n## Detailed Results\n\n")
            
            for result in results:
                f.write(f"### Configuration: {result['config_id']}\n\n")
                f.write("**Parameters:**\n")
                f.write("```json\n")
                f.write(json.dumps(result['config_params'], indent=2))
                f.write("\n```\n\n")
                
                f.write("**Performance Metrics:**\n")
                workload = result["workload_results"]
                f.write(f"- Total Requests: {workload['total_requests']}\n")
                f.write(f"- Success Rate: {workload['success_rate']:.2%}\n")
                f.write(f"- Throughput: {workload['throughput_tokens_per_second']:.1f} tokens/s\n")
                f.write(f"- Average Latency: {workload['avg_latency_ms']:.1f} ms\n")
                f.write(f"- Min/Max Latency: {workload['min_latency_ms']:.1f}/{workload['max_latency_ms']:.1f} ms\n")
                f.write("\n")
            
            f.write("\n## Recommendations\n\n")
            
            # Find best configuration
            best_throughput = max(results, key=lambda x: x["workload_results"]["throughput_tokens_per_second"])
            best_latency = min(results, key=lambda x: x["workload_results"]["avg_latency_ms"])
            
            f.write(f"- **Best Throughput:** {best_throughput['config_id']} "
                   f"({best_throughput['workload_results']['throughput_tokens_per_second']:.1f} tokens/s)\n")
            f.write(f"- **Best Latency:** {best_latency['config_id']} "
                   f"({best_latency['workload_results']['avg_latency_ms']:.1f} ms)\n")
        
        print(f"\nComparison report saved to: {report_path}")


async def main():
    """Main test execution"""
    
    # Sample test prompts
    test_prompts = [
        "Extract all legal entities from this text: The case of Smith v. Jones, 123 F.3d 456 (2d Cir. 2020) establishes precedent.",
        "Identify the parties in this contract between Apple Inc. and Microsoft Corporation dated January 1, 2024.",
        "List all citations in: See Brown v. Board of Education, 347 U.S. 483 (1954); also Roe v. Wade, 410 U.S. 113 (1973).",
        "Find the jurisdiction mentioned in: Filed in the United States District Court for the Southern District of New York.",
        "Extract dates from: The agreement was signed on March 15, 2024 and expires on December 31, 2025."
    ]
    
    # Define configurations to test
    configurations = [
        {
            "id": "baseline_config",
            "params": {
                "temperature": 0.7,
                "max_tokens": 200,
                "top_p": 0.95
            }
        },
        {
            "id": "speed_optimized",
            "params": {
                "temperature": 0.1,
                "max_tokens": 100,
                "top_p": 0.8
            }
        },
        {
            "id": "quality_focused",
            "params": {
                "temperature": 0.5,
                "max_tokens": 300,
                "top_p": 0.98
            }
        }
    ]
    
    # Create tester
    tester = VLLMConfigTester()
    
    # Run tests
    results = await tester.test_multiple_configurations(
        configurations=configurations,
        test_prompts=test_prompts,
        test_duration=30  # 30 seconds per configuration for demo
    )
    
    print("\n=== All Tests Complete ===")
    print(f"Tested {len(results)} configurations")
    print(f"Results saved to: {tester.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())