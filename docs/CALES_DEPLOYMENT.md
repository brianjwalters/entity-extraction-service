# CALES Deployment Guide

## Overview

This guide provides complete instructions for deploying the CALES (Comprehensive AI Legal Entity System) Entity Extraction Service on Ubuntu with NVIDIA GPU support.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Installation Setup](#pre-installation-setup)
3. [Automated Deployment](#automated-deployment)
4. [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
6. [Service Management](#service-management)
7. [Validation and Testing](#validation-and-testing)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

## System Requirements

### Hardware Requirements

- **CPU**: 8+ cores recommended (Intel Xeon or AMD EPYC preferred)
- **RAM**: 32GB minimum, 64GB recommended
- **GPU**: NVIDIA A40 (48GB VRAM) or equivalent
  - RTX 3090/4090 (24GB VRAM) supported
  - A100 (40GB/80GB VRAM) optimal
- **Storage**: 500GB SSD minimum, 1TB+ recommended
  - Fast NVMe SSD for model cache
  - Additional storage for fine-tuned models

### Software Requirements

- **OS**: Ubuntu 20.04 LTS or 22.04 LTS
- **Python**: 3.8, 3.9, 3.10, or 3.11
- **CUDA**: 11.8+ or 12.x
- **Docker**: Optional, for containerized deployment
- **Git**: For source code management

### Network Requirements

- Internet connection for model downloads (initial setup)
- Access to HuggingFace Hub
- Port 8007 available for service API

## Pre-Installation Setup

### 1. Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential
```

### 2. Install NVIDIA Drivers and CUDA

```bash
# Install NVIDIA driver
sudo apt install -y nvidia-driver-535
sudo reboot

# Verify driver installation
nvidia-smi

# Install CUDA Toolkit
wget https://developer.download.nvidia.com/compute/cuda/12.2.2/local_installers/cuda_12.2.2_535.104.05_linux.run
sudo sh cuda_12.2.2_535.104.05_linux.run

# Add CUDA to PATH
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### 3. Install Python and Dependencies

```bash
# Install Python 3.10 (recommended)
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
```

### 4. Create Service User (Optional)

```bash
sudo useradd -r -s /bin/bash -d /srv/luris -m luris
sudo usermod -aG video luris  # GPU access
```

## Automated Deployment

### Quick Start (Recommended)

```bash
# Clone the repository (if not already done)
cd /srv/luris/be/entity-extraction-service

# Run the automated deployment script
chmod +x deploy/deploy_cales.sh
./deploy/deploy_cales.sh
```

### Deployment Options

```bash
# Full deployment with all options
./deploy/deploy_cales.sh

# Skip model downloads (for offline deployment)
./deploy/deploy_cales.sh --skip-models

# Force reinstall virtual environment
./deploy/deploy_cales.sh --force-reinstall

# Skip validation tests
./deploy/deploy_cales.sh --skip-tests

# Get help
./deploy/deploy_cales.sh --help
```

## Manual Installation

### 1. Create Directory Structure

```bash
sudo mkdir -p /srv/luris/models/{base,fine-tuned,staging,production,archived,experimental}
sudo chown -R ubuntu:ubuntu /srv/luris/models
sudo chmod -R 755 /srv/luris/models
```

### 2. Setup Virtual Environment

```bash
cd /srv/luris/be/entity-extraction-service
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### 3. Install Python Dependencies

```bash
# Install CALES-specific requirements
pip install -r deploy/requirements_cales.txt

# Install base service requirements
pip install -r requirements.txt
```

### 4. Download SpaCy Models

```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md
python -m spacy download en_core_web_trf

# Install legal SpaCy model (Blackstone)
pip install https://blackstone-model.s3-eu-west-1.amazonaws.com/en_blackstone_proto-0.0.1.tar.gz
```

### 5. Initialize Base Models

```bash
# Run model initializer
python src/core/model_management/model_initializer.py --init

# Or use Python directly
python -c "
from src.core.model_management.model_initializer import ModelInitializer
initializer = ModelInitializer()
results = initializer.initialize_base_models()
print('Initialization results:', results)
"
```

### 6. Install Systemd Service

```bash
sudo cp deploy/systemd/luris-entity-extraction-cales.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable luris-entity-extraction-cales.service
```

## Configuration

### 1. Environment Variables

The service uses the following key environment variables:

```bash
# Core service settings
SERVICE_PORT=8007
SERVICE_HOST=0.0.0.0
LOG_LEVEL=INFO

# CALES-specific settings
CALES_MODEL_BASE_PATH=/srv/luris/models
CALES_CONFIG_PATH=/srv/luris/be/entity-extraction-service/config/models_config.yaml
CALES_GPU_MEMORY_FRACTION=0.8
CALES_MAX_BATCH_SIZE=16
CALES_MAX_SEQUENCE_LENGTH=512

# GPU and CUDA settings
CUDA_VISIBLE_DEVICES=0,1
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024

# Cache directories
TRANSFORMERS_CACHE=/srv/luris/models/cache/transformers
HF_HOME=/srv/luris/models/cache/huggingface
TORCH_HOME=/srv/luris/models/cache/torch
```

### 2. Model Configuration

Edit `/srv/luris/be/entity-extraction-service/config/models_config.yaml`:

```yaml
model_repository:
  base_path: "/srv/luris/models"
  max_total_size_gb: 100

available_models:
  base_models:
    bert_ner:
      model_id: "bert-base-ner-v1"
      huggingface_id: "dslim/bert-base-NER"
      # ... other settings
```

### 3. Service Configuration

The `.env` file contains additional service configuration:

```bash
# Database settings
DATABASE_URL=postgresql://user:pass@localhost/luris
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# External services
LOG_SERVICE_URL=http://localhost:8001
PROMPT_SERVICE_URL=http://localhost:8003
```

## Service Management

### Starting the Service

```bash
# Start the service
sudo systemctl start luris-entity-extraction-cales.service

# Enable auto-start on boot
sudo systemctl enable luris-entity-extraction-cales.service

# Check service status
sudo systemctl status luris-entity-extraction-cales.service
```

### Monitoring Logs

```bash
# Follow service logs
sudo journalctl -u luris-entity-extraction-cales.service -f

# View recent logs
sudo journalctl -u luris-entity-extraction-cales.service -n 100

# Filter by log level
sudo journalctl -u luris-entity-extraction-cales.service -p err
```

### Service Commands

```bash
# Restart service
sudo systemctl restart luris-entity-extraction-cales.service

# Stop service
sudo systemctl stop luris-entity-extraction-cales.service

# Reload configuration
sudo systemctl reload luris-entity-extraction-cales.service

# View service configuration
systemctl cat luris-entity-extraction-cales.service
```

## Validation and Testing

### 1. Health Check

```bash
# Check service health
curl http://localhost:8007/health

# Expected response:
{
  "status": "healthy",
  "service": "entity-extraction-service",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 2. API Documentation

Access the interactive API documentation:
- **Swagger UI**: http://localhost:8007/docs
- **ReDoc**: http://localhost:8007/redoc

### 3. Basic Entity Extraction Test

```bash
# Test entity extraction
curl -X POST http://localhost:8007/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John Smith works at Microsoft in Seattle.",
    "model": "bert_ner",
    "strategy": "transformer"
  }'
```

### 4. Model Status Check

```bash
# Check model status
curl http://localhost:8007/api/v1/models/status
```

### 5. GPU Utilization Test

```bash
# Monitor GPU usage during extraction
nvidia-smi -l 1

# Check GPU memory usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

## Monitoring

### 1. System Monitoring

```bash
# GPU monitoring
watch -n 1 nvidia-smi

# Resource monitoring
htop
iostat -x 1
```

### 2. Service Metrics

The service exposes metrics at:
- **Prometheus metrics**: http://localhost:8007/metrics
- **Health endpoint**: http://localhost:8007/health
- **Model info**: http://localhost:8007/api/v1/models/info

### 3. Log Analysis

```bash
# Service performance logs
sudo journalctl -u luris-entity-extraction-cales.service | grep "performance"

# Error analysis
sudo journalctl -u luris-entity-extraction-cales.service -p err --since "1 hour ago"

# GPU memory issues
sudo journalctl -u luris-entity-extraction-cales.service | grep -i "cuda\|memory"
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check service status
sudo systemctl status luris-entity-extraction-cales.service

# Check for Python/dependency issues
source /srv/luris/be/entity-extraction-service/venv/bin/activate
python -c "import torch; print(torch.cuda.is_available())"

# Verify model files exist
ls -la /srv/luris/models/base/
```

#### 2. CUDA Out of Memory

```bash
# Check GPU memory usage
nvidia-smi

# Reduce batch size in configuration
export CALES_MAX_BATCH_SIZE=8
export CALES_GPU_MEMORY_FRACTION=0.6

# Restart service
sudo systemctl restart luris-entity-extraction-cales.service
```

#### 3. Model Download Failures

```bash
# Check internet connectivity
curl -I https://huggingface.co

# Manually download models
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python src/core/model_management/model_initializer.py --init --force
```

#### 4. Permission Issues

```bash
# Fix model directory permissions
sudo chown -R ubuntu:ubuntu /srv/luris/models
sudo chmod -R 755 /srv/luris/models

# Fix service directory permissions
sudo chown -R ubuntu:ubuntu /srv/luris/be/entity-extraction-service
```

#### 5. Port Already in Use

```bash
# Check what's using port 8007
sudo netstat -tlnp | grep :8007
sudo lsof -i :8007

# Kill competing process or change port
export SERVICE_PORT=8017
```

### Debug Mode

Run the service in debug mode:

```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
export LOG_LEVEL=DEBUG
python run.py --debug
```

### Performance Issues

```bash
# Check system resources
free -h
df -h
iostat -x 1

# Monitor model loading times
tail -f /var/log/luris-entity-extraction-cales.log | grep "model.*loaded"

# Profile memory usage
python -m memory_profiler run.py
```

## Maintenance

### 1. Model Updates

```bash
# Update base models
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python src/core/model_management/model_initializer.py --init --force

# Clean up old model versions
python src/core/model_management/model_initializer.py --cleanup
```

### 2. Dependency Updates

```bash
# Update Python dependencies
source venv/bin/activate
pip install --upgrade -r deploy/requirements_cales.txt

# Update SpaCy models
python -m spacy download en_core_web_trf --upgrade
```

### 3. Log Rotation

```bash
# Configure logrotate for service logs
sudo tee /etc/logrotate.d/luris-entity-extraction << EOF
/var/log/luris/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 0644 ubuntu ubuntu
    postrotate
        systemctl reload luris-entity-extraction-cales.service
    endscript
}
EOF
```

### 4. Backup Strategy

```bash
# Backup model registry
cp /srv/luris/models/registry.db /srv/luris/backups/

# Backup configuration
tar -czf /srv/luris/backups/cales-config-$(date +%Y%m%d).tar.gz \
    /srv/luris/be/entity-extraction-service/config/ \
    /srv/luris/be/entity-extraction-service/.env
```

### 5. Performance Optimization

#### GPU Memory Optimization

```bash
# Set conservative memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,expandable_segments:True
export CALES_GPU_MEMORY_FRACTION=0.7
```

#### Model Caching

```bash
# Warm up model cache
curl -X POST http://localhost:8007/api/v1/models/warmup

# Check cache hit rates
curl http://localhost:8007/metrics | grep cache_hit_rate
```

## Security Considerations

### 1. Network Security

```bash
# Configure firewall
sudo ufw allow 8007/tcp
sudo ufw enable

# Use reverse proxy (nginx/apache)
# Implement SSL/TLS termination
```

### 2. Service Security

```bash
# Run with restricted permissions
sudo systemctl edit luris-entity-extraction-cales.service

# Add security restrictions:
[Service]
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadOnlyPaths=/srv/luris/be/entity-extraction-service
```

### 3. Model Security

```bash
# Verify model checksums
python src/core/model_management/model_initializer.py --verify

# Enable model signing
export CALES_VERIFY_MODEL_SIGNATURES=true
```

## Performance Tuning

### GPU Configuration

```bash
# Set GPU persistence mode
sudo nvidia-smi -pm 1

# Set GPU performance mode
sudo nvidia-smi -ac memory_clock,graphics_clock

# Monitor GPU utilization
nvidia-smi dmon -s pucvmet
```

### CPU Optimization

```bash
# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Optimize Python threading
export OMP_NUM_THREADS=4
export TOKENIZERS_PARALLELISM=false
```

## Deployment Verification Checklist

- [ ] System requirements met
- [ ] NVIDIA drivers installed and working
- [ ] CUDA toolkit installed
- [ ] Python environment setup
- [ ] All dependencies installed
- [ ] Base models downloaded
- [ ] Service configuration correct
- [ ] Systemd service enabled
- [ ] Health check passes
- [ ] API documentation accessible
- [ ] Entity extraction test successful
- [ ] GPU utilization working
- [ ] Logs are being written
- [ ] Monitoring setup complete

## Support and Resources

- **API Documentation**: http://localhost:8007/docs
- **Service Logs**: `sudo journalctl -u luris-entity-extraction-cales.service -f`
- **Model Configuration**: `/srv/luris/be/entity-extraction-service/config/models_config.yaml`
- **Health Check Script**: Run `./deploy/health_check.sh`

For additional support or troubleshooting, check the service logs and refer to the error messages for specific guidance.