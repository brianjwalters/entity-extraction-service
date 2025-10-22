# vLLM Factory Error Handling Improvements

## Overview
This document describes improvements made to the vLLM factory's initialization error handling to better distinguish between different types of errors and provide clearer guidance for troubleshooting.

## Changes Made

### File Modified
- `/srv/luris/be/entity-extraction-service/src/vllm/factory.py`

### Key Improvements

#### 1. **Separate ImportError from Other Initialization Errors**

**Before:**
```python
except ImportError as e:
    logger.warning(f"vLLM direct API not available: {e}")
except Exception as e:
    logger.error(f"Failed to initialize direct API: {e}", exc_info=True)
```

**After:**
```python
except ImportError as e:
    logger.error(f"❌ vLLM library not installed: {e}")
    logger.error("Install with: source venv/bin/activate && pip install vllm==0.6.3")
    if enable_fallback:
        logger.warning("⚠️  Falling back to HTTPVLLMClient (guided JSON may not work)")
        logger.warning("⚠️  HTTP fallback uses OpenAI-compatible API, which may not support guided_json parameter")

except Exception as e:
    logger.error(f"❌ DirectVLLMClient initialization failed: {e}", exc_info=True)
    if enable_fallback:
        logger.warning("⚠️  Falling back to HTTPVLLMClient")
        logger.warning("⚠️  HTTP fallback may not support all Direct API features (e.g., guided JSON)")
```

**Benefits:**
- Clear distinction between vLLM not installed vs other initialization failures
- Installation instructions provided immediately when library is missing
- Contextual warnings about fallback limitations

#### 2. **Enhanced Logging for Initialization Steps**

**Before:**
```python
logger.info("Attempting to initialize Direct vLLM Python API...")
client = DirectVLLMClient(config=config)
success = await client.connect()

if success:
    logger.info("Using Direct vLLM Python API")
    return client
```

**After:**
```python
logger.info("Initializing DirectVLLMClient (vLLM Python library)...")
logger.info(f"Model: {config.model}, Max tokens: {config.max_model_len}, GPU memory: {config.gpu_memory_utilization}")

client = DirectVLLMClient(config=config)
success = await client.connect()

if success:
    logger.info("✅ DirectVLLMClient initialized successfully")
    logger.info("✅ Guided JSON support: AVAILABLE")
    return client
else:
    logger.warning("❌ DirectVLLMClient connection failed (connect() returned False)")
```

**Benefits:**
- Configuration details logged for debugging
- Success/failure clearly indicated with visual markers
- Explicit confirmation of guided JSON support availability

#### 3. **Improved Fallback Warnings**

**Before:**
```python
logger.info("Using HTTP vLLM API (fallback)")
```

**After:**
```python
logger.info("✅ HTTPVLLMClient initialized successfully")
logger.warning("⚠️  Guided JSON support: LIMITED (depends on vLLM server configuration)")
```

**Benefits:**
- Clear warning about guided JSON limitations in HTTP mode
- Users understand why certain features may not work
- Helps diagnose issues with structured output

#### 4. **Better Exception Handling in Convenience Methods**

All three client creation methods now have improved error handling:

- `create_client()` - Main factory with fallback
- `create_direct_client()` - Direct API only (no fallback)
- `create_http_client()` - HTTP API only (no fallback)

Each method now:
- Separates ImportError from other exceptions
- Provides installation instructions for ImportError
- Logs configuration details
- Warns about feature limitations
- Re-raises VLLMConnectionError without double-wrapping

## Error Scenarios & Messages

### Scenario 1: vLLM Library Not Installed (Direct API)

**Log Output:**
```
INFO: Initializing DirectVLLMClient (vLLM Python library)...
INFO: Model: qwen-instruct-160k, Max tokens: 131072, GPU memory: 0.85
ERROR: ❌ vLLM library not installed: No module named 'vllm'
ERROR: Install with: source venv/bin/activate && pip install vllm==0.6.3
WARNING: ⚠️  Falling back to HTTPVLLMClient (guided JSON may not work)
WARNING: ⚠️  HTTP fallback uses OpenAI-compatible API, which may not support guided_json parameter
INFO: Initializing HTTPVLLMClient (OpenAI-compatible API)...
INFO: Base URL: http://10.10.0.87:8080, Timeout: 1800s
INFO: ✅ HTTPVLLMClient initialized successfully
WARNING: ⚠️  Guided JSON support: LIMITED (depends on vLLM server configuration)
```

**User Action:**
- Install vLLM: `source venv/bin/activate && pip install vllm==0.6.3`
- Or accept HTTP fallback with limited guided JSON support

### Scenario 2: Direct API Initialization Failed (Other Error)

**Log Output:**
```
INFO: Initializing DirectVLLMClient (vLLM Python library)...
INFO: Model: qwen-instruct-160k, Max tokens: 131072, GPU memory: 0.85
ERROR: ❌ DirectVLLMClient initialization failed: CUDA out of memory
WARNING: ⚠️  Falling back to HTTPVLLMClient
WARNING: ⚠️  HTTP fallback may not support all Direct API features (e.g., guided JSON)
INFO: Initializing HTTPVLLMClient (OpenAI-compatible API)...
INFO: Base URL: http://10.10.0.87:8080, Timeout: 1800s
INFO: ✅ HTTPVLLMClient initialized successfully
WARNING: ⚠️  Guided JSON support: LIMITED (depends on vLLM server configuration)
```

**User Action:**
- Reduce `gpu_memory_utilization` in VLLMConfig
- Or use HTTP client to connect to external vLLM server

### Scenario 3: Successful Direct API Initialization

**Log Output:**
```
INFO: Initializing DirectVLLMClient (vLLM Python library)...
INFO: Model: qwen-instruct-160k, Max tokens: 131072, GPU memory: 0.85
INFO: ✅ DirectVLLMClient initialized successfully
INFO: ✅ Guided JSON support: AVAILABLE
```

**User Action:**
- None - system is working optimally

### Scenario 4: HTTP Client Connection Failed

**Log Output:**
```
INFO: Initializing HTTPVLLMClient (OpenAI-compatible API)...
INFO: Base URL: http://10.10.0.87:8080, Timeout: 1800s
ERROR: ❌ HTTPVLLMClient connection failed (connect() returned False)
ERROR: ❌ HTTPVLLMClient initialization failed: HTTP API connection failed
```

**User Action:**
- Check vLLM server is running at specified URL
- Verify network connectivity
- Check firewall rules

## Testing the Improvements

### Manual Testing

```bash
# Test 1: vLLM not installed scenario
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

# Temporarily rename vllm to simulate not installed
python -c "
import asyncio
from src.vllm.factory import VLLMClientFactory
from src.vllm.models import VLLMClientType, VLLMConfig

async def test():
    try:
        client = await VLLMClientFactory.create_client(
            preferred_type=VLLMClientType.DIRECT_API,
            enable_fallback=True
        )
        print(f'Client type: {type(client).__name__}')
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test())
"
```

### Expected Behavior

1. **ImportError**: Clear error message with installation instructions
2. **Fallback Warning**: Explicit warning about guided JSON limitations
3. **HTTP Success**: Falls back to HTTP client with appropriate warnings
4. **Feature Clarity**: User understands which features are available

## Benefits

### For Developers
- Faster debugging with clear error messages
- Configuration details logged for troubleshooting
- Easy to understand which client is being used

### For Operations
- Clear installation instructions when vLLM is missing
- Better understanding of fallback behavior
- Feature availability clearly communicated

### For Users
- Know when guided JSON is available vs limited
- Understand why certain features may not work
- Clear guidance on resolving issues

## Related Files

- `/srv/luris/be/entity-extraction-service/src/vllm/factory.py` - Main implementation
- `/srv/luris/be/entity-extraction-service/src/vllm/client.py` - Client implementations
- `/srv/luris/be/entity-extraction-service/src/vllm/models.py` - Configuration models
- `/srv/luris/be/entity-extraction-service/src/vllm/exceptions.py` - Custom exceptions

## Future Improvements

1. Add retry logic for transient initialization failures
2. Health check endpoint to verify client status
3. Metrics for tracking fallback frequency
4. Configuration validation before initialization
5. Automatic detection of vLLM server capabilities
