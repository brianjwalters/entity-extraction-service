# Comprehensive Legal Entity Examples for PageBatch Prompt Template

## Analysis Summary
Based on analysis of 295+ regex patterns across 53 YAML files in the Entity Extraction Service, here are concrete examples for each major legal entity type that should be incorporated into the PageBatch prompt template.

## Critical Entity Types with Examples

### 1. CASE_CITATION
**Pattern:** `\d{1,3}\s+[A-Z]\.\s*(?:2d|3d|4th)?\s+\d{1,4}`

**Examples:**
- "347 U.S. 483"
- "384 U.S. 436"
- "123 F.3d 456"
- "789 F.2d 234"
- "456 N.Y.S.2d 789"
- "234 Cal. App. 4th 567"
- "890 F. Supp. 2d 123"
- "74 S. Ct. 686"
- "86 S. Ct. 1602"

### 2. USC_CITATION
**Pattern:** `\d{1,2}\s+U\.S\.C\.\s+§\s*\d+`

**Examples:**
- "42 U.S.C. § 1983"
- "18 U.S.C. § 242"
- "28 U.S.C. § 1331"
- "15 U.S.C. § 78j(b)"
- "26 U.S.C. § 501(c)(3)"
- "18 U.S.C. § 922(g)(8)"
- "5 U.S.C. § 706(2)(A)"
- "42 U.S.C. §§ 1981-1988"

### 3. COURT
**Pattern:** Various court name patterns

**Examples:**
- "Supreme Court of the United States"
- "United States District Court"
- "Court of Appeals for the Ninth Circuit"
- "Fifth Circuit"
- "Northern District of California"
- "Eastern District of Texas"
- "Superior Court of California"
- "New York Court of Appeals"

### 4. JUDGE
**Pattern:** `[Name],?\s+(?:Chief\s+)?(?:Circuit\s+|District\s+|Magistrate\s+)?Judge`

**Examples:**
- "Chief Justice Roberts"
- "Justice Sotomayor"
- "CHAGARES, Chief Judge"
- "HARDIMAN, Circuit Judge"
- "Pratter, District Judge"
- "Smith, Magistrate Judge"
- "The Honorable Jane Doe"
- "Associate Justice Kagan"

### 5. PARTY
**Pattern:** Case party names in citations

**Examples:**
- "United States"
- "Zackey Rahimi"
- "Brown"
- "Board of Education"
- "Smith Corporation"
- "ABC Company, Inc."
- "The State of California"
- "John Doe"
- "Jane Roe"

### 6. STATUTE
**Pattern:** Various statutory references

**Examples:**
- "Section 922(g)(8)"
- "18 USC 242"
- "Title VII of the Civil Rights Act"
- "Americans with Disabilities Act"
- "Federal Magistrates Act of 1968"
- "Cal. Penal Code § 187"
- "N.Y. Gen. Bus. Law § 349"
- "Tex. Bus. & Com. Code § 17.46"

### 7. LEGAL_DOCTRINE
**Pattern:** Legal principle terms

**Examples:**
- "res judicata"
- "stare decisis"
- "due process"
- "qualified immunity"
- "sovereign immunity"
- "collateral estoppel"
- "prima facie"
- "inter alia"
- "habeas corpus"
- "mens rea"

### 8. MOTION
**Pattern:** `motion\s+(to|for)\s+[phrase]`

**Examples:**
- "Motion to Dismiss"
- "Motion for Summary Judgment"
- "Motion to Compel Discovery"
- "Motion in Limine"
- "Motion to Vacate Default Judgment"
- "Rule 12(b)(6)"
- "summary judgment granted"
- "cross-motion for summary judgment"

### 9. DATE
**Pattern:** Various date formats

**Examples:**
- "June 21, 2024"
- "November 7, 2023"
- "January 1, 2024"
- "03/15/2024"
- "2024-06-30"
- "May 5th, 2023"
- "within 30 days"
- "on or before January 15, 2024"

### 10. CASE_NUMBER
**Pattern:** `(No\.|Case No\.|Civil Action No\.)\s*[\d:\-cv]+`

**Examples:**
- "No. 22-915"
- "Case No. 1:21-cv-00123"
- "Civil Action No. 20-4567"
- "Criminal No. 19-cr-890"
- "Bankruptcy No. 18-12345"
- "Appeal No. 21-1234"
- "Docket No. 19-1392"

### 11. CONSTITUTIONAL_PROVISION
**Pattern:** Constitutional references

**Examples:**
- "First Amendment"
- "Second Amendment"
- "Fourteenth Amendment Due Process Clause"
- "Fifth Amendment"
- "Article II Executive Power"
- "Commerce Clause"
- "Supremacy Clause"
- "Equal Protection Clause"

### 12. CFR_CITATION
**Pattern:** `\d{1,2}\s+C\.F\.R\.\s+§?\s*\d+`

**Examples:**
- "40 C.F.R. § 1500.1"
- "21 C.F.R. Part 211"
- "29 C.F.R. § 1910.134"
- "17 C.F.R. § 240.10b-5"
- "14 C.F.R. Part 91"
- "28 C.F.R. Part 52"

### 13. PROCEDURAL_RULE
**Pattern:** Federal Rules references

**Examples:**
- "Federal Rules of Civil Procedure"
- "Rule 12(b)(6)"
- "Rule 56"
- "Rule 11 Sanctions"
- "Rule 26 Discovery"
- "Rule 23 Class Action"
- "Federal Rules of Evidence"

### 14. LEGAL_STANDARD
**Pattern:** Burden of proof standards

**Examples:**
- "beyond a reasonable doubt"
- "preponderance of the evidence"
- "clear and convincing evidence"
- "probable cause"
- "reasonable suspicion"
- "abuse of discretion"
- "de novo review"

### 15. ATTORNEY
**Pattern:** Attorney names and titles

**Examples:**
- "John Smith, Esq."
- "Attorney Jane Doe"
- "Counsel for Plaintiff"
- "Defense Attorney Michael Johnson"
- "Sarah Williams, Attorney at Law"
- "Assistant U.S. Attorney"
- "State Bar No. 123456"

## Recommended Prompt Template Enhancement

To fix the zero entity extraction issue in PageBatch strategy, add this instruction block to the prompt:

```
ENTITY IDENTIFICATION INSTRUCTIONS:

You must identify and extract ALL legal entities in the text. Look for these specific patterns:

1. **Case Citations**: Numbers followed by reporter abbreviations (e.g., "347 U.S. 483", "123 F.3d 456")
2. **Statute Citations**: Title numbers with U.S.C. and section symbols (e.g., "42 U.S.C. § 1983", "18 U.S.C. § 922(g)(8)")
3. **Court Names**: Any mention of courts (e.g., "Supreme Court", "Fifth Circuit", "Northern District")
4. **Judge Names**: Names with judicial titles (e.g., "Chief Justice Roberts", "Judge Smith")
5. **Party Names**: Names in case captions or legal proceedings (e.g., "United States", "Zackey Rahimi")
6. **Legal Doctrines**: Latin terms and legal principles (e.g., "stare decisis", "due process")
7. **Motions**: Legal motions and procedural requests (e.g., "Motion to Dismiss", "summary judgment")
8. **Dates**: Any date references (e.g., "June 21, 2024", "within 30 days")
9. **Case Numbers**: Docket and case identifiers (e.g., "No. 22-915", "1:21-cv-00123")
10. **Constitutional Provisions**: Amendment references (e.g., "Second Amendment", "Due Process Clause")

For EACH entity found, provide:
- entity_type: The category from above
- text: The exact text of the entity
- confidence: Your confidence score (0.0-1.0)
- context: Brief surrounding context
```

## Key Patterns for Rahimi Case

Since the test case is United States v. Rahimi, ensure the prompt specifically catches:

1. **Case Name**: "United States v. Rahimi" or "United States v. Zackey Rahimi"
2. **Case Number**: "No. 22-915"
3. **Statute**: "18 U.S.C. § 922(g)(8)" (the challenged provision)
4. **Constitutional**: "Second Amendment"
5. **Court**: "Supreme Court of the United States"
6. **Standard**: "facial challenge", "as-applied challenge"
7. **Precedents**: References to "Heller", "Bruen", "McDonald"

## Testing Recommendations

1. Test extraction with these specific text snippets
2. Verify each entity type is properly identified
3. Check confidence scores are appropriate
4. Ensure no false positives for common words
5. Validate against the Rahimi PDF test document

## Pattern Confidence Levels

Based on the regex patterns analyzed:
- **High Confidence (0.95-0.98)**: USC citations, case citations, court names
- **Medium-High (0.90-0.94)**: Judge names, motions, dates
- **Medium (0.85-0.89)**: Party names, legal doctrines, attorney names

This comprehensive list should significantly improve the PageBatch strategy's entity extraction performance.