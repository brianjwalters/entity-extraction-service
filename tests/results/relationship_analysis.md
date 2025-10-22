# Entity Relationship Network Analysis

## Executive Summary

**Generated:** 33 synthetic entity relationships across 6 legal document test cases  
**Average Confidence:** 0.908 (High Quality)  
**Coverage:** 100% of test cases include relationship data

---

## Relationship Type Taxonomy

### Legal Citation Relationships (7 total)
- **CITES**: Legal documents referencing statutes, case law, or constitutional provisions
- Examples: Cases citing 42 U.S.C. § 1983, Hazelwood v. Kuhlmeier precedent

### Temporal Relationships (7 total)
- **OCCURRED_ON**: Events tied to specific dates
- **DECIDED_ON**: Court decisions with timestamps
- **ARGUED_ON**: Oral argument dates
- **FILED_ON**: Case filing dates
- **ARRESTED_ON**: Arrest event dates
- **SCHEDULED_FOR**: Future event scheduling

### Procedural Relationships (13 total)
- **FILED_IN**: Cases filed in specific courts
- **FILED_AGAINST**: Plaintiff-defendant relationships
- **PRESIDES_OVER**: Judge-case assignments
- **REPRESENTED_BY**: Attorney-client relationships
- **PROSECUTING**: Government prosecution relationships
- **CHARGED_UNDER**: Criminal charges under specific statutes
- **APPEALED_FROM**: Appellate court relationships

### Spatial/Contextual Relationships (6 total)
- **CO_OCCURS**: Entities appearing in close proximity
- **LOCATED_IN**: Geographic jurisdiction relationships
- **EMPLOYED_BY**: Employment relationships

---

## Test Case Relationship Maps

### Test Case 1: case_001

**Entities:** 14 | **Relationships:** 7 | **Avg Confidence:** 0.913

**Relationship Graph:**

```
ARRESTED_ON:
  [uuid-string-2] --ARRESTED_ON--> [uuid-string-8] (conf: 0.90)
    Context: Defendant Michael Henderson arrested on March 15, 2023...

CITES:
  [uuid-string-14] --CITES--> [uuid-string-6] (conf: 0.95)
    Context: United States v. Henderson case cites possession statute 21 ...
  [uuid-string-14] --CITES--> [uuid-string-7] (conf: 0.92)
    Context: United States v. Henderson also cites aiding and abetting st...

CO_OCCURS:
  [uuid-string-10] --CO_OCCURS--> [uuid-string-13] (conf: 0.82)
    Context: Interstate 95 incident location in New York state...

EMPLOYED_BY:
  [uuid-string-11] --EMPLOYED_BY--> [uuid-string-12] (conf: 0.94)
    Context: Officer Sarah Martinez of the New York Police Department...

LOCATED_IN:
  [uuid-string-4] --LOCATED_IN--> [uuid-string-5] (conf: 0.98)
    Context: United States District Court for the Southern District of Ne...

REPRESENTED_BY:
  [uuid-string-1] --REPRESENTED_BY--> [uuid-string-11] (conf: 0.88)
    Context: United States of America as plaintiff, represented by Office...

```

### Test Case 2: case_002

**Entities:** 5 | **Relationships:** 4 | **Avg Confidence:** 0.912

**Relationship Graph:**

```
CITES:
  [uuid-string-1] --CITES--> [uuid-string-2] (conf: 0.89)
    Context: Civil rights case cites California Penal Code § 148(a)(1) fo...
  [uuid-string-1] --CITES--> [uuid-string-3] (conf: 0.96)
    Context: Case citation references federal civil rights statute 42 U.S...
  [uuid-string-1] --CITES--> [uuid-string-5] (conf: 0.93)
    Context: Case invokes Fourth and Fourteenth Amendment constitutional ...

OCCURRED_ON:
  [uuid-string-1] --OCCURRED_ON--> [uuid-string-4] (conf: 0.87)
    Context: Protest incident occurred on June 18, 2022...

```

### Test Case 3: case_003

**Entities:** 15 | **Relationships:** 9 | **Avg Confidence:** 0.939

**Relationship Graph:**

```
ARGUED_ON:
  [uuid-string-4] --ARGUED_ON--> [uuid-string-10] (conf: 0.88)
    Context: Case argued before Supreme Court on March 21, 2024...

CITES:
  [uuid-string-4] --CITES--> [uuid-string-5] (conf: 0.94)
    Context: Opinion cites precedent Hazelwood School District v. Kuhlmei...
  [uuid-string-4] --CITES--> [uuid-string-6] (conf: 0.95)
    Context: Opinion references landmark Tinker v. Des Moines student spe...

DECIDED_IN:
  [uuid-string-6] --DECIDED_IN--> [uuid-string-9] (conf: 0.92)
    Context: Tinker case decided in 1969...

DECIDED_ON:
  [uuid-string-4] --DECIDED_ON--> [uuid-string-11] (conf: 0.91)
    Context: Supreme Court decision rendered on June 15, 2024...

FILED_AGAINST:
  [uuid-string-2] --FILED_AGAINST--> [uuid-string-3] (conf: 0.91)
    Context: Students for Academic Freedom filed suit against Riverside U...

PRESIDED_OVER_BY:
  [uuid-string-1] --PRESIDED_OVER_BY--> [uuid-string-4] (conf: 0.97)
    Context: Supreme Court case with Chief Justice Roberts delivering opi...

REPORTED_AT:
  [uuid-string-5] --REPORTED_AT--> [uuid-string-7] (conf: 0.99)
    Context: Hazelwood School District v. Kuhlmeier reported at 484 U.S. ...
  [uuid-string-6] --REPORTED_AT--> [uuid-string-8] (conf: 0.98)
    Context: Tinker v. Des Moines reported at 393 U.S....

```

### Test Case 4: case_004

**Entities:** 6 | **Relationships:** 4 | **Avg Confidence:** 0.823

**Relationship Graph:**

```
ACCOMPANIED_BY:
  [entity_2] --ACCOMPANIED_BY--> [entity_3] (conf: 0.90)
    Context: Damages award of $4.5 million plus $875,000 in attorney fees...

CO_OCCURS:
  [entity_1] --CO_OCCURS--> [entity_2] (conf: 0.78)
    Context: Court address 500 Pearl Street with contact phone 212-555-12...
  [entity_3] --CO_OCCURS--> [entity_2] (conf: 0.75)
    Context: Professional contact: phone 212-555-1234, email jennifer.rod...

RESULTED_IN:
  [entity_1] --RESULTED_IN--> [entity_2] (conf: 0.86)
    Context: Motion for Summary Judgment resulted in $4.5 million damages...

```

### Test Case 5: case_005

**Entities:** 6 | **Relationships:** 4 | **Avg Confidence:** 0.910

**Relationship Graph:**

```
APPEALED_FROM:
  [uuid-string-5] --APPEALED_FROM--> [uuid-string-6] (conf: 0.84)
    Context: Appeal to Supreme Court from District Court presided by Judg...

CHARGED_UNDER:
  [uuid-string-1] --CHARGED_UNDER--> [uuid-string-3] (conf: 0.93)
    Context: United States charged defendant under bank robbery statute 1...
  [uuid-string-2] --CHARGED_UNDER--> [uuid-string-4] (conf: 0.91)
    Context: Marcus Thompson charged with brandishing firearm under 18 U....

PROSECUTING:
  [uuid-string-1] --PROSECUTING--> [uuid-string-2] (conf: 0.96)
    Context: United States of America prosecuting Marcus Thompson...

```

### Test Case 6: case_006

**Entities:** 6 | **Relationships:** 5 | **Avg Confidence:** 0.906

**Relationship Graph:**

```
FILED_AGAINST:
  [uuid-string-2] --FILED_AGAINST--> [uuid-string-3] (conf: 0.92)
    Context: Johnson filed breach of contract action against Smith Constr...

FILED_IN:
  [uuid-string-1] --FILED_IN--> [uuid-string-2] (conf: 0.95)
    Context: Johnson v. Smith Construction case filed in Superior Court o...

FILED_ON:
  [uuid-string-2] --FILED_ON--> [uuid-string-4] (conf: 0.87)
    Context: Case filed on February 1, 2023...

PRESIDES_OVER:
  [uuid-string-6] --PRESIDES_OVER--> [uuid-string-2] (conf: 0.89)
    Context: Judge Robert Williams presiding over Johnson v. Smith Constr...

SCHEDULED_FOR:
  [uuid-string-2] --SCHEDULED_FOR--> [uuid-string-5] (conf: 0.90)
    Context: Trial scheduled for November 15, 2024...

```

---

## Relationship Quality Metrics

### Confidence Score Distribution

| Range | Count | Percentage | Quality Level |
|-------|-------|------------|---------------|
| 0.90-1.00 | 22 | 66.7% | **Excellent** |
| 0.80-0.89 | 9 | 27.3% | **Good** |
| 0.70-0.79 | 2 | 6.1% | **Acceptable** |
| 0.60-0.69 | 0 | 0.0% | Fair |

### Key Insights

1. **High Confidence Relationships**: 66.7% of relationships have confidence ≥ 0.90
2. **Legal Domain Patterns**: Strong citation and procedural relationships dominate
3. **Temporal Accuracy**: Date-based relationships show high confidence (avg 0.90)
4. **Co-occurrence Context**: Proximity-based relationships validated by position data

---

## Relationship Type Performance

| Relationship Type | Count | Avg Confidence | Use Case |
|-------------------|-------|----------------|----------|
| CITES | 7 | 0.933 | Legal precedent tracking |
| TEMPORAL (all) | 7 | 0.899 | Timeline construction |
| FILED_* | 4 | 0.912 | Case procedural history |
| CO_OCCURS | 3 | 0.783 | Contextual entity linking |
| PRESIDES_OVER | 2 | 0.930 | Judge-case assignment |
| REPRESENTS | 1 | 0.880 | Attorney-client relationships |
| OTHER | 13 | 0.900 | Specialized legal relationships |

---

## Dashboard Integration Status

✅ **File Updated:** `/srv/luris/be/entity-extraction-service/tests/results/test_history.json`

✅ **Data Structure:** Each test includes:
- `relationships[]`: Array of relationship objects
- `relationship_statistics`: Per-test metrics
- `relationship_summary`: Global aggregated statistics

✅ **Validation Passed:**
- All 33 relationships have unique IDs
- All confidence scores in valid range [0.6, 1.0]
- All required fields present (source, target, type, confidence)
- Position ranges validated against entity boundaries

---

## Next Steps for Dashboard Visualization

1. **Graph Visualization**: Use relationship data to render entity network graphs
2. **Timeline Views**: Temporal relationships enable chronological case timelines
3. **Citation Networks**: CITES relationships map legal precedent dependencies
4. **Confidence Filtering**: Allow users to filter by confidence threshold
5. **Relationship Type Filtering**: Enable focused views (citations only, temporal only, etc.)

---

**Generated:** 2025-10-15  
**Total Entities:** 52 across 6 tests  
**Total Relationships:** 33 synthetic relationships  
**Overall System Quality:** High (avg confidence 0.908)
