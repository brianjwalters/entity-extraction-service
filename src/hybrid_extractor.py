#!/usr/bin/env python3
"""
Hybrid Legal Entity Extractor combining regex, few-shot prompting, and fine-tuned LegalBERT.
Implements confidence-based routing and fusion strategies.
"""

import re
import json
import yaml
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging
from jinja2 import Template
import asyncio
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Entity:
    """Represents an extracted entity."""
    type: str
    text: str
    start: int
    end: int
    confidence: float
    source: str  # 'regex', 'few_shot', 'legalbert', 'fusion'
    metadata: Dict[str, Any] = None
    
    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

class HybridEntityExtractor:
    """Orchestrates hybrid entity extraction using multiple methods."""
    
    def __init__(self, 
                 patterns_dir: str = "/srv/luris/be/entity-extraction-service/src/patterns",
                 prompt_template_path: str = "/srv/luris/be/entity-extraction-service/prompts/few_shot_entity_extraction.jinja2",
                 legalbert_model_path: str = "/srv/luris/be/entity-extraction-service/models/legalbert-ner",
                 vllm_url: str = "http://localhost:8080/v1",
                 use_gpu: bool = True):
        
        self.patterns_dir = Path(patterns_dir)
        self.prompt_template_path = Path(prompt_template_path)
        self.legalbert_model_path = Path(legalbert_model_path)
        self.vllm_url = vllm_url
        self.use_gpu = use_gpu and torch.cuda.is_available()
        
        # Load components
        self.regex_patterns = self._load_regex_patterns()
        self.prompt_template = self._load_prompt_template()
        self.example_bank = self._load_example_bank()
        self.entity_descriptions = self._load_entity_descriptions()
        
        # Initialize models (lazy loading)
        self.legalbert_model = None
        self.tokenizer = None
        
        # Configuration
        self.confidence_thresholds = {
            'regex': 0.9,      # High confidence for regex
            'few_shot': 0.7,   # Medium for few-shot
            'legalbert': 0.8   # High for fine-tuned model
        }
        
    def _load_regex_patterns(self) -> Dict[str, List[Dict]]:
        """Load all regex patterns from YAML files."""
        patterns_by_type = defaultdict(list)
        
        for yaml_file in self.patterns_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._extract_patterns(data, patterns_by_type)
            except Exception as e:
                logger.warning(f"Error loading {yaml_file}: {e}")
        
        logger.info(f"Loaded {sum(len(p) for p in patterns_by_type.values())} regex patterns for {len(patterns_by_type)} entity types")
        return dict(patterns_by_type)
    
    def _extract_patterns(self, data: Any, patterns_by_type: Dict, path: str = ""):
        """Recursively extract patterns from YAML data."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and 'pattern' in value:
                    entity_type = value.get('entity_type', key.upper())
                    patterns_by_type[entity_type].append({
                        'pattern': value['pattern'],
                        'confidence': value.get('confidence', 0.9),
                        'name': key
                    })
                else:
                    self._extract_patterns(value, patterns_by_type, f"{path}.{key}" if path else key)
        elif isinstance(data, list):
            for item in data:
                self._extract_patterns(item, patterns_by_type, path)
    
    def _load_prompt_template(self) -> Template:
        """Load Jinja2 prompt template."""
        if self.prompt_template_path.exists():
            with open(self.prompt_template_path, 'r') as f:
                return Template(f.read())
        else:
            # Default template
            return Template("""
Extract legal entities from the following text:

Text: "{{ input_text }}"

Entity types to extract: {{ entity_types | join(', ') }}

Return entities in JSON format with type, text, start, end, and confidence.
""")
    
    def _load_example_bank(self) -> List[Dict]:
        """Load example bank for few-shot prompting."""
        examples_file = Path("/srv/luris/be/entity-extraction-service/training/data/bio_training_examples.json")
        if examples_file.exists():
            with open(examples_file, 'r') as f:
                data = json.load(f)
                # Convert to simple format
                examples = []
                for item in data[:100]:  # Use first 100 as examples
                    if 'original_text' in item and 'entities' in item:
                        examples.append({
                            'text': item['original_text'],
                            'entities': item['entities']
                        })
                return examples
        return []
    
    def _load_entity_descriptions(self) -> Dict[str, str]:
        """Load entity type descriptions."""
        return {
            'CASE_CITATION': 'Legal case citations (e.g., Brown v. Board, 347 U.S. 483)',
            'STATUTE': 'Statutory references (e.g., 42 U.S.C. § 1983)',
            'DATE': 'Dates in various formats',
            'PARTY': 'Parties involved in legal proceedings',
            'ATTORNEY': 'Attorney names and titles',
            'JUDGE': 'Judge names and titles',
            'COURT': 'Court names and jurisdictions',
            'MONETARY_AMOUNT': 'Dollar amounts and financial figures',
            'LEGAL_DOCTRINE': 'Legal doctrines and principles',
            'PROCEDURAL_TERM': 'Procedural legal terms',
            'DOCKET_NUMBER': 'Case docket numbers',
            'REGULATION_CITATION': 'Regulatory citations (CFR)',
            'CONSTITUTIONAL_CITATION': 'Constitutional provisions',
            'ADDRESS': 'Physical addresses',
            'LAW_FIRM': 'Law firm names',
            'LEGAL_TERM': 'General legal terminology'
        }
    
    async def extract_entities(self, text: str, 
                              methods: List[str] = ['regex', 'few_shot', 'legalbert'],
                              fusion_strategy: str = 'confidence_weighted') -> List[Entity]:
        """
        Extract entities using specified methods and fusion strategy.
        
        Args:
            text: Input text to extract entities from
            methods: List of extraction methods to use
            fusion_strategy: How to combine results ('confidence_weighted', 'union', 'intersection', 'cascade')
        
        Returns:
            List of extracted entities
        """
        all_entities = []
        
        # Run extraction methods
        if 'regex' in methods:
            regex_entities = self._extract_with_regex(text)
            all_entities.extend(regex_entities)
            logger.info(f"Regex extracted {len(regex_entities)} entities")
        
        if 'few_shot' in methods:
            few_shot_entities = await self._extract_with_few_shot(text)
            all_entities.extend(few_shot_entities)
            logger.info(f"Few-shot extracted {len(few_shot_entities)} entities")
        
        if 'legalbert' in methods:
            legalbert_entities = self._extract_with_legalbert(text)
            all_entities.extend(legalbert_entities)
            logger.info(f"LegalBERT extracted {len(legalbert_entities)} entities")
        
        # Apply fusion strategy
        fused_entities = self._apply_fusion_strategy(all_entities, fusion_strategy)
        
        # Sort by position
        fused_entities.sort(key=lambda e: (e.start, e.end))
        
        return fused_entities
    
    def _extract_with_regex(self, text: str) -> List[Entity]:
        """Extract entities using regex patterns."""
        entities = []
        
        for entity_type, patterns in self.regex_patterns.items():
            for pattern_info in patterns:
                try:
                    pattern = pattern_info['pattern']
                    regex = re.compile(pattern, re.IGNORECASE | re.VERBOSE)
                    
                    for match in regex.finditer(text):
                        entity = Entity(
                            type=entity_type,
                            text=match.group(0),
                            start=match.start(),
                            end=match.end(),
                            confidence=pattern_info['confidence'],
                            source='regex',
                            metadata={'pattern_name': pattern_info['name']}
                        )
                        entities.append(entity)
                        
                except re.error as e:
                    logger.debug(f"Regex error for pattern {pattern_info['name']}: {e}")
        
        return entities
    
    async def _extract_with_few_shot(self, text: str) -> List[Entity]:
        """Extract entities using few-shot prompting with vLLM."""
        entities = []
        
        # Select relevant examples
        selected_examples = self._select_examples(text)
        
        # Get entity types to extract
        entity_types = list(self.entity_descriptions.keys())
        
        # Create prompt
        prompt = self.prompt_template.render(
            input_text=text,
            entity_types=entity_types,
            entity_descriptions=self.entity_descriptions,
            selected_examples=selected_examples
        )
        
        # Call vLLM API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.vllm_url}/chat/completions",
                    json={
                        "model": "granite-3.3-2b-instruct",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Parse JSON response
                        try:
                            # Extract JSON from response
                            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                            else:
                                json_str = content
                            
                            data = json.loads(json_str)
                            
                            for entity_dict in data.get('entities', []):
                                entity = Entity(
                                    type=entity_dict['type'],
                                    text=entity_dict['text'],
                                    start=entity_dict['start'],
                                    end=entity_dict['end'],
                                    confidence=entity_dict.get('confidence', 0.7),
                                    source='few_shot'
                                )
                                entities.append(entity)
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse LLM response: {e}")
                    
        except Exception as e:
            logger.error(f"Error calling vLLM API: {e}")
        
        return entities
    
    def _extract_with_legalbert(self, text: str) -> List[Entity]:
        """Extract entities using fine-tuned LegalBERT model."""
        entities = []
        
        # Load model if not already loaded
        if self.legalbert_model is None:
            self._load_legalbert_model()
        
        if self.legalbert_model is None:
            logger.warning("LegalBERT model not available")
            return entities
        
        # Tokenize text
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt"
        )
        
        if self.use_gpu:
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = self.legalbert_model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=-1)
            probabilities = torch.softmax(outputs.logits, dim=-1)
        
        # Convert predictions to entities
        tokens = self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
        word_ids = inputs.word_ids(0)
        
        current_entity = None
        entities_dict = {}
        
        for idx, (token, word_id, pred_id, probs) in enumerate(zip(tokens, word_ids, predictions[0], probabilities[0])):
            if word_id is None:  # Special token
                continue
            
            label = self.legalbert_model.config.id2label.get(pred_id.item(), 'O')
            confidence = probs[pred_id].item()
            
            if label != 'O':
                # Extract entity type and BIO tag
                if '-' in label:
                    bio_tag, entity_type = label.split('-', 1)
                else:
                    bio_tag, entity_type = 'B', label
                
                # Calculate position in original text
                token_start = inputs['offset_mapping'][0][idx][0].item() if hasattr(inputs, 'offset_mapping') else 0
                token_end = inputs['offset_mapping'][0][idx][1].item() if hasattr(inputs, 'offset_mapping') else len(text)
                
                if bio_tag == 'B':
                    # Start new entity
                    if current_entity:
                        entities.append(current_entity)
                    
                    current_entity = Entity(
                        type=entity_type,
                        text=text[token_start:token_end],
                        start=token_start,
                        end=token_end,
                        confidence=confidence,
                        source='legalbert'
                    )
                elif bio_tag == 'I' and current_entity and current_entity.type == entity_type:
                    # Continue entity
                    current_entity.end = token_end
                    current_entity.text = text[current_entity.start:current_entity.end]
                    current_entity.confidence = (current_entity.confidence + confidence) / 2
            else:
                # End current entity
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
        
        # Add final entity
        if current_entity:
            entities.append(current_entity)
        
        return entities
    
    def _load_legalbert_model(self):
        """Load fine-tuned LegalBERT model."""
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification
            
            if self.legalbert_model_path.exists():
                self.tokenizer = AutoTokenizer.from_pretrained(str(self.legalbert_model_path))
                self.legalbert_model = AutoModelForTokenClassification.from_pretrained(str(self.legalbert_model_path))
                
                if self.use_gpu:
                    self.legalbert_model = self.legalbert_model.cuda()
                
                self.legalbert_model.eval()
                logger.info("Loaded fine-tuned LegalBERT model")
            else:
                logger.warning(f"LegalBERT model not found at {self.legalbert_model_path}")
                
        except Exception as e:
            logger.error(f"Error loading LegalBERT model: {e}")
    
    def _select_examples(self, text: str, max_examples: int = 10) -> List[Dict]:
        """Select relevant examples for few-shot prompting."""
        if not self.example_bank:
            return []
        
        # Simple selection: random sampling
        # TODO: Implement smarter selection based on similarity
        import random
        selected = random.sample(self.example_bank, min(max_examples, len(self.example_bank)))
        
        return selected
    
    def _apply_fusion_strategy(self, entities: List[Entity], strategy: str) -> List[Entity]:
        """Apply fusion strategy to combine entities from different sources."""
        if strategy == 'union':
            return self._fusion_union(entities)
        elif strategy == 'intersection':
            return self._fusion_intersection(entities)
        elif strategy == 'cascade':
            return self._fusion_cascade(entities)
        else:  # confidence_weighted
            return self._fusion_confidence_weighted(entities)
    
    def _fusion_confidence_weighted(self, entities: List[Entity]) -> List[Entity]:
        """Combine entities using confidence-weighted voting."""
        # Group overlapping entities
        entity_groups = self._group_overlapping_entities(entities)
        
        fused = []
        for group in entity_groups:
            if len(group) == 1:
                fused.append(group[0])
            else:
                # Weighted voting
                best_entity = max(group, key=lambda e: e.confidence)
                
                # Boost confidence if multiple sources agree
                sources = set(e.source for e in group)
                if len(sources) > 1:
                    best_entity.confidence = min(0.99, best_entity.confidence * 1.1)
                    best_entity.source = 'fusion'
                    best_entity.metadata = {'sources': list(sources)}
                
                fused.append(best_entity)
        
        return fused
    
    def _fusion_union(self, entities: List[Entity]) -> List[Entity]:
        """Keep all entities (union of all methods)."""
        # Remove exact duplicates
        seen = set()
        unique = []
        
        for entity in entities:
            key = (entity.type, entity.text, entity.start, entity.end)
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        
        return unique
    
    def _fusion_intersection(self, entities: List[Entity]) -> List[Entity]:
        """Keep only entities found by multiple methods."""
        # Group overlapping entities
        entity_groups = self._group_overlapping_entities(entities)
        
        fused = []
        for group in entity_groups:
            sources = set(e.source for e in group)
            if len(sources) > 1:
                # Take highest confidence entity from group
                best_entity = max(group, key=lambda e: e.confidence)
                best_entity.source = 'fusion'
                best_entity.metadata = {'sources': list(sources)}
                fused.append(best_entity)
        
        return fused
    
    def _fusion_cascade(self, entities: List[Entity]) -> List[Entity]:
        """Use cascade: regex first, then LLM for gaps, then LegalBERT for remaining."""
        # Sort by source priority
        priority = {'regex': 1, 'legalbert': 2, 'few_shot': 3}
        entities.sort(key=lambda e: (priority.get(e.source, 4), -e.confidence))
        
        # Remove overlaps, keeping higher priority
        fused = []
        covered_spans = []
        
        for entity in entities:
            # Check if this span is already covered
            overlaps = False
            for start, end in covered_spans:
                if (entity.start >= start and entity.start < end) or \
                   (entity.end > start and entity.end <= end):
                    overlaps = True
                    break
            
            if not overlaps:
                fused.append(entity)
                covered_spans.append((entity.start, entity.end))
        
        return fused
    
    def _group_overlapping_entities(self, entities: List[Entity]) -> List[List[Entity]]:
        """Group entities that overlap in position."""
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda e: (e.start, e.end))
        
        groups = []
        current_group = [sorted_entities[0]]
        
        for entity in sorted_entities[1:]:
            # Check if overlaps with any entity in current group
            overlaps = False
            for group_entity in current_group:
                if (entity.start >= group_entity.start and entity.start < group_entity.end) or \
                   (entity.end > group_entity.start and entity.end <= group_entity.end) or \
                   (group_entity.start >= entity.start and group_entity.start < entity.end):
                    overlaps = True
                    break
            
            if overlaps:
                current_group.append(entity)
            else:
                groups.append(current_group)
                current_group = [entity]
        
        if current_group:
            groups.append(current_group)
        
        return groups

async def test_hybrid_extraction():
    """Test the hybrid extraction system."""
    extractor = HybridEntityExtractor()
    
    # Test text
    test_text = """
    In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court held on May 17, 1954 
    that racial segregation violated the Equal Protection Clause of the Fourteenth Amendment. 
    Chief Justice Earl Warren delivered the unanimous opinion, finding that separate educational 
    facilities are inherently unequal. The case overturned Plessy v. Ferguson, 163 U.S. 537 (1896).
    """
    
    # Extract entities
    entities = await extractor.extract_entities(
        test_text,
        methods=['regex'],  # Start with just regex for testing
        fusion_strategy='confidence_weighted'
    )
    
    print(f"\nExtracted {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.type}: '{entity.text}' [{entity.start}:{entity.end}] (conf: {entity.confidence:.2f}, source: {entity.source})")

if __name__ == "__main__":
    asyncio.run(test_hybrid_extraction())