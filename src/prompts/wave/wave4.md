---
wave: 4
entity_count: 0
relationship_count: 34
focus: "Entity Relationship Extraction for GraphRAG"
confidence_threshold: 0.85
estimated_tokens: 8000
description: "Extract relationships between entities for knowledge graph construction"
---

# Wave 4: Entity Relationship Extraction

## Task Description

You have completed entity extraction in Waves 1-3, identifying 161 entity types across core legal entities, procedural elements, and supporting concepts. **Wave 4 focuses exclusively on extracting relationships between these entities** to build a knowledge graph for GraphRAG-powered contextual legal research.

**Input**: All entities from Waves 1-3 (provided in previous_results)
**Output**: Relationships with explicit text evidence and confidence scores
**Purpose**: Knowledge graph construction enabling semantic search, precedent analysis, and legal reasoning chains

**Critical Requirements**:
- Both source and target entities MUST exist in Waves 1-3 results
- Every relationship MUST have explicit text evidence (no inference)
- Minimum confidence threshold: 0.85
- Include context spans (before/after relationship mention)
- No speculative or implied relationships

## Relationship Categories

### 1. Case-to-Case Relationships (5 types - Confidence: 0.90-0.95)

These relationships map the judicial precedent hierarchy and case law evolution.

#### 1.1 CITES_CASE
**Definition**: Case A cites Case B as legal authority or precedent

**Extraction Patterns**:
- "In [Case A], the Court cited [Case B]"
- "[Case A] relies on [Case B] for the proposition that..."
- "As held in [Case B], this Court in [Case A] concluded..."
- "Following [Case B], the [Case A] court ruled..."

**Example**:
```
Text: "In Roe v. Wade (1973), the Supreme Court extensively cited Griswold v. Connecticut (1965) as establishing the constitutional foundation for privacy rights."

Relationship:
{
  "source_entity_id": "entity_042",  // Roe v. Wade
  "target_entity_id": "entity_018",  // Griswold v. Connecticut
  "relationship_type": "CITES_CASE",
  "confidence": 0.95,
  "evidence_text": "the Supreme Court extensively cited Griswold v. Connecticut (1965) as establishing the constitutional foundation",
  "context_before": "In Roe v. Wade (1973),",
  "context_after": "for privacy rights."
}
```

**Evidence Required**:
- Explicit citation language ("cited", "citing", "referenced", "relied upon")
- Both case names clearly identified
- Context showing citation purpose

#### 1.2 OVERRULES_CASE
**Definition**: Case A explicitly overrules or reverses Case B

**Extraction Patterns**:
- "[Case A] overrules [Case B]"
- "[Case B] is hereby overruled by [Case A]"
- "[Case A] expressly overrules [Case B]"
- "We overrule [Case B] to the extent it conflicts with..."

**Example**:
```
Text: "Dobbs v. Jackson Women's Health Organization (2022) expressly overrules Roe v. Wade (1973) and Planned Parenthood v. Casey (1992)."

Relationship:
{
  "source_entity_id": "entity_156",  // Dobbs v. Jackson
  "target_entity_id": "entity_042",  // Roe v. Wade
  "relationship_type": "OVERRULES_CASE",
  "confidence": 0.98,
  "evidence_text": "expressly overrules Roe v. Wade (1973)",
  "context_before": "Dobbs v. Jackson Women's Health Organization (2022)",
  "context_after": "and Planned Parenthood v. Casey (1992)."
}
```

**Evidence Required**:
- Explicit overruling language ("overrule", "reverse", "abrogate")
- Clear identification of both cases
- High confidence threshold (0.95+) - this is a critical relationship

#### 1.3 DISTINGUISHES_CASE
**Definition**: Case A distinguishes itself from Case B by highlighting factual or legal differences

**Extraction Patterns**:
- "[Case A] is distinguishable from [Case B] because..."
- "Unlike [Case B], [Case A] involves..."
- "We distinguish [Case B] on the grounds that..."
- "[Case A] differs from [Case B] in that..."

**Example**:
```
Text: "Brown v. Board of Education is distinguishable from Plessy v. Ferguson because the modern understanding of equality under the Fourteenth Amendment has evolved."

Relationship:
{
  "source_entity_id": "entity_089",  // Brown v. Board
  "target_entity_id": "entity_021",  // Plessy v. Ferguson
  "relationship_type": "DISTINGUISHES_CASE",
  "confidence": 0.92,
  "evidence_text": "Brown v. Board of Education is distinguishable from Plessy v. Ferguson",
  "context_before": "",
  "context_after": "because the modern understanding of equality under the Fourteenth Amendment has evolved."
}
```

**Evidence Required**:
- Explicit distinguishing language
- Explanation of difference (factual or legal)
- Both cases clearly identified

#### 1.4 FOLLOWS_CASE
**Definition**: Case A follows the precedent established by Case B

**Extraction Patterns**:
- "[Case A] follows [Case B]"
- "Following [Case B], this Court holds..."
- "[Case A] adopts the reasoning of [Case B]"
- "Consistent with [Case B], [Case A] concludes..."

**Example**:
```
Text: "Miranda v. Arizona follows the precedent established in Escobedo v. Illinois regarding custodial interrogation protections."

Relationship:
{
  "source_entity_id": "entity_067",  // Miranda v. Arizona
  "target_entity_id": "entity_055",  // Escobedo v. Illinois
  "relationship_type": "FOLLOWS_CASE",
  "confidence": 0.90,
  "evidence_text": "Miranda v. Arizona follows the precedent established in Escobedo v. Illinois",
  "context_before": "",
  "context_after": "regarding custodial interrogation protections."
}
```

**Evidence Required**:
- Language indicating precedent-following ("follows", "adopts", "consistent with")
- Both cases identified
- Context showing legal principle continuity

#### 1.5 QUESTIONS_CASE
**Definition**: Case A questions or casts doubt on the reasoning or holding of Case B (without formally overruling)

**Extraction Patterns**:
- "[Case A] questions the reasoning in [Case B]"
- "The [Case A] court expressed doubts about [Case B]"
- "[Case A] criticized [Case B] but declined to overrule it"
- "We question whether [Case B] remains viable..."

**Example**:
```
Text: "The majority opinion questions the reasoning in Lochner v. New York, suggesting its substantive due process analysis may no longer be sound."

Relationship:
{
  "source_entity_id": "entity_103",  // Current case
  "target_entity_id": "entity_034",  // Lochner v. New York
  "relationship_type": "QUESTIONS_CASE",
  "confidence": 0.88,
  "evidence_text": "questions the reasoning in Lochner v. New York, suggesting its substantive due process analysis may no longer be sound",
  "context_before": "The majority opinion",
  "context_after": ""
}
```

**Evidence Required**:
- Language expressing doubt or criticism
- Both cases identified
- Must NOT be formal overruling (use OVERRULES_CASE instead)

---

### 2. Statute Relationships (4 types - Confidence: 0.90-0.95)

These relationships connect judicial decisions to statutory authority.

#### 2.1 CITES_STATUTE
**Definition**: Document or case cites a statute as authority

**Extraction Patterns**:
- "Section [number] of [statute]"
- "[Entity] cites [USC/CFR citation]"
- "Under [statute], the defendant..."
- "As required by [statute]..."

**Example**:
```
Text: "The complaint alleges violations of 42 U.S.C. § 1983, the federal civil rights statute."

Relationship:
{
  "source_entity_id": "entity_012",  // Complaint
  "target_entity_id": "entity_088",  // 42 U.S.C. § 1983
  "relationship_type": "CITES_STATUTE",
  "confidence": 0.94,
  "evidence_text": "alleges violations of 42 U.S.C. § 1983",
  "context_before": "The complaint",
  "context_after": ", the federal civil rights statute."
}
```

#### 2.2 INTERPRETS_STATUTE
**Definition**: Court interprets the meaning or scope of a statute

**Extraction Patterns**:
- "The Court interprets [statute] to mean..."
- "In construing [statute], we hold that..."
- "[Statute] must be interpreted as..."
- "The proper interpretation of [statute] is..."

**Example**:
```
Text: "The Court interprets Title VII of the Civil Rights Act of 1964 to include sexual orientation discrimination as a form of sex discrimination."

Relationship:
{
  "source_entity_id": "entity_145",  // Court/Case
  "target_entity_id": "entity_091",  // Title VII
  "relationship_type": "INTERPRETS_STATUTE",
  "confidence": 0.96,
  "evidence_text": "The Court interprets Title VII of the Civil Rights Act of 1964 to include sexual orientation discrimination",
  "context_before": "",
  "context_after": "as a form of sex discrimination."
}
```

#### 2.3 APPLIES_STATUTE
**Definition**: Court applies a statute to the facts of a case

**Extraction Patterns**:
- "Applying [statute] to these facts..."
- "Under [statute], the defendant's conduct..."
- "[Statute] applies to this situation because..."
- "The Court applies [statute] and finds..."

**Example**:
```
Text: "Applying the Administrative Procedure Act, the Court finds the agency's rulemaking violated notice-and-comment requirements."

Relationship:
{
  "source_entity_id": "entity_078",  // Court
  "target_entity_id": "entity_102",  // APA
  "relationship_type": "APPLIES_STATUTE",
  "confidence": 0.93,
  "evidence_text": "Applying the Administrative Procedure Act, the Court finds the agency's rulemaking violated notice-and-comment requirements",
  "context_before": "",
  "context_after": ""
}
```

#### 2.4 INVALIDATES_STATUTE
**Definition**: Court declares a statute unconstitutional or otherwise invalid

**Extraction Patterns**:
- "The Court invalidates [statute]"
- "[Statute] is hereby declared unconstitutional"
- "We strike down [statute] as violating..."
- "[Statute] is invalidated on [constitutional grounds]"

**Example**:
```
Text: "The Supreme Court invalidates Section 4 of the Voting Rights Act as exceeding Congressional authority under the Fifteenth Amendment."

Relationship:
{
  "source_entity_id": "entity_134",  // Supreme Court
  "target_entity_id": "entity_096",  // VRA Section 4
  "relationship_type": "INVALIDATES_STATUTE",
  "confidence": 0.97,
  "evidence_text": "The Supreme Court invalidates Section 4 of the Voting Rights Act",
  "context_before": "",
  "context_after": "as exceeding Congressional authority under the Fifteenth Amendment."
}
```

---

### 3. Party Relationships (4 types - Confidence: 0.85-0.90)

These relationships map the human and organizational actors in legal proceedings.

#### 3.1 PARTY_VS_PARTY
**Definition**: Adversarial relationship between parties in litigation

**Extraction Patterns**:
- "[Party A] v. [Party B]"
- "[Party A] versus [Party B]"
- "[Plaintiff] brings suit against [Defendant]"
- "[Party A] sued [Party B]"

**Example**:
```
Text: "John Smith brings this action against Acme Corporation for employment discrimination."

Relationship:
{
  "source_entity_id": "entity_007",  // John Smith
  "target_entity_id": "entity_015",  // Acme Corporation
  "relationship_type": "PARTY_VS_PARTY",
  "confidence": 0.92,
  "evidence_text": "John Smith brings this action against Acme Corporation",
  "context_before": "",
  "context_after": "for employment discrimination."
}
```

#### 3.2 REPRESENTS
**Definition**: Attorney or law firm represents a party

**Extraction Patterns**:
- "[Attorney] represents [Party]"
- "[Party] is represented by [Attorney]"
- "Counsel for [Party], [Attorney]..."
- "[Attorney], appearing on behalf of [Party]..."

**Example**:
```
Text: "Sarah Johnson of Johnson & Associates represents the plaintiff, Mary Williams."

Relationship:
{
  "source_entity_id": "entity_022",  // Sarah Johnson
  "target_entity_id": "entity_009",  // Mary Williams
  "relationship_type": "REPRESENTS",
  "confidence": 0.95,
  "evidence_text": "Sarah Johnson of Johnson & Associates represents the plaintiff, Mary Williams",
  "context_before": "",
  "context_after": ""
}
```

#### 3.3 EMPLOYED_BY
**Definition**: Attorney is employed by or affiliated with a law firm or organization

**Extraction Patterns**:
- "[Attorney] of [Law Firm]"
- "[Attorney], employed by [Organization]"
- "[Attorney], partner at [Law Firm]"
- "[Attorney] ([Law Firm])"

**Example**:
```
Text: "Michael Chen, partner at Chen & Associates, argued for the appellant."

Relationship:
{
  "source_entity_id": "entity_031",  // Michael Chen
  "target_entity_id": "entity_047",  // Chen & Associates
  "relationship_type": "EMPLOYED_BY",
  "confidence": 0.90,
  "evidence_text": "Michael Chen, partner at Chen & Associates",
  "context_before": "",
  "context_after": ", argued for the appellant."
}
```

#### 3.4 MEMBER_OF
**Definition**: Party is a member of an organization, class, or group

**Extraction Patterns**:
- "[Party], a member of [Organization]"
- "[Party] belongs to [Group]"
- "[Party], member of the [Class]"
- "[Organization] includes [Party] as a member"

**Example**:
```
Text: "The named plaintiffs, members of the proposed class of affected consumers, seek certification."

Relationship:
{
  "source_entity_id": "entity_019",  // Named plaintiffs
  "target_entity_id": "entity_028",  // Proposed class
  "relationship_type": "MEMBER_OF",
  "confidence": 0.88,
  "evidence_text": "The named plaintiffs, members of the proposed class",
  "context_before": "",
  "context_after": "of affected consumers, seek certification."
}
```

---

### 4. Procedural Relationships (4 types - Confidence: 0.85-0.90)

These relationships track the progression of legal proceedings through the court system.

#### 4.1 APPEALS_FROM
**Definition**: Case A is an appeal from Case B or lower court decision

**Extraction Patterns**:
- "[Case A] appeals from [Court/Case B]"
- "On appeal from [Court]..."
- "[Party] appeals the decision of [Court]"
- "This appeal arises from [Court's] ruling in [Case B]"

**Example**:
```
Text: "This case comes to us on appeal from the United States District Court for the Southern District of New York."

Relationship:
{
  "source_entity_id": "entity_056",  // Current case
  "target_entity_id": "entity_073",  // SDNY
  "relationship_type": "APPEALS_FROM",
  "confidence": 0.94,
  "evidence_text": "on appeal from the United States District Court for the Southern District of New York",
  "context_before": "This case comes to us",
  "context_after": ""
}
```

#### 4.2 REMANDS_TO
**Definition**: Appellate court remands case back to lower court

**Extraction Patterns**:
- "We remand to [Court]"
- "Case is remanded to [Court] for further proceedings"
- "Remanded to [Court] for [purpose]"
- "The matter is remanded to [Court]"

**Example**:
```
Text: "We reverse and remand to the District Court for proceedings consistent with this opinion."

Relationship:
{
  "source_entity_id": "entity_089",  // Appellate Court
  "target_entity_id": "entity_041",  // District Court
  "relationship_type": "REMANDS_TO",
  "confidence": 0.96,
  "evidence_text": "remand to the District Court for proceedings consistent with this opinion",
  "context_before": "We reverse and",
  "context_after": ""
}
```

#### 4.3 CONSOLIDATES_WITH
**Definition**: Case A is consolidated with Case B for joint proceedings

**Extraction Patterns**:
- "[Case A] is consolidated with [Case B]"
- "These cases are consolidated for trial"
- "[Case A] and [Case B] are hereby consolidated"
- "Consolidation of [Case A] with [Case B]"

**Example**:
```
Text: "Smith v. Acme Corp. is hereby consolidated with Jones v. Acme Corp. for purposes of discovery and trial."

Relationship:
{
  "source_entity_id": "entity_011",  // Smith v. Acme
  "target_entity_id": "entity_014",  // Jones v. Acme
  "relationship_type": "CONSOLIDATES_WITH",
  "confidence": 0.93,
  "evidence_text": "Smith v. Acme Corp. is hereby consolidated with Jones v. Acme Corp.",
  "context_before": "",
  "context_after": "for purposes of discovery and trial."
}
```

#### 4.4 RELATES_TO
**Definition**: Case A is related to Case B (same parties, issues, or facts) without formal consolidation

**Extraction Patterns**:
- "[Case A] is related to [Case B]"
- "This matter is related to [Case B]"
- "[Case A] involves issues similar to [Case B]"
- "See also [Related Case]"

**Example**:
```
Text: "This matter is related to Case No. 21-cv-12345, which involves the same underlying contract dispute."

Relationship:
{
  "source_entity_id": "entity_067",  // Current case
  "target_entity_id": "entity_078",  // Related case
  "relationship_type": "RELATES_TO",
  "confidence": 0.87,
  "evidence_text": "This matter is related to Case No. 21-cv-12345",
  "context_before": "",
  "context_after": ", which involves the same underlying contract dispute."
}
```

---

### 5. Document Relationships (4 types - Confidence: 0.85-0.90)

These relationships connect legal documents to each other.

#### 5.1 REFERENCES_DOCUMENT
**Definition**: Document A references or mentions Document B

**Extraction Patterns**:
- "[Document A] references [Document B]"
- "As stated in [Document B]..."
- "[Document A] refers to [Document B]"
- "See [Document B]"

**Example**:
```
Text: "The Complaint references Exhibit A, the signed employment agreement dated January 15, 2020."

Relationship:
{
  "source_entity_id": "entity_003",  // Complaint
  "target_entity_id": "entity_024",  // Exhibit A
  "relationship_type": "REFERENCES_DOCUMENT",
  "confidence": 0.92,
  "evidence_text": "The Complaint references Exhibit A, the signed employment agreement",
  "context_before": "",
  "context_after": "dated January 15, 2020."
}
```

#### 5.2 INCORPORATES_BY_REFERENCE
**Definition**: Document A legally incorporates Document B by reference

**Extraction Patterns**:
- "[Document A] incorporates [Document B] by reference"
- "[Document B] is incorporated herein by reference"
- "[Document A] includes [Document B] as if fully set forth"
- "Incorporating [Document B] by reference"

**Example**:
```
Text: "This Agreement incorporates by reference all terms of the Master Services Agreement dated March 1, 2019."

Relationship:
{
  "source_entity_id": "entity_045",  // This Agreement
  "target_entity_id": "entity_062",  // Master Services Agreement
  "relationship_type": "INCORPORATES_BY_REFERENCE",
  "confidence": 0.96,
  "evidence_text": "This Agreement incorporates by reference all terms of the Master Services Agreement",
  "context_before": "",
  "context_after": "dated March 1, 2019."
}
```

#### 5.3 AMENDS
**Definition**: Document A amends or modifies Document B

**Extraction Patterns**:
- "[Document A] amends [Document B]"
- "Amendment to [Document B]"
- "[Document A] modifies [Document B]"
- "[Document B], as amended by [Document A]"

**Example**:
```
Text: "This First Amendment to Lease Agreement amends the Original Lease dated June 1, 2018."

Relationship:
{
  "source_entity_id": "entity_051",  // First Amendment
  "target_entity_id": "entity_038",  // Original Lease
  "relationship_type": "AMENDS",
  "confidence": 0.95,
  "evidence_text": "First Amendment to Lease Agreement amends the Original Lease",
  "context_before": "This",
  "context_after": "dated June 1, 2018."
}
```

#### 5.4 SUPERSEDES
**Definition**: Document A supersedes and replaces Document B

**Extraction Patterns**:
- "[Document A] supersedes [Document B]"
- "[Document A] replaces [Document B]"
- "[Document B] is superseded by [Document A]"
- "Superseding [Document B]"

**Example**:
```
Text: "This Restated Agreement supersedes and replaces all prior agreements between the parties."

Relationship:
{
  "source_entity_id": "entity_072",  // Restated Agreement
  "target_entity_id": "entity_059",  // Prior agreements
  "relationship_type": "SUPERSEDES",
  "confidence": 0.94,
  "evidence_text": "This Restated Agreement supersedes and replaces all prior agreements",
  "context_before": "",
  "context_after": "between the parties."
}
```

---

### 6. Contractual Relationships (4 types - Confidence: 0.85-0.95)

These relationships map commercial and contractual obligations between parties.

#### 6.1 CONTRACTS_WITH
**Definition**: Party A enters into a contract with Party B

**Extraction Patterns**:
- "[Party A] contracts with [Party B]"
- "[Party A] enters into agreement with [Party B]"
- "Contract between [Party A] and [Party B]"
- "[Party A] and [Party B] agree that..."

**Example**:
```
Text: "Acme Corporation entered into a Software Development Agreement with TechCo, Inc. on March 15, 2021."

Relationship:
{
  "source_entity_id": "entity_016",  // Acme Corporation
  "target_entity_id": "entity_029",  // TechCo, Inc.
  "relationship_type": "CONTRACTS_WITH",
  "confidence": 0.94,
  "evidence_text": "Acme Corporation entered into a Software Development Agreement with TechCo, Inc.",
  "context_before": "",
  "context_after": "on March 15, 2021."
}
```

#### 6.2 OBLIGATED_TO
**Definition**: Party A has a contractual obligation to Party B

**Extraction Patterns**:
- "[Party A] is obligated to [Party B]"
- "[Party A] shall [obligation] to [Party B]"
- "[Party A] agrees to provide [Party B] with..."
- "[Party A] owes [Party B]"

**Example**:
```
Text: "The Contractor is obligated to deliver the completed software to Client by December 31, 2023."

Relationship:
{
  "source_entity_id": "entity_033",  // Contractor
  "target_entity_id": "entity_048",  // Client
  "relationship_type": "OBLIGATED_TO",
  "confidence": 0.91,
  "evidence_text": "The Contractor is obligated to deliver the completed software to Client",
  "context_before": "",
  "context_after": "by December 31, 2023."
}
```

#### 6.3 BENEFITS
**Definition**: Party A receives benefits from a contractual provision or relationship

**Extraction Patterns**:
- "[Party A] benefits from [provision/relationship]"
- "[Provision] benefits [Party A]"
- "[Party A] receives [benefit]"
- "[Party A] is entitled to [benefit]"

**Example**:
```
text: "The indemnification clause benefits TechCo by protecting it from third-party claims arising from Acme's use of the software."

Relationship:
{
  "source_entity_id": "entity_029",  // TechCo
  "target_entity_id": "entity_065",  // Indemnification clause
  "relationship_type": "BENEFITS",
  "confidence": 0.89,
  "evidence_text": "The indemnification clause benefits TechCo by protecting it from third-party claims",
  "context_before": "",
  "context_after": "arising from Acme's use of the software."
}
```

#### 6.4 GUARANTEES
**Definition**: Party A guarantees an obligation of Party B

**Extraction Patterns**:
- "[Party A] guarantees [obligation] of [Party B]"
- "[Party A] provides guarantee for [Party B]"
- "[Party A] guaranties the obligations of [Party B]"
- "[Party A], as guarantor of [Party B]"

**Example**:
```
Text: "Parent Company guarantees all payment obligations of its subsidiary, Subsidiary Corp., under this Agreement."

Relationship:
{
  "source_entity_id": "entity_081",  // Parent Company
  "target_entity_id": "entity_092",  // Subsidiary Corp.
  "relationship_type": "GUARANTEES",
  "confidence": 0.96,
  "evidence_text": "Parent Company guarantees all payment obligations of its subsidiary, Subsidiary Corp.",
  "context_before": "",
  "context_after": "under this Agreement."
}
```

---

### 7. Judicial Relationships (6 types - Confidence: 0.90-0.95)

These relationships map judicial authorship, voting, and decision-making.

#### 7.1 DECIDED_BY
**Definition**: Case decided by specific judge or judicial panel

**Extraction Patterns**:
- "Decided by [Judge/Panel]"
- "[Judge] decided [Case]"
- "Before: [Judge A], [Judge B], [Judge C]"
- "[Case] heard by [Judge]"

**Example**:
```
Text: "This case was decided by a three-judge panel consisting of Circuit Judges Smith, Jones, and Williams."

Relationship:
{
  "source_entity_id": "entity_104",  // Case
  "target_entity_id": "entity_117",  // Panel
  "relationship_type": "DECIDED_BY",
  "confidence": 0.94,
  "evidence_text": "This case was decided by a three-judge panel consisting of Circuit Judges Smith, Jones, and Williams",
  "context_before": "",
  "context_after": ""
}
```

#### 7.2 AUTHORED_BY
**Definition**: Opinion authored by specific judge

**Extraction Patterns**:
- "[Judge], writing for the [Court/majority]"
- "Opinion by [Judge]"
- "[Judge] delivered the opinion of the Court"
- "[Judge], Circuit Judge, authored the majority opinion"

**Example**:
```
Text: "Chief Justice Roberts delivered the opinion of the Court, in which Justices Thomas, Alito, Gorsuch, Kavanaugh, and Barrett joined."

Relationship:
{
  "source_entity_id": "entity_128",  // Majority Opinion
  "target_entity_id": "entity_135",  // Chief Justice Roberts
  "relationship_type": "AUTHORED_BY",
  "confidence": 0.97,
  "evidence_text": "Chief Justice Roberts delivered the opinion of the Court",
  "context_before": "",
  "context_after": ", in which Justices Thomas, Alito, Gorsuch, Kavanaugh, and Barrett joined."
}
```

#### 7.3 JOINED_BY
**Definition**: Judge joined another judge's opinion

**Extraction Patterns**:
- "[Judge A], joined by [Judge B]"
- "[Judge B] joined [Judge A's] opinion"
- "Joining [Judge A]: [Judge B], [Judge C]"
- "[Judge A's] opinion, in which [Judge B] joined"

**Example**:
```
Text: "Justice Kagan's dissent, in which Justices Sotomayor and Jackson joined, argued for a different interpretation."

Relationship:
{
  "source_entity_id": "entity_142",  // Justice Sotomayor
  "target_entity_id": "entity_139",  // Justice Kagan's dissent
  "relationship_type": "JOINED_BY",
  "confidence": 0.95,
  "evidence_text": "Justice Kagan's dissent, in which Justices Sotomayor and Jackson joined",
  "context_before": "",
  "context_after": ", argued for a different interpretation."
}
```

#### 7.4 DISSENTED_BY
**Definition**: Judge authored or joined a dissenting opinion

**Extraction Patterns**:
- "[Judge] dissented"
- "[Judge] filed a dissenting opinion"
- "Dissent by [Judge]"
- "[Judge], dissenting"

**Example**:
```
Text: "Justice Breyer filed a dissenting opinion, arguing that the majority misapplied the constitutional standard."

Relationship:
{
  "source_entity_id": "entity_147",  // Dissenting Opinion
  "target_entity_id": "entity_151",  // Justice Breyer
  "relationship_type": "DISSENTED_BY",
  "confidence": 0.96,
  "evidence_text": "Justice Breyer filed a dissenting opinion",
  "context_before": "",
  "context_after": ", arguing that the majority misapplied the constitutional standard."
}
```

#### 7.5 CONCURRED_BY
**Definition**: Judge authored or joined a concurring opinion

**Extraction Patterns**:
- "[Judge] concurred"
- "[Judge] filed a concurring opinion"
- "Concurrence by [Judge]"
- "[Judge], concurring in the judgment"

**Example**:
```
Text: "Justice Thomas filed a concurring opinion, agreeing with the result but offering different reasoning."

Relationship:
{
  "source_entity_id": "entity_158",  // Concurring Opinion
  "target_entity_id": "entity_136",  // Justice Thomas
  "relationship_type": "CONCURRED_BY",
  "confidence": 0.95,
  "evidence_text": "Justice Thomas filed a concurring opinion",
  "context_before": "",
  "context_after": ", agreeing with the result but offering different reasoning."
}
```

#### 7.6 RECUSED_FROM
**Definition**: Judge recused from case participation

**Extraction Patterns**:
- "[Judge] recused [himself/herself] from [Case]"
- "[Judge] took no part in [Case]"
- "[Judge] recused due to [reason]"
- "[Case] heard without participation of [Judge]"

**Example**:
```
Text: "Justice Sotomayor recused herself from this case due to prior involvement while serving on the Second Circuit."

Relationship:
{
  "source_entity_id": "entity_142",  // Justice Sotomayor
  "target_entity_id": "entity_126",  // Case
  "relationship_type": "RECUSED_FROM",
  "confidence": 0.94,
  "evidence_text": "Justice Sotomayor recused herself from this case",
  "context_before": "",
  "context_after": "due to prior involvement while serving on the Second Circuit."
}
```

---

### 8. Temporal Relationships (3 types - Confidence: 0.80-0.90)

These relationships establish temporal ordering and chronology of legal events.

#### 8.1 OCCURRED_BEFORE
**Definition**: Event A occurred before Event B

**Extraction Patterns**:
- "[Event A] occurred before [Event B]"
- "Prior to [Event B], [Event A]..."
- "[Event A] preceded [Event B]"
- "Before [Event B], [Event A] took place"

**Example**:
```
Text: "The employment agreement was signed on January 15, 2020, before the first alleged discriminatory act on March 3, 2020."

Relationship:
{
  "source_entity_id": "entity_025",  // Agreement signing
  "target_entity_id": "entity_037",  // Discriminatory act
  "relationship_type": "OCCURRED_BEFORE",
  "confidence": 0.92,
  "evidence_text": "employment agreement was signed on January 15, 2020, before the first alleged discriminatory act on March 3, 2020",
  "context_before": "The",
  "context_after": ""
}
```

#### 8.2 OCCURRED_AFTER
**Definition**: Event A occurred after Event B

**Extraction Patterns**:
- "[Event A] occurred after [Event B]"
- "Following [Event B], [Event A]..."
- "[Event A] came after [Event B]"
- "After [Event B], [Event A] took place"

**Example**:
```
Text: "The plaintiff filed suit on June 1, 2021, after receiving a right-to-sue letter from the EEOC on May 15, 2021."

Relationship:
{
  "source_entity_id": "entity_044",  // Lawsuit filing
  "target_entity_id": "entity_039",  // Right-to-sue letter
  "relationship_type": "OCCURRED_AFTER",
  "confidence": 0.91,
  "evidence_text": "plaintiff filed suit on June 1, 2021, after receiving a right-to-sue letter from the EEOC on May 15, 2021",
  "context_before": "The",
  "context_after": ""
}
```

#### 8.3 OCCURRED_DURING
**Definition**: Event A occurred during time period B

**Extraction Patterns**:
- "[Event] occurred during [Time Period]"
- "During [Time Period], [Event]..."
- "[Event] took place during [Time Period]"
- "While [Time Period], [Event] occurred"

**Example**:
```
Text: "The alleged harassment occurred during the plaintiff's employment from January 2019 through December 2020."

Relationship:
{
  "source_entity_id": "entity_052",  // Harassment
  "target_entity_id": "entity_063",  // Employment period
  "relationship_type": "OCCURRED_DURING",
  "confidence": 0.88,
  "evidence_text": "alleged harassment occurred during the plaintiff's employment from January 2019 through December 2020",
  "context_before": "The",
  "context_after": ""
}
```

---

## Relationship Types for This Wave (34 types total)

**Case-to-Case (5)**: `CITES_CASE`, `OVERRULES_CASE`, `DISTINGUISHES_CASE`, `FOLLOWS_CASE`, `QUESTIONS_CASE`

**Statute (4)**: `CITES_STATUTE`, `INTERPRETS_STATUTE`, `APPLIES_STATUTE`, `INVALIDATES_STATUTE`

**Party (4)**: `PARTY_VS_PARTY`, `REPRESENTS`, `EMPLOYED_BY`, `MEMBER_OF`

**Procedural (4)**: `APPEALS_FROM`, `REMANDS_TO`, `CONSOLIDATES_WITH`, `RELATES_TO`

**Document (4)**: `REFERENCES_DOCUMENT`, `INCORPORATES_BY_REFERENCE`, `AMENDS`, `SUPERSEDES`

**Contractual (4)**: `CONTRACTS_WITH`, `OBLIGATED_TO`, `BENEFITS`, `GUARANTEES`

**Judicial (6)**: `DECIDED_BY`, `AUTHORED_BY`, `JOINED_BY`, `DISSENTED_BY`, `CONCURRED_BY`, `RECUSED_FROM`

**Temporal (3)**: `OCCURRED_BEFORE`, `OCCURRED_AFTER`, `OCCURRED_DURING`

---

## Pattern Examples for Relationship Extraction

The following patterns demonstrate common relationship extraction scenarios:

{{pattern_examples}}

---

## Previous Entities (Waves 1-3)

You MUST reference entities extracted in previous waves. All source and target entity IDs must exist in the following results:

{{previous_results}}

---

## ⚠️ CRITICAL: Wave 4 Relationship Extraction Rules

### 🚫 ERROR #1: Missing Entity Validation
**Both source and target MUST exist in Waves 1-3 results**

❌ **BAD EXAMPLE**:
```json
{
  "source_entity_id": "entity_999",  // Does not exist in previous_results
  "target_entity_id": "entity_042",
  "relationship_type": "CITES_CASE"
}
```

✅ **GOOD EXAMPLE**:
```json
// First verify entities exist in previous_results
// previous_results contains: entity_042 (Roe v. Wade), entity_018 (Griswold v. Connecticut)
{
  "source_entity_id": "entity_042",
  "target_entity_id": "entity_018",
  "relationship_type": "CITES_CASE"
}
```

**Validation Step**: Before creating relationship, check:
```python
assert source_entity_id in previous_results
assert target_entity_id in previous_results
```

---

### 🚫 ERROR #2: Speculative Relationships
**ALL relationships MUST have explicit text evidence - NO inference or assumption**

❌ **BAD EXAMPLE**:
```json
{
  "source_entity_id": "entity_007",  // John Smith
  "target_entity_id": "entity_015",  // Acme Corporation
  "relationship_type": "PARTY_VS_PARTY",
  "evidence_text": "John Smith and Acme Corporation"  // Too vague!
}
```

✅ **GOOD EXAMPLE**:
```json
{
  "source_entity_id": "entity_007",
  "target_entity_id": "entity_015",
  "relationship_type": "PARTY_VS_PARTY",
  "evidence_text": "John Smith brings this action against Acme Corporation for employment discrimination",
  "context_before": "",
  "context_after": "under Title VII of the Civil Rights Act."
}
```

**Required Evidence Markers**:
- **PARTY_VS_PARTY**: "v.", "versus", "against", "sued", "brings action"
- **CITES_CASE**: "cited", "citing", "relied on", "referenced"
- **REPRESENTS**: "represents", "counsel for", "attorney for"
- **APPEALS_FROM**: "appeal from", "on appeal from"

---

### 🚫 ERROR #3: Missing Context Evidence
**Every relationship MUST include text span evidence with context_before and context_after**

❌ **BAD EXAMPLE**:
```json
{
  "relationship_type": "OVERRULES_CASE",
  "evidence_text": "overrules",  // Too short!
  "context_before": "",  // Missing!
  "context_after": ""    // Missing!
}
```

✅ **GOOD EXAMPLE**:
```json
{
  "relationship_type": "OVERRULES_CASE",
  "evidence_text": "Dobbs v. Jackson Women's Health Organization expressly overrules Roe v. Wade",
  "context_before": "The Supreme Court held that",
  "context_after": "and Planned Parenthood v. Casey to the extent they recognized a constitutional right to abortion."
}
```

**Context Requirements**:
- **evidence_text**: Minimum 20 characters, must contain relationship indicator
- **context_before**: 20-100 characters of preceding text (empty string if at document start)
- **context_after**: 20-100 characters of following text (empty string if at document end)

---

### 🚫 ERROR #4: Weak Confidence Relationships
**Confidence threshold: 0.85 minimum - only extract relationships with strong textual evidence**

❌ **BAD EXAMPLE**:
```json
{
  "relationship_type": "QUESTIONS_CASE",
  "confidence": 0.65,  // Too low!
  "evidence_text": "Some scholars debate whether Lochner remains good law"
}
```

✅ **GOOD EXAMPLE**:
```json
{
  "relationship_type": "QUESTIONS_CASE",
  "confidence": 0.88,
  "evidence_text": "The majority opinion questions the reasoning in Lochner v. New York, suggesting its substantive due process analysis may no longer be sound"
}
```

**Confidence Scoring Guidelines**:
- **0.95-1.00**: Explicit relationship with clear legal language (e.g., "overrules", "incorporates by reference")
- **0.90-0.94**: Strong relationship with standard legal terminology (e.g., "cites", "represents")
- **0.85-0.89**: Clear relationship but less formal language (e.g., "relates to", "questions")
- **< 0.85**: DO NOT EXTRACT (insufficient evidence)

---

### 🚫 ERROR #5: Self-Referential Relationships
**Source and target MUST be different entities - no self-loops**

❌ **BAD EXAMPLE**:
```json
{
  "source_entity_id": "entity_042",  // Roe v. Wade
  "target_entity_id": "entity_042",  // Same entity!
  "relationship_type": "CITES_CASE"
}
```

✅ **GOOD EXAMPLE**:
```json
{
  "source_entity_id": "entity_042",  // Roe v. Wade
  "target_entity_id": "entity_018",  // Griswold v. Connecticut (different entity)
  "relationship_type": "CITES_CASE"
}
```

**Validation Check**:
```python
assert source_entity_id != target_entity_id, "Self-referential relationship detected"
```

---

### 🚫 ERROR #6: Duplicate Relationships
**Check for existing relationships before creating - avoid duplicates based on (source, relationship_type, target) tuple**

❌ **BAD EXAMPLE**:
```json
[
  {
    "id": "rel_1",
    "source_entity_id": "entity_042",
    "target_entity_id": "entity_018",
    "relationship_type": "CITES_CASE"
  },
  {
    "id": "rel_2",
    "source_entity_id": "entity_042",  // Duplicate!
    "target_entity_id": "entity_018",  // Same relationship
    "relationship_type": "CITES_CASE"  // Already exists
  }
]
```

✅ **GOOD EXAMPLE**:
```json
[
  {
    "id": "rel_1",
    "source_entity_id": "entity_042",
    "target_entity_id": "entity_018",
    "relationship_type": "CITES_CASE",
    "evidence_text": "Roe v. Wade cited Griswold v. Connecticut as establishing privacy rights"
  }
  // No duplicate - if same relationship appears multiple times in text,
  // keep the one with highest confidence or most detailed evidence_text
]
```

**Deduplication Strategy**:
1. Create unique key: `(source_entity_id, relationship_type, target_entity_id)`
2. If duplicate found, keep relationship with:
   - Higher confidence score, OR
   - More detailed evidence_text (longer, more specific)
3. Add occurrence count to metadata if relationship appears multiple times

**Metadata Enhancement for Duplicates**:
```json
{
  "id": "rel_1",
  "source_entity_id": "entity_042",
  "target_entity_id": "entity_018",
  "relationship_type": "CITES_CASE",
  "confidence": 0.95,
  "evidence_text": "Roe v. Wade extensively cited Griswold v. Connecticut",
  "metadata": {
    "occurrence_count": 3,  // Relationship appears 3 times in document
    "evidence_positions": [12450, 15780, 18920]  // Character positions
  }
}
```

---

## Output Schema

Return a JSON object with the following structure:

```json
{
  "relationships": [
    {
      "id": "rel_1",
      "source_entity_id": "entity_12",
      "target_entity_id": "entity_45",
      "relationship_type": "CITES_CASE",
      "confidence": 0.95,
      "evidence_text": "In Roe v. Wade, the Court cited Griswold v. Connecticut as precedent for privacy rights",
      "context_before": "The majority opinion thoroughly analyzed constitutional foundations.",
      "context_after": "This citation established the framework for the Court's analysis.",
      "metadata": {
        "evidence_start_pos": 12450,
        "evidence_end_pos": 12537,
        "wave_number": 4,
        "pattern_matched": "citation_relationship_pattern",
        "occurrence_count": 1,
        "relationship_category": "case_to_case"
      }
    },
    {
      "id": "rel_2",
      "source_entity_id": "entity_22",
      "target_entity_id": "entity_09",
      "relationship_type": "REPRESENTS",
      "confidence": 0.94,
      "evidence_text": "Sarah Johnson of Johnson & Associates represents the plaintiff, Mary Williams",
      "context_before": "Counsel for plaintiff appeared at the hearing.",
      "context_after": "Ms. Williams seeks damages for wrongful termination.",
      "metadata": {
        "evidence_start_pos": 8920,
        "evidence_end_pos": 8997,
        "wave_number": 4,
        "pattern_matched": "attorney_representation_pattern",
        "occurrence_count": 1,
        "relationship_category": "party"
      }
    },
    {
      "id": "rel_3",
      "source_entity_id": "entity_156",
      "target_entity_id": "entity_042",
      "relationship_type": "OVERRULES_CASE",
      "confidence": 0.98,
      "evidence_text": "Dobbs v. Jackson Women's Health Organization expressly overrules Roe v. Wade",
      "context_before": "The Supreme Court held that",
      "context_after": "to the extent it recognized a constitutional right to abortion.",
      "metadata": {
        "evidence_start_pos": 23100,
        "evidence_end_pos": 23176,
        "wave_number": 4,
        "pattern_matched": "overrules_relationship_pattern",
        "occurrence_count": 2,
        "relationship_category": "case_to_case"
      }
    }
  ],
  "metadata": {
    "wave": 4,
    "total_relationships": 23,
    "relationship_types_found": [
      "CITES_CASE",
      "REPRESENTS",
      "OVERRULES_CASE",
      "PARTY_VS_PARTY",
      "APPEALS_FROM",
      "DECIDED_BY"
    ],
    "relationship_categories": {
      "case_to_case": 8,
      "party": 6,
      "procedural": 4,
      "judicial": 3,
      "statute": 2
    },
    "entities_referenced": 45,
    "average_confidence": 0.92,
    "confidence_distribution": {
      "0.95-1.00": 8,
      "0.90-0.94": 11,
      "0.85-0.89": 4
    },
    "validation_passed": true,
    "errors_detected": 0
  }
}
```

### Field Descriptions

#### Relationship Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique relationship identifier (e.g., "rel_1", "rel_2") |
| `source_entity_id` | string | Yes | ID of source entity (must exist in Waves 1-3 results) |
| `target_entity_id` | string | Yes | ID of target entity (must exist in Waves 1-3 results) |
| `relationship_type` | string | Yes | One of 34 defined relationship types (see list above) |
| `confidence` | float | Yes | Confidence score (0.85-1.00 range) |
| `evidence_text` | string | Yes | Text span showing the relationship (20+ characters) |
| `context_before` | string | Yes | Text preceding evidence (20-100 chars, or empty if at doc start) |
| `context_after` | string | Yes | Text following evidence (20-100 chars, or empty if at doc end) |
| `metadata` | object | Yes | Additional metadata about the relationship |

#### Metadata Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `evidence_start_pos` | integer | Yes | Character position where evidence_text starts |
| `evidence_end_pos` | integer | Yes | Character position where evidence_text ends |
| `wave_number` | integer | Yes | Always 4 for this wave |
| `pattern_matched` | string | Yes | Name of extraction pattern that matched |
| `occurrence_count` | integer | No | Number of times this relationship appears (default: 1) |
| `relationship_category` | string | Yes | Category: case_to_case, statute, party, procedural, document, contractual, judicial, temporal |

#### Top-Level Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `wave` | integer | Wave number (4) |
| `total_relationships` | integer | Total number of relationships extracted |
| `relationship_types_found` | array | List of relationship types found in document |
| `relationship_categories` | object | Count of relationships per category |
| `entities_referenced` | integer | Number of unique entities involved in relationships |
| `average_confidence` | float | Mean confidence score across all relationships |
| `confidence_distribution` | object | Count of relationships in each confidence band |
| `validation_passed` | boolean | Whether all validation checks passed |
| `errors_detected` | integer | Number of validation errors (should be 0) |

---

## Validation Checklist

Before returning results, verify ALL of the following:

- [ ] **Entity Validation**: All `source_entity_id` values exist in `previous_results` (Waves 1-3)
- [ ] **Entity Validation**: All `target_entity_id` values exist in `previous_results` (Waves 1-3)
- [ ] **Evidence Quality**: Every relationship has `evidence_text` with 20+ characters
- [ ] **Context Quality**: Every relationship has `context_before` and `context_after` (or empty string if at document boundary)
- [ ] **Confidence Threshold**: All relationships have `confidence` ≥ 0.85
- [ ] **No Self-Loops**: No relationship has `source_entity_id` == `target_entity_id`
- [ ] **No Duplicates**: No duplicate relationships based on `(source_entity_id, relationship_type, target_entity_id)` tuple
- [ ] **Wave Metadata**: All relationships have `metadata.wave_number: 4`
- [ ] **Type Validation**: All `relationship_type` values are one of the 34 defined types
- [ ] **Position Data**: All relationships include `evidence_start_pos` and `evidence_end_pos` in metadata
- [ ] **Category Assignment**: All relationships have valid `relationship_category` in metadata
- [ ] **Aggregate Metadata**: Top-level metadata includes accurate counts and statistics

### Validation Error Handling

If validation fails, include error details in output:

```json
{
  "relationships": [...],
  "metadata": {
    "wave": 4,
    "validation_passed": false,
    "errors_detected": 2,
    "validation_errors": [
      {
        "error_type": "MISSING_ENTITY",
        "relationship_id": "rel_5",
        "details": "source_entity_id 'entity_999' not found in previous_results"
      },
      {
        "error_type": "LOW_CONFIDENCE",
        "relationship_id": "rel_12",
        "details": "confidence 0.72 below minimum threshold 0.85"
      }
    ]
  }
}
```

**Error Types**:
- `MISSING_ENTITY`: Source or target entity not in previous_results
- `LOW_CONFIDENCE`: Confidence below 0.85 threshold
- `MISSING_EVIDENCE`: Evidence text missing or too short (< 20 chars)
- `MISSING_CONTEXT`: Context before/after missing when not at document boundary
- `SELF_REFERENTIAL`: Source and target are the same entity
- `DUPLICATE_RELATIONSHIP`: Duplicate (source, type, target) tuple
- `INVALID_TYPE`: Relationship type not in 34 defined types
- `MISSING_METADATA`: Required metadata field missing

---

## Example: Complete Wave 4 Extraction

**Input Document Excerpt**:
```
In Dobbs v. Jackson Women's Health Organization (2022), the Supreme Court
expressly overruled Roe v. Wade (1973) and Planned Parenthood v. Casey (1992).
Justice Alito authored the majority opinion, in which Chief Justice Roberts,
Justices Thomas, Gorsuch, Kavanaugh, and Barrett joined. The case came to
the Court on appeal from the Fifth Circuit Court of Appeals, which had upheld
Mississippi's Gestational Age Act. Justice Breyer filed a dissenting opinion,
joined by Justices Sotomayor and Kagan, arguing that the majority's decision
contravened decades of precedent.
```

**Previous Results (Waves 1-3)** - Simplified:
```json
{
  "entities": [
    {"id": "entity_001", "text": "Dobbs v. Jackson Women's Health Organization", "type": "CASE_CITATION"},
    {"id": "entity_002", "text": "Roe v. Wade", "type": "CASE_CITATION"},
    {"id": "entity_003", "text": "Planned Parenthood v. Casey", "type": "CASE_CITATION"},
    {"id": "entity_004", "text": "Justice Alito", "type": "JUDGE"},
    {"id": "entity_005", "text": "Chief Justice Roberts", "type": "JUDGE"},
    {"id": "entity_006", "text": "Fifth Circuit Court of Appeals", "type": "COURT"},
    {"id": "entity_007", "text": "Justice Breyer", "type": "JUDGE"},
    {"id": "entity_008", "text": "majority opinion", "type": "JUDICIAL_OPINION"},
    {"id": "entity_009", "text": "dissenting opinion", "type": "JUDICIAL_OPINION"}
  ]
}
```

**Wave 4 Output**:
```json
{
  "relationships": [
    {
      "id": "rel_1",
      "source_entity_id": "entity_001",
      "target_entity_id": "entity_002",
      "relationship_type": "OVERRULES_CASE",
      "confidence": 0.98,
      "evidence_text": "the Supreme Court expressly overruled Roe v. Wade (1973)",
      "context_before": "In Dobbs v. Jackson Women's Health Organization (2022),",
      "context_after": "and Planned Parenthood v. Casey (1992).",
      "metadata": {
        "evidence_start_pos": 56,
        "evidence_end_pos": 112,
        "wave_number": 4,
        "pattern_matched": "overrules_explicit_pattern",
        "occurrence_count": 1,
        "relationship_category": "case_to_case"
      }
    },
    {
      "id": "rel_2",
      "source_entity_id": "entity_001",
      "target_entity_id": "entity_003",
      "relationship_type": "OVERRULES_CASE",
      "confidence": 0.98,
      "evidence_text": "expressly overruled Roe v. Wade (1973) and Planned Parenthood v. Casey (1992)",
      "context_before": "In Dobbs v. Jackson Women's Health Organization (2022), the Supreme Court",
      "context_after": ". Justice Alito authored the majority opinion",
      "metadata": {
        "evidence_start_pos": 75,
        "evidence_end_pos": 153,
        "wave_number": 4,
        "pattern_matched": "overrules_explicit_pattern",
        "occurrence_count": 1,
        "relationship_category": "case_to_case"
      }
    },
    {
      "id": "rel_3",
      "source_entity_id": "entity_008",
      "target_entity_id": "entity_004",
      "relationship_type": "AUTHORED_BY",
      "confidence": 0.97,
      "evidence_text": "Justice Alito authored the majority opinion",
      "context_before": "and Planned Parenthood v. Casey (1992).",
      "context_after": ", in which Chief Justice Roberts, Justices Thomas, Gorsuch, Kavanaugh, and Barrett joined.",
      "metadata": {
        "evidence_start_pos": 155,
        "evidence_end_pos": 198,
        "wave_number": 4,
        "pattern_matched": "opinion_authorship_pattern",
        "occurrence_count": 1,
        "relationship_category": "judicial"
      }
    },
    {
      "id": "rel_4",
      "source_entity_id": "entity_005",
      "target_entity_id": "entity_008",
      "relationship_type": "JOINED_BY",
      "confidence": 0.95,
      "evidence_text": "in which Chief Justice Roberts, Justices Thomas, Gorsuch, Kavanaugh, and Barrett joined",
      "context_before": "Justice Alito authored the majority opinion,",
      "context_after": ". The case came to the Court on appeal",
      "metadata": {
        "evidence_start_pos": 200,
        "evidence_end_pos": 288,
        "wave_number": 4,
        "pattern_matched": "joined_opinion_pattern",
        "occurrence_count": 1,
        "relationship_category": "judicial"
      }
    },
    {
      "id": "rel_5",
      "source_entity_id": "entity_001",
      "target_entity_id": "entity_006",
      "relationship_type": "APPEALS_FROM",
      "confidence": 0.94,
      "evidence_text": "The case came to the Court on appeal from the Fifth Circuit Court of Appeals",
      "context_before": "Justices Thomas, Gorsuch, Kavanaugh, and Barrett joined.",
      "context_after": ", which had upheld Mississippi's Gestational Age Act.",
      "metadata": {
        "evidence_start_pos": 290,
        "evidence_end_pos": 366,
        "wave_number": 4,
        "pattern_matched": "appeal_from_pattern",
        "occurrence_count": 1,
        "relationship_category": "procedural"
      }
    },
    {
      "id": "rel_6",
      "source_entity_id": "entity_009",
      "target_entity_id": "entity_007",
      "relationship_type": "DISSENTED_BY",
      "confidence": 0.96,
      "evidence_text": "Justice Breyer filed a dissenting opinion",
      "context_before": "which had upheld Mississippi's Gestational Age Act.",
      "context_after": ", joined by Justices Sotomayor and Kagan",
      "metadata": {
        "evidence_start_pos": 420,
        "evidence_end_pos": 461,
        "wave_number": 4,
        "pattern_matched": "dissent_authorship_pattern",
        "occurrence_count": 1,
        "relationship_category": "judicial"
      }
    }
  ],
  "metadata": {
    "wave": 4,
    "total_relationships": 6,
    "relationship_types_found": [
      "OVERRULES_CASE",
      "AUTHORED_BY",
      "JOINED_BY",
      "APPEALS_FROM",
      "DISSENTED_BY"
    ],
    "relationship_categories": {
      "case_to_case": 2,
      "judicial": 3,
      "procedural": 1
    },
    "entities_referenced": 7,
    "average_confidence": 0.96,
    "confidence_distribution": {
      "0.95-1.00": 5,
      "0.90-0.94": 1,
      "0.85-0.89": 0
    },
    "validation_passed": true,
    "errors_detected": 0
  }
}
```

---

## Best Practices for Wave 4 Extraction

### 1. Entity Reference Verification
Always verify entities exist before creating relationships:
```
1. Load all entity IDs from previous_results into set
2. For each potential relationship:
   a. Check if source_entity_id in entity_set
   b. Check if target_entity_id in entity_set
   c. Only proceed if both exist
```

### 2. Evidence Quality Control
Ensure evidence is specific and verifiable:
- **Good Evidence**: "Justice Alito authored the majority opinion in Dobbs v. Jackson"
- **Poor Evidence**: "Alito opinion" (too vague)
- **Good Evidence**: "The Court expressly overruled Roe v. Wade"
- **Poor Evidence**: "overruled" (missing entities)

### 3. Confidence Scoring Consistency
Apply consistent confidence scoring:
- Explicit legal language (overrules, incorporates) → 0.95-0.98
- Standard legal terminology (cites, represents) → 0.90-0.94
- Clear but informal language (relates to, questions) → 0.85-0.89

### 4. Context Window Selection
Choose meaningful context windows:
- Include enough context to show relationship nature
- Avoid overly long context (100 char maximum)
- Prefer sentence boundaries when possible

### 5. Deduplication Strategy
Handle duplicate relationships intelligently:
- Track occurrence count if relationship appears multiple times
- Keep relationship with strongest evidence
- Maintain all evidence positions in metadata

### 6. Relationship Type Selection
Choose most specific relationship type:
- **OVERRULES_CASE** (not CITES_CASE) when explicit overruling language present
- **INCORPORATES_BY_REFERENCE** (not REFERENCES_DOCUMENT) when legal incorporation present
- **AUTHORED_BY** (not DECIDED_BY) when specific authorship identified

---

## Performance Optimization Tips

1. **Batch Entity Lookups**: Load all Waves 1-3 entities into memory once
2. **Pattern Caching**: Compile regex patterns once, reuse for all extractions
3. **Confidence Pre-filtering**: Skip relationship candidates with weak evidence early
4. **Position Tracking**: Maintain character position index to avoid re-scanning text
5. **Parallel Processing**: Extract different relationship categories in parallel when possible

---

## GraphRAG Integration

Wave 4 relationships directly support GraphRAG knowledge graph construction:

**Knowledge Graph Schema**:
- **Nodes**: Entities from Waves 1-3 (161 types)
- **Edges**: Relationships from Wave 4 (34 types)
- **Properties**: Entity metadata, relationship confidence, evidence text

**Query Examples**:
```cypher
// Find all cases cited by Roe v. Wade
MATCH (roe:Case {name: "Roe v. Wade"})-[r:CITES_CASE]->(cited:Case)
RETURN cited.name, r.confidence, r.evidence_text

// Find judge authorship patterns
MATCH (judge:Judge)-[r:AUTHORED_BY]->(opinion:Opinion)
RETURN judge.name, COUNT(opinion) as opinion_count

// Trace case law evolution
MATCH path = (newer:Case)-[:OVERRULES_CASE|FOLLOWS_CASE*1..5]->(older:Case)
RETURN path
```

---

## Troubleshooting

### Common Issues and Solutions

**Issue**: High number of MISSING_ENTITY errors
**Solution**: Verify previous_results format and entity ID consistency

**Issue**: Low confidence scores across all relationships
**Solution**: Review extraction patterns and evidence text quality

**Issue**: Many duplicate relationships
**Solution**: Implement deduplication before returning results

**Issue**: Missing context for relationships at document boundaries
**Solution**: Use empty string for context_before/after when at document start/end

**Issue**: Relationship type confusion (e.g., CITES_CASE vs FOLLOWS_CASE)
**Solution**: Review relationship type definitions and evidence requirements

---

## Summary

Wave 4 completes the entity extraction pipeline by creating a rich knowledge graph connecting entities from Waves 1-3. The 34 relationship types cover all major legal relationship categories, enabling powerful GraphRAG-based semantic search, precedent analysis, and legal reasoning chains.

**Success Criteria**:
- ✓ All relationships validated against Waves 1-3 entities
- ✓ Strong text evidence for every relationship (confidence ≥ 0.85)
- ✓ No self-referential or duplicate relationships
- ✓ Complete metadata for GraphRAG integration
- ✓ Comprehensive context spans for human review

**Next Steps**: Wave 4 output feeds directly into GraphRAG service for knowledge graph construction and semantic query capabilities.
