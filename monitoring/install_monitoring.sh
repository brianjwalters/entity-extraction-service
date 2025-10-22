#!/bin/bash

# vLLM Monitoring System Installation Script
# This script sets up the monitoring system for vLLM and Entity Extraction services

set -e

echo "==============================================="
echo "vLLM Monitoring System Installation"
echo "==============================================="

# Check if running as root/sudo
if [ "$EUID" -eq 0 ]; then
   echo "Please run this script as the ubuntu user, not as root"
   exit 1
fi

# Create monitoring directories
echo "Creating monitoring directories..."
sudo mkdir -p /srv/luris/be/monitoring/logs
sudo mkdir -p /srv/luris/be/monitoring/metrics
sudo chown -R ubuntu:ubuntu /srv/luris/be/monitoring

# Install Python dependencies
echo "Installing Python dependencies..."
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
pip install httpx psutil

# Make scripts executable
echo "Setting script permissions..."
chmod +x monitoring/check_performance.py
chmod +x monitoring/monitor_service.py
chmod +x monitoring/vllm_monitor.py
chmod +x monitoring/monitor_integration.py

# Install systemd service
echo "Installing systemd service..."
sudo cp monitoring/luris-vllm-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload

# Create default configuration
echo "Creating default configuration..."
cat > /srv/luris/be/monitoring/config.json << 'EOF'
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
    "gpu_memory_critical": 95,
    "gpu_utilization_low": 20,
    "gpu_temperature_warning": 80,
    "gpu_temperature_critical": 85,
    "error_rate_warning": 5,
    "error_rate_critical": 10
  }
}
EOF

echo ""
echo "==============================================="
echo "Installation Complete!"
echo "==============================================="
echo ""
echo "Available commands:"
echo ""
echo "1. Check current performance:"
echo "   cd /srv/luris/be/entity-extraction-service"
echo "   source venv/bin/activate"
echo "   python monitoring/check_performance.py"
echo ""
echo "2. Start monitoring service:"
echo "   sudo systemctl enable luris-vllm-monitor"
echo "   sudo systemctl start luris-vllm-monitor"
echo ""
echo "3. Check monitoring status:"
echo "   sudo systemctl status luris-vllm-monitor"
echo ""
echo "4. View monitoring logs:"
echo "   sudo journalctl -u luris-vllm-monitor -f"
echo ""
echo "5. View alerts:"
echo "   tail -f /srv/luris/be/monitoring/logs/alerts.log"
echo ""
echo "Configuration file: /srv/luris/be/monitoring/config.json"
echo "Monitoring logs: /srv/luris/be/monitoring/logs/"
echo "Metrics export: /srv/luris/be/monitoring/metrics/"
echo ""
echo "For more information, see: monitoring/README.md"
echo "==============================================="