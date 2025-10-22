# Migration Guide: v2.0.0 → v2.0.1

**Entity Extraction Service - Configuration & Schema Migration**

## Overview

Version 2.0.1 includes **two major breaking changes**:
1. **Configuration Migration**: YAML → .env (48 new variables added)
2. **Entity Schema Changes**: Field renamed from `type` to `entity_type`

**Estimated Migration Time**: 15-30 minutes

**Downtime Required**: Yes (service restart needed)

---

## ⚠️ Breaking Changes Summary

### Configuration
- YAML configuration (`config/settings.yaml`) **completely removed**
- All settings now managed through `.env` (161 total variables)
- 48 new environment variables added across 3 new sections

### Entity Schema
- `type` field renamed to `entity_type` in all entity objects
- `entities` field now required (never null/undefined)
- `confidence` field now required with minimum 0.7 threshold

---

## Part 1: Configuration Migration

### Step 1: Backup Current Configuration

```bash
# Navigate to service directory
cd /srv/luris/be/entity-extraction-service

# Backup current .env
cp .env .env.backup.$(date +%Y%m%d-%H%M%S)

# Archive YAML configuration
mkdir -p config/archive
mv config/settings.yaml config/archive/settings.yaml.deprecated
```

### Step 2: Create New .env File

```bash
# Copy template
cp .env.example .env

# Edit with your settings
nano .env
```

### Step 3: Required Environment Variables

**You MUST set these variables before service will start:**

```bash
# Database - Supabase (ALL 4 REQUIRED)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_API_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here

# Service Configuration
SERVICE_URL=http://your-server-ip:8007
SECRET_KEY=generate-secure-random-string-here

# vLLM Integration
AI_EXTRACTION_VLLM_URL=http://your-server-ip:8080/v1

# Service URLs (Replace YOUR_SERVER_IP with actual IP)
LOG_SERVICE_URL=http://YOUR_SERVER_IP:8001
PROMPT_SERVICE_URL=http://YOUR_SERVER_IP:8003
DOCUMENT_UPLOAD_SERVICE_URL=http://YOUR_SERVER_IP:8008
GRAPHRAG_SERVICE_URL=http://YOUR_SERVER_IP:8010
DOCUMENT_PROCESSING_SERVICE_URL=http://YOUR_SERVER_IP:8000
WEBSOCKET_SERVICE_URL=http://YOUR_SERVER_IP:8085

# Security
JWT_SECRET=generate-secure-jwt-secret-here
```

### Step 4: New Configuration Sections

#### Logging Configuration (14 variables)

```bash
LOGGING__ENABLE_STRUCTURED_LOGGING=true
LOGGING__LOG_FORMAT=json
LOGGING__LOG_EXTRACTION_DETAILS=true
LOGGING__LOG_PATTERN_MATCHING=false
LOGGING__LOG_AI_REQUESTS=true
LOGGING__LOG_PERFORMANCE_METRICS=true
LOGGING__ENABLE_REQUEST_ID_LOGGING=true
LOGGING__LOG_REQUEST_BODY=false
LOGGING__LOG_RESPONSE_BODY=false
LOGGING__ENABLE_FILE_LOGGING=true
LOGGING__LOG_FILE_PATH=logs/entity-extraction.log
LOGGING__LOG_ROTATION_SIZE_MB=100
LOGGING__LOG_RETENTION_DAYS=30
LOGGING__LOG_LEVEL_OVERRIDE=
```

#### Health Check Configuration (11 variables)

```bash
HEALTH__ENABLE_HEALTH_CHECKS=true
HEALTH__HEALTH_CHECK_INTERVAL_SECONDS=30
HEALTH__HEALTH_CHECK_TIMEOUT_SECONDS=5
HEALTH__CHECK_PATTERN_LOADER=true
HEALTH__CHECK_AI_SERVICES=true
HEALTH__CHECK_DATABASE_CONNECTION=true
HEALTH__CHECK_MEMORY_USAGE=true
HEALTH__MEMORY_WARNING_THRESHOLD_PERCENT=80.0
HEALTH__MEMORY_CRITICAL_THRESHOLD_PERCENT=95.0
HEALTH__EXTRACTION_LATENCY_WARNING_MS=5000
HEALTH__EXTRACTION_LATENCY_CRITICAL_MS=15000
```

#### Performance Monitoring (10 variables)

```bash
PERFORMANCE__ENABLE_PERFORMANCE_MONITORING=true
PERFORMANCE__PERFORMANCE_SAMPLE_RATE=0.1
PERFORMANCE__ENABLE_METRICS_EXPORT=true
PERFORMANCE__MAX_MEMORY_USAGE_MB=2048
PERFORMANCE__MEMORY_CHECK_INTERVAL_SECONDS=60
PERFORMANCE__ENABLE_MEMORY_CLEANUP=true
PERFORMANCE__MAX_WORKER_THREADS=10
PERFORMANCE__THREAD_POOL_SIZE=8
PERFORMANCE__RESULT_CACHE_SIZE=1000
PERFORMANCE__RESULT_CACHE_TTL_SECONDS=1800
```

### Step 5: Restart Service

```bash
# Restart with systemd
sudo systemctl restart luris-entity-extraction

# Verify service started
sudo systemctl status luris-entity-extraction

# Check logs for errors
sudo journalctl -u luris-entity-extraction -n 50 --no-pager
```

### Step 6: Validate Configuration

```bash
# Check health endpoint
curl http://localhost:8007/api/v1/health/detailed | jq

# Should return:
# {
#   "status": "healthy",
#   "service": "entity-extraction-service",
#   "version": "2.0.1",
#   ...
# }

# Test extraction
curl -X POST http://localhost:8007/api/v2/process/extract \
  -H "Content-Type: application/json" \
  -d '{
    "content": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Court held...",
    "document_id": "test_migration"
  }'
```

---

## Part 2: Entity Schema Migration

### Step 1: Update Client Code

#### Python Client

```python
# ❌ OLD (v2.0.0) - WILL FAIL
def process_entity_old(entity: dict):
    entity_type = entity["type"]  # KeyError: 'type'
    confidence = entity.get("confidence", 0.8)  # Optional before

    if entity.type == "CASE_CITATION":  # AttributeError
        return parse_citation(entity)

# ✅ NEW (v2.0.1) - CORRECT
def process_entity_new(entity: dict):
    entity_type = entity["entity_type"]  # Required field
    confidence = entity["confidence"]  # Required field (≥ 0.7)

    if entity.entity_type == "CASE_CITATION":
        return parse_citation(entity)
```

#### JavaScript/TypeScript Client

```typescript
// ❌ OLD (v2.0.0) - WILL FAIL
interface EntityOld {
  type: string;
  text: string;
  confidence?: number;
}

function processEntity(entity: EntityOld) {
  console.log(entity.type);  // Undefined in v2.0.1
}

// ✅ NEW (v2.0.1) - CORRECT
interface EntityNew {
  entity_type: string;
  text: string;
  confidence: number;  // Required, minimum 0.7
}

function processEntity(entity: EntityNew) {
  console.log(entity.entity_type);

  // Validate confidence
  if (entity.confidence < 0.7) {
    throw new Error('Invalid entity confidence');
  }
}
```

### Step 2: Update Response Parsing

```python
# ❌ OLD - Assumed entities could be null
response = api.extract(document)
entities = response.get("entities") or []  # Defensive check
for entity in entities:
    print(entity.get("type", "UNKNOWN"))

# ✅ NEW - entities is always present, use entity_type
response = api.extract(document)
entities = response["entities"]  # Required field, never null
for entity in entities:
    print(entity["entity_type"])  # Required field
    assert entity["confidence"] >= 0.7  # Guaranteed
```

### Step 3: Update Test Code

```python
# Update all test assertions
def test_entity_extraction():
    result = extract_entities(test_content)

    # ❌ OLD
    # assert result["entities"][0]["type"] == "CASE_CITATION"

    # ✅ NEW
    assert result["entities"][0]["entity_type"] == "CASE_CITATION"
    assert result["entities"][0]["confidence"] >= 0.7
    assert "entities" in result  # Always present
```

### Step 4: Update Database Queries

If you store entities in a database:

```sql
-- Update schema
ALTER TABLE extracted_entities
  RENAME COLUMN type TO entity_type;

-- Update existing records (if storing raw JSON)
UPDATE extracted_entities
SET entity_data = jsonb_set(
  entity_data - 'type',
  '{entity_type}',
  entity_data->'type'
)
WHERE entity_data ? 'type';

-- Add confidence validation
ALTER TABLE extracted_entities
  ADD CONSTRAINT entity_confidence_check
  CHECK ((entity_data->>'confidence')::float >= 0.7);
```

---

## Validation Checklist

### Configuration Validation

- [ ] `.env` file created with all 161 variables
- [ ] All required variables set (SUPABASE_*, SERVICE_URL, JWT_SECRET)
- [ ] Service URLs updated with correct IPs
- [ ] Service starts without errors: `sudo systemctl status luris-entity-extraction`
- [ ] Health endpoint returns healthy: `curl http://localhost:8007/api/v1/health`
- [ ] Extraction works: Test POST to `/api/v2/process/extract`

### Schema Validation

- [ ] Client code updated to use `entity_type` field
- [ ] Response parsing updated for required `entities` field
- [ ] Confidence validation added (minimum 0.7)
- [ ] Test code updated with new field names
- [ ] Database schema updated (if applicable)
- [ ] All integration tests passing

---

## Rollback Plan

If issues arise during migration:

### Rollback Configuration

```bash
cd /srv/luris/be/entity-extraction-service

# Restore backup .env
cp .env.backup.TIMESTAMP .env

# Restore YAML (only works if reverting to v2.0.0)
cp config/archive/settings.yaml.deprecated config/settings.yaml

# Downgrade to v2.0.0 (if needed)
git checkout v2.0.0

# Restart service
sudo systemctl restart luris-entity-extraction
```

### Rollback Client Code

```bash
# Revert client code changes
git revert <commit-hash>

# Deploy previous client version
```

---

## Troubleshooting

### Service Won't Start

**Error**: `ModuleNotFoundError` or configuration errors

**Solution**:
```bash
# Check .env file exists
ls -la /srv/luris/be/entity-extraction-service/.env

# Verify required variables set
grep "SUPABASE_URL" .env
grep "SUPABASE_KEY" .env
grep "SERVICE_URL" .env

# Check service logs
sudo journalctl -u luris-entity-extraction -n 100 --no-pager
```

### Entity Extraction Returns Empty Results

**Error**: Zero entities extracted after migration

**Solution**:
```bash
# Check vLLM service is running
curl http://localhost:8080/v1/models

# Verify extraction configuration
grep "EXTRACTION_" .env

# Test with simple document
curl -X POST http://localhost:8007/api/v2/process/extract \
  -H "Content-Type: application/json" \
  -d '{"content": "Test v. Example, 123 F.3d 456", "document_id": "test"}'
```

### Client Code Errors

**Error**: `KeyError: 'type'` or `AttributeError: 'type'`

**Solution**: Update all entity field references from `type` to `entity_type`

```python
# Find all references
grep -r "\.type" your_client_code/
grep -r '\["type"\]' your_client_code/

# Replace with
# .entity_type
# ["entity_type"]
```

---

## Post-Migration Verification

### Run Full Test Suite

```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Should show: All tests passing with new schema
```

### Performance Benchmark

```bash
# Compare extraction performance
curl -X POST http://localhost:8007/api/v2/process/extract \
  -H "Content-Type: application/json" \
  -d @tests/test_document.json \
  -w "Time: %{time_total}s\n"

# Should be similar to pre-migration performance
```

### Monitor Logs

```bash
# Watch logs for 5 minutes
sudo journalctl -u luris-entity-extraction -f

# Look for:
# ✅ No configuration warnings
# ✅ Successful entity extractions
# ✅ No schema validation errors
```

---

## Support

If you encounter issues during migration:

1. **Check Documentation**:
   - README.md - Configuration details
   - CHANGELOG.md - Complete change list
   - api.md - Schema documentation

2. **Review Logs**:
   ```bash
   sudo journalctl -u luris-entity-extraction -n 200 --no-pager
   ```

3. **Test Connectivity**:
   ```bash
   # Check all service dependencies
   curl http://localhost:8003/api/v1/health  # Prompt Service
   curl http://localhost:8001/api/v1/health  # Log Service
   curl http://localhost:8080/v1/models      # vLLM Service
   ```

4. **Validate Configuration**:
   ```bash
   # Check all required variables
   cat .env | grep -E "(SUPABASE_|SERVICE_URL|JWT_SECRET)"
   ```

---

## Summary

**Total Changes**:
- Configuration: 48 new variables, YAML removed
- Schema: `type` → `entity_type`, required fields added
- Code: Client code and tests updated

**Migration Time**: 15-30 minutes

**Downtime**: ~5 minutes for service restart

**Rollback**: Possible by restoring .env backup and reverting code changes

---

**Migration Complete!** 🎉

Your Entity Extraction Service is now running on v2.0.1 with:
- Modern .env-based configuration (161 variables)
- Enhanced entity schema with required fields
- Improved logging and monitoring capabilities
