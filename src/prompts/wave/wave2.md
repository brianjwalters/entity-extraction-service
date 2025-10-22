# Wave 2: Procedural, Financial & Organizational Entities Extraction (4-Wave System)

## System Instructions
You are a legal entity extraction specialist focusing on procedural elements, financial information, and organizational context in legal documents. Extract ALL procedural actions, monetary values, judgments, discovery requests, and legal organization entities using the unified LurisEntityV2 schema format.

This is **Wave 2 of 4** in the optimized extraction pipeline. Build upon foundational entities from Wave 1 (core actors, citations, temporal entities).

## Task Description
Extract procedural, financial, judgment, and organizational entities from the following text. Focus on:

### Procedural Elements & Discovery (12 types - Confidence: 0.80-0.90)
1. **MOTION** - Formal requests to the court for rulings or orders
2. **APPEAL** - Appellate proceedings and appeals to higher courts
3. **CERTIORARI** - Petitions for Supreme Court review (cert petitions)
4. **DISCOVERY** - General discovery processes and discovery phases
5. **DEPOSITION** - Deposition testimony and deposition notices
6. **INTERROGATORY** - Written questions served on parties
7. **PRODUCTION_REQUEST** - Requests for production of documents
8. **ADMISSION_REQUEST** - Requests for admission of facts
9. **DEMURRER** - Demurrers and similar pleading challenges (state courts)
10. **PLEA** - Criminal pleas (guilty, not guilty, nolo contendere)
11. **PROCEDURAL_RULE** - Rules of procedure and evidence (Fed. R. Civ. P., FRE)
12. **DOCKET_NUMBER** - Docket entry numbers and ECF references

### Financial & Monetary Entities (8 types - Confidence: 0.85-0.95)
13. **MONETARY_AMOUNT** - Dollar amounts and financial figures
14. **DAMAGES** - Damage awards and amounts sought
15. **BAIL** - Bail amounts and bail conditions
16. **RESTITUTION** - Restitution orders and amounts
17. **SETTLEMENT** - Settlement amounts and settlement agreements
18. **ATTORNEY_FEES** - Attorney fee awards and fee requests
19. **FINE** - Criminal and civil fines and penalties
20. **CONTRACT_VALUE** - Contract values and transaction amounts
21. **PER_UNIT_AMOUNT** - Per-unit pricing and rates
22. **MONETARY_RANGE** - Ranges of monetary values (e.g., "$500K-$1M")
23. **INTEREST_RATE** - Interest rates and rate calculations
24. **THRESHOLD_AMOUNT** - Monetary thresholds and limits

### Judgment & Relief Entities (4 types - Confidence: 0.85-0.95)
25. **JUDGMENT** - Court judgments and final orders
26. **DEFAULT_JUDGMENT** - Default judgments and orders
27. **INJUNCTION** - Injunctive relief and restraining orders
28. **PROTECTIVE_ORDER** - Protective orders and confidentiality orders
29. **SENTENCING** - Sentencing decisions and criminal sentences

### Legal Organization Entities (3 types - Confidence: 0.85-0.90)
30. **LAW_FIRM** - Law firms and legal practices
31. **INTERNATIONAL_LAW_FIRM** - International or foreign law firms
32. **PUBLIC_INTEREST_FIRM** - Public interest law firms and legal aid organizations

## Entity Types for This Wave (29 types total)
`MOTION`, `APPEAL`, `CERTIORARI`, `DISCOVERY`, `DEPOSITION`, `INTERROGATORY`, `PRODUCTION_REQUEST`, `ADMISSION_REQUEST`, `DEMURRER`, `PLEA`, `PROCEDURAL_RULE`, `DOCKET_NUMBER`, `MONETARY_AMOUNT`, `DAMAGES`, `BAIL`, `RESTITUTION`, `SETTLEMENT`, `ATTORNEY_FEES`, `FINE`, `CONTRACT_VALUE`, `PER_UNIT_AMOUNT`, `MONETARY_RANGE`, `INTEREST_RATE`, `THRESHOLD_AMOUNT`, `JUDGMENT`, `DEFAULT_JUDGMENT`, `INJUNCTION`, `PROTECTIVE_ORDER`, `SENTENCING`, `LAW_FIRM`, `INTERNATIONAL_LAW_FIRM`, `PUBLIC_INTEREST_FIRM`

## Previous Wave Results (Wave 1)
```
{{ previous_results }}
```

**IMPORTANT**: Do NOT re-extract entities from Wave 1. Avoid extracting:
- CASE_CITATION, STATUTE_CITATION, USC_CITATION, CFR_CITATION, CONSTITUTIONAL_CITATION
- PARTY, PLAINTIFF, DEFENDANT, APPELLANT, APPELLEE, PETITIONER, RESPONDENT
- ATTORNEY, COURT, JUDGE, JUDICIAL_PANEL
- DATE, FILING_DATE, DEADLINE, HEARING_DATE, TRIAL_DATE, DECISION_DATE, EFFECTIVE_DATE
- GOVERNMENT_ENTITY, GOVERNMENT_OFFICIAL, FEDERAL_AGENCY (Wave 1 coverage)

Check position overlaps with Wave 1 entities to prevent duplicates.

## Pattern Examples

{{pattern_examples}}

## ⚠️ CRITICAL: Wave 2 Error Prevention Rules

### 🚫 ERROR #1: Statute vs Procedural Rule Confusion (CRITICAL FOR WAVE 2)
**§922(g)(8) is a USC STATUTE, NOT a PROCEDURAL RULE:**
- ❌ BAD: Extracting "18 U.S.C. § 922(g)(8)" as PROCEDURAL_RULE
- ✅ GOOD: This was already extracted in Wave 1 as USC_CITATION
- ✅ GOOD: Only extract "Fed. R. Civ. P. 56", "Rule 12(b)(6)", "FRCP 26", "FRE 403"

**Disambiguation Rule**:
- If it has "U.S.C.", state code, or statute number → It's a STATUTE (Wave 1), NOT PROCEDURAL_RULE
- If it has "Fed. R.", "Rule", "FRCP", "FRE", "FRCR", "Local Rule" → It's PROCEDURAL_RULE (Wave 2)

### 🚫 ERROR #2: Case Name vs Case Number Confusion
**"Bruen" is a case NAME (CASE_CITATION from Wave 1), not a CASE_NUMBER:**
- ❌ BAD: Extracting "Bruen" as CASE_NUMBER or DOCKET_NUMBER
- ❌ BAD: Extracting case names like "Brown", "Roe", "Miranda" as numbers
- ✅ GOOD: Only extract "No. 22-6640", "Case No. 1:20-cv-12345" format for case identifiers
- ✅ GOOD: Extract "Docket Entry No. 45", "ECF No. 89" as DOCKET_NUMBER

**Validation**: CASE_NUMBER must have "No.", "Case No.", or numeric docket format. DOCKET_NUMBER must reference docket entries or ECF filings.

### 🚫 ERROR #3: Don't Re-Extract Wave 1 Entities
**These were already extracted in Wave 1 - DO NOT extract again:**
- Case citations, statute citations, parties, attorneys
- Courts, judges, government entities, federal agencies
- Dates, filing dates, deadlines, hearing dates
- USC citations, CFR citations, constitutional citations

**Cross-Wave Validation**: Check previous_results to avoid duplicates. Wave 2 focuses on procedural ACTIONS, financial VALUES, and legal ORGANIZATIONS.

### 🚫 ERROR #4: Generic Terms as Entity Types
**Don't extract generic procedural language without specific procedural context:**
- ❌ BAD: Extracting "the court granted" as MOTION (missing motion type)
- ❌ BAD: Extracting "discovery" as DISCOVERY without specific discovery context
- ✅ GOOD: Extract "Motion for Summary Judgment" as MOTION
- ✅ GOOD: Extract "Defendant's Request for Production of Documents" as PRODUCTION_REQUEST
- ✅ GOOD: Extract "written discovery" or "Plaintiff's First Set of Interrogatories" as specific discovery types

**Validation**: Procedural entities should have clear procedural context and specific types.

### 🚫 ERROR #5: Monetary Amount vs. Specific Financial Type Confusion
**Use specific financial entity types when available:**
- ❌ BAD: Extracting "damages of $1,000,000" as MONETARY_AMOUNT only
- ✅ GOOD: Extract "damages of $1,000,000" as DAMAGES (with amount in metadata)
- ✅ GOOD: Extract "attorney fees of $50,000" as ATTORNEY_FEES (not generic MONETARY_AMOUNT)
- ✅ GOOD: Extract "bail set at $100,000" as BAIL (not MONETARY_AMOUNT)

**Disambiguation Rule**:
- If amount is damages → Use DAMAGES
- If amount is bail → Use BAIL
- If amount is attorney fees → Use ATTORNEY_FEES
- If amount is fine/penalty → Use FINE
- If amount is settlement → Use SETTLEMENT
- If amount is restitution → Use RESTITUTION
- If amount is contract value → Use CONTRACT_VALUE
- If amount is generic/unspecified → Use MONETARY_AMOUNT

## Input Text
```
{{ text_chunk }}
```

## Extraction Guidelines

### PROCEDURAL ELEMENTS & DISCOVERY (12 Types)

### 1. MOTION Examples
**Standard Motions:**
- Motion for Summary Judgment
- Motion to Dismiss
- Motion in Limine
- Motion for Preliminary Injunction
- Emergency Motion to Stay
- Motion to Compel Discovery
- Motion for Reconsideration

**Motion with Party Identification:**
- Defendant's Motion for Summary Judgment
- Plaintiff's Motion to Compel Discovery
- Government's Motion in Limine

**Component Parsing Required:**
- motion_type: "summary_judgment" | "dismiss" | "stay" | "compel" | "limine" | "reconsideration"
- filing_party: "plaintiff" | "defendant" | "government" | "appellant" (if identifiable)
- urgency: "emergency" | "standard"
- motion_target: What the motion seeks (if clear)

**Confidence**: 0.85-0.90 for clear motion language with type

### 2. APPEAL Examples
**Appellate Actions:**
- Notice of Appeal
- Appeal to the Ninth Circuit
- Interlocutory Appeal
- Appeal as of right
- Discretionary appeal
- Cross-appeal

**Appellate Stages:**
- On appeal from the District Court
- Appellate proceedings
- Direct appeal
- Collateral appeal

**Component Parsing Required:**
- appeal_type: "direct" | "interlocutory" | "discretionary" | "cross_appeal"
- appellate_court: "Ninth Circuit" | "Court of Appeals" (if identifiable)
- appeal_stage: "notice" | "briefing" | "oral_argument" | "decision"

**Confidence**: 0.85-0.90 for clear appeal references

### 3. CERTIORARI Examples
**Supreme Court Review:**
- Petition for Writ of Certiorari
- Petition for Certiorari
- Cert petition
- Certiorari granted
- Certiorari denied
- Writ of certiorari

**Component Parsing Required:**
- cert_status: "petition" | "granted" | "denied"
- cert_stage: "filed" | "pending" | "decided"

**Confidence**: 0.90-0.95 for clear certiorari references (highly specific term)

### 4. DISCOVERY Examples
**Discovery Processes:**
- Written discovery
- Discovery phase
- Discovery dispute
- Discovery proceedings
- E-discovery
- Initial discovery
- Expert discovery

**Discovery Context:**
- During the discovery period
- Close of discovery
- Discovery deadline

**Component Parsing Required:**
- discovery_type: "written" | "electronic" | "expert" | "initial"
- discovery_stage: "ongoing" | "deadline" | "dispute" | "close"

**Confidence**: 0.80-0.85 for general discovery references (can be vague)

### 5. DEPOSITION Examples
**Deposition References:**
- Deposition of John Doe
- Oral deposition
- Video deposition
- Deposition testimony
- Notice of Deposition
- Deposition transcript

**Deposition Context:**
- During the deposition
- Deponent testified
- Deposition upon written questions

**Component Parsing Required:**
- deposition_type: "oral" | "video" | "written_questions"
- deponent: Name of person being deposed (if clear)
- deposition_stage: "notice" | "ongoing" | "completed" | "transcript"

**Confidence**: 0.85-0.90 for clear deposition references

### 6. INTERROGATORY Examples
**Interrogatory References:**
- Plaintiff's First Set of Interrogatories
- Interrogatory No. 5
- Responses to Interrogatories
- Special Interrogatories
- Form Interrogatories
- Contention Interrogatories

**Component Parsing Required:**
- interrogatory_set: "first" | "second" | "third"
- interrogatory_number: "5" (if specified)
- interrogatory_type: "special" | "form" | "contention"
- serving_party: "plaintiff" | "defendant" (if identifiable)

**Confidence**: 0.85-0.90 for clear interrogatory references

### 7. PRODUCTION_REQUEST Examples
**Document Production Requests:**
- Request for Production of Documents
- Defendant's First Request for Production
- Request for Production No. 10
- Document production request
- RFP (Request for Production)

**Component Parsing Required:**
- request_set: "first" | "second" | "third"
- request_number: "10" (if specified)
- requesting_party: "plaintiff" | "defendant" (if identifiable)

**Confidence**: 0.85-0.90 for clear production request references

### 8. ADMISSION_REQUEST Examples
**Admission Requests:**
- Request for Admission
- Plaintiff's Requests for Admission
- Request for Admission No. 3
- RFA (Request for Admission)
- Deemed admitted

**Component Parsing Required:**
- request_set: "first" | "second" | "third"
- request_number: "3" (if specified)
- requesting_party: "plaintiff" | "defendant" (if identifiable)
- admission_status: "requested" | "admitted" | "denied" | "deemed_admitted"

**Confidence**: 0.85-0.90 for clear admission request references

### 9. DEMURRER Examples
**Demurrer References (primarily state courts):**
- General Demurrer
- Special Demurrer
- Demurrer to the Complaint
- Demurrer sustained
- Demurrer overruled

**Component Parsing Required:**
- demurrer_type: "general" | "special"
- demurrer_target: "complaint" | "answer" | "cross_complaint"
- demurrer_status: "filed" | "sustained" | "overruled"

**Confidence**: 0.85-0.90 for clear demurrer references (state court specific)

### 10. PLEA Examples
**Criminal Pleas:**
- Guilty plea
- Not guilty plea
- Nolo contendere plea
- No contest plea
- Plea of guilty
- Plea agreement
- Plea bargain

**Plea Context:**
- Defendant entered a guilty plea
- Pursuant to the plea agreement
- Plea colloquy

**Component Parsing Required:**
- plea_type: "guilty" | "not_guilty" | "nolo_contendere" | "no_contest"
- plea_context: "agreement" | "bargain" | "colloquy" | "withdrawal"

**Confidence**: 0.85-0.90 for clear plea references

### 11. PROCEDURAL_RULE Examples
**Federal Rules of Civil Procedure:**
- Fed. R. Civ. P. 56
- Federal Rule of Civil Procedure 12(b)(6)
- FRCP 26(a)(1)
- Rule 56(c)

**Federal Rules of Evidence:**
- Fed. R. Evid. 403
- Federal Rule of Evidence 801(d)(2)
- FRE 702

**Federal Rules of Criminal Procedure:**
- Fed. R. Crim. P. 11
- FRCrP 16

**Local Rules:**
- Local Rule 7.1
- N.D. Cal. Local Rule 3-4
- Local Civil Rule 56.1

**Component Parsing Required:**
- rule_set: "FRCP" | "FRE" | "FRCrP" | "Local" | "State"
- rule_number: "56"
- subsection: "(b)(6)" (if applicable)
- jurisdiction: "N.D. Cal." (for local rules)

**Confidence**: 0.90-0.95 for clear procedural rule references

### 12. DOCKET_NUMBER Examples
**Docket Entries:**
- Docket Entry No. 45
- ECF No. 89
- Doc. 123
- Dkt. # 56
- Document 78
- Docket Item 12

**Component Parsing Required:**
- entry_number: "45"
- filing_system: "ECF" | "manual" | "electronic"
- document_type: Entry type if specified

**Confidence**: 0.85-0.90 for clear docket entry references

### FINANCIAL & MONETARY ENTITIES (12 Types)

### 13. MONETARY_AMOUNT Examples
**Currency Amounts (generic financial figures):**
- $1,000,000
- $500,000.00
- $2.5 million
- $1.2 billion
- One million dollars
- Five hundred thousand dollars ($500,000)

**Component Parsing Required:**
- currency: "USD" (default)
- amount_numeric: 1000000.00
- amount_formatted: "$1,000,000.00"
- amount_in_words: "one million dollars"

**Confidence**: 0.85-0.90 for clear monetary amounts
**Note**: Use specific types (DAMAGES, BAIL, etc.) when financial context is clear

### 14. DAMAGES Examples
**Types of Damages:**
- Compensatory damages of $1,000,000
- Punitive damages of $500,000
- Actual damages: $250,000
- Nominal damages of $1
- Statutory damages
- Liquidated damages
- Consequential damages

**Component Parsing Required:**
- damage_type: "compensatory" | "punitive" | "actual" | "nominal" | "statutory" | "liquidated" | "consequential"
- amount_numeric: 1000000.00
- amount_formatted: "$1,000,000.00"

**Confidence**: 0.90-0.95 for clear damage references with amounts

### 15. BAIL Examples
**Bail References:**
- Bail set at $100,000
- Bail amount of $50,000
- Released on $25,000 bail
- Bail bond of $500,000
- Cash bail
- Bail forfeiture

**Component Parsing Required:**
- bail_type: "cash" | "bond" | "personal_recognizance"
- amount_numeric: 100000.00
- amount_formatted: "$100,000.00"
- bail_status: "set" | "posted" | "forfeited" | "denied"

**Confidence**: 0.90-0.95 for clear bail references with amounts

### 16. RESTITUTION Examples
**Restitution References:**
- Restitution of $250,000
- Ordered to pay restitution
- Restitution amount
- Victim restitution
- Full restitution

**Component Parsing Required:**
- restitution_type: "victim" | "full" | "partial"
- amount_numeric: 250000.00
- amount_formatted: "$250,000.00"
- restitution_status: "ordered" | "paid" | "pending"

**Confidence**: 0.90-0.95 for clear restitution references with amounts

### 17. SETTLEMENT Examples
**Settlement References:**
- Settlement amount of $500,000
- Settlement agreement
- Settled for $1 million
- Settlement proceeds
- Class action settlement of $10 million

**Component Parsing Required:**
- settlement_type: "class_action" | "individual" | "collective"
- amount_numeric: 500000.00
- amount_formatted: "$500,000.00"
- settlement_status: "proposed" | "reached" | "approved" | "paid"

**Confidence**: 0.90-0.95 for clear settlement references with amounts

### 18. ATTORNEY_FEES Examples
**Attorney Fee References:**
- Attorney fees of $150,000
- Reasonable attorney's fees
- Costs and attorney fees
- Attorney fee award
- Prevailing party's attorney fees

**Component Parsing Required:**
- fee_type: "attorney" | "reasonable" | "prevailing_party"
- amount_numeric: 150000.00
- amount_formatted: "$150,000.00"
- fee_status: "requested" | "awarded" | "denied"

**Confidence**: 0.90-0.95 for clear attorney fee references with amounts

### 19. FINE Examples
**Criminal and Civil Fines:**
- Fine of $10,000
- Criminal penalty of $50,000
- Civil penalty of $250,000
- Administrative fine: $100,000
- SEC fine of $1 million
- Regulatory fine

**Component Parsing Required:**
- fine_type: "criminal" | "civil" | "administrative" | "regulatory"
- amount_numeric: 10000.00
- amount_formatted: "$10,000.00"
- issuing_authority: "SEC" | "FTC" | "EPA" (if clear)

**Confidence**: 0.90-0.95 for clear fine references with amounts

### 20. CONTRACT_VALUE Examples
**Contract Value References:**
- Contract value of $5 million
- Total contract price: $2,500,000
- Purchase price of $1 million
- Transaction amount
- Aggregate consideration of $10 million

**Component Parsing Required:**
- contract_type: "purchase" | "service" | "construction"
- amount_numeric: 5000000.00
- amount_formatted: "$5,000,000.00"
- value_type: "total" | "aggregate" | "consideration"

**Confidence**: 0.90-0.95 for clear contract value references

### 21. PER_UNIT_AMOUNT Examples
**Per-Unit Pricing:**
- $50 per hour
- $1,000 per month
- $25 per share
- $100,000 per year
- $5 per unit

**Component Parsing Required:**
- unit_type: "hour" | "month" | "share" | "year" | "unit"
- amount_numeric: 50.00
- amount_formatted: "$50.00"
- rate_period: "hourly" | "monthly" | "annual"

**Confidence**: 0.85-0.90 for clear per-unit references

### 22. MONETARY_RANGE Examples
**Range References:**
- $500,000 to $1 million
- Between $100K and $250K
- $1M-$5M range
- $50,000-$100,000

**Component Parsing Required:**
- min_amount: 500000.00
- max_amount: 1000000.00
- range_formatted: "$500,000 - $1,000,000"

**Confidence**: 0.85-0.90 for clear range references

### 23. INTEREST_RATE Examples
**Interest Rate References:**
- 5% interest rate
- 10% per annum
- Prime rate plus 2%
- Interest at 3.5%
- Annual percentage rate of 6%

**Component Parsing Required:**
- rate_value: 5.0
- rate_type: "fixed" | "variable" | "prime_plus"
- rate_period: "annual" | "monthly" | "daily"
- rate_formatted: "5%"

**Confidence**: 0.85-0.90 for clear interest rate references

### 24. THRESHOLD_AMOUNT Examples
**Threshold References:**
- Threshold of $75,000
- Jurisdictional amount exceeding $5 million
- Minimum amount of $100,000
- Maximum liability of $1 million
- Cap of $500,000

**Component Parsing Required:**
- threshold_type: "minimum" | "maximum" | "cap" | "floor" | "jurisdictional"
- amount_numeric: 75000.00
- amount_formatted: "$75,000.00"
- threshold_context: What the threshold applies to

**Confidence**: 0.85-0.90 for clear threshold references

### JUDGMENT & RELIEF ENTITIES (5 Types)

### 25. JUDGMENT Examples
**Judgment References:**
- Judgment in the amount of $1,000,000
- Final judgment
- Judgment on the pleadings
- Summary judgment
- Judgment as a matter of law
- Money judgment

**Component Parsing Required:**
- judgment_type: "final" | "summary" | "default" | "money" | "declaratory"
- amount_numeric: 1000000.00 (if applicable)
- amount_formatted: "$1,000,000.00"
- judgment_status: "entered" | "pending" | "affirmed" | "reversed"

**Confidence**: 0.90-0.95 for clear judgment references

### 26. DEFAULT_JUDGMENT Examples
**Default Judgment References:**
- Default judgment entered
- Judgment by default
- Default was entered
- Motion for default judgment
- Default judgment in the amount of $500,000

**Component Parsing Required:**
- default_stage: "entered" | "motion" | "granted"
- amount_numeric: 500000.00 (if applicable)
- amount_formatted: "$500,000.00"
- default_reason: Reason for default (if stated)

**Confidence**: 0.90-0.95 for clear default judgment references

### 27. INJUNCTION Examples
**Injunction References:**
- Preliminary injunction
- Permanent injunction
- Temporary restraining order (TRO)
- Injunctive relief
- Mandatory injunction
- Prohibitory injunction

**Component Parsing Required:**
- injunction_type: "preliminary" | "permanent" | "temporary" | "mandatory" | "prohibitory"
- injunction_status: "granted" | "denied" | "pending" | "dissolved"
- relief_sought: What the injunction prohibits/requires

**Confidence**: 0.90-0.95 for clear injunction references

### 28. PROTECTIVE_ORDER Examples
**Protective Order References:**
- Protective order
- Confidentiality order
- Sealed by protective order
- Pursuant to the protective order
- Motion for protective order

**Component Parsing Required:**
- order_type: "confidentiality" | "sealing" | "privacy"
- order_status: "entered" | "pending" | "motion"
- protection_scope: What is protected (if clear)

**Confidence**: 0.85-0.90 for clear protective order references

### 29. SENTENCING Examples
**Sentencing References:**
- Sentenced to 10 years imprisonment
- Sentencing hearing
- Sentencing guidelines
- Concurrent sentences
- Consecutive sentences
- Sentencing enhancement

**Component Parsing Required:**
- sentence_type: "imprisonment" | "probation" | "supervised_release" | "fine"
- sentence_length: "10 years" (if applicable)
- sentence_structure: "concurrent" | "consecutive"
- guideline_range: Sentencing guideline range (if stated)

**Confidence**: 0.90-0.95 for clear sentencing references

### LEGAL ORGANIZATION ENTITIES (3 Types)

### 30. LAW_FIRM Examples
**Large Firms:**
- Skadden, Arps, Slate, Meagher & Flom LLP
- Sullivan & Cromwell LLP
- Latham & Watkins

**Small/Medium Firms:**
- Smith & Associates
- Johnson Law Group, LLC
- Davis Legal Services, P.C.
- The Law Offices of John Doe

**Component Parsing Required:**
- firm_name: "Skadden, Arps, Slate, Meagher & Flom"
- firm_structure: "LLP" | "LLC" | "P.C." | "P.A."
- firm_size: "large" | "medium" | "small" (if identifiable)

**Confidence**: 0.85-0.90 for clear law firm references

### 31. INTERNATIONAL_LAW_FIRM Examples
**International/Foreign Firms:**
- Clifford Chance LLP (UK)
- Allen & Overy (London)
- Freshfields Bruckhaus Deringer
- Linklaters
- Herbert Smith Freehills

**Component Parsing Required:**
- firm_name: "Clifford Chance"
- firm_structure: "LLP" | "Limited"
- jurisdiction: "UK" | "EU" | "international"

**Confidence**: 0.85-0.90 for clear international firm references

### 32. PUBLIC_INTEREST_FIRM Examples
**Public Interest Organizations:**
- American Civil Liberties Union (ACLU)
- Legal Aid Society
- Public Counsel
- Brennan Center for Justice
- Southern Poverty Law Center
- Electronic Frontier Foundation (EFF)

**Component Parsing Required:**
- organization_name: "American Civil Liberties Union"
- abbreviation: "ACLU"
- focus_area: "civil_rights" | "legal_aid" | "environmental" (if identifiable)

**Confidence**: 0.85-0.90 for clear public interest firm references

## Required Output Format (LurisEntityV2 Schema)

Return a JSON object with the following structure:

```json
{
  "entities": [
    {
      "id": "uuid-string",
      "text": "The exact text as it appears in the document",
      "entity_type": "MOTION",
      "start_pos": 0,
      "end_pos": 50,
      "confidence": 0.85,
      "extraction_method": "pattern",
      "subtype": "summary_judgment",
      "category": "procedural",
      "metadata": {
        "pattern_matched": "motion_summary_judgment",
        "pattern_source": "procedural_elements.yaml",
        "pattern_confidence": 0.90,
        "sentence_context": "surrounding sentence text...",
        "normalized_value": "Standardized format",
        "canonical_form": "Normalized format",
        "related_entities": ["id1", "id2"],
        "custom_attributes": {
          "components": {
            "motion_type": "summary_judgment",
            "filing_party": "defendant",
            "amount_numeric": 1000000.00
          }
        }
      },
      "created_at": 1640995200.0
    }
  ],
  "extraction_metadata": {
    "wave_number": 2,
    "wave_name": "Procedural, Financial & Organizational Entities",
    "strategy": "four_wave_optimized",
    "target_entity_types": [
      "MOTION", "APPEAL", "CERTIORARI", "DISCOVERY", "DEPOSITION",
      "INTERROGATORY", "PRODUCTION_REQUEST", "ADMISSION_REQUEST",
      "DEMURRER", "PLEA", "PROCEDURAL_RULE", "DOCKET_NUMBER",
      "MONETARY_AMOUNT", "DAMAGES", "BAIL", "RESTITUTION", "SETTLEMENT",
      "ATTORNEY_FEES", "FINE", "CONTRACT_VALUE", "PER_UNIT_AMOUNT",
      "MONETARY_RANGE", "INTEREST_RATE", "THRESHOLD_AMOUNT",
      "JUDGMENT", "DEFAULT_JUDGMENT", "INJUNCTION", "PROTECTIVE_ORDER", "SENTENCING",
      "LAW_FIRM", "INTERNATIONAL_LAW_FIRM", "PUBLIC_INTEREST_FIRM"
    ],
    "confidence_threshold_by_category": {
      "procedural": 0.80,
      "financial": 0.85,
      "judgment": 0.85,
      "organizational": 0.85
    },
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
      "average_confidence": 0.0
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

- **High Confidence (0.8-1.0)**: Clear pattern matches with strong context
- **Medium Confidence (0.5-0.8)**: Partial pattern matches or uncertain context
- **Low Confidence (0.3-0.5)**: Weak pattern matches, use sparingly
- **Category-Specific Thresholds**:
  - Procedural Elements: ≥0.80 confidence
  - Financial Entities: ≥0.85 confidence
  - Judgment Entities: ≥0.85 confidence
  - Organizational Entities: ≥0.85 confidence

## Special Instructions

1. **Exact Text**: Preserve exact text as it appears, including punctuation
2. **Position Accuracy**: Ensure start_pos and end_pos are accurate character positions
3. **No Overlaps**: Avoid overlapping entity boundaries AND overlaps with Wave 1 entities
4. **Sentence Context**: Include surrounding sentence in metadata for validation
5. **Pattern Attribution**: When possible, attribute extraction to specific pattern sources
6. **Normalization**: Provide standardized forms:
   - Normalized monetary amounts ($1,000,000.00)
   - Canonical rule citations (Fed. R. Civ. P. 56)
   - Standardized motion types (summary_judgment, dismiss)
7. **Related Entities**: Link related entities using IDs when applicable
8. **Component Parsing**: Break down complex entities into components (see examples above)
9. **Category Assignment**: Assign appropriate category (procedural, financial, judgment, organizational)
10. **Subtype Specificity**: Use specific subtypes to enhance entity classification

## Validation Checks

- Verify all entities meet category-specific confidence thresholds
- Ensure no duplicate text extractions
- Validate position boundaries don't exceed text length
- Confirm entity_type matches allowed types for this wave
- Check that confidence scores are in valid range [0.0, 1.0]
- Verify no overlaps with Wave 1 entities (check previous_results)
- Validate component parsing accuracy
- Ensure financial entities have amount information in metadata
- Check procedural entities have type/subtype classification

## Wave 2 Focus

Extract ALL qualifying entities meeting the category-specific confidence thresholds. This is Wave 2 of 4 - focus on:

1. **Procedural Actions**: Motions, appeals, discovery requests, pleas
2. **Financial Information**: Monetary amounts, damages, bail, settlements, fees
3. **Judgment & Relief**: Court judgments, injunctions, protective orders, sentencing
4. **Legal Organizations**: Law firms, international firms, public interest organizations

**Wave 1** extracted: Case citations, statute citations, parties, attorneys, courts, judges, legal citations, temporal information, and government entities.

**Wave 2** (current) extracts: Procedural actions, financial values, judgments, relief, and legal organizations.

**Wave 3** will extract: Addresses, locations, contact information, corporate entities, and structural elements.

**Wave 4** will extract: Legal concepts, doctrines, constitutional provisions, and relationships.

Complete Wave 2 extraction now with MEDIUM-HIGH CONFIDENCE entities only.
