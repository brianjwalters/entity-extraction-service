# EntityType Enum Quick Reference

**Last Updated:** 2025-10-18
**Source:** Patterns API at `http://10.10.0.87:8007/api/v1/patterns`
**Total Types:** 161 (160 from API + 1 UNKNOWN)

---

## Quick Import

```python
from src.core.schema.luris_entity_schema import EntityType, LurisEntityV2
```

---

## Category Overview

| Category | Count | Use Case |
|----------|-------|----------|
| Citations | 22 | Legal citation extraction (cases, statutes, regulations) |
| Legal Parties | 12 | Party identification in legal documents |
| Temporal | 11 | Date and time extraction |
| Courts & Judicial | 9 | Court and judge entity extraction |
| Legal Professionals | 4 | Attorney and law firm identification |
| Statutory | 3 | Statutory reference extraction |
| Financial | 3 | Monetary amount extraction |
| Miscellaneous | 96 | Other legal entities and concepts |

---

## Common Entity Types by Use Case

### Document Analysis
```python
# Citation extraction
EntityType.CASE_CITATION
EntityType.STATUTE_CITATION
EntityType.CFR_CITATIONS
EntityType.USC_CITATIONS
EntityType.CONSTITUTIONAL_CITATION

# Party identification
EntityType.PLAINTIFF
EntityType.DEFENDANT
EntityType.APPELLANT
EntityType.APPELLEE
EntityType.PARTY

# Temporal information
EntityType.DATE
EntityType.FILING_DATE
EntityType.DEADLINE
EntityType.DECISION_DATE

# Court information
EntityType.FEDERAL_COURTS
EntityType.STATE_COURTS
EntityType.JUDGE
```

### Contract Analysis
```python
# Parties
EntityType.CONTRACT_PARTY
EntityType.CORPORATION

# Financial terms
EntityType.MONETARY_AMOUNT
EntityType.CONTRACT_VALUE
EntityType.THRESHOLD_AMOUNT

# Temporal
EntityType.EFFECTIVE_DATE
EntityType.EXECUTION_DATE
EntityType.TERM_DATE

# Document structure
EntityType.SECTION_MARKER
EntityType.PARAGRAPH_HEADER
EntityType.DEFINED_TERM
```

### Legal Research
```python
# Citations
EntityType.CASE_CITATION
EntityType.PARALLEL_CITATIONS
EntityType.LAW_REVIEW_CITATION
EntityType.RESTATEMENT_CITATION
EntityType.TREATISE_CITATION

# Legal concepts
EntityType.PRECEDENT
EntityType.STARE_DECISIS
EntityType.RES_JUDICATA

# Constitutional law
EntityType.CONSTITUTIONAL_CITATION
EntityType.FOURTH_AMENDMENT
EntityType.FIFTH_AMENDMENT
EntityType.DUE_PROCESS
```

### Litigation Documents
```python
# Procedural
EntityType.MOTION
EntityType.APPEAL
EntityType.DISCOVERY
EntityType.DEPOSITION

# Parties
EntityType.PLAINTIFF
EntityType.DEFENDANT
EntityType.INTERVENOR
EntityType.AMICUS_CURIAE

# Court actions
EntityType.JUDGMENT
EntityType.INJUNCTION
EntityType.DEFAULT_JUDGMENT

# Evidence
EntityType.ADMISSION_REQUEST
EntityType.INTERROGATORY
EntityType.PRODUCTION_REQUEST
```

---

## Usage Examples

### Basic Entity Extraction

```python
from src.core.schema.luris_entity_schema import EntityType, LurisEntityV2, Position
import uuid

# Create a legal entity
entity = LurisEntityV2(
    id=str(uuid.uuid4()),
    text="28 U.S.C. § 1331",
    entity_type=EntityType.STATUTE_CITATION.value,
    position=Position(start_pos=0, end_pos=17),
    confidence=0.95,
    extraction_method="ai_enhanced"
)

# Access entity properties
print(f"Type: {entity.entity_type}")  # STATUTE_CITATION
print(f"Text: {entity.text}")         # 28 U.S.C. § 1331
print(f"Confidence: {entity.confidence}")  # 0.95
```

### Entity Type Validation

```python
from src.core.schema.luris_entity_schema import EntityType

# Check if type exists
def is_valid_entity_type(type_str: str) -> bool:
    try:
        EntityType(type_str)
        return True
    except ValueError:
        return False

# Example usage
is_valid_entity_type("CASE_CITATION")  # True
is_valid_entity_type("INVALID_TYPE")   # False
```

### Category-Based Filtering

```python
from src.core.schema.luris_entity_schema import EntityType

# Get all citation types
citation_types = [
    EntityType.ADMINISTRATIVE_CITATION,
    EntityType.CASE_CITATION,
    EntityType.CFR_CITATIONS,
    EntityType.CONSTITUTIONAL_CITATION,
    EntityType.STATUTE_CITATION,
    EntityType.USC_CITATIONS,
    # ... etc
]

# Filter entities by category
def filter_citations(entities: list) -> list:
    citation_type_values = [t.value for t in citation_types]
    return [e for e in entities if e.entity_type in citation_type_values]
```

---

## All Entity Types by Category

### Citations (22)
```
ADMINISTRATIVE_CITATION, CASE_CITATION, CFR_CITATIONS, CONSTITUTIONAL_CITATION,
ELECTRONIC_CITATION, ELECTRONIC_CITATIONS, ENHANCED_CASE_CITATIONS,
HISTORICAL_CITATIONS, INTERNATIONAL_CITATION, INTERNATIONAL_CITATIONS,
LAW_REVIEW_CITATION, PARALLEL_CITATIONS, PATENT_CITATION, PINPOINT_CITATIONS,
REGULATION_CITATION, RESTATEMENT_CITATION, SEC_CITATION, STATUTE_CITATION,
TREATISE_CITATION, TREATY_CITATION, UNIFORM_LAW_CITATION, USC_CITATIONS
```

### Legal Parties (12)
```
APPELLANT, APPELLEE, CONTRACT_PARTY, DEFENDANT, ENHANCED_PARTY_PATTERNS,
INDIVIDUAL_PARTY, PARTY, PARTY_GROUP, PETITIONER, PLAINTIFF, PRO_SE_PARTY,
RESPONDENT
```

### Temporal (11)
```
DATE, DATE_RANGE, DEADLINE, DECISION_DATE, EFFECTIVE_DATE, EXECUTION_DATE,
FILING_DATE, LIMITATIONS_PERIOD, OPINION_DATE, RELATIVE_DATE, TERM_DATE
```

### Courts and Judicial (9)
```
COURT_COSTS, COURT_RULE_CITATION, ENHANCED_COURT_PATTERNS, FEDERAL_COURTS,
GENERIC_COURT_REFERENCES, JUDGE, SPECIALIZED_COURTS, SPECIALIZED_COURT_CITATIONS,
STATE_COURTS
```

### Legal Professionals (4)
```
ATTORNEY, ATTORNEY_FEES, INTERNATIONAL_LAW_FIRM, LAW_FIRM
```

### Statutory (3)
```
CFR_TITLES, STATE_STATUTES, USC_TITLES
```

### Financial (3)
```
MONETARY_AMOUNT, PER_UNIT_AMOUNT, THRESHOLD_AMOUNT
```

### Miscellaneous (96)
```
ADDRESS, ADMINISTRATIVE, ADMISSION_REQUEST, AGENCIES, AMENDMENTS, AMICUS_CURIAE,
APPEAL, ARTICLE_REFERENCE, BAIL, CASE_PARTIES, CERTIORARI, CIRCUITS, CLASS_ACTION,
COMMERCE_CLAUSE, CONGRESSIONAL, CONSTITUTIONAL, CONSTITUTIONAL_AMENDMENT,
CONTRACT_VALUE, CORPORATE_RESOLUTION, CORPORATION, DAMAGES, DEFAULT_JUDGMENT,
DEFINED_TERM, DEFINED_TERM_REFERENCE, DEMURRER, DEPOSITION, DISCOVERY, DISTRICT,
DOUBLE_JEOPARDY, DUE_PROCESS, EIGHTH_AMENDMENT, ENHANCED_PROCEDURAL_PATTERNS,
ENTITY_STATUS, EQUAL_PROTECTION, ESTATE, FEDERAL_AGENCY, FEDERAL_REGISTER,
FEDERAL_RULES, FIDUCIARY, FIFTH_AMENDMENT, FINE, FISCAL_YEAR, FOURTH_AMENDMENT,
FREE_SPEECH, GOVERNMENT_ENTITY, GOVERNMENT_LEGAL_OFFICE, GOVERNMENT_OFFICIAL,
HABEAS_CORPUS, HISTORICAL, IMMUNITY, INJUNCTION, INTEREST_RATE, INTERROGATORY,
INTERVENOR, JUDGMENT, JUDICIAL_PANEL, JURISDICTION, LATIN_TERM, LEGAL_MARKER,
LOCATION, MONETARY_RANGE, MOTION, NOTARY_BLOCK, PARAGRAPH_HEADER, PARTIES_CLAUSE,
PATTERNS, PLEA, PRECEDENT, PRECLUSION, PROCEDURAL_RULE, PRODUCTION_REQUEST,
PROTECTIVE_ORDER, PUBLIC_INTEREST_FIRM, PUBLIC_LAWS, QUARTER, RELIGIOUS_FREEDOM,
RESTITUTION, RES_JUDICATA, SECTION_HEADER, SECTION_MARKER, SECTION_REFERENCE,
SECTION_SYMBOLS, SENTENCING, SETTLEMENT, SHORT_FORMS, SIGNATORY_BLOCK,
SIGNATURE_LINE, SIXTH_AMENDMENT, SOVEREIGN_IMMUNITY, SPECIALIZED_JURISDICTION,
STARE_DECISIS, STATUTORY_CONSTRUCTION, SUBSECTION_MARKER, SUPREMACY_CLAUSE,
VENUE, WITNESS_BLOCK
```

---

## Migration Guide

### From Old EntityType (42 types) to New (161 types)

Most old entity types still exist. Here are the mappings for changed types:

| Old Type | New Type | Notes |
|----------|----------|-------|
| `COURT` | `FEDERAL_COURTS` or `STATE_COURTS` | More specific |
| `USC_CITATION` | `USC_CITATIONS` | Plural form |
| `CFR_CITATION` | `CFR_CITATIONS` | Plural form |
| `STATE_STATUTE_CITATION` | `STATE_STATUTES` | Simplified |
| `FEE` | `ATTORNEY_FEES` or `COURT_COSTS` | More specific |
| `AWARD` | `DAMAGES` or `SETTLEMENT` | More specific |

### New Types Available (119 additional)

The new enum adds 119 entity types that were not in the old schema. Review the full list above to see what's now available.

---

## Best Practices

1. **Always use EntityType enum constants**
   ```python
   # ✅ Good
   entity_type = EntityType.CASE_CITATION.value

   # ❌ Bad
   entity_type = "CASE_CITATION"
   ```

2. **Validate entity types before use**
   ```python
   try:
       entity_type = EntityType(user_input)
   except ValueError:
       # Handle invalid type
       entity_type = EntityType.UNKNOWN
   ```

3. **Use category-based organization**
   - Group related entity types together
   - Use consistent naming within categories
   - Leverage the 8-category taxonomy

4. **Check the Patterns API for examples**
   - Each entity type has regex pattern examples
   - API: `http://10.10.0.87:8007/api/v1/patterns`
   - Use examples to understand entity type usage

---

## Troubleshooting

### "Unknown entity type" Warning

If you see this warning during extraction:
```
WARNING: Unknown entity type: XYZ, using UNKNOWN
```

**Solutions:**
1. Check if the type exists in the 161-type enum
2. Verify correct spelling and capitalization
3. Use `EntityType.UNKNOWN` for unrecognized types
4. Update extraction logic to use new entity types

### Import Errors

If imports fail:
```python
from src.core.schema.luris_entity_schema import EntityType
```

**Solutions:**
1. Ensure you're in the entity-extraction-service directory
2. Activate venv: `source venv/bin/activate`
3. Verify file exists at correct path
4. Check for syntax errors in the schema file

---

## Additional Resources

- **Full Specification:** `/srv/luris/be/entity-extraction-service/docs/LurisEntityV2_Specification.md`
- **Patterns API:** `http://10.10.0.87:8007/api/v1/patterns`
- **Schema File:** `/srv/luris/be/entity-extraction-service/src/core/schema/luris_entity_schema.py`
- **Generation Report:** `/tmp/entity_type_enum_generation_report.md`

---

**Canonical Source:** This enum is generated from the Patterns API and represents the single source of truth for all entity types in the Luris platform.
