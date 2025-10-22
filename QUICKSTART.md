# Entity Extraction Service - Quick Start Guide

## 🚀 Start the Service

```bash
# Start the service
sudo systemctl start luris-entity-extraction

# Wait 20 seconds for initialization
sleep 20

# Verify it's running
./verify_startup.sh
```

## ✅ Verify Service Health

```bash
# Check service status
sudo systemctl status luris-entity-extraction

# Check health endpoint
curl http://localhost:8007/api/v1/health
```

## 🔄 Restart the Service

```bash
# Restart the service
sudo systemctl restart luris-entity-extraction

# Wait for initialization
sleep 20

# Run verification
./verify_startup.sh
```

## 📊 Monitor the Service

```bash
# View real-time logs
sudo journalctl -u luris-entity-extraction -f

# Check memory usage
sudo systemctl show luris-entity-extraction --property=MemoryCurrent

# Check GPU usage (for vLLM backend)
nvidia-smi
```

## 🧪 Test the Service

```bash
# Test entity extraction
curl -X POST http://localhost:8007/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "test-001",
    "content": "Brown v. Board of Education, 347 U.S. 483 (1954)",
    "entity_types": ["case_citation"],
    "extraction_mode": "regex"
  }'

# Test relationship extraction
curl -X POST http://localhost:8007/api/v1/extract/relationships \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "test-002",
    "content": "In Rahimi v. United States, the Court cited Brown v. Board.",
    "entity_types": ["case_citation"]
  }'
```

## 📝 Key Information

- **Service Port**: 8007
- **Service Version**: 2.0.0
- **Startup Time**: ~20 seconds
- **Memory Limit**: 80GB (currently using ~594MB)
- **Patterns Loaded**: 511 patterns
- **Entity Types**: 31 legal entity types

## 🔧 Troubleshooting

### Service won't start
```bash
# Check dependencies
sudo systemctl status luris-vllm

# Check logs
sudo journalctl -u luris-entity-extraction -n 50
```

### Endpoints not responding
```bash
# Wait for full initialization (20 seconds)
sleep 20

# Check health
curl http://localhost:8007/api/v1/health
```

## 📚 Documentation

- **Full Documentation**: [README.md](README.md)
- **API Reference**: [api.md](api.md)
- **Deployment Readiness**: [DEPLOYMENT_READINESS.md](DEPLOYMENT_READINESS.md)
- **Startup Verification**: [STARTUP_VERIFIED.md](STARTUP_VERIFIED.md)
- **Development Guide**: [CLAUDE.md](../CLAUDE.md)
- **Testing Guide**: [TESTING.md](TESTING.md)

## ✅ Status

**Service Status**: ✅ Running and Verified
**Last Verification**: October 14, 2025
**Production Ready**: Yes
