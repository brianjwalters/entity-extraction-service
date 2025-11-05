# vLLM Infrastructure Issue - Resolution Guide

**Date**: November 5, 2025
**Status**: 🔴 Critical - Blocking AI Extraction Mode
**Affected Service**: vLLM Instruct (Port 8080)
**Impact**: Phase 1 Family Law patterns deployed but AI extraction unavailable

---

## 🔴 Issue Summary

**Problem**: Qwen/Qwen3-VL-8B-Instruct model has xFormers attention operator incompatibility

**Error Message**:
```
NotImplementedError: No operator found for `memory_efficient_attention_forward` with inputs:
     query       : shape=(1, 1, 8, 4, 128) (torch.bfloat16)
     key         : shape=(1, 123344, 8, 4, 128) (torch.bfloat16)
     value       : shape=(1, 123344, 8, 4, 128) (torch.bfloat16)
     attn_bias   : <class 'xformers.ops.fmha.attn_bias.PagedBlockDiagonalCausalWithOffsetPaddedKeysMask'>
     p           : 0.0
```

**Root Cause**: The Qwen3-VL vision-language model requires a specific xFormers attention operator that is not available in the current installation.

**Impact**:
- ❌ AI extraction mode (`extraction_mode: "ai"`) blocked
- ❌ All vLLM services currently inactive (ports 8080, 8081, 8082)
- ✅ Phase 1 patterns deployed and verified (regex mode works)
- ✅ Entity Extraction Service operational (pattern API functional)

---

## 📊 Current System Status

### vLLM Services Status (All Inactive)
```
Port 8080 - Instruct (Multi-Purpose): ❌ INACTIVE (xFormers error)
Port 8081 - Embeddings:                ❌ INACTIVE
Port 8082 - Thinking + Context:        ❌ INACTIVE
```

### Entity Extraction Service Status
```
Service: ✅ ACTIVE (Port 8007)
Mode: Pattern API Mode (regex extraction only)
Patterns Loaded: 818 total (including 15 new Phase 1 family law patterns)
AI Extraction: ❌ BLOCKED (requires vLLM)
```

### Last Known Service Activity
```
vLLM Instruct Service:
- Started: Nov 05 13:21:43 MST
- Model Loading: Successful (11.7 GiB in 8.66 seconds)
- KV Cache Init: Successful (16.94 GiB, 123,344 tokens)
- API Server: Started successfully
- First Request: FAILED with xFormers attention operator error
- Status: Crashed and deactivated

Timeline:
13:21:43 - Service started
13:22:56 - API server ready
13:41:56 - xFormers error on first extraction request
13:42:01 - Service shutdown
```

---

## 🛠️ Resolution Options

### Option 1: Update vLLM to Latest Version (RECOMMENDED)

**Pros**:
- Official support for Qwen3-VL models in newer vLLM versions
- Includes updated xFormers with required attention operators
- Long-term solution with ongoing support

**Steps**:
```bash
# 1. Check current vLLM version
vllm --version

# 2. Update vLLM to latest stable release
pip install --upgrade vllm

# Or specific version with Qwen3-VL support:
pip install vllm>=0.6.0

# 3. Verify xFormers compatibility
python -c "import xformers; print(xformers.__version__)"

# 4. Restart all vLLM services
sudo systemctl daemon-reload
sudo systemctl restart luris-vllm-instruct
sudo systemctl restart luris-vllm-embeddings
sudo systemctl restart luris-vllm-thinking

# 5. Verify services are running
curl http://localhost:8080/v1/models
curl http://localhost:8081/v1/models
curl http://localhost:8082/v1/models

# 6. Restart Entity Extraction Service to reconnect
sudo systemctl restart luris-entity-extraction
```

**Expected Result**: All services operational with Qwen3-VL support

---

### Option 2: Switch to Compatible Model (ALTERNATIVE)

If vLLM update doesn't resolve the issue, switch to a proven compatible model.

**Compatible Models** (tested with current vLLM/xFormers):
1. **Mistral-Nemo-12B-Instruct-128K** (previously used, known working)
2. **Meta-Llama-3-8B-Instruct**
3. **Qwen2.5-7B-Instruct** (non-VL version)

**Steps to Switch Model**:
```bash
# 1. Edit vLLM Instruct systemd service
sudo nano /etc/systemd/system/luris-vllm-instruct.service

# 2. Change ExecStart line from:
ExecStart=/usr/local/bin/vllm serve Qwen/Qwen3-VL-8B-Instruct \

# To (example - Mistral-Nemo):
ExecStart=/usr/local/bin/vllm serve mistralai/Mistral-Nemo-Instruct-2407 \

# 3. Update Entity Extraction Service .env file
sudo nano /srv/luris/be/entity-extraction-service/.env

# Update these variables:
VLLM_INSTRUCT_MODEL=mistralai/Mistral-Nemo-Instruct-2407
AI_EXTRACTION_MODEL_NAME=mistralai/Mistral-Nemo-Instruct-2407
VLLM_MODEL=mistralai/Mistral-Nemo-Instruct-2407

# 4. Update Python source code defaults
cd /srv/luris/be/entity-extraction-service
# Edit src/core/config.py line 1018
# Edit src/vllm_client/models.py lines 38-44
# Edit src/api/main.py line 110

# 5. Reload and restart services
sudo systemctl daemon-reload
sudo systemctl restart luris-vllm-instruct
sudo systemctl restart luris-entity-extraction

# 6. Verify
curl http://localhost:8080/v1/models | jq '.data[0].id'
# Should show: "mistralai/Mistral-Nemo-Instruct-2407"
```

**Pros**:
- Immediate resolution
- Proven compatibility
- No vLLM version changes required

**Cons**:
- Loses vision-language capabilities of Qwen3-VL
- May need different prompts/parameters
- Performance characteristics differ

---

### Option 3: Rebuild vLLM from Source (ADVANCED)

For maximum control over xFormers integration.

**Steps**:
```bash
# 1. Clone vLLM repository
cd /opt
git clone https://github.com/vllm-project/vllm.git
cd vllm

# 2. Checkout latest stable release
git checkout v0.6.2  # Or latest version

# 3. Install with xFormers support
pip install -e . --extra-index-url https://download.pytorch.org/whl/cu121

# 4. Verify xFormers operators
python -c "from xformers.ops.fmha import memory_efficient_attention; print('OK')"

# 5. Follow Option 1 restart steps
```

**Pros**:
- Full control over dependencies
- Can apply custom patches if needed
- Bleeding-edge features

**Cons**:
- Complex build process
- Requires deep technical knowledge
- Time-consuming
- May introduce instability

---

## 🧪 Testing After Resolution

### 1. Verify vLLM Services
```bash
# Check all services are running
sudo systemctl status luris-vllm-instruct
sudo systemctl status luris-vllm-embeddings
sudo systemctl status luris-vllm-thinking

# Test model endpoints
curl http://localhost:8080/v1/models | jq
curl http://localhost:8081/v1/models | jq
curl http://localhost:8082/v1/models | jq

# Test simple completion
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3-vl-instruct-384k", "prompt": "Test", "max_tokens": 10}'
```

### 2. Verify Entity Extraction Service
```bash
# Check service logs for successful vLLM connection
sudo journalctl -u luris-entity-extraction --since "1 minute ago" | grep -i "vllm"

# Should see:
# "✅ HTTPVLLMClient connection successful"
# "All extraction capabilities operational"
```

### 3. Test AI Extraction Mode
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

python3 -c "
import asyncio
import httpx
import json

async def test():
    payload = {
        'document_text': 'California is the child home state under the UCCJEA. A petition for dissolution of marriage was filed.',
        'extraction_mode': 'ai',
        'entity_type_filter': ['HOME_STATE', 'DISSOLUTION_PETITION']
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            'http://localhost:8007/api/v2/process/extract',
            json=payload
        )
        print(f'Status: {response.status_code}')
        result = response.json()

        if response.status_code == 200:
            entities = result.get('entities', [])
            print(f'✅ SUCCESS: Extracted {len(entities)} entities')
            for entity in entities:
                print(f'  - {entity.get(\"entity_type\")}: \"{entity.get(\"text\")}\"')
        else:
            print(f'❌ FAILED: {result}')

asyncio.run(test())
"
```

**Expected Output**:
```
Status: 200
✅ SUCCESS: Extracted 2 entities
  - HOME_STATE: "California is the child home state"
  - DISSOLUTION_PETITION: "petition for dissolution of marriage"
```

### 4. Run Phase 1 Test Suite
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Run all Phase 1 tests
pytest tests/e2e/test_family_law_tier1.py -v -m tier1

# Expected:
# - 20 tests total
# - 15 unit tests (single entity extraction)
# - 3 integration tests (multi-entity)
# - 1 E2E test (full document)
# - 1 performance test (<15ms target)
```

---

## 📋 Post-Resolution Checklist

- [ ] **vLLM Instruct service running** on port 8080
- [ ] **vLLM Embeddings service running** on port 8081
- [ ] **vLLM Thinking service running** on port 8082
- [ ] **Entity Extraction Service** reconnected to vLLM
- [ ] **AI extraction mode** tested and working
- [ ] **Phase 1 test suite** passes (20/20 tests)
- [ ] **Performance benchmarks** meet targets (<15ms)
- [ ] **Documentation updated** with actual model used
- [ ] **Git commit** created for Phase 1 deployment

---

## 🔍 Diagnostic Commands

### Check vLLM Installation
```bash
# Version check
vllm --version
pip show vllm

# xFormers check
python -c "import xformers; print(f'xFormers: {xformers.__version__}')"

# CUDA check
nvidia-smi
nvcc --version
```

### Check GPU Availability
```bash
# All GPUs
nvidia-smi

# Specific GPU clusters
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv --id=0,1,2,3
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv --id=4,5
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv --id=6,7

# Check for GPU processes
nvidia-smi pids
```

### Check Service Logs
```bash
# Recent errors
sudo journalctl -u luris-vllm-instruct --since "10 minutes ago" | grep -i "error"

# Full startup sequence
sudo journalctl -u luris-vllm-instruct --since "10 minutes ago" -n 100

# Entity Extraction Service logs
sudo journalctl -u luris-entity-extraction --since "5 minutes ago" | grep -i "vllm"
```

---

## 📚 Related Documentation

- **vLLM Operations Guide**: `/srv/luris/be/VLLM_OPERATIONS.md`
- **Phase 1 Deployment Summary**: `/srv/luris/be/entity-extraction-service/docs/PHASE1_DEPLOYMENT_SUMMARY.md`
- **Entity Extraction API**: `/srv/luris/be/entity-extraction-service/api.md`
- **Test Execution Guide**: `/srv/luris/be/tests/reports/TIER1_TEST_EXECUTION_SUMMARY.md`

---

## 🆘 Escalation

If none of the resolution options work, escalate to:

1. **vLLM GitHub Issues**: https://github.com/vllm-project/vllm/issues
   - Search for "Qwen3-VL xFormers attention"
   - Include error trace and vLLM version

2. **xFormers GitHub Issues**: https://github.com/facebookresearch/xformers/issues
   - Search for "memory_efficient_attention_forward NotImplementedError"
   - Include PyTorch and CUDA versions

3. **Anthropic Support** (if using Claude infrastructure)
   - Provide this document
   - Include all diagnostic command outputs

---

**Issue Created**: November 5, 2025
**Last Updated**: November 5, 2025
**Status**: Awaiting Resolution
**Priority**: High (Blocks AI Extraction)
**Workaround**: Use regex extraction mode (fully functional)
