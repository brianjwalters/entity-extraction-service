# vLLM Metrics Collection System

## Overview

The metrics collection system provides comprehensive real-time monitoring of vLLM performance optimization testing. It collects GPU, vLLM service, and system metrics at configurable intervals and exports data for analysis.

## Features

### 1. GPU Metrics Collection
- **Real-time monitoring** of both GPUs using nvidia-smi
- **Metrics collected**:
  - GPU utilization percentage
  - Memory usage (used/free/total)
  - Temperature monitoring
  - Power consumption
- **Collection interval**: Every 2 seconds (configurable)

### 2. vLLM Performance Metrics
- **Throughput metrics**:
  - Tokens per second
  - Request processing rate
- **Latency metrics**:
  - First token latency
  - Mean generation latency
  - P50, P90, P99 percentiles
- **Queue metrics**:
  - Request queue size
  - Active batch size

### 3. System Metrics
- CPU utilization
- System memory usage
- Network I/O statistics
- Disk I/O statistics

### 4. Data Export
- **JSON format**: Complete metrics with nested structure
- **CSV format**: Flattened metrics for spreadsheet analysis
- **Real-time display**: Optional console dashboard
- **Summary statistics**: Aggregated metrics per test run

## Installation

```bash
# Required system packages
sudo apt-get update
sudo apt-get install -y nvidia-utils-535  # Or your NVIDIA driver version

# Python dependencies
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
pip install psutil aiohttp numpy
```

## Usage

### Basic Metrics Collection

```python
from metrics_collector import MetricsCollector
import asyncio

async def collect_metrics():
    # Create collector
    collector = MetricsCollector(
        config_id="test_config_001",
        collection_interval=2.0,  # Collect every 2 seconds
        gpu_ids=[0, 1],           # Monitor both GPUs
        vllm_base_url="http://localhost:8080"
    )
    
    # Start collection
    await collector.start(enable_display=True)
    
    # Run your test workload here
    await asyncio.sleep(60)  # Collect for 60 seconds
    
    # Stop and export
    await collector.stop()
    collector.export_json()
    collector.export_csv()
    
    # Get summary
    summary = collector.get_summary_statistics()
    print(summary)

# Run
asyncio.run(collect_metrics())
```

### Integration with vLLM Testing

```python
from vllm_metrics_integration import VLLMConfigTester

async def test_vllm_configs():
    tester = VLLMConfigTester()
    
    # Define test configurations
    configs = [
        {
            "id": "speed_optimized",
            "params": {
                "temperature": 0.1,
                "max_tokens": 100,
                "top_p": 0.8
            }
        }
    ]
    
    # Test with metrics collection
    results = await tester.test_multiple_configurations(
        configurations=configs,
        test_prompts=["Your test prompts here"],
        test_duration=60
    )

asyncio.run(test_vllm_configs())
```

## Data Structure

### Metrics Snapshot Format

```json
{
  "timestamp": "2025-09-09T10:30:00",
  "config_id": "dual_gpu_config_021",
  "gpu_metrics": {
    "gpu_0": {
      "utilization": 85,
      "memory_used_mb": 40000,
      "memory_free_mb": 5000,
      "memory_total_mb": 45000,
      "temp_c": 72,
      "power_w": 250
    },
    "gpu_1": {
      "utilization": 80,
      "memory_used_mb": 38000,
      "memory_free_mb": 7000,
      "memory_total_mb": 45000,
      "temp_c": 70,
      "power_w": 240
    }
  },
  "vllm_metrics": {
    "tokens_per_second": 15000,
    "first_token_latency_ms": 120,
    "mean_latency_ms": 85,
    "p50_latency_ms": 80,
    "p90_latency_ms": 120,
    "p99_latency_ms": 150,
    "request_queue_size": 5,
    "active_batch_size": 32
  },
  "system_metrics": {
    "cpu_percent": 45,
    "memory_gb": 32,
    "memory_available_gb": 96,
    "network_sent_bytes": 1048576,
    "network_recv_bytes": 2097152
  }
}
```

## Output Files

### Directory Structure
```
/srv/luris/be/entity-extraction-service/tests/
├── metrics_output/                      # Default output directory
│   ├── metrics_<config>_<timestamp>.json
│   ├── metrics_<config>_<timestamp>.csv
│   └── summary_statistics.json
└── vllm_metrics/                       # Integration test results
    ├── <config_id>_metrics.json
    ├── <config_id>_metrics.csv
    ├── <config_id>_results.json
    └── comparison_report_<timestamp>.md
```

## Real-time Monitoring

Enable the real-time display to see metrics during collection:

```python
await collector.start(enable_display=True)
```

This shows a console dashboard with:
- GPU utilization and memory for each GPU
- vLLM throughput and latency metrics
- System CPU and memory usage
- Updates every collection interval

## Summary Statistics

The collector automatically calculates:
- **GPU Statistics**: Average/max utilization and memory usage per GPU
- **vLLM Statistics**: Average/max throughput, latency percentiles
- **System Statistics**: Average/max CPU and memory usage

Access via:
```python
summary = collector.get_summary_statistics()
```

## Performance Tips

1. **Collection Interval**: 2 seconds provides good granularity without excessive overhead
2. **GPU Selection**: Monitor only the GPUs actually used by vLLM to reduce overhead
3. **Export Format**: Use JSON for detailed analysis, CSV for spreadsheet tools
4. **Memory Management**: The collector uses deques with max length to prevent memory issues during long tests

## Troubleshooting

### nvidia-smi not found
```bash
# Install NVIDIA drivers and utilities
sudo apt-get install nvidia-utils-535
```

### Permission denied for GPU monitoring
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and back in
```

### vLLM metrics not collecting
- Verify vLLM service is running: `curl http://localhost:8080/health`
- Check if Prometheus metrics endpoint is enabled in vLLM
- Ensure the collector is recording requests via `record_request()`

## Integration with vLLM Configurations

The system is designed to work with the vLLM configuration generator:

```python
# Load configuration
with open('vllm_configs/config_001.json') as f:
    config = json.load(f)

# Test with metrics
result = await tester.test_configuration(
    config_id=config['config_id'],
    config_params=config['llm_params'],
    test_prompts=prompts,
    test_duration=60
)
```

## Example Analysis

After collecting metrics, analyze performance:

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load CSV data
df = pd.read_csv('metrics_output/metrics_test_001.csv')

# Plot GPU utilization over time
plt.figure(figsize=(12, 6))
plt.plot(df.index, df['gpu_0_utilization'], label='GPU 0')
plt.plot(df.index, df['gpu_1_utilization'], label='GPU 1')
plt.xlabel('Time (samples)')
plt.ylabel('GPU Utilization (%)')
plt.legend()
plt.title('GPU Utilization During vLLM Testing')
plt.show()

# Analyze throughput correlation with latency
plt.scatter(df['tokens_per_second'], df['mean_latency_ms'])
plt.xlabel('Throughput (tokens/s)')
plt.ylabel('Mean Latency (ms)')
plt.title('Throughput vs Latency Trade-off')
plt.show()
```

## Support

For issues or questions about the metrics collection system:
1. Check the logs in the console output
2. Verify all services are running correctly
3. Ensure proper GPU driver installation
4. Review the test configuration parameters