#!/usr/bin/env python3
"""
Improved inference script for fine-tuned SaulLM model with proper prompt formatting
that matches the training data structure exactly.
"""

import json
import time
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import logging
from datetime import datetime
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedFineTunedInference:
    def __init__(self, base_model_name="Equall/Saul-7B-Instruct-v1", 
                 adapter_path="./fine_tuned_saullm_legal"):
        """Initialize the improved fine-tuned model inference."""
        self.base_model_name = base_model_name
        self.adapter_path = adapter_path
        self.model = None
        self.tokenizer = None
        
        # Define all 219 entity types from training data
        self.entity_types = [
            # Courts and Judicial Officers
            "ARBITRATOR", "COURT", "COURT_CLERK", "COURT_REPORTER", 
            "ENHANCED_COURT_PATTERNS", "FEDERAL_COURTS", "JUDGE", 
            "MAGISTRATE", "MEDIATOR", "SPECIALIZED_COURTS", 
            "SPECIALIZED_COURT_CITATIONS", "STATE_COURTS",
            
            # Legal Professionals
            "ATTORNEY", "CORPORATE_COUNSEL", "GOVERNMENT_ATTORNEY", 
            "LAW_CLERK", "LAW_FIRM", "LEGAL_AID_ATTORNEY", 
            "LEGAL_SECRETARY", "PARALEGAL", "PROSECUTOR",
            
            # Parties and Participants
            "CLASS_REPRESENTATIVE", "DEFENDANT", "ENHANCED_PARTY_PATTERNS",
            "INDIVIDUAL_PARTY", "PARTY", "PLAINTIFF", "THIRD_PARTY",
            
            # Legal Authority and Citations
            "ADMINISTRATIVE_CODE", "CONSTITUTIONAL_AMENDMENT", 
            "CONSTITUTIONAL_PROVISION", "EXECUTIVE_ORDER", "LEGAL_RULE",
            "ORDINANCE", "REGULATION", "REGULATION_CITATION", 
            "STATE_REGULATION_CITATION", "STATE_STATUTES", 
            "STATE_STATUTE_CITATION", "STATUTE", "STATUTE_CITATION",
            "STATUTE_OF_LIMITATIONS", "TREATY",
            
            # Case Citations
            "CASE_CITATION", "CFR_CITATION", "CFR_CITATIONS", 
            "ELECTRONIC_CITATION", "ELECTRONIC_CITATIONS", 
            "ENHANCED_CASE_CITATIONS", "PINPOINT_CITATIONS", 
            "SHORT_FORMS", "USC_CITATION", "USC_CITATIONS",
            
            # Courts and Jurisdictions
            "CIRCUIT", "CIRCUITS", "DISTRICT", "DIVISION", 
            "FEDERAL_JURISDICTION", "FORUM", "JURISDICTION", 
            "STATE_JURISDICTION", "VENUE",
            
            # Legal Documents and Filings
            "ANSWER", "BRIEF", "COMPLAINT", "COUNTERCLAIM", "DISCOVERY",
            "DISCOVERY_MATERIAL", "DISCOVERY_REQUEST", "DOCUMENT", 
            "DOCUMENTARY_EVIDENCE", "FILING", "MOTION", "ORDER", 
            "STANDING_ORDER",
            
            # Procedural Elements
            "APPEAL", "CERTIORARI", "CIVIL_PROCEDURE", "CLASS_ACTION",
            "CRIMINAL_PROCEDURE", "PLEA", "SETTLEMENT", "SETTLEMENT_AMOUNT",
            
            # Evidence and Testimony
            "AFFIDAVIT", "DEMONSTRATIVE_EVIDENCE", "DIGITAL_EVIDENCE",
            "EVIDENCE_TYPE", "EXHIBIT", "EXPERT_WITNESS", 
            "FORENSIC_EVIDENCE", "HEARSAY", "HEARSAY_EXCEPTION",
            "LAY_WITNESS", "PHYSICAL_EVIDENCE", "TESTIMONIAL_EVIDENCE",
            "TESTIMONY", "TRANSCRIPT", "WITNESS_STATEMENT",
            
            # Financial and Damages
            "AWARD", "COMPENSATION", "COMPENSATORY_DAMAGES", "FEE",
            "JUDGMENT", "LIQUIDATED_DAMAGES", "MONETARY_AMOUNT",
            "NOMINAL_DAMAGES", "PENALTY", "PUNITIVE_DAMAGES",
            "STATUTORY_DAMAGES",
            
            # Criminal Law
            "ACQUITTAL", "CHARGES", "CONVICTION", "FELONY", 
            "MISDEMEANOR", "OFFENSE", "PAROLE", "PROBATION", "SENTENCE",
            
            # Legal Concepts and Standards
            "BURDEN_OF_PROOF", "DUE_PROCESS", "LEGAL_DOCTRINE",
            "LEGAL_STANDARD", "LEGAL_TEST",
            
            # Organizations and Entities
            "ADMINISTRATIVE_AGENCY", "FEDERAL_AGENCY", "GOVERNMENT_AGENCY",
            "LAW_ENFORCEMENT", "LEGISLATIVE_BODY", "LLC", "LOCAL_AGENCY",
            "NONPROFIT", "ORGANIZATION", "PARTNERSHIP", "REGULATORY_BODY",
            "STATE_AGENCY",
            
            # Intellectual Property
            "COPYRIGHT", "PATENT", "TRADEMARK", "TRADE_SECRET",
            
            # Geographic and Personal
            "ADDRESS", "CITY", "COUNTRY", "COUNTY", "EMAIL", "PERSON",
            "PHONE_NUMBER", "STATE", "URL",
            
            # Dates and Time
            "DATE", "DECISION_DATE", "EXPIRATION_DATE", "HEARING_DATE",
            "SERVICE_DATE", "TRIAL_DATE",
            
            # Case Management
            "CASE_CAPTION", "CASE_NUMBER", "CASE_STATUS", "CASE_TITLE",
            "CASE_TYPE", "DOCKET_NUMBER", "HEARING", "PROCEEDING",
            
            # Relief and Remedies
            "AFFIRMATIVE_DEFENSE", "CAUSE_OF_ACTION", "CLAIM", 
            "CROSSCLAIM", "CROSS_CLAIM", "DECLARATORY_RELIEF", 
            "DEFENSE", "EQUITABLE_RELIEF", "INJUNCTION", 
            "RELIEF_REQUESTED", "REMEDY",
            
            # Specialized Citations
            "CFR_TITLES", "FEDERAL_RULES", "LATIN_TERM", "LEGAL_MARKER",
            "SECTION_HEADER", "SECTION_REFERENCE", "SECTION_SYMBOLS",
            "USC_TITLES",
            
            # Miscellaneous Legal
            "AGENCIES", "AGREEMENT", "ALLEGATION", "ASSOCIATION",
            "BAR_NUMBER", "CASE_LAW", "CASE_PARTIES", "CHARGE",
            "CONVENTION", "COUNT", "DECLARATION", "DEFINED_TERM",
            "ELEMENT", "EQUAL_PROTECTION", "EXECUTIVE_OFFICE", "FACTOR",
            "FIFTH_AMENDMENT", "FREE_SPEECH", "INFRACTION", "LEGAL_ACTION",
            "LEGAL_AID", "LEGAL_CITATION", "LEGAL_CONCEPT", 
            "LEGAL_DEFINITION", "LEGAL_TERM", "LEGAL_THEORY", 
            "LOCAL_RULE", "PERCENTAGE", "PRINCIPLE", "PROCEDURAL_RULE",
            "PUBLIC_DEFENDER", "RULING", "SENTENCING", "SPECIAL_MASTER",
            "STANDARD_OF_REVIEW", "TRUST", "UNION", "VERDICT"
        ]
        
    def load_model(self):
        """Load the base model and apply LoRA adapter."""
        logger.info(f"Loading base model: {self.base_model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.adapter_path,
            trust_remote_code=True,
            use_fast=True
        )
        
        # Set padding token if not set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load base model
        logger.info("Loading base model...")
        base_model = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True
        )
        
        # Load LoRA adapter
        logger.info(f"Loading LoRA adapter from: {self.adapter_path}")
        self.model = PeftModel.from_pretrained(
            base_model,
            self.adapter_path
        )
        
        # Set to evaluation mode
        self.model.eval()
        logger.info("Fine-tuned model loaded successfully!")
        
    def create_training_compatible_prompt(self, text: str) -> str:
        """
        Create a prompt that exactly matches the training data format.
        This is critical for the fine-tuned model to work properly.
        """
        prompt = f"""You are a specialized legal entity extraction and relationship detection system based on SaulLM (Legal Language Model). Your task is to analyze legal documents and extract entities while detecting relationships between them. Return results in the LurisEntityV2 structure format.

## Primary Objectives

1. **Entity Extraction**: Identify and extract ALL legal entities with high precision and recall
2. **Relationship Detection**: Discover and map relationships between extracted entities
3. **Structured Output**: Return data in LurisEntityV2 compliant JSON format
4. **Legal Accuracy**: Maintain domain-specific accuracy for legal terminology and concepts

## Entity Types to Extract

You must identify ALL occurrences of the following 219 entity types:

### Courts and Judicial Officers
ARBITRATOR, COURT, COURT_CLERK, COURT_REPORTER, ENHANCED_COURT_PATTERNS, FEDERAL_COURTS, JUDGE, MAGISTRATE, MEDIATOR, SPECIALIZED_COURTS, SPECIALIZED_COURT_CITATIONS, STATE_COURTS

### Legal Professionals
ATTORNEY, CORPORATE_COUNSEL, GOVERNMENT_ATTORNEY, LAW_CLERK, LAW_FIRM, LEGAL_AID_ATTORNEY, LEGAL_SECRETARY, PARALEGAL, PROSECUTOR

### Parties and Participants
CLASS_REPRESENTATIVE, DEFENDANT, ENHANCED_PARTY_PATTERNS, INDIVIDUAL_PARTY, PARTY, PLAINTIFF, THIRD_PARTY

### Legal Authority and Citations
ADMINISTRATIVE_CODE, CONSTITUTIONAL_AMENDMENT, CONSTITUTIONAL_PROVISION, EXECUTIVE_ORDER, LEGAL_RULE, ORDINANCE, REGULATION, REGULATION_CITATION, STATE_REGULATION_CITATION, STATE_STATUTES, STATE_STATUTE_CITATION, STATUTE, STATUTE_CITATION, STATUTE_OF_LIMITATIONS, TREATY

### Case Citations
CASE_CITATION, CFR_CITATION, CFR_CITATIONS, ELECTRONIC_CITATION, ELECTRONIC_CITATIONS, ENHANCED_CASE_CITATIONS, PINPOINT_CITATIONS, SHORT_FORMS, USC_CITATION, USC_CITATIONS

### Additional Categories
Include all Courts and Jurisdictions, Legal Documents and Filings, Procedural Elements, Evidence and Testimony, Financial and Damages, Criminal Law, Legal Concepts and Standards, Organizations and Entities, Intellectual Property, Geographic and Personal, Dates and Time, Case Management, Relief and Remedies, Specialized Citations, and Miscellaneous Legal entities.

## Output Format: LurisEntityV2 Structure

Return your analysis in the following JSON structure:

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
      "relationship_type": "RELATIONSHIP_TYPE",
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

1. **Precision**: Extract only entities that clearly match the defined types
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

### Text to Analyze

{text[:4000]}

Extract all legal entities and relationships from the above text following the LurisEntityV2 structure."""
        
        return prompt
    
    def extract_entities_improved(self, text: str) -> Dict[str, Any]:
        """
        Extract entities using the improved prompt that matches training format.
        """
        # Create the properly formatted prompt
        prompt = self.create_training_compatible_prompt(text)
        
        # Tokenize the input with optimal settings
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=4096,
            padding=True
        )
        inputs = {k: v.cuda() if torch.cuda.is_available() else v for k, v in inputs.items()}
        
        # Generate response with optimal parameters matching training
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.1,  # Low temperature for consistency
                do_sample=True,
                top_p=0.95,  # Balanced creativity and precision
                repetition_penalty=1.1,  # Prevent repetitive outputs
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode the response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract and parse the LurisEntityV2 JSON structure
        try:
            # Find the JSON part of the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate the structure
                if self.validate_luris_structure(result):
                    return result
                else:
                    # If structure is invalid, try to fix it
                    return self.fix_luris_structure(result)
            else:
                logger.warning("Could not find valid JSON in response")
                return self.create_empty_result()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            # Try to extract entities in a simpler format
            return self.fallback_extraction(response)
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return self.create_empty_result()
    
    def validate_luris_structure(self, result: Dict) -> bool:
        """Validate that the result follows LurisEntityV2 structure."""
        required_keys = ["entities", "relationships", "summary"]
        return all(key in result for key in required_keys)
    
    def fix_luris_structure(self, result: Dict) -> Dict:
        """Fix incomplete LurisEntityV2 structure."""
        fixed = {
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
            "summary": result.get("summary", {})
        }
        
        # Ensure each entity has required fields
        for entity in fixed["entities"]:
            if "entity_id" not in entity:
                entity["entity_id"] = f"entity_{hash(entity.get('text', ''))}"
            if "confidence" not in entity:
                entity["confidence"] = 0.85
            if "metadata" not in entity:
                entity["metadata"] = {}
                
        # Update summary
        fixed["summary"]["total_entities"] = len(fixed["entities"])
        fixed["summary"]["total_relationships"] = len(fixed["relationships"])
        
        return fixed
    
    def fallback_extraction(self, response: str) -> Dict:
        """Fallback extraction method if JSON parsing fails."""
        entities = []
        
        # Try to extract entities from the response text
        lines = response.split('\n')
        entity_id = 0
        
        for line in lines:
            # Look for patterns that indicate entities
            if any(entity_type in line.upper() for entity_type in self.entity_types):
                for entity_type in self.entity_types:
                    if entity_type in line.upper():
                        entities.append({
                            "entity_id": f"entity_{entity_id}",
                            "text": line.strip(),
                            "entity_type": entity_type,
                            "confidence": 0.75,
                            "metadata": {"extraction_method": "fallback"}
                        })
                        entity_id += 1
                        break
        
        return {
            "entities": entities,
            "relationships": [],
            "summary": {
                "total_entities": len(entities),
                "total_relationships": 0,
                "extraction_method": "fallback"
            }
        }
    
    def create_empty_result(self) -> Dict:
        """Create an empty but valid LurisEntityV2 result."""
        return {
            "entities": [],
            "relationships": [],
            "summary": {
                "total_entities": 0,
                "total_relationships": 0,
                "extraction_timestamp": datetime.now().isoformat(),
                "error": "No entities extracted"
            }
        }
    
    def process_document(self, text: str, chunk_size: int = 4000) -> Dict[str, Any]:
        """Process a complete document by chunking and aggregating results."""
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        all_entities = []
        all_relationships = []
        entity_id_map = {}
        
        logger.info(f"Processing {len(chunks)} chunks...")
        
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}...")
            
            result = self.extract_entities_improved(chunk)
            
            # Add entities with deduplication
            for entity in result.get("entities", []):
                # Create a unique key for deduplication
                key = (entity.get("text", ""), entity.get("entity_type", ""))
                
                if key not in entity_id_map:
                    # Assign new entity ID
                    new_id = f"entity_{len(all_entities)}"
                    entity["entity_id"] = new_id
                    entity_id_map[key] = new_id
                    all_entities.append(entity)
                else:
                    # Update confidence if higher
                    existing_idx = next(
                        i for i, e in enumerate(all_entities) 
                        if e["entity_id"] == entity_id_map[key]
                    )
                    if entity.get("confidence", 0) > all_entities[existing_idx].get("confidence", 0):
                        all_entities[existing_idx]["confidence"] = entity["confidence"]
            
            # Add relationships
            all_relationships.extend(result.get("relationships", []))
        
        # Calculate summary statistics
        entity_types = {}
        for entity in all_entities:
            entity_type = entity.get("entity_type", "UNKNOWN")
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        avg_confidence = sum(e.get("confidence", 0) for e in all_entities) / len(all_entities) if all_entities else 0
        
        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "summary": {
                "total_entities": len(all_entities),
                "total_relationships": len(all_relationships),
                "unique_entity_types": len(entity_types),
                "entity_type_distribution": entity_types,
                "avg_confidence": avg_confidence,
                "primary_entity_types": sorted(
                    entity_types.keys(), 
                    key=lambda x: entity_types[x], 
                    reverse=True
                )[:10],
                "chunks_processed": len(chunks),
                "extraction_timestamp": datetime.now().isoformat(),
                "model_version": "SaulLM-7B-Instruct-v1-FineTuned"
            }
        }
    
    def test_on_rahimi(self):
        """Test the improved inference on Rahimi document."""
        # Read Rahimi document text
        rahimi_text_file = Path("tests/docs/rahimi_text.txt")
        
        if not rahimi_text_file.exists():
            # Extract text from PDF if text file doesn't exist
            logger.info("Extracting text from Rahimi PDF...")
            import PyPDF2
            pdf_path = Path("tests/docs/Rahimi.pdf")
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
                
                # Save text for future use
                with open(rahimi_text_file, 'w', encoding='utf-8') as f:
                    f.write(text)
        else:
            with open(rahimi_text_file, 'r', encoding='utf-8') as f:
                text = f.read()
        
        logger.info(f"Document text length: {len(text)} characters")
        
        # Process with improved method
        start_time = time.time()
        result = self.process_document(text[:15000])  # Process first 15000 chars for testing
        processing_time = time.time() - start_time
        
        # Add performance metrics
        result["summary"]["processing_time"] = processing_time
        result["summary"]["entities_per_second"] = len(result["entities"]) / processing_time if processing_time > 0 else 0
        
        # Load baseline for comparison
        baseline_path = Path("tests/results/baselines/pre_training_baseline.json")
        if baseline_path.exists():
            with open(baseline_path, 'r') as f:
                baseline_data = json.load(f)
                rahimi_baseline = baseline_data.get("rahimi", {})
                
                # Calculate improvements
                baseline_count = rahimi_baseline.get("entities_found", 75)
                baseline_types = rahimi_baseline.get("unique_entities", 32)
                baseline_confidence = rahimi_baseline.get("confidence_avg", 0.65)
                
                result["improvements"] = {
                    "entity_count_increase": len(result["entities"]) - baseline_count,
                    "entity_count_increase_pct": ((len(result["entities"]) - baseline_count) / baseline_count * 100) if baseline_count > 0 else 0,
                    "type_diversity_increase": result["summary"]["unique_entity_types"] - baseline_types,
                    "type_diversity_increase_pct": ((result["summary"]["unique_entity_types"] - baseline_types) / baseline_types * 100) if baseline_types > 0 else 0,
                    "confidence_increase": result["summary"]["avg_confidence"] - baseline_confidence,
                    "confidence_increase_pct": ((result["summary"]["avg_confidence"] - baseline_confidence) / baseline_confidence * 100) if baseline_confidence > 0 else 0
                }
                
                logger.info(f"Baseline: {baseline_count} entities, {baseline_types} types")
                logger.info(f"Improved: {len(result['entities'])} entities, {result['summary']['unique_entity_types']} types")
                logger.info(f"Improvement: {result['improvements']['entity_count_increase_pct']:.1f}% more entities")
        
        # Save results
        results_dir = Path("tests/results/improved_inference")
        results_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"rahimi_improved_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to: {results_file}")
        
        return result

def main():
    """Main execution function."""
    logger.info("Starting improved fine-tuned model inference...")
    
    inference = ImprovedFineTunedInference()
    
    # Load the fine-tuned model
    inference.load_model()
    
    # Test on Rahimi document
    result = inference.test_on_rahimi()
    
    # Print summary
    print("\n" + "="*60)
    print("IMPROVED FINE-TUNED MODEL INFERENCE RESULTS")
    print("="*60)
    print(f"Entities Found: {result['summary']['total_entities']}")
    print(f"Unique Entity Types: {result['summary']['unique_entity_types']}")
    print(f"Average Confidence: {result['summary']['avg_confidence']:.3f}")
    print(f"Processing Time: {result['summary']['processing_time']:.2f}s")
    
    if "improvements" in result:
        print("\nIMPROVEMENTS OVER BASELINE:")
        print(f"  Entity Count: {result['improvements']['entity_count_increase_pct']:.1f}% increase")
        print(f"  Type Diversity: {result['improvements']['type_diversity_increase_pct']:.1f}% increase")
        print(f"  Confidence: {result['improvements']['confidence_increase_pct']:.1f}% increase")
    
    print("\nTop Entity Types:")
    for entity_type, count in sorted(
        result['summary']['entity_type_distribution'].items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10]:
        print(f"  {entity_type}: {count}")
    
    print("="*60)

if __name__ == "__main__":
    main()