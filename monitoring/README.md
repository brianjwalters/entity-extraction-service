# vLLM Performance Monitoring System

Comprehensive monitoring solution for vLLM services with GPU tracking, timeout warnings, and automated alerts.

## 📊 Overview

The monitoring system provides real-time tracking of:
- **GPU Utilization**: Memory usage, compute utilization, temperature
- **Service Response Times**: With multi-tier alerting
- **Timeout Warnings**: At 50%, 75%, and 90% of configured limits
- **Large Document Processing**: Performance metrics and progress tracking
- **System Health**: CPU, memory, and disk usage

## 🚀 Quick Start

### Check Current Performance

```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python monitoring/check_performance.py
```

### Start Monitoring Service

```bash
# Install monitoring service
sudo cp monitoring/luris-vllm-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable luris-vllm-monitor
sudo systemctl start luris-vllm-monitor

# Check status
sudo systemctl status luris-vllm-monitor
sudo journalctl -u luris-vllm-monitor -f
```

## 📈 Key Metrics & Thresholds

### Response Time Thresholds
| Level | Threshold | Action |
|-------|-----------|--------|
| **Normal** | < 30 seconds | No action |
| **Warning** | 30-60 seconds | Log warning |
| **Critical** | > 60 seconds | Generate alert |

### Timeout Warnings (30-minute limit)
| Level | Time Elapsed | Percentage | Alert Type |
|-------|-------------|------------|------------|
| **Info** | 15 minutes | 50% | Informational |
| **Warning** | 22.5 minutes | 75% | Warning alert |
| **Critical** | 27 minutes | 90% | Critical alert |

### GPU Memory Thresholds
| Level | Memory Usage | Action |
|-------|-------------|--------|
| **Normal** | < 85% | No action |
| **Warning** | 85-95% | Monitor closely |
| **Critical** | > 95% | Alert + potential OOM |

### GPU Temperature Thresholds
| Level | Temperature | Action |
|-------|------------|--------|
| **Normal** | < 80°C | No action |
| **Warning** | 80-85°C | Check cooling |
| **Critical** | > 85°C | Immediate attention |

## 🔧 Configuration

### Environment Variables

```bash
# Service URLs
VLLM_SERVICE_URL=http://localhost:8080
ENTITY_EXTRACTION_URL=http://localhost:8007
DOCUMENT_UPLOAD_URL=http://localhost:8008

# Monitoring intervals (seconds)
MONITORING_INTERVAL=30        # Service health checks
GPU_CHECK_INTERVAL=10         # GPU metrics collection
DASHBOARD_INTERVAL=300        # Dashboard generation (5 minutes)

# Alert configuration
ENABLE_AUTO_RECOVERY=false   # Enable automatic recovery actions
MAX_CONSECUTIVE_FAILURES=5   # Failures before escalation
ALERT_WEBHOOK_URL=           # Webhook for alerts (optional)
ALERT_EMAIL=                 # Email for alerts (optional)
```

### Configuration File (Optional)

Create `/srv/luris/be/monitoring/config.json`:

```json
{
  "vllm_service_url": "http://localhost:8080",
  "entity_extraction_url": "http://localhost:8007",
  "document_upload_url": "http://localhost:8008",
  "monitoring_interval": 30,
  "gpu_check_interval": 10,
  "enable_auto_recovery": false,
  "max_consecutive_failures": 5,
  "dashboard_interval": 300,
  "thresholds": {
    "response_time_warning": 30000,
    "response_time_critical": 60000,
    "timeout_warning_1": 50,
    "timeout_warning_2": 75,
    "timeout_critical": 90,
    "gpu_memory_warning": 85,
    "gpu_memory_critical": 95
  }
}
```

## 📁 Monitoring Components

### 1. vllm_monitor.py
Core monitoring engine with:
- GPU metrics collection via nvidia-smi
- Service health checks
- Timeout threshold monitoring
- Alert generation and processing
- Metrics export to JSON

### 2. monitor_integration.py
Integration layer for Entity Extraction Service:
- Document processing tracking
- Chunk-level monitoring
- Performance metric aggregation
- FastAPI endpoints for monitoring

### 3. monitor_service.py
Production monitoring service:
- Runs as systemd service
- Automatic alert escalation
- Optional auto-recovery actions
- Dashboard generation
- Alert notifications

### 4. check_performance.py
Manual performance check script:
- Instant GPU status
- Service health verification
- Inference speed testing
- System resource check
- Performance recommendations

## 📊 Monitoring Outputs

### Dashboard Files
Located in `/srv/luris/be/monitoring/logs/`:
- `dashboard_YYYYMMDD_HHMMSS.txt` - Performance dashboards
- `alerts.log` - Alert history
- `alerts.jsonl` - Structured alert logs
- `escalations.log` - Critical escalation events

### Metrics Export
Located in `/srv/luris/be/monitoring/metrics/`:
- `gpu_metrics_YYYYMMDD_HHMMSS.json` - GPU utilization data
- `service_metrics_YYYYMMDD_HHMMSS.json` - Service performance
- `alerts_YYYYMMDD_HHMMSS.json` - Alert summaries

## 🔍 Usage Examples

### Track Document Processing

```python
from monitoring.monitor_integration import MonitoringIntegration

# Initialize monitoring
monitor = MonitoringIntegration()
await monitor.initialize()

# Track document start
request_id = "doc_12345"
operation_id = monitor.track_document_start(
    request_id=request_id,
    document_path="/path/to/document.pdf",
    document_size_kb=1024,
    chunk_count=10
)

# Track chunk processing
for i in range(10):
    monitor.track_chunk_processing(
        request_id=request_id,
        chunk_index=i,
        chunk_size=100,
        processing_time_ms=850,
        success=True
    )

# Complete tracking
monitor.track_document_complete(
    request_id=request_id,
    success=True,
    total_chunks_processed=10,
    total_entities_extracted=25
)
```

### Get Monitoring Status

```python
# Get current status
status = await monitor.get_monitoring_status()
print(f"GPU Status: {status['gpu_status']}")
print(f"Health Score: {status['health_score']['overall_score']}")

# Generate performance report
report = await monitor.generate_performance_report()
print(report)
```

## 🚨 Alert Handling

### Alert Levels
1. **INFO**: Informational messages (50% timeout usage)
2. **WARNING**: Performance degradation (75% timeout, high memory)
3. **CRITICAL**: Immediate attention needed (90% timeout, OOM risk)
4. **EMERGENCY**: Service failure or escalation

### Alert Escalation
When `MAX_CONSECUTIVE_FAILURES` is reached:
1. Log escalation event
2. Send notifications (webhook/email if configured)
3. Trigger auto-recovery if enabled
4. Reset failure counter after recovery

### Auto-Recovery Actions
When enabled (`ENABLE_AUTO_RECOVERY=true`):
- Restart affected services
- Clear GPU cache if memory critical
- Reset monitoring counters
- Log recovery attempts

## 📉 Troubleshooting

### High GPU Memory Usage
```bash
# Check GPU status
nvidia-smi

# Clear GPU cache (if using PyTorch)
python -c "import torch; torch.cuda.empty_cache()"

# Restart vLLM service
sudo systemctl restart luris-vllm
```

### Slow Response Times
```bash
# Check active requests
python monitoring/check_performance.py

# Review recent alerts
tail -n 50 /srv/luris/be/monitoring/logs/alerts.log

# Check service logs
sudo journalctl -u luris-vllm -n 100
```

### Timeout Warnings
```bash
# Monitor active requests
watch -n 5 'tail /srv/luris/be/monitoring/logs/monitor_service.log'

# Check timeout percentages
grep "timeout" /srv/luris/be/monitoring/logs/alerts.jsonl | tail -10
```

## 🔄 Maintenance

### Log Rotation
Dashboards and metrics are automatically rotated:
- Dashboards: Keep last 48 files (4 days)
- Metrics: Keep last 1000 entries per type
- Alerts: Keep last 500 alerts

### Manual Cleanup
```bash
# Clean old dashboard files
find /srv/luris/be/monitoring/logs -name "dashboard_*.txt" -mtime +7 -delete

# Clean old metric exports
find /srv/luris/be/monitoring/metrics -name "*.json" -mtime +30 -delete
```

## 🏁 Best Practices

1. **Regular Monitoring**: Run `check_performance.py` before heavy workloads
2. **Alert Response**: Investigate warnings before they become critical
3. **Resource Planning**: Monitor trends for capacity planning
4. **Timeout Configuration**: Adjust timeouts based on document sizes
5. **GPU Management**: Keep GPU memory below 85% for stability

## 📚 Performance Optimization Tips

### For Large Documents
- Monitor chunk processing progress
- Watch for timeout warnings at 50% and 75%
- Consider splitting very large documents
- Adjust batch sizes based on GPU memory

### For High Throughput
- Monitor GPU utilization (should be >50% during processing)
- Check for CPU bottlenecks
- Optimize context window size
- Use batch processing when possible

### For Low Latency
- Keep GPU memory usage moderate (<70%)
- Monitor response time percentiles (p95, p99)
- Optimize model configuration
- Consider model quantization

## 🔗 Integration with Services

The monitoring system integrates with:
- **vLLM Service** (Port 8080): Model inference monitoring
- **Entity Extraction** (Port 8007): Document processing tracking
- **Document Upload** (Port 8008): File handling metrics
- **Performance Monitor**: Entity extraction performance tracking

## 📧 Support

For issues or questions:
1. Check monitoring logs: `/srv/luris/be/monitoring/logs/`
2. Review alerts: `tail -f /srv/luris/be/monitoring/logs/alerts.log`
3. Run performance check: `python monitoring/check_performance.py`
4. Check service status: `sudo systemctl status luris-vllm-monitor`