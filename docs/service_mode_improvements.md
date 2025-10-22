# Service Mode Messaging Improvements

## Overview

Consolidated confusing degraded mode warnings into clear, actionable service mode banners that communicate service capabilities at startup.

## Changes Implemented

### 1. Service Mode Enumeration (`main.py`)

Added `ServiceMode` enum to clearly define three operational states:

```python
class ServiceMode(str, Enum):
    """Service operational mode indicating available capabilities."""
    FULL = "full"          # Wave System + Multipass + Patterns
    DEGRADED = "degraded"  # Patterns only (no vLLM)
    MULTIPASS = "multipass" # Multipass + Patterns (no Wave System)
```

### 2. Service Mode Detection Function (`main.py`)

```python
def get_service_mode(vllm_available: bool,
                     ai_enhancer_available: bool,
                     multipass_available: bool) -> ServiceMode:
    """
    Determine current service operational mode based on component availability.

    - FULL mode: All AI features operational (vLLM + AIEnhancer + MultiPass)
    - DEGRADED mode: No vLLM connection, pattern extraction only
    - MULTIPASS mode: vLLM available but Wave System failed, multipass only
    """
```

### 3. Startup Banner Messages (`main.py`, lines 285-310)

Replaced multiple scattered warnings with single comprehensive banner:

#### FULL Mode (All Systems Operational)
```
================================================================================
✅ SERVICE MODE: FULL
   Available features:
   • Wave System (AIEnhancer) - AI-powered entity extraction
   • Multipass Extraction - 7-stage comprehensive extraction
   • Pattern API - Legacy pattern-based extraction
   All extraction capabilities operational
================================================================================
```

#### DEGRADED Mode (vLLM Unavailable)
```
================================================================================
⚠️ SERVICE MODE: DEGRADED
   vLLM service not available - AI extraction disabled
   Available features:
   • Pattern API - Pattern-based extraction only
   Unavailable features:
   • Wave System - Requires vLLM connection
   • Multipass Extraction - Requires vLLM connection
   Action required: Ensure vLLM service is running on port 8080
================================================================================
```

#### MULTIPASS Mode (Wave System Failed)
```
================================================================================
⚠️ SERVICE MODE: MULTIPASS ONLY
   Wave System unavailable - limited AI extraction
   Available features:
   • Multipass Extraction - 7-stage extraction
   • Pattern API - Pattern-based extraction
   Unavailable features:
   • Wave System - Initialization failed
================================================================================
```

### 4. Enhanced Health Endpoint (`health.py`)

Added new fields to `DetailedHealthResponse`:

```python
class DetailedHealthResponse(HealthResponse):
    """Detailed health check response with service mode information."""
    service_mode: str = Field(default="unknown",
                              description="Current service operational mode")
    wave_system_available: bool = Field(default=False,
                                        description="Wave System availability")
    multipass_available: bool = Field(default=False,
                                     description="Multipass extraction availability")
    capabilities: list = Field(default_factory=list,
                              description="List of functional capabilities")
```

#### Example Health Response

```json
{
  "status": "degraded",
  "service_name": "entity-extraction-service",
  "service_version": "2.0.0",
  "service_mode": "degraded",
  "wave_system_available": false,
  "multipass_available": false,
  "capabilities": [
    "pattern_extraction"
  ],
  "checks": {
    "entity_extraction": {
      "status": "unhealthy",
      "message": "Required extraction components not initialized"
    }
  },
  "dependencies": {
    "vllm_service": "unavailable",
    "ai_processing": {
      "vllm_available": false,
      "vllm_status": "not_ready"
    }
  }
}
```

## Benefits

### 1. Clear Communication
- **Before**: Multiple scattered warnings (`⚠️ AIEnhancer not initialized`, `⚠️ MultiPassExtractor not initialized`)
- **After**: Single banner explaining service mode and exact capabilities

### 2. Actionable Guidance
- **Before**: Generic warnings with no guidance
- **After**: Clear action items ("Ensure vLLM service is running on port 8080")

### 3. Programmatic Access
- **Before**: Manual log parsing to determine service state
- **After**: `/health/detailed` endpoint provides structured service mode information

### 4. User Experience
- **Before**: Confusion about what features are available
- **After**: Clear list of available and unavailable features

## Testing

### Test Startup Messages

```bash
# Test FULL mode (vLLM running)
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate
python run.py
# Should see: ✅ SERVICE MODE: FULL

# Test DEGRADED mode (vLLM stopped)
sudo systemctl stop luris-vllm
python run.py
# Should see: ⚠️ SERVICE MODE: DEGRADED
```

### Test Health Endpoint

```bash
# Test detailed health endpoint
curl http://localhost:8007/api/v1/health/detailed | jq
# Should include: service_mode, wave_system_available, multipass_available, capabilities
```

## Removed Warnings

Eliminated redundant warnings from startup sequence:

1. ~~`⚠️ AIEnhancer not initialized - vLLM client unavailable`~~ (line 173)
2. ~~`⚠️ MultiPassExtractor not initialized - vLLM client unavailable`~~ (line 199)

These are now consolidated into the service mode banner.

## Files Modified

1. **`/srv/luris/be/entity-extraction-service/src/api/main.py`**
   - Added `ServiceMode` enum (lines 42-46)
   - Added `get_service_mode()` function (lines 49-66)
   - Added service mode detection and banner (lines 277-313)
   - Removed redundant warnings (lines 173, 199)

2. **`/srv/luris/be/entity-extraction-service/src/api/routes/health.py`**
   - Enhanced `DetailedHealthResponse` model (lines 54-57)
   - Updated `detailed_health()` endpoint (lines 151-189)

## Backward Compatibility

All changes are backward compatible:
- Existing health endpoints continue to work
- New fields are optional and default to sensible values
- Service continues to operate in degraded mode when vLLM unavailable

## Future Enhancements

Consider adding:
1. Automatic retry logic for vLLM connection failures
2. Service mode transition logging
3. Prometheus metrics for service mode state
4. Alert integration for prolonged degraded mode operation
