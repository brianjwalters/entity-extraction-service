# Entity Extraction Schema & Prompt Analysis for vLLM Guided JSON

**Analysis Date**: 2025-10-15
**Problem**: DirectVLLMClient with IBM Granite 8B returns 0 entities with guided JSON feature
**Context**: vLLM returns valid JSON but without expected 'entities' key in response

---

## Executive Summary

After comprehensive analysis of the entity extraction system, I've identified **5 critical issues** preventing successful entity extraction with vLLM guided JSON:

1. **Schema Field Name Mismatch**: Pydantic model uses `type` but prompts expect `entity_type`
2. **Missing Required Field in Schema**: `entities` key not marked as required in JSON schema
3. **Prompt-Schema Disconnect**: Wave prompts define complex 92-entity schemas that don't match simple Pydantic model
4. **Temperature Too Low (0.3)**: Model may not generate diverse enough output
5. **Guided JSON Currently Disabled**: Line 1031 shows `guided_json` is commented out for testing

---

## Issue #1: Critical Schema Field Name Mismatch 🚨

### Problem
**Pydantic Model** (entity_models.py:15-18) defines:
```python
class ExtractedEntity(BaseModel):
    type: str = Field(..., description="Entity type (e.g., PERSON, CASE_CITATION, STATUTE, etc.)")
    text: str = Field(..., description="The extracted entity text...")
```

**Wave Prompts** (wave1.md:390-425) expect:
```json
{
  "entities": [
    {
      "entity_type": "CASE_CITATION",  // ← Using entity_type, not type
      "text": "...",
      "start_pos": 0,
      "end_pos": 50
    }
  ]
}
```

**Impact**:
- LLM receives schema requesting `type` field
- LLM sees prompts requesting `entity_type` field
- Confusion leads to empty/malformed responses

### Solution
**Option A** (Recommended): Update Pydantic model to match prompts:
```python
class ExtractedEntity(BaseModel):
    entity_type: str = Field(
        ...,
        description="Entity type (e.g., CASE_CITATION, STATUTE_CITATION, PARTY, etc.)",
        alias="type"  # Allow 'type' for backward compatibility
    )
    text: str = Field(...)
```

**Option B**: Update all wave prompts to use `type` instead of `entity_type` (not recommended - massive refactor)

---

## Issue #2: Schema Missing Required 'entities' Key

### Problem
Generated JSON schema from `EntityExtractionResponse.model_json_schema()`:
```json
{
  "properties": {
    "entities": {
      "description": "List of all extracted entities from the document",
      "items": {"$ref": "#/$defs/ExtractedEntity"},
      "type": "array"
    }
  },
  "title": "EntityExtractionResponse",
  "type": "object"
  // ⚠️ NO "required": ["entities"] field!
}
```

**Current Pydantic Model** (entity_models.py:43-49):
```python
class EntityExtractionResponse(BaseModel):
    entities: List[ExtractedEntity] = Field(
        default_factory=list,  # ← Makes field optional with default []
        description="List of all extracted entities from the document"
    )
```

**Impact**:
- vLLM guided JSON allows returning `{}` (empty object)
- Model can skip `entities` key entirely since it has default value
- Result: Valid JSON but no entities extracted

### Solution
Make `entities` required by removing default:
```python
class EntityExtractionResponse(BaseModel):
    entities: List[ExtractedEntity] = Field(
        ...,  # ← Required, no default
        description="List of all extracted entities from the document"
    )

    class Config:
        # Add schema customization to enforce required
        json_schema_extra = {
            "required": ["entities"],
            "example": {...}
        }
```

---

## Issue #3: Prompt-Schema Complexity Mismatch

### Problem
**Wave 1 Prompt** defines **92 entity types**:
- 25 Party & Actor types (PARTY, PLAINTIFF, DEFENDANT, ...)
- 14 Court & Judicial types (COURT, JUDGE, FEDERAL_COURTS, ...)
- 12 Core Citation types (CASE_CITATION, USC_CITATIONS, ...)
- 17 Advanced Citation types (PARALLEL_CITATIONS, TREATISE_CITATION, ...)
- 14 Temporal types (DATE, FILING_DATE, DEADLINE, ...)
- 8 Document Structure types (DEFINED_TERM, SECTION_MARKER, ...)

**But ExtractedEntity model** is extremely simple:
```python
class ExtractedEntity(BaseModel):
    type: str  # ← Any string accepted, no validation!
    text: str
    start_pos: Optional[int]
    end_pos: Optional[int]
    confidence: Optional[float]
    metadata: Optional[Dict[str, Any]]
```

**Impact**:
- Model doesn't know about 92 entity types
- No validation that `type` is valid entity type
- Schema too generic for LLM to understand legal domain
- Prompts say "extract CASE_CITATION" but schema says "any string"

### Solution
Create legal-domain-aware schema with entity type validation:

```python
from enum import Enum
from typing import Literal

# Option A: Use Enum for strong typing
class EntityType(str, Enum):
    # Party & Actor (25 types)
    PARTY = "PARTY"
    PLAINTIFF = "PLAINTIFF"
    DEFENDANT = "DEFENDANT"
    APPELLANT = "APPELLANT"
    # ... all 92 types

class ExtractedEntity(BaseModel):
    entity_type: EntityType = Field(
        ...,
        description="Legal entity type from predefined taxonomy"
    )
    text: str = Field(...)

# Option B: Use Literal for wave-specific typing
EntityTypeWave1 = Literal[
    "PARTY", "PLAINTIFF", "DEFENDANT", "APPELLANT", "APPELLEE",
    "CASE_CITATION", "USC_CITATION", "CFR_CITATION",
    "COURT", "JUDGE", "FEDERAL_COURTS",
    "DATE", "FILING_DATE", "DEADLINE",
    # ... all 92 Wave 1 types
]

class ExtractedEntityWave1(BaseModel):
    entity_type: EntityTypeWave1 = Field(...)
    text: str = Field(...)
```

**Benefits**:
- JSON schema explicitly lists valid entity types
- vLLM guided JSON sees legal entity taxonomy
- Model validation ensures only valid types extracted
- Better alignment between prompts and schema

---

## Issue #4: Temperature Configuration

### Problem
**Current Setting** (extraction_orchestrator.py:1028):
```python
request = VLLMRequest(
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096,
    temperature=0.3,  # ← May be too low for entity diversity
    seed=42,
    stream=False,
    # extra_body={"guided_json": json_schema}  # DISABLED
)
```

**Analysis**:
- Temperature 0.3 is moderate (was 0.0, then 0.1, now 0.3)
- Legal entity extraction needs deterministic but diverse output
- IBM Granite 8B may need higher temperature for entity variety
- Wave 1 extracts 92 entity types - needs diversity

### Recommendation
```python
# For Wave 1 (92 types - needs diversity)
temperature=0.4  # Higher for entity type diversity

# For Wave 2-3 (fewer types)
temperature=0.3  # Current setting OK

# For Wave 4 (relationships - needs creativity)
temperature=0.5  # Higher for relationship inference
```

**Testing Strategy**:
1. Test with temperature 0.3 (current) - measure entity diversity
2. Test with temperature 0.4 - measure if more entity types extracted
3. Test with temperature 0.5 - check if too creative/hallucinations
4. Optimal: 0.3-0.4 for legal extraction

---

## Issue #5: Guided JSON Currently Disabled

### Problem
**Line 1024-1031** in extraction_orchestrator.py:
```python
# Get JSON schema from Pydantic model
json_schema = EntityExtractionResponse.model_json_schema()

logger.debug(f"Using guided JSON with schema model: EntityExtractionResponse")

# Create VLLMRequest WITHOUT guided_json to test raw output
request = VLLMRequest(
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096,
    temperature=0.3,
    seed=42,
    stream=False,
    # extra_body={"guided_json": json_schema}  # DISABLED to test raw output
)

logger.info(f"Calling vLLM WITHOUT guided JSON to test raw model output")
```

**Impact**:
- Guided JSON is disabled for raw output testing
- Model generates free-form JSON without schema constraint
- This is intentional for debugging but blocks structured extraction

### Solution
Re-enable guided JSON after fixing schema issues:
```python
# After fixing Issues #1-#3, re-enable:
request = VLLMRequest(
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096,
    temperature=0.3,
    seed=42,
    stream=False,
    extra_body={"guided_json": json_schema}  # ✅ Re-enabled
)

logger.info(f"Calling vLLM with guided JSON (schema: EntityExtractionResponse)")
```

---

## Recommended Schema Improvements

### Enhanced ExtractedEntity Model

```python
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator

# Define Wave 1 Entity Types (92 types)
Wave1EntityTypes = Literal[
    # Party & Actor (25 types)
    "PARTY", "PLAINTIFF", "DEFENDANT", "APPELLANT", "APPELLEE",
    "PETITIONER", "RESPONDENT", "AMICUS_CURIAE", "INTERVENOR",
    "PRO_SE_PARTY", "CLASS_ACTION", "INDIVIDUAL_PARTY", "CORPORATION",
    "GOVERNMENT_ENTITY", "FEDERAL_AGENCY", "CONTRACT_PARTY", "ESTATE",
    "FIDUCIARY", "CASE_PARTIES", "PARTY_GROUP", "ATTORNEY",
    "GOVERNMENT_LEGAL_OFFICE", "GOVERNMENT_OFFICIAL",
    "INTERNATIONAL_LAW_FIRM", "PARTIES_CLAUSE",

    # Court & Judicial (14 types)
    "COURT", "FEDERAL_COURTS", "STATE_COURTS", "SPECIALIZED_COURTS",
    "CIRCUITS", "DISTRICT", "JUDGE", "JUDICIAL_PANEL",
    "SPECIALIZED_JURISDICTION", "GENERIC_COURT_REFERENCES",
    "ENHANCED_COURT_PATTERNS", "SPECIALIZED_COURT_CITATIONS",
    "COURT_COSTS", "COURT_RULE_CITATION",

    # Citations - Core (12 types)
    "CASE_CITATION", "STATUTE_CITATION", "USC_CITATIONS", "USC_TITLES",
    "CFR_CITATIONS", "CFR_TITLES", "STATE_STATUTES", "CONSTITUTIONAL",
    "CONSTITUTIONAL_CITATION", "CONSTITUTIONAL_AMENDMENT",
    "REGULATION_CITATION", "ADMINISTRATIVE_CITATION",

    # Citations - Advanced (17 types)
    "PARALLEL_CITATIONS", "PINPOINT_CITATIONS", "SHORT_FORMS",
    "ELECTRONIC_CITATION", "ELECTRONIC_CITATIONS", "LAW_REVIEW_CITATION",
    "TREATISE_CITATION", "RESTATEMENT_CITATION", "UNIFORM_LAW_CITATION",
    "PATENT_CITATION", "SEC_CITATION", "TREATY_CITATION",
    "INTERNATIONAL_CITATION", "INTERNATIONAL_CITATIONS",
    "HISTORICAL_CITATIONS", "ENHANCED_CASE_CITATIONS", "FEDERAL_REGISTER",

    # Temporal (14 types)
    "DATE", "FILING_DATE", "DEADLINE", "DECISION_DATE", "OPINION_DATE",
    "EFFECTIVE_DATE", "EXECUTION_DATE", "TERM_DATE", "DATE_RANGE",
    "RELATIVE_DATE", "FISCAL_YEAR", "QUARTER", "LIMITATIONS_PERIOD",
    "MONETARY_RANGE",

    # Document Structure (8 types)
    "ENHANCED_PARTY_PATTERNS", "DEFINED_TERM", "DEFINED_TERM_REFERENCE",
    "SECTION_MARKER", "SECTION_REFERENCE", "SECTION_HEADER",
    "SUBSECTION_MARKER", "SECTION_SYMBOLS", "LATIN_TERM", "FEDERAL_RULES"
]

class ExtractedEntity(BaseModel):
    """Enhanced entity model aligned with Wave 1 prompts."""

    entity_type: Wave1EntityTypes = Field(
        ...,
        description="Legal entity type from Wave 1 taxonomy (92 types)",
        alias="type"  # Allow 'type' for backward compatibility
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=500,  # Prevent extracting massive text blocks
        description="The extracted entity text as it appears in the document"
    )
    start_pos: Optional[int] = Field(
        None,
        ge=0,
        description="Character position where entity starts in document"
    )
    end_pos: Optional[int] = Field(
        None,
        ge=0,
        description="Character position where entity ends in document"
    )
    confidence: float = Field(
        ...,  # Make required instead of optional
        ge=0.7,  # Wave 1 minimum threshold
        le=1.0,
        description="Confidence score for this entity (0.7-1.0 for Wave 1)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the entity"
    )

    @validator('end_pos')
    def validate_position_order(cls, v, values):
        """Ensure end_pos > start_pos."""
        if v is not None and 'start_pos' in values and values['start_pos'] is not None:
            if v <= values['start_pos']:
                raise ValueError('end_pos must be greater than start_pos')
        return v

    @validator('text')
    def validate_text_length(cls, v):
        """Prevent extracting massive text blocks (Issue #5 from prompts)."""
        if len(v) > 500:
            raise ValueError('Entity text exceeds 500 character limit')
        return v

class EntityExtractionResponse(BaseModel):
    """Complete response from Wave 1 entity extraction."""

    entities: List[ExtractedEntity] = Field(
        ...,  # ✅ Required, no default
        description="List of all extracted entities from Wave 1 (92 types)"
    )

    class Config:
        json_schema_extra = {
            "required": ["entities"],  # Explicitly mark as required
            "example": {
                "entities": [
                    {
                        "entity_type": "CASE_CITATION",
                        "text": "United States v. Rahimi, No. 22-915 (U.S. Jun. 21, 2024)",
                        "start_pos": 0,
                        "end_pos": 58,
                        "confidence": 0.98,
                        "metadata": {
                            "court": "Supreme Court",
                            "case_number": "22-915",
                            "decision_date": "2024-06-21"
                        }
                    },
                    {
                        "entity_type": "USC_CITATIONS",
                        "text": "18 U.S.C. § 922(g)(8)",
                        "start_pos": 120,
                        "end_pos": 141,
                        "confidence": 0.95
                    }
                ]
            }
        }
```

### Benefits of Enhanced Schema

1. **Explicit Entity Type Taxonomy**: vLLM sees all 92 Wave 1 entity types
2. **Field Name Consistency**: Uses `entity_type` matching prompts
3. **Required Fields**: `entities`, `entity_type`, `text`, `confidence` all required
4. **Validation Rules**: Length limits (500 chars), confidence threshold (≥0.7), position ordering
5. **Legal Domain Awareness**: Schema explicitly encodes legal entity knowledge
6. **Better Error Messages**: Pydantic validation provides clear error messages

---

## Prompt Enhancement Recommendations

### Current Prompt Issues

**Wave 1 Prompt** (wave1.md) has good structure but:
1. Uses `entity_type` field (mismatches schema `type`)
2. Requests complex metadata that schema doesn't validate
3. No explicit JSON format example at the top
4. 92 entity types may overwhelm 8B model

### Recommended Prompt Improvements

```markdown
# Wave 1: Critical Legal Entities Extraction

## CRITICAL: Output Format Requirements

**YOU MUST return ONLY valid JSON matching this exact format:**

```json
{
  "entities": [
    {
      "entity_type": "CASE_CITATION",
      "text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "start_pos": 0,
      "end_pos": 48,
      "confidence": 0.95,
      "metadata": {}
    }
  ]
}
```

**Field Requirements:**
- `entities`: REQUIRED array (return empty array [] if no entities found)
- `entity_type`: REQUIRED - must be one of 92 Wave 1 types listed below
- `text`: REQUIRED - exact text from document (max 500 characters)
- `start_pos`: OPTIONAL - character position (integer ≥ 0)
- `end_pos`: OPTIONAL - character position (integer > start_pos)
- `confidence`: REQUIRED - float between 0.7 and 1.0
- `metadata`: OPTIONAL - additional entity metadata

**Valid Entity Types (92 types):**
PARTY, PLAINTIFF, DEFENDANT, APPELLANT, APPELLEE, PETITIONER, RESPONDENT,
AMICUS_CURIAE, INTERVENOR, PRO_SE_PARTY, CLASS_ACTION, INDIVIDUAL_PARTY,
CORPORATION, GOVERNMENT_ENTITY, FEDERAL_AGENCY, CONTRACT_PARTY, ESTATE,
FIDUCIARY, CASE_PARTIES, PARTY_GROUP, ATTORNEY, GOVERNMENT_LEGAL_OFFICE,
GOVERNMENT_OFFICIAL, INTERNATIONAL_LAW_FIRM, PARTIES_CLAUSE, COURT,
FEDERAL_COURTS, STATE_COURTS, SPECIALIZED_COURTS, CIRCUITS, DISTRICT,
JUDGE, JUDICIAL_PANEL, SPECIALIZED_JURISDICTION, GENERIC_COURT_REFERENCES,
ENHANCED_COURT_PATTERNS, SPECIALIZED_COURT_CITATIONS, COURT_COSTS,
COURT_RULE_CITATION, CASE_CITATION, STATUTE_CITATION, USC_CITATIONS,
USC_TITLES, CFR_CITATIONS, CFR_TITLES, STATE_STATUTES, CONSTITUTIONAL,
CONSTITUTIONAL_CITATION, CONSTITUTIONAL_AMENDMENT, REGULATION_CITATION,
ADMINISTRATIVE_CITATION, PARALLEL_CITATIONS, PINPOINT_CITATIONS, SHORT_FORMS,
ELECTRONIC_CITATION, ELECTRONIC_CITATIONS, LAW_REVIEW_CITATION,
TREATISE_CITATION, RESTATEMENT_CITATION, UNIFORM_LAW_CITATION, PATENT_CITATION,
SEC_CITATION, TREATY_CITATION, INTERNATIONAL_CITATION, INTERNATIONAL_CITATIONS,
HISTORICAL_CITATIONS, ENHANCED_CASE_CITATIONS, FEDERAL_REGISTER, DATE,
FILING_DATE, DEADLINE, DECISION_DATE, OPINION_DATE, EFFECTIVE_DATE,
EXECUTION_DATE, TERM_DATE, DATE_RANGE, RELATIVE_DATE, FISCAL_YEAR, QUARTER,
LIMITATIONS_PERIOD, MONETARY_RANGE, ENHANCED_PARTY_PATTERNS, DEFINED_TERM,
DEFINED_TERM_REFERENCE, SECTION_MARKER, SECTION_REFERENCE, SECTION_HEADER,
SUBSECTION_MARKER, SECTION_SYMBOLS, LATIN_TERM, FEDERAL_RULES

## Error Prevention Rules (CRITICAL)

🚫 **NEVER extract:**
- Filenames as CASE_CITATION: "Rahimi.md", "document.pdf"
- Generic terms as PARTY: "intimate partner", "the victim"
- Text longer than 500 characters
- Entities with confidence < 0.7

✅ **ALWAYS:**
- Return `{"entities": []}` if no qualifying entities found
- Include confidence score for every entity
- Use exact text from document (preserve capitalization)
- Limit entity text to 500 characters maximum

[... rest of prompt with entity type descriptions ...]
```

---

## Testing Strategy for Rahimi.pdf

### Expected Entities from Rahimi v. United States

Based on the Supreme Court case United States v. Rahimi, No. 22-915 (2024), expect:

**Wave 1 Extraction Target (92 types)**:

**Party & Actor Entities (10-15 expected)**:
- `PETITIONER`: "United States"
- `RESPONDENT`: "Zackey Rahimi"
- `PARTY`: "Zackey Rahimi", "United States"
- `ATTORNEY`: "Solicitor General Elizabeth Prelogar", "J. Matthew Wright"
- `GOVERNMENT_OFFICIAL`: "Chief Justice Roberts", "Justice Sotomayor"
- `JUDGE`: "Chief Justice Roberts", "Justice Sotomayor", "Justice Thomas"

**Court & Judicial (5-10 expected)**:
- `COURT`: "Supreme Court of the United States", "United States Court of Appeals"
- `FEDERAL_COURTS`: "U.S. Supreme Court", "Fifth Circuit"
- `CIRCUITS`: "Fifth Circuit Court of Appeals"
- `JUDGE`: Multiple justices

**Citations - Core (15-25 expected)**:
- `CASE_CITATION`: "United States v. Rahimi, No. 22-915 (U.S. Jun. 21, 2024)"
- `CASE_CITATION`: "District of Columbia v. Heller, 554 U.S. 570 (2008)"
- `CASE_CITATION`: "New York State Rifle & Pistol Assn., Inc. v. Bruen, 597 U.S. 1 (2022)"
- `USC_CITATIONS`: "18 U.S.C. § 922(g)(8)"
- `CONSTITUTIONAL_AMENDMENT`: "Second Amendment"

**Citations - Advanced (5-10 expected)**:
- `SHORT_FORMS`: "Bruen", "Heller"
- `PINPOINT_CITATIONS`: "554 U.S. at 595"
- `PARALLEL_CITATIONS`: Multiple reporters for same case

**Temporal (5-10 expected)**:
- `DECISION_DATE`: "June 21, 2024"
- `DATE`: Various dates in opinion
- `FILING_DATE`: Petition filing date

**Total Expected**: 40-70 entities from Wave 1

### Validation Criteria

**Success Metrics**:
- ✅ At least 40 entities extracted (minimum viable)
- ✅ All entities have `entity_type` field (not `type`)
- ✅ All entities have confidence ≥ 0.7
- ✅ Response contains `entities` key (not empty object)
- ✅ No entities exceed 500 character limit
- ✅ Entity types match Wave 1 taxonomy (92 types)

**Quality Metrics**:
- Precision: % of extracted entities that are correct (target >90%)
- Recall: % of expected entities that were extracted (target >70%)
- Entity Type Diversity: Number of different entity types extracted (target >10 types)
- Confidence Distribution: Average confidence score (target >0.85)

---

## Implementation Roadmap

### Phase 1: Schema Fixes (Priority P0 - Immediate)
1. ✅ Update `ExtractedEntity` to use `entity_type` (not `type`)
2. ✅ Make `entities` field required (remove `default_factory=list`)
3. ✅ Add Wave 1 entity type taxonomy (92 types as Literal)
4. ✅ Add validation rules (length limits, confidence thresholds)
5. ✅ Update example in `json_schema_extra` to use `entity_type`

**Files to Modify**:
- `/srv/luris/be/entity-extraction-service/src/core/entity_models.py`

### Phase 2: Re-enable Guided JSON (Priority P0 - Immediate)
1. ✅ Uncomment `extra_body={"guided_json": json_schema}` in `extraction_orchestrator.py:1031`
2. ✅ Update log message to indicate guided JSON is enabled
3. ✅ Test with fixed schema

**Files to Modify**:
- `/srv/luris/be/entity-extraction-service/src/core/extraction_orchestrator.py`

### Phase 3: Prompt Enhancements (Priority P1 - High)
1. ✅ Add explicit JSON format example at top of wave1.md
2. ✅ Emphasize required `entities` key
3. ✅ List all 92 valid entity types prominently
4. ✅ Add "return empty array if no entities" instruction
5. ✅ Simplify complex metadata requirements

**Files to Modify**:
- `/srv/luris/be/entity-extraction-service/src/prompts/wave/wave1.md`
- `/srv/luris/be/entity-extraction-service/src/prompts/wave/wave2.md`
- `/srv/luris/be/entity-extraction-service/src/prompts/wave/wave3.md`

### Phase 4: Testing & Validation (Priority P1 - High)
1. ✅ Run extraction on Rahimi.pdf
2. ✅ Validate entities format (entity_type field present)
3. ✅ Check entities array is not empty
4. ✅ Measure precision/recall against ground truth
5. ✅ Analyze entity type diversity
6. ✅ Test with different temperatures (0.3, 0.4, 0.5)

**Test Script**:
```python
# Test Wave 1 extraction with fixed schema
import asyncio
from pathlib import Path
from src.core.extraction_orchestrator import ExtractionOrchestrator
from src.routing.document_router import DocumentRouter

async def test_rahimi_extraction():
    # Load Rahimi.pdf
    doc_path = Path("/srv/luris/be/tests/docs/Rahimi.pdf")

    # Extract text (assume converted to markdown)
    with open(doc_path, 'r') as f:
        document_text = f.read()

    # Route document
    router = DocumentRouter()
    routing_decision = router.route_document(
        document_text=document_text,
        document_type="legal_opinion"
    )

    # Extract entities
    orchestrator = ExtractionOrchestrator()
    result = await orchestrator.extract(
        document_text=document_text,
        routing_decision=routing_decision,
        size_info=routing_decision.size_info
    )

    # Validate results
    print(f"✅ Entities extracted: {len(result.entities)}")
    print(f"✅ Unique entity types: {len(set(e['entity_type'] for e in result.entities))}")
    print(f"✅ Average confidence: {sum(e['confidence'] for e in result.entities) / len(result.entities):.2f}")

    # Check schema compliance
    for entity in result.entities:
        assert 'entity_type' in entity, f"Missing entity_type: {entity}"
        assert entity['confidence'] >= 0.7, f"Low confidence: {entity}"
        assert len(entity['text']) <= 500, f"Text too long: {entity}"

    print("✅ All schema validations passed!")

    return result

# Run test
result = asyncio.run(test_rahimi_extraction())
```

### Phase 5: Temperature Optimization (Priority P2 - Medium)
1. ✅ Test extraction with temperature 0.3, 0.4, 0.5
2. ✅ Measure entity type diversity for each temperature
3. ✅ Check for hallucinations at higher temperatures
4. ✅ Select optimal temperature per wave
5. ✅ Document temperature recommendations

### Phase 6: Documentation (Priority P2 - Medium)
1. ✅ Update entity_models.py docstrings
2. ✅ Document Wave 1 entity type taxonomy
3. ✅ Create troubleshooting guide for 0 entities issue
4. ✅ Document vLLM guided JSON best practices
5. ✅ Add schema examples to API documentation

---

## Critical Findings Summary

### Root Cause Analysis

**Why vLLM Returns 0 Entities:**
1. **Field Name Mismatch** (`type` vs `entity_type`) confuses the model
2. **Optional `entities` Field** allows model to return `{}`
3. **Generic Schema** doesn't encode legal domain knowledge
4. **Guided JSON Disabled** for testing (intentional)
5. **Prompt-Schema Disconnect** (92 types in prompt, any string in schema)

### Quick Wins

**Immediate Fixes (< 30 minutes)**:
1. Rename `type` → `entity_type` in ExtractedEntity
2. Remove `default_factory=list` from entities field
3. Re-enable `guided_json` in extraction_orchestrator.py
4. Test extraction - should see entities returned

**High-Impact Improvements (< 2 hours)**:
1. Add Wave1EntityTypes Literal with all 92 types
2. Add validation rules (length, confidence, position)
3. Update wave1.md prompt with explicit JSON format
4. Test with Rahimi.pdf and measure improvement

---

## Recommended Next Steps

### Immediate Actions (Today)
1. **Fix entity_models.py**:
   - Change `type` to `entity_type`
   - Make `entities` required
   - Add Wave1EntityTypes taxonomy

2. **Re-enable guided JSON**:
   - Uncomment line 1031 in extraction_orchestrator.py
   - Test with fixed schema

3. **Test with Rahimi.pdf**:
   - Run extraction
   - Validate entities returned
   - Check field names correct

### Short-Term Actions (This Week)
1. **Enhance prompts**:
   - Add explicit JSON format examples
   - Emphasize required fields
   - List valid entity types

2. **Optimize temperature**:
   - Test 0.3, 0.4, 0.5
   - Measure entity diversity
   - Select optimal value

3. **Comprehensive testing**:
   - Test all 3 waves
   - Measure precision/recall
   - Validate Bluebook compliance

### Long-Term Actions (This Month)
1. **Schema evolution**:
   - Create wave-specific schemas
   - Add relationship validation
   - Implement entity type versioning

2. **Performance optimization**:
   - Cache compiled schemas
   - Optimize prompt token usage
   - Implement batch extraction

3. **Quality assurance**:
   - Build ground truth dataset
   - Implement automated validation
   - Track precision/recall metrics

---

## Conclusion

The root cause of 0 entities returned is a **schema-prompt mismatch**:
- Pydantic model uses `type` field
- Wave prompts expect `entity_type` field
- `entities` field is optional (has default)
- Schema doesn't validate legal entity taxonomy
- Guided JSON is disabled for testing

**Fixing these 3 issues should immediately resolve the problem:**
1. Rename `type` → `entity_type` in schema
2. Make `entities` required (remove default)
3. Re-enable guided JSON

**Expected improvement**: From 0 entities to 40-70 entities on Rahimi.pdf test.

---

**Analysis completed by**: Legal Data Engineer
**Files analyzed**:
- `entity_models.py` (schema definitions)
- `extraction_orchestrator.py` (vLLM integration)
- `wave1.md` (Wave 1 prompt template)
- `settings.yaml` (entity type configuration)

**Next**: Implement Phase 1 schema fixes and test with Rahimi.pdf
