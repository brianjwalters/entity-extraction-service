#!/usr/bin/env python3
"""
Fixed inference script for fine-tuned SaulLM model.
Addresses the template output issue with multiple prompt strategies.
"""

import json
import time
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedFineTunedInference:
    def __init__(self, base_model_name="Equall/Saul-7B-Instruct-v1", 
                 adapter_path="./fine_tuned_saullm_legal"):
        """Initialize the fixed fine-tuned model inference."""
        self.base_model_name = base_model_name
        self.adapter_path = adapter_path
        self.model = None
        self.tokenizer = None
        
        # Define key entity types we expect to find
        self.key_entity_types = [
            "CASE_CITATION", "COURT", "JUDGE", "ATTORNEY", "DEFENDANT", "PLAINTIFF",
            "DATE", "STATUTE", "LEGAL_STANDARD", "JURISDICTION", "DOCKET_NUMBER",
            "CASE_TITLE", "CONSTITUTIONAL_PROVISION", "LEGAL_DOCTRINE"
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
    
    def create_minimal_prompt(self, text: str) -> str:
        """
        Strategy 1: Minimal prompt without examples to prevent template copying.
        """
        prompt = f"""Extract legal entities from the following text. Return JSON with entities array.

Text: {text[:2000]}

Entities:"""
        return prompt
    
    def create_instruction_only_prompt(self, text: str) -> str:
        """
        Strategy 2: Clear instructions without example structure.
        """
        prompt = f"""You are a legal entity extraction system. Analyze this text and identify all legal entities.

Extract these types: CASE_CITATION, COURT, JUDGE, ATTORNEY, DEFENDANT, PLAINTIFF, DATE, STATUTE, LEGAL_STANDARD

For each entity found, provide:
- The exact text
- The entity type
- Confidence score

Text to analyze:
{text[:2500]}

Begin extraction:"""
        return prompt
    
    def create_completion_style_prompt(self, text: str) -> str:
        """
        Strategy 3: Completion-style prompt that guides generation.
        """
        prompt = f"""Legal Entity Extraction Task

Document text:
{text[:2000]}

Identified entities:
1."""
        return prompt
    
    def create_direct_extraction_prompt(self, text: str) -> str:
        """
        Strategy 4: Direct extraction without JSON structure in prompt.
        """
        prompt = f"""Extract all legal entities from this text. List each entity with its type.

{text[:2000]}

ENTITIES FOUND:
-"""
        return prompt
    
    def extract_with_strategy(self, text: str, strategy: str = "minimal") -> Dict[str, Any]:
        """
        Extract entities using specified prompt strategy.
        """
        # Select prompt strategy
        if strategy == "minimal":
            prompt = self.create_minimal_prompt(text)
        elif strategy == "instruction":
            prompt = self.create_instruction_only_prompt(text)
        elif strategy == "completion":
            prompt = self.create_completion_style_prompt(text)
        elif strategy == "direct":
            prompt = self.create_direct_extraction_prompt(text)
        else:
            prompt = self.create_minimal_prompt(text)
        
        # Tokenize the input
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=2048,  # Reduced to focus on extraction
            padding=True
        )
        inputs = {k: v.cuda() if torch.cuda.is_available() else v for k, v in inputs.items()}
        
        # Generate with different parameters for each strategy
        generation_params = self.get_generation_params(strategy)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                **generation_params,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode the response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove the prompt from response
        response = response[len(prompt):].strip()
        
        # Parse based on strategy
        return self.parse_response(response, strategy)
    
    def get_generation_params(self, strategy: str) -> Dict:
        """Get optimized generation parameters for each strategy."""
        base_params = {
            "max_new_tokens": 1024,
            "do_sample": True,
            "repetition_penalty": 1.2,
        }
        
        if strategy == "minimal":
            # Very low temperature for structured output
            return {**base_params, "temperature": 0.1, "top_p": 0.9}
        elif strategy == "instruction":
            # Slightly higher temperature for natural generation
            return {**base_params, "temperature": 0.3, "top_p": 0.95}
        elif strategy == "completion":
            # Balanced parameters for completion
            return {**base_params, "temperature": 0.2, "top_p": 0.92}
        elif strategy == "direct":
            # Lower temperature for list generation
            return {**base_params, "temperature": 0.15, "top_p": 0.9}
        else:
            return {**base_params, "temperature": 0.2, "top_p": 0.95}
    
    def parse_response(self, response: str, strategy: str) -> Dict[str, Any]:
        """Parse response based on strategy used."""
        entities = []
        
        # Check if response contains the template structure
        if "exact_extracted_text" in response or "ENTITY_TYPE_FROM_ABOVE" in response:
            logger.warning(f"Strategy {strategy} returned template output, attempting recovery")
            return self.parse_fallback(response)
        
        # Try JSON parsing first
        try:
            # Find JSON structure
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                if "entities" in result:
                    return result
                else:
                    # Convert to expected format
                    return {"entities": [result] if isinstance(result, dict) else result}
        except:
            pass
        
        # Strategy-specific parsing
        if strategy == "completion" or strategy == "direct":
            entities = self.parse_list_format(response)
        else:
            entities = self.parse_natural_format(response)
        
        return {
            "entities": entities,
            "relationships": [],
            "summary": {
                "total_entities": len(entities),
                "extraction_strategy": strategy,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def parse_list_format(self, response: str) -> List[Dict]:
        """Parse list-style response format."""
        entities = []
        lines = response.split('\n')
        entity_id = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Look for patterns like "1. United States v. Rahimi (CASE_CITATION)"
            # or "- Judge Barrett (JUDGE)"
            # or "CASE_CITATION: United States v. Rahimi"
            
            # Pattern 1: numbered or bulleted lists
            match = re.match(r'^[\d\-\*\.]+\s*(.+?)\s*\(([A-Z_]+)\)', line)
            if match:
                text, entity_type = match.groups()
                entities.append({
                    "entity_id": f"entity_{entity_id}",
                    "text": text.strip(),
                    "entity_type": entity_type,
                    "confidence": 0.85,
                    "source": "list_format"
                })
                entity_id += 1
                continue
            
            # Pattern 2: Type first format
            match = re.match(r'^([A-Z_]+):\s*(.+)', line)
            if match:
                entity_type, text = match.groups()
                if entity_type in self.key_entity_types:
                    entities.append({
                        "entity_id": f"entity_{entity_id}",
                        "text": text.strip(),
                        "entity_type": entity_type,
                        "confidence": 0.85,
                        "source": "type_first_format"
                    })
                    entity_id += 1
                    continue
            
            # Pattern 3: Plain text with known entity types
            for entity_type in self.key_entity_types:
                if entity_type in line.upper():
                    # Extract text around the entity type mention
                    text = re.sub(rf'\b{entity_type}\b', '', line, flags=re.IGNORECASE).strip()
                    if text and len(text) > 2:
                        entities.append({
                            "entity_id": f"entity_{entity_id}",
                            "text": text[:100],  # Limit length
                            "entity_type": entity_type,
                            "confidence": 0.75,
                            "source": "keyword_match"
                        })
                        entity_id += 1
                        break
        
        return entities
    
    def parse_natural_format(self, response: str) -> List[Dict]:
        """Parse natural language response format."""
        entities = []
        entity_id = 0
        
        # Look for entity mentions in natural text
        # Common patterns: "the case of X", "Judge X", "on [date]", etc.
        
        # Extract case citations
        case_patterns = [
            r'\b(\w+\s+v\.\s+\w+)\b',
            r'\b(\w+\s+versus\s+\w+)\b',
            r'\b(No\.\s+\d+[-–]\d+)\b',
        ]
        for pattern in case_patterns:
            for match in re.finditer(pattern, response, re.IGNORECASE):
                entities.append({
                    "entity_id": f"entity_{entity_id}",
                    "text": match.group(1),
                    "entity_type": "CASE_CITATION",
                    "confidence": 0.9,
                    "source": "pattern_match"
                })
                entity_id += 1
        
        # Extract judges
        judge_pattern = r'\b(?:Judge|Justice|Magistrate)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        for match in re.finditer(judge_pattern, response):
            entities.append({
                "entity_id": f"entity_{entity_id}",
                "text": match.group(1),
                "entity_type": "JUDGE",
                "confidence": 0.85,
                "source": "pattern_match"
            })
            entity_id += 1
        
        # Extract courts
        court_pattern = r'\b((?:Supreme|District|Circuit|Appeals|Federal|State)\s+Court(?:\s+of\s+[A-Z][a-z]+)?)\b'
        for match in re.finditer(court_pattern, response, re.IGNORECASE):
            entities.append({
                "entity_id": f"entity_{entity_id}",
                "text": match.group(1),
                "entity_type": "COURT",
                "confidence": 0.85,
                "source": "pattern_match"
            })
            entity_id += 1
        
        # Extract dates
        date_patterns = [
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
            r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',
            r'\b(\d{4}[-–]\d{2}[-–]\d{2})\b',
        ]
        for pattern in date_patterns:
            for match in re.finditer(pattern, response):
                entities.append({
                    "entity_id": f"entity_{entity_id}",
                    "text": match.group(1),
                    "entity_type": "DATE",
                    "confidence": 0.9,
                    "source": "pattern_match"
                })
                entity_id += 1
        
        return entities
    
    def parse_fallback(self, response: str) -> Dict[str, Any]:
        """Fallback parser for when other methods fail."""
        # Try to extract any meaningful entities from the response
        entities = []
        
        # Look for actual entity text even in template output
        lines = response.split('\n')
        for line in lines:
            # Skip template lines
            if any(template in line for template in 
                   ["exact_extracted_text", "ENTITY_TYPE_FROM_ABOVE", 
                    "surrounding_context", "unique_identifier"]):
                continue
            
            # Try to extract real content
            line = line.strip()
            if line and len(line) > 5 and not line.startswith('{') and not line.startswith('}'):
                # Check if line contains legal terms
                legal_terms = ["court", "judge", "case", "defendant", "plaintiff", 
                              "statute", "amendment", "united states", "v.", "no."]
                if any(term in line.lower() for term in legal_terms):
                    entities.append({
                        "entity_id": f"entity_{len(entities)}",
                        "text": line[:200],
                        "entity_type": "UNKNOWN",
                        "confidence": 0.5,
                        "source": "fallback"
                    })
        
        return {
            "entities": entities,
            "relationships": [],
            "summary": {
                "total_entities": len(entities),
                "extraction_method": "fallback",
                "warning": "Template output detected, used fallback extraction"
            }
        }
    
    def extract_entities_multi_strategy(self, text: str) -> Dict[str, Any]:
        """
        Try multiple strategies and combine results.
        """
        strategies = ["minimal", "instruction", "completion", "direct"]
        all_entities = []
        strategy_results = {}
        
        for strategy in strategies:
            logger.info(f"Trying strategy: {strategy}")
            try:
                result = self.extract_with_strategy(text, strategy)
                strategy_results[strategy] = result
                
                # Check if we got real entities (not template)
                if result.get("entities") and not self.is_template_output(result):
                    all_entities.extend(result.get("entities", []))
                    logger.info(f"Strategy {strategy} found {len(result.get('entities', []))} entities")
                else:
                    logger.warning(f"Strategy {strategy} returned template or no entities")
                    
            except Exception as e:
                logger.error(f"Strategy {strategy} failed: {e}")
                continue
        
        # Deduplicate entities
        unique_entities = self.deduplicate_entities(all_entities)
        
        # If still no entities, try regex extraction as last resort
        if len(unique_entities) == 0:
            logger.warning("All strategies failed, using regex extraction")
            unique_entities = self.regex_extraction(text)
        
        return {
            "entities": unique_entities,
            "relationships": [],
            "summary": {
                "total_entities": len(unique_entities),
                "strategies_tried": len(strategies),
                "successful_strategies": sum(1 for r in strategy_results.values() 
                                           if r.get("entities") and not self.is_template_output(r)),
                "extraction_timestamp": datetime.now().isoformat(),
                "model_version": "SaulLM-7B-FineTuned-Fixed"
            }
        }
    
    def is_template_output(self, result: Dict) -> bool:
        """Check if result contains template output."""
        if not result.get("entities"):
            return False
        
        # Check for template indicators
        template_indicators = [
            "exact_extracted_text",
            "ENTITY_TYPE_FROM_ABOVE",
            "surrounding_context_text",
            "unique_identifier",
            "entity_1_id",
            "pattern_name"
        ]
        
        for entity in result.get("entities", []):
            entity_str = json.dumps(entity)
            if any(indicator in entity_str for indicator in template_indicators):
                return True
        
        return False
    
    def deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on text and type."""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.get("text", "").lower().strip(), 
                   entity.get("entity_type", ""))
            
            if key not in seen and key[0]:  # Ensure text is not empty
                seen.add(key)
                # Assign consistent entity_id
                entity["entity_id"] = f"entity_{len(unique)}"
                unique.append(entity)
        
        return unique
    
    def regex_extraction(self, text: str) -> List[Dict]:
        """Last resort regex-based extraction."""
        entities = []
        entity_id = 0
        
        # Case citations
        case_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+v\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        for match in re.finditer(case_pattern, text):
            entities.append({
                "entity_id": f"entity_{entity_id}",
                "text": match.group(1),
                "entity_type": "CASE_CITATION",
                "confidence": 0.8,
                "source": "regex"
            })
            entity_id += 1
        
        # Docket numbers
        docket_pattern = r'\b(No\.\s+\d{2}[-–]\d{3,4})\b'
        for match in re.finditer(docket_pattern, text):
            entities.append({
                "entity_id": f"entity_{entity_id}",
                "text": match.group(1),
                "entity_type": "DOCKET_NUMBER",
                "confidence": 0.85,
                "source": "regex"
            })
            entity_id += 1
        
        # Courts
        court_pattern = r'\b(United States (?:Supreme|District|Circuit) Court|Court of Appeals|Fifth Circuit)\b'
        for match in re.finditer(court_pattern, text, re.IGNORECASE):
            entities.append({
                "entity_id": f"entity_{entity_id}",
                "text": match.group(1),
                "entity_type": "COURT",
                "confidence": 0.9,
                "source": "regex"
            })
            entity_id += 1
        
        # Judges/Justices
        judge_pattern = r'\b(?:Chief )?(?:Judge|Justice)\s+([A-Z][A-Za-z]+(?:\s+[A-Z]\.)?\s+[A-Z][A-Za-z]+)\b'
        for match in re.finditer(judge_pattern, text):
            entities.append({
                "entity_id": f"entity_{entity_id}",
                "text": match.group(1),
                "entity_type": "JUDGE",
                "confidence": 0.85,
                "source": "regex"
            })
            entity_id += 1
        
        # Constitutional provisions
        const_pattern = r'\b((?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Fourteenth) Amendment|Article [IVX]+|Constitution)\b'
        for match in re.finditer(const_pattern, text, re.IGNORECASE):
            entities.append({
                "entity_id": f"entity_{entity_id}",
                "text": match.group(1),
                "entity_type": "CONSTITUTIONAL_PROVISION",
                "confidence": 0.9,
                "source": "regex"
            })
            entity_id += 1
        
        return entities
    
    def process_document(self, text: str, chunk_size: int = 2000) -> Dict[str, Any]:
        """Process a complete document by chunking and aggregating results."""
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size-200)]  # Overlap of 200 chars
        
        all_entities = []
        successful_chunks = 0
        failed_chunks = 0
        
        logger.info(f"Processing {len(chunks)} chunks...")
        
        for i, chunk in enumerate(chunks[:5], 1):  # Process first 5 chunks for testing
            logger.info(f"Processing chunk {i}/{min(5, len(chunks))}...")
            
            try:
                result = self.extract_entities_multi_strategy(chunk)
                
                if result.get("entities"):
                    all_entities.extend(result.get("entities", []))
                    successful_chunks += 1
                else:
                    failed_chunks += 1
                    
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                failed_chunks += 1
        
        # Deduplicate final results
        unique_entities = self.deduplicate_entities(all_entities)
        
        # Calculate statistics
        entity_types = {}
        for entity in unique_entities:
            entity_type = entity.get("entity_type", "UNKNOWN")
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        return {
            "entities": unique_entities,
            "relationships": [],
            "summary": {
                "total_entities": len(unique_entities),
                "unique_entity_types": len(entity_types),
                "entity_type_distribution": entity_types,
                "chunks_processed": successful_chunks + failed_chunks,
                "successful_chunks": successful_chunks,
                "failed_chunks": failed_chunks,
                "extraction_timestamp": datetime.now().isoformat(),
                "model_version": "SaulLM-7B-FineTuned-Fixed"
            }
        }
    
    def test_on_rahimi(self):
        """Test the fixed inference on Rahimi document."""
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
                for page_num in range(min(10, len(pdf_reader.pages))):  # First 10 pages
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
                
                # Save text for future use
                with open(rahimi_text_file, 'w', encoding='utf-8') as f:
                    f.write(text)
        else:
            with open(rahimi_text_file, 'r', encoding='utf-8') as f:
                text = f.read()
        
        logger.info(f"Document text length: {len(text)} characters")
        
        # Process with fixed method
        start_time = time.time()
        result = self.process_document(text[:10000])  # Process first 10000 chars
        processing_time = time.time() - start_time
        
        # Add performance metrics
        result["summary"]["processing_time"] = processing_time
        result["summary"]["entities_per_second"] = len(result["entities"]) / processing_time if processing_time > 0 else 0
        
        # Save results
        results_dir = Path("tests/results/fixed_inference")
        results_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"rahimi_fixed_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Results saved to: {results_file}")
        
        return result

def main():
    """Main execution function."""
    logger.info("Starting fixed fine-tuned model inference...")
    
    inference = FixedFineTunedInference()
    
    # Load the fine-tuned model
    inference.load_model()
    
    # Test on Rahimi document
    result = inference.test_on_rahimi()
    
    # Print summary
    print("\n" + "="*60)
    print("FIXED FINE-TUNED MODEL INFERENCE RESULTS")
    print("="*60)
    print(f"Entities Found: {result['summary']['total_entities']}")
    print(f"Unique Entity Types: {result['summary']['unique_entity_types']}")
    print(f"Successful Chunks: {result['summary'].get('successful_chunks', 'N/A')}")
    print(f"Failed Chunks: {result['summary'].get('failed_chunks', 'N/A')}")
    print(f"Processing Time: {result['summary'].get('processing_time', 0):.2f}s")
    
    print("\nEntity Type Distribution:")
    for entity_type, count in sorted(
        result['summary'].get('entity_type_distribution', {}).items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10]:
        print(f"  {entity_type}: {count}")
    
    # Show sample entities
    print("\nSample Entities Found:")
    for entity in result.get("entities", [])[:10]:
        print(f"  [{entity['entity_type']}] {entity['text'][:50]}... (conf: {entity.get('confidence', 0):.2f})")
    
    print("="*60)

if __name__ == "__main__":
    main()