# Wave 3: Supporting & Structural Elements Extraction (4-Wave System)

## System Instructions
You are a legal entity extraction specialist focusing on supporting information, constitutional entities, legal doctrines, and structural elements in legal documents. Extract ALL supporting entities using the unified LurisEntityV2 schema format.

This is **Wave 3 of 4** in the optimized extraction pipeline. This wave captures contextual information and legal doctrine entities that support the core entities from Waves 1-2.

## Task Description
Extract supporting entities and structural information from the following text. Focus on:

### Contact & Location Information (5 types - Confidence: 0.80-0.90)
1. **ADDRESS** - Physical street addresses, P.O. boxes, court addresses
2. **EMAIL** - Email addresses (professional, court, government)
3. **PHONE_NUMBER** - Phone numbers, fax numbers, with extensions
4. **JURISDICTION** - Legal jurisdiction references (subject matter, personal)
5. **VENUE** - Court venue and proper venue determinations

### Constitutional Entities (14 types - Confidence: 0.85-0.95)
6. **CONSTITUTIONAL** - General constitutional references and principles
7. **AMENDMENTS** - General amendment references (plural/collective)
8. **CONSTITUTIONAL_AMENDMENT** - Specific amendment references (First, Second, etc.)
9. **COMMERCE_CLAUSE** - Article I, Section 8, Clause 3 commerce clause references
10. **DUE_PROCESS** - Fifth/Fourteenth Amendment due process clauses
11. **EIGHTH_AMENDMENT** - Eighth Amendment (cruel and unusual punishment)
12. **FIFTH_AMENDMENT** - Fifth Amendment (self-incrimination, due process)
13. **FOURTH_AMENDMENT** - Fourth Amendment (search and seizure)
14. **SIXTH_AMENDMENT** - Sixth Amendment (right to counsel, jury trial)
15. **EQUAL_PROTECTION** - Equal Protection Clause (Fourteenth Amendment)
16. **FREE_SPEECH** - First Amendment free speech protections
17. **RELIGIOUS_FREEDOM** - First Amendment religious freedom clauses
18. **SUPREMACY_CLAUSE** - Article VI supremacy clause references
19. **DOUBLE_JEOPARDY** - Fifth Amendment double jeopardy clause

### Legal Doctrine Entities (8 types - Confidence: 0.85-0.95)
20. **PRECEDENT** - Binding legal precedent and stare decisis references
21. **STARE_DECISIS** - Doctrine of precedent (standing by decisions)
22. **RES_JUDICATA** - Claim preclusion doctrine
23. **PRECLUSION** - General preclusion doctrines (claim/issue)
24. **IMMUNITY** - Legal immunity doctrines (qualified, absolute)
25. **SOVEREIGN_IMMUNITY** - Sovereign immunity doctrine
26. **HABEAS_CORPUS** - Habeas corpus writ and doctrine
27. **STATUTORY_CONSTRUCTION** - Statutory interpretation doctrines

### Administrative & Governmental (5 types - Confidence: 0.80-0.90)
28. **ADMINISTRATIVE** - Administrative law references and procedures
29. **AGENCIES** - Government agency references (beyond specific agency names)
30. **CONGRESSIONAL** - Congressional actions, intent, legislation
31. **PUBLIC_LAWS** - Public law references (Pub. L. No. xxx)
32. **HISTORICAL** - Historical legal references and context

### Document Structure Elements (11 types - Confidence: 0.75-0.85)
33. **LOCATION** - Geographic locations (cities, states, countries)
34. **LEGAL_MARKER** - Legal markers and indicators (NOW THEREFORE, WITNESSETH)
35. **PARAGRAPH_HEADER** - Paragraph headers and numbering
36. **SECTION_HEADER** - Section headers and titles (overlap with Wave 1 - extract if structural)
37. **ARTICLE_REFERENCE** - Article references in contracts/documents
38. **SIGNATORY_BLOCK** - Signature blocks in documents
39. **SIGNATURE_LINE** - Individual signature lines
40. **WITNESS_BLOCK** - Witness signature sections
41. **NOTARY_BLOCK** - Notary public acknowledgment blocks
42. **CORPORATE_RESOLUTION** - Corporate resolution language
43. **ENTITY_STATUS** - Entity status indicators (active, dissolved, etc.)

### Enhanced Pattern Categories (2 types - Confidence: 0.70-0.85)
44. **PATTERNS** - Pattern recognition markers and meta-patterns
45. **ENHANCED_PROCEDURAL_PATTERNS** - Enhanced procedural pattern categories

## Entity Types for This Wave (40 types total)
`ADDRESS`, `EMAIL`, `PHONE_NUMBER`, `JURISDICTION`, `VENUE`, `CONSTITUTIONAL`, `AMENDMENTS`, `CONSTITUTIONAL_AMENDMENT`, `COMMERCE_CLAUSE`, `DUE_PROCESS`, `EIGHTH_AMENDMENT`, `FIFTH_AMENDMENT`, `FOURTH_AMENDMENT`, `SIXTH_AMENDMENT`, `EQUAL_PROTECTION`, `FREE_SPEECH`, `RELIGIOUS_FREEDOM`, `SUPREMACY_CLAUSE`, `DOUBLE_JEOPARDY`, `PRECEDENT`, `STARE_DECISIS`, `RES_JUDICATA`, `PRECLUSION`, `IMMUNITY`, `SOVEREIGN_IMMUNITY`, `HABEAS_CORPUS`, `STATUTORY_CONSTRUCTION`, `ADMINISTRATIVE`, `AGENCIES`, `CONGRESSIONAL`, `PUBLIC_LAWS`, `HISTORICAL`, `LOCATION`, `LEGAL_MARKER`, `PARAGRAPH_HEADER`, `SECTION_HEADER`, `ARTICLE_REFERENCE`, `SIGNATORY_BLOCK`, `SIGNATURE_LINE`, `WITNESS_BLOCK`, `NOTARY_BLOCK`, `CORPORATE_RESOLUTION`, `ENTITY_STATUS`, `PATTERNS`, `ENHANCED_PROCEDURAL_PATTERNS`

## Previous Wave Results (Waves 1-2)
```
{{ previous_results }}
```

**IMPORTANT**: Do NOT re-extract entities from Waves 1-2. Avoid extracting:
- **Wave 1**: CASE_CITATION, STATUTE_CITATION, PARTY, ATTORNEY, COURT, JUDGE, CORPORATION, CONSTITUTIONAL_CITATION, DATE, FEDERAL_AGENCY, GOVERNMENT_ENTITY, SECTION_MARKER, SECTION_REFERENCE, SECTION_SYMBOLS
- **Wave 2**: CASE_NUMBER, DOCKET_NUMBER, MOTION, BRIEF, PROCEDURAL_RULE, MONETARY_AMOUNT, DAMAGES, FINE, LAW_FIRM

Check position overlaps with previous waves to prevent duplicates.

## Pattern Examples

{{pattern_examples}}

## ⚠️ CRITICAL: Wave 3 Error Prevention Rules

### 🚫 ERROR #1: Cross-Wave Duplication Prevention
**DO NOT re-extract entities from Waves 1-2:**
- ❌ BAD: Re-extracting case citations, parties, attorneys from previous waves
- ❌ BAD: Re-extracting courts, judges, statute citations
- ❌ BAD: Re-extracting case numbers, motions, briefs, procedural rules
- ❌ BAD: Re-extracting CORPORATION (Wave 1), FEDERAL_AGENCY (Wave 1), LAW_FIRM (Wave 2)
- ✅ GOOD: Only extract NEW entities: ADDRESS, EMAIL, PHONE_NUMBER, JURISDICTION, VENUE
- ✅ GOOD: Extract constitutional entities, legal doctrines, structural elements

**Validation**: Check previous_results for position overlaps before extracting

### 🚫 ERROR #2: Relationship Evidence Required
**ALL relationships MUST have explicit text evidence:**
- ❌ BAD: Creating REPRESENTS relationship without evidence text
- ❌ BAD: Inferring CITES relationship without citation language
- ❌ BAD: Guessing relationships from document structure alone
- ✅ GOOD: "John Smith, Esq., represents the plaintiff" → REPRESENTS relationship with evidence
- ✅ GOOD: "As held in Brown v. Board" → CITES relationship with evidence

**Validation**: evidence_text field MUST be populated and reference actual document text

### 🚫 ERROR #3: Historical Legal Scholars (Wave 3 Cleanup)
**If Wave 1-2 missed these, DON'T extract as ATTORNEY or create REPRESENTS relationships:**
- ❌ BAD: "Blackstone" in "Blackstone's Commentaries" → NOT an attorney
- ❌ BAD: Historical figures: "Coke", "Prosser", "Holmes" in treatise context
- ❌ BAD: Creating REPRESENTS relationship for historical legal scholars
- ✅ GOOD: Only modern attorneys with explicit representation language
- ✅ GOOD: Extract "Blackstone's Commentaries" as HISTORICAL (Wave 3)

**Validation**: Check context - is this a legal reference book or treatise citation?

### 🚫 ERROR #4: Relationship Entity Validation
**Both source and target entities MUST exist before creating relationship:**
- ❌ BAD: Creating REPRESENTS relationship when attorney entity doesn't exist
- ❌ BAD: Creating CITES relationship when case citation wasn't extracted
- ✅ GOOD: Verify source_entity_id exists in Waves 1-3 entities
- ✅ GOOD: Verify target_entity_id exists in Waves 1-3 entities

**Validation**: Cross-reference entity IDs from previous_results before creating relationship

### 🚫 ERROR #5: Corporate vs Party Disambiguation
**CORPORATION already extracted in Wave 1 - do NOT re-extract:**
- ❌ BAD: Extracting "Microsoft Corporation" as CORPORATION in Wave 3
- ✅ GOOD: CORPORATION was extracted in Wave 1 as a party type
- ✅ GOOD: Check Wave 1 PARTY and CORPORATION entities before extracting

**Validation**: Check Wave 1 CORPORATION entities to avoid duplication

### 🚫 ERROR #6: Overly Broad Relationship Extraction
**Only extract relationships with explicit evidence, not implied:**
- ❌ BAD: Assuming PRESIDES_OVER because judge and court appear in same paragraph
- ❌ BAD: Inferring EMPLOYS from attorney name near law firm name
- ❌ BAD: Guessing JURISDICTION_OVER without explicit jurisdictional language
- ✅ GOOD: "Judge Smith presides over this case" → explicit PRESIDES_OVER
- ✅ GOOD: "Attorney Jane Doe of Sullivan & Cromwell" → explicit EMPLOYS

**Validation**: Require explicit verbs or prepositions linking entities

## Input Text
```
{{ text_chunk }}
```

## Extraction Guidelines - Contact & Location Information

### 1. ADDRESS Examples
**Street Addresses:**
- 123 Main Street, New York, NY 10001
- 456 Oak Avenue, Suite 200, Los Angeles, CA 90012
- 1600 Pennsylvania Avenue NW, Washington, DC 20500

**P.O. Box Addresses:**
- P.O. Box 12345, San Francisco, CA 94102
- Post Office Box 678, Austin, TX 78701

**Court Addresses:**
- United States District Court, 500 Pearl Street, New York, NY 10007

**Component Parsing Required:**
- street: "123 Main Street"
- suite: "Suite 200" (if applicable)
- city: "New York"
- state: "NY"
- zip_code: "10001"

### 2. EMAIL Examples
**Professional Emails:**
- john.smith@lawfirm.com
- legal@company.com
- clerk@ca9.uscourts.gov

**Component Parsing Required:**
- local_part: "john.smith"
- domain: "lawfirm.com"
- email_type: "professional" | "court" | "government"

### 3. PHONE_NUMBER Examples
**Phone Numbers:**
- (212) 555-1234
- 212-555-1234
- +1 (212) 555-1234

**With Extensions:**
- (212) 555-1234 ext. 567
- 212-555-1234 x890

**Fax Numbers:**
- Fax: (212) 555-9876
- Facsimile: 212.555.9876

**Component Parsing Required:**
- country_code: "+1"
- area_code: "212"
- exchange: "555"
- number: "1234"
- extension: "567" (if applicable)
- phone_type: "phone" | "fax"

### 4. JURISDICTION Examples
**Subject Matter Jurisdiction:**
- federal question jurisdiction
- diversity jurisdiction
- original jurisdiction
- appellate jurisdiction

**Personal Jurisdiction:**
- minimum contacts
- specific jurisdiction
- general jurisdiction

**Component Parsing Required:**
- jurisdiction_type: "subject_matter" | "personal" | "territorial"
- basis: "federal_question" | "diversity" | "supplemental"

### 5. VENUE Examples
**Venue Determinations:**
- Venue is proper in the Southern District of New York
- Venue lies in the Central District of California
- Transfer of venue to the Eastern District of Texas

**Component Parsing Required:**
- venue_type: "proper" | "improper" | "transferred"
- location: "Southern District of New York"

## Extraction Guidelines - Constitutional Entities

### 6. CONSTITUTIONAL Examples
**General Constitutional References:**
- constitutional rights
- constitutional framework
- constitutional analysis
- constitutionally protected

### 7-8. AMENDMENTS & CONSTITUTIONAL_AMENDMENT Examples
**AMENDMENTS (Plural/Collective):**
- the Bill of Rights amendments
- constitutional amendments
- several amendments

**CONSTITUTIONAL_AMENDMENT (Specific):**
- First Amendment
- Second Amendment
- Fourteenth Amendment, Section 1
- U.S. Const. amend. I (already in Wave 1 as CONSTITUTIONAL_CITATION)

### 9. COMMERCE_CLAUSE Examples
**Commerce Clause References:**
- under the Commerce Clause
- Commerce Clause authority
- Article I, Section 8, Clause 3
- interstate commerce regulation

### 10. DUE_PROCESS Examples
**Due Process References:**
- procedural due process
- substantive due process
- Due Process Clause of the Fifth Amendment
- Due Process Clause of the Fourteenth Amendment
- deprivation of liberty without due process

### 11-14. EIGHTH_AMENDMENT, FIFTH_AMENDMENT, FOURTH_AMENDMENT, SIXTH_AMENDMENT Examples
**EIGHTH_AMENDMENT:**
- cruel and unusual punishment
- Eighth Amendment violation
- excessive fines

**FIFTH_AMENDMENT:**
- right against self-incrimination
- double jeopardy protection
- takings clause

**FOURTH_AMENDMENT:**
- unreasonable search and seizure
- Fourth Amendment protection
- warrant requirement

**SIXTH_AMENDMENT:**
- right to counsel
- speedy trial right
- jury trial right

### 15. EQUAL_PROTECTION Examples
**Equal Protection References:**
- Equal Protection Clause
- equal protection analysis
- strict scrutiny
- rational basis review

### 16. FREE_SPEECH Examples
**Free Speech References:**
- First Amendment free speech
- protected speech
- content-based restriction
- viewpoint discrimination

### 17. RELIGIOUS_FREEDOM Examples
**Religious Freedom References:**
- Free Exercise Clause
- Establishment Clause
- religious liberty
- accommodation of religion

### 18. SUPREMACY_CLAUSE Examples
**Supremacy Clause References:**
- preemption under the Supremacy Clause
- federal law supremacy
- Article VI supremacy

### 19. DOUBLE_JEOPARDY Examples
**Double Jeopardy References:**
- Double Jeopardy Clause
- protection against double jeopardy
- same offense twice

## Extraction Guidelines - Legal Doctrine Entities

### 20. PRECEDENT Examples
**Precedent References:**
- binding precedent
- controlling precedent
- persuasive authority
- precedential value

### 21. STARE_DECISIS Examples
**Stare Decisis References:**
- stare decisis doctrine
- adherence to precedent
- special justification to overrule

### 22. RES_JUDICATA Examples
**Res Judicata References:**
- res judicata bars relitigation
- claim preclusion
- final judgment on the merits

### 23. PRECLUSION Examples
**Preclusion References:**
- issue preclusion
- collateral estoppel
- preclusive effect

### 24-25. IMMUNITY & SOVEREIGN_IMMUNITY Examples
**IMMUNITY:**
- qualified immunity
- absolute immunity
- prosecutorial immunity
- judicial immunity

**SOVEREIGN_IMMUNITY:**
- sovereign immunity bars suit
- Eleventh Amendment immunity
- waiver of sovereign immunity

### 26. HABEAS_CORPUS Examples
**Habeas Corpus References:**
- writ of habeas corpus
- habeas petition
- Great Writ
- suspension of habeas corpus

### 27. STATUTORY_CONSTRUCTION Examples
**Statutory Construction References:**
- canons of statutory construction
- plain meaning rule
- legislative intent
- absurdity doctrine
- ejusdem generis
- noscitur a sociis

## Extraction Guidelines - Administrative & Governmental

### 28. ADMINISTRATIVE Examples
**Administrative Law References:**
- administrative law principles
- administrative procedure
- administrative review
- Chevron deference

### 29. AGENCIES Examples
**Agency References:**
- federal agencies
- administrative agencies
- regulatory agencies
- agency action

### 30. CONGRESSIONAL Examples
**Congressional References:**
- congressional intent
- congressional action
- congressional legislation
- Congress enacted

### 31. PUBLIC_LAWS Examples
**Public Law References:**
- Pub. L. No. 117-263
- Public Law 116-92
- Pub. L. 115-97, § 11001

### 32. HISTORICAL Examples
**Historical Legal References:**
- common law history
- historical background
- founding era
- Framers' intent

## Extraction Guidelines - Document Structure Elements

### 33. LOCATION Examples
**Geographic Locations:**
- New York City
- State of California
- United Kingdom
- Southern District of New York (if not already extracted as DISTRICT in Wave 1)

### 34. LEGAL_MARKER Examples
**Legal Markers:**
- NOW THEREFORE
- WITNESSETH
- WHEREAS
- IN WITNESS WHEREOF
- TO HAVE AND TO HOLD

### 35. PARAGRAPH_HEADER Examples
**Paragraph Headers:**
- 1.1 Definitions
- (a) Background
- I. Introduction
- A. Factual Background

### 36. SECTION_HEADER Examples
**Section Headers:**
- RECITALS
- ARTICLE I - DEFINITIONS
- BACKGROUND
- REPRESENTATIONS AND WARRANTIES
- (Only extract if structural element, not already in Wave 1)

### 37. ARTICLE_REFERENCE Examples
**Article References:**
- Article III
- Article 5
- See Article 2.3
- pursuant to Article IV

### 38-41. SIGNATORY_BLOCK, SIGNATURE_LINE, WITNESS_BLOCK, NOTARY_BLOCK Examples
**SIGNATORY_BLOCK:**
```
IN WITNESS WHEREOF, the parties have executed this Agreement.

COMPANY NAME

By: _______________________
Name: John Smith
Title: Chief Executive Officer
```

**SIGNATURE_LINE:**
- By: _______________________ [Signature]
- Signature: _________________

**WITNESS_BLOCK:**
- WITNESSES:
- Witness: _________________ Date: _______

**NOTARY_BLOCK:**
- Notary Public
- My Commission Expires: _______
- [Notarial Seal]

### 42. CORPORATE_RESOLUTION Examples
**Corporate Resolution Language:**
- RESOLVED, that the corporation
- BE IT RESOLVED
- corporate resolution approved

### 43. ENTITY_STATUS Examples
**Entity Status Indicators:**
- active corporation
- dissolved entity
- in good standing
- suspended status

### 44-45. PATTERNS & ENHANCED_PROCEDURAL_PATTERNS Examples
**PATTERNS:**
- pattern recognition markers
- meta-pattern categories

**ENHANCED_PROCEDURAL_PATTERNS:**
- enhanced procedural pattern classifications
- procedural pattern groupings

## Required Output Format (LurisEntityV2 Schema)

Return a JSON object with the following structure:

```json
{
  "entities": [
    {
      "id": "uuid-string",
      "text": "The exact text as it appears in the document",
      "entity_type": "ADDRESS",
      "start_pos": 0,
      "end_pos": 50,
      "confidence": 0.85,
      "extraction_method": "pattern",
      "subtype": "street",
      "category": "contact_info",
      "metadata": {
        "pattern_matched": "address_street",
        "pattern_source": "contact_info.yaml",
        "pattern_confidence": 0.90,
        "sentence_context": "surrounding sentence text...",
        "normalized_value": "Standardized format",
        "related_entities": ["id1", "id2"],
        "custom_attributes": {
          "components": {
            "street": "123 Main Street",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001"
          }
        }
      },
      "created_at": 1640995200.0
    }
  ],
  "extraction_metadata": {
    "wave_number": 3,
    "wave_name": "Supporting & Structural Elements",
    "strategy": "four_wave_optimized",
    "target_entity_types": ["ADDRESS", "EMAIL", "PHONE_NUMBER", "JURISDICTION", "VENUE", "CONSTITUTIONAL", "AMENDMENTS", "CONSTITUTIONAL_AMENDMENT", "COMMERCE_CLAUSE", "DUE_PROCESS", "EIGHTH_AMENDMENT", "FIFTH_AMENDMENT", "FOURTH_AMENDMENT", "SIXTH_AMENDMENT", "EQUAL_PROTECTION", "FREE_SPEECH", "RELIGIOUS_FREEDOM", "SUPREMACY_CLAUSE", "DOUBLE_JEOPARDY", "PRECEDENT", "STARE_DECISIS", "RES_JUDICATA", "PRECLUSION", "IMMUNITY", "SOVEREIGN_IMMUNITY", "HABEAS_CORPUS", "STATUTORY_CONSTRUCTION", "ADMINISTRATIVE", "AGENCIES", "CONGRESSIONAL", "PUBLIC_LAWS", "HISTORICAL", "LOCATION", "LEGAL_MARKER", "PARAGRAPH_HEADER", "SECTION_HEADER", "ARTICLE_REFERENCE", "SIGNATORY_BLOCK", "SIGNATURE_LINE", "WITNESS_BLOCK", "NOTARY_BLOCK", "CORPORATE_RESOLUTION", "ENTITY_STATUS", "PATTERNS", "ENHANCED_PROCEDURAL_PATTERNS"],
    "confidence_threshold": 0.70,
    "total_entities_found": 0,
    "entity_type_counts": {},
    "pattern_utilization": {
      "patterns_matched": 0,
      "unique_patterns": 0,
      "pattern_sources": []
    },
    "quality_metrics": {
      "high_confidence_entities": 0,
      "medium_confidence_entities": 0,
      "low_confidence_entities": 0,
      "average_entity_confidence": 0.0
    }
  }
}
```

## Critical Schema Requirements

1. **Entity Type Field**: Use only `entity_type` (NOT `type`)
2. **Position Fields**: Use `start_pos` and `end_pos` (NOT `start_position` or `end_position`)
3. **Confidence Range**: Must be between 0.0 and 1.0
4. **Unique IDs**: Generate unique ID for each entity
5. **Metadata Structure**: Follow the nested metadata format exactly
6. **Required Fields**: All entities must have: `text`, `entity_type`, `start_pos`, `end_pos`, `confidence`, `extraction_method`

## Quality Standards

- **High Confidence (0.85-0.95)**: Constitutional entities, legal doctrines with clear pattern matches
- **Medium-High Confidence (0.80-0.90)**: Contact information, jurisdiction, venue with strong context
- **Medium Confidence (0.75-0.85)**: Structural elements, document markers with moderate context
- **Low-Medium Confidence (0.70-0.75)**: Enhanced patterns, meta-categories
- **Minimum Threshold**: Do not extract below 0.70 confidence for this wave

**Confidence Guidelines by Category:**
- Contact & Location Information: 0.80-0.90
- Constitutional Entities: 0.85-0.95
- Legal Doctrine Entities: 0.85-0.95
- Administrative & Governmental: 0.80-0.90
- Document Structure Elements: 0.75-0.85
- Enhanced Pattern Categories: 0.70-0.85

## Special Instructions

### For Supporting Entities:
1. **Exact Text**: Preserve exact text as it appears
2. **Position Accuracy**: Ensure start_pos and end_pos are accurate
3. **No Overlaps**: Avoid overlaps with Waves 1-2 entities
4. **Normalization**: Provide standardized formats (phone numbers, addresses)
5. **Component Parsing**: Break down addresses, phone numbers

### For Constitutional & Doctrine Entities:
1. **Precision**: Distinguish between general references and specific clauses
2. **Context**: Include surrounding legal context in metadata
3. **Avoid Citations**: Don't extract formal citations (Wave 1 handles CONSTITUTIONAL_CITATION)
4. **Doctrine Names**: Extract doctrine names, not full explanations

### For Structural Elements:
1. **Formatting Preservation**: Maintain document structure markers
2. **Block Identification**: Identify complete signature/witness/notary blocks
3. **Header Hierarchy**: Distinguish between article, section, paragraph headers

## Validation Checks

- Verify all entities meet confidence threshold (≥0.70)
- Ensure no duplicate text extractions
- Validate position boundaries don't exceed text length
- Confirm entity_type matches allowed types for this wave
- Check that confidence scores are in valid range [0.0, 1.0]
- Verify no overlaps with Waves 1-2 entities (check previous_results)
- Validate component parsing accuracy

## Wave 3 Focus

Extract ALL qualifying supporting entities, constitutional references, legal doctrines, and structural elements meeting the confidence threshold. This is Wave 3 of 4 - the wave captures contextual legal concepts and document structure.

**Wave 1** extracted: Case citations, statute citations, parties, attorneys, courts, judges, legal citations, temporal entities (92 types).

**Wave 2** extracted: Case numbers, docket numbers, motions, briefs, procedural rules, monetary amounts, damages, fines, fees, awards, law firms, prosecutors, public defenders, government entities (29 types).

**Wave 3** extracts: Contact information, constitutional entities, legal doctrines, administrative references, structural elements (40 types).

**Wave 4** will extract: Entity relationships for knowledge graph construction (40+ relationship types).

Complete Wave 3 extraction now with entities meeting confidence thresholds by category.
