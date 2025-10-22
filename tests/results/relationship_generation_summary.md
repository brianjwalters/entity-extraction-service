# Entity Relationship Generation Summary

**Generated:** 2025-10-15
**Purpose:** Synthetic entity relationship data for test dashboard visualization

---

## 📊 Overview

Successfully generated **59 entity relationships** across **6 test cases** involving **52 unique entities** from the Entity Extraction Service test suite.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Total Tests** | 6 |
| **Total Entities** | 52 |
| **Total Relationships** | 59 |
| **Avg Relationships/Test** | 9.8 |
| **Relationship Types** | 3 |

---

## 🔗 Relationship Types

### Distribution by Type

| Relationship Type | Count | Avg Confidence | Description |
|------------------|-------|----------------|-------------|
| **CO_OCCURS** | 53 | 0.745 | Entities appearing within 200 characters of each other |
| **FILED_IN** | 3 | 0.923 | Party-Court filing relationships |
| **REPRESENTS** | 3 | 0.893 | Attorney-Party representation relationships |

### Confidence Statistics

- **Mean Confidence:** 0.761
- **Min Confidence:** 0.650
- **Max Confidence:** 0.950
- **Standard Range:** 0.65 - 0.99

---

## 📋 Test-by-Test Breakdown

### Test 1: `test_1760575089802`
**Document:** case_001 | **Entities:** 14 | **Relationships:** 10

**Relationship Types:**
- CO_OCCURS: 7 relationships
- FILED_IN: 2 relationships
- REPRESENTS: 1 relationship

**Sample Relationships:**
```
1. FILED_IN (confidence: 0.92)
   United States of America (PARTY) → United States District Court (COURT)

2. CO_OCCURS (confidence: 0.80)
   United States of America (PARTY) → Southern District of New York (STATE_STATUTE_CITATION)

3. CO_OCCURS (confidence: 0.72)
   United States of America (PARTY) → Case No. (CASE_CITATION)
```

---

### Test 2: `test_1760575126888`
**Document:** case_002 | **Entities:** 5 | **Relationships:** 9

**Relationship Types:**
- CO_OCCURS: 9 relationships (all proximity-based)

**Sample Relationships:**
```
1. CO_OCCURS (confidence: 0.84)
   [Long case text] (CASE_CITATION) → California Penal Code § 148(a)(1) (STATUTE_CITATION)

2. CO_OCCURS (confidence: 0.84)
   [Case citation] (CASE_CITATION) → 42 U.S.C. § 1983 (STATUTE_CITATION)

3. CO_OCCURS (confidence: 0.74)
   [Case citation] (CASE_CITATION) → June 18, 2022 (DATE)
```

---

### Test 3: `test_1760575189645`
**Document:** case_003 | **Entities:** 15 | **Relationships:** 10

**Relationship Types:**
- CO_OCCURS: 8 relationships
- REPRESENTS: 2 relationships

**Sample Relationships:**
```
1. CO_OCCURS (confidence: 0.79)
   Supreme Court of the United States (COURT) → Students for Academic Freedom (PARTY)

2. CO_OCCURS (confidence: 0.70)
   Supreme Court of the United States (COURT) → Riverside Unified School District (PARTY)

3. REPRESENTS (confidence: 0.89)
   [Party] → Chief Justice Roberts (ATTORNEY)
```

---

### Test 4: `test_1760575343531`
**Document:** case_004 | **Entities:** 6 | **Relationships:** 10

**Relationship Types:**
- CO_OCCURS: 10 relationships (all proximity-based)

**Note:** This test contains generic placeholder text entities with high co-occurrence due to document structure.

---

### Test 5: `test_1760575386296`
**Document:** case_005 | **Entities:** 6 | **Relationships:** 10

**Relationship Types:**
- CO_OCCURS: 8 relationships
- FILED_IN: 2 relationships

**Sample Relationships:**
```
1. FILED_IN (confidence: 0.95)
   United States of America (PARTY) → Supreme Court of the United States (COURT)

2. CO_OCCURS (confidence: 0.79)
   United States of America (PARTY) → 18 U.S.C. § 924(c)(1)(A)(ii) (STATUTE_CITATION)

3. CO_OCCURS (confidence: 0.75)
   United States of America (PARTY) → 18 U.S.C. § 2113(a) (STATUTE_CITATION)
```

---

### Test 6: `test_1760575420481`
**Document:** case_006 | **Entities:** 6 | **Relationships:** 10

**Relationship Types:**
- CO_OCCURS: 10 relationships (all proximity-based)

**Sample Relationships:**
```
1. CO_OCCURS (confidence: 0.81)
   [Court name] (COURT) → Defendant Smith Construction, Inc. (PARTY)

2. CO_OCCURS (confidence: 0.78)
   [Court name] (COURT) → JOHNSON v. SMITH CONSTRUCTION, INC. (PARTY)

3. CO_OCCURS (confidence: 0.71)
   [Court name] (COURT) → February 1, 2023 (DATE)
```

---

## 🎯 Relationship Generation Rules

### 1. **PARTY-ATTORNEY (REPRESENTS)**
- **Trigger:** Party entity + Attorney entity
- **Confidence Range:** 0.85 - 0.98
- **Context:** "Attorney [name] represents [party]"
- **Metadata:** Legal role, relationship strength

### 2. **CASE-STATUTE (CITES)**
- **Trigger:** Case citation + Statute citation
- **Confidence Range:** 0.80 - 0.95
- **Context:** "Case [citation] cites statute [reference]"
- **Metadata:** Citation type, precedential value

### 3. **JUDGE-COURT (PRESIDES_OVER)**
- **Trigger:** Judge entity + Court entity
- **Confidence Range:** 0.90 - 0.99
- **Context:** "Judge [name] presides over [court]"
- **Metadata:** Jurisdiction, judicial role

### 4. **PARTY-COURT (FILED_IN)**
- **Trigger:** Party entity + Court entity
- **Confidence Range:** 0.85 - 0.96
- **Context:** "Case involving [party] filed in [court]"
- **Metadata:** Filing type, venue

### 5. **EVENT-DATE (OCCURS_ON)**
- **Trigger:** Date entity + Party/Event entity
- **Confidence Range:** 0.75 - 0.92
- **Context:** "Event involving [party] on [date]"
- **Metadata:** Temporal type, precision

### 6. **CO-OCCURRENCE (CO_OCCURS)**
- **Trigger:** Any two entities within 200 characters
- **Confidence Range:** 0.65 - 0.85
- **Context:** Generated based on entity texts
- **Metadata:** Proximity distance, co-occurrence strength

---

## ✅ Validation Results

### All Validation Checks Passed

- ✅ **Entity ID Validation:** All source/target entity IDs exist in respective test entities
- ✅ **Confidence Range:** All scores within valid range [0.0, 1.0]
- ✅ **Position Validity:** All start/end positions are valid and ordered correctly
- ✅ **Test ID Consistency:** All relationships correctly reference parent test
- ✅ **Document ID Consistency:** All relationships reference correct document

### Data Quality Metrics

- **0** invalid entity references
- **0** out-of-range confidence scores
- **0** invalid position ranges
- **100%** validation pass rate

---

## 🔧 Implementation Details

### Relationship Structure

Each relationship contains:

```json
{
  "id": "rel-{uuid}",
  "source_entity_id": "entity-uuid-1",
  "target_entity_id": "entity-uuid-2",
  "relationship_type": "REPRESENTS|CITES|PRESIDES_OVER|FILED_IN|OCCURS_ON|CO_OCCURS",
  "confidence": 0.85,
  "start_pos": 1250,
  "end_pos": 1500,
  "context": "descriptive text connecting both entities",
  "test_id": "test_xxx",
  "document_id": "case_001",
  "metadata": {
    "relationship_strength": "strong|moderate|weak",
    "legal_role": "representation|filing|citation|etc"
  }
}
```

### Proximity Calculation

CO_OCCURS relationships use proximity-based detection:
- **Max Distance:** 200 characters
- **Calculation:** Minimum distance between entity boundaries
- **Filter:** Only creates relationships between different entity types

---

## 📈 Usage in Dashboard

This synthetic relationship data enables:

1. **Entity Network Visualization:**
   - Graph visualization of entity connections
   - Relationship type filtering
   - Confidence-based edge weighting

2. **Relationship Analytics:**
   - Type distribution charts
   - Confidence score histograms
   - Co-occurrence pattern analysis

3. **Test Comparison:**
   - Cross-test relationship patterns
   - Entity interaction frequency
   - Relationship density metrics

4. **Quality Metrics:**
   - Relationship confidence trends
   - Type-specific confidence analysis
   - Validation status tracking

---

## 🚀 Future Enhancements

### Potential Additions

1. **Temporal Relationships:**
   - BEFORE/AFTER relationships between dates
   - Timeline-based event sequencing

2. **Hierarchical Relationships:**
   - PART_OF (entity hierarchy)
   - BELONGS_TO (jurisdiction relationships)

3. **Semantic Relationships:**
   - CONFLICTS_WITH (opposing parties)
   - SUPPORTS (legal argument chains)

4. **Advanced Metadata:**
   - Relationship strength scoring
   - Legal significance weighting
   - Document section context

### Dashboard Integration

- **Interactive network graphs** using D3.js or Cytoscape
- **Relationship filtering** by type, confidence, test
- **Entity-centric views** showing all relationships for selected entity
- **Temporal analysis** of relationship evolution across tests

---

## 📝 Notes

- All relationships generated using realistic legal domain patterns
- Confidence scores calibrated to reflect relationship type certainty
- Proximity threshold (200 chars) based on typical legal document density
- Metadata structure allows future expansion without schema changes

**File Location:** `/srv/luris/be/entity-extraction-service/tests/results/test_history.json`

**Last Updated:** 2025-10-15
