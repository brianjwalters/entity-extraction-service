#!/usr/bin/env python3
"""
SaulLM Rahimi Document Comparison Test
Tests SaulLM-7B entity extraction on the actual Rahimi Supreme Court case document.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any
import sys
import os
from datetime import datetime

# Add src to path for imports

from rahimi_processor import RahimiProcessor

# Import vLLM for direct API usage
try:
    from vllm import LLM, SamplingParams
    import torch
    import psutil
    print("✅ vLLM imported successfully")
except ImportError as e:
    print(f"❌ Failed to import vLLM: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SaulLMRahimiExtractor:
    """SaulLM-based entity extractor specifically for Rahimi document testing."""
    
    def __init__(self, model_name: str = "Equall/Saul-7B-Instruct-v1"):
        self.model_name = model_name
        self.llm = None
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # SaulLM sampling parameters
        self.sampling_params = SamplingParams(
            temperature=0.1,
            top_p=0.95,
            repetition_penalty=1.1,
            max_tokens=2048,
            stop=["```", "\n\n\n"]
        )
        
        # Legal entity types for SaulLM
        self.entity_types = {
            'CASE_CITATION': 'Case names with full citations (e.g., Brown v. Board, 347 U.S. 483)',
            'STATUTE': 'Federal and state statutory references (e.g., 42 U.S.C. § 1983)',
            'REGULATION': 'CFR and administrative regulations',
            'CONSTITUTIONAL': 'Constitutional provisions and amendments',
            'PARTY': 'Plaintiff, defendant, petitioner, respondent names',
            'JUDGE': 'Judge names, justices, and judicial officers',
            'ATTORNEY': 'Attorney names and law firm references',
            'COURT': 'Court names and jurisdictions',
            'DOCKET_NUMBER': 'Case numbers and docket identifiers',
            'DATE': 'Legal dates in any format',
            'MONETARY_AMOUNT': 'Dollar amounts and financial figures',
            'LEGAL_DOCTRINE': 'Legal principles and doctrines',
            'PROCEDURAL_TERM': 'Motions, orders, procedural actions',
            'JURISDICTION': 'Geographic and legal jurisdictions',
            'LEGAL_STANDARD': 'Standards of review and legal tests'
        }
    
    def initialize_model(self):
        """Initialize SaulLM model with vLLM."""
        logger.info(f"Initializing {self.model_name} with vLLM...")
        
        # Check GPU availability
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            logger.info(f"CUDA available with {gpu_count} GPUs")
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
                logger.info(f"GPU {i}: {gpu_name} with {gpu_memory:.2f}GB memory")
        else:
            logger.warning("CUDA not available, using CPU")
        
        # vLLM configuration for optimal performance
        config = {
            "model": self.model_name,
            "dtype": "half",  # Use FP16 for memory efficiency
            "max_model_len": 8192,  # Reduced context window
            "enable_prefix_caching": True,  # Speed up repeated prefixes
            "gpu_memory_utilization": 0.8,  # Use available GPU memory
            "max_num_batched_tokens": 8192,  # Reduced batch processing
            "max_num_seqs": 32,  # Reduced concurrent sequences
            "disable_log_stats": True,  # Reduce logging overhead
            "enable_chunked_prefill": True,  # Better memory management
            "tensor_parallel_size": 1  # Single GPU mode
        }
        
        try:
            start_time = time.time()
            self.llm = LLM(**config)
            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
            
            # Test generation to ensure model is working
            test_prompt = "This is a test prompt for legal entity extraction."
            test_output = self.llm.generate([test_prompt], self.sampling_params)
            logger.info("Model test generation successful")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def create_legal_extraction_prompt(self, text: str) -> str:
        """Create specialized prompt for legal entity extraction from Rahimi document."""
        
        entity_descriptions = "\n".join([
            f"- {etype}: {desc}" for etype, desc in self.entity_types.items()
        ])
        
        prompt = f"""You are an expert legal entity extraction system specializing in Supreme Court cases and federal law. Extract ALL legal entities from the following Supreme Court document text with maximum precision and recall.

## Entity Types to Extract:
{entity_descriptions}

## Instructions:
1. Extract EVERY entity that matches the types above
2. Focus on Supreme Court specific entities (case names, justices, constitutional provisions)
3. Include full case citations with reporter information
4. Capture all procedural terms and legal standards
5. Return entities as a JSON array only

## Supreme Court Document Text:
"{text}"

## Output Format:
Return ONLY a JSON array with this exact structure:
```json
[
  {{
    "type": "ENTITY_TYPE",
    "text": "exact text from document",
    "confidence": 0.95
  }}
]
```

Entities:"""
        
        return prompt
    
    def extract_entities_from_text(self, text: str) -> List[Dict]:
        """Extract entities from a single text chunk."""
        if not self.llm:
            self.initialize_model()
        
        # Create prompt
        prompt = self.create_legal_extraction_prompt(text)
        
        # Generate with vLLM
        start_time = time.time()
        outputs = self.llm.generate([prompt], self.sampling_params)
        generation_time = time.time() - start_time
        
        # Parse result
        if outputs and len(outputs) > 0:
            generated_text = outputs[0].outputs[0].text
            entities = self._parse_json_response(generated_text)
            
            logger.info(f"Extracted {len(entities)} entities in {generation_time:.2f}s")
            return entities, generation_time
        
        return [], generation_time
    
    def _parse_json_response(self, response: str) -> List[Dict]:
        """Parse JSON response from SaulLM output."""
        entities = []
        
        try:
            # Try to find JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                # Clean up common issues
                json_str = json_str.replace(',\n]', '\n]')  # Remove trailing commas
                json_str = json_str.replace(',]', ']')  # Remove trailing commas
                
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    entities = parsed
                    
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            # Fallback parsing for partial responses
            entities = self._fallback_entity_parsing(response)
        
        # Validate and clean entities
        validated_entities = []
        for entity in entities:
            if isinstance(entity, dict) and 'type' in entity and 'text' in entity:
                # Ensure confidence is set
                if 'confidence' not in entity:
                    entity['confidence'] = 0.8
                validated_entities.append(entity)
        
        return validated_entities
    
    def _fallback_entity_parsing(self, text: str) -> List[Dict]:
        """Fallback parsing when JSON fails."""
        import re
        entities = []
        
        # Look for common Supreme Court patterns
        patterns = {
            'CASE_CITATION': [
                r'[A-Z][a-z]+ v\. [A-Z][a-z]+,?\s+\d+\s+U\.?\s*S\.?\s+\d+',
                r'[A-Z][a-z]+ v\. [A-Z][a-z]+',
            ],
            'JUDGE': [
                r'Justice [A-Z][a-z]+',
                r'Chief Justice [A-Z][a-z]+',
            ],
            'CONSTITUTIONAL': [
                r'(First|Second|Fourth|Fifth|Sixth|Eighth|Fourteenth) Amendment',
                r'Article [IVX]+',
                r'Due Process Clause',
                r'Equal Protection Clause',
            ],
            'STATUTE': [
                r'\d+\s+U\.S\.C\.?\s+§\s*\d+',
                r'Section \d+',
            ]
        }
        
        for entity_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entities.append({
                        'type': entity_type,
                        'text': match.group(0),
                        'confidence': 0.7
                    })
        
        return entities
    
    def process_rahimi_document(self, chunk_size: int = 4000) -> Dict[str, Any]:
        """Process the complete Rahimi document."""
        logger.info("Starting SaulLM Rahimi document processing...")
        
        # Get Rahimi content
        processor = RahimiProcessor()
        doc_info = processor.process_document()
        
        if "error" in doc_info:
            return {"error": doc_info["error"]}
        
        content = doc_info["content"]
        chunks = processor.get_chunked_content(content, chunk_size)
        
        logger.info(f"Processing {len(chunks)} chunks...")
        
        # Process each chunk
        all_entities = []
        total_extraction_time = 0
        chunk_times = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            
            entities, extraction_time = self.extract_entities_from_text(chunk)
            total_extraction_time += extraction_time
            chunk_times.append(extraction_time)
            
            # Add chunk identifier to entities
            for entity in entities:
                entity['chunk_id'] = i
            
            all_entities.extend(entities)
        
        # Deduplicate entities
        unique_entities = self._deduplicate_entities(all_entities)
        
        # Calculate metrics
        metrics = {
            "model_name": "SaulLM-7B-Instruct",
            "document_length": len(content),
            "word_count": doc_info["word_count"],
            "chunks_processed": len(chunks),
            "chunk_size": chunk_size,
            "total_extraction_time": total_extraction_time,
            "avg_chunk_time": sum(chunk_times) / len(chunk_times) if chunk_times else 0,
            "entities_found": len(all_entities),
            "unique_entities": len(unique_entities),
            "entity_types": {},
            "confidence_avg": 0.0
        }
        
        # Calculate entity type distribution and confidence
        if unique_entities:
            type_counts = {}
            confidences = []
            
            for entity in unique_entities:
                entity_type = entity.get('type', 'UNKNOWN')
                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
                confidences.append(entity.get('confidence', 0.0))
            
            metrics["entity_types"] = type_counts
            metrics["confidence_avg"] = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            "metrics": metrics,
            "entities": unique_entities,
            "chunk_times": chunk_times,
            "timestamp": timestamp
        }
        
        results_file = self.results_dir / f"saullm_rahimi_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {results_file}")
        
        return results
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate entities based on text and type."""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.get('type', ''), entity.get('text', '').strip().lower())
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        logger.info(f"Deduplicated {len(entities)} entities to {len(unique)} unique entities")
        return unique
    
    def cleanup(self):
        """Clean up model and free GPU memory."""
        if self.llm:
            del self.llm
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        logger.info("Model cleaned up and GPU memory freed")


def main():
    """Main function to run SaulLM Rahimi comparison test."""
    print("="*80)
    print("SAULLM RAHIMI DOCUMENT EXTRACTION TEST")
    print("="*80)
    
    try:
        # Initialize extractor
        extractor = SaulLMRahimiExtractor()
        
        # Process Rahimi document
        results = extractor.process_rahimi_document()
        
        if "error" in results:
            print(f"❌ Error: {results['error']}")
            return 1
        
        # Display results
        metrics = results["metrics"]
        entities = results["entities"]
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"📄 Document: {metrics['word_count']:,} words, {metrics['document_length']:,} characters")
        print(f"🔗 Chunks: {metrics['chunks_processed']} chunks processed")
        print(f"⏱️  Time: {metrics['total_extraction_time']:.2f}s total ({metrics['avg_chunk_time']:.2f}s avg per chunk)")
        print(f"📦 Entities: {metrics['entities_found']} total, {metrics['unique_entities']} unique")
        print(f"🎯 Confidence: {metrics['confidence_avg']:.2f} average")
        
        print(f"\n🏷️  Entity Types Found:")
        for entity_type, count in sorted(metrics["entity_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"   {entity_type:20}: {count:4d}")
        
        print(f"\n📝 Sample Entities:")
        for i, entity in enumerate(entities[:10]):  # Show first 10
            print(f"   [{entity['type']}] {entity['text'][:60]}{'...' if len(entity['text']) > 60 else ''}")
        
        print(f"\n✅ Test completed successfully!")
        print(f"📁 Results saved to: {extractor.results_dir}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
        return 1
        
    finally:
        if 'extractor' in locals():
            extractor.cleanup()


if __name__ == "__main__":
    exit(main())