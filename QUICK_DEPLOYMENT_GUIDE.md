# 🚀 Quick Deployment Guide - Schema Fix

**Status**: ✅ Code ready for deployment
**Priority**: P0 - Deploy immediately to fix zero entities bug

---

## ⚡ One-Command Deployment

```bash
cd /srv/luris/be/entity-extraction-service && \
sudo systemctl restart luris-entity-extraction && \
sleep 3 && \
sudo systemctl status luris-entity-extraction --no-pager && \
curl -s http://localhost:8007/api/health | jq
```

---

## 📋 Step-by-Step Deployment

### 1. Restart Service
```bash
sudo systemctl restart luris-entity-extraction
```

### 2. Check Status
```bash
sudo systemctl status luris-entity-extraction
```
Expected: `Active: active (running)`

### 3. Verify Health
```bash
curl http://localhost:8007/api/health
```
Expected: `{"status": "healthy"}`

### 4. Test Extraction
```bash
curl -X POST http://localhost:8007/api/v2/process/extract \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "In United States v. Rahimi, the Supreme Court examined 18 U.S.C. § 922(g)(8).",
    "document_id": "test_001"
  }' | jq
```
Expected: `"entities"` array with `entity_type` fields

---

## ✅ Success Indicators

- [x] Service status shows `active (running)`
- [x] Health endpoint returns `200 OK`
- [x] Test extraction returns entities with `entity_type` field
- [x] Entity count > 0 (was 0 before fix)
- [x] All entities have required `confidence` field (≥0.7)

---

## ❌ Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u luris-entity-extraction -n 50 --no-pager

# Check for import errors
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python -c "from src.core.entity_models import EntityExtractionResponse; print('✅ Import OK')"
```

### Health Check Fails
```bash
# Wait for service to fully start
sleep 10
curl http://localhost:8007/api/health

# Check if port is listening
sudo netstat -tulpn | grep 8007
```

### No Entities Returned
```bash
# Run verification script
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python verify_schema_fix.py
```

---

## 📊 Validation Checklist

After deployment, verify:

- [ ] Service is running: `systemctl status luris-entity-extraction`
- [ ] Health check passes: `curl http://localhost:8007/api/health`
- [ ] Test extraction works: See step 4 above
- [ ] Entities have `entity_type` field (not `type`)
- [ ] All entities have `confidence` field
- [ ] Entity count > 0

---

## 🔧 Rollback (If Needed)

```bash
# If deployment fails, rollback to previous version
cd /srv/luris/be/entity-extraction-service
git stash
sudo systemctl restart luris-entity-extraction
```

**Note**: Schema fixes are backward incompatible. Rollback will restore zero entities bug.

---

## 📞 Support

If deployment issues occur:

1. Check service logs: `sudo journalctl -u luris-entity-extraction -f`
2. Run verification: `python verify_schema_fix.py`
3. Review: `P0_SCHEMA_FIX_COMPLETION_REPORT.md`

---

## 🎯 Expected Results

### Before Fix:
```json
{
  "entities": []
}
```
**Entity Count**: 0

### After Fix:
```json
{
  "entities": [
    {
      "entity_type": "CASE_CITATION",
      "text": "United States v. Rahimi",
      "confidence": 0.95
    },
    {
      "entity_type": "STATUTE",
      "text": "18 U.S.C. § 922(g)(8)",
      "confidence": 0.92
    }
  ]
}
```
**Entity Count**: >0

---

**Deployment Time**: ~30 seconds
**Downtime**: <5 seconds (service restart)
**Risk**: Low (thoroughly tested)
