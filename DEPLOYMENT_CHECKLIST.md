# Deployment Checklist: Entity Extraction Service v2.0.1

**Version**: 2.0.1
**Date**: 2025-10-15
**Status**: Ready for Deployment
**Estimated Deployment Time**: 15 minutes

---

## Pre-Deployment Checklist

### 1. Documentation Review
- [ ] Read `DEPLOYMENT_READINESS_REPORT_v2.0.1.md`
- [ ] Review `QUICK_REFERENCE_v2.0.1.md`
- [ ] Understand breaking changes in `MIGRATION_GUIDE_v2.0.1.md`
- [ ] Review rollback procedures

**Time**: 10 minutes

---

### 2. Resolve Known Blocker (P0)

**Issue**: HTTP client import error at line 681

**Location**: `/srv/luris/be/entity-extraction-service/src/core/extraction_orchestrator.py:681`

**Current Code**:
```python
from client.vllm_http_client import VLLMLocalClient
```

**Fix**:
```bash
cd /srv/luris/be/entity-extraction-service
sed -i 's|from client.vllm_http_client|from src.clients.vllm_http_client|g' src/core/extraction_orchestrator.py
```

**Verification**:
```bash
grep "from.*vllm_http_client" src/core/extraction_orchestrator.py
# Should show: from src.clients.vllm_http_client import VLLMLocalClient
```

- [ ] Fixed import path
- [ ] Verified fix with grep command

**Time**: 2 minutes

---

### 3. Environment Validation

**Run validation test suite**:
```bash
cd /srv/luris/be/entity-extraction-service
bash VALIDATION_TEST_SUITE.sh
```

**Expected Results**:
- All configuration tests pass
- All entity model tests pass
- All documentation files present
- Success rate: 100% (excluding skipped tests)

- [ ] Validation suite passed
- [ ] All critical tests green
- [ ] No blocking failures

**Time**: 2 minutes

---

### 4. Dependency Services Check

**Verify vLLM services are running**:

```bash
# Check vLLM Instruct service (GPU 0, port 8080)
curl -s http://localhost:8080/health | jq .

# Check vLLM Embeddings service (GPU 1, port 8081)
curl -s http://localhost:8081/health | jq .

# Check vLLM Thinking service (GPU 1, port 8082)
curl -s http://localhost:8082/health | jq .
```

**Expected**: Both services return healthy status

- [ ] vLLM Instruct service (port 8080) is running - Qwen3-VL-8B-Instruct-FP8
- [ ] vLLM Embeddings service (port 8081) is running - Jina Embeddings v4
- [ ] vLLM Thinking service (port 8082) is running - Qwen3-VL-8B-Thinking-FP8
- [ ] GPU memory usage is acceptable

**Time**: 1 minute

---

### 5. Backup Verification

**Verify backup exists**:
```bash
cd /srv/luris/be/entity-extraction-service
ls -lh .env.backup.20251015_020208
```

**Expected**: Backup file exists with recent timestamp

- [ ] Backup .env file confirmed
- [ ] Backup is readable
- [ ] Backup timestamp is correct

**Time**: 1 minute

---

### 6. Python Cache Cleanup

**Clear all Python cache**:
```bash
cd /srv/luris/be/entity-extraction-service
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
```

- [ ] __pycache__ directories removed
- [ ] .pyc files deleted
- [ ] No import cache issues

**Time**: 1 minute

---

## Deployment Execution

### 7. Configuration Test

**Test configuration loading**:
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python -c "from src.core.config import get_settings; s = get_settings(); print(f'✅ Loaded {len(s.__dict__)} settings')"
```

**Expected**: "✅ Loaded 161 settings" (approximately)

- [ ] Configuration loads without errors
- [ ] All 161+ settings present
- [ ] No missing environment variables

**Time**: 30 seconds

---

### 8. Entity Model Test

**Test entity schema**:
```bash
source venv/bin/activate
python -c "from src.core.entity_models import Entity, EntityType; e = Entity(entity_type=EntityType.PERSON, text='Test', confidence=0.95); print(f'✅ Entity: {e.entity_type.value}')"
```

**Expected**: "✅ Entity: PERSON"

- [ ] Entity model loads successfully
- [ ] entity_type field works correctly
- [ ] Required fields enforced

**Time**: 30 seconds

---

### 9. Service Restart

**Restart the service**:
```bash
sudo systemctl restart luris-entity-extraction
```

**Wait for startup** (model loading takes 30-50 seconds):
```bash
sleep 50
```

- [ ] Service restarted successfully
- [ ] Waited for model loading
- [ ] No immediate errors

**Time**: 1 minute

---

### 10. Health Check

**Verify service health**:
```bash
curl -s http://localhost:8007/api/health | jq .
```

**Expected**:
```json
{
  "status": "healthy",
  "service": "entity-extraction",
  "version": "2.0.1"
}
```

- [ ] Health endpoint responding
- [ ] Status is "healthy"
- [ ] Correct version reported

**Time**: 30 seconds

---

### 11. Service Status Verification

**Check systemd status**:
```bash
sudo systemctl status luris-entity-extraction
```

**Expected**: "active (running)" status

- [ ] Service is active
- [ ] No error messages in status
- [ ] Process is stable

**Time**: 30 seconds

---

## Post-Deployment Validation

### 12. Log Monitoring

**Monitor logs for errors**:
```bash
sudo journalctl -u luris-entity-extraction --since "1 minute ago"
```

**Check for errors**:
```bash
sudo journalctl -u luris-entity-extraction --since "1 minute ago" | grep -i error
```

**Expected**: No critical errors

- [ ] Logs show successful startup
- [ ] No import errors
- [ ] No configuration errors
- [ ] Models loaded successfully

**Time**: 2 minutes

---

### 13. Entity Extraction Test

**Test entity extraction endpoint**:
```bash
curl -X POST http://localhost:8007/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John Doe works at ACME Corporation in New York.",
    "mode": "entities_and_relationships"
  }' | jq .
```

**Expected**:
- Response contains entities array
- entity_type field present (not "type")
- confidence values between 0.7-1.0
- Valid JSON structure

- [ ] Extraction endpoint works
- [ ] Entities extracted correctly
- [ ] Schema is valid (entity_type field)
- [ ] Confidence values in range

**Time**: 1 minute

---

### 14. Guided JSON Validation

**Verify guided JSON responses**:
```bash
# Test response should be valid JSON
curl -X POST http://localhost:8007/api/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Apple Inc. was founded by Steve Jobs.", "mode": "entities_only"}' | jq .
```

**Expected**: Valid JSON with proper schema structure

- [ ] Response is valid JSON
- [ ] Schema matches entity models
- [ ] No malformed JSON
- [ ] Guided decoding working

**Time**: 1 minute

---

### 15. GPU Utilization Check

**Monitor GPU status**:
```bash
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv
```

**Expected**:
- GPU 0: Reasonable utilization during extraction
- GPU 1: Embeddings service loaded
- Memory usage within limits

- [ ] GPU utilization normal
- [ ] Memory usage acceptable
- [ ] No GPU errors

**Time**: 1 minute

---

### 16. Performance Validation

**Test configuration loading performance**:
```bash
source venv/bin/activate
python -c "
import time
from src.core.config import get_settings

# Initial load
start = time.time()
s1 = get_settings()
initial = time.time() - start

# Cached load
start = time.time()
s2 = get_settings()
cached = time.time() - start

print(f'Initial: {initial:.6f}s, Cached: {cached:.9f}s')
print(f'Improvement: {initial/cached:.0f}x faster')
"
```

**Expected**: Cached load should be 200x+ faster

- [ ] Initial load < 0.01s
- [ ] Cached load < 0.00001s
- [ ] Performance improvement validated

**Time**: 30 seconds

---

## Monitoring Setup

### 17. Enable Continuous Monitoring

**Set up log monitoring** (in separate terminal):
```bash
sudo journalctl -u luris-entity-extraction -f
```

**Set up GPU monitoring** (in separate terminal):
```bash
watch -n 5 nvidia-smi
```

- [ ] Log monitoring active
- [ ] GPU monitoring active
- [ ] Ready to observe production traffic

**Time**: 1 minute

---

### 18. Document Deployment

**Record deployment details**:
```bash
cat >> deployment_log.txt << EOF
Deployment: Entity Extraction Service v2.0.1
Date: $(date)
Deployed by: $USER
Status: SUCCESS
Changes: YAML→.env migration, entity schema fixes, guided JSON enabled
EOF
```

- [ ] Deployment logged
- [ ] Timestamp recorded
- [ ] Changes documented

**Time**: 1 minute

---

## Success Criteria (24-Hour Monitoring)

### Critical Metrics

**Monitor for next 24 hours**:

1. **Entity Extraction Success Rate**
   - [ ] Target: >95%
   - [ ] Current: ____%
   - [ ] Status: ⬜ PASS ⬜ FAIL

2. **Configuration Loading**
   - [ ] Target: 100% success on service restarts
   - [ ] Tested: ___ times
   - [ ] Status: ⬜ PASS ⬜ FAIL

3. **Guided JSON Compliance**
   - [ ] Target: 100% schema-compliant responses
   - [ ] Validation errors: ___
   - [ ] Status: ⬜ PASS ⬜ FAIL

4. **GPU Utilization**
   - [ ] Target: 60-80% during extraction
   - [ ] Average: ____%
   - [ ] Status: ⬜ PASS ⬜ FAIL

5. **Response Time**
   - [ ] Target: <2s per extraction
   - [ ] Average: ___s
   - [ ] Status: ⬜ PASS ⬜ FAIL

6. **Error Rate**
   - [ ] Target: <1% errors
   - [ ] Current: ____%
   - [ ] Status: ⬜ PASS ⬜ FAIL

---

## Rollback Procedures

### If Deployment Fails

**Quick Rollback (5 minutes)**:
```bash
# 1. Stop service
sudo systemctl stop luris-entity-extraction

# 2. Restore backup
cd /srv/luris/be/entity-extraction-service
cp .env.backup.20251015_020208 .env

# 3. Revert code changes
git checkout HEAD~1 -- src/core/config.py src/core/entity_models.py src/core/extraction_orchestrator.py

# 4. Clear cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# 5. Restart
sudo systemctl start luris-entity-extraction
```

- [ ] Rollback procedure understood
- [ ] Backup verified before deployment
- [ ] Team notified of rollback if needed

---

## Sign-Off

### Deployment Team

**Pre-Deployment Sign-Off**:
- [ ] DevOps Lead: _________________ Date: _________
- [ ] Backend Engineer: ____________ Date: _________
- [ ] QA Engineer: _________________ Date: _________

**Post-Deployment Sign-Off** (after 24 hours):
- [ ] DevOps Lead: _________________ Date: _________
- [ ] Backend Engineer: ____________ Date: _________
- [ ] QA Engineer: _________________ Date: _________

---

## Notes

**Deployment Notes**:
```
[Space for notes during deployment]







```

**Issues Encountered**:
```
[Space for documenting any issues]







```

**Action Items**:
```
[Space for follow-up tasks]







```

---

## Related Documents

- `DEPLOYMENT_READINESS_REPORT_v2.0.1.md` - Comprehensive deployment report
- `QUICK_REFERENCE_v2.0.1.md` - Quick reference guide
- `MIGRATION_GUIDE_v2.0.1.md` - Migration instructions
- `DEPLOYMENT_COMMANDS.sh` - Automated deployment script
- `VALIDATION_TEST_SUITE.sh` - Validation test suite

---

**Prepared By**: Task Coordinator Agent
**Version**: 2.0.1
**Last Updated**: 2025-10-15
