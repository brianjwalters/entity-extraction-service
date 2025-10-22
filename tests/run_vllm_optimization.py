#!/usr/bin/env python3
"""
vLLM Optimization Test Runner
Tests different vLLM configurations and generates performance report
"""

import subprocess
import time
import json
import requests
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simplified vLLM configurations that work with current API
VLLM_CONFIGS = [
    {
        "id": "single_gpu_baseline",
        "name": "Single GPU Baseline (85% memory)",
        "env": {"CUDA_VISIBLE_DEVICES": "0"},
        "args": [
            "--model", "mistralai/Mistral-Nemo-Instruct-2407",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--tensor-parallel-size", "1",
            "--gpu-memory-utilization", "0.85",
            "--max-model-len", "128000",
            "--max-num-seqs", "64",
            "--served-model-name", "mistral-nemo-12b-instruct-128k",
            "--trust-remote-code"
        ]
    },
    {
        "id": "single_gpu_optimized",
        "name": "Single GPU Optimized (95% memory + caching)",
        "env": {"CUDA_VISIBLE_DEVICES": "0"},
        "args": [
            "--model", "mistralai/Mistral-Nemo-Instruct-2407",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--tensor-parallel-size", "1",
            "--gpu-memory-utilization", "0.95",
            "--max-model-len", "128000",
            "--max-num-seqs", "128",
            "--served-model-name", "mistral-nemo-12b-instruct-128k",
            "--enable-prefix-caching",
            "--enable-chunked-prefill",
            "--trust-remote-code"
        ]
    },
    {
        "id": "dual_gpu_tensor_parallel",
        "name": "Dual GPU Tensor Parallel",
        "env": {"CUDA_VISIBLE_DEVICES": "0,1"},
        "args": [
            "--model", "mistralai/Mistral-Nemo-Instruct-2407",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--tensor-parallel-size", "2",
            "--gpu-memory-utilization", "0.90",
            "--max-model-len", "128000",
            "--max-num-seqs", "256",
            "--served-model-name", "mistral-nemo-12b-instruct-128k",
            "--enable-prefix-caching",
            "--enable-chunked-prefill",
            "--trust-remote-code"
        ]
    }
]

def stop_vllm():
    """Stop any running vLLM service."""
    logger.info("Stopping vLLM service...")
    subprocess.run(["sudo", "systemctl", "stop", "luris-vllm"], capture_output=True)
    subprocess.run(["sudo", "fuser", "-k", "8080/tcp"], capture_output=True)
    time.sleep(5)

def start_vllm(config):
    """Start vLLM with given configuration."""
    logger.info(f"Starting vLLM config: {config['name']}")
    
    # Build command
    cmd = ["/srv/luris/be/vllm/.venv/bin/python", "-m", "vllm.entrypoints.openai.api_server"]
    cmd.extend(config['args'])
    
    # Set environment
    import os
    env = os.environ.copy()
    env.update(config['env'])
    
    # Start process
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for service to be ready
    logger.info("Waiting for vLLM to start (up to 120 seconds)...")
    start_time = time.time()
    while time.time() - start_time < 120:
        try:
            response = requests.get("http://localhost:8080/health", timeout=2)
            if response.status_code == 200:
                logger.info("✓ vLLM service is ready!")
                return process
        except:
            pass
        time.sleep(2)
    
    logger.error("✗ vLLM failed to start")
    process.terminate()
    return None

def test_extraction(document_path="/srv/luris/be/tests/docs/Rahimi.pdf"):
    """Test entity extraction performance."""
    logger.info(f"Testing extraction on: {document_path}")
    
    try:
        # Upload document
        with open(document_path, 'rb') as f:
            upload_resp = requests.post(
                "http://localhost:8008/api/v1/upload",
                files={"file": f},
                timeout=60
            )
        
        if upload_resp.status_code != 200:
            logger.error(f"Upload failed: {upload_resp.status_code}")
            return None
        
        upload_data = upload_resp.json()
        
        # Extract entities
        start_time = time.time()
        extract_resp = requests.post(
            "http://localhost:8007/api/v1/extract",
            json={
                "document_id": upload_data.get("document_id"),
                "text": upload_data.get("markdown_content", ""),
                "strategy": "AI_ENHANCED",
                "options": {
                    "extract_citations": True,
                    "confidence_threshold": 0.6
                }
            },
            timeout=300
        )
        
        extraction_time = time.time() - start_time
        
        if extract_resp.status_code != 200:
            logger.error(f"Extraction failed: {extract_resp.status_code}")
            return None
        
        data = extract_resp.json()
        entities = data.get("entities", [])
        
        # Count entity types
        entity_types = {}
        for entity in entities:
            etype = entity.get("type", "UNKNOWN")
            entity_types[etype] = entity_types.get(etype, 0) + 1
        
        return {
            "extraction_time_seconds": extraction_time,
            "total_entities": len(entities),
            "entity_types": entity_types,
            "citations_count": len(data.get("citations", [])),
            "sample_entities": entities[:5]  # First 5 entities
        }
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return None

def get_gpu_metrics():
    """Get current GPU metrics."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used,temperature.gpu", 
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        
        metrics = {}
        for line in result.stdout.strip().split('\n'):
            parts = line.split(', ')
            if len(parts) >= 4:
                gpu_id = parts[0]
                metrics[f"gpu_{gpu_id}"] = {
                    "utilization": float(parts[1]),
                    "memory_mb": float(parts[2]),
                    "temperature": float(parts[3])
                }
        return metrics
    except:
        return {}

def main():
    """Main test execution."""
    results = []
    
    # Ensure services are running
    logger.info("Checking required services...")
    for port, service in [(8007, "entity-extraction"), (8008, "document-upload")]:
        try:
            resp = requests.get(f"http://localhost:{port}/api/v1/health", timeout=2)
            if resp.status_code == 200:
                logger.info(f"✓ {service} service is healthy")
            else:
                logger.error(f"✗ {service} service is not healthy")
                sys.exit(1)
        except:
            logger.error(f"✗ {service} service is not running on port {port}")
            logger.info(f"Start it with: sudo systemctl start luris-{service}")
            sys.exit(1)
    
    # Test each configuration
    for config in VLLM_CONFIGS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {config['name']}")
        logger.info(f"{'='*60}")
        
        # Stop existing vLLM
        stop_vllm()
        
        # Start new configuration
        vllm_process = start_vllm(config)
        if not vllm_process:
            logger.error(f"Failed to start config: {config['id']}")
            continue
        
        try:
            # Get initial GPU metrics
            gpu_before = get_gpu_metrics()
            
            # Run extraction test
            test_result = test_extraction()
            
            # Get final GPU metrics
            gpu_after = get_gpu_metrics()
            
            if test_result:
                result = {
                    "config_id": config["id"],
                    "config_name": config["name"],
                    "timestamp": datetime.now().isoformat(),
                    "extraction_results": test_result,
                    "gpu_metrics": {
                        "before": gpu_before,
                        "after": gpu_after
                    }
                }
                results.append(result)
                
                logger.info(f"✓ Test completed successfully!")
                logger.info(f"  Time: {test_result['extraction_time_seconds']:.2f}s")
                logger.info(f"  Entities: {test_result['total_entities']}")
                logger.info(f"  GPU 0: {gpu_after.get('gpu_0', {}).get('utilization', 0):.1f}%")
                if 'gpu_1' in gpu_after:
                    logger.info(f"  GPU 1: {gpu_after.get('gpu_1', {}).get('utilization', 0):.1f}%")
            
        finally:
            # Stop vLLM
            logger.info("Stopping vLLM...")
            vllm_process.terminate()
            try:
                vllm_process.wait(timeout=10)
            except:
                vllm_process.kill()
    
    # Save results
    output_dir = Path("/srv/luris/be/entity-extraction-service/tests/results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"vllm_optimization_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    for result in results:
        extraction = result['extraction_results']
        logger.info(f"\nConfiguration: {result['config_name']}")
        logger.info(f"  Extraction Time: {extraction['extraction_time_seconds']:.2f}s")
        logger.info(f"  Total Entities: {extraction['total_entities']}")
        logger.info(f"  Entity Types: {len(extraction['entity_types'])}")
        
        gpu_after = result['gpu_metrics']['after']
        for gpu_id in sorted(gpu_after.keys()):
            metrics = gpu_after[gpu_id]
            logger.info(f"  {gpu_id.upper()}: {metrics['utilization']:.1f}% util, "
                       f"{metrics['memory_mb']:.0f}MB mem, {metrics['temperature']:.0f}°C")
    
    logger.info(f"\n✓ Results saved to: {output_file}")
    
    # Find best configuration
    if results:
        best_speed = min(results, key=lambda x: x['extraction_results']['extraction_time_seconds'])
        best_entities = max(results, key=lambda x: x['extraction_results']['total_entities'])
        
        logger.info(f"\n🏆 Best for Speed: {best_speed['config_name']}")
        logger.info(f"   Time: {best_speed['extraction_results']['extraction_time_seconds']:.2f}s")
        
        logger.info(f"\n🏆 Best for Accuracy: {best_entities['config_name']}")
        logger.info(f"   Entities: {best_entities['extraction_results']['total_entities']}")
    
    # Restart default vLLM service
    logger.info("\nRestarting default vLLM service...")
    subprocess.run(["sudo", "systemctl", "start", "luris-vllm"], capture_output=True)

if __name__ == "__main__":
    main()