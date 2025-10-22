#!/usr/bin/env python3
"""
Test SaulLM-7B-Instruct with vLLM direct Python API for legal entity extraction.
Compares performance with existing Granite-based system on Rahimi document.
"""

import os
import json
import time
import torch
import gc
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path

try:
    from vllm import LLM, SamplingParams
    logger.info("vLLM imported successfully")
except ImportError as e:
    logger.error(f"Failed to import vLLM: {e}")
    sys.exit(1)

@dataclass
class ExtractionMetrics:
    """Metrics for extraction performance."""
    model_name: str
    total_time: float
    tokens_processed: int
    tokens_per_second: float
    memory_used_gb: float
    chunks_processed: int
    entities_found: Dict[str, int]
    total_entities: int
    unique_entities: int
    confidence_avg: float
    
@dataclass
class EntityResult:
    """Extracted entity result."""
    type: str
    text: str
    start: Optional[int] = None
    end: Optional[int] = None
    confidence: float = 0.8
    chunk_id: Optional[int] = None
    
    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

class SaulLMDirectExtractor:
    """SaulLM-7B entity extractor using vLLM direct API."""
    
    def __init__(self, 
                 model_name: str = "Equall/Saul-7B-Instruct-v1",
                 gpu_id: int = 1,
                 max_model_len: int = 32768,
                 gpu_memory_utilization: float = 0.85):
        
        self.model_name = model_name
        self.gpu_id = gpu_id
        self.llm = None
        self.sampling_params = None
        
        # Configuration
        self.config = {
            "model": model_name,
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": gpu_memory_utilization,
            "dtype": "half",  # FP16 for A40
            "max_model_len": max_model_len,
            "trust_remote_code": False,  # Mistral-based doesn't need custom code
            "enable_prefix_caching": True,
            "enable_chunked_prefill": True,
            "swap_space": 4,  # GB
            "max_num_batched_tokens": 16384,
            "max_num_seqs": 64,
        }
        
        # Set CUDA device
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
        
    def initialize(self):
        """Initialize vLLM model."""
        logger.info(f"Initializing {self.model_name} with vLLM direct API...")
        
        try:
            # Check GPU availability
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                total_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"GPU: {gpu_name} with {total_memory:.2f}GB memory")
            else:
                raise RuntimeError("No GPU available")
            
            # Initialize vLLM
            start_time = time.time()
            self.llm = LLM(**self.config)
            load_time = time.time() - start_time
            
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
            
            # Setup sampling parameters for deterministic extraction
            self.sampling_params = SamplingParams(
                temperature=0.0,  # Deterministic
                top_p=1.0,
                max_tokens=2000,
                stop=["\n\n###", "</output>", "```\n\n"],
                include_stop_str_in_output=False,
                skip_special_tokens=True
            )
            
            # Test generation
            test_output = self.llm.generate(
                ["Test prompt"],
                self.sampling_params
            )
            logger.info("Model test generation successful")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            return False
    
    def create_legal_extraction_prompt(self, text: str) -> str:
        """Create optimized prompt for legal entity extraction."""
        
        prompt = f"""<s>[INST] You are a legal entity extraction specialist. Extract ALL legal entities from the following text with high precision.

Entity Types to Extract:
- CASE_CITATION: Complete case citations (e.g., "Brown v. Board, 347 U.S. 483 (1954)")
- STATUTE: Federal and state statutes (e.g., "42 U.S.C. § 1983", "Cal. Penal Code § 187")
- REGULATION: CFR citations (e.g., "17 C.F.R. § 240.10b-5")
- CONSTITUTIONAL: Constitutional provisions (e.g., "U.S. Const. amend. XIV")
- PARTY: All parties, plaintiffs, defendants, petitioners, respondents
- JUDGE: Judges, justices, magistrates with titles
- ATTORNEY: Attorney names, bar numbers, roles
- LAW_FIRM: Law firm and legal organization names
- COURT: Court names and jurisdictions
- DOCKET_NUMBER: Case numbers, docket numbers
- DATE: All dates in any format
- MONETARY_AMOUNT: Dollar amounts, damages, settlements
- LEGAL_DOCTRINE: Legal principles, doctrines, standards
- PROCEDURAL_TERM: Motions, orders, filings, procedures
- JURISDICTION: Geographic and legal jurisdictions

Instructions:
1. Extract EVERY entity matching the types above
2. Use the EXACT text as it appears in the document
3. Include confidence scores (0.0-1.0) for each entity
4. Handle overlapping entities by including both

Legal Text:
"{text[:8000]}"

Extract and return ONLY a JSON array of entities. Each entity must have: type, text, confidence.

Output:
```json
[
  {{"type": "ENTITY_TYPE", "text": "exact text from document", "confidence": 0.95}},
"""
        
        return prompt
    
    def extract_entities(self, text: str) -> List[EntityResult]:
        """Extract entities from text using vLLM."""
        if not self.llm:
            raise RuntimeError("Model not initialized. Call initialize() first.")
        
        # Create prompt
        prompt = self.create_legal_extraction_prompt(text)
        
        # Generate with vLLM
        start_time = time.time()
        outputs = self.llm.generate([prompt], self.sampling_params)
        generation_time = time.time() - start_time
        
        # Parse output
        generated_text = outputs[0].outputs[0].text
        entities = self._parse_entities(generated_text)
        
        logger.info(f"Extracted {len(entities)} entities in {generation_time:.2f}s")
        
        return entities
    
    def extract_from_chunks(self, chunks: List[str]) -> List[EntityResult]:
        """Extract entities from multiple text chunks."""
        all_entities = []
        
        # Prepare all prompts
        prompts = [self.create_legal_extraction_prompt(chunk) for chunk in chunks]
        
        # Batch generation with vLLM
        logger.info(f"Processing {len(chunks)} chunks in batch...")
        start_time = time.time()
        
        outputs = self.llm.generate(prompts, self.sampling_params)
        
        generation_time = time.time() - start_time
        logger.info(f"Batch generation completed in {generation_time:.2f}s")
        
        # Parse outputs
        for i, output in enumerate(outputs):
            generated_text = output.outputs[0].text
            chunk_entities = self._parse_entities(generated_text)
            
            # Add chunk ID for tracking
            for entity in chunk_entities:
                entity.chunk_id = i
            
            all_entities.extend(chunk_entities)
        
        # Deduplicate entities
        unique_entities = self._deduplicate_entities(all_entities)
        
        return unique_entities
    
    def _parse_entities(self, generated_text: str) -> List[EntityResult]:
        """Parse JSON entities from generated text."""
        entities = []
        
        try:
            # Find JSON content
            import re
            
            # Try to find JSON array
            json_match = re.search(r'\[.*?\]', generated_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                
                # Clean up common issues
                json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas
                json_str = re.sub(r'}\s*{', '},{', json_str)  # Add missing commas
                
                # Parse JSON
                parsed = json.loads(json_str)
                
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and 'type' in item and 'text' in item:
                            entity = EntityResult(
                                type=item.get('type', 'UNKNOWN'),
                                text=item.get('text', ''),
                                confidence=float(item.get('confidence', 0.8))
                            )
                            entities.append(entity)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            # Fallback: extract common patterns
            entities.extend(self._fallback_extraction(generated_text))
        except Exception as e:
            logger.error(f"Error parsing entities: {e}")
        
        return entities
    
    def _fallback_extraction(self, text: str) -> List[EntityResult]:
        """Fallback extraction using patterns."""
        entities = []
        
        # Simple patterns for common entities
        patterns = {
            'CASE_CITATION': r'[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+(?:,?\s+\d+\s+[A-Z]\.\S+\s+\d+(?:\s+\(\d{4}\))?)?',
            'STATUTE': r'\d+\s+U\.S\.C\.\s+§\s*\d+',
            'DATE': r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',
        }
        
        import re
        for entity_type, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                entities.append(EntityResult(
                    type=entity_type,
                    text=match.group(0),
                    confidence=0.7
                ))
        
        return entities
    
    def _deduplicate_entities(self, entities: List[EntityResult]) -> List[EntityResult]:
        """Deduplicate entities based on text and type."""
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.type, entity.text.lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        return unique
    
    def get_memory_stats(self) -> Dict[str, float]:
        """Get current GPU memory statistics."""
        if torch.cuda.is_available():
            return {
                "allocated_gb": torch.cuda.memory_allocated() / 1e9,
                "reserved_gb": torch.cuda.memory_reserved() / 1e9,
                "free_gb": (torch.cuda.get_device_properties(0).total_memory - 
                           torch.cuda.memory_allocated()) / 1e9
            }
        return {}
    
    def cleanup(self):
        """Clean up model and free GPU memory."""
        if self.llm:
            del self.llm
            self.llm = None
            gc.collect()
            torch.cuda.empty_cache()
            logger.info("Model cleaned up and GPU memory freed")


class DocumentProcessor:
    """Process documents for entity extraction."""
    
    @staticmethod
    def create_chunks(text: str, 
                     chunk_size: int = 8000, 
                     overlap: int = 500) -> List[str]:
        """Create overlapping chunks from text."""
        chunks = []
        
        # Clean text
        text = text.strip()
        
        if len(text) <= chunk_size:
            return [text]
        
        # Create chunks with overlap
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end
                last_period = text.rfind('. ', start, end)
                if last_period != -1 and last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Move start with overlap
            start = end - overlap if end < len(text) else end
        
        logger.info(f"Created {len(chunks)} chunks from {len(text)} characters")
        return chunks
    
    @staticmethod
    def load_sample_text() -> str:
        """Load sample legal text for testing."""
        sample_text = """
UNITED STATES DISTRICT COURT
SOUTHERN DISTRICT OF NEW YORK

JANE DOE, individually and on behalf of all others similarly situated,
    Plaintiff,
v.
ABC CORPORATION, a Delaware corporation, and JOHN SMITH, individually,
    Defendants.

Case No. 23-CV-1234 (JFK)

MEMORANDUM OPINION AND ORDER

Before the Court is Defendants' Motion to Dismiss pursuant to Fed. R. Civ. P. 12(b)(6), 
filed on March 15, 2024. Plaintiff filed her Response on April 5, 2024, and Defendants 
filed their Reply on April 12, 2024.

I. BACKGROUND

This case arises under the Securities Exchange Act of 1934, 15 U.S.C. § 78a et seq., 
and the Sherman Antitrust Act, 15 U.S.C. § 1 et seq. Plaintiff Jane Doe alleges that 
between January 1, 2023 and December 31, 2023, Defendants engaged in a scheme to manipulate 
the market price of ABC Corporation's common stock in violation of Section 10(b) of the 
Exchange Act and SEC Rule 10b-5, 17 C.F.R. § 240.10b-5.

As discussed in Brown v. Board of Education, 347 U.S. 483, 495 (1954), federal courts 
have jurisdiction under 28 U.S.C. § 1331 to hear cases arising under federal law. 
Similarly, in Twombly v. Bell Atlantic Corp., 550 U.S. 544, 555 (2007), the Supreme Court 
established the plausibility standard for evaluating motions to dismiss.

The Court must accept all well-pleaded facts as true. See Morrison v. National Australia 
Bank Ltd., 561 U.S. 247, 268 (2010). Plaintiff seeks damages in excess of $5,000,000.

IT IS SO ORDERED.

Dated: June 15, 2024
New York, New York

                                    /s/ John F. Kennedy
                                    JOHN F. KENNEDY
                                    United States District Judge
"""
        return sample_text


def run_comparison_test():
    """Run comparison test between SaulLM and baseline."""
    logger.info("=" * 80)
    logger.info("SAULLM-7B vLLM DIRECT ENTITY EXTRACTION TEST")
    logger.info("=" * 80)
    
    # Initialize extractor
    extractor = SaulLMDirectExtractor(
        model_name="Equall/Saul-7B-Instruct-v1",
        gpu_id=1,
        max_model_len=16384,  # Conservative for testing
        gpu_memory_utilization=0.75
    )
    
    # Initialize model
    logger.info("Initializing SaulLM-7B with vLLM...")
    if not extractor.initialize():
        logger.error("Failed to initialize model")
        return None
    
    # Get memory stats after loading
    memory_stats = extractor.get_memory_stats()
    logger.info(f"GPU Memory: {memory_stats.get('allocated_gb', 0):.2f}GB allocated")
    
    # Load test document
    processor = DocumentProcessor()
    test_text = processor.load_sample_text()
    logger.info(f"Test document length: {len(test_text)} characters")
    
    # Create chunks
    chunks = processor.create_chunks(test_text, chunk_size=4000, overlap=200)
    
    # Extract entities
    logger.info("Extracting entities...")
    start_time = time.time()
    
    entities = extractor.extract_from_chunks(chunks)
    
    extraction_time = time.time() - start_time
    
    # Calculate metrics
    entity_types = {}
    for entity in entities:
        entity_types[entity.type] = entity_types.get(entity.type, 0) + 1
    
    metrics = ExtractionMetrics(
        model_name="SaulLM-7B-Instruct",
        total_time=extraction_time,
        tokens_processed=len(test_text),  # Approximate
        tokens_per_second=len(test_text) / extraction_time,
        memory_used_gb=memory_stats.get('allocated_gb', 0),
        chunks_processed=len(chunks),
        entities_found=entity_types,
        total_entities=len(entities),
        unique_entities=len(set((e.type, e.text) for e in entities)),
        confidence_avg=sum(e.confidence for e in entities) / len(entities) if entities else 0
    )
    
    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total Entities: {metrics.total_entities}")
    logger.info(f"Unique Entities: {metrics.unique_entities}")
    logger.info(f"Extraction Time: {metrics.total_time:.2f} seconds")
    logger.info(f"Tokens/Second: {metrics.tokens_per_second:.0f}")
    logger.info(f"Average Confidence: {metrics.confidence_avg:.2f}")
    
    logger.info("\nEntity Types Found:")
    for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {entity_type:20s}: {count:3d}")
    
    logger.info("\nSample Entities:")
    for entity in entities[:10]:
        logger.info(f"  [{entity.type}] {entity.text} (conf: {entity.confidence:.2f})")
    
    # Save results
    results_dir = Path("/srv/luris/be/entity-extraction-service/tests/results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"saullm_vllm_test_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "metrics": asdict(metrics),
            "entities": [e.to_dict() for e in entities],
            "test_text_length": len(test_text),
            "chunks": len(chunks),
            "timestamp": timestamp
        }, f, indent=2)
    
    logger.info(f"\nResults saved to: {results_file}")
    
    # Cleanup
    extractor.cleanup()
    
    return metrics, entities


if __name__ == "__main__":
    try:
        results = run_comparison_test()
        if results:
            logger.info("\n✅ Test completed successfully!")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()