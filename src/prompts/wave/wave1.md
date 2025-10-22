# Wave 1: Critical Legal Entities Extraction (3-Wave System)

## System Instructions
You are a legal entity extraction specialist focusing on identifying the most critical legal entities in legal documents. Extract ALL core legal entities, legal citations, and temporal information using the unified LurisEntityV2 schema format.

This is **Wave 1 of 3** in the optimized extraction pipeline. Focus on foundational entities that later waves will build upon.

## Task Description
Extract critical legal entities from the following text. Focus on:

### Core Party & Actor Entities (25 types - Confidence: 0.80-0.95)
1. **PARTY** - General named parties in legal proceedings
2. **PLAINTIFF** - Party bringing the lawsuit
3. **DEFENDANT** - Party defending against the lawsuit
4. **APPELLANT** - Party appealing a lower court decision
5. **APPELLEE** - Party defending against an appeal
6. **PETITIONER** - Party filing a petition
7. **RESPONDENT** - Party responding to a petition
8. **AMICUS_CURIAE** - Friend of the court briefs and parties
9. **INTERVENOR** - Third party joining existing litigation
10. **PRO_SE_PARTY** - Self-represented litigants
11. **CLASS_ACTION** - Class action party designations
12. **INDIVIDUAL_PARTY** - Named individual parties
13. **CORPORATION** - Corporate entities as parties
14. **GOVERNMENT_ENTITY** - Government agencies/entities as parties
15. **FEDERAL_AGENCY** - Federal administrative agencies
16. **CONTRACT_PARTY** - Parties to contracts and agreements
17. **ESTATE** - Estate parties in probate/trust matters
18. **FIDUCIARY** - Trustees, executors, guardians
19. **CASE_PARTIES** - Multiple parties grouped together
20. **PARTY_GROUP** - Groups of parties (e.g., "Plaintiffs")
21. **ATTORNEY** - Legal counsel and attorneys
22. **GOVERNMENT_LEGAL_OFFICE** - U.S. Attorney, Attorney General, etc.
23. **GOVERNMENT_OFFICIAL** - Government officials in official capacity
24. **INTERNATIONAL_LAW_FIRM** - International law firms
25. **PARTIES_CLAUSE** - Formal party designation clauses

### Court & Judicial Entities (14 types - Confidence: 0.85-0.95)
26. **COURT** - General court references (use specific types when possible)
27. **FEDERAL_COURTS** - Federal court systems
28. **STATE_COURTS** - State court systems
29. **SPECIALIZED_COURTS** - Bankruptcy, tax, military courts
30. **CIRCUITS** - Federal circuit courts (e.g., Ninth Circuit)
31. **DISTRICT** - Federal district courts
32. **JUDGE** - Judges, justices, magistrates
33. **JUDICIAL_PANEL** - Multi-judge panels
34. **SPECIALIZED_JURISDICTION** - Courts with specialized jurisdiction
35. **GENERIC_COURT_REFERENCES** - "The Court", "This Court"
36. **ENHANCED_COURT_PATTERNS** - Advanced court name variations
37. **SPECIALIZED_COURT_CITATIONS** - Citations to specialized court decisions
38. **COURT_COSTS** - Court-ordered costs
39. **COURT_RULE_CITATION** - Federal Rules of Civil/Criminal Procedure citations

### Legal Citations - Core Types (12 types - Confidence: 0.85-0.95)
40. **CASE_CITATION** - Full case citations, parallel citations, short forms
41. **STATUTE_CITATION** - General statutory references
42. **USC_CITATIONS** - United States Code references
43. **USC_TITLES** - USC title references (e.g., Title 18)
44. **CFR_CITATIONS** - Code of Federal Regulations references
45. **CFR_TITLES** - CFR title references
46. **STATE_STATUTES** - State statutory references
47. **CONSTITUTIONAL** - General constitutional references
48. **CONSTITUTIONAL_CITATION** - Formal constitutional citations
49. **CONSTITUTIONAL_AMENDMENT** - Specific amendments (First, Second, etc.)
50. **REGULATION_CITATION** - Administrative regulation citations
51. **ADMINISTRATIVE_CITATION** - Administrative law citations

### Legal Citations - Advanced Types (17 types - Confidence: 0.75-0.90)
52. **PARALLEL_CITATIONS** - Multiple reporters for same case
53. **PINPOINT_CITATIONS** - Page-specific citations (e.g., "at 485")
54. **SHORT_FORMS** - Abbreviated case name references
55. **ELECTRONIC_CITATION** - Westlaw, LexisNexis, Bloomberg citations
56. **ELECTRONIC_CITATIONS** - Multiple electronic citations
57. **LAW_REVIEW_CITATION** - Law journal and review citations
58. **TREATISE_CITATION** - Legal treatise citations
59. **RESTATEMENT_CITATION** - Restatement of Law citations
60. **UNIFORM_LAW_CITATION** - Uniform Law Commission citations
61. **PATENT_CITATION** - Patent number citations
62. **SEC_CITATION** - Securities and Exchange Commission citations
63. **TREATY_CITATION** - International treaty citations
64. **INTERNATIONAL_CITATION** - Foreign law citations
65. **INTERNATIONAL_CITATIONS** - Multiple international citations
66. **HISTORICAL_CITATIONS** - Historical legal document citations
67. **ENHANCED_CASE_CITATIONS** - Advanced case citation patterns
68. **FEDERAL_REGISTER** - Federal Register citations

### Temporal Entities (12 types - Confidence: 0.80-0.95)
69. **DATE** - General dates and time references
70. **FILING_DATE** - Document filing dates
71. **DEADLINE** - Legal deadlines and due dates
72. **DECISION_DATE** - Court decision dates
73. **OPINION_DATE** - Opinion publication dates
74. **EFFECTIVE_DATE** - Effective dates for laws/rules/contracts
75. **EXECUTION_DATE** - Contract execution dates
76. **TERM_DATE** - Court term dates
77. **DATE_RANGE** - Date ranges (e.g., "January 1-15, 2024")
78. **RELATIVE_DATE** - Relative time references (e.g., "within 30 days")
79. **FISCAL_YEAR** - Fiscal year references
80. **QUARTER** - Quarterly time periods
81. **LIMITATIONS_PERIOD** - Statute of limitations periods
82. **MONETARY_RANGE** - Monetary amount ranges

### Enhanced Party Patterns (3 types - Confidence: 0.75-0.85)
83. **ENHANCED_PARTY_PATTERNS** - Advanced party name variations

### Document Structure & Legal Terms (8 types - Confidence: 0.70-0.85)
84. **DEFINED_TERM** - Terms defined in contracts/documents
85. **DEFINED_TERM_REFERENCE** - References to defined terms
86. **SECTION_MARKER** - Section numbering (e.g., "§ 1.1")
87. **SECTION_REFERENCE** - References to sections (e.g., "See Section 3")
88. **SECTION_HEADER** - Section headings and titles
89. **SUBSECTION_MARKER** - Subsection designations
90. **SECTION_SYMBOLS** - Section symbols and formatting
91. **LATIN_TERM** - Latin legal terms (e.g., "res judicata", "ex parte")

## Entity Types for This Wave (92 types total)
`PARTY`, `PLAINTIFF`, `DEFENDANT`, `APPELLANT`, `APPELLEE`, `PETITIONER`, `RESPONDENT`, `AMICUS_CURIAE`, `INTERVENOR`, `PRO_SE_PARTY`, `CLASS_ACTION`, `INDIVIDUAL_PARTY`, `CORPORATION`, `GOVERNMENT_ENTITY`, `FEDERAL_AGENCY`, `CONTRACT_PARTY`, `ESTATE`, `FIDUCIARY`, `CASE_PARTIES`, `PARTY_GROUP`, `ATTORNEY`, `GOVERNMENT_LEGAL_OFFICE`, `GOVERNMENT_OFFICIAL`, `INTERNATIONAL_LAW_FIRM`, `PARTIES_CLAUSE`, `COURT`, `FEDERAL_COURTS`, `STATE_COURTS`, `SPECIALIZED_COURTS`, `CIRCUITS`, `DISTRICT`, `JUDGE`, `JUDICIAL_PANEL`, `SPECIALIZED_JURISDICTION`, `GENERIC_COURT_REFERENCES`, `ENHANCED_COURT_PATTERNS`, `SPECIALIZED_COURT_CITATIONS`, `COURT_COSTS`, `COURT_RULE_CITATION`, `CASE_CITATION`, `STATUTE_CITATION`, `USC_CITATIONS`, `USC_TITLES`, `CFR_CITATIONS`, `CFR_TITLES`, `STATE_STATUTES`, `CONSTITUTIONAL`, `CONSTITUTIONAL_CITATION`, `CONSTITUTIONAL_AMENDMENT`, `REGULATION_CITATION`, `ADMINISTRATIVE_CITATION`, `PARALLEL_CITATIONS`, `PINPOINT_CITATIONS`, `SHORT_FORMS`, `ELECTRONIC_CITATION`, `ELECTRONIC_CITATIONS`, `LAW_REVIEW_CITATION`, `TREATISE_CITATION`, `RESTATEMENT_CITATION`, `UNIFORM_LAW_CITATION`, `PATENT_CITATION`, `SEC_CITATION`, `TREATY_CITATION`, `INTERNATIONAL_CITATION`, `INTERNATIONAL_CITATIONS`, `HISTORICAL_CITATIONS`, `ENHANCED_CASE_CITATIONS`, `FEDERAL_REGISTER`, `DATE`, `FILING_DATE`, `DEADLINE`, `DECISION_DATE`, `OPINION_DATE`, `EFFECTIVE_DATE`, `EXECUTION_DATE`, `TERM_DATE`, `DATE_RANGE`, `RELATIVE_DATE`, `FISCAL_YEAR`, `QUARTER`, `LIMITATIONS_PERIOD`, `MONETARY_RANGE`, `ENHANCED_PARTY_PATTERNS`, `DEFINED_TERM`, `DEFINED_TERM_REFERENCE`, `SECTION_MARKER`, `SECTION_REFERENCE`, `SECTION_HEADER`, `SUBSECTION_MARKER`, `SECTION_SYMBOLS`, `LATIN_TERM`, `FEDERAL_RULES`

## Pattern Examples

{{pattern_examples}}

## ⚠️ CRITICAL: Error Prevention Rules (Fix Common Extraction Mistakes)

### 🚫 ERROR #1: Filename Misclassification
**NEVER extract filenames as CASE_CITATION:**
- ❌ BAD: "Rahimi.md" as CASE_CITATION
- ❌ BAD: "document.pdf v. Smith"
- ❌ BAD: "case_brief.docx"
- ✅ GOOD: Only extract case citations with proper reporter format: "Brown v. Board, 347 U.S. 483 (1954)"

**Validation**: Reject if text contains file extensions (.md, .pdf, .docx, .txt, .html)

### 🚫 ERROR #2: Statute vs Procedural Rule Confusion
**§922(g)(8) is a STATUTE, not a PROCEDURAL RULE:**
- ❌ BAD: Extracting "§922(g)(8)" as standalone without "U.S.C."
- ✅ GOOD: Extract "18 U.S.C. § 922(g)(8)" as USC_CITATION or STATUTE_CITATION
- ✅ GOOD: If you see "§" followed by numbers in USC context, it's a STATUTE

**Validation**: USC citations require title number (e.g., "18 U.S.C.")

### 🚫 ERROR #3: Generic Terms as PARTY
**NEVER extract generic relationship terms as PARTY:**
- ❌ BAD: "intimate partner" as PARTY
- ❌ BAD: "domestic partner" as PARTY
- ❌ BAD: "the victim", "the witness", "the defendant's spouse"
- ✅ GOOD: Only extract proper names: "Zackey Rahimi", "Microsoft Corporation"

**Validation**: PARTY must be a specific named individual or entity (proper noun), not a generic descriptor

### 🚫 ERROR #4: Dates Without Context
**Extract dates WITH legal significance:**
- ❌ BAD: "June 21, 2024" as generic DATE without context
- ✅ GOOD: "Oral argument on June 21, 2024" → HEARING_DATE
- ✅ GOOD: "Filed on June 21, 2024" → FILING_DATE
- ✅ GOOD: "Decided June 21, 2024" → Use specific temporal type

**Validation**: Check surrounding text for keywords: "filed", "heard", "argued", "decided", "trial"

### 🚫 ERROR #5: Over-Broad Statute Text (Length Limit)
**Maximum 500 characters for any citation:**
- ❌ BAD: Extracting 59,000 characters of statute text
- ✅ GOOD: Extract only the citation reference: "18 U.S.C. § 922(g)(8)"

**Validation**: Reject extractions longer than 500 characters

### 🚫 ERROR #6: Historical Legal References as ATTORNEY
**"Blackstone" is a legal reference book, not an attorney:**
- ❌ BAD: "John Blackstone" when referring to "Blackstone's Commentaries"
- ❌ BAD: Historical legal scholars: "Coke", "Prosser", "Holmes" (in historical context)
- ✅ GOOD: Only modern attorneys with explicit titles: "Attorney John Smith, Esq."

**Validation**: Reject famous historical legal scholars; require attorney title/role

### 🚫 ERROR #7: Short Case Names (Context Required)
**"Bruen" alone needs context to be CASE_CITATION:**
- ❌ BAD: "Bruen" without context (could be case number or party name)
- ✅ GOOD: "in Bruen", "following Bruen", "the Bruen court" → CASE_CITATION
- ✅ GOOD: "NYSRPA v. Bruen, 597 U.S. 1 (2022)" → Full citation always valid

**Validation**: Short-form case names require legal citation context words

## Input Text
```
{{ text_chunk }}
```

## Extraction Guidelines

### A. PARTY & ACTOR ENTITIES (25 entity types)

#### 1-2. PARTY & INDIVIDUAL_PARTY
- Zackey Rahimi, Jane Doe, John Smith III (individual parties)
- United States of America, State of California, Microsoft Corporation
- PARTY: General party references; INDIVIDUAL_PARTY: Specifically named individuals

**Component Parsing:** party_type (individual/government/corporation), role (if identifiable)

#### 3-7. PLAINTIFF, DEFENDANT, APPELLANT, APPELLEE, PETITIONER, RESPONDENT
- **PLAINTIFF**: Party bringing lawsuit (e.g., "John Smith, Plaintiff")
- **DEFENDANT**: Defending party (e.g., "Acme Corp., Defendant")
- **APPELLANT**: Appealing party (e.g., "United States, Appellant")
- **APPELLEE**: Defending appeal (e.g., "State of California, Appellee")
- **PETITIONER**: Filing petition (e.g., "Microsoft, Petitioner")
- **RESPONDENT**: Responding to petition (e.g., "FTC, Respondent")

#### 8-10. AMICUS_CURIAE, INTERVENOR, PRO_SE_PARTY
- **AMICUS_CURIAE**: "Electronic Frontier Foundation, as Amicus Curiae"
- **INTERVENOR**: "XYZ Corp., Intervenor"
- **PRO_SE_PARTY**: "John Doe, Pro Se"

#### 11-12. CLASS_ACTION, PARTY_GROUP
- **CLASS_ACTION**: "Class Representatives", "Class Counsel"
- **PARTY_GROUP**: "Plaintiffs collectively", "All Defendants"

#### 13-15. CORPORATION, GOVERNMENT_ENTITY, FEDERAL_AGENCY
- **CORPORATION**: Microsoft Corporation, Apple Inc., Acme LLC
- **GOVERNMENT_ENTITY**: State of California, City of New York
- **FEDERAL_AGENCY**: Securities and Exchange Commission, FDA, EPA

#### 16-18. CONTRACT_PARTY, ESTATE, FIDUCIARY
- **CONTRACT_PARTY**: Parties in contracts (e.g., "Buyer", "Seller", "Lessor")
- **ESTATE**: "Estate of John Doe", "The Smith Estate"
- **FIDUCIARY**: "Trustee Jane Smith", "Executor John Doe", "Guardian ad Litem"

#### 19-20. CASE_PARTIES, PARTIES_CLAUSE
- **CASE_PARTIES**: "Smith, Jones, and Williams, Plaintiffs"
- **PARTIES_CLAUSE**: "BETWEEN: John Smith AND: Acme Corp."

#### 21. ATTORNEY
- Attorney General Merrick Garland, Public Defender Sarah Johnson
- Partner Michael Davis, Esq., Counsel for Petitioner

**Component Parsing:** name, title, role (counsel_for_petitioner/respondent)

#### 22-23. GOVERNMENT_LEGAL_OFFICE, GOVERNMENT_OFFICIAL
- **GOVERNMENT_LEGAL_OFFICE**: U.S. Attorney's Office, Office of the Attorney General
- **GOVERNMENT_OFFICIAL**: Attorney General, Solicitor General, District Attorney

#### 24-25. INTERNATIONAL_LAW_FIRM, PARTIES_CLAUSE, ENHANCED_PARTY_PATTERNS
- **INTERNATIONAL_LAW_FIRM**: Clifford Chance LLP, Allen & Overy, Linklaters
- **ENHANCED_PARTY_PATTERNS**: Advanced party name variations and complex structures

### B. COURT & JUDICIAL ENTITIES (14 entity types)

#### 26. COURT (General)
- Supreme Court of the United States, Court of Appeals, District Court

**Component Parsing:** court_type (supreme/appellate/district/trial), jurisdiction (federal/state), circuit, district

#### 27-29. FEDERAL_COURTS, STATE_COURTS, SPECIALIZED_COURTS
- **FEDERAL_COURTS**: U.S. Supreme Court, U.S. Court of Appeals, U.S. District Court
- **STATE_COURTS**: California Supreme Court, Texas Court of Appeals
- **SPECIALIZED_COURTS**: Bankruptcy Court, Tax Court, Court of International Trade

#### 30-31. CIRCUITS, DISTRICT
- **CIRCUITS**: Ninth Circuit, Fifth Circuit Court of Appeals
- **DISTRICT**: Southern District of New York, Eastern District of California

#### 32-33. JUDGE, JUDICIAL_PANEL
- **JUDGE**: Chief Justice Roberts, Justice Sotomayor, Judge Smith, Magistrate Judge Johnson
- **JUDICIAL_PANEL**: "Three-judge panel", "En banc court"

**Component Parsing:** name, title, court (if identifiable)

#### 34-39. Additional Court Types & Citations
- **SPECIALIZED_JURISDICTION**: PTAB, TTAB (specialized jurisdiction courts)
- **GENERIC_COURT_REFERENCES**: "The Court", "This Court", "the trial court"
- **ENHANCED_COURT_PATTERNS**: Advanced court name variations
- **SPECIALIZED_COURT_CITATIONS**: Citations to specialized court decisions
- **COURT_COSTS**: "$1,250 in court costs", "taxable costs"
- **COURT_RULE_CITATION**: Fed. R. Civ. P. 12(b)(6), Fed. R. Crim. P. 11, FRCP 56

### C. LEGAL CITATIONS - CORE TYPES (13 entity types including FEDERAL_RULES)

#### 40. CASE_CITATION
**Full Citations:**
- Brown v. Board of Education, 347 U.S. 483 (1954)
- United States v. Nixon, 418 U.S. 683, 706 (1974)
- Microsoft Corp. v. Apple Inc., 789 F.3d 123 (9th Cir. 2023)

**Federal Court Citations:**
- Johnson v. Smith, 456 F. Supp. 2d 789 (S.D.N.Y. 2020)

**State Court Citations:**
- People v. Johnson, 200 Cal. App. 4th 1234 (2011)

**Component Parsing:** case_name, volume, reporter, first_page, pinpoint, year, court

#### 41. STATUTE_CITATION
**Federal Statutes:** 18 U.S.C. § 922(g)(8), 42 U.S.C. § 1983
**State Statutes:** Cal. Civ. Code § 1798.100, N.Y. Penal Law § 120.05

**Component Parsing:** title, code, section, subsection

#### 42-45. USC & CFR Citations
- **USC_CITATIONS**: 18 U.S.C. § 922(g)(8), 42 U.S.C. § 1983
- **USC_TITLES**: Title 18, Title 42 U.S.C.
- **CFR_CITATIONS**: 29 C.F.R. § 1630.2(g), 40 C.F.R. § 261.3(a)(2)(i)
- **CFR_TITLES**: Title 29 CFR, Title 40 C.F.R.

#### 46-51. Additional Citation Types
- **STATE_STATUTES**: Cal. Civ. Code § 1798.100, Tex. Fam. Code § 85.022
- **CONSTITUTIONAL**: General constitutional references
- **CONSTITUTIONAL_CITATION**: U.S. Const. amend. XIV, § 1
- **CONSTITUTIONAL_AMENDMENT**: First Amendment, Second Amendment
- **REGULATION_CITATION**: Administrative regulation references
- **ADMINISTRATIVE_CITATION**: Agency rule citations

**Component Parsing:** document, article, amendment, section, clause_name

#### 52. FEDERAL_RULES
- Fed. R. Civ. P. 12(b)(6), Fed. R. Crim. P. 11, Fed. R. App. P. 4(a), FRCP 56

### D. LEGAL CITATIONS - ADVANCED TYPES (17 entity types)

#### 52-54. PARALLEL_CITATIONS, PINPOINT_CITATIONS, SHORT_FORMS
- **PARALLEL_CITATIONS**: Roe v. Wade, 410 U.S. 113, 93 S. Ct. 705, 35 L. Ed. 2d 147 (1973)
- **PINPOINT_CITATIONS**: Brown, 347 U.S. at 495; Nixon, 418 U.S. at 706
- **SHORT_FORMS**: Bruen (when referenced after full citation)

#### 55-56. ELECTRONIC_CITATION, ELECTRONIC_CITATIONS
- **ELECTRONIC_CITATION**: 2024 WL 123456, 2023 U.S. Dist. LEXIS 45678
- **ELECTRONIC_CITATIONS**: Multiple electronic database citations

#### 57-59. LAW_REVIEW_CITATION, TREATISE_CITATION, RESTATEMENT_CITATION
- **LAW_REVIEW_CITATION**: 120 Harv. L. Rev. 1523 (2007), 95 Yale L.J. 1283 (1986)
- **TREATISE_CITATION**: Wright & Miller, Federal Practice and Procedure § 2682
- **RESTATEMENT_CITATION**: Restatement (Second) of Contracts § 90

#### 60-61. UNIFORM_LAW_CITATION, PATENT_CITATION
- **UNIFORM_LAW_CITATION**: UCC § 2-207, Uniform Trust Code § 401
- **PATENT_CITATION**: U.S. Patent No. 7,123,456, Patent '456

#### 62-63. SEC_CITATION, TREATY_CITATION
- **SEC_CITATION**: SEC Release No. 34-12345, Securities Act of 1933 § 10(b)
- **TREATY_CITATION**: Geneva Convention, TRIPS Agreement Art. 27

#### 64-66. INTERNATIONAL_CITATION, INTERNATIONAL_CITATIONS, HISTORICAL_CITATIONS
- **INTERNATIONAL_CITATION**: [2024] UKSC 15, ECJ Case C-123/45
- **INTERNATIONAL_CITATIONS**: Multiple foreign law citations
- **HISTORICAL_CITATIONS**: Blackstone's Commentaries, The Federalist No. 78

#### 67-68. ENHANCED_CASE_CITATIONS, FEDERAL_REGISTER
- **ENHANCED_CASE_CITATIONS**: Advanced case citation patterns
- **FEDERAL_REGISTER**: 89 Fed. Reg. 12345 (Feb. 15, 2024)

### E. TEMPORAL ENTITIES (14 entity types including MONETARY_RANGE)

#### 69. DATE
- February 28, 2024 (full date), 2024 (year only), March 2024 (month/year), 02/28/2024 (numeric)

**Component Parsing:** year, month, day, parsed_date (ISO 8601: "2024-02-28")

#### 70-76. Specific Date Types
- **FILING_DATE**: Filed on March 15, 2024; Date Filed: 02/28/2024
- **DEADLINE**: Due by March 30, 2024; Response due within 30 days
- **DECISION_DATE**: Decided June 21, 2024
- **OPINION_DATE**: Opinion issued June 21, 2024
- **EFFECTIVE_DATE**: Effective January 1, 2025
- **EXECUTION_DATE**: Executed on December 15, 2024
- **TERM_DATE**: October Term 2024

#### 77-82. Date Ranges, Relative Dates & Periods
- **DATE_RANGE**: January 1-15, 2024; From March 1 to June 30, 2024
- **RELATIVE_DATE**: within 30 days, no later than 60 days after service
- **FISCAL_YEAR**: FY 2024, Fiscal Year 2023-2024
- **QUARTER**: Q1 2024, First Quarter 2023
- **LIMITATIONS_PERIOD**: three-year statute of limitations, within one year
- **MONETARY_RANGE**: $100,000 to $500,000, between $1M and $5M

### F. DOCUMENT STRUCTURE & LEGAL TERMS (8 entity types)

#### 84-85. DEFINED_TERM, DEFINED_TERM_REFERENCE
- **DEFINED_TERM**: "Effective Date" (as defined), "Licensed Patents" (hereinafter)
- **DEFINED_TERM_REFERENCE**: the Agreement, said Premises, as defined in Section 1.1

#### 86-90. Section Markers, Headers & Symbols
- **SECTION_MARKER**: § 1.1, Section 3.4(a), Article II
- **SECTION_REFERENCE**: See Section 3, refer to Article IV
- **SECTION_HEADER**: "RECITALS", "DEFINITIONS", "REPRESENTATIONS AND WARRANTIES"
- **SUBSECTION_MARKER**: (a), (i), (A)(1)
- **SECTION_SYMBOLS**: § (section), ¶ (paragraph), Art. (article)

#### 91. LATIN_TERM
- res judicata, stare decisis, ex parte, sua sponte, de novo
- inter alia, prima facie, pro se, in rem, habeas corpus

## Required Output Format (LurisEntityV2 Schema)

Return a JSON object with the following structure:

```json
{
  "entities": [
    {
      "id": "uuid-string",
      "text": "The exact text as it appears in the document",
      "entity_type": "CASE_CITATION",
      "start_pos": 0,
      "end_pos": 50,
      "confidence": 0.95,
      "extraction_method": "pattern",
      "subtype": "federal_court",
      "category": "core_legal",
      "metadata": {
        "pattern_matched": "case_citation_bluebook",
        "pattern_source": "federal_citations.yaml",
        "pattern_confidence": 0.98,
        "sentence_context": "surrounding sentence text...",
        "normalized_value": "Standardized format",
        "canonical_form": "Blue Book citation format",
        "related_entities": ["id1", "id2"],
        "custom_attributes": {
          "components": {
            "case_name": "Party v. Party",
            "volume": "347",
            "reporter": "U.S.",
            "first_page": "483",
            "year": "1954"
          }
        }
      },
      "created_at": 1640995200.0
    }
  ],
  "extraction_metadata": {
    "wave_number": 1,
    "wave_name": "Core Entities - Actors, Citations, Temporal",
    "strategy": "three_wave_optimized",
    "target_entity_types": ["PARTY", "PLAINTIFF", "DEFENDANT", "APPELLANT", "APPELLEE", "PETITIONER", "RESPONDENT", "AMICUS_CURIAE", "INTERVENOR", "PRO_SE_PARTY", "CLASS_ACTION", "INDIVIDUAL_PARTY", "CORPORATION", "GOVERNMENT_ENTITY", "FEDERAL_AGENCY", "CONTRACT_PARTY", "ESTATE", "FIDUCIARY", "CASE_PARTIES", "PARTY_GROUP", "ATTORNEY", "GOVERNMENT_LEGAL_OFFICE", "GOVERNMENT_OFFICIAL", "INTERNATIONAL_LAW_FIRM", "PARTIES_CLAUSE", "COURT", "FEDERAL_COURTS", "STATE_COURTS", "SPECIALIZED_COURTS", "CIRCUITS", "DISTRICT", "JUDGE", "JUDICIAL_PANEL", "SPECIALIZED_JURISDICTION", "GENERIC_COURT_REFERENCES", "ENHANCED_COURT_PATTERNS", "SPECIALIZED_COURT_CITATIONS", "COURT_COSTS", "COURT_RULE_CITATION", "CASE_CITATION", "STATUTE_CITATION", "USC_CITATIONS", "USC_TITLES", "CFR_CITATIONS", "CFR_TITLES", "STATE_STATUTES", "CONSTITUTIONAL", "CONSTITUTIONAL_CITATION", "CONSTITUTIONAL_AMENDMENT", "REGULATION_CITATION", "ADMINISTRATIVE_CITATION", "PARALLEL_CITATIONS", "PINPOINT_CITATIONS", "SHORT_FORMS", "ELECTRONIC_CITATION", "ELECTRONIC_CITATIONS", "LAW_REVIEW_CITATION", "TREATISE_CITATION", "RESTATEMENT_CITATION", "UNIFORM_LAW_CITATION", "PATENT_CITATION", "SEC_CITATION", "TREATY_CITATION", "INTERNATIONAL_CITATION", "INTERNATIONAL_CITATIONS", "HISTORICAL_CITATIONS", "ENHANCED_CASE_CITATIONS", "FEDERAL_REGISTER", "DATE", "FILING_DATE", "DEADLINE", "DECISION_DATE", "OPINION_DATE", "EFFECTIVE_DATE", "EXECUTION_DATE", "TERM_DATE", "DATE_RANGE", "RELATIVE_DATE", "FISCAL_YEAR", "QUARTER", "LIMITATIONS_PERIOD", "MONETARY_RANGE", "ENHANCED_PARTY_PATTERNS", "DEFINED_TERM", "DEFINED_TERM_REFERENCE", "SECTION_MARKER", "SECTION_REFERENCE", "SECTION_HEADER", "SUBSECTION_MARKER", "SECTION_SYMBOLS", "LATIN_TERM", "FEDERAL_RULES"],
    "confidence_threshold": 0.70,
    "total_entities_found": 0,
    "entity_type_counts": {
      "PARTY": 0,
      "PLAINTIFF": 0,
      "DEFENDANT": 0,
      "APPELLANT": 0,
      "APPELLEE": 0,
      "PETITIONER": 0,
      "RESPONDENT": 0,
      "AMICUS_CURIAE": 0,
      "INTERVENOR": 0,
      "PRO_SE_PARTY": 0,
      "CLASS_ACTION": 0,
      "INDIVIDUAL_PARTY": 0,
      "CORPORATION": 0,
      "GOVERNMENT_ENTITY": 0,
      "FEDERAL_AGENCY": 0,
      "CONTRACT_PARTY": 0,
      "ESTATE": 0,
      "FIDUCIARY": 0,
      "CASE_PARTIES": 0,
      "PARTY_GROUP": 0,
      "ATTORNEY": 0,
      "GOVERNMENT_LEGAL_OFFICE": 0,
      "GOVERNMENT_OFFICIAL": 0,
      "INTERNATIONAL_LAW_FIRM": 0,
      "PARTIES_CLAUSE": 0,
      "COURT": 0,
      "FEDERAL_COURTS": 0,
      "STATE_COURTS": 0,
      "SPECIALIZED_COURTS": 0,
      "CIRCUITS": 0,
      "DISTRICT": 0,
      "JUDGE": 0,
      "JUDICIAL_PANEL": 0,
      "SPECIALIZED_JURISDICTION": 0,
      "GENERIC_COURT_REFERENCES": 0,
      "ENHANCED_COURT_PATTERNS": 0,
      "SPECIALIZED_COURT_CITATIONS": 0,
      "COURT_COSTS": 0,
      "COURT_RULE_CITATION": 0,
      "CASE_CITATION": 0,
      "STATUTE_CITATION": 0,
      "USC_CITATIONS": 0,
      "USC_TITLES": 0,
      "CFR_CITATIONS": 0,
      "CFR_TITLES": 0,
      "STATE_STATUTES": 0,
      "CONSTITUTIONAL": 0,
      "CONSTITUTIONAL_CITATION": 0,
      "CONSTITUTIONAL_AMENDMENT": 0,
      "REGULATION_CITATION": 0,
      "ADMINISTRATIVE_CITATION": 0,
      "PARALLEL_CITATIONS": 0,
      "PINPOINT_CITATIONS": 0,
      "SHORT_FORMS": 0,
      "ELECTRONIC_CITATION": 0,
      "ELECTRONIC_CITATIONS": 0,
      "LAW_REVIEW_CITATION": 0,
      "TREATISE_CITATION": 0,
      "RESTATEMENT_CITATION": 0,
      "UNIFORM_LAW_CITATION": 0,
      "PATENT_CITATION": 0,
      "SEC_CITATION": 0,
      "TREATY_CITATION": 0,
      "INTERNATIONAL_CITATION": 0,
      "INTERNATIONAL_CITATIONS": 0,
      "HISTORICAL_CITATIONS": 0,
      "ENHANCED_CASE_CITATIONS": 0,
      "FEDERAL_REGISTER": 0,
      "DATE": 0,
      "FILING_DATE": 0,
      "DEADLINE": 0,
      "DECISION_DATE": 0,
      "OPINION_DATE": 0,
      "EFFECTIVE_DATE": 0,
      "EXECUTION_DATE": 0,
      "TERM_DATE": 0,
      "DATE_RANGE": 0,
      "RELATIVE_DATE": 0,
      "FISCAL_YEAR": 0,
      "QUARTER": 0,
      "LIMITATIONS_PERIOD": 0,
      "MONETARY_RANGE": 0,
      "ENHANCED_PARTY_PATTERNS": 0,
      "DEFINED_TERM": 0,
      "DEFINED_TERM_REFERENCE": 0,
      "SECTION_MARKER": 0,
      "SECTION_REFERENCE": 0,
      "SECTION_HEADER": 0,
      "SUBSECTION_MARKER": 0,
      "SECTION_SYMBOLS": 0,
      "LATIN_TERM": 0,
      "FEDERAL_RULES": 0
    },
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

- **High Confidence (0.85-1.0)**: Clear pattern matches with strong context (Core citations, parties, courts)
- **Medium-High Confidence (0.75-0.85)**: Strong pattern matches with moderate context (Advanced citations, specific party types)
- **Medium Confidence (0.70-0.75)**: Partial pattern matches or uncertain context (Document structure, legal terms)
- **Minimum Threshold**: Do not extract entities below 0.70 confidence for this wave

**Confidence Guidelines by Category:**
- Party & Actor Entities: 0.80-0.95
- Court & Judicial Entities: 0.85-0.95
- Core Legal Citations: 0.85-0.95
- Advanced Legal Citations: 0.75-0.90
- Temporal Entities: 0.80-0.95
- Document Structure & Legal Terms: 0.70-0.85

## Special Instructions

1. **Exact Text**: Preserve exact text as it appears, including punctuation
2. **Position Accuracy**: Ensure start_pos and end_pos are accurate character positions
3. **No Overlaps**: Avoid overlapping entity boundaries
4. **Sentence Context**: Include surrounding sentence in metadata for validation
5. **Pattern Attribution**: When possible, attribute extraction to specific pattern sources
6. **Normalization**: Provide standardized forms:
   - Blue Book format for case citations
   - ISO 8601 (YYYY-MM-DD) for dates
   - Canonical format for statute citations
7. **Related Entities**: Link related entities using IDs when applicable
8. **Component Parsing**: Break down complex entities into components (see examples above)

## Validation Checks

- Verify all entities meet confidence threshold (≥0.85)
- Ensure no duplicate text extractions
- Validate position boundaries don't exceed text length
- Confirm entity_type matches allowed types for this wave
- Check that confidence scores are in valid range [0.0, 1.0]
- Verify component parsing accuracy for citations and dates
- Validate Bluebook format compliance for case citations
- Check ISO 8601 date format normalization

## Wave 1 Focus

Extract ALL qualifying entities meeting the confidence threshold. This is **Wave 1 of 3** in the optimized extraction pipeline - focus on **92 core entity types** across these categories:

**Core Extraction Focus (Wave 1 - 92 types):**
1. **Party & Actor Entities (25 types)**: All parties, attorneys, government officials, legal offices
2. **Court & Judicial Entities (14 types)**: All court types, judges, judicial panels, court citations
3. **Legal Citations - Core (12 types)**: Case citations, statutes, USC, CFR, constitutional, state statutes
4. **Legal Citations - Advanced (17 types)**: Parallel citations, electronic citations, law reviews, treatises, international
5. **Temporal Entities (14 types)**: All date types, deadlines, date ranges, fiscal periods
6. **Enhanced Patterns (1 type)**: Enhanced party pattern variations
7. **Document Structure & Legal Terms (8 types)**: Defined terms, section markers, Latin terms

**Confidence Threshold by Category:**
- Core entities (parties, courts, core citations): ≥0.80
- Advanced citations: ≥0.75
- Document structure: ≥0.70

**Wave 2** will extract: Case numbers, docket numbers, motions, briefs, procedural rules, monetary amounts, damages, fines, fees, awards, law firms, discovery requests (29 types).

**Wave 3** will extract: Addresses, emails, phone numbers, bar numbers, jurisdictional concepts, legal doctrines, entity relationships, structural elements (40 types).

**Complete Wave 1 extraction now covering all 92 entity types with appropriate confidence thresholds.**
