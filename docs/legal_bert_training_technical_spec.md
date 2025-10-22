# Legal-BERT Training Technical Specification Document

## Executive Summary

This document provides a comprehensive technical specification for training a custom Legal-BERT model using the existing Entity Extraction Service's patterns, examples, and relationship data to significantly enhance entity recognition and relationship extraction performance.

### Key Objectives
- **Leverage Existing Assets**: Utilize 664 regex patterns, 272 entity types, and existing examples from `/patterns/detailed` endpoint
- **Synthetic Training Data Generation**: Transform entity examples into annotated training sentences
- **Multi-Task Learning**: Train simultaneous entity recognition and relationship extraction
- **100-Epoch Training**: Comprehensive fine-tuning for maximum accuracy
- **Performance Enhancement**: Achieve >95% entity accuracy and >90% relationship accuracy

---

## 1. Project Overview

### 1.1 Current State Analysis

#### Entity Extraction Service Assets
- **664 Regex Patterns**: Loaded from 74 YAML files
- **272 Entity Types**: 160 EntityType + 112 CitationType enums
- **Pattern Examples**: Available through `/patterns/detailed` endpoint
- **Relationship Types**: 40+ legal relationships (decided_by, filed_by, represents, etc.)
- **Performance**: Current 176ms processing time with 94% GPU utilization

#### Key Endpoints to Leverage
```bash
# Primary data source
GET /api/v1/patterns/detailed
GET /api/v1/entity-types?include_examples=true
GET /api/v1/patterns/comprehensive?entity_type=ALL

# Training integration points (if available)
POST /api/v1/training/data/prepare
POST /api/v1/training/models/train
GET /api/v1/training/status/{training_id}
```

### 1.2 Training Objectives

#### Performance Targets
- **Entity Recognition F1**: >95% (vs current ~87%)
- **Relationship Extraction F1**: >90% (vs current ~80%)
- **Inference Speed**: <100ms per document (vs current 176ms)
- **Training Duration**: 100 epochs over 48-72 hours
- **Model Size**: <2GB for deployment efficiency

#### Accuracy Improvements
- **State Statute Recognition**: >98% (with jurisdiction context)
- **Case Citation Extraction**: >97% (Bluebook compliant)
- **Party Relationship Mapping**: >92% (complex legal relationships)
- **Financial Entity Extraction**: >95% (monetary amounts, damages)

---

## 2. Technical Architecture

### 2.1 Data Pipeline Architecture

```mermaid
graph TB
    subgraph "Entity Extraction Service"
        A[/patterns/detailed API] --> B[Pattern Examples]
        C[/entity-types API] --> D[Entity Definitions]
        E[Existing Relationships] --> F[Relationship Examples]
    end
    
    subgraph "Data Generation Pipeline"
        B --> G[Example Extraction]
        D --> G
        F --> G
        G --> H[Sentence Generation]
        H --> I[Context Annotation]
        I --> J[JSON Dataset Creation]
    end
    
    subgraph "Legal-BERT Training"
        J --> K[Multi-Task Trainer]
        K --> L[Entity Recognition Head]
        K --> M[Relationship Extraction Head]
        L --> N[Trained Entity Model]
        M --> O[Trained Relationship Model]
    end
    
    subgraph "Evaluation & Deployment"
        N --> P[Model Validation]
        O --> P
        P --> Q[Performance Testing]
        Q --> R[Production Deployment]
    end
```

### 2.2 Training Data Structure

#### JSON Training Example Format
```json
{
  "id": "train_example_001",
  "source_entity_type": "STATE_STATUTE",
  "source_example": "Cal. Civ. Code § 1950.5",
  "enhanced_sentence": "Under Cal. Civ. Code § 1950.5, landlords must return security deposits within 21 days after tenant vacates the premises.",
  "annotations": {
    "entities": [
      {
        "text": "Cal. Civ. Code § 1950.5",
        "label": "STATE_STATUTE",
        "start_pos": 6,
        "end_pos": 29,
        "attributes": {
          "state": "California",
          "code_type": "Civil Code",
          "section": "1950.5",
          "subject_matter": "security deposits"
        }
      },
      {
        "text": "21 days",
        "label": "DEADLINE", 
        "start_pos": 89,
        "end_pos": 96,
        "attributes": {
          "duration": "21 days",
          "trigger_event": "tenant vacates"
        }
      }
    ],
    "relationships": [
      {
        "source_entity": "Cal. Civ. Code § 1950.5",
        "target_entity": "21 days",
        "relationship_type": "establishes_deadline",
        "evidence_text": "landlords must return security deposits within 21 days",
        "confidence": 0.95
      }
    ]
  },
  "sentence_variants": [
    "California Civil Code Section 1950.5 requires landlords to return deposits within 21 days.",
    "The statute Cal. Civ. Code § 1950.5 mandates a 21-day return period for security deposits.",
    "Per Cal. Civ. Code § 1950.5, security deposit returns are due within 21 days of vacancy."
  ]
}
```

### 2.3 Model Architecture

#### Multi-Task Legal-BERT Configuration
```python
class LegalBERTMultiTask(nn.Module):
    def __init__(self, config):
        super().__init__()
        # Base Legal-BERT model
        self.legal_bert = AutoModel.from_pretrained("nlpaueb/legal-bert-base-uncased")
        
        # Entity recognition head
        self.entity_classifier = nn.Linear(
            config.hidden_size, 
            len(ENTITY_LABELS)  # 544 labels (272 types * 2 BIO + O)
        )
        
        # Relationship extraction head  
        self.relationship_classifier = nn.Linear(
            config.hidden_size * 2,  # Concatenated entity representations
            len(RELATIONSHIP_TYPES)  # 40+ relationship types
        )
        
        # Dropout for regularization
        self.dropout = nn.Dropout(config.dropout_prob)
        
    def forward(self, input_ids, attention_mask, entity_positions=None):
        # Get contextual representations
        outputs = self.legal_bert(input_ids, attention_mask)
        sequence_output = outputs.last_hidden_state
        
        # Entity recognition
        entity_logits = self.entity_classifier(self.dropout(sequence_output))
        
        # Relationship extraction (if entity positions provided)
        relationship_logits = None
        if entity_positions is not None:
            relationship_logits = self._extract_relationships(
                sequence_output, entity_positions
            )
        
        return {
            'entity_logits': entity_logits,
            'relationship_logits': relationship_logits
        }
```

---

## 3. Data Generation Strategy

### 3.1 Entity Example Extraction

#### Primary Data Source Integration
```python
class EntityExampleExtractor:
    """Extract examples from Entity Extraction Service patterns"""
    
    def __init__(self, service_url="http://localhost:8007/api/v1"):
        self.service_url = service_url
        self.session = requests.Session()
    
    async def extract_all_examples(self) -> Dict[str, List[Dict]]:
        """Extract all entity examples with patterns"""
        
        # Get all patterns with examples
        response = await self.session.get(
            f"{self.service_url}/patterns/detailed?include_examples=true"
        )
        patterns_data = response.json()
        
        # Get entity type definitions
        entity_response = await self.session.get(
            f"{self.service_url}/entity-types?include_examples=true"
        )
        entity_data = entity_response.json()
        
        # Combine and organize examples
        examples_by_type = {}
        
        # Process pattern examples (with regex patterns)
        for pattern in patterns_data.get('patterns', []):
            entity_type = pattern['entity_type']
            if entity_type not in examples_by_type:
                examples_by_type[entity_type] = []
            
            for example in pattern.get('examples', []):
                examples_by_type[entity_type].append({
                    'text': example,
                    'source': 'pattern',
                    'pattern': pattern.get('pattern'),
                    'confidence': pattern.get('confidence', 0.8),
                    'category': pattern.get('category'),
                    'jurisdiction': pattern.get('jurisdiction')
                })
        
        # Process entity type examples (recognition examples)
        for entity in entity_data.get('entity_types', []):
            entity_type = entity['name']
            if entity_type not in examples_by_type:
                examples_by_type[entity_type] = []
            
            for example in entity.get('recognition_examples', []):
                examples_by_type[entity_type].append({
                    'text': example,
                    'source': 'recognition',
                    'pattern': None,
                    'confidence': 0.9,
                    'category': entity.get('category'),
                    'description': entity.get('description')
                })
        
        return examples_by_type
    
    def get_entity_attributes(self, entity_type: str, example: str) -> Dict[str, Any]:
        """Generate contextual attributes for entity"""
        attributes = {}
        
        if entity_type == "STATE_STATUTE":
            # Extract state information
            state_patterns = {
                r'\bCal\.': 'California',
                r'\bN\.Y\.': 'New York', 
                r'\bTex\.': 'Texas',
                r'\bFla\.': 'Florida'
            }
            for pattern, state in state_patterns.items():
                if re.search(pattern, example):
                    attributes['state'] = state
                    break
        
        elif entity_type == "CASE_CITATION":
            # Extract citation components
            if match := re.search(r'(\d+)\s+([A-Z][a-z.]+)\s+(\d+)', example):
                attributes['volume'] = match.group(1)
                attributes['reporter'] = match.group(2)
                attributes['page'] = match.group(3)
        
        elif entity_type == "MONETARY_AMOUNT":
            # Extract amount and currency
            if match := re.search(r'\$?([\d,]+(?:\.\d{2})?)', example):
                attributes['amount'] = match.group(1)
                attributes['currency'] = 'USD'
        
        return attributes
```

### 3.2 Sentence Generation

#### Contextual Sentence Creation
```python
class LegalSentenceGenerator:
    """Generate realistic legal sentences containing entity examples"""
    
    def __init__(self, prompt_client):
        self.prompt_client = prompt_client
        self.sentence_templates = self._load_sentence_templates()
    
    def _load_sentence_templates(self) -> Dict[str, List[str]]:
        """Load sentence templates by entity category"""
        return {
            "case_citations": [
                "In {example}, the court held that {legal_principle}.",
                "The landmark decision in {example} established {legal_doctrine}.",
                "Plaintiff cites {example} in support of their motion for summary judgment.",
                "The defendant's reliance on {example} is misplaced because {distinguishing_factor}."
            ],
            "statutes": [
                "Under {example}, {legal_requirement}.",
                "Section {example} provides that {statutory_language}.",
                "Plaintiff alleges violations of {example} based on {factual_allegations}.",
                "The statute {example} was enacted to {legislative_purpose}."
            ],
            "courts": [
                "The {example} has jurisdiction over {matter_type}.",
                "This matter was filed in the {example} on {date}.",
                "The {example} granted defendant's motion to dismiss.",
                "Plaintiff seeks to remove this case to the {example}."
            ],
            "parties": [
                "{example} filed a motion for preliminary injunction.",
                "The court ordered {example} to produce documents by {deadline}.",
                "Settlement negotiations between {example} and opposing counsel continued.",
                "{example} was served with the complaint on {date}."
            ],
            "monetary_amounts": [
                "The jury awarded {example} in damages to the plaintiff.",
                "Defendant agreed to pay {example} to settle all claims.",
                "Attorney's fees in the amount of {example} were awarded.",
                "The contract specified liquidated damages of {example}."
            ]
        }
    
    async def generate_sentences(self, entity_type: str, example: str, count: int = 4) -> List[str]:
        """Generate multiple sentences containing the entity example"""
        
        category = self._get_entity_category(entity_type)
        templates = self.sentence_templates.get(category, self.sentence_templates["case_citations"])
        
        sentences = []
        
        # Use templates for basic sentence generation
        for i, template in enumerate(templates[:count]):
            sentence = self._fill_template(template, example, entity_type)
            sentences.append(sentence)
        
        # Use AI for additional creative sentences if needed
        if count > len(templates):
            ai_sentences = await self._generate_ai_sentences(entity_type, example, count - len(templates))
            sentences.extend(ai_sentences)
        
        return sentences
    
    def _fill_template(self, template: str, example: str, entity_type: str) -> str:
        """Fill sentence template with contextual information"""
        
        # Fill in the entity example
        sentence = template.format(example=example, **self._get_context_vars(entity_type))
        
        return sentence
    
    def _get_context_vars(self, entity_type: str) -> Dict[str, str]:
        """Generate contextual variables for sentence templates"""
        
        context_vars = {
            "legal_principle": "due process requires adequate notice",
            "legal_doctrine": "the separate but equal doctrine",
            "distinguishing_factor": "the facts here involve a different constitutional standard",
            "legal_requirement": "defendants must respond within 30 days",
            "statutory_language": "no person shall be deprived of property without due process",
            "factual_allegations": "defendant's failure to provide adequate security measures",
            "legislative_purpose": "protect consumers from unfair business practices",
            "matter_type": "federal civil rights claims",
            "date": "January 15, 2024",
            "deadline": "March 1, 2024"
        }
        
        return context_vars
    
    async def _generate_ai_sentences(self, entity_type: str, example: str, count: int) -> List[str]:
        """Use AI to generate additional contextual sentences"""
        
        prompt = f"""Generate {count} realistic legal sentences that naturally contain the {entity_type} "{example}". 
        The sentences should be typical of legal documents like briefs, motions, or court opinions.
        Make each sentence different in structure and context.
        
        Entity Type: {entity_type}
        Entity Example: {example}
        
        Requirements:
        - Each sentence must contain the exact text "{example}"
        - Sentences should sound like professional legal writing
        - Vary the context (motions, court decisions, legal analysis, etc.)
        - Keep sentences 15-30 words long
        
        Format as a numbered list."""
        
        response = await self.prompt_client.simple_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        # Extract sentences from AI response
        sentences = []
        for line in response.content.split('\n'):
            if re.match(r'^\d+\.', line.strip()):
                sentence = re.sub(r'^\d+\.\s*', '', line.strip())
                if sentence and example in sentence:
                    sentences.append(sentence)
        
        return sentences[:count]
```

### 3.3 Relationship Annotation

#### Legal Relationship Extraction
```python
class LegalRelationshipAnnotator:
    """Annotate relationships between entities in generated sentences"""
    
    def __init__(self):
        self.relationship_patterns = self._initialize_relationship_patterns()
    
    def _initialize_relationship_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize patterns for detecting legal relationships"""
        return {
            "decided_by": [
                {"pattern": r"(.+?) held that (.+)", "roles": ["court", "ruling"]},
                {"pattern": r"In (.+?), (.+?) ruled", "roles": ["case", "court"]},
                {"pattern": r"(.+?) delivered the opinion", "roles": ["judge", "opinion"]}
            ],
            "filed_by": [
                {"pattern": r"(.+?) filed (.+)", "roles": ["party", "document"]},
                {"pattern": r"(.+?) was filed by (.+)", "roles": ["document", "party"]}
            ],
            "represents": [
                {"pattern": r"(.+?) represents (.+)", "roles": ["attorney", "client"]},
                {"pattern": r"counsel for (.+)", "roles": ["attorney", "client"]}
            ],
            "awarded_to": [
                {"pattern": r"awarded (.+?) to (.+)", "roles": ["amount", "recipient"]},
                {"pattern": r"(.+?) was awarded (.+)", "roles": ["recipient", "amount"]}
            ],
            "establishes_deadline": [
                {"pattern": r"(.+?) (?:requires|mandates) (.+?) within (.+)", "roles": ["statute", "action", "deadline"]},
                {"pattern": r"under (.+?), (.+?) must (.+?) by (.+)", "roles": ["statute", "party", "action", "deadline"]}
            ]
        }
    
    def extract_relationships(self, sentence: str, entities: List[Dict]) -> List[Dict]:
        """Extract relationships between entities in sentence"""
        
        relationships = []
        
        # Create entity lookup by position
        entity_spans = [(e['start_pos'], e['end_pos'], e) for e in entities]
        entity_spans.sort()  # Sort by start position
        
        # Check each relationship pattern
        for rel_type, patterns in self.relationship_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                match = re.search(pattern, sentence, re.IGNORECASE)
                
                if match:
                    # Find entities in matched groups
                    groups = match.groups()
                    entity_matches = self._map_groups_to_entities(groups, entity_spans, sentence)
                    
                    # Create relationship if we found entity pairs
                    if len(entity_matches) >= 2:
                        for i, source_entity in enumerate(entity_matches[:-1]):
                            for target_entity in entity_matches[i+1:]:
                                relationship = {
                                    "source_entity": source_entity['text'],
                                    "target_entity": target_entity['text'],
                                    "relationship_type": rel_type,
                                    "evidence_text": match.group(0),
                                    "confidence": 0.8,
                                    "pattern_match": pattern
                                }
                                relationships.append(relationship)
        
        return relationships
    
    def _map_groups_to_entities(self, groups: tuple, entity_spans: List[tuple], sentence: str) -> List[Dict]:
        """Map regex groups to actual entities"""
        
        entity_matches = []
        
        for group_text in groups:
            if not group_text:
                continue
            
            # Find group position in sentence
            group_start = sentence.find(group_text)
            if group_start == -1:
                continue
            
            group_end = group_start + len(group_text)
            
            # Find overlapping entities
            for ent_start, ent_end, entity in entity_spans:
                # Check for overlap
                if (ent_start < group_end and ent_end > group_start):
                    entity_matches.append(entity)
                    break
        
        return entity_matches
```

---

## 4. Training Implementation

### 4.1 Training Configuration

#### Comprehensive Training Parameters
```python
@dataclass
class LegalBERTTrainingConfig:
    """Complete training configuration for Legal-BERT"""
    
    # Model configuration
    model_name: str = "nlpaueb/legal-bert-base-uncased"
    output_dir: str = "./legal-bert-enhanced-100epochs"
    
    # Training parameters (100 epochs as specified)
    num_train_epochs: int = 100
    per_device_train_batch_size: int = 8
    per_device_eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    
    # Learning rate schedule (critical for 100 epochs)
    learning_rate: float = 2e-5
    warmup_ratio: float = 0.1  # 10% warmup for long training
    lr_scheduler_type: str = "cosine"  # Cosine decay for stability
    
    # Regularization (important for long training)
    weight_decay: float = 0.01
    dropout_rate: float = 0.1
    attention_dropout: float = 0.1
    
    # Multi-task learning weights
    entity_loss_weight: float = 0.6
    relationship_loss_weight: float = 0.4
    
    # Data parameters
    max_length: int = 512
    test_size: float = 0.15
    val_size: float = 0.10
    
    # Optimization
    optimizer: str = "adamw"
    adam_beta1: float = 0.9
    adam_beta2: float = 0.999
    adam_epsilon: float = 1e-8
    max_grad_norm: float = 1.0
    
    # Evaluation and saving
    evaluation_strategy: str = "steps"
    eval_steps: int = 500
    save_steps: int = 1000
    save_total_limit: int = 5
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_combined_f1"
    greater_is_better: bool = True
    
    # Early stopping (for 100 epochs)
    early_stopping_patience: int = 10
    early_stopping_threshold: float = 0.001
    
    # Logging
    logging_steps: int = 100
    report_to: List[str] = field(default_factory=lambda: ["tensorboard"])
    
    # Hardware optimization
    fp16: bool = True
    dataloader_num_workers: int = 4
    remove_unused_columns: bool = True
    
    # Advanced features
    label_smoothing_factor: float = 0.1
    warmup_steps: int = 0  # Calculated from warmup_ratio
```

### 4.2 Training Data Loader

#### Optimized Dataset Implementation
```python
class LegalBERTDataset(Dataset):
    """Optimized dataset for Legal-BERT training"""
    
    def __init__(self, 
                 training_examples: List[Dict], 
                 tokenizer,
                 config: LegalBERTTrainingConfig,
                 entity_to_id: Dict[str, int],
                 relationship_to_id: Dict[str, int]):
        
        self.examples = training_examples
        self.tokenizer = tokenizer
        self.config = config
        self.entity_to_id = entity_to_id
        self.relationship_to_id = relationship_to_id
        
        # Pre-process all examples for faster training
        self.processed_examples = []
        self._preprocess_examples()
    
    def _preprocess_examples(self):
        """Pre-process all examples to avoid repetitive work during training"""
        
        logger.info(f"Pre-processing {len(self.examples)} training examples...")
        
        for example in tqdm(self.examples):
            processed = self._process_single_example(example)
            if processed:
                self.processed_examples.append(processed)
        
        logger.info(f"Pre-processed {len(self.processed_examples)} valid examples")
    
    def _process_single_example(self, example: Dict) -> Optional[Dict]:
        """Process single training example"""
        
        try:
            # Get the enhanced sentence
            sentence = example['enhanced_sentence']
            
            # Tokenize
            encoding = self.tokenizer(
                sentence,
                truncation=True,
                padding='max_length',
                max_length=self.config.max_length,
                return_offsets_mapping=True,
                return_tensors='pt'
            )
            
            # Create entity labels (BIO format)
            entity_labels = self._create_entity_labels(
                example['annotations']['entities'],
                encoding['offset_mapping'][0]
            )
            
            # Create relationship pairs and labels
            relationship_data = self._create_relationship_data(
                example['annotations']['relationships'],
                example['annotations']['entities']
            )
            
            return {
                'input_ids': encoding['input_ids'].flatten(),
                'attention_mask': encoding['attention_mask'].flatten(),
                'entity_labels': torch.tensor(entity_labels, dtype=torch.long),
                'relationship_pairs': relationship_data['pairs'],
                'relationship_labels': torch.tensor(relationship_data['labels'], dtype=torch.long),
                'sentence_id': example.get('id', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Error processing example {example.get('id', 'unknown')}: {e}")
            return None
    
    def _create_entity_labels(self, entities: List[Dict], offset_mapping) -> List[int]:
        """Create BIO entity labels for token classification"""
        
        labels = [self.entity_to_id['O']] * len(offset_mapping)
        
        for entity in entities:
            start_char = entity['start_pos']
            end_char = entity['end_pos']
            entity_type = entity['label']
            
            if entity_type not in self.entity_to_id:
                continue
            
            # Find overlapping tokens
            entity_tokens = []
            for i, (start, end) in enumerate(offset_mapping):
                if start == 0 and end == 0:  # Special tokens
                    continue
                
                # Check for overlap with entity
                if start < end_char and end > start_char:
                    entity_tokens.append(i)
            
            # Apply BIO labeling
            for i, token_idx in enumerate(entity_tokens):
                if i == 0:
                    labels[token_idx] = self.entity_to_id[f'B-{entity_type}']
                else:
                    labels[token_idx] = self.entity_to_id[f'I-{entity_type}']
        
        return labels
    
    def _create_relationship_data(self, relationships: List[Dict], entities: List[Dict]) -> Dict:
        """Create relationship training data"""
        
        # Create entity lookup
        entity_lookup = {e['text']: i for i, e in enumerate(entities)}
        
        pairs = []
        labels = []
        
        for rel in relationships:
            source_text = rel['source_entity']
            target_text = rel['target_entity']
            rel_type = rel['relationship_type']
            
            if (source_text in entity_lookup and 
                target_text in entity_lookup and 
                rel_type in self.relationship_to_id):
                
                pairs.append([entity_lookup[source_text], entity_lookup[target_text]])
                labels.append(self.relationship_to_id[rel_type])
        
        # Add negative examples (no relationship)
        max_negative_pairs = len(pairs) * 2  # 2:1 negative to positive ratio
        negative_count = 0
        
        for i, source_entity in enumerate(entities):
            if negative_count >= max_negative_pairs:
                break
            
            for j, target_entity in enumerate(entities):
                if i != j and negative_count < max_negative_pairs:
                    # Check if this pair already has a relationship
                    existing_pair = any(
                        (pair[0] == i and pair[1] == j) or (pair[0] == j and pair[1] == i)
                        for pair in pairs
                    )
                    
                    if not existing_pair:
                        pairs.append([i, j])
                        labels.append(self.relationship_to_id['NO_RELATION'])
                        negative_count += 1
        
        return {
            'pairs': pairs,
            'labels': labels
        }
    
    def __len__(self):
        return len(self.processed_examples)
    
    def __getitem__(self, idx):
        return self.processed_examples[idx]
```

### 4.3 Multi-Task Trainer Implementation

#### Advanced Training Loop with 100 Epochs
```python
class LegalBERTMultiTaskTrainer:
    """Advanced trainer for 100-epoch Legal-BERT training"""
    
    def __init__(self, config: LegalBERTTrainingConfig):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Initialize models
        self._initialize_models()
        
        # Training state
        self.training_state = {
            'epoch': 0,
            'global_step': 0,
            'best_score': 0.0,
            'epochs_without_improvement': 0
        }
    
    def _initialize_models(self):
        """Initialize Legal-BERT models"""
        
        # Load Legal-BERT configuration
        bert_config = AutoConfig.from_pretrained(self.config.model_name)
        bert_config.dropout = self.config.dropout_rate
        bert_config.attention_dropout = self.config.attention_dropout
        
        # Initialize multi-task model
        self.model = LegalBERTMultiTask(bert_config)
        self.model.to(self.device)
        
        # Print model info
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        
        logger.info(f"Model initialized with {total_params:,} parameters ({trainable_params:,} trainable)")
    
    def train(self, training_data: List[Dict]):
        """Main training function for 100 epochs"""
        
        logger.info(f"Starting Legal-BERT training for {self.config.num_train_epochs} epochs")
        
        # Prepare datasets
        train_dataset, val_dataset, test_dataset = self._prepare_datasets(training_data)
        
        # Setup training arguments for 100 epochs
        training_args = self._create_training_arguments()
        
        # Create trainer
        trainer = self._create_trainer(train_dataset, val_dataset, training_args)
        
        # Start training
        try:
            train_result = trainer.train()
            
            # Save final model
            trainer.save_model()
            self._save_training_metadata(train_result)
            
            # Evaluate on test set
            test_results = trainer.evaluate(eval_dataset=test_dataset)
            logger.info(f"Final test results: {test_results}")
            
            return train_result, test_results
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
    
    def _create_training_arguments(self) -> TrainingArguments:
        """Create training arguments optimized for 100 epochs"""
        
        return TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            
            # Learning rate and scheduling
            learning_rate=self.config.learning_rate,
            lr_scheduler_type=self.config.lr_scheduler_type,
            warmup_ratio=self.config.warmup_ratio,
            
            # Regularization
            weight_decay=self.config.weight_decay,
            max_grad_norm=self.config.max_grad_norm,
            label_smoothing_factor=self.config.label_smoothing_factor,
            
            # Evaluation and saving
            evaluation_strategy=self.config.evaluation_strategy,
            eval_steps=self.config.eval_steps,
            save_steps=self.config.save_steps,
            save_total_limit=self.config.save_total_limit,
            
            # Best model selection
            load_best_model_at_end=self.config.load_best_model_at_end,
            metric_for_best_model=self.config.metric_for_best_model,
            greater_is_better=self.config.greater_is_better,
            
            # Logging
            logging_steps=self.config.logging_steps,
            report_to=self.config.report_to,
            
            # Optimization
            fp16=self.config.fp16,
            dataloader_num_workers=self.config.dataloader_num_workers,
            remove_unused_columns=self.config.remove_unused_columns,
            
            # Advanced settings for long training
            save_safetensors=True,
            resume_from_checkpoint=True,  # Allow resuming if interrupted
            
            # Memory optimization
            gradient_checkpointing=True,
            dataloader_pin_memory=True,
        )
    
    def _create_trainer(self, train_dataset, val_dataset, training_args) -> Trainer:
        """Create customized trainer with callbacks"""
        
        # Custom callbacks for 100-epoch training
        callbacks = [
            EarlyStoppingCallback(
                early_stopping_patience=self.config.early_stopping_patience,
                early_stopping_threshold=self.config.early_stopping_threshold
            ),
            # Custom callback for periodic model saving
            PeriodicSaveCallback(save_every_n_epochs=5),
            # Custom callback for learning rate monitoring
            LearningRateMonitorCallback(),
        ]
        
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=self.tokenizer,
            data_collator=self._create_data_collator(),
            compute_metrics=self._compute_multi_task_metrics,
            callbacks=callbacks,
        )
        
        return trainer
    
    def _compute_multi_task_metrics(self, eval_pred):
        """Compute combined entity and relationship metrics"""
        
        entity_predictions, relationship_predictions, labels = eval_pred
        entity_labels, relationship_labels = labels
        
        # Entity recognition metrics
        entity_preds = np.argmax(entity_predictions, axis=2)
        entity_metrics = self._compute_entity_metrics(entity_preds, entity_labels)
        
        # Relationship extraction metrics  
        rel_preds = np.argmax(relationship_predictions, axis=1)
        rel_metrics = self._compute_relationship_metrics(rel_preds, relationship_labels)
        
        # Combined metrics
        combined_f1 = (entity_metrics['f1'] * self.config.entity_loss_weight + 
                      rel_metrics['f1'] * self.config.relationship_loss_weight)
        
        return {
            # Entity metrics
            'entity_precision': entity_metrics['precision'],
            'entity_recall': entity_metrics['recall'],
            'entity_f1': entity_metrics['f1'],
            
            # Relationship metrics
            'relationship_precision': rel_metrics['precision'],
            'relationship_recall': rel_metrics['recall'], 
            'relationship_f1': rel_metrics['f1'],
            
            # Combined metric
            'combined_f1': combined_f1
        }
    
    def _save_training_metadata(self, train_result):
        """Save comprehensive training metadata"""
        
        metadata = {
            'model_config': self.config.__dict__,
            'training_results': train_result.__dict__ if hasattr(train_result, '__dict__') else str(train_result),
            'model_info': {
                'base_model': self.config.model_name,
                'total_parameters': sum(p.numel() for p in self.model.parameters()),
                'trainable_parameters': sum(p.numel() for p in self.model.parameters() if p.requires_grad),
            },
            'training_timestamp': datetime.now().isoformat(),
            'device_info': str(self.device),
            'torch_version': torch.__version__,
            'transformers_version': transformers.__version__
        }
        
        with open(f"{self.config.output_dir}/training_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Training metadata saved to {self.config.output_dir}/training_metadata.json")
```

---

## 5. Evaluation and Testing

### 5.1 Real-World Testing Framework

#### Document Testing Pipeline
```python
class LegalBERTEvaluator:
    """Comprehensive evaluation using real legal documents"""
    
    def __init__(self, model_path: str, test_documents: List[str]):
        self.model_path = model_path
        self.test_documents = test_documents
        
        # Load trained models
        self.entity_model = AutoModelForTokenClassification.from_pretrained(
            f"{model_path}/entity_model"
        )
        self.relationship_model = AutoModelForSequenceClassification.from_pretrained(
            f"{model_path}/relationship_model"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Load configuration and mappings
        with open(f"{model_path}/training_metadata.json", 'r') as f:
            self.metadata = json.load(f)
    
    async def comprehensive_evaluation(self) -> Dict[str, Any]:
        """Run comprehensive evaluation on real legal documents"""
        
        results = {
            'performance_metrics': {},
            'document_analysis': [],
            'error_analysis': {},
            'comparison_with_baseline': {}
        }
        
        # Test on different document types
        doc_types = {
            'briefs': [doc for doc in self.test_documents if 'brief' in doc.lower()],
            'motions': [doc for doc in self.test_documents if 'motion' in doc.lower()], 
            'orders': [doc for doc in self.test_documents if 'order' in doc.lower()],
            'opinions': [doc for doc in self.test_documents if 'opinion' in doc.lower()]
        }
        
        for doc_type, docs in doc_types.items():
            if not docs:
                continue
                
            logger.info(f"Evaluating {len(docs)} {doc_type} documents...")
            
            type_results = await self._evaluate_document_type(docs, doc_type)
            results['document_analysis'].append({
                'document_type': doc_type,
                'count': len(docs),
                'results': type_results
            })
        
        # Overall performance metrics
        results['performance_metrics'] = self._calculate_overall_metrics(results['document_analysis'])
        
        # Compare with baseline (existing entity extraction service)
        results['comparison_with_baseline'] = await self._compare_with_baseline()
        
        return results
    
    async def _evaluate_document_type(self, documents: List[str], doc_type: str) -> Dict[str, Any]:
        """Evaluate model performance on specific document type"""
        
        results = {
            'entity_accuracy': [],
            'relationship_accuracy': [],
            'processing_times': [],
            'error_cases': []
        }
        
        for doc_path in documents:
            try:
                # Load document
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Time the extraction
                start_time = time.time()
                
                # Extract entities and relationships
                entities = await self._extract_entities(content)
                relationships = await self._extract_relationships(content, entities)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Evaluate against ground truth (if available)
                if self._has_ground_truth(doc_path):
                    ground_truth = self._load_ground_truth(doc_path)
                    
                    entity_metrics = self._evaluate_entities(entities, ground_truth['entities'])
                    rel_metrics = self._evaluate_relationships(relationships, ground_truth['relationships'])
                    
                    results['entity_accuracy'].append(entity_metrics['f1'])
                    results['relationship_accuracy'].append(rel_metrics['f1'])
                
                results['processing_times'].append(processing_time)
                
            except Exception as e:
                logger.error(f"Error evaluating document {doc_path}: {e}")
                results['error_cases'].append({
                    'document': doc_path,
                    'error': str(e)
                })
        
        return results
    
    async def _compare_with_baseline(self) -> Dict[str, Any]:
        """Compare performance with existing Entity Extraction Service"""
        
        comparison_results = {}
        
        # Test a sample of documents with both systems
        sample_docs = self.test_documents[:10]  # Test on 10 documents
        
        for doc_path in sample_docs:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Test Legal-BERT model
            bert_start = time.time()
            bert_entities = await self._extract_entities(content)
            bert_relationships = await self._extract_relationships(content, bert_entities)
            bert_time = time.time() - bert_start
            
            # Test baseline Entity Extraction Service
            baseline_start = time.time()
            baseline_result = await self._test_baseline_service(content)
            baseline_time = time.time() - baseline_start
            
            # Compare results
            comparison_results[doc_path] = {
                'legal_bert': {
                    'entities_found': len(bert_entities),
                    'relationships_found': len(bert_relationships),
                    'processing_time': bert_time
                },
                'baseline': {
                    'entities_found': len(baseline_result.get('entities', [])),
                    'relationships_found': len(baseline_result.get('relationships', [])),
                    'processing_time': baseline_time
                }
            }
        
        return comparison_results
    
    async def _test_baseline_service(self, content: str) -> Dict[str, Any]:
        """Test baseline Entity Extraction Service for comparison"""
        
        # Call existing entity extraction service
        async with aiohttp.ClientSession() as session:
            payload = {
                "document_id": f"test_{int(time.time())}",
                "content": content,
                "extraction_mode": "hybrid",
                "enable_relationships": True,
                "confidence_threshold": 0.7
            }
            
            async with session.post(
                "http://localhost:8007/api/v1/extract",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Baseline service error: {response.status}")
                    return {'entities': [], 'relationships': []}
```

---

## 6. Deployment and Integration

### 6.1 Production Integration

#### Enhanced Document Service Integration
```python
class EnhancedLegalBERTDocumentProcessor:
    """Production-ready Legal-BERT integration for Document Service"""
    
    def __init__(self, 
                 model_path: str,
                 supabase_client,
                 prompt_client,
                 log_client):
        
        self.supabase_client = supabase_client
        self.prompt_client = prompt_client
        self.log_client = log_client
        
        # Load Legal-BERT models
        self.legal_bert_inference = LegalBERTInference(model_path)
        
        # Initialize MarkItDown for document conversion
        self.markitdown = MarkItDown()
        
        # Performance tracking
        self.performance_metrics = defaultdict(list)
    
    async def process_document(self, document_path: str, case_id: str, client_id: str) -> Dict[str, Any]:
        """Main document processing pipeline with Legal-BERT"""
        
        processing_start = time.time()
        
        try:
            # Step 1: Document conversion
            content = await self._convert_document(document_path)
            if not content:
                raise ValueError(f"Failed to convert document: {document_path}")
            
            # Step 2: Entity and relationship extraction with Legal-BERT
            extraction_result = await self.legal_bert_inference.extract_entities_and_relationships(content)
            
            # Step 3: Enhance with contextual information
            enhanced_entities = await self._enhance_entities(extraction_result['entities'])
            
            # Step 4: Create knowledge graph structures for GraphRAG
            graph_data = self._create_graph_structures(enhanced_entities, extraction_result['relationships'])
            
            # Step 5: Generate contextual chunks for retrieval
            contextual_chunks = self._create_contextual_chunks(content, enhanced_entities, extraction_result['relationships'])
            
            # Step 6: Store results
            document_record = await self._store_results(
                document_path, content, enhanced_entities, 
                extraction_result['relationships'], graph_data, 
                contextual_chunks, case_id, client_id
            )
            
            processing_time = time.time() - processing_start
            
            # Log performance metrics
            await self._log_performance_metrics(document_path, processing_time, extraction_result)
            
            return {
                'success': True,
                'document_id': document_record['id'],
                'entities_extracted': len(enhanced_entities),
                'relationships_extracted': len(extraction_result['relationships']),
                'contextual_chunks': len(contextual_chunks),
                'processing_time': processing_time,
                'graph_nodes': len(graph_data['nodes']),
                'graph_edges': len(graph_data['edges'])
            }
            
        except Exception as e:
            await self.log_client.error(f"Document processing failed for {document_path}: {e}")
            raise
    
    async def _enhance_entities(self, entities: List[Dict]) -> List[Dict]:
        """Enhance entities with additional contextual information"""
        
        enhanced_entities = []
        
        for entity in entities:
            enhanced = entity.copy()
            
            # Add jurisdiction context for state statutes
            if entity['label'] == 'STATE_STATUTE':
                enhanced['jurisdiction'] = self._identify_jurisdiction(entity['text'])
            
            # Add court hierarchy for court entities
            elif entity['label'] == 'COURT':
                enhanced['court_level'] = self._identify_court_level(entity['text'])
                enhanced['jurisdiction'] = self._identify_court_jurisdiction(entity['text'])
            
            # Add party type classification
            elif entity['label'] in ['PLAINTIFF', 'DEFENDANT']:
                enhanced['party_type'] = self._classify_party_type(entity['text'])
            
            # Add citation validation for case citations
            elif entity['label'] == 'CASE_CITATION':
                enhanced['bluebook_compliant'] = self._validate_bluebook_citation(entity['text'])
                enhanced['citation_components'] = self._parse_citation_components(entity['text'])
            
            enhanced_entities.append(enhanced)
        
        return enhanced_entities
    
    def _create_graph_structures(self, entities: List[Dict], relationships: List[Dict]) -> Dict[str, Any]:
        """Create knowledge graph structures for LlamaIndex GraphRAG"""
        
        # Create nodes for entities
        nodes = []
        for i, entity in enumerate(entities):
            node = {
                'id': f"entity_{i}",
                'label': entity['text'],
                'type': entity['label'],
                'properties': {
                    'confidence': entity.get('confidence', 0.9),
                    'start_pos': entity.get('start', 0),
                    'end_pos': entity.get('end', 0),
                    **entity.get('attributes', {})
                }
            }
            nodes.append(node)
        
        # Create edges for relationships
        edges = []
        entity_text_to_id = {e['text']: f"entity_{i}" for i, e in enumerate(entities)}
        
        for i, rel in enumerate(relationships):
            source_id = entity_text_to_id.get(rel.get('source_entity', {}).get('text'))
            target_id = entity_text_to_id.get(rel.get('target_entity', {}).get('text'))
            
            if source_id and target_id:
                edge = {
                    'id': f"relationship_{i}",
                    'source': source_id,
                    'target': target_id,
                    'type': rel['relationship_type'],
                    'properties': {
                        'confidence': rel.get('confidence_score', 0.8),
                        'evidence': rel.get('evidence_text', ''),
                    }
                }
                edges.append(edge)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'total_entities': len(entities),
                'total_relationships': len(relationships),
                'entity_types': list(set(e['label'] for e in entities)),
                'relationship_types': list(set(r['relationship_type'] for r in relationships))
            }
        }
    
    def _create_contextual_chunks(self, 
                                content: str, 
                                entities: List[Dict], 
                                relationships: List[Dict],
                                chunk_size: int = 1000,
                                overlap: int = 200) -> List[Dict]:
        """Create contextual chunks for enhanced retrieval"""
        
        chunks = []
        
        # Split content into sentences
        sentences = self._split_into_sentences(content)
        
        current_chunk = ""
        current_entities = []
        current_relationships = []
        chunk_start = 0
        
        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk + sentence) > chunk_size and current_chunk:
                # Finalize current chunk
                chunk_entities = self._get_entities_in_range(entities, chunk_start, chunk_start + len(current_chunk))
                chunk_relationships = self._get_relationships_in_range(relationships, chunk_entities)
                
                # Create contextual information
                context = self._generate_chunk_context(chunk_entities, chunk_relationships)
                
                chunks.append({
                    'text': current_chunk,
                    'context': context,
                    'entities': chunk_entities,
                    'relationships': chunk_relationships,
                    'start_pos': chunk_start,
                    'end_pos': chunk_start + len(current_chunk)
                })
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + sentence
                chunk_start = chunk_start + len(current_chunk) - len(overlap_text) - len(sentence)
            else:
                current_chunk += sentence
        
        # Add final chunk
        if current_chunk:
            chunk_entities = self._get_entities_in_range(entities, chunk_start, chunk_start + len(current_chunk))
            chunk_relationships = self._get_relationships_in_range(relationships, chunk_entities)
            context = self._generate_chunk_context(chunk_entities, chunk_relationships)
            
            chunks.append({
                'text': current_chunk,
                'context': context,
                'entities': chunk_entities,
                'relationships': chunk_relationships,
                'start_pos': chunk_start,
                'end_pos': chunk_start + len(current_chunk)
            })
        
        return chunks
```

---

## 7. Success Metrics and KPIs

### 7.1 Performance Targets

#### Entity Recognition Performance
- **Overall F1 Score**: >95% (vs current ~87%)
- **State Statute Recognition**: >98% with jurisdiction context
- **Case Citation Extraction**: >97% with Bluebook compliance
- **Court Name Recognition**: >96% with hierarchy classification
- **Party Identification**: >94% with type classification
- **Monetary Amount Extraction**: >99% with currency/amount parsing

#### Relationship Extraction Performance  
- **Overall Relationship F1**: >90% (vs current ~80%)
- **decided_by Relationships**: >95% (Court/Judge → Case/Opinion)
- **filed_by Relationships**: >92% (Attorney/Party → Document)
- **represents Relationships**: >90% (Attorney → Client/Party)
- **cited_in Relationships**: >88% (Case → Case precedent)

#### Processing Performance
- **Inference Speed**: <100ms per document (vs current 176ms)
- **Memory Usage**: <2GB model size
- **Throughput**: >200 documents/minute
- **GPU Utilization**: >90% efficiency

### 7.2 Quality Assurance Metrics

#### Training Quality
- **Training Loss Convergence**: <0.01 final loss
- **Validation F1 Improvement**: >15% over baseline
- **Overfitting Control**: <5% train/val gap
- **Early Stopping**: Triggered within 100 epochs if optimal

#### Production Integration
- **API Response Time**: <150ms end-to-end
- **Error Rate**: <1% processing failures
- **Uptime**: >99.9% service availability
- **Memory Stability**: No memory leaks over 24h

---

## 8. Implementation Timeline

### Phase 1: Data Preparation (Weeks 1-2)
- **Week 1**: Extract examples from `/patterns/detailed` endpoint
- **Week 1**: Generate synthetic training sentences (3-4 per example)
- **Week 2**: Create JSON annotation format with entity positions
- **Week 2**: Generate relationship annotations and validation

### Phase 2: Training Setup (Weeks 3-4)  
- **Week 3**: Set up 100-epoch training configuration
- **Week 3**: Implement multi-task learning architecture
- **Week 4**: Create training data loaders and validation pipeline
- **Week 4**: Set up monitoring and checkpointing system

### Phase 3: Model Training (Weeks 5-6)
- **Weeks 5-6**: Execute 100-epoch training (48-72 hour duration)
- **Continuous**: Monitor training metrics and adjust if needed
- **Week 6**: Run comprehensive model validation

### Phase 4: Testing and Validation (Weeks 7-8)
- **Week 7**: Test on real legal documents
- **Week 7**: Compare against baseline Entity Extraction Service
- **Week 8**: Performance optimization and fine-tuning
- **Week 8**: Create deployment package

### Phase 5: Production Integration (Weeks 9-10)
- **Week 9**: Integrate with Document Service pipeline
- **Week 9**: Connect to GraphRAG knowledge graph
- **Week 10**: Deploy and monitor production performance
- **Week 10**: Create documentation and handover

---

## 9. Risk Mitigation

### Technical Risks
- **Training Instability**: Implement gradient clipping and learning rate scheduling
- **Overfitting**: Use dropout, weight decay, and validation monitoring
- **Memory Constraints**: Implement gradient checkpointing and batch optimization
- **Performance Degradation**: Continuous monitoring and rollback procedures

### Operational Risks
- **Service Downtime**: Blue-green deployment with rollback capability
- **Data Quality Issues**: Comprehensive validation and testing pipeline
- **Integration Failures**: Thorough testing with existing Document Service
- **Resource Constraints**: GPU cluster with redundancy and scaling

---

## 10. Conclusion

This technical specification provides a comprehensive roadmap for training a custom Legal-BERT model that leverages your existing Entity Extraction Service assets to achieve significant performance improvements in legal entity recognition and relationship extraction. The 100-epoch training approach, combined with synthetic data generation from your existing patterns and examples, will create a highly accurate and specialized legal NLP model optimized for your Document Service and GraphRAG implementation.

The expected outcomes include >95% entity recognition accuracy, >90% relationship extraction accuracy, and <100ms inference times, representing substantial improvements over the current system while maintaining full integration with your existing infrastructure.