# Guided JSON Validation Tests - Important Notes

## Test Execution Constraints

### DirectVLLMClient vs HTTPVLLMClient

The guided JSON tests in `test_guided_json.py` are designed to validate that vLLM's guided JSON feature works correctly. However, there are important constraints to understand:

#### Production Environment Limitation

**In production, DirectVLLMClient CANNOT be instantiated when vLLM is already running as a service on the same GPU.**

Current GPU status shows:
```
GPU 0: 93.2% utilized (41.9GB / 45.0GB)
```

This means vLLM is already running as a service on GPU 0. When the tests try to create a new `DirectVLLMClient`, it attempts to load a second model instance on the same GPU, which fails due to:
1. Insufficient GPU memory
2. CUDA context conflicts
3. Model already loaded by the service

#### Test Modes

**Mode 1: Direct API Testing (Requires Dedicated GPU)**

To test DirectVLLMClient with guided JSON:
```bash
# 1. Stop vLLM service
sudo systemctl stop luris-vllm

# 2. Wait for GPU memory to clear
nvidia-smi  # Verify GPU 0 is free

# 3. Run tests
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
pytest tests/test_guided_json.py -v

# 4. Restart vLLM service
sudo systemctl start luris-vllm
```

**Mode 2: HTTP API Testing (Works with Running Service)**

The HTTP client connects to the already-running vLLM service:
```bash
# Guided JSON support depends on vLLM server configuration
# vLLM 0.6.3+ HTTP server MAY support guided_json parameter
```

## Guided JSON Implementation Details

### What is Guided JSON?

Guided JSON is a vLLM feature that ensures the LLM output matches a JSON schema **exactly**. Without it, LLMs often:
- Add extra text before/after JSON
- Produce malformed JSON
- Cause "Extra data: line X column Y" parsing errors

### How It Works

```python
from vllm.sampling_params import GuidedDecodingParams

# Create schema
schema = EntityExtractionResponse.model_json_schema()

# Create guided decoding parameters
guided_decoding = GuidedDecodingParams(
    backend="outlines",  # outlines backend is most stable
    json=json.dumps(schema)
)

# Add to sampling params
sampling_params = SamplingParams(
    temperature=0.0,
    guided_decoding=guided_decoding
)

# LLM output will now match schema exactly
```

### Backend Options

vLLM 0.6.3 supports multiple guided decoding backends:

1. **outlines** (RECOMMENDED)
   - Most stable for JSON schemas
   - Best schema compliance
   - Used in our implementation

2. **lm-format-enforcer**
   - Alternative backend
   - May have different performance characteristics

3. **xgrammar**
   - Newer backend
   - Experimental in vLLM 0.6.3

### Verification

To verify guided JSON is working:

1. **Check logs** for:
   ```
   ✅ Guided JSON decoding enabled - LLM output will match schema exactly
   ```

2. **JSON parsing** should succeed without "Extra data" errors:
   ```python
   response = await client.generate_chat_completion(request)
   parsed = json.loads(response.content)  # No errors
   validated = EntityExtractionResponse.model_validate(parsed)  # Valid
   ```

3. **Schema compliance**:
   - Response has required fields
   - Field types match schema
   - No extra fields (unless allowed)

## Test Coverage

The test suite validates:

1. **DirectVLLMClient initialization** (when GPU available)
2. **Entity extraction** with guided JSON schema
3. **Relationship extraction** with guided JSON schema
4. **No JSON parsing errors** (critical test)
5. **Complex nested schemas**

## Known Issues

### Issue 1: GPU Memory Conflicts

**Symptom**: `DirectVLLMClient initialization failed: Direct API initialization failed`

**Cause**: vLLM service already using GPU 0

**Solution**: Stop vLLM service before running tests, or use HTTP client

### Issue 2: Import Warnings

**Symptom**: Pydantic deprecation warnings

**Impact**: None - warnings only, tests still work

**Status**: Non-critical, will be addressed in future Pydantic V2 migration

### Issue 3: HTTP Client Guided JSON Support

**Symptom**: HTTP client may not support guided_json parameter

**Cause**: Depends on vLLM server version and configuration

**Solution**: Use DirectVLLMClient when testing guided JSON features

## Recommendations

### For Testing

1. **Use dedicated GPU** for DirectVLLMClient tests
2. **Stop vLLM service** before running guided JSON tests
3. **Monitor GPU memory** with `nvidia-smi`
4. **Restart service** after tests complete

### For Production

1. **Use HTTP client** to connect to running vLLM service
2. **Configure vLLM server** to support guided JSON
3. **Monitor service logs** for guided JSON confirmation
4. **Validate all responses** with Pydantic models

## Alternative: Mock Testing

For CI/CD pipelines without dedicated GPUs, consider:

```python
@pytest.fixture
def mock_vllm_client(monkeypatch):
    """Mock DirectVLLMClient for testing without GPU."""
    # Mock implementation here
    pass
```

This allows testing the guided JSON **logic** without requiring actual LLM inference.

## References

- vLLM Guided Decoding: https://docs.vllm.ai/en/latest/
- Outlines Library: https://github.com/outlines-dev/outlines
- Pydantic JSON Schema: https://docs.pydantic.dev/latest/concepts/json_schema/

## Status

- **Test File**: `/srv/luris/be/entity-extraction-service/tests/test_guided_json.py`
- **Implementation**: `/srv/luris/be/entity-extraction-service/src/vllm/client.py`
- **Schema Models**: `/srv/luris/be/entity-extraction-service/src/core/entity_models.py`
- **vLLM Version**: 0.6.3
- **Last Updated**: 2025-10-14
