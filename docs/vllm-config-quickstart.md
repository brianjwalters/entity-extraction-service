# vLLM Configuration Quick Start Guide

**Last Updated:** 2025-10-14

---

## TL;DR

All vLLM configuration is now centralized in `.env` (Section 9). Use these patterns:

```python
# ✅ RECOMMENDED - Auto-loads from centralized config
from src.vllm.factory import get_default_client

client = await get_default_client()
```

```python
# ✅ RECOMMENDED - For entity extraction
from src.vllm.factory import get_client_for_entity_extraction

client = await get_client_for_entity_extraction()
```

```python
# ✅ RECOMMENDED - Explicit config loading
from src.vllm.models import VLLMConfig

config = VLLMConfig.from_settings()  # Loads from .env
# Use config...
```

---

## Quick Configuration Changes

### Change GPU Memory Allocation
**File:** `.env`
```bash
# Change from 0.85 to 0.90
VLLM_GPU_MEMORY_UTILIZATION=0.90
```

**Effect:** Immediate on next service restart. No code changes needed.

### Change Max Tokens
**File:** `.env`
```bash
# Increase from 4096 to 8000
VLLM_DEFAULT_MAX_TOKENS=8000
```

**Effect:** All new VLLMRequest.from_config() calls use new value.

### Change GPU ID
**File:** `.env`
```bash
# Switch from GPU 0 to GPU 1
VLLM_GPU_ID=1
```

**Effect:** vLLM loads on different GPU. Useful for multi-GPU setups.

### Change Random Seed
**File:** `.env`
```bash
# Change seed for different reproducible outputs
VLLM_SEED=12345
```

**Effect:** All generations use new seed for reproducibility.

---

## Configuration Priority

1. **Explicit parameters** (highest priority)
   ```python
   config = VLLMConfig(gpu_memory_utilization=0.95)
   ```

2. **Centralized config from .env** (recommended)
   ```python
   config = VLLMConfig.from_settings()
   ```

3. **Hardcoded defaults** (fallback for backward compatibility)
   ```python
   config = VLLMConfig()  # Uses defaults if no .env
   ```

---

## Common Patterns

### Pattern 1: Default Client (Simplest)
```python
from src.vllm.factory import get_default_client

# Everything from centralized config
client = await get_default_client()
response = await client.generate_chat_completion(request)
```

### Pattern 2: Request with Config Defaults
```python
from src.vllm.models import VLLMRequest

# Uses centralized temperature, seed, max_tokens
request = VLLMRequest.from_config(
    messages=[{"role": "user", "content": "Extract entities"}]
)

# Override specific parameters
request = VLLMRequest.from_config(
    messages=[{"role": "user", "content": "Extract entities"}],
    max_tokens=8000  # Override default
)
```

### Pattern 3: Custom Config
```python
from src.core.config import get_settings
from src.vllm.models import VLLMConfig
from src.vllm.factory import VLLMClientFactory

# Load settings
settings = get_settings()
config = VLLMConfig.from_settings(settings)

# Customize if needed
config.gpu_memory_utilization = 0.90

# Create client
client = await VLLMClientFactory.create_client(config=config)
```

---

## Environment Variables Reference

### Essential Variables (Most Common)

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.85` | GPU memory fraction (0.0-1.0) |
| `VLLM_SEED` | `42` | Random seed for reproducibility |
| `VLLM_DEFAULT_MAX_TOKENS` | `4096` | Max tokens per generation |
| `VLLM_DEFAULT_TEMPERATURE` | `0.0` | Temperature (0.0 = deterministic) |
| `VLLM_GPU_ID` | `0` | GPU device ID |

### Performance Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_ENABLE_PREFIX_CACHING` | `True` | Enable KV cache prefix caching |
| `VLLM_ENABLE_CHUNKED_PREFILL` | `True` | Enable chunked prefill |
| `VLLM_MAX_NUM_SEQS` | `256` | Max concurrent sequences |
| `VLLM_MAX_NUM_BATCHED_TOKENS` | `8192` | Max tokens in batch |

### Token Estimation Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_CHARS_PER_TOKEN` | `4.0` | Chars per token estimate |
| `VLLM_PREFILL_RATE` | `19000` | Prefill tokens/second |
| `VLLM_DECODE_RATE` | `150` | Decode tokens/second |

**Full list:** See `.env` Section 9 (30 total variables)

---

## Troubleshooting

### Issue: Config changes not taking effect
**Solution:** Restart the service to reload .env
```bash
sudo systemctl restart luris-entity-extraction
```

### Issue: Import errors
**Solution:** Ensure virtual environment is activated
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
```

### Issue: GPU memory errors
**Solution:** Reduce `VLLM_GPU_MEMORY_UTILIZATION` in .env
```bash
# Reduce from 0.85 to 0.80
VLLM_GPU_MEMORY_UTILIZATION=0.80
```

### Issue: Token overflow errors
**Solution:** Increase context window or reduce max_tokens
```bash
# Option 1: Increase context (if model supports)
VLLM_MAX_MODEL_LEN=262144  # 256K context

# Option 2: Reduce max completion tokens
VLLM_DEFAULT_MAX_TOKENS=2048
```

---

## Testing Configuration

### Test Config Loading
```python
from src.core.config import get_settings
from src.vllm.models import VLLMConfig

settings = get_settings()
config = VLLMConfig.from_settings(settings)

print(f"GPU Memory: {config.gpu_memory_utilization}")
print(f"Seed: {config.seed}")
print(f"Max Tokens: {config.max_completion_tokens}")
```

### Test Client Creation
```python
from src.vllm.factory import get_default_client

client = await get_default_client()
print(f"Client ready: {client.is_ready()}")
print(f"Stats: {client.get_stats()}")
```

---

## Best Practices

### ✅ DO

- Use `VLLMConfig.from_settings()` for centralized configuration
- Use `VLLMRequest.from_config()` for request-level defaults
- Modify `.env` for configuration changes (not code)
- Test configuration changes in dev/staging before production
- Document any custom configuration overrides

### ❌ DON'T

- Hardcode configuration values in code
- Modify config.py dataclass defaults directly
- Use different configurations across environments without documentation
- Change .env in production without testing
- Bypass centralized config unless necessary

---

## Migration from Old Code

### Old Pattern (Deprecated)
```python
# ❌ OLD - Hardcoded values
config = VLLMConfig(
    gpu_memory_utilization=0.85,
    seed=42,
    max_completion_tokens=4096
)
```

### New Pattern (Recommended)
```python
# ✅ NEW - Centralized config
config = VLLMConfig.from_settings()
```

**Note:** Old pattern still works (backward compatible) but doesn't benefit from centralized configuration.

---

## Support

**Documentation:**
- Full migration guide: `docs/vllm-config-migration.md`
- Config reference: `src/core/config.py` (lines 952-1176)
- Environment variables: `.env` (Section 9)

**Code Examples:**
- Factory patterns: `src/vllm/factory.py`
- Request creation: `src/vllm/models.py`
- Client usage: `src/vllm/client.py`

**Testing:**
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python -c "from src.vllm.models import VLLMConfig; config = VLLMConfig.from_settings(); print('✅ Config loaded')"
```

---

## Summary

**Single Command to Remember:**
```python
config = VLLMConfig.from_settings()  # Everything from .env
```

**Single File to Modify:**
```bash
.env  # Section 9: vLLM Configuration (30 variables)
```

**Result:**
- ✅ Centralized configuration
- ✅ Environment-specific tuning
- ✅ No code changes for config updates
- ✅ Type-validated with Pydantic
- ✅ Backward compatible
