# Temperature Configuration Strategy

## Overview
The Entity Extraction Service uses **domain-specific temperature overrides** to balance reproducibility with flexibility.

## Temperature Settings

### Entity Extraction: 0.0 (Deterministic)
- **Variable**: `EXTRACTION_ENTITY_TEMPERATURE=0.0`
- **Usage**: Entity and relationship extraction from legal documents
- **Rationale**: Legal compliance requires reproducible, auditable results
- **Expected Reproducibility**: ~95-98% identical results across runs
- **Code Location**: `src/core/extraction_orchestrator.py` lines 600, 1028

### General Operations: 0.3 (Moderate Diversity)
- **Variable**: `VLLM_DEFAULT_TEMPERATURE=0.3`
- **Usage**: Non-extraction operations (summarization, classification, etc.)
- **Rationale**: Balance between consistency and output diversity

## Configuration Architecture

### Environment Variables (.env)
```bash
# Default for all vLLM operations (unless overridden)
VLLM_DEFAULT_TEMPERATURE=0.3

# Entity extraction overrides (legal compliance requirement)
EXTRACTION_ENTITY_TEMPERATURE=0.0
EXTRACTION_RELATIONSHIP_TEMPERATURE=0.0
```

### Pydantic Configuration (config.py)
```python
class ExtractionSettings(BaseModel):
    entity_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    relationship_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
```

### Code Usage (extraction_orchestrator.py)
```python
from src.core.config import get_settings
settings = get_settings()

# Entity extraction uses 0.0 for reproducibility
temperature=settings.extraction.entity_temperature

# General operations use 0.3 (from VLLMConfig)
temperature=settings.vllm.default_temperature
```

## Testing Reproducibility

Run the same extraction 3 times:
```bash
cd /srv/luris/be/entity-extraction-service
source venv/bin/activate

for i in {1..3}; do
  echo "=== Run $i ==="
  python test_rahimi_simple.py 2>&1 | grep -E "(Entities:|Relationships:)"
done
```

Expected: Entity counts should be >95% identical across runs.

## Rationale

### Why 0.0 for Entity Extraction?
1. **Legal Compliance**: Courts require reproducible, auditable results
2. **Consistency**: Same document → same entities (deterministic)
3. **Quality**: Seed=42 + temperature=0.0 = ~95-98% reproducibility

### Why 0.3 for General Operations?
1. **Diversity**: Summarization benefits from variety
2. **Creativity**: Higher temperature for text generation
3. **Balance**: Not too random (0.7+), not too rigid (0.0)

## Version History
- **v2.0.1**: Split temperature configuration (2025-10-15)
- **v2.0.0**: Unified temperature=0.3 (deprecated)
