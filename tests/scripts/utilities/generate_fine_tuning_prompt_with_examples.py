#!/usr/bin/env python3
"""
Generate SaulLM Fine-Tuning Prompt with Real Examples

This script creates a comprehensive fine-tuning prompt that includes
all 219 entity types with their actual examples from the pattern system.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def load_training_data() -> Dict[str, Any]:
    """Load the training data summary with examples."""
    summary_file = Path(__file__).parent / "training_data_summary.json"
    with open(summary_file, 'r') as f:
        return json.load(f)

def format_entity_examples(entity_types_with_examples: Dict[str, Any]) -> str:
    """Format entity types with their examples."""
    output = []
    
    # Group entity types by domain
    domains = {
        'Courts and Judicial Officers': [],
        'Legal Professionals': [],
        'Parties and Participants': [],
        'Legal Authority and Citations': [],
        'Case Citations': [],
        'Courts and Jurisdictions': [],
        'Legal Documents and Filings': [],
        'Procedural Elements': [],
        'Evidence and Testimony': [],
        'Financial and Damages': [],
        'Criminal Law': [],
        'Legal Concepts and Standards': [],
        'Organizations and Entities': [],
        'Intellectual Property': [],
        'Geographic and Personal': [],
        'Dates and Time': [],
        'Case Management': [],
        'Relief and Remedies': [],
        'Specialized Citations': [],
        'Miscellaneous Legal': []
    }
    
    # Categorize entity types
    for entity_type in entity_types_with_examples.keys():
        entity_lower = entity_type.lower()
        
        if any(term in entity_lower for term in ['court', 'judge', 'magistrate', 'justice', 'arbitrator', 'mediator']):
            domains['Courts and Judicial Officers'].append(entity_type)
        elif any(term in entity_lower for term in ['attorney', 'law_firm', 'prosecutor', 'counsel', 'paralegal', 'legal_secretary', 'law_clerk']):
            domains['Legal Professionals'].append(entity_type)
        elif any(term in entity_lower for term in ['party', 'plaintiff', 'defendant', 'third_party', 'class_representative']):
            domains['Parties and Participants'].append(entity_type)
        elif any(term in entity_lower for term in ['statute', 'regulation', 'constitutional', 'treaty', 'executive_order', 'administrative_code', 'legal_rule', 'ordinance']):
            domains['Legal Authority and Citations'].append(entity_type)
        elif any(term in entity_lower for term in ['case_citation', 'usc_citation', 'cfr_citation', 'electronic_citation', 'pinpoint_citation', 'short_form']):
            domains['Case Citations'].append(entity_type)
        elif any(term in entity_lower for term in ['federal_court', 'state_court', 'specialized_court', 'circuit', 'district', 'division', 'jurisdiction', 'venue', 'forum']):
            domains['Courts and Jurisdictions'].append(entity_type)
        elif any(term in entity_lower for term in ['complaint', 'brief', 'order', 'discovery', 'answer', 'counterclaim', 'motion', 'document', 'filing']):
            domains['Legal Documents and Filings'].append(entity_type)
        elif any(term in entity_lower for term in ['appeal', 'certiorari', 'class_action', 'plea', 'settlement', 'civil_procedure', 'criminal_procedure']):
            domains['Procedural Elements'].append(entity_type)
        elif any(term in entity_lower for term in ['evidence', 'testimony', 'affidavit', 'transcript', 'exhibit', 'witness', 'hearsay']):
            domains['Evidence and Testimony'].append(entity_type)
        elif any(term in entity_lower for term in ['monetary', 'settlement_amount', 'judgment', 'penalty', 'award', 'compensation', 'damages', 'fee']):
            domains['Financial and Damages'].append(entity_type)
        elif any(term in entity_lower for term in ['charges', 'sentence', 'conviction', 'acquittal', 'parole', 'probation', 'offense', 'felony', 'misdemeanor']):
            domains['Criminal Law'].append(entity_type)
        elif any(term in entity_lower for term in ['legal_doctrine', 'legal_standard', 'legal_test', 'burden_of_proof', 'constitutional_amendment', 'due_process']):
            domains['Legal Concepts and Standards'].append(entity_type)
        elif any(term in entity_lower for term in ['organization', 'agency', 'regulatory_body', 'legislative_body', 'law_enforcement', 'llc', 'partnership', 'nonprofit']):
            domains['Organizations and Entities'].append(entity_type)
        elif any(term in entity_lower for term in ['patent', 'trademark', 'copyright', 'trade_secret']):
            domains['Intellectual Property'].append(entity_type)
        elif any(term in entity_lower for term in ['city', 'state', 'county', 'country', 'person', 'address', 'phone', 'email', 'url']):
            domains['Geographic and Personal'].append(entity_type)
        elif any(term in entity_lower for term in ['date', 'expiration', 'service_date', 'hearing_date', 'trial_date', 'statute_of_limitations']):
            domains['Dates and Time'].append(entity_type)
        elif any(term in entity_lower for term in ['case_number', 'docket', 'case_caption', 'case_title', 'case_status', 'case_type', 'filing', 'hearing', 'proceeding']):
            domains['Case Management'].append(entity_type)
        elif any(term in entity_lower for term in ['remedy', 'relief', 'declaratory', 'equitable', 'injunction', 'cause_of_action', 'claim', 'defense']):
            domains['Relief and Remedies'].append(entity_type)
        elif any(term in entity_lower for term in ['usc_titles', 'cfr_titles', 'federal_rules', 'latin_term', 'legal_marker', 'section_']):
            domains['Specialized Citations'].append(entity_type)
        else:
            domains['Miscellaneous Legal'].append(entity_type)
    
    # Generate output for each domain
    for domain, entity_types in domains.items():
        if entity_types:
            output.append(f"\n### {domain}\n")
            
            for entity_type in sorted(entity_types):
                if entity_type in entity_types_with_examples:
                    info = entity_types_with_examples[entity_type]
                    examples = info['examples']
                    description = info.get('description', '')
                    
                    output.append(f"#### **{entity_type}**")
                    output.append(f"*{description}*\n")
                    output.append(f"**Examples ({len(examples)} total):**")
                    
                    # Show first 5 examples
                    for i, example in enumerate(examples[:5]):
                        output.append(f"- \"{example}\"")
                    
                    if len(examples) > 5:
                        output.append(f"- *(and {len(examples) - 5} more examples)*")
                    
                    output.append("")  # Empty line
    
    return "\n".join(output)

def generate_comprehensive_prompt() -> str:
    """Generate the comprehensive fine-tuning prompt with examples."""
    
    # Load training data
    training_data = load_training_data()
    entity_types_with_examples = training_data["entity_types_with_examples"]
    
    # Format entity examples
    entity_examples_section = format_entity_examples(entity_types_with_examples)
    
    # Build the complete prompt
    prompt = f"""# SaulLM Fine-Tuning Prompt for Legal Entity Extraction and Relationship Detection

## System Instructions

You are a specialized legal entity extraction and relationship detection system based on SaulLM (Legal Language Model). Your task is to analyze legal documents and extract entities while detecting relationships between them. Return results in the LurisEntityV2 structure format.

## Primary Objectives

1. **Entity Extraction**: Identify and extract ALL legal entities with high precision and recall
2. **Relationship Detection**: Discover and map relationships between extracted entities
3. **Structured Output**: Return data in LurisEntityV2 compliant JSON format
4. **Legal Accuracy**: Maintain domain-specific accuracy for legal terminology and concepts

## Training Data Overview

- **Total Entity Types**: {training_data['total_training_ready_types']}
- **Total Examples**: {training_data['total_examples']}
- **Top Priority Types**: {', '.join(training_data['recommended_for_immediate_training'][:10])}

## Entity Types with Examples ({training_data['total_training_ready_types']} Types)

{entity_examples_section}

## Relationship Types

### Primary Relationships
- **ATTORNEY_REPRESENTS**: Attorney-client representation
- **ATTORNEY_WORKS_FOR**: Attorney-law firm employment
- **COUNSEL_FOR**: Legal counsel designation
- **APPEARING_FOR**: Court appearance representation
- **PARTY_V_PARTY**: Adversarial party relationships
- **PLAINTIFF_V_DEFENDANT**: Civil litigation parties
- **APPELLANT_V_APPELLEE**: Appellate parties
- **PETITIONER_V_RESPONDENT**: Petition parties

### Court Relationships
- **DECIDED_BY**: Case decided by court/judge
- **JUDGE_PRESIDING**: Judge presiding over case
- **COURT_JURISDICTION**: Court jurisdictional authority
- **APPEAL_FROM**: Appellate court relationship
- **REMAND_TO**: Case remanded to lower court

### Citation Relationships
- **CITES**: Legal authority citation
- **CITED_BY**: Reverse citation relationship
- **DISTINGUISHES**: Case distinction
- **FOLLOWS**: Precedent following
- **OVERRULES**: Precedent overruling
- **SUPERSEDES**: Authority supersession

### Document Relationships
- **FILED_IN**: Document filed in case
- **ATTACHED_TO**: Exhibit attachment
- **INCORPORATED_BY**: Document incorporation
- **REFERENCES**: Document cross-reference
- **AMENDS**: Document amendment

### Entity Relationships
- **MEMBER_OF**: Organization membership
- **SUBSIDIARY_OF**: Corporate relationships
- **PARTNER_IN**: Partnership relationships
- **OWNS**: Ownership relationships
- **CONTROLS**: Control relationships

### Temporal Relationships
- **BEFORE**: Temporal precedence
- **AFTER**: Temporal sequence
- **DURING**: Temporal overlap
- **EXPIRES**: Expiration relationship
- **EFFECTIVE**: Effective date relationship

### Legal Relationships
- **VIOLATES**: Legal violation
- **COMPLIES_WITH**: Legal compliance
- **GOVERNED_BY**: Governing authority
- **SUBJECT_TO**: Legal subjection
- **PURSUANT_TO**: Legal authorization

## Output Format: LurisEntityV2 Structure

```json
{{
  "entities": [
    {{
      "entity_id": "unique_identifier",
      "text": "exact_extracted_text",
      "entity_type": "ENTITY_TYPE_FROM_ABOVE",
      "start_position": 123,
      "end_position": 145,
      "confidence": 0.95,
      "context": "surrounding_context_text",
      "metadata": {{
        "pattern_matched": "pattern_name",
        "jurisdiction": "federal|state|local",
        "court_level": "supreme|appellate|district|trial",
        "citation_type": "primary|secondary|parallel",
        "legal_domain": "civil|criminal|administrative|constitutional"
      }}
    }}
  ],
  "relationships": [
    {{
      "relationship_id": "unique_identifier",
      "source_entity_id": "entity_1_id",
      "target_entity_id": "entity_2_id",
      "relationship_type": "RELATIONSHIP_TYPE_FROM_ABOVE",
      "confidence": 0.88,
      "evidence": "textual_evidence_for_relationship",
      "metadata": {{
        "relationship_strength": "strong|moderate|weak",
        "temporal_aspect": "past|present|future",
        "legal_significance": "high|medium|low"
      }}
    }}
  ],
  "summary": {{
    "total_entities": 25,
    "total_relationships": 15,
    "primary_entity_types": ["CASE_CITATION", "JUDGE", "ATTORNEY"],
    "document_type": "court_opinion|brief|motion|contract|statute",
    "legal_domain": "civil_rights|contract|criminal|constitutional",
    "jurisdiction": "federal|state|local",
    "processing_metadata": {{
      "model_version": "SaulLM-7B-Instruct-v1",
      "extraction_timestamp": "ISO_timestamp",
      "confidence_threshold": 0.7
    }}
  }}
}}
```

## Extraction Instructions

### Entity Extraction Guidelines

1. **Precision**: Extract only entities that clearly match the defined types and examples
2. **Completeness**: Identify ALL occurrences of target entity types
3. **Context**: Include sufficient context for entity disambiguation
4. **Confidence**: Assign realistic confidence scores (0.0-1.0)
5. **Positioning**: Provide exact character positions in source text
6. **Metadata**: Include relevant legal metadata for enhanced analysis

### Relationship Detection Guidelines

1. **Evidence-Based**: Only extract relationships with textual evidence
2. **Legal Significance**: Focus on legally meaningful relationships
3. **Directionality**: Properly identify source and target entities
4. **Confidence**: Score relationship confidence based on evidence clarity
5. **Completeness**: Identify all explicit and reasonably implied relationships

### Confidence Scoring

- **0.95-1.0**: Explicit, unambiguous matches with clear legal significance
- **0.85-0.94**: Clear matches with minor ambiguity
- **0.75-0.84**: Good matches with some uncertainty
- **0.70-0.74**: Threshold matches requiring human review
- **Below 0.70**: Exclude from results

### Quality Standards

1. **Legal Accuracy**: Maintain precision for legal terminology
2. **Bluebook Compliance**: Follow legal citation standards
3. **Jurisdictional Awareness**: Respect federal/state/local distinctions
4. **Temporal Accuracy**: Correctly identify dates and temporal relationships
5. **Hierarchical Understanding**: Recognize court hierarchies and authority levels

## Example Analysis

### Input Text Sample
```
"In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held that segregation violated the Equal Protection Clause. The plaintiff, represented by Thurgood Marshall of the NAACP Legal Defense Fund, argued successfully before Chief Justice Warren."
```

### Expected Output Structure
```json
{{
  "entities": [
    {{
      "entity_id": "case_001",
      "text": "Brown v. Board of Education, 347 U.S. 483 (1954)",
      "entity_type": "CASE_CITATION",
      "start_position": 3,
      "end_position": 52,
      "confidence": 0.98,
      "context": "In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held",
      "metadata": {{
        "citation_type": "primary",
        "court_level": "supreme",
        "jurisdiction": "federal"
      }}
    }},
    {{
      "entity_id": "attorney_001", 
      "text": "Thurgood Marshall",
      "entity_type": "ATTORNEY",
      "start_position": 165,
      "end_position": 182,
      "confidence": 0.96,
      "context": "represented by Thurgood Marshall of the NAACP Legal Defense Fund",
      "metadata": {{
        "legal_domain": "civil_rights"
      }}
    }}
  ],
  "relationships": [
    {{
      "relationship_id": "rel_001",
      "source_entity_id": "attorney_001",
      "target_entity_id": "party_001", 
      "relationship_type": "ATTORNEY_REPRESENTS",
      "confidence": 0.94,
      "evidence": "represented by Thurgood Marshall",
      "metadata": {{
        "relationship_strength": "strong"
      }}
    }}
  ]
}}
```

## Processing Instructions

1. **Chunk Processing**: Process documents in manageable chunks (4000 characters max)
2. **Cross-Chunk Relationships**: Identify relationships spanning chunk boundaries
3. **Deduplication**: Eliminate duplicate entities across chunks
4. **Consistency**: Maintain consistent entity identification across chunks
5. **Aggregation**: Combine chunk results into coherent document analysis

## Model Specific Instructions

- **Temperature**: Use 0.1 for consistent, precise extraction
- **Max Tokens**: Limit to 2048 tokens for focused responses
- **Stop Sequences**: Use appropriate JSON delimiters
- **Repetition Penalty**: Apply 1.1 to prevent repetitive outputs
- **Top-p**: Use 0.95 for balanced creativity and precision

## Error Handling

1. **Malformed JSON**: Return valid JSON even if extraction is incomplete
2. **Missing Entities**: Include summary of potential missed entities
3. **Low Confidence**: Flag entities below confidence threshold
4. **Ambiguous Relationships**: Note ambiguous relationships in metadata
5. **Processing Errors**: Include error details in processing metadata

---

**This prompt is optimized for SaulLM fine-tuning to achieve maximum accuracy in legal entity extraction and relationship detection while maintaining compliance with LurisEntityV2 structure requirements.**

**Training Data Sources**: {training_data['total_training_ready_types']} entity types with {training_data['total_examples']} real examples from legal document patterns, comprehensive relationship detection framework, and LurisEntityV2 structure compliance."""

    return prompt

def main():
    """Generate and save the comprehensive prompt."""
    print("🔄 Generating comprehensive fine-tuning prompt with examples...")
    
    try:
        # Generate the prompt
        prompt = generate_comprehensive_prompt()
        
        # Save the new prompt
        output_file = Path(__file__).parent / "src" / "prompts" / "saullm_fine_tuning_prompt_with_examples.md"
        with open(output_file, 'w') as f:
            f.write(prompt)
        
        print(f"✅ Comprehensive prompt generated successfully!")
        print(f"📁 Saved to: {output_file}")
        print(f"📊 Prompt size: {len(prompt):,} characters")
        print(f"📝 Includes all 219 entity types with real examples")
        print(f"🎯 Ready for SaulLM fine-tuning!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating prompt: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)